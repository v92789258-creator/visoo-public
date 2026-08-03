import logging

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import QTableWidgetItem

logger = logging.getLogger(__name__)


def update_sales_history_table(page, sales):
    return update_sales_history_table_chunked(page, sales)


def update_sales_history_table_chunked(page, sales):
    cancel_sales_fill(page)
    page.sales_table.setRowCount(0)
    try:
        page.sales_table.clearSpans()
    except Exception:
        pass

    page.filtered_sales = sales
    try:
        if not sales:
            if hasattr(page, "empty_message") and page.empty_message is not None:
                page.empty_message.setVisible(True)
            if hasattr(page, "sales_table") and page.sales_table is not None:
                page.sales_table.setVisible(False)
        else:
            if hasattr(page, "empty_message") and page.empty_message is not None:
                page.empty_message.setVisible(False)
            if hasattr(page, "sales_table") and page.sales_table is not None:
                page.sales_table.setVisible(True)
    except Exception:
        pass

    total_periodo = 0.0
    total_efectivo = 0.0
    try:
        for s in (sales or []):
            if isinstance(s, dict):
                total_periodo += float(s.get("total", 0) or 0)
                metodo = str(s.get("metodo_pago", "") or "").strip().lower()
                if "efectivo" in metodo:
                    total_venta = float(s.get("total", 0) or 0)
                    pagado = float(s.get("monto_pagado", total_venta) or 0)
                    total_efectivo += pagado
    except Exception:
        total_periodo = 0.0
        total_efectivo = 0.0
    try:
        page.total_amount_label.setText(f"S/. {total_periodo:.2f}")
        page.total_efectivo_label.setText(f"S/. {total_efectivo:.2f}")
    except Exception:
        pass

    if hasattr(page, "btn_generar_reporte"):
        try:
            page.btn_generar_reporte.setEnabled(bool(sales))
        except Exception:
            pass

    if not sales:
        return

    page._sales_fill_sales = list(sales) if isinstance(sales, (list, tuple)) else []
    page._sales_fill_pos = 0
    page._sales_fill_chunk_size = 15 if len(page._sales_fill_sales) <= 800 else 8
    try:
        page.sales_table.setSortingEnabled(False)
    except Exception:
        pass
    fill_sales_chunk(page)
    if page._sales_fill_pos < len(page._sales_fill_sales):
        page._sales_fill_timer = QTimer(page)
        page._sales_fill_timer.timeout.connect(lambda: fill_sales_chunk(page))
        page._sales_fill_timer.start(10)


def cancel_sales_fill(page):
    timer = getattr(page, "_sales_fill_timer", None)
    if timer is not None:
        try:
            timer.stop()
        except Exception:
            pass
        try:
            timer.deleteLater()
        except Exception:
            pass
    page._sales_fill_timer = None
    page._sales_fill_sales = []
    page._sales_fill_pos = 0
    page._sales_fill_chunk_size = 15


def sales_fill_in_progress(page):
    timer = getattr(page, "_sales_fill_timer", None)
    if timer is None:
        return False
    try:
        return bool(timer.isActive())
    except Exception:
        return False


def fill_sales_chunk(page):
    if getattr(page, "_is_closing", False):
        try:
            cancel_sales_fill(page)
        except Exception:
            pass
        return

    try:
        chunk_size = int(getattr(page, "_sales_fill_chunk_size", 15) or 15)
        sales = getattr(page, "_sales_fill_sales", []) or []
        pos = int(getattr(page, "_sales_fill_pos", 0) or 0)
        if pos >= len(sales):
            timer = getattr(page, "_sales_fill_timer", None)
            if timer is not None:
                try:
                    timer.stop()
                except Exception:
                    pass
                page._sales_fill_timer = None
            return

        end = min(pos + int(chunk_size), len(sales))
        try:
            page.sales_table.setUpdatesEnabled(False)
        except Exception:
            pass

        for i in range(pos, end):
            sale = sales[i]
            if isinstance(sale, dict):
                row_idx = page.sales_table.rowCount()
                page.sales_table.insertRow(row_idx)
                try:
                    render_sale_row_fast(page, row_idx, sale)
                except Exception:
                    logger.exception("[VENTAS] Error renderizando fila %s", row_idx)

        page._sales_fill_pos = end
        try:
            page.sales_table.setUpdatesEnabled(True)
        except Exception:
            pass

        if end >= len(sales):
            timer = getattr(page, "_sales_fill_timer", None)
            if timer is not None:
                try:
                    timer.stop()
                except Exception:
                    pass
                page._sales_fill_timer = None
    except Exception:
        logger.exception("[VENTAS] Error en _fill_sales_chunk()")
        try:
            cancel_sales_fill(page)
        except Exception:
            pass
        try:
            page.sales_table.setUpdatesEnabled(True)
        except Exception:
            pass


