"""
Status / Group Wise Billing E2E (/<IPOid>/Status, templates/Status.html).

Runs on its OWN IPOs (STATUS TEST IPO - MAINBOARD, STATUS SME IPO, STATUS PAGER IPO) so the Tally
checkboxes it flips and the data it seeds never touch the other pages. Orders are seeded with known
allotments; the app's calculate() fills in the amounts; EVERY number the page shows is then compared
with an independent calculation from the raw orders (see test_cases/oracle.py for the formulas).

What the Mainboard table shows per group (one row per group that has orders in the IPO):
  Kostak and Subject To, for Retail / SHNI / BHNI:   Count    = BUY quantity - SELL quantity
                                                     Alloted  = BUY allotted applications - SELL allotted applications
                                                     Billing  = sum of the BUY and SELL amounts
  Premium shares / billing, Call amount, Put amount
  Total shares = net allotted Kostak + Subject To shares + net Premium shares      Total amount = every billing column
  "@ avg" next to the total shares = total amount / total shares - (pre-open price - IPO price)
Hover tooltips split every figure into BUY and SELL.
"""
import io
import json
import os
import re
import tempfile
import unittest
from collections import Counter, defaultdict
from unittest import mock

import openpyxl
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from playwright.sync_api import expect

from home.models import CurrentIpoName, GroupDetail, Order, OrderDetail
from home.views import calculate
from test_cases import oracle
from test_cases.base import PASSWORD, PersistentLiveServerTestCase, pause_for_inspection, settle

STATUS_IPO, SME_IPO, PAGER_IPO = "STATUS TEST IPO", "STATUS SME IPO", "STATUS PAGER IPO"
IPO_PRICE, PRE_OPEN = 100.0, 250.0
ALPHA, BETA, SIGMA, ZETA = "ALPHA TRADERS", "BETA INVESTORS", "SIGMA CAPITAL", "ZETA BUYERS"
TIERS = ("RETAIL", "SHNI", "BHNI")
CUSTOMER_USER = "playwright_customer"

# ALPHA is BUY heavy (positive total), BETA is SELL heavy (negative total), SIGMA has BHNI on both sides
# (and an application that is allotted 0), ZETA only has a Premium order (every other column is 0).
SPECS = [
    dict(group=ALPHA, type="BUY", cat="Kostak", inv="RETAIL", rate=450, alloted=[10, 10, 0, None]),
    dict(group=ALPHA, type="BUY", cat="Kostak", inv="SHNI", rate=600, alloted=[5]),
    dict(group=ALPHA, type="SELL", cat="Kostak", inv="RETAIL", rate=455, alloted=[10]),
    dict(group=ALPHA, type="BUY", cat="Subject To", inv="RETAIL", rate=1200, alloted=[10, 10]),
    dict(group=ALPHA, type="BUY", cat="Subject To", inv="RETAIL", rate=5, method="Premium", alloted=[20]),
    dict(group=ALPHA, type="BUY", cat="Premium", inv="PREMIUM", rate=20, qty=100),
    dict(group=BETA, type="SELL", cat="Kostak", inv="RETAIL", rate=460, alloted=[10, 10, 10]),
    dict(group=BETA, type="BUY", cat="Kostak", inv="RETAIL", rate=440, alloted=[10]),
    dict(group=BETA, type="SELL", cat="Kostak", inv="BHNI", rate=700, alloted=[4]),
    dict(group=BETA, type="SELL", cat="Subject To", inv="SHNI", rate=1210, alloted=[10]),
    dict(group=BETA, type="SELL", cat="Subject To", inv="BHNI", rate=6, method="Premium", alloted=[10]),
    dict(group=BETA, type="SELL", cat="Premium", inv="PREMIUM", rate=30, qty=50),
    dict(group=BETA, type="BUY", cat="CALL", inv="OPTIONS", rate=10, qty=100, method="120"),
    dict(group=BETA, type="SELL", cat="PUT", inv="OPTIONS", rate=10, qty=100, method="200"),
    dict(group=SIGMA, type="BUY", cat="Kostak", inv="BHNI", rate=710, alloted=[3, 0]),
    dict(group=SIGMA, type="SELL", cat="Kostak", inv="BHNI", rate=715, alloted=[3]),
    dict(group=SIGMA, type="BUY", cat="Subject To", inv="BHNI", rate=1100, alloted=[2]),
    dict(group=SIGMA, type="BUY", cat="Premium", inv="PREMIUM", rate=25, qty=10),
    dict(group=ZETA, type="BUY", cat="Premium", inv="PREMIUM", rate=40, qty=20),
]
SME_SPECS = [
    dict(group=ALPHA, type="BUY", cat="Kostak", inv="RETAIL", rate=300, alloted=[5, 6, None]),
    dict(group=ALPHA, type="SELL", cat="Kostak", inv="RETAIL", rate=310, alloted=[2]),
    dict(group=BETA, type="BUY", cat="Subject To", inv="RETAIL", rate=900, alloted=[4]),
    dict(group=BETA, type="BUY", cat="Premium", inv="PREMIUM", rate=10, qty=20),
]
FILLERS = [f"STATUS FILLER {i:02d}" for i in range(1, 56)]
PAGER_SPECS = [dict(group=name, type="BUY", cat="Premium", inv="PREMIUM", rate=10, qty=1) for name in FILLERS]


def whole(x):
    """The page shows amounts with '{:.0f}'."""
    return int(float(f"{x:.0f}"))


def avg_text(v):
    """The page's average formatting: 4 decimals, trailing zeros removed, blank for 0."""
    if v is None or float(v or 0) == 0:
        return ""
    return f"{float(v):.4f}".rstrip("0").rstrip(".")


def indian(n):
    """toLocaleString('en-IN') for an integer."""
    n = int(n)
    sign, digits = ("-" if n < 0 else ""), str(abs(n))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        digits = ",".join(parts) + "," + tail
    return sign + digits


class FakeTelegram:
    """Stands in for telethon's TelegramClient: records what would have been sent, contacts nobody."""
    sent = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def start(self):
        pass

    async def disconnect(self):
        pass

    async def get_entity(self, entity):
        return entity

    async def send_message(self, entity, message, parse_mode=None):
        FakeTelegram.sent.append({"kind": "message", "to": entity, "text": message})

    async def send_file(self, entity, file, caption=None, parse_mode=None):
        data = file.read() if hasattr(file, "read") else file
        FakeTelegram.sent.append({"kind": "file", "to": entity, "bytes": data, "caption": caption})


