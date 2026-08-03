import datetime
import uuid

from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, Qt, QTimer
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from utils.file_handler import (
    cargar_metodos_pago,
    cargar_pacientes,
    cargar_ventas,
    guardar_graduaciones,
    guardar_pacientes,
    guardar_ventas,
)

from .workers import SearchDNIWorker, predecir_genero_por_nombre


class GraduacionPaymentDialog(QtWidgets.QDialog):
    def __init__(self, username, resumen_items, total_venta, monto_a_pagar, pago_parcial=False, prefill=None, parent=None):
        super().__init__(parent)
        self.username = username
        self.resumen_items = list(resumen_items or [])
        self.total_venta = float(total_venta or 0.0)
        self.monto_a_pagar = float(monto_a_pagar or 0.0)
        self.pago_parcial = bool(pago_parcial)
        self.prefill = prefill if isinstance(prefill, dict) else {}
        self.setWindowTitle("Confirmar método de pago")
        self.setModal(True)
        self.resize(760, 560)
        self._setup_ui()
        self._apply_prefill()
        self._toggle_multi_payment(self.check_multi.isChecked())
        self._update_info_label()

    def _load_payment_methods(self):
        try:
            return list(cargar_metodos_pago(self.username) or [])
        except Exception:
            return []

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Resumen de la graduación")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Confirma el resumen y define cómo se cobrará antes de guardar.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #667085; font-size: 12px;")
        layout.addWidget(subtitle)

        self.summary_table = QtWidgets.QTableWidget()
        self.summary_table.setColumnCount(4)
        self.summary_table.setHorizontalHeaderLabels(["Concepto", "Cant.", "Precio", "Total"])
        self.summary_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.summary_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.summary_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.summary_table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.summary_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.summary_table.setFocusPolicy(Qt.NoFocus)
        self.summary_table.setMinimumHeight(220)
        layout.addWidget(self.summary_table)
        self._fill_summary_table()

        totals_frame = QtWidgets.QFrame()
        totals_frame.setStyleSheet("QFrame { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }")
        totals_layout = QtWidgets.QGridLayout(totals_frame)
        totals_layout.setContentsMargins(14, 12, 14, 12)
        totals_layout.addWidget(QtWidgets.QLabel("<b>Total venta:</b>"), 0, 0)
        totals_layout.addWidget(QtWidgets.QLabel(f"S/. {self.total_venta:.2f}"), 0, 1)
        totals_layout.addWidget(QtWidgets.QLabel("<b>Pago actual:</b>"), 0, 2)
        totals_layout.addWidget(
            QtWidgets.QLabel(f"{'Adelanto' if self.pago_parcial else 'Total a cobrar'}: S/. {self.monto_a_pagar:.2f}"),
            0,
            3,
        )
        layout.addWidget(totals_frame)

        payment_group = QtWidgets.QGroupBox("Método de pago")
        payment_layout = QtWidgets.QVBoxLayout(payment_group)
        payment_layout.setContentsMargins(14, 14, 14, 14)
        payment_layout.setSpacing(10)
        methods = self._load_payment_methods()

        single_row = QtWidgets.QHBoxLayout()
        single_row.addWidget(QtWidgets.QLabel("Método principal"))
        self.single_method_combo = QtWidgets.QComboBox()
        self.single_method_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.single_method_combo.addItems(methods or ["Sin métodos de pago"])
        self.single_method_combo.setEnabled(bool(methods))
        single_row.addWidget(self.single_method_combo, 1)
        payment_layout.addLayout(single_row)

        self.check_multi = QtWidgets.QCheckBox("Usar más de un método de pago")
        self.check_multi.toggled.connect(self._toggle_multi_payment)
        payment_layout.addWidget(self.check_multi)

        self.multi_container = QtWidgets.QWidget()
        multi_layout = QtWidgets.QGridLayout(self.multi_container)
        multi_layout.setContentsMargins(0, 0, 0, 0)
        multi_layout.setHorizontalSpacing(10)
        multi_layout.setVerticalSpacing(8)
        multi_layout.addWidget(QtWidgets.QLabel("Método 1"), 0, 0)
        self.multi_method_combo_1 = QtWidgets.QComboBox()
        self.multi_method_combo_1.addItems(methods or ["Sin métodos de pago"])
        self.multi_method_combo_1.setEnabled(bool(methods))
        multi_layout.addWidget(self.multi_method_combo_1, 0, 1)
        multi_layout.addWidget(QtWidgets.QLabel("Monto 1"), 0, 2)
        self.multi_amount_1 = QtWidgets.QDoubleSpinBox()
        self.multi_amount_1.setRange(0.0, 999999.99)
        self.multi_amount_1.setDecimals(2)
        self.multi_amount_1.valueChanged.connect(self._sync_multi_amount_limits)
        multi_layout.addWidget(self.multi_amount_1, 0, 3)
        multi_layout.addWidget(QtWidgets.QLabel("Método 2"), 1, 0)
        self.multi_method_combo_2 = QtWidgets.QComboBox()
        self.multi_method_combo_2.addItems(methods or ["Sin métodos de pago"])
        self.multi_method_combo_2.setEnabled(bool(methods))
        multi_layout.addWidget(self.multi_method_combo_2, 1, 1)
        multi_layout.addWidget(QtWidgets.QLabel("Monto 2"), 1, 2)
        self.multi_amount_2 = QtWidgets.QDoubleSpinBox()
        self.multi_amount_2.setRange(0.0, 999999.99)
        self.multi_amount_2.setDecimals(2)
        self.multi_amount_2.valueChanged.connect(self._sync_multi_amount_limits)
        multi_layout.addWidget(self.multi_amount_2, 1, 3)
        payment_layout.addWidget(self.multi_container)

        self.info_label = QtWidgets.QLabel("")
        self.info_label.setStyleSheet("color: #475467; font-size: 11px;")
        payment_layout.addWidget(self.info_label)
        layout.addWidget(payment_group)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_accept = QtWidgets.QPushButton("Guardar")
        btn_accept.setDefault(True)
        btn_accept.clicked.connect(self.accept)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_accept)
        layout.addLayout(buttons)

    def _fill_summary_table(self):
        self.summary_table.setRowCount(len(self.resumen_items))
        for row, item in enumerate(self.resumen_items):
            concepto = str(item.get("producto") or item.get("nombre") or "Concepto")
            cantidad = int(item.get("cantidad", 1) or 1)
            precio = float(item.get("precio_unitario", item.get("precio", 0)) or 0)
            total = float(item.get("subtotal", item.get("total", precio * cantidad)) or 0)
            self.summary_table.setItem(row, 0, QtWidgets.QTableWidgetItem(concepto))
            self.summary_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(cantidad)))
            self.summary_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"S/. {precio:.2f}"))
            self.summary_table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"S/. {total:.2f}"))

    def _apply_prefill(self):
        detalles = list(self.prefill.get("metodos_pago_detalle") or [])
        metodo_pago = str(self.prefill.get("metodo_pago", "") or "").strip()
        metodo_simple_prefill = metodo_pago
        if len(detalles) == 1 and not metodo_simple_prefill:
            metodo_simple_prefill = str(detalles[0].get("metodo", "") or "").strip()
        if metodo_simple_prefill.lower().startswith("mixto -"):
            metodo_simple_prefill = ""
        if len(detalles) >= 2:
            self.check_multi.setChecked(True)
            for combo, key in ((self.multi_method_combo_1, 0), (self.multi_method_combo_2, 1)):
                metodo = str(detalles[key].get("metodo", "") or "").strip()
                idx = combo.findText(metodo)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.multi_amount_1.setValue(float(detalles[0].get("monto", 0) or 0))
            self.multi_amount_2.setValue(float(detalles[1].get("monto", 0) or 0))
            self._sync_multi_amount_limits()
            return
        if metodo_simple_prefill:
            idx = self.single_method_combo.findText(metodo_simple_prefill)
            if idx >= 0:
                self.single_method_combo.setCurrentIndex(idx)

    def _toggle_multi_payment(self, checked):
        self.single_method_combo.setEnabled(
            (not checked) and self.single_method_combo.count() > 0 and self.single_method_combo.itemText(0) != "Sin métodos de pago"
        )
        self.multi_container.setVisible(bool(checked))
        self._sync_multi_amount_limits()
        self._update_info_label()

    def _update_info_label(self):
        if self.check_multi.isChecked():
            self.info_label.setText(f"La suma de ambos montos debe ser exactamente S/. {self.monto_a_pagar:.2f}.")
        else:
            self.info_label.setText(f"Se registrará un único método por S/. {self.monto_a_pagar:.2f}.")

    def _sync_multi_amount_limits(self):
        limite_total = max(0.0, round(self.monto_a_pagar, 2))
        self.multi_amount_1.blockSignals(True)
        self.multi_amount_2.blockSignals(True)
        try:
            valor_1 = min(float(self.multi_amount_1.value() or 0.0), limite_total)
            valor_2 = min(float(self.multi_amount_2.value() or 0.0), limite_total)

            max_para_1 = max(0.0, round(limite_total - valor_2, 2))
            if valor_1 > max_para_1:
                valor_1 = max_para_1

            max_para_2 = max(0.0, round(limite_total - valor_1, 2))
            if valor_2 > max_para_2:
                valor_2 = max_para_2

            self.multi_amount_1.setMaximum(max(0.0, round(limite_total - valor_2, 2)))
            self.multi_amount_2.setMaximum(max(0.0, round(limite_total - valor_1, 2)))
            self.multi_amount_1.setValue(round(valor_1, 2))
            self.multi_amount_2.setValue(round(valor_2, 2))
        finally:
            self.multi_amount_1.blockSignals(False)
            self.multi_amount_2.blockSignals(False)

    def get_payment_state(self):
        return {
            "mixed": bool(self.check_multi.isChecked()),
            "single_method": str(self.single_method_combo.currentText() or "").strip(),
            "method_1": str(self.multi_method_combo_1.currentText() or "").strip(),
            "method_2": str(self.multi_method_combo_2.currentText() or "").strip(),
            "amount_1": float(self.multi_amount_1.value()),
            "amount_2": float(self.multi_amount_2.value()),
        }


