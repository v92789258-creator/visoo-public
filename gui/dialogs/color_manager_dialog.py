from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QMessageBox, QListWidgetItem
)
from PyQt5.QtCore import Qt
import json
import os


class ColorManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Inicializar colors antes de setup_ui
        self.colors = []
        self.setup_ui()
        # Recargar colores desde archivo
        self.load_colors_from_file()
        
    def setup_ui(self):
        self.setWindowTitle("Gestor de Colores")
        self.setMinimumWidth(400)
        self.setMinimumHeight(350)
        layout = QVBoxLayout(self)
        
        # Campo de entrada
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Nuevo Color:"))
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("Ej: Negro, Azul, Dorado...")
        self.color_input.returnPressed.connect(self.add_color)
        input_layout.addWidget(self.color_input)
        layout.addLayout(input_layout)
        
        # Botón de agregar
        add_btn = QPushButton("➕ Agregar Color")
        add_btn.clicked.connect(self.add_color)
        layout.addWidget(add_btn)
        
        # Lista de colores
        layout.addWidget(QLabel("Colores disponibles:"))
        self.color_list = QListWidget()
        self.color_list.setSelectionMode(QListWidget.SingleSelection)
        self.refresh_colors()
        layout.addWidget(self.color_list)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        
        delete_btn = QPushButton("  Eliminar")
        delete_btn.clicked.connect(self.delete_color)
        button_layout.addWidget(delete_btn)
        
        close_btn = QPushButton("✓ Cerrar")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def load_colors_from_file(self):
        """Carga colores desde el archivo JSON."""
        file_path = os.path.join("VISO", "data", "colors.json")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.colors = json.load(f)
            else:
                self.colors = ["Blanco", "Negro"]
        except Exception as e:
            print(f"Error cargando colores: {e}")
            self.colors = ["Blanco", "Negro"]
        self.refresh_colors()
    
    def load_colors(self):
        """Carga colores desde JSON (legacy)."""
        file_path = os.path.join("VISO", "data", "colors.json")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return ["Blanco", "Negro"]
        except Exception as e:
            print(f"Error cargando colores: {e}")
            return ["Blanco", "Negro"]
    
    def save_colors(self):
        """Guarda colores a JSON."""
        file_path = os.path.join("VISO", "data", "colors.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sorted(self.colors), f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar colores: {str(e)}")
    
    def refresh_colors(self):
        """Actualiza la lista de colores."""
        self.color_list.clear()
        for color in sorted(self.colors):
            self.color_list.addItem(color)
    
    def add_color(self):
        """Agrega un nuevo color."""
        color = self.color_input.text().strip()
        if not color:
            QMessageBox.warning(self, "Error", "El nombre del color no puede estar vacío.")
            return
        
        if color in self.colors:
            QMessageBox.warning(self, "Error", f"El color '{color}' ya existe.")
            return
        
        self.colors.append(color)
        self.save_colors()
        self.refresh_colors()
        self.color_input.clear()
        QMessageBox.information(self, "Éxito", f"Color '{color}' agregado correctamente.")
        self.color_input.clear()
        QMessageBox.information(self, "Éxito", f"Color '{color}' agregado correctamente.")
    
    def delete_color(self):
        """Elimina el color seleccionado."""
        current_item = self.color_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Selecciona un color para eliminar.")
            return
        
        color = current_item.text()
        reply = QMessageBox.question(
            self, 
            "Confirmar eliminación", 
            f"¿Estás seguro de que quieres eliminar '{color}'?"
        )
        
        if reply == QMessageBox.Yes:
            self.colors.remove(color)
            self.save_colors()
            self.refresh_colors()
            QMessageBox.information(self, "Éxito", f"Color '{color}' eliminado correctamente.")
