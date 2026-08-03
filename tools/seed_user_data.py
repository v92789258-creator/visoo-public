import argparse
import datetime as dt
import json
import random
import shutil
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
VISO_DIR = BASE_DIR / "VISO"


FIRST_NAMES_M = [
    "ALEX", "LUIS", "CARLOS", "BRUNO", "MATEO", "JOSE", "DIEGO", "JULIO", "MIGUEL", "PABLO",
    "RICARDO", "DAVID", "RODRIGO", "SERGIO", "ANDRES", "MARIO", "VICTOR", "EDUARDO",
]
FIRST_NAMES_F = [
    "MIA", "SOFIA", "ANA", "PAOLA", "KAREN", "VALERIA", "KATIA", "MARIA", "CAMILA", "DANIELA",
    "LAURA", "GABRIELA", "ELENA", "PATRICIA", "MONICA", "SANDRA", "LUCIA", "NATALIA",
]
LAST_NAMES = [
    "MONTES", "TORPOCO", "RODRIGUEZ", "VARGAS", "DIAZ", "PEREZ", "GOMEZ", "FLORES", "RAMIREZ",
    "SANCHEZ", "SILVA", "CASTILLO", "RIVERA", "HERRERA", "ROJAS", "GARCIA",
]

MATERIALES = ["ACETATO", "METAL", "TR90", "CR-39", "POLICARBONATO", "TRIVEX", "MICROFIBRA", "PLASTICO", "HIDROGEL", "SILICONA-HIDROGEL"]
MARCAS = ["VISIONPRO", "OPTILUX", "EYECARE", "ZENITH", "AURORA", "CLARITY", "NOVA", "LUMINA"]
SECCIONES = [
    ("MONTURAS", "MONTURAS"),
    ("LENTES", "LENTES"),
    ("CONTACTO", "LENTES DE CONTACTO"),
    ("ACCESORIOS", "ACCESORIOS"),
]
PRODUCTOS_TIPOS = {
    "MONTURAS": ["MONTURA CLASICA", "MONTURA RECTANGULAR", "MONTURA REDONDA", "MONTURA AVIADOR", "MONTURA CAT EYE"],
    "LENTES": ["LENTE MONOFOCAL", "LENTE BIFOCAL", "LENTE PROGRESIVO", "LENTE FILTRO AZUL"],
    "CONTACTO": ["CONTACTO DIARIO", "CONTACTO QUINCENAL", "CONTACTO MENSUAL"],
    "ACCESORIOS": ["ESTUCHE", "CORDON", "PANO MICROFIBRA", "SPRAY LIMPIADOR", "KIT MANTENIMIENTO"],
}


def _now_ts():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _backup_file(path: Path, backup_root: Path):
    try:
        if path.exists() and path.is_file():
            rel = path.relative_to(VISO_DIR)
            dest = backup_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(path), str(dest))
    except Exception:
        pass


def _rand_date(start: dt.date, end: dt.date) -> dt.date:
    if end <= start:
        return start
    days = (end - start).days
    return start + dt.timedelta(days=random.randint(0, days))


def _fmt_fecha(d: dt.date) -> str:
    return d.strftime("%d/%m/%Y")


def _fmt_datetime(d: dt.datetime) -> str:
    return d.strftime("%d/%m/%Y %H:%M:%S")


def _gen_dni(used: set[str]) -> str:
    while True:
        dni = str(random.randint(10000000, 79999999))
        if dni not in used:
            used.add(dni)
            return dni


def _gen_nombre(genero: str) -> str:
    if genero == "Masculino":
        fn = random.choice(FIRST_NAMES_M)
    else:
        fn = random.choice(FIRST_NAMES_F)
    ln1 = random.choice(LAST_NAMES)
    ln2 = random.choice(LAST_NAMES)
    return f"{fn} {ln1} {ln2}".upper()


def _calc_edad(nacimiento: dt.date, hoy: dt.date) -> int:
    years = hoy.year - nacimiento.year
    if (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day):
        years -= 1
    return max(0, years)


