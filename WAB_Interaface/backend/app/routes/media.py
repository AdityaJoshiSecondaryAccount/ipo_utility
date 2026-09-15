import os
import shutil
import uuid
import httpx
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from ..config import settings

router = APIRouter(prefix="/api/media", tags=["Media"])

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

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
        "media_url": f"/api/media/file/{unique_filename}",
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")
