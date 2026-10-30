"""
Positions page E2E (/group-billing-details/ and /group-billing-details/<group id>/, templates/group_billing_details.html;
the "Positions" link in the top bar).

Runs on its OWN IPOs and groups (POS MAIN IPO - MAINBOARD, POS SME IPO - SME; groups POS ONE, POS TWO, POS EMPTY) so the
tally ticks it flips never touch the other pages. Orders are seeded with known allotments, the app's calculate() fills in
the amounts, and EVERY figure of a row is compared with an independent calculation from the raw orders
(test_cases/oracle.py). The page lists every group of the broker, so figures are checked on the single-group URL.

What the page shows, per group (a group with no orders is only named in the "No records found for" box):
  Mainboard table, one row per IPO the group has orders in:
      tally tick | IPO (link to its Status page) | Kostak Retail / SHNI / BHNI | Subject To Retail / SHNI / BHNI
      (each: Count, Alloted, Billing) | Premium shares, billing | Call amount | Put amount | Total shares "@ avg" | Total amount
  SME table (SME IPOs): tick | IPO | Kostak, Subject To (Count, Alloted, Billing) | Premium (Count, Billing) | Total share | Total amount
  Hover titles split each figure into BUY and SELL; the "Share" button opens a share dialog for that table.
Toolbar: tally filter (default "Show Untallied"; kept in localStorage 'tallyFilterIpos'), IPO multi-select, "Shares with
average" switch (localStorage 'positions_show_avg'), Active Group select. The all-groups view loads 5 populated groups at a
time and fetches the next batch (AJAX, ?offset=) when you scroll.
"""
import re
from collections import Counter

from playwright.sync_api import expect

from home.models import CurrentIpoName, GroupDetail, Order
from home.views import calculate
from test_cases import oracle
from test_cases.base import PersistentLiveServerTestCase, pause_for_inspection, settle

MAIN_IPO, SME_IPO = "POS MAIN IPO", "POS SME IPO"
ONE, TWO, EMPTY = "POS ONE", "POS TWO", "POS EMPTY"
IPO_PRICE, PRE_OPEN = 100.0, 250.0
TIERS = ("RETAIL", "SHNI", "BHNI")

# ONE is BUY heavy and has SME orders too; TWO is SELL heavy with options; EMPTY has no orders at all.
MAIN_SPECS = [
    dict(group=ONE, type="BUY", cat="Kostak", inv="RETAIL", rate=450, alloted=[10, 10, 0, None]),
    dict(group=ONE, type="BUY", cat="Kostak", inv="SHNI", rate=600, alloted=[5]),
    dict(group=ONE, type="SELL", cat="Kostak", inv="RETAIL", rate=455, alloted=[10]),
    dict(group=ONE, type="BUY", cat="Subject To", inv="RETAIL", rate=1200, alloted=[10, 10]),
    dict(group=ONE, type="BUY", cat="Subject To", inv="RETAIL", rate=5, method="Premium", alloted=[20]),
    dict(group=ONE, type="BUY", cat="Premium", inv="PREMIUM", rate=20, qty=100),
    dict(group=TWO, type="SELL", cat="Kostak", inv="RETAIL", rate=460, alloted=[10, 10, 10]),
    dict(group=TWO, type="BUY", cat="Kostak", inv="RETAIL", rate=440, alloted=[10]),
    dict(group=TWO, type="SELL", cat="Kostak", inv="BHNI", rate=700, alloted=[4]),
    dict(group=TWO, type="SELL", cat="Subject To", inv="SHNI", rate=1210, alloted=[10]),
    dict(group=TWO, type="SELL", cat="Subject To", inv="BHNI", rate=6, method="Premium", alloted=[10]),
    dict(group=TWO, type="SELL", cat="Premium", inv="PREMIUM", rate=30, qty=50),
    dict(group=TWO, type="BUY", cat="CALL", inv="OPTIONS", rate=10, qty=100, method="120"),
    dict(group=TWO, type="SELL", cat="PUT", inv="OPTIONS", rate=10, qty=100, method="200"),
]
SME_SPECS = [
    dict(group=ONE, type="BUY", cat="Kostak", inv="RETAIL", rate=300, alloted=[5, 6, None]),
    dict(group=ONE, type="SELL", cat="Kostak", inv="RETAIL", rate=310, alloted=[2]),
    dict(group=ONE, type="BUY", cat="Subject To", inv="RETAIL", rate=900, alloted=[4]),
    dict(group=ONE, type="BUY", cat="Premium", inv="PREMIUM", rate=10, qty=20),
]

