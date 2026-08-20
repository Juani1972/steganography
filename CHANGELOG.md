# Changelog

## v2.2.0 — Real-World Validation & Nostr E2E (2026-08-16)

### WhatsApp Adapter (3/10 → 7/10)
- Self-messaging vía Business API (mismo número remitente/destinatario)
- Polling de delivery status (delivered/read)
- Download real desde WhatsApp CDN usando media_id del mensaje entregado
- Selenium fallback con sesión persistente (user-data-dir)
- Webhook support para confirmaciones de entrega

### Instagram Adapter (4.5/10 → 7/10)
- Servidor HTTP temporal propio (sin dependencia de Imgur)
- Detección automática de IP pública + ngrok fallback
- Descarga post-publish real: media_url → OpenGraph → oEmbed
- Análisis de compresión: JPEG quality, bits-per-pixel, nivel

### Telegram Adapter (5.5/10 → 7.5/10)
- Dual-mode: sendPhoto (comprimido) + sendDocument (original)
- Ground truth comparison entre ambos modos
- Retry con backoff exponencial configurable
- Tracking de metadatos: file_size, width, height, quality estimate

### Nostr Client (7.5/10 → 9/10)
- Cola de suscripción por sub_id con Condition variables
- query_events() recolecta eventos reales esperando EOSE
- ACK tracking: RelayAck con event_id, relay, accepted, message
- Deduplicación de eventos entre relays
- Sincronización histórica: sync_historical(days_back, batch_size)
- Publish con wait_for_acks opcional

### Real-World Validator (5/10 → 7.5/10)
- Benchmark N-iteration con semilla aleatoria (reproducible)
- Stress test: múltiples carriers × múltiples mensajes
- BER real bit-a-bit (no solo string match)
- Carrier hash + payload hash para trazabilidad
- Detección de regresiones vs baseline JSON
- Reporte agregado: mean/std PSNR, BER, duración

### Tests (5/10 → 7.5/10)
- test_query_events_e2e: publica en relay real, consulta, verifica
- test_ack_tracking: verifica ACKs post-publicación
- test_subscription_dedup: confirma deduplicación
- test_historical_sync: sincronización de eventos históricos
- test_reproducible_benchmark: determinismo con seed
- test_stress_test_mock: stress con múltiples carriers/messages
- test_regression_detection: detección de regresiones
- test_ber_computation_accuracy: valida BER=0/BER>0
- Mock adapters realistas: JPEG, crop, resize, double-compression

### Scripts
- real_world_benchmark.py: CLI con --iterations, --seed, --stress, --baseline, --csv

### Meta
- Versión bump: 2.1.5 → 2.2.0
- pyproject.toml actualizado
- __init__.py con exports en todos los módulos
- CONTEST_SUBMISSION.md con tabla comparativa

## v2.1.5 — Previous stable
- Motor esteganográfico con 5 modos
- Cifrado AES-256-GCM + Argon2id
- Simuladores de plataformas v1/v2
- Nostr client NIP-01/05/94/96/98
- AI Agent Operability
- CLI completo
- Benchmarks científicos
