# Stegstr — Esteganografía LSB Avanzada

## Versión 2.2.0 — Parche de coherencia GUI ↔ Backend

### Correcciones aplicadas en esta versión

| Problema | Estado |
|---|---|
| Modos `STANDARD`/`AGGRESSIVE` inexistentes en GUI | ✅ Eliminados; añadidos `GHOST`/`PHANTOM` reales |
| Credenciales Instagram desfasadas (username/password vs Business API) | ✅ Unificadas a `INSTAGRAM_BUSINESS_ACCOUNT_ID` + `META_PAGE_ACCESS_TOKEN` |
| Credenciales WhatsApp inventadas | ✅ Unificadas a `WHATSAPP_BUSINESS_PHONE_ID` + `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_RECIPIENT_PHONE` |
| Twitter: `TWITTER_ACCESS_SECRET` → `TWITTER_ACCESS_TOKEN_SECRET` | ✅ Nombre corregido |
| Plataforma "Signal" sin adaptador | ✅ Eliminada de `web_app.py` |
| Capacidad hardcoded en `web_app.py` | ✅ Ahora consulta `POST /api/capacity` al motor real |
| Barra de capacidad: `tamaño_imagen / cap` | ✅ Corregida a `bytes_mensaje / capacidad_real` |
| Simulador desdoblado (`PlatformSimulator` vs `RealisticPlatformSimulator`) | ✅ Unificado a `RealisticPlatformSimulator` en ambas GUIs |
| CORS `origins="*"` | ✅ Restringido a `127.0.0.1:8080` y `localhost:8080` |
| README sin `widget_server.py` | ✅ Estructura actualizada |

### Estructura del proyecto

```
stegstr/
├── stego/
│   ├── engine.py           # Motor esteganográfico (5 modos: FORTRESS, ARMOR, GHOST, PHANTOM, HYBRID)
│   ├── analyzer.py         # Análisis de detectabilidad
│   ├── benchmark.py        # Benchmark de rendimiento
│   └── crypto.py           # Cifrado AES-256-GCM + Argon2id
├── platform/
│   ├── simulator.py        # RealisticPlatformSimulator (unificado)
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
