"""
Orders page E2E (/<IPOid>/Order, templates/Order.html).

Runs last in the pipeline, on the IPO / groups / broker left behind by the BUY
and SELL tests. Nothing here deletes orders. The only data change is the bulk
CSV upload test, which ADDS two orders (one BUY, one SELL).

Every assertion about row contents is computed from the database at run time
(not hard-coded), so the file stays correct if the BUY/SELL tests change or the
bulk-upload test has already added rows.
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

import openpyxl

from playwright.sync_api import expect

from home.models import GroupDetail, Order, OrderDetail
from home.views import format_remark
from test_cases.base import IPO_NAME, PersistentLiveServerTestCase, pause_for_inspection, settle


class OrdersPagePlaywrightTestCase(PersistentLiveServerTestCase):
    PAGE_NAME = "orders"
    _ran_any = False

    # --------------------------------------------------------------------------
    # Setup / teardown
    # --------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):
        # Keep the window open on the Orders page for manual inspection. Done here
        # (not in a test) so it happens once, after whichever test runs last, and
        # while the live server is still up.
        cls.log_summary()
        if cls._ran_any:
            try:
                cls.page.goto(f"{cls.live_server_url}/{cls._ipo_id}/Order")
                cls.settle(page)
            except Exception:
                pass
            pause_for_inspection(cls.PAGE_NAME)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        orders = self.all_orders()
        if not orders.filter(OrderType="BUY").exists() or not orders.filter(OrderType="SELL").exists():
            self.skipTest("No BUY+SELL data yet - run `python run_tests.py` (all pages) "
                          "so BUY and SELL run first.")
        type(self)._ran_any = True
        type(self)._ipo_id = self.ipo.id
        self.js_errors = []
        self.page.on("pageerror", lambda e: self.js_errors.append(f"{e.message}\n{e.stack}"))
        self.page.on("console", self._on_console)

    def tearDown(self):
        self.page.remove_listener("console", self._on_console)
        super().tearDown()

    def _on_console(self, msg):
        # Ignore "Failed to load resource" noise (e.g. manifest/CDN 404s); real JS
        # exceptions arrive through "pageerror".
        if msg.type == "error" and not msg.text.startswith("Failed to load resource"):
            self.js_errors.append(msg.text)

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    @property
    def orders_url(self):
        return f"{self.live_server_url}/{self.ipo.id}/Order"

    def open_orders(self):
        self.page.goto(self.orders_url)
        settle(self.page)
        expect(self.page.locator("#example")).to_be_visible()

    def table_cells(self):
        """Text of every cell of every body row currently in the Orders table."""
        return self.page.evaluate("""() => [...document.querySelectorAll('#example tbody tr')]
            .map(tr => [...tr.querySelectorAll('td')].map(td => td.textContent.trim()))""")

    def reveal_remark_column(self):
        """The Remark column is hidden by default; show it through the 'Columns' button."""
        rows = self.table_cells()
        if rows and len(rows[0]) > 12:      # already visible (13 cols incl. Remark)
            return
        self.page.get_by_role("button", name="Columns").click()
        self.page.locator(".dt-button-collection").get_by_text("Remark", exact=True).first.click()
        self.page.keyboard.press("Escape")
        expect(self.page.locator(".dt-button-collection")).to_have_count(0)

    @staticmethod
    def db_row(o, with_remark=False):
        row = (o.OrderGroup.GroupName, o.OrderType, o.OrderCategory, o.InvestorType,
               int(o.Quantity), float(o.Rate))
        return row + (format_remark(o.remark) or "-",) if with_remark else row

    def db_signature(self, qs, with_remark=False):
        return Counter(self.db_row(o, with_remark) for o in qs.select_related("OrderGroup"))

    def table_signature(self, with_remark=False):
        # td: 0 sr, 1 group, 2 type, 3 category, 4 strike/method, 5 investor, 6 qty, 7 rate,
        #     8 date-time, 9 date, 10 time, [11 remark], last = Edit button
        sig = Counter()
        for r in self.table_cells():
            row = (r[1], r[2], r[3], r[5], int(float(r[6])), float(r[7]))
            sig[row + (r[-2],) if with_remark else row] += 1
        return sig

    def expect_showing(self, total):
        expect(self.page.get_by_text(f"Showing 1 to {total} of {total} Rows")).to_be_visible()

    def assert_table_shows(self, qs, msg=""):
        self.assertEqual(self.table_signature(), self.db_signature(qs), msg)
        if qs.count():
            self.expect_showing(qs.count())

    def choose(self, selector, **kw):
        """Pick a filter option; the select's onchange submits the form -> page reload."""
        with self.page.expect_navigation():
            self.page.select_option(selector, **kw)
        settle(self.page)


    # -- seeding (edit / delete tests get their OWN orders; BUY/SELL data is never touched)
    def seed_order(self, group="ALPHA TRADERS", order_type="BUY", category="Kostak",
                   investor="RETAIL", qty=3, rate=901.0, method=None, remark=None,
                   date=datetime.date(2026, 1, 10), time=datetime.time(9, 15, 30), details=True):
        order = Order.objects.create(
            user=self.user, OrderIPOName=self.ipo,
            OrderGroup=GroupDetail.objects.get(user=self.user, GroupName=group),
            OrderType=order_type, OrderCategory=category, InvestorType=investor,
            Quantity=qty, Rate=rate, Method=method, remark=remark,
            OrderDate=date, OrderTime=time)
        if details:
            OrderDetail.objects.bulk_create(
                [OrderDetail(user=self.user, Order=order, PreOpenPrice=self.ipo.PreOpenPrice)
                 for _ in range(int(qty))])
        return order

    def open_edit_from_list(self, order):
        """Open the Orders page and click the Edit button of one specific row."""
        self.open_orders()
        row = self.page.locator("#example tbody tr").filter(
            has=self.page.get_by_text(f"{order.Rate}", exact=True))
        expect(row).to_have_count(1)
        row.get_by_role("button", name="Edit").click()
        self.page.wait_for_url(re.compile(rf"/{self.ipo.id}/EditOrder/{order.id}/"))
        expect(self.page.locator("h3.card-title")).to_have_text("Edit Order")

    def submit_edit(self):
        """Press Submit on the edit form; expect the redirect back to the Orders list."""
        with self.page.expect_navigation():
            self.page.get_by_role("button", name="Submit").click()
        self.page.wait_for_url(re.compile(rf"/{self.ipo.id}/Order/"))
        settle(self.page)

    def open_delete_modal(self, modal):
        self.page.get_by_role("button", name="Delete", exact=True).first.click()
        expect(modal).to_have_class(re.compile(r"\bshow\b"))       # fade-in finished
        expect(modal).to_be_visible()

    def remark_chips(self):
        return self.page.locator("#tagsDisplay .tag").evaluate_all(
            "els => els.map(e => e.firstChild.textContent.trim())")

    def tolerant(self, actual, expected, msg=""):
        self.assertAlmostEqual(float(actual), float(expected), delta=max(0.011, abs(expected) * 1e-6), msg=msg)

    # -- Status-modal oracle: recomputed from raw orders, independent of the view code
    INVESTORS = ("RETAIL", "SHNI", "BHNI")

    def lot_size(self, investor):
        return {"RETAIL": self.ipo.LotSizeRetail, "SHNI": self.ipo.LotSizeSHNI,
                "BHNI": self.ipo.LotSizeBHNI}[investor] or 1

    def status_oracle(self, orders, category):
        """{investor: {BUY|SELL|NET: dict(count, avg, amount, avg_app, avg_prem)}} for one category."""
        out = {}
        for inv in self.INVESTORS:
            lot, side = self.lot_size(inv), {}
            for kind in ("BUY", "SELL"):
                os_ = [o for o in orders if o.OrderCategory == category
                       and o.InvestorType == inv and o.OrderType == kind]
                count = sum(o.Quantity for o in os_)
                amount = sum(
                    (lot if category == "Subject To" and o.Method == "Premium" else 1) * o.Quantity * o.Rate
                    for o in os_)
                avg = amount / count if count else 0
                side[kind] = dict(count=count, amount=amount, avg=avg, avg_app=avg,
                                  avg_prem=avg / lot if count else 0)
            net_c = side["BUY"]["count"] - side["SELL"]["count"]
            net_amt = side["BUY"]["amount"] - side["SELL"]["amount"]
            net_a = net_amt / net_c if net_c else 0
            if net_c == 0:
                net_amt = side["SELL"]["amount"] - side["BUY"]["amount"]
            side["NET"] = dict(count=net_c, amount=round(net_amt, 2), avg=round(net_a, 2),
                               avg_app=round(net_a, 2), avg_prem=round(net_a / lot, 2))
            out[inv] = side
        return out

    def read_status_table(self, table):
        """{BUY|SELL|NET: [{'v': data-status-value, 't': text}, ...9 cells]}."""
        return table.evaluate("""t => Object.fromEntries([...t.querySelectorAll('tbody tr')]
            .filter(tr => ['BUY','SELL','NET'].includes(tr.cells[0].textContent.trim()))
            .map(tr => [tr.cells[0].textContent.trim(),
                [...tr.cells].slice(1).map(td => ({v: td.dataset.statusValue ?? '', t: td.textContent.trim()}))]))""")

    def assert_status_matches(self, modal, orders, mode_label=""):
        """Compare the Kostak and Subject To tables in the modal with the oracle."""
        non_zero = 0
        for css, category in ((".kostak-table", "Kostak"), (".subjectto-table", "Subject To")):
            table = modal.locator(f"{css} table").first
            shown = self.read_status_table(table)
            expected = self.status_oracle(orders, category)
            for i, inv in enumerate(self.INVESTORS):
                for label in ("BUY", "SELL", "NET"):
                    cells = shown[label][i * 3: i * 3 + 3]       # count, avg, amount
                    want = expected[inv][label]
                    where = f"{category} {inv} {label} {mode_label}"
                    non_zero += bool(want["count"]) + bool(want["amount"])
                    self.tolerant(cells[0]["v"] or 0, want["count"], f"{where} count")
                    self.tolerant(cells[2]["v"] or 0, want["amount"], f"{where} amount")
                    avg_key = "avg" if category == "Kostak" else self._avg_key
                    self.tolerant(cells[1]["t"].replace(",", "") or 0, want[avg_key], f"{where} avg")
        self.assertGreater(non_zero, 10, "status check ran on (almost) empty data - nothing verified")

    # -- export helpers ------------------------------------------------------------
    EXPORT_HEADER = ["Sr No.", "Group Name", "Order Type", "Order Category", "Premium Strike Price",
                     "Investor Type", "Qty", "Rate", "Date", "Time", "Remark"]

    @staticmethod
    def export_row(o):
        method = "-" if o.OrderCategory == "Premium" else (o.Method or "Application")
        return (o.OrderGroup.GroupName, o.OrderType, o.OrderCategory, method, o.InvestorType,
                int(o.Quantity), float(o.Rate), o.OrderDate.strftime("%d-%m-%Y"),
                o.OrderTime.strftime("%H:%M:%S"), format_remark(o.remark) or "-")

    def export_signature(self, qs):
        return Counter(self.export_row(o) for o in qs.select_related("OrderGroup"))

    def start_export(self, kind):
        """Open Download -> Excel|PDF and return the confirm dialog."""
        self.page.get_by_role("button", name="Download").click()
        self.page.locator(".dt-button-collection .dt-button", has_text=kind).click()
        popup = self.page.locator(".swal2-popup")
        expect(popup).to_be_visible()
        return popup

    def do_export(self, kind, expected_rows):
        popup = self.start_export(kind)
        expect(popup.locator(".swal2-title")).to_have_text("Download Partial Data?")
        expect(popup).to_contain_text(f"export {expected_rows} rows out of {expected_rows} total rows")
        expect(popup.locator(".swal2-confirm")).to_contain_text(f"Download {expected_rows} Rows")
        with self.page.expect_download() as info:
            popup.locator(".swal2-confirm").click()
        download = info.value
        ext = "xlsx" if kind == "Excel" else "pdf"
        self.assertEqual(download.suggested_filename, f"{IPO_NAME}-Order.{ext}")
        path = os.path.join(self.tmpdir, f"{kind}_{len(os.listdir(self.tmpdir))}.{ext}")
        download.save_as(path)
        return path

    def assert_same_rows(self, got, want, label):
        if got != want:
            self.fail(f"{label}\n  only in file: {sorted((got - want).elements())}"
                      f"\n  only in DB:   {sorted((want - got).elements())}")

    def assert_rows(self, got, want, rows_shown, label):
        """Exact match, unless the table itself shows more rows than there are orders
        (the known search-duplicates bug): then compare distinct rows and the row count."""
        if sum(want.values()) == rows_shown:
            self.assert_same_rows(got, want, label)
        else:
            self.assertEqual(sum(got.values()), rows_shown, f"{label}: row count != table")
            self.assert_same_rows(Counter(set(got)), Counter(set(want)), label)

    def check_excel(self, path, qs, rows_shown):
        rows = list(openpyxl.load_workbook(path).active.iter_rows(values_only=True))
        idx = next(i for i, r in enumerate(rows) if r and r[1] == "Group Name")
        self.assertEqual(list(rows[idx]), self.EXPORT_HEADER)
        data = [r for r in rows[idx + 1:] if any(c is not None for c in r)]
        self.assertEqual([r[0] for r in data], list(range(1, len(data) + 1)), "Sr No. must run 1..N")
        def text(v):   # Excel stores a numeric strike price ("150") as a number
            return str(int(v)) if isinstance(v, (int, float)) and float(v).is_integer() else v

        got = Counter((r[1], r[2], r[3], text(r[4]), r[5], int(r[6]), float(r[7]), r[8], r[9], r[10] or "-")
                      for r in data)
        self.assert_rows(got, self.export_signature(qs), rows_shown,
                         "Excel rows differ from the orders in the DB")
        return len(data)

    def check_pdf(self, path, qs, rows_shown):
        if not shutil.which("pdftotext"):
            self.skipTest("pdftotext not installed - cannot read the PDF")
        text = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True,
                              text=True, check=True).stdout
        for heading in ("Sr", "Group Name", "Order", "Premium Strike", "Investor", "Qty", "Rate",
                        "Date", "Time", "Remark"):
            self.assertIn(heading, text)
        # Group names wrap onto two lines in the PDF, so match on the first word of the group.
        row_re = re.compile(
            r"^\s*(\d+)\s+(.+?)\s+(BUY|SELL)\s+(Kostak|Subject To|Premium|CALL|PUT)\s+(\S+)\s+"
            r"(RETAIL|SHNI|BHNI|PREMIUM|OPTIONS)\s+(\d+)\s+([\d.]+)\s+(\d\d-\d\d-\d{4})\s+(\d\d:\d\d:\d\d)")
        got, srs = Counter(), []
        for line in text.splitlines():
            m = row_re.match(line)
            if m:
                srs.append(int(m[1]))
                got[(m[2].split()[0], m[3], m[4], m[5], m[6], int(m[7]), float(m[8]), m[9], m[10])] += 1
        self.assertEqual(srs, list(range(1, len(srs) + 1)), "Sr No. must run 1..N")
        want = Counter((r[0].split()[0],) + r[1:9] for r in self.export_signature(qs).elements())
        self.assert_rows(got, want, rows_shown, "PDF rows differ from the orders in the DB")
        # every remark is printed in the PDF; -raw keeps each cell's wrapped lines together
        raw = subprocess.run(["pdftotext", "-raw", path, "-"], capture_output=True,
                             text=True, check=True).stdout
        flat = " ".join(raw.split())
        for o in qs:
            if o.remark:
                self.assertIn(" ".join(format_remark(o.remark).split()), flat)
        return len(srs)

    # --------------------------------------------------------------------------
    # 1. Page load & unified feed
    # --------------------------------------------------------------------------
    def test_orders_page_renders_buy_and_sell_orders(self):
        orders = self.all_orders()
        total = orders.count()
        self.open_orders()

        # Heading: IPO name + "Order"
        expect(self.page.locator("h3.iponame")).to_have_text(IPO_NAME)
        expect(self.page.locator("h3", has_text=re.compile(r"^Order$"))).to_be_visible()

        # Counter: "Showing 1 to X of X Rows" == real order count
        self.expect_showing(total)
        expect(self.page.locator("#example tbody tr")).to_have_count(total)

        self.log(f"{total} orders in the DB ({orders.filter(OrderType='BUY').count()} BUY, "
                 f"{orders.filter(OrderType='SELL').count()} SELL): comparing every table row with it")
        # Both BUY and SELL rows are in the one table
        cells = self.table_cells()
        self.assertEqual(sum(r[2] == "BUY" for r in cells), orders.filter(OrderType="BUY").count())
        self.assertEqual(sum(r[2] == "SELL" for r in cells), orders.filter(OrderType="SELL").count())
        self.assertGreater(sum(r[2] == "BUY" for r in cells), 0)
        self.assertGreater(sum(r[2] == "SELL" for r in cells), 0)

        # Group, category, investor, qty, rate AND remark of every row match the DB
        self.reveal_remark_column()
        self.assertEqual(self.table_signature(with_remark=True),
                         self.db_signature(orders, with_remark=True),
                         "Orders table differs from the BUY+SELL orders in the DB")
        shown = self.table_cells()
        self.assertTrue({"ALPHA TRADERS", "BETA INVESTORS"} <= {r[1] for r in shown})
        self.assertTrue({"Kostak", "Subject To"} <= {r[3] for r in shown})
        self.assertTrue({"RETAIL", "SHNI", "BHNI"} <= {r[5] for r in shown})
        remarks = {r[-2] for r in shown}
        self.assertIn("Urgent client confirmation", remarks)                         # custom text
        self.assertIn("Shareholder Application", remarks)                            # dropdown tag
        self.assertIn("Shareholder Application - Call before allotment", remarks)    # tag + text
        self.assertEqual(self.js_errors, [])

    # --------------------------------------------------------------------------
    # 2. Filter dropdowns
    # --------------------------------------------------------------------------
    def test_filter_dropdowns(self):
        orders = self.all_orders()
        self.open_orders()

        group, category, investor = "ALPHA TRADERS", "Kostak", "RETAIL"
        self.log(f"filtering: group={group} -> category={category} -> investor={investor} -> rate -> reset")

        self.choose("#Groupfilter", label=group)
        by_group = orders.filter(OrderGroup__GroupName=group)
        self.assertTrue({r[2] for r in self.table_cells()} >= {"BUY", "SELL"})
        self.assertEqual({r[1] for r in self.table_cells()}, {group})
        self.assert_table_shows(by_group, "group filter")

        self.choose("#OrderCategoryFilter", value=category)
        by_cat = by_group.filter(OrderCategory=category)
        self.assertEqual({r[3] for r in self.table_cells()}, {category})
        self.assert_table_shows(by_cat, "category filter")

        self.choose("#InvestorTypeFilter", value=investor)
        by_inv = by_cat.filter(InvestorType=investor)
        self.assertEqual({r[5] for r in self.table_cells()}, {investor})
        self.assert_table_shows(by_inv, "investor filter")

        # Rate filter: pick the rate of the first remaining order
        rate = float(by_inv.order_by("id").first().Rate)
        values = self.page.eval_on_selector_all(
            "#RateFilterValue option", "els => els.map(e => e.value)")
        value = next(v for v in values if v != "All" and float(v) == rate)
        self.choose("#RateFilterValue", value=value)
        by_rate = by_inv.filter(Rate=rate)
        self.assertEqual({float(r[7]) for r in self.table_cells()}, {rate})
        self.assert_table_shows(by_rate, "rate filter")

        # Reset every filter back to All -> everything reappears
        for selector in ("#RateFilterValue", "#InvestorTypeFilter",
                         "#OrderCategoryFilter", "#Groupfilter"):
            self.choose(selector, value="All")
        self.assert_table_shows(orders, "after reset")
        self.assertEqual(self.js_errors, [])

    # --------------------------------------------------------------------------
    # 3. Search with debounce
    # --------------------------------------------------------------------------
    def test_search_input_filtering(self):
        orders = self.all_orders()
        total = orders.count()
        self.open_orders()
        search = lambda: self.page.locator('input[type="search"]')

        # Remark text: matches both the BUY and the SELL order carrying it
        term = "Urgent client confirmation"
        self.log(f"searching '{term}' (waits for the 500 ms debounce), then clearing, then '480'")
        with self.page.expect_navigation():           # fires ~500ms after typing stops
            search().fill(term)
        settle(self.page)
        matching = [o for o in orders if o.remark and term in (o.remark.get("text") or "")]
        self.assertEqual({o.OrderType for o in matching}, {"BUY", "SELL"})
        self.assertEqual(self.table_signature(),
                         Counter(self.db_row(o) for o in matching))
        expect(search()).to_have_value(term)

        # Clear -> table resets to every order
        with self.page.expect_navigation():
            search().fill("")
        settle(self.page)
        self.assert_table_shows(orders, "after clearing search")
        self.assertEqual(self.table_signature(), self.db_signature(orders))

        # Rate: "480" narrows the list and includes the BUY order placed at 480
        with self.page.expect_navigation():
            search().fill("480")
        settle(self.page)
        rows = self.table_cells()
        self.assertIn(480.0, {float(r[7]) for r in rows})
        self.assertLess(len(rows), total)
        # the page re-fills the box with the last search shortly after loading; wait for that, as a user
        # would, otherwise clearing an (already empty) box fires no event and nothing reloads
        expect(search()).to_have_value("480")
        with self.page.expect_navigation():
            search().fill("")
        settle(self.page)
        expect(self.page.locator("#example tbody tr")).to_have_count(total)
        self.assertEqual(self.js_errors, [])

    def test_search_returns_each_order_once(self):
        """Asserts each order is listed once in search results, even when an order has multiple
        OrderDetail items or matches across joined fields."""
        orders = self.all_orders()
        term = "Shareholder Application"
        matching = [o for o in orders if term in format_remark(o.remark)]
        self.assertTrue(any(o.Quantity > 1 for o in matching), "needs a multi-quantity match")
        self.open_orders()
        with self.page.expect_navigation():
            self.page.locator('input[type="search"]').fill(term)
        settle(self.page)
        self.assertEqual(self.table_signature(), Counter(self.db_row(o) for o in matching))

    # --------------------------------------------------------------------------
    # 4. Status modal
    # --------------------------------------------------------------------------
    def test_status_modal_calculations_and_controls(self):
        orders = self.all_orders()
        self.open_orders()
        modal = self.page.locator("#exampleModal")
        self.page.evaluate("localStorage.setItem('subjectToAvgMode', 'application')")

        self.page.get_by_role("button", name="Status", exact=True).click()
        expect(modal).to_be_visible()
        expect(modal.locator("#ipoStatusModalLabel")).to_have_text(f"{IPO_NAME} IPO Status - All")

        kostak = modal.locator(".kostak-table")
        subject_to = modal.locator(".subjectto-table")
        expect(kostak.first).to_be_visible()
        expect(subject_to.first).to_be_visible()
        for table in (kostak.first, subject_to.first):
            for label in ("BUY", "SELL", "NET"):
                expect(table.locator("tbody th", has_text=re.compile(rf"^{label}$"))).to_have_count(1)

        # Every count / average / amount of BUY, SELL and NET, for Kostak and Subject To
        # and all three investor tiers, recomputed from the real orders in the DB.
        self.log("recomputing every Kostak / Subject To count, average and amount from the raw orders")
        select = modal.locator("#subjectToAvgSelect")
        cells = modal.locator(".subjectto-avg-cell")
        read = lambda: cells.evaluate_all("els => els.map(e => e.textContent.trim())")
        attr = lambda name: cells.evaluate_all(f"els => els.map(e => e.dataset.{name})")

        select.select_option("application")
        self._avg_key = "avg_app"
        self.assert_status_matches(modal, orders, "avg by application")
        self.assertEqual(read(), attr("avgApp"))
        by_application = read()

        select.select_option("premium")
        self._avg_key = "avg_prem"
        self.assert_status_matches(modal, orders, "avg by premium")
        self.assertEqual(read(), attr("avgPrem"))
        by_premium = read()
        self.assertNotEqual(by_application, by_premium, "Avg. by had no effect on any cell")
        select.select_option("application")
        self.assertEqual(read(), by_application)

        # Category checkbox hides / shows the Kostak table (inside the Filter dropdown)
        self.page.locator("#tableFilterDropdown").click()
        self.page.locator("#filterKostak").uncheck()
        expect(kostak.first).to_be_hidden()
        expect(subject_to.first).to_be_visible()
        self.page.locator("#filterKostak").check()
        expect(kostak.first).to_be_visible()
        self.page.locator("#tableFilterDropdown").click()   # close the Filter dropdown

        # Close with data-dismiss
        modal.locator('[data-dismiss="modal"]:visible').first.click()
        expect(modal).to_be_hidden()

        # With a group filter the modal reports THAT group's orders only
        group = "ALPHA TRADERS"
        self.log(f"re-checking the modal with the group filter set to {group}")
        self.choose("#Groupfilter", label=group)
        self.page.get_by_role("button", name="Status", exact=True).click()
        expect(modal).to_be_visible()
        expect(modal.locator("#ipoStatusModalLabel")).to_have_text(f"{IPO_NAME} IPO Status - {group}")
        in_group = list(orders.filter(OrderGroup__GroupName=group).select_related("OrderGroup"))
        self.page.evaluate("localStorage.setItem('subjectToAvgMode', 'application')")
        modal.locator("#subjectToAvgSelect").select_option("application")
        self._avg_key = "avg_app"
        self.assert_status_matches(modal, in_group, f"group {group}")
        modal.locator('[data-dismiss="modal"]:visible').first.click()
        expect(modal).to_be_hidden()
        self.assertEqual(self.js_errors, [])

    # --------------------------------------------------------------------------
    # 8. Edit order (every field) and Delete from the edit page
    #    These tests seed their own orders; the BUY / SELL data is never modified.
    # --------------------------------------------------------------------------
    def test_edit_order_every_field(self):
        """Group, type, category, investor, qty, rate (+premium tick), date/time and remark."""
        order = self.seed_order(
            group="ALPHA TRADERS", order_type="BUY", category="Kostak", investor="RETAIL",
            qty=3, rate=901.0, remark={"tags": ["First Day Bidding"], "text": "seed note"})
        total = self.all_orders().count()
        self.open_edit_from_list(order)
        page = self.page

        # The form is pre-filled with the saved order
        expect(page.locator("#Group")).to_have_value("ALPHA TRADERS")
        expect(page.locator('select[name="OrderType"]')).to_have_value("BUY")
        expect(page.locator("#id_order_category")).to_have_value("Kostak")
        expect(page.locator('select[name="InvestorType"]')).to_have_value("RETAIL")
        self.assertEqual(float(page.locator('input[name="Qty"]').input_value()), 3.0)
        expect(page.locator('input[name="Rate"]')).to_have_value("901.0")
        expect(page.locator("#datetime")).to_have_value("2026-01-10T09:15:30")
        self.assertEqual(self.remark_chips(), ["First Day Bidding"])
        expect(page.locator("#remarkInput")).to_have_value("seed note")
        expect(page.locator("#rate_normal_section")).to_be_visible()
        expect(page.locator("#rate_subject_to_section")).to_be_hidden()

        self.log(f"editing order #{order.pk}: changing group, type, category, tier, qty, rate, premium, date and remark")
        # Change EVERY field
        page.select_option("#Group", label="BETA INVESTORS")
        page.select_option('select[name="OrderType"]', "SELL")
        page.select_option("#id_order_category", "Subject To")        # swaps the rate input
        expect(page.locator("#rate_subject_to_section")).to_be_visible()
        expect(page.locator("#rate_normal_section")).to_be_hidden()
        page.select_option('select[name="InvestorType"]', "SHNI")
        page.fill('input[name="Qty"]', "5")                           # 3 -> 5 creates 2 OrderDetails
        page.fill('input[name="Sub_Rate"]', "912.5")
        page.check("#subjectToIsPremium", force=True)                 # premium tick mark
        page.fill("#datetime", "2026-01-11T10:20:30")
        page.locator("#tagsDisplay .tag-remove").first.click()        # drop the old tag ...
        page.click("#remarkDropdownBtn")
        page.click('.dropdown-item:has-text("Profit Sharing")')       # ... add a new one
        page.fill("#remarkInput", "edited note")
        self.assertEqual(self.remark_chips(), ["Profit Sharing"])
        self.submit_edit()

        # UI: back on the Orders list with the success message and the edited row
        expect(page.locator(".alert", has_text="Order Modified successfully")).to_be_visible()
        self.expect_showing(total)
        # DB: every field changed, OrderDetails grew to the new quantity
        order.refresh_from_db()
        self.assertEqual(order.OrderGroup.GroupName, "BETA INVESTORS")
        self.assertEqual(order.OrderType, "SELL")
        self.assertEqual(order.OrderCategory, "Subject To")
        self.assertEqual(order.InvestorType, "SHNI")
        self.assertEqual(int(order.Quantity), 5)
        self.assertEqual(float(order.Rate), 912.5)
        self.assertEqual(order.Method, "Premium")
        self.assertEqual((order.OrderDate, order.OrderTime),
                         (datetime.date(2026, 1, 11), datetime.time(10, 20, 30)))
        self.assertEqual(order.remark, {"tags": ["Profit Sharing"], "text": "edited note"})
        self.assertEqual(OrderDetail.objects.filter(Order=order).count(), 5)
        self.assertEqual(self.all_orders().count(), total)
        # ... and the Orders table shows it
        self.reveal_remark_column()
        row = [r for r in self.table_cells() if r[7] == "912.5"]
        self.assertEqual(len(row), 1)
        self.assertEqual((row[0][1], row[0][2], row[0][3], row[0][4], row[0][5], row[0][6]),
                         ("BETA INVESTORS", "SELL", "Subject To", "Premium", "SHNI", "5"))
        self.assertEqual(row[0][-2], "Profit Sharing - edited note")
        self.assertEqual(self.js_errors, [])

    def test_edit_order_plain_rate_decrease_qty_and_clear_remark(self):
        """Kostak keeps the plain Rate input; qty 4 -> 2 removes blank OrderDetails; remark cleared."""
        order = self.seed_order(
            group="BETA INVESTORS", order_type="SELL", category="Kostak", investor="SHNI",
            qty=4, rate=902.0, remark={"tags": ["Profit Sharing"], "text": "to be cleared"})
        self.open_edit_from_list(order)
        page = self.page

        page.select_option("#Group", label="ALPHA TRADERS")
        page.select_option('select[name="OrderType"]', "BUY")
        page.select_option('select[name="InvestorType"]', "BHNI")
        page.fill('input[name="Qty"]', "2")
        page.fill('input[name="Rate"]', "903.25")
        page.fill("#datetime", "2026-01-12T08:00:07")
        page.locator("#tagsDisplay .tag-remove").first.click()
        page.fill("#remarkInput", "")
        self.assertEqual(self.remark_chips(), [])
        self.submit_edit()

        expect(page.locator(".alert", has_text="Order Modified successfully")).to_be_visible()
        order.refresh_from_db()
        self.assertEqual((order.OrderGroup.GroupName, order.OrderType, order.OrderCategory,
                          order.InvestorType), ("ALPHA TRADERS", "BUY", "Kostak", "BHNI"))
        self.assertEqual((int(order.Quantity), float(order.Rate)), (2, 903.25))
        self.assertIsNone(order.Method)
        self.assertEqual((order.OrderDate, order.OrderTime),
                         (datetime.date(2026, 1, 12), datetime.time(8, 0, 7)))
        self.assertIsNone(order.remark)
        self.assertEqual(OrderDetail.objects.filter(Order=order).count(), 2)
        self.reveal_remark_column()
        row = [r for r in self.table_cells() if r[7] == "903.25"]
        self.assertEqual(len(row), 1)
        self.assertEqual(row[0][-2], "-")
        self.assertEqual(self.js_errors, [])

    def test_edit_order_options_strike_price(self):
        """CALL / PUT orders also expose the Strike Price field."""
        order = self.seed_order(
            group="ALPHA TRADERS", order_type="BUY", category="CALL", investor="OPTIONS",
            qty=6, rate=7.5, method="100", details=False)
        self.open_edit_from_list(order)
        page = self.page
        expect(page.locator("#strike_price_section")).to_be_visible()
        expect(page.locator("#strike_price_input")).to_have_value("100")

        page.select_option("#Group", label="BETA INVESTORS")
        page.select_option('select[name="OrderType"]', "SELL")
        page.select_option("#id_order_category", "PUT")
        page.fill("#strike_price_input", "150")
        page.fill('input[name="Qty"]', "8")
        page.fill('input[name="Rate"]', "9.25")
        page.fill("#datetime", "2026-01-13T11:11:11")
        page.click("#remarkDropdownBtn")
        page.click('.dropdown-item:has-text("First Day Bidding")')
        page.fill("#remarkInput", "options edit")
        self.submit_edit()

        expect(page.locator(".alert", has_text="Order Modified successfully")).to_be_visible()
        order.refresh_from_db()
        self.assertEqual((order.OrderGroup.GroupName, order.OrderType, order.OrderCategory,
                          order.InvestorType), ("BETA INVESTORS", "SELL", "PUT", "OPTIONS"))
        self.assertEqual(order.Method, "150")
        self.assertEqual((int(order.Quantity), float(order.Rate)), (8, 9.25))
        self.assertEqual((order.OrderDate, order.OrderTime),
                         (datetime.date(2026, 1, 13), datetime.time(11, 11, 11)))
        self.assertEqual(order.remark, {"tags": ["First Day Bidding"], "text": "options edit"})
        self.assertEqual(OrderDetail.objects.filter(Order=order).count(), 0)   # options have no PAN rows
        self.assertEqual(self.js_errors, [])

    def test_edit_order_unchanged_and_back_button(self):
        """Submitting without changes reports 'same values'; Back leaves the order alone."""
        order = self.seed_order(
            group="ALPHA TRADERS", order_type="BUY", category="Kostak", investor="RETAIL",
            qty=2, rate=904.0, remark={"text": "unchanged"})
        snapshot = (order.OrderGroup_id, order.OrderType, order.OrderCategory, order.InvestorType,
                    order.Quantity, order.Rate, order.OrderDate, order.OrderTime, order.remark)

        def current():
            o = Order.objects.get(pk=order.pk)
            return (o.OrderGroup_id, o.OrderType, o.OrderCategory, o.InvestorType,
                    o.Quantity, o.Rate, o.OrderDate, o.OrderTime, o.remark)

        self.open_edit_from_list(order)
        self.submit_edit()
        expect(self.page.locator(".alert", has_text="Order values are same")).to_be_visible()
        self.assertEqual(current(), snapshot)

        self.open_edit_from_list(order)
        self.page.fill('input[name="Qty"]', "9")               # edit, but leave via Back
        self.page.get_by_role("button", name="Back").click()
        self.page.wait_for_url(re.compile(rf"/{self.ipo.id}/Order/"))
        self.assertEqual(current(), snapshot)
        self.assertEqual(self.js_errors, [])

    def test_delete_order_from_edit_page(self):
        """Delete button -> confirmation modal -> Cancel keeps it -> Delete removes it (and only it)."""
        order = self.seed_order(group="ALPHA TRADERS", order_type="BUY", category="Kostak",
                                investor="RETAIL", qty=3, rate=905.0)
        order_id = order.pk
        others_before = self.db_signature(self.all_orders().exclude(pk=order_id))
        total_before = self.all_orders().count()
        self.assertEqual(OrderDetail.objects.filter(Order_id=order_id).count(), 3)
        self.open_edit_from_list(order)
        page = self.page
        modal = page.locator(f'[id="{order_id}"].modal')

        # Open the confirmation, then Cancel: nothing is deleted
        self.open_delete_modal(modal)
        expect(modal).to_contain_text("Are you sure you want to delete this order?")
        modal.get_by_role("button", name="Cancel").click()
        expect(modal).to_be_hidden()
        self.assertTrue(Order.objects.filter(pk=order_id).exists())
        # ... and so does the close (x) button
        self.open_delete_modal(modal)
        modal.locator('.close[data-dismiss="modal"]').click()
        expect(modal).to_be_hidden()
        self.assertTrue(Order.objects.filter(pk=order_id).exists())
        self.assertEqual(self.all_orders().count(), total_before)

        self.log(f"deleting order #{order_id} ({total_before} orders before): Cancel and x keep it, Delete removes it")
        # Confirm: the order and its OrderDetails are gone, every other order is untouched
        self.open_delete_modal(modal)
        with page.expect_navigation():
            modal.get_by_role("button", name="Delete").click()
        page.wait_for_url(re.compile(rf"/{self.ipo.id}/Order/"))
        settle(page)

        self.assertFalse(Order.objects.filter(pk=order_id).exists())
        self.assertEqual(OrderDetail.objects.filter(Order_id=order_id).count(), 0)
        self.assertEqual(self.all_orders().count(), total_before - 1)
        self.assertEqual(self.db_signature(self.all_orders()), others_before)
        self.expect_showing(total_before - 1)
        self.assertEqual(self.table_signature(), others_before)
        self.assertNotIn("905.0", [r[7] for r in self.table_cells()])
        self.assertEqual(self.js_errors, [])

    # --------------------------------------------------------------------------
    # 5. Bulk order modal & CSV upload (adds one BUY and one SELL order)
    # --------------------------------------------------------------------------
    def test_bulk_order_modal_and_sample_download(self):
        orders = self.all_orders()
        before = orders.count()
        details_before = OrderDetail.objects.filter(user=self.user).count()
        self.open_orders()
        modal = self.page.locator("#exampleuploadModal")

        self.page.locator("#bulk-order-btn").click()
        expect(modal).to_be_visible()

        # Sample download link points at a valid CSV
        link = modal.locator('a[href*="/Sample-Order"]')
        expect(link).to_have_attribute("href", f"/{self.ipo.id}/Sample-Order")
        sample = self.page.request.get(f"{self.live_server_url}/{self.ipo.id}/Sample-Order")
        self.assertEqual(sample.status, 200)
        self.assertIn("text/csv", sample.headers["content-type"])
        header = sample.text().strip().split(",")
        self.assertEqual(header, ["GroupName", "Ordertype", "OrderCategory", "InvestorType",
                                  "Quantity", "Rate", "StrikPrice", "OrderDate", "OrderTime", "Remark"])

        # File input + Upload button exist; submitting without a file is blocked
        file_input = modal.locator('input[name=" file"]')
        upload = modal.get_by_role("button", name=re.compile("Upload"))
        expect(file_input).to_be_visible()
        expect(upload).to_be_visible()
        url_before = self.page.url
        upload.click()
        self.page.wait_for_timeout(500)
        self.assertEqual(self.page.url, url_before, "form must not submit without a file")
        self.assertTrue(file_input.evaluate("el => el.validity.valueMissing"))
        self.assertEqual(orders.count(), before)

        # Closing and reopening the modal works
        modal.locator('.close[data-dismiss="modal"]').click()
        expect(modal).to_be_hidden()
        self.page.locator("#bulk-order-btn").click()
        expect(modal).to_be_visible()

        self.log("uploading a 2-row CSV (1 BUY + 1 SELL) -> expecting exactly 2 new orders")
        # Upload a valid CSV: one BUY and one SELL (rates unique to this test)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bulk_orders.csv")
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(header)
                w.writerow(["ALPHA TRADERS", "BUY", "Kostak", "RETAIL", 2, 777, "",
                            "2026-01-05", "10:00:00", "Uploaded via CSV buy"])
                w.writerow(["BETA INVESTORS", "SELL", "Kostak", "SHNI", 3, 778, "",
                            "2026-01-05", "10:05:00", "Uploaded via CSV sell"])
            file_input.set_input_files(path)
            with self.page.expect_navigation():
                upload.click()
        settle(self.page)

        # DB: exactly those two orders arrived, with their OrderDetails
        self.assertEqual(orders.count(), before + 2)
        buy = orders.get(Rate=777)
        sell = orders.get(Rate=778)
        self.assertEqual((buy.OrderType, buy.OrderGroup.GroupName, buy.InvestorType, int(buy.Quantity)),
                         ("BUY", "ALPHA TRADERS", "RETAIL", 2))
        self.assertEqual((sell.OrderType, sell.OrderGroup.GroupName, sell.InvestorType, int(sell.Quantity)),
                         ("SELL", "BETA INVESTORS", "SHNI", 3))
        self.assertEqual(format_remark(buy.remark), "Uploaded via CSV buy")
        self.assertEqual(OrderDetail.objects.filter(user=self.user).count(), details_before + 5)

        # UI: page reloaded on the Orders page and shows the new rows + new total
        self.assertRegex(self.page.url, rf"/{self.ipo.id}/Order")
        expect(self.page.get_by_text("Successfully added 2 orders")).to_be_visible()
        self.expect_showing(before + 2)
        self.assertEqual(self.table_signature(), self.db_signature(orders))
        self.assertEqual(self.js_errors, [])

    # --------------------------------------------------------------------------
    # 6. Export (Excel + PDF)
    # --------------------------------------------------------------------------
    def test_export_buttons_presence(self):
        self.open_orders()
        self.page.get_by_role("button", name="Download").click()
        menu = self.page.locator(".dt-button-collection")
        expect(menu).to_be_visible()
        expect(menu.locator(".dt-button", has_text="Excel")).to_be_visible()
        expect(menu.locator(".dt-button", has_text="PDF")).to_be_visible()
        self.page.keyboard.press("Escape")
        self.assertEqual(self.js_errors, [])

    def test_export_cancel_downloads_nothing(self):
        self.open_orders()
        downloads = []
        self.page.on("download", lambda d: downloads.append(d))
        for kind in ("Excel", "PDF"):
            popup = self.start_export(kind)
            popup.locator(".swal2-cancel").click()
            expect(self.page.locator(".swal2-popup")).to_have_count(0)
        self.page.wait_for_timeout(1000)
        self.assertEqual(downloads, [], "cancelling the dialog must not download a file")

    def test_export_excel_and_pdf_match_orders(self):
        """Excel and PDF contents are checked row by row against the DB under every condition."""
        orders = self.all_orders()
        group, category, investor = "ALPHA TRADERS", "Kostak", "RETAIL"
        term = "Shareholder Application"

        def nothing():
            pass

        def by_group():
            self.choose("#Groupfilter", label=group)

        def by_category_and_investor():
            self.choose("#OrderCategoryFilter", value=category)
            self.choose("#InvestorTypeFilter", value=investor)

        def by_group_category_investor():
            by_group()
            by_category_and_investor()

        def by_search():
            with self.page.expect_navigation():
                self.page.locator('input[type="search"]').fill(term)
            settle(self.page)

        def with_remark_column_shown():
            self.reveal_remark_column()

        # (label, apply filter, expected orders, search results may repeat orders - see
        #  test_search_returns_each_order_once)
        scenarios = [
            ("all orders (Remark column hidden)", nothing, orders, False),
            ("all orders (Remark column shown)", with_remark_column_shown, orders, False),
            (f"group = {group}", by_group, orders.filter(OrderGroup__GroupName=group), False),
            (f"category = {category}, investor = {investor}", by_category_and_investor,
             orders.filter(OrderCategory=category, InvestorType=investor), False),
            ("group + category + investor", by_group_category_investor,
             orders.filter(OrderGroup__GroupName=group, OrderCategory=category, InvestorType=investor), False),
            (f"search '{term}'", by_search,
             orders.filter(pk__in=[o.pk for o in orders if term in format_remark(o.remark)]), True),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            self.tmpdir = tmp
            for label, apply, qs, search_may_repeat in scenarios:
                self.log(f"exporting '{label}' -> {qs.count()} rows (Excel + PDF)", indent=2)
                self.assertGreater(qs.count(), 0, f"scenario '{label}' has no data to export")
                self.open_orders()
                self.page.evaluate("localStorage.clear()")
                self.open_orders()
                apply()
                self.page.wait_for_timeout(300)
                shown = len(self.table_cells())
                if search_may_repeat:
                    self.assertGreaterEqual(shown, qs.count(), f"rows shown for '{label}'")
                else:
                    self.assertEqual(shown, qs.count(), f"rows shown for '{label}'")
                with self.subTest(scenario=label, file="Excel"):
                    path = self.do_export("Excel", shown)
                    self.assertEqual(self.check_excel(path, qs, shown), shown)
                with self.subTest(scenario=label, file="PDF"):
                    path = self.do_export("PDF", shown)
                    self.assertEqual(self.check_pdf(path, qs, shown), shown)
        self.assertEqual(self.js_errors, [])


    # --------------------------------------------------------------------------
    # 7. Footer navigation
    # --------------------------------------------------------------------------
    def test_footer_navigation_links(self):
        self.open_orders()
        footer = self.page.locator(".footer")
        ipo = self.ipo.id

        def link(path):
            return footer.locator(f'a[href="/{ipo}/{path}"]')

        expect(link("BUY")).to_be_visible()
        expect(link("SELL")).to_be_visible()
        expect(link("OrderDetail/BUY")).to_be_visible()
        expect(link("OrderDetail/SELL")).to_be_visible()
        expect(link("Order")).to_have_class(re.compile(r"\bdisabled\b"))   # active page
        for path in ("BUY", "SELL", "OrderDetail/BUY", "OrderDetail/SELL"):
            expect(link(path)).not_to_have_class(re.compile(r"\bdisabled\b"))
        expect(link("OrderDetail/BUY")).to_contain_text("Buy Order")
        expect(link("OrderDetail/SELL")).to_contain_text("Sell Order")

        # The links actually work
        for path, marker in (("BUY", "BUY"), ("OrderDetail/SELL", None)):
            self.page.goto(f"{self.live_server_url}/{ipo}/{path}")
            settle(self.page)
            self.assertEqual(self.page.url, f"{self.live_server_url}/{ipo}/{path}")
            self.assertNotIn("Server Error", self.page.title())
        self.open_orders()
        self.assertEqual(self.js_errors, [])
