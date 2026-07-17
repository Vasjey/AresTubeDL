"""
core/video_player.py

Ventana de VIDEO nativa e independiente (Toplevel de tkinter), NO en el
navegador. Embebe la salida de video de VLC directamente en un Frame
de tkinter usando el handle de ventana (HWND en Windows).

Controles incluidos (accesibles, texto/botones grandes):
  - Play / Pausa
  - Retroceder 10s / Adelantar 10s
  - Barra de progreso (Scale) arrastrable para saltar a cualquier punto
  - Etiqueta de tiempo "MM:SS / MM:SS"
  - Doble clic sobre el video -> Pantalla completa (doble clic de nuevo
    para volver a ventana normal)

Uso desde la UI principal (Fase 4):

    ok, vlc_module, err = vlc_check.try_load_vlc()
    if ok:
        resuelto = stream_resolver.resolve_video_stream(webpage_url)
        ventana = VideoPlayerWindow(root, vlc_module)
        ventana.play_url(resuelto.direct_url, resuelto.title)
    else:
        mostrar_mensaje_grande(err)
"""

import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger("video_player")

FONT_GRANDE = ("Segoe UI", 13)
FONT_BOTON = ("Segoe UI", 13, "bold")
COLOR_FONDO = "#1c1c1c"
COLOR_CONTROLES = "#2b2b2b"
COLOR_TEXTO = "#ffffff"
COLOR_BOTON = "#3a7bd5"


def _formatear_tiempo(segundos: float) -> str:
    segundos = max(0, int(segundos))
    minutos, seg = divmod(segundos, 60)
    return f"{minutos:02d}:{seg:02d}"