def gen_clientes(n: int, hoy: dt.date) -> list[dict]:
    used_dni: set[str] = set()
    clientes: list[dict] = []
    for _ in range(n):
        genero = random.choice(["Masculino", "Femenino"])
        nacimiento = _rand_date(dt.date(1945, 1, 1), dt.date(2015, 12, 31))
        edad = _calc_edad(nacimiento, hoy)
        registro = _rand_date(hoy - dt.timedelta(days=75), hoy)
        etiquetas = ["Falta pagar"] if random.random() < 0.55 else ["Pagado"]

        dni = _gen_dni(used_dni)
        nombre = _gen_nombre(genero)

        c = {
            "dni": dni,
            "nombre": nombre,
            "fecha_nacimiento": nacimiento.strftime("%Y-%m-%d"),
            "edad": edad,
            "genero": genero,
            "fecha_registro": _fmt_fecha(registro),
            "etiquetas": etiquetas,
        }

        # Extras opcionales (campos usados por UI: telefono/email)
        if random.random() < 0.85:
            c["telefono"] = "9" + str(random.randint(10000000, 99999999))
        if random.random() < 0.70:
            c["email"] = f"cliente{dni}@correo.com"
            # Compatibilidad con versiones que usan "correo"
            c["correo"] = c["email"]
        if random.random() < 0.40:
            c["direccion"] = ""
            c["empresa"] = ""
            c["notas"] = ""

        clientes.append(c)
    return clientes


def gen_optometras() -> list[str]:
    base = ["OPTO 1", "OPTO 2", "OPTO 3", "OPTO 4"]
    return base


def _gen_rx_block(distp: str | None = None) -> dict:
    # Mantener strings como en datasets existentes
    return {
        "esferico": f"{random.uniform(-6, 3):.2f}".rstrip("0").rstrip("."),
        "cilindro": f"{random.uniform(-3, 0):.2f}".rstrip("0").rstrip("."),
        "eje": str(random.randint(1, 180)),
        "av": random.choice(["20/20", "20/30", "20/40"]),
        "adicmedia": f"{random.uniform(0, 3):.2f}".rstrip("0").rstrip("."),
        "prisma": "",
        "distp": distp or "",
    }


def gen_pacientes(clientes: list[dict], optometras: list[str], n: int, hoy: dt.date, username: str) -> list[dict]:
    if not clientes:
        return []
    picks = random.sample(clientes, k=min(n, len(clientes)))
    pacientes: list[dict] = []
    for c in picks:
        dni = str(c.get("dni", "") or "")
        nombre = str(c.get("nombre", "") or "")
        genero = str(c.get("genero", "") or "Masculino")
        fecha_nac = str(c.get("fecha_nacimiento", "") or "1980-01-01")
        try:
            nacimiento = dt.date.fromisoformat(fecha_nac)
        except Exception:
            nacimiento = dt.date(1980, 1, 1)

        historial: list[dict] = []
        num_grads = random.randint(1, 3)
        for _ in range(num_grads):
            fecha = _rand_date(hoy - dt.timedelta(days=120), hoy)
            prox = fecha + dt.timedelta(days=random.randint(25, 95))
            opto = random.choice(optometras) if optometras else ""
            total = round(random.uniform(35, 180), 2)

            # Parcial en ~35% de graduaciones
            pagos_parciales = []
            monto_adelanto = None
            es_parcial = random.random() < 0.35
            if es_parcial:
                pagado = round(total * random.uniform(0.15, 0.75), 2)
                monto_adelanto = pagado
                pagos_parciales = [
                    {"fecha": dt.datetime.now().strftime("%d/%m/%Y %H:%M"), "monto": pagado, "observacion": "Adelanto"}
                ]

            lejos_distp = str(random.randint(58, 67))
            cerca_distp = str(random.randint(54, 62))

            grad = {
                "fecha": _fmt_fecha(fecha),
                "proxima_cita": _fmt_fecha(prox),
                "optometra": opto,
                "monto_cobrado": total,
                "lejos_od": _gen_rx_block(distp=lejos_distp),
                "lejos_oi": _gen_rx_block(distp=""),
                "lejos_distp": lejos_distp,
                "cerca_od": _gen_rx_block(distp=cerca_distp),
                "cerca_oi": _gen_rx_block(distp=""),
                "cerca_distp": cerca_distp,
                "observacion": random.choice(["Control", "Cambio de montura", "Molestia ocular", ""]),
                "motilidad_versiones": {},
                "items_venta": [],
                "es_pago_parcial": bool(es_parcial),
                "monto_adelanto": monto_adelanto,
                "pagos_parciales": pagos_parciales,
                "registrado_por": username,
            }
            historial.append(grad)

        # Fecha "principal" como ultima graduacion
        historial_sorted = sorted(historial, key=lambda x: x.get("fecha", ""), reverse=True)
        fecha_principal = historial_sorted[0].get("fecha", _fmt_fecha(hoy))

        p = {
            "dni": dni,
            "nombre": nombre,
            "fecha": fecha_principal,
            "edad": _calc_edad(nacimiento, hoy),
            "genero": genero,
            "fecha_nacimiento": nacimiento.strftime("%Y-%m-%d"),
            "historial_graduaciones": historial,
        }

        # Campos adicionales usados en tabla/listas
        telefono = str(c.get("telefono") or "").strip()
        if not telefono and random.random() < 0.9:
            telefono = "9" + str(random.randint(10000000, 99999999))
        email = str(c.get("email") or c.get("correo") or "").strip()
        if not email and random.random() < 0.8:
            email = f"paciente{dni}@correo.com"

        ultima_visita = ""
        try:
            ultima_visita = dt.datetime.strptime(str(fecha_principal), "%d/%m/%Y").date().isoformat()
        except Exception:
            ultima_visita = ""

        if telefono:
            p["telefono"] = telefono
        if email:
            p["email"] = email
        if ultima_visita:
            p["ultima_visita"] = ultima_visita
        pacientes.append(p)
    return pacientes


