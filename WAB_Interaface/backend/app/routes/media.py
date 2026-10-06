import logging
import os
import shutil
import uuid
import httpx
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Request
from fastapi.responses import FileResponse
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-api", tags=["Media Proxy"])

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

LOCAL_MEDIA_DIR = MEDIA_DIR / "media"
LOCAL_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

PROD_MEDIA_BASE_URL = "https://hostinger.ipoutility.in/chat-api/media/local"


@router.get("/media/local/{filename}")
async def get_local_media(filename: str, request: Request):
    """
    Serves generated local media file (e.g. orders summary PNGs).
    If missing locally (e.g. created on production server), automatically proxies and caches from production.
    """
    file_path = LOCAL_MEDIA_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)

    # Prevent loop if request is already a proxy fallback request
    if request.headers.get("X-Proxy-Fallback") == "1":
        raise HTTPException(status_code=404, detail="Media file not found")

    # Fallback: attempt to fetch and cache from production Hostinger server
    prod_url = f"{PROD_MEDIA_BASE_URL}/{filename}"
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(prod_url, headers={"X-Proxy-Fallback": "1"})
            if resp.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(resp.content)
                content_type = resp.headers.get("Content-Type", "image/png")
                return Response(content=resp.content, media_type=content_type)
    except Exception as e:
        logger.warning(f"Could not fetch media {filename} from production: {e}")

    raise HTTPException(status_code=404, detail="Media file not found")



@router.post("/upload")
async def upload_media_file(file: UploadFile = File(...)):
    """Saves uploaded media file locally to be served or sent via WhatsApp."""
    ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = MEDIA_DIR / unique_filename

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": file.filename,
        "media_url": f"/chat-api/file/{unique_filename}",
        "content_type": file.content_type
    }


@router.get("/file/{filename}")
async def get_uploaded_file(filename: str):
    """Serves locally uploaded file."""
    file_path = MEDIA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    with file_path.open("rb") as f:
        content = f.read()
        
    return Response(content=content)


@router.get("/proxy")
async def proxy_whatsapp_media(url: str):
    """Securely proxies media download from Meta WhatsApp CDN using Bearer token."""
    # Safety fallback: if an internal uploaded file URL was passed, serve it directly
    if "/chat-api/file/" in url:
        filename = url.split("/chat-api/file/")[-1].split("?")[0]
        file_path = MEDIA_DIR / filename
        if file_path.exists():
            import mimetypes
            content_type, _ = mimetypes.guess_type(str(file_path))
            with file_path.open("rb") as f:
                content = f.read()
            return Response(content=content, media_type=content_type or "application/octet-stream")
        raise HTTPException(status_code=404, detail="File not found")

    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("Content-Type", "application/octet-stream")
                )
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch media from Meta")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

