#!/usr/bin/env python3
"""
Stegstr Widget Server v2.2.0 (PATCHED)

Servidor Flask ligero dedicado al widget visual.
Expone endpoints REST JSON que consume el frontend SPA (widget.html).

CAMBIOS v2.2.0:
- Corregido import de NostrAdapter (ahora existe en adapters/__init__.py)
- Corregido constructor de InstagramAdapter (account_id + access_token)
- Corregido constructor de WhatsAppAdapter (phone_id + access_token + recipient_phone)
- Validación E2E ahora compara mensaje original con extraído
- caption ahora se pasa al adaptador cuando es posible
- CORS restringido a 127.0.0.1
- Añadido rate limiting básico y límite de tamaño de archivo
- Modos de estego sincronizados con StegoMode (eliminados STANDARD/AGGRESSIVE)

Uso:
    python -m stegstr.gui.widget_server
    Abre http://127.0.0.1:8080 en el navegador.
"""

import os
import sys
import time
import tempfile
import base64
import hashlib
import traceback
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any

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

try:
    from stegstr.platform.adapters import (
        TelegramAdapter, DiscordAdapter, ImgurAdapter,
        RedditAdapter, TwitterAdapter, InstagramAdapter,
        WhatsAppAdapter, NostrAdapter,
    )
    HAS_ADAPTERS = True
except ImportError:
    HAS_ADAPTERS = False
    print("[WARN] No se pudieron importar los adaptadores de plataforma.")

app = Flask(__name__, static_folder=".")
CORS(app, resources={
    r"/api/*": {"origins": ["http://127.0.0.1:8080", "http://localhost:8080"]},
    r"/*": {"origins": ["http://127.0.0.1:8080", "http://localhost:8080"]}
})
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

WIDGET_HTML = Path(__file__).parent / "widget.html"
APP_VERSION = "2.2.0"

GUI_CREDENTIALS: Dict[str, Dict[str, str]] = {}
_request_log: Dict[str, list] = {}
MAX_REQUESTS_PER_MINUTE = 60

def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    if ip not in _request_log:
        _request_log[ip] = []
    _request_log[ip] = [t for t in _request_log[ip] if now - t < 60]
    if len(_request_log[ip]) >= MAX_REQUESTS_PER_MINUTE:
        return False
    _request_log[ip].append(now)
    return True

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
    resp.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:8080")
    return resp

def _file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]

def _get_adapter_instance(platform: str):
    creds = GUI_CREDENTIALS.get(platform, {})
    if platform == "telegram":
        return TelegramAdapter(
            bot_token=creds.get("bot_token") or None,
            chat_id=creds.get("chat_id") or None,
        )
    elif platform == "discord":
        return DiscordAdapter(
            webhook_url=creds.get("webhook_url") or None,
        )
    elif platform == "imgur":
        return ImgurAdapter(
            client_id=creds.get("client_id") or None,
        )
    elif platform == "reddit":
        return RedditAdapter(
            client_id=creds.get("client_id") or None,
            client_secret=creds.get("client_secret") or None,
            username=creds.get("username") or None,
            password=creds.get("password") or None,
        )
    elif platform == "twitter":
        return TwitterAdapter(
            api_key=creds.get("api_key") or None,
            api_secret=creds.get("api_secret") or None,
            access_token=creds.get("access_token") or None,
            access_secret=creds.get("access_secret") or None,
        )
    elif platform == "instagram":
        return InstagramAdapter(
            account_id=creds.get("account_id") or None,
            access_token=creds.get("access_token") or None,
        )
    elif platform == "whatsapp":
        return WhatsAppAdapter(
            phone_id=creds.get("phone_id") or None,
            access_token=creds.get("access_token") or None,
            recipient_phone=creds.get("recipient_phone") or None,
        )
    elif platform == "nostr":
        relay_urls = None
        if creds.get("relay_urls"):
            relay_urls = [u.strip() for u in creds.get("relay_urls", "").split(",") if u.strip()]
        return NostrAdapter(
            private_key=creds.get("private_key") or None,
            relay_urls=relay_urls,
        )
    else:
        raise ValueError(f"Plataforma '{platform}' no soportada")

