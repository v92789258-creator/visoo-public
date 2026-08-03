"""
Módulo para la pantalla de selección de plantillas.
Interfaz de usuario para elegir y configurar plantillas de boletas.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla


class PlantillaCard(QGroupBox):
    """Tarjeta individual para una plantilla."""
    
    def __init__(self, titulo, descripcion, icono, on_select):
        super().__init__()
        self.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                margin-top: 0px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        titulo_label = QLabel(f"{icono} {titulo}")
        titulo_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1976D2;")
        layout.addWidget(titulo_label)
        
        # Descripción
        desc_label = QLabel(descripcion)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 13px;")
        layout.addWidget(desc_label)
        
        # Separador
        separator = QGroupBox()
        separator.setStyleSheet("background-color: #e0e0e0;")
        separator.setMaximumHeight(1)
        layout.addWidget(separator)
        
        # Botón
        self.button = QPushButton("Seleccionar")
        self.button.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1976D2;
            }
        """)
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(on_select)
        layout.addWidget(self.button)
    
    def set_seleccionada(self):
        """Marca la tarjeta como seleccionada."""
        self.button.setText("✓ Seleccionada")
        self.button.setStyleSheet("""
            QPushButton {
                background: #757575;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #616161;
            }
        """)
    
    def set_no_seleccionada(self):
        """Marca la tarjeta como no seleccionada."""
        self.button.setText("Seleccionar")
        self.button.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1976D2;
            }
        """)


class PanelPlantillas(QWidget):
    """Panel de selección de plantillas."""
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.generador = GeneradorBoletasPlantilla(username)
        self.plantilla_actual = self.generador.plantilla_seleccionada
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Título
        titulo = QLabel("<h2>Plantilla</h2>")
        titulo.setStyleSheet("color: #1976D2;")
        layout.addWidget(titulo)
        
        # Contenedor de tarjetas
        cards_container = QWidget()
        cards_layout = QHBoxLayout(cards_container)
        cards_layout.setSpacing(15)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear tarjetas
        self.cards = {}
        
        plantillas_config = [
            {
                'id': 'pequeña',
                'titulo': 'Diseño Pequeño',
                'icono': '📋',
                'descripcion': 'Plantilla de boleta compacta y condensada para impresoras térmicas.',
            },
            {
                'id': 'larga',
                'titulo': 'Diseño Larga',
                'icono': '📜',
                'descripcion': 'Plantilla de boleta más amplia con detalles completos para impresoras térmicas.',
            },
            {
                'id': 'extra_larga',
                'titulo': 'Diseño Extra Largo',
                'icono': '📑',
                'descripcion': 'Plantilla de boleta con formato completo y detallado con toda la información disponible.',
            },
            {
                'id': 'a4',
                'titulo': 'Diseño A4',
                'icono': '📄',
                'descripcion': 'Plantilla de boleta en formato A4 con toda la información disponible para impresoras convencionales.',
            },
        ]
        
        for config in plantillas_config:
            card = PlantillaCard(
                config['titulo'],
                config['descripcion'],
                config['icono'],
                lambda pid=config['id']: self.seleccionar_plantilla(pid)
            )
            
            if config['id'] == self.plantilla_actual:
                card.set_seleccionada()
            
            cards_layout.addWidget(card)
            self.cards[config['id']] = card
        
        layout.addWidget(cards_container)
        layout.addStretch()
    
    def seleccionar_plantilla(self, tipo_plantilla):
        """Selecciona una plantilla y actualiza la UI."""
        self.generador.guardar_plantilla_seleccionada(tipo_plantilla)
        
        # Actualizar UI
        for plantilla_id, card in self.cards.items():
            if plantilla_id == tipo_plantilla:
                card.set_seleccionada()
            else:
                card.set_no_seleccionada()
        
        self.plantilla_actual = tipo_plantilla
        
        # Mostrar mensaje
        from PyQt5.QtWidgets import QMessageBox
        nombres_plantillas = {
            'pequeña': '📋 Diseño Pequeño',
            'larga': '📜 Diseño Larga',
            'extra_larga': '📑 Diseño Extra Largo',
            'a4': '📄 Diseño A4'
        }
        
        nombre = nombres_plantillas.get(tipo_plantilla, tipo_plantilla)
        QMessageBox.information(
            self,
            "Plantilla Seleccionada",
            f"✓ {nombre} ha sido seleccionada correctamente.\n\n"
            f"Las nuevas boletas se generarán con este formato."
        )
