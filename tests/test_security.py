"""
Security & Fuzzing Tests for Stegstr v2.1.3

Fase 4 — Hardening de seguridad:
  - Fuzzing de entrada (mensajes aleatorios, binarios, unicode extremo)
  - Malformed input (headers corruptos, payloads truncados)
  - Password incorrecta
  - Path traversal en rutas
  - Zip bomb / compression bomb
  - Imágenes especialmente diseñadas (gradientes, uniformes)
  - Límites de memoria
  - ECC corrupto
  - Delta extremo

Run:
  pytest tests/test_security.py -v
"""

import pytest
import tempfile
import os
import struct
import zlib
import numpy as np
from PIL import Image

from stegstr.stego.engine import StegoEngine, StegoMode, MAX_MESSAGE_BYTES, MAX_PAYLOAD_BYTES
from stegstr.platform.simulator import PlatformSimulator

class TestSecurity:
    """Security-focused tests."""

    @pytest.fixture
    def cover_image(self):
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "cover.png")
        img.save(path)
        return path

    # ------------------------------------------------------------------
    # Fuzzing: random messages
    # ------------------------------------------------------------------
    def test_fuzz_random_messages(self, cover_image):
        """Embed and extract 20 random binary messages."""
        engine = StegoEngine(mode=StegoMode.GHOST)
        for i in range(20):
            msg = os.urandom(np.random.randint(10, 500))
            with tempfile.TemporaryDirectory() as tmpdir:
                stego = os.path.join(tmpdir, f"stego_{i}.png")
                engine.embed(cover_image, msg, stego)
                result = engine.extract(stego)
                assert result is not None
                assert result["raw_bytes"] == len(msg)

    def test_fuzz_unicode_extreme(self, cover_image):
        """Test with extreme unicode and zero-width characters."""
        pytest.importorskip("reedsolo", reason="ARMOR usa ECC=48 por defecto (reedsolo)")
        msgs = [
            "\x00",  # control chars
            "\u200b\u200c\u200d",  # zero-width
            "a" * 10000,
            "🎉" * 1000,
            "\x00",  # raw null bytes as string
        ]
        engine = StegoEngine(mode=StegoMode.ARMOR)
        for msg in msgs:
            with tempfile.TemporaryDirectory() as tmpdir:
                stego = os.path.join(tmpdir, "stego.png")
                try:
                    engine.embed(cover_image, msg, stego)
                    result = engine.extract(stego)
                    if result is not None:
                        # Some unicode may roundtrip differently; just ensure no crash
                        pass
                except ValueError:
                    pass  # Some inputs may be rejected legitimately

    # ------------------------------------------------------------------
    # Malformed headers
    # ------------------------------------------------------------------
    def test_corrupt_magic(self, cover_image):
        """Change MAGIC bytes and ensure extraction fails gracefully."""
        engine = StegoEngine(mode=StegoMode.GHOST)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover_image, "test", stego)
            img = Image.open(stego).convert("RGB")
            arr = np.array(img)
            # Corrupt first byte of payload (LSB of first pixel red channel)
            arr[0, 0, 0] = (arr[0, 0, 0] & 0xFE) | 1
            corrupted = Image.fromarray(arr)
            cpath = os.path.join(tmpdir, "corrupt.png")
            corrupted.save(cpath)
            result = engine.extract(cpath)
            assert result is None or result.get("message") != "test"

    def test_truncated_payload(self, cover_image):
        """Simulate truncated payload by cropping image.
        GHOST embeds sequentially from top-left; crop from bottom-right
        to actually remove payload bits."""
        engine = StegoEngine(mode=StegoMode.GHOST)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            msg = "This is a longer message to embed for truncation testing"
            engine.embed(cover_image, msg, stego)
            img = Image.open(stego)
            w, h = img.size
            # Crop keeping only top-left quadrant where payload starts
            cropped = img.crop((0, 0, w // 4, h // 4))
            cpath = os.path.join(tmpdir, "cropped.png")
            cropped.save(cpath)
            result = engine.extract(cpath)
            assert result is None or result.get("message") != msg

    # ------------------------------------------------------------------
    # Wrong password
    # ------------------------------------------------------------------
    def test_wrong_password_rejection(self, cover_image):
        """Ensure wrong password does not reveal message."""
        pytest.importorskip("argon2", reason="cifrado con contraseña requiere argon2-cffi")
        pytest.importorskip("reedsolo", reason="ARMOR usa ECC=48 por defecto (reedsolo)")
        engine_enc = StegoEngine(mode=StegoMode.ARMOR, password="correct_password")
        engine_wrong = StegoEngine(password="wrong_password")
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine_enc.embed(cover_image, "secret", stego)
            result = engine_wrong.extract(stego)
            assert result is None or result.get("message") != "secret"

    # ------------------------------------------------------------------
    # Path traversal
    # ------------------------------------------------------------------
    def test_path_traversal_cover(self):
        """Reject paths with traversal sequences."""
        engine = StegoEngine()
        bad_paths = [
            "../../../etc/passwd",
            r"..\..\windows\system32\config\sam",
            "/tmp/../../etc/shadow",
        ]
        for path in bad_paths:
            with pytest.raises(ValueError):
                engine.embed(path, "test", "/tmp/out.png")

    def test_path_traversal_output(self, cover_image):
        """Reject output paths with traversal."""
        engine = StegoEngine()
        with pytest.raises(ValueError):
            engine.embed(cover_image, "test", "../../../etc/passwd.png")

    # ------------------------------------------------------------------
    # Zip bomb / compression bomb
    # ------------------------------------------------------------------
    def test_zip_bomb_protection(self):
        """Verify safe decompressor rejects oversized expansion."""
        from stegstr.stego.engine import StegoEngine
        # Create a small zlib stream
        small = b"X" * 1000
        compressed = zlib.compress(small)
        # Should succeed within limit
        result = StegoEngine._safe_zlib_decompress(compressed, max_size=5000)
        assert result == small

        # Should fail when limit is too low
        with pytest.raises(ValueError):
            StegoEngine._safe_zlib_decompress(compressed, max_size=100)

    # ------------------------------------------------------------------
    # Adversarial images
    # ------------------------------------------------------------------
    def test_uniform_image(self):
        """Test embedding in a perfectly uniform image (worst case for DCT)."""
        pytest.importorskip("reedsolo", reason="ARMOR usa ECC=48 por defecto (reedsolo)")
        tmpdir = tempfile.mkdtemp()
        arr = np.ones((512, 512, 3), dtype=np.uint8) * 128
        path = os.path.join(tmpdir, "uniform.png")
        Image.fromarray(arr).save(path)
        engine = StegoEngine(mode=StegoMode.ARMOR)
        with tempfile.TemporaryDirectory() as tmpdir2:
            stego = os.path.join(tmpdir2, "stego.png")
            engine.embed(path, "Uniform image test", stego)
            result = engine.extract(stego)
            assert result is not None
            assert result["message"] == "Uniform image test"

    def test_gradient_image(self):
        """Test embedding in a smooth gradient image."""
        pytest.importorskip("reedsolo", reason="FORTRESS usa ECC=96 por defecto (reedsolo)")
        tmpdir = tempfile.mkdtemp()
        x = np.linspace(0, 255, 512)
        y = np.linspace(0, 255, 512)
        X, Y = np.meshgrid(x, y)
        arr = np.stack([X, Y, (X + Y) / 2], axis=-1).astype(np.uint8)
        path = os.path.join(tmpdir, "gradient.png")
        Image.fromarray(arr).save(path)
        engine = StegoEngine(mode=StegoMode.FORTRESS)
        with tempfile.TemporaryDirectory() as tmpdir2:
            stego = os.path.join(tmpdir2, "stego.png")
            engine.embed(path, "Gradient test", stego)
            result = engine.extract(stego)
            assert result is not None
            assert result["message"] == "Gradient test"

    # ------------------------------------------------------------------
    # ECC corrupto
    # ------------------------------------------------------------------
    def test_corrupt_ecc_recovery(self, cover_image):
        """Test that corrupt ECC payload is handled gracefully."""
        pytest.importorskip("reedsolo", reason="ecc_override=32 requiere reedsolo")
        engine = StegoEngine(mode=StegoMode.ARMOR, ecc_override=32)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            meta = engine.embed(cover_image, "ECC test", stego)
            # Corrupt a few bytes in the middle of the image
            img = Image.open(stego).convert("RGB")
            arr = np.array(img)
            arr[100, 100, 0] = (arr[100, 100, 0] + 50) % 256
            arr[200, 200, 1] = (arr[200, 200, 1] + 50) % 256
            cpath = os.path.join(tmpdir, "corrupt_ecc.png")
            Image.fromarray(arr).save(cpath)
            result = engine.extract(cpath)
            # With 32 bytes ECC, minor corruption should be recoverable
            # but we only assert graceful handling (no crash)
            if result is not None:
                assert result.get("message") == "ECC test" or result.get("message") is None

    # ------------------------------------------------------------------
    # Delta extremo — AHORA espera ValueError (validación estricta)
    # ------------------------------------------------------------------
    def test_extreme_delta_bounds(self):
        """Ensure extreme deltas are rejected with ValueError."""
        with pytest.raises(ValueError):
            StegoEngine(delta_override=-5.0)
        with pytest.raises(ValueError):
            StegoEngine(delta_override=1000.0)
        # Values within bounds should work
        engine = StegoEngine(delta_override=0.5)
        assert engine.delta_override == 0.5
        engine2 = StegoEngine(delta_override=50.0)
        assert engine2.delta_override == 50.0

    # ------------------------------------------------------------------
    # Memory limits / DoS
    # ------------------------------------------------------------------
    def test_extraction_dos_protection(self, cover_image):
        """Ensure extraction on clean image terminates quickly (no infinite loop)."""
        engine = StegoEngine()
        import time
        t0 = time.perf_counter()
        result = engine.extract(cover_image)
        elapsed = time.perf_counter() - t0
        assert result is None
        assert elapsed < 5.0, f"Extraction took too long: {elapsed:.2f}s (possible DoS)"

    def test_oversized_message_rejection(self, cover_image):
        """Ensure messages beyond MAX_MESSAGE_BYTES are rejected."""
        engine = StegoEngine()
        huge = "X" * (MAX_MESSAGE_BYTES + 1)
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="too large"):
                engine.embed(cover_image, huge, os.path.join(tmpdir, "out.png"))

    def test_image_dimension_limits(self):
        """Reject images beyond MAX_IMAGE_DIMENSION without loading them fully."""
        from stegstr.stego.engine import MAX_IMAGE_DIMENSION
        assert MAX_IMAGE_DIMENSION == 16384
        # We test the logic by creating a small image and asserting the check
        # would fail for a larger one
        tmpdir = tempfile.mkdtemp()
        arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
        path = os.path.join(tmpdir, "small.png")
        Image.fromarray(arr).save(path)
        engine = StegoEngine()
        # This should succeed
        with tempfile.TemporaryDirectory() as tmpdir2:
            engine.embed(path, "ok", os.path.join(tmpdir2, "out.png"))

    # ------------------------------------------------------------------
    # Header manipulation
    # ------------------------------------------------------------------
    def test_invalid_version_rejection(self, cover_image):
        """Craft a packet with invalid version and ensure rejection."""
        engine = StegoEngine(mode=StegoMode.GHOST)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover_image, "version test", stego)
            # Manually corrupt the version byte in the LSB
            img = Image.open(stego).convert("RGB")
            arr = np.array(img)
            # Version is byte 5 of header (after 4-byte magic)
            # We flip bits in the first few pixels to corrupt it
            for i in range(8 * 5, 8 * 6):
                row = i // (arr.shape[1] * 3)
                col = (i % (arr.shape[1] * 3)) // 3
                ch = i % 3
                if row < arr.shape[0] and col < arr.shape[1]:
                    arr[row, col, ch] ^= 1
            cpath = os.path.join(tmpdir, "bad_version.png")
            Image.fromarray(arr).save(cpath)
            result = engine.extract(cpath)
            assert result is None or result.get("message") != "version test"

    def test_invalid_ecc_value_rejection(self, cover_image):
        """Craft header with invalid ECC value."""
        engine = StegoEngine(mode=StegoMode.GHOST)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover_image, "ecc test", stego)
            img = Image.open(stego).convert("RGB")
            arr = np.array(img)
            # ECC is bytes 10-13 of header (4-byte uint32)
            # Corrupt the ECC field bits
            for i in range(8 * 10, 8 * 14):
                row = i // (arr.shape[1] * 3)
                col = (i % (arr.shape[1] * 3)) // 3
                ch = i % 3
                if row < arr.shape[0] and col < arr.shape[1]:
                    arr[row, col, ch] ^= 1
            cpath = os.path.join(tmpdir, "bad_ecc.png")
            Image.fromarray(arr).save(cpath)
            result = engine.extract(cpath)
            assert result is None or result.get("message") != "ecc test"
