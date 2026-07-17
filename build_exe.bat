@echo off
REM ============================================================
REM build_exe.bat
REM Empaqueta la app como un unico .exe de 32 bits para Windows 7.
REM Debe ejecutarse DENTRO de un Python 3.8.10 de 32 bits
REM (instala el Python de 32 bits, no el de 64, o el .exe resultante
REM no correra en un Windows 7 de 32 bits).
REM ============================================================

pyinstaller --noconfirm --onefile --windowed ^
    --name "AresYT" ^
    --icon "assets\icon.ico" ^
    main.py

echo.
echo Listo. El ejecutable queda en dist\AresYT.exe
echo.
echo IMPORTANTE: copia la carpeta "ffmpeg" (con ffmpeg.exe de 32 bits
echo dentro) junto a dist\AresYT.exe antes de distribuir. Sin eso,
echo la conversion a MP3 fallara (ver config.FFMPEG_PATH).
echo.
echo Sube ese archivo como asset de una nueva Release en GitHub
echo con el mismo nombre definido en version.APP_EXECUTABLE_NAME.
pause
