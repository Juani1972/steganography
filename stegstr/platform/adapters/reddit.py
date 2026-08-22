"""
Reddit API Adapter for Stegstr Real-World Validation.

Requires:
  - REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD
  - A target subreddit (default: r/test)

Reddit re-encodes uploaded images (i.redd.it). Good for testing
resilience against platform compression.

Usage:
    export REDDIT_CLIENT_ID="..."
    export REDDIT_CLIENT_SECRET="..."
    export REDDIT_USERNAME="..."
    export REDDIT_PASSWORD="..."
    export REDDIT_SUBREDDIT="test"
"""

import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RedditAdapter:
    """Upload/download images via Reddit PRAW."""

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None,
                 username: Optional[str] = None, password: Optional[str] = None,
                 subreddit: Optional[str] = None):
        self.client_id = client_id or os.environ.get("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("REDDIT_CLIENT_SECRET")
        self.username = username or os.environ.get("REDDIT_USERNAME")
        self.password = password or os.environ.get("REDDIT_PASSWORD")
        self.subreddit = subreddit or os.environ.get("REDDIT_SUBREDDIT", "test")
        self._reddit = None

    def platform_name(self) -> str:
        return "reddit"

    def description(self) -> str:
        return "Reddit PRAW — i.redd.it re-encoding, requires OAuth app"

    def requires_credentials(self) -> bool:
        return True

    def is_available(self) -> bool:
        if not all([self.client_id, self.client_secret, self.username, self.password]):
            return False
        try:
            import praw
            self._reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                username=self.username,
                password=self.password,
                user_agent="StegstrValidator/2.1.3",
            )
            self._reddit.user.me()
            return True
        except Exception:
            return False

    def upload(self, image_path: str) -> Optional[str]:
        if not self.is_available():
            logger.warning("Reddit adapter not available")
            return None
        try:
            import praw
            if self._reddit is None:
                self._reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    username=self.username,
                    password=self.password,
                    user_agent="StegstrValidator/2.1.3",
                )
            sub = self._reddit.subreddit(self.subreddit)
            title = f"Stegstr validation {int(time.time())}"
            submission = sub.submit_image(title, image_path)
            # Wait for image to be available
            time.sleep(5)
            return submission.url
        except Exception as e:
            logger.error(f"Reddit upload failed: {e}")
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
            logger.error(f"Reddit download failed: {e}")
            return False
