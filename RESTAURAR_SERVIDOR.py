#!/usr/bin/env python3
"""
SCRIPT CRÍTICO: Restaurar el servidor con los 16 productos locales.

El servidor está vacío (0 productos), pero el usuario tiene 16 locales.
Este script subirá esos 16 al servidor para restaurarlo.

USO:
    python RESTAURAR_SERVIDOR.py
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    from utils.file_handler import cargar_productos, cargar_usuarios
    from utils.sync_manager import get_sync_manager
    
    print("=" * 70)
    print("🔄 RESTAURAR SERVIDOR - Subir productos locales")
    print("=" * 70)
    
    # Obtener usuarios
    usuarios = cargar_usuarios() or {}
    if not usuarios:
        print("❌ No se encontraron usuarios registrados")
        return False
    
    # Mostrar usuarios disponibles
    print(f"\n📋 Usuarios encontrados: {len(usuarios)}")
    for uid, info in usuarios.items():
        username = info.get('username', 'desconocido') if isinstance(info, dict) else 'desconocido'
        print(f"   - ID {uid}: {username}")
    
    # Usar el primer usuario (o solo si hay uno)
    if len(usuarios) == 1:
        usuario_id = list(usuarios.keys())[0]
        username = usuarios[usuario_id].get('username') if isinstance(usuarios[usuario_id], dict) else str(usuario_id)
    else:
        # Preguntar al usuario
        print("\n¿Cuál es el ID del usuario a sincronizar?")
        try:
            usuario_id = int(input("> ").strip())
            if usuario_id not in usuarios:
                print(f"❌ Usuario ID {usuario_id} no encontrado")
                return False
            username = usuarios[usuario_id].get('username') if isinstance(usuarios[usuario_id], dict) else str(usuario_id)
        except ValueError:
            print("❌ ID inválido")
            return False
    
    print(f"\n✓ Usando usuario: {username} (ID: {usuario_id})")
    
    # Cargar productos locales
    print(f"\n📂 Cargando productos locales...")
    productos_locales = cargar_productos(username)
    
    if not productos_locales or len(productos_locales) == 0:
        print("❌ No hay productos locales para sincronizar")
        return False
    
    print(f"✓ {len(productos_locales)} productos locales encontrados:")
    for i, prod in enumerate(productos_locales[:5], 1):
        nombre = prod.get('nombre', 'sin nombre')
        print(f"   {i}. {nombre}")
    if len(productos_locales) > 5:
        print(f"   ... y {len(productos_locales) - 5} más")
    
    # Verificar estado del servidor
    print(f"\n🌐 Verificando estado del servidor...")
    from utils.api_handler import obtener_productos_remoto
    
    productos_remotos = obtener_productos_remoto(usuario_id)
    print(f"✓ Servidor actual: {len(productos_remotos)} productos" if productos_remotos else "✓ Servidor vacío")
    
    # Confirmar antes de subir
    print(f"\n⚠️  ADVERTENCIA: Se subirán {len(productos_locales)} productos al servidor")
    print("Esta acción sobrescribirá los datos remotos.")
    respuesta = input("\n¿Deseas continuar? (escribe 'SUBIR' para confirmar): ").strip()
    
    if respuesta != 'SUBIR':
        print("❌ Cancelado")
        return False
    
    # Sincronizar
    print(f"\n⏳ Sincronizando {len(productos_locales)} productos...")
    
    sync_mgr = get_sync_manager()
    success, message = sync_mgr.upload_inventory_direct(str(usuario_id), productos_locales)
    
    if success:
        print(f"✅ ¡ÉXITO! Inventario sincronizado: {message}")
        
        # Verificar que se subieron correctamente
        print(f"\n🔍 Verificando servidor...")
        productos_verificacion = obtener_productos_remoto(usuario_id)
        if productos_verificacion and len(productos_verificacion) > 0:
            print(f"✅ CONFIRMADO: Servidor ahora tiene {len(productos_verificacion)} productos")
            return True
        else:
            print(f"⚠️  Servidor sigue vacío - Intenta nuevamente")
            return False
    else:
        print(f"❌ Error: {message}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
