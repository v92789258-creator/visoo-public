"""
Diálogo para generar reportes globales de ventas con filtros de período.
Permite seleccionar: Anuales, Mensuales, Semanales, o Rango Personalizado.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QDateEdit, QGroupBox, QSpinBox, QMessageBox, QStackedWidget, QWidget
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont


class ReporteGlobalDialog(QDialog):
    """Diálogo de dos pasos para generar reportes globales."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generar Reporte Global")
        self.setGeometry(100, 100, 500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QGroupBox {
                border: 2px solid #00B0D0;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                background-color: #00B0D0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0099B8;
            }
            QPushButton:pressed {
                background-color: #0077A3;
            }
            QPushButton#cancelBtn {
                background-color: #cccccc;
            }
            QPushButton#cancelBtn:hover {
                background-color: #bbbbbb;
            }
        """)
        
        self.selected_period = None
        self.start_date = None
        self.end_date = None
        self.selected_format = None
        self.current_step = 1
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializa la interfaz del diálogo."""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Stack widget para mostrar paso 1 o paso 2
        self.stacked_widget = QStackedWidget()
        
        # Paso 1: Selector de período
        step1 = self.create_step1()
        self.stacked_widget.addWidget(step1)
        
        # Paso 2: Selector de formato
        step2 = self.create_step2()
        self.stacked_widget.addWidget(step2)
        
        layout.addWidget(self.stacked_widget)
        
        # ========== BOTONES ==========
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.back_btn = QPushButton("← Atrás")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setMinimumWidth(120)
        self.back_btn.setVisible(False)
        
        self.next_btn = QPushButton("Siguiente →")
        self.next_btn.clicked.connect(self.go_next)
        self.next_btn.setMinimumWidth(120)
        
        self.gen_btn = QPushButton("Generar Reporte")
        self.gen_btn.clicked.connect(self.accept)
        self.gen_btn.setMinimumWidth(120)
        self.gen_btn.setVisible(False)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(120)
        
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.gen_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_step1(self):
        """Crea el widget del paso 1: Selector de período."""
        step1 = QWidget()
        layout = QVBoxLayout(step1)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("Selecciona el período del reporte")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Tipo de período
        period_group = QGroupBox("Tipo de Período")
        period_layout = QVBoxLayout()
        
        period_label = QLabel("Selecciona período:")
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "Anuales",
            "Mensuales",
            "Semanales",
            "Rango Personalizado"
        ])
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        
        period_layout.addWidget(period_label)
        period_layout.addWidget(self.period_combo)
        period_group.setLayout(period_layout)
        layout.addWidget(period_group)
        
        # Filtro por año
        year_group = QGroupBox("Filtrar por Año")
        year_layout = QVBoxLayout()
        
        year_label = QLabel("Año:")
        self.year_spin = QSpinBox()
        current_year = QDate.currentDate().year()
        self.year_spin.setMinimum(2020)
        self.year_spin.setMaximum(current_year + 5)
        self.year_spin.setValue(current_year)
        self.year_spin.setMinimumWidth(100)
        
        year_layout.addWidget(year_label)
        year_layout.addWidget(self.year_spin)
        year_group.setLayout(year_layout)
        layout.addWidget(year_group)
        
        # Rango personalizado
        range_group = QGroupBox("Rango Personalizado")
        range_layout = QVBoxLayout()
        range_layout.setSpacing(10)
        
        # Fecha inicio
        start_h_layout = QHBoxLayout()
        start_label = QLabel("Desde:")
        start_label.setMinimumWidth(80)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDateRange(QDate(2020, 1, 1), QDate(current_year + 5, 12, 31))
        start_h_layout.addWidget(start_label)
        start_h_layout.addWidget(self.start_date_edit)
        range_layout.addLayout(start_h_layout)
        
        # Fecha fin
        end_h_layout = QHBoxLayout()
        end_label = QLabel("Hasta:")
        end_label.setMinimumWidth(80)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDateRange(QDate(2020, 1, 1), QDate(current_year + 5, 12, 31))
        end_h_layout.addWidget(end_label)
        end_h_layout.addWidget(self.end_date_edit)
        range_layout.addLayout(end_h_layout)
        
        range_group.setLayout(range_layout)
        layout.addWidget(range_group)
        
        # Inicialmente ocultamos el rango personalizado
        range_group.setVisible(False)
        self.range_group = range_group
        
        layout.addStretch()
        
        return step1
    
    def create_step2(self):
        """Crea el widget del paso 2: Selector de formato."""
        step2 = QWidget()
        layout = QVBoxLayout(step2)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("Selecciona el Formato del Reporte")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setAlignment(Qt.AlignCenter)
        title.setFont(title_font)
        layout.addWidget(title)
        
        subtitle = QLabel("Elige cómo deseas que se vea tu reporte de ventas")
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Contenedor para las opciones
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)
        
        # Opción 1: Con Diseño
        design_btn = QPushButton()
        design_btn.setMinimumSize(200, 200)
        design_btn.setText("✨ Con Diseño\n\nReporte formateado y profesional\ncon colores y estilos")
        design_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 8px;
                color: #333;
                font-weight: bold;
                font-size: 11px;
                padding: 20px;
            }
            QPushButton:hover {
                border: 2px solid #00B0D0;
                background-color: #f0f8ff;
            }
        """)
        design_btn.clicked.connect(lambda: self.select_format("con_diseño"))
        options_layout.addWidget(design_btn)
        
        # Opción 2: Sin Diseño
        simple_btn = QPushButton()
        simple_btn.setMinimumSize(200, 200)
        simple_btn.setText("📋 Sin Diseño\n\nReporte simple y limpio\nsin estilos adicionales")
        simple_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 8px;
                color: #333;
                font-weight: bold;
                font-size: 11px;
                padding: 20px;
            }
            QPushButton:hover {
                border: 2px solid #00B0D0;
                background-color: #f0f8ff;
            }
        """)
        simple_btn.clicked.connect(lambda: self.select_format("sin_diseño"))
        options_layout.addWidget(simple_btn)
        
        layout.addLayout(options_layout)
        layout.addStretch()
        
        return step2
    
    def on_period_changed(self, text):
        """Muestra/oculta el rango personalizado según la selección."""
        if text == "Rango Personalizado":
            self.range_group.setVisible(True)
        else:
            self.range_group.setVisible(False)
    
    def go_next(self):
        """Avanza al siguiente paso."""
        if self.current_step == 1:
            # Validar rango personalizado
            period = self.period_combo.currentText()
            if period == "Rango Personalizado":
                start_date = self.start_date_edit.date().toPyDate()
                end_date = self.end_date_edit.date().toPyDate()
                if start_date > end_date:
                    QMessageBox.warning(self, "Error", "La fecha 'Desde' debe ser anterior a 'Hasta'")
                    return
            
            # Cambiar a paso 2
            self.current_step = 2
            self.stacked_widget.setCurrentIndex(1)
            self.next_btn.setVisible(False)
            self.back_btn.setVisible(True)
            self.gen_btn.setVisible(True)
    
    def go_back(self):
        """Vuelve al paso anterior."""
        if self.current_step == 2:
            self.current_step = 1
            self.stacked_widget.setCurrentIndex(0)
            self.next_btn.setVisible(True)
            self.back_btn.setVisible(False)
            self.gen_btn.setVisible(False)
            self.selected_format = None
    
    def select_format(self, format_type):
        """Selecciona el formato y genera el reporte."""
        self.selected_format = format_type
        self.accept()
    
    def get_parameters(self):
        """Retorna los parámetros seleccionados."""
        period = self.period_combo.currentText()
        year = self.year_spin.value()
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        
        return {
            'period': period,
            'year': year,
            'start_date': start_date,
            'end_date': end_date,
            'format': self.selected_format
        }

