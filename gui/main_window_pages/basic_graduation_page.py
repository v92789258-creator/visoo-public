import datetime
import uuid

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.main_window_pages.basic_mode_common import set_button_busy
from utils.file_handler import (
    cargar_graduaciones,
    cargar_pacientes,
    cargar_ventas,
    guardar_graduaciones,
    guardar_pacientes,
    guardar_ventas,
)


class BasicGraduationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = getattr(parent, "username", None)
        self._product_rows = []
        self._expense_rows = []
        self._rx_fields = {}
        self._saving = False
        self._setup_ui()
        self._reset_form()

    def _setup_ui(self):
        self.setStyleSheet(
            """
            QWidget {
                background: #F7F4EC;
                color: #102A43;
                font-size: 20px;
            }
            QGroupBox {
                background: #FFFFFF;
                border: 2px solid #D9E2EC;
                border-radius: 18px;
                margin-top: 18px;
                padding-top: 18px;
                font-size: 22px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 18px;
                padding: 0 8px;
                color: #0F172A;
            }
            QLabel {
                font-size: 20px;
                color: #243B53;
            }
            QLineEdit, QTextEdit {
                background: #FFFDF8;
                border: 2px solid #BCCCDC;
                border-radius: 14px;
                padding: 12px 14px;
                font-size: 22px;
                color: #102A43;
                min-height: 34px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #2F80ED;
                background: #FFFFFF;
            }
            QPushButton {
                min-height: 54px;
                border-radius: 14px;
                font-size: 20px;
                font-weight: 700;
                padding: 10px 18px;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)

        title = QLabel("Nueva Graduacion - Modo Basico")
        title.setStyleSheet("font-size: 40px; font-weight: 800; color: #0B1F33;")
        layout.addWidget(title)

        subtitle = QLabel("Registro simple de graduacion, productos y gastos.")
        subtitle.setStyleSheet("font-size: 22px; color: #486581;")
        layout.addWidget(subtitle)

        layout.addLayout(self._build_top_actions())

        layout.addWidget(self._build_basic_info_group())
        layout.addWidget(self._build_service_group())
        layout.addWidget(self._build_rx_group("Vision de Lejos", "lejos"))
        layout.addWidget(self._build_rx_group("Vision de Cerca", "cerca"))
        layout.addWidget(self._build_products_group())
        layout.addWidget(self._build_expenses_group())
        layout.addWidget(self._build_observation_group())
        layout.addLayout(self._build_footer_actions())
        layout.addStretch()

    def _build_top_actions(self):
        layout = QHBoxLayout()
        layout.setSpacing(14)

        self.btn_save_top = QPushButton("GUARDAR GRADUACION")
        self.btn_save_top.setStyleSheet(
            "QPushButton { background: #1F9D55; color: white; border: 3px solid #157347; }"
            "QPushButton:hover { background: #157347; }"
        )
        self.btn_save_top.clicked.connect(self._save_basic_graduation)
        layout.addWidget(self.btn_save_top, 2)

        self.btn_clear_top = QPushButton("LIMPIAR TODO")
        self.btn_clear_top.setStyleSheet(
            "QPushButton { background: #F59E0B; color: #1F2937; border: 3px solid #D97706; }"
            "QPushButton:hover { background: #D97706; color: white; }"
        )
        self.btn_clear_top.clicked.connect(self._reset_form)
        layout.addWidget(self.btn_clear_top, 1)

        btn_home = QPushButton("VOLVER AL INICIO")
        btn_home.setStyleSheet(
            "QPushButton { background: #64748B; color: white; border: 3px solid #475569; }"
            "QPushButton:hover { background: #475569; }"
        )
        btn_home.clicked.connect(
            lambda: self.parent_app.go_to_home()
            if self.parent_app and hasattr(self.parent_app, "go_to_home")
            else None
        )
        layout.addWidget(btn_home, 1)

        return layout

    def _build_basic_info_group(self):
        group = QGroupBox("Paciente")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.entry_fecha = QLineEdit()
        self.entry_dni = QLineEdit()
        self.entry_dni.setPlaceholderText("00000000")
        self.entry_nombre = QLineEdit()
        self.entry_nombre.setPlaceholderText("Nombre del paciente")
        self.entry_contrato = QLineEdit()

        btn_refresh_contract = QPushButton("Nuevo contrato")
        btn_refresh_contract.setStyleSheet(
            "QPushButton { background: #2F80ED; color: white; border: 3px solid #1C64D1; }"
            "QPushButton:hover { background: #1C64D1; }"
        )
        btn_refresh_contract.clicked.connect(self._refresh_contract_number)

        grid.addWidget(QLabel("Fecha"), 0, 0)
        grid.addWidget(self.entry_fecha, 0, 1)
        grid.addWidget(QLabel("DNI"), 0, 2)
        grid.addWidget(self.entry_dni, 0, 3)
        grid.addWidget(QLabel("Nombre"), 1, 0)
        grid.addWidget(self.entry_nombre, 1, 1, 1, 3)
        grid.addWidget(QLabel("Contrato"), 2, 0)
        grid.addWidget(self.entry_contrato, 2, 1, 1, 2)
        grid.addWidget(btn_refresh_contract, 2, 3)
        return group

    def _build_service_group(self):
        group = QGroupBox("Servicio")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.entry_service_name = QLineEdit("Servicio de Graduacion")
        self.entry_service_cost = QLineEdit()
        self.entry_service_cost.setPlaceholderText("0.00")
        self.entry_service_cost.textChanged.connect(self._update_totals_preview)

        grid.addWidget(QLabel("Servicio"), 0, 0)
        grid.addWidget(self.entry_service_name, 0, 1)
        grid.addWidget(QLabel("Costo"), 0, 2)
        grid.addWidget(self.entry_service_cost, 0, 3)
        return group

    def _build_rx_group(self, title, prefix):
        group = QGroupBox(title)
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        headers = ["Ojo", "Esferico", "Cilindro", "Eje", "A.V", "DIP", "Adicion", "Prisma"]
        for col, header in enumerate(headers):
            lbl = QLabel(header)
            lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #334155;")
            grid.addWidget(lbl, 0, col)

        field_map = {
            "Esferico": "esferico",
            "Cilindro": "cilindro",
            "Eje": "eje",
            "A.V": "av",
            "DIP": "distp",
            "Adicion": "adicmedia",
            "Prisma": "prisma",
        }
        for row, eye in enumerate(("OD", "OI"), start=1):
            eye_label = QLabel(eye)
            eye_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
            grid.addWidget(eye_label, row, 0)
            for col, header in enumerate(headers[1:], start=1):
                key = (prefix, eye, field_map[header])
                edit = QLineEdit()
                edit.setPlaceholderText("-")
                self._rx_fields[key] = edit
                grid.addWidget(edit, row, col)
        return group

    def _build_products_group(self):
        group = QGroupBox("Productos")
        layout = QVBoxLayout(group)
        layout.setSpacing(14)

        header = QHBoxLayout()
        helper = QLabel("Agrega uno o mas productos con su precio.")
        helper.setStyleSheet("font-size: 20px; color: #486581;")
        header.addWidget(helper)
        header.addStretch()
        btn_add = QPushButton("Agregar producto")
        btn_add.setStyleSheet(
            "QPushButton { background: #0EA5A4; color: white; border: 3px solid #0F766E; }"
            "QPushButton:hover { background: #0F766E; }"
        )
        btn_add.clicked.connect(self._add_product_row)
        header.addWidget(btn_add)
        layout.addLayout(header)

        self.products_container = QVBoxLayout()
        self.products_container.setSpacing(10)
        layout.addLayout(self.products_container)
        return group

    def _build_expenses_group(self):
        group = QGroupBox("Gastos de Lunas")
        layout = QVBoxLayout(group)
        layout.setSpacing(14)

        header = QHBoxLayout()
        helper = QLabel("Registra nombre del gasto, donde se compro y precio.")
        helper.setStyleSheet("font-size: 20px; color: #486581;")
        header.addWidget(helper)
        header.addStretch()
        btn_add = QPushButton("Agregar gasto")
        btn_add.setStyleSheet(
            "QPushButton { background: #8B5CF6; color: white; border: 3px solid #6D28D9; }"
            "QPushButton:hover { background: #6D28D9; }"
        )
        btn_add.clicked.connect(self._add_expense_row)
        header.addWidget(btn_add)
        layout.addLayout(header)

        self.expenses_container = QVBoxLayout()
        self.expenses_container.setSpacing(10)
        layout.addLayout(self.expenses_container)
        return group

    def _build_observation_group(self):
        group = QGroupBox("Observaciones")
        layout = QVBoxLayout(group)
        self.text_observacion = QTextEdit()
        self.text_observacion.setMinimumHeight(150)
        layout.addWidget(self.text_observacion)
        return group

    def _build_footer_actions(self):
        layout = QHBoxLayout()
        layout.setSpacing(14)

        self.lbl_total = QLabel("Total venta: S/ 0.00 | Gastos: S/ 0.00")
        self.lbl_total.setStyleSheet(
            "font-size: 24px; font-weight: 800; color: #0F172A; "
            "background: #E8F1FF; border: 2px solid #BFD3FF; border-radius: 16px; padding: 14px 18px;"
        )
        layout.addWidget(self.lbl_total, 2)

        layout.addStretch()

        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.setStyleSheet(
            "QPushButton { background: #F59E0B; color: #1F2937; border: 3px solid #D97706; }"
            "QPushButton:hover { background: #D97706; color: white; }"
        )
        self.btn_clear.clicked.connect(self._reset_form)
        layout.addWidget(self.btn_clear)

        self.btn_save = QPushButton("Guardar graduacion")
        self.btn_save.setStyleSheet(
            "QPushButton { background: #1F9D55; color: white; border: 3px solid #157347; "
            "padding: 12px 20px; border-radius: 14px; font-weight: 800; }"
            "QPushButton:hover { background: #15803D; }"
        )
        self.btn_save.clicked.connect(self._save_basic_graduation)
        layout.addWidget(self.btn_save)
        return layout

    def _set_save_buttons_busy(self, busy):
        for button, normal_text, busy_text in (
            (getattr(self, "btn_save_top", None), "GUARDAR GRADUACION", "Guardando"),
            (getattr(self, "btn_save", None), "Guardar graduacion", "Guardando"),
            (getattr(self, "btn_clear_top", None), "LIMPIAR TODO", "Espere"),
            (getattr(self, "btn_clear", None), "Limpiar", "Espere"),
        ):
            set_button_busy(button, busy, normal_text, busy_text)

        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass

    def _create_dynamic_row(self, placeholders, remove_callback):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_widget.setStyleSheet(
            "QWidget { background: #FFFDF8; border: 2px solid #D9E2EC; border-radius: 16px; }"
        )
        row_layout.setContentsMargins(12, 12, 12, 12)
        edits = []
        for placeholder in placeholders:
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            row_layout.addWidget(edit, 1)
            edits.append(edit)
        btn_remove = QPushButton("Quitar")
        btn_remove.setStyleSheet(
            "QPushButton { background: #EF4444; color: white; border: 3px solid #DC2626; }"
            "QPushButton:hover { background: #DC2626; }"
        )
        btn_remove.clicked.connect(lambda: remove_callback(row_widget))
        row_layout.addWidget(btn_remove)
        return row_widget, edits

    def _add_product_row(self, data=None):
        row_widget, edits = self._create_dynamic_row(
            ["Nombre del producto", "Precio"],
            self._remove_product_row,
        )
        if isinstance(data, dict):
            edits[0].setText(str(data.get("nombre", "")))
            edits[1].setText(str(data.get("precio", "")))
        edits[0].textChanged.connect(self._update_totals_preview)
        edits[1].textChanged.connect(self._update_totals_preview)
        self.products_container.addWidget(row_widget)
        self._product_rows.append({"widget": row_widget, "nombre": edits[0], "precio": edits[1]})

    def _remove_product_row(self, row_widget):
        self._product_rows = [row for row in self._product_rows if row.get("widget") is not row_widget]
        row_widget.deleteLater()
        self._update_totals_preview()

    def _add_expense_row(self, data=None):
        row_widget, edits = self._create_dynamic_row(
            ["Nombre del gasto", "Donde se compro (opcional)", "Precio"],
            self._remove_expense_row,
        )
        if isinstance(data, dict):
            edits[0].setText(str(data.get("nombre", "")))
            edits[1].setText(str(data.get("proveedor", "")))
            edits[2].setText(str(data.get("precio", "")))
        edits[0].textChanged.connect(self._update_totals_preview)
        edits[1].textChanged.connect(self._update_totals_preview)
        edits[2].textChanged.connect(self._update_totals_preview)
        self.expenses_container.addWidget(row_widget)
        self._expense_rows.append(
            {"widget": row_widget, "nombre": edits[0], "proveedor": edits[1], "precio": edits[2]}
        )

    def _remove_expense_row(self, row_widget):
        self._expense_rows = [row for row in self._expense_rows if row.get("widget") is not row_widget]
        row_widget.deleteLater()
        self._update_totals_preview()

    @staticmethod
    def _money_to_float(value):
        try:
            return float(str(value or "0").strip().replace("S/.", "").replace("S/", "").replace(",", ""))
        except (TypeError, ValueError):
            return 0.0

    def _compute_next_contract_sequence(self):
        highest = 0
        pacientes = cargar_pacientes(self.username) or []
        for paciente in pacientes if isinstance(pacientes, list) else []:
            if not isinstance(paciente, dict):
                continue
            for grad in paciente.get("historial_graduaciones", []) or []:
                if not isinstance(grad, dict):
                    continue
                highest = max(highest, self._extract_contract_sequence(grad.get("contrato_numero", "")))

        ventas = cargar_ventas(self.username) or []
        for venta in ventas if isinstance(ventas, list) else []:
            if not isinstance(venta, dict):
                continue
            highest = max(highest, self._extract_contract_sequence(venta.get("contrato_numero", "")))
        return highest + 1 if highest > 0 else 1

    @staticmethod
    def _extract_contract_sequence(value):
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        try:
            return int(digits or 0)
        except (TypeError, ValueError):
            return 0

    def _format_contract_sequence(self, value):
        try:
            return f"{max(1, int(value or 1)):07d}"
        except (TypeError, ValueError):
            return "0000001"

    def _refresh_contract_number(self):
        self.entry_contrato.setText(self._format_contract_sequence(self._compute_next_contract_sequence()))

    def _collect_products(self):
        items = []
        for row in self._product_rows:
            nombre = str(row["nombre"].text() or "").strip()
            precio = self._money_to_float(row["precio"].text())
            if not nombre and precio <= 0:
                continue
            if not nombre:
                raise ValueError("Cada producto debe tener nombre.")
            if precio <= 0:
                raise ValueError(f"El producto '{nombre}' debe tener un precio válido.")
            items.append(
                {
                    "producto": nombre,
                    "nombre": nombre,
                    "cantidad": 1,
                    "precio_unitario": round(precio, 2),
                    "precio": round(precio, 2),
                    "subtotal": round(precio, 2),
                    "total": round(precio, 2),
                }
            )
        return items

    def _collect_expenses(self):
        gastos = []
        for row in self._expense_rows:
            nombre = str(row["nombre"].text() or "").strip()
            proveedor = str(row["proveedor"].text() or "").strip()
            precio = self._money_to_float(row["precio"].text())
            if not nombre and not proveedor and precio <= 0:
                continue
            if not nombre:
                raise ValueError("Cada gasto debe tener nombre.")
            if precio <= 0:
                raise ValueError(f"El gasto '{nombre}' debe tener un precio válido.")
            gastos.append(
                {
                    "nombre": nombre,
                    "proveedor": proveedor,
                    "precio": round(precio, 2),
                }
            )
        return gastos

    def _build_rx_block(self, prefix):
        od = {
            "esferico": self._rx_fields[(prefix, "OD", "esferico")].text().strip(),
            "cilindro": self._rx_fields[(prefix, "OD", "cilindro")].text().strip(),
            "eje": self._rx_fields[(prefix, "OD", "eje")].text().strip(),
            "av": self._rx_fields[(prefix, "OD", "av")].text().strip(),
            "adicmedia": self._rx_fields[(prefix, "OD", "adicmedia")].text().strip(),
            "prisma": self._rx_fields[(prefix, "OD", "prisma")].text().strip(),
            "distp": self._rx_fields[(prefix, "OD", "distp")].text().strip(),
        }
        oi = {
            "esferico": self._rx_fields[(prefix, "OI", "esferico")].text().strip(),
            "cilindro": self._rx_fields[(prefix, "OI", "cilindro")].text().strip(),
            "eje": self._rx_fields[(prefix, "OI", "eje")].text().strip(),
            "av": self._rx_fields[(prefix, "OI", "av")].text().strip(),
            "adicmedia": self._rx_fields[(prefix, "OI", "adicmedia")].text().strip(),
            "prisma": self._rx_fields[(prefix, "OI", "prisma")].text().strip(),
            "distp": self._rx_fields[(prefix, "OI", "distp")].text().strip(),
        }
        distp = od.get("distp") or oi.get("distp") or ""
        return od, oi, distp

    def _find_existing_patient(self, pacientes, dni, nombre):
        nombre_cmp = str(nombre or "").strip().lower()
        if dni != "00000000":
            for paciente in pacientes:
                if isinstance(paciente, dict) and str(paciente.get("dni", "")).strip() == dni:
                    return paciente
        for paciente in pacientes:
            if not isinstance(paciente, dict):
                continue
            if str(paciente.get("dni", "")).strip() == "00000000" and str(paciente.get("nombre", "")).strip().lower() == nombre_cmp:
                return paciente
        return None

    def _build_sale_payload(self, dni, nombre, fecha, contrato_numero, service_name, service_cost, product_items, total_venta):
        ventas = cargar_ventas(self.username) or []
        max_id = 0
        for venta in ventas if isinstance(ventas, list) else []:
            try:
                max_id = max(max_id, int(venta.get("id", 0) or 0))
            except (TypeError, ValueError):
                continue

        items = []
        if service_cost > 0:
            items.append(
                {
                    "producto": service_name,
                    "nombre": service_name,
                    "descripcion": "Servicio de Graduacion",
                    "cantidad": 1,
                    "precio_unitario": round(service_cost, 2),
                    "precio": round(service_cost, 2),
                    "subtotal": round(service_cost, 2),
                    "total": round(service_cost, 2),
                }
            )
        items.extend(product_items)

        subtotal = round(total_venta / 1.18, 2) if total_venta > 0 else 0.0
        igv = round(total_venta - subtotal, 2)
        return {
            "id": max_id + 1,
            "fecha": f"{fecha} {datetime.datetime.now().strftime('%H:%M:%S')}",
            "paciente_dni": dni,
            "paciente_nombre": nombre,
            "usuario": self.username,
            "numero_orden": "",
            "contrato_numero": contrato_numero,
            "tipo_venta": "graduacion",
            "origen": "graduacion",
            "items": items,
            "subtotal": subtotal,
            "igv": igv,
            "total": round(total_venta, 2),
            "monto_total_venta": round(total_venta, 2),
            "metodo_pago": "Efectivo",
            "metodos_pago_detalle": [{"metodo": "Efectivo", "monto": round(total_venta, 2)}],
            "pago_mixto": False,
            "es_pago_partes": False,
            "es_pago_parcial": False,
            "monto_adelanto": round(total_venta, 2),
            "monto_faltante": 0.0,
            "monto_pagado": round(total_venta, 2),
            "helper_name": getattr(self.parent_app, "helper_name", None) if getattr(self.parent_app, "is_helper", False) else None,
            "vendedor": getattr(self.parent_app, "helper_name", "") or self.username,
            "luna_tipo": "",
            "luna_costo": "",
        }

    def _save_basic_graduation(self):
        if self._saving:
            return
        self._saving = True
        self._set_save_buttons_busy(True)
        try:
            dni = "".join(ch for ch in str(self.entry_dni.text() or "").strip() if ch.isdigit())
            nombre = str(self.entry_nombre.text() or "").strip()
            contrato_numero = "".join(ch for ch in str(self.entry_contrato.text() or "").strip() if ch.isdigit())
            fecha = str(self.entry_fecha.text() or "").strip()
            service_name = str(self.entry_service_name.text() or "Servicio de Graduacion").strip() or "Servicio de Graduacion"
            service_cost = self._money_to_float(self.entry_service_cost.text())

            if not dni:
                raise ValueError("El DNI es obligatorio. Puedes usar 00000000.")
            if len(dni) != 8:
                raise ValueError("El DNI debe tener 8 digitos.")
            if not nombre:
                raise ValueError("El nombre del paciente es obligatorio.")
            if not contrato_numero:
                raise ValueError("El contrato es obligatorio.")
            if service_cost < 0:
                raise ValueError("El costo del servicio no puede ser negativo.")
            try:
                datetime.datetime.strptime(fecha, "%d/%m/%Y")
            except ValueError:
                raise ValueError("La fecha debe tener formato DD/MM/AAAA.")

            normalized_contract = self._format_contract_sequence(contrato_numero)
            contract_sequence = self._extract_contract_sequence(normalized_contract)
            pacientes = cargar_pacientes(self.username) or []
            ventas = cargar_ventas(self.username) or []
            if not isinstance(pacientes, list):
                pacientes = []
            if not isinstance(ventas, list):
                ventas = []

            for paciente_item in pacientes:
                if not isinstance(paciente_item, dict):
                    continue
                for grad in paciente_item.get("historial_graduaciones", []) or []:
                    if (
                        isinstance(grad, dict)
                        and self._extract_contract_sequence(grad.get("contrato_numero", "")) == contract_sequence
                    ):
                        raise ValueError(f"El contrato {normalized_contract} ya existe.")
            for venta in ventas:
                if (
                    isinstance(venta, dict)
                    and self._extract_contract_sequence(venta.get("contrato_numero", "")) == contract_sequence
                ):
                    raise ValueError(f"El contrato {normalized_contract} ya existe.")

            products = self._collect_products()
            expenses = self._collect_expenses()
            total_products = round(sum(float(item.get("total", 0) or 0) for item in products), 2)
            total_expenses = round(sum(float(item.get("precio", 0) or 0) for item in expenses), 2)
            total_venta = round(service_cost + total_products, 2)

            lejos_od, lejos_oi, lejos_distp = self._build_rx_block("lejos")
            cerca_od, cerca_oi, cerca_distp = self._build_rx_block("cerca")

            graduacion_data = {
                "contrato_numero": normalized_contract,
                "fecha": fecha,
                "proxima_cita": None,
                "optometra": "",
                "monto_cobrado": f"{service_cost:.2f}",
                "servicio_graduacion": {
                    "nombre": service_name,
                    "precio": round(service_cost, 2),
                },
                "metodo_pago": "Efectivo" if total_venta > 0 else "",
                "metodos_pago_detalle": [{"metodo": "Efectivo", "monto": round(total_venta, 2)}] if total_venta > 0 else [],
                "pago_mixto": False,
                "lejos_od": lejos_od,
                "lejos_oi": lejos_oi,
                "lejos_distp": lejos_distp,
                "cerca_od": cerca_od,
                "cerca_oi": cerca_oi,
                "cerca_distp": cerca_distp,
                "observacion": str(self.text_observacion.toPlainText() or "").strip(),
                "motilidad_versiones": {},
                "items_venta": products,
                "gastos_laboratorio": expenses,
                "total_gastos_laboratorio": total_expenses,
                "monto_total_venta": total_venta,
                "deuda_id": "",
                "es_pago_parcial": False,
                "monto_adelanto": total_venta,
                "pagos_parciales": [],
                "registrado_por": getattr(self.parent_app, "helper_name", "") or self.username,
                "comision_activada": False,
                "comision_porcentaje": 0.0,
                "comision_monto": 0.0,
                "comision_usuario": "",
                "venta_relacionada_id": None,
                "cristales": "",
                "resina": "",
                "color": "",
                "bifocal_tipo": "",
                "multifocal_tipo": "",
                "altura": "",
                "luna_tipo": "",
                "luna_costo": "",
            }

            paciente = self._find_existing_patient(pacientes, dni, nombre)
            if paciente is None:
                paciente = {
                    "uuid": str(uuid.uuid4()),
                    "dni": dni,
                    "nombre": nombre,
                    "fecha": fecha,
                    "telefono": "",
                    "direccion": "",
                    "historial_graduaciones": [],
                }
                pacientes.append(paciente)
            else:
                paciente["dni"] = dni
                paciente["nombre"] = nombre
                paciente.setdefault("historial_graduaciones", [])

            paciente["historial_graduaciones"].append(graduacion_data)

            sale_payload = self._build_sale_payload(
                dni=dni,
                nombre=nombre,
                fecha=fecha,
                contrato_numero=graduacion_data["contrato_numero"],
                service_name=service_name,
                service_cost=service_cost,
                product_items=products,
                total_venta=total_venta,
            )

            ventas.append(sale_payload)
            graduacion_data["venta_relacionada_id"] = sale_payload["id"]

            guardar_pacientes(self.username, pacientes)
            guardar_graduaciones(self.username, self._build_graduaciones_payload(pacientes))
            guardar_ventas(self.username, ventas)

            QMessageBox.information(
                self,
                "Graduacion",
                f"Graduacion guardada.\n\nContrato: {graduacion_data['contrato_numero']}\nTotal venta: S/ {total_venta:.2f}",
            )
            self._reset_form()
        except Exception as exc:
            QMessageBox.critical(self, "Graduacion", str(exc))
        finally:
            self._set_save_buttons_busy(False)
            self._saving = False

    def _build_graduaciones_payload(self, pacientes):
        graduaciones = []
        for paciente in pacientes if isinstance(pacientes, list) else []:
            if not isinstance(paciente, dict):
                continue
            historial = paciente.get("historial_graduaciones", []) or []
            for grad in historial:
                if not isinstance(grad, dict):
                    continue
                monto_total = str(grad.get("monto_cobrado", "0"))
                monto_pagado = str(grad.get("monto_adelanto", monto_total))
                graduaciones.append(
                    {
                        "fecha": grad.get("fecha", ""),
                        "paciente": paciente.get("nombre", "N/A"),
                        "dni": paciente.get("dni", ""),
                        "optica_medico": grad.get("optometra", "N/A"),
                        "tipo": grad.get("tipo", "Graduacion"),
                        "informacion": grad.get("prescripcion", grad.get("informacion", "")),
                        "precio": monto_total,
                        "pago": monto_pagado,
                        "id_paciente": paciente.get("id", ""),
                    }
                )
        return graduaciones

    def _update_totals_preview(self):
        service_cost = self._money_to_float(self.entry_service_cost.text())
        product_total = sum(self._money_to_float(row["precio"].text()) for row in self._product_rows)
        expense_total = sum(self._money_to_float(row["precio"].text()) for row in self._expense_rows)
        self.lbl_total.setText(
            f"Total venta: S/ {service_cost + product_total:.2f} | Gastos: S/ {expense_total:.2f}"
        )

    def _reset_form(self):
        self.entry_fecha.setText(datetime.date.today().strftime("%d/%m/%Y"))
        self.entry_dni.setText("00000000")
        self.entry_nombre.clear()
        self.entry_service_name.setText("Servicio de Graduacion")
        self.entry_service_cost.clear()
        self.text_observacion.clear()
        self._refresh_contract_number()

        for row in list(self._product_rows):
            row["widget"].deleteLater()
        self._product_rows = []
        for row in list(self._expense_rows):
            row["widget"].deleteLater()
        self._expense_rows = []

        for field in self._rx_fields.values():
            field.clear()

        self._add_product_row()
        self._add_expense_row()
        self._update_totals_preview()
