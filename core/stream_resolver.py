"""
core/stream_resolver.py

Resuelve, a partir de una URL de YouTube, una URL de streaming DIRECTA
que VLC puede reproducir sin descargar el archivo completo primero.

Plan D: migrado de yt-dlp a pytubefix (libreria Python pura,
compatible con Python 3.8, sin binarios ni subprocesos externos).

  - Audio: yt.streams.get_audio_only().url
  - Video: yt.streams.get_highest_resolution().url (el mejor formato
    PROGRESIVO: video+audio en un solo archivo - lo unico que VLC
    puede reproducir en vivo desde una sola URL sin mezclar streams).

pytubefix usa por defecto el cliente "ANDROID_VR" internamente para
evitar bloqueos/PoToken de YouTube; no hace falta configurar nada
adicional para eso.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from pytubefix import YouTube
from pytubefix.exceptions import PytubeFixError

logger = logging.getLogger("stream_resolver")


class StreamResolveError(Exception):
    """Error amigable para mostrar en texto grande en la UI."""
    pass


@dataclass
class ResolvedStream:
    direct_url: str
    title: str
    duration_seconds: Optional[int]


def _cargar_video(webpage_url: str) -> YouTube:
    try:
        return YouTube(webpage_url)
    except PytubeFixError as exc:
        logger.warning("Error cargando video: %s", exc)
        raise StreamResolveError(f"No se pudo cargar el video: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado cargando video: %s", exc)
        raise StreamResolveError("Ocurrio un error al preparar la reproduccion.") from exc


def resolve_audio_stream(webpage_url: str) -> ResolvedStream:
    """Devuelve la URL directa de la mejor pista de solo audio."""
    yt = _cargar_video(webpage_url)

    try:
        stream = yt.streams.get_audio_only()
    except PytubeFixError as exc:
        raise StreamResolveError(f"No se pudo obtener el audio: {exc}") from exc

    if not stream:
        raise StreamResolveError("Este video no tiene ninguna pista de audio disponible.")

    return ResolvedStream(
        direct_url=stream.url,
        title=yt.title or "(sin titulo)",
        duration_seconds=yt.length,
    )


def resolve_video_stream(webpage_url: str) -> ResolvedStream:
    """
    Devuelve la URL directa del formato progresivo de mayor resolucion
    disponible (video+audio combinados).
    """
    yt = _cargar_video(webpage_url)

    try:
        stream = yt.streams.get_highest_resolution()
    except PytubeFixError as exc:
        raise StreamResolveError(f"No se pudo obtener el video: {exc}") from exc

    if not stream:
        raise StreamResolveError(
            "Este video no tiene un formato compatible para reproducir en vivo. "
            "Prueba descargarlo en vez de reproducirlo."
        )

    return ResolvedStream(
        direct_url=stream.url,
        title=yt.title or "(sin titulo)",
        duration_seconds=yt.length,
    )
