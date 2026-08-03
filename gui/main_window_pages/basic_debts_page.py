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
    set_button_busy,
)
from utils.file_handler import (
    cargar_pacientes,
    cargar_ventas,
    guardar_graduaciones,
    guardar_pacientes,
    guardar_ventas,
)


class BasicDebtsPage(BasicWindowBase):
    def __init__(self, parent=None):
        super().__init__(
            parent_app=parent,
            title="Deudas",
            subtitle="Consulta deudas reales de ventas sin repetir contratos.",
            loader_text="Cargando deudas",
        )
        self.all_records = []
        self.selected_record = None
        self._updating = False
        self._build_ui()

    def _build_ui(self):
        toolbar = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Pendientes", "pending")
        self.filter_combo.addItem("Todas", "all")
        self.filter_combo.addItem("Pagadas", "paid")
        self.filter_combo.addItem("Vencidas", "overdue")
        self.filter_combo.addItem("Dia especifico", "specific")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_combo)

        self.date_edit = QDateEdit(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.hide()
        self.date_edit.dateChanged.connect(self._apply_filter)
        toolbar.addWidget(self.date_edit)

        self.summary = QLabel("Pendiente: S/ 0.00")
        self.summary.setStyleSheet(
            "font-size: 22px; font-weight: 800; color: #991B1B; "
            "background: #FEE2E2; border: 2px solid #FCA5A5; border-radius: 14px; padding: 12px 16px;"
        )
        toolbar.addWidget(self.summary, 1)
        btn_refresh = make_button("Recargar")
        btn_refresh.clicked.connect(self.reload_data)
        toolbar.addWidget(btn_refresh)
        btn_close = make_button("Cerrar", "#64748B", "#475569")
        btn_close.clicked.connect(self.exit_basic_page)
        toolbar.addWidget(btn_close)
        self.content_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Fecha", "Codigo", "Cliente", "Total", "Pagado", "Debe", "Estado"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.itemSelectionChanged.connect(self._on_selected)
        header = self.table.horizontalHeader()
        for column in (0, 1, 3, 4, 5, 6):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.content_layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.btn_paid = make_button("Marcar como pagado", "#1F9D55", "#157347")
        self.btn_paid.clicked.connect(self._mark_paid)
        actions.addWidget(self.btn_paid)
        actions.addStretch()
        self.content_layout.addLayout(actions)

    @staticmethod
    def _record_key(sale):
        contract = str(sale.get("contrato_numero", "") or "").strip()
        if contract:
            return f"contract:{contract}"
        sale_id = str(sale.get("id", "") or "").strip()
        if sale_id:
            return f"id:{sale_id}"
        order = str(sale.get("numero_orden", "") or "").strip()
        if order:
            return f"order:{order}"
        patient = str(sale.get("paciente_dni", "") or sale.get("paciente_nombre", "") or "").strip().casefold()
        return f"fallback:{str(sale.get('fecha', '') or '').strip()}:{patient}:{sale_total_safe(sale):.2f}"

    def _load_records(self):
        sales, _sales_branch = load_scoped_list(self.parent_app, self.username, "ventas.json", cargar_ventas)
        patients, _patients_branch = load_scoped_list(self.parent_app, self.username, "pacientes.json", cargar_pacientes)
        records = []
        by_debt_id = {}
        legacy_refs = []
        sales_by_id = {}

        for sale in sales if isinstance(sales, list) else []:
            if not isinstance(sale, dict):
                continue
            sale_id = str(sale.get("id", "") or "").strip()
            if sale_id:
                sales_by_id[sale_id] = sale

        for sale in sales if isinstance(sales, list) else []:
            if not isinstance(sale, dict):
                continue
            if bool(sale.get("deuda_anulada")) or str(sale.get("estado_deuda", "") or "").lower() == "anulada":
                continue
            total, paid, pending = self._amounts(sale)
            if pending <= 0.05:
                continue
            debt = dict(sale)
            debt["tipo"] = "venta"
            debt["total"] = total
            debt["monto_pagado"] = paid
            debt["monto_adelanto"] = safe_float(debt.get("monto_adelanto", paid), paid)
            debt["monto_faltante"] = pending
            debt_id = str(debt.get("deuda_id", "") or "").strip()
            records.append(debt)
            if debt_id:
                by_debt_id[debt_id] = debt
            legacy_refs.append(
                {
                    "dni": str(debt.get("paciente_dni", "") or "").strip(),
                    "fecha": str(debt.get("fecha", "") or "").strip(),
                    "total": round(total, 2),
                    "ref": debt,
                }
            )

        for patient in patients if isinstance(patients, list) else []:
            if not isinstance(patient, dict):
                continue
            patient_dni = str(patient.get("dni", "") or "").strip()
            patient_name = str(patient.get("nombre", "") or "").strip()
            for grad in patient.get("historial_graduaciones", []) or []:
                if not isinstance(grad, dict):
                    continue
                if bool(grad.get("deuda_anulada")) or str(grad.get("estado_deuda", "") or "").lower() == "anulada":
                    continue
                total, paid, pending = self._graduation_amounts(grad)
                if total <= 0 or pending <= 0.05:
                    continue

                debt_id = str(grad.get("deuda_id", "") or "").strip()
                grad_date = str(grad.get("fecha", "") or "").strip()
                duplicate = by_debt_id.get(debt_id) if debt_id else None
                if duplicate is None:
                    for legacy in legacy_refs:
                        if legacy["dni"] != patient_dni:
                            continue
                        if not self._dates_equivalent(legacy["fecha"], grad_date):
                            continue
                        if abs(float(legacy["total"]) - float(round(total, 2))) < 0.05:
                            duplicate = legacy["ref"]
                            break
                if duplicate is not None:
                    duplicate["tipo"] = ""
                    if debt_id and not duplicate.get("deuda_id"):
                        duplicate["deuda_id"] = debt_id
                    continue

                debt = dict(grad)
                debt["tipo"] = "graduacion"
                debt["paciente_dni"] = patient_dni
                debt["paciente_nombre"] = patient_name or str(debt.get("paciente_nombre", "") or "").strip()
                debt["total"] = total
                debt["monto_pagado"] = paid
                debt["monto_adelanto"] = paid
                debt["monto_faltante"] = pending
                sale_ref = sales_by_id.get(str(grad.get("venta_relacionada_id", "") or "").strip())
                if isinstance(sale_ref, dict):
                    debt.setdefault("id", sale_ref.get("id"))
                    if not str(debt.get("numero_orden", "") or "").strip():
                        debt["numero_orden"] = sale_ref.get("numero_orden", "")
                    if not str(debt.get("contrato_numero", "") or "").strip():
                        debt["contrato_numero"] = sale_ref.get("contrato_numero", "")
                records.append(debt)
                if debt_id:
                    by_debt_id[debt_id] = debt
                legacy_refs.append(
                    {
                        "dni": patient_dni,
                        "fecha": grad_date,
                        "total": round(total, 2),
                        "ref": debt,
                    }
                )

        return records

    def reload_data(self):
        self.load_async(self._load_records, self._on_loaded, loading_text="Cargando deudas")

    def _on_loaded(self, records):
        self.all_records = sorted(
            records,
            key=lambda sale: parse_date_safe(sale.get("fecha")) or datetime.datetime.min,
            reverse=True,
        )
        self._apply_filter()

    @staticmethod
    def _amounts(sale):
        total = sale_total_safe(sale)
        paid = safe_float(sale.get("monto_pagado", sale.get("monto_adelanto", total)), total)
        pending = safe_float(sale.get("monto_faltante"))
        if pending <= 0.05:
            pending = max(0.0, total - paid)
        return total, min(max(paid, 0.0), total), max(pending, 0.0)

    @staticmethod
    def _dates_equivalent(left, right):
        left_dt = parse_date_safe(left)
        right_dt = parse_date_safe(right)
        if left_dt and right_dt:
            return left_dt.date() == right_dt.date()
        return str(left or "").strip() == str(right or "").strip()

    @staticmethod
    def _graduation_total_canonical(grad):
        if not isinstance(grad, dict):
            return 0.0

        stored_total = safe_float(grad.get("monto_total_venta", 0), 0.0)
        service_amount = safe_float(grad.get("monto_cobrado", 0), 0.0)
        items_total = 0.0
        service_items_total = 0.0
        product_items_total = 0.0
        items_include_service = False

        for item in grad.get("items_venta", []) or []:
            if not isinstance(item, dict):
                continue
            item_name = str(item.get("producto") or item.get("nombre") or "").strip().lower()
            if "servicio de gradu" in item_name or item_name == "graduacion":
                items_include_service = True
            quantity = safe_float(item.get("cantidad", 1), 1.0)
            price = safe_float(item.get("precio_unitario", item.get("precio", 0)), 0.0)
            item_total = safe_float(item.get("subtotal", item.get("total", price * quantity)), 0.0)
            items_total += item_total
            if "servicio de gradu" in item_name or item_name == "graduacion":
                service_items_total += item_total
            else:
                product_items_total += item_total

        if items_total > 0.01:
            if items_include_service:
                if service_amount > 0.01 and abs(service_items_total - service_amount) > 0.05:
                    return service_amount + product_items_total
                return items_total
            if service_amount > 0.01:
                return service_amount + items_total
            return items_total
        if stored_total > 0.01:
            return stored_total
        return service_amount

    @staticmethod
    def _graduation_amounts(grad):
        if not isinstance(grad, dict):
            return 0.0, 0.0, 0.0
        total = BasicDebtsPage._graduation_total_canonical(grad)
        payments = grad.get("pagos_parciales", [])
        paid = 0.0
        if isinstance(payments, list) and payments:
            for payment in payments:
                if isinstance(payment, dict):
                    paid += safe_float(payment.get("monto", 0.0))
        else:
            adelanto_raw = grad.get("monto_adelanto", None)
            if adelanto_raw not in (None, ""):
                paid = safe_float(adelanto_raw, 0.0)
            elif not bool(grad.get("es_pago_parcial", False)) and total > 0:
                paid = total
        pending = max(0.0, total - max(paid, 0.0))
        return total, min(max(paid, 0.0), total), pending

    @staticmethod
    def _build_graduaciones_payload(pacientes):
        graduaciones = []
        for paciente in pacientes if isinstance(pacientes, list) else []:
            if not isinstance(paciente, dict):
                continue
            dni = str(paciente.get("dni", "") or "").strip()
            nombre = str(paciente.get("nombre", "") or "").strip()
            for grad in paciente.get("historial_graduaciones", []) or []:
                if not isinstance(grad, dict):
                    continue
                payload = dict(grad)
                payload.setdefault("dni", dni)
                payload.setdefault("nombre", nombre)
                graduaciones.append(payload)
        return graduaciones

    def _graduation_matches_sale(self, grad, patient_dni, selected, matched_sales):
        if not isinstance(grad, dict) or not isinstance(selected, dict):
            return False
        selected_debt_id = str(selected.get("deuda_id", "") or "").strip()
        selected_contract = str(selected.get("contrato_numero", "") or "").strip()
        selected_date = str(selected.get("fecha", "") or "").strip()
        selected_dni = str(selected.get("paciente_dni", "") or "").strip()
        selected_sale_id = str(selected.get("id", "") or "").strip()

        grad_debt_id = str(grad.get("deuda_id", "") or "").strip()
        grad_contract = str(grad.get("contrato_numero", "") or "").strip()
        grad_date = str(grad.get("fecha", "") or "").strip()
        grad_sale_id = str(grad.get("venta_relacionada_id", "") or "").strip()

        if selected_debt_id and grad_debt_id == selected_debt_id:
            return True
        if selected_sale_id and grad_sale_id == selected_sale_id:
            return True
        if selected_contract and grad_contract and grad_contract == selected_contract:
            return True

        for sale in matched_sales:
            if not isinstance(sale, dict):
                continue
            sale_debt_id = str(sale.get("deuda_id", "") or "").strip()
            sale_contract = str(sale.get("contrato_numero", "") or "").strip()
            sale_id = str(sale.get("id", "") or "").strip()
            if grad_debt_id and sale_debt_id and grad_debt_id == sale_debt_id:
                return True
            if grad_sale_id and sale_id and grad_sale_id == sale_id:
                return True
            if grad_contract and sale_contract and grad_contract == sale_contract:
                return True

        return bool(
            selected_dni
            and grad.get("es_pago_parcial")
            and str(grad_date or "").strip() == selected_date
            and str(patient_dni or "").strip() == selected_dni
        )

    def _apply_filter(self):
        if not hasattr(self, "table"):
            return
        key = str(self.filter_combo.currentData() or "pending")
        self.date_edit.setVisible(key == "specific")
        selected_date = self.date_edit.date().toPyDate()
        today = datetime.date.today()
        filtered = []
        for sale in self.all_records:
            _, _, pending = self._amounts(sale)
            sale_date = parse_date_safe(sale.get("fecha"))
            if key == "pending" and pending <= 0.05:
                continue
            if key == "paid" and pending > 0.05:
                continue
            if key == "overdue" and not (pending > 0.05 and sale_date and sale_date.date() < today):
                continue
            if key == "specific" and not date_in_filter(sale.get("fecha"), "specific", selected_date):
                continue
            filtered.append(sale)
        self._render(filtered)

    def _render(self, records):
        self.table.setRowCount(0)
        pending_total = 0.0
        for row, sale in enumerate(records):
            self.table.insertRow(row)
            total, paid, pending = self._amounts(sale)
            pending_total += pending
            code = str(sale.get("contrato_numero", "") or sale.get("numero_orden", "") or sale.get("id", "") or "-")
            tipo = str(sale.get("tipo", "") or "").strip().lower()
            if tipo == "graduacion":
                code = str(sale.get("contrato_numero", "") or sale.get("numero_orden", "") or sale.get("deuda_id", "") or code)
            status = "Pagada" if pending <= 0.05 else ("Abonada" if paid > 0 else "Pendiente")
            values = [
                str(sale.get("fecha", "") or "Sin fecha"),
                code,
                str(sale.get("paciente_nombre", "") or "Sin cliente"),
                f"S/ {total:.2f}",
                f"S/ {paid:.2f}",
                f"S/ {pending:.2f}",
                status,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter if column != 2 else Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row, column, item)
            self.table.item(row, 0).setData(Qt.UserRole, sale)
        self.summary.setText(f"Registros: {len(records)} | Pendiente: S/ {pending_total:.2f}")

    def _on_selected(self):
        items = self.table.selectedItems()
        self.selected_record = items[0].data(Qt.UserRole) if items else None

    def _mark_paid(self):
        if self._updating:
            return
        selected = self.selected_record
        if not isinstance(selected, dict):
            QMessageBox.information(self, "Deudas", "Selecciona una deuda primero.")
            return
        _, _, pending = self._amounts(selected)
        if pending <= 0.05:
            QMessageBox.information(self, "Deudas", "Esta venta ya esta pagada.")
            return
        answer = QMessageBox.question(
            self,
            "Marcar deuda pagada",
            f"Se registrara el pago completo de S/ {pending:.2f}. Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._updating = True
        set_button_busy(self.btn_paid, True, "Marcar como pagado", "Actualizando")
        try:
            sales = cargar_ventas(self.username) or []
            target_key = self._record_key(selected)
            matched_sales = []
            updated_sales = False
            for sale in sales:
                if not isinstance(sale, dict) or self._record_key(sale) != target_key:
                    continue
                total, _, _ = self._amounts(sale)
                sale["monto_pagado"] = total
                sale["monto_adelanto"] = total
                sale["monto_faltante"] = 0.0
                sale["es_pago_partes"] = False
                sale["es_pago_parcial"] = False
                sale["estado_deuda"] = "pagada"
                matched_sales.append(sale)
                updated_sales = True

            updated_patients = False
            patients = cargar_pacientes(self.username) or []
            for patient in patients if isinstance(patients, list) else []:
                if not isinstance(patient, dict):
                    continue
                for grad in patient.get("historial_graduaciones", []) or []:
                    if not self._graduation_matches_sale(
                        grad,
                        patient.get("dni", ""),
                        selected,
                        matched_sales,
                    ):
                        continue
                    total_grad, paid_grad, pending_grad = self._graduation_amounts(grad)
                    if pending_grad > 0.05:
                        payments = grad.get("pagos_parciales", [])
                        if not isinstance(payments, list):
                            payments = []
                        grad["pagos_parciales"] = list(payments)
                        grad["pagos_parciales"].append(
                            {
                                "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "monto": round(pending_grad, 2),
                                "observacion": "Pago completo registrado desde modo basico",
                            }
                        )
                    elif not isinstance(grad.get("pagos_parciales"), list):
                        grad["pagos_parciales"] = []
                    grad["monto_adelanto"] = total_grad if total_grad > 0 else paid_grad
                    grad["es_pago_parcial"] = False
                    grad["estado_deuda"] = "pagada"
                    updated_patients = True

            if updated_patients:
                guardar_pacientes(self.username, patients)
                guardar_graduaciones(self.username, self._build_graduaciones_payload(patients))

            if not updated_sales and not updated_patients:
                raise ValueError("No se encontro la deuda original para actualizarla.")
            if updated_sales:
                guardar_ventas(self.username, sales)
            QMessageBox.information(self, "Deudas", "La deuda fue marcada como pagada.")
            self.reload_data()
        except Exception as exc:
            QMessageBox.warning(self, "Deudas", f"No se pudo actualizar la deuda.\n\n{exc}")
        finally:
            set_button_busy(self.btn_paid, False, "Marcar como pagado", "Actualizando")
            self._updating = False

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_data()
