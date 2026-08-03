"""
Generador de Códigos de Barras - VISO v4.2.2
Dialogo completo con personalización de tamaños, generador aleatorio, etc.
"""
import os
import sys
import tempfile
import random
import string
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QSpinBox, QPushButton, QMessageBox, QComboBox, QScrollArea,
    QFrame, QDoubleSpinBox, QCheckBox, QWidget, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont

import barcode
from barcode.writer import ImageWriter
from PIL import Image


class BarcodeGeneratorDialog(QDialog):
    """Generador de códigos de barras con personalización completa"""
    
    barcode_generated = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.barcode_format = 'code128'
        self.last_generated_path = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setGeometry(100, 100, 900, 750)
        self.setWindowIcon(self.get_icon())
        self.init_ui()
        self.setWindowTitle("🏷️ Generador de Códigos de Barras")
    
    def get_icon(self):
        """Obtiene el icono"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'icons', 'icon.ico')
            if os.path.exists(icon_path):
                return QtGui.QIcon(icon_path)
        except:
            pass
        return QtGui.QIcon()
    
    def init_ui(self):
        """Crea la interfaz completa con diseño nativo"""
        # Layout principal
        main = QVBoxLayout(self)
        main.setSpacing(0)
        main.setContentsMargins(0, 0, 0, 0)
        
        # --- BARRA DE TÍTULO PERSONALIZADA ---
        from gui.draggable_title_bar import DraggableTitleBar
        title_bar = DraggableTitleBar("🏷️  Generador de Códigos de Barras", self)
        main.addWidget(title_bar)
        
        # Contenido principal
        content = QWidget()
        content.setStyleSheet("background: #f0f0f0;")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(12, 12, 12, 12)
        
        # Scroll para contenido
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: #f0f0f0;
                border: none;
            }
            QScrollBar:vertical {
                width: 12px;
                background: #f0f0f0;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- 1. SECCIÓN: CÓDIGO Y FORMATO ---
        code_format_layout = QHBoxLayout()
        code_format_layout.setSpacing(12)
        
        # Panel código
        lbl_code = QLabel("Código:")
        lbl_code.setFixedWidth(60)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Ej: ABC123456")
        self.code_input.setMinimumHeight(24)
        self.code_input.textChanged.connect(lambda: self.generate_barcode() if self.code_input.text() else None)
        
        btn_random = QPushButton("Aleatorio")
        btn_random.setMaximumWidth(100)
        btn_random.setMinimumHeight(24)
        btn_random.clicked.connect(self.generate_random_code)
        
        code_format_layout.addWidget(lbl_code)
        code_format_layout.addWidget(self.code_input, 2)
        code_format_layout.addWidget(btn_random)
        
        layout.addLayout(code_format_layout)
        
        # --- 2. SECCIÓN: FORMATO ---
        fmt_layout = QHBoxLayout()
        fmt_layout.setSpacing(12)
        
        lbl_format = QLabel("Formato:")
        lbl_format.setFixedWidth(60)
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(['code128', 'code39', 'ean13', 'ean8', 'upca', 'upce', 'itf', 'gs1'])
        self.fmt_combo.currentTextChanged.connect(lambda: self.generate_barcode() if self.code_input.text() else None)
        
        fmt_layout.addWidget(lbl_format)
        fmt_layout.addWidget(self.fmt_combo)
        fmt_layout.addStretch()
        
        layout.addLayout(fmt_layout)
        
        # --- 3. SECCIÓN: RANGO ---
        range_layout = QHBoxLayout()
        range_layout.setSpacing(12)
        
        lbl_range = QLabel("Rango:")
        lbl_range.setFixedWidth(60)
        range_layout.addWidget(lbl_range)
        
        range_layout.addWidget(QLabel("Desde:"))
        self.from_spin = QSpinBox()
        self.from_spin.setValue(1)
        self.from_spin.setMaximum(99999)
        range_layout.addWidget(self.from_spin)
        
        range_layout.addWidget(QLabel("Hasta:"))
        self.to_spin = QSpinBox()
        self.to_spin.setValue(1)
        self.to_spin.setMaximum(99999)
        range_layout.addWidget(self.to_spin)
        range_layout.addStretch()
        
        layout.addLayout(range_layout)
        
        # Separador
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("background: #d0d0d0;")
        layout.addWidget(sep1)
        
        # --- 4. SECCIÓN: TAMAÑO ---
        size_layout = QHBoxLayout()
        size_layout.setSpacing(12)
        
        lbl_size = QLabel("Tamaño:")
        lbl_size.setFixedWidth(60)
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            '4x6 pulgadas (estándar)',
            '3x5 pulgadas',
            '2x4 pulgadas',
            'Personalizado'
        ])
        self.size_combo.currentTextChanged.connect(self.on_size_changed)
        
        size_layout.addWidget(lbl_size)
        size_layout.addWidget(self.size_combo)
        size_layout.addStretch()
        
        layout.addLayout(size_layout)
        
        # --- 5. SECCIÓN: DIMENSIONES ---
        dims_layout = QHBoxLayout()
        dims_layout.setSpacing(12)
        
        lbl_width = QLabel("Ancho:")
        lbl_width.setFixedWidth(60)
        self.width = QDoubleSpinBox()
        self.width.setRange(20, 200)
        self.width.setValue(60)
        self.width.setSuffix(" mm")
        
        dims_layout.addWidget(lbl_width)
        dims_layout.addWidget(self.width)
        
        dims_layout.addWidget(QLabel("Alto:"))
        self.height = QDoubleSpinBox()
        self.height.setRange(10, 100)
        self.height.setValue(30)
        self.height.setSuffix(" mm")
        dims_layout.addWidget(self.height)
        dims_layout.addStretch()
        
        layout.addLayout(dims_layout)
        
        # --- 6. SECCIÓN: OPCIONES ---
        opts_layout = QHBoxLayout()
        opts_layout.setSpacing(12)
        
        opts_layout.addWidget(QLabel("Mostrar número:"))
        self.show_text = QComboBox()
        self.show_text.addItems(['Sí', 'No'])
        opts_layout.addWidget(self.show_text)
        
        opts_layout.addWidget(QLabel("Centrar:"))
        self.center_cb = QCheckBox()
        self.center_cb.setChecked(True)
        opts_layout.addWidget(self.center_cb)
        opts_layout.addStretch()
        
        layout.addLayout(opts_layout)
        
        # --- 7. SECCIÓN: MÁRGENES ---
        margins_layout = QHBoxLayout()
        margins_layout.setSpacing(12)
        
        lbl_margin_top = QLabel("Margen superior:")
        lbl_margin_top.setFixedWidth(100)
        self.margin_top = QDoubleSpinBox()
        self.margin_top.setRange(0, 50)
        self.margin_top.setValue(0)
        self.margin_top.setSuffix(" mm")
        
        margins_layout.addWidget(lbl_margin_top)
        margins_layout.addWidget(self.margin_top)
        
        margins_layout.addWidget(QLabel("Izquierdo:"))
        self.margin_left = QDoubleSpinBox()
        self.margin_left.setRange(0, 50)
        self.margin_left.setValue(0)
        self.margin_left.setSuffix(" mm")
        margins_layout.addWidget(self.margin_left)
        margins_layout.addStretch()
        
        layout.addLayout(margins_layout)
        
        # --- 8. SECCIÓN: CALIDAD ---
        quality_layout = QHBoxLayout()
        quality_layout.setSpacing(12)
        
        lbl_quality = QLabel("Calidad:")
        lbl_quality.setFixedWidth(60)
        self.quality = QComboBox()
        self.quality.addItems(['Baja (rápida)', 'Media', 'Alta (lenta)'])
        self.quality.setCurrentText('Alta (lenta)')
        
        quality_layout.addWidget(lbl_quality)
        quality_layout.addWidget(self.quality)
        quality_layout.addStretch()
        
        layout.addLayout(quality_layout)
        
        # Separador
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background: #d0d0d0;")
        layout.addWidget(sep2)
        
        # --- 9. SECCIÓN: VISTA PREVIA ---
        layout.addWidget(QLabel("Vista Previa:"))
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(150)
        self.preview.setStyleSheet("border: 1px solid #c0c0c0; padding: 8px; background: white;")
        layout.addWidget(self.preview)
        
        layout.addStretch()
        scroll.setWidget(widget)
        content_layout.addWidget(scroll)
        
        # --- BOTONES DE ACCIÓN ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_layout.addStretch()
        
        self.gen_btn = QPushButton("Generar")
        self.gen_btn.setMinimumHeight(28)
        self.gen_btn.setMinimumWidth(100)
        self.gen_btn.clicked.connect(self.generate_barcode)
        btn_layout.addWidget(self.gen_btn)
        
        self.print_btn = QPushButton("Imprimir")
        self.print_btn.setMinimumHeight(28)
        self.print_btn.setMinimumWidth(100)
        self.print_btn.setEnabled(False)
        self.print_btn.clicked.connect(self.print_barcode)
        btn_layout.addWidget(self.print_btn)
        
        self.save_btn = QPushButton("Guardar PNG")
        self.save_btn.setMinimumHeight(28)
        self.save_btn.setMinimumWidth(100)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_barcode)
        btn_layout.addWidget(self.save_btn)
        
        btn_close = QPushButton("Cerrar")
        btn_close.setMinimumHeight(28)
        btn_close.setMinimumWidth(80)
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        content_layout.addLayout(btn_layout)
        
        main.addWidget(content)
        self.setLayout(main)
    
    def generate_random_code(self):
        """Genera código aleatorio"""
        code = ''.join(random.choices(string.digits, k=random.randint(8, 12)))
        self.code_input.setText(code)
    
    def on_size_changed(self):
        """Actualiza tamaños según etiqueta"""
        text = self.size_combo.currentText()
        if '4x6' in text:
            self.width.setValue(100)
            self.height.setValue(50)
        elif '3x5' in text:
            self.width.setValue(75)
            self.height.setValue(40)
        elif '2x4' in text:
            self.width.setValue(50)
            self.height.setValue(25)
    
    def generate_barcode(self):
        """Genera el código de barras"""
        code = self.code_input.text().strip()
        if not code:
            self.preview.setText("")
            self.print_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            return
        
        try:
            # Generar código base
            temp_dir = tempfile.gettempdir()
            path = os.path.join(temp_dir, f"barcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            barcode_obj = barcode.get(self.fmt_combo.currentText(), code, writer=ImageWriter())
            barcode_obj.save(path)
            
            base_barcode_path = f"{path}.png"
            
            # Si está activado centrar, crear imagen centrada
            if self.center_cb.isChecked():
                from PIL import Image as PILImage
                
                # Cargar código base
                base_img = PILImage.open(base_barcode_path)
                
                # Convertir a valores en píxeles (300 DPI por defecto)
                dpi = 300 if 'Alta' in self.quality.currentText() else (203 if 'Media' in self.quality.currentText() else 100)
                
                # Calcular dimensiones de la hoja en píxeles
                width_px = int((self.width.value() / 25.4) * dpi)
                height_px = int((self.height.value() / 25.4) * dpi)
                
                # Calcular márgenes en píxeles
                margin_top_px = int((self.margin_top.value() / 25.4) * dpi)
                margin_left_px = int((self.margin_left.value() / 25.4) * dpi)
                
                # Redimensionar código de barras
                barcode_width_px = int((self.width.value() / 25.4) * dpi)
                barcode_height_px = int((self.height.value() / 25.4) * dpi)
                
                # Redimensionar proporcionalmente
                base_img.thumbnail((barcode_width_px, barcode_height_px), PILImage.Resampling.LANCZOS)
                
                # Crear imagen blanca con el tamaño total
                final_img = PILImage.new('RGB', (width_px, height_px), 'white')
                
                # Calcular posición para centrar
                x_pos = margin_left_px + (barcode_width_px - base_img.width) // 2
                y_pos = margin_top_px + (barcode_height_px - base_img.height) // 2
                
                # Pegar código centrado
                if base_img.mode == 'RGBA':
                    final_img.paste(base_img, (x_pos, y_pos), base_img)
                else:
                    final_img.paste(base_img, (x_pos, y_pos))
                
                # Guardar imagen final
                self.last_generated_path = f"{path}_centered.png"
                final_img.save(self.last_generated_path)
            else:
                self.last_generated_path = base_barcode_path
            
            # Mostrar preview
            pixmap = QPixmap(self.last_generated_path)
            scaled = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
            self.preview.setPixmap(scaled)
            
            self.print_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.barcode_generated.emit(code)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
            self.preview.setText("")
            self.print_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
    
    def print_barcode(self):
        """Imprime el código"""
        if not self.last_generated_path or not os.path.exists(self.last_generated_path):
            QMessageBox.warning(self, "Error", "Primero genera un código")
            return
        
        try:
            from gui.dialogs.printer_selection_dialog import PrinterSelectionDialog
            from utils.printer_handler import print_image
            
            dialog = PrinterSelectionDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                return
            
            printer = dialog.get_selected_printer()
            if not printer:
                QMessageBox.warning(self, "Error", "Selecciona impresora")
                return
            
            # Detectar si es térmica
            if any(x in printer.lower() for x in ['bt-', 'thermal', 'hoco', 'bluetooth']):
                from utils.escpos_thermal_printer import ThermalBluetoothPrinter
                from PIL import Image as PILImage
                
                img = PILImage.open(self.last_generated_path)
                
                # Redimensionar
                dpi = 300 if 'Alta' in self.quality.currentText() else (203 if 'Media' in self.quality.currentText() else 100)
                w_px = int((self.width.value() / 25.4) * dpi)
                h_px = int((self.height.value() / 25.4) * dpi)
                
                img.thumbnail((w_px, h_px), PILImage.Resampling.LANCZOS)
                
                success, msg = ThermalBluetoothPrinter.print_image_thermal(img)
            else:
                success, msg = print_image(self.last_generated_path, printer)
            
            if success:
                QMessageBox.information(self, "✓ Éxito", "Código enviado a imprimir")
            else:
                QMessageBox.critical(self, "✗ Error", f"No se pudo imprimir:\n{msg}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
    
    def save_barcode(self):
        """Guarda como PNG"""
        if not self.last_generated_path or not os.path.exists(self.last_generated_path):
            QMessageBox.warning(self, "Error", "Primero genera un código")
            return
        
        try:
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Guardar código de barras",
                f"codigo_{self.code_input.text()}.png",
                "PNG (*.png);;All (*)"
            )
            
            if file_path:
                img = Image.open(self.last_generated_path)
                img.save(file_path)
                QMessageBox.information(self, "✓ Guardado", f"Código guardado:\n{file_path}")
                self.barcode_generated.emit(self.code_input.text())
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
