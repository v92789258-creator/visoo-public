"""
Sistema centralizado de logging para VISO.
Proporciona logging consistente con niveles de severidad en toda la aplicación.
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Directorio de logs
LOG_DIR = Path(os.path.expanduser("~")) / ".viso" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Archivo de log principal
LOG_FILE = LOG_DIR / f"viso_{datetime.now().strftime('%Y%m%d')}.log"

# Niveles de severidad
CRITICAL = logging.CRITICAL  # 50
ERROR = logging.ERROR        # 40
WARNING = logging.WARNING    # 30
INFO = logging.INFO          # 20
DEBUG = logging.DEBUG        # 10


class ColoredFormatter(logging.Formatter):
    """Formateador con colores para consola."""
    
    COLORS = {
        logging.DEBUG: '\033[36m',      # Cyan
        logging.INFO: '\033[32m',       # Green
        logging.WARNING: '\033[33m',    # Yellow
        logging.ERROR: '\033[31m',      # Red
        logging.CRITICAL: '\033[1;31m', # Bold Red
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if sys.platform.startswith('win'):
            # Windows no soporta ANSI colors en cmd.exe nativo
            return super().format(record)
        
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class VISOLogger:
    """Logger centralizado para VISO con múltiples handlers."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if VISOLogger._initialized:
            return
        
        self.logger = logging.getLogger('VISO')
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar agregar handlers múltiples
        if self.logger.handlers:
            return
        
        # Formato consistente
        log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # Handler para archivo (sin colores)
        try:
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(log_format, date_format))
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"[ERROR] No se pudo crear handler de archivo: {e}")
        
        # Handler para consola (con colores en Linux/Mac)
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = ColoredFormatter(log_format, date_format)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        except Exception as e:
            print(f"[ERROR] No se pudo crear handler de consola: {e}")
        
        VISOLogger._initialized = True
    
    def get_logger(self, name='VISO'):
        """Obtiene un logger con el nombre especificado."""
        return logging.getLogger(name)
    
    def debug(self, message, *args, **kwargs):
        """Log en nivel DEBUG."""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        """Log en nivel INFO."""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """Log en nivel WARNING."""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        """Log en nivel ERROR."""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        """Log en nivel CRITICAL."""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message, *args, **kwargs):
        """Log de excepción con stack trace."""
        self.logger.exception(message, *args, **kwargs)


# Instancia global singleton
_logger_instance = VISOLogger()


def get_logger(name='VISO'):
    """Función de utilidad para obtener logger de VISO."""
    return _logger_instance.get_logger(name)


def log_debug(message):
    """Log rápido en DEBUG."""
    _logger_instance.debug(message)


def log_info(message):
    """Log rápido en INFO."""
    _logger_instance.info(message)


def log_warning(message):
    """Log rápido en WARNING."""
    _logger_instance.warning(message)


def log_error(message):
    """Log rápido en ERROR."""
    _logger_instance.error(message)


def log_critical(message):
    """Log rápido en CRITICAL."""
    _logger_instance.critical(message)


def log_exception(message):
    """Log rápido de excepción."""
    _logger_instance.exception(message)
