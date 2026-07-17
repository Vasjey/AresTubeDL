"""
updater/app_updater.py

Auto-actualizacion de LA APP (no de yt-dlp) desde GitHub Releases.

Flujo:
1. Consulta la API publica de GitHub: /repos/{owner}/{repo}/releases/latest
2. Compara el tag_name contra version.APP_VERSION.
3. Si hay una version mas nueva, descarga el asset que coincide con
   version.APP_EXECUTABLE_NAME a un archivo temporal "*_new".
4. Genera un .bat que espera a que el proceso actual cierre, reemplaza
   el archivo viejo por el nuevo, y vuelve a lanzar la app.
5. Lanza ese .bat de forma independiente (DETACHED_PROCESS) y cierra
   la app actual para liberar el archivo.

Todo se ejecuta pensado para correr en un hilo (threading.Thread) desde
main.py, para no bloquear el arranque de la ventana si no hay internet.

Diseño defensivo: cualquier fallo de red o de GitHub NO debe nunca
crashear la app ni bloquear su uso normal. El usuario adulto mayor debe
poder seguir usando la app aunque el update falle silenciosamente.
"""

import os
import sys
import json
import subprocess
import tempfile
import logging
from typing import Optional, Callable

import requests
from packaging import version as pkg_version

import config
from version import APP_VERSION, APP_EXECUTABLE_NAME

logger = logging.getLogger("app_updater")


class UpdateInfo:
    def __init__(self, tag_name: str, download_url: str):
        self.tag_name = tag_name
        self.download_url = download_url


def _get_latest_release() -> Optional[UpdateInfo]:
    """Consulta GitHub Releases. Devuelve None si no hay internet,
    no hay releases, o el asset esperado no existe (nunca lanza excepcion
    hacia afuera)."""
    api_url = (
        f"https://api.github.com/repos/{config.GITHUB_OWNER}/"
        f"{config.GITHUB_REPO}/releases/latest"
    )
    try:
        resp = requests.get(
            api_url, timeout=config.UPDATE_CHECK_TIMEOUT_SECONDS
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.info("No se pudo consultar GitHub Releases: %s", exc)
        return None

    tag_name = data.get("tag_name", "").lstrip("v")
    assets = data.get("assets", [])

    matching_asset = next(
        (a for a in assets if a.get("name") == APP_EXECUTABLE_NAME), None
    )
    if not matching_asset:
        logger.info(
            "La release %s no tiene un asset llamado %s",
            tag_name, APP_EXECUTABLE_NAME,
        )
        return None

    return UpdateInfo(
        tag_name=tag_name,
        download_url=matching_asset.get("browser_download_url"),
    )


def _is_newer(remote_tag: str, local_version: str) -> bool:
    try:
        return pkg_version.parse(remote_tag) > pkg_version.parse(local_version)
    except pkg_version.InvalidVersion:
        # Si el tag no es semver valido, no arriesgamos: no actualiza.
        logger.warning("Tag remoto no valido para comparar: %s", remote_tag)
        return False


def _download_new_version(download_url: str) -> Optional[str]:
    """Descarga el nuevo ejecutable a un archivo temporal.
    Devuelve la ruta local, o None si falla."""
    try:
        resp = requests.get(download_url, stream=True, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Fallo al descargar nueva version: %s", exc)
        return None

    tmp_dir = tempfile.gettempdir()
    new_path = os.path.join(tmp_dir, f"_new_{APP_EXECUTABLE_NAME}")
    try:
        with open(new_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
    except OSError as exc:
        logger.warning("Fallo al escribir archivo descargado: %s", exc)
        return None

    return new_path


def _current_executable_path() -> str:
    """Ruta del ejecutable/script actual que debe ser reemplazado."""
    if getattr(sys, "frozen", False):
        # Corriendo como .exe empaquetado con PyInstaller
        return sys.executable
    # Corriendo como script .py (modo desarrollo)
    return os.path.abspath(sys.argv[0])


def _build_and_launch_swap_script(new_file_path: str, current_exe_path: str):
    """
    Crea un .bat que:
      1. Espera unos segundos a que el proceso actual libere el archivo.
      2. Borra el ejecutable viejo.
      3. Renombra el nuevo archivo descargado al nombre original.
      4. Vuelve a lanzar la app.
      5. Se autoelimina.
    Lo lanza en un proceso independiente y separado de la app actual.
    """
    bat_path = os.path.join(tempfile.gettempdir(), "ares_yt_update.bat")
    current_dir = os.path.dirname(current_exe_path)

    bat_content = f"""@echo off
:wait_loop
tasklist /FI "IMAGENAME eq {os.path.basename(current_exe_path)}" 2>NUL | find /I "{os.path.basename(current_exe_path)}" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /T 1 /NOBREAK >NUL
    goto wait_loop
)
del /F /Q "{current_exe_path}"
move /Y "{new_file_path}" "{current_exe_path}"
start "" "{current_exe_path}"
del /F /Q "%~f0"
"""
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    # DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP para que sobreviva
    # al cierre de la app actual, sin ventana de consola visible.
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd", "/c", bat_path],
        cwd=current_dir,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
        close_fds=True,
    )


def check_and_apply_update(
    on_status: Optional[Callable[[str], None]] = None,
    on_ready_to_restart: Optional[Callable[[], None]] = None,
):
    """
    Punto de entrada principal. Pensado para correr en un hilo de fondo.

    on_status(texto): callback opcional para mostrar texto grande en la UI
        (ej: "Buscando actualizaciones...", "Descargando nueva version...").
    on_ready_to_restart(): callback opcional que la UI puede usar para
        avisar al usuario y cerrar la app de forma ordenada, en vez de
        que la app se cierre abruptamente sin avisar.

    IMPORTANTE: esta funcion NUNCA lanza excepciones hacia afuera.
    Cualquier problema de red/GitHub se registra en el log y la app
    sigue funcionando con la version actual.
    """
    try:
        if on_status:
            on_status("Buscando actualizaciones...")

        info = _get_latest_release()
        if info is None:
            if on_status:
                on_status("")  # nada que mostrar, sigue como si nada
            return

        if not _is_newer(info.tag_name, APP_VERSION):
            logger.info("La app ya esta en la ultima version (%s)", APP_VERSION)
            if on_status:
                on_status("")
            return

        if on_status:
            on_status("Descargando nueva version de la aplicacion...")

        new_file_path = _download_new_version(info.download_url)
        if new_file_path is None:
            if on_status:
                on_status("")
            return

        current_exe_path = _current_executable_path()

        # Si estamos corriendo como script .py en desarrollo, no
        # intentamos el reemplazo binario automatico (evita corromper
        # el entorno de desarrollo). Solo se aplica en modo "frozen"
        # (.exe empaquetado), que es como se distribuye al usuario final.
        if not getattr(sys, "frozen", False):
            logger.info(
                "Modo desarrollo (.py): se detecto version nueva (%s) "
                "pero el auto-reemplazo solo aplica en .exe empaquetado.",
                info.tag_name,
            )
            if on_status:
                on_status("")
            return

        if on_status:
            on_status(
                "Instalando actualizacion. La aplicacion se reiniciara..."
            )

        _build_and_launch_swap_script(new_file_path, current_exe_path)

        if on_ready_to_restart:
            on_ready_to_restart()
        else:
            os._exit(0)

    except Exception as exc:  # noqa: BLE001 - defensivo a proposito
        logger.exception("Error inesperado en check_and_apply_update: %s", exc)
        if on_status:
            on_status("")
