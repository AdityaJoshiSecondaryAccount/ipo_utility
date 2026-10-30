"""
Trades page E2E (/trades, templates/trades.html; "Trade Book" in the top bar).

The Trades page is the broker's book of ALL orders of ALL IPOs (the Orders page shows one IPO). Runs on its OWN IPOs and
groups (TRD MAIN IPO - MAINBOARD, TRD SME IPO - SME; groups TRD ONE / TWO / THREE) with orders dated February 2026, so
nothing it edits or deletes touches another page's data. Every test starts from the same fixture (reset in setUp).

The page lists orders of the chosen date range (From / To date; DEFAULT = today only, "All" = no limit) and filters
them on the server: IPO, Group, Order Category, Investor Type, a search box (live, debounced), a sort (click a header),
and a page size (50 / 100 / 200 / 250 / All, kept in the session). Per row: checkbox (bulk delete), Sr No., IPO, Group,
Type, Category, "Premium Strike Price" column (Application / Premium / the strike), Investor, Qty (a link to the
order's OrderDetail page), Rate, Date and time, Remark, and an Edit button (modal -> /trades/update_order/<id>, with a
Delete button inside). Also: Status modal (per-IPO Kostak / Subject To / Premium / Strike tables of the listed
orders), Bulk Order (CSV upload for several IPOs at once), Download (Excel / PDF), Columns, double-click a cell to
filter by it, and "+" / "-" keys to open BUY / SELL for the highlighted row.
"""
import csv
import datetime
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from collections import Counter
from urllib.parse import urlencode

import openpyxl
from playwright.sync_api import expect

from home.models import CurrentIpoName, GroupDetail, Order, OrderDetail
from home.views import format_remark
from test_cases.base import IPO_NAME, PersistentLiveServerTestCase, pause_for_inspection, settle

MAIN_IPO, SME_IPO = "TRD MAIN IPO", "TRD SME IPO"
ONE, TWO, THREE = "TRD ONE", "TRD TWO", "TRD THREE"
IPO_PRICE, PRE_OPEN = 100.0, 250.0
LOT = {"RETAIL": 100, "SHNI": 1400, "BHNI": 7000}

WINDOW = {"StartDate": "2026-02-10", "EndDate": "2026-02-14"}
SAMPLE_HEADER = ["IPOName", "GroupName", "Ordertype", "OrderCategory", "InvestorType", "Quantity", "Rate",
                 "StrikPrice", "OrderDate", "OrderTime", "Remark"]

# key -> (ipo, group, type, category, investor, qty, rate, date, time, method, remark)
SPECS = {
    "k_buy": ("main", ONE, "BUY", "Kostak", "RETAIL", 10, 450, "2026-02-10", "09:00:00", None, None),
    "k_sell": ("main", ONE, "SELL", "Kostak", "SHNI", 5, 600, "2026-02-10", "10:00:00", None,
               {"tags": ["Profit Sharing"], "text": "half"}),
    "st_buy": ("main", TWO, "BUY", "Subject To", "RETAIL", 8, 1200, "2026-02-11", "09:30:00", None, None),
    "st_sell": ("main", TWO, "SELL", "Subject To", "BHNI", 4, 5, "2026-02-11", "11:00:00", "Premium", None),
    "pr_buy": ("main", TWO, "BUY", "Premium", "PREMIUM", 100, 20, "2026-02-12", "09:00:00", None, None),
    "call_buy": ("main", THREE, "BUY", "CALL", "OPTIONS", 100, 10, "2026-02-12", "10:00:00", "120", None),
    "put_sell": ("main", THREE, "SELL", "PUT", "OPTIONS", 100, 12, "2026-02-12", "11:00:00", "200", None),
    "sme_buy": ("sme", ONE, "BUY", "Kostak", "RETAIL", 6, 300, "2026-02-13", "09:00:00", None, None),
    "sme_sell": ("sme", TWO, "SELL", "Kostak", "RETAIL", 2, 310, "2026-02-13", "10:00:00", None, None),
    "early": ("main", ONE, "BUY", "Kostak", "RETAIL", 1, 111, "2026-02-01", "09:00:00", None, None),
    "late": ("main", ONE, "SELL", "Kostak", "RETAIL", 1, 222, "2026-02-20", "09:00:00", None, None),
}
IN_WINDOW = [k for k in SPECS if k not in ("early", "late")]

# One parsed body row: the order id, its 12 cells (0 Sr, 1 IPO, 2 Group, 3 Type, 4 Category, 5 Strike/method,
# 6 Investor, 7 Qty, 8 Rate, 9 Date and time, 10 Remark, 11 Edit) and the targets of the quantity link / Edit button.
ROWS_JS = """() => [...document.querySelectorAll('#example tbody tr')].filter(tr => !tr.querySelector('td.dataTables_empty')).map(tr => {
    const td = [...tr.querySelectorAll(':scope > td')];
    const clean = t => t.replace(/\\s+/g, ' ').trim();
    const edit = tr.querySelector('button[data-order-id]');
    return {id: Number(tr.querySelector('.order-checkbox')?.value), cells: td.map(c => clean(c.textContent)),
            qtyHref: td[7]?.querySelector('a')?.getAttribute('href') || null,
            edit: edit ? {...edit.dataset} : null, focused: tr.classList.contains('row-focus')};
})"""

# The per-IPO block of the Status modal: every table's rows (th + td texts) and whether it is displayed.
STATUS_JS = """name => {
    const h = [...document.querySelectorAll('#exampleModal .modal-body h2')].find(h => h.textContent.trim() === name + ' IPO Status');
    if (!h) return null;
    const block = h.parentElement.parentElement, clean = t => t.replace(/\\s+/g, ' ').trim();
    const out = {blockShown: getComputedStyle(block).display !== 'none'};
    for (const cls of ['kostak-table', 'subjectto-table', 'premium-table', 'strikeprice-table']) {
        const w = block.querySelector('.' + cls);
        out[cls] = w ? {shown: getComputedStyle(w).display !== 'none',
            rows: [...w.querySelectorAll('tbody tr')].map(tr => [...tr.children].map(c => clean(c.textContent)))} : null;
    }
    return out;
}"""


def clock(text):
    return datetime.time.fromisoformat(text)


def day(text):
    return datetime.date.fromisoformat(text)


def shown_stamp(o):
    return datetime.datetime.combine(o.OrderDate, o.OrderTime).strftime("%b. %d, %Y | %I:%M:%S %p")


def money(x):
    return f"{float(x):.2f}"


