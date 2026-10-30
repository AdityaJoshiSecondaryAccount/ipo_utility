import time
import threading
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class IPOAllotmentAPIClient:
    """
    Unified Multi-Registrar Client for IPO Allotment Checker API
    (Specification: https://api.ipoutility.in/api/v1)
    """
    BASE_URL = "https://api.ipoutility.in/api/v1"
    DEFAULT_USERNAME = "Demo"
    DEFAULT_PASSWORD = "Demo@1234"
    TOKEN_VALIDITY_SECONDS = 25 * 60  # 25 minutes (server has 30m rolling expiration)
    REQUEST_TIMEOUT = 60  # 60 seconds per batch

    def __init__(self, username: str = None, password: str = None):
        self.username = username or self.DEFAULT_USERNAME
        self.password = password or self.DEFAULT_PASSWORD
        self._access_token: Optional[str] = None
        self._token_time: float = 0.0
        self._lock = threading.Lock()
        self._session = requests.Session()

    def get_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Retrieves or refreshes the Bearer JWT token in a thread-safe manner.
        Auto-refreshes if older than 25 minutes or if force_refresh is True.
        """
        with self._lock:
            now = time.time()
            if not force_refresh and self._access_token and (now - self._token_time < self.TOKEN_VALIDITY_SECONDS):
                return self._access_token

            login_url = f"{self.BASE_URL}/login"
            payload = {
                "username": self.username,
                "password": self.password
            }
            try:
                resp = self._session.post(login_url, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    self._access_token = data.get("access_token")
                    self._token_time = now
                    logger.info("[AllotmentAPI] Token successfully acquired.")
                    return self._access_token
                else:
                    logger.error(f"[AllotmentAPI] Login failed ({resp.status_code}): {resp.text}")
                    return None
            except Exception as e:
                logger.error(f"[AllotmentAPI] Login exception: {e}")
                return None

    def _get_headers(self, force_refresh: bool = False) -> Dict[str, str]:
        token = self.get_token(force_refresh=force_refresh)
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        return {"Content-Type": "application/json"}

    def get_active_ipos(self, registrar: str = "bigshare") -> List[Dict[str, str]]:
        """
        Fetches active IPOs for a given registrar (e.g. 'bigshare').
        Returns list of dicts: [{'ipo_id': '...', 'ipo_name': '...'}]
        """
        url = f"{self.BASE_URL}/registrars/{registrar}/ipos"
        headers = self._get_headers()
        try:
            resp = self._session.get(url, headers=headers, timeout=15)
            if resp.status_code == 401:
                # Token expired/invalidated, refresh and retry once
                headers = self._get_headers(force_refresh=True)
                resp = self._session.get(url, headers=headers, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and "data" in data:
                    return data["data"]
            logger.warning(f"[AllotmentAPI] Failed to fetch active IPOs for {registrar}: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"[AllotmentAPI] Error fetching active IPOs for {registrar}: {e}")
        return []

    def check_allotment_chunk(self, registrar: str, ipo_id: str, ipo_name: str, pans: List[str], search_type: str = "pan", max_retries: int = 2) -> List[Dict[str, Any]]:
        """
        Checks allotment for up to 100 lookup values via POST /api/v1/allotment/check.
        Includes automatic retry on transient timeout/network errors.
        """
        if not pans:
            return []
        
        # Enforce max 100 limit per request
        pans = pans[:100]
        url = f"{self.BASE_URL}/allotment/check"
        payload = {
            "registrar": registrar,
            "ipo_id": str(ipo_id),
            "ipo_name": str(ipo_name),
            "search_type": search_type,
            "values": pans
        }

        for attempt in range(max_retries + 1):
            headers = self._get_headers()
            try:
                # timeout=(15, None): 15s to establish connection, no read timeout (waits for full response)
                resp = self._session.post(url, json=payload, headers=headers, timeout=(15, None))
                if resp.status_code == 401:
                    headers = self._get_headers(force_refresh=True)
                    resp = self._session.post(url, json=payload, headers=headers, timeout=(15, None))

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and "results" in data:
                        return data["results"]
                logger.error(f"[AllotmentAPI] Check allotment failed (attempt {attempt+1}, {resp.status_code}): {resp.text}")
            except Exception as e:
                logger.warning(f"[AllotmentAPI] Exception checking allotment chunk (attempt {attempt+1}/{max_retries+1}): {e}")
                if attempt < max_retries:
                    time.sleep(1.5)
                    continue

        # Return fallback error records if all attempts failed
        fallback_results = []
        for pan in pans:
            fallback_results.append({
                "search_type": search_type,
                "search_value": pan,
                "pan": pan,
                "registrar": registrar,
                "ipo_id": ipo_id,
                "ipo_name": ipo_name,
                "status": "error",
                "applicant_name": "",
                "application_number": "",
                "dp_id_client_id": "",
                "shares_applied": 0,
                "shares_allotted": 0,
                "category": "",
                "error_reason": "ERROR"
            })
        return fallback_results

    def check_allotment_bulk(self, registrar: str, ipo_id: str, ipo_name: str, pans: List[str], search_type: str = "pan") -> List[Dict[str, Any]]:
        """
        Chunks any number of PANs into batches of 100, calls the API sequentially/concurrently,
        and aggregates the combined results.
        """
        if not pans:
            return []

        all_results = []
        batch_size = 100
        total_pans = len(pans)
        
        logger.info(f"[AllotmentAPI] Starting bulk allotment check for {total_pans} PANs on {registrar} ('{ipo_name}')...")

        for i in range(0, total_pans, batch_size):
            chunk = pans[i:i + batch_size]
            logger.info(f"[AllotmentAPI] Querying batch {i // batch_size + 1} ({len(chunk)} PANs)...")
            chunk_results = self.check_allotment_chunk(
                registrar=registrar,
                ipo_id=ipo_id,
                ipo_name=ipo_name,
                pans=chunk,
                search_type=search_type
            )
            all_results.extend(chunk_results)

        return all_results

# Global singleton client instance
allotment_api_client = IPOAllotmentAPIClient()
