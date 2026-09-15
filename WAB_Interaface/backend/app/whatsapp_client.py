import logging
import httpx
from typing import Optional, Dict, Any
from .config import settings

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"

class WhatsAppClient:
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.api_version = settings.WHATSAPP_API_VERSION or "v21.0"
        self.base_url = f"{GRAPH_API_BASE}/{self.api_version}/{self.phone_number_id}"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def send_text_message(self, to_phone: str, text: str) -> Dict[str, Any]:
        """Sends a text message to a customer's WhatsApp number."""
        clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "text",
            "text": {"preview_url": False, "body": text}
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=self._get_headers(), json=payload)
            data = response.json()
            if response.status_code >= 400:
                logger.error(f"Error sending WhatsApp text: {data}")
                raise Exception(data.get("error", {}).get("message", f"WhatsApp API error {response.status_code}"))
            return data

    async def send_image_message(self, to_phone: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Sends an image message with optional caption."""
        clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")
        url = f"{self.base_url}/messages"
        image_payload = {"link": image_url}
        if caption:
            image_payload["caption"] = caption
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "image",
            "image": image_payload
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=self._get_headers(), json=payload)
            data = response.json()
            if response.status_code >= 400:
                logger.error(f"Error sending WhatsApp image: {data}")
                raise Exception(data.get("error", {}).get("message", f"WhatsApp API error {response.status_code}"))
            return data

    async def send_document_message(self, to_phone: str, document_url: str, filename: Optional[str] = None, caption: Optional[str] = None) -> Dict[str, Any]:
        """Sends a document message."""
        clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")
        url = f"{self.base_url}/messages"
        doc_payload = {"link": document_url}
        if filename:
            doc_payload["filename"] = filename
        if caption:
            doc_payload["caption"] = caption
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "document",
            "document": doc_payload
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=self._get_headers(), json=payload)
            data = response.json()
            if response.status_code >= 400:
                logger.error(f"Error sending WhatsApp document: {data}")
                raise Exception(data.get("error", {}).get("message", f"WhatsApp API error {response.status_code}"))
            return data

    async def mark_message_as_read(self, message_id: str) -> bool:
        """Marks an incoming message as read."""
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, headers=self._get_headers(), json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to mark message {message_id} as read: {e}")
            return False

    async def get_media_url(self, media_id: str) -> Optional[str]:
        """Retrieves direct download URL for received media ID."""
        url = f"{GRAPH_API_BASE}/{self.api_version}/{media_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("url")
        except Exception as e:
            logger.warning(f"Failed to get media URL for {media_id}: {e}")
        return None

whatsapp_client = WhatsAppClient()
