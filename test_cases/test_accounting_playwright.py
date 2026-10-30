"""
Accounting & ledger E2E (/accounting/, templates/accounting.html; /accounting-logs/, accounting_logs.html).

Last page of the pipeline. Two kinds of data, kept apart on purpose (see test_cases/pipeline_state.py):
  * PIPELINE data: the ledger entries the Group-Wise page's payment modals created. Section 1 and the
    running-balance check only READ them (they are looked up by the ids Group-Wise recorded) and no other
    test here edits or deletes them. If Group-Wise did not run, a few equivalent entries are seeded for
    "ACCFB" groups so the checks still have something to look at.
  * PRIVATE data: "ACCT ..." groups and one "ACCT IPO", wiped and re-seeded before every test. Every test
    that edits, deletes, restores or filters works on these.

What the page really does (the tests assert this, not the wording of the task):
  * table columns: [checkbox] IPO | Group | Amount Type | Amount | Remark | Date Time | [Actions]; there is no
    separate JV column (a JV entry has no IPO and shows "JV"); amounts print as stored, e.g. "12500.00";
  * the rows of one Bulk Transfer (the "JV Payment" modal) are shown as ONE collapsible row, "Group A -> Group B",
    badge TRANSFER, with the transfer amount; Edit / Delete / Restore act on the whole batch;
  * deleting (single or bulk) asks for a reason in a SweetAlert box and the reason is written to the audit log;
  * "Show Deleted Entries" lists the deleted rows (red, no checkbox, no action buttons): single entries have NO
    restore button; the only one is a DISABLED button on a deleted bulk transfer. /restore-accounting/ works
    when called directly and is tested that way;
  * the date filter runs backwards: "From Date" is the NEWER end (entries on or before it) and "To Date" the
    older end (entries on or after it); a future From Date, or a To Date after From Date, is rejected;
  * editing re-checks the IPO payment rules (the group still owes, the type matches, the amount fits), needs a
    reason, and also edits the matching JV sibling when there is exactly one;
  * the "Payment" / "JV Payment" buttons open the modals shared with Group-Wise; #transactionModal1 (Add Payment
    Non-JV -> save_transaction) is in the DOM but has no button, so it is opened with bootstrap's modal plugin;
  * /accounting-logs/ columns are Timestamp | Transaction | Action | Details (before/after values and reason);
    there is no separate "user" column.
"""
import datetime
import re
import unittest
import uuid
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from playwright.sync_api import expect

from home.models import Accounting, AccountingAuditLog, CurrentIpoName, GroupDetail, Order
from test_cases import pipeline_state
from test_cases.base import PersistentLiveServerTestCase, pause_for_inspection, settle

ACCT_IPO = "ACCT IPO"
ONE, TWO, PAGE = "ACCT ONE", "ACCT TWO", "ACCT PAGE"
PRIVATE_GROUPS = (ONE, TWO, PAGE)
SEED_DATE, SEED_TIME = datetime.date(2026, 1, 20), datetime.time(10, 0, 0)
# KNOWN APP BUG on the encrypted-SQLite backend (the desktop build, and this suite with DB_ENGINE=sqlite):
# userproject/db_backend/base.py opens the connection without registering Django's SQLite date functions, so every
# `date_time__date` lookup fails with "no such function: django_datetime_cast_date" and the page answers 500.
SQLCIPHER_BACKEND = settings.DATABASES["default"]["ENGINE"] == "userproject.db_backend"
known_bug_on_sqlcipher = unittest.expectedFailure if SQLCIPHER_BACKEND else (lambda test: test)

GWD_KEYS = ("add_payment", "jv_payment", "multi_ipo_payment", "multi_ipo_payment_with_jv")

ROWS_JS = """() => {
    const off = document.querySelector('#selectAllAccounting') ? 1 : 0;
    const clean = t => t.replace(/\\s+/g, ' ').trim();
    return [...document.querySelectorAll('#example tbody tr')]
        .filter(tr => !tr.classList.contains('bulk-transfer-detail-row') && !tr.querySelector('.dataTables_empty'))
        .map(tr => {
            const td = [...tr.children], box = tr.querySelector('.accounting-select'), edit = tr.querySelector('.edit-btn');
            const bulk = tr.classList.contains('bulk-transfer-row');
            return {id: box ? box.value : (edit ? edit.dataset.id : null), bulk, batch: tr.dataset.transferBatch || null,
                    ipo: bulk ? clean(tr.querySelector('.bulk-transfer-label strong').textContent) : clean(td[off].textContent),
                    group: clean(td[off + 1].textContent), type: clean(td[off + 2].textContent),
                    amount: clean(td[off + 3].textContent), remark: td[off + 4].querySelector('textarea').value,
                    date: clean(td[off + 5].textContent), dateOrder: td[off + 5].dataset.order,
                    style: tr.getAttribute('style') || '', buttons: [...tr.querySelectorAll('button')].map(b => b.className)};
        });
}"""

DETAIL_JS = """batch => {
    const off = document.querySelector('#selectAllAccounting') ? 1 : 0;
    const clean = t => t.replace(/\\s+/g, ' ').trim();
    return [...document.querySelectorAll(`#example tr.bulk-transfer-detail-row[data-transfer-batch="${batch}"]`)]
        .map(tr => { const td = [...tr.children];
            return {ipo: clean(td[off].textContent).replace(/^↳\\s*/, ''), group: clean(td[off + 1].textContent),
                    type: clean(td[off + 2].textContent), amount: clean(td[off + 3].textContent),
                    remark: td[off + 4].querySelector('textarea').value}; });
}"""

OPEN_MODAL_JS = """id => $(document.getElementById(id)).modal('show')"""
LOCAL_NOW_JS = """sel => { const e = document.querySelector(sel); e.removeAttribute('readonly');
    e.value = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 19); }"""


def shown_date(dt):
    return timezone.localtime(dt).strftime("%d-%m-%y %H:%M:%S")


def gwd_cell(row_kids_js="kids[n - 2]"):
    return row_kids_js


