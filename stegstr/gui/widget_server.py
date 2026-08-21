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
    GET  /platform_status   → Estado de adaptadores (env vars)
    POST /configure_platform → Guardar credenciales en memoria
    GET  /platform_config   → Credenciales guardadas en memoria
    POST /publish           → Publicar en plataforma real
    POST /publish_validate  → Publicar + validar E2E
"""

import os
import sys
import time
import tempfile
import base64
import hashlib
import traceback
import json
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional

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

# ── Importar adaptadores de plataforma ──────────────────────────────
try:
    from stegstr.platform.adapters import (
        get_adapter,
        TelegramAdapter, DiscordAdapter, ImgurAdapter,
        RedditAdapter, TwitterAdapter, InstagramAdapter,
        WhatsAppAdapter, NostrAdapter,
    )
    HAS_ADAPTERS = True
except ImportError:
    HAS_ADAPTERS = False
    print("[WARN] No se pudieron importar los adaptadores de plataforma.")
    print("[WARN] La pestaña Publicar no funcionará hasta que configures los adaptadores.")

app = Flask(__name__, static_folder=".")
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/*": {"origins": "*"}})

WIDGET_HTML = Path(__file__).parent / "widget.html"
APP_VERSION = "2.2.0"

# ── Credential Store (en memoria, no persiste en disco) ─────────────
# Estructura: { "telegram": {"bot_token": "...", "chat_id": "..."}, ... }
CREDENTIAL_STORE: Dict[str, Dict[str, str]] = {}

# ── Mapa de campos requeridos por plataforma ────────────────────────
PLATFORM_CREDENTIAL_FIELDS = {
    "telegram":   ["bot_token", "chat_id"],
    "discord":    ["webhook_url"],
    "imgur":      ["client_id"],
    "reddit":     ["client_id", "client_secret", "username", "password"],
    "twitter":    ["api_key", "api_secret", "access_token", "access_token_secret"],
    "instagram":  ["username", "password"],
    "whatsapp":   ["api_key", "phone_number"],
    "nostr":      ["private_key", "relay_url"],
}

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

def _file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]

def _check_adapter_configured(adapter_class) -> tuple[bool, str]:
    """Verifica si un adaptador está configurado (tiene credenciales via env vars)."""
    try:
        adapter = adapter_class()
        if hasattr(adapter, '_get_auth_headers'):
            adapter._get_auth_headers()
        return True, "Adaptador listo (env vars)"
    except Exception as e:
        return False, str(e)

def _inject_credentials(platform: str, credentials: Dict[str, str]):
    """
    Inyecta credenciales en las variables de entorno para que los adaptadores
    las lean. Usa prefijo para evitar colisiones con env vars existentes.
    """
    mapping = {
        "telegram": {
            "TELEGRAM_BOT_TOKEN": credentials.get("bot_token", ""),
            "TELEGRAM_CHAT_ID": credentials.get("chat_id", ""),
        },
        "discord": {
            "DISCORD_WEBHOOK_URL": credentials.get("webhook_url", ""),
        },
        "imgur": {
            "IMGUR_CLIENT_ID": credentials.get("client_id", ""),
        },
        "reddit": {
            "REDDIT_CLIENT_ID": credentials.get("client_id", ""),
            "REDDIT_CLIENT_SECRET": credentials.get("client_secret", ""),
            "REDDIT_USERNAME": credentials.get("username", ""),
            "REDDIT_PASSWORD": credentials.get("password", ""),
        },
        "twitter": {
            "TWITTER_API_KEY": credentials.get("api_key", ""),
            "TWITTER_API_SECRET": credentials.get("api_secret", ""),
            "TWITTER_ACCESS_TOKEN": credentials.get("access_token", ""),
            "TWITTER_ACCESS_TOKEN_SECRET": credentials.get("access_token_secret", ""),
        },
        "instagram": {
            "INSTAGRAM_USERNAME": credentials.get("username", ""),
            "INSTAGRAM_PASSWORD": credentials.get("password", ""),
        },
        "whatsapp": {
            "WHATSAPP_API_KEY": credentials.get("api_key", ""),
            "WHATSAPP_PHONE_NUMBER": credentials.get("phone_number", ""),
        },
        "nostr": {
            "NOSTR_PRIVATE_KEY": credentials.get("private_key", ""),
            "NOSTR_RELAY_URL": credentials.get("relay_url", ""),
        },
    }
    for key, value in mapping.get(platform, {}).items():
        if value:
            os.environ[key] = value

def _get_adapter_instance(platform: str, inline_creds: Optional[Dict[str, str]] = None):
    """
    Obtiene una instancia del adaptador con las credenciales correctas.
    Prioridad: 1) credenciales inline, 2) credenciales guardadas en memoria, 3) env vars.
    """
    if not HAS_ADAPTERS:
        raise RuntimeError("Adaptadores no disponibles")

    adapter_class = ADAPTER_MAP.get(platform)
    if not adapter_class:
        raise ValueError(f"Plataforma '{platform}' no soportada")

    # Prioridad 1: credenciales inline (del formulario actual)
    if inline_creds:
        _inject_credentials(platform, inline_creds)
        return adapter_class()

    # Prioridad 2: credenciales guardadas en memoria
    if platform in CREDENTIAL_STORE and CREDENTIAL_STORE[platform]:
        _inject_credentials(platform, CREDENTIAL_STORE[platform])
        return adapter_class()

    # Prioridad 3: env vars existentes (los adaptadores ya las leen)
    return adapter_class()

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


# ════════════════════════════════════════════════════════════════════
#  CREDENTIALS MANAGEMENT (nuevo)
# ════════════════════════════════════════════════════════════════════

@app.route("/configure_platform", methods=["POST"])
def configure_platform():
    """
    Guarda credenciales de una plataforma en memoria (RAM).
    Las credenciales se pierden al reiniciar el servidor.

    JSON body:
      { "platform": "telegram", "credentials": { "bot_token": "...", "chat_id": "..." } }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        platform = data.get("platform", "").lower().strip()
        credentials = data.get("credentials", {})

        if not platform:
            return _cors_jsonify({"error": "Falta plataforma"}, 400)
        if platform not in PLATFORM_CREDENTIAL_FIELDS:
            return _cors_jsonify({"error": f"Plataforma '{platform}' no soportada"}, 400)
        if not credentials:
            return _cors_jsonify({"error": "Faltan credenciales"}, 400)

        # Validar que vengan todos los campos requeridos
        required = PLATFORM_CREDENTIAL_FIELDS[platform]
        missing = [f for f in required if not credentials.get(f, "").strip()]
        if missing:
            return _cors_jsonify({
                "error": f"Faltan campos obligatorios: {', '.join(missing)}",
                "required": required,
            }, 400)

        # Guardar en memoria
        CREDENTIAL_STORE[platform] = credentials

        # Probar conexión
        try:
            adapter = _get_adapter_instance(platform)
            return _cors_jsonify({
                "success": True,
                "platform": platform,
                "message": "Credenciales guardadas y adaptador inicializado correctamente",
                "fields_configured": list(credentials.keys()),
            })
        except Exception as e:
            # Guardamos igual pero advertimos
            return _cors_jsonify({
                "success": True,
                "platform": platform,
                "warning": "Credenciales guardadas pero el adaptador reportó: " + str(e),
                "fields_configured": list(credentials.keys()),
            })

    except Exception as e:
        return _cors_jsonify({"error": str(e)}, 500)

