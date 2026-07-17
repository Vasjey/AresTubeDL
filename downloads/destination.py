"""
downloads/destination.py

Decide DONDE se guarda el MP3 descargado:
  - Si hay un pendrive conectado, la UI (Fase 4) debe preguntar en
    texto grande: "¿Guardar en Pendrive o en el Computador?"
  - Si no hay pendrive, se va directo a la carpeta
    "Musica_Descargada" en el Escritorio (sin preguntar nada).

Este modulo NO muestra ningun dialogo (eso es responsabilidad de la
UI en Fase 4); solo entrega la informacion y arma la ruta final.
"""

import os
import logging

import config
from downloads.usb_detector import detectar_primer_pendrive

logger = logging.getLogger("destination")


def hay_pendrive_conectado() -> "str | None":
    """
    Punto de entrada que debe llamar la UI justo antes de iniciar una
    descarga, para decidir si preguntar o no.
    Devuelve la ruta del pendrive (ej "E:\\\\") o None si no hay.
    """
    return detectar_primer_pendrive()


def construir_carpeta_destino(usar_pendrive: bool, ruta_pendrive: "str | None" = None) -> str:
    """
    Devuelve la ruta final de la carpeta de descargas ya creada en
    disco (la crea si no existe).

    usar_pendrive=True  -> guarda dentro de <pendrive>/Musica_Descargada
    usar_pendrive=False -> guarda en el Escritorio/Musica_Descargada
    """
    if usar_pendrive and ruta_pendrive:
        carpeta = os.path.join(ruta_pendrive, config.DOWNLOAD_FOLDER_NAME)
    else:
        carpeta = config.DEFAULT_DOWNLOAD_PATH

    try:
        os.makedirs(carpeta, exist_ok=True)
    except OSError as exc:
        logger.warning(
            "No se pudo crear carpeta en %s (%s); usando Escritorio.",
            carpeta, exc,
        )
        carpeta = config.DEFAULT_DOWNLOAD_PATH
        os.makedirs(carpeta, exist_ok=True)

    return carpeta
