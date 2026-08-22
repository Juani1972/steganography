#!/usr/bin/env python3
"""
Stegstr Widget Server v2.2.0
Backend Flask para la SPA widget.html.
"""

import os
import sys
import json
import time
import hashlib
import tempfile
import traceback as tb_mod
from pathlib import Path
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import numpy as np

# -- Paths --
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.simulator_v2 import RealisticPlatformSimulator
from stegstr.platform.adapters import (
    TelegramAdapter, DiscordAdapter, ImgurAdapter, RedditAdapter,
    TwitterAdapter, InstagramAdapter, WhatsAppAdapter, NostrAdapter
)

# -- Flask App --
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {"origins": ["http://127.0.0.1:8080", "http://localhost:8080"]},
    r"/*":      {"origins": ["http://127.0.0.1:8080", "http://localhost:8080"]}
})

UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "stegstr_widget"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# -- In-memory credential store (RAM only) --
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

# ================================================================
# Helpers
# ================================================================

def _save_upload(file_storage, prefix="upload") -> Path:
    ext = Path(file_storage.filename).suffix or ".png"
    name = f"{prefix}_{int(time.time()*1000)}_{hashlib.md5(file_storage.filename.encode()).hexdigest()[:8]}{ext}"
    path = UPLOAD_FOLDER / name
    file_storage.save(str(path))
    return path

def _inject_credentials(platform, credentials):
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

def _get_mode(mode_str):
    if not mode_str or mode_str.lower() == "hybrid":
        return None
    mode_map = {
        "fortress": StegoMode.FORTRESS,
        "armor":    StegoMode.ARMOR,
        "ghost":    StegoMode.GHOST,
        "phantom":  StegoMode.PHANTOM,
    }
    return mode_map.get(mode_str.lower())

def _safe_extract(engine, stego_path, expected_mode=None):
    try:
        result = engine.extract(stego_path, expected_mode=expected_mode)
        if result is None:
            return None
        if isinstance(result, dict):
            return result
        if isinstance(result, str):
            return {
                "message": result,
                "mode": expected_mode.name if expected_mode else "unknown",
                "encoding": "utf-8",
                "raw_bytes": len(result.encode("utf-8"))
            }
        return None
    except Exception as e:
        print(f"[EXTRACT ERROR] {e}")
        tb_mod.print_exc()
        return None

# ================================================================
# Endpoints
# ================================================================

