import datetime
import math
import json
import os
import re
from pathlib import Path
from collections import Counter, defaultdict

import requests


_MISTRAL_CONFIG_PATH = Path(os.path.expanduser("~")) / ".viso" / "mistral_config.json"


def save_mistral_api_key(api_key):
    key = str(api_key or "").strip()
    if not key:
        return False
    try:
        _MISTRAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_MISTRAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"api_key": key}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_mistral_api_key():
    env_key = str(os.environ.get("MISTRAL_API_KEY", "") or "").strip()
    if env_key:
        return env_key

    try:
        if _MISTRAL_CONFIG_PATH.exists():
            with open(_MISTRAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            key = str((data or {}).get("api_key", "") or "").strip()
            if key:
                return key
    except Exception:
        pass
    return ""


def _parse_date(value):
    text = str(value or "").strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1]

    formats = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _safe_float(value, default=0.0):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return float(default)


def _normalize_name(value):
    text = str(value or "").strip().upper()
    if not text:
        return ""
    return " ".join(text.split())


def _short_name(value, max_len=44):
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _build_target_items(rows, limit=30):
    items = []
    seen = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip().upper()
        name = str(row.get("name") or "").strip()
        key = code or name.upper()
        if not key or key in seen:
            continue
        seen.add(key)
        items.append({
            "code": code,
            "name": name,
        })
        if len(items) >= int(limit or 30):
            break
    return items


def _merge_target_items(*groups, limit=40):
    items = []
    seen = set()
    for group in groups:
        for row in group or []:
            if not isinstance(row, dict):
                continue
            code = str(row.get("code") or "").strip().upper()
            name = str(row.get("name") or "").strip()
            key = code or name.upper()
            if not key or key in seen:
                continue
            seen.add(key)
            items.append({
                "code": code,
                "name": name,
            })
            if len(items) >= int(limit or 40):
                return items
    return items


def _iter_recent_sales_items(ventas, lookback_days, today):
    cutoff = today - datetime.timedelta(days=max(1, int(lookback_days or 1)) - 1)
    for venta in ventas or []:
        if not isinstance(venta, dict):
            continue
        fecha = _parse_date(venta.get("fecha"))
        if fecha is None or fecha.date() < cutoff:
            continue
        items = venta.get("items") or []
        if not isinstance(items, list):
            continue
        yield fecha.date(), venta, items


def _resolve_cloud_codes(username, branch_code=""):
    from utils.api_handler import listar_dispositivos_hijos_remoto, listar_snapshots_dispositivos_nube
    from utils.file_handler import _resolve_usuario_madre_cloud, resolve_username, get_user_file_path

    usuario_madre = _resolve_usuario_madre_cloud(username)
    resolved_username = resolve_username(username)
    selected_branch = str(branch_code or "").strip().upper()

    codes = []

    def _add_code(value):
        code = str(value or "").strip().upper()
        if code and code not in codes:
            codes.append(code)

    if selected_branch:
        _add_code(selected_branch)
        return usuario_madre, codes

    try:
        base = re.sub(r"[^A-Za-z0-9]+", "", str(resolved_username).upper()) or "USER"
        _add_code(f"MADRE-{base}"[:80])
    except Exception:
        pass

    try:
        cfg_path = get_user_file_path(username, "config_dispositivo.json")
        if cfg_path.exists():
            import json

            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                _add_code(cfg.get("codigo_dispositivo"))
    except Exception:
        pass

    ok, devices, _msg = listar_dispositivos_hijos_remoto(usuario_madre)
    if not ok or not isinstance(devices, list) or not devices:
        try:
            ok_s, snap_devices, _msg_s = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
            if ok_s and isinstance(snap_devices, list):
                devices = snap_devices
                ok = True
        except Exception:
            ok = False

    if ok and isinstance(devices, list):
        for device in devices:
            if not isinstance(device, dict):
                continue
            if str(device.get("estado", "activo")).strip().lower() == "bloqueado":
                continue
            _add_code(device.get("codigo_dispositivo"))

    return usuario_madre, codes


def _download_dataset_http(usuario_madre, code, dataset_name):
    from utils.file_handler import _download_snapshot_payload_for_dataset, _extract_list_dataset_from_snapshot

    payload = _download_snapshot_payload_for_dataset(usuario_madre, code, dataset_name)
    if payload is None:
        return None

    data = _extract_list_dataset_from_snapshot(payload, dataset_name)
    if data is None:
        return None
    return data if isinstance(data, list) else []


