#!/usr/bin/env python3
"""
Basic usage examples for Stegstr v2.1.5

Demonstrates:
  - Simple embed/extract
  - Platform-specific embedding
  - Auto-tune
  - Nostr posting
"""
import os
import tempfile

from stegstr.stego.engine import StegoEngine, StegoMode


def example_1_basic():
    """Example 1: Simple embed and extract."""
    print("Example 1: Basic embed/extract")
    engine = StegoEngine(mode=StegoMode.ARMOR)
    with tempfile.TemporaryDirectory() as tmpdir:
        cover = os.path.join(tmpdir, "cover.png")
        stego = os.path.join(tmpdir, "stego.png")
        # Create a simple test cover
        import numpy as np
        from PIL import Image
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        Image.fromarray(arr).save(cover, "PNG")

        engine.embed(cover, "Hello, Stegstr!", stego)
        result = engine.extract(stego)
        assert result["message"] == "Hello, Stegstr!"
        print(f"  ✓ Message recovered: {result['message']}")


def example_2_platform():
    """Example 2: Platform-specific embedding."""
    print("\nExample 2: Platform-specific (WhatsApp)")
    engine = StegoEngine(mode=StegoMode.FORTRESS)
    with tempfile.TemporaryDirectory() as tmpdir:
        cover = os.path.join(tmpdir, "cover.png")
        stego = os.path.join(tmpdir, "stego.png")
        import numpy as np
        from PIL import Image
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        Image.fromarray(arr).save(cover, "PNG")

        meta = engine.embed(cover, "Secret for WhatsApp", stego, target_platform="whatsapp_standard")
        print(f"  ✓ Mode: {meta['mode']}, ECC: {meta['ecc_used']}, Delta: {meta['delta_used']}")


def example_3_auto_tune():
    """Example 3: Auto-tune parameters."""
    print("\nExample 3: Auto-tune")
    engine = StegoEngine()
    with tempfile.TemporaryDirectory() as tmpdir:
        cover = os.path.join(tmpdir, "cover.png")
        import numpy as np
        from PIL import Image
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        Image.fromarray(arr).save(cover, "PNG")

        result = engine.auto_tune(cover, "Auto-tuned message", "telegram_photo", search_depth="quick")
        print(f"  ✓ Best mode: {result['mode']}, Delta: {result['delta']:.2f}, ECC: {result['ecc']}")


def example_4_nostr():
    """Example 4: Nostr client initialization."""
    print("\nExample 4: Nostr client")
    try:
        from stegstr.nostr.client import NostrClient, NostrEvent
        client = NostrClient()
        print(f"  ✓ Default relays: {len(client.relays)}")
        event = NostrEvent(
            id="", pubkey="a" * 64, created_at=1234567890,
            kind=1, tags=[["t", "test"]], content="Hello Nostr", sig=""
        )
        print(f"  ✓ Event ID: {event.compute_id()[:16]}...")
    except ImportError as e:
        print(f"  ⚠ Nostr not available: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Stegstr v2.1.5 — Basic Usage Examples")
    print("=" * 60)
    example_1_basic()
    example_2_platform()
    example_3_auto_tune()
    example_4_nostr()
    print("\n✅ All examples completed")
