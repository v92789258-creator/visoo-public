"""
Ventana de Activación - Diseño Profesional y Moderno
Características:
- Diseño limpio y atractivo
- Validación en tiempo real
- Feedback visual (loader)
- Formateo automático de clave
- Soporte para copiar/pegar
- Thread para no bloquear UI
"""

import sys
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFrame, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QCursor

# Importa las funciones para guardar la clave y validar la API
from utils.file_handler import guardar_clave_activacion
from utils.api_handler import validar_clave_activacion_api

try:
    from utils.error_logger import get_logger
    logger = get_logger('ACTIVATION')
except ImportError:
    import logging
    logger = logging.getLogger('ACTIVATION')


class ActivationValidator(QThread):
    """Thread para validar la clave sin bloquear la UI"""
    validacion_completa = pyqtSignal(bool, str)  # (es_valida, mensaje)
    
    def __init__(self, clave):
        super().__init__()
        self.clave = clave
    
    def run(self):
        try:
            # Validar clave con API
            success, message = validar_clave_activacion_api(self.clave)
            self.validacion_completa.emit(success, message)
            
            if success:
                logger.info(f"Clave activada: {self.clave[:4]}...")
            else:
                logger.warning(f"Validación fallida: {message}")
                
        except Exception as e:
            logger.error(f"Error en validación: {e}")
            self.validacion_completa.emit(False, "Error de conexión")


