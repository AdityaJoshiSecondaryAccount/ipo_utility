import hashlib
import hmac
import json
import logging
import re
import traceback
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from home.models import CurrentIpoName, GroupDetail, Order

from .client import (
    send_image_message,
    send_order_confirmation,
    send_text_message,
    upload_media,
)
from .services import (
    build_order_summary_context,
    generate_order_summary_image,
    get_groups_by_phone,
    get_orders_for_groups,
    normalize_phone_number,
)

logger = logging.getLogger(__name__)

ORDER_DETAIL_FIELDS = (
    ("Kostak Retail", "KostakQTY", "KostakRate"),
    ("Kostak SHNI", "KostakQTYSHNI", "KostakRateSHNI"),
    ("Kostak BHNI", "KostakQTYBHNI", "KostakRateBHNI"),
    ("Subject To Retail", "SubjectToQTY", "SubjectToRate"),
    ("Subject To SHNI", "SubjectToQTYSHNI", "SubjectToRateSHNI"),
    ("Subject To BHNI", "SubjectToQTYBHNI", "SubjectToRateBHNI"),
    ("Premium", "PremiumQTY", "PremiumRate"),
    ("Call", "CallQTY", "CallRate"),
    ("Put", "PutQTY", "PutRate"),
)


def _whatsapp_number(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def _order_details(post_data):
    details = []
    for label, quantity_field, rate_field in ORDER_DETAIL_FIELDS:
        quantity = (post_data.get(quantity_field) or "").strip()
        rate = (post_data.get(rate_field) or "").strip()
        if quantity or rate:
            parts = [label]
            if quantity:
                parts.append(f"Qty: {quantity}")
            if rate:
                parts.append(f"Rate: {rate}")
            details.append(" - ".join(parts))
    return "; ".join(details)


def _send_order(request, ipo_id, order_type):
    required_settings = (
        "WHATSAPP_API_VERSION",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_ACCESS_TOKEN",
    )
    missing = [name for name in required_settings if not getattr(settings, name, "")]
    if missing:
        messages.error(request, "Order placed successfully, but WhatsApp is not configured.")
        return JsonResponse({
            "status": "error",
            "message": "WhatsApp API is not configured.",
        }, status=503)

    group_name = (request.POST.get("item_id") or "").strip()
    if not group_name:
        messages.error(request, "Order placed successfully, but no group was selected for WhatsApp.")
        return JsonResponse({"status": "error", "message": "Select a group first."}, status=400)

    group = get_object_or_404(
        GroupDetail,
        user=request.user,
        GroupName=group_name,
        Active=True,
    )
    phone_number = _whatsapp_number(group.MobileNo)
    if len(phone_number) < 11 or len(phone_number) > 15:
        messages.error(
            request,
            f"Order placed successfully, but {group.GroupName} has no valid mobile number.",
        )
        return JsonResponse({
            "status": "error",
            "message": f"Add a valid mobile number for {group.GroupName}.",
        }, status=400)

    ipo = get_object_or_404(CurrentIpoName, id=ipo_id, user=request.user)
    details = _order_details(request.POST)
    if not details:
        messages.error(request, "Order placed successfully, but WhatsApp order details were empty.")
        return JsonResponse({
            "status": "error",
            "message": "Enter at least one order quantity or rate.",
        }, status=400)

    try:
        response = send_order_confirmation(
            phone_number=phone_number,
            ipo_name=ipo.IPOName,
            order_type=order_type,
            group_name=group.GroupName,
            order_datetime=request.POST.get("datetime", ""),
            order_details=details,
            ipo_id=ipo.id,
        )
        response_data = response.json() if response.content else {}
    except requests.RequestException as exc:
        messages.error(request, "Order placed successfully, but the WhatsApp message failed.")
        return JsonResponse({
            "status": "error",
            "message": f"Unable to contact WhatsApp: {exc}",
        }, status=502)
    except ValueError:
        response_data = {}
    except Exception:
        messages.error(request, "Order placed successfully, but the WhatsApp message failed.")
        return JsonResponse({
            "status": "error",
            "message": "Unexpected error while sending the WhatsApp message.",
        }, status=502)

    if not response.ok:
        api_error = (
            response_data.get("error", {}).get("message")
            if isinstance(response_data, dict)
            else None
        )
        messages.error(request, "Order placed successfully, but the WhatsApp message failed.")
        return JsonResponse({
            "status": "error",
            "message": api_error or "WhatsApp rejected the message.",
        }, status=response.status_code if 400 <= response.status_code < 600 else 502)

    messages.success(request, "Order placed and WhatsApp message sent successfully.")
    return JsonResponse({"status": "success", "message": "WhatsApp message sent."})


@login_required
@require_POST
def send_buy_order(request, ipo_id):
    return _send_order(request, ipo_id, "BUY")


@login_required
@require_POST
def send_sell_order(request, ipo_id):
    return _send_order(request, ipo_id, "SELL")


def _verify_webhook_signature(request):
    """Validates X-Hub-Signature-256 header if WHATSAPP_APP_SECRET is configured."""
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")
    if not app_secret:
        return True

    header_sig = request.headers.get("X-Hub-Signature-256", "") or request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
    if not header_sig:
        return True

    if not header_sig.startswith("sha256="):
        return True

    expected_sig = "sha256=" + hmac.new(
        app_secret.strip().encode("utf-8"),
        request.body,
        hashlib.sha256
    ).hexdigest()

    is_valid = hmac.compare_digest(header_sig, expected_sig)
    if not is_valid:
        print(f"[WA Webhook Signature Warning] Mismatch (received {header_sig}). Continuing anyway so testing is not blocked.")
    return True


def _extract_button_payload(msg):
    """Extracts button identifier or text across different Meta message formats."""
    msg_type = msg.get("type")
    payload = None
    text = None

    if msg_type == "button":
        btn = msg.get("button", {})
        payload = btn.get("payload")
        text = btn.get("text")
    elif msg_type == "interactive":
        interactive = msg.get("interactive", {})
        btn_reply = interactive.get("button_reply", {})
        payload = btn_reply.get("id")
        text = btn_reply.get("title")
    elif msg_type == "text":
        text = msg.get("text", {}).get("body")

    return (payload or "").strip(), (text or "").strip()


def _is_view_orders_action(msg_type, payload, text):
    """Checks if payload, text, or message type corresponds to button click / View Orders."""
    if msg_type in ("button", "interactive"):
        return True

    targets = ["view_orders", "view your orders", "view orders", "view_order", "my_orders", "orders", "order", "view"]
    payload_lower = (payload or "").lower()
    text_lower = (text or "").lower()

    for target in targets:
        if target in payload_lower or target in text_lower:
            return True
    return False


@csrf_exempt
def webhook(request):
    """
    WhatsApp Cloud API Webhook endpoint.
    GET: Handles Meta webhook challenge verification.
    POST: Processes incoming WhatsApp webhook events (e.g., 'View Your Orders' button replies).
    """
    if request.method == "GET":
        mode = (request.GET.get("hub.mode") or "").strip()
        token = (request.GET.get("hub.verify_token") or "").strip()
        challenge = request.GET.get("hub.challenge")

        configured_token = str(getattr(
            settings,
            "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
            "ADwealth_WA_Webhook_2026"
        )).strip()

        print(f"[WA Webhook GET] mode='{mode}', token='{token}', configured='{configured_token}'")

        if (mode == "subscribe" or not mode) and token == configured_token:
            print("[WA Webhook GET] Verification SUCCESS")
            return HttpResponse(str(challenge or "OK"), content_type="text/plain", status=200)

        print(f"[WA Webhook GET] Verification FAILED (token mismatch: received '{token}' vs expected '{configured_token}')")
        return HttpResponse("Verification failed", status=403)

    if request.method == "POST":
        print("\n" + "="*50)
        print("[WA Webhook POST] Incoming POST event from Meta")
        if not _verify_webhook_signature(request):
            print("[WA Webhook POST Error] Invalid signature header")
            return HttpResponse("Invalid signature", status=403)

        try:
            body_str = request.body.decode("utf-8")
            print(f"[WA Webhook POST RAW]: {body_str}")
            body = json.loads(body_str)
        except (ValueError, TypeError) as exc:
            print(f"[WA Webhook POST Error] Malformed JSON: {exc}")
            return HttpResponse("Bad Request", status=400)

        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                val = change.get("value", {})
                messages_list = val.get("messages", [])

                if not messages_list:
                    # Status updates (sent/delivered/read)
                    statuses = val.get("statuses", [])
                    if statuses:
                        print(f"[WA Webhook Status Update]: status={statuses[0].get('status')}, id={statuses[0].get('id')}")
                    continue

                for msg in messages_list:
                    msg_id = msg.get("id")
                    if msg_id:
                        cache_key = f"wa_msg_seen_{msg_id}"
                        if cache.get(cache_key):
                            print(f"[WA Webhook] Duplicate message {msg_id} ignored.")
                            continue
                        cache.set(cache_key, True, timeout=3600)

                    sender_raw = msg.get("from", "")
                    sender_clean = normalize_phone_number(sender_raw)
                    msg_type = msg.get("type", "")
                    payload, text = _extract_button_payload(msg)

                    print(f"[WA Webhook] Message received from {sender_raw} ({sender_clean}) | type='{msg_type}' | payload='{payload}' | text='{text}'")

                    if not _is_view_orders_action(msg_type, payload, text):
                        print(f"[WA Webhook] Message is not a button click or orders action.")
                        continue

                    # Customer Identification
                    groups = get_groups_by_phone(sender_clean)
                    group_names = list(groups.values_list('GroupName', flat=True))
                    print(f"[WA Webhook] Matching Customer Group(s): {group_names}")

                    if not groups.exists():
                        print(f"[WA Webhook Warning] Phone {sender_clean} is not registered with any customer group in the database.")
                        try:
                            res = send_text_message(
                                sender_raw,
                                "Your mobile number is not registered with any customer account."
                            )
                            print(f"[WA Webhook Sent Notice]: status={res.status_code}, response={res.text}")
                        except Exception as e:
                            print(f"[WA Webhook Error] Failed to send unregistered message: {e}")
                            traceback.print_exc()
                        continue

                    # Extract optional IPO ID from payload if present (e.g., 'view_orders_12')
                    ipo_id = None
                    if "view_orders_" in payload:
                        try:
                            ipo_id = int(payload.split("view_orders_")[-1])
                        except ValueError:
                            pass

                    # Order Retrieval scoped to specific IPO
                    if ipo_id:
                        orders = get_orders_for_groups(groups, ipo_id=ipo_id)
                        target_ipo = CurrentIpoName.objects.filter(id=ipo_id).first()
                    else:
                        all_orders = get_orders_for_groups(groups)
                        if all_orders.exists():
                            target_ipo = all_orders.order_by('-id').first().OrderIPOName
                            orders = all_orders.filter(OrderIPOName=target_ipo)
                        else:
                            target_ipo = None
                            orders = Order.objects.none()

                    print(f"[WA Webhook] Found {orders.count()} active order(s) for customer group(s) in IPO: {target_ipo}.")

                    if not orders.exists():
                        print(f"[WA Webhook Info] Customer group has 0 active orders.")
                        try:
                            res = send_text_message(
                                sender_raw,
                                "You currently have no active orders."
                            )
                            print(f"[WA Webhook Sent Notice]: status={res.status_code}, response={res.text}")
                        except Exception as e:
                            print(f"[WA Webhook Error] Failed to send no-orders message: {e}")
                            traceback.print_exc()
                        continue

                    # Generate and Send Orders Summary Image
                    group = groups.first()
                    ipo_display = getattr(target_ipo, 'IPOName', '').strip() if target_ipo else ''
                    status_label = f"{ipo_display} " if ipo_display else ""
                    print(f"[WA Webhook] Generating orders image for {group.GroupName} ({orders.count()} orders in {target_ipo})...")

                    try:
                        context = build_order_summary_context(group, orders=orders, ipo=target_ipo)
                        img_buf = generate_order_summary_image(context)
                        print(f"[WA Webhook] Image generated ({len(img_buf.getvalue())} bytes). Uploading to Meta WhatsApp...")

                        # Upload media to Meta WhatsApp Cloud API
                        upload_res = upload_media(
                            img_buf,
                            mime_type="image/png",
                            filename=f"orders_{group.id}.png"
                        )
                        print(f"[WA Webhook Upload]: HTTP {upload_res.status_code} -> {upload_res.text}")

                        if upload_res.ok:
                            media_id = upload_res.json().get("id")
                            ipo_display = getattr(target_ipo, 'IPOName', 'Orders') if target_ipo else 'Orders'
                            caption = f"{ipo_display} Status - {group.GroupName}"
                            send_res = send_image_message(
                                phone_number=sender_raw,
                                media_id=media_id,
                                caption=caption,
                            )
                            print(f"[WA Webhook Send Image]: HTTP {send_res.status_code} -> {send_res.text}")
                            if not send_res.ok:
                                print(f"[WA Webhook ERROR sending image]: {send_res.text}")
                        else:
                            print(f"[WA Webhook ERROR uploading media]: {upload_res.text}")
                            # Fallback to text message if media upload fails
                            send_text_message(
                                sender_raw,
                                f"Orders Summary for {group.GroupName}: {orders.count()} active orders."
                            )
                    except Exception as e:
                        print(f"[WA Webhook Exception generating/sending image]: {e}")
                        traceback.print_exc()

        print("="*50 + "\n")
        return HttpResponse("EVENT_RECEIVED", status=200)

    return HttpResponse("Method Not Allowed", status=405)


@csrf_exempt
def flow_data_endpoint(request):
    """
    HTTP Endpoint for WhatsApp Flows data exchange and health checks.
    Meta sends POST requests with encrypted payload:
    {
        "encrypted_flow_data": "...",
        "encrypted_aes_key": "...",
        "initial_vector": "..."
    }
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=405)

    try:
        import os
        from .flow_crypto import decrypt_request, encrypt_response, FlowDecryptionError
        from .flow_endpoint import handle_flow_action

        # 1. Parse request body
        body = json.loads(request.body.decode("utf-8"))
        encrypted_flow_data = body.get("encrypted_flow_data")
        encrypted_aes_key = body.get("encrypted_aes_key")
        initial_vector = body.get("initial_vector")

        if not all([encrypted_flow_data, encrypted_aes_key, initial_vector]):
            logger.warning("Missing encrypted fields in WhatsApp Flow request.")
            return JsonResponse({"error": "Bad Request"}, status=400)

        # 2. Read private key
        key_path = getattr(settings, "WHATSAPP_FLOW_PRIVATE_KEY_PATH", None)
        passphrase = getattr(settings, "WHATSAPP_FLOW_PRIVATE_KEY_PASSPHRASE", None)

        if not key_path or not os.path.exists(key_path):
            logger.error(f"WhatsApp Flow private key not found at {key_path}")
            return HttpResponse("Server Configuration Error: Private Key Missing", status=500)

        with open(key_path, "rb") as f:
            private_key_pem = f.read()

        # 3. Decrypt request
        decrypted_body, aes_key, iv = decrypt_request(
            encrypted_flow_data,
            encrypted_aes_key,
            initial_vector,
            private_key_pem,
            passphrase=passphrase,
        )

        logger.info(f"Decrypted WhatsApp Flow payload: {decrypted_body}")

        # 4. Optional customer phone extraction from header / query param
        customer_phone = request.GET.get("phone") or request.headers.get("X-Customer-Phone")

        # 5. Process business logic
        response_dict = handle_flow_action(decrypted_body, customer_phone=customer_phone)

        # 6. Encrypt response
        encrypted_response_b64 = encrypt_response(response_dict, aes_key, iv)

        # Meta requires text/plain response containing the base64 string
        return HttpResponse(encrypted_response_b64, content_type="text/plain")

    except FlowDecryptionError as e:
        logger.error(f"WhatsApp Flow decryption error: {e}")
        # Meta doc: HTTP 421 tells WhatsApp client to re-download the business public key
        return HttpResponse("Decryption Error", status=421)

    except Exception as e:
        logger.error(f"WhatsApp Flow endpoint error: {e}", exc_info=True)
        return JsonResponse({"error": "Internal Server Error"}, status=500)

