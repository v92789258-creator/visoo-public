"""
VISO - Sistema de Gestión Óptica
Punto de entrada principal de la aplicación
"""
import os
import sys
import logging
import json
import time
import traceback

# Rutas de logs tempranas (antes de inicializar Qt)
try:
    from core.config.settings import TEMP_DIR as _TEMP_DIR, FATAL_LOG_FILE as _FATAL_LOG_FILE
except Exception:
    _TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VISO", "temp")
    _FATAL_LOG_FILE = os.path.join(_TEMP_DIR, "fatal.log")

# Capturar trazas si hay crash duro (segfault/abort) para poder diagnosticar.
try:
    import faulthandler

    os.makedirs(os.path.dirname(_FATAL_LOG_FILE), exist_ok=True)
    _fh = open(_FATAL_LOG_FILE, "a", buffering=1, encoding="utf-8")
    faulthandler.enable(file=_fh, all_threads=True)
except Exception:
    pass

# Deshabilitar warnings de PIL sobre módulos opcionales faltantes
import warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

# ============================================================================
# MOSTRAR SPLASH SCREEN AL INICIAR (PyQt5 nativo)
# ============================================================================
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer

# ESTABLECER ATRIBUTOS ANTES DE CREAR QApplication
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

class SafeApplication(QApplication):
    """QApplication que captura excepciones dentro del loop Qt (slots/events) para loggear en fatal.log."""

    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception:
            try:
                os.makedirs(os.path.dirname(_FATAL_LOG_FILE), exist_ok=True)
                with open(_FATAL_LOG_FILE, "a", encoding="utf-8") as fh:
                    fh.write("\n----- QT NOTIFY EXCEPTION -----\n")
                    traceback.print_exc(file=fh)
            except Exception:
                pass
            try:
                logging.getLogger(__name__).exception("[QT] Excepción no manejada en notify()")
            except Exception:
                pass
            return False


