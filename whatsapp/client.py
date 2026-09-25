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
    template_name="ipo_order_formatted"
):
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = _get_api_headers("application/json")

    components = [{
        "type": "body",
        "parameters": [
            {"type": "text", "text": str(ipo_name)},
            {"type": "text", "text": str(order_type)},
            {"type": "text", "text": str(group_name)},
            {"type": "text", "text": str(order_datetime)},
            {"type": "text", "text": kostak_str if kostak_str else "\u200B"},
            {"type": "text", "text": subject_str if subject_str else "\u200B"},
            {"type": "text", "text": premium_str if premium_str else "\u200B"},
            {"type": "text", "text": options_str if options_str else "\u200B"},
            {"type": "text", "text": remark_text if remark_text else "\u200B"},
        ],
    }]

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": components,
        },
    }

    res = requests.post(url, headers=headers, json=payload, timeout=15)

    # Log to FastAPI
    if res.ok:
        try:
            wamid = res.json().get("messages", [{}])[0].get("id")
        except:
            wamid = None
        exact_text = f"Order Confirmation\nIPO: {ipo_name}\nOrder Type: {order_type}\nGroup: {group_name}\nDate: {order_datetime}\n\nKostak: {kostak_str}\nSubject To: {subject_str}\nPremium: {premium_str}\nOptions: {options_str}\nRemarks: {remark_text}"
        _log_outbound_to_fastapi(
            phone_number=phone_number,
            text=exact_text,
            msg_type="template",
            wamid=wamid
        )
    return res