class CreatePatientPagePatientActionsMixin:
    @staticmethod
    def _is_anonymous_dni(dni):
        return str(dni or "").strip() == "00000000"

    @staticmethod
    def _default_extra_contract_fields():
        return {
            "telefono": "",
            "direccion": "",
            "cristales": "",
            "resina": "",
            "color": "",
            "bifocal_tipo": "",
            "multifocal_tipo": "",
            "altura": "",
            "luna_tipo": "",
            "luna_costo": "",
            "luna_laboratorio": "",
        }

    def _normalize_extra_contract_fields(self, data=None):
        base = self._default_extra_contract_fields()
        if isinstance(data, dict):
            for key in base:
                base[key] = str(data.get(key, "") or "").strip()
        return base

    def _format_payment_method_summary(self, details):
        labels = []
        for item in details if isinstance(details, list) else []:
            if not isinstance(item, dict):
                continue
            metodo = str(item.get("metodo", "") or "").strip()
            monto = float(item.get("monto", 0) or 0)
            if metodo and monto > 0:
                labels.append(f"{metodo}: S/. {monto:.2f}")
        if not labels:
            return ""
        if len(labels) == 1:
            return labels[0].split(": ", 1)[0]
        return "Mixto - " + " | ".join(labels)

    def _build_graduacion_payment_details(self, target_amount, payment_state=None):
        target = float(target_amount or 0.0)
        if target <= 0:
            return "", []

        state = payment_state if isinstance(payment_state, dict) else {}
        metodo_1 = str(state.get("single_method", "") or "").strip()
        if metodo_1 == "Sin métodos de pago":
            metodo_1 = ""

        mixed = bool(state.get("mixed", False))
        if not mixed:
            if not metodo_1:
                raise ValueError("Debe seleccionar un método de pago.")
            return metodo_1, [{"metodo": metodo_1, "monto": round(target, 2)}]

        metodo_2 = str(state.get("method_1", "") or "").strip()
        metodo_3 = str(state.get("method_2", "") or "").strip()
        if metodo_2 == "Sin métodos de pago":
            metodo_2 = ""
        if metodo_3 == "Sin métodos de pago":
            metodo_3 = ""
        monto_1 = float(state.get("amount_1", 0.0) or 0.0)
        monto_2 = float(state.get("amount_2", 0.0) or 0.0)

        if not metodo_2 or not metodo_3:
            raise ValueError("Selecciona los dos métodos para el pago mixto.")
        if metodo_2 == metodo_3:
            raise ValueError("Los métodos del pago mixto deben ser distintos.")
        if monto_1 <= 0 or monto_2 <= 0:
            raise ValueError("Los montos del pago mixto deben ser mayores a 0.")

        total_entered = round(monto_1 + monto_2, 2)
        if abs(total_entered - round(target, 2)) > 0.05:
            raise ValueError(f"El pago mixto debe sumar S/. {target:.2f}.")

        details = [
            {"metodo": metodo_2, "monto": round(monto_1, 2)},
            {"metodo": metodo_3, "monto": round(monto_2, 2)},
        ]
        return self._format_payment_method_summary(details), details

    def _show_graduacion_payment_dialog(self, items_resumen, total_venta, monto_actual):
        prefill = getattr(self, "_graduacion_payment_prefill", {})
        if not isinstance(prefill, dict):
            prefill = {}
        dialog = GraduacionPaymentDialog(
            username=self.username,
            resumen_items=items_resumen,
            total_venta=total_venta,
            monto_a_pagar=monto_actual,
            pago_parcial=bool(getattr(self, "checkbox_en_partes", None) and self.checkbox_en_partes.isChecked()),
            prefill=prefill,
            parent=self,
        )
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return None, None
        payment_state = dialog.get_payment_state()
        metodo_pago, detalles = self._build_graduacion_payment_details(monto_actual, payment_state=payment_state)
        self._graduacion_payment_prefill = {
            "metodo_pago": metodo_pago,
            "metodos_pago_detalle": list(detalles or []),
            "pago_mixto": bool(len(detalles or []) > 1),
        }
        return metodo_pago, detalles

    def _refresh_extra_data_button_tooltip(self):
        if not hasattr(self, "btn_datos_extra") or self.btn_datos_extra is None:
            return
        data = self._normalize_extra_contract_fields(getattr(self, "_extra_contract_fields", {}))
        filled = sum(1 for value in data.values() if str(value or "").strip())
        if filled > 0:
            self.btn_datos_extra.setToolTip(f"Datos extra opcionales ({filled} completados)")
        else:
            self.btn_datos_extra.setToolTip("Completar datos extra opcionales")

    def _editar_datos_extra(self):
        current = self._normalize_extra_contract_fields(getattr(self, "_extra_contract_fields", {}))

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Datos extra")
        dialog.setModal(True)
        dialog.resize(520, 360)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        intro = QtWidgets.QLabel("Completa solo los datos opcionales que necesites para esta graduación.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #5f6b7a; font-size: 12px;")
        layout.addWidget(intro)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        entry_telefono = QtWidgets.QLineEdit(current.get("telefono", ""))
        entry_direccion = QtWidgets.QLineEdit(current.get("direccion", ""))
        entry_cristales = QtWidgets.QLineEdit(current.get("cristales", ""))
        entry_resina = QtWidgets.QLineEdit(current.get("resina", ""))
        entry_color = QtWidgets.QLineEdit(current.get("color", ""))
        entry_bifocal = QtWidgets.QLineEdit(current.get("bifocal_tipo", ""))
        entry_multifocal = QtWidgets.QLineEdit(current.get("multifocal_tipo", ""))
        entry_altura = QtWidgets.QLineEdit(current.get("altura", ""))
        entry_luna_tipo = QtWidgets.QLineEdit(current.get("luna_tipo", ""))
        entry_luna_costo = QtWidgets.QLineEdit(current.get("luna_costo", ""))
        entry_luna_laboratorio = QtWidgets.QLineEdit(current.get("luna_laboratorio", ""))

        live_widgets = {
            "telefono": entry_telefono,
            "direccion": entry_direccion,
            "cristales": entry_cristales,
            "resina": entry_resina,
            "color": entry_color,
            "bifocal_tipo": entry_bifocal,
            "multifocal_tipo": entry_multifocal,
            "altura": entry_altura,
            "luna_tipo": entry_luna_tipo,
            "luna_costo": entry_luna_costo,
            "luna_laboratorio": entry_luna_laboratorio,
        }

        def _sync_live_extra_fields():
            self._extra_contract_fields = self._normalize_extra_contract_fields(
                {key: widget.text() for key, widget in live_widgets.items()}
            )
            self._refresh_extra_data_button_tooltip()

        for widget in live_widgets.values():
            widget.textChanged.connect(_sync_live_extra_fields)

        form.addRow("Teléfono:", entry_telefono)
        form.addRow("Dirección:", entry_direccion)
        form.addRow("Cristales:", entry_cristales)
        form.addRow("Resina:", entry_resina)
        form.addRow("Color:", entry_color)
        form.addRow("Bifocal:", entry_bifocal)
        form.addRow("Multifocal:", entry_multifocal)
        form.addRow("Altura:", entry_altura)
        form.addRow("Tipo Luna:", entry_luna_tipo)
        form.addRow("Costo Luna (S/.):", entry_luna_costo)
        form.addRow("Laboratorio:", entry_luna_laboratorio)
        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()

        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(dialog.reject)
        btn_save = QtWidgets.QPushButton("Guardar")
        btn_save.clicked.connect(dialog.accept)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_save)
        layout.addLayout(buttons)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        _sync_live_extra_fields()

    @staticmethod
    def _extract_contract_sequence(value):
        digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
        if not digits:
            return 0
        try:
            return int(digits)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _format_contract_sequence(value):
        try:
            return f"{max(1, int(value or 1)):07d}"
        except (TypeError, ValueError):
            return "0000001"

    def _compute_next_contract_sequence(self, pacientes=None):
        highest = 0
        
        # 1. Buscar en la lista de pacientes (historial de graduaciones)
        source = pacientes if isinstance(pacientes, list) else []
        for paciente in source:
            if not isinstance(paciente, dict):
                continue
            historial = paciente.get("historial_graduaciones", []) or []
            if not isinstance(historial, list):
                continue
            for grad in historial:
                if not isinstance(grad, dict):
                    continue
                seq = self._extract_contract_sequence(grad.get("contrato_numero", ""))
                if seq > highest:
                    highest = seq
                    
        # 2. Buscar en el archivo de VENTAS (donde se registran los contratos finales)
        try:
            from utils.file_handler import cargar_ventas
            # Intentar obtener el username de varias fuentes comunes en esta app
            username = getattr(self, "username", "")
            if not username and hasattr(self, "parent"):
                parent = self.parent()
                username = getattr(parent, "username", "")
            
            if username:
                ventas = cargar_ventas(username)
                if isinstance(ventas, list):
                    for v in ventas:
                        if not isinstance(v, dict): continue
                        # Buscar tanto en la raíz de la venta como en posibles campos alternos
                        seq_v = self._extract_contract_sequence(v.get("contrato_numero", ""))
                        if seq_v > highest:
                            highest = seq_v
        except Exception:
            pass
            
        return highest + 1 if highest > 0 else 1

    def _resolve_contract_number_for_form(self, pacientes=None):
        existing = str(getattr(self, "_prefilled_contrato_numero", "") or "").strip()
        if existing:
            return self._format_contract_sequence(self._extract_contract_sequence(existing))
        next_seq = self._compute_next_contract_sequence(pacientes=pacientes)
        return self._format_contract_sequence(next_seq)

    def _refresh_contract_number_preview(self, pacientes=None):
        if not hasattr(self, "label_contrato_numero_top") or self.label_contrato_numero_top is None:
            return
        contract_number = self._resolve_contract_number_for_form(pacientes=pacientes)
        self.label_contrato_numero_top.setText(f"Contrato: {contract_number}")

    def _editar_contrato_numero(self):
        current_value = self._resolve_contract_number_for_form()
        value, ok = QInputDialog.getText(
            self,
            "Editar contrato",
            "Número de contrato:",
            QLineEdit.Normal,
            str(current_value or ""),
        )
        if not ok:
            return

        digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
        if not digits:
            QMessageBox.warning(self, "Contrato", "Ingresa un número de contrato válido.")
            return

        self._prefilled_contrato_numero = self._format_contract_sequence(digits)
        self._refresh_contract_number_preview()

    def _set_save_busy_ui(self, active: bool, message: str = ""):
        try:
            if hasattr(self, "btn_guardar_paciente_top") and self.btn_guardar_paciente_top is not None:
                self.btn_guardar_paciente_top.setEnabled(not active)
                self.btn_guardar_paciente_top.setText("Guardando..." if active else "Guardar")
        except Exception:
            pass

        parent_app = getattr(self, "parent_app", None)
        try:
            if active and parent_app is not None:
                status_message = message or "Guardando graduación..."
                if hasattr(parent_app, "system_status_text") and parent_app.system_status_text is not None:
                    parent_app.system_status_text.setText(status_message)
                    parent_app.system_status_text.setToolTip(status_message)
                    parent_app.system_status_text.setCursor(Qt.ArrowCursor)
                if hasattr(parent_app, "_apply_system_status_style"):
                    parent_app._apply_system_status_style("#2563EB")
                if hasattr(parent_app, "_set_system_status_icon_state"):
                    parent_app._set_system_status_icon_state("dot", "#2563EB")
                if hasattr(parent_app, "_set_system_status_progress_state"):
                    parent_app._set_system_status_progress_state(35, "#2563EB", True)
            elif not active and parent_app is not None:
                if hasattr(parent_app, "_queue_system_status_snapshot"):
                    parent_app._queue_system_status_snapshot()
                if hasattr(parent_app, "_refresh_system_status_bar"):
                    parent_app._refresh_system_status_bar()
        except Exception:
            pass

        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass

    def _generar_id_venta_unico_local(self, ventas):
        max_id = 0
        for venta in ventas if isinstance(ventas, list) else []:
            if not isinstance(venta, dict):
                continue
            try:
                vid = int(venta.get("id", 0) or 0)
                if vid > max_id:
                    max_id = vid
            except (TypeError, ValueError):
                continue
        return max_id + 1

    def _construir_items_venta_graduacion(self, optometra, monto_total):
        items = []
        monto_f = float(monto_total or 0.0)

        # 1. El Servicio de Graduación es el item principal de esta página.
        # Lo añadimos SIEMPRE al inicio.
        items.append(
            {
                "producto": "Servicio de Graduacion",
                "nombre": "Servicio de Graduacion",
                "descripcion": f"Graduacion - {optometra or 'Sin optometra'}",
                "cantidad": 1,
                "precio_unitario": monto_f,
                "precio": monto_f,
                "subtotal": monto_f,
                "total": monto_f,
            }
        )

        # 2. Añadir los productos seleccionados (Monturas, Lunas, etc.)
        for item in self.items_venta if isinstance(self.items_venta, list) else []:
            if not isinstance(item, dict):
                continue
            
            # EVITAR DUPLICADOS: Si por alguna razón el servicio ya está aquí, lo saltamos
            nombre_i = str(item.get("nombre") or item.get("producto") or "").strip().lower()
            if "servicio de gradu" in nombre_i:
                continue

            cantidad = int(item.get("cantidad", 1) or 1)
            precio = self._safe_float_value(item.get("precio_unitario", item.get("precio", 0)))
            subtotal = self._safe_float_value(item.get("total", item.get("subtotal", precio * cantidad)))

            items.append(
                {
                    "producto": item.get("nombre") or item.get("producto") or "Producto",
                    "nombre": item.get("nombre") or item.get("producto") or "Producto",
                    "codigo": item.get("codigo", ""),
                    "cantidad": cantidad,
                    "precio_unitario": precio,
                    "precio": precio,
                    "subtotal": subtotal,
                    "total": subtotal,
                }
            )

        return items

    def _registrar_graduacion_en_ventas(
        self,
        username,
        dni,
        nombre,
        optometra,
        monto_total_grad,
        monto_adelanto,
        en_partes,
        deuda_grad_id,
        usuario_registrador,
        graduacion_data,
    ):
        ventas = cargar_ventas(username) or []
        venta_relacionada_id = str(graduacion_data.get("venta_relacionada_id", "") or "").strip()
        deuda_id_ref = str(graduacion_data.get("deuda_id", "") or deuda_grad_id or "").strip()
        venta_existente = None

        if venta_relacionada_id:
            venta_existente = next(
                (
                    venta for venta in ventas
                    if isinstance(venta, dict) and str(venta.get("id", "")).strip() == str(venta_relacionada_id).strip()
                ),
                None,
            )
        if venta_existente is None and deuda_id_ref:
            venta_existente = next(
                (
                    venta for venta in ventas
                    if isinstance(venta, dict)
                    and str(venta.get("deuda_id", "") or "").strip() == deuda_id_ref
                    and str(venta.get("tipo_venta", "") or "").strip().lower() == "graduacion"
                ),
                None,
            )
            if venta_existente is not None and not venta_relacionada_id:
                venta_relacionada_id = str(venta_existente.get("id", "") or "").strip()
                graduacion_data["venta_relacionada_id"] = venta_relacionada_id

        # USAR DATOS YA CONSOLIDADOS PARA EVITAR DUPLICIDAD (100 + 50 = 150)
        items = graduacion_data.get("items_venta", [])
        total_venta = float(graduacion_data.get("monto_total_venta", 0.0))

        if total_venta <= 0:
            # Fallback extremo solo si no hay nada calculado
            total_venta = float(monto_total_grad or 0.0)

        total_venta = round(total_venta, 2)
        subtotal = round(total_venta / 1.18, 2) if total_venta > 0 else 0.0
        igv = round(total_venta - subtotal, 2)
        monto_pagado = float(graduacion_data.get("monto_adelanto", total_venta))
        monto_faltante = max(0.0, total_venta - monto_pagado)

        # Usar la fecha seleccionada en el formulario (de graduacion_data)
        fecha_registro_venta = str(graduacion_data.get("fecha", "") or "").strip()
        if not fecha_registro_venta:
            fecha_registro_venta = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        elif len(fecha_registro_venta) <= 10: # Si solo tiene fecha sin hora
            fecha_registro_venta += " " + datetime.datetime.now().strftime("%H:%M:%S")

        venta_payload = {
            "fecha": fecha_registro_venta,
            "paciente_dni": dni,
            "paciente_nombre": nombre,
            "usuario": self.username,
            "helper_name": self.parent_app.helper_name if (self.parent_app and self.parent_app.is_helper) else None,
            "contrato_numero": str(graduacion_data.get("contrato_numero", "") or "").strip(),
            "items": items,
            "subtotal": subtotal,
            "igv": igv,
            "total": total_venta,
            "descuento_total": 0.0,
            "metodo_pago": str(graduacion_data.get("metodo_pago", "") or "graduacion"),
            "metodos_pago_detalle": list(graduacion_data.get("metodos_pago_detalle", []) or []),
            "pago_mixto": bool(graduacion_data.get("pago_mixto", False)),
            "es_pago_partes": bool(en_partes and monto_faltante > 0.05),
            "es_pago_parcial": bool(en_partes and monto_faltante > 0.05),
            "monto_adelanto": monto_pagado if en_partes else 0.0,
            "monto_faltante": monto_faltante,
            "monto_pagado": monto_pagado,
            "vendedor": usuario_registrador,
            "optometra": optometra,
            "tipo_venta": "graduacion",
            "origen": "graduacion",
            "descripcion": f"Graduación - {optometra or 'Sin optómetra'}",
            "comision_activada": bool(graduacion_data.get("comision_activada", False)),
            "comision_monto": float(graduacion_data.get("comision_monto", 0.0) or 0.0),
            "comision_usuario": str(graduacion_data.get("comision_usuario", "") or ""),
            "luna_tipo": graduacion_data.get("luna_tipo", ""),
            "luna_costo": graduacion_data.get("luna_costo", ""),
            "luna_laboratorio": graduacion_data.get("luna_laboratorio", ""),
        }

        if deuda_id_ref:
            venta_payload["deuda_id"] = deuda_id_ref

        if venta_existente is not None:
            venta_payload["id"] = venta_existente.get("id")
            venta_existente.clear()
            venta_existente.update(venta_payload)
            venta_id = venta_payload["id"]
        else:
            venta_id = self._generar_id_venta_unico_local(ventas)
            venta_payload["id"] = venta_id
            ventas.append(venta_payload)

        guardar_ventas(username, ventas)
        return venta_id

    def _current_registrador_name(self):
        if self.parent_app:
            if getattr(self.parent_app, "is_helper", False):
                return getattr(self.parent_app, "helper_name", None) or "Ayudante"
            return getattr(self.parent_app, "username", None) or "Usuario"
        return "Sistema"

    def _current_comision_beneficiario_name(self):
        if hasattr(self, "optometra_combo") and self.optometra_combo.count() > 0:
            optometra = str(self.optometra_combo.currentText() or "").strip()
            if optometra and optometra != "Sin Optometras":
                return optometra
        return "Optómetra"

    def _safe_float_value(self, value):
        try:
            return float(str(value or "0").strip().replace("S/.", "").replace("S/", "").replace(",", "").replace(" ", ""))
        except (TypeError, ValueError):
            return 0.0

    def buscar_por_dni(self):
        raw_dni = self.entry_dni.text().strip()
        dni = "".join(filter(str.isdigit, raw_dni))
        if not dni:
            QMessageBox.critical(self, "Error", "El campo DNI esta vacio. Ingrese un DNI valido.")
            return
        if len(dni) != 8:
            QMessageBox.critical(
                self,
                "Error",
                f"El DNI ingresado ('{raw_dni}') debe tener exactamente 8 digitos numericos. Usted ingreso: '{dni}' ({len(dni)} digitos)",
            )
            return
        self.start_loader_animation()
        self.search_worker = SearchDNIWorker(dni)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.start()

    def on_search_finished(self, full_name, birth_date_str, success):
        if success and full_name:
            self.entry_paciente.setText(full_name)
            if birth_date_str:
                try:
                    birth_qdate = QDate.fromString(birth_date_str, "yyyy-MM-dd")
                    self.entry_fecha_nacimiento.setDate(birth_qdate)
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Advertencia",
                        "Fecha de nacimiento invalida de la API. Por favor, ingresela manualmente.",
                    )
                    self.entry_fecha_nacimiento.setDate(QDate.currentDate())

            primer_nombre = full_name.split()[0] if full_name else ""
            genero_predicho = predecir_genero_por_nombre(primer_nombre)
            index = self.genero_combo.findText(genero_predicho, Qt.MatchFixedString)
            if index >= 0:
                self.genero_combo.setCurrentIndex(index)
            else:
                self.genero_combo.setCurrentIndex(self.genero_combo.findText("No especificado"))
            self.stop_loader_animation(success=True)
        else:
            self.stop_loader_animation(success=False)
            QMessageBox.warning(self, "No Encontrado", "No se encontraron datos para el DNI ingresado.")

    def on_search_error(self, error_msg):
        self.stop_loader_animation(success=False)
        QMessageBox.critical(self, "Error", f"Error al buscar DNI: {error_msg}")

    def _build_graduaciones_payload(self, pacientes):
        graduaciones = []
        for paciente in pacientes if isinstance(pacientes, list) else []:
            if not isinstance(paciente, dict):
                continue
            historial = paciente.get("historial_graduaciones", [])
            if not isinstance(historial, list):
                continue
            for grad in historial:
                if not isinstance(grad, dict):
                    continue
                monto_total = str(grad.get("monto_cobrado", "0"))
                monto_pagado = str(grad.get("monto_adelanto") if grad.get("monto_adelanto") else monto_total)
                graduaciones.append(
                    {
                        "fecha": grad.get("fecha", ""),
                        "paciente": paciente.get("nombre", "N/A"),
                        "dni": paciente.get("dni", ""),
                        "optica_medico": grad.get(
                            "medico_optometra",
                            grad.get("optometra", grad.get("optica_medico", "N/A")),
                        ),
                        "tipo": grad.get("tipo", "Graduacion"),
                        "informacion": grad.get("prescripcion", grad.get("informacion", "")),
                        "precio": monto_total,
                        "pago": monto_pagado,
                        "id_paciente": paciente.get("id", ""),
                    }
                )
        return graduaciones

    def guardar_paciente(self):
        if self.parent_app and self.parent_app.is_helper:
            print("[DEBUG] Es helper. Verificando permiso...")
            if not self.parent_app.puede_hacer_accion("pacientes", "crear"):
                print("[DEBUG] Helper NO tiene permiso para crear pacientes")
                QMessageBox.warning(self, "Permiso Denegado", "No tienes permiso para crear nuevos pacientes.")
                return
            print("[DEBUG] Helper SI tiene permiso para crear pacientes")
        else:
            print("[DEBUG] No es helper o parent_app no existe. Continuando...")

        raw_dni = self.entry_dni.text().strip()
        dni = "".join(filter(str.isdigit, raw_dni))
        if raw_dni != dni:
            self.entry_dni.setText(dni)
        nombre = self.entry_paciente.text().strip()
        fecha = self.entry_fecha.text().strip()
        genero = self.genero_combo.currentText()
        optometra = (
            self.optometra_combo.currentText()
            if self.optometra_combo.count() > 0 and self.optometra_combo.currentText() != "Sin Optometras"
            else None
        )
        proxima_cita_fecha = self.entry_proxima_cita.date().toString("dd/MM/yyyy") if self.check_proxima_cita.isChecked() else None
        observacion = self.text_observacion.toPlainText().strip()
        monto_cobrado = self.entry_monto_cobrado.text().strip()
        en_partes = self.checkbox_en_partes.isChecked()
        metodo_pago_graduacion = ""

        if not dni:
            print(f"[VALIDACION DNI] Error: campo vacio. Valor ingresado: '{raw_dni}' -> Filtrado: '{dni}'")
            QMessageBox.critical(self, "Error", "El campo DNI esta vacio. Ingrese un DNI valido.")
            return
        if not nombre or not fecha:
            QMessageBox.critical(self, "Error", "El Nombre y la Fecha son campos obligatorios.")
            return
        if not optometra or optometra == "Sin Optometras":
            QMessageBox.critical(self, "Error", "Debe seleccionar un optometra.")
            return

        monto_adelanto = 0
        if en_partes:
            monto_referencia = self._safe_float_value(monto_cobrado)
            for item in getattr(self, "items_venta", []) or []:
                if isinstance(item, dict):
                    monto_referencia += self._safe_float_value(
                        item.get("total", item.get("subtotal", item.get("precio_unitario", 0)))
                    )

            monto_prefill = 0.0
            for pago in getattr(self, "_graduacion_payment_prefill", {}).get("metodos_pago_detalle", []) or []:
                if isinstance(pago, dict):
                    monto_prefill += self._safe_float_value(pago.get("monto", 0))
            if monto_prefill <= 0:
                for pago in getattr(self, "_graduacion_payment_prefill", {}).get("pagos_parciales", []) or []:
                    if isinstance(pago, dict):
                        monto_prefill += self._safe_float_value(pago.get("monto", 0))

            default_adelanto = max(0.0, min(monto_prefill if monto_prefill > 0 else monto_referencia, monto_referencia or 999999.99))
            max_adelanto = max(default_adelanto, monto_referencia, 999999.99 if monto_referencia <= 0 else monto_referencia)

            monto_adelanto, ok = QInputDialog.getDouble(
                self,
                "Pago en Partes",
                "Cuanto dejo como adelanto (en soles)?",
                default_adelanto,
                0.0,
                max_adelanto,
                2,
            )
            if not ok:
                return

            if monto_adelanto < 0:
                QMessageBox.critical(self, "Error", "El monto no puede ser negativo")
                return

        username = getattr(self.parent(), "username", self.username)
        pacientes = cargar_pacientes(username)
        contrato_numero = self._resolve_contract_number_for_form(pacientes=pacientes)
        paciente_existente = None if self._is_anonymous_dni(dni) else next((p for p in pacientes if p.get("dni") == dni), None)
        fecha_nacimiento_qdate = self.entry_fecha_nacimiento.date()
        fecha_nacimiento_obj = fecha_nacimiento_qdate.toPyDate()
        hoy = datetime.date.today()
        edad = hoy.year - fecha_nacimiento_obj.year - (
            (hoy.month, hoy.day) < (fecha_nacimiento_obj.month, fecha_nacimiento_obj.day)
        )

        usuario_registrador = self._current_registrador_name()
        extra_fields = self._normalize_extra_contract_fields(getattr(self, "_extra_contract_fields", {}))

        lejos_distp = self.lejos_form_widgets.get("distp", QLineEdit()).text()
        cerca_distp = self.cerca_form_widgets.get("distp", QLineEdit()).text()
        lejos_od_data = {f: self.lejos_form_widgets[f"{f}_OD"].text() for f in ["esferico", "cilindro", "eje", "av", "adicmedia", "prisma"]}
        lejos_od_data["distp"] = lejos_distp
        lejos_oi_data = {f: self.lejos_form_widgets[f"{f}_OI"].text() for f in ["esferico", "cilindro", "eje", "av", "adicmedia", "prisma"]}
        lejos_oi_data["distp"] = ""
        cerca_od_data = {f: self.cerca_form_widgets[f"{f}_OD"].text() for f in ["esferico", "cilindro", "eje", "av", "adicmedia", "prisma"]}
        cerca_od_data["distp"] = cerca_distp
        cerca_oi_data = {f: self.cerca_form_widgets[f"{f}_OI"].text() for f in ["esferico", "cilindro", "eje", "av", "adicmedia", "prisma"]}
        cerca_oi_data["distp"] = ""

        deuda_grad_id = None
        try:
            _mc_clean = str(monto_cobrado or "0").strip().replace("S/.", "").replace("S/", "").replace(",", "").replace(" ", "")
            monto_total_grad = float(_mc_clean)
        except (TypeError, ValueError):
            monto_total_grad = 0.0
        # Obtener items consolidados (Productos + Servicio si aplica)
        items_consolidados = self._construir_items_venta_graduacion(optometra, monto_total_grad)
        monto_total_venta = 0.0
        for item in items_consolidados if isinstance(items_consolidados, list) else []:
            if not isinstance(item, dict):
                continue
            monto_total_venta += self._safe_float_value(
                item.get("total", item.get("subtotal", item.get("precio_unitario", 0)))
            )
        
        # Redondear para evitar problemas de precisión
        monto_total_venta = round(monto_total_venta, 2)

        es_pago_parcial_real = bool(en_partes and max(0.0, monto_total_venta - monto_adelanto) > 0.05)
        monto_pagado_actual = monto_adelanto if en_partes else monto_total_venta
        payment_details_grad = []
        if monto_pagado_actual > 0:
            try:
                metodo_pago_graduacion, payment_details_grad = self._show_graduacion_payment_dialog(
                    items_consolidados,
                    monto_total_venta,
                    monto_pagado_actual,
                )
                if metodo_pago_graduacion is None:
                    return
            except ValueError as exc:
                QMessageBox.critical(self, "Error", str(exc))
                return
        deuda_grad_id = ""
        old_grad = None
        if paciente_existente and self._modo_edicion_graduacion:
            edit_idx = self._graduacion_edit_index
            historial_existente = paciente_existente.get("historial_graduaciones", []) if isinstance(paciente_existente, dict) else []
            if isinstance(edit_idx, int) and 0 <= edit_idx < len(historial_existente):
                old_grad = historial_existente[edit_idx] if isinstance(historial_existente[edit_idx], dict) else None

        if es_pago_parcial_real:
            deuda_grad_id = str((old_grad or {}).get("deuda_id", "") or "").strip()
            if not deuda_grad_id:
                deuda_grad_id = f"DEU-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"

        comision_activada = bool(getattr(self, "check_comision", None) and self.check_comision.isChecked())
        comision_monto = self._safe_float_value(
            self.entry_comision_monto.text() if hasattr(self, "entry_comision_monto") else 0
        ) if comision_activada else 0.0

        graduacion_data = {
            "contrato_numero": contrato_numero,
            "fecha": fecha,
            "proxima_cita": proxima_cita_fecha,
            "optometra": optometra,
            "monto_cobrado": monto_cobrado,
            "metodo_pago": metodo_pago_graduacion if monto_total_grad > 0 else "",
            "metodos_pago_detalle": payment_details_grad,
            "pago_mixto": bool(len(payment_details_grad) > 1),
            "lejos_od": lejos_od_data,
            "lejos_oi": lejos_oi_data,
            "lejos_distp": lejos_distp,
            "cerca_od": cerca_od_data,
            "cerca_oi": cerca_oi_data,
            "cerca_distp": cerca_distp,
            "observacion": observacion,
            "motilidad_versiones": self._normalize_motilidad_versiones(self.motilidad_versiones),
            "items_venta": items_consolidados,
            "monto_total_venta": monto_total_venta,
            "deuda_id": deuda_grad_id,
            "es_pago_parcial": es_pago_parcial_real,
            "monto_adelanto": monto_adelanto if en_partes else monto_total_venta,
            "pagos_parciales": (
                [{"fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "monto": monto_adelanto, "observacion": "Adelanto"}]
                if en_partes and monto_adelanto > 0
                else []
            ),
            "registrado_por": usuario_registrador,
            "comision_activada": comision_activada,
            "comision_porcentaje": 0.0,
            "comision_monto": comision_monto,
            "comision_usuario": (optometra or "") if comision_activada else "",
            "venta_relacionada_id": None,
            "cristales": extra_fields.get("cristales", ""),
            "resina": extra_fields.get("resina", ""),
            "color": extra_fields.get("color", ""),
            "bifocal_tipo": extra_fields.get("bifocal_tipo", ""),
            "multifocal_tipo": extra_fields.get("multifocal_tipo", ""),
            "altura": extra_fields.get("altura", ""),
            "luna_tipo": extra_fields.get("luna_tipo", ""),
            "luna_costo": extra_fields.get("luna_costo", ""),
            "luna_laboratorio": extra_fields.get("luna_laboratorio", ""),
        }

        self._set_save_busy_ui(True, "Guardando graduación...")

        if paciente_existente:
            if extra_fields.get("telefono"):
                paciente_existente["telefono"] = extra_fields.get("telefono", "")
            if extra_fields.get("direccion"):
                paciente_existente["direccion"] = extra_fields.get("direccion", "")
            if "historial_graduaciones" not in paciente_existente:
                paciente_existente["historial_graduaciones"] = []
            if self._modo_edicion_graduacion:
                edit_idx = self._graduacion_edit_index
                if isinstance(edit_idx, int) and 0 <= edit_idx < len(paciente_existente["historial_graduaciones"]):
                    old_grad = paciente_existente["historial_graduaciones"][edit_idx]
                    old_deuda_id = str(old_grad.get("deuda_id", "") or "").strip()
                    old_venta_relacionada_id = str(old_grad.get("venta_relacionada_id", "") or "").strip()
                    if not graduacion_data.get("items_venta") and old_grad.get("items_venta"):
                        graduacion_data["items_venta"] = old_grad["items_venta"]
                    if not graduacion_data.get("pagos_parciales") and old_grad.get("pagos_parciales"):
                        graduacion_data["pagos_parciales"] = old_grad["pagos_parciales"]
                        graduacion_data["es_pago_parcial"] = old_grad.get("es_pago_parcial", False)
                    if old_deuda_id:
                        if graduacion_data.get("es_pago_parcial"):
                            graduacion_data["deuda_id"] = old_deuda_id
                        else:
                            graduacion_data["deuda_id"] = old_deuda_id
                    if not graduacion_data.get("comision_activada") and old_grad.get("comision_activada"):
                        graduacion_data["comision_activada"] = old_grad.get("comision_activada", False)
                        graduacion_data["comision_porcentaje"] = old_grad.get("comision_porcentaje", 0.0)
                        graduacion_data["comision_monto"] = old_grad.get("comision_monto", 0.0)
                        graduacion_data["comision_usuario"] = old_grad.get("comision_usuario", "")
                    if old_venta_relacionada_id:
                        graduacion_data["venta_relacionada_id"] = old_venta_relacionada_id
                    if not graduacion_data.get("contrato_numero") and old_grad.get("contrato_numero"):
                        graduacion_data["contrato_numero"] = old_grad.get("contrato_numero")
                    paciente_existente["historial_graduaciones"][edit_idx] = graduacion_data
                    mensaje = "Graduacion existente actualizada correctamente."
                else:
                    paciente_existente["historial_graduaciones"].append(graduacion_data)
                    mensaje = "Nueva visita registrada y paciente actualizado correctamente."
            else:
                paciente_existente["historial_graduaciones"].append(graduacion_data)
                mensaje = "Nueva visita registrada y paciente actualizado correctamente."

            self.entry_fecha.setText(paciente_existente.get("fecha", datetime.date.today().strftime("%d/%m/%Y")))
            self.entry_fecha.setReadOnly(True)
        else:
            nuevo_paciente = {
                "uuid": str(uuid.uuid4()),
                "dni": dni,
                "nombre": nombre,
                "fecha": fecha,
                "edad": edad,
                "genero": genero,
                "fecha_nacimiento": fecha_nacimiento_qdate.toString("yyyy-MM-dd"),
                "telefono": extra_fields.get("telefono", ""),
                "direccion": extra_fields.get("direccion", ""),
                "historial_graduaciones": [graduacion_data],
            }
            pacientes.append(nuevo_paciente)
            mensaje = "Paciente guardado correctamente."

        try:
            self._set_save_busy_ui(True, "Guardando graduación | registrando venta...")
            venta_id = self._registrar_graduacion_en_ventas(
                username=username,
                dni=dni,
                nombre=nombre,
                optometra=optometra,
                monto_total_grad=monto_total_grad,
                monto_adelanto=monto_adelanto,
                en_partes=en_partes,
                deuda_grad_id=deuda_grad_id,
                usuario_registrador=usuario_registrador,
                graduacion_data=graduacion_data,
            )
            if venta_id is not None:
                graduacion_data["venta_relacionada_id"] = venta_id
        except Exception as e:
            print(f"[DEBUG] Error registrando graduación en ventas: {e}")

        print(f"[DEBUG] Guardando paciente con DNI: {dni}")
        self._set_save_busy_ui(True, "Guardando graduación | guardando paciente...")
        guardar_pacientes(username, pacientes)
        print("[DEBUG] Paciente guardado exitosamente")
        try:
            self._set_save_busy_ui(True, "Guardando graduación | actualizando historial...")
            guardar_graduaciones(username, self._build_graduaciones_payload(pacientes))
            print(f"[DEBUG] Graduaciones sincronizadas para DNI: {dni}")
        except Exception as e:
            print(f"[DEBUG] Error sincronizando graduaciones para nube: {e}")

        try:
            if hasattr(self.parent_app, "app_instance") and hasattr(self.parent_app.app_instance, "audit_manager"):
                audit_mgr = self.parent_app.app_instance.audit_manager
                helper_name = getattr(self.parent_app, "helper_name", None)
                audit_mgr.log_action(
                    user_id=getattr(self.parent_app, "user_id", "unknown"),
                    username=username,
                    helper_name=helper_name,
                    action="crear",
                    module="pacientes",
                    details=(
                        f"Graduacion para {nombre} (DNI: {dni}) - Monto: S/. {monto_cobrado} - "
                        f"Optometra: {optometra} - Comisión: "
                        f"{f'S/. {comision_monto:.2f}' if comision_activada else 'No'}"
                    ),
                )
        except Exception as e:
            print(f"[LIBRO CONTABLE] Error al registrar graduacion: {e}")

        self._set_save_busy_ui(False)
        QMessageBox.information(self, "Exito", mensaje)

        self.clear_patient_form()
        if hasattr(self.parent_app, "load_patient_page"):
            self.parent_app.load_patient_page()
        elif hasattr(self.parent_app, "mostrar_frame"):
            self.parent_app.mostrar_frame(1)
        if hasattr(self.parent_app, "clients_page") and hasattr(self.parent_app.clients_page, "update_clients_table"):
            self.parent_app.clients_page.update_clients_table()

    def on_dni_changed(self, text):
        dni = "".join(filter(str.isdigit, text or ""))
        if not dni or len(dni) < 8:
            return
        if self._is_anonymous_dni(dni):
            self.entry_fecha.setReadOnly(False)
            self.entry_fecha.setText(datetime.date.today().strftime("%d/%m/%Y"))
            self.motilidad_versiones = self._default_motilidad_versiones()
            return
        username = getattr(self.parent(), "username", self.username)
        try:
            pacientes = cargar_pacientes(username)
        except Exception:
            pacientes = []
        paciente = next((p for p in pacientes if p.get("dni") == dni), None)
        if paciente:
            self.entry_paciente.setText(paciente.get("nombre", ""))
            self.entry_fecha.setText(paciente.get("fecha", datetime.date.today().strftime("%d/%m/%Y")))
            if paciente.get("fecha_nacimiento"):
                try:
                    qd = QDate.fromString(paciente["fecha_nacimiento"], "yyyy-MM-dd")
                    self.entry_fecha_nacimiento.setDate(qd)
                except Exception:
                    pass
            gen = paciente.get("genero")
            if gen:
                idx = self.genero_combo.findText(gen)
                if idx >= 0:
                    self.genero_combo.setCurrentIndex(idx)
            historial = paciente.get("historial_graduaciones", [])
            if historial and isinstance(historial, list):
                ultima_grad = historial[-1] if isinstance(historial[-1], dict) else {}
                self.motilidad_versiones = self._normalize_motilidad_versiones(ultima_grad.get("motilidad_versiones", {}))
            else:
                self.motilidad_versiones = self._default_motilidad_versiones()
            extra_from_grad = self._normalize_extra_contract_fields({
                "telefono": paciente.get("telefono", ""),
                "direccion": paciente.get("direccion", ""),
                "cristales": ultima_grad.get("cristales", "") if isinstance(ultima_grad, dict) else "",
                "resina": ultima_grad.get("resina", "") if isinstance(ultima_grad, dict) else "",
                "color": ultima_grad.get("color", "") if isinstance(ultima_grad, dict) else "",
                "bifocal_tipo": ultima_grad.get("bifocal_tipo", "") if isinstance(ultima_grad, dict) else "",
                "multifocal_tipo": ultima_grad.get("multifocal_tipo", "") if isinstance(ultima_grad, dict) else "",
                "altura": ultima_grad.get("altura", "") if isinstance(ultima_grad, dict) else "",
                "luna_tipo": ultima_grad.get("luna_tipo", "") if isinstance(ultima_grad, dict) else "",
                "luna_costo": ultima_grad.get("luna_costo", "") if isinstance(ultima_grad, dict) else "",
                "luna_laboratorio": ultima_grad.get("luna_laboratorio", "") if isinstance(ultima_grad, dict) else "",
            })
            self._extra_contract_fields = extra_from_grad
            self._refresh_extra_data_button_tooltip()
            self.entry_fecha.setReadOnly(True)
        else:
            if self.entry_fecha.isReadOnly():
                self.entry_fecha.setText(datetime.date.today().strftime("%d/%m/%Y"))
            self.entry_fecha.setReadOnly(False)
            self.motilidad_versiones = self._default_motilidad_versiones()
            self._extra_contract_fields = self._default_extra_contract_fields()
            self._refresh_extra_data_button_tooltip()

    def clear_patient_form(self):
        self.entry_dni.clear()
        self.entry_paciente.clear()
        self.entry_fecha.setText(datetime.date.today().strftime("%d/%m/%Y"))
        self.entry_fecha_nacimiento.setDate(QDate.currentDate())
        self.genero_combo.setCurrentIndex(0)
        self.check_proxima_cita.setChecked(False)
        self.entry_proxima_cita.setDate(QDate.currentDate().addDays(30))
        self.text_observacion.clear()
        self.entry_monto_cobrado.clear()
        if hasattr(self, "check_comision"):
            self.check_comision.setChecked(False)
        if hasattr(self, "entry_comision_monto"):
            self.entry_comision_monto.setText("0.00")
        if hasattr(self, "_update_comision_preview"):
            self._update_comision_preview()
        self.cargar_optometras_en_combo()
        self.items_venta = []
        self.motilidad_versiones = self._default_motilidad_versiones()
        self._modo_edicion_graduacion = False
        self._graduacion_edit_index = None
        self._prefilled_contrato_numero = ""
        self._graduacion_payment_prefill = {}
        self._extra_contract_fields = self._default_extra_contract_fields()
        self._refresh_contract_number_preview()
        self._refresh_extra_data_button_tooltip()
        if hasattr(self, "_update_multi_metodo_pago_grad_state"):
            self._update_multi_metodo_pago_grad_state()
        for widgets in [self.lejos_form_widgets, self.cerca_form_widgets]:
            if widgets:
                for widget in widgets.values():
                    widget.clear()

    def _set_clear_graduacion_busy(self, busy, base_text="Limpiando"):
        button = getattr(self, "btn_limpiar_graduacion", None)
        if button is None:
            return

        if busy:
            try:
                button.setEnabled(False)
                button.setProperty("_busy_base_text", base_text)
                button.setText(f"{base_text}.")
            except Exception:
                pass

            timer = getattr(self, "_clear_graduacion_busy_timer", None)
            if timer is None:
                timer = QTimer(self)
                timer.setInterval(180)

                def _tick():
                    try:
                        dots = int(getattr(self, "_clear_graduacion_busy_dots", 0) or 0)
                        dots = (dots % 3) + 1
                        self._clear_graduacion_busy_dots = dots
                        base = str(button.property("_busy_base_text") or base_text)
                        button.setText(f"{base}{'.' * dots}")
                    except Exception:
                        pass

                timer.timeout.connect(_tick)
                self._clear_graduacion_busy_timer = timer

            self._clear_graduacion_busy_dots = 1
            try:
                self._clear_graduacion_busy_timer.start()
            except Exception:
                pass
            return

        timer = getattr(self, "_clear_graduacion_busy_timer", None)
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
        try:
            button.setEnabled(True)
            button.setText("Limpiar")
            button.setProperty("_busy_base_text", None)
        except Exception:
            pass

    def clear_patient_form_with_loader(self):
        if getattr(self, "_clear_graduacion_in_progress", False):
            return

        self._clear_graduacion_in_progress = True
        self._set_clear_graduacion_busy(True)

        def _run_clear():
            try:
                self.clear_patient_form()
            finally:
                QTimer.singleShot(320, _finish_clear)

        def _finish_clear():
            self._clear_graduacion_in_progress = False
            self._set_clear_graduacion_busy(False)

        QTimer.singleShot(0, _run_clear)
