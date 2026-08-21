# Patch Notes v2.2.0

Fecha: 2026-08-21

## 🔴 Correcciones críticas

### 1. NostrAdapter no exportado (CRÍTICO)
- **Problema:** `widget_server.py` importaba `NostrAdapter` desde `adapters/__init__.py`, pero este adaptador no existía. El `try/except` capturaba el `ImportError` y ponía `HAS_ADAPTERS = False`, desactivando **todos** los adaptadores de la GUI.
- **Solución:** Creado `nostr_adapter.py` como bridge entre `NostrClient` y la interfaz de adaptadores de plataforma. Añadido a `adapters/__init__.py`.

### 2. Instagram: inconsistencia GUI/backend (CRÍTICO)
- **Problema:** La GUI pedía `username`/`password`, pero `InstagramAdapter` esperaba `account_id`/`access_token` (Graph API). El servidor creaba `InstagramAdapter(username=..., password=...)` lanzando `TypeError`.
- **Solución:**
  - GUI: campos cambiados a **Business Account ID** y **Meta Page Access Token**.
  - Servidor: constructor corregido a `InstagramAdapter(account_id=..., access_token=...)`.

### 3. WhatsApp: inconsistencia GUI/backend (CRÍTICO)
- **Problema:** La GUI pedía `API Key`/`Phone Number`, pero `WhatsAppAdapter` esperaba `phone_id`/`access_token`/`recipient_phone` (Business API). El servidor creaba `WhatsAppAdapter(api_key=..., phone_number=...)` lanzando `TypeError`.
- **Solución:**
  - GUI: campos cambiados a **Business Phone ID**, **Access Token** y **Recipient Phone**.
  - Servidor: constructor corregido a `WhatsAppAdapter(phone_id=..., access_token=..., recipient_phone=...)`.

### 4. Modos de estego no existentes (CRÍTICO)
- **Problema:** La GUI ofrecía `STANDARD` y `AGGRESSIVE`, pero `StegoMode` solo define `FORTRESS`, `ARMOR`, `GHOST`, `PHANTOM`, `HYBRID`. Seleccionarlos lanzaba `KeyError`.
- **Solución:** Eliminados `STANDARD` y `AGGRESSIVE` de todos los `<select>` de la GUI.

## 🟠 Mejoras importantes

### 5. Validación E2E ahora compara mensaje original
- **Problema:** El endpoint `/publish_validate` consideraba éxito si se extraía **cualquier texto no vacío**, sin verificar que coincidiera con el mensaje original.
- **Solución:**
  - El frontend ahora envía `original_message` en el FormData de validación E2E.
  - El backend compara `extracted_message == original_message` y devuelve `message_match`.
  - `success` ahora depende de `message_match`, no solo de `has_message`.

### 6. Caption ahora se pasa al adaptador
- **Problema:** El campo `caption` se recibía en `/publish` pero nunca se pasaba al adaptador.
- **Solución:** Se intenta llamar `upload_with_caption()` si el adaptador lo soporta; de lo contrario, fallback a `upload()`.

### 7. Seguridad de la API endurecida
- **Problema:** CORS permitía `origins: "*"` en todos los endpoints. Sin autenticación ni rate limiting.
- **Solución:**
  - CORS restringido a `http://127.0.0.1:8080` y `http://localhost:8080`.
  - Añadido rate limiting básico: máximo 60 peticiones/minuto por IP.
  - Añadido límite de tamaño de archivo: 20MB (`MAX_CONTENT_LENGTH`).
  - El servidor solo escucha en `127.0.0.1` (no `0.0.0.0`).

### 8. Diferenciación visual: API real vs simulación
- **Problema:** La GUI no distinguía entre plataformas con adaptador real y plataformas solo de simulación.
- **Solución:**
  - En la pestaña **Publicar**, las plataformas se agrupan en `🟢 API real` y `🟡 Solo simulación`.
  - En la pestaña **Configurar**, se añaden badges `Graph API` y `Business API` para Instagram y WhatsApp.
  - Se añaden badges de estado `🟢 API real` / `🟡 Simulación` en la cabecera de la pestaña Publicar.

## 🟡 Mejoras menores

### 9. Dependencias sincronizadas
- Añadido `flask-cors>=4.0.0` a `pyproject.toml` y `requirements.txt`.
- Eliminadas dependencias de desarrollo desalineadas (`flake8`, `pylint`, `isort`) de `requirements.txt`.
- Añadidas dependencias de Nostr (`pynacl`, `bech32`, `qrcode`) a ambos archivos.
- `reedsolo`, `opencv-python`, `scikit-image` ahora están en `dependencies` principales de `pyproject.toml`.

### 10. Documentación del parche
- Añadido este archivo `PATCH_NOTES_v2.2.0.md` con el detalle completo de cambios.

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `stegstr/platform/adapters/__init__.py` | Añadido `NostrAdapter` al `__all__` |
| `stegstr/platform/adapters/nostr_adapter.py` | **NUEVO** — Bridge NostrClient ↔ pipeline |
| `stegstr/gui/widget_server.py` | Correcciones críticas + seguridad + validación E2E |
| `stegstr/gui/widget.html` | Campos corregidos + modos + badges + E2E |
| `pyproject.toml` | Dependencias sincronizadas |
| `requirements.txt` | Dependencias sincronizadas |
| `PATCH_NOTES_v2.2.0.md` | **NUEVO** — Este archivo |

## Cómo aplicar

1. Descomprime el ZIP sobre tu repositorio (sobrescribirá los archivos existentes).
2. Instala dependencias faltantes: `pip install flask-cors secp256k1`
3. Reinicia el servidor: `python -m stegstr.gui.widget_server`
4. Abre `http://127.0.0.1:8080` en tu navegador.

## Estado post-parche

| Área | Estado anterior | Estado post-parche |
|------|-----------------|-------------------|
| Motor de esteganografía | 9/10 | 9/10 |
| Arquitectura general | 8.5/10 | 8.5/10 |
| GUI / UX | 8/10 | 8.5/10 |
| API/servidor GUI | 7/10 | 8/10 |
| Integración con redes sociales | 5.5/10 | 7.5/10 |
| Consistencia frontend/backend | 5.5/10 | 8.5/10 |
| Seguridad de la GUI | 5/10 | 7/10 |
| Documentación | 9/10 | 9/10 |
| Tests | 8/10 | 8/10 |
| **Estado global** | **~7.5/10** | **~8.5/10** |
