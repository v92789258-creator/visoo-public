# SplashLoader - Pantalla de Carga para VISO

Esta es una aplicación C++ que muestra una pantalla de carga elegante mientras se inicializa VISO.

## Características

✅ Ventana splash moderna y centrada  
✅ Barra de progreso visual  
✅ Mensajes de estado en tiempo real  
✅ Inicia automáticamente main.py  
✅ Rendimiento optimizado (escrito en C++, no Python)  
✅ Sin dependencias externas (solo Win32 API)

## Compilación

### Opción 1: Compilación Simple (Recomendada)

Abre "Visual Studio Developer Command Prompt" y ejecuta:

```batch
cd "C:\Users\USUARIO.DESKTOP-NOO0BDB\Desktop\VISO VERSIONES\4.1\viso version 4.2.4"
compile_splash_simple.bat
```

### Opción 2: Con CMake

```batch
cd "C:\Users\USUARIO.DESKTOP-NOO0BDB\Desktop\VISO VERSIONES\4.1\viso version 4.2.4"
compile_splash.bat
```

## Uso

Ejecuta el programa compilado:

```batch
SplashLoader.exe
```

O crea un acceso directo que lance `SplashLoader.exe` desde esta carpeta.

## Cómo funciona

1. **SplashLoader.exe** se inicia primero
2. Muestra la pantalla de carga con barra de progreso
3. Inicia **main.py** en background
4. Simula fases de carga (PyQt5, Sesión, Licencia, etc.)
5. Cuando main.py está listo, cierra automáticamente la pantalla de carga
6. Se muestra la interfaz completa de VISO

## Personalización

Puedes editar `SplashLoader.cpp` para:

- Cambiar colores (línea ~130: `RGB(15, 23, 42)`)
- Agregar tu logo o imagen
- Modificar las fases de carga
- Ajustar tiempos de animación

## Requisitos

- Windows 7 o superior
- Visual Studio Community (versión 2019 o superior)
- CMake (opcional, solo para la opción 2)
- Python instalado en PATH

## Notas

- El programa es muy ligero (~50KB)
- Se ejecuta sin consola (UI limpia)
- Compatible con PyInstaller (puede incluirse en .exe empaquetado)
