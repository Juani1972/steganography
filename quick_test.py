#!/usr/bin/env python3
"""
Stegstr v2.1.3 Quick Test — Verifica entorno + roundtrip básico
"""

import sys
import importlib

CORE_REQUIRED = {
    "numpy": "numpy",
    "PIL": "pillow",
    "cryptography": "cryptography",
    "argon2": "argon2-cffi",
}

FULL_REQUIRED = {
    "reedsolo": "reedsolo",
}

def check_env():
    print("Checking environment...")
    missing_core = []
    for module, package in CORE_REQUIRED.items():
        try:
            importlib.import_module(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package}")
            missing_core.append(package)

    missing_full = []
    for module, package in FULL_REQUIRED.items():
        try:
            importlib.import_module(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (optional — ARMOR/FORTRESS/HYBRID will be skipped)")
            missing_full.append(package)

    if missing_core:
        print(f"\nInstall core missing: pip install {' '.join(missing_core)}")
        sys.exit(1)
    print()

def test_mode(mode_name, engine_class, mode_enum):
    import tempfile
    import os
    import numpy as np
    from PIL import Image

    print(f"  {mode_name:10} : ", end="", flush=True)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            cover = os.path.join(tmpdir, "cover.png")
            stego = os.path.join(tmpdir, "stego.png")
            # Crear imagen RGB ruidosa
            arr = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
            Image.fromarray(arr).save(cover)

            msg = f"Test-{mode_name}-v2.1.3"
            eng = engine_class(mode=mode_enum, password="quicktest")
            eng.embed(cover, msg, stego, mode=mode_enum)
            result = eng.extract(stego, expected_mode=mode_enum)

            if result and result.get("message") == msg:
                print("PASS")
                return True
            else:
                print(f"FAIL (got {result})")
                return False
    except Exception as e:
        print(f"FAIL ({e})")
        return False

def main():
    check_env()

    from stegstr.stego.engine import StegoEngine, StegoMode

    print("Stegstr v2.1.3 Quick Test")
    print("=" * 42)

    results = {
        "GHOST": test_mode("GHOST", StegoEngine, StegoMode.GHOST),
        "PHANTOM": test_mode("PHANTOM", StegoEngine, StegoMode.PHANTOM),
    }

    # ARMOR/FORTRESS require reedsolo
    try:
        importlib.import_module("reedsolo")
        results["ARMOR"] = test_mode("ARMOR", StegoEngine, StegoMode.ARMOR)
        results["FORTRESS"] = test_mode("FORTRESS", StegoEngine, StegoMode.FORTRESS)
    except ImportError:
        print("  ARMOR     : SKIP (reedsolo not installed)")
        print("  FORTRESS  : SKIP (reedsolo not installed)")

    print("=" * 42)
    passed = sum(results.values())
    total = len(results)
    print(f"Result: {passed}/{total} passed")

    if passed < total:
        sys.exit(1)
    print("\nAll quick tests passed. Run pytest for full validation.")

if __name__ == "__main__":
    main()
