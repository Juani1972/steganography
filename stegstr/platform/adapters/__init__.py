"""
Platform adapters for Stegstr real-world validation.
"""

try:
    from .telegram import TelegramAdapter
except ImportError:
    TelegramAdapter = None

try:
    from .whatsapp import WhatsAppAdapter, SeleniumFallbackAdapter
except ImportError:
    WhatsAppAdapter = None
    SeleniumFallbackAdapter = None

try:
    from .instagram import InstagramAdapter
except ImportError:
    InstagramAdapter = None

try:
    from .twitter import TwitterAdapter
except ImportError:
    TwitterAdapter = None

try:
    from .reddit import RedditAdapter
except ImportError:
    RedditAdapter = None

try:
    from .discord import DiscordAdapter
except ImportError:
    DiscordAdapter = None

try:
    from .imgur import ImgurAdapter
except ImportError:
    ImgurAdapter = None

__all__ = [
    "TelegramAdapter",
    "WhatsAppAdapter",
    "SeleniumFallbackAdapter",
    "InstagramAdapter",
    "TwitterAdapter",
    "RedditAdapter",
    "DiscordAdapter",
    "ImgurAdapter",
]
