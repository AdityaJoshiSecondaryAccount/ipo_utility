import requests
from django.conf import settings


def send_order_confirmation(phone_number, ipo_name, order_type, group_name,
                            order_datetime, order_details):
    url = (
        "https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": "ipo_order_confirmation",
            "language": {"code": "en"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "parameter_name": "ipo_name", "text": str(ipo_name)},
                    {"type": "text", "parameter_name": "order_type", "text": str(order_type)},
                    {"type": "text", "parameter_name": "group_name", "text": str(group_name)},
                    {"type": "text", "parameter_name": "order_datetime", "text": str(order_datetime)},
                    {"type": "text", "parameter_name": "order_details", "text": str(order_details)},
                ],
            }],
        },
    }
    return requests.post(url, headers=headers, json=payload, timeout=15)

