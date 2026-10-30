"""
Interactive Mock WhatsApp Message Sender for Testing
Allows you to simulate incoming WhatsApp messages to the inbox from:
- 916355783769
- 917016868618
"""
import sys
import time
import requests

BACKEND_WEBHOOK_URL = "http://localhost:8001/whatsapp/webhook/"

USERS = {
    "1": {"phone": "916355783769", "name": "Aditya (6355783769)"},
    "2": {"phone": "917016868618", "name": "Prateek (7016868618)"}
}

def send_mock_message(user_choice, message_text, is_button=False):
    user = USERS.get(user_choice, USERS["1"])
    ts = str(int(time.time()))
    msg_id = f"wamid.mock_{int(time.time()*1000)}"

    if is_button:
        msg_obj = {
            "from": user["phone"],
            "id": msg_id,
            "timestamp": ts,
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {
                    "id": "view_orders",
                    "title": "View Your Orders"
                }
            }
        }
    else:
        msg_obj = {
            "from": user["phone"],
            "id": msg_id,
            "timestamp": ts,
            "type": "text",
            "text": {"body": message_text}
        }

    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1001693916214003",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "1287337667797572",
                        "phone_number_id": "1287337667797572"
                    },
                    "contacts": [{
                        "profile": {"name": user["name"]},
                        "wa_id": user["phone"]
                    }],
                    "messages": [msg_obj]
                },
                "field": "messages"
            }]
        }]
    }

    try:
        res = requests.post(BACKEND_WEBHOOK_URL, json=payload, timeout=5)
        if res.status_code == 200:
            print(f"[SUCCESS] Sent mock message from {user['name']}: '{message_text}'")
            print("Check your browser at http://localhost:5173 to see it appear live!")
        else:
            print(f"[FAILED] Webhook returned status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[ERROR] Could not connect to backend at {BACKEND_WEBHOOK_URL}. Is the backend running? ({e})")

if __name__ == "__main__":
    print("==================================================")
    print("   ADwealth WhatsApp Inbox - Mock Message Sender  ")
    print("==================================================")
    print("Select Sender:")
    print("1) 916355783769 (Aditya)")
    print("2) 917016868618 (Prateek)")
    
    choice = input("Enter 1 or 2 [Default 1]: ").strip() or "1"
    
    print("\nMessage Type:")
    print("1) Custom text message")
    print("2) 'View Your Orders' button click simulation")
    mtype = input("Enter choice [Default 1]: ").strip() or "1"

    if mtype == "2":
        send_mock_message(choice, "View Your Orders", is_button=True)
    else:
        text = input("\nEnter message to send: ").strip() or "Hello, please check my IPO allotment status."
        send_mock_message(choice, text, is_button=False)
