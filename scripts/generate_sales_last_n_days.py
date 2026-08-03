"""Genera ventas sintéticas para los últimos N días y las añade a VISO/1/data/ventas.json.
Hace un backup del archivo antes de modificar.
Formato de fecha utilizado: dd/mm/YYYY HH:MM:SS
"""
import os
import json
import random
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VENTAS_PATH = BASE_DIR / "VISO" / "1" / "data" / "ventas.json"

def backup_file(path: Path):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    try:
        path.replace(backup)
        # After move, restore original by copying backup back so we keep file name for further writes
        import shutil
        shutil.copy(backup, path)
        return backup
    except Exception as e:
        print(f"No se pudo crear backup: {e}")
        return None


def random_time_for_date(d: datetime.date):
    hour = random.randint(9, 18)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime.datetime(d.year, d.month, d.day, hour, minute, second)


def generate_sale(dtime: datetime.datetime):
    # Productos de ejemplo
    productos = [
        ("lentes de sol", 11.0),
        ("armazón clásico", 45.0),
        ("lentes graduados", 75.0),
        ("montura infantil", 30.0),
        ("limpiador lentes", 5.0)
    ]
    num_items = random.randint(1, 2)
    items = []
    total = 0.0
    for _ in range(num_items):
        prod, price = random.choice(productos)
        cantidad = random.randint(1, 3)
        subtotal = round(price * cantidad, 2)
        items.append({
            "producto": prod,
            "cantidad": cantidad,
            "subtotal": subtotal,
            "precio_unitario": price
        })
        total += subtotal

    sale = {
        "fecha": dtime.strftime("%d/%m/%Y %H:%M:%S"),
        "paciente_dni": f"{random.randint(10000000, 99999999):08d}",
        "items": items,
        "total": round(total, 2),
        "metodo_pago": random.choice(["efectivo", "tarjeta", "transferencia"]) 
    }
    return sale


def main(days: int = 15, min_per_day=1, max_per_day=3):
    if not VENTAS_PATH.exists():
        print(f"Archivo no encontrado: {VENTAS_PATH}")
        return

    # Leer ventas actuales
    with open(VENTAS_PATH, "r", encoding="utf-8") as f:
        try:
            ventas = json.load(f)
        except Exception:
            ventas = []

    # Backup
    backup = backup_file(VENTAS_PATH)
    if backup:
        print(f"Backup creado: {backup}")

    added = 0
    added_per_day = {}
    today = datetime.date.today()
    for delta in range(days):
        d = today - datetime.timedelta(days=delta)
        n = random.randint(min_per_day, max_per_day)
        added_per_day[d.strftime("%d/%m/%Y")] = n
        for _ in range(n):
            dtime = random_time_for_date(d)
            sale = generate_sale(dtime)
            ventas.append(sale)
            added += 1

    # Sort ventas by date ascending
    def parse_fecha(s):
        try:
            return datetime.datetime.strptime(s["fecha"], "%d/%m/%Y %H:%M:%S")
        except Exception:
            return datetime.datetime.min

    ventas.sort(key=parse_fecha)

    # Escribir archivo actualizado
    with open(VENTAS_PATH, "w", encoding="utf-8") as f:
        json.dump(ventas, f, indent=4, ensure_ascii=False)

    print(f"Se añadieron {added} ventas en total.")
    for day, count in sorted(added_per_day.items()):
        print(f"  {day}: {count} ventas")
    print(f"Archivo actualizado: {VENTAS_PATH}")

if __name__ == '__main__':
    main(days=15, min_per_day=1, max_per_day=3)
