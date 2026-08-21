#!/usr/bin/env python3
"""
Stegstr Control Center v2.2.0
Interfaz web alternativa (wizard-style) para esteganografía LSB avanzada.

Correcciones v2.2.0:
- Eliminada plataforma "Signal" (sin adaptador real)
- Credenciales unificadas con adaptadores:
  · Instagram: Business Account ID + Meta Page Access Token
  · WhatsApp: Business Phone ID + Access Token + Recipient Phone
  · Twitter/X: TWITTER_ACCESS_TOKEN_SECRET (nombre corregido)
- Capacidad: consulta POST /capacity (backend) en lugar de valores hardcoded
- Barra de capacidad: compara bytes_mensaje / capacidad_real (no tamaño_imagen / cap)
- Simulador: RealisticPlatformSimulator (unificado con widget_server.py)
- Añadido endpoint /api/capacity
"""

import os, sys, json, time, hashlib, tempfile, base64
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.stego.analyzer import StegoAnalyzer
from stegstr.platform.simulator import RealisticPlatformSimulator
from stegstr.platform.adapters import (
    TelegramAdapter, DiscordAdapter, ImgurAdapter, RedditAdapter,
    TwitterAdapter, InstagramAdapter, WhatsAppAdapter, NostrAdapter
)

app = Flask(__name__)
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "stegstr_webapp"
UPLOAD_FOLDER.mkdir(exist_ok=True)

PLATFORMS = [
    {"key": "telegram",      "label": "Telegram",      "env": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]},
    {"key": "discord",       "label": "Discord",       "env": ["DISCORD_WEBHOOK_URL"]},
    {"key": "imgur",         "label": "Imgur",         "env": ["IMGUR_CLIENT_ID"]},
    {"key": "reddit",        "label": "Reddit",        "env": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"]},
    {"key": "twitter",       "label": "Twitter / X",   "env": ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"]},
    {"key": "instagram",     "label": "Instagram",     "env": ["INSTAGRAM_BUSINESS_ACCOUNT_ID", "META_PAGE_ACCESS_TOKEN"]},
    {"key": "whatsapp",      "label": "WhatsApp",      "env": ["WHATSAPP_BUSINESS_PHONE_ID", "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_RECIPIENT_PHONE"]},
    {"key": "nostr",         "label": "Nostr",         "env": ["NOSTR_PRIVATE_KEY"]},
]

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

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stegstr Control Center v2.2.0</title>
<style>
:root {
  --bg: #0b0f14; --surface: #111820; --surface-hover: #17202a;
  --border: #1e2a35; --border-hover: #2a3a4a;
  --text: #d8dee4; --text-dim: #7a8899; --text-bright: #e8eef4;
  --accent: #4dabf7; --accent-glow: rgba(77,171,247,0.25);
  --accent2: #51cf66; --accent2-glow: rgba(81,207,102,0.25);
  --danger: #ff6b6b; --warning: #ffd43b;
  --font: 'Segoe UI', system-ui, sans-serif;
  --mono: 'SF Mono', 'Fira Code', monospace;
  --radius: 8px; --shadow: 0 2px 8px rgba(0,0,0,0.4);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font); background: var(--bg); color: var(--text); min-height: 100vh; }
.container { max-width: 900px; margin: 0 auto; padding: 24px 16px; }
header { text-align: center; margin-bottom: 28px; }
header h1 { font-size: 1.8rem; color: var(--text-bright); }
header p { color: var(--text-dim); font-size: 0.85rem; margin-top: 4px; }

.step-nav { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 2px; overflow-x: auto; }
.step-btn { background: transparent; border: none; border-bottom: 2px solid transparent; color: var(--text-dim); padding: 10px 14px; cursor: pointer; font-size: 0.8rem; font-weight: 500; white-space: nowrap; transition: all 0.2s; }
.step-btn:hover { color: var(--text); }
.step-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

