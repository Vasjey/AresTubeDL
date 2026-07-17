"""
downloads/mp3_downloader.py

Descarga el mejor audio disponible de un video de YouTube (via
pytubefix) y lo convierte a MP3 REAL usando ffmpeg.

IMPORTANTE - por que se sigue usando ffmpeg con pytubefix:
pytubefix ofrece un parametro `stream.download(mp3=True)`, pero eso
SOLO renombra el archivo descargado (que en realidad viene codificado
en AAC dentro de un .m4a, o en Opus dentro de un .webm) a extension
".mp3" - NO vuelve a codificar el audio. Un archivo asi no es un MP3
de verdad: muchas radios de auto antiguas, que decodifican
estrictamente MPEG-1 Layer III, lo van a rechazar o reproducir mal.
Por eso, igual que en la version basada en yt-dlp, se hace la
conversion real de codec con ffmpeg despues de descargar.

Reporta progreso real a la UI:
    "Descargando... 42%"
    "Convirtiendo a MP3... Por favor espere"
    "Listo: Nombre de la cancion.mp3"

La UI debe llamar a esta funcion SIEMPRE desde un hilo de fondo
(threading), nunca en el hilo principal de tkinter.
"""

import os
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional, Callable

from pytubefix import YouTube
from pytubefix.exceptions import PytubeFixError

import config

logger = logging.getLogger("mp3_downloader")

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class DownloadError(Exception):
    """Error amigable para mostrar en texto grande en la UI."""
    pass


@dataclass
class DownloadResult:
    ruta_archivo_mp3: str
    titulo: str


def _convertir_a_mp3_con_ffmpeg(ruta_origen: str, ruta_destino_mp3: str):
    ffmpeg_exe = config.FFMPEG_PATH or "ffmpeg"
    comando = [
        ffmpeg_exe, "-y", "-i", ruta_origen,
        "-vn", "-ar", "44100", "-ac", "2",
        "-b:a", f"{config.MP3_CALIDAD_KBPS}k",
        ruta_destino_mp3,
    ]
    try:
        resultado = subprocess.run(
            comando, capture_output=True, text=True, timeout=600,
            creationflags=CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise DownloadError(
            "No se encontro ffmpeg. Es necesario para convertir a MP3. "
            "Reinstala la aplicacion o contacta a soporte."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DownloadError("La conversion a MP3 tardo demasiado y se cancelo.") from exc

    if resultado.returncode != 0 or not os.path.isfile(ruta_destino_mp3):
        logger.warning(
            "ffmpeg fallo (code=%s): %s",
            resultado.returncode, (resultado.stderr or "")[-500:],
        )
        raise DownloadError("La conversion a MP3 fallo. Intenta de nuevo.")


def descargar_mp3(
    webpage_url: str,
    destination_folder: str,
    on_status: Optional[Callable[[str], None]] = None,
) -> DownloadResult:
    """
    Descarga el audio con pytubefix y lo convierte a MP3 real con
    ffmpeg. Lanza DownloadError con mensaje en español, listo para
    mostrar en la UI, si algo falla.
    """
    if on_status:
        on_status("Preparando descarga...")

    def hook_progreso(stream, chunk, bytes_restantes):
        try:
            total = stream.filesize
            if total:
                porcentaje = (1 - bytes_restantes / total) * 100
                if on_status:
                    on_status(f"Descargando... {porcentaje:.0f}%")
        except Exception:  # noqa: BLE001
            pass  # el progreso es decorativo, nunca debe romper la descarga

    ruta_temporal = None
    titulo = "cancion"

    try:
        yt = YouTube(webpage_url, on_progress_callback=hook_progreso)
        titulo = yt.title or "cancion"

        stream = yt.streams.get_audio_only()
        if not stream:
            raise DownloadError("Este video no tiene ninguna pista de audio disponible.")

        ruta_temporal = stream.download(output_path=destination_folder)

    except DownloadError:
        raise
    except PytubeFixError as exc:
        logger.warning("Error descargando audio: %s", exc)
        raise DownloadError(f"No se pudo descargar: {exc}") from exc
    except OSError as exc:
        logger.warning("Error de disco descargando audio: %s", exc)
        raise DownloadError(
            "No se pudo guardar el archivo. Verifica que haya espacio "
            "disponible en el destino elegido."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado descargando audio: %s", exc)
        raise DownloadError(
            "Ocurrio un error inesperado al descargar. Intenta de nuevo."
        ) from exc

    if on_status:
        on_status("Convirtiendo a MP3... Por favor espere")

    ruta_mp3 = os.path.splitext(ruta_temporal)[0] + ".mp3"
    try:
        _convertir_a_mp3_con_ffmpeg(ruta_temporal, ruta_mp3)
    finally:
        # Borra el archivo intermedio (m4a/webm), haya funcionado o no
        # la conversion, para no dejar basura a medio convertir.
        try:
            if ruta_temporal and os.path.isfile(ruta_temporal) and ruta_temporal != ruta_mp3:
                os.remove(ruta_temporal)
        except OSError:
            pass

    if on_status:
        on_status(f"Listo: {os.path.basename(ruta_mp3)}")

    return DownloadResult(ruta_archivo_mp3=ruta_mp3, titulo=titulo)
