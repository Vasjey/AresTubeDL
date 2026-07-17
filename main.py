"""
main.py

Punto de entrada real de la aplicacion (Fase 4).
Arranca la ventana principal (ui.app.AresApp), que internamente:
  - dispara la auto-actualizacion de la app y de yt-dlp en background,
  - construye las 4 pestañas (BUSQUEDA, DESCARGAS, PLAYLISTS, IMPORTAR TXT),
  - deja lista la barra inferior de reproduccion de audio.
"""

import logging
import os

import config
from ui.app import AresApp

os.makedirs(config.LOG_FOLDER, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(config.LOG_FOLDER, "app.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    app = AresApp()
    app.run()