.step { display: none; }
.step.active { display: block; }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; margin-bottom: 16px; box-shadow: var(--shadow); }
.card h2 { font-size: 1rem; font-weight: 600; margin-bottom: 14px; color: var(--text-bright); }
label { display: block; font-size: 0.75rem; color: var(--text-dim); margin-bottom: 4px; font-weight: 500; }
input, textarea, select { width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 8px 10px; border-radius: 6px; font-size: 0.85rem; outline: none; transition: all 0.2s; font-family: var(--font); }
input:focus, textarea:focus, select:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }
textarea { resize: vertical; min-height: 60px; font-family: var(--mono); font-size: 0.8rem; }
select { cursor: pointer; appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%237a8899' d='M6 8L1 3h10z'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 8px center; padding-right: 26px; }

.btn { display: inline-flex; align-items: center; gap: 6px; background: var(--accent); color: #0b0f14; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600; transition: all 0.2s; }
.btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px var(--accent-glow); }
.btn-success { background: var(--accent2); }
.btn-success:hover { box-shadow: 0 4px 12px var(--accent2-glow); }
.btn-secondary { background: var(--surface-hover); color: var(--text); border: 1px solid var(--border); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }

.dropzone { border: 2px dashed var(--border); border-radius: var(--radius); padding: 24px 16px; text-align: center; color: var(--text-dim); cursor: pointer; transition: all 0.2s; margin-bottom: 10px; background: var(--bg); }
.dropzone:hover { border-color: var(--accent); color: var(--accent); }
.dropzone input { display: none; }

.preview-img { max-width: 100%; max-height: 200px; border-radius: 6px; border: 1px solid var(--border); display: none; margin-top: 6px; }

.result-box { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin-top: 10px; font-family: var(--mono); font-size: 0.78rem; white-space: pre-wrap; max-height: 240px; overflow-y: auto; color: var(--text-dim); }

.metric { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid var(--border); font-size: 0.8rem; }
.metric:last-child { border-bottom: none; }
.metric .value { font-family: var(--mono); color: var(--accent); font-weight: 500; }

.progress-bar { width: 100%; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; margin-top: 6px; }
.progress-bar .fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.3s; width: 0%; }

.platform-card { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 10px 12px; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; }
.platform-card .name { font-weight: 600; font-size: 0.85rem; color: var(--text-bright); }
.platform-card .status { font-size: 0.7rem; padding: 2px 6px; border-radius: 10px; }
.status-ok { background: rgba(81,207,102,0.12); color: var(--accent2); }
.status-missing { background: rgba(255,107,107,0.12); color: var(--danger); }
.status-warn { background: rgba(255,212,59,0.12); color: var(--warning); }

.nav-btns { display: flex; gap: 8px; margin-top: 16px; }

footer { text-align: center; margin-top: 24px; padding-top: 12px; border-top: 1px solid var(--border); color: var(--text-dim); font-size: 0.75rem; }

