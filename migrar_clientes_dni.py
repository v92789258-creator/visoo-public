#!/usr/bin/env python3
"""
Script para migrar clientes existentes y asignarles DNI '0000000' si no tienen
"""
import json
import os
import getpass

def migrar_clientes():
    """Agrega DNI por defecto a clientes que no lo tienen"""
    try:
        username = getpass.getuser()
        base_path = f"VISO/{username}/data"
        os.makedirs(base_path, exist_ok=True)
        clientes_path = os.path.join(base_path, "clientes.json")
        
        if not os.path.exists(clientes_path):
            print(f"✓ No hay archivo de clientes para migrar en: {clientes_path}")
            return
        
        # Cargar clientes existentes
        with open(clientes_path, 'r', encoding='utf-8') as f:
            clientes = json.load(f)
        
        migrados = 0
        for cliente in clientes:
            if 'dni' not in cliente or not cliente['dni']:
                cliente['dni'] = '0000000'
                migrados += 1
        
        # Guardar cambios
        with open(clientes_path, 'w', encoding='utf-8') as f:
            json.dump(clientes, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Migración completada")
        print(f"  - Total de clientes: {len(clientes)}")
        print(f"  - Clientes actualizados con DNI por defecto: {migrados}")
        
    except Exception as e:
        print(f"✗ Error durante migración: {e}")

if __name__ == "__main__":
    migrar_clientes()
