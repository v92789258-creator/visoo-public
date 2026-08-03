"""
Rankings components for top customers/products.
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from datetime import datetime
import logging

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MPL = True
except Exception:
    FigureCanvas = None
    Figure = None
    HAS_MPL = False

logger = logging.getLogger(__name__)

GENERIC_CUSTOMER_NAMES = {
    "",
    "anonimo",
    "anónimo",
    "desconocido",
    "cliente generico",
    "cliente genérico",
    "cliente general",
    "consumidor final",
    "publico general",
    "público general",
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


def _parse_sale_date(fecha_str):
    if not fecha_str:
        return None

    fecha_texto = str(fecha_str).strip()
    if not fecha_texto:
        return None

    if fecha_texto.endswith("Z"):
        fecha_texto = fecha_texto[:-1]

    formatos = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    )
    for fmt in formatos:
        try:
            return datetime.strptime(fecha_texto, fmt)
        except ValueError:
            continue
    return None


def _to_float(value):
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


def _get_current_month_sales(username, sales_data=None, allow_remote_restore=True):
    ventas = sales_data if sales_data is not None else _load_sales_data(
        username,
        allow_remote_restore=allow_remote_restore,
    )
    if isinstance(ventas, dict):
        ventas = list(ventas.values())
    if not isinstance(ventas, list):
        return []

    now = datetime.now()
    filtered = []
    for venta in ventas:
        if not isinstance(venta, dict):
            continue
        fecha = _parse_sale_date(venta.get("fecha"))
        if fecha and fecha.year == now.year and fecha.month == now.month:
            filtered.append(venta)
    return filtered


def _extract_customer_name(venta):
    for key in ("paciente_nombre", "cliente", "cliente_nombre"):
        value = str(venta.get(key, "") or "").strip()
        if value:
            return value
    return "Anonimo"


def _is_generic_customer(nombre):
    normalized = str(nombre or "").strip().lower()
    return normalized in GENERIC_CUSTOMER_NAMES


def _extract_sale_items(venta):
    for key in ("items", "productos"):
        items = venta.get(key)
        if isinstance(items, list):
            normalized = [item for item in items if isinstance(item, dict)]
            if normalized:
                return normalized

    sale_level_name = str(venta.get("producto") or venta.get("nombre") or "").strip()
    if sale_level_name:
        return [{
            "nombre": sale_level_name,
            "cantidad": venta.get("cantidad", 1),
            "total": venta.get("total") or venta.get("subtotal") or 0,
            "precio_unitario": venta.get("precio_unitario", 0),
        }]
    return []


class _BaseRanking(QFrame):
    """Base class with safe matplotlib lifecycle management."""

    def __init__(self, username=None, parent=None):
        super().__init__(parent)
        self.username = username
        self.parent_widget = parent
        self.setStyleSheet("background: transparent; border: none;")
        self.setFixedHeight(320)

        self.ax = None
        self.figure = None
        self.canvas = None
        self._fallback_label = None
        self._is_closing = False
        self._sales_data = []
        self._sales_data_initialized = False
        self._allow_remote_restore = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.destroyed.connect(lambda *_: self.cleanup())

    def _setup_canvas(self, pick_handler):
        if HAS_MPL:
            self.figure = Figure(figsize=(6, 4), dpi=100, facecolor='none')
            self.canvas = FigureCanvas(self.figure)
            self.canvas.mpl_connect('button_press_event', pick_handler)
            self.layout().addWidget(self.canvas)
        else:
            self.figure = None
            self.canvas = None
            self._fallback_label = QLabel("Ranking no disponible en version ligera")
            self._fallback_label.setAlignment(Qt.AlignCenter)
            self._fallback_label.setStyleSheet("color: #64748B; font-size: 12px;")
            self.layout().addWidget(self._fallback_label)

    def _canvas_alive(self):
        if not HAS_MPL or self.canvas is None:
            return False
        try:
            _ = self.canvas.parent()
            return True
        except Exception:
            return False

    def cleanup(self):
        """Stop pending draw-idle operations before widget deletion."""
        if self._is_closing:
            return
        self._is_closing = True

        if not HAS_MPL:
            return

        try:
            if self.canvas is not None:
                timer = getattr(self.canvas, "_draw_idle_timer", None)
                if timer is not None:
                    try:
                        timer.stop()
                    except Exception:
                        pass
                try:
                    self.canvas.close()
                except Exception:
                    pass
        except Exception:
            pass

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def set_sales_data(self, sales_data=None, allow_remote_restore=True):
        if isinstance(sales_data, dict):
            sales_data = list(sales_data.values())
        if isinstance(sales_data, list):
            self._sales_data = list(sales_data)
        else:
            self._sales_data = []
        self._sales_data_initialized = True
        self._allow_remote_restore = bool(allow_remote_restore)

    def _render_empty_state(self, message):
        if not HAS_MPL or not self._canvas_alive():
            if self._fallback_label is not None:
                self._fallback_label.setText(str(message or "Sin datos"))
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#F8FAFC')
        ax.set_axis_off()
        ax.text(0.5, 0.5, str(message or "Sin datos"),
                ha='center', va='center', fontsize=11, color='#64748B',
                transform=ax.transAxes)
        self.figure.tight_layout()
        self.canvas.draw()


class TopCustomersRanking(_BaseRanking):
    """Chart for top customers by sales amount."""

    def __init__(self, username=None, parent=None):
        super().__init__(username=username, parent=parent)
        self.clientes_data = []
        self._setup_canvas(self.on_pick_customer)
        self._render_empty_state("Cargando ranking...")

    def load_data(self, sales_data=None, allow_remote_restore=None):
        if not HAS_MPL or self._is_closing or not self._canvas_alive():
            return

        try:
            if allow_remote_restore is None:
                allow_remote_restore = self._allow_remote_restore

            if sales_data is not None:
                self.set_sales_data(sales_data, allow_remote_restore=allow_remote_restore)
            elif sales_data is None and not self._sales_data_initialized:
                self._sales_data = _load_sales_data(
                    self.username,
                    allow_remote_restore=bool(allow_remote_restore),
                )
                self._sales_data_initialized = True

            ventas = _get_current_month_sales(
                self.username,
                sales_data=self._sales_data,
                allow_remote_restore=bool(allow_remote_restore),
            )

            clientes = {}
            for venta in ventas:
                try:
                    cliente = _extract_customer_name(venta)
                    if _is_generic_customer(cliente):
                        continue
                    monto = _to_float(venta.get('total') or venta.get('monto') or 0.0)
                    if monto <= 0:
                        continue
                    clientes[cliente] = clientes.get(cliente, 0) + monto
                except Exception:
                    continue

            self.clientes_data = sorted(clientes.items(), key=lambda x: x[1], reverse=True)[:8]
            if not self.clientes_data:
                self._render_empty_state("Sin ventas del mes")
                return

            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            self.ax.set_facecolor('#F8FAFC')

            nombres = [c[0][:20] for c in self.clientes_data]
            montos = [c[1] for c in self.clientes_data]

            colores = ['#3B82F6', '#0EA5E9', '#06B6D4', '#14B8A6', '#10B981', '#84CC16', '#EAB308', '#F59E0B']

            y_pos = list(range(len(nombres)))
            self.ax.barh(y_pos, montos, color=colores[:len(nombres)], alpha=0.8, height=0.6)

            self.ax.set_yticks(y_pos)
            self.ax.set_yticklabels(nombres, fontsize=9, color='#64748B')
            self.ax.set_xlabel('Monto (S/.)', fontsize=10, color='#64748B', fontweight='bold')
            self.ax.invert_yaxis()

            self.ax.grid(axis='x', alpha=0.2, linestyle='--', color='#CBD5E1')
            self.ax.set_axisbelow(True)

            for i, mon in enumerate(montos):
                self.ax.text(mon, i, f' S/. {mon:,.2f}', va='center', fontsize=8, fontweight='bold', color='#0F172A')

            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['left'].set_color('#E2E8F0')
            self.ax.spines['bottom'].set_color('#E2E8F0')

            self.figure.tight_layout()
            if self._canvas_alive():
                self.canvas.draw()
        except Exception as e:
            logger.error("[TopCustomersRanking] Error: %s", e)
            self._render_empty_state("No se pudo cargar el ranking")

    def on_pick_customer(self, event):
        if not HAS_MPL:
            return
        try:
            if event.inaxes == self.ax and event.xdata is not None:
                pass
        except Exception as e:
            print(f"[on_pick_customer] Error: {e}")


class TopProductsRanking(_BaseRanking):
    """Chart for top products by sales amount."""

    def __init__(self, username=None, parent=None):
        super().__init__(username=username, parent=parent)
        self.productos_data = []
        self._setup_canvas(self.on_pick_product)
        self._render_empty_state("Cargando ranking...")

    def load_data(self, sales_data=None, allow_remote_restore=None):
        if not HAS_MPL or self._is_closing or not self._canvas_alive():
            return

        try:
            if allow_remote_restore is None:
                allow_remote_restore = self._allow_remote_restore

            if sales_data is not None:
                self.set_sales_data(sales_data, allow_remote_restore=allow_remote_restore)
            elif sales_data is None and not self._sales_data_initialized:
                self._sales_data = _load_sales_data(
                    self.username,
                    allow_remote_restore=bool(allow_remote_restore),
                )
                self._sales_data_initialized = True

            ventas = _get_current_month_sales(
                self.username,
                sales_data=self._sales_data,
                allow_remote_restore=bool(allow_remote_restore),
            )

            productos = {}
            for venta in ventas:
                try:
                    for item in _extract_sale_items(venta):
                        producto = str(item.get('nombre') or item.get('producto') or 'Desconocido').strip() or 'Desconocido'
                        monto = _to_float(item.get('total') or item.get('subtotal'))
                        if monto <= 0:
                            monto = _to_float(item.get('precio_unitario')) * max(1.0, _to_float(item.get('cantidad') or 1))
                        if monto <= 0:
                            continue
                        productos[producto] = productos.get(producto, 0) + monto
                except Exception:
                    continue
 
            self.productos_data = sorted(productos.items(), key=lambda x: x[1], reverse=True)[:8]
            if not self.productos_data:
                self._render_empty_state("Sin productos vendidos este mes")
                return

            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            self.ax.set_facecolor('#F8FAFC')

            nombres = [p[0][:20] for p in self.productos_data]
            montos = [p[1] for p in self.productos_data]

            colores = ['#10B981', '#059669', '#047857', '#065F46', '#14B8A6', '#06B6D4', '#0EA5E9', '#3B82F6']

            y_pos = list(range(len(nombres)))
            self.ax.barh(y_pos, montos, color=colores[:len(nombres)], alpha=0.8, height=0.6)
 
            self.ax.set_yticks(y_pos)
            self.ax.set_yticklabels(nombres, fontsize=9, color='#64748B')
            self.ax.set_xlabel('Monto (S/.)', fontsize=10, color='#64748B', fontweight='bold')
            self.ax.invert_yaxis()

            self.ax.grid(axis='x', alpha=0.2, linestyle='--', color='#CBD5E1')
            self.ax.set_axisbelow(True)

            for i, mon in enumerate(montos):
                self.ax.text(mon, i, f' S/. {mon:,.2f}', va='center', fontsize=8, fontweight='bold', color='#0F172A')

            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['left'].set_color('#E2E8F0')
            self.ax.spines['bottom'].set_color('#E2E8F0')

            self.figure.tight_layout()
            if self._canvas_alive():
                self.canvas.draw()
        except Exception as e:
            logger.error("[TopProductsRanking] Error: %s", e)
            self._render_empty_state("No se pudo cargar el ranking")

    def on_pick_product(self, event):
        if not HAS_MPL:
            return
        try:
            if event.inaxes == self.ax and event.xdata is not None:
                pass
        except Exception as e:
            print(f"[on_pick_product] Error: {e}")
