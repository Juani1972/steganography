# Stegstr Next — Steganografía Robusta para Redes Sociales

**Estado: Beta técnica avanzada** · **Licencia: MIT**

> Arquitectura funcional y componentes principales implementados. Algunos módulos (marcados como 🧪 Experimental más abajo) requieren validación end-to-end adicional en entornos reales antes de considerarse producción.

Stegstr es un cliente de esteganografía en Python orientado a la supervivencia de mensajes ocultos frente a la recompresión y el reprocesamiento que aplican las redes sociales y apps de mensajería. Combina:

- 5 modos de esteganografía optimizados para distintos escenarios de robustez/capacidad.
- Cifrado autenticado **AES-256-GCM** con derivación de clave **Argon2id**.
- Corrección de errores (ECC) mediante **Reed-Solomon**.
- Marcadores de sincronización DCT para resistir recompresión JPEG.
- Un motor heurístico de **auto-tune** que optimiza parámetros automáticamente.
- Simuladores (experimentales) del procesamiento de imágenes de WhatsApp, Instagram, Telegram, Twitter/X, Facebook, Signal, LinkedIn y Reddit.
- Un cliente **Nostr** completo (NIP-01/05/94/96/98).
- Una API de *tool-calling* para agentes de IA (LLM), un gestor de sincronización de mensajes y una API REST opcional.
- CLI con salida en texto enriquecido (Rich) y JSON, y un panel web local para gestionar credenciales.
- Suite de benchmarking científico (BER, PSNR, SSIM) y validación de esteganálisis (Chi², RS, SPA).

---

## Tabla de contenidos

