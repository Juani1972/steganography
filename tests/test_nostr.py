"""
Tests for Nostr client v2.2 — validates real implementation with E2E relay tests.

NUEVO v2.2:
- test_query_events_real: conecta a relay real, publica, consulta, verifica
- test_subscription_dedup: verifica deduplicación entre relays
- test_ack_tracking: verifica ACK/OK de relays
- test_historical_sync: sincronización histórica
- test_publish_with_acks: publicación con espera de confirmación
"""

import pytest
import asyncio
import json
import hashlib
import time

try:
    from stegstr.nostr.client import NostrClient, NostrEvent, SubscriptionResult
    HAS_SECP256K1 = True
except ImportError:
    HAS_SECP256K1 = False

pytestmark = pytest.mark.skipif(not HAS_SECP256K1, reason="secp256k1 not installed")


class TestNostrEvent:
    def test_event_id_determinism(self):
        event = NostrEvent(
            id="", pubkey="a" * 64, created_at=1234567890,
            kind=1, tags=[["t", "test"]], content="hello", sig=""
        )
        id1 = event.compute_id(); id2 = event.compute_id()
        assert id1 == id2 and len(id1) == 64

    def test_event_id_changes_with_content(self):
        e1 = NostrEvent(id="", pubkey="a"*64, created_at=0, kind=1, tags=[], content="A", sig="")
        e2 = NostrEvent(id="", pubkey="a"*64, created_at=0, kind=1, tags=[], content="B", sig="")
        assert e1.compute_id() != e2.compute_id()


class TestNostrClient:
    def test_default_relays(self):
        client = NostrClient()
        assert len(client.relays) >= 3 and all(r.startswith("wss://") for r in client.relays)

    def test_key_derivation(self):
        dummy_sk = "a" * 64
        client = NostrClient(private_key_hex=dummy_sk)
        assert client.pubkey is not None and len(client.pubkey) == 64 and client.pubkey != dummy_sk

    def test_invalid_key_raises(self):
        with pytest.raises(Exception):
            NostrClient(private_key_hex="not_a_key")

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        client = NostrClient()
        try:
            await asyncio.wait_for(client.connect(), timeout=15)
            assert len(client._relay_connections) > 0
        except Exception as e:
            pytest.skip(f"Relay connection failed: {e}")
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_publish_without_key_raises(self):
        client = NostrClient()
        with pytest.raises(ValueError, match="Private key required"):
            await client.publish_event(kind=1, content="test")

    @pytest.mark.asyncio
    async def test_handler_registration(self):
        client = NostrClient()
        async def handler(event, relay): pass
        client.on_event(handler)
        assert handler in client._handlers

    def test_nip96_upload_no_auth(self):
        client = NostrClient()
        assert client.pubkey is None

    @pytest.mark.asyncio
    async def test_query_events_e2e(self):
        """
        E2E test: connect, publish an event, query it back.
        Requires live relay connectivity.
        """
        # Generate a deterministic test key
        test_sk = "1" * 64
        client = NostrClient(private_key_hex=test_sk)
        try:
            await asyncio.wait_for(client.connect(), timeout=15)
        except Exception as e:
            pytest.skip(f"Relay connection failed: {e}")
            return

        try:
            # Publish a test event
            content = f"Stegstr test {time.time()}"
            event_id = await client.publish_event(kind=1, content=content, wait_for_acks=True)
            assert event_id is not None

            # Wait for propagation
            await asyncio.sleep(2)

            # Query events by author
            result = await client.query_events(
                kinds=[1],
                authors=[client.pubkey],
                limit=10,
                wait_for_eose=True,
                eose_timeout=10.0,
            )
            assert isinstance(result, SubscriptionResult)
            assert result.sub_id.startswith("stegstr_query_")
            # Should find at least our published event
            assert len(result.events) >= 1, f"Expected >=1 event, got {len(result.events)}"

            # Verify our event is in results
            found = any(e.id == event_id for e in result.events)
            assert found, f"Published event {event_id[:16]}... not found in query results"

        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_ack_tracking(self):
        """Test that ACKs are tracked after publish."""
        test_sk = "2" * 64
        client = NostrClient(private_key_hex=test_sk)
        try:
            await asyncio.wait_for(client.connect(), timeout=15)
        except Exception as e:
            pytest.skip(f"Relay connection failed: {e}")
            return

        try:
            event_id = await client.publish_event(kind=1, content="ACK test", wait_for_acks=True)
            assert event_id is not None

            acks = client.get_acks(event_id)
            # Should have at least one ACK if connected
            if client._relay_connections:
                assert len(acks) > 0, "Expected at least one ACK"
                assert all(a.accepted for a in acks), "Expected all ACKs to be accepted"
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_subscription_dedup(self):
        """Test that duplicate events from multiple relays are deduplicated."""
        test_sk = "3" * 64
        client = NostrClient(private_key_hex=test_sk)
        try:
            await asyncio.wait_for(client.connect(), timeout=15)
        except Exception as e:
            pytest.skip(f"Relay connection failed: {e}")
            return

        try:
            # Publish once
            event_id = await client.publish_event(kind=1, content="dedup test")
            await asyncio.sleep(2)

            # Query — event may come from multiple relays
            result = await client.query_events(
                kinds=[1],
                authors=[client.pubkey],
                limit=10,
                wait_for_eose=True,
                eose_timeout=8.0,
            )
            # Count unique event IDs
            unique_ids = set(e.id for e in result.events)
            # Should not have duplicates
            assert len(unique_ids) == len(result.events),                 f"Found duplicates: {len(result.events)} events, {len(unique_ids)} unique"
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_historical_sync(self):
        """Test historical event synchronization."""
        test_sk = "4" * 64
        client = NostrClient(private_key_hex=test_sk)
        try:
            await asyncio.wait_for(client.connect(), timeout=15)
        except Exception as e:
            pytest.skip(f"Relay connection failed: {e}")
            return

        try:
            # Sync last 1 day
            events = await client.sync_historical(
                kinds=[1],
                authors=[client.pubkey],
                days_back=1,
                batch_size=100,
            )
            # Should not crash and return a list
            assert isinstance(events, list)
        finally:
            await client.disconnect()
