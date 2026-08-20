"""
Nostr Client v2.2 — Relay communication with resilient pool, integrity verification,
                    and REAL event collection via subscription queue.

Implements NIP-01 (basic protocol), NIP-05 (identity verification),
NIP-94 (media metadata), NIP-96 (HTTP file storage),
NIP-98 (HTTP auth), and SHA-256 integrity hashes for received media.

CAMBIOS v2.2:
- query_events() ahora recolecta eventos reales vía cola de suscripción
- ACK/confirmación de entrega por relay
- Gestión de suscripciones con sub_id tracking
- Resolución de duplicados entre relays
- Sincronización histórica con since/until
"""

import json
import time
import hashlib
import base64
import asyncio
from typing import List, Optional, Dict, Callable, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class NostrEvent:
    """Nostr event per NIP-01 specification."""
    id: str
    pubkey: str
    created_at: int
    kind: int
    tags: List[List[str]]
    content: str
    sig: str

    def to_json(self) -> List:
        """Serialize to NIP-01 canonical array [0, pubkey, created_at, kind, tags, content]."""
        return [0, self.pubkey, self.created_at, self.kind, self.tags, self.content]

    def compute_id(self) -> str:
        """Compute SHA-256 event ID per NIP-01."""
        data = json.dumps(self.to_json(), separators=(',', ':'), ensure_ascii=False)
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind,
            "tags": self.tags,
            "content": self.content,
            "sig": self.sig,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NostrEvent":
        return cls(
            id=data.get("id", ""),
            pubkey=data.get("pubkey", ""),
            created_at=data.get("created_at", 0),
            kind=data.get("kind", 1),
            tags=data.get("tags", []),
            content=data.get("content", ""),
            sig=data.get("sig", ""),
        )


@dataclass
class RelayAck:
    """ACK from a relay for a published event."""
    event_id: str
    relay: str
    accepted: bool
    message: str
    timestamp: float


@dataclass
class SubscriptionResult:
    """Result of a subscription query."""
    sub_id: str
    events: List[NostrEvent]
    eose_received: Dict[str, bool]  # relay -> received EOSE
    duration_seconds: float


