from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QWidget, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class ProductActionsDialog(QDialog):
    """Dialogo con acciones rapidas para un producto del inventario."""

    def __init__(self, product_data, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.action = None
        self.setup_ui()

    def setup_ui(self):
        product_name = str(self.product_data.get('nombre', 'Desconocido')).strip() or "Desconocido"
        self.setWindowTitle("Acciones del producto")
        self.setMinimumWidth(460)
        self.setMaximumWidth(560)
        self.setWindowModality(Qt.ApplicationModal)
        self.setObjectName("productActionsDialog")

        self.setStyleSheet(
            """
            QDialog#productActionsDialog {
                background-color: #F4F6F9;
            }
            QFrame#headerPanel {
                background-color: #FFFFFF;
                border: 1px solid #E5EAF0;
                border-radius: 12px;
            }
            QLabel#titleLabel {
                color: #111827;
                font-size: 26px;
                font-weight: 700;
            }
            QLabel#subtitleLabel {
                color: #6B7280;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#helpButton {
                background-color: #0EA5E9;
                color: #FFFFFF;
                border: none;
                border-radius: 13px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton#helpButton:hover {
                background-color: #0284C7;
            }
            QFrame#infoPanel {
                background-color: #FFFFFF;
                border: 1px solid #E5EAF0;
                border-radius: 12px;
            }
            QLabel#infoPanelTitle {
                color: #111827;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#fieldLabel {
                color: #4B5563;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#fieldValue {
                color: #111827;
                font-size: 12px;
                font-weight: 500;
            }
            QFrame#dividerLine {
                background-color: #E5EAF0;
                max-height: 1px;
                min-height: 1px;
            }
            QPushButton[role="primary"] {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 11px 14px;
            }
            QPushButton[role="primary"]:hover {
                background-color: #1D4ED8;
            }
            QPushButton[role="section"] {
                background-color: #0F766E;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 11px 14px;
            }
            QPushButton[role="section"]:hover {
                background-color: #0D5F59;
            }
            QPushButton[role="stock"] {
                background-color: #111827;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 11px 14px;
            }
            QPushButton[role="stock"]:hover {
                background-color: #0B1220;
            }
            QPushButton[role="branch"] {
                background-color: #7C3AED;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 11px 14px;
            }
            QPushButton[role="branch"]:hover {
                background-color: #6D28D9;
            }
            QPushButton[role="branch_blocked"] {
                background-color: #E5E7EB;
                color: #6B7280;
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 11px 14px;
            }
            QPushButton[role="branch_blocked"]:hover {
                background-color: #DDE1E7;
                color: #4B5563;
            }
            QPushButton[role="danger"] {
                background-color: #DC2626;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 11px 14px;
            }
            QPushButton[role="danger"]:hover {
                background-color: #B91C1C;
            }
            QPushButton[role="cancel"] {
                background-color: #E5E7EB;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 14px;
            }
            QPushButton[role="cancel"]:hover {
                background-color: #DDE1E7;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(12)
        root_layout.setContentsMargins(18, 18, 18, 18)

        header_panel = QFrame()
        header_panel.setObjectName("headerPanel")
        header_layout = QHBoxLayout(header_panel)
        header_layout.setContentsMargins(16, 14, 12, 14)
        header_layout.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        title_label = QLabel(product_name)
        title_label.setObjectName("titleLabel")
        title_label.setWordWrap(True)

        subtitle_label = QLabel("Gestion rapida del producto")
        subtitle_label.setObjectName("subtitleLabel")

        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)

        btn_help = QPushButton("?")
        btn_help.setObjectName("helpButton")
        btn_help.setFixedSize(26, 26)
        btn_help.setToolTip("Mini tutorial")
        btn_help.clicked.connect(self.show_help)

        header_layout.addLayout(title_col, stretch=1)
        header_layout.addWidget(btn_help, alignment=Qt.AlignTop)
        root_layout.addWidget(header_panel)

        info_panel = QFrame()
        info_panel.setObjectName("infoPanel")
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(8)

        info_title = QLabel("Resumen del producto")
        info_title.setObjectName("infoPanelTitle")
        info_layout.addWidget(info_title)

        try:
            venta = float(self.product_data.get('venta', 0))
        except (ValueError, TypeError):
            venta = 0.0

        try:
            stock = int(self.product_data.get('stock', 0))
        except (ValueError, TypeError):
            stock = 0

        marca = str(self.product_data.get('marca', 'N/A')).strip() or "N/A"
        categoria = str(self.product_data.get('seccion') or self.product_data.get('categoria') or "N/A").strip() or "N/A"

        self._add_info_row(info_layout, "Marca", marca)
        self._add_info_row(info_layout, "Stock", f"{stock} unidades")
        self._add_info_row(info_layout, "Precio de venta", f"S/ {venta:.2f}")
        self._add_info_row(info_layout, "Categoria", categoria)

        root_layout.addWidget(info_panel)

        divider = QFrame()
        divider.setObjectName("dividerLine")
        root_layout.addWidget(divider)

        btn_edit = self._build_action_button("Editar producto", "primary", self.on_edit)
        btn_change_section = self._build_action_button("Cambiar seccion", "section", self.on_change_section)
        btn_add_stock = self._build_action_button("Aumentar stock", "stock", self.on_add_stock)
        btn_transfer = self._build_action_button("Mover a otra sucursal", "branch_blocked", self.on_transfer_blocked)
        btn_transfer.setToolTip("Bloqueado temporalmente por seguridad hasta validar transferencias entre sucursales.")
        btn_transfer.setCursor(Qt.ForbiddenCursor)
        btn_delete = self._build_action_button("Eliminar producto", "danger", self.on_delete)
        btn_cancel = self._build_action_button("Cancelar", "cancel", self.reject)

        root_layout.addWidget(btn_edit)
        root_layout.addWidget(btn_change_section)
        root_layout.addWidget(btn_add_stock)
        root_layout.addWidget(btn_transfer)
        root_layout.addWidget(btn_delete)
        root_layout.addSpacing(2)
        root_layout.addWidget(btn_cancel)

    def _build_action_button(self, text, role, callback):
        button = QPushButton(text)
        button.setMinimumHeight(46 if role != "cancel" else 42)
        button.setProperty("role", role)
        button.clicked.connect(callback)
        return button

    def _add_info_row(self, parent_layout, label_text, value_text):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        lbl = QLabel(f"{label_text}:")
        lbl.setObjectName("fieldLabel")
        lbl.setMinimumWidth(110)

        val = QLabel(value_text)
        val.setObjectName("fieldValue")
        val.setWordWrap(True)
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)

        row_layout.addWidget(lbl)
        row_layout.addWidget(val, stretch=1)
        parent_layout.addWidget(row)

    def on_edit(self):
        self.action = 'edit'
        self.accept()

    def on_change_section(self):
        self.action = 'change_section'
        self.accept()

    def on_add_stock(self):
        self.action = 'add_stock'
        self.accept()

    def on_transfer(self):
        self.action = 'transfer'
        self.accept()

    def on_transfer_blocked(self):
        QMessageBox.information(
            self,
            "Funcion bloqueada temporalmente",
            "Mover a otra sucursal esta bloqueado temporalmente por seguridad.\n\nSe reactivara cuando la transferencia quede validada."
        )

    def on_delete(self):
        product_name = self.product_data.get('nombre', 'Desconocido')
        reply = QMessageBox.question(
            self,
            "Confirmar eliminacion",
            (
                f"Estas seguro de eliminar el producto '{product_name}'?\n\n"
                "Esta accion no se puede deshacer."
            ),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.action = 'delete'
            self.accept()

    def show_help(self):
        help_text = """
<h3>Mini tutorial - Gestion de productos</h3>
<p><b>Editar producto:</b> modifica los datos completos.</p>
<p><b>Cambiar seccion:</b> mueve el producto a otra seccion/categoria.</p>
<p><b>Aumentar stock:</b> agrega unidades disponibles.</p>
<p><b>Eliminar producto:</b> borra el producto de forma permanente.</p>
"""
        QMessageBox.information(self, "Opciones del producto", help_text)

    def get_action(self):
        return self.action