def gen_productos(n: int, branch_prefix: str, ahora: dt.datetime) -> list[dict]:
    productos: list[dict] = []
    for idx in range(1, n + 1):
        seccion, categoria = random.choice(SECCIONES)
        tipo = random.choice(PRODUCTOS_TIPOS.get(seccion, ["PRODUCTO"]))
        codigo = f"{branch_prefix}-{idx:03d}"
        nombre = f"{tipo} {codigo}"
        costo = round(random.uniform(10, 220), 2)
        venta = round(costo * random.uniform(1.4, 3.2), 2)
        stock = random.randint(0, 80)
        productos.append(
            {
                "nombre": nombre,
                "costo": costo,
                "venta": venta,
                "stock": stock,
                "image_path": None,
                "material": random.choice(MATERIALES),
                "marca": random.choice(MARCAS),
                "categoria": categoria,
                "seccion": seccion,
                "created_at": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                "codigo": codigo,
            }
        )
    return productos


def gen_ventas(productos: list[dict], pacientes: list[dict], n: int, username: str, hoy: dt.date) -> list[dict]:
    if not productos or not pacientes:
        return []

    metodos = ["Efectivo", "Yape", "Plin", "Transferencia", "Tarjeta"]
    ventas: list[dict] = []
    base_epoch = int(dt.datetime.now().timestamp())

    for i in range(n):
        pac = random.choice(pacientes)
        dni = str(pac.get("dni", "") or "")
        nombre = str(pac.get("nombre", "") or "")

        when = dt.datetime.combine(_rand_date(hoy - dt.timedelta(days=120), hoy), dt.time(hour=random.randint(8, 20), minute=random.randint(0, 59), second=random.randint(0, 59)))
        items = []
        num_items = random.randint(1, 4)
        picks = random.sample(productos, k=min(num_items, len(productos)))
        subtotal = 0.0
        for prod in picks:
            precio = float(prod.get("venta", 0) or 0)
            cantidad = random.randint(1, 3)
            total_item = round(precio * cantidad, 2)
            subtotal += total_item
            items.append(
                {
                    "nombre": prod.get("nombre", ""),
                    "cantidad": cantidad,
                    "total": total_item,
                    "precio_unitario": round(precio, 2),
                }
            )

        subtotal = round(subtotal, 2)
        igv = round(subtotal * 0.18, 2)
        total = round(subtotal + igv, 2)
        descuento = round(random.choice([0, 0, 0, random.uniform(1, 7)]), 2)
        total_desc = max(0.0, round(total - descuento, 2))

        es_parcial = random.random() < 0.35
        if es_parcial:
            pagado = round(total_desc * random.uniform(0.2, 0.8), 2)
        else:
            pagado = total_desc

        venta_id = f"V{base_epoch}{i:04d}"
        venta = {
            "fecha": _fmt_datetime(when),
            "paciente_dni": dni,
            "paciente_nombre": nombre,
            "usuario": username,
            "helper_name": None,
            "items": items,
            "subtotal": subtotal,
            "igv": igv,
            "total": total_desc,
            "descuento_total": descuento,
            "metodo_pago": random.choice(metodos),
            "es_pago_parcial": bool(es_parcial),
            "monto_pagado": pagado,
            "vendedor": username,
            "id": venta_id,
        }

        if es_parcial:
            faltante = round(max(0.0, total_desc - pagado), 2)
            venta.update(
                {
                    "deuda_id": f"D{venta_id}",
                    "es_pago_partes": True,
                    "monto_faltante": faltante,
                    "monto_adelanto": pagado,
                }
            )

        ventas.append(venta)

    return ventas


