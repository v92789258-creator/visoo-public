@echo off
REM Script para compilar SplashLoader.cpp con MSVC

setlocal enabledelayedexpansion

REM Detectar Visual Studio
for /f "tokens=*" %%i in ('where cl.exe 2^>nul') do set "MSVC_PATH=%%i"

if not defined MSVC_PATH (
    echo [ERROR] No se encontró compilador MSVC (cl.exe)
    echo Asegúrate de tener Visual Studio instalado y agregar las herramientas al PATH
    pause
    exit /b 1
)

echo [INFO] Compilador encontrado: !MSVC_PATH!

REM Crear carpeta de build
if not exist "build" mkdir build
cd build

REM Limpiar builds anteriores
echo [INFO] Limpiando builds anteriores...
if exist "CMakeCache.txt" del CMakeCache.txt
if exist "CMakeFiles" rmdir /s /q CMakeFiles

REM Ejecutar CMake
echo [INFO] Generando archivos de proyecto con CMake...
cmake -G "Visual Studio 17 2022" -A x64 ..

if errorlevel 1 (
    echo [ERROR] CMake falló
    pause
    exit /b 1
)

REM Compilar
echo [INFO] Compilando SplashLoader...
cmake --build . --config Release

if errorlevel 1 (
    echo [ERROR] Compilación falló
    pause
    exit /b 1
)

echo [SUCCESS] Compilación completada!
echo [INFO] Ejecutable: .\Release\SplashLoader.exe

REM Copiar ejecutable a carpeta raíz
if exist "Release\SplashLoader.exe" (
    copy "Release\SplashLoader.exe" ".."
    echo [SUCCESS] SplashLoader.exe copiado a carpeta raíz
)

cd ..
pause