@app.route("/platform_config", methods=["GET"])
def platform_config():
    """
    Devuelve las plataformas que tienen credenciales guardadas en memoria.
    No devuelve los valores, solo los nombres de los campos configurados.
    """
    result = {}
    for platform, creds in CREDENTIAL_STORE.items():
        result[platform] = {
            "configured": True,
            "fields": list(creds.keys()),
        }
    # También incluir plataformas con env vars
    if HAS_ADAPTERS:
        for name, adapter_class in ADAPTER_MAP.items():
            if name not in result:
                configured, desc = _check_adapter_configured(adapter_class)
                if configured:
                    result[name] = {
                        "configured": True,
                        "source": "environment",
                        "fields": PLATFORM_CREDENTIAL_FIELDS.get(name, []),
                    }
    return _cors_jsonify(result)

@app.route("/clear_credentials", methods=["POST"])
def clear_credentials():
    """Limpia todas las credenciales guardadas en memoria."""
    global CREDENTIAL_STORE
    count = len(CREDENTIAL_STORE)
    CREDENTIAL_STORE = {}
    return _cors_jsonify({"success": True, "cleared_count": count})


# ════════════════════════════════════════════════════════════════════
#  PUBLISH ENDPOINTS (actualizados para soportar credenciales inline)
# ════════════════════════════════════════════════════════════════════

@app.route("/platform_status", methods=["GET"])
def platform_status():
    """Devuelve el estado de configuración de cada adaptador (env vars + memoria)."""
    if not HAS_ADAPTERS:
        return _cors_jsonify({"error": "Adaptadores no disponibles"}, 503)

    status = {}
    for name, adapter_class in ADAPTER_MAP.items():
        # Primero verificar memoria
        if name in CREDENTIAL_STORE:
            status[name] = {
                "configured": True,
                "source": "memory",
                "description": "Credenciales configuradas vía GUI",
            }
            continue
        # Luego env vars
        configured, desc = _check_adapter_configured(adapter_class)
        status[name] = {
            "configured": configured,
            "source": "environment" if configured else "none",
            "description": desc,
        }
    return _cors_jsonify(status)

