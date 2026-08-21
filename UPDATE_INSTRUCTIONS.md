# Instrucciones de actualización — Stegstr v2.2.0

Este paquete corrige las discrepancias críticas entre el README y el código real,
sincroniza las versiones, añade dependencias faltantes, y marca los placeholders.

## 📦 Contenido del paquete

```
stegstr-v2.2.0-update/
├── README.md                          ← Reescrito completo (CLI real, credenciales, placeholders)
├── pyproject.toml                     ← scipy en base, versión 2.2.0
├── .env.example                       ← Nuevo: variables de entorno documentadas
├── validate.py                        ← Versión 2.2.0
├── apply_patches.py                   ← Script automático de aplicación
├── UPDATE_INSTRUCTIONS.md             ← Este archivo
├── stegstr/
│   ├── stego/engine.py                ← Versión 2.2.0
│   ├── config/wizard.py               ← Credenciales sincronizadas con adaptadores
│   ├── api/
│   │   ├── agent_api.py               ← Versión 2.2.0
│   │   └── server.py                  ← NotImplementedError + @TODO
│   ├── video/engine.py                ← NotImplementedError + @TODO
│   ├── gui/widget.html                ← Aviso de placeholder + versión 2.2.0
│   └── ...
└── scripts/
    └── health_check.py                ← Versión 2.2.0, typer, scipy
```

## ⚡ Método rápido: script automático

```bash
cd tu_repo_stegstr
# Copia el paquete dentro del repo (o descomprime aquí)
cp -r /ruta/a/stegstr-v2.2.0-update/* .

# Aplica todos los cambios automáticamente
python apply_patches.py
```

El script `apply_patches.py`:
1. Sobreescribe los archivos que cambian completamente
2. Hace reemplazos in-place de versión en archivos grandes
3. Verifica que cada cambio se aplicó correctamente

## 🛠️ Método manual (si prefieres control paso a paso)

### Paso 1: Reescribir el README
```bash
cp stegstr-v2.2.0-update/README.md README.md
```

### Paso 2: Corregir dependencias
```bash
cp stegstr-v2.2.0-update/pyproject.toml pyproject.toml
```

### Paso 3: Sincronizar versiones
En los siguientes archivos, busca y reemplaza `v2.1.5` o `2.1.5` por `2.2.0`:
- `stegstr/stego/engine.py` (primera línea del docstring)
- `validate.py` (docstring + print)
- `scripts/health_check.py` (docstring + print + click→typer + añadir scipy)
- `stegstr/api/agent_api.py` (versión FastAPI + endpoint /health)

### Paso 4: Sincronizar wizard de credenciales
```bash
cp stegstr-v2.2.0-update/stegstr/config/wizard.py stegstr/config/wizard.py
```

### Paso 5: Marcar placeholders
```bash
cp stegstr-v2.2.0-update/stegstr/video/engine.py stegstr/video/engine.py
cp stegstr-v2.2.0-update/stegstr/api/server.py stegstr/api/server.py
cp stegstr-v2.2.0-update/stegstr/gui/widget.html stegstr/gui/widget.html
```

### Paso 6: Añadir .env.example
```bash
cp stegstr-v2.2.0-update/.env.example .env.example
```

## 🔧 Post-instalación

### Reinstalar dependencias
```bash
pip install -e ".[all]"
```

Esto instalará `scipy` (ahora obligatorio en base) y cualquier dependencia nueva.

### Verificar que todo funciona
```bash
python validate.py              # 32 tests de integridad
python check_env.py             # Dependencias funcionales
python -m stegstr.cli --help    # CLI con comandos reales
python check_credentials.py     # Estado de credenciales
```

### Probar el wizard
```bash
python -m stegstr.cli config --wizard
python -m stegstr.cli config --list
```

## 📝 Resumen de cambios

| Cambio | Archivos afectados | Impacto |
|--------|-------------------|---------|
| README reescrito | `README.md` | Los usuarios ahora ven los comandos CLI reales |
| scipy en base | `pyproject.toml` | `pip install -e .` ya no deja el motor roto para FORTRESS/ARMOR |
| Versiones unificadas | 6 archivos | Elimina confusión de 2.1.5 vs 2.2 vs 2.2.0 |
| Wizard sincronizado | `stegstr/config/wizard.py` | Las credenciales del wizard ahora coinciden con los adaptadores |
| Placeholders marcados | `video/engine.py`, `api/server.py`, `widget.html` | Usuarios ven `NotImplementedError` en lugar de silencioso fallo |
| .env.example nuevo | `.env.example` | Alternativa al wizard, documentado correctamente |
| health_check actualizado | `scripts/health_check.py` | Verifica typer y scipy |

## ⚠️ Notas importantes

- **No borres el README antiguo** sin haberlo revisado: contiene información técnica valiosa (explicaciones de algoritmos, notas de parches) que el nuevo README mantiene pero reorganiza.
- **Los tests existentes no se modifican**: todos los tests pytest (`tests/test_*.py`) permanecen intactos.
- **Backward compatibility**: el motor sigue soportando payloads v2 y v3. Los cambios son solo de documentación, versiones y dependencias.
- **Si algo falla** tras aplicar los cambios, ejecuta `python validate.py` para identificar qué componente tiene problemas.

## 🐛 Troubleshooting

### "scipy not found" tras reinstalar
```bash
pip install scipy
# o
pip install -e ".[full]"
```

### "typer not found" en health_check
```bash
pip install typer
```

### Placeholders siguen sin levantar error
Asegúrate de haber copiado los archivos del paquete, no solo de haber editado a mano.

### Wizard no reconoce mis credenciales antiguas
El wizard nuevo usa nombres de variables distintos (sincronizados con los adaptadores). Las credenciales guardadas en `~/.config/stegstr/credentials.json` con los nombres antiguos no serán reconocidas. Vuelve a configurar con `python -m stegstr.cli config --wizard`.
