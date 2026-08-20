"""
Selenium Fallback Adapter for Stegstr Real-World Validation.

For platforms without easy APIs (WhatsApp Web, Facebook, Signal Desktop),
uses Selenium/Playwright to automate browser upload/download.

Requires:
  - selenium or playwright installed
  - Browser driver (chromedriver, geckodriver, etc.)

This is a generic base class. Specific platform subclasses would extend it.
"""

import os
import time
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SeleniumFallbackAdapter:
    """Generic Selenium-based adapter for platforms without APIs."""

    def __init__(self, platform: str, upload_url: str, download_selector: str):
        self.platform = platform
        self.upload_url = upload_url
        self.download_selector = download_selector
        self._driver = None

    def platform_name(self) -> str:
        return self.platform

    def description(self) -> str:
        return f"Selenium fallback for {self.platform} — browser automation"

    def requires_credentials(self) -> bool:
        return True  # Usually requires login via browser

    def is_available(self) -> bool:
        try:
            from selenium import webdriver
            return True
        except ImportError:
            try:
                from playwright.sync_api import sync_playwright
                return True
            except ImportError:
                return False

    def _get_driver(self):
        if self._driver is None:
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                opts = Options()
                opts.add_argument("--headless")
                opts.add_argument("--no-sandbox")
                opts.add_argument("--disable-dev-shm-usage")
                self._driver = webdriver.Chrome(options=opts)
            except Exception as e:
                logger.error(f"Could not start Selenium driver: {e}")
        return self._driver

    def upload(self, image_path: str) -> Optional[str]:
        """
        Generic upload via Selenium.
        Subclasses should override with platform-specific selectors.
        """
        logger.warning(f"Selenium upload for {self.platform} not fully implemented. "
                       "Subclass with platform-specific selectors.")
        return None

    def download(self, url: str, output_path: str) -> bool:
        try:
            import requests
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            logger.error(f"Selenium download failed: {e}")
            return False

    def __del__(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
