import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse

from home.models import CurrentIpoName, CustomUser, GroupDetail, Order


class WhatsAppWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse("whatsapp:webhook")

        # Create test broker and customer group
        self.user = CustomUser.objects.create_user(
            username="testbroker",
            password="testpassword123",
            Broker_id="B001",
        )
        self.group = GroupDetail.objects.create(
            user=self.user,
            GroupName="VIP TRADERS",
            MobileNo="7016868618",
            Active=True,
        )
        self.ipo = CurrentIpoName.objects.create(
            user=self.user,
            IPOName="ACME CORP IPO",
            IPOPrice=100.0,
            LotSizeRetail=100,
            LotSizeSHNI=1000,
            LotSizeBHNI=2000,
            Active=True,
        )
        self.order = Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo,
            OrderType="BUY",
            Rate=105.0,
            Quantity=500.0,
            OrderCategory="Kostak",
            Amount=52500.0,
            OrderDate="2026-09-12",
            InvestorType="RETAIL",
            Active=True,
        )

    def test_get_verification_success(self):
        """GET request with matching verify_token should return challenge with 200."""
        response = self.client.get(self.webhook_url, {
            "hub.mode": "subscribe",
            "hub.verify_token": "ADwealth_WA_Webhook_2026",
            "hub.challenge": "challenge_token_abc123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), "challenge_token_abc123")

    def test_get_verification_failure_invalid_token(self):
        """GET request with wrong verify_token should return 403."""
        response = self.client.get(self.webhook_url, {
            "hub.mode": "subscribe",
            "hub.verify_token": "WRONG_TOKEN",
            "hub.challenge": "challenge_token_abc123",
        })
        self.assertEqual(response.status_code, 403)

    def test_post_status_event_handled_gracefully(self):
        """POST with delivery/read receipt status update returns 200."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "1287337667797572",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "919999999999", "phone_number_id": "1287337667797572"},
                        "statuses": [{"id": "wamid.123", "status": "delivered", "timestamp": "1710000000"}]
                    },
                    "field": "messages"
                }]
            }]
        }
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), "EVENT_RECEIVED")

    @patch("whatsapp.views.upload_media")
    @patch("whatsapp.views.send_image_message")
    def test_post_button_reply_view_orders_success(self, mock_send_image, mock_upload_media):
        """POST with 'view_orders' button reply finds customer orders and sends order summary image."""
        mock_upload_resp = MagicMock(ok=True, status_code=200, text="OK")
        mock_upload_resp.json.return_value = {"id": "meta_media_id_999"}
        mock_upload_media.return_value = mock_upload_resp
        mock_send_image.return_value = MagicMock(ok=True, status_code=200, text="OK")

        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "1287337667797572",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "1287337667797572", "phone_number_id": "1287337667797572"},
                        "contacts": [{"profile": {"name": "VIP Trader"}, "wa_id": "917016868618"}],
                        "messages": [{
                            "from": "917016868618",
                            "id": "wamid.HBgMOTE3MDE2ODY4NjE4FQIAEhggQ0RFRjEyMwA=",
                            "timestamp": "1710000000",
                            "type": "button",
                            "button": {
                                "payload": "view_orders",
                                "text": "View Your Orders"
                            }
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), "EVENT_RECEIVED")
        mock_upload_media.assert_called_once()
        mock_send_image.assert_called_once_with(
            phone_number="917016868618",
            media_id="meta_media_id_999",
            caption="ACME CORP IPO Status - VIP TRADERS"
        )

    @patch("whatsapp.views.upload_media")
    @patch("whatsapp.views.send_image_message")
    def test_post_interactive_button_reply_view_orders(self, mock_send_image, mock_upload_media):
        """POST with interactive button reply format also triggers view_orders."""
        mock_upload_resp = MagicMock(ok=True, status_code=200, text="OK")
        mock_upload_resp.json.return_value = {"id": "meta_media_id_888"}
        mock_upload_media.return_value = mock_upload_resp
        mock_send_image.return_value = MagicMock(ok=True, status_code=200, text="OK")

        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "1287337667797572",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "1287337667797572", "phone_number_id": "1287337667797572"},
                        "messages": [{
                            "from": "917016868618",
                            "id": "wamid.INTERACTIVE_TEST_001",
                            "timestamp": "1710000000",
                            "type": "interactive",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "view_orders",
                                    "title": "View Your Orders"
                                }
                            }
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        mock_upload_media.assert_called_once()
        mock_send_image.assert_called_once()

    @patch("whatsapp.views.send_text_message")
    def test_post_button_reply_unregistered_number(self, mock_send_text):
        """POST with view_orders from unknown phone notifies user."""
        mock_send_text.return_value = MagicMock(ok=True)

        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "1287337667797572",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "from": "919999000000",
                            "id": "wamid.UNKNOWN_USER_1",
                            "timestamp": "1710000000",
                            "type": "button",
                            "button": {
                                "payload": "view_orders",
                                "text": "View Your Orders"
                            }
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        mock_send_text.assert_called_once_with(
            "919999000000",
            "Your mobile number is not registered with any customer account."
        )

    @patch("whatsapp.views.send_text_message")
    def test_post_button_reply_no_active_orders(self, mock_send_text):
        """POST with view_orders for customer with no active orders sends helpful text."""
        # Deactivate existing order
        self.order.Active = False
        self.order.save()

        mock_send_text.return_value = MagicMock(ok=True)

        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "1287337667797572",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "from": "917016868618",
                            "id": "wamid.NO_ORDERS_TEST_1",
                            "timestamp": "1710000000",
                            "type": "button",
                            "button": {
                                "payload": "view_orders",
                                "text": "View Your Orders"
                            }
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        mock_send_text.assert_called_once_with(
            "917016868618",
            "You currently have no active orders."
        )

    @patch("whatsapp.views.upload_media")
    @patch("whatsapp.views.send_image_message")
    def test_post_idempotency_duplicate_webhook_event(self, mock_send_image, mock_upload_media):
        """Duplicate message IDs in webhook retries are processed only once."""
        mock_upload_resp = MagicMock(ok=True, status_code=200, text="OK")
        mock_upload_resp.json.return_value = {"id": "meta_media_id_777"}
        mock_upload_media.return_value = mock_upload_resp
        mock_send_image.return_value = MagicMock(ok=True, status_code=200, text="OK")

        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "1287337667797572",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "from": "917016868618",
                            "id": "wamid.DUPLICATE_EVENT_ID_001",
                            "timestamp": "1710000000",
                            "type": "button",
                            "button": {
                                "payload": "view_orders",
                                "text": "View Your Orders"
                            }
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

        # First request
        res1 = self.client.post(self.webhook_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(mock_upload_media.call_count, 1)

        # Retry request with exact same message ID
        res2 = self.client.post(self.webhook_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res2.status_code, 200)
        # Call count should not increase
        self.assertEqual(mock_upload_media.call_count, 1)


class TemplateAndDataMismatchTests(TestCase):
    """
    Test suite specifically verifying:
    1. HTML status table template rendering accuracy.
    2. Zero data mismatch across IPOs (JIO vs BAJAJ isolation).
    3. Mathematical precision for Kostak, Subject To, Premium, and Options (Strike Prices).
    """
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testbroker_calc",
            password="testpassword123",
            Broker_id="B002",
        )
        self.group = GroupDetail.objects.create(
            user=self.user,
            GroupName="ALPHA TRADERS",
            MobileNo="9876543210",
            Active=True,
        )
        self.ipo_jio = CurrentIpoName.objects.create(
            user=self.user,
            IPOName="JIO IPO",
            IPOPrice=100.0,
            LotSizeRetail=50,
            LotSizeSHNI=500,
            LotSizeBHNI=1000,
            Active=True,
        )
        self.ipo_bajaj = CurrentIpoName.objects.create(
            user=self.user,
            IPOName="BAJAJ IPO",
            IPOPrice=200.0,
            LotSizeRetail=25,
            LotSizeSHNI=250,
            LotSizeBHNI=500,
            Active=True,
        )

    def test_multi_ipo_isolation_no_data_mismatch(self):
        """Verify orders from different IPOs never bleed into each other."""
        from whatsapp.services import build_order_summary_context

        # Create JIO Orders: 10 BUY @ 50 Kostak Retail
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=50.0,
            Quantity=10.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        # Create BAJAJ Orders: 20 SELL @ 80 Kostak Retail
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_bajaj,
            OrderType="SELL",
            Rate=80.0,
            Quantity=20.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        # 1. Fetch JIO Summary
        jio_orders = Order.objects.filter(OrderGroup=self.group, OrderIPOName=self.ipo_jio, Active=True)
        jio_ctx = build_order_summary_context(self.group, orders=jio_orders, ipo=self.ipo_jio)

        self.assertEqual(jio_ctx["IPOName"], self.ipo_jio)
        self.assertEqual(jio_ctx["dict_count"]["KostakRETAILBUYCount"], 10)
        self.assertEqual(jio_ctx["dict_avg"]["KostakRETAILBUYAvg"], 50.0)
        self.assertEqual(jio_ctx["dict_amount"]["KostakRETAILBUYAmount"], 500.0)
        self.assertEqual(jio_ctx["dict_count"].get("KostakRETAILSELLCount", 0), 0)
        self.assertEqual(jio_ctx["net_count"]["KostakRETAILNetCount"], 10)

        # 2. Fetch BAJAJ Summary
        bajaj_orders = Order.objects.filter(OrderGroup=self.group, OrderIPOName=self.ipo_bajaj, Active=True)
        bajaj_ctx = build_order_summary_context(self.group, orders=bajaj_orders, ipo=self.ipo_bajaj)

        self.assertEqual(bajaj_ctx["IPOName"], self.ipo_bajaj)
        self.assertEqual(bajaj_ctx["dict_count"].get("KostakRETAILBUYCount", 0), 0)
        self.assertEqual(bajaj_ctx["dict_count"]["KostakRETAILSELLCount"], 20)
        self.assertEqual(bajaj_ctx["dict_avg"]["KostakRETAILSELLAvg"], 80.0)
        self.assertEqual(bajaj_ctx["dict_amount"]["KostakRETAILSELLAmount"], 1600.0)
        self.assertEqual(bajaj_ctx["net_count"]["KostakRETAILNetCount"], -20)

    def test_options_strike_prices_math_accuracy(self):
        """Verify strike prices CALL / PUT calculations match views2.py exact formulas."""
        from whatsapp.services import build_order_summary_context

        # CALL Buy 100 @ 5, Sell 40 @ 8 on Strike 150
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            OrderCategory="CALL",
            InvestorType="OPTIONS",
            Method="150",
            Rate=5.0,
            Quantity=100.0,
            OrderDate="2026-09-15",
            Active=True,
        )
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="SELL",
            OrderCategory="CALL",
            InvestorType="OPTIONS",
            Method="150",
            Rate=8.0,
            Quantity=40.0,
            OrderDate="2026-09-15",
            Active=True,
        )

        # PUT Buy 50 @ 10, Sell 50 @ 6 on Strike 150
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            OrderCategory="PUT",
            InvestorType="OPTIONS",
            Method="150",
            Rate=10.0,
            Quantity=50.0,
            OrderDate="2026-09-15",
            Active=True,
        )
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="SELL",
            OrderCategory="PUT",
            InvestorType="OPTIONS",
            Method="150",
            Rate=6.0,
            Quantity=50.0,
            OrderDate="2026-09-15",
            Active=True,
        )

        orders = Order.objects.filter(OrderGroup=self.group, OrderIPOName=self.ipo_jio, Active=True)
        ctx = build_order_summary_context(self.group, orders=orders, ipo=self.ipo_jio)

        self.assertEqual(len(ctx["strike_prices"]), 1)
        sp = ctx["strike_prices"][0]
        self.assertEqual(sp["value"], "150")

        # CALL Net Qty = 100 - 40 = 60
        self.assertEqual(sp["call_total_count"], 60)
        # CALL Net Amount = (100 * 5) - (40 * 8) = 500 - 320 = 180
        self.assertEqual(sp["call_net_amount"], 180.0)
        # CALL Avg = 180 / 60 = 3.0
        self.assertEqual(sp["call_avg"], 3.0)

        # PUT Net Qty = 50 - 50 = 0
        self.assertEqual(sp["put_total_count"], 0)
        # PUT Net Amount when count is 0 = Sell Amount - Buy Amount = 300 - 500 = -200
        self.assertEqual(sp["put_net_amount"], -200.0)

    def test_status_table_template_html_rendering(self):
        """Verify status_table_template.html renders without error and displays IPO name in title."""
        from django.template.loader import render_to_string
        from whatsapp.services import build_order_summary_context

        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=15.0,
            Quantity=100.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        orders = Order.objects.filter(OrderGroup=self.group, OrderIPOName=self.ipo_jio, Active=True)
        ctx = build_order_summary_context(self.group, orders=orders, ipo=self.ipo_jio)
        html_out = render_to_string("status_table_template.html", ctx)

        # Verify HTML structure and dynamic IPO title
        self.assertIn("JIO IPO Ipo Status", html_out)
        self.assertIn("Kostak", html_out)
        self.assertIn("Subject To", html_out)
        self.assertIn("Premium", html_out)
        self.assertIn("Strike Price", html_out)
        self.assertIn("100", html_out)  # Buy count
        self.assertIn("15.00", html_out)  # Buy avg

    def test_cross_group_data_leakage_prevention(self):
        """Verify customer group A never sees orders belonging to customer group B."""
        from whatsapp.services import build_order_summary_context, get_orders_for_groups

        group_b = GroupDetail.objects.create(
            user=self.user,
            GroupName="BETA TRADERS",
            MobileNo="9111222333",
            Active=True,
        )

        # Group A orders: 50 BUY Kostak Retail
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=20.0,
            Quantity=50.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        # Group B orders: 500 BUY Kostak Retail (High volume)
        Order.objects.create(
            user=self.user,
            OrderGroup=group_b,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=25.0,
            Quantity=500.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        # Group A summary context must strictly have only 50 qty, never 500 or 550
        orders_a = get_orders_for_groups(GroupDetail.objects.filter(id=self.group.id), ipo_id=self.ipo_jio.id)
        ctx_a = build_order_summary_context(self.group, orders=orders_a, ipo=self.ipo_jio)

        self.assertEqual(ctx_a["dict_count"]["KostakRETAILBUYCount"], 50)
        self.assertEqual(ctx_a["dict_amount"]["KostakRETAILBUYAmount"], 1000.0)
        self.assertEqual(ctx_a["net_count"]["KostakRETAILNetCount"], 50)

        # Group B summary context must strictly have only 500 qty
        orders_b = get_orders_for_groups(GroupDetail.objects.filter(id=group_b.id), ipo_id=self.ipo_jio.id)
        ctx_b = build_order_summary_context(group_b, orders=orders_b, ipo=self.ipo_jio)

        self.assertEqual(ctx_b["dict_count"]["KostakRETAILBUYCount"], 500)
        self.assertEqual(ctx_b["dict_amount"]["KostakRETAILBUYAmount"], 12500.0)
        self.assertEqual(ctx_b["net_count"]["KostakRETAILNetCount"], 500)

    def test_inactive_and_cancelled_orders_excluded(self):
        """Verify cancelled or inactive orders (Active=False) are never included in image calculation."""
        from whatsapp.services import build_order_summary_context, get_orders_for_groups

        # Active order: 100 BUY @ 10
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=10.0,
            Quantity=100.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        # Inactive / Cancelled order: 900 BUY @ 50
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=50.0,
            Quantity=900.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=False,
        )

        orders = get_orders_for_groups(GroupDetail.objects.filter(id=self.group.id), ipo_id=self.ipo_jio.id)
        ctx = build_order_summary_context(self.group, orders=orders, ipo=self.ipo_jio)

        # Total count must be 100, not 1000
        self.assertEqual(ctx["dict_count"]["KostakRETAILBUYCount"], 100)
        self.assertEqual(ctx["dict_amount"]["KostakRETAILBUYAmount"], 1000.0)
        self.assertEqual(ctx["dict_avg"]["KostakRETAILBUYAvg"], 10.0)

    def test_kostak_weighted_average_calculation(self):
        """Verify weighted average rates for multiple BUY and SELL orders at varying rates."""
        from whatsapp.services import build_order_summary_context

        # BUY 100 @ 50 (= 5000), BUY 200 @ 80 (= 16000) -> Total 300 Qty, Total Amount 21000, Weighted Avg = 70.0
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=50.0,
            Quantity=100.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=80.0,
            Quantity=200.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        # SELL 50 @ 100 (= 5000), SELL 50 @ 120 (= 6000) -> Total 100 Qty, Total Amount 11000, Weighted Avg = 110.0
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="SELL",
            Rate=100.0,
            Quantity=50.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="SELL",
            Rate=120.0,
            Quantity=50.0,
            OrderCategory="Kostak",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        orders = Order.objects.filter(OrderGroup=self.group, OrderIPOName=self.ipo_jio, Active=True)
        ctx = build_order_summary_context(self.group, orders=orders, ipo=self.ipo_jio)

        # BUY checks
        self.assertEqual(ctx["dict_count"]["KostakRETAILBUYCount"], 300)
        self.assertEqual(ctx["dict_amount"]["KostakRETAILBUYAmount"], 21000.0)
        self.assertEqual(ctx["dict_avg"]["KostakRETAILBUYAvg"], 70.0)

        # SELL checks
        self.assertEqual(ctx["dict_count"]["KostakRETAILSELLCount"], 100)
        self.assertEqual(ctx["dict_amount"]["KostakRETAILSELLAmount"], 11000.0)
        self.assertEqual(ctx["dict_avg"]["KostakRETAILSELLAvg"], 110.0)

        # NET checks (Net Qty = 300 - 100 = 200, Net Amount = 21000 - 11000 = 10000, Net Avg = 10000 / 200 = 50.0)
        self.assertEqual(ctx["net_count"]["KostakRETAILNetCount"], 200)
        self.assertEqual(ctx["net_amount"]["KostakRETAILNetAmount"], 10000.0)
        self.assertEqual(ctx["net_avg"]["KostakRETAILNetAvg"], 50.0)

    def test_subject_to_lot_size_multipliers(self):
        """Verify Subject To method='Premium' applies correct LotSizeRetail, LotSizeSHNI, LotSizeBHNI multipliers."""
        from whatsapp.services import build_order_summary_context

        # Lot sizes defined on ipo_jio: Retail=50, SHNI=500, BHNI=1000

        # RETAIL Subject To Premium: 2 applications @ 10 rate -> (2 * 10) * 50 = 1000 amount
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=10.0,
            Quantity=2.0,
            OrderCategory="Subject To",
            InvestorType="RETAIL",
            Method="Premium",
            OrderDate="2026-09-15",
            Active=True,
        )

        # SHNI Subject To Premium: 1 application @ 20 rate -> (1 * 20) * 500 = 10000 amount
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=20.0,
            Quantity=1.0,
            OrderCategory="Subject To",
            InvestorType="SHNI",
            Method="Premium",
            OrderDate="2026-09-15",
            Active=True,
        )

        # BHNI Subject To Premium: 1 application @ 30 rate -> (1 * 30) * 1000 = 30000 amount
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=30.0,
            Quantity=1.0,
            OrderCategory="Subject To",
            InvestorType="BHNI",
            Method="Premium",
            OrderDate="2026-09-15",
            Active=True,
        )

        orders = Order.objects.filter(OrderGroup=self.group, OrderIPOName=self.ipo_jio, Active=True)
        ctx = build_order_summary_context(self.group, orders=orders, ipo=self.ipo_jio)

        # RETAIL
        self.assertEqual(ctx["dict_count"]["SubjectToRETAILBUYCount"], 2)
        self.assertEqual(ctx["dict_amount"]["SubjectToRETAILBUYAmount"], 1000.0)
        self.assertEqual(ctx["dict_avg"]["SubjectToRETAILBUYAvg"], 500.0)  # 1000 / 2

        # SHNI
        self.assertEqual(ctx["dict_count"]["SubjectToSHNIBUYCount"], 1)
        self.assertEqual(ctx["dict_amount"]["SubjectToSHNIBUYAmount"], 10000.0)

        # BHNI
        self.assertEqual(ctx["dict_count"]["SubjectToBHNIBUYCount"], 1)
        self.assertEqual(ctx["dict_amount"]["SubjectToBHNIBUYAmount"], 30000.0)

    def test_premium_instrument_math_and_net_calculations(self):
        """Verify Premium category calculation of Buy/Sell counts, amounts, net averages."""
        from whatsapp.services import build_order_summary_context

        # Premium BUY: 50 @ 12 = 600
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=12.0,
            Quantity=50.0,
            OrderCategory="Premium",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        # Premium SELL: 20 @ 15 = 300
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="SELL",
            Rate=15.0,
            Quantity=20.0,
            OrderCategory="Premium",
            InvestorType="RETAIL",
            OrderDate="2026-09-15",
            Active=True,
        )

        orders = Order.objects.filter(OrderGroup=self.group, OrderIPOName=self.ipo_jio, Active=True)
        ctx = build_order_summary_context(self.group, orders=orders, ipo=self.ipo_jio)

        self.assertEqual(ctx["PremiumBuyCount"], 50.0)
        self.assertEqual(ctx["PremiumBuyAmount"], 600.0)
        self.assertEqual(ctx["PremiumBuyAvg"], "12.00")

        self.assertEqual(ctx["PremiumSellCount"], 20.0)
        self.assertEqual(ctx["PremiumSellAmount"], 300.0)
        self.assertEqual(ctx["PremiumSellAvg"], "15.00")

        # Net = 50 - 20 = 30
        self.assertEqual(ctx["PremiumNetCount"], "30.00")
        self.assertEqual(ctx["PremiumNetAmount"], 300.0)  # 600 - 300
        self.assertEqual(ctx["PremiumNetAvg"], "10.00")  # (600 - 300) / 30 = 10.0

    def test_options_multi_strike_aggregation_and_grand_totals(self):
        """Verify multi-strike options math correctly computes across Strike 100, 150, 200 and grand totals."""
        from whatsapp.services import build_order_summary_context

        # Strike 100: CALL BUY 50 @ 4 (=200), CALL SELL 10 @ 6 (=60)
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=4.0,
            Quantity=50.0,
            OrderCategory="CALL",
            InvestorType="OPTIONS",
            Method="100",
            OrderDate="2026-09-15",
            Active=True,
        )
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="SELL",
            Rate=6.0,
            Quantity=10.0,
            OrderCategory="CALL",
            InvestorType="OPTIONS",
            Method="100",
            OrderDate="2026-09-15",
            Active=True,
        )

        # Strike 200: PUT BUY 30 @ 8 (=240), PUT SELL 30 @ 10 (=300) -> Net count = 0
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="BUY",
            Rate=8.0,
            Quantity=30.0,
            OrderCategory="PUT",
            InvestorType="OPTIONS",
            Method="200",
            OrderDate="2026-09-15",
            Active=True,
        )
        Order.objects.create(
            user=self.user,
            OrderGroup=self.group,
            OrderIPOName=self.ipo_jio,
            OrderType="SELL",
            Rate=10.0,
            Quantity=30.0,
            OrderCategory="PUT",
            InvestorType="OPTIONS",
            Method="200",
            OrderDate="2026-09-15",
            Active=True,
        )

        orders = Order.objects.filter(OrderGroup=self.group, OrderIPOName=self.ipo_jio, Active=True)
        ctx = build_order_summary_context(self.group, orders=orders, ipo=self.ipo_jio)

        strike_100 = next(s for s in ctx["strike_prices"] if s["value"] == "100")
        strike_200 = next(s for s in ctx["strike_prices"] if s["value"] == "200")

        # Strike 100 CALL: Net Qty = 50 - 10 = 40, Net Amount = 200 - 60 = 140, Avg = 140 / 40 = 3.5
        self.assertEqual(strike_100["call_total_count"], 40)
        self.assertEqual(strike_100["call_net_amount"], 140.0)
        self.assertEqual(strike_100["call_avg"], 3.5)

        # Strike 200 PUT: Net Qty = 30 - 30 = 0, Net Amount (Sell - Buy) = 300 - 240 = 60
        self.assertEqual(strike_200["put_total_count"], 0)
        self.assertEqual(strike_200["put_net_amount"], 60.0)
        self.assertEqual(strike_200["put_avg"], 0)

        # Grand Totals
        self.assertEqual(ctx["grand_total"]["call_total_count"], 40)
        self.assertEqual(ctx["grand_total"]["call_net_amount"], 140.0)
        self.assertEqual(ctx["grand_total"]["put_total_count"], 0)
        self.assertEqual(ctx["grand_total"]["put_net_amount"], 60.0)


class FlowEndpointTests(TestCase):
    """Test suite for WhatsApp Flows endpoint encryption, decryption, and health check actions."""
    def setUp(self):
        import os
        from django.conf import settings
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        self.client = Client()
        self.flow_url = reverse("whatsapp:flow_data_endpoint")
        self.pub_key_path = os.path.join(settings.BASE_DIR, "whatsapp", "flow_keys", "public.pem")
        with open(self.pub_key_path, "rb") as f:
            self.public_key = load_pem_public_key(f.read())

    def _encrypt_meta_request(self, payload_dict):
        import os
        from base64 import b64encode
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        # 1. Generate 16-byte AES key and 12-byte IV
        aes_key = os.urandom(16)
        iv = os.urandom(12)

        # 2. Encrypt AES key using RSA public key with OAEP SHA-256
        encrypted_aes_key = self.public_key.encrypt(
            aes_key,
            OAEP(
                mgf=MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # 3. Encrypt payload with AES-GCM
        encryptor = Cipher(algorithms.AES(aes_key), modes.GCM(iv)).encryptor()
        json_bytes = json.dumps(payload_dict).encode("utf-8")
        ciphertext = encryptor.update(json_bytes) + encryptor.finalize()
        flow_data = ciphertext + encryptor.tag

        return {
            "encrypted_flow_data": b64encode(flow_data).decode("utf-8"),
            "encrypted_aes_key": b64encode(encrypted_aes_key).decode("utf-8"),
            "initial_vector": b64encode(iv).decode("utf-8"),
        }, aes_key, iv

    def test_flow_health_check_ping_returns_200(self):
        """Verify Meta Flow health check 'ping' request returns 200 with status: active."""
        from whatsapp.flow_crypto import decrypt_request

        ping_payload = {
            "version": "3.0",
            "action": "ping",
        }
        enc_payload, aes_key, iv = self._encrypt_meta_request(ping_payload)

        response = self.client.post(
            self.flow_url,
            data=json.dumps(enc_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Decrypt response
        resp_b64 = response.content.decode("utf-8")
        from base64 import b64decode
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        resp_bytes = b64decode(resp_b64)
        tag = resp_bytes[-16:]
        body = resp_bytes[:-16]
        flipped_iv = bytearray(b ^ 0xFF for b in iv)
        decryptor = Cipher(algorithms.AES(aes_key), modes.GCM(flipped_iv, tag)).decryptor()
        plain_bytes = decryptor.update(body) + decryptor.finalize()
        result = json.loads(plain_bytes.decode("utf-8"))

        self.assertEqual(result.get("data", {}).get("status"), "active")

    def test_flow_init_returns_start_screen(self):
        """Verify Meta Flow launch 'INIT' action returns START screen with active ipo_list."""
        init_payload = {
            "version": "3.0",
            "action": "INIT",
        }
        enc_payload, aes_key, iv = self._encrypt_meta_request(init_payload)

        response = self.client.post(
            self.flow_url,
            data=json.dumps(enc_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Decrypt response
        resp_b64 = response.content.decode("utf-8")
        from base64 import b64decode
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        resp_bytes = b64decode(resp_b64)
        tag = resp_bytes[-16:]
        body = resp_bytes[:-16]
        flipped_iv = bytearray(b ^ 0xFF for b in iv)
        decryptor = Cipher(algorithms.AES(aes_key), modes.GCM(flipped_iv, tag)).decryptor()
        plain_bytes = decryptor.update(body) + decryptor.finalize()
        result = json.loads(plain_bytes.decode("utf-8"))

        self.assertEqual(result.get("screen"), "START")
        self.assertIn("ipo_list", result.get("data", {}))




