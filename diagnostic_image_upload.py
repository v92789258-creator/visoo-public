"""
Script de diagnóstico para identificar por qué las imágenes no se suben
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

print("="*80)
print("🔍 DIAGNÓSTICO DE UPLOAD DE IMÁGENES")
print("="*80)

# 1. Verificar que la función existe en api_handler.py
print("\n1️⃣ VERIFICAR FUNCIÓN subir_imagenes_productos()")
try:
    sys.path.insert(0, '.')
    from utils.api_handler import subir_imagenes_productos
    print("✅ Función importada correctamente")
except ImportError as e:
    print(f"❌ Error importando: {e}")
    sys.exit(1)

# 2. Verificar datos en SQLite local
print("\n2️⃣ VERIFICAR PRODUCTOS EN SQLITE LOCAL")
db_path = 'data/viso_app.db'
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ver si hay productos
        cursor.execute("SELECT COUNT(*) FROM productos")
        count = cursor.fetchone()[0]
        print(f"✅ Total productos en BD local: {count}")
        
        # Ver algunos productos con campo image_path
        cursor.execute("""
            SELECT codigo, nombre, image_path 
            FROM productos 
            LIMIT 5
        """)
        
        products = cursor.fetchall()
        print(f"\n📋 Muestra de productos:")
        for codigo, nombre, image_path in products:
            has_image = image_path and os.path.exists(image_path)
            status = "✅ EXISTE" if has_image else "❌ NO EXISTE O VACÍO"
            print(f"  {codigo:20s} {nombre:30s}")
            print(f"    image_path: {image_path}")
            print(f"    {status}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error leyendo BD: {e}")
else:
    print(f"❌ BD no encontrada: {db_path}")

# 3. Verificar que la función llama al PHP correctamente
print("\n3️⃣ VERIFICAR FUNCIÓN subir_imagenes_productos()")
try:
    # Leer el código fuente
    with open('utils/api_handler.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar la función
    if 'def subir_imagenes_productos' in content:
        print("✅ Función definida en api_handler.py")
        
        # Verificar que hace POST a endpoint correcto
        if 'upload_product_image.php' in content:
            print("✅ Hace POST a upload_product_image.php")
        else:
            print("❌ NO hace POST a upload_product_image.php")
        
        # Verificar que abre archivos
        if 'open(' in content and 'rb' in content:
            print("✅ Abre archivos en modo binary")
        else:
            print("❌ NO abre archivos correctamente")
        
        # Buscar sección de la función
        lines = content.split('\n')
        in_function = False
        for i, line in enumerate(lines):
            if 'def subir_imagenes_productos' in line:
                in_function = True
                print(f"\n📝 Código de la función (líneas {i}-{min(i+30, len(lines))}):")
                for j in range(i, min(i+30, len(lines))):
                    print(f"  {j:4d}: {lines[j]}")
                break
    else:
        print("❌ Función NO definida en api_handler.py")
except Exception as e:
    print(f"❌ Error leyendo función: {e}")

# 4. Verificar que InventoryAutoSyncWorker llama la función
print("\n4️⃣ VERIFICAR QUE InventoryAutoSyncWorker LLAMA LA FUNCIÓN")
try:
    with open('gui/workers/product_refresh_worker.py', 'r', encoding='utf-8') as f:
        worker_content = f.read()
    
    if 'subir_imagenes_productos' in worker_content:
        print("✅ InventoryAutoSyncWorker llama a subir_imagenes_productos()")
        
        # Mostrar dónde la llama
        lines = worker_content.split('\n')
        for i, line in enumerate(lines):
            if 'subir_imagenes_productos' in line:
                print(f"\n   Línea {i}: {line.strip()}")
    else:
        print("❌ InventoryAutoSyncWorker NO llama a subir_imagenes_productos()")
except Exception as e:
    print(f"❌ Error verificando worker: {e}")

# 5. Verificar que inventory_page.py inicia los workers
print("\n5️⃣ VERIFICAR QUE inventory_page.py INICIA LOS WORKERS")
try:
    with open('gui/main_window_pages/inventory_page.py', 'r', encoding='utf-8') as f:
        page_content = f.read()
    
    if 'InventoryAutoSyncWorker' in page_content:
        print("✅ inventory_page.py usa InventoryAutoSyncWorker")
        
        if '_init_refresh_workers' in page_content:
            print("✅ Tiene método _init_refresh_workers()")
        else:
            print("⚠️  No tiene _init_refresh_workers()")
        
        if 'sync_completed' in page_content:
            print("✅ Conecta signal sync_completed")
        else:
            print("⚠️  No conecta signal sync_completed")
    else:
        print("❌ inventory_page.py NO usa InventoryAutoSyncWorker")
except Exception as e:
    print(f"❌ Error verificando inventory_page.py: {e}")

print("\n" + "="*80)
print("✅ DIAGNÓSTICO COMPLETADO")
print("="*80)
