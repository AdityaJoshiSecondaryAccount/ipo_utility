import io
import requests
import threading
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def _log_outbound_to_fastapi(phone_number, text, msg_type="text", media_url=None, media_filename=None, wamid=None):
    def run():
        fastapi_url = getattr(settings, "FASTAPI_INTERNAL_URL", "http://127.0.0.1:8005/chat-api")
        url = f"{fastapi_url}/log-outbound"
        payload = {
            "phone_number": phone_number,
            "text": str(text) if text else None,
            "message_type": msg_type,
            "media_url": str(media_url) if media_url else None,
            "media_filename": str(media_filename) if media_filename else None,
            "wamid": wamid,
            "status": "sent"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.warning(f"Failed to sync outbound message to FastAPI: {e}")

    threading.Thread(target=run, daemon=True).start()



def _get_api_headers(content_type="application/json"):
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def send_order_confirmation(phone_number, ipo_name, order_type, group_name,
                            order_datetime, order_details, remark_text, ipo_id=None, broker_id=None):
    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = _get_api_headers("application/json")
    components = [{
        "type": "body",
        "parameters": [
            {"type": "text", "parameter_name": "ipo_name", "text": str(ipo_name)},
            {"type": "text", "parameter_name": "order_type", "text": str(order_type)},
            {"type": "text", "parameter_name": "group_name", "text": str(group_name)},
            {"type": "text", "parameter_name": "order_datetime", "text": str(order_datetime)},
            {"type": "text", "parameter_name": "item_1", "text": str(order_details[0]) if order_details[0] else "\u200B"},
            {"type": "text", "parameter_name": "item_2", "text": str(order_details[1]) if order_details[1] else "\u200B"},
            {"type": "text", "parameter_name": "item_3", "text": str(order_details[2]) if order_details[2] else "\u200B"},
            {"type": "text", "parameter_name": "item_4", "text": str(order_details[3]) if order_details[3] else "\u200B"},
            {"type": "text", "parameter_name": "item_5", "text": str(order_details[4]) if order_details[4] else "\u200B"},
            {"type": "text", "parameter_name": "item_6", "text": str(order_details[5]) if order_details[5] else "\u200B"},
            {"type": "text", "parameter_name": "item_7", "text": str(order_details[6]) if order_details[6] else "\u200B"},
            {"type": "text", "parameter_name": "item_8", "text": str(order_details[7]) if order_details[7] else "\u200B"},
            {"type": "text", "parameter_name": "item_9", "text": str(order_details[8]) if order_details[8] else "\u200B"},
            {"type": "text", "parameter_name": "remark_text", "text": str(remark_text) if remark_text else "\u200B"},
        ],
    }]

    if ipo_id:
        payload_str = f"view_orders_{ipo_id}_{broker_id}" if broker_id else f"view_orders_{ipo_id}"
        components.append({
            "type": "button",
            "sub_type": "quick_reply",
            "index": "0",
            "parameters": [
                {
                    "type": "payload",
                    "payload": payload_str
                }
            ]
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            # "name": "ipo_order_confirmation",
            "name": "ipo_order_formatted",
            # "name": "three_var_second ",
            # "name": "ipo_order_lines",
            "language": {"code": "en"},
            "components": components,
        },
    }
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    # If Meta template does not accept dynamic button parameter, fallback to body-only
    if not res.ok and ipo_id:
        try:
            res_json = res.json()
            error_code = res_json.get("error", {}).get("code")
            if error_code in (100, 132000, 132001, 132005, 132007):
                payload["template"]["components"] = [components[0]]
                res = requests.post(url, headers=headers, json=payload, timeout=15)
        except Exception:
            pass
    if res.ok:
        try:
            wamid = res.json().get("messages", [{}])[0].get("id")
        except Exception:
            wamid = None
        exact_text = (
            "Order Confirmation\n"
            f"📢 IPO Name: {ipo_name}\n\n"
            f"📦 Order: {order_type}\n"
            f"👥 Group: {group_name}\n\n"
            f"🕒 Date & Time: {order_datetime}\n\n"
            "Order Details:\n"
            f"{order_details}\n\n"
            "Order has been placed successfully. Revert if there is any discrepancy."
        )
        _log_outbound_to_fastapi(
            phone_number=phone_number,
            text=exact_text,
            msg_type="template",
            wamid=wamid
        )
    return res


def upload_media(file_bytes_or_buffer, mime_type="image/png", filename="orders.png"):
    """Uploads media to Meta WhatsApp Cloud API and returns the response."""
    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
    )
    headers = _get_api_headers(content_type=None)
    
    if isinstance(file_bytes_or_buffer, io.BytesIO):
        data_bytes = file_bytes_or_buffer.getvalue()
    elif hasattr(file_bytes_or_buffer, "read"):
        data_bytes = file_bytes_or_buffer.read()
    else:
        data_bytes = file_bytes_or_buffer

    files = {
        "file": (filename, data_bytes, mime_type),
    }
    data = {
        "messaging_product": "whatsapp",
        "type": mime_type,
    }
    return requests.post(url, headers=headers, data=data, files=files, timeout=30)


