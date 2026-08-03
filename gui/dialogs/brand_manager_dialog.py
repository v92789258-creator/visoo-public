from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QMessageBox, QFormLayout
)
from PyQt5.QtCore import Qt
import json
import os

class BrandManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.brands = self.load_brands()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Gestor de Marcas")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        
        # Formulario de entrada
        form_layout = QFormLayout()
        
        # Campo de nombre de marca
        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Nombre de la marca...")
        form_layout.addRow("Marca:", self.brand_input)
        
        # Campo de proveedor
        self.provider_input = QLineEdit()
        self.provider_input.setPlaceholderText("Nombre del proveedor...")
        form_layout.addRow("Proveedor:", self.provider_input)
        
        # Campo de contacto
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Información de contacto...")
        form_layout.addRow("Contacto:", self.contact_input)
        
        layout.addLayout(form_layout)
        
        # Botón de agregar
        add_btn = QPushButton("Agregar Marca")
        add_btn.clicked.connect(self.add_brand)
        layout.addWidget(add_btn)
        
        # Lista de marcas
        self.brand_list = QListWidget()
        self.brand_list.setSelectionMode(QListWidget.SingleSelection)
        self.refresh_brands()
        layout.addWidget(QLabel("Marcas registradas:"))
        layout.addWidget(self.brand_list)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        remove_btn = QPushButton("Eliminar")
        remove_btn.clicked.connect(self.remove_brand)
        edit_btn = QPushButton("Editar")
        edit_btn.clicked.connect(self.edit_brand)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.brand_list.itemClicked.connect(self.load_brand_details)
    
    def load_brands(self):
        try:
            file_path = os.path.join("VISO", "data", "brands.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            # No seeds defaults: marcas deben ser añadidas por el usuario.
            return {}
        except Exception:
            return {}
    
    def save_brands(self):
        try:
            file_path = os.path.join("VISO", "data", "brands.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.brands, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron guardar las marcas: {str(e)}")
    
    def refresh_brands(self):
        self.brand_list.clear()
        self.brand_list.addItems(sorted(self.brands.keys()))
    
    def add_brand(self):
        brand = self.brand_input.text().strip()
        provider = self.provider_input.text().strip()
        contact = self.contact_input.text().strip()
        
        if not brand:
            QMessageBox.warning(self, "Error", "Por favor ingresa el nombre de la marca.")
            return
            
        if brand in self.brands and not self.editing_existing:
            QMessageBox.warning(self, "Error", "Esta marca ya existe.")
            return
            
        self.brands[brand] = {
            "provider": provider,
            "contact": contact
        }
        
        self.save_brands()
        self.refresh_brands()
        self.clear_inputs()
    
    def remove_brand(self):
        current_item = self.brand_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Por favor selecciona una marca para eliminar.")
            return
            
        brand = current_item.text()
        reply = QMessageBox.question(self, "Confirmar", 
                                   f"¿Estás seguro de eliminar la marca '{brand}'?",
                                   QMessageBox.Yes | QMessageBox.No)
                                   
        if reply == QMessageBox.Yes:
            del self.brands[brand]
            self.save_brands()
            self.refresh_brands()
            self.clear_inputs()
    
    def edit_brand(self):
        current_item = self.brand_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Por favor selecciona una marca para editar.")
            return
        
        brand = current_item.text()
        brand_data = self.brands[brand]
        
        self.brand_input.setText(brand)
        self.provider_input.setText(brand_data.get("provider", ""))
        self.contact_input.setText(brand_data.get("contact", ""))
        
        # Eliminar la marca anterior después de editarla
        del self.brands[brand]
        self.editing_existing = True
    
    def load_brand_details(self, item):
        brand = item.text()
        brand_data = self.brands[brand]
        
        self.brand_input.setText(brand)
        self.provider_input.setText(brand_data.get("provider", ""))
        self.contact_input.setText(brand_data.get("contact", ""))
        
    def clear_inputs(self):
        self.brand_input.clear()
        self.provider_input.clear()
        self.contact_input.clear()
        self.editing_existing = False