import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QRadioButton, QSpinBox, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from utils.api_handler import listar_dispositivos_hijos_remoto

class BranchTransferDialog(QDialog):
    """Ventana para transferir stock de un producto a otra sucursal."""

    def __init__(self, product_data, current_username, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.username = current_username
        self.selected_branch_code = None
        self.transfer_quantity = 0
        self.setup_ui()
        self.load_branches()

    def setup_ui(self):
        self.setWindowTitle("Transferencia de Inventario")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #F9FAFB; }
            QLabel#title { font-size: 18px; font-weight: bold; color: #111827; }
            QFrame#card { background-color: white; border: 1px solid #E5E7EB; border-radius: 12px; }
            QPushButton#btnConfirm { background-color: #7C3AED; color: white; font-weight: bold; padding: 10px; border-radius: 8px; }
            QPushButton#btnCancel { background-color: #F3F4F6; color: #374151; padding: 10px; border-radius: 8px; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Encabezado
        title = QLabel("Mover Producto")
        title.setObjectName("title")
        layout.addWidget(title)

        prod_name = self.product_data.get('nombre', 'Producto')
        current_stock = int(self.product_data.get('stock', 0))
        layout.addWidget(QLabel(f"Producto: <b>{prod_name}</b>"))
        layout.addWidget(QLabel(f"Stock disponible actual: <b>{current_stock} unidades</b>"))

        # Seleccionar Sucursal
        layout.addWidget(QLabel("Seleccionar sucursal de destino:"))
        self.combo_branches = QComboBox()
        self.combo_branches.addItem("Cargando sucursales...")
        layout.addWidget(self.combo_branches)

        # Opciones de cantidad
        group_box = QFrame()
        group_box.setObjectName("card")
        group_layout = QVBoxLayout(group_box)
        
        self.radio_all = QRadioButton(f"Mover todo el stock ({current_stock})")
        self.radio_all.setChecked(True)
        
        self.radio_manual = QRadioButton("Mover cantidad específica:")
        
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setRange(1, current_stock)
        self.spin_quantity.setValue(min(max(1, current_stock), current_stock))
        self.spin_quantity.setKeyboardTracking(False)
        self.spin_quantity.setEnabled(False)
        
        group_layout.addWidget(self.radio_all)
        group_layout.addWidget(self.radio_manual)
        group_layout.addWidget(self.spin_quantity)
        
        layout.addWidget(group_box)

        # Conectar radio buttons
        self.radio_manual.toggled.connect(self.spin_quantity.setEnabled)

        # Botones finales
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_confirm = QPushButton("Confirmar Transferencia")
        self.btn_confirm.setObjectName("btnConfirm")
        self.btn_confirm.clicked.connect(self.validate_and_accept)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    def load_branches(self):
        """Carga la lista de sucursales desde el servidor."""
        try:
            ok, dispositivos, msg = listar_dispositivos_hijos_remoto(self.username)
            self.combo_branches.clear()
            if ok and dispositivos:
                for d in dispositivos:
                    nombre = d.get('nombre_optica', 'Sin nombre')
                    ciudad = d.get('ciudad', '')
                    codigo = d.get('codigo_dispositivo', '')
                    self.combo_branches.addItem(f"{nombre} ({ciudad})", codigo)
                self.btn_confirm.setEnabled(True)
            else:
                self.combo_branches.addItem("No se encontraron sucursales")
                self.btn_confirm.setEnabled(False)
        except Exception as e:
            self.combo_branches.clear()
            self.combo_branches.addItem("Error al cargar sucursales")
            self.btn_confirm.setEnabled(False)

    def validate_and_accept(self):
        self.selected_branch_code = self.combo_branches.currentData()
        if not self.selected_branch_code:
            QMessageBox.warning(self, "Error", "Debes seleccionar una sucursal de destino.")
            return

        if self.radio_all.isChecked():
            self.transfer_quantity = int(self.product_data.get('stock', 0))
        else:
            try:
                # Forzar que el texto escrito manualmente se convierta en valor
                # antes de leerlo. Sin esto puede quedarse en el valor previo (ej. 1).
                self.spin_quantity.interpretText()
            except Exception:
                pass
            self.transfer_quantity = self.spin_quantity.value()

        if self.transfer_quantity <= 0:
            QMessageBox.warning(self, "Error", "La cantidad debe ser mayor a cero.")
            return

        self.accept()

    def get_transfer_data(self):
        return {
            "branch_code": self.selected_branch_code,
            "quantity": self.transfer_quantity
        }
