#!/usr/bin/env python3
"""
Real-World Benchmark Script v2.2 — Reproducible Platform Validation

Usage:
    # List available platforms
    python scripts/real_world_benchmark.py --list

    # Single test
    python scripts/real_world_benchmark.py --message "Secret" --cover cover.png

    # Reproducible N-iteration benchmark
    python scripts/real_world_benchmark.py --message "Secret" --cover cover.png \
        --iterations 10 --seed 42 --output report.json --csv report.csv

    # Stress test
    python scripts/real_world_benchmark.py --stress --carriers 20 --messages 5 --seed 42

    # Regression check
    python scripts/real_world_benchmark.py --message "Secret" --cover cover.png \
        --baseline baseline.json

    # Specific platforms only
    python scripts/real_world_benchmark.py --platforms telegram,imgur --cover cover.png
"""

import argparse
import sys
import os
import json
import logging

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stegstr.platform.real_world_validator import RealWorldValidator
from stegstr.stego.engine import StegoMode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("real_world_benchmark")


def parse_modes(mode_str: str):
    """Parse comma-separated mode names."""
    if not mode_str:
        return None
    mode_map = {
        "ghost": StegoMode.GHOST,
        "phantom": StegoMode.PHANTOM,
        "armor": StegoMode.ARMOR,
        "fortress": StegoMode.FORTRESS,
        "hybrid": StegoMode.HYBRID,
    }
    modes = []
    for m in mode_str.split(","):
        m = m.strip().lower()
        if m in mode_map:
            modes.append(mode_map[m])
        else:
            logger.warning(f"Unknown mode: {m}")
    return modes if modes else None


def main():
    parser = argparse.ArgumentParser(description="Stegstr Real-World Benchmark v2.2")
    parser.add_argument("--list", action="store_true", help="List available platforms")
    parser.add_argument("--message", default="Stegstr validation test message", help="Message to embed")
    parser.add_argument("--cover", default="samples/cover.png", help="Cover image path")
    parser.add_argument("--platforms", default="", help="Comma-separated platform names")
    parser.add_argument("--modes", default="", help="Comma-separated modes (ghost,phantom,armor,fortress,hybrid)")
    parser.add_argument("--iterations", type=int, default=1, help="Number of iterations")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", default="", help="JSON output file")
    parser.add_argument("--csv", default="", help="CSV output file")
    parser.add_argument("--stress", action="store_true", help="Run stress test")
    parser.add_argument("--carriers", type=int, default=20, help="Stress test carriers")
    parser.add_argument("--messages", type=int, default=5, help="Stress test messages")
    parser.add_argument("--baseline", default="", help="Baseline JSON for regression check")
    parser.add_argument("--password", default="benchmark", help="Stego password")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list:
        adapters = RealWorldValidator.list_available_adapters()
        print("\nAvailable platforms:")
        print("-" * 60)
        for a in adapters:
            status = "✅" if a["available"] else "❌"
            print(f"  {status} {a['name']:12} | {a['description']}")
            if not a["available"] and a["requires_credentials"]:
                print(f"      → Requires credentials")
        print()
        return

    # Validate cover image exists
    if not os.path.exists(args.cover):
        logger.error(f"Cover image not found: {args.cover}")
        sys.exit(1)

    modes = parse_modes(args.modes)

    # Build validator
    validator = RealWorldValidator(password=args.password)

    # Filter platforms if specified
    if args.platforms:
        wanted = set(p.strip() for p in args.platforms.split(","))
        validator.adapters = [a for a in validator.adapters if a.platform_name() in wanted]
        if not validator.adapters:
            logger.error(f"No adapters available for platforms: {args.platforms}")
            sys.exit(1)

    logger.info(f"Starting benchmark: cover={args.cover}, message_len={len(args.message)}")
    logger.info(f"Adapters: {[a.platform_name() for a in validator.adapters]}")
    logger.info(f"Modes: {[m.name for m in (modes or [])] or 'default'}")

    # Run benchmark
    if args.stress:
        logger.info(f"Running stress test: {args.carriers} carriers x {args.messages} messages")
        report = validator.run_stress_test(
            num_carriers=args.carriers,
            num_messages=args.messages,
            seed=args.seed,
            modes=modes,
        )
    elif args.iterations > 1 or args.seed is not None:
        logger.info(f"Running reproducible benchmark: {args.iterations} iterations, seed={args.seed}")
        report = validator.run_reproducible_benchmark(
            args.cover, args.message,
            iterations=args.iterations,
            seed=args.seed,
            modes=modes,
        )
    else:
        report = validator.run_full_benchmark(args.cover, args.message, modes=modes)

    # Print summary
    stats = report.aggregate_stats()
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total tests:      {stats.get('total_tests', 0)}")
    print(f"Survived:         {stats.get('survived', 0)}")
    print(f"Failed:           {stats.get('failed', 0)}")
    print(f"Survival rate:    {stats.get('overall_survival_rate', 0):.1%}")
    print(f"Mean PSNR:        {stats.get('mean_psnr_db', 0):.2f} dB")
    print(f"Mean BER:         {stats.get('mean_ber', 1.0):.4f}")
    print(f"Mean duration:    {stats.get('mean_duration_sec', 0):.2f} s")
    print(f"Best platform:    {stats.get('best_platform', 'N/A')}")
    print(f"Best mode:        {stats.get('best_mode', 'N/A')}")
    print("=" * 60)

    # Per-platform breakdown
    platforms = stats.get("platforms_tested", [])
    if platforms:
        print("\nPer-platform survival rates:")
        for p in platforms:
            rate = report.survival_rate(platform=p)
            best = report.best_mode_for_platform(p) or "N/A"
            print(f"  {p:12}: {rate:.1%} (best mode: {best})")

    # Combinaciones saltadas por dependencia opcional ausente (p.ej. reedsolo
    # para ARMOR/FORTRESS). Antes desaparecían sin explicación de `results`;
    # ahora se listan de forma explícita para no confundirlas con un fallo.
    if report.skipped:
        print(f"\n⚠️  {len(report.skipped)} combinación(es) saltada(s) por dependencia ausente:")
        for s in report.skipped:
            print(f"  - {s['platform']:12} / {s['mode']:10} | {s['reason']}")

    # Regression check
    if args.baseline and os.path.exists(args.baseline):
        reg = report.regression_check(args.baseline)
        print("\nRegression check:")
        print(f"  Baseline rate:  {reg.get('baseline_survival_rate', 0):.1%}")
        print(f"  Current rate:   {reg.get('current_survival_rate', 0):.1%}")
        if reg.get("regression"):
            print(f"  ⚠️  REGRESSION DETECTED: {reg['regression_delta']:+.1%}")
        else:
            print(f"  ✅ No regression: {reg.get('regression_delta', 0):+.1%}")

    # Save outputs
    if args.output:
        with open(args.output, "w") as f:
            f.write(report.to_json())
        logger.info(f"JSON report saved to {args.output}")

    if args.csv:
        with open(args.csv, "w") as f:
            f.write(report.to_csv())
        logger.info(f"CSV report saved to {args.csv}")

    # Exit with error code if survival rate is too low
    survival = stats.get("overall_survival_rate", 0)
    if survival < 0.5:
        logger.error(f"Low survival rate: {survival:.1%}")
        sys.exit(2)


if __name__ == "__main__":
    main()
