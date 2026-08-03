from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLabel, QFrame, QHBoxLayout, QPushButton, QCheckBox, QMessageBox
from PyQt5.QtCore import Qt
import os
import sys

# Agregar la ruta base
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.file_handler import is_modo_basico, set_modo_basico

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = getattr(parent, "username", "Usuario")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Título
        title = QLabel("Configuración")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1976d2; margin-bottom: 10px;")
        layout.addWidget(title)

        # Modos
        modos_group = QGroupBox("Modos de Visualización")
        modos_group.setStyleSheet("""
            QGroupBox {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 16px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #2C2C2C;
                padding: 8px;
            }
        """)
        modos_layout = QVBoxLayout(modos_group)

        self.checkbox_modo_basico = QCheckBox("Activar Modo Básico")
        self.checkbox_modo_basico.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #333333;
                padding: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        
        # Cargar estado
        self.checkbox_modo_basico.setChecked(is_modo_basico(self.username))
        self.checkbox_modo_basico.toggled.connect(self._toggle_modo_basico)
        modos_layout.addWidget(self.checkbox_modo_basico)

        modos_info = QLabel("El Modo Básico simplifica la interfaz para usuarios de la tercera edad o sin experiencia tecnológica. Oculta módulos complejos y presenta una pantalla de inicio fácil de usar.")
        modos_info.setWordWrap(True)
        modos_info.setStyleSheet("color: #666; font-size: 12px; margin-left: 30px;")
        modos_layout.addWidget(modos_info)

        layout.addWidget(modos_group)

        # Términos de Uso
        terms_group = QGroupBox("Términos de Uso")
        terms_group.setStyleSheet("""
            QGroupBox {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 16px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #2C2C2C;
                padding: 8px;
            }
        """)
        terms_layout = QVBoxLayout(terms_group)

        terms_info = QLabel(
            "Al utilizar esta aplicación, aceptas automáticamente nuestros Términos y Condiciones.\n\n"
            "📋 Términos y Condiciones Principales:\n\n"
            "• El software es propietario y está protegido por derechos de autor.\n"
            "• Se prohíbe la distribución, modificación o venta sin autorización.\n"
            "• Los datos de los usuarios son confidenciales y protegidos.\n"
            "• El proveedor no es responsable por pérdida de datos.\n"
            "• El acceso está limitado a usuarios autorizados.\n"
            "• Cualquier uso indebido resultará en cancelación de acceso.\n"
            "• Se registran todas las actividades para auditoría.\n"
            "• Actualizaciones pueden cambiar términos en cualquier momento.\n"
        )
        terms_info.setWordWrap(True)
        terms_info.setStyleSheet("""
            QLabel {
                color: #424242;
                font-size: 11px;
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 4px;
                padding: 12px;
                line-height: 1.5;
            }
        """)
        terms_layout.addWidget(terms_info)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #E0E0E0;")
        terms_layout.addWidget(separator)

        acceptance_widget = QWidget()
        acceptance_layout = QHBoxLayout(acceptance_widget)
        acceptance_layout.setContentsMargins(0, 0, 0, 0)

        self.terms_accepted_checkbox = QPushButton("✓ Acepto los Términos y Condiciones")
        self.terms_accepted_checkbox.setCheckable(True)
        self.terms_accepted_checkbox.setChecked(True)
        self.terms_accepted_checkbox.setStyleSheet("""
            QPushButton {
                background-color: #191919;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.terms_accepted_checkbox.setFlat(True)
        acceptance_layout.addWidget(self.terms_accepted_checkbox)
        acceptance_layout.addStretch()

        terms_layout.addWidget(acceptance_widget)

        confirmation_text = QLabel(
            "⚠️ Al continuar usando esta aplicación, confirmas que has leído y aceptas estos términos."
        )
        confirmation_text.setWordWrap(True)
        confirmation_text.setStyleSheet("""
            QLabel {
                color: #D32F2F;
                font-size: 10px;
                font-weight: bold;
                padding: 8px 0px;
                border-top: 1px solid #E0E0E0;
                margin-top: 8px;
            }
        """)
        terms_layout.addWidget(confirmation_text)

        layout.addWidget(terms_group)

        # Plantilla
        template_group = QGroupBox("Plantilla")
        template_group.setStyleSheet("""
            QGroupBox {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 16px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #2C2C2C;
                padding: 8px;
            }
        """)
        template_layout = QVBoxLayout(template_group)

        template_placeholder = QLabel("Configuración de plantilla")
        template_placeholder.setWordWrap(True)
        template_placeholder.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 12px;
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 4px;
                padding: 30px;
                text-align: center;
            }
        """)
        template_layout.addWidget(template_placeholder)

        layout.addWidget(template_group)
        layout.addStretch()

    def _toggle_modo_basico(self, checked):
        set_modo_basico(self.username, checked)
        if checked:
            QMessageBox.information(self, 'Modo B�sico', 'Modo B�sico activado. Por favor, reinicie la aplicaci�n para ver los cambios.')
        else:
            QMessageBox.information(self, 'Modo Normal', 'Modo B�sico desactivado. Por favor, reinicie la aplicaci�n para volver al modo normal.')
