"""
core/error_helpers.py

Traduce excepciones de yt-dlp/red a mensajes en español aptos para
mostrar en texto grande en la UI, SIN esconder la causa real detras
de un generico "no hay internet" cuando el problema es otro (formato
no disponible, video privado, "please sign in", etc).

Solo se muestra el mensaje de conectividad cuando el texto de la
excepcion realmente corresponde a un fallo de red/DNS/timeout.
"""

_PALABRAS_CLAVE_CONEXION = (
    "failed to establish a new connection",
    "getaddrinfo failed",
    "name or service not known",
    "network is unreachable",
    "connection refused",
    "max retries exceeded",
    "timed out",
    "temporary failure in name resolution",
    "no address associated with hostname",
)

_LARGO_MAXIMO_MENSAJE = 260


def formatear_error_ytdlp(exc: Exception, contexto: str = "") -> str:
    """
    contexto: texto corto que se antepone, ej: "No se pudo cargar el video"
    Devuelve un mensaje en español que:
      - si es un problema de red real, lo dice claramente.
      - si es cualquier otro error de yt-dlp (formato, privado, "sign in",
        video eliminado, etc), muestra el motivo real (recortado) en vez
        de decir "revisa tu internet" a ciegas.
    """
    texto_original = str(exc)
    texto_minusculas = texto_original.lower()

    if any(clave in texto_minusculas for clave in _PALABRAS_CLAVE_CONEXION):
        return "No se pudo conectar a Internet. Revisa tu conexion e intenta de nuevo."

    mensaje_limpio = texto_original.replace("ERROR:", "").strip()
    if len(mensaje_limpio) > _LARGO_MAXIMO_MENSAJE:
        mensaje_limpio = mensaje_limpio[:_LARGO_MAXIMO_MENSAJE] + "..."

    if contexto:
        return f"{contexto}:\n{mensaje_limpio}"
    return mensaje_limpio
