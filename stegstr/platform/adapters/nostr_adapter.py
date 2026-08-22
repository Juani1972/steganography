"""
Nostr Platform Adapter v2.2 — Bridge entre NostrClient y el pipeline de validación E2E.

Implementa la interfaz estándar de adaptadores de Stegstr para que Nostr pueda
usarse desde la GUI, CLI y validador real sin romper el pipeline.

Requiere: websockets>=12.0, aiohttp>=3.9.0, secp256k1>=0.14.0
"""

import os
import asyncio
import tempfile
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class NostrAdapter:
    """
    Adaptador de plataforma para Nostr (protocolo descentralizado).

    Usa NostrClient internamente para publicar imágenes vía NIP-96
    y recuperarlas para validación E2E.
    """

    def __init__(self, private_key: Optional[str] = None,
                 relay_urls: Optional[list] = None,
                 nip96_server: str = "https://nostr.build"):
        self.private_key = private_key or os.environ.get("NOSTR_PRIVATE_KEY")
        self.relay_urls = relay_urls or [
            "wss://relay.damus.io",
            "wss://nos.lol",
            "wss://relay.nostr.band",
        ]
        self.nip96_server = nip96_server
        self._client = None
        self._last_image_url: Optional[str] = None

    def _get_client(self):
        if self._client is None:
            from stegstr.nostr.client import NostrClient
            self._client = NostrClient(
                private_key_hex=self.private_key,
                relays=self.relay_urls,
            )
        return self._client

    def platform_name(self) -> str:
        return "nostr"

    def description(self) -> str:
        return "Nostr Protocol — NIP-96 image upload + relay publishing"

    def requires_credentials(self) -> bool:
        return True

    def is_available(self) -> bool:
        if not self.private_key:
            return False
        try:
            from stegstr.nostr.client import NostrClient
            import secp256k1
            return True
        except ImportError:
            return False

    def upload(self, image_path: str) -> Optional[str]:
        """
        Upload image via NIP-96 and publish event to Nostr relays.
        Returns the NIP-96 image URL for later download.
        """
        if not self.is_available():
            logger.warning("Nostr adapter not available — missing private_key or dependencies")
            return None

        client = self._get_client()

        async def _do_upload():
            await client.connect()
            try:
                url = await client.upload_image_nip96(image_path, server_url=self.nip96_server)
                if url:
                    self._last_image_url = url
                    await client.publish_stegstr_post(
                        image_url=url,
                        image_path=image_path,
                        wait_for_acks=False,
                    )
                return url
            finally:
                await client.disconnect()

        try:
            return asyncio.run(_do_upload())
        except Exception as e:
            logger.error(f"Nostr upload failed: {e}")
            return None

    def download(self, url: str, output_path: str) -> bool:
        """
        Download image from Nostr (direct URL from NIP-96 upload).
        """
        try:
            import requests
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"Nostr download: {len(resp.content)} bytes")
            return True
        except Exception as e:
            logger.error(f"Nostr download failed: {e}")
            return False
