#!/usr/bin/env python3
"""
Script para verificar e inicializar pywin32 correctamente
"""
import sys
import os
import subprocess

def setup_pywin32():
    """Configura pywin32 sin necesidad de post-install."""
    try:
        # Intentar importar win32api y win32con
        import win32api
        import win32con
        print("✓ pywin32 ya está disponible")
        return True
    except ImportError:
        print("⚠ Intentando registrar pywin32...")
        try:
            # Ejecutar post-install via subprocess (más seguro que importar directamente)
            import site
            site_packages = site.getsitepackages()[0]
            postinstall_script = os.path.join(site_packages, 'pywin32_postinstall.py')
            
            if os.path.exists(postinstall_script):
                subprocess.run([sys.executable, postinstall_script, '-install'], check=True)
                print("✓ pywin32 registrado correctamente")
                return True
            else:
                print("⚠ Script de post-install no encontrado, pero pywin32 debería funcionar...")
                return True
        except Exception as e:
            print(f"⚠ No se pudo registrar automáticamente: {e}")
            print("Pero pywin32 debería funcionar de todos modos...")
            return True

if __name__ == "__main__":
    setup_pywin32()
    
    # Intentar importar las librerías que usamos
    try:
        import win32print
        print("✓ win32print disponible")
    except ImportError:
        print("✗ win32print no disponible")
        sys.exit(1)
    
    try:
        import win32api
        print("✓ win32api disponible")
    except ImportError:
        print("✗ win32api no disponible")
        sys.exit(1)
    
    print("\n✓ Todas las librerías necesarias están disponibles")
    sys.exit(0)
