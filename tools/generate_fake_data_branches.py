import json
import os
import datetime
import random


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
USERNAME = "alex9121"
BRANCH_CACHE_DIR = os.path.join(ROOT, "VISO", USERNAME, "branch_cache")


FIRST_NAMES = [
    "ALEX", "LUIS", "CARLOS", "JOSE", "MIGUEL", "JUAN", "MARCO", "DIEGO", "EDUARDO", "PABLO",
    "ANA", "MARIA", "LUISA", "CARMEN", "ROSA", "ELENA", "SOFIA", "DANIELA", "VALERIA", "PAOLA",
]
LAST_NAMES_1 = [
    "MONTES", "VARGAS", "RODRIGUEZ", "TORRES", "GARCIA", "RAMIREZ", "FLORES", "SANCHEZ", "DIAZ", "RIVERA",
    "CASTILLO", "ROMERO", "HERRERA", "NAVARRO", "PEREZ", "GOMEZ", "MENDOZA", "SOTO", "SILVA", "CRUZ",
]
LAST_NAMES_2 = [
    "QUISPE", "HUAMAN", "MAMANI", "RIVAS", "SALAZAR", "AGUILAR", "FERNANDEZ", "CHAVEZ", "LOPEZ", "MORALES",
    "TORPOCO", "PACHECO", "GUERRERO", "VEGA", "CAMPOS", "VASQUEZ", "ACOSTA", "MARTINEZ", "NUNEZ", "BENAVIDES",
]


PRODUCT_NAMES = [
    "MONTURA CLASICA", "MONTURA METAL", "MONTURA ACETATO", "MONTURA SPORT",
    "LENTE BLUECUT", "LENTE PHOTOCHROMIC", "LENTE ANTIRREFLEX", "LENTE MONOFOCAL",
    "LENTE BIFOCAL", "LENTE PROGRESIVO", "LENTE POLARIZADO",
    "ESTUCHE", "PANO MICROFIBRA", "GOTAS LUBRICANTES", "SPRAY LIMPIADOR",
]
BRANDS = ["VISIONPRO", "OPTILUX", "NOVA", "CLARITY", "URBAN", "CLASSIC"]
MATERIALS = ["METAL", "ACETATO", "TR90", "POLICARBONATO", "RESINA"]
PAY_METHODS = ["efectivo", "yape", "plin", "tarjeta"]


