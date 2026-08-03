"""
Widget de loader circular animado para pantallas de transición.
Se muestra mientras se carga una página y luego desaparece automáticamente.
"""

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QPen, QColor, QFont


class CircularLoader(QWidget):
    """
    Widget de loader circular animado con mensaje opcional.
    
    Uso:
        loader = CircularLoader(parent_widget, "Cargando...")
        layout.addWidget(loader)
        
        # El loader se detiene automáticamente después de que cargue todo
        loader.start()
        
        # O detenerlo manualmente
        loader.stop()
    """
    
    animation_stopped = pyqtSignal()
    
    def __init__(self, parent=None, message="Cargando..."):
        super().__init__(parent)
        self.message = message
        self.angle = 0
        self.is_running = False
        
        # Configurar widget
        self.setStyleSheet("background-color: rgba(255, 255, 255, 240);")
        self.setCursor(Qt.WaitCursor)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Label con mensaje
        self.label = QLabel(message)
        self.label.setFont(QFont("Segoe UI", 12))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #333333; margin-top: 20px;")
        
        layout.addStretch()
        # NO agregar 'self' aquí, solo el label
        layout.addWidget(self.label, alignment=Qt.AlignHCenter)
        layout.addStretch()
        
        # Timer para animar el loader
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        
    def start(self):
        """Inicia la animación del loader."""
        if not self.is_running:
            self.is_running = True
            self.show()
            self.timer.start(30)  # 30ms = ~33 FPS
    
    def stop(self):
        """Detiene la animación y oculta el loader."""
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self.timer.disconnect()  # Desconectar todas las señales
            self.hide()
            self.animation_stopped.emit()
    
    def set_message(self, message):
        """Actualiza el mensaje del loader."""
        self.message = message
        self.label.setText(message)
    
    def animate(self):
        """Actualiza el ángulo del loader para animar."""
        self.angle = (self.angle + 6) % 360
        self.update()
    
    def paintEvent(self, event):
        """Dibuja el círculo animado."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Centro del widget
        center_x = self.width() // 2
        center_y = self.height() // 3
        
        # Parámetros del círculo
        radius = 30
        pen_width = 4
        
        # Crear el rectángulo para el arco
        rect = QRect(
            center_x - radius,
            center_y - radius,
            radius * 2,
            radius * 2
        )
        
        # Dibujar el fondo del círculo (gris claro)
        pen_bg = QPen(QColor(230, 230, 230), pen_width)
        pen_bg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, 0, 360 * 16)
        
        # Dibujar el arco animado (azul)
        pen_fg = QPen(QColor(33, 150, 243), pen_width)
        pen_fg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_fg)
        
        # Dibujar arco desde el ángulo actual (120 grados de ancho)
        start_angle = self.angle * 16
        span_angle = 120 * 16
        painter.drawArc(rect, start_angle, span_angle)


class LoaderOverlay(QWidget):
    """
    Overlay transparente que cubre toda la página con un loader circular.
    Ideal para mostrar mientras se cargan los datos.
    
    Uso:
        overlay = LoaderOverlay(page_widget, "Cargando datos...")
        # Se muestra automáticamente
        
        # Cuando termine de cargar:
        overlay.hide_and_remove()
    """
    
    def __init__(self, parent=None, message="Cargando..."):
        super().__init__(parent)
        
        # Configurar overlay
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 230);
            }
        """)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # Layout con loader
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        
        self.loader = CircularLoader(self, message)
        layout.addWidget(self.loader)
        
        # Ajustar al tamaño del padre
        if parent:
            self.resize(parent.size())
        
        self.show()
        self.loader.start()
    
    def resizeEvent(self, event):
        """Asegura que el overlay siempre cubra el parent."""
        super().resizeEvent(event)
        if self.parent():
            self.resize(self.parent().size())
    
    def set_message(self, message):
        """Actualiza el mensaje del loader."""
        self.loader.set_message(message)
    
    def hide_and_remove(self):
        """Oculta el overlay con animación suave."""
        try:
            self.loader.stop()
        except Exception:
            pass
        
        # Animar desaparición
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)
        fade_out.finished.connect(self.hide)
        fade_out.finished.connect(self.deleteLater)
        fade_out.start()
        fade_out.start()


class PageLoadingWidget(QWidget):
    """
    Widget que combina un loader circular con un área para contenido.
    Muestra loader mientras carga y luego el contenido.
    
    Uso:
        loading_widget = PageLoadingWidget()
        layout.addWidget(loading_widget)
        
        # Cargar contenido en background
        loading_widget.start_loading()
        # ... cargar datos ...
        loading_widget.finish_loading()
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Loader circular
        self.loader = CircularLoader(self, "Cargando datos...")
        self.loader.hide()
        
        # Contenedor para el contenido
        self.content_container = QWidget()
        self.content_container.setLayout(QVBoxLayout())
        self.content_container.layout().setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.loader)
        layout.addWidget(self.content_container)
    
    def start_loading(self, message="Cargando datos..."):
        """Muestra el loader."""
        self.loader.set_message(message)
        self.loader.show()
        self.loader.start()
    
    def finish_loading(self):
        """Oculta el loader."""
        self.loader.stop()
        self.loader.hide()
    
    def get_content_layout(self):
        """Retorna el layout del contenedor para agregar widgets."""
        return self.content_container.layout()
    
    def set_content_widget(self, widget):
        """Establece el widget de contenido."""
        layout = self.content_container.layout()
        while layout.count():
            layout.takeAt(0)
        layout.addWidget(widget)
