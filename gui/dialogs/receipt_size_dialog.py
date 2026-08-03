"""
Diálogo para seleccionar el tamaño de boleta (en milímetros).
Permite al usuario elegir entre tamaños estándar o personalizados.
"""

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QRadioButton, QButtonGroup, QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt
import json
import os


class ReceiptSizeDialog(QDialog):
    """Diálogo para configurar el tamaño de la boleta."""
    
    STANDARD_SIZES = {
        "80mm (Estándar)": 80,
    }
    
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.selected_width = 80  # Default
        self.setWindowTitle("Configuración de Tamaño de Boleta")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMinimumHeight(350)
        self.setup_ui()
        self.load_saved_size()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Título
        title = QLabel("Selecciona el Tamaño de Boleta")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2a2a2a;")
        layout.addWidget(title)
        
        # Descripción
        description = QLabel(
            "Elige el ancho de la boleta en milímetros.\n"
            "Esto afectará el tamaño de impresión."
        )
        description.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(description)
        
        layout.addSpacing(10)
        
        # Grupo de botones para tamaños estándar
        self.size_group = QButtonGroup(self)
        
        group_box = QtWidgets.QGroupBox("Tamaños Estándar")
        group_box.setStyleSheet("""
            QGroupBox {
                color: #2a2a2a;
                border: 1px solid #ced4da;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)
        group_layout = QVBoxLayout(group_box)
        group_layout.setSpacing(12)
        
        for idx, (label, width) in enumerate(self.STANDARD_SIZES.items()):
            radio = QRadioButton(label)
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 11px;
                    color: #333;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                }
            """)
            radio.toggled.connect(lambda checked, w=width: self.on_size_selected(checked, w))
            # Evitar disparar señales antes de que exista spinbox_width
            radio.blockSignals(True)
            radio.setChecked(True)  # 80mm siempre marcado
            radio.blockSignals(False)
            self.size_group.addButton(radio, idx)
            group_layout.addWidget(radio)
        
        layout.addWidget(group_box)
        
        # Opción personalizada (oculta)
        layout.addSpacing(5)
        
        custom_group_box = QtWidgets.QGroupBox("Tamaño Personalizado")
        custom_group_box.setVisible(False)  # Ocultar sección personalizada
        custom_group_box.setStyleSheet("""
            QGroupBox {
                color: #2a2a2a;
                border: 1px solid #ced4da;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)
        custom_layout = QHBoxLayout(custom_group_box)
        custom_layout.setSpacing(10)
        
        # Radio para personalizado
        self.radio_custom = QRadioButton("Ancho personalizado (mm):")
        self.radio_custom.setStyleSheet("font-size: 11px;")
        self.radio_custom.toggled.connect(self.on_custom_toggled)
        custom_layout.addWidget(self.radio_custom)
        
        # Spin box para valor personalizado
        self.spinbox_width = QSpinBox()
        self.spinbox_width.setMinimum(30)
        self.spinbox_width.setMaximum(200)
        self.spinbox_width.setValue(80)
        self.spinbox_width.setSuffix(" mm")
        self.spinbox_width.setStyleSheet("""
            QSpinBox {
                padding: 4px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background: white;
                font-size: 11px;
                width: 80px;
            }
        """)
        self.spinbox_width.valueChanged.connect(self.on_custom_value_changed)
        custom_layout.addWidget(self.spinbox_width)
        custom_layout.addStretch()
        
        layout.addWidget(custom_group_box)
        
        layout.addSpacing(10)
        
        # Info del tamaño seleccionado
        self.info_label = QLabel("Tamaño seleccionado: 80 mm")
        self.info_label.setStyleSheet("""
            color: #198754;
            font-size: 11px;
            font-weight: bold;
            padding: 8px;
            background: #e7f3eb;
            border-radius: 4px;
        """)
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        btn_ok = QPushButton("Guardar y Continuar")
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
    
    def load_saved_size(self):
        """Carga el tamaño de boleta guardado del usuario."""
        try:
            config_path = self._get_config_file()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    saved_width = config.get('receipt_width', 80)
                    
                    # Intentar seleccionar un tamaño estándar
                    found_standard = False
                    for idx, width in enumerate(self.STANDARD_SIZES.values()):
                        if width == saved_width:
                            self.size_group.button(idx).setChecked(True)
                            found_standard = True
                            break
                    
                    # Si no es estándar, usar personalizado
                    if not found_standard:
                        self.radio_custom.setChecked(True)
                        self.spinbox_width.setValue(saved_width)
                    
                    self.selected_width = saved_width
        except Exception as e:
            print(f"[WARNING] Error al cargar configuración de tamaño: {e}")
    
    def on_size_selected(self, checked, width):
        """Maneja la selección de un tamaño estándar."""
        if checked:
            self.selected_width = width
            if hasattr(self, 'spinbox_width'):
                self.spinbox_width.setValue(width)
            self.update_info_label()
    
    def on_custom_toggled(self, checked):
        """Maneja el toggle del tamaño personalizado."""
        if hasattr(self, 'spinbox_width'):
            self.spinbox_width.setEnabled(checked)
        if checked:
            if hasattr(self, 'spinbox_width'):
                self.selected_width = self.spinbox_width.value()
            self.update_info_label()
    
    def on_custom_value_changed(self, value):
        """Maneja el cambio del valor personalizado."""
        if self.radio_custom.isChecked():
            self.selected_width = value
            self.update_info_label()
    
    def update_info_label(self):
        """Actualiza el label de información del tamaño seleccionado."""
        self.info_label.setText(f"Tamaño seleccionado: {self.selected_width} mm")
    
    def accept_selection(self):
        """Acepta la selección y guarda la configuración."""
        if self.selected_width < 30 or self.selected_width > 200:
            QMessageBox.warning(
                self,
                "Tamaño Inválido",
                "El tamaño debe estar entre 30 mm y 200 mm."
            )
            return
        
        try:
            self._save_config()
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al Guardar",
                f"No se pudo guardar la configuración:\n{e}"
            )
    
    def _get_config_file(self):
        """Obtiene la ruta del archivo de configuración del usuario."""
        from utils.file_handler import VISO_DIR
        user_dir = VISO_DIR / self.username
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, '.receipt_config.json')
    
    def _save_config(self):
        """Guarda la configuración de tamaño de boleta."""
        config_path = self._get_config_file()
        config = {
            'receipt_width': self.selected_width
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def get_selected_width(self):
        """Devuelve el ancho de boleta seleccionado en milímetros."""
        return self.selected_width
