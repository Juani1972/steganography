"""
Nostr client for Stegstr.
"""

try:
    from .client import NostrClient, NostrEvent, RelayAck, SubscriptionResult
except ImportError:
    NostrClient = None
    NostrEvent = None
    RelayAck = None
    SubscriptionResult = None

__all__ = ["NostrClient", "NostrEvent", "RelayAck", "SubscriptionResult"]