class ActivationWindow(QDialog):
    """Ventana profesional de activación de licencia"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activar Licencia VISO")
        self.setFixedSize(550, 480)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        
        # Establecer ícono
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Variables de estado
        self.validador = None
        self.esta_validando = False
        
        self.setup_ui()
        self.apply_styles()
        self.center_window()
    
    def setup_ui(self):
        """Construir interfaz de usuario"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 35, 35, 35)
        main_layout.setSpacing(20)
        
        # --- ENCABEZADO ---
        header_layout = QVBoxLayout()
        header_layout.setSpacing(12)
        
        # Logo/Ícono grande
        logo_label = QLabel("🔑")
        logo_label.setFont(QFont("Arial", 56))
        logo_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(logo_label)
        
        # Título
        titulo = QLabel("Activar Licencia VISO")
        titulo.setFont(QFont("Arial", 20, QFont.Bold))
        titulo.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(titulo)
        
        # Subtítulo
        subtitulo = QLabel("Ingresa tu clave para continuar usando el sistema")
        subtitulo.setFont(QFont("Arial", 11))
        subtitulo.setAlignment(Qt.AlignCenter)
        subtitulo.setStyleSheet("color: #666666; margin-top: 5px;")
        header_layout.addWidget(subtitulo)
        
        main_layout.addLayout(header_layout)
        
        # --- SEPARADOR ---
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setStyleSheet("background-color: #E8E8E8; height: 1px;")
        main_layout.addWidget(separador)
        
        # --- FORMULARIO ---
        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)
        
        # Etiqueta de clave
        clave_label = QLabel("Clave de Activación:")
        clave_label.setFont(QFont("Arial", 11, QFont.Bold))
        clave_label.setStyleSheet("color: #333333;")
        form_layout.addWidget(clave_label)
        
        # Input de clave con estilos
        self.clave_entry = QLineEdit()
        self.clave_entry.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.clave_entry.setFont(QFont("Courier", 13))
        self.clave_entry.setCursor(QCursor(Qt.IBeamCursor))
        self.clave_entry.setMinimumHeight(48)
        self.clave_entry.textChanged.connect(self.formatear_clave)
        self.clave_entry.returnPressed.connect(self.activar)  # Enter para activar
        self.clave_entry.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(self.clave_entry)
        
        # Información de ayuda
        help_label = QLabel(
            "💡 Copia y pega tu clave aquí. Se formateará automáticamente."
        )
        help_label.setFont(QFont("Arial", 10))
        help_label.setStyleSheet("color: #0066CC; margin-top: 5px;")
        help_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(help_label)
        
        main_layout.addLayout(form_layout)
        
        # --- BARRA DE PROGRESO (oculta inicialmente) ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Modo indeterminado
        self.progress_bar.setMinimumHeight(3)
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #F0F0F0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0066CC;
                border-radius: 2px;
            }
        """)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        # --- BOTONES ---
        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(12)
        
        # Botón "Obtener Clave"
        self.obtener_button = QPushButton("💬 Obtener Clave por WhatsApp")
        self.obtener_button.setMinimumHeight(42)
        self.obtener_button.setFont(QFont("Arial", 10))
        self.obtener_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.obtener_button.clicked.connect(self.obtener_clave)
        self.obtener_button.setObjectName("obtenerButton")
        botones_layout.addWidget(self.obtener_button)
        
        # Botón "Activar"
        self.activar_button = QPushButton("✓ Activar Licencia")
        self.activar_button.setMinimumHeight(42)
        self.activar_button.setFont(QFont("Arial", 10, QFont.Bold))
        self.activar_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.activar_button.clicked.connect(self.activar)
        self.activar_button.setObjectName("activarButton")
        botones_layout.addWidget(self.activar_button)
        
        main_layout.addLayout(botones_layout)
        
        # --- PIE DE PÁGINA ---
        pie_layout = QVBoxLayout()
        pie_layout.setContentsMargins(0, 15, 0, 0)
        pie_layout.setSpacing(0)
        
        # Línea separadora
        separador_pie = QFrame()
        separador_pie.setFrameShape(QFrame.HLine)
        separador_pie.setStyleSheet("background-color: #E8E8E8; height: 1px;")
        pie_layout.addWidget(separador_pie)
        
        # Texto de soporte
        soporte_label = QLabel(
            "¿Necesitas ayuda? Visita api.yhana.cloud"
        )
        soporte_label.setFont(QFont("Arial", 9))
        soporte_label.setAlignment(Qt.AlignCenter)
        soporte_label.setStyleSheet("color: #999999; margin-top: 12px;")
        pie_layout.addWidget(soporte_label)
        
        main_layout.addLayout(pie_layout)
    
    def apply_styles(self):
        """Aplicar estilos CSS profesionales"""
        self.setStyleSheet("""
            ActivationWindow {
                background-color: #FFFFFF;
            }
            
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 10px;
                background-color: #F8F9FA;
                selection-background-color: #0066CC;
                color: #333333;
            }
            
            QLineEdit:focus {
                border: 2px solid #0066CC;
                background-color: #FFFFFF;
                color: #333333;
            }
            
            QLineEdit::placeholder {
                color: #AAAAAA;
            }
            
            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                border: none;
                background-color: #F0F0F0;
                color: #333333;
                transition: all 0.2s;
            }
            
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            
            QPushButton:pressed {
                background-color: #D0D0D0;
            }
            
            #obtenerButton {
                background-color: #25D366;
                color: #FFFFFF;
                font-weight: bold;
            }
            
            #obtenerButton:hover {
                background-color: #1EBD56;
            }
            
            #obtenerButton:pressed {
                background-color: #128C44;
            }
            
            #activarButton {
                background-color: #0066CC;
                color: #FFFFFF;
            }
            
            #activarButton:hover {
                background-color: #0052A3;
            }
            
            #activarButton:pressed {
                background-color: #003D7A;
            }
            
            #activarButton:disabled {
                background-color: #CCCCCC;
                color: #FFFFFF;
            }
        """)
    
    def center_window(self):
        """Centrar la ventana en la pantalla"""
        from PyQt5.QtWidgets import QApplication
        screen_geometry = QApplication.desktop().screenGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
    
    def formatear_clave(self):
        """Formatear automáticamente la clave en grupos de 4"""
        texto = self.clave_entry.text()
        
        # Remover caracteres no alfanuméricos
        texto_limpio = ''.join(c.upper() for c in texto if c.isalnum())
        
        # Limitar a 16 caracteres (4 grupos de 4)
        if len(texto_limpio) > 16:
            texto_limpio = texto_limpio[:16]
        
        # Formatear con guiones
        texto_formateado = '-'.join([
            texto_limpio[i:i+4] for i in range(0, len(texto_limpio), 4)
        ])
        
        self.clave_entry.blockSignals(True)
        self.clave_entry.setText(texto_formateado)
        self.clave_entry.setCursorPosition(len(texto_formateado))
        self.clave_entry.blockSignals(False)
    
    def activar(self):
        """Activar la licencia"""
        clave = self.clave_entry.text().strip()
        
        # Validar que no esté vacío
        if not clave or len(clave.replace('-', '')) < 16:
            QMessageBox.warning(
                self, 
                "⚠ Clave Incompleta",
                "Por favor, ingresa una clave de activación válida.\n"
                "Formato: XXXX-XXXX-XXXX-XXXX\n\n"
                "Si no tienes clave, haz clic en 'Obtener Clave'"
            )
            return
        
        # Evitar múltiples activaciones simultáneas
        if self.esta_validando:
            return
        
        # Mostrar indicador de carga
        self.esta_validando = True
        self.progress_bar.show()
        self.activar_button.setEnabled(False)
        self.obtener_button.setEnabled(False)
        self.activar_button.setText("⏳ Validando...")
        self.clave_entry.setEnabled(False)
        
        print(f"\n[VERIFICANDO] Clave de activación: {clave}")
        logger.info(f"Iniciando validación de clave: {clave[:4]}...")
        
        # Crear thread de validación
        self.validador = ActivationValidator(clave)
        self.validador.validacion_completa.connect(self.en_validacion_completa)
        self.validador.start()
    
    def en_validacion_completa(self, es_valida, mensaje):
        """Callback cuando la validación se completa"""
        self.esta_validando = False
        self.progress_bar.hide()
        self.activar_button.setEnabled(True)
        self.obtener_button.setEnabled(True)
        self.clave_entry.setEnabled(True)
        self.activar_button.setText("✓ Activar Licencia")
        
        if es_valida:
            try:
                # Guardar clave
                guardar_clave_activacion(self.clave_entry.text())
                
                # Mensaje de éxito
                QMessageBox.information(
                    self,
                    "✓ Éxito",
                    "¡Licencia activada correctamente!\n\n"
                    "El sistema VISO está listo para usar.\n"
                    "Ingresa con tu usuario para continuar."
                )
                logger.info("Licencia activada exitosamente")
                self.accept()
                
            except Exception as e:
                logger.error(f"Error al guardar clave: {e}")
                QMessageBox.critical(
                    self,
                    "❌ Error",
                    f"Error al guardar la licencia:\n{str(e)}"
                )
        else:
            QMessageBox.critical(
                self,
                "❌ Clave Inválida",
                f"No se pudo validar la clave.\n\n{mensaje}\n\n"
                "Por favor, verifica:\n"
                "1. Tu conexión a internet\n"
                "2. Que la clave sea correcta\n"
                "3. Que la clave no esté vencida"
            )
            logger.warning(f"Validación fallida: {mensaje}")
            self.clave_entry.selectAll()
            self.clave_entry.setFocus()
    
    def obtener_clave(self):
        """Abrir WhatsApp para obtener clave"""
        try:
            import webbrowser
            
            # Número de WhatsApp
            numero_whatsapp = "51972330654"
            mensaje = "Hola, necesito obtener una clave de activación para VISO"
            
            # URL de WhatsApp con mensaje predefinido
            url_whatsapp = f"https://wa.me/{numero_whatsapp}?text={mensaje.replace(' ', '%20')}"
            
            QMessageBox.information(
                self,
                "💬 Obtener Clave por WhatsApp",
                "Se abrirá WhatsApp para comunicarte con soporte.\n\n"
                "Te pediremos:\n"
                "1. Información de tu cuenta\n"
                "2. Plan que deseas contratar\n"
                "3. Enviaremos tu clave de activación"
            )
            
            webbrowser.open(url_whatsapp)
            logger.info("Abriendo WhatsApp para obtener clave")
            
        except Exception as e:
            logger.error(f"Error abriendo WhatsApp: {e}")
            QMessageBox.warning(
                self,
                "⚠ Error",
                "No se pudo abrir WhatsApp.\n\n"
                "Contacta directamente a:\n"
                "+51 972 330 654\n\n"
                "O abre WhatsApp manualmente e ingresa el número"
            )