1. [Características principales](#características-principales)
2. [Estado de los módulos](#estado-de-los-módulos-por-área)
3. [Instalación](#instalación)
4. [Configuración de credenciales y GUI local](#configuración-de-credenciales-y-gui-local)
5. [Uso rápido](#uso-rápido)
6. [Cifrado](#cifrado)
7. [Interoperabilidad con agentes de IA](#interoperabilidad-con-agentes-de-ia)
8. [Estructura del proyecto](#estructura-del-proyecto)
9. [Tests](#tests)
10. [Plataformas soportadas (simulación)](#plataformas-simulación-experimental)
11. [Validación en plataformas reales](#validación-en-plataformas-reales)
12. [Resistencia al steganálisis](#resistencia-al-steganálisis)
13. [Seguridad](#seguridad)
14. [Soporte de video](#soporte-de-video)
15. [GUI interactiva (explorador de modos)](#gui-interactiva-explorador-de-modos)
16. [Compatibilidad de versiones de payload](#compatibilidad-de-versiones-de-payload)
17. [Solución de problemas](#solución-de-problemas)
18. [Contribuir](#contribuir)
19. [Historial de versiones (Changelog)](#historial-de-versiones-changelog)
20. [Licencia](#licencia)

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
- **Validación exhaustiva:** script `validate.py` con más de 28 tests de integridad, sin depender de `pytest`.
- **Benchmark científico:** `benchmarks/run_benchmarks.py` calcula BER, PSNR, SSIM, tiempo y memoria.
- **Simulador experimental de plataformas:** aproxima el comportamiento de WhatsApp, Instagram, Telegram, Twitter/X, Facebook, Signal, LinkedIn y Reddit.
- **Panel web local:** interfaz en `127.0.0.1` para gestionar credenciales de cada adaptador y lanzar pruebas sin usar la terminal.

---

## Estado de los módulos por área

| Módulo | Estado | Validación |
|---|---|---|
| Motor de esteganografía (5 modos) | ✅ Funcional | Tests unitarios + robustez |
| Criptografía (AES-GCM + Argon2id) | ✅ Funcional | Tests de roundtrip |
| Auto-tune | ✅ Funcional | Tests de convergencia |
| Simulador de plataformas v1 | ✅ Funcional | Tests de supervivencia |
| Simulador de plataformas v2 | 🧪 Experimental | Arquitectura implementada |
| Steganálisis (Chi², RS, SPA) | 🧪 Experimental | Tests comparativos PHANTOM vs GHOST en validación |
| Esteganografía en video | 🧪 Experimental | Arquitectura + FEC global implementados |
| Cliente Nostr | 🧪 Experimental | Código completo, con tests E2E contra relays públicos reales |
| Adaptadores de redes sociales (WhatsApp, Instagram, Telegram, Twitter/X, Discord, Reddit, Imgur) | 🧪 Experimental | Validados de forma desigual — ver [Validación en plataformas reales](#validación-en-plataformas-reales) |
| Interfaz para agentes de IA / API REST | 🧪 Experimental | Implementación completa, integración no validada extensamente |
| CLI | ✅ Funcional | Comandos `embed` / `extract` / `test` / `check` / `analyze` |
| Benchmarks | ✅ Funcional | Métricas BER / PSNR / SSIM / tiempo / memoria |

> **Nota sobre los simuladores:** son aproximaciones basadas en comportamientos documentados públicamente. No garantizan reproducir exactamente el procesamiento real de cada red social — para eso, usa la [validación en plataformas reales](#validación-en-plataformas-reales).

---

## Instalación

### Requisitos

- Python **3.9 – 3.13**
- `pip`
- Opcionalmente, Docker (para ejecución en contenedor)

### Dependencias

El proyecto define extras opcionales en `pyproject.toml` / `requirements.txt`:

| Extra | Contenido | Cuándo usarlo |
|---|---|---|
| *(base)* | `numpy`, `pillow`, `click`, `rich`, `cryptography`, `argon2-cffi`, `reedsolo` | Siempre — motor de esteganografía + cifrado (el motor cifra siempre, incluso con contraseña por defecto, así que `argon2-cffi` es obligatorio) |
| `full` | `scipy`, `opencv-python`, `scikit-image` | Esteganografía completa (incluye video) |
| `nostr` | `websockets`, `aiohttp`, `secp256k1` | Cliente Nostr |
| `social` | `requests`, `tweepy`, `praw`, `ngrok`, `flask` | Adaptadores reales de redes sociales y GUI web local |
| `browser` | `selenium` | Fallback por navegador para WhatsApp/Facebook/Signal |
| `dev` | `pytest`, `pytest-cov`, `hypothesis`, `flake8`, `pylint`, `black`, `isort`, `bandit`, `safety` | Desarrollo, testing y linting |
| `all` | `full` + `social` + `browser` + `nostr` + `dev` | Atajo que instala todo de una vez (recomendado para validación real) |

### Instalación estándar (recomendada)

```bash
git clone https://github.com/Juani1972/steganography.git
cd steganography
pip install -e ".[all]"
```

Esto instala el paquete en modo editable con soporte completo: esteganografía, Nostr, adaptadores de redes sociales, fallback de navegador y herramientas de desarrollo.

### Instalación mínima

Si solo necesitas el motor base (embed/extract con imágenes PNG):

```bash
pip install -e .
```

### Instalación por combinaciones específicas

```bash
# Núcleo + procesamiento de imagen
pip install -e ".[full]"

# Núcleo + adaptadores de redes sociales
pip install -e ".[social]"

# Núcleo + cliente Nostr
pip install -e ".[nostr]"
```

### Instalación con Docker

El repositorio incluye tres Dockerfiles (`Dockerfile`, `Dockerfile.api`, `Dockerfile.gui`) y un `docker-compose.yml`. Requiere construcción local (no hay imagen publicada):

```bash
docker build -t stegstr:latest .
docker run --rm -v $(pwd):/data stegstr:latest embed /data/cover.png "Hola" -o /data/stego.png
```

### Verificar la instalación

```bash
python check_env.py          # Comprueba que las dependencias funcionales estén disponibles
python check_credentials.py  # Comprueba qué credenciales están configuradas por adaptador
python validate.py           # Ejecuta la suite de validación exhaustiva (28+ tests)
```

---

## Configuración de credenciales y GUI local

Los adaptadores de redes sociales reales necesitan credenciales propias de cada API (ver la tabla en [Validación en plataformas reales](#validación-en-plataformas-reales)).

### Opción 1 — Archivo `.env`

```bash
cp .env.example .env
# edita .env con las credenciales de las plataformas que vayas a usar
export $(grep -v '^#' .env | xargs)
python check_credentials.py
```

### Opción 2 — Panel web local

En lugar de editar el `.env` a mano, puedes usar un panel web que corre en tu propia máquina:

```bash
pip install -e ".[social]"   # incluye flask
python -m stegstr.gui.web_app
# abre http://127.0.0.1:8080
```

Desde el panel puedes:

- Ver de un vistazo qué plataformas tienen credenciales configuradas y cuáles no.
- Rellenar un formulario por plataforma que guarda directamente en `.env` (el servidor solo escucha en `127.0.0.1`, no sale de tu equipo).
- Pulsar "Probar" sobre cualquier plataforma configurada para lanzar una prueba real (embed → subir → descargar → extraer) y ver el resultado en el navegador.

> ⚠️ **Aviso de seguridad:** el `.env` se guarda en texto plano, el panel no tiene autenticación ni protección CSRF, y está pensado como herramienta de un solo usuario para uso exclusivamente en `127.0.0.1`. No lo expongas en una red ni en una interfaz pública.

---

## Uso rápido

### Cifrado y embed/extract básicos

```bash
python -m stegstr.cli embed cover.png "Mensaje" -o stego.png --password clave
python -m stegstr.cli extract stego.png --password clave
```

### Comandos principales del CLI

```bash
# Verificar entorno
python check_env.py

# Validación exhaustiva (28+ tests)
python validate.py

# Embed con auto-tune (elige automáticamente los mejores parámetros)
python -m stegstr.cli embed cover.png "Mensaje" -o stego.png --platform instagram --auto-tune

# Extraer un mensaje oculto
python -m stegstr.cli extract stego.png

# Extraer y decodificar payload binario (base64)
python -m stegstr.cli extract stego.png --decode

# Test de robustez frente al procesamiento de una plataforma concreta
python -m stegstr.cli test cover.png "Mensaje" --platform whatsapp_standard

# Benchmark científico básico
python benchmarks/run_benchmarks.py --output benchmarks/results.json

# Benchmark cross-platform con dataset diverso e intervalos de confianza del 95%
python benchmarks/dataset_generator.py --output benchmarks/dataset --count 100
python benchmarks/real_benchmark.py --dataset benchmarks/dataset --output benchmarks/report.json --plots

# Auditoría de seguridad (bandit + safety + tests de seguridad)
python scripts/run_security_audit.py
```

### Uso programático — simulador realista v2

```python
from stegstr.platform.simulator_v2 import RealisticPlatformSimulator
# Consulta examples/basic_usage.py y examples/platform_guide.md para ejemplos completos
```

### Uso programático — esteganografía en video

```python
from stegstr.video.engine import VideoStegoEngine
from stegstr.stego.engine import StegoMode

vengine = VideoStegoEngine(mode=StegoMode.ARMOR, password="clave")
vengine.embed_video("input.mp4", "mensaje largo...", "output.mp4")
result = vengine.extract_video("output.mp4")
print(result["message"])
```

Requiere `opencv-python` (incluido en el extra `full`).

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
stegstr/
├── __init__.py
├── cli.py                    # CLI con Rich + salida JSON
├── stego/
│   └── engine.py              # Motor: 5 modos + AES-256-GCM + Argon2id + auto-tune
├── agent/
│   └── optimizer.py           # Optimizador heurístico vectorizado
├── ai_agent/
│   └── interface.py            # API de tool-calling para agentes de IA
├── api/
│   └── agent_api.py            # Servidor FastAPI opcional para el agente de IA
├── networking/
│   └── sync_manager.py         # Gestión de sincronización/reintentos de mensajes
├── platform/
│   ├── analyzer.py             # Análisis de transformaciones de plataforma
│   ├── simulator.py            # Simulación experimental de plataformas (v1)
│   ├── simulator_v2.py         # Simulador realista de plataformas (v2)
│   ├── real_world_validator.py # Validación contra APIs reales
│   └── adapters/                # Adaptadores por plataforma (whatsapp, instagram, telegram, twitter, discord, reddit, imgur...)
├── video/
│   └── engine.py                # Motor de esteganografía en video (FEC global)
├── gui/
│   ├── widget.html              # Explorador visual de modos
│   └── web_app.py               # Panel web local (Flask) de credenciales y pruebas
└── nostr/
    └── client.py                # Cliente Nostr NIP-01/05/94/96/98

benchmarks/
├── run_benchmarks.py            # Benchmark científico (BER, PSNR, SSIM, etc.)
├── dataset_generator.py         # Generación de datasets de prueba
└── real_benchmark.py            # Benchmark cross-platform con intervalos de confianza

examples/
├── basic_usage.py               # Ejemplos de uso básico
└── platform_guide.md            # Guía de plataformas

scripts/
├── run_security_audit.py        # Auditoría: Bandit + Safety + tests de seguridad
├── real_world_benchmark.py      # Validación contra APIs reales de plataformas
└── analyze_detectability.py     # Análisis comparativo de esteganálisis

samples/                         # Imágenes/archivos de muestra para pruebas

tests/
├── test_robustness.py           # Tests unitarios y de robustez
├── test_security.py             # Tests de seguridad y fuzzing
├── test_integration.py          # Tests end-to-end
├── test_benchmarks.py           # Benchmarks automatizados
├── test_fuzzing.py              # Fuzzing basado en propiedades (hypothesis)
├── test_steganalysis.py         # Tests de resistencia a esteganálisis
├── test_real_world.py           # Tests con adaptadores mock realistas
└── test_nostr.py                # Tests del cliente Nostr (incluye E2E contra relays reales)

.github/workflows/
└── ci.yml                       # CI/CD: Python 3.9–3.13, bandit, safety, benchmarks

validate.py                      # Validación exhaustiva standalone (sin pytest)
check_env.py                     # Verificación de dependencias funcionales
check_credentials.py             # Verificación de credenciales para adaptadores reales
demo.py                          # Demostración rápida de funcionalidad
quick_test.py                    # Test rápido de humo (smoke test)
.env.example                     # Plantilla de variables de credenciales, comentada
Dockerfile / Dockerfile.api / Dockerfile.gui   # Contenedores Docker
docker-compose.yml               # Orquestación de servicios
pyproject.toml                   # Metadatos y dependencias (PEP 621)
requirements.txt                 # Dependencias por extras (pip clásico)
setup.py / setup_contest_deps.py
MANIFEST.in
LICENSE                          # MIT
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

# Tests del cliente Nostr (incluye E2E contra relays públicos reales; si un relay
# está caído, el test se salta con un mensaje informativo)
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

## Plataformas (simulación experimental)

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

> ⚠️ El simulador es una aproximación experimental basada en comportamientos documentados públicamente. No garantiza reproducir exactamente el procesamiento real de cada plataforma — para eso, usa la validación en plataformas reales (siguiente sección).

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
| Reddit | PRAW | `REDDIT_CLIENT_ID`, `REDDIT_SECRET`, `REDDIT_USER`, `REDDIT_PASS` | ⭐⭐ Media | Moderada |
| Instagram | Graph API | `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `META_PAGE_ACCESS_TOKEN` | ⭐⭐⭐ Difícil | Agresiva |
| Twitter/X | API v2 | `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` | ⭐⭐⭐⭐ Muy difícil | Muy agresiva |
| WhatsApp | Business API (self-messaging) / Selenium | `WHATSAPP_BUSINESS_PHONE_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_RECIPIENT_PHONE` (mismo número que `phone_id` para auto-mensajería) | ⭐⭐⭐⭐⭐ Extremo | Variable |
| Facebook | Selenium | Login manual | ⭐⭐⭐⭐⭐ Extremo | Variable |

Usa `check_credentials.py` para verificar qué credenciales tienes configuradas antes de ejecutar el benchmark.

> **Notas sobre adaptadores concretos:**
> - **WhatsApp**: el modo self-messaging requiere una cuenta Business con el mismo número como remitente y destinatario — comportamiento válido según la API de Meta. También existe un fallback vía Selenium con sesión persistente para casos sin API Business.
> - **Instagram**: si no tienes IP pública, el adaptador puede levantar un servidor HTTP temporal propio y usar ngrok como fallback automático (requiere el CLI de ngrok disponible).
> - **Telegram**: el modo documento (`sendDocument`) preserva el archivo original al 100%, permitiendo comparación exacta contra el modo foto comprimido (`sendPhoto`).
> - **Nostr**: los tests end-to-end usan relays públicos reales; si un relay está caído, el test se salta con un mensaje informativo en lugar de fallar.

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
- **Análisis comparativo:** `scripts/analyze_detectability.py` compara la imagen original (cover) contra la imagen con mensaje oculto (stego).
- **Benchmark de detectabilidad:** evalúa estadísticamente cuán "invisible" resulta un mensaje oculto.

```bash
python scripts/analyze_detectability.py benchmark cover.png "mensaje" --mode PHANTOM
python scripts/analyze_detectability.py compare cover.png stego.png
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
- **Panel web local:** sin autenticación ni protección CSRF por diseño — pensado exclusivamente para uso en `127.0.0.1` por un único usuario; el `.env` que genera se guarda en texto plano.
- **Auditoría automatizada:** `scripts/run_security_audit.py` ejecuta Bandit (análisis estático) y Safety (dependencias vulnerables) además de los tests de seguridad y fuzzing.

---

## Soporte de video

Permite ocultar mensajes distribuidos a lo largo de los frames de un video, protegidos con FEC (Forward Error Correction) global mediante Reed-Solomon. La recuperación tolera pérdida de frames hasta el límite de redundancia configurado.

```python
from stegstr.video.engine import VideoStegoEngine
from stegstr.stego.engine import StegoMode

vengine = VideoStegoEngine(mode=StegoMode.ARMOR, password="clave")
vengine.embed_video("input.mp4", "mensaje largo...", "output.mp4")
result = vengine.extract_video("output.mp4")
print(result["message"])
```

Características:
- Distribución del payload con cabeceras de secuencia y hash MD5 por fragmento (chunk).
- Reconstrucción tolerante a huecos (gaps) de frames.
- Requiere `opencv-python` (`pip install opencv-python`, incluido en el extra `full`).

> Módulo marcado como 🧪 Experimental — la arquitectura y el FEC global están implementados, pero requiere más validación end-to-end.

---

## GUI interactiva (explorador de modos)

El repositorio incluye un explorador visual de los 5 modos de esteganografía, disponible como página HTML autocontenida:

```bash
# Abrir en el navegador
open stegstr/gui/widget.html
```

(En Linux, usa `xdg-open stegstr/gui/widget.html`; en Windows, simplemente haz doble clic sobre el archivo).

Esto es distinto del [panel web de credenciales](#configuración-de-credenciales-y-gui-local) (`stegstr/gui/web_app.py`), que es un servidor Flask con backend, mientras que `widget.html` es un explorador estático sin lógica de servidor.

---

## Compatibilidad de versiones de payload

El formato interno del payload ha evolucionado entre versiones:

- **v2 (antiguo):** orden de operaciones `encrypt → compress`.
- **v3 (actual):** orden de operaciones `compress → encrypt`.

La extracción (`extract`) es compatible con ambos formatos: puede leer payloads generados por versiones antiguas (v2) además de los nuevos (v3). La API pública no ha sufrido cambios incompatibles (*breaking changes*) entre estas versiones.

---

## Solución de problemas

### Faltan dependencias

```bash
pip install -e ".[all]"
```

Si ves errores al importar un adaptador de red social concreto, comprueba que instalaste el extra `social` (incluye `requests`, `tweepy`, `praw`, `ngrok`).

### `RuntimeError` al hacer el primer `embed()` / `extract()`

El motor cifra siempre, incluso con la contraseña por defecto, por lo que `argon2-cffi` es una dependencia núcleo obligatoria. Si instalaste solo con `pip install -e .` sin extras y sigues viendo este error, confirma que `argon2-cffi` está instalado (`pip show argon2-cffi`).

### El modo PHANTOM falla

Asegúrate de estar usando una versión reciente. Versiones antiguas tenían una semilla RNG fija que rompía el roundtrip (embed → extract); la versión actual deriva la semilla del hash del propio mensaje.

### Errores de validación de delta

Los valores de delta fuera del rango `[0.5, 50.0]` lanzan un `ValueError` en lugar de recortarse (clamp) silenciosamente. Revisa el valor pasado a `--auto-tune` o al parámetro `delta` si construyes el motor programáticamente.

### Protección contra path traversal

El motor rechaza rutas que contengan `..` o que apunten a directorios del sistema. Si tu script falla al leer o escribir un archivo, verifica que la ruta sea relativa y esté dentro del árbol de trabajo esperado.

### Un test de esteganálisis falla de forma intermitente

Los tests comparativos entre PHANTOM y GHOST pueden ser sensibles a la imagen de portada usada como muestra única. Si ves resultados inconsistentes entre ejecuciones, repite la comparación sobre varias imágenes distintas y compara la mediana en lugar de una sola muestra (ver [Resistencia al steganálisis](#resistencia-al-steganálisis)).

### Un adaptador de red social falla al subir/descargar

- Confirma con `python check_credentials.py` que las variables de entorno necesarias están definidas.
- Empieza probando con Discord o Imgur, que son los más simples de configurar, antes de pasar a Instagram/WhatsApp/Twitter.
- Si usas el panel web local, revisa que el servidor siga escuchando en `127.0.0.1` y que el `.env` se haya guardado correctamente.

### Otros problemas

- Ejecuta `python check_env.py` para confirmar que todas las dependencias funcionales están correctamente instaladas.
- Ejecuta `python validate.py` para una validación exhaustiva del motor.
- Para adaptadores de redes sociales, ejecuta `python check_credentials.py` y revisa la tabla de [credenciales necesarias](#plataformas-soportadas-y-credenciales-necesarias).

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

El proyecto usa `black` e `isort`:

```bash
black stegstr/ tests/
isort stegstr/ tests/
```

Antes de enviar un Pull Request, ejecuta también la auditoría de seguridad (`python scripts/run_security_audit.py`) y confirma que el CI (`.github/workflows/ci.yml`, que corre en Python 3.9–3.13) pasaría en tu entorno local.

### Buenas prácticas al añadir tests

Si tu cambio usa `StegoMode.ARMOR`/`FORTRESS`/`HYBRID` o el parámetro `password=`, añade el correspondiente `pytest.importorskip` para las dependencias opcionales relacionadas (`reedsolo`, `argon2-cffi`), de forma que el test se salte de forma clara si la dependencia no está instalada, en lugar de fallar con un error confuso.

---

## Historial de versiones (Changelog)

### Validación en el mundo real y Nostr E2E

**Adaptador de WhatsApp**
- Self-mensajería vía Business API (mismo número remitente/destinatario).
- Polling del estado de entrega (delivered/read).
- Descarga real desde el CDN de WhatsApp usando el `media_id` del mensaje entregado.
- Fallback con Selenium y sesión persistente (`user-data-dir`), con auto-login tras el escaneo inicial del QR.
- Soporte de webhooks para confirmaciones de entrega.

**Adaptador de Instagram**
- Servidor HTTP temporal propio (sin depender de Imgur).
- Detección automática de IP pública con fallback a ngrok.
- Descarga real post-publicación, en cascada: `media_url` de la API Graph → scraping OpenGraph (`og:image`) → oEmbed como último recurso.
- Análisis de compresión: calidad JPEG, bits por píxel, nivel de compresión.

**Adaptador de Telegram**
- Modo dual: `sendPhoto` (comprimido) + `sendDocument` (original preservado).
- Comparación ground-truth entre ambos modos.
- Reintentos con backoff exponencial configurable.
- Tracking de metadatos: tamaño de archivo, ancho, alto, estimación de calidad.

**Cliente Nostr**
- Cola de suscripción por `sub_id` con variables de condición (Condition variables).
- `query_events()` recolecta eventos reales esperando EOSE (en versiones previas devolvía una lista vacía).
- Seguimiento de ACKs: `RelayAck` con `event_id`, `relay`, `accepted`, `message`.
- Deduplicación de eventos entre relays.
- Sincronización histórica: `sync_historical(days_back, batch_size)`.
- Publicación con `wait_for_acks` opcional.

**Validador del mundo real**
- Benchmark de N iteraciones con semilla aleatoria reproducible.
- Test de estrés: múltiples carriers × múltiples mensajes.
- BER real bit a bit (no solo comparación de strings).
- Hash de carrier y de payload para trazabilidad.
- Detección de regresiones frente a una baseline en JSON.
- Reporte agregado: media/desviación estándar de PSNR, BER, duración.
- Combinaciones saltadas por falta de dependencia opcional (por ejemplo `reedsolo`) ahora quedan registradas explícitamente en el reporte (campo `skipped`) en vez de omitirse en silencio.

**Tests**
- `test_query_events_e2e`: publica en un relay real, consulta y verifica.
- `test_ack_tracking`: verifica ACKs tras publicación.
- `test_subscription_dedup`: confirma la deduplicación.
- `test_historical_sync`: sincronización de eventos históricos.
- `test_reproducible_benchmark`: determinismo con semilla fija.
- `test_stress_test_mock`: estrés con múltiples carriers/mensajes.
- `test_regression_detection`: detección de regresiones.
- `test_ber_computation_accuracy`: valida BER=0 / BER>0.
- `test_multiple_adapters`: múltiples plataformas simultáneas.
- Adaptadores mock realistas: JPEG, recorte, redimensionado, doble compresión.
- Auditoría automática de cobertura de `pytest.importorskip` en toda la suite `tests/`, que detectó y corrigió varios tests que usaban modos con dependencias opcionales (`ARMOR`/`FORTRESS`, o el parámetro `password=`) sin el correspondiente skip declarado.

**Scripts**
- `real_world_benchmark.py`: CLI con `--iterations`, `--seed`, `--stress`, `--baseline`, `--csv`.

**Meta**
- `pyproject.toml` actualizado, con `argon2-cffi` añadido a las dependencias núcleo (antes solo estaba en `requirements.txt`, causando `RuntimeError` en instalaciones sin extras) y con el nuevo extra `[all]`.
- `__init__.py` con exports en todos los módulos.

### Correcciones de comunicación con redes sociales (rondas de parcheo)

A lo largo de varias rondas de revisión (incluida una revisión externa) se corrigieron los siguientes problemas, verificados uno por uno contra el código:

- **Adaptador de Instagram:** el servidor HTTP temporal no aplicaba correctamente el directorio de archivos servido (`server.directory` no tenía efecto sobre `SimpleHTTPRequestHandler`), lo que causaba errores 404. Corregido usando `functools.partial` con el directorio correcto.
- **Adaptador de WhatsApp:** faltaba el import de `base64` en el fallback de Selenium, lo que provocaba un `NameError` silenciado por el manejo genérico de excepciones. Corregido añadiendo el import.
- **Adaptador de Discord:** los webhooks devuelven `204 No Content` por defecto (sin cuerpo JSON), lo que hacía fallar la lectura de la URL del adjunto aunque la subida sí funcionase. Corregido forzando `wait=true` en la petición para obtener el cuerpo de respuesta.
- **Dependencias no declaradas:** `tweepy` y `praw` se usaban en el código pero no estaban declaradas en ningún fichero de dependencias, por lo que ninguna combinación de extras las instalaba. Corregido con el nuevo extra `[social]`.
- **Adaptador de Instagram:** fuga de archivos temporales en `get_compression_info()` cuando la descarga o apertura de imagen fallaba — el archivo temporal no se eliminaba en caso de error. Corregido moviendo la limpieza a un bloque `finally`.
- **Adaptador de Twitter/X:** si la plataforma tardaba en indexar la imagen subida, el código devolvía como si fuera la URL de la imagen un enlace a la página del tweet; la descarga "tenía éxito" pero el contenido era HTML, no una imagen, y el fallo real solo se detectaba más tarde con un error confuso. Corregido con reintentos con espera y un fallo explícito si la imagen sigue sin estar disponible.
- **Steganálisis:** un test comparativo entre PHANTOM y GHOST resultó ser inestable (flaky) sobre una única imagen de portada de ruido aleatorio, no un fallo real del algoritmo — la diferencia entre modos vivía en cifras decimales muy pequeñas, del orden del ruido de una sola muestra. Corregido repitiendo el experimento sobre varias imágenes de portada distintas (semilla fija) y comparando la mediana de los resultados.
- **Panel web local:** se añadió un aviso de seguridad permanente y visible en el dashboard (no solo en la página de credenciales) recordando que el `.env` se guarda en texto plano, que no hay autenticación ni CSRF, y que es una herramienta de un solo usuario pensada exclusivamente para `127.0.0.1`.

**Ficheros de configuración de credenciales:**
- `.env.example` — plantilla comentada con todas las variables de credenciales necesarias por adaptador, con enlaces a dónde conseguir cada una.
- `check_credentials.py` — script que indica, plataforma por plataforma, qué variable de entorno falta.
- `stegstr/gui/web_app.py` — panel web local (ver [Configuración de credenciales y GUI local](#configuración-de-credenciales-y-gui-local)).

### Pulido de motor y correcciones de robustez

- **PHANTOM mode**: la semilla del generador aleatorio pasó a derivarse del hash del propio mensaje, en lugar de una semilla fija, evitando roturas de roundtrip (embed → extract).
- **Validación de delta**: los valores fuera de rango pasaron a rechazarse explícitamente con `ValueError`, en lugar de recortarse (clamp) de forma silenciosa.
- **Orden de operaciones del payload**: cambiado a `compress → encrypt` (formato v3), en lugar de `encrypt → compress` (formato v2 anterior). Ver [Compatibilidad de versiones de payload](#compatibilidad-de-versiones-de-payload).
- **Protección contra path traversal**: añadida validación contra rutas con `..` o que apunten a directorios del sistema.
- Tests sincronizados con el comportamiento real del motor tras estos cambios.

### Versión base

- Motor esteganográfico con 5 modos.
- Cifrado AES-256-GCM + Argon2id.
- Simuladores de plataformas v1/v2.
- Cliente Nostr NIP-01/05/94/96/98.
- Interoperabilidad con agentes de IA (AI Agent Operability).
- CLI completo.
- Benchmarks científicos.

> El historial detallado de commits, línea por línea, está disponible en el historial de Git del repositorio.

---

## Licencia

MIT — Open Source. Consulta el archivo `LICENSE` para el texto completo.
