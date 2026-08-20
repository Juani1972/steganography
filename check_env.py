#!/usr/bin/env python3
"""
Stegstr Environment Checker — Verifies all dependencies are installed and functional.

Run this before the competition to ensure your environment is fully configured.
"""

import sys
import importlib
from typing import Dict, List, Tuple

def check_dependency(module_name: str, package_name: str = None, critical: bool = True) -> Tuple[bool, str]:
    pkg = package_name or module_name
    try:
        mod = importlib.import_module(module_name)
        version = getattr(mod, "__version__", "unknown")
        return True, f"{pkg} ({version})"
    except ImportError:
        return False, f"{pkg} MISSING"

def check_reedsolo_functional() -> Tuple[bool, str]:
    """Verify reedsolo can actually encode/decode data."""
    try:
        from reedsolo import RSCodec
        rsc = RSCodec(nsym=32, nsize=255)
        data = b"Stegstr test data for Reed-Solomon validation"
        encoded = rsc.encode(data)
        decoded = rsc.decode(encoded)[0]
        if decoded == data:
            return True, "reedsolo (functional, encode/decode OK)"
        return False, "reedsolo (installed but decode mismatch)"
    except Exception as e:
        return False, f"reedsolo (installed but broken: {e})"

def check_argon2_functional() -> Tuple[bool, str]:
    """Verify argon2 can derive keys."""
    try:
        from argon2.low_level import hash_secret_raw, Type
        key = hash_secret_raw(
            secret=b"test", salt=b"1234567890123456",
            time_cost=3, memory_cost=65536, parallelism=4,
            hash_len=32, type=Type.ID,
        )
        if len(key) == 32:
            return True, "argon2-cffi (functional, key derivation OK)"
        return False, "argon2-cffi (installed but wrong key length)"
    except Exception as e:
        return False, f"argon2-cffi (installed but broken: {e})"

def check_secp256k1_functional() -> Tuple[bool, str]:
    """Verify secp256k1 can sign/verify."""
    try:
        import secp256k1
        sk = secp256k1.PrivateKey()
        msg = hashlib.sha256(b"test").digest()
        sig = sk.schnorr_sign(msg, None, raw=True)
        pk = sk.pubkey
        if pk.schnorr_verify(msg, sig, None, raw=True):
            return True, "secp256k1 (functional, sign/verify OK)"
        return False, "secp256k1 (installed but verify failed)"
    except Exception as e:
        return False, f"secp256k1 (installed but broken: {e})"

def main():
    print("=" * 60)
    print("Stegstr Next — Environment Check")
    print("=" * 60)

    core_deps = [
        ("numpy", "numpy"),
        ("PIL", "pillow"),
        ("scipy", "scipy"),
        ("click", "click"),
        ("rich", "rich"),
        ("cryptography", "cryptography"),
    ]

    stego_deps = [
        ("reedsolo", "reedsolo"),
        ("cv2", "opencv-python"),
        ("skimage", "scikit-image"),
    ]

    network_deps = [
        ("websockets", "websockets"),
        ("aiohttp", "aiohttp"),
        ("secp256k1", "secp256k1"),
    ]

    optional_deps = [
        ("nacl", "pynacl"),
        ("bech32", "bech32"),
        ("qrcode", "qrcode"),
        ("pytest", "pytest"),
        ("hypothesis", "hypothesis"),
    ]

    all_ok = True

    def check_group(name: str, deps: List[Tuple[str, str]], critical: bool = True):
        nonlocal all_ok
        print(f"\n{name}:")
        print("-" * 40)
        for mod_name, pkg_name in deps:
            ok, msg = check_dependency(mod_name, pkg_name, critical)
            status = "✅" if ok else "❌"
            if not ok and critical:
                all_ok = False
            print(f"  {status} {msg}")

    check_group("Core Dependencies", core_deps, critical=True)
    check_group("Steganography Dependencies", stego_deps, critical=True)
    check_group("Network Dependencies", network_deps, critical=True)
    check_group("Optional Dependencies", optional_deps, critical=False)

    # Functional checks
    print(f"\nFunctional Checks:")
    print("-" * 40)

    ok, msg = check_reedsolo_functional()
    status = "✅" if ok else "❌"
    print(f"  {status} {msg}")
    if not ok:
        all_ok = False

    ok, msg = check_argon2_functional()
    status = "✅" if ok else "❌"
    print(f"  {status} {msg}")
    if not ok:
        all_ok = False

    ok, msg = check_secp256k1_functional()
    status = "✅" if ok else "❌"
    print(f"  {status} {msg}")
    if not ok:
        all_ok = False

    print(f"\nPython Version:")
    print("-" * 40)
    py_version = sys.version_info
    py_ok = py_version >= (3, 9)
    status = "✅" if py_ok else "❌"
    if not py_ok:
        all_ok = False
    print(f"  {status} Python {py_version.major}.{py_version.minor}.{py_version.micro}")

    print("\n" + "=" * 60)
    if all_ok:
        print("✅ ALL CRITICAL DEPENDENCIES FUNCTIONAL — Ready for competition!")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME CRITICAL DEPENDENCIES MISSING OR BROKEN")
        print("  Install with: pip install -r requirements.txt")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    import hashlib
    sys.exit(main())
