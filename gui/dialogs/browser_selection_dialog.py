"""
Diálogo para seleccionar navegador y abrir archivos en él.
"""

import os
import sys
import subprocess
from pathlib import Path
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QRadioButton, QButtonGroup
from PyQt5.QtCore import Qt


class BrowserSelectionDialog(QDialog):
    """Diálogo para seleccionar navegador disponible."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Navegador")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.selected_browser = None
        
        # Detectar navegadores disponibles
        self.browsers = self._detect_browsers()
        
        self.setup_ui()
    
    def _detect_browsers(self):
        """Detecta los navegadores instalados en el sistema."""
        browsers = {}
        
        # Rutas típicas para cada navegador en Windows
        if sys.platform == "win32":
            browser_paths = {
                'Chrome': [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                ],
                'Opera': [
                    r"C:\Program Files\Opera\opera.exe",
                    r"C:\Program Files (x86)\Opera\opera.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\opera.exe"),
                ],
                'Edge': [
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
                ]
            }
        else:  # macOS, Linux
            browser_paths = {
                'Chrome': ['/usr/bin/google-chrome', '/usr/bin/chromium', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'],
                'Opera': ['/usr/bin/opera', '/Applications/Opera.app/Contents/MacOS/Opera'],
                'Firefox': ['/usr/bin/firefox', '/Applications/Firefox.app/Contents/MacOS/firefox'],
            }
        
        # Verificar qué navegadores están instalados
        for browser_name, paths in browser_paths.items():
            for path in paths:
                if os.path.exists(path):
                    browsers[browser_name] = path
                    break
        
        return browsers
    
    def setup_ui(self):
        """Configura la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("Seleccionar Navegador")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2a2a2a;")
        layout.addWidget(title)
        
        # Instrucciones
        instructions = QLabel("Elige un navegador para abrir la boleta:")
        instructions.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(instructions)
        
        # Frame para las opciones
        options_frame = QtWidgets.QFrame()
        options_frame.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        options_layout = QVBoxLayout(options_frame)
        options_layout.setSpacing(10)
        options_layout.setContentsMargins(10, 10, 10, 10)
        
        # Grupo de botones de radio
        self.button_group = QButtonGroup()
        
        if not self.browsers:
            # No se encontraron navegadores
            no_browser_label = QLabel("❌ No se encontraron navegadores instalados")
            no_browser_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            options_layout.addWidget(no_browser_label)
        else:
            # Crear botón radio para cada navegador disponible
            for idx, (browser_name, browser_path) in enumerate(self.browsers.items()):
                radio_button = QRadioButton(f"🌐 {browser_name}")
                radio_button.setStyleSheet("""
                    QRadioButton {
                        color: #2a2a2a;
                        font-size: 12px;
                        padding: 5px;
                    }
                    QRadioButton:hover {
                        background: #e9ecef;
                        border-radius: 4px;
                    }
                """)
                radio_button.setProperty("browser_path", browser_path)
                self.button_group.addButton(radio_button, idx)
                options_layout.addWidget(radio_button)
                
                # Seleccionar el primer navegador por defecto
                if idx == 0:
                    radio_button.setChecked(True)
        
        layout.addWidget(options_frame)
        
        # Separador
        separator = QtWidgets.QFrame()
        separator.setStyleSheet("background: #e9ecef;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Botón Aceptar
        btn_accept = QPushButton("Abrir")
        btn_accept.setCursor(QtCore.Qt.PointingHandCursor)
        btn_accept.setMinimumHeight(36)
        btn_accept.setStyleSheet("""
            QPushButton {
                background: #0d6efd;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0b5ed7;
            }
            QPushButton:pressed {
                background: #0a58ca;
            }
        """)
        btn_accept.clicked.connect(self.accept_selection)
        button_layout.addWidget(btn_accept)
        
        # Botón Cancelar
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        btn_cancel.setMinimumHeight(36)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #dee2e6;
            }
            QPushButton:pressed {
                background: #ced4da;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
    
    def accept_selection(self):
        """Valida la selección y acepta el diálogo."""
        if not self.browsers:
            QMessageBox.warning(
                self,
                "Sin Navegadores",
                "No se encontraron navegadores instalados.\n\n"
                "Por favor instala Chrome, Opera o Edge y vuelve a intentar."
            )
            return
        
        checked_button = self.button_group.checkedButton()
        if checked_button:
            self.selected_browser = checked_button.property("browser_path")
            self.accept()
        else:
            QMessageBox.warning(self, "Advertencia", "Por favor selecciona un navegador.")
    
    def get_selected_browser(self):
        """Retorna la ruta del navegador seleccionado."""
        return self.selected_browser
    
    @staticmethod
    def open_file_in_browser(file_path, parent=None):
        """
        Abre un archivo en el navegador seleccionado por el usuario.
        Retorna True si fue exitoso, False si falló o el usuario canceló.
        """
        dialog = BrowserSelectionDialog(parent)
        
        if dialog.exec_() != QDialog.Accepted:
            return False  # Usuario canceló
        
        browser_path = dialog.get_selected_browser()
        
        if not browser_path:
            QMessageBox.warning(
                parent,
                "Error",
                "No se pudo obtener la ruta del navegador seleccionado."
            )
            return False
        
        try:
            # Convertir a URL si es un archivo local
            if os.path.isfile(file_path):
                file_url = f"file:///{Path(file_path).as_posix()}"
            else:
                file_url = file_path
            
            # Abrir el archivo en el navegador seleccionado
            subprocess.Popen([browser_path, file_url])
            return True
        except Exception as e:
            QMessageBox.critical(
                parent,
                "Error",
                f"No se pudo abrir el navegador:\n{str(e)}"
            )
            return False
