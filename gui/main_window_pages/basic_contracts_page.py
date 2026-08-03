import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QMessageBox,
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
from utils.file_handler import cargar_pacientes, cargar_ventas


class BasicContractsPage(BasicWindowBase):
    def __init__(self, parent=None):
        super().__init__(
            parent_app=parent,
            title="Contratos",
            subtitle="Contratos de graduacion de la sucursal actual.",
            loader_text="Cargando contratos",
        )
        self.all_contracts = []
        self.selected_contract = None
        self._build_ui()

    def _build_ui(self):
        toolbar = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Hoy", "today")
        self.filter_combo.addItem("Esta semana", "this_week")
        self.filter_combo.addItem("Semana anterior", "previous_week")
        self.filter_combo.addItem("Dia especifico", "specific")
        self.filter_combo.addItem("Pendientes de recoger", "pending_pickup")
        self.filter_combo.addItem("Entregados", "delivered")
        self.filter_combo.addItem("Todos", "all")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_combo)

        self.date_edit = QDateEdit(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.hide()
        self.date_edit.dateChanged.connect(self._apply_filter)
        toolbar.addWidget(self.date_edit)

        self.summary = QLabel("Contratos: 0")
        self.summary.setStyleSheet(
            "font-size: 22px; font-weight: 800; color: #0F172A; "
            "background: #E8F1FF; border: 2px solid #BFD3FF; border-radius: 14px; padding: 12px 16px;"
        )
        toolbar.addWidget(self.summary, 1)
        btn_refresh = make_button("Recargar")
        btn_refresh.clicked.connect(self.reload_data)
        toolbar.addWidget(btn_refresh)
        btn_close = make_button("Cerrar", "#64748B", "#475569")
        btn_close.clicked.connect(self.exit_basic_page)
        toolbar.addWidget(btn_close)
        self.content_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Codigo", "Paciente", "Fecha", "Total", "Saldo", "Estado"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.itemSelectionChanged.connect(self._on_selected)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        self.content_layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        btn_detail = make_button("Ver detalle", "#7C3AED", "#6D28D9")
        btn_detail.clicked.connect(self._show_detail)
        actions.addWidget(btn_detail)
        actions.addStretch()
        self.content_layout.addLayout(actions)

    @staticmethod
    def _is_delivered(record):
        state = str(
            record.get("estado_entrega", "")
            or record.get("estado", "")
            or record.get("estado_contrato", "")
            or ""
        ).strip().lower()
        return bool(record.get("entregado")) or state in {"entregado", "entregada", "recogido", "recogida"}

    @staticmethod
    def _graduation_amounts(grad):
        total = safe_float(grad.get("monto_total_venta"))
        if total <= 0:
            total = safe_float(grad.get("monto_cobrado"))
            total += sum(
                safe_float(item.get("total", item.get("subtotal", item.get("precio", 0))))
                for item in (grad.get("items_venta", []) or [])
                if isinstance(item, dict)
            )
        paid = safe_float(grad.get("monto_adelanto"), total)
        pending = max(0.0, total - paid)
        return total, paid, pending

    def _load_contracts(self):
        sales, _ = load_scoped_list(self.parent_app, self.username, "ventas.json", cargar_ventas)
        patients, _ = load_scoped_list(self.parent_app, self.username, "pacientes.json", cargar_pacientes)
        contracts = {}
        for sale in sales:
            number = str(sale.get("contrato_numero", "") or "").strip()
            if not number:
                continue
            total = sale_total_safe(sale)
            paid = safe_float(sale.get("monto_pagado", sale.get("monto_adelanto", total)), total)
            pending = safe_float(sale.get("monto_faltante"))
            if pending <= 0.05:
                pending = max(0.0, total - paid)
            contracts[number] = {
                "numero": number,
                "paciente": str(sale.get("paciente_nombre", "") or "Sin paciente"),
                "dni": str(sale.get("paciente_dni", "") or "Sin DNI"),
                "fecha": sale.get("fecha", ""),
                "total": total,
                "pagado": paid,
                "saldo": pending,
                "entregado": self._is_delivered(sale),
                "raw": sale,
            }

        for patient in patients:
            history = patient.get("historial_graduaciones", []) or []
            if not isinstance(history, list):
                continue
            for grad in history:
                if not isinstance(grad, dict):
                    continue
                number = str(grad.get("contrato_numero", "") or "").strip()
                if not number or number in contracts:
                    continue
                total, paid, pending = self._graduation_amounts(grad)
                contracts[number] = {
                    "numero": number,
                    "paciente": str(patient.get("nombre", "") or "Sin paciente"),
                    "dni": str(patient.get("dni", "") or "Sin DNI"),
                    "fecha": grad.get("fecha", ""),
                    "total": total,
                    "pagado": paid,
                    "saldo": pending,
                    "entregado": self._is_delivered(grad),
                    "raw": grad,
                }
        return list(contracts.values())

    def reload_data(self):
        self.load_async(self._load_contracts, self._on_loaded, loading_text="Cargando contratos")

    def _on_loaded(self, contracts):
        self.all_contracts = sorted(
            contracts,
            key=lambda contract: parse_date_safe(contract.get("fecha")) or datetime.datetime.min,
            reverse=True,
        )
        self._apply_filter()

    def _apply_filter(self):
        if not hasattr(self, "table"):
            return
        key = str(self.filter_combo.currentData() or "today")
        self.date_edit.setVisible(key == "specific")
        selected_date = self.date_edit.date().toPyDate()
        filtered = []
        for contract in self.all_contracts:
            if key == "pending_pickup" and contract.get("entregado"):
                continue
            if key == "delivered" and not contract.get("entregado"):
                continue
            if key in {"today", "this_week", "previous_week", "specific"} and not date_in_filter(
                contract.get("fecha"), key, selected_date
            ):
                continue
            filtered.append(contract)
        self._render(filtered)

    def _render(self, contracts):
        self.table.setRowCount(0)
        balance = 0.0
        for row, contract in enumerate(contracts):
            self.table.insertRow(row)
            balance += safe_float(contract.get("saldo"))
            values = [
                str(contract.get("numero", "") or "-"),
                str(contract.get("paciente", "") or "Sin paciente"),
                str(contract.get("fecha", "") or "Sin fecha"),
                f"S/ {safe_float(contract.get('total')):.2f}",
                f"S/ {safe_float(contract.get('saldo')):.2f}",
                "Entregado" if contract.get("entregado") else "Pendiente",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter if column != 1 else Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row, column, item)
            self.table.item(row, 0).setData(Qt.UserRole, contract)
        self.summary.setText(f"Contratos: {len(contracts)} | Saldo: S/ {balance:.2f}")

    def _on_selected(self):
        items = self.table.selectedItems()
        self.selected_contract = items[0].data(Qt.UserRole) if items else None

    def _show_detail(self):
        contract = self.selected_contract
        if not isinstance(contract, dict):
            QMessageBox.information(self, "Contratos", "Selecciona un contrato primero.")
            return
        QMessageBox.information(
            self,
            "Detalle del contrato",
            f"Codigo: {contract.get('numero', '-')}\n"
            f"Paciente: {contract.get('paciente', 'Sin paciente')}\n"
            f"DNI: {contract.get('dni', 'Sin DNI')}\n"
            f"Fecha: {contract.get('fecha', 'Sin fecha')}\n"
            f"Total: S/ {safe_float(contract.get('total')):.2f}\n"
            f"Pagado: S/ {safe_float(contract.get('pagado')):.2f}\n"
            f"Saldo: S/ {safe_float(contract.get('saldo')):.2f}\n"
            f"Estado: {'Entregado' if contract.get('entregado') else 'Pendiente de recoger'}",
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_data()
