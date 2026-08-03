import os
import json
import logging
import sys
import webbrowser
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QMessageBox, QStackedWidget, QDialog, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtCore import QThread, pyqtSignal, QUrl, QByteArray

logger = logging.getLogger(__name__)

# Ruta del logo (fallback si no existe)
LOGO_PATH = "icon.ico"


def _import_optica_app():
    from gui.main_window import OpticaApp
    return OpticaApp


def _get_file_handler():
    from utils import file_handler
    return file_handler


def cargar_usuarios():
    return _get_file_handler().cargar_usuarios()


def guardar_usuarios(usuarios):
    return _get_file_handler().guardar_usuarios(usuarios)


def crear_directorios_usuario(user_id):
    return _get_file_handler().crear_directorios_usuario(user_id)


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_viso_dir():
    return os.path.join(_get_base_dir(), "VISO")


def cargar_preferencias():
    try:
        pref_file = os.path.join(_get_viso_dir(), "user_preferences.json")
        if os.path.exists(pref_file):
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def guardar_preferencias(preferencias):
    try:
        viso_dir = _get_viso_dir()
        os.makedirs(viso_dir, exist_ok=True)
        pref_file = os.path.join(viso_dir, "user_preferences.json")
        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(preferencias, f, indent=2)
        return True
    except Exception:
        return False


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = _get_base_dir()
    return os.path.join(base_path, relative_path)


def _get_sesion_file():
    return os.path.join(_get_viso_dir(), "sesion.txt")

# ============================================================
# WORKER PARA LOGIN EN HILO SEPARADO
# ============================================================
class LoginWorker(QThread):
    """Worker que ejecuta el login en un hilo separado."""
    login_complete = pyqtSignal(bool, str, str, dict, dict)  # exito, id, mensaje, licencia, datos_extra
    
    def __init__(self, usuario, contrasena):
        super().__init__()
        self.usuario = usuario
        self.contrasena = contrasena
    
    def run(self):
        """Ejecuta el login en background (sin mostrar consolas)."""
        try:
            from utils.api_handler import login_remoto

            # Suprimir output a consola durante login
            import sys
            import io
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            
            try:
                exito, id_usuario, mensaje, datos_licencia = login_remoto(
                    self.usuario, 
                    self.contrasena
                )
            finally:
                # Restaurar salida estándar
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Emitir resultado
            self.login_complete.emit(exito, id_usuario or "", mensaje or "", datos_licencia or {}, {})
        except Exception as e:
            self.login_complete.emit(False, "", str(e), {}, {})

# ============================================================
# SPINNER MODERNO SIMPLE (SIN QPAINTER)
# ============================================================
class ModernSpinner(QtWidgets.QLabel):
    """Spinner animado simple sin QPainter."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("font-size: 32px; color: #2196F3;")
        
        self.angle = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.rotate)
        self.timer.start(100)
        
        self.spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.index = 0
    
    def rotate(self):
        """Actualiza el spinner."""
        self.setText(self.spinners[self.index % len(self.spinners)])
        self.index += 1
    
    def stop(self):
        """Detiene la animación."""
        self.timer.stop()



# ============================================================
# ANIMACIÓN DE CARGANDO CON SPINNER
# ============================================================
class LoadingAnimation(QtCore.QObject):
    """Animación mejorada de cargando con spinner."""
    
    def __init__(self, button):
        super().__init__()
        self.button = button
        self.is_running = False
    
    def start(self):
        """Inicia la animación."""
        self.is_running = True
        self.button.setEnabled(False)
        self.button.setText("◑ Conectando...")
        
        # Timer para cambiar el spinner
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_spinner)
        self.timer.start(150)
    
    def stop(self):
        """Detiene la animación."""
        self.is_running = False
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.button.setText("Iniciar Sesión")
        self.button.setEnabled(True)
    
    def update_spinner(self):
        """Actualiza el spinner visual."""
        spinners = ["◑", "◐", "◕", "◔"]
        if not hasattr(self, 'spinner_index'):
            self.spinner_index = 0
        
        spinner = spinners[self.spinner_index % len(spinners)]
        self.button.setText(f"{spinner} Conectando...")
        self.spinner_index += 1



# ============================================================
# OVERLAY DE CARGANDO CON FONDO SEMITRANSPARENTE
# ============================================================
class LoginLoadingOverlay(QtWidgets.QWidget):
    """Overlay semitransparente con spinner durante el login."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(parent.rect() if parent else self.rect())
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.4);")
        self.parent_widget = parent
        
        # Container central
        layout = QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        
        container = QtWidgets.QWidget()
        container.setFixedSize(220, 240)
        container.setStyleSheet("""
            background-color: white;
            border-radius: 16px;
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.setSpacing(15)
        container_layout.setContentsMargins(10, 10, 10, 10)
        
        # Botón cerrar en la esquina superior derecha
        close_btn = QtWidgets.QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: none;
                border-radius: 15px;
                color: #666;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        close_btn.clicked.connect(self.cancel_login)
        
        # Agregar botón a la esquina
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        top_layout.addWidget(close_btn)
        container_layout.addLayout(top_layout)
        
        # Spinner
        self.spinner = ModernSpinner()
        container_layout.addWidget(self.spinner, alignment=QtCore.Qt.AlignCenter)
        
        # Texto
        self.label = QLabel("Iniciando sesión...")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setStyleSheet("""
            color: #333;
            font-size: 14px;
            font-weight: 500;
        """)
        container_layout.addWidget(self.label)
        
        # Espacio flexible
        container_layout.addStretch()
        
        layout.addWidget(container, alignment=QtCore.Qt.AlignCenter)
        
        # Animación suave de aparición
        self.animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
    
    def cancel_login(self):
        """Cancela el login y cierra el overlay."""
        print("[OVERLAY] Botón cerrar presionado")
        # Intentar cancelar el worker si existe
        try:
            if hasattr(self.parent_widget, 'login_worker'):
                worker = self.parent_widget.login_worker
                if worker and worker.isRunning():
                    print("[OVERLAY] Terminando worker...")
                    worker.quit()
                    worker.wait(500)
        except Exception as e:
            print(f"[OVERLAY] Error terminando worker: {e}")
        
        # Cerrar inmediatamente
        print("[OVERLAY] Cerrando overlay...")
        self.hide()
        self.stop_spinner()
        self.deleteLater()
    
    def show_animated(self):
        """Muestra el overlay con animación suave."""
        self.show()
        self.animation.start()

    def set_message(self, text):
        """Actualiza el texto del modal de carga."""
        try:
            self.label.setText(str(text or "Cargando..."))
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.processEvents()
        except Exception:
            pass
    
    def hide_animated(self):
        """Oculta el overlay con animación suave."""
        hide_anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        hide_anim.setDuration(200)
        hide_anim.setStartValue(1)
        hide_anim.setEndValue(0)
        hide_anim.finished.connect(self._cleanup)
        hide_anim.start()
    
    def _cleanup(self):
        """Limpia el overlay después de ocultarse."""
        self.hide()
        self.stop_spinner()
        self.deleteLater()  # Destruir el widget
    
    def stop_spinner(self):
        """Detiene el spinner."""
        if hasattr(self, 'spinner'):
            self.spinner.stop()




class ErrorDialog(QDialog):
    """Modal elegante para mostrar errores de login."""
    def __init__(self, parent=None, title="Error", message=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 280)
        self.setup_ui(title, message)
        self.center_on_parent(parent)
    
    def setup_ui(self, title, message):
        """Configurar interfaz elegante."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Contenedor principal con sombra y bordes redondeados
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 16px;
                padding: 0px;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(30, 30, 30, 30)
        
        # Icono de error (círculo rojo con tache)
        icon_label = QLabel()
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setFixedSize(80, 80)
        icon_label.setStyleSheet("""
            QLabel {
                background-color: #ffebee;
                border-radius: 40px;
                color: #d32f2f;
                font-size: 40px;
                font-weight: bold;
            }
        """)
        icon_label.setText("✕")
        container_layout.addWidget(icon_label, alignment=QtCore.Qt.AlignCenter)
        
        container_layout.addSpacing(20)
        
        # Título del error
        title_label = QLabel(title)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #263238;
            }
        """)
        container_layout.addWidget(title_label)
        
        container_layout.addSpacing(10)
        
        # Mensaje de error
        msg_label = QLabel(message)
        msg_label.setAlignment(QtCore.Qt.AlignCenter)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
                line-height: 1.5;
            }
        """)
        container_layout.addWidget(msg_label)
        
        container_layout.addSpacing(30)
        
        # Botón de aceptar
        btn_aceptar = QPushButton("Intentar de nuevo")
        btn_aceptar.setFixedHeight(48)
        btn_aceptar.setCursor(QtCore.Qt.PointingHandCursor)
        btn_aceptar.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        btn_aceptar.clicked.connect(self.accept)
        container_layout.addWidget(btn_aceptar)
        
        main_layout.addWidget(container)
        
        # Aplicar sombra
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QtGui.QColor(0, 0, 0, 60))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)
    
    def center_on_parent(self, parent):
        """Centrar el diálogo en relación al parent."""
        if parent:
            parent_geometry = parent.geometry()
            self.move(
                parent_geometry.center().x() - self.width() // 2,
                parent_geometry.center().y() - self.height() // 2
            )

