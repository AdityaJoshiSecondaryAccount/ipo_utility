"""
Application BUY / SELL Order Detail E2E
(/<IPOid>/OrderDetail/BUY and /<IPOid>/OrderDetail/SELL, templates/OrderDetailsUnified.html).

Runs last in the pipeline, on the IPO / broker left behind by the earlier pages (always
MAINBOARD, so the Retail / SHNI / BHNI tiers and their selectors exist). Every core test is
run for BOTH order types and checks the scoping (OrderDetail.Order.OrderType).

Data model note: a PAN is not stored on OrderDetail itself. OrderDetail.OrderDetailPANNo
points to a ClientDetail whose PANNo holds the PAN, so "PAN saved" means
OrderDetail.OrderDetailPANNo.PANNo == "<PAN>".

Isolation: the PAN-editing tests use dedicated "lab" groups (PAN LAB, PAN LAB 2, NET LAB,
PAGE LAB) whose orders are seeded here and whose PAN state is reset at the start of each
subtest, so they never disturb the BUY/SELL data from the earlier pages. Read-only checks
(summary maths, filters) run against the real IPO-wide data and are computed from the DB.
"""
import csv
import datetime
import io
import os
import re
import tempfile
import unittest
import uuid
from collections import Counter
from urllib.parse import quote

from django.utils import timezone
from playwright.sync_api import expect

from home.models import (ClientDetail, GroupDetail, Order, OrderDetail, SharedLink)
from test_cases.base import (IPO_NAME, PersistentLiveServerTestCase, pause_for_inspection, settle)

ORDER_TYPES = ("BUY", "SELL")
LAB, LAB2, NET_LAB, PAGE_LAB = "PAN LAB", "PAN LAB 2", "NET LAB", "PAGE LAB"
# Shareholder-quota labs. SHF's NAME contains the word "shareholder" on purpose (see the
# expected-failure test about the page's text-based shareholder detection).
SH, SHF = "SH LAB", "SHAREHOLDER FAMILY"
SHAREHOLDER_REMARK = {"tags": ["Shareholder Application"]}
LAB_DATE, LAB_TIME = datetime.date(2026, 1, 20), datetime.time(10, 0, 0)
VALID_PAN = "ABCDE1234F"


