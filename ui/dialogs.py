"""
ui/dialogs.py

Ventanas emergentes simples y reutilizables, todas con texto grande
y botones grandes, pensadas para un adulto mayor:
  - mostrar_mensaje(): error/info generico.
  - preguntar_usb_o_computador(): "¿Guardar en Pendrive o en el Computador?"
  - elegir_o_crear_playlist(): para el boton "Agregar a Playlist".
"""

import tkinter as tk
from tkinter import ttk, simpledialog

from ui.theme import FONT_NORMAL, FONT_BOTON, boton_grande
from core import playlist_store


def mostrar_mensaje(parent, titulo: str, texto: str, es_error: bool = False):
    ventana = tk.Toplevel(parent)
    ventana.title(titulo)
    ventana.configure(bg="#ffffff")
    ventana.resizable(False, False)
    ventana.grab_set()

    color_texto = "#b00020" if es_error else "#000000"
    tk.Label(
        ventana, text=texto, font=FONT_NORMAL, fg=color_texto, bg="#ffffff",
        wraplength=380, justify="left", padx=20, pady=20,
    ).pack()

    ttk.Button(
        ventana, text="Aceptar", command=ventana.destroy, style="Accion.TButton",
    ).pack(pady=18)

    ventana.transient(parent)
    ventana.update_idletasks()
    ventana.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")


def preguntar_usb_o_computador(parent) -> str:
    """
    Muestra el dialogo de destino y BLOQUEA hasta que el usuario elija.
    Devuelve "usb" o "computador".
    """
    resultado = {"valor": "computador"}
    ventana = tk.Toplevel(parent)
    ventana.title("¿Dónde guardar?")
    ventana.configure(bg="#ffffff")
    ventana.resizable(False, False)
    ventana.grab_set()

    tk.Label(
        ventana,
        text="Se detectó un Pendrive conectado.\n\n¿Guardar en el Pendrive o en el Computador?",
        font=FONT_NORMAL, bg="#ffffff", wraplength=380, justify="center",
        padx=24, pady=20,
    ).pack()

    fila = tk.Frame(ventana, bg="#ffffff")
    fila.pack(pady=20)

    def elegir(valor):
        resultado["valor"] = valor
        ventana.destroy()

    ttk.Button(
        fila, text="Pendrive", width=14, style="Accion.TButton",
        command=lambda: elegir("usb"),
    ).pack(side=tk.LEFT, padx=10)

    ttk.Button(
        fila, text="Computador", width=14, style="Accion.TButton",
        command=lambda: elegir("computador"),
    ).pack(side=tk.LEFT, padx=10)

    ventana.transient(parent)
    ventana.update_idletasks()
    ventana.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")
    parent.wait_window(ventana)

    return resultado["valor"]


def elegir_o_crear_playlist(parent) -> "str | None":
    """
    Dialogo para elegir una playlist existente o crear una nueva,
    usado por el boton "Agregar a Playlist" en resultados de busqueda.
    Devuelve el nombre elegido/creado, o None si el usuario cancelo.
    """
    resultado = {"valor": None}
    ventana = tk.Toplevel(parent)
    ventana.title("Agregar a Playlist")
    ventana.configure(bg="#ffffff")
    ventana.resizable(False, False)
    ventana.grab_set()

    tk.Label(
        ventana, text="Elige una playlist:", font=FONT_NORMAL, bg="#ffffff",
        padx=20,
    ).pack(anchor="w", pady=20)

    playlists_existentes = playlist_store.listar_playlists()

    lista = tk.Listbox(
        ventana, font=FONT_NORMAL, height=6, width=32,
        exportselection=False,
    )
    for nombre in playlists_existentes:
        lista.insert(tk.END, nombre)
    lista.pack(padx=20, pady=10)

    def confirmar_existente():
        seleccion = lista.curselection()
        if seleccion:
            resultado["valor"] = lista.get(seleccion[0])
            ventana.destroy()
        else:
            mostrar_mensaje(ventana, "Aviso", "Selecciona una playlist de la lista.")

    def crear_nueva():
        nombre_nuevo = simpledialog.askstring(
            "Nueva Playlist", "Nombre de la nueva playlist:", parent=ventana,
        )
        if nombre_nuevo and nombre_nuevo.strip():
            resultado["valor"] = nombre_nuevo.strip()
            ventana.destroy()

    fila_botones = tk.Frame(ventana, bg="#ffffff")
    fila_botones.pack(pady=20)

    ttk.Button(
        fila_botones, text="Usar esta Playlist", style="Accion.TButton",
        command=confirmar_existente, width=18,
    ).pack(side=tk.LEFT, padx=8)

    ttk.Button(
        fila_botones, text="Crear Nueva...", style="Accion.TButton",
        command=crear_nueva, width=14,
    ).pack(side=tk.LEFT, padx=8)

    ventana.transient(parent)
    ventana.update_idletasks()
    ventana.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")
    parent.wait_window(ventana)

    return resultado["valor"]
