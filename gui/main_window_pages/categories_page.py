import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QInputDialog, QFrame
)
from PyQt5.QtCore import Qt
from pathlib import Path

class CategoriesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = parent.username if parent else None
        self.categories_file = os.path.join(Path(__file__).resolve().parent.parent.parent, 
                                          'data', 'categories.json')
        self.setup_ui()
        self.load_categories()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Contenedor principal
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Título y campo de nueva categoría
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)

        title = QLabel("Categorías de Productos")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2C3E50;
            }
        """)
        header_layout.addWidget(title)

        # Campo de nueva categoría
        add_widget = QWidget()
        add_layout = QHBoxLayout(add_widget)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.setSpacing(10)

        self.new_category_input = QLineEdit()
        self.new_category_input.setPlaceholderText("Nombre de la categoría")
        self.new_category_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #DEE2E6;
                border-radius: 4px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #0D6EFD;
            }
        """)

        add_btn = QPushButton("+ Agregar Categoría")
        add_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #0D6EFD;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #0B5ED7;
            }
        """)
        add_btn.clicked.connect(self.add_category)
        
        add_layout.addWidget(self.new_category_input)
        add_layout.addWidget(add_btn)
        
        header_layout.addStretch()
        header_layout.addWidget(add_widget)
        main_layout.addWidget(header)

        # Lista de categorías con ejemplos
        examples_label = QLabel("Ejemplos de categorías:")
        examples_label.setStyleSheet("color: #6C757D; font-size: 13px;")
        main_layout.addWidget(examples_label)

        # Lista de categorías
        self.categories_list = QListWidget()
        self.categories_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                padding: 10px;
                background: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #DEE2E6;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
            QListWidget::item:selected {
                background: #E9ECEF;
                color: #2C3E50;
            }
            QListWidget::item:hover {
                background: #F8F9FA;
            }
            QListWidget::item:hover {
                background: #F8F9FA;
            }
        """)
        main_layout.addWidget(self.categories_list)

        # Botones de acción
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(10)

        edit_btn = QPushButton("✏️ Editar Categoría")
        edit_btn.clicked.connect(self.edit_category)
        edit_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #FFC107;
                color: #000;
                border: none;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #E0A800;
            }
        """)
        
        delete_btn = QPushButton("  Eliminar Categoría")
        delete_btn.clicked.connect(self.delete_category)
        delete_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        
        main_layout.addWidget(button_container)
        layout.addWidget(main_container)
        # Los botones de acción ya están definidos en el layout principal

    def load_categories(self):
        try:
            os.makedirs(os.path.dirname(self.categories_file), exist_ok=True)
            if os.path.exists(self.categories_file):
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    categories = json.load(f)
            else:
                categories = []
                with open(self.categories_file, 'w', encoding='utf-8') as f:
                    json.dump(categories, f, ensure_ascii=False, indent=4)
            
            self.categories_list.clear()
            for category in sorted(categories):
                item = QListWidgetItem(category)
                self.categories_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar las categorías: {str(e)}")

    def save_categories(self):
        try:
            categories = []
            for i in range(self.categories_list.count()):
                categories.append(self.categories_list.item(i).text())
            
            os.makedirs(os.path.dirname(self.categories_file), exist_ok=True)
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(categories, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar las categorías: {str(e)}")

    def quick_add_category(self, category_name):
        # Verificar si la categoría ya existe
        existing_items = self.categories_list.findItems(category_name, Qt.MatchExactly)
        if existing_items:
            QMessageBox.warning(self, "Error", "Esta categoría ya existe")
            return

        # Agregar la categoría
        self.categories_list.addItem(category_name)
        self.categories_list.sortItems()
        self.save_categories()
        QMessageBox.information(self, "Éxito", "Categoría agregada correctamente")

    def add_category(self):
        category_name = self.category_input.text().strip()
        if not category_name:
            QMessageBox.warning(self, "Error", "Por favor ingrese un nombre de categoría")
            return

        # Verificar si la categoría ya existe
        existing_items = self.categories_list.findItems(category_name, Qt.MatchExactly)
        if existing_items:
            QMessageBox.warning(self, "Error", "Esta categoría ya existe")
            return

        # Agregar la nueva categoría
        self.categories_list.addItem(category_name)
        self.categories_list.sortItems()
        self.category_input.clear()
        self.save_categories()
        QMessageBox.information(self, "Éxito", "Categoría agregada correctamente")

    def edit_category(self):
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Por favor seleccione una categoría para editar")
            return

        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(
            self, "Editar Categoría", "Nuevo nombre de la categoría:",
            QLineEdit.Normal, old_name
        )

        if ok and new_name.strip():
            # Verificar si el nuevo nombre ya existe
            if new_name != old_name:
                existing_items = self.categories_list.findItems(new_name, Qt.MatchExactly)
                if existing_items:
                    QMessageBox.warning(self, "Error", "Esta categoría ya existe")
                    return

            current_item.setText(new_name)
            self.categories_list.sortItems()
            self.save_categories()
            QMessageBox.information(self, "Éxito", "Categoría actualizada correctamente")

    def delete_category(self):
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Por favor seleccione una categoría para eliminar")
            return

        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar la categoría '{current_item.text()}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.categories_list.takeItem(self.categories_list.row(current_item))
            self.save_categories()
            QMessageBox.information(self, "Éxito", "Categoría eliminada correctamente")