from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QMessageBox, QListWidgetItem
)
from PyQt5.QtCore import Qt
import json
import os


class MaterialManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Obtener username desde el parent (producto dialog)
        self.username = self._get_username_from_parent(parent)
        # Inicializar materials antes de setup_ui
        self.materials = []
        self.setup_ui()
        # Recargar materiales desde archivo
        self.load_materials_from_file()
    
    def _get_username_from_parent(self, parent):
        """Obtiene el username desde el parent chain."""
        current = parent
        while current:
            if hasattr(current, 'username'):
                return current.username
            current = current.parent() if hasattr(current, 'parent') else None
        return None
        
    def setup_ui(self):
        self.setWindowTitle("Gestor de Materiales")
        self.setMinimumWidth(400)
        self.setMinimumHeight(350)
        layout = QVBoxLayout(self)
        
        # Campo de entrada
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Nuevo Material:"))
        self.material_input = QLineEdit()
        self.material_input.setPlaceholderText("Ej: Acetato, Metal, Policarbonato...")
        self.material_input.returnPressed.connect(self.add_material)
        input_layout.addWidget(self.material_input)
        layout.addLayout(input_layout)
        
        # Botón de agregar
        add_btn = QPushButton("➕ Agregar Material")
        add_btn.clicked.connect(self.add_material)
        layout.addWidget(add_btn)
        
        # Lista de materiales
        layout.addWidget(QLabel("Materiales disponibles:"))
        self.material_list = QListWidget()
        self.material_list.setSelectionMode(QListWidget.SingleSelection)
        self.refresh_materials()
        layout.addWidget(self.material_list)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        
        delete_btn = QPushButton("  Eliminar")
        delete_btn.clicked.connect(self.delete_material)
        button_layout.addWidget(delete_btn)
        
        close_btn = QPushButton("✓ Cerrar")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def load_materials_from_file(self):
        """Carga materiales desde el archivo JSON del usuario o global."""
        try:
            # Intentar cargar del archivo del usuario primero
            if self.username:
                user_file_path = os.path.join("VISO", self.username, "data", "materials.json")
                if os.path.exists(user_file_path):
                    try:
                        with open(user_file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Manejar ambas estructuras: lista de strings o lista de objetos
                            self.materials = self._extract_material_names(data)
                        self.refresh_materials()
                        return
                    except Exception as e:
                        print(f"Error cargando materiales del usuario: {e}")
            
            # Fallback: cargar del archivo global
            file_path = os.path.join("VISO", "data", "materials.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.materials = self._extract_material_names(data)
                except Exception as e:
                    print(f"Error cargando materiales global: {e}")
                    self.materials = ["Acetato", "Metal", "Policarbonato", "Resina", "Titanio", "Nylon", "Madera"]
            else:
                self.materials = ["Acetato", "Metal", "Policarbonato", "Resina", "Titanio", "Nylon", "Madera"]
        except Exception as e:
            print(f"Error en load_materials_from_file: {e}")
            self.materials = ["Acetato", "Metal", "Policarbonato", "Resina", "Titanio", "Nylon", "Madera"]
        finally:
            self.refresh_materials()
    
    def _extract_material_names(self, data):
        """Extrae nombres de materiales de diferentes estructuras JSON."""
        if not data:
            return []
        
        try:
            if not isinstance(data, list):
                print(f"[WARNING] data no es lista, es {type(data)}")
                return []
            
            result = []
            for i, item in enumerate(data):
                try:
                    if isinstance(item, dict):
                        # Objeto con campos
                        name = item.get('name', '')
                        if isinstance(name, str) and name:
                            result.append(name)
                    elif isinstance(item, str):
                        # String simple
                        if item:
                            result.append(item)
                except Exception as item_error:
                    print(f"[WARNING] Error en item {i}: {item_error}")
                    continue
            
            return result
        except Exception as e:
            print(f"[ERROR] Error en _extract_material_names: {e}")
            return []
    
    def load_materials(self):
        """Carga materiales desde JSON."""
        file_path = os.path.join("VISO", "data", "materials.json")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return self._extract_material_names(data)
            return ["Acetato", "Metal", "Policarbonato", "Resina", "Titanio", "Nylon", "Madera"]
        except Exception as e:
            print(f"Error cargando materiales: {e}")
            return ["Acetato", "Metal", "Policarbonato", "Resina", "Titanio", "Nylon", "Madera"]
    
    def save_materials(self):
        """Guarda materiales a JSON del usuario o global."""
        # Guardar en el archivo del usuario si existe el username
        if self.username:
            file_path = os.path.join("VISO", self.username, "data", "materials.json")
        else:
            file_path = os.path.join("VISO", "data", "materials.json")
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sorted(self.materials), f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar materiales: {str(e)}")
    
    def refresh_materials(self):
        """Actualiza la lista de materiales."""
        if not hasattr(self, 'material_list'):
            return
        materials = getattr(self, 'materials', []) or []
        self.material_list.clear()
        for material in sorted(materials):
            self.material_list.addItem(material)
    
    def add_material(self):
        """Agrega un nuevo material."""
        material = self.material_input.text().strip()
        if not material:
            QMessageBox.warning(self, "Error", "El nombre del material no puede estar vacío.")
            return
        
        if material in self.materials:
            QMessageBox.warning(self, "Error", f"El material '{material}' ya existe.")
            return
        
        self.materials.append(material)
        self.save_materials()
        self.refresh_materials()
        self.material_input.clear()
        QMessageBox.information(self, "Éxito", f"Material '{material}' agregado correctamente.")
    
    def delete_material(self):
        """Elimina el material seleccionado."""
        current_item = self.material_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Selecciona un material para eliminar.")
            return
        
        material = current_item.text()
        reply = QMessageBox.question(
            self, 
            "Confirmar eliminación", 
            f"¿Estás seguro de que quieres eliminar '{material}'?"
        )
        
        if reply == QMessageBox.Yes:
            self.materials.remove(material)
            self.save_materials()
            self.refresh_materials()
            QMessageBox.information(self, "Éxito", f"Material '{material}' eliminado correctamente.")
