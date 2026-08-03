#!/usr/bin/env python3
"""
Script de compilación MINIMAL para VISO.exe
Versión simplificada sin dependencias problemáticas
"""

import PyInstaller.__main__
import os
import sys
from pathlib import Path

# --- Configuración de rutas ---
base_dir = os.path.abspath(os.path.dirname(__file__))
icon_path = os.path.join(base_dir, "icon.ico")
main_py = os.path.join(base_dir, "main.py")

is_development = len(sys.argv) > 1 and sys.argv[1] == 'dev'
console_flag = "--console" if is_development else "--windowed"

print("\n" + "="*70)
print("COMPILANDO VISO A .EXE (MINIMAL - SIN DEPENDENCIAS PESADAS)")
print(f"   Modo: {'DESARROLLO (con consola)' if is_development else 'PRODUCCION (sin consola)'}")
print("="*70 + "\n")

if not os.path.exists(icon_path):
    print(f"ERROR: No se encuentra el archivo icon.ico en {icon_path}")
    sys.exit(1)

print(f"OK Icono encontrado: {icon_path}")
print(f"OK Main: {main_py}")

# --- Construcción del ejecutable (VERSIÓN LIMPIA) ---
args = [
    main_py,
    "--onefile",
    console_flag,
    f"--icon={icon_path}",
    "--name=VISO",
    "--noupx",
    "-y",
    "--clean",
    
    # === EXCLUIR TODAS LAS DEPENDENCIAS PROBLEMÁTICAS ===
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
    "--exclude-module=keras",
    "--exclude-module=torch",
    "--exclude-module=matplotlib",  # EXCLUIR matplotlib
    "--exclude-module=pandas",  # EXCLUIR pandas
    "--exclude-module=numpy",  # EXCLUIR numpy (solo si no es necesario)
    "--exclude-module=scipy",
    "--exclude-module=sklearn",
    "--exclude-module=jinja2",
    "--exclude-module=flask",
    
    # === INCLUIR SOLO LO ESENCIAL ===
    "--hidden-import=PyQt5.QtCore",
    "--hidden-import=PyQt5.QtGui",
    "--hidden-import=PyQt5.QtWidgets",
    "--hidden-import=PyQt5.QtPrintSupport",
    "--hidden-import=PyQt5.QtSql",
    "--hidden-import=PyQt5.QtNetwork",
    "--hidden-import=requests",
    "--hidden-import=sqlite3",
    "--hidden-import=json",
    "--hidden-import=hashlib",
    "--hidden-import=urllib3",
    "--hidden-import=escpos",
    "--hidden-import=escpos.printer",
]

# --- Incluir archivos locales ---
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

print("\nOPCIONES:")
print("   --onefile: Compilar en un solo archivo")
print("   --windowed: Sin consola (produccion)")
print("   --noupx: Compilacion mas rapida")
print("   [LIMPIEZA DE DEPENDENCIAS PESADAS]")

print("\nINICIANDO COMPILACION...")
print("Ejecuta con 'python build_exe_minimal.py dev' para compilar con consola\n")

# Ejecutar PyInstaller
PyInstaller.__main__.run(args)

print("\n" + "="*70)
print("COMPILACION COMPLETADA")
print("="*70)
