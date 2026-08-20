"""
Integration tests v2.2 — End-to-End validation across all components.

Tests:
  1. Full pipeline: embed → platform upload → download → extract
  2. Nostr E2E: publish → query → verify
  3. Multi-platform roundtrip with mock adapters
  4. Stress test: multiple carriers, multiple messages
  5. Regression: compare against baseline
"""

import pytest
import tempfile
import os
import json
import numpy as np
from PIL import Image

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.real_world_validator import RealWorldValidator, BenchmarkReport

# La práctica totalidad de los tests de este fichero usan StegoEngine con
# contraseña (cifrado -> requiere argon2-cffi) y/o modos ARMOR/FORTRESS
# (ECC -> requiere reedsolo). Sin estas dos dependencias opcionales, los
# tests fallaban con "results=[]" o RuntimeError confusos en vez de un
# SKIP claro. Ver PATCH_NOTES.md, sección "Parches v3".
pytest.importorskip("argon2", reason="argon2-cffi no instalado (necesario: StegoEngine cifra con contraseña)")
pytest.importorskip("reedsolo", reason="reedsolo no instalado (necesario para modos ARMOR/FORTRESS)")


class TestIntegration:
    @pytest.fixture
    def cover(self):
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "cover.png")
        Image.fromarray(arr).save(path)
        return path

    def test_full_pipeline(self, cover):
        """Basic embed/extract roundtrip."""
        engine = StegoEngine(mode=StegoMode.ARMOR, password="test")
        with tempfile.TemporaryDirectory() as tmpdir:
            stego = os.path.join(tmpdir, "stego.png")
            engine.embed(cover, "integration test", stego)
            result = engine.extract(stego)
            assert result is not None
            assert result["message"] == "integration test"

    def test_all_modes_roundtrip(self, cover):
        """Test all modes can embed and extract correctly."""
        modes = [StegoMode.GHOST, StegoMode.PHANTOM, StegoMode.ARMOR, StegoMode.FORTRESS]
        for mode in modes:
            engine = StegoEngine(mode=mode, password="test")
            with tempfile.TemporaryDirectory() as tmpdir:
                stego = os.path.join(tmpdir, "stego.png")
                engine.embed(cover, f"mode_{mode.name}", stego)
                result = engine.extract(stego)
                assert result is not None, f"Mode {mode.name} extraction failed"
                assert result["message"] == f"mode_{mode.name}", f"Mode {mode.name} message mismatch"

    def test_platform_mock_roundtrip(self, cover):
        """Test full platform cycle with mock adapter."""
        from tests.test_real_world import MockAdapter
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover, "hello world",
                                                modes=[StegoMode.GHOST])
        assert len(report.results) == 1
        r = report.results[0]
        assert r.uploaded and r.downloaded and r.extracted and r.message_match

    def test_reproducible_benchmark(self, cover):
        """Test N-iteration reproducible benchmark."""
        from tests.test_real_world import MockAdapter
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")

        report1 = validator.run_reproducible_benchmark(
            cover, "test msg", iterations=3, seed=42,
            modes=[StegoMode.GHOST]
        )
        report2 = validator.run_reproducible_benchmark(
            cover, "test msg", iterations=3, seed=42,
            modes=[StegoMode.GHOST]
        )

        assert report1.summary["overall_survival_rate"] == report2.summary["overall_survival_rate"]
        assert len(report1.results) == len(report2.results) == 3

    def test_stress_test_mock(self):
        """Stress test with mock adapters."""
        from tests.test_real_world import MockAdapter
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")

        report = validator.run_stress_test(
            num_carriers=3, num_messages=2, seed=42,
            modes=[StegoMode.GHOST]
        )
        assert report.stress_test
        assert report.num_carriers == 3
        assert report.num_messages == 2
        assert len(report.results) == 3 * 2 * 1  # 3 carriers * 2 messages * 1 adapter
        survival = report.survival_rate()
        assert survival == 1.0, f"Expected 100% survival, got {survival}"

    def test_report_serialization(self, cover):
        """Test report JSON/CSV serialization."""
        from tests.test_real_world import MockAdapter
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover, "test", modes=[StegoMode.GHOST])

        json_str = report.to_json()
        assert "survival_rate" in json_str

        csv_str = report.to_csv()
        assert "iteration,platform,mode" in csv_str

        # Verify JSON is valid
        parsed = json.loads(json_str)
        assert parsed["version"] == "2.2"

    def test_ber_computation(self, cover):
        """Test BER is computed correctly."""
        from tests.test_real_world import MockAdapter
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover, "test", modes=[StegoMode.GHOST])
        r = report.results[0]
        assert r.ber == 0.0, f"Expected BER=0 for lossless, got {r.ber}"

    def test_regression_check(self, cover, tmp_path):
        """Test regression detection against baseline."""
        from tests.test_real_world import MockAdapter
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover, "test", modes=[StegoMode.GHOST])

        baseline = tmp_path / "baseline.json"
        baseline.write_text(report.to_json())

        # Same test should show no regression
        reg = report.regression_check(str(baseline))
        assert not reg["regression"]
        assert reg["regression_delta"] == 0.0
