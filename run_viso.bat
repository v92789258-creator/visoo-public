@echo off
REM Script para ejecutar VISO con Splash Loader
REM Ejecuta launcher.py que a su vez inicia el splash y main.py

cd /d "%~dp0"

echo.
echo ========================================
echo   VISO v4.2.4 - Inicializando...
echo ========================================
echo.

python launcher.py

REM Si se ejecutó desde un acceso directo, mantener ventana abierta
if "%1"=="pause" pause
