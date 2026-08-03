#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de compilacion RAPIDA para VISO.exe - Sin validaciones complejas

Uso:
    python build_exe_fast.py      # Compilacion normal
    python build_exe_fast.py dev  # Con consola para debugging
"""

import importlib
import os
import sys

base_dir = os.path.abspath(os.path.dirname(__file__))
icon_path = os.path.join(base_dir, "icon.ico")
main_py = os.path.join(base_dir, "main.py")

is_development = len(sys.argv) > 1 and sys.argv[1] == 'dev'
console_flag = "--console" if is_development else "--windowed"

print("\n[COMPILACION RAPIDA VISO] Modo: " + ("DESARROLLO" if is_development else "PRODUCCION"))

args = [
    main_py,
    "--onefile",
    console_flag,
    f"--icon={icon_path}",
    "--name=VISO",
    "-y",
    "--clean",
    
    # EXCLUIR pesadas
    "--exclude-module=pandas",
    "--exclude-module=scipy",
    "--exclude-module=sklearn",
    "--exclude-module=tensorflow",
    "--exclude-module=keras",
    "--exclude-module=torch",
    "--exclude-module=pytest",
    "--exclude-module=jupyter",
    "--exclude-module=notebook",
    "--exclude-module=ipython",
    
    # INCLUIR esenciales
    "--hidden-import=PyQt5.QtCore",
    "--hidden-import=PyQt5.QtGui",
    "--hidden-import=PyQt5.QtWidgets",
    "--hidden-import=PyQt5.QtPrintSupport",
    "--hidden-import=PyQt5.QtSql",
    "--hidden-import=PyQt5.QtNetwork",
    "--hidden-import=PyQt5.QtConcurrent",
    "--hidden-import=PyQt5.plugins.imageformats",
    "--hidden-import=PyQt5.plugins.platforms",
    "--hidden-import=PyQt5.plugins.platformthemes",
    
    "--hidden-import=requests",
    "--hidden-import=urllib3",
    "--hidden-import=certifi",
    "--hidden-import=ssl",
    "--hidden-import=socket",
    "--hidden-import=webbrowser",
    
    "--hidden-import=sqlite3",
    "--hidden-import=escpos",
    "--hidden-import=escpos.printer",
    
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--hidden-import=PIL.ImageDraw",
    
    "--hidden-import=fitz",
    "--hidden-import=pymupdf",
    
    "--hidden-import=asyncio",
    "--hidden-import=json",
    "--hidden-import=hashlib",
    "--hidden-import=datetime",
    "--hidden-import=re",
    "--hidden-import=io",
    "--hidden-import=base64",
    "--hidden-import=threading",
    "--hidden-import=subprocess",
    "--hidden-import=ctypes",
    "--hidden-import=ctypes.wintypes",
    "--hidden-import=tempfile",
    "--hidden-import=shutil",
    
    # APP MODULES
    "--hidden-import=gui",
    "--hidden-import=gui.login_window",
    "--hidden-import=gui.main_window",
    "--hidden-import=gui.lazy_page_loader",
    "--hidden-import=gui.dialogs",
    "--hidden-import=gui.main_window_pages",
    "--hidden-import=gui.main_window_pages.home_page",
    "--hidden-import=gui.widgets",
    "--hidden-import=gui.widgets.components",
    "--hidden-import=gui.widgets.components.charts",
    "--hidden-import=gui.styles",
    
    "--hidden-import=utils",
    "--hidden-import=utils.file_handler",
    "--hidden-import=utils.api_handler",
]

# Agregar data items
data_items = [
    ("gui", "gui"),
    ("utils", "utils"),
    ("data", "data"),
    ("images", "images"),
    ("icon.ico", "."),
    ("INICIAR.PNG", "."),
    ("ext", "ext"),
]

for src, dest in data_items:
    src_path = os.path.join(base_dir, src)
    if os.path.exists(src_path):
        args.append(f"--add-data={src_path}{os.pathsep}{dest}")
        print(f"[OK] {src}")

print("[INICIO] Compilando...\n")

try:
    pyinstaller_main = importlib.import_module("PyInstaller.__main__")
    pyinstaller_main.run(args)
    print("\n[EXITO] Compilacion completada")
    if os.path.exists('dist/VISO.exe'):
        size = os.path.getsize('dist/VISO.exe') / (1024*1024)
        print(f"[INFO] Tamanio: {size:.1f} MB")
except Exception as e:
    print(f"[ERROR] {e}")
