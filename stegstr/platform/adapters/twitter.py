"""
Twitter/X API v2 Adapter for Stegstr Real-World Validation.

Requires:
  - TWITTER_BEARER_TOKEN
  - TWITTER_API_KEY, TWITTER_API_SECRET
  - TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET

Twitter re-encodes images aggressively. One of the hardest platforms.

Usage:
    export TWITTER_BEARER_TOKEN="..."
    export TWITTER_API_KEY="..."
    export TWITTER_API_SECRET="..."
    export TWITTER_ACCESS_TOKEN="..."
    export TWITTER_ACCESS_TOKEN_SECRET="..."
"""

import os
import time
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class TwitterAdapter:
    """Upload/download images via Twitter API v2 + v1.1 media upload."""

    def __init__(self, bearer_token: Optional[str] = None,
                 api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 access_token: Optional[str] = None, access_token_secret: Optional[str] = None):
        self.bearer_token = bearer_token or os.environ.get("TWITTER_BEARER_TOKEN")
        self.api_key = api_key or os.environ.get("TWITTER_API_KEY")
        self.api_secret = api_secret or os.environ.get("TWITTER_API_SECRET")
        self.access_token = access_token or os.environ.get("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")
        self._session = requests.Session()

    def platform_name(self) -> str:
        return "twitter"

    def description(self) -> str:
        return "Twitter/X API v2 — aggressive re-encoding, hardest platform"

    def requires_credentials(self) -> bool:
        return True

    def is_available(self) -> bool:
        return bool(self.bearer_token and self.api_key and self.api_secret
                   and self.access_token and self.access_token_secret)

    def upload(self, image_path: str) -> Optional[str]:
        if not self.is_available():
            logger.warning("Twitter adapter not available")
            return None
        try:
            import tweepy
            client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                self.access_token, self.access_token_secret,
            )
            api = tweepy.API(auth)
            media = api.media_upload(image_path)
            tweet = client.create_tweet(text="Stegstr validation", media_ids=[media.media_id])
            tweet_id = tweet.data["id"]

            # Bug previo: si Twitter tardaba en indexar la media, el código
            # caía directo al fallback `https://twitter.com/i/web/status/{id}`,
            # una URL de PÁGINA (HTML), no de imagen. download() la descargaba
            # igualmente "con éxito" (200 OK) pero el contenido era HTML, no
            # una imagen — el fallo real solo se veía después, al intentar
            # extraer el mensaje, con un error confuso de "not an image".
            # Ahora reintentamos varias veces con espera antes de rendirnos,
            # y si no conseguimos la URL real de la imagen, devolvemos None
            # explícitamente para que el fallo se reporte como "Upload failed"
            # en el punto correcto.
            for attempt in range(4):
                time.sleep(3 if attempt == 0 else 2)
                tweet_data = client.get_tweet(
                    tweet_id, expansions=["attachments.media_keys"],
                    media_fields=["url"],
                )
                if tweet_data.includes and tweet_data.includes.get("media"):
                    for m in tweet_data.includes["media"]:
                        if hasattr(m, "url") and m.url:
                            return m.url
                logger.debug(f"Twitter media URL not ready yet (attempt {attempt + 1})")

            logger.error(
                f"Twitter media URL never became available for tweet {tweet_id}; "
                "not returning the tweet permalink since it is not a downloadable image."
            )
            return None
        except Exception as e:
            logger.error(f"Twitter upload failed: {e}")
        return None

    def download(self, url: str, output_path: str) -> bool:
        try:
            resp = self._session.get(url, timeout=60)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            logger.error(f"Twitter download failed: {e}")
            return False
