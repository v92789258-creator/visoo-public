from pathlib import Path

import json
import sys
import traceback

# Ensure project root is importable when running directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla


def main():
    user = "alex"
    base = Path("VISO") / user / "data"
    ventas = json.loads((base / "ventas.json").read_text(encoding="utf-8"))
    venta = ventas[0]

    productos = []
    for item in venta.get("items", []) or []:
        if isinstance(item, dict):
            productos.append(
                {
                    "nombre": item.get("nombre", "Producto"),
                    "cantidad": item.get("cantidad", 1),
                    "precio": item.get("precio_unitario", 0),
                    "total": item.get("total", 0),
                }
            )

    total_final = sum(float(p.get("total", 0) or 0) for p in productos)
    subtotal = total_final / 1.18 if total_final else 0.0
    igv = total_final - subtotal

    datos = {
        "nombre_optica": "Optica Alex",
        "ruc": "",
        "ruc_empresa": "",
        "direccion": "Direccion no configurada",
        "numero_boleta": f"VENTA-{venta.get('id', 'S/N')}",
        "fecha": venta.get("fecha", ""),
        "cliente": venta.get("paciente_nombre", ""),
        "productos": productos,
        "subtotal": subtotal,
        "igv": igv,
        "total": total_final,
        "descuento": venta.get("descuento_total", 0),
        "metodo_pago": venta.get("metodo_pago", "Efectivo"),
        "pie_pagina": "Gracias por su compra",
        "es_pago_parcial": bool(venta.get("es_pago_parcial", False)),
        "monto_pagado": venta.get("monto_pagado", 0),
        "vendedor": venta.get("vendedor", user),
    }

    gen = GeneradorBoletasPlantilla(user)
    print("plantilla:", gen.plantilla_seleccionada)
    try:
        pdf = gen.generar_boleta(datos)
        print("pdf:", pdf)
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()
