"""
Script para ofuscar código Python antes de compilar con PyInstaller
Ofusca los archivos .py en carpetas gui/, utils/ y otros
y guarda los originales en una carpeta de backup
"""
import os
import sys
import shutil
import py_compile
from pathlib import Path

def ofuscar_directorio(directorio, backup_dir):
    """Ofusca todos los archivos .py en un directorio recursivamente"""
    directorio = Path(directorio)
    backup_dir = Path(backup_dir)
    
    if not directorio.exists():
        print(f"⚠️  Directorio no existe: {directorio}")
        return
    
    # Crear carpeta de backup si no existe
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    contador = 0
    for archivo_py in directorio.rglob("*.py"):
        try:
            # Ruta relativa
            rel_path = archivo_py.relative_to(directorio)
            
            # Crear estructura en backup
            backup_path = backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Hacer backup del original
            if not backup_path.exists():
                shutil.copy2(archivo_py, backup_path)
                print(f"  ✓ Backup: {rel_path}")
            
            # Compilar a bytecode (.pyc) - PyInstaller usará esto
            # Esto convierte .py a bytecode compilado (ofuscado)
            py_compile.compile(str(archivo_py), doraise=True)
            
            # Opcionalmente: reemplazar .py con comentarios minimalistas
            # pero mantener estructura para que PyInstaller lo encuentre
            with open(archivo_py, 'w', encoding='utf-8') as f:
                f.write("# Archivo compilado - versión ofuscada\n")
                f.write(f"# Original: {rel_path}\n")
            
            contador += 1
            print(f"  🔒 Ofuscado: {rel_path}")
            
        except Exception as e:
            print(f"  ⚠️  Error procesando {archivo_py}: {e}")
    
    return contador

def main():
    base_dir = Path(__file__).parent
    backup_dir = base_dir / ".backup_original_code"
    
    print("\n" + "="*60)
    print("🔐 INICIANDO OFUSCACIÓN DE CÓDIGO")
    print("="*60 + "\n")
    
    carpetas_a_ofuscar = [
        base_dir / "gui",
        base_dir / "utils",
    ]
    
    total_ofuscados = 0
    
    for carpeta in carpetas_a_ofuscar:
        if carpeta.exists():
            print(f"\n📁 Procesando: {carpeta.name}/")
            count = ofuscar_directorio(carpeta, backup_dir / carpeta.name)
            total_ofuscados += count if count else 0
        else:
            print(f"\n⚠️  No encontrada: {carpeta}")
    
    print("\n" + "="*60)
    print(f"✅ OFUSCACIÓN COMPLETADA")
    print(f"   - Archivos procesados: {total_ofuscados}")
    print(f"   - Backup guardado en: {backup_dir.name}/")
    print("="*60 + "\n")
    
    print("💡 IMPORTANTE:")
    print("   - Tu código original está seguro en la carpeta '.backup_original_code'")
    print("   - Después de compilar, puedes restaurar los .py originales si es necesario")
    print("   - El .exe final tendrá tu código compilado en _internal/\n")

if __name__ == "__main__":
    main()