def seed_user(username: str, clients_n: int, patients_n: int, sales_n: int, products_n: int):
    random.seed(1337)
    hoy = dt.date.today()
    ahora = dt.datetime.now().replace(microsecond=0)

    user_root = VISO_DIR / username
    local_data_dir = user_root / "data"
    cache_data_dir = user_root / "branch_cache" / f"MADRE-{username.upper()}" / "data"

    backup_root = VISO_DIR / "_seed_backups" / f"{username}-{_now_ts()}"

    targets = [
        local_data_dir / "clientes.json",
        local_data_dir / "pacientes.json",
        local_data_dir / "ventas.json",
        local_data_dir / "optometras.json",
        local_data_dir / "metodos_pago.json",
        local_data_dir / "productos.json",
        cache_data_dir / "clientes.json",
        cache_data_dir / "pacientes.json",
        cache_data_dir / "ventas.json",
        cache_data_dir / "optometras.json",
        cache_data_dir / "metodos_pago.json",
        cache_data_dir / "productos.json",
    ]

    for fp in targets:
        _backup_file(fp, backup_root)

    optometras = gen_optometras()
    clientes = gen_clientes(clients_n, hoy)
    pacientes = gen_pacientes(clientes, optometras, patients_n, hoy, username=username)
    productos = gen_productos(products_n, branch_prefix="MADRE", ahora=ahora)
    ventas = gen_ventas(productos, pacientes, sales_n, username=username, hoy=hoy)

    metodos_pago = ["Efectivo", "Yape", "Plin", "Transferencia", "Tarjeta"]

    payloads = {
        "clientes.json": clientes,
        "pacientes.json": pacientes,
        "ventas.json": ventas,
        "optometras.json": optometras,
        "metodos_pago.json": metodos_pago,
        "productos.json": productos,
    }

    for name, data in payloads.items():
        _write_json(local_data_dir / name, data)
        _write_json(cache_data_dir / name, data)

    # Asegurar etiquetas default para clientes si no existen
    etiquetas = ["Falta pagar", "Pagado"]
    _write_json(local_data_dir / "clientes_etiquetas.json", etiquetas)
    _write_json(cache_data_dir / "clientes_etiquetas.json", etiquetas)

    return {
        "local_dir": str(local_data_dir),
        "cache_dir": str(cache_data_dir),
        "backup_dir": str(backup_root),
        "counts": {
            "clientes": len(clientes),
            "pacientes": len(pacientes),
            "ventas": len(ventas),
            "productos": len(productos),
            "optometras": len(optometras),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="alex")
    ap.add_argument("--clients", type=int, default=80)
    ap.add_argument("--patients", type=int, default=45)
    ap.add_argument("--sales", type=int, default=120)
    ap.add_argument("--products", type=int, default=60)
    args = ap.parse_args()

    res = seed_user(args.user, args.clients, args.patients, args.sales, args.products)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
