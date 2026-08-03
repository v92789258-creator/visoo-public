import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QCheckBox
)
from PyQt5.QtCore import Qt

class SizesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = parent.username if parent else None
        self.setup_ui()
        self.load_sizes()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header section with title and add button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("📏 Gestión de Tallas")
        title.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title)

        self.add_btn = QPushButton("➕ Nueva Talla")
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
                background-color: #34495E;
            }
        """)
        self.add_btn.clicked.connect(self.add_size)
        header_layout.addWidget(self.add_btn, alignment=Qt.AlignRight)
        layout.addWidget(header)

        # Search bar
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar talla...")
        self.search_input.textChanged.connect(self.filter_sizes)
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
        self.table.setHorizontalHeaderLabels(["Talla", "Es Lente?", "Acciones"])
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

    def load_sizes(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            sizes_file = os.path.join(base_dir, "VISO", self.username, "data", "sizes.json")
            
            if not os.path.exists(sizes_file):
                os.makedirs(os.path.dirname(sizes_file), exist_ok=True)
                # No crear datos por defecto - dejar que el usuario configure
                sizes = []
                with open(sizes_file, "w", encoding="utf-8") as f:
                    json.dump(sizes, f, ensure_ascii=False, indent=2)
            else:
                with open(sizes_file, "r", encoding="utf-8") as f:
                    sizes = json.load(f)

            self.table.setRowCount(len(sizes))
            for i, size in enumerate(sizes):
                # Handle legacy string format
                if isinstance(size, str):
                    size_data = {"name": size, "is_lens": False}
                else:
                    size_data = size

                # Size name
                name_item = QTableWidgetItem(size_data.get("name", ""))
                self.table.setItem(i, 0, name_item)
                
                # Is lens
                is_lens = size_data.get("is_lens", False)
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
                edit_btn.clicked.connect(lambda _, row=i: self.edit_size(row))
                
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
                delete_btn.clicked.connect(lambda _, row=i: self.delete_size(row))
                
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)
                action_layout.addStretch()
                
                self.table.setCellWidget(i, 2, action_widget)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar tallas: {str(e)}")

    def save_sizes(self, sizes):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            sizes_file = os.path.join(base_dir, "VISO", self.username, "data", "sizes.json")
            
            with open(sizes_file, "w", encoding="utf-8") as f:
                json.dump(sizes, f, ensure_ascii=False, indent=2)
            
            self.load_sizes()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar tallas: {str(e)}")

    def get_sizes(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            sizes_file = os.path.join(base_dir, "VISO", self.username, "data", "sizes.json")
            
            if not os.path.exists(sizes_file):
                return []

            with open(sizes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def add_size(self):
        from gui.dialogs.size_dialog import SizeDialog
        dialog = SizeDialog(self)
        
        if dialog.exec_():
            sizes = self.get_sizes()
            new_size = {
                "name": dialog.name_input.text().strip(),
                "is_lens": dialog.is_lens_check.isChecked()
            }
            sizes.append(new_size)
            self.save_sizes(sizes)

    def edit_size(self, row):
        from gui.dialogs.size_dialog import SizeDialog
        current_size = self.get_sizes()[row]
        dialog = SizeDialog(self, current_size)
        
        if dialog.exec_():
            sizes = self.get_sizes()
            sizes[row] = {
                "name": dialog.name_input.text().strip(),
                "is_lens": dialog.is_lens_check.isChecked()
            }
            self.save_sizes(sizes)

    def delete_size(self, row):
        confirm = QMessageBox.question(
            self, 
            "Confirmar eliminación",
            "¿Está seguro de que desea eliminar esta talla?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            sizes = self.get_sizes()
            sizes.pop(row)
            self.save_sizes(sizes)

    def filter_sizes(self):
        search_text = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            should_show = True
            size_name = self.table.item(row, 0).text().lower()
            
            if search_text and search_text not in size_name:
                should_show = False
                
            self.table.setRowHidden(row, not should_show)