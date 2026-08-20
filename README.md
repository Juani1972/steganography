# Stegstr Next — Steganografía Robusta para Redes Sociales (v2.1.5)

> **Estado: Beta técnica avanzada (v2.1.5)** — Arquitectura funcional y componentes principales implementados. Algunos módulos requieren validación end-to-end en entornos reales antes de considerarse producción.

Cliente de esteganografía con 5 modos de operación, cifrado AES-256-GCM, derivación de clave Argon2id, marcadores de sincronización DCT, ECC Reed-Solomon, simulación experimental de plataformas sociales, CLI con salida JSON, motor heurístico de optimización, y cliente Nostr completo (NIP-01/05/94/96/98).

## ✨ Características principales

- **5 modos**: FORTRESS (máxima robustez), ARMOR (equilibrio), GHOST (máxima capacidad PNG), PHANTOM (LSB Matching anti-detección), HYBRID (auto-selección)
- **Cifrado**: AES-256-GCM + Argon2id (time=3, memory=64MB, parallelism=4)
- **Auto-tune profundo**: búsqueda gruesa → fina → validación → score multi-objetivo (ECC, delta y modo reales)
- **Seguridad**: Límites de payload (10MB/50MB), validación de header, protección contra zip-bombs, límites de iteración en extracción
- **Nostr completo**: NIP-01/05/94/96/98 con verificación de identidad y metadatos enriquecidos
- **Validación exhaustiva**: `validate.py` con 28+ tests de integridad
- **Benchmark científico**: `benchmarks/run_benchmarks.py` con métricas BER, PSNR, SSIM, tiempo, memoria
- **Simulador experimental**: WhatsApp, Instagram, Telegram, Twitter/X, Facebook, Signal, LinkedIn, Reddit

## 🔐 Cifrado

**AES-256-GCM** con autenticación integrada. Clave derivada mediante **Argon2id**:

- Time cost: 3 | Memory cost: 64 MB | Parallelism: 4 | Salt: 16 bytes aleatorios

```bash
python -m stegstr.cli embed cover.png "Mensaje" -o stego.png --password clave
python -m stegstr.cli extract stego.png --password clave
```

## ⚠️ Estado de módulos por área

| Módulo | Estado | Validación |
|--------|--------|------------|
| Motor esteganografía (5 modos) | ✅ Funcional | Tests unitarios + robustez |
| Criptografía (AES-GCM + Argon2id) | ✅ Funcional | Tests de roundtrip |
| Auto-tune | ✅ Funcional | Tests de convergencia |
| Simulador de plataformas v1 | ✅ Funcional | Tests de supervivencia |
| Simulador de plataformas v2 | 🧪 Experimental | Arquitectura implementada |
| Steganálisis (Chi², RS, SPA) | 🧪 Experimental | Tests comparativos PHANTOM vs GHOST en validación |
| Video steganography | 🧪 Experimental | Arquitectura + FEC global implementados |
| Nostr client | 🧪 Experimental | Código completo, no validado en red real |
| CLI | ✅ Funcional | Comandos embed/extract/test/check/analyze |
| Benchmarks | ✅ Funcional | Métricas BER/PSNR/SSIM/tiempo/memoria |

> **Nota sobre simuladores**: Los simuladores de plataformas son aproximaciones basadas en comportamientos documentados públicamente. No garantizan reproducir exactamente el procesamiento real de cada red social.

## 🚀 Instalación

```bash
pip install -e ".[full,nostr,dev]"
```

O con Docker (requiere construcción local):

```bash
docker build -t stegstr:latest .
docker run --rm -v $(pwd):/data stegstr:latest embed /data/cover.png "Hola" -o /data/stego.png
```

## 📖 Uso rápido

