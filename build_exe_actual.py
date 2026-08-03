#!/usr/bin/env python3
"""
Script de compilación limpio para VISO.exe

Uso:
    python build_exe_actual.py      # Compilación normal (sin consola)
    python build_exe_actual.py dev  # Compilación desarrollo (con consola para debugging)
"""

import PyInstaller.__main__
import os
import sys
from pathlib import Path

# --- Configuración de rutas ---
base_dir = os.path.abspath(os.path.dirname(__file__))
icon_path = os.path.join(base_dir, "icon.ico")
main_py = os.path.join(base_dir, "main.py")

# Modo desarrollo (con consola) o producción (sin consola)
# Por defecto: sin consola (--windowed)
# Con 'dev': con consola para debugging
is_development = len(sys.argv) > 1 and sys.argv[1] == 'dev'
console_flag = "--console" if is_development else "--windowed"

print("\n" + "="*70)
print("COMPILANDO VISO A .EXE (ACTUAL)")
print(f"   Modo: {'DESARROLLO (con consola)' if is_development else 'PRODUCCION (sin consola)'}")
print("="*70 + "\n")

# Verificar que el archivo ico existe
if not os.path.exists(icon_path):
    print(f"ERROR: No se encuentra el archivo icon.ico en {icon_path}")
    sys.exit(1)

print(f"OK Icono encontrado: {icon_path}")
print(f"OK Main: {main_py}")

# --- Construcción del ejecutable ---
args = [
    main_py,
    "--onefile",                              # UN SOLO ARCHIVO (.exe)
    console_flag,                             # Con o sin consola según modo
    f"--icon={icon_path}",                    # Icono de la aplicacion
    "--name=VISO",                            # Nombre del ejecutable
    "--noupx",                                # Desactivar UPX (más rápido)
    "-y",                                     # Confirmar automaticamente
    "--clean",                                # Limpiar antes de compilar
    
    # --- EXCLUIR: Módulos innecesarios para reducir tamaño ---
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
    "--exclude-module=PyQt6",  # Excluir PyQt6 para evitar conflictos
    "--exclude-module=tensorflow",  # Excluir TensorFlow (problemas en Windows)
    "--exclude-module=keras",  # Excluir Keras
    "--exclude-module=torch",  # Excluir PyTorch si existe

    # --- INCLUIR: Dependencias necesarias ---
    "--hidden-import=PyQt5.QtCore",
    "--hidden-import=PyQt5.QtGui",
    "--hidden-import=PyQt5.QtWidgets",
    "--hidden-import=PyQt5.QtPrintSupport",
    "--hidden-import=PyQt5.QtSql",
    "--hidden-import=PyQt5.QtNetwork",
    "--hidden-import=PyQt5.QtConcurrent",
    "--hidden-import=requests",
    "--hidden-import=sqlite3",
    "--hidden-import=json",
    "--hidden-import=hashlib",
    "--hidden-import=urllib3",
    "--hidden-import=escpos",
    "--hidden-import=escpos.printer",
    "--hidden-import=escpos.capabilities",
    "--hidden-import=matplotlib",
    "--hidden-import=matplotlib.pyplot",
    "--hidden-import=matplotlib.backends",
    "--hidden-import=matplotlib.figure",
    "--hidden-import=numpy",
    "--hidden-import=pandas",
]

# --- Incluir archivos locales (data, imagenes, etc) ---
data_items = [
    ("gui", "gui"),
    ("utils", "utils"),
    ("data", "data"),
    ("images", "images"),
    ("icon.ico", "."),
    ("INICIAR.PNG", "."),
    ("DISEÑOSPDF", "DISEÑOSPDF"),
]

for src, dest in data_items:
    src_path = os.path.join(base_dir, src)
    if os.path.exists(src_path):
        args.append(f"--add-data={src_path}{os.pathsep}{dest}")
        print(f"OK Incluido: {src} -> {dest}")
    else:
        print(f"WARNING No encontrado: {src}")

# --- Incluir archivos de escpos (capabilities.json) ---
try:
    import escpos
    escpos_path = os.path.dirname(escpos.__file__)
    print(f"OK Incluido: escpos capabilities -> escpos")
    args.append(f"--add-data={escpos_path}{os.pathsep}escpos")
except ImportError:
    print("WARNING escpos no encontrado")
print(f"\nOPCIONES:")
print(f"   --onefile: Compilar en un solo archivo")
print(f"   {console_flag}: {'Con consola (desarrollo)' if is_development else 'Sin consola (produccion)'}")
print(f"   --noupx: Compilacion mas rapida")
print(f"\nINICIANDO COMPILACION...\n")
print(f"Ejecuta con 'python build_exe_actual.py dev' para compilar con consola\n")

try:
    PyInstaller.__main__.run(args)
    print("\n" + "="*70)
    print("COMPILACION EXITOSA")
    print("="*70)
    if os.path.exists('dist/VISO.exe'):
        size = os.path.getsize('dist/VISO.exe') / (1024*1024)
        print(f"\nArchivo generado: dist/VISO.exe")
        print(f"Tamano: {size:.1f} MB")
    print("\n")
except SystemExit as e:
    if e.code == 0:
        print("\n" + "="*70)
        print("COMPILACION EXITOSA")
        print("="*70)
        if os.path.exists('dist/VISO.exe'):
            size = os.path.getsize('dist/VISO.exe') / (1024*1024)
            print(f"\nArchivo generado: dist/VISO.exe")
            print(f"Tamano: {size:.1f} MB")
        print("\n")
    else:
        print(f"\nError en compilacion (exit code: {e.code})")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
