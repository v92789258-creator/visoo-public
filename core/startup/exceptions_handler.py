"""Manejo global de excepciones"""
import sys
import traceback
import logging

from core.config.settings import FATAL_LOG_FILE

logger = logging.getLogger(__name__)

def setup_exception_handlers():
    """Configura los manejadores globales de excepciones"""
    sys.excepthook = _global_excepthook
    
    try:
        import threading
        if hasattr(threading, 'excepthook'):
            threading.excepthook = _thread_excepthook
    except Exception:
        pass

def _write_fatal(exc_type, exc_value, exc_tb):
    """Escribe excepciones fatales en un archivo de log"""
    try:
        with open(FATAL_LOG_FILE, 'a', encoding='utf-8') as fh:
            fh.write(f"\n----- UNHANDLED EXCEPTION ({exc_type.__name__}) -----\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=fh)
    except Exception:
        traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stderr)

def _global_excepthook(exc_type, exc_value, exc_tb):
    """Manejador global de excepciones del hilo principal"""
    if exc_type is KeyboardInterrupt:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    try:
        _write_fatal(exc_type, exc_value, exc_tb)
    finally:
        sys.__excepthook__(exc_type, exc_value, exc_tb)

def _thread_excepthook(args):
    """Manejador de excepciones en threads"""
    if args.exc_type is KeyboardInterrupt:
        return
    _write_fatal(args.exc_type, args.exc_value, args.exc_traceback)
