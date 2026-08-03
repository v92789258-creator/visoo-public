"""
Widget de loader circular animado para mostrar durante la carga de datos.
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import pyqtSignal
import math


class AnimatedCircleLoader(QWidget):
    """Loader circular animado que gira mientras se cargan datos."""
    
    def __init__(self, parent=None, size=60):
        super().__init__(parent)
        self.size = size
        self.rotation = 0
        self.is_loading = False
        
        # Timer para la animación
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_rotation)
        self.timer.setInterval(50)  # 50ms = 20fps
        
        self.setFixedSize(size, size)
        self.setStyleSheet("background: transparent;")
    
    def _update_rotation(self):
        """Actualiza el ángulo de rotación."""
        self.rotation = (self.rotation + 6) % 360
        self.update()
    
    def start_loading(self):
        """Inicia la animación de carga."""
        if not self.is_loading:
            self.is_loading = True
            self.timer.start()
            self.show()
    
    def stop_loading(self):
        """Detiene la animación de carga."""
        if self.is_loading:
            self.is_loading = False
            self.timer.stop()
            self.hide()
    
    def paintEvent(self, event):
        """Dibuja el loader circular animado."""
        if not self.is_loading:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Centro del widget
        center_x = self.size / 2
        center_y = self.size / 2
        radius = self.size / 2 - 5
        
        # Dibujar círculo de fondo (gris claro)
        pen = QPen()
        pen.setColor(QColor(230, 230, 230))
        pen.setWidth(4)
        painter.setPen(pen)
        painter.drawEllipse(5, 5, self.size - 10, self.size - 10)
        
        # Dibujar arco animado (azul)
        pen.setColor(QColor(25, 118, 210))  # Azul VISO
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # Arco que gira
        start_angle = self.rotation * 16  # convertir a 1/16 de grado
        span_angle = 120 * 16  # 120 grados de arco
        
        painter.drawArc(
            5, 5, 
            self.size - 10, self.size - 10,
            int(start_angle), int(span_angle)
        )
        
        painter.end()
