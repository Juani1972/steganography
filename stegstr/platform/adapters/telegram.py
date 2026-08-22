"""
Telegram Bot API Adapter v2.2 — Real-World End-to-End Validation.

Ciclo completo real:
  1. sendPhoto → compresión ligera por Telegram
  2. sendDocument → SIN compresión (archivo original)
  3. getFile → descarga del archivo procesado
  4. Comparación photo vs document para análisis de compresión
  5. Reintentos con backoff exponencial

Requires:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID

Optional:
  TELEGRAM_MAX_RETRIES (default 3)
  TELEGRAM_RETRY_BACKOFF (default 2.0)
"""

import os
import time
import tempfile
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

import requests
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class TelegramUploadResult:
    """Result of Telegram upload with metadata."""
    file_id: str
    file_unique_id: str
    file_size: int
    width: int
    height: int
    upload_type: str  # "photo" or "document"


class TelegramAdapter:
    """
    Telegram Bot API adapter with dual-mode upload (photo + document)
    and compression analysis.

    sendPhoto: Telegram re-encodes as JPEG (compresión ligera)
    sendDocument: Telegram preserva el archivo original (sin compresión)

    Para validación robusta:
    - Primero subimos como documento (ground truth, sin compresión)
    - Luego como foto (compresión real de Telegram)
    - Comparamos ambos para medir exactamente qué hace Telegram
    """

    API_BASE = "https://api.telegram.org/bot"

    def __init__(self, bot_token: Optional[str] = None,
                 chat_id: Optional[str] = None,
                 max_retries: int = 3,
                 retry_backoff: float = 2.0):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.max_retries = int(os.environ.get("TELEGRAM_MAX_RETRIES", max_retries))
        self.retry_backoff = float(os.environ.get("TELEGRAM_RETRY_BACKOFF", retry_backoff))
        self._session = requests.Session()
        self._last_photo_result: Optional[TelegramUploadResult] = None
        self._last_document_result: Optional[TelegramUploadResult] = None

    def platform_name(self) -> str:
        return "telegram"

    def description(self) -> str:
        return "Telegram Bot API — dual-mode (photo+document), compression tracking"

    def requires_credentials(self) -> bool:
        return True

    def is_available(self) -> bool:
        if not self.bot_token or not self.chat_id:
            return False
        try:
            resp = self._session.get(
                f"{self.API_BASE}{self.bot_token}/getMe",
                timeout=10
            )
            return resp.status_code == 200 and resp.json().get("ok")
        except Exception:
            return False

    def _api_call(self, method: str, **kwargs) -> Dict[str, Any]:
        """Make API call with retry and exponential backoff."""
        url = f"{self.API_BASE}{self.bot_token}/{method}"
        for attempt in range(self.max_retries):
            try:
                if "files" in kwargs:
                    resp = self._session.post(url, **kwargs, timeout=60)
                else:
                    resp = self._session.post(url, **kwargs, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                if data.get("ok"):
                    return data["result"]
                else:
                    raise RuntimeError(f"Telegram API error: {data.get('description')}")
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = self.retry_backoff ** attempt
                    logger.warning(f"Telegram API {method} failed (attempt {attempt + 1}), retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise
        return {}

    def upload_photo(self, image_path: str) -> Optional[TelegramUploadResult]:
        """Send as photo (Telegram applies JPEG compression)."""
        with open(image_path, "rb") as f:
            result = self._api_call(
                "sendPhoto",
                files={"photo": f},
                data={"chat_id": self.chat_id}
            )
        if result and "photo" in result:
            photos = result["photo"]
            largest = max(photos, key=lambda p: p.get("file_size", 0))
            self._last_photo_result = TelegramUploadResult(
                file_id=largest["file_id"],
                file_unique_id=largest.get("file_unique_id", ""),
                file_size=largest.get("file_size", 0),
                width=largest.get("width", 0),
                height=largest.get("height", 0),
                upload_type="photo",
            )
            return self._last_photo_result
        return None

    def upload_document(self, image_path: str) -> Optional[TelegramUploadResult]:
        """Send as document (Telegram preserves original file)."""
        with open(image_path, "rb") as f:
            result = self._api_call(
                "sendDocument",
                files={"document": (os.path.basename(image_path), f, "image/png")},
                data={"chat_id": self.chat_id}
            )
        if result and "document" in result:
            doc = result["document"]
            self._last_document_result = TelegramUploadResult(
                file_id=doc["file_id"],
                file_unique_id=doc.get("file_unique_id", ""),
                file_size=doc.get("file_size", 0),
                width=doc.get("width", 0),
                height=doc.get("height", 0),
                upload_type="document",
            )
            return self._last_document_result
        return None

    def upload(self, image_path: str) -> Optional[str]:
        """
        Upload image to Telegram.
        Returns file_id of the PHOTO (compressed) version for validation.
        Also stores document version for ground truth comparison.
        """
        if not self.is_available():
            logger.warning("Telegram adapter not available")
            return None

        # Upload both modes
        doc_result = self.upload_document(image_path)
        photo_result = self.upload_photo(image_path)

        if photo_result:
            logger.info(
                f"Telegram upload: photo={photo_result.file_size}B "
                f"document={doc_result.file_size if doc_result else 'N/A'}B"
            )
            return photo_result.file_id
        return None

    def download(self, file_id: str, output_path: str) -> bool:
        """Download file by file_id with retry logic."""
        if not self.is_available():
            return False
        try:
            # Get file path
            result = self._api_call("getFile", data={"file_id": file_id})
            file_path = result.get("file_path")
            if not file_path:
                return False

            # Download actual file
            dl_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            dl_resp = self._session.get(dl_url, timeout=60)
            dl_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(dl_resp.content)
            logger.info(f"Telegram download: {len(dl_resp.content)} bytes")
            return True
        except Exception as e:
            logger.error(f"Telegram download failed: {e}")
            return False

    def get_compression_analysis(self, original_path: str,
                                  photo_path: str,
                                  document_path: str) -> Dict[str, Any]:
        """
        Analyze Telegram compression by comparing original, photo, and document.

        Returns:
            {
                "photo_compression_ratio": float,
                "photo_quality_estimate": str,
                "dimensions_changed": bool,
                "format_changed": bool,
                "psnr_vs_original": float,
            }
        """
        analysis = {
            "photo_compression_ratio": 0.0,
            "photo_quality_estimate": "unknown",
            "dimensions_changed": False,
            "format_changed": False,
            "psnr_vs_original": 0.0,
        }
        try:
            orig = Image.open(original_path)
            photo = Image.open(photo_path)
            doc = Image.open(document_path)

            orig_size = os.path.getsize(original_path)
            photo_size = os.path.getsize(photo_path)
            doc_size = os.path.getsize(document_path)

            analysis["photo_compression_ratio"] = round(orig_size / max(photo_size, 1), 2)
            analysis["document_preserved"] = (doc_size == orig_size)
            analysis["dimensions_changed"] = (orig.size != photo.size)
            analysis["format_changed"] = (orig.format != photo.format)

            # Estimate JPEG quality from file size
            if photo.format == "JPEG":
                w, h = photo.size
                pixels = w * h
                bpp = (photo_size * 8) / max(pixels, 1)
                if bpp < 1.0:
                    analysis["photo_quality_estimate"] = "high_compression"
                elif bpp < 2.5:
                    analysis["photo_quality_estimate"] = "medium_compression"
                else:
                    analysis["photo_quality_estimate"] = "low_compression"

            # PSNR vs original
            import numpy as np
            orig_rgb = np.array(orig.convert("RGB"), dtype=np.float32)
            photo_rgb = np.array(photo.convert("RGB").resize(orig.size, Image.LANCZOS), dtype=np.float32)
            mse = np.mean((orig_rgb - photo_rgb) ** 2)
            if mse > 0:
                analysis["psnr_vs_original"] = round(20 * np.log10(255.0 / np.sqrt(mse)), 2)
            else:
                analysis["psnr_vs_original"] = float("inf")

        except Exception as e:
            analysis["error"] = str(e)
        return analysis

    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata from Telegram."""
        try:
            result = self._api_call("getFile", data={"file_id": file_id})
            return {
                "file_id": file_id,
                "file_path": result.get("file_path"),
                "file_size": result.get("file_size"),
                "width": result.get("width"),
                "height": result.get("height"),
            }
        except Exception as e:
            return {"error": str(e)}
