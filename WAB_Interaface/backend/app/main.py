import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .database import init_db
from .websocket_manager import manager
from .routes import webhook, conversations, media

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("WAB_Inbox")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing IPO Utility WhatsApp Inbox Database...")
    await init_db()
    try:
        from .database import AsyncSessionLocal
        from .models import Conversation, Message
        from sqlalchemy import select, desc
        async with AsyncSessionLocal() as session:
            convs_res = await session.execute(select(Conversation))
            for conv in convs_res.scalars().all():
                last_msg_res = await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(desc(Message.timestamp), desc(Message.id))
                    .limit(1)
                )
                last_msg = last_msg_res.scalar_one_or_none()
                if last_msg:
                    new_text = last_msg.text or f"[{last_msg.message_type.capitalize()}]"
                    if conv.last_message_text != new_text:
                        conv.last_message_text = new_text
                        conv.last_message_time = last_msg.timestamp
                        conv.last_message_status = last_msg.status
                elif conv.last_message_text is not None:
                    conv.last_message_text = None
                    conv.last_message_status = "sent"
            await session.commit()
            logger.info("Conversation latest messages synchronized.")
    except Exception as e:
        logger.warning(f"Could not auto-sync conversation last messages: {e}")

    logger.info("IPO Utility WhatsApp Inbox running on http://localhost:%s", settings.PORT)
    yield
    logger.info("Shutting down IPO Utility WhatsApp Inbox...")

app = FastAPI(
    title="IPO Utility WhatsApp Inbox API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register backend API and webhook routes
app.include_router(webhook.router)
app.include_router(conversations.router)
app.include_router(media.router)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads", "media")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/chat-api/media/local", StaticFiles(directory=UPLOAD_DIR), name="local_media")

# WebSocket endpoint for real-time live inbox updates
@app.websocket("/chat-api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        manager.disconnect(websocket)

# Serve built frontend static assets if available
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/chat/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/chat/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/chat")
    async def serve_spa_root():
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "service": "IPO Utility WhatsApp Business Inbox",
            "status": "online",
            "phone_number_id": settings.WHATSAPP_PHONE_NUMBER_ID
        }

        


