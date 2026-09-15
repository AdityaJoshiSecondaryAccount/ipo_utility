import logging
import json
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Contact, Conversation, Message, utcnow
from .whatsapp_client import whatsapp_client
from .websocket_manager import manager
from .config import settings

logger = logging.getLogger(__name__)

async def get_or_create_contact_and_conversation(session: AsyncSession, phone: str, name: str = None) -> tuple[Contact, Conversation]:
    # Find contact
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    stmt = select(Contact).where(Contact.phone_number == clean_phone)
    result = await session.execute(stmt)
    contact = result.scalar_one_or_none()

    if not contact:
        contact = Contact(phone_number=clean_phone, name=name or f"+{clean_phone}")
        session.add(contact)
        await session.flush()
    elif name and (not contact.name or contact.name.startswith("+")):
        contact.name = name

    # Find conversation
    stmt = select(Conversation).where(Conversation.contact_id == contact.id)
    result = await session.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        conv = Conversation(contact_id=contact.id)
        session.add(conv)
        await session.flush()

    return contact, conv


async def forward_to_existing_django(raw_payload: dict):
    """Forwards button interactions like 'view_orders' to existing Django application."""
    if not settings.EXISTING_DJANGO_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                settings.EXISTING_DJANGO_WEBHOOK_URL,
                json=raw_payload,
                headers={"Content-Type": "application/json"}
            )
            logger.info(f"Forwarded payload to Django. Status: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Could not forward payload to Django app: {e}")


