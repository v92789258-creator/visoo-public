#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilación SIMPLE y CONFIABLE de VISO.exe con PyInstaller
Sin exclusiones problemáticas - solo lo esencial
"""

import PyInstaller.__main__
import os
import sys
import shutil
from pathlib import Path

base_dir = os.path.abspath(os.path.dirname(__file__))
icon_path = os.path.join(base_dir, "icon.ico")
main_py = os.path.join(base_dir, "main.py")

is_development = len(sys.argv) > 1 and sys.argv[1] == 'dev'
console_flag = "--console" if is_development else "--windowed"

print("\n" + "="*70)
print("COMPILANDO VISO.exe - VERSIÓN SIMPLE Y CONFIABLE")
print("="*70 + "\n")

if not os.path.exists(icon_path):
    print(f"ERROR: No encontrado icon.ico en {icon_path}")
    sys.exit(1)

print(f"✅ Icono: {icon_path}")
print(f"✅ Main: {main_py}\n")

# COMPILACIÓN SIMPLE - SIN EXCLUSIONES PROBLEMÁTICAS
args = [
    main_py,
    "--onefile",
    console_flag,
    f"--icon={icon_path}",
    "--name=VISO",
    "-y",
    "--clean",
    
    # === EXCLUIR SOLO LO MÁS PESADO ===
    # Análisis de datos - REALMENTE no se usan
    "--exclude-module=pandas",
    "--exclude-module=scipy",
    "--exclude-module=numpy",
    "--exclude-module=scikit-learn",
    "--exclude-module=sklearn",
    
    # Machine Learning - REALMENTE no se usan
    "--exclude-module=tensorflow",
    "--exclude-module=keras",
    "--exclude-module=torch",
    "--exclude-module=torchvision",
    "--exclude-module=torchaudio",
    "--exclude-module=jax",
    
    # Gráficos/Visualización - Usamos C++ nativo
    "--exclude-module=matplotlib",
    "--exclude-module=pyqtgraph",
    "--exclude-module=plotly",
    
    # IDEs/Dev tools
    "--exclude-module=ipython",
    "--exclude-module=IPython",
    "--exclude-module=jupyter",
    "--exclude-module=notebook",
    "--exclude-module=jedi",
    "--exclude-module=pylint",
    "--exclude-module=flake8",
    "--exclude-module=black",
    
    # Testing
    "--exclude-module=pytest",
    "--exclude-module=nose",
    "--exclude-module=unittest2",
    "--exclude-module=mock",
    
    # Otros GUIs
    "--exclude-module=PyQt6",
    "--exclude-module=PySide2",
    "--exclude-module=PySide6",
    "--exclude-module=wx",
    "--exclude-module=gi",
    
    # === INCLUIR ESENCIAL ===
    "--hidden-import=PyQt5.QtCore",
    "--hidden-import=PyQt5.QtGui",
    "--hidden-import=PyQt5.QtWidgets",
    "--hidden-import=PyQt5.QtPrintSupport",
    "--hidden-import=PyQt5.QtSql",
    "--hidden-import=PyQt5.QtNetwork",
    "--hidden-import=PyQt5.QtConcurrent",
    "--hidden-import=PyQt5.plugins.imageformats",
    "--hidden-import=PyQt5.plugins.platforms",
    
    # Redes
    "--hidden-import=requests",
    "--hidden-import=urllib3",
    "--hidden-import=certifi",
    
    # Criptografía (SUNAT)
    "--hidden-import=cryptography",
    "--hidden-import=cryptography.hazmat.primitives",
    "--hidden-import=cryptography.hazmat.backends",
    
    # Imágenes
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    
    # Códigos
    "--hidden-import=qrcode",
    "--hidden-import=barcode",
    
    # PDF
    "--hidden-import=reportlab",
    "--hidden-import=reportlab.pdfgen",
    "--hidden-import=reportlab.lib",
    "--hidden-import=fitz",
    
    # Impresoras
    "--hidden-import=escpos",
    "--hidden-import=escpos.printer",
    
    # Hojas de cálculo
    "--hidden-import=openpyxl",
    "--hidden-import=xlrd",
]

print("🔨 Compilando...\n")
result = PyInstaller.__main__.run(args)

if result is None or result == 0:
    exe_path = os.path.join(base_dir, "dist", "VISO", "VISO.exe")
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024*1024)
        print("\n" + "="*70)
        print("✅ ¡ÉXITO!")
        print("="*70)
        print(f"📦 Ejecutable: dist/VISO/VISO.exe")
        print(f"📊 Tamaño: {size:.1f} MB")
        print("⚡ Listo para usar")
        print("="*70 + "\n")
    sys.exit(0)
else:
    print("\n❌ Compilación fallida")
    sys.exit(1)
