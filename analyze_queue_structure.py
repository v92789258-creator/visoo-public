#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizar detalladamente la estructura de la cola de sincronización
"""
import sqlite3
import os
import sys
from datetime import datetime
from collections import defaultdict

# Fix encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_path = os.path.join("VISO", ".sync_queue.db")

if not os.path.exists(db_path):
    print(f"ERROR: Base de datos no encontrada: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n" + "="*80)
print("ANALISIS DETALLADO DE COLA DE SINCRONIZACION")
print("="*80)

# Ver estructura de tabla
cursor.execute("PRAGMA table_info(sync_queue)")
columns = cursor.fetchall()
print("\nColumnas en sync_queue:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Estadísticas por tipo de datos y operación
cursor.execute("""
    SELECT tipo_dato, operacion, COUNT(*) as count
    FROM sync_queue
    GROUP BY tipo_dato, operacion
    ORDER BY tipo_dato, operacion
""")

print("\n" + "="*80)
print("ESTADISTICAS POR TIPO Y OPERACION:")
print("="*80)

stats = cursor.fetchall()
for tipo_dato, operacion, count in stats:
    print(f"{tipo_dato:15s} | {operacion:10s} | {count:5d}")

# Ver contenido de algunos SYNC_ALL para entender el problema
cursor.execute("""
    SELECT id, usuario_id, tipo_dato, operacion, LENGTH(contenido) as contenido_size, estado
    FROM sync_queue
    WHERE operacion = 'SYNC_ALL'
    LIMIT 5
""")

print("\n" + "="*80)
print("EJEMPLO DE PRIMEROS SYNC_ALL:")
print("="*80)

examples = cursor.fetchall()
for row in examples:
    id_, user, tipo, op, size, estado = row
    print(f"[{id_:4d}] Usuario: {user:3s} | Tipo: {tipo:12s} | Tamaño contenido: {size:6d} bytes | Estado: {estado}")

# Ver si todos los SYNC_ALL tienen el mismo contenido
cursor.execute("""
    SELECT COUNT(DISTINCT contenido) as distinct_contents
    FROM sync_queue
    WHERE operacion = 'SYNC_ALL'
""")

distinct = cursor.fetchone()[0]
cursor.execute("""
    SELECT COUNT(*) as total
    FROM sync_queue
    WHERE operacion = 'SYNC_ALL'
""")
total = cursor.fetchone()[0]

print("\n" + "="*80)
print("ANALISIS DE CONTENIDO SYNC_ALL:")
print("="*80)
print(f"Total SYNC_ALL:                {total}")
print(f"SYNC_ALL unicos (por contenido): {distinct}")

if distinct == 1:
    print("\nPROBLEMA: Todos los SYNC_ALL tienen EL MISMO contenido")
    print("Esto significa que se estan creando SYNC_ALL identicos repetidamente")
    print("Deberia haber solo 1 SYNC_ALL consolidado")
elif distinct < total:
    print(f"\nADVERTENCIA: Hay {distinct} contenidos unicos en {total} SYNC_ALL")
    print("Hay duplicados de contenido")

conn.close()
