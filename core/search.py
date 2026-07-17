"""
core/search.py

Busqueda de videos en YouTube usando pytubefix (Plan D: migracion
completa desde yt-dlp). pytubefix es una libreria 100% Python puro
(sin binarios nativos ni subprocesos externos), soporta Python 3.8
oficialmente, y sigue actualizada contra los cambios de YouTube.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from pytubefix import Search
from pytubefix.exceptions import PytubeFixError

logger = logging.getLogger("search")


@dataclass
class SearchResultItem:
    video_id: str
    title: str
    uploader: str
    duration_seconds: Optional[int]
    thumbnail_url: Optional[str]
    webpage_url: str

    @property
    def duration_formatted(self) -> str:
        if not self.duration_seconds:
            return "--:--"
        minutos, segundos = divmod(int(self.duration_seconds), 60)
        return f"{minutos}:{segundos:02d}"


class SearchError(Exception):
    """Error amigable para mostrar en texto grande en la UI."""
    pass


def search_youtube(query: str, max_results: int = 15) -> List[SearchResultItem]:
    """
    Busca `query` en YouTube y devuelve una lista de resultados.
    Lanza SearchError con un mensaje en español, apto para mostrar
    directamente en la UI, si algo falla (sin internet, sin resultados).
    """
    if not query or not query.strip():
        raise SearchError("Escribe algo para buscar.")

    try:
        busqueda = Search(query.strip())
        videos = busqueda.videos[:max_results]
    except PytubeFixError as exc:
        logger.warning("Error de busqueda pytubefix: %s", exc)
        raise SearchError(f"No se pudo buscar: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado en busqueda: %s", exc)
        raise SearchError("Ocurrio un error al buscar. Intenta de nuevo.") from exc

    if not videos:
        raise SearchError("No se encontraron resultados. Prueba con otras palabras.")

    resultados = []
    for video in videos:
        # Cada resultado se procesa de forma independiente: si un video
        # puntual falla (privado, borrado, region-bloqueado), se omite
        # ese resultado en vez de arruinar toda la busqueda.
        try:
            video_id = video.video_id
            titulo = video.title or "(sin titulo)"
            autor = video.author or "Desconocido"
            duracion = video.length
            miniatura = video.thumbnail_url
            url_pagina = video.watch_url
        except PytubeFixError as exc:
            logger.info("Se omite un resultado no disponible: %s", exc)
            continue
        except Exception as exc:  # noqa: BLE001
            logger.info("Se omite un resultado por error inesperado: %s", exc)
            continue

        resultados.append(
            SearchResultItem(
                video_id=video_id,
                title=titulo,
                uploader=autor,
                duration_seconds=duracion,
                thumbnail_url=miniatura,
                webpage_url=url_pagina,
            )
        )

    if not resultados:
        raise SearchError("No se encontraron resultados. Prueba con otras palabras.")

    return resultados
