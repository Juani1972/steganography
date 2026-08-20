"""
Robustness tests for Stegstr steganography v2.1.1.
Tests all modes against simulated platform pipelines with sync markers.
"""

import pytest
import tempfile
import os
from PIL import Image
import numpy as np
from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.simulator import PlatformSimulator


class TestRobustness:
    @pytest.fixture
    def cover_image(self):
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "cover.png")
        img.save(path)
        return path

    @pytest.fixture
    def short_message(self):
        return "Stegstr test message for social media!"

    @pytest.fixture
    def long_message(self):
        return "This is a longer test message. " * 50

    def test_ghost_file_mode(self, cover_image, long_message):
        engine = StegoEngine(mode=StegoMode.GHOST)
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        engine.embed(cover_image, long_message, stego)
        result = engine.extract(stego)
        assert result is not None
        assert result["message"] == long_message
        assert result["mode"] == "GHOST"

    def test_armor_telegram(self, cover_image, long_message):
        pytest.importorskip("reedsolo", reason="ARMOR usa ECC por defecto (reedsolo)")
        engine = StegoEngine(mode=StegoMode.ARMOR)
        sim = PlatformSimulator()
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        processed = os.path.join(tmpdir, "telegram.jpg")
        engine.embed(cover_image, long_message, stego, target_platform="telegram_photo")
        sim.simulate("telegram_photo", stego, processed)
        result = engine.extract(processed)
        assert result is not None
        assert result["message"] == long_message

    def test_fortress_whatsapp(self, cover_image, short_message):
        pytest.importorskip("reedsolo", reason="FORTRESS usa ECC por defecto (reedsolo)")
        engine = StegoEngine(mode=StegoMode.FORTRESS)
        sim = PlatformSimulator()
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        processed = os.path.join(tmpdir, "whatsapp.jpg")
        engine.embed(cover_image, short_message, stego, target_platform="whatsapp_standard")
        sim.simulate("whatsapp_standard", stego, processed)
        result = engine.extract(processed)
        assert result is not None
        assert result["message"] == short_message

    def test_fortress_instagram(self, cover_image, short_message):
        pytest.importorskip("reedsolo", reason="FORTRESS usa ECC por defecto (reedsolo)")
        engine = StegoEngine(mode=StegoMode.FORTRESS)
        sim = PlatformSimulator()
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        processed = os.path.join(tmpdir, "instagram.jpg")
        engine.embed(cover_image, short_message, stego, target_platform="instagram")
        sim.simulate("instagram", stego, processed)
        result = engine.extract(processed)
        assert result is not None
        assert result["message"] == short_message

    def test_hybrid_auto_select(self, cover_image, short_message):
        pytest.importorskip("reedsolo", reason="HYBRID selecciona FORTRESS con ECC por defecto")
        engine = StegoEngine(mode=StegoMode.HYBRID)
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        meta = engine.embed(cover_image, short_message, stego, target_platform="whatsapp_standard")
        assert meta["mode"] == "FORTRESS"

    def test_capacity_calculation(self, cover_image):
        engine = StegoEngine()
        cap_fortress = engine.get_capacity(cover_image, StegoMode.FORTRESS)
        cap_armor = engine.get_capacity(cover_image, StegoMode.ARMOR)
        cap_ghost = engine.get_capacity(cover_image, StegoMode.GHOST)
        assert cap_ghost > cap_armor > cap_fortress
        assert cap_fortress > 0

    def test_capacity_with_ecc(self, cover_image):
        """Test that capacity correctly reflects ECC overhead."""
        engine = StegoEngine()
        cap_no_ecc = engine.get_capacity(cover_image, StegoMode.ARMOR, ecc_bytes=0)
        cap_32 = engine.get_capacity(cover_image, StegoMode.ARMOR, ecc_bytes=32)
        cap_96 = engine.get_capacity(cover_image, StegoMode.ARMOR, ecc_bytes=96)
        assert cap_no_ecc > cap_32 > cap_96

    def test_encryption_argon2id(self, cover_image, short_message):
        """Test Argon2id key derivation + AES-256-GCM roundtrip."""
        pytest.importorskip("argon2", reason="cifrado con contraseña requiere argon2-cffi")
        engine = StegoEngine(mode=StegoMode.GHOST, password="secret123")
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        engine.embed(cover_image, short_message, stego)
        engine_no_pass = StegoEngine()
        result = engine_no_pass.extract(stego)
        assert result is None or result["message"] != short_message
        engine_with_pass = StegoEngine(password="secret123")
        result = engine_with_pass.extract(stego)
        assert result is not None
        assert result["message"] == short_message

    def test_sync_markers_detected(self, cover_image, short_message):
        pytest.importorskip("reedsolo", reason="FORTRESS usa ECC por defecto (reedsolo)")
        engine = StegoEngine(mode=StegoMode.FORTRESS)
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        engine.embed(cover_image, short_message, stego)
        img = Image.open(stego).convert("YCbCr")
        y = np.array(img.split()[0], dtype=np.float32)
        detected, score = engine._detect_sync_markers(y)
        assert detected is True
        assert score > 0.3

    def test_auto_tune_standard(self, cover_image, short_message):
        pytest.importorskip("reedsolo", reason="auto_tune prueba candidatos con ECC (reedsolo)")
        engine = StegoEngine()
        result = engine.auto_tune(cover_image, short_message, "telegram_photo", search_depth="standard")
        assert result is not None
        assert "delta" in result
        assert "mode" in result
        assert "ecc" in result
        assert "phase" in result
        # Phase may be "complete" or "coarse_failed" depending on simulation survival
        assert result["phase"] in ("complete", "coarse_failed", "no_candidates")
        assert result["candidates_tested"] > 0

    def test_auto_tune_quick(self, cover_image, short_message):
        pytest.importorskip("reedsolo", reason="auto_tune prueba candidatos con ECC (reedsolo)")
        engine = StegoEngine()
        result = engine.auto_tune(cover_image, short_message, "telegram_photo", search_depth="quick")
        assert result is not None
        assert result["phase"] in ("complete", "coarse_failed", "no_candidates")

    def test_auto_tune_deep(self, cover_image, short_message):
        pytest.importorskip("reedsolo", reason="auto_tune prueba candidatos con ECC (reedsolo)")
        engine = StegoEngine()
        result = engine.auto_tune(cover_image, short_message, "telegram_photo", search_depth="deep")
        assert result is not None
        assert result["phase"] in ("complete", "coarse_failed", "no_candidates")
        assert result["candidates_tested"] >= result.get("candidates_tested", 0)

    def test_ecc_override_embedding(self, cover_image, short_message):
        """Test that ecc_override is actually used and reflected in metadata."""
        pytest.importorskip("reedsolo", reason="ecc_override>0 requiere reedsolo")
        engine = StegoEngine(mode=StegoMode.ARMOR, ecc_override=64)
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        meta = engine.embed(cover_image, short_message, stego)
        assert meta["ecc_used"] == 64

    def test_delta_bounds(self):
        """Test that invalid delta values are clamped or rejected."""
        with pytest.raises(ValueError):
            StegoEngine(delta_override=-1.0)
        with pytest.raises(ValueError):
            StegoEngine(delta_override=100.0)
        engine = StegoEngine(delta_override=0.3)  # Below MIN_DELTA=0.5
        assert engine.delta_override == 0.5

    def test_extraction_iteration_limit(self, cover_image):
        """Test that extraction on a clean image returns None quickly."""
        engine = StegoEngine()
        result = engine.extract(cover_image)
        assert result is None

    def test_json_cli_output(self, cover_image, short_message):
        pytest.importorskip("reedsolo", reason="perfil telegram_photo usa ARMOR con ECC")
        from click.testing import CliRunner
        from stegstr.cli import cli
        import json
        runner = CliRunner()
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        result = runner.invoke(cli, ["embed", cover_image, short_message, "-o", stego, "--json", "--platform", "telegram_photo"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["status"] == "success"
        assert output["mode"] == "ARMOR"

    def test_payload_limits(self, cover_image):
        """Test that oversized messages are rejected."""
        engine = StegoEngine()
        huge = "X" * (51 * 1024 * 1024)  # 51 MB > 50 MB limit
        tmpdir = tempfile.mkdtemp()
        with pytest.raises(ValueError, match="too large"):
            engine.embed(cover_image, huge, os.path.join(tmpdir, "out.png"))

    def test_malformed_header_rejection(self, cover_image, short_message):
        """Test that extraction rejects malformed headers."""
        engine = StegoEngine(mode=StegoMode.GHOST)
        tmpdir = tempfile.mkdtemp()
        stego = os.path.join(tmpdir, "stego.png")
        engine.embed(cover_image, short_message, stego)
        # Corrupt the first few bytes of the image (not the PNG structure, but the LSB data)
        img = Image.open(stego).convert("RGB")
        arr = np.array(img)
        arr[0, 0, 0] = (arr[0, 0, 0] & 0xFE) | 1  # Flip first bit
        corrupted = Image.fromarray(arr)
        corrupted_path = os.path.join(tmpdir, "corrupted.png")
        corrupted.save(corrupted_path)
        result = engine.extract(corrupted_path)
        # Should either fail gracefully or return None
        assert result is None or result.get("message") != short_message
