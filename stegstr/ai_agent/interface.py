"""
AI Agent Interface for Stegstr — Tool-calling API for external agents.
"""

import os
import base64
import json
import tempfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.agent.optimizer import StegstrAgent
from stegstr.platform.simulator import PlatformSimulator
from stegstr.analysis.steganalysis import StegAnalyzer


@dataclass
class ToolResult:
    success: bool
    action: str
    data: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "data": self.data,
            "error": self.error,
        }


class AIAgent:
    """
    Stegstr AI Agent exposing tool-callable operations.
    """

    def __init__(self, password: Optional[str] = None):
        self.engine = StegoEngine(password=password)
        self.optimizer = StegstrAgent()
        self.simulator = PlatformSimulator()
        self.analyzer = StegAnalyzer()

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get("action")
        if not action:
            return ToolResult(False, "unknown", {}, "Missing 'action' field").to_dict()

        handlers = {
            "analyze_carrier": self.analyze_carrier,
            "estimate_capacity": self.estimate_capacity,
            "recommend_parameters": self.recommend_parameters,
            "encode": self.encode,
            "decode": self.decode,
            "simulate_platform": self.simulate_platform,
            "auto_optimize": self.auto_optimize,
            "benchmark_detectability": self.benchmark_detectability,
            "list_actions": self.list_actions,
        }

        handler = handlers.get(action)
        if not handler:
            return ToolResult(
                False, action, {}, f"Unknown action: {action}. Use 'list_actions' to see available actions."
            ).to_dict()

        try:
            return handler(request)
        except Exception as e:
            return ToolResult(False, action, {}, str(e)).to_dict()

    def list_actions(self, _request: Dict[str, Any] = None) -> Dict[str, Any]:
        actions = {
            "analyze_carrier": {
                "description": "Analyze texture, dimensions, and format of a carrier image",
                "parameters": {"carrier": "str — path to image file"},
            },
            "estimate_capacity": {
                "description": "Estimate bit capacity for each steganography mode",
                "parameters": {"carrier": "str", "platform": "str — optional"},
            },
            "recommend_parameters": {
                "description": "Get optimizer recommendation",
                "parameters": {"carrier": "str", "message": "str", "platform": "str"},
            },
            "encode": {
                "description": "Embed a message into a carrier image",
                "parameters": {
                    "carrier": "str", "message": "str", "output": "str",
                    "mode": "str — optional", "platform": "str — optional",
                    "password": "str — optional", "delta": "float — optional", "ecc": "int — optional",
                },
            },
            "decode": {
                "description": "Extract a hidden message",
                "parameters": {"stego": "str", "password": "str — optional", "mode": "str — optional"},
            },
            "simulate_platform": {
                "description": "Simulate platform processing",
                "parameters": {"stego": "str", "platform": "str", "message": "str"},
            },
            "auto_optimize": {
                "description": "Run auto-tune",
                "parameters": {"carrier": "str", "message": "str", "platform": "str", "depth": "str"},
            },
            "benchmark_detectability": {
                "description": "Compare detectability",
                "parameters": {"cover": "str", "stego": "str"},
            },
        }
        return ToolResult(True, "list_actions", {"actions": actions}).to_dict()

    def analyze_carrier(self, request: Dict[str, Any]) -> Dict[str, Any]:
        carrier = request["carrier"]
        from PIL import Image
        img = Image.open(carrier)
        arr = img.convert("RGB")
        texture_score = float(arr.convert("L").getextrema()[1] - arr.convert("L").getextrema()[0]) / 255.0
        data = {
            "path": carrier, "format": img.format, "mode": img.mode,
            "size": img.size, "width": img.width, "height": img.height,
            "texture_score": round(texture_score, 4),
            "recommendation": "High texture → better hiding" if texture_score > 0.3 else "Low texture → use PHANTOM",
        }
        return ToolResult(True, "analyze_carrier", data).to_dict()

    def estimate_capacity(self, request: Dict[str, Any]) -> Dict[str, Any]:
        carrier = request["carrier"]
        platform = request.get("platform")
        caps = {}
        for mode in StegoMode:
            if mode == StegoMode.HYBRID:
                continue
            try:
                cap = self.engine.get_capacity(carrier, mode, platform=platform)
                caps[mode.name] = cap
            except Exception as e:
                caps[mode.name] = f"error: {e}"
        best = None
        if platform:
            rec = self.optimizer.recommend_mode(carrier, "X" * 100, platform)
            best = rec.get("mode")
        return ToolResult(True, "estimate_capacity", {"capacities_bytes": caps, "platform": platform, "recommended_mode": best}).to_dict()

    def recommend_parameters(self, request: Dict[str, Any]) -> Dict[str, Any]:
        rec = self.optimizer.recommend_mode(request["carrier"], request["message"], request["platform"])
        return ToolResult(True, "recommend_parameters", rec).to_dict()

    def encode(self, request: Dict[str, Any]) -> Dict[str, Any]:
        mode = StegoMode[request.get("mode", "HYBRID").upper()] if request.get("mode") else StegoMode.HYBRID
        engine = StegoEngine(
            mode=mode, password=request.get("password") or self.engine.password,
            delta_override=request.get("delta"), ecc_override=request.get("ecc")
        )
        meta = engine.embed(request["carrier"], request["message"], request["output"], target_platform=request.get("platform"))
        return ToolResult(True, "encode", meta).to_dict()

    def decode(self, request: Dict[str, Any]) -> Dict[str, Any]:
        engine = StegoEngine(password=request.get("password") or self.engine.password)
        expected = StegoMode[request["mode"].upper()] if request.get("mode") else None
        result = engine.extract(request["stego"], expected_mode=expected)
        if result is None:
            return ToolResult(False, "decode", {}, "Extraction failed").to_dict()
        return ToolResult(True, "decode", result).to_dict()

    def simulate_platform(self, request: Dict[str, Any]) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmpdir:
            processed = os.path.join(tmpdir, "processed.jpg")
            self.simulator.simulate(request["platform"], request["stego"], processed)
            result = self.engine.extract(processed)
            success = result is not None and result.get("message") == request["message"]
            return ToolResult(True, "simulate_platform", {
                "platform": request["platform"], "survived": success,
                "extracted": result.get("message") if result else None,
            }).to_dict()

    def auto_optimize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        result = self.engine.auto_tune(request["carrier"], request["message"], request["platform"], search_depth=request.get("depth", "standard"))
        return ToolResult(True, "auto_optimize", result).to_dict()

    def benchmark_detectability(self, request: Dict[str, Any]) -> Dict[str, Any]:
        report = self.analyzer.compare(request["cover"], request["stego"])
        return ToolResult(True, "benchmark_detectability", report).to_dict()
