# CHANGELOG — Stegstr v2.2.0 Patch

## Fecha: 2026-08-21
## Tipo: Parche de coherencia GUI ↔ Backend

---

### 🔴 Crítico — Fallos funcionales corregidos

#### 1. Modos de estego inexistentes en widget.html
- **Antes:** `STANDARD`, `AGGRESSIVE` (no existen en StegoEngine)
- **Después:** `FORTRESS`, `ARMOR`, `GHOST`, `PHANTOM`, `HYBRID` (5 modos reales)
- **Archivos:** `widget.html` (todos los <select> de modo)

#### 2. Credenciales Instagram desfasadas
- **Antes (widget):** `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD`
- **Antes (web_app):** `INSTAGRAM_BUSINESS_ACCOUNT_ID` + `META_PAGE_ACCESS_TOKEN` ✅
- **Después (ambos):** `INSTAGRAM_BUSINESS_ACCOUNT_ID` + `META_PAGE_ACCESS_TOKEN`
- **Archivos:** `widget.html`, `widget_server.py`, `web_app.py`

#### 3. Credenciales WhatsApp inventadas
- **Antes (widget):** `WHATSAPP_API_KEY` + `WHATSAPP_PHONE_NUMBER`
- **Antes (web_app):** `WHATSAPP_PHONE` + `WHATSAPP_PASSWORD` ❌
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

---

### 🟠 Alto — Inconsistencias serias corregidas

#### 6. Capacidad hardcoded
- **Antes:** `const capMap={FORTRESS:150,ARMOR:3000,GHOST:50000,PHANTOM:1000,HYBRID:500}`
- **Después:** Consulta `POST /api/capacity` al motor real (`StegoEngine.get_capacity()`)
- **Archivos:** `web_app.py` (nuevo endpoint `/api/capacity` + JS)

#### 7. Barra de capacidad incorrecta
- **Antes:** `capBar = (file.size / 1024) / cap` → comparaba tamaño de imagen vs capacidad
- **Después:** `capBar = msgBytes / capacityReal` → compara bytes del mensaje vs capacidad real
- **Archivos:** `web_app.py`

#### 8. Simulador desdoblado
- **Antes:** `web_app.py` usaba `PlatformSimulator` (v1); `widget_server.py` usaba `RealisticPlatformSimulator` (v2)
- **Después:** Ambos usan `RealisticPlatformSimulator`
- **Archivos:** `web_app.py`, `widget_server.py`

#### 9. CORS abierto
- **Antes:** `origins="*"`
- **Después:** `origins=["http://127.0.0.1:8080", "http://localhost:8080"]`
- **Archivos:** `widget_server.py`

---

### 🟡 Medio — Documentación y estructura

#### 10. README sin widget_server.py
- **Antes:** Estructura de directorios omitía `widget_server.py`
- **Después:** Estructura completa con los 3 archivos de GUI
- **Archivos:** `README_v2.2.0_PATCH.md`

---

### Instrucciones de aplicación del parche

1. Reemplazar `stegstr/gui/widget.html` → nuevo `widget.html`
2. Reemplazar `stegstr/gui/widget_server.py` → nuevo `widget_server.py`
3. Reemplazar `stegstr/gui/web_app.py` → nuevo `web_app.py`
4. Fusionar `README_v2.2.0_PATCH.md` con `README.md` principal
5. Commit: `git commit -m "v2.2.0: parche de coherencia GUI-backend + corrección credenciales"`
6. Tag: `git tag v2.2.0`

---

### Valoración post-parche (estimada)

| Área | Antes | Después |
|---|---|---|
| Motor esteganográfico | 8,5/10 | 8,5/10 |
| Criptografía | 8,5/10 | 8,5/10 |
| GUI visual | 6/10 | 7,5/10 |
| Integración GUI ↔ backend | 5/10 | 7,5/10 |
| Consistencia de credenciales | 4/10 | 8/10 |
| Preparación para concurso | 6,5/10 | 8/10 |

**Nota:** Para alcanzar 8,5–9/10 se recomienda realizar pruebas E2E reales
con al menos 3 plataformas (Telegram, Discord, Imgur/Reddit) y documentar los resultados.
