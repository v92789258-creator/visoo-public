import sys
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Importa las funciones para guardar la clave y validar la API
from utils.file_handler import guardar_clave_activacion
from utils.api_handler import validar_clave_activacion_api

class ActivationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activar Licencia")
    # self.setFixedSize(400, 200)  # Eliminado para responsividad
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.CustomizeWindowHint)
        
        # Establecer ícono de la ventana
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        title_label = QLabel("<b>Activar Licencia del Sistema</b>")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        form_layout = QFormLayout()
        self.clave_entry = QLineEdit()
        self.clave_entry.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        form_layout.addRow("Clave de activación:", self.clave_entry)
        main_layout.addLayout(form_layout)

        activate_button = QPushButton("Activar")
        activate_button.clicked.connect(self.activar)
        main_layout.addWidget(activate_button)

    def activar(self):
        clave = self.clave_entry.text().strip()

        if validar_clave_activacion_api(clave):
            guardar_clave_activacion(clave)
            QMessageBox.information(self, "Éxito", "¡Licencia activada correctamente!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Clave de activación incorrecta. Inténtalo de nuevo.")