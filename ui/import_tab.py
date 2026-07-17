"""
ui/import_tab.py

Pestaña "IMPORTAR TXT": el usuario elige un archivo .txt con una
cancion (link o texto de busqueda) por linea, la app resuelve cada
linea en segundo plano, y el resultado se guarda como una playlist
nueva (usando el mismo almacenamiento que las playlists manuales de
la pestaña PLAYLISTS).
"""

import threading
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog

from ui.theme import FONT_NORMAL, FONT_NORMAL_NEGRITA, COLOR_FONDO
from core import playlist_store
from core.playlist_store import CancionGuardada
from downloads.playlist_importer import resolver_playlist, PlaylistImportError


class ImportTab(tk.Frame):
    def __init__(self, parent, on_playlist_creada, on_mostrar_error):
        super().__init__(parent, bg=COLOR_FONDO)
        self._on_playlist_creada = on_playlist_creada
        self._on_mostrar_error = on_mostrar_error
        self._construir_ui()

    def _construir_ui(self):
        tk.Label(
            self,
            text=(
                "Importa una lista de canciones desde un archivo de texto (.txt).\n"
                "Escribe un link de YouTube o el nombre de una cancion por linea."
            ),
            font=FONT_NORMAL, bg=COLOR_FONDO, justify="left", wraplength=560,
        ).pack(anchor="w", padx=16, pady=20)

        ttk.Button(
            self, text="Elegir Archivo TXT...", style="Accion.TButton",
            width=22, command=self._elegir_archivo,
        ).pack(anchor="w", padx=16)

        self.label_estado = tk.Label(
            self, text="", font=FONT_NORMAL_NEGRITA, bg=COLOR_FONDO,
        )
        self.label_estado.pack(anchor="w", padx=16, pady=16)

    def _elegir_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Elegir archivo de playlist",
            filetypes=[("Archivo de texto", "*.txt")],
        )
        if not ruta:
            return

        nombre_playlist = simpledialog.askstring(
            "Nombre de la Playlist",
            "¿Como quieres llamar a esta playlist importada?",
            parent=self,
        )
        if not nombre_playlist or not nombre_playlist.strip():
            return
        nombre_playlist = nombre_playlist.strip()

        self.label_estado.config(text="Importando...", fg="#000000")

        hilo = threading.Thread(
            target=self._importar_en_hilo, args=(ruta, nombre_playlist), daemon=True,
        )
        hilo.start()

    def _importar_en_hilo(self, ruta: str, nombre_playlist: str):
        def actualizar_estado(texto):
            self.after(0, lambda: self.label_estado.config(text=texto, fg="#000000"))

        try:
            entradas = resolver_playlist(ruta, on_status=actualizar_estado)
        except PlaylistImportError as exc:
            mensaje_error = str(exc)
            self.after(0, lambda: self._al_fallar(mensaje_error))
            return
        except Exception:  # noqa: BLE001
            self.after(0, lambda: self._al_fallar(
                "Ocurrio un error al importar el archivo."
            ))
            return

        self.after(0, lambda: self._al_terminar(nombre_playlist, entradas))

    def _al_fallar(self, mensaje: str):
        self.label_estado.config(text="", fg="#000000")
        self._on_mostrar_error(mensaje)

    def _al_terminar(self, nombre_playlist: str, entradas: list):
        playlist_store.crear_playlist_si_no_existe(nombre_playlist)

        encontradas = 0
        for entrada in entradas:
            if not entrada.encontrado:
                continue
            playlist_store.agregar_cancion(
                nombre_playlist,
                CancionGuardada(
                    titulo=entrada.titulo, artista="", duracion="",
                    webpage_url=entrada.webpage_url,
                ),
            )
            encontradas += 1

        total = len(entradas)
        self.label_estado.config(
            text=f"Listo: {encontradas} de {total} canciones agregadas a '{nombre_playlist}'.",
            fg="#000000",
        )
        self._on_playlist_creada(nombre_playlist)
