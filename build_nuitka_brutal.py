"""
COMPILAR VISO CON NUITKA - BRUTAL MODE
⚡ ULTRA-SIMPLIFICADO - SOLO LO ESENCIAL
"""

import subprocess
import sys
import os
import shutil

def main():
    output_dir = "dist_cpp"
    
    # Limpiar
    if os.path.exists(output_dir):
        print(f"🧹 Limpiando {output_dir}...")
        shutil.rmtree(output_dir)
    
    # ⚡ BRUTAL MODE: Excluir CASI TODAS las librerías
    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--output-dir=" + output_dir,
        # Solo incluir lo VITAL
        "--include-package=PyQt5",
        "--include-package=core",
        "--include-package=gui",
        "--include-package=utils",
        "--include-data-files=splash.png=splash.png",
        # EXCLUIR CUALQUIER COSA QUE CAUSE PROBLEMAS
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=reportlab",
        "--nofollow-import-to=PIL",
        "--nofollow-import-to=fitz",
        "--nofollow-import-to=pymupdf",
        "--nofollow-import-to=fontTools",
        "--nofollow-import-to=xlsxwriter",
        "--nofollow-import-to=barcode",
        "--nofollow-import-to=qrcode",
        "--nofollow-import-to=escpos",
        "--nofollow-import-to=tensorflow",
        "--nofollow-import-to=torch",
        "--nofollow-import-to=sklearn",
        "--follow-stdlib",
        "--remove-output",
        "main.py"
    ]
    
    print("⚡ MODO BRUTAL: Compilando VISO (ULTRA-RÁPIDO)...")
    print("   Excluyendo: matplotlib, numpy, scipy, pandas, fitz...")
    print("              PIL, fontTools, xlsxwriter, barcode, qrcode...\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = os.path.join(output_dir, "main.exe")
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024*1024)
            print("\n" + "="*70)
            print("✅ ¡ÉXITO!")
            print("="*70)
            print(f"📦 Ejecutable: {exe_path}")
            print(f"📊 Tamaño: {size:.1f} MB")
            print("⚡ C++ Nativo - MÁS RÁPIDO")
            print("="*70)
        return True
    else:
        print("\n❌ No compiló")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
