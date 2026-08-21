# Stegstr v2.2.0 — Steganografía Robusta para Redes Sociales

**Versión:** 2.2.0 · **Estado:** Beta técnica avanzada · **Licencia:** MIT

> Motor esteganográfico funcional y validado (5 modos, cifrado AES-256-GCM + Argon2id, ECC Reed-Solomon).
> Algunos módulos están marcados como experimental — ver [Estado de los módulos](#estado-de-los-módulos-por-área).

Stegstr es un cliente de esteganografía en Python orientado a la supervivencia de mensajes ocultos frente a la recompresión y el reprocesamiento que aplican las redes sociales y apps de mensajería. Combina:

- 5 modos de esteganografía optimizados para distintos escenarios de robustez/capacidad.
- Cifrado autenticado **AES-256-GCM** con derivación de clave **Argon2id**.
- Corrección de errores (ECC) mediante **Reed-Solomon**.
- Marcadores de sincronización DCT para resistir recompresión JPEG.
- Motor heurístico de **auto-tune** que optimiza parámetros automáticamente.
- Simuladores del procesamiento de imágenes de WhatsApp, Instagram, Telegram, Twitter/X, Facebook, Signal, LinkedIn y Reddit.
- Un cliente **Nostr** completo (NIP-01/05/94/96/98).
- Una API de *tool-calling* para agentes de IA (LLM), un gestor de sincronización de mensajes y una API REST opcional.
- CLI con salida en texto enriquecido (Rich) y JSON, y un panel web local para gestionar credenciales.
- Suite de benchmarking científico (BER, PSNR, SSIM) y validación de esteganálisis (Chi², RS, SPA).

---

## Tabla de contenidos

1. [Características principales](#características-principales)
2. [Estado de los módulos](#estado-de-los-módulos-por-área)
3. [Instalación](#instalación)
4. [Configuración de credenciales](#configuración-de-credenciales)
5. [Uso rápido](#uso-rápido)
6. [Cifrado](#cifrado)
7. [Interoperabilidad con agentes de IA](#interoperabilidad-con-agentes-de-ia)
8. [Estructura del proyecto](#estructura-del-proyecto)
9. [Tests](#tests)
10. [Plataformas soportadas (simulación)](#plataformas-simulación)
11. [Validación en plataformas reales](#validación-en-plataformas-reales)
12. [Resistencia al steganálisis](#resistencia-al-steganálisis)
13. [Seguridad](#seguridad)
14. [Solución de problemas](#solución-de-problemas)
15. [Contribuir](#contribuir)
16. [Licencia](#licencia)

---

## Características principales

- **5 modos de operación:**
  - `FORTRESS` — máxima robustez, ideal para plataformas muy agresivas comprimiendo imágenes.
  - `ARMOR` — equilibrio entre robustez y capacidad de mensaje.
  - `GHOST` — máxima capacidad en PNG (sin pérdida).
  - `PHANTOM` — LSB Matching, diseñado para resistir la detección estadística (anti-steganálisis).
  - `HYBRID` — selección automática del modo más adecuado según el contexto.
- **Cifrado:** AES-256-GCM (autenticado) + derivación de clave Argon2id (`time=3`, `memory=64MB`, `parallelism=4`).
- **Auto-tune profundo:** búsqueda gruesa → búsqueda fina → validación → score multi-objetivo (considerando ECC, delta y modo reales).
- **Seguridad de entrada:** límites de tamaño de payload (10MB comprimido / 50MB en crudo), validación estricta de cabecera, protección contra zip-bombs y límites de iteración en la extracción.
- **Nostr completo:** NIP-01/05/94/96/98, con verificación de identidad, cola de suscripciones, deduplicación de eventos entre relays y sincronización histórica.
- **Interoperabilidad con agentes de IA:** API de acciones (`analyze_carrier`, `estimate_capacity`, `recommend_parameters`, `encode`, `decode`, `simulate_platform`, `auto_optimize`, `benchmark_detectability`) pensada para integrarse con LLMs, más una API REST opcional.
- **Validación exhaustiva:** script `validate.py` con 32 tests de integridad, sin depender de `pytest`.
- **Benchmark científico:** `benchmarks/run_benchmarks.py` calcula BER, PSNR, SSIM, tiempo y memoria.
- **Simulador de plataformas:** aproxima el comportamiento de WhatsApp, Instagram, Telegram, Twitter/X, Facebook, Signal, LinkedIn y Reddit.
- **Panel web local:** interfaz en `127.0.0.1` para gestionar credenciales de cada adaptador y lanzar pruebas sin usar la terminal.
- **Wizard de credenciales:** configuración interactiva por terminal que guarda en `~/.config/stegstr/credentials.json`.

---

## Estado de los módulos por área

| Módulo | Estado | Validación |
|---|---|---|
| Motor de esteganografía (5 modos) | ✅ Funcional | Tests unitarios + robustez + 32 tests standalone |
| Criptografía (AES-GCM + Argon2id) | ✅ Funcional | Tests de roundtrip |
| Auto-tune | ✅ Funcional | Tests de convergencia |
| Simulador de plataformas v1 | ✅ Funcional | Tests de supervivencia |
| Simulador de plataformas v2 | ✅ Funcional | Tests de supervivencia |
| Steganálisis (Chi², RS, SPA) | ✅ Funcional | Tests comparativos PHANTOM vs GHOST |
| Cliente Nostr | ✅ Funcional | Código completo, tests E2E contra relays públicos reales |
| Adaptadores de redes sociales | ✅ Funcional | Validados con mocks; requieren credenciales reales para E2E |
| Interfaz para agentes de IA / API REST | ✅ Funcional | Implementación completa |
| CLI | ✅ Funcional | Comandos `encode`, `extract`, `capacity`, `optimize`, `analyze`, `config` |
| Benchmarks | ✅ Funcional | Métricas BER / PSNR / SSIM / tiempo / memoria |
| Wizard de credenciales | ✅ Funcional | Interactivo, guarda en `~/.config/stegstr/credentials.json` |
| Panel web local | ✅ Funcional | Flask en `127.0.0.1` |
| Esteganografía en video | ❌ No implementado | Placeholder — `VideoStegoEngine` vacío |
| Widget HTML explorador | ✅ Funcional | SPA interactiva: embed/extract/analyze/capacity/benchmark. Requiere backend Flask |

> **Nota sobre los simuladores:** son aproximaciones basadas en comportamientos documentados públicamente. No garantizan reproducir exactamente el procesamiento real de cada red social — para eso, usa la [validación en plataformas reales](#validación-en-plataformas-reales).

---

## Instalación

### Requisitos

- Python **3.9 – 3.13**
- `pip`
- Opcionalmente, Docker (para ejecución en contenedor)

### Dependencias

El proyecto define extras opcionales en `pyproject.toml`:

| Extra | Contenido | Cuándo usarlo |
|---|---|---|
| *(base)* | `numpy`, `Pillow`, `cryptography`, `rich`, `typer`, `argon2-cffi`, `scipy` | Siempre — motor de esteganografía + cifrado + DCT |
| `nostr` | `websockets`, `aiohttp`, `secp256k1` | Cliente Nostr |
| `agent` | `fastapi`, `uvicorn` | API REST del agente de IA |
| `full` | `nostr` + `agent` + `reedsolo`, `selenium`, `requests` | Todo excepto adaptadores sociales |
| `social` | `requests`, `tweepy`, `praw`, `ngrok`, `flask` | Adaptadores reales de redes sociales y GUI web local |
| `dev` | `pytest`, `pytest-asyncio`, `pytest-cov`, `hypothesis`, `bandit`, `safety`, `black`, `ruff` | Desarrollo, testing y linting |
| `all` | Todo lo anterior | Atajo que instala todo de una vez (recomendado para validación real) |

### Instalación estándar (recomendada)

```bash
git clone https://github.com/Juani1972/steganography.git
cd steganography
pip install -e ".[all]"
```

Esto instala el paquete en modo editable con soporte completo: esteganografía, Nostr, adaptadores de redes sociales, fallback de navegador y herramientas de desarrollo.

### Instalación mínima

```bash
pip install -e .
```

Soporta GHOST y PHANTOM. Para FORTRESS/ARMOR (modos DCT) necesitas `reedsolo` (instala con `pip install -e ".[full]"`).

### Instalación por combinaciones específicas

```bash
# Núcleo + ECC + simuladores completos
pip install -e ".[full]"

# Núcleo + adaptadores de redes sociales + panel web
pip install -e ".[social]"

# Núcleo + cliente Nostr
pip install -e ".[nostr]"

# Núcleo + API REST del agente
pip install -e ".[agent]"
```

### Instalación con Docker

El repositorio incluye tres Dockerfiles (`Dockerfile`, `Dockerfile.api`, `Dockerfile.gui`) y un `docker-compose.yml`. Requiere construcción local (no hay imagen publicada):

```bash
docker build -t stegstr:latest .
docker run --rm -v $(pwd):/data stegstr:latest python -m stegstr.cli encode --cover /data/cover.png --message "Hola" --output /data/stego.png
```

### Verificar la instalación

```bash
python check_env.py          # Comprueba dependencias funcionales
python check_credentials.py  # Comprueba credenciales configuradas
python validate.py           # Suite de validación exhaustiva (32 tests)
python -m stegstr.cli --help # Ayuda del CLI
```

---

## Configuración de credenciales

Los adaptadores de redes sociales reales necesitan credenciales propias de cada API.

### Opción 1 — Wizard interactivo (recomendado)

```bash
python -m stegstr.cli config --wizard
```

El wizard te guía plataforma por plataforma y guarda las credenciales en `~/.config/stegstr/credentials.json` con permisos `0o600` (solo tu usuario puede leerlo). Las credenciales se cargan automáticamente al iniciar cualquier comando que las necesite.

Comandos adicionales del wizard:

```bash
stegstr config --list                    # Ver estado de todas las plataformas
stegstr config --set KEY valor           # Guardar una credencial manualmente
stegstr config --get KEY                 # Leer una credencial
stegstr config --delete KEY              # Eliminar una credencial
stegstr config --test whatsapp           # Probar conexión con una plataforma
stegstr config --export-env              # Exportar como variables de entorno
```

### Opción 2 — Variables de entorno

Puedes exportar las variables directamente en tu shell:

```bash
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export IMGUR_CLIENT_ID="tu_client_id"
export REDDIT_CLIENT_ID="tu_client_id"
export REDDIT_CLIENT_SECRET="tu_secret"
export REDDIT_USERNAME="tu_user"
export REDDIT_PASSWORD="tu_pass"
export INSTAGRAM_BUSINESS_ACCOUNT_ID="tu_account_id"
export META_PAGE_ACCESS_TOKEN="tu_token"
export TWITTER_BEARER_TOKEN="tu_token"
export TWITTER_API_KEY="tu_key"
export TWITTER_API_SECRET="tu_secret"
export TWITTER_ACCESS_TOKEN="tu_token"
export TWITTER_ACCESS_SECRET="tu_secret"
export WHATSAPP_BUSINESS_PHONE_ID="tu_phone_id"
export WHATSAPP_ACCESS_TOKEN="tu_token"
export WHATSAPP_RECIPIENT_PHONE="tu_numero"
export NOSTR_PRIVATE_KEY="tu_clave_hex_64_chars"
```

### Opción 3 — Panel web local

```bash
pip install -e ".[social]"  # incluye flask
python -m stegstr.gui.web_app
# abre http://127.0.0.1:8080
```

### Widget visual interactivo (SPA)

```bash
# Método 1: Servidor dedicado del widget (recomendado)
pip install -e ".[social]"  # incluye flask, flask-cors
python -m stegstr.gui.widget_server
# Abre http://127.0.0.1:8080
```

```bash
# Método 2: Desde el panel web existente
python -m stegstr.gui.web_app
# El widget está disponible en http://127.0.0.1:8080/widget.html
```

El widget es una **SPA (Single Page Application)** moderna que permite:

- **Ocultar mensajes** con selección visual de los 5 modos (cards interactivas)
- **Extraer mensajes** de imágenes stego con detección automática de modo
- **Analizar detectabilidad** comparando cover vs stego (Chi², RS, SPA)
- **Calcular capacidad** por modo y plataforma con gráficos en tiempo real
- **Benchmark rápido** comparando los 5 modos en la misma imagen
- **Simulación de plataforma** para predecir supervivencia antes de publicar
- **Drag & drop** de imágenes con preview instantáneo
- **Métricas visuales** (PSNR, SSIM, delta, ECC, tiempo)
- **Tema oscuro** responsive, funciona en móvil y escritorio
- **Detección de backend** — si el servidor no está corriendo, muestra demo offline

> **Nota:** El widget requiere el backend Flask (`widget_server.py` o `web_app.py`) para las operaciones de esteganografía reales. El motor está en Python (numpy, scipy, PIL, cryptography) y no puede ejecutarse en el navegador. El frontend se comunica vía HTTP con el backend.

Desde el panel puedes:

- Ver de un vistazo qué plataformas tienen credenciales configuradas y cuáles no.
- Rellenar un formulario por plataforma que guarda directamente en el wizard.
- Pulsar "Probar" sobre cualquier plataforma configurada para lanzar una prueba real (embed → subir → descargar → extraer) y ver el resultado en el navegador.

> ⚠️ **Aviso de seguridad:** las credenciales se guardan en `~/.config/stegstr/credentials.json` en texto plano (aunque con permisos restrictivos `0o600`). El panel no tiene autenticación ni protección CSRF, y está pensado como herramienta de un solo usuario para uso exclusivamente en `127.0.0.1`. No lo expongas en una red ni en una interfaz pública.

### Credenciales necesarias por plataforma

| Plataforma | Variables necesarias | Dificultad |
|---|---|---|
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | ⭐ Fácil |
| Imgur | `IMGUR_CLIENT_ID` | ⭐ Fácil |
| Discord | `DISCORD_WEBHOOK_URL` | ⭐ Fácil |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` | ⭐⭐ Media |
| Instagram | `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `META_PAGE_ACCESS_TOKEN` | ⭐⭐⭐ Difícil |
| Twitter/X | `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` | ⭐⭐⭐⭐ Muy difícil |
| WhatsApp | `WHATSAPP_BUSINESS_PHONE_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_RECIPIENT_PHONE` | ⭐⭐⭐⭐⭐ Extremo |
| Nostr | `NOSTR_PRIVATE_KEY` | ⭐⭐ Media |

Usa `python check_credentials.py` para verificar qué credenciales tienes configuradas antes de ejecutar el benchmark.

---

## Uso rápido

### CLI — Comandos disponibles

```bash
# Ver ayuda completa
python -m stegstr.cli --help
python -m stegstr.cli <comando> --help
```

#### `encode` — Ocultar un mensaje en una imagen

```bash
# Básico
python -m stegstr.cli encode --cover cover.png --message "Mensaje secreto" --output stego.png

# Con contraseña (cifrado AES-256-GCM)
python -m stegstr.cli encode --cover cover.png --message "Mensaje" --output stego.png --password clave

# Con plataforma de destino (auto-selección de modo)
python -m stegstr.cli encode --cover cover.png --message "Mensaje" --output stego.png --platform instagram

# Modo específico
python -m stegstr.cli encode --cover cover.png --message "Mensaje" --output stego.png --mode FORTRESS

# Con parámetros personalizados
python -m stegstr.cli encode --cover cover.png --message "Mensaje" --output stego.png --mode ARMOR --delta 6.0 --ecc 48

# Salida JSON (para scripting)
python -m stegstr.cli encode --cover cover.png --message "Mensaje" --output stego.png --json
```

#### `extract` — Extraer un mensaje oculto

```bash
# Básico
python -m stegstr.cli extract --stego stego.png

# Con contraseña
python -m stegstr.cli extract --stego stego.png --password clave

# Forzar modo (útil si la auto-detección falla)
python -m stegstr.cli extract --stego stego.png --mode ARMOR

# Decodificar payload binario (base64)
python -m stegstr.cli extract --stego stego.png --decode

# Salida JSON
python -m stegstr.cli extract --stego stego.png --json
```

#### `capacity` — Calcular capacidad de una imagen

```bash
python -m stegstr.cli capacity --cover cover.png --mode ARMOR
python -m stegstr.cli capacity --cover cover.png --mode FORTRESS --platform whatsapp_standard
```

#### `optimize` — Auto-tune (optimizar parámetros)

```bash
python -m stegstr.cli optimize --cover cover.png --message "Mensaje de prueba" --platform instagram
python -m stegstr.cli optimize --cover cover.png --message "Mensaje" --platform telegram_photo --depth deep --json
```

Profundidad de búsqueda: `quick` (rápida), `standard` (por defecto), `deep` (exhaustiva).

#### `analyze` — Análisis de detectabilidad

```bash
python -m stegstr.cli analyze --cover cover.png --stego stego.png
```

#### `config` — Gestión de credenciales

```bash
python -m stegstr.cli config --wizard      # Wizard interactivo
python -m stegstr.cli config --list        # Listar configuradas
python -m stegstr.cli config --set KEY val # Guardar valor
python -m stegstr.cli config --get KEY     # Leer valor
python -m stegstr.cli config --delete KEY  # Eliminar valor
python -m stegstr.cli config --test telegram  # Probar plataforma
python -m stegstr.cli config --export-env  # Exportar a shell
```

### Uso programático — motor de esteganografía

```python
from stegstr.stego.engine import StegoEngine, StegoMode

# Embed básico
engine = StegoEngine(mode=StegoMode.ARMOR, password="clave")
meta = engine.embed("cover.png", "Mensaje secreto", "stego.png")
print(meta)  # modo, capacidad, métricas de calidad, etc.

# Extract
result = engine.extract("stego.png")
print(result["message"])

# Auto-tune
tune = engine.auto_tune("cover.png", "Mensaje", "instagram", search_depth="standard")
print(tune["mode"], tune["delta"], tune["ecc"])
```

### Uso programático — simulador realista v2

```python
from stegstr.platform.simulator_v2 import RealisticPlatformSimulator

sim = RealisticPlatformSimulator()
result = sim.simulate("instagram", "input.png", "output.jpg")
print(result["transformations"])  # ['converted_to_rgb', 'resized_to_1080x1080', ...]
```

Consulta `examples/basic_usage.py` y `examples/platform_guide.md` para ejemplos completos.

### Benchmarks

```bash
# Benchmark científico básico
python benchmarks/run_benchmarks.py --output benchmarks/results.json

# Modo rápido
python benchmarks/run_benchmarks.py --quick

# Benchmark cross-platform con dataset diverso
python scripts/real_world_benchmark.py --stress --carriers 10 --messages 3 --seed 42

# Auditoría de seguridad (bandit + safety + tests de seguridad)
python scripts/run_security_audit.py
```

---

## Cifrado

Stegstr cifra el payload con **AES-256-GCM** (cifrado autenticado — protege confidencialidad e integridad). La clave se deriva de la contraseña mediante **Argon2id**, con los siguientes parámetros:

| Parámetro | Valor |
|---|---|
| Time cost | 3 |
| Memory cost | 64 MB |
| Parallelism | 4 |
| Salt | 16 bytes aleatorios por operación |

---

## Interoperabilidad con agentes de IA

Stegstr expone una API de *tool-calling* pensada para integrarse con agentes LLM.

```python
from stegstr.ai_agent.interface import AIAgent

agent = AIAgent()
result = agent.execute({
    "action": "encode",
    "carrier": "cover.png",
    "message": "hello",
    "output": "stego.png",
    "platform": "whatsapp_standard",
})
```

Acciones disponibles: `analyze_carrier`, `estimate_capacity`, `recommend_parameters`, `encode`, `decode`, `simulate_platform`, `auto_optimize`, `benchmark_detectability`, `list_actions`. Todos los métodos devuelven diccionarios serializables a JSON.

### API REST opcional

`stegstr/api/agent_api.py` expone un servidor FastAPI opcional para el agente:

- `POST /agent/execute`
- `GET /agent/actions`
- `GET /health`

Arrancar:

```bash
pip install -e ".[agent]"
uvicorn stegstr.api.agent_api:app --host 0.0.0.0 --port 8000
```

### Sincronización de mensajes (Networking)

`stegstr/networking/sync_manager.py` gestiona el ciclo de vida de un mensaje con reintentos, deduplicación y verificación de integridad:

```python
import asyncio
from stegstr.networking.sync_manager import SyncManager

sm = SyncManager(private_key_hex="tu_clave")
await sm.start()
msg_id = await sm.send_message(payload_b64="...", platform_hint="whatsapp_standard")
```

Estados del mensaje: `CREATED → QUEUED → SENT → RECEIVED → VERIFIED → FAILED → RETRYING`, con reintentos con backoff exponencial y almacenamiento persistente.

---

## Estructura del proyecto

```
steganography/
├── stegstr/
│   ├── __init__.py
│   ├── cli.py                    # CLI v2.2.0 (Click + Rich + JSON)
│   ├── stego/
│   │   └── engine.py             # Motor: 5 modos + AES-256-GCM + Argon2id + auto-tune
│   ├── agent/
│   │   └── optimizer.py          # Optimizador heurístico (reglas basadas en capacidad)
│   ├── ai_agent/
│   │   └── interface.py          # API de tool-calling para agentes de IA
│   ├── api/
│   │   ├── agent_api.py          # Servidor FastAPI opcional para el agente de IA
│   │   └── server.py             # PLACEHOLDER (no implementado)
│   ├── networking/
│   │   └── sync_manager.py       # Gestión de sincronización/reintentos de mensajes
│   ├── platform/
│   │   ├── analyzer.py           # Análisis de transformaciones de plataforma
│   │   ├── simulator.py          # Simulación de plataformas (v1)
│   │   ├── simulator_v2.py       # Simulador realista de plataformas (v2)
│   │   ├── real_world_validator.py # Validación contra APIs reales
│   │   ├── real_world_pipeline.py  # Pipeline de validación
│   │   └── adapters/             # Adaptadores por plataforma
│   │       ├── discord.py
│   │       ├── imgur.py
│   │       ├── instagram.py
│   │       ├── reddit.py
│   │       ├── selenium_fallback.py
│   │       ├── telegram.py
│   │       ├── twitter.py
│   │       └── whatsapp.py
│   ├── video/
│   │   └── engine.py             # PLACEHOLDER (no implementado)
│   ├── gui/
│   │   ├── web_app.py            # Panel web local (Flask)
│   │   └── widget.html           # PLACEHOLDER (no implementado)
│   ├── nostr/
│   │   ├── __init__.py
│   │   └── client.py             # Cliente Nostr NIP-01/05/94/96/98
│   ├── analysis/
│   │   └── steganalysis.py       # Detectores estadísticos (Chi², RS, SPA, entropía)
│   └── config/
│       └── wizard.py             # Wizard interactivo de credenciales
│
├── benchmarks/
│   ├── run_benchmarks.py         # Benchmark científico (BER, PSNR, SSIM, etc.)
│   ├── real_benchmark.py         # Benchmark cross-platform
│   └── dataset_generator.py      # Generación de datasets de prueba (placeholder)
│
├── examples/
│   ├── basic_usage.py
│   └── platform_guide.md
│
├── scripts/
│   ├── run_security_audit.py     # Auditoría: Bandit + Safety + tests de seguridad
│   ├── real_world_benchmark.py   # Validación contra APIs reales de plataformas
│   ├── health_check.py           # Verificación de dependencias y estado del sistema
│   ├── analyze_detectability.py  # Placeholder
│   └── benchmark.py              # Placeholder
│
├── samples/                      # Imágenes de muestra para pruebas
├── tests/                        # Suite de tests pytest
├── validate.py                   # Validación exhaustiva standalone (32 tests)
├── check_env.py                  # Verificación de dependencias funcionales
├── check_credentials.py          # Verificación de credenciales por adaptador
├── demo.py                       # Demostración rápida
├── quick_test.py                 # Smoke test
├── pyproject.toml                # Metadatos y dependencias (PEP 621)
├── requirements.txt
├── Dockerfile / Dockerfile.api / Dockerfile.gui
├── docker-compose.yml
└── LICENSE                       # MIT
```

---

## Tests

```bash
# Tests unitarios y de robustez
pytest tests/test_robustness.py -v

# Tests de seguridad y fuzzing
pytest tests/test_security.py -v

# Tests de steganálisis
pytest tests/test_steganalysis.py -v

# Tests de integración end-to-end
pytest tests/test_integration.py -v

# Tests con adaptadores mock realistas de redes sociales
pytest tests/test_real_world.py -v

# Tests del cliente Nostr (incluye E2E contra relays públicos reales;
# si un relay está caído, el test se salta con un mensaje informativo)
pytest tests/test_nostr.py -v

# Validación exhaustiva (standalone, sin pytest)
python validate.py

# Benchmarks rápidos
python benchmarks/run_benchmarks.py --quick

# Benchmark reproducible (no requiere credenciales reales)
python scripts/real_world_benchmark.py --stress --carriers 10 --messages 3 --seed 42

# Cobertura completa
pytest --cov=stegstr --cov-report=html
```

---

## Plataformas (simulación)

| Plataforma | Modo recomendado | Mensaje máx. aprox. | ECC | Notas |
|---|---|---|---|---|
| WhatsApp Standard | FORTRESS | ~150 B | 96 | Resize + calidad JPEG 55 |
| WhatsApp HD | ARMOR | ~2 KB | 48 | Calidad JPEG 75 |
| Telegram Photo | ARMOR | ~3 KB | 40 | Calidad JPEG 82 |
| Telegram File | GHOST | ~50 KB | 0 | Sin compresión |
| Instagram | FORTRESS | ~150 B | 96 | Recorte 1:1 + doble compresión JPEG |
| Twitter/X | ARMOR | ~4 KB | 32 | Límite de 5MB |
| Facebook | ARMOR | ~3 KB | 40 | Aplica UnsharpMask |
| Signal HD | GHOST | ~50 KB | 16 | Calidad JPEG 95 |
| LinkedIn | ARMOR | ~5 KB | 32 | Experimental |
| Reddit | ARMOR | ~10 KB | 24 | Experimental |

> ⚠️ El simulador es una aproximación basada en comportamientos documentados públicamente. No garantiza reproducir exactamente el procesamiento real de cada plataforma — para eso, usa la validación en plataformas reales (siguiente sección).

---

## Validación en plataformas reales

Comprueba automáticamente si un mensaje sobrevive al procesamiento real (no simulado) de una red social, usando las APIs oficiales de cada plataforma.

```bash
# Ver qué plataformas están disponibles según tus credenciales
python scripts/real_world_benchmark.py --list

# Benchmark completo
python scripts/real_world_benchmark.py --message "Mensaje secreto" --cover cover.png

# Solo plataformas específicas
python scripts/real_world_benchmark.py --platforms telegram,imgur,discord

# Benchmark reproducible con N iteraciones y semilla fija
python scripts/real_world_benchmark.py --cover cover.png --message "test" \
    --iterations 10 --seed 42 --output report.json --csv report.csv

# Test de estrés: múltiples carriers × múltiples mensajes
python scripts/real_world_benchmark.py --stress --carriers 20 --messages 5 --seed 42

# Detección de regresiones frente a una baseline previa
python scripts/real_world_benchmark.py --cover cover.png --baseline baseline.json
```

### Plataformas soportadas y credenciales necesarias

| Plataforma | API | Variables de entorno | Dificultad | Compresión aplicada |
|---|---|---|---|---|
| Telegram | Bot API | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | ⭐ Fácil | Ligera |
| Imgur | Anónima | `IMGUR_CLIENT_ID` | ⭐ Fácil | Moderada (proxy JPEG) |
| Discord | Webhook | `DISCORD_WEBHOOK_URL` | ⭐ Fácil | Moderada |
| Reddit | PRAW | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` | ⭐⭐ Media | Moderada |
| Instagram | Graph API | `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `META_PAGE_ACCESS_TOKEN` | ⭐⭐⭐ Difícil | Agresiva |
| Twitter/X | API v2 | `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` | ⭐⭐⭐⭐ Muy difícil | Muy agresiva |
| WhatsApp | Business API (self-messaging) / Selenium | `WHATSAPP_BUSINESS_PHONE_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_RECIPIENT_PHONE` (mismo número que `phone_id` para auto-mensajería) | ⭐⭐⭐⭐⭐ Extremo | Variable |
| Nostr | Protocolo descentralizado | `NOSTR_PRIVATE_KEY` | ⭐⭐ Media | N/A (protocolo) |

Usa `python check_credentials.py` para verificar qué credenciales tienes configuradas antes de ejecutar el benchmark.

> **Notas sobre adaptadores concretos:**
> - **WhatsApp:** el modo self-messaging requiere una cuenta Business con el mismo número como remitente y destinatario — comportamiento válido según la API de Meta. También existe un fallback vía Selenium con sesión persistente para casos sin API Business.
> - **Instagram:** si no tienes IP pública, el adaptador puede levantar un servidor HTTP temporal propio y usar ngrok como fallback automático (requiere el CLI de ngrok disponible).
> - **Telegram:** el modo documento (`sendDocument`) preserva el archivo original al 100%, permitiendo comparación exacta contra el modo foto comprimido (`sendPhoto`).
> - **Nostr:** los tests end-to-end usan relays públicos reales; si un relay está caído, el test se salta con un mensaje informativo en lugar de fallar.

### Métricas reportadas

- **Supervivencia:** si el mensaje se recupera intacto tras el procesamiento de la plataforma.
- **PSNR:** calidad de imagen tras el procesamiento.
- **BER (Bit Error Rate):** tasa de error de bits real, bit a bit, entre el mensaje original y el recuperado (no una simple comparación de strings).
- **Mejor modo por plataforma:** recomendación automática según los resultados obtenidos.
- **Trazabilidad:** hash del carrier y del payload en cada ejecución, para poder auditar resultados.
- **Combinaciones saltadas:** si falta una dependencia opcional (por ejemplo `reedsolo` para ECC en modos FORTRESS/ARMOR), la combinación se registra explícitamente en el reporte (campo `skipped`, con plataforma, modo y motivo) en lugar de desaparecer silenciosamente.

---

## Resistencia al steganálisis

- **Modo PHANTOM:** usa LSB Matching (±1) en lugar de LSB Replacement, lo que derrota el ataque estadístico Chi-square clásico.
- **Detectores integrados:** Chi-square (χ²), RS Analysis, Sample Pairs Analysis (SPA) y entropía LSB.
- **Análisis comparativo:** `stegstr/analysis/steganalysis.py` compara la imagen original (cover) contra la imagen con mensaje oculto (stego).
- **Benchmark de detectabilidad:** evalúa estadísticamente cuán invisible resulta un mensaje oculto.

```python
from stegstr.analysis.steganalysis import StegAnalyzer

analyzer = StegAnalyzer()
report = analyzer.analyze("stego.png")
print(f"Score de detección: {report['combined_detection_score']}")
print(f"¿Probable stego? {report['likely_stego']}")
```

> Nota técnica: al comparar PHANTOM vs GHOST con imágenes de portada de ruido aleatorio, ambos p-valores pueden quedar saturados cerca de 1.0, con la diferencia real entre modos concentrada en cifras decimales muy pequeñas. Para una comparación robusta, se recomienda repetir el experimento sobre varias imágenes de portada distintas y comparar la mediana de los resultados en lugar de una única muestra.

---

## Seguridad

- **Derivación de clave:** Argon2id con `time=3`, `memory=64MB`, `parallelism=4`.
- **Límites de payload:** 10MB comprimido / 50MB en crudo. Límite de imagen: 16384×16384 px.
- **Validación de cabecera:** se verifican `MAGIC`, versión, modo, ECC y longitud de payload antes de procesar.
- **Protección contra zip-bombs:** el descompresor aplica un límite de ratio de compresión.
- **Protección contra DoS:** límite de 30 iteraciones máximo en la búsqueda de delta.
- **Validación estricta de parámetros:** los valores de delta fuera del rango `[0.5, 50.0]` lanzan un `ValueError` en lugar de recortarse silenciosamente.
- **Protección contra path traversal:** el motor rechaza rutas que contengan `..` o que apunten a directorios del sistema.
- **Nostr:** `secp256k1` es obligatorio — no existe fallback inseguro si la librería no está disponible.
- **Panel web local:** sin autenticación ni protección CSRF por diseño — pensado exclusivamente para uso en `127.0.0.1` por un único usuario; las credenciales se guardan en `~/.config/stegstr/credentials.json`.
- **Auditoría automatizada:** `scripts/run_security_audit.py` ejecuta Bandit (análisis estático) y Safety (dependencias vulnerables) además de los tests de seguridad y fuzzing.

---

## Solución de problemas

### Faltan dependencias

```bash
pip install -e ".[all]"
```

Si ves errores al importar un adaptador de red social concreto, comprueba que instalaste el extra `social` (incluye `requests`, `tweepy`, `praw`, `ngrok`).

### `RuntimeError` al hacer el primer `embed()` / `extract()`

El motor cifra siempre, incluso con la contraseña por defecto, por lo que `argon2-cffi` es una dependencia núcleo obligatoria. Si instalaste solo con `pip install -e .` sin extras y sigues viendo este error, confirma que `argon2-cffi` está instalado (`pip show argon2-cffi`).

Si el error menciona `scipy`, instálalo: `pip install scipy` (o usa `pip install -e ".[full]"`).

### El modo PHANTOM falla

Asegúrate de estar usando una versión reciente. Versiones antiguas tenían una semilla RNG fija que rompía el roundtrip (embed → extract); la versión actual deriva la semilla del hash del propio mensaje.

### Errores de validación de delta

Los valores de delta fuera del rango `[0.5, 50.0]` lanzan un `ValueError` en lugar de recortarse (clamp) silenciosamente. Revisa el valor pasado a `--delta` o al parámetro `delta_override` si construyes el motor programáticamente.

### Protección contra path traversal

El motor rechaza rutas que contengan `..` o que apunten a directorios del sistema. Si tu script falla al leer o escribir un archivo, verifica que la ruta sea relativa y esté dentro del árbol de trabajo esperado.

### Un test de esteganálisis falla de forma intermitente

Los tests comparativos entre PHANTOM y GHOST pueden ser sensibles a la imagen de portada usada como muestra única. Si ves resultados inconsistentes entre ejecuciones, repite la comparación sobre varias imágenes distintas y compara la mediana en lugar de una sola muestra (ver [Resistencia al steganálisis](#resistencia-al-steganálisis)).

### Un adaptador de red social falla al subir/descargar

- Confirma con `python check_credentials.py` que las variables de entorno necesarias están definidas.
- También puedes usar `python -m stegstr.cli config --list` para ver el estado desde el wizard.
- Empieza probando con Discord o Imgur, que son los más simples de configurar, antes de pasar a Instagram/WhatsApp/Twitter.
- Si usas el panel web local, revisa que el servidor siga escuchando en `127.0.0.1` y que las credenciales se hayan guardado correctamente.

### Otros problemas

- Ejecuta `python check_env.py` para confirmar que todas las dependencias funcionales están correctamente instaladas.
- Ejecuta `python validate.py` para una validación exhaustiva del motor.
- Para adaptadores de redes sociales, ejecuta `python check_credentials.py` o `stegstr config --list`.

---

## Contribuir

¡Gracias por tu interés en contribuir a Stegstr!

### Configuración del entorno de desarrollo

```bash
git clone https://github.com/Juani1972/steganography.git
cd steganography
pip install -e ".[all]"
```

### Ejecutar los tests

```bash
pytest tests/ -v
python validate.py
```

### Estilo de código

El proyecto usa `black` y `ruff`:

```bash
black stegstr/ tests/
ruff check stegstr/ tests/
```

Antes de enviar un Pull Request, ejecuta también la auditoría de seguridad (`python scripts/run_security_audit.py`) y confirma que el CI (`.github/workflows/ci.yml`, que corre en Python 3.9–3.13) pasaría en tu entorno local.

### Buenas prácticas al añadir tests

Si tu cambio usa `StegoMode.ARMOR`/`FORTRESS`/`HYBRID` o el parámetro `password=`, añade el correspondiente `pytest.importorskip` para las dependencias opcionales relacionadas (`reedsolo`, `argon2-cffi`), de forma que el test se salte de forma clara si la dependencia no está instalada, en lugar de fallar con un error confuso.

---

## Licencia

MIT — Open Source. Consulta el archivo `LICENSE` para el texto completo.