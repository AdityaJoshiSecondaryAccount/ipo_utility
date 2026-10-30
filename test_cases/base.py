"""
Shared plumbing for the page-level Playwright E2E tests.

Persistence model
-----------------
All page tests run inside ONE `manage.py test` process (see run_tests.py), so
they share:
  * one test database  - PersistentLiveServerTestCase skips Django's per-test
                         table flush, so BUY data is still there for SELL, and
                         BUY + SELL data is still there for the Orders page;
  * one Chromium window - started lazily on first use, closed at process exit.

Every test is written to be idempotent (get_or_create) and to count relative to
what already exists, so each page file can also be run on its own.
"""
import atexit
import contextlib
import json
import os
import re
import sys
import time
from collections import Counter

# Playwright's sync API runs an asyncio loop in the test thread; Django's ORM
# refuses to run inside it unless this is set. Must be set before Django checks.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import expect, sync_playwright

from home.models import CurrentIpoName, GroupDetail, Order, OrderDetail

User = get_user_model()

# PW_HEADLESS=1 -> no visible window (CI). Default is a visible maximized window.
HEADLESS = os.environ.get("PW_HEADLESS", "0") == "1"

USERNAME = "playwright_broker"
PASSWORD = "Password@123"
IPO_NAME = "RELIANCE GREEN ENERGY LTD"


# ------------------------------------------------------------------------------
# Shared browser (one window for the whole run)
# ------------------------------------------------------------------------------
_session = {}


def get_page():
    """Return the single shared Playwright page, launching Chromium on first use."""
    if "page" not in _session:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=HEADLESS,
            slow_mo=0 if HEADLESS else 300,
            args=["--start-maximized"],
        )
        context = browser.new_context(no_viewport=True)
        _session.update(pw=pw, browser=browser, context=context, page=context.new_page())
        atexit.register(_close_session)
    return _session["page"]


def _close_session():
    for key in ("context", "browser"):
        try:
            _session[key].close()
        except Exception:
            pass
    try:
        _session["pw"].stop()
    except Exception:
        pass
    _session.clear()


def pause_for_inspection(page_name):
    """
    Keep the browser open for manual inspection. Only the LAST page of a run
    pauses (run_tests.py sets PW_LAST_PAGE); run on its own, a page always pauses.
    """
    if HEADLESS or os.environ.get("PW_NO_PAUSE") == "1":
        return
    last = os.environ.get("PW_LAST_PAGE")
    if last and last != page_name:
        return
    print("\n" + "=" * 70, flush=True)
    print(" Tests finished - the browser is still open for inspection.", flush=True)
    try:
        input(" Press Enter to close browser... ")
    except EOFError:
        print(" (no interactive stdin; closing)", flush=True)


def settle(page, timeout=8000):
    """
    Wait for the page to go network-idle, but don't hang on slow third-party
    resources (CDN fonts etc.): after `timeout` carry on, since every step
    asserts on the DOM it needs anyway.
    """
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeout:
        page.wait_for_load_state("load")


def parse_multipart(post_data):
    """Return {field: value} from a multipart/form-data body captured by Playwright."""
    return dict(re.findall(
        r'name="([^"]+)"\r\n\r\n(.*?)\r\n--', post_data or "", flags=re.S))


