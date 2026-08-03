from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QCheckBox, QWidget
)
from PyQt5.QtCore import Qt

class SizeDialog(QDialog):
    def __init__(self, parent=None, size=None):
        super().__init__(parent)
        self.size = size
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Talla" if not self.size else "Editar Talla")
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Size name
        name_label = QLabel("Nombre de la talla:")
        name_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: S, M, L, XL, 52, 54, etc.")
        if self.size:
            self.name_input.setText(self.size["name"])
        self.name_input.setStyleSheet("""
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
        layout.addWidget(self.name_input)

        # Is lens checkbox
        self.is_lens_check = QCheckBox("Es una talla para lentes")
        if self.size is None:  # New size
            self.is_lens_check.setChecked(False)  # Default to False for new sizes
        else:
            self.is_lens_check.setChecked(self.size.get("is_lens", False))
        self.is_lens_check.setStyleSheet("""
            QCheckBox {
                color: #2C3E50;
                font-size: 13px;
                padding: 4px 0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #191919;
                border-radius: 4px;
                background: #191919;
            }
        """)
        layout.addWidget(self.is_lens_check)

        # Buttons
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 8, 0, 0)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #F8F9FA;
                color: #6C757D;
                border: 1px solid #DEE2E6;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E9ECEF;
                border-color: #CED4DA;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Guardar")
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #191919;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #191919;
            }
        """)
        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)

        layout.addWidget(btn_container)

    def accept(self):
        if not self.name_input.text().strip():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Error",
                "El nombre de la talla no puede estar vacío."
            )
            return
        super().accept()