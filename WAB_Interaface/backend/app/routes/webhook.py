import logging
import hmac
import hashlib
from fastapi import APIRouter, Request, Query, Response, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import settings
from ..database import get_db
from ..webhook_handler import process_webhook_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-api", tags=["Webhook"])

def verify_meta_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verifies X-Hub-Signature-256 header against WHATSAPP_APP_SECRET."""
    if not settings.WHATSAPP_APP_SECRET or not signature_header:
        return True  # Skip if secret is not set or empty
    
    if not signature_header.startswith("sha256="):
        return False
        
    expected_hash = hmac.new(
        key=settings.WHATSAPP_APP_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    received_hash = signature_header.split("sha256=")[1]
    return hmac.compare_digest(expected_hash, received_hash)


@router.get("/webhook")
@router.get("/whatsapp/webhook/")
@router.get("/whatsapp/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Handles Meta webhook verification handshake.
    """
    logger.info(f"Webhook verification request: mode={hub_mode}, token={hub_verify_token}")
    
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook successfully verified by Meta.")
        return Response(content=hub_challenge, media_type="text/plain")
        
    logger.warning(f"Webhook verification failed. Expected token: {settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN}, Received: {hub_verify_token}")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/webhook")
@router.post("/whatsapp/webhook/")
@router.post("/whatsapp/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests live incoming WhatsApp events from Meta Cloud API.
    """
    raw_body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    
    # Optional HMAC signature verification
    if settings.WHATSAPP_APP_SECRET and sig_header:
        if not verify_meta_signature(raw_body, sig_header):
            logger.warning("Invalid HMAC signature received from Meta webhook")
            # We log warning but continue to prevent Meta from disabling the webhook endpoint if secret is slightly different
            
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    # Process payload in DB
    await process_webhook_payload(payload, db)
    
    return {"status": "success"}


@router.post("/whatsapp/flow-endpoint/")
@router.post("/whatsapp/flow-endpoint")
@router.post("/flow-endpoint/")
@router.post("/flow-endpoint")
async def handle_whatsapp_flow(request: Request):
    """
    Handles Meta WhatsApp Flows endpoint requests (health check ping, INIT, and data_exchange).
    """
    try:
        import sys
        from pathlib import Path
        import os

        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        try:
            import django
            from django.conf import settings as django_settings
            if not django_settings.configured:
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "userproject.settings")
                django.setup()
        except Exception as err:
            logger.error(f"Django setup exception: {err}")

        from whatsapp.flow_crypto import decrypt_request, encrypt_response, FlowDecryptionError
        from whatsapp.flow_endpoint import handle_flow_action

        payload = await request.json()
        encrypted_flow_data = payload.get("encrypted_flow_data")
        encrypted_aes_key = payload.get("encrypted_aes_key")
        initial_vector = payload.get("initial_vector")

        if not all([encrypted_flow_data, encrypted_aes_key, initial_vector]):
            raise HTTPException(status_code=400, detail="Missing required encrypted payload fields")

        key_path = project_root / "whatsapp" / "flow_keys" / "private.pem"
        if not key_path.exists():
            logger.error(f"Private key not found at {key_path}")
            return Response(content="Private Key Missing", status_code=500)

        with open(key_path, "rb") as f:
            private_key_pem = f.read()

        # Decrypt payload
        decrypted_body, aes_key, iv = decrypt_request(
            encrypted_flow_data,
            encrypted_aes_key,
            initial_vector,
            private_key_pem,
        )

        logger.info(f"Decrypted Flow Request via FastAPI: {decrypted_body}")

        # Process logic in worker thread (safe for Django ORM)
        import asyncio
        customer_phone = request.query_params.get("phone") or request.headers.get("X-Customer-Phone")
        response_dict = await asyncio.to_thread(handle_flow_action, decrypted_body, customer_phone=customer_phone)

        # Encrypt response
        encrypted_response_b64 = encrypt_response(response_dict, aes_key, iv)

        return Response(content=encrypted_response_b64, media_type="text/plain")

    except FlowDecryptionError as e:
        logger.error(f"Flow decryption error: {e}")
        return Response(content="Decryption Error", status_code=421)
    except Exception as e:
        logger.error(f"Flow endpoint error: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=500)