def _merge_global_patients(items):
    merged = []
    by_dni = {}

    for paciente in items or []:
        if not isinstance(paciente, dict):
            continue
        dni = str(paciente.get("dni") or "").strip()
        if not dni:
            merged.append(paciente)
            continue

        current_idx = by_dni.get(dni)
        if current_idx is None:
            by_dni[dni] = len(merged)
            merged.append(dict(paciente))
            continue

        base = dict(merged[current_idx])
        historial_base = base.get("historial_graduaciones") or []
        historial_new = paciente.get("historial_graduaciones") or []

        seen_hist = set()
        combined_hist = []
        for grad in list(historial_base) + list(historial_new):
            if not isinstance(grad, dict):
                continue
            key = (
                str(grad.get("fecha") or "").strip(),
                str(grad.get("optometra") or grad.get("medico_optometra") or "").strip(),
                str(grad.get("monto_cobrado") or grad.get("precio") or "").strip(),
            )
            if key in seen_hist:
                continue
            seen_hist.add(key)
            combined_hist.append(grad)

        for k, v in paciente.items():
            if k == "historial_graduaciones":
                continue
            if not base.get(k) and v:
                base[k] = v
        base["historial_graduaciones"] = combined_hist
        merged[current_idx] = base

    return merged


def fetch_inventory_control_cloud_data(username, branch_code=""):
    usuario_madre, codes = _resolve_cloud_codes(username, branch_code=branch_code)
    datasets = {
        "productos": [],
        "ventas": [],
        "pacientes": [],
    }

    if not codes:
        return {
            "productos": [],
            "ventas": [],
            "pacientes": [],
            "codes": [],
            "source": "cloud_empty",
        }

    for code in codes:
        for dataset_name in ("productos", "ventas", "pacientes"):
            data = _download_dataset_http(usuario_madre, code, dataset_name)
            if isinstance(data, list):
                datasets[dataset_name].extend(data)

    unique_products = []
    seen_products = set()
    for producto in datasets["productos"]:
        if not isinstance(producto, dict):
            continue
        key = (
            str(producto.get("codigo") or "").strip().upper(),
            str(producto.get("nombre") or "").strip().upper(),
        )
        if key in seen_products:
            continue
        seen_products.add(key)
        unique_products.append(producto)

    unique_sales = []
    seen_sales = set()
    for venta in datasets["ventas"]:
        if not isinstance(venta, dict):
            continue
        key = str(venta.get("id") or "").strip() or (
            str(venta.get("fecha") or "").strip() + "|" + str(venta.get("paciente_dni") or "").strip()
        )
        if key in seen_sales:
            continue
        seen_sales.add(key)
        unique_sales.append(venta)

    merged_patients = _merge_global_patients(datasets["pacientes"])

    source = "cloud_branch" if branch_code else "cloud_global"
    return {
        "productos": unique_products,
        "ventas": unique_sales,
        "pacientes": merged_patients,
        "codes": codes,
        "source": source,
    }


