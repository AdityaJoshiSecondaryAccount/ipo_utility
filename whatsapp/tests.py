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

