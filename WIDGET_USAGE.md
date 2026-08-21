# Guía de uso — Stegstr Widget v2.2.0

## ¿Qué es?

El widget es una **interfaz visual moderna** (SPA) que te permite usar todo el motor de esteganografía de Stegstr desde el navegador, sin escribir comandos de terminal.

## Características

| Feature | Descripción |
|---------|-------------|
| 🎨 **5 modos visuales** | Cards interactivas con iconos y descripciones de FORTRESS, ARMOR, GHOST, PHANTOM, HYBRID |
| 📁 **Drag & Drop** | Arrastra imágenes directamente al navegador |
| 📊 **Métricas en tiempo real** | PSNR, SSIM, capacidad, delta, ECC, tiempo de procesamiento |
| 🔍 **Análisis de detectabilidad** | Compara cover vs stego con Chi², RS, SPA |
| ⚡ **Benchmark integrado** | Compara los 5 modos en la misma imagen |
| 🧪 **Simulador de plataformas** | Predice si tu mensaje sobrevivirá antes de publicar |
| 🌙 **Tema oscuro** | Diseño moderno, responsive (móvil + escritorio) |
| 🔌 **Detección de backend** | Si no hay servidor, muestra demo offline |

## Requisitos

```bash
pip install -e ".[social]"
# o mínimo:
pip install flask flask-cors pillow numpy scipy cryptography argon2-cffi reedsolo
```

## Iniciar

### Opción A: Servidor dedicado del widget (recomendado)

```bash
python -m stegstr.gui.widget_server
# Servidor en http://127.0.0.1:8080
```

Ventajas:
- Más ligero que el panel web completo
- Endpoints REST optimizados para el widget
- CORS habilitado por defecto

### Opción B: Panel web existente

```bash
python -m stegstr.gui.web_app
# Widget disponible en http://127.0.0.1:8080/widget.html
# (el panel principal sigue en http://127.0.0.1:8080/)
```

## Uso paso a paso

### 1. Ocultar un mensaje (Embed)

1. Arrastra una imagen PNG/JPEG a la zona de "Imagen de portada"
2. Selecciona el modo:
   - **HYBRID** → Auto-selección según plataforma (recomendado)
   - **FORTRESS** → Máxima robustez (WhatsApp, Instagram)
   - **ARMOR** → Equilibrio (Telegram, Twitter)
   - **GHOST** → Máxima capacidad (archivos sin pérdida)
   - **PHANTOM** → Anti-detección (resiste análisis estadístico)
3. (Opcional) Selecciona la plataforma de destino
4. Ajusta delta y ECC, o activa "Auto-tune"
5. Escribe el mensaje secreto
6. (Recomendado) Añade contraseña para cifrado AES-256-GCM
7. Pulsa "Ocultar mensaje"
8. Descarga la imagen stego resultante

### 2. Extraer un mensaje (Extract)

1. Ve a la pestaña "Extraer"
2. Arrastra la imagen stego
3. Introduce la contraseña (si se usó al ocultar)
4. (Opcional) Forzar modo si la auto-detección falla
5. Pulsa "Extraer mensaje"

### 3. Analizar detectabilidad (Analyze)

1. Ve a la pestaña "Analizar"
2. Carga la imagen original (cover) y la sospechosa (stego)
3. Pulsa "Analizar"
4. Revisa las métricas:
   - **Chi² p-value** → cercano a 1 = poco detectable
   - **RS rate** → cercano a 0 = poco detectable
   - **SPA rate** → cercano a 0 = poco detectable
   - **Score combinado** → menor = mejor

### 4. Calcular capacidad (Capacity)

1. Ve a la pestaña "Capacidad"
2. Carga una imagen
3. Selecciona modo y plataforma
4. Pulsa "Calcular capacidad"
5. Verás capacidad útil, bruta y overhead

### 5. Benchmark (Benchmark)

1. Ve a la pestaña "Benchmark"
2. Carga una imagen y escribe un mensaje de prueba
3. Pulsa "Ejecutar benchmark"
4. Compara los 5 modos en tabla:
   - Capacidad
   - Tiempo de procesamiento
   - PSNR (calidad visual)
   - Estado de extracción

## Arquitectura

```
┌─────────────────┐     HTTP/JSON      ┌─────────────────┐
│  Navegador      │ ◄────────────────► │  Flask Backend  │
│  (widget.html)  │                    │  (widget_server)│
│  SPA vanilla JS │                    │                 │
└─────────────────┘                    │  ┌───────────┐  │
                                       │  │  Motor    │  │
                                       │  │  Stego    │  │
                                       │  │  (Python) │  │
                                       │  └───────────┘  │
                                       └─────────────────┘
```

**Importante:** El motor de esteganografía (numpy, scipy, PIL, cryptography, argon2) corre en el servidor Python. El navegador solo muestra la interfaz y envía/recibe datos. No hay procesamiento de imágenes en JavaScript.

## Endpoints REST

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `GET /` | GET | Sirve widget.html |
| `GET /health` | GET | Estado del backend |
| `POST /embed` | POST | Ocultar mensaje |
| `POST /extract` | POST | Extraer mensaje |
| `POST /capacity` | POST | Calcular capacidad |
| `POST /analyze` | POST | Análisis de detectabilidad |
| `POST /simulate` | POST | Simular plataforma |
| `POST /benchmark` | POST | Benchmark por modo |
| `POST /optimize` | POST | Auto-tune |

## Solución de problemas

### "Sin conexión" en la esquina superior
El widget detecta automáticamente si el backend está corriendo. Si ves "Sin conexión":
```bash
# Asegúrate de que el servidor está corriendo
python -m stegstr.gui.widget_server
```

### CORS error en consola del navegador
El widget_server.py tiene CORS habilitado por defecto. Si usas web_app.py en lugar de widget_server.py, asegúrate de que sirva el widget desde el mismo origen (mismo puerto).

### Las imágenes no se previsualizan
Asegúrate de que el archivo sea PNG o JPEG y que no exceda 16.384×16.384 píxeles.

### "Backend no disponible" al ejecutar una acción
El backend Flask debe estar corriendo en `127.0.0.1:8080`. El widget no funciona sin él.

## Personalización

El widget es un archivo HTML/CSS/JS vanilla. Puedes editar `stegstr/gui/widget.html` directamente:
- Cambiar colores: modifica las variables CSS `--accent`, `--bg`, etc.
- Añadir endpoints: edita `widget_server.py` y el objeto `API` en el JS
- Cambiar el puerto: edita `API_BASE` en el JS y el `app.run()` en el servidor
