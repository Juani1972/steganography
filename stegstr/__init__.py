"""
Stegstr Next — Robust Steganography for Social Media

v2.2.0 — Evolucion continua
- 5 modos: FORTRESS, ARMOR, GHOST, PHANTOM, HYBRID
- Steganalysis resistance (Chi², RS, SPA)
- Realistic platform simulation (chroma subsampling, progressive JPEG)
- Video steganography (OpenCV)
- Interactive GUI widget (Flask SPA)
- Config wizard para credenciales de redes sociales
"""

__version__ = "2.2.0"
__author__ = "Stegstr Team"
__license__ = "MIT"

from stegstr.stego.engine import StegoEngine, StegoMode

try:
    from stegstr.analysis.steganalysis import StegAnalyzer
    __all__ = ["StegoEngine", "StegoMode", "StegAnalyzer", "__version__"]
except ImportError:
    __all__ = ["StegoEngine", "StegoMode", "__version__"]
