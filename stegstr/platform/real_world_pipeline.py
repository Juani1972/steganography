"""
Real-World Platform Pipeline — Wrapper sobre PlatformSimulator existente.
Expone API de bytes para el servidor + metadatos descriptivos.
"""

import io
import tempfile
from pathlib import Path
from typing import Dict, List

from PIL import Image

from stegstr.platform.simulator import PlatformSimulator


class PlatformPipeline:
    """
    Wrapper sobre PlatformSimulator que añade:
    - Procesamiento desde bytes (para API server)
    - Descripciones de pipeline
    - Estimación de supervivencia
    """

    PIPELINE_DESCRIPTIONS = {
        "whatsapp_standard": "WhatsApp Standard: JPEG QF55, 1600px max, metadata stripped",
        "whatsapp_hd": "WhatsApp HD: JPEG QF75, 5120px max",
        "telegram_photo": "Telegram Photo: JPEG QF82, 2560px max",
        "telegram_file": "Telegram File: No compression, original preserved",
        "instagram": "Instagram: Double JPEG, 1:1 crop, 1080px, unsharp mask",
        "twitter": "Twitter/X: JPEG QF85, 4096px max, 5MB limit",
        "facebook": "Facebook: JPEG QF80, 2048px max, unsharp mask",
        "signal": "Signal: JPEG QF95, 4096px max, minimal processing",
        "linkedin": "LinkedIn: JPEG QF85, 7680px max",
        "reddit": "Reddit: JPEG QF90, 8192px max",
    }

    def __init__(self, platform: str):
        if platform not in self.PIPELINE_DESCRIPTIONS:
            raise ValueError(f"Unknown platform: {platform}. Available: {list(self.PIPELINE_DESCRIPTIONS.keys())}")
        self.platform = platform
        self._simulator = PlatformSimulator()

    def get_pipeline_description(self) -> str:
        return self.PIPELINE_DESCRIPTIONS[self.platform]

    def process(self, image_data: bytes) -> bytes:
        """
        Apply platform processing to image bytes.
        Uses existing PlatformSimulator under the hood.
        """
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as in_tmp:
            in_tmp.write(image_data)
            input_path = in_tmp.name

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as out_tmp:
            output_path = out_tmp.name

        try:
            self._simulator.simulate(self.platform, input_path, output_path)
            with open(output_path, "rb") as f:
                return f.read()
        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def process_file(self, input_path: str, output_path: str) -> str:
        """Process file path to file path (delegates to simulator)."""
        return self._simulator.simulate(self.platform, input_path, output_path)

    @classmethod
    def list_platforms(cls) -> List[Dict]:
        return [
            {"name": k, "description": v}
            for k, v in cls.PIPELINE_DESCRIPTIONS.items()
        ]

    def estimate_survival(self, mode: str, payload_size: int) -> float:
        """Estimate survival probability based on mode, platform, and payload size."""
        base_rates = {
            "FORTRESS": 0.95, "ARMOR": 0.85, "GHOST": 0.40,
            "PHANTOM": 0.75, "HYBRID": 0.80
        }
        platform_factors = {
            "whatsapp_standard": 0.70, "whatsapp_hd": 0.85,
            "instagram": 0.60, "telegram_photo": 0.80,
            "telegram_file": 1.00, "twitter": 0.75,
            "facebook": 0.70, "signal": 0.90,
            "linkedin": 0.80, "reddit": 0.85
        }
        size_penalty = min(1.0, max(0.0, 1.0 - (payload_size / 50000)))

        base = base_rates.get(mode, 0.5)
        factor = platform_factors.get(self.platform, 0.5)

        return base * factor * size_penalty