def _check_adapter_configured(platform: str) -> tuple[bool, str]:
    if not HAS_ADAPTERS:
        return False, "Adaptadores no importados"
    try:
        adapter = _get_adapter_instance(platform)
        if hasattr(adapter, "is_available"):
            available = adapter.is_available()
            return available, "Adaptador listo" if available else "Faltan credenciales"
        if hasattr(adapter, "_get_auth_headers"):
            adapter._get_auth_headers()
        return True, "Adaptador listo"
    except Exception as e:
        return False, str(e)

@app.before_request
def _rate_limit():
    ip = request.remote_addr or "unknown"
    if not _check_rate_limit(ip):
        return _cors_jsonify({"error": "Rate limit exceeded. Max 60 requests/minute."}, 429)

@app.route("/")
def index():
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

        return _cors_jsonify({"success": True, "report": report})
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

        return _cors_jsonify({"success": True, "transformations": result.get("transformations", []), "platform": platform})
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

@app.route("/config", methods=["GET"])
def get_config():
    masked = {}
    for platform, creds in GUI_CREDENTIALS.items():
        masked[platform] = {k: ("✓" if v else "✗") for k, v in creds.items()}
    return _cors_jsonify({"success": True, "credentials": masked})

@app.route("/config", methods=["POST"])
def set_config():
    global GUI_CREDENTIALS
    data = request.get_json(force=True, silent=True) or {}
    platform = data.get("platform", "").lower().strip()
    creds = data.get("credentials", {})

    if not platform:
        return _cors_jsonify({"success": False, "error": "Falta plataforma"}, 400)

    if platform not in GUI_CREDENTIALS:
        GUI_CREDENTIALS[platform] = {}

    for key, value in creds.items():
        if value and str(value).strip():
            GUI_CREDENTIALS[platform][key] = str(value).strip()

    return _cors_jsonify({
        "success": True,
        "platform": platform,
        "saved_keys": list(GUI_CREDENTIALS[platform].keys()),
    })

@app.route("/config/clear", methods=["POST"])
def clear_config():
    global GUI_CREDENTIALS
    GUI_CREDENTIALS = {}
    return _cors_jsonify({"success": True, "message": "Credenciales eliminadas"})

ADAPTER_MAP = {
    "telegram": TelegramAdapter,
    "discord": DiscordAdapter,
    "imgur": ImgurAdapter,
    "reddit": RedditAdapter,
    "twitter": TwitterAdapter,
    "instagram": InstagramAdapter,
    "whatsapp": WhatsAppAdapter,
    "nostr": NostrAdapter,
}

@app.route("/platform_status", methods=["GET"])
def platform_status():
    if not HAS_ADAPTERS:
        return _cors_jsonify({"error": "Adaptadores no disponibles"}, 503)

    status = {}
    for name in ADAPTER_MAP.keys():
        configured, desc = _check_adapter_configured(name)
        status[name] = {
            "configured": configured,
            "description": desc,
        }
    return _cors_jsonify(status)

@app.route("/publish", methods=["POST"])
def publish():
    if not HAS_ADAPTERS:
        return _cors_jsonify({"error": "Adaptadores no disponibles"}, 503)

    try:
        file = request.files.get("image")
        platform = request.form.get("platform", "").lower().strip()
        caption = request.form.get("caption", "")

        if not file:
            return _cors_jsonify({"error": "Falta imagen"}, 400)
        if not platform:
            return _cors_jsonify({"error": "Falta plataforma"}, 400)
        if platform not in ADAPTER_MAP:
            return _cors_jsonify({"error": f"Plataforma '{platform}' no soportada"}, 400)

        img_data = file.read()
        suffix = ".png" if file.filename.lower().endswith(".png") else ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(img_data)
            tmp_path = tmp.name

        try:
            adapter = _get_adapter_instance(platform)
            if hasattr(adapter, "upload_with_caption"):
                result = adapter.upload_with_caption(tmp_path, caption)
            else:
                result = adapter.upload(tmp_path)

            url = result if isinstance(result, str) else (result.get("url") if isinstance(result, dict) else "")

            return _cors_jsonify({
                "success": True,
                "platform": platform,
                "url": url or "",
                "details": result if isinstance(result, dict) else {},
            })
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    except Exception as e:
        traceback.print_exc()
        return _cors_jsonify({"error": str(e)}, 500)

