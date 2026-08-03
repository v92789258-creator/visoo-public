import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from ..dialogs.material_dialog import MaterialDialog
from utils.data_handler import load_materials, save_materials
from utils.file_handler import SESION_FILE

class MaterialsPage(QWidget):
    data_changed = pyqtSignal()  # Signal to notify when data changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.materials = []
        # Resolver username de forma robusta: preferir parent.username, caer
        # de forma segura a la sesión o al primer usuario disponible en VISO/
        self.username = getattr(parent, 'username', None)
        if not self.username:
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                # Intentar leer archivo de sesión para obtener user_id
                if SESION_FILE and os.path.exists(str(SESION_FILE)):
                    try:
                        with open(str(SESION_FILE), 'r', encoding='utf-8') as sf:
                            user_id = sf.read().strip()
                        usuarios_path = os.path.join(base_dir, 'VISO', '.usuarios.json')
                        if os.path.exists(usuarios_path):
                            with open(usuarios_path, 'r', encoding='utf-8') as uf:
                                usuarios = json.load(uf)
                            user_data = usuarios.get(user_id)
                            if isinstance(user_data, dict) and user_data.get('username'):
                                self.username = user_data.get('username')
                            else:
                                # fallback a usar user_id si no hay username
                                self.username = user_id
                    except Exception:
                        self.username = None
                # Si no hay sesión, intentar detectar el primer usuario en VISO/
                if not self.username:
                    viso_dir = os.path.join(base_dir, 'VISO')
                    try:
                        candidates = [d for d in os.listdir(viso_dir) if os.path.isdir(os.path.join(viso_dir, d))]
                        # Excluir known files
                        candidates = [c for c in candidates if c not in ('.usuarios.json', 'data', 'images', 'temp')]
                        if candidates:
                            self.username = candidates[0]
                    except Exception:
                        self.username = None
            except Exception:
                self.username = None

        self.setup_ui()
        # Compatibilidad: cargar materiales al inicializar (usa self.username resuelto)
        self.load_materials()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header section with title and add button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("🎯 Gestión de Materiales")
        title.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title)

        self.add_btn = QPushButton("➕ Nuevo Material")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #191919;
            }
        """)
        self.add_btn.clicked.connect(self.add_material)
        header_layout.addWidget(self.add_btn, alignment=Qt.AlignRight)
        layout.addWidget(header)

        # Search bar
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("")
        self.search_input.textChanged.connect(self.filter_materials)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #191919;
            }
        """)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_container)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Material", "Es Lente?", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setDefaultSectionSize(100)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #333333;
                border: 1px solid #ddd;
                border-radius: 4px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
                color: #333333;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #333333;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)

    def load_materials(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            materials_file = os.path.join(base_dir, "VISO", self.username, "data", "materials.json")
            
            if not os.path.exists(materials_file):
                os.makedirs(os.path.dirname(materials_file), exist_ok=True)
                # Crear archivo vacío sin materiales por defecto
                default_materials = []
                with open(materials_file, "w", encoding="utf-8") as f:
                    json.dump(default_materials, f, ensure_ascii=False, indent=2)
                materials = default_materials
            else:
                with open(materials_file, "r", encoding="utf-8") as f:
                    materials = json.load(f)

            self.table.setRowCount(len(materials))
            for i, material in enumerate(materials):
                # Handle legacy string format
                if isinstance(material, str):
                    material_data = {"name": material, "is_lens": True}
                else:
                    material_data = material
                
                # Material name
                name_item = QTableWidgetItem(material_data.get("name", ""))
                self.table.setItem(i, 0, name_item)
                
                # Is lens checkbox
                is_lens = material_data.get("is_lens", True)
                is_lens_text = "Sí" if is_lens else "No"
                is_lens_item = QTableWidgetItem(is_lens_text)
                is_lens_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 1, is_lens_item)
                
                # Action buttons container
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(4, 4, 4, 4)
                action_layout.setSpacing(8)

                edit_btn = QPushButton("✏️")
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFC107;
                        border: none;
                        border-radius: 4px;
                        padding: 4px 8px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #FFA000;
                    }
                """)
                edit_btn.clicked.connect(lambda _, row=i: self.edit_material(row))
                
                delete_btn = QPushButton(" ")
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F44336;
                        border: none;
                        border-radius: 4px;
                        padding: 4px 8px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #D32F2F;
                    }
                """)
                delete_btn.clicked.connect(lambda _, row=i: self.delete_material(row))
                
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)
                action_layout.addStretch()
                
                self.table.setCellWidget(i, 2, action_widget)

        except Exception as e:
            # Silenciosamente manejar el error sin mostrar diálogo
            print(f"[DEBUG] Error al cargar materiales: {str(e)}")

    def save_materials(self, materials):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            materials_file = os.path.join(base_dir, "VISO", self.username, "data", "materials.json")
            
            with open(materials_file, "w", encoding="utf-8") as f:
                json.dump(materials, f, ensure_ascii=False, indent=2)
            
            self.load_materials()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar materiales: {str(e)}")

    # Alias para compatibilidad con código que espera `load_data()`
    def load_data(self):
        return self.load_materials()

    def get_materials(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            materials_file = os.path.join(base_dir, "VISO", self.username, "data", "materials.json")
            
            if not os.path.exists(materials_file):
                return []

            with open(materials_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def add_material(self):
        from gui.dialogs.material_dialog import MaterialDialog
        dialog = MaterialDialog(self)
        
        if dialog.exec_():
            materials = self.get_materials()
            new_material = {
                "name": dialog.name_input.text().strip(),
                "is_lens": dialog.is_lens_check.isChecked()
            }
            materials.append(new_material)
            self.save_materials(materials)

    def edit_material(self, row):
        from gui.dialogs.material_dialog import MaterialDialog
        current_material = self.get_materials()[row]
        dialog = MaterialDialog(self, current_material)
        
        if dialog.exec_():
            materials = self.get_materials()
            materials[row] = {
                "name": dialog.name_input.text().strip(),
                "is_lens": dialog.is_lens_check.isChecked()
            }
            self.save_materials(materials)

    def delete_material(self, row):
        confirm = QMessageBox.question(
            self, 
            "Confirmar eliminación",
            "¿Está seguro de que desea eliminar este material?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            materials = self.get_materials()
            materials.pop(row)
            self.save_materials(materials)

    def filter_materials(self):
        search_text = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            should_show = True
            material_name = self.table.item(row, 0).text().lower()
            
            if search_text and search_text not in material_name:
                should_show = False
                
            self.table.setRowHidden(row, not should_show)