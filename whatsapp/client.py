import io
import requests
from django.conf import settings


def _get_api_headers(content_type="application/json"):
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def send_order_confirmation(phone_number, ipo_name, order_type, group_name,
                            order_datetime, order_details, ipo_id=None, broker_id=None):
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
            {"type": "text", "parameter_name": "order_details", "text": str(order_details)},
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
            "name": "ipo_order_confirmation",
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


def send_image_message(phone_number, media_id=None, image_url=None, caption=None):
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
    return requests.post(url, headers=headers, json=payload, timeout=15)


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
    return requests.post(url, headers=headers, json=payload, timeout=15)
