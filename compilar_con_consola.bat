@echo off
REM Compilar VISO con consola
echo ======================================
echo Compilando VISO.exe CON CONSOLA...
echo ======================================
echo.
python build_exe.py dev
echo.
echo ======================================
if exist "dist\VISO.exe" (
    echo LISTO! El EXE esta en: dist\VISO.exe
    echo Con consola lista para debugging
) else (
    echo ERROR en la compilacion
)
echo ======================================
pause
