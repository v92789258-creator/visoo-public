"""
Diálogo para generar códigos de barras para impresoras térmicas
"""
import os
import tempfile
import random
import string
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui, QtPrintSupport
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QSpinBox, QPushButton, QMessageBox, QComboBox, QScrollArea,
    QFrame, QGridLayout, QDoubleSpinBox, QCheckBox, QGroupBox, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
import barcode
from barcode.writer import ImageWriter
from PIL import Image


class BarcodeGeneratorDialog(QDialog):
    """Mini ventana para generar y imprimir códigos de barras"""
    
    barcode_generated = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.barcode_format = 'code128'
        self.last_generated_path = None
        self.last_generated_image = None  # Guardar la imagen PIL
        self.init_ui()
        self.setWindowTitle("Generador de Códigos de Barras")
        self.setGeometry(100, 100, 850, 950)  # Ventana más grande
        self.setWindowIcon(self.get_icon())
    
    def get_icon(self):
        """Obtiene el icono de la aplicación"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'icons', 'icon.ico')
            if os.path.exists(icon_path):
                return QtGui.QIcon(icon_path)
        except:
            pass
        return QtGui.QIcon()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Usar scroll para que quepa todo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        
        # --- SECCIÓN 1: Tipo de código de barras ---
        format_layout = QHBoxLayout()
        format_label = QLabel("Formato:")
        format_label.setMinimumWidth(120)
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            'code128',
            'code39',
            'ean13',
            'ean8',
            'upca',
            'upce',
            'itf',
            'gs1',
        ])
        self.format_combo.setCurrentText('code128')
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        scroll_layout.addLayout(format_layout)
        
        # Línea separadora
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        scroll_layout.addWidget(line1)
        
        # --- SECCIÓN 2: Entrada de datos ---
        input_label = QLabel("Código a generar:")
        input_label.setFont(QFont("Arial", 10, QFont.Bold))
        scroll_layout.addWidget(input_label)
        
        # Layout para el input y botones de generación
        input_buttons_layout = QHBoxLayout()
        
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Ingresa el número/código para el código de barras")
        self.barcode_input.setMinimumHeight(30)
        self.barcode_input.textChanged.connect(self.validate_input)
        input_buttons_layout.addWidget(self.barcode_input)
        
        # Botón para generar aleatorio
        btn_random = QPushButton("🎲 Aleatorio")
        btn_random.setMaximumWidth(120)
        btn_random.setMinimumHeight(30)
        btn_random.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #8B1FA0;
            }
            QPushButton:pressed {
                background-color: #7A1A8E;
            }
        """)
        btn_random.clicked.connect(self.generate_random_code)
        input_buttons_layout.addWidget(btn_random)
        
        scroll_layout.addLayout(input_buttons_layout)
        
        # Rango de códigos
        range_layout = QHBoxLayout()
        range_label = QLabel("¿Rango?")
        range_layout.addWidget(range_label)
        
        range_start_label = QLabel("Desde:")
        self.range_start = QSpinBox()
        self.range_start.setMinimum(1)
        self.range_start.setValue(1)
        self.range_start.setMaximum(99999)
        
        range_end_label = QLabel("Hasta:")
        self.range_end = QSpinBox()
        self.range_end.setMinimum(1)
        self.range_end.setValue(1)
        self.range_end.setMaximum(99999)
        
        range_layout.addWidget(range_start_label)
        range_layout.addWidget(self.range_start)
        range_layout.addWidget(range_end_label)
        range_layout.addWidget(self.range_end)
        range_layout.addStretch()
        scroll_layout.addLayout(range_layout)
        
        # Línea separadora
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        scroll_layout.addWidget(line2)
        
        # --- SECCIÓN 3: Opciones de personalización ---
        options_label = QLabel("⚙️ Personalización:")
        options_label.setFont(QFont("Arial", 10, QFont.Bold))
        scroll_layout.addWidget(options_label)
        
        # Tamaño de etiqueta predefinido
        label_size_layout = QHBoxLayout()
        label_size_layout.addWidget(QLabel("Tamaño de Etiqueta:"))
        self.label_size_combo = QComboBox()
        self.label_size_combo.addItems([
            '4x6 pulgadas (térmica estándar)',
            '3x5 pulgadas',
            '2x4 pulgadas',
            'Personalizado'
        ])
        self.label_size_combo.setCurrentText('4x6 pulgadas (térmica estándar)')
        self.label_size_combo.currentTextChanged.connect(self.on_label_size_changed)
        label_size_layout.addWidget(self.label_size_combo)
        label_size_layout.addStretch()
        scroll_layout.addLayout(label_size_layout)
        
        # Tamaño del código de barras
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Ancho Código (mm):"))
        self.width_spinbox = QDoubleSpinBox()
        self.width_spinbox.setMinimum(20)
        self.width_spinbox.setMaximum(200)
        self.width_spinbox.setValue(60)
        self.width_spinbox.setSuffix(" mm")
        size_layout.addWidget(self.width_spinbox)
        
        size_layout.addWidget(QLabel("Alto Código (mm):"))
        self.height_spinbox = QDoubleSpinBox()
        self.height_spinbox.setMinimum(10)
        self.height_spinbox.setMaximum(100)
        self.height_spinbox.setValue(30)
        self.height_spinbox.setSuffix(" mm")
        size_layout.addWidget(self.height_spinbox)
        size_layout.addStretch()
        scroll_layout.addLayout(size_layout)
        
        # Mostrar código y Centrado
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Mostrar número:"))
        self.show_text_combo = QComboBox()
        self.show_text_combo.addItems(['Sí', 'No'])
        self.show_text_combo.setCurrentText('Sí')
        options_layout.addWidget(self.show_text_combo)
        
        options_layout.addWidget(QLabel("Centrar:"))
        self.center_checkbox = QCheckBox()
        self.center_checkbox.setChecked(True)
        options_layout.addWidget(self.center_checkbox)
        options_layout.addStretch()
        scroll_layout.addLayout(options_layout)
        
        # Márgenes
        margins_layout = QHBoxLayout()
        margins_layout.addWidget(QLabel("Margen Superior (mm):"))
        self.margin_top_spinbox = QDoubleSpinBox()
        self.margin_top_spinbox.setMinimum(0)
        self.margin_top_spinbox.setMaximum(50)
        self.margin_top_spinbox.setValue(0)
        self.margin_top_spinbox.setSuffix(" mm")
        margins_layout.addWidget(self.margin_top_spinbox)
        
        margins_layout.addWidget(QLabel("Margen Izquierdo (mm):"))
        self.margin_left_spinbox = QDoubleSpinBox()
        self.margin_left_spinbox.setMinimum(0)
        self.margin_left_spinbox.setMaximum(50)
        self.margin_left_spinbox.setValue(0)
        self.margin_left_spinbox.setSuffix(" mm")
        margins_layout.addWidget(self.margin_left_spinbox)
        margins_layout.addStretch()
        scroll_layout.addLayout(margins_layout)
        
        # Calidad
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Calidad:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(['Baja (rápida)', 'Media', 'Alta (lenta)'])
        self.quality_combo.setCurrentText('Alta (lenta)')
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        scroll_layout.addLayout(quality_layout)
        
        # Línea separadora
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        scroll_layout.addWidget(line3)
        
        # --- SECCIÓN 4: Vista previa ---
        preview_label = QLabel("Vista previa:")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        scroll_layout.addWidget(preview_label)
        
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setMinimumHeight(180)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; padding: 10px; background-color: white;")
        preview_scroll.setWidget(self.preview_label)
        scroll_layout.addWidget(preview_scroll)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # --- SECCIÓN 5: Botones de acción ---
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.generate_btn = QPushButton("✓ Generar Código")
        self.generate_btn.setMinimumHeight(35)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_barcode)
        button_layout.addWidget(self.generate_btn)
        
        self.print_btn = QPushButton("🖨️ Imprimir")
        self.print_btn.setMinimumHeight(35)
        self.print_btn.setEnabled(False)
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover:enabled {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.print_btn.clicked.connect(self.print_barcode)
        button_layout.addWidget(self.print_btn)
        
        self.save_btn = QPushButton("💾 Guardar PNG")
        self.save_btn.setMinimumHeight(35)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover:enabled {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.save_btn.clicked.connect(self.save_barcode)
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def generate_random_code(self):
        """Genera un código aleatorio"""
        # Generar un código aleatorio de 8-12 caracteres
        length = random.randint(8, 12)
        random_code = ''.join(random.choices(string.digits, k=length))
        self.barcode_input.setText(random_code)
        # Generar automáticamente el código de barras
        self.generate_barcode()
    
    def on_label_size_changed(self):
        """Se ejecuta cuando cambia el tamaño de etiqueta predefinido"""
        size_text = self.label_size_combo.currentText()
        
        # Configurar tamaños según la selección
        if '4x6' in size_text:
            self.width_spinbox.setValue(100)
            self.height_spinbox.setValue(50)
        elif '3x5' in size_text:
            self.width_spinbox.setValue(75)
            self.height_spinbox.setValue(40)
        elif '2x4' in size_text:
            self.width_spinbox.setValue(50)
            self.height_spinbox.setValue(25)
        # Para 'Personalizado' no cambiar nada, dejar que el usuario lo haga
    
    def on_format_changed(self):
        """Se ejecuta cuando cambia el formato"""
        self.barcode_format = self.format_combo.currentText()
        if self.barcode_input.text():
            self.generate_barcode()
    
    def validate_input(self):
        """Valida la entrada del usuario"""
        text = self.barcode_input.text().strip()
        # Limpiar caracteres especiales según el formato
        if self.barcode_format == 'ean13':
            text = ''.join(c for c in text if c.isdigit())
            if len(text) > 13:
                text = text[:13]
            self.barcode_input.setText(text)
    
    def generate_barcode(self):
        """Genera el código de barras"""
        code = self.barcode_input.text().strip()
        
        if not code:
            QMessageBox.warning(self, "Error", "Por favor ingresa un código")
            self.preview_label.setText("")
            self.print_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            return
        
        try:
            # Crear archivo temporal para la imagen
            temp_dir = tempfile.gettempdir()
            barcode_filename = f"barcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            barcode_path = os.path.join(temp_dir, barcode_filename)
            
            # Generar el código de barras
            barcode_obj = barcode.get(self.barcode_format, code, writer=ImageWriter())
            barcode_obj.save(barcode_path)
            
            # Cargar imagen
            self.last_generated_path = f"{barcode_path}.png"
            self.last_generated_image = Image.open(self.last_generated_path)
            
            pixmap = QPixmap(self.last_generated_path)
            
            # Escalar para que se vea bien en el preview
            scaled_pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            
            # Habilitar botones
            self.print_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            
            # Emitir señal
            self.barcode_generated.emit(code)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar código: {str(e)}")
            self.preview_label.setText("")
            self.print_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
    
    def print_barcode(self):
        """Imprime el código de barras usando tu sistema integrado"""
        if not self.last_generated_path or not os.path.exists(self.last_generated_path):
            QMessageBox.warning(self, "Error", "Primero debes generar un código de barras")
            return
        
        try:
            from gui.dialogs.printer_selection_dialog import PrinterSelectionDialog
            from utils.printer_handler import print_image
            
            # Mostrar diálogo de selección de impresora
            printer_dialog = PrinterSelectionDialog(self)
            if printer_dialog.exec_() != QDialog.Accepted:
                return
            
            printer_name = printer_dialog.get_selected_printer()
            if not printer_name:
                QMessageBox.warning(self, "Error", "Por favor selecciona una impresora")
                return
            
            # Obtener opciones de personalización
            width_mm = self.width_spinbox.value()
            height_mm = self.height_spinbox.value()
            margin_top = self.margin_top_spinbox.value()
            margin_left = self.margin_left_spinbox.value()
            quality = self.quality_combo.currentText()
            
            # Para impresoras térmicas, procesar la imagen con opciones
            if any(x in printer_name.lower() for x in ['bt-', 'thermal', 'hoco', 'bluetooth']):
                from utils.escpos_thermal_printer import ThermalBluetoothPrinter
                from PIL import Image as PILImage
                
                # Cargar imagen
                img = PILImage.open(self.last_generated_path)
                
                # Redimensionar según opciones
                dpi = 300 if 'Alta' in quality else (203 if 'Media' in quality else 100)
                width_px = int((width_mm / 25.4) * dpi)
                height_px = int((height_mm / 25.4) * dpi)
                
                # Redimensionar manteniendo aspecto
                img.thumbnail((width_px, height_px), PILImage.Resampling.LANCZOS)
                
                # Imprimir en térmica
                success, message = ThermalBluetoothPrinter.print_image_thermal(img)
            else:
                # Para impresoras estándar
                success, message = print_image(self.last_generated_path, printer_name)
            
            if success:
                QMessageBox.information(self, "Éxito", f"Código de barras enviado a imprimir")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo imprimir:\n{message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al imprimir: {str(e)}")
    
    def save_barcode(self):
        """Guarda el código de barras como PNG"""
        if not self.last_generated_path or not os.path.exists(self.last_generated_path):
            QMessageBox.warning(self, "Error", "Primero debes generar un código de barras")
            return
        
        try:
            file_dialog = QtWidgets.QFileDialog()
            file_path, _ = file_dialog.getSaveFileName(
                self,
                "Guardar código de barras",
                f"codigo_barras_{self.barcode_input.text()}.png",
                "PNG Files (*.png);;All Files (*)"
            )
            
            if file_path:
                img = Image.open(self.last_generated_path)
                img.save(file_path)
                QMessageBox.information(self, "Éxito", f"Código guardado en:\n{file_path}")
                self.barcode_generated.emit(self.barcode_input.text())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
    
    def get_icon(self):
        """Obtiene el icono de la aplicación"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'icons', 'icon.ico')
            if os.path.exists(icon_path):
                return QtGui.QIcon(icon_path)
        except:
            pass
        return QtGui.QIcon()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- SECCIÓN 1: Tipo de código de barras ---
        format_layout = QHBoxLayout()
        format_label = QLabel("Formato:")
        format_label.setMinimumWidth(100)
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            'code128',
            'code39',
            'ean13',
            'ean8',
            'upca',
            'upce',
            'itf',
            'gs1',
        ])
        self.format_combo.setCurrentText('code128')
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Línea separadora
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line1)
        
        # --- SECCIÓN 2: Entrada de datos ---
        input_label = QLabel("Código a generar:")
        input_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(input_label)
        
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Ingresa el número/código para el código de barras")
        self.barcode_input.setMinimumHeight(35)
        self.barcode_input.textChanged.connect(self.validate_input)
        layout.addWidget(self.barcode_input)
        
        # Rango de códigos
        range_layout = QHBoxLayout()
        range_label = QLabel("¿Generar rango de códigos?")
        range_layout.addWidget(range_label)
        range_layout.addStretch()
        
        range_start_label = QLabel("Desde:")
        self.range_start = QSpinBox()
        self.range_start.setMinimum(1)
        self.range_start.setValue(1)
        self.range_start.setMaximum(99999)
        
        range_end_label = QLabel("Hasta:")
        self.range_end = QSpinBox()
        self.range_end.setMinimum(1)
        self.range_end.setValue(1)
        self.range_end.setMaximum(99999)
        
        range_layout.addWidget(range_start_label)
        range_layout.addWidget(self.range_start)
        range_layout.addWidget(range_end_label)
        range_layout.addWidget(self.range_end)
        layout.addLayout(range_layout)
        
        # Línea separadora
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)
        
        # --- SECCIÓN 3: Vista previa ---
        preview_label = QLabel("Vista previa:")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(preview_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(250)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; padding: 10px; background-color: white;")
        scroll.setWidget(self.preview_label)
        layout.addWidget(scroll)
        
        # --- SECCIÓN 4: Botones de acción ---
        button_layout = QGridLayout()
        button_layout.setSpacing(10)
        
        self.generate_btn = QPushButton("Generar Código")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_barcode)
        button_layout.addWidget(self.generate_btn, 0, 0)
        
        self.print_btn = QPushButton("Imprimir")
        self.print_btn.setMinimumHeight(40)
        self.print_btn.setEnabled(False)
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.print_btn.clicked.connect(self.print_barcode)
        button_layout.addWidget(self.print_btn, 0, 1)
        
        self.save_btn = QPushButton("Guardar PNG")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.save_btn.clicked.connect(self.save_barcode)
        button_layout.addWidget(self.save_btn, 0, 2)
        
        layout.addLayout(button_layout)
        
        # --- SECCIÓN 5: Info de uso ---
        info_text = QLabel(
            "💡 Tips:\n"
            "• Ingresa un código o números para generar el código de barras\n"
            "• O usa el rango para generar múltiples códigos secuenciales\n"
            "• Imprime en papel adhesivo para stickers\n"
            "• El formato Code128 es el más versátil"
        )
        info_text.setStyleSheet("color: #666; font-size: 9px; padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        info_text.setWordWrap(True)
        layout.addWidget(info_text)
        
        self.setLayout(layout)
    
    def on_format_changed(self):
        """Se ejecuta cuando cambia el formato"""
        self.barcode_format = self.format_combo.currentText()
        if self.barcode_input.text():
            self.generate_barcode()
    
    def validate_input(self):
        """Valida la entrada del usuario"""
        text = self.barcode_input.text().strip()
        # Limpiar caracteres especiales según el formato
        if self.barcode_format == 'ean13':
            text = ''.join(c for c in text if c.isdigit())
            if len(text) > 13:
                text = text[:13]
            self.barcode_input.setText(text)
    
    def generate_barcode(self):
        """Genera el código de barras"""
        code = self.barcode_input.text().strip()
        
        if not code:
            QMessageBox.warning(self, "Error", "Por favor ingresa un código")
            self.preview_label.setText("")
            self.print_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            return
        
        try:
            # Crear archivo temporal para la imagen
            temp_dir = tempfile.gettempdir()
            barcode_filename = f"barcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            barcode_path = os.path.join(temp_dir, barcode_filename)
            
            # Generar el código de barras
            barcode_obj = barcode.get(self.barcode_format, code, writer=ImageWriter())
            barcode_obj.save(barcode_path)
            
            # Cargar y mostrar en preview
            self.last_generated_path = f"{barcode_path}.png"
            pixmap = QPixmap(self.last_generated_path)
            
            # Escalar para que se vea bien en el preview
            scaled_pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            
            # Habilitar botones
            self.print_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            
            # Emitir señal
            self.barcode_generated.emit(code)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar código: {str(e)}")
            self.preview_label.setText("")
            self.print_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
    
    def print_barcode(self):
        """Imprime el código de barras usando tu sistema integrado"""
        if not self.last_generated_path or not os.path.exists(self.last_generated_path):
            QMessageBox.warning(self, "Error", "Primero debes generar un código de barras")
            return
        
        try:
            from gui.dialogs.printer_selection_dialog import PrinterSelectionDialog
            
            # Mostrar diálogo de selección de impresora
            printer_dialog = PrinterSelectionDialog(self)
            if printer_dialog.exec_() != QDialog.Accepted:
                return
            
            printer_name = printer_dialog.get_selected_printer()
            if not printer_name:
                QMessageBox.warning(self, "Error", "Por favor selecciona una impresora")
                return
            
            # Usar el sistema de impresión integrado
            from utils.printer_handler import print_image
            
            success, message = print_image(self.last_generated_path, printer_name)
            
            if success:
                QMessageBox.information(self, "Éxito", f"Código de barras enviado a imprimir\n{message}")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo imprimir:\n{message}")
        except ImportError as e:
            QMessageBox.critical(self, "Error", f"Error de importación: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al imprimir: {str(e)}")
    
    def save_barcode(self):
        """Guarda el código de barras como PNG"""
        if not self.last_generated_path or not os.path.exists(self.last_generated_path):
            QMessageBox.warning(self, "Error", "Primero debes generar un código de barras")
            return
        
        try:
            file_dialog = QtWidgets.QFileDialog()
            file_path, _ = file_dialog.getSaveFileName(
                self,
                "Guardar código de barras",
                f"codigo_barras_{self.barcode_input.text()}.png",
                "PNG Files (*.png);;All Files (*)"
            )
            
            if file_path:
                img = Image.open(self.last_generated_path)
                img.save(file_path)
                QMessageBox.information(self, "Éxito", f"Código guardado en:\n{file_path}")
                self.barcode_generated.emit(self.barcode_input.text())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