def send_image_message(phone_number, media_id=None, image_url=None, caption=None, log_to_fastapi=True):
    """Sends an image message via WhatsApp Cloud API using either media_id or image_url."""
    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = _get_api_headers("application/json")
    image_obj = {}
    if media_id:
        image_obj["id"] = str(media_id)
    elif image_url:
        image_obj["link"] = str(image_url)
    
    if caption:
        image_obj["caption"] = str(caption)

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "image",
        "image": image_obj,
    }
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    if res.ok and log_to_fastapi:
        try:
            wamid = res.json().get("messages", [{}])[0].get("id")
        except Exception:
            wamid = None
        _log_outbound_to_fastapi(
            phone_number=phone_number,
            text=caption or "",
            msg_type="image",
            media_url=image_url or str(media_id) if media_id else None,
            wamid=wamid
        )
    return res


def send_text_message(phone_number, text):
    """Sends a plain text message via WhatsApp Cloud API."""
    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = _get_api_headers("application/json")
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": str(text),
        },
    }
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    if res.ok:
        try:
            wamid = res.json().get("messages", [{}])[0].get("id")
        except Exception:
            wamid = None
        _log_outbound_to_fastapi(
            phone_number=phone_number,
            text=str(text),
            msg_type="text",
            wamid=wamid
        )
    return res


def send_document_message(phone_number, media_id=None, image_url=None, caption=None, log_to_fastapi=True):
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = _get_api_headers("application/json")
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "document",
        "document": {
            "id": str(media_id),
            "caption": str(caption) if caption else "",
            "filename": "Orders_Summary.pdf"
        },
    }
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    
    if res.ok and log_to_fastapi:
        try:
            wamid = res.json().get("messages", [{}])[0].get("id")
        except Exception:
            wamid = None
        _log_outbound_to_fastapi(
            phone_number=phone_number,
            text=caption or "",
            msg_type="document",
            media_url=image_url or str(media_id) if media_id else None,
            wamid=wamid
        )
    return res