class OrderDetailPlaywrightTestCase(PersistentLiveServerTestCase):
    PAGE_NAME = "order_detail"
    _ran_any = False

    # ------------------------------------------------------------------ setup / teardown
    @classmethod
    def tearDownClass(cls):
        # Keep the window open on the page for manual inspection (once, after the last test,
        # while the live server is still up).
        cls.log_summary()
        if cls._ran_any:
            try:
                cls.page.goto(f"{cls.live_server_url}/{cls._ipo_id}/OrderDetail/BUY")
                settle(cls.page)
            except Exception:
                pass
            pause_for_inspection(cls.PAGE_NAME)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        type(self)._ran_any = True
        type(self)._ipo_id = self.ipo.id
        self.assertEqual(self.ipo.IPOType, "MAINBOARD")
        self.js_errors = []
        self.page.on("pageerror", lambda e: self.js_errors.append(f"{e.message}\n{e.stack}"))
        self.page.on("console", self._on_console)
        self.ensure_core_data()

    def tearDown(self):
        self.page.remove_listener("console", self._on_console)
        super().tearDown()

    def _on_console(self, msg):
        if msg.type == "error" and not msg.text.startswith("Failed to load resource"):
            self.js_errors.append(msg.text)

    # ------------------------------------------------------------------------- data helpers
    def group(self, name):
        return GroupDetail.objects.get_or_create(user=self.user, GroupName=name)[0]

    def details(self, ordtyp):
        return OrderDetail.objects.filter(
            user=self.user, Order__OrderIPOName_id=self.ipo.id, Order__OrderType=ordtyp)

    def seed_order(self, group, ordtyp, rate, qty, category="Kostak", investor="RETAIL",
                   remark=None, date=LAB_DATE, time=LAB_TIME):
        """Idempotent: one Order (+ qty OrderDetails) per (group, type, category, investor, rate)."""
        grp = self.group(group)
        order = Order.objects.filter(
            user=self.user, OrderIPOName=self.ipo, OrderGroup=grp, OrderType=ordtyp,
            OrderCategory=category, InvestorType=investor, Rate=rate).first()
        if order is None:
            order = Order.objects.create(
                user=self.user, OrderIPOName=self.ipo, OrderGroup=grp, OrderType=ordtyp,
                OrderCategory=category, InvestorType=investor, Rate=rate, Quantity=qty,
                OrderDate=date, OrderTime=time, remark=remark)
        missing = int(qty) - OrderDetail.objects.filter(Order=order).count()
        if missing > 0:
            OrderDetail.objects.bulk_create([
                OrderDetail(user=self.user, Order=order, PreOpenPrice=self.ipo.PreOpenPrice)
                for _ in range(missing)])
        return order

    def ensure_core_data(self):
        """The earlier BUY/SELL pages leave real data; if run on its own, seed a small set."""
        for ordtyp, shift in (("BUY", 0), ("SELL", 5)):
            if Order.objects.filter(user=self.user, OrderIPOName=self.ipo, OrderType=ordtyp,
                                    OrderGroup__GroupName="ALPHA TRADERS").exists():
                continue
            self.seed_order("ALPHA TRADERS", ordtyp, 450 + shift, 5)
            self.seed_order("ALPHA TRADERS", ordtyp, 1200 + shift, 3, category="Subject To")
            self.seed_order("BETA INVESTORS", ordtyp, 600 + shift, 2, investor="SHNI")
            self.seed_order("BETA INVESTORS", ordtyp, 700 + shift, 4, investor="BHNI")
        # lab data
        self.seed_order(LAB, "BUY", 111.0, 4)
        self.seed_order(LAB, "SELL", 222.0, 4, investor="SHNI")           # different tier -> no netting
        self.seed_order(LAB2, "BUY", 333.0, 1)
        self.seed_order(LAB2, "SELL", 444.0, 1, investor="SHNI")
        self.seed_order(NET_LAB, "BUY", 555.0, 3)                          # 3 BUY vs 2 SELL, same key
        self.seed_order(NET_LAB, "SELL", 556.0, 2)
        self.seed_order(PAGE_LAB, "BUY", 666.0, 60)                        # > one page of 50
        self.seed_order(PAGE_LAB, "SELL", 667.0, 60, investor="SHNI")
        self.seed_sh_labs()

    SH_BASE = {"BUY": 800, "SELL": 810}
    SH_CATEGORY = {"BUY": "Kostak", "SELL": "Subject To"}      # different categories -> BUY and SELL never net off

    def seed_sh_labs(self):
        """
        Per order type (rate = base + n):
          +1 RETAIL standard (2 apps)      +2 RETAIL shareholder-remark (2 apps)
          +3 SHNI with a shareholder remark (1 app; SHNI is never a shareholder quota)
          +4 RETAIL shareholder-remark in SHAREHOLDER FAMILY (1 app); +1 RETAIL standard in SHAREHOLDER FAMILY
        """
        for ordtyp, base in self.SH_BASE.items():
            cat = self.SH_CATEGORY[ordtyp]
            self.seed_order(SH, ordtyp, base + 1, 2, category=cat)
            self.seed_order(SH, ordtyp, base + 2, 2, category=cat, remark=SHAREHOLDER_REMARK)
            self.seed_order(SH, ordtyp, base + 3, 1, category=cat, investor="SHNI", remark=SHAREHOLDER_REMARK)
            self.seed_order(SHF, ordtyp, base + 1, 1, category=cat)
            self.seed_order(SHF, ordtyp, base + 4, 1, category=cat, remark=SHAREHOLDER_REMARK)

    def sh_ids(self, ordtyp):
        """Application ids by kind (creation order)."""
        base = self.SH_BASE[ordtyp]

        def ids(group, rate):
            return list(self.details(ordtyp).filter(
                Order__OrderGroup__GroupName=group, Order__Rate=rate).order_by("id").values_list("id", flat=True))
        return {"std": ids(SH, base + 1), "sh": ids(SH, base + 2), "shni": ids(SH, base + 3),
                "fam_std": ids(SHF, base + 1), "fam_sh": ids(SHF, base + 4)}

    def reset_labs(self):
        """Back to 'no PAN anywhere' for all lab groups (BUY/SELL data is untouched)."""
        groups = GroupDetail.objects.filter(user=self.user, GroupName__in=[LAB, LAB2, NET_LAB, PAGE_LAB, SH, SHF])
        OrderDetail.objects.filter(user=self.user, Order__OrderGroup__in=groups).update(
            OrderDetailPANNo=None, AllotedQty=None, DematNumber="", ApplicationNumber="", Amount=0)
        ClientDetail.objects.filter(user=self.user, Group__in=groups).delete()

    def assign_pan(self, od, pan, group=LAB):
        client, _ = ClientDetail.objects.get_or_create(
            user=self.user, PANNo=pan, defaults={"Name": "TEST CLIENT", "Group": self.group(group)})
        od.OrderDetailPANNo = client
        od.save()

    def lab_details(self, ordtyp, group=LAB):
        return self.details(ordtyp).filter(Order__OrderGroup__GroupName=group).order_by("id")

    def pans_in_db(self, ordtyp, group=LAB):
        return [od.OrderDetailPANNo.PANNo if od.OrderDetailPANNo else None
                for od in self.lab_details(ordtyp, group).select_related("OrderDetailPANNo")]

    # ---------------------------------------------------------------------------- page helpers
    def url(self, ordtyp, group=None, category="All", investor="All", query=""):
        path = f"/{self.ipo.id}/OrderDetail/{ordtyp}"
        if group:
            path += f"/{quote(group)}/{quote(category)}/{quote(investor)}"
        return f"{self.live_server_url}{path}{query}"

    def open_detail(self, ordtyp, group=None, query=""):
        # ids of this group's applications in creation order. The table re-sorts after a PAN
        # is saved, so tests address rows by id (#PAN_<id>), never by screen position.
        self.ids = (list(self.lab_details(ordtyp, group).values_list("id", flat=True)) if group else [])
        self.page.goto(self.url(ordtyp, group, query=query))
        settle(self.page)
        expect(self.page.locator("#sortable-table")).to_be_visible()

    def relogin(self):
        self.page.context.add_cookies([{
            "name": "sessionid", "value": self.client.cookies["sessionid"].value,
            "domain": "localhost", "path": "/"}])

    def set_view_mode(self, mode):
        """The page remembers Net/Gross in localStorage; set it before loading."""
        self.page.goto(f"{self.live_server_url}/login")
        self.page.evaluate(f"localStorage.setItem('ipo_order_view_mode', '{mode}')")

    def ajax_wait(self):
        """fetchOrderData() fades the table to 0.5 while loading; wait until it is back."""
        self.page.wait_for_function("document.getElementById('sortable-table').style.opacity !== '0.5'")
        self.page.wait_for_timeout(350)

    def pick(self, selector, **kw):
        self.page.select_option(selector, **kw)
        self.ajax_wait()

    def rows(self):
        return self.page.evaluate("""() => [...document.querySelectorAll('#sortable-table tbody tr')]
            .filter(tr => !tr.querySelector('td.dataTables_empty'))
            .map(tr => { const td = [...tr.querySelectorAll('td')];
                const pan = tr.querySelector("input[name^='PAN_']");
                return {group: td[1].textContent.trim(), category: td[2].textContent.trim(),
                        investor: td[3].textContent.trim(), rate: parseFloat(td[4].textContent),
                        pan: pan ? pan.value : '', squared: tr.dataset.squaredOff === 'true',
                        id: tr.querySelector('.row_checkbox')?.dataset.rowId}; })""")

    def table_signature(self):
        return Counter((r["group"], r["category"], r["investor"], r["rate"]) for r in self.rows())

    def db_signature(self, qs):
        return Counter((od.Order.OrderGroup.GroupName, od.Order.OrderCategory,
                        od.Order.InvestorType, float(od.Order.Rate))
                       for od in qs.select_related("Order", "Order__OrderGroup"))

    def counter(self, element_id):
        return int(self.page.locator(f"#{element_id}").inner_text().strip())

    def pan_input(self, index):
        """The PAN field of the index-th application (by id) of the group being viewed."""
        return self.page.locator(f"#PAN_{self.ids[index]}")

    def tooltip(self, index):
        return self.page.locator(f"#tooltip_{self.ids[index]}")

    def pan_on_screen(self):
        """{application id: PAN text shown} for every row on screen."""
        return {int(r["id"]): r["pan"] for r in self.rows()}

    def click_update_and_wait(self):
        with self.page.expect_navigation():
            self.page.locator("#main-update-btn").click()
        settle(self.page)

    def click_update_expect_blocked(self):
        """Update must NOT submit: the page does not reload (a sentinel survives) and nothing is sent."""
        self.page.evaluate("window.__sentinel = 'still-here'")
        requests = []
        handler = lambda r: requests.append(r.url) if "update_pann" in r.url else None
        self.page.on("request", handler)
        self.page.locator("#main-update-btn").click()
        self.page.wait_for_timeout(800)
        self.page.remove_listener("request", handler)
        self.assertEqual(self.page.evaluate("window.__sentinel"), "still-here", "page reloaded")
        self.assertEqual(requests, [], "validation should stop the submission")

    # ---------------------------------------------------- expected values (independent oracle)
    def expected_summary(self, ordtyp, group="All", category="All", investor="All", rate=None):
        qs = self.details(ordtyp)
        opp = self.details("SELL" if ordtyp == "BUY" else "BUY")
        if group != "All":
            qs, opp = (q.filter(Order__OrderGroup__GroupName=group) for q in (qs, opp))
        if category != "All":
            qs, opp = (q.filter(Order__OrderCategory=category) for q in (qs, opp))
        if investor != "All":
            qs, opp = (q.filter(Order__InvestorType__iexact=investor) for q in (qs, opp))
        if rate is not None:
            qs = qs.filter(Order__Rate=rate)             # the view does not filter the opposite side by rate
        key = lambda od: (od.Order.OrderGroup.GroupName, od.Order.OrderCategory, od.Order.InvestorType)
        cur = Counter(key(od) for od in qs.select_related("Order", "Order__OrderGroup"))
        oth = Counter(key(od) for od in opp.select_related("Order", "Order__OrderGroup"))
        pending = Counter(key(od) for od in
                          qs.filter(OrderDetailPANNo=None).select_related("Order", "Order__OrderGroup"))
        squared = sum(min(min(cur[k], oth[k]), pending[k]) for k in cur)
        total = qs.count()
        without = qs.filter(OrderDetailPANNo=None).count()
        return dict(total=total, received=total - without, squared=squared,
                    pending=max(0, without - squared))

    def assert_summary(self, ordtyp, **filters):
        want = self.expected_summary(ordtyp, **filters)
        self.assertEqual(self.counter("summary-app-total"), want["total"], f"{ordtyp} total {filters}")
        self.assertEqual(self.counter("summary-received-pan"), want["received"], f"{ordtyp} received")
        self.assertEqual(self.counter("summary-pending-pan"), want["pending"], f"{ordtyp} pending")
        return want

    # ======================================================================================
    # 1. Page identity, layout, scoping, access control
    # ======================================================================================
    def test_page_identity_title_and_footer(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                label = ordtyp.title()
                self.open_detail(ordtyp)
                expect(self.page.locator("h3", has_text=re.compile(rf"^App\.-{label} Order Detail$"))).to_be_visible()
                self.assertIn(f"App.-{label} Order Detail", self.page.title())
                expect(self.page.locator("h3.iponame")).to_have_text(IPO_NAME)

                buy = self.page.locator(".footer a", has_text="App. Buy Order (PAN)")
                sell = self.page.locator(".footer a", has_text="App. Sell Order (PAN)")
                active, other = (buy, sell) if ordtyp == "BUY" else (sell, buy)
                expect(active).to_have_class(re.compile(r"\bdisabled\b"))
                expect(other).not_to_have_class(re.compile(r"\bdisabled\b"))
                expect(other).to_have_attribute(
                    "href", f"/{self.ipo.id}/OrderDetail/{'SELL' if ordtyp == 'BUY' else 'BUY'}")

                # scoping: every row shown belongs to this order type, and nothing is missing
                self.page.select_option("#page_size", "All")
                self.ajax_wait()
        self.assertEqual(self.js_errors, [])

    def test_rows_are_scoped_to_the_order_type(self):
        """BUY lab rows only on the BUY page, SELL lab rows only on the SELL page."""
        self.reset_labs()
        for ordtyp, other in (("BUY", "SELL"), ("SELL", "BUY")):
            with self.subTest(ordtyp=ordtyp):
                self.open_detail(ordtyp, LAB)
                self.assertEqual(self.table_signature(), self.db_signature(self.lab_details(ordtyp)))
                self.assertFalse(self.lab_details(other).filter(
                    id__in=[int(r["id"]) for r in self.rows()]).exists())
                want_rate = 111.0 if ordtyp == "BUY" else 222.0
                self.assertEqual({r["rate"] for r in self.rows()}, {want_rate})

    def test_unauthenticated_access_is_denied(self):
        self.reset_labs()
        self.page.context.clear_cookies()
        try:
            for ordtyp in ORDER_TYPES:
                with self.subTest(ordtyp=ordtyp):
                    self.page.goto(self.url(ordtyp, LAB))
                    settle(self.page)
                    self.assertIn("/login", self.page.url)
                    body = self.page.content()
                    for leak in (LAB, "ALPHA TRADERS", IPO_NAME, "PAN_"):
                        self.assertNotIn(leak, body, f"{leak!r} leaked to an anonymous visitor")
                    self.assertEqual(self.page.locator("#sortable-table").count(), 0)
        finally:
            self.relogin()

    @unittest.expectedFailure
    def test_invalid_ipo_id_is_a_clean_404(self):
        """KNOWN APP BUG: an unknown IPO id raises CurrentIpoName.DoesNotExist -> HTTP 500.
        Asserts the CORRECT behaviour (404); reports 'unexpected success' once the view handles it."""
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                response = self.page.goto(f"{self.live_server_url}/999999/OrderDetail/{ordtyp}")
                self.assertEqual(response.status, 404, "an unknown IPO should be a clean 404, not a 500")

    # ------------------------------------------------------------------------- guest link
    def make_guest_link(self, group=LAB, hours=24):
        return SharedLink.objects.create(
            user=self.user, group=self.group(group), ipo=self.ipo,
            expiry_at=timezone.now() + datetime.timedelta(hours=hours))

    def open_guest(self, link, ordtyp):
        self.page.context.clear_cookies()
        self.page.goto(f"{self.live_server_url}/access-link/{link.id}/{ordtyp}")
        settle(self.page)

    def test_guest_link_view_hides_broker_controls(self):
        self.reset_labs()
        link = self.make_guest_link(LAB)
        try:
            for ordtyp in ORDER_TYPES:
                with self.subTest(ordtyp=ordtyp):
                    self.open_guest(link, ordtyp)
                    # guest heading, live countdown, only the shared group, no broker buttons
                    expect(self.page.locator("h3", has_text="Application Sell Order Detail")
                           if ordtyp == "SELL" else self.page.locator("h3").nth(1)).to_be_visible()
                    expect(self.page.locator("#expiry-timer")).to_be_visible()
                    first = self.page.locator("#seconds").inner_text()
                    self.page.wait_for_timeout(2200)
                    self.assertNotEqual(first, self.page.locator("#seconds").inner_text(), "countdown frozen")
                    self.assertEqual(self.page.locator("#hours").inner_text(), "23")   # ~24h left
                    for name in ("Manage Links", "Firm Allotment", "Check Allotment"):
                        self.assertEqual(self.page.get_by_role("button", name=name).count(), 0,
                                         f"{name} must not render for guests")
                    self.assertEqual([t.strip() for t in self.page.locator("#category option").all_inner_texts()], [LAB])
                    self.assertEqual(self.table_signature(), self.db_signature(self.lab_details(ordtyp)))
        finally:
            self.page.context.clear_cookies()
            self.relogin()
            link.delete()

    @unittest.expectedFailure
    def test_guest_buy_page_heading_says_buy(self):
        """KNOWN APP BUG: the guest template hard-codes 'Application Sell Order Detail' even for BUY.
        Asserts the CORRECT heading; reports 'unexpected success' once the template is fixed."""
        link = self.make_guest_link(LAB)
        try:
            self.open_guest(link, "BUY")
            expect(self.page.locator("h3", has_text="Application Buy Order Detail")).to_be_visible(timeout=2000)
        finally:
            self.page.context.clear_cookies()
            self.relogin()
            link.delete()

    # ======================================================================================
    # 2. Summary counters
    # ======================================================================================
    def test_summary_counters_match_database(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.open_detail(ordtyp)
                want = self.assert_summary(ordtyp)
                self.assertGreater(want["total"], 0)
                if want["squared"]:
                    badge = self.page.locator("#summary-net-badge")
                    expect(badge).to_have_text(str(want["squared"]))
                    expect(badge).to_have_attribute(
                        "title", f"Gross: {want['total']} Applications | Settled: {want['squared']} "
                                 f"| Pending: {want['pending']}")

    def test_new_orders_without_pan_are_all_pending(self):
        """No PAN yet -> received 0; pending == total (nothing to net in the lab group)."""
        self.reset_labs()
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.open_detail(ordtyp, LAB)
                self.assertEqual(self.counter("summary-app-total"), 4)
                self.assertEqual(self.counter("summary-received-pan"), 0)
                self.assertEqual(self.counter("summary-pending-pan"), self.counter("summary-app-total"))
                self.assertEqual(self.page.locator("#summary-net-badge").count(), 0)

    def test_settled_badge_when_buy_and_sell_overlap(self):
        """NET LAB: 3 BUY vs 2 SELL in the same group/category/investor -> 2 settled on each side."""
        self.reset_labs()
        for ordtyp, total, settled in (("BUY", 3, 2), ("SELL", 2, 2)):
            with self.subTest(ordtyp=ordtyp):
                self.open_detail(ordtyp, NET_LAB)
                want = self.assert_summary(ordtyp, group=NET_LAB)
                self.assertEqual((want["total"], want["squared"]), (total, settled))
                expect(self.page.locator("#summary-net-badge")).to_have_text(str(settled))
                expect(self.page.locator("#summary-net-container")).to_be_visible()
                self.assertEqual(self.counter("summary-pending-pan"), total - settled)

    # ======================================================================================
    # 3. Filters
    # ======================================================================================
    def test_filter_bar_group_category_investor_rate(self):
        self.reset_labs()
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.set_view_mode("gross")                    # show every row, settled or not
                try:
                    self.open_detail(ordtyp)
                    self.pick("#page_size", value="All")
                    base = self.details(ordtyp)
                    self.assertEqual(self.table_signature(), self.db_signature(base), "unfiltered")

                    group = "ALPHA TRADERS"
                    self.log(f"unfiltered table == DB ({base.count()} applications); now filtering step by step", indent=2)
                    self.pick("#category", value=group)
                    qs = base.filter(Order__OrderGroup__GroupName=group)
                    self.assertEqual({r["group"] for r in self.rows()}, {group})
                    self.assertEqual(self.table_signature(), self.db_signature(qs), "group filter")
                    self.assert_summary(ordtyp, group=group)

                    self.pick("#category1", value="Kostak")
                    qs = qs.filter(Order__OrderCategory="Kostak")
                    self.assertEqual({r["category"] for r in self.rows()}, {"Kostak"})
                    self.assertEqual(self.table_signature(), self.db_signature(qs), "category filter")

                    self.pick("#category2", value="RETAIL")
                    qs = qs.filter(Order__InvestorType="RETAIL")
                    self.assertEqual({r["investor"] for r in self.rows()}, {"RETAIL"})
                    self.assertEqual(self.table_signature(), self.db_signature(qs), "investor filter")

                    rate = float(qs.order_by("id").first().Order.Rate)
                    values = self.page.eval_on_selector_all("#frate option", "els => els.map(e => e.value)")
                    value = next(v for v in values if v != "All" and float(v) == rate)
                    self.pick("#frate", value=value)
                    qs = qs.filter(Order__Rate=rate)
                    self.assertEqual({r["rate"] for r in self.rows()}, {rate})
                    self.assertEqual(self.table_signature(), self.db_signature(qs), "rate filter")
                    self.assert_summary(ordtyp, group=group, category="Kostak", investor="RETAIL", rate=rate)

                    self.log("group + category + investor + rate filters all matched the DB; resetting", indent=2)
                    # tier filter on its own
                    self.pick("#frate", value="All")
                    self.pick("#category", value="All")
                    self.pick("#category1", value="All")
                    self.pick("#category2", value="SHNI")
                    self.assertEqual(self.table_signature(),
                                     self.db_signature(base.filter(Order__InvestorType="SHNI")), "SHNI")
                    self.pick("#category2", value="All")
                    self.assertEqual(self.table_signature(), self.db_signature(base), "reset")
                    self.assertEqual(self.js_errors, [])
                finally:
                    self.set_view_mode("net")

    def test_filter_combination_with_no_orders_shows_empty_state(self):
        self.reset_labs()
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                # AJAX: the lab group only has RETAIL (BUY) / SHNI (SELL) orders; ask for BHNI
                self.open_detail(ordtyp)
                self.pick("#category", value=LAB)
                self.pick("#category2", value="BHNI")
                expect(self.page.locator("#sortable-table td.dataTables_empty")).to_have_text("No data available")
                self.assertEqual(self.rows(), [])
                self.assertEqual(self.counter("summary-app-total"), 0)
                # URL: group + a rate that group never traded
                self.page.goto(self.url(ordtyp, LAB, query="?RateFilterValue=450"))
                settle(self.page)
                expect(self.page.locator("#sortable-table td.dataTables_empty")).to_have_text("No data available")
                self.assertEqual(self.counter("summary-app-total"), 0)
        self.assertEqual(self.js_errors, [])

    # ======================================================================================
    # 4. Inline PAN entry and validation
    # ======================================================================================
    def test_valid_pan_is_saved_uppercased_and_counters_update(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, LAB)
                self.assertEqual(self.counter("summary-received-pan"), 0)
                pan = self.pan_input(0)
                pan.fill("abcde1234f")                                    # typed in lowercase
                self.assertEqual(pan.evaluate("el => getComputedStyle(el).textTransform"), "uppercase")
                self.click_update_and_wait()

                self.assertEqual(self.pans_in_db(ordtyp), ["ABCDE1234F", None, None, None])
                client = self.lab_details(ordtyp).first().OrderDetailPANNo
                self.assertEqual(client.PANNo, "ABCDE1234F")
                self.assertEqual(client.Group.GroupName, LAB)
                self.assertEqual(self.pan_input(0).input_value(), "ABCDE1234F")
                self.assertEqual(self.counter("summary-received-pan"), 1)
                self.assertEqual(self.counter("summary-pending-pan"), 3)
                self.assertEqual(self.counter("summary-app-total"), 4)
        self.assertEqual(self.js_errors, [])

    def test_pan_field_enforces_maxlength_when_typing(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, LAB)
                expect(self.pan_input(0)).to_have_attribute("maxlength", "10")
                self.pan_input(0).click()
                self.pan_input(0).press_sequentially("ABCDE123456F")        # 12 keystrokes
                value = self.pan_input(0).input_value()
                self.assertEqual(len(value), 10)
                self.assertEqual(value, "ABCDE12345")

    def test_invalid_pans_are_rejected_without_saving(self):
        # Three representative formats (the 10-character cap is covered by its own maxlength test):
        bad = {
            "too short (8 characters)": "ABCDE123",
            "wrong structure (digits in the letter positions)": "123AB4567C",
            "special character": "ABCDE@123F",
        }
        for ordtyp in ORDER_TYPES:
            for label, value in bad.items():
                with self.subTest(ordtyp=ordtyp, case=label):
                    self.reset_labs()
                    self.open_detail(ordtyp, LAB)
                    self.pan_input(0).fill(value)
                    self.click_update_expect_blocked()
                    if len(value) < 10:
                        # minlength=10: the browser's own validation stops the submit first and
                        # focuses the field (which hides the app tooltip) ...
                        self.assertTrue(self.pan_input(0).evaluate("el => el.validity.tooShort"))
                        self.pan_input(0).evaluate("el => el.blur()")      # ... it shows again on blur
                    expect(self.tooltip(0)).to_be_visible()
                    expect(self.tooltip(0)).to_have_text("Invalid PAN number")
                    self.assertEqual(self.pans_in_db(ordtyp), [None] * 4, "nothing may be saved")
        self.assertEqual(self.js_errors, [])

    def test_duplicate_pan_in_same_batch_fix_rows(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, LAB)
                self.pan_input(0).fill(VALID_PAN)
                self.pan_input(1).fill(VALID_PAN)
                self.click_update_expect_blocked()

                modal = self.page.locator("#duplicatePanModal")
                expect(modal).to_have_class(re.compile(r"\bshow\b"))
                expect(modal.locator("#duplicatePanModalLabel")).to_contain_text("Duplicate PANs Detected")
                expect(modal.locator("#duplicate-pan-list")).to_have_text(VALID_PAN)
                expect(modal.locator("#duplicate-pan-count-msg")).to_contain_text("1")
                for i in (0, 1):                                            # both rows flagged red
                    self.assertEqual(self.pan_input(i).evaluate("el => getComputedStyle(el).backgroundColor"),
                                     "rgb(254, 215, 215)")
                self.assertEqual(self.pans_in_db(ordtyp), [None] * 4)

                modal.get_by_role("button", name="Fix Row(s)").click()
                expect(modal).to_be_hidden()
                self.assertEqual(self.pans_in_db(ordtyp), [None] * 4)

                self.pan_input(1).fill("FGHIJ5678K")                         # fix the second row
                self.click_update_and_wait()
                self.assertEqual(self.pans_in_db(ordtyp), [VALID_PAN, "FGHIJ5678K", None, None])

    def test_duplicate_pan_in_same_batch_skip_duplicates(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, LAB)
                self.pan_input(0).fill(VALID_PAN)
                self.pan_input(1).fill(VALID_PAN)
                self.pan_input(2).fill("LMNOP9012Q")                          # the only unique one
                self.click_update_expect_blocked()
                modal = self.page.locator("#duplicatePanModal")
                expect(modal).to_have_class(re.compile(r"\bshow\b"))
                with self.page.expect_navigation():
                    modal.get_by_role("button", name="Skip Duplicates & Update Rest").click()
                settle(self.page)
                self.assertEqual(self.pans_in_db(ordtyp), [None, None, "LMNOP9012Q", None])
                self.assertEqual(self.counter("summary-received-pan"), 1)

    def test_duplicate_pan_against_existing_record_in_another_application(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                other = self.lab_details(ordtyp, LAB2).first()
                self.assign_pan(other, VALID_PAN, group=LAB2)                # saved on another application
                self.open_detail(ordtyp, LAB)                                # that row is not on this page
                self.pan_input(0).fill(VALID_PAN)
                self.click_update_expect_blocked()
                modal = self.page.locator("#duplicatePanModal")
                expect(modal).to_have_class(re.compile(r"\bshow\b"))
                expect(modal.locator("#duplicate-pan-list")).to_have_text(VALID_PAN)
                self.assertEqual(self.pan_input(0).evaluate("el => getComputedStyle(el).backgroundColor"),
                                 "rgb(254, 215, 215)")
                self.assertEqual(self.pans_in_db(ordtyp), [None] * 4)
                modal.get_by_role("button", name="Fix Row(s)").click()
                expect(modal).to_be_hidden()

    def test_same_pan_may_be_used_once_on_buy_and_once_on_sell(self):
        """Duplicates are checked per order type: the same PAN can hold one BUY and one SELL application."""
        self.reset_labs()
        self.assign_pan(self.lab_details("SELL").first(), VALID_PAN)
        self.open_detail("BUY", LAB)
        self.pan_input(0).fill(VALID_PAN)
        self.click_update_and_wait()
        self.assertEqual(self.pans_in_db("BUY"), [VALID_PAN, None, None, None])
        self.assertEqual(self.pans_in_db("SELL"), [VALID_PAN, None, None, None])

    def test_clear_selected_records(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                details = list(self.lab_details(ordtyp))
                for od, pan in zip(details[:3], (VALID_PAN, "FGHIJ5678K", "LMNOP9012Q")):
                    self.assign_pan(od, pan)
                self.open_detail(ordtyp, LAB)
                self.assertEqual(self.counter("summary-received-pan"), 3)
                popup = self.page.locator("#all-confirmation-popup")
                first, second, third = self.ids[0], self.ids[1], self.ids[2]

                self.log("clear with nothing selected -> error popup", indent=2)
                self.page.locator("#clear_records_btn").click()
                expect(self.page.locator("#all-messages-popup")).to_contain_text("select at least one record")

                self.log("select 2 rows -> Cancel keeps the PANs -> confirm clears only those 2", indent=2)
                self.page.reload()
                settle(self.page)
                self.page.locator(f".row_checkbox[data-row-id='{first}']").check()
                self.page.locator(f".row_checkbox[data-row-id='{second}']").check()
                self.page.locator("#clear_records_btn").click()
                expect(popup).to_have_class(re.compile(r"\bshow\b"))
                expect(popup.locator("#confirmation-message")).to_contain_text("2 selected record")
                popup.get_by_role("button", name="Cancel").click()
                expect(popup).to_be_hidden()
                self.assertEqual(self.pans_in_db(ordtyp), [VALID_PAN, "FGHIJ5678K", "LMNOP9012Q", None])
                self.assertEqual(self.pan_input(0).input_value(), VALID_PAN)
                self.assertEqual(self.pan_on_screen()[first], VALID_PAN)

                # confirm -> those two are cleared in DB and UI, the third keeps its PAN
                self.page.locator("#clear_records_btn").click()
                expect(popup).to_have_class(re.compile(r"\bshow\b"))
                with self.page.expect_navigation():
                    popup.locator("#confirm-proceed-btn").click()
                settle(self.page)
                self.assertEqual(self.pans_in_db(ordtyp), [None, None, "LMNOP9012Q", None])
                shown = self.pan_on_screen()
                self.assertEqual([shown[i] for i in self.ids], ["", "", "LMNOP9012Q", ""])
                self.assertEqual(self.counter("summary-received-pan"), 1)
        self.assertEqual(self.js_errors, [])

    # ======================================================================================
    # 5. Bulk PAN CSV upload
    # ======================================================================================
    CSV_HEADER = ["GroupName", "OrderCategory", "InvestorType", "Rate", "PANNo", "ClientName",
                  "AllotedQty", "DematNumber", "ApplicationNumber", "OrderDate", "OrderTime", "Remark"]

    def lab_csv_row(self, ordtyp, pan, name="Client One"):
        investor, rate = ("RETAIL", 111) if ordtyp == "BUY" else ("SHNI", 222)
        return [LAB, "Kostak", investor, rate, pan, name, "", "", "", "2026-01-20", "10:00:00", ""]

    def write_csv(self, folder, name, rows, header=None):
        path = os.path.join(folder, name)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header or self.CSV_HEADER)
            w.writerows(rows)
        return path

    def open_bulk_modal(self):
        self.page.get_by_role("button", name=re.compile(r"Bulk\s*Upload")).click()
        modal = self.page.locator("#exampleModal")
        expect(modal).to_have_class(re.compile(r"\bshow\b"))
        return modal

    def test_bulk_upload_without_file_shows_validation(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, LAB)
                modal = self.open_bulk_modal()
                expect(modal).to_contain_text("Only accepts CSV files")
                self.page.evaluate("window.__sentinel = 1")
                modal.get_by_role("button", name=re.compile("Upload")).click()
                self.page.wait_for_timeout(500)
                self.assertEqual(self.page.evaluate("window.__sentinel"), 1, "must not submit")
                expect(modal.locator("form")).to_have_class(re.compile(r"was-validated"))
                expect(modal.locator(".invalid-feedback")).to_be_visible()
                expect(modal.locator(".invalid-feedback")).to_have_text("Choose Your File.")
                self.assertEqual(self.pans_in_db(ordtyp), [None] * 4)

    def test_bulk_upload_rejects_non_csv_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for ordtyp in ORDER_TYPES:
                for ext in ("txt", "png"):
                    with self.subTest(ordtyp=ordtyp, ext=ext):
                        self.reset_labs()
                        self.open_detail(ordtyp, LAB)
                        path = os.path.join(tmp, f"pans.{ext}")
                        with open(path, "wb") as f:
                            f.write(b"not a csv")
                        modal = self.open_bulk_modal()
                        modal.locator('input[name=" file"]').set_input_files(path)
                        with self.page.expect_navigation():
                            modal.get_by_role("button", name=re.compile("Upload")).click()
                        popup = self.page.locator("#all-messages-popup")
                        expect(popup).to_contain_text("Please upload a valid CSV file.")
                        expect(self.page.locator("#messageModalLabel")).to_have_text("Errors")
                        self.assertEqual(self.pans_in_db(ordtyp), [None] * 4)

    def upload_expecting_error_csv(self, path):
        """Upload, then catch the 'Download Error CSV' the page offers (it auto-clicks after 1s)."""
        modal = self.open_bulk_modal()
        modal.locator('input[name=" file"]').set_input_files(path)
        with self.page.expect_download(timeout=15000) as info:
            modal.get_by_role("button", name=re.compile("Upload")).click()
        download = info.value
        self.assertRegex(download.suggested_filename, r"^Errors_in_Upload-.*\.csv$")
        text = open(download.path(), encoding="utf-8-sig").read()
        return list(csv.reader(io.StringIO(text)))

    def test_bulk_upload_csv_missing_the_pan_column(self):
        """The upload is positional (header names are not read). Dropping the PAN column shifts every
        value left, so the client name lands in the PAN slot and each row is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            for ordtyp in ORDER_TYPES:
                with self.subTest(ordtyp=ordtyp):
                    self.reset_labs()
                    self.open_detail(ordtyp, LAB)
                    header = [h for h in self.CSV_HEADER if h != "PANNo"]
                    rows = []
                    for _ in range(2):
                        full = self.lab_csv_row(ordtyp, VALID_PAN)
                        del full[4]                                          # drop the PAN column
                        rows.append(full)
                    path = self.write_csv(tmp, "no_pan_column.csv", rows, header=header)
                    error_rows = self.upload_expecting_error_csv(path)
                    self.assertEqual(error_rows[0][0], "CSV Row #")
                    self.assertEqual(len(error_rows) - 1, 2)
                    self.assertTrue(all("Invalid or missing PAN" in r[-1] for r in error_rows[1:]), error_rows)
                    self.assertEqual(self.pans_in_db(ordtyp), [None] * 4, "database must not change")
                    expect(self.page.locator("#all-messages-popup")).to_contain_text("Invalid or missing PAN")

    def test_bulk_upload_truncated_rows_are_rejected(self):
        """Rows with fewer than the 11 required columns are reported and nothing is saved."""
        with tempfile.TemporaryDirectory() as tmp:
            for ordtyp in ORDER_TYPES:
                with self.subTest(ordtyp=ordtyp):
                    self.reset_labs()
                    self.open_detail(ordtyp, LAB)
                    rows = [self.lab_csv_row(ordtyp, VALID_PAN)[:6] for _ in range(2)]
                    path = self.write_csv(tmp, "truncated.csv", rows)
                    error_rows = self.upload_expecting_error_csv(path)
                    self.assertEqual(len(error_rows) - 1, 2)
                    self.assertTrue(all("Insufficient columns" in r[-1] for r in error_rows[1:]), error_rows)
                    self.assertEqual(self.pans_in_db(ordtyp), [None] * 4)

    def test_bulk_upload_applies_valid_rows_and_offers_error_csv_for_invalid_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            for ordtyp in ORDER_TYPES:
                with self.subTest(ordtyp=ordtyp):
                    self.reset_labs()
                    self.open_detail(ordtyp, LAB)
                    rows = [self.lab_csv_row(ordtyp, VALID_PAN),
                            self.lab_csv_row(ordtyp, "12345"),               # invalid format
                            self.lab_csv_row(ordtyp, "ABCDEFGHIJ")]          # invalid format
                    path = self.write_csv(tmp, "mixed.csv", rows)
                    error_rows = self.upload_expecting_error_csv(path)
                    self.assertEqual(len(error_rows) - 1, 2, "only the two invalid rows are reported")
                    self.assertEqual([r[0] for r in error_rows[1:]], ["3", "4"])      # file line numbers (header = line 1)
                    self.assertTrue(all("Invalid or missing PAN" in r[-1] for r in error_rows[1:]))
                    # the valid row WAS applied
                    self.assertEqual(self.pans_in_db(ordtyp).count(VALID_PAN), 1)
                    self.assertEqual(sum(p is not None for p in self.pans_in_db(ordtyp)), 1)
                    expect(self.page.locator("#downloadErrorCsvButton")).to_be_attached()
                    self.assertEqual(self.counter("summary-received-pan"), 1)

    def test_bulk_upload_valid_csv_fills_every_pending_row(self):
        pans = [VALID_PAN, "FGHIJ5678K", "LMNOP9012Q", "RSTUV3456W"]
        with tempfile.TemporaryDirectory() as tmp:
            for ordtyp in ORDER_TYPES:
                with self.subTest(ordtyp=ordtyp):
                    self.reset_labs()
                    self.open_detail(ordtyp, LAB)
                    self.assertEqual(self.counter("summary-pending-pan"), 4)
                    path = self.write_csv(tmp, "valid.csv",
                                          [self.lab_csv_row(ordtyp, p, f"Client {i}") for i, p in enumerate(pans)])
                    modal = self.open_bulk_modal()
                    modal.locator('input[name=" file"]').set_input_files(path)
                    # record the button text right after the page's own submit handler ran
                    self.page.evaluate("""() => { const f = document.querySelector('#exampleModal form');
                        f.addEventListener('submit', () => { sessionStorage.setItem('uploadBtn',
                            f.querySelector('button[type=submit]').innerHTML); }); }""")
                    with self.page.expect_navigation():
                        modal.get_by_role("button", name=re.compile("Upload")).click()
                    settle(self.page)
                    self.assertIn("Processing...", self.page.evaluate("sessionStorage.getItem('uploadBtn')"))
                    self.assertEqual(sorted(self.pans_in_db(ordtyp)), sorted(pans))
                    names = {od.OrderDetailPANNo.PANNo: od.OrderDetailPANNo.Name
                             for od in self.lab_details(ordtyp).select_related("OrderDetailPANNo")}
                    self.assertEqual(names[VALID_PAN], "CLIENT 0")
                    self.assertEqual(sorted(r["pan"] for r in self.rows()), sorted(pans))
                    self.assertEqual(self.counter("summary-received-pan"), 4)
                    self.assertEqual(self.counter("summary-pending-pan"), 0)

    # ======================================================================================
    # 6. Firm allotment
    # ======================================================================================
    def open_firm_allotment(self):
        button = self.page.get_by_role("button", name="Firm Allotment")
        if button.count() == 0:
            self.skipTest("Firm Allotment is replaced by 'Check Allotment' for premium users")
        button.click()
        modal = self.page.locator("#editbtn")
        expect(modal).to_have_class(re.compile(r"\bshow\b"))
        return modal

    def test_firm_allotment_rejects_invalid_quantity(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.open_detail(ordtyp)
                self.open_firm_allotment()
                qty, submit = self.page.locator("#AllotedQty"), self.page.locator("#submit-btn")
                for bad in (".", ".."):
                    qty.fill(bad)
                    expect(qty).to_have_class(re.compile(r"is-invalid"))
                    expect(submit).to_be_disabled()
                # letters are stripped by the field itself, leaving an empty (valid) value
                qty.fill("abc")
                self.assertEqual(qty.input_value(), "")
                qty.fill("12.5.6")
                self.assertNotIn("a", qty.input_value())
                qty.fill("100")
                expect(qty).to_have_class(re.compile(r"is-valid"))
                expect(submit).to_be_enabled()

    def test_firm_allotment_updates_the_selected_group_only(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                before = dict(self.details(ordtyp).values_list("id", "AllotedQty"))
                other = "SELL" if ordtyp == "BUY" else "BUY"
                other_before = dict(self.details(other).values_list("id", "AllotedQty"))
                try:
                    self.open_detail(ordtyp)
                    self.open_firm_allotment()
                    self.page.select_option("#category3", "ALPHA TRADERS")
                    self.page.fill("#AllotedQty", "100")
                    expect(self.page.locator("#submit-btn")).to_be_enabled()
                    with self.page.expect_navigation():
                        self.page.locator("#submit-btn").click()
                    settle(self.page)
                    for od in self.details(ordtyp).select_related("Order__OrderGroup"):
                        if od.Order.OrderGroup.GroupName == "ALPHA TRADERS":
                            self.assertEqual(od.AllotedQty, 100.0, f"ALPHA row {od.id}")
                        else:
                            self.assertEqual(od.AllotedQty, before[od.id], f"row {od.id} must be untouched")
                    self.assertEqual(dict(self.details(other).values_list("id", "AllotedQty")), other_before,
                                     f"firm allotment on {ordtyp} must not touch {other} applications")
                finally:
                    for od_id, qty in before.items():                          # leave the data as found
                        OrderDetail.objects.filter(id=od_id).update(AllotedQty=qty)

    # ======================================================================================
    # 7. Net Required / All Transactions
    # ======================================================================================
    def test_view_toggle_net_required_vs_all_transactions(self):
        self.reset_labs()
        for ordtyp, total, settled in (("BUY", 3, 2), ("SELL", 2, 2)):
            with self.subTest(ordtyp=ordtyp):
                self.set_view_mode("net")
                try:
                    self.open_detail(ordtyp, NET_LAB)
                    expect(self.page.locator("#viewModeGroup")).to_be_visible()
                    expect(self.page.locator("#btnViewNet")).to_have_class(re.compile(r"\bactive\b"))

                    self.log(f"{NET_LAB}: {total} applications, {settled} settled -> Net Required / All Transactions", indent=2)
                    self.page.locator("#btnViewNet").click()
                    self.ajax_wait()
                    net = self.rows()
                    self.assertFalse(any(r["squared"] for r in net), "settled rows hidden in Net mode")
                    self.assertEqual(len(net), total - settled)
                    expect(self.page.locator("#btnViewNet")).to_have_class(re.compile(r"\bactive\b"))
                    self.assertEqual(self.counter("summary-app-total"), total)         # counters stay gross
                    self.assertEqual(self.counter("summary-pending-pan"), total - settled)

                    self.page.locator("#btnViewGross").click()
                    self.ajax_wait()
                    gross = self.rows()
                    self.assertEqual(len(gross), total, "every transaction shown in Gross mode")
                    self.assertEqual(sum(r["squared"] for r in gross), settled)
                    expect(self.page.locator("#btnViewGross")).to_have_class(re.compile(r"\bactive\b"))
                    expect(self.page.locator("#btnViewNet")).not_to_have_class(re.compile(r"\bactive\b"))
                    self.assertTrue(all(self.page.locator(f"tr[data-squared-off='true']").nth(i).is_visible()
                                        for i in range(settled)))
                    # settled rows are marked by their placeholder ("Enter PAN | Settled")
                    expect(self.page.locator("#sortable-table input[placeholder*='Settled']")).to_have_count(settled)

                    self.page.locator("#btnViewNet").click()                          # and back again
                    self.ajax_wait()
                    self.assertEqual(len(self.rows()), total - settled)
                finally:
                    self.set_view_mode("net")
        self.assertEqual(self.js_errors, [])

    def test_view_toggle_is_hidden_when_nothing_is_settled(self):
        self.reset_labs()
        self.open_detail("BUY", LAB)
        expect(self.page.locator("#viewModeGroup")).to_be_hidden()
        self.assertEqual(self.page.locator("#summary-net-badge").count(), 0)

    # ======================================================================================
    # 8. Downloads and pagination
    # ======================================================================================
    def test_download_modal_links_follow_active_filters(self):
        """'All Record' = every application matching the filters; 'Pending PAN' = only the open ones
        (no PAN yet and not settled against the opposite side)."""
        self.reset_labs()
        group, category = "ALPHA TRADERS", "Kostak"
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.open_detail(ordtyp)
                self.pick("#category", value=group)
                self.pick("#category1", value=category)
                want_all = self.details(ordtyp).filter(
                    Order__OrderGroup__GroupName=group, Order__OrderCategory=category).count()
                want_pending = self.expected_summary(ordtyp, group=group, category=category)["pending"]
                self.assertGreater(want_all, 0)

                for kind, route, want in (("all-single", "download-AllRecords-csv", want_all),
                                          ("pending-single", "download-csv", want_pending)):
                    self.page.get_by_role("button", name=re.compile(r"^Download")).first.click()
                    modal = self.page.locator("#exampleModals")
                    expect(modal).to_have_class(re.compile(r"\bshow\b"))
                    expect(modal).to_contain_text("All Record")
                    expect(modal).to_contain_text("Pending PAN")
                    with self.page.expect_download() as info:
                        modal.locator(f"a[onclick*='{kind}']").click()
                    download = info.value
                    # the link was rebuilt from the ACTIVE filters
                    self.assertIn(f"/{route}/{ordtyp}/{quote(group)}/{quote(category)}/All/", download.url)
                    self.assertTrue(download.suggested_filename.endswith(".csv"), download.suggested_filename)
                    text = open(download.path(), encoding="utf-8-sig", errors="replace").read()
                    data = [r for r in csv.reader(io.StringIO(text)) if r][1:]
                    self.assertEqual(len(data), want, f"{kind}: rows in the CSV")
                    self.assertEqual({r[0] for r in data} - {group}, set(), f"{kind} ignored the group filter")
                    self.assertEqual({r[1] for r in data} - {category}, set(), f"{kind} ignored the category filter")
                    self.page.reload()
                    settle(self.page)
                    self.pick("#category", value=group)
                    self.pick("#category1", value=category)

    def test_page_size_changes_row_count(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, PAGE_LAB)                    # 60 applications in one group
                self.assertEqual(self.counter("summary-app-total"), 60)
                self.log("60 applications: page size 50 -> 100 -> All", indent=2)
                self.pick("#page_size", value="50")
                self.assertEqual(len(self.rows()), 50)
                expect(self.page.locator(".pagination .page-link", has_text="2").first).to_be_visible()
                self.pick("#page_size", value="100")
                self.assertEqual(len(self.rows()), 60)
                self.pick("#page_size", value="All")
                self.assertEqual(len(self.rows()), 60)
                self.assertEqual(self.table_signature(), self.db_signature(self.lab_details(ordtyp, PAGE_LAB)))
                expect(self.page.locator("#row-info-text")).to_contain_text("60")
        self.assertEqual(self.js_errors, [])

    def test_out_of_range_page_number_is_handled(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.log("bad page numbers must fall back to a real page (no 500)", indent=2)
                for query in ("?page=9999", "?page=0", "?page=abc", "?page=-3"):
                    with self.subTest(query=query):
                        response = self.page.goto(self.url(ordtyp, PAGE_LAB, query=query))
                        settle(self.page)
                        self.assertLess(response.status, 500, f"{query} must not be a server error")
                        self.assertEqual(response.status, 200)
                        expect(self.page.locator("#sortable-table")).to_be_visible()
                        self.assertGreater(len(self.rows()), 0, "falls back to a real page")
        self.assertEqual(self.js_errors, [])

    # ======================================================================================
    # 9. Shareholder-quota PAN rule
    #
    # An investor holding parent-company shares may bid twice on one PAN:
    #   - one STANDARD application (Retail / SHNI / BHNI), and
    #   - one SHAREHOLDER application (Retail only, marked "Shareholder Application").
    # Anything else (two standard, or two shareholder, applications on one PAN) is a duplicate.
    # The rule lives in validatePANs() (browser), process_data()/handle_single_row() (server)
    # and OrderDetail_upload() (CSV).
    # ======================================================================================
    def pan_by_id(self, od_id):
        return self.page.locator(f"#PAN_{od_id}")

    def open_sh(self, ordtyp, query="", group=SH):
        self.page.goto(self.url(ordtyp, group, query=query) if group else self.url(ordtyp, query=query))
        settle(self.page)
        expect(self.page.locator("#sortable-table")).to_be_visible()

    def fill_pans(self, assignments):
        for od_id, pan in assignments.items():
            self.pan_by_id(od_id).fill(pan)

    def saved_pan(self, od_id):
        od = OrderDetail.objects.select_related("OrderDetailPANNo").get(id=od_id)
        return od.OrderDetailPANNo.PANNo if od.OrderDetailPANNo else None

    def assert_update_accepted(self, assignments):
        """No duplicate warning: the update goes through and exactly these PANs are saved."""
        self.fill_pans(assignments)
        self.click_update_and_wait()
        for od_id, pan in assignments.items():
            self.assertEqual(self.saved_pan(od_id), pan, f"application {od_id}")

    def assert_update_flagged_as_duplicate(self, assignments, pan=VALID_PAN):
        """The duplicate warning appears, the rows are highlighted and nothing is saved."""
        self.fill_pans(assignments)
        self.click_update_expect_blocked()
        modal = self.page.locator("#duplicatePanModal")
        expect(modal).to_have_class(re.compile(r"\bshow\b"))
        expect(modal.locator("#duplicate-pan-list")).to_have_text(pan)
        for od_id in assignments:
            self.assertEqual(self.pan_by_id(od_id).evaluate("el => getComputedStyle(el).backgroundColor"),
                             "rgb(254, 215, 215)", f"application {od_id} should be highlighted")
            self.assertIsNone(self.saved_pan(od_id), f"application {od_id} must not be saved")
        modal.get_by_role("button", name="Fix Row(s)").click()
        expect(modal).to_be_hidden()

    def test_shareholder_rule_one_standard_plus_one_shareholder_is_allowed(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                ids = self.sh_ids(ordtyp)
                self.open_sh(ordtyp)
                self.log("same PAN on a standard RETAIL row and a shareholder RETAIL row -> accepted")
                self.assert_update_accepted({ids["std"][0]: VALID_PAN, ids["sh"][0]: VALID_PAN})
                self.assertEqual(self.pans_in_db(ordtyp, SH).count(VALID_PAN), 2)
        self.assertEqual(self.js_errors, [])

    def test_shareholder_rule_two_standard_applications_are_duplicates(self):
        for ordtyp in ORDER_TYPES:
            ids = self.sh_ids(ordtyp)
            for label, pair in (("two RETAIL standard rows", (ids["std"][0], ids["std"][1])),
                                ("RETAIL standard + SHNI row (also standard)", (ids["std"][0], ids["shni"][0]))):
                with self.subTest(ordtyp=ordtyp, case=label):
                    self.reset_labs()
                    self.open_sh(ordtyp)
                    self.assert_update_flagged_as_duplicate({pair[0]: VALID_PAN, pair[1]: VALID_PAN})

    def test_shareholder_rule_two_shareholder_applications_are_duplicates(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                ids = self.sh_ids(ordtyp)
                self.open_sh(ordtyp)
                self.assert_update_flagged_as_duplicate({ids["sh"][0]: VALID_PAN, ids["sh"][1]: VALID_PAN})

    def test_shareholder_rule_is_retail_only(self):
        """A SHNI application carrying a 'Shareholder Application' remark is NOT a quota application."""
        for ordtyp in ORDER_TYPES:
            ids = self.sh_ids(ordtyp)
            with self.subTest(ordtyp=ordtyp, case="SHNI (remark) + RETAIL shareholder -> allowed"):
                self.reset_labs()
                self.open_sh(ordtyp)
                self.assert_update_accepted({ids["shni"][0]: VALID_PAN, ids["sh"][0]: VALID_PAN})
            with self.subTest(ordtyp=ordtyp, case="SHNI (remark) + RETAIL standard -> duplicate"):
                self.reset_labs()
                self.open_sh(ordtyp)
                self.assert_update_flagged_as_duplicate({ids["shni"][0]: VALID_PAN, ids["std"][0]: VALID_PAN})

    def test_shareholder_rule_against_applications_not_on_the_page(self):
        """The same rule applies to PANs already saved on rows that are filtered out of the page."""
        for ordtyp in ORDER_TYPES:
            ids, base = self.sh_ids(ordtyp), self.SH_BASE[ordtyp]
            cases = [
                # (description, row already holding the PAN, rate filter, row typed into, expect duplicate?)
                ("saved shareholder + new standard", ids["sh"][0], base + 1, ids["std"][0], False),
                ("saved standard (SHNI) + new standard", ids["shni"][0], base + 1, ids["std"][0], True),
                ("saved standard + new shareholder", ids["std"][0], base + 2, ids["sh"][0], False),
                ("saved shareholder (other group) + new shareholder", ids["fam_sh"][0], base + 2, ids["sh"][0], True),
            ]
            for label, saved_on, rate, typed_on, expect_dup in cases:
                with self.subTest(ordtyp=ordtyp, case=label):
                    self.reset_labs()
                    self.assign_pan(OrderDetail.objects.get(id=saved_on), VALID_PAN, group=SH)
                    self.open_sh(ordtyp, query=f"?RateFilterValue={rate}")
                    self.assertEqual(self.page.locator(f"#PAN_{saved_on}").count(), 0, "saved row must be off-page")
                    if expect_dup:
                        self.assert_update_flagged_as_duplicate({typed_on: VALID_PAN})
                    else:
                        self.assert_update_accepted({typed_on: VALID_PAN})

    def post_pan_update(self, ordtyp, assignments):
        """Send the same request the Update button sends, WITHOUT the browser-side validation."""
        token = self.page.locator("input[name=csrfmiddlewaretoken]").first.input_value()
        form = {"csrfmiddlewaretoken": token}
        for od_id, pan in assignments.items():
            rate = OrderDetail.objects.get(id=od_id).Order.Rate
            form[f"PAN_{od_id}_{rate}_____"] = pan            # PAN_<id>_<rate>_<panid>_<qty>_<demat>_<app>_<name>
        response = self.page.request.post(
            f"{self.live_server_url}/{self.ipo.id}/{ordtyp}/update_pann/All/All/All?page=1",
            form=form, headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_server_enforces_the_shareholder_rule_when_javascript_is_bypassed(self):
        """The server drops a conflicting row (silently - there is no error message)."""
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                ids = self.sh_ids(ordtyp)
                self.open_sh(ordtyp)
                steps = [
                    ("first standard", ids["std"][0], True),
                    ("second standard (same type) -> dropped", ids["std"][1], False),
                    ("SHNI standard (same type) -> dropped", ids["shni"][0], False),
                    ("first shareholder (other type) -> saved", ids["sh"][0], True),
                    ("second shareholder (same type) -> dropped", ids["sh"][1], False),
                ]
                for label, od_id, should_save in steps:
                    self.post_pan_update(ordtyp, {od_id: VALID_PAN})
                    self.assertEqual(self.saved_pan(od_id), VALID_PAN if should_save else None, label)
                    self.log(f"{label}: {'saved' if should_save else 'rejected by the server'}", indent=2)

    @unittest.expectedFailure
    def test_shareholder_detection_ignores_words_elsewhere_in_the_row(self):
        """KNOWN APP BUG (suspected from the code, confirmed here): validatePANs() treats a RETAIL row as
        a shareholder application if ANY text in the row contains 'shareholder' (it falls back to
        tr.textContent), e.g. a group named 'SHAREHOLDER FAMILY'. The server only looks at the remark.
        So two STANDARD rows on one PAN pass the browser check, and the server then silently drops one.
        Asserts the CORRECT behaviour (duplicate warning); 'unexpected success' once fixed."""
        ordtyp = "BUY"
        self.reset_labs()
        ids = self.sh_ids(ordtyp)
        rate = self.SH_BASE[ordtyp] + 1                    # SH LAB standard row and SHAREHOLDER FAMILY standard row
        self.open_sh(ordtyp, query=f"?RateFilterValue={rate}", group=None)
        self.fill_pans({ids["std"][0]: VALID_PAN, ids["fam_std"][0]: VALID_PAN})
        self.page.locator("#main-update-btn").click()
        expect(self.page.locator("#duplicatePanModal")).to_have_class(re.compile(r"\bshow\b"), timeout=3000)

    def sh_csv_row(self, ordtyp, kind, pan):
        base, cat = self.SH_BASE[ordtyp], self.SH_CATEGORY[ordtyp]
        investor, rate, remark = {"std": ("RETAIL", base + 1, ""),
                                  "sh": ("RETAIL", base + 2, "Shareholder Application"),
                                  "shni": ("SHNI", base + 3, "Shareholder Application")}[kind]
        return [SH, cat, investor, rate, pan, "Client X", "", "", "", "2026-01-20", "10:00:00", remark]

    def test_csv_upload_applies_the_shareholder_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            for ordtyp in ORDER_TYPES:
                ids = self.sh_ids(ordtyp)
                with self.subTest(ordtyp=ordtyp, case="standard + shareholder on one PAN -> both applied"):
                    self.reset_labs()
                    self.open_sh(ordtyp)
                    path = self.write_csv(tmp, "ok.csv", [self.sh_csv_row(ordtyp, "std", VALID_PAN),
                                                          self.sh_csv_row(ordtyp, "sh", VALID_PAN)])
                    modal = self.open_bulk_modal()
                    modal.locator('input[name=" file"]').set_input_files(path)
                    with self.page.expect_navigation():
                        modal.get_by_role("button", name=re.compile("Upload")).click()
                    settle(self.page)
                    self.assertEqual(self.pans_in_db(ordtyp, SH).count(VALID_PAN), 2)
                for case, kinds, reason in (
                        ("two standard rows -> second rejected", ("std", "std"), "Duplicate standard application"),
                        ("two shareholder rows -> second rejected", ("sh", "sh"), "Duplicate shareholder application")):
                    with self.subTest(ordtyp=ordtyp, case=case):
                        self.reset_labs()
                        self.open_sh(ordtyp)
                        path = self.write_csv(tmp, "dup.csv", [self.sh_csv_row(ordtyp, k, VALID_PAN) for k in kinds])
                        error_rows = self.upload_expecting_error_csv(path)
                        self.assertEqual(len(error_rows) - 1, 1)
                        self.assertIn(reason, error_rows[1][-1])
                        self.assertEqual(self.pans_in_db(ordtyp, SH).count(VALID_PAN), 1)

    # ======================================================================================
    # 10. Pending PAN amount -> CSV download
    # ======================================================================================
    PENDING_HEADER = ["Group", "Order Category", "Investor Type", "Rate", "PAN No", "Client Name", "Alloted Qty",
                      "Demat Number", "Application Number", "Order Date", " Order Time", "Remark"]

    def click_pending_and_read_csv(self):
        shown = self.counter("summary-pending-pan")
        with self.page.expect_download() as info:
            self.page.locator("#summary-pending-pan").click()
        download = info.value
        self.assertEqual(download.suggested_filename, f"{IPO_NAME}-OrderDetail.csv")
        text = open(download.path(), encoding="utf-8-sig", errors="replace").read()
        rows = [r for r in csv.reader(io.StringIO(text)) if r]
        self.assertEqual(rows[0], self.PENDING_HEADER)
        return shown, rows[1:]

    def test_clicking_pending_pan_downloads_a_csv_of_the_pending_applications(self):
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, LAB)
                shown, rows = self.click_pending_and_read_csv()
                self.log(f"{LAB}: counter shows {shown}, CSV has {len(rows)} rows", indent=2)
                self.assertEqual((shown, len(rows)), (4, 4))
                self.assertEqual({r[0] for r in rows}, {LAB})
                self.assertEqual({r[4] for r in rows}, {""}, "pending rows have no PAN yet")
                self.assertEqual({float(r[3]) for r in rows}, {111.0 if ordtyp == "BUY" else 222.0})

                # once a PAN is saved that application leaves the pending list
                self.assign_pan(self.lab_details(ordtyp).first(), VALID_PAN)
                self.open_detail(ordtyp, LAB)
                shown, rows = self.click_pending_and_read_csv()
                self.assertEqual((shown, len(rows)), (3, 3))
                self.assertNotIn(VALID_PAN, [r[4] for r in rows])

    def test_pending_pan_csv_leaves_out_settled_applications(self):
        """NET LAB: 3 BUY vs 2 SELL on one key -> BUY has 1 open application, SELL has none."""
        for ordtyp, open_apps in (("BUY", 1), ("SELL", 0)):
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, NET_LAB)
                shown, rows = self.click_pending_and_read_csv()
                self.log(f"{NET_LAB}: counter shows {shown}, CSV has {len(rows)} rows (settled ones excluded)", indent=2)
                self.assertEqual((shown, len(rows)), (open_apps, open_apps))

    @unittest.expectedFailure
    def test_pending_pan_link_follows_filters_changed_on_the_page(self):
        """KNOWN APP BUG: the Pending PAN link is rendered once by the server; the AJAX filter bar updates
        only the NUMBER, not the link. After choosing a group the page says e.g. 4, but clicking downloads
        the whole IPO's pending list (73 rows in my run). The Download modal does it right
        (downloadWithActiveFilters reads the current selects); the link should do the same.
        Asserts the CORRECT behaviour; 'unexpected success' once fixed."""
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp)
                self.pick("#category", value=LAB)
                shown, rows = self.click_pending_and_read_csv()
                self.log(f"after filtering to {LAB}: counter shows {shown}, CSV has {len(rows)} rows", indent=2)
                self.assertEqual(shown, 4)
                self.assertEqual(len(rows), shown)
                self.assertEqual({r[0] for r in rows}, {LAB})

    # ======================================================================================
    # 11. Alloted Qty of settled applications
    # ======================================================================================
    def allotted_inputs(self):
        return self.page.evaluate("""() => Object.fromEntries([...document.querySelectorAll("input[name^='allotedqty_']")]
            .map(i => [i.name.split('_')[1], i.value]))""")

    def test_settled_applications_show_zero_allotted_qty_by_default(self):
        """Settled (squared-off) applications with no stored quantity show 0; open ones stay empty; the 0
        is a display default (nothing is written to the database); a stored quantity is never overwritten."""
        for ordtyp, total, settled in (("BUY", 3, 2), ("SELL", 2, 2)):
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp, NET_LAB, query="?view_mode=gross")
                rows, shown = self.rows(), self.allotted_inputs()
                self.assertEqual((len(rows), sum(r["squared"] for r in rows)), (total, settled))
                for r in rows:
                    want = "0" if r["squared"] else ""
                    self.assertEqual(shown[r["id"]], want, f"{'settled' if r['squared'] else 'open'} row {r['id']}")
                self.assertFalse(self.lab_details(ordtyp, NET_LAB).exclude(AllotedQty=None).exists(),
                                 "the default 0 must not be saved")
                self.log(f"settled rows show 0, open rows empty, nothing saved ({settled} settled of {total})", indent=2)

                # a stored quantity wins over the default
                settled_ids = [int(r["id"]) for r in rows if r["squared"]]
                OrderDetail.objects.filter(id=settled_ids[0]).update(AllotedQty=5)
                self.open_detail(ordtyp, NET_LAB, query="?view_mode=gross")
                shown = self.allotted_inputs()
                self.assertEqual(shown[str(settled_ids[0])], "5")
                if len(settled_ids) > 1:
                    self.assertEqual(shown[str(settled_ids[1])], "0")

    def test_saving_a_pan_does_not_write_the_default_zero_for_settled_applications(self):
        self.reset_labs()
        self.open_detail("BUY", NET_LAB, query="?view_mode=gross")
        rows = self.rows()
        open_id = int(next(r["id"] for r in rows if not r["squared"]))
        self.pan_by_id(open_id).fill(VALID_PAN)
        self.click_update_and_wait()
        self.assertEqual(self.saved_pan(open_id), VALID_PAN)
        for r in rows:
            if r["squared"]:
                self.assertIsNone(OrderDetail.objects.get(id=r["id"]).AllotedQty, "settled row must stay unset")

    # ======================================================================================
    # 7. Filters survive a PAN save and a bulk upload
    # ======================================================================================
    def apply_lab_filters(self, ordtyp):
        """Group + category + investor + rate, set through the filter bar (all of it AJAX, no page load)."""
        investor, rate = ("RETAIL", 111.0) if ordtyp == "BUY" else ("SHNI", 222.0)
        self.pick("#category", value=LAB)
        self.pick("#category1", value="Kostak")
        self.pick("#category2", value=investor)
        values = self.page.eval_on_selector_all("#frate option", "els => els.map(e => e.value)")
        self.pick("#frate", value=next(v for v in values if v != "All" and float(v) == rate))
        return dict(group=LAB, category="Kostak", investor=investor, rate=rate)

    def assert_filters_kept(self, ordtyp, chosen):
        """The four selects still hold the chosen values and the table is still the filtered one."""
        expect(self.page.locator("#category")).to_have_value(chosen["group"])
        expect(self.page.locator("#category1")).to_have_value(chosen["category"])
        expect(self.page.locator("#category2")).to_have_value(chosen["investor"])
        self.assertEqual(float(self.page.locator("#frate").input_value()), chosen["rate"])
        self.assertEqual({r["group"] for r in self.rows()}, {LAB}, "other groups came back after the reload")
        self.assertEqual(self.table_signature(), self.db_signature(self.lab_details(ordtyp)))

    def test_filters_are_kept_after_adding_a_pan(self):
        """Filter, type a PAN, press Update All: the page reloads and must still be filtered."""
        for ordtyp in ORDER_TYPES:
            with self.subTest(ordtyp=ordtyp):
                self.reset_labs()
                self.open_detail(ordtyp)
                self.pick("#page_size", value="All")
                self.ids = list(self.lab_details(ordtyp).values_list("id", flat=True))
                everything = len(self.rows())
                chosen = self.apply_lab_filters(ordtyp)
                self.assertLess(len(self.rows()), everything, "the filter should narrow the table")

                self.pan_input(0).fill(VALID_PAN)
                self.click_update_and_wait()

                self.assertEqual(self.pans_in_db(ordtyp), [VALID_PAN, None, None, None])
                self.assert_filters_kept(ordtyp, chosen)
                self.assertEqual(self.counter("summary-received-pan"), 1)
                self.assertEqual(self.counter("summary-app-total"), 4)

    def test_filters_are_kept_after_a_bulk_upload(self):
        """Filter, upload a CSV of PANs: the redirect back must still be filtered."""
        pans = [VALID_PAN, "FGHIJ5678K", "LMNOP9012Q", "RSTUV3456W"]
        with tempfile.TemporaryDirectory() as tmp:
            for ordtyp in ORDER_TYPES:
                with self.subTest(ordtyp=ordtyp):
                    self.reset_labs()
                    self.open_detail(ordtyp)
                    self.pick("#page_size", value="All")
                    everything = len(self.rows())
                    chosen = self.apply_lab_filters(ordtyp)
                    self.assertLess(len(self.rows()), everything, "the filter should narrow the table")

                    path = self.write_csv(tmp, f"{ordtyp}.csv",
                                          [self.lab_csv_row(ordtyp, p, f"Client {i}") for i, p in enumerate(pans)])
                    modal = self.open_bulk_modal()
                    modal.locator('input[name=" file"]').set_input_files(path)
                    with self.page.expect_navigation():
                        modal.get_by_role("button", name=re.compile("Upload")).click()
                    settle(self.page)

                    self.assertEqual(sorted(self.pans_in_db(ordtyp)), sorted(pans))
                    self.assert_filters_kept(ordtyp, chosen)
                    self.assertEqual(self.counter("summary-received-pan"), 4)
