"""
HomeUIBuilder - Especializado en construcción y estilización de la interfaz

Responsabilidades:
- Crear estructura visual (layouts, frames, widgets)
- Aplicar estilos CSS
- Configurar efectos visuales (sombras, colores)
- NO mezcla lógica de datos
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from gui.widgets.home_page_widget_improved import HomePageWidgetImproved
from utils.file_handler import cargar_nombre_optica


class HomeUIBuilder:
    """Constructor de UI para HomePage.
    
    Separa completamente la construcción visual del procesamiento de datos.
    """
    
    def __init__(self, parent_page):
        self.parent_page = parent_page
        self.username = parent_page.username
        self.home_widget = None
        self.card_frame = None
    
    def build(self):
        """Construye y retorna el contenedor visual completo.
        
        Returns:
            QFrame: Widget raíz con toda la estructura visual
        """
        # Configurar fondo principal
        self._setup_background()
        
        # Crear tarjeta contenedora
        self.card_frame = self._create_card_frame()
        
        # Insertar widget C++ dentro de la tarjeta
        self._insert_home_widget()
        
        return self.card_frame
    
    def _setup_background(self):
        """Configura el fondo/estilo principal del widget padre."""
        self.parent_page.setObjectName("MainBackground")
        self.parent_page.setStyleSheet("""
            QWidget#MainBackground {
                background-color: #ECEFF1;  /* Gris-azulado suave */
            }
        """)
    
    def _create_card_frame(self):
        """Crea el frame "tarjeta" con estilos y sombra.
        
        Returns:
            QFrame: Marco estilizado
        """
        card = QFrame()
        card.setObjectName("CardFrame")
        
        # Estilos: blanco, bordes redondos, borde sutil
        card.setStyleSheet("""
            QFrame#CardFrame {
                background-color: #FFFFFF;
                border-radius: 15px;
                border: 1px solid #E0E0E0;
            }
        """)
        
        # Efecto de sombra elegante
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 40))  # Negro semitransparente
        card.setGraphicsEffect(shadow)
        
        # Layout interno
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        return card
    
    def _insert_home_widget(self):
        """Inserta el widget C++ HomePageWidgetImproved dentro de la tarjeta."""
        # Crear instancia del widget C++
        optica_name = cargar_nombre_optica(self.username) or "VISO"
        
        self.home_widget = HomePageWidgetImproved(
            optica_name=optica_name,
            username=self.username,
            parent=self.card_frame,
            parent_window=self.parent_page.parent_app
        )
        
        # Intentar hacer transparente para que herede el blanco de la tarjeta
        self.home_widget.setStyleSheet("background: transparent;")
        self.home_widget.setAttribute(Qt.WA_TranslucentBackground)
        
        # Añadir al layout de la tarjeta
        self.card_frame.layout().addWidget(self.home_widget)
