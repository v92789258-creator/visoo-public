import copy
import datetime
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.file_handler import (
    VISO_DIR,
    cargar_kardex,
    cargar_pacientes,
    cargar_productos,
    cargar_ventas,
    clear_active_branch_context,
    get_active_branch_context,
    guardar_kardex,
    guardar_pacientes,
    guardar_productos,
    guardar_ventas,
    resolve_username,
    set_active_branch_context,
)


TRASH_FILE_NAME = "papelera.json"
DATASET_LABELS = {
    "pacientes": "Pacientes",
    "productos": "Productos",
    "ventas": "Ventas",
}


def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _deep_copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except Exception:
        return copy.deepcopy(value)


def _record_signature(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return repr(value)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except Exception:
        return default


def get_trash_file_path(username: str) -> Path:
    resolved = resolve_username(username)
    return Path(VISO_DIR) / resolved / "data" / TRASH_FILE_NAME


def _load_trash_entries(username: str) -> List[Dict[str, Any]]:
    path = get_trash_file_path(username)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_trash_entries(username: str, entries: List[Dict[str, Any]]) -> None:
    path = get_trash_file_path(username)
    os.makedirs(path.parent, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2, ensure_ascii=False)
    os.replace(str(tmp_path), str(path))


def _build_summary(dataset: str, record: Dict[str, Any]) -> str:
    if dataset == "pacientes":
        nombre = str(record.get("nombre", "") or "Paciente sin nombre").strip()
        dni = str(record.get("dni", "") or "").strip()
        return f"{nombre} | DNI: {dni or 'sin DNI'}"
    if dataset == "productos":
        nombre = str(record.get("nombre", "") or "Producto sin nombre").strip()
        codigo = str(record.get("codigo", "") or "").strip()
        return f"{nombre} | Codigo: {codigo or 'sin codigo'}"
    if dataset == "ventas":
        venta_id = str(record.get("id", "") or "").strip()
        fecha = str(record.get("fecha", "") or "").strip()
        total = _safe_float(record.get("total", 0))
        paciente = str(
            record.get("paciente_nombre")
            or record.get("cliente")
            or record.get("nombre")
            or ""
        ).strip()
        return (
            f"Venta {venta_id or 'sin ID'} | {fecha or 'sin fecha'}"
            f" | {paciente or 'sin paciente'} | S/{total:.2f}"
        )
    return DATASET_LABELS.get(dataset, dataset.title())


def _get_branch_snapshot(username: str) -> Dict[str, str]:
    ctx = get_active_branch_context(username)
    return {
        "code": str((ctx or {}).get("code", "") or "").strip().upper(),
        "label": str((ctx or {}).get("label", "") or "").strip(),
    }


@contextmanager
def _branch_restore_scope(username: str, branch_code: str = "", branch_label: str = ""):
    previous = _get_branch_snapshot(username)
    target_code = str(branch_code or "").strip().upper()
    target_label = str(branch_label or "").strip()

    try:
        if target_code:
            set_active_branch_context(username, target_code, target_label)
        else:
            clear_active_branch_context(username)
        yield
    finally:
        if previous.get("code"):
            set_active_branch_context(username, previous.get("code", ""), previous.get("label", ""))
        else:
            clear_active_branch_context(username)


def list_trash_entries(username: str, dataset: str = "") -> List[Dict[str, Any]]:
    entries = _load_trash_entries(username)
    wanted = str(dataset or "").strip().lower()
    if wanted:
        entries = [item for item in entries if str(item.get("dataset", "")).strip().lower() == wanted]
    return sorted(
        entries,
        key=lambda item: str(item.get("deleted_at", "") or ""),
        reverse=True,
    )


def move_to_trash(
    username: str,
    dataset: str,
    record: Dict[str, Any],
    source: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    dataset_key = str(dataset or "").strip().lower()
    if dataset_key not in DATASET_LABELS:
        raise ValueError(f"Dataset de papelera no soportado: {dataset_key}")
    if not isinstance(record, dict):
        raise ValueError("Solo se pueden enviar registros dict a la papelera.")

    branch = _get_branch_snapshot(username)
    payload = _deep_copy(record)
    entry = {
        "trash_id": uuid.uuid4().hex,
        "dataset": dataset_key,
        "dataset_label": DATASET_LABELS.get(dataset_key, dataset_key.title()),
        "deleted_at": _now_iso(),
        "source": str(source or "").strip(),
        "summary": _build_summary(dataset_key, payload),
        "record": payload,
        "branch_code": branch.get("code", ""),
        "branch_label": branch.get("label", ""),
        "extra": _deep_copy(extra) if isinstance(extra, dict) else {},
    }

    entries = _load_trash_entries(username)
    entries.insert(0, entry)
    _save_trash_entries(username, entries)
    return entry


def purge_trash_entry(username: str, trash_id: str) -> Tuple[bool, str]:
    trash_id = str(trash_id or "").strip()
    if not trash_id:
        return False, "No se recibio un ID de papelera."

    entries = _load_trash_entries(username)
    filtered = [item for item in entries if str(item.get("trash_id", "")).strip() != trash_id]
    if len(filtered) == len(entries):
        return False, "No se encontro el elemento en papelera."

    _save_trash_entries(username, filtered)
    return True, "Elemento eliminado permanentemente de la papelera."


def _find_trash_entry(entries: List[Dict[str, Any]], trash_id: str) -> Optional[Dict[str, Any]]:
    target_id = str(trash_id or "").strip()
    for entry in entries:
        if str(entry.get("trash_id", "")).strip() == target_id:
            return entry
    return None


def _restore_patient(username: str, entry: Dict[str, Any]) -> Tuple[bool, str]:
    record = entry.get("record") if isinstance(entry.get("record"), dict) else {}
    patients = cargar_pacientes(username) or []
    if not isinstance(patients, list):
        patients = []

    record_signature = _record_signature(record)
    if any(_record_signature(item) == record_signature for item in patients if isinstance(item, dict)):
        return False, "Ese paciente ya existe actualmente."

    target_dni = str(record.get("dni", "") or "").strip()
    if target_dni and target_dni != "00000000":
        for existing in patients:
            if not isinstance(existing, dict):
                continue
            existing_dni = str(existing.get("dni", "") or "").strip()
            if existing_dni == target_dni:
                return False, f"Ya existe otro paciente con DNI {target_dni}."

    patients.append(record)
    guardar_pacientes(username, patients)
    return True, "Paciente restaurado desde papelera."


def _restore_product(username: str, entry: Dict[str, Any]) -> Tuple[bool, str]:
    record = entry.get("record") if isinstance(entry.get("record"), dict) else {}
    products = cargar_productos(username) or []
    if isinstance(products, dict):
        products = list(products.values())
    if not isinstance(products, list):
        products = []

    record_signature = _record_signature(record)
    if any(_record_signature(item) == record_signature for item in products if isinstance(item, dict)):
        return False, "Ese producto ya existe actualmente."

    target_code = str(record.get("codigo", "") or "").strip().upper()
    target_name = str(record.get("nombre", "") or "").strip().lower()

    for existing in products:
        if not isinstance(existing, dict):
            continue
        existing_code = str(existing.get("codigo", "") or "").strip().upper()
        existing_name = str(existing.get("nombre", "") or "").strip().lower()
        if target_code and existing_code == target_code:
            return False, f"Ya existe otro producto con codigo {target_code}."
        if target_name and existing_name == target_name:
            return False, f"Ya existe otro producto con nombre {record.get('nombre', '')}."

    products.append(record)
    guardar_productos(username, products)
    return True, "Producto restaurado desde papelera."


def _restore_sale_stock(username: str, sale_record: Dict[str, Any]) -> Tuple[bool, str]:
    products = cargar_productos(username) or []
    if isinstance(products, dict):
        products = list(products.values())
    if not isinstance(products, list):
        products = []

    by_name = {}
    for product in products:
        if not isinstance(product, dict):
            continue
        name_key = str(product.get("nombre", "") or "").strip().lower()
        if name_key and name_key not in by_name:
            by_name[name_key] = product

    issues = []
    moves = []

    for item in sale_record.get("items", []) if isinstance(sale_record.get("items"), list) else []:
        if not isinstance(item, dict):
            continue

        item_name = str(item.get("nombre") or item.get("producto") or "").strip()
        if not item_name:
            continue

        qty = _safe_int(item.get("cantidad", 0), default=0)
        if qty <= 0:
            continue

        product = by_name.get(item_name.lower())
        if not product:
            issues.append(f"Falta el producto '{item_name}' en inventario.")
            continue

        current_stock = _safe_int(product.get("stock", 0), default=0)
        if current_stock < qty:
            issues.append(
                f"Stock insuficiente para '{item_name}' ({current_stock} disponible, {qty} requerido)."
            )
            continue

        moves.append((product, qty, item))

    if issues:
        return False, "\n".join(issues)

    kardex_entries = []
    for product, qty, item in moves:
        current_stock = _safe_int(product.get("stock", 0), default=0)
        new_stock = current_stock - qty
        product["stock"] = new_stock
        unit_cost = _safe_float(item.get("precio_unitario", product.get("costo", 0)), default=0.0)
        kardex_entries.append(
            {
                "producto": str(product.get("nombre", "") or "").strip(),
                "cantidad": qty,
                "costo_unitario": unit_cost,
                "stock_final": new_stock,
            }
        )

    guardar_productos(username, products)

    if kardex_entries:
        try:
            kardex = cargar_kardex(username) or []
            if not isinstance(kardex, list):
                kardex = []
            event_at = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            for entry in kardex_entries:
                unit_cost = _safe_float(entry.get("costo_unitario", 0))
                qty = _safe_int(entry.get("cantidad", 0))
                kardex.append(
                    {
                        "fecha": event_at,
                        "movimiento": "Salida - Restauracion de venta",
                        "producto": entry.get("producto", ""),
                        "cantidad": qty,
                        "costo_unitario": unit_cost,
                        "valor_total": unit_cost * qty,
                        "stock_final": entry.get("stock_final", 0),
                    }
                )
            guardar_kardex(username, kardex)
        except Exception:
            pass

    return True, "Stock ajustado para restaurar la venta."


def _restore_sale(username: str, entry: Dict[str, Any]) -> Tuple[bool, str]:
    record = entry.get("record") if isinstance(entry.get("record"), dict) else {}
    extra = entry.get("extra") if isinstance(entry.get("extra"), dict) else {}

    sales = cargar_ventas(username) or []
    if not isinstance(sales, list):
        sales = []

    record_signature = _record_signature(record)
    sale_id = str(record.get("id", "") or "").strip()
    for sale in sales:
        if not isinstance(sale, dict):
            continue
        if sale_id and str(sale.get("id", "") or "").strip() == sale_id:
            return False, f"La venta {sale_id} ya existe actualmente."
        if _record_signature(sale) == record_signature:
            return False, "Esa venta ya existe actualmente."

    stock_adjusted_on_delete = bool(extra.get("stock_adjusted_on_delete"))
    if stock_adjusted_on_delete:
        ok_stock, stock_message = _restore_sale_stock(username, record)
        if not ok_stock:
            return False, stock_message

    sales.append(record)
    guardar_ventas(username, sales)

    if stock_adjusted_on_delete:
        return True, "Venta restaurada y stock re-aplicado."
    return True, "Venta restaurada desde papelera."


def restore_trash_entry(username: str, trash_id: str) -> Tuple[bool, str]:
    trash_id = str(trash_id or "").strip()
    if not trash_id:
        return False, "No se recibio un ID de papelera."

    entries = _load_trash_entries(username)
    entry = _find_trash_entry(entries, trash_id)
    if not entry:
        return False, "No se encontro el elemento en papelera."

    dataset = str(entry.get("dataset", "") or "").strip().lower()
    branch_code = str(entry.get("branch_code", "") or "").strip().upper()
    branch_label = str(entry.get("branch_label", "") or "").strip()

    with _branch_restore_scope(username, branch_code, branch_label):
        if dataset == "pacientes":
            ok, message = _restore_patient(username, entry)
        elif dataset == "productos":
            ok, message = _restore_product(username, entry)
        elif dataset == "ventas":
            ok, message = _restore_sale(username, entry)
        else:
            return False, f"Dataset no soportado para restauracion: {dataset}"

    if not ok:
        return False, message

    remaining = [item for item in entries if str(item.get("trash_id", "")).strip() != trash_id]
    _save_trash_entries(username, remaining)

    if branch_code:
        message = f"{message} Destino restaurado: {branch_label or branch_code}."
    return True, message

