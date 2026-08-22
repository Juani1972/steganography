#!/usr/bin/env python3
"""
Stegstr Config Wizard v2.2.0
Gestion interactiva de credenciales para adaptadores de redes sociales.
Guarda en ~/.config/stegstr/credentials.json con permisos 0o600.

Las variables de entorno definidas aqui coinciden con las que usan
stegstr/platform/adapters/*.py y check_credentials.py.
"""
import os
import json
import stat
from pathlib import Path
from getpass import getpass

CONFIG_DIR = Path.home() / ".config" / "stegstr"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

# Variables sincronizadas con check_credentials.py y los adaptadores reales
PLATFORMS = {
    "instagram": {
        "label": "Instagram",
        "env": ["INSTAGRAM_BUSINESS_ACCOUNT_ID", "META_PAGE_ACCESS_TOKEN"],
        "help": "Necesitas una cuenta de negocio de Instagram y un token de acceso de Meta."
    },
    "twitter": {
        "label": "Twitter / X",
        "env": ["TWITTER_BEARER_TOKEN", "TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"],
        "help": "Crea una app en developer.twitter.com para obtener las credenciales."
    },
    "telegram": {
        "label": "Telegram",
        "env": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
        "help": "Habla con @BotFather en Telegram para crear un bot y obtener el token."
    },
    "whatsapp": {
        "label": "WhatsApp",
        "env": ["WHATSAPP_BUSINESS_PHONE_ID", "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_RECIPIENT_PHONE"],
        "help": "Credenciales de la API de WhatsApp Business. Usa el mismo numero como remitente y destinatario para self-messaging."
    },
    "reddit": {
        "label": "Reddit",
        "env": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"],
        "help": "Crea una app en www.reddit.com/prefs/apps"
    },
    "discord": {
        "label": "Discord",
        "env": ["DISCORD_WEBHOOK_URL"],
        "help": "Crea un webhook en la configuracion de un canal de Discord."
    },
    "imgur": {
        "label": "Imgur",
        "env": ["IMGUR_CLIENT_ID"],
        "help": "Registra una app en api.imgur.com para obtener un client ID."
    },
    "nostr": {
        "label": "Nostr",
        "env": ["NOSTR_PRIVATE_KEY"],
        "help": "Clave privada hex de 64 caracteres para Nostr."
    },
}

def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)

def load_credentials():
    if not CREDENTIALS_FILE.exists():
        return {}
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_credentials(creds):
    _ensure_config_dir()
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2, ensure_ascii=False)
    os.chmod(CREDENTIALS_FILE, 0o600)

def set_credential(key, value):
    creds = load_credentials()
    creds[key] = value
    save_credentials(creds)
    os.environ[key] = value
    return True

def get_credential(key, default=None):
    return os.getenv(key) or load_credentials().get(key, default)

def delete_credential(key):
    creds = load_credentials()
    if key in creds:
        del creds[key]
        save_credentials(creds)
        if key in os.environ:
            del os.environ[key]
        return True
    return False

def list_configured():
    creds = load_credentials()
    result = []
    for key, info in PLATFORMS.items():
        missing = [e for e in info["env"] if not os.getenv(e) and not creds.get(e)]
        result.append({
            "key": key,
            "label": info["label"],
            "configured": len(missing) == 0,
            "missing": missing,
            "help": info["help"],
        })
    return result

def run_wizard():
    print("\n" + "=" * 60)
    print(" Stegstr Config Wizard v2.2.0")
    print(" Configuracion de credenciales para redes sociales")
    print("=" * 60 + "\n")
    print("Las credenciales se guardaran en:")
    print(f"  {CREDENTIALS_FILE}")
    print("  (permisos 0o600 — solo tu usuario puede leerlo)\n")
    configured_any = False
    for key, info in PLATFORMS.items():
        print(f"\n--- {info['label']} ---")
        print(f"  {info['help']}")
        missing = [e for e in info["env"] if not get_credential(e)]
        if not missing:
            print(f"  [✓] Ya configurada")
            continue
        resp = input(f"  Configurar {info['label']}? [s/N]: ").strip().lower()
        if resp not in ("s", "si", "yes", "y"):
            print(f"  [ ] Saltada")
            continue
        for env_key in info["env"]:
            current = get_credential(env_key, "")
            prompt = f"    {env_key}"
            if current:
                prompt += f" [actual: {current[:10]}...]"
            prompt += ": "
            if any(x in env_key.lower() for x in ["token", "secret", "password", "key"]):
                value = getpass(prompt)
            else:
                value = input(prompt)
            if value.strip():
                set_credential(env_key, value.strip())
                configured_any = True
        print(f"  [✓] Configurada")
    if configured_any:
        print(f"\n[✓] Credenciales guardadas en {CREDENTIALS_FILE}")
    else:
        print("\n[i] No se configuraron nuevas credenciales.")
    print("\nPara probar una plataforma:")
    print("  stegstr config --test <plataforma>")
    print("Para ver el estado:")
    print("  stegstr config --list\n")

def test_platform(platform_key):
    if platform_key not in PLATFORMS:
        print(f"[✗] Plataforma desconocida: {platform_key}")
        print(f"  Disponibles: {', '.join(PLATFORMS.keys())}")
        return False
    info = PLATFORMS[platform_key]
    missing = [e for e in info["env"] if not get_credential(e)]
    if missing:
        print(f"[✗] {info['label']} — faltan credenciales:")
        for m in missing:
            print(f"  - {m}")
        return False
    print(f"[→] Probando {info['label']}...")
    try:
        from stegstr.platform.adapters import get_adapter
        adapter = get_adapter(platform_key)
        if adapter is None:
            print(f"[✗] Adapter no encontrado para {platform_key}")
            print(f"  Instala dependencias: pip install stegstr[social]")
            return False
        if adapter.is_available():
            print(f"[✓] {info['label']} — conexion OK")
            return True
        else:
            print(f"[✗] {info['label']} — adapter no disponible (credenciales invalidas?)")
            return False
    except ImportError:
        print(f"[✗] Modulo de adaptadores no instalado")
        print(f"  Ejecuta: pip install stegstr[social]")
        return False
    except Exception as e:
        print(f"[✗] Error: {e}")
        return False

def export_env():
    creds = load_credentials()
    if not creds:
        print("# No hay credenciales guardadas")
        return
    for k, v in creds.items():
        print(f'export {k}="{v}"')

# Auto-cargar credenciales al importar el modulo
_ensure_config_dir()
for _k, _v in load_credentials().items():
    if _k not in os.environ:
        os.environ[_k] = _v
