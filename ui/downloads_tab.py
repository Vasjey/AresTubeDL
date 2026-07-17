"""
ui/downloads_tab.py

Pestaña "DESCARGAS": muestra el historial de canciones descargadas
durante esta sesion (titulo + carpeta destino), con un boton para
abrir la carpeta donde quedo guardado el archivo.

El estado en vivo de una descarga en curso ("Descargando... 42%",
"Convirtiendo a MP3... Por favor espere") se muestra en la barra de
estado inferior (bottom_bar), no aqui; esta pestaña solo lleva el
registro de lo ya completado.
"""

import os
import subprocess
import tkinter as tk
from tkinter import ttk

from ui.theme import FONT_NORMAL, FONT_NORMAL_NEGRITA, COLOR_FONDO, COLOR_FILA_PAR, COLOR_FILA_IMPAR


class DownloadsTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=COLOR_FONDO)
        self._contador_filas = 0
        self._construir_ui()

    def _construir_ui(self):
        tk.Label(
            self, text="Canciones descargadas en esta sesion",
            font=FONT_NORMAL_NEGRITA, bg=COLOR_FONDO,
        ).pack(anchor="w", padx=16, pady=14)

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

        self.label_vacio = tk.Label(
            self._frame_filas, text="Aun no has descargado ninguna cancion.",
            font=FONT_NORMAL, bg=COLOR_FONDO, fg="#666666",
        )
        self.label_vacio.pack(pady=20)

    def agregar_descarga_completada(self, titulo: str, ruta_archivo: str):
        if self.label_vacio.winfo_exists():
            self.label_vacio.destroy()

        color_fondo = COLOR_FILA_PAR if self._contador_filas % 2 == 0 else COLOR_FILA_IMPAR
        self._contador_filas += 1

        fila = tk.Frame(self._frame_filas, bg=color_fondo)
        fila.pack(fill=tk.X, pady=1)

        tk.Label(
            fila, text=titulo, font=FONT_NORMAL, bg=color_fondo, width=40,
            anchor="w", wraplength=380, justify="left",
        ).pack(side=tk.LEFT, padx=10, pady=8)

        ttk.Button(
            fila, text="Abrir Carpeta", style="Accion.TButton", width=14,
            command=lambda: self._abrir_carpeta(ruta_archivo),
        ).pack(side=tk.RIGHT, padx=10)

    @staticmethod
    def _abrir_carpeta(ruta_archivo: str):
        carpeta = os.path.dirname(ruta_archivo)
        try:
            os.startfile(carpeta)  # Windows
        except AttributeError:
            subprocess.Popen(["xdg-open", carpeta])  # fallback no-Windows
        except OSError:
            pass
