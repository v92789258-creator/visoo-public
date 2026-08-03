import sys
import os
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QMessageBox
)

class EditProductDialog(QDialog):
    def __init__(self, product_data=None, parent=None):
        super().__init__(parent)
        # Si no hay product_data, es un producto nuevo
        self.is_new_product = product_data is None
        self.product_data = product_data or {}
        
        # Si es nuevo producto, generar código secuencial
        if self.is_new_product:
            next_code = self.generate_next_sequential_code()
            self.product_data['codigo'] = next_code
            self.setWindowTitle("Nuevo Producto")
        else:
            self.setWindowTitle(f"Editar Producto: {self.product_data['nombre']}")
        
        self.init_ui()
    
    def generate_next_sequential_code(self):
        """Genera el siguiente código secuencial basado en los códigos existentes."""
        try:
            # Obtener username del padre
            username = None
            current = self.parent()
            
            # Buscar username en la cadena de parents
            while current and not username:
                username = getattr(current, 'username', None)
                current = current.parent() if hasattr(current, 'parent') and callable(current.parent) else None
            
            if not username:
                print("[DEBUG] No username found, returning 0000001")
                return "0000001"
            
            print(f"[DEBUG] Found username: {username}")
            
            # Cargar productos existentes
            from utils.file_handler import cargar_productos
            productos = cargar_productos(username)
            print(f"[DEBUG] Loaded {len(productos)} productos")
            
            if not productos:
                print("[DEBUG] No productos, returning 0000001")
                return "0000001"
            
            # Extraer códigos numéricos
            numeric_codes = []
            for prod in productos:
                codigo = prod.get('codigo', '').strip()
                if codigo and codigo.isdigit():
                    try:
                        numeric_codes.append(int(codigo))
                    except (ValueError, TypeError):
                        pass
            
            print(f"[DEBUG] Found {len(numeric_codes)} numeric codes")
            
            # Si hay códigos numéricos, obtener el máximo y sumar 1
            if numeric_codes:
                max_code = max(numeric_codes)
                next_code = max_code + 1
            else:
                next_code = 1
            
            result = f"{next_code:07d}"
            print(f"[DEBUG] Generated code: {result}")
            return result
        except Exception as e:
            print(f"[ERROR] Error al generar código: {e}")
            import traceback
            traceback.print_exc()
            return "0000001"
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.codigo_entry = QLineEdit(self.product_data.get('codigo', ''))
        self.nombre_entry = QLineEdit(self.product_data.get('nombre', ''))
        self.costo_entry = QLineEdit(str(self.product_data.get('costo', 0.0)))
        self.venta_entry = QLineEdit(str(self.product_data.get('venta', 0.0)))
        self.stock_entry = QLineEdit(str(self.product_data.get('stock', 0)))

        form_layout.addRow("Código:", self.codigo_entry)
        form_layout.addRow("Nombre:", self.nombre_entry)
        form_layout.addRow("Costo:", self.costo_entry)
        form_layout.addRow("Venta:", self.venta_entry)
        form_layout.addRow("Stock:", self.stock_entry)

        main_layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Save).setObjectName("primaryButton")
        button_box.accepted.connect(self.save_changes)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def save_changes(self):
        new_codigo = self.codigo_entry.text().strip()
        new_nombre = self.nombre_entry.text().strip()
        new_costo_str = self.costo_entry.text().strip()
        new_venta_str = self.venta_entry.text().strip()
        new_stock_str = self.stock_entry.text().strip()

        if not new_codigo:
            QMessageBox.critical(self, "Error", "El código del producto es obligatorio.")
            return

        if not new_nombre:
            QMessageBox.critical(self, "Error", "El nombre es obligatorio.")
            return

        try:
            new_costo = float(new_costo_str) if new_costo_str else 0.0
            new_venta = float(new_venta_str) if new_venta_str else 0.0
            new_stock = int(new_stock_str) if new_stock_str else 0
        except ValueError:
            QMessageBox.critical(self, "Error de datos", "Costo, Venta y Stock deben ser números válidos.")
            return

        self.product_data['codigo'] = new_codigo
        self.product_data['nombre'] = new_nombre
        self.product_data['costo'] = new_costo
        self.product_data['venta'] = new_venta
        self.product_data['stock'] = new_stock

        self.accept()