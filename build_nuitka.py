"""
Compilar VISO con Nuitka - Convierte Python a C++ nativo ultra rápido

Instalación requerida:
    pip install nuitka zstandard

Compilación:
    python build_nuitka.py
"""

import subprocess
import sys
import os
import shutil

def main():
    # Verificar Nuitka instalado
    try:
        import nuitka
        print("✅ Nuitka detectado")
    except ImportError:
        print("❌ Nuitka no está instalado")
        print("Instala con: pip install nuitka zstandard")
        return False
    
    # Rutas
    main_file = "main.py"
    output_dir = "dist_nuitka"
    
    # Limpiar build anterior
    if os.path.exists(output_dir):
        print(f"🧹 Limpiando {output_dir}...")
        shutil.rmtree(output_dir)
    
    # Crear comando de compilación Nuitka - SIMPLIFICADO
    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--output-dir=" + output_dir,
        "--follow-imports",
        "--enable-plugin=pyqt5",  # Plugin para PyQt5
        "--include-package=PyQt5",
        "--include-package=core",
        "--include-package=gui",
        "--include-package=utils",
        "--include-data-files=splash.png=splash.png",
        "--remove-output",
        main_file
    ]
    
    print("🔨 Compilando con Nuitka...")
    print(f"Comando: {' '.join(cmd[:5])}...")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ Compilación exitosa!")
        exe_path = os.path.join(output_dir, "main.exe" if sys.platform == "win32" else "main")
        print(f"📦 Ejecutable: {exe_path}")
        return True
    else:
        print("❌ Error en compilación")
        print("Intenta con PyInstaller: python build_exe_optimized.py")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
