#!/usr/bin/env python3
"""
Setup script for contest dependencies.
Installs additional packages required for the contest submission
without modifying pyproject.toml.

Usage:
    python setup_contest_deps.py
"""

import subprocess
import sys

CONTEST_DEPENDENCIES = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "streamlit>=1.32.0",
    "httpx>=0.27.0",
    "websockets>=12.0",  # Already in [nostr], but ensure version
    "aiohttp>=3.9.0",    # Already in [nostr]
    "pydantic>=2.0.0",
]

def install():
    print("Installing Stegstr Contest dependencies...")
    print("=" * 60)

    for dep in CONTEST_DEPENDENCIES:
        print(f"\nInstalling {dep}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ All contest dependencies installed!")
    print("\nNext steps:")
    print("  1. Start API server:  python -m stegstr.api.server")
    print("  2. Start Web GUI:     streamlit run stegstr/gui/web_app.py")
    print("  3. Run tests:         pytest tests/test_real_world.py -v")

if __name__ == "__main__":
    install()
