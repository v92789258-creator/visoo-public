import datetime

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QMessageBox


def apply_text_date_filter(page):
    texto = page.fecha_texto_input.text().strip()
    if not texto:
        hoy_str = datetime.date.today().strftime("%d/%m/%Y")
        page.fecha_texto_input.setText(hoy_str)
        texto = hoy_str

    try:
        sale_date = datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        page.date_start.blockSignals(True)
        page.date_end.blockSignals(True)
        page.date_start.setDate(QDate(sale_date))
        page.date_end.setDate(QDate(sale_date))
        page.date_start.blockSignals(False)
        page.date_end.blockSignals(False)
        page.filter_by_dates()
    except ValueError:
        QMessageBox.warning(page, "Fecha invalida", "La fecha ingresada no tiene el formato correcto (dd/mm/aaaa).")


def filter_by_dates(page):
    start_date = page.date_start.date().toPyDate()
    end_date = page.date_end.date().toPyDate()
    all_sales = getattr(page, "_all_sales", None)
    if all_sales is None:
        return

    start_key = (start_date.year * 10000) + (start_date.month * 100) + start_date.day
    end_key = (end_date.year * 10000) + (end_date.month * 100) + end_date.day
    filtered_sales = []
    for sale in (all_sales or []):
        if not isinstance(sale, dict):
            continue
        key = int(sale.get("_viso_date_key", 0) or 0)
        if not key:
            try:
                sale_date = datetime.datetime.strptime(sale.get("fecha", "").split()[0], "%d/%m/%Y").date()
                if start_date <= sale_date <= end_date:
                    filtered_sales.append(sale)
            except Exception:
                continue
        else:
            if start_key <= key <= end_key:
                filtered_sales.append(sale)
    page.update_sales_history_table(filtered_sales)


def on_payment_method_changed(page, _text):
    if not hasattr(page, "sales_table") or page.sales_table is None:
        return

    method_key = page.payment_method_combo.currentData()
    if method_key is None:
        method_key = "todos"

    start_date = page.date_start.date().toPyDate()
    end_date = page.date_end.date().toPyDate()
    all_sales = getattr(page, "_all_sales", None)
    if all_sales is None:
        return

    start_key = (start_date.year * 10000) + (start_date.month * 100) + start_date.day
    end_key = (end_date.year * 10000) + (end_date.month * 100) + end_date.day
    filtered_sales = []
    for sale in (all_sales or []):
        if not isinstance(sale, dict):
            continue
        key = int(sale.get("_viso_date_key", 0) or 0)
        if not key or not (start_key <= key <= end_key):
            continue
        if method_key == "todos":
            filtered_sales.append(sale)
            continue

        metodo_venta = str(sale.get("metodo_pago", "") or "").lower()
        metodos_detalle = sale.get("metodos_pago_detalle") or []
        metodos_lookup = set()
        if isinstance(metodos_detalle, list):
            for item in metodos_detalle:
                if isinstance(item, dict):
                    metodo_item = str(item.get("metodo", "") or "").strip().lower()
                    if metodo_item:
                        metodos_lookup.add(metodo_item)
        if metodo_venta == method_key or method_key in metodos_lookup:
            filtered_sales.append(sale)

    page.update_sales_history_table(filtered_sales)


def on_sales_selection_changed(page):
    try:
        if hasattr(page, "btn_mass_rules"):
            page.btn_mass_rules.setText("Acciones deshabilitadas")
            page.btn_mass_rules.setVisible(False)
        if hasattr(page, "mass_actions_container"):
            page.mass_actions_container.setVisible(False)
    except Exception:
        pass


def mass_action_change_date(page):
    QMessageBox.warning(
        page,
        "Accion deshabilitada",
        "La edicion masiva de fechas fue deshabilitada temporalmente para evitar cambios no deseados en ventas.",
    )
