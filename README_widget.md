# Stegstr Widget v2.2.0

Explorador visual de esteganografia LSB avanzada con publicacion real a redes sociales.

## Que es

Widget web (SPA) que permite:
- Ocultar mensajes secretos en imagenes PNG/JPEG
- Extraer mensajes de imagenes stego
- Analizar detectabilidad (PSNR, MSE, heatmap)
- Calcular capacidad por modo
- Benchmark comparativo de modos
- Simular procesamiento de plataformas antes de publicar
- Publicar imagenes stego en redes sociales reales (Telegram, Discord, Imgur, etc.)

## Requisitos

- Python 3.10+
- Stegstr instalado (`pip install -e ".[social]"`)
- Navegador moderno (Chrome, Firefox, Edge)

## Instalacion

```bash
git clone https://github.com/Juani1972/steganography.git
cd steganography
pip install -e ".[social]"
```

## Arrancar

```bash
python -m stegstr.gui.widget_server
```

Abre `http://127.0.0.1:8080` en tu navegador.

**Advertencia:** Este servidor esta disenado para ejecutarse UNICAMENTE en localhost. NO lo expongas a Internet.

## Pestañas

### 1. Ocultar (Embed)

1. Arrastra una imagen PNG/JPEG
2. Escribe el mensaje secreto
3. Selecciona modo:
   - **HYBRID**: Auto-seleccion inteligente (recomendado)
   - **FORTRESS**: Maxima robustez (DCT + ECC)
   - **ARMOR**: Equilibrio robustez/capacidad (DCT + ECC)
   - **GHOST**: Maxima capacidad PNG (LSB puro)
   - **PHANTOM**: Anti-deteccion LSB-M
4. Opcional: selecciona plataforma objetivo para auto-tune
5. Pulsa "Ocultar"
6. Descarga la imagen stego o usa "Extraer de esta imagen" para probar

### 2. Extraer (Extract)

1. Sube una imagen stego
2. Selecciona el modo usado al ocultar (o deja "Auto-detectar")
3. Introduce contraseña si aplica
4. Pulsa "Extraer"

**Nota:** Si descargaste la imagen del navegador con "Guardar imagen como...", el navegador puede haberla re-comprimido. Usa siempre el boton "Descargar imagen stego" o "Extraer de esta imagen".

### 3. Analizar (Analyze)

Compara una imagen original (cover) con su version stego:
- Slider visual lado a lado
- Heatmap de diferencias de pixeles
- Metricas: PSNR (dB), MSE, diferencia media/maxima

### 4. Capacidad (Capacity)

Calcula cuantos bytes caben en una imagen segun el modo seleccionado. Muestra:
- Capacidad en bytes y KB
- Grafico comparativo por modo
- Recomendacion del mejor modo segun la capacidad

### 5. Benchmark

Mide rendimiento de cada modo:
- Tiempo de embed/extract
- Roundtrip OK (mensaje se recupera intacto)
- PSNR de calidad
- Grafico comparativo y tabla

**Nota:** FORTRESS/ARMOR usan DCT + ECC. A veces el roundtrip falla con mensajes muy cortos. GHOST/PHANTOM (LSB puro) suelen ser mas fiables.

### 6. Simular (Simulate)

Predice si tu mensaje sobrevivira al procesamiento de una red social:
1. Sube imagen + mensaje
2. Selecciona plataforma (Telegram, Instagram, WhatsApp, etc.)
3. Pulsa "Simular"
4. Resultado: "Sobrevive: Si/No" + lista de transformaciones aplicadas

### 7. Publicar (Publish)

Publica imagenes stego en plataformas reales:
1. Sube imagen stego
2. Selecciona plataforma
3. Introduce credenciales (o configuralas previamente)
4. Pulsa "Publicar" o "Publicar + Validar E2E"

**Credenciales soportadas:**
- Telegram: Bot Token + Chat ID
- Discord: Webhook URL
- Imgur: Client ID
- Reddit: Client ID + Secret + Username + Password
- Twitter/X: API Key + Secret + Access Token + Secret
- Instagram: Business Account ID + Meta Page Access Token
- WhatsApp: Business Phone ID + Access Token + Recipient Phone
- Nostr: Private Key (nsec) + Relay URL

Las credenciales se almacenan solo en RAM y se pierden al cerrar el servidor.

## Atajos de teclado

| Atajo | Pestaña |
|-------|---------|
| Ctrl+1 | Ocultar |
| Ctrl+2 | Extraer |
| Ctrl+3 | Analizar |
| Ctrl+4 | Capacidad |
| Ctrl+5 | Benchmark |
| Ctrl+6 | Simular |
| Ctrl+7 | Publicar |

## Solucion de problemas

### "Backend offline" en el widget
- Verifica que `python -m stegstr.gui.widget_server` esta corriendo
- Comprueba que no hay otro proceso usando el puerto 8080

### "No se encontro mensaje" al extraer
- Usa el mismo modo que al ocultar
- Verifica la contraseña
- No uses "Guardar imagen como..." del navegador (re-comprime). Usa el boton de descarga o "Extraer de esta imagen"
- Prueba con modo GHOST (el mas fiable)

### Analyze falla con "np not defined"
- Asegurate de tener `numpy` instalado: `pip install numpy`
- Verifica que usas la ultima version de `widget_server.py`

### Simulate falla con "float cannot be interpreted as integer"
- Actualiza `stegstr/platform/simulator_v2.py` a la version corregida (v2.1.2+)

## Estructura de archivos

```
stegstr/
├── gui/
│   ├── widget.html          # Frontend SPA (este archivo)
│   ├── widget_server.py     # Backend Flask
│   └── web_app.py           # Version alternativa (streamlit)
├── platform/
│   ├── simulator_v2.py      # Simulador de plataformas
│   └── adapters/            # Adaptadores para publicacion real
└── stego/
    └── engine.py            # Motor de esteganografia
```

## Version

v2.2.0 - Stegstr Widget
