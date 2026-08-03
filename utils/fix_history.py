import json
from pathlib import Path
import sys

# Agregar la ruta de utils para poder importar file_handler si es necesario
sys.path.append(r"C:\Users\USUARIO.DESKTOP-NOO0BDB\Desktop\VISO VERSIONES\4.1\viso version 4.2.4")

from utils.file_handler import cargar_ventas, guardar_ventas, cargar_pacientes, guardar_pacientes

users = ["alex9121", "NANCY", "Usuario"]

for user in users:
    print(f"\n--- Procesando usuario: {user} ---")
    
    # 1. FIX VENTAS
    try:
        ventas = cargar_ventas(user)
        ventas_changed = False
        if ventas:
            for v in ventas:
                if not isinstance(v, dict):
                    continue
                if str(v.get('tipo_venta', '')).strip().lower() == 'graduacion' or str(v.get('origen', '')).strip().lower() == 'graduacion':
                    items = v.get('items', [])
                    if isinstance(items, list) and items:
                        real_total = 0.0
                        for i in items:
                            if isinstance(i, dict):
                                precio_u = float(i.get('precio_unitario', i.get('precio', 0)) or 0)
                                cant = float(i.get('cantidad', 1) or 1)
                                sub_i = float(i.get('total', i.get('subtotal', precio_u * cant)) or 0)
                                real_total += sub_i
                        
                        current_total = float(v.get('total', 0) or 0)
                        
                        if real_total > 0.01 and abs(current_total - real_total) > 0.05:
                            print(f"[Venta {v.get('id')}] Corrigiendo total: {current_total:.2f} -> {real_total:.2f}")
                            v['total'] = real_total
                            v['subtotal'] = round(real_total / 1.18, 2)
                            v['igv'] = round(real_total - v['subtotal'], 2)
                            
                            monto_pagado = float(v.get('monto_pagado', current_total) or 0)
                            # Si estaba pagado completo, ajustamos el monto pagado
                            if abs(monto_pagado - current_total) < 0.05:
                                v['monto_pagado'] = real_total
                            else:
                                v['monto_pagado'] = min(monto_pagado, real_total)
                                
                            v['monto_faltante'] = max(0.0, real_total - v['monto_pagado'])
                            ventas_changed = True
            
            if ventas_changed:
                print(f"Guardando ventas corregidas para {user}...")
                guardar_ventas(user, ventas)
            else:
                print("Todas las ventas estaban correctas.")
    except Exception as e:
        print(f"Error procesando ventas de {user}: {e}")

    # 2. FIX PACIENTES (Historial)
    try:
        pacientes = cargar_pacientes(user)
        pacientes_changed = False
        if pacientes:
            for p in pacientes:
                if not isinstance(p, dict):
                    continue
                historial = p.get('historial_graduaciones', [])
                if isinstance(historial, list):
                    for g in historial:
                        if isinstance(g, dict):
                            items = g.get('items_venta', [])
                            if isinstance(items, list) and items:
                                real_total = 0.0
                                for i in items:
                                    if isinstance(i, dict):
                                        precio_u = float(i.get('precio_unitario', i.get('precio', 0)) or 0)
                                        cant = float(i.get('cantidad', 1) or 1)
                                        sub_i = float(i.get('total', i.get('subtotal', precio_u * cant)) or 0)
                                        real_total += sub_i
                                
                                current_total = float(g.get('monto_total_venta', 0) or 0)
                                
                                if real_total > 0.01 and abs(current_total - real_total) > 0.05:
                                    print(f"[Paciente {p.get('dni')}] Corrigiendo graduación {g.get('fecha')}: {current_total:.2f} -> {real_total:.2f}")
                                    g['monto_total_venta'] = real_total
                                    pacientes_changed = True
            
            if pacientes_changed:
                print(f"Guardando pacientes corregidos para {user}...")
                guardar_pacientes(user, pacientes)
            else:
                print("Todos los pacientes estaban correctos.")
    except Exception as e:
        print(f"Error procesando pacientes de {user}: {e}")

print("\n--- PROCESO TERMINADO ---")
