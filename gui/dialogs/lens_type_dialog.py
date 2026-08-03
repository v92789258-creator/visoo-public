from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QTextEdit, QWidget
)
from PyQt5.QtCore import Qt

class LensTypeDialog(QDialog):
    def __init__(self, parent=None, lens_type=None):
        super().__init__(parent)
        self.lens_type = lens_type
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Tipo de Lente" if not self.lens_type else "Editar Tipo de Lente")
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Name
        name_label = QLabel("Nombre:")
        name_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Monofocal, Bifocal, etc.")
        if self.lens_type:
            self.name_input.setText(self.lens_type["name"])
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

        # Description
        desc_label = QLabel("Descripción:")
        desc_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 13px;
                font-weight: bold;
                margin-top: 8px;
            }
        """)
        layout.addWidget(desc_label)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Describe las características de este tipo de lente...")
        if self.lens_type:
            self.desc_input.setText(self.lens_type["description"])
        self.desc_input.setStyleSheet("""
            QTextEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QTextEdit:focus {
                border-color: #4CAF50;
            }
        """)
        self.desc_input.setFixedHeight(100)
        layout.addWidget(self.desc_input)

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
                "El nombre del tipo de lente no puede estar vacío."
            )
            return
        super().accept()