"""
Charts Components - Graficos ultra-ligeros con QPainter nativo

Responsabilidades:
- SalesBarChart: Grafico de barras ultimos 15 dias
- ComparisonLineChart: Grafico de lineas mes anterior vs actual

Ventajas:
- SIN DEPENDENCIAS EXTERNAS (usando QPainter nativo de PyQt5)
- ~100x mas rapido que Matplotlib
- Minimo uso de memoria
- Rendering suave y sin lags
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QSize, QVariantAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush
import logging
import calendar
from datetime import datetime

logger = logging.getLogger(__name__)

THEME = {
    "card_bg": "#FBFCFE",
    "text_dim": "#64748B",
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "accent": "#0F172A",
    "grid": "#DCE6F2",
}


def _load_sales_data(username, allow_remote_restore=True):
    try:
        from utils.file_handler import cargar_ventas_dashboard

        ventas = cargar_ventas_dashboard(
            username,
            allow_remote_restore=allow_remote_restore,
        ) or []
    except Exception:
        ventas = []

    if isinstance(ventas, dict):
        ventas = list(ventas.values())
    return ventas if isinstance(ventas, list) else []



class SalesBarChart(QFrame):
    """Grafico de barras con ventas ultimos 15 dias - QPAINTER (ULTRA RAPIDO!)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {THEME['card_bg']}; border: 1px solid #E2E8F0; border-radius: 18px;")
        self.setFixedHeight(250)
        self.sales_data = []
        self.padding = 50  # Espacio para labels
        self._animation_progress = 1.0
        self._loading = True
        self._bar_animation = QVariantAnimation(self)
        self._bar_animation.setDuration(700)
        self._bar_animation.setStartValue(0.0)
        self._bar_animation.setEndValue(1.0)
        self._bar_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._bar_animation.valueChanged.connect(self._on_animation_value_changed)
        self._skeleton_animation = QVariantAnimation(self)
        self._skeleton_animation.setDuration(950)
        self._skeleton_animation.setStartValue(0.0)
        self._skeleton_animation.setEndValue(1.0)
        self._skeleton_animation.setLoopCount(-1)
        self._skeleton_animation.valueChanged.connect(lambda _value: self.update())
        self._skeleton_animation.start()
        
        self.render_chart()

    def _on_animation_value_changed(self, value):
        try:
            self._animation_progress = max(0.0, min(1.0, float(value)))
        except Exception:
            self._animation_progress = 1.0
        self.update()

    def _start_bar_animation(self):
        try:
            self._bar_animation.stop()
        except Exception:
            pass
        self._animation_progress = 0.0
        self._bar_animation.start()
    
    def paintEvent(self, event):
        """Dibuja el grafico usando QPainter"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            if getattr(self, "_loading", False):
                self._paint_bar_skeleton(painter)
                return

            # Datos
            data = list(self.sales_data or [])

            data = list(data)[:15]  # Asegurar 15 elementos

            # Area de dibujo
            rect = self.rect()
            margin = 30
            plot_width = rect.width() - 2 * margin
            plot_height = rect.height() - 68
            x_start = margin
            y_start = 18

            # Encontrar max para escala
            max_val = max(data) if data else 0
            if max_val <= 0:
                painter.setPen(QPen(QColor(THEME["text_dim"])))
                painter.setFont(QFont("Segoe UI", 10))
                painter.drawText(QRect(margin, 10, rect.width() - 2 * margin, rect.height() - 20),
                                 Qt.AlignCenter, "Sin datos")
                return

            max_val = max_val * 1.2  # 20% extra para espacio

            # Dibujar grid horizontal
            grid_pen = QPen(QColor(THEME["grid"]), 1)
            painter.setPen(grid_pen)

            num_lines = 5
            for i in range(num_lines + 1):
                y = y_start + plot_height - (plot_height * i / num_lines)
                painter.drawLine(x_start, int(y), x_start + plot_width, int(y))

                # Labels Y
                val = int(max_val * i / num_lines)
                label_font = QFont("Segoe UI", 8)
                painter.setFont(label_font)
                painter.setPen(QPen(QColor(THEME["text_dim"])))
                painter.drawText(int(x_start - 40), int(y - 5), 35, 20, Qt.AlignRight | Qt.AlignVCenter, str(val))

            # Dibujar barras
            num_bars = len(data)
            if num_bars <= 0:
                return

            bar_width = plot_width / num_bars * 0.7  # 70% del espacio disponible
            spacing = (plot_width - bar_width * num_bars) / (num_bars + 1)

            bar_color = QColor(THEME["primary"])
            progress = max(0.0, min(1.0, float(getattr(self, "_animation_progress", 1.0))))

            for i, value in enumerate(data):
                x = x_start + spacing + i * (bar_width + spacing)
                bar_height = (value / max_val) * plot_height * progress
                y = y_start + plot_height - bar_height

                # Dibujar barra
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(bar_color))
                painter.drawRoundedRect(QRect(int(x), int(y), int(bar_width), int(bar_height)), 9, 9)

                # Label X (dia)
                painter.setPen(QPen(QColor(THEME["text_dim"])))
                label_font = QFont("Segoe UI", 8)
                painter.setFont(label_font)
                painter.drawText(int(x), int(y_start + plot_height + 5), int(bar_width), 20,
                                 Qt.AlignHCenter | Qt.AlignTop, str(i + 1))

            # Etiquetas de ejes
            axis_font = QFont("Segoe UI", 9)
            painter.setFont(axis_font)
            painter.setPen(QPen(QColor(THEME["text_dim"])))
            painter.drawText(QRect(x_start, y_start + plot_height + 25, 100, 25),
                             Qt.AlignHCenter | Qt.AlignVCenter, "Dia")

            painter.save()
            painter.translate(10, y_start + plot_height / 2)
            painter.rotate(-90)
            painter.drawText(QRect(0, 0, plot_height, 20), Qt.AlignHCenter | Qt.AlignVCenter, "Ventas (S/.)")
            painter.restore()
        finally:
            painter.end()
    
    def render_chart(self):
        """Actualiza el grafico"""
        self.update()  # Triggers paintEvent
    
    def setSalesData(self, data):
        """Actualiza los datos de ventas"""
        self.sales_data = list(data)[:15]
        self._loading = False
        try:
            self._skeleton_animation.stop()
        except Exception:
            pass
        self._start_bar_animation()
        self.render_chart()

    def setLoading(self, loading=True):
        self._loading = bool(loading)
        if self._loading:
            try:
                if self._skeleton_animation.state() != QVariantAnimation.Running:
                    self._skeleton_animation.start()
            except Exception:
                self._skeleton_animation.start()
        else:
            try:
                self._skeleton_animation.stop()
            except Exception:
                pass
        self.update()

    def _paint_bar_skeleton(self, painter):
        rect = self.rect()
        margin = 30
        plot_width = rect.width() - 2 * margin
        plot_height = rect.height() - 68
        x_start = margin
        y_start = 18
        pulse = 0.35 + (float(self._skeleton_animation.currentValue() or 0.0) * 0.45)
        base = QColor(229, 235, 243)
        glow = QColor(214, 223, 236)
        grid_pen = QPen(QColor(232, 238, 246), 1)
        painter.setPen(grid_pen)

        for i in range(6):
            y = y_start + plot_height - (plot_height * i / 5)
            painter.drawLine(x_start, int(y), x_start + plot_width, int(y))

        bars = [0.25, 0.48, 0.36, 0.62, 0.44, 0.72, 0.55, 0.81, 0.58, 0.68, 0.40, 0.77, 0.61, 0.52, 0.70]
        bar_width = plot_width / len(bars) * 0.7
        spacing = (plot_width - bar_width * len(bars)) / (len(bars) + 1)
        painter.setPen(Qt.NoPen)
        for i, ratio in enumerate(bars):
            x = x_start + spacing + i * (bar_width + spacing)
            bar_height = plot_height * ratio
            y = y_start + plot_height - bar_height
            color = QColor(glow if i % 2 == 0 else base)
            color.setAlphaF(min(1.0, pulse))
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRect(int(x), int(y), int(bar_width), int(bar_height)), 9, 9)




class ComparisonLineChart(QFrame):
    """Grafico de lineas comparativo - QPAINTER NATIVO (100x MAS RAPIDO!)"""
    
    # Senal para cuando se hace click en un dia
    day_clicked = pyqtSignal(int)
    
    def __init__(self, username=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {THEME['card_bg']}; border: 1px solid #E2E8F0; border-radius: 18px;")
        self.setFixedHeight(320)
        self.username = username
        self.sales_data = []
        self._sales_data_initialized = False
        self.allow_remote_restore = True
        self.purchase_data = {}
        self.current_month_data = {}
        self.previous_month = None
        self.current_month = None
        self.days = None
        self.clicked_day = None
        self._animation_progress = 1.0
        self._loading = True
        self._line_animation = QVariantAnimation(self)
        self._line_animation.setDuration(900)
        self._line_animation.setStartValue(0.0)
        self._line_animation.setEndValue(1.0)
        self._line_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._line_animation.valueChanged.connect(self._on_animation_value_changed)
        self._skeleton_animation = QVariantAnimation(self)
        self._skeleton_animation.setDuration(950)
        self._skeleton_animation.setStartValue(0.0)
        self._skeleton_animation.setEndValue(1.0)
        self._skeleton_animation.setLoopCount(-1)
        self._skeleton_animation.valueChanged.connect(lambda _value: self.update())
        self._skeleton_animation.start()

    def _on_animation_value_changed(self, value):
        try:
            self._animation_progress = max(0.0, min(1.0, float(value)))
        except Exception:
            self._animation_progress = 1.0
        self.update()

    def _start_line_animation(self):
        if self.current_month is None or self.previous_month is None:
            self._animation_progress = 1.0
            return
        try:
            self._line_animation.stop()
        except Exception:
            pass
        self._animation_progress = 0.0
        self._line_animation.start()

    @staticmethod
    def _parse_sale_date(fecha_str):
        """Parsea fecha de venta en formatos historicos/actuales."""
        if not fecha_str:
            return None

        fecha_texto = str(fecha_str).strip()
        if not fecha_texto:
            return None

        if fecha_texto.endswith("Z"):
            fecha_texto = fecha_texto[:-1]

        formatos = [
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formatos:
            try:
                return datetime.strptime(fecha_texto, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def _to_float(value):
        """Normaliza montos para evitar errores por tipos/string."""
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = value.strip().replace("S/", "").replace("$", "").replace(" ", "")
            cleaned = cleaned.replace(",", "")
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        return 0.0

    def set_sales_data(self, sales_data=None, allow_remote_restore=True):
        if isinstance(sales_data, dict):
            sales_data = list(sales_data.values())
        if isinstance(sales_data, list):
            self.sales_data = list(sales_data)
        else:
            self.sales_data = []
        self._sales_data_initialized = True
        self.allow_remote_restore = bool(allow_remote_restore)

    def load_real_data(self, sales_data=None, allow_remote_restore=None):
        """Carga datos reales de ventas del archivo JSON"""
        self._loading = True
        self.update()
        now = datetime.now()
        current_year = now.year
        current_month_num = now.month
        if current_month_num == 1:
            previous_year = current_year - 1
            previous_month_num = 12
        else:
            previous_year = current_year
            previous_month_num = current_month_num - 1

        current_month_days = calendar.monthrange(current_year, current_month_num)[1]
        previous_month_days = calendar.monthrange(previous_year, previous_month_num)[1]
        num_days = max(current_month_days, previous_month_days)

        try:
            if not self.username:
                self.purchase_data = {i: [] for i in range(1, num_days + 1)}
                self.current_month_data = {i: 0.0 for i in range(1, num_days + 1)}
                self.days = list(range(1, num_days + 1))
                self.current_month = [0.0] * num_days
                self.previous_month = [0.0] * num_days
                self._loading = False
                return

            if allow_remote_restore is None:
                allow_remote_restore = self.allow_remote_restore

            if sales_data is not None:
                self.set_sales_data(sales_data, allow_remote_restore=allow_remote_restore)
                ventas = list(self.sales_data)
            elif self._sales_data_initialized:
                ventas = list(self.sales_data)
            else:
                ventas = _load_sales_data(
                    self.username,
                    allow_remote_restore=bool(allow_remote_restore),
                )
                self.set_sales_data(ventas, allow_remote_restore=allow_remote_restore)
            
            self.purchase_data = {i: [] for i in range(1, num_days + 1)}
            self.current_month_data = {i: 0.0 for i in range(1, num_days + 1)}
            previous_month_data = {i: 0.0 for i in range(1, num_days + 1)}
            
            for venta in ventas:
                try:
                    fecha_obj = self._parse_sale_date(venta.get('fecha', ''))
                    if not fecha_obj:
                        continue

                    day = fecha_obj.day
                    if not (1 <= day <= num_days):
                        continue

                    total = self._to_float(venta.get('total', 0))

                    if fecha_obj.year == current_year and fecha_obj.month == current_month_num:
                        nombre_cliente = venta.get('paciente_nombre', 'Anonimo')
                        self.purchase_data[day].append(nombre_cliente)
                        self.current_month_data[day] += total
                    elif fecha_obj.year == previous_year and fecha_obj.month == previous_month_num:
                        previous_month_data[day] += total
                except Exception:
                    continue
            
            current_sales_count = sum(len(v) for v in self.purchase_data.values())
            logger.info(
                "[ComparisonLineChart] Datos cargados: %s compras del mes actual (%s-%s) y comparacion con %s-%s",
                current_sales_count,
                current_year,
                str(current_month_num).zfill(2),
                previous_year,
                str(previous_month_num).zfill(2)
            )
        except Exception as e:
            logger.error(f"[ComparisonLineChart] Error cargando datos: {e}")
            self.purchase_data = {i: [] for i in range(1, num_days + 1)}
            self.current_month_data = {i: 0.0 for i in range(1, num_days + 1)}
            previous_month_data = {i: 0.0 for i in range(1, num_days + 1)}
        
        # Prepare data
        self.days = list(range(1, num_days + 1))
        self.current_month = [float(self.current_month_data.get(day, 0.0)) for day in range(1, num_days + 1)]
        self.previous_month = [float(previous_month_data.get(day, 0.0)) for day in range(1, num_days + 1)]
        self._loading = False
        try:
            self._skeleton_animation.stop()
        except Exception:
            pass
        self._start_line_animation()
        self.update()
    
    def paintEvent(self, event):
        """Dibuja el grafico usando QPainter"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            if getattr(self, "_loading", False):
                self._paint_line_skeleton(painter)
                return

            if self.current_month is None or self.previous_month is None:
                return

            # Area de dibujo
            rect = self.rect()
            margin = 34
            plot_width = rect.width() - 2 * margin
            plot_height = rect.height() - 92
            x_start = margin
            y_start = 20

            num_days = len(self.current_month)
            if num_days <= 0:
                return

            # Encontrar max
            max_val = max(max(self.current_month), max(self.previous_month))
            if max_val <= 0:
                painter.setPen(QPen(QColor(THEME["text_dim"])))
                painter.setFont(QFont("Segoe UI", 10))
                painter.drawText(QRect(margin, 10, rect.width() - 2 * margin, rect.height() - 20),
                                 Qt.AlignCenter, "Sin datos")
                return

            max_val = max_val * 1.1

            # Grid horizontal
            grid_pen = QPen(QColor(THEME["grid"]), 1)
            painter.setPen(grid_pen)

            for i in range(6):
                y = y_start + plot_height - (plot_height * i / 5)
                painter.drawLine(x_start, int(y), x_start + plot_width, int(y))

                # Y labels
                val = int(max_val * i / 5)
                label_font = QFont("Segoe UI", 8)
                painter.setFont(label_font)
                painter.setPen(QPen(QColor(THEME["text_dim"])))
                painter.drawText(int(x_start - 45), int(y - 5), 40, 20, Qt.AlignRight | Qt.AlignVCenter, str(val))

            # Calcular posiciones de puntos
            x_spacing = plot_width / max(num_days - 1, 1)

            painter.save()
            progress = max(0.0, min(1.0, float(getattr(self, "_animation_progress", 1.0))))
            reveal_width = int(plot_width * progress)
            painter.setClipRect(QRect(int(x_start - 8), int(y_start - 12), max(0, reveal_width + 16), int(plot_height + 24)))

            # Dibujar linea mes anterior (gris)
            painter.setPen(QPen(QColor("#94A3B8"), 2.5))
            for i in range(num_days - 1):
                x1 = x_start + i * x_spacing
                y1 = y_start + plot_height - (self.previous_month[i] / max_val) * plot_height
                x2 = x_start + (i + 1) * x_spacing
                y2 = y_start + plot_height - (self.previous_month[i + 1] / max_val) * plot_height
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # Dibujar puntos mes anterior
            painter.setBrush(QBrush(QColor("#94A3B8")))
            painter.setPen(QPen(QColor("#64748B"), 1))
            for i in range(num_days):
                x = x_start + i * x_spacing
                y = y_start + plot_height - (self.previous_month[i] / max_val) * plot_height
                painter.drawEllipse(int(x - 3), int(y - 3), 6, 6)

            # Dibujar linea mes actual (principal)
            painter.setPen(QPen(QColor(THEME["primary_dark"]), 2.5))
            for i in range(num_days - 1):
                x1 = x_start + i * x_spacing
                y1 = y_start + plot_height - (self.current_month[i] / max_val) * plot_height
                x2 = x_start + (i + 1) * x_spacing
                y2 = y_start + plot_height - (self.current_month[i + 1] / max_val) * plot_height
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # Dibujar puntos mes actual
            painter.setBrush(QBrush(QColor(THEME["primary"])))
            painter.setPen(QPen(QColor(THEME["primary_dark"]), 1))
            for i in range(num_days):
                x = x_start + i * x_spacing
                y = y_start + plot_height - (self.current_month[i] / max_val) * plot_height
                painter.drawRect(int(x - 3), int(y - 3), 6, 6)

            painter.restore()

            # X labels (dias)
            painter.setPen(QPen(QColor(THEME["text_dim"])))
            label_font = QFont("Segoe UI", 8)
            painter.setFont(label_font)

            label_step = 5 if num_days > 10 else 1
            for i in range(0, num_days, label_step):
                x = x_start + i * x_spacing
                painter.drawText(int(x - 10), int(y_start + plot_height + 5), 20, 20,
                                 Qt.AlignHCenter | Qt.AlignTop, str(i + 1))

            # Asegurar que el ultimo dia se vea en el eje X
            if (num_days - 1) % label_step != 0:
                x = x_start + (num_days - 1) * x_spacing
                painter.drawText(int(x - 10), int(y_start + plot_height + 5), 20, 20,
                                 Qt.AlignHCenter | Qt.AlignTop, str(num_days))

            # Legend
            legend_y = y_start + plot_height + 26

            # Anterior
            painter.fillRect(margin, legend_y, 15, 15, QBrush(QColor("#94A3B8")))
            painter.setPen(QPen(QColor(THEME["text_dim"])))
            label_font = QFont("Segoe UI", 9)
            painter.setFont(label_font)
            painter.drawText(margin + 20, legend_y, 120, 15, Qt.AlignLeft | Qt.AlignVCenter, "Mes Anterior")

            # Actual
            painter.fillRect(margin + 160, legend_y, 15, 15, QBrush(QColor(THEME["primary"])))
            painter.drawText(margin + 180, legend_y, 120, 15, Qt.AlignLeft | Qt.AlignVCenter, "Mes Actual")
        finally:
            painter.end()
    
    def mousePressEvent(self, event):
        """Detecta clicks en el grafico"""
        if self.current_month is None:
            return
        
        rect = self.rect()
        margin = 50
        plot_width = rect.width() - 2 * margin
        plot_height = rect.height() - 100
        x_start = margin
        y_start = 30
        
        num_days = len(self.current_month)
        if num_days <= 0:
            return

        x_spacing = plot_width / max(num_days - 1, 1)
        
        # Obtener posicion del click
        mouse_x = event.x()
        
        # Convertir a dia
        if x_start <= mouse_x <= x_start + plot_width:
            if num_days == 1:
                day = 1
            else:
                day = int(round((mouse_x - x_start) / x_spacing)) + 1
                day = max(1, min(num_days, day))

            if 1 <= day <= num_days:
                logger.info(f"[ComparisonLineChart] Click en dia: {day}")
                self.day_clicked.emit(day)
    
    def render_chart(self):
        """Actualiza el grafico"""
        self.update()

    def setLoading(self, loading=True):
        self._loading = bool(loading)
        if self._loading:
            try:
                if self._skeleton_animation.state() != QVariantAnimation.Running:
                    self._skeleton_animation.start()
            except Exception:
                self._skeleton_animation.start()
        else:
            try:
                self._skeleton_animation.stop()
            except Exception:
                pass
        self.update()

    def _paint_line_skeleton(self, painter):
        rect = self.rect()
        margin = 34
        plot_width = rect.width() - 2 * margin
        plot_height = rect.height() - 92
        x_start = margin
        y_start = 20
        pulse = 0.32 + (float(self._skeleton_animation.currentValue() or 0.0) * 0.45)

        painter.setPen(QPen(QColor(232, 238, 246), 1))
        for i in range(6):
            y = y_start + plot_height - (plot_height * i / 5)
            painter.drawLine(x_start, int(y), x_start + plot_width, int(y))

        def draw_series(points, fill_color, line_color):
            painter.setPen(QPen(QColor(line_color), 2.5))
            x_spacing = plot_width / max(len(points) - 1, 1)
            for i in range(len(points) - 1):
                x1 = x_start + i * x_spacing
                y1 = y_start + plot_height - (plot_height * points[i])
                x2 = x_start + (i + 1) * x_spacing
                y2 = y_start + plot_height - (plot_height * points[i + 1])
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.setPen(Qt.NoPen)
            brush = QColor(fill_color)
            brush.setAlphaF(min(1.0, pulse))
            painter.setBrush(QBrush(brush))
            for i, ratio in enumerate(points):
                x = x_start + i * x_spacing
                y = y_start + plot_height - (plot_height * ratio)
                painter.drawRoundedRect(QRect(int(x - 4), int(y - 4), 8, 8), 3, 3)

        draw_series(
            [0.22, 0.58, 0.40, 0.63, 0.51, 0.69, 0.57, 0.74, 0.61, 0.78, 0.66, 0.83],
            "#CBD5E1",
            "#CBD5E1",
        )
        draw_series(
            [0.15, 0.44, 0.31, 0.54, 0.43, 0.60, 0.49, 0.67, 0.52, 0.71, 0.60, 0.76],
            "#93C5FD",
            "#93C5FD",
        )
