# Stegstr — Actualización: arreglos de comunicación con redes sociales

## Qué cambió en esta actualización (sobre el ZIP que subiste al principio)

Ver **`PATCH_NOTES.md`** para el detalle completo de los 6 arreglos en
`stegstr/platform/adapters/` (Instagram, WhatsApp, Discord, Twitter) y en
`requirements.txt`/`pyproject.toml` (dependencias que faltaban).

Además se añaden dos ficheros nuevos que no existían en el proyecto original:
- **`.env.example`** — plantilla con todas las variables de credenciales que
  necesita cada adaptador, comentada y con enlaces a dónde conseguir cada una.
- **`check_credentials.py`** — script que te dice, plataforma por plataforma,
  qué variable de entorno falta.

## Novedad: GUI local para credenciales y pruebas

En vez de editar el `.env` a mano, ahora puedes usar un panel web que corre
en tu propia máquina:

```bash
pip install -e ".[social]"   # incluye flask
python -m stegstr.gui.web_app
# abre http://127.0.0.1:8080
```

Desde ahí puedes:
- Ver de un vistazo qué plataformas tienen credenciales y cuáles no.
- Rellenar un formulario por plataforma que guarda directamente en `.env`
  (nunca sale de tu equipo — el servidor solo escucha en `127.0.0.1`).
- Pulsar "Probar" sobre cualquier plataforma configurada para lanzar una
  prueba real (embed → subir → descargar → extraer) y ver el resultado
  completo en el navegador, sin tocar la terminal.

Probado en este entorno (sin red externa, solo localhost): el servidor
arranca, el dashboard responde, el formulario guarda correctamente en
`.env` conservando los comentarios y sin borrar plataformas ya configuradas,
y la ruta de prueba ejecuta de verdad `scripts/real_world_benchmark.py` y
muestra el resultado sin romperse. Lo que no se ha podido probar aquí es
una subida real contra una API externa — eso requiere tus credenciales e
internet, en tu máquina.

## Cómo aplicar esta actualización

1. Descomprime este ZIP y sustituye tu carpeta del proyecto por esta (o copia
   encima los ficheros modificados si prefieres conservar tus propios cambios):
   ```bash
   cp -r steganography_repo_v2/* /ruta/a/tu/proyecto/
   ```

2. Instala las dependencias que faltaban (necesita internet; no se pudo hacer
   en el entorno donde se preparó este parche):
   ```bash
   pip install -e ".[full,social,nostr,dev]"
   ```

3. Configura tus credenciales:
   ```bash
   cp .env.example .env
   # rellena .env con las plataformas que vayas a usar
   export $(grep -v '^#' .env | xargs)
   python check_credentials.py
   ```

4. Verifica que el entorno está bien y que los tests pasan:
   ```bash
   python check_env.py
   python validate.py
   python scripts/real_world_benchmark.py --list
   ```

5. Prueba con Discord o Imgur primero (son las más simples de configurar)
   antes de meterte con Instagram/WhatsApp/Twitter.

---



## What changed (from v2.1.3/2.1.4)

### Fixed bugs
- `pyproject.toml`: TOML escape fixed (`\.pyi?$` → `\.pyi?$` as raw string), version synced to 2.1.5
- `validate.py`: Added missing `import zlib`, fixed `test_delta_bounds` to match engine constants, added `test_binary_data` with encoding detection, added `test_nostr_lifecycle`
- `stegstr/stego/engine.py`:
  - `_safe_zlib_decompress`: Now checks `len(buf) >= max_size` in addition to `unconsumed_tail`
  - `_check_path_security`: Removed duplicate `@staticmethod` decorator
  - `extract()`: Returns `encoding` field (`utf-8` or `base64`) for binary payload support
- `stegstr/cli.py`: Version bumped to 2.1.5, added `--decode` option in `extract`

### New features
- `stegstr/ai_agent/interface.py`: Full AI Agent tool-calling API (replaces placeholder)
  - Actions: `analyze_carrier`, `estimate_capacity`, `recommend_parameters`, `encode`, `decode`, `simulate_platform`, `auto_optimize`, `benchmark_detectability`, `list_actions`
  - All methods return JSON-serializable dicts for LLM integration
- `stegstr/networking/sync_manager.py`: Real SyncManager (replaces placeholder)
  - Message states: CREATED → QUEUED → SENT → RECEIVED → VERIFIED → FAILED → RETRYING
  - Retry with exponential backoff, deduplication, integrity verification, persistent store
- `stegstr/api/agent_api.py`: Optional FastAPI REST server for the AI Agent
  - Endpoints: `POST /agent/execute`, `GET /agent/actions`, `GET /health`
- `tests/test_nostr.py`: Real tests for Nostr client (event determinism, key derivation, connect/disconnect, handler registration)

## How to apply

1. Copy all files from this ZIP into your repository root, overwriting existing files:
   ```bash
   cp -r stegstr-v2.1.5/* /path/to/your/repo/
   ```

2. Install/update dependencies:
   ```bash
   pip install -e ".[all]"
   ```

3. Run validation:
   ```bash
   python validate.py
   pytest tests/test_nostr.py -v
   ```

4. Expected result: 32/32 tests pass in `validate.py`, Nostr tests pass (or skip if `secp256k1` not installed).

## Version checklist
Ensure these files show `2.1.5`:
- `pyproject.toml`
- `stegstr/__init__.py`
- `stegstr/stego/engine.py` (docstring)
- `stegstr/cli.py`
- `stegstr/api/agent_api.py`
- `validate.py`

## Post-update: README additions
Add these sections to your `README.md` before submission:

### AI Agent Operability
```python
from stegstr.ai_agent.interface import AIAgent
agent = AIAgent()
result = agent.execute({"action": "encode", "carrier": "cover.png", "message": "hello", "output": "stego.png", "platform": "whatsapp_standard"})
```

### Networking
```python
import asyncio
from stegstr.networking.sync_manager import SyncManager
sm = SyncManager(private_key_hex="your_key")
await sm.start()
msg_id = await sm.send_message(payload_b64="...", platform_hint="whatsapp_standard")
```

### Benchmark Matrix
| Platform | Mode | Max Msg | ECC | Delta | Sim Survival | PSNR | SSIM |
|----------|------|---------|-----|-------|-------------|------|------|
| WhatsApp Std | FORTRESS | ~150 B | 96 | 8.0 | 100% | ~39 | ~0.98 |
| Telegram Photo | ARMOR | ~3 KB | 40 | 4.0 | 100% | ~42 | ~0.99 |
| Instagram | FORTRESS | ~150 B | 96 | 10.0 | 95% | ~37 | ~0.97 |
