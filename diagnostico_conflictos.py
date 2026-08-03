#!/usr/bin/env python3
"""
Diagnóstico de conflictos de citas
"""
import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent))

from utils.appointments_model import AppointmentStatus, AppointmentsManager

def diagnosticar():
    # Obtener el usuario actual
    username = "admin"
    
    manager = AppointmentsManager(username)
    print(f"\n📋 DIAGNÓSTICO DE CITAS - Usuario: {username}")
    print(f"Total de citas cargadas: {len(manager.citas)}\n")
    
    if not manager.citas:
        print("❌ No hay citas cargadas")
        return
    
    print("=" * 80)
    print("CITAS CARGADAS:")
    print("=" * 80)
    
    for i, cita in enumerate(manager.citas, 1):
        print(f"\n{i}. ID: {cita.cita_id}")
        print(f"   DNI: {cita.dni}")
        print(f"   Fecha: {cita.fecha}")
        print(f"   Hora: {cita.hora}")
        print(f"   Duración: {cita.duracion_minutos} min")
        print(f"   Estado: {cita.estado.value if hasattr(cita.estado, 'value') else cita.estado}")
        print(f"   Doctor: {cita.doctor}")
    
    print("\n" + "=" * 80)
    print("PRUEBA DE CONFLICTOS:")
    print("=" * 80)
    
    # Prueba de 24/01/2026 a las 10:00
    fecha_test = "2026-01-24"
    hora_test = "10:00"
    duracion_test = 30
    
    print(f"\n🔍 Probando: {fecha_test} {hora_test} (duración: {duracion_test} min)")
    
    hay_conflicto = manager.hay_conflicto(fecha_test, hora_test, duracion_test)
    print(f"Resultado: {'❌ CONFLICTO' if hay_conflicto else '✅ DISPONIBLE'}")
    
    # Mostrar detalles
    print(f"\nCitas en fecha {fecha_test}:")
    citas_fecha = manager.obtener_citas_fecha(fecha_test)
    if citas_fecha:
        for cita in citas_fecha:
            print(f"  - {cita.hora} ({cita.duracion_minutos}min) - Estado: {cita.estado.value if hasattr(cita.estado, 'value') else cita.estado}")
    else:
        print("  (ninguna)")

if __name__ == "__main__":
    diagnosticar()
