from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class DeudaPaymentDialog(QDialog):
    """Diálogo para registrar pagos de deudas con detalles completos."""

    def __init__(self, deuda, parent=None):
        super().__init__(parent)
        self.deuda = deuda
        self.setWindowTitle(f"Pago de Deuda - {deuda.get('paciente_nombre', 'Cliente')}")
        self.setGeometry(100, 100, 500, 400)
        self.init_ui()

    def _to_float(self, value, default=0.0):
        try:
            if value in (None, ""):
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _escape_html(self, text):
        return (
            str(text or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _open_contract_link(self, contract_number):
        parent = self.parent()
        if parent is not None and hasattr(parent, "abrir_contrato_desde_deuda"):
            parent.abrir_contrato_desde_deuda(contract_number)
        self.reject()

    def init_ui(self):
        """Inicializa la interfaz del diálogo."""
        layout = QVBoxLayout()

        cliente_group = QGroupBox("Detalles del Cliente")
        cliente_layout = QGridLayout()

        cliente_layout.addWidget(QLabel("DNI:"), 0, 0)
        dni_label = QLabel(self.deuda.get("paciente_dni", "N/A"))
        dni_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        cliente_layout.addWidget(dni_label, 0, 1)

        cliente_layout.addWidget(QLabel("Nombre:"), 1, 0)
        nombre_label = QLabel(self.deuda.get("paciente_nombre", "N/A"))
        nombre_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        cliente_layout.addWidget(nombre_label, 1, 1)

        compra_texto = str(self.deuda.get("descripcion_compra", "") or self.deuda.get("descripcion", "") or "").strip()
        numero_orden = str(self.deuda.get("numero_orden", "") or "").strip()
        contrato_numero = str(self.deuda.get("contrato_numero", "") or "").strip()
        row_detalle = 2
        if compra_texto:
            cliente_layout.addWidget(QLabel("Compra:"), row_detalle, 0)
            compra_label = QLabel(compra_texto)
            compra_label.setWordWrap(True)
            compra_label.setStyleSheet("color: #374151; font-size: 12px;")
            cliente_layout.addWidget(compra_label, row_detalle, 1)
            row_detalle += 1

        if numero_orden:
            cliente_layout.addWidget(QLabel("N° Orden:"), row_detalle, 0)
            if contrato_numero:
                orden_label = QLabel(f'<a href="{self._escape_html(contrato_numero)}">{self._escape_html(numero_orden)}</a>')
                orden_label.setTextFormat(Qt.RichText)
                orden_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                orden_label.setOpenExternalLinks(False)
                orden_label.linkActivated.connect(self._open_contract_link)
            else:
                orden_label = QLabel(self._escape_html(numero_orden))
            orden_label.setStyleSheet("font-weight: bold; color: #1976D2; font-size: 12px;")
            cliente_layout.addWidget(orden_label, row_detalle, 1)
            row_detalle += 1

        if contrato_numero:
            cliente_layout.addWidget(QLabel("Contrato:"), row_detalle, 0)
            contrato_label = QLabel(f'<a href="{self._escape_html(contrato_numero)}">{self._escape_html(contrato_numero)}</a>')
            contrato_label.setTextFormat(Qt.RichText)
            contrato_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            contrato_label.setOpenExternalLinks(False)
            contrato_label.linkActivated.connect(self._open_contract_link)
            contrato_label.setStyleSheet("font-weight: bold; font-size: 12px;")
            cliente_layout.addWidget(contrato_label, row_detalle, 1)

        cliente_group.setLayout(cliente_layout)
        layout.addWidget(cliente_group)

        deuda_group = QGroupBox("Detalles de la Deuda")
        deuda_layout = QGridLayout()

        deuda_layout.addWidget(QLabel("Total a Pagar:"), 0, 0)
        total = self._to_float(self.deuda.get("total", 0), 0.0)
        total_label = QLabel(f"S/. {total:.2f}")
        total_label.setStyleSheet("font-weight: bold; color: #1976D2; font-size: 12px;")
        deuda_layout.addWidget(total_label, 0, 1)

        deuda_layout.addWidget(QLabel("Adelanto Pagado:"), 1, 0)
        adelanto = self._to_float(self.deuda.get("monto_adelanto", 0), 0.0)
        adelanto_label = QLabel(f"S/. {adelanto:.2f}")
        adelanto_label.setStyleSheet("color: #388E3C; font-size: 12px;")
        deuda_layout.addWidget(adelanto_label, 1, 1)

        deuda_layout.addWidget(QLabel("Falta Pagar:"), 2, 0)
        falta = self._to_float(self.deuda.get("monto_faltante", 0), 0.0)
        falta_label = QLabel(f"S/. {falta:.2f}")
        falta_label.setStyleSheet("color: #D32F2F; font-weight: bold; font-size: 12px;")
        deuda_layout.addWidget(falta_label, 2, 1)

        deuda_group.setLayout(deuda_layout)
        layout.addWidget(deuda_group)

        pago_group = QGroupBox("Registrar Pago")
        pago_layout = QGridLayout()

        pago_layout.addWidget(QLabel("¿Cuánto cancela?"), 0, 0)
        self.monto_pago = QLineEdit()
        self.monto_pago.setPlaceholderText(f"0.00 (máximo S/. {falta:.2f})")
        pago_layout.addWidget(self.monto_pago, 0, 1)

        pago_layout.addWidget(QLabel("Fecha del pago:"), 1, 0)
        self.fecha_pago_edit = QDateEdit()
        self.fecha_pago_edit.setCalendarPopup(True)
        self.fecha_pago_edit.setDisplayFormat("dd/MM/yyyy")
        self.fecha_pago_edit.setDate(QDate.currentDate())
        pago_layout.addWidget(self.fecha_pago_edit, 1, 1)

        pago_layout.addWidget(QLabel("Observaciones:"), 2, 0)
        self.observaciones = QLineEdit()
        self.observaciones.setPlaceholderText("(opcional)")
        pago_layout.addWidget(self.observaciones, 2, 1)

        pago_group.setLayout(pago_layout)
        layout.addWidget(pago_group)

        buttons_layout = QHBoxLayout()

        btn_cancelar_todo = QPushButton("Cancelar Todo")
        btn_cancelar_todo.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_cancelar_todo.clicked.connect(self.cancelar_todo)
        buttons_layout.addWidget(btn_cancelar_todo)

        btn_pago_parcial = QPushButton("Registrar Pago")
        btn_pago_parcial.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_pago_parcial.clicked.connect(self.registrar_pago_parcial)
        buttons_layout.addWidget(btn_pago_parcial)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cerrar)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def cancelar_todo(self):
        """Marca la deuda como completamente pagada."""
        self.deuda["_accion"] = "cancelar_todo"
        if hasattr(self, "fecha_pago_edit"):
            self.deuda["_fecha_pago"] = self.fecha_pago_edit.date().toString("dd/MM/yyyy")
        self.accept()

    def registrar_pago_parcial(self):
        """Registra un pago parcial."""
        try:
            monto_str = self.monto_pago.text().strip()
            if not monto_str:
                QMessageBox.warning(self, "Error", "Ingrese el monto a cancelar.")
                return

            monto = float(monto_str)
            falta = self._to_float(self.deuda.get("monto_faltante", 0), 0.0)

            if monto <= 0:
                QMessageBox.warning(self, "Error", "El monto debe ser mayor a 0.")
                return

            if monto > falta:
                QMessageBox.warning(self, "Error", f"El monto no puede exceder S/. {falta:.2f}")
                return

            self.deuda["_accion"] = "pago_parcial"
            self.deuda["_monto_pagado"] = monto
            if hasattr(self, "fecha_pago_edit"):
                self.deuda["_fecha_pago"] = self.fecha_pago_edit.date().toString("dd/MM/yyyy")
            self.deuda["_observaciones"] = self.observaciones.text().strip()
            self.accept()

        except ValueError:
            QMessageBox.critical(self, "Error", "Ingrese un monto válido (números).")