class NostrClient:
    """
    Resilient Nostr client with relay pool, retry logic,
    subscription queue, and deduplication.
    """

    DEFAULT_RELAYS = [
        "wss://relay.damus.io",
        "wss://nos.lol",
        "wss://relay.nostr.band",
        "wss://relay.snort.social",
        "wss://nostr.wine",
    ]

    def __init__(self, private_key_hex: Optional[str] = None,
                 relays: Optional[List[str]] = None,
                 timeout: int = 10,
                 max_retries: int = 3):
        self.relays = relays or self.DEFAULT_RELAYS.copy()
        self.private_key = private_key_hex
        self.pubkey = self._derive_pubkey() if private_key_hex else None
        self._relay_connections: Dict[str, Any] = {}
        self._handlers: List[Callable] = []
        self._listen_tasks: Dict[str, asyncio.Task] = {}
        self.timeout = timeout
        self.max_retries = max_retries
        self._connected = False
        self._subscription_counter = 0
        # v2.2: Subscription event queues
        self._subscription_events: Dict[str, List[NostrEvent]] = defaultdict(list)
        self._subscription_eose: Dict[str, Set[str]] = defaultdict(set)
        self._subscription_locks: Dict[str, asyncio.Lock] = {}
        self._subscription_conditions: Dict[str, asyncio.Condition] = {}
        # v2.2: ACK tracking
        self._ack_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._ack_history: List[RelayAck] = []
        # v2.2: Deduplication
        self._seen_event_ids: Set[str] = set()

    def _derive_pubkey(self) -> str:
        """Derive public key from private key using secp256k1."""
        try:
            import secp256k1
            sk = secp256k1.PrivateKey(bytes.fromhex(self.private_key), raw=True)
            return sk.pubkey.serialize()[1:].hex()
        except Exception as e:
            raise ValueError(f"Invalid private key: {e}")

    def _sign_event(self, event: NostrEvent) -> str:
        """Sign event ID with Schnorr signature per NIP-01."""
        import secp256k1
        event_id = event.compute_id()
        sk = secp256k1.PrivateKey(bytes.fromhex(self.private_key), raw=True)
        sig = sk.schnorr_sign(bytes.fromhex(event_id), None, raw=True)
        return sig.hex()

    @property
    def connected(self) -> bool:
        return self._connected and len(self._relay_connections) > 0

    async def connect(self):
        """Connect to relays with retry and fallback logic."""
        try:
            import websockets
        except ImportError:
            raise ImportError("websockets>=12.0 required for Nostr connectivity")

        connected = []
        for relay in self.relays:
            for attempt in range(self.max_retries):
                try:
                    ws = await asyncio.wait_for(
                        websockets.connect(relay),
                        timeout=self.timeout
                    )
                    self._relay_connections[relay] = ws
                    logger.info(f"Connected to {relay} (attempt {attempt + 1})")
                    task = asyncio.create_task(self._listen(ws, relay))
                    self._listen_tasks[relay] = task
                    connected.append(relay)
                    break
                except Exception as e:
                    logger.warning(
                        f"Failed to connect to {relay} (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

        if not connected:
            raise ConnectionError("Failed to connect to any relay after retries")

        self._connected = True
        logger.info(f"Connected to {len(connected)}/{len(self.relays)} relays")

    async def disconnect(self):
        """Disconnect from all relays gracefully."""
        for relay, task in list(self._listen_tasks.items()):
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
        self._listen_tasks.clear()

        for relay, ws in list(self._relay_connections.items()):
            try:
                await ws.close()
            except Exception as e:
                logger.debug(f"Error closing {relay}: {e}")
        self._relay_connections.clear()
        self._connected = False
        logger.info("Disconnected from all relays")

    async def _listen(self, ws, relay: str):
        """Listen for incoming events with auto-reconnect and subscription tracking."""
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    if len(data) >= 3 and data[0] == "EVENT":
                        sub_id = data[1]
                        event_data = data[2]
                        event = NostrEvent.from_dict(event_data)

                        # Deduplication
                        if event.id in self._seen_event_ids:
                            continue
                        self._seen_event_ids.add(event.id)

                        # Store in subscription queue
                        if sub_id in self._subscription_events:
                            self._subscription_events[sub_id].append(event)
                            async with self._subscription_conditions[sub_id]:
                                self._subscription_conditions[sub_id].notify_all()

                        # ACK tracking
                        if event.id in self._ack_callbacks:
                            for cb in self._ack_callbacks[event.id]:
                                try:
                                    if asyncio.iscoroutinefunction(cb):
                                        await cb(event, relay)
                                    else:
                                        cb(event, relay)
                                except Exception:
                                    pass

                        # User handlers
                        for handler in self._handlers:
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(event, relay)
                                else:
                                    handler(event, relay)
                            except Exception as e:
                                logger.debug(f"Handler error: {e}")

                    elif len(data) >= 2 and data[0] == "EOSE":
                        sub_id = data[1]
                        logger.debug(f"EOSE received from {relay} for {sub_id}")
                        if sub_id in self._subscription_eose:
                            self._subscription_eose[sub_id].add(relay)
                            async with self._subscription_conditions[sub_id]:
                                self._subscription_conditions[sub_id].notify_all()

                    elif len(data) >= 4 and data[0] == "OK":
                        event_id = data[1]
                        accepted = data[2]
                        msg = data[3] if len(data) > 3 else ""
                        ack = RelayAck(
                            event_id=event_id,
                            relay=relay,
                            accepted=accepted,
                            message=msg,
                            timestamp=time.time(),
                        )
                        self._ack_history.append(ack)
                        logger.debug(f"ACK from {relay}: event={event_id[:16]}... accepted={accepted}")

                    elif len(data) >= 2 and data[0] == "NOTICE":
                        logger.warning(f"NOTICE from {relay}: {data[1]}")

                except Exception as e:
                    logger.debug(f"Error processing message from {relay}: {e}")
        except Exception as e:
            logger.warning(f"Listener error on {relay}: {e}")
        finally:
            if relay in self._relay_connections:
                del self._relay_connections[relay]
                if self._connected:
                    for attempt in range(self.max_retries):
                        try:
                            await asyncio.sleep(2 ** attempt)
                            import websockets
                            ws_new = await asyncio.wait_for(
                                websockets.connect(relay),
                                timeout=self.timeout
                            )
                            self._relay_connections[relay] = ws_new
                            logger.info(f"Reconnected to {relay}")
                            task = asyncio.create_task(self._listen(ws_new, relay))
                            self._listen_tasks[relay] = task
                            break
                        except Exception as e2:
                            logger.warning(f"Reconnection to {relay} failed (attempt {attempt + 1}): {e2}")

    def on_event(self, handler: Callable):
        """Register event handler."""
        self._handlers.append(handler)
        return handler

    def on_ack(self, event_id: str, callback: Callable):
        """Register ACK callback for a specific event_id."""
        self._ack_callbacks[event_id].append(callback)

    def get_acks(self, event_id: str) -> List[RelayAck]:
        """Get all ACKs received for an event."""
        return [ack for ack in self._ack_history if ack.event_id == event_id]

    async def publish_event(self, kind: int, content: str,
                           tags: Optional[List[List[str]]] = None,
                           wait_for_acks: bool = False,
                           ack_timeout: float = 5.0) -> Optional[str]:
        """
        Publish event to all connected relays with retry and optional ACK wait.

        Args:
            wait_for_acks: If True, wait for OK responses from relays
            ack_timeout: Max seconds to wait for ACKs
        """
        if not self.private_key:
            raise ValueError("Private key required to publish")

        tags = tags or []
        event = NostrEvent(
            id="", pubkey=self.pubkey, created_at=int(time.time()),
            kind=kind, tags=tags, content=content, sig=""
        )
        event.id = event.compute_id()
        event.sig = self._sign_event(event)
        message = ["EVENT", event.to_dict()]

        success_count = 0
        for relay, ws in list(self._relay_connections.items()):
            for attempt in range(self.max_retries):
                try:
                    await asyncio.wait_for(
                        ws.send(json.dumps(message)),
                        timeout=self.timeout
                    )
                    success_count += 1
                    break
                except Exception as e:
                    logger.warning(f"Failed to publish to {relay} (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1)

        logger.info(f"Published to {success_count}/{len(self._relay_connections)} relays")

        if wait_for_acks and success_count > 0:
            start = time.time()
            while time.time() - start < ack_timeout:
                acks = self.get_acks(event.id)
                if len(acks) >= min(success_count, len(self._relay_connections)):
                    break
                await asyncio.sleep(0.5)

        return event.id if success_count > 0 else None

    async def query_events(self, kinds: List[int],
                           authors: Optional[List[str]] = None,
                           limit: int = 100,
                           since: Optional[int] = None,
                           until: Optional[int] = None,
                           wait_for_eose: bool = True,
                           eose_timeout: float = 5.0) -> SubscriptionResult:
        """
        Query events from all connected relays.

        v2.2: Now actually collects events via subscription queue.
        Waits for EOSE (End of Stored Events) from all relays or timeout.

        Args:
            kinds: Event kinds to query
            authors: Optional list of author pubkeys
            limit: Max events per relay
            since: Unix timestamp for historical sync
            until: Unix timestamp for historical sync
            wait_for_eose: Wait for EOSE before returning
            eose_timeout: Max seconds to wait for EOSE
        """
        self._subscription_counter += 1
        sub_id = f"stegstr_query_{self._subscription_counter}_{int(time.time())}"
        filters = {"kinds": kinds, "limit": limit}
        if authors:
            filters["authors"] = authors
        if since:
            filters["since"] = since
        if until:
            filters["until"] = until

        message = ["REQ", sub_id, filters]

        # Initialize subscription state
        self._subscription_events[sub_id] = []
        self._subscription_eose[sub_id] = set()
        self._subscription_conditions[sub_id] = asyncio.Condition()

        start_time = time.time()

        # Send REQ to all relays
        for relay, ws in list(self._relay_connections.items()):
            try:
                await asyncio.wait_for(
                    ws.send(json.dumps(message)),
                    timeout=self.timeout
                )
                logger.debug(f"Sent REQ {sub_id} to {relay}")
            except Exception as e:
                logger.warning(f"Query failed on {relay}: {e}")

        if wait_for_eose:
            # Wait for EOSE from all connected relays or timeout
            expected_relays = set(self._relay_connections.keys())
            async with self._subscription_conditions[sub_id]:
                deadline = time.time() + eose_timeout
                while time.time() < deadline:
                    received = self._subscription_eose[sub_id]
                    if received >= expected_relays:
                        break
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        break
                    try:
                        await asyncio.wait_for(
                            self._subscription_conditions[sub_id].wait(),
                            timeout=min(remaining, 1.0)
                        )
                    except asyncio.TimeoutError:
                        pass

        # Also wait a brief moment for any trailing events
        await asyncio.sleep(0.5)

        events = self._subscription_events.get(sub_id, [])
        eose = self._subscription_eose.get(sub_id, set())

        # Clean up subscription state
        self._subscription_events.pop(sub_id, None)
        self._subscription_eose.pop(sub_id, None)
        self._subscription_conditions.pop(sub_id, None)

        # Close subscription
        await self.close_subscription(sub_id)

        duration = time.time() - start_time
        logger.info(f"Query {sub_id}: collected {len(events)} events from {len(eose)} relays in {duration:.1f}s")

        return SubscriptionResult(
            sub_id=sub_id,
            events=events,
            eose_received={r: (r in eose) for r in self.relays},
            duration_seconds=duration,
        )

    async def close_subscription(self, sub_id: str):
        """Close a subscription by ID."""
        message = ["CLOSE", sub_id]
        for relay, ws in list(self._relay_connections.items()):
            try:
                await asyncio.wait_for(ws.send(json.dumps(message)), timeout=self.timeout)
            except Exception as e:
                logger.debug(f"Error closing subscription on {relay}: {e}")

    async def sync_historical(self, kinds: List[int],
                               authors: Optional[List[str]] = None,
                               days_back: int = 7,
                               batch_size: int = 500) -> List[NostrEvent]:
        """
        Synchronize historical events from all relays.

        Fetches events in time-windowed batches to avoid overwhelming relays.
        """
        all_events = []
        now = int(time.time())
        window = 86400  # 1 day

        for day_offset in range(days_back):
            until = now - (day_offset * window)
            since = until - window

            result = await self.query_events(
                kinds=kinds,
                authors=authors,
                limit=batch_size,
                since=since,
                until=until,
                wait_for_eose=True,
                eose_timeout=10.0,
            )
            all_events.extend(result.events)
            logger.info(f"Synced day {day_offset + 1}/{days_back}: {len(result.events)} events")

        # Deduplicate
        seen = set()
        unique = []
        for e in all_events:
            if e.id not in seen:
                seen.add(e.id)
                unique.append(e)
        return unique

    async def upload_image_nip96(self, image_path: str,
                                  server_url: str = "https://nostr.build") -> Optional[str]:
        """Upload image via NIP-96 with integrity hash in metadata."""
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required for NIP-96 uploads")
            return None

        sha256_hash = self._compute_file_hash(image_path)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{server_url}/.well-known/nostr/nip96.json",
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        return None
                    config = await resp.json()
                    api_url = config.get("api_url", server_url)
            except Exception as e:
                logger.warning(f"NIP-96 discovery failed: {e}")
                api_url = server_url

            headers = {}
            if self.pubkey:
                auth_event = NostrEvent(
                    id="", pubkey=self.pubkey, created_at=int(time.time()),
                    kind=27235, tags=[["u", api_url], ["method", "POST"]],
                    content="", sig=""
                )
                auth_event.id = auth_event.compute_id()
                auth_event.sig = self._sign_event(auth_event)
                auth_token = base64.b64encode(
                    json.dumps(auth_event.to_dict()).encode()
                ).decode()
                headers["Authorization"] = f"Nostr {auth_token}"

            try:
                with open(image_path, "rb") as f:
                    data = aiohttp.FormData()
                    data.add_field("file", f, filename=image_path.split("/")[-1])

                    async with session.post(
                        api_url, data=data, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=120)
                    ) as resp:
                        if resp.status in (200, 201):
                            result = await resp.json()
                            if result.get("status") == "success":
                                nip94 = result.get("nip94_event", {})
                                url = None
                                for tag in nip94.get("tags", []):
                                    if len(tag) >= 2 and tag[0] == "url":
                                        url = tag[1]
                                logger.info(f"Uploaded image SHA-256: {sha256_hash}")
                                return url
            except Exception as e:
                logger.error(f"NIP-96 upload failed: {e}")

        return None

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file for integrity verification."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def verify_image_integrity(self, image_url: str, expected_hash: str) -> bool:
        """Download and verify image integrity against expected SHA-256 hash."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.read()
                    actual_hash = hashlib.sha256(data).hexdigest()
                    return actual_hash == expected_hash
        except Exception as e:
            logger.error(f"Integrity verification failed: {e}")
            return False

    async def publish_stegstr_post(self, image_url: str,
                                    message_preview: str = "",
                                    platform_hint: str = "",
                                    image_path: Optional[str] = None,
                                    wait_for_acks: bool = False) -> Optional[str]:
        """Publish a Stegstr post with integrity hash in metadata."""
        tags = [
            ["imeta", "url", image_url, "m", "image/png"],
            ["t", "stegstr"],
        ]
        if platform_hint:
            tags.append(["platform", platform_hint])

        if image_path:
            sha256_hash = self._compute_file_hash(image_path)
            tags.append(["x", sha256_hash])

        content = f"{message_preview}\n{image_url}" if message_preview else image_url
        return await self.publish_event(kind=1, content=content, tags=tags,
                                          wait_for_acks=wait_for_acks)

    async def verify_nip05(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Verify NIP-05 identifier (name@domain). Returns pubkey or None."""
        try:
            import aiohttp
            if "@" not in identifier:
                return None
            name, domain = identifier.split("@", 1)
            url = f"https://{domain}/.well-known/nostr.json?name={name}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        names = data.get("names", {})
                        return {"pubkey": names.get(name), "nip05": identifier}
        except Exception as e:
            logger.debug(f"NIP-05 verification failed: {e}")
        return None
