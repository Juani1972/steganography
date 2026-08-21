#!/usr/bin/env python3
"""
Stegstr Widget Server v2.2.0

Servidor Flask ligero dedicado al widget visual.
Expone endpoints REST JSON que consume el frontend SPA (widget.html).

Uso:
    python -m stegstr.gui.widget_server
    # o
    python stegstr/gui/widget_server.py

    Abre http://127.0.0.1:8080 en el navegador.

Endpoints:
    GET  /              → Sirve widget.html
    GET  /health        → Estado del backend {version, status}
    POST /embed         → Ocultar mensaje
    POST /extract       → Extraer mensaje
    POST /capacity      → Calcular capacidad
    POST /analyze       → Análisis de detectabilidad
    POST /simulate      → Simular procesamiento de plataforma
    POST /benchmark     → Benchmark rápido por modo
    POST /optimize      → Auto-tune de parámetros
"""

import os
import sys
import time
import tempfile
import base64
from io import BytesIO
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("ERROR: Flask no está instalado. Ejecuta: pip install flask flask-cors")
    sys.exit(1)

from PIL import Image
from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.simulator import PlatformSimulator
from stegstr.platform.simulator_v2 import RealisticPlatformSimulator
from stegstr.analysis.steganalysis import StegAnalyzer

app = Flask(__name__, static_folder=".")
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/*": {"origins": "*"}})

WIDGET_HTML = Path(__file__).parent / "widget.html"
APP_VERSION = "2.2.0"

# ── Helpers ──

def _img_to_b64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = BytesIO()
    img.save(buf, format=fmt)
    return "data:image/" + fmt.lower() + ";base64," + base64.b64encode(buf.getvalue()).decode()

def _b64_to_img(b64: str) -> Image.Image:
    if "," in b64:
        b64 = b64.split(",")[1]
    return Image.open(BytesIO(base64.b64decode(b64)))

def _file_to_img(file_storage) -> Image.Image:
    return Image.open(file_storage.stream)

def _img_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

def _mode_from_str(s: str) -> StegoMode:
    return StegoMode[s.upper()]

def _cors_jsonify(data, status=200):
    resp = jsonify(data)
    resp.status_code = status
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

# ── Routes ──

@app.route("/")
def index():
    """Serve the widget SPA."""
    if WIDGET_HTML.exists():
        return send_from_directory(WIDGET_HTML.parent, WIDGET_HTML.name)
    return "<h1>Stegstr Widget v2.2.0</h1><p>widget.html not found</p>", 404

@app.route("/health")
def health():
    return _cors_jsonify({"status": "ok", "version": APP_VERSION, "widget": True})

@app.route("/embed", methods=["POST"])
def embed():
    t0 = time.perf_counter()
    try:
        cover_file = request.files.get("cover")
        message = request.form.get("message", "")
        mode_str = request.form.get("mode", "HYBRID")
        platform = request.form.get("platform", "")
        delta = request.form.get("delta", "")
        ecc = request.form.get("ecc", "")
        password = request.form.get("password", "")
        autotune = request.form.get("autotune", "false").lower() == "true"

        if not cover_file:
            return _cors_jsonify({"success": False, "error": "No cover image provided"}, 400)
        if not message:
            return _cors_jsonify({"success": False, "error": "No message provided"}, 400)

        cover_img = _file_to_img(cover_file)
        tmpdir = tempfile.mkdtemp()
        cover_path = os.path.join(tmpdir, "cover.png")
        cover_img.save(cover_path, "PNG")

        # Auto-tune
        if autotune and platform:
            engine = StegoEngine(password=password or None)
            tune = engine.auto_tune(cover_path, message, platform, search_depth="standard")
            mode = tune.get("mode", StegoMode.ARMOR)
            delta_val = tune.get("delta", 8.0)
            ecc_val = tune.get("ecc", 48)
        else:
            mode = _mode_from_str(mode_str) if mode_str else StegoMode.HYBRID
            delta_val = float(delta) if delta else None
            ecc_val = int(ecc) if ecc else None

        engine = StegoEngine(
            mode=mode,
            password=password or None,
            delta_override=delta_val,
            ecc_override=ecc_val
        )

        stego_path = os.path.join(tmpdir, "stego.png")
        meta = engine.embed(
            cover_path, message, stego_path,
            mode=mode if mode != StegoMode.HYBRID else None,
            target_platform=platform or None,
            delta_override=delta_val,
            ecc_override=ecc_val
        )

        stego_img = Image.open(stego_path)
        stego_b64 = _img_to_b64(stego_img, "PNG")

        return _cors_jsonify({
            "success": True,
            "stego_url": stego_b64,
            "mode": meta.get("mode"),
            "delta_used": meta.get("delta_used"),
            "ecc_used": meta.get("ecc_used"),
            "quality_metrics": meta.get("quality_metrics", {}),
            "capacity_bits": meta.get("capacity_bits"),
            "time_ms": int((time.perf_counter() - t0) * 1000),
        })
    except Exception as e:
        return _cors_jsonify({"success": False, "error": str(e)}, 500)

@app.route("/extract", methods=["POST"])
def extract():
    try:
        stego_file = request.files.get("stego")
        password = request.form.get("password", "")
        mode_str = request.form.get("mode", "")

        if not stego_file:
            return _cors_jsonify({"success": False, "error": "No stego image provided"}, 400)

        stego_img = _file_to_img(stego_file)
        tmpdir = tempfile.mkdtemp()
        stego_path = os.path.join(tmpdir, "stego.png")
        stego_img.save(stego_path, "PNG")

        engine = StegoEngine(password=password or None)
        expected_mode = _mode_from_str(mode_str) if mode_str else None

        result = engine.extract(stego_path, expected_mode=expected_mode)
        if result is None:
            return _cors_jsonify({"success": False, "error": "No hidden message found, or incorrect password/mode"}, 404)

        return _cors_jsonify({
            "success": True,
            "message": result.get("message"),
            "mode": result.get("mode"),
            "delta_used": result.get("delta_used"),
            "encoding": result.get("encoding", "utf-8"),
        })
    except Exception as e:
        return _cors_jsonify({"success": False, "error": str(e)}, 500)

@app.route("/capacity", methods=["POST"])
def capacity():
    try:
        cover_file = request.files.get("cover")
        mode_str = request.form.get("mode", "ARMOR")
        platform = request.form.get("platform", "")
        ecc_str = request.form.get("ecc", "")

        if not cover_file:
            return _cors_jsonify({"success": False, "error": "No cover image provided"}, 400)

        cover_img = _file_to_img(cover_file)
        tmpdir = tempfile.mkdtemp()
        cover_path = os.path.join(tmpdir, "cover.png")
        cover_img.save(cover_path, "PNG")

        mode = _mode_from_str(mode_str)
        ecc = int(ecc_str) if ecc_str else None

        engine = StegoEngine()
        cap = engine.get_capacity(cover_path, mode, platform=platform or None, ecc_bytes=ecc)

        # Raw capacity (without ECC overhead)
        w, h = cover_img.size
        w = (w // 8) * 8
        h = (h // 8) * 8
        if mode == StegoMode.FORTRESS:
            raw = (h // 8 // 2) * (w // 8 // 2)
        elif mode == StegoMode.ARMOR:
            raw = (h // 8) * (w // 8) * 5
        else:
            raw = w * h
        overhead = raw - cap * 8

        return _cors_jsonify({
            "success": True,
            "capacity_bytes": cap,
            "raw_capacity": raw // 8,
            "overhead": max(0, overhead) // 8,
            "mode": mode.name,
            "platform": platform or None,
            "ecc": ecc,
        })
    except Exception as e:
        return _cors_jsonify({"success": False, "error": str(e)}, 500)

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        cover_file = request.files.get("cover")
        stego_file = request.files.get("stego")

        if not cover_file or not stego_file:
            return _cors_jsonify({"success": False, "error": "Both cover and stego images required"}, 400)

        cover_img = _file_to_img(cover_file)
        stego_img = _file_to_img(stego_file)
        tmpdir = tempfile.mkdtemp()
        cover_path = os.path.join(tmpdir, "cover.png")
        stego_path = os.path.join(tmpdir, "stego.png")
        cover_img.save(cover_path, "PNG")
        stego_img.save(stego_path, "PNG")

        analyzer = StegAnalyzer()
        report = analyzer.compare(cover_path, stego_path)

        return _cors_jsonify({
            "success": True,
            "report": report,
        })
    except Exception as e:
        return _cors_jsonify({"success": False, "error": str(e)}, 500)

@app.route("/simulate", methods=["POST"])
def simulate():
    try:
        image_file = request.files.get("image")
        platform = request.form.get("platform", "")

        if not image_file or not platform:
            return _cors_jsonify({"success": False, "error": "Image and platform required"}, 400)

        img = _file_to_img(image_file)
        tmpdir = tempfile.mkdtemp()
        input_path = os.path.join(tmpdir, "input.png")
        output_path = os.path.join(tmpdir, "output.jpg")
        img.save(input_path, "PNG")

        sim = RealisticPlatformSimulator()
        result = sim.simulate(platform, input_path, output_path)

        return _cors_jsonify({
            "success": True,
            "transformations": result.get("transformations", []),
            "platform": platform,
        })
    except Exception as e:
        return _cors_jsonify({"success": False, "error": str(e)}, 500)

@app.route("/benchmark", methods=["POST"])
def benchmark():
    t0 = time.perf_counter()
    try:
        cover_file = request.files.get("cover")
        message = request.form.get("message", "Benchmark test message")
        mode_str = request.form.get("mode", "ARMOR")

        if not cover_file:
            return _cors_jsonify({"success": False, "error": "No cover image provided"}, 400)

        cover_img = _file_to_img(cover_file)
        tmpdir = tempfile.mkdtemp()
        cover_path = os.path.join(tmpdir, "cover.png")
        stego_path = os.path.join(tmpdir, "stego.png")
        cover_img.save(cover_path, "PNG")

        mode = _mode_from_str(mode_str)
        engine = StegoEngine(mode=mode)
        meta = engine.embed(cover_path, message, stego_path)
        result = engine.extract(stego_path, expected_mode=mode)

        return _cors_jsonify({
            "success": True,
            "mode": mode.name,
            "capacity_bytes": meta.get("capacity_bits", 0) // 8,
            "time_ms": int((time.perf_counter() - t0) * 1000),
            "quality_metrics": meta.get("quality_metrics", {}),
            "extracted_ok": result is not None and result.get("message") == message,
        })
    except Exception as e:
        return _cors_jsonify({"success": False, "error": str(e)}, 500)

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        cover_file = request.files.get("cover")
        message = request.form.get("message", "")
        platform = request.form.get("platform", "telegram_photo")
        depth = request.form.get("depth", "standard")

        if not cover_file:
            return _cors_jsonify({"success": False, "error": "No cover image provided"}, 400)

        cover_img = _file_to_img(cover_file)
        tmpdir = tempfile.mkdtemp()
        cover_path = os.path.join(tmpdir, "cover.png")
        cover_img.save(cover_path, "PNG")

        engine = StegoEngine()
        tune = engine.auto_tune(cover_path, message, platform, search_depth=depth)

        return _cors_jsonify({
            "success": True,
            "recommendation": {
                "mode": tune.get("mode", {}).name if hasattr(tune.get("mode"), "name") else str(tune.get("mode")),
                "delta": tune.get("delta"),
                "ecc": tune.get("ecc"),
                "psnr_db": tune.get("psnr_db"),
                "success": tune.get("success"),
                "candidates_tested": tune.get("candidates_tested"),
            }
        })
    except Exception as e:
        return _cors_jsonify({"success": False, "error": str(e)}, 500)

# ── Main ──

def main():
    print("=" * 60)
    print(" Stegstr Widget Server v2.2.0")
    print("=" * 60)
    print(f"Serving widget from: {WIDGET_HTML}")
    print("Open http://127.0.0.1:8080 in your browser")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    app.run(host="127.0.0.1", port=8080, debug=False)

if __name__ == "__main__":
    main()