class StatusPlaywrightTestCase(PersistentLiveServerTestCase):
    PAGE_NAME = "status"
    _ran_any = False

    # ------------------------------------------------------------------ setup / teardown
    @classmethod
    def tearDownClass(cls):
        cls.log_summary()
        if cls._ran_any:
            try:
                cls.page.goto(f"{cls.live_server_url}/{cls._ipo_id}/Status")
                settle(cls.page)
            except Exception:
                pass
            pause_for_inspection(cls.PAGE_NAME)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        type(self)._ran_any = True
        self.js_errors = []
        self.page.on("pageerror", lambda e: self.js_errors.append(f"{e.message}\n{e.stack}"))
        self.page.on("console", self._on_console)
        base = dict(IPOPrice=IPO_PRICE, PreOpenPrice=PRE_OPEN, LotSizeRetail=100, LotSizeSHNI=1400,
                    LotSizeBHNI=7000, Active=True)
        make = lambda name, kind: CurrentIpoName.objects.get_or_create(
            user=self.user, IPOName=name, defaults=dict(base, IPOType=kind))[0]
        self.sipo, self.sme, self.pager = make(STATUS_IPO, "MAINBOARD"), make(SME_IPO, "SME"), make(PAGER_IPO, "MAINBOARD")
        type(self)._ipo_id = self.sipo.id
        for ipo, specs in ((self.sipo, SPECS), (self.sme, SME_SPECS), (self.pager, PAGER_SPECS)):
            oracle.seed_specs(self.user, ipo, specs, PRE_OPEN)
        self.reset_state()
        self.page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=self.live_server_url)
        FakeTelegram.sent = []

    def tearDown(self):
        self.page.remove_listener("console", self._on_console)
        try:
            self.page.evaluate("localStorage.removeItem('positions_show_avg')")
        except Exception:
            pass
        super().tearDown()

    def _on_console(self, msg):
        if msg.type == "error" and not msg.text.startswith("Failed to load resource"):
            self.js_errors.append(msg.text)

    def reset_state(self):
        """Canonical state: pre-open 250, nothing tallied, amounts recalculated by the app."""
        for ipo in (self.sipo, self.sme, self.pager):
            ipo.PreOpenPrice = PRE_OPEN
            ipo.save()
            OrderDetail.objects.filter(Order__OrderIPOName=ipo).update(PreOpenPrice=PRE_OPEN)
            Order.objects.filter(OrderIPOName=ipo).update(Telly="False", tally_timestamp=None)
            calculate(ipo.id, self.user)

    # -------------------------------------------------------- independent expectation
    def expected(self, ipo):
        """{group name: figures} recomputed from the raw orders with the formulas in test_cases/oracle.py."""
        pre, price = float(ipo.PreOpenPrice), float(ipo.IPOPrice)
        groups = defaultdict(lambda: {
            "cell": defaultdict(lambda: dict(cnt_b=0.0, cnt_s=0.0, al_b=0, al_s=0, bill_b=0.0, bill_s=0.0, sh_b=0.0, sh_s=0.0)),
            "prem": dict(q_b=0.0, q_s=0.0, a_b=0.0, a_s=0.0), "call_b": 0.0, "call_s": 0.0, "put_b": 0.0, "put_s": 0.0})
        for o in Order.objects.filter(user=self.user, OrderIPOName=ipo).select_related("OrderGroup"):
            g, side = groups[o.OrderGroup.GroupName], ("b" if o.OrderType == "BUY" else "s")
            if o.OrderCategory in ("Kostak", "Subject To"):
                g["cell"][(o.OrderCategory, o.InvestorType)][f"cnt_{side}"] += o.Quantity
            elif o.OrderCategory == "Premium":
                g["prem"][f"q_{side}"] += o.Quantity
                g["prem"][f"a_{side}"] += oracle.order_amount(o, ipo)
            elif o.OrderCategory in ("CALL", "PUT"):
                g[f"{o.OrderCategory.lower()}_{side}"] += oracle.order_amount(o, ipo)
        for od in OrderDetail.objects.filter(user=self.user, Order__OrderIPOName=ipo).select_related("Order__OrderGroup"):
            o = od.Order
            if o.OrderCategory not in ("Kostak", "Subject To"):
                continue
            c, side = groups[o.OrderGroup.GroupName]["cell"][(o.OrderCategory, o.InvestorType)], ("b" if o.OrderType == "BUY" else "s")
            c[f"bill_{side}"] += oracle.detail_amount(od, ipo)
            if od.AllotedQty not in (None, 0):
                c[f"al_{side}"] += 1
                c[f"sh_{side}"] += float(od.AllotedQty)
        for name, g in groups.items():
            cell = lambda cat, t: g["cell"][(cat, t)]
            g["k_shares"] = sum(cell("Kostak", t)["sh_b"] - cell("Kostak", t)["sh_s"] for t in TIERS)
            g["st_shares"] = sum(cell("Subject To", t)["sh_b"] - cell("Subject To", t)["sh_s"] for t in TIERS)
            g["k_bill"] = sum(cell("Kostak", t)["bill_b"] + cell("Kostak", t)["bill_s"] for t in TIERS)
            g["st_bill"] = sum(cell("Subject To", t)["bill_b"] + cell("Subject To", t)["bill_s"] for t in TIERS)
            g["p_shares"] = g["prem"]["q_b"] - g["prem"]["q_s"]
            g["p_bill"] = g["prem"]["a_b"] + g["prem"]["a_s"]
            g["call"], g["put"] = g["call_b"] + g["call_s"], g["put_b"] + g["put_s"]
            g["total_shares"] = g["k_shares"] + g["st_shares"] + g["p_shares"]
            g["total_amount"] = g["k_bill"] + g["st_bill"] + g["p_bill"] + g["call"] + g["put"]
            gain = pre - price
            g["k_avg"] = avg_text(g["k_bill"] / g["k_shares"] - gain) if g["k_shares"] else ""
            g["st_avg"] = avg_text(g["st_bill"] / g["st_shares"] - gain) if g["st_shares"] else ""
            g["p_avg"] = avg_text(g["p_bill"] / g["p_shares"] - gain) if g["p_shares"] else ""
            g["total_avg"] = avg_text(g["total_amount"] / g["total_shares"] - gain) if g["total_shares"] else ""
        return dict(groups)

    # ---------------------------------------------------------------------- page helpers
    def status_url(self, ipo=None, query=""):
        return f"{self.live_server_url}/{(ipo or self.sipo).id}/Status{query}"

    def open_status(self, ipo=None, query=""):
        self.page.goto(self.status_url(ipo, query))
        settle(self.page)
        if self.page.locator("#example").count() == 0:
            self.fail(f"no status table at {self.page.url}: {self.page.inner_text('body')[:300]!r}")
        expect(self.page.locator("#example")).to_be_visible()

    def rows(self):
        return self.page.evaluate("""() => [...document.querySelectorAll('#example tbody tr')].filter(tr => !tr.querySelector('.dataTables_empty')).map(tr => {
            const cells = [...tr.children];
            const title = c => c.getAttribute('title') || c.querySelector('[title]')?.getAttribute('title') || '';
            return {texts: cells.map(c => c.textContent.trim().replace(/\\s+/g, ' ')), titles: cells.map(title),
                    group: cells[1].textContent.trim(), checked: tr.querySelector('.group-checkbox')?.checked ?? null,
                    avg: tr.querySelector('.row-avg-disp')?.textContent.trim() ?? '',
                    shares: cells[cells.length - 2].childNodes[0].textContent.trim(),
                    tallyTime: tr.querySelector('.tally-time-div')?.innerText.replace(/\\s+/g, ' ').trim() ?? '',
                    shareBtn: Object.fromEntries([...(tr.querySelector('.copy-shares-btn')?.attributes ?? [])].map(a => [a.name, a.value])),
                    amountBtn: Object.fromEntries([...(tr.querySelector('.copy-amount-btn')?.attributes ?? [])].map(a => [a.name, a.value]))};
        })""")

    @staticmethod
    def col(cat, tier, metric):
        return 2 + (0 if cat == "Kostak" else 9) + TIERS.index(tier) * 3 + ("count", "alloted", "billing").index(metric)

    PREM_SHARES, PREM_BILL, CALL, PUT, TOTAL_SHARES, TOTAL_AMOUNT = 20, 21, 22, 23, 24, 25

    @staticmethod
    def num(text):
        """The leading number of a cell ('155 @ -38.6774' -> 155)."""
        return int(float(re.match(r"-?[\d,]+(?:\.\d+)?", text.strip()).group(0).replace(",", "")))

    def numbers(self, title):
        return [int(n) for n in re.findall(r"-?\d+", title)]

    def row_for(self, group):
        return next(r for r in self.rows() if r["group"] == group)

    def check_cells(self, ipo, wanted):
        """wanted(group_figures) -> {column index: expected whole number}; compared for every group row."""
        exp = self.expected(ipo)
        rows = self.rows()
        self.assertEqual(sorted(exp), [r["group"] for r in rows], "groups on the page")
        for r in rows:
            for column, value in wanted(exp[r["group"]]).items():
                self.assertEqual(self.num(r["texts"][column]), whole(value), f"{r['group']} column {column}")

    def tally_state(self, ipo=None):
        orders = Order.objects.filter(user=self.user, OrderIPOName=ipo or self.sipo).select_related("OrderGroup")
        state = defaultdict(list)
        for o in orders:
            state[o.OrderGroup.GroupName].append(o.Telly)
        return dict(state)

    def relogin(self):
        self.page.context.clear_cookies()
        self.page.context.add_cookies([{"name": "sessionid", "value": self.client.cookies["sessionid"].value,
                                        "domain": "localhost", "path": "/"}])

    def make_customer(self, group=ALPHA):
        user_model = get_user_model()
        customer, _ = user_model.objects.get_or_create(username=CUSTOMER_USER, defaults={"email": "c@example.com"})
        customer.set_password(PASSWORD)
        customer.Broker_id = str(self.user.id)
        customer.Group_id = str(GroupDetail.objects.get_or_create(user=self.user, GroupName=group)[0].id)
        customer.save()
        customer.groups.set([Group.objects.get_or_create(name="Customer")[0]])
        browser = Client()
        self.assertTrue(browser.login(username=CUSTOMER_USER, password=PASSWORD))
        self.page.context.clear_cookies()
        self.page.context.add_cookies([{"name": "sessionid", "value": browser.cookies["sessionid"].value,
                                        "domain": "localhost", "path": "/"}])

    # ======================================================================================
    # Section 1: calculations (every figure checked against the independent calculation)
    # ======================================================================================
    def test_groups_are_listed_alphabetically_and_only_when_they_have_orders(self):
        GroupDetail.objects.get_or_create(user=self.user, GroupName="NO ORDERS HERE")
        self.open_status()
        names = [r["group"] for r in self.rows()]
        self.log(f"groups on the page: {names}", indent=2)
        self.assertEqual(names, sorted(names))
        self.assertEqual(names, sorted({o.OrderGroup.GroupName for o in
                                        Order.objects.filter(user=self.user, OrderIPOName=self.sipo)
                                        .select_related("OrderGroup")}))
        self.assertNotIn("NO ORDERS HERE", names)
        self.assertEqual(self.js_errors, [])

    def test_kostak_columns_per_group_and_investor_tier(self):
        def wanted(g):
            out = {}
            for t in TIERS:
                c = g["cell"][("Kostak", t)]
                out[self.col("Kostak", t, "count")] = c["cnt_b"] - c["cnt_s"]
                out[self.col("Kostak", t, "alloted")] = c["al_b"] - c["al_s"]
                out[self.col("Kostak", t, "billing")] = c["bill_b"] + c["bill_s"]
            return out
        self.open_status()
        self.check_cells(self.sipo, wanted)
        exp = self.expected(self.sipo)
        # spot values worked out by hand: ALPHA Kostak Retail BUY 450 [10,10,0,None] and SELL 455 [10]
        # BUY: 1050 + 1050 + (0 -> -450) + (None -> 0) = 1650     SELL: -(1500 - 455) = -1045
        c = exp[ALPHA]["cell"][("Kostak", "RETAIL")]
        self.assertEqual((c["bill_b"], c["bill_s"], c["cnt_b"], c["cnt_s"], c["al_b"], c["al_s"]), (1650, -1045, 4, 1, 2, 1))
        row = self.row_for(ALPHA)
        self.assertEqual(self.num(row["texts"][self.col("Kostak", "RETAIL", "billing")]), 605)
        self.assertEqual(self.num(row["texts"][self.col("Kostak", "RETAIL", "count")]), 3)       # 4 - 1
        self.assertEqual(self.num(row["texts"][self.col("Kostak", "RETAIL", "alloted")]), 1)     # 2 - 1
        self.log("ALPHA Kostak Retail: count 3, alloted 1, billing 1650 - 1045 = 605", indent=2)

    def test_subject_to_columns_fixed_and_premium_method(self):
        def wanted(g):
            out = {}
            for t in TIERS:
                c = g["cell"][("Subject To", t)]
                out[self.col("Subject To", t, "count")] = c["cnt_b"] - c["cnt_s"]
                out[self.col("Subject To", t, "alloted")] = c["al_b"] - c["al_s"]
                out[self.col("Subject To", t, "billing")] = c["bill_b"] + c["bill_s"]
            return out
        self.open_status()
        self.check_cells(self.sipo, wanted)
        exp = self.expected(self.sipo)
        # fixed method:   (250 - 100) * 10 - 1200 = 300 per application (x2)
        # premium method: (250 - 100) * 20 - 5 * 20 = 2900            -> ALPHA Retail Subject To = 600 + 2900
        self.assertEqual(exp[ALPHA]["cell"][("Subject To", "RETAIL")]["bill_b"], 3500)
        self.assertEqual(self.num(self.row_for(ALPHA)["texts"][self.col("Subject To", "RETAIL", "billing")]), 3500)
        # SELL: fixed -(1500 - 1210) = -290 (SHNI) and premium -(1500 - 6*10) = -1440 (BHNI)
        self.assertEqual(self.num(self.row_for(BETA)["texts"][self.col("Subject To", "SHNI", "billing")]), -290)
        self.assertEqual(self.num(self.row_for(BETA)["texts"][self.col("Subject To", "BHNI", "billing")]), -1440)
        self.log("fixed 300 x2 + premium 2900 = 3500 (BUY); fixed -290, premium -1440 (SELL)", indent=2)

    def test_premium_call_and_put_columns(self):
        def wanted(g):
            return {self.PREM_SHARES: g["p_shares"], self.PREM_BILL: g["p_bill"], self.CALL: g["call"], self.PUT: g["put"]}
        self.open_status()
        self.check_cells(self.sipo, wanted)
        by = {g: self.row_for(g)["texts"] for g in (ALPHA, BETA, SIGMA, ZETA)}
        # ALPHA Premium BUY 100 @ 20: (250 - 120) * 100 = 13000     BETA Premium SELL 50 @ 30: -(250 - 130) * 50 = -6000
        self.assertEqual((self.num(by[ALPHA][self.PREM_SHARES]), self.num(by[ALPHA][self.PREM_BILL])), (100, 13000))
        self.assertEqual((self.num(by[BETA][self.PREM_SHARES]), self.num(by[BETA][self.PREM_BILL])), (-50, -6000))
        # BETA CALL BUY strike 120 @ 10 x100 = -1000 + 3000 = 2000     PUT SELL strike 200 = 1000 + (-5000) = -4000
        self.assertEqual((self.num(by[BETA][self.CALL]), self.num(by[BETA][self.PUT])), (2000, -4000))
        self.assertEqual((self.num(by[ZETA][self.PREM_SHARES]), self.num(by[ZETA][self.PREM_BILL])), (20, (250 - 140) * 20))
        self.log("Premium 13000 / -6000, Call 2000, Put -4000, ZETA premium only 2200", indent=2)

    def test_group_total_shares_and_net_settlement_amount(self):
        self.open_status()
        self.check_cells(self.sipo, lambda g: {self.TOTAL_SHARES: g["total_shares"], self.TOTAL_AMOUNT: g["total_amount"]})
        exp = self.expected(self.sipo)
        for group, sign in ((ALPHA, 1), (BETA, -1)):
            total = exp[group]["total_amount"]
            self.log(f"{group}: total amount {total:.0f} ({'BUY heavy -> positive' if sign > 0 else 'SELL heavy -> negative'})", indent=2)
            self.assertGreater(total * sign, 0)
            self.assertEqual(self.num(self.row_for(group)["texts"][self.TOTAL_AMOUNT]), whole(total))
        # ALPHA = Kostak 605+150... worked out by hand: 1650 + 150 - 1045 + 600 + 2900 + 13000
        self.assertEqual(exp[ALPHA]["total_amount"], 17255)
        self.assertEqual(self.num(self.row_for(ALPHA)["texts"][self.TOTAL_AMOUNT]), 17255)
        # BETA = -3120 + 100 + 1060 - 290 - 1440 - 6000 + 2000 - 4000
        self.assertEqual(exp[BETA]["total_amount"], -11690)
        self.assertEqual(self.num(self.row_for(BETA)["texts"][self.TOTAL_AMOUNT]), -11690)
        # shares: ALPHA 20 Kostak Retail - 10 SELL + 5 SHNI = 15; + 40 Subject To = 55; + 100 premium
        self.assertEqual(self.num(self.row_for(ALPHA)["texts"][self.TOTAL_SHARES]), 55 + 100)
        # every row's total is the sum of its own columns
        for r in self.rows():
            billing_columns = [self.col(c, t, "billing") for c in ("Kostak", "Subject To") for t in TIERS]
            parts = [self.num(r["texts"][i]) for i in billing_columns + [self.PREM_BILL, self.CALL, self.PUT]]
            self.assertAlmostEqual(self.num(r["texts"][self.TOTAL_AMOUNT]), sum(parts), delta=3, msg=r["group"])

    def test_average_rates_next_to_shares(self):
        """'@ avg' = total amount / total shares - (pre-open - IPO price); Kostak / Subject To / Premium in the tooltip."""
        self.open_status()
        exp = self.expected(self.sipo)
        for r in self.rows():
            g = exp[r["group"]]
            with self.subTest(group=r["group"]):
                self.assertEqual(r["avg"], g["total_avg"])
                self.assertEqual(r["shareBtn"].get("data-total-avg", ""), g["total_avg"])
                tip = r["titles"][self.TOTAL_SHARES]
                for label, shares, avg in (("Kostak", g["k_shares"], g["k_avg"]), ("Subject To", g["st_shares"], g["st_avg"]),
                                           ("Premium", g["p_shares"], g["p_avg"])):
                    m = re.search(rf"{label}:(-?\d+)(?: @ (\S+))?", tip)
                    self.assertIsNotNone(m, f"{label} missing in tooltip {tip!r}")
                    self.assertEqual(int(m.group(1)), whole(shares), f"{label} shares")
                    self.assertEqual(m.group(2) or "", avg, f"{label} average")
        self.log("total @ avg for " + ", ".join(f"{r['group'].split()[0]} {r['avg'] or '-'}" for r in self.rows()), indent=2)

    def test_tooltips_split_every_figure_into_buy_and_sell(self):
        self.open_status()
        exp = self.expected(self.sipo)
        for r in self.rows():
            g = exp[r["group"]]
            for cat in ("Kostak", "Subject To"):
                for tier in TIERS:
                    c = g["cell"][(cat, tier)]
                    with self.subTest(group=r["group"], category=cat, tier=tier):
                        count_tip = r["titles"][self.col(cat, tier, "count")]
                        if c["cnt_b"] - c["cnt_s"] != 0:                      # only linked (non-zero) counts carry a tooltip
                            self.assertEqual(self.numbers(count_tip), [whole(c["cnt_b"]), whole(c["cnt_s"])])
                        self.assertEqual(self.numbers(r["titles"][self.col(cat, tier, "alloted")]),
                                         [c["al_b"], c["al_s"], whole(c["sh_b"]), whole(c["sh_s"])])
                        if tier != "BHNI" or cat != "Kostak":                  # BHNI Kostak is checked by its own known-bug test
                            self.assertEqual(self.numbers(r["titles"][self.col(cat, tier, "billing")]),
                                             [whole(c["bill_b"]), whole(c["bill_s"])])
            self.assertEqual(self.numbers(r["titles"][self.CALL]), [whole(g["call_b"]), whole(g["call_s"])])
            self.assertEqual(self.numbers(r["titles"][self.PUT]), [whole(g["put_b"]), whole(g["put_s"])])

    @unittest.expectedFailure
    def test_kostak_bhni_billing_tooltip_shows_the_sell_amount(self):
        """KNOWN APP BUG: the Kostak BHNI Billing tooltip prints the BUY amount in both slots
        ('SELL: x' uses KostakBHNIBillingBuy). Asserts the CORRECT tooltip; 'unexpected success' once fixed."""
        self.open_status()
        g = self.expected(self.sipo)[SIGMA]["cell"][("Kostak", "BHNI")]
        self.assertNotEqual(g["bill_b"], g["bill_s"], "needs different BUY and SELL amounts")
        title = self.row_for(SIGMA)["titles"][self.col("Kostak", "BHNI", "billing")]
        self.assertEqual(self.numbers(title), [whole(g["bill_b"]), whole(g["bill_s"])])

    def test_sme_ipo_group_rows(self):
        """SME layout: Kostak and Subject To (count, alloted, billing), Premium (count, billing), totals."""
        self.open_status(self.sme)
        exp = self.expected(self.sme)
        rows = self.rows()
        self.assertEqual([r["group"] for r in rows], sorted(exp))
        for r in rows:
            g = exp[r["group"]]
            k = [g["cell"][("Kostak", t)] for t in TIERS]
            st = [g["cell"][("Subject To", t)] for t in TIERS]
            want = {2: sum(c["cnt_b"] - c["cnt_s"] for c in k), 3: sum(c["al_b"] - c["al_s"] for c in k), 4: g["k_bill"],
                    5: sum(c["cnt_b"] - c["cnt_s"] for c in st), 6: sum(c["al_b"] - c["al_s"] for c in st), 7: g["st_bill"],
                    8: g["p_shares"], 9: g["p_bill"], 10: g["total_shares"], 11: g["total_amount"]}
            for column, value in want.items():
                self.assertEqual(self.num(r["texts"][column] if column != 10 else r["shares"]), whole(value),
                                 f"{r['group']} column {column}")
            self.assertEqual(r["avg"], g["total_avg"])
        a = exp[ALPHA]
        self.assertEqual(a["k_bill"], (150 * 5 - 300) + (150 * 6 - 300) + 0 - (150 * 2 - 310))     # 450 + 600 - (-10)
        self.log(f"SME ALPHA Kostak billing {a['k_bill']:.0f} (BUY 1050 - SELL -10 = 1060)", indent=2)

    def test_only_a_broker_can_open_the_status_page(self):
        self.make_customer(ALPHA)
        try:
            response = self.page.goto(self.status_url())
            settle(self.page)
            body = self.page.inner_text("body")
            self.log(f"client user -> HTTP {response.status}: {body[:60]!r}", indent=2)
            self.assertEqual(self.page.locator("#example").count(), 0)
            self.assertIn("not authorized", body)
            for group in (ALPHA, BETA, SIGMA, ZETA):
                self.assertNotIn(group, body)
        finally:
            self.relogin()
        self.page.context.clear_cookies()
        try:
            self.page.goto(self.status_url())
            settle(self.page)
            self.assertIn("/login", self.page.url)
            self.assertEqual(self.page.locator("#example").count(), 0)
        finally:
            self.relogin()

    @unittest.expectedFailure
    def test_a_client_user_is_refused_with_an_http_error_status(self):
        """KNOWN GAP: a non-broker is shown 'You are not authorized to view this page' with HTTP 200, not 403."""
        self.make_customer(ALPHA)
        try:
            response = self.page.goto(self.status_url())
            self.assertIn(response.status, (301, 302, 401, 403))
        finally:
            self.relogin()

    def test_copy_buttons_carry_the_calculated_figures(self):
        """The buttons next to Total Shares / Total Amount hold the Kostak / Subject To / Premium split."""
        self.open_status()
        exp = self.expected(self.sipo)
        for r in self.rows():
            g = exp[r["group"]]
            with self.subTest(group=r["group"]):
                s, a = r["shareBtn"], r["amountBtn"]
                self.assertEqual(self.num(s["data-k-shares"]), whole(g["k_shares"]))
                self.assertEqual(self.num(s["data-st-shares"]), whole(g["st_shares"]))
                self.assertEqual(self.num(s["data-p-shares"]), whole(g["p_shares"]))
                self.assertEqual(self.num(s["data-total-shares"]), whole(g["total_shares"]))
                self.assertEqual(s.get("data-k-avg", ""), g["k_avg"])
                self.assertEqual(s.get("data-st-avg", ""), g["st_avg"])
                self.assertEqual(s.get("data-p-avg", ""), g["p_avg"])
                self.assertEqual(self.num(s["data-k-count"]), sum(g["cell"][("Kostak", t)]["al_b"] - g["cell"][("Kostak", t)]["al_s"] for t in TIERS))
                self.assertEqual(self.num(a["data-k-amount"]), whole(g["k_bill"]))
                self.assertEqual(self.num(a["data-st-amount"]), whole(g["st_bill"]))
                self.assertEqual(self.num(a["data-p-amount"]), whole(g["p_bill"]))
                self.assertEqual(self.num(a["data-total-amount"]), whole(g["total_amount"]))

    def test_copy_buttons_put_the_right_text_on_the_clipboard(self):
        self.open_status()
        exp = self.expected(self.sipo)
        title_ipo = self.page.title().split("-")[0].strip()
        for group in (ALPHA, BETA):
            g = exp[group]
            row = self.page.locator("#example tbody tr").filter(has=self.page.get_by_text(group, exact=True)).first
            # -- amount breakdown: each component with Cr / Dr, then the total
            row.locator(".copy-amount-btn").click()
            self.page.wait_for_timeout(300)
            text = self.page.evaluate("navigator.clipboard.readText()")
            cr_dr = lambda v: f"{indian(abs(whole(v)))} {'Cr' if whole(v) >= 0 else 'Dr'}"
            items = [("Kostak", g["k_bill"]), ("Subject to", g["st_bill"]), ("Premium", g["p_bill"])]
            items = [(label, v) for label, v in items if whole(v) != 0]
            width = max(len(cr_dr(v)) for _l, v in items + [("Total Amount", g["total_amount"])])
            lines = [label.ljust(13) + cr_dr(v).rjust(width) for label, v in items]
            lines.append("Total Amount".ljust(13) + cr_dr(g["total_amount"]).rjust(width))
            self.assertIn("\n".join(lines), text, f"{group} amount copy")
            self.assertTrue(text.startswith(f"{title_ipo} - {group}"), text[:60])
            self.log(f"{group}: amount copy -> " + " | ".join(l.strip() for l in lines), indent=2)
            # -- shares breakdown with averages and allotted counts
            row.locator(".copy-shares-btn").click()
            self.page.wait_for_timeout(300)
            text = self.page.evaluate("navigator.clipboard.readText()")
            for label, shares, avg in (("Kostak", g["k_shares"], g["k_avg"]), ("Subject to", g["st_shares"], g["st_avg"]),
                                       ("Premium", g["p_shares"], g["p_avg"])):
                if whole(shares) != 0:
                    self.assertIn(f"{label.ljust(13)}", text)
                    self.assertRegex(text, rf"{label}\s+{re.escape(indian(whole(shares)))}( @ {re.escape(avg)})?")
            self.assertRegex(text, rf"Total Shares\s+{re.escape(indian(whole(g['total_shares'])))}( @ {re.escape(g['total_avg'])})?")
            kostak_alloted = sum(g["cell"][("Kostak", t)]["al_b"] - g["cell"][("Kostak", t)]["al_s"] for t in TIERS)
            if kostak_alloted:
                self.assertIn(f"({indian(kostak_alloted)} Alloted)", text)
        self.assertEqual(self.js_errors, [])

    # ======================================================================================
    # Section 2: toggle, search, rows per page
    # ======================================================================================
    def test_shares_with_average_toggle(self):
        self.open_status()
        switch = self.page.locator("#toggleAvgRateSwitch")
        label = self.page.locator("label.custom-switch")
        wrappers = self.page.locator(".row-avg-wrapper")
        shown = wrappers.count()
        self.assertGreater(shown, 0)
        expect(switch).to_be_checked()
        self.assertFalse(self.page.evaluate("document.body.classList.contains('hide-avg-rate')"))
        self.assertTrue(all(wrappers.nth(i).is_visible() for i in range(shown)))

        self.log(f"{shown} rows show '@ avg'; turning the switch off hides them", indent=2)
        label.click()
        expect(switch).not_to_be_checked()
        self.assertTrue(self.page.evaluate("document.body.classList.contains('hide-avg-rate')"))
        self.assertTrue(all(wrappers.nth(i).is_hidden() for i in range(shown)))
        self.assertEqual(self.page.evaluate("getComputedStyle(document.querySelector('.row-avg-wrapper')).display"), "none")
        self.assertEqual(self.page.evaluate("localStorage.getItem('positions_show_avg')"), "false")
        # the choice survives a reload
        self.page.reload()
        settle(self.page)
        expect(self.page.locator("#toggleAvgRateSwitch")).not_to_be_checked()
        self.assertTrue(self.page.evaluate("document.body.classList.contains('hide-avg-rate')"))
        # ... and back on
        self.page.locator("label.custom-switch").click()
        expect(self.page.locator("#toggleAvgRateSwitch")).to_be_checked()
        self.assertFalse(self.page.evaluate("document.body.classList.contains('hide-avg-rate')"))
        self.assertTrue(all(self.page.locator(".row-avg-wrapper").nth(i).is_visible() for i in range(shown)))
        self.assertEqual(self.js_errors, [])

    def search_for(self, term):
        with self.page.expect_navigation():                       # submitted ~500 ms after typing stops
            self.page.locator("#example_filter input").fill(term)
        settle(self.page)

    def test_search_filters_groups_and_updates_the_row_count(self):
        self.open_status()
        all_groups = [r["group"] for r in self.rows()]
        self.assertGreater(len(all_groups), 1)
        expect(self.page.get_by_text(f"Showing 1 to {len(all_groups)} of {len(all_groups)} Rows")).to_be_visible()

        for term, wanted in ((ALPHA, [ALPHA]), ("alpha", [ALPHA]), ("sigma cap", [SIGMA]), ("ZETA", [ZETA])):
            with self.subTest(search=term):
                self.search_for(term)
                self.assertEqual([r["group"] for r in self.rows()], wanted)
                expect(self.page.get_by_text("Showing 1 to 1 of 1 Rows")).to_be_visible()
                expect(self.page.locator("#example_filter input")).to_have_value(term)
        # the filtered row still carries the right figures
        self.search_for(ALPHA)
        g = self.expected(self.sipo)[ALPHA]
        self.assertEqual(self.num(self.row_for(ALPHA)["texts"][self.TOTAL_AMOUNT]), whole(g["total_amount"]))

        self.search_for("NO SUCH GROUP")
        self.assertEqual(self.rows(), [])
        expect(self.page.get_by_text("Showing 0 to 0 of 0 Rows")).to_be_visible()

        self.search_for("")                                                      # cleared -> everything is back
        self.assertEqual([r["group"] for r in self.rows()], all_groups)
        self.assertEqual(self.js_errors, [])

    def test_rows_per_page_selection_is_applied_and_remembered(self):
        total = len(FILLERS)
        self.open_status(self.pager)
        select = self.page.locator("#status_page_size")
        self.assertEqual(len(self.rows()), 50)
        expect(self.page.get_by_text(f"Showing 1 to 50 of {total} Rows")).to_be_visible()
        self.assertGreater(self.page.locator(".pagination .page-link", has_text="2").count(), 0)

        for size, shown in (("100", total), ("200", total), ("All", total), ("50", 50)):
            with self.subTest(size=size):
                with self.page.expect_navigation():
                    select.select_option(size)
                settle(self.page)
                self.assertEqual(len(self.rows()), shown)
                expect(self.page.locator("#status_page_size")).to_have_value(size)
                expect(self.page.get_by_text(f"Showing 1 to {shown} of {total} Rows")).to_be_visible()
                self.page.goto(self.status_url(self.pager))                      # remembered in the session
                settle(self.page)
                expect(self.page.locator("#status_page_size")).to_have_value(size)
                self.assertEqual(len(self.rows()), shown)
        # page 2 of the 50-row view holds the rest, in order
        self.page.goto(self.status_url(self.pager, "?page=2"))
        settle(self.page)
        self.assertEqual([r["group"] for r in self.rows()], sorted(FILLERS)[50:])
        expect(self.page.get_by_text(f"Showing 51 to {total} of {total} Rows")).to_be_visible()

    # ======================================================================================
    # Section 3: exports and Telegram
    # ======================================================================================
    def export_excel(self, tmp):
        self.page.get_by_role("button", name="Download").click()
        self.page.locator(".dt-button-collection .dt-button", has_text="Excel").click()
        popup = self.page.locator(".swal2-popup")
        expect(popup).to_be_visible()
        with self.page.expect_download() as info:
            popup.locator(".swal2-confirm").click()
        download = info.value
        path = os.path.join(tmp, download.suggested_filename)
        download.save_as(path)
        return download.suggested_filename, path

    def test_excel_export_matches_the_page(self):
        self.open_status()
        rows = self.rows()
        with tempfile.TemporaryDirectory() as tmp:
            name, path = self.export_excel(tmp)
            sheet = [["" if c is None else str(c).strip() for c in r]
                     for r in openpyxl.load_workbook(path).active.iter_rows(values_only=True)]
        self.log(f"exported '{name}' with {len(rows)} group rows", indent=2)
        self.assertEqual(name, f"{STATUS_IPO}-Group Wise Billing.xlsx")
        flat_header = " ".join(" ".join(r) for r in sheet[:4])
        for label in ("Count", "Alloted", "Billing", "Shares", "Amount"):
            self.assertIn(label, flat_header, f"header {label!r} missing from the Excel file")
        by_group = {r[1]: r for r in sheet if len(r) > 1 and r[1] in {x["group"] for x in rows}}
        self.assertEqual(sorted(by_group), sorted(x["group"] for x in rows), "group rows in the Excel file")
        for page_row in rows:
            excel = by_group[page_row["group"]]
            for column in range(2, len(page_row["texts"])):
                on_page = page_row["texts"][column]
                self.assertEqual(self.leading_number(excel[column]), self.leading_number(on_page),
                                 f"{page_row['group']} column {column}: {excel[column]!r} vs {on_page!r}")
        # the file's totals equal the sum over the page's groups, and the independent calculation
        expected = self.expected(self.sipo).values()
        self.assertEqual(sum(self.leading_number(by_group[g][self.TOTAL_AMOUNT]) for g in by_group),
                         sum(whole(g["total_amount"]) for g in expected))
        self.assertEqual(sum(self.leading_number(by_group[g][self.TOTAL_SHARES]) for g in by_group),
                         sum(whole(g["total_shares"]) for g in expected))

    @staticmethod
    def leading_number(text):
        m = re.match(r"-?[\d,]+(?:\.\d+)?", text.strip())
        return int(float(m.group(0).replace(",", ""))) if m else None

    @unittest.expectedFailure
    def test_the_export_to_excel_button_at_the_top_works(self):
        """KNOWN APP BUG: the 'Export to Excel' button calls exportTableToExcel(), which is not defined
        anywhere in the project, so it throws a ReferenceError and downloads nothing. (The Download > Excel
        button in the table toolbar is the working export.) Asserts the CORRECT behaviour."""
        self.open_status()
        self.assertEqual(self.page.evaluate("typeof exportTableToExcel"), "function")

    def telegram_user(self, session="fake-session"):
        self.user.Telegram_session, self.user.TelegramApi_id, self.user.TelegramApi_key = session, "12345", "key"
        self.user.save()

    def post_telegram(self, path, **kwargs):
        return self.page.request.post(f"{self.live_server_url}/{self.sipo.id}/{path}", **kwargs)

    def patched_telegram(self):
        return mock.patch.multiple("home.views", TelegramClient=FakeTelegram, StringSession=lambda s: s)

    def test_telegram_text_report_needs_a_verified_session(self):
        self.telegram_user(session=None)
        try:
            response = self.post_telegram("send-status-telegram/")
            self.assertEqual(response.status, 400)
            self.assertEqual(response.json()["status"], "session_expired")
            self.assertEqual(self.page.request.get(f"{self.live_server_url}/{self.sipo.id}/send-status-telegram/").status, 405)
        finally:
            self.telegram_user(session=None)

    def report_lines(self):
        self.telegram_user()
        try:
            with self.patched_telegram():
                response = self.post_telegram("send-status-telegram/")
        finally:
            self.telegram_user(session=None)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json(), {"status": "success", "message": "Status sent to Telegram successfully!"})
        self.assertEqual([m["kind"] for m in FakeTelegram.sent], ["message"])
        self.assertEqual(FakeTelegram.sent[0]["to"], "me")
        return FakeTelegram.sent[0]["text"].splitlines()

    def report_section(self, lines, heading, side):
        """The lines under '<heading>' / '<side>:' up to the next header."""
        start = lines.index(next(l for l in lines if heading in l))
        side_at = lines.index(f"**{side}:**", start)
        out = []
        for line in lines[side_at + 1:]:
            if not line.startswith("  "):
                break
            out.append(line.strip())
        return out

    def test_telegram_text_report_counts_and_structure(self):
        lines = self.report_lines()
        self.assertIn(f"**📊 {STATUS_IPO} - Status Report**", lines)
        self.assertTrue(any(l.startswith("**🕒 Generated: ") for l in lines))
        counts = defaultdict(lambda: [0, 0])
        for o in Order.objects.filter(user=self.user, OrderIPOName=self.sipo):
            counts[(o.OrderCategory, o.InvestorType, o.OrderType)][0 if o.OrderType == "BUY" else 1] += o.Quantity
        names = {"RETAIL": "Retail", "SHNI": "SHNI", "BHNI": "BHNI"}
        for heading, cat in (("Kostak", "Kostak"), ("Subject To", "Subject To")):
            for side in ("BUY", "SELL", "NET"):
                section = self.report_section(lines, heading, side)
                for tier, line in zip(TIERS, section):
                    buy = counts[(cat, tier, "BUY")][0]
                    sell = counts[(cat, tier, "SELL")][1]
                    want = {"BUY": buy, "SELL": sell, "NET": buy - sell}[side]
                    self.assertRegex(line, rf"^{names[tier]}: {want:.0f} @ ")
        premium = [self.report_section(lines, "Premium", s)[0] for s in ("BUY", "SELL", "NET")]
        buy = sum(q[0] for k, q in counts.items() if k[0] == "Premium")
        sell = sum(q[1] for k, q in counts.items() if k[0] == "Premium")
        self.assertRegex(premium[0], rf"^Count: {buy:.0f} @ ")
        self.assertRegex(premium[1], rf"^Count: {sell:.0f} @ ")
        self.assertRegex(premium[2], rf"^Count: {buy - sell:.0f} @ ")
        self.log(f"report has {len(lines)} lines; Kostak / Subject To / Premium counts match the orders", indent=2)

    @unittest.expectedFailure
    def test_telegram_text_report_amounts_and_averages(self):
        """KNOWN APP BUG: the report adds each order's RATE once (amount = amount + i.Rate) instead of
        rate x quantity, so every Kostak / Subject To amount and average is wrong for any order with more than
        one application (ALPHA's 5-application BUY order at 450 is reported as 450, not 2250), and Subject To
        premium-method amounts are off the same way. Asserts the CORRECT amounts."""
        lines = self.report_lines()
        want = defaultdict(lambda: [0.0, 0.0])        # (cat, tier, side) -> [count, amount]
        lot = {"RETAIL": 100, "SHNI": 1400, "BHNI": 7000}
        for o in Order.objects.filter(user=self.user, OrderIPOName=self.sipo, OrderCategory__in=["Kostak", "Subject To"]):
            factor = lot[o.InvestorType] if (o.OrderCategory == "Subject To" and o.Method == "Premium") else 1
            slot = want[(o.OrderCategory, o.InvestorType, o.OrderType)]
            slot[0] += o.Quantity
            slot[1] += o.Rate * o.Quantity * factor
        section = self.report_section(lines, "Kostak", "BUY")
        retail = want[("Kostak", "RETAIL", "BUY")]
        self.assertEqual(section[0], f"Retail: {retail[0]:.0f} @ ₹{retail[1] / retail[0]:.2f} = ₹{retail[1]:.2f}")

    def post_image(self, group_name, payload=b"\x89PNG-fake", with_file=True):
        files = {"image": {"name": "status.png", "mimeType": "image/png", "buffer": payload}} if with_file else {}
        return self.post_telegram("send-status-telegram-image/", multipart={"group_id": group_name, **files})

    def test_telegram_image_snapshot_is_sent_with_a_caption(self):
        GroupDetail.objects.filter(user=self.user, GroupName=ALPHA).update(MobileNo="9876543210")
        self.telegram_user()
        try:
            with self.patched_telegram():
                response = self.post_image(ALPHA, payload=b"\x89PNG-snapshot-bytes")
        finally:
            self.telegram_user(session=None)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(len(FakeTelegram.sent), 1)
        sent = FakeTelegram.sent[0]
        self.assertEqual(sent["kind"], "file")
        self.assertEqual(sent["to"], "+919876543210")                     # the group's mobile number
        self.assertEqual(sent["bytes"], b"\x89PNG-snapshot-bytes")
        self.assertIn(f"{STATUS_IPO} - Status Report", sent["caption"])
        self.assertIn(f"Group: {ALPHA}", sent["caption"])

    def test_telegram_image_rejects_bad_requests(self):
        self.telegram_user()
        try:
            with self.patched_telegram():
                self.assertEqual(self.post_image(ALPHA, with_file=False).status, 400)         # no image
                self.assertEqual(self.post_image("NO SUCH GROUP").status, 404)                # unknown group
                self.assertEqual(self.page.request.get(
                    f"{self.live_server_url}/{self.sipo.id}/send-status-telegram-image/").status, 405)
            self.telegram_user(session=None)
            self.assertEqual(self.post_image(ALPHA).json()["status"], "session_expired")
        finally:
            self.telegram_user(session=None)
        self.assertEqual(FakeTelegram.sent, [])

    # ======================================================================================
    # Section 4: Tally
    # ======================================================================================
    def visible_checkbox(self, group):
        return self.page.locator(f".group-checkbox[value='{group}']").locator("visible=true").first

    def capture_tally_post(self, action):
        seen = []
        handler = lambda request: seen.append(request) if request.url.endswith("/update-telly-status/") else None
        self.page.on("request", handler)
        try:
            with self.page.expect_navigation():              # the page reloads after the response
                action()
        finally:
            self.page.remove_listener("request", handler)
        settle(self.page)
        self.assertEqual(len(seen), 1)
        return seen[0]

    def test_tally_checkbox_for_one_group(self):
        self.open_status()
        before = self.tally_state()
        self.assertTrue(all(v == "False" for vals in before.values() for v in vals))
        self.log(f"ticking the Tally box of {BETA}", indent=2)
        request = self.capture_tally_post(lambda: self.visible_checkbox(BETA).check())
        payload = json.loads(request.post_data)
        self.assertEqual(payload, {"updateType": "One", "groupname": BETA, "status": True, "IPO_id": str(self.sipo.id)})
        self.assertEqual(request.method, "POST")

        state = self.tally_state()
        self.assertTrue(all(v == "True" for v in state[BETA]), "every order of the group is tallied")
        for group, values in state.items():
            if group != BETA:
                self.assertTrue(all(v == "False" for v in values), f"{group} must not change")
        stamps = set(Order.objects.filter(user=self.user, OrderIPOName=self.sipo, OrderGroup__GroupName=BETA)
                     .values_list("tally_timestamp", flat=True))
        self.assertNotIn(None, stamps)
        self.assertFalse(Order.objects.filter(user=self.user, OrderIPOName=self.sipo).exclude(OrderGroup__GroupName=BETA)
                         .exclude(tally_timestamp=None).exists())
        # persists across a reload: ticked, with the time shown
        self.page.reload()
        settle(self.page)
        for r in self.rows():
            self.assertEqual(r["checked"], r["group"] == BETA, r["group"])
        self.assertRegex(self.row_for(BETA)["tallyTime"], r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$")
        self.assertEqual(self.row_for(ALPHA)["tallyTime"], "")
        # the other tally's figures are untouched by ticking
        self.assertEqual(self.num(self.row_for(BETA)["texts"][self.TOTAL_AMOUNT]),
                         whole(self.expected(self.sipo)[BETA]["total_amount"]))

        # un-tick: false again, and the last tally time is kept ("Last: ...")
        request = self.capture_tally_post(lambda: self.visible_checkbox(BETA).uncheck())
        self.assertEqual(json.loads(request.post_data)["status"], False)
        self.assertTrue(all(v == "False" for v in self.tally_state()[BETA]))
        self.assertFalse(self.row_for(BETA)["checked"])
        self.assertTrue(self.row_for(BETA)["tallyTime"].startswith("Last: "))

    def test_server_answers_the_tally_request_with_success_and_the_time(self):
        self.open_status()
        reply = self.page.request.post(
            f"{self.live_server_url}/update-telly-status/",
            data=json.dumps({"updateType": "One", "groupname": ALPHA, "status": True, "IPO_id": str(self.sipo.id)}),
            headers={"Content-Type": "application/json"})
        body = reply.json()
        self.assertTrue(body["success"])
        self.assertRegex(body["ts_str"], r"^\d{2}-\d{2}-\d{4}<br>\d{2}:\d{2}:\d{2}$")
        self.assertTrue(all(v == "True" for v in self.tally_state()[ALPHA]))

    def test_master_tally_checkbox_toggles_every_group(self):
        self.open_status()
        master = self.page.locator("#master-tally-checkbox").locator("visible=true").first
        self.assertFalse(master.is_checked())
        request = self.capture_tally_post(lambda: master.check())
        payload = json.loads(request.post_data)
        groups = [r["group"] for r in self.rows()]
        self.assertEqual((payload["updateType"], payload["status"], payload["IPO_id"]), ("All", True, str(self.sipo.id)))
        self.assertEqual(sorted(payload["group_names"]), sorted(groups))
        self.assertTrue(all(v == "True" for vals in self.tally_state().values() for v in vals))
        self.assertTrue(all(r["checked"] for r in self.rows()))
        self.assertTrue(self.page.locator("#master-tally-checkbox").locator("visible=true").first.is_checked())
        self.log(f"master tick -> {len(groups)} groups tallied and still ticked after the reload", indent=2)

        request = self.capture_tally_post(lambda: self.page.locator("#master-tally-checkbox").locator("visible=true").first.uncheck())
        self.assertEqual(json.loads(request.post_data)["status"], False)
        self.assertTrue(all(v == "False" for vals in self.tally_state().values() for v in vals))
        self.assertFalse(any(r["checked"] for r in self.rows()))

    def test_a_group_is_ticked_only_when_all_its_orders_are_tallied(self):
        orders = Order.objects.filter(user=self.user, OrderIPOName=self.sipo, OrderGroup__GroupName=ALPHA)
        self.assertGreater(orders.count(), 1)
        orders.update(Telly="True")
        Order.objects.filter(pk=orders.first().pk).update(Telly="False")                          # one order left untallied
        self.open_status()
        self.assertFalse(self.row_for(ALPHA)["checked"])
        Order.objects.filter(user=self.user, OrderIPOName=self.sipo, OrderGroup__GroupName=ALPHA).update(Telly="True")
        self.open_status()
        self.assertTrue(self.row_for(ALPHA)["checked"])
        # master is ticked only when EVERY group is
        self.assertFalse(self.page.locator("#master-tally-checkbox").locator("visible=true").first.is_checked())
        Order.objects.filter(user=self.user, OrderIPOName=self.sipo).update(Telly="True")
        self.open_status()
        self.assertTrue(self.page.locator("#master-tally-checkbox").locator("visible=true").first.is_checked())

    def test_tally_requests_without_a_login_change_nothing(self):
        self.page.context.clear_cookies()
        try:
            reply = self.page.request.post(
                f"{self.live_server_url}/update-telly-status/",
                data=json.dumps({"updateType": "All", "status": True, "IPO_id": str(self.sipo.id)}),
                headers={"Content-Type": "application/json"})
            self.assertFalse(reply.json().get("success"))
        finally:
            self.relogin()
        self.assertTrue(all(v == "False" for vals in self.tally_state().values() for v in vals))