class VideoPlayerWindow(tk.Toplevel):
    def __init__(self, parent, vlc_module, ancho=900, alto=560):
        super().__init__(parent)
        self.title("Reproduciendo video")
        self.geometry(f"{ancho}x{alto}")
        self.configure(bg=COLOR_FONDO)
        self.minsize(480, 320)

        self._vlc = vlc_module
        self._instance = vlc_module.Instance("--network-caching=1500")
        self._player = self._instance.media_player_new()

        self._es_pantalla_completa = False
        self._usuario_arrastrando_barra = False
        self._duracion_segundos = 0.0
        self._after_id = None

        self._construir_ui()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        # Empieza a actualizar la barra de progreso periodicamente
        self._ciclo_actualizacion()

    # ------------------------------------------------------------
    # Construccion de la interfaz
    # ------------------------------------------------------------
    def _construir_ui(self):
        # Area de video (aqui se embebe la salida de VLC)
        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        self.video_frame.bind("<Double-Button-1>", self._alternar_pantalla_completa)

        # Barra de controles inferior
        controles = tk.Frame(self, bg=COLOR_CONTROLES, height=90)
        controles.pack(fill=tk.X, side=tk.BOTTOM)
        controles.pack_propagate(False)

        fila_botones = tk.Frame(controles, bg=COLOR_CONTROLES)
        fila_botones.pack(pady=6)

        self.btn_retroceder = tk.Button(
            fila_botones, text="<< 10s", font=FONT_BOTON,
            bg=COLOR_BOTON, fg="white", width=8, height=1,
            command=self._retroceder_10s,
        )
        self.btn_retroceder.pack(side=tk.LEFT, padx=6)

        self.btn_play_pausa = tk.Button(
            fila_botones, text="Pausa", font=FONT_BOTON,
            bg=COLOR_BOTON, fg="white", width=10, height=1,
            command=self._alternar_play_pausa,
        )
        self.btn_play_pausa.pack(side=tk.LEFT, padx=6)

        self.btn_adelantar = tk.Button(
            fila_botones, text="10s >>", font=FONT_BOTON,
            bg=COLOR_BOTON, fg="white", width=8, height=1,
            command=self._adelantar_10s,
        )
        self.btn_adelantar.pack(side=tk.LEFT, padx=6)

        self.btn_pantalla_completa = tk.Button(
            fila_botones, text="Pantalla completa", font=FONT_BOTON,
            bg=COLOR_BOTON, fg="white", width=16, height=1,
            command=self._alternar_pantalla_completa,
        )
        self.btn_pantalla_completa.pack(side=tk.LEFT, padx=6)

        # Barra de progreso + tiempos
        fila_progreso = tk.Frame(controles, bg=COLOR_CONTROLES)
        fila_progreso.pack(fill=tk.X, padx=12, pady=8)

        self.label_tiempo = tk.Label(
            fila_progreso, text="00:00 / 00:00", font=FONT_GRANDE,
            bg=COLOR_CONTROLES, fg=COLOR_TEXTO, width=13,
        )
        self.label_tiempo.pack(side=tk.RIGHT, padx=8)

        self.barra_progreso = ttk.Scale(
            fila_progreso, from_=0, to=1000, orient=tk.HORIZONTAL,
        )
        self.barra_progreso.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.barra_progreso.bind("<ButtonPress-1>", self._inicio_arrastre)
        self.barra_progreso.bind("<ButtonRelease-1>", self._fin_arrastre)

        # Atajo: Escape sale de pantalla completa
        self.bind("<Escape>", lambda e: self._salir_pantalla_completa())

    # ------------------------------------------------------------
    # Reproduccion
    # ------------------------------------------------------------
    def play_url(self, direct_url: str, titulo: str = ""):
        try:
            media = self._instance.media_new(direct_url)
            self._player.set_media(media)

            # Embeber la salida de video en el Frame de tkinter (Windows)
            self.update_idletasks()
            self._player.set_hwnd(self.video_frame.winfo_id())

            self._player.play()
        except Exception:
            logger.exception("Error al reproducir video con VLC (url=%s)", direct_url)
            raise

        self.btn_play_pausa.config(text="Pausa")
        if titulo:
            self.title(f"Reproduciendo: {titulo}")

    def _alternar_play_pausa(self):
        if self._player.is_playing():
            self._player.pause()
            self.btn_play_pausa.config(text="Reproducir")
        else:
            self._player.play()
            self.btn_play_pausa.config(text="Pausa")

    def _retroceder_10s(self):
        self._saltar_segundos(-10)

    def _adelantar_10s(self):
        self._saltar_segundos(10)

    def _saltar_segundos(self, delta_segundos: int):
        actual_ms = self._player.get_time()
        if actual_ms is None or actual_ms < 0:
            return
        nuevo_ms = max(0, actual_ms + delta_segundos * 1000)
        self._player.set_time(int(nuevo_ms))

    # ------------------------------------------------------------
    # Barra de progreso arrastrable
    # ------------------------------------------------------------
    def _inicio_arrastre(self, evento):
        self._usuario_arrastrando_barra = True

    def _fin_arrastre(self, evento):
        self._usuario_arrastrando_barra = False
        if self._duracion_segundos > 0:
            fraccion = self.barra_progreso.get() / 1000.0
            nuevo_ms = int(fraccion * self._duracion_segundos * 1000)
            self._player.set_time(nuevo_ms)

    # ------------------------------------------------------------
    # Pantalla completa
    # ------------------------------------------------------------
    def _alternar_pantalla_completa(self, evento=None):
        self._es_pantalla_completa = not self._es_pantalla_completa
        self.attributes("-fullscreen", self._es_pantalla_completa)

    def _salir_pantalla_completa(self):
        if self._es_pantalla_completa:
            self._es_pantalla_completa = False
            self.attributes("-fullscreen", False)

    # ------------------------------------------------------------
    # Ciclo periodico de actualizacion (tiempo + barra de progreso)
    # ------------------------------------------------------------
    def _ciclo_actualizacion(self):
        try:
            duracion_ms = self._player.get_length()
            posicion_ms = self._player.get_time()

            if duracion_ms and duracion_ms > 0:
                self._duracion_segundos = duracion_ms / 1000.0

            if not self._usuario_arrastrando_barra and duracion_ms and duracion_ms > 0:
                fraccion = max(0.0, min(1.0, (posicion_ms or 0) / duracion_ms))
                self.barra_progreso.set(fraccion * 1000)

            self.label_tiempo.config(
                text=f"{_formatear_tiempo((posicion_ms or 0) / 1000)} / "
                     f"{_formatear_tiempo(self._duracion_segundos)}"
            )

            # Si el video termino, refleja "Reproducir" en el boton
            estado = self._player.get_state()
            if estado == self._vlc.State.Ended:
                self.btn_play_pausa.config(text="Reproducir")

        except Exception:  # noqa: BLE001
            logger.warning("Error en ciclo de actualizacion del video", exc_info=True)

        self._after_id = self.after(500, self._ciclo_actualizacion)

    # ------------------------------------------------------------
    # Cierre ordenado
    # ------------------------------------------------------------
    def _al_cerrar(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:  # noqa: BLE001
                pass
        try:
            self._player.stop()
            self._player.release()
            self._instance.release()
        except Exception:  # noqa: BLE001
            logger.warning("Error liberando recursos de video_player", exc_info=True)
        self.destroy()
