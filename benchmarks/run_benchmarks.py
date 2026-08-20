#!/usr/bin/env python3
"""
Scientific benchmark suite for Stegstr v2.1.5

Metrics: BER, PSNR, SSIM, extraction time, memory usage.

Usage:
    python benchmarks/run_benchmarks.py --output benchmarks/results.json
    python benchmarks/run_benchmarks.py --quick
"""
import argparse
import json
import time
import tempfile
import os
import tracemalloc
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.simulator import PlatformSimulator


def create_cover(path: str, size: int = 512):
    arr = np.random.randint(0, 256, (size, size, 3), dtype=np.uint8)
    Image.fromarray(arr).save(path, "PNG")


def compute_psnr(img1_path: str, img2_path: str) -> float:
    try:
        from skimage.metrics import peak_signal_noise_ratio
        img1 = np.array(Image.open(img1_path).convert("RGB"), dtype=np.float32)
        img2 = np.array(Image.open(img2_path).convert("RGB"), dtype=np.float32)
        if img1.shape != img2.shape:
            img2 = np.array(Image.open(img2_path).convert("RGB").resize(
                (img1.shape[1], img1.shape[0]), Image.LANCZOS), dtype=np.float32)
        return float(peak_signal_noise_ratio(img1, img2, data_range=255))
    except Exception:
        return 0.0


def compute_ssim(img1_path: str, img2_path: str) -> float:
    try:
        from skimage.metrics import structural_similarity
        img1 = np.array(Image.open(img1_path).convert("RGB"), dtype=np.float32)
        img2 = np.array(Image.open(img2_path).convert("RGB"), dtype=np.float32)
        if img1.shape != img2.shape:
            img2 = np.array(Image.open(img2_path).convert("RGB").resize(
                (img1.shape[1], img1.shape[0]), Image.LANCZOS), dtype=np.float32)
        return float(structural_similarity(img1, img2, data_range=255, channel_axis=2))
    except Exception:
        return 0.0


def benchmark_mode(mode: StegoMode, message: str, platform: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        cover = os.path.join(tmpdir, "cover.png")
        stego = os.path.join(tmpdir, "stego.png")
        processed = os.path.join(tmpdir, "processed.jpg")
        create_cover(cover)

        engine = StegoEngine(mode=mode, password="bench")
        sim = PlatformSimulator()

        # Embed
        t0 = time.perf_counter()
        tracemalloc.start()
        meta = engine.embed(cover, message, stego, target_platform=platform)
        _, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        embed_time = time.perf_counter() - t0

        # Simulate platform
        sim.simulate(platform, stego, processed)

        # Extract
        t0 = time.perf_counter()
        result = engine.extract(processed, expected_mode=mode)
        extract_time = time.perf_counter() - t0

        # Metrics
        psnr_val = compute_psnr(cover, stego)
        ssim_val = compute_ssim(cover, stego)

        # BER (bit error rate between original and extracted message)
        ber = 0.0
        if result and result.get("message") == message:
            ber = 0.0
        elif result:
            orig_bits = np.unpackbits(np.frombuffer(message.encode("utf-8"), dtype=np.uint8))
            extr_bits = np.unpackbits(np.frombuffer(result.get("message", "").encode("utf-8"), dtype=np.uint8))
            min_len = min(len(orig_bits), len(extr_bits))
            if min_len > 0:
                errors = np.sum(orig_bits[:min_len] != extr_bits[:min_len])
                ber = float(errors / len(orig_bits))
            else:
                ber = 1.0
        else:
            ber = 1.0

        return {
            "mode": mode.name,
            "platform": platform,
            "message_length": len(message.encode("utf-8")),
            "embed_time_ms": round(embed_time * 1000, 2),
            "extract_time_ms": round(extract_time * 1000, 2),
            "peak_memory_mb": round(mem_peak / (1024 * 1024), 2),
            "psnr_db": round(psnr_val, 2),
            "ssim": round(ssim_val, 4),
            "ber": round(ber, 4),
            "survived": result is not None and result.get("message") == message,
            "ecc_used": meta.get("ecc_used", 0),
            "delta_used": meta.get("delta_used", 0.0),
        }


def main():
    parser = argparse.ArgumentParser(description="Stegstr Scientific Benchmark v2.1.5")
    parser.add_argument("--output", default="benchmarks/results.json", help="JSON output path")
    parser.add_argument("--quick", action="store_true", help="Quick mode")
    args = parser.parse_args()

    message = "Benchmark test message for steganographic evaluation across platforms."
    platforms = ["telegram_photo", "whatsapp_standard", "instagram"]
    modes = [StegoMode.GHOST, StegoMode.ARMOR, StegoMode.FORTRESS]

    if args.quick:
        platforms = platforms[:1]
        modes = modes[:2]

    results = []
    print(f"\n{'='*60}")
    print("Stegstr Scientific Benchmark v2.1.5")
    print(f"{'='*60}")

    for platform in platforms:
        for mode in modes:
            label = f"{mode.name} on {platform}"
            print(f"\nBenchmarking {label}...")
            try:
                r = benchmark_mode(mode, message, platform)
                results.append(r)
                status = "✓" if r["survived"] else "✗"
                print(f"  {status} PSNR={r['psnr_db']}dB SSIM={r['ssim']:.4f} BER={r['ber']:.4f} "
                      f"time={r['embed_time_ms']}ms mem={r['peak_memory_mb']}MB")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append({"mode": mode.name, "platform": platform, "error": str(e)})

    # Summary stats
    survived = sum(1 for r in results if r.get("survived"))
    total = len([r for r in results if "error" not in r])
    avg_psnr = sum(r.get("psnr_db", 0) for r in results if "error" not in r) / max(total, 1)
    avg_ssim = sum(r.get("ssim", 0) for r in results if "error" not in r) / max(total, 1)

    output = {
        "version": "2.1.5",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_tests": total,
            "survived": survived,
            "failed": total - survived,
            "survival_rate": round(survived / max(total, 1), 4),
            "avg_psnr_db": round(avg_psnr, 2),
            "avg_ssim": round(avg_ssim, 4),
        },
        "benchmarks": results,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Total: {total} | Survived: {survived} | Failed: {total - survived}")
    print(f"  Avg PSNR: {avg_psnr:.1f}dB | Avg SSIM: {avg_ssim:.4f}")
    print(f"  Results saved to: {args.output}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
