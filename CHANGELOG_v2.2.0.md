# CHANGELOG — Stegstr v2.2.0 Patch

## Fecha: 2026-08-21
## Tipo: Parche de coherencia GUI ↔ Backend (basado en código real del ZIP)

---

### 🔴 Crítico — Fallos funcionales corregidos

#### 1. Modos de estego inexistentes en widget.html
- **Antes:** `STANDARD`, `AGGRESSIVE` (no existen en StegoEngine)
- **Después:** `FORTRESS`, `ARMOR`, `GHOST`, `PHANTOM`, `HYBRID` (5 modos reales)
- **Archivos:** `widget.html`

#### 2. Credenciales Instagram desfasadas
- **Antes (widget):** `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD`
- **Después (ambos):** `INSTAGRAM_BUSINESS_ACCOUNT_ID` + `META_PAGE_ACCESS_TOKEN`
- **Archivos:** `widget.html`, `widget_server.py`, `web_app.py`

#### 3. Credenciales WhatsApp inventadas
- **Antes (widget):** `WHATSAPP_API_KEY` + `WHATSAPP_PHONE_NUMBER`
- **Antes (web_app):** `WHATSAPP_PHONE` + `WHATSAPP_PASSWORD`
- **Después (ambos):** `WHATSAPP_BUSINESS_PHONE_ID` + `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_RECIPIENT_PHONE`
- **Archivos:** `widget.html`, `widget_server.py`, `web_app.py`

#### 4. Twitter: nombre de variable incorrecto
- **Antes (web_app):** `TWITTER_ACCESS_SECRET`
- **Después:** `TWITTER_ACCESS_TOKEN_SECRET`
- **Archivos:** `web_app.py`

#### 5. Plataforma "Signal" fantasma
- **Antes:** Listada en web_app.py sin adaptador real
- **Después:** Eliminada
- **Archivos:** `web_app.py`

#### 6. API del motor incorrecta: `.hide()` no existe
- **Antes:** `engine.hide(cover, message, mode=mode)`
- **Después:** `engine.embed(cover_path, message, output_path, mode=mode, target_platform=platform)`
- **Archivos:** `widget_server.py`, `web_app.py`

#### 7. Bug `HYBRID` explícito → extracción falla
- **Antes:** Se pasaba `mode=StegoMode.HYBRID` al motor, que escribía cabecera HYBRID pero embebía como FORTRESS/ARMOR. Al extraer, `_extract_bits` no tenía rama HYBRID y usaba GHOST → fallo silencioso.
- **Después:** `_get_mode("HYBRID")` devuelve `None`, dejando que el motor auto-seleccione el modo real (FORTRESS/ARMOR/GHOST/PHANTOM).
- **Archivos:** `widget_server.py`, `web_app.py`

---

### 🟠 Alto — Inconsistencias de importación y arquitectura

#### 8. `StegoAnalyzer` no existe en el proyecto
- **Antes:** `from stegstr.stego.analyzer import StegoAnalyzer`
- **Después:** Eliminado. Análisis básico implementado con PIL/numpy (PSNR/MSE).
- **Archivos:** `widget_server.py`, `web_app.py`

#### 9. `StegoBenchmark` no existe en el proyecto
- **Antes:** `from stegstr.stego.benchmark import StegoBenchmark`
- **Después:** Eliminado. Benchmark básico implementado con timer de `time`.
- **Archivos:** `widget_server.py`

#### 10. `RealisticPlatformSimulator` en ruta incorrecta
- **Antes:** `from stegstr.platform.simulator import RealisticPlatformSimulator`
- **Después:** `from stegstr.platform.simulator_v2 import RealisticPlatformSimulator`
- **Archivos:** `widget_server.py`, `web_app.py`

#### 11. `send_file` no importado
- **Antes:** Usado en `/uploads/<file>` sin importar
- **Después:** `from flask import ..., send_file`
- **Archivos:** `web_app.py`

#### 12. Capacidad hardcoded
- **Antes:** `const capMap={FORTRESS:150,ARMOR:3000,GHOST:50000,PHANTOM:1000,HYBRID:500}`
- **Después:** Consulta `POST /api/capacity` al motor real (`StegoEngine.get_capacity()`)
- **Archivos:** `web_app.py`

#### 13. Barra de capacidad incorrecta
- **Antes:** `capBar = (file.size / 1024) / cap` → comparaba tamaño de imagen vs capacidad
- **Después:** `capBar = msgBytes / capacityReal` → compara bytes del mensaje vs capacidad real
- **Archivos:** `web_app.py`

#### 14. Simulador desdoblado
- **Antes:** `web_app.py` usaba `PlatformSimulator` (v1); `widget_server.py` usaba `RealisticPlatformSimulator` (v2)
- **Después:** Ambos usan `RealisticPlatformSimulator` desde `simulator_v2.py`
- **Archivos:** `web_app.py`, `widget_server.py`

#### 15. CORS abierto
- **Antes:** `origins="*"`
- **Después:** `origins=["http://127.0.0.1:8080", "http://localhost:8080"]`
- **Archivos:** `widget_server.py`

---

### 🟡 Medio — Documentación y dependencias

#### 16. README sin `widget_server.py`
- **Antes:** Estructura de directorios omitía `widget_server.py`
- **Después:** Estructura completa con los 3 archivos de GUI
- **Archivos:** `README_v2.2.0_PATCH.md`

#### 17. `requirements.txt` incompleto
- **Faltaban:** `argon2-cffi` (core, usado por engine), `rich` (usado por cli.py), `click` (usado por cli.py)
- **Archivos:** `requirements.txt`

---

### Instrucciones de aplicación del parche

```bash
# 1. Descomprime en la raíz del repositorio
unzip stegstr-v2.2.0-patch.zip

# 2. Aplica (hace backup automático)
bash stegstr-v2.2.0-patch/apply_patch_v2.2.0.sh

# 3. Verifica
python -c "from stegstr.gui.widget_server import app; print('widget_server OK')"
python -c "from stegstr.gui.web_app import app; print('web_app OK')"

# 4. Commit y tag
git add stegstr/gui/ requirements.txt
git commit -m "v2.2.0: parche coherencia GUI-backend + corrección credenciales + fixes de importación"
git tag v2.2.0
```

---

### Valoración post-parche (estimada)

| Área | Antes | Después |
|---|---|---|
| Motor esteganográfico | 8,5/10 | 8,5/10 |
| Criptografía | 8,5/10 | 8,5/10 |
| GUI arranca sin errores | 2/10 | 8/10 |
| Integración GUI ↔ backend | 3/10 | 7,5/10 |
| Consistencia de credenciales | 4/10 | 8/10 |
| Preparación para concurso | 4/10 | 7,5/10 |

**Nota:** Para alcanzar 8,5–9/10 se recomienda:
1. Realizar pruebas E2E reales con al menos 3 plataformas
2. Añadir tests que cubran `widget_server.py` y `web_app.py`
3. Implementar `StegoAnalyzer` real o añadir `scikit-image` para análisis avanzado
