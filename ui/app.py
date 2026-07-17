"""
ui/app.py

Ventana principal de la aplicacion. Une todos los modulos construidos
en las Fases 1-3:
  - Auto-actualizacion de la app y de yt-dlp (en background al iniciar).
  - Busqueda (SearchTab) + reproduccion de audio (BottomBar) y de
    video (VideoPlayerWindow).
  - Descargas a MP3 con deteccion de USB.
  - Playlists manuales + importadas desde TXT.

Este es el punto donde toda la app "cobra vida"; el resto de los
modulos son deliberadamente independientes de tkinter para poder
probarlos por separado.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk

import config
from version import APP_VERSION
from updater.app_updater import check_and_apply_update
from updater.pytubefix_updater import update_pytubefix_silently

from core.vlc_check import try_load_vlc
from core.audio_player import AudioPlayer
from core.video_player import VideoPlayerWindow
from core.stream_resolver import resolve_video_stream, StreamResolveError
from core import playlist_store
from core.playlist_store import CancionGuardada

from downloads import destination
from downloads.mp3_downloader import descargar_mp3, DownloadError

from ui.theme import aplicar_estilo, FONT_TITULO, COLOR_FONDO
from ui.dialogs import mostrar_mensaje, preguntar_usb_o_computador, elegir_o_crear_playlist
from ui.bottom_bar import BottomBar
from ui.search_tab import SearchTab
from ui.downloads_tab import DownloadsTab
from ui.playlists_tab import PlaylistsTab
from ui.import_tab import ImportTab


class AresApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(
            f"Ares YouTube Downloader (v{APP_VERSION}) - Diseñado para Accesibilidad Senior"
        )
        self.root.geometry("980x640")
        self.root.minsize(760, 520)
        aplicar_estilo(self.root)

        self._descarga_en_curso = False

        # --- VLC: se valida UNA vez al iniciar ---
        ok_vlc, vlc_module, error_vlc = try_load_vlc()
        self._vlc_disponible = ok_vlc
        self._vlc_module = vlc_module
        self._audio_player = AudioPlayer(vlc_module) if ok_vlc else None

        self._construir_ui()

        if not ok_vlc:
            self.root.after(300, lambda: mostrar_mensaje(
                self.root, "Reproductor no disponible", error_vlc, es_error=True
            ))

        self._iniciar_actualizaciones_en_segundo_plano()
        self._ciclo_deteccion_usb()

        self.root.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    # ------------------------------------------------------------
    def _construir_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.search_tab = SearchTab(
            self.notebook,
            on_reproducir_audio=self._reproducir_audio_desde_busqueda,
            on_reproducir_video=self._reproducir_video,
            on_descargar=self._iniciar_descarga,
            on_agregar_playlist=self._agregar_a_playlist,
            on_mostrar_error=self._mostrar_error,
        )
        self.downloads_tab = DownloadsTab(self.notebook)
        self.playlists_tab = PlaylistsTab(
            self.notebook,
            on_reproducir_playlist=self._reproducir_cola_generica,
            on_descargar_cancion=self._iniciar_descarga,
            on_mostrar_error=self._mostrar_error,
        )
        self.import_tab = ImportTab(
            self.notebook,
            on_playlist_creada=self._al_crear_playlist_importada,
            on_mostrar_error=self._mostrar_error,
        )

        self.notebook.add(self.search_tab, text="BUSQUEDA")
        self.notebook.add(self.downloads_tab, text="DESCARGAS")
        self.notebook.add(self.playlists_tab, text="PLAYLISTS")
        self.notebook.add(self.import_tab, text="IMPORTAR TXT")

        self.bottom_bar = BottomBar(
            self.root, self._audio_player, self._vlc_disponible, self._mostrar_error,
        )
        self.bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------------------------------------------------
    # Reproduccion
    # ------------------------------------------------------------
    def _reproducir_audio_desde_busqueda(self, resultados: list, indice: int):
        cola = [
            {"titulo": r.title, "webpage_url": r.webpage_url}
            for r in resultados
        ]
        self.bottom_bar.reproducir_cola(cola, indice)

    def _reproducir_cola_generica(self, cola: list, indice: int):
        self.bottom_bar.reproducir_cola(cola, indice)

    def _reproducir_video(self, webpage_url: str, titulo: str):
        if not self._vlc_disponible:
            self._mostrar_error("No se puede reproducir video: VLC no esta disponible.")
            return

        hilo = threading.Thread(
            target=self._resolver_video_en_hilo, args=(webpage_url, titulo), daemon=True,
        )
        hilo.start()

    def _resolver_video_en_hilo(self, webpage_url: str, titulo: str):
        try:
            resuelto = resolve_video_stream(webpage_url)
        except StreamResolveError as exc:
            mensaje_error = str(exc)
            self.root.after(0, lambda: self._mostrar_error(mensaje_error))
            return
        except Exception:  # noqa: BLE001
            self.root.after(0, lambda: self._mostrar_error(
                "Ocurrio un error al preparar el video."
            ))
            return

        self.root.after(0, lambda: self._abrir_ventana_video(resuelto.direct_url, titulo))

    def _abrir_ventana_video(self, direct_url: str, titulo: str):
        ventana = VideoPlayerWindow(self.root, self._vlc_module)
        try:
            ventana.play_url(direct_url, titulo)
        except Exception:  # noqa: BLE001
            ventana.destroy()
            self._mostrar_error("VLC no pudo reproducir este video. Prueba con otro.")

    # ------------------------------------------------------------
    # Descargas
    # ------------------------------------------------------------
    def _iniciar_descarga(self, item):
        if self._descarga_en_curso:
            self._mostrar_error("Espera a que termine la descarga actual.")
            return

        ruta_usb = destination.hay_pendrive_conectado()
        if ruta_usb:
            eleccion = preguntar_usb_o_computador(self.root)
            usar_pendrive = eleccion == "usb"
        else:
            usar_pendrive = False

        carpeta_destino = destination.construir_carpeta_destino(usar_pendrive, ruta_usb)

        self._descarga_en_curso = True
        hilo = threading.Thread(
            target=self._descargar_en_hilo, args=(item, carpeta_destino), daemon=True,
        )
        hilo.start()

    def _descargar_en_hilo(self, item, carpeta_destino: str):
        def actualizar_estado(texto):
            self.root.after(0, lambda: self.bottom_bar.establecer_estado_actualizacion(texto))

        try:
            resultado = descargar_mp3(item.webpage_url, carpeta_destino, on_status=actualizar_estado)
        except DownloadError as exc:
            mensaje_error = str(exc)
            self.root.after(0, lambda: self._al_fallar_descarga(mensaje_error))
            return
        except Exception:  # noqa: BLE001
            self.root.after(0, lambda: self._al_fallar_descarga(
                "Ocurrio un error inesperado al descargar."
            ))
            return

        self.root.after(0, lambda: self._al_completar_descarga(resultado))

    def _al_completar_descarga(self, resultado):
        self._descarga_en_curso = False
        self.bottom_bar.establecer_estado_actualizacion("")
        self.downloads_tab.agregar_descarga_completada(resultado.titulo, resultado.ruta_archivo_mp3)

    def _al_fallar_descarga(self, mensaje: str):
        self._descarga_en_curso = False
        self.bottom_bar.establecer_estado_actualizacion("")
        self._mostrar_error(mensaje)

    # ------------------------------------------------------------
    # Playlists
    # ------------------------------------------------------------
    def _agregar_a_playlist(self, item):
        nombre_playlist = elegir_o_crear_playlist(self.root)
        if not nombre_playlist:
            return

        playlist_store.crear_playlist_si_no_existe(nombre_playlist)
        playlist_store.agregar_cancion(
            nombre_playlist,
            CancionGuardada(
                titulo=item.title, artista=item.uploader,
                duracion=item.duration_formatted, webpage_url=item.webpage_url,
            ),
        )
        self.playlists_tab.refrescar_lista_playlists(seleccionar=nombre_playlist)
        mostrar_mensaje(
            self.root, "Agregado",
            f"'{item.title}' se agrego a la playlist '{nombre_playlist}'.",
        )

    def _al_crear_playlist_importada(self, nombre_playlist: str):
        self.playlists_tab.refrescar_lista_playlists(seleccionar=nombre_playlist)

    # ------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------
    def _mostrar_error(self, mensaje: str):
        mostrar_mensaje(self.root, "Aviso", mensaje, es_error=True)

    # ------------------------------------------------------------
    # Actualizaciones en background
    # ------------------------------------------------------------
    def _iniciar_actualizaciones_en_segundo_plano(self):
        def estado_callback(texto):
            self.root.after(0, lambda: self.bottom_bar.establecer_estado_actualizacion(texto))

        threading.Thread(
            target=update_pytubefix_silently,
            kwargs={"on_status": estado_callback},
            daemon=True,
        ).start()

        threading.Thread(
            target=check_and_apply_update,
            kwargs={"on_status": estado_callback},
            daemon=True,
        ).start()

    # ------------------------------------------------------------
    # Deteccion periodica de USB (solo actualiza el texto de la barra)
    # ------------------------------------------------------------
    def _ciclo_deteccion_usb(self):
        ruta = destination.hay_pendrive_conectado()
        if ruta:
            self.bottom_bar.establecer_estado_usb(f"Pendrive detectado ({ruta})")
        else:
            self.bottom_bar.establecer_estado_usb("Sin Pendrive conectado")

        self.root.after(4000, self._ciclo_deteccion_usb)

    # ------------------------------------------------------------
    def _al_cerrar(self):
        if self._audio_player:
            self._audio_player.release()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
