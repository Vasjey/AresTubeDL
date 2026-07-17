"""
core/vlc_check.py

python-vlc es solo un "binding": necesita que VLC este instalado en el
sistema (libvlc.dll). Si no esta instalado, o si esta instalado en la
version de 64 bits mientras Python corre en 32 bits (o viceversa),
python-vlc falla con un OSError poco claro para un usuario final.

Este modulo intenta el import de forma controlada y devuelve un
mensaje en español, grande y claro, listo para mostrar en la UI,
en vez de dejar que la excepcion crude llegue al usuario.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger("vlc_check")

MENSAJE_VLC_NO_INSTALADO = (
    "No se encontro VLC instalado en este computador.\n\n"
    "Para poder reproducir videos y musica, instala VLC (version de 32 bits) "
    "desde videolan.org y vuelve a abrir esta aplicacion."
)

MENSAJE_VLC_ERROR_GENERICO = (
    "No se pudo iniciar el reproductor de video.\n\n"
    "Cierra la aplicacion, reinicia el computador e intenta de nuevo. "
    "Si el problema continua, reinstala VLC (version de 32 bits)."
)


def try_load_vlc() -> Tuple[bool, Optional[object], Optional[str]]:
    """
    Intenta importar y crear una instancia de VLC.

    Devuelve (ok, vlc_module_o_none, mensaje_error_o_none):
      - ok=True  -> (True, modulo_vlc, None)
      - ok=False -> (False, None, "mensaje en español para mostrar en la UI")

    Se llama UNA VEZ al iniciar la app (Fase 4), antes de habilitar
    los botones de Reproducir. Si falla, la app debe seguir funcionando
    para Buscar y Descargar, solo deshabilitando la reproduccion en vivo.
    """
    try:
        import vlc  # python-vlc; requiere VLC instalado en el sistema
    except OSError as exc:
        logger.warning("VLC no encontrado / incompatible: %s", exc)
        return False, None, MENSAJE_VLC_NO_INSTALADO
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado cargando python-vlc: %s", exc)
        return False, None, MENSAJE_VLC_ERROR_GENERICO

    try:
        instancia_prueba = vlc.Instance()
        if instancia_prueba is None:
            raise RuntimeError("vlc.Instance() devolvio None")
    except Exception as exc:  # noqa: BLE001
        logger.exception("VLC importado pero no se pudo instanciar: %s", exc)
        return False, None, MENSAJE_VLC_ERROR_GENERICO

    return True, vlc, None