async def process_webhook_payload(payload: dict, session: AsyncSession):
    """Processes Meta WhatsApp Cloud API webhook POST payload."""
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                
                # 1. Process Status Updates (sent, delivered, read, failed)
                statuses = value.get("statuses", [])
                for status_data in statuses:
                    wamid = status_data.get("id")
                    status_val = status_data.get("status")  # sent, delivered, read, failed
                    timestamp_str = status_data.get("timestamp")
                    
                    if wamid and status_val:
                        stmt = select(Message).where(Message.wamid == wamid)
                        result = await session.execute(stmt)
                        msg = result.scalar_one_or_none()
                        if msg:
                            msg.status = status_val
                            if status_val == "failed":
                                errors = status_data.get("errors", [])
                                if errors:
                                    msg.error_message = errors[0].get("message", "Delivery failed")
                            await session.commit()
                            
                            # Broadcast update to UI
                            await manager.broadcast("MESSAGE_STATUS_UPDATE", {
                                "message_id": msg.id,
                                "conversation_id": msg.conversation_id,
                                "wamid": wamid,
                                "status": status_val,
                                "error_message": msg.error_message
                            })

                # 2. Process Incoming Messages
                messages = value.get("messages", [])
                contacts_meta = value.get("contacts", [])
                
                # Map phone to profile name
                profile_name = None
                if contacts_meta:
                    profile_name = contacts_meta[0].get("profile", {}).get("name")

                for msg_data in messages:
                    sender_phone = msg_data.get("from")
                    msg_id = msg_data.get("id")
                    msg_type = msg_data.get("type", "text")
                    ts = msg_data.get("timestamp")
                    msg_time = datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts else utcnow()

                    contact, conv = await get_or_create_contact_and_conversation(
                        session, sender_phone, profile_name
                    )

                    body_text = ""
                    media_url = None
                    media_mime = None
                    media_filename = None
                    button_payload = None

                    if msg_type == "text":
                        body_text = msg_data.get("text", {}).get("body", "")
                    elif msg_type == "interactive":
                        interactive = msg_data.get("interactive", {})
                        int_type = interactive.get("type")
                        if int_type == "button_reply":
                            reply = interactive.get("button_reply", {})
                            body_text = reply.get("title", "")
                            button_payload = reply.get("id", "")
                        elif int_type == "list_reply":
                            reply = interactive.get("list_reply", {})
                            body_text = reply.get("title", "")
                            button_payload = reply.get("id", "")
                    elif msg_type == "button":
                        btn = msg_data.get("button", {})
                        body_text = btn.get("text", "")
                        button_payload = btn.get("payload", "")
                    elif msg_type == "image":
                        image_data = msg_data.get("image", {})
                        body_text = image_data.get("caption", "[Image]")
                        media_mime = image_data.get("mime_type")
                        media_id = image_data.get("id")
                        if media_id:
                            media_url = await whatsapp_client.get_media_url(media_id)
                    elif msg_type == "document":
                        doc_data = msg_data.get("document", {})
                        body_text = doc_data.get("caption", doc_data.get("filename", "[Document]"))
                        media_filename = doc_data.get("filename")
                        media_mime = doc_data.get("mime_type")
                        media_id = doc_data.get("id")
                        if media_id:
                            media_url = await whatsapp_client.get_media_url(media_id)
                    elif msg_type == "audio":
                        body_text = "[Voice Note / Audio]"
                        audio_data = msg_data.get("audio", {})
                        media_mime = audio_data.get("mime_type")
                        media_id = audio_data.get("id")
                        if media_id:
                            media_url = await whatsapp_client.get_media_url(media_id)
                    else:
                        body_text = f"[{msg_type.capitalize()} message]"

                    # Check if already inserted
                    stmt = select(Message).where(Message.wamid == msg_id)
                    res = await session.execute(stmt)
                    existing_msg = res.scalar_one_or_none()
                    if existing_msg:
                        continue

                    # Insert message
                    new_msg = Message(
                        conversation_id=conv.id,
                        wamid=msg_id,
                        direction="inbound",
                        message_type=msg_type,
                        text=body_text,
                        media_url=media_url,
                        media_mime_type=media_mime,
                        media_filename=media_filename,
                        status="delivered",
                        timestamp=msg_time,
                        raw_payload=json.dumps(msg_data)
                    )
                    session.add(new_msg)

                    # Update conversation stats
                    conv.last_message_text = body_text
                    conv.last_message_time = msg_time
                    conv.last_message_status = "delivered"
                    conv.last_inbound_time = msg_time
                    conv.unread_count = (conv.unread_count or 0) + 1

                    await session.commit()
                    await session.refresh(new_msg)
                    await session.refresh(conv)
                    await session.refresh(contact)

                    # Realtime Broadcast to Frontend
                    await manager.broadcast("NEW_MESSAGE", {
                        "message": {
                            "id": new_msg.id,
                            "conversation_id": conv.id,
                            "wamid": new_msg.wamid,
                            "direction": new_msg.direction,
                            "message_type": new_msg.message_type,
                            "text": new_msg.text,
                            "media_url": new_msg.media_url,
                            "media_mime_type": new_msg.media_mime_type,
                            "media_filename": new_msg.media_filename,
                            "status": new_msg.status,
                            "timestamp": new_msg.timestamp.isoformat()
                        },
                        "conversation": {
                            "id": conv.id,
                            "contact": {
                                "id": contact.id,
                                "phone_number": contact.phone_number,
                                "name": contact.name
                            },
                            "unread_count": conv.unread_count,
                            "last_message_text": conv.last_message_text,
                            "last_message_time": conv.last_message_time.isoformat(),
                            "last_message_status": conv.last_message_status,
                            "last_inbound_time": conv.last_inbound_time.isoformat() if conv.last_inbound_time else None,
                            "is_window_open": True
                        }
                    })

                    # If customer clicked "View Your Orders" button or payload indicates order inquiry, forward to Django
                    if button_payload and ("view_orders" in str(button_payload).lower() or "order" in str(button_payload).lower()):
                        logger.info(f"Detected view_orders payload: {button_payload}. Routing to existing ADwealth Django...")
                        await forward_to_existing_django(payload)
                    elif body_text and "view your orders" in body_text.lower():
                        logger.info(f"Detected 'View Your Orders' text: {body_text}. Routing to existing ADwealth Django...")
                        await forward_to_existing_django(payload)

    except Exception as e:
        logger.error(f"Error processing webhook payload: {e}", exc_info=True)
        await session.rollback()