def render_sale_row_fast(page, i, sale):
    fecha_item = QTableWidgetItem(str(sale.get("fecha", "") or ""))
    fecha_item.setTextAlignment(Qt.AlignCenter)
    page.sales_table.setItem(i, 0, fecha_item)

    raw_order = str(sale.get("numero_orden", "") or "").strip()
    order_item = QTableWidgetItem(page._format_order_number(raw_order) if raw_order else "")
    order_item.setTextAlignment(Qt.AlignCenter)
    page.sales_table.setItem(i, 1, order_item)

    dni_item = QTableWidgetItem(str(sale.get("paciente_dni", "") or ""))
    dni_item.setTextAlignment(Qt.AlignCenter)
    page.sales_table.setItem(i, 2, dni_item)

    items = sale.get("items") or []
    if not isinstance(items, (list, tuple)):
        items = []
    parts = []
    for item in items:
        if isinstance(item, dict):
            nombre = item.get("nombre") or item.get("producto") or "Producto"
            cantidad = item.get("cantidad", 1)
            parts.append(f"{nombre} (x{cantidad})")

    items_str = ", ".join(parts)
    if not items_str and sale.get("tipo_venta") == "graduacion":
        items_str = "Servicio de Graduación"
    page.sales_table.setItem(i, 3, QTableWidgetItem(items_str or "Sin detalle"))

    try:
        total_val = float(sale.get("total", 0) or 0)
    except Exception:
        total_val = 0.0
    total_item = QTableWidgetItem(f"S/. {total_val:.2f}")
    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    total_font = QFont()
    total_font.setBold(True)
    total_item.setFont(total_font)
    page.sales_table.setItem(i, 4, total_item)

    metodo = str(sale.get("metodo_pago", "N/A") or "N/A").strip().title()
    metodo_item = QTableWidgetItem(metodo)
    metodo_item.setTextAlignment(Qt.AlignCenter)
    page.sales_table.setItem(i, 5, metodo_item)

    try:
        total_venta = float(sale.get("total", 0) or 0)
        pagado = float(sale.get("monto_pagado", total_venta) or 0)
        faltante = float(sale.get("monto_faltante", 0) or 0)
    except Exception:
        total_venta, pagado, faltante = 0.0, 0.0, 0.0

    pendiente = faltante if faltante > 0 else (total_venta - pagado)
    if pendiente > 0.05:
        estado_txt = f"Por cobrar: S/. {pendiente:.2f}"
        color = "#d32f2f"
    else:
        estado_txt = "Cobrado"
        color = "#2e7d32"

    estado_item = QTableWidgetItem(estado_txt)
    estado_item.setTextAlignment(Qt.AlignCenter)
    try:
        estado_item.setForeground(QBrush(QColor(color)))
        font = QFont()
        font.setBold(True)
        estado_item.setFont(font)
    except Exception:
        pass
    page.sales_table.setItem(i, 6, estado_item)

    accion_item = QTableWidgetItem("Eliminar")
    accion_item.setTextAlignment(Qt.AlignCenter)
    try:
        accion_item.setForeground(QBrush(QColor("#d32f2f")))
        font = QFont()
        font.setBold(True)
        accion_item.setFont(font)
    except Exception:
        pass
    page.sales_table.setItem(i, 7, accion_item)


def on_sales_table_cell_clicked(page, row, col):
    try:
        if int(col) != 7:
            return
    except Exception:
        return

    try:
        sale = (page.filtered_sales or [])[int(row)]
    except Exception:
        return

    if isinstance(sale, dict):
        page.eliminar_venta(sale)
