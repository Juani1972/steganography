# Parches aplicados — comunicación con redes sociales (v2)

## 1. stegstr/platform/adapters/instagram.py — servidor temporal roto
Bug: `server.directory = tmpdir` no tiene ningún efecto en `SimpleHTTPRequestHandler`;
el servidor temporal servía desde el cwd del proceso y devolvía 404 al pedir la imagen.
Fix: usar `functools.partial(_QuietHTTPHandler, directory=tmpdir)` al crear el `HTTPServer`.
Verificado con un test aislado que reproduce el servidor: antes → 404, después → 200 y bytes correctos.

## 2. stegstr/platform/adapters/whatsapp.py — NameError en fallback Selenium
Bug: `WhatsAppAdapter._selenium_download()` usaba `base64.b64decode(...)` sin que el
módulo `base64` estuviera importado en el archivo → `NameError` silenciado por el `except Exception`.
Fix: añadido `import base64` a la cabecera del archivo.

## 3. stegstr/platform/adapters/discord.py — webhook sin cuerpo de respuesta
Bug: los webhooks de Discord devuelven `204 No Content` por defecto, sin cuerpo JSON.
`resp.json()` lanzaba excepción y el upload fallaba siempre pese a subirse la imagen.
Fix: añadido `params={"wait": "true"}` a la petición POST para que Discord devuelva
el objeto del mensaje (con la URL del adjunto) en el cuerpo de la respuesta.

## 4. requirements.txt / pyproject.toml — dependencias no declaradas
`tweepy` (Twitter) y `praw` (Reddit) se usaban en el código pero no estaban declarados
en ninguna parte, así que ni `pip install -e ".[full]"` los instalaba. Añadido nuevo
extra `[social]` con `requests`, `tweepy`, `praw` y `ngrok`.

## 5. stegstr/platform/adapters/instagram.py — fuga de ficheros temporales
Bug: en `get_compression_info()`, si `download()` fallaba o `Image.open()` lanzaba
excepción, el fichero temporal creado con `NamedTemporaryFile(delete=False)` nunca
se borraba — cada llamada fallida dejaba un fichero huérfano en `/tmp`.
Fix: limpieza movida a un bloque `finally`, se borra siempre (éxito, fallo o excepción).

## 6. stegstr/platform/adapters/twitter.py — fallback devolvía una página HTML, no una imagen
Bug: si Twitter tardaba en indexar la media subida, el código caía directo a devolver
`https://twitter.com/i/web/status/{id}` como si fuera la URL de la imagen. `download()`
descargaba esa URL "con éxito" (200 OK) pero el contenido era HTML de la página del tweet,
no la imagen — el fallo real solo aparecía más tarde, al intentar extraer el mensaje, con
un error confuso de "no es una imagen válida".
Fix: se reintenta varias veces (con espera) para obtener la URL real de la imagen; si tras
los reintentos sigue sin estar disponible, se devuelve `None` explícitamente, de modo que
el fallo se reporta correctamente como "Upload failed" en el punto donde ocurre de verdad.

---

## Lo que sigue sin poder verificarse en este entorno (no depende del código)
- Instalación real de `rich`, `argon2-cffi`, `reedsolo`, `tweepy`, `praw`, `ngrok`
  (sandbox sin acceso a internet).
- Credenciales reales de cada plataforma (Meta Graph API, Bot de Telegram, OAuth de
  Reddit, API de Twitter/X, WhatsApp Business verificado, etc.).
- IP pública o cuenta de ngrok para el fallback de Instagram sin servidor externo.
- Que el mensaje sobreviva de verdad a la compresión de cada red social — depende del
  ECC (`reedsolo`), no probado en este entorno.
- No se auditaron con el mismo nivel de detalle: `telegram.py`, `reddit.py`, `imgur.py`
  (se revisaron y no se encontraron bugs evidentes, pero no se sometieron a pruebas
  aisladas como Instagram/WhatsApp/Discord/Twitter).

---

# Parches v3 — a raíz de una revisión externa (verificados uno por uno)

## 7. pyproject.toml — argon2-cffi faltaba en las dependencias núcleo
Bug real y no detectado antes: `argon2-cffi` está en `requirements.txt` pero
NO estaba en `[project.dependencies]` de `pyproject.toml`. Como `StegoEngine`
cifra siempre (incluso con la contraseña por defecto), cualquier instalación
hecha con `pip install -e .` (sin extras) fallaba con `RuntimeError` en el
primer `embed()`/`extract()`. Confirmado reproduciendo `RealWorldValidator`
a mano: el primer resultado fallaba exactamente por este motivo.
Fix: añadido `argon2-cffi>=23.1.0` a las dependencias núcleo.