def _read_json_list(path: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if not raw:
                return []
            data = json.loads(raw)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_json_list(path: str, data: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=True)
        f.write("\n")


def _dt_to_sale_str(dt: datetime.datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def _d_to_date_str(d: datetime.date) -> str:
    return d.strftime("%d/%m/%Y")


def _compute_age(today: datetime.date, birth: datetime.date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _pick_unique_name(rnd: random.Random, suffix: str) -> str:
    fn = rnd.choice(FIRST_NAMES)
    ln1 = rnd.choice(LAST_NAMES_1)
    ln2 = rnd.choice(LAST_NAMES_2)
    return f"{fn} {ln1} {ln2} {suffix}".strip().upper()


def _safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _max_int_id(items: list, key: str, base: int) -> int:
    m = int(base)
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            v = int(it.get(key, 0) or 0)
        except Exception:
            continue
        if v > m:
            m = v
    return m


def _make_products_if_empty(rnd: random.Random, productos: list, branch_suffix: str) -> list:
    if productos:
        return productos

    out = []
    used = set()
    created_at = datetime.datetime.now().replace(microsecond=0).isoformat()
    for i in range(20):
        base = rnd.choice(PRODUCT_NAMES)
        name = f"{base} {branch_suffix}-{i+1}"
        if name in used:
            continue
        used.add(name)

        costo = round(rnd.uniform(12, 90), 2)
        venta = round(costo * rnd.uniform(1.6, 3.2), 2)
        stock = rnd.randint(10, 60)

        seccion = "LENTES" if "LENTE" in base else "ACCESORIOS" if base in ("ESTUCHE", "PANO MICROFIBRA", "SPRAY LIMPIADOR", "GOTAS LUBRICANTES") else "MONTURAS"

        out.append(
            {
                "nombre": name.upper(),
                "costo": costo,
                "venta": venta,
                "stock": int(stock),
                "image_path": None,
                "material": rnd.choice(MATERIALS),
                "marca": rnd.choice(BRANDS),
                "categoria": seccion,
                "seccion": seccion,
                "created_at": created_at,
            }
        )
    return out


def _seed_kardex_for_products(productos: list, base_dt: datetime.datetime) -> list:
    kardex = []
    dt = base_dt
    for p in productos:
        nombre = str(p.get("nombre", "")).strip()
        if not nombre:
            continue
        cantidad = int(p.get("stock", 0) or 0)
        costo_unit = _safe_float(p.get("costo", 0), 0.0)
        kardex.append(
            {
                "fecha": _dt_to_sale_str(dt),
                "movimiento": "Entrada",
                "producto": nombre,
                "cantidad": cantidad,
                "costo_unitario": costo_unit,
                "valor_total": round(costo_unit * cantidad, 2),
                "stock_final": cantidad,
            }
        )
        dt = dt + datetime.timedelta(minutes=3)
    return kardex


def _make_pacientes_if_empty(rnd: random.Random, pacientes: list, clientes: list, branch_suffix: str) -> list:
    if pacientes:
        return pacientes

    today = datetime.date.today()
    out = []

    # pick up to 30 clientes to become pacientes
    pool = [c for c in clientes if isinstance(c, dict) and str(c.get("dni", "")).strip()]
    rnd.shuffle(pool)
    pool = pool[:30]

    for idx, c in enumerate(pool):
        dni = str(c.get("dni", "")).strip()
        nombre = str(c.get("nombre", "")).strip().upper()
        if not nombre:
            nombre = _pick_unique_name(rnd, branch_suffix)

        # Birthdate: use cliente date if present, else generate
        fnac = str(c.get("fecha_nacimiento", "")).strip()
        try:
            birth = datetime.datetime.strptime(fnac, "%Y-%m-%d").date() if fnac else None
        except Exception:
            birth = None
        if not birth:
            year = 1958 + (idx % 45)
            month = 1 + (idx % 12)
            day = 1 + ((idx * 2) % 28)
            birth = datetime.date(year, month, day)

        genero = str(c.get("genero", "")).strip() or ("Masculino" if (idx % 2 == 0) else "Femenino")
        edad = int(c.get("edad", 0) or 0)
        if edad <= 0:
            edad = _compute_age(today, birth)

        # Create 1-2 graduaciones, some partial payments to show debts.
        historial = []
        visits = 1 if rnd.random() < 0.7 else 2
        for v in range(visits):
            visit_date = today - datetime.timedelta(days=rnd.randint(0, 25))
            monto_total = round(rnd.uniform(40, 260), 2)
            pago_parcial = rnd.random() < 0.25
            adelanto = round(monto_total * rnd.uniform(0.2, 0.7), 2) if pago_parcial else monto_total
            pagos = [{"fecha": f"{_d_to_date_str(visit_date)} 10:{(v+1)*10:02d}", "monto": adelanto, "observacion": "Adelanto"}] if pago_parcial else [{"fecha": f"{_d_to_date_str(visit_date)} 10:{(v+1)*10:02d}", "monto": monto_total, "observacion": "Pago completo"}]

            grad = {
                "fecha": _d_to_date_str(visit_date),
                "optometra": "DR ALEX",
                "monto_cobrado": monto_total,
                "estado": "pendiente" if pago_parcial else "completada",
                "es_pago_parcial": bool(pago_parcial),
                "monto_adelanto": adelanto if pago_parcial else None,
                "pagos_parciales": pagos,
                "items_venta": [],
                "observacion": "",
                "lejos_od": {},
                "lejos_oi": {},
                "cerca_od": {},
                "cerca_oi": {},
            }
            if pago_parcial and (monto_total - adelanto) > 0.05:
                grad["deuda_id"] = f"DEU-GRAD-{branch_suffix}-{dni}-{v+1}"
            historial.append(grad)

        out.append(
            {
                "dni": dni,
                "nombre": nombre,
                "fecha": _d_to_date_str(today - datetime.timedelta(days=rnd.randint(0, 40))),
                "edad": int(edad),
                "genero": genero,
                "fecha_nacimiento": birth.strftime("%Y-%m-%d"),
                "historial_graduaciones": historial,
            }
        )

    return out


def _generate_sales_and_update_stock(
    rnd: random.Random,
    ventas: list,
    productos: list,
    kardex: list,
    clientes: list,
    branch_suffix: str,
    count: int,
) -> tuple[list, list, list]:
    if ventas:
        # If already present, keep as-is (avoid exploding data).
        return ventas, productos, kardex

    today = datetime.datetime.now()
    base_id = _max_int_id(ventas, "id", 364)
    sale_id = base_id + 1

    # index products by name for faster updates
    prod_by_name = {}
    for p in productos:
        if isinstance(p, dict) and str(p.get("nombre", "")).strip():
            prod_by_name[str(p["nombre"]).strip()] = p

    clients_pool = [c for c in clientes if isinstance(c, dict) and str(c.get("dni", "")).strip()]
    if not clients_pool:
        clients_pool = [{"dni": "00000000", "nombre": f"CLIENTE {branch_suffix}"}]

    for i in range(count):
        dt = today - datetime.timedelta(days=rnd.randint(0, 14), hours=rnd.randint(0, 23), minutes=rnd.randint(0, 59))
        c = rnd.choice(clients_pool)
        dni = str(c.get("dni", "")).strip() or "00000000"
        nombre = str(c.get("nombre", "")).strip().upper() or f"CLIENTE {dni}"

        # build items (1..3)
        items = []
        n_items = 1 if rnd.random() < 0.6 else 2 if rnd.random() < 0.85 else 3
        prod_names = list(prod_by_name.keys())
        rnd.shuffle(prod_names)

        total = 0.0
        for pn in prod_names:
            if len(items) >= n_items:
                break
            p = prod_by_name.get(pn)
            if not p:
                continue
            stock = int(p.get("stock", 0) or 0)
            if stock <= 0:
                continue
            qty = 1 if stock == 1 else rnd.randint(1, min(3, stock))
            price = _safe_float(p.get("venta", 0), 0.0)
            line_total = round(price * qty, 2)
            line_subtotal = round(line_total / 1.18, 2)
            items.append(
                {
                    "nombre": pn,
                    "producto": pn,
                    "cantidad": int(qty),
                    "precio_unitario": float(price),
                    "subtotal": float(line_subtotal),
                    "total": float(line_total),
                }
            )
            total += line_total

            # Update stock and kardex salida
            p["stock"] = stock - qty
            kardex.append(
                {
                    "fecha": _dt_to_sale_str(dt),
                    "movimiento": "Salida",
                    "producto": pn,
                    "cantidad": int(qty),
                    "costo_unitario": float(_safe_float(p.get("costo", 0), 0.0)),
                    "valor_total": round(_safe_float(p.get("costo", 0), 0.0) * qty, 2),
                    "stock_final": int(p.get("stock", 0) or 0),
                }
            )

        if not items:
            # no stock available, skip sale
            continue

        total = round(total, 2)
        subtotal = round(total / 1.18, 2)
        igv = round(total - subtotal, 2)
        metodo = rnd.choice(PAY_METHODS)

        es_parcial = rnd.random() < 0.22
        monto_pagado = total
        deuda_id = None
        monto_adelanto = 0.0
        monto_faltante = 0.0
        es_pago_partes = False

        if es_parcial:
            monto_pagado = round(total * rnd.uniform(0.15, 0.75), 2)
            monto_adelanto = monto_pagado
            monto_faltante = round(total - monto_pagado, 2)
            es_pago_partes = True
            if monto_faltante > 0.05:
                deuda_id = f"DEU-VENTA-{branch_suffix}-{sale_id}"
            else:
                es_parcial = False
                monto_pagado = total

        venta = {
            "id": int(sale_id),
            "fecha": _dt_to_sale_str(dt),
            "paciente_dni": dni,
            "paciente_nombre": nombre,
            "usuario": USERNAME,
            "helper_name": None,
            "items": items,
            "subtotal": float(subtotal),
            "igv": float(igv),
            "total": float(total),
            "descuento_total": 0.0,
            "metodo_pago": metodo,
            "es_pago_parcial": bool(es_parcial),
            "monto_pagado": float(monto_pagado),
            # compat fields used by deudas tab
            "es_pago_partes": bool(es_pago_partes),
            "monto_adelanto": float(monto_adelanto),
            "monto_faltante": float(monto_faltante),
            "vendedor": USERNAME,
        }
        if deuda_id:
            venta["deuda_id"] = deuda_id

        ventas.append(venta)
        sale_id += 1

    # Order ventas descending by fecha string (rough)
    ventas.sort(key=lambda x: str(x.get("fecha", "")), reverse=True)
    return ventas, productos, kardex


def main() -> int:
    if not os.path.isdir(BRANCH_CACHE_DIR):
        print(f"ERROR: No existe {BRANCH_CACHE_DIR}")
        return 2

    branch_codes = sorted([d for d in os.listdir(BRANCH_CACHE_DIR) if os.path.isdir(os.path.join(BRANCH_CACHE_DIR, d))])
    if not branch_codes:
        print("ERROR: No hay sucursales en branch_cache.")
        return 2

    # Deterministic but different from clients script.
    rnd = random.Random(260316)

    for code in branch_codes:
        branch_suffix = code.split("-")[-1]
        data_dir = os.path.join(BRANCH_CACHE_DIR, code, "data")
        clientes_path = os.path.join(data_dir, "clientes.json")
        pacientes_path = os.path.join(data_dir, "pacientes.json")
        ventas_path = os.path.join(data_dir, "ventas.json")
        productos_path = os.path.join(data_dir, "productos.json")
        kardex_path = os.path.join(data_dir, "kardex.json")

        clientes = _read_json_list(clientes_path)
        pacientes = _read_json_list(pacientes_path)
        ventas = _read_json_list(ventas_path)
        productos = _read_json_list(productos_path)
        kardex = _read_json_list(kardex_path)

        productos = _make_products_if_empty(rnd, productos, branch_suffix)
        if not kardex:
            kardex = _seed_kardex_for_products(productos, datetime.datetime.now() - datetime.timedelta(days=30))

        pacientes = _make_pacientes_if_empty(rnd, pacientes, clientes, branch_suffix)
        ventas, productos, kardex = _generate_sales_and_update_stock(
            rnd=rnd,
            ventas=ventas,
            productos=productos,
            kardex=kardex,
            clientes=clientes,
            branch_suffix=branch_suffix,
            count=60,
        )

        # Persist
        _write_json_list(productos_path, productos)
        _write_json_list(kardex_path, kardex)
        _write_json_list(pacientes_path, pacientes)
        _write_json_list(ventas_path, ventas)

        # Summary
        deuda_ventas = sum(1 for v in ventas if isinstance(v, dict) and str(v.get("deuda_id", "")).strip())
        deuda_grads = 0
        for p in pacientes:
            if not isinstance(p, dict):
                continue
            for g in (p.get("historial_graduaciones", []) or []):
                if isinstance(g, dict) and str(g.get("deuda_id", "")).strip():
                    deuda_grads += 1
        total_stock = sum(int((p.get("stock", 0) or 0)) for p in productos if isinstance(p, dict))
        print(
            f"{code}: pacientes={len(pacientes)} ventas={len(ventas)} "
            f"deudas_ventas={deuda_ventas} deudas_graduaciones={deuda_grads} "
            f"productos={len(productos)} stock_total={total_stock} kardex={len(kardex)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
