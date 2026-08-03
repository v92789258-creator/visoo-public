from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QPainter, QLinearGradient, QPixmap, QIcon as QIcon
import os
import math


class WelcomeDialog(QDialog):
    """Modal de bienvenida bonito para la primera vez que entra el usuario."""
    
    def __init__(self, username="Usuario", parent=None):
        super().__init__(parent)
        self.username = username
        self.icon_label = None
        self.title_label = None
        self.user_label = None
        self.message_label = None
        self.btn_start = None
        self.animation_step = 0
        self.setup_ui()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
    
    def setup_ui(self):
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Fondo minimalista - Blanco y gris claro
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 20px;
                padding: 0px;
            }
        """)
        
        # Sombra suave para profundidad minimalista
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 40))
        container.setGraphicsEffect(shadow)
        
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(45, 45, 45, 45)
        content_layout.setSpacing(12)
        
        # Icono de bienvenida - minimalista
        self.icon_label = QLabel("✨")
        self.icon_label.setFont(QFont('Arial', 70))
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setObjectName("iconLabel")
        self.icon_label.setMinimumHeight(100)
        content_layout.addWidget(self.icon_label)
        
        # Título principal - minimalista
        self.title_label = QLabel("Bienvenido a VISO")
        title_font = QFont('Segoe UI', 24)
        title_font.setWeight(500)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #1a1a1a;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(True)
        content_layout.addWidget(self.title_label)
        
        # Nombre del usuario
        self.user_label = QLabel(f"{self.username}")
        user_font = QFont('Segoe UI', 15)
        user_font.setWeight(300)
        self.user_label.setFont(user_font)
        self.user_label.setStyleSheet("color: #808080;")
        self.user_label.setAlignment(Qt.AlignCenter)
        self.user_label.setObjectName("userLabel")
        content_layout.addWidget(self.user_label)
        
        # Línea divisora sutil
        divider = QFrame()
        divider.setStyleSheet("background: #e8e8e8;")
        divider.setFixedHeight(1)
        content_layout.addSpacing(8)
        content_layout.addWidget(divider)
        content_layout.addSpacing(8)
        
        # Mensaje de agradecimiento - minimalista
        self.message_label = QLabel(
            "Gracias por elegir VISO.\n\n"
            "Tu sistema de gestión para ópticas,\n"
            "diseñado para la eficiencia."
        )
        message_font = QFont('Segoe UI', 12)
        message_font.setWeight(300)
        self.message_label.setFont(message_font)
        self.message_label.setStyleSheet("color: #606060; line-height: 1.6;")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("messageLabel")
        content_layout.addWidget(self.message_label)
        
        content_layout.addSpacing(15)
        
        # Botón minimalista
        self.btn_start = QPushButton("Continuar")
        self.btn_start.setFont(QFont('Segoe UI', 12, QFont.Normal))
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                color: #1a1a1a;
                border: 1px solid #e0e0e0;
                padding: 12px 35px;
                border-radius: 8px;
                font-weight: 500;
                font-size: 12px;
                letter-spacing: 0.5px;
                min-width: 180px;
            }
            QPushButton:hover {
                background: #e5e5e5;
                border: 1px solid #d0d0d0;
            }
            QPushButton:pressed {
                background: #d8d8d8;
                border: 1px solid #c0c0c0;
            }
        """)
        self.btn_start.setFixedHeight(48)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.accept)
        content_layout.addWidget(self.btn_start, alignment=Qt.AlignCenter)
        
        main_layout.addWidget(container)
        
        # Tamaño - compacto y elegante
        self.setFixedSize(520, 580)
        
        # Posicionar en el centro
        if self.parent():
            parent_geometry = self.parent().geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
        
        # Iniciar animaciones
        self.start_animations()
    
    def start_animations(self):
        """Inicia todas las animaciones del diálogo."""
        # Hacer invisible inicialmente
        self.icon_label.setStyleSheet("font-size: 70px; color: #1a1a1a; opacity: 0;")
        self.title_label.setStyleSheet("color: rgba(26, 26, 26, 0);")
        self.user_label.setStyleSheet("color: rgba(128, 128, 128, 0);")
        self.message_label.setStyleSheet("color: rgba(96, 96, 96, 0); line-height: 1.6;")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: rgba(240, 240, 240, 0);
                color: #1a1a1a;
                border: 1px solid rgba(224, 224, 224, 0);
                padding: 12px 35px;
                border-radius: 8px;
                font-weight: 500;
                font-size: 12px;
                letter-spacing: 0.5px;
                min-width: 180px;
            }
        """)
        
        # Animación del icono
        self.animate_icon()
        
        # Animaciones de los textos
        QTimer.singleShot(150, self.animate_title)
        QTimer.singleShot(300, self.animate_user_label)
        QTimer.singleShot(450, self.animate_message)
        QTimer.singleShot(600, self.animate_button)
    
    def animate_icon(self):
        """Anima el icono con efecto suave de escala."""
        self.icon_animation_step = 0
        self.icon_animation_timer = QTimer()
        self.icon_animation_timer.timeout.connect(self._update_icon_animation)
        self.icon_animation_timer.start(20)
    
    def _update_icon_animation(self):
        """Actualiza la animación del icono."""
        step = self.icon_animation_step % 60
        
        # Efecto de escala suave
        scale = 0.8 + 0.2 * math.sin(step * math.pi / 60)
        font_size = int(70 * scale)
        opacity = min(self.icon_animation_step / 15, 1.0)
        
        self.icon_label.setStyleSheet(f"""
            font-size: {font_size}px;
            color: rgba(26, 26, 26, {int(255 * opacity)});
        """)
        
        self.icon_animation_step += 1
        
        # Parar después de 2 ciclos
        if self.icon_animation_step > 120:
            self.icon_animation_timer.stop()
            self.icon_label.setStyleSheet("font-size: 70px; color: #1a1a1a;")
    
    def animate_title(self):
        """Anima el título con fade in."""
        self.title_animation_step = 0
        self.title_animation_timer = QTimer()
        self.title_animation_timer.timeout.connect(self._update_title_animation)
        self.title_animation_timer.start(20)
    
    def _update_title_animation(self):
        """Actualiza la animación del título."""
        self.title_animation_step += 1
        opacity = min(self.title_animation_step / 15, 1.0)
        self.title_label.setStyleSheet(f"color: rgba(26, 26, 26, {int(255 * opacity)});")
        
        if self.title_animation_step >= 15:
            self.title_animation_timer.stop()
            self.title_label.setStyleSheet("color: #1a1a1a;")
    
    def animate_user_label(self):
        """Anima la etiqueta del usuario con fade in."""
        self.user_animation_step = 0
        self.user_animation_timer = QTimer()
        self.user_animation_timer.timeout.connect(self._update_user_animation)
        self.user_animation_timer.start(20)
    
    def _update_user_animation(self):
        """Actualiza la animación del usuario."""
        self.user_animation_step += 1
        opacity = min(self.user_animation_step / 15, 1.0)
        self.user_label.setStyleSheet(f"color: rgba(128, 128, 128, {int(255 * opacity)});")
        
        if self.user_animation_step >= 15:
            self.user_animation_timer.stop()
            self.user_label.setStyleSheet("color: #808080;")
    
    def animate_message(self):
        """Anima el mensaje con fade in."""
        self.message_animation_step = 0
        self.message_animation_timer = QTimer()
        self.message_animation_timer.timeout.connect(self._update_message_animation)
        self.message_animation_timer.start(20)
    
    def _update_message_animation(self):
        """Actualiza la animación del mensaje."""
        self.message_animation_step += 1
        opacity = min(self.message_animation_step / 15, 1.0)
        self.message_label.setStyleSheet(f"color: rgba(96, 96, 96, {int(255 * opacity)}); line-height: 1.6;")
        
        if self.message_animation_step >= 15:
            self.message_animation_timer.stop()
            self.message_label.setStyleSheet("color: #606060; line-height: 1.6;")
    
    def animate_button(self):
        """Anima el botón con fade in."""
        self.button_animation_step = 0
        self.button_animation_timer = QTimer()
        self.button_animation_timer.timeout.connect(self._update_button_animation)
        self.button_animation_timer.start(20)
    
    def _update_button_animation(self):
        """Actualiza la animación del botón."""
        self.button_animation_step += 1
        opacity = min(self.button_animation_step / 15, 1.0)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background: rgba(240, 240, 240, {int(255 * opacity)});
                color: #1a1a1a;
                border: 1px solid rgba(224, 224, 224, {int(255 * opacity)});
                padding: 12px 35px;
                border-radius: 8px;
                font-weight: 500;
                font-size: 12px;
                letter-spacing: 0.5px;
                min-width: 180px;
            }}
            QPushButton:hover {{
                background: rgba(229, 229, 229, {int(255 * opacity)});
                border: 1px solid rgba(208, 208, 208, {int(255 * opacity)});
            }}
            QPushButton:pressed {{
                background: rgba(216, 216, 216, {int(255 * opacity)});
                border: 1px solid rgba(192, 192, 192, {int(255 * opacity)});
            }}
        """)
        
        if self.button_animation_step >= 15:
            self.button_animation_timer.stop()
            self.btn_start.setStyleSheet("""
                QPushButton {
                    background: #f0f0f0;
                    color: #1a1a1a;
                    border: 1px solid #e0e0e0;
                    padding: 12px 35px;
                    border-radius: 8px;
                    font-weight: 500;
                    font-size: 12px;
                    letter-spacing: 0.5px;
                    min-width: 180px;
                }
                QPushButton:hover {
                    background: #e5e5e5;
                    border: 1px solid #d0d0d0;
                }
                QPushButton:pressed {
                    background: #d8d8d8;
                    border: 1px solid #c0c0c0;
                }
            """)
    
    def show_with_animation(self):
        """Muestra el diálogo con una animación suave."""
        self.show()

