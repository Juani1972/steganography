# Cambios v2.1.3 → v2.1.4 — Pasada de pulido final

## 🐛 Correcciones

### 1. Dependencias de APIs sociales no declaradas (CRÍTICO)
**Archivo:** `pyproject.toml`

**Problema:** `requests`, `praw` y `tweepy` no estaban declarados como dependencias. Una instalación limpia con `pip install -e ".[full,nostr,dev]"` fallaba al importar cualquier adaptador de plataforma real.

**Solución:** Añadidos grupos opcionales:
- `social`: `requests>=2.31.0`, `praw>=7.7.0`, `tweepy>=4.14.0`
- `browser`: `selenium>=4.15.0`
- `all`: metagrupo que instala todo (`full + social + browser + nostr + dev`)

**Comandos de instalación ahora válidos:**
```bash
# Solo núcleo
pip install -e "."

# Núcleo + procesamiento de imagen
pip install -e ".[full]"

# Núcleo + adaptadores de redes sociales
pip install -e ".[social]"

# Todo incluido (recomendado para validación real)
pip install -e ".[all]"
```

### 2. Test `test_mock_lossless` fallaba (CRÍTICO)
**Archivo:** `tests/test_real_world.py`

**Problema:** `MockAdapter.upload()` devolvía el string literal `"mock_url"`, pero `MockAdapter.download()` intentaba `Image.open("mock_url")`, lo que lanzaba `FileNotFoundError`.

**Solución:** `MockAdapter` ahora mantiene un diccionario interno `_uploaded: {mock_url → real_path}`. `upload()` genera una URL mock única y almacena el mapeo. `download()` resuelve la URL mock al path real antes de abrir la imagen.

```python
self._uploaded = {}  # mock_url -> real_image_path

def upload(self, image_path):
    mock_url = f"mock://{self.name}/{uuid.uuid4().hex}"
    self._uploaded[mock_url] = image_path
    return mock_url

def download(self, url, output_path):
    real_path = self._uploaded.get(url, url)  # resuelve mock o fallback
    img = Image.open(real_path).convert("RGB")
    ...
```

**Resultado:** Todos los tests de `test_real_world.py` pasan ahora.

---

## 📋 Checklist de validación recomendada

Tras aplicar estos cambios:

```bash
# 1. Instalar todo
pip install -e ".[all]"

# 2. Verificar entorno
python check_env.py

# 3. Ejecutar suite completa
pytest tests/ -v --tb=short

# 4. Validar adaptadores disponibles
python scripts/real_world_benchmark.py --list

# 5. Probar al menos una plataforma real (Imgur es la más fácil)
export IMGUR_CLIENT_ID="tu_client_id"
python scripts/real_world_benchmark.py --platforms imgur --message "test"
```

---

## ⚠️ Lo que sigue sin cambiar (y es correcto así)

| Elemento | Estado | Razón |
|----------|--------|-------|
| `SeleniumFallbackAdapter` | ⚠️ No terminado | Es infraestructura base para futuras integraciones. WhatsApp/Facebook/Signal requieren selectores específicos por plataforma. |
| Simuladores v1/v2 | ✅ Sin cambios | Funcionan correctamente como capa de desarrollo. |
| Motor esteganográfico | ✅ Sin cambios | No requería modificaciones. |
| Nostr client | ✅ Sin cambios | Código completo, pendiente de validación en red real. |

---

## 🏷️ Versión

`2.1.3` → `2.1.4`
