"""
core/audio_player.py

Reproductor de SOLO AUDIO, pensado para controlarse desde la barra
inferior de la ventana principal (Fase 4): Anterior / Play-Pausa /
Siguiente / Volumen.

No abre ninguna ventana propia: solo maneja el motor de audio VLC.
La UI (Fase 4) es responsable de:
  - Llamar a play_url() cuando el usuario aprieta "Reproducir" en la
    lista de resultados (usando la URL directa que entrega
    stream_resolver.resolve_audio_stream).
  - Actualizar un Label con el titulo / tiempo transcurrido usando
    get_position_seconds() y get_duration_seconds() en un ciclo
    root.after(...).
"""

import logging
from typing import Optional

logger = logging.getLogger("audio_player")


class AudioPlayer:
    def __init__(self, vlc_module):
        """
        vlc_module: el modulo `vlc` ya validado por vlc_check.try_load_vlc().
        Se pasa como parametro (en vez de importar aqui) para que la app
        pueda arrancar aunque VLC no este disponible, sin crashear al
        importar este archivo.
        """
        self._vlc = vlc_module
        # --no-video: fuerza modo audio.
        # --network-caching: buffer de 1.5s para tolerar redes/discos
        # lentos sin que el audio se corte o falle al abrir el stream.
        self._instance = vlc_module.Instance("--no-video", "--network-caching=1500")
        self._player = self._instance.media_player_new()
        self._current_title: Optional[str] = None

    def play_url(self, direct_url: str, title: str = ""):
        try:
            media = self._instance.media_new(direct_url)
            self._player.set_media(media)
            self._player.play()
            self._current_title = title
        except Exception:  # noqa: BLE001
            logger.exception("Error al reproducir audio con VLC (url=%s)", direct_url)
            self._current_title = None
            raise

    def toggle_play_pause(self):
        if self._player.is_playing():
            self._player.pause()
        else:
            self._player.play()

    def stop(self):
        self._player.stop()
        self._current_title = None

    def set_volume(self, volumen_0_a_100: int):
        volumen_0_a_100 = max(0, min(100, int(volumen_0_a_100)))
        self._player.audio_set_volume(volumen_0_a_100)

    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    def get_current_title(self) -> Optional[str]:
        return self._current_title

    def get_position_seconds(self) -> float:
        """Tiempo transcurrido en segundos (0 si no hay media cargada)."""
        ms = self._player.get_time()
        return max(0.0, ms / 1000.0) if ms is not None and ms >= 0 else 0.0

    def get_duration_seconds(self) -> float:
        ms = self._player.get_length()
        return max(0.0, ms / 1000.0) if ms is not None and ms >= 0 else 0.0

    def release(self):
        """Liberar recursos VLC al cerrar la app."""
        try:
            self._player.stop()
            self._player.release()
            self._instance.release()
        except Exception:  # noqa: BLE001
            logger.warning("Error liberando recursos de audio_player", exc_info=True)
