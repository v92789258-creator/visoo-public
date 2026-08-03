#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECUPERACION: Cargar todos los datos del servidor y guardarlos localmente
Uso cuando la carpeta VISO se borra o se corrompe
"""
import sys
import os
import json
from datetime import datetime

# Fix encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("\n" + "="*80)
print("RECUPERACION DE DATOS DESDE SERVIDOR")
print("="*80)

# Para hacer pruebas, pedir usuario_id
usuario_id = input("\nIngresa el usuario_id (ejemplo: alex9121 o 45453073): ").strip()

if not usuario_id:
    print("ERROR: usuario_id no especificado")
    exit(1)

print(f"\nRecuperando datos para usuario: {usuario_id}")
print("...")

try:
    from utils.api_handler import (
        obtener_productos_remoto,
        obtener_pacientes_remoto,
        obtener_ventas_remoto
    )
    from utils.file_handler import (
        guardar_productos,
        guardar_pacientes,
        guardar_ventas
    )
    
    # Crear directorio si no existe
    data_dir = os.path.join("VISO", usuario_id, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"\nDirectorio: {data_dir}")
    
    # PRODUCTOS
    print("\n[1/3] Cargando productos del servidor...")
    try:
        productos = obtener_productos_remoto(usuario_id)
        if productos:
            guardar_productos(usuario_id, productos)
            print(f"  ✓ {len(productos)} productos descargados y guardados")
        else:
            print("  ⚠ No hay productos en servidor")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # PACIENTES
    print("\n[2/3] Cargando pacientes del servidor...")
    try:
        pacientes = obtener_pacientes_remoto(usuario_id)
        if pacientes:
            guardar_pacientes(usuario_id, pacientes)
            print(f"  ✓ {len(pacientes)} pacientes descargados y guardados")
        else:
            print("  ⚠ No hay pacientes en servidor")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # VENTAS
    print("\n[3/3] Cargando ventas del servidor...")
    try:
        ventas = obtener_ventas_remoto(usuario_id)
        if ventas:
            guardar_ventas(usuario_id, ventas)
            print(f"  ✓ {len(ventas)} ventas descargadas y guardadas")
        else:
            print("  ⚠ No hay ventas en servidor")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    print("\n" + "="*80)
    print("RECUPERACION COMPLETADA")
    print("="*80)
    print(f"\nDatos restaurados en: {data_dir}")
    print("\nProximos pasos:")
    print("1. Cierra la app si está abierta")
    print("2. Reabre la app")
    print("3. Navega a Inventario")
    print("4. Verifica que los datos están ahí")
    print("\nNOTA: No uses 'Sincronizar Ahora' hasta confirmar que los datos se ven bien")
    
except Exception as e:
    print(f"\nERROR CRÍTICO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
