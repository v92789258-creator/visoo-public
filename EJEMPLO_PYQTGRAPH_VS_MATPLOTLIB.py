"""
Ejemplo: Comparacion Matplotlib vs PyQtGraph
Muestra como reemplazar Matplotlib con PyQtGraph en el dashboard
"""

# ============================================================
# OPCION 1: MATPLOTLIB (ACTUAL - PESADA)
# ============================================================
from PyQt5.QtWidgets import QFrame, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class ComparisonLineChart_OLD(QFrame):
    """Gráfico con Matplotlib - LENTO"""
    
    def __init__(self, username=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(350)
        
        # Matplotlib: 40-50 MB, 2-3 segundos en importar
        self.figure = Figure(figsize=(14, 4), dpi=100)  # Pesado
        self.canvas = FigureCanvasQTAgg(self.figure)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        
        # Renderizar gráfico (500-1000ms)
        self.render_chart()
    
    def render_chart(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        # ... mucho código ...
        self.canvas.draw()  # LENTO


# ============================================================
# OPCION 2: PyQtGRAPH (RECOMENDADO - RAPIDO)
# ============================================================
from PyQt5.QtWidgets import QFrame, QVBoxLayout
import pyqtgraph as pg

class ComparisonLineChart_NEW(QFrame):
    """Gráfico con PyQtGraph - RAPIDO"""
    
    def __init__(self, username=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(350)
        
        # PyQtGraph: 2-3 MB, 0.1 segundos en importar (30x más rápido!)
        self.plot_widget = pg.PlotWidget()  # Nativa de PyQt5
        self.plot_widget.setLabel('bottom', 'Día del Mes')
        self.plot_widget.setLabel('left', 'Ventas (S/.)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setBackground('w')
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_widget)
        
        # Renderizar gráfico (50-100ms - INSTANTANEO!)
        self.render_chart()
    
    def render_chart(self):
        days = list(range(1, 31))
        data_prev = [100 * i for i in days]
        data_curr = [120 * i for i in days]
        
        # Línea 1: Mes anterior
        self.plot_widget.plot(days, data_prev, pen='purple', 
                             name='Mes Anterior', symbol='o')
        
        # Línea 2: Mes actual
        self.plot_widget.plot(days, data_curr, pen='blue', 
                             name='Mes Actual', symbol='s')
        
        # YA ESTÁ RENDERIZADO (casi instantáneo!)


# ============================================================
# COMPARACION VISUAL: Código necesario
# ============================================================
print("""
MATPLOTLIB (Complicado):
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    figure = Figure(figsize=(14, 4), dpi=100)
    canvas = FigureCanvasQTAgg(figure)
    ax = figure.add_subplot(111)
    ax.plot(x, y1, ...)
    ax.plot(x, y2, ...)
    canvas.draw()

    Líneas: ~20
    Complejidad: Alta
    Velocidad: Lenta


PyQtGraph (Simple):
    import pyqtgraph as pg
    plot_widget = pg.PlotWidget()
    plot_widget.plot(x, y1, pen='purple')
    plot_widget.plot(x, y2, pen='blue')
    # YA ESTÁ LISTO!

    Líneas: ~5
    Complejidad: Baja
    Velocidad: Instantánea
""")


# ============================================================
# INSTALACION
# ============================================================
print("""
Para cambiar a PyQtGraph:

1. Instalar:
   pip install pyqtgraph

2. Reemplazar imports:
   # Antes:
   from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
   
   # Después:
   import pyqtgraph as pg

3. Cambiar código:
   # Antes:
   self.figure = Figure()
   self.canvas = FigureCanvasQTAgg(self.figure)
   
   # Después:
   self.plot_widget = pg.PlotWidget()

4. Listo! Ganaste 10x de velocidad!
""")


# ============================================================
# CARACTERISTICAS DE PyQtGraph
# ============================================================
print("""
Que puedes hacer con PyQtGraph:

1. Lineas normales:
   plot_widget.plot(x, y, pen='blue')

2. Lineas animadas (30+ FPS):
   curve = plot_widget.plot()
   curve.setData(x, y)  # Actualizar datos en tiempo real

3. Graficos de barras:
   barGraph = pg.BarGraphItem(x=x, height=heights, width=0.6)
   plot_widget.addItem(barGraph)

4. Scatter plots (puntos):
   scatter = pg.ScatterPlotItem(x=x, y=y, size=10)
   plot_widget.addItem(scatter)

5. Heatmaps (mapas de calor):
   heatmap = pg.ImageItem(image_data)
   plot_widget.addItem(heatmap)

6. Interactividad:
   - Zoom automático
   - Pan (arrastrar)
   - Click detection
   - Exportar a PNG/SVG

7. Multiples ejes:
   plot_widget.plot(x, y1, pen='blue')  # Eje izquierdo
   plot2 = pg.ViewBox()
   plot2.addItem(pg.PlotCurveItem(x, y2, pen='red'))
""")
