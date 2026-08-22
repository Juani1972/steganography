"""Video steganography engine placeholder.

@TODO: Implementar distribución de payload en frames, cabeceras de secuencia,
hash MD5 por fragmento, reconstrucción tolerante a huecos, y FEC global.

Este módulo está planificado pero no implementado. Usar levantará
NotImplementedError hasta que se complete el desarrollo.
"""

class VideoStegoEngine:
    """Placeholder for video steganography engine."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "VideoStegoEngine is not yet implemented. "
            "Follow the project for updates or contribute at "
            "https://github.com/Juani1972/steganography"
        )

    def embed_video(self, *args, **kwargs):
        raise NotImplementedError("VideoStegoEngine.embed_video() is not yet implemented.")

    def extract_video(self, *args, **kwargs):
        raise NotImplementedError("VideoStegoEngine.extract_video() is not yet implemented.")
