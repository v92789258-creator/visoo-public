#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Limpiar SYNC_ALL pendientes para testuser"""

import sqlite3
from pathlib import Path

base_dir = Path(__file__).parent
sync_db = base_dir / "VISO" / ".sync_queue.db"

print(f"Limpiando BD: {sync_db}")

conn = sqlite3.connect(str(sync_db))
cursor = conn.cursor()

# Ver qué hay antes
cursor.execute("""
    SELECT id, usuario_id, tipo_dato, operacion, estado 
    FROM sync_queue 
    WHERE usuario_id LIKE '%testuser%' OR usuario_id LIKE '%test_user%'
    ORDER BY timestamp DESC
""")
items_antes = cursor.fetchall()
print(f"\nItems ANTES de limpiar ({len(items_antes)}):")
for item in items_antes:
    print(f"  {item}")

# Limpiar SYNC_ALL de productos para testuser
cursor.execute("""
    DELETE FROM sync_queue 
    WHERE usuario_id IN ('testuser', 'test_user') 
    AND tipo_dato = 'productos' 
    AND operacion = 'SYNC_ALL'
""")
deleted = cursor.rowcount
print(f"\n✓ Eliminados {deleted} SYNC_ALL de productos")

# Limpiar DELETE de productos también
cursor.execute("""
    DELETE FROM sync_queue 
    WHERE usuario_id IN ('testuser', 'test_user') 
    AND tipo_dato = 'productos' 
    AND operacion = 'DELETE'
""")
deleted_deletes = cursor.rowcount
print(f"✓ Eliminados {deleted_deletes} DELETE de productos")

conn.commit()

# Ver qué queda
cursor.execute("""
    SELECT id, usuario_id, tipo_dato, operacion, estado 
    FROM sync_queue 
    WHERE usuario_id LIKE '%testuser%' OR usuario_id LIKE '%test_user%'
    ORDER BY timestamp DESC
""")
items_despues = cursor.fetchall()
print(f"\nItems DESPUÉS de limpiar ({len(items_despues)}):")
for item in items_despues:
    print(f"  {item}")

conn.close()
print("\n✅ Limpieza completada")
