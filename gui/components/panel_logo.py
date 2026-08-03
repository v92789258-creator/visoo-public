"""
Módulo para la gestión del logo de empresa.
Interfaz para subir, mostrar y eliminar el logo.
"""

import os
import shutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt


class PanelLogo(QWidget):
    """Panel para gestionar el logo de la empresa."""
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.ruta_logos = self._obtener_ruta_logos()
        
        self.init_ui()
        self.actualizar_estado_logo()
    
    def _obtener_ruta_logos(self):
        """Obtiene la ruta del directorio de logos."""
        ruta = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'logos'
        )
        os.makedirs(ruta, exist_ok=True)
        return ruta
    
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Descripción
        desc = QLabel(
            "Sube el logo de tu empresa para que se muestre en las boletas grandes "
            "(Largo y Extra Largo)."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)
        
        # Botón subir
        self.btn_upload = QPushButton("📁 Seleccionar Logo")
        self.btn_upload.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #45a049;
            }
        """)
        self.btn_upload.setCursor(Qt.PointingHandCursor)
        self.btn_upload.clicked.connect(self.cargar_logo)
        buttons_layout.addWidget(self.btn_upload)
        
        # Etiqueta de estado
        self.lbl_estado = QLabel("Sin logo cargado")
        self.lbl_estado.setStyleSheet("color: #666666; font-size: 12px;")
        buttons_layout.addWidget(self.lbl_estado)
        
        # Botón eliminar
        self.btn_delete = QPushButton("  Eliminar Logo")
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #da190b;
            }
        """)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self.eliminar_logo)
        buttons_layout.addWidget(self.btn_delete)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
    
    def actualizar_estado_logo(self):
        """Actualiza el estado de los botones según si hay logo."""
        ruta_logo = os.path.join(self.ruta_logos, 'logo_empresa.png')
        
        if os.path.exists(ruta_logo):
            self.lbl_estado.setText("✓ Logo cargado (20.0 KB)")
            self.btn_delete.setEnabled(True)
        else:
            self.lbl_estado.setText("Sin logo cargado")
            self.btn_delete.setEnabled(False)
    
    def cargar_logo(self):
        """Abre un diálogo para seleccionar el logo."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Logo de Empresa",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos los archivos (*.*)",
            options=options
        )
        
        if file_path:
            try:
                ruta_destino = os.path.join(self.ruta_logos, 'logo_empresa.png')
                shutil.copy2(file_path, ruta_destino)
                
                # Obtener tamaño
                tamaño_kb = os.path.getsize(ruta_destino) / 1024
                
                self.lbl_estado.setText(f"✓ Logo cargado ({tamaño_kb:.1f} KB)")
                self.btn_delete.setEnabled(True)
                
                QMessageBox.information(
                    self,
                    "Logo Cargado",
                    f"✓ Logo guardado correctamente\n\n"
                    f"Tamaño: {tamaño_kb:.1f} KB\n\n"
                    f"El logo aparecerá en las boletas grande, larga y extra larga."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo cargar el logo:\n{str(e)}")
    
    def eliminar_logo(self):
        """Elimina el logo actual."""
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Estás seguro de que deseas eliminar el logo?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                ruta_logo = os.path.join(self.ruta_logos, 'logo_empresa.png')
                if os.path.exists(ruta_logo):
                    os.remove(ruta_logo)
                
                self.lbl_estado.setText("Sin logo cargado")
                self.btn_delete.setEnabled(False)
                
                QMessageBox.information(
                    self,
                    "Logo Eliminado",
                    "✓ El logo ha sido eliminado correctamente."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el logo:\n{str(e)}")
