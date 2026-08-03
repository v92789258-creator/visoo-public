#!/usr/bin/env python3
"""
Script de compilación limpio para VISO.exe

Uso:
    python build_exe.py      # Compilación normal (sin consola)
    python build_exe.py dev  # Compilación desarrollo (con consola para debugging)
"""

import PyInstaller.__main__
import os
import sys
from pathlib import Path

# Importar el helper de imports ANTES de compilar para que PyInstaller lo analice
print("[BUILD] Importando helper de módulos para análisis estático...")
try:
    import pyinstaller_imports_helper
except ImportError as e:
    print(f"[WARNING] No se pudo importar helper: {e}")

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
print("COMPILANDO VISO A .EXE")
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
    "--exclude-module=PyQt6",
    # Machine Learning (NO LOS NECESITAMOS)
    "--exclude-module=tensorflow",
    "--exclude-module=keras",
    "--exclude-module=tf",
    "--exclude-module=torch",
    "--exclude-module=torchvision",
    "--exclude-module=torchaudio",
    "--exclude-module=scipy",
    "--exclude-module=numba",
    "--exclude-module=llvmlite",
    # Testing & Debug
    "--exclude-module=doctest",
    # Otros no necesarios
    "--exclude-module=pydoc",
    "--exclude-module=curses",

    # --- INCLUIR: Dependencias necesarias ---
    "--hidden-import=PyQt5.QtCore",
    "--hidden-import=PyQt5.QtGui",
    "--hidden-import=PyQt5.QtWidgets",
    "--hidden-import=PyQt5.QtPrintSupport",
    "--hidden-import=PyQt5.QtSql",
    "--hidden-import=PyQt5.QtNetwork",
    "--hidden-import=PyQt5.QtConcurrent",
    "--hidden-import=PyQt5.QtWebEngineCore",
    "--hidden-import=PyQt5.QtWebEngineWidgets",
    "--hidden-import=PyQt5.QtMultimedia",
    "--hidden-import=PyQt5.QtMultimediaWidgets",
    # PyQt5 plugins
    "--hidden-import=PyQt5.plugins",
    "--hidden-import=PyQt5.plugins.imageformats",
    "--hidden-import=PyQt5.plugins.platforms",
    "--hidden-import=PyQt5.plugins.platformthemes",
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
    # === IMPORTES DINÁMICOS DE MÓDULOS GUI ===
    "--hidden-import=gui",
    "--hidden-import=gui.dialogs",
    "--hidden-import=gui.dialogs.selection_dialogs",
    "--hidden-import=gui.dialogs.sale_options_dialog",
    "--hidden-import=gui.dialogs.appointment_dialog",
    "--hidden-import=gui.dialogs.paciente_selector_dialog",
    "--hidden-import=gui.main_window_pages",
    "--hidden-import=gui.main_window_pages.sales_page",
    "--hidden-import=gui.main_window_pages.caja_page",
    "--hidden-import=gui.main_window_pages.customers_page",
    "--hidden-import=gui.main_window_pages.appointments_page",
    "--hidden-import=gui.widgets",
    "--hidden-import=gui.widgets.appointment_improvements",
    "--hidden-import=gui.styles",
    "--hidden-import=gui.styles.appointments_professional_style",
    # === IMPORTES DINÁMICOS DE UTILS ===
    "--hidden-import=utils",
    "--hidden-import=utils.file_handler",
    "--hidden-import=utils.barcode_scanner",
    "--hidden-import=utils.generador_boletas_plantilla",
    "--hidden-import=utils.appointments_model",
    "--hidden-import=utils.appointments_stats",
    "--hidden-import=utils.appointments_improvements",
    "--hidden-import=utils.schedule_manager",
    "--hidden-import=utils.data_cache_manager",
    # Imports dinámicos de GUI (importados dentro de métodos)
    "--hidden-import=gui.dialogs.receipt_size_dialog",
    "--hidden-import=gui.dialogs.pdf_viewer_dialog",
    "--hidden-import=gui.dialogs.sale_options_dialog",
    "--hidden-import=gui.dialogs.selection_dialogs",
    "--hidden-import=gui.dialogs.appointment_dialog",
    "--hidden-import=gui.dialogs.paciente_selector_dialog",
    # Utils dinámicos
    "--hidden-import=utils.helpers_manager",
    "--hidden-import=utils.file_handler",
    "--hidden-import=utils.data_cache_manager",
    "--hidden-import=utils.barcode_scanner",
    "--hidden-import=utils.generador_boletas_plantilla",
    # PIL/Pillow
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--hidden-import=PIL.ImageDraw",
    "--hidden-import=PIL.ImageFont",
    # Tkinter (para splash loader)
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    # Otros
    "--hidden-import=datetime",
    "--hidden-import=re",
    "--hidden-import=os",
    "--hidden-import=sys",
    "--hidden-import=io",
    "--hidden-import=base64",
]


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
print(f"Ejecuta con 'python build_exe.py dev' para compilar con consola\n")

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