class AccountingPlaywrightTestCase(PersistentLiveServerTestCase):
    PAGE_NAME = "accounting"
    _ran_any = False

    # ------------------------------------------------------------------ setup / teardown
    @classmethod
    def tearDownClass(cls):
        cls.log_summary()
        if cls._ran_any:
            try:
                cls.page.goto(f"{cls.live_server_url}/accounting/")
                settle(cls.page)
            except Exception:
                pass
            pause_for_inspection(cls.PAGE_NAME)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        type(self)._ran_any = True
        base = dict(IPOType="MAINBOARD", IPOPrice=100.0, PreOpenPrice=250.0, LotSizeRetail=100, LotSizeSHNI=1400,
                    LotSizeBHNI=7000, Active=True)
        self.ipo_acct = CurrentIpoName.objects.get_or_create(user=self.user, IPOName=ACCT_IPO, defaults=base)[0]
        self.groups = {n: GroupDetail.objects.get_or_create(user=self.user, GroupName=n)[0] for n in PRIVATE_GROUPS}
        self.reset_private()

    def reset_private(self):
        """Private fixture: both ACCT groups owe 20,000 on the ACCT IPO; no ledger entries; 60 JV rows on PAGE."""
        mine = list(self.groups.values())
        Accounting.objects.filter(user=self.user, group__in=mine).delete()      # audit logs go with them
        Order.objects.filter(user=self.user, OrderGroup__in=mine).delete()
        for name in (ONE, TWO):
            Order.objects.create(user=self.user, OrderGroup=self.groups[name], OrderIPOName=self.ipo_acct,
                                 OrderType="BUY", Rate=1.0, Quantity=1.0, OrderCategory="Premium", Amount=20000.0,
                                 OrderDate=SEED_DATE, OrderTime=SEED_TIME)
        base = timezone.now() - datetime.timedelta(days=2)
        Accounting.objects.bulk_create([
            Accounting(user=self.user, group=self.groups[PAGE], ipo=None, amount=Decimal(i + 1), amount_type="credit",
                       remark=f"page row {i + 1:02d}", date_time=base + datetime.timedelta(minutes=i), jv=True)
            for i in range(60)])

    def seed(self, group, amount_type, amount, ipo=True, jv=False, remark="", when=None, minutes=0):
        """One ledger entry. (date_time, amount) is unique per test so nothing is mistaken for a JV sibling."""
        when = when or (timezone.now() - datetime.timedelta(hours=1, minutes=minutes))
        return Accounting.objects.create(
            user=self.user, group=self.groups[group] if group in self.groups else group,
            ipo=self.ipo_acct if (ipo and not jv) else None, amount=Decimal(str(amount)), amount_type=amount_type,
            remark=remark, date_time=when, jv=jv)

    # ---------------------------------------------------------------------- page helpers
    def url(self, **query):
        qs = "&".join(f"{k}={v}" for k, v in query.items())
        return f"{self.live_server_url}/accounting/" + (f"?{qs}" if qs else "")

    def open_accounting(self, **query):
        self.page.goto(self.url(**query))
        settle(self.page)
        expect(self.page.locator("#example")).to_be_visible()

    def rows(self):
        return self.page.evaluate(ROWS_JS)

    def row_by_id(self, entry_id):
        found = [r for r in self.rows() if r["id"] == str(entry_id)]
        self.assertEqual(len(found), 1, f"entry {entry_id} should be listed once, found {len(found)}")
        return found[0]

    def row_locator(self, entry_id):
        return self.page.locator("#example tbody tr").filter(has=self.page.locator(f"[data-id='{entry_id}'], .accounting-select[value='{entry_id}']"))

    def swal_reason(self, reason):
        """Fill the reason box of the SweetAlert dialog and confirm it; waits for the reload that follows."""
        popup = self.page.locator(".swal2-popup")
        expect(popup).to_be_visible()
        self.page.fill(".swal2-textarea", reason)
        with self.page.expect_navigation(timeout=15000):
            self.page.click(".swal2-confirm")
        settle(self.page)

    def delete_row(self, entry_id, reason):
        with self.page.expect_request(lambda r: f"/soft-delete-accounting/{entry_id}/" in r.url) as info:
            self.row_locator(entry_id).locator(".delete-btn").click()
            self.swal_reason(reason)
        return info.value

    def open_modal(self, modal_id):
        self.page.evaluate(OPEN_MODAL_JS, modal_id)
        expect(self.page.locator(f"#{modal_id}")).to_have_class(re.compile(r"\bshow\b"))

    def fill_transaction(self, group, ipo, amount, amount_type, remark, jv_group):
        page = self.page
        page.select_option("#group_id", label=group)
        page.select_option("#ipo_id", label=ipo)
        page.fill("#amount", amount)
        page.select_option("#amount_type", amount_type)
        page.select_option("#jv_group", label=jv_group)
        page.fill("#remark", remark)
        page.evaluate(LOCAL_NOW_JS, "#date_time")

    def submit_transaction(self):
        with self.page.expect_navigation(url=re.compile(r"/accounting/"), timeout=15000):
            self.page.click("#saveBtn")
        settle(self.page)

    def edit_entry(self, entry_id, amount=None, reason="test edit", amount_type=None, remark=None):
        self.row_locator(entry_id).locator(".edit-btn").click()
        modal = self.page.locator("#editTransactionModal")
        expect(modal).to_have_class(re.compile(r"\bshow\b"))
        if amount is not None:
            self.page.fill("#edit_amount", amount)
        if amount_type:
            self.page.select_option("#edit_amount_type", amount_type)
        if remark is not None:
            self.page.fill("#edit_remark", remark)
        self.page.fill("#edit_reason", reason)
        with self.page.expect_navigation(timeout=15000):
            modal.locator("button[type=submit]").click()
        settle(self.page)

    # ---------------------------------------------------- pipeline data (from Group-Wise)
    def gwd_record(self, key):
        """What Group-Wise recorded for `key`; seeds an equivalent set (once) if that page did not run."""
        record = pipeline_state.get("groupwise", key)
        if record:
            return record
        record = pipeline_state.get("accounting", f"fallback_{key}")
        if record is None:
            record = self.seed_fallback(key)
            pipeline_state.record("accounting", f"fallback_{key}", record)
        return record

    def seed_fallback(self, key):
        ipo = CurrentIpoName.objects.get_or_create(
            user=self.user, IPOName="ACCFB IPO",
            defaults=dict(IPOType="MAINBOARD", IPOPrice=100.0, PreOpenPrice=250.0, LotSizeRetail=100,
                          LotSizeSHNI=1400, LotSizeBHNI=7000, Active=True))[0]
        mark, when = pipeline_state.marker("accounting"), timezone.now() - datetime.timedelta(minutes=30 + GWD_KEYS.index(key))
        spec = {
            "add_payment": [("ACCFB SINGLE", True, "credit", "4000.00", False, False)],
            "jv_payment": [("ACCFB FROM", True, "credit", "3000.00", False, True),
                           ("ACCFB TO", True, "debit", "3000.00", False, True)],
            "multi_ipo_payment": [("ACCFB MULTI", True, "credit", "2500.00", False, False),
                                  ("ACCFB MULTI", True, "credit", "4000.00", False, False)],
            "multi_ipo_payment_with_jv": [("ACCFB WITH JV", False, "debit", "800.00", True, False),
                                          ("ACCFB WITH JV", True, "credit", "3000.00", False, False)],
        }[key]
        batch, entries = uuid.uuid4(), []
        for group, with_ipo, kind, amount, jv, in_batch in spec:
            grp = GroupDetail.objects.get_or_create(user=self.user, GroupName=group)[0]
            row = Accounting.objects.create(
                user=self.user, group=grp, ipo=ipo if with_ipo else None, amount=Decimal(amount), amount_type=kind,
                remark=mark, date_time=when, jv=jv, transfer_batch_id=batch if in_batch else None)
            entries.append(dict(id=row.pk, group=group, ipo=ipo.IPOName if with_ipo else None, amount=amount,
                                type=kind, jv=jv, remark=mark, batch=str(batch) if in_batch else None,
                                date_time=timezone.localtime(when).strftime("%Y-%m-%d %H:%M:%S")))
        return dict(modal=f"fallback {key}", entries=entries)

    # ====================================================================================
    # Section 1: ledger continuity (Group-Wise -> Accounting)
    # ====================================================================================
    def test_group_wise_payments_appear_as_the_same_entries(self):
        """Single entries made in the Payment and Add Multiple IPO Payments modals, field for field."""
        checked = 0
        for key in ("add_payment", "multi_ipo_payment", "multi_ipo_payment_with_jv"):
            record = self.gwd_record(key)
            self.log(f"{key}: {len(record['entries'])} entries", indent=2)
            for entry in record["entries"]:
                with self.subTest(modal=key, entry=entry["id"]):
                    db = Accounting.objects.get(pk=entry["id"])
                    self.assertFalse(db.is_deleted)
                    self.assertEqual((db.group.GroupName, str(db.amount), db.amount_type, db.jv, db.remark),
                                     (entry["group"], entry["amount"], entry["type"], entry["jv"], entry["remark"]))
                    self.open_accounting(group_name=entry["group"].replace(" ", "%20"))
                    row = self.row_by_id(entry["id"])
                    self.assertEqual(row["group"], entry["group"])
                    self.assertEqual(row["ipo"], entry["ipo"] or "JV")           # a JV entry has no IPO
                    self.assertEqual(row["type"], entry["type"].upper())
                    self.assertEqual(row["amount"], entry["amount"])
                    self.assertEqual(row["remark"], entry["remark"])
                    self.assertEqual(row["date"], shown_date(db.date_time))
                    self.assertEqual(row["dateOrder"], entry["date_time"])
                    self.assertEqual(db.jv, entry["jv"])
                    checked += 1
        self.assertGreaterEqual(checked, 4)

    def test_group_wise_jv_payment_is_one_balanced_bulk_transfer(self):
        """The JV Payment modal's entries: one batch, equal credit and debit, shown as a single expandable row."""
        record = self.gwd_record("jv_payment")
        entries = record["entries"]
        self.assertEqual(len(entries), 2)
        db = [Accounting.objects.get(pk=e["id"]) for e in entries]
        self.assertEqual(len({str(d.transfer_batch_id) for d in db}), 1)
        self.assertIsNotNone(db[0].transfer_batch_id)
        self.assertEqual(db[0].date_time, db[1].date_time)                      # same timestamp
        credit = sum((d.amount for d in db if d.amount_type == "credit"), Decimal("0"))
        debit = sum((d.amount for d in db if d.amount_type == "debit"), Decimal("0"))
        self.assertEqual(credit, debit)                                          # balanced
        self.assertTrue(all(not d.is_deleted for d in db))

        source, dest = entries[0]["group"], entries[1]["group"]
        self.open_accounting(group_name=source.replace(" ", "%20"))
        bulk = [r for r in self.rows() if r["batch"] == entries[0]["batch"]]
        self.assertEqual(len(bulk), 1, "the two legs must be ONE row")
        row = bulk[0]
        self.assertEqual((row["bulk"], row["ipo"], row["type"]), (True, "Bulk Transfer", "TRANSFER"))
        self.assertEqual(row["group"], f"{source} → {dest}")
        self.assertEqual(row["amount"], entries[0]["amount"])
        self.assertEqual(row["date"], shown_date(db[0].date_time))
        if entries[0]["remark"].startswith("Transfer to"):                       # remark typed in the modal
            self.assertEqual(row["remark"], entries[0]["remark"].split(" - ", 1)[1])

        self.page.locator(f".bulk-transfer-toggle[data-transfer-batch='{entries[0]['batch']}']").click()
        legs = self.page.evaluate(DETAIL_JS, entries[0]["batch"])
        self.assertEqual(len(legs), 2)
        for leg, want in zip(legs, entries):
            self.assertEqual((leg["ipo"], leg["group"], leg["type"], leg["amount"], leg["remark"]),
                             (want["ipo"] or "JV", want["group"], want["type"].upper(), want["amount"], want["remark"]))

    def test_running_balance_matches_the_group_wise_collection(self):
        """Per group: credit - debit over its active entries == the Collection column on the Group-Wise page."""
        groups = []
        for key in GWD_KEYS:
            for entry in self.gwd_record(key)["entries"]:
                if entry["group"] not in groups:
                    groups.append(entry["group"])
        self.assertGreaterEqual(len(groups), 3)
        self.page.goto(f"{self.live_server_url}/GroupWiseDashboard?GWD_page_size=All&show_zero_due=true")
        settle(self.page)
        for group in groups:
            with self.subTest(group=group):
                net = Decimal("0")
                for e in Accounting.objects.filter(user=self.user, group__GroupName=group, is_deleted=False):
                    net += e.amount if e.amount_type == "credit" else -e.amount
                shown = self.page.evaluate("""name => {
                    const tr = [...document.querySelectorAll('#example tbody tr')].find(r => r.children[0].textContent.trim() === name);
                    if (!tr) return null;
                    const kids = [...tr.children]; return kids[kids.length - 2].textContent.trim(); }""", group)
                self.assertIsNotNone(shown, f"{group} is not on the Group-Wise page")
                self.assertEqual(shown, "0" if round(net) == 0 else f"{float(net):.0f}")

    # ====================================================================================
    # Section 2: creating a transaction (#transactionModal1)
    # ====================================================================================
    def test_standard_payment_entry_is_saved_and_listed(self):
        self.open_accounting(group_name="ACCT%20ONE")
        before = Accounting.objects.filter(user=self.user).count()
        self.open_modal("transactionModal1")
        self.fill_transaction(ONE, ACCT_IPO, "25000.50", "credit", "standard payment", TWO)
        self.submit_transaction()
        self.assertEqual(Accounting.objects.filter(user=self.user).count(), before + 2)       # the payment + its JV leg
        entry = Accounting.objects.get(user=self.user, group=self.groups[ONE], ipo=self.ipo_acct, jv=False)
        self.assertEqual((entry.amount, entry.amount_type, entry.remark, entry.is_deleted),
                         (Decimal("25000.50"), "credit", "standard payment", False))
        self.open_accounting(group_name="ACCT%20ONE")
        row = self.row_by_id(entry.pk)
        self.assertEqual((row["ipo"], row["group"], row["type"], row["amount"], row["remark"]),
                         (ACCT_IPO, ONE, "CREDIT", "25000.50", "standard payment"))

    def test_direct_jv_transfer_creates_both_legs(self):
        self.open_accounting()
        self.open_modal("transactionModal1")
        self.fill_transaction(ONE, ACCT_IPO, "1000", "debit", "jv out", TWO)
        self.submit_transaction()
        leg_a = Accounting.objects.get(user=self.user, group=self.groups[ONE], remark="jv out")
        leg_b = Accounting.objects.get(user=self.user, group=self.groups[TWO], jv=True, amount=Decimal("1000.00"))
        self.assertEqual((leg_a.jv, leg_a.ipo_id, leg_a.amount_type), (False, self.ipo_acct.id, "debit"))
        self.assertEqual((leg_b.jv, leg_b.ipo_id, leg_b.amount_type), (True, None, "credit"))   # the mirror image
        self.assertEqual(leg_a.amount, leg_b.amount)
        self.assertEqual(leg_a.date_time, leg_b.date_time)
        self.open_accounting(group_name="ACCT%20TWO")
        row = self.row_by_id(leg_b.pk)
        self.assertEqual((row["ipo"], row["type"], row["amount"]), ("JV", "CREDIT", "1000.00"))

    def test_amount_rules_in_the_payment_form(self):
        self.open_accounting()
        before = Accounting.objects.filter(user=self.user).count()
        self.open_modal("transactionModal1")
        form_valid = lambda: self.page.evaluate("document.querySelector('#nonJVForm').checkValidity()")
        self.fill_transaction(ONE, ACCT_IPO, "100.50", "credit", "ok", TWO)
        self.assertTrue(form_valid(), "100.50 is a valid amount")
        for bad, why in (("100.505", "three decimals"), ("", "empty")):
            with self.subTest(amount=bad, why=why):
                self.page.fill("#amount", bad)
                self.assertFalse(form_valid(), f"{why} must not be accepted")
        self.page.fill("#amount", "")
        self.page.click("#saveBtn")
        self.page.wait_for_timeout(500)
        self.assertEqual(Accounting.objects.filter(user=self.user).count(), before)

    def test_remark_longer_than_250_characters_is_refused(self):
        self.open_accounting()
        self.open_modal("transactionModal1")
        self.fill_transaction(ONE, ACCT_IPO, "10", "credit", "x", TWO)
        error, save = self.page.locator("#remark_error"), self.page.locator("#saveBtn")
        expect(error).to_be_hidden()
        self.page.fill("#remark", "r" * 251)
        expect(error).to_be_visible()
        expect(error).to_contain_text("Maximum 250 characters")
        expect(save).to_be_disabled()
        self.assertEqual(len(self.page.input_value("#remark")), 250)            # cut to the limit
        self.page.fill("#remark", "r" * 250)
        expect(error).to_be_hidden()
        expect(save).to_be_enabled()

    @unittest.expectedFailure
    def test_zero_or_negative_amounts_are_not_saved(self):
        """
        KNOWN APP BUG. The amount field has step 0.01 but no minimum and save_transaction() does not check the
        amount (the Payment modal and update_accounting() do), so a payment of 0 or -5 is written to the ledger.
        """
        self.open_accounting()
        before = Accounting.objects.filter(user=self.user).count()
        for bad in ("0", "-5"):
            with self.subTest(amount=bad):
                self.open_accounting()
                self.open_modal("transactionModal1")
                self.fill_transaction(ONE, ACCT_IPO, bad, "credit", "bad amount", TWO)
                self.page.click("#saveBtn")
                self.page.wait_for_timeout(700)
        self.assertEqual(Accounting.objects.filter(user=self.user, remark="bad amount").count(), 0)
        self.assertEqual(Accounting.objects.filter(user=self.user).count(), before)

    # ====================================================================================
    # Section 3: editing and the audit log
    # ====================================================================================
    def test_editing_an_entry_updates_the_row_and_writes_an_audit_log(self):
        entry = self.seed(ONE, "credit", "10000.00", remark="first transfer")
        self.open_accounting(group_name="ACCT%20ONE")
        self.assertEqual(self.row_by_id(entry.pk)["amount"], "10000.00")

        self.row_locator(entry.pk).locator(".edit-btn").click()                  # the modal opens pre-filled
        expect(self.page.locator("#edit_amount")).to_have_value("10000.00")
        expect(self.page.locator("#edit_remark")).to_have_value("first transfer")
        expect(self.page.locator("#edit_amount_type")).to_have_value("credit")
        self.assertEqual(self.page.eval_on_selector("#edit_group", "e => e.selectedOptions[0].text.trim()"), ONE)
        self.assertEqual(self.page.eval_on_selector("#edit_ipo", "e => e.selectedOptions[0].text.trim()"), ACCT_IPO)
        self.page.fill("#edit_amount", "12500.00")
        self.page.fill("#edit_reason", "Corrected bank transfer fee")
        with self.page.expect_navigation(timeout=15000):
            self.page.locator("#editTransactionModal button[type=submit]").click()
        settle(self.page)

        self.assertEqual(self.row_by_id(entry.pk)["amount"], "12500.00")
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("12500.00"))
        log = AccountingAuditLog.objects.get(accounting=entry)
        self.assertEqual((log.action, log.user_id), ("EDIT", self.user.id))
        self.assertEqual(log.changes["Amount"], {"old": "10000.00", "new": "12500.00"})
        self.assertEqual(log.changes["reason"], "Corrected bank transfer fee")
        self.assertNotIn("Amount Type", log.changes)                                  # only what changed is logged
        self.assertLess(abs((timezone.now() - log.timestamp).total_seconds()), 120)

    def test_the_edit_reason_is_mandatory(self):
        entry = self.seed(ONE, "credit", "10000.00")
        self.open_accounting(group_name="ACCT%20ONE")
        self.row_locator(entry.pk).locator(".edit-btn").click()
        self.page.fill("#edit_amount", "11000")
        reason = self.page.locator("#edit_reason")
        expect(reason).to_have_value("")
        self.page.evaluate("window.__sentinel = 1")
        self.page.locator("#editTransactionModal button[type=submit]").click()
        self.page.wait_for_timeout(600)
        self.assertEqual(self.page.evaluate("window.__sentinel"), 1, "the page must not have been submitted")
        self.assertTrue(reason.evaluate("e => e.matches(':invalid')"))
        self.assertTrue(reason.evaluate("e => e.validity.valueMissing"))
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("10000.00"))
        self.assertEqual(AccountingAuditLog.objects.filter(accounting=entry).count(), 0)
        reason.fill("   ")                                                           # blanks are not a reason either
        self.page.evaluate("document.querySelector('#editTransactionModal form').submit()")
        settle(self.page)
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("10000.00"))
        self.assertEqual(AccountingAuditLog.objects.filter(accounting=entry).count(), 0)

    def test_an_edit_that_breaks_the_payment_rules_is_refused(self):
        entry = self.seed(ONE, "credit", "10000.00")
        self.open_accounting(group_name="ACCT%20ONE")
        self.edit_entry(entry.pk, amount="25000", reason="too big")             # the group only owes 20,000
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal("10000.00"))
        self.open_accounting(group_name="ACCT%20ONE")
        self.edit_entry(entry.pk, amount_type="debit", reason="wrong way")
        entry.refresh_from_db()
        self.assertEqual(entry.amount_type, "credit")
        self.assertEqual(AccountingAuditLog.objects.filter(accounting=entry).count(), 0)

    @unittest.expectedFailure
    def test_a_refused_edit_tells_the_user_why(self):
        """
        KNOWN APP BUG. update_accounting() refuses the edit with messages.error(...), but templates/basic.html has
        the block that prints Django messages commented out, so the modal just closes and nothing says the edit
        was not saved or why.
        """
        entry = self.seed(ONE, "credit", "10000.00")
        self.open_accounting(group_name="ACCT%20ONE")
        self.edit_entry(entry.pk, amount="25000", reason="too big")
        expect(self.page.locator("body")).to_contain_text("cannot exceed its outstanding balance", timeout=3000)

    def test_editing_one_leg_of_a_jv_pair_edits_the_other(self):
        when = timezone.now() - datetime.timedelta(hours=2)
        leg_a = self.seed(ONE, "credit", "3000.00", remark="pair", when=when)
        leg_b = self.seed(TWO, "debit", "3000.00", jv=True, remark="pair jv", when=when)
        self.open_accounting(group_name="ACCT%20ONE")
        self.edit_entry(leg_a.pk, amount="4000.00", reason="pair correction")
        leg_a.refresh_from_db()
        leg_b.refresh_from_db()
        self.assertEqual((leg_a.amount, leg_b.amount), (Decimal("4000.00"), Decimal("4000.00")))
        self.assertEqual((leg_a.amount_type, leg_b.amount_type), ("credit", "debit"))   # still opposite
        logs = AccountingAuditLog.objects.filter(accounting__in=[leg_a, leg_b])
        self.assertEqual(logs.count(), 2)
        self.assertIn("auto-edited", AccountingAuditLog.objects.get(accounting=leg_b).changes["note"])

    # ====================================================================================
    # Section 4: soft delete, restore, bulk delete
    # ====================================================================================
    def test_single_entry_soft_delete_asks_for_a_reason(self):
        entry = self.seed(ONE, "credit", "1111.00", remark="to delete")
        keep = self.seed(ONE, "credit", "2222.00", remark="to keep", minutes=7)
        self.open_accounting(group_name="ACCT%20ONE")

        self.step(1, 3, "the reason is required")
        self.row_locator(entry.pk).locator(".delete-btn").click()
        expect(self.page.locator(".swal2-popup")).to_be_visible()
        self.page.click(".swal2-confirm")
        expect(self.page.locator(".swal2-validation-message")).to_have_text("Please enter a reason.")
        entry.refresh_from_db()
        self.assertFalse(entry.is_deleted)
        self.page.click(".swal2-cancel")

        self.step(2, 3, "with a reason: POST, flag set, row gone")
        request = self.delete_row(entry.pk, "entered twice")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.post_data_json, {"reason": "entered twice"})
        entry.refresh_from_db()
        self.assertTrue(entry.is_deleted)
        self.assertIsNotNone(entry.deleted_at)
        ids = [r["id"] for r in self.rows()]
        self.assertNotIn(str(entry.pk), ids)
        self.assertIn(str(keep.pk), ids)

        self.step(3, 3, "it is logged with the reason")
        log = AccountingAuditLog.objects.get(accounting=entry, action="SOFT_DELETE")
        self.assertEqual((log.changes["reason"], log.changes["Amount"], log.changes["Group"]), ("entered twice", "1111.00", ONE))

    def test_show_deleted_lists_deleted_entries_and_they_can_be_restored(self):
        entry = self.seed(ONE, "credit", "1313.00", remark="was deleted")
        live = self.seed(ONE, "credit", "2323.00", remark="still live", minutes=9)
        self.open_accounting(group_name="ACCT%20ONE")
        self.delete_row(entry.pk, "mistake")

        self.step(1, 3, "tick Show Deleted Entries: only deleted rows, styled, with no action buttons")
        self.open_accounting(group_name="ACCT%20ONE")
        self.assertFalse(self.page.locator("#showDeletedCheck").is_checked())
        with self.page.expect_navigation():
            self.page.locator("#showDeletedCheck").check()
        settle(self.page)
        self.assertIn("show_deleted=1", self.page.url)
        expect(self.page.locator("#showDeletedCheck")).to_be_checked()
        rows = self.rows()
        self.assertEqual([r["id"] for r in rows] if rows[0]["id"] else [], [])        # no checkboxes / buttons to key on
        self.assertEqual([(r["amount"], r["remark"]) for r in rows], [("1313.00", "was deleted")])
        self.assertIn("opacity: 0.6", rows[0]["style"])
        self.assertIn("#ffe6e6", rows[0]["style"])
        self.assertEqual(rows[0]["buttons"], [])
        self.assertEqual(self.page.locator(".restore-btn").count(), 0)
        self.assertEqual(self.page.locator("#deleteSelectedAccounting").count(), 0)

        self.step(2, 3, "the restore endpoint brings it back")
        reply = self.page.request.post(f"{self.live_server_url}/restore-accounting/{entry.pk}/",
                                       headers={"X-CSRFToken": self.csrf()})
        self.assertEqual(reply.json(), {"success": True})
        entry.refresh_from_db()
        self.assertFalse(entry.is_deleted)
        self.assertIsNone(entry.deleted_at)

        self.step(3, 3, "back in the live view; the restore is logged")
        self.open_accounting(group_name="ACCT%20ONE")
        self.assertEqual(sorted(r["amount"] for r in self.rows()), ["1313.00", "2323.00"])
        self.assertEqual(AccountingAuditLog.objects.filter(accounting=entry, action="RESTORE").count(), 1)
        self.open_accounting(group_name="ACCT%20ONE", show_deleted=1)
        self.assertEqual(self.rows(), [])

    @unittest.expectedFailure
    def test_a_deleted_entry_has_a_restore_button(self):
        """
        KNOWN APP BUG. accounting.html wires up a .restore-btn click handler (SweetAlert confirm -> POST
        /restore-accounting/<id>/), but in the Show Deleted view the view renders no Actions column, so there is no
        button to click and a deleted entry can only be restored by calling the endpoint.
        """
        entry = self.seed(ONE, "credit", "1414.00", remark="restore me")
        self.open_accounting(group_name="ACCT%20ONE")
        self.delete_row(entry.pk, "mistake")
        self.open_accounting(group_name="ACCT%20ONE", show_deleted=1)
        button = self.page.locator(".restore-btn").first
        expect(button).to_be_visible(timeout=3000)
        button.click()
        self.page.click(".swal2-confirm")
        entry.refresh_from_db()
        self.assertFalse(entry.is_deleted)

    def csrf(self):
        return next(c["value"] for c in self.page.context.cookies() if c["name"] == "csrftoken") \
            if any(c["name"] == "csrftoken" for c in self.page.context.cookies()) else self.page.input_value("[name=csrfmiddlewaretoken]")

    def test_deleting_a_bulk_transfer_removes_and_restores_the_whole_batch(self):
        batch, when = uuid.uuid4(), timezone.now() - datetime.timedelta(hours=3)
        out = Accounting.objects.create(user=self.user, group=self.groups[ONE], ipo=self.ipo_acct, amount=Decimal("500.00"),
                                        amount_type="credit", remark="Transfer to ACCT TWO", date_time=when,
                                        transfer_batch_id=batch)
        into = Accounting.objects.create(user=self.user, group=self.groups[TWO], ipo=self.ipo_acct, amount=Decimal("500.00"),
                                         amount_type="debit", remark="Transfer from ACCT ONE", date_time=when,
                                         transfer_batch_id=batch)
        self.open_accounting(group_name="ACCT%20ONE")
        row = [r for r in self.rows() if r["bulk"]][0]
        self.delete_row(row["id"], "wrong transfer")
        out.refresh_from_db(), into.refresh_from_db()
        self.assertTrue(out.is_deleted and into.is_deleted)
        self.assertEqual(AccountingAuditLog.objects.filter(action="SOFT_DELETE", accounting__in=[out, into]).count(), 2)
        self.open_accounting(group_name="ACCT%20ONE", show_deleted=1)
        deleted = self.rows()
        self.assertEqual((len(deleted), deleted[0]["bulk"]), (1, True))
        reply = self.page.request.post(f"{self.live_server_url}/restore-accounting/{out.pk}/",
                                       headers={"X-CSRFToken": self.csrf()})
        self.assertEqual(reply.json(), {"success": True})
        out.refresh_from_db(), into.refresh_from_db()
        self.assertFalse(out.is_deleted or into.is_deleted)

    def test_bulk_delete_selected_entries(self):
        entries = [self.seed(ONE, "credit", f"{100 + i}.00", remark=f"bulk {i}", minutes=11 * i) for i in range(4)]
        self.open_accounting(group_name="ACCT%20ONE")
        counter, button = self.page.locator("#selectedAccountingCount"), self.page.locator("#deleteSelectedAccounting")
        expect(counter).to_have_text("0")
        expect(button).to_be_disabled()
        chosen = entries[:3]
        for n, entry in enumerate(chosen, start=1):
            self.row_locator(entry.pk).locator(".accounting-select").check()
            expect(counter).to_have_text(str(n))
            expect(button).to_be_enabled()
        self.row_locator(chosen[0].pk).locator(".accounting-select").uncheck()
        expect(counter).to_have_text("2")
        self.row_locator(chosen[0].pk).locator(".accounting-select").check()
        expect(counter).to_have_text("3")

        with self.page.expect_request(lambda r: "/bulk-delete-accounting/" in r.url) as info:
            button.click()
            self.swal_reason("clean-up")
        request = info.value
        self.assertEqual(request.method, "POST")
        self.assertEqual(sorted(request.post_data_json["ids"]), sorted(e.pk for e in chosen))
        self.assertEqual(request.post_data_json["reason"], "clean-up")
        for entry in entries:
            entry.refresh_from_db()
        self.assertEqual([e.is_deleted for e in entries], [True, True, True, False])
        self.assertEqual([r["id"] for r in self.rows()], [str(entries[3].pk)])
        self.assertEqual(AccountingAuditLog.objects.filter(action="SOFT_DELETE", accounting__in=chosen).count(), 3)

    def test_select_all_counts_every_row_on_the_page(self):
        for i in range(3):
            self.seed(ONE, "credit", f"{300 + i}.00", minutes=13 * i)
        self.open_accounting(group_name="ACCT%20ONE")
        self.page.locator("#selectAllAccounting").check()
        expect(self.page.locator("#selectedAccountingCount")).to_have_text("3")
        self.page.locator("#selectAllAccounting").uncheck()
        expect(self.page.locator("#selectedAccountingCount")).to_have_text("0")
        expect(self.page.locator("#deleteSelectedAccounting")).to_be_disabled()

    # ====================================================================================
    # Section 5: filters, search and page size
    # ====================================================================================
    def local_day(self, days_ago, hour=12):
        day = timezone.localdate() - datetime.timedelta(days=days_ago)
        return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hour, 0, 7)))

    @known_bug_on_sqlcipher
    def test_date_range_filter_runs_from_the_newer_date_back_to_the_older_one(self):
        """On the encrypted-SQLite backend this page answers 500 (see SQLCIPHER_BACKEND); on MySQL it runs."""
        old = self.seed(ONE, "credit", "11.00", remark="ten days ago", when=self.local_day(10))
        mid = self.seed(ONE, "credit", "22.00", remark="five days ago", when=self.local_day(5))
        new = self.seed(ONE, "credit", "33.00", remark="one day ago", when=self.local_day(1))
        day = lambda n: (timezone.localdate() - datetime.timedelta(days=n)).isoformat()
        self.open_accounting(group_name="ACCT%20ONE")
        self.assertEqual(len(self.rows()), 3)

        self.step(1, 2, "a window around the middle entry, set through the two pickers")
        with self.page.expect_navigation():
            self.page.fill("#date_from", day(3))                         # newer end: on or before
        settle(self.page)
        with self.page.expect_navigation():
            self.page.fill("#date_to", day(7))                           # older end: on or after
        settle(self.page)
        self.assertEqual([r["id"] for r in self.rows()], [str(mid.pk)])
        self.assertIn(f"date_from={day(3)}", self.page.url)

        self.step(2, 2, "one day only: both ends the same date")
        self.open_accounting(group_name="ACCT%20ONE", date_from=day(1), date_to=day(1))
        self.assertEqual([r["id"] for r in self.rows()], [str(new.pk)])
        self.open_accounting(group_name="ACCT%20ONE", date_from=day(10), date_to=day(10))
        self.assertEqual([r["id"] for r in self.rows()], [str(old.pk)])

    def test_date_pickers_cannot_pick_the_future_and_bad_ranges_are_rejected(self):
        day = lambda n: (timezone.localdate() - datetime.timedelta(days=n)).isoformat()
        self.open_accounting(group_name="ACCT%20ONE")
        today = self.page.evaluate("(() => { const n = new Date(); return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}-${String(n.getDate()).padStart(2,'0')}`; })()")
        self.assertEqual(self.page.get_attribute("#date_from", "max"), today)
        self.assertEqual(self.page.get_attribute("#date_to", "max"), today)
        # picking a From Date (without submitting) caps the To Date at it
        self.page.evaluate("""d => { const f = document.getElementById('date_from'); f.value = d;
            f.dispatchEvent(new Event('input')); }""", day(3))
        self.assertEqual(self.page.get_attribute("#date_to", "max"), day(3))
        # a From Date in the future is pulled back to today
        self.page.evaluate("""d => { const f = document.getElementById('date_from'); f.value = d;
            f.dispatchEvent(new Event('input')); }""", (timezone.localdate() + datetime.timedelta(days=5)).isoformat())
        self.assertEqual(self.page.input_value("#date_from"), today)

        tomorrow = (timezone.localdate() + datetime.timedelta(days=1)).isoformat()
        for query in (dict(date_from=tomorrow), dict(date_from=day(5), date_to=day(2))):
            with self.subTest(query=query):
                self.open_accounting(group_name="ACCT%20ONE", **query)
                self.assertEqual(self.rows(), [])

    def test_group_and_ipo_filters_and_double_click_filtering(self):
        mine = self.seed(ONE, "credit", "44.00", remark="on the ipo")
        jv = self.seed(ONE, "credit", "55.00", jv=True, remark="a jv entry", minutes=5)
        other = self.seed(TWO, "credit", "66.00", remark="other group", minutes=9)
        self.open_accounting(group_name="ACCT%20ONE")
        self.assertEqual(sorted(r["id"] for r in self.rows()), sorted([str(mine.pk), str(jv.pk)]))
        self.open_accounting(group_name="ACCT%20ONE", ipo_name="JV")
        self.assertEqual([r["id"] for r in self.rows()], [str(jv.pk)])
        self.open_accounting(group_name="ACCT%20ONE", ipo_name="ACCT%20IPO")
        self.assertEqual([r["id"] for r in self.rows()], [str(mine.pk)])
        self.open_accounting(group_name="ACCT%20ONE")
        with self.page.expect_navigation():
            self.row_locator(mine.pk).locator(".filter-group").dblclick()    # double-click a group name to filter
        settle(self.page)
        self.assertIn("group_name=ACCT%20ONE", self.page.url)
        self.assertNotIn(str(other.pk), [r["id"] for r in self.rows()])

    def test_search_box_filters_instantly_without_duplicates(self):
        a = self.seed(ONE, "credit", "71.00", remark="alpha invoice", minutes=1)
        b = self.seed(ONE, "debit", "72.00", remark="beta invoice", minutes=3)
        c = self.seed(TWO, "credit", "73.00", remark="gamma receipt", minutes=5)
        self.open_accounting()
        self.page.evaluate("window.__sentinel = 1")
        search = self.page.locator("#example_filter input")
        wanted = lambda ids: sorted(str(i.pk) for i in ids)
        mine = lambda: sorted(r["id"] for r in self.rows() if r["id"] in {str(a.pk), str(b.pk), str(c.pk)})
        for text, expected in (("ACCT TWO", [c]), ("invoice", [a, b]), ("alpha", [a]), (ACCT_IPO, [a, b, c]),
                               ("GAMMA RECEIPT", [c])):
            with self.subTest(search=text):
                search.fill(text)
                self.page.wait_for_timeout(250)
                self.assertEqual(mine(), wanted(expected))
                ids = [r["id"] for r in self.rows()]
                self.assertEqual(len(ids), len(set(ids)), "a row is listed twice")
        search.fill("no such text anywhere")
        expect(self.page.locator("#example tbody td.dataTables_empty")).to_be_visible()
        search.fill("")
        self.assertEqual(self.page.evaluate("window.__sentinel"), 1, "searching must not reload the page")
        self.assertEqual(mine(), wanted([a, b, c]))

    def test_page_size_selector_and_pagination(self):
        self.open_accounting(group_name="ACCT%20PAGE")
        select = self.page.locator("#example_length select")
        self.assertEqual(select.locator("option").all_inner_texts(), ["50", "100", "150", "200", "All"])
        info = self.page.locator("#example_info")
        expect(select).to_have_value("50")
        self.assertEqual(len(self.rows()), 50)
        expect(info).to_have_text("Showing 1 to 50 of 60 Rows")
        self.assertGreater(self.page.locator("#example_paginate .paginate_button.page-item").count(), 2)   # Prev 1 2 Next
        self.page.locator("#example_paginate a", has_text=re.compile(r"^2$")).click()
        expect(info).to_have_text("Showing 51 to 60 of 60 Rows")
        self.assertEqual(len(self.rows()), 10)
        select.select_option("100")
        expect(info).to_have_text("Showing 1 to 60 of 60 Rows")
        self.assertEqual(len(self.rows()), 60)
        select.select_option("All")
        expect(info).to_have_text("Showing 1 to 60 of 60 Rows")
        select.select_option("50")
        self.assertEqual(len(self.rows()), 50)
        ids = [r["id"] for r in self.rows()]
        self.assertEqual(len(ids), len(set(ids)))

    # ====================================================================================
    # Section 6: the audit log page
    # ====================================================================================
    def log_rows(self):
        return self.page.evaluate("""() => [...document.querySelectorAll('#auditLogTable tbody tr')].map(tr => {
            const td = [...tr.children], clean = t => t.replace(/\\s+/g, ' ').trim();
            return {time: clean(td[0].textContent), txn: clean(td[1].textContent), href: td[1].querySelector('a')?.getAttribute('href'),
                    action: clean(td[2].textContent), details: clean(td[3].textContent)}; })""")

    def test_activity_log_lists_every_edit_delete_and_restore(self):
        entry = self.seed(ONE, "credit", "10000.00", remark="logged entry")
        gone = self.seed(ONE, "credit", "1999.00", remark="to be deleted", minutes=15)
        self.open_accounting(group_name="ACCT%20ONE")
        self.edit_entry(entry.pk, amount="12500.00", reason="Corrected bank transfer fee")
        self.delete_row(gone.pk, "wrong person")
        reply = self.page.request.post(f"{self.live_server_url}/restore-accounting/{gone.pk}/",
                                       headers={"X-CSRFToken": self.csrf()})
        self.assertTrue(reply.json()["success"])

        self.page.goto(f"{self.live_server_url}/accounting-logs/")
        settle(self.page)
        self.assertEqual(self.page.locator("#auditLogTable thead th").all_inner_texts(),
                         ["Timestamp", "Transaction", "Action", "Details"])
        rows = self.log_rows()
        ref = f"{ACCT_IPO} / {ONE}"
        edit = next(r for r in rows if r["action"] == "Edited" and f"entry_id={entry.pk}" in (r["href"] or ""))
        self.assertEqual(edit["txn"], ref)
        self.assertIn("Amount", edit["details"])
        self.assertIn("10000.00", edit["details"])                                   # before
        self.assertIn("12500.00", edit["details"])                                   # after
        self.assertIn("Reason: Corrected bank transfer fee", edit["details"])
        deleted = next(r for r in rows if r["action"] == "Deleted" and f"entry_id={gone.pk}" in (r["href"] or ""))
        self.assertIn("Reason: wrong person", deleted["details"])
        self.assertIn("1999.00", deleted["details"])
        restored = next(r for r in rows if r["action"] == "Restored" and f"entry_id={gone.pk}" in (r["href"] or ""))
        self.assertIn("1999.00", restored["details"])
        for r in (edit, deleted, restored):
            self.assertRegex(r["time"], r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$")
        logs = AccountingAuditLog.objects.filter(accounting__in=[entry, gone])
        self.assertEqual(sorted(logs.values_list("action", flat=True)), ["EDIT", "RESTORE", "SOFT_DELETE"])
        self.assertTrue(all(log.user_id == self.user.id for log in logs))
        # newest first: the restore is above the delete, which is above the edit
        positions = {r["action"]: i for i, r in enumerate(rows) if f"entry_id={gone.pk}" in (r["href"] or "") or f"entry_id={entry.pk}" in (r["href"] or "")}
        self.assertLess(positions["Restored"], positions["Deleted"])
        self.assertLess(positions["Deleted"], positions["Edited"])

        with self.page.expect_navigation():
            self.page.locator(f"#auditLogTable a[href*='entry_id={entry.pk}']").first.click()
        settle(self.page)
        self.assertEqual([r["id"] for r in self.rows()], [str(entry.pk)])             # the link opens that entry

    def test_activity_log_shows_a_bulk_transfer_once_per_action(self):
        batch, when = uuid.uuid4(), timezone.now() - datetime.timedelta(hours=4)
        legs = [Accounting.objects.create(user=self.user, group=self.groups[g], ipo=self.ipo_acct, amount=Decimal("800.00"),
                                          amount_type=t, remark="Transfer", date_time=when, transfer_batch_id=batch)
                for g, t in ((ONE, "credit"), (TWO, "debit"))]
        self.open_accounting(group_name="ACCT%20ONE")
        row = [r for r in self.rows() if r["bulk"]][0]
        self.delete_row(row["id"], "batch mistake")
        self.page.goto(f"{self.live_server_url}/accounting-logs/")
        settle(self.page)
        mine = [r for r in self.log_rows() if f"batch_id={batch}" in (r["href"] or "")]
        self.assertEqual(len(mine), 1, "two legs, one logged action")
        self.assertEqual(mine[0]["action"], "Deleted")
        self.assertIn("Bulk Transfer", mine[0]["txn"])
        self.assertIn(f"{ONE} → {TWO}", mine[0]["details"])
        self.assertIn("₹800.00", mine[0]["details"])
        self.assertIn("Entries: 2", mine[0]["details"])
        self.assertIn("Reason: batch mistake", mine[0]["details"])
        self.assertIn("show_deleted=1", mine[0]["href"])

    def test_activity_log_page_without_activity_still_loads(self):
        AccountingAuditLog.objects.filter(user=self.user).delete()
        self.page.goto(f"{self.live_server_url}/accounting-logs/")
        settle(self.page)
        self.assertEqual(self.page.locator("#auditLogTable").count(), 0)
        self.assertIn("Activity", self.page.inner_text("body"))
