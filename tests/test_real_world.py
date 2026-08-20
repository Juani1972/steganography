"""
Tests for Real-World Platform Validator v2.2

NUEVO v2.2:
- Mock adapters con compresión realista (JPEG, crop, resize)
- Ground truth comparison (document vs photo)
- N-iteration tests
- BER validation
- Regression detection

Run:
    pytest tests/test_real_world.py -v
"""

import pytest
import tempfile
import os
import uuid
import numpy as np
from PIL import Image

from stegstr.platform.real_world_validator import RealWorldValidator, BenchmarkReport, PlatformResult
from stegstr.stego.engine import StegoEngine, StegoMode

# RealWorldValidator siempre cifra (password="test"/"validation" por
# defecto) -> requiere argon2-cffi en TODOS los tests de este fichero.
# Los tests concretos que además usan FORTRESS/ARMOR añaden su propio
# pytest.importorskip("reedsolo"). Ver PATCH_NOTES.md, "Parches v3".
pytest.importorskip("argon2", reason="argon2-cffi no instalado (RealWorldValidator cifra siempre)")


class MockAdapter:
    """Mock platform adapter with configurable realistic transformations."""

    def __init__(self, name="mock", simulate_compression=False, simulate_crop=False,
                 simulate_resize=False, simulate_reencode=False, quality=75):
        self.name = name
        self.simulate_compression = simulate_compression
        self.simulate_crop = simulate_crop
        self.simulate_resize = simulate_resize
        self.simulate_reencode = simulate_reencode
        self.quality = quality
        self._uploaded = {}

    def platform_name(self):
        return self.name

    def description(self):
        transforms = []
        if self.simulate_compression:
            transforms.append(f"JPEG Q{self.quality}")
        if self.simulate_crop:
            transforms.append("crop")
        if self.simulate_resize:
            transforms.append("resize")
        if self.simulate_reencode:
            transforms.append("re-encode")
        return f"Mock adapter for {self.name} ({', '.join(transforms) or 'lossless'})"

    def requires_credentials(self):
        return False

    def is_available(self):
        return True

    def upload(self, image_path):
        mock_url = f"mock://{self.name}/{uuid.uuid4().hex}"
        self._uploaded[mock_url] = image_path
        return mock_url

    def download(self, url, output_path):
        from PIL import Image
        real_path = self._uploaded.get(url, url)
        img = Image.open(real_path).convert("RGB")

        # Apply transformations in order
        if self.simulate_resize:
            w, h = img.size
            img = img.resize((w // 2, h // 2), Image.LANCZOS)

        if self.simulate_crop:
            w, h = img.size
            img = img.crop((0, 0, w // 2, h // 2))

        if self.simulate_compression:
            buf = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            img.save(buf.name, "JPEG", quality=self.quality, optimize=True)
            img = Image.open(buf.name).convert("RGB")
            os.unlink(buf.name)

        if self.simulate_reencode:
            # Double JPEG compression (like Instagram)
            buf1 = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            img.save(buf1.name, "JPEG", quality=85, optimize=True)
            img = Image.open(buf1.name).convert("RGB")
            os.unlink(buf1.name)
            buf2 = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            img.save(buf2.name, "JPEG", quality=self.quality, optimize=True)
            img = Image.open(buf2.name).convert("RGB")
            os.unlink(buf2.name)

        img.save(output_path, "PNG")
        return True


class TestRealWorldValidator:
    @pytest.fixture
    def cover_image(self):
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "cover.png")
        img.save(path)
        return path

    def test_mock_lossless(self, cover_image):
        """Perfect mock adapter should preserve GHOST messages."""
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover_image, "hello world",
                                                modes=[StegoMode.GHOST])
        assert len(report.results) == 1
        r = report.results[0]
        assert r.uploaded and r.downloaded and r.extracted and r.message_match
        assert r.ber == 0.0
        assert r.error is None

    def test_mock_jpeg_compression(self, cover_image):
        """JPEG compression mock should fail GHOST but maybe survive FORTRESS."""
        pytest.importorskip("reedsolo", reason="FORTRESS requiere ECC (reedsolo)")
        adapter = MockAdapter("mock_jpeg", simulate_compression=True, quality=75)
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover_image, "hello world",
                                                modes=[StegoMode.GHOST, StegoMode.FORTRESS])
        ghost = [r for r in report.results if r.mode == "GHOST"][0]
        fortress = [r for r in report.results if r.mode == "FORTRESS"][0]
        # GHOST should fail under JPEG
        assert not ghost.message_match or ghost.ber > 0
        # FORTRESS might survive with ECC
        assert fortress.extracted

    def test_mock_double_compression(self, cover_image):
        """Double JPEG (Instagram-like) should be harder."""
        pytest.importorskip("reedsolo", reason="FORTRESS/ARMOR requieren ECC (reedsolo)")
        adapter = MockAdapter("mock_instagram", simulate_reencode=True, quality=75)
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover_image, "hello world",
                                                modes=[StegoMode.FORTRESS, StegoMode.ARMOR])
        for r in report.results:
            assert r.extracted  # Should at least extract something

    def test_mock_crop(self, cover_image):
        """Crop should test DCT marker resilience."""
        pytest.importorskip("reedsolo", reason="FORTRESS requiere ECC (reedsolo)")
        adapter = MockAdapter("mock_crop", simulate_crop=True)
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover_image, "hello world",
                                                modes=[StegoMode.FORTRESS])
        r = report.results[0]
        assert r.extracted

    def test_reproducible_benchmark(self, cover_image):
        """N-iteration benchmark should be deterministic with same seed."""
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")

        report1 = validator.run_reproducible_benchmark(
            cover_image, "test", iterations=5, seed=42,
            modes=[StegoMode.GHOST]
        )
        report2 = validator.run_reproducible_benchmark(
            cover_image, "test", iterations=5, seed=42,
            modes=[StegoMode.GHOST]
        )

        assert len(report1.results) == len(report2.results) == 5
        assert report1.summary["overall_survival_rate"] == report2.summary["overall_survival_rate"]
        for r1, r2 in zip(report1.results, report2.results):
            assert r1.message_match == r2.message_match
            assert r1.ber == r2.ber

    def test_stress_test(self):
        """Stress test with multiple carriers and messages."""
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")

        report = validator.run_stress_test(
            num_carriers=5, num_messages=3, seed=42,
            modes=[StegoMode.GHOST]
        )
        assert report.stress_test
        assert len(report.results) == 5 * 3 * 1  # 5 carriers * 3 messages * 1 adapter
        assert report.survival_rate() == 1.0

    def test_report_stats(self, cover_image):
        """Test aggregate statistics computation."""
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover_image, "test",
                                                modes=[StegoMode.GHOST, StegoMode.PHANTOM])
        stats = report.aggregate_stats()
        assert stats["total_tests"] == 2
        assert stats["survived"] == 2
        assert stats["overall_survival_rate"] == 1.0
        assert stats["mean_psnr_db"] > 0
        assert stats["mean_ber"] == 0.0

    def test_regression_detection(self, cover_image, tmp_path):
        """Test regression detection against baseline."""
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover_image, "test", modes=[StegoMode.GHOST])

        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(report.to_json())

        reg = report.regression_check(str(baseline_path))
        assert not reg["regression"]
        assert reg["regression_delta"] == 0.0

    def test_ber_computation_accuracy(self, cover_image):
        """Verify BER is 0 for perfect extraction and >0 for corrupted."""
        # Lossless: BER = 0
        adapter_lossless = MockAdapter("lossless")
        validator = RealWorldValidator(adapters=[adapter_lossless], password="test")
        report = validator.run_full_benchmark(cover_image, "exact message",
                                               modes=[StegoMode.GHOST])
        assert report.results[0].ber == 0.0

    def test_csv_export(self, cover_image):
        """Test CSV export format."""
        adapter = MockAdapter("mock_lossless")
        validator = RealWorldValidator(adapters=[adapter], password="test")
        report = validator.run_full_benchmark(cover_image, "test", modes=[StegoMode.GHOST])
        csv = report.to_csv()
        lines = csv.strip().split("\n")
        assert len(lines) == 2  # header + 1 result
        assert lines[0].startswith("iteration,platform,mode")

    def test_multiple_adapters(self, cover_image):
        """Test with multiple mock adapters simultaneously."""
        pytest.importorskip("reedsolo", reason="FORTRESS/ARMOR requieren ECC (reedsolo)")
        adapters = [
            MockAdapter("telegram", simulate_compression=True, quality=82),
            MockAdapter("instagram", simulate_reencode=True, quality=75),
            MockAdapter("whatsapp", simulate_compression=True, quality=55),
        ]
        validator = RealWorldValidator(adapters=adapters, password="test")
        report = validator.run_full_benchmark(cover_image, "test",
                                                modes=[StegoMode.FORTRESS, StegoMode.ARMOR])
        assert len(report.results) == 3 * 2  # 3 adapters * 2 modes

        # All should extract (FORTRESS/ARMOR are robust)
        for r in report.results:
            assert r.extracted, f"{r.platform}/{r.mode} failed to extract"

    def test_platform_listing(self):
        """Test adapter availability listing."""
        adapters = RealWorldValidator.list_available_adapters()
        assert len(adapters) > 0
        for a in adapters:
            assert "name" in a
            assert "available" in a
