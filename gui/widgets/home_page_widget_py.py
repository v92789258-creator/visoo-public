"""
Versión Python pura de la página principal (HomePage)
Esta es la implementación en C++ renderizada con Python/PyQt5
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from typing import List

class SalesCardPy(QWidget):
    """Tarjeta de información de ventas"""
    
    def __init__(self, title: str, value: str, color: str = "#1976d2", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setMaximumHeight(180)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Título
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666; font-size: 13px; font-weight: 500;")
        layout.addWidget(title_label)
        
        # Valor
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: 700;")
        layout.addWidget(self.value_label)
        
        layout.addStretch()
        
        # Estilo de tarjeta
        self.setStyleSheet(f"""
            QWidget {{
                background: white;
                border-radius: 12px;
                border-left: 5px solid {color};
            }}
        """)
    
    def setValue(self, value: str):
        """Actualiza el valor mostrado"""
        self.value_label.setText(value)


class HomePageWidgetPy(QWidget):
    """Página principal completa en Python/C++"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.setStyleSheet("background-color: #f8f9fa;")
        
        self.patient_count = 0
        self.product_count = 0
        self.monthly_patients = 0
        self.total_sales = 0.0
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # ===== HEADER =====
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        title_label = QLabel("Bienvenido — Mi Óptica")
        title_label.setStyleSheet("color: #1a1a1a; font-size: 28px; font-weight: 700;")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Panel de control y estadísticas")
        subtitle_label.setStyleSheet("color: #999; font-size: 14px; font-weight: 400;")
        header_layout.addWidget(subtitle_label)
        
        main_layout.addWidget(header_container)
        main_layout.addSpacing(30)
        
        # ===== TARJETAS DE INFORMACIÓN =====
        self._setup_cards(main_layout)
        main_layout.addSpacing(30)
        
        # ===== GRÁFICO DE VENTAS =====
        chart_title = QLabel("📊 Gráfico de Ventas")
        chart_title.setStyleSheet("color: #1a1a1a; font-size: 18px; font-weight: 600;")
        main_layout.addWidget(chart_title)
        
        self._setup_chart(main_layout)
        
        main_layout.addStretch()
    
    def _setup_cards(self, parent_layout):
        """Configura las tarjetas de información"""
        cards_widget = QWidget()
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setSpacing(20)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear tarjetas
        self.patients_card = SalesCardPy("Pacientes", "1", "#1976d2")
        self.products_card = SalesCardPy("Productos", "0", "#ff9800")
        self.monthly_patients_card = SalesCardPy("Nuevos (30d)", "1", "#4caf50")
        self.sales_card = SalesCardPy("Ventas", "S/ 0.00", "#e91e63")
        
        # Añadir a grid (2x2)
        cards_layout.addWidget(self.patients_card, 0, 0)
        cards_layout.addWidget(self.products_card, 0, 1)
        cards_layout.addWidget(self.monthly_patients_card, 0, 2)
        cards_layout.addWidget(self.sales_card, 0, 3)
        
        parent_layout.addWidget(cards_widget)
    
    def _setup_chart(self, parent_layout):
        """Configura el área del gráfico"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(400)
        chart_widget.setStyleSheet("background: white; border-radius: 12px;")
        
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(20, 20, 20, 20)
        
        # Importar el gráfico de ventas
        from gui.widgets.sales_chart_widget import SalesChartWidgetPy
        
        self.chart = SalesChartWidgetPy(chart_widget)
        self.chart.setTitle("Gráfico de Ventas — Últimos 15 días")
        self.chart.setLineColor(QColor(25, 118, 210))
        
        chart_layout.addWidget(self.chart)
        parent_layout.addWidget(chart_widget)
    
    def setPatientCount(self, count: int):
        """Establece el conteo de pacientes"""
        self.patient_count = count
        self.patients_card.setValue(str(count))
    
    def setProductCount(self, count: int):
        """Establece el conteo de productos"""
        self.product_count = count
        self.products_card.setValue(str(count))
    
    def setMonthlyPatients(self, count: int):
        """Establece el conteo de pacientes nuevos (30 días)"""
        self.monthly_patients = count
        self.monthly_patients_card.setValue(str(count))
    
    def setTotalSales(self, amount: float):
        """Establece el total de ventas"""
        self.total_sales = amount
        self.sales_card.setValue(f"S/ {amount:,.2f}")
    
    def updateSalesChart(self, values: List[float], labels: List[str]):
        """Actualiza el gráfico de ventas"""
        if hasattr(self, 'chart'):
            self.chart.setData(values, labels)