@app.route("/")
def index():
    return send_file(Path(__file__).parent / "widget.html")

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
        engine = StegoEngine(password=password or None)

        delta = None
        ecc = None
        if autotune and platform:
            tune_result = engine.auto_tune(cover_path, message, platform)
            mode = tune_result.get("mode", mode)
            delta = tune_result.get("delta")
            ecc = tune_result.get("ecc")

        stego_path = str(UPLOAD_FOLDER / f"stego_{int(time.time())}.png")
        result = engine.embed(
            cover_path, message, stego_path,
            mode=mode,
            target_platform=platform or None,
            delta_override=delta,
            ecc_override=ecc,
        )

        if not Path(stego_path).exists():
            return jsonify({"success": False, "error": "No se genero imagen stego"}), 500

        ext = ".png"
        out_name = f"stego_{int(time.time())}{ext}"
        out_path = UPLOAD_FOLDER / out_name
        import shutil
        shutil.copy(stego_path, out_path)

        return jsonify({
            "success": True,
            "stego_url": f"/uploads/{out_name}",
            "mode": result.get("mode", "HYBRID"),
            "capacity_bits": result.get("capacity_bits"),
            "message_bytes": result.get("message_bytes"),
            "quality_metrics": result.get("quality_metrics", {}),
            "platform": platform,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

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
        engine = StegoEngine(password=password or None)
        result = _safe_extract(engine, stego_path, expected_mode=mode)

        if result is None:
            return jsonify({
                "success": False,
                "error": "No se encontro mensaje. Verifica: (1) que la imagen contiene un mensaje stego, (2) que usas la contrasena correcta si aplica, (3) que el modo coincide con el usado al ocultar."
            }), 400

        return jsonify({
            "success": True,
            "message": result.get("message", ""),
            "mode": result.get("mode", "unknown"),
            "encoding": result.get("encoding", "utf-8"),
            "raw_bytes": result.get("raw_bytes", 0),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

@app.route("/extract_url", methods=["POST"])
def extract_url():
    try:
        stego_url = request.form.get("stego_url", "")
        mode_str = request.form.get("mode", "")
        password = request.form.get("password", "")

        if not stego_url:
            return jsonify({"success": False, "error": "Falta stego_url"}), 400

        if stego_url.startswith("/uploads/"):
            filename = stego_url.replace("/uploads/", "")
            stego_path = UPLOAD_FOLDER / filename
        elif stego_url.startswith("/"):
            filename = stego_url.lstrip("/")
            stego_path = UPLOAD_FOLDER / filename
        else:
            return jsonify({"success": False, "error": "URL invalida"}), 400

        if not stego_path.exists():
            return jsonify({"success": False, "error": f"Archivo no encontrado: {stego_path}"}), 404

        mode = _get_mode(mode_str) if mode_str else None
        engine = StegoEngine(password=password or None)
        result = _safe_extract(engine, stego_path, expected_mode=mode)

        if result is None:
            return jsonify({
                "success": False,
                "error": "No se encontro mensaje. Verifica: (1) que la imagen contiene un mensaje stego, (2) que usas la contrasena correcta si aplica, (3) que el modo coincide con el usado al ocultar."
            }), 400

        return jsonify({
            "success": True,
            "message": result.get("message", ""),
            "mode": result.get("mode", "unknown"),
            "encoding": result.get("encoding", "utf-8"),
            "raw_bytes": result.get("raw_bytes", 0),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        cover = request.files.get("cover")
        stego = request.files.get("stego")
        if not cover or not stego:
            return jsonify({"success": False, "error": "Faltan ambas imagenes"}), 400

        cover_path = _save_upload(cover, "cover")
        stego_path = _save_upload(stego, "stego")

        cover_img = Image.open(cover_path).convert("RGB")
        stego_img = Image.open(stego_path).convert("RGB")

        if cover_img.size != stego_img.size:
            stego_img = stego_img.resize(cover_img.size, Image.LANCZOS)

        c_arr = np.array(cover_img, dtype=np.float32)
        s_arr = np.array(stego_img, dtype=np.float32)

        mse = np.mean((c_arr - s_arr) ** 2)
        psnr = 20 * np.log10(255.0 / np.sqrt(mse)) if mse > 0 else float("inf")

        diff = np.abs(c_arr - s_arr)
        diff_mean = np.mean(diff)
        diff_max = np.max(diff)

        return jsonify({
            "success": True,
            "psnr_db": round(float(psnr), 2),
            "mse": round(float(mse), 4),
            "diff_mean": round(float(diff_mean), 2),
            "diff_max": int(diff_max),
            "cover_size": cover_img.size,
            "stego_size": stego_img.size,
            "note": "Analisis basico (PSNR/MSE/diff).",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

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
        mode = _get_mode(mode_str) or StegoMode.ARMOR
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
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

@app.route("/benchmark", methods=["POST"])
def benchmark():
    try:
        cover = request.files.get("cover")
        message = request.form.get("message", "Mensaje de prueba")
        mode_str = request.form.get("mode", "ARMOR")

        if not cover:
            return jsonify({"success": False, "error": "Falta imagen"}), 400

        cover_path = _save_upload(cover, "cover")
        mode = _get_mode(mode_str) or StegoMode.ARMOR
        import time as time_mod
        engine = StegoEngine()

        t0 = time_mod.time()
        stego_path = str(UPLOAD_FOLDER / f"bench_{int(time_mod.time()*1000)}.png")
        meta = engine.embed(cover_path, message, stego_path, mode=mode)
        t_embed = time_mod.time() - t0

        t0 = time_mod.time()
        result = _safe_extract(engine, stego_path, expected_mode=mode)
        t_extract = time_mod.time() - t0

        success = result is not None and result.get("message") == message

        return jsonify({
            "success": True,
            "mode": mode.name if mode else "HYBRID",
            "embed_time_ms": round(t_embed * 1000, 2),
            "extract_time_ms": round(t_extract * 1000, 2),
            "roundtrip_ok": success,
            "capacity_bits": meta.get("capacity_bits"),
            "message_bytes": meta.get("message_bytes"),
            "psnr_db": meta.get("quality_metrics", {}).get("psnr_db"),
            "note": "Benchmark basico (embed/extract/roundtrip).",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

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
        if mode is None:
            mode = StegoMode.ARMOR

        engine = StegoEngine()
        stego_path = str(UPLOAD_FOLDER / f"sim_stego_{int(time.time()*1000)}.png")
        meta = engine.embed(cover_path, message, stego_path, mode=mode)

        sim = RealisticPlatformSimulator()
        processed_path = str(UPLOAD_FOLDER / f"sim_proc_{int(time.time()*1000)}.jpg")

        try:
            sim_result = sim.simulate(platform, stego_path, processed_path)
        except Exception as sim_e:
            return jsonify({
                "success": False,
                "error": f"Error en simulador: {sim_e}",
                "traceback": tb_mod.format_exc(),
                "mode_used": meta.get("mode"),
            }), 500

        extracted = _safe_extract(engine, processed_path, expected_mode=mode)
        survived = extracted is not None and extracted.get("message") == message

        return jsonify({
            "success": True,
            "platform": platform,
            "survived": survived,
            "mode_used": meta.get("mode"),
            "transformations": sim_result.get("transformations", []),
            "original_size": sim_result.get("original_size"),
            "final_size": sim_result.get("final_size"),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

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
        result = adapter.publish(image_path, caption=caption)

        return jsonify({
            "success": result.get("success", False),
            "url": result.get("url", ""),
            "platform": platform,
            "message": result.get("message", ""),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

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
                "error": pub_result.get("error", "Error en publicacion"),
                "platform": platform,
            }), 500

        url = pub_result.get("url", "")
        e2e = {"success": False, "url": url, "platform": platform}

        if url and hasattr(adapter, "download"):
            try:
                downloaded = adapter.download(url)
                if downloaded:
                    downloaded_path = UPLOAD_FOLDER / f"downloaded_{int(time.time()*1000)}.png"
                    with open(downloaded_path, "wb") as f:
                        f.write(downloaded)
                    downloaded_hash = hashlib.sha256(downloaded).hexdigest()

                    e2e["original_size"] = image_path.stat().st_size
                    e2e["downloaded_size"] = len(downloaded)
                    e2e["original_hash"] = original_hash
                    e2e["downloaded_hash"] = downloaded_hash
                    e2e["hash_match"] = original_hash == downloaded_hash

                    if mode_str and mode_str != "auto":
                        engine = StegoEngine()
                        mode = _get_mode(mode_str)
                        ext_result = _safe_extract(engine, downloaded_path, expected_mode=mode)
                        if ext_result:
                            e2e["extracted_message"] = ext_result.get("message", "")

                    try:
                        orig = Image.open(image_path).convert("RGB")
                        down = Image.open(downloaded_path).convert("RGB")
                        if orig.size != down.size:
                            down = down.resize(orig.size, Image.LANCZOS)
                        o_arr = np.array(orig, dtype=np.float32)
                        d_arr = np.array(down, dtype=np.float32)
                        mse = np.mean((o_arr - d_arr) ** 2)
                        psnr = 20 * np.log10(255.0 / np.sqrt(mse)) if mse > 0 else float("inf")
                        e2e["psnr"] = round(float(psnr), 2)
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
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

@app.route("/configure_platform", methods=["POST"])
def configure_platform():
    try:
        data = request.get_json(force=True)
        platform = data.get("platform", "").lower()
        credentials = data.get("credentials", {})

        if not platform or platform not in PLATFORM_CREDENTIAL_FIELDS:
            return jsonify({"success": False, "error": "Plataforma no valida"}), 400

        PLATFORM_CREDENTIALS[platform] = credentials
        _inject_credentials(platform, credentials)

        return jsonify({
            "success": True,
            "message": f"Credenciales de {platform} guardadas en memoria",
            "platform": platform,
            "fields": list(credentials.keys()),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": tb_mod.format_exc()}), 500

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

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_file(UPLOAD_FOLDER / filename)

if __name__ == "__main__":
    print("=" * 60)
    print(" Stegstr Widget Server v2.2.0")
    print("=" * 60)
    print("")
    print(" ADVERTENCIA DE SEGURIDAD:")
    print("   Este servidor esta disenado para ejecutarse UNICAMENTE en localhost.")
    print("   NO expongas este servidor directamente a Internet.")
    print("   Las credenciales se almacenan solo en RAM y se pierden al reiniciar.")
    print("")
    print("   Abre http://127.0.0.1:8080 en tu navegador.")
    print("")
    app.run(host="127.0.0.1", port=8080, debug=False)
