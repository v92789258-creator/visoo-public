"""
Diálogo de Suspensión de Cuenta por Falta de Pago
Muestra cuando la licencia ha expirado o la cuenta está inactiva
"""

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

class SuspensionDialog(QDialog):
    """Diálogo elegante para informar que la cuenta está suspendida."""
    
    def __init__(self, parent=None, reason="expired", dias_restantes=-1, vigencia=None):
        """
        Args:
            parent: Widget padre
            reason: Razón de suspensión (expired, no_activation, invalid_key)
            dias_restantes: Días restantes (-1 si expirado)
            vigencia: Fecha de vigencia en formato ISO
        """
        super().__init__(parent)
        self.reason = reason
        self.dias_restantes = dias_restantes
        self.vigencia = vigencia
        
        self.setWindowTitle("Cuenta Suspendida")
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 400)
        self.setup_ui()
        self.center_on_parent(parent)
    
    def setup_ui(self):
        """Construir la interfaz del diálogo."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Contenedor principal (fondo blanco redondeado)
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 16px;
                padding: 0px;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)
        container_layout.setContentsMargins(40, 40, 40, 40)
        
        # === ÍCONO Y TÍTULO ===
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignCenter)
        
        # Ícono (círculo rojo con cerrado)
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(100, 100)
        icon_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #ff6b6b, stop:1 #ee5a52);
                border-radius: 50px;
                color: white;
                font-size: 48px;
                font-weight: bold;
                padding: 0px;
            }
        """)
        icon_label.setText("🔒")
        header_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        
        # Título
        title = QLabel("Cuenta Suspendida")
        title.setAlignment(Qt.AlignCenter)
        font_title = QFont()
        font_title.setPointSize(22)
        font_title.setBold(True)
        title.setFont(font_title)
        title.setStyleSheet("color: #263238; margin-bottom: 10px;")
        header_layout.addWidget(title)
        
        container_layout.addLayout(header_layout)
        
        # === CONTENIDO DEL MENSAJE ===
        message_layout = QVBoxLayout()
        message_layout.setSpacing(12)
        
        # Línea separadora
        separator1 = QWidget()
        separator1.setFixedHeight(1)
        separator1.setStyleSheet("background-color: #eeeeee;")
        message_layout.addWidget(separator1)
        
        # Mensaje principal según la razón
        message_text = self._get_message_text()
        
        message_label = QLabel(message_text)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)
        font_msg = QFont()
        font_msg.setPointSize(13)
        message_label.setFont(font_msg)
        message_label.setStyleSheet("color: #555; line-height: 1.6; padding: 10px;")
        message_layout.addWidget(message_label)
        
        # Información adicional
        if self.vigencia:
            info_label = QLabel(f"Vigencia: {self.vigencia}")
            info_label.setAlignment(Qt.AlignCenter)
            font_info = QFont()
            font_info.setPointSize(11)
            info_label.setFont(font_info)
            info_label.setStyleSheet("color: #999; font-style: italic;")
            message_layout.addWidget(info_label)
        
        # Línea separadora
        separator2 = QWidget()
        separator2.setFixedHeight(1)
        separator2.setStyleSheet("background-color: #eeeeee; margin-top: 10px;")
        message_layout.addWidget(separator2)
        
        container_layout.addLayout(message_layout)
        
        # === INSTRUCCIONES ===
        instructions = QLabel(
            "📧 Contacta con nuestro equipo de soporte:\n"
            "api.yhana.cloud\n\n"
            "Portal: api.yhana.cloud"
        )
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)
        font_instr = QFont()
        font_instr.setPointSize(10)
        instructions.setFont(font_instr)
        instructions.setStyleSheet("""
            QLabel {
                color: #666;
                background-color: #f5f5f5;
                border-radius: 8px;
                padding: 15px;
                line-height: 1.5;
            }
        """)
        container_layout.addWidget(instructions)
        
        # Espacio flexible
        container_layout.addStretch()
        
        # === BOTÓN DE CIERRE ===
        btn_close = QPushButton("Cerrar Sesión")
        btn_close.setFixedHeight(45)
        font_btn = QFont()
        font_btn.setPointSize(12)
        font_btn.setBold(True)
        btn_close.setFont(font_btn)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #9a0007;
            }
        """)
        btn_close.clicked.connect(self.accept)
        container_layout.addWidget(btn_close)
        
        main_layout.addWidget(container)
    
    def _get_message_text(self) -> str:
        """Obtiene el texto del mensaje según la razón."""
        if self.reason == "expired":
            return (
                "Tu clave de activación ha expirado.\n\n"
                "No puedes utilizar VISO en este momento.\n"
                "Por favor, renueva tu suscripción."
            )
        elif self.reason == "no_activation":
            return (
                "Tu cuenta no tiene una clave de activación activa.\n\n"
                "Debes activar tu cuenta para usar VISO.\n"
                "Contacta con nuestro equipo de soporte."
            )
        elif self.reason == "invalid_key":
            return (
                "Tu clave de activación no es válida.\n\n"
                "Verifica tu información de pago.\n"
                "Si crees que es un error, contacta soporte."
            )
        else:
            return (
                "Tu cuenta está suspendida por falta de pago.\n\n"
                "Por favor, revisa tu estado de suscripción.\n"
                "Contacta con nuestro equipo de soporte."
            )
    
    def center_on_parent(self, parent):
        """Centra el diálogo en la pantalla."""
        if parent:
            parent_geometry = parent.geometry()
            x = parent_geometry.center().x() - self.width() // 2
            y = parent_geometry.center().y() - self.height() // 2
            self.move(x, y)
        else:
            # Centrar en pantalla si no hay padre
            screen = QtWidgets.QApplication.primaryScreen()
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
