"""
version.py
Fuente unica de verdad de la version de la app.
El auto-updater compara este numero contra el tag de la ultima
release publicada en el repositorio de GitHub.

Formato: MAJOR.MINOR.PATCH (semver simple, sin 'v' al inicio)
"""

APP_VERSION = "1.0.0"

# Nombre del archivo ejecutable/script que el updater debe reemplazar.
# Cambialo segun como distribuyas la app:
#   - "AresYT.exe"      -> si empaquetas con PyInstaller
#   - "main.py"         -> si el usuario corre la app como script
APP_EXECUTABLE_NAME = "AresYT.exe"
