import json
import os
import random
import datetime


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


def _load_json_list(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []


def _write_json_list(path: str, data: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=True)
        f.write("\n")


def _compute_age(today: datetime.date, birth: datetime.date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _make_client(dni: str, nombre: str, birth: datetime.date, genero: str, fecha_registro: str, etiqueta: str) -> dict:
    return {
        "dni": dni,
        "nombre": nombre,
        "fecha_nacimiento": birth.strftime("%Y-%m-%d"),
        "edad": _compute_age(datetime.date.today(), birth),
        "genero": genero,
        "fecha_registro": fecha_registro,
        "telefono": "",
        "correo": "",
        "direccion": "",
        "empresa": "",
        "notas": "",
        "etiquetas": [etiqueta],
    }


def main() -> int:
    if not os.path.isdir(BRANCH_CACHE_DIR):
        print(f"ERROR: No existe {BRANCH_CACHE_DIR}")
        return 2

    branch_codes = sorted([d for d in os.listdir(BRANCH_CACHE_DIR) if os.path.isdir(os.path.join(BRANCH_CACHE_DIR, d))])
    if not branch_codes:
        print("ERROR: No se encontraron sucursales (branch_cache vacio).")
        return 2

    # Load existing DNIs across all branches to keep them unique globally.
    existing_dnis = set()
    per_branch_clients = {}
    for code in branch_codes:
        path = os.path.join(BRANCH_CACHE_DIR, code, "data", "clientes.json")
        clients = _load_json_list(path)
        per_branch_clients[code] = clients
        for c in clients:
            dni = str(c.get("dni", "")).strip()
            if dni:
                existing_dnis.add(dni)

    today = datetime.date.today()
    fecha_registro = today.strftime("%d/%m/%Y")

    # Deterministic generation per run.
    rnd = random.Random(260315)
    next_dni = 70000000

    for b_idx, code in enumerate(branch_codes):
        clients = per_branch_clients[code]
        added = 0

        while added < 40:
            # Unique DNI (8 digits) across all branches.
            while True:
                dni = str(next_dni)
                next_dni += 1
                if len(dni) == 8 and dni not in existing_dnis:
                    existing_dnis.add(dni)
                    break

            # Unique-ish name (ASCII only). Use code suffix to help avoid duplicates.
            fn = FIRST_NAMES[(b_idx * 7 + added) % len(FIRST_NAMES)]
            ln1 = LAST_NAMES_1[(b_idx * 11 + added) % len(LAST_NAMES_1)]
            ln2 = LAST_NAMES_2[(b_idx * 13 + added) % len(LAST_NAMES_2)]
            code_suffix = code.split("-")[-1]
            nombre = f"{fn} {ln1} {ln2} {code_suffix}".upper()

            # Birth date between 1955 and 2008 (inclusive-ish), deterministic but varied.
            year = 1955 + ((b_idx * 37 + added * 3) % 54)  # 1955..2008
            month = 1 + ((b_idx * 5 + added) % 12)
            day = 1 + ((b_idx * 9 + added * 2) % 28)
            birth = datetime.date(year, month, day)

            genero = "Masculino" if (added % 2 == 0) else "Femenino"
            etiqueta = "Falta pagar" if (added % 3 != 0) else "Pagado"

            clients.append(_make_client(dni, nombre, birth, genero, fecha_registro, etiqueta))
            added += 1

        # Shuffle a bit within branch so it doesn't look generated in strict order.
        rnd.shuffle(clients)

        out_path = os.path.join(BRANCH_CACHE_DIR, code, "data", "clientes.json")
        _write_json_list(out_path, clients)
        print(f"{code}: total={len(clients)} (agregados 40) -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
