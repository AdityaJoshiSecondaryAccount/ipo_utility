from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    conversations = relationship("Conversation", back_populates="contact", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, unique=True)
    unread_count = Column(Integer, default=0)
    last_message_text = Column(Text, nullable=True)
    last_message_time = Column(DateTime, default=utcnow, index=True)
    last_message_status = Column(String(20), default="sent")  # sent, delivered, read, failed
    last_inbound_time = Column(DateTime, nullable=True)  # For tracking 24-hr session window
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    contact = relationship("Contact", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.timestamp", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    wamid = Column(String(100), unique=True, index=True, nullable=True)
    direction = Column(String(10), nullable=False)  # "inbound" or "outbound"
    message_type = Column(String(20), default="text")  # text, image, document, audio, video, interactive, template
    text = Column(Text, nullable=True)
    media_id = Column(String(100), nullable=True)
    media_url = Column(String(1000), nullable=True)
    media_mime_type = Column(String(100), nullable=True)
    media_filename = Column(String(255), nullable=True)
    status = Column(String(20), default="sent")  # pending, sent, delivered, read, failed
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    raw_payload = Column(Text, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


class CannedResponse(Base):
    __tablename__ = "canned_responses"

    id = Column(Integer, primary_key=True, index=True)
    shortcut = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(50), default="General")
