#!/usr/bin/env python3
"""Analyze detectability of a stego image."""
import sys
from stegstr.analysis.steganalysis import StegAnalyzer

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python analyze_detectability.py <cover> <stego>")
        sys.exit(1)
    analyzer = StegAnalyzer()
    report = analyzer.compare(sys.argv[1], sys.argv[2])
    print(report)
