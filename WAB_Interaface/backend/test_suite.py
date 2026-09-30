import asyncio
import httpx
from app.main import app
from app.database import init_db

async def run_tests():
    print("--- Starting ADwealth WhatsApp Inbox Automated Test Suite ---")
    await init_db()
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Root Check (Serves Web Inbox UI)
        r = await client.get("/")
        print(f"1. Root Endpoint: status={r.status_code} (Serves Inbox UI)")
        assert r.status_code == 200

        # 2. Webhook Handshake Verification (GET)
        r = await client.get("/chat-api/whatsapp/webhook/?hub.mode=subscribe&hub.verify_token=ADwealth_WA_Webhook_2026&hub.challenge=998877")
        print(f"2. Webhook Handshake (GET): status={r.status_code}, body={r.text}")
        assert r.status_code == 200
        assert r.text == "998877"

        # 3. Simulate Incoming Customer Message (POST)
        mock_payload = {
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
                            "profile": {"name": "Test User 1"},
                            "wa_id": "916355783769"
                        }],
                        "messages": [{
                            "from": "916355783769",
                            "id": "wamid.HBgMOTExOTg3NjU0MzIxMBUCABIYFDNBRjAxMjM0NTY3ODkwMTIzNDU2AA==",
                            "timestamp": "1726376400",
                            "text": {"body": "Hi, I have a question about my IPO order."},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        r = await client.post("/chat-api/whatsapp/webhook/", json=mock_payload)
        print(f"3. Inbound Message Webhook (POST): status={r.status_code}, response={r.json()}")
        assert r.status_code == 200

        # Simulate Incoming Message for Second Number (7016868618)
        mock_payload_2 = {
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
                            "profile": {"name": "Test User 2"},
                            "wa_id": "917016868618"
                        }],
                        "messages": [{
                            "from": "917016868618",
                            "id": "wamid.HBgMOTExOTg3NjU0MzIxMBUCABIYFDNBRjAxMjM0NTY3ODkwMTIzNDU3BB==",
                            "timestamp": "1726376500",
                            "text": {"body": "Is my allotment confirmed?"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        r2 = await client.post("/whatsapp/webhook/", json=mock_payload_2)
        print(f"3b. Inbound Webhook User 2 (POST): status={r2.status_code}, response={r2.json()}")
        assert r2.status_code == 200

        # 4. Check Conversations List
        r = await client.get("/api/conversations")
        convs = r.json()
        print(f"4. List Conversations (GET): count={len(convs)}")
        assert len(convs) >= 1
        conv_id = convs[0]["id"]
        print(f"   First Conv: Contact={convs[0]['contact']['name']} ({convs[0]['contact']['phone_number']}), Last Msg={convs[0]['last_message_text']}")

        # 5. Check Conversation Messages
        r = await client.get(f"/api/conversations/{conv_id}/messages")
        msgs = r.json()
        print(f"5. Get Messages (GET): count={len(msgs)}")
        assert len(msgs) >= 1
        print(f"   First Message: '{msgs[0]['text']}' (Direction: {msgs[0]['direction']}, Status: {msgs[0]['status']})")

        # 6. Check Canned Responses
        r = await client.get("/api/canned-responses")
        canned = r.json()
        print(f"6. Canned Responses (GET): count={len(canned)}")
        assert len(canned) >= 4

    print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
