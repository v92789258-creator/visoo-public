#!/usr/bin/env python3
"""
🛠️ HERRAMIENTA DE RECUPERACIÓN: Restaurar servidor desde respaldo local

SITUACIÓN:
- Servidor: 0 productos (BORRADO)
- Local: 16 productos (PROTEGIDOS)

ACCIÓN:
1. Preparar los 16 productos locales para sincronización
2. Subir al servidor
3. Verificar que se sincronizaron correctamente

USO:
    python restore_server_from_local.py
"""
import os
import sys
import json
from pathlib import Path

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from utils.file_handler import cargar_usuarios, cargar_productos, guardar_productos
from utils.api_handler import obtener_productos_remoto
from utils.sync_manager import get_sync_manager

def main():
    print("=" * 70)
    print("🛠️  RECUPERADOR DE SERVIDOR - Restaurar desde respaldo local")
    print("=" * 70)
    
    # Inicializar sync manager (asegura que DB existe)
    sync_mgr = get_sync_manager()
    print("\n✓ Sync manager inicializado")
    
    # Cargar usuarios
    usuarios = cargar_usuarios() or {}
    if not usuarios:
        print("❌ No hay usuarios configurados")
        return
    
    # Procesar cada usuario
    for uid, info in usuarios.items():
        if not isinstance(info, dict):
            continue
        
        username = info.get('username', '?')
        uid_int = int(uid)
        
        print(f"\n{'=' * 70}")
        print(f"👤 USUARIO: {username} (ID={uid_int})")
        print(f"{'=' * 70}")
        
        # 1. Cargar productos locales
        productos_locales = cargar_productos(username)
        if not productos_locales:
            print(f"⚠️  No hay productos locales para restaurar")
            continue
        
        print(f"\n✓ Productos locales encontrados: {len(productos_locales)}")
        
        # 2. Verificar estado del servidor
        print(f"\n📡 Verificando servidor...")
        try:
            productos_remotos = obtener_productos_remoto(uid_int)
            print(f"   Servidor actual: {len(productos_remotos) if productos_remotos else 0} productos")
        except Exception as e:
            print(f"   ❌ Error consultando servidor: {e}")
            productos_remotos = None
        
        # 3. Decidir si restaurar
        if productos_remotos and len(productos_remotos) > 0:
            print(f"\n⚠️  El servidor ya tiene {len(productos_remotos)} productos")
            print(f"    NO se restaurarán los locales (evitar duplicados)")
            continue
        
        # 4. Preparar para sincronización
        print(f"\n📝 Preparando {len(productos_locales)} productos para sincronización...")
        
        # Agregar cada producto a la cola como CREATE
        added_count = 0
        for producto in productos_locales:
            producto_id = str(producto.get('id', ''))
            if not producto_id:
                print(f"   ⚠️  Producto sin ID: {producto.get('nombre', '?')}")
                continue
            
            success = sync_mgr.add_to_queue(
                usuario_id=str(uid_int),
                tipo_dato='productos',
                operacion='CREATE',
                registro_id=producto_id,
                contenido=producto
            )
            
            if success:
                added_count += 1
            else:
                print(f"   ⚠️  No se pudo agregar: {producto.get('nombre', '?')}")
        
        print(f"\n✓ {added_count}/{len(productos_locales)} productos agregados a la cola")
        
        # 5. Sincronizar
        print(f"\n⏱️  Sincronizando con servidor...")
        try:
            stats = sync_mgr.sync_now(str(uid_int))
            
            print(f"\n📊 Resultado de sincronización:")
            print(f"   - Sincronizados: {stats.get('sincronizados', 0)}")
            print(f"   - Errores: {stats.get('errores', 0)}")
            print(f"   - Pendientes: {stats.get('pendientes', 0)}")
            
            if stats.get('sincronizados', 0) > 0:
                print(f"\n✅ Sincronización exitosa!")
            else:
                print(f"\n⚠️  No se sincronizaron items (revisar logs)")
        except Exception as e:
            print(f"❌ Error sincronizando: {e}")
            import traceback
            traceback.print_exc()
        
        # 6. Verificar resultado final
        print(f"\n🔍 Verificando servidor después de sincronización...")
        try:
            import time
            time.sleep(2)  # Esperar un poco para que el servidor procese
            
            productos_remotos_nuevos = obtener_productos_remoto(uid_int)
            print(f"   Servidor ahora: {len(productos_remotos_nuevos) if productos_remotos_nuevos else 0} productos")
            
            if productos_remotos_nuevos and len(productos_remotos_nuevos) > 0:
                print(f"\n✅ ¡ÉXITO! Servidor restaurado con {len(productos_remotos_nuevos)} productos")
            else:
                print(f"\n⚠️  Servidor aún muestra 0 productos (puede tardar en actualizar)")
        except Exception as e:
            print(f"❌ Error verificando: {e}")
    
    print(f"\n{'=' * 70}")
    print("✅ RESTAURACIÓN COMPLETADA")
    print(f"{'=' * 70}")
    print("\nPróximos pasos:")
    print("1. Cierra esta ventana")
    print("2. Abre la app y ve a Inventario")
    print("3. Deberías ver los 16 productos restaurados")
    print("4. Si ves 0, haz clic en 'Sincronizar Ahora'")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelado por usuario")
    except Exception as e:
        print(f"\n\n❌ Error general: {e}")
        import traceback
        traceback.print_exc()
