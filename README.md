# YoutubeSeniorApp — Fase 1: Estructura y Auto-actualización

## Perfil de usuario objetivo
- Adulto mayor, PC antigua con **Windows 7 de 32 bits**.
- **Python 3.8.10** (última versión oficial con instalador para Win7).
- Requiere UI ultra simple, fuentes grandes, sin navegador de por medio.
- Debe poder buscar, **reproducir video en ventana nativa VLC**, reproducir
  **solo audio en la barra inferior**, descargar a MP3/MP4, detectar USB,
  e importar playlists desde `.txt`.

## Estructura de carpetas

```
YoutubeSeniorApp/
├── main.py                    # Punto de entrada (Fase 4)
├── version.py                 # Versión actual de la app (usada por el auto-updater)
├── config.py                  # Rutas, constantes, carpeta de descargas (Fase 3)
├── requirements.txt           # Dependencias compatibles con Win7 32-bit / Py 3.8.10
├── build_exe.bat               # Script de referencia para empaquetar con PyInstaller
├── updater/
│   ├── __init__.py
│   ├── app_updater.py         # Auto-actualización de la APP desde GitHub Releases
│   └── pytubefix_updater.py    # Actualización silenciosa de pytubefix
├── core/                      # (Fase 2) búsqueda, reproducción VLC
├── downloads/                 # (Fase 3) lógica de descarga, USB, importación TXT
├── ui/                        # (Fase 4) tkinter
└── assets/
    └── icon.ico                # Ícono de la app (agregar manualmente)
```

## Por qué esta arquitectura

1. **`version.py` como fuente única de verdad**: un simple string
   `APP_VERSION = "1.0.0"` que se compara contra la última release de GitHub.
   Así el updater no depende de parsear el `.exe` ni nada frágil.

2. **Reemplazo de ejecutable en caliente (Windows)**: en Windows no se puede
   sobrescribir un `.exe` que está corriendo. La solución estándar es:
   - Descargar la nueva versión como `app_new.exe` (o `main_new.py` si se
     distribuye como script).
   - Generar un pequeño **script `.bat`** que:
     a) espera a que el proceso actual termine,
     b) borra el `.exe` viejo,
     c) renombra el nuevo,
     d) vuelve a lanzar la app.
   - La app actual se cierra y lanza ese `.bat` con `subprocess.Popen` +
     `DETACHED_PROCESS`, y termina su propio proceso.
   - Esto se maneja igual si distribuyes `.py` en vez de `.exe` (incluí ambos
     casos en `app_updater.py`).

3. **La extracción de YouTube usa `pytubefix`, no `yt-dlp`**: se migró
   porque yt-dlp (oficial y sus forks) dejó de poder instalarse o
   funcionar en Python 3.8 / Windows 7. `pytubefix` es una librería
   100% Python puro con soporte oficial para Python 3.7+, y se
   actualiza sola vía pip (`pip install -U pytubefix`), cubierto en
   `pytubefix_updater.py`. La conversión a MP3 real sigue necesitando
   `ffmpeg` por separado (pytubefix no recodifica audio).

4. **Todo el chequeo de actualizaciones ocurre en background threads** al
   arrancar `main.py`, para que la ventana aparezca de inmediato (crítico
   para UX de adultos mayores: nunca dejar la pantalla "congelada" sin texto).

## Nota importante sobre compatibilidad Win7 32-bit

- `pytubefix` es un proyecto activo que se actualiza seguido para seguirle
  el paso a los cambios de YouTube. A diferencia de yt-dlp, es 100% Python
  puro (sin binarios nativos), así que no hay riesgo de incompatibilidad
  de versión de Python al actualizarlo - se deja sin fijar en
  `requirements.txt` a propósito, y se autoactualiza vía pip al iniciar.
- `python-vlc` NO trae VLC embebido: en la PC del usuario debe estar
  instalado **VLC de 32 bits** (mismo bitness que Python). Esto se valida
  en Fase 2 con un mensaje claro en texto grande si no lo encuentra.