def send_ipo_flow_to_user(phone_number, log_to_fastapi=True):
    """
    Sends the WhatsApp Flow template to the user.
    Critically, it injects the phone_number into the flow_token so that
    when the user opens the flow, we know exactly who they are!
    """
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = _get_api_headers("application/json")
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": "place_ipo_order",  # <--- Make sure this matches your Meta Template Name!
            "language": {"code": "en"},
            "components": [
                {
                    "type": "button",
                    "sub_type": "flow",
                    "index": "0",
                    "parameters": [
                        {
                            "type": "action",
                            "action": {
                                "flow_token": str(phone_number)  # <--- THE MAGIC STICKY NOTE!
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    
    if res.ok and log_to_fastapi:
        try:
            wamid = res.json().get("messages", [{}])[0].get("id")
        except Exception:
            wamid = None
        _log_outbound_to_fastapi(
            phone_number=phone_number,
            text="IPO Order Form (Flow)",
            msg_type="template",
            wamid=wamid
        )
    return res

def send_grouped_order_confirmation(
    phone_number, ipo_name, order_type, group_name, order_datetime,
    kostak_str, subject_str, premium_str, options_str, remark_text,
    template_name="ipo_order"
):
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = _get_api_headers("application/json")
    
    # Meta WhatsApp Cloud API forbids newlines (\n), tabs (\t), or >4 consecutive spaces inside parameter values!
    def clean_param(val):
        if not val:
            return "\u200B"
        cleaned = str(val).replace("\r\n", "\n").replace("\r", "\n").replace("\n", ", ").replace("\t", " ")
        import re
        cleaned = re.sub(r" {5,}", "    ", cleaned).strip()
        return cleaned if cleaned else "\u200B"

    clean_ipo = clean_param(ipo_name)
    clean_order_type = clean_param(order_type)
    clean_group = clean_param(group_name)
    clean_datetime = clean_param(order_datetime)
    clean_kostak = clean_param(kostak_str)
    clean_subject = clean_param(subject_str)
    clean_premium = clean_param(premium_str)
    clean_options = clean_param(options_str)
    clean_remarks = clean_param(remark_text)

    # Candidate 1: 9 Named parameters (matches user's approved 'ipo_order' template: remarks)
    params_9_named_remarks = [
        {"type": "text", "parameter_name": "ipo_name", "text": clean_ipo},
        {"type": "text", "parameter_name": "order_type", "text": clean_order_type},
        {"type": "text", "parameter_name": "group_name", "text": clean_group},
        {"type": "text", "parameter_name": "order_datetime", "text": clean_datetime},
        {"type": "text", "parameter_name": "kostak", "text": clean_kostak},
        {"type": "text", "parameter_name": "subject", "text": clean_subject},
        {"type": "text", "parameter_name": "premium", "text": clean_premium},
        {"type": "text", "parameter_name": "options", "text": clean_options},
        {"type": "text", "parameter_name": "remarks", "text": clean_remarks},
    ]

    # Candidate 2: 9 Named parameters with 'remark_text'
    params_9_named_remark_text = [
        {"type": "text", "parameter_name": "ipo_name", "text": clean_ipo},
        {"type": "text", "parameter_name": "order_type", "text": clean_order_type},
        {"type": "text", "parameter_name": "group_name", "text": clean_group},
        {"type": "text", "parameter_name": "order_datetime", "text": clean_datetime},
        {"type": "text", "parameter_name": "kostak", "text": clean_kostak},
        {"type": "text", "parameter_name": "subject", "text": clean_subject},
        {"type": "text", "parameter_name": "premium", "text": clean_premium},
        {"type": "text", "parameter_name": "options", "text": clean_options},
        {"type": "text", "parameter_name": "remark_text", "text": clean_remarks},
    ]

    # Candidate 3: 9 Named parameters with 'order_date' instead of 'order_datetime'
    params_9_named_order_date = [
        {"type": "text", "parameter_name": "ipo_name", "text": clean_ipo},
        {"type": "text", "parameter_name": "order_type", "text": clean_order_type},
        {"type": "text", "parameter_name": "group_name", "text": clean_group},
        {"type": "text", "parameter_name": "order_date", "text": clean_datetime},
        {"type": "text", "parameter_name": "kostak", "text": clean_kostak},
        {"type": "text", "parameter_name": "subject", "text": clean_subject},
        {"type": "text", "parameter_name": "premium", "text": clean_premium},
        {"type": "text", "parameter_name": "options", "text": clean_options},
        {"type": "text", "parameter_name": "remarks", "text": clean_remarks},
    ]

    # Candidate 4: 9 Positional parameters (for templates with positional variables {{1}}..{{9}})
    params_9_positional = [
        {"type": "text", "text": clean_ipo},
        {"type": "text", "text": clean_order_type},
        {"type": "text", "text": clean_group},
        {"type": "text", "text": clean_datetime},
        {"type": "text", "text": clean_kostak},
        {"type": "text", "text": clean_subject},
        {"type": "text", "text": clean_premium},
        {"type": "text", "text": clean_options},
        {"type": "text", "text": clean_remarks},
    ]

    # Candidate 5: 14 Named parameters ('ipo_order_formatted')
    params_14_named = [
        {"type": "text", "parameter_name": "ipo_name", "text": clean_ipo},
        {"type": "text", "parameter_name": "order_type", "text": clean_order_type},
        {"type": "text", "parameter_name": "group_name", "text": clean_group},
        {"type": "text", "parameter_name": "order_datetime", "text": clean_datetime},
        {"type": "text", "parameter_name": "item_1", "text": clean_kostak},
        {"type": "text", "parameter_name": "item_2", "text": clean_subject},
        {"type": "text", "parameter_name": "item_3", "text": clean_premium},
        {"type": "text", "parameter_name": "item_4", "text": clean_options},
        {"type": "text", "parameter_name": "item_5", "text": "\u200B"},
        {"type": "text", "parameter_name": "item_6", "text": "\u200B"},
        {"type": "text", "parameter_name": "item_7", "text": "\u200B"},
        {"type": "text", "parameter_name": "item_8", "text": "\u200B"},
        {"type": "text", "parameter_name": "item_9", "text": "\u200B"},
        {"type": "text", "parameter_name": "remark_text", "text": clean_remarks},
    ]

    # Order candidates depending on requested template
    if template_name == "ipo_order_formatted":
        candidates = [params_14_named, params_9_named_remarks, params_9_named_remark_text, params_9_positional]
    else:
        candidates = [params_9_named_remarks, params_9_named_remark_text, params_9_named_order_date, params_9_positional, params_14_named]

    res = None
    for idx, params in enumerate(candidates, 1):
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [{"type": "body", "parameters": params}],
            },
        }
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"[WHATSAPP_DEBUG] Candidate #{idx} for '{template_name}': status={res.status_code}, response={res.text}", flush=True)
        if res.ok:
            break
        try:
            err_code = res.json().get("error", {}).get("code")
            if err_code not in (100, 132000, 132001, 132005, 132007, 132018):
                break
        except Exception:
            pass

    # Log to FastAPI
    if res and res.ok:
        try:
            wamid = res.json().get("messages", [{}])[0].get("id")
        except Exception:
            wamid = None
        sections = [s for s in [kostak_str, subject_str, premium_str, options_str, remark_text] if s and s.strip()]
        details_block = "\n".join(sections)
        exact_text = (
            "Order Confirmation\n"
            f"📢 IPO Name: *{ipo_name}*\n"
            f"📦 Order: *{order_type}*\n"
            f"👥 Group: *{group_name}*\n"
            f"🕒 Date & Time: {order_datetime}\n\n"
            f"{details_block}\n\n"
            "> Disclaimer: This is an automated order confirmation message. Please verify your order carefully. For any discrepancy, please contact us."
        )
        _log_outbound_to_fastapi(
            phone_number=phone_number,
            text=exact_text,
            msg_type="template",
            wamid=wamid
        )
    return res


# ==============================================================================
# 24-HOUR FREE WINDOW & CUSTOM FREE-TEXT FORMATTING HELPERS
# ==============================================================================

from datetime import timedelta
from django.utils import timezone


def is_within_24hr_window(phone_number: str) -> bool:
    """
    Checks if a contact sent an inbound WhatsApp message within the last 24 hours (86,400 seconds).
    If True, free-form custom text messages can be sent without Meta template restrictions.
    """
    try:
        from .models import Conversation, Message
        clean_number = "".join(filter(str.isdigit, str(phone_number)))
        last10 = clean_number[-10:] if len(clean_number) >= 10 else clean_number

        if not last10:
            return False

        # 1. Check Conversation.last_inbound_time
        conv = Conversation.objects.filter(contact__phone_number__endswith=last10).first()
        if conv and conv.last_inbound_time:
            if timezone.now() - conv.last_inbound_time < timedelta(hours=24):
                return True

        # 2. Fallback check directly on Message direction='inbound'
        last_inbound_msg = Message.objects.filter(
            conversation__contact__phone_number__endswith=last10,
            direction="inbound"
        ).order_by("-timestamp").first()

        if last_inbound_msg and last_inbound_msg.timestamp:
            return timezone.now() - last_inbound_msg.timestamp < timedelta(hours=24)

    except Exception as e:
        logger.warning(f"Error checking 24hr window for {phone_number}: {e}")

    return False


def format_24hr_order_message(
    ipo_name: str,
    order_type: str,
    group_name: str,
    order_datetime: str,
    kostak_str: str = "",
    subject_str: str = "",
    premium_str: str = "",
    options_str: str = "",
    remark_text: str = ""
) -> str:
    """
    Formats a clean, rich-markdown WhatsApp message matching exact design specifications.
    Uses bold labels, emojis, line breaks between item headers & values, and disclaimer footer.
    """
    def clean_val(val: str, prefix: str):
        if not val or not val.strip() or val.strip() == "None":
            return ""
        s = val.strip()
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
        # Add clean space around @ if needed (e.g., 1@₹100 -> 1 @ ₹100)
        s = s.replace("@₹", " @ ₹")
        return s

    k = clean_val(kostak_str, "*Kostak*- ")
    sub = clean_val(subject_str, "*Subject To*- ")
    prem = clean_val(premium_str, "*Premium*- ")
    opt = clean_val(options_str, "*Options*- ")

    breakdown_parts = []
    if k:
        breakdown_parts.append(f"📌 *Kostak*\n{k}")
    if sub:
        breakdown_parts.append(f"📌 *Subject To*\n{sub}")
    if prem:
        breakdown_parts.append(f"📌 *Premium:* {prem}")
    if opt:
        breakdown_parts.append(f"📌 *Options*\n{opt}")

    breakdown_block = "\n\n".join(breakdown_parts) if breakdown_parts else "📌 Standard Order"

    rem = remark_text.strip() if remark_text and remark_text.strip() and remark_text != "None" else ""
    remark_line = f"\n\n📝 *Remarks:* {rem}" if rem else ""

    message = (
        "*✅ ORDER CONFIRMATION*\n\n"
        f"📢 *IPO:* {ipo_name}\n"
        f"🛒 *Order:* {order_type}\n"
        f"👥 *Group:* {group_name}\n"
        f"🕐 *Date & Time:* {order_datetime}\n\n"
        "*📋 ORDER BREAKDOWN*\n\n"
        f"{breakdown_block}"
        f"{remark_line}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ *Please verify your order carefully.*\n"
        "For any discrepancy, please contact us immediately."
    )
    return message


def send_free_text_message(phone_number: str, text: str, button_title: str = None, button_payload: str = None):
    """
    Sends a custom free-form text message to a contact via Meta API (usable inside 24-hour window).
    If button_title and button_payload are provided, sends as an Interactive Quick Reply Button message!
    """
    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = _get_api_headers("application/json")

    if button_title and button_payload:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": text
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": str(button_payload),
                                "title": str(button_title)[:20]  # Meta button title limit: 20 chars
                            }
                        }
                    ]
                }
            }
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text
            }
        }

    res = requests.post(url, headers=headers, json=payload, timeout=15)
    
    if res.ok:
        try:
            wamid = res.json().get("messages", [{}])[0].get("id")
        except Exception:
            wamid = None
        _log_outbound_to_fastapi(
            phone_number=phone_number,
            text=text,
            msg_type="interactive" if (button_title and button_payload) else "text",
            wamid=wamid
        )
    return res


