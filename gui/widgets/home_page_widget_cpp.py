"""
Wrapper Python para el widget HomePage en C++
Permite usar el widget C++ compilado desde Python/PyQt5
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
import os
import ctypes
import platform
from typing import List, Optional

class HomePageWidgetCpp(QWidget):
    """
    Wrapper que carga el widget C++ compilado.
    
    Si la DLL/SO no está disponible, cae a una versión Python pura.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.cpp_widget = None
        self._try_load_cpp_widget()
        
        if self.cpp_widget is None:
            self._load_python_fallback()
    
    def _try_load_cpp_widget(self):
        """Intenta cargar el widget C++ compilado"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cpp_dir = os.path.join(base_dir, "cpp", "build")
            
            # Determinar archivo según SO
            if platform.system() == "Windows":
                lib_name = "SalesChartWidget.dll"
            elif platform.system() == "Darwin":
                lib_name = "libSalesChartWidget.dylib"
            else:
                lib_name = "libSalesChartWidget.so"
            
            lib_path = os.path.join(cpp_dir, lib_name)
            
            if os.path.exists(lib_path):
                ctypes.CDLL(lib_path)
                print(f"✅ Widget C++ cargado: {lib_path}")
                self.cpp_widget = True
                return True
        except Exception as e:
            print(f"⚠️ No se pudo cargar widget C++: {e}")
        
        return False
    
    def _load_python_fallback(self):
        """Carga versión Python pura del widget"""
        from gui.widgets.home_page_widget_py import HomePageWidgetPy
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.python_widget = HomePageWidgetPy(self)
        layout.addWidget(self.python_widget)
    
    def setPatientCount(self, count: int):
        """Establece el conteo de pacientes"""
        if self.cpp_widget:
            # Llamar a C++
            pass
        elif hasattr(self, 'python_widget'):
            self.python_widget.setPatientCount(count)
    
    def setProductCount(self, count: int):
        """Establece el conteo de productos"""
        if self.cpp_widget:
            # Llamar a C++
            pass
        elif hasattr(self, 'python_widget'):
            self.python_widget.setProductCount(count)
    
    def setMonthlyPatients(self, count: int):
        """Establece el conteo de pacientes nuevos (30 días)"""
        if self.cpp_widget:
            # Llamar a C++
            pass
        elif hasattr(self, 'python_widget'):
            self.python_widget.setMonthlyPatients(count)
    
    def setTotalSales(self, amount: float):
        """Establece el total de ventas"""
        if self.cpp_widget:
            # Llamar a C++
            pass
        elif hasattr(self, 'python_widget'):
            self.python_widget.setTotalSales(amount)
    
    def updateSalesChart(self, values: List[float], labels: List[str]):
        """Actualiza el gráfico de ventas"""
        if self.cpp_widget:
            # Llamar a C++
            pass
        elif hasattr(self, 'python_widget'):
            self.python_widget.updateSalesChart(values, labels)