def analyze_inventory_control(
    productos,
    ventas,
    pacientes,
    lookback_days=45,
    prescription_days=90,
    conversion_window_days=30,
    today=None,
):
    today = today or datetime.date.today()
    productos_validos = [p for p in (productos or []) if isinstance(p, dict)]
    ventas_validas = [v for v in (ventas or []) if isinstance(v, dict)]
    pacientes_validos = [p for p in (pacientes or []) if isinstance(p, dict)]

    sold_qty = defaultdict(float)
    sold_amount = defaultdict(float)
    recent_sales_count = 0
    recent_units = 0.0
    recent_revenue = 0.0

    for _sale_date, _venta, items in _iter_recent_sales_items(ventas_validas, lookback_days, today):
        recent_sales_count += 1
        recent_revenue += _safe_float(_venta.get("total"), 0.0)
        for item in items:
            if not isinstance(item, dict):
                continue
            key = _normalize_name(item.get("nombre"))
            if not key:
                continue
            qty = _safe_float(item.get("cantidad"), 0.0)
            amount = _safe_float(item.get("total"), 0.0)
            if amount <= 0 and qty > 0:
                amount = _safe_float(item.get("precio_unitario"), 0.0) * qty
            sold_qty[key] += qty
            sold_amount[key] += amount
            recent_units += qty

    product_rows = []
    for producto in productos_validos:
        name = str(producto.get("nombre") or producto.get("codigo") or "Producto").strip()
        code = str(producto.get("codigo") or "").strip().upper()
        key = _normalize_name(name)
        stock = max(0.0, _safe_float(producto.get("stock"), 0.0))
        costo = max(0.0, _safe_float(producto.get("costo"), 0.0))
        venta = max(0.0, _safe_float(producto.get("venta"), 0.0))
        sold_recent = max(0.0, sold_qty.get(key, 0.0))
        avg_daily = sold_recent / float(max(1, int(lookback_days or 1)))
        days_left = (stock / avg_daily) if avg_daily > 0 else None
        reorder_units = max(0, int(math.ceil(avg_daily * 30.0 - stock)))

        product_rows.append(
            {
                "name": name,
                "code": code,
                "short_name": _short_name(name),
                "stock": stock,
                "costo": costo,
                "venta": venta,
                "sold_recent": sold_recent,
                "avg_daily": avg_daily,
                "days_left": days_left,
                "reorder_units": reorder_units,
                "amount_recent": sold_amount.get(key, 0.0),
                "stock_value_cost": costo * stock,
                "stock_value_sale": venta * stock,
                "estimated_recent_margin": max(0.0, (venta - costo) * sold_recent),
            }
        )

    demand_candidates = [row for row in product_rows if row["sold_recent"] > 0]
    demand_candidates.sort(
        key=lambda row: (
            0 if row["days_left"] is not None else 1,
            row["days_left"] if row["days_left"] is not None else 999999,
            -row["sold_recent"],
            -row["amount_recent"],
        )
    )

    top_demand = demand_candidates[0] if demand_candidates else None
    prediction_candidates = [
        row
        for row in demand_candidates
        if row["days_left"] is not None and (row["days_left"] <= 30 or row["stock"] <= 3)
    ]
    top_predictions = prediction_candidates[:3]
    zero_low_rows = [row for row in product_rows if row["stock"] <= 3]
    zero_low_rows.sort(key=lambda row: (row["stock"], row["days_left"] if row["days_left"] is not None else 999999, row["name"]))

    demand_title = "Sin demanda reciente"
    demand_body = "Todavia no hay suficiente historial reciente de ventas para sugerir una reposicion."
    if top_demand is not None:
        sold_recent = int(round(top_demand["sold_recent"]))
        stock_now = int(round(top_demand["stock"]))
        if top_demand["days_left"] is None:
            demand_title = "Producto con movimiento"
            demand_body = (
                f"{top_demand['short_name']} vendio {sold_recent} u. en {lookback_days} dias. "
                f"Stock actual: {stock_now}."
            )
        elif top_demand["days_left"] <= 14:
            demand_title = "Compra mas de este producto"
            demand_body = (
                f"{top_demand['short_name']} vendio {sold_recent} u. en {lookback_days} dias y su stock "
                f"alcanzaria para {top_demand['days_left']:.1f} dias. Reponer al menos {max(1, top_demand['reorder_units'])} u."
            )
        else:
            demand_title = "Producto de alta rotacion"
            demand_body = (
                f"{top_demand['short_name']} vendio {sold_recent} u. en {lookback_days} dias. "
                f"Stock estimado para {top_demand['days_left']:.1f} dias."
            )

    prediction_title = "Prediccion de stock"
    if top_predictions:
        prediction_lines = []
        for row in top_predictions:
            prediction_lines.append(
                f"{row['short_name']}: {int(round(row['stock']))} u., {row['days_left']:.1f} dias de cobertura."
            )
        prediction_body = "\n".join(prediction_lines)
    else:
        prediction_body = "No hay productos con riesgo inmediato segun las ventas recientes."

    zero_stock_count = sum(1 for row in product_rows if row["stock"] <= 0)
    low_stock_count = sum(1 for row in product_rows if 0 < row["stock"] <= 3)
    at_risk_7_count = sum(1 for row in product_rows if row["days_left"] is not None and row["days_left"] <= 7)
    at_risk_30_count = sum(1 for row in product_rows if row["days_left"] is not None and row["days_left"] <= 30)
    total_stock_units = sum(row["stock"] for row in product_rows)
    inventory_sale_value = sum(row["stock_value_sale"] for row in product_rows)
    inventory_cost_value = sum(row["stock_value_cost"] for row in product_rows)
    estimated_recent_margin = sum(row["estimated_recent_margin"] for row in product_rows)
    average_ticket = (recent_revenue / recent_sales_count) if recent_sales_count > 0 else 0.0

    dead_stock_rows = [row for row in product_rows if row["stock"] > 0 and row["sold_recent"] <= 0]
    dead_stock_rows.sort(key=lambda row: (-row["stock_value_cost"], -row["stock"], row["name"]))
    dead_stock_count = len(dead_stock_rows)
    dead_stock_value = sum(row["stock_value_cost"] for row in dead_stock_rows)
    top_dead_stock = dead_stock_rows[0] if dead_stock_rows else None

    slow_stock_rows = [
        row for row in product_rows
        if row["stock"] > 0 and row["sold_recent"] > 0 and row["days_left"] is not None and row["days_left"] >= 60
    ]
    slow_stock_rows.sort(key=lambda row: (-row["days_left"], -row["stock_value_cost"], row["name"]))
    slow_stock_count = len(slow_stock_rows)

    top_seller = None
    top_seller_rows = []
    if demand_candidates:
        top_seller_rows = sorted(
            demand_candidates,
            key=lambda row: (-row["sold_recent"], -row["amount_recent"], row["name"])
        )
        top_seller = top_seller_rows[0]

    top_revenue_rows = sorted(
        [row for row in demand_candidates if row["amount_recent"] > 0],
        key=lambda row: (-row["amount_recent"], -row["sold_recent"], row["name"])
    )

    top_margin_rows = sorted(
        [row for row in product_rows if row["estimated_recent_margin"] > 0],
        key=lambda row: (-row["estimated_recent_margin"], -row["sold_recent"], row["name"])
    )

    sales_by_dni = defaultdict(list)
    for venta in ventas_validas:
        dni = str(venta.get("paciente_dni") or "").strip()
        fecha = _parse_date(venta.get("fecha"))
        if not dni or fecha is None:
            continue
        sales_by_dni[dni].append(venta)

    for dni in list(sales_by_dni.keys()):
        sales_by_dni[dni].sort(key=lambda item: _parse_date(item.get("fecha")) or datetime.datetime.min)

    rx_cutoff = today - datetime.timedelta(days=max(1, int(prescription_days or 1)) - 1)
    total_rx = 0
    converted_rx = 0
    linked_sales_amount = 0.0
    linked_products = Counter()

    for paciente in pacientes_validos:
        dni = str(paciente.get("dni") or "").strip()
        historial = paciente.get("historial_graduaciones") or []
        if not dni or not isinstance(historial, list):
            continue

        for grad in historial:
            if not isinstance(grad, dict):
                continue
            grad_dt = _parse_date(grad.get("fecha") or grad.get("created_at"))
            if grad_dt is None or grad_dt.date() < rx_cutoff:
                continue

            total_rx += 1
            matched_sale = None
            for venta in sales_by_dni.get(dni, []):
                sale_dt = _parse_date(venta.get("fecha"))
                if sale_dt is None:
                    continue
                delta = (sale_dt.date() - grad_dt.date()).days
                if 0 <= delta <= int(conversion_window_days or 30):
                    matched_sale = venta
                    break

            if matched_sale is None:
                continue

            converted_rx += 1
            linked_sales_amount += _safe_float(matched_sale.get("total"), 0.0)
            for item in matched_sale.get("items") or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("nombre") or "").strip()
                if name:
                    linked_products[_short_name(name, max_len=32)] += int(round(_safe_float(item.get("cantidad"), 0.0)))

    if total_rx > 0:
        conversion_rate = (converted_rx / float(total_rx)) * 100.0
        rx_title = "Recetas y ventas reales"
        rx_body = (
            f"{converted_rx} de {total_rx} recetas de los ultimos {prescription_days} dias terminaron en venta "
            f"dentro de {conversion_window_days} dias ({conversion_rate:.1f}%)."
        )
        if linked_sales_amount > 0:
            rx_body += f"\nIngresos vinculados: S/. {linked_sales_amount:,.2f}."
        if linked_products:
            top_name, top_qty = linked_products.most_common(1)[0]
            rx_body += f"\nProducto mas repetido en esas ventas: {top_name} ({top_qty} u.)."
    else:
        rx_title = "Recetas y ventas reales"
        rx_body = "Todavia no hay recetas recientes suficientes para medir conversion a venta."

    status_parts = [f"{len(productos_validos)} productos"]
    if recent_sales_count > 0:
        status_parts.append(f"{recent_sales_count} ventas recientes")
    if total_rx > 0:
        status_parts.append(f"{total_rx} recetas recientes")

    return {
        "status_text": "Analisis sobre " + ", ".join(status_parts) + ".",
        "demand_title": demand_title,
        "demand_body": demand_body,
        "prediction_title": prediction_title,
        "prediction_body": prediction_body,
        "rx_title": rx_title,
        "rx_body": rx_body,
        "restock_count": len(top_predictions),
        "recent_units": recent_units,
        "recent_revenue": recent_revenue,
        "average_ticket": average_ticket,
        "estimated_recent_margin": estimated_recent_margin,
        "zero_stock_count": zero_stock_count,
        "low_stock_count": low_stock_count,
        "at_risk_7_count": at_risk_7_count,
        "at_risk_30_count": at_risk_30_count,
        "dead_stock_count": dead_stock_count,
        "dead_stock_value": dead_stock_value,
        "slow_stock_count": slow_stock_count,
        "total_stock_units": total_stock_units,
        "inventory_sale_value": inventory_sale_value,
        "inventory_cost_value": inventory_cost_value,
        "top_dead_stock_name": top_dead_stock["short_name"] if top_dead_stock else "",
        "top_dead_stock_value": top_dead_stock["stock_value_cost"] if top_dead_stock else 0.0,
        "top_seller_name": top_seller["short_name"] if top_seller else "",
        "top_seller_units": top_seller["sold_recent"] if top_seller else 0.0,
        "top_seller_revenue": top_seller["amount_recent"] if top_seller else 0.0,
        "focus_summary_items": _merge_target_items(top_predictions, top_seller_rows[:3], zero_low_rows[:5], limit=20),
        "focus_risk_items": _build_target_items(
            [row for row in demand_candidates if row["days_left"] is not None and row["days_left"] <= 30],
            limit=30
        ),
        "focus_dead_items": _build_target_items(dead_stock_rows, limit=40),
        "focus_leader_items": _build_target_items(top_seller_rows[:15], limit=15),
        "focus_ticket_items": _build_target_items(top_revenue_rows[:15], limit=15),
        "focus_margin_items": _build_target_items(top_margin_rows[:15], limit=15),
        "focus_stock_items": _build_target_items(zero_low_rows[:30], limit=30),
    }


