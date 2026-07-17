"""
ui/bottom_bar.py

Barra inferior persistente de la ventana principal, igual que en el
mockup:
  - Fila de estado: texto grande a la izquierda para mensajes de
    actualizacion en background ("Actualizando yt-dlp...") y a la
    derecha el estado del USB ("Detectando USB..." / "Pendrive
    detectado" / "Sin pendrive conectado").
  - Fila de controles: Anterior | Play/Pausa | Siguiente | Volumen.

Mantiene una "cola" simple de reproduccion (lista de canciones) para
poder avanzar/retroceder, ya sea que la cola venga de una busqueda o
de una playlist.
"""

import threading
import tkinter as tk
from tkinter import ttk

from ui.theme import (
    FONT_ESTADO, FONT_NORMAL, FONT_BOTON,
    COLOR_BARRA_INFERIOR, COLOR_TEXTO, COLOR_ERROR,
)
from core import stream_resolver
from core.stream_resolver import StreamResolveError


class BottomBar(tk.Frame):
    def __init__(self, parent, audio_player, vlc_disponible: bool, mostrar_error_callback):
        super().__init__(parent, bg=COLOR_BARRA_INFERIOR)

        self._audio_player = audio_player
        self._vlc_disponible = vlc_disponible
        self._mostrar_error = mostrar_error_callback

        self._cola = []
        self._indice_actual = -1

        self._construir_ui()

    # ------------------------------------------------------------
    def _construir_ui(self):
        fila_estado = tk.Frame(self, bg="#f0f0f0")
        fila_estado.pack(fill=tk.X, side=tk.TOP)

        self.label_estado_actualizacion = tk.Label(
            fila_estado, text="", font=FONT_ESTADO, bg="#f0f0f0", fg=COLOR_TEXTO,
            anchor="w", padx=14, pady=6,
        )
        self.label_estado_actualizacion.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.label_usb = tk.Label(
            fila_estado, text="Detectando USB...", font=FONT_ESTADO,
            bg="#f0f0f0", fg=COLOR_TEXTO, anchor="e", padx=14, pady=6,
        )
        self.label_usb.pack(side=tk.RIGHT)

        fila_controles = tk.Frame(self, bg=COLOR_BARRA_INFERIOR)
        fila_controles.pack(fill=tk.X, pady=8)

        self.btn_anterior = ttk.Button(
            fila_controles, text="Anterior", style="Accion.TButton",
            width=12, command=self.anterior,
        )
        self.btn_anterior.pack(side=tk.LEFT, padx=14)

        self.btn_play_pausa = ttk.Button(
            fila_controles, text="Play/Pausa", style="Accion.TButton",
            width=12, command=self.alternar_play_pausa,
        )
        self.btn_play_pausa.pack(side=tk.LEFT, padx=6)

        self.btn_siguiente = ttk.Button(
            fila_controles, text="Siguiente", style="Accion.TButton",
            width=12, command=self.siguiente,
        )
        self.btn_siguiente.pack(side=tk.LEFT, padx=6)

        tk.Label(
            fila_controles, text="Volumen", font=FONT_NORMAL,
            bg=COLOR_BARRA_INFERIOR, fg=COLOR_TEXTO,
        ).pack(side=tk.LEFT, padx=24)

        self.slider_volumen = ttk.Scale(
            fila_controles, from_=0, to=100, orient=tk.HORIZONTAL,
            command=self._al_cambiar_volumen, length=220,
        )
        self.slider_volumen.set(80)
        self.slider_volumen.pack(side=tk.LEFT, padx=14)

        self.label_cancion_actual = tk.Label(
            fila_controles, text="", font=FONT_NORMAL, bg=COLOR_BARRA_INFERIOR,
            fg=COLOR_TEXTO, anchor="w",
        )
        self.label_cancion_actual.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        if self._audio_player:
            self._audio_player.set_volume(80)
        else:
            self.btn_anterior.state(["disabled"])
            self.btn_play_pausa.state(["disabled"])
            self.btn_siguiente.state(["disabled"])
            self.slider_volumen.state(["disabled"])

    # ------------------------------------------------------------
    def establecer_estado_actualizacion(self, texto: str):
        self.label_estado_actualizacion.config(text=texto)

    def establecer_estado_usb(self, texto: str):
        self.label_usb.config(text=texto)

    # ------------------------------------------------------------
    def _al_cambiar_volumen(self, valor_str):
        if self._audio_player:
            self._audio_player.set_volume(float(valor_str))

    # ------------------------------------------------------------
    # Manejo de cola de reproduccion
    # ------------------------------------------------------------
    def reproducir_cola(self, canciones: list, indice_inicio: int = 0):
        """
        canciones: lista de dicts con al menos 'titulo' y 'webpage_url'.
        Reemplaza la cola actual y comienza a reproducir desde indice_inicio.
        """
        if not self._vlc_disponible:
            self._mostrar_error(
                "No se puede reproducir: VLC no esta disponible en este equipo."
            )
            return
        if not canciones:
            return

        self._cola = canciones
        self._indice_actual = max(0, min(indice_inicio, len(canciones) - 1))
        self._reproducir_actual()

    def siguiente(self):
        if not self._cola:
            return
        if self._indice_actual + 1 < len(self._cola):
            self._indice_actual += 1
            self._reproducir_actual()

    def anterior(self):
        if not self._cola:
            return
        if self._indice_actual - 1 >= 0:
            self._indice_actual -= 1
            self._reproducir_actual()

    def alternar_play_pausa(self):
        if self._audio_player and self._audio_player.get_current_title():
            self._audio_player.toggle_play_pause()

    # ------------------------------------------------------------
    def _reproducir_actual(self):
        cancion = self._cola[self._indice_actual]
        titulo = cancion.get("titulo") or cancion.get("title") or "(sin titulo)"
        webpage_url = cancion.get("webpage_url")

        self.label_cancion_actual.config(text=f"Cargando: {titulo}...")
        self._deshabilitar_controles(True)

        hilo = threading.Thread(
            target=self._resolver_y_reproducir, args=(webpage_url, titulo), daemon=True,
        )
        hilo.start()

    def _resolver_y_reproducir(self, webpage_url: str, titulo: str):
        try:
            resuelto = stream_resolver.resolve_audio_stream(webpage_url)
        except StreamResolveError as exc:
            mensaje_error = str(exc)
            self.after(0, lambda: self._al_fallar_reproduccion(mensaje_error))
            return
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._al_fallar_reproduccion(
                "Ocurrio un error al preparar la cancion."
            ))
            return

        self.after(0, lambda: self._al_lograr_reproducir(resuelto.direct_url, titulo))

    def _al_lograr_reproducir(self, direct_url: str, titulo: str):
        try:
            self._audio_player.play_url(direct_url, titulo)
        except Exception:  # noqa: BLE001
            self._al_fallar_reproduccion(
                "VLC no pudo reproducir este audio. Prueba con otra cancion."
            )
            return
        self.label_cancion_actual.config(text=titulo)
        self._deshabilitar_controles(False)

    def _al_fallar_reproduccion(self, mensaje: str):
        self.label_cancion_actual.config(text="No se pudo reproducir.")
        self._deshabilitar_controles(False)
        self._mostrar_error(mensaje)

    def _deshabilitar_controles(self, deshabilitar: bool):
        estado = ["disabled"] if deshabilitar else ["!disabled"]
        for boton in (self.btn_anterior, self.btn_play_pausa, self.btn_siguiente):
            boton.state(estado)
