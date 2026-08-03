import datetime
from types import SimpleNamespace

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QDateEdit, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from gui.main_window_pages.sales_page_parts import SalesTableWidget
from gui.main_window_pages.sales_page_parts.sale_deletion import eliminar_venta as delete_sale
from gui.salesHistorypage.table_render import render_sale_row_fast


def _date_key(value):
    try:
        raw = str(value or "").strip()
        if not raw:
            return 0
        raw = raw.split()[0]
        dd, mm, yy = raw.split("/")
        return (int(yy) * 10000) + (int(mm) * 100) + int(dd)
    except Exception:
        return 0


def _filter_sales_for_range(sales, start_date, end_date):
    if not isinstance(sales, list):
        return []
    start_key = (start_date.year * 10000) + (start_date.month * 100) + start_date.day
    end_key = (end_date.year * 10000) + (end_date.month * 100) + end_date.day
    out = []
    for sale in sales:
        if not isinstance(sale, dict):
            continue
        key = int(sale.get("_viso_date_key", 0) or 0)
        if not key:
            key = _date_key(sale.get("fecha", ""))
        if start_key <= key <= end_key:
            out.append(sale)
    return out


def build_compare_view(page):
    container = QWidget()
    container.setVisible(False)
    container.setStyleSheet(
        """
        QWidget {
            background: #F8FAFC;
        }
        QWidget#ComparePanel {
            background: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
        }
        QLabel {
            color: #374151;
        }
        QDateEdit {
            padding: 6px 8px;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            background: white;
        }
        QPushButton {
            border: none;
            border-radius: 6px;
            padding: 7px 12px;
            font-weight: 700;
        }
        """
    )

    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)

    page.compare_view_container = container
    page.compare_panels = {}
    page.compare_visible = False

    def _build_panel(side, title):
        panel = QWidget()
        panel.setObjectName("ComparePanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #111827;")
        panel_layout.addWidget(title_label)

        dates_row = QHBoxLayout()
        dates_row.setSpacing(8)

        start_edit = QDateEdit(calendarPopup=True)
        start_edit.setDisplayFormat("dd/MM/yyyy")
        start_edit.setDate(QDate.currentDate().addDays(-7))

        end_edit = QDateEdit(calendarPopup=True)
        end_edit.setDisplayFormat("dd/MM/yyyy")
        end_edit.setDate(QDate.currentDate())

        apply_btn = QPushButton("Aplicar")
        apply_btn.setStyleSheet("background: #0d6efd; color: white;")
        apply_btn.clicked.connect(lambda _checked=False, s=side: refresh_compare_panel(page, s))

        dates_row.addWidget(QLabel("Desde:"))
        dates_row.addWidget(start_edit)
        dates_row.addWidget(QLabel("Hasta:"))
        dates_row.addWidget(end_edit)
        dates_row.addWidget(apply_btn)
        panel_layout.addLayout(dates_row)

        table = SalesTableWidget(parent_page=page)
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            ["Fecha", "N° Orden", "DNI Paciente", "Artículos", "Total", "Método de Pago", "Estado", "Acciones"]
        )
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.verticalHeader().setDefaultSectionSize(45)
        table.setColumnWidth(0, 130)
        table.setColumnWidth(1, 95)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(4, 120)
        table.setColumnWidth(5, 140)
        table.setColumnWidth(6, 150)
        table.setColumnWidth(7, 100)

        header = table.horizontalHeader()
        header.setVisible(True)
        header.setMinimumHeight(45)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.Fixed)

        table.cellClicked.connect(lambda row, col, s=side: on_compare_table_cell_clicked(page, s, row, col))
        panel_layout.addWidget(table)

        info_label = QLabel("0 ventas")
        info_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(info_label)

        page.compare_panels[side] = {
            "panel": panel,
            "title": title_label,
            "start": start_edit,
            "end": end_edit,
            "apply": apply_btn,
            "table": table,
            "info": info_label,
            "sales": [],
        }
        return panel

    layout.addWidget(_build_panel("left", "Comparacion A"))
    layout.addWidget(_build_panel("right", "Comparacion B"))
    return container


def toggle_compare_mode(page):
    page.compare_visible = not bool(getattr(page, "compare_visible", False))
    try:
        if hasattr(page, "compare_view_container") and page.compare_view_container is not None:
            page.compare_view_container.setVisible(page.compare_visible)
    except Exception:
        pass
    try:
        if hasattr(page, "payment_filter_container"):
            page.payment_filter_container.setVisible(not page.compare_visible)
        if hasattr(page, "sales_table_container"):
            page.sales_table_container.setVisible(not page.compare_visible)
        if hasattr(page, "mass_actions_container"):
            page.mass_actions_container.setVisible(False)
    except Exception:
        pass
    if page.compare_visible:
        refresh_compare_panel(page, "left")
        refresh_compare_panel(page, "right")
    else:
        try:
            if hasattr(page, "sales_table_container"):
                page.sales_table_container.setVisible(True)
            page.filter_by_dates()
        except Exception:
            try:
                page.update_sales_history_table(page._all_sales or [])
            except Exception:
                pass


def refresh_compare_panel(page, side):
    panel = getattr(page, "compare_panels", {}).get(side)
    if not panel:
        return
    all_sales = getattr(page, "_all_sales", None) or []
    start_date = panel["start"].date().toPyDate()
    end_date = panel["end"].date().toPyDate()
    sales = _filter_sales_for_range(all_sales, start_date, end_date)
    panel["sales"] = sales

    table = panel["table"]
    table.setRowCount(0)
    try:
        table.clearSpans()
    except Exception:
        pass

    wrapper = SimpleNamespace(
        sales_table=table,
        _format_order_number=getattr(page, "_format_order_number", lambda x: x),
        _is_closing=False,
    )
    for idx, sale in enumerate(sales):
        table.insertRow(idx)
        render_sale_row_fast(wrapper, idx, sale)

    panel["info"].setText(f"{len(sales)} ventas")
    try:
        page.compare_view_container.setVisible(True)
    except Exception:
        pass


def on_compare_table_cell_clicked(page, side, row, col):
    try:
        if int(col) != 7:
            return
    except Exception:
        return
    panel = getattr(page, "compare_panels", {}).get(side)
    if not panel:
        return
    try:
        sale = panel["sales"][int(row)]
    except Exception:
        return
    if isinstance(sale, dict):
        delete_sale(page, sale)
