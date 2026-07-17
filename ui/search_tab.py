"""
ui/search_tab.py

Pestaña "BUSQUEDA": entrada de texto, boton BUSCAR, y una lista de
resultados con fila por cancion. Cada fila tiene:
  - Titulo / Artista / Duracion
  - REPRODUCIR (audio, en la barra inferior)
  - VER VIDEO (ventana nativa VLC aparte)
  - DESCARGAR (MP3)
  - + PLAYLIST (agregar a una playlist existente o nueva)

Las miniaturas SI se descargan y muestran (ver core/thumbnail_loader.py,
que usa Pillow para decodificar JPEG/WebP). Mientras se descargan, la
columna CARATULA muestra un icono de nota musical como marcador
temporal; si la descarga falla (sin internet, formato raro), se queda
con ese icono en vez de romper la fila.
"""

import threading
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from ui.theme import (
    FONT_NORMAL, FONT_NORMAL_NEGRITA, FONT_ENCABEZADO_TABLA,
    COLOR_FONDO, COLOR_FONDO_ENCABEZADO, COLOR_FILA_PAR, COLOR_FILA_IMPAR,
    COLOR_TEXTO,
)
from core.search import search_youtube, SearchError, SearchResultItem
from core.thumbnail_loader import descargar_miniatura_pil

ANCHO_MINIATURA = 56
ALTO_MINIATURA = 42


