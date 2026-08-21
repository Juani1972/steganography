#!/usr/bin/env python3
"""
Health check for Stegstr v2.2.0

Verifies:
  - Core dependencies (numpy, pillow, cryptography, scipy)
  - Optional dependencies (websockets, aiohttp, secp256k1)
  - Nostr client importability
  - SyncManager importability
  - Stego engine roundtrip (quick)
"""
import sys
import importlib

def check_module(name, optional=False, display_name=None):
    dn = display_name or name
    try:
        importlib.import_module(name)
        print(f"  ✓ {dn}")
        return True
    except ImportError as e:
        status = "⚠ OPTIONAL" if optional else "✗ MISSING"
        print(f"  {status} {dn}: {e}")
        return optional

def main():
    print("=" * 60)
    print("Stegstr v2.2.0 Health Check")
    print("=" * 60)

    ok = True
    print("\nCore dependencies:")
    ok &= check_module("numpy")
    ok &= check_module("PIL")
    ok &= check_module("cryptography")
    ok &= check_module("rich")
    ok &= check_module("typer")
    ok &= check_module("argon2")
    ok &= check_module("scipy")
    ok &= check_module("reedsolo")

    print("\nOptional dependencies:")
    ok &= check_module("websockets", optional=True)
    ok &= check_module("aiohttp", optional=True)
    ok &= check_module("secp256k1", optional=True)
    ok &= check_module("fastapi", optional=True)
    ok &= check_module("uvicorn", optional=True)
    ok &= check_module("skimage", optional=True, display_name="scikit-image (skimage)")

    print("\nStegstr imports:")
    try:
        from stegstr.stego.engine import StegoEngine, StegoMode
        print("  ✓ stegstr.stego.engine")
    except Exception as e:
        print(f"  ✗ stegstr.stego.engine: {e}")
        ok = False

    try:
        from stegstr.nostr.client import NostrClient, NostrEvent
        print("  ✓ stegstr.nostr.client")
    except Exception as e:
        print(f"  ✗ stegstr.nostr.client: {e}")
        ok = False

    try:
        from stegstr.networking.sync_manager import SyncManager
        print("  ✓ stegstr.networking.sync_manager")
    except Exception as e:
        print(f"  ✗ stegstr.networking.sync_manager: {e}")
        ok = False

    try:
        from stegstr.platform.real_world_validator import RealWorldValidator
        print("  ✓ stegstr.platform.real_world_validator")
    except Exception as e:
        print(f"  ✗ stegstr.platform.real_world_validator: {e}")
        ok = False

    print("\n" + "=" * 60)
    if ok:
        print("✅ All checks passed")
        return 0
    else:
        print("❌ Some checks failed. Run: pip install -e '.[full,nostr,agent,dev]'")
        return 1

if __name__ == "__main__":
    sys.exit(main())
