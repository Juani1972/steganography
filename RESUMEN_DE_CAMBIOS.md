# Resumen de Cambios v2.1.3

## Correcciones críticas

1. **PHANTOM mode**: Seed derivada del hash del mensaje en lugar de seed fija (42)
2. **Validación de delta**: Rechazo estricto con ValueError en lugar de clamping silencioso
3. **Orden de operaciones**: compress → encrypt (v3) en lugar de encrypt → compress (v2)
4. **Path traversal**: Protección contra rutas con `..` y directorios del sistema
5. **Tests sincronizados**: Todos los tests actualizados para reflejar el comportamiento real
6. **Versiones unificadas**: Todas las referencias a 2.1.3

## Compatibilidad

- Extracción compatible con payloads v2 (antiguos) y v3 (nuevos)
- API pública sin cambios breaking