@app.route("/publish", methods=["POST"])
def publish():
    """
    Publica una imagen en una plataforma real.
    Acepta credenciales inline vía form-data (prefijo cred_*) o usa las guardadas en memoria/env vars.
    """
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

        # Extraer credenciales inline del formulario (campos cred_*)
        inline_creds = {}
        for key in PLATFORM_CREDENTIAL_FIELDS.get(platform, []):
            val = request.form.get(f"cred_{key}", "").strip()
            if val:
                inline_creds[key] = val

        img_data = file.read()
        suffix = ".png" if file.filename.lower().endswith(".png") else ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(img_data)
            tmp_path = tmp.name

        try:
            adapter = _get_adapter_instance(platform, inline_creds if inline_creds else None)
            result = adapter.send_image(tmp_path, caption=caption or None)

            return _cors_jsonify({
                "success": True,
                "platform": platform,
                "url": result.get("url", ""),
                "details": result,
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
    """
    Publica, descarga de vuelta y valida E2E.
    Acepta credenciales inline vía form-data.
    """
    if not HAS_ADAPTERS:
        return _cors_jsonify({"error": "Adaptadores no disponibles"}, 503)

    try:
        file = request.files.get("image")
        platform = request.form.get("platform", "").lower().strip()
        caption = request.form.get("caption", "")
        mode_str = request.form.get("mode", "auto")

        if not file:
            return _cors_jsonify({"error": "Falta imagen"}, 400)
        if not platform:
            return _cors_jsonify({"error": "Falta plataforma"}, 400)
        if platform not in ADAPTER_MAP:
            return _cors_jsonify({"error": f"Plataforma '{platform}' no soportada"}, 400)

        # Extraer credenciales inline
        inline_creds = {}
        for key in PLATFORM_CREDENTIAL_FIELDS.get(platform, []):
            val = request.form.get(f"cred_{key}", "").strip()
            if val:
                inline_creds[key] = val

        # Leer imagen original
        original_data = file.read()
        original_hash = _file_hash(original_data)
        original_size = len(original_data)
        original_pil = Image.open(BytesIO(original_data))

        # Guardar temporalmente para subir
        suffix = ".png" if file.filename.lower().endswith(".png") else ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(original_data)
            tmp_path = tmp.name

        try:
            # 1. Publicar
            adapter = _get_adapter_instance(platform, inline_creds if inline_creds else None)
            pub_result = adapter.send_image(tmp_path, caption=caption or None)
            url = pub_result.get("url", "")

            if not url:
                return _cors_jsonify({
                    "success": False,
                    "error": "La publicación no devolvió URL",
                    "details": pub_result,
                }, 500)

            # 2. Descargar imagen publicada
            downloaded_data = adapter.download_image(url)
            downloaded_hash = _file_hash(downloaded_data)
            downloaded_size = len(downloaded_data)
            downloaded_pil = Image.open(BytesIO(downloaded_data))

            # 3. Extraer mensaje
            tmpdir = tempfile.mkdtemp()
            dl_path = os.path.join(tmpdir, "downloaded.png")
            downloaded_pil.save(dl_path, "PNG")

            engine = StegoEngine()
            expected_mode = _mode_from_str(mode_str) if mode_str and mode_str != "auto" else None
            extract_result = engine.extract(dl_path, expected_mode=expected_mode)
            extracted_message = extract_result.get("message", "") if extract_result else ""

            # 4. Calcular PSNR
            analyzer = StegAnalyzer()
            report = analyzer.compare_images(original_pil, downloaded_pil)
            psnr = report.get("psnr", 0.0)

            # 5. Verificar mensaje legible
            has_message = bool(extracted_message and len(extracted_message.strip()) > 0
                               and not extracted_message.startswith("\x00"))

            e2e_result = {
                "success": has_message,
                "extracted_message": extracted_message if has_message else "No se pudo extraer mensaje legible",
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


# ── Main ──

def main():
    print("=" * 60)
    print(" Stegstr Widget Server v2.2.0")
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
    print("  POST /configure_platform→ Guardar credenciales (RAM)")
    print("  GET  /platform_config   → Credenciales guardadas")
    print("  POST /clear_credentials → Limpiar credenciales")
    print("  POST /publish           → Publicar en plataforma real")
    print("  POST /publish_validate  → Publicar + validar E2E")
    print("=" * 60)
    app.run(host="127.0.0.1", port=8080, debug=False)

if __name__ == "__main__":
    main()
