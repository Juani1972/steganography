#!/usr/bin/env python3
"""
Stegstr Widget Server v2.2.0
Backend Flask para la SPA widget.html.
Expone endpoints REST para esteganografía, análisis, benchmark y publicación.

Correcciones v2.2.0:
- CORS restringido a localhost (seguridad)
- Credenciales unificadas: Instagram (Business API), WhatsApp (Business API)
- Credenciales Twitter: TWITTER_ACCESS_TOKEN_SECRET (nombre correcto)
- Mapeo de credenciales sincronizado con adaptadores reales
"""

import os, sys, json, time, hashlib, tempfile, base64, io
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image

# ── Paths ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.stego.analyzer import StegoAnalyzer
from stegstr.stego.benchmark import StegoBenchmark
from stegstr.platform.simulator import RealisticPlatformSimulator
from stegstr.platform.adapters import (
    TelegramAdapter, DiscordAdapter, ImgurAdapter, RedditAdapter,
    TwitterAdapter, InstagramAdapter, WhatsAppAdapter, NostrAdapter
)

# ── Flask App ──
app = Flask(__name__)
# CORS restringido a localhost/127.0.0.1 para seguridad
CORS(app, resources={
    r"/api/*": {"origins": ["http://127.0.0.1:8080", "http://localhost:8080"]},
    r"/*":      {"origins": ["http://127.0.0.1:8080", "http://localhost:8080"]}
})

UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "stegstr_widget"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# ── In-memory credential store (RAM only) ──
PLATFORM_CREDENTIALS = {}

PLATFORM_CREDENTIAL_FIELDS = {
    "telegram":  ["bot_token", "chat_id"],
    "discord":   ["webhook_url"],
    "imgur":     ["client_id"],
    "reddit":    ["client_id", "client_secret", "username", "password"],
    "twitter":   ["api_key", "api_secret", "access_token", "access_token_secret"],
    "instagram": ["business_account_id", "page_access_token"],
    "whatsapp":  ["business_phone_id", "access_token", "recipient_phone"],
    "nostr":     ["private_key", "relay_url"],
}

ADAPTER_MAP = {
    "telegram":  TelegramAdapter,
    "discord":   DiscordAdapter,
    "imgur":     ImgurAdapter,
    "reddit":    RedditAdapter,
    "twitter":   TwitterAdapter,
    "instagram": InstagramAdapter,
    "whatsapp":  WhatsAppAdapter,
    "nostr":     NostrAdapter,
}

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _save_upload(file_storage, prefix="upload") -> Path:
    ext = Path(file_storage.filename).suffix or ".png"
    name = f"{prefix}_{int(time.time()*1000)}_{hashlib.md5(file_storage.filename.encode()).hexdigest()[:8]}{ext}"
    path = UPLOAD_FOLDER / name
    file_storage.save(str(path))
    return path

def _inject_credentials(platform: str, credentials: dict):
    """
    Inyecta credenciales en variables de entorno del proceso actual
    de forma que los adaptadores las encuentren vía os.environ.get().
    Mapeo sincronizado con los nombres que cada adaptador espera.
    """
    mapping = {
        "telegram": {
            "TELEGRAM_BOT_TOKEN": credentials.get("bot_token", ""),
            "TELEGRAM_CHAT_ID":   credentials.get("chat_id", ""),
        },
        "discord": {
            "DISCORD_WEBHOOK_URL": credentials.get("webhook_url", ""),
        },
        "imgur": {
            "IMGUR_CLIENT_ID": credentials.get("client_id", ""),
        },
        "reddit": {
            "REDDIT_CLIENT_ID":     credentials.get("client_id", ""),
            "REDDIT_CLIENT_SECRET": credentials.get("client_secret", ""),
            "REDDIT_USERNAME":      credentials.get("username", ""),
            "REDDIT_PASSWORD":      credentials.get("password", ""),
        },
        "twitter": {
            "TWITTER_API_KEY":            credentials.get("api_key", ""),
            "TWITTER_API_SECRET":         credentials.get("api_secret", ""),
            "TWITTER_ACCESS_TOKEN":       credentials.get("access_token", ""),
            "TWITTER_ACCESS_TOKEN_SECRET": credentials.get("access_token_secret", ""),
        },
        "instagram": {
            "INSTAGRAM_BUSINESS_ACCOUNT_ID": credentials.get("business_account_id", ""),
            "META_PAGE_ACCESS_TOKEN":        credentials.get("page_access_token", ""),
        },
        "whatsapp": {
            "WHATSAPP_BUSINESS_PHONE_ID": credentials.get("business_phone_id", ""),
            "WHATSAPP_ACCESS_TOKEN":      credentials.get("access_token", ""),
            "WHATSAPP_RECIPIENT_PHONE":   credentials.get("recipient_phone", ""),
        },
        "nostr": {
            "NOSTR_PRIVATE_KEY": credentials.get("private_key", ""),
            "NOSTR_RELAY_URL":   credentials.get("relay_url", ""),
        },
    }
    for key, value in mapping.get(platform, {}).items():
        if value:
            os.environ[key] = value

