"""
core/playlist_store.py

Guardado simple de playlists en un archivo JSON local (sin base de
datos, para mantener la app ligera). Cada playlist es una lista de
canciones con los datos minimos para poder reproducirlas/descargarlas
despues sin tener que volver a buscar.

Estructura del archivo playlists.json:
{
  "Favoritas de la Abuela": [
      {"titulo": "...", "artista": "...", "duracion": "6:07",
       "webpage_url": "https://..."},
      ...
  ],
  "Otra playlist": [...]
}
"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict

logger = logging.getLogger("playlist_store")

_CARPETA_APP = os.path.dirname(os.path.abspath(__file__))
_RUTA_JSON = os.path.join(os.path.dirname(_CARPETA_APP), "playlists.json")


@dataclass
class CancionGuardada:
    titulo: str
    artista: str
    duracion: str
    webpage_url: str


def _cargar_todo() -> Dict[str, list]:
    if not os.path.isfile(_RUTA_JSON):
        return {}
    try:
        with open(_RUTA_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("No se pudo leer playlists.json: %s", exc)
        return {}


def _guardar_todo(datos: Dict[str, list]):
    try:
        with open(_RUTA_JSON, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.warning("No se pudo guardar playlists.json: %s", exc)


def listar_playlists() -> List[str]:
    return sorted(_cargar_todo().keys())


def obtener_canciones(nombre_playlist: str) -> List[CancionGuardada]:
    datos = _cargar_todo()
    crudos = datos.get(nombre_playlist, [])
    return [CancionGuardada(**c) for c in crudos]


def crear_playlist_si_no_existe(nombre_playlist: str):
    datos = _cargar_todo()
    if nombre_playlist not in datos:
        datos[nombre_playlist] = []
        _guardar_todo(datos)


def agregar_cancion(nombre_playlist: str, cancion: CancionGuardada):
    datos = _cargar_todo()
    lista = datos.setdefault(nombre_playlist, [])

    # Evita duplicados exactos (misma URL) dentro de la misma playlist.
    ya_existe = any(c.get("webpage_url") == cancion.webpage_url for c in lista)
    if not ya_existe:
        lista.append(asdict(cancion))
        _guardar_todo(datos)


def quitar_cancion(nombre_playlist: str, webpage_url: str):
    datos = _cargar_todo()
    lista = datos.get(nombre_playlist, [])
    datos[nombre_playlist] = [c for c in lista if c.get("webpage_url") != webpage_url]
    _guardar_todo(datos)


def eliminar_playlist(nombre_playlist: str):
    datos = _cargar_todo()
    datos.pop(nombre_playlist, None)
    _guardar_todo(datos)
