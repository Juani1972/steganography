"""
Fuzzing tests for Stegstr v2.1.5

Property-based tests using Hypothesis (if available)
or manual fuzzing vectors.
"""
import pytest
import tempfile
import os
import numpy as np
from PIL import Image

from stegstr.stego.engine import StegoEngine, StegoMode


class TestFuzzing:
    @pytest.fixture
    def cover_image(self):
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "cover.png")
        img.save(path)
        return path

    def test_random_messages_roundtrip(self, cover_image):
        """Various message types must roundtrip correctly."""
        messages = [
            "",  # empty
            "a",  # single char
            "Hello World!",  # ASCII
            "Héllo Wörld 🌍",  # Unicode
            "x" * 1000,  # long ASCII
            "🔒" * 100,  # emoji heavy
        ]
        engine = StegoEngine(mode=StegoMode.GHOST)
        for msg in messages:
            with tempfile.TemporaryDirectory() as tmpdir:
                stego = os.path.join(tmpdir, "stego.png")
                engine.embed(cover_image, msg, stego)
                result = engine.extract(stego)
                assert result is not None, f"Extraction failed for message: {msg[:50]}"
                assert result["message"] == msg, f"Mismatch for message: {msg[:50]}"

    def test_binary_data_roundtrip(self, cover_image):
        """Binary data encoded as base64 must survive."""
        pytest.importorskip("reedsolo", reason="ARMOR usa ECC=48 por defecto (reedsolo)")
        import base64
        binary = bytes(range(256)) * 4
        b64_msg = base64.b64encode(binary).decode("ascii")
        engine = StegoEngine(mode=StegoMode.ARMOR)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover_image, b64_msg, stego)
            result = engine.extract(stego)
            assert result is not None
            assert result["message"] == b64_msg

    def test_special_characters(self, cover_image):
        """Messages with special/control characters."""
        msg = "\x00\x01\x02\x03\xff\xfe"
        engine = StegoEngine(mode=StegoMode.GHOST)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover_image, msg, stego)
            result = engine.extract(stego)
            assert result is not None
            assert result["message"] == msg
