"""
Diálogo para seleccionar el formato del reporte de ventas.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
)
from PyQt5.QtGui import QFont, QColor, QPixmap
from PyQt5.QtCore import Qt, QSize


class ReporteFormatoDialog(QDialog):
    """Diálogo para seleccionar formato del reporte de ventas."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_format = None
        self.setup_ui()
        self.setWindowTitle("Seleccionar Formato de Reporte")
        self.setModal(True)
        self.resize(600, 350)
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # Título
        title = QLabel("Selecciona el Formato del Reporte")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2C3E50;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Subtítulo
        subtitle = QLabel("Elige cómo deseas que se vea tu reporte de ventas")
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7F8C8D;
            }
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle)
        
        # Espaciador
        main_layout.addSpacing(10)
        
        # Contenedor de opciones
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)
        
        # Opción 1: Con Diseño
        con_diseño = self.create_option_card(
            title="✨ Con Diseño",
            description="Reporte formateado y profesional\ncon colores y estilos",
            icon="🎨",
            option_value="con_diseño"
        )
        options_layout.addWidget(con_diseño)
        
        # Opción 2: Sin Diseño
        sin_diseño = self.create_option_card(
            title="📋 Sin Diseño",
            description="Reporte simple y limpio\nsin estilos",
            icon="📄",
            option_value="sin_diseño"
        )
        options_layout.addWidget(sin_diseño)
        
        main_layout.addLayout(options_layout, 1)
        
        # Espaciador
        main_layout.addSpacing(10)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedSize(100, 40)
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background: #E8E8E8;
                color: #2C3E50;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #D0D0D0;
            }
            QPushButton:pressed {
                background: #B0B0B0;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancelar)
        
        main_layout.addLayout(buttons_layout)
    
    def create_option_card(self, title, description, icon, option_value):
        """Crea una tarjeta de opción clickeable."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #E0E0E0;
                border-radius: 12px;
                padding: 20px;
            }
            QFrame:hover {
                border: 2px solid #3498DB;
                background: #F8FBFF;
            }
        """)
        card.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Icono
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Título
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2C3E50;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #7F8C8D;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Almacenar el valor de opción
        card.option_value = option_value
        
        # Hacer la tarjeta clickeable
        def on_click():
            self.selected_format = option_value
            self.accept()
        
        card.mousePressEvent = lambda event: on_click()
        
        return card