class StartupSpinner(QLabel):
    """Loader circular ultra liviano para el arranque."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("color: #2563EB; font-size: 18px; font-weight: 700;")
        self._frames = ("◜", "◝", "◞", "◟")
        self._index = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(90)
        self._tick()

    def _tick(self):
        self.setText(self._frames[self._index % len(self._frames)])
        self._index += 1


class StartupLoadingDialog(QDialog):
    """Modal de carga ligero para el arranque."""

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setFixedSize(220, 118)
        self.setStyleSheet(
            """
            QDialog {
                background: #FFFFFF;
                border: 1px solid #D7DEEA;
                border-radius: 14px;
            }
            QLabel {
                color: #0F172A;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#StartupBrand {
                color: #0F172A;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#StartupSubtitle {
                color: #64748B;
                font-size: 10px;
                font-weight: 500;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        self.brand_label = QLabel("Yhana para Opticas")
        self.brand_label.setObjectName("StartupBrand")
        self.brand_label.setAlignment(Qt.AlignCenter)

        self.spinner = StartupSpinner(self)

        self.title_label = QLabel("Cargando")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.subtitle_label = QLabel("Preparando inicio")
        self.subtitle_label.setObjectName("StartupSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.brand_label)
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

    def showEvent(self, event):
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.center().x() - (self.width() // 2)
            y = screen.center().y() - (self.height() // 2)
            self.move(x, y)
        except Exception:
            pass
        super().showEvent(event)

app = SafeApplication(sys.argv)

# Redirigir stderr y mensajes de Qt a archivo (para diagnosticar crashes al abrir ventanas).
try:
    from PyQt5 import QtCore as _QtCore

    class _DualWriter:
        def __init__(self, *writers):
            self.writers = [w for w in writers if w is not None]

        def write(self, text):
            for writer in self.writers:
                try:
                    writer.write(text)
                    writer.flush()
                except Exception:
                    pass

        def flush(self):
            for writer in self.writers:
                try:
                    writer.flush()
                except Exception:
                    pass

    _log_dir = str(_TEMP_DIR or os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
    os.makedirs(_log_dir, exist_ok=True)

    _stderr_path = os.path.join(_log_dir, "runtime_stderr.log")
    _qtmsg_path = os.path.join(_log_dir, "qt_messages.log")
    _orig_stderr = getattr(sys, "__stderr__", None) or getattr(sys, "stderr", None)

    try:
        _stderr_f = open(_stderr_path, "a", buffering=1, encoding="utf-8")
        if getattr(_orig_stderr, "write", None):
            sys.stderr = _DualWriter(_orig_stderr, _stderr_f)
        else:
            sys.stderr = _stderr_f
    except Exception:
        _stderr_f = None

    _qtmsg_f = open(_qtmsg_path, "a", buffering=1, encoding="utf-8")

    def _qt_message_handler(mode, context, message):
        try:
            _qtmsg_f.write(str(message or "") + "\n")
            _qtmsg_f.flush()
        except Exception:
            pass

    _QtCore.qInstallMessageHandler(_qt_message_handler)
except Exception:
    pass

# Normalizar textos de diálogos (tildes/caracteres rotos) automáticamente
try:
    from gui.ui_text_normalization import DialogTextNormalizer

    _dialog_text_normalizer = DialogTextNormalizer(app)
    app.installEventFilter(_dialog_text_normalizer)
    # Mantener referencia viva
    app._dialog_text_normalizer = _dialog_text_normalizer
except Exception:
    pass

# Obtener la ruta correcta según si se ejecuta desde Python o desde PyInstaller
if getattr(sys, 'frozen', False):
    # Se ejecuta desde PyInstaller
    base_path = sys._MEIPASS
else:
    # Se ejecuta desde Python
    base_path = os.path.dirname(os.path.abspath(__file__))

# Cargar y mostrar splash screen - OPTIMIZADO PARA VELOCIDAD
# En ejecutable compilado preferimos SOLO el splash nativo del bootloader.
# Aunque falle la deteccion de pyi_splash, no crear un segundo QSplashScreen.
splash_pix = None
splash = None
_BOOTLOADER_SPLASH_ACTIVE = False
_ALLOW_QT_SPLASH = not getattr(sys, 'frozen', False)


def _has_bootloader_splash():
    if not getattr(sys, 'frozen', False):
        return False
    try:
        import pyi_splash  # noqa: F401
        return True
    except Exception:
        return False

_BOOTLOADER_SPLASH_ACTIVE = _has_bootloader_splash()


def _close_bootloader_splash():
    global _BOOTLOADER_SPLASH_ACTIVE
    if not _BOOTLOADER_SPLASH_ACTIVE:
        return
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass
    finally:
        _BOOTLOADER_SPLASH_ACTIVE = False


def _finish_startup_splash(target_widget=None):
    global splash
    try:
        if splash is not None:
            if target_widget is not None and hasattr(splash, "finish"):
                splash.finish(target_widget)
            else:
                splash.close()
            splash = None
    except Exception:
        pass
    _close_bootloader_splash()

try:
    if _ALLOW_QT_SPLASH and not _BOOTLOADER_SPLASH_ACTIVE:
        splash = StartupLoadingDialog()
        splash.show()
        app.processEvents()  # Procesar eventos una sola vez
except:
    pass  # Ignorar errores de splash silenciosamente

# ============================================================================
# CONFIGURACIÓN INICIAL - OPTIMIZADA
# ============================================================================
# PyInstaller fix - RÁPIDO
if getattr(sys, 'frozen', False):
    sys._MEIPASS = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    os.environ['PYTHONPATH'] = sys._MEIPASS

# Configurar logging DESPUÉS del splash (más rápido)
try:
    from core.config.logging_config import setup_logging, setup_hidpi
    setup_logging()
    setup_hidpi()
    logger = logging.getLogger(__name__)
except:
    logger = logging.getLogger(__name__)  # Fallback rápido

# Lazy imports - solo cargar cuando sea necesario
try:
    from core.config.settings import BASE_DIR, APP_NAME, VISO_DIR
    from core.startup.dependencies import check_dependencies
    from core.startup.exceptions_handler import setup_exception_handlers
    from core.app import SingletonApplication
    setup_exception_handlers()
except:
    pass  # Ignorar errores no críticos


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def import_login():
    """Importa LoginWindow"""
    try:
        from gui.login_window import LoginWindow
        return LoginWindow
    except ImportError as e:
        logger.error(f"❌ No se pudo cargar LoginWindow: {e}", exc_info=True)
        raise

def import_main_window():
    """Importa OpticaApp"""
    try:
        from gui.main_window import OpticaApp
        return OpticaApp
    except ImportError as e:
        logger.error(f"❌ No se pudo cargar OpticaApp: {e}", exc_info=True)
        raise

def import_terms_dialog():
    """Importa TermsDialog"""
    try:
        from gui.dialogs.terms_dialog import TermsDialog
        return TermsDialog
    except ImportError as e:
        logger.error(f"❌ No se pudo cargar TermsDialog: {e}", exc_info=True)
        raise


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def main(app_instance):
    """Función principal que orquesta el inicio de la aplicación"""
    if not check_dependencies():
        from PyQt5 import QtWidgets
        _finish_startup_splash()
        QtWidgets.QMessageBox.critical(
            None,
            "Error de Dependencias",
            "Faltan dependencias críticas. Por favor ejecute:\npip install -r requirements.txt"
        )
        return False
    
    try:
        if not app_instance or not app_instance.app:
            logger.error("❌ No hay instancia de aplicación válida")
            return False
        
        # Verificar términos y condiciones
        try:
            TermsDialog = import_terms_dialog()
            if not TermsDialog.has_accepted():
                _finish_startup_splash()
                terms_dialog = TermsDialog()
                if terms_dialog.exec_() != QtWidgets.QDialog.Accepted:
                    return False
        except Exception as e:
            logger.warning(f"⚠️ Error al verificar términos: {e}")
        
        # Continuar con el startup
        return _continue_startup(app_instance)
    
    except Exception as e:
        logger.error(f"❌ Error en main(): {e}", exc_info=True)
        return False

def _continue_startup(app_instance):
    """Continúa el proceso de startup después de verificar términos"""
    from PyQt5 import QtWidgets
    
    try:
        app_instance.app.processEvents()
    except Exception as e:
        logger.warning(f"⚠️ Error procesando eventos: {e}")
    
    try:
        sesion_file_path = os.path.join(VISO_DIR, "sesion.txt")
        
        # Verificar si hay sesión guardada
        if os.path.exists(sesion_file_path):
            try:
                with open(sesion_file_path, "r", encoding="utf-8") as f:
                    user_id = f.read().strip()
                
                if not user_id:
                    logger.warning("⚠️ Archivo de sesión está vacío")
                    try:
                        os.remove(sesion_file_path)
                    except:
                        pass
                    raise ValueError("Session file is empty")
                
                # Verificar si es sesión de ayudante o usuario normal
                if _load_user_session(app_instance, user_id, sesion_file_path):
                    return True
                
                logger.warning("⚠️ No se pudo cargar sesión, requiere login")
                try:
                    os.remove(sesion_file_path)
                except:
                    pass
            
            except (json.JSONDecodeError, ValueError, IOError) as e:
                logger.warning(f"⚠️ Error al cargar sesión: {e}")
                try:
                    os.remove(sesion_file_path)
                except:
                    pass
            except Exception as e:
                logger.error(f"❌ Error inesperado al cargar sesión: {e}", exc_info=True)
                try:
                    os.remove(sesion_file_path)
                except:
                    pass
        
        # Si no hay sesión, mostrar login
        try:
            LoginWindow = import_login()
            login_window = LoginWindow()
            login_window.show()
            _finish_startup_splash(login_window)
            logger.info("✅ Ventana de login mostrada")
            return True
        except Exception as e:
            logger.error(f"❌ Error al cargar LoginWindow: {e}", exc_info=True)
            _finish_startup_splash()
            QtWidgets.QMessageBox.critical(
                None,
                "Error de Carga",
                f"No se pudo cargar ventana de login:\n{str(e)}"
            )
            return False
    
    except Exception as e:
        logger.error(f"❌ Error inesperado en startup: {e}", exc_info=True)
        _finish_startup_splash()
        QtWidgets.QMessageBox.critical(
            None,
            "Error",
            f"Error durante el inicio:\n{str(e)}"
        )
        return False

def _load_user_session(app_instance, user_id, sesion_file_path):
    """Carga una sesión de usuario guardada"""
    try:
        usuarios_path = os.path.join(BASE_DIR, "VISO", ".usuarios.json")
        if not os.path.exists(usuarios_path):
            logger.warning("⚠️ Archivo de usuarios no encontrado")
            return False
        
        with open(usuarios_path, "r", encoding="utf-8") as uf:
            usuarios = json.load(uf)
        
        # Parsear tipo de sesión (helper, user, legacy)
        is_helper_session = False
        is_user_session = False
        username = None
        helper_name = None
        allowed_modules = []
        
        if ":" in user_id:
            parts = user_id.split(":")
            if len(parts) == 3:
                session_type = parts[2]
                if session_type == "helper":
                    is_helper_session = True
                    username = parts[0]
                    helper_name = parts[1]
                    user_id = username
                elif session_type == "user":
                    is_user_session = True
                    username = parts[0]
                    user_id = parts[1]
        
        # Determinar username y validar usuario
        if not username:
            user_data = usuarios.get(user_id)
            if user_data:
                username = user_data.get("username")
        
        if not username:
            logger.warning(f"⚠️ No se encontró usuario: {user_id}")
            return False
        
        logger.info(f"✅ Sesión recuperada: {username}")
        
        # Obtener módulos permitidos si es helper
        if is_helper_session:
            try:
                from utils.helpers_manager import obtener_modulos_permitidos
                allowed_modules = obtener_modulos_permitidos(username, helper_name)
            except Exception as e:
                logger.warning(f"⚠️ Error al obtener módulos: {e}")
        
        # Cargar la aplicación principal
        on_resources_loaded(
            app_instance, user_id, username,
            is_helper=is_helper_session,
            helper_name=helper_name,
            allowed_modules=allowed_modules
        )
        return True
    
    except Exception as e:
        logger.error(f"❌ Error cargando sesión: {e}", exc_info=True)
        return False

def on_resources_loaded(app_instance, user_id, username, is_helper=False, helper_name=None, allowed_modules=None):
    """Se ejecuta cuando los recursos han sido cargados y la sesión es válida"""
    import logging
    import datetime
    import time
    from PyQt5.QtCore import QTimer, QThread, pyqtSignal
    
    OpticaApp = import_main_window()
    
    # Crear ventana principal
    if is_helper:
        app_instance.main_window = OpticaApp(
            user_id=user_id,
            username=username,
            is_helper=True,
            helper_name=helper_name,
            allowed_modules=allowed_modules or []
        )
    else:
        app_instance.main_window = OpticaApp(user_id=user_id, username=username)
    
    logger.info("✅ Ventana principal creada")
    app_instance.main_window.app_instance = app_instance
    app_instance.main_window.resize(400, 300)
    app_instance.main_window.showMaximized()
    
    # Conectar señal de UI lista para cerrar splash
    if ('splash' in globals() and splash is not None) or _BOOTLOADER_SPLASH_ACTIVE:
        app_instance.main_window.ui_ready.connect(
            lambda: _finish_startup_splash(app_instance.main_window)
        )
    
    # Emitir señal cuando UI está lista - REDUCIDO A 20ms PARA MÁXIMA VELOCIDAD
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(20, app_instance.main_window.ui_ready.emit)
    
    # Inicializar auditoría
    try:
        from utils.audit_manager import init_audit_manager
        audit_mgr = init_audit_manager(BASE_DIR)
        app_instance.audit_manager = audit_mgr
        
        audit_mgr.log_action(
            user_id, username,
            helper_name if is_helper else None,
            'login', 'sistema',
            f"{'Ayudante' if is_helper else 'Usuario'} inició sesión"
        )
    except Exception as e:
        logger.warning(f"⚠️ Error al inicializar auditoría: {e}")
    
    # Configurar backup automático (desactivado)
    _setup_backup_thread(app_instance, user_id)

    # [ELIMINADO] La subida inicial automática en background ya no se ejecuta aquí.
    # Ahora se gestiona en MainWindow para mostrar un modal obligatorio si no hay datos en la nube.


def _setup_backup_thread(app_instance, user_id):
    """Configura el thread de backup automático (actualmente desactivado)"""
    from PyQt5.QtCore import QThread, pyqtSignal, QTimer
    import logging
    from utils.local_backup_manager import ensure_weekly_local_backup

    logger = logging.getLogger(__name__)
    
    class RespaldoThread(QThread):
        finished = pyqtSignal(str)
        
        def __init__(self, usuario_id, parent=None):
            super().__init__(parent)
            self.usuario_id = usuario_id
            self._is_cancelled = False
            self._is_running = False
        
        def cancel(self):
            self._is_cancelled = True
        
        def cleanup(self):
            try:
                self._is_cancelled = True
                if self.isRunning():
                    self.quit()
                    self.wait(1000)
            except Exception:
                pass
        
        def run(self):
            """Ejecuta backup en thread separado"""
            self._is_running = True
            try:
                if not requests:
                    self.finished.emit("❌ Error: librería requests no instalada")
                    return
                
                # Lógica de backup aquí
                logger.info(f"[BACKUP] Respaldo para usuario {self.usuario_id}")
                self.finished.emit("✅ Respaldo completado")
            
            except Exception as e:
                logger.error(f"❌ Error en backup: {e}", exc_info=True)
                self.finished.emit(f"❌ Error: {e}")
            
            finally:
                self._is_running = False
                self._is_cancelled = False

    def _run_local_backup(self):
        self._is_running = True
        try:
            if self._is_cancelled:
                self.finished.emit("Backup cancelado")
                return

            ok, message, backup_path = ensure_weekly_local_backup(self.usuario_id)
            if backup_path:
                logger.info("[BACKUP] Respaldo local generado en %s", backup_path)
            if ok:
                self.finished.emit(message)
            else:
                self.finished.emit(f"Error backup local: {message}")
        except Exception as e:
            logger.error("[BACKUP] Error en backup local: %s", e, exc_info=True)
            self.finished.emit(f"Error backup local: {e}")
        finally:
            self._is_running = False
            self._is_cancelled = False

    RespaldoThread.run = _run_local_backup
    
    # Configurar atributos
    app_instance.main_window._backup_thread = None
    app_instance.main_window._backup_timer = QTimer(app_instance.main_window)
    app_instance.main_window._backup_active = False

    def start_backup_if_idle():
        try:
            current = getattr(app_instance.main_window, '_backup_thread', None)
            if current is not None and hasattr(current, 'isRunning') and current.isRunning():
                return

            username = getattr(app_instance.main_window, 'username', None) or user_id
            username = str(username or "").strip()
            if not username:
                return

            thread = RespaldoThread(username, app_instance.main_window)
            app_instance.main_window._backup_thread = thread

            def on_finished(message):
                logger.info("[BACKUP] %s", message)
                app_instance.main_window._backup_active = False
                app_instance.main_window._backup_thread = None

            app_instance.main_window._backup_active = True
            thread.finished.connect(on_finished)
            thread.finished.connect(thread.deleteLater)
            thread.start()
        except Exception as exc:
            logger.warning("[BACKUP] No se pudo iniciar backup automatico: %s", exc)
    
    def cleanup_backup():
        """Limpia el thread al cerrar"""
        try:
            thr = getattr(app_instance.main_window, '_backup_thread', None)
            if thr is not None and hasattr(thr, 'isRunning'):
                if thr.isRunning():
                    thr.quit()
                    thr.wait(2000)
        except Exception:
            pass
    
    try:
        app_instance.main_window._backup_timer.setInterval(6 * 60 * 60 * 1000)
        app_instance.main_window._backup_timer.timeout.connect(start_backup_if_idle)
        app_instance.main_window._backup_timer.start()
        QTimer.singleShot(45 * 1000, start_backup_if_idle)
    except Exception as exc:
        logger.warning("[BACKUP] No se pudo programar backup local: %s", exc)

    app_instance.main_window.destroyed.connect(cleanup_backup)
    logger.info("✅ Sistema de backup configurado")

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    # Check for LAN server mode before starting GUI
    if "--server" in sys.argv:
        print("LAN deshabilitado: el modo servidor ya no esta disponible.")
        sys.exit(0)

    try:
        # Crear instancia de aplicación
        app_instance = SingletonApplication()
        
        if app_instance.initialize():
            logger.info("✅ Aplicación inicializada")
            if main(app_instance):
                logger.info("✅ Iniciando event loop Qt")
                exit_code = app_instance.app.exec_()
                sys.exit(exit_code)
            else:
                logger.error("❌ main() retornó False")
                if getattr(sys, 'frozen', False):
                    input("\nPresiona ENTER para cerrar...")
                sys.exit(1)
        else:
            logger.error("❌ No se pudo inicializar aplicación")
            if getattr(sys, 'frozen', False):
                input("\nPresiona ENTER para cerrar...")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}", exc_info=True)
        if getattr(sys, 'frozen', False):
            input("\nPresiona ENTER para cerrar...")
        sys.exit(1)
 
