from collections import Counter

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem

from gui.main_window_pages.basic_mode_common import (
    BasicWindowBase,
    date_in_filter,
    load_scoped_list,
    make_button,
    safe_float,
    safe_int,
    sale_total_safe,
)
from utils.file_handler import cargar_ventas


class BasicDailyReportPage(BasicWindowBase):
    def __init__(self, parent=None):
        super().__init__(
            parent_app=parent,
            title="Reporte del Dia",
            subtitle="Resumen simple de las operaciones registradas hoy.",
            loader_text="Preparando reporte",
        )
        self.cards = {}
        self._build_ui()

    def _build_ui(self):
        actions = QHBoxLayout()
        actions.addStretch()
        btn_refresh = make_button("Actualizar reporte")
        btn_refresh.clicked.connect(self.reload_data)
        actions.addWidget(btn_refresh)
        btn_close = make_button("Cerrar", "#64748B", "#475569")
        btn_close.clicked.connect(self.exit_basic_page)
        actions.addWidget(btn_close)
        self.content_layout.addLayout(actions)

        cards_grid = QGridLayout()
        cards_grid.setSpacing(14)
        card_defs = (
            ("sales_count", "Ventas del dia", "#DBEAFE", "#1D4ED8"),
            ("sales_total", "Total vendido", "#DCFCE7", "#15803D"),
            ("debts", "Deudas generadas", "#FEE2E2", "#B91C1C"),
            ("payments", "Pagos recibidos", "#FEF3C7", "#B45309"),
            ("contracts", "Contratos creados", "#EDE9FE", "#6D28D9"),
            ("products", "Productos vendidos", "#CCFBF1", "#0F766E"),
        )
        for index, (key, title, background, color) in enumerate(card_defs):
            card = QLabel(f"{title}\n0")
            card.setAlignment(Qt.AlignCenter)
            card.setMinimumHeight(125)
            card.setStyleSheet(
                f"font-size: 23px; font-weight: 800; color: {color}; background: {background}; "
                "border: 2px solid rgba(15, 23, 42, 0.10); border-radius: 18px; padding: 16px;"
            )
            self.cards[key] = card
            cards_grid.addWidget(card, index // 3, index % 3)
        self.content_layout.addLayout(cards_grid)

        title = QLabel("Productos vendidos hoy")
        title.setStyleSheet("font-size: 23px; font-weight: 800; color: #0F172A;")
        self.content_layout.addWidget(title)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Producto", "Cantidad"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.content_layout.addWidget(self.table, 1)

    def _calculate_report(self):
        sales, _ = load_scoped_list(self.parent_app, self.username, "ventas.json", cargar_ventas)
        today_sales = [sale for sale in sales if date_in_filter(sale.get("fecha"), "today")]
        total_sold = 0.0
        debt_generated = 0.0
        payments_received = 0.0
        contracts = set()
        products = Counter()

        for sale in today_sales:
            total = sale_total_safe(sale)
            paid = safe_float(sale.get("monto_pagado", sale.get("monto_adelanto", total)), total)
            pending = safe_float(sale.get("monto_faltante"))
            if pending <= 0.05:
                pending = max(0.0, total - paid)
            total_sold += total
            debt_generated += pending
            payments_received += min(max(paid, 0.0), total)
            contract = str(sale.get("contrato_numero", "") or "").strip()
            if contract:
                contracts.add(contract)
            for item in sale.get("items", []) or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("producto") or item.get("nombre") or "Producto").strip()
                products[name] += max(1, safe_int(item.get("cantidad"), 1))

        return {
            "sales_count": len(today_sales),
            "sales_total": total_sold,
            "debts": debt_generated,
            "payments": payments_received,
            "contracts": len(contracts),
            "products": sum(products.values()),
            "product_rows": products.most_common(),
        }

    def reload_data(self):
        self.load_async(self._calculate_report, self._on_loaded, loading_text="Preparando reporte")

    def _on_loaded(self, report):
        self.cards["sales_count"].setText(f"Ventas del dia\n{report['sales_count']}")
        self.cards["sales_total"].setText(f"Total vendido\nS/ {report['sales_total']:.2f}")
        self.cards["debts"].setText(f"Deudas generadas\nS/ {report['debts']:.2f}")
        self.cards["payments"].setText(f"Pagos recibidos\nS/ {report['payments']:.2f}")
        self.cards["contracts"].setText(f"Contratos creados\n{report['contracts']}")
        self.cards["products"].setText(f"Productos vendidos\n{report['products']}")

        rows = report.get("product_rows", []) or []
        self.table.setRowCount(0)
        for row, (name, quantity) in enumerate(rows):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(name or "Producto")))
            qty_item = QTableWidgetItem(str(quantity))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, qty_item)

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_data()