TABLE_JS = """kind => [...document.querySelectorAll(`table[id^="${kind}BillingTable_"] tbody tr`)].filter(tr => !tr.querySelector('td.dataTables_empty')).map(tr => {
    const th = [...tr.querySelectorAll(':scope > th')], td = [...tr.querySelectorAll(':scope > td')];
    const tick = tr.querySelector('.ipo-archive-checkbox');
    const clean = t => t.replace(/\\s+/g, ' ').trim();
    const last = kind === 'mainboard' ? 22 : 8;
    return {ipo: clean(th[1].textContent), href: th[1].querySelector('a')?.getAttribute('href'),
            tallied: !!tick && tick.checked, archived: tr.classList.contains('archived-ipo'),
            tallyId: tick?.dataset.id, tallyGroup: tick?.dataset.group, stamp: clean(th[0].querySelector('.tally-ts-span')?.textContent || ''),
            cells: td.map(c => clean(c.childNodes[0] ? c.childNodes[0].textContent : '')),
            titles: td.map(c => c.getAttribute('title') || c.querySelector('[title]')?.getAttribute('title') || ''),
            links: td.map(c => c.querySelector('a')?.getAttribute('href') || null),
            avg: clean(td[last].querySelector('.row-avg-disp')?.textContent || ''),
            avgShown: td[last].querySelector('.row-avg-wrapper') ? getComputedStyle(td[last].querySelector('.row-avg-wrapper')).display !== 'none' : null,
            amount: clean(td[td.length - 1].textContent)};
})"""


def whole(x):
    return f"{float(x):.0f}"


def one(x):
    return f"{float(x):.1f}"


