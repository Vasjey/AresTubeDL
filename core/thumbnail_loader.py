"""
core/thumbnail_loader.py

Descarga y decodifica miniaturas de YouTube (JPEG/WebP) usando Pillow,
porque tkinter (PhotoImage nativo) solo soporta GIF/PGM/PPM/PNG y no
puede abrir JPEG ni WebP por si solo.

IMPORTANTE sobre threads: tkinter NO es thread-safe. Esta funcion hace
la parte pesada (descarga por red + decodificacion con Pillow) y
devuelve un objeto PIL.Image.Image, que es datos puros y SI se puede
crear en un hilo de fondo. La conversion final a ImageTk.PhotoImage
(que si necesita el hilo principal de tkinter) debe hacerla quien
llama a esta funcion, dentro de un root.after(...).
"""

import io
import logging
from typing import Optional

import requests
from PIL import Image, ImageOps

logger = logging.getLogger("thumbnail_loader")

TIMEOUT_SEGUNDOS = 6


def descargar_miniatura_pil(url: str, ancho: int = 56, alto: int = 42) -> Optional[Image.Image]:
    """
    Descarga la miniatura y la devuelve como imagen PIL ya ajustada al
    tamaño (ancho x alto) SIN deformarla: se usa ImageOps.contain, que
    respeta la relacion de aspecto real (las miniaturas de YouTube son
    16:9) y solo reduce el tamaño hasta que quepa dentro del recuadro,
    sin estirar ni aplastar la imagen en ningun eje.

    El resultado puede terminar mas chico que (ancho, alto) en alguno
    de los dos ejes (por ejemplo, alto x (alto*16/9) en vez de llenar
    todo el recuadro) - eso es intencional para no deformar la imagen.
    Quien la muestre en la UI debe centrarla en un contenedor de tamaño
    fijo, no forzar el label a ese ancho/alto.

    Devuelve None si falla (sin miniatura, red caida, formato invalido),
    sin lanzar excepcion: la miniatura es decorativa, nunca debe romper
    la busqueda ni la reproduccion.
    """
    if not url:
        return None

    try:
        respuesta = requests.get(url, timeout=TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
        imagen = Image.open(io.BytesIO(respuesta.content))
        imagen = imagen.convert("RGB")
        # ImageOps.contain: redimensiona preservando el ratio real de
        # la imagen (no estira/aplasta), a diferencia de .resize() que
        # fuerza exactamente (ancho, alto) y deforma la miniatura si el
        # ratio original no coincide con el del recuadro.
        imagen = ImageOps.contain(imagen, (ancho, alto), method=Image.LANCZOS)
        return imagen
    except Exception as exc:  # noqa: BLE001
        logger.info("No se pudo cargar miniatura (%s): %s", url, exc)
        return None