# ------------------------------------------------------------------------------
# Base test case
# ------------------------------------------------------------------------------
class PersistentLiveServerTestCase(StaticLiveServerTestCase):
    """
    Live-server test case that KEEPS its data between tests and test classes.

    StaticLiveServerTestCase flushes every table after each test; overriding
    _fixture_teardown makes the database accumulate for the whole run.
    """

    def _fixture_teardown(self):
        pass

    # ------------------------------------------------------------------ logging
    # One format for every page:
    #   <PAGE>  │ ▶ <what the test checks>   (test_method_name)
    #   <PAGE>  │    ↳ ordtyp=BUY            (one line per sub-case)
    #   <PAGE>  │    step 3/10: ...          (multi-step flows)
    #   <PAGE>  │ ✔ PASS  test_method_name  (4.2s)
    #   <PAGE>  │ ── page done: 38 tests · 36 passed · ...
    LOG_TAG = None                                   # defaults to PAGE_NAME, e.g. "ORDER DETAIL"
    _RESULT_MARKS = {"PASS": "✔", "FAIL": "✘", "ERROR": "✘", "SKIP": "–",
                     "XFAIL": "✔", "XPASS": "!"}

    @classmethod
    def log_tag(cls):
        return (cls.LOG_TAG or getattr(cls, "PAGE_NAME", None) or cls.__name__).upper().replace("_", " ")

    @classmethod
    def _emit(cls, indent, msg):
        print(f"{cls.log_tag():<12} │ {'   ' * indent}{msg}", flush=True)

    def log(self, msg, indent=1):
        """A progress line inside the current test."""
        self._emit(indent, msg)

    def step(self, number, total, msg):
        self._emit(1, f"step {number}/{total}: {msg}")

    @contextlib.contextmanager
    def subTest(self, msg=None, **params):
        label = ", ".join(f"{k}={v}" for k, v in params.items()) or (msg or "")
        self._emit(1, f"↳ {label}")
        with (super().subTest(msg, **params) if msg is not None else super().subTest(**params)):
            yield

    @classmethod
    def _stats(cls):
        if "_stats_counter" not in cls.__dict__:
            cls._stats_counter = Counter()
        return cls._stats_counter

    def run(self, result=None):
        if result is None:
            return super().run(result)
        lists = ("failures", "errors", "skipped", "expectedFailures", "unexpectedSuccesses")
        before = {name: len(getattr(result, name, [])) for name in lists}
        name = self._testMethodName
        self._emit(0, f"▶ {name[5:].replace('_', ' ') if name.startswith('test_') else name}   ({name})")
        started = time.perf_counter()
        outcome = super().run(result)
        grew = {n: len(getattr(result, n, [])) - before[n] for n in lists}
        status = ("ERROR" if grew["errors"] else "FAIL" if grew["failures"] else
                  "XPASS" if grew["unexpectedSuccesses"] else "SKIP" if grew["skipped"] else
                  "XFAIL" if grew["expectedFailures"] else "PASS")
        type(self)._stats()[status] += 1
        note = "  (known app bug - expected failure)" if status == "XFAIL" else ""
        self._emit(0, f"{self._RESULT_MARKS[status]} {status:<5} {name}  ({time.perf_counter() - started:.1f}s){note}")
        return outcome

    @classmethod
    def log_summary(cls):
        if cls.__dict__.get("_summary_done") or not cls._stats():
            return
        cls._summary_done = True
        st = cls._stats()
        total = sum(st.values())
        parts = [f"{total} tests", f"{st['PASS']} passed"]
        for key, word in (("FAIL", "failed"), ("ERROR", "errors"), ("SKIP", "skipped"),
                          ("XFAIL", "known bugs (expected failures)"), ("XPASS", "UNEXPECTED successes")):
            if st[key]:
                parts.append(f"{st[key]} {word}")
        cls._emit(0, "── page done: " + " · ".join(parts))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page = get_page()

    @classmethod
    def tearDownClass(cls):
        cls.log_summary()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.broker_group, _ = Group.objects.get_or_create(name="Broker")
        self.user, _ = User.objects.get_or_create(
            username=USERNAME, defaults={"email": "broker@example.com"})
        self.user.set_password(PASSWORD)
        self.user.Order_limit = None  # an earlier page's limit test must not leak
        self.user.save()
        self.user.groups.add(self.broker_group)

        # MAINBOARD so the SHNI / BHNI fields render
        self.ipo, _ = CurrentIpoName.objects.get_or_create(
            user=self.user,
            IPOName=IPO_NAME,
            defaults={
                "IPOType": "MAINBOARD",
                "IPOPrice": 100.0,
                "PreOpenPrice": 250.0,
                "LotSizeRetail": 100,
                "LotSizeSHNI": 1400,
                "LotSizeBHNI": 7000,
                "Active": True,
            },
        )
        GroupDetail.objects.get_or_create(user=self.user, GroupName="ALPHA TRADERS")
        GroupDetail.objects.get_or_create(user=self.user, GroupName="BETA INVESTORS")

        # Log in through the test client and hand the session to the browser
        self.client.login(username=USERNAME, password=PASSWORD)
        self.page.context.add_cookies([{
            "name": "sessionid",
            "value": self.client.cookies["sessionid"].value,
            "domain": "localhost",
            "path": "/",
        }])

    def all_orders(self):
        """Every order on the IPO, BUY and SELL."""
        return Order.objects.filter(user=self.user, OrderIPOName_id=self.ipo.id)

    def all_details(self):
        return OrderDetail.objects.filter(user=self.user, Order__OrderIPOName_id=self.ipo.id)


