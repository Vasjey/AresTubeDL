"""
ui/playlists_tab.py

Pestaña "PLAYLISTS": permite crear playlists manualmente (las
canciones se agregan desde la pestaña BUSQUEDA con el boton
"+ PLAYLIST"), verlas, reproducirlas completas, y descargar o quitar
canciones individuales. Tambien recibe las playlists creadas por la
pestaña IMPORTAR TXT (se guardan con el mismo almacenamiento).
"""

import tkinter as tk
from tkinter import ttk, simpledialog

from ui.theme import (
    FONT_NORMAL, FONT_NORMAL_NEGRITA, COLOR_FONDO,
    COLOR_FILA_PAR, COLOR_FILA_IMPAR,
)
from core import playlist_store


class PlaylistsTab(tk.Frame):
    def __init__(self, parent, on_reproducir_playlist, on_descargar_cancion, on_mostrar_error):
        super().__init__(parent, bg=COLOR_FONDO)

        self._on_reproducir_playlist = on_reproducir_playlist
        self._on_descargar_cancion = on_descargar_cancion
        self._on_mostrar_error = on_mostrar_error

        self._playlist_seleccionada = None

        self._construir_ui()
        self.refrescar_lista_playlists()

    # ------------------------------------------------------------
    def _construir_ui(self):
        panel_izquierdo = tk.Frame(self, bg=COLOR_FONDO, width=220)
        panel_izquierdo.pack(side=tk.LEFT, fill=tk.Y, padx=16, pady=14)
        panel_izquierdo.pack_propagate(False)

        tk.Label(
            panel_izquierdo, text="Mis Playlists", font=FONT_NORMAL_NEGRITA,
            bg=COLOR_FONDO,
        ).pack(anchor="w", pady=6)

        self._lista_playlists = tk.Listbox(
            panel_izquierdo, font=FONT_NORMAL, exportselection=False,
        )
        self._lista_playlists.pack(fill=tk.BOTH, expand=True)
        self._lista_playlists.bind("<<ListboxSelect>>", self._al_seleccionar_playlist)

        ttk.Button(
            panel_izquierdo, text="Crear Playlist Nueva", style="Accion.TButton",
            command=self._crear_playlist_nueva,
        ).pack(fill=tk.X, pady=10)

        # Panel derecho: canciones de la playlist seleccionada
        panel_derecho = tk.Frame(self, bg=COLOR_FONDO)
        panel_derecho.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=14)

        fila_titulo = tk.Frame(panel_derecho, bg=COLOR_FONDO)
        fila_titulo.pack(fill=tk.X)

        self.label_titulo_playlist = tk.Label(
            fila_titulo, text="Selecciona una playlist a la izquierda",
            font=FONT_NORMAL_NEGRITA, bg=COLOR_FONDO,
        )
        self.label_titulo_playlist.pack(side=tk.LEFT)

        self.btn_reproducir_todo = ttk.Button(
            fila_titulo, text="Reproducir Toda", style="Accion.TButton",
            width=16, command=self._reproducir_playlist_completa,
        )
        self.btn_reproducir_todo.pack(side=tk.RIGHT)
        self.btn_reproducir_todo.state(["disabled"])

        contenedor = tk.Frame(panel_derecho, bg=COLOR_FONDO)
        contenedor.pack(fill=tk.BOTH, expand=True, pady=10)

        self._canvas = tk.Canvas(contenedor, bg=COLOR_FONDO, highlightthickness=0)
        barra_scroll = ttk.Scrollbar(contenedor, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=barra_scroll.set)
        barra_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._frame_filas = tk.Frame(self._canvas, bg=COLOR_FONDO)
        self._canvas.create_window((0, 0), window=self._frame_filas, anchor="nw")
        self._frame_filas.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )

    # ------------------------------------------------------------
    def refrescar_lista_playlists(self, seleccionar: str = None):
        self._lista_playlists.delete(0, tk.END)
        nombres = playlist_store.listar_playlists()
        for nombre in nombres:
            self._lista_playlists.insert(tk.END, nombre)

        if seleccionar and seleccionar in nombres:
            indice = nombres.index(seleccionar)
            self._lista_playlists.selection_clear(0, tk.END)
            self._lista_playlists.selection_set(indice)
            self._mostrar_playlist(seleccionar)

    def _crear_playlist_nueva(self):
        nombre_nuevo = simpledialog.askstring(
            "Nueva Playlist", "Nombre de la nueva playlist:", parent=self,
        )
        if nombre_nuevo and nombre_nuevo.strip():
            nombre_nuevo = nombre_nuevo.strip()
            playlist_store.crear_playlist_si_no_existe(nombre_nuevo)
            self.refrescar_lista_playlists(seleccionar=nombre_nuevo)

    def _al_seleccionar_playlist(self, evento):
        seleccion = self._lista_playlists.curselection()
        if not seleccion:
            return
        nombre = self._lista_playlists.get(seleccion[0])
        self._mostrar_playlist(nombre)

    def _mostrar_playlist(self, nombre: str):
        self._playlist_seleccionada = nombre
        self.label_titulo_playlist.config(text=nombre)

        canciones = playlist_store.obtener_canciones(nombre)
        self.btn_reproducir_todo.state(["!disabled"] if canciones else ["disabled"])

        for hijo in self._frame_filas.winfo_children():
            hijo.destroy()

        if not canciones:
            tk.Label(
                self._frame_filas, text="Esta playlist no tiene canciones todavia.",
                font=FONT_NORMAL, bg=COLOR_FONDO, fg="#666666",
            ).pack(pady=16)
            return

        for indice, cancion in enumerate(canciones):
            color_fondo = COLOR_FILA_PAR if indice % 2 == 0 else COLOR_FILA_IMPAR
            self._crear_fila_cancion(cancion, indice, canciones, color_fondo)

    def _crear_fila_cancion(self, cancion, indice, lista_completa, color_fondo):
        fila = tk.Frame(self._frame_filas, bg=color_fondo)
        fila.pack(fill=tk.X, pady=1)

        tk.Label(
            fila, text=f"{cancion.titulo}  -  {cancion.artista} ({cancion.duracion})",
            font=FONT_NORMAL, bg=color_fondo, anchor="w", wraplength=340, justify="left",
        ).pack(side=tk.LEFT, padx=10, pady=8, fill=tk.X, expand=True)

        ttk.Button(
            fila, text="Reproducir", style="Accion.TButton", width=11,
            command=lambda: self._reproducir_desde(lista_completa, indice),
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            fila, text="Descargar", style="Accion.TButton", width=11,
            command=lambda: self._descargar(cancion),
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            fila, text="Quitar", style="Accion.TButton", width=9,
            command=lambda: self._quitar(cancion),
        ).pack(side=tk.LEFT, padx=10)

    # ------------------------------------------------------------
    def _reproducir_playlist_completa(self):
        canciones = playlist_store.obtener_canciones(self._playlist_seleccionada)
        self._reproducir_desde(canciones, 0)

    def _reproducir_desde(self, canciones, indice):
        cola = [
            {"titulo": c.titulo, "webpage_url": c.webpage_url}
            for c in canciones
        ]
        self._on_reproducir_playlist(cola, indice)

    def _descargar(self, cancion):
        from core.search import SearchResultItem
        item = SearchResultItem(
            video_id="", title=cancion.titulo, uploader=cancion.artista,
            duration_seconds=None, thumbnail_url=None, webpage_url=cancion.webpage_url,
        )
        self._on_descargar_cancion(item)

    def _quitar(self, cancion):
        if self._playlist_seleccionada:
            playlist_store.quitar_cancion(self._playlist_seleccionada, cancion.webpage_url)
            self._mostrar_playlist(self._playlist_seleccionada)
