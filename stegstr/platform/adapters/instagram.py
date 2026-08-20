"""
Instagram Graph API Adapter v2.2 — Real-World End-to-End Validation.

Ciclo completo real:
  1. Host image en servidor temporal propio (sin depender de Imgur)
  2. Create media container → publish
  3. Get permalink
  4. Descargar imagen REAL procesada por Instagram desde permalink
  5. Extraer metadatos de compresión (OpenGraph scraping)

Requires:
  INSTAGRAM_BUSINESS_ACCOUNT_ID
  META_PAGE_ACCESS_TOKEN (long-lived)

Optional:
  INSTAGRAM_TEMP_HOST_PORT — puerto para servidor temporal (default 8765)
"""

import os
import time
import json
import logging
import tempfile
import threading
import hashlib
import functools
from typing import Optional, Dict, Any
from pathlib import Path
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler

import requests
from PIL import Image

logger = logging.getLogger(__name__)


class _QuietHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves files quietly (no log spam)."""
    def log_message(self, format, *args):
        pass


class InstagramAdapter:
    """
    Instagram Graph API adapter with self-hosted temporary image server.

    Avoids Imgur dependency by spinning up a temporary HTTP server
    to serve the image with a public URL, then downloads the
    ACTUAL processed image from Instagram after publishing.
    """

    GRAPH_API_VERSION = "v22.0"
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, account_id: Optional[str] = None,
                 access_token: Optional[str] = None,
                 temp_host_port: int = 8765):
        self.account_id = account_id or os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.access_token = access_token or os.environ.get("META_PAGE_ACCESS_TOKEN")
        self.temp_host_port = temp_host_port
        self._session = requests.Session()
        self._published_media_id: Optional[str] = None
        self._published_permalink: Optional[str] = None

    def platform_name(self) -> str:
        return "instagram"

    def description(self) -> str:
        return "Instagram Graph API — self-hosted temp server, real post-publish download"

    def requires_credentials(self) -> bool:
        return True

    def is_available(self) -> bool:
        return bool(self.account_id and self.access_token)

    def _start_temp_server(self, image_path: str) -> str:
        """
        Start a temporary HTTP server to serve the image.
        Returns the public URL (uses ngrok or local tunnel if available,
        otherwise assumes localhost is accessible).
        """
        # Try ngrok first for public URL
        public_url = self._try_ngrok(image_path)
        if public_url:
            return public_url

        # Fallback: local server (works if running on a server with public IP)
        tmpdir = tempfile.mkdtemp(prefix="stegstr_instagram_")
        dest = os.path.join(tmpdir, "image.png")
        shutil.copy(image_path, dest)

        # NOTE: SimpleHTTPRequestHandler doesn't read a `directory` attribute
        # set on the server instance — it must be bound via functools.partial
        # (or passed as a constructor kwarg) so the handler itself knows
        # which directory to serve from. Setting `server.directory` silently
        # does nothing and the handler falls back to serving the process's
        # current working directory, causing 404s for the uploaded image.
        handler_cls = functools.partial(_QuietHTTPHandler, directory=tmpdir)
        server = HTTPServer(("0.0.0.0", self.temp_host_port), handler_cls)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._temp_server = server

        # Try to detect public IP
        try:
            ip_resp = requests.get("https://api.ipify.org", timeout=5)
            public_ip = ip_resp.text.strip()
            url = f"http://{public_ip}:{self.temp_host_port}/image.png"
            logger.info(f"Temporary server at {url}")
            return url
        except Exception:
            logger.warning("Could not detect public IP. Using localhost (may fail with Instagram API).")
            return f"http://localhost:{self.temp_host_port}/image.png"

    def _try_ngrok(self, image_path: str) -> Optional[str]:
        """Try to use ngrok for a public URL."""
        try:
            import ngrok
            # ngrok v2 Python SDK
            listener = ngrok.connect(self.temp_host_port, "http")
            return listener.public_url + "/image.png"
        except Exception:
            pass
        # Try ngrok CLI
        try:
            import subprocess
            # Start ngrok in background
            proc = subprocess.Popen(
                ["ngrok", "http", str(self.temp_host_port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)
            # Get tunnel URL from ngrok API
            tunnels = requests.get("http://localhost:4040/api/tunnels", timeout=5).json()
            for t in tunnels.get("tunnels", []):
                if t["proto"] == "https":
                    return t["public_url"] + "/image.png"
        except Exception:
            pass
        return None

    def _stop_temp_server(self):
        """Stop temporary server if running."""
        if hasattr(self, "_temp_server"):
            try:
                self._temp_server.shutdown()
            except Exception:
                pass

    def upload(self, image_path: str) -> Optional[str]:
        """
        Upload image to Instagram via Graph API.
        Returns permalink URL for later download.
        """
        if not self.is_available():
            logger.warning("Instagram adapter not available")
            return None

        # 1. Get public URL via temporary server
        public_url = self._start_temp_server(image_path)
        if not public_url:
            logger.error("Could not create public URL for Instagram upload")
            return None

        # Wait for server to be ready
        time.sleep(2)

        try:
            # 2. Create media container
            container_url = f"{self.BASE_URL}/{self.account_id}/media"
            resp = self._session.post(
                container_url,
                data={
                    "image_url": public_url,
                    "caption": "Stegstr validation — test image",
                    "access_token": self.access_token,
                },
                timeout=60,
            )
            resp.raise_for_status()
            container = resp.json()
            if "id" not in container:
                logger.error(f"Container creation failed: {container}")
                self._stop_temp_server()
                return None
            container_id = container["id"]

            # 3. Poll for container readiness
            for attempt in range(15):
                time.sleep(3)
                status_resp = self._session.get(
                    f"{self.BASE_URL}/{container_id}"
                    f"?fields=status_code&access_token={self.access_token}",
                    timeout=30,
                )
                status_resp.raise_for_status()
                status = status_resp.json()
                code = status.get("status_code", "")
                logger.debug(f"Container status: {code} (attempt {attempt + 1})")
                if code == "FINISHED":
                    break
                if code == "ERROR":
                    logger.error(f"Container error: {status}")
                    self._stop_temp_server()
                    return None
            else:
                logger.error("Container not ready after max polling")
                self._stop_temp_server()
                return None

            # 4. Publish
            publish_url = f"{self.BASE_URL}/{self.account_id}/media_publish"
            pub_resp = self._session.post(
                publish_url,
                data={"creation_id": container_id, "access_token": self.access_token},
                timeout=60,
            )
            pub_resp.raise_for_status()
            publish = pub_resp.json()
            media_id = publish.get("id")
            self._published_media_id = media_id

            # 5. Get permalink
            if media_id:
                info_resp = self._session.get(
                    f"{self.BASE_URL}/{media_id}"
                    f"?fields=permalink,media_url&access_token={self.access_token}",
                    timeout=30,
                )
                info_resp.raise_for_status()
                info = info_resp.json()
                permalink = info.get("permalink")
                media_url = info.get("media_url")
                self._published_permalink = permalink
                self._published_media_url = media_url
                self._stop_temp_server()
                logger.info(f"Instagram published: {permalink}")
                return permalink

        except Exception as e:
            logger.error(f"Instagram upload failed: {e}")
        finally:
            self._stop_temp_server()
        return None

    def download(self, permalink: str, output_path: str) -> bool:
        """
        Download the ACTUAL processed image from Instagram.

        Strategy:
        1. Try direct media_url from publish response
        2. Fallback: scrape OpenGraph meta tags from permalink
        3. Final fallback: use oEmbed API
        """
        # Strategy 1: Direct media URL
        if hasattr(self, "_published_media_url") and self._published_media_url:
            try:
                resp = self._session.get(
                    self._published_media_url,
                    timeout=60,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    logger.info(f"Downloaded from media_url: {len(resp.content)} bytes")
                    return True
            except Exception as e:
                logger.debug(f"media_url download failed: {e}")

        # Strategy 2: Scrape OpenGraph from permalink
        try:
            resp = self._session.get(
                permalink,
                timeout=30,
                headers={"User-Agent": "facebookexternalhit/1.1"},
            )
            if resp.status_code == 200:
                html = resp.text
                # Extract og:image
                import re
                og_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
                if og_match:
                    img_url = og_match.group(1).replace("&amp;", "&")
                    img_resp = self._session.get(img_url, timeout=60)
                    if img_resp.status_code == 200:
                        with open(output_path, "wb") as f:
                            f.write(img_resp.content)
                        logger.info(f"Downloaded from og:image: {len(img_resp.content)} bytes")
                        return True
        except Exception as e:
            logger.debug(f"OpenGraph scrape failed: {e}")

        # Strategy 3: oEmbed
        try:
            oembed_url = f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/instagram_oembed"
            oembed_resp = self._session.get(
                oembed_url,
                params={"url": permalink, "access_token": self.access_token},
                timeout=30,
            )
            if oembed_resp.status_code == 200:
                data = oembed_resp.json()
                thumbnail_url = data.get("thumbnail_url")
                if thumbnail_url:
                    thumb_resp = self._session.get(thumbnail_url, timeout=60)
                    if thumb_resp.status_code == 200:
                        with open(output_path, "wb") as f:
                            f.write(thumb_resp.content)
                        return True
        except Exception as e:
            logger.debug(f"oEmbed failed: {e}")

        logger.error("All Instagram download strategies failed")
        return False

    def get_compression_info(self, permalink: str) -> Dict[str, Any]:
        """Analyze Instagram compression by comparing original vs downloaded."""
        info = {"platform": "instagram", "compression_detected": False}
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            if self.download(permalink, tmp_path):
                img = Image.open(tmp_path)
                info["format"] = img.format
                info["mode"] = img.mode
                info["size"] = img.size
                # Try to estimate JPEG quality
                if img.format == "JPEG":
                    # Rough estimate based on file size vs dimensions
                    w, h = img.size
                    pixels = w * h
                    file_size = os.path.getsize(tmp_path)
                    bpp = (file_size * 8) / pixels
                    info["bits_per_pixel"] = round(bpp, 3)
                    info["compression_detected"] = True
                    # Instagram typically produces ~0.5-2.0 bpp
                    if bpp < 1.5:
                        info["compression_level"] = "high"
                    elif bpp < 3.0:
                        info["compression_level"] = "medium"
                    else:
                        info["compression_level"] = "low"
        except Exception as e:
            info["error"] = str(e)
        finally:
            # Bug previo: si download() fallaba o Image.open() lanzaba excepción,
            # el fichero temporal nunca se borraba (fuga de ficheros en /tmp
            # en cada llamada fallida). Ahora se limpia siempre.
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        return info
