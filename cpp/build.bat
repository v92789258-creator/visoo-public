@echo off
REM Script de compilación automática de InventoryOptimizer para Windows
REM Requisitos: Visual Studio 2019+ o CMake instalado

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo Compilando InventoryOptimizer (C++)
echo ============================================

REM Crear directorio de compilación
if not exist "build" mkdir build
cd build

REM Ejecutar CMake
echo Configurando proyecto con CMake...
cmake .. -G "Visual Studio 16 2019" -DCMAKE_BUILD_TYPE=Release

REM Compilar
echo Compilando...
cmake --build . --config Release

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo ✓ Compilación exitosa!
    echo ============================================
    echo DLL generada en: %cd%\Release\InventoryOptimizer.dll
) else (
    echo.
    echo ============================================
    echo ✗ Error en la compilación
    echo ============================================
    pause
    exit /b 1
)

pause