@media (max-width: 560px) { .container { padding: 16px 10px; } header h1 { font-size: 1.4rem; } }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🔐 Stegstr Control Center <span style="color:var(--accent);font-weight:300;font-size:1rem">v2.2.0</span></h1>
    <p>Wizard de esteganografía LSB avanzada con publicación a redes sociales</p>
  </header>

  <nav class="step-nav">
    <button class="step-btn active" data-step="0">1. Plataforma</button>
    <button class="step-btn" data-step="1">2. Mensaje</button>
    <button class="step-btn" data-step="2">3. Ocultar</button>
    <button class="step-btn" data-step="3">4. Simular</button>
    <button class="step-btn" data-step="4">5. Publicar</button>
  </nav>

  <!-- Step 0: Platform -->
  <div class="step active" data-step="0">
    <div class="card">
      <h2>1️⃣ Selecciona la plataforma objetivo</h2>
      <p style="color:var(--text-dim);font-size:0.8rem;margin-bottom:12px">
        Esto configura el simulador y las credenciales necesarias.
      </p>
      <select id="platformSelect">
        <option value="">-- Selecciona plataforma --</option>
        {% for p in platforms %}
        <option value="{{ p.key }}">{{ p.label }}</option>
        {% endfor %}
      </select>
      <div id="platformInfo" style="margin-top:12px"></div>
    </div>
  </div>

  <!-- Step 1: Message -->
  <div class="step" data-step="1">
    <div class="card">
      <h2>2️⃣ Escribe tu mensaje secreto</h2>
      <label>Mensaje</label>
      <textarea id="messageText" placeholder="Escribe aquí tu mensaje..."></textarea>
      <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
        <label style="margin:0; display:flex; align-items:center; gap:4px; cursor:pointer; font-size:0.8rem">
          <input type="checkbox" id="usePassword" style="width:auto"> Usar contraseña
        </label>
        <input type="text" id="passwordInput" placeholder="Contraseña" style="display:none; flex:1; margin-bottom:0">
      </div>
      <div style="margin-top:8px; font-size:0.75rem; color:var(--text-dim)">
        <span id="msgBytes">0</span> bytes | Modo sugerido: <span id="suggestedMode">HYBRID</span>
      </div>
    </div>
  </div>

  <!-- Step 2: Hide -->
  <div class="step" data-step="2">
    <div class="card">
      <h2>3️⃣ Selecciona imagen y oculta el mensaje</h2>
      <label>Imagen portadora</label>
      <div class="dropzone" id="hideDrop">
        <div>📁 Arrastra imagen o haz clic para seleccionar</div>
        <input type="file" id="hideFile" accept="image/*">
      </div>
      <img class="preview-img" id="hidePreview">

      <label style="margin-top:10px">Modo de estego</label>
      <select id="hideMode">
        <option value="HYBRID" selected>HYBRID (auto-selección)</option>
        <option value="FORTRESS">FORTRESS (máxima robustez)</option>
        <option value="ARMOR">ARMOR (robustez + capacidad)</option>
        <option value="GHOST">GHOST (máxima capacidad PNG)</option>
        <option value="PHANTOM">PHANTOM (anti-detección LSB-M)</option>
      </select>

      <div style="margin-top:10px">
        <div class="metric"><span>Capacidad estimada:</span><span class="value" id="capValue">--</span></div>
        <div class="progress-bar"><div class="fill" id="capBar"></div></div>
        <div style="font-size:0.7rem; color:var(--text-dim); margin-top:4px" id="capHint"></div>
      </div>

      <div class="nav-btns">
        <button class="btn btn-success" id="hideBtn">🚀 Ocultar mensaje</button>
      </div>
      <div class="result-box" id="hideResult" style="display:none"></div>
      <div id="hideDownload" style="margin-top:8px; display:none">
        <a class="btn" id="hideLink" download="stego.png">⬇️ Descargar</a>
      </div>
    </div>
  </div>

  <!-- Step 3: Simulate -->
  <div class="step" data-step="3">
    <div class="card">
      <h2>4️⃣ Simular paso por la plataforma</h2>
      <p style="color:var(--text-dim);font-size:0.8rem;margin-bottom:10px">
        Simula cómo la plataforma comprimirá o modificará la imagen stego.
      </p>
      <div class="nav-btns">
        <button class="btn btn-success" id="simulateBtn">⚡ Simular</button>
      </div>
      <div class="result-box" id="simulateResult" style="display:none"></div>
    </div>
  </div>

  <!-- Step 4: Publish -->
  <div class="step" data-step="4">
    <div class="card">
      <h2>5️⃣ Publicar en la plataforma</h2>
      <p style="color:var(--text-dim);font-size:0.8rem;margin-bottom:10px">
        Sube la imagen stego a la plataforma seleccionada.
      </p>
      <div id="credStatus" style="margin-bottom:12px"></div>
      <div class="nav-btns">
        <button class="btn btn-success" id="publishBtn">📡 Publicar</button>
        <button class="btn btn-warning" id="publishValidateBtn">✅ Publicar + Validar E2E</button>
      </div>
      <div class="result-box" id="publishResult" style="display:none"></div>
      <div id="publishUrlBox" style="margin-top:8px; display:none">
        <label>URL</label>
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;font-family:var(--mono);font-size:0.75rem;word-break:break-all;color:var(--accent);cursor:pointer" id="pubUrl" title="Haz clic para copiar"></div>
      </div>
    </div>
  </div>

  <div class="nav-btns" style="justify-content:center; margin-top:20px">
    <button class="btn btn-secondary" id="prevBtn" disabled>← Anterior</button>
    <button class="btn btn-secondary" id="nextBtn">Siguiente →</button>
  </div>

  <footer>
    Stegstr Control Center v2.2.0 — Local-only. No expongas a redes públicas.
  </footer>
