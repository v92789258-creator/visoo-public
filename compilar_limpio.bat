@echo off
REM Limpiar y compilar VISO con todos los imports correctos
echo ======================================
echo COMPILANDO VISO.exe CON CONSOLA
echo (Limpieza + Imports Corregidos)
echo ======================================
echo.

REM Limpiar builds anteriores
echo Limpiando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del *.spec
echo OK Limpieza completada
echo.

REM Compilar con todos los imports
echo Iniciando compilacion...
python build_exe.py dev

echo.
if exist "dist\VISO.exe" (
    echo ======================================
    echo COMPILACION EXITOSA!
    echo ======================================
    for /f %%A in ('powershell -Command "[math]::Round((Get-Item dist\VISO.exe).Length / 1MB, 1)"') do (
        echo Tamano: %%A MB
    )
    echo.
    echo Ejecuta: test_exe_debug.bat
) else (
    echo ERROR: VISO.exe no se creo
)
pause
