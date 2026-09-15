from datetime import datetime, timezone
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_serializer

def serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

class ContactBase(BaseModel):
    phone_number: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class ContactResponse(ContactBase):
    id: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dates(self, dt: datetime) -> str:
        return serialize_datetime(dt)

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    text: Optional[str] = None
    message_type: str = "text"
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None
    media_filename: Optional[str] = None

class MessageCreate(BaseModel):
    phone_number: str
    text: Optional[str] = None
    message_type: str = "text"
    media_url: Optional[str] = None
    media_filename: Optional[str] = None

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    wamid: Optional[str] = None
    direction: str
    message_type: str
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None
    media_filename: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        return serialize_datetime(dt)

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    contact: ContactResponse
    unread_count: int
    last_message_text: Optional[str] = None
    last_message_time: Optional[datetime] = None
    last_message_status: Optional[str] = None
    last_inbound_time: Optional[datetime] = None
    is_window_open: bool = False
    is_archived: bool = False

    @field_serializer("last_message_time", "last_inbound_time")
    def serialize_conversation_dates(self, dt: Optional[datetime]) -> Optional[str]:
        return serialize_datetime(dt)

    class Config:
        from_attributes = True

class CannedResponseItem(BaseModel):
    id: int
    shortcut: str
    title: str
    body: str
    category: str

    class Config:
        from_attributes = True

class CannedResponseCreate(BaseModel):
    shortcut: str
    title: str
    body: str
    category: str = "General"
