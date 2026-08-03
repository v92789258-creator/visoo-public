import os
import shutil
import datetime
import time
import pathlib
import requests
import json
from urllib.parse import quote_plus

# Deshabilitar warnings de PIL sobre mÃ³dulos faltantes
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Deshabilitar intentos de carga de plugins PIL opcionales
try:
    from PIL import ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except:
    pass

from PyQt5 import QtWidgets, QtCore, QtGui, sip
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout, QLineEdit,
    QPushButton, QScrollArea, QTableWidget, QHeaderView, QMessageBox,
    QAbstractItemView, QHBoxLayout, QFileDialog, QTabWidget,
    QDialog, QTableWidgetItem, QComboBox, QListWidget, QStackedWidget,
    QButtonGroup, QFrame, QSizePolicy, QSpinBox, QDateEdit, QInputDialog,
    QMenu, QToolButton, QCheckBox, QListWidgetItem
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, QDate, QVariantAnimation
from PyQt5.QtGui import QIcon, QColor, QPixmap, QPainter
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtSvg import QSvgRenderer
from gui.widgets.product_card import ProductCard
from gui.components.animated_loader import AnimatedLoaderButton, LoaderWorker
from .materials_page import MaterialsPage
from .sizes_page import SizesPage
from .lens_types_page import LensTypesPage
from utils.barcode_scanner import BarcodeLineEdit

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent

def _is_qt_object_alive(obj) -> bool:
    try:
        return obj is not None and not sip.isdeleted(obj)
    except Exception:
        return False

def _safe_print(message: str) -> None:
    """Imprime sin romperse si el encoding de la consola no soporta Unicode."""
    try:
        print(message)
    except Exception:
        pass


def _is_alive_widget_attr(owner, attr_name: str) -> bool:
    try:
        widget = getattr(owner, attr_name, None)
        return _is_qt_object_alive(widget)
    except Exception:
        return False

# Importar diÃ¡logos y utilidades
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from gui.dialogs.product_dialog_new import OpticalProductDialog
from gui.dialogs.product_migration_dialog import ProductMigrationDialog
from gui.dialogs.category_manager_dialog import CategoryManagerDialog
from gui.dialogs.brand_manager_dialog import BrandManagerDialog
from .sales_page import SalesHistoryPage
import os
import shutil
import json
import datetime
import pathlib
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout, QLineEdit,
    QPushButton, QScrollArea, QTableWidget, QHeaderView, QMessageBox,
    QAbstractItemView, QHBoxLayout, QFileDialog, QTabWidget,
    QDialog, QTableWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets, QtCore, QtGui
# --- AGREGAR ESTO EN LOS IMPORTS (ARRIBA DEL TODO) ---
from utils.sync_manager import restore_products_from_cloud, get_sync_manager

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent

from utils.file_handler import (
    cargar_productos, cargar_productos_dashboard, guardar_productos, agregar_producto, cargar_kardex, guardar_kardex,
    cargar_ventas, guardar_ventas, open_pdf_with_chrome,
    cargar_pacientes, guardar_pacientes,
    set_active_branch_context, clear_active_branch_context, get_active_branch_context, get_effective_branch_context,
    get_productos_mysql_migration_info,
)
from utils.inventory_smart_control import analyze_inventory_control_from_cloud

# Ã°Å¸Å¡â‚¬ OPTIMIZACIÃƒâ€œN: Importar optimizador de C++ para bÃºsqueda ultrarrÃ¡pida
try:
    from utils.inventory_optimizer_cpp import get_optimizer as get_inventory_optimizer
    HAS_INVENTORY_OPTIMIZER = True
except ImportError:
    HAS_INVENTORY_OPTIMIZER = False
    get_inventory_optimizer = None

def create_save_svg():
    """Crea un SVG de save (diskette)."""
    svg_code = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
    <rect x="2" y="2" width="20" height="20" rx="2" fill="transparent" stroke="#191919" stroke-width="2"/>
    <rect x="2" y="2" width="20" height="6" rx="1" fill="#191919"/>
    <circle cx="17" cy="17" r="4" fill="transparent" stroke="#191919" stroke-width="1.5"/>
    <rect x="2" y="10" width="12" height="10" fill="transparent" stroke="#191919" stroke-width="0.5"/>
    </svg>'''
    pixmap = QtGui.QPixmap(24, 24)
    pixmap.fill(QtCore.Qt.transparent)
    svg_renderer = QSvgRenderer(svg_code.encode())
    painter = QPainter(pixmap)
    svg_renderer.render(painter)
    painter.end()
    return QtGui.QIcon(pixmap)

def create_check_svg():
    """Crea un SVG de check (tilde)."""
    svg_code = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
    <circle cx="12" cy="12" r="10" fill="transparent" stroke="#191919" stroke-width="2"/>
    <polyline points="8,12 11,15 16,8" fill="none" stroke="#191919" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    pixmap = QtGui.QPixmap(24, 24)
    pixmap.fill(QtCore.Qt.transparent)
    svg_renderer = QSvgRenderer(svg_code.encode())
    painter = QPainter(pixmap)
    svg_renderer.render(painter)
    painter.end()
    return QtGui.QIcon(pixmap)

def create_loader_svg():
    """Crea un SVG de loader circular animado."""
    svg_code = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">
    <circle cx="25" cy="25" r="20" fill="none" stroke="#E0E0E0" stroke-width="3"/>
    <path d="M 45 25 A 20 20 0 0 1 25 5" fill="none" stroke="#1976D2" stroke-width="3" stroke-linecap="round">
        <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="1s" repeatCount="indefinite"/>
    </path>
    </svg>'''
    pixmap = QtGui.QPixmap(100, 100)
    pixmap.fill(QtCore.Qt.transparent)
    svg_renderer = QSvgRenderer(svg_code.encode())
    painter = QPainter(pixmap)
    svg_renderer.render(painter)
    painter.end()
    return pixmap

# Ã°Å¸Å¡â‚¬ OPTIMIZACIÃƒâ€œN: Worker thread para cargar productos sin bloquear UI
class ProductLoaderThread(QThread):
    """Carga productos en background sin bloquear la UI."""
    finished = pyqtSignal(list)  # Emite lista de productos
    error = pyqtSignal(str)      # Emite mensaje de error
    
    def __init__(self, username):
        super().__init__()
        self.username = username
    
    def run(self):
        try:
            productos = cargar_productos(self.username)
            self.finished.emit(productos if productos else [])
        except Exception as e:
            self.error.emit(f"Error cargando productos: {str(e)}")
            self.finished.emit([])

# Ã°Å¸Å¡â‚¬ STREAMING: Worker para cargar productos por chunks
class ProductStreamerThread(QThread):
    """Carga productos en chunks/streaming para renderizado incremental."""
    chunk_ready = pyqtSignal(list)  # Emite chunk de productos
    finished = pyqtSignal()          # SeÃ±al cuando termina
    error = pyqtSignal(str)          # SeÃ±al de error
    
    def __init__(self, username, chunk_size=50):
        super().__init__()
        self.username = username
        self.chunk_size = chunk_size
    
    def run(self):
        try:
            productos = cargar_productos(self.username)
            
            if not productos:
                print(f"Ã¢â€žÂ¹Ã¯Â¸Â  No hay productos para {self.username}")
                self.finished.emit()
                return
            
            # Emitir en chunks de N productos
            total = len(productos)
            for i in range(0, total, self.chunk_size):
                chunk = productos[i:i + self.chunk_size]
                self.chunk_ready.emit(chunk)
                # PequeÃ±o delay para permitir que la UI se actualice
                self.msleep(30)
            
            # Ã¢Å¡Â Ã¯Â¸Â NO imprimir aquÃ­ - se imprime en el callback _on_streaming_finished
            self.finished.emit()
        except Exception as e:
            print(f"Ã¢ÂÅ’ Error en streaming de inventario: {e}")
            self.error.emit(f"Error cargando productos: {str(e)}")

class InventoryInsightsThread(QThread):
    """Analiza control inteligente leyendo datasets cloud por HTTP."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, username, branch_code=""):
        super().__init__()
        self.username = username
        self.branch_code = str(branch_code or "").strip().upper()

    def run(self):
        try:
            result = analyze_inventory_control_from_cloud(
                username=self.username,
                branch_code=self.branch_code,
            )
            self.finished.emit(result if isinstance(result, dict) else {})
        except Exception as e:
            self.error.emit(str(e))


class ClickableInfoLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        try:
            if event.button() == QtCore.Qt.LeftButton:
                self.clicked.emit()
        except Exception:
            pass
        super().mousePressEvent(event)


class InventorySkeletonGrid(QtWidgets.QWidget):
    """Loader esquelético con el mismo layout base del ProductCard real."""

    def __init__(self, title="Cargando inventario", subtitle="Preparando productos...", cards_count=6, columns=3):
        super().__init__()
        self._pulse_value = 0.0
        self._placeholders = []
        self._meta_lines = []
        self._title = str(title or "Cargando inventario")
        self._subtitle = str(subtitle or "Preparando productos...")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        cards_host = QWidget()
        cards_grid = QGridLayout(cards_host)
        cards_grid.setContentsMargins(0, 0, 0, 0)
        cards_grid.setHorizontalSpacing(20)
        cards_grid.setVerticalSpacing(20)
        cards_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        total_cards = max(1, int(cards_count or 6))
        total_columns = max(1, int(columns or 3))
        for index in range(total_cards):
            card, meta_line = self._build_placeholder_card()
            self._placeholders.append(card)
            self._meta_lines.append(meta_line)
            cards_grid.addWidget(card, index // total_columns, index % total_columns)

        layout.addWidget(cards_host)

        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(900)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._on_anim_value_changed)
        self._apply_skeleton_style()
        self.anim.start()

    def _build_placeholder_card(self):
        wrapper = QWidget()
        wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        wrapper.setMinimumWidth(0)

        main = QVBoxLayout(wrapper)
        main.setContentsMargins(4, 4, 4, 4)

        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 22))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        img_box = QFrame()
        img_box.setObjectName("img_box")
        img_box.setFixedHeight(160)
        img_layout = QVBoxLayout(img_box)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setAlignment(Qt.AlignCenter)

        image_block = QFrame()
        image_block.setObjectName("image_block")
        image_block.setFixedSize(145, 145)
        img_layout.addWidget(image_block)

        info = QFrame()
        info.setObjectName("info_box")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(6, 6, 6, 6)
        info_layout.setSpacing(6)

        title_block = QFrame()
        title_block.setObjectName("title_block")
        title_block.setFixedHeight(18)
        info_layout.addWidget(title_block)

        brand_block = QFrame()
        brand_block.setObjectName("brand_block")
        brand_block.setFixedHeight(14)
        brand_block.setFixedWidth(90)
        info_layout.addWidget(brand_block)

        price_block = QFrame()
        price_block.setObjectName("price_block")
        price_block.setFixedHeight(22)
        price_block.setFixedWidth(84)
        info_layout.addWidget(price_block)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 10, 0, 0)

        stock_group = QWidget()
        stock_group_layout = QHBoxLayout(stock_group)
        stock_group_layout.setContentsMargins(0, 0, 0, 0)
        stock_group_layout.setSpacing(6)

        stock_block = QFrame()
        stock_block.setObjectName("stock_block")
        stock_block.setFixedSize(26, 12)
        stock_group_layout.addWidget(stock_block)

        indicator = QFrame()
        indicator.setObjectName("indicator_block")
        indicator.setFixedSize(8, 8)
        stock_group_layout.addWidget(indicator)
        stock_group_layout.addStretch()

        bottom.addWidget(stock_group)
        bottom.addStretch()

        cart_block = QFrame()
        cart_block.setObjectName("cart_block")
        cart_block.setFixedSize(48, 48)
        bottom.addWidget(cart_block)

        info_layout.addLayout(bottom)
        layout.addWidget(img_box)
        layout.addWidget(info)
        main.addWidget(card)

        meta_line = {
            "title": title_block,
            "brand": brand_block,
            "price": price_block,
            "stock": stock_block,
            "indicator": indicator,
            "cart": cart_block,
            "image": image_block,
            "img_box": img_box,
            "card": card,
        }
        return wrapper, meta_line

    def set_loading_text(self, title="", subtitle=""):
        self._title = str(title or "Cargando inventario")
        self._subtitle = str(subtitle or "Preparando productos...")

    def _on_anim_value_changed(self, value):
        try:
            self._pulse_value = float(value or 0.0)
        except Exception:
            self._pulse_value = 0.0
        self._apply_skeleton_style()

    def _apply_skeleton_style(self):
        block_tone = 226 + int(14 * self._pulse_value)
        img_tone = 238 + int(8 * self._pulse_value)
        block_bg = f"rgb({block_tone},{block_tone},{block_tone})"
        image_bg = f"rgb({img_tone},{img_tone},{img_tone})"
        for card, meta in zip(self._placeholders, self._meta_lines):
            card.setStyleSheet(
                f"""
                QFrame#card {{
                    background: #fff;
                    border-radius: 10px;
                    border: 1px solid #e4e4e4;
                }}
                QFrame#img_box {{
                    background: #f2f2f2;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }}
                QFrame#image_block {{
                    background: {image_bg};
                    border-radius: 6px;
                    border: none;
                }}
                QFrame#title_block {{
                    background: {block_bg};
                    border-radius: 5px;
                    border: none;
                }}
                QFrame#brand_block, QFrame#price_block, QFrame#stock_block {{
                    background: {block_bg};
                    border-radius: 4px;
                    border: none;
                }}
                QFrame#indicator_block {{
                    background: {block_bg};
                    border-radius: 4px;
                    border: none;
                }}
                QFrame#cart_block {{
                    background: #191919;
                    border-radius: 24px;
                    border: none;
                }}
                """
            )


class WebScraperThread(QThread):
    """Thread para buscar productos en opticaperu.com usando la API REST de WooCommerce."""
    finished = pyqtSignal(list)  # Lista de productos encontrados
    error = pyqtSignal(str)       # Mensaje de error
    
    def __init__(self, search_term):
        super().__init__()
        self.search_term = search_term
    
    def run(self):
        try:
            # Usar la API REST de WooCommerce en lugar de web scraping
            termino_encoded = quote_plus(self.search_term)
            url = f"https://opticaperu.com/wp-json/wc/store/v1/products?search={termino_encoded}&per_page=100"
            
            # Headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Realizar solicitud
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parsear JSON
            productos_api = response.json()
            
            if not productos_api:
                self.error.emit("No se encontraron productos con ese tÃ©rmino de bÃºsqueda.")
                return
            
            productos = []
            
            for prod in productos_api:
                try:
                    nombre = prod.get('name', 'Producto sin nombre')
                    
                    # Obtener precio desde el objeto 'prices'
                    prices_obj = prod.get('prices', {})
                    if isinstance(prices_obj, dict):
                        precio_actual = prices_obj.get('sale_price', prices_obj.get('regular_price', 'N/A'))
                        precio_original = prices_obj.get('regular_price', precio_actual)
                        currency_symbol = prices_obj.get('currency_symbol', 'S/')
                    else:
                        precio_actual = 'N/A'
                        precio_original = 'N/A'
                        currency_symbol = 'S/'
                    
                    # Convertir a string con formato
                    if precio_actual != 'N/A':
                        precio_actual_str = f"{currency_symbol}{precio_actual}"
                    else:
                        precio_actual_str = 'N/A'
                    
                    if precio_original != 'N/A':
                        precio_original_str = f"{currency_symbol}{precio_original}"
                    else:
                        precio_original_str = 'N/A'
                    
                    # Calcular descuento si hay
                    descuento = ""
                    try:
                        if precio_actual != 'N/A' and precio_original != 'N/A':
                            p_actual = float(str(precio_actual))
                            p_original = float(str(precio_original))
                            if p_actual < p_original:
                                desc_pct = ((p_original - p_actual) / p_original) * 100
                                descuento = f"-{int(desc_pct)}%"
                    except:
                        pass
                    
                    # Link
                    link = prod.get('permalink', '#')
                    
                    # Imagen
                    images = prod.get('images', [])
                    imagen = images[0].get('src', '') if images and isinstance(images, list) else ''
                    
                    # Marca (obtener de brands si existe)
                    marca = "Ãƒâ€œptica PerÃº"
                    brands = prod.get('brands', [])
                    if brands and isinstance(brands, list) and len(brands) > 0:
                        marca = brands[0].get('name', 'Ãƒâ€œptica PerÃº')
                    
                    productos.append({
                        'nombre': nombre,
                        'marca': marca,
                        'precio_actual': precio_actual_str,
                        'precio_original': precio_original_str,
                        'descuento': descuento,
                        'link': link,
                        'imagen': imagen,
                        'fuente': 'opticaperu.com'
                    })
                except Exception as e:
                    print(f"Error procesando producto: {e}")
                    continue
            
            if productos:
                self.finished.emit(productos)
            else:
                self.error.emit("No se pudieron procesar los productos encontrados.")
                
        except requests.exceptions.Timeout:
            self.error.emit("Ã¢ÂÂ±Ã¯Â¸Â Tiempo de conexiÃ³n agotado. Intenta de nuevo.")
        except requests.exceptions.ConnectionError:
            self.error.emit("Ã°Å¸Å’Â Error de conexiÃ³n. Verifica tu conexiÃ³n a internet.")
        except json.JSONDecodeError:
            self.error.emit("Ã¢ÂÅ’ Error: La API no devolviÃ³ datos vÃ¡lidos.")
        except Exception as e:
            self.error.emit(f"Ã¢ÂÅ’ Error en la bÃºsqueda: {str(e)}")

class CombinedWebScraperThread(QThread):
    """Thread para buscar en mÃºltiples fuentes simultÃ¡neamente."""
    finished = pyqtSignal(list)  # Lista de productos encontrados combinados
    error = pyqtSignal(str)       # Mensaje de error
    
    def __init__(self, search_term):
        super().__init__()
        self.search_term = search_term
    
    def run(self):
        try:
            termino_encoded = quote_plus(self.search_term)
            
            # Busquedas globales xd
            urls = [
                ("woocommerce", f"https://opticaperu.com/wp-json/wc/store/v1/products?search={termino_encoded}&per_page=40"),
                ("woocommerce", f"https://sferaoptical.com/wp-json/wc/store/v1/products?search={termino_encoded}&per_page=40"),
                ("shopify", "https://www.visioncenter.com.pe/products.json"),
                ("shopify", "https://www.optilens.pe/products.json")
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Guardar productos por fuente para intercalarlos
            productos_por_fuente = {}
            
            # Buscar en cada fuente
            for tipo_api, url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    # Determinar fuente
                    if "opticaperu" in url:
                        fuente = "opticaperu.com"
                    elif "sferaoptical" in url:
                        fuente = "sferaoptical.com"
                    elif "visioncenter" in url:
                        fuente = "visioncenter.com.pe"
                    else:
                        fuente = "Desconocido"
                    
                    productos_por_fuente[fuente] = []
                    
                    if tipo_api == "woocommerce":
                        productos_api = response.json()
                        
                        for prod in productos_api:
                            try:
                                nombre = prod.get('name', 'Producto sin nombre')
                                
                                # Obtener precio desde el objeto 'prices'
                                prices_obj = prod.get('prices', {})
                                if isinstance(prices_obj, dict):
                                    precio_actual = prices_obj.get('sale_price', prices_obj.get('regular_price', 'N/A'))
                                    precio_original = prices_obj.get('regular_price', precio_actual)
                                    currency_symbol = prices_obj.get('currency_symbol', 'S/')
                                else:
                                    precio_actual = 'N/A'
                                    precio_original = 'N/A'
                                    currency_symbol = 'S/'
                                
                                # Convertir a string con formato
                                if precio_actual != 'N/A':
                                    precio_actual_str = f"{currency_symbol}{precio_actual}"
                                else:
                                    precio_actual_str = 'N/A'
                                
                                if precio_original != 'N/A':
                                    precio_original_str = f"{currency_symbol}{precio_original}"
                                else:
                                    precio_original_str = 'N/A'
                                
                                # Calcular descuento si hay
                                descuento = ""
                                try:
                                    if precio_actual != 'N/A' and precio_original != 'N/A':
                                        p_actual = float(str(precio_actual))
                                        p_original = float(str(precio_original))
                                        if p_actual < p_original:
                                            desc_pct = ((p_original - p_actual) / p_original) * 100
                                            descuento = f"-{int(desc_pct)}%"
                                except:
                                    pass
                                
                                # Link
                                link = prod.get('permalink', '#')
                                
                                # Imagen
                                images = prod.get('images', [])
                                imagen = images[0].get('src', '') if images and isinstance(images, list) else ''
                                
                                # Marca
                                marca = fuente.split('.')[0].capitalize()
                                brands = prod.get('brands', [])
                                if brands and isinstance(brands, list) and len(brands) > 0:
                                    marca = brands[0].get('name', marca)
                                
                                productos_por_fuente[fuente].append({
                                    'nombre': nombre,
                                    'marca': marca,
                                    'precio_actual': precio_actual_str,
                                    'precio_original': precio_original_str,
                                    'descuento': descuento,
                                    'link': link,
                                    'imagen': imagen,
                                    'fuente': fuente
                                })
                            except Exception as e:
                                print(f"Error procesando producto: {e}")
                                continue
                    
                    elif tipo_api == "shopify":
                        data = response.json()
                        productos_api = data.get('products', [])
                        
                        # Filtrar por tÃ©rmino de bÃºsqueda
                        for prod in productos_api:
                            try:
                                nombre = prod.get('title', 'Producto sin nombre')
                                
                                # Buscar coincidencia con tÃ©rmino
                                if termino_encoded.lower() not in nombre.lower().replace('+', ' '):
                                    continue
                                
                                # Obtener precio
                                variants = prod.get('variants', [])
                                if variants and len(variants) > 0:
                                    variant = variants[0]
                                    precio_actual = variant.get('price', 'N/A')
                                    compare_price = variant.get('compare_at_price', precio_actual)
                                else:
                                    precio_actual = 'N/A'
                                    compare_price = 'N/A'
                                
                                # Formatear precios
                                if precio_actual != 'N/A':
                                    precio_actual_str = f"S/{precio_actual}"
                                else:
                                    precio_actual_str = 'N/A'
                                
                                if compare_price and compare_price != 'N/A':
                                    precio_original_str = f"S/{compare_price}"
                                else:
                                    precio_original_str = precio_actual_str
                                
                                # Calcular descuento
                                descuento = ""
                                try:
                                    if precio_actual != 'N/A' and compare_price:
                                        p_actual = float(str(precio_actual))
                                        p_original = float(str(compare_price))
                                        if p_actual < p_original:
                                            desc_pct = ((p_original - p_actual) / p_original) * 100
                                            descuento = f"-{int(desc_pct)}%"
                                except:
                                    pass
                                
                                # Link (usando handle)
                                handle = prod.get('handle', '')
                                link = f"https://www.visioncenter.com.pe/products/{handle}" if handle else '#'
                                
                                # Imagen
                                images = prod.get('images', [])
                                imagen = images[0].get('src', '') if images and len(images) > 0 else ''
                                
                                # Marca (vendor)
                                marca = prod.get('vendor', 'Vision Center')
                                
                                productos_por_fuente[fuente].append({
                                    'nombre': nombre,
                                    'marca': marca,
                                    'precio_actual': precio_actual_str,
                                    'precio_original': precio_original_str,
                                    'descuento': descuento,
                                    'link': link,
                                    'imagen': imagen,
                                    'fuente': fuente
                                })
                            except Exception as e:
                                print(f"Error procesando producto Shopify: {e}")
                                continue
                
                except requests.exceptions.Timeout:
                    pass  # Continuar con otras fuentes
                except requests.exceptions.ConnectionError:
                    pass  # Continuar con otras fuentes
                except Exception as e:
                    print(f"Error en bÃºsqueda de {url}: {str(e)}")
                    pass  # Continuar con otras fuentes
            
            # Intercalar productos de todas las fuentes
            todos_productos = []
            max_productos = max([len(prods) for prods in productos_por_fuente.values()]) if productos_por_fuente else 0
            
            fuentes_orden = ['opticaperu.com', 'sferaoptical.com', 'visioncenter.com.pe']
            
            for i in range(max_productos):
                for fuente in fuentes_orden:
                    if fuente in productos_por_fuente and i < len(productos_por_fuente[fuente]):
                        todos_productos.append(productos_por_fuente[fuente][i])
            
            if todos_productos:
                self.finished.emit(todos_productos)
            else:
                self.error.emit(f"No se encontraron productos con '{self.search_term}' en ninguna fuente.")
                
        except Exception as e:
            self.error.emit(f"Ã¢ÂÅ’ Error en la bÃºsqueda: {str(e)}")

class ImageLoaderThread(QThread):
    """Thread para descargar imÃ¡genes sin bloquear la UI."""
    image_loaded = pyqtSignal(QPixmap)  # Emite la imagen cargada
    
    def __init__(self, image_url, max_width=180):
        super().__init__()
        self.image_url = image_url
        self.max_width = max_width
    
    def run(self):
        try:
            if not self.image_url:
                self.image_loaded.emit(QPixmap())
                return
            
            # Intentar descargar con reintentos
            max_intentos = 2
            for intento in range(max_intentos):
                try:
                    # Timeout de 5 segundos con reintentos
                    response = requests.get(self.image_url, timeout=5, stream=True, allow_redirects=True)
                    if response.status_code == 200:
                        # Limitar tamaÃ±o de descarga a 1MB
                        content = response.content[:1024*1024]  # MÃ¡ximo 1MB
                        
                        pixmap = QPixmap()
                        pixmap.loadFromData(content)
                        
                        if not pixmap.isNull():
                            # Reducir tamaÃ±o significativamente (100 pÃ­xeles de ancho)
                            pixmap = pixmap.scaledToWidth(100, Qt.FastTransformation)
                            
                            # Crear pixmap comprimido
                            compressed_pixmap = QPixmap(pixmap.size())
                            compressed_pixmap.fill(QtCore.Qt.white)
                            
                            painter = QtGui.QPainter(compressed_pixmap)
                            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)
                            painter.drawPixmap(0, 0, pixmap)
                            painter.end()
                            
                            self.image_loaded.emit(compressed_pixmap)
                            return
                        else:
                            # Si falla primer intento, reintentar
                            if intento < max_intentos - 1:
                                continue
                            else:
                                self.image_loaded.emit(QPixmap())
                                return
                    else:
                        self.image_loaded.emit(QPixmap())
                        return
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                    if intento < max_intentos - 1:
                        continue
                    else:
                        self.image_loaded.emit(QPixmap())
                        return
            
            self.image_loaded.emit(QPixmap())
        except Exception as e:
            # Sin prints para no bloquear la ejecuciÃ³n
            self.image_loaded.emit(QPixmap())

class CopyProductThread(QThread):
    """Thread para copiar producto a inventario sin bloquear UI."""
    finished = pyqtSignal(bool, str)  # (success, mensaje)
    
    def __init__(self, username, producto):
        super().__init__()
        self.username = username
        self.producto = producto
    
    def run(self):
        try:
            nombre = self.producto.get('nombre', '')
            marca = self.producto.get('marca', '')
            imagen_url = self.producto.get('imagen', '')
            
            if not nombre:
                self.finished.emit(False, "El producto no tiene nombre.")
                return
            
            # Extraer precio
            precio_str = self.producto.get('precio_actual', '0')
            try:
                precio_limpio = precio_str.replace('S/', '').replace(',', '.').strip()
                costo = float(precio_limpio)
            except (ValueError, AttributeError):
                costo = 0.0
            
            venta = costo
            
            # Cargar productos
            productos = cargar_productos(self.username)
            
            # Verificar duplicados
            if any(p.get('nombre', '').lower() == nombre.lower() for p in productos):
                self.finished.emit(False, f"El producto '{nombre}' ya existe en el inventario.")
                return
            
            # Descargar imagen
            image_path = None
            if imagen_url:
                try:
                    img_dir = os.path.join("VISO", self.username, "product_images")
                    os.makedirs(img_dir, exist_ok=True)
                    
                    response = requests.get(imagen_url, timeout=5)
                    if response.status_code == 200:
                        import hashlib
                        hash_name = hashlib.md5(nombre.encode()).hexdigest()[:8]
                        img_filename = f"{hash_name}_{nombre.replace(' ', '_')[:20]}.jpg"
                        img_path = os.path.join(img_dir, img_filename)
                        
                        with open(img_path, 'wb') as f:
                            f.write(response.content)
                        
                        image_path = img_path
                except Exception as e:
                    print(f"Error descargando imagen: {e}")
            
            # Crear producto
            nuevo_producto = {
                'nombre': nombre,
                'marca': marca,
                'costo': costo,
                'venta': venta,
                'stock': 0,
                'categoria': '',
                'seccion': '',
                'material': '',
                'image_path': image_path,
                'created_at': datetime.datetime.now().isoformat(),
                'fuente_web': self.producto.get('link', '')
            }
            
            if not agregar_producto(self.username, nuevo_producto):
                self.finished.emit(False, f"No se pudo agregar '{nombre}' (duplicado o error de guardado).")
                return
            
            self._log_audit('crear', f"Producto creado: {nombre}")
            
            # Agregar al kardex
            try:
                # AquÃ­ se usa una referencia global a la funciÃ³n - necesitamos pasar username
                from utils.file_handler import cargar_kardex, guardar_kardex
                kardex = cargar_kardex(self.username)
                kardex.append({
                    'tipo': 'Entrada',
                    'producto': nombre,
                    'cantidad': 0,
                    'precio': costo,
                    'fecha': datetime.datetime.now().isoformat()
                })
                guardar_kardex(self.username, kardex)
            except Exception as e:
                print(f"Error al agregar al kardex: {e}")
            
            mensaje = f"Producto '{nombre}' agregado al inventario.\n\nCosto: S/{costo:.2f}\nStock: 0\nImagen: {'Ã¢Å“â€œ Guardada' if image_path else 'Ã¢Å“â€” No disponible'}"
            self.finished.emit(True, mensaje)
            
        except Exception as e:
            self.finished.emit(False, f"Error al copiar producto: {str(e)}")

class AnimatedLoaderThread(QThread):
    """Thread que anima un loader circular."""
    update_frame = pyqtSignal(int)  # Emite el frame actual (0-7)
    
    def __init__(self):
        super().__init__()
        self.is_running = True
    
    def run(self):
        frame = 0
        while self.is_running:
            self.update_frame.emit(frame)
            frame = (frame + 1) % 8
            self.msleep(100)
    
    def stop(self):
        self.is_running = False


class ProductEditorDialog(QDialog):
    """DiÃ¡logo modal para crear/editar un producto fuera de la vista principal.

    Usa su propia lÃ³gica de subida de imagen y guarda usando las utilidades
    de `utils.file_handler`. Al guardar, actualiza la galerÃ­a llamando a
    `parent_page.update_inventory_gallery()` y registra entrada en kardex
    cuando se crea un producto nuevo.
    """
    def __init__(self, parent_page, producto=None):
        super().__init__(parent_page)
        self.parent_page = parent_page
        self.username = getattr(parent_page, 'username', None)
        self.producto_original = producto
        self.current_image_path = None

        self.setWindowTitle("Editor de Producto")
        self.setModal(True)
        self._build_ui()

        if producto:
            # poblar campos con datos existentes
            self.name_entry.setText(producto.get('nombre', ''))
            self.costo_entry.setText(str(producto.get('costo', '')))
            self.venta_entry.setText(str(producto.get('venta', '')))
            self.stock_entry.setText(str(producto.get('stock', '')))
            self.material_entry.setText(producto.get('material', ''))
            self.marca_entry.setText(producto.get('marca', ''))
            seccion_actual = str(producto.get('seccion') or producto.get('categoria') or '').strip()
            if seccion_actual:
                seccion_index = self.seccion_combo.findData(seccion_actual)
                if seccion_index < 0:
                    self.seccion_combo.addItem(seccion_actual, seccion_actual)
                    seccion_index = self.seccion_combo.findData(seccion_actual)
                if seccion_index >= 0:
                    self.seccion_combo.setCurrentIndex(seccion_index)
            self.current_image_path = producto.get('image_path')
            if self.current_image_path:
                self.image_label.setText(os.path.basename(self.current_image_path))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QGridLayout()

        self.name_entry = QLineEdit(); self.name_entry.setPlaceholderText('Nombre')
        self.costo_entry = QLineEdit(); self.costo_entry.setPlaceholderText('Costo')
        self.venta_entry = QLineEdit(); self.venta_entry.setPlaceholderText('Venta')
        self.stock_entry = QLineEdit(); self.stock_entry.setPlaceholderText('Stock')
        self.material_entry = QLineEdit(); self.material_entry.setPlaceholderText('Material (opcional)')
        self.marca_entry = QLineEdit(); self.marca_entry.setPlaceholderText('Marca (opcional)')
        self.seccion_combo = QComboBox()
        self._reload_sections()

        form.addWidget(QLabel('Nombre:'), 0, 0); form.addWidget(self.name_entry, 0, 1)
        form.addWidget(QLabel('Costo:'), 1, 0); form.addWidget(self.costo_entry, 1, 1)
        form.addWidget(QLabel('Venta:'), 2, 0); form.addWidget(self.venta_entry, 2, 1)
        form.addWidget(QLabel('Stock:'), 3, 0); form.addWidget(self.stock_entry, 3, 1)
        form.addWidget(QLabel('Material:'), 4, 0); form.addWidget(self.material_entry, 4, 1)
        form.addWidget(QLabel('Marca:'), 5, 0); form.addWidget(self.marca_entry, 5, 1)
        form.addWidget(QLabel('Seccion:'), 6, 0); form.addWidget(self.seccion_combo, 6, 1)

        # imagen
        self.image_label = QLabel('Sin imagen seleccionada')
        btn_image = QPushButton('Subir imagen')
        btn_image.clicked.connect(self._upload_image)
        form.addWidget(QLabel('Imagen:'), 7, 0); form.addWidget(self.image_label, 7, 1); form.addWidget(btn_image, 7, 2)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_save = QPushButton('Guardar')
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton('Cancelar')
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_save); btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def _reload_sections(self):
        """Carga secciones (categorias) para asignar al producto."""
        default_sections = [
            "Monturas",
            "Lunas",
            "Lentes de Contacto",
            "Gafas de Sol",
            "Accesorios",
            "Liquidos de Limpieza",
        ]
        sections = []
        try:
            file_path = os.path.join("VISO", "data", "categories.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                if isinstance(loaded, list):
                    sections = [str(s).strip() for s in loaded if str(s).strip()]
        except Exception:
            sections = []

        if not sections:
            sections = default_sections

        self.seccion_combo.clear()
        self.seccion_combo.addItem("Sin seccion", "")
        for section in sorted(set(sections), key=lambda x: x.lower()):
            self.seccion_combo.addItem(section, section)

    def _upload_image(self):
        dlg = QFileDialog(self)
        dlg.setNameFilter('Images (*.png *.jpg *.jpeg *.bmp *.gif)')
        if dlg.exec_() == QDialog.Accepted:
            src = dlg.selectedFiles()[0]
            images_dir = os.path.join(os.getcwd(), 'images')
            os.makedirs(images_dir, exist_ok=True)
            dst = os.path.join(images_dir, os.path.basename(src))
            try:
                shutil.copy(src, dst)
                self.current_image_path = dst
                self.image_label.setText(os.path.basename(dst))
                QMessageBox.information(self, 'Éxito', f'Imagen copiada a: {dst}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'No se pudo copiar la imagen: {e}')

    def _save(self):
        try:
            if self.parent_page and hasattr(self.parent_page, "_sync_branch_context_from_parent"):
                self.parent_page._sync_branch_context_from_parent()
        except Exception:
            pass
        # Ã°Å¸â€ºÂ¡Ã¯Â¸Â VERIFICAR PERMISOS antes de guardar
        parent_app = getattr(self.parent_page, 'parent_app', None)
        if parent_app and parent_app.is_helper:
            if self.producto_original:
                # EDITAR
                if not parent_app.puede_hacer_accion('inventario', 'editar'):
                    QMessageBox.warning(
                        self,
                        "Permiso Denegado",
                        "No tienes permiso para editar productos."
                    )
                    return
            else:
                # CREAR
                if not parent_app.puede_hacer_accion('inventario', 'crear'):
                    QMessageBox.warning(
                        self,
                        "Permiso Denegado",
                        "No tienes permiso para crear productos."
                    )
                    return
        
        nombre = self.name_entry.text().strip()
        if not nombre:
            QMessageBox.critical(self, 'Error', "El campo 'Nombre' es obligatorio.")
            return

        try:
            # Limpieza robusta de montos (maneja comas y símbolos)
            def _clean_num(txt):
                if not txt: return "0"
                return str(txt).strip().replace("S/.", "").replace("S/", "").replace(",", "").replace(" ", "")

            costo = float(_clean_num(self.costo_entry.text()))
            venta = float(_clean_num(self.venta_entry.text()))
            stock_txt = _clean_num(self.stock_entry.text())
            stock = int(float(stock_txt)) if stock_txt else 0
        except (ValueError, TypeError):
            QMessageBox.critical(self, 'Error', 'Costo, Venta y Stock deben ser números válidos.')
            return

        seccion = str(self.seccion_combo.currentData() or '').strip()
        productos = cargar_productos(self.username) or []

        if self.producto_original:
            # edicion: buscar por nombre original
            for i, p in enumerate(productos):
                if p.get('nombre') == self.producto_original.get('nombre'):
                    productos[i].update({
                        'nombre': nombre,
                        'costo': costo,
                        'venta': venta,
                        'stock': stock,
                        'material': self.material_entry.text().strip(),
                        'marca': self.marca_entry.text().strip(),
                        'categoria': seccion,
                        'seccion': seccion,
                        'image_path': self.current_image_path or p.get('image_path')
                    })
                    break
            guardar_productos(self.username, productos)
        else:
            # creacion: evitar duplicados
            if any(p.get('nombre') == nombre for p in productos):
                QMessageBox.information(self, 'Error', 'El producto ya existe. Usa la edicion para actualizarlo.')
                return
            nuevo_producto = {
                'nombre': nombre,
                'costo': costo,
                'venta': venta,
                'stock': stock,
                'image_path': self.current_image_path,
                'material': self.material_entry.text().strip(),
                'marca': self.marca_entry.text().strip(),
                'categoria': seccion,
                'seccion': seccion,
                'created_at': datetime.datetime.now().isoformat()
            }
            if not agregar_producto(self.username, nuevo_producto):
                QMessageBox.information(self, 'Error', 'No se pudo guardar el producto (duplicado o error de archivo).')
                return
            # agregar kardex
            try:
                self.parent_page.add_kardex_entry('Entrada', nombre, stock, costo)
            except Exception:
                pass
        
        try:
            if self.producto_original:
                self.parent_page._log_audit('editar', f"Producto editado: {nombre}")
            else:
                self.parent_page._log_audit('crear', f"Producto creado: {nombre}")
        except Exception:
            pass
        
        try:
            self.parent_page.update_inventory_gallery()
        except Exception:
            pass
        QMessageBox.information(self, 'Éxito', 'Producto guardado correctamente.')
        self.accept()



class InventoryPage(QWidget):
    # Signal para actualizar UI desde thread background
    productos_cargados = pyqtSignal(list)
    refresh_cargado = pyqtSignal(dict)
    sync_feedback_requested = pyqtSignal(str, str, str)
    sync_button_state_requested = pyqtSignal(bool, str)
    migration_dialog_finish_requested = pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = parent.username if parent else None
        self.helper_name = getattr(parent, 'helper_name', None) if parent else None
        self.user_id = parent.user_id if parent else None
        self.current_image_path = None
        self.config_file = os.path.join("VISO", "data", "inventory_preferences.json")
        self.grid_columns = 4
        
        # Conectar signal para actualizar UI desde thread
        self.productos_cargados.connect(self._on_productos_cargados)
        self.refresh_cargado.connect(self._on_refresh_cargado)
        self.sync_feedback_requested.connect(self._show_sync_feedback)
        self.sync_button_state_requested.connect(self._apply_sync_button_state)
        self.migration_dialog_finish_requested.connect(self._finish_product_migration_dialog)
        self._image_loaders = []
        self._copy_threads = []
        self._loader_threads = []
        self._refresh_in_progress = False
        self._initial_data_loading = False
        self._loader_timer = None
        self._loader_status_label = None
        self._loader_step = 0
        self._insights_thread = None
        self._insights_request_id = 0
        self._smart_inventory_signature = None
        self._running_inventory_signature = None
        self._queued_insights_refresh = False
        self._smart_focus_targets = {}
        self._smart_focus_active_key = ""
        self._smart_focus_active_title = ""
        self._smart_status_default_text = "Analiza demanda, stock y recetas usando tus propios datos."
        self._smart_source_default_text = "Fuente: analisis local"
        self._manual_sync_in_progress = False
        self._pending_product_creation = None
        self._pending_product_skeleton_anim = None
        self._migration_dialog = None
        self._migration_dialog_expected = False
        
        # Variables de paginaciÃ³n
        self.current_page = 0
        self.products_per_page = 20
        self.total_products = []
        
        # Streaming
        self.streamer_thread = None
        self.all_productos = []
        self._inventory_filter_timer = None
        self._inventory_filter_loader_timer = None
        self._inventory_filter_loader_step = 0
        self._inventory_filter_delay_ms = 900
        
        # Carrito
        self.cart_items = {}
        self.cart_table = None
        
        # Paciente actual (para registrar ventas asociadas a un paciente especÃ­fico)
        self.current_paciente_dni = None
        self.current_paciente_nombre = None
        self.optometra = ""

        # Asegurar contexto de sucursal correcto antes de cualquier lectura/escritura de inventario.
        self._sync_branch_context_from_parent()

        self.setObjectName("MainContent")

        # InicializaciÃƒÆ’Ã‚Â³n diferida para evitar congelar la UI al navegar a Inventario.
        # Construir UI pesada en el siguiente tick del event loop.
        self._deferred_initialized = False
        self._setup_shell_ui()
        try:
            QTimer.singleShot(20, self._deferred_init)
        except Exception:
            self._deferred_init()
        return
        
        # =========================================================================
        # Ã°Å¸â€ºÂ¡Ã¯Â¸Â INICIO SEGURO: CORRECCIÃƒâ€œN DEL BUG DE BORRADO DE BD
        # =========================================================================
        print("[INIT] Iniciando InventoryPage de forma segura...")
        
        # 1. Mostrar UI instantÃ¡neamente (sin bloquear)
        self._show_inventory_loader(
            title="Cargando inventario",
            subtitle="Sincronizando con la nube. Esto puede tardar unos segundos."
        )
        # Cargar en background con thread
        import threading
        load_thread = threading.Thread(target=self._background_load, daemon=True)
        load_thread.start()

    def _show_sync_feedback(self, level: str, title: str, message: str):
        level_norm = str(level or "").strip().lower()
        box_fn = QMessageBox.information
        if level_norm == "warning":
            box_fn = QMessageBox.warning
        elif level_norm in ("error", "critical"):
            box_fn = QMessageBox.critical

        try:
            box_fn(self, str(title or "Sincronizacion"), str(message or ""))
        except Exception:
            pass

    def _apply_sync_button_state(self, enabled: bool, text: str = ""):
        button_text = str(text or ("Sincronizar Ahora" if enabled else "Sincronizando..."))
        self._manual_sync_in_progress = not bool(enabled)
        for attr in ("btn_sync", "btn_sync_side"):
            btn = getattr(self, attr, None)
            if btn is None:
                continue
            try:
                btn.setEnabled(bool(enabled))
                btn.setText(button_text)
            except Exception:
                pass

    def _setup_shell_ui(self):
        """UI mÃƒÂ­nima para mostrar rÃƒÂ¡pido al entrar a Inventario."""
        try:
            layout = self.layout()
            if layout is None:
                layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            shell = QWidget()
            shell_layout = QVBoxLayout(shell)
            shell_layout.setAlignment(Qt.AlignCenter)
            shell_layout.setContentsMargins(24, 24, 24, 24)

            title = QLabel("Cargando Inventario...")
            title.setStyleSheet("font-size: 18px; font-weight: 700; color: #172b4d;")
            subtitle = QLabel("Preparando interfaz y sincronización en segundo plano.")
            subtitle.setStyleSheet("font-size: 12px; color: #5e6c84;")
            subtitle.setWordWrap(True)
            subtitle.setAlignment(Qt.AlignCenter)

            shell_layout.addWidget(title, alignment=Qt.AlignCenter)
            shell_layout.addWidget(subtitle, alignment=Qt.AlignCenter)

            self._shell_container = shell
            layout.addWidget(shell)
        except Exception:
            pass

    def _deferred_init(self):
        """Construye UI pesada y arranca carga en background sin bloquear navegaciÃƒÆ’Ã‚Â³n."""
        if getattr(self, "_deferred_initialized", False):
            return
        self._deferred_initialized = True

        # Remover placeholder si existe
        try:
            shell = getattr(self, "_shell_container", None)
            if shell is not None:
                layout = self.layout()
                if layout is not None:
                    layout.removeWidget(shell)
                shell.deleteLater()
            self._shell_container = None
        except Exception:
            pass

        try:
            print("[INIT] Iniciando InventoryPage (deferred)...", flush=True)
        except Exception:
            pass

        try:
            self.setup_ui()
        except Exception as e:
            _safe_print(f"[INIT] Error en setup_ui Inventario: {e}")

        try:
            self.load_view_preference()
        except Exception:
            pass
        try:
            self.load_grid_preferences()
        except Exception:
            pass

        try:
            self._show_inventory_loader(
                title="Cargando inventario",
                subtitle="Sincronizando con la nube. Esto puede tardar unos segundos."
            )
        except Exception:
            pass

        try:
            self._maybe_show_product_migration_dialog()
        except Exception:
            pass

        try:
            import threading
            load_thread = threading.Thread(target=self._background_load, daemon=True)
            load_thread.start()
        except Exception:
            pass

    def _sync_branch_context_from_parent(self):
        """
        Mantiene sincronizado el contexto activo de sucursal con MainWindow.
        Esto evita subir inventario al codigo fallback MADRE-* cuando hay sucursal seleccionada.
        """
        try:
            if not self.username:
                return
            parent = self.parent_app
            code = str(getattr(parent, "selected_branch_code", "") or "").strip().upper() if parent else ""
            label = str(getattr(parent, "selected_branch_label", "") or "").strip() if parent else ""

            # Fallback para modo trabajador: si no hay sucursal seleccionada en el parent,
            # usar el codigo vinculado en config_dispositivo.json.
            worker_code = ""
            worker_label = ""
            try:
                cfg_path = BASE_DIR / "VISO" / str(self.username) / "data" / "config_dispositivo.json"
                if cfg_path.exists():
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    if isinstance(cfg, dict):
                        role = str(cfg.get("tipo_dispositivo", "")).strip().lower()
                        if role == "trabajador":
                            worker_code = str(
                                cfg.get("codigo_dispositivo_hijo")
                                or cfg.get("codigo_dispositivo_trabajador")
                                or cfg.get("codigo_dispositivo")
                                or ""
                            ).strip().upper()
                            name = str(cfg.get("dispositivo_hijo_nombre", "Sucursal")).strip() or "Sucursal"
                            city = str(cfg.get("dispositivo_hijo_ciudad", "")).strip()
                            worker_label = f"{name} - {city} ({worker_code})" if city else f"{name} ({worker_code})"
            except Exception:
                worker_code = ""
                worker_label = ""

            if not code and worker_code:
                code = worker_code
                label = worker_label

            if code:
                set_active_branch_context(self.username, code, label)
            else:
                clear_active_branch_context(self.username)
        except Exception as e:
            _safe_print(f"[BRANCH] No se pudo sincronizar contexto de sucursal: {e}")
    
    def _background_load(self):
        """Carga los productos en background sin bloquear la UI."""
        if not _is_qt_object_alive(self):
            return
        self._initial_data_loading = True
        try:
            # Ejecutar carga segura (Maneja el caso de products.json perdido)
            self._safe_initial_load()
            
            # Emitir signal para actualizar UI en el thread principal
            if _is_qt_object_alive(self):
                self.productos_cargados.emit(self.all_productos)
            
            # Iniciar workers secundarios (pero NO sincronizaciÃ³n automÃ¡tica destructiva)
            if _is_qt_object_alive(self):
                self._init_refresh_workers()
        except Exception as e:
            if _is_qt_object_alive(self):
                self._initial_data_loading = False
                try:
                    self.migration_dialog_finish_requested.emit(False, f"No se pudo completar la migracion: {e}")
                except Exception:
                    pass
            _safe_print(f"Error en carga background: {e}")
            import traceback
            traceback.print_exc()

    def _on_productos_cargados(self, productos):
        """Callback que se ejecuta en el thread principal cuando los productos se cargan."""
        self._initial_data_loading = False
        self._stop_inventory_loader_animation()
        if getattr(self, "_migration_dialog_expected", False):
            try:
                migration_info = get_productos_mysql_migration_info(self.username)
            except Exception:
                migration_info = {}

            if isinstance(migration_info, dict) and migration_info.get("needs_migration"):
                self._finish_product_migration_dialog(
                    False,
                    "No se completo la migracion a la base de datos. El inventario sigue saliendo del respaldo local."
                )
            else:
                self._finish_product_migration_dialog(
                    True,
                    f"Tu inventario ya esta listo en la base de datos. Productos cargados: {len(productos)}."
                )
        self.all_productos = productos
        self.total_products = productos
        self._refresh_side_section_combo()
        self._refresh_side_brand_combo()
        self.update_inventory_gallery()
        self.refresh_smart_inventory_panel(force=True)
        print(f"[UI] GalerÃ­a actualizada con {len(productos)} productos")
    
    def _log_audit(self, action, details):
        """Registra una acciÃ³n en auditorÃ­a."""
        try:
            if hasattr(self.parent_app, 'app_instance') and hasattr(self.parent_app.app_instance, 'audit_manager'):
                audit_mgr = self.parent_app.app_instance.audit_manager
                audit_mgr.log_action(
                    user_id=self.user_id,
                    username=self.username,
                    helper_name=self.helper_name,
                    action=action,
                    module='inventario',
                    details=details
                )
        except Exception as e:
            pass

    def _maybe_show_product_migration_dialog(self):
        info = get_productos_mysql_migration_info(self.username)
        if not isinstance(info, dict) or not info.get("needs_migration"):
            self._migration_dialog_expected = False
            return

        self._migration_dialog_expected = True
        if self._migration_dialog is not None:
            return

        dialog = ProductMigrationDialog(
            estimated_seconds=int(info.get("estimated_seconds", 12) or 12),
            product_count=int(info.get("legacy_count", 0) or 0),
            parent=self,
        )
        branch_label = str(info.get("branch_label", "") or "").strip()
        branch_code = str(info.get("branch_code", "") or "").strip()
        skipped_count = int(info.get("skipped_count", 0) or 0)
        if branch_label or branch_code:
            target = branch_label or branch_code
            dialog.meta_label.setText(
                f"Productos detectados: {int(info.get('legacy_count', 0) or 0)} | Destino: {target}"
            )
        if skipped_count > 0:
            dialog.note_label.setText(
                f"Se omitiran {skipped_count} registro(s) invalidos antes de subir a la base de datos."
            )
            dialog.note_label.setVisible(True)
        dialog.show()
        self._migration_dialog = dialog

    def _finish_product_migration_dialog(self, success=True, message=""):
        dialog = getattr(self, "_migration_dialog", None)
        if dialog is None:
            return
        try:
            dialog.mark_finished(bool(success), str(message or ""))
        except Exception:
            pass

    def set_current_paciente(self, paciente_dni, paciente_nombre, optometra=""):
        """Establece el paciente actual para asociar las ventas a ese paciente."""
        self.current_paciente_dni = paciente_dni
        self.current_paciente_nombre = paciente_nombre
        self.optometra = optometra
        _safe_print(f"[INVENTORY] Paciente actual establecido: {paciente_nombre} (DNI: {paciente_dni})")

    def _safe_initial_load(self):
        """
        MÃƒâ€°TODO CRÃTICO: Gestiona la carga inicial para evitar borrar la BD remota.
        
        LÃ³gica:
                    1. ¿Es un ayudante? ¿Tiene permiso "ver" en inventario?
           NO -> No cargar datos. La pÃ¡gina estarÃ¡ vacÃ­a.
           SI -> Continuar con carga normal.
                    2. ¿Existe products.json?
           NO -> Â¡PELIGRO! PodrÃ­a haberse borrado. Intentar RESTAURAR desde nube (Download).
           SI -> Cargar normal.
        """
        try:
            # Ã°Å¸â€ºÂ¡Ã¯Â¸Â VERIFICACIÃƒâ€œN DE PERMISOS: Solo cargar si puede ver
            if self.parent_app and self.parent_app.is_helper:
                from utils.helpers_manager import tiene_accion_permitida
                
                # Obtener jefe del ayudante actual
                username_ayudante = self.parent_app.helper_name
                username_jefe = self.parent_app.username
                
                if not tiene_accion_permitida(username_jefe, username_ayudante, 'inventario', 'ver'):
                    _safe_print(f"[PERMISOS] Ayudante '{username_ayudante}' no tiene permiso 'ver' en inventario")
                    self.all_productos = []
                    # Mostrar mensaje en la UI
                    self._mostrar_sin_permisos("Sin permiso para ver inventario")
                    return
            
            from utils.file_handler import (
                cargar_productos,
                cargar_productos_dashboard,
                guardar_productos,
                get_active_branch_context,
            )

            # POLITICA REMOTO-FIRST:
            # - Cargar desde internet primero
            # - Usar local solo si falla internet/API
            _safe_print("[CARGA] Intentando cargar inventario desde internet (remoto-first)...")
            productos_remotos = restore_products_from_cloud(self.username)
            productos_locales = cargar_productos(self.username) or []
            try:
                ctx = get_effective_branch_context(self.username) or {}
                branch_code = str(ctx.get("code", "") or "").strip().upper()
                vista_global = not bool(branch_code)
            except Exception:
                vista_global = True

            # En vista global (Todas las sucursales), si el archivo local esta vacio,
            # usar consolidado del branch_cache.
            if vista_global and not productos_locales:
                productos_locales = cargar_productos_dashboard(self.username) or []

            # Si el inventario esta precargado localmente pero remoto viene vacio,
            # iniciar subida automatica (en background) para que el sistema quede "casi en linea".
            try:
                rem_list = productos_remotos if isinstance(productos_remotos, list) else None
                if rem_list is not None and len(rem_list) == 0 and productos_locales:
                    def _seed_bg():
                        try:
                            from utils.sync_manager import auto_seed_inventario_precargado
                            if vista_global:
                                auto_seed_inventario_precargado(self.username)
                            else:
                                auto_seed_inventario_precargado(self.username, branch_codes=[branch_code])
                        except Exception:
                            pass
                    import threading
                    threading.Thread(target=_seed_bg, daemon=True).start()
            except Exception:
                pass

            if productos_remotos is not None:
                # La API respondio (puede venir vacia para usuarios/sucursales nuevas)
                rem = productos_remotos if isinstance(productos_remotos, list) else []
                # Si remoto viene vacio, preferir el respaldo local para no mostrar 0 productos.
                self.all_productos = rem if len(rem) > 0 else productos_locales
                _safe_print(f"[CARGA] Inventario remoto cargado: {len(rem)} productos.")

                # Mantener respaldo local actualizado solo cuando hay datos remotos
                if isinstance(rem, list) and len(rem) > 0:
                    guardar_productos(self.username, rem, queue_sync=False)
                    _safe_print("[BACKUP] Respaldo local actualizado desde nube.")
                else:
                    _safe_print("[BACKUP] Remoto vacio; se conserva respaldo local existente.")
            else:
                _safe_print("[CARGA] No se pudo cargar desde internet. Usando respaldo local.")
                self.all_productos = productos_locales

            # 3. Validar consistencia
            if not self.all_productos:
                _safe_print("[AVISO] El inventario esta vacio (Local y Remoto).")
            else:
                _safe_print(f"[LISTO] Inventario cargado: {len(self.all_productos)} productos.")

            # 4. NO actualizar UI aquÃ­ - se hace desde el signal en el thread principal
            self.total_products = self.all_productos
            
        except Exception as e:
            _safe_print(f"[ERROR] Fallo la carga segura: {e}")
            import traceback
            traceback.print_exc()

    def _init_refresh_workers(self):
        """
        Inicializa workers secundarios.
        YA NO hace una carga forzada del servidor que sobrescribÃ­a cosas.
        """
        # Solo necesitamos asegurarnos que el sync manager estÃ© listo, 
        # pero NO disparamos sincronizaciones automÃ¡ticas al inicio.
        pass
    
    def _mostrar_sin_permisos(self, mensaje: str):
        """Muestra un mensaje cuando el ayudante no tiene permisos para ver."""
        # Crear un widget con mensaje
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setAlignment(Qt.AlignCenter)
        
        # ?cono
        icono_label = QLabel("!")
        icono_label.setStyleSheet("font-size: 48px;")
        icono_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icono_label)
        
        # Mensaje
        msg_label = QLabel(mensaje)
        msg_label.setStyleSheet("""
            font-size: 16px;
            color: #666;
            font-weight: bold;
        """)
        msg_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg_label)
        
        # Submensaje
        submsg_label = QLabel("Contacta al administrador para solicitar permisos")
        submsg_label.setStyleSheet("color: #999; font-size: 12px;")
        submsg_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(submsg_label)
        
        layout.addStretch()
        
        # Reemplazar la galerÃ­a principal
        main_col = self.findChild(QWidget)
        if main_col:
            # Limpiar layout anterior
            while main_col.layout() and main_col.layout().count():
                main_col.layout().takeAt(0)
            main_col.layout().addWidget(contenedor)

    def _load_from_server_once(self):
        """
        Intenta descargar inventario remoto UNA SOLA VEZ al entrar al Inventario.
        - Se ejecuta en background para no bloquear la UI.
        - Si el servidor devuelve productos (lista no vacÃ­a) se delega a
          `_on_products_refreshed` para hacer merge y guardar localmente.
        - Si el servidor estÃ¡ vacÃ­o no sobrescribe nada.
        """
        if not self.username:
            return

        def _worker():
            try:
                print("[LOAD_SERVER] Intentando descargar inventario remoto...")
                from utils.sync_manager import get_sync_manager
                sync_mgr = get_sync_manager()

                # Determinar usuario_id
                from utils.file_handler import cargar_usuarios
                usuarios = cargar_usuarios() or {}
                usuario_id = None
                if self.username.isdigit():
                    usuario_id = str(self.username)
                else:
                    for uid, info in usuarios.items():
                        if isinstance(info, dict) and info.get('username') == self.username:
                            usuario_id = str(uid)
                            break

                if not usuario_id:
                    print("[LOAD_SERVER] No se encontrÃ³ usuario_id para descarga remota")
                    return

                productos_remotos = sync_mgr.download_remote_inventory(str(usuario_id))

                if productos_remotos is None:
                    print("[LOAD_SERVER] No fue posible descargar inventario remoto (sin internet o error)")
                    return

                if not productos_remotos:
                    print("[LOAD_SERVER] Ã¢â€žÂ¹Ã¯Â¸Â Servidor vacÃ­o, usando productos locales")
                    try:
                        import time
                        # Guardar respaldo local inmediato (timestamp) por precauciÃ³n
                        from utils.file_handler import guardar_remote_backup, guardar_productos
                        backup_path = guardar_remote_backup(self.username, self.all_productos or [])
                        if backup_path:
                            print(f"[LOAD_SERVER] Ã¢Å¡Â Ã¯Â¸Â Respaldo local creado en: {backup_path}")
                        # Registrar aviso en temp
                        temp_dir = os.path.join('VISO', 'temp')
                        os.makedirs(temp_dir, exist_ok=True)
                        warn_file = os.path.join(temp_dir, f'remote_empty_warning_{int(time.time())}.log')
                        with open(warn_file, 'w', encoding='utf-8') as wf:
                            wf.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Servidor reportÃ³ 0 productos para usuario {usuario_id}\n")
                            wf.write(f"Local products: {len(self.all_productos or [])}\n")
                        print(f"[LOAD_SERVER] Ã¢Å¡Â Ã¯Â¸Â Advertencia registrada en: {warn_file}")
                    except Exception as e:
                        print(f"[LOAD_SERVER] Ã¢Å¡Â Ã¯Â¸Â No se pudo crear respaldo/registro: {e}")
                    return

                # Si hay productos remotos, aplicarlos (merge + guardar)
                print(f"[LOAD_SERVER] Ã¢Å“â€¦ Inventario remoto encontrado: {len(productos_remotos)} productos. Actualizando localmente...")
                try:
                    self._on_products_refreshed(productos_remotos)
                except Exception as e:
                    print(f"[LOAD_SERVER] Error aplicando inventario remoto: {e}")

            except Exception as e:
                print(f"[LOAD_SERVER] ExcepciÃ³n (ignorada): {str(e)}")
                import traceback
                traceback.print_exc()

        import threading
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    # ... (MANTÃƒâ€°N EL RESTO DE TUS MÃƒâ€°TODOS UI: showEvent, setup_ui, etc.) ...

    # ============================
    # UI Principal
    # ============================
    def setup_ui(self):
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout(self)
        try:
            layout.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass

        # Limpiar galer?a anterior
        try:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        except Exception:
            pass

        self.tab_widget = QTabWidget()

        # Construir solo el tab de Inventario al inicio (los demÃ¡s se arman on-demand).
        self.tab_widget.addTab(self.create_inventory_tab(), "Inventario General")

        def _placeholder(text: str):
            w = QWidget()
            l = QVBoxLayout(w)
            l.setAlignment(Qt.AlignCenter)
            lbl = QLabel(str(text or "Cargando..."))
            lbl.setStyleSheet("color:#5e6c84; font-size: 12px;")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            l.addWidget(lbl)
            return w

        # Tabs lazy (evita freeze al entrar a Inventario por construir TODO de golpe)
        self._lazy_tab_builders = {
            1: ("Historial Kardex", self.create_kardex_tab),
            2: ("Historial de Ventas", lambda: SalesHistoryPage(self.parent_app)),
            3: ("ConfiguraciÃ³n del Inventario", self.create_config_tab),
        }
        self._lazy_tabs_built = {0}
        self._lazy_tabs_building = set()
        try:
            self._lazy_tab_builders[3] = ("Configuracion del Inventario", self.create_config_tab)
            QTimer.singleShot(0, self._fix_inventory_config_tab_texts)
        except Exception:
            pass

        self.tab_widget.addTab(_placeholder("Cargando Kardex..."), "Historial Kardex")
        self.tab_widget.addTab(_placeholder("Cargando Historial de Ventas..."), "Historial de Ventas")
        self.tab_widget.addTab(_placeholder("Cargando ConfiguraciÃ³n..."), "ConfiguraciÃ³n del Inventario")

        try:
            self.tab_widget.currentChanged.connect(self._ensure_lazy_tab_built)
        except Exception:
            pass

        layout.addWidget(self.tab_widget)

    def _ensure_lazy_tab_built(self, index: int):
        """Construye el contenido real del tab cuando el usuario lo abre por primera vez."""
        try:
            idx = int(index)
        except Exception:
            return

        built = getattr(self, "_lazy_tabs_built", set()) or set()
        if idx in built:
            return

        building = getattr(self, "_lazy_tabs_building", set()) or set()
        if idx in building:
            return

        builders = getattr(self, "_lazy_tab_builders", {}) or {}
        if idx not in builders:
            return

        title, builder = builders.get(idx)
        building.add(idx)
        self._lazy_tabs_building = building
        try:
            real_widget = builder() if callable(builder) else None
        except Exception as e:
            _safe_print(f"[UI] Error construyendo tab Inventario idx={idx}: {e}")
            real_widget = None

        if real_widget is None:
            try:
                building.discard(idx)
                self._lazy_tabs_building = building
            except Exception:
                pass
            return

        try:
            blocker = QtCore.QSignalBlocker(self.tab_widget)
            try:
                placeholder = self.tab_widget.widget(idx)
                current_idx = int(self.tab_widget.currentIndex() or 0)
                self.tab_widget.removeTab(idx)
                self.tab_widget.insertTab(idx, real_widget, str(title))

                if current_idx >= 0 and current_idx < self.tab_widget.count():
                    self.tab_widget.setCurrentIndex(current_idx if current_idx != idx else idx)
                else:
                    self.tab_widget.setCurrentIndex(min(idx, max(0, self.tab_widget.count() - 1)))

                if placeholder is not None:
                    placeholder.deleteLater()

                built.add(idx)
                self._lazy_tabs_built = built
            finally:
                del blocker
        except Exception as e:
            _safe_print(f"[UI] Error reemplazando placeholder de tab idx={idx}: {e}")
        finally:
            try:
                building.discard(idx)
                self._lazy_tabs_building = building
            except Exception:
                pass

    # ============================
    # PestaÃ±a Inventario
    # ============================
    def create_inventory_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # T?tulo
        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        # T?tulo
        title_label = QLabel("GestiÃ³n de Inventario")
        # font-weight: 300 (thin/light), font-size: 25px
        title_label.setStyleSheet("font-weight: 300; font-size: 25px;")
        title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        header_layout.addWidget(title_label, stretch=1)
        
        
        # Contenedor principal para la columna central (header + galerÃ­a)
        main_col = QWidget()
        main_col_layout = QVBoxLayout(main_col)
        main_col_layout.setContentsMargins(0, 0, 0, 0)
        main_col_layout.addWidget(header_row)

    # (Se removiÃ³ un contenedor de galerÃ­a duplicado aquÃ­)

        # Botones de cambio de vista
        view_controls = QWidget()
        view_layout = QHBoxLayout(view_controls)
        view_layout.setContentsMargins(0, 0, 0, 0)
        
        self.view_button_group = QButtonGroup(self)
        
        self.grid_button = QPushButton()
        self.grid_button.setIcon(QIcon(os.path.join(BASE_DIR, "images", "grid.svg")))
        self.grid_button.setIconSize(QSize(24, 24))
        self.grid_button.setCheckable(True)
        self.grid_button.setChecked(True)
        self.grid_button.setToolTip("Vista de cuadrÃ­cula")
        # Hacer el botÃ³n de vista sin borde y plano
        self.grid_button.setFlat(True)
        self.grid_button.setStyleSheet("""
            QPushButton { border: none; background: transparent; padding: 6px; }
            QPushButton:checked { background: rgba(0,0,0,0.06); border-radius: 6px; }
        """)
        
        self.list_button = QPushButton()
        self.list_button.setIcon(QIcon(os.path.join(BASE_DIR, "images", "list.svg")))
        self.list_button.setIconSize(QSize(24, 24))
        self.list_button.setCheckable(True)
        self.list_button.setToolTip("Vista de lista")
        # Hacer el botÃ³n de vista sin borde y plano
        self.list_button.setFlat(True)
        self.list_button.setStyleSheet("""
            QPushButton { border: none; background: transparent; padding: 6px; }
            QPushButton:checked { background: rgba(0,0,0,0.06); border-radius: 6px; }
        """)
        
        self.view_button_group.addButton(self.grid_button, 0)
        self.view_button_group.addButton(self.list_button, 1)
        
        view_layout.addWidget(self.grid_button)
        view_layout.addWidget(self.list_button)
        
        header_layout.addWidget(view_controls)
        # Helper local para cargar iconos con fallback si el archivo no existe
        def _get_icon(icon_name, fallback='search.svg'):
            try:
                icon_path = os.path.join(BASE_DIR, 'gui', 'icons', icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
                fallback_path = os.path.join(BASE_DIR, 'gui', 'icons', fallback)
                if os.path.exists(fallback_path):
                    return QIcon(fallback_path)
            except Exception:
                pass
            return QIcon()
        
        btn_open_new = QPushButton("Agregar producto")
        btn_open_new.setObjectName("primaryButton")
        btn_open_new.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                padding: 8px 14px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        btn_open_new.clicked.connect(lambda: self.open_product_dialog())
        header_layout.addWidget(btn_open_new)
        
        # BotÃ³n de sincronizaciÃ³n manual
        self.btn_sync = QPushButton("Sincronizar Ahora")
        self.btn_sync.setObjectName("secondaryButton")
        self.btn_sync.setStyleSheet("""
            QPushButton {
                background-color: #2a8659;
                color: white;
                border: 1px solid #2a8659;
                padding: 8px 14px;
                border-radius: 0px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1f5f3f;
                border: 1px solid #1f5f3f;
            }
            QPushButton:pressed {
                background-color: #0d3820;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
                border: 1px solid #cccccc;
            }
        """)
        self.btn_sync.clicked.connect(self._on_sync_now_clicked)
        header_layout.addWidget(self.btn_sync)
        self.btn_sync.setVisible(True)
        self.btn_sync.setEnabled(True)

        self.btn_inventory_more = QToolButton()
        self.btn_inventory_more.setText("⋯")
        self.btn_inventory_more.setToolTip("Más opciones")
        self.btn_inventory_more.setCursor(Qt.PointingHandCursor)
        self.btn_inventory_more.setPopupMode(QToolButton.InstantPopup)
        self.btn_inventory_more.setStyleSheet("""
            QToolButton {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #D1D5DB;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 20px;
                font-weight: 700;
            }
            QToolButton:hover {
                background-color: #F3F4F6;
                border: 1px solid #9CA3AF;
            }
            QToolButton::menu-indicator {
                image: none;
                width: 0px;
            }
        """)
        self.inventory_actions_menu = QMenu(self.btn_inventory_more)
        self.inventory_actions_menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #EFF6FF;
                color: #1D4ED8;
            }
        """)
        self.inventory_actions_menu.addAction("Imprimir inventario", self._open_inventory_pdf_customizer)
        self.inventory_actions_menu.addAction("Exportar a Excel", self._open_inventory_excel_customizer)
        self.btn_inventory_more.setMenu(self.inventory_actions_menu)
        header_layout.addWidget(self.btn_inventory_more)
        # Contenedor para las vistas
        self.views_stack = QStackedWidget()
        
        # Vista de cuadrÃ­cula con el nuevo diseÃ±o de tarjetas
        self.product_gallery_area = QScrollArea()
        self.product_gallery_area.setWidgetResizable(True)
        self.product_gallery_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                width: 10px;
                margin: 0px;
                background-color: #F0F0F0;
            }
            QScrollBar::handle:vertical {
                background-color: #CDCDCD;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #BBBBBB;
            }
        """)
        
        self.products_container = QWidget()
        self.product_gallery_widget = QWidget(self.products_container)
        self.products_grid = QGridLayout(self.product_gallery_widget)
        self.products_grid.setContentsMargins(20, 20, 20, 20)
        index_offset = 0
        pending_product = getattr(self, "_pending_product_creation", None)
        if self.current_page == 0 and isinstance(pending_product, dict):
            skeleton_card = self._create_product_creation_skeleton_widget(
                str(pending_product.get("nombre", "") or "").strip()
            )
            self.products_grid.addWidget(skeleton_card, 0, 0)
            index_offset = 1
        index_offset = 0
        pending_product = getattr(self, "_pending_product_creation", None)
        if self.current_page == 0 and isinstance(pending_product, dict):
            skeleton_card = self._create_product_creation_skeleton_widget(
                str(pending_product.get("nombre", "") or "").strip()
            )
            self.products_grid.addWidget(skeleton_card, 0, 0)
            index_offset = 1

        index_offset = 0
        pending_product = getattr(self, "_pending_product_creation", None)
        if self.current_page == 0 and isinstance(pending_product, dict):
            skeleton_card = self._create_product_creation_skeleton_widget(
                str(pending_product.get("nombre", "") or "").strip()
            )
            self.products_grid.addWidget(skeleton_card, 0, 0)
            index_offset = 1
        pending_product = getattr(self, "_pending_product_creation", None)
        if self.current_page == 0 and isinstance(pending_product, dict):
            skeleton_card = self._create_product_creation_skeleton_widget(
                str(pending_product.get("nombre", "") or "").strip()
            )
            self.products_grid.addWidget(skeleton_card, 0, 0)
            index_offset = 1
        pending_product = getattr(self, "_pending_product_creation", None)
        if self.current_page == 0 and isinstance(pending_product, dict):
            skeleton_card = self._create_product_creation_skeleton_widget(
                str(pending_product.get("nombre", "") or "").strip()
            )
            self.products_grid.addWidget(skeleton_card, 0, 0)
            index_offset = 1
        self.products_grid.setSpacing(20)
        self.products_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # Configure the container layout
        container_layout = QVBoxLayout(self.products_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.product_gallery_widget)
        
        self.product_gallery_area.setWidget(self.products_container)
        self.views_stack.addWidget(self.product_gallery_area)
        
        # Vista de tabla
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(7)
        self.product_table.setHorizontalHeaderLabels(["Codigo / Nombre", "Costo", "Venta", "Stock", "Material", "Marca", "Acciones"])
        
        # Configurar estilos de la tabla
        self.product_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                gridline-color: #E8E8E8;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                background-color: #FFFFFF;
                color: #424242;
                font-size: 12px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1565C0;
            }
            QTableWidget::item:hover {
                background-color: #F5F5F5;
            }
            QHeaderView::section {
                background-color: #191919;
                color: #FFFFFF;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QHeaderView::section:hover {
                background-color: #2D2D2D;
            }
        """)
        
        header = self.product_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setMinimumHeight(45)
        header.setDefaultAlignment(Qt.AlignCenter)
        
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setRowHeight(0, 40)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.setShowGrid(False)
        self.product_table.setColumnWidth(0, 200)
        
        self.views_stack.addWidget(self.product_table)
        
        main_col_layout.addWidget(self.views_stack)
        
        # Conectar los botones de vista
        self.view_button_group.buttonClicked.connect(self.change_view)

        # Panel lateral con herramientas (solo en esta pestaÃ±a)
        side_col = QGroupBox("Herramientas")
        # Dar un ancho mÃ­nimo para evitar que el panel colapse en pantallas pequeÃ±as
        side_col.setMinimumWidth(320)
        side_col.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px;
            }
            QGroupBox::title {
                background-color: white;
                padding: 4px 8px;
                color: #1976D2;
                font-weight: bold;
                font-size: 13px;
            }
            QLabel {
                color: #424242;
                font-weight: 500;
                margin-top: 6px;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: #F8F9FA;
                margin-bottom: 6px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                background: white;
            }
            QComboBox {
                padding: 6px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: #F8F9FA;
            }
            QComboBox:hover {
                border-color: #BBDEFB;
            }
            QComboBox:focus {
                border-color: #2196F3;
                background: white;
            }
            QPushButton {
                padding: 6px 10px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
                border: none;
            }
        """)
        side_layout = QVBoxLayout(side_col)
        side_layout.setSpacing(6)
        side_layout.setContentsMargins(12, 8, 12, 12)

        # SecciÃ³n de bÃºsqueda
        search_section = QFrame()
        search_layout = QVBoxLayout(search_section)
        search_layout.setSpacing(4)
        search_layout.setContentsMargins(0, 0, 0, 8)
        
        # T?tulo
        search_label = QLabel("Buscar producto")
        search_label.setStyleSheet("QLabel { padding-left: 5px; }")

        # ?cono
        self.side_search_entry = BarcodeLineEdit()
        self.side_search_entry.setPlaceholderText("Nombre, marca o cÃ³digo...")
        self.side_search_entry.barcode_captured.connect(self.on_inventory_barcode_scanned)
        # Conectar tambiÃ©n para bÃºsqueda mientras se escribe
        self.side_search_entry.textChanged.connect(self.on_inventory_search_text_changed)
        try:
            search_icon = _get_icon("search.svg", fallback='search.svg')
        # ?cono
            self.side_search_entry.addAction(search_icon, QLineEdit.LeadingPosition)
            # Ajustar padding para que el placeholder/text no quede encima del icono
            self.side_search_entry.setStyleSheet("QLineEdit { padding-left: 24px; }")
        except Exception:
            pass
        self.side_search_entry.setMinimumHeight(32)
        self.side_search_entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Iniciar modo de escaneo
        self.side_search_entry.start_scanning()
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.side_search_entry)
        self.inventory_filter_status_label = QLabel("")
        self.inventory_filter_status_label.setMinimumHeight(16)
        self.inventory_filter_status_label.setStyleSheet("color: #2563EB; font-size: 10px; font-weight: 600; padding-left: 5px;")
        search_layout.addWidget(self.inventory_filter_status_label)

        section_section = QFrame()
        section_layout = QVBoxLayout(section_section)
        section_layout.setSpacing(4)
        section_layout.setContentsMargins(0, 0, 0, 8)

        section_label = QLabel("Seccion")
        section_label.setStyleSheet("QLabel { padding-left: 5px; }")

        self.side_section_combo = QComboBox()
        self.side_section_combo.setMinimumHeight(34)
        self.side_section_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._refresh_side_section_combo()

        section_layout.addWidget(section_label)
        section_layout.addWidget(self.side_section_combo)

        brand_section = QFrame()
        brand_layout = QVBoxLayout(brand_section)
        brand_layout.setSpacing(4)
        brand_layout.setContentsMargins(0, 0, 0, 8)

        brand_label = QLabel("Marca")
        brand_label.setStyleSheet("QLabel { padding-left: 5px; }")

        self.side_brand_combo = QComboBox()
        self.side_brand_combo.setMinimumHeight(34)
        self.side_brand_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._refresh_side_brand_combo()

        brand_layout.addWidget(brand_label)
        brand_layout.addWidget(self.side_brand_combo)

        # Seccion de ordenamiento
        sort_section = QFrame()
        sort_layout = QVBoxLayout(sort_section)
        sort_layout.setSpacing(4)
        sort_layout.setContentsMargins(0, 0, 0, 8)
        
        sort_label = QLabel("Ordenar por")
        sort_label.setStyleSheet("QLabel { padding-left: 5px; }")

        self.side_sort_combo = QComboBox()
        self.side_sort_combo.addItems(["MÃ¡s nuevo primero", "MÃ¡s viejo primero", "AlfabÃ©tico A-Z"])
        self.side_sort_combo.setCurrentIndex(0)
        self.side_sort_combo.setMinimumHeight(34)
        self.side_sort_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Icono al lado izquierdo del combo (se muestra adjunto)
        sort_icon = _get_icon("sort.svg", fallback='search.svg')
        icon_label = QLabel()
        _pm = sort_icon.pixmap(QSize(16, 16))
        if not _pm.isNull():
            icon_label.setPixmap(_pm)
            icon_label.setContentsMargins(2, 0, 6, 0)

        combo_row = QWidget()
        combo_row_layout = QHBoxLayout(combo_row)
        combo_row_layout.setContentsMargins(0, 0, 0, 0)
        combo_row_layout.setSpacing(4)
        combo_row_layout.addWidget(icon_label)
        combo_row_layout.addWidget(self.side_sort_combo)

        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(combo_row)

        # BotÃ³n aplicar filtros
        btn_apply_filters = QPushButton("Aplicar filtros")
        btn_apply_filters.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                padding: 8px 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        btn_apply_filters.clicked.connect(self.apply_inventory_filters)
        btn_apply_filters.setMinimumHeight(36)
        btn_apply_filters.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Botón actualizar página
        self.btn_refresh = QPushButton("Actualizar Página")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: 1px solid #1976D2;
                padding: 8px 10px;
                border-radius: 0px !important;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
                border: 1px solid #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_inventory_page)
        self.btn_refresh.setMinimumHeight(36)
        self.btn_refresh.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Controles de paginación
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(6)
        pagination_layout.setContentsMargins(0, 8, 0, 8)
        
        self.btn_prev_page = QPushButton("← Anterior")
        self.btn_prev_page.setStyleSheet("""
            QPushButton {
                background-color: #191919;
                color: white;
                border: 1px solid #191919;
                padding: 6px 10px;
                border-radius: 0px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #ffffff;
                color: #191919;
                border: 1px solid #191919;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #999;
                border: 1px solid #E0E0E0;
            }
        """)
        self.btn_prev_page.clicked.connect(self.prev_page)
        self.btn_prev_page.setEnabled(False)
        
        self.pagination_info = QLabel("Página 1")
        self.pagination_info.setStyleSheet("color: #666; font-size: 12px; text-align: center;")
        self.pagination_info.setAlignment(Qt.AlignCenter)
        
        self.btn_next_page = QPushButton("Siguiente →")
        self.btn_next_page.setStyleSheet("""
            QPushButton {
                background-color: #191919;
                color: white;
                border: 1px solid #191919;
                padding: 6px 10px;
                border-radius: 0px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #ffffff;
                color: #191919;
                border: 1px solid #191919;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #999;
                border: 1px solid #E0E0E0;
            }
        """)
        self.btn_next_page.clicked.connect(self.next_page)
        self.btn_next_page.setEnabled(False)
        
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.pagination_info)
        pagination_layout.addWidget(self.btn_next_page)
        
        pagination_widget = QWidget()
        pagination_widget.setLayout(pagination_layout)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #E0E0E0;")

        # Agregar todos los widgets al layout principal
        side_layout.addWidget(search_section)
        side_layout.addWidget(section_section)
        side_layout.addWidget(brand_section)
        side_layout.addWidget(sort_section)
        side_layout.addWidget(btn_apply_filters)
        self.btn_sync_side = QPushButton("Sincronizar Ahora")
        self.btn_sync_side.setObjectName("secondaryButton")
        self.btn_sync_side.setMinimumHeight(36)
        self.btn_sync_side.clicked.connect(self._on_sync_now_clicked)
        side_layout.addWidget(self.btn_sync_side)
        side_layout.addWidget(self.btn_refresh)
        side_layout.addWidget(pagination_widget)
        self.smart_control_panel = self._create_smart_control_panel()
        side_layout.addWidget(self.smart_control_panel)
        side_layout.addWidget(separator)
        
        # ---------- TABLA DEL CARRITO ----------
        cart_label = QLabel("Carrito de Compra")
        cart_label.setStyleSheet("""
            QLabel {
                font-weight: 600;
                font-size: 14px;
                color: #191919;
                padding: 8px 0px 4px 0px;
            }
        """)
        
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(4)
        self.cart_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio", "Total"])
        self.cart_table.setMaximumHeight(200)
        self.cart_table.setMinimumHeight(100)
        self.cart_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f5f5f5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #191919;
                color: white;
                padding: 6px;
                border: none;
                font-weight: 600;
                font-size: 11px;
            }
        """)
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.doubleClicked.connect(self.open_cart_enlarged)  # Doble clic abre ventana ampliada
        self.cart_table.hide()  # Ocultada inicialmente
        
        side_layout.addWidget(cart_label)
        side_layout.addWidget(self.cart_table)

        side_layout.addStretch()

        # Envolver el panel lateral en un QScrollArea para que no se corte en pantallas pequeÃ±as
        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QFrame.NoFrame)
        side_scroll.setWidget(side_col)
        side_scroll.setMinimumWidth(320)

        # Montar columnas en el layout principal
        layout.addWidget(main_col, stretch=3)
        layout.addWidget(side_scroll, stretch=1)

        # Conectar bÃºsqueda en tiempo real y cambios de ordenamiento
        self.side_section_combo.currentTextChanged.connect(self.apply_inventory_filters)
        self.side_brand_combo.currentTextChanged.connect(self.apply_inventory_filters)
        self.side_sort_combo.currentTextChanged.connect(self.apply_inventory_filters)

        # Ã¢Å¡Â Ã¯Â¸Â NO llamar a update_inventory_gallery() aquÃ­ - se carga vÃ­a load_inventory_streaming()
        return tab
        
    def save_view_preference(self, is_grid_view):
        """Guarda la preferencia de vista en un archivo JSON."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            preferences = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    preferences = json.load(f)
            
            if not self.username:
                return
                
            if 'view_preferences' not in preferences:
                preferences['view_preferences'] = {}
            
            preferences['view_preferences'][self.username] = {
                'is_grid_view': is_grid_view
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar preferencia de vista: {str(e)}")
    
    def save_grid_preferences(self):
        """Guarda las preferencias de la cuadrÃ­cula en el archivo JSON."""
        try:
            preferences = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    preferences = json.load(f)
            
            if not self.username:
                return
                
            if 'grid_preferences' not in preferences:
                preferences['grid_preferences'] = {}
            
            preferences['grid_preferences'][self.username] = {
                'columns': self.columns_spin.value()
            }
            
            self.grid_columns = self.columns_spin.value()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, indent=4, ensure_ascii=False)
                
            # Actualizar la vista de productos
            self.update_inventory_gallery()
            
        except Exception as e:
            print(f"Error al guardar preferencias de cuadrÃ­cula: {str(e)}")
    
    def load_grid_preferences(self):
        """Carga las preferencias de la cuadrÃ­cula desde el archivo JSON."""
        try:
            if not os.path.exists(self.config_file) or not self.username:
                return
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
            
            user_preferences = preferences.get('grid_preferences', {}).get(self.username, {})
            self.grid_columns = user_preferences.get('columns', 4)
            
            # Actualizar el spinbox si existe
            if hasattr(self, 'columns_spin'):
                self.columns_spin.setValue(self.grid_columns)
                
        except Exception as e:
            print(f"Error al cargar preferencias de cuadrÃ­cula: {str(e)}")
    
    def load_view_preference(self):
        """Carga la preferencia de vista desde el archivo JSON."""
        try:
            if not os.path.exists(self.config_file) or not self.username:
                return
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
            
            user_preferences = preferences.get('view_preferences', {}).get(self.username, {})
            is_grid_view = user_preferences.get('is_grid_view', True)
            
            if is_grid_view:
                self.grid_button.setChecked(True)
                self.views_stack.setCurrentIndex(0)
            else:
                self.list_button.setChecked(True)
                self.views_stack.setCurrentIndex(1)
        except Exception as e:
            print(f"Error al cargar preferencia de vista: {str(e)}")
    
    def change_view(self, button):
        """Cambia entre vista de cuadrÃ­cula y tabla."""
        if button == self.grid_button:
            self.views_stack.setCurrentIndex(0)
            self.save_view_preference(True)
        else:
            self.views_stack.setCurrentIndex(1)
            self.save_view_preference(False)

    # ============================
    # PestaÃ±a Buscar Producto
    # ============================
    
    def create_search_product_tab(self):
        """Crear la pestaÃ±a de bÃºsqueda web en opticaperu.com como catÃ¡logo visual."""
        search_tab = QWidget()
        layout = QVBoxLayout(search_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # T?tulo
        title_label = QLabel("Búsqueda Global")
        title_label.setStyleSheet("font-weight: 300; font-size: 28px; color: #1976D2;")
        title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        layout.addWidget(title_label)
        
        # T?tulo
        source_label = QLabel("Búsqueda en tiempo real desde opticaperu.com")
        source_label.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(source_label)
        
        # === BARRA DE B?SQUEDA ===
        search_bar_widget = QWidget()
        search_bar_layout = QHBoxLayout(search_bar_widget)
        search_bar_layout.setContentsMargins(0, 0, 0, 0)
        search_bar_layout.setSpacing(10)
        
        self.web_search_input = QLineEdit()
        self.web_search_input.setPlaceholderText("Busca lentes, armazones, marcas, etc...")
        self.web_search_input.setMinimumHeight(45)
        self.web_search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
                background-color: #F8F9FA;
            }
        """)
        self.web_search_input.returnPressed.connect(self.perform_web_search)
        search_bar_layout.addWidget(self.web_search_input)
        
        btn_search_web = QPushButton("Buscar")
        btn_search_web.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        btn_search_web.setMinimumHeight(45)
        btn_search_web.setMaximumWidth(140)
        btn_search_web.clicked.connect(self.perform_web_search)
        search_bar_layout.addWidget(btn_search_web)
        
        layout.addWidget(search_bar_widget)
        
        # === INFORMACIÃƒâ€œN DE RESULTADOS ===
        self.web_search_info_label = QLabel("Ingresa un tÃ©rmino de bÃºsqueda para comenzar")
        self.web_search_info_label.setStyleSheet("color: #666; font-size: 12px; padding: 8px; font-weight: 500;")
        layout.addWidget(self.web_search_info_label)
        
        # === GALERÃA DE PRODUCTOS ===
        gallery_scroll = QScrollArea()
        gallery_scroll.setWidgetResizable(True)
        gallery_scroll.setFrameShape(QFrame.NoFrame)
        gallery_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                width: 10px;
                margin: 0px;
                background-color: #F0F0F0;
            }
            QScrollBar::handle:vertical {
                background-color: #CDCDCD;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #BBBBBB;
            }
        """)
        
        self.web_gallery_container = QWidget()
        self.web_gallery_layout = QGridLayout(self.web_gallery_container)
        self.web_gallery_layout.setSpacing(20)
        self.web_gallery_layout.setContentsMargins(10, 10, 10, 10)
        self.web_gallery_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        gallery_scroll.setWidget(self.web_gallery_container)
        self.web_gallery_scroll = gallery_scroll  # Guardar referencia para scroll
        layout.addWidget(gallery_scroll, stretch=1)
        
        # === CONTROLES DE PAGINACIÃƒâ€œN ===
        pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(pagination_widget)
        pagination_layout.setContentsMargins(0, 10, 0, 10)
        pagination_layout.setSpacing(10)
        
        btn_anterior = QPushButton("← Anterior")
        btn_anterior.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        btn_anterior.setMaximumWidth(120)
        btn_anterior.clicked.connect(self.pagina_anterior)
        pagination_layout.addWidget(btn_anterior)
        
        pagination_layout.addStretch()
        
        btn_siguiente = QPushButton("Siguiente →")
        btn_siguiente.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        btn_siguiente.setMaximumWidth(120)
        btn_siguiente.clicked.connect(self.pagina_siguiente)
        pagination_layout.addWidget(btn_siguiente)
        
        layout.addWidget(pagination_widget)
        
        # Inicializar el thread de bÃºsqueda
        self.web_scraper_thread = None
        self.web_gallery_columns = 3  # NÃºmero de columnas en la galerÃ­a (reducido para ver tarjetas completas)
        
        # Variables de paginaciÃ³n
        self.web_productos_cache = []  # Cache de todos los productos
        self.web_pagina_actual = 0
        self.web_productos_por_pagina = 15
        
        return search_tab
    
    def perform_web_search(self):
        """Realiza la bÃºsqueda en mÃºltiples fuentes simultÃ¡neamente."""
        search_term = self.web_search_input.text().strip()
        
        if not search_term:
            QMessageBox.warning(self, "Búsqueda vacía", "Por favor ingresa un término de búsqueda.")
            return
        
        # Cambiar mensaje a estado de carga
            self.web_search_info_label.setText(f"Buscando '{search_term}' en múltiples fuentes...")
        
        # Limpiar galer?a anterior
        while self.web_gallery_layout.count():
            child = self.web_gallery_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Crear y iniciar el thread de b?squeda combinada
        self.web_scraper_thread = CombinedWebScraperThread(search_term)
        self.web_scraper_thread.finished.connect(self.display_web_results)
        self.web_scraper_thread.error.connect(self.display_web_error)
        self.web_scraper_thread.finished.connect(self.web_scraper_thread.deleteLater)
        self.web_scraper_thread.start()
    
    def _on_image_loaded(self, label, pixmap, imagen_url=None):
        """Callback cuando una imagen finaliz? de cargar."""
        try:
            # Verificar si el widget a?n existe
            if label is None:
                return
            
            # Verificar si el label tiene padre (no fue eliminado)
            if label.parent() is None:
                return
            
            if pixmap.isNull():
                label.setText("Sin imagen")
                label.setStyleSheet("font-size: 48px; color: #CCC;")
            else:
                label.setPixmap(pixmap)
        except RuntimeError:
            # El widget fue eliminado mientras se cargaba la imagen
            pass
        except Exception as e:
            print(f"Error al cargar imagen: {e}")
            pass
        finally:
            # Limpiar threads de imagen finalizados
            if hasattr(self, '_image_loaders'):
                self._image_loaders = [t for t in self._image_loaders if t and t.isRunning()]
    
    def display_web_results(self, productos):
        """Muestra los resultados de la bÃºsqueda web como catÃ¡logo visual con paginaciÃ³n."""
        try:
        # Limpiar galer?a anterior
            if hasattr(self, 'web_scraper_thread') and self.web_scraper_thread and not self.web_scraper_thread.isRunning():
                self.web_scraper_thread.deleteLater()
                self.web_scraper_thread = None
            
            # Guardar en cache y resetear paginaciÃ³n
            self.web_productos_cache = productos
            self.web_pagina_actual = 0
            
            # Mostrar primera pÃ¡gina
            self._show_pagination_page()
            
        except Exception as e:
            self.display_web_error(f"Error mostrando resultados: {str(e)}")
    
    def _show_pagination_page(self):
        """Muestra la pÃ¡gina actual de resultados."""
        try:
            # Detener todos los threads activos (loaders)
            self._stop_loader_threads()
            
        # Limpiar galer?a anterior
            while self.web_gallery_layout.count():
                child = self.web_gallery_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            if not self.web_productos_cache:
                empty_label = QLabel("No se encontraron productos")
                empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
                empty_label.setAlignment(Qt.AlignCenter)
                self.web_gallery_layout.addWidget(empty_label, 0, 0)
                return
            
            # Calcular rango de productos para esta pÃ¡gina
            inicio = self.web_pagina_actual * self.web_productos_por_pagina
            fin = inicio + self.web_productos_por_pagina
            productos_pagina = self.web_productos_cache[inicio:fin]
            
            # Crear tarjetas de productos
            for i, producto in enumerate(productos_pagina):
                row = i // self.web_gallery_columns
                col = i % self.web_gallery_columns
                
                # Crear tarjeta
                card = self.create_web_product_card(producto)
                self.web_gallery_layout.addWidget(card, row, col)
            
            # Agregar stretch al final
            self.web_gallery_layout.addItem(
                QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
                (len(productos_pagina) + self.web_gallery_columns - 1) // self.web_gallery_columns,
                0
            )
            
            # Actualizar informaciÃ³n de paginaciÃ³n
            total_paginas = (len(self.web_productos_cache) + self.web_productos_por_pagina - 1) // self.web_productos_por_pagina
            pagina_mostrada = self.web_pagina_actual + 1
            total_productos = len(self.web_productos_cache)
            
            self.web_search_info_label.setText(
                f"Ã¢Å“â€œ Se encontraron {total_productos} producto(s) | "
                f"PÃ¡gina {pagina_mostrada}/{total_paginas}"
            )
            
        except Exception as e:
            self.web_search_info_label.setText(f"Error al mostrar resultados: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _stop_loader_threads(self):
        """Detiene todos los threads de loader activos."""
        if not _is_qt_object_alive(self):
            return
        try:
            # Detener y limpiar threads de loader
            for thread in list(getattr(self, "_loader_threads", []) or []):
                if thread and thread.isRunning():
                    thread.quit()
                    thread.wait(1000)  # Esperar mÃ¡ximo 1 segundo
            if hasattr(self, "_loader_threads"):
                self._loader_threads.clear()
        except Exception as e:
            print(f"Error al detener loaders: {e}")
    
    def _cleanup_all_threads(self):
        """Limpia todos los threads activos para evitar 'QThread: Destroyed while thread is still running'."""
        if not _is_qt_object_alive(self):
            return
        try:
            # Limpiar threads de copia
            for thread in list(getattr(self, "_copy_threads", []) or []):
                if thread:
                    if thread.isRunning():
                        thread.quit()
                        thread.wait(2000)  # Esperar mÃ¡ximo 2 segundos
                    thread.deleteLater()
            if hasattr(self, "_copy_threads"):
                self._copy_threads.clear()
            
        # Limpiar galer?a anterior
            for thread in list(getattr(self, "_image_loaders", []) or []):
                if thread:
                    if thread.isRunning():
                        thread.quit()
                        thread.wait(2000)
                    thread.deleteLater()
            if hasattr(self, "_image_loaders"):
                self._image_loaders.clear()
            
            # Limpiar threads de loader animado
            self._stop_loader_threads()
            
            # Detener thread de bÃºsqueda web
            if getattr(self, 'web_scraper_thread', None):
                if self.web_scraper_thread.isRunning():
                    self.web_scraper_thread.quit()
                    self.web_scraper_thread.wait(2000)
                self.web_scraper_thread.deleteLater()
                self.web_scraper_thread = None
        except Exception as e:
            print(f"Error al limpiar threads: {e}")
    
    def closeEvent(self, event):
        """Maneja el cierre de la pÃ¡gina limpiando todos los threads."""
        # Limpiar galer?a anterior
        self._cleanup_all_threads()
        
        # Detener workers de auto-refresh de inventario
        try:
            if hasattr(self, 'product_refresh_worker') and self.product_refresh_worker:
                if self.product_refresh_worker.isRunning():
                    self.product_refresh_worker.stop()
                    self.product_refresh_worker.wait()
            
            if hasattr(self, 'inventory_sync_worker') and self.inventory_sync_worker:
                if self.inventory_sync_worker.isRunning():
                    self.inventory_sync_worker.stop()
                    self.inventory_sync_worker.wait()
            if getattr(self, '_insights_thread', None):
                if self._insights_thread.isRunning():
                    self._insights_thread.quit()
                    self._insights_thread.wait(1000)
                self._insights_thread.deleteLater()
                self._insights_thread = None
        except:
            pass
        
        super().closeEvent(event) if hasattr(super(), 'closeEvent') else None
    
    def __del__(self):
        """Destructor para asegurar limpieza de threads."""
        try:
            self._cleanup_all_threads()
        except Exception:
            pass
    
    # ========================================================================
    # AUTO-REFRESH DE INVENTARIO - SincronizaciÃ³n automÃ¡tica sin necesidad
    # de actualizar la app manualmente
    # ========================================================================
    
    def _init_refresh_workers(self):
        """No dispara una segunda carga ni toca la UI desde background."""
        return

    def _on_sync_now_clicked(self):
        """
        Ejecuta sincronizaciÃ³n manual con PROTECCIONES EXTREMAS.
        
        Ã¢Å¡Â Ã¯Â¸Â CRÃTICO: Valida que hay datos locales antes de sincronizar
        para evitar sobrescribir servidor con datos vacÃ­os/corruptos
        
        FLUJO:
        1. Verificar que hay productos en memoria (self.all_productos)
        2. Verificar que hay productos en archivo JSON local
        3. Verificar que no hay DELETE pendientes
        4. Ejecutar sync_manager que limpia DELETE antes de sincronizar
        """
        if not self.username:
            QMessageBox.warning(self, "Error", "Usuario no identificado")
            return

        if getattr(self, "_manual_sync_in_progress", False):
            QMessageBox.information(
                self,
                "Sincronizacion en curso",
                "Ya hay una sincronizacion manual ejecutandose. Espera a que termine para volver a intentarlo.",
            )
            return
        
        # Ã¢Å¡Â Ã¯Â¸Â PROTECCIÃƒâ€œN 1: Verificar que hay datos en MEMORIA
        # En "Todas las sucursales" no hay destino unico para subir inventario.
        # El inventario se sincroniza por sucursal (codigo_dispositivo).
        try:
            self._sync_branch_context_from_parent()
            ctx = get_effective_branch_context(self.username) or {}
            branch_code = str(ctx.get("code", "") or "").strip().upper()
        except Exception:
            branch_code = ""

        is_madre = False
        try:
            parent = self.parent_app
            if parent is not None:
                fn = getattr(parent, "es_dispositivo_madre", None)
                if callable(fn):
                    is_madre = bool(fn())
                else:
                    # Fallback si el parent no expone el metodo.
                    is_madre = str(getattr(parent, "device_role", "")).strip().lower() == "madre"
        except Exception:
            is_madre = False

        if not branch_code and not is_madre:
            QMessageBox.information(
                self,
                "Selecciona una sucursal",
                "Estás en 'Todas las sucursales'.\n\n"
                "La sincronización de inventario es por sucursal.\n"
                "Selecciona una sucursal arriba y vuelve a intentar."
            )
            return

        # Madre sin sucursal seleccionada: el SyncManager resolvera codigo_dispositivo a MADRE-<USER>.
        sync_target_hint = ""
        if not branch_code and is_madre:
            sync_target_hint = "\n\nDestino: Sucursal madre (modo global)."
            try:
                print("[SYNC] Modo madre sin sucursal seleccionada: destino sucursal madre en la nube")
            except Exception:
                pass

        if not self.all_productos or len(self.all_productos) == 0:
            QMessageBox.critical(
                self, 
                "ERROR: No hay productos en memoria",
                "No se puede sincronizar sin datos locales.\n\n"
                "Por favor:\n"
                "1. Cierra esta ventana\n"
                "2. Reabre Inventario\n"
                "3. Espera a que carguen los productos\n"
                "4. Intenta sincronizar de nuevo"
            )
            print("[SYNC_BLOCKED] No hay productos en memoria")
            return
        
        # Ã¢Å¡Â Ã¯Â¸Â PROTECCIÃƒâ€œN 2: Verificar que hay datos en ARCHIVO JSON local
        from utils.file_handler import cargar_productos
        productos_locales = cargar_productos(self.username)
        # DEBUG: Mostrar paths y existencia para diagnosticar casos de 'products.json' vs 'productos.json'
        try:
            from utils.file_handler import get_user_file_path, VISO_DIR
            p1 = get_user_file_path(self.username, 'productos.json')
            p2 = get_user_file_path(self.username, 'products.json')
            print(f"[DEBUG] VISO_DIR: {VISO_DIR} | productos.json exists: {p1.exists()} -> {p1} | products.json exists: {p2.exists()} -> {p2}")
        except Exception:
            pass

        print(f"[DEBUG] Productos en memoria: {len(self.all_productos)} - Productos en archivo local: {len(productos_locales) if productos_locales is not None else 'None'}")
        
        if not productos_locales or len(productos_locales) == 0:
            QMessageBox.critical(
                self, 
                "ADVERTENCIA CRÃTICA DE SEGURIDAD",
                f"El archivo local estÃ¡ VACÃO pero hay {len(self.all_productos)} productos en pantalla.\n\n"
                "Esto indica corrupciÃ³n de datos. No se sincronizarÃ¡.\n\n"
                "Por favor:\n"
                "1. Reporta esto al equipo de soporte\n"
                "2. NO cierres la app\n"
                "3. Los productos en pantalla estÃ¡n protegidos"
            )
            print("[SYNC_BLOCKED] Archivo JSON vacÃ­o pero hay datos en pantalla - CORRUPCIÃƒâ€œN DETECTADA")
            return
        
        # Ã¢Å¡Â Ã¯Â¸Â PROTECCIÃƒâ€œN 3: Verificar que no hay muchos DELETE pendientes
        try:
            from utils.sync_manager import get_sync_manager
            from utils.file_handler import cargar_usuarios
            
            # Obtener usuario_id
            usuarios = cargar_usuarios() or {}
            usuario_id = None
            if self.username.isdigit():
                usuario_id = str(self.username)
            else:
                for uid, info in usuarios.items():
                    if isinstance(info, dict) and info.get('username') == self.username:
                        usuario_id = str(uid)
                        break
            
            if usuario_id:
                sync_mgr = get_sync_manager()
                pending = sync_mgr.queue.get_pending_items(str(usuario_id), limit=1000)
                
                # Contar DELETE de productos
                delete_count = sum(1 for p in pending if p.get('tipo_dato') == 'productos' and p.get('operacion') == 'DELETE')
                
                if delete_count > 0:
                    print(f"[SYNC_INFO] Se encontraron {delete_count} DELETE pendientes - Se limpiarÃ¡n antes de sincronizar")
                # DEBUG: Totales para diagnÃ³stico avanzado
                prod_pending = sum(1 for p in pending if p.get('tipo_dato') == 'productos' and p.get('estado') == 'pendiente')
                otros_pending = sum(1 for p in pending if p.get('tipo_dato') != 'productos' and p.get('estado') == 'pendiente')
                print(f"[SYNC_INFO] Pendientes en cola: {len(pending)} (productos pendientes: {prod_pending}, otros pendientes: {otros_pending})")
        
        except Exception as e:
            print(f"[SYNC_INFO] No se pudo verificar pendientes: {e}")
            pass
        
        # Ã¢Å¡Â Ã¯Â¸Â PROTECCIÃƒâ€œN 4: Mostrar confirmaciÃ³n con detalles
        response = QMessageBox.question(
            self,
            "Confirmar Sincronizacion",
            f"Se sincronizaran {len(productos_locales)} productos\n\n"
            "IMPORTANTE:\n"
            "- Se agregaran/actualizaran productos en la nube (merge)\n"
            "- No se eliminaran productos remotos\n"
            "- Esta accion no se puede deshacer\n\n"
                    f"¿Deseas continuar?{sync_target_hint}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if response != QMessageBox.Yes:
            print("[SYNC] SincronizaciÃ³n cancelada por usuario")
            return

        # Si no hay items pendientes en la cola, ofrecer subir TODO el inventario
        force_full_upload = False
        try:
            sync_mgr = get_sync_manager()
            usuario_id_check = usuario_id
            pending_now = sync_mgr.queue.get_pending_items(str(usuario_id_check), limit=5)
            if len(pending_now) == 0 and productos_locales and len(productos_locales) > 0:
                resp2 = QMessageBox.question(
                    self,
                "¿Subir inventario completo?",
                f"No se encontraron cambios pendientes en la cola.\n\n¿Deseas subir TODO el inventario ({len(productos_locales)} productos) al servidor ahora?\n\nEsto hará un merge: agregará/actualizará productos y no eliminará productos remotos.{sync_target_hint}",
                    QMessageBox.Yes | QMessageBox.No
                )
                if resp2 == QMessageBox.Yes:
                    # Pedir confirmaciÃ³n textual para evitar borrados accidentales
                    from PyQt5.QtWidgets import QInputDialog
                    text, ok = QInputDialog.getText(self, "Confirmar subida", "Escribe 'SUBIR' para confirmar la subida completa:")
                    if not ok or text != 'SUBIR':
                        print("[SYNC] Subida completa cancelada: confirmaciÃ³n textual no vÃ¡lida")
                    else:
                        force_full_upload = True
        except Exception:
            pass
        
        # Desabilitar botÃ³n durante sincronizaciÃ³n
        def _set_sync_buttons_state(enabled, text):
            for attr in ("btn_sync", "btn_sync_side"):
                btn = getattr(self, attr, None)
                if btn is None:
                    continue
                try:
                    btn.setEnabled(bool(enabled))
                    btn.setText(str(text or ""))
                except Exception:
                    pass

        self._manual_sync_in_progress = True
        _set_sync_buttons_state(False, "Sincronizando...")
        
        def _sync_in_background():
            """Ejecuta sync en thread separado"""
            try:
                from utils.sync_manager import get_sync_manager
                from utils.file_handler import cargar_usuarios
                
                # Obtener usuario_id
                usuarios = cargar_usuarios() or {}
                
                usuario_id = None
                if self.username.isdigit():
                    usuario_id = str(self.username)
                else:
                    for uid, info in usuarios.items():
                        if isinstance(info, dict) and info.get('username') == self.username:
                            usuario_id = str(uid)
                            break
                
                if not usuario_id:
                    print("[ERROR] No se pudo determinar usuario_id para sincronizar")
                    self.sync_feedback_requested.emit(
                        "critical",
                        "Error de sincronizacion",
                        "No se pudo determinar el usuario para sincronizar el inventario.",
                    )
                    return
                
                sync_mgr = get_sync_manager()
                print("\n[SYNC] Iniciando sincronizacion manual...")
                if force_full_upload:
                    # Subir inventario completo directamente
                    success, message = sync_mgr.upload_inventory_direct(str(usuario_id), productos_locales)
                    stats = {'sincronizados': len(productos_locales) if success else 0, 'errores': 0 if success else 1, 'pendientes': 0}
                    if success:
                        print(f"[SYNC_SUCCESS] Inventario completo subido: {message}")
                        self.sync_feedback_requested.emit(
                            "info",
                            "Inventario sincronizado",
                            str(message or "Inventario subido correctamente."),
                        )
                    else:
                        print(f"[SYNC_ERROR] Error subiendo inventario: {message}")
                        self.sync_feedback_requested.emit(
                            "critical",
                            "Error al subir inventario",
                            str(message or "No se pudo subir el inventario."),
                        )
                else:
                    stats = sync_mgr.sync_now(str(usuario_id))
                
                print(f"[SYNC] Resultado:")
                print(f"  - Sincronizados: {stats.get('sincronizados', 0)}")
                print(f"  - Errores: {stats.get('errores', 0)}")
                print(f"  - Pendientes: {stats.get('pendientes', 0)}")
                
                if stats.get('sincronizados', 0) > 0:
                    print("[SYNC_SUCCESS] Cambios sincronizados correctamente")
                    print("[SYNC] Inventario sincronizado OK")
                elif (not force_full_upload) and int(stats.get('errores', 0) or 0) > 0:
                    self.sync_feedback_requested.emit(
                        "warning",
                        "Sincronizacion incompleta",
                        (
                            "La sincronizacion termino con errores.\n\n"
                            f"Sincronizados: {int(stats.get('sincronizados', 0) or 0)}\n"
                            f"Errores: {int(stats.get('errores', 0) or 0)}\n"
                            f"Pendientes: {int(stats.get('pendientes', 0) or 0)}"
                        ),
                    )
                
            except Exception as e:
                print(f"[SYNC_ERROR] Error durante sincronizacion: {e}")
                self.sync_feedback_requested.emit(
                    "critical",
                    "Error de sincronizacion",
                    str(e),
                )
                import traceback
                traceback.print_exc()
            finally:
                self.sync_button_state_requested.emit(True, "Sincronizar Ahora")

        import threading
        sync_thread = threading.Thread(target=_sync_in_background, daemon=True)
        sync_thread.start()
        
        # Re-habilitar botÃ³n despuÃ©s de 3 segundos
    
    def _on_products_refreshed(self, productos_remotos):
        """Actualiza productos cuando se reciben datos remotos."""
        try:
            if productos_remotos is None:
                return
            
            from utils.file_handler import cargar_productos, guardar_productos
            
            # Cargar productos locales
            productos_locales = cargar_productos(self.username)
            
            # MERGE: Remotos + locales no sincronizados
            productos_merged = []
            productos_merged.extend(productos_remotos)
            
            codigos_remotos = {p.get('codigo') for p in productos_remotos if p.get('codigo')}
            for producto_local in productos_locales:
                if producto_local.get('codigo') not in codigos_remotos:
                    productos_merged.append(producto_local)
            
            # Guardar merged localmente (PARÃMETROS EN ORDEN CORRECTO)
            guardar_productos(self.username, productos_merged, queue_sync=False)
            self.all_productos = productos_merged
            
            print(f"[INFO] Inventario actualizado - {len(productos_merged)} productos")
            
        except Exception as e:
            print(f"[ERROR] Error en _on_products_refreshed: {e}")
    
    def _on_inventory_stats_updated(self, stats):
        """Actualiza estadÃ­sticas de inventario."""
        try:
            print(f"[INFO] Inventario sincronizado - Stock: {stats['stock_total']}, Valor: ${stats['valor_total']:,.2f}")
        except Exception as e:
            print(f"[ERROR] Error actualizando stats: {e}")
    
    def _on_auto_sync_completed(self, result):
        """Se ejecuta cuando la sincronizaciÃ³n automÃ¡tica completa."""
        try:
            sincronizados = result.get('sincronizados', 0)
            errores = result.get('errores', 0)
            pendientes = result.get('pendientes', 0)
            imagenes_subidas = result.get('imagenes_subidas', 0)
            imagenes_errores = result.get('imagenes_errores', 0)
            
            if sincronizados > 0 or imagenes_subidas > 0:
                msg = f"[SYNC] Inventario sincronizado - {sincronizados} items, {errores} errores, {pendientes} pendientes"
                if imagenes_subidas > 0:
                    msg += f" | {imagenes_subidas} imÃ¡genes subidas"
                if imagenes_errores > 0:
                    msg += f" ({imagenes_errores} errores)"
                print(msg)
        except Exception as e:
            print(f"[ERROR] Error en auto sync completed: {e}")
    
    def _on_auto_sync_error(self, error_msg):
        """Se ejecuta cuando hay error en sincronizaciÃ³n automÃ¡tica."""
        print(f"[ERROR] Auto sync error: {error_msg}")
    
    def create_web_product_card(self, producto):
        """Crea una tarjeta visual para un producto web."""
        card_widget = QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)
        card_widget.setMaximumWidth(250)
        card_widget.setMinimumWidth(220)
        
        card_layout = QVBoxLayout(card_widget)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)
        
        # === IMAGEN ===
        imagen_widget = QWidget()
        imagen_widget.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                border-radius: 8px;
            }
        """)
        imagen_layout = QVBoxLayout(imagen_widget)
        imagen_layout.setContentsMargins(0, 0, 0, 0)
        
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setMinimumSize(QSize(100, 100))
        img_label.setMaximumSize(QSize(100, 100))
        
        # Mostrar loader circular mientras carga
        loader_pixmap = create_loader_svg()
        img_label.setPixmap(loader_pixmap)
        
        imagen_url = producto.get('imagen', '')
        if imagen_url:
            # Crear thread para descargar imagen asincronicamente
            image_loader = ImageLoaderThread(imagen_url, max_width=100)
            # Usar functools.partial en lugar de lambda para evitar referencias circulares
            from functools import partial
            safe_callback = partial(self._on_image_loaded, img_label, imagen_url=imagen_url)
            image_loader.image_loaded.connect(safe_callback)
            image_loader.finished.connect(image_loader.deleteLater)
            image_loader.start()
            # Guardar referencia para evitar garbage collection
            if not hasattr(self, '_image_loaders'):
                self._image_loaders = []
            self._image_loaders.append(image_loader)
        else:
            img_label.setText("Sin imagen")
            img_label.setStyleSheet("font-size: 48px; color: #CCC;")
        
        imagen_layout.addWidget(img_label, alignment=Qt.AlignCenter)
        card_layout.addWidget(imagen_widget)
        
        # === DESCUENTO (si existe) ===
        descuento = producto.get('descuento', '')
        if descuento:
            desc_label = QLabel(descuento)
            desc_label.setStyleSheet("""
                QLabel {
                    background-color: #FF5252;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            desc_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(desc_label)
        
        # === NOMBRE ===
        nombre = producto.get('nombre', 'Producto sin nombre')
        nombre_label = QLabel(nombre)
        nombre_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 12px;
                color: #1A1A1A;
            }
        """)
        nombre_label.setWordWrap(True)
        nombre_label.setMaximumHeight(50)
        nombre_label.setMinimumHeight(30)
        card_layout.addWidget(nombre_label)
        
        # === MARCA ===
        marca = producto.get('marca', '')
        if marca:
            marca_label = QLabel(marca)
            marca_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #666;
                    font-style: italic;
                }
            """)
            marca_label.setWordWrap(True)
            marca_label.setMaximumHeight(25)
            card_layout.addWidget(marca_label)
        else:
            card_layout.addSpacing(5)
        
        # === PRECIOS ===
        precios_widget = QWidget()
        precios_layout = QVBoxLayout(precios_widget)
        precios_layout.setContentsMargins(0, 0, 0, 0)
        precios_layout.setSpacing(2)
        
        precio_original = producto.get('precio_original', 'N/A')
        precio_actual = producto.get('precio_actual', 'N/A')
        
        if descuento:
            # Mostrar precio original tachado
            precio_orig_label = QLabel(precio_original)
            precio_orig_label.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #999;
                    text-decoration: line-through;
                }
            """)
            precios_layout.addWidget(precio_orig_label)
        
        # Precio actual en grande y en verde
        precio_actual_label = QLabel(precio_actual)
        precio_actual_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 16px;
                color: #2E7D32;
            }
        """)
        precios_layout.addWidget(precio_actual_label)
        
        card_layout.addWidget(precios_widget)
        
        # === BOTONES ===
        botones_widget = QWidget()
        botones_layout = QHBoxLayout(botones_widget)
        botones_layout.setContentsMargins(0, 0, 0, 0)
        botones_layout.setSpacing(6)
        
        # BotÃ³n Abrir
        btn_abrir = QPushButton("Abrir")
        btn_abrir.setToolTip("Abrir en navegador")
        btn_abrir.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        btn_abrir.setMaximumWidth(40)
        btn_abrir.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        btn_abrir.clicked.connect(lambda: self.open_product_link(producto.get('link', '#')))
        botones_layout.addWidget(btn_abrir)
        
        # BotÃ³n Copiar
        btn_copiar = QPushButton()
        btn_copiar.setIcon(create_save_svg())
        btn_copiar.setIconSize(QSize(24, 24))
        btn_copiar.setToolTip("Agregar al inventario")
        btn_copiar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #191919;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        btn_copiar.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        btn_copiar.clicked.connect(lambda: self.copy_product_to_inventory(producto, btn_copiar))
        botones_layout.addWidget(btn_copiar, stretch=1)
        
        card_layout.addWidget(botones_widget)
        
        card_widget.setMinimumWidth(200)
        card_widget.setMaximumWidth(220)
        
        return card_widget
    
    def display_web_error(self, error_msg):
        """Muestra un mensaje de error en la bÃºsqueda web."""
        # Limpiar galer?a anterior
        if hasattr(self, 'web_scraper_thread') and self.web_scraper_thread and not self.web_scraper_thread.isRunning():
            self.web_scraper_thread.deleteLater()
            self.web_scraper_thread = None
        
        self.web_search_info_label.setText(f"Error: {error_msg}")
        QMessageBox.warning(self, "Error en la búsqueda", error_msg)
    
    def pagina_anterior(self):
        """Navega a la pÃ¡gina anterior."""
        if self.web_pagina_actual > 0:
            self.web_pagina_actual -= 1
            self._show_pagination_page()
            # Scroll al top
            self.web_gallery_scroll.verticalScrollBar().setValue(0)
    
    def pagina_siguiente(self):
        """Navega a la pÃ¡gina siguiente."""
        total_paginas = (len(self.web_productos_cache) + self.web_productos_por_pagina - 1) // self.web_productos_por_pagina
        if self.web_pagina_actual < total_paginas - 1:
            self.web_pagina_actual += 1
            self._show_pagination_page()
            # Scroll al top
            self.web_gallery_scroll.verticalScrollBar().setValue(0)
    
    def open_product_link(self, url):
        """Abre el enlace del producto en el navegador."""
        import webbrowser
        if url and url != '#':
            webbrowser.open(url)
        else:
            QMessageBox.information(self, "Sin enlace", "Este producto no tiene un enlace disponible.")
    
    def copy_product_to_inventory(self, producto, btn_copiar=None):
        """Inicia el thread para copiar un producto. Muestra loader en el botÃ³n."""
        # Desabilitar botÃ³n y mostrar loader
        if btn_copiar:
            btn_copiar.setEnabled(False)
            btn_copiar.setText("")
            
            # Crear y iniciar thread del loader
            loader_thread = AnimatedLoaderThread()
            loader_thread.update_frame.connect(lambda frame: self._update_loader(btn_copiar, frame))
            loader_thread.finished.connect(loader_thread.deleteLater)
            loader_thread.start()
            self._loader_threads.append(loader_thread)  # Guardar referencia
        
        # Crear thread para hacer la copia
        copy_thread = CopyProductThread(self.username, producto)
        copy_thread.finished.connect(lambda success, msg: self._on_copy_finished(success, msg, btn_copiar, producto.get('nombre', '')))
        copy_thread.finished.connect(copy_thread.deleteLater)
        copy_thread.start()
        self._copy_threads.append(copy_thread)  # Guardar referencia
    
    def _update_loader(self, btn, frame):
        """Actualiza el loader circular animado."""
        try:
            # Verificar que el botÃ³n aÃºn existe y es vÃ¡lido
            if not btn or not isinstance(btn, QPushButton):
                return
            # Verificar que el widget aÃºn existe en la interfaz
            if btn.parent() is None:
                return
        except RuntimeError:
            return
            
        loader_chars = ['Ã¢Â â€¹', 'Ã¢Â â„¢', 'Ã¢Â Â¹', 'Ã¢Â Â¸', 'Ã¢Â Â¼', 'Ã¢Â Â´', 'Ã¢Â Â¦', 'Ã¢Â Â§']
        btn.setText(loader_chars[frame])
        btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
            }
        """)
    
    def _reset_copy_button(self, btn_copiar):
        """Reinicia el botÃ³n de copiar al estado original."""
        if btn_copiar:
            btn_copiar.setIcon(create_save_svg())
            btn_copiar.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 2px solid #191919;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #f5f5f5;
                }
                QPushButton:pressed {
                    background-color: #e0e0e0;
                }
            """)
    
    def _on_copy_finished(self, success, mensaje, btn_copiar, nombre_producto):
        """Callback cuando termina la copia."""
        # Limpiar threads de loader
        active_loaders = [t for t in self._loader_threads if t and t.isRunning()]
        for loader in active_loaders:
            loader.quit()
            loader.wait(1000)
        # Mantener solo threads inactivos
        self._loader_threads = [t for t in self._loader_threads if t and t.isRunning()]
        
        # Limpiar threads de copia finalizados
        self._copy_threads = [t for t in self._copy_threads if t and t.isRunning()]
        
        # Detener loader
        if hasattr(self, '_loader_thread') and self._loader_thread:
            self._loader_thread.stop()
            self._loader_thread.wait()
        
        # Restaurar botÃ³n
        if btn_copiar:
            btn_copiar.setEnabled(True)
            if success:
                # Mostrar SVG de check
                btn_copiar.setIcon(create_check_svg())
                btn_copiar.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: 2px solid #191919;
                        padding: 8px 12px;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #f5f5f5;
                    }
                    QPushButton:pressed {
                        background-color: #e0e0e0;
                    }
                """)
                # Volver al estado normal despuÃ©s de 2 segundos
                QtCore.QTimer.singleShot(2000, lambda: self._reset_copy_button(btn_copiar))
                
                # Mostrar diÃ¡logo para agregar stock
                dialog = AgregarStockInventarioDialog(nombre_producto, self)
                if dialog.exec_() == QDialog.Accepted:
                    unidades = dialog.get_unidades()
                    if unidades > 0:
                        # Actualizar stock del producto
                        try:
                            productos = cargar_productos(self.username)
                            prod = next((p for p in productos if p.get('nombre', '') == nombre_producto), None)
                            if prod:
                                prod['stock'] = unidades
                                guardar_productos(self.username, productos)
                                
                                # Agregar entrada al kardex
                                try:
                                    from utils.file_handler import cargar_kardex, guardar_kardex
                                    kardex = cargar_kardex(self.username)
                                    kardex.append({
                                        'tipo': 'Entrada',
                                        'producto': nombre_producto,
                                        'cantidad': unidades,
                                        'precio': prod.get('costo', 0),
                                        'fecha': datetime.datetime.now().isoformat()
                                    })
                                    guardar_kardex(self.username, kardex)
                                except:
                                    pass
                                
                                QMessageBox.information(self, "Éxito",
                                    f"Producto '{nombre_producto}' agregado con {unidades} unidades de stock.")
                        except Exception as e:
                            QMessageBox.warning(self, "Aviso", 
                                f"Producto agregado pero hubo un error al actualizar el stock: {str(e)}")
                else:
                    # Usuario no quiso agregar stock, solo mostrar mensaje de Ã©xito
                    QMessageBox.information(self, "Éxito", mensaje)
            else:
                # Si hubo error, volver al estado original
                btn_copiar.setIcon(create_save_svg())
                btn_copiar.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: 2px solid #191919;
                        padding: 8px 12px;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #f5f5f5;
                    }
                    QPushButton:pressed {
                        background-color: #e0e0e0;
                    }
                """)
                QMessageBox.critical(self, "Error", mensaje)
        
        if success:
            # Actualizar galerÃ­a
            try:
                self.update_inventory_gallery()
            except:
                pass
    
    def on_inventory_barcode_scanned(self, barcode: str):
        """Se ejecuta cuando se escanea un cÃ³digo de barras en el campo de bÃºsqueda del inventario."""
        # Buscar el producto por cÃ³digo
        productos = self.all_productos if isinstance(getattr(self, "all_productos", None), list) else []
        if not productos:
            productos = cargar_productos(self.username)
        search_term = barcode.lower()
        
        # Filtrar productos por cÃ³digo, nombre o marca
        resultados = []
        for p in productos:
            codigo = str(p.get('codigo', '')).lower()
            nombre = str(p.get('nombre', '')).lower()
            marca = str(p.get('marca', '')).lower()
            
            if search_term in codigo or search_term in nombre or search_term in marca:
                resultados.append(p)
        
        # Mostrar los resultados
        if resultados:
            # Establecer los productos encontrados
            self.total_products = resultados
            self.current_page = 0
            self._display_current_page()
        else:
            QMessageBox.warning(self, "Producto no encontrado", f"No se encontrÃ³ un producto con cÃ³digo: {barcode}")
        
        # NO limpiar el input - dejar el cÃ³digo visible
        # Mantener el foco en el campo para el prÃ³ximo escaneo
        self.side_search_entry.setFocus()

    def _ensure_inventory_filter_timer(self):
        if self._inventory_filter_timer is None:
            self._inventory_filter_timer = QTimer(self)
            self._inventory_filter_timer.setSingleShot(True)
            self._inventory_filter_timer.timeout.connect(self._run_debounced_inventory_filters)
        return self._inventory_filter_timer

    def _set_inventory_filter_busy(self, active: bool):
        label = getattr(self, "inventory_filter_status_label", None)
        if label is None:
            return

        if active:
            self._inventory_filter_loader_step = 0
            if self._inventory_filter_loader_timer is None:
                self._inventory_filter_loader_timer = QTimer(self)
                self._inventory_filter_loader_timer.setInterval(220)
                self._inventory_filter_loader_timer.timeout.connect(self._tick_inventory_filter_loader)
            self._inventory_filter_loader_timer.start()
            self._tick_inventory_filter_loader()
            return

        try:
            if self._inventory_filter_loader_timer is not None:
                self._inventory_filter_loader_timer.stop()
        except Exception:
            pass
        label.setText("")

    def _tick_inventory_filter_loader(self):
        label = getattr(self, "inventory_filter_status_label", None)
        if label is None:
            return
        frames = ("Buscando", "Buscando.", "Buscando..", "Buscando...")
        idx = int(getattr(self, "_inventory_filter_loader_step", 0)) % len(frames)
        label.setText(frames[idx])
        self._inventory_filter_loader_step = idx + 1

    def _run_debounced_inventory_filters(self):
        self.apply_inventory_filters()
    
    def on_inventory_search_text_changed(self, text):
        """Se ejecuta cuando cambia el texto de busqueda del inventario."""
        _ = text
        self._set_inventory_filter_busy(True)
        delay_ms = int(getattr(self, "_inventory_filter_delay_ms", 900) or 900)
        self._ensure_inventory_filter_timer().start(delay_ms)
    
    def perform_advanced_search(self):
        """Realiza la bÃºsqueda avanzada con los filtros especificados."""
        try:
            productos = cargar_productos(self.username)
            
            # Obtener valores de filtros
            search_name = self.search_name.text().strip().lower()
            search_marca = self.search_marca.text().strip().lower()
            search_material = self.search_material.text().strip().lower()
            
            try:
                cost_min = float(self.search_cost_min.text().strip()) if self.search_cost_min.text().strip() else 0
            except ValueError:
                cost_min = 0
            try:
                cost_max = float(self.search_cost_max.text().strip()) if self.search_cost_max.text().strip() else float('inf')
            except ValueError:
                cost_max = float('inf')
            
            try:
                price_min = float(self.search_price_min.text().strip()) if self.search_price_min.text().strip() else 0
            except ValueError:
                price_min = 0
            try:
                price_max = float(self.search_price_max.text().strip()) if self.search_price_max.text().strip() else float('inf')
            except ValueError:
                price_max = float('inf')
            
            try:
                stock_min = int(self.search_stock_min.text().strip()) if self.search_stock_min.text().strip() else 0
            except ValueError:
                stock_min = 0
            try:
                stock_max = int(self.search_stock_max.text().strip()) if self.search_stock_max.text().strip() else 999999
            except ValueError:
                stock_max = 999999
            
            only_stock = self.search_only_stock.isChecked()
            
            # Filtrar productos
            resultados = []
            for p in productos:
                # Filtro por nombre
                if search_name and search_name not in str(p.get('nombre', '')).lower():
                    continue
                
                # Filtro por marca
                if search_marca and search_marca not in str(p.get('marca', '')).lower():
                    continue
                
                # Filtro por material
                if search_material and search_material not in str(p.get('material', '')).lower():
                    continue
                
                # Filtro por costo
                try:
                    costo = float(p.get('costo', 0))
                    if not (cost_min <= costo <= cost_max):
                        continue
                except (ValueError, TypeError):
                    continue
                
                # Filtro por precio de venta
                try:
                    venta = float(p.get('venta', 0))
                    if not (price_min <= venta <= price_max):
                        continue
                except (ValueError, TypeError):
                    continue
                
                # Filtro por stock
                try:
                    stock = int(p.get('stock', 0))
                    if not (stock_min <= stock <= stock_max):
                        continue
                    if only_stock and stock == 0:
                        continue
                except (ValueError, TypeError):
                    continue
                
                resultados.append(p)
            
            # Mostrar resultados en la tabla
            self.search_results_table.setRowCount(0)
            for i, producto in enumerate(resultados):
                self.search_results_table.insertRow(i)
                
                nombre = producto.get('nombre', '')
                marca = producto.get('marca', '')
                material = producto.get('material', '')
                try:
                    costo = float(producto.get('costo', 0))
                except (ValueError, TypeError):
                    costo = 0
                try:
                    venta = float(producto.get('venta', 0))
                except (ValueError, TypeError):
                    venta = 0
                try:
                    stock = int(producto.get('stock', 0))
                except (ValueError, TypeError):
                    stock = 0
                
                # Calcular margen de ganancia
                if costo > 0:
                    margen = ((venta - costo) / costo) * 100
                else:
                    margen = 0
                
                self.search_results_table.setItem(i, 0, QTableWidgetItem(nombre))
                self.search_results_table.setItem(i, 1, QTableWidgetItem(marca))
                self.search_results_table.setItem(i, 2, QTableWidgetItem(material))
                self.search_results_table.setItem(i, 3, QTableWidgetItem(f"S/{costo:.2f}"))
                self.search_results_table.setItem(i, 4, QTableWidgetItem(f"S/{venta:.2f}"))
                self.search_results_table.setItem(i, 5, QTableWidgetItem(str(stock)))
                self.search_results_table.setItem(i, 6, QTableWidgetItem(f"{margen:.1f}%"))
                
                # BotÃ³n de acciones
                btn_action = QPushButton("Ver")
                btn_action.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 4px 8px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                btn_action.clicked.connect(lambda checked, prod=producto: self.view_product_details(prod))
                self.search_results_table.setCellWidget(i, 7, btn_action)
            
            # Actualizar informaciÃ³n de resultados
            self.search_info_label.setText(f"Se encontraron {len(resultados)} producto(s)")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error en la bÃºsqueda: {str(e)}")

    # ============================
    # PestaÃ±a Kardex
    # ============================
    
    def create_kardex_tab(self):
        """Crear la pestaÃ±a de historial Kardex."""
        kardex_widget = QWidget()
        kardex_layout = QVBoxLayout(kardex_widget)
        kardex_layout.setContentsMargins(15, 15, 15, 15)
        
        return kardex_widget
        
    # ============================
    # PestaÃ±a de ConfiguraciÃ³n
    # ============================
    
    def create_config_tab(self):
        """Crear la pestaÃ±a de configuraciÃ³n del inventario (RediseÃ±ada)."""
        config_widget = QWidget()
        config_layout = QHBoxLayout(config_widget)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(0)
        
        # 1. Panel de NavegaciÃ³n Lateral (Estilo Moderno)
        nav_panel = self._create_nav_panel()
        
        # 2. Stack de Contenido
        self.config_stacked = QStackedWidget()
        self.config_stacked.setStyleSheet("QStackedWidget { background-color: #FAFAFA; }")
        
        # -- PÃ¡ginas del Stack --
        # 0: CategorÃ­as
        self.config_stacked.addWidget(self._create_categories_panel())
        # 1: Colores
        self.config_stacked.addWidget(self._create_colors_panel())
        # 2: Marcas
        self.config_stacked.addWidget(self._create_brands_panel())
        # 3: CuadrÃ­cula
        self.config_stacked.addWidget(self._create_grid_panel())
        
        # PÃ¡ginas externas (Materiales, Tallas, Tipos de Lente)
        try:
            self._materials_page = MaterialsPage(self)
            self.config_stacked.addWidget(self._materials_page)  # 4
        except: pass
            
        try:
            self._sizes_page = SizesPage(self)
            self.config_stacked.addWidget(self._sizes_page)      # 5
        except: pass

        try:
            self._lens_types_page = LensTypesPage(self)
            self.config_stacked.addWidget(self._lens_types_page) # 6
        except: pass

        # Conectar navegaciÃ³n
        self.subsections_list.currentRowChanged.connect(self.config_stacked.setCurrentIndex)
        
        # Layout Principal
        config_layout.addWidget(nav_panel)
        config_layout.addWidget(self.config_stacked)
        
        # Cargar datos iniciales
        self.load_categories()
        self.load_brands()
        self.load_colors()
        self.load_grid_preferences()
        
        return config_widget

    def _create_nav_panel(self):
        """Crea el panel de navegaciÃ³n lateral con estilo mejorado."""
        nav_container = QWidget()
        nav_container.setFixedWidth(240)
        nav_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-right: 1px solid #E0E0E0;
            }
        """)
        layout = QVBoxLayout(nav_container)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)
        
        # T?tulo
        lbl_title = QLabel("CONFIGURACIÓN")
        lbl_title.setStyleSheet("""
            color: #757575;
            font-weight: bold;
            font-size: 12px;
            letter-spacing: 1px;
            padding-left: 5px;
        """)
        layout.addWidget(lbl_title)
        
        # Lista de NavegaciÃ³n
        self.subsections_list = QListWidget()
        self.subsections_list.setFocusPolicy(Qt.NoFocus)
        self.subsections_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 10px;
                border-radius: 6px;
                color: #424242;
                margin-bottom: 2px;
                font-size: 14px;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
                font-weight: 500;
            }
        """)
        
        # Items con Iconos
        items = [
            ("CategorÃ­as", "Ã°Å¸ÂÂ·Ã¯Â¸Â"),
            ("Colores", "Ã°Å¸Å½Â¨"),
            ("Marcas y Proveedores", "Ã°Å¸ÂÂ¢"),
            ("CuadrÃ­cula", "Ã¢â€“Â¦"),
            ("Materiales", "Ã°Å¸Â§Â±"),
            ("Tallas", "Ã°Å¸â€œÂ"),
            ("Tipos de Lente", "Ã°Å¸â€˜â€œ")
        ]
        
        for name, icon in items:
            item = QtWidgets.QListWidgetItem(f"{icon}  {name}")
            self.subsections_list.addItem(item)
            
        self.subsections_list.setCurrentRow(0)
        layout.addWidget(self.subsections_list)
        layout.addStretch()
        
        return nav_container

    def _create_header(self, title, description):
        """Helper para crear headers consistentes en los paneles."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(5)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 22px; font-weight: 300; color: #191919;")
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet("font-size: 14px; color: #757575;")
        lbl_desc.setWordWrap(True)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        return container

    def _create_categories_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        layout.addWidget(self._create_header("CategorÃ­as de Productos", 
                                           "Administra las categorÃ­as para organizar tu inventario (ej. Monturas, Lentes de Sol)."))
        
        # Ãrea de contenido
        content = QWidget()
        content.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #E0E0E0;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(20, 20, 20, 20)
        
        # Input y BotÃ³n Agregar
        input_row = QHBoxLayout()
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Nombre de nueva categorÃ­a...")
        self.category_input.setMinimumHeight(40)
        self.category_input.setStyleSheet("""
            QLineEdit { border: 1px solid #CCC; border-radius: 4px; padding: 0 10px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #2196F3; }
        """)
        
        btn_add = QPushButton("Agregar")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setMinimumHeight(40)
        btn_add.setStyleSheet("""
            QPushButton { background: #2196F3; color: white; border: none; border-radius: 4px; padding: 0 20px; font-weight: bold; }
            QPushButton:hover { background: #1976D2; }
        """)
        btn_add.clicked.connect(self.add_category)
        
        input_row.addWidget(self.category_input)
        input_row.addWidget(btn_add)
        
        # Lista
        self.categories_list = QListWidget()
        self.categories_list.setStyleSheet("""
            QListWidget { border: 1px solid #F0F0F0; border-radius: 4px; padding: 5px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #F9F9F9; }
            QListWidget::item:selected { background: #E3F2FD; color: #1565C0; }
        """)
        
        # BotÃ³n Eliminar
        btn_del = QPushButton("Eliminar Seleccionada")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton { color: #D32F2F; background: transparent; border: 1px solid #D32F2F; border-radius: 4px; padding: 8px; }
            QPushButton:hover { background: #FFEBEE; }
        """)
        btn_del.clicked.connect(self.remove_category)
        
        c_layout.addLayout(input_row)
        c_layout.addWidget(self.categories_list)
        c_layout.addWidget(btn_del, alignment=Qt.AlignRight)
        
        layout.addWidget(content)
        layout.addStretch()
        return panel

    def _create_colors_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        layout.addWidget(self._create_header("Colores Disponibles", 
                                           "Define la paleta de colores para asignar a tus productos."))
        
        content = QWidget()
        content.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #E0E0E0;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(20, 20, 20, 20)
        
        input_row = QHBoxLayout()
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("Nombre del color (ej. Negro Mate)...")
        self.color_input.setMinimumHeight(40)
        self.color_input.setStyleSheet("""
            QLineEdit { border: 1px solid #CCC; border-radius: 4px; padding: 0 10px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #2196F3; }
        """)
        
        btn_add = QPushButton("Agregar")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setMinimumHeight(40)
        btn_add.setStyleSheet("""
            QPushButton { background: #2196F3; color: white; border: none; border-radius: 4px; padding: 0 20px; font-weight: bold; }
            QPushButton:hover { background: #1976D2; }
        """)
        btn_add.clicked.connect(self.add_color)
        
        input_row.addWidget(self.color_input)
        input_row.addWidget(btn_add)
        
        self.colors_list = QListWidget()
        self.colors_list.setStyleSheet("""
            QListWidget { border: 1px solid #F0F0F0; border-radius: 4px; padding: 5px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #F9F9F9; }
            QListWidget::item:selected { background: #E3F2FD; color: #1565C0; }
        """)
        
        btn_del = QPushButton("Eliminar Seleccionado")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton { color: #D32F2F; background: transparent; border: 1px solid #D32F2F; border-radius: 4px; padding: 8px; }
            QPushButton:hover { background: #FFEBEE; }
        """)
        btn_del.clicked.connect(self.remove_color)
        
        c_layout.addLayout(input_row)
        c_layout.addWidget(self.colors_list)
        c_layout.addWidget(btn_del, alignment=Qt.AlignRight)
        
        layout.addWidget(content)
        layout.addStretch()
        return panel

    def _create_brands_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        layout.addWidget(self._create_header("Marcas y Proveedores", 
                                           "Gestiona las marcas que vendes y la informaciÃ³n de contacto de tus proveedores."))
        
        content = QWidget()
        content.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #E0E0E0;")
        main_h = QHBoxLayout(content)
        main_h.setContentsMargins(20, 20, 20, 20)
        main_h.setSpacing(20)
        
        # Columna Izquierda: Lista
        left_col = QVBoxLayout()
        self.brands_list = QListWidget()
        self.brands_list.setFixedWidth(250)
        self.brands_list.setStyleSheet("""
            QListWidget { border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #F5F5F5; font-weight: 500; }
            QListWidget::item:selected { background: #E3F2FD; color: #1565C0; border-left: 3px solid #1565C0; }
        """)
        self.brands_list.itemClicked.connect(self.load_brand_details)
        
        left_col.addWidget(QLabel("Marcas Registradas:"))
        left_col.addWidget(self.brands_list)
        
        # Columna Derecha: Formulario
        right_col = QVBoxLayout()
        form_layout = QGridLayout()
        form_layout.setSpacing(15)
        
        self.brand_input = QLineEdit(); self.brand_input.setPlaceholderText("Nombre de la Marca")
        self.provider_input = QLineEdit(); self.provider_input.setPlaceholderText("Nombre del Proveedor")
        self.contact_input = QLineEdit(); self.contact_input.setPlaceholderText("TelÃ©fono / Email / DirecciÃ³n")
        
        for w in [self.brand_input, self.provider_input, self.contact_input]:
            w.setMinimumHeight(40)
            w.setStyleSheet("border: 1px solid #CCC; border-radius: 4px; padding: 0 10px;")

        form_layout.addWidget(QLabel("Marca:"), 0, 0); form_layout.addWidget(self.brand_input, 0, 1)
        form_layout.addWidget(QLabel("Proveedor:"), 1, 0); form_layout.addWidget(self.provider_input, 1, 1)
        form_layout.addWidget(QLabel("Contacto:"), 2, 0); form_layout.addWidget(self.contact_input, 2, 1)
        
        btns_layout = QHBoxLayout()
        
        btn_save = QPushButton("Guardar / Actualizar")
        btn_save.setStyleSheet("background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold;")
        btn_save.clicked.connect(self.add_brand)
        
        btn_clear = QPushButton("Limpiar")
        btn_clear.setStyleSheet("background: #f5f5f5; color: #333; border: 1px solid #CCC; padding: 10px 20px; border-radius: 4px;")
        btn_clear.clicked.connect(self.clear_brand_inputs)
        
        btn_del = QPushButton("Eliminar")
        btn_del.setStyleSheet("background: #FFEBEE; color: #D32F2F; border: 1px solid #ffcdd2; padding: 10px 20px; border-radius: 4px;")
        btn_del.clicked.connect(self.remove_brand)
        
        btns_layout.addWidget(btn_clear)
        btns_layout.addStretch()
        btns_layout.addWidget(btn_del)
        btns_layout.addWidget(btn_save)
        
        right_col.addLayout(form_layout)
        right_col.addStretch()
        right_col.addLayout(btns_layout)
        
        main_h.addLayout(left_col)
        main_h.addLayout(right_col)
        
        layout.addWidget(content)
        return panel

    def _create_grid_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        layout.addWidget(self._create_header("VisualizaciÃ³n", "Personaliza cÃ³mo se ven los productos en el inventario."))
        
        content = QWidget()
        content.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #E0E0E0;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(30, 30, 30, 30)
        c_layout.setSpacing(20)
        
        # Grid Size
        row = QHBoxLayout()
        icon = QLabel("-")
        icon.setStyleSheet("font-size: 24px; color: #555;")
        
        lbl = QLabel("Columnas en vista de cuadrÃ­cula:")
        lbl.setStyleSheet("font-size: 16px; font-weight: 500;")
        
        self.columns_spin = QtWidgets.QSpinBox()
        self.columns_spin.setMinimum(2)
        self.columns_spin.setMaximum(8)
        self.columns_spin.setFixedWidth(100)
        self.columns_spin.setMinimumHeight(35)
        self.columns_spin.setStyleSheet("font-size: 14px; padding: 5px;")
        self.columns_spin.valueChanged.connect(self.save_grid_preferences)
        
        row.addWidget(icon)
        row.addWidget(lbl)
        row.addWidget(self.columns_spin)
        row.addStretch()
        
        c_layout.addLayout(row)
        
        # Preview Text
        info = QLabel("Ajusta este valor segÃºn el tamaÃ±o de tu monitor. Un valor mÃ¡s alto mostrarÃ¡ mÃ¡s productos por fila pero mÃ¡s pequeÃ±os.")
        info.setStyleSheet("color: #666; font-style: italic; margin-left: 35px;")
        info.setWordWrap(True)
        c_layout.addWidget(info)
        
        layout.addWidget(content)
        layout.addStretch()
        return panel
        
    def _fix_inventory_config_tab_texts(self):
        try:
            tab_widget = getattr(self, "tab_widget", None)
            if tab_widget is None or tab_widget.count() <= 3:
                return

            tab_widget.setTabText(3, "Configuracion del Inventario")

            built = getattr(self, "_lazy_tabs_built", set()) or set()
            if 3 in built:
                return

            placeholder = tab_widget.widget(3)
            if placeholder is None:
                return

            labels = placeholder.findChildren(QLabel)
            if labels:
                labels[0].setText("Cargando Configuracion...")
        except Exception:
            pass

    def _create_nav_panel(self):
        nav_container = QWidget()
        nav_container.setFixedWidth(240)
        nav_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-right: 1px solid #E0E0E0;
            }
        """)

        layout = QVBoxLayout(nav_container)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)

        lbl_title = QLabel("CONFIGURACIÓN")
        lbl_title.setStyleSheet("""
            color: #757575;
            font-weight: bold;
            font-size: 12px;
            letter-spacing: 1px;
            padding-left: 5px;
        """)
        layout.addWidget(lbl_title)

        self.subsections_list = QListWidget()
        self.subsections_list.setFocusPolicy(Qt.NoFocus)
        self.subsections_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 10px;
                border-radius: 6px;
                color: #424242;
                margin-bottom: 2px;
                font-size: 14px;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
                font-weight: 500;
            }
        """)

        for name in [
            "Categorias",
            "Colores",
            "Marcas y Proveedores",
            "Cuadricula",
            "Materiales",
            "Tallas",
            "Tipos de Lente",
        ]:
            self.subsections_list.addItem(QtWidgets.QListWidgetItem(name))

        self.subsections_list.setCurrentRow(0)
        layout.addWidget(self.subsections_list)
        layout.addStretch()
        return nav_container

    def _create_categories_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(self._create_header(
            "Categorias de Productos",
            "Administra las categorias para organizar tu inventario (ej. Monturas, Lentes de Sol).",
        ))

        content = QWidget()
        content.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #E0E0E0;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(20, 20, 20, 20)

        input_row = QHBoxLayout()
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Nombre de nueva categoria...")
        self.category_input.setMinimumHeight(40)
        self.category_input.setStyleSheet("""
            QLineEdit { border: 1px solid #CCC; border-radius: 4px; padding: 0 10px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #2196F3; }
        """)

        btn_add = QPushButton("Agregar")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setMinimumHeight(40)
        btn_add.setStyleSheet("""
            QPushButton { background: #2196F3; color: white; border: none; border-radius: 4px; padding: 0 20px; font-weight: bold; }
            QPushButton:hover { background: #1976D2; }
        """)
        btn_add.clicked.connect(self.add_category)

        input_row.addWidget(self.category_input)
        input_row.addWidget(btn_add)

        self.categories_list = QListWidget()
        self.categories_list.setStyleSheet("""
            QListWidget { border: 1px solid #F0F0F0; border-radius: 4px; padding: 5px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #F9F9F9; }
            QListWidget::item:selected { background: #E3F2FD; color: #1565C0; }
        """)

        btn_del = QPushButton("Eliminar seleccionada")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton { color: #D32F2F; background: transparent; border: 1px solid #D32F2F; border-radius: 4px; padding: 8px; }
            QPushButton:hover { background: #FFEBEE; }
        """)
        btn_del.clicked.connect(self.remove_category)

        c_layout.addLayout(input_row)
        c_layout.addWidget(self.categories_list)
        c_layout.addWidget(btn_del, alignment=Qt.AlignRight)

        layout.addWidget(content)
        layout.addStretch()
        return panel

    def _create_brands_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(self._create_header(
            "Marcas y Proveedores",
            "Gestiona las marcas que vendes y la informacion de contacto de tus proveedores.",
        ))

        content = QWidget()
        content.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #E0E0E0;")
        main_h = QHBoxLayout(content)
        main_h.setContentsMargins(20, 20, 20, 20)
        main_h.setSpacing(20)

        left_col = QVBoxLayout()
        self.brands_list = QListWidget()
        self.brands_list.setFixedWidth(250)
        self.brands_list.setStyleSheet("""
            QListWidget { border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #F5F5F5; font-weight: 500; }
            QListWidget::item:selected { background: #E3F2FD; color: #1565C0; border-left: 3px solid #1565C0; }
        """)
        self.brands_list.itemClicked.connect(self.load_brand_details)

        left_col.addWidget(QLabel("Marcas registradas:"))
        left_col.addWidget(self.brands_list)

        right_col = QVBoxLayout()
        form_layout = QGridLayout()
        form_layout.setSpacing(15)

        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Nombre de la marca")
        self.provider_input = QLineEdit()
        self.provider_input.setPlaceholderText("Nombre del proveedor")
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Telefono / Email / Direccion")

        for widget in [self.brand_input, self.provider_input, self.contact_input]:
            widget.setMinimumHeight(40)
            widget.setStyleSheet("border: 1px solid #CCC; border-radius: 4px; padding: 0 10px;")

        form_layout.addWidget(QLabel("Marca:"), 0, 0)
        form_layout.addWidget(self.brand_input, 0, 1)
        form_layout.addWidget(QLabel("Proveedor:"), 1, 0)
        form_layout.addWidget(self.provider_input, 1, 1)
        form_layout.addWidget(QLabel("Contacto:"), 2, 0)
        form_layout.addWidget(self.contact_input, 2, 1)

        btns_layout = QHBoxLayout()

        btn_save = QPushButton("Guardar / Actualizar")
        btn_save.setStyleSheet("background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold;")
        btn_save.clicked.connect(self.add_brand)

        btn_clear = QPushButton("Limpiar")
        btn_clear.setStyleSheet("background: #f5f5f5; color: #333; border: 1px solid #CCC; padding: 10px 20px; border-radius: 4px;")
        btn_clear.clicked.connect(self.clear_brand_inputs)

        btn_del = QPushButton("Eliminar")
        btn_del.setStyleSheet("background: #FFEBEE; color: #D32F2F; border: 1px solid #ffcdd2; padding: 10px 20px; border-radius: 4px;")
        btn_del.clicked.connect(self.remove_brand)

        btns_layout.addWidget(btn_clear)
        btns_layout.addStretch()
        btns_layout.addWidget(btn_del)
        btns_layout.addWidget(btn_save)

        right_col.addLayout(form_layout)
        right_col.addStretch()
        right_col.addLayout(btns_layout)

        main_h.addLayout(left_col)
        main_h.addLayout(right_col)

        layout.addWidget(content)
        return panel

    def _create_grid_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(self._create_header(
            "Visualizacion",
            "Personaliza como se ven los productos en el inventario.",
        ))

        content = QWidget()
        content.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #E0E0E0;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(30, 30, 30, 30)
        c_layout.setSpacing(20)

        row = QHBoxLayout()
        icon = QLabel("#")
        icon.setStyleSheet("font-size: 24px; color: #555;")

        lbl = QLabel("Columnas en vista de cuadricula:")
        lbl.setStyleSheet("font-size: 16px; font-weight: 500;")

        self.columns_spin = QtWidgets.QSpinBox()
        self.columns_spin.setMinimum(2)
        self.columns_spin.setMaximum(8)
        self.columns_spin.setFixedWidth(100)
        self.columns_spin.setMinimumHeight(35)
        self.columns_spin.setStyleSheet("font-size: 14px; padding: 5px;")
        self.columns_spin.valueChanged.connect(self.save_grid_preferences)

        row.addWidget(icon)
        row.addWidget(lbl)
        row.addWidget(self.columns_spin)
        row.addStretch()

        c_layout.addLayout(row)

        info = QLabel(
            "Ajusta este valor segun el tamano de tu monitor. Un valor mas alto mostrara mas productos por fila, pero mas pequenos."
        )
        info.setStyleSheet("color: #666; font-style: italic; margin-left: 35px;")
        info.setWordWrap(True)
        c_layout.addWidget(info)

        layout.addWidget(content)
        layout.addStretch()
        return panel

    def _default_sections(self):
        return [
            "Monturas",
            "Lunas",
            "Lentes de Contacto",
            "Gafas de Sol",
            "Accesorios",
            "Liquidos de Limpieza",
        ]

    def _categories_file_path(self):
        return os.path.join("VISO", "data", "categories.json")

    def _get_sorted_categories(self):
        categories = []
        try:
            file_path = self._categories_file_path()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                if isinstance(raw_data, list):
                    categories = [str(c).strip() for c in raw_data if str(c).strip()]
        except Exception:
            categories = []

        if not categories:
            categories = self._default_sections()

        return sorted(set(categories), key=lambda x: x.lower())

    def _refresh_side_section_combo(self):
        if not hasattr(self, 'side_section_combo'):
            return

        selected_value = str(self.side_section_combo.currentData() or '').strip()
        categories = self._get_sorted_categories()

        self.side_section_combo.blockSignals(True)
        self.side_section_combo.clear()
        self.side_section_combo.addItem("Todas las secciones", "")
        for category in categories:
            self.side_section_combo.addItem(category, category)

        if selected_value:
            idx = self.side_section_combo.findData(selected_value)
            if idx >= 0:
                self.side_section_combo.setCurrentIndex(idx)
        self.side_section_combo.blockSignals(False)

    def _refresh_side_brand_combo(self):
        if not hasattr(self, 'side_brand_combo'):
            return

        selected_value = str(self.side_brand_combo.currentData() or '').strip()
        marcas = sorted({
            str((p or {}).get('marca') or '').strip()
            for p in (self.all_productos if isinstance(getattr(self, 'all_productos', None), list) else [])
            if isinstance(p, dict) and str((p or {}).get('marca') or '').strip()
        }, key=lambda x: x.lower())

        self.side_brand_combo.blockSignals(True)
        self.side_brand_combo.clear()
        self.side_brand_combo.addItem("Todas las marcas", "")
        for marca in marcas:
            self.side_brand_combo.addItem(marca, marca)

        if selected_value:
            idx = self.side_brand_combo.findData(selected_value)
            if idx >= 0:
                self.side_brand_combo.setCurrentIndex(idx)
        self.side_brand_combo.blockSignals(False)

    def _normalize_section_value(self, value):
        return str(value or '').strip()

    def _get_product_section(self, product):
        if not isinstance(product, dict):
            return ''
        return self._normalize_section_value(product.get('seccion') or product.get('categoria'))

    def _set_product_section(self, product, section):
        if not isinstance(product, dict):
            return
        normalized = self._normalize_section_value(section)
        product['categoria'] = normalized
        product['seccion'] = normalized

    def load_categories(self):
        """Cargar lista de categorias desde el archivo."""
        try:
            categories = self._get_sorted_categories()
            if hasattr(self, 'categories_list'):
                self.categories_list.clear()
                self.categories_list.addItems(categories)
            self._refresh_side_section_combo()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar categorias: {str(e)}")
    
    def save_categories(self):
        """Guardar lista de categorias al archivo."""
        try:
            categories = sorted(set([
                self.categories_list.item(i).text().strip()
                for i in range(self.categories_list.count())
                if self.categories_list.item(i).text().strip()
            ]), key=lambda x: x.lower())
            file_path = self._categories_file_path()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(categories, f, ensure_ascii=False, indent=4)
            self._refresh_side_section_combo()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar categorias: {str(e)}")
    
    def add_category(self):
        """Agregar una nueva categoria."""
        category = self.category_input.text().strip()
        if not category:
            return
            
        existing_items = [
            self.categories_list.item(i).text().strip().lower()
            for i in range(self.categories_list.count())
        ]
        if category.lower() in existing_items:
            QMessageBox.warning(self, "Error", "Esta categoria ya existe.")
            return
            
        self.categories_list.addItem(category)
        self.category_input.clear()
        self.save_categories()
    
    def remove_category(self):
        """Eliminar la categoria seleccionada y reasignar productos si esta en uso."""
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Selecciona una categoria para eliminar.")
            return

        category_to_remove = current_item.text().strip()
        if not category_to_remove:
            return

        productos = cargar_productos(self.username) or []
        in_use_products = [
            p for p in productos
            if self._get_product_section(p).lower() == category_to_remove.lower()
        ]

        reply = QMessageBox.question(
            self,
            "Confirmar",
                f"¿Eliminar la categoría '{category_to_remove}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if in_use_products:
            available_targets = sorted(set([
                self.categories_list.item(i).text().strip()
                for i in range(self.categories_list.count())
                if self.categories_list.item(i).text().strip() and
                self.categories_list.item(i).text().strip().lower() != category_to_remove.lower()
            ]), key=lambda x: x.lower())

            if available_targets:
                target_category, ok = QInputDialog.getItem(
                    self,
                    "Reasignar productos",
                    (
                        f"La categoria '{category_to_remove}' esta asignada a "
                        f"{len(in_use_products)} productos.\n\n"
                        "Selecciona la nueva categoria para esos productos:"
                    ),
                    available_targets,
                    0,
                    False
                )
                if not ok:
                    return
                for p in productos:
                    if self._get_product_section(p).lower() == category_to_remove.lower():
                        self._set_product_section(p, target_category)
            else:
                clear_reply = QMessageBox.question(
                    self,
                    "Categoria en uso",
                    (
                        f"La categoria '{category_to_remove}' esta asignada a "
                        f"{len(in_use_products)} productos y no hay otra categoria disponible.\n\n"
                    "¿Deseas dejar esos productos sin categoría?"
                    ),
                    QMessageBox.Yes | QMessageBox.No
                )
                if clear_reply != QMessageBox.Yes:
                    return
                for p in productos:
                    if self._get_product_section(p).lower() == category_to_remove.lower():
                        self._set_product_section(p, "")

            guardar_productos(self.username, productos)
            self.all_productos = productos

        self.categories_list.takeItem(self.categories_list.row(current_item))
        self.save_categories()
        self.apply_inventory_filters()
    
    def load_brands(self):
        """Cargar lista de marcas desde el archivo."""
        try:
            file_path = os.path.join("VISO", "data", "brands.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.brands_data = json.load(f)
            else:
                # No crear marcas por defecto. Las marcas son personales por usuario
                # y deben aÃ±adirse manualmente desde el gestor de marcas.
                self.brands_data = {}
            
            self.brands_list.clear()
            self.brands_list.addItems(sorted(self.brands_data.keys()))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar marcas: {str(e)}")
    
    def save_brands(self):
        """Guardar marcas al archivo y sincronizar con la nube."""
        try:
            from utils.file_handler import get_user_file_path
            file_path = get_user_file_path(self.username, "brands.json")
            os.makedirs(file_path.parent, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.brands_data, f, ensure_ascii=False, indent=4)
            
            # Sincronizar con la nube
            try:
                from utils.sync_manager import get_sync_manager
                sync_mgr = get_sync_manager()
                
                # Obtener usuario_id real
                usuarios = cargar_usuarios() or {}
                usuario_id = self.username
                for uid, info in usuarios.items():
                    if isinstance(info, dict) and info.get('username') == self.username:
                        usuario_id = uid
                        break
                
                sync_mgr.queue_change(
                    usuario_id=str(usuario_id),
                    tipo_dato='marcas',
                    operacion='SYNC_ALL',
                    registro_id='bulk',
                    contenido={'marcas': self.brands_data}
                )
                sync_mgr.sync_now(str(usuario_id))
            except Exception as sync_e:
                print(f"[SYNC] Error encolando marcas: {sync_e}")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar marcas: {str(e)}")
    
    def add_brand(self):
        """Agregar una nueva marca."""
        brand = self.brand_input.text().strip()
        provider = self.provider_input.text().strip()
        contact = self.contact_input.text().strip()
        
        if not brand:
            QMessageBox.warning(self, "Error", "Ingresa el nombre de la marca.")
            return
            
        if brand in self.brands_data and not hasattr(self, 'editing_brand'):
            QMessageBox.warning(self, "Error", "Esta marca ya existe.")
            return
            
        self.brands_data[brand] = {
            "provider": provider,
            "contact": contact
        }
        
        self.save_brands()
        self.load_brands()
        self.clear_brand_inputs()
    
    def edit_brand(self):
        """Editar la marca seleccionada."""
        current_item = self.brands_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Selecciona una marca para editar.")
            return
        
        brand = current_item.text()
        new_brand = self.brand_input.text().strip()
        
        if not new_brand:
            QMessageBox.warning(self, "Error", "El nombre de la marca no puede estar vacÃ­o.")
            return
        
        # Si el nombre cambiÃ³, eliminar la entrada antigua
        if brand != new_brand:
            del self.brands_data[brand]
        
        self.editing_brand = True
        self.add_brand()
        delattr(self, 'editing_brand')
    
    def remove_brand(self):
        """Eliminar la marca seleccionada."""
        current_item = self.brands_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Selecciona una marca para eliminar.")
            return
            
        brand = current_item.text()
        reply = QMessageBox.question(self, "Confirmar", 
            f"¿Eliminar la marca '{brand}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.brands_data[brand]
            self.save_brands()
            self.load_brands()
            self.clear_brand_inputs()
    
    def load_brand_details(self, item):
        """Cargar detalles de la marca seleccionada."""
        brand = item.text()
        brand_data = self.brands_data[brand]
        
        self.brand_input.setText(brand)
        self.provider_input.setText(brand_data.get("provider", ""))
        self.contact_input.setText(brand_data.get("contact", ""))
    
    def clear_brand_inputs(self):
        """Limpiar los campos del formulario de marcas."""
        self.brand_input.clear()
        self.provider_input.clear()
        self.contact_input.clear()
        
    # ============================
    # GestiÃ³n de Colores
    # ============================
    
    def load_colors(self):
        """Cargar lista de colores desde el archivo."""
        try:
            file_path = os.path.join("VISO", "data", "colors.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    colors = json.load(f)
            else:
                colors = [
                    "Negro", "Blanco", "Dorado", "Plateado", "Azul", "Verde",
                    "Rojo", "Rosa", "Morado", "MarrÃ³n", "Gris", "Transparente"
                ]
            self.colors_list.clear()
            self.colors_list.addItems(sorted(colors))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar colores: {str(e)}")
    
    def save_colors(self):
        """Guardar lista de colores al archivo."""
        try:
            colors = [self.colors_list.item(i).text() 
                     for i in range(self.colors_list.count())]
            file_path = os.path.join("VISO", "data", "colors.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(colors, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al guardar colores: {str(e)}")
    
    def add_color(self):
        """Agregar un nuevo color."""
        color = self.color_input.text().strip()
        if not color:
            return
            
        # Verificar si ya existe
        existing_items = [self.colors_list.item(i).text() 
                         for i in range(self.colors_list.count())]
        if color in existing_items:
            QMessageBox.warning(self, "Error", "Este color ya existe.")
            return
            
        self.colors_list.addItem(color)
        self.color_input.clear()
        self.save_colors()
    
    def remove_color(self):
        """Eliminar el color seleccionado."""
        current_item = self.colors_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Selecciona un color para eliminar.")
            return
            
        reply = QMessageBox.question(self, "Confirmar", 
                f"¿Eliminar el color '{current_item.text()}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.colors_list.takeItem(self.colors_list.row(current_item))
            self.save_colors()
    def create_kardex_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title aligned to left
        title = QLabel("Kardex de Inventario")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignLeft)
        layout.addWidget(title)

        # --- SECCIÃƒâ€œN DE FILTROS Y ACCIONES ---
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 6px;
                border: 1px solid #E0E0E0;
            }
            QLabel {
                font-weight: 600;
                color: #555;
            }
        """)
        
        # Layout principal del frame de filtros (Vertical para apilar controles rÃ¡pidos y filtros manuales)
        main_filter_layout = QVBoxLayout(filter_frame)
        main_filter_layout.setContentsMargins(15, 12, 15, 12)
        main_filter_layout.setSpacing(10)

        # 1. FILTROS RÃPIDOS DE FECHA
        quick_dates_layout = QHBoxLayout()
        quick_dates_layout.setSpacing(10)
        
        lbl_quick = QLabel("Filtros RÃ¡pidos:")
        quick_dates_layout.addWidget(lbl_quick)

        # Definir botones y sus rangos
        quick_buttons = [
            ("Hoy", "today"),
            ("Esta Semana", "week"),
            ("Este Mes", "month"),
            ("ÃƒÅ¡ltimos 3 Meses", "3months"),
            ("ÃƒÅ¡ltimos 6 Meses", "6months"),
            ("ÃƒÅ¡ltimo AÃ±o", "year"),
            ("Todo", "all")
        ]

        for text, mode in quick_buttons:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f5f5f5;
                    color: #333;
                    border: 1px solid #ddd;
                    padding: 5px 12px;
                    border-radius: 15px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                    border-color: #ccc;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            # Usar lambda con argumento por defecto para capturar el valor de 'mode'
            btn.clicked.connect(lambda checked, m=mode: self.set_kardex_date_range(m))
            quick_dates_layout.addWidget(btn)
        
        quick_dates_layout.addStretch()
        main_filter_layout.addLayout(quick_dates_layout)

        # Separador horizontal
        h_line = QFrame()
        h_line.setFrameShape(QFrame.HLine)
        h_line.setFrameShadow(QFrame.Sunken)
        h_line.setStyleSheet("background-color: #F0F0F0;")
        main_filter_layout.addWidget(h_line)

        # 2. FILTROS MANUALES Y ACCIONES
        manual_filter_layout = QHBoxLayout()
        manual_filter_layout.setSpacing(15)

        # Filtro de Fechas
        lbl_from = QLabel("Desde:")
        self.kardex_date_from = QDateEdit()
        self.kardex_date_from.setCalendarPopup(True)
        self.kardex_date_from.setDate(QDate.currentDate().addDays(-30))
        self.kardex_date_from.setDisplayFormat("dd/MM/yyyy")
        self.kardex_date_from.setMinimumHeight(30)
        
        lbl_to = QLabel("Hasta:")
        self.kardex_date_to = QDateEdit()
        self.kardex_date_to.setCalendarPopup(True)
        self.kardex_date_to.setDate(QDate.currentDate())
        self.kardex_date_to.setDisplayFormat("dd/MM/yyyy")
        self.kardex_date_to.setMinimumHeight(30)

        # BÃºsqueda de Producto
        lbl_search = QLabel("Producto:")
        self.kardex_txt_search = QLineEdit()
        self.kardex_txt_search.setPlaceholderText("Nombre del producto...")
        self.kardex_txt_search.setMinimumWidth(200)
        self.kardex_txt_search.setMinimumHeight(30)

        # Botones de Filtro
        btn_filter = QPushButton("Filtrar")
        btn_filter.setMinimumHeight(30)
        btn_filter.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                padding: 0 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #222; }
        """)
        btn_filter.clicked.connect(self.update_kardex_table)

        # Separador vertical
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0;")

        # Botones de Acciones
        btn_reload = QPushButton("Recargar")
        btn_reload.setMinimumHeight(30)
        btn_reload.setStyleSheet("""
            QPushButton {
                background-color: #0288D1;
                color: white;
                border: none;
                padding: 0 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0277BD; }
        """)
        btn_reload.clicked.connect(self.update_kardex_table)

        btn_delete = QPushButton("Eliminar Seleccionados")
        btn_delete.setMinimumHeight(30)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                border: none;
                padding: 0 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #C62828; }
        """)
        btn_delete.clicked.connect(self.delete_selected_kardex_items)

        btn_export = QPushButton("Exportar Excel")
        btn_export.setMinimumHeight(30)
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2A8659;
                color: white;
                border: none;
                padding: 0 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1E6642; }
        """)
        btn_export.clicked.connect(self.export_kardex_to_excel)

        # AÃ±adir widgets al layout manual
        manual_filter_layout.addWidget(lbl_from)
        manual_filter_layout.addWidget(self.kardex_date_from)
        manual_filter_layout.addWidget(lbl_to)
        manual_filter_layout.addWidget(self.kardex_date_to)
        manual_filter_layout.addWidget(lbl_search)
        manual_filter_layout.addWidget(self.kardex_txt_search)
        manual_filter_layout.addWidget(btn_filter)
        manual_filter_layout.addWidget(line)
        manual_filter_layout.addWidget(btn_reload)
        manual_filter_layout.addWidget(btn_delete)
        manual_filter_layout.addStretch()
        manual_filter_layout.addWidget(btn_export)

        main_filter_layout.addLayout(manual_filter_layout)

        layout.addWidget(filter_frame)

        # Tabla
        self.tree_kardex = QTableWidget()
        self.tree_kardex.setColumnCount(7)
        self.tree_kardex.setHorizontalHeaderLabels(
            ["Fecha", "Movimiento", "CÃ³digo", "Producto", "Cantidad", "Costo Total", "Stock Final"]
        )
        self.tree_kardex.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tree_kardex.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Permitir selecciÃ³n mÃºltiple para borrar varios a la vez
        self.tree_kardex.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tree_kardex.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.tree_kardex.setAlternatingRowColors(True)
        self.tree_kardex.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 10px;
                font-weight: 600;
                color: #444;
                border: none;
                border-bottom: 2px solid #E0E0E0;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #000;
            }
        """)
        layout.addWidget(self.tree_kardex)

        self.update_kardex_table()
        return tab

    def set_kardex_date_range(self, mode):
        """Establece el rango de fechas para los filtros rÃ¡pidos."""
        today = QDate.currentDate()
        start_date = today
        
        if mode == "today":
            start_date = today
        elif mode == "week":
            # Inicio de semana (Lunes)
            start_date = today.addDays(-(today.dayOfWeek() - 1))
        elif mode == "month":
            start_date = QDate(today.year(), today.month(), 1)
        elif mode == "3months":
            start_date = today.addMonths(-3)
        elif mode == "6months":
            start_date = today.addMonths(-6)
        elif mode == "year":
            start_date = today.addYears(-1)
        elif mode == "all":
            # Fecha muy antigua para incluir todo
            start_date = QDate(2020, 1, 1)

        self.kardex_date_from.setDate(start_date)
        self.kardex_date_to.setDate(today)
        
        # Actualizar automÃ¡ticamente
        self.update_kardex_table()

    # ============================
    # Funciones Inventario
    # ============================
    
    # Ã°Å¸Å¡â‚¬ STREAMING: Carga de productos por chunks
    def load_inventory_streaming(self):
        """Inicia la carga de productos en background con streaming.
        Muestra un loader bonito en el Ã¡rea de productos mientras carga.
        
        Ã¢Å¡Â Ã¯Â¸Â ProtecciÃ³n: Ignora llamadas duplicadas si ya estÃ¡ cargando.
        """
        # Si ya estÃ¡ cargando, no iniciar otra carga
        if self.streamer_thread is not None and self.streamer_thread.isRunning():
            print("Ã¢â€žÂ¹Ã¯Â¸Â Ya hay una carga en progreso, ignorando llamada duplicada")
            return
        
        # Si ya estÃ¡ cargado, no recargar (serÃ¡ reemplazado por _load_from_server_once si hay algo del servidor)
        if self.all_productos:
            print("Ã¢â€žÂ¹Ã¯Â¸Â Inventario ya cargado, usando cachÃ©")
            return
        
        # Mostrar loader bonito en el Ã¡rea de productos
        self._show_inventory_loader()
        
        # Iniciar streaming en thread separado
        # Ã¢Å¡Â Ã¯Â¸Â IMPORTANTE: Esto solo carga locales como FALLBACK
        # SerÃ¡ reemplazado por _load_from_server_once() si hay productos en servidor
        self.streamer_thread = ProductStreamerThread(self.username, chunk_size=50)
        self.streamer_thread.chunk_ready.connect(self._on_product_chunk_ready)
        self.streamer_thread.finished.connect(self._on_streaming_finished)
        self.streamer_thread.error.connect(self._on_streaming_error)
        self.streamer_thread.start()
    
    def _show_inventory_loader(self, title="Cargando inventario", subtitle="Conectando con la nube..."):
        """Muestra un loader esquelético animado en la galeria de productos."""
        self._stop_inventory_loader_animation()

        # Limpiar grid
        while self.products_grid.count():
            item = self.products_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Container principal
        self.skeleton_loader = InventorySkeletonGrid(title=title, subtitle=subtitle)
        self.skeleton_loader.setMinimumHeight(800) # Ensure it covers the scroll area

        self.products_grid.addWidget(self.skeleton_loader, 0, 0, 1, 1)
        self.products_grid.update()

        # Update references for other methods that might expect them
        self._loader_status_label = self.skeleton_loader
        self._start_inventory_loader_animation()

    def _start_inventory_loader_animation(self):
        try:
            if self._loader_timer is not None:
                self._loader_timer.stop()
                self._loader_timer.deleteLater()
        except Exception:
            pass
        self._loader_timer = None
        self._loader_status_label = None
        self._loader_step = 0
        self._loader_timer = QTimer(self)
        self._loader_timer.setInterval(340)
        self._loader_timer.timeout.connect(self._tick_inventory_loader)
        self._loader_timer.start()
        self._tick_inventory_loader()

    def _stop_inventory_loader_animation(self):
        try:
            if self._loader_timer is not None:
                self._loader_timer.stop()
                self._loader_timer.deleteLater()
        except Exception:
            pass
        self._loader_timer = None
        self._loader_status_label = None
        self._loader_step = 0

        # Stop and remove skeleton loader if it exists
        if hasattr(self, 'skeleton_loader') and self.skeleton_loader is not None:
            try:
                self.skeleton_loader.anim.stop()
                self.skeleton_loader.deleteLater()
            except Exception:
                pass
            self.skeleton_loader = None

    def _tick_inventory_loader(self):
        label = getattr(self, "_loader_status_label", None)
        if label is None:
            return
        frames = (
            "Preparando datos",
            "Preparando datos.",
            "Preparando datos..",
            "Preparando datos...",
            "Sincronizando inventario",
            "Sincronizando inventario.",
            "Sincronizando inventario..",
            "Sincronizando inventario...",
        )
        idx = int(getattr(self, "_loader_step", 0)) % len(frames)
        try:
            if hasattr(label, "set_loading_text"):
                label.set_loading_text("Cargando inventario", frames[idx])
            else:
                label.setText(frames[idx])
        except Exception:
            pass
        self._loader_step = idx + 1

    
    def _on_product_chunk_ready(self, chunk):
        """Callback cuando un chunk de productos está listo."""
        is_first_chunk = len(self.all_productos) == 0
        self.all_productos.extend(chunk)

        if is_first_chunk:
            self._stop_inventory_loader_animation()
            self.total_products = self.all_productos
            self.current_page = 0
            QtCore.QTimer.singleShot(0, self._display_current_page)
            QtCore.QTimer.singleShot(0, self._update_pagination_buttons)
        else:
            self.total_products = self.all_productos
            QtCore.QTimer.singleShot(0, self._update_pagination_buttons)
        
        print(f"--- Chunk de {len(chunk)} cargado. Total: {len(self.all_productos)}")

    def _on_streaming_finished(self):
        """Callback cuando termina el streaming de productos."""
        self._stop_inventory_loader_animation()
        print(f"Streaming de inventario finalizado: {len(self.all_productos)} productos cargados")
        self.total_products = self.all_productos
        self._update_pagination_buttons()
        self.refresh_smart_inventory_panel(force=True)

    def _on_streaming_error(self, error_msg):
        """Callback en caso de error."""
        self._stop_inventory_loader_animation()
        print(f"Error en streaming: {error_msg}")
        
        # Limpiar grid
        while self.products_grid.count():
            item = self.products_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Mostrar error
        error_label = QLabel(f"Error al cargar: {error_msg}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #d32f2f;
                padding: 40px;
            }
        """)
        self.products_grid.addWidget(error_label, 0, 0)
    
    def update_inventory_gallery(self, refresh_smart=True):
        """Actualiza la galerÃ­a de inventario desde el cache.
        
        Ã°Å¸Å¡â‚¬ OPTIMIZACIÃƒâ€œN:
        - Usa cache pre-cargado con streaming (no bloquea UI)
        - BÃºsqueda/filtrado rÃ¡pido desde cache local
        """
        self._stop_inventory_loader_animation()
        # Limpiar el grid de productos
        while self.products_grid.count():
            item = self.products_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Limpiar galer?a anterior
        self.product_table.setRowCount(0)

        # Usar total_products si tiene resultados, sino usar cache
        if self.total_products is not None and len(self.total_products) > 0:
            productos = self.total_products
        elif self.all_productos:
            productos = self.all_productos
        else:
            productos = []

        if not productos and getattr(self, "_initial_data_loading", False):
            self._show_inventory_loader(
                title="Cargando inventario",
                subtitle="Preparando productos y sincronizando datos."
            )
            self.btn_prev_page.setEnabled(False)
            self.btn_next_page.setEnabled(False)
            self.pagination_info.setText("Cargando inventario...")
            return
        
        if not productos:
            # Mostrar mensaje si no hay productos
            empty_label = QLabel("No hay productos en el inventario")
            empty_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #666;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                }
            """)
            empty_label.setAlignment(Qt.AlignCenter)
            self.products_grid.addWidget(empty_label, 0, 0)
            self.btn_prev_page.setEnabled(False)
            self.btn_next_page.setEnabled(False)
            self.pagination_info.setText("PÃ¡gina 1")
            return

        # Resetear pÃ¡gina cuando se actualiza la galerÃ­a
        self.current_page = 0
        
        # Mostrar pÃ¡gina actual
        self._display_current_page()
        # Actualizar botones de paginaciÃ³n
        self._update_pagination_buttons()
        if refresh_smart:
            self.refresh_smart_inventory_panel()

    def _create_smart_control_panel(self):
        panel = QGroupBox("Control inteligente")
        panel.setStyleSheet("""
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid #E8EDF3;
                border-radius: 6px;
                margin-top: 10px;
                padding: 8px;
            }
            QGroupBox::title {
                background-color: #FFFFFF;
                color: #374151;
                font-weight: 600;
                padding: 0 6px;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(6)

        self.smart_status_label = QLabel("Analiza demanda, stock y recetas usando tus propios datos.")
        self.smart_status_label.setWordWrap(True)
        self.smart_status_label.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        layout.addWidget(self.smart_status_label)

        self.smart_summary_card = self._create_smart_info_card(
            "Sugerencia de hoy",
            "La IA te dira en lenguaje natural que accion conviene tomar con tu inventario."
        )
        layout.addWidget(self.smart_summary_card["frame"])
        try:
            self.smart_summary_card["body"].clicked.connect(lambda: self._apply_smart_product_focus("summary"))
        except Exception:
            pass

        self.smart_facts_frame = QFrame()
        self.smart_facts_frame.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #EDF1F5;
                border-radius: 4px;
            }
            QLabel {
                background: transparent;
            }
        """)
        facts_layout = QGridLayout(self.smart_facts_frame)
        facts_layout.setContentsMargins(10, 8, 10, 8)
        facts_layout.setHorizontalSpacing(14)
        facts_layout.setVerticalSpacing(6)
        self.smart_fact_labels = {}
        fact_specs = [
            ("risk7", "Riesgo 7 dias"),
            ("dead", "Stock inmovil"),
            ("leader", "Producto lider"),
            ("ticket", "Ticket reciente"),
            ("margin", "Margen reciente"),
            ("stock", "Sin stock / bajo"),
        ]
        for idx, (key, label_text) in enumerate(fact_specs):
            row = idx % 3
            col = (idx // 3) * 2

            label = QLabel(label_text)
            label.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 600;")
            value = ClickableInfoLabel("--")
            value.setCursor(Qt.PointingHandCursor)
            value.setStyleSheet("color: #111827; font-size: 10px; font-weight: 500;")
            value.setWordWrap(True)
            value.clicked.connect(lambda _key=key: self._apply_smart_product_focus(_key))

            facts_layout.addWidget(label, row, col)
            facts_layout.addWidget(value, row, col + 1)
            self.smart_fact_labels[key] = value

        layout.addWidget(self.smart_facts_frame)

        self.smart_source_label = QLabel("Fuente: analisis local")
        self.smart_source_label.setWordWrap(True)
        self.smart_source_label.setStyleSheet("color: #9CA3AF; font-size: 9px; font-weight: 600;")
        layout.addWidget(self.smart_source_label)

        self.btn_smart_refresh = QPushButton("Analizar ahora")
        self.btn_smart_refresh.setMinimumHeight(30)
        self.btn_smart_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_smart_refresh.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #334155;
                border: 1px solid #D7DFEA;
                border-radius: 5px;
                font-weight: 600;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
            }
            QPushButton:disabled {
                background-color: #F8FAFC;
                color: #94A3B8;
                border: 1px solid #E2E8F0;
            }
        """)
        self.btn_smart_refresh.clicked.connect(lambda: self.refresh_smart_inventory_panel(force=True))
        layout.addWidget(self.btn_smart_refresh)

        return panel

    def _create_smart_info_card(self, title, body):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FCFDFE;
                border: 1px solid #E8EDF3;
                border-radius: 5px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(3)

        title_label = QLabel(str(title or ""))
        title_label.setStyleSheet("color: #334155; font-size: 10px; font-weight: 700;")
        title_label.setWordWrap(True)

        body_label = ClickableInfoLabel(str(body or ""))
        body_label.setCursor(Qt.PointingHandCursor)
        body_label.setStyleSheet("color: #334155; font-size: 11px; font-weight: 400; line-height: 1.35;")
        body_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(body_label)
        return {"frame": frame, "title": title_label, "body": body_label}

    def _set_smart_card_content(self, card, title, body, tone="info"):
        if not isinstance(card, dict):
            return

        colors = {
            "info": "#CBD5E1",
            "success": "#D1FAE5",
            "warning": "#FEF3C7",
            "danger": "#FEE2E2",
            "neutral": "#E5E7EB",
        }
        accent = colors.get(str(tone or "info"), colors["info"])

        frame = card.get("frame")
        title_label = card.get("title")
        body_label = card.get("body")

        if frame is not None:
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #FCFDFE;
                    border: 1px solid {accent};
                    border-radius: 5px;
                }}
            """)
        if title_label is not None:
            title_label.setText(str(title or ""))
        if body_label is not None:
            body_label.setText(str(body or ""))

    def _set_smart_fact_value(self, key, value):
        labels = getattr(self, "smart_fact_labels", {}) or {}
        label = labels.get(str(key or "").strip())
        if label is not None:
            label.setText(str(value or "--"))

    def _set_smart_focus_target(self, key, title, items):
        focus_targets = getattr(self, "_smart_focus_targets", None)
        if not isinstance(focus_targets, dict):
            focus_targets = {}
            self._smart_focus_targets = focus_targets
        focus_targets[str(key or "").strip()] = {
            "title": str(title or "").strip(),
            "items": list(items or []),
        }

    def _resolve_smart_focus_products(self, items):
        productos = list(self.all_productos or [])
        if not productos:
            return []

        by_code = {}
        by_name = {}
        for producto in productos:
            if not isinstance(producto, dict):
                continue
            code = str(producto.get("codigo") or "").strip().upper()
            name = str(producto.get("nombre") or "").strip().upper()
            if code and code not in by_code:
                by_code[code] = producto
            if name and name not in by_name:
                by_name[name] = producto

        resolved = []
        seen = set()
        for item in items or []:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip().upper()
            name = str(item.get("name") or "").strip().upper()
            producto = by_code.get(code) if code else None
            if producto is None and name:
                producto = by_name.get(name)
            if producto is None:
                continue
            key = code or name
            if key in seen:
                continue
            seen.add(key)
            resolved.append(producto)
        return resolved

    def _clear_smart_product_focus(self):
        self._smart_focus_active_key = ""
        self._smart_focus_active_title = ""
        try:
            if hasattr(self, "smart_status_label"):
                self.smart_status_label.setText(str(getattr(self, "_smart_status_default_text", "") or ""))
            if hasattr(self, "smart_source_label"):
                self.smart_source_label.setText(str(getattr(self, "_smart_source_default_text", "") or ""))
        except Exception:
            pass
        try:
            self.apply_inventory_filters()
        except Exception:
            self.total_products = list(self.all_productos or [])
            self.current_page = 0
            self.update_inventory_gallery()
            self._update_pagination_buttons()

    def _apply_smart_product_focus(self, key):
        key = str(key or "").strip()
        target = dict((getattr(self, "_smart_focus_targets", {}) or {}).get(key) or {})
        items = list(target.get("items") or [])
        title = str(target.get("title") or "analisis").strip()

        if not items:
            QtWidgets.QMessageBox.information(self, "Sin resultados", "No hay productos afectados para ese analisis.")
            return

        if self._smart_focus_active_key == key:
            self._clear_smart_product_focus()
            return

        productos = self._resolve_smart_focus_products(items)
        if not productos:
            QtWidgets.QMessageBox.information(self, "Sin resultados", "No pude ubicar esos productos en el inventario actual.")
            return

        self._smart_focus_active_key = key
        self._smart_focus_active_title = title

        try:
            if hasattr(self, "side_search_entry"):
                self.side_search_entry.blockSignals(True)
                self.side_search_entry.clear()
                self.side_search_entry.blockSignals(False)
            if hasattr(self, "side_section_combo"):
                self.side_section_combo.blockSignals(True)
                self.side_section_combo.setCurrentIndex(0)
                self.side_section_combo.blockSignals(False)
        except Exception:
            pass

        self.total_products = productos
        self.current_page = 0
        self.update_inventory_gallery()
        self._update_pagination_buttons()
        try:
            self.smart_status_label.setText(f"Mostrando productos afectados: {title}. Pulsa de nuevo para volver a la vista normal.")
        except Exception:
            pass

    def _inventory_signature_for_insights(self):
        productos = []
        for producto in list(self.all_productos or []):
            if not isinstance(producto, dict):
                continue
            nombre = str(producto.get("nombre") or producto.get("codigo") or "").strip().upper()
            try:
                stock = round(float(producto.get("stock", 0) or 0), 2)
            except Exception:
                stock = 0.0
            productos.append((nombre, stock))
        productos.sort()
        return tuple(productos)

    def refresh_smart_inventory_panel(self, force=False):
        if not _is_qt_object_alive(self):
            return
        if not _is_alive_widget_attr(self, "smart_status_label"):
            return

        try:
            active_ctx = get_effective_branch_context(self.username) or {}
            branch_code = str(active_ctx.get("code", "")).strip().upper()
        except Exception:
            branch_code = ""

        signature = (branch_code, self._inventory_signature_for_insights())
        if not force and signature == self._smart_inventory_signature:
            return

        if self._insights_thread is not None and self._insights_thread.isRunning():
            self._queued_insights_refresh = True
            return

        self._insights_request_id += 1
        request_id = self._insights_request_id
        self._running_inventory_signature = signature
        self._queued_insights_refresh = False
        self.smart_status_label.setText("Consultando JSON remotos y analizando demanda...")

        if _is_alive_widget_attr(self, "btn_smart_refresh"):
            self.btn_smart_refresh.setEnabled(False)
            self.btn_smart_refresh.setText("Analizando...")

        worker = InventoryInsightsThread(self.username, branch_code=branch_code)
        self._insights_thread = worker
        worker.finished.connect(lambda result, rid=request_id: self._on_inventory_insights_ready(rid, result))
        worker.error.connect(lambda error_msg, rid=request_id: self._on_inventory_insights_error(rid, error_msg))
        worker.finished.connect(lambda _result=None, rid=request_id, current_worker=worker: self._on_inventory_insights_finished(rid, current_worker))
        worker.error.connect(lambda _error=None, rid=request_id, current_worker=worker: self._on_inventory_insights_finished(rid, current_worker))
        worker.start()

    def _on_inventory_insights_ready(self, request_id, result):
        if request_id != self._insights_request_id:
            return
        if not _is_qt_object_alive(self):
            return
        if not _is_alive_widget_attr(self, "smart_status_label"):
            return

        result = result if isinstance(result, dict) else {}
        self._smart_inventory_signature = self._running_inventory_signature
        source_label = "Nube"
        codes = result.get("cloud_codes") or []
        if result.get("cloud_source") == "cloud_branch" and codes:
            source_label = f"Nube ({codes[0]})"
        elif result.get("cloud_source") == "cloud_global" and codes:
            source_label = f"Nube ({len(codes)} origenes)"
        provider = str(result.get("ai_summary_provider") or "local").strip().lower()
        provider_label = "Mistral" if provider == "mistral" else "Resumen local"
        self._smart_status_default_text = f"{source_label}: {str(result.get('status_text') or 'Analisis completado.')}"
        self.smart_status_label.setText(self._smart_status_default_text)
        if _is_alive_widget_attr(self, "smart_source_label"):
            self._smart_source_default_text = f" "
            self.smart_source_label.setText(self._smart_source_default_text)

        restock_count = int(result.get("restock_count") or 0)
        rx_body = str(result.get("rx_body") or "")
        summary_tone = "danger" if restock_count > 0 else ("success" if "terminaron en venta" in rx_body else "info")

        self._set_smart_card_content(
            self.smart_summary_card,
            "Sugerencia de hoy",
            result.get("ai_summary_body") or "No se pudo generar un resumen en este momento.",
            tone=summary_tone
        )
        self._set_smart_focus_target("summary", "sugerencia de hoy", result.get("focus_summary_items") or [])

        self._set_smart_fact_value("risk7", f"{int(result.get('at_risk_7_count') or 0)} en 7d / {int(result.get('at_risk_30_count') or 0)} en 30d")
        self._set_smart_focus_target("risk7", "riesgo de quiebre", result.get("focus_risk_items") or [])
        dead_count = int(result.get("dead_stock_count") or 0)
        dead_text = f"{dead_count} producto(s)"
        dead_value = float(result.get("dead_stock_value") or 0.0)
        if dead_value > 0:
            dead_text += f" | S/. {dead_value:,.0f}"
        self._set_smart_fact_value("dead", dead_text)
        self._set_smart_focus_target("dead", "stock inmovil", result.get("focus_dead_items") or [])

        leader_name = str(result.get("top_seller_name") or "").strip() or "Sin lider claro"
        leader_units = int(round(float(result.get("top_seller_units") or 0.0)))
        leader_text = leader_name if leader_units <= 0 else f"{leader_name} ({leader_units} u.)"
        self._set_smart_fact_value("leader", leader_text)
        self._set_smart_focus_target("leader", "producto lider", result.get("focus_leader_items") or [])

        avg_ticket = float(result.get("average_ticket") or 0.0)
        self._set_smart_fact_value("ticket", f"S/. {avg_ticket:,.2f}" if avg_ticket > 0 else "Sin ventas recientes")
        self._set_smart_focus_target("ticket", "productos que mas mueven ticket", result.get("focus_ticket_items") or [])

        margin = float(result.get("estimated_recent_margin") or 0.0)
        self._set_smart_fact_value("margin", f"S/. {margin:,.2f}" if margin > 0 else "No estimable")
        self._set_smart_focus_target("margin", "productos con mejor margen", result.get("focus_margin_items") or [])

        zero_stock = int(result.get("zero_stock_count") or 0)
        low_stock = int(result.get("low_stock_count") or 0)
        self._set_smart_fact_value("stock", f"{zero_stock} sin stock | {low_stock} bajo")
        self._set_smart_focus_target("stock", "alertas de stock", result.get("focus_stock_items") or [])

    def _on_inventory_insights_error(self, request_id, error_msg):
        if request_id != self._insights_request_id:
            return
        if not _is_qt_object_alive(self):
            return
        if not _is_alive_widget_attr(self, "smart_status_label"):
            return

        self._smart_status_default_text = "No se pudo consultar los JSON remotos para el control inteligente."
        self.smart_status_label.setText(self._smart_status_default_text)
        if _is_alive_widget_attr(self, "smart_source_label"):
            self._smart_source_default_text = "Fuente del consejo: sin datos"
            self.smart_source_label.setText(self._smart_source_default_text)
        self._set_smart_card_content(
            self.smart_summary_card,
            "Sugerencia de hoy",
            f"No pude analizar la nube ahora. Error: {error_msg}",
            tone="warning"
        )
        self._smart_focus_targets = {}
        self._smart_focus_active_key = ""
        self._smart_focus_active_title = ""
        for key in ("risk7", "dead", "leader", "ticket", "margin", "stock"):
            self._set_smart_fact_value(key, "--")

    def _on_inventory_insights_finished(self, request_id, worker):
        if self._insights_thread is worker:
            self._insights_thread = None

        try:
            if worker is not None:
                worker.deleteLater()
        except Exception:
            pass

        if _is_qt_object_alive(self) and _is_alive_widget_attr(self, "btn_smart_refresh"):
            self.btn_smart_refresh.setEnabled(True)
            self.btn_smart_refresh.setText("Analizar ahora")

        if request_id != self._insights_request_id:
            return

        if self._queued_insights_refresh:
            self._queued_insights_refresh = False
            self._smart_inventory_signature = None
            if _is_qt_object_alive(self):
                QtCore.QTimer.singleShot(0, lambda: _is_qt_object_alive(self) and self.refresh_smart_inventory_panel(force=True))

    def _filter_products_python(self, productos, search_term, sort_mode):
        """Filtrado en Python puro (fallback si no hay DLL)."""
        # Aplicar filtro de bÃºsqueda
        if search_term:
            productos = [p for p in productos if
                       search_term.lower() in str(p.get('nombre', '')).lower() or
                       search_term.lower() in str(p.get('marca', '')).lower()]

        # Ordenar productos
        if sort_mode == 'MÃ¡s nuevo primero':
            productos.sort(key=lambda x: str(x.get('created_at')) if x.get('created_at') is not None else '', reverse=True)
        elif sort_mode == 'MÃ¡s viejo primero':
            productos.sort(key=lambda x: str(x.get('created_at')) if x.get('created_at') is not None else '')
        elif sort_mode == 'AlfabÃ©tico A-Z':
            productos.sort(key=lambda x: str(x.get('nombre', '')).lower())
        elif sort_mode == 'Precio: Menor a Mayor':
            def get_precio(x):
                try:
                    return float(x.get('precio', 0) or 0)
                except (ValueError, TypeError):
                    return 0.0
            productos.sort(key=get_precio)
        elif sort_mode == 'Precio: Mayor a Menor':
            def get_precio_desc(x):
                try:
                    return float(x.get('precio', 0) or 0)
                except (ValueError, TypeError):
                    return 0.0
            productos.sort(key=get_precio_desc, reverse=True)
        elif sort_mode == 'Stock: Mayor a Menor':
            def get_stock(x):
                try:
                    return int(float(x.get('stock', 0) or 0))
                except (ValueError, TypeError):
                    return 0
            productos.sort(key=get_stock, reverse=True)
            
        return productos
    
    def _display_current_page(self):
        """Muestra los productos de la pÃ¡gina actual."""
        # Limpiar grid
        while self.products_grid.count():
            item = self.products_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Usar total_products si estÃ¡ filtrado, sino usar all_productos
        productos_a_mostrar = self.total_products if self.total_products is not None else self.all_productos
        
        # Calcular rango de productos para esta pÃ¡gina
        start_idx = self.current_page * self.products_per_page
        end_idx = start_idx + self.products_per_page
        productos_pagina = productos_a_mostrar[start_idx:end_idx]
        index_offset = 0
        
        if not productos_pagina and not isinstance(getattr(self, "_pending_product_creation", None), dict):
            empty_label = QLabel("No hay productos en esta pÃ¡gina")
            empty_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #666;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                }
            """)
            empty_label.setAlignment(Qt.AlignCenter)
            self.products_grid.addWidget(empty_label, 0, 0)
            return
        
        # Configurar el diseÃ±o de la galerÃ­a
        self.products_grid.setSpacing(20)
        self.products_grid.setContentsMargins(20, 20, 20, 20)
        
        # Agregar productos en la cuadrÃ­cula
        pending_product = getattr(self, "_pending_product_creation", None)
        if self.current_page == 0 and isinstance(pending_product, dict):
            skeleton_card = self._create_product_creation_skeleton_widget(
                str(pending_product.get("nombre", "") or "").strip()
            )
            self.products_grid.addWidget(skeleton_card, 0, 0)
            index_offset = 1
        for index, producto in enumerate(productos_pagina):
            display_index = index + index_offset
            row = display_index // self.grid_columns
            col = display_index % self.grid_columns
            card = ProductCard(producto, self)
            card.clicked.connect(self.on_product_card_clicked)
            card.item_added.connect(self.on_item_added_to_cart)
            self.products_grid.addWidget(card, row, col)
            
            # AÃ±adir a la vista de tabla
            row_index = self.product_table.rowCount()
            self.product_table.insertRow(row_index)
            
            codigo_producto = str(producto.get('codigo', '') or '').strip()
            nombre_producto = str(producto.get('nombre', '') or '').strip()
            nombre_display = f"{codigo_producto} - {nombre_producto}" if codigo_producto else nombre_producto
            nombre_item = QTableWidgetItem(nombre_display)
            # Convertir strings a nÃºmeros para costo/venta/stock
            try:
                costo_val = float(producto.get('costo', 0) or 0)
            except (ValueError, TypeError):
                costo_val = 0.0
            try:
                venta_val = float(producto.get('venta', 0) or 0)
            except (ValueError, TypeError):
                venta_val = 0.0
            try:
                stock_val = int(float(producto.get('stock', 0) or 0))
            except (ValueError, TypeError):
                stock_val = 0
            costo_item = QTableWidgetItem(f"S/ {costo_val:.2f}")
            venta_item = QTableWidgetItem(f"S/ {venta_val:.2f}")
            stock_item = QTableWidgetItem(str(stock_val))
            material_item = QTableWidgetItem(producto.get('material', ''))
            marca_item = QTableWidgetItem(producto.get('marca', ''))
            
            self.product_table.setItem(row_index, 0, nombre_item)
            self.product_table.setItem(row_index, 1, costo_item)
            self.product_table.setItem(row_index, 2, venta_item)
            self.product_table.setItem(row_index, 3, stock_item)
            self.product_table.setItem(row_index, 4, material_item)
            self.product_table.setItem(row_index, 5, marca_item)
            
            # Agregar botones de acciÃ³n
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            btn_editar = QPushButton()
            btn_editar.setIcon(QIcon(os.path.join(BASE_DIR, "images", "edit.svg")))
            btn_editar.setIconSize(QSize(16, 16))
            btn_editar.setToolTip("Editar producto")
            btn_editar.clicked.connect(lambda checked, p=producto: self.abrir_edicion_producto(p))
            btn_editar.setStyleSheet("""
                QPushButton {
                    background-color: #E3F2FD;
                    border: 1px solid #BBDEFB;
                    border-radius: 12px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
            """)
            
            btn_eliminar = QPushButton()
            btn_eliminar.setIcon(QIcon(os.path.join(BASE_DIR, "images", "delete.svg")))
            btn_eliminar.setIconSize(QSize(16, 16))
            btn_eliminar.setToolTip("Eliminar producto")
            btn_eliminar.clicked.connect(lambda checked, p=dict(producto): self.eliminar_producto_galeria(p))
            btn_eliminar.setStyleSheet("""
                QPushButton {
                    background-color: #FFEBEE;
                    border: 1px solid #FFCDD2;
                    border-radius: 12px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                }
            """)
            
            actions_layout.addWidget(btn_editar)
            actions_layout.addWidget(btn_eliminar)
            actions_layout.addStretch()
            
            self.product_table.setCellWidget(row_index, 6, actions_widget)
            
            # Colorear fila segÃºn el stock
            stock = producto.get('stock', 0)
            stock_color = self.get_stock_color(stock)
            for col in range(self.product_table.columnCount()):
                if col != 6:  # No colorear la columna de acciones
                    item = self.product_table.item(row_index, col)
                    if item:
                        item.setBackground(QtGui.QColor(stock_color))

    def get_stock_color(self, stock):
        """Retorna el color correspondiente al nivel de stock."""
        try:
            stock_val = int(float(stock or 0))
        except (ValueError, TypeError):
            stock_val = 0
        if stock_val <= 0:
            return "#FF5252"  # Rojo para agotado
        elif stock_val <= 5:
            return "#FFA726"  # Naranja para bajo stock
        elif stock_val <= 10:
            return "#FFD740"  # Amarillo para stock medio
        else:
            return "#66BB6A"  # Verde para stock disponible

    def _apply_product_skeleton_tone(self, card, shade: str, border: str):
        if not _is_qt_object_alive(card):
            return
        card.setStyleSheet(f"""
            QFrame#CreatingProductSkeleton {{
                background: #FFFFFF;
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QFrame[skeleton_block=\"true\"] {{
                background: {shade};
                border: none;
                border-radius: 8px;
            }}
        """)

    def _create_product_creation_skeleton_widget(self, product_name: str = ""):
        card = QFrame()
        card.setObjectName("CreatingProductSkeleton")
        card.setMinimumSize(240, 330)
        card.setMaximumWidth(320)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        image_block = QFrame()
        image_block.setFixedHeight(150)
        image_block.setProperty("skeleton_block", True)

        title_block = QLabel("Creando producto...")
        title_block.setStyleSheet("font-size: 16px; font-weight: 700; color: #334155; background: transparent;")

        name_block = QLabel(product_name or "Preparando datos del producto")
        name_block.setWordWrap(True)
        name_block.setStyleSheet("font-size: 12px; color: #64748b; background: transparent;")

        line_one = QFrame()
        line_one.setFixedHeight(16)
        line_one.setProperty("skeleton_block", True)

        line_two = QFrame()
        line_two.setFixedHeight(16)
        line_two.setMaximumWidth(120)
        line_two.setProperty("skeleton_block", True)

        footer = QLabel("Guardando en inventario...")
        footer.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent;")

        layout.addWidget(image_block)
        layout.addWidget(title_block)
        layout.addWidget(name_block)
        layout.addSpacing(4)
        layout.addWidget(line_one)
        layout.addWidget(line_two)
        layout.addStretch(1)
        layout.addWidget(footer)

        self._apply_product_skeleton_tone(card, "#F1F5F9", "#E2E8F0")

        anim = QVariantAnimation(card)
        anim.setDuration(900)
        anim.setLoopCount(-1)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def _on_value_changed(value):
            start = QtGui.QColor("#F1F5F9")
            end = QtGui.QColor("#E2E8F0")
            factor = float(value or 0.0)
            r = int(start.red() + (end.red() - start.red()) * factor)
            g = int(start.green() + (end.green() - start.green()) * factor)
            b = int(start.blue() + (end.blue() - start.blue()) * factor)
            self._apply_product_skeleton_tone(card, QtGui.QColor(r, g, b).name(), "#E2E8F0")

        anim.valueChanged.connect(_on_value_changed)
        anim.start()
        self._pending_product_skeleton_anim = anim
        return card

    def _begin_product_creation_skeleton(self, product_name: str = ""):
        self._pending_product_creation = {
            "nombre": str(product_name or "").strip(),
            "started_at": datetime.datetime.now().timestamp(),
        }
        try:
            self.update_inventory_gallery()
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass

    def _end_product_creation_skeleton(self):
        pending = getattr(self, "_pending_product_creation", None)
        started_at = 0.0
        try:
            if isinstance(pending, dict):
                started_at = float(pending.get("started_at", 0) or 0)
        except Exception:
            started_at = 0.0

        if started_at > 0:
            elapsed_ms = max(0, int((datetime.datetime.now().timestamp() - started_at) * 1000))
            remaining_ms = max(0, 650 - elapsed_ms)
            if remaining_ms > 0:
                QtCore.QTimer.singleShot(remaining_ms, self._end_product_creation_skeleton)
                return

        self._pending_product_creation = None
        try:
            anim = getattr(self, "_pending_product_skeleton_anim", None)
            if anim is not None:
                anim.stop()
        except Exception:
            pass
        self._pending_product_skeleton_anim = None
        try:
            self.update_inventory_gallery()
        except Exception:
            pass

    def create_product_card(self, prod):
        # Crear un efecto de sombra para la tarjeta
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QtGui.QColor(0, 0, 0, 25))

        card = QGroupBox()
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QtGui.QColor(0, 0, 0, 15))
        card.setGraphicsEffect(shadow)
        
        card.setStyleSheet("""
            QGroupBox {
                background: white;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 4px;
                margin: 6px;
            }
            QGroupBox:hover {
                border: 1px solid rgba(0, 0, 0, 0.12);
                background: #FFFFFF;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(0)
        card_layout.setContentsMargins(0, 0, 0, 12)

        image_label = QLabel()
        image_label.setMaximumSize(220, 220)
        image_label.setMinimumSize(150, 150)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                background: white;
                border-radius: 4px 4px 0 0;
                padding: 8px;
            }
        """)

        image_path = prod.get('image_path') or prod.get('imagen')
        pixmap = None

        def _pixmap_from_path(p):
            if not p:
                return None
            try:
                if os.path.exists(p):
                    pm = QtGui.QPixmap(p)
                    if not pm.isNull():
                        return pm
            except Exception:
                return None
            return None

        # 1) Intentar usar la ruta guardada en el producto
        pixmap = _pixmap_from_path(image_path)

        # 2) Si no existe, buscar en la carpeta de imÃ¡genes del proyecto
        if pixmap is None:
            try:
                # Nombre normalizado del producto para buscar
                product_name = prod.get('nombre', '').lower().replace(' ', '_')
                for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                    img_path = os.path.join(BASE_DIR, 'images', product_name + ext)
                    if os.path.exists(img_path):
                        pixmap = QtGui.QPixmap(img_path)
                        break
            except Exception:
                pass

        # 3) Si aÃºn no hay imagen, usar placeholder
        if pixmap is None:
            placeholder_path = os.path.join(BASE_DIR, 'images', 'placeholder.png')
            if os.path.exists(placeholder_path):
                pixmap = QtGui.QPixmap(placeholder_path)

        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
        else:
            image_label.setText("Sin imagen")
        
        card_layout.addWidget(image_label)

        info_label = QLabel()
        # Preparar el color del stock y su mensaje
        stock = prod.get('stock', 0)
        stock_color = self.get_stock_color(stock)
        stock_status = "AGOTADO" if stock <= 0 else "BAJO" if stock <= 5 else "MEDIO" if stock <= 10 else "DISPONIBLE"
        
        # Definir estados de stock y sus etiquetas
        stock_status = "Agotado" if stock <= 0 else "Bajo" if stock <= 5 else "Medio" if stock <= 10 else "Disponible"
        
        info_html = [f"""
            <div style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 12px 16px;'>
                <div style='border-bottom: 1px solid rgba(0, 0, 0, 0.06); padding-bottom: 12px;'>
                    <div style='font-size: 14px; font-weight: 500; color: #1a1a1a; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                        {prod.get('nombre', 'Sin nombre')}
                    </div>
                    <div style='font-size: 13px; color: rgba(0, 0, 0, 0.45); letter-spacing: -0.1px;'>
                        {prod.get('marca', 'Sin marca')}
                    </div>
                </div>
                
                <div style='display: flex; justify-content: space-between; align-items: flex-end; margin-top: 12px;'>
                    <div style='display: flex; align-items: baseline; gap: 8px;'>
                        <div style='font-size: 17px; font-weight: 600; color: #111111; letter-spacing: -0.2px;'>
                            S/ {prod.get('venta', 0):.2f}
                        </div>
                        <div style='font-size: 12px; color: rgba(0, 0, 0, 0.45);'>
                            Costo: S/ {prod.get('costo', 0):.2f}
                        </div>
                    </div>
                    
                    <div style='display: flex; align-items: center; gap: 4px; background: rgba(0, 0, 0, 0.02); 
                               padding: 4px 8px; border-radius: 3px; border: 1px solid rgba(0, 0, 0, 0.06);'>
                        <div style='
                            width: 6px;
                            height: 6px;
                            border-radius: 50%;
                            background-color: {stock_color};
                        '></div>
                        <span style='font-size: 12px; color: rgba(0, 0, 0, 0.65); font-weight: 500;'>
                            {stock}
                        </span>
                    </div>
                </div>
                
                {f'''
                <div style='margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap;'>
                    <span style='
                        font-size: 12px;
                        color: #7f8c8d;
                        background-color: #f8f9fa;
                        padding: 4px 8px;
                        border-radius: 4px;
                        display: inline-flex;
                        align-items: center;
                    '>
                        <span style="margin-right: 4px;">Ã°Å¸ÂÂ·Ã¯Â¸Â</span>
                        {prod.get("material")}
                    </span>
                </div>
                ''' if prod.get('material') else ''}
            </div>
        """]
        info_label.setText("".join(info_html))
        info_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border-radius: 4px;
                padding: 8px;
                margin-top: 8px;
            }
        """)
        card_layout.addWidget(info_label)

        # Crear un widget contenedor para la imagen y los botones
        image_container = QWidget()
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        image_container_layout.setSpacing(0)
        
        # Contenedor para los botones con posiciÃ³n absoluta
        buttons_container = QWidget(image_container)
        buttons_container.setObjectName("buttonsContainer")
        buttons_container.setFixedHeight(35)
        buttons_container.setFixedWidth(70)  # Ancho fijo para los dos botones
        
        # Asegurar que el contenedor de botones siempre estÃ© en la esquina superior derecha
        class ButtonOverlay(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.hide()
            
            def resizeEvent(self, event):
                if self.parentWidget():
                    self.move(self.parentWidget().width() - self.width() - 5, 5)
                super().resizeEvent(event)
        
        buttons_container = ButtonOverlay(image_container)
        
        btn_editar = QPushButton()
        btn_editar.setIcon(QIcon(os.path.join(BASE_DIR, "images", "edit.svg")))
        btn_editar.setIconSize(QSize(16, 16))
        btn_editar.setToolTip("Editar producto")
        btn_editar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_editar.setFixedSize(28, 28)
        btn_editar.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 4px;
                padding: 4px;
                min-width: 28px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-color: rgba(0, 0, 0, 0.12);
            }
            QPushButton:pressed {
                background-color: #eeeeee;
            }
        """)
        btn_editar.clicked.connect(lambda _, p=prod: self.abrir_edicion_producto(p))
        
        btn_eliminar = QPushButton()
        btn_eliminar.setIcon(QIcon(os.path.join(BASE_DIR, "images", "delete.svg")))
        btn_eliminar.setIconSize(QSize(16, 16))
        btn_eliminar.setToolTip("Eliminar producto")
        btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar.setFixedSize(28, 28)
        btn_eliminar.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 4px;
                padding: 4px;
                min-width: 28px;
                min-height: 28px;
                margin-left: 4px;
            }
            QPushButton:hover {
                background-color: #fff1f0;
                border-color: #ffa39e;
            }
            QPushButton:pressed {
                background-color: #ffece8;
                border-color: #ff7875;
            }
        """)
        btn_eliminar.clicked.connect(lambda _, p=dict(prod): self.eliminar_producto_galeria(p))

        # BotÃ³n para aÃ±adir stock
        btn_add_stock = QPushButton()
        btn_add_stock.setIcon(QIcon(os.path.join(BASE_DIR, "images", "add-stock.svg")))
        btn_add_stock.setIconSize(QSize(16, 16))
        btn_add_stock.setToolTip("AÃ±adir stock")
        btn_add_stock.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_stock.clicked.connect(lambda _, p=prod: self.abrir_dialogo_add_stock(p))
        btn_add_stock.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 4px;
                padding: 4px;
                min-width: 28px;
                min-height: 28px;
                margin-left: 4px;
            }
            QPushButton:hover {
                background-color: #e6f7ff;
                border-color: #91d5ff;
            }
            QPushButton:pressed {
                background-color: #bae7ff;
                border-color: #69c0ff;
            }
        """)

        # Layout horizontal para los botones
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(4)
        buttons_layout.addWidget(btn_editar)
        buttons_layout.addWidget(btn_add_stock)
        buttons_layout.addWidget(btn_eliminar)
        buttons_layout.addStretch()
        
        buttons_container.hide()
        
        # Crear una subclase de QWidget para manejar los eventos del mouse correctamente
        class HoverContainer(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.buttons = None
            
            def enterEvent(self, event):
                if self.buttons:
                    self.buttons.show()
                    self.buttons.raise_()
                super().enterEvent(event)
            
            def leaveEvent(self, event):
                if self.buttons:
                    self.buttons.hide()
                super().leaveEvent(event)
        
        # Usar el contenedor personalizado
        hover_container = HoverContainer(image_container)
        hover_layout = QVBoxLayout(hover_container)
        hover_layout.setContentsMargins(0, 0, 0, 0)
        hover_layout.setSpacing(0)
        hover_layout.addWidget(image_label)
        
        # Configurar el contenedor de botones
        buttons_container.setParent(hover_container)
        buttons_container.show()
        hover_container.buttons = buttons_container
        
        # Agregar el contenedor al layout principal
        image_container_layout.addWidget(hover_container)
        
        # Agregar el contenedor de imagen al layout principal
        card_layout.addWidget(image_container)

        return card

    def open_add_product_dialog(self):
        """Abre el diÃ¡logo para crear un nuevo producto y lo guarda si es aceptado."""
        self._sync_branch_context_from_parent()
        # Ã°Å¸â€ºÂ¡Ã¯Â¸Â VERIFICAR PERMISO: Solo puede crear si tiene permiso 'crear' en inventario
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('inventario', 'crear'):
                QMessageBox.warning(
                    self,
                    "Permiso Denegado",
                    "No tienes permiso para crear productos en el inventario."
                )
                return
        
        dialog = OpticalProductDialog(parent=self)
        dialog_result = dialog.exec_()
        self._refresh_side_section_combo()
        if dialog_result == QDialog.Accepted:
            # Obtener datos del producto
            product_data = dialog.get_product_data()
            seccion = self._normalize_section_value(
                product_data.get('categoria') or product_data.get('seccion')
            )
            
            try:

                # Crear carpeta de im?genes de productos si no existe
                user_dir = os.path.join("VISO", str(self.username))
                images_dir = os.path.join(user_dir, "product_images")
                if not os.path.exists(images_dir):
                    os.makedirs(images_dir, exist_ok=True)
                
                # Procesar imagen
                image_path = ''
                # Buscar en ambas claves por compatibilidad
                image_source = product_data.get('image_path') or product_data.get('imagen')
                if image_source:
                    try:
                        # Obtener el nombre del archivo original
                        original_file = image_source
                        file_extension = os.path.splitext(original_file)[1]
                        
                        # Generar nombre ?nico para la imagen
                        codigo_producto = product_data.get('codigo', 'producto')
                        image_filename = f"{codigo_producto}{file_extension}"
                        image_path = os.path.join(images_dir, image_filename)
                        
                        # Copiar la imagen a la carpeta de productos
                        if os.path.exists(original_file):
                            shutil.copy2(original_file, image_path)
                    except Exception as e:
                        print(f"Error al copiar imagen: {e}")
                        image_path = ''
                productos = cargar_productos(self.username) or []
                
                # Crear entrada del producto con estructura completa
                nuevo_producto = {
                    'codigo': product_data.get('codigo', ''),
                    'nombre': product_data.get('nombre', ''),
                    'marca': product_data.get('marca', ''),
                    'categoria': seccion,
                    'seccion': seccion,
                    'material': product_data.get('material', ''),
                    'talla': product_data.get('talla', ''),
                    'tipo_lente': product_data.get('tipo_lente', ''),
                    'colors': product_data.get('colors', []),
                    'stock': product_data.get('stock', 0),
                    'costo': product_data.get('costo', 0.0),
                    'venta': product_data.get('venta', 0.0),
                    'precio_regular': product_data.get('precio_regular', 0.0),
                    'caracteristicas': product_data.get('caracteristicas', {}),
                    'variantes': product_data.get('variantes', {}),
                    'image_path': image_path,
                    'created_at': __import__('datetime').datetime.now().isoformat()
                }
                
                if not agregar_producto(self.username, nuevo_producto):
                    raise ValueError("No se pudo agregar el producto (duplicado o error de archivo).")
                productos = cargar_productos(self.username) or []
                
                # Ã°Å¸â€Â¥ ACTUALIZAR CACHE LOCAL INMEDIATAMENTE
                self.all_productos = productos
                self.total_products = productos
                
                # Refrescar la galerÃ­a
                self.update_inventory_gallery()
                
                # Ã°Å¸â€â€ž DISPARAR REFRESH AUTOMÃTICO PARA SINCRONIZAR
                self.refresh_inventory_page()
                
                QMessageBox.information(self, "Éxito", "Producto creado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al guardar el producto: {str(e)}")

    def next_page(self):
        """Ir a la siguiente pÃ¡gina."""
        total_pages = (len(self.total_products) + self.products_per_page - 1) // self.products_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._display_current_page()
            self._update_pagination_buttons()
    
    def prev_page(self):
        """Ir a la pÃ¡gina anterior."""
        if self.current_page > 0:
            self.current_page -= 1
            self._display_current_page()
            self._update_pagination_buttons()
    
    def _update_pagination_buttons(self):
        """Actualiza el estado de los botones de paginaciÃ³n."""
        total_pages = (len(self.total_products) + self.products_per_page - 1) // self.products_per_page if self.total_products else 1
        
        # Actualizar etiqueta de pÃ¡gina
        self.pagination_info.setText(f"PÃ¡gina {self.current_page + 1} de {total_pages}")
        
        # Habilitar/deshabilitar botones
        self.btn_prev_page.setEnabled(self.current_page > 0)
        self.btn_next_page.setEnabled(self.current_page < total_pages - 1)

    def on_item_added_to_cart(self, product_data):
        """Maneja cuando un producto se agrega al carrito."""
        # Ã°Å¸â€ºÂ¡Ã¯Â¸Â VERIFICAR PERMISO: Solo puede agregar al carrito si tiene 'registrar' en ventas
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('ventas', 'registrar'):
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Permiso Denegado",
                    "No tienes permiso para registrar ventas."
                )
                return
        
        # Usar el nombre del producto como identificador Ãºnico (ya que los productos no tienen ID)
        product_name = product_data.get('nombre', '').strip()
        if not product_name:
            return
        
        # Si ya existe, aumentar cantidad
        if product_name in self.cart_items:
            self.cart_items[product_name]['cantidad'] = self.cart_items[product_name].get('cantidad', 1) + 1
        else:
            # Agregar nuevo producto al carrito
            self.cart_items[product_name] = {
                'nombre': product_name,
                'precio': float(product_data.get('venta', 0)),
                'cantidad': 1
            }
        
        # Actualizar tabla del carrito
        self.update_cart_table()

    def update_cart_table(self):
        """Actualiza la tabla del carrito con los items agregados."""
        if not self.cart_table:
            return
        
        # Limpiar tabla
        self.cart_table.setRowCount(0)
        
        # Si no hay items, no mostrar tabla
        if not self.cart_items:
            self.cart_table.hide()
            return
        
        # Mostrar tabla
        self.cart_table.show()
        
        # Agregar items a la tabla
        for idx, (product_id, item) in enumerate(self.cart_items.items()):
            self.cart_table.insertRow(idx)
            
            # Nombre del producto
            nombre_item = QTableWidgetItem(item.get('nombre', ''))
            nombre_item.setFlags(nombre_item.flags() & ~Qt.ItemIsEditable)
            
            # Cantidad (editable)
            cantidad_item = QTableWidgetItem(str(item.get('cantidad', 1)))
            
            # Precio unitario
            precio_item = QTableWidgetItem(f"S/ {item.get('precio', 0):.2f}")
            precio_item.setFlags(precio_item.flags() & ~Qt.ItemIsEditable)
            
            # Precio total
            total_precio = float(item.get('precio', 0)) * int(item.get('cantidad', 1))
            total_item = QTableWidgetItem(f"S/ {total_precio:.2f}")
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            
            self.cart_table.setItem(idx, 0, nombre_item)
            self.cart_table.setItem(idx, 1, cantidad_item)
            self.cart_table.setItem(idx, 2, precio_item)
            self.cart_table.setItem(idx, 3, total_item)

    def open_cart_enlarged(self):
        """Abre una ventana ampliada con la tabla del carrito."""
        if not self.cart_items:
            return
        
        # Crear ventana modal
        enlarged_window = QDialog(self)
        enlarged_window.setWindowTitle("Carrito de Compra - Vista Ampliada")
        enlarged_window.setGeometry(100, 100, 900, 600)
        enlarged_window.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
            }
        """)
        
        layout = QVBoxLayout(enlarged_window)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # T?tulo
        title = QLabel("Carrito de Compra")
        title.setStyleSheet("""
            QLabel {
                font-weight: 700;
                font-size: 18px;
                color: #191919;
            }
        """)
        layout.addWidget(title)
        
        # Tabla ampliada
        enlarged_table = QTableWidget()
        enlarged_table.setColumnCount(4)
        enlarged_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio", "Total"])
        enlarged_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f5f5f5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #191919;
                color: white;
                padding: 10px;
                border: none;
                font-weight: 700;
                font-size: 12px;
            }
        """)
        enlarged_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        enlarged_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        enlarged_table.setAlternatingRowColors(True)
        enlarged_table.setRowCount(len(self.cart_items))
        
        # Agregar items a la tabla ampliada
        total_general = 0
        for idx, (product_id, item) in enumerate(self.cart_items.items()):
            # Nombre del producto
            nombre_item = QTableWidgetItem(item.get('nombre', ''))
            nombre_item.setFlags(nombre_item.flags() & ~Qt.ItemIsEditable)
            
            # Cantidad
            cantidad_item = QTableWidgetItem(str(item.get('cantidad', 1)))
            
            # Precio unitario
            precio = float(item.get('precio', 0))
            precio_item = QTableWidgetItem(f"S/ {precio:.2f}")
            precio_item.setFlags(precio_item.flags() & ~Qt.ItemIsEditable)
            
            # Precio total
            cantidad = int(item.get('cantidad', 1))
            total_precio = precio * cantidad
            total_general += total_precio
            total_item = QTableWidgetItem(f"S/ {total_precio:.2f}")
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            
            enlarged_table.setItem(idx, 0, nombre_item)
            enlarged_table.setItem(idx, 1, cantidad_item)
            enlarged_table.setItem(idx, 2, precio_item)
            enlarged_table.setItem(idx, 3, total_item)
        
        layout.addWidget(enlarged_table)
        
        # Resumen
        summary_layout = QHBoxLayout()
        summary_layout.addStretch()
        
        total_label = QLabel(f"Total General: <b>S/ {total_general:.2f}</b>")
        total_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #191919;
                font-weight: 600;
            }
        """)
        summary_layout.addWidget(total_label)
        
        layout.addLayout(summary_layout)
        
        # Botones de acciones
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(10)
        action_buttons_layout.addStretch()
        
        btn_register = AnimatedLoaderButton("Ã°Å¸â€™Â¾ Registrar Venta")
        btn_register.setObjectName("primaryButton")
        btn_register.setMinimumWidth(150)
        btn_register.setMinimumHeight(40)
        btn_register.setStyleSheet("""
            QPushButton {
                background-color: #191919;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
            QPushButton:pressed {
                background-color: #0a0a0a;
            }
        """)
        btn_register.clicked.connect(lambda: self._register_sale_and_generate(btn_register, btn_generate, enlarged_window))
        # Ã°Å¸â€ºÂ¡Ã¯Â¸Â VERIFICAR PERMISO: Deshabilitar botÃ³n si no tiene 'registrar' en ventas
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('ventas', 'registrar'):
                btn_register.setEnabled(False)
                btn_register.setToolTip("No tienes permiso para registrar ventas")
        action_buttons_layout.addWidget(btn_register)
        
        btn_generate = QPushButton("Generar Boleta")
        btn_generate.setObjectName("secondaryButton")
        btn_generate.setMinimumWidth(150)
        btn_generate.setMinimumHeight(40)
        btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #CCCCCC;
                color: #999999;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
                color: white;
            }
            QPushButton:pressed:enabled {
                background-color: #3d8b40;
            }
        """)
        btn_generate.setEnabled(False)  # Deshabilitado inicialmente
        btn_generate.clicked.connect(self.generate_receipt)
        action_buttons_layout.addWidget(btn_generate)
        
        layout.addLayout(action_buttons_layout)
        
        # BotÃ³n Cerrar
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("secondaryButton")
        btn_close.setMinimumWidth(120)
        btn_close.clicked.connect(enlarged_window.accept)
        button_layout.addWidget(btn_close)
        
        layout.addLayout(button_layout)
        
        enlarged_window.exec_()

    def register_sale(self):
        """Registra la venta actual en el sistema."""
        if not self.cart_items:
            QMessageBox.warning(self, "Carrito vacÃ­o", "No hay productos en el carrito para registrar una venta.")
            return
        
        try:
            # Calcular totales
            total_general = 0
            items_data = []
            
            for product_name, item in self.cart_items.items():
                cantidad = int(item.get('cantidad', 1))
                precio = float(item.get('precio', 0))
                subtotal = cantidad * precio
                total_general += subtotal
                
                items_data.append({
                    'nombre': product_name,
                    'cantidad': cantidad,
                    'precio': precio,
                    'subtotal': subtotal
                })
            
            # Crear registro de venta
            venta = {
                'id': datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                'fecha': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'items': items_data,
                'total': total_general,
                'estado': 'completada'
            }
            
            # Guardar en archivo de ventas
            ventas_dir = os.path.join("VISO", str(self.username), "ventas")
            os.makedirs(ventas_dir, exist_ok=True)
            
            ventas_file = os.path.join(ventas_dir, "ventas.json")
            ventas = []
            
            if os.path.exists(ventas_file):
                try:
                    with open(ventas_file, 'r', encoding='utf-8') as f:
                        ventas = json.load(f)
                except:
                    ventas = []
            
            ventas.append(venta)
            
            with open(ventas_file, 'w', encoding='utf-8') as f:
                json.dump(ventas, f, indent=4, ensure_ascii=False)
            
            # ========== DISMINUIR STOCK ==========
            # Cargar productos actuales
            productos = cargar_productos(self.username)
            
            # Actualizar stock de cada producto vendido
            for product_id, item in self.cart_items.items():
                cantidad_vendida = int(item.get('cantidad', 1))
                
                # Buscar el producto en la lista
                for producto in productos:
                    if str(producto.get('id', '')) == str(product_id):
                        # Disminuir stock
                        stock_actual = int(producto.get('stock', 0))
                        nuevo_stock = max(0, stock_actual - cantidad_vendida)  # No permitir stock negativo
                        producto['stock'] = nuevo_stock
                        
                        # Registrar en kardex
                        kardex_entry = {
                            'producto_id': product_id,
                            'producto_nombre': producto.get('nombre', ''),
                            'producto': producto.get('nombre', ''),
                            'tipo': 'salida',
                            'movimiento': 'Salida',
                            'cantidad': cantidad_vendida,
                            'precio': float(producto.get('precio', producto.get('costo', 0)) or 0),
                            'stock_anterior': stock_actual,
                            'stock_nuevo': nuevo_stock,
                            'stock_final': nuevo_stock,
                            'fecha': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'razon': 'Venta registrada',
                            'venta_id': datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                        }
                        
                        # Guardar en kardex
                        kardex = cargar_kardex(self.username)
                        kardex.append(kardex_entry)
                        guardar_kardex(self.username, kardex)
                        
                        break
            
            # Guardar productos actualizados
            guardar_productos(self.username, productos)
            
            # Limpiar carrito
            self.cart_items.clear()
            self.update_cart_table()
            
            # Actualizar vista de inventario
            self.update_inventory_gallery()
            
            QMessageBox.information(self, "Éxito", f"Venta registrada exitosamente.\nTotal: S/ {total_general:.2f}\nStock actualizado.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al registrar la venta: {str(e)}")

    def _register_sale_and_generate(self, btn_register, btn_generate, window, paciente_dni=None, paciente_nombre=None):
        """Registra la venta y habilita el botÃ³n de generar boleta (en otro hilo)."""
        if not self.cart_items:
            QMessageBox.warning(self, "Carrito vacÃ­o", "No hay productos en el carrito para registrar una venta.")
            return
        
        # ========== VALIDACIÃƒâ€œN DE STOCK EN THREAD PRINCIPAL ==========
        # Esto DEBE hacerse aquÃ­, NO en el thread worker
        productos = cargar_productos(self.username)
        
        stock_insuficiente = []
        for product_name, item in self.cart_items.items():
            cantidad_vendida = int(item.get('cantidad', 1))
            encontrado = False
            
            for producto in productos:
                prod_nombre = producto.get('nombre', '').strip()
                if prod_nombre == product_name:
                    encontrado = True
                    stock_actual = int(producto.get('stock', 0))
                    if stock_actual < cantidad_vendida:
                        stock_insuficiente.append({
                            'nombre': prod_nombre,
                            'solicitado': cantidad_vendida,
                            'disponible': stock_actual
                        })
                    break
            
            if not encontrado:
                stock_insuficiente.append({
                    'nombre': product_name,
                    'solicitado': cantidad_vendida,
                    'disponible': 0
                })
        
        # Si hay stock insuficiente, mostrar diÃ¡logo
        if stock_insuficiente:
            dialog = QDialog(self)
            dialog.setWindowTitle("Stock Insuficiente - Agregar Stock")
            dialog.setGeometry(100, 100, 500, 400)
            
            layout = QVBoxLayout()
            
            # Mensaje
            msg_label = QLabel("Los siguientes productos no tienen stock suficiente:")
            layout.addWidget(msg_label)
            
            # Scroll con inputs
            scroll = QScrollArea()
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout()
            
            inputs_dict = {}
            for prod in stock_insuficiente:
                group = QGroupBox(f"{prod['nombre']}")
                group_layout = QVBoxLayout()
                
                # Info actual
                info_label = QLabel(f"Solicitado: {prod['solicitado']} | Disponible: {prod['disponible']}")
                info_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
                group_layout.addWidget(info_label)
                
                # Input para agregar stock
                input_layout = QHBoxLayout()
                input_layout.addWidget(QLabel("Agregar stock:"))
                spin_box = QSpinBox()
                spin_box.setMinimum(0)
                spin_box.setMaximum(10000)
                spin_box.setValue(prod['solicitado'] - prod['disponible'])  # Sugerir lo faltante
                input_layout.addWidget(spin_box)
                group_layout.addLayout(input_layout)
                
                group.setLayout(group_layout)
                scroll_layout.addWidget(group)
                inputs_dict[prod['nombre']] = spin_box
            
            scroll_layout.addStretch()
            scroll_widget.setLayout(scroll_layout)
            scroll.setWidget(scroll_widget)
            layout.addWidget(scroll)
            
            # Botones
            btn_layout = QHBoxLayout()
            btn_agregar = QPushButton("Agregar Stock y Continuar")
            btn_cancelar = QPushButton("Cancelar Venta")
            btn_layout.addWidget(btn_agregar)
            btn_layout.addWidget(btn_cancelar)
            layout.addLayout(btn_layout)
            
            dialog.setLayout(layout)
            
            # Funciones de botones
            def agregar_y_continuar():
                # Actualizar stock en productos
                for prod_nombre, spin_box in inputs_dict.items():
                    stock_a_agregar = spin_box.value()
                    if stock_a_agregar > 0:
                        for producto in productos:
                            if producto.get('nombre', '').strip() == prod_nombre:
                                stock_actual = int(producto.get('stock', 0))
                                producto['stock'] = stock_actual + stock_a_agregar
                                print(f"[VENTA] Stock de '{prod_nombre}' actualizado: {stock_actual} Ã¢â€ â€™ {producto['stock']}")
                                break
                
                # Guardar productos actualizados
                guardar_productos(self.username, productos)
                dialog.accept()
            
            btn_agregar.clicked.connect(agregar_y_continuar)
            btn_cancelar.clicked.connect(dialog.reject)
            
            # Mostrar diÃ¡logo
            if dialog.exec_() != QDialog.Accepted:
                return
        
        # ========== SI VALIDACIÃƒâ€œN PASÃƒâ€œ, AHORA SÃ INICIAR EL THREAD WORKER ==========
        # Guardar referencias a los widgets (no los pasamos al thread)
        self.btn_register_ref = btn_register
        self.btn_generate_ref = btn_generate
        
        # Copiar datos del carrito (datos puros, sin referencias a widgets)
        cart_items_copy = dict(self.cart_items)
        
        # Iniciar la animaciÃ³n del loader en el botÃ³n
        btn_register.start_loading()
        
        # Crear el worker para ejecutar la venta en otro hilo
        # Solo pasamos DATOS, no widgets
        self.sale_worker = LoaderWorker(
            self._process_sale_in_thread,
            cart_items_copy, paciente_dni, paciente_nombre
        )
        
        # Conectar seÃ±ales
        self.sale_worker.finished.connect(self._on_sale_completed)
        self.sale_worker.error.connect(self._on_sale_error)
        
        # Iniciar el worker
        self.sale_worker.start()
    
    def _process_sale_in_thread(self, cart_items_copy, paciente_dni=None, paciente_nombre=None):
        """Procesa la venta en un hilo separado. SOLO OPERACIONES NO-GUI, SIN QDialog."""
        try:
            # Calcular totales
            total_general = 0
            items_data = []
            
            for product_name, item in cart_items_copy.items():
                cantidad = int(item.get('cantidad', 1))
                precio = float(item.get('precio', 0))
                subtotal = cantidad * precio
                total_general += subtotal
                
                items_data.append({
                    'producto': product_name,
                    'nombre': product_name,
                    'cantidad': cantidad,
                    'precio_unitario': precio,
                    'precio': precio,
                    'subtotal': subtotal
                })
            
            # Usar DNI proporcionado como parÃ¡metro, o usar el del paciente actual, o valor por defecto
            dni_venta = paciente_dni if paciente_dni else (self.current_paciente_dni if self.current_paciente_dni else '00000000')
            nombre_paciente = paciente_nombre if paciente_nombre else self.current_paciente_nombre
            
            # Crear registro de venta con formato correcto
            venta = {
                'fecha': datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                'paciente_dni': dni_venta,
                'items': items_data,
                'total': total_general,
                'metodo_pago': 'efectivo'
            }
            
            # Guardar en archivo de ventas usando las funciones de file_handler
            ventas = cargar_ventas(self.username)
            ventas.append(venta)
            guardar_ventas(self.username, ventas)
            
            # ========== ACTUALIZAR HISTORIAL DE PACIENTE ==========
            # Si se proporcionÃ³ un DNI de paciente, actualizar su historial_graduaciones
            if dni_venta and dni_venta != '00000000':
                try:
                    pacientes = cargar_pacientes(self.username)
                    
                    # Ã°Å¸â€Â AUDITORÃA: Registrar quiÃ©n realizÃ³ la venta
                    usuario_registrador = "Sistema"
                    if self.parent_app:
                        if self.parent_app.is_helper:
                            # Si es un ayudante, registrar su nombre
                            usuario_registrador = self.parent_app.helper_name or "Ayudante"
                        else:
                            # Si es el usuario principal, usar su username
                            usuario_registrador = self.parent_app.username or "Usuario"
                    
                    for paciente in pacientes:
                        if paciente.get('dni', '') == dni_venta:
                            # Crear entrada de graduaciÃ³n con los items de venta
                            fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
                            nueva_graduacion = {
                                'fecha': fecha_hoy,
                                'monto_cobrado': total_general,
                                'items_venta': items_data,
                                'estado': 'completada',
                                'optometra': self.optometra if self.optometra else '',
                                'registrado_por': usuario_registrador  # Ã°Å¸â€Â QuiÃ©n realizÃ³ la venta
                            }
                            
                            # Inicializar historial si no existe
                            if 'historial_graduaciones' not in paciente:
                                paciente['historial_graduaciones'] = []
                            
                            # Agregar la nueva graduaciÃ³n
                            paciente['historial_graduaciones'].append(nueva_graduacion)
                            print(f"[VENTA] Agregada al historial de {paciente.get('nombre', 'Paciente')} (DNI: {dni_venta}) por {usuario_registrador}")
                            break
                    
                    # Guardar pacientes actualizados
                    guardar_pacientes(self.username, pacientes)
                except Exception as e:
                    print(f"[WARNING] Error al actualizar historial del paciente: {e}")
                    import traceback
                    traceback.print_exc()
            
            # ========== DISMINUIR STOCK ==========
            # Cargar productos actuales
            productos = cargar_productos(self.username)
            
            print(f"\n[VENTA] Iniciando actualizaciÃ³n de stock")
            print(f"[VENTA] Carrito items: {list(self.cart_items.keys())}")
            print(f"[VENTA] Total productos en archivo: {len(productos)}")
            
            # ========== DISMINUIR STOCK ==========
            # Cargar productos actuales
            productos = cargar_productos(self.username)
            
            print(f"\n[VENTA] Iniciando actualizaciÃ³n de stock")
            print(f"[VENTA] Carrito items: {list(cart_items_copy.keys())}")
            print(f"[VENTA] Total productos en archivo: {len(productos)}")
            
            # Actualizar stock de cada producto vendido
            for product_name, item in cart_items_copy.items():
                cantidad_vendida = int(item.get('cantidad', 1))
                print(f"\n[VENTA] Buscando producto: '{product_name}', cantidad: {cantidad_vendida}")
                
                # Buscar el producto en la lista por nombre
                encontrado = False
                for producto in productos:
                    prod_nombre = producto.get('nombre', '').strip()
                    
                    if prod_nombre == product_name:
                        encontrado = True
                        # Disminuir stock
                        stock_actual = int(producto.get('stock', 0))
                        nuevo_stock = max(0, stock_actual - cantidad_vendida)
                        producto['stock'] = nuevo_stock
                        
                        print(f"[VENTA] Ã¢Å“â€œ ENCONTRADO Y ACTUALIZADO")
                        print(f"[VENTA] Stock anterior: {stock_actual}, Stock nuevo: {nuevo_stock}")
                        
                        # Registrar en kardex
                        kardex_entry = {
                            'producto_nombre': prod_nombre,
                            'producto': prod_nombre,
                            'tipo': 'salida',
                            'movimiento': 'Salida',
                            'cantidad': cantidad_vendida,
                            'precio': float(producto.get('precio', producto.get('costo', 0)) or 0),
                            'stock_anterior': stock_actual,
                            'stock_nuevo': nuevo_stock,
                            'stock_final': nuevo_stock,
                            'fecha': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'razon': 'Venta registrada',
                            'venta_id': datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                        }
                        
                        # Guardar en kardex
                        kardex = cargar_kardex(self.username)
                        kardex.append(kardex_entry)
                        guardar_kardex(self.username, kardex)
                        
                        break
                
                if not encontrado:
                    print(f"[VENTA] Ã¢Å“â€” NO ENCONTRADO. Productos disponibles:")
                    for p in productos:
                        print(f"[VENTA]   - {p.get('nombre', 'SIN NOMBRE')}")
            
            # Guardar productos actualizados
            guardar_productos(self.username, productos)
            print(f"\n[VENTA] Productos guardados correctamente\n")
            
            # ========== GUARDAR ÃƒÅ¡LTIMA VENTA PARA GENERAR BOLETA ==========
            # Guardar la venta en un atributo para que pueda usarse al generar la boleta
            self.last_sale = venta
            self.last_sale_total = total_general
            
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            raise e
    
    def _on_sale_completed(self):
        """Callback cuando la venta se completa exitosamente."""
        try:
            # Mostrar el checkmark en el botÃ³n
            if hasattr(self, 'btn_register_ref'):
                btn_register = self.btn_register_ref
                btn_register.show_success(duration=1000)  # Mostrar Ã¢Å“â€œ por 1 segundo
            
            # Habilitar botÃ³n de generar boleta despuÃ©s del check
            if hasattr(self, 'btn_generate_ref'):
                btn_generate = self.btn_generate_ref
                btn_generate.setEnabled(True)
                btn_generate.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-weight: 600;
                        font-size: 12px;
                        padding: 8px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:pressed {
                        background-color: #3d8b40;
                    }
                """)
            
            # Limpiar carrito
            self.cart_items.clear()
            self.update_cart_table()
            
            # Actualizar vista de inventario
            self.update_inventory_gallery()
            
            # Mostrar mensaje de Ã©xito
            QMessageBox.information(
                self,
                "Éxito",
                f"Venta registrada exitosamente.\nTotal: S/ {self.last_sale_total:.2f}\n\nAhora puedes generar la boleta."
            )
            
            # Recargar el historial de ventas si estÃ¡ disponible
            try:
                if hasattr(self, 'parent_app') and hasattr(self.parent_app, 'sales_page'):
                    sales_page = self.parent_app.sales_page
                    if hasattr(sales_page, 'sales_history'):
                        sales_page.sales_history._reload_sales()
            except Exception as e:
                print(f"[INFO] No se pudo recargar el historial de ventas: {e}")
        
        except Exception as e:
            print(f"[ERROR] Error en _on_sale_completed: {str(e)}")

    
    def _on_sale_error(self, error_msg):
        """Callback cuando hay un error en la venta."""
        try:
            # Volver el botÃ³n a su estado normal
            if hasattr(self, 'btn_register_ref'):
                btn_register = self.btn_register_ref
                btn_register.reset_button()
            
            # Mostrar mensaje de error
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(self, "Error", f"Error al registrar la venta: {error_msg}")
        except Exception as e:
            print(f"[ERROR] Error en _on_sale_error: {str(e)}")


    def generate_receipt(self):
        """Abre el diÃ¡logo de opciones de venta para gestionar la boleta."""
        # Verificar que hay una venta registrada
        if not hasattr(self, 'last_sale') or not self.last_sale:
            QMessageBox.warning(self, "Sin venta", "No hay venta registrada. Registra una venta primero.")
            return
        
        try:
            from gui.dialogs.sale_options_dialog import SaleOptionsDialog
            
            # Preparar datos de venta para el diÃ¡logo
            sale_data = {
                'fecha': self.last_sale.get('fecha', ''),
                'paciente_dni': self.last_sale.get('paciente_dni', '00000000'),
                'items': self.last_sale.get('items', []),
                'total': self.last_sale.get('total', 0),
                'metodo_pago': self.last_sale.get('metodo_pago', 'efectivo')
            }
            
            # Abrir diÃ¡logo de opciones de venta
            dialog = SaleOptionsDialog(sale_data, self.username, parent=self)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir opciones de venta: {str(e)}")
            import traceback
            traceback.print_exc()


    def on_product_card_clicked(self, product_data):
        """Maneja el click en una tarjeta de producto y abre el diÃ¡logo de acciones."""
        from gui.dialogs.product_actions_dialog import ProductActionsDialog
        
        dialog = ProductActionsDialog(product_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            action = dialog.get_action()
            
            if action == 'edit':
                # Abrir editor de producto
                from gui.dialogs.product_dialog_new import OpticalProductDialog
                edit_dialog = OpticalProductDialog(product_data, parent=self)
                edit_dialog_result = edit_dialog.exec_()
                self._refresh_side_section_combo()
                if edit_dialog_result == QDialog.Accepted:
                    updated_data = edit_dialog.get_product_data()
                    seccion = self._normalize_section_value(
                        updated_data.get('categoria') or updated_data.get('seccion')
                    )
                    
                    # Crear carpeta de imÃ¡genes de productos si no existe
                    user_dir = os.path.join("VISO", str(self.username))
                    images_dir = os.path.join(user_dir, "product_images")
                    if not os.path.exists(images_dir):
                        os.makedirs(images_dir, exist_ok=True)
                    

                    # Procesar imagen si cambi?
                    image_source = updated_data.get('image_path') or updated_data.get('imagen')
                    final_image_path = product_data.get('image_path', '')
                    if image_source:
                        try:
                            original_file = image_source
                            # Si es una ruta nueva (no es la ruta guardada anterior), copiar
                            if original_file != final_image_path:
                                file_extension = os.path.splitext(original_file)[1]
                                codigo_producto = updated_data.get('codigo', 'producto')
                                image_filename = f"{codigo_producto}{file_extension}"
                                image_path = os.path.join(images_dir, image_filename)
                                
                                # Copiar la imagen
                                if os.path.exists(original_file):
                                    shutil.copy2(original_file, image_path)
                                    final_image_path = image_path
                        except Exception as e:
                            print(f"Error al copiar imagen: {e}")
                    # Guardar ruta final (compatibilidad)
                    updated_data['image_path'] = final_image_path
                    updated_data['imagen'] = final_image_path
                    
                    # Cargar productos
                    productos = cargar_productos(self.username)
                    # Encontrar y actualizar el producto
                    for i, prod in enumerate(productos):
                        if prod.get('codigo') == product_data.get('codigo'):
                            # Preparar datos actualizados
                            datos_actualizados = {
                                'codigo': updated_data.get('codigo', ''),
                                'nombre': updated_data.get('nombre', ''),
                                'marca': updated_data.get('marca', ''),
                                'categoria': seccion,
                                'seccion': seccion,
                                'material': updated_data.get('material', ''),
                                'talla': updated_data.get('talla', ''),
                                'tipo_lente': updated_data.get('tipo_lente', ''),
                                'colors': updated_data.get('colors', []),
                                'stock': updated_data.get('stock', 0),
                                'costo': updated_data.get('costo', 0.0),
                                'venta': updated_data.get('venta', 0.0),
                                'precio_regular': updated_data.get('precio_regular', 0.0),
                                'caracteristicas': updated_data.get('caracteristicas', {}),
                                'variantes': updated_data.get('variantes', {}),
                                'image_path': updated_data.get('image_path', ''),
                            }
                            productos[i].update(datos_actualizados)
                            break
                    # Guardar cambios
                    guardar_productos(self.username, productos)
                    self.all_productos = productos
                    self.apply_inventory_filters()
                    QMessageBox.information(self, "Éxito", "Producto actualizado correctamente.")
            
            elif action == 'add_stock':
                # Abrir diÃ¡logo para aÃ±adir stock
                self.abrir_dialogo_add_stock(product_data)

            elif action == 'change_section':
                # Cambiar seccion/categoria rapido desde selector
                if self.parent_app and self.parent_app.is_helper:
                    if not self.parent_app.puede_hacer_accion('inventario', 'editar'):
                        QMessageBox.warning(
                            self,
                            "Permiso Denegado",
                            "No tienes permiso para editar productos."
                        )
                        return

                categorias = self._get_sorted_categories()
                if not categorias:
                    QMessageBox.warning(self, "Sin secciones", "No hay secciones disponibles para asignar.")
                    return

                seccion_actual = self._get_product_section(product_data)
                idx_default = 0
                if seccion_actual:
                    for i, c in enumerate(categorias):
                        if c.lower() == seccion_actual.lower():
                            idx_default = i
                            break

                nueva_seccion, ok = QInputDialog.getItem(
                    self,
                    "Cambiar seccion",
                    "Selecciona la nueva seccion para el producto:",
                    categorias,
                    idx_default,
                    False
                )
                if not ok:
                    return

                nueva_seccion = self._normalize_section_value(nueva_seccion)
                productos = cargar_productos(self.username) or []
                actualizado = False

                for prod in productos:
                    if not isinstance(prod, dict):
                        continue

                    codigo_prod = str(prod.get('codigo', '')).strip()
                    codigo_target = str(product_data.get('codigo', '')).strip()

                    if codigo_target and codigo_prod == codigo_target:
                        self._set_product_section(prod, nueva_seccion)
                        actualizado = True
                        break

                    if (not codigo_target) and prod.get('nombre') == product_data.get('nombre'):
                        self._set_product_section(prod, nueva_seccion)
                        actualizado = True
                        break

                if not actualizado:
                    QMessageBox.warning(self, "No encontrado", "No se pudo ubicar el producto para cambiar su seccion.")
                    return

                guardar_productos(self.username, productos)
                self.all_productos = productos
                self._refresh_side_section_combo()
                self.apply_inventory_filters()
                QMessageBox.information(self, "Exito", f"Seccion actualizada a '{nueva_seccion}'.")
            elif action == 'transfer':
                QMessageBox.information(
                    self,
                    "Funcion bloqueada temporalmente",
                    "Mover a otra sucursal esta bloqueado temporalmente por seguridad.\n\nSe reactivara cuando la transferencia quede validada."
                )
                return
                from gui.dialogs.branch_transfer_dialog import BranchTransferDialog
                transfer_dialog = BranchTransferDialog(product_data, self.username, parent=self)
                if transfer_dialog.exec_() == QDialog.Accepted:
                    transfer_data = transfer_dialog.get_transfer_data()
                    dest_branch = str(transfer_data.get('branch_code') or '').strip()
                    try:
                        qty = int(transfer_data.get('quantity') or 0)
                    except Exception:
                        qty = 0

                    if not dest_branch:
                        QMessageBox.warning(self, "Destino invalido", "Debes seleccionar una sucursal de destino.")
                        return

                    productos = cargar_productos(self.username) or []
                    codigo_target = str(product_data.get('codigo', '')).strip()
                    nombre_target = str(product_data.get('nombre', '')).strip()
                    producto_origen = None

                    for prod in productos:
                        if not isinstance(prod, dict):
                            continue
                        codigo_prod = str(prod.get('codigo', '')).strip()
                        nombre_prod = str(prod.get('nombre', '')).strip()
                        if codigo_target and codigo_prod == codigo_target:
                            producto_origen = prod
                            break
                        if (not codigo_target) and nombre_target and nombre_prod == nombre_target:
                            producto_origen = prod
                            break

                    if not producto_origen:
                        QMessageBox.warning(self, "No encontrado", "No se pudo ubicar el producto origen para transferir.")
                        return

                    try:
                        stock_actual = int(float(producto_origen.get('stock', 0) or 0))
                    except Exception:
                        stock_actual = 0

                    if qty <= 0:
                        QMessageBox.warning(self, "Cantidad invalida", "La cantidad a mover debe ser mayor a cero.")
                        return

                    if qty > stock_actual:
                        QMessageBox.warning(
                            self,
                            "Stock insuficiente",
                            f"No puedes mover {qty} unidades porque solo hay {stock_actual} disponibles."
                        )
                        return

                    # Preparar payload independiente para la sucursal destino.
                    # IMPORTANTE: el servidor no debe recibir el stock restante del origen.
                    producto_transferido = dict(producto_origen)
                    producto_transferido['stock'] = qty
                    producto_transferido['cantidad_transferida'] = qty
                    producto_transferido['stock_origen_antes'] = stock_actual

                    # 1. Restar de la sucursal actual
                    new_stock = stock_actual - qty
                    producto_origen['stock'] = new_stock
                    producto_transferido['stock_origen_despues'] = new_stock

                    # 2. Guardar cambios locales y sincronizar
                    guardar_productos(self.username, productos)
                    self.all_productos = productos
                    
                    # 3. Registrar en Kardex
                    try:
                        self.add_kardex_entry(
                            tipo='Salida',
                            producto=producto_origen.get('nombre', 'Producto'),
                            cantidad=qty,
                            costo=producto_origen.get('costo', 0),
                            motivo=f"Transferencia a sucursal {dest_branch}"
                        )
                    except Exception:
                        pass

                    self.update_inventory_gallery()

                    # Ruta nueva: actualizar destino directamente por snapshot/dataset
                    # y salir antes de ejecutar la ruta legacy transfer_stock.php.
                    try:
                        from utils.api_handler import subir_dataset_dispositivo_nube
                        from utils.file_handler import (
                            _download_snapshot_payload_for_dataset,
                            _extract_list_dataset_from_snapshot,
                            save_branch_snapshot_datasets,
                        )

                        current_ctx = get_effective_branch_context(self.username) or {}
                        current_branch_code = str(current_ctx.get('code', '') or '').strip().upper()
                        if current_branch_code and current_branch_code == dest_branch:
                            QMessageBox.warning(self, "Sucursal invalida", "La sucursal destino no puede ser la misma sucursal actual.")
                            return

                        payload_dest = _download_snapshot_payload_for_dataset(self.username, dest_branch, "productos")
                        productos_destino = _extract_list_dataset_from_snapshot(payload_dest, "productos") if payload_dest else []
                        if not isinstance(productos_destino, list):
                            productos_destino = []

                        producto_destino = None
                        codigo_transfer = str(producto_transferido.get('codigo', '')).strip()
                        nombre_transfer = str(producto_transferido.get('nombre', '')).strip()

                        for prod_dest in productos_destino:
                            if not isinstance(prod_dest, dict):
                                continue
                            codigo_dest = str(prod_dest.get('codigo', '')).strip()
                            nombre_dest = str(prod_dest.get('nombre', '')).strip()
                            if codigo_transfer and codigo_dest == codigo_transfer:
                                producto_destino = prod_dest
                                break
                            if (not codigo_transfer) and nombre_transfer and nombre_dest == nombre_transfer:
                                producto_destino = prod_dest
                                break

                        if producto_destino is not None:
                            try:
                                stock_dest_actual = int(float(producto_destino.get('stock', 0) or 0))
                            except Exception:
                                stock_dest_actual = 0
                            producto_destino['stock'] = stock_dest_actual + qty
                        else:
                            nuevo_producto_destino = dict(producto_transferido)
                            nuevo_producto_destino.pop('cantidad_transferida', None)
                            nuevo_producto_destino.pop('stock_origen_antes', None)
                            nuevo_producto_destino.pop('stock_origen_despues', None)
                            nuevo_producto_destino['stock'] = qty
                            productos_destino.append(nuevo_producto_destino)

                        ok_up, msg_up, _resp_up = subir_dataset_dispositivo_nube(
                            usuario_madre=str(self.username),
                            codigo_dispositivo=dest_branch,
                            dataset="productos",
                            data=productos_destino,
                            operacion="SYNC_ALL",
                        )

                        if ok_up:
                            try:
                                save_branch_snapshot_datasets(self.username, dest_branch, {"productos": productos_destino})
                            except Exception:
                                pass
                            QMessageBox.information(
                                self,
                                "Transferencia exitosa",
                                f"Se movieron {qty} unidades correctamente.\n\nLa sucursal destino ya fue actualizada en la nube."
                            )
                        else:
                            QMessageBox.warning(
                                self,
                                "No se pudo actualizar destino",
                                str(msg_up or "La sucursal origen se actualizo, pero el stock no pudo subirse a la sucursal destino.")
                            )
                    except Exception as transfer_err:
                        print(f"[TRANSFER] Error actualizando sucursal destino: {transfer_err}")
                        QMessageBox.information(
                            self,
                            "Transferencia local OK",
                            f"Se restaron {qty} unidades localmente, pero no se pudo actualizar la sucursal destino.\n\nDetalle: {transfer_err}"
                        )
                    return
                    
                    # 4. Informar al servidor para que la otra sucursal reciba el stock
                    try:
                        import requests
                        import urllib3
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        
                        transfer_url = "https://api.yhana.cloud/win/new/transfer_stock.php"
                        payload = {
                            "usuario_madre": self.username,
                            "codigo_destino": dest_branch,
                            "producto": producto_transferido,
                            "cantidad": qty
                        }
                        
                        response = requests.post(transfer_url, json=payload, timeout=10, verify=False)
                        server_res = response.json()
                        
                        if server_res.get("status") == "success":
                            QMessageBox.information(
                                self, 
                                "Transferencia exitosa", 
                                f"Se han movido {qty} unidades correctamente.\n\nLa sucursal destino ya tiene el stock actualizado en la nube."
                            )
                        else:
                            QMessageBox.warning(self, "Aviso del servidor", server_res.get("message", "Error desconocido en el servidor"))
                            
                    except Exception as e:
                        print(f"[TRANSFER] Error informando al servidor: {e}")
                        QMessageBox.information(
                            self, 
                            "Transferencia local OK", 
                            f"Se han restado {qty} unidades localmente, pero no se pudo actualizar la nube. La otra sucursal deberá agregarlo manualmente."
                        )
            
            elif action == 'delete':
                # Eliminar producto
                productos = cargar_productos(self.username)
                productos = [p for p in productos if p.get('codigo') != product_data.get('codigo')]
                guardar_productos(self.username, productos)
                self.update_inventory_gallery()
                QMessageBox.information(self, "Éxito", "Producto eliminado correctamente.")

    def abrir_dialogo_add_stock(self, producto):
        """Abre un diÃ¡logo para aÃ±adir stock a un producto."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Aumentar Stock")
        dialog.setModal(True)
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # InformaciÃ³n del producto
        info_layout = QHBoxLayout()
        nombre_label = QLabel(f"<b>{producto.get('nombre', '')}</b>")
        stock_actual_label = QLabel(f"Stock actual: {producto.get('stock', 0)}")
        info_layout.addWidget(nombre_label)
        info_layout.addWidget(stock_actual_label)
        layout.addLayout(info_layout)
        
        # Campo para la cantidad
        cantidad_layout = QHBoxLayout()
        cantidad_layout.addWidget(QLabel("Cantidad a aÃ±adir:"))
        cantidad_spin = QtWidgets.QSpinBox()
        cantidad_spin.setMinimum(1)
        cantidad_spin.setMaximum(9999)
        cantidad_spin.setValue(1)
        cantidad_layout.addWidget(cantidad_spin)
        layout.addLayout(cantidad_layout)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.setStyleSheet("""
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:pressed {
                background-color: #096dd9;
            }
        """)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                border-color: #40a9ff;
                color: #40a9ff;
            }
        """)
        
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        def guardar_stock():
            cantidad = cantidad_spin.value()
            productos = cargar_productos(self.username)
            for prod in productos:
                if prod.get('codigo') == producto.get('codigo'):
                    prod['stock'] = prod.get('stock', 0) + cantidad
                    break
            guardar_productos(self.username, productos)
            self.update_inventory_gallery()
            dialog.accept()
            QMessageBox.information(self, "Éxito", f"Stock aumentado en {cantidad} unidades.")
        
        btn_aceptar.clicked.connect(guardar_stock)
        btn_cancelar.clicked.connect(dialog.reject)
        
        dialog.exec_()

    def abrir_edicion_producto(self, prod):
        # Ã°Å¸â€ºÂ¡Ã¯Â¸Â VERIFICAR PERMISOS: Solo puede editar si tiene permiso
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('inventario', 'editar'):
                QMessageBox.warning(
                    self,
                    "Permiso Denegado",
                    "No tienes permiso para editar productos."
                )
                return
        
        # Usar el diÃ¡logo modal local (ProductEditorDialog) que permite editar imagen
        dialog = ProductEditorDialog(self, prod)
        if dialog.exec_() == QDialog.Accepted:
            # El diÃ¡logo guarda los cambios en disco; solo refrescar la galerÃ­a
            try:
                self.update_inventory_gallery()
            except Exception:
                pass
            QMessageBox.information(self, "Éxito", "Producto actualizado correctamente.")

    def eliminar_producto_galeria(self, producto_ref):
        """Elimina un producto del inventario local y sincroniza al servidor."""
        # Ã°Å¸â€ºÂ¡Ã¯Â¸Â VERIFICAR PERMISO: Solo puede eliminar si tiene permiso 'eliminar' en inventario
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('inventario', 'eliminar'):
                QMessageBox.warning(
                    self,
                    "Permiso Denegado",
                    "No tienes permiso para eliminar productos del inventario."
                )
                return

        try:
            current_ctx = get_effective_branch_context(self.username) or {}
            current_branch_code = str(current_ctx.get("code", "") or "").strip().upper()
        except Exception:
            current_branch_code = ""

        if not current_branch_code:
            QMessageBox.warning(
                self,
                "Selecciona una sucursal",
                "Estás en 'Todas las sucursales'.\n\n"
                "Para eliminar un producto debes seleccionar primero la sucursal exacta arriba,\n"
                "porque la nube guarda el inventario por tienda."
            )
            return

        if isinstance(producto_ref, dict):
            codigo_eliminar = str(producto_ref.get('codigo', '') or '').strip()
            nombre_eliminar = str(producto_ref.get('nombre', '') or '').strip()
        else:
            codigo_eliminar = ""
            nombre_eliminar = str(producto_ref or '').strip()

        display_name = f"{codigo_eliminar} - {nombre_eliminar}" if codigo_eliminar else nombre_eliminar

        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Estás seguro de que quieres eliminar el producto '{display_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        print(f"\n[DELETE] Iniciando eliminación del producto: '{display_name}'", flush=True)
        try:
            productos = cargar_productos(self.username, prefer_cloud=False) or []
            if isinstance(productos, dict):
                productos = list(productos.values())
            if not isinstance(productos, list):
                productos = []
            productos = [p for p in productos if isinstance(p, dict)]

            codigo_target = codigo_eliminar.strip().upper()
            nombre_target = nombre_eliminar.strip().lower()
            productos_nuevos = []
            deleted_products = []

            for producto in productos:
                codigo_actual = str(producto.get('codigo', '') or '').strip().upper()
                nombre_actual = str(producto.get('nombre', '') or '').strip()

                coincide = False
                if codigo_target:
                    coincide = codigo_actual == codigo_target
                elif nombre_target:
                    coincide = nombre_actual.lower() == nombre_target

                if coincide:
                    deleted_products.append(dict(producto))
                    continue
                productos_nuevos.append(producto)

            if not deleted_products:
                print(f"[DELETE] No se encontró producto: '{display_name}'", flush=True)
                QMessageBox.warning(self, "Advertencia", f"No se encontró el producto '{display_name}'")
                return

            from utils.trash_manager import move_to_trash

            for deleted_product in deleted_products:
                move_to_trash(
                    self.username,
                    "productos",
                    deleted_product,
                    source="inventory_page.delete",
                )

            guardar_productos(self.username, productos_nuevos, queue_sync=False)
            self._log_audit('eliminar', f"Producto eliminado: {display_name}")
            self.all_productos = productos_nuevos
            self.total_products = None
            self.apply_inventory_filters()
            self.update_inventory_gallery()
            try:
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass

            from utils.sync_manager import sync_product_change
            sync_product_change(
                self.username,
                'DELETE',
                producto_nombre=nombre_eliminar,
                producto_codigo=codigo_eliminar,
            )

            try:
                parent_main = getattr(self, "parent_app", None)
                if parent_main is not None:
                    if hasattr(parent_main, "_queue_system_status_snapshot"):
                        parent_main._queue_system_status_snapshot()
                    if hasattr(parent_main, "_refresh_system_status_bar"):
                        parent_main._refresh_system_status_bar()
            except Exception:
                pass

            print(f"[DELETE] Eliminado localmente y encolado para nube: {display_name}", flush=True)
        except Exception as e:
            print(f"[DELETE] ERROR: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al eliminar el producto: {str(e)}")
            return
        return
        
        if QMessageBox.question(
            self, "Confirmar",
                    f"¿Estás seguro de que quieres eliminar el producto '{nombre}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            # Capturar el nombre de forma muy explÃ­cita
            nombre_eliminar = str(nombre).strip()
            
            # Ã¢Å“â€¦ PASO 1: Eliminar localmente de inmediato
            print(f"\n[DELETE] Iniciando eliminaciÃ³n del producto: '{nombre_eliminar}'", flush=True)
            try:
                # Cargar productos actuales
                productos = cargar_productos(self.username) or []
                # Normalizar estructura
                if isinstance(productos, dict):
                    productos = list(productos.values())
                if not isinstance(productos, list):
                    productos = []
                # Filtrar solo dicts vÃ¡lidos
                productos = [p for p in productos if isinstance(p, dict)]
                print(f"[DELETE] Total de productos antes: {len(productos)}", flush=True)
                
                # Debug: mostrar todos los productos
                for idx, p in enumerate(productos):
                    print(f"[DELETE]   [{idx}] '{p.get('nombre', 'SIN_NOMBRE')}'", flush=True)
                
                # Filtrar: mantener solo los que NO coinciden
                productos_nuevos = []
                deleted_products = []
                eliminado = False
                
                for producto in productos:
                    nombre_actual = str(producto.get('nombre', '')).strip()
                    
                    # Comparar de forma sensible (ignorar mayÃºsculas y espacios extra)
                    if nombre_actual.lower() == nombre_eliminar.lower():
                        print(f"[DELETE] Ã¢Å“â€œ COINCIDENCIA ENCONTRADA: '{nombre_actual}'", flush=True)
                        eliminado = True
                        deleted_products.append(dict(producto))
                        continue  # Saltar este producto (no lo agregamos)
                    else:
                        productos_nuevos.append(producto)
                
                if eliminado:
                    print(f"[DELETE] Ã¢Å“â€œ Producto fue eliminado de la lista", flush=True)
                    print(f"[DELETE] Total de productos despuÃ©s: {len(productos_nuevos)}", flush=True)
                    
                    from utils.trash_manager import move_to_trash

                    for deleted_product in deleted_products:
                        move_to_trash(
                            self.username,
                            "productos",
                            deleted_product,
                            source="inventory_page.delete",
                        )

                    # Guardar los productos sin el eliminado
                    guardar_productos(self.username, productos_nuevos)
                    print(f"[DELETE] Ã¢Å“â€œ Archivo JSON guardado exitosamente", flush=True)
                    
                    self._log_audit('eliminar', f"Producto eliminado: {nombre_eliminar}")
                    
                    # Actualizar cache local
                    self.all_productos = productos_nuevos
                    
                    # Re-aplicar filtros para mantener la vista consistente y actualizar UI
                    self.apply_inventory_filters()
                    print(f"[DELETE] Ã¢Å“â€œ GalerÃ­a actualizada y filtros reaplicados", flush=True)
                    
                    QMessageBox.information(self, "Éxito", f"Producto '{nombre_eliminar}' eliminado correctamente.")
                else:
                    print(f"[DELETE] Ã¢ÂÅ’ NO SE ENCONTRÃƒâ€œ PRODUCTO CON NOMBRE: '{nombre_eliminar}'", flush=True)
                    QMessageBox.warning(self, "Advertencia", f"No se encontrÃ³ un producto con el nombre '{nombre_eliminar}'")
                    
            except Exception as e:
                print(f"[DELETE] Ã¢ÂÅ’ ERROR: {str(e)}", flush=True)
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Error al eliminar el producto: {str(e)}")
                return
            
            # Ã¢Å“â€¦ PASO 2: Sincronizar eliminaciÃ³n en background SIN BLOQUEAR
            def _sync_delete_background():
                """Sincroniza la eliminaciÃ³n en thread separado."""
                try:
                    import time
                    time.sleep(0.5)
                    
                    print(f"\n[SYNC] Sincronizando eliminaciÃ³n de: '{nombre_eliminar}'...", flush=True)
                    from utils.sync_manager import sync_product_change
                    sync_product_change(self.username, 'DELETE', producto_nombre=nombre_eliminar)
                    
                    print(f"[SYNC] Ã¢Å“â€œ EliminaciÃ³n sincronizada en servidor\n", flush=True)
                except Exception as e:
                    print(f"[SYNC] Ã¢Å¡Â  Error sincronizando: {e}", flush=True)
            
            import threading
            delete_sync_thread = threading.Thread(target=_sync_delete_background, daemon=True)
            delete_sync_thread.start()


    def abrir_dialogo_add_stock(self, producto):
        """Abre un diÃ¡logo para aÃ±adir stock a un producto."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("AÃ±adir Stock")
        dialog.setModal(True)
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # InformaciÃ³n del producto
        info_layout = QHBoxLayout()
        nombre_label = QLabel(f"<b>{producto.get('nombre', '')}</b>")
        stock_actual_label = QLabel(f"Stock actual: {producto.get('stock', 0)}")
        info_layout.addWidget(nombre_label)
        info_layout.addWidget(stock_actual_label)
        layout.addLayout(info_layout)
        
        # Campo para la cantidad
        cantidad_layout = QHBoxLayout()
        cantidad_layout.addWidget(QLabel("Cantidad a aÃ±adir:"))
        cantidad_spin = QtWidgets.QSpinBox()
        cantidad_spin.setMinimum(1)
        cantidad_spin.setMaximum(9999)
        cantidad_spin.setValue(1)
        cantidad_layout.addWidget(cantidad_spin)
        layout.addLayout(cantidad_layout)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.setStyleSheet("""
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:pressed {
                background-color: #096dd9;
            }
        """)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                border-color: #40a9ff;
                color: #40a9ff;
            }
        """)
        
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        def guardar_stock():
            cantidad = cantidad_spin.value()
            if cantidad > 0:
                productos = cargar_productos(self.username)
                producto_actualizado = None
                for p in productos:
                    if p.get('nombre') == producto.get('nombre'):
                        nuevo_stock = p.get('stock', 0) + cantidad
                        p['stock'] = nuevo_stock
                        producto_actualizado = p
                        self.add_kardex_entry('Entrada', p['nombre'], cantidad, p.get('costo', 0))
                        break
                
                # Ã¢Å“â€¦ PASO 1: Guardar localmente de inmediato
                print(f"[LOCAL] Guardando aumento de stock localmente...", flush=True)
                guardar_productos(self.username, productos)
                print(f"[LOCAL] Ã¢Å“â€œ Stock actualizado en JSON local", flush=True)
                
                # Ã¢Å“â€¦ PASO 2: Actualizar UI
                print(f"[UI] Actualizando galerÃ­a...", flush=True)
                self.update_inventory_gallery()
                print(f"[UI] Ã¢Å“â€œ GalerÃ­a actualizada", flush=True)
                QMessageBox.information(dialog, "Éxito", f"Se aÃ±adieron {cantidad} unidades al stock.")
                dialog.accept()
                
                # Ã¢Å“â€¦ PASO 3: Sincronizar en background SIN BLOQUEAR
                def _sync_stock_background():
                    """Sincroniza el cambio de stock en thread separado"""
                    try:
                        import time
                        time.sleep(0.2)
                        
                        print(f"\n[SYNC_START] Iniciando sincronizaciÃ³n de stock...", flush=True)
                        from utils.sync_manager import sync_product_change
                        if producto_actualizado:
                            sync_product_change(self.username, 'UPDATE', producto_data=producto_actualizado)
                        
                        print(f"[SYNC_END] Stock UPDATE sincronizado en background\n", flush=True)
                    except Exception as e:
                        print(f"[SYNC_ERROR] Ã¢Å¡Â  Error sincronizando stock: {e}", flush=True)
                
                import threading
                stock_sync_thread = threading.Thread(target=_sync_stock_background, daemon=True)
                stock_sync_thread.start()
        
        btn_aceptar.clicked.connect(guardar_stock)
        btn_cancelar.clicked.connect(dialog.reject)
        
        dialog.exec_()

    def clear_product_form(self):
        pass

    def guardar_producto_quick(self):
        """Agregar un producto desde el panel lateral (campos rÃ¡pidos)."""
        self._sync_branch_context_from_parent()
        nombre = (getattr(self, 'quick_name', None).text().strip()) if getattr(self, 'quick_name', None) else ''
        costo_str = (getattr(self, 'quick_costo', None).text().strip()) if getattr(self, 'quick_costo', None) else ''
        venta_str = (getattr(self, 'quick_venta', None).text().strip()) if getattr(self, 'quick_venta', None) else ''
        stock_str = (getattr(self, 'quick_stock', None).text().strip()) if getattr(self, 'quick_stock', None) else ''
        marca = (getattr(self, 'quick_marca', None).text().strip()) if getattr(self, 'quick_marca', None) else ''

        if not nombre:
            QMessageBox.critical(self, "Error", "El campo 'Nombre' es obligatorio.")
            return

        try:
            costo = float(costo_str) if costo_str else 0.0
            venta = float(venta_str) if venta_str else 0.0
            stock = int(stock_str) if stock_str else 0
        except ValueError:
            QMessageBox.critical(self, "Error", "Costo, Venta y Stock deben ser nÃºmeros vÃ¡lidos.")
            return

        productos = cargar_productos(self.username)
        producto_existente = next((p for p in productos if p.get('nombre') == nombre), None)
        if producto_existente:
            QMessageBox.information(self, "Error", "El producto ya existe. Usa la ediciÃ³n para actualizarlo.")
            return

        nuevo = {
            "nombre": nombre,
            "costo": costo,
            "venta": venta,
            "stock": stock,
            "image_path": None,
            "material": '',
            "marca": marca,
            "categoria": "",
            "seccion": "",
            "created_at": datetime.datetime.now().isoformat()
        }
        self._begin_product_creation_skeleton(nombre)
        if not agregar_producto(self.username, nuevo):
            self._end_product_creation_skeleton()
            QMessageBox.information(self, "Error", "No se pudo agregar el producto (duplicado o error de archivo).")
            return
        self.add_kardex_entry('Entrada', nombre, stock, costo)
        QMessageBox.information(self, "Éxito", "Producto agregado correctamente.")
        # limpiar campos rÃ¡pidos y refrescar
        try:
            self.quick_name.clear(); self.quick_costo.clear(); self.quick_venta.clear(); self.quick_stock.clear(); self.quick_marca.clear()
        except Exception:
            pass
        self.update_inventory_gallery()
        self._end_product_creation_skeleton()

    def open_product_dialog(self, producto=None):
        """Abrir el diÃ¡logo modal avanzado para crear/editar un producto."""
        self._sync_branch_context_from_parent()
        # Ã°Å¸â€ºÂ¡Ã¯Â¸Â VERIFICAR PERMISOS
        if self.parent_app and self.parent_app.is_helper:
            if producto:  # EDITAR
                if not self.parent_app.puede_hacer_accion('inventario', 'editar'):
                    QMessageBox.warning(
                        self,
                        "Permiso Denegado",
                        "No tienes permiso para editar productos."
                    )
                    return
            else:  # CREAR
                if not self.parent_app.puede_hacer_accion('inventario', 'crear'):
                    QMessageBox.warning(
                        self,
                        "Permiso Denegado",
                        "No tienes permiso para crear productos."
                    )
                    return
        
        dialog = OpticalProductDialog(producto, parent=self)
        dialog_result = dialog.exec_()
        self._refresh_side_section_combo()
        if dialog_result == QDialog.Accepted:
            print("[PRODUCTO] Dialog aceptado, procesando...", flush=True)
            show_creation_skeleton = not bool(producto)
            try:
                # Obtener los datos actualizados
                producto_actualizado = dialog.get_product_data()
                
                # Validar que producto_actualizado es un dict vÃ¡lido
                if not isinstance(producto_actualizado, dict):
                    raise ValueError(f"get_product_data() retornÃ³ tipo invÃ¡lido: {type(producto_actualizado)}")
                seccion = self._normalize_section_value(
                    producto_actualizado.get('categoria') or producto_actualizado.get('seccion')
                )
                producto_actualizado['categoria'] = seccion
                producto_actualizado['seccion'] = seccion                
                # Cargar productos existentes (convertir None a lista vacÃ­a y filtrar None items)
                productos = cargar_productos(self.username)
                if productos is None:
                    productos = []
                if not isinstance(productos, list):
                    productos = []
                # Filtrar items None de la lista
                productos = [p for p in productos if p is not None and isinstance(p, dict)]
                
                if producto:  # Si estamos editando
                    # Encontrar y actualizar el producto existente
                    for i, p in enumerate(productos):
                        try:
                            if p and isinstance(p, dict) and p.get('codigo') == producto.get('codigo') and p.get('nombre') == producto.get('nombre'):
                                productos[i] = producto_actualizado
                                break
                        except (AttributeError, TypeError) as e:
                            print(f"[ERROR] Error comparando producto en Ã­ndice {i}: {e}")
                            continue
                    operacion = "ACTUALIZAR"
                    # PASO 1: Guardar cambios localmente primero
                    print(f"[LOCAL] Guardando producto {operacion.lower()} localmente...", flush=True)
                    guardar_productos(self.username, productos)
                    print(f"[LOCAL] Producto guardado en JSON local", flush=True)
                else:  # Si es un nuevo producto
                    if not isinstance(producto_actualizado, dict):
                        raise ValueError("producto_actualizado debe ser un dict")
                    producto_actualizado['created_at'] = datetime.datetime.now().isoformat()
                    operacion = "CREAR"
                    self._begin_product_creation_skeleton(
                        str(producto_actualizado.get('nombre', '') or '').strip()
                    )
                    print(f"[LOCAL] Guardando producto {operacion.lower()} localmente...", flush=True)
                    if not agregar_producto(self.username, producto_actualizado):
                        raise ValueError("No se pudo crear el producto (duplicado o error de archivo)")
                    print(f"[LOCAL] Producto guardado en JSON local", flush=True)
                
                # Ã¢Å“â€¦ PASO 2: Recargar cachÃ© local desde archivo para sincronizar
                print(f"[CACHE] Recargando cachÃ© desde archivo...", flush=True)
                self.all_productos = cargar_productos(self.username) or []
                self.total_products = None  # Limpiar bÃºsquedas previas
                self.search_term = ""  # Limpiar bÃºsqueda
                print(f"[CACHE] Ã¢Å“â€œ {len(self.all_productos)} productos en cachÃ©", flush=True)
                
                # Ã¢Å“â€¦ PASO 3: Actualizar UI al instante (refresh completo)
                print(f"[UI] Actualizando inventario completo...", flush=True)
                self.update_inventory_gallery()
                print(f"[UI] Ã¢Å“â€œ Inventario actualizado - producto visible", flush=True)
                
                # Ã¢Å“â€¦ PASO 4: Mostrar mensaje de Ã©xito de inmediato
                msg = "Producto creado exitosamente" if not producto else "Producto actualizado exitosamente"
                print(f"[INFO] {msg}", flush=True)
                    
            except Exception as e:
                import traceback
                print(f"\n[ERROR_TRACEBACK] Error creando/editando producto:", flush=True)
                traceback.print_exc()
                print(f"[ERROR_MENSAJE] {str(e)}\n", flush=True)
                QMessageBox.warning(
                    self, 
                    "Error", 
                    f"No se pudo {'actualizar' if producto else 'crear'} el producto: {str(e)}"
                )
            finally:
                if show_creation_skeleton:
                    self._end_product_creation_skeleton()

    def apply_inventory_filters(self, *args, refresh_smart=False):
        """Aplica busqueda, filtro por seccion, marca y ordenamiento a los productos."""
        _ = args
        try:
            try:
                if self._inventory_filter_timer is not None and self._inventory_filter_timer.isActive():
                    self._inventory_filter_timer.stop()
            except Exception:
                pass
            search_text = self.side_search_entry.text().strip().lower() if hasattr(self, 'side_search_entry') else ''
            selected_section = ''
            selected_brand = ''
            if hasattr(self, 'side_section_combo'):
                selected_section = str(self.side_section_combo.currentData() or '').strip().lower()
            if hasattr(self, 'side_brand_combo'):
                selected_brand = str(self.side_brand_combo.currentData() or '').strip().lower()

            productos = self.all_productos if hasattr(self, 'all_productos') else []
            if not isinstance(productos, list):
                productos = []

            if selected_section:
                productos = [
                    p for p in productos
                    if self._get_product_section(p).lower() == selected_section
                ]

            if selected_brand:
                productos = [
                    p for p in productos
                    if str(p.get('marca', '')).strip().lower() == selected_brand
                ]

            if search_text:
                filtered = []
                for p in productos:
                    if not isinstance(p, dict):
                        continue
                    codigo = str(p.get('codigo', '')).lower()
                    nombre = str(p.get('nombre', '')).lower()
                    marca = str(p.get('marca', '')).lower()
                    section = self._get_product_section(p).lower()

                    if (
                        search_text in codigo or
                        search_text in nombre or
                        search_text in marca or
                        search_text in section
                    ):
                        filtered.append(p)
                productos = filtered

            sort_index = self.side_sort_combo.currentIndex() if hasattr(self, 'side_sort_combo') else 0
            if sort_index == 0:
                productos = sorted(productos, key=lambda x: x.get('created_at', ''), reverse=True)
            elif sort_index == 1:
                productos = sorted(productos, key=lambda x: x.get('created_at', ''))
            elif sort_index == 2:
                productos = sorted(productos, key=lambda x: x.get('nombre', '').lower())

            self.total_products = productos
            self.current_page = 0
            self.update_inventory_gallery(refresh_smart=bool(refresh_smart))
            self._update_pagination_buttons()

            if len(productos) == 0:
                print(f"[FILTROS] No se encontraron productos con '{search_text}'")
            else:
                print(f"[FILTROS] Se mostraron {len(productos)} productos")
        finally:
            self._set_inventory_filter_busy(False)

    def _get_inventory_products_for_report(self):
        productos = self.total_products if isinstance(self.total_products, list) else None
        if productos is None:
            productos = self.all_productos if isinstance(self.all_productos, list) else []
        return [p for p in (productos or []) if isinstance(p, dict)]

    def _get_inventory_export_column_defs(self):
        return {
            "codigo_nombre": {
                "label": "Código / Nombre",
                "width": 0.38,
                "value": lambda p: f"{str(p.get('codigo') or '').strip()} - {str(p.get('nombre') or '').strip() or 'N/A'}"
                if str(p.get("codigo") or "").strip()
                else (str(p.get("nombre") or "").strip() or "N/A"),
            },
            "costo": {
                "label": "Costo",
                "width": 0.10,
                "value": lambda p: str(p.get("precio_compra") or p.get("costo") or "0.00"),
            },
            "venta": {
                "label": "Venta",
                "width": 0.10,
                "value": lambda p: str(p.get("venta") or p.get("precio_venta") or p.get("precio") or "0.00"),
            },
            "stock": {
                "label": "Stock",
                "width": 0.08,
                "value": lambda p: str(p.get("stock") or "0"),
            },
            "material": {
                "label": "Material",
                "width": 0.16,
                "value": lambda p: str(p.get("material") or "N/A"),
            },
            "marca": {
                "label": "Marca",
                "width": 0.18,
                "value": lambda p: str(p.get("marca") or "N/A"),
            },
        }

    def _filter_inventory_export_products(self, productos, options=None):
        options = options or {}
        brand_mode = str(options.get("brand_mode") or "all").strip().lower()
        selected_brands = {
            str(brand).strip().lower()
            for brand in (options.get("brands") or [])
            if str(brand).strip()
        }
        filtered = list(productos or [])
        if brand_mode in {"include", "exclude"} and selected_brands:
            output = []
            for producto in filtered:
                marca = str(producto.get("marca") or "").strip().lower()
                if brand_mode == "include" and marca in selected_brands:
                    output.append(producto)
                elif brand_mode == "exclude" and marca not in selected_brands:
                    output.append(producto)
            filtered = output
        return filtered

    def _print_inventory_report(self):
        productos = self._get_inventory_products_for_report()
        if not productos:
            QMessageBox.information(
                self,
                "Imprimir inventario",
                "No hay productos para imprimir en el inventario actual.",
            )
            return

        now = datetime.datetime.now()
        rows = []
        for producto in productos:
            codigo = str(producto.get("codigo") or "").strip()
            nombre = str(producto.get("nombre") or "").strip() or "N/A"
            codigo_nombre = f"{codigo} - {nombre}" if codigo else nombre
            costo = str(producto.get("precio_compra") or producto.get("costo") or "0.00")
            venta = str(producto.get("precio_venta") or producto.get("precio") or "0.00")
            stock = str(producto.get("stock") or "0")
            material = str(producto.get("material") or "N/A")
            marca = str(producto.get("marca") or "N/A")
            rows.append(
                f"""
                <tr>
                    <td>{codigo_nombre}</td>
                    <td>{costo}</td>
                    <td>{venta}</td>
                    <td>{stock}</td>
                    <td>{material}</td>
                    <td>{marca}</td>
                </tr>
                """
            )

        section_text = "Todas las secciones"
        if hasattr(self, "side_section_combo"):
            section_text = str(self.side_section_combo.currentText() or section_text).strip() or section_text

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    color: #111827;
                    margin: 20px;
                }}
                h1 {{
                    font-size: 20px;
                    margin-bottom: 2px;
                }}
                .meta {{
                    font-size: 11px;
                    color: #4B5563;
                    margin-bottom: 14px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 10px;
                }}
                th {{
                    background: #111111;
                    color: white;
                    text-align: left;
                    padding: 6px;
                    border: 1px solid #D1D5DB;
                }}
                td {{
                    padding: 6px;
                    border: 1px solid #E5E7EB;
                }}
                tr:nth-child(even) {{
                    background: #F9FAFB;
                }}
            </style>
        </head>
        <body>
            <h1>Inventario</h1>
            <div class="meta">
                Generado: {now.strftime("%d/%m/%Y %H:%M")}<br>
                Sección: {section_text}<br>
                Total de productos visibles: {len(productos)}
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Código / Nombre</th>
                        <th>Costo</th>
                        <th>Venta</th>
                        <th>Stock</th>
                        <th>Material</th>
                        <th>Marca</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </body>
        </html>
        """

        document = QtGui.QTextDocument(self)
        document.setHtml(html)

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageMargins(12, 12, 12, 12, QPrinter.Millimeter)
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Imprimir inventario")
        preview.paintRequested.connect(document.print_)
        preview.exec_()

    def _open_inventory_pdf_customizer(self):
        productos = self._get_inventory_products_for_report()
        if not productos:
            QMessageBox.information(
                self,
                "PDF de inventario",
                "No hay productos para personalizar el PDF del inventario actual.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Personalizar PDF de inventario")
        dialog.setMinimumWidth(560)
        dialog.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
            }
            QGroupBox {
                font-weight: 700;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        info = QLabel("Elige qué columnas y qué marcas quieres incluir en el PDF antes de generarlo.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #4B5563;")
        layout.addWidget(info)

        columns_group = QGroupBox("Columnas")
        columns_layout = QGridLayout(columns_group)
        columns_layout.setHorizontalSpacing(16)
        columns_layout.setVerticalSpacing(10)

        column_specs = [
            ("codigo_nombre", "Código / Nombre", True),
            ("costo", "Costo", True),
            ("venta", "Venta", True),
            ("stock", "Stock", True),
            ("material", "Material", True),
            ("marca", "Marca", True),
        ]
        column_checks = {}
        for idx, (key, label, checked) in enumerate(column_specs):
            checkbox = QCheckBox(label)
            checkbox.setChecked(checked)
            columns_layout.addWidget(checkbox, idx // 2, idx % 2)
            column_checks[key] = checkbox
        layout.addWidget(columns_group)

        brand_group = QGroupBox("Filtro por marca")
        brand_layout = QVBoxLayout(brand_group)
        brand_layout.setSpacing(10)

        brand_mode_combo = QComboBox()
        brand_mode_combo.addItem("Todas las marcas", "all")
        brand_mode_combo.addItem("Solo marcas seleccionadas", "include")
        brand_mode_combo.addItem("Excluir marcas seleccionadas", "exclude")
        brand_layout.addWidget(brand_mode_combo)

        brand_list = QListWidget()
        brand_list.setSelectionMode(QAbstractItemView.NoSelection)
        brand_list.setMinimumHeight(180)
        unique_brands = sorted({
            str(p.get("marca") or "").strip()
            for p in productos
            if str(p.get("marca") or "").strip()
        }, key=lambda x: x.lower())
        for brand in unique_brands:
            item = QListWidgetItem(brand)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            brand_list.addItem(item)
        brand_layout.addWidget(brand_list)
        layout.addWidget(brand_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F3F4F6;
                color: #111827;
                border: 1px solid #D1D5DB;
                padding: 8px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #E5E7EB;
            }
        """)
        btn_cancel.clicked.connect(dialog.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_generate = QPushButton("Generar PDF")
        btn_generate.setStyleSheet("""
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1D4ED8;
            }
        """)
        buttons_layout.addWidget(btn_generate)
        layout.addLayout(buttons_layout)

        def _generate():
            selected_columns = [
                key for key, checkbox in column_checks.items()
                if checkbox.isChecked()
            ]
            if not selected_columns:
                QMessageBox.warning(dialog, "PDF de inventario", "Selecciona al menos una columna.")
                return

            selected_brands = []
            for index in range(brand_list.count()):
                item = brand_list.item(index)
                if item is not None and item.checkState() == Qt.Checked:
                    selected_brands.append(str(item.text()).strip())

            options = {
                "columns": selected_columns,
                "brand_mode": str(brand_mode_combo.currentData() or "all"),
                "brands": selected_brands,
            }
            dialog.accept()
            self._export_inventory_pdf(options=options)

        btn_generate.clicked.connect(_generate)
        dialog.exec_()

    def _open_inventory_excel_customizer(self):
        productos = self._get_inventory_products_for_report()
        if not productos:
            QMessageBox.information(
                self,
                "Excel de inventario",
                "No hay productos para personalizar el Excel del inventario actual.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Personalizar Excel de inventario")
        dialog.setMinimumWidth(580)
        dialog.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
            }
            QGroupBox {
                font-weight: 700;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        info = QLabel("Elige qué columnas y qué marcas quieres incluir en el Excel. También puedes separarlo por hojas según la marca.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #4B5563;")
        layout.addWidget(info)

        columns_group = QGroupBox("Columnas")
        columns_layout = QGridLayout(columns_group)
        columns_layout.setHorizontalSpacing(16)
        columns_layout.setVerticalSpacing(10)

        column_specs = [
            ("codigo_nombre", "Código / Nombre", True),
            ("costo", "Costo", True),
            ("venta", "Venta", True),
            ("stock", "Stock", True),
            ("material", "Material", True),
            ("marca", "Marca", True),
        ]
        column_checks = {}
        for idx, (key, label, checked) in enumerate(column_specs):
            checkbox = QCheckBox(label)
            checkbox.setChecked(checked)
            columns_layout.addWidget(checkbox, idx // 2, idx % 2)
            column_checks[key] = checkbox
        layout.addWidget(columns_group)

        brand_group = QGroupBox("Filtro por marca")
        brand_layout = QVBoxLayout(brand_group)
        brand_layout.setSpacing(10)

        brand_mode_combo = QComboBox()
        brand_mode_combo.addItem("Todas las marcas", "all")
        brand_mode_combo.addItem("Solo marcas seleccionadas", "include")
        brand_mode_combo.addItem("Excluir marcas seleccionadas", "exclude")
        brand_layout.addWidget(brand_mode_combo)

        brand_list = QListWidget()
        brand_list.setSelectionMode(QAbstractItemView.NoSelection)
        brand_list.setMinimumHeight(180)
        unique_brands = sorted({
            str(p.get("marca") or "").strip()
            for p in productos
            if str(p.get("marca") or "").strip()
        }, key=lambda x: x.lower())
        for brand in unique_brands:
            item = QListWidgetItem(brand)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            brand_list.addItem(item)
        brand_layout.addWidget(brand_list)
        layout.addWidget(brand_group)

        extra_group = QGroupBox("Opciones")
        extra_layout = QVBoxLayout(extra_group)
        extra_layout.setSpacing(8)
        split_by_brand_check = QCheckBox("Separar hojas por marca")
        extra_layout.addWidget(split_by_brand_check)
        layout.addWidget(extra_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F3F4F6;
                color: #111827;
                border: 1px solid #D1D5DB;
                padding: 8px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #E5E7EB;
            }
        """)
        btn_cancel.clicked.connect(dialog.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_generate = QPushButton("Generar Excel")
        btn_generate.setStyleSheet("""
            QPushButton {
                background: #15803D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #166534;
            }
        """)
        buttons_layout.addWidget(btn_generate)
        layout.addLayout(buttons_layout)

        def _generate():
            selected_columns = [
                key for key, checkbox in column_checks.items()
                if checkbox.isChecked()
            ]
            if not selected_columns:
                QMessageBox.warning(dialog, "Excel de inventario", "Selecciona al menos una columna.")
                return

            selected_brands = []
            for index in range(brand_list.count()):
                item = brand_list.item(index)
                if item is not None and item.checkState() == Qt.Checked:
                    selected_brands.append(str(item.text()).strip())

            options = {
                "columns": selected_columns,
                "brand_mode": str(brand_mode_combo.currentData() or "all"),
                "brands": selected_brands,
                "split_by_brand": bool(split_by_brand_check.isChecked()),
            }
            dialog.accept()
            self._export_inventory_excel(options=options)

        btn_generate.clicked.connect(_generate)
        dialog.exec_()

    def _export_inventory_pdf(self, options=None):
        productos = self._get_inventory_products_for_report()
        options = options or {}
        selected_columns = list(options.get("columns") or [
            "codigo_nombre", "costo", "venta", "stock", "material", "marca"
        ])
        productos = self._filter_inventory_export_products(productos, options=options)

        if not productos:
            QMessageBox.information(
                self,
                "Imprimir inventario",
                "No hay productos para generar el PDF con los filtros elegidos.",
            )
            return

        now = datetime.datetime.now()
        section_text = "Todas las secciones"
        if hasattr(self, "side_section_combo"):
            section_text = str(self.side_section_combo.currentText() or section_text).strip() or section_text

        temp_dir = BASE_DIR / "VISO" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = temp_dir / f"inventario_{self.username}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=10 * mm,
            rightMargin=10 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )

        styles = getSampleStyleSheet()
        story = []
        
        # Obtener nombre de la sucursal activa para el título
        branch_name = "Todas las sucursales"
        try:
            from utils.file_handler import get_effective_branch_context
            ctx = get_effective_branch_context(self.username)
            # Solo usar la etiqueta (nombre) si existe
            if ctx and ctx.get("label"):
                branch_name = str(ctx.get("label")).strip()
        except Exception:
            pass
            
        story.append(Paragraph(f"<b>Inventario de la Tienda: {branch_name}</b>", styles["Title"]))
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                f"Generado: {now.strftime('%d/%m/%Y %H:%M')}<br/>"
                f"Sección: {section_text}<br/>"
                f"Total de productos visibles: {len(productos)}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 5 * mm))

        column_defs = {
            "codigo_nombre": {
                "label": "Código / Nombre",
                "width": 0.38,
                "value": lambda p: f"{str(p.get('codigo') or '').strip()} - {str(p.get('nombre') or '').strip() or 'N/A'}"
                if str(p.get("codigo") or "").strip()
                else (str(p.get("nombre") or "").strip() or "N/A"),
            },
            "costo": {
                "label": "Costo",
                "width": 0.10,
                "value": lambda p: str(p.get("precio_compra") or p.get("costo") or "0.00"),
            },
            "venta": {
                "label": "Venta",
                "width": 0.10,
                "value": lambda p: str(p.get("venta") or p.get("precio_venta") or p.get("precio") or "0.00"),
            },
            "stock": {
                "label": "Stock",
                "width": 0.08,
                "value": lambda p: str(p.get("stock") or "0"),
            },
            "material": {
                "label": "Material",
                "width": 0.16,
                "value": lambda p: str(p.get("material") or "N/A"),
            },
            "marca": {
                "label": "Marca",
                "width": 0.18,
                "value": lambda p: str(p.get("marca") or "N/A"),
            },
        }

        active_columns = [key for key in selected_columns if key in column_defs]
        if not active_columns:
            active_columns = ["codigo_nombre"]

        data = [[column_defs[key]["label"] for key in active_columns]]

        for producto in productos:
            data.append([column_defs[key]["value"](producto) for key in active_columns])

        page_width = A4[0] - (20 * mm)
        total_ratio = sum(column_defs[key]["width"] for key in active_columns) or 1.0
        col_widths = [
            page_width * (column_defs[key]["width"] / total_ratio)
            for key in active_columns
        ]

        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 1), (3, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))

        story.append(table)
        
        # --- CÁLCULO DE TOTALES AL FINAL ---
        total_stock = 0
        valor_total_inventario = 0.0
        
        for p in productos:
            try:
                s = int(float(p.get("stock", 0) or 0))
                # Intentar obtener costo de varios campos posibles
                c = float(str(p.get("precio_compra") or p.get("costo") or 0).replace(",", "").replace(" ", "") or 0)
                
                total_stock += s
                valor_total_inventario += (s * c)
            except Exception:
                continue

        story.append(Spacer(1, 10 * mm))
        
        # Crear una pequeña tabla de resumen para los totales
        resumen_data = [
            ["RESUMEN DE INVENTARIO", ""],
            ["Total Unidades (Stock):", f"{total_stock}"],
            ["Valor Total Inventario (Costo x Stock):", f"S/ {valor_total_inventario:,.2f}"]
        ]
        
        resumen_table = Table(resumen_data, colWidths=[80 * mm, 40 * mm])
        resumen_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TEXTCOLOR", (1, 2), (1, 2), colors.HexColor("#0d6efd")), # Color azul para el valor monetario
            ("FONTNAME", (1, 2), (1, 2), "Helvetica-Bold"),
        ]))
        
        story.append(resumen_table)
        
        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.gray)
            page_num = canvas.getPageNumber()
            text = f"Página {page_num}"
            # Dibujar a la derecha, 10mm desde el borde derecho y 10mm desde abajo
            canvas.drawRightString(A4[0] - 10 * mm, 10 * mm, text)
            canvas.restoreState()

        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
        open_pdf_with_chrome(str(pdf_path))

    def _export_inventory_excel(self, options=None):
        options = options or {}
        productos = self._filter_inventory_export_products(
            self._get_inventory_products_for_report(),
            options=options,
        )
        if not productos:
            QMessageBox.information(
                self,
                "Excel de inventario",
                "No hay productos para generar el Excel con los filtros elegidos.",
            )
            return

        selected_columns = list(options.get("columns") or [
            "codigo_nombre", "costo", "venta", "stock", "material", "marca"
        ])
        split_by_brand = bool(options.get("split_by_brand"))
        column_defs = self._get_inventory_export_column_defs()
        active_columns = [key for key in selected_columns if key in column_defs]
        if not active_columns:
            active_columns = ["codigo_nombre"]

        now = datetime.datetime.now()
        temp_dir = BASE_DIR / "VISO" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"inventario_{self.username}_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"

        try:
            import xlsxwriter
        except ImportError:
            QMessageBox.warning(
                self,
                "Excel de inventario",
                "Esta compilación no incluye soporte Excel (xlsxwriter).",
            )
            return

        workbook = xlsxwriter.Workbook(str(file_path))
        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#111111",
            "font_color": "#FFFFFF",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })
        cell_format = workbook.add_format({
            "border": 1,
            "valign": "vcenter",
        })
        meta_format = workbook.add_format({
            "font_color": "#4B5563",
        })

        def _sheet_name(value):
            text = str(value or "").strip() or "Sin marca"
            text = text.replace("[", "(").replace("]", ")").replace(":", "-").replace("/", "-").replace("\\", "-").replace("?", "").replace("*", "")
            return text[:31] or "Sin marca"

        def _write_sheet(worksheet, items, sheet_title):
            section_text = "Todas las secciones"
            if hasattr(self, "side_section_combo"):
                section_text = str(self.side_section_combo.currentText() or section_text).strip() or section_text

            worksheet.write(0, 0, "Inventario")
            worksheet.write(1, 0, f"Generado: {now.strftime('%d/%m/%Y %H:%M')}", meta_format)
            worksheet.write(2, 0, f"Sección: {section_text}", meta_format)
            worksheet.write(3, 0, f"Hoja: {sheet_title}", meta_format)
            worksheet.write(4, 0, f"Total de productos: {len(items)}", meta_format)

            for col_idx, key in enumerate(active_columns):
                worksheet.write(6, col_idx, column_defs[key]["label"], header_format)

            for row_idx, producto in enumerate(items, start=7):
                for col_idx, key in enumerate(active_columns):
                    worksheet.write(row_idx, col_idx, column_defs[key]["value"](producto), cell_format)

            for col_idx, key in enumerate(active_columns):
                width = max(len(column_defs[key]["label"]) + 2, int(18 + (column_defs[key]["width"] * 30)))
                if key == "codigo_nombre":
                    width = max(width, 32)
                worksheet.set_column(col_idx, col_idx, width)

        if split_by_brand:
            grouped = {}
            for producto in productos:
                brand = str(producto.get("marca") or "").strip() or "Sin marca"
                grouped.setdefault(brand, []).append(producto)

            for brand, items in sorted(grouped.items(), key=lambda pair: pair[0].lower()):
                worksheet = workbook.add_worksheet(_sheet_name(brand))
                _write_sheet(worksheet, items, brand)
        else:
            worksheet = workbook.add_worksheet("Inventario")
            _write_sheet(worksheet, productos, "Inventario")

        workbook.close()
        try:
            os.startfile(str(file_path))
        except Exception:
            QMessageBox.information(
                self,
                "Excel de inventario",
                f"Excel generado en:\n{file_path}",
            )

    def refresh_inventory_page(self):
        """Recarga inventario sin bloquear UI (remoto-first con loader)."""
        if getattr(self, "_initial_data_loading", False):
            print("[REFRESH] La carga inicial sigue en progreso, se omite recarga manual.", flush=True)
            return
        if self._refresh_in_progress:
            print("[REFRESH] Ya hay una recarga en progreso, ignorando solicitud.", flush=True)
            return

        self._refresh_in_progress = True
        print("[REFRESH] Recargando productos (remoto-first)...", flush=True)
        self._sync_branch_context_from_parent()

        if hasattr(self, "btn_refresh"):
            self.btn_refresh.setText("Cargando...")
            self.btn_refresh.setEnabled(False)

        self._show_inventory_loader(
            title="Actualizando inventario",
            subtitle="Consultando datos en internet y sincronizando respaldo local."
        )

        def _refresh_worker():
            result = {
                "productos": [],
                "source": "local_fallback",
                "error": None,
            }
            try:
                # Siempre cargar local primero (cache). En vista global usamos consolidado.
                try:
                    ctx = get_effective_branch_context(self.username) or {}
                    branch_code = str(ctx.get("code", "") or "").strip().upper()
                except Exception:
                    branch_code = ""
                vista_global = not bool(branch_code)
                from utils.sync_manager import get_sync_manager

                sync_mgr = get_sync_manager()
                if sync_mgr.check_internet():
                    result["productos"] = cargar_productos(self.username, prefer_cloud=True) or []
                    result["source"] = "cloud_priority"
                else:
                    if vista_global:
                        result["productos"] = cargar_productos_dashboard(self.username, allow_remote_restore=False) or []
                    else:
                        result["productos"] = cargar_productos(self.username, prefer_cloud=False) or []
                    result["source"] = "local_offline"
            except Exception as e:
                result["error"] = str(e)
                try:
                    try:
                        ctx = get_effective_branch_context(self.username) or {}
                        branch_code = str(ctx.get("code", "") or "").strip().upper()
                        vista_global = not bool(branch_code)
                    except Exception:
                        vista_global = True

                    if vista_global:
                        result["productos"] = cargar_productos_dashboard(self.username, allow_remote_restore=False) or []
                    else:
                        result["productos"] = cargar_productos(self.username, prefer_cloud=False) or []
                    result["source"] = "local_error_fallback"
                except Exception:
                    result["productos"] = []

            self.refresh_cargado.emit(result)

        import threading
        threading.Thread(target=_refresh_worker, daemon=True).start()

    def _on_refresh_cargado(self, result):
        """Aplica en UI el resultado de la recarga remota/local."""
        try:
            if not isinstance(result, dict):
                result = {}

            productos = result.get("productos")
            if not isinstance(productos, list):
                productos = []
            source = str(result.get("source", "unknown"))
            error_msg = result.get("error")

            self.all_productos = productos
            self._refresh_side_section_combo()

            if hasattr(self, "side_search_entry"):
                self.side_search_entry.clear()
            self.total_products = None
            self.current_page = 0
            self.search_term = ""
            self.apply_inventory_filters()

            if error_msg:
                print(f"[REFRESH] Error en recarga: {error_msg}", flush=True)
            print(f"[REFRESH] Fuente={source} | productos={len(self.all_productos)}", flush=True)

            if source == "remote_empty_keep_local":
                try:
                    QMessageBox.information(
                        self,
                        "Inventario en linea vacio",
                        "No hay productos en linea para esta sucursal.\n\n"
                        "Se esta mostrando el inventario local (cache).\n"
                        "Usa 'Sincronizar Ahora' para subir tus productos."
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"[REFRESH] Error aplicando resultado: {e}", flush=True)
        finally:
            self._refresh_in_progress = False
            self._stop_inventory_loader_animation()
            if hasattr(self, "btn_refresh"):
                self.btn_refresh.setText("Actualizar Página")
                self.btn_refresh.setEnabled(True)
    
    # MÃ©todos deprecated - ya no se usan, mantener por compatibilidad

    # ============================
    # Funciones Kardex
    # ============================
    def add_kardex_entry(self, movimiento, producto_nombre, cantidad, costo_unitario):
        productos = cargar_productos(self.username)
        prod_info = next((p for p in productos if p['nombre'] == producto_nombre), None)
        stock_final = prod_info['stock'] if prod_info else 0

        # Si el costo es 0, usar precio de venta como referencia
        real_costo = costo_unitario
        if real_costo == 0 and prod_info:
            real_costo = float(prod_info.get('venta', 0) or 0)

        entry = {
            'fecha': datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'movimiento': movimiento,
            'producto': producto_nombre,
            'cantidad': cantidad,
            'costo_unitario': real_costo,
            'valor_total': real_costo * cantidad,
            'stock_final': stock_final
        }

        try:
            from utils.file_handler import agregar_movimiento_kardex

            if agregar_movimiento_kardex(self.username, entry):
                return
        except Exception:
            pass

        kardex_data = cargar_kardex(self.username)
        kardex_data.append(entry)
        guardar_kardex(self.username, kardex_data)

    def update_kardex_table(self):
        self.tree_kardex.setRowCount(0)
        
        # Cargar datos frescos
        raw_kardex_data = cargar_kardex(self.username)
        
        # Cargar productos para buscar cÃ³digos
        products_list = cargar_productos(self.username) or []
        # Crear mapa nombre -> codigo
        product_code_map = {}
        for p in products_list:
            if p.get('nombre'):
                product_code_map[p.get('nombre')] = p.get('codigo', '')

        # Crear lista de tuplas (indice_original, datos) para preservar referencia al eliminar
        indexed_data = list(enumerate(raw_kardex_data))
        
        # Obtener valores de filtros si existen (pueden no estar inicializados aÃºn la primera vez)
        start_date = getattr(self, 'kardex_date_from', None)
        end_date = getattr(self, 'kardex_date_to', None)
        search_txt = getattr(self, 'kardex_txt_search', None)
        
        start_date_py = start_date.date().toPyDate() if start_date else None
        end_date_py = end_date.date().toPyDate() if end_date else None
        search_term = search_txt.text().lower().strip() if search_txt else ""

        # Ordenar por fecha descendente (manteniendo la tupla con el Ã­ndice original)
        try:
            indexed_data.sort(
                key=lambda x: datetime.datetime.strptime(x[1].get('fecha', '').split('.')[0], "%d/%m/%Y %H:%M:%S") if x[1].get('fecha') else datetime.datetime.min,
                reverse=True
            )
        except:
            pass

        row_idx = 0
        for original_index, entry in indexed_data:
            # --- NORMALIZAR DATOS ---
            producto_nombre = entry.get('producto') or entry.get('producto_nombre') or ""
            movimiento = entry.get('movimiento') or entry.get('tipo') or "Desconocido"
            movimiento = movimiento.capitalize()
            
            # Buscar cÃ³digo
            codigo_prod = product_code_map.get(producto_nombre, "")

            # --- APLICAR FILTROS ---
            fecha_str = entry.get('fecha', '')
            
            # Filtro de bÃºsqueda (nombre o cÃ³digo)
            if search_term and (search_term not in producto_nombre.lower() and search_term not in codigo_prod.lower()):
                continue

            # Filtro de fecha
            if start_date_py and end_date_py and fecha_str:
                try:
                    date_part = fecha_str.split(' ')[0]
                    if '-' in date_part:
                        entry_date = datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
                    else:
                        entry_date = datetime.datetime.strptime(date_part, "%d/%m/%Y").date()
                        
                    if not (start_date_py <= entry_date <= end_date_py):
                        continue
                except:
                    pass

            self.tree_kardex.insertRow(row_idx)
            
            # Extraer fecha
            fecha = entry.get('fecha', '')
            if 'T' in fecha:
                fecha = fecha.split('T')[0]
            
            # Columna 0: Fecha (Guardamos el Ã­ndice original aquÃ­ para borrar despuÃ©s)
            fecha_item = QTableWidgetItem(fecha)
            fecha_item.setData(Qt.UserRole, original_index)
            self.tree_kardex.setItem(row_idx, 0, fecha_item)
            
            # Columna 1: Movimiento
            mov_item = QTableWidgetItem(movimiento)
            if movimiento.lower().startswith("salida"):
                mov_item.setForeground(QtGui.QColor("#B71C1C")) # Dark red
            elif movimiento.lower().startswith("entrada"):
                mov_item.setForeground(QtGui.QColor("#1B5E20")) # Dark green
            self.tree_kardex.setItem(row_idx, 1, mov_item)
            
            # Columna 2: CÃ³digo
            self.tree_kardex.setItem(row_idx, 2, QTableWidgetItem(codigo_prod))

            # Columna 3: Producto
            self.tree_kardex.setItem(row_idx, 3, QTableWidgetItem(producto_nombre))
            
            # Columna 4: Cantidad
            cantidad = entry.get('cantidad', 0)
            self.tree_kardex.setItem(row_idx, 4, QTableWidgetItem(str(cantidad)))
            
            # Columna 5: Costo Total
            if movimiento.lower().startswith("entrada"):
                costo_display = "None"
            else:
                try:
                    if 'valor_total' in entry:
                        valor_total = float(entry['valor_total'])
                    else:
                        cantidad_num = float(cantidad) if cantidad else 0
                        precio = float(entry.get('costo_unitario', entry.get('precio', entry.get('costo', 0))) or 0)
                        valor_total = cantidad_num * precio
                    costo_display = f"S/{valor_total:.2f}"
                except (ValueError, TypeError):
                    costo_display = "S/0.00"
            
            self.tree_kardex.setItem(row_idx, 5, QTableWidgetItem(costo_display))
            
            # Columna 6: Stock Final
            stock_final = entry.get('stock_final', entry.get('stock', entry.get('stock_nuevo', '')))
            self.tree_kardex.setItem(row_idx, 6, QTableWidgetItem(str(stock_final)))
            row_idx += 1

    def delete_selected_kardex_items(self):
        """Elimina los elementos seleccionados del historial."""
        selected_rows = self.tree_kardex.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Eliminar", "Por favor, selecciona al menos un registro para eliminar.")
            return
            
        count = len(selected_rows)
        reply = QMessageBox.question(
            self, 
            "Confirmar EliminaciÃ³n", 
                f"¿Estás seguro de eliminar {count} registro(s) del historial?\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Obtener los Ã­ndices originales a eliminar
            indices_to_delete = set()
            for index in selected_rows:
                # El Ã­ndice original estÃ¡ guardado en la columna 0
                item = self.tree_kardex.item(index.row(), 0)
                original_index = item.data(Qt.UserRole)
                if original_index is not None:
                    indices_to_delete.add(original_index)
            
            # Cargar datos actuales
            current_data = cargar_kardex(self.username)
            
            # Crear nueva lista excluyendo los Ã­ndices marcados
            # Usamos enumerate para comparar con los Ã­ndices originales que recolectamos
            new_data = [item for i, item in enumerate(current_data) if i not in indices_to_delete]
            
            # Guardar y recargar
            guardar_kardex(self.username, new_data)
            self.update_kardex_table()
            
            QMessageBox.information(self, "Éxito", "Registros eliminados correctamente.")

    def export_kardex_to_excel(self):
        """Exporta los datos visibles del Kardex a Excel Profesional con estadÃ­sticas."""
        if self.tree_kardex.rowCount() == 0:
            QMessageBox.warning(self, "Exportar", "No hay datos para exportar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte Kardex", "", "Excel (*.xlsx)")
        if not file_path:
            return

        try:
            try:
                import xlsxwriter
            except Exception:
                QMessageBox.critical(
                    self,
                    "Exportar",
                    "Esta compilacion no incluye soporte Excel (xlsxwriter).",
                )
                return

            workbook = xlsxwriter.Workbook(file_path)
            
            # --- ESTILOS ---
            header_format = workbook.add_format({
                'bold': True, 'font_color': 'white', 'bg_color': '#2C3E50',
                'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm', 'align': 'center'})
            currency_format = workbook.add_format({'num_format': '"S/ " #,##0.00', 'align': 'right'})
            text_center = workbook.add_format({'align': 'center'})
            text_left = workbook.add_format({'align': 'left'})
            
            # Estilos de Movimiento
            mov_entrada = workbook.add_format({'font_color': '#1B5E20', 'bold': True, 'align': 'center'})
            mov_salida = workbook.add_format({'font_color': '#B71C1C', 'bold': True, 'align': 'center'})
            
            # Estilos Resumen
            title_format = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#2C3E50'})
            stat_label = workbook.add_format({'bold': True, 'bg_color': '#ECF0F1', 'border': 1})
            stat_value = workbook.add_format({'border': 1, 'align': 'right'})
            stat_currency = workbook.add_format({'border': 1, 'num_format': '"S/ " #,##0.00', 'align': 'right', 'bold': True})

            # === HOJA 1: RESUMEN ESTADÃSTICO ===
            ws_stats = workbook.add_worksheet("Resumen")
            ws_stats.set_column('A:A', 5)
            ws_stats.set_column('B:B', 30)
            ws_stats.set_column('C:C', 20)
            ws_stats.hide_gridlines(2)
            
            # Recolectar estadÃ­sticas de los datos VISIBLES en la tabla
            rows_data = []
            total_entradas_qty = 0
            total_entradas_val = 0.0
            total_salidas_qty = 0
            total_salidas_val = 0.0
            
            # Diccionario para top productos
            product_counts = {}

            for r in range(self.tree_kardex.rowCount()):
                fecha = self.tree_kardex.item(r, 0).text()
                movimiento = self.tree_kardex.item(r, 1).text()
                codigo = self.tree_kardex.item(r, 2).text()
                producto = self.tree_kardex.item(r, 3).text()
                cantidad = int(self.tree_kardex.item(r, 4).text() or 0)
                total_str = self.tree_kardex.item(r, 5).text().replace("S/", "").replace("None", "0").strip()
                stock = self.tree_kardex.item(r, 6).text()
                
                try:
                    valor = float(total_str)
                except:
                    valor = 0.0
                
                rows_data.append([fecha, movimiento, codigo, producto, cantidad, valor, stock])
                
                # EstadÃ­sticas
                if movimiento.lower().startswith("entrada"):
                    total_entradas_qty += cantidad
                    total_entradas_val += valor
                elif movimiento.lower().startswith("salida"):
                    total_salidas_qty += cantidad
                    total_salidas_val += valor
                
                product_counts[producto] = product_counts.get(producto, 0) + cantidad

            # Escribir Resumen
            ws_stats.write(1, 1, "Reporte de Kardex - EstadÃ­sticas", title_format)
            ws_stats.write(3, 1, f"Fecha de EmisiÃ³n: {datetime.datetime.now().strftime('%d/%m/%Y')}")
            
            ws_stats.write(5, 1, "MÃ©tricas Generales", header_format)
            ws_stats.write(6, 1, "Total Movimientos Registrados", stat_label)
            ws_stats.write(6, 2, len(rows_data), stat_value)
            
            ws_stats.write(8, 1, "Resumen de Entradas", header_format)
            ws_stats.write(9, 1, "Total Unidades Ingresadas", stat_label)
            ws_stats.write(9, 2, total_entradas_qty, stat_value)
            ws_stats.write(10, 1, "Valor Total Entradas", stat_label)
            ws_stats.write(10, 2, total_entradas_val, stat_currency)
            
            ws_stats.write(12, 1, "Resumen de Salidas (Ventas)", header_format)
            ws_stats.write(13, 1, "Total Unidades Vendidas", stat_label)
            ws_stats.write(13, 2, total_salidas_qty, stat_value)
            ws_stats.write(14, 1, "Valor Total Salidas", stat_label)
            ws_stats.write(14, 2, total_salidas_val, stat_currency)
            
            # Top 5 Productos
            ws_stats.write(16, 1, "Top 5 Productos con mÃ¡s movimiento", header_format)
            sorted_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            row_idx = 17
            for name, count in sorted_products:
                ws_stats.write(row_idx, 1, name, stat_label)
                ws_stats.write(row_idx, 2, count, stat_value)
                row_idx += 1

            # === HOJA 2: KARDEX DETALLADO ===
            ws_data = workbook.add_worksheet("Kardex Detallado")
            
            # Configurar anchos de columna (Esto soluciona los #####)
            ws_data.set_column('A:A', 20) # Fecha
            ws_data.set_column('B:B', 15) # Movimiento
            ws_data.set_column('C:C', 15) # CÃ³digo
            ws_data.set_column('D:D', 40) # Producto
            ws_data.set_column('E:E', 12) # Cantidad
            ws_data.set_column('F:F', 15) # Costo Total
            ws_data.set_column('G:G', 12) # Stock Final
            
            # Encabezados
            headers = ["Fecha", "Movimiento", "CÃ³digo", "Producto", "Cantidad", "Valor Total", "Stock Final"]
            for col, text in enumerate(headers):
                ws_data.write(0, col, text, header_format)
            
            # Activar filtros automÃ¡ticos (El "Buscador")
            ws_data.autofilter(0, 0, len(rows_data), 6)
            ws_data.freeze_panes(1, 0) # Congelar encabezado
            
            # Escribir datos
            for i, row_vals in enumerate(rows_data):
                # row_vals: [fecha, movimiento, codigo, producto, cantidad, valor, stock]
                ws_data.write(i + 1, 0, row_vals[0], text_center) # Fecha
                
                mov = row_vals[1]
                fmt = mov_entrada if mov.lower().startswith('entrada') else (mov_salida if mov.lower().startswith('salida') else text_center)
                ws_data.write(i + 1, 1, mov, fmt)
                
                ws_data.write(i + 1, 2, row_vals[2], text_center) # CÃ³digo
                ws_data.write(i + 1, 3, row_vals[3], text_left)   # Producto
                ws_data.write_number(i + 1, 4, row_vals[4], text_center) # Cantidad
                
                # Para entradas, mostrar "None" en la columna de valor
                if mov.lower().startswith("entrada"):
                    ws_data.write(i + 1, 5, "None", text_center)
                else:
                    ws_data.write_number(i + 1, 5, row_vals[5], currency_format)
                    
                # Stock Final
                try:
                    s_val = int(float(str(row_vals[6])))
                    ws_data.write_number(i + 1, 6, s_val, text_center)
                except:
                    ws_data.write(i + 1, 6, str(row_vals[6]), text_center)

            workbook.close()
            
            # DiÃ¡logo de Ã©xito
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("ExportaciÃ³n Exitosa")
            msg_box.setText(f"El reporte profesional se ha generado en:\n{file_path}")
            msg_box.setIcon(QMessageBox.Information)
            
            btn_abrir = msg_box.addButton("Abrir Excel", QMessageBox.AcceptRole)
            btn_cerrar = msg_box.addButton("Cerrar", QMessageBox.RejectRole)
            
            msg_box.exec_()
            
            if msg_box.clickedButton() == btn_abrir:
                os.startfile(file_path)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar Excel: {str(e)}")

    def load_products(self):
        """Recarga la lista de productos en el inventario."""
        # Este mÃ©todo se llama despuÃ©s de crear un nuevo producto
        # para actualizar la vista del inventario
        pass


class AgregarStockInventarioDialog(QDialog):
    """DiÃ¡logo para agregar stock a un producto al copiarlo al inventario."""
    
    def __init__(self, producto_nombre, parent=None):
        super().__init__(parent)
        self.producto_nombre = producto_nombre
        self.unidades_agregar = 0
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Agregar Stock al Nuevo Producto")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # InformaciÃ³n del producto
        info_label = QLabel(f"<b>Producto:</b> {self.producto_nombre}")
        layout.addWidget(info_label)
        
        # Mensaje informativo
        msg_label = QLabel(
            "El producto se ha agregado al inventario con stock inicial de 0.\n"
                "¿Deseas agregar unidades de stock ahora?"
        )
        msg_label.setStyleSheet("color: #555;")
        layout.addWidget(msg_label)
        
        # Separador
        separator = QLabel()
        layout.addWidget(separator)
        
        # Input para agregar unidades
        input_layout = QHBoxLayout()
        input_label = QLabel("Unidades a agregar:")
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(0)
        self.spinbox.setMaximum(10000)
        self.spinbox.setValue(0)
        self.spinbox.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 14px;
                min-width: 100px;
            }
        """)
        input_layout.addWidget(input_label)
        input_layout.addStretch()
        input_layout.addWidget(self.spinbox)
        layout.addLayout(input_layout)
        
        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_no = QPushButton("Sin Stock por Ahora")
        btn_no.setMinimumWidth(150)
        btn_no.clicked.connect(self.reject)
        button_layout.addWidget(btn_no)
        
        btn_si = QPushButton("Agregar Stock")
        btn_si.setObjectName("primaryButton")
        btn_si.setMinimumWidth(120)
        btn_si.clicked.connect(self._on_agregar_clicked)
        button_layout.addWidget(btn_si)
        
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def _on_agregar_clicked(self):
        """Guarda la cantidad a agregar y cierra el diÃ¡logo."""
        self.unidades_agregar = self.spinbox.value()
        self.accept()
        
    def get_unidades(self):
        """Retorna la cantidad de unidades a agregar."""
        return self.unidades_agregar



