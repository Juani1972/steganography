"""
Stegstr — GUI web local.

Panel de control que corre en tu propia máquina (127.0.0.1) para:
  1. Rellenar credenciales de cada red social desde un formulario y
     guardarlas en el ".env" del proyecto (nunca salen de tu equipo).
  2. Ver de un vistazo qué plataformas están listas.
  3. Lanzar una prueba real (embed -> subir -> descargar -> extraer)
     contra la plataforma elegida y ver el resultado en el navegador.

Lanzamiento:
    cd steganography_repo_v2
    python -m stegstr.gui.web_app
    # abre http://127.0.0.1:8080

Solo escucha en localhost por defecto: nadie fuera de tu máquina puede
acceder a este panel ni a las credenciales que guardes en él.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for

# --------------------------------------------------------------------------
# Rutas base
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # raíz del repo
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"
DEFAULT_COVER = BASE_DIR / "samples" / "hd_2048.png"

# --------------------------------------------------------------------------
# Definición de campos por plataforma (nombre var -> etiqueta, tipo, ayuda)
# --------------------------------------------------------------------------
PLATFORMS = {
    "discord": {
        "label": "Discord",
        "help": "Webhook de canal. Configuración → Integraciones → Webhooks.",
        "fields": [
            ("DISCORD_WEBHOOK_URL", "Webhook URL", "password"),
        ],
    },
    "imgur": {
        "label": "Imgur",
        "help": "Subida anónima. https://api.imgur.com/oauth2/addclient",
        "fields": [
            ("IMGUR_CLIENT_ID", "Client ID", "password"),
        ],
    },
    "telegram": {
        "label": "Telegram",
        "help": "Bot creado con @BotFather.",
        "fields": [
            ("TELEGRAM_BOT_TOKEN", "Bot token", "password"),
            ("TELEGRAM_CHAT_ID", "Chat ID", "text"),
        ],
    },
    "reddit": {
        "label": "Reddit",
        "help": "App tipo 'script' en https://www.reddit.com/prefs/apps",
        "fields": [
            ("REDDIT_CLIENT_ID", "Client ID", "password"),
            ("REDDIT_CLIENT_SECRET", "Client secret", "password"),
            ("REDDIT_USERNAME", "Usuario", "text"),
            ("REDDIT_PASSWORD", "Contraseña", "password"),
            ("REDDIT_SUBREDDIT", "Subreddit de pruebas (opcional, def. 'test')", "text"),
        ],
    },
    "instagram": {
        "label": "Instagram",
        "help": "Cuenta profesional + app de Meta for Developers.",
        "fields": [
            ("INSTAGRAM_BUSINESS_ACCOUNT_ID", "Business Account ID", "text"),
            ("META_PAGE_ACCESS_TOKEN", "Page Access Token (larga duración)", "password"),
            ("NGROK_AUTHTOKEN", "ngrok authtoken (opcional, solo sin IP pública)", "password"),
        ],
    },
    "twitter": {
        "label": "Twitter / X",
        "help": "App con permisos de lectura y escritura en developer.twitter.com",
        "fields": [
            ("TWITTER_BEARER_TOKEN", "Bearer token", "password"),
            ("TWITTER_API_KEY", "API key", "password"),
            ("TWITTER_API_SECRET", "API secret", "password"),
            ("TWITTER_ACCESS_TOKEN", "Access token", "password"),
            ("TWITTER_ACCESS_TOKEN_SECRET", "Access token secret", "password"),
        ],
    },
    "whatsapp": {
        "label": "WhatsApp Business",
        "help": "Requiere verificación de negocio en Meta Business Manager.",
        "fields": [
            ("WHATSAPP_BUSINESS_PHONE_ID", "Phone number ID", "text"),
            ("WHATSAPP_ACCESS_TOKEN", "Access token", "password"),
            ("WHATSAPP_RECIPIENT_PHONE", "Teléfono destino (sin '+')", "text"),
        ],
    },
}

ALL_ENV_KEYS = [k for p in PLATFORMS.values() for k, *_ in p["fields"]]


# --------------------------------------------------------------------------
# Lectura / escritura de .env (sin dependencias externas)
# --------------------------------------------------------------------------
def load_env_file() -> dict:
    """Lee el .env (o .env.example si aún no existe) y devuelve {clave: valor}."""
    path = ENV_PATH if ENV_PATH.exists() else ENV_EXAMPLE_PATH
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        values[key.strip()] = val.strip()
    return values


def apply_env_to_process(values: dict) -> None:
    """Vuelca las claves conocidas al entorno del proceso actual (para que
    los adaptadores las vean vía os.environ.get(...))."""
    for key in ALL_ENV_KEYS:
        if values.get(key):
            os.environ[key] = values[key]


def save_env_file(updates: dict) -> None:
    """
    Actualiza (o crea) el .env con los valores de `updates`, conservando
    comentarios y el resto de líneas si el .env ya existía. Los campos con
    valor vacío en el formulario NO borran un valor ya guardado (para que
    puedas guardar solo la plataforma que estás rellenando sin tener que
    reescribir el resto cada vez).
    """
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    elif ENV_EXAMPLE_PATH.exists():
        lines = ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    seen = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        m = re.match(r"^([A-Z0-9_]+)=(.*)$", stripped) if stripped and not stripped.startswith("#") else None
        if m and m.group(1) in updates:
            key = m.group(1)
            new_val = updates[key]
            if new_val:  # solo sobrescribe si el usuario mandó algo
                new_lines.append(f"{key}={new_val}")
            else:
                new_lines.append(line)  # conserva el valor anterior tal cual
            seen.add(key)
        else:
            new_lines.append(line)

    # Añade al final cualquier clave nueva que no existiera todavía en el fichero
    missing = [k for k, v in updates.items() if k not in seen and v]
    if missing:
        new_lines.append("")
        new_lines.append("# Añadidas desde la GUI")
        for k in missing:
            new_lines.append(f"{k}={updates[k]}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def platform_statuses() -> list:
    """Reutiliza la misma lógica que check_credentials.py, pero también
    intenta reflejar el is_available() real de cada adaptador si el
    paquete stegstr está en el PYTHONPATH."""
    current = load_env_file()
    apply_env_to_process(current)
    result = []
    try:
        sys.path.insert(0, str(BASE_DIR))
        from stegstr.platform.real_world_validator import RealWorldValidator
        adapter_info = {a["name"]: a["available"] for a in RealWorldValidator.list_available_adapters()}
    except Exception:
        adapter_info = {}

    for key, meta in PLATFORMS.items():
        required = [f[0] for f in meta["fields"] if "opcional" not in f[1].lower()]
        configured = all(current.get(k) for k in required)
        result.append({
            "key": key,
            "label": meta["label"],
            "configured": configured,
            "available": adapter_info.get(key, configured),
        })
    return result


# --------------------------------------------------------------------------
# App Flask
# --------------------------------------------------------------------------
app = Flask(__name__)

BASE_CSS = """
:root{
  --bg:#0b0e14; --panel:#121722; --panel-2:#171d2b; --border:#232a3a;
  --text:#e7ecf5; --muted:#8b95ab; --accent:#00e5b0; --accent-dim:#0a3d33;
  --warn:#ffb454; --bad:#ff6b6b; --good:#00e5b0;
  --mono:"JetBrains Mono","SFMono-Regular",Consolas,monospace;
  --sans:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
*{box-sizing:border-box;}
body{
  margin:0; background:var(--bg); color:var(--text); font-family:var(--sans);
  line-height:1.5;
}
header{
  padding:28px 32px 20px; border-bottom:1px solid var(--border);
}
header h1{
  font-family:var(--mono); font-size:20px; letter-spacing:.04em; margin:0 0 4px;
  color:var(--accent);
}
header p{margin:0; color:var(--muted); font-size:14px;}
main{max-width:920px; margin:0 auto; padding:32px;}
.card{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:20px 24px; margin-bottom:18px;
}
table{width:100%; border-collapse:collapse;}
th,td{text-align:left; padding:10px 8px; border-bottom:1px solid var(--border); font-size:14px;}
th{color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.05em;}
.badge{
  display:inline-block; padding:3px 9px; border-radius:100px; font-size:12px;
  font-family:var(--mono);
}
.badge.ok{background:var(--accent-dim); color:var(--accent);}
.badge.no{background:#3a1620; color:var(--bad);}
a.btn, button.btn{
  display:inline-block; background:var(--panel-2); color:var(--text);
  border:1px solid var(--border); padding:6px 14px; border-radius:6px;
  font-size:13px; text-decoration:none; cursor:pointer; font-family:var(--sans);
}
a.btn:hover, button.btn:hover{border-color:var(--accent); color:var(--accent);}
a.btn.primary, button.btn.primary{
  background:var(--accent); color:#03211b; border-color:var(--accent); font-weight:600;
}
a.btn.primary:hover{opacity:.9;}
fieldset{border:1px solid var(--border); border-radius:8px; padding:16px 18px; margin-bottom:16px;}
legend{font-family:var(--mono); color:var(--accent); padding:0 6px; font-size:14px;}
.help{color:var(--muted); font-size:12px; margin:-4px 0 12px;}
label{display:block; font-size:13px; color:var(--muted); margin-bottom:4px; margin-top:10px;}
input[type=text], input[type=password]{
  width:100%; background:var(--bg); border:1px solid var(--border); color:var(--text);
  padding:8px 10px; border-radius:6px; font-family:var(--mono); font-size:13px;
}
input:focus{outline:none; border-color:var(--accent);}
pre{
  background:#05070c; border:1px solid var(--border); border-radius:8px; padding:14px;
  overflow-x:auto; font-family:var(--mono); font-size:12.5px; color:#c9d6e3;
  white-space:pre-wrap; word-break:break-word;
}
.row{display:flex; gap:10px; align-items:center; margin-top:16px;}
.notice{
  background:var(--accent-dim); border:1px solid var(--accent); color:var(--accent);
  padding:10px 14px; border-radius:8px; font-size:13px; margin-bottom:16px;
}
.warn{
  background:#2b2008; border:1px solid var(--warn); color:var(--warn);
  padding:10px 14px; border-radius:8px; font-size:13px; margin-bottom:16px;
}
footer{max-width:920px; margin:0 auto; padding:0 32px 40px; color:var(--muted); font-size:12px;}
"""

DASHBOARD_TMPL = """
<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Stegstr — Panel local</title>
<style>{{ css }}</style></head><body>
<header>
  <h1>&gt; stegstr / panel local</h1>
  <p>Corriendo en 127.0.0.1 — las credenciales que guardes aquí no salen de esta máquina.</p>
</header>
<main>
  {% if flash %}<div class="notice">{{ flash }}</div>{% endif %}
  <div class="warn">
    ⚠️ Este panel guarda credenciales en <code>.env</code> en <strong>texto plano</strong>
    y no tiene autenticación ni protección CSRF: es una herramienta de un solo
    usuario pensada para correr solo en tu máquina (127.0.0.1). No la expongas
    en una red compartida ni en un servidor accesible desde fuera, y confirma
    que <code>.env</code> está en tu <code>.gitignore</code> antes de hacer commit.
  </div>
  <div class="card">
    <table>
      <tr><th>Plataforma</th><th>Credenciales</th><th>Adaptador</th><th></th></tr>
      {% for p in statuses %}
      <tr>
        <td>{{ p.label }}</td>
        <td>{% if p.configured %}<span class="badge ok">configurado</span>{% else %}<span class="badge no">falta</span>{% endif %}</td>
        <td>{% if p.available %}<span class="badge ok">disponible</span>{% else %}<span class="badge no">no disponible</span>{% endif %}</td>
        <td>
          <a class="btn" href="{{ url_for('credentials', focus=p.key) }}">Configurar</a>
          {% if p.available %}<a class="btn primary" href="{{ url_for('test_platform', platform=p.key) }}">Probar</a>{% endif %}
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>
  <div class="card">
    <p style="color:var(--muted); font-size:13px; margin:0;">
      Imagen de portada usada en las pruebas: <code>{{ cover }}</code><br>
      "Probar" ejecuta <code>scripts/real_world_benchmark.py</code> de verdad contra la
      plataforma elegida: ocultará un mensaje, lo subirá, lo descargará y comprobará si
      sobrevive. Puede tardar entre unos segundos y ~1 minuto.
    </p>
  </div>
</main>
<footer>stegstr GUI local · solo accesible desde este equipo</footer>
</body></html>
"""

CREDENTIALS_TMPL = """
<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Stegstr — Credenciales</title>
<style>{{ css }}</style></head><body>
<header>
  <h1>&gt; stegstr / credenciales</h1>
  <p><a class="btn" href="{{ url_for('dashboard') }}">&larr; volver al panel</a></p>
</header>
<main>
  <div class="warn">
    Estas credenciales se guardan en texto plano en <code>.env</code>, en esta misma
    máquina. No compartas ese fichero ni lo subas a git.
  </div>
  <form method="post">
    {% for key, meta in platforms.items() %}
    <fieldset id="{{ key }}" {% if focus==key %}style="border-color:var(--accent)"{% endif %}>
      <legend>{{ meta.label }}</legend>
      <p class="help">{{ meta.help }}</p>
      {% for env_key, field_label, field_type in meta.fields %}
        <label for="{{ env_key }}">{{ field_label }}{% if current.get(env_key) %} — <span style="color:var(--accent)">ya guardado</span>{% endif %}</label>
        <input type="{{ field_type }}" id="{{ env_key }}" name="{{ env_key }}"
               placeholder="{% if current.get(env_key) %}•••••••• (déjalo en blanco para no cambiarlo){% else %}sin configurar{% endif %}">
      {% endfor %}
    </fieldset>
    {% endfor %}
    <div class="row">
      <button class="btn primary" type="submit">Guardar en .env</button>
      <a class="btn" href="{{ url_for('dashboard') }}">Cancelar</a>
    </div>
  </form>
</main>
<footer>Los campos vacíos no borran valores ya guardados — solo se actualiza lo que rellenes.</footer>
</body></html>
"""

TEST_TMPL = """
<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Stegstr — Prueba {{ platform }}</title>
<style>{{ css }}</style></head><body>
<header>
  <h1>&gt; stegstr / prueba real — {{ platform }}</h1>
  <p><a class="btn" href="{{ url_for('dashboard') }}">&larr; volver al panel</a></p>
</header>
<main>
  <div class="card">
    <p style="margin-top:0;">Comando ejecutado:</p>
    <pre>{{ cmd }}</pre>
    <p>Código de salida: <strong style="color:{{ '#00e5b0' if returncode == 0 else '#ff6b6b' }}">{{ returncode }}</strong></p>
  </div>
  <div class="card">
    <p style="margin-top:0; color:var(--muted);">Salida:</p>
    <pre>{{ output }}</pre>
  </div>
</main>
<footer>stegstr GUI local</footer>
</body></html>
"""


@app.route("/")
def dashboard():
    flash = request.args.get("flash", "")
    return render_template_string(
        DASHBOARD_TMPL, css=BASE_CSS, statuses=platform_statuses(),
        cover=str(DEFAULT_COVER.relative_to(BASE_DIR)) if DEFAULT_COVER.exists() else "samples/hd_2048.png",
        flash=flash,
    )


@app.route("/credentials", methods=["GET", "POST"])
def credentials():
    if request.method == "POST":
        updates = {k: request.form.get(k, "").strip() for k in ALL_ENV_KEYS}
        save_env_file(updates)
        apply_env_to_process(load_env_file())
        return redirect(url_for("dashboard", flash="Credenciales guardadas en .env"))
    current = load_env_file()
    focus = request.args.get("focus", "")
    return render_template_string(
        CREDENTIALS_TMPL, css=BASE_CSS, platforms=PLATFORMS, current=current, focus=focus,
    )


@app.route("/test/<platform>")
def test_platform(platform):
    if platform not in PLATFORMS:
        return redirect(url_for("dashboard"))

    apply_env_to_process(load_env_file())

    cover = str(DEFAULT_COVER) if DEFAULT_COVER.exists() else str(BASE_DIR / "samples" / "cover.png")
    message = request.args.get("message", "Mensaje de prueba desde la GUI de stegstr")
    cmd = [
        sys.executable, "scripts/real_world_benchmark.py",
        "--platforms", platform,
        "--cover", cover,
        "--message", message,
        "--verbose",
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=str(BASE_DIR), env=os.environ.copy(),
            capture_output=True, text=True, timeout=180,
        )
        output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        returncode = proc.returncode
    except subprocess.TimeoutExpired as e:
        output = (e.stdout or "") + "\n\n[La prueba superó el tiempo máximo de 180s y se ha cancelado]"
        returncode = -1
    except Exception as e:
        output = f"No se pudo ejecutar la prueba: {e}"
        returncode = -1

    return render_template_string(
        TEST_TMPL, css=BASE_CSS, platform=platform,
        cmd=" ".join(cmd), output=output.strip() or "(sin salida)", returncode=returncode,
    )


def main():
    print("Stegstr GUI local -> http://127.0.0.1:8080  (Ctrl+C para parar)")
    apply_env_to_process(load_env_file())
    # host=127.0.0.1: solo accesible desde esta máquina, a propósito
    # (aquí se manejan credenciales reales de redes sociales).
    app.run(host="127.0.0.1", port=8080, debug=False)


if __name__ == "__main__":
    main()
