"""
Módulo de gráfico de ventas en C++ integrado con PyQt5
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QBrush
import math
from typing import List, Optional

class SalesChartWidgetPy(QWidget):
    """
    Widget de gráfico de líneas para mostrar ventas.
    Implementación en Python/PyQt5 (alternativa al C++)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.setStyleSheet("background-color: white;")
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        self.m_values = []
        self.m_labels = []
        self.m_title = "Gráfico de Ventas"
        self.m_lineColor = QColor(25, 118, 210)  # #1976d2
        
        # Márgenes
        self.m_marginLeft = 60
        self.m_marginRight = 40
        self.m_marginTop = 60
        self.m_marginBottom = 80
    
    def setData(self, values: List[float], labels: List[str]):
        """Establece los datos del gráfico"""
        self.m_values = values
        self.m_labels = labels
        self.update()
    
    def setTitle(self, title: str):
        """Establece el título del gráfico"""
        self.m_title = title
        self.update()
    
    def setLineColor(self, color: QColor):
        """Establece el color de la línea"""
        self.m_lineColor = color
        self.update()
    
    def clearData(self):
        """Limpia los datos del gráfico"""
        self.m_values = []
        self.m_labels = []
        self.update()
    
    def paintEvent(self, event):
        """Dibuja el gráfico"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            
            # Fondo blanco
            painter.fillRect(self.rect(), Qt.white)
            
            self._drawChart(painter)
        except Exception:
            # Fallback silencioso si hay error
            pass
    
    def _drawChart(self, painter: QPainter):
        """Dibuja el gráfico completo"""
        if not self.m_values:
            # Sin datos
            painter.setPen(Qt.gray)
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "No hay datos disponibles")
            return
        
        self._drawGrid(painter)
        self._drawAxes(painter)
        self._drawLine(painter)
        self._drawLabels(painter)
        self._drawLegend(painter)
    
    def _drawGrid(self, painter: QPainter):
        """Dibuja la cuadrícula"""
        chartWidth = self.width() - self.m_marginLeft - self.m_marginRight
        chartHeight = self.height() - self.m_marginTop - self.m_marginBottom
        
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
        
        # Líneas horizontales
        gridLines = 5
        for i in range(gridLines + 1):
            y = self.m_marginTop + (chartHeight * i // gridLines)
            painter.drawLine(self.m_marginLeft, y, self.width() - self.m_marginRight, y)
    
    def _drawAxes(self, painter: QPainter):
        """Dibuja los ejes"""
        chartWidth = self.width() - self.m_marginLeft - self.m_marginRight
        chartHeight = self.height() - self.m_marginTop - self.m_marginBottom
        
        # Ejes principales
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(self.m_marginLeft, self.m_marginTop, 
                        self.m_marginLeft, self.height() - self.m_marginBottom)
        painter.drawLine(self.m_marginLeft, self.height() - self.m_marginBottom,
                        self.width() - self.m_marginRight, self.height() - self.m_marginBottom)
        
        # Etiquetas de eje Y
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 9))
        
        if self.m_values:
            maxValue = max(self.m_values)
            if maxValue == 0:
                maxValue = 1
            
            for i in range(6):
                y = self.height() - self.m_marginBottom - (chartHeight * i // 5)
                value = int((maxValue * i) / 5)
                text_rect = self.rect()
                text_rect.setCoords(5, y - 10, self.m_marginLeft - 10, y + 10)
                painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, str(value))
    
    def _drawLine(self, painter: QPainter):
        """Dibuja la línea del gráfico"""
        if not self.m_values:
            return
        
        chartWidth = self.width() - self.m_marginLeft - self.m_marginRight
        chartHeight = self.height() - self.m_marginTop - self.m_marginBottom
        
        maxValue = max(self.m_values)
        if maxValue == 0:
            maxValue = 1
        
        # Dibujar línea
        painter.setPen(QPen(self.m_lineColor, 2.4))
        
        n = len(self.m_values)
        for i in range(n - 1):
            x1 = self.m_marginLeft + (chartWidth * i) / (n - 1) if n > 1 else self.m_marginLeft
            y1 = self.height() - self.m_marginBottom - (chartHeight * self.m_values[i]) / maxValue
            
            x2 = self.m_marginLeft + (chartWidth * (i + 1)) / (n - 1) if n > 1 else self.m_marginLeft + chartWidth
            y2 = self.height() - self.m_marginBottom - (chartHeight * self.m_values[i + 1]) / maxValue
            
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # Dibujar puntos
        painter.setBrush(self.m_lineColor)
        painter.setPen(Qt.NoPen)
        
        for i in range(n):
            x = self.m_marginLeft + (chartWidth * i) / (n - 1) if n > 1 else self.m_marginLeft
            y = self.height() - self.m_marginBottom - (chartHeight * self.m_values[i]) / maxValue
            painter.drawEllipse(QPointF(x, y), 4, 4)
    
    def _drawLabels(self, painter: QPainter):
        """Dibuja las etiquetas"""
        if not self.m_values:
            return
        
        chartWidth = self.width() - self.m_marginLeft - self.m_marginRight
        
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 9))
        
        # Etiquetas del eje X
        n = len(self.m_labels)
        for i in range(n):
            x = self.m_marginLeft + (chartWidth * i) / (n - 1) if n > 1 else self.m_marginLeft
            y = self.height() - self.m_marginBottom + 20
            
            painter.save()
            painter.translate(x, y)
            painter.rotate(-45)
            text_rect = self.rect()
            text_rect.setCoords(0, 0, 100, 30)
            painter.drawText(text_rect, Qt.AlignLeft, self.m_labels[i])
            painter.restore()
        
        # Título
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        title_rect = self.rect()
        title_rect.setCoords(self.m_marginLeft, 10, self.width() - self.m_marginRight, 50)
        painter.drawText(title_rect, Qt.AlignCenter, self.m_title)
    
    def _drawLegend(self, painter: QPainter):
        """Dibuja la leyenda"""
        legX = self.width() - self.m_marginRight - 150
        legY = self.m_marginTop + 20
        legWidth = 130
        legHeight = 50
        
        # Fondo de leyenda
        painter.setPen(QPen(Qt.gray, 1))
        painter.setBrush(QColor(255, 255, 255, 240))
        painter.drawRect(legX, legY, legWidth, legHeight)
        
        # Línea de ejemplo
        painter.setPen(QPen(self.m_lineColor, 2.4))
        painter.drawLine(legX + 10, legY + 15, legX + 30, legY + 15)
        painter.setBrush(self.m_lineColor)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(legX + 20, legY + 15), 3, 3)
        
        # Texto de leyenda
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 10))
        text_rect = self.rect()
        text_rect.setCoords(legX + 40, legY + 8, legX + legWidth, legY + 33)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, "Ventas")