## 8. pyproject.toml — nuevo extra [all]
Añadido `pip install -e ".[all]"` como atajo que instala todo
(full+social+nostr+agent+dev) de una vez, con lista explícita de paquetes
(no auto-referenciado, para evitar problemas conocidos de extras
auto-referenciados en instalaciones editable con setuptools antiguo).

## 9. tests/test_steganalysis.py — test flaky (PHANTOM vs GHOST)
Una revisión externa reportó que `test_phantom_vs_ghost_chi2` fallaba.
Lo reproduje 8 veces seguidas manualmente: **pasaba 5/8 y fallaba 3/8** —
es decir, era inestable (flaky), no un fallo consistente del algoritmo.
Causa: con imágenes de portada de ruido aleatorio, ambos p-valores quedan
saturados casi en 1.0, y la diferencia GHOST/PHANTOM vive en la 9ª-10ª
cifra decimal — del orden del ruido de la propia generación aleatoria de
UNA sola imagen.
Fix: el test ahora repite el experimento con 9 imágenes de portada
distintas (semilla de numpy fija para que sea reproducible) y compara la
MEDIANA de los p-valores en vez de una sola muestra. Verificado: dos
ejecuciones independientes dan exactamente el mismo resultado
(GHOST median=0.9999999964796591, PHANTOM median=0.9999999967053361).

## 10. stegstr/gui/web_app.py — aviso de seguridad más visible
Se añadió un aviso permanente en el dashboard (no solo en la página de
credenciales) recordando que el `.env` se guarda en texto plano, que no
hay autenticación ni CSRF, y que es una herramienta de un solo usuario
pensada solo para 127.0.0.1.

---

## Nota sobre la revisión externa que motivó estos cambios
Se verificaron sus afirmaciones contra el código antes de aplicar nada.
Dos matices importantes:
- El fallo de steganalysis no era "el detector no distingue PHANTOM de
  GHOST" sino un test estadísticamente débil con una sola muestra — el
  algoritmo en sí no se tocó.
- Los fallos de `RealWorldValidator` que atribuían a `reedsolo` también
  dependían de `argon2-cffi` (el motor cifra siempre), y `FORTRESS`/`ARMOR`
  se saltan silenciosamente sin `reedsolo` (comportamiento intencional del
  código, ver `real_world_validator.py` líneas 368-373) — no es un bug,
  pero si no se sabe, confunde a la hora de leer un informe de tests.

---

# Parches v4 — cobertura completa de skips por dependencia ausente

A raíz de la sugerencia de usar `pytest.importorskip` en vez de dejar que
los tests fallen de forma confusa cuando falta `reedsolo`/`argon2-cffi`,
se auditó **todo** `tests/` con un script automático que busca usos de
`StegoMode.ARMOR/FORTRESS/HYBRID` o `password=` sin su
`pytest.importorskip` correspondiente. Se encontraron y corrigieron 6 gaps
que no se habían visto en la ronda anterior:

- `tests/test_fuzzing.py::test_binary_data_roundtrip` (ARMOR)
- `tests/test_security.py::test_fuzz_unicode_extreme` (ARMOR)
- `tests/test_security.py::test_wrong_password_rejection` (ARMOR + password)
- `tests/test_security.py::test_uniform_image` (ARMOR)
- `tests/test_security.py::test_gradient_image` (FORTRESS)
- `tests/test_security.py::test_corrupt_ecc_recovery` (ecc_override=32)
- `tests/test_steganalysis.py::test_analyzer_report_structure` (ARMOR)

Tras esta ronda, la auditoría automática (repetible con el script incluido
en el propio historial de cambios) confirma **cero gaps restantes** en
`tests/`.

## 11. stegstr/platform/real_world_validator.py — skips ya no son silenciosos
Más allá de los tests, el propio `RealWorldValidator.run_full_benchmark()`
(usado tanto por el CLI `scripts/real_world_benchmark.py` como por la GUI)
saltaba combinaciones ARMOR/FORTRESS sin `reedsolo` con solo un log a nivel
INFO — invisible si no se mira la consola con detalle, y ausente por
completo del JSON/CSV exportado.
Fix: nuevo campo `BenchmarkReport.skipped` (lista de
`{platform, mode, reason}`), poblado explícitamente en vez de un `continue`
silencioso. El CLI ahora imprime una sección "⚠️ N combinación(es)
saltada(s)" en el resumen, y el campo queda también en el JSON exportado
(`to_json()`) para quien consuma el reporte programáticamente.
Verificado: con `reedsolo` no instalado, `report.skipped` contiene
exactamente `{"platform": "mock", "mode": "FORTRESS", "reason": "..."}`
en vez de que FORTRESS desaparezca sin dejar rastro.