# Pequeñas reglas adicionales específicas para el login
LOGIN_EXTRA_QSS = """
    /* Estilos base para todos los botones */
    QPushButton {
        background-color: #E3F2FD !important; /* Celeste muy suave */
        color: #1565C0 !important; /* Azul oscuro para el texto */
        border: 1px solid #90CAF9 !important; /* Borde celeste */
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
    }

    QPushButton:hover {
        background-color: #BBDEFB !important; /* Celeste un poco más intenso en hover */
        border-color: #64B5F6 !important;
        color: #0D47A1 !important; /* Azul más oscuro en hover */
    }

    QPushButton:pressed {
        background-color: #90CAF9 !important; /* Aún más intenso al presionar */
        border-color: #42A5F5 !important;
    }

    /* Contenedor principal */
    LoginWindow QWidget#form_container { 
        background-color: white;
        border-radius: 18px;
        border: 1px solid rgba(0,0,0,0.06);
        padding: 20px;
    }

    /* Títulos */
    LoginWindow QLabel#loginTitle { 
        font-size: 26px; 
        font-weight: 700; 
        color: #263238; 
    }
    LoginWindow QLabel#loginSubtitle { 
        font-size: 14px; 
        color: #546e7a; 
    }

    /* Botones específicos del login */
    LoginWindow QPushButton#primaryButton {
        background-color: #2196F3; /* Azul más intenso para el botón principal */
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 15px;
        font-weight: bold;
        min-height: 48px;
        border-radius: 12px;
    }

    LoginWindow QPushButton#primaryButton:hover {
        background-color: #1976D2;
    }

    LoginWindow QPushButton#primaryButton:pressed {
        background-color: #1565C0;
        padding-top: 13px;
    }

    /* Enlaces en el login */
    LoginWindow QPushButton:flat {
        background: transparent;
        border: none;
        color: #2196F3;
        padding: 4px;
    }

    LoginWindow QPushButton:flat:hover {
        color: #1565C0;
        text-decoration: underline;
    }

    /* Checkboxes en el login */
    LoginWindow QCheckBox {
        color: #333333;
        font-size: 13px;
        spacing: 8px;
    }

    /* Campos de entrada */
    QLineEdit {
        color: #333333;
        background: white;
        font-size: 14px;
        padding: 12px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    QLineEdit:focus {
        border: 2px solid #2196F3;
    }

    /* Checkboxes */
    QCheckBox {
        color: #333333;
        font-size: 13px;
        spacing: 8px;
    }
    QCheckBox:hover {
        color: #1976D2;
    }

    /* Botones normales */
    QPushButton {
        color: #000000;
        background-color: #f5f5f5;
        border: 1px solid #dddddd;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
    }

    QPushButton:hover {
        background-color: #e8e8e8;
        border-color: #2196F3;
        color: #1976D2;
    }

    /* Botón principal */
    QPushButton#primaryButton {
        background-color: #2196F3;
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 15px;
        font-weight: bold;
        min-height: 48px;
        border-radius: 12px;
    }

    QPushButton#primaryButton:hover {
        background-color: #1976D2;
    }

    /* Enlaces */
    QPushButton:flat {
        background: transparent;
        border: none;
        color: #2196F3;
        padding: 4px;
    }

    QPushButton:flat:hover {
        color: #1565C0;
        text-decoration: underline;
    }

    /* Checkboxes más visibles */
    QCheckBox {
        color: #333333;
        font-size: 13px;
        spacing: 8px;
    }
    QCheckBox:hover {
        color: #1976D2;
    }

    /* Inputs con mejor contraste */
    QLineEdit {
        color: #333333;
        background: white;
        font-size: 14px;
        padding: 12px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    QLineEdit:focus {
        border: 2px solid #2196F3;
    }

    /* Botones básicos */
    QPushButton {
        color: #000000;
        font-size: 14px;
        font-weight: 600;
        border-radius: 8px;
        padding: 8px 16px;
    }

    /* Botones normales (no flat y no primary) */
    QPushButton:!flat:!#primaryButton { 
        background-color: #f0f0f0;
        border: 2px solid #cccccc;
    }
    QPushButton:!flat:!#primaryButton:hover {
        background-color: #e3e3e3;
        border-color: #2196F3;
        color: #1565C0;
    }
    QPushButton:!flat:!#primaryButton:pressed {
        background-color: #d4d4d4;
        border-color: #1976D2;
        padding-top: 9px;
    }

    /* Botón principal de login/registro */
    QPushButton#primaryButton { 
        min-height: 48px; 
        border-radius: 12px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2);
        color: black; /* forzar color negro */
        font-size: 15px;
        font-weight: bold;
        border: none;
        padding: 8px 24px;
    }
    QPushButton#primaryButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E88E5, stop:1 #1565C0);
        color: black !important;
    }
    QPushButton#primaryButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1976D2, stop:1 #0D47A1);
        color: black !important;
        padding-top: 10px;
    }

    /* Botones tipo link (flat) */
    QPushButton:flat {
        background: transparent;
        border: none;
        color: #2196F3;
        font-size: 13px;
        text-decoration: none;
        padding: 4px;
    }
    QPushButton:flat:hover {
        color: #1976D2;
        text-decoration: underline;
    }

    /* Botón principal de login/registro */
    QPushButton#primaryButton { 
        min-height: 48px; 
        border-radius: 12px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2);
        color: black;
        font-size: 15px;
        font-weight: bold;
        border: none;
        padding: 8px 24px;
    }
    QPushButton#primaryButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E88E5, stop:1 #1565C0);
    }
    QPushButton#primaryButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1976D2, stop:1 #0D47A1);
        padding-top: 10px;
    }

    /* Botones secundarios (no flat) */
    QPushButton:!flat { 
        background-color: #f0f0f0;
        color: #000000;
        border: 2px solid #cccccc;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 600;
    }
    QPushButton:!flat:hover {
        background-color: #e3e3e3;
        border-color: #2196F3;
        color: #1565C0;
    }
    QPushButton:!flat:pressed {
        background-color: #d4d4d4;
        border-color: #1976D2;
    }

    /* Botones tipo link (flat) */
    QPushButton:flat {
        background: transparent;
        border: none;
        color: #2196F3;
        font-size: 13px;
        text-decoration: none;
        padding: 4px;
    }
    QPushButton:flat:hover {
        color: #1976D2;
        text-decoration: underline;
    }
"""

class LoginWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Forzar una familia de fuentes del sistema para evitar que se use una fuente no deseada
        # (algunos equipos no tienen Poppins u otras fonts web instaladas).
        try:
            preferred_font = QtGui.QFont("Segoe UI", 10)
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.setFont(preferred_font)
            else:
                self.setFont(preferred_font)
        except Exception:
            # Si algo falla, no bloquearnos — Qt usará la fuente por defecto del sistema
            pass
        
        self.setWindowTitle("VISO LOGIN")
        self.resize(1000, 600)  # Aumentado de 800 a 1000
        
        # Establecer ícono de la ventana
        import sys
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        
        self.stacked_widget = QStackedWidget()
        # Aplicar estilos globales del proyecto y reglas extra para login
        try:
            # Forzar la aplicación de estilos primero
            self.setStyleSheet(LOGIN_EXTRA_QSS)
        except Exception as e:
            print("Error aplicando estilos:", str(e))
            pass
            
        self.setup_ui()

    def _show_login_loading_overlay(self, message="Iniciando sesión..."):
        try:
            overlay = getattr(self, "loading_overlay", None)
            if overlay is None:
                overlay = LoginLoadingOverlay(self)
                self.loading_overlay = overlay
                overlay.show_animated()
            overlay.set_message(message)
        except Exception:
            pass

    def _hide_login_loading_overlay(self, callback=None, delay_ms=300):
        overlay = getattr(self, "loading_overlay", None)
        if overlay:
            try:
                overlay.hide_animated()
            except Exception:
                try:
                    overlay.hide()
                except Exception:
                    pass
            self.loading_overlay = None
            if callback is not None:
                QtCore.QTimer.singleShot(delay_ms, callback)
            return
        if callback is not None:
            callback()
    
    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Layout dividido horizontalmente: izquierda imagen grande, derecha formulario
        split_widget = QtWidgets.QWidget()
        split_layout = QtWidgets.QHBoxLayout(split_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)
        # Forzar fondo blanco del split para evitar áreas negras cuando la imagen no cubre completamente
        try:
            split_widget.setStyleSheet("background-color: white;")
        except Exception:
            pass

        # Animación/Imagen grande a la izquierda usando QMovie (GIF)
        self.image_label = QtWidgets.QLabel()
        self.image_label.setObjectName("loginImage")
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        try:
            self.image_label.setStyleSheet("background-color: white;")
        except Exception:
            pass

        self.image_label.setMinimumSize(0, 0)
        try:
            self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        except Exception:
            pass

        # Buscar el archivo GIF o imagen estática
        media_path = None
        candidate_media = [
            resource_path('sesion.gif'),
            resource_path('images/sesion.gif'),
            resource_path('INICIAR.PNG'),
            resource_path('INICIAR.png'),
            resource_path('images/INICIAR.png')
        ]
        
        for p in candidate_media:
            try:
                p_abs = os.path.abspath(p)
                if os.path.exists(p_abs):
                    media_path = p_abs
                    break
            except Exception:
                pass

        if media_path:
            if media_path.lower().endswith('.gif'):
                # Es un GIF animado
                self.movie = QMovie(media_path)
                self.movie.setFormat(QByteArray(b"gif"))
                if not self.movie.isValid():
                    print(f"Warning: El archivo {media_path} no es un GIF válido para PyQt5.")
                self.image_label.setMovie(self.movie)
                self.image_label.setScaledContents(True)
                self.movie.start()
                self.image_pix = None # No usamos resizeEvent custom
            else:
                # Es una imagen estática (fallback)
                try:
                    pix = QtGui.QPixmap(media_path)
                    self.image_pix = pix
                    try:
                        target = self.image_label.size()
                        if target.width() > 0 and target.height() > 0:
                            scaled_pix = self.image_pix.scaled(target.width(), target.height(), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
                        else:
                            scaled_pix = self.image_pix
                    except Exception:
                        scaled_pix = self.image_pix
                    self.image_label.setPixmap(scaled_pix)
                    self.image_label.setScaledContents(True)
                except Exception:
                    self.image_pix = None
                    self.image_label.setText("Error cargando imagen")
        else:
            self.image_pix = None
            self.image_label.setText("Imagen/Animación no encontrada")

        # Agregar botón de Facebook flotante sobre el GIF
        img_layout = QtWidgets.QVBoxLayout(self.image_label)
        img_layout.setContentsMargins(30, 30, 30, 40) # Aumentar un poco el margen inferior
        img_layout.addStretch(1) # Empuja hacia abajo
        
        btn_fb_layout = QtWidgets.QHBoxLayout()
        # Empujar hacia la derecha para alinear el botón en la esquina inferior derecha
        btn_fb_layout.addStretch(1) 
        
        btn_fb = QtWidgets.QPushButton("")
        fb_icon_path = resource_path('images/facebook.svg')
        if os.path.exists(fb_icon_path):
            btn_fb.setIcon(QIcon(fb_icon_path))
            btn_fb.setIconSize(QtCore.QSize(24, 24))
            
        btn_fb.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_fb.setFixedSize(48, 48) # Hacer el botón circular
        btn_fb.setStyleSheet("""
            QPushButton {
                background-color: #1877F2;
                border-radius: 24px;
                border: 2px solid rgba(255, 255, 255, 0.8);
            }
            QPushButton:hover {
                background-color: #166FE5;
                border: 2px solid white;
            }
        """)
        btn_fb.clicked.connect(lambda: webbrowser.open("https://www.facebook.com/profile.php?id=61584112137845"))
        
        btn_fb_layout.addWidget(btn_fb)
        btn_fb_layout.addSpacing(60) # Empujar el botón un poco hacia la izquierda desde el borde derecho
        
        img_layout.addLayout(btn_fb_layout)

        split_layout.addWidget(self.image_label)

        # Contenedor del formulario a la derecha
        self.form_container = QtWidgets.QWidget()
        # self.form_container.setFixedSize(450, 550)  # Eliminado para responsividad
        self.form_container.setObjectName("form_container")
        try:
            self.form_container.setStyleSheet("background-color: white;")
        except Exception:
            pass
        # Añadir sombra suave al contenedor para destacarlo sobre el fondo
        try:
            shadow = QtWidgets.QGraphicsDropShadowEffect(self.form_container)
            shadow.setBlurRadius(28)
            shadow.setColor(QtGui.QColor(0, 0, 0, 50))
            shadow.setOffset(0, 6)
            self.form_container.setGraphicsEffect(shadow)
        except Exception:
            pass
        
        # añadir formulario al split y configurar proporciones - 50/50
        split_layout.addWidget(self.form_container)
        split_layout.setStretch(0, 1)
        split_layout.setStretch(1, 1)
        main_layout.addWidget(split_widget)

        form_layout = QtWidgets.QVBoxLayout(self.form_container)
        form_layout.setSpacing(20)  # Aumentado de 18 a 20 para mejor espaciado
        
        # Crear un widget contenedor para centrar verticalmente
        center_container = QtWidgets.QWidget()
        center_container_layout = QtWidgets.QVBoxLayout(center_container)
        center_container_layout.setContentsMargins(40, 0, 40, 0)
        
        # Agregar el título sin el logo
        title_label = QtWidgets.QLabel("Inicia sesión en VISO")
        title_label.setObjectName("loginTitle")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        center_container_layout.addWidget(title_label)
        subtitle = QtWidgets.QLabel("Accede con tu usuario para continuar")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(subtitle)
        
        center_container_layout.addWidget(self.stacked_widget)
        
        # Agregar el contenedor centrado al layout principal con espaciadores
        form_layout.addStretch(1)  # Espaciador superior
        form_layout.addWidget(center_container)
        form_layout.addStretch(1)  # Espaciador inferior

        self.setup_login_page()
        self.setup_register_page()
    
    def setup_login_page(self):
        self.login_page = QtWidgets.QWidget()
        login_layout = QtWidgets.QVBoxLayout(self.login_page)
        login_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # Encabezado de la página de login
        login_layout.addWidget(QtWidgets.QLabel("<h2>Iniciar Sesión</h2>", alignment=QtCore.Qt.AlignmentFlag.AlignCenter))

        # Contenedor para los campos con ancho fijo
        fields_container = QtWidgets.QWidget()
        fields_container.setMinimumWidth(400)  # Ancho mínimo para los campos
        fields_container.setMaximumWidth(500)  # Ancho máximo para mantener la forma
        fields_layout = QtWidgets.QVBoxLayout(fields_container)
        fields_layout.setContentsMargins(20, 0, 20, 0)  # Padding horizontal

        # Campos de entrada
        self.entry_nombre_login = QtWidgets.QLineEdit()
        self.entry_nombre_login.setPlaceholderText("Nombre de usuario")
        fields_layout.addWidget(self.entry_nombre_login)

        self.entry_pass_login = QtWidgets.QLineEdit()
        self.entry_pass_login.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.entry_pass_login.setPlaceholderText("Contraseña")
        fields_layout.addWidget(self.entry_pass_login)

        # Vinculación opcional como dispositivo hijo
        self.chk_dispositivo_hijo = QtWidgets.QCheckBox("Este equipo es dispositivo hijo")
        self.chk_dispositivo_hijo.setStyleSheet("font-size: 12px; color: #455a64;")
        fields_layout.addWidget(self.chk_dispositivo_hijo)

        self.entry_codigo_dispositivo_hijo = QtWidgets.QLineEdit()
        self.entry_codigo_dispositivo_hijo.setPlaceholderText("Código del dispositivo hijo (ej: VISO-240101-AB12CD)")
        self.entry_codigo_dispositivo_hijo.setVisible(False)
        fields_layout.addWidget(self.entry_codigo_dispositivo_hijo)

        self.lbl_dispositivo_hijo_info = QtWidgets.QLabel(
            "Al iniciar sesión se guardará este equipo como Dispositivo trabajador."
        )
        self.lbl_dispositivo_hijo_info.setStyleSheet("font-size: 11px; color: #546e7a;")
        self.lbl_dispositivo_hijo_info.setWordWrap(True)
        self.lbl_dispositivo_hijo_info.setVisible(False)
        fields_layout.addWidget(self.lbl_dispositivo_hijo_info)

        self.chk_dispositivo_hijo.stateChanged.connect(self.toggle_dispositivo_hijo_fields)

        # Agregar el contenedor al layout principal
        login_layout.addWidget(fields_container, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

        # Opciones (recordarme / mostrar contraseña)
        opts_layout = QtWidgets.QHBoxLayout()
        self.chk_recordarme = QtWidgets.QCheckBox("Recordarme")
        # Cargar preferencia guardada o usar True por defecto si no hay preferencia
        preferencias = cargar_preferencias()
        self.chk_recordarme.setChecked(preferencias.get('recordarme', True))
        self.chk_mostrar = QtWidgets.QCheckBox("Mostrar contraseña")
        self.chk_mostrar.stateChanged.connect(lambda s: self.entry_pass_login.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal if s else QtWidgets.QLineEdit.EchoMode.Password))
        opts_layout.addWidget(self.chk_recordarme)
        # Conectar el cambio de estado para guardar la preferencia
        self.chk_recordarme.stateChanged.connect(self.guardar_preferencia_recordarme)
        opts_layout.addStretch()
        opts_layout.addWidget(self.chk_mostrar)
        login_layout.addLayout(opts_layout)

        # Botón principal
        self.btn_login = QtWidgets.QPushButton("Iniciar Sesión")
        self.btn_login.setObjectName("primaryButton")
        self.btn_login.clicked.connect(self.iniciar_sesion)
        self.btn_login.setDefault(True)
        self.btn_login.setMinimumHeight(36)  # Reducido de 48 a 36
        # Aplicar estilos directamente al botón
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;  /* Reducido de 12px a 8px */
                padding: 8px 20px;  /* Reducido de 12px 24px a 8px 20px */
                font-size: 14px;  /* Reducido de 15px a 14px */
                font-weight: 600;  /* Cambiado de bold a 600 */
                min-height: 36px;  /* Reducido de 48px a 36px */
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
                padding-top: 9px;  /* Ajustado para el nuevo tamaño */
            }
        """)
        login_layout.addWidget(self.btn_login)

        # Link de registro
        btn_registro = QtWidgets.QPushButton("¿No tienes cuenta? Regístrate aquí")
        btn_registro.setFlat(True)
        btn_registro.setCursor(QtCore.Qt.PointingHandCursor)
        btn_registro.clicked.connect(self.abrir_registro)
        btn_registro.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #2196F3;
                font-size: 13px;
                padding: 4px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #1565C0;
            }
        """)
        login_layout.addWidget(btn_registro, alignment=QtCore.Qt.AlignCenter)
        
        # Link para ayudantes
        btn_ayudante = QtWidgets.QPushButton("¿Eres ayudante? Inicia sesión aquí")
        btn_ayudante.setFlat(True)
        btn_ayudante.setCursor(QtCore.Qt.PointingHandCursor)
        btn_ayudante.clicked.connect(self.mostrar_login_ayudante)
        btn_ayudante.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #FF9800;
                font-size: 13px;
                padding: 4px;
                text-decoration: underline;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #F57C00;
            }
        """)
        login_layout.addWidget(btn_ayudante, alignment=QtCore.Qt.AlignCenter)
        
        login_layout.addStretch()
        self.stacked_widget.addWidget(self.login_page)

    def toggle_dispositivo_hijo_fields(self, state):
        """Muestra/oculta el campo de código para vincular dispositivo hijo."""
        activo = bool(state)
        self.entry_codigo_dispositivo_hijo.setVisible(activo)
        self.lbl_dispositivo_hijo_info.setVisible(activo)
        if not activo:
            self.entry_codigo_dispositivo_hijo.clear()

    def setup_register_page(self):
        # Página vacía - El registro se realiza desde la web
        pass

    def iniciar_sesion(self):
        nombre_ingresado = self.entry_nombre_login.text().strip()
        contrasena_ingresada = self.entry_pass_login.text().strip()
        codigo_dispositivo_hijo = self.entry_codigo_dispositivo_hijo.text().strip().upper()

        if not nombre_ingresado or not contrasena_ingresada:
            error_dialog = ErrorDialog(
                parent=self,
                title="Campos Vacíos",
                message="Por favor, completa usuario y contraseña."
            )
            error_dialog.exec_()
            return

        if self.chk_dispositivo_hijo.isChecked() and not codigo_dispositivo_hijo:
            error_dialog = ErrorDialog(
                parent=self,
                title="Código Requerido",
                message="Ingresa el código del dispositivo hijo para vincular este equipo."
            )
            error_dialog.exec_()
            return

        # Mostrar overlay de cargando
        self._show_login_loading_overlay("Iniciando sesión...")
        
        # Crear worker para login en hilo separado
        self.login_worker = LoginWorker(nombre_ingresado, contrasena_ingresada)
        self.login_worker.login_complete.connect(
            lambda exito, user_id, mensaje, licencia, extra: 
            self.on_login_complete(nombre_ingresado, contrasena_ingresada, exito, user_id, mensaje, licencia)
        )
        self.login_worker.start()
    
    def on_login_complete(self, nombre_ingresado, contrasena_ingresada, exito_remoto, id_usuario_remoto, mensaje_remoto, datos_licencia):
        """Llamado cuando el login en background termina."""
        if exito_remoto and id_usuario_remoto:
            self._show_login_loading_overlay("Cargando sistema...")
            self._handle_login_result(
                nombre_ingresado, contrasena_ingresada, exito_remoto, id_usuario_remoto, mensaje_remoto, datos_licencia
            )
            return

        self._hide_login_loading_overlay(
            lambda: self._handle_login_result(
                nombre_ingresado, contrasena_ingresada, exito_remoto, id_usuario_remoto, mensaje_remoto, datos_licencia
            )
        )
    
    def _handle_login_result(self, nombre_ingresado, contrasena_ingresada, exito_remoto, id_usuario_remoto, mensaje_remoto, datos_licencia):
        """Procesa el resultado del login después de cerrar el overlay."""
        if not exito_remoto or not id_usuario_remoto:
            usuarios_locales = cargar_usuarios() or {}
            for local_user_id, info in usuarios_locales.items():
                if not isinstance(info, dict):
                    continue
                saved_username = str(info.get("username", "")).strip()
                saved_password = str(info.get("password", "")).strip()
                if saved_username == nombre_ingresado and saved_password == contrasena_ingresada:
                    exito_remoto = True
                    id_usuario_remoto = str(local_user_id)
                    mensaje_remoto = "Login local"
                    datos_licencia = {
                        'tiene_licencia': None,
                        'licencia_vigente': None,
                        'plan_type': 'Local',
                        'fecha_vencimiento': None,
                        'dias_restantes': 0
                    }
                    break

        if not exito_remoto or not id_usuario_remoto:
            # ❌ Login remoto falló - Mostrar error
            self._hide_login_loading_overlay()
            error_dialog = ErrorDialog(
                parent=self,
                title="Error de Acceso",
                message=f"No se pudo autenticar remotamente:\n{mensaje_remoto}\n\nVerifica tu conexión e intenta nuevamente."
            )
            error_dialog.exec_()
            # Limpiar y preparar para nuevo intento
            self.entry_nombre_login.clear()
            self.entry_pass_login.clear()
            self.entry_nombre_login.setFocus()
            return
        
        # ✅ Login exitoso en servidor remoto
        # 2️⃣ Verificar estado de licencia usando datos del login o API adicional
        tiene_licencia = datos_licencia.get('tiene_licencia', None)
        licencia_vigente = datos_licencia.get('licencia_vigente', None)
        plan_type = datos_licencia.get('plan_type', 'Desconocido')
        fecha_vencimiento = datos_licencia.get('fecha_vencimiento')
        dias_restantes = datos_licencia.get('dias_restantes', 0)
        
        # Mostrar información de licencia en consola
        if tiene_licencia:
            print(f"[LICENCIA] Usuario: {nombre_ingresado}")
            print(f"[LICENCIA] Plan: {plan_type}")
            if fecha_vencimiento:
                print(f"[LICENCIA] Vencimiento: {fecha_vencimiento}")
                print(f"[LICENCIA] Días restantes: {dias_restantes}")
            
            if not licencia_vigente:
                print(f"[LICENCIA] ADVERTENCIA: LICENCIA EXPIRADA - Requiere actualizacion\n")
            else:
                print(f"[LICENCIA] OK Licencia activa y vigente\n")
        else:
            print(f"[LICENCIA] Usuario sin licencia: {nombre_ingresado}")
            print(f"[LICENCIA] ADVERTENCIA: NO TIENE LICENCIA - Requiere activacion\n")
        
        # Contingencia: no bloquear acceso por estado de licencia.
        # Luego se puede restaurar esta validación cuando vuelva a ser necesaria.
        
        # ✅ Licencia vigente - Permitir acceso
        modo_dispositivo_hijo = self.chk_dispositivo_hijo.isChecked()
        dispositivo_hijo_validado = None

        # Si inicia como dispositivo hijo, validar código en la nube.
        if modo_dispositivo_hijo:
            codigo_hijo = self.entry_codigo_dispositivo_hijo.text().strip().upper()
            try:
                self._show_login_loading_overlay("Validando dispositivo...")
                from utils.api_handler import validar_codigo_dispositivo_hijo_remoto
                

                codigo_valido, dispositivo_hijo_validado, msg_codigo = validar_codigo_dispositivo_hijo_remoto(
                    nombre_ingresado,
                    codigo_hijo
                )
                if not codigo_valido:
                    self._hide_login_loading_overlay()
                    QMessageBox.critical(
                        self,
                        "Código de dispositivo inválido",
                        f"No se pudo validar el código del dispositivo hijo.\n\n{msg_codigo}"
                    )
                    self.btn_login.setEnabled(True)
                    return

                estado_hijo = str((dispositivo_hijo_validado or {}).get("estado", "activo")).strip().lower()
                if estado_hijo != "activo":
                    self._hide_login_loading_overlay()
                    QMessageBox.critical(
                        self,
                        "Dispositivo bloqueado",
                        "El código pertenece a un dispositivo hijo bloqueado. Actívalo desde el panel madre."
                    )
                    self.btn_login.setEnabled(True)
                    return
            except Exception as e:
                self._hide_login_loading_overlay()
                QMessageBox.critical(
                    self,
                    "Error de validación cloud",
                    f"No se pudo validar el código del dispositivo hijo en internet.\n\n{e}"
                )
                self.btn_login.setEnabled(True)
                return

        # Para modo trabajador (dispositivo hijo) se omiten bloqueos por PC única/sesión única.
        if not modo_dispositivo_hijo:
            # 🔒 VALIDAR DISPOSITIVO - Verificar que el usuario está en la PC correcta
            self._show_login_loading_overlay("Validando dispositivo...")
            print(f"\n[DEVICE_LOCK] Validando dispositivo para usuario '{nombre_ingresado}'...")
            try:
                from utils.device_lock import validar_dispositivo_usuario, registrar_usuario_en_dispositivo

                sesion_file = _get_sesion_file()
                base_dir = os.path.dirname(os.path.dirname(sesion_file))
                
                # Validar que el dispositivo sea correcto
                dispositivo_valido, mensaje_dispositivo = validar_dispositivo_usuario(base_dir, nombre_ingresado)
                
                if not dispositivo_valido:
                    # Dispositivo no coincide - Bloquear acceso
                    self._hide_login_loading_overlay()
                    logger.warning(f"[DEVICE_LOCK] Bloqueo: {mensaje_dispositivo}")
                    QMessageBox.critical(
                        self,
                        "Acceso Denegado - Dispositivo No Autorizado",
                        f"❌ Este usuario no puede acceder desde esta computadora.\n\n{mensaje_dispositivo}\n\n"
                        "Si crees que esto es un error, contacta al administrador.",
                        QMessageBox.Ok
                    )
                    self.btn_login.setEnabled(True)
                    return
                
                logger.info(f"[DEVICE_LOCK] {mensaje_dispositivo}")
                
                # Registrar el usuario en este dispositivo (si es primera vez)
                registrar_usuario_en_dispositivo(base_dir, nombre_ingresado, id_usuario_remoto)
            
            except Exception as e:
                print(f"[DEVICE_LOCK] Error en validación de dispositivo: {e}")
                import traceback
                traceback.print_exc()
                # No bloquear el acceso si hay error
            
            # 🔐 VALIDAR SESIÓN ÚNICA - Verificar que no está logueado en otra PC
            self._show_login_loading_overlay("Validando sesión...")
            print(f"\n[SESSION] Validando sesión única para '{nombre_ingresado}'...")
            try:
                from utils.device_lock import generar_device_id
                from utils.single_session import validar_sesion_unica, registrar_sesion_activa

                sesion_file = _get_sesion_file()
                base_dir = os.path.dirname(os.path.dirname(sesion_file))
                
                # Validar que no haya otra sesión activa
                sesion_valida, mensaje_sesion = validar_sesion_unica(base_dir, nombre_ingresado)
                
                if not sesion_valida:
                    # Sesión duplicada - Bloquear acceso
                    self._hide_login_loading_overlay()
                    logger.warning(f"[SESSION] {mensaje_sesion}")
                    QMessageBox.critical(
                        self,
                        "Sesión Activa en Otra PC",
                        mensaje_sesion,
                        QMessageBox.Ok
                    )
                    self.btn_login.setEnabled(True)
                    return
                
                logger.info("[SESSION] Sesión única validada")
                
                # Registrar sesión activa
                device_info = generar_device_id()
                registrar_sesion_activa(base_dir, nombre_ingresado, id_usuario_remoto, device_info)
            
            except Exception as e:
                print(f"[SESSION] Error en validación de sesión única: {e}")
                import traceback
                traceback.print_exc()
                # No bloquear el acceso si hay error
        
        # Guardar licencia localmente (oculta, para verificación offline)
        self._show_login_loading_overlay("Preparando datos...")
        from utils.license_manager import save_license_info
        save_license_info(
            user_id=id_usuario_remoto,
            username=nombre_ingresado,
            plan_type=plan_type,
            fecha_vencimiento=fecha_vencimiento or '',
            dias_restantes=dias_restantes
        )
        
        # Guardar en local también (sync)
        usuarios = cargar_usuarios()
        usuarios[id_usuario_remoto] = {
            'username': nombre_ingresado,
            'password': contrasena_ingresada
        }
        guardar_usuarios(usuarios)
        crear_directorios_usuario(id_usuario_remoto)
        
        # 🌐 DESCARGAR CLIENTES DESDE LA NUBE
        self._show_login_loading_overlay("Sincronizando datos iniciales...")
        print(f"\n[SYNC] Descargando clientes desde la BD remota con usuario_id='{id_usuario_remoto}'...")
        try:
            from utils.api_handler import obtener_clientes_remoto
            # id_usuario_remoto es el username (ahora retornado por login_license.php)
            clientes_remotos = obtener_clientes_remoto(id_usuario_remoto)
            if clientes_remotos:
                from utils.file_handler import guardar_clientes
                # Guardar con el username como clave
                guardar_clientes(nombre_ingresado, clientes_remotos)
                print(f"[SYNC] OK {len(clientes_remotos)} clientes descargados y guardados")
            else:
                print(f"[SYNC] Sin clientes en la nube")
        except Exception as e:
            print(f"[SYNC] Error descargando clientes: {e}")
        
        # Solo crear archivo de sesión si "Recordarme" está activado
        if self.chk_recordarme.isChecked():
            sesion_file = _get_sesion_file()
            with open(sesion_file, "w") as f:
                # Formato: "username:user_id" o "username:user_id:user" para usuario normal
                f.write(f"{nombre_ingresado}:{id_usuario_remoto}:user")
        else:
            sesion_file = _get_sesion_file()
            if os.path.exists(sesion_file):
                try:
                    os.remove(sesion_file)
                except Exception:
                    pass

        # Si se marcó como dispositivo hijo en login, guardar configuración local.
        if self.chk_dispositivo_hijo.isChecked():
            codigo_hijo = self.entry_codigo_dispositivo_hijo.text().strip().upper()
            self.guardar_config_dispositivo_hijo_login(
                nombre_ingresado,
                codigo_hijo,
                dispositivo_hijo_validado=dispositivo_hijo_validado
            )
        
        # Cerrar login window
        self._show_login_loading_overlay("Abriendo sistema...")
        self.close()
        
        # Abrir aplicación principal
        OpticaApp = _import_optica_app()
        self.main_app = OpticaApp(user_id=id_usuario_remoto, username=nombre_ingresado)
        self.main_app.show()

    def guardar_config_dispositivo_hijo_login(self, username, codigo_hijo, dispositivo_hijo_validado=None):
        """
        Guarda configuración de este equipo como dispositivo trabajador.
        Esta vinculación queda lista para validación/sincronización cloud.
        """
        try:
            if not username or not codigo_hijo:
                return

            from utils.file_handler import VISO_DIR
            config_path = os.path.join(VISO_DIR, username, "data", "config_dispositivo.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            config_data = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            config_data = loaded
                except Exception:
                    config_data = {}

            config_data.update({
                "tipo_dispositivo": "trabajador",
                "tipo_dispositivo_label": "Dispositivo trabajador",
                "codigo_dispositivo_hijo": codigo_hijo,
                "usuario_madre": username,
                "vinculado_desde_login": True,
                "updated_at": QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate),
            })

            # Priorizar metadata validada desde nube; fallback local si existe.
            child_device = dispositivo_hijo_validado or self.obtener_dispositivo_hijo_por_codigo(username, codigo_hijo)
            if child_device:
                config_data["dispositivo_hijo_id"] = child_device.get("id")
                config_data["dispositivo_hijo_nombre"] = child_device.get("nombre_optica")
                config_data["dispositivo_hijo_ciudad"] = child_device.get("ciudad")
                config_data["dispositivo_hijo_estado"] = child_device.get("estado")

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.warning("No se pudo guardar config de dispositivo hijo en login: %s", e)

    def obtener_dispositivo_hijo_por_codigo(self, username, codigo_hijo):
        """Busca dispositivo hijo por código en el catálogo local del usuario."""
        try:
            from utils.file_handler import VISO_DIR
            child_path = os.path.join(VISO_DIR, username, "data", "dispositivos_hijos.json")
            if not os.path.exists(child_path):
                return None

            with open(child_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return None

            codigo_ref = str(codigo_hijo).strip().upper()
            for item in data:
                if not isinstance(item, dict):
                    continue
                if str(item.get("codigo_dispositivo", "")).strip().upper() == codigo_ref:
                    return item
        except Exception:
            return None
        return None

    def guardar_preferencia_recordarme(self, estado):
        """Guarda la preferencia del checkbox recordarme."""
        preferencias = cargar_preferencias()
        preferencias['recordarme'] = bool(estado)
        guardar_preferencias(preferencias)

    def abrir_registro(self):
        """Abre el navegador con la página de registro web."""
        url = "https://api.yhana.cloud/panel/registro.php"
        webbrowser.open(url)

    def mostrar_login_ayudante(self):
        """Cambia a la pantalla de login de ayudantes."""
        if not hasattr(self, 'helper_login_page'):
            self.setup_helper_login_page()
        self.stacked_widget.setCurrentWidget(self.helper_login_page)
    
    def mostrar_login_jefe(self):
        """Vuelve a la pantalla de login del jefe."""
        self.stacked_widget.setCurrentWidget(self.login_page)
    
    def setup_helper_login_page(self):
        """Configura la página de login para ayudantes."""
        self.helper_login_page = QtWidgets.QWidget()
        helper_layout = QtWidgets.QVBoxLayout(self.helper_login_page)
        helper_layout.setContentsMargins(30, 30, 30, 30)
        helper_layout.setSpacing(15)
        
        # Título
        titulo = QtWidgets.QLabel("Login de Ayudante")
        titulo.setAlignment(QtCore.Qt.AlignCenter)
        titulo.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2196F3;
                margin-bottom: 10px;
            }
        """)
        helper_layout.addWidget(titulo)
        
        # Subtítulo
        subtitulo = QtWidgets.QLabel("Ingresa tu usuario y contraseña de ayudante")
        subtitulo.setAlignment(QtCore.Qt.AlignCenter)
        subtitulo.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #888;
                margin-bottom: 20px;
            }
        """)
        helper_layout.addWidget(subtitulo)
        
        # Campos
        fields_container = QtWidgets.QWidget()
        fields_container.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 8px;
                border: none;
            }
            QLineEdit {
                color: #333333;
                background: white;
                font-size: 14px;
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
            QLineEdit::placeholder {
                color: #BDBDBD;
            }
        """)
        fields_layout = QtWidgets.QVBoxLayout(fields_container)
        fields_layout.setContentsMargins(15, 15, 15, 15)
        fields_layout.setSpacing(12)
        
        # Usuario del Jefe (para buscar ayudantes)
        self.entry_username_jefe = QtWidgets.QLineEdit()
        self.entry_username_jefe.setPlaceholderText("Ingresa el usuario del jefe")
        self.entry_username_jefe.setMinimumHeight(36)
        fields_layout.addWidget(self.entry_username_jefe)
        
        # Usuario del Ayudante
        self.entry_username_helper = QtWidgets.QLineEdit()
        self.entry_username_helper.setPlaceholderText("Tu usuario")
        self.entry_username_helper.setMinimumHeight(36)
        fields_layout.addWidget(self.entry_username_helper)
        
        # Contraseña
        self.entry_pass_helper = QtWidgets.QLineEdit()
        self.entry_pass_helper.setPlaceholderText("Tu contraseña")
        self.entry_pass_helper.setEchoMode(QtWidgets.QLineEdit.Password)
        self.entry_pass_helper.setMinimumHeight(36)
        fields_layout.addWidget(self.entry_pass_helper)
        
        helper_layout.addWidget(fields_container)
        
        # Botón Login
        self.btn_login_helper = QtWidgets.QPushButton("Iniciar Sesión como Ayudante")
        self.btn_login_helper.setObjectName("primaryButton")
        self.btn_login_helper.clicked.connect(self.iniciar_sesion_ayudante)
        self.btn_login_helper.setMinimumHeight(36)
        self.btn_login_helper.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: 600;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
                padding-top: 9px;
            }
        """)
        helper_layout.addWidget(self.btn_login_helper)
        
        # Botón Volver
        btn_volver = QtWidgets.QPushButton("← Volver al login principal")
        btn_volver.setFlat(True)
        btn_volver.setCursor(QtCore.Qt.PointingHandCursor)
        btn_volver.clicked.connect(self.mostrar_login_jefe)
        btn_volver.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #2196F3;
                font-size: 12px;
                padding: 4px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #1565C0;
            }
        """)
        helper_layout.addWidget(btn_volver, alignment=QtCore.Qt.AlignCenter)
        
        helper_layout.addStretch()
        
        self.stacked_widget.addWidget(self.helper_login_page)
    
    def iniciar_sesion_ayudante(self):
        """Autentica un ayudante."""
        username_jefe = self.entry_username_jefe.text().strip()
        username_helper = self.entry_username_helper.text().strip()
        password_helper = self.entry_pass_helper.text().strip()
        
        if not username_jefe or not username_helper or not password_helper:
            QMessageBox.warning(
                self,
                "Campos Vacíos",
                "Por favor, completa todos los campos."
            )
            return
        
        from utils.helpers_manager import (
            obtener_ayudante_por_usuario, verify_password,
            registrar_conexion_ayudante, obtener_modulos_permitidos
        )

        # Obtener ayudante
        ayudante = obtener_ayudante_por_usuario(username_jefe, username_helper)
        
        if not ayudante:
            QMessageBox.critical(
                self,
                "Error de Autenticación",
                f"Ayudante '{username_helper}' no encontrado para el jefe '{username_jefe}'."
            )
            return
        
        # Verificar que esté activo
        if not ayudante.get('activo', False):
            QMessageBox.critical(
                self,
                "Cuenta Desactivada",
                "Este ayudante ha sido desactivado. Contacta a tu jefe."
            )
            return
        
        # Verificar contraseña
        if not verify_password(password_helper, ayudante.get('password_hash', '')):
            QMessageBox.critical(
                self,
                "Error de Autenticación",
                "Usuario o contraseña incorrectos."
            )
            self.entry_pass_helper.clear()
            return
        
        # ✅ Autenticación exitosa - Mostrar animación breve
        self.animation = LoadingAnimation(self.btn_login_helper)
        self.animation.start()
        self.btn_login_helper.setEnabled(False)
        
        # Registrar conexión
        registrar_conexion_ayudante(username_jefe, username_helper)
        
        # Guardar sesión de ayudante
        try:
            sesion_file = _get_sesion_file()
            with open(sesion_file, "w") as f:
                # Formato: "usuario_jefe:usuario_ayudante:tipo=helper"
                f.write(f"{username_jefe}:{username_helper}:helper")
        except Exception:
            pass
        
        # Obtener módulos permitidos
        modulos_permitidos = obtener_modulos_permitidos(username_jefe, username_helper)
        
        # Detener animación y cerrar login
        self.animation.stop()
        self.close()
        
        # ✅ Obtener user_id del jefe desde .usuarios.json
        try:
            usuarios = cargar_usuarios()
            jefe_user_id = None
            for uid, udata in usuarios.items():
                if udata.get("username") == username_jefe:
                    jefe_user_id = uid
                    break
            
            if not jefe_user_id:
                # Fallback: usar el username como user_id si no se encuentra
                jefe_user_id = username_jefe
                print(f"[WARNING] No se encontró user_id para {username_jefe}, usando username")
        except Exception as e:
            print(f"[WARNING] Error al obtener user_id del jefe: {e}")
            jefe_user_id = username_jefe
        
        # Abrir la app
        OpticaApp = _import_optica_app()
        self.main_app = OpticaApp(
            user_id=jefe_user_id,
            username=username_jefe,
            is_helper=True,
            helper_name=username_helper,
            allowed_modules=modulos_permitidos
        )
        self.main_app.show()