def _build_local_inventory_recommendation(result):
    if not isinstance(result, dict):
        return "No hay suficiente informacion para recomendar una accion ahora."

    ideas = []
    demand = str(result.get("demand_body") or "").strip()
    prediction = str(result.get("prediction_body") or "").strip()
    rx = str(result.get("rx_body") or "").strip()
    restock_count = int(result.get("restock_count") or 0)
    dead_stock_count = int(result.get("dead_stock_count") or 0)
    dead_stock_value = float(result.get("dead_stock_value") or 0.0)
    top_dead_name = str(result.get("top_dead_stock_name") or "").strip()

    if demand:
        ideas.append(demand.rstrip(".") + ".")

    if restock_count > 0 and prediction:
        first_line = str(prediction.splitlines()[0] or "").strip()
        if first_line:
            ideas.append(f"Prioriza reposicion inmediata empezando por: {first_line.rstrip('.')}.")

    if rx:
        first_rx = str(rx.splitlines()[0] or "").strip()
        if first_rx:
            ideas.append(first_rx.rstrip(".") + ".")

    if dead_stock_count > 0:
        dead_text = f"Tienes {dead_stock_count} producto(s) sin movimiento reciente"
        if dead_stock_value > 0:
            dead_text += f" con valor inmovilizado aprox. de S/. {dead_stock_value:,.2f}"
        if top_dead_name:
            dead_text += f"; revisa primero {top_dead_name}"
        ideas.append(dead_text.rstrip(".") + ".")

    if not ideas:
        return "Hoy no se detecta una alerta fuerte. Mantén el inventario monitoreado y vuelve a analizar después de nuevas ventas."

    summary = " ".join(ideas[:3]).strip()
    if restock_count > 0:
        summary += " Si haces una compra hoy, enfócate primero en los productos con menor cobertura."
    elif dead_stock_count > 0:
        summary += " Antes de comprar más, limpia o mueve el stock que lleva tiempo parado."
    else:
        summary += " No se ve un quiebre urgente, pero sí conviene seguir monitoreando la rotación."
    return summary.strip()


