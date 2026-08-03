import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QMessageBox,
    QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from ..dialogs.lens_type_dialog import LensTypeDialog

class LensTypesPage(QWidget):
    data_changed = pyqtSignal()  # Signal to notify when data changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Buttons Container
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        # Add Button
        add_btn = QPushButton("+ Agregar Tipo de Lente")
        add_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #2C3E50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #34495E;
            }
        """)
        add_btn.clicked.connect(self.add_lens_type)
        btn_layout.addWidget(add_btn)

        # Add spacer to push button to the left
        btn_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addWidget(btn_container)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)  # ID, Name, Description
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Descripción"])
        
        # Style the table
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #212529;
                border: 1px solid #ddd;
                border-radius: 4px;
                gridline-color: #ddd;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
                color: #495057;
            }
            QTableWidget::item {
                padding: 8px;
                color: #212529;
            }
            QTableWidget::item:selected {
                background-color: #e9ecef;
                color: #212529;
            }
        """)
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Description
        self.table.setColumnWidth(0, 50)  # ID width
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.edit_lens_type)
        
        layout.addWidget(self.table)

        # Delete button
        delete_btn = QPushButton("Eliminar Seleccionado")
        delete_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        delete_btn.clicked.connect(self.delete_lens_type)
        layout.addWidget(delete_btn)

    def load_data(self):
        try:
            data_path = os.path.join("VISO", "data", "lens_types.json")
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    self.lens_types = []
                    if isinstance(data, list):
                        for i, item in enumerate(data):
                            if isinstance(item, str):
                                # Convert legacy string to object
                                self.lens_types.append({
                                    "id": i + 1,
                                    "name": item,
                                    "description": ""
                                })
                            elif isinstance(item, dict):
                                self.lens_types.append(item)
            else:
                # No crear datos por defecto - dejar que el usuario configure
                self.lens_types = []
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar los datos: {str(e)}")
            self.lens_types = []
        
        self.update_table()

    def save_data(self):
        try:
            os.makedirs(os.path.join("VISO", "data"), exist_ok=True)
            with open(os.path.join("VISO", "data", "lens_types.json"), 'w', encoding='utf-8') as f:
                json.dump(self.lens_types, f, indent=2, ensure_ascii=False)
            self.data_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar los datos: {str(e)}")

    def update_table(self):
        self.table.setRowCount(0)
        for lens_type in sorted(self.lens_types, key=lambda x: x["name"]):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # ID
            id_item = QTableWidgetItem(str(lens_type["id"]))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, id_item)
            
            # Name
            name_item = QTableWidgetItem(lens_type["name"])
            self.table.setItem(row, 1, name_item)
            
            # Description
            desc_item = QTableWidgetItem(lens_type["description"])
            self.table.setItem(row, 2, desc_item)

    def get_next_id(self):
        if not self.lens_types:
            return 1
        return max(t["id"] for t in self.lens_types) + 1

    def add_lens_type(self):
        dialog = LensTypeDialog(self)
        if dialog.exec_():
            name = dialog.name_input.text().strip()
            
            # Check for duplicates
            if any(t["name"].lower() == name.lower() for t in self.lens_types):
                QMessageBox.warning(self, "Error", "Ya existe un tipo de lente con ese nombre.")
                return
            
            new_type = {
                "id": self.get_next_id(),
                "name": name,
                "description": dialog.desc_input.toPlainText().strip()
            }
            self.lens_types.append(new_type)
            self.save_data()
            self.update_table()

    def edit_lens_type(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        lens_type_id = int(self.table.item(current_row, 0).text())
        lens_type = next((t for t in self.lens_types if t["id"] == lens_type_id), None)
        if not lens_type:
            return

        dialog = LensTypeDialog(self, lens_type)
        if dialog.exec_():
            new_name = dialog.name_input.text().strip()
            
            # Check for duplicates, excluding current item
            if any(t["name"].lower() == new_name.lower() and t["id"] != lens_type["id"] 
                  for t in self.lens_types):
                QMessageBox.warning(self, "Error", "Ya existe un tipo de lente con ese nombre.")
                return
            
            lens_type["name"] = new_name
            lens_type["description"] = dialog.desc_input.toPlainText().strip()
            self.save_data()
            self.update_table()

    def delete_lens_type(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Por favor seleccione un tipo de lente para eliminar.")
            return

        lens_type = self.lens_types[current_row]
        reply = QMessageBox.question(
            self, 
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar el tipo de lente '{lens_type['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.lens_types.pop(current_row)
            self.save_data()
            self.update_table()

    def get_lens_type_by_id(self, id):
        return next((t for t in self.lens_types if t["id"] == id), None)

    def get_all_lens_types(self):
        return self.lens_types.copy()