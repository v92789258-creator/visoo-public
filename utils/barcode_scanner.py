"""
Módulo para captura de códigos de barras desde lectora de código de barras.
Soporta múltiples tipos de lectoras (USB HID).
"""

import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut


class BarcodeLineEdit(QLineEdit):
    """
    QLineEdit personalizado que captura códigos de barras sin interferencias.
    Bloquea los atajos de teclado normales durante el escaneo.
    """
    
    barcode_captured = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_scanning = False
        self.scanning_buffer = ""
        self.last_input_time = 0
        
    def start_scanning(self):
        """Inicia el modo de escaneo de código de barras."""
        self.is_scanning = True
        self.scanning_buffer = ""
        self.clear()
        self.setPlaceholderText("Escaneando... (escanea el código)")
        self.setFocus()
        
    def stop_scanning(self):
        """Detiene el modo de escaneo."""
        self.is_scanning = False
        self.scanning_buffer = ""
        self.setPlaceholderText("Escanea el código de barras")
        
    def keyPressEvent(self, event):
        """
        Captura eventos de teclado durante el escaneo.
        Bloquea atajos de teclado para evitar interferencias.
        """
        if not self.is_scanning:
            super().keyPressEvent(event)
            return
            
        # Bloquear TODOS los atajos de teclado con modificadores (Ctrl, Alt, Shift+Ctrl, etc.)
        modifiers = event.modifiers()
        if modifiers & (0x04000000 | 0x08000000 | 0x02000000):  # Ctrl | Alt | Shift (con Ctrl)
            # Ignorar completamente los eventos con modificadores
            return
            
        # Si es Enter/Return, finalizar el escaneo
        if event.key() in (16777220, 16777221):  # Qt.Key_Return, Qt.Key_Enter
            barcode = self.text().strip()
            if barcode:
                self.barcode_captured.emit(barcode)
            return
        
        # Si es Escape, cancelar el escaneo
        if event.key() == 16777216:  # Qt.Key_Escape
            self.stop_scanning()
            self.clear()
            return
        
        # Si es Tab, no hacer nada (evitar cambiar de campo)
        if event.key() == 16777217:  # Qt.Key_Tab
            return
        
        # Permitir Backspace y Delete para edición manual
        if event.key() in (16777219, 16777223):  # Qt.Key_Backspace, Qt.Key_Delete
            super().keyPressEvent(event)
            return
        
        # Permitir solo caracteres imprimibles normales (sin modificadores)
        if event.text() and event.text().isprintable():
            super().keyPressEvent(event)
        # Ignorar todo lo demás


class BarcodeScanner(QObject):
    """
    Captura códigos de barras desde una lectora conectada por USB.
    La lectora debe estar configurada en modo HID (Human Interface Device).
    """
    
    # Señal que emite cuando se lee un código
    barcode_read = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.buffer = ""
        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_timeout)
        self.timeout_delay = 100  # milisegundos
        self.is_scanning = False
        
    def start_scanning_mode(self, line_edit: QLineEdit):
        """
        Inicia el modo de escaneo. El código se capturará directamente en el QLineEdit.
        Este método configura el QLineEdit para recibir caracteres de la lectora.
        """
        self.is_scanning = True
        self.buffer = ""
        line_edit.clear()
        line_edit.setFocus()
        line_edit.setPlaceholderText("Escaneando... (escanea el código)")
        
    def stop_scanning_mode(self, line_edit: QLineEdit):
        """Detiene el modo de escaneo."""
        self.is_scanning = False
        line_edit.setPlaceholderText("Escanea el código de barras")
        self.timeout_timer.stop()
        
    def _on_timeout(self):
        """Se ejecuta cuando expira el timeout de lectura."""
        if self.buffer.strip():
            # El código de barras está completo
            barcode = self.buffer.strip()
            self.buffer = ""
            self.barcode_read.emit(barcode)
            
    def process_barcode_input(self, text: str) -> bool:
        """
        Procesa la entrada de la lectora de código de barras.
        Retorna True si el código está completo (usuario presionó Enter).
        
        Args:
            text: El texto ingresado en el QLineEdit
            
        Returns:
            bool: True si el código está completo, False si sigue leyendo
        """
        if not self.is_scanning:
            return False
            
        # Reiniciar el timer
        self.timeout_timer.stop()
        self.timeout_timer.start(self.timeout_delay)
        
        return False
        
    def finalize_barcode(self, line_edit: QLineEdit):
        """
        Finaliza la lectura del código de barras cuando el usuario presiona Enter.
        """
        if self.is_scanning:
            barcode = line_edit.text().strip()
            if barcode:
                self.barcode_read.emit(barcode)
                return barcode
        return None


class BarcodeScannedLineEdit(QLineEdit):
    """
    QLineEdit personalizado que captura automáticamente códigos de barras
    de una lectora USB HID.
    """
    
    barcode_scanned = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner = BarcodeScanner()
        self.scanner.barcode_read.connect(self._on_barcode_read)
        self.is_scanning = False
        self.start_scanning()
        
    def start_scanning(self):
        """Inicia el modo de escaneo."""
        self.is_scanning = True
        self.scanner.start_scanning_mode(self)
        
    def stop_scanning(self):
        """Detiene el modo de escaneo."""
        self.is_scanning = False
        self.scanner.stop_scanning_mode(self)
        
    def _on_barcode_read(self, barcode: str):
        """Se ejecuta cuando se lee un código."""
        self.setText(barcode)
        self.barcode_scanned.emit(barcode)
        
    def keyPressEvent(self, event):
        """
        Intercepta la tecla Enter para capturar el código de barras.
        Bloquea atajos de teclado durante escaneo.
        """
        # Bloquear atajos de teclado comunes durante escaneo
        if self.is_scanning and event.modifiers() & (0x02000000 | 0x04000000):  # Ctrl or Cmd
            return
            
        super().keyPressEvent(event)


def create_barcode_scanner_button():
    """
    Crea un botón para escanear códigos de barras.
    Retorna un diccionario con la configuración del botón.
    """
    return {
        'text': '📱 Escanear',
        'tooltip': 'Escanea el código de barras con la lectora USB',
        'icon': None
    }
