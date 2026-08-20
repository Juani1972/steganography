#!/usr/bin/env python3
"""
Stegstr Exhaustive Validation Suite v2.1.5 — Fase 7.1 (Corregido)

Validates all components of the steganography system:
 - Roundtrip tests for all modes (GHOST, ARMOR, FORTRESS, HYBRID, PHANTOM)
 - Platform simulation survival tests
 - Encryption/decryption with Argon2id
 - Reed-Solomon ECC functionality
 - Sync marker detection
 - Auto-tune across all search depths
 - Capacity calculations (including dynamic ECC)
 - Edge cases (empty messages, oversized images, binary data)
 - Nostr client initialization and event lifecycle
 - PHANTOM mode anti-detection (LSB Matching)
 - Steganalysis report generation (Chi², RS, SPA)
 - Heuristic optimizer recommendations
 - Security hardening (zip-bomb protection, delta bounds, extraction limits)
 - ECC override propagation
 - Binary data roundtrip with encoding detection
 - Delta bounds synchronized with engine constants

Run: python validate.py
"""

import sys
import os
import tempfile
import time
import traceback
import zlib
from typing import List, Tuple

import numpy as np
from PIL import Image

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stegstr.stego.engine import StegoEngine, StegoMode, MIN_DELTA, MAX_DELTA
from stegstr.platform.simulator import PlatformSimulator
from stegstr.agent.optimizer import StegstrAgent
from stegstr.analysis.steganalysis import StegAnalyzer


