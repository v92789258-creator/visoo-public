from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt
import json
import os
from utils.file_handler import cargar_productos, guardar_productos

class CategoryManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories = self.load_categories()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Gestor de Categorías")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        
        # Campo de entrada
        input_layout = QHBoxLayout()
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Nueva categoría...")
        add_btn = QPushButton("Agregar")
        add_btn.clicked.connect(self.add_category)
        input_layout.addWidget(self.category_input)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)
        
        # Lista de categorías
        self.category_list = QListWidget()
        self.category_list.setSelectionMode(QListWidget.SingleSelection)
        self.refresh_categories()
        layout.addWidget(QLabel("Categorías existentes:"))
        layout.addWidget(self.category_list)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        remove_btn = QPushButton("Eliminar")
        remove_btn.clicked.connect(self.remove_category)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def load_categories(self):
        try:
            file_path = os.path.join("VISO", "data", "categories.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return ["Monturas", "Lunas", "Lentes de Contacto", "Gafas de Sol", "Accesorios", "Líquidos de Limpieza"]
        except Exception:
            return ["Monturas", "Lunas", "Lentes de Contacto", "Gafas de Sol", "Accesorios", "Líquidos de Limpieza"]
    
    def save_categories(self):
        try:
            file_path = os.path.join("VISO", "data", "categories.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron guardar las categorías: {str(e)}")
    
    def refresh_categories(self):
        self.category_list.clear()
        self.category_list.addItems(sorted(self.categories))
    
    def add_category(self):
        category = self.category_input.text().strip()
        if not category:
            return
            
        if category in self.categories:
            QMessageBox.warning(self, "Error", "Esta categoría ya existe.")
            return
            
        self.categories.append(category)
        self.save_categories()
        self.refresh_categories()
        self.category_input.clear()
    
    def remove_category(self):
        current_item = self.category_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Por favor selecciona una categoría para eliminar.")
            return
            
        category = current_item.text()
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Estás seguro de eliminar la categoría '{category}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        username = self._get_parent_username()
        if username:
            productos = cargar_productos(username) or []
            in_use_products = [
                p for p in productos
                if self._get_product_section(p).lower() == category.lower()
            ]
            if in_use_products:
                targets = sorted([
                    c for c in self.categories
                    if c.lower() != category.lower()
                ], key=lambda x: x.lower())

                if targets:
                    target, ok = QInputDialog.getItem(
                        self,
                        "Reasignar productos",
                        (
                            f"La categoría '{category}' está asignada a "
                            f"{len(in_use_products)} productos.\n\n"
                            "Selecciona la nueva categoría:"
                        ),
                        targets,
                        0,
                        False
                    )
                    if not ok:
                        return
                    for p in productos:
                        if self._get_product_section(p).lower() == category.lower():
                            self._set_product_section(p, target)
                else:
                    clear_reply = QMessageBox.question(
                        self,
                        "Categoría en uso",
                        (
                            f"La categoría '{category}' está asignada a "
                            f"{len(in_use_products)} productos y no hay otra categoría.\n\n"
                            "¿Deseas dejar esos productos sin categoría?"
                        ),
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if clear_reply != QMessageBox.Yes:
                        return
                    for p in productos:
                        if self._get_product_section(p).lower() == category.lower():
                            self._set_product_section(p, "")

                guardar_productos(username, productos)

        self.categories.remove(category)
        self.save_categories()
        self.refresh_categories()

    def _get_parent_username(self):
        current = self.parent()
        while current:
            username = getattr(current, 'username', None)
            if username:
                return username
            current = current.parent() if hasattr(current, 'parent') else None
        return None

    def _get_product_section(self, product):
        if not isinstance(product, dict):
            return ''
        return str(product.get('seccion') or product.get('categoria') or '').strip()

    def _set_product_section(self, product, section):
        if not isinstance(product, dict):
            return
        normalized = str(section or '').strip()
        product['categoria'] = normalized
        product['seccion'] = normalized
