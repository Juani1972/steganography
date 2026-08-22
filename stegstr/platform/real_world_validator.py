"""
Stegstr Real-World Platform Validator v2.2

Validates steganographic message survival across real social media platforms
by uploading images via official APIs, downloading the processed versions,
and attempting extraction — with REPRODUCIBLE BENCHMARKS and STRESS TESTING.

NUEVO v2.2:
- N-iteration benchmark (configurable repetitions)
- Stress test: múltiples carriers, múltiples payloads
- Ground truth comparison (document vs photo en Telegram)
- Métricas agregadas: tasa de supervivencia, BER, PSNR, tiempo
- Reporte JSON/CSV reproducible con semilla aleatoria
- Detección de regresiones vs baseline

Supported platforms:
  telegram, imgur, discord, reddit, instagram, twitter, whatsapp

Usage:
    from stegstr.platform.real_world_validator import RealWorldValidator
    validator = RealWorldValidator()

    # Single test
    report = validator.run_full_benchmark("cover.png", "secret message")

    # Reproducible N-iteration benchmark
    report = validator.run_reproducible_benchmark(
        "cover.png", "secret message",
        iterations=10, seed=42
    )

    # Stress test
    report = validator.run_stress_test(
        num_carriers=20, num_messages=5, seed=42
    )

    print(report.to_json())
"""

import os
import time
import tempfile
import json
import logging
import random
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

import numpy as np
from PIL import Image

from stegstr.stego.engine import StegoEngine, StegoMode

logger = logging.getLogger(__name__)


@dataclass
class PlatformResult:
    """Result of testing a single platform + mode combination."""
    platform: str
    mode: str
    message: str
    uploaded: bool
    downloaded: bool
    extracted: bool
    message_match: bool
    psnr_db: float = 0.0
    ber: float = 1.0
    delta_used: float = 0.0
    ecc_used: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0
    iteration: int = 1
    carrier_hash: str = ""  # SHA-256 of cover image for reproducibility
    payload_hash: str = ""  # SHA-256 of message for reproducibility


