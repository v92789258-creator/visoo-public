"""
Script para sincronizar productos locales a BD remota (primera vez)
"""

import sys
import json

sys.path.insert(0, '.')

from utils.file_handler import cargar_usuarios, cargar_productos
from utils.sync_manager import SyncManager

print("="*80)
print("SINCRONIZAR PRODUCTOS LOCALES -> BD REMOTA")
print("="*80)

# Obtener usuario
usuarios = cargar_usuarios() or {}
if not usuarios:
    print("❌ No hay usuarios")
    sys.exit(1)

username = list(usuarios.keys())[0]
usuario_id = int(username) if username.isdigit() else None

print(f"\n👤 Usuario: {username}")
print(f"🔐 ID: {usuario_id}")

# Cargar productos locales
productos = cargar_productos(username)
print(f"\n📦 Productos locales: {len(productos)}")

if not productos:
    print("❌ No hay productos locales para sincronizar")
    sys.exit(1)

# Mostrar primeros 2
for i, p in enumerate(productos[:2], 1):
    print(f"  {i}. {p.get('codigo')}: {p.get('nombre')}")

# Sincronizar a BD remota
print(f"\n📤 SINCRONIZANDO A BD REMOTA...")
sync_manager = SyncManager(username)
result = sync_manager.sync()

if result:
    print(f"\n✅ SINCRONIZADO")
    print(f"  OK: {result.get('OK', 0)}")
    print(f"  Errores: {result.get('XX', 0)}")
    print(f"  Pendientes: {result.get('PENDING', 0)}")
else:
    print(f"\n⚠️ Sync retornó None")

print("\n" + "="*80)
print("Ahora verifica que get_productos.php retorna los productos")
print("="*80)
