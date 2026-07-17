"""
updater/pytubefix_updater.py

Actualizacion silenciosa de pytubefix en background, al iniciar la
app (Plan D: reemplaza al antiguo ytdlp_updater.py). pytubefix es una
libreria pura de Python instalada via pip/requirements.txt, asi que
se actualiza igual que cualquier otro paquete:

    python -m pip install -U pytubefix

Corre en un hilo de fondo y nunca debe bloquear ni crashear el
arranque de la UI si falla (sin internet, sin permisos, etc). Vale la
pena mantenerla al dia porque YouTube cambia seguido su forma de
entregar los streams, y pytubefix se actualiza frecuentemente para
seguirle el paso.
"""

import os
import sys
import subprocess
import logging
from typing import Optional, Callable

import config

logger = logging.getLogger("pytubefix_updater")

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def update_pytubefix_silently(
    on_status: Optional[Callable[[str], None]] = None,
):
    """
    Ejecuta 'pip install -U pytubefix' en background. Respeta
    config.YTDLP_AUTO_UPDATE (nombre historico de la bandera; ahora
    controla la actualizacion de pytubefix): si esta en False, no
    hace nada (util para congelar una version conocida-buena).
    """
    if not config.YTDLP_AUTO_UPDATE:
        logger.info("Auto-actualizacion de pytubefix desactivada por config.")
        return

    try:
        if on_status:
            on_status("Actualizando pytubefix... (en segundo plano)")

        resultado = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "pytubefix"],
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=CREATE_NO_WINDOW,
        )
        if resultado.returncode == 0:
            logger.info("pytubefix actualizado correctamente.")
        else:
            logger.warning(
                "pip install -U pytubefix fallo (code=%s): %s",
                resultado.returncode, resultado.stderr,
            )

    except Exception as exc:  # noqa: BLE001 - defensivo a proposito
        logger.warning("Excepcion actualizando pytubefix: %s", exc)
    finally:
        if on_status:
            on_status("")
