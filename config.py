"""
config.py
Constantes centrales del proyecto. Editar aqui los valores propios
antes de distribuir la app (usuario/repo de GitHub, etc).
"""

import os

# ----------------------------------------------------------------
# Auto-actualizacion de la APP (Fase 1)
# ----------------------------------------------------------------
# Repositorio publico de GitHub donde se publican las releases del
# ejecutable/script de la app. Debe contener Releases con un asset
# llamado igual a version.APP_EXECUTABLE_NAME (ej: "AresYT.exe").
GITHUB_OWNER = "Vasjey"
GITHUB_REPO = "AresTubeDL"

# Timeout de red para no colgar el arranque si no hay internet
# (muy comun en PCs de adultos mayores con wifi inestable).
UPDATE_CHECK_TIMEOUT_SECONDS = 6

# ----------------------------------------------------------------
# Actualizacion silenciosa de pytubefix
# ----------------------------------------------------------------
# Si True: intenta "pip install -U pytubefix" en background al iniciar.
# Si False: usa la version ya instalada sin tocarla (mas seguro para
# no romper algo sin que el usuario se entere).
# (El nombre "YTDLP_..." quedo de una version anterior del proyecto
# basada en yt-dlp; ver la nota mas abajo.)
YTDLP_AUTO_UPDATE = True

# ----------------------------------------------------------------
# Descargas / conversion a MP3
# ----------------------------------------------------------------
# Calidad del MP3 final (kbps). 192 es un buen balance calidad/tamaño
# para musica; en un HDD lento no conviene subir mas (mas tiempo de
# conversion sin beneficio audible para la mayoria de los usuarios).
MP3_CALIDAD_KBPS = "192"

# Ruta a ffmpeg.exe. Si es None, se asume que "ffmpeg" esta en el PATH
# del sistema. Se recomienda distribuir ffmpeg.exe junto a la app
# (carpeta "ffmpeg/ffmpeg.exe" al lado del ejecutable) para no
# depender de que el usuario lo instale manualmente.
import os as _os
_carpeta_app = _os.path.dirname(_os.path.abspath(__file__))
_ffmpeg_local = _os.path.join(_carpeta_app, "ffmpeg", "ffmpeg.exe")
FFMPEG_PATH = _ffmpeg_local if _os.path.isfile(_ffmpeg_local) else None

# ----------------------------------------------------------------
# pytubefix (Plan D: reemplaza a yt-dlp)
# ----------------------------------------------------------------
# yt-dlp (oficial y el fork nicolaasjan/yt-dlp) dejaron de poder
# instalarse/funcionar en Python 3.8, asi que la extraccion de
# YouTube se hace con pytubefix: libreria 100% Python puro, sin
# binarios nativos ni subprocesos, con soporte oficial para
# Python 3.7+. Se actualiza sola via pip (ver
# updater/pytubefix_updater.py). El nombre de esta bandera quedo
# como "YTDLP_AUTO_UPDATE" por razones historicas del proyecto, pero
# ahora controla la actualizacion de pytubefix.

# ----------------------------------------------------------------
# Carpetas de trabajo
# ----------------------------------------------------------------
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
DOWNLOAD_FOLDER_NAME = "Musica_Descargada"
DEFAULT_DOWNLOAD_PATH = os.path.join(DESKTOP_PATH, DOWNLOAD_FOLDER_NAME)

# Carpeta local de logs simples (texto plano, facil de revisar/soportar
# remotamente por un familiar o tecnico)
LOG_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
