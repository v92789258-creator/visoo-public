#!/usr/bin/env python3
"""
Script de compilación ULTRA LIGERO para VISO.exe
Solo para probar el splash screen y la interfaz básica
Excluye casi todo lo innecesario

Uso:
    python build_exe_light.py
"""

import PyInstaller.__main__
import os
import sys

# --- Configuración de rutas ---
base_dir = os.path.abspath(os.path.dirname(__file__))
icon_path = os.path.join(base_dir, "icon.ico")
main_py = os.path.join(base_dir, "main.py")

print("\n" + "="*70)
print("COMPILANDO VISO LIGERO (SPLASH SCREEN ONLY)")
print("="*70 + "\n")

if not os.path.exists(icon_path):
    print(f"WARNING: No se encuentra {icon_path}")

# --- Construcción del ejecutable MINIMAL ---
args = [
    main_py,
    "--onefile",
    "--windowed",
    f"--icon={icon_path}" if os.path.exists(icon_path) else "",
    "--name=VISO_Light",
    "--noupx",
    "-y",
    "--clean",
    
    # --- EXCLUIR: CASI TODO ---
    "--exclude-module=tkinter",
    "--exclude-module=jupyter",
    "--exclude-module=notebook",
    "--exclude-module=ipython",
    "--exclude-module=IPython",
    "--exclude-module=pytest",
    "--exclude-module=nose",
    "--exclude-module=sphinx",
    "--exclude-module=setuptools",
    "--exclude-module=pip",
    "--exclude-module=PyQt6",
    "--exclude-module=tensorflow",
    "--exclude-module=matplotlib",
    "--exclude-module=numpy",
    "--exclude-module=pandas",
    "--exclude-module=requests",
    "--exclude-module=flask",
    "--exclude-module=google",
    "--exclude-module=escpos",
    "--exclude-module=cv2",
    "--exclude-module=PIL",
    "--exclude-module=openpyxl",
    
    # --- INCLUIR: SOLO LO BASICO ---
    "--hidden-import=PyQt5.QtCore",
    "--hidden-import=PyQt5.QtGui",
    "--hidden-import=PyQt5.QtWidgets",
]

# Incluir splash.png
splash_src = os.path.join(base_dir, "splash.png")
if os.path.exists(splash_src):
    args.append(f"--add-data={splash_src}{os.pathsep}.")
    print(f"OK Incluido: splash.png")
else:
    print(f"WARNING: splash.png no encontrado")

# Limpiar strings vacios
args = [arg for arg in args if arg]

print(f"Tamaño esperado: < 50 MB\n")
print(f"Opciones:")
print(f"   --onefile: Un solo archivo")
print(f"   --windowed: Sin consola")
print(f"   Modo: ULTRA LIGERO (splash screen only)\n")

try:
    PyInstaller.__main__.run(args)
    print("\n" + "="*70)
    print("COMPILACION EXITOSA")
    print("="*70)
    if os.path.exists('dist/VISO_Light.exe'):
        size = os.path.getsize('dist/VISO_Light.exe') / (1024*1024)
        print(f"\nArchivo: dist/VISO_Light.exe")
        print(f"Tamaño: {size:.1f} MB")
    print("\n")
except SystemExit as e:
    if e.code == 0:
        print("\n" + "="*70)
        print("COMPILACION EXITOSA")
        print("="*70)
        if os.path.exists('dist/VISO_Light.exe'):
            size = os.path.getsize('dist/VISO_Light.exe') / (1024*1024)
            print(f"\nArchivo: dist/VISO_Light.exe")
            print(f"Tamaño: {size:.1f} MB")
        print("\n")
    else:
        print(f"\nError en compilacion (exit code: {e.code})")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
