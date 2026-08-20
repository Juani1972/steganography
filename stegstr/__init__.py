"""
Stegstr Next — Steganografía Robusta para Redes Sociales v2.2
"""

__version__ = "2.2.0"

from .stego.engine import StegoEngine, StegoMode

try:
    from .nostr import NostrClient, NostrEvent
except ImportError:
    pass

try:
    from .platform import RealWorldValidator
except ImportError:
    pass

__all__ = [
    "StegoEngine",
    "StegoMode",
    "NostrClient",
    "NostrEvent",
    "RealWorldValidator",
]
