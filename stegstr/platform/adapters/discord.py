"""
Discord Webhook Adapter for Stegstr Real-World Validation.

Requires:
  - DISCORD_WEBHOOK_URL environment variable

Discord re-encodes uploaded images. Good proxy for testing
moderate JPEG compression.

Usage:
    export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
"""

import os
import json
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class DiscordAdapter:
    """Upload/download images via Discord webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
        self._session = requests.Session()

    def platform_name(self) -> str:
        return "discord"

    def description(self) -> str:
        return "Discord Webhook — re-encodes images, moderate compression"

    def requires_credentials(self) -> bool:
        return True

    def is_available(self) -> bool:
        return bool(self.webhook_url)

    def upload(self, image_path: str) -> Optional[str]:
        """Upload via webhook. Returns attachment URL from response."""
        if not self.is_available():
            logger.warning("Discord adapter not available")
            return None
        try:
            with open(image_path, "rb") as f:
                files = {"file": (os.path.basename(image_path), f)}
                data = {"content": "Stegstr validation upload"}
                # Discord webhooks return 204 No Content by default, with no
                # body to parse. `wait=true` makes Discord wait for message
                # creation and return the message object (including the
                # uploaded attachment URL we need) in the response body.
                resp = self._session.post(
                    self.webhook_url,
                    params={"wait": "true"},
                    data=data,
                    files=files,
                    timeout=60,
                )
            resp.raise_for_status()
            result = resp.json()
            attachments = result.get("attachments", [])
            if attachments:
                return attachments[0]["url"]
        except Exception as e:
            logger.error(f"Discord upload failed: {e}")
        return None

    def download(self, url: str, output_path: str) -> bool:
        try:
            resp = self._session.get(url, timeout=60)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            logger.error(f"Discord download failed: {e}")
            return False