class PositionsPlaywrightTestCase(PersistentLiveServerTestCase):
    PAGE_NAME = "positions"
    _ran_any = False

    # ------------------------------------------------------------------ setup / teardown
    @classmethod
    def tearDownClass(cls):
        cls.log_summary()
        if cls._ran_any:
            try:
                cls.page.goto(f"{cls.live_server_url}/group-billing-details/")
                settle(cls.page)
            except Exception:
                pass
            pause_for_inspection(cls.PAGE_NAME)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        type(self)._ran_any = True
        base = dict(IPOPrice=IPO_PRICE, PreOpenPrice=PRE_OPEN, LotSizeRetail=100, LotSizeSHNI=1400, LotSizeBHNI=7000,
                    Active=True)
        self.main = CurrentIpoName.objects.get_or_create(user=self.user, IPOName=MAIN_IPO, defaults=dict(base, IPOType="MAINBOARD"))[0]
        self.sme = CurrentIpoName.objects.get_or_create(user=self.user, IPOName=SME_IPO, defaults=dict(base, IPOType="SME"))[0]
        self.groups = {n: GroupDetail.objects.get_or_create(user=self.user, GroupName=n)[0] for n in (ONE, TWO, EMPTY)}
        oracle.seed_specs(self.user, self.main, MAIN_SPECS, PRE_OPEN)
        oracle.seed_specs(self.user, self.sme, SME_SPECS, PRE_OPEN)
        for ipo in (self.main, self.sme):
            calculate(ipo.id, self.user)
        Order.objects.filter(user=self.user, OrderIPOName__in=[self.main, self.sme]).update(Telly="False", tally_timestamp=None)
        self.clear_local_storage()

    def tearDown(self):
        self.clear_local_storage()
        super().tearDown()

    def clear_local_storage(self):
        try:
            if self.page.url.startswith(self.live_server_url):
                self.page.evaluate("localStorage.clear()")
        except Exception:
            pass

    # ---------------------------------------------------------------------- page helpers
    def open_group(self, name):
        self.page.goto(f"{self.live_server_url}/group-billing-details/{self.groups[name].id}/")
        settle(self.page)
        expect(self.page.locator("#positionsToolbar")).to_be_visible()

    def open_all(self):
        self.page.goto(f"{self.live_server_url}/group-billing-details/")
        settle(self.page)
        expect(self.page.locator("#positionsToolbar")).to_be_visible()

    def set_tally_filter(self, value):
        self.page.select_option("#tallyFilterSelect", value)
        self.page.wait_for_timeout(300)

    def main_rows(self):
        return self.page.evaluate(TABLE_JS, "mainboard")

    def sme_rows(self):
        return self.page.evaluate(TABLE_JS, "sme")

    def main_row(self, ipo=MAIN_IPO):
        found = [r for r in self.main_rows() if r["ipo"] == ipo]
        self.assertEqual(len(found), 1, f"{ipo!r}: expected one row, got {len(found)}")
        return found[0]

    def tick(self, table_kind="mainboard"):
        return self.page.locator(f"table[id^='{table_kind}BillingTable_'] .ipo-archive-checkbox").first

    # -------------------------------------------------------- expected values
    def expected_main_cells(self, group):
        g = oracle.group_figures(self.user, self.main)[group]
        cells = []
        for cat in ("Kostak", "Subject To"):
            for tier in TIERS:
                c = g["cell"][(cat, tier)]
                cells += [whole(c["cnt_b"] - c["cnt_s"]), whole(c["al_b"] - c["al_s"]), one(c["bill_b"] + c["bill_s"])]
        cells += [whole(g["p_shares"]), one(g["p_bill"]), one(g["call"]), one(g["put"]), whole(g["total_shares"])]
        return cells, g

    # ====================================================================================
    # Page, toolbar and figures
    # ====================================================================================
    def test_page_opens_from_the_menu_with_its_toolbar(self):
        self.page.goto(f"{self.live_server_url}/")
        settle(self.page)
        with self.page.expect_navigation():
            self.page.locator("a.nav-link", has_text="Positions").first.click()
        settle(self.page)
        self.assertTrue(self.page.url.rstrip("/").endswith("/group-billing-details"))
        self.assertEqual(self.page.locator("h3.positions-title").inner_text().strip(), "Positions")
        expect(self.page.locator("#tallyFilterSelect")).to_have_value("untallied")
        self.assertEqual(self.page.locator("#tallyFilterSelect option").all_inner_texts(), ["All", "Show Tallied", "Show Untallied"])
        expect(self.page.locator("#toggleAvgRateSwitch")).to_be_checked()
        expect(self.page.locator("#ipoSelectBtnText")).to_have_text(re.compile(r"^All IPOs \(\d+\)$"))
        expect(self.page.locator("#groupSelect")).to_have_value("all")
        options = self.page.locator("#groupSelect option").all_inner_texts()
        self.assertEqual(options[0], "All Groups")
        self.assertEqual(options[1:], sorted(GroupDetail.objects.filter(user=self.user).values_list("GroupName", flat=True)))

    def test_mainboard_row_matches_the_orders_for_every_figure(self):
        for name in (ONE, TWO):
            with self.subTest(group=name):
                self.open_group(name)
                self.set_tally_filter("all")
                rows = self.main_rows()
                self.assertEqual([r["ipo"] for r in rows], [MAIN_IPO])
                row = rows[0]
                cells, g = self.expected_main_cells(name)
                self.assertEqual(row["cells"][:22], cells[:22])
                self.assertEqual(row["cells"][22], cells[22])               # total shares (the "@ avg" is its own span)
                self.assertEqual(row["amount"], whole(g["total_amount"]))
                self.assertEqual(row["avg"], g["total_avg"])
                self.assertEqual(len(row["cells"]), 24)
                self.log(f"{name}: shares {cells[22]} @ {row['avg'] or '-'}, amount {row['amount']}", indent=2)

    def test_group_with_sme_orders_gets_a_second_table(self):
        self.open_group(ONE)
        self.set_tally_filter("all")
        rows = self.sme_rows()
        self.assertEqual([r["ipo"] for r in rows], [SME_IPO])
        g = oracle.group_figures(self.user, self.sme)[ONE]
        cell = lambda cat: [sum(g["cell"][(cat, t)][k] for t in oracle.TIERS) for k in ("cnt_b", "cnt_s", "al_b", "al_s", "bill_b", "bill_s")]
        k, st = cell("Kostak"), cell("Subject To")
        expected = [whole(k[0] - k[1]), whole(k[2] - k[3]), one(k[4] + k[5]),
                    whole(st[0] - st[1]), whole(st[2] - st[3]), one(st[4] + st[5]),
                    whole(g["p_shares"]), one(g["p_bill"]), whole(g["total_shares"]), whole(g["total_amount"])]
        self.assertEqual(rows[0]["cells"], expected)
        self.assertEqual(rows[0]["amount"], whole(g["total_amount"]))
        headings = self.page.locator(".group-subtable-wrapper h4").all_inner_texts()
        self.assertEqual([h.replace("Share", "").strip() for h in headings], [f"Group : {ONE} (SME IPOs)", f"Group : {ONE}"])
        # TWO has no SME orders: only the mainboard table
        self.open_group(TWO)
        self.assertEqual(self.page.locator("table[id^='smeBillingTable_']").count(), 0)

    def test_hover_titles_split_every_figure_into_buy_and_sell(self):
        self.open_group(ONE)
        self.set_tally_filter("all")
        row = self.main_row()
        g = oracle.group_figures(self.user, self.main)[ONE]
        retail_k = g["cell"][("Kostak", "RETAIL")]
        self.assertEqual(row["titles"][0], f"BUY:{retail_k['cnt_b']:.0f}     SELL:{retail_k['cnt_s']:.0f}")
        self.assertIn(f"BUY-K: {retail_k['al_b']}", row["titles"][1])
        self.assertIn(f"SELL-K: {retail_k['al_s']}", row["titles"][1])
        self.assertEqual(row["titles"][2], f"BUY: {retail_k['bill_b']:.0f}     SELL: {retail_k['bill_s']:.0f}")
        self.assertIn(f"Kostak:{g['k_shares']:.0f}", row["titles"][22])
        self.assertIn(f"Subject To:{g['st_shares']:.0f}", row["titles"][22])
        self.assertIn(f"Premium:{g['p_shares']:.0f}", row["titles"][22])

    def test_counts_link_to_the_orders_and_the_ipo_name_to_its_status_page(self):
        self.open_group(ONE)
        self.set_tally_filter("all")
        row = self.main_row()
        self.assertEqual(row["href"], f"/{self.main.id}/Status")
        self.assertEqual(row["links"][0], f"/{self.main.id}/Order/{ONE}/Kostak/RETAIL")
        self.assertEqual(row["links"][1], None)
        self.assertEqual(row["links"][9], f"/{self.main.id}/Order/{ONE}/Subject To/RETAIL")
        self.assertEqual(row["links"][18], f"/{self.main.id}/Order/{ONE}/Premium/All")
        # a count of 0 is plain text, not a link (ONE has no BHNI Kostak orders)
        self.assertEqual(row["links"][6], None)
        with self.page.expect_navigation():
            self.page.locator(f"table[id^='mainboardBillingTable_'] a[href='/{self.main.id}/Status']").click()
        settle(self.page)
        self.assertTrue(self.page.url.endswith(f"/{self.main.id}/Status"))

    # ====================================================================================
    # Groups
    # ====================================================================================
    def test_group_select_switches_between_one_group_and_all_groups(self):
        self.open_all()
        with self.page.expect_navigation():
            self.page.select_option("#groupSelect", str(self.groups[ONE].id))
        settle(self.page)
        self.assertTrue(self.page.url.endswith(f"/group-billing-details/{self.groups[ONE].id}/"))
        expect(self.page.locator("#groupSelect")).to_have_value(str(self.groups[ONE].id))
        headings = self.page.locator(".group-subtable-wrapper h4").all_inner_texts()
        self.assertTrue(all(ONE in h for h in headings), headings)
        self.assertEqual(self.page.locator("table[id^='mainboardBillingTable_']").count(), 1)
        with self.page.expect_navigation():
            self.page.select_option("#groupSelect", "all")
        settle(self.page)
        self.assertTrue(self.page.url.rstrip("/").endswith("/group-billing-details"))
        expect(self.page.locator("#groupSelect")).to_have_value("all")

    def test_a_group_without_orders_is_named_in_the_no_records_box(self):
        self.open_group(EMPTY)
        self.assertEqual(self.page.locator("table[id^='mainboardBillingTable_']").count(), 0)
        box = self.page.locator("#emptyGroupsContainer")
        expect(box).to_be_visible()
        expect(box).to_contain_text("No records found for:")
        expect(self.page.locator("#emptyGroupsList")).to_have_text(EMPTY)

    def test_all_groups_loads_five_populated_groups_then_more_on_scroll(self):
        # the earlier pages leave plenty of groups with orders; run on its own, add enough to need a second batch
        fillers = [dict(group=f"POS FILLER {i}", type="BUY", cat="Premium", inv="PREMIUM", rate=10, qty=1) for i in range(1, 8)]
        oracle.seed_specs(self.user, self.main, fillers, PRE_OPEN)
        calculate(self.main.id, self.user)
        populated = list(GroupDetail.objects.filter(user=self.user, order__isnull=False).distinct()
                         .order_by("GroupName").values_list("GroupName", flat=True))
        self.assertGreater(len(populated), 5)
        self.set_local_filter_all()
        self.open_all()
        first = self.page.evaluate("[...document.querySelectorAll('.group-section')].length")
        self.assertEqual(self.page.locator("#groupsContainer").get_attribute("data-has-next"), "true")
        names = lambda: self.page.evaluate("""() => [...document.querySelectorAll('.group-subtable-wrapper h4')]
            .map(h => h.textContent.replace('Share', '').replace(/\\s+/g, ' ').trim().replace(/^Group : /, '').replace(/ \\(SME IPOs\\)$/, ''))""")
        initial = list(dict.fromkeys(names()))
        self.assertEqual(initial[:5], populated[:5])                              # alphabetical, five at a time
        self.assertGreaterEqual(first, 5)
        with self.page.expect_response(lambda r: "offset=" in r.url and r.request.resource_type in ("xhr", "fetch")) as info:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        body = info.value.json()
        self.assertTrue({"html", "has_next", "next_offset", "empty_groups"} <= set(body))
        self.page.wait_for_timeout(500)
        grown = list(dict.fromkeys(names()))
        self.assertGreater(len(grown), len(initial))
        self.assertEqual(grown[:len(initial)], initial)                           # appended, nothing repeated
        self.assertEqual(len(grown), len(set(grown)))

    def set_local_filter_all(self):
        """Tallied groups are hidden by the default filter; show everything so batches are predictable."""
        self.page.goto(f"{self.live_server_url}/login")
        self.page.evaluate("localStorage.setItem('tallyFilterIpos', 'all')")

    def test_another_brokers_group_id_is_not_found(self):
        reply = self.page.request.get(f"{self.live_server_url}/group-billing-details/999999/")
        self.assertEqual(reply.status, 404)

    def test_login_is_required(self):
        self.page.context.clear_cookies()
        try:
            self.page.goto(f"{self.live_server_url}/group-billing-details/")
            settle(self.page)
            self.assertIn("/login", self.page.url)
        finally:
            self.page.context.add_cookies([{"name": "sessionid", "value": self.client.cookies["sessionid"].value,
                                            "domain": "localhost", "path": "/"}])

    # ====================================================================================
    # Tally
    # ====================================================================================
    def test_tally_filter_shows_untallied_tallied_or_all(self):
        self.open_group(ONE)
        self.assertEqual(self.page.locator("#tallyFilterSelect").input_value(), "untallied")
        self.assertEqual([r["ipo"] for r in self.main_rows()], [MAIN_IPO])
        Order.objects.filter(user=self.user, OrderGroup=self.groups[ONE], OrderIPOName=self.main).update(Telly="True")
        self.open_group(ONE)
        self.set_tally_filter("untallied")
        self.assertEqual(self.main_rows(), [], "a tallied row is hidden by Show Untallied")
        self.assertEqual([r["ipo"] for r in self.sme_rows()], [SME_IPO])            # the SME row is not tallied

        self.step(1, 3, "Show Tallied")
        self.set_tally_filter("tallied")
        self.assertEqual([r["ipo"] for r in self.main_rows()], [MAIN_IPO])
        self.assertTrue(self.main_rows()[0]["tallied"])
        self.assertEqual(self.sme_rows(), [])
        self.step(2, 3, "All")
        self.set_tally_filter("all")
        self.assertEqual(len(self.main_rows()) + len(self.sme_rows()), 2)
        self.step(3, 3, "the choice is remembered")
        self.assertEqual(self.page.evaluate("localStorage.getItem('tallyFilterIpos')"), "all")
        self.open_group(ONE)
        expect(self.page.locator("#tallyFilterSelect")).to_have_value("all")
        self.assertEqual(len(self.main_rows()) + len(self.sme_rows()), 2)

    def test_ticking_a_row_tallies_that_groups_orders_only(self):
        self.open_group(ONE)
        self.set_tally_filter("all")
        tick = self.tick()
        self.assertFalse(tick.is_checked())
        with self.page.expect_request(lambda r: "/update-telly-status/" in r.url) as info:
            tick.check()
        request = info.value
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.post_data_json, {"updateType": "One", "groupname": ONE, "status": True, "IPO_id": self.main.id})
        expect(tick).to_be_enabled()
        mine = Order.objects.filter(user=self.user, OrderGroup=self.groups[ONE], OrderIPOName=self.main)
        self.assertTrue(mine.exists())
        self.assertEqual({o.Telly for o in mine}, {"True"})
        self.assertTrue(all(o.tally_timestamp for o in mine))
        other = Order.objects.filter(user=self.user, OrderGroup=self.groups[TWO], OrderIPOName=self.main)
        self.assertEqual({o.Telly for o in other}, {"False"})                        # another group, same IPO
        self.assertEqual({o.Telly for o in Order.objects.filter(user=self.user, OrderGroup=self.groups[ONE], OrderIPOName=self.sme)}, {"False"})
        row = self.main_row()
        self.assertTrue(row["archived"] and row["tallied"])
        self.assertRegex(row["stamp"], r"^\d{2}-\d{2}-\d{4}\s*\d{2}:\d{2}:\d{2}$")

        self.step(1, 2, "the tick survives a reload, and Show Untallied now hides the row")
        self.open_group(ONE)
        self.set_tally_filter("untallied")
        self.assertEqual(self.main_rows(), [])
        self.set_tally_filter("tallied")
        self.assertTrue(self.main_row()["tallied"])

        self.step(2, 2, "unticking clears it again")
        self.set_tally_filter("all")                                                 # keep the row on screen while it flips
        with self.page.expect_request(lambda r: "/update-telly-status/" in r.url) as info:
            self.tick().uncheck()
        self.assertEqual(info.value.post_data_json["status"], False)
        self.page.wait_for_timeout(500)
        self.assertEqual({o.Telly for o in mine.all()}, {"False"})
        self.set_tally_filter("untallied")
        self.assertEqual([r["ipo"] for r in self.main_rows()], [MAIN_IPO])

    # ====================================================================================
    # IPO filter and average switch
    # ====================================================================================
    def test_ipo_multiselect_filters_the_rows(self):
        self.open_group(ONE)
        self.set_tally_filter("all")
        total = self.page.locator(".ipo-filter-checkbox").count()
        self.assertEqual(len(self.main_rows()) + len(self.sme_rows()), 2)
        button, menu = self.page.locator("#ipoSelectDropdownBtn"), self.page.locator("#ipoSelectMenu")
        button.click()
        expect(menu).to_have_class(re.compile(r"\bshow\b"))

        self.step(1, 4, "untick one IPO: its row goes, the label shows the count")
        self.page.locator(f".ipo-filter-checkbox[value='{SME_IPO}']").uncheck()
        self.page.wait_for_timeout(300)
        self.assertEqual(self.sme_rows(), [])
        self.assertEqual([r["ipo"] for r in self.main_rows()], [MAIN_IPO])
        expect(self.page.locator("#ipoSelectBtnText")).to_have_text(f"{total - 1} IPOs Selected" if total > 2 else re.compile(r".+"))

        self.step(2, 4, "Clear All, then tick one IPO: the label names it")
        self.page.click("#ipoClearAllBtn")
        self.page.wait_for_timeout(300)
        expect(self.page.locator("#ipoSelectBtnText")).to_have_text("None Selected (0)")
        self.assertEqual(self.main_rows() + self.sme_rows(), [])
        self.page.locator(f".ipo-filter-checkbox[value='{MAIN_IPO}']").check()
        self.page.wait_for_timeout(300)
        expect(self.page.locator("#ipoSelectBtnText")).to_have_text(MAIN_IPO)
        self.assertEqual([r["ipo"] for r in self.main_rows()], [MAIN_IPO])
        self.assertEqual(self.sme_rows(), [])

        self.step(3, 4, "the search box narrows the list")
        self.page.fill("#ipoSearchInput", "pos sme")
        visible = self.page.locator("#ipoMultiselectList li:visible label").all_inner_texts()
        self.assertEqual(visible, [SME_IPO])
        self.page.fill("#ipoSearchInput", "")

        self.step(4, 4, "Select All brings everything back")
        self.page.click("#ipoSelectAllBtn")
        self.page.wait_for_timeout(300)
        expect(self.page.locator("#ipoSelectBtnText")).to_have_text(f"All IPOs ({total})")
        self.assertEqual(len(self.main_rows()) + len(self.sme_rows()), 2)

    def test_average_switch_hides_and_shows_the_average_rate(self):
        self.open_group(ONE)
        self.set_tally_filter("all")
        row = self.main_row()
        self.assertTrue(row["avg"], "ONE holds shares, so the row has an average")
        self.assertTrue(row["avgShown"])
        track = self.page.locator("#toggleAvgRateSwitch + .custom-switch-track")
        track.click()
        expect(self.page.locator("#toggleAvgRateSwitch")).not_to_be_checked()
        expect(self.page.locator("body")).to_have_class(re.compile(r"hide-avg-rate"))
        self.assertFalse(self.main_row()["avgShown"])
        self.assertEqual(self.page.evaluate("localStorage.getItem('positions_show_avg')"), "false")
        self.open_group(ONE)
        expect(self.page.locator("#toggleAvgRateSwitch")).not_to_be_checked()
        expect(self.page.locator("body")).to_have_class(re.compile(r"hide-avg-rate"))
        self.set_tally_filter("all")
        track.click()
        expect(self.page.locator("body")).not_to_have_class(re.compile(r"hide-avg-rate"))
        self.assertTrue(self.main_row()["avgShown"])
        self.assertEqual(self.page.evaluate("localStorage.getItem('positions_show_avg')"), "true")

    # ====================================================================================
    # Share dialog
    # ====================================================================================
    def test_share_button_opens_a_dialog_with_that_groups_table(self):
        self.open_group(ONE)
        self.set_tally_filter("all")
        self.page.locator(".group-subtable-wrapper", has=self.page.locator("table[id^='mainboardBillingTable_']")) \
            .locator("button", has_text="Share").click()
        modal = self.page.locator("#shareGroupModal")
        expect(modal).to_have_class(re.compile(r"\bshow\b"))
        expect(modal.locator("#shareGroupModalBody h3")).to_have_text(ONE)
        body = modal.locator("#shareGroupModalBody")
        self.assertGreaterEqual(body.locator("table").count(), 1)                    # a copy of that group's table
        self.assertIn(MAIN_IPO, body.inner_text())
        expect(modal.locator("#copyGroupImageBtn")).to_be_visible()
        expect(modal.locator("#shareGroupImageBtn")).to_be_visible()
        expect(modal.locator("#hideEmptyRowsToggle")).to_be_checked()
        expect(modal.locator("#showNetTableToggle")).to_be_checked()
        self.assertEqual(modal.locator("#modalTallyFilterSelect").input_value(), self.page.input_value("#tallyFilterSelect"))