@app.route("/publish_validate", methods=["POST"])
def publish_validate():
    if not HAS_ADAPTERS:
        return _cors_jsonify({"error": "Adaptadores no disponibles"}, 503)

    try:
        file = request.files.get("image")
        platform = request.form.get("platform", "").lower().strip()
        caption = request.form.get("caption", "")
        mode_str = request.form.get("mode", "auto")
        original_message = request.form.get("original_message", "")

        if not file:
            return _cors_jsonify({"error": "Falta imagen"}, 400)
        if not platform:
            return _cors_jsonify({"error": "Falta plataforma"}, 400)
        if platform not in ADAPTER_MAP:
            return _cors_jsonify({"error": f"Plataforma '{platform}' no soportada"}, 400)

        original_data = file.read()
        original_hash = _file_hash(original_data)
        original_size = len(original_data)
        original_pil = Image.open(BytesIO(original_data))

        suffix = ".png" if file.filename.lower().endswith(".png") else ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(original_data)
            tmp_path = tmp.name

        try:
            adapter = _get_adapter_instance(platform)
            pub_result = adapter.upload(tmp_path)
            url = pub_result if isinstance(pub_result, str) else (pub_result.get("url") if isinstance(pub_result, dict) else "")

            if not url:
                return _cors_jsonify({
                    "success": False,
                    "error": "La publicación no devolvió URL",
                    "details": pub_result if isinstance(pub_result, dict) else {},
                }, 500)

            dl_path = os.path.join(tempfile.mkdtemp(), "downloaded.png")
            if hasattr(adapter, "download"):
                adapter.download(url, dl_path)
            else:
                import requests
                r = requests.get(url, timeout=60)
                with open(dl_path, "wb") as f:
                    f.write(r.content)

            downloaded_data = open(dl_path, "rb").read()
            downloaded_hash = _file_hash(downloaded_data)
            downloaded_size = len(downloaded_data)
            downloaded_pil = Image.open(BytesIO(downloaded_data))

            engine = StegoEngine()
            expected_mode = _mode_from_str(mode_str) if mode_str and mode_str != "auto" else None
            extract_result = engine.extract(dl_path, expected_mode=expected_mode)
            extracted_message = extract_result.get("message", "") if extract_result else ""

            analyzer = StegAnalyzer()
            report = analyzer.compare_images(original_pil, downloaded_pil)
            psnr = report.get("psnr", 0.0)

            has_message = bool(
                extracted_message
                and len(extracted_message.strip()) > 0
                and not extracted_message.startswith("\x00")
            )
            message_match = False
            if has_message and original_message:
                message_match = (extracted_message == original_message)
            elif has_message and not original_message:
                message_match = True

            e2e_result = {
                "success": message_match,
                "extracted_message": extracted_message if has_message else "No se pudo extraer mensaje legible",
                "message_match": message_match,
                "original_size": original_size,
                "downloaded_size": downloaded_size,
                "original_hash": original_hash,
                "downloaded_hash": downloaded_hash,
                "psnr": round(psnr, 2),
                "url": url,
            }

            return _cors_jsonify({
                "success": True,
                "platform": platform,
                "url": url,
                "e2e": e2e_result,
            })

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    except Exception as e:
        traceback.print_exc()
        return _cors_jsonify({"error": str(e)}, 500)

def main():
    print("=" * 60)
    print(" Stegstr Widget Server v2.2.0 (PATCHED)")
    print("=" * 60)
    print(f"Serving widget from: {WIDGET_HTML}")
    print("Open http://127.0.0.1:8080 in your browser")
    print("Press Ctrl+C to stop")
    print("\nEndpoints disponibles:")
    print("  GET  /                  → Widget HTML")
    print("  GET  /health            → Estado del backend")
    print("  POST /embed             → Ocultar mensaje")
    print("  POST /extract           → Extraer mensaje")
    print("  POST /capacity          → Capacidad de imagen")
    print("  POST /analyze           → Análisis estadístico")
    print("  POST /simulate          → Simulación local")
    print("  POST /benchmark         → Benchmark")
    print("  POST /optimize          → Auto-tune")
    print("  GET  /platform_status   → Estado de adaptadores")
    print("  POST /publish           → Publicar en plataforma real")
    print("  POST /publish_validate  → Publicar + validar E2E")
    print("  GET  /config            → Leer credenciales GUI")
    print("  POST /config            → Guardar credenciales GUI")
    print("  POST /config/clear      → Limpiar credenciales GUI")
    print("=" * 60)
    app.run(host="127.0.0.1", port=8080, debug=False)

if __name__ == "__main__":
    main()
