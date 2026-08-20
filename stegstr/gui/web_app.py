#!/usr/bin/env python3
"""
Stegstr Web App v2.2 — Panel local con wizard visual y endpoints reales.
Mantiene la funcionalidad anterior (credenciales .env, benchmark real)
y anade una SPA conectada al backend via API REST.

Ejecutar:
    python -m stegstr.gui.web_app
    # o
    flask --app stegstr.gui.web_app run

Advertencia: Guarda credenciales en .env en texto plano. Solo localhost.
"""
import os
import sys
import json
import tempfile
import base64
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string

try:
    from dotenv import load_dotenv, set_key
    _HAS_DOTENV = True
except ImportError:
    _HAS_DOTENV = False

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.simulator import PlatformSimulator
from stegstr.analysis.steganalysis import StegAnalyzer

try:
    from stegstr.platform.adapters import get_adapter_statuses
    _HAS_ADAPTERS = True
except ImportError:
    _HAS_ADAPTERS = False

app = Flask(__name__)
app.secret_key = os.urandom(24)

ENV_PATH = Path(".env")
COVER_PATH = Path("cover_sample.png")

PLATFORMS = [
    {"key": "instagram", "label": "Instagram", "env": ["INSTAGRAM_BUSINESS_ACCOUNT_ID", "META_PAGE_ACCESS_TOKEN"]},
    {"key": "twitter", "label": "Twitter / X", "env": ["TWITTER_BEARER_TOKEN", "TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"]},
    {"key": "telegram_photo", "label": "Telegram", "env": ["TELEGRAM_BOT_TOKEN"]},
    {"key": "whatsapp_standard", "label": "WhatsApp", "env": ["WHATSAPP_PHONE", "WHATSAPP_PASSWORD"]},
    {"key": "signal", "label": "Signal", "env": ["SIGNAL_USERNAME", "SIGNAL_PASSWORD"]},
    {"key": "reddit", "label": "Reddit", "env": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"]},
    {"key": "discord", "label": "Discord", "env": ["DISCORD_WEBHOOK_URL"]},
    {"key": "nostr", "label": "Nostr", "env": ["NOSTR_PRIVATE_KEY"]},
]


def _ensure_cover():
    if COVER_PATH.exists():
        return str(COVER_PATH)
    try:
        import numpy as np
        from PIL import Image
        arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        Image.fromarray(arr).save(COVER_PATH)
        return str(COVER_PATH)
    except Exception:
        return None


def _get_platform_statuses():
    statuses = []
    for p in PLATFORMS:
        configured = all(os.getenv(k, "") != "" for k in p["env"])
        available = False
        if _HAS_ADAPTERS:
            try:
                adapter_status = get_adapter_statuses()
                available = adapter_status.get(p["key"], {}).get("available", False)
            except Exception:
                pass
        statuses.append({
            "key": p["key"],
            "label": p["label"],
            "configured": configured,
            "available": available,
            "env": p["env"],
        })
    return statuses


SPA_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stegstr Control Center</title>
<style>
  :root { --font-sans: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; --font-mono: "SFMono-Regular",Consolas,monospace; --text-primary:#111; --text-secondary:#555; --text-tertiary:#888; --text-quaternary:#bbb; --border:#e5e5e5; --surface:#f5f5f5; --positive:#16a34a; --danger:#dc2626; --warning:#ca8a04; --chart-1:#2563eb; --radius:10px; --radius-sm:6px; --t-fast:150ms; }
  *{box-sizing:border-box}
  body{font-family:var(--font-sans);margin:0;padding:16px;color:var(--text-primary);background:#fafafa}
  .ssc-wrap{max-width:720px;margin:0 auto}
  .ssc-header{display:flex;align-items:center;gap:12px;margin-bottom:20px}
  .ssc-header h1{font-size:20px;font-weight:500;margin:0}
  .ssc-badge{font-size:12px;font-weight:500;padding:3px 10px;border-radius:999px;background:#dcfce7;color:var(--positive)}
  .ssc-card{border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px;background:#fff;transition:box-shadow var(--t-fast)}
  .ssc-card:hover{box-shadow:0 2px 8px rgba(0,0,0,0.04)}
  .ssc-section-title{font-size:14px;font-weight:500;color:var(--text-secondary);margin:0 0 12px 0}
  .ssc-grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .ssc-grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
  @media(max-width:560px){.ssc-grid-2,.ssc-grid-3{grid-template-columns:1fr}}
  .ssc-platform-chip{display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);cursor:pointer;transition:all var(--t-fast);font-size:14px;background:#fff}
  .ssc-platform-chip:hover{border-color:var(--text-tertiary);background:var(--surface)}
  .ssc-platform-chip.active{border-color:var(--text-primary);background:#f0f0f0}
  .ssc-platform-chip .dot{width:8px;height:8px;border-radius:50%;background:var(--text-quaternary)}
  .ssc-platform-chip.active .dot{background:var(--positive)}
  .ssc-platform-chip .cfg{font-size:11px;color:var(--text-tertiary);margin-left:auto}
  .ssc-input,.ssc-select,.ssc-textarea{width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius);font-size:14px;font-family:inherit;color:var(--text-primary);background:#fff;outline:none}
  .ssc-input:focus,.ssc-select:focus,.ssc-textarea:focus{border-color:var(--text-primary)}
  .ssc-textarea{min-height:90px;resize:vertical}
  .ssc-metric{text-align:center;padding:12px;border-radius:var(--radius);background:var(--surface)}
  .ssc-metric-value{font-size:28px;font-weight:500;line-height:1.1;font-variant-numeric:tabular-nums}
  .ssc-metric-label{font-size:12px;color:var(--text-tertiary);margin-top:4px}
  .ssc-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:10px 18px;border-radius:var(--radius);font-size:14px;font-weight:500;cursor:pointer;border:1px solid transparent;transition:all var(--t-fast);font-family:inherit}
  .ssc-btn-primary{background:var(--text-primary);color:#fff}
  .ssc-btn-primary:hover{opacity:.85}
  .ssc-btn-primary:disabled{opacity:.5;cursor:not-allowed}
  .ssc-btn-secondary{background:#fff;color:var(--text-primary);border-color:var(--border)}
  .ssc-btn-secondary:hover{background:var(--surface)}
  .ssc-btn-danger{background:#fef2f2;color:var(--danger);border-color:#fecaca}
  .ssc-stepbar{display:flex;gap:8px;margin-bottom:20px;overflow-x:auto}
  .ssc-step{flex:1;min-width:100px;padding:10px;text-align:center;border-radius:var(--radius);font-size:13px;font-weight:500;border:1px solid var(--border);color:var(--text-tertiary);cursor:pointer;white-space:nowrap;background:#fff}
  .ssc-step.active{border-color:var(--text-primary);color:var(--text-primary);background:var(--surface)}
  .ssc-step.done{border-color:var(--positive);color:var(--positive)}
  .ssc-panel{display:none}
  .ssc-panel.active{display:block;animation:fadeIn 200ms ease}
  @keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
  .ssc-result-box{padding:12px;border-radius:var(--radius);border:1px solid var(--border);background:#f0fdf4;font-size:13px;line-height:1.5}
  .ssc-result-box.warn{background:#fefce8;border-color:#fde047}
  .ssc-result-box.err{background:#fef2f2;border-color:#fecaca}
  .ssc-progress{height:6px;border-radius:999px;background:var(--border);overflow:hidden;margin-top:8px}
  .ssc-progress-fill{height:100%;border-radius:999px;background:var(--positive);width:0%;transition:width 600ms ease}
  .ssc-toggle{display:flex;align-items:center;gap:10px;font-size:14px;cursor:pointer}
  .ssc-toggle input{width:16px;height:16px;accent-color:var(--text-primary)}
  .ssc-tag{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:500;background:var(--surface);color:var(--text-secondary);border:1px solid var(--border)}
  .ssc-log{font-family:var(--font-mono);font-size:12px;line-height:1.6;color:var(--text-secondary);background:var(--surface);padding:12px;border-radius:var(--radius);max-height:200px;overflow-y:auto;white-space:pre-wrap;word-break:break-all}
  .ssc-cred-row{display:flex;gap:8px;align-items:center;margin-bottom:8px}
  .ssc-cred-row input{flex:1}
  .ssc-cred-row span{font-size:12px;color:var(--text-tertiary);min-width:140px}
  .dropzone{border:2px dashed var(--border);border-radius:var(--radius);padding:24px;text-align:center;color:var(--text-tertiary);cursor:pointer;transition:all var(--t-fast)}
  .dropzone:hover{border-color:var(--text-tertiary);background:var(--surface)}
  .dropzone.dragover{border-color:var(--positive);background:#f0fdf4}
</style>
</head>
<body>
<div class="ssc-wrap">
  <div class="ssc-header"><h1>Stegstr Control Center</h1><span class="ssc-badge">v2.2</span></div>
  <div class="ssc-stepbar">
    <div class="ssc-step active" onclick="goStep(0)">1. Plataforma</div>
    <div class="ssc-step" onclick="goStep(1)">2. Mensaje</div>
    <div class="ssc-step" onclick="goStep(2)">3. Ocultar</div>
    <div class="ssc-step" onclick="goStep(3)">4. Simular</div>
    <div class="ssc-step" onclick="goStep(4)">5. Publicar</div>
  </div>

  <div class="ssc-panel active" id="panel-0">
    <div class="ssc-card">
      <p class="ssc-section-title">Selecciona la red social de destino</p>
      <div class="ssc-grid-3" id="platformGrid"></div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;" id="platformMeta"></div>
    </div>
    <div class="ssc-card">
      <p class="ssc-section-title">Configurar credenciales</p>
      <div id="credForm"></div>
      <div style="margin-top:10px;">
        <button class="ssc-btn ssc-btn-secondary" onclick="saveCreds()">Guardar credenciales</button>
        <span id="credStatus" style="font-size:12px;margin-left:8px;color:var(--text-tertiary);"></span>
      </div>
    </div>
    <div class="ssc-card">
      <p class="ssc-section-title">Parametros recomendados</p>
      <div class="ssc-grid-3">
        <div class="ssc-metric"><div class="ssc-metric-value" id="recMode">-</div><div class="ssc-metric-label">Modo</div></div>
        <div class="ssc-metric"><div class="ssc-metric-value" id="recDelta">-</div><div class="ssc-metric-label">Delta</div></div>
        <div class="ssc-metric"><div class="ssc-metric-value" id="recEcc">-</div><div class="ssc-metric-label">ECC</div></div>
      </div>
      <div style="margin-top:12px;"><label class="ssc-toggle"><input type="checkbox" id="autoTuneCheck" checked><span>Usar auto-tune (optimizar delta + ECC)</span></label></div>
    </div>
    <div style="text-align:right"><button class="ssc-btn ssc-btn-primary" onclick="nextStep()">Continuar →</button></div>
  </div>

  <div class="ssc-panel" id="panel-1">
    <div class="ssc-card">
      <p class="ssc-section-title">Imagen de portada (cover)</p>
      <div class="dropzone" id="dropzone" onclick="document.getElementById('fileInput').click()">
        <div id="dropText">Arrastra una imagen o haz clic para elegir</div>
        <input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFile(this.files[0])">
      </div>
      <div id="coverInfo" style="margin-top:8px;font-size:13px;color:var(--text-tertiary);"></div>
      <div style="margin-top:10px;height:6px;background:var(--border);border-radius:999px;overflow:hidden;"><div id="capBar" style="width:0%;height:100%;background:var(--chart-1);border-radius:999px;transition:width 300ms"></div></div>
      <div style="font-size:12px;color:var(--text-tertiary);margin-top:6px;">Capacidad estimada: <strong id="capValue">-</strong></div>
    </div>
    <div class="ssc-card">
      <p class="ssc-section-title">Mensaje secreto</p>
      <textarea class="ssc-textarea" id="msgInput" placeholder="Escribe aqui el mensaje a ocultar..." oninput="updateMsgStats()"></textarea>
      <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:var(--text-tertiary);">
        <span id="msgBytes">0 bytes</span><span id="msgStatus" style="color:var(--positive);">Dentro del limite</span>
      </div>
    </div>
    <div class="ssc-card">
      <p class="ssc-section-title">Cifrado (opcional)</p>
      <input class="ssc-input" type="password" id="passwordInput" placeholder="Contrasena para AES-256-GCM + Argon2id">
      <div style="margin-top:8px;font-size:12px;color:var(--text-tertiary);">Si dejas vacio, el mensaje se oculta sin cifrar (no recomendado).</div>
    </div>
    <div style="display:flex;justify-content:space-between;">
      <button class="ssc-btn ssc-btn-secondary" onclick="prevStep()">← Atras</button>
      <button class="ssc-btn ssc-btn-primary" onclick="nextStep()">Ocultar mensaje →</button>
    </div>
  </div>

  <div class="ssc-panel" id="panel-2">
    <div class="ssc-card">
      <p class="ssc-section-title">Proceso de ocultacion</p>
      <div class="ssc-log" id="embedLog">Esperando...</div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;" id="embedTags"></div>
    </div>
    <div class="ssc-card">
      <p class="ssc-section-title">Metricas de calidad</p>
      <div class="ssc-grid-3">
        <div class="ssc-metric"><div class="ssc-metric-value" id="resPsnr">-</div><div class="ssc-metric-label">PSNR (dB)</div></div>
        <div class="ssc-metric"><div class="ssc-metric-value" id="resSsim">-</div><div class="ssc-metric-label">SSIM</div></div>
        <div class="ssc-metric"><div class="ssc-metric-value" id="resTime">-</div><div class="ssc-metric-label">Tiempo</div></div>
      </div>
    </div>
    <div class="ssc-card">
      <p class="ssc-section-title">Imagen resultante</p>
      <div id="stegoPreview" style="text-align:center;padding:20px;color:var(--text-tertiary);">La imagen stego aparecera aqui</div>
      <div style="margin-top:10px;text-align:center;">
        <a id="dlLink" class="ssc-btn ssc-btn-secondary" style="display:none" download="stego.png">Descargar stego.png</a>
      </div>
    </div>
    <div style="display:flex;justify-content:space-between;">
      <button class="ssc-btn ssc-btn-secondary" onclick="prevStep()">← Atras</button>
      <button class="ssc-btn ssc-btn-primary" onclick="nextStep()">Simular envio →</button>
    </div>
  </div>

  <div class="ssc-panel" id="panel-3">
    <div class="ssc-card">
      <p class="ssc-section-title">Simulacion de procesado por la red social</p>
      <div class="ssc-log" id="simLog">Esperando...</div>
      <div class="ssc-result-box" id="simResult" style="display:none"></div>
    </div>
    <div class="ssc-card">
      <p class="ssc-section-title">Analisis de detectabilidad</p>
      <div class="ssc-grid-3">
        <div class="ssc-metric"><div class="ssc-metric-value" id="resChi2">-</div><div class="ssc-metric-label">Chi² p-value</div></div>
        <div class="ssc-metric"><div class="ssc-metric-value" id="resRs">-</div><div class="ssc-metric-label">RS rate</div></div>
        <div class="ssc-metric"><div class="ssc-metric-value" id="resRisk">-</div><div class="ssc-metric-label">Riesgo deteccion</div></div>
      </div>
    </div>
    <div style="display:flex;justify-content:space-between;">
      <button class="ssc-btn ssc-btn-secondary" onclick="prevStep()">← Atras</button>
      <button class="ssc-btn ssc-btn-primary" onclick="nextStep()">Publicar / Exportar →</button>
    </div>
  </div>

  <div class="ssc-panel" id="panel-4">
    <div class="ssc-card">
      <p class="ssc-section-title">Publicar en red social</p>
      <div class="ssc-grid-2" id="publishGrid"></div>
    </div>
    <div class="ssc-card">
      <p class="ssc-section-title">Benchmark rapido</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
        <button class="ssc-btn ssc-btn-secondary" onclick="runBench('quick')">Quick</button>
        <button class="ssc-btn ssc-btn-secondary" onclick="runBench('full')">Full</button>
      </div>
      <div class="ssc-progress"><div class="ssc-progress-fill" id="benchBar"></div></div>
      <div id="benchResult" style="margin-top:8px;font-size:13px;color:var(--text-secondary);"></div>
    </div>
    <div style="display:flex;justify-content:space-between;">
      <button class="ssc-btn ssc-btn-secondary" onclick="prevStep()">← Atras</button>
      <button class="ssc-btn ssc-btn-danger" onclick="resetAll()">Reiniciar</button>
    </div>
  </div>
</div>

<script>
let currentStep=0, selectedPlatform='instagram', coverFile=null, stegoBlob=null, stegoMeta=null;
const platforms={
  instagram:{mode:'FORTRESS',delta:'8.0',ecc:'96 B',cap:'~150 B',resize:true,qf:75},
  whatsapp_standard:{mode:'FORTRESS',delta:'8.0',ecc:'96 B',cap:'~150 B',resize:true,qf:55},
  telegram_photo:{mode:'ARMOR',delta:'4.0',ecc:'40 B',cap:'~3 KB',resize:false,qf:82},
  twitter:{mode:'ARMOR',delta:'4.0',ecc:'32 B',cap:'~4 KB',resize:false,qf:85},
  signal:{mode:'GHOST',delta:'0.0',ecc:'16 B',cap:'~50 KB',resize:false,qf:95},
  nostr:{mode:'ARMOR',delta:'4.0',ecc:'48 B',cap:'~5 KB',resize:false,qf:90}
};

async function api(path, opts={}){
  const r=await fetch('/api'+path, {headers:{'Content-Type':'application/json'}, ...opts});
  if(!r.ok){ const t=await r.text(); throw new Error(t||r.statusText); }
  return r.json();
}

function goStep(n){
  document.querySelectorAll('.ssc-panel').forEach((p,i)=>p.classList.toggle('active',i===n));
  document.querySelectorAll('.ssc-step').forEach((s,i)=>{s.classList.remove('active','done');if(i===n)s.classList.add('active');if(i<n)s.classList.add('done')});
  currentStep=n;
}
function nextStep(){ if(currentStep===1 && !coverFile){ alert('Selecciona una imagen cover primero'); return; } if(currentStep===1){ doEmbed(); } if(currentStep===2){ doSimulate(); } if(currentStep===3){ loadPublish(); } if(currentStep<4) goStep(currentStep+1); }
function prevStep(){ if(currentStep>0) goStep(currentStep-1); }

async function loadPlatforms(){
  const data=await api('/platforms');
  const grid=document.getElementById('platformGrid');
  grid.innerHTML=data.platforms.map(p=>{
    const cfg=p.configured?'✓':'✗'; const dot=p.configured?'background:var(--positive)':'';
    return `<div class="ssc-platform-chip ${p.key===selectedPlatform?'active':''}" data-platform="${p.key}" onclick="selectPlatform(this)"><span class="dot" style="${dot}"></span> ${p.label} <span class="cfg">${cfg}</span></div>`;
  }).join('');
  selectPlatform(document.querySelector(`[data-platform="${selectedPlatform}"]`));
}
function selectPlatform(el){
  document.querySelectorAll('.ssc-platform-chip').forEach(c=>c.classList.remove('active')); el.classList.add('active');
  selectedPlatform=el.dataset.platform; const p=platforms[selectedPlatform];
  document.getElementById('recMode').textContent=p.mode;
  document.getElementById('recDelta').textContent=p.delta;
  document.getElementById('recEcc').textContent=p.ecc;
  document.getElementById('platformMeta').innerHTML=`<span class="ssc-tag">Resize: ${p.resize?'Si':'No'}</span><span class="ssc-tag">JPEG Q=${p.qf}</span><span class="ssc-tag">${p.mode}</span>`;
  loadCreds(selectedPlatform);
}

async function loadCreds(key){
  const data=await api('/platforms');
  const plat=data.platforms.find(x=>x.key===key);
  const form=document.getElementById('credForm');
  if(!plat||!plat.env.length){ form.innerHTML='<span style="color:var(--text-tertiary)">No se requieren credenciales para esta plataforma.</span>'; return; }
  form.innerHTML=plat.env.map(k=>`<div class="ssc-cred-row"><span>${k}</span><input class="ssc-input" type="text" id="cred_${k}" value="${plat.values[k]||''}" placeholder="Valor..."></div>`).join('');
}
async function saveCreds(){
  const inputs=document.querySelectorAll('#credForm input');
  const body={}; inputs.forEach(i=>{ body[i.id.replace('cred_','')]=i.value; });
  await api('/credentials',{method:'POST',body:JSON.stringify(body)});
  document.getElementById('credStatus').textContent='Guardado';
  setTimeout(()=>document.getElementById('credStatus').textContent='',2000);
  loadPlatforms();
}

function handleFile(file){
  if(!file) return; coverFile=file;
  document.getElementById('dropText').textContent=file.name+' ('+(file.size/1024).toFixed(1)+' KB)';
  document.getElementById('coverInfo').textContent='Listo para procesar';
  const p=platforms[selectedPlatform];
  const capMap={FORTRESS:150,ARMOR:3000,GHOST:50000,PHANTOM:1000,HYBRID:500};
  const cap=capMap[p.mode]||500;
  document.getElementById('capValue').textContent='~'+cap+' B';
  document.getElementById('capBar').style.width=Math.min(100,(file.size/1024)/cap*100)+'%';
}
['dragenter','dragover','dragleave','drop'].forEach(e=>{ window.addEventListener(e, ev=>ev.preventDefault()); });
const dz=document.getElementById('dropzone');
dz.addEventListener('dragenter',()=>dz.classList.add('dragover'));
dz.addEventListener('dragleave',()=>dz.classList.remove('dragover'));
dz.addEventListener('drop',e=>{dz.classList.remove('dragover');handleFile(e.dataTransfer.files[0]);});

function updateMsgStats(){
  const bytes=new Blob([document.getElementById('msgInput').value]).size;
  document.getElementById('msgBytes').textContent=bytes+' bytes';
  const cap=parseInt(document.getElementById('capValue').textContent.replace(/\D/g,''))||150;
  const status=document.getElementById('msgStatus');
  if(bytes>cap){status.textContent='Excede capacidad';status.style.color='var(--danger)';}
  else if(bytes>cap*0.8){status.textContent='Cerca del limite';status.style.color='var(--warning)';}
  else{status.textContent='Dentro del limite';status.style.color='var(--positive)';}
}

async function doEmbed(){
  const log=document.getElementById('embedLog');
  const btn=document.querySelector('#panel-2 .ssc-btn-primary');
  log.textContent='Procesando...'; btn.disabled=true;
  try{
    const fd=new FormData();
    fd.append('cover',coverFile);
    fd.append('message',document.getElementById('msgInput').value);
    fd.append('platform',selectedPlatform);
    const pw=document.getElementById('passwordInput').value;
    if(pw) fd.append('password',pw);
    if(document.getElementById('autoTuneCheck').checked) fd.append('auto_tune','1');
    const r=await fetch('/api/embed',{method:'POST',body:fd});
    if(!r.ok) throw new Error(await r.text());
    const data=await r.json();
    stegoMeta=data;
    log.textContent=`Modo: ${data.mode} | Delta: ${data.delta_used} | ECC: ${data.ecc_bytes}\nPSNR: ${data.psnr?.toFixed(2)||'-'} dB | SSIM: ${data.ssim?.toFixed(4)||'-'} | Tiempo: ${data.elapsed_ms} ms`;
    document.getElementById('embedTags').innerHTML=`<span class="ssc-tag">${data.format||'PNG'}</span><span class="ssc-tag">${data.mode}</span><span class="ssc-tag">d=${data.delta_used}</span><span class="ssc-tag">ECC=${data.ecc_bytes}</span>`;
    document.getElementById('resPsnr').textContent=data.psnr?.toFixed(1)||'-'; document.getElementById('resPsnr').style.color=data.psnr>35?'var(--positive)':'var(--warning)';
    document.getElementById('resSsim').textContent=data.ssim?.toFixed(3)||'-'; document.getElementById('resSsim').style.color=data.ssim>0.95?'var(--positive)':'var(--warning)';
    document.getElementById('resTime').textContent=(data.elapsed_ms||0)+' ms';
    const imgB64=data.stego_b64;
    if(imgB64){
      stegoBlob=Uint8Array.from(atob(imgB64),c=>c.charCodeAt(0));
      const blob=new Blob([stegoBlob],{type:'image/png'});
      const url=URL.createObjectURL(blob);
      document.getElementById('stegoPreview').innerHTML=`<img src="${url}" style="max-width:100%;max-height:300px;border-radius:8px">`;
      const a=document.getElementById('dlLink'); a.href=url; a.style.display='inline-flex';
    }
  }catch(e){
    log.textContent='Error: '+e.message; log.style.color='var(--danger)';
  }finally{ btn.disabled=false; }
}

async function doSimulate(){
  const log=document.getElementById('simLog');
  const box=document.getElementById('simResult');
  log.textContent='Simulando...'; box.style.display='none';
  try{
    if(!stegoMeta) throw new Error('No hay imagen stego. Vuelve al paso anterior.');
    const fd=new FormData();
    const blob=new Blob([stegoBlob],{type:'image/png'});
    fd.append('stego',blob,'stego.png');
    fd.append('platform',selectedPlatform);
    const pw=document.getElementById('passwordInput').value;
    if(pw) fd.append('password',pw);
    const r=await fetch('/api/simulate',{method:'POST',body:fd});
    if(!r.ok) throw new Error(await r.text());
    const data=await r.json();
    log.textContent=`[simulator] ${data.simulation_steps?.join('\n[simulator] ')||'OK'}\n[result] ${data.recovered?'Mensaje recuperado':'Fallo'}`;
    box.style.display='block';
    box.className='ssc-result-box '+(data.recovered?'':'err');
    box.innerHTML=`<strong>Resultado:</strong> ${data.recovered?'El mensaje sobrevive al procesado.':'El mensaje NO sobrevive.'}<br>BER: ${data.ber||0} | PSNR post: ${data.psnr_post?.toFixed(1)||'-'} dB`;
    document.getElementById('resChi2').textContent=data.analysis?.chi2_pvalue?.toFixed(2)||'-'; document.getElementById('resChi2').style.color=(data.analysis?.chi2_pvalue>0.05)?'var(--positive)':'var(--warning)';
    document.getElementById('resRs').textContent=data.analysis?.rs_rate?.toFixed(2)||'-'; document.getElementById('resRs').style.color=(data.analysis?.rs_rate<0.1)?'var(--positive)':'var(--warning)';
    document.getElementById('resRisk').textContent=data.analysis?.risk||'Bajo'; document.getElementById('resRisk').style.color='var(--positive)';
  }catch(e){
    log.textContent='Error: '+e.message; log.style.color='var(--danger)';
  }
}

async function loadPublish(){
  const data=await api('/platforms');
  const grid=document.getElementById('publishGrid');
  grid.innerHTML=data.platforms.map(p=>{
    const ok=p.configured&&p.available;
    return `<button class="ssc-btn ssc-btn-secondary" style="justify-content:flex-start;${ok?'':'opacity:.5'}" onclick="publish('${p.key}')" ${ok?'':'disabled'}><span>${p.label}</span> ${ok?'listo':'falta'}</button>`;
  }).join('');
}
async function publish(platform){
  if(!stegoBlob){ alert('No hay imagen stego'); return; }
  const fd=new FormData();
  const blob=new Blob([stegoBlob],{type:'image/png'});
  fd.append('stego',blob,'stego.png');
  fd.append('platform',platform);
  const r=await fetch('/api/publish',{method:'POST',body:fd});
  const t=await r.text();
  alert(r.ok?'Publicado: '+t:'Error: '+t);
}

async function runBench(type){
  const bar=document.getElementById('benchBar'),res=document.getElementById('benchResult');
  bar.style.width='0%'; res.textContent='Ejecutando...';
  try{
    const data=await api('/bench?type='+type);
    bar.style.width='100%';
    res.innerHTML=`<span style="color:var(--positive)">${data.label} OK</span> — ${data.summary}`;
  }catch(e){ bar.style.width='0%'; res.textContent='Error: '+e.message; }
}

function resetAll(){
  coverFile=null; stegoBlob=null; stegoMeta=null;
  document.getElementById('msgInput').value='';
  document.getElementById('passwordInput').value='';
  document.getElementById('dropText').textContent='Arrastra una imagen o haz clic para elegir';
  document.getElementById('coverInfo').textContent='';
  document.getElementById('capBar').style.width='0%';
  document.getElementById('capValue').textContent='-';
  document.getElementById('embedLog').textContent='Esperando...';
  document.getElementById('embedTags').innerHTML='';
  document.getElementById('stegoPreview').innerHTML='La imagen stego aparecera aqui';
  document.getElementById('dlLink').style.display='none';
  document.getElementById('simLog').textContent='Esperando...';
  document.getElementById('simResult').style.display='none';
  document.getElementById('benchBar').style.width='0%';
  document.getElementById('benchResult').textContent='';
  updateMsgStats(); goStep(0);
}

loadPlatforms();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(SPA_HTML)


@app.route("/api/platforms")
def api_platforms():
    statuses = _get_platform_statuses()
    for s in statuses:
        s["values"] = {k: os.getenv(k, "") for k in s["env"]}
    return jsonify({"platforms": statuses})


@app.route("/api/credentials", methods=["POST"])
def api_credentials():
    if not _HAS_DOTENV:
        return "python-dotenv no instalado", 500
    data = request.get_json(force=True, silent=True) or {}
    for key, value in data.items():
        if key.startswith(("..", "/")) or ".." in key:
            return jsonify({"error": "invalid key"}), 400
        set_key(str(ENV_PATH), key, str(value))
        os.environ[key] = str(value)
    return jsonify({"saved": True})


@app.route("/api/embed", methods=["POST"])
def api_embed():
    import time
    t0 = time.perf_counter()
    cover = request.files.get("cover")
    message = request.form.get("message", "")
    platform = request.form.get("platform")
    password = request.form.get("password") or None
    auto_tune = request.form.get("auto_tune") == "1"

    if not cover or not message:
        return jsonify({"error": "cover and message required"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        cover_path = os.path.join(tmpdir, "cover.png")
        cover.save(cover_path)
        stego_path = os.path.join(tmpdir, "stego.png")

        engine = StegoEngine(password=password)
        try:
            if auto_tune:
                tune = engine.auto_tune(cover_path, message, platform or "instagram", search_depth="standard")
                meta = engine.embed(cover_path, message, stego_path,
                                    target_platform=platform,
                                    mode_override=StegoMode[tune["best_mode"]],
                                    delta_override=tune["best_delta"],
                                    ecc_override=tune["best_ecc"])
                meta["auto_tune"] = tune
            else:
                meta = engine.embed(cover_path, message, stego_path, target_platform=platform)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        with open(stego_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")

        try:
            analyzer = StegAnalyzer()
            analysis = analyzer.compare(cover_path, stego_path)
        except Exception:
            analysis = {}

        elapsed = int((time.perf_counter() - t0) * 1000)
        return jsonify({
            **meta,
            "stego_b64": b64,
            "analysis": analysis,
            "elapsed_ms": elapsed,
        })


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    stego = request.files.get("stego")
    platform = request.form.get("platform", "instagram")
    password = request.form.get("password") or None

    if not stego:
        return jsonify({"error": "stego required"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        stego_path = os.path.join(tmpdir, "stego.png")
        proc_path = os.path.join(tmpdir, "proc.jpg")
        stego.save(stego_path)

        sim = PlatformSimulator()
        steps = []
        try:
            sim.simulate(platform, stego_path, proc_path)
            steps.append(f"Simulacion {platform} completada")
        except Exception as e:
            steps.append(f"Simulacion fallo: {e}")

        engine = StegoEngine(password=password)
        result = engine.extract(proc_path)

        try:
            analyzer = StegAnalyzer()
            analysis = analyzer.analyze(proc_path)
        except Exception:
            analysis = {}

        return jsonify({
            "recovered": result is not None and result.get("message") is not None,
            "message": result.get("message") if result else None,
            "simulation_steps": steps,
            "analysis": analysis,
        })


@app.route("/api/publish", methods=["POST"])
def api_publish():
    stego = request.files.get("stego")
    platform = request.form.get("platform")
    if not stego or not platform:
        return jsonify({"error": "stego and platform required"}), 400

    if not _HAS_ADAPTERS:
        return "Adaptadores no instalados (pip install stegstr[social])", 503

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "stego.png")
        stego.save(path)
        try:
            from stegstr.platform.adapters import get_adapter
            adapter = get_adapter(platform)
            if not adapter or not adapter.is_available():
                return f"Adapter {platform} no disponible", 503
            url = adapter.upload(path)
            return jsonify({"url": url})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/bench")
def api_bench():
    bench_type = request.args.get("type", "quick")
    cover = _ensure_cover()
    if not cover:
        return jsonify({"error": "no cover available"}), 500

    import time
    engine = StegoEngine()
    sim = PlatformSimulator()
    msg = "Benchmark test message " * 5
    platforms_test = ["instagram", "telegram_photo", "twitter"]
    results = []

    for p in platforms_test:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                stego = os.path.join(tmpdir, "st.png")
                proc = os.path.join(tmpdir, "pr.jpg")
                t0 = time.perf_counter()
                engine.embed(cover, msg, stego, target_platform=p)
                sim.simulate(p, stego, proc)
                result = engine.extract(proc)
                elapsed = time.perf_counter() - t0
                ok = result is not None and result.get("message") == msg
                results.append({"platform": p, "ok": ok, "elapsed": round(elapsed, 2)})
        except Exception as e:
            results.append({"platform": p, "ok": False, "error": str(e)})

    passed = sum(1 for r in results if r["ok"])
    return jsonify({
        "label": "Quick" if bench_type == "quick" else "Full",
        "summary": f"{passed}/{len(results)} plataformas OK | " + ", ".join(f"{r['platform']}: {'OK' if r['ok'] else 'FAIL'}" for r in results),
        "details": results,
    })


if __name__ == "__main__":
    if _HAS_DOTENV and ENV_PATH.exists():
        load_dotenv(str(ENV_PATH))
    _ensure_cover()
    print("Stegstr Web App v2.2 — http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