@dataclass
class BenchmarkReport:
    """Complete benchmark report across all platforms and modes."""
    timestamp: str
    version: str = "2.2"
    seed: Optional[int] = None
    iterations: int = 1
    cover_image: str = ""
    message_length: int = 0
    results: List[PlatformResult] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    stress_test: bool = False
    num_carriers: int = 0
    num_messages: int = 0
    # Combinaciones plataforma/modo que se saltaron por falta de una
    # dependencia opcional (p.ej. reedsolo para ARMOR/FORTRESS), en vez de
    # desaparecer silenciosamente de `results` sin explicación. Cada entrada:
    # {"platform": ..., "mode": ..., "reason": ...}
    skipped: List[Dict] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent, ensure_ascii=False, default=str)

    def to_csv(self) -> str:
        lines = [
            "iteration,platform,mode,uploaded,downloaded,extracted,match,psnr_db,ber,duration,error"
        ]
        for r in self.results:
            lines.append(
                f"{r.iteration},{r.platform},{r.mode},{r.uploaded},{r.downloaded},"
                f"{r.extracted},{r.message_match},{r.psnr_db:.2f},{r.ber:.4f},"
                f"{r.duration_seconds:.2f},{r.error or ''}"
            )
        return "\n".join(lines)

    def survival_rate(self, platform: Optional[str] = None,
                       mode: Optional[str] = None,
                       iteration: Optional[int] = None) -> float:
        """Fraction of tests where message survived intact."""
        filtered = self.results
        if platform:
            filtered = [r for r in filtered if r.platform == platform]
        if mode:
            filtered = [r for r in filtered if r.mode == mode]
        if iteration:
            filtered = [r for r in filtered if r.iteration == iteration]
        if not filtered:
            return 0.0
        survived = sum(1 for r in filtered if r.message_match)
        return survived / len(filtered)

    def best_mode_for_platform(self, platform: str) -> Optional[str]:
        """Return the mode with highest survival rate for a given platform."""
        platform_results = [r for r in self.results if r.platform == platform]
        if not platform_results:
            return None
        modes = {}
        for r in platform_results:
            if r.mode not in modes:
                modes[r.mode] = []
            modes[r.mode].append(r.message_match)
        best = max(modes.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        return best[0]

    def aggregate_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all results."""
        if not self.results:
            return {}

        psnr_values = [r.psnr_db for r in self.results if r.psnr_db > 0]
        ber_values = [r.ber for r in self.results if r.ber < 1.0]
        durations = [r.duration_seconds for r in self.results]

        return {
            "total_tests": len(self.results),
            "survived": sum(1 for r in self.results if r.message_match),
            "failed": sum(1 for r in self.results if not r.message_match),
            "overall_survival_rate": self.survival_rate(),
            "mean_psnr_db": round(np.mean(psnr_values), 2) if psnr_values else 0,
            "std_psnr_db": round(np.std(psnr_values), 2) if psnr_values else 0,
            "mean_ber": round(np.mean(ber_values), 4) if ber_values else 1.0,
            "std_ber": round(np.std(ber_values), 4) if ber_values else 0,
            "mean_duration_sec": round(np.mean(durations), 2) if durations else 0,
            "std_duration_sec": round(np.std(durations), 2) if durations else 0,
            "platforms_tested": list({r.platform for r in self.results}),
            "modes_tested": list({r.mode for r in self.results}),
            "best_platform": self._best_platform(),
            "best_mode": self._best_mode(),
        }

    def _best_platform(self) -> Optional[str]:
        platforms = {}
        for r in self.results:
            platforms.setdefault(r.platform, []).append(r.message_match)
        if not platforms:
            return None
        return max(platforms.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]

    def _best_mode(self) -> Optional[str]:
        modes = {}
        for r in self.results:
            modes.setdefault(r.mode, []).append(r.message_match)
        if not modes:
            return None
        return max(modes.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]

    def regression_check(self, baseline_path: str) -> Dict[str, Any]:
        """Compare against a baseline report to detect regressions."""
        try:
            with open(baseline_path, 'r') as f:
                baseline = json.load(f)
            baseline_rate = baseline.get("summary", {}).get("overall_survival_rate", 0)
            current_rate = self.aggregate_stats().get("overall_survival_rate", 0)
            return {
                "baseline_survival_rate": baseline_rate,
                "current_survival_rate": current_rate,
                "regression": current_rate < baseline_rate,
                "regression_delta": round(current_rate - baseline_rate, 4),
            }
        except Exception as e:
            return {"error": str(e)}


class RealWorldValidator:
    """
    Orchestrates real-world platform validation with reproducible benchmarks.
    """

    def __init__(self, adapters: Optional[List] = None, password: Optional[str] = None):
        self.password = password or "validation"
        self.adapters = adapters or self._default_adapters()
        self._engine = StegoEngine(password=self.password)

    def _default_adapters(self):
        """Auto-discover available adapters."""
        adapters = []
        adapter_specs = [
            ("stegstr.platform.adapters.telegram", "TelegramAdapter"),
            ("stegstr.platform.adapters.imgur", "ImgurAdapter"),
            ("stegstr.platform.adapters.discord", "DiscordAdapter"),
            ("stegstr.platform.adapters.reddit", "RedditAdapter"),
            ("stegstr.platform.adapters.instagram", "InstagramAdapter"),
            ("stegstr.platform.adapters.twitter", "TwitterAdapter"),
            ("stegstr.platform.adapters.whatsapp", "WhatsAppAdapter"),
        ]
        for module, cls_name in adapter_specs:
            try:
                mod = __import__(module, fromlist=[cls_name])
                cls = getattr(mod, cls_name)
                inst = cls()
                if inst.is_available():
                    adapters.append(inst)
                    logger.info(f"Adapter available: {inst.platform_name()}")
            except Exception as e:
                logger.debug(f"Adapter {cls_name} not available: {e}")
        return adapters

    def _compute_psnr(self, img1_path: str, img2_path: str) -> float:
        """Compute PSNR between two images."""
        try:
            img1 = np.array(Image.open(img1_path).convert("RGB"), dtype=np.float32)
            img2 = np.array(Image.open(img2_path).convert("RGB"), dtype=np.float32)
            if img1.shape != img2.shape:
                img2 = np.array(Image.open(img2_path).convert("RGB").resize(
                    (img1.shape[1], img1.shape[0]), Image.LANCZOS), dtype=np.float32)
            mse = np.mean((img1 - img2) ** 2)
            if mse == 0:
                return float("inf")
            return 20 * np.log10(255.0 / np.sqrt(mse))
        except Exception as e:
            logger.debug(f"PSNR computation failed: {e}")
            return 0.0

    def _compute_ber(self, original_bits: np.ndarray, extracted_bits: np.ndarray) -> float:
        """Compute Bit Error Rate between original and extracted bit arrays."""
        min_len = min(len(original_bits), len(extracted_bits))
        if min_len == 0:
            return 1.0
        errors = np.sum(original_bits[:min_len] != extracted_bits[:min_len])
        return float(errors / len(original_bits))

    def _message_to_bits(self, message: str) -> np.ndarray:
        """Convert message to bit array for BER computation."""
        data = message.encode("utf-8")
        return np.unpackbits(np.frombuffer(data, dtype=np.uint8))

    def test_platform(self, adapter, cover_path: str, message: str,
                      mode: StegoMode, iteration: int = 1) -> PlatformResult:
        """Test a single platform + mode combination."""
        platform = adapter.platform_name()
        mode_name = mode.name
        result = PlatformResult(
            platform=platform,
            mode=mode_name,
            message=message,
            uploaded=False,
            downloaded=False,
            extracted=False,
            message_match=False,
            iteration=iteration,
            carrier_hash=self._file_hash(cover_path),
            payload_hash=hashlib.sha256(message.encode()).hexdigest(),
        )
        start = time.time()

        with tempfile.TemporaryDirectory() as tmpdir:
            stego_path = os.path.join(tmpdir, "stego.png")
            processed_path = os.path.join(tmpdir, "processed.png")

            try:
                # 1. Embed
                self._engine.embed(cover_path, message, stego_path, mode=mode)

                # 2. Upload
                url_or_id = adapter.upload(stego_path)
                if url_or_id is None:
                    result.error = "Upload failed"
                    result.duration_seconds = time.time() - start
                    return result
                result.uploaded = True

                # 3. Download
                success = adapter.download(url_or_id, processed_path)
                if not success:
                    result.error = "Download failed"
                    result.duration_seconds = time.time() - start
                    return result
                result.downloaded = True

                # 4. PSNR
                result.psnr_db = self._compute_psnr(stego_path, processed_path)

                # 5. Extract
                extract_result = self._engine.extract(processed_path, expected_mode=mode)
                if extract_result is None:
                    result.error = "Extraction returned None"
                    result.duration_seconds = time.time() - start
                    return result
                result.extracted = True
                result.delta_used = extract_result.get("delta_used", 0.0)
                result.ecc_used = extract_result.get("ecc_used", 0)

                # 6. BER
                original_bits = self._message_to_bits(message)
                extracted_msg = extract_result.get("message", "")
                extracted_bits = self._message_to_bits(extracted_msg)
                result.ber = self._compute_ber(original_bits, extracted_bits)

                # 7. Compare message
                result.message_match = (extracted_msg == message)
                if not result.message_match:
                    result.error = f"Message mismatch: got '{extracted_msg[:50]}...'"

            except Exception as e:
                result.error = str(e)
                logger.error(f"Validation error for {platform}/{mode_name}: {e}")

            result.duration_seconds = time.time() - start
            return result

    def _file_hash(self, path: str) -> str:
        """Compute SHA-256 of file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def run_full_benchmark(self, cover_path: str, message: str,
                           modes: Optional[List[StegoMode]] = None) -> BenchmarkReport:
        """Run complete benchmark across all available adapters and modes."""
        if modes is None:
            modes = [StegoMode.GHOST, StegoMode.PHANTOM, StegoMode.ARMOR, StegoMode.FORTRESS]

        report = BenchmarkReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            cover_image=cover_path,
            message_length=len(message.encode("utf-8")),
        )

        if not self.adapters:
            logger.warning("No platform adapters available.")
            report.summary = {
                "status": "no_adapters",
                "message": "No adapters available. Set environment variables.",
            }
            return report

        for adapter in self.adapters:
            platform = adapter.platform_name()
            logger.info(f"Testing platform: {platform}")
            for mode in modes:
                if mode in (StegoMode.ARMOR, StegoMode.FORTRESS):
                    try:
                        import reedsolo
                    except ImportError:
                        reason = "reedsolo not installed (required for ECC in ARMOR/FORTRESS)"
                        logger.info(f"Skipping {platform}/{mode.name} ({reason})")
                        report.skipped.append({
                            "platform": platform, "mode": mode.name, "reason": reason,
                        })
                        continue
                result = self.test_platform(adapter, cover_path, message, mode)
                report.results.append(result)
                status = "✓" if result.message_match else "✗"
                logger.info(
                    f"  [{status}] {platform:12} / {mode.name:10} | "
                    f"PSNR={result.psnr_db:.1f}dB | BER={result.ber:.3f} | "
                    f"Match={result.message_match}"
                )

        report.summary = report.aggregate_stats()
        if report.skipped:
            report.summary["skipped_count"] = len(report.skipped)
            report.summary["skipped"] = report.skipped
        return report

    def run_reproducible_benchmark(self, cover_path: str, message: str,
                                    iterations: int = 10,
                                    seed: Optional[int] = None,
                                    modes: Optional[List[StegoMode]] = None) -> BenchmarkReport:
        """
        Run N-iteration reproducible benchmark.

        Each iteration uses the same cover and message (deterministic),
        but tests all platform/mode combinations.

        Args:
            iterations: Number of repetitions
            seed: Random seed for reproducibility (affects carrier generation if needed)
            modes: Modes to test
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        report = BenchmarkReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            seed=seed,
            iterations=iterations,
            cover_image=cover_path,
            message_length=len(message.encode("utf-8")),
        )

        if modes is None:
            modes = [StegoMode.GHOST, StegoMode.PHANTOM, StegoMode.ARMOR, StegoMode.FORTRESS]

        if not self.adapters:
            report.summary = {"status": "no_adapters"}
            return report

        for i in range(1, iterations + 1):
            logger.info(f"=== Iteration {i}/{iterations} ===")
            for adapter in self.adapters:
                platform = adapter.platform_name()
                for mode in modes:
                    if mode in (StegoMode.ARMOR, StegoMode.FORTRESS):
                        try:
                            import reedsolo
                        except ImportError:
                            continue
                    result = self.test_platform(adapter, cover_path, message, mode, iteration=i)
                    report.results.append(result)

        report.summary = report.aggregate_stats()
        report.summary["iterations"] = iterations
        report.summary["seed"] = seed
        return report

    def run_stress_test(self, num_carriers: int = 20,
                         num_messages: int = 5,
                         seed: Optional[int] = None,
                         modes: Optional[List[StegoMode]] = None) -> BenchmarkReport:
        """
        Stress test with multiple random carriers and messages.

        Generates random carriers, embeds random messages, and tests
        all platform/mode combinations.

        Args:
            num_carriers: Number of random cover images to generate
            num_messages: Number of random messages per carrier
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        report = BenchmarkReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            seed=seed,
            stress_test=True,
            num_carriers=num_carriers,
            num_messages=num_messages,
        )

        if modes is None:
            modes = [StegoMode.GHOST, StegoMode.PHANTOM, StegoMode.ARMOR, StegoMode.FORTRESS]

        if not self.adapters:
            report.summary = {"status": "no_adapters"}
            return report

        # Generate carriers and messages
        carriers = []
        messages = []
        for i in range(num_carriers):
            arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
            tmpdir = tempfile.mkdtemp()
            path = os.path.join(tmpdir, f"carrier_{i}.png")
            Image.fromarray(arr).save(path)
            carriers.append(path)

        for i in range(num_messages):
            msg_len = random.randint(10, 500)
            msg = ''.join(random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ",
                k=msg_len
            ))
            messages.append(msg)

        # Run all combinations
        total = len(carriers) * len(messages) * len(self.adapters) * len(modes)
        count = 0
        for carrier_path in carriers:
            for message in messages:
                for adapter in self.adapters:
                    platform = adapter.platform_name()
                    for mode in modes:
                        if mode in (StegoMode.ARMOR, StegoMode.FORTRESS):
                            try:
                                import reedsolo
                            except ImportError:
                                continue
                        count += 1
                        logger.info(f"Stress test {count}/{total}: {platform}/{mode.name}")
                        result = self.test_platform(adapter, carrier_path, message, mode)
                        report.results.append(result)

        report.summary = report.aggregate_stats()
        report.summary["stress_test"] = True
        report.summary["total_combinations"] = total
        return report

    @staticmethod
    def list_available_adapters() -> List[Dict]:
        """List all adapters and their availability status."""
        adapters = []
        adapter_classes = [
            ("telegram", "stegstr.platform.adapters.telegram", "TelegramAdapter"),
            ("imgur", "stegstr.platform.adapters.imgur", "ImgurAdapter"),
            ("discord", "stegstr.platform.adapters.discord", "DiscordAdapter"),
            ("reddit", "stegstr.platform.adapters.reddit", "RedditAdapter"),
            ("instagram", "stegstr.platform.adapters.instagram", "InstagramAdapter"),
            ("twitter", "stegstr.platform.adapters.twitter", "TwitterAdapter"),
            ("whatsapp", "stegstr.platform.adapters.whatsapp", "WhatsAppAdapter"),
        ]
        for name, module, cls_name in adapter_classes:
            try:
                mod = __import__(module, fromlist=[cls_name])
                cls = getattr(mod, cls_name)
                inst = cls()
                adapters.append({
                    "name": name,
                    "available": inst.is_available(),
                    "requires_credentials": inst.requires_credentials(),
                    "description": inst.description(),
                })
            except Exception as e:
                adapters.append({
                    "name": name,
                    "available": False,
                    "requires_credentials": True,
                    "description": f"Error loading: {e}",
                })
        return adapters
