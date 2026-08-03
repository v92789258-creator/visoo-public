import datetime

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QCheckBox,
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
from utils.file_handler import cargar_metodos_pago, cargar_ventas, guardar_ventas


class BasicSalesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = getattr(parent, "username", None)
        self._product_rows = []
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
            QCheckBox {
                font-size: 20px;
                font-weight: 700;
                color: #243B53;
                spacing: 10px;
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

        title = QLabel("Nueva Venta - Modo Basico")
        title.setStyleSheet("font-size: 40px; font-weight: 800; color: #0B1F33;")
        layout.addWidget(title)

        subtitle = QLabel("Registro simple para vender escribiendo producto, cantidad y precio.")
        subtitle.setStyleSheet("font-size: 22px; color: #486581;")
        layout.addWidget(subtitle)

        layout.addLayout(self._build_top_actions())
        layout.addWidget(self._build_basic_info_group())
        layout.addWidget(self._build_payment_group())
        layout.addWidget(self._build_products_group())
        layout.addWidget(self._build_observation_group())
        layout.addLayout(self._build_footer_actions())
        layout.addStretch()

    def _build_top_actions(self):
        layout = QHBoxLayout()
        layout.setSpacing(14)

        self.btn_save_top = QPushButton("GUARDAR VENTA")
        self.btn_save_top.setStyleSheet(
            "QPushButton { background: #1F9D55; color: white; border: 3px solid #157347; }"
            "QPushButton:hover { background: #157347; }"
        )
        self.btn_save_top.clicked.connect(self._save_basic_sale)
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
        group = QGroupBox("Cliente y Venta")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.entry_fecha = QLineEdit()
        self.entry_dni = QLineEdit()
        self.entry_dni.setPlaceholderText("00000000")
        self.entry_nombre = QLineEdit()
        self.entry_nombre.setPlaceholderText("Nombre del cliente")
        self.entry_orden = QLineEdit()
        self.entry_vendedor = QLineEdit()

        btn_refresh_order = QPushButton("Nuevo orden")
        btn_refresh_order.setStyleSheet(
            "QPushButton { background: #2F80ED; color: white; border: 3px solid #1C64D1; }"
            "QPushButton:hover { background: #1C64D1; }"
        )
        btn_refresh_order.clicked.connect(self._refresh_order_number)

        grid.addWidget(QLabel("Fecha"), 0, 0)
        grid.addWidget(self.entry_fecha, 0, 1)
        grid.addWidget(QLabel("DNI"), 0, 2)
        grid.addWidget(self.entry_dni, 0, 3)
        grid.addWidget(QLabel("Nombre"), 1, 0)
        grid.addWidget(self.entry_nombre, 1, 1, 1, 3)
        grid.addWidget(QLabel("N° Orden"), 2, 0)
        grid.addWidget(self.entry_orden, 2, 1, 1, 2)
        grid.addWidget(btn_refresh_order, 2, 3)
        grid.addWidget(QLabel("Vendedor"), 3, 0)
        grid.addWidget(self.entry_vendedor, 3, 1, 1, 3)
        return group

    def _build_payment_group(self):
        group = QGroupBox("Pago")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.entry_metodo_pago = QLineEdit()
        self.checkbox_pago_partes = QCheckBox("Pago en partes")
        self.checkbox_pago_partes.toggled.connect(self._toggle_partial_payment)
        self.entry_monto_pagado = QLineEdit()
        self.entry_monto_pagado.setPlaceholderText("0.00")
        self.entry_monto_pagado.textChanged.connect(self._update_totals_preview)
        self.entry_descuento = QLineEdit()
        self.entry_descuento.setPlaceholderText("0")
        self.entry_descuento.textChanged.connect(self._update_totals_preview)

        grid.addWidget(QLabel("Metodo de pago"), 0, 0)
        grid.addWidget(self.entry_metodo_pago, 0, 1, 1, 3)
        grid.addWidget(self.checkbox_pago_partes, 1, 0, 1, 2)
        grid.addWidget(QLabel("Descuento %"), 1, 2)
        grid.addWidget(self.entry_descuento, 1, 3)
        grid.addWidget(QLabel("Monto pagado"), 2, 0)
        grid.addWidget(self.entry_monto_pagado, 2, 1, 1, 3)
        return group

    def _build_products_group(self):
        group = QGroupBox("Productos")
        layout = QVBoxLayout(group)
        layout.setSpacing(14)

        header = QHBoxLayout()
        helper = QLabel("Agrega uno o mas productos con cantidad y precio.")
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

        btn_inventory = QPushButton("Buscar en inventario")
        btn_inventory.setStyleSheet(
            "QPushButton { background: #2563EB; color: white; border: 3px solid #1D4ED8; }"
            "QPushButton:hover { background: #1D4ED8; }"
        )
        btn_inventory.clicked.connect(self._open_inventory_selector)
        header.addWidget(btn_inventory)
        layout.addLayout(header)

        self.products_container = QVBoxLayout()
        self.products_container.setSpacing(10)
        layout.addLayout(self.products_container)
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

        self.lbl_total = QLabel("Total venta: S/ 0.00 | Pagado: S/ 0.00 | Debe: S/ 0.00")
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

        self.btn_save = QPushButton("Guardar venta")
        self.btn_save.setStyleSheet(
            "QPushButton { background: #1F9D55; color: white; border: 3px solid #157347; "
            "padding: 12px 20px; border-radius: 14px; font-weight: 800; }"
            "QPushButton:hover { background: #15803D; }"
        )
        self.btn_save.clicked.connect(self._save_basic_sale)
        layout.addWidget(self.btn_save)
        return layout

    def _set_save_buttons_busy(self, busy):
        for button, normal_text, busy_text in (
            (getattr(self, "btn_save_top", None), "GUARDAR VENTA", "Guardando"),
            (getattr(self, "btn_save", None), "Guardar venta", "Guardando"),
            (getattr(self, "btn_clear_top", None), "LIMPIAR TODO", "Espere"),
            (getattr(self, "btn_clear", None), "Limpiar", "Espere"),
        ):
            set_button_busy(button, busy, normal_text, busy_text)

        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass

    def update_metodo_pago_combo(self):
        metodos = cargar_metodos_pago(self.username) or []
        if self.entry_metodo_pago.text().strip():
            return
        self.entry_metodo_pago.setText(str(metodos[0] if metodos else "Efectivo"))

    def update_sales_page(self):
        self.update_metodo_pago_combo()
        self._update_totals_preview()

    def _create_dynamic_row(self):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(12, 12, 12, 12)
        row_layout.setSpacing(8)
        row_widget.setStyleSheet(
            "QWidget { background: #FFFDF8; border: 2px solid #D9E2EC; border-radius: 16px; }"
        )

        entry_name = QLineEdit()
        entry_name.setPlaceholderText("Nombre del producto")
        entry_qty = QLineEdit()
        entry_qty.setPlaceholderText("Cantidad")
        entry_price = QLineEdit()
        entry_price.setPlaceholderText("Precio")

        for edit in (entry_name, entry_qty, entry_price):
            edit.textChanged.connect(self._update_totals_preview)

        row_layout.addWidget(entry_name, 3)
        row_layout.addWidget(entry_qty, 1)
        row_layout.addWidget(entry_price, 1)

        btn_remove = QPushButton("Quitar")
        btn_remove.setStyleSheet(
            "QPushButton { background: #EF4444; color: white; border: 3px solid #DC2626; }"
            "QPushButton:hover { background: #DC2626; }"
        )
        btn_remove.clicked.connect(lambda: self._remove_product_row(row_widget))
        row_layout.addWidget(btn_remove)
        return row_widget, entry_name, entry_qty, entry_price

    def _add_product_row(self, data=None):
        row_widget, entry_name, entry_qty, entry_price = self._create_dynamic_row()
        if isinstance(data, dict):
            code = str(data.get("codigo", "") or "").strip()
            name = str(data.get("producto", data.get("nombre", "")) or "").strip()
            entry_name.setText(f"{code} - {name}" if code and code not in name else name)
            entry_qty.setText(str(data.get("cantidad", "1")))
            entry_price.setText(str(data.get("precio_unitario", data.get("precio", ""))))
        self.products_container.addWidget(row_widget)
        self._product_rows.append(
            {
                "widget": row_widget,
                "nombre": entry_name,
                "cantidad": entry_qty,
                "precio": entry_price,
                "codigo": str(data.get("codigo", "") or "").strip() if isinstance(data, dict) else "",
                "stock_disponible": (
                    self._qty_to_float(data.get("stock_disponible"))
                    if isinstance(data, dict) and "stock_disponible" in data
                    else None
                ),
            }
        )

    def _open_inventory_selector(self):
        try:
            from gui.dialogs.selection_products_v2 import SeleccionarProductosDialogV2

            dialog = SeleccionarProductosDialogV2(self, username=self.username)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            selected = dialog.selected_products if isinstance(dialog.selected_products, list) else []
            for product in selected:
                if isinstance(product, dict):
                    self._add_product_row(product)
            if selected:
                self._update_totals_preview()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Inventario",
                f"No se pudo abrir el inventario. Puedes escribir el producto manualmente.\n\n{exc}",
            )

    def _remove_product_row(self, row_widget):
        self._product_rows = [row for row in self._product_rows if row.get("widget") is not row_widget]
        row_widget.deleteLater()
        self._update_totals_preview()

    @staticmethod
    def _money_to_float(value):
        try:
            return float(str(value or "0").strip().replace("S/.", "").replace("S/", "").replace(",", ""))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _qty_to_float(value):
        try:
            qty = float(str(value or "0").strip().replace(",", ""))
            return qty if qty > 0 else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _extract_order_sequence(value):
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        try:
            return int(digits or 0)
        except (TypeError, ValueError):
            return 0

    def _format_order_number(self, value):
        sequence = self._extract_order_sequence(value)
        if sequence <= 0:
            return "0001"
        digits = str(sequence)
        return digits.zfill(4) if len(digits) < 4 else digits

    def _compute_next_order_sequence(self, ventas=None):
        ventas = ventas if isinstance(ventas, list) else (cargar_ventas(self.username) or [])
        max_order = 0
        for venta in ventas:
            if not isinstance(venta, dict):
                continue
            max_order = max(max_order, self._extract_order_sequence(venta.get("numero_orden", "")))
        return max_order + 1 if max_order > 0 else 1

    def _refresh_order_number(self):
        self.entry_orden.setText(self._format_order_number(self._compute_next_order_sequence()))

    def _toggle_partial_payment(self, checked):
        self.entry_monto_pagado.setEnabled(bool(checked))
        if not checked:
            self.entry_monto_pagado.clear()
        self._update_totals_preview()

    def _collect_items(self):
        items = []
        for row in self._product_rows:
            nombre = str(row["nombre"].text() or "").strip()
            cantidad = self._qty_to_float(row["cantidad"].text())
            precio = self._money_to_float(row["precio"].text())
            if not nombre and cantidad <= 0 and precio <= 0:
                continue
            if not nombre:
                raise ValueError("Cada producto debe tener nombre.")
            if cantidad <= 0:
                raise ValueError(f"El producto '{nombre}' debe tener cantidad válida.")
            if precio <= 0:
                raise ValueError(f"El producto '{nombre}' debe tener precio válido.")
            stock_available = row.get("stock_disponible")
            if stock_available is not None and cantidad > stock_available:
                raise ValueError(
                    f"Stock insuficiente para '{nombre}'. Disponible: {stock_available:g}."
                )
            subtotal = round(cantidad * precio, 2)
            item = {
                "producto": nombre,
                "nombre": nombre,
                "cantidad": cantidad,
                "precio_unitario": round(precio, 2),
                "precio": round(precio, 2),
                "subtotal": subtotal,
                "total": subtotal,
            }
            if row.get("codigo"):
                item["codigo"] = row["codigo"]
            items.append(item)
        return items

    def _build_sale_payload(
        self,
        dni,
        nombre,
        fecha,
        numero_orden,
        metodo_pago,
        vendedor,
        items,
        total_venta,
        monto_pagado,
        descuento_percent,
        descuento_total,
    ):
        ventas = cargar_ventas(self.username) or []
        max_id = 0
        for venta in ventas if isinstance(ventas, list) else []:
            try:
                max_id = max(max_id, int(venta.get("id", 0) or 0))
            except (TypeError, ValueError):
                continue

        subtotal = round(total_venta / 1.18, 2) if total_venta > 0 else 0.0
        igv = round(total_venta - subtotal, 2)
        monto_pagado = round(min(max(monto_pagado, 0.0), total_venta), 2)
        monto_faltante = round(max(total_venta - monto_pagado, 0.0), 2)
        es_parcial = monto_faltante > 0.05

        return {
            "id": max_id + 1,
            "fecha": f"{fecha} {datetime.datetime.now().strftime('%H:%M:%S')}",
            "paciente_dni": dni,
            "paciente_nombre": nombre,
            "usuario": self.username,
            "numero_orden": self._format_order_number(numero_orden),
            "items": items,
            "subtotal": subtotal,
            "igv": igv,
            "total": round(total_venta, 2),
            "descuento_percent": round(descuento_percent, 2),
            "descuento_total": round(descuento_total, 2),
            "metodo_pago": str(metodo_pago or "Efectivo").strip().lower(),
            "metodos_pago_detalle": [{"metodo": str(metodo_pago or "Efectivo").strip(), "monto": monto_pagado}],
            "pago_mixto": False,
            "es_pago_partes": es_parcial,
            "es_pago_parcial": es_parcial,
            "monto_adelanto": monto_pagado if es_parcial else 0.0,
            "monto_faltante": monto_faltante,
            "monto_pagado": monto_pagado,
            "helper_name": getattr(self.parent_app, "helper_name", None) if getattr(self.parent_app, "is_helper", False) else None,
            "vendedor": vendedor,
            "tipo_venta": "directa",
            "origen": "modo_basico",
            "observaciones": str(self.text_observacion.toPlainText() or "").strip(),
        }

    def _save_basic_sale(self):
        if self._saving:
            return
        self._saving = True
        self._set_save_buttons_busy(True)
        try:
            dni = "".join(ch for ch in str(self.entry_dni.text() or "").strip() if ch.isdigit())
            nombre = str(self.entry_nombre.text() or "").strip()
            fecha = str(self.entry_fecha.text() or "").strip()
            numero_orden = "".join(ch for ch in str(self.entry_orden.text() or "").strip() if ch.isdigit())
            metodo_pago = str(self.entry_metodo_pago.text() or "").strip()
            vendedor = str(self.entry_vendedor.text() or "").strip()

            if not dni:
                raise ValueError("El DNI es obligatorio. Puedes usar 00000000.")
            if len(dni) != 8:
                raise ValueError("El DNI debe tener 8 digitos.")
            if not nombre and dni != "00000000":
                raise ValueError("El nombre del cliente es obligatorio.")
            if not numero_orden:
                raise ValueError("El número de orden es obligatorio.")
            if not metodo_pago:
                raise ValueError("El metodo de pago es obligatorio.")
            try:
                datetime.datetime.strptime(fecha, "%d/%m/%Y")
            except ValueError:
                raise ValueError("La fecha debe tener formato DD/MM/AAAA.")

            items = self._collect_items()
            if not items:
                raise ValueError("Debes agregar al menos un producto.")

            gross_total = round(sum(float(item.get("total", 0) or 0) for item in items), 2)
            descuento_percent = self._money_to_float(self.entry_descuento.text())
            if descuento_percent < 0 or descuento_percent > 100:
                raise ValueError("El descuento debe estar entre 0 y 100.")
            descuento_total = round(gross_total * descuento_percent / 100.0, 2)
            total_venta = round(max(gross_total - descuento_total, 0.0), 2)
            if total_venta <= 0:
                raise ValueError("El total de la venta debe ser mayor a 0.")
            monto_pagado = total_venta
            if self.checkbox_pago_partes.isChecked():
                monto_pagado = self._money_to_float(self.entry_monto_pagado.text())
                if monto_pagado <= 0:
                    raise ValueError("El monto pagado debe ser mayor a 0.")

            if dni == "00000000" and not nombre:
                nombre = "Cliente Genérico"
            elif not nombre:
                nombre = f"Cliente {dni}"

            formatted_order = self._format_order_number(numero_orden)
            ventas = cargar_ventas(self.username) or []
            if not isinstance(ventas, list):
                ventas = []
            if any(
                isinstance(venta, dict)
                and str(venta.get("numero_orden", "") or "").strip()
                and self._format_order_number(venta.get("numero_orden", "")) == formatted_order
                for venta in ventas
            ):
                raise ValueError(f"El numero de orden {formatted_order} ya existe.")

            sale_payload = self._build_sale_payload(
                dni=dni,
                nombre=nombre,
                fecha=fecha,
                numero_orden=numero_orden,
                metodo_pago=metodo_pago,
                vendedor=vendedor or (getattr(self.parent_app, "helper_name", "") or self.username),
                items=items,
                total_venta=total_venta,
                monto_pagado=monto_pagado,
                descuento_percent=descuento_percent,
                descuento_total=descuento_total,
            )

            ventas.append(sale_payload)
            guardar_ventas(self.username, ventas)

            QMessageBox.information(
                self,
                "Venta",
                f"Venta guardada.\n\nN° Orden: {sale_payload['numero_orden']}\nTotal venta: S/ {total_venta:.2f}",
            )
            self._reset_form()
        except Exception as exc:
            QMessageBox.critical(self, "Venta", str(exc))
        finally:
            self._set_save_buttons_busy(False)
            self._saving = False

    def _update_totals_preview(self):
        gross_total = 0.0
        for row in self._product_rows:
            gross_total += self._qty_to_float(row["cantidad"].text()) * self._money_to_float(row["precio"].text())
        gross_total = round(gross_total, 2)
        discount_percent = min(max(self._money_to_float(self.entry_descuento.text()), 0.0), 100.0)
        total = round(max(gross_total - (gross_total * discount_percent / 100.0), 0.0), 2)

        pagado = total
        if self.checkbox_pago_partes.isChecked():
            pagado = round(min(max(self._money_to_float(self.entry_monto_pagado.text()), 0.0), total), 2)
        debe = round(max(total - pagado, 0.0), 2)
        self.lbl_total.setText(f"Total venta: S/ {total:.2f} | Pagado: S/ {pagado:.2f} | Debe: S/ {debe:.2f}")

    def _reset_form(self):
        self.entry_fecha.setText(datetime.datetime.now().strftime("%d/%m/%Y"))
        self.entry_dni.setText("00000000")
        self.entry_nombre.clear()
        self.entry_vendedor.setText(getattr(self.parent_app, "helper_name", "") or self.username or "")
        self.update_metodo_pago_combo()
        self._refresh_order_number()
        self.checkbox_pago_partes.setChecked(False)
        self.entry_monto_pagado.clear()
        self.entry_descuento.setText("0")
        self.text_observacion.clear()

        for row in list(self._product_rows):
            widget = row.get("widget")
            if widget is not None:
                widget.deleteLater()
        self._product_rows = []
        self._add_product_row()
        self._update_totals_preview()
