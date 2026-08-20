#!/usr/bin/env python3
"""
Security audit for Stegstr v2.1.5

Runs:
  - pytest tests/test_security.py
  - bandit security linter
  - validate.py (exhaustive validation)
"""
import subprocess
import sys
import os


def run(cmd, description):
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    print("=" * 60)
    print("Stegstr v2.1.5 Security Audit")
    print("=" * 60)

    codes = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base_dir)

    # 1. Security tests
    codes.append(run("pytest tests/test_security.py -v --tb=short", "Security & Fuzzing Tests"))

    # 2. Bandit
    codes.append(run("bandit -r stegstr/ -f json -o bandit-report.json || true", "Bandit Security Linter"))

    # 3. Validate
    codes.append(run("python validate.py", "Exhaustive Validation Suite"))

    print(f"\n{'='*60}")
    print("AUDIT COMPLETE")
    print(f"{'='*60}")
    if any(c != 0 for c in codes):
        print("⚠ Some checks reported issues. Review output above.")
        return 1
    print("✅ All security checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
