"""
Script para verificar qué datos tienen los productos cargados
"""

import os
import sys
import json

sys.path.insert(0, '.')

print("="*80)
print("🔍 DIAGNÓSTICO - ESTRUCTURA DE PRODUCTOS")
print("="*80)

# Obtener lista de usuarios
from utils.file_handler import cargar_usuarios, cargar_productos, get_user_file_path

usuarios = cargar_usuarios() or {}
print(f"\n📋 Usuarios en el sistema: {list(usuarios.keys())}")

for username, info in usuarios.items():
    print(f"\n\n👤 Usuario: {username}")
    print("-" * 80)
    
    # Cargar productos
    productos = cargar_productos(username)
    print(f"📦 Total productos cargados: {len(productos)}")
    
    if productos:
        # Mostrar primer producto
        p = productos[0]
        print(f"\n🔍 PRIMER PRODUCTO (estructura):")
        print(f"  Tipo: {type(p)}")
        print(f"  Campos: {list(p.keys()) if isinstance(p, dict) else 'N/A'}")
        
        # Mostrar algunos campos importantes
        important_fields = ['codigo', 'nombre', 'image_path', 'imagen', 'ruta_imagen']
        print(f"\n  Campos importantes:")
        for field in important_fields:
            if isinstance(p, dict) and field in p:
                value = p[field]
                if isinstance(value, str) and len(value) > 60:
                    print(f"    {field}: {value[:60]}...")
                else:
                    print(f"    {field}: {value}")
            else:
                print(f"    {field}: ❌ NO EXISTE")
        
        # Mostrar primeros 3 productos
        print(f"\n📋 Primeros 3 productos (resumen):")
        for i, prod in enumerate(productos[:3]):
            if isinstance(prod, dict):
                print(f"  {i+1}. {prod.get('codigo', 'N/A'):20s} - {prod.get('nombre', 'N/A'):30s}")
                image_path = prod.get('image_path') or prod.get('imagen') or prod.get('ruta_imagen')
                if image_path:
                    exists = "✅ EXISTE" if os.path.exists(image_path) else "❌ NO EXISTE"
                    print(f"     Imagen: {image_path} ({exists})")
                else:
                    print(f"     Imagen: ❌ SIN RUTA")
    else:
        print("❌ No hay productos cargados")

print("\n" + "="*80)