def _extract_mistral_text(payload):
    try:
        choices = payload.get("choices") or []
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for chunk in content:
                if isinstance(chunk, dict):
                    text = str(chunk.get("text", "") or "").strip()
                    if text:
                        parts.append(text)
            return "\n".join(parts).strip()
    except Exception:
        return ""
    return ""


def _clean_ai_summary_text(text):
    value = str(text or "").strip()
    if not value:
        return ""
    value = value.replace("**", "")
    value = value.replace("__", "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _finalize_ai_summary_text(text, fallback):
    value = _clean_ai_summary_text(text)
    if not value:
        return _clean_ai_summary_text(fallback)

    if value[-1:] not in ".!?":
        last_stop = max(value.rfind("."), value.rfind("!"), value.rfind("?"))
        if last_stop >= max(40, len(value) // 2):
            value = value[: last_stop + 1].strip()
        else:
            value = _clean_ai_summary_text(fallback)

    return value.strip() or _clean_ai_summary_text(fallback)


def _build_mistral_inventory_prompt(result):
    facts = {
        "status": str(result.get("status_text") or "").strip(),
        "demanda": str(result.get("demand_body") or "").strip(),
        "prediccion": str(result.get("prediction_body") or "").strip(),
        "recetas": str(result.get("rx_body") or "").strip(),
        "restock_count": int(result.get("restock_count") or 0),
        "recent_units": float(result.get("recent_units") or 0.0),
        "riesgo_7_dias": int(result.get("at_risk_7_count") or 0),
        "riesgo_30_dias": int(result.get("at_risk_30_count") or 0),
        "sin_stock": int(result.get("zero_stock_count") or 0),
        "stock_bajo": int(result.get("low_stock_count") or 0),
        "stock_inmovil": int(result.get("dead_stock_count") or 0),
        "valor_inmovilizado": float(result.get("dead_stock_value") or 0.0),
        "producto_parado_principal": str(result.get("top_dead_stock_name") or "").strip(),
        "producto_lider": str(result.get("top_seller_name") or "").strip(),
        "producto_lider_unidades": float(result.get("top_seller_units") or 0.0),
        "ticket_promedio_reciente": float(result.get("average_ticket") or 0.0),
        "margen_estimado_reciente": float(result.get("estimated_recent_margin") or 0.0),
        "valor_inventario_venta": float(result.get("inventory_sale_value") or 0.0),
    }
    facts_json = json.dumps(facts, ensure_ascii=False)
    return (
        "Eres un asesor comercial para una óptica. "
        "Resume estos hallazgos técnicos en español natural, corto y accionable. "
        "Di qué debe hacer el dueño hoy y menciona el riesgo u oportunidad más importante. "
        "Máximo 3 oraciones, sin viñetas, sin repetir números innecesarios, sin mencionar JSON ni sistema.\n"
        f"DATOS: {facts_json}"
    )


def summarize_inventory_control_natural(result):
    fallback = _build_local_inventory_recommendation(result)
    api_key = load_mistral_api_key()
    if not api_key:
        return {
            "title": "Resumen inteligente",
            "body": fallback,
            "provider": "local",
        }

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistral-small-latest",
                "temperature": 0.2,
                "max_tokens": 120,
                "messages": [
                    {
                        "role": "system",
                        "content": "Responde en español claro, útil y comercial.",
                    },
                    {
                        "role": "user",
                        "content": _build_mistral_inventory_prompt(result),
                    },
                ],
            },
            timeout=18,
        )
        response.raise_for_status()
        payload = response.json() if response.content else {}
        text = _finalize_ai_summary_text(_extract_mistral_text(payload), fallback)
        if text:
            return {
                "title": "Resumen IA",
                "body": text,
                "provider": "mistral",
            }
    except Exception:
        pass

    return {
        "title": "Resumen inteligente",
        "body": fallback,
        "provider": "local",
    }


def analyze_inventory_control_from_cloud(username, branch_code=""):
    cloud_data = fetch_inventory_control_cloud_data(username, branch_code=branch_code)
    result = analyze_inventory_control(
        productos=cloud_data.get("productos") or [],
        ventas=cloud_data.get("ventas") or [],
        pacientes=cloud_data.get("pacientes") or [],
    )
    result["cloud_source"] = cloud_data.get("source") or "cloud"
    result["cloud_codes"] = cloud_data.get("codes") or []
    ai_summary = summarize_inventory_control_natural(result)
    result["ai_summary_title"] = str((ai_summary or {}).get("title", "") or "Resumen inteligente")
    result["ai_summary_body"] = str((ai_summary or {}).get("body", "") or "")
    result["ai_summary_provider"] = str((ai_summary or {}).get("provider", "") or "local")
    return result
