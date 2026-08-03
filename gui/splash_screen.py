"""Splash screen simple y rápido para VISO"""
from PyQt5.QtWidgets import QSplashScreen, QApplication
from PyQt5.QtGui import QPixmap, QColor, QFont
from PyQt5.QtCore import Qt
import os


def create_simple_splash():
    """Crea un splash screen simple sin dependencias de imágenes"""
    # Crear pixmap simple (200x200)
    pixmap = QPixmap(300, 200)
    pixmap.fill(QColor(51, 121, 194))  # Color azul VISO
    
    return QSplashScreen(pixmap)


def show_splash():
    """Muestra el splash screen"""
    try:
        splash = create_simple_splash()
        splash.setWindowFlags(splash.windowFlags() | Qt.FramelessWindowHint)
        splash.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # Mostrar mensaje
        font = QFont("Segoe UI", 10)
        splash.setFont(font)
        splash.showMessage("Inicializando VISO...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        
        # Procesar eventos para que aparezca
        app = QApplication.instance()
        if app:
            app.processEvents()
        
        return splash
    except Exception as e:
        print(f"[WARNING] No se pudo crear splash screen: {e}")
        return None
