"""
Platform Analyzer v2.1 — Detects transformations applied to images.

Improvements:
- Handles custom quantization tables
- Validates RGB input
- Robust double-compression detection
- Platform estimation with confidence scores
- Block alignment analysis
"""

import numpy as np
from PIL import Image
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PlatformAnalyzer:
    """Analyze received images to detect platform transformations."""

    KNOWN_CUSTOM_TABLES = {
        "instagram": {
            "signature": [16, 11, 10, 16, 24, 40, 51, 61],
            "qf_range": (70, 82),
        },
        "whatsapp": {
            "signature": [10, 7, 6, 10, 15, 25, 32, 38],
            "qf_range": (50, 60),
        },
    }

    def analyze(self, image_path: str) -> Dict:
        img = Image.open(image_path)
        results = {
            "resize_detected": False,
            "recompression_detected": False,
            "estimated_qf": None,
            "qf_confidence": None,
            "format_conversion": False,
            "metadata_stripped": False,
            "likely_platform": None,
            "platform_confidence": None,
            "block_alignment_score": 1.0,
            "original_size": None,
            "current_size": img.size,
            "image_mode": img.mode,
        }

        if img.mode not in ("RGB", "L", "YCbCr"):
            if img.mode == "RGBA":
                logger.warning("RGBA image detected, analysis may be less accurate")
                results["format_conversion"] = True

        if img.format == "JPEG":
            results = self._analyze_jpeg(image_path, results)
        elif img.format == "PNG":
            results = self._analyze_png(image_path, results)
        elif img.format in ("WEBP", "AVIF"):
            results["format_conversion"] = True
            results["recompression_detected"] = True
            results["metadata_stripped"] = self._check_metadata_stripped(image_path)

        results["likely_platform"] = self._estimate_platform(results)
        return results

    def _analyze_jpeg(self, image_path: str, results: Dict) -> Dict:
        try:
            img = Image.open(image_path)
            if hasattr(img, 'quantization'):
                q_tables = img.quantization
                if q_tables:
                    q_table = q_tables.get(0) or list(q_tables.values())[0]
                    qf, confidence = self._estimate_qf_from_table(q_table)
                    results["estimated_qf"] = qf
                    results["qf_confidence"] = confidence
                    results["recompression_detected"] = self._detect_double_compression(image_path)
                    results["block_alignment_score"] = self._check_block_alignment(image_path)
                    if results["block_alignment_score"] < 0.9:
                        results["resize_detected"] = True
        except Exception as e:
            logger.debug(f"JPEG analysis failed: {e}")
        return results

    def _analyze_png(self, image_path: str, results: Dict) -> Dict:
        try:
            img = Image.open(image_path)
            arr = np.array(img.convert("L"), dtype=np.float32)
            block_variance = self._compute_block_variance(arr)
            if block_variance < 0.01:
                results["format_conversion"] = True
                results["recompression_detected"] = True
        except Exception as e:
            logger.debug(f"PNG analysis failed: {e}")
        return results

    def _estimate_qf_from_table(self, q_table) -> tuple:
        if isinstance(q_table, bytes):
            q_table = list(q_table)
        q_table = np.array(q_table[:64])
        std_table_50 = np.array([
            16, 11, 10, 16, 24, 40, 51, 61,
            12, 12, 14, 19, 26, 58, 60, 55,
            14, 13, 16, 24, 40, 57, 69, 56,
            14, 17, 22, 29, 51, 87, 80, 62,
            18, 22, 37, 56, 68, 109, 103, 77,
            24, 35, 55, 64, 81, 104, 113, 92,
            49, 64, 78, 87, 103, 121, 120, 101,
            72, 92, 95, 98, 112, 100, 103, 99
        ])

        for platform, info in self.KNOWN_CUSTOM_TABLES.items():
            sig = np.array(info["signature"])
            if len(q_table) >= len(sig):
                correlation = np.corrcoef(q_table[:len(sig)], sig)[0, 1]
                if correlation > 0.95:
                    qf = np.median(info["qf_range"])
                    return qf, 0.9

        scale = np.median(q_table / (std_table_50 + 1e-10))
        if scale <= 1.0:
            qf = max(1, int(50 / (scale + 1e-10)))
        else:
            qf = max(1, int(50 - (scale - 1) * 25))
        qf = min(100, qf)
        predicted_table = std_table_50 * scale
        mse = np.mean((q_table - predicted_table) ** 2)
        confidence = max(0.3, 1.0 - mse / 1000)
        return qf, confidence

    def _detect_double_compression(self, image_path: str) -> bool:
        try:
            img = Image.open(image_path).convert("L")
            arr = np.array(img, dtype=np.float32)
            h, w = arr.shape
            h = (h // 8) * 8
            w = (w // 8) * 8
            arr = arr[:h, :w]
            from scipy.fftpack import dct
            coeffs = []
            for i in range(0, h, 8):
                for j in range(0, w, 8):
                    block = arr[i:i+8, j:j+8]
                    dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
                    coeffs.append(dct_block[1, 2])
            coeffs = np.array(coeffs)
            from scipy.ndimage import median_filter
            coeffs_filtered = median_filter(coeffs, size=5)
            hist, _ = np.histogram(coeffs_filtered, bins=50)
            if len(hist) > 10:
                autocorr = np.correlate(hist - np.mean(hist), hist - np.mean(hist), mode='full')
                autocorr = autocorr[len(autocorr)//2:]
                if len(autocorr) > 5:
                    peaks = np.argsort(autocorr[1:6])[-2:]
                    if autocorr[peaks[0] + 1] > 0.3 * autocorr[0]:
                        return True
            return False
        except Exception as e:
            logger.debug(f"Double compression detection failed: {e}")
            return False

    def _check_block_alignment(self, image_path: str) -> float:
        try:
            img = Image.open(image_path).convert("L")
            arr = np.array(img, dtype=np.float32)
            h, w = arr.shape
            h_scores = []
            for i in range(8, h-8, 8):
                diff = np.abs(arr[i, :] - arr[i-1, :])
                h_scores.append(np.mean(diff))
            v_scores = []
            for j in range(8, w-8, 8):
                diff = np.abs(arr[:, j] - arr[:, j-1])
                v_scores.append(np.mean(diff))
            random_h = [np.mean(np.abs(arr[np.random.randint(8, h-8), :] - arr[np.random.randint(8, h-8), :])) for _ in range(10)]
            random_v = [np.mean(np.abs(arr[:, np.random.randint(8, w-8)] - arr[:, np.random.randint(8, w-8)])) for _ in range(10)]
            if not h_scores or not random_h:
                return 1.0
            block_score = (np.mean(h_scores) + np.mean(v_scores)) / 2
            random_score = (np.mean(random_h) + np.mean(random_v)) / 2
            if random_score > 0:
                alignment = 1.0 - min(1.0, block_score / random_score)
            else:
                alignment = 1.0
            return alignment
        except Exception as e:
            logger.debug(f"Block alignment check failed: {e}")
            return 1.0

    def _compute_block_variance(self, arr: np.ndarray) -> float:
        h, w = arr.shape
        h = (h // 8) * 8
        w = (w // 8) * 8
        arr = arr[:h, :w]
        block_avgs = []
        for i in range(0, h, 8):
            for j in range(0, w, 8):
                block = arr[i:i+8, j:j+8]
                block_avgs.append(np.mean(block))
        return np.var(block_avgs)

    def _check_metadata_stripped(self, image_path: str) -> bool:
        try:
            img = Image.open(image_path)
            if hasattr(img, '_getexif') and img._getexif():
                return False
            if hasattr(img, 'info') and img.info:
                if any(k not in ('gamma', 'dpi') for k in img.info.keys()):
                    return False
            return True
        except:
            return True

    def _estimate_platform(self, results: Dict) -> Optional[str]:
        qf = results.get("estimated_qf")
        resize = results.get("resize_detected")
        confidence = results.get("qf_confidence", 0.5)
        if qf is None:
            if results.get("format_conversion"):
                return "unknown_converted"
            return None
        platform_scores = {}
        if resize and qf < 65:
            platform_scores["whatsapp_standard"] = 0.9
        elif resize and qf < 80:
            platform_scores["instagram"] = 0.85
        elif not resize and 78 <= qf <= 85:
            platform_scores["telegram_photo"] = 0.8
        elif not resize and qf >= 85:
            platform_scores["twitter"] = 0.75
        elif not resize and 70 <= qf < 78:
            platform_scores["whatsapp_hd"] = 0.7
        elif resize and qf >= 80:
            platform_scores["facebook"] = 0.6
        if platform_scores:
            best_platform = max(platform_scores, key=platform_scores.get)
            best_score = platform_scores[best_platform]
            results["platform_confidence"] = best_score * confidence
            return best_platform
        results["platform_confidence"] = 0.3
        return None
