"""Heuristic optimizer for steganography parameters."""
from typing import Dict
from stegstr.stego.engine import StegoEngine, StegoMode

class StegstrAgent:
    """Rule-based heuristic engine for parameter recommendation."""

    def recommend_mode(self, cover_path: str, message: str, platform: str) -> Dict:
        engine = StegoEngine()
        cap_f = engine.get_capacity(cover_path, StegoMode.FORTRESS, platform=platform)
        cap_a = engine.get_capacity(cover_path, StegoMode.ARMOR, platform=platform)
        cap_g = engine.get_capacity(cover_path, StegoMode.GHOST, platform=platform)
        msg_len = len(message.encode("utf-8"))

        fits_f = cap_f >= msg_len
        fits_a = cap_a >= msg_len
        fits_g = cap_g >= msg_len

        if platform in ["whatsapp_standard", "instagram"] and fits_f:
            mode = StegoMode.FORTRESS
            delta = 8.0
        elif fits_a:
            mode = StegoMode.ARMOR
            delta = 4.0
        elif fits_g:
            mode = StegoMode.GHOST
            delta = 0.0
        else:
            mode = StegoMode.FORTRESS
            delta = 12.0

        return {
            "mode": mode.name,
            "delta": delta,
            "fits_message": fits_f or fits_a or fits_g,
            "quality_score": 0.8,
            "recommendations": ["Use FORTRESS for maximum robustness", "Use ARMOR for balanced approach"],
        }
