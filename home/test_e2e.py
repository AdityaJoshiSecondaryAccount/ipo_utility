import os
import time
from contextlib import contextmanager
from datetime import timedelta

from django.contrib.auth.models import Group
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import expect, sync_playwright

from home.models import ClientDetail, CurrentIpoName, CustomUser, GroupDetail, Order
from e2e.browser import BrowserCase


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class AddClientEndToEndTest(BrowserCase):
    """Exercise the Add Client form in a real browser."""

    def setUp(self):
        # Create database fixtures before starting Playwright. Its synchronous
        # API owns an asyncio loop, and Django blocks synchronous ORM calls
        # while that loop is active.
        self.user = CustomUser.objects.create_user(
            username="e2e-broker",
            password="test-password-123",
            Expiry_Date=timezone.localdate() + timedelta(days=30),
        )
        broker_role = Group.objects.create(name="Broker")
        self.user.groups.add(broker_role)
        self.client_group = GroupDetail.objects.create(
            user=self.user,
            GroupName="TEST GROUP",
            MobileNo="7016868618",
        )

        self.start_browser()

    def tearDown(self):
        self._stop_browser()
        super().tearDown()

    def _stop_browser(self):
        self.stop_browser()

    @contextmanager
    def _step(self, name):
        """Print a readable result for every browser workflow step."""
        started_at = time.monotonic()
        print(f"\n[E2E][START] {name}", flush=True)
        try:
            yield
        except Exception as exc:
            elapsed = time.monotonic() - started_at
            current_url = self.page.url if self.page is not None else "browser unavailable"
            print(
                f"[E2E][FAIL]  {name} ({elapsed:.2f}s)\n"
                f"[E2E][URL]   {current_url}\n"
                f"[E2E][ERROR] {type(exc).__name__}: {exc}",
                flush=True,
            )
            raise
        else:
            elapsed = time.monotonic() - started_at
            print(
                f"[E2E][PASS]  {name} ({elapsed:.2f}s)\n"
                f"[E2E][URL]   {self.page.url}",
                flush=True,
            )

    def _open_home_card(self, card_name, expected_path):
        self.page.goto(f"{self.live_server_url}/")
        expect(self.page.get_by_role("heading", name="Current IPOs")).to_be_visible()
        expect(self.page.get_by_text("TEST IPO", exact=True)).to_be_visible()

        card_link = self.page.get_by_role("link", name=card_name, exact=True)
        expect(card_link).to_be_visible()
        with self.page.expect_navigation(wait_until="domcontentloaded"):
            card_link.click()

        self.assertTrue(
            self.page.url.endswith(expected_path),
            f"{card_name} opened unexpected URL: {self.page.url}",
        )
        self.assertNotIn("Server Error (500)", self.page.content())

    def _assert_order_form_controls(self, order_type):
        expected_fields = (
            "item_id",
            "datetime",
            "KostakQTY",
            "KostakRate",
            "KostakQTYSHNI",
            "KostakRateSHNI",
            "KostakQTYBHNI",
            "KostakRateBHNI",
            "SubjectToQTY",
            "SubjectToRate",
            "SubjectToQTYSHNI",
            "SubjectToRateSHNI",
            "SubjectToQTYBHNI",
            "SubjectToRateBHNI",
            "PremiumQTY",
            "PremiumRate",
            "CallQTY",
            "CallStrikePrice",
            "CallRate",
            "PutQTY",
            "PutStrikePrice",
            "PutRate",
        )
        form = self.page.locator("#placeOrderForm")
        expect(form).to_be_visible()
        for field_name in expected_fields:
            expect(form.locator(f'[name="{field_name}"]')).to_be_attached()

        expect(self.page.locator("#btnPlaceOnly")).to_be_visible()
        expect(self.page.locator("#btnPlaceWithTelegram")).to_be_visible()
        expect(self.page.locator("#btnSendWhatsApp")).to_have_count(0)
        print(
            f"[E2E][INFO]  {order_type}: verified {len(expected_fields)} form fields "
            "and both available order action buttons; WhatsApp is absent",
            flush=True,
        )

    def _place_order(self, order_type, ipo_id, rate):
        self._open_home_card(order_type, f"/{ipo_id}/{order_type}")
        expect(
            self.page.get_by_role("heading", name=order_type, exact=True)
        ).to_be_visible()
        self._assert_order_form_controls(order_type)

        form = self.page.locator("#placeOrderForm")
        form.locator('[name="item_id"]').select_option(label="TEST GROUP")
        form.locator('[name="datetime"]').fill("2026-09-11T10:30")
        form.locator('[name="KostakQTY"]').fill("1")
        form.locator('[name="KostakRate"]').fill(str(rate))

        with self.page.expect_navigation(wait_until="domcontentloaded"):
            self.page.locator("#btnPlaceOnly").click()

        success_message = f"{order_type.title()} order placed successfully."
        expect(self.page.get_by_text(success_message)).to_be_visible()
        expect(
            self.page.get_by_role("heading", name="Recent Orders", exact=False)
        ).to_be_visible()

    def _verify_card_pages(self, ipo_id):
        with self._step("BUY card: validate form and place a BUY order"):
            self._place_order("BUY", ipo_id, 100)

        with self._step("SELL card: validate form and place a SELL order"):
            self._place_order("SELL", ipo_id, 110)

        with self._step("Orders card: validate filters, table, BUY and SELL rows"):
            self._open_home_card("Orders", f"/{ipo_id}/Order")
            expect(self.page.get_by_role("heading", name="Order", exact=True)).to_be_visible()
            for selector in ("#Groupfilter", "#OrderCategoryFilter", "#InvestorTypeFilter"):
                expect(self.page.locator(selector)).to_be_visible()
            orders_table = self.page.locator("#example")
            expect(orders_table).to_be_visible()
            expect(orders_table.get_by_text("BUY", exact=True).first).to_be_visible()
            expect(orders_table.get_by_text("SELL", exact=True).first).to_be_visible()

        with self._step("Analysis card: validate tabs and submit analysis inputs"):
            self._open_home_card("Analysis", f"/{ipo_id}/Dashboard/A")
            expect(self.page.get_by_role("heading", name="Analysis", exact=True)).to_be_visible()
            for tab_id in ("#inlineRadio1", "#inlineRadio2", "#inlineRadio3"):
                expect(self.page.locator(tab_id)).to_be_visible()
            analysis_form = self.page.locator(f'form[action="/{ipo_id}/DashboardForm/A"]')
            expect(analysis_form).to_be_visible()
            analysis_form.locator('[name="ExpecetdRetailApplication"]').fill("2500000")
            analysis_form.locator('[name="ExpecetdSHNIApplication"]').fill("150000")
            analysis_form.locator('[name="ExpecetdBHNIApplication"]').fill("50000")
            analysis_form.locator('[name="ProfitMargin"]').fill("15")
            analysis_form.locator('[name="Premium"]').fill("20")
            with self.page.expect_navigation(wait_until="domcontentloaded"):
                analysis_form.get_by_role("button", name="Submit", exact=True).click()
            self.assertTrue(self.page.url.endswith(f"/{ipo_id}/Dashboard/A"))
            expect(self.page.locator("#bootstrapdatatable").first).to_be_visible()

        with self._step("App. Buy Order (PAN): validate filters, actions and table"):
            self._open_home_card(
                "App. Buy Order (PAN)", f"/{ipo_id}/OrderDetail/BUY"
            )
            expect(
                self.page.get_by_role("heading", name="App.-Buy Order Detail", exact=True)
            ).to_be_visible()
            for selector in ("#category", "#category1", "#category2", "#frate"):
                expect(self.page.locator(selector)).to_be_visible()
            expect(self.page.locator("#bootstrapdatatable:visible")).to_be_visible()
            expect(self.page.get_by_role("button", name="Search", exact=False).first).to_be_visible()
            expect(self.page.get_by_role("button", name="Download", exact=False).first).to_be_visible()

        with self._step("App. Sell Order (PAN): validate filters, actions and table"):
            self._open_home_card(
                "App. Sell Order (PAN)", f"/{ipo_id}/OrderDetail/SELL"
            )
            expect(
                self.page.get_by_role(
                    "heading", name="App.-Sell Order Detail", exact=True
                )
            ).to_be_visible()
            for selector in ("#category", "#category1", "#category2", "#frate"):
                expect(self.page.locator(selector)).to_be_visible()
            expect(self.page.locator("#bootstrapdatatable:visible")).to_be_visible()
            expect(self.page.get_by_role("button", name="Search", exact=False).first).to_be_visible()
            expect(self.page.get_by_role("button", name="Download", exact=False).first).to_be_visible()

        with self._step("Client Wise Billing: validate filters, actions and table"):
            self._open_home_card("Client Wise Billing", f"/{ipo_id}/Billing")
            expect(
                self.page.get_by_role("heading", name="Client Wise Billing", exact=True)
            ).to_be_visible()
            billing_form = self.page.locator('form[name="BillingFilter"]').first
            expect(billing_form).to_be_visible()
            for field_name in ("Groupfilter", "IPOTypefilter", "InvestorTypeFilter"):
                expect(billing_form.locator(f'[name="{field_name}"]')).to_be_visible()
            expect(self.page.locator("#searchButton")).to_be_visible()
            expect(self.page.get_by_role("button", name="Download", exact=False).first).to_be_visible()
            expect(self.page.locator("#example")).to_be_visible()

        with self._step("Group Wise Billing: validate table and export action"):
            self._open_home_card("Group Wise Billing", f"/{ipo_id}/Status")
            expect(
                self.page.get_by_role("heading", name="Group Wise Billing", exact=True)
            ).to_be_visible()
            expect(
                self.page.get_by_role("button", name="Export to Excel", exact=True)
            ).to_be_visible()
            expect(self.page.locator("#example")).to_be_visible()

    def _login(self):
        login_response = self.page.goto(f"{self.live_server_url}/login")
        self.assertIsNotNone(login_response, "The login page returned no response.")
        self.assertEqual(
            login_response.status,
            200,
            f"Login page returned HTTP {login_response.status}:\n{self.page.content()}",
        )
        self.page.locator("#inputEmail").fill("e2e-broker")
        self.page.locator("#inputPassword").fill("test-password-123")
        self.page.get_by_role("button", name="Login").click()
        self.page.wait_for_url(f"{self.live_server_url}/")

    def test_user_can_add_client_from_modal(self):
        self._login()

        # Open the page and verify that clicking ADD CLIENT opens the modal.
        self.page.goto(f"{self.live_server_url}/ClientSetup")
        self.page.get_by_role("button", name="ADD CLIENT").click()
        add_client_modal = self.page.locator("#ADDCLIENT")
        expect(add_client_modal).to_be_visible()

        # Fill and submit the form.
        add_client_modal.locator("#PANNo").fill("ABCDE1234F")
        add_client_modal.locator("#Name").fill("Test Client")
        add_client_modal.locator("#group").select_option(label="TEST GROUP")
        add_client_modal.locator('[name="ClientIdDpId"]').fill("1234567890123456")
        add_client_modal.get_by_role("button", name="Submit Form").click()

        # Confirm both the visible result and the saved database record.
        self.page.wait_for_url(f"{self.live_server_url}/ClientSetup")
        expect(self.page.get_by_text("Client Added successfully.")).to_be_visible()
        expect(
            self.page.get_by_role("cell", name="ABCDE1234F", exact=True)
        ).to_be_visible()

        # Leave Playwright's asyncio context before querying with Django's
        # synchronous ORM.
        self._stop_browser()
        self.assertTrue(
            ClientDetail.objects.filter(
                user=self.user,
                PANNo="ABCDE1234F",
                Name="TEST CLIENT",
                Group=self.client_group,
            ).exists()
        )

    def test_create_ipo_and_verify_all_home_card_pages(self):
        with self._step("Login as the test broker"):
            self._login()

        with self._step("Create a Mainboard IPO through the ADD IPO modal"):
            self.page.goto(f"{self.live_server_url}/IPOSETUP")
            self.page.get_by_role("button", name="ADD IPO").click()
            add_ipo_modal = self.page.locator("#ADDIPO")
            expect(add_ipo_modal).to_be_visible()

            add_ipo_modal.locator("#name").fill("Test IPO")
            add_ipo_modal.locator("#IPOPrice").fill("150")
            add_ipo_modal.locator('[name="TotalIPOSzie"]').fill("1200")
            add_ipo_modal.locator("#LotSize").fill("100")
            add_ipo_modal.locator("#LotSizeSH").fill("1400")
            add_ipo_modal.locator("#LotSizeBH").fill("6700")
            add_ipo_modal.locator('[name="RetailPercentage"]').fill("35")
            add_ipo_modal.locator('[name="BHNIPercentage"]').fill("10")
            add_ipo_modal.locator('[name="SHNIPercentage"]').fill("5")
            add_ipo_modal.locator('[name="Remark"]').fill("Created by Playwright")
            add_ipo_modal.get_by_role("button", name="Submit Form").click()

            self.page.wait_for_url(f"{self.live_server_url}/IPOSETUP")
            expect(self.page.get_by_text("IPO Added successfully.")).to_be_visible()
            ipo_link = self.page.get_by_role("link", name="TEST IPO", exact=True)
            expect(ipo_link).to_be_visible()
            ipo_id = int(ipo_link.get_attribute("href").strip("/").split("/")[0])
            print(f"[E2E][INFO]  Created TEST IPO with id={ipo_id}", flush=True)

        self._verify_card_pages(ipo_id)

        # Stop Playwright before using Django's synchronous ORM.
        self._stop_browser()
        ipo = CurrentIpoName.objects.get(user=self.user, IPOName="TEST IPO")
        self.assertEqual(ipo.IPOType, "MAINBOARD")
        self.assertEqual(ipo.IPOPrice, 150)
        self.assertEqual(ipo.PreOpenPrice, 150)
        self.assertEqual(ipo.LotSizeRetail, 100)
        self.assertEqual(ipo.LotSizeSHNI, 1400)
        self.assertEqual(ipo.LotSizeBHNI, 6700)
        self.assertEqual(ipo.TotalIPOSzie, "1200")
        self.assertEqual(ipo.RetailPercentage, "35")
        self.assertEqual(ipo.BHNIPercentage, "10")
        self.assertEqual(ipo.SHNIPercentage, "5")
        self.assertEqual(ipo.Remark, "Created by Playwright")
        self.assertEqual(Order.objects.filter(user=self.user, OrderIPOName=ipo).count(), 2)
        self.assertSetEqual(
            set(
                Order.objects.filter(user=self.user, OrderIPOName=ipo).values_list(
                    "OrderType", flat=True
                )
            ),
            {"BUY", "SELL"},
        )
        print(
            "\n[E2E][SUMMARY] PASS - IPO created, 2 orders placed, "
            "and all 8 home card pages verified.",
            flush=True,
        )
