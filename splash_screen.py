"""Splash Screen simple para VISO - Solo muestra la imagen"""

import os
import sys
import time
from PyQt5 import QtWidgets, QtCore, QtGui


def get_splash_path():
    """Obtiene el path correcto de splash.png dependiendo del entorno"""
    # En ejecutable empaquetado con PyInstaller
    if getattr(sys, 'frozen', False):
        # PyInstaller extrae en _MEIPASS
        base_dir = sys._MEIPASS
    else:
        # En desarrollo
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        os.path.join(base_dir, "splash.png"),
        os.path.join(base_dir, "_internal", "splash.png"),
        os.path.join(os.path.dirname(sys.executable), "splash.png"),
        "splash.png",
        os.path.abspath("splash.png"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"[SPLASH] Encontrado en: {path}")
            return path
    
    print(f"[SPLASH] splash.png NO encontrado. Buscadas:")
    for path in possible_paths:
        print(f"  - {path}")
    return None


class SplashScreen(QtWidgets.QSplashScreen):
    """Pantalla de carga simple - Solo muestra la imagen"""
    
    def __init__(self):
        # Buscar splash.png
        splash_path = get_splash_path()
        
        if splash_path:
            pixmap = QtGui.QPixmap(splash_path)
            if pixmap.isNull():
                print(f"[SPLASH] ERROR: No se pudo cargar la imagen desde {splash_path}")
                pixmap = self._create_fallback()
            else:
                print(f"[SPLASH] Imagen cargada: {pixmap.width()}x{pixmap.height()}")
                # Redimensionar si es muy grande
                if pixmap.width() > 800 or pixmap.height() > 600:
                    pixmap = pixmap.scaledToWidth(800, QtCore.Qt.SmoothTransformation)
        else:
            # Si no existe, crear un pixmap simple
            print(f"[SPLASH] Usando fallback")
            pixmap = self._create_fallback()
        
        super().__init__(pixmap)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        # Centrar en pantalla
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _create_fallback(self):
        """Crea una imagen fallback si no encuentra splash.png"""
        pixmap = QtGui.QPixmap(600, 300)
        pixmap.fill(QtGui.QColor(0, 0, 0))
        
        painter = QtGui.QPainter(pixmap)
        
        # Gradiente
        gradient = QtGui.QLinearGradient(0, 0, 0, 300)
        gradient.setColorAt(0, QtGui.QColor(10, 10, 10))
        gradient.setColorAt(1, QtGui.QColor(30, 30, 30))
        painter.fillRect(pixmap.rect(), gradient)
        
        # Texto
        font = QtGui.QFont("Arial", 28, QtGui.QFont.Bold)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, "VISO")
        
        painter.end()
        return pixmap
    
    def show_message(self, message):
        """Muestra un mensaje (compatible con la interfaz original)"""
        pass


def show_splash(app):
    """Muestra la pantalla de carga simple"""
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    time.sleep(2)  # Mostrar por 2 segundos
    return splash
