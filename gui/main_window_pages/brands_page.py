import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QInputDialog
)
from PyQt5.QtCore import Qt
from pathlib import Path

class BrandsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = parent.username if parent else None
        self.brands_file = os.path.join(Path(__file__).resolve().parent.parent.parent, 
                                      'data', 'brands.json')
        self.setup_ui()
        self.load_brands()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Panel izquierdo (lista de marcas)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)

        # Título de la lista
        title = QLabel("Marcas Registradas")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2C3E50;
                padding: 5px 0;
            }
        """)
        left_layout.addWidget(title)

        # Lista de marcas
        self.brands_list = QListWidget()
        self.brands_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 5px;
                background: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F1F3F5;
            }
            QListWidget::item:selected {
                background: #E7F1FF;
                color: #0D6EFD;
            }
            QListWidget::item:hover {
                background: #F8F9FA;
            }
        """)
        left_layout.addWidget(self.brands_list)

        # Panel derecho (acciones)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)

        # Sección de agregar marca
        add_section = QWidget()
        add_layout = QVBoxLayout(add_section)
        add_layout.setSpacing(10)

        add_title = QLabel("Agregar Nueva Marca")
        add_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50;")
        add_layout.addWidget(add_title)

        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Nombre de la marca")
        self.brand_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #DEE2E6;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #86B7FE;
                outline: none;
            }
        """)
        add_layout.addWidget(self.brand_input)

        # Botones de acción
        button_style = """
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
            }
        """

        add_btn = QPushButton("✚ Agregar Marca")
        add_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #0D6EFD;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #0B5ED7;
            }
        """)
        add_btn.clicked.connect(self.add_brand)
        add_layout.addWidget(add_btn)

        edit_btn = QPushButton("✎ Editar Marca")
        edit_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #FFC107;
                color: #000;
                border: none;
            }
            QPushButton:hover {
                background-color: #FFCA2C;
            }
        """)
        edit_btn.clicked.connect(self.edit_brand)
        add_layout.addWidget(edit_btn)

        delete_btn = QPushButton("🗑 Eliminar Marca")
        delete_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #BB2D3B;
            }
        """)
        delete_btn.clicked.connect(self.delete_brand)
        add_layout.addWidget(delete_btn)

        right_layout.addWidget(add_section)
        right_layout.addStretch()

        # Agregar paneles al layout principal
        layout.addWidget(left_panel, 2)
        layout.addWidget(right_panel, 1)

    def load_brands(self):
        try:
            os.makedirs(os.path.dirname(self.brands_file), exist_ok=True)
            if os.path.exists(self.brands_file):
                with open(self.brands_file, 'r', encoding='utf-8') as f:
                    brands = json.load(f)
            else:
                brands = []
                with open(self.brands_file, 'w', encoding='utf-8') as f:
                    json.dump(brands, f, ensure_ascii=False, indent=4)
            
            self.brands_list.clear()
            for brand in sorted(brands):
                item = QListWidgetItem(brand)
                self.brands_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar las marcas: {str(e)}")

    def save_brands(self):
        try:
            brands = []
            for i in range(self.brands_list.count()):
                brands.append(self.brands_list.item(i).text())
            
            os.makedirs(os.path.dirname(self.brands_file), exist_ok=True)
            with open(self.brands_file, 'w', encoding='utf-8') as f:
                json.dump(brands, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar las marcas: {str(e)}")

    def add_brand(self):
        brand_name = self.brand_input.text().strip()
        if not brand_name:
            QMessageBox.warning(self, "Error", "Por favor ingrese un nombre de marca")
            return

        # Verificar si la marca ya existe
        existing_items = self.brands_list.findItems(brand_name, Qt.MatchExactly)
        if existing_items:
            QMessageBox.warning(self, "Error", "Esta marca ya existe")
            return

        # Agregar la nueva marca
        self.brands_list.addItem(brand_name)
        self.brands_list.sortItems()
        self.brand_input.clear()
        self.save_brands()
        QMessageBox.information(self, "Éxito", "Marca agregada correctamente")

    def edit_brand(self):
        current_item = self.brands_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Por favor seleccione una marca para editar")
            return

        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(
            self, "Editar Marca", "Nuevo nombre de la marca:",
            QLineEdit.Normal, old_name
        )

        if ok and new_name.strip():
            # Verificar si el nuevo nombre ya existe
            if new_name != old_name:
                existing_items = self.brands_list.findItems(new_name, Qt.MatchExactly)
                if existing_items:
                    QMessageBox.warning(self, "Error", "Esta marca ya existe")
                    return

            current_item.setText(new_name)
            self.brands_list.sortItems()
            self.save_brands()
            QMessageBox.information(self, "Éxito", "Marca actualizada correctamente")

    def delete_brand(self):
        current_item = self.brands_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Por favor seleccione una marca para eliminar")
            return

        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar la marca '{current_item.text()}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.brands_list.takeItem(self.brands_list.row(current_item))
            self.save_brands()
            QMessageBox.information(self, "Éxito", "Marca eliminada correctamente")