import requests
import json

# Pointing directly to FastAPI to test the backend logic
WEBHOOK_URL = "http://127.0.0.1:8005/chat-api/whatsapp/webhook/"

# This is the exact JSON structure Meta sends when a user clicks an interactive button
payload = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "1234567890", # Your WABA ID
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "1234567890",
                            "phone_number_id": "0987654321"
                        },
                        "contacts": [
                            {
                                "profile": {
                                    "name": "Test User"
                                },
                                "wa_id": "919876543210" # Sender phone number
                            }
                        ],
                        "messages": [
                            {
                                "from": "919876543210",
                                "id": "wamid.HBgLOTE5ODc2NTQzMjEw...",
                                "timestamp": "1700000000",
                                "type": "interactive",
                                "interactive": {
                                    "type": "button_reply",
                                    "button_reply": {
                                        "id": "view_orders_btn_id",
                                        "title": "View Orders" # This is the exact text FastAPI should look for
                                    }
                                }
                            }
                        ]
                    },
                    "field": "messages"
                }
            ]
        }
    ]
}

print(f"Sending simulated Meta webhook to: {WEBHOOK_URL}")

try:
    response = requests.post(
        WEBHOOK_URL,
        headers={"Content-Type": "application/json"},
        json=payload
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Connection Error: {e}")
