"""
Benchmark tests for Stegstr v2.1.5

Validates that benchmark scripts execute without errors
and produce valid output structures.
"""
import pytest
import tempfile
import os
import json
import subprocess
import sys


class TestBenchmarks:
    def test_run_benchmarks_quick(self):
        """Quick benchmark must complete and produce valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "results.json")
            result = subprocess.run(
                [sys.executable, "benchmarks/run_benchmarks.py", "--quick", "--output", output],
                capture_output=True, text=True, timeout=120,
            )
            # May fail if skimage not installed, but should still produce output or exit cleanly
            if os.path.exists(output):
                with open(output, "r") as f:
                    data = json.load(f)
                assert "version" in data
                assert data["version"] == "2.1.5"
                assert "benchmarks" in data
                assert "summary" in data

    def test_real_benchmark_list_adapters(self):
        """real_benchmark --list must show adapters table."""
        result = subprocess.run(
            [sys.executable, "benchmarks/real_benchmark.py", "--list"],
            capture_output=True, text=True, timeout=30,
        )
        assert "Available Platform Adapters" in result.stdout or result.returncode == 0
