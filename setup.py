import PyInstaller.__main__
import os
import sys
from pathlib import Path

# --- Configuración de rutas ---
base_dir = os.path.abspath(os.path.dirname(__file__))
icon_path = os.path.join(base_dir, "icon.ico")

# Verificar que el archivo ico existe
if not os.path.exists(icon_path):
    print("ADVERTENCIA: No se encuentra el archivo icon.ico")
    sys.exit(1)

print("\n" + "="*70)
print("🔨 COMPILANDO VISO A .EXE CON PYINSTALLER")
print("="*70 + "\n")

print("📦 Preparando compilación...")
print("-" * 70 + "\n")

# --- Construcción del ejecutable ---
args = [
    "main.py",
    "--onefile",                            # UN SOLO ARCHIVO (.exe)
    "--noconsole",                         # Sin consola en produccion
    f"--icon={icon_path}",                 # Icono de la aplicacion
    "--name=VISO",                         # Nombre del ejecutable
    "--noupx",                             # Desactivar UPX
    "--runtime-tmpdir=%LOCALAPPDATA%\\VISO_tmp",  # Directorio temporal
    "-y",                                  # Confirmar automaticamente
    "--clean",                             # Limpiar antes de compilar
    
    # --- EXCLUIR: Módulos innecesarios ---
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

    # --- INCLUIR: PyQt5 ---
    "--hidden-import=PyQt5.QtCore",
    "--hidden-import=PyQt5.QtGui",
    "--hidden-import=PyQt5.QtWidgets",
    "--hidden-import=PyQt5.QtPrintSupport",
    "--hidden-import=PyQt5.sip",

    # --- INCLUIR: PDF y Imágenes ---
    "--hidden-import=reportlab",
    "--hidden-import=reportlab.lib.pagesizes",
    "--hidden-import=reportlab.lib.styles",
    "--hidden-import=reportlab.platypus",
    "--hidden-import=reportlab.pdfgen",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--hidden-import=PIL.ImageDraw",
    "--hidden-import=PIL.ImageFont",
    "--hidden-import=fitz",

    # --- INCLUIR: Red y APIs ---
    "--hidden-import=requests",
    "--hidden-import=urllib3",

    # --- INCLUIR: Impresoras ---
    "--hidden-import=serial",
    "--hidden-import=serial.tools.list_ports",
    "--hidden-import=escpos",
    "--hidden-import=escpos.printer",

    # --- INCLUIR: Utilidades ---
    "--hidden-import=qrcode",
    "--hidden-import=dateutil",
    "--hidden-import=dateutil.relativedelta",
    "--hidden-import=num2words",
    "--hidden-import=psutil",

    # --- INCLUIR: AI (Opcional) ---
]

# --- Carpetas/archivos locales a incluir ---
data_items = [
    ("gui", "gui"),
    ("utils", "utils"),
    ("data", "data"),
    ("images", "images"),
    ("icon.ico", "."),
    ("INICIAR.PNG", "."),
]

# Agregar datos y recursos
for src, dest in data_items:
    src_path = os.path.join(base_dir, src)
    if os.path.exists(src_path):
        args.append(f"--add-data={src_path};{dest}")
        print(f"[OK] Incluido: {src}")

print(f"\n{'='*60}")
print("🚀 Iniciando compilación PyInstaller")
print(f"{'='*60}\n")

# Ejecutar PyInstaller
try:
    PyInstaller.__main__.run(args)
    print("\n" + "="*70)
    print("✅ COMPILACION EXITOSA")
    print("="*70)
    print("\n📁 Archivo generado: dist/VISO/VISO.exe")
    print("📦 El ejecutable está listo para usar\n")
    
except Exception as e:
    print(f"\n❌ Error durante compilacion: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

