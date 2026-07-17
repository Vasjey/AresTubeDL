"""
ui/theme.py

Constantes visuales compartidas por toda la interfaz, siguiendo el
estilo del mockup: botones grandes tipo Windows clasico (gris claro,
texto negro en negrita), fuentes grandes (13-16), alto contraste,
sin decoraciones innecesarias.
"""

import tkinter as tk
from tkinter import ttk

FONT_TITULO = ("Segoe UI", 16, "bold")
FONT_PESTANA = ("Segoe UI", 13, "bold")
FONT_NORMAL = ("Segoe UI", 13)
FONT_NORMAL_NEGRITA = ("Segoe UI", 13, "bold")
FONT_BOTON = ("Segoe UI", 13, "bold")
FONT_ENCABEZADO_TABLA = ("Segoe UI", 12, "bold")
FONT_ESTADO = ("Segoe UI", 13, "bold")

COLOR_FONDO = "#ffffff"
COLOR_FONDO_ENCABEZADO = "#e6e6e6"
COLOR_BARRA_INFERIOR = "#e6e6e6"
COLOR_BOTON = "#d9d9d9"
COLOR_BOTON_BORDE = "#9a9a9a"
COLOR_BOTON_ACCION = "#c9c9c9"  # BUSCAR / botones principales
COLOR_TEXTO = "#000000"
COLOR_TEXTO_SECUNDARIO = "#444444"
COLOR_FILA_PAR = "#ffffff"
COLOR_FILA_IMPAR = "#f4f4f4"
COLOR_ESTADO_TEXTO = "#1a1a1a"
COLOR_ERROR = "#b00020"


def aplicar_estilo(root: tk.Tk):
    """Configura ttk con un tema simple, plano y de alto contraste."""
    estilo = ttk.Style(root)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    estilo.configure("TNotebook", background=COLOR_FONDO, borderwidth=0)
    estilo.configure(
        "TNotebook.Tab",
        font=FONT_PESTANA,
        padding=(18, 10),
    )

    estilo.configure(
        "Accion.TButton",
        font=FONT_BOTON,
        padding=(10, 8),
        background=COLOR_BOTON,
        foreground=COLOR_TEXTO,
        borderwidth=1,
    )
    estilo.map(
        "Accion.TButton",
        background=[("active", "#c0c0c0"), ("disabled", "#f0f0f0")],
        foreground=[("disabled", "#a0a0a0")],
    )

    estilo.configure(
        "Volumen.Horizontal.TScale",
        background=COLOR_BARRA_INFERIOR,
    )

    root.configure(bg=COLOR_FONDO)


def boton_grande(parent, texto, comando, ancho=16, style="Accion.TButton"):
    return ttk.Button(parent, text=texto, command=comando, width=ancho, style=style)
