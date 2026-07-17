"""
downloads/usb_detector.py

Deteccion simple de pendrive en Windows: busca la PRIMERA letra de
unidad (de A: a Z:) marcada por Windows como "removible" (DRIVE_REMOVABLE).

Segun lo confirmado por el usuario: nunca habra mas de un pendrive
conectado a la vez, asi que basta con devolver el primero encontrado
(no hace falta listar ni elegir entre varios).

Usa ctypes contra la API de Windows directamente (sin dependencias
extra), asi que funciona igual este empaquetado con PyInstaller o no.
En cualquier sistema que no sea Windows, devuelve None sin fallar
(para poder probar el resto de la app en otro entorno de desarrollo).
"""

import sys
import string
import logging

logger = logging.getLogger("usb_detector")

DRIVE_REMOVABLE = 2


def detectar_primer_pendrive() -> "str | None":
    """
    Devuelve la ruta raiz del primer pendrive detectado, ej: "E:\\\\",
    o None si no hay ninguno conectado (o si no es Windows).
    """
    if sys.platform != "win32":
        logger.info("Deteccion de USB solo aplica en Windows.")
        return None

    try:
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()

        for indice, letra in enumerate(string.ascii_uppercase):
            unidad_presente = bitmask & (1 << indice)
            if not unidad_presente:
                continue

            ruta_unidad = f"{letra}:\\"
            tipo_unidad = ctypes.windll.kernel32.GetDriveTypeW(ruta_unidad)

            if tipo_unidad == DRIVE_REMOVABLE:
                logger.info("Pendrive detectado en %s", ruta_unidad)
                return ruta_unidad

        return None

    except Exception as exc:  # noqa: BLE001
        logger.warning("Error detectando USB: %s", exc)
        return None