class TradesPlaywrightTestCase(PersistentLiveServerTestCase):
    PAGE_NAME = "trades"
    _ran_any = False

    # ------------------------------------------------------------------ setup / teardown
    @classmethod
    def tearDownClass(cls):
        cls.log_summary()
        if cls._ran_any:
            try:
                cls.page.goto(f"{cls.live_server_url}/trades?{urlencode(WINDOW)}")
                settle(cls.page)
            except Exception:
                pass
            pause_for_inspection(cls.PAGE_NAME)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        type(self)._ran_any = True
        base = dict(IPOPrice=IPO_PRICE, PreOpenPrice=PRE_OPEN, LotSizeRetail=LOT["RETAIL"], LotSizeSHNI=LOT["SHNI"],
                    LotSizeBHNI=LOT["BHNI"], Active=True)
        self.ipos = {
            "main": CurrentIpoName.objects.get_or_create(user=self.user, IPOName=MAIN_IPO, defaults=dict(base, IPOType="MAINBOARD"))[0],
            "sme": CurrentIpoName.objects.get_or_create(user=self.user, IPOName=SME_IPO, defaults=dict(base, IPOType="SME"))[0],
        }
        self.groups = {n: GroupDetail.objects.get_or_create(user=self.user, GroupName=n)[0] for n in (ONE, TWO, THREE)}
        self.reset()
        self.js_errors = []
        self.page.on("pageerror", lambda e: self.js_errors.append(f"{e.message}\n{e.stack}"))
        self.clear_local_storage()

    def tearDown(self):
        self.clear_local_storage()
        super().tearDown()

    def clear_local_storage(self):
        try:
            if self.page.url.startswith(self.live_server_url):
                self.page.evaluate("localStorage.clear(); sessionStorage.clear()")
        except Exception:
            pass

    def trd_orders(self):
        return Order.objects.filter(user=self.user, OrderIPOName__in=self.ipos.values())

    def reset(self):
        OrderDetail.objects.filter(user=self.user, Order__OrderIPOName__in=self.ipos.values()).delete()
        self.trd_orders().delete()
        self.o = {key: self.seed(*spec) for key, spec in SPECS.items()}
        self.fixture_ids = {o.id for o in self.o.values()}

    def seed(self, ipo, group, order_type, category, investor, qty, rate, date, time, method=None, remark=None):
        order = Order.objects.create(
            user=self.user, OrderIPOName=self.ipos[ipo], OrderGroup=self.groups[group], OrderType=order_type,
            OrderCategory=category, InvestorType=investor, Quantity=qty, Rate=rate, Method=method, remark=remark,
            OrderDate=day(date), OrderTime=clock(time))
        if category in ("Kostak", "Subject To", "SubjectTo"):
            OrderDetail.objects.bulk_create([OrderDetail(user=self.user, Order=order, PreOpenPrice=PRE_OPEN)
                                             for _ in range(qty)])
        return order

    # ---------------------------------------------------------------------- page helpers
    def url(self, **params):
        query = {**WINDOW, "Order_page_size": "50", **params}
        return f"{self.live_server_url}/trades?{urlencode(query)}"

    def open(self, **params):
        """Open /trades with the test window (and page size 50) unless told otherwise."""
        self.page.goto(self.url(**params))
        settle(self.page)
        expect(self.page.locator("h1.header-title")).to_have_text("Trade Book")
        self.page.wait_for_selector("#example")
        return self

    def rows(self):
        return self.page.evaluate(ROWS_JS)

    def shown_ids(self):
        return [r["id"] for r in self.rows()]

    def shown_fixture(self):
        """Ids of the fixture orders in the table, as a set (other pages' orders, if any, are ignored)."""
        return {i for i in self.shown_ids() if i in self.fixture_ids}

    def ids(self, *keys):
        return {self.o[k].id for k in keys}

    def choose(self, selector, **kw):
        """Pick a filter option; the select's onchange submits the form -> page reload."""
        with self.page.expect_navigation():
            self.page.select_option(selector, **kw)
        settle(self.page)

    def search(self, text):
        box = self.page.locator("#mainSearchInput")
        box.fill(text)
        with self.page.expect_navigation():
            box.press("Enter")
        settle(self.page)

    def banner(self):
        """Text of the flash messages at the top of the page."""
        return " | ".join(t.strip() for t in self.page.locator(".alert").all_inner_texts())

    @staticmethod
    def expected_cells(o, sr):
        if o.OrderCategory == "Premium":
            method = "-"
        else:
            method = str(o.Method) if o.Method else "Application"
        return [str(sr), o.OrderIPOName.IPOName, o.OrderGroup.GroupName, o.OrderType, o.OrderCategory, method,
                o.InvestorType, str(int(o.Quantity)), None, shown_stamp(o), format_remark(o.remark) or "-", "Edit"]

    def assert_row_matches(self, row, o, sr):
        want = self.expected_cells(o, sr)
        got = list(row["cells"])
        self.assertAlmostEqual(float(got[8]), float(o.Rate), places=2, msg=f"rate of order {o.id}")
        got[8] = want[8] = None
        self.assertEqual(got, want, f"cells of order {o.id}")

    def db_window(self, start="2026-02-10", end="2026-02-14"):
        return Order.objects.filter(user=self.user, OrderDate__gte=start, OrderDate__lte=end).order_by("-id", "-OrderTime") \
            .select_related("OrderIPOName", "OrderGroup")

    # ====================================================================== 1. the list
    def test_lists_every_order_of_the_date_range_with_exact_cells(self):
        self.open()
        rows, expected = self.rows(), list(self.db_window())
        self.assertGreaterEqual(len(expected), len(IN_WINDOW))
        self.assertEqual([r["id"] for r in rows], [o.id for o in expected], "newest order first, every order once")
        self.assertEqual({o.id for o in expected} & self.fixture_ids, self.ids(*IN_WINDOW))
        for sr, (row, o) in enumerate(zip(rows, expected), start=1):
            self.assert_row_matches(row, o, sr)
        expect(self.page.get_by_text(f"Showing 1 to {len(expected)} of {len(expected)} Rows")).to_be_visible()
        self.assertEqual(self.js_errors, [])

    def test_quantity_links_to_the_order_detail_page_only_where_there_are_details(self):
        self.open()
        by_id = {r["id"]: r for r in self.rows()}
        for key in IN_WINDOW:
            o, row = self.o[key], by_id[self.o[key].id]
            if o.OrderCategory in ("Kostak", "Subject To"):
                stamp = datetime.datetime.combine(o.OrderDate, o.OrderTime)
                want = (f"/{o.OrderIPOName_id}/OrderDetail/{o.OrderType}/{o.OrderGroup.GroupName}/{o.OrderCategory}/"
                        f"{o.InvestorType}/{stamp:%Y%m%d}/{stamp:%H%M%S}{o.id}")
                self.assertEqual(row["qtyHref"], want, key)
            else:
                self.assertIsNone(row["qtyHref"], f"{key}: Premium / options orders have no OrderDetail page")
        # ... and the link really opens that order's details
        o = self.o["k_buy"]
        with self.page.expect_navigation():
            self.page.locator(f'tr:has(.order-checkbox[value="{o.id}"]) td a').click()
        settle(self.page)
        self.assertIn(f"/{o.OrderIPOName_id}/OrderDetail/BUY/{o.OrderGroup.GroupName.replace(' ', '%20')}/Kostak/RETAIL/20260210/090000{o.id}",
                      self.page.url)
        expect(self.page.locator("body")).not_to_contain_text("Server Error")

    def test_every_order_the_buy_and_sell_pages_placed_is_listed(self):
        pipeline = Order.objects.filter(user=self.user, OrderIPOName__IPOName=IPO_NAME)
        if not pipeline.exists():
            self.skipTest("No BUY / SELL data yet - run `python run_tests.py` so BUY and SELL run first.")
        ipo = CurrentIpoName.objects.get(user=self.user, IPOName=IPO_NAME)
        self.open(StartDate="All", EndDate="All", IPOFilter=ipo.id, Order_page_size="All")
        want = list(pipeline.order_by("-id", "-OrderTime").select_related("OrderIPOName", "OrderGroup"))
        rows = self.rows()
        self.assertEqual([r["id"] for r in rows], [o.id for o in want])
        for sr, (row, o) in enumerate(zip(rows, want), start=1):
            self.assert_row_matches(row, o, sr)

    def test_the_date_range_defaults_to_today(self):
        self.page.goto(f"{self.live_server_url}/trades")
        settle(self.page)
        today = datetime.date.today().isoformat()
        self.assertEqual(self.page.input_value("#StartDate"), today)
        self.assertEqual(self.page.input_value("#EndDate"), today)
        self.assertEqual(self.shown_fixture(), set(), "February 2026 orders are not 'today'")
        expect(self.page.locator("#StartDate + input")).to_have_value(datetime.date.today().strftime("%d/%m/%Y"))

    def test_date_range_is_inclusive_and_all_removes_the_limit(self):
        cases = [
            ({"StartDate": "2026-02-10", "EndDate": "2026-02-10"}, ["k_buy", "k_sell"]),
            ({"StartDate": "2026-02-11", "EndDate": "2026-02-12"}, ["st_buy", "st_sell", "pr_buy", "call_buy", "put_sell"]),
            ({"StartDate": "2026-02-01", "EndDate": "2026-02-01"}, ["early"]),
            ({"StartDate": "2026-02-10", "EndDate": "2026-02-20"}, IN_WINDOW + ["late"]),
            ({"StartDate": "2026-02-14", "EndDate": "2026-02-10"}, []),                      # backwards range
            ({"StartDate": "All", "EndDate": "All"}, list(SPECS)),
        ]
        for params, keys in cases:
            with self.subTest(**params):
                self.open(IPOFilter="All", Order_page_size="All", **params)
                self.assertEqual(self.shown_fixture(), self.ids(*keys))

    def test_dates_can_be_typed_or_picked(self):
        self.open()
        start = self.page.locator("#StartDate + input")
        with self.page.expect_navigation():
            start.fill("11/02/2026")
            start.press("Enter")
        settle(self.page)
        self.assertEqual(self.page.input_value("#StartDate"), "2026-02-11")
        self.assertEqual(self.shown_fixture(), self.ids("st_buy", "st_sell", "pr_buy", "call_buy", "put_sell", "sme_buy", "sme_sell"))
        with self.page.expect_navigation():
            self.page.evaluate("document.querySelector('#EndDate')._flatpickr.setDate('2026-02-12', true)")
        settle(self.page)
        self.assertEqual(self.page.input_value("#EndDate"), "2026-02-12")
        self.assertEqual(self.shown_fixture(), self.ids("st_buy", "st_sell", "pr_buy", "call_buy", "put_sell"))

    # ====================================================================== 2. filters
    def test_dropdowns_only_offer_what_the_listed_orders_have(self):
        self.open(IPOFilter=self.ipos["sme"].id)
        options = lambda sel: self.page.eval_on_selector_all(f"{sel} option", "os => os.map(o => o.textContent.trim())")
        self.assertEqual(options("#Groupfilter"), ["All", ONE, TWO])
        self.assertEqual(options("#OrderCategoryFilter"), ["All", "Kostak"])
        self.assertEqual(options("#InvestorTypeFilter"), ["All", "Retail"])
        ipo_names = options("#IPOFilter")
        self.assertEqual(ipo_names[0], "All")
        self.assertIn(MAIN_IPO, ipo_names)
        self.assertIn(SME_IPO, ipo_names)
        self.assertEqual(self.page.input_value("#IPOFilter"), str(self.ipos["sme"].id))
        self.assertEqual(self.shown_fixture(), self.ids("sme_buy", "sme_sell"))

        self.open(IPOFilter=self.ipos["main"].id)
        self.assertEqual(options("#Groupfilter"), ["All", ONE, THREE, TWO])      # by name
        self.assertEqual(options("#OrderCategoryFilter"), ["All", "Kostak", "Subject To", "CALL", "PUT", "Premium"])
        self.assertEqual(options("#InvestorTypeFilter"), ["All", "Retail", "SHNI", "BHNI", "OPTIONS", "Premium"])

    def test_each_filter_narrows_the_list(self):
        main = str(self.ipos["main"].id)
        cases = [
            ("#IPOFilter", {"value": str(self.ipos["sme"].id)}, ["sme_buy", "sme_sell"]),
            ("#Groupfilter", {"label": TWO}, ["st_buy", "st_sell", "pr_buy", "sme_sell"]),
            ("#OrderCategoryFilter", {"value": "Kostak"}, ["k_buy", "k_sell", "sme_buy", "sme_sell"]),
            ("#OrderCategoryFilter", {"value": "Subject To"}, ["st_buy", "st_sell"]),
            ("#OrderCategoryFilter", {"value": "CALL"}, ["call_buy"]),
            ("#InvestorTypeFilter", {"value": "RETAIL"}, ["k_buy", "st_buy", "sme_buy", "sme_sell"]),
            ("#InvestorTypeFilter", {"value": "OPTIONS"}, ["call_buy", "put_sell"]),
        ]
        for selector, pick, keys in cases:
            with self.subTest(filter=selector, pick=pick):
                self.open()
                self.choose(selector, **pick)
                self.assertEqual(self.shown_fixture(), self.ids(*keys))
                expect(self.page.locator(selector)).not_to_have_value("All")        # the choice stays selected
        # a filter combination, and all of them back to "All"
        self.open(IPOFilter=main)
        self.choose("#Groupfilter", label=TWO)
        self.choose("#OrderCategoryFilter", value="Subject To")
        self.choose("#InvestorTypeFilter", value="BHNI")
        self.assertEqual(self.shown_fixture(), self.ids("st_sell"))
        self.assertEqual(self.page.input_value("#Groupfilter"), TWO)
        for selector in ("#InvestorTypeFilter", "#OrderCategoryFilter", "#Groupfilter"):
            self.choose(selector, value="All")
        self.assertEqual(self.shown_fixture(), self.ids(*[k for k in IN_WINDOW if SPECS[k][0] == "main"]))

    def test_the_subject_to_filter_also_lists_legacy_subjectto_orders(self):
        legacy = self.seed("main", TWO, "BUY", "SubjectTo", "RETAIL", 3, 1300, "2026-02-12", "12:00:00")
        self.fixture_ids.add(legacy.id)
        self.open()
        self.choose("#OrderCategoryFilter", value="Subject To")
        self.assertEqual(self.shown_fixture(), self.ids("st_buy", "st_sell") | {legacy.id})

    def test_clear_filters_goes_back_to_the_defaults(self):
        self.open(IPOFilter=self.ipos["main"].id, Groupfilter=TWO)
        self.search("Premium")
        self.page.get_by_role("button", name="Clear filters").click()
        self.page.wait_for_url(re.compile(r"/trades$"))
        settle(self.page)
        for sel in ("#IPOFilter", "#Groupfilter", "#OrderCategoryFilter", "#InvestorTypeFilter"):
            self.assertEqual(self.page.input_value(sel), "All", sel)
        self.assertEqual(self.page.input_value("#mainSearchInput"), "")
        self.assertEqual(self.page.input_value("#StartDate"), datetime.date.today().isoformat())

    def test_double_clicking_a_cell_filters_by_it(self):
        cases = [(1, "#IPOFilter", self.ipos["sme"].id, self.o["sme_buy"], ["sme_buy", "sme_sell"]),
                 (2, "#Groupfilter", TWO, self.o["st_buy"], ["st_buy", "st_sell", "pr_buy", "sme_sell"]),
                 (4, "#OrderCategoryFilter", "Subject To", self.o["st_buy"], ["st_buy", "st_sell"]),
                 (6, "#InvestorTypeFilter", "RETAIL", self.o["k_buy"], ["k_buy", "st_buy", "sme_buy", "sme_sell"])]
        for column, select, value, order, keys in cases:
            with self.subTest(column=column):
                self.open()
                with self.page.expect_navigation():
                    self.page.locator(f'tr:has(.order-checkbox[value="{order.id}"]) td').nth(column).dblclick()
                settle(self.page)
                self.assertEqual(self.page.input_value(select), str(value))
                self.assertEqual(self.shown_fixture(), self.ids(*keys))
        # quantity / rate cells do not filter
        self.open()
        url = self.page.url
        self.page.locator(f'tr:has(.order-checkbox[value="{self.o["pr_buy"].id}"]) td').nth(8).dblclick()
        self.page.wait_for_timeout(600)
        self.assertEqual(self.page.url, url)

    # ====================================================================== 3. search
    def test_search_looks_at_every_visible_column(self):
        cases = [
            ("TRD SME", ["sme_buy", "sme_sell"]),                                       # IPO name
            ("trd two", ["st_buy", "st_sell", "pr_buy", "sme_sell"]),                   # group, any case
            ("SELL", ["k_sell", "st_sell", "put_sell", "sme_sell"]),                    # order type
            ("Premium", ["st_sell", "pr_buy"]),                                         # category / method / investor
            ("OPTIONS", ["call_buy", "put_sell"]),                                      # investor
            ("120", ["st_buy", "call_buy"]),                                            # rate 1200 and strike 120
            ("Feb. 11, 2026 | 09:30:00 AM", ["st_buy", "st_sell"]),                     # the date as it is shown
            ("2026-02-12", ["pr_buy", "call_buy", "put_sell"]),                         # the date as stored
            ("zzz-nothing", []),
        ]
        for term, keys in cases:
            with self.subTest(search=term):
                self.open(IPOFilter="All")
                self.search(term)
                self.assertEqual(self.shown_fixture(), self.ids(*keys))
                self.assertEqual(self.page.input_value("#mainSearchInput"), term, "the box keeps what was typed")
        self.assertEqual(self.js_errors, [])

    def test_search_works_together_with_the_other_filters_and_resets_the_page(self):
        self.open(Groupfilter=ONE)
        self.search("SELL")
        self.assertEqual(self.shown_fixture(), self.ids("k_sell"))
        self.assertEqual(self.page.input_value("#Groupfilter"), ONE)
        self.assertEqual(self.page.input_value("#pageInput"), "1")
        self.search("")
        self.assertEqual(self.shown_fixture(), self.ids("k_buy", "k_sell", "sme_buy"))

    def test_typing_searches_by_itself_after_a_short_pause(self):
        self.open()
        box = self.page.locator("#mainSearchInput")
        box.click()
        with self.page.expect_navigation(timeout=5000):
            box.press_sequentially("TRD SME", delay=40)
        settle(self.page)
        self.assertEqual(self.shown_fixture(), self.ids("sme_buy", "sme_sell"))
        self.assertEqual(self.page.input_value("#mainSearchInput"), "TRD SME")

    # ====================================================================== 4. sort
    def sort_by(self, title):
        header = self.page.locator(".dataTables_scrollHead thead tr:not(.filters) th", has_text=re.compile(rf"^\s*{title}\s*$"))
        with self.page.expect_navigation():
            header.first.click()
        settle(self.page)

    def test_clicking_a_header_sorts_all_rows_on_the_server(self):
        window = self.db_window()
        wanted = {
            "Qty": lambda d: ("Quantity", "id"),
            "Rate": lambda d: ("Rate", "id"),
            "Group Name": lambda d: ("OrderGroup__GroupName", "id"),
            "IPO Name": lambda d: ("OrderIPOName__IPOName", "id"),
            "Order Type": lambda d: ("OrderType", "id"),
            "Date and Time": lambda d: ("OrderDate", "OrderTime", "id"),
        }
        for title, fields in wanted.items():
            with self.subTest(column=title):
                self.open(IPOFilter="All")
                self.sort_by(title)
                asc = [o.id for o in window.order_by(*fields(None))]
                self.assertEqual(self.shown_ids(), asc, f"{title} ascending")
                self.sort_by(title)
                desc = [o.id for o in window.order_by(*[("-" + f) for f in fields(None)])]
                self.assertEqual(self.shown_ids(), desc, f"{title} descending")
                self.assertEqual(self.page.input_value("#sort_dir"), "desc")

    def test_the_sort_survives_a_filter_change(self):
        self.open()
        self.sort_by("Qty")
        self.sort_by("Qty")                                           # descending
        self.choose("#Groupfilter", label=TWO)
        qty = [int(r["cells"][7]) for r in self.rows()]
        self.assertEqual(qty, sorted(qty, reverse=True))
        self.assertEqual(self.page.input_value("#sort_dir"), "desc")
        self.assertEqual(self.shown_fixture(), self.ids("st_buy", "st_sell", "pr_buy", "sme_sell"))

    # ====================================================================== 5. page size and pages
    def fillers(self, count=55):
        Order.objects.bulk_create([
            Order(user=self.user, OrderIPOName=self.ipos["main"], OrderGroup=self.groups[ONE], OrderType="BUY",
                  OrderCategory="Kostak", InvestorType="RETAIL", Quantity=1, Rate=500 + i,
                  OrderDate=day("2026-02-15"), OrderTime=clock("08:00:00")) for i in range(count)])
        return {"StartDate": "2026-02-15", "EndDate": "2026-02-15", "IPOFilter": self.ipos["main"].id}

    def test_pages_of_fifty_and_the_page_links(self):
        view = self.fillers(55)
        self.open(**view)
        rows = self.rows()
        self.assertEqual(len(rows), 50)
        self.assertEqual([r["cells"][0] for r in rows], [str(i) for i in range(1, 51)])
        expect(self.page.get_by_text("Showing 1 to 50 of 55 Rows")).to_be_visible()
        with self.page.expect_navigation():
            self.page.locator(".pagination .page-link", has_text=re.compile(r"^2$")).click()
        settle(self.page)
        rows = self.rows()
        self.assertEqual([r["cells"][0] for r in rows], [str(i) for i in range(51, 56)])
        expect(self.page.get_by_text("Showing 51 to 55 of 55 Rows")).to_be_visible()
        self.assertEqual(len({r["id"] for r in rows}), 5)
        # a page past the end shows the last page
        self.open(page=99, **view)
        self.assertEqual(len(self.rows()), 5)

    def test_page_size_all_and_the_size_is_remembered(self):
        view = self.fillers(55)
        self.open(**view)
        self.choose("select[name=Order_page_size]", value="All")
        self.assertEqual(len(self.rows()), 55)
        expect(self.page.get_by_text("Showing 1 to 55 of 55 Rows")).to_be_visible()
        # the choice lives in the session: a visit without the parameter keeps it
        self.page.goto(f"{self.live_server_url}/trades?{urlencode({k: v for k, v in view.items()})}")
        settle(self.page)
        self.assertEqual(len(self.rows()), 55)
        self.choose("select[name=Order_page_size]", value="100")
        self.assertEqual(len(self.rows()), 55)
        self.open(**view)                                              # back to 50 for the pages that follow
        self.assertEqual(len(self.rows()), 50)

    @unittest.expectedFailure
    def test_the_page_size_select_shows_the_size_in_use(self):
        """KNOWN BUG: the select compares the size (a string) with the number 100, so no option is marked selected."""
        view = self.fillers(55)
        self.open(**view)
        self.choose("select[name=Order_page_size]", value="100")
        self.assertEqual(self.page.input_value("select[name=Order_page_size]"), "100")
        self.open(**view)

    @unittest.expectedFailure
    def test_the_export_dialog_counts_all_rows_when_the_list_has_pages(self):
        """KNOWN BUG: 'N rows out of M total rows' looks for a <p> that this page does not have, so M = N."""
        view = self.fillers(55)
        self.open(**view)
        self.page.get_by_role("button", name="Download").click()
        self.page.locator(".dt-button-collection .dt-button", has_text="Excel").click()
        popup = self.page.locator(".swal2-popup")
        expect(popup).to_be_visible()
        try:
            expect(popup).to_contain_text("export 50 rows out of 55 total rows")
        finally:
            popup.locator(".swal2-cancel").click()

    # ====================================================================== 6. column filters, columns, row focus
    def type_in_column_box(self, placeholder, text):
        box = self.page.locator(f'.dataTables_scrollHead .filters input[placeholder="{placeholder}"]')
        box.press_sequentially(text)                                    # the box filters on keyup
        self.page.wait_for_timeout(400)
        return box

    def test_column_filter_boxes_narrow_the_rows_once_a_sort_is_chosen(self):
        self.open(IPOFilter="All")
        self.sort_by("Qty")
        url = self.page.url
        box = self.type_in_column_box("Order Type", "SELL")
        self.assertEqual(self.page.url, url, "a column box filters in the page, no reload")
        self.assertEqual(self.shown_fixture(), self.ids("k_sell", "st_sell", "put_sell", "sme_sell"))
        box.press("Control+a")
        box.press("Backspace")
        self.page.wait_for_timeout(400)
        self.assertEqual(self.shown_fixture(), self.ids(*IN_WINDOW))
        self.type_in_column_box("Group Name", "TRD THREE")
        self.assertEqual(self.shown_fixture(), self.ids("call_buy", "put_sell"))

    @unittest.expectedFailure
    def test_column_filter_boxes_work_on_a_freshly_opened_page(self):
        """KNOWN BUG: the filter's redraw fires DataTables' 'order' event; with no sort chosen yet the page sees
        column 0 != '' and submits the form, so the page reloads and what was typed is lost."""
        self.open(IPOFilter="All")
        url = self.page.url
        try:
            self.type_in_column_box("Order Type", "SELL")
        except Exception:
            pass                                                        # typing into a page that is reloading
        settle(self.page)
        self.assertEqual(self.page.url, url)
        self.assertEqual(self.shown_fixture(), self.ids("k_sell", "st_sell", "put_sell", "sme_sell"))

    def test_the_columns_button_hides_and_shows_a_column(self):
        self.open()
        header = self.page.locator(".dataTables_scrollHead thead tr:not(.filters) th", has_text="Remark")
        expect(header).to_be_visible()
        self.page.get_by_role("button", name="Columns").click()
        self.page.locator(".dt-button-collection").get_by_text("Remark", exact=True).first.click()
        self.page.keyboard.press("Escape")
        expect(header).to_have_count(0)
        self.page.get_by_role("button", name="Columns").click()
        self.page.locator(".dt-button-collection").get_by_text("Remark", exact=True).first.click()
        self.page.keyboard.press("Escape")
        expect(self.page.locator(".dataTables_scrollHead thead tr:not(.filters) th", has_text="Remark")).to_be_visible()

    def test_the_plus_and_minus_keys_open_buy_and_sell_for_the_highlighted_row(self):
        self.open()
        rows = self.rows()
        self.assertTrue(rows[0]["focused"], "the first row starts highlighted")
        self.assertEqual(sum(r["focused"] for r in rows), 1)
        # click another row (an SME one): it takes the highlight and the shortcut follows it
        sme = self.o["sme_buy"]
        self.page.locator(f'tr:has(.order-checkbox[value="{sme.id}"]) td').nth(5).click()
        self.assertEqual([r["id"] for r in self.rows() if r["focused"]], [sme.id])
        for key, page_name in (("NumpadAdd", "BUY"), ("NumpadSubtract", "SELL")):
            with self.subTest(key=key):
                self.open()
                self.page.locator(f'tr:has(.order-checkbox[value="{sme.id}"]) td').nth(5).click()
                with self.page.expect_navigation():
                    self.page.keyboard.press(key)
                settle(self.page)
                self.assertRegex(self.page.url, rf"/{page_name}/{sme.OrderIPOName_id}/TRD(%20| )ONE")
                expect(self.page.locator("body")).not_to_contain_text("Server Error")

    # ====================================================================== 7. edit an order
    def open_edit(self, key, **params):
        o = self.o[key]
        self.open(**params)
        self.page.locator(f'button[data-order-id="{o.id}"]').click()
        modal = self.page.locator("#globalEditModal")
        expect(modal).to_be_visible()
        return o, modal

    def save_edit(self):
        with self.page.expect_navigation():
            self.page.locator('#globalEditForm button[type="submit"]').click()
        settle(self.page)

    def test_the_edit_modal_is_filled_with_the_order(self):
        for key in ("k_buy", "st_buy", "pr_buy", "call_buy", "sme_sell"):
            with self.subTest(order=key):
                o, modal = self.open_edit(key)
                value = lambda sel: self.page.input_value(sel)
                self.assertEqual(value("#modal_ipo_id"), str(o.OrderIPOName_id))
                self.assertEqual(value("#modal_group"), o.OrderGroup.GroupName)
                self.assertEqual(value("#modal_order_type"), o.OrderType)
                self.assertEqual(value("#modal_category"), o.OrderCategory)
                self.assertEqual(value("#modal_investor"), o.InvestorType)
                self.assertEqual(int(value("#modal_qty")), int(o.Quantity))
                # the browser drops ":00" seconds from a datetime-local value
                self.assertEqual(value("#modal_datetime"), f"{o.OrderDate}T{o.OrderTime:%H:%M}")
                rate = value("#modal_sub_rate" if o.OrderCategory == "Subject To" else "#modal_rate")
                self.assertAlmostEqual(float(rate), float(o.Rate), places=2)
                # the right rate / strike fields are showing
                expect(self.page.locator("#div_sub_rate")).to_be_visible() if o.OrderCategory == "Subject To" \
                    else expect(self.page.locator("#div_rate")).to_be_visible()
                if o.OrderCategory in ("CALL", "PUT"):
                    expect(self.page.locator("#div_strike")).to_be_visible()
                    self.assertEqual(int(float(value("#modal_strike"))), int(o.Method))
                else:
                    expect(self.page.locator("#div_strike")).to_be_hidden()
                expect(self.page.locator("#globalEditForm")).to_have_attribute("action", f"/trades/update_order/{o.id}")

    def test_cancel_closes_the_edit_modal_without_saving(self):
        o, modal = self.open_edit("k_buy")
        self.page.fill("#modal_rate", "999")
        modal.get_by_role("button", name="Cancel").click()
        expect(modal).to_be_hidden()
        o.refresh_from_db()
        self.assertEqual(float(o.Rate), 450.0)

    def test_editing_the_rate_saves_it(self):
        o, _ = self.open_edit("k_buy")
        self.page.fill("#modal_rate", "455")
        self.save_edit()
        self.assertIn("Order Modified successfully", self.banner())
        o.refresh_from_db()
        self.assertEqual((float(o.Rate), int(o.Quantity), o.OrderGroup.GroupName, o.OrderType), (455.0, 10, ONE, "BUY"))
        self.assertEqual(OrderDetail.objects.filter(Order=o).count(), 10)
        self.open(IPOFilter="All")
        row = next(r for r in self.rows() if r["id"] == o.id)
        self.assertAlmostEqual(float(row["cells"][8]), 455.0, places=2)

    def test_saving_without_a_change_keeps_the_order(self):
        o, _ = self.open_edit("k_buy")
        self.save_edit()
        o.refresh_from_db()
        self.assertEqual((float(o.Rate), int(o.Quantity), o.OrderGroup.GroupName, o.OrderType, o.OrderCategory),
                         (450.0, 10, ONE, "BUY", "Kostak"))
        self.assertEqual(OrderDetail.objects.filter(Order=o).count(), 10)

    @unittest.expectedFailure
    def test_saving_without_a_change_says_so_and_keeps_the_tally(self):
        """KNOWN BUG: the 'same values' check looks up remark=None, which on a JSON field means JSON null, never an
        empty remark - so it never matches: an unchanged save says 'Order Modified successfully' and un-tallies."""
        o = self.o["k_buy"]
        Order.objects.filter(id=o.id).update(Telly="True")
        self.open_edit("k_buy")
        self.save_edit()
        o.refresh_from_db()
        self.assertEqual(str(o.Telly), "True")
        self.assertIn("Order values are same", self.banner())

    def test_every_field_of_an_order_can_be_changed_at_once(self):
        o, _ = self.open_edit("k_buy")
        self.page.select_option("#modal_ipo_id", str(self.ipos["sme"].id))
        self.page.select_option("#modal_group", TWO)
        self.page.select_option("#modal_order_type", "SELL")
        self.page.fill("#modal_rate", "333")
        self.page.fill("#modal_datetime", "2026-02-12T14:15:16")
        self.save_edit()
        self.assertIn("Order Modified successfully", self.banner())
        o.refresh_from_db()
        self.assertEqual((o.OrderIPOName_id, o.OrderGroup.GroupName, o.OrderType, float(o.Rate), str(o.OrderDate), str(o.OrderTime)),
                         (self.ipos["sme"].id, TWO, "SELL", 333.0, "2026-02-12", "14:15:16"))
        self.assertEqual(o.InvestorType, "RETAIL", "an SME order is always RETAIL")

    def test_a_subject_to_order_is_edited_through_its_own_rate_field(self):
        o, _ = self.open_edit("k_buy")
        self.page.select_option("#modal_category", "Subject To")
        expect(self.page.locator("#div_sub_rate")).to_be_visible()
        expect(self.page.locator("#div_rate")).to_be_hidden()
        self.page.fill("#modal_sub_rate", "1250")
        self.save_edit()
        o.refresh_from_db()
        self.assertEqual((o.OrderCategory, float(o.Rate)), ("Subject To", 1250.0))

    def test_an_options_order_can_change_its_strike_price(self):
        o, _ = self.open_edit("call_buy")
        self.page.fill("#modal_strike", "135")
        self.save_edit()
        o.refresh_from_db()
        self.assertEqual((o.OrderCategory, str(o.Method)), ("CALL", "135"))

    def test_raising_the_quantity_adds_blank_order_details_and_lowering_it_removes_them(self):
        o, _ = self.open_edit("k_buy")
        self.page.fill("#modal_qty", "13")
        self.save_edit()
        o.refresh_from_db()
        self.assertEqual((int(o.Quantity), OrderDetail.objects.filter(Order=o).count()), (13, 13))
        o, _ = self.open_edit("k_buy")
        self.page.fill("#modal_qty", "7")
        self.save_edit()
        o.refresh_from_db()
        self.assertEqual((int(o.Quantity), OrderDetail.objects.filter(Order=o).count()), (7, 7))

    def test_a_quantity_cannot_drop_below_the_details_that_already_have_a_pan(self):
        from home.models import ClientDetail
        o = self.o["k_buy"]
        client = ClientDetail.objects.get_or_create(user=self.user, PANNo="TRDPN1234A", defaults={"Name": "TRD CLIENT", "Group": o.OrderGroup})[0]
        OrderDetail.objects.filter(Order=o).update(OrderDetailPANNo=client)      # all 10 have a PAN
        self.open_edit("k_buy")
        self.page.fill("#modal_qty", "4")
        self.save_edit()
        self.assertIn("Only Blank PAN entry in OrderDetail can be deleted", self.banner())
        self.assertEqual(OrderDetail.objects.filter(Order=o).count(), 10)

    def test_the_edit_form_refuses_an_empty_quantity(self):
        o, _ = self.open_edit("k_buy")
        self.page.fill("#modal_qty", "")
        url = self.page.url
        self.page.locator('#globalEditForm button[type="submit"]').click()
        self.page.wait_for_timeout(400)
        self.assertEqual(self.page.url, url)
        self.assertTrue(self.page.evaluate("document.querySelector('#modal_qty').validity.valueMissing"))

    @unittest.expectedFailure
    def test_editing_an_order_keeps_its_remark(self):
        """KNOWN BUG: the edit modal has no remark field but the view saves 'no remark', wiping the order's remark."""
        o, _ = self.open_edit("k_sell")
        self.page.fill("#modal_rate", "605")
        self.save_edit()
        o.refresh_from_db()
        self.assertEqual(float(o.Rate), 605.0)
        self.assertEqual(format_remark(o.remark), "Profit Sharing - half")

    @unittest.expectedFailure
    def test_the_filters_are_kept_after_editing_an_order(self):
        """KNOWN BUG: saving redirects to /trades?page=None, so the date range / filters / search are lost."""
        o, _ = self.open_edit("st_buy", Groupfilter=TWO)
        self.page.fill("#modal_rate", "1210")
        self.save_edit()
        self.assertIn("StartDate=2026-02-10", self.page.url)
        self.assertEqual(self.page.input_value("#Groupfilter"), TWO)

    # ====================================================================== 8. delete
    def test_delete_inside_the_edit_modal_asks_first(self):
        o, modal = self.open_edit("k_buy")
        self.page.once("dialog", lambda d: d.dismiss())
        modal.get_by_role("button", name="Delete", exact=True).click()
        self.page.wait_for_timeout(500)
        self.assertTrue(Order.objects.filter(id=o.id).exists(), "cancelling the confirmation keeps the order")

        messages = []
        def accept(d):
            messages.append(d.message)
            d.accept()
        self.page.once("dialog", accept)
        with self.page.expect_navigation():
            modal.get_by_role("button", name="Delete", exact=True).click()
        settle(self.page)
        self.assertEqual(messages, ["Are you sure you want to delete this order?"])
        self.assertFalse(Order.objects.filter(id=o.id).exists())
        self.assertFalse(OrderDetail.objects.filter(Order_id=o.id).exists())
        self.assertRegex(self.page.url, r"/trades$")
        self.assertTrue(Order.objects.filter(id=self.o["k_sell"].id).exists(), "other orders stay")

    def select_rows(self, *keys):
        for key in keys:
            self.page.locator(f'.order-checkbox[value="{self.o[key].id}"]').check()

    def test_selecting_rows_swaps_bulk_order_for_delete(self):
        self.open(IPOFilter="All")
        bulk, delete = self.page.locator("#bulk-order-btn"), self.page.locator("#bulk-delete-btn")
        expect(bulk).to_be_visible()
        expect(delete).to_be_hidden()
        self.select_rows("k_buy")
        expect(delete).to_be_visible()
        expect(bulk).to_be_hidden()
        self.page.locator("#select-all-orders").check()
        boxes = self.page.locator(".order-checkbox")
        self.assertEqual(boxes.evaluate_all("els => els.filter(e => e.checked).length"), boxes.count())
        self.page.locator(f'.order-checkbox[value="{self.o["k_sell"].id}"]').uncheck()
        expect(self.page.locator("#select-all-orders")).not_to_be_checked()
        expect(delete).to_be_visible()
        self.page.locator("#select-all-orders").check()
        self.page.locator("#select-all-orders").uncheck()
        self.assertEqual(boxes.evaluate_all("els => els.filter(e => e.checked).length"), 0)
        expect(delete).to_be_hidden()
        expect(bulk).to_be_visible()

    def test_bulk_delete_removes_exactly_the_selected_orders(self):
        self.open(IPOFilter="All")
        self.select_rows("k_buy", "st_buy", "sme_sell")
        self.page.locator("#bulk-delete-btn").click()
        modal = self.page.locator("#bulkDeleteModal")
        expect(modal).to_be_visible()
        expect(modal.locator("#selected-count")).to_have_text("3")
        expect(modal.locator("#order-suffix")).to_have_text("orders")
        # Cancel keeps everything
        modal.get_by_role("button", name="Cancel").click()
        expect(modal).to_be_hidden()
        self.assertEqual(self.trd_orders().count(), len(SPECS))
        self.page.locator("#bulk-delete-btn").click()
        with self.page.expect_navigation():
            modal.locator("#confirm-bulk-delete").click()
        settle(self.page)
        gone = self.ids("k_buy", "st_buy", "sme_sell")
        self.assertFalse(Order.objects.filter(id__in=gone).exists())
        self.assertFalse(OrderDetail.objects.filter(Order_id__in=gone).exists())
        self.assertEqual(set(self.trd_orders().values_list("id", flat=True)), self.fixture_ids - gone)
        self.assertFalse(gone & self.shown_fixture())

    def test_bulk_delete_of_one_order_says_order(self):
        self.open(IPOFilter="All")
        self.select_rows("pr_buy")
        self.page.locator("#bulk-delete-btn").click()
        expect(self.page.locator("#bulkDeleteModal #selected-count")).to_have_text("1")
        expect(self.page.locator("#bulkDeleteModal #order-suffix")).to_have_text("order")

    @unittest.expectedFailure
    def test_bulk_delete_resets_the_tally_of_the_groups_latest_order_like_a_single_delete(self):
        """KNOWN BUG: the Trades page posts the bulk delete to /0/BulkDeleteOrders/, so the tally reset is skipped."""
        older = self.o["k_buy"]
        newer = self.seed("main", ONE, "BUY", "Kostak", "RETAIL", 2, 460, "2026-02-12", "15:00:00")
        Order.objects.filter(id__in=[older.id, newer.id]).update(Telly="True")
        self.fixture_ids.add(newer.id)
        self.open(IPOFilter="All")
        self.page.locator(f'.order-checkbox[value="{newer.id}"]').check()
        self.page.locator("#bulk-delete-btn").click()
        with self.page.expect_navigation():
            self.page.locator("#confirm-bulk-delete").click()
        settle(self.page)
        older.refresh_from_db()
        self.assertFalse(Order.objects.filter(id=newer.id).exists())
        self.assertEqual(str(older.Telly), "False")

    # ====================================================================== 9. bulk order (CSV)
    def write_csv(self, folder, name, rows, header=SAMPLE_HEADER):
        path = os.path.join(folder, name)
        with open(path, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def upload(self, path):
        self.page.locator("#bulk-order-btn").click()
        modal = self.page.locator("#exampleuploadModal")
        expect(modal).to_be_visible()
        modal.locator('input[type="file"]').set_input_files(path)
        with self.page.expect_navigation():
            modal.get_by_role("button", name=re.compile("Upload")).click()
        settle(self.page)

    def test_the_bulk_order_modal_offers_a_sample_with_an_ipo_column(self):
        self.open()
        self.page.locator("#bulk-order-btn").click()
        modal = self.page.locator("#exampleuploadModal")
        expect(modal).to_be_visible()
        expect(modal.locator('a[href="/trades/Sample-Order"]')).to_be_visible()
        sample = self.page.request.get(f"{self.live_server_url}/trades/Sample-Order")
        self.assertEqual(sample.status, 200)
        self.assertIn("text/csv", sample.headers["content-type"])
        self.assertIn("Trades-Bulk-Order-Sample.csv", sample.headers["content-disposition"])
        self.assertEqual(sample.text().strip().split(","), SAMPLE_HEADER)
        # no file -> the browser stops the submit
        url = self.page.url
        modal.get_by_role("button", name=re.compile("Upload")).click()
        self.page.wait_for_timeout(400)
        self.assertEqual(self.page.url, url)
        self.assertTrue(modal.locator('input[type="file"]').evaluate("el => el.validity.valueMissing"))

    def test_a_csv_adds_orders_to_several_ipos_and_reports_the_rows_it_refused(self):
        before = self.trd_orders().count()
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_csv(tmp, "trades.csv", [
                [MAIN_IPO, ONE, "BUY", "Kostak", "RETAIL", 3, 771, "", "2026-02-12", "12:00:00", "Up via trades"],
                [SME_IPO, TWO, "sell", "kostak", "retail", 2, 772, "", "12/02/2026", "12:30", ""],
                [MAIN_IPO, THREE, "BUY", "CALL", "OPTIONS", 50, 5, "130", "2026-02-12", "13:00:00", ""],
                ["NO SUCH IPO", ONE, "BUY", "Kostak", "RETAIL", 1, 100, "", "2026-02-12", "14:00:00", ""],
                [MAIN_IPO, "NO SUCH GROUP", "BUY", "Kostak", "RETAIL", 1, 100, "", "2026-02-12", "14:00:00", ""],
                [MAIN_IPO, ONE, "BUY", "Kostak", "RETAIL", 0, 100, "", "2026-02-12", "14:00:00", ""],
                [MAIN_IPO, ONE, "HOLD", "Kostak", "RETAIL", 1, 100, "", "2026-02-12", "14:00:00", ""],
            ])
            self.open()
            self.upload(path)
        banner = self.banner()
        self.assertIn("Successfully added 3 orders", banner)
        self.assertIn("4 rows failed to upload", banner)
        for reason in ("IPO 'NO SUCH IPO' not found in your account", "Group 'NO SUCH GROUP' does not exist",
                       "Quantity must be greater than zero", "Invalid Order Type 'HOLD'"):
            self.assertIn(reason, banner)
        self.assertRegex(self.page.url, r"/trades$")
        self.assertEqual(self.trd_orders().count(), before + 3)
        new = {int(o.Rate): o for o in self.trd_orders().filter(Rate__in=[771, 772, 5])}
        a, b, c = new[771], new[772], new[5]
        self.assertEqual((a.OrderIPOName_id, a.OrderGroup.GroupName, a.OrderType, a.OrderCategory, a.InvestorType, int(a.Quantity),
                          str(a.OrderDate), str(a.OrderTime), format_remark(a.remark)),
                         (self.ipos["main"].id, ONE, "BUY", "Kostak", "RETAIL", 3, "2026-02-12", "12:00:00", "Up via trades"))
        self.assertEqual((b.OrderIPOName_id, b.OrderGroup.GroupName, b.OrderType, b.OrderCategory, int(b.Quantity), str(b.OrderDate), str(b.OrderTime)),
                         (self.ipos["sme"].id, TWO, "SELL", "Kostak", 2, "2026-02-12", "12:30:00"))
        self.assertEqual((c.OrderCategory, c.InvestorType, str(c.Method), int(c.Quantity)), ("CALL", "OPTIONS", "130", 50))
        self.assertEqual((OrderDetail.objects.filter(Order=a).count(), OrderDetail.objects.filter(Order=b).count(),
                          OrderDetail.objects.filter(Order=c).count()), (3, 2, 0))
        # ... and the new orders are on the page for their date
        self.open(IPOFilter="All")
        self.assertTrue({a.id, b.id, c.id} <= set(self.shown_ids()))

    def test_a_file_that_is_not_a_csv_or_has_no_rows_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = os.path.join(tmp, "orders.txt")
            with open(text, "w") as handle:
                handle.write("not,a,csv\n")
            self.open()
            self.upload(text)
            self.assertIn("THIS IS NOT A CSV FILE", self.banner())
            empty = self.write_csv(tmp, "empty.csv", [])
            self.open()
            self.upload(empty)
            self.assertIn("No data rows were found", self.banner())
        self.assertEqual(self.trd_orders().count(), len(SPECS))

    # ====================================================================== 10. status modal
    def status(self, ipo_name):
        return self.page.evaluate(STATUS_JS, ipo_name)

    def open_status(self):
        self.page.get_by_role("button", name="Status", exact=True).click()
        expect(self.page.locator("#exampleModal")).to_be_visible()

    def test_the_status_modal_summarises_the_listed_orders_per_ipo(self):
        self.open()
        self.open_status()
        main = self.status(MAIN_IPO)
        # Kostak: columns after the BUY / SELL / NET label are Retail, SHNI, BHNI x (count, avg, amount)
        kostak = {r[0]: r[1:] for r in main["kostak-table"]["rows"] if r and r[0] in ("BUY", "SELL", "NET")}
        self.assertEqual(kostak["BUY"], ["10", money(450), money(4500), "0", "0.00", "0.00", "0", "0.00", "0.00"])
        self.assertEqual(kostak["SELL"], ["0", "0.00", "0.00", "5", money(600), money(3000), "0", "0.00", "0.00"])
        self.assertEqual([kostak["NET"][0], kostak["NET"][3]], ["10", "-5"])
        # Subject To: a plain one, and a "Premium" method one whose cost is lot size x rate x quantity
        subject = {r[0]: r[1:] for r in main["subjectto-table"]["rows"] if r and r[0] in ("BUY", "SELL", "NET")}
        self.assertEqual(subject["BUY"][:3], ["8", money(1200), money(9600)])
        premium_cost = LOT["BHNI"] * 5 * 4
        self.assertEqual(subject["SELL"][6:9], ["4", money(premium_cost / 4), money(premium_cost)])
        # Premium orders
        prem = {r[0]: r[1:] for r in main["premium-table"]["rows"] if r and r[0] in ("BUY", "SELL", "NET")}
        self.assertEqual(float(prem["BUY"][0]), 100)                     # shown as "100.0" (no number format)
        self.assertEqual(prem["BUY"][1:3], [money(20), money(2000)])
        self.assertEqual(float(prem["SELL"][0]), 0)
        # Strike price table: one row per strike, CALL then PUT (total share, average, amount)
        strikes = {r[0]: r[1:] for r in main["strikeprice-table"]["rows"] if r and re.fullmatch(r"\d+", r[0])}
        self.assertEqual(set(strikes), {"120", "200"})
        self.assertEqual((float(strikes["120"][0]), strikes["120"][1]), (100, money(10)))
        self.assertEqual((float(strikes["200"][3]), strikes["200"][4]), (-100, money(12)))   # net shares: SELL is negative
        # The SME IPO has its own block, with one Retail column per figure
        sme = self.status(SME_IPO)
        sme_kostak = {r[0]: r[1:] for r in sme["kostak-table"]["rows"] if r and r[0] in ("BUY", "SELL", "NET")}
        self.assertEqual(sme_kostak["BUY"], ["6", money(300), money(1800)])
        self.assertEqual(sme_kostak["SELL"], ["2", money(310), money(620)])
        self.assertEqual(sme_kostak["NET"][0], "4")
        self.assertEqual(self.js_errors, [])

    def test_the_status_modal_follows_the_filters_and_hides_empty_tables(self):
        self.open(Groupfilter=ONE)
        self.open_status()
        main = self.status(MAIN_IPO)
        kostak = {r[0]: r[1:] for r in main["kostak-table"]["rows"] if r and r[0] in ("BUY", "SELL")}
        self.assertEqual(kostak["BUY"][:3], ["10", money(450), money(4500)])
        subject = {r[0]: r[1:] for r in main["subjectto-table"]["rows"] if r and r[0] in ("BUY", "SELL")}
        self.assertEqual(subject["BUY"][:3], ["0", "0.00", "0.00"], "TRD TWO's Subject To orders are filtered out")
        sme = self.status(SME_IPO)
        self.assertEqual({r[0]: r[1] for r in sme["kostak-table"]["rows"] if r and r[0] in ("BUY", "SELL")}, {"BUY": "6", "SELL": "0"})
        # "Hide Empty Tables" (on by default) hides tables without any figure, the switch shows them again
        self.assertTrue(main["kostak-table"]["shown"])
        self.assertFalse(main["subjectto-table"]["shown"])
        self.assertFalse(main["premium-table"]["shown"])
        self.assertFalse(sme["subjectto-table"]["shown"])
        self.page.locator("#hideEmptyTablesToggle").uncheck()
        main = self.status(MAIN_IPO)
        self.assertTrue(main["subjectto-table"]["shown"])
        self.assertTrue(main["premium-table"]["shown"])
        self.page.locator("#exampleModal .modal-footer").get_by_role("button", name="Close").click()
        expect(self.page.locator("#exampleModal")).to_be_hidden()

    def test_the_status_modal_has_nothing_to_show_for_an_empty_range(self):
        self.open(StartDate="2026-03-01", EndDate="2026-03-02")
        self.open_status()
        expect(self.page.locator("#exampleModal")).to_contain_text("No trades found to summarize.")

    # ====================================================================== 11. downloads
    def do_export(self, kind, folder, rows):
        self.page.get_by_role("button", name="Download").click()
        self.page.locator(".dt-button-collection .dt-button", has_text=kind).click()
        popup = self.page.locator(".swal2-popup")
        expect(popup).to_be_visible()
        expect(popup.locator(".swal2-confirm")).to_contain_text(f"Download {rows} Rows")
        with self.page.expect_download() as info:
            popup.locator(".swal2-confirm").click()
        download = info.value
        path = os.path.join(folder, download.suggested_filename)
        download.save_as(path)
        return path

    def test_the_excel_download_matches_the_listed_orders(self):
        scenarios = [("whole range", {}, list(self.db_window())),
                     ("one group", {"Groupfilter": TWO}, list(self.db_window().filter(OrderGroup__GroupName=TWO))),
                     ("searched", {"SearchQuery": "OPTIONS"}, list(self.db_window().filter(InvestorType="OPTIONS")))]
        with tempfile.TemporaryDirectory() as tmp:
            for label, params, want in scenarios:
                with self.subTest(scenario=label):
                    self.open(**params)
                    path = self.do_export("Excel", tmp, len(want))
                    self.assertTrue(path.endswith(".xlsx"), path)
                    rows = list(openpyxl.load_workbook(path).active.iter_rows(values_only=True))
                    head = next(i for i, r in enumerate(rows) if r and "IPO Name" in r)
                    cols = {name: i for i, name in enumerate(rows[head]) if name}
                    for name in ("IPO Name", "Group Name", "Order Type", "Order Category", "Investor Type", "Qty", "Rate", "Remark"):
                        self.assertIn(name, cols)
                    self.assertNotIn("Action", cols)
                    data = [r for r in rows[head + 1:] if any(c is not None for c in r)]
                    got = Counter((r[cols["IPO Name"]], r[cols["Group Name"]], r[cols["Order Type"]], r[cols["Order Category"]],
                                   r[cols["Investor Type"]], int(r[cols["Qty"]]), float(r[cols["Rate"]]), (r[cols["Remark"]] or "-"))
                                  for r in data)
                    exp = Counter((o.OrderIPOName.IPOName, o.OrderGroup.GroupName, o.OrderType, o.OrderCategory, o.InvestorType,
                                   int(o.Quantity), float(o.Rate), format_remark(o.remark) or "-") for o in want)
                    self.assertEqual(got, exp)

    def test_the_pdf_download_lists_the_orders_and_cancel_downloads_nothing(self):
        if not shutil.which("pdftotext"):
            self.skipTest("pdftotext not installed - cannot read the PDF")
        self.open(Groupfilter=TWO)
        downloads = []
        self.page.on("download", lambda d: downloads.append(d))
        self.page.get_by_role("button", name="Download").click()
        self.page.locator(".dt-button-collection .dt-button", has_text="PDF").click()
        self.page.locator(".swal2-popup .swal2-cancel").click()
        self.page.wait_for_timeout(800)
        self.assertEqual(downloads, [])
        want = list(self.db_window().filter(OrderGroup__GroupName=TWO))
        with tempfile.TemporaryDirectory() as tmp:
            path = self.do_export("PDF", tmp, len(want))
            text = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout
        for heading in ("IPO Name", "Group Name", "Order Type", "Investor Type", "Qty", "Rate"):
            self.assertIn(heading, text)
        self.assertEqual(text.count(TWO), len(want))
        self.assertNotIn(THREE, text)