</div>

<script>
const platforms = {{ platforms_json | safe }};
let currentStep = 0;
let stegoData = null;
let lastCapacity = 0;

function showStep(n) {
  currentStep = n;
  document.querySelectorAll('.step').forEach(s => s.classList.toggle('active', parseInt(s.dataset.step) === n));
  document.querySelectorAll('.step-btn').forEach(b => b.classList.toggle('active', parseInt(b.dataset.step) === n));
  document.getElementById('prevBtn').disabled = n === 0;
  document.getElementById('nextBtn').disabled = n === 4;
}

document.querySelectorAll('.step-btn').forEach(b => {
  b.addEventListener('click', () => showStep(parseInt(b.dataset.step)));
});
document.getElementById('prevBtn').addEventListener('click', () => showStep(Math.max(0, currentStep - 1)));
document.getElementById('nextBtn').addEventListener('click', () => showStep(Math.min(4, currentStep + 1)));

// Platform selection
const platformSelect = document.getElementById('platformSelect');
const platformInfo = document.getElementById('platformInfo');

platformSelect.addEventListener('change', () => {
  const key = platformSelect.value;
  if (!key) { platformInfo.innerHTML = ''; return; }
  const p = platforms.find(x => x.key === key);
  if (!p) return;

  let html = '<div style="margin-top:8px">';
  p.env.forEach(e => {
    const set = !!localStorage.getItem(e);
    html += `<div class="platform-card">
      <span class="name">${e}</span>
      <span class="status ${set ? 'status-ok' : 'status-missing'}">${set ? '✅ Configurado' : '❌ No configurado'}</span>
    </div>`;
  });
  html += '</div>';
  html += '<p style="color:var(--text-dim);font-size:0.75rem;margin-top:8px">';
  html += 'Las credenciales se guardan en localStorage del navegador. ';
  html += 'Para configurarlas, usa el panel de credenciales o define variables de entorno en el servidor.';
  html += '</p>';
  platformInfo.innerHTML = html;
});

// Message typing
const msgText = document.getElementById('messageText');
const msgBytes = document.getElementById('msgBytes');
const usePassword = document.getElementById('usePassword');
const passwordInput = document.getElementById('passwordInput');

usePassword.addEventListener('change', () => {
  passwordInput.style.display = usePassword.checked ? 'block' : 'none';
});

msgText.addEventListener('input', () => {
  const bytes = new Blob([msgText.value]).size;
  msgBytes.textContent = bytes;
  updateCapacityBar();
});

// Hide dropzone
const hideDrop = document.getElementById('hideDrop');
const hideFile = document.getElementById('hideFile');
const hidePreview = document.getElementById('hidePreview');

hideDrop.addEventListener('click', () => hideFile.click());
hideDrop.addEventListener('dragover', e => { e.preventDefault(); hideDrop.style.borderColor = 'var(--accent)'; });
hideDrop.addEventListener('dragleave', () => hideDrop.style.borderColor = 'var(--border)');
hideDrop.addEventListener('drop', e => {
  e.preventDefault(); hideDrop.style.borderColor = 'var(--border)';
  if (e.dataTransfer.files.length) {
    hideFile.files = e.dataTransfer.files;
    showPreview(hideFile.files[0], hidePreview);
    checkCapacity();
  }
});
hideFile.addEventListener('change', () => {
  if (hideFile.files.length) { showPreview(hideFile.files[0], hidePreview); checkCapacity(); }
});