def send_smart_order_confirmation(
    phone_number, ipo_name, order_type, group_name,
    order_datetime, kostak_str="", subject_str="", premium_str="", options_str="",
    remark_text="", template_name="ipo_order_grouped", ipo_id=None, broker_id=None
):
    """
    Smart Dispatcher:
    - If customer is INSIDE 24hr free window: Sends custom rich-markdown free text + Quick Reply Button (0 cost).
    - If customer is OUTSIDE 24hr free window: Automatically falls back to Meta pre-approved template message.
    """
    if is_within_24hr_window(phone_number):
        logger.info(f"[24HR_WINDOW] Customer {phone_number} is INSIDE 24hr window. Sending free-text message with Interactive Button.")
        formatted_text = format_24hr_order_message(
            ipo_name=ipo_name,
            order_type=order_type,
            group_name=group_name,
            order_datetime=order_datetime,
            kostak_str=kostak_str,
            subject_str=subject_str,
            premium_str=premium_str,
            options_str=options_str,
            remark_text=remark_text
        )
        button_payload = None
        button_title = None
        if ipo_id:
            button_payload = f"view_orders_{ipo_id}_{broker_id}" if broker_id else f"view_orders_{ipo_id}"
            button_title = "View Order History"

        return send_free_text_message(
            phone_number=phone_number,
            text=formatted_text,
            button_title=button_title,
            button_payload=button_payload
        )
    else:
        logger.info(f"[24HR_WINDOW] Customer {phone_number} is OUTSIDE 24hr window. Falling back to template message.")
        return send_grouped_order_confirmation(
            phone_number=phone_number,
            ipo_name=ipo_name,
            order_type=order_type,
            group_name=group_name,
            order_datetime=order_datetime,
            kostak_str=kostak_str,
            subject_str=subject_str,
            premium_str=premium_str,
            options_str=options_str,
            remark_text=remark_text,
            template_name=template_name,
            ipo_id=ipo_id,
            broker_id=broker_id
        )


