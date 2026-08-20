#!/usr/bin/env python3
"""Stegstr v2.1.3 Demo Script"""
import tempfile, os
import numpy as np
from PIL import Image
from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.simulator import PlatformSimulator

def main():
    print("=" * 60)
    print("Stegstr v2.1.3 Demo")
    print("=" * 60)
    arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    tmpdir = tempfile.mkdtemp()
    cover = os.path.join(tmpdir, "cover.png")
    Image.fromarray(arr).save(cover)
    msg = "This is a secret message for the demo!"
    for mode in [StegoMode.GHOST, StegoMode.ARMOR, StegoMode.FORTRESS, StegoMode.PHANTOM]:
        engine = StegoEngine(mode=mode)
        stego = os.path.join(tmpdir, f"{mode.name.lower()}.png")
        engine.embed(cover, msg, stego)
        result = engine.extract(stego)
        ok = result is not None and result["message"] == msg
        print(f"{mode.name:10s}: {'PASS' if ok else 'FAIL'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
