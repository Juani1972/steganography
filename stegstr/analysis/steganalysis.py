"""
Stegstr Steganalysis Module v2.1.3 — Fase 6

Detectores estadísticos para evaluar la detectabilidad de mensajes ocultos:
  - Chi-square (χ²) attack on LSB
  - RS (Regular-Singular) analysis
  - Sample Pairs Analysis (SPA)
  - Entropy analysis
  - KL divergence estimation

Uso:
    from stegstr.analysis.steganalysis import StegAnalyzer
    analyzer = StegAnalyzer()
    report = analyzer.analyze("stego.png")
    print(report["chi2_p_value"])  # p > 0.05 = no detectable
"""

import numpy as np
from PIL import Image
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class StegAnalyzer:
    """Statistical steganalysis detectors."""

    # ------------------------------------------------------------------
    # Chi-square attack (Westfeld, 2001)
    # ------------------------------------------------------------------
    @staticmethod
    def chi2_attack(image_path: str, channel: int = 0) -> Dict:
        """
        Chi-square attack on LSB plane.
        For RGB images, analyzes all three channels and returns the minimum p-value
        (most suspicious channel drives the detection).
        Low p-value suggests non-random LSB distribution (stego detected).
        """
        from scipy.stats import chi2 as chi2_dist
        img = Image.open(image_path).convert("RGB")
        arr = np.array(img)

        def _chi2_single(ch):
            flat = arr[:, :, ch].flatten()
            hist, _ = np.histogram(flat, bins=256, range=(0, 256))
            observed = []
            expected = []
            for i in range(0, 256, 2):
                o1 = hist[i]
                o2 = hist[i + 1]
                exp = (o1 + o2) / 2.0
                if exp > 0:
                    observed.append(o1)
                    expected.append(exp)
                    observed.append(o2)
                    expected.append(exp)

            observed = np.array(observed, dtype=np.float64)
            expected = np.array(expected, dtype=np.float64)
            mask = expected > 0
            chi2_stat = np.sum(((observed[mask] - expected[mask]) ** 2) / expected[mask])
            dof = np.sum(mask) - 1
            p_value = 1.0 - chi2_dist.cdf(chi2_stat, max(dof, 1))
            return chi2_stat, p_value

        # Analyze all RGB channels
        all_results = []
        for ch in range(3):
            stat, p = _chi2_single(ch)
            all_results.append({"channel": ch, "chi2_statistic": float(stat), "chi2_p_value": float(p)})

        # Use minimum p-value (most detectable channel)
        min_p = min(r["chi2_p_value"] for r in all_results)
        max_stat = max(r["chi2_statistic"] for r in all_results)

        return {
            "chi2_statistic": float(max_stat),
            "chi2_dof": 255,
            "chi2_p_value": float(min_p),
            "detected": min_p < 0.05,
            "per_channel": all_results,
        }

    # ------------------------------------------------------------------
    # RS Analysis (Fridrich et al., 2001)
    # ------------------------------------------------------------------
    @staticmethod
    def rs_analysis(image_path: str, channel: int = 0, mask: Tuple[int, ...] = (1, 0, 1, 0)) -> Dict:
        """
        Regular-Singular analysis for LSB steganography.
        Estimates embedding rate by comparing Rm, Sm, R-m, S-m groups.
        Returns estimated embedding rate (0.0 = clean, ~1.0 = fully embedded).
        For RGB images, analyzes all channels and returns the average rate.
        """
        img = Image.open(image_path).convert("RGB")
        full_arr = np.array(img)
        mask = np.array(mask)
        m_len = len(mask)

        def flip_lsb(x):
            return x ^ 1

        def flip_neg(x):
            return x ^ 1 if x % 2 == 0 else x

        def apply_f(g):
            return np.sum(np.abs(np.diff(g)))

        def apply_mask(group, mask_vec, flip_func):
            g = group.copy()
            for i in range(min(len(g), len(mask_vec))):
                if mask_vec[i] == 1:
                    g[i] = flip_func(g[i])
            return g

        def _rs_single(arr_2d):
            arr = arr_2d.astype(np.int32)
            h, w = arr.shape
            flat = arr.flatten()
            groups = []
            for i in range(0, len(flat) - m_len + 1, m_len):
                groups.append(flat[i:i + m_len])

            Rm, Sm, Rm_, Sm_ = 0, 0, 0, 0
            for g in groups:
                f0 = apply_f(g)
                gm = apply_mask(g, mask, flip_lsb)
                fm = apply_f(gm)
                gm_ = apply_mask(g, mask, flip_neg)
                fm_ = apply_f(gm_)

                if fm > f0:
                    Rm += 1
                elif fm < f0:
                    Sm += 1
                if fm_ > f0:
                    Rm_ += 1
                elif fm_ < f0:
                    Sm_ += 1

            total = len(groups)
            if total == 0:
                return 0.0, total, Rm, Sm, Rm_, Sm_

            d0 = float(Rm - Sm)
            d1 = float(Rm_ - Sm_)
            if d0 == 0:
                rate = 0.0
            else:
                a = 2 * (d1 - d0)
                b = d0 - d1
                c = d0
                if a != 0:
                    disc = b * b - 4 * a * c
                    if disc >= 0:
                        x1 = (-b + np.sqrt(disc)) / (2 * a)
                        x2 = (-b - np.sqrt(disc)) / (2 * a)
                        rate = min(abs(x1), abs(x2))
                    else:
                        rate = 0.0
                else:
                    rate = 0.0
            rate = float(np.clip(rate, 0.0, 1.0))
            return rate, total, Rm, Sm, Rm_, Sm_

        # Analyze all 3 RGB channels and average
        rates = []
        totals = []
        for ch in range(3):
            rate, total, Rm, Sm, Rm_, Sm_ = _rs_single(full_arr[:, :, ch])
            rates.append(rate)
            totals.append(total)

        avg_rate = float(np.mean(rates))
        max_total = max(totals)

        return {
            "rs_embedding_rate": round(avg_rate, 4),
            "rs_groups": max_total,
            "detected": avg_rate > 0.1,
            "per_channel_rates": [round(r, 4) for r in rates],
        }

    # ------------------------------------------------------------------
    # Sample Pairs Analysis (SPA)
    # ------------------------------------------------------------------
    @staticmethod
    def spa_analysis(image_path: str, channel: int = 0) -> Dict:
        """
        Sample Pairs Analysis — estimates LSB embedding rate.
        For RGB images, analyzes all channels and returns average rate.
        """
        img = Image.open(image_path).convert("RGB")
        full_arr = np.array(img)

        def _spa_single(arr_1d):
            arr = arr_1d.astype(np.int32).flatten()
            u = arr[0::2]
            v = arr[1::2]
            P = Q = Z = 0
            for a, b in zip(u, v):
                if a < b:
                    P += 1
                elif a > b:
                    Q += 1
                else:
                    Z += 1
            total = len(u)
            if total == 0:
                return 0.0, total
            rate = abs(P - Q) / max(total - Z, 1)
            return float(np.clip(rate, 0.0, 1.0)), total

        rates = []
        totals = []
        for ch in range(3):
            rate, total = _spa_single(full_arr[:, :, ch])
            rates.append(rate)
            totals.append(total)

        avg_rate = float(np.mean(rates))
        return {
            "spa_rate": round(avg_rate, 4),
            "spa_pairs": max(totals),
            "spa_detected": avg_rate > 0.15,
            "per_channel_rates": [round(r, 4) for r in rates],
        }

    # ------------------------------------------------------------------
    # Entropy analysis
    # ------------------------------------------------------------------
    @staticmethod
    def entropy_analysis(image_path: str, channel: int = 0) -> Dict:
        """Compare entropy of cover vs LSB plane. Analyzes all RGB channels."""
        img = Image.open(image_path).convert("RGB")
        full_arr = np.array(img)

        entropy_full_vals = []
        entropy_lsb_vals = []
        p1_vals = []

        for ch in range(3):
            arr = full_arr[:, :, ch].flatten()
            hist_full, _ = np.histogram(arr, bins=256, range=(0, 256), density=True)
            hist_full = hist_full[hist_full > 0]
            ent_full = -np.sum(hist_full * np.log2(hist_full))
            entropy_full_vals.append(ent_full)

            lsb = arr & 1
            p1 = np.mean(lsb)
            p0 = 1 - p1
            if p0 > 0 and p1 > 0:
                ent_lsb = -(p0 * np.log2(p0) + p1 * np.log2(p1))
            else:
                ent_lsb = 0.0
            entropy_lsb_vals.append(ent_lsb)
            p1_vals.append(p1)

        avg_p1 = float(np.mean(p1_vals))
        avg_ent_full = float(np.mean(entropy_full_vals))
        avg_ent_lsb = float(np.mean(entropy_lsb_vals))

        return {
            "entropy_full": round(avg_ent_full, 4),
            "entropy_lsb": round(avg_ent_lsb, 4),
            "lsb_balance": round(avg_p1, 4),
            "detected": abs(avg_p1 - 0.5) < 0.01 and avg_ent_lsb > 0.99,
            "per_channel_balance": [round(p, 4) for p in p1_vals],
        }

    # ------------------------------------------------------------------
    # Combined analysis
    # ------------------------------------------------------------------
    def analyze(self, image_path: str) -> Dict:
        """Run all detectors and return combined report."""
        chi2 = self.chi2_attack(image_path)
        rs = self.rs_analysis(image_path)
        spa = self.spa_analysis(image_path)
        ent = self.entropy_analysis(image_path)

        # Combined score: weighted average of detection indicators
        scores = [
            1.0 if chi2["detected"] else 0.0,
            rs["rs_embedding_rate"],
            1.0 if spa["spa_detected"] else 0.0,
            1.0 if ent["detected"] else 0.0,
        ]
        combined_score = float(np.mean(scores))

        return {
            "image": image_path,
            "combined_detection_score": round(combined_score, 4),
            "likely_stego": combined_score > 0.3,
            "chi2": chi2,
            "rs": rs,
            "spa": spa,
            "entropy": ent,
        }

    # ------------------------------------------------------------------
    # Compare cover vs stego
    # ------------------------------------------------------------------
    def compare(self, cover_path: str, stego_path: str) -> Dict:
        """Compare statistical profiles of cover and stego images."""
        cover_report = self.analyze(cover_path)
        stego_report = self.analyze(stego_path)

        return {
            "cover": {
                "chi2_p": cover_report["chi2"]["chi2_p_value"],
                "rs_rate": cover_report["rs"]["rs_embedding_rate"],
                "spa_rate": cover_report["spa"]["spa_rate"],
                "entropy_lsb": cover_report["entropy"]["entropy_lsb"],
            },
            "stego": {
                "chi2_p": stego_report["chi2"]["chi2_p_value"],
                "rs_rate": stego_report["rs"]["rs_embedding_rate"],
                "spa_rate": stego_report["spa"]["spa_rate"],
                "entropy_lsb": stego_report["entropy"]["entropy_lsb"],
            },
            "increased_detectability": stego_report["combined_detection_score"] > cover_report["combined_detection_score"],
            "recommendation": (
                "HIGH RISK: stego is easily detectable" if stego_report["combined_detection_score"] > 0.5
                else "MODERATE: some statistical artifacts present" if stego_report["combined_detection_score"] > 0.2
                else "LOW: stego appears statistically natural"
            ),
        }
