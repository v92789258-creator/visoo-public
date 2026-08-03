"""Clase principal de la aplicación"""
import logging
from PyQt5 import QtWidgets, QtGui

from core.config.settings import ICON_PATH
from core.startup.instance import single_instance

logger = logging.getLogger(__name__)

class SingletonApplication:
    """Aplicación Qt con control de instancia única"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
    
    def initialize(self):
        """Inicializa la aplicación Qt y verifica instancia única"""
        try:
            # Crear la aplicación Qt
            self.app = QtWidgets.QApplication.instance()
            if self.app is None:
                self.app = QtWidgets.QApplication([])
                if ICON_PATH:
                    try:
                        self.app.setWindowIcon(QtGui.QIcon(ICON_PATH))
                    except Exception:
                        pass
            
            # Verificar instancia única
            with single_instance() as can_run:
                if not can_run:
                    QtWidgets.QMessageBox.warning(
                        None,
                        'VISO ya está en ejecución',
                        'Ya hay una instancia de VISO ejecutándose.\n\n'
                        'Por favor, cierre la otra ventana antes de abrir una nueva.'
                    )
                    return False
            
            logger.info("✅ Aplicación Qt inicializada correctamente")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error al inicializar aplicación: {e}", exc_info=True)
            return False
