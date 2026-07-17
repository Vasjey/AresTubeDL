"""
downloads/playlist_importer.py

Importa una "playlist" desde un archivo .txt plano, pensado para que
un adulto mayor (o un familiar) pueda armar una lista simplemente
escribiendo, una linea por cancion, ya sea:
  - Un link de YouTube:  https://www.youtube.com/watch?v=xxxxxxxxxxx
  - O el nombre de la cancion/artista: "Bohemian Rhapsody Queen"

Lineas vacias y lineas que empiecen con "#" (comentarios) se ignoran.

Cada linea que NO es un link se resuelve con una busqueda (se toma el
primer resultado). Por eso esta funcion hace llamadas de red y debe
ejecutarse SIEMPRE en un hilo de fondo desde la UI.
"""

import logging
from dataclasses import dataclass
from typing import List, Callable, Optional

from core.search import search_youtube, SearchError

logger = logging.getLogger("playlist_importer")


class PlaylistImportError(Exception):
    """Error amigable para mostrar en texto grande en la UI."""
    pass


@dataclass
class PlaylistEntry:
    texto_original: str
    webpage_url: str
    titulo: str
    encontrado: bool


def _es_url(linea: str) -> bool:
    return linea.startswith("http://") or linea.startswith("https://")


def leer_lineas_txt(ruta_archivo: str) -> List[str]:
    """Lee el .txt y devuelve las lineas utiles (sin vacias ni comentarios)."""
    try:
        with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
            lineas_crudas = f.readlines()
    except OSError as exc:
        logger.warning("No se pudo leer el archivo %s: %s", ruta_archivo, exc)
        raise PlaylistImportError(
            "No se pudo abrir el archivo. Verifica que el archivo exista "
            "y no este abierto en otro programa."
        ) from exc

    lineas = []
    for linea in lineas_crudas:
        limpia = linea.strip()
        if not limpia or limpia.startswith("#"):
            continue
        lineas.append(limpia)

    if not lineas:
        raise PlaylistImportError(
            "El archivo esta vacio. Escribe una cancion o link por linea."
        )

    return lineas


def resolver_playlist(
    ruta_archivo: str,
    on_status: Optional[Callable[[str], None]] = None,
) -> List[PlaylistEntry]:
    """
    Lee el .txt y resuelve cada linea a una entrada reproducible/descargable.
    Las lineas que ya son un link se usan directamente (no gastan una
    busqueda). Las que son texto libre se buscan una por una.

    Nunca lanza excepcion por una linea individual fallida: esa entrada
    queda marcada con encontrado=False para que la UI la muestre en
    rojo/tachada, y el resto de la playlist se sigue procesando.
    """
    lineas = leer_lineas_txt(ruta_archivo)
    resultados: List[PlaylistEntry] = []

    for indice, linea in enumerate(lineas, start=1):
        if on_status:
            on_status(f"Importando {indice} de {len(lineas)}...")

        if _es_url(linea):
            resultados.append(
                PlaylistEntry(
                    texto_original=linea,
                    webpage_url=linea,
                    titulo=linea,
                    encontrado=True,
                )
            )
            continue

        try:
            encontrados = search_youtube(linea, max_results=1)
            primero = encontrados[0]
            resultados.append(
                PlaylistEntry(
                    texto_original=linea,
                    webpage_url=primero.webpage_url,
                    titulo=primero.title,
                    encontrado=True,
                )
            )
        except SearchError as exc:
            logger.info("No se encontro resultado para '%s': %s", linea, exc)
            resultados.append(
                PlaylistEntry(
                    texto_original=linea,
                    webpage_url="",
                    titulo=f"No encontrado: {linea}",
                    encontrado=False,
                )
            )

    if on_status:
        on_status("")

    return resultados
