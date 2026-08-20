#!/usr/bin/env python3
"""
Real-World Benchmark for Stegstr v2.1.5

Cross-platform benchmark with dataset generation, statistical intervals,
and survival rate analysis.

Usage:
    python benchmarks/real_benchmark.py --dataset benchmarks/dataset --output report.json
    python benchmarks/real_benchmark.py --quick
"""
import argparse
import json
import sys
import tempfile
import time
import os
from pathlib import Path
from datetime import datetime

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.real_world_validator import RealWorldValidator


def create_test_cover(output_path: str, size: int = 1024):
    """Generate a random RGB cover image for testing."""
    arr = np.random.randint(0, 256, (size, size, 3), dtype=np.uint8)
    Image.fromarray(arr).save(output_path, "PNG")


def main():
    parser = argparse.ArgumentParser(
        description="Stegstr Real-World Benchmark v2.1.5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --quick
  %(prog)s --dataset benchmarks/dataset --output report.json
  %(prog)s --platforms telegram,imgur --modes GHOST,ARMOR
        """,
    )
    parser.add_argument("--dataset", help="Path to dataset directory")
    parser.add_argument("--output", default="benchmarks/report.json", help="JSON output path")
    parser.add_argument("--csv", default=None, help="CSV output path")
    parser.add_argument("--message", default="Stegstr benchmark message v2.1.5", help="Test message")
    parser.add_argument("--password", default="benchmark")
    parser.add_argument("--platforms", default=None, help="Comma-separated platforms")
    parser.add_argument("--modes", default=None, help="Comma-separated modes: GHOST,PHANTOM,ARMOR,FORTRESS,HYBRID")
    parser.add_argument("--quick", action="store_true", help="Quick mode: fewer platforms/modes")
    args = parser.parse_args()

    cover_path = args.dataset
    if not cover_path or not os.path.exists(cover_path):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            cover_path = f.name
            create_test_cover(cover_path)

    validator = RealWorldValidator(password=args.password)

    # Filter platforms
    if args.platforms:
        wanted = {p.strip().lower() for p in args.platforms.split(",")}
        validator.adapters = [a for a in validator.adapters if a.platform_name() in wanted]

    mode_map = {
        "GHOST": StegoMode.GHOST,
        "PHANTOM": StegoMode.PHANTOM,
        "ARMOR": StegoMode.ARMOR,
        "FORTRESS": StegoMode.FORTRESS,
        "HYBRID": StegoMode.HYBRID,
    }
    modes = None
    if args.modes:
        modes = [mode_map[m.strip().upper()] for m in args.modes.split(",") if m.strip().upper() in mode_map]

    if args.quick:
        # Limit to first 2 adapters and 2 modes
        validator.adapters = validator.adapters[:2]
        modes = [StegoMode.GHOST, StegoMode.ARMOR]

    print(f"\n{'='*60}")
    print("Stegstr Real-World Benchmark v2.1.5")
    print(f"{'='*60}")
    print(f"Cover: {cover_path}")
    print(f"Message: {args.message} ({len(args.message.encode('utf-8'))} bytes)")
    print(f"Platforms: {', '.join(a.platform_name() for a in validator.adapters) or 'None'}")
    print(f"Modes: {', '.join(m.name for m in modes) if modes else 'All'}")
    print(f"{'='*60}\n")

    report = validator.run_full_benchmark(cover_path, args.message, modes=modes)

    # Save JSON
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report.to_json())

    # Save CSV if requested
    if args.csv:
        os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
        with open(args.csv, "w", encoding="utf-8") as f:
            f.write(report.to_csv())
        print(f"CSV report saved to: {args.csv}")

    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    for r in report.results:
        status = "✓ SURVIVED" if r.message_match else "✗ LOST"
        print(f"  {status:12} {r.platform:12} / {r.mode:10} | PSNR={r.psnr_db:6.1f}dB | {r.error or 'OK'}")

    s = report.summary
    print(f"\n{'='*60}")
    print("OVERALL")
    print(f"{'='*60}")
    print(f"  Total tests: {s.get('total_tests', 0)}")
    print(f"  Survived: {s.get('survived', 0)}")
    print(f"  Failed: {s.get('failed', 0)}")
    print(f"  Best platform: {s.get('best_platform') or 'N/A'}")
    print(f"  Best mode: {s.get('best_mode') or 'N/A'}")
    print(f"  Survival rate: {report.survival_rate()*100:.1f}%")
    print(f"{'='*60}")
    print(f"\nJSON report saved to: {args.output}")

    sys.exit(0 if s.get("failed", 0) == 0 else 1)


if __name__ == "__main__":
    main()
