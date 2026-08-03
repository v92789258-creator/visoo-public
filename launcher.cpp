/**
 * VISO Launcher - C++ puro
 * Inicia la aplicación Python compilada con máxima velocidad
 * 
 * Compilación:
 *   g++ -O3 launcher.cpp -o launcher.exe
 * o con MSVC:
 *   cl /O2 launcher.cpp
 */

#include <windows.h>
#include <stdio.h>
#include <tchar.h>

int main() {
    // Splash mínimo (opcional)
    printf("Iniciando VISO...\n");
    
    // Ejecutar la aplicación compilada con Nuitka
    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    
    TCHAR szCmdline[] = TEXT("main.exe");
    
    if (!CreateProcess(
        NULL,           // Nombre del módulo
        szCmdline,      // Línea de comandos
        NULL,           // Atributos de proceso
        NULL,           // Atributos de thread
        FALSE,          // Sin herencia de handles
        0,              // Sin banderas
        NULL,           // Sin entorno
        NULL,           // Sin directorio
        &si,            // Estructura STARTUPINFO
        &pi             // Estructura PROCESS_INFORMATION
    )) {
        printf("Error: No se pudo iniciar VISO (%ld)\n", GetLastError());
        return 1;
    }
    
    // Esperar a que termine
    WaitForSingleObject(pi.hProcess, INFINITE);
    
    // Obtener código de salida
    DWORD dwExitCode = 0;
    GetExitCodeProcess(pi.hProcess, &dwExitCode);
    
    // Cerrar handles
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    
    return dwExitCode;
}
