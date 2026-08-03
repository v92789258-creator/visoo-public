"""
Diálogo para seleccionar impresora.
Permite al usuario elegir una impresora disponible en el sistema.
"""

import os
import json
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt
from utils.printer_handler import find_available_printers, get_printer_handler


class PrinterSelectionDialog(QDialog):
    """Diálogo para seleccionar una impresora disponible."""
    
    CONFIG_DIR = "viso"
    CONFIG_FILE = "printer_config.json"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Impresora")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.selected_printer = None
        self.ensure_config_dir()
        self.setup_ui()
        self.load_printers()
        self.load_last_printer()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Título
        title = QLabel("Selecciona una Impresora")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2a2a2a;")
        layout.addWidget(title)
        
        # Descripción
        description = QLabel(
            "Selecciona la impresora en la que deseas imprimir la boleta."
        )
        description.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(description)
        
        layout.addSpacing(10)
        
        # ComboBox para seleccionar impresora
        self.printer_combo = QComboBox()
        self.printer_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background: white;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        layout.addWidget(self.printer_combo)
        
        # Botón para refrescar lista de impresoras
        btn_refresh = QPushButton("🔄 Refrescar Lista")
        btn_refresh.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5c636a;
            }
            QPushButton:pressed {
                background: #4c545d;
            }
        """)
        btn_refresh.clicked.connect(self.load_printers)
        layout.addWidget(btn_refresh)
        
        layout.addSpacing(10)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        btn_ok = QPushButton("Seleccionar")
        btn_ok.setStyleSheet("""
            QPushButton {
                background: #198754;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #157347;
            }
            QPushButton:pressed {
                background: #12533a;
            }
        """)
        btn_ok.clicked.connect(self.accept_selection)
        buttons_layout.addWidget(btn_ok)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #dee2e6;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        
        layout.addLayout(buttons_layout)
    
    def ensure_config_dir(self):
        """Asegura que la carpeta de configuración exista."""
        if not os.path.exists(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
    
    def get_config_path(self):
        """Devuelve la ruta del archivo de configuración."""
        return os.path.join(self.CONFIG_DIR, self.CONFIG_FILE)
    
    def save_last_printer(self, printer_name):
        """Guarda el nombre de la última impresora usada."""
        try:
            config_path = self.get_config_path()
            config = {"last_printer": printer_name}
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error guardando configuración de impresora: {e}")
    
    def load_last_printer(self):
        """Carga la última impresora usada y la selecciona."""
        try:
            config_path = self.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    last_printer = config.get("last_printer")
                    if last_printer:
                        # Buscar y seleccionar la última impresora usada
                        for i in range(self.printer_combo.count()):
                            if self.printer_combo.itemData(i) == last_printer:
                                self.printer_combo.setCurrentIndex(i)
                                return
        except Exception as e:
            print(f"Error cargando configuración de impresora: {e}")
    
    def load_printers(self):
        """Carga la lista de impresoras disponibles (Bluetooth + Cableadas)."""
        try:
            self.printer_combo.clear()
            self.printer_combo.addItem("🔍 Buscando impresoras...")
            
            # Obtener TODAS las impresoras disponibles
            printers = find_available_printers()
            
            # Limpiar y agregar nuevas impresoras con indicadores
            self.printer_combo.clear()
            
            if printers:
                # Agregar impresoras con etiquetas indicando tipo
                for printer in printers:
                    # Detectar tipo de impresora
                    if any(x in printer.upper() for x in ['BT-', 'BLUETOOTH', 'HOCO', 'THERMAL']):
                        display_name = f"📱 [BLUETOOTH] {printer}"
                    else:
                        display_name = f"🖨️ [CABLEADA] {printer}"
                    
                    self.printer_combo.addItem(display_name, printer)  # Guardar nombre real en userData
                self.printer_combo.setCurrentIndex(0)
            else:
                self.printer_combo.addItem("❌ No hay impresoras disponibles")
        
        except Exception as e:
            self.printer_combo.clear()
            self.printer_combo.addItem("Error cargando impresoras")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al cargar impresoras:\n{e}"
            )
    
    def get_all_system_printers(self):
        """Obtiene todas las impresoras del sistema."""
        try:
            if self._is_windows():
                return self._get_windows_printers()
            elif self._is_linux():
                return self._get_linux_printers()
            elif self._is_macos():
                return self._get_macos_printers()
        except Exception:
            pass
        return []
    
    def _is_windows(self):
        """Verifica si el sistema es Windows."""
        import platform
        return platform.system() == "Windows"
    
    def _is_linux(self):
        """Verifica si el sistema es Linux."""
        import platform
        return platform.system() == "Linux"
    
    def _is_macos(self):
        """Verifica si el sistema es macOS."""
        import platform
        return platform.system() == "Darwin"
    
    def _get_windows_printers(self):
        """Obtiene impresoras en Windows."""
        try:
            import win32print
            printers = []
            for printer_name in win32print.EnumPrinters():
                printers.append(printer_name)
            return printers
        except Exception:
            return []
    
    def _get_linux_printers(self):
        """Obtiene impresoras en Linux."""
        try:
            import subprocess
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            printers = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) > 1:
                        printer_name = parts[1].rstrip(':')
                        printers.append(printer_name)
            return printers
        except Exception:
            return []
    
    def _get_macos_printers(self):
        """Obtiene impresoras en macOS."""
        try:
            import subprocess
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            printers = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) > 1:
                        printer_name = parts[1].rstrip(':')
                        printers.append(printer_name)
            return printers
        except Exception:
            return []
    
    def accept_selection(self):
        """Acepta la selección de impresora."""
        selected_display = self.printer_combo.currentText()
        
        if selected_display == "❌ No hay impresoras disponibles":
            QMessageBox.warning(
                self,
                "Sin Impresoras",
                "No hay impresoras disponibles en el sistema."
            )
            return
        
        # Obtener el nombre real de la impresora (guardado en userData)
        selected_printer = self.printer_combo.currentData()
        if not selected_printer:
            # Si no hay userData, usar el texto mostrado limpio
            selected_printer = selected_display.replace("📱 [BLUETOOTH] ", "").replace("🖨️ [CABLEADA] ", "")
        
        self.selected_printer = selected_printer
        # Guardar la impresora seleccionada en la configuración
        self.save_last_printer(selected_printer)
        handler = get_printer_handler()
        handler.set_printer(selected_printer)
        
        self.accept()
    
    def get_selected_printer(self):
        """Devuelve la impresora seleccionada."""
        return self.selected_printer