```bash
# Verificar entorno
python check_env.py

# Validación exhaustiva (28+ tests)
python validate.py

# Embed con auto-tune
python -m stegstr.cli embed cover.png "Mensaje" -o stego.png --platform instagram --auto-tune

# Extraer
python -m stegstr.cli extract stego.png

# Test de robustez
python -m stegstr.cli test cover.png "Mensaje" --platform whatsapp_standard

# Benchmark científico (básico)
python benchmarks/run_benchmarks.py --output benchmarks/results.json

# Benchmark cross-platform con dataset diverso e intervalos de confianza 95%
python benchmarks/dataset_generator.py --output benchmarks/dataset --count 100
python benchmarks/real_benchmark.py --dataset benchmarks/dataset --output benchmarks/report.json --plots

# Simulador realista v2
python -c "from stegstr.platform.simulator_v2 import RealisticPlatformSimulator; ..."

# Video steganography
python -c "from stegstr.video.engine import VideoStegoEngine; ..."

# Auditoría de seguridad
python scripts/run_security_audit.py
```

## 🧪 Tests

```bash
# Tests unitarios y de robustez
pytest tests/test_robustness.py -v

# Tests de seguridad y fuzzing
pytest tests/test_security.py -v

# Tests de steganálisis (Fase 6)
pytest tests/test_steganalysis.py -v

# Validación exhaustiva (standalone, sin pytest)
python validate.py

# Benchmarks
python benchmarks/run_benchmarks.py --quick

# Cobertura completa
pytest --cov=stegstr --cov-report=html
```

## 🏗️ Estructura

```
stegstr/
├── __init__.py
├── cli.py                    # CLI con Rich + JSON output
├── stego/
│   └── engine.py             # Motor (5 modos + AES-256-GCM + Argon2id + auto-tune)
├── agent/
│   └── optimizer.py          # Optimizador heurístico vectorizado
├── platform/
│   ├── analyzer.py           # Análisis de transformaciones
│   └── simulator.py          # Simulación experimental
└── nostr/
    └── client.py             # Nostr NIP-01/05/94/96/98

benchmarks/
└── run_benchmarks.py         # Benchmark científico (BER, PSNR, SSIM, etc.)

examples/
├── basic_usage.py            # Ejemplos de uso
└── platform_guide.md         # Guía de plataformas

scripts/
└── run_security_audit.py     # Bandit + Safety + security tests

tests/
├── test_robustness.py        # Tests unitarios y de robustez
├── test_security.py          # Tests de seguridad y fuzzing
├── test_integration.py       # Tests end-to-end
├── test_benchmarks.py        # Benchmarks
├── test_fuzzing.py           # Property-based fuzzing
└── test_nostr.py             # Tests Nostr

.github/workflows/
└── ci.yml                    # CI/CD (Python 3.9–3.13, bandit, safety, benchmarks)

validate.py                   # Validación exhaustiva standalone
check_env.py                  # Verificación de dependencias funcionales
Dockerfile                    # Contenedor Docker
pyproject.toml                # Metadatos y dependencias (PEP 621)
```

## 📊 Plataformas (simulación experimental)

| Plataforma | Modo | Max msg | ECC | Notas |
|-----------|------|--------:|----:|-------|
| WhatsApp Standard | FORTRESS | ~150 B | 96 | Resize + QF55 |
| WhatsApp HD | ARMOR | ~2 KB | 48 | QF75 |
| Telegram Photo | ARMOR | ~3 KB | 40 | QF82 |
| Telegram File | GHOST | ~50 KB | 0 | Sin compresión |
| Instagram | FORTRESS | ~150 B | 96 | Crop 1:1 + doble JPEG |
| Twitter/X | ARMOR | ~4 KB | 32 | Límite 5MB |
| Facebook | ARMOR | ~3 KB | 40 | UnsharpMask |
| Signal HD | GHOST | ~50 KB | 16 | QF95 |
| LinkedIn | ARMOR | ~5 KB | 32 | Experimental |
| Reddit | ARMOR | ~10 KB | 24 | Experimental |

> ⚠️ **Aviso**: El simulador es una aproximación experimental. No garantiza reproducir exactamente el procesamiento real de cada plataforma.

## 🌍 Validación en Plataformas Reales (Fase 7) — NUEVO

Prueba automáticamente si tu mensaje sobrevive al procesamiento real de redes sociales:

```bash
# Ver qué plataformas están disponibles
python scripts/real_world_benchmark.py --list

# Benchmark completo
python scripts/real_world_benchmark.py --message "Mensaje secreto" --cover cover.png

# Solo plataformas específicas
python scripts/real_world_benchmark.py --platforms telegram,imgur,discord

# Exportar resultados
python scripts/real_world_benchmark.py --output report.json --csv report.csv
```

### Plataformas soportadas

| Plataforma | API | Credenciales | Dificultad | Compresión |
|-----------|-----|-------------|-----------|-----------|
| Telegram | Bot API | `TELEGRAM_BOT_TOKEN` | ⭐ Fácil | Ligera |
| Imgur | Anonymous | `IMGUR_CLIENT_ID` | ⭐ Fácil | Moderada (proxy JPEG) |
| Discord | Webhook | `DISCORD_WEBHOOK_URL` | ⭐ Fácil | Moderada |
| Reddit | PRAW | `REDDIT_CLIENT_ID`, `SECRET`, `USER`, `PASS` | ⭐⭐ Media | Moderada |
| Instagram | Graph API | `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `META_PAGE_ACCESS_TOKEN` | ⭐⭐⭐ Difícil | Agresiva |
| Twitter/X | API v2 | `TWITTER_BEARER_TOKEN`, `API_KEY`, `API_SECRET`, `ACCESS_TOKEN`, `ACCESS_SECRET` | ⭐⭐⭐⭐ Muy difícil | Muy agresiva |
| WhatsApp/Facebook | Selenium | Login manual | ⭐⭐⭐⭐⭐ Extremo | Variable |

### Métricas reportadas

- **Supervivencia**: ¿el mensaje se recupera intacto?
- **PSNR**: calidad de imagen post-procesamiento
- **BER**: tasa de error de bits
- **Mejor modo por plataforma**: recomendación automática

---

## 🕵️ Resistencia al steganálisis (Fase 6)

- **PHANTOM mode**: LSB Matching (±1) en lugar de LSB Replacement, derrotando el ataque Chi-square
- **Detectores integrados**: Chi-square (χ²), RS Analysis, Sample Pairs Analysis (SPA), entropía LSB
- **Análisis comparativo**: `scripts/analyze_detectability.py` compara cover vs stego
- **Benchmark de detectabilidad**: Evalúa qué tan "invisible" es estadísticamente un mensaje

```bash
python scripts/analyze_detectability.py benchmark cover.png "mensaje" --mode PHANTOM
python scripts/analyze_detectability.py compare cover.png stego.png
```

## 🔒 Seguridad

- **Argon2id**: time=3, memory=64MB, parallelism=4
- **Límites**: Payload 10MB comprimido / 50MB raw / Imágenes 16K×16K
- **Validación**: Header verificado (MAGIC, versión, modo, ECC, payload_len)
- **Zip-bomb protection**: Decompressor con límite de ratio de compresión
- **DoS protection**: Límite de iteraciones en búsqueda de delta (30 max)
- **Nostr**: `secp256k1` obligatorio, sin fallback inseguro

## 🎬 Soporte de video (v2.1.2)

Oculta mensajes distribuidos across frames de video con FEC global (Reed-Solomon). Recuperación tolerant a pérdida de frames hasta el límite de redundancia configurado:

```python
from stegstr.video.engine import VideoStegoEngine
from stegstr.stego.engine import StegoMode

vengine = VideoStegoEngine(mode=StegoMode.ARMOR, password="clave")
vengine.embed_video("input.mp4", "mensaje largo...", "output.mp4")
result = vengine.extract_video("output.mp4")
print(result["message"])
```

- Distribución de payload con headers de secuencia y hash MD5 por chunk
- Reconstrucción tolerant a gaps de frames
- Requiere: `pip install opencv-python`

## 🖥️ GUI Interactiva

Explorador visual de modos incluido en `stegstr/gui/widget.html`:

```bash
# Abrir en navegador
open stegstr/gui/widget.html
```

## 📄 Licencia

MIT — Open Source
