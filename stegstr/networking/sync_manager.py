"""
Sync Manager — Reliable networking layer for steganographic message exchange.
"""

import asyncio
import base64
import hashlib
import json
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from stegstr.nostr.client import NostrClient, NostrEvent

logger = logging.getLogger(__name__)


class MessageState(Enum):
    CREATED = auto(); QUEUED = auto(); SENT = auto()
    RECEIVED = auto(); VERIFIED = auto(); FAILED = auto(); RETRYING = auto()


@dataclass
class StegstrMessage:
    id: str
    sender_pubkey: Optional[str]
    recipient_pubkey: Optional[str]
    payload_b64: str
    timestamp: float
    state: MessageState = MessageState.CREATED
    platform_hint: str = ""
    mode_hint: str = ""
    retry_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(
                f"{self.sender_pubkey or ''}:{self.recipient_pubkey or ''}:{self.payload_b64}:{self.timestamp}".encode()
            ).hexdigest()[:32]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "sender_pubkey": self.sender_pubkey,
            "recipient_pubkey": self.recipient_pubkey, "payload_b64": self.payload_b64,
            "timestamp": self.timestamp, "state": self.state.name,
            "platform_hint": self.platform_hint, "mode_hint": self.mode_hint,
            "retry_count": self.retry_count, "last_error": self.last_error,
            "metadata": self.metadata,
        }


class SyncManager:
    MAX_RETRIES = 5
    BASE_RETRY_DELAY = 2.0
    DEDUP_WINDOW_SECONDS = 3600

    def __init__(self, nostr_client: Optional[NostrClient] = None, store_path: Optional[str] = None, private_key_hex: Optional[str] = None):
        self.nostr = nostr_client
        self.store_path = Path(store_path) if store_path else None
        self._messages: Dict[str, StegstrMessage] = {}
        self._handlers: List[Callable[[StegstrMessage], None]] = []
        self._dedup_cache: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._background_task: Optional[asyncio.Task] = None
        if not self.nostr and private_key_hex:
            self.nostr = NostrClient(private_key_hex=private_key_hex)

    async def start(self):
        if self.nostr:
            await self.nostr.connect()
            self.nostr.on_event(self._on_nostr_event)
        self._background_task = asyncio.create_task(self._background_processor())
        logger.info("SyncManager started")

    async def stop(self):
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        if self.nostr:
            await self.nostr.disconnect()
        self._persist_store()
        logger.info("SyncManager stopped")

    def register_handler(self, handler: Callable[[StegstrMessage], None]):
        self._handlers.append(handler)

    async def send_message(self, payload_b64: str, recipient_pubkey: Optional[str] = None,
                           platform_hint: str = "", mode_hint: str = "", metadata: Optional[Dict[str, Any]] = None) -> str:
        msg = StegstrMessage(
            id="", sender_pubkey=self.nostr.pubkey if self.nostr else None,
            recipient_pubkey=recipient_pubkey, payload_b64=payload_b64,
            timestamp=time.time(), platform_hint=platform_hint, mode_hint=mode_hint, metadata=metadata or {},
        )
        msg.state = MessageState.QUEUED
        async with self._lock:
            self._messages[msg.id] = msg
        await self._try_send(msg.id)
        return msg.id

    async def _try_send(self, msg_id: str):
        async with self._lock:
            msg = self._messages.get(msg_id)
            if not msg or msg.state not in (MessageState.QUEUED, MessageState.RETRYING):
                return
        if not self.nostr:
            msg.last_error = "No Nostr client configured"; msg.state = MessageState.FAILED; return
        content = json.dumps({
            "stegstr_version": "2.1.5", "payload_b64": msg.payload_b64,
            "platform_hint": msg.platform_hint, "mode_hint": msg.mode_hint, "metadata": msg.metadata,
        })
        tags = [["t", "stegstr"]]
        if msg.recipient_pubkey:
            tags.append(["p", msg.recipient_pubkey])
        try:
            event_id = await self.nostr.publish_event(kind=1, content=content, tags=tags)
            if event_id:
                msg.state = MessageState.SENT; msg.last_error = None
                logger.info(f"Message {msg_id} sent as event {event_id}")
            else:
                raise ConnectionError("Publish returned None")
        except Exception as e:
            msg.retry_count += 1
            if msg.retry_count >= self.MAX_RETRIES:
                msg.state = MessageState.FAILED; msg.last_error = str(e)
            else:
                msg.state = MessageState.RETRYING; msg.last_error = str(e)

    async def _background_processor(self):
        while True:
            try:
                await asyncio.sleep(5); await self._process_retries(); self._persist_store()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background error: {e}")

    async def _process_retries(self):
        retrying = []
        async with self._lock:
            for msg in self._messages.values():
                if msg.state == MessageState.RETRYING:
                    retrying.append(msg.id)
        for msg_id in retrying:
            delay = self.BASE_RETRY_DELAY * (2 ** self._messages[msg_id].retry_count)
            await asyncio.sleep(delay); await self._try_send(msg_id)

    async def _on_nostr_event(self, event: NostrEvent, relay: str):
        if event.kind != 1:
            return
        is_stegstr = any(len(t) >= 2 and t[0] == "t" and t[1] == "stegstr" for t in event.tags)
        if not is_stegstr:
            return
        try:
            data = json.loads(event.content)
        except json.JSONDecodeError:
            return
        payload_b64 = data.get("payload_b64")
        if not payload_b64:
            return
        payload_hash = hashlib.sha256(payload_b64.encode()).hexdigest()
        now = time.time()
        if payload_hash in self._dedup_cache and now - self._dedup_cache[payload_hash] < self.DEDUP_WINDOW_SECONDS:
            return
        self._dedup_cache[payload_hash] = now
        msg = StegstrMessage(
            id=event.id[:32] if event.id else payload_hash[:32],
            sender_pubkey=event.pubkey, recipient_pubkey=None,
            payload_b64=payload_b64, timestamp=event.created_at,
            state=MessageState.RECEIVED, platform_hint=data.get("platform_hint", ""),
            mode_hint=data.get("mode_hint", ""), metadata=data.get("metadata", {}),
        )
        async with self._lock:
            self._messages[msg.id] = msg
        if msg.metadata.get("payload_sha256"):
            expected = msg.metadata["payload_sha256"]
            actual = hashlib.sha256(base64.b64decode(payload_b64)).hexdigest()
            if expected == actual:
                msg.state = MessageState.VERIFIED
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(msg)
                else:
                    handler(msg)
            except Exception as e:
                logger.error(f"Handler error: {e}")

    def get_messages(self, state: Optional[MessageState] = None) -> List[Dict[str, Any]]:
        return [msg.to_dict() for msg in self._messages.values() if state is None or msg.state == state]

    def get_message(self, msg_id: str) -> Optional[Dict[str, Any]]:
        msg = self._messages.get(msg_id)
        return msg.to_dict() if msg else None

    def _persist_store(self):
        if not self.store_path:
            return
        try:
            data = {k: v.to_dict() for k, v in self._messages.items()}
            for v in data.values():
                v["state"] = v["state"].name if hasattr(v["state"], "name") else str(v["state"])
            self.store_path.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.error(f"Persist failed: {e}")

    def load_store(self):
        if not self.store_path or not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            for k, v in data.items():
                v["state"] = MessageState[v["state"]]
                self._messages[k] = StegstrMessage(**v)
        except Exception as e:
            logger.error(f"Load failed: {e}")
