@echo off
REM Script simple para compilar SplashLoader.cpp directamente con MSVC

echo [INFO] Compilando SplashLoader.cpp...
cl.exe /W3 /O2 /EHsc SplashLoader.cpp /link user32.lib kernel32.lib comctl32.lib gdi32.lib /SUBSYSTEM:WINDOWS

if errorlevel 1 (
    echo [ERROR] Compilación falló
    echo Asegúrate de ejecutar esto desde Visual Studio Developer Command Prompt
    pause
    exit /b 1
)

echo [SUCCESS] Compilación completada!
echo [INFO] Ejecutable: SplashLoader.exe
pause