function showPreview(file, img) {
  const r = new FileReader();
  r.onload = e => { img.src = e.target.result; img.style.display = 'block'; };
  r.readAsDataURL(file);
}

// ── CAPACIDAD REAL vía backend ──
async function checkCapacity() {
  const file = hideFile.files[0];
  const mode = document.getElementById('hideMode').value;
  const platform = platformSelect.value;
  if (!file) return;

  const fd = new FormData();
  fd.append('cover', file);
  fd.append('mode', mode);
  if (platform) fd.append('platform', platform);

  try {
    const res = await fetch('/api/capacity', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.success) {
      lastCapacity = data.capacity_bytes;
      document.getElementById('capValue').textContent = data.capacity_bytes + ' B (' + data.capacity_kb + ' KB)';
      updateCapacityBar();
    }
  } catch (e) {
    console.error('Error consultando capacidad:', e);
  }
}

document.getElementById('hideMode').addEventListener('change', checkCapacity);

function updateCapacityBar() {
  const msgLen = new Blob([msgText.value]).size;
  const cap = lastCapacity || 1;
  const pct = Math.min(100, (msgLen / cap) * 100);
  document.getElementById('capBar').style.width = pct + '%';
  document.getElementById('capBar').style.background = pct > 90 ? 'var(--danger)' : (pct > 70 ? 'var(--warning)' : 'var(--accent)');
  document.getElementById('capHint').textContent = `Mensaje: ${msgLen} B / Capacidad: ${cap} B (${pct.toFixed(1)}%)`;
}

// Hide
async function doHide() {
  const file = hideFile.files[0];
  const msg = msgText.value;
  const mode = document.getElementById('hideMode').value;
  const platform = platformSelect.value;
  const password = usePassword.checked ? passwordInput.value : '';
  if (!file || !msg) return alert('Falta imagen o mensaje');

  const fd = new FormData();
  fd.append('cover', file);
  fd.append('message', msg);
  fd.append('mode', mode);
  if (platform) fd.append('platform', platform);
  if (password) fd.append('password', password);

  const res = await fetch('/api/hide', { method: 'POST', body: fd });
  const data = await res.json();
  const box = document.getElementById('hideResult');
  box.style.display = 'block';
  box.textContent = JSON.stringify(data, null, 2);
  if (data.success && data.stego_url) {
    stegoData = data;
    document.getElementById('hideLink').href = data.stego_url;
    document.getElementById('hideDownload').style.display = 'block';
  }
}
document.getElementById('hideBtn').addEventListener('click', doHide);

// Simulate
async function doSimulate() {
  if (!stegoData || !stegoData.stego_url) return alert('Primero oculta un mensaje');
  const platform = platformSelect.value || 'telegram_photo';
  const res = await fetch('/api/simulate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({stego_url: stegoData.stego_url, platform}),
  });
  const data = await res.json();
  const box = document.getElementById('simulateResult');
  box.style.display = 'block';
  box.textContent = JSON.stringify(data, null, 2);
}
document.getElementById('simulateBtn').addEventListener('click', doSimulate);

