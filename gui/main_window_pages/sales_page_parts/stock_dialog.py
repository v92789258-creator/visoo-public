from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout


class AgregarStockDialog(QDialog):
    """Diálogo para agregar stock a un producto cuando hay insuficiencia."""

    def __init__(self, producto_nombre, stock_actual, cantidad_necesaria, parent=None):
        super().__init__(parent)
        self.producto_nombre = producto_nombre
        self.stock_actual = stock_actual
        self.cantidad_necesaria = cantidad_necesaria
        self.unidades_agregar = 0
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Agregar Stock al Producto")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        info_label = QLabel(f"<b>Producto:</b> {self.producto_nombre}")
        layout.addWidget(info_label)

        stock_label = QLabel(
            f"<b>Stock actual:</b> {self.stock_actual} unidades<br>"
            f"<b>Cantidad requerida:</b> {self.cantidad_necesaria} unidades<br>"
            f"<b>Faltante:</b> {max(0, self.cantidad_necesaria - self.stock_actual)} unidades"
        )
        stock_label.setStyleSheet("color: #E74C3C;")
        layout.addWidget(stock_label)

        separator = QLabel()
        layout.addWidget(separator)

        input_layout = QHBoxLayout()
        input_label = QLabel("¿Cuántas unidades desea agregar?")
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(0)
        self.spinbox.setMaximum(10000)
        self.spinbox.setValue(max(0, self.cantidad_necesaria - self.stock_actual))
        self.spinbox.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 14px;
                min-width: 100px;
            }
        """)
        input_layout.addWidget(input_label)
        input_layout.addStretch()
        input_layout.addWidget(self.spinbox)
        layout.addLayout(input_layout)

        self.total_stock_label = QLabel(f"<b>Nuevo stock total:</b> {self.stock_actual + self.spinbox.value()} unidades")
        layout.addWidget(self.total_stock_label)
        self.spinbox.valueChanged.connect(self._update_total_stock)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setMinimumWidth(100)
        btn_cancelar.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancelar)

        btn_agregar = QPushButton("✓ Agregar Stock")
        btn_agregar.setObjectName("primaryButton")
        btn_agregar.setMinimumWidth(120)
        btn_agregar.clicked.connect(self._on_agregar_clicked)
        button_layout.addWidget(btn_agregar)

        layout.addStretch()
        layout.addLayout(button_layout)

    def _update_total_stock(self):
        """Actualiza el label del stock total."""
        nuevo_total = self.stock_actual + self.spinbox.value()
        self.total_stock_label.setText(f"<b>Nuevo stock total:</b> {nuevo_total} unidades")

    def _on_agregar_clicked(self):
        """Guarda la cantidad a agregar y cierra el diálogo."""
        self.unidades_agregar = self.spinbox.value()
        self.accept()

    def get_unidades(self):
        """Retorna la cantidad de unidades a agregar."""
        return self.unidades_agregar
