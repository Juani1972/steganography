"""
Imgur API Adapter for Stegstr Real-World Validation.

Requires:
  - IMGUR_CLIENT_ID environment variable (anonymous upload)

Imgur compresses uploaded images. This makes it an excellent proxy
for testing JPEG resilience without needing social media credentials.

Usage:
    export IMGUR_CLIENT_ID="your_client_id"
"""

import os
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class ImgurAdapter:
    """Upload/download images via Imgur anonymous API."""

    UPLOAD_URL = "https://api.imgur.com/3/image"

    def __init__(self, client_id: Optional[str] = None):
        self.client_id = client_id or os.environ.get("IMGUR_CLIENT_ID")
        self._session = requests.Session()
        if self.client_id:
            self._session.headers.update({"Authorization": f"Client-ID {self.client_id}"})

    def platform_name(self) -> str:
        return "imgur"

    def description(self) -> str:
        return "Imgur Anonymous API — JPEG compression proxy, no account needed"

    def requires_credentials(self) -> bool:
        return True  # client_id needed, but free and instant

    def is_available(self) -> bool:
        return bool(self.client_id)

    def upload(self, image_path: str) -> Optional[str]:
        """Upload image. Returns direct image URL."""
        if not self.is_available():
            logger.warning("Imgur adapter not available (set IMGUR_CLIENT_ID)")
            return None
        try:
            with open(image_path, "rb") as f:
                resp = self._session.post(
                    self.UPLOAD_URL,
                    data={"image": f.read(), "type": "file"},
                    timeout=60,
                )
            resp.raise_for_status()
            result = resp.json()
            if result.get("success"):
                return result["data"]["link"]  # direct image URL
        except Exception as e:
            logger.error(f"Imgur upload failed: {e}")
        return None

    def download(self, url: str, output_path: str) -> bool:
        """Download image from URL."""
        try:
            resp = self._session.get(url, timeout=60)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            logger.error(f"Imgur download failed: {e}")
            return False
