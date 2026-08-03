from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QMessageBox
)
from PyQt5.QtCore import Qt
import json
import os

class ColorsManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.colors = self.load_colors()
        self.editing_index = -1
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Gestor de Colores")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        
        # Campo de entrada de color
        input_layout = QHBoxLayout()
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("Nombre del color (ej: Azul, Rojo, etc.)...")
        input_layout.addWidget(QLabel("Color:"))
        input_layout.addWidget(self.color_input)
        layout.addLayout(input_layout)
        
        # Botón de agregar
        add_btn = QPushButton("Agregar Color")
        add_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; border-radius: 4px;")
        add_btn.clicked.connect(self.add_color)
        layout.addWidget(add_btn)
        
        # Lista de colores
        layout.addWidget(QLabel("Colores disponibles:"))
        self.color_list = QListWidget()
        self.color_list.setSelectionMode(QListWidget.SingleSelection)
        self.color_list.itemClicked.connect(self.load_color_details)
        self.refresh_colors()
        layout.addWidget(self.color_list)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        remove_btn = QPushButton("Eliminar")
        remove_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px; border-radius: 4px;")
        remove_btn.clicked.connect(self.remove_color)
        
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px; border-radius: 4px;")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def load_colors(self):
        try:
            file_path = os.path.join("VISO", "data", "colors.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            # Colores por defecto si no existe el archivo
            return [
                "Negro", "Blanco", "Dorado", "Plateado", "Azul", "Verde",
                "Rojo", "Rosa", "Morado", "Marrón", "Gris", "Transparente"
            ]
        except Exception:
            return [
                "Negro", "Blanco", "Dorado", "Plateado", "Azul", "Verde",
                "Rojo", "Rosa", "Morado", "Marrón", "Gris", "Transparente"
            ]
    
    def save_colors(self):
        try:
            file_path = os.path.join("VISO", "data", "colors.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sorted(self.colors), f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron guardar los colores: {str(e)}")
    
    def refresh_colors(self):
        self.color_list.clear()
        self.color_list.addItems(sorted(self.colors))
    
    def add_color(self):
        color = self.color_input.text().strip()
        
        if not color:
            QMessageBox.warning(self, "Error", "Por favor ingresa el nombre del color.")
            return
            
        if color in self.colors:
            QMessageBox.warning(self, "Error", f"El color '{color}' ya existe.")
            return
            
        self.colors.append(color)
        self.save_colors()
        self.refresh_colors()
        self.clear_inputs()
        QMessageBox.information(self, "Éxito", f"Color '{color}' agregado correctamente.")
    
    def remove_color(self):
        current_item = self.color_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Por favor selecciona un color para eliminar.")
            return
            
        color = current_item.text()
        reply = QMessageBox.question(
            self, "Confirmar", 
            f"¿Estás seguro de eliminar el color '{color}'?",
            QMessageBox.Yes | QMessageBox.No
        )
                                   
        if reply == QMessageBox.Yes:
            self.colors.remove(color)
            self.save_colors()
            self.refresh_colors()
            self.clear_inputs()
            QMessageBox.information(self, "Éxito", f"Color '{color}' eliminado correctamente.")
    
    def load_color_details(self, item):
        color = item.text()
        self.color_input.setText(color)
        
    def clear_inputs(self):
        self.color_input.clear()
        self.editing_index = -1
