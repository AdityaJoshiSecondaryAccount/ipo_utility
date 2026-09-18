import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Contact, Conversation, Message, CannedResponse, utcnow
from ..schemas import (
    ConversationResponse, MessageResponse, MessageCreate,
    CannedResponseItem, CannedResponseCreate, OutboundLogCreate
)
from ..whatsapp_client import whatsapp_client
from ..websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-api", tags=["Conversations & Messages"])

def is_within_24_hours(last_inbound_time: Optional[datetime]) -> bool:
    if not last_inbound_time:
        return False
    # Check if timezone aware
    if last_inbound_time.tzinfo is None:
        last_inbound = last_inbound_time.replace(tzinfo=timezone.utc)
    else:
        last_inbound = last_inbound_time
    now = datetime.now(timezone.utc)
    return (now - last_inbound) <= timedelta(hours=24)


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    search: Optional[str] = None,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Lists all conversations ordered by most recent message."""
    query = select(Conversation).options(selectinload(Conversation.contact)).order_by(desc(Conversation.last_message_time))
    
    if unread_only:
        query = query.where(Conversation.unread_count > 0)
        
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    output = []
    for conv in conversations:
        # Search filter if provided
        if search:
            s = search.lower()
            name_match = conv.contact.name and s in conv.contact.name.lower()
            phone_match = s in conv.contact.phone_number
            msg_match = conv.last_message_text and s in conv.last_message_text.lower()
            if not (name_match or phone_match or msg_match):
                continue
                
        output.append(ConversationResponse(
            id=conv.id,
            contact=conv.contact,
            unread_count=conv.unread_count,
            last_message_text=conv.last_message_text,
            last_message_time=conv.last_message_time,
            last_message_status=conv.last_message_status,
            last_inbound_time=conv.last_inbound_time,
            is_window_open=is_within_24_hours(conv.last_inbound_time),
            is_archived=conv.is_archived
        ))
        
    return output


@router.get("/conversations/{conv_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conv_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all messages for a given conversation."""
    stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.timestamp.asc())
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return messages


@router.post("/conversations/{conv_id}/read")
async def mark_conversation_as_read(
    conv_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Resets the unread count for a conversation and sends Read Receipts (Blue Ticks) to Meta.
    """
    stmt = select(Conversation).where(Conversation.id == conv_id)
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    conv.unread_count = 0

    # Find unread inbound messages to notify Meta
    msg_stmt = select(Message).where(
        Message.conversation_id == conv_id,
        Message.direction == "inbound",
        Message.status != "read"
    )
    msg_res = await db.execute(msg_stmt)
    unread_messages = msg_res.scalars().all()

    for msg in unread_messages:
        msg.status = "read"
        if msg.wamid:
            try:
                await whatsapp_client.mark_message_as_read(msg.wamid)
            except Exception as e:
                logger.warning(f"Could not send read receipt to Meta for {msg.wamid}: {e}")

    await db.commit()
    
    # Broadcast to UI
    await manager.broadcast("CONVERSATION_READ", {"conversation_id": conv_id})
    return {"status": "success", "conversation_id": conv_id, "marked_read_count": len(unread_messages)}


@router.post("/messages/send", response_model=MessageResponse)
async def send_message(
    msg_in: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Sends an employee reply to a customer through WhatsApp Cloud API.
    """
    clean_phone = msg_in.phone_number.replace("+", "").replace(" ", "").replace("-", "")
    
    # 1. Find or create Contact & Conversation
    stmt = select(Contact).where(Contact.phone_number == clean_phone)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        contact = Contact(phone_number=clean_phone, name=f"+{clean_phone}")
        db.add(contact)
        await db.flush()
        
    stmt = select(Conversation).where(Conversation.contact_id == contact.id)
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(contact_id=contact.id)
        db.add(conv)
        await db.flush()

    # 2. Call WhatsApp Cloud API
    wamid = None
    status = "sent"
    error_msg = None
    
    try:
        media_id = None
        if msg_in.media_url and ("/chat-api/file/" in msg_in.media_url or "localhost" in msg_in.media_url):
            filename = msg_in.media_url.split("/")[-1]
            from pathlib import Path
            local_path = Path(__file__).resolve().parent.parent.parent / "uploads" / filename
            if local_path.exists():
                import mimetypes
                mime_type, _ = mimetypes.guess_type(local_path)
                media_id = await whatsapp_client.upload_media(str(local_path), mime_type or "application/octet-stream")

        if msg_in.message_type == "image" and msg_in.media_url:
            resp = await whatsapp_client.send_image_message(
                clean_phone, 
                image_url=msg_in.media_url if not media_id else None, 
                caption=msg_in.text,
                media_id=media_id
            )
        elif msg_in.message_type == "document" and msg_in.media_url:
            resp = await whatsapp_client.send_document_message(
                clean_phone, 
                document_url=msg_in.media_url if not media_id else None, 
                filename=msg_in.media_filename, 
                caption=msg_in.text,
                media_id=media_id
            )
        else:
            if not msg_in.text:
                raise HTTPException(status_code=400, detail="Message text is required")
            resp = await whatsapp_client.send_text_message(clean_phone, msg_in.text)
            
        messages_resp = resp.get("messages", [])
        if messages_resp:
            wamid = messages_resp[0].get("id")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        status = "failed"
        error_msg = str(e)

    # 3. Store message in Database
    now = utcnow()
    new_msg = Message(
        conversation_id=conv.id,
        wamid=wamid,
        direction="outbound",
        message_type=msg_in.message_type,
        text=msg_in.text,
        media_url=msg_in.media_url,
        media_filename=msg_in.media_filename,
        status=status,
        error_message=error_msg,
        timestamp=now
    )
    db.add(new_msg)
    
    # Update conversation metadata
    conv.last_message_text = msg_in.text or f"[{msg_in.message_type.capitalize()}]"
    conv.last_message_time = now
    conv.last_message_status = status
    
    await db.commit()
    await db.refresh(new_msg)
    
    # 4. Broadcast message creation to UI clients via WebSocket
    await manager.broadcast("NEW_MESSAGE", {
        "message": {
            "id": new_msg.id,
            "conversation_id": conv.id,
            "wamid": new_msg.wamid,
            "direction": new_msg.direction,
            "message_type": new_msg.message_type,
            "text": new_msg.text,
            "media_url": new_msg.media_url,
            "media_filename": new_msg.media_filename,
            "status": new_msg.status,
            "error_message": new_msg.error_message,
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
            "last_inbound_time": conv.last_inbound_time.isoformat() if conv.last_inbound_time else None
        }
    })

    if status == "failed":
        raise HTTPException(status_code=400, detail=f"Message failed to send: {error_msg}")

    return new_msg


@router.post("/test/simulate-incoming")
async def simulate_incoming_test_message(
    phone_choice: str = Query("1"),
    text: str = Query("Hello! This is a live test message from WhatsApp."),
    db: AsyncSession = Depends(get_db)
):
    """Simulates an incoming WhatsApp message for 6355783769 or 7016868618 directly from UI."""
    from ..webhook_handler import process_webhook_payload
    import time
    phone = "916355783769" if phone_choice == "1" else "917016868618"
    name = "Aditya (6355783769)" if phone_choice == "1" else "Prateek (7016868618)"
    
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
                        "profile": {"name": name},
                        "wa_id": phone
                    }],
                    "messages": [{
                        "from": phone,
                        "id": f"wamid.ui_test_{int(time.time()*1000)}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": text},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    await process_webhook_payload(mock_payload, db)
    return {"status": "success", "phone": phone, "message": text}


@router.post("/log-outbound")
async def log_outbound_message(
    log_in: OutboundLogCreate,
    db: AsyncSession = Depends(get_db)
):
    """Logs an outbound message sent externally (e.g. from Django/Postman)."""
    clean_phone = log_in.phone_number.replace("+", "").replace(" ", "").replace("-", "")
    
    # 1. Find or create Contact & Conversation
    stmt = select(Contact).where(Contact.phone_number == clean_phone)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        contact = Contact(phone_number=clean_phone, name=f"+{clean_phone}")
        db.add(contact)
        await db.flush()
        
    stmt = select(Conversation).where(Conversation.contact_id == contact.id)
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(contact_id=contact.id)
        db.add(conv)
        await db.flush()

    # 3. Store message in Database
    now = utcnow()
    new_msg = Message(
        conversation_id=conv.id,
        wamid=log_in.wamid,
        direction="outbound",
        message_type=log_in.message_type,
        text=log_in.text,
        media_url=log_in.media_url,
        media_filename=log_in.media_filename,
        status=log_in.status,
        timestamp=now
    )
    db.add(new_msg)
    
    # Update conversation metadata
    conv.last_message_text = log_in.text or f"[{log_in.message_type.capitalize()}]"
    conv.last_message_time = now
    conv.last_message_status = log_in.status
    
    await db.commit()
    await db.refresh(new_msg)
    
    # 4. Broadcast message creation to UI clients via WebSocket
    await manager.broadcast("NEW_MESSAGE", {
        "message": {
            "id": new_msg.id,
            "conversation_id": conv.id,
            "wamid": new_msg.wamid,
            "direction": new_msg.direction,
            "message_type": new_msg.message_type,
            "text": new_msg.text,
            "media_url": new_msg.media_url,
            "media_filename": new_msg.media_filename,
            "status": new_msg.status,
            "error_message": new_msg.error_message,
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
            "last_inbound_time": conv.last_inbound_time.isoformat() if conv.last_inbound_time else None
        }
    })

    return {"status": "success", "message_id": new_msg.id}


# --- Canned Responses API ---
@router.get("/canned-responses", response_model=List[CannedResponseItem])
async def get_canned_responses(db: AsyncSession = Depends(get_db)):
    """Lists predefined quick replies."""
    stmt = select(CannedResponse).order_by(CannedResponse.id.asc())
    res = await db.execute(stmt)
    items = res.scalars().all()
    
    # Seed default canned responses if table is empty
    if not items:
        defaults = [
            CannedResponse(shortcut="/greet", title="Welcome Greeting", body="Hello! Welcome to ADwealth Support. How can we assist you today?", category="Greetings"),
            CannedResponse(shortcut="/order", title="Order Check", body="Please hold on while I check your order details in our system.", category="Orders"),
            CannedResponse(shortcut="/ipo_help", title="IPO Support", body="For IPO applications, kindly confirm your registered PAN and Group Name.", category="Support"),
            CannedResponse(shortcut="/thanks", title="Thank You", body="Thank you for contacting ADwealth. Have a wonderful day ahead!", category="Closing"),
        ]
        db.add_all(defaults)
        await db.commit()
        res = await db.execute(stmt)
        items = res.scalars().all()
        
    return items


@router.post("/canned-responses", response_model=CannedResponseItem)
async def create_canned_response(
    item_in: CannedResponseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Creates a new canned quick reply."""
    new_item = CannedResponse(**item_in.model_dump())
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    return new_item


@router.delete("/canned-responses/{item_id}")
async def delete_canned_response(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Deletes a canned quick reply."""
    stmt = select(CannedResponse).where(CannedResponse.id == item_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return {"status": "deleted"}