// Publish
async function doPublish(validate=false) {
  if (!stegoData || !stegoData.stego_url) return alert('Primero oculta un mensaje');
  const platform = platformSelect.value;
  if (!platform) return alert('Selecciona una plataforma');

  // Recuperar credenciales de localStorage
  const p = platforms.find(x => x.key === platform);
  const creds = {};
  p.env.forEach(e => {
    const v = localStorage.getItem(e);
    if (v) creds[e] = v;
  });

  const res = await fetch(validate ? '/api/publish_validate' : '/api/publish', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({stego_url: stegoData.stego_url, platform, credentials: creds}),
  });
  const data = await res.json();
  const box = document.getElementById('publishResult');
  box.style.display = 'block';
  box.textContent = JSON.stringify(data, null, 2);

  if (data.url) {
    document.getElementById('pubUrl').textContent = data.url;
    document.getElementById('pubUrl').onclick = () => navigator.clipboard.writeText(data.url);
    document.getElementById('publishUrlBox').style.display = 'block';
  }
}
document.getElementById('publishBtn').addEventListener('click', () => doPublish(false));
document.getElementById('publishValidateBtn').addEventListener('click', () => doPublish(true));

showStep(0);
</script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════
# Backend routes
# ═══════════════════════════════════════════════════════════════

def _save_upload(file_storage, prefix="upload") -> Path:
    ext = Path(file_storage.filename).suffix or ".png"
    name = f"{prefix}_{int(time.time()*1000)}_{hashlib.md5(file_storage.filename.encode()).hexdigest()[:8]}{ext}"
    path = UPLOAD_FOLDER / name
    file_storage.save(str(path))
    return path

def _get_mode(mode_str: str) -> StegoMode:
    mode_map = {
        "fortress": StegoMode.FORTRESS, "armor": StegoMode.ARMOR,
        "ghost": StegoMode.GHOST, "phantom": StegoMode.PHANTOM,
        "hybrid": StegoMode.HYBRID,
    }
    return mode_map.get(mode_str.lower(), StegoMode.HYBRID)

@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        platforms=PLATFORMS,
        platforms_json=json.dumps(PLATFORMS),
    )

