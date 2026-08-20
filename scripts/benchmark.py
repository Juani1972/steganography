#!/usr/bin/env python3
"""
Benchmark entry point for Stegstr v2.1.5

Delegates to the full benchmark suite.
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base_dir)
    sys.exit(subprocess.run([sys.executable, "benchmarks/run_benchmarks.py"] + sys.argv[1:]).returncode)
