import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)

from gui.main_window_pages.basic_mode_common import (
    BasicWindowBase,
    date_in_filter,
    load_scoped_list,
    make_button,
    parse_date_safe,
    safe_float,
    sale_total_safe,
)
from utils.file_handler import cargar_ventas


class BasicSalesHistoryPage(BasicWindowBase):
    DISPLAY_LIMIT = 1000

    def __init__(self, parent=None):
        super().__init__(
            parent_app=parent,
            title="Ventas Registradas",
            subtitle="Revisa ventas con filtros simples y letras grandes.",
            loader_text="Cargando ventas",
        )
        self.all_sales = []
        self._build_ui()

    def _build_ui(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Hoy", "today")
        self.filter_combo.addItem("Esta semana", "this_week")
        self.filter_combo.addItem("Semana anterior", "previous_week")
        self.filter_combo.addItem("Dia especifico", "specific")
        self.filter_combo.addItem("Todas", "all")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_combo)

        self.date_edit = QDateEdit(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setVisible(False)
        self.date_edit.dateChanged.connect(self._apply_filter)
        toolbar.addWidget(self.date_edit)

        self.lbl_summary = QLabel("Ventas: 0 | Total: S/ 0.00")
        self.lbl_summary.setStyleSheet(
            "font-size: 22px; font-weight: 800; color: #0F172A; "
            "background: #E8F1FF; border: 2px solid #BFD3FF; border-radius: 14px; padding: 12px 16px;"
        )
        toolbar.addWidget(self.lbl_summary, 1)

        btn_refresh = make_button("Recargar")
        btn_refresh.clicked.connect(self.reload_data)
        toolbar.addWidget(btn_refresh)

        btn_close = make_button("Cerrar", "#64748B", "#475569")
        btn_close.clicked.connect(self.exit_basic_page)
        toolbar.addWidget(btn_close)
        self.content_layout.addLayout(toolbar)

        self.empty_label = QLabel("No hay ventas para el periodo seleccionado.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: #64748B; "
            "background: white; border: 2px dashed #CBD5E1; border-radius: 16px; padding: 30px;"
        )
        self.empty_label.hide()
        self.content_layout.addWidget(self.empty_label)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Fecha", "Orden", "DNI", "Cliente", "Detalle", "Total", "Pago", "Estado"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeToContents)
        self.content_layout.addWidget(self.table, 1)

    @staticmethod
    def _format_order_number(value):
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if not digits:
            return ""
        return digits.zfill(4) if len(digits) < 4 else digits

    @staticmethod
    def _build_items_summary(sale):
        parts = []
        for item in sale.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("producto") or item.get("nombre") or "Producto").strip()
            quantity = item.get("cantidad", 1)
            if name:
                parts.append(f"{name} x{quantity}")
        if parts:
            return ", ".join(parts)
        if str(sale.get("tipo_venta", "") or "").strip().lower() == "graduacion":
            return "Servicio de Graduacion"
        return "Sin detalle"

    def reload_data(self):
        self.load_async(
            lambda: load_scoped_list(self.parent_app, self.username, "ventas.json", cargar_ventas)[0],
            self._on_sales_loaded,
            loading_text="Cargando ventas",
        )

    def _on_sales_loaded(self, sales):
        self.all_sales = sorted(
            [sale for sale in sales if isinstance(sale, dict)],
            key=lambda sale: parse_date_safe(sale.get("fecha")) or datetime.datetime.min,
            reverse=True,
        )
        self._apply_filter()

    def _apply_filter(self):
        if not hasattr(self, "table"):
            return
        filter_key = str(self.filter_combo.currentData() or "today")
        self.date_edit.setVisible(filter_key == "specific")
        specific_date = self.date_edit.date().toPyDate()
        filtered = [
            sale
            for sale in self.all_sales
            if date_in_filter(sale.get("fecha"), filter_key, specific_date)
        ]
        self._render_sales(filtered)

    def _render_sales(self, sales):
        self.table.setRowCount(0)
        total_general = sum(sale_total_safe(sale) for sale in sales)
        visible_sales = sales[: self.DISPLAY_LIMIT]
        for row_index, sale in enumerate(visible_sales):
            self.table.insertRow(row_index)
            total = sale_total_safe(sale)
            paid = safe_float(sale.get("monto_pagado"), total)
            pending = safe_float(sale.get("monto_faltante"))
            if pending <= 0.05:
                pending = max(0.0, total - paid)
            status = "Pagado" if pending <= 0.05 else ("Abonado" if paid > 0 else "Debe")
            payment = str(sale.get("metodo_pago", "") or "No registrado").strip()
            values = [
                str(sale.get("fecha", "") or "Sin fecha"),
                self._format_order_number(sale.get("numero_orden")) or str(sale.get("contrato_numero", "") or ""),
                str(sale.get("paciente_dni", "") or "Sin DNI"),
                str(sale.get("paciente_nombre", "") or "Sin cliente"),
                self._build_items_summary(sale),
                f"S/ {total:.2f}",
                payment,
                status,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter if column in (1, 2, 5, 6, 7) else Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row_index, column, item)

        suffix = f" | Mostrando {len(visible_sales)}" if len(sales) > self.DISPLAY_LIMIT else ""
        self.lbl_summary.setText(f"Ventas: {len(sales)} | Total: S/ {total_general:.2f}{suffix}")
        self.empty_label.setVisible(not sales)
        self.table.setVisible(bool(sales))

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_data()
