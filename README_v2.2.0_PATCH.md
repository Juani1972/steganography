# Stegstr — Esteganografía LSB Avanzada

## Versión 2.2.0 — Parche de coherencia GUI ↔ Backend

### Correcciones aplicadas en esta versión

| # | Problema | Estado |
|---|----------|--------|
| 1 | Modos `STANDARD`/`AGGRESSIVE` inexistentes en GUI | ✅ Eliminados; añadidos `GHOST`/`PHANTOM` reales |
| 2 | Credenciales Instagram desfasadas (username/password vs Business API) | ✅ Unificadas a `INSTAGRAM_BUSINESS_ACCOUNT_ID` + `META_PAGE_ACCESS_TOKEN` |
| 3 | Credenciales WhatsApp inventadas | ✅ Unificadas a `WHATSAPP_BUSINESS_PHONE_ID` + `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_RECIPIENT_PHONE` |
| 4 | Twitter: `TWITTER_ACCESS_SECRET` → `TWITTER_ACCESS_TOKEN_SECRET` | ✅ Nombre corregido |
| 5 | Plataforma "Signal" sin adaptador | ✅ Eliminada de `web_app.py` |
| 6 | Capacidad hardcoded en `web_app.py` | ✅ Ahora consulta `POST /api/capacity` al motor real |
| 7 | Barra de capacidad: `tamaño_imagen / cap` | ✅ Corregida a `bytes_mensaje / capacidad_real` |
| 8 | Simulador desdoblado (`PlatformSimulator` vs `RealisticPlatformSimulator`) | ✅ Unificado a `RealisticPlatformSimulator` en ambas GUIs |
| 9 | CORS `origins="*"` | ✅ Restringido a `127.0.0.1:8080` / `localhost:8080` |
| 10 | README sin `widget_server.py` | ✅ Estructura actualizada |
| 11 | `.hide()` no existe en motor real | ✅ Corregido a `.embed()` |
| 12 | `StegoAnalyzer` no existe | ✅ Eliminado; análisis básico con PIL/numpy |
| 13 | `StegoBenchmark` no existe | ✅ Eliminado; benchmark básico con timer |
| 14 | `send_file` no importado en `web_app.py` | ✅ Importado de Flask |
| 15 | Bug `HYBRID` explícito → `None` silencioso | ✅ HYBRID se traduce a `None` (auto-select) |
| 16 | `RealisticPlatformSimulator` en `simulator_v2.py` | ✅ Import corregido |
| 17 | `requirements.txt` incompleto | ✅ Añadidos `argon2-cffi`, `rich`, `click` |

### Estructura del proyecto

```
stegstr/
├── stego/
│   ├── engine.py           # Motor esteganográfico (5 modos: FORTRESS, ARMOR, GHOST, PHANTOM, HYBRID)
│   ├── crypto.py           # Cifrado AES-256-GCM + Argon2id
│   └── ...
├── platform/
│   ├── simulator_v2.py     # RealisticPlatformSimulator (unificado)
│   └── adapters/
│       ├── telegram.py     # Telegram Bot API
│       ├── discord.py      # Discord Webhooks
│       ├── imgur.py        # Imgur API
│       ├── reddit.py       # Reddit API
│       ├── twitter.py      # Twitter/X API v2
│       ├── instagram.py    # Instagram Graph API (Business)
│       ├── whatsapp.py     # WhatsApp Business API
│       └── nostr.py        # Protocolo Nostr
├── gui/
│   ├── web_app.py          # Stegstr Control Center (wizard, puerto 5000)
│   ├── widget.html         # Stegstr Widget SPA (puerto 8080)
│   └── widget_server.py    # Backend Flask para widget.html (puerto 8080)
├── cli.py                  # Interfaz de línea de comandos
├── requirements.txt        # Dependencias completas
└── tests/                  # Tests unitarios y de integración
```

### Advertencia de seguridad

> **Local-only / Do not expose to public networks**
>
> Tanto `web_app.py` como `widget_server.py` están diseñados para ejecutarse
> únicamente en `127.0.0.1`. No exponer directamente a Internet.
> Las credenciales se almacenan en RAM (widget_server) o localStorage (web_app).

### Inicio rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Widget SPA (recomendado para concurso)
python stegstr/gui/widget_server.py
# Abrir http://127.0.0.1:8080

# Control Center (alternativa wizard)
python stegstr/gui/web_app.py
# Abrir http://127.0.0.1:5000
```

### Requisitos de credenciales por plataforma

| Plataforma | Variables requeridas | Tipo de cuenta |
|---|---|---|
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Bot |
| Discord | `DISCORD_WEBHOOK_URL` | Webhook |
| Imgur | `IMGUR_CLIENT_ID` | App OAuth |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` | App script |
| Twitter/X | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET` | Developer |
| Instagram | `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `META_PAGE_ACCESS_TOKEN` | Business/Creator |
| WhatsApp | `WHATSAPP_BUSINESS_PHONE_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_RECIPIENT_PHONE` | Business API |
| Nostr | `NOSTR_PRIVATE_KEY` | Cualquiera (clave nsec/hex) |

---

*Stegstr v2.2.0 — Parche de coherencia y corrección de fallos funcionales.*