def _get_mode(mode_str: str) -> StegoMode:
    """Convierte string a StegoMode. Acepta nombres en minúscula o mayúscula."""
    mode_map = {
        "fortress": StegoMode.FORTRESS,
        "armor":    StegoMode.ARMOR,
        "ghost":    StegoMode.GHOST,
        "phantom":  StegoMode.PHANTOM,
        "hybrid":   StegoMode.HYBRID,
    }
    return mode_map.get(mode_str.lower(), StegoMode.HYBRID)

# ═══════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_file(Path(__file__).parent / "widget.html")

# ── Embed ──
@app.route("/embed", methods=["POST"])
def embed():
    try:
        cover = request.files.get("cover")
        message = request.form.get("message", "")
        mode_str = request.form.get("mode", "HYBRID")
        platform = request.form.get("platform", "")
        password = request.form.get("password", "")
        autotune = request.form.get("autotune", "false").lower() == "true"

        if not cover or not message:
            return jsonify({"success": False, "error": "Falta imagen o mensaje"}), 400

        cover_path = _save_upload(cover, "cover")
        mode = _get_mode(mode_str)

        engine = StegoEngine()
        kwargs = {"password": password} if password else {}

        if autotune and platform:
            kwargs["platform"] = platform
            kwargs["autotune"] = True

        result = engine.hide(cover_path, message, mode=mode, **kwargs)

        stego_path = result.get("stego_path")
        if not stego_path or not Path(stego_path).exists():
            return jsonify({"success": False, "error": "No se generó imagen stego"}), 500

        # Copiar a uploads para servirla
        ext = Path(stego_path).suffix
        out_name = f"stego_{int(time.time())}{ext}"
        out_path = UPLOAD_FOLDER / out_name
        import shutil
        shutil.copy(stego_path, out_path)

        return jsonify({
            "success": True,
            "stego_url": f"/uploads/{out_name}",
            "mode": mode_str,
            "capacity_used": result.get("capacity_used"),
            "psnr": result.get("psnr"),
            "platform": platform,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Extract ──
@app.route("/extract", methods=["POST"])
def extract():
    try:
        stego = request.files.get("stego")
        mode_str = request.form.get("mode", "")
        password = request.form.get("password", "")

        if not stego:
            return jsonify({"success": False, "error": "Falta imagen stego"}), 400

        stego_path = _save_upload(stego, "stego")
        mode = _get_mode(mode_str) if mode_str else None

        engine = StegoEngine()
        kwargs = {"password": password} if password else {}
        if mode:
            kwargs["mode"] = mode

        result = engine.extract(stego_path, **kwargs)
        return jsonify({
            "success": True,
            "message": result.get("message", ""),
            "mode": result.get("mode", "unknown"),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Analyze ──
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        cover = request.files.get("cover")
        stego = request.files.get("stego")
        if not cover or not stego:
            return jsonify({"success": False, "error": "Faltan ambas imágenes"}), 400

        cover_path = _save_upload(cover, "cover")
        stego_path = _save_upload(stego, "stego")

        analyzer = StegoAnalyzer()
        report = analyzer.compare(cover_path, stego_path)
        return jsonify({"success": True, **report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Capacity ──
@app.route("/capacity", methods=["POST"])
def capacity():
    try:
        cover = request.files.get("cover")
        mode_str = request.form.get("mode", "ARMOR")
        platform = request.form.get("platform", "")
        ecc = request.form.get("ecc", "")

        if not cover:
            return jsonify({"success": False, "error": "Falta imagen"}), 400

        cover_path = _save_upload(cover, "cover")
        mode = _get_mode(mode_str)

        engine = StegoEngine()
        kwargs = {"mode": mode}
        if platform:
            kwargs["platform"] = platform
        if ecc:
            try:
                kwargs["ecc_bytes"] = int(ecc)
            except ValueError:
                pass

        cap = engine.get_capacity(cover_path, **kwargs)
        return jsonify({
            "success": True,
            "capacity_bytes": cap,
            "capacity_kb": round(cap / 1024, 2),
            "mode": mode_str,
            "platform": platform,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Benchmark ──
@app.route("/benchmark", methods=["POST"])
def benchmark():
    try:
        cover = request.files.get("cover")
        message = request.form.get("message", "Mensaje de prueba")
        mode_str = request.form.get("mode", "ARMOR")

        if not cover:
            return jsonify({"success": False, "error": "Falta imagen"}), 400

        cover_path = _save_upload(cover, "cover")
        mode = _get_mode(mode_str)

        bench = StegoBenchmark()
        result = bench.run(cover_path, message, mode=mode)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Simulate ──
@app.route("/simulate", methods=["POST"])
def simulate():
    try:
        cover = request.files.get("cover")
        message = request.form.get("message", "")
        mode_str = request.form.get("mode", "HYBRID")
        platform = request.form.get("platform", "telegram_photo")

        if not cover or not message:
            return jsonify({"success": False, "error": "Falta imagen o mensaje"}), 400

        cover_path = _save_upload(cover, "cover")
        mode = _get_mode(mode_str)

        engine = StegoEngine()
        result = engine.hide(cover_path, message, mode=mode)
        stego_path = result.get("stego_path")

        sim = RealisticPlatformSimulator()
        sim_result = sim.simulate(platform, stego_path)

        return jsonify({
            "success": True,
            "platform": platform,
            "survived": sim_result.get("survived", False),
            "psnr_after": sim_result.get("psnr_after"),
            "size_after_kb": sim_result.get("size_after_kb"),
            "modifications": sim_result.get("modifications", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Publish ──
@app.route("/publish", methods=["POST"])
def publish():
    try:
        image = request.files.get("image")
        platform = request.form.get("platform", "")
        caption = request.form.get("caption", "")
        creds_json = request.form.get("credentials", "{}")

        if not image or not platform:
            return jsonify({"success": False, "error": "Falta imagen o plataforma"}), 400

        image_path = _save_upload(image, "publish")

        # Inyectar credenciales inline si se proporcionan
        try:
            inline_creds = json.loads(creds_json)
            if inline_creds:
                _inject_credentials(platform, inline_creds)
        except json.JSONDecodeError:
            pass

        # También inyectar credenciales guardadas en memoria
        if platform in PLATFORM_CREDENTIALS:
            _inject_credentials(platform, PLATFORM_CREDENTIALS[platform])

        adapter_cls = ADAPTER_MAP.get(platform)
        if not adapter_cls:
            return jsonify({"success": False, "error": f"Plataforma '{platform}' no soportada"}), 400

        adapter = adapter_cls()
        result = adapter.publish(image_path, caption=caption)

        return jsonify({
            "success": result.get("success", False),
            "url": result.get("url", ""),
            "platform": platform,
            "message": result.get("message", ""),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Publish + Validate E2E ──
@app.route("/publish_validate", methods=["POST"])
def publish_validate():
    try:
        image = request.files.get("image")
        platform = request.form.get("platform", "")
        caption = request.form.get("caption", "")
        mode_str = request.form.get("mode", "auto")
        creds_json = request.form.get("credentials", "{}")

        if not image or not platform:
            return jsonify({"success": False, "error": "Falta imagen o plataforma"}), 400

        image_path = _save_upload(image, "publish")
        original_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()

        # Inyectar credenciales
        try:
            inline_creds = json.loads(creds_json)
            if inline_creds:
                _inject_credentials(platform, inline_creds)
        except json.JSONDecodeError:
            pass
        if platform in PLATFORM_CREDENTIALS:
            _inject_credentials(platform, PLATFORM_CREDENTIALS[platform])

        adapter_cls = ADAPTER_MAP.get(platform)
        if not adapter_cls:
            return jsonify({"success": False, "error": f"Plataforma '{platform}' no soportada"}), 400

        adapter = adapter_cls()
        pub_result = adapter.publish(image_path, caption=caption)

        if not pub_result.get("success"):
            return jsonify({
                "success": False,
                "error": pub_result.get("error", "Error en publicación"),
                "platform": platform,
            }), 500

        # Validación E2E: descargar y comparar
        url = pub_result.get("url", "")
        e2e = {"success": False, "url": url, "platform": platform}

        if url and hasattr(adapter, "download"):
            try:
                downloaded = adapter.download(url)
                if downloaded:
                    downloaded_path = UPLOAD_FOLDER / f"downloaded_{int(time.time())}.png"
                    with open(downloaded_path, "wb") as f:
                        f.write(downloaded)
                    downloaded_hash = hashlib.sha256(downloaded).hexdigest()

                    e2e["original_size"] = image_path.stat().st_size
                    e2e["downloaded_size"] = len(downloaded)
                    e2e["original_hash"] = original_hash
                    e2e["downloaded_hash"] = downloaded_hash
                    e2e["hash_match"] = original_hash == downloaded_hash

                    # Extraer mensaje si hay modo
                    if mode_str and mode_str != "auto":
                        engine = StegoEngine()
                        mode = _get_mode(mode_str)
                        ext_result = engine.extract(downloaded_path, mode=mode)
                        e2e["extracted_message"] = ext_result.get("message", "")

                    # Calcular PSNR si tenemos cover (no disponible aquí, usamos proxy)
                    try:
                        from stegstr.stego.analyzer import StegoAnalyzer
                        analyzer = StegoAnalyzer()
                        psnr = analyzer.psnr(image_path, downloaded_path)
                        e2e["psnr"] = round(psnr, 2) if psnr else None
                    except Exception:
                        pass

                    e2e["success"] = e2e.get("hash_match", False)
            except Exception as e:
                e2e["error"] = str(e)

        return jsonify({
            "success": pub_result.get("success", False),
            "url": url,
            "platform": platform,
            "e2e": e2e,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── Credential Management ──
@app.route("/configure_platform", methods=["POST"])
def configure_platform():
    try:
        data = request.get_json(force=True)
        platform = data.get("platform", "").lower()
        credentials = data.get("credentials", {})

        if not platform or platform not in PLATFORM_CREDENTIAL_FIELDS:
            return jsonify({"success": False, "error": "Plataforma no válida"}), 400

        PLATFORM_CREDENTIALS[platform] = credentials
        _inject_credentials(platform, credentials)

        return jsonify({
            "success": True,
            "message": f"Credenciales de {platform} guardadas en memoria",
            "platform": platform,
            "fields": list(credentials.keys()),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/platform_config", methods=["GET"])
def platform_config():
    result = {}
    for platform, fields in PLATFORM_CREDENTIAL_FIELDS.items():
        configured = platform in PLATFORM_CREDENTIALS
        result[platform] = {
            "configured": configured,
            "fields": fields if configured else [],
            "source": "memory" if configured else "none",
        }
    return jsonify(result)

@app.route("/clear_credentials", methods=["POST"])
def clear_credentials():
    PLATFORM_CREDENTIALS.clear()
    return jsonify({"success": True, "message": "Todas las credenciales eliminadas de memoria"})

# ── Serve uploads ──
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_file(UPLOAD_FOLDER / filename)

# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print(" Stegstr Widget Server v2.2.0")
    print("=" * 60)
    print("\n⚠️  ADVERTENCIA DE SEGURIDAD:")
    print("   Este servidor está diseñado para ejecutarse ÚNICAMENTE en localhost.")
    print("   NO expongas este servidor directamente a Internet.")
    print("   Las credenciales se almacenan solo en RAM y se pierden al reiniciar.")
    print("\n   Endpoints disponibles:")
    print("   - GET  /                    → widget.html")
    print("   - POST /embed               → Ocultar mensaje")
    print("   - POST /extract             → Extraer mensaje")
    print("   - POST /analyze             → Analizar detectabilidad")
    print("   - POST /capacity            → Calcular capacidad real")
    print("   - POST /benchmark           → Benchmark de modo")
    print("   - POST /simulate            → Simular plataforma (RealisticPlatformSimulator)")
    print("   - POST /publish             → Publicar en red social")
    print("   - POST /publish_validate    → Publicar + validación E2E")
    print("   - POST /configure_platform  → Guardar credenciales en RAM")
    print("   - GET  /platform_config     → Listar credenciales configuradas")
    print("   - POST /clear_credentials   → Limpiar credenciales de RAM")
    print("\n   Abre http://127.0.0.1:8080 en tu navegador.\n")
    app.run(host="127.0.0.1", port=8080, debug=False)
