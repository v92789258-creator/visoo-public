"""
Loading Overlay - Ventana de carga separada que aparece encima de la ventana principal
Diseño moderno con animación suave y profesional
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QRect, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient
import math

class LoadingOverlay(QDialog):
    """Ventana de carga separada con diseño moderno"""
    
    loading_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cargando...")
        self.setWindowModality(Qt.ApplicationModal)
        
        # Estilos modernos: fondo blanco limpio
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(248, 249, 250, 1);
                border-radius: 20px;
            }
        """)
        
        # Ventana sin marco, siempre al frente
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Agregar sombra elegante
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
        
        self.fade_timer = None
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Spinner animado mejorado
        self.spinner = SpinnerWidget(self)
        self.spinner.setFixedSize(100, 100)
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        
        # Texto principal "Cargando..."
        self.text_label = QLabel("Cargando datos...", self)
        font = QFont("Segoe UI", 16)
        font.setWeight(QFont.Bold)
        self.text_label.setFont(font)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("color: #1a1a1a; font-weight: 600;")
        layout.addWidget(self.text_label, alignment=Qt.AlignCenter)
        
        # Texto secundario con color más suave
        self.subtitle_label = QLabel("Por favor espera...", self)
        subtitle_font = QFont("Segoe UI", 11)
        subtitle_font.setWeight(QFont.Normal)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.subtitle_label, alignment=Qt.AlignCenter)
        
        # Tamaño optimizado
        self.setFixedSize(400, 300)
        
        # Inicialmente invisible
        self.setWindowOpacity(0)
    
    def show_loading(self, text="Cargando datos..."):
        """Muestra la ventana de carga con fade in"""
        self.text_label.setText(text)
        self.spinner.start_animation()
        
        # Mostrar ventana
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Fade in suave
        if self.fade_timer is not None:
            self.fade_timer.stop()
        
        self.fade_timer = QTimer(self)
        self._fade_in_step = 0
        self.fade_timer.timeout.connect(self._fade_in)
        self.fade_timer.start(20)
    
    def _fade_in(self):
        """Animación de fade in"""
        self._fade_in_step += 0.08
        if self._fade_in_step <= 1.0:
            self.setWindowOpacity(self._fade_in_step)
        else:
            self.fade_timer.stop()
            self.setWindowOpacity(1.0)
    
    def hide_loading(self):
        """Oculta la ventana de carga con fade out"""
        self.spinner.stop_animation()
        
        if self.fade_timer is not None:
            self.fade_timer.stop()
        
        # Fade out suave
        self.fade_timer = QTimer(self)
        self._fade_out_step = 1.0
        self.fade_timer.timeout.connect(self._fade_out)
        self.fade_timer.start(20)
    
    def _fade_out(self):
        """Animación de fade out"""
        self._fade_out_step -= 0.08
        if self._fade_out_step >= 0.0:
            self.setWindowOpacity(self._fade_out_step)
        else:
            self.fade_timer.stop()
            self.hide()
            self.setWindowOpacity(1.0)
            self.loading_complete.emit()

class SpinnerWidget(QWidget):
    """Widget spinner animado con diseño moderno"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.is_animating = False
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_angle)
        self.setMinimumSize(100, 100)
        self.setFocusPolicy(Qt.NoFocus)
    
    def start_animation(self):
        """Inicia la animación"""
        if not self.is_animating:
            self.is_animating = True
            self.animation_timer.start(20)
    
    def stop_animation(self):
        """Detiene la animación"""
        self.is_animating = False
        self.animation_timer.stop()
    
    def _update_angle(self):
        """Actualiza el ángulo de rotación"""
        self.angle = (self.angle + 8) % 360
        self.update()
    
    def paintEvent(self, event):
        """Dibuja el spinner con estilo moderno"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # Centro del widget
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Radio del spinner
        radius = min(self.width(), self.height()) / 2 - 8
        
        # Color primario (azul moderno)
        primary_color = QColor(13, 110, 253)  # Azul Bootstrap
        
        # Dibujar arco principal (la parte animada)
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.angle)
        
        # Crear gradiente para efecto más suave
        pen = QPen()
        pen.setCapStyle(Qt.RoundCap)
        pen.setWidth(5)
        
        # Arco principal con gradiente
        pen.setColor(primary_color)
        painter.setPen(pen)
        
        rect = QRect(int(-radius), int(-radius), int(2*radius), int(2*radius))
        painter.drawArc(rect, 0, 120 * 16)
        
        # Arco secundario más débil (para efecto más bonito)
        pen.setColor(QColor(13, 110, 253, 100))
        pen.setWidth(4)
        painter.setPen(pen)
        painter.drawArc(rect, 180 * 16, 100 * 16)
        
        painter.restore()
        
        # Puntos decorativos alrededor
        for i in range(3):
            angle = (self.angle + i * 120) * math.pi / 180
            x = center_x + radius * 1.3 * math.cos(angle)
            y = center_y + radius * 1.3 * math.sin(angle)
            
            alpha = 255 - (i * 85)
            dot_color = QColor(13, 110, 253, alpha)
            painter.setBrush(dot_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(x - 3), int(y - 3), 6, 6)

        painter.end()