class SearchTab(tk.Frame):
    def __init__(
        self,
        parent,
        on_reproducir_audio,
        on_reproducir_video,
        on_descargar,
        on_agregar_playlist,
        on_mostrar_error,
    ):
        super().__init__(parent, bg=COLOR_FONDO)

        self._on_reproducir_audio = on_reproducir_audio
        self._on_reproducir_video = on_reproducir_video
        self._on_descargar = on_descargar
        self._on_agregar_playlist = on_agregar_playlist
        self._on_mostrar_error = on_mostrar_error

        self._resultados_actuales: list[SearchResultItem] = []
        self._imagenes_referencia = []  # evita que Tkinter libere las PhotoImage

        self._construir_ui()

    # ------------------------------------------------------------
    def _construir_ui(self):
        fila_busqueda = tk.Frame(self, bg=COLOR_FONDO)
        fila_busqueda.pack(fill=tk.X, padx=16, pady=14)

        self.entry_busqueda = tk.Entry(fila_busqueda, font=FONT_NORMAL)
        self.entry_busqueda.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.entry_busqueda.bind("<Return>", lambda e: self._iniciar_busqueda())
        self.entry_busqueda.insert(0, "")
        self._colocar_placeholder()

        self.btn_buscar = ttk.Button(
            fila_busqueda, text="BUSCAR", style="Accion.TButton",
            width=12, command=self._iniciar_busqueda,
        )
        self.btn_buscar.pack(side=tk.LEFT, padx=10)

        self.label_estado_busqueda = tk.Label(
            self, text="", font=FONT_NORMAL, bg=COLOR_FONDO, fg="#b00020",
        )
        self.label_estado_busqueda.pack(fill=tk.X, padx=16)

        # Encabezado de la tabla
        encabezado = tk.Frame(self, bg=COLOR_FONDO_ENCABEZADO)
        encabezado.pack(fill=tk.X, padx=16)
        tk.Label(encabezado, text="", width=6, bg=COLOR_FONDO_ENCABEZADO).pack(side=tk.LEFT)
        tk.Label(
            encabezado, text="TITULO", font=FONT_ENCABEZADO_TABLA,
            bg=COLOR_FONDO_ENCABEZADO, width=28, anchor="w",
        ).pack(side=tk.LEFT, padx=4)
        tk.Label(
            encabezado, text="ARTISTA", font=FONT_ENCABEZADO_TABLA,
            bg=COLOR_FONDO_ENCABEZADO, width=16, anchor="w",
        ).pack(side=tk.LEFT, padx=4)
        tk.Label(
            encabezado, text="DURACION", font=FONT_ENCABEZADO_TABLA,
            bg=COLOR_FONDO_ENCABEZADO, width=9, anchor="w",
        ).pack(side=tk.LEFT, padx=4)
        tk.Label(
            encabezado, text="ACCIONES", font=FONT_ENCABEZADO_TABLA,
            bg=COLOR_FONDO_ENCABEZADO, anchor="w",
        ).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        # Area con scroll para las filas de resultados
        contenedor = tk.Frame(self, bg=COLOR_FONDO)
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

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
        self._canvas.bind_all("<MouseWheel>", self._al_rueda_mouse)

    def _al_rueda_mouse(self, evento):
        self._canvas.yview_scroll(int(-1 * (evento.delta / 120)), "units")

    def _colocar_placeholder(self):
        self.entry_busqueda.config(fg="#888888")
        self.entry_busqueda.insert(0, "Buscar canciones, artistas, bandas...")

        def al_foco_entrar(evento):
            if self.entry_busqueda.get() == "Buscar canciones, artistas, bandas...":
                self.entry_busqueda.delete(0, tk.END)
                self.entry_busqueda.config(fg="#000000")

        self.entry_busqueda.bind("<FocusIn>", al_foco_entrar)

    # ------------------------------------------------------------
    def _iniciar_busqueda(self):
        consulta = self.entry_busqueda.get().strip()
        if not consulta or consulta == "Buscar canciones, artistas, bandas...":
            self.label_estado_busqueda.config(text="Escribe algo para buscar.")
            return

        self.btn_buscar.state(["disabled"])
        self.label_estado_busqueda.config(text="Buscando...", fg="#000000")
        self._limpiar_resultados()

        hilo = threading.Thread(target=self._buscar_en_hilo, args=(consulta,), daemon=True)
        hilo.start()

    def _buscar_en_hilo(self, consulta: str):
        try:
            resultados = search_youtube(consulta, max_results=15)
        except SearchError as exc:
            mensaje_error = str(exc)
            self.after(0, lambda: self._al_fallar_busqueda(mensaje_error))
            return
        except Exception:  # noqa: BLE001
            self.after(0, lambda: self._al_fallar_busqueda(
                "Ocurrio un error al buscar. Intenta de nuevo."
            ))
            return

        self.after(0, lambda: self._al_lograr_busqueda(resultados))

    def _al_fallar_busqueda(self, mensaje: str):
        self.btn_buscar.state(["!disabled"])
        self.label_estado_busqueda.config(text=mensaje, fg="#b00020")

    def _al_lograr_busqueda(self, resultados: list):
        self.btn_buscar.state(["!disabled"])
        self.label_estado_busqueda.config(text="")
        self._resultados_actuales = resultados
        self._mostrar_resultados(resultados)

    # ------------------------------------------------------------
    def _limpiar_resultados(self):
        for hijo in self._frame_filas.winfo_children():
            hijo.destroy()
        self._imagenes_referencia.clear()

    def _mostrar_resultados(self, resultados: list):
        self._limpiar_resultados()

        for indice, item in enumerate(resultados):
            color_fondo = COLOR_FILA_PAR if indice % 2 == 0 else COLOR_FILA_IMPAR
            self._crear_fila(item, indice, color_fondo)

    def _cargar_miniatura_en_hilo(self, url: str, label_destino: tk.Label):
        imagen_pil = descargar_miniatura_pil(url, ANCHO_MINIATURA, ALTO_MINIATURA)
        if imagen_pil is None:
            return  # se queda con el icono de nota musical por defecto
        self.after(0, lambda: self._aplicar_miniatura(label_destino, imagen_pil))

    def _aplicar_miniatura(self, label_destino: tk.Label, imagen_pil):
        # La fila pudo haber sido destruida (nueva busqueda) mientras
        # se descargaba la miniatura; si es asi, simplemente se ignora.
        if not label_destino.winfo_exists():
            return
        try:
            foto = ImageTk.PhotoImage(imagen_pil)
        except Exception:  # noqa: BLE001
            return
        self._imagenes_referencia.append(foto)  # evita garbage collection
        label_destino.config(image=foto, text="")
        label_destino.image = foto

    def _crear_fila(self, item: SearchResultItem, indice: int, color_fondo: str):
        fila = tk.Frame(self._frame_filas, bg=color_fondo)
        fila.pack(fill=tk.X, pady=1)

        # IMPORTANTE: el recuadro de la miniatura se fija con un Frame
        # de tamaño en PIXELES (pack_propagate(False)), en vez de usar
        # el "width" del propio Label. Si el Label tiene width=N (en
        # caracteres, para el icono de texto) y despues se le asigna
        # una imagen, Tk reinterpreta ese mismo "width" como PIXELES,
        # aplastando la miniatura a un recuadro angosto (el bug de las
        # "barras verticales" deformadas). Al fijar el tamaño en un
        # Frame contenedor aparte, el Label queda libre para mostrar
        # texto o imagen sin que su "width" interfiera.
        contenedor_caratula = tk.Frame(
            fila, bg=color_fondo, width=ANCHO_MINIATURA, height=ALTO_MINIATURA,
        )
        contenedor_caratula.pack(side=tk.LEFT, padx=6)
        contenedor_caratula.pack_propagate(False)

        label_caratula = tk.Label(
            contenedor_caratula, text="\U0001F3B5", font=("Segoe UI", 18), bg=color_fondo,
        )
        label_caratula.pack(expand=True)

        if item.thumbnail_url:
            hilo_miniatura = threading.Thread(
                target=self._cargar_miniatura_en_hilo,
                args=(item.thumbnail_url, label_caratula),
                daemon=True,
            )
            hilo_miniatura.start()

        tk.Label(
            fila, text=item.title, font=FONT_NORMAL_NEGRITA, bg=color_fondo,
            fg=COLOR_TEXTO, width=28, anchor="w", wraplength=230, justify="left",
        ).pack(side=tk.LEFT, padx=4, pady=6)

        tk.Label(
            fila, text=item.uploader, font=FONT_NORMAL, bg=color_fondo,
            fg=COLOR_TEXTO, width=16, anchor="w",
        ).pack(side=tk.LEFT, padx=4)

        tk.Label(
            fila, text=item.duration_formatted, font=FONT_NORMAL, bg=color_fondo,
            fg=COLOR_TEXTO, width=9, anchor="w",
        ).pack(side=tk.LEFT, padx=4)

        acciones = tk.Frame(fila, bg=color_fondo)
        acciones.pack(side=tk.LEFT, padx=4, pady=6, fill=tk.X, expand=True)

        fila_botones_1 = tk.Frame(acciones, bg=color_fondo)
        fila_botones_1.pack(anchor="w")
        fila_botones_2 = tk.Frame(acciones, bg=color_fondo)
        fila_botones_2.pack(anchor="w", pady=4)

        ttk.Button(
            fila_botones_1, text="REPRODUCIR", style="Accion.TButton", width=13,
            command=lambda: self._on_reproducir_audio(self._resultados_actuales, indice),
        ).pack(side=tk.LEFT, padx=6)

        ttk.Button(
            fila_botones_1, text="VER VIDEO", style="Accion.TButton", width=12,
            command=lambda: self._on_reproducir_video(item.webpage_url, item.title),
        ).pack(side=tk.LEFT)

        ttk.Button(
            fila_botones_2, text="DESCARGAR", style="Accion.TButton", width=13,
            command=lambda: self._on_descargar(item),
        ).pack(side=tk.LEFT, padx=6)

        ttk.Button(
            fila_botones_2, text="+ PLAYLIST", style="Accion.TButton", width=12,
            command=lambda: self._on_agregar_playlist(item),
        ).pack(side=tk.LEFT)