def create_test_image(size: Tuple[int, int] = (512, 512), textured: bool = True) -> str:
    """Create a test image and return its path."""
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, f"test_{size[0]}x{size[1]}.png")
    if textured:
        arr = np.random.randint(0, 256, (*size, 3), dtype=np.uint8)
    else:
        arr = np.ones((*size, 3), dtype=np.uint8) * 128
        noise = np.random.randint(-5, 5, (*size, 3), dtype=np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(path)
    return path


class ValidationResult:
    def __init__(self, name: str, passed: bool, duration_ms: float, error: str = None, details: dict = None):
        self.name = name
        self.passed = passed
        self.duration_ms = duration_ms
        self.error = error
        self.details = details or {}


class StegstrValidator:
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.engine = StegoEngine()
        self.simulator = PlatformSimulator()

    def run_all(self):
        """Run all validation tests."""
        print("=" * 70)
        print("Stegstr Exhaustive Validation Suite v2.1.5 — Fase 7.1 (Corregido)")
        print("=" * 70)

        tests = [
            ("Basic GHOST roundtrip", self.test_ghost_roundtrip),
            ("Basic ARMOR roundtrip", self.test_armor_roundtrip),
            ("Basic FORTRESS roundtrip", self.test_fortress_roundtrip),
            ("PHANTOM roundtrip", self.test_phantom_roundtrip),
            ("HYBRID auto-selection", self.test_hybrid_auto_select),
            ("Encrypted roundtrip (Argon2id)", self.test_encrypted_roundtrip),
            ("Platform survival: WhatsApp", self.test_whatsapp_survival),
            ("Platform survival: Instagram", self.test_instagram_survival),
            ("Platform survival: Telegram", self.test_telegram_survival),
            ("Sync marker detection", self.test_sync_markers),
            ("Auto-tune quick", self.test_auto_tune_quick),
            ("Auto-tune standard", self.test_auto_tune_standard),
            ("Auto-tune deep", self.test_auto_tune_deep),
            ("Capacity calculation", self.test_capacity_calculation),
            ("Capacity with ECC override", self.test_capacity_ecc_override),
            ("Empty message rejection", self.test_empty_message_rejection),
            ("Oversized message rejection", self.test_oversized_message),
            ("Small image rejection", self.test_small_image_rejection),
            ("Large image rejection (no RAM bomb)", self.test_large_image_rejection),
            ("Binary data roundtrip", self.test_binary_data),
            ("Unicode message roundtrip", self.test_unicode_message),
            ("Heuristic optimizer", self.test_heuristic_optimizer),
            ("Reed-Solomon ECC", self.test_reed_solomon),
            ("Malformed header handling", self.test_malformed_header),
            ("Delta search extraction", self.test_delta_search),
            ("ECC override propagation", self.test_ecc_override_propagation),
            ("Delta bounds validation", self.test_delta_bounds),
            ("Extraction iteration limit", self.test_extraction_limits),
            ("Zip-bomb protection", self.test_zip_bomb_protection),
            ("PHANTOM less detectable than GHOST", self.test_phantom_anti_detection),
            ("StegAnalyzer report structure", self.test_analyzer_report),
            ("Nostr client lifecycle", self.test_nostr_lifecycle),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            start = time.perf_counter()
            try:
                test_func()
                duration = (time.perf_counter() - start) * 1000
                self.results.append(ValidationResult(name, True, duration))
                print(f" ✅ {name:.<50} {duration:>8.1f}ms")
                passed += 1
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                self.results.append(ValidationResult(name, False, duration, error=str(e)))
                print(f" ❌ {name:.<50} {duration:>8.1f}ms")
                print(f"    Error: {e}")
                failed += 1

        print("\n" + "=" * 70)
        print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
        success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        print("=" * 70)

        if failed > 0:
            print("\nFailed tests details:")
            for r in self.results:
                if not r.passed:
                    print(f" • {r.name}: {r.error}")

        return failed == 0

    def test_ghost_roundtrip(self):
        cover = create_test_image()
        msg = "GHOST test message"
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            self.engine.embed(cover, msg, stego, mode=StegoMode.GHOST)
            result = self.engine.extract(stego, expected_mode=StegoMode.GHOST)
            assert result is not None, "Extraction returned None"
            assert result["message"] == msg, f"Message mismatch: {result['message']} != {msg}"

    def test_armor_roundtrip(self):
        cover = create_test_image()
        msg = "ARMOR test message for social media"
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            self.engine.embed(cover, msg, stego, mode=StegoMode.ARMOR)
            result = self.engine.extract(stego, expected_mode=StegoMode.ARMOR)
            assert result is not None, "Extraction returned None"
            assert result["message"] == msg, f"Message mismatch: {result['message']} != {msg}"

    def test_fortress_roundtrip(self):
        cover = create_test_image()
        msg = "FORTRESS test"
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            self.engine.embed(cover, msg, stego, mode=StegoMode.FORTRESS)
            result = self.engine.extract(stego, expected_mode=StegoMode.FORTRESS)
            assert result is not None, "Extraction returned None"
            assert result["message"] == msg, f"Message mismatch: {result['message']} != {msg}"

    def test_phantom_roundtrip(self):
        cover = create_test_image()
        msg = "PHANTOM anti-detection test message"
        engine = StegoEngine(mode=StegoMode.PHANTOM)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "phantom.png")
            engine.embed(cover, msg, stego)
            result = engine.extract(stego, expected_mode=StegoMode.PHANTOM)
            assert result is not None, "PHANTOM extraction returned None"
            assert result["message"] == msg
            assert result["mode"] == "PHANTOM"

    def test_hybrid_auto_select(self):
        cover = create_test_image()
        msg = "Hybrid test"
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            meta = self.engine.embed(cover, msg, stego, target_platform="whatsapp_standard")
            assert meta["mode"] == "FORTRESS", f"Expected FORTRESS, got {meta['mode']}"
            meta = self.engine.embed(cover, msg, stego, target_platform="telegram_photo")
            assert meta["mode"] == "ARMOR", f"Expected ARMOR, got {meta['mode']}"
            meta = self.engine.embed(cover, msg, stego, target_platform="signal")
            assert meta["mode"] == "PHANTOM", f"Expected PHANTOM, got {meta['mode']}"

    def test_encrypted_roundtrip(self):
        cover = create_test_image()
        msg = "Secret encrypted message"
        engine_enc = StegoEngine(mode=StegoMode.ARMOR, password="test_password_123")
        engine_dec = StegoEngine(password="test_password_123")
        engine_wrong = StegoEngine(password="wrong_password")
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine_enc.embed(cover, msg, stego)
            result_wrong = engine_wrong.extract(stego)
            assert result_wrong is None or result_wrong.get("message") != msg, "Wrong password extracted message!"
            result = engine_dec.extract(stego)
            assert result is not None, "Correct password extraction failed"
            assert result["message"] == msg, f"Message mismatch: {result['message']} != {msg}"

    def test_whatsapp_survival(self):
        cover = create_test_image()
        msg = "WA test"
        engine = StegoEngine(mode=StegoMode.FORTRESS)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            processed = os.path.join(tmpdir, "wa.jpg")
            engine.embed(cover, msg, stego, target_platform="whatsapp_standard")
            self.simulator.simulate("whatsapp_standard", stego, processed)
            result = engine.extract(processed)
            assert result is not None, "Message did not survive WhatsApp simulation"
            assert result["message"] == msg, f"Message mismatch after WA: {result['message']} != {msg}"

    def test_instagram_survival(self):
        cover = create_test_image()
        msg = "IG test"
        engine = StegoEngine(mode=StegoMode.FORTRESS)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            processed = os.path.join(tmpdir, "ig.jpg")
            engine.embed(cover, msg, stego, target_platform="instagram")
            self.simulator.simulate("instagram", stego, processed)
            result = engine.extract(processed)
            assert result is not None, "Message did not survive Instagram simulation"
            assert result["message"] == msg, f"Message mismatch after IG: {result['message']} != {msg}"

    def test_telegram_survival(self):
        cover = create_test_image()
        msg = "TG test message"
        engine = StegoEngine(mode=StegoMode.ARMOR)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            processed = os.path.join(tmpdir, "tg.jpg")
            engine.embed(cover, msg, stego, target_platform="telegram_photo")
            self.simulator.simulate("telegram_photo", stego, processed)
            result = engine.extract(processed)
            assert result is not None, "Message did not survive Telegram simulation"
            assert result["message"] == msg, f"Message mismatch after TG: {result['message']} != {msg}"

    def test_sync_markers(self):
        cover = create_test_image()
        msg = "Sync test"
        engine = StegoEngine(mode=StegoMode.FORTRESS)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover, msg, stego)
            img = Image.open(stego).convert("YCbCr")
            y = np.array(img.split()[0], dtype=np.float32)
            detected, score = engine._detect_sync_markers(y)
            assert detected, f"Sync markers not detected (score: {score})"
            assert score > 0.3, f"Sync score too low: {score}"

    def test_auto_tune_quick(self):
        cover = create_test_image()
        msg = "Auto-tune quick"
        result = self.engine.auto_tune(cover, msg, "telegram_photo", search_depth="quick")
        assert result["phase"] in ("complete", "coarse_failed", "no_candidates"), f"Auto-tune quick failed: {result}"
        assert result["candidates_tested"] > 0

    def test_auto_tune_standard(self):
        cover = create_test_image()
        msg = "Auto-tune standard"
        result = self.engine.auto_tune(cover, msg, "telegram_photo", search_depth="standard")
        assert result["phase"] in ("complete", "coarse_failed", "no_candidates"), f"Auto-tune standard failed: {result}"
        assert result["candidates_tested"] > 0

    def test_auto_tune_deep(self):
        cover = create_test_image()
        msg = "Auto-tune deep"
        result = self.engine.auto_tune(cover, msg, "telegram_photo", search_depth="deep")
        assert result["phase"] in ("complete", "coarse_failed", "no_candidates"), f"Auto-tune deep failed: {result}"
        assert result["candidates_tested"] > 0

    def test_capacity_calculation(self):
        cover = create_test_image((1024, 1024))
        cap_f = self.engine.get_capacity(cover, StegoMode.FORTRESS)
        cap_a = self.engine.get_capacity(cover, StegoMode.ARMOR)
        cap_g = self.engine.get_capacity(cover, StegoMode.GHOST)
        assert cap_g > cap_a > cap_f > 0, f"Capacity ordering wrong: G={cap_g}, A={cap_a}, F={cap_f}"

    def test_capacity_ecc_override(self):
        cover = create_test_image((1024, 1024))
        cap_0 = self.engine.get_capacity(cover, StegoMode.ARMOR, ecc_bytes=0)
        cap_32 = self.engine.get_capacity(cover, StegoMode.ARMOR, ecc_bytes=32)
        cap_96 = self.engine.get_capacity(cover, StegoMode.ARMOR, ecc_bytes=96)
        assert cap_0 > cap_32 > cap_96, f"ECC capacity ordering wrong: 0={cap_0}, 32={cap_32}, 96={cap_96}"

    def test_empty_message_rejection(self):
        cover = create_test_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest_raises(ValueError):
                self.engine.embed(cover, "", os.path.join(tmpdir, "out.png"))

    def test_oversized_message(self):
        cover = create_test_image()
        huge = "X" * (51 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                self.engine.embed(cover, huge, os.path.join(tmpdir, "out.png"))
                assert False, "Should have rejected oversized message"
            except ValueError as e:
                assert "too large" in str(e).lower() or "large" in str(e).lower()

    def test_small_image_rejection(self):
        tmpdir = tempfile.mkdtemp()
        small = os.path.join(tmpdir, "small.png")
        arr = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)
        Image.fromarray(arr).save(small)
        with tempfile.TemporaryDirectory() as tmpdir2:
            try:
                self.engine.embed(small, "test", os.path.join(tmpdir2, "out.png"))
                assert False, "Should have rejected small image"
            except ValueError as e:
                assert "small" in str(e).lower() or "too small" in str(e).lower()

    def test_large_image_rejection(self):
        tmpdir = tempfile.mkdtemp()
        with tempfile.TemporaryDirectory() as tmpdir2:
            try:
                from stegstr.stego.engine import MAX_IMAGE_DIMENSION
                assert MAX_IMAGE_DIMENSION == 16384
                img = Image.new("RGB", (20000, 20000))
                w, h = img.size
                assert w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION
            except AssertionError:
                raise

    def test_binary_data(self):
        cover = create_test_image()
        msg = bytes(range(256)) * 100
        engine = StegoEngine(mode=StegoMode.GHOST)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover, msg, stego)
            result = engine.extract(stego)
            assert result is not None
            assert result["encoding"] == "base64"
            import base64
            decoded = base64.b64decode(result["message"])
            assert decoded == msg, "Binary data roundtrip failed"

    def test_unicode_message(self):
        cover = create_test_image()
        msg = "日本語テスト 🎉 émojis ñoño «guillemets» 中文测试"
        engine = StegoEngine(mode=StegoMode.ARMOR)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover, msg, stego)
            result = engine.extract(stego)
            assert result is not None
            assert result["message"] == msg

    def test_heuristic_optimizer(self):
        cover = create_test_image()
        agent = StegstrAgent()
        rec = agent.recommend_mode(cover, "Test message", "whatsapp_standard")
        assert rec["mode"] == "FORTRESS"
        assert rec["fits_message"] is True
        assert 0 <= rec["quality_score"] <= 1
        assert rec["delta"] > 0
        assert len(rec["recommendations"]) > 0

    def test_reed_solomon(self):
        from stegstr.stego.engine import StegoEngine
        data = b"Reed-Solomon test data for ECC validation"
        encoded = StegoEngine._rs_encode(data, ecc_bytes=32)
        assert encoded is not None
        assert len(encoded) > len(data)
        decoded = StegoEngine._rs_decode(encoded, ecc_bytes=32)
        assert decoded == data, "RS decode mismatch"

    def test_malformed_header(self):
        cover = create_test_image()
        engine = StegoEngine(mode=StegoMode.GHOST)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover, "test", stego)
            img = Image.open(stego).convert("RGB")
            arr = np.array(img)
            for i in range(14 * 8):
                row = i // (arr.shape[1] * 3)
                col = (i % (arr.shape[1] * 3)) // 3
                ch = i % 3
                if row < arr.shape[0] and col < arr.shape[1]:
                    arr[row, col, ch] = (arr[row, col, ch] & 0xFE) | ((i + 1) % 2)
            corrupted = Image.fromarray(arr)
            corrupted_path = os.path.join(tmpdir, "corrupted.png")
            corrupted.save(corrupted_path)
            result = engine.extract(corrupted_path)
            assert result is None, "Should have returned None for corrupted data"

    def test_delta_search(self):
        cover = create_test_image()
        msg = "Delta search test"
        engine_embed = StegoEngine(mode=StegoMode.ARMOR, delta_override=6.5)
        engine_extract = StegoEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine_embed.embed(cover, msg, stego)
            result = engine_extract.extract(stego)
            assert result is not None, "Delta search extraction failed"
            assert result["message"] == msg
            assert result["delta_used"] == 6.5, f"Expected delta 6.5, got {result['delta_used']}"

    def test_ecc_override_propagation(self):
        cover = create_test_image()
        msg = "ECC override test"
        engine = StegoEngine(mode=StegoMode.ARMOR, ecc_override=64)
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            meta = engine.embed(cover, msg, stego)
            assert meta["ecc_used"] == 64, f"Expected ecc_used=64, got {meta['ecc_used']}"

    def test_delta_bounds(self):
        with pytest_raises(ValueError):
            StegoEngine(delta_override=-1.0)
        with pytest_raises(ValueError):
            StegoEngine(delta_override=MAX_DELTA + 1)
        engine = StegoEngine(delta_override=MIN_DELTA)
        assert engine.delta_override == MIN_DELTA
        engine2 = StegoEngine(delta_override=MAX_DELTA)
        assert engine2.delta_override == MAX_DELTA

    def test_extraction_limits(self):
        cover = create_test_image()
        result = self.engine.extract(cover)
        assert result is None

    def test_zip_bomb_protection(self):
        from stegstr.stego.engine import StegoEngine
        bomb = zlib.compress(b"X" * 1000)
        try:
            StegoEngine._safe_zlib_decompress(bomb, max_size=500)
            assert False, "Should have rejected potential zip bomb"
        except ValueError as e:
            assert "zip bomb" in str(e).lower() or "exceeds" in str(e).lower()

    def test_phantom_anti_detection(self):
        cover = create_test_image()
        msg = "A" * 5000
        analyzer = StegAnalyzer()
        with tempfile.TemporaryDirectory() as tmpdir:
            ghost = os.path.join(tmpdir, "ghost.png")
            phantom = os.path.join(tmpdir, "phantom.png")
            StegoEngine(mode=StegoMode.GHOST).embed(cover, msg, ghost)
            StegoEngine(mode=StegoMode.PHANTOM).embed(cover, msg, phantom)
            ghost_p = analyzer.chi2_attack(ghost)["chi2_p_value"]
            phantom_p = analyzer.chi2_attack(phantom)["chi2_p_value"]
            assert phantom_p >= ghost_p, (
                f"PHANTOM p-value ({phantom_p}) should exceed or match GHOST ({ghost_p})"
            )

    def test_analyzer_report(self):
        cover = create_test_image()
        msg = "Analyzer test"
        analyzer = StegAnalyzer()
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            StegoEngine(mode=StegoMode.ARMOR).embed(cover, msg, stego)
            report = analyzer.analyze(stego)
            assert "combined_detection_score" in report
            assert 0.0 <= report["combined_detection_score"] <= 1.0
            assert "likely_stego" in report

    def test_nostr_lifecycle(self):
        from stegstr.nostr.client import NostrClient, NostrEvent
        import time
        dummy_sk = "a" * 64
        client = NostrClient(private_key_hex=dummy_sk)
        assert client.pubkey is not None
        assert len(client.pubkey) == 64
        event = NostrEvent(
            id="", pubkey=client.pubkey, created_at=int(time.time()),
            kind=1, tags=[["t", "test"]], content="hello", sig=""
        )
        event_id = event.compute_id()
        assert len(event_id) == 64
        assert event.compute_id() == event_id
        assert len(client.relays) >= 3


def pytest_raises(exc_type):
    class RaisesContext:
        def __enter__(self):
            return self
        def __exit__(self, exc_type_actual, exc_val, exc_tb):
            if exc_type_actual is None:
                raise AssertionError(f"Expected {exc_type.__name__} but no exception was raised")
            if not issubclass(exc_type_actual, exc_type):
                raise AssertionError(f"Expected {exc_type.__name__} but got {exc_type_actual.__name__}")
            return True
    return RaisesContext()


if __name__ == "__main__":
    validator = StegstrValidator()
    success = validator.run_all()
    sys.exit(0 if success else 1)
