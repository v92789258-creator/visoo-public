"""ConfiguraciÃ³n de logging centralizada"""
import os
import sys
import io
import logging

from .settings import LOG_DIR, IS_FROZEN, APP_NAME

class DualWriter:
    """Escribe en mÃºltiples outputs simultÃ¡neamente"""
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


def _resolve_console_stream():
    """Devuelve el stream real de consola si existe."""
    for candidate in (
        getattr(sys, "__stderr__", None),
        getattr(sys, "__stdout__", None),
        getattr(sys, "stderr", None),
        getattr(sys, "stdout", None),
    ):
        if getattr(candidate, "write", None):
            return candidate
    return None

def setup_logging():
    """Configura logging para archivo y consola"""
    try:
        # Crear directorio de logs
        os.makedirs(LOG_DIR, exist_ok=True)
        
        log_file = os.path.join(LOG_DIR, 'app.log')
        
        # En ejecutables sin consola, sys.stdout/sys.stderr pueden ser None.
        # Eso rompe StreamHandler y tambiÃ©n varios prints/tracebacks.
        if IS_FROZEN:
            # Evitar que errores internos del logging intenten escribir a stderr inexistente
            logging.raiseExceptions = False
            
            # Abrir en append para no truncar logs anteriores
            log_handle = open(log_file, 'a', encoding='utf-8', buffering=1)
            
            # Si no hay consola, usar un buffer en memoria como fallback seguro
            if sys.stdout is None:
                sys.stdout = io.StringIO()
            if sys.stderr is None:
                sys.stderr = io.StringIO()
            
            # Duplicar salida hacia el archivo de log
            sys.stdout = DualWriter(sys.stdout, log_handle)
            sys.stderr = DualWriter(sys.stderr, log_handle)
            
            # Mensajes de arranque
            print(f"\n[LOG] === {APP_NAME} INICIADO ===")
            print(f"[LOG] Log guardado en: {log_file}\n")
        
        # Configurar handlers de forma robusta
        handlers = [logging.FileHandler(log_file, encoding='utf-8')]
        console_stream = _resolve_console_stream()
        if console_stream is not None:
            handlers.append(logging.StreamHandler(console_stream))
        
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            handlers=handlers
        )
        
        return logging.getLogger(__name__)
    
    except Exception as e:
        print(f"[WARNING] No se pudo configurar logging: {e}")
        return logging.getLogger(__name__)

def setup_hidpi():
    """Configura escalado automatico para pantallas HiDPI"""
    try:
        from PyQt5 import QtWidgets, QtCore
        # Estos atributos solo se pueden establecer antes de crear QApplication.
        if QtWidgets.QApplication.instance() is None:
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    except Exception as e:
        print(f"[WARNING] No se pudo configurar HiDPI: {e}")