# ------------------------------------------------------------------------------
# BUY / SELL page flow (the two pages are the same form with a different type)
# ------------------------------------------------------------------------------
class OrderPageFlow:
    """
    Mixin holding the full workflow for /<ipo>/BUY or /<ipo>/SELL.

    Every "Place <TYPE> Order" click is verified on three levels:
      1. Network: the exact POST (URL, CSRF header, form fields) and the JSON reply
      2. UI:      redirect back to the clean page URL and the new top row in the table
      3. DB:      Order row (type, tier, category, qty, rate, method, remark) and
                  its OrderDetail rows

    Subclasses set ORDER_TYPE, PAGE_NAME, NEW_GROUP_NAME and RATE_SHIFT.
    """

    ORDER_TYPE = None       # "BUY" | "SELL"
    PAGE_NAME = None        # "buy" | "sell" (matches run_tests.py)
    NEW_GROUP_NAME = None   # group created through the UI in step 3
    RATE_SHIFT = 0          # added to every rate so BUY and SELL rows are tellable apart

    # -- helpers ---------------------------------------------------------------
    @property
    def page_url(self):
        return f"{self.live_server_url}/{self.ipo.id}/{self.ORDER_TYPE}"

    def rate(self, base):
        return base + self.RATE_SHIFT

    def orders(self):
        """Orders of THIS page's type only."""
        return self.all_orders().filter(OrderType=self.ORDER_TYPE)

    def expect_orders(self, placed_so_far):
        self.assertEqual(self.orders().count(), self.base_orders + placed_so_far)

    def details_of(self, order):
        return OrderDetail.objects.filter(Order_id=order.id).count()

    def capture_next_post(self):
        """
        Route-intercept the page's POST: forward it to the real server, record
        request + response body, and pass the response through untouched.
        (Reading the body after the fact races with window.location.replace.)
        """
        captured = {}
        pattern = re.compile(rf"/({self.ORDER_TYPE}/{self.ipo.id}/|{self.ipo.id}/{self.ORDER_TYPE})")

        def handler(route, request):
            if request.method != "POST":
                return route.continue_()
            response = route.fetch()
            captured["request"] = request
            captured["status"] = response.status
            captured["body"] = response.body()
            route.fulfill(response=response)

        self.page.route(lambda url: pattern.search(url) is not None, handler)
        return captured

    def click_place_and_capture(self):
        captured = self.capture_next_post()
        try:
            self.page.click("#btnPlaceOnly")
            for _ in range(300):
                if "body" in captured:
                    break
                self.page.wait_for_timeout(100)
        finally:
            self.page.unroute_all(behavior="wait")
        self.assertIn("body", captured, f"no {self.ORDER_TYPE} POST was fired by the click")
        return captured

    def place_order(self):
        """Click Place, verify the network contract, return the form fields sent."""
        page = self.page
        page_url_before = page.url
        captured = self.click_place_and_capture()
        request = captured["request"]

        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url, page_url_before, "fetch must POST to the page's own URL")
        self.assertTrue(request.headers.get("x-csrftoken"), "CSRF header missing on fetch")
        self.assertIn("multipart/form-data", request.headers.get("content-type", ""))
        sent = parse_multipart(request.post_data)
        self.assertEqual(sent.get("placeOrderOnly"), "true")

        self.assertEqual(captured["status"], 200)
        body = json.loads(captured["body"])
        self.assertEqual(body["status"], "success")
        # JS handler calls window.location.replace(cleanOrderUrl)
        page.wait_for_url(self.page_url)
        settle(page)
        return sent

    def top_row(self):
        """Newest row of the orders table (page lists orders by -id, last 5)."""
        return self.page.locator("#bootstrapdatatable tbody tr").first

    def assert_top_row(self, group, category, investor, qty, rate, remark="-"):
        cells = self.top_row().locator("td")
        expect(cells.nth(0)).to_have_text(group)
        expect(cells.nth(1)).to_have_text(self.ORDER_TYPE)
        expect(cells.nth(2)).to_have_text(category)
        expect(cells.nth(3)).to_have_text(investor)
        expect(cells.nth(5)).to_have_text(str(qty))
        expect(cells.nth(6)).to_have_text(f"{rate:.2f}")
        expect(cells.nth(8)).to_have_text(remark)

    def open_page(self, group=None):
        self.page.goto(self.page_url)
        settle(self.page)
        if group:
            self.page.select_option("#validationCustom04", label=group)

    def table_rows_expected(self):
        return min(self.all_orders().count(), 5)  # template shows the 5 newest

    # -- workflow --------------------------------------------------------------
    def run_order_page_flow(self):
        page, T = self.page, self.ORDER_TYPE
        r = self.rate
        self.base_orders = self.orders().count()
        expected_details = self.all_details().count()

        # ---- Step 1: UI structure --------------------------------------------
        self.step(1, 10, f"Opening {T} page and verifying UI columns")
        self.open_page()
        expect(page.locator(f'h3:has-text("{T}")').first).to_be_visible()
        expect(page.locator('label[name="Retailinvestor"]').first).to_contain_text("Retail")
        expect(page.locator('label[name="SHNIinvestor"]').first).to_contain_text("SHNI")
        expect(page.locator('label[name="BHNIinvestor"]').first).to_contain_text("BHNI")
        expect(page.locator("#btnPlaceOnly")).to_be_enabled()
        expect(page.locator("#btnPlaceOnly")).to_contain_text(f"Place {T} Order")
        expect(page.locator("#bootstrapdatatable tbody tr")).to_have_count(self.table_rows_expected())
        # Data from earlier pages is visible here: the group of the newest order
        # (any type) comes pre-selected.
        if Order.objects.exists():
            expect(page.locator("#validationCustom04")).to_have_value(
                Order.objects.latest("id").OrderGroup.GroupName)

        # ---- Step 2: group validation ----------------------------------------
        self.step(2, 10, f"Testing group selection validation")
        # The page pre-selects the group of the most recent order (shared by BUY and
        # SELL), so clear the dropdown to really have "no group".
        page.eval_on_selector("#validationCustom04", "el => { el.value = ''; el.dispatchEvent(new Event('change')); }")
        expect(page.locator("#validationCustom04")).to_have_value("")
        page.fill('input[name="KostakQTY"]', "5")
        page.fill('input[name="KostakRate"]', str(r(500)))
        page.click("#btnPlaceOnly")
        page.wait_for_timeout(500)
        self.expect_orders(0)
        self.assertEqual(self.all_details().count(), expected_details)

        # ---- Step 3: add group via the form ----------------------------------
        self.step(3, 10, f"Adding new group '{self.NEW_GROUP_NAME}' via form")
        page.locator("#GroupName").fill(self.NEW_GROUP_NAME)
        page.locator('button.addgc:has-text("Add Group")').click()
        settle(page)
        self.assertTrue(GroupDetail.objects.filter(user=self.user, GroupName=self.NEW_GROUP_NAME).exists())
        expect(page.locator("#validationCustom04")).to_have_value(self.NEW_GROUP_NAME)

        # ---- Step 4: Retail Kostak -------------------------------------------
        self.step(4, 10, f"Placing Retail Kostak {T} order")
        page.select_option("#validationCustom04", label="ALPHA TRADERS")
        page.fill('input[name="KostakQTY"]', "5")
        page.fill('input[name="KostakRate"]', str(r(450)))
        sent = self.place_order()

        self.assertEqual(sent["KostakQTY"], "5")
        self.assertEqual(sent["KostakRate"], str(r(450)))
        self.expect_orders(1)
        order = self.orders().get(OrderCategory="Kostak", InvestorType="RETAIL", Rate=r(450))
        self.assertEqual(order.OrderGroup.GroupName, "ALPHA TRADERS")
        self.assertEqual(order.OrderType, T)
        self.assertEqual(int(order.Quantity), 5)
        self.assertIsNone(order.remark)
        self.assertEqual(self.details_of(order), 5)
        expected_details += 5
        self.assert_top_row("ALPHA TRADERS", "Kostak", "RETAIL", 5, r(450.0))
        expect(page.locator(".alert").first).to_be_visible()

        # ---- Step 5: Retail Subject To + Premium tick mark -------------------
        self.step(5, 10, f"Placing Retail Subject To order with tick mark")
        self.open_page("ALPHA TRADERS")
        page.fill('input[name="SubjectToQTY"]', "3")
        page.fill('input[name="SubjectToRate"]', str(r(1200)))
        page.check("#subjectToIsPremiumRetail")
        sent = self.place_order()

        self.assertEqual(sent["SubjectToQTY"], "3")
        self.expect_orders(2)
        order = self.orders().get(OrderCategory="Subject To", InvestorType="RETAIL", Rate=r(1200))
        self.assertEqual(order.Method, "Premium")
        self.assertEqual(int(order.Quantity), 3)
        self.assertEqual(self.details_of(order), 3)
        expected_details += 3
        self.assert_top_row("ALPHA TRADERS", "Subject To", "RETAIL", 3, r(1200.0))
        expect(self.top_row().locator("td").nth(4)).to_have_text("Premium")

        # ---- Step 6: SHNI + BHNI together ------------------------------------
        self.step(6, 10, f"Placing simultaneous SHNI and BHNI orders for BETA INVESTORS")
        self.open_page("BETA INVESTORS")
        page.fill('input[name="KostakQTYSHNI"]', "2")
        page.fill('input[name="KostakRateSHNI"]', str(r(600)))
        page.fill('input[name="KostakQTYBHNI"]', "4")
        page.fill('input[name="KostakRateBHNI"]', str(r(700)))
        sent = self.place_order()

        self.assertEqual((sent["KostakQTYSHNI"], sent["KostakQTYBHNI"]), ("2", "4"))
        self.expect_orders(4)
        shni = self.orders().get(InvestorType="SHNI", Rate=r(600))
        bhni = self.orders().get(InvestorType="BHNI", Rate=r(700))
        self.assertEqual((int(shni.Quantity), shni.OrderCategory), (2, "Kostak"))
        self.assertEqual((int(bhni.Quantity), bhni.OrderCategory), (4, "Kostak"))
        self.assertEqual(shni.OrderGroup.GroupName, "BETA INVESTORS")
        self.assertEqual(bhni.OrderGroup.GroupName, "BETA INVESTORS")
        self.assertEqual(self.details_of(shni), 2)
        self.assertEqual(self.details_of(bhni), 4)
        expected_details += 6
        rows = page.locator("#bootstrapdatatable tbody tr")
        expect(rows).to_have_count(self.table_rows_expected())
        expect(rows.nth(0).locator("td").nth(3)).to_have_text("BHNI")  # newest first
        expect(rows.nth(1).locator("td").nth(3)).to_have_text("SHNI")

        # ---- Step 7: free-text remark ----------------------------------------
        self.step(7, 10, f"Placing order with custom remarks")
        self.open_page("ALPHA TRADERS")
        page.fill('input[name="KostakQTY"]', "1")
        page.fill('input[name="KostakRate"]', str(r(480)))
        page.fill("#remarkInput", "Urgent client confirmation")
        sent = self.place_order()

        self.assertEqual(sent["remark_text"], "Urgent client confirmation")
        self.expect_orders(5)
        order = self.orders().get(Rate=r(480))
        self.assertEqual(order.remark, {"text": "Urgent client confirmation"})
        self.assertEqual(self.details_of(order), 1)
        expected_details += 1
        self.assert_top_row("ALPHA TRADERS", "Kostak", "RETAIL", 1, r(480.0),
                            remark="Urgent client confirmation")

        # ---- Step 8: dropdown remark -----------------------------------------
        self.step(8, 10, f"Placing order with 'Shareholder Application' dropdown remark")
        self.open_page("ALPHA TRADERS")
        page.fill('input[name="KostakQTY"]', "1")
        page.fill('input[name="KostakRate"]', str(r(490)))
        page.click("#remarkDropdownBtn")
        page.click('.dropdown-item:has-text("Shareholder Application")')
        expect(page.locator(".remark-tag")).to_have_count(1)  # chip shows before submit
        expect(page.locator(".remark-tag")).to_contain_text("Shareholder Application")
        sent = self.place_order()

        self.assertEqual(sent["remark_tags"], '["Shareholder Application"]')
        self.expect_orders(6)
        order = self.orders().get(Rate=r(490))
        self.assertEqual(order.remark, {"tags": ["Shareholder Application"]})
        self.assertEqual(self.details_of(order), 1)
        expected_details += 1
        self.assert_top_row("ALPHA TRADERS", "Kostak", "RETAIL", 1, r(490.0),
                            remark="Shareholder Application")

        # ---- Step 9: dropdown tag + free text --------------------------------
        self.step(9, 10, f"Placing order with dropdown tag AND free text")
        self.open_page("BETA INVESTORS")
        page.fill('input[name="KostakQTY"]', "2")
        page.fill('input[name="KostakRate"]', str(r(495)))
        page.click("#remarkDropdownBtn")
        page.click('.dropdown-item:has-text("Shareholder Application")')
        page.fill("#remarkInput", "Call before allotment")
        self.place_order()

        self.expect_orders(7)
        order = self.orders().get(Rate=r(495))
        self.assertEqual(order.remark, {
            "tags": ["Shareholder Application"],
            "text": "Call before allotment",
        })
        self.assertEqual(self.details_of(order), 2)
        expected_details += 2
        self.assert_top_row("BETA INVESTORS", "Kostak", "RETAIL", 2, r(495.0),
                            remark="Shareholder Application - Call before allotment")

        # ---- Step 10: broker order limit -------------------------------------
        self.step(10, 10, f"Enforcing broker order limit")
        used = self.all_details().count()
        self.assertEqual(used, expected_details)
        limit = used + 2                      # room for only 2 more
        self.user.Order_limit = limit
        self.user.save()

        self.open_page("ALPHA TRADERS")
        page.fill('input[name="KostakQTY"]', "5")
        page.fill('input[name="KostakRate"]', str(r(510)))
        # The view redirects instead of returning JSON; the page's fetch handler
        # then reloads. Observe the POST only, not the JSON contract.
        captured = self.click_place_and_capture()
        self.assertNotEqual(captured["status"], 500)
        settle(page)

        self.expect_orders(7)
        self.assertFalse(self.orders().filter(Rate=r(510)).exists())
        self.assertEqual(self.all_details().count(), used)
        # The server did emit the limit error (flashed on the redirected page that
        # the fetch consumed) ...
        self.assertIn(f"You have reached the limit of {limit} OrderDetail.",
                      captured["body"].decode("utf-8", "replace"))
        # ... but it is not JSON, so the page cannot show it. KNOWN APP BUG: the
        # message is swallowed by fetch() and the reloaded page shows no alert.
        # Flip this to expect(...).to_contain_text(...) once the view returns JSON.
        self.assertEqual(page.locator(".alert").count(), 0)

        self.user.Order_limit = None          # leave no limit behind for later pages
        self.user.save()

        self.log(f"done: {self.orders().count()} {T} orders in DB | "
                 f"all orders: {self.all_orders().count()} | OrderDetails: {self.all_details().count()}")