@app.route("/api/hide", methods=["POST"])
def api_hide():
    try:
        cover = request.files.get("cover")
        message = request.form.get("message", "")
        mode_str = request.form.get("mode", "HYBRID")
        platform = request.form.get("platform", "")
        password = request.form.get("password", "")
        if not cover or not message:
            return jsonify({"success": False, "error": "Falta imagen o mensaje"}), 400

        cover_path = _save_upload(cover, "cover")
        mode = _get_mode(mode_str)
        engine = StegoEngine()
        kwargs = {"password": password} if password else {}
        result = engine.hide(cover_path, message, mode=mode, **kwargs)
        stego_path = result.get("stego_path")
        if not stego_path or not Path(stego_path).exists():
            return jsonify({"success": False, "error": "No se generó imagen stego"}), 500

        ext = Path(stego_path).suffix
        out_name = f"stego_{int(time.time())}{ext}"
        out_path = UPLOAD_FOLDER / out_name
        import shutil
        shutil.copy(stego_path, out_path)

        return jsonify({
            "success": True, "stego_url": f"/uploads/{out_name}",
            "mode": mode_str, "capacity_used": result.get("capacity_used"), "psnr": result.get("psnr"),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/capacity", methods=["POST"])
def api_capacity():
    """NUEVO: Calcula capacidad real consultando el motor."""
    try:
        cover = request.files.get("cover")
        mode_str = request.form.get("mode", "ARMOR")
        platform = request.form.get("platform", "")
        if not cover:
            return jsonify({"success": False, "error": "Falta imagen"}), 400
        cover_path = _save_upload(cover, "cover")
        mode = _get_mode(mode_str)
        engine = StegoEngine()
        kwargs = {"mode": mode}
        if platform:
            kwargs["platform"] = platform
        cap = engine.get_capacity(cover_path, **kwargs)
        return jsonify({
            "success": True, "capacity_bytes": cap,
            "capacity_kb": round(cap / 1024, 2), "mode": mode_str, "platform": platform,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """CORREGIDO: Usa RealisticPlatformSimulator (unificado con widget_server.py)."""
    try:
        data = request.get_json(force=True)
        stego_url = data.get("stego_url", "")
        platform = data.get("platform", "telegram_photo")
        if not stego_url:
            return jsonify({"success": False, "error": "Falta stego_url"}), 400

        # stego_url es relativo tipo /uploads/...
        filename = stego_url.replace("/uploads/", "")
        stego_path = UPLOAD_FOLDER / filename
        if not stego_path.exists():
            return jsonify({"success": False, "error": "Imagen stego no encontrada"}), 404

        sim = RealisticPlatformSimulator()
        result = sim.simulate(platform, str(stego_path))
        return jsonify({
            "success": True, "platform": platform,
            "survived": result.get("survived", False),
            "psnr_after": result.get("psnr_after"),
            "size_after_kb": result.get("size_after_kb"),
            "modifications": result.get("modifications", []),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/publish", methods=["POST"])
def api_publish():
    try:
        data = request.get_json(force=True)
        stego_url = data.get("stego_url", "")
        platform = data.get("platform", "")
        credentials = data.get("credentials", {})
        if not stego_url or not platform:
            return jsonify({"success": False, "error": "Falta URL o plataforma"}), 400

        filename = stego_url.replace("/uploads/", "")
        image_path = UPLOAD_FOLDER / filename
        if not image_path.exists():
            return jsonify({"success": False, "error": "Imagen no encontrada"}), 404

        # Inyectar credenciales desde localStorage del navegador
        for key, value in credentials.items():
            if value:
                os.environ[key] = value

        adapter_cls = ADAPTER_MAP.get(platform)
        if not adapter_cls:
            return jsonify({"success": False, "error": f"Plataforma '{platform}' no soportada"}), 400

        adapter = adapter_cls()
        result = adapter.publish(image_path)
        return jsonify({
            "success": result.get("success", False),
            "url": result.get("url", ""),
            "platform": platform,
            "message": result.get("message", ""),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/publish_validate", methods=["POST"])
def api_publish_validate():
    try:
        data = request.get_json(force=True)
        stego_url = data.get("stego_url", "")
        platform = data.get("platform", "")
        credentials = data.get("credentials", {})
        if not stego_url or not platform:
            return jsonify({"success": False, "error": "Falta URL o plataforma"}), 400

        filename = stego_url.replace("/uploads/", "")
        image_path = UPLOAD_FOLDER / filename
        if not image_path.exists():
            return jsonify({"success": False, "error": "Imagen no encontrada"}), 404

        for key, value in credentials.items():
            if value:
                os.environ[key] = value

        adapter_cls = ADAPTER_MAP.get(platform)
        if not adapter_cls:
            return jsonify({"success": False, "error": f"Plataforma no soportada"}), 400

        adapter = adapter_cls()
        pub = adapter.publish(image_path)
        if not pub.get("success"):
            return jsonify({"success": False, "error": pub.get("error", "Error")}), 500

        url = pub.get("url", "")
        e2e = {"success": False, "url": url}
        if url and hasattr(adapter, "download"):
            try:
                downloaded = adapter.download(url)
                if downloaded:
                    e2e["downloaded_size"] = len(downloaded)
                    e2e["original_size"] = image_path.stat().st_size
                    e2e["hash_match"] = hashlib.sha256(image_path.read_bytes()).hexdigest() == hashlib.sha256(downloaded).hexdigest()
                    e2e["success"] = e2e["hash_match"]
            except Exception as e:
                e2e["error"] = str(e)

        return jsonify({"success": True, "url": url, "platform": platform, "e2e": e2e})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_file(UPLOAD_FOLDER / filename)

# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print(" Stegstr Control Center v2.2.0")
    print("=" * 60)
    print("\n⚠️  ADVERTENCIA DE SEGURIDAD:")
    print("   Este servidor está diseñado para ejecutarse ÚNICAMENTE en localhost.")
    print("   NO expongas este servidor directamente a Internet.")
    print("   El panel no tiene autenticación ni protección CSRF.")
    print("   Las credenciales se guardan en localStorage del navegador.")
    print("\n   Abre http://127.0.0.1:5000 en tu navegador.\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
