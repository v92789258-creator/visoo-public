import datetime
import json
import os
import barcode
from barcode.writer import ImageWriter
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QComboBox, QPushButton, QDateEdit, QGroupBox, QGridLayout,
    QTabWidget, QHeaderView, QFrame, QGraphicsDropShadowEffect, QSizePolicy, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon, QPainter
import sys

# Importar LoadingOverlay
try:
    from gui.loading_overlay import LoadingOverlay
except ImportError:
    # Fallback si no se puede importar
    class LoadingOverlay:
        def __init__(self, parent): pass
        def show_loading(self, text): pass
        def hide_loading(self): pass

# Asumimos que utils existe, si no, mantener tus imports
try:
    from utils.file_handler import cargar_productos, cargar_ventas, VISO_DIR
except ImportError as e:
    print(f"Error importando from utils.file_handler: {e}")
    # Mocks para que el ejemplo funcione si faltan archivos
    VISO_DIR = "visordata"
    def cargar_productos(u): 
        return []
    def cargar_ventas(u): 
        return []

# === PALETA DE COLORES PROFESIONAL (ESTILO SHOPIFY/STRIPE) ===
THEME = {
    'bg_app': '#F1F5F9',        # Gris muy claro azulado (Slate 100)
    'card_bg': '#FFFFFF',       # Blanco puro
    'text_main': '#0F172A',     # Slate 900
    'text_sec': '#64748B',      # Slate 500
    'primary': '#0F172A',       # Negro/Azul muy oscuro para acciones principales
    'primary_hover': '#334155',
    'accent': '#6366F1',        # Indigo moderno para destaques
    'success_bg': '#DCFCE7',    # Verde muy claro
    'success_text': '#166534',  # Verde oscuro
    'danger_bg': '#FEE2E2',     # Rojo muy claro
    'danger_text': '#991B1B',   # Rojo oscuro
    'warning_bg': '#FEF3C7',
    'warning_text': '#92400E',
    'border': '#E2E8F0',        # Slate 200
    'shadow': 'rgba(148, 163, 184, 0.1)'
}


class ClickableBarcodeLabel(QLabel):
    """Label con imagen de código de barras clickeable que abre en navegador"""
    def __init__(self, image_path, code_text="", parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.code_text = code_text
        
        # Verificar si el archivo existe ANTES de intentar cargar
        import os
        if os.path.exists(image_path):
            # Cargar y mostrar imagen
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():  # Verificar que se cargó correctamente
                self.setPixmap(pixmap.scaledToHeight(40, Qt.SmoothTransformation))
            else:
                # Imagen no se pudo cargar, mostrar fallback
                self.setText(f"📊 {code_text[:10]}")
        else:
            # Archivo no existe (común en .exe), mostrar fallback
            self.setText(f"📊 {code_text[:10]}")
        
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setCursor(Qt.PointingHandCursor)  # Cursor de mano para indicar que es clickeable
        self.setStyleSheet("""
            QLabel {
                padding-left: 5px;
                border-radius: 4px;
                font-weight: bold;
                color: #0F172A;
            }
            QLabel:hover {
                background-color: #F1F5F9;
            }
        """)
        
        # Tooltip
        self.setToolTip("Haz clic para abrir el código de barras")
    
    def mousePressEvent(self, event):
        """Al hacer clic, abrir la imagen en el navegador"""
        import webbrowser
        import os
        
        if os.path.exists(self.image_path):
            # Convertir ruta a URL
            url = 'file:///' + os.path.abspath(self.image_path).replace('\\', '/')
            webbrowser.open(url)
        else:
            # Si no existe, al menos mostrar un mensaje
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Código de Barras",
                f"Código: {self.code_text}\n\nArchivo de imagen no disponible en esta instalación."
            )
        
        super().mousePressEvent(event)


class ModernCard(QFrame):
    """Contenedor estilo tarjeta con sombra suave y bordes redondeados"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            ModernCard {{
                background-color: {THEME['card_bg']};
                border: 1px solid {THEME['border']};
                border-radius: 12px;
            }}
        """)
        # Efecto de sombra sutil
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 15)) # Sombra muy transparente
        self.setGraphicsEffect(shadow)

class StatusBadge(QLabel):
    """Etiqueta pequeña para estados (Alto, Bajo, OK)"""
    def __init__(self, text, type='success'):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        bg = THEME[f'{type}_bg']
        color = THEME[f'{type}_text']
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 11px;
            }}
        """)
        self.setFixedHeight(24)
        self.setFixedWidth(80) # Ancho fijo para uniformidad

class ReportDataLoader(QThread):
    """Hilo secundario para cargar y procesar datos pesados sin bloquear la interfaz"""
    finished = pyqtSignal(dict)
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        
    def run(self):
        try:
            productos = cargar_productos(self.username) or []
            ventas_raw = cargar_ventas(self.username) or []
            
            # Procesar ventas para extraer items individuales (operación pesada)
            ventas_flat = []
            for venta in ventas_raw:
                fecha = venta.get('fecha', 'N/A')
                metodo_pago = venta.get('metodo_pago', 'Efectivo')
                cliente = (
                    venta.get('cliente')
                    or venta.get('nombre_cliente')
                    or venta.get('cliente_nombre')
                    or venta.get('customer')
                    or 'N/A'
                )
                items = venta.get('items', [])
                
                for item in items:
                    venta_item = {
                        'fecha': fecha,
                        'cliente': cliente,
                        'producto': item.get('producto', ''),
                        'codigo': item.get('codigo', ''),
                        'cantidad': item.get('cantidad', 0),
                        'venta': item.get('precio_unitario', 0),
                        'price': item.get('precio_unitario', 0),
                        'subtotal': item.get('subtotal', 0),
                        'metodo_pago': metodo_pago
                    }
                    ventas_flat.append(venta_item)
            
            self.finished.emit({
                'productos': productos,
                'ventas_flat': ventas_flat,
                'success': True
            })
        except Exception as e:
            self.finished.emit({'success': False, 'error': str(e)})

class AdvancedReportsPage(QWidget):
    def __init__(self, username=None, parent=None):
        super().__init__(parent)
        self.username = username
        self.setObjectName("AdvancedReports")
        
        # Trabajador de carga
        self.data_worker = None
        
        self.setup_ui()
        
        # Overlay de carga
        self.loading_overlay = LoadingOverlay(self)
        
        # Cargar datos de forma asíncrona al iniciar
        self.load_data()

    def showEvent(self, event):
        super().showEvent(event)
        # Solo recargar si no hay datos o si queremos forzar actualización
        if not hasattr(self, 'all_ventas') or not self.all_ventas:
            self.load_data()

    def setup_ui(self):
        # Configuración general
        self.setStyleSheet(f"""
            QWidget#AdvancedReports {{
                background-color: {THEME['bg_app']};
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {THEME['bg_app']};
                width: 10px;
                margin: 0px; 
            }}
            QScrollBar::handle:vertical {{
                background: #CBD5E1;
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        # === 1. HEADER SECTON ===
        header_layout = QHBoxLayout()
        
        title_container = QVBoxLayout()
        title = QLabel("Reportes Generales")
        title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        title.setStyleSheet(f"color: {THEME['text_main']}; margin-bottom: 5px;")
        
        subtitle = QLabel("Análisis de rentabilidad, márgenes e inventario en tiempo real.")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet(f"color: {THEME['text_sec']};")
        
        title_container.addWidget(title)
        title_container.addWidget(subtitle)
        
        # Botones de Acción Superior
        btn_layout = QHBoxLayout()
        btn_export = self._create_modern_button("📥 Exportar Excel", "secondary")
        btn_pdf = self._create_modern_button("📄 PDF Códigos de Barras", "success")
        btn_refresh = self._create_modern_button("🔄 Actualizar", "primary")
        
        btn_export.clicked.connect(self.export_to_excel)
        btn_pdf.clicked.connect(self.generate_barcodes_pdf)
        btn_refresh.clicked.connect(self.load_data)

        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_pdf)
        btn_layout.addWidget(btn_refresh)
        
        header_layout.addLayout(title_container)
        header_layout.addStretch()
        header_layout.addLayout(btn_layout)
        
        main_layout.addLayout(header_layout)

        # === 2. FILTROS (Dentro de una Card) ===
        filter_card = ModernCard()
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(20, 15, 20, 15)
        filter_layout.setSpacing(20)

        # Estilo común para labels de filtros
        lbl_style = f"color: {THEME['text_sec']}; font-weight: 600; font-size: 12px;"
        
        # Filtro Fecha
        f_date_layout = QHBoxLayout()
        f_date_layout.setSpacing(10)
        
        lbl_desde = QLabel("Periodo:")
        lbl_desde.setStyleSheet(lbl_style)
        self.date_desde = self._create_modern_dateedit()
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))
        
        lbl_hasta = QLabel("hasta")
        lbl_hasta.setStyleSheet(f"color: {THEME['text_sec']}; font-size: 12px;")
        self.date_hasta = self._create_modern_dateedit()
        self.date_hasta.setDate(QDate.currentDate())
        
        f_date_layout.addWidget(lbl_desde)
        f_date_layout.addWidget(self.date_desde)
        f_date_layout.addWidget(lbl_hasta)
        f_date_layout.addWidget(self.date_hasta)

        # Filtro Categoría
        f_cat_layout = QHBoxLayout()
        lbl_cat = QLabel("Categoría:")
        lbl_cat.setStyleSheet(lbl_style)
        self.combo_categoria = QComboBox()
        self.combo_categoria.addItem("Todos los productos")
        self.combo_categoria.setMinimumWidth(200)
        self.combo_categoria.setStyleSheet(self._get_input_style())
        
        f_cat_layout.addWidget(lbl_cat)
        f_cat_layout.addWidget(self.combo_categoria)

        filter_layout.addLayout(f_date_layout)
        filter_layout.addLayout(f_cat_layout)
        filter_layout.addStretch()

        main_layout.addWidget(filter_card)

        # === 3. TABS DE CONTENIDO ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {THEME['text_sec']};
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                border-bottom: 2px solid transparent;
                margin-right: 15px;
            }}
            QTabBar::tab:selected {{
                color: {THEME['text_main']};
                border-bottom: 2px solid {THEME['primary']};
            }}
            QTabBar::tab:hover {{
                color: {THEME['primary']};
            }}
        """)

        self.tabs.addTab(self._create_tab_financial_summary(), "Resumen")
        self.tabs.addTab(self._create_tab_product_earnings(), "Productos y Ganancias")
        self.tabs.addTab(self._create_tab_margin_analysis(), "Análisis de Margen")
        
        main_layout.addWidget(self.tabs)

    def _get_input_style(self):
        return f"""
            QComboBox, QDateEdit {{
                border: 1px solid {THEME['border']};
                border-radius: 6px;
                padding: 6px 10px;
                background: white;
                color: {THEME['text_main']};
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox:focus, QDateEdit:focus {{
                border: 1px solid {THEME['accent']};
            }}
        """

    def _create_modern_dateedit(self):
        dt = QDateEdit()
        dt.setCalendarPopup(True)
        dt.setDisplayFormat("dd MMM yyyy")
        dt.setStyleSheet(self._get_input_style())
        dt.setFixedWidth(130)
        return dt

    def _create_modern_button(self, text, variant="primary"):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        
        bg = THEME['primary'] if variant == "primary" else "white"
        text_color = "white" if variant == "primary" else THEME['text_main']
        border = "none" if variant == "primary" else f"1px solid {THEME['border']}"
        hover_bg = THEME['primary_hover'] if variant == "primary" else "#F8FAFC"
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                border: {border};
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
        """)
        return btn

    def _create_table(self, columns):
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)  # Quitar grilla para look moderno
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setFrameShape(QFrame.NoFrame)
        table.setFocusPolicy(Qt.NoFocus)
        
        # Estilo CSS de la Tabla
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: white;
                alternate-background-color: #F8FAFC;
                gridline-color: transparent;
            }}
            QHeaderView::section {{
                background-color: white;
                color: {THEME['text_sec']};
                padding: 12px 10px;
                border: none;
                border-bottom: 1px solid {THEME['border']};
                font-weight: bold;
                font-size: 12px;
                text-transform: uppercase;
                text-align: left;
            }}
            QTableWidget::item {{
                padding: 12px 10px;
                border-bottom: 1px solid {THEME['bg_app']};
                color: {THEME['text_main']};
            }}
            QTableWidget::item:selected {{
                background-color: {THEME['bg_app']};
                color: {THEME['primary']};
            }}
        """)
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        return table

    def _create_tab_product_earnings(self):
        """Tab de Productos con tabla de ventas al lado"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 15, 0, 0)
        
        # Layout horizontal para dos tablas
        h_layout = QHBoxLayout()
        
        # === TABLA DE PRODUCTOS (IZQUIERDA) ===
        card_productos = ModernCard()
        card_prod_layout = QVBoxLayout(card_productos)
        card_prod_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_productos = QLabel("📊 Productos")
        lbl_productos.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {THEME['text_main']};")
        card_prod_layout.addWidget(lbl_productos)
        
        self.table_products = self._create_table([
            "Producto", "Código", "Costo Total", "Valor Venta", "Ganancia", "% Margen", 
            "Stock", "Rotación"
        ])
        
        # Ajustar anchos específicos
        h = self.table_products.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)     # Nombre
        h.setSectionResizeMode(1, QHeaderView.Fixed)       # Codigo
        self.table_products.setColumnWidth(1, 120)
        
        # Conectar click en tabla para mostrar ventas
        self.table_products.itemSelectionChanged.connect(self._on_product_selected)
        
        card_prod_layout.addWidget(self.table_products)
        h_layout.addWidget(card_productos, 1)
        
        # === TABLA DE VENTAS (DERECHA) ===
        card_ventas = ModernCard()
        card_ventas_layout = QVBoxLayout(card_ventas)
        card_ventas_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_ventas = QLabel("💰 Ventas del Producto Seleccionado")
        lbl_ventas.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {THEME['text_main']};")
        card_ventas_layout.addWidget(lbl_ventas)
        
        self.table_sales = self._create_table([
            "Fecha", "Días Atrás", "Cantidad", "Precio Unit.", "Total", "Método Pago"
        ])
        card_ventas_layout.addWidget(self.table_sales)
        h_layout.addWidget(card_ventas, 1)
        
        layout.addLayout(h_layout)
        
        # Guardar referencia a ventas y productos para exportar
        self.all_ventas = []
        self.selected_product = None
        
        return container

    def _create_tab_financial_summary(self):
        """Tab de Resumen KPI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 15, 0, 0)
        
        # === KPIS ===
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(20)
        
        self.kpi_profit = self._create_kpi_card("Ganancia Potencial", "S/. 0.00", "success")
        self.kpi_value = self._create_kpi_card("Valor Inventario", "S/. 0.00", "primary")
        self.kpi_margin = self._create_kpi_card("Margen Promedio", "0.0%", "warning")
        self.kpi_roi = self._create_kpi_card("ROI Estimado", "0.0%", "accent")
        
        kpi_layout.addWidget(self.kpi_profit)
        kpi_layout.addWidget(self.kpi_value)
        kpi_layout.addWidget(self.kpi_margin)
        kpi_layout.addWidget(self.kpi_roi)
        
        layout.addLayout(kpi_layout)
        
        # === TABLA RESUMEN ===
        layout.addSpacing(20)
        lbl = QLabel("Detalle de Métricas")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(lbl)
        
        card_table = ModernCard()
        l_table = QVBoxLayout(card_table)
        l_table.setContentsMargins(0,0,0,0)
        
        self.table_summary = self._create_table([
            "Métrica", "Valor Actual", "Variación Mes", "Tendencia", "Objetivo", "Estado"
        ])
        l_table.addWidget(self.table_summary)
        
        layout.addWidget(card_table)
        layout.addStretch()
        
        return container

    def _create_tab_margin_analysis(self):
        """Tab de Análisis de Margen"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 15, 0, 0)
        
        card = ModernCard()
        l = QVBoxLayout(card)
        l.setContentsMargins(0,0,0,0)
        
        self.table_margin = self._create_table([
            "Producto", "Costo Unit.", "P. Venta", "Ganancia Unit.", "% Margen",
            "Clasificación", "Recomendación"
        ])
        
        l.addWidget(self.table_margin)
        layout.addWidget(card)
        return container

    def _create_kpi_card(self, title, value, color_key="primary"):
        """Crea una tarjeta de KPI con diseño limpio"""
        card = ModernCard()
        card.setFixedHeight(140)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5)
        
        # Título
        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet(f"color: {THEME['text_sec']}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        
        # Valor
        lbl_val = QLabel(value)
        lbl_val.setFont(QFont("Segoe UI", 24, QFont.Bold))
        color = THEME['text_main']
        if color_key == 'success': color = THEME['success_text']
        lbl_val.setStyleSheet(f"color: {color}; margin-top: 5px;")
        
        # Decoración (Icono o línea)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {THEME['bg_app']}; max-width: 50px;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(line)
        layout.addStretch()
        
        # Guardar referencia
        card.value_label = lbl_val
        return card

    # ================= LOGICA DE DATOS =================
    
    def load_data(self):
        """Inicia el proceso de carga asíncrona"""
        if not self.username: 
            print("⚠️ No hay username")
            return
            
        # Si ya hay un trabajador corriendo, ignorar
        if self.data_worker and self.data_worker.isRunning():
            return
            
        # Mostrar loader
        self.loading_overlay.show_loading("Analizando datos y procesando márgenes...")
        
        # Crear e iniciar trabajador
        self.data_worker = ReportDataLoader(self.username)
        self.data_worker.finished.connect(self._on_data_loaded)
        self.data_worker.start()

    def _on_data_loaded(self, result):
        """Callback cuando los datos terminan de cargarse"""
        # Ocultar loader
        self.loading_overlay.hide_loading()
        
        if not result.get('success'):
            print(f"Error cargando datos: {result.get('error')}")
            return
            
        try:
            productos = result.get('productos', [])
            self.all_ventas = result.get('ventas_flat', [])
            
            print(f"📦 Datos cargados asíncronamente: {len(productos)} productos, {len(self.all_ventas)} ventas")
            
            # Actualizar tablas en el hilo principal
            self._update_products_table(productos, self.all_ventas)
            self._update_financials(productos, self.all_ventas)
            self._update_margins(productos)
            
        except Exception as e:
            print(f"Error procesando datos cargados: {e}")
            import traceback
            traceback.print_exc()

    def _on_product_selected(self):
        """Maneja cuando se selecciona un producto en la tabla"""
        selected_rows = self.table_products.selectedIndexes()
        if not selected_rows:
            self.table_sales.setRowCount(0)
            self.selected_product = None
            return
        
        row = selected_rows[0].row()
        product_name = self.table_products.item(row, 0).text()
        
        self.selected_product = product_name
        self._update_sales_table(product_name)

    def _update_products_table(self, productos, ventas):
        self.table_products.setRowCount(0)
        
        for i, prod in enumerate(productos):
            nombre = prod.get('nombre', 'N/A')
            codigo = prod.get('codigo', 'N/A')
            
            try:
                costo = float(prod.get('costo', 0) or 0)
                precio = float(prod.get('venta', 0) or 0)
                stock = float(prod.get('stock', 0) or 0)
            except ValueError:
                continue

            # Cálculos
            costo_total = costo * stock
            precio_total = precio * stock
            ganancia_total = precio_total - costo_total
            margen = ((precio - costo) / precio * 100) if precio > 0 else 0
            
            # Ventas de este producto - buscar por nombre o código
            ventas_prod = []
            for v in ventas:
                venta_producto = str(v.get('producto', '')).lower()
                venta_codigo = str(v.get('codigo', '')).lower()
                if venta_producto == nombre.lower() or (codigo != 'N/A' and venta_codigo == codigo.lower()):
                    ventas_prod.append(v)
            
            cant_vendida = sum(int(v.get('cantidad', 0) or 0) for v in ventas_prod)
            rotacion = (cant_vendida / (cant_vendida + stock) * 100) if (cant_vendida + stock) > 0 else 0

            self.table_products.insertRow(i)
            self.table_products.setRowHeight(i, 70) # Filas más altas para el código

            # Items
            self._set_cell(self.table_products, i, 0, nombre, bold=True)
            
            # Código de barras (widget custom o texto)
            self._set_barcode_cell(i, 1, codigo, nombre)
            
            self._set_cell(self.table_products, i, 2, f"S/. {costo_total:,.2f}")
            self._set_cell(self.table_products, i, 3, f"S/. {precio_total:,.2f}")
            
            # Ganancia con color condicional
            color = THEME['success_text'] if ganancia_total > 0 else THEME['danger_text']
            self._set_cell(self.table_products, i, 4, f"S/. {ganancia_total:,.2f}", color=color, bold=True)
            
            self._set_cell(self.table_products, i, 5, f"{margen:.1f}%")
            
            # Stock con badge si es bajo
            if stock < 5:
                widget = QWidget()
                lay = QHBoxLayout(widget)
                lay.setContentsMargins(5,0,5,0)
                lbl = QLabel(str(int(stock)))
                lbl.setStyleSheet("color: #ef4444; font-weight: bold;") 
                lay.addWidget(lbl)
                warn = QLabel("⚠️")
                lay.addWidget(warn)
                lay.addStretch()
                self.table_products.setCellWidget(i, 6, widget)
            else:
                self._set_cell(self.table_products, i, 6, str(int(stock)))

            self._set_cell(self.table_products, i, 7, f"{rotacion:.1f}%")

    def _update_sales_table(self, product_name):
        """Actualiza la tabla de ventas para un producto específico"""
        self.table_sales.setRowCount(0)
        
        print(f"\n🔍 Buscando ventas para: {product_name}")
        print(f"Total de ventas disponibles: {len(self.all_ventas)}")
        
        # Filtrar ventas del producto
        ventas_prod = []
        for v in self.all_ventas:
            # Intentar diferentes campos que puedan contener el nombre del producto
            venta_producto = str(v.get('producto', '') or v.get('name', '') or v.get('nombre', '')).lower().strip()
            product_lower = product_name.lower().strip()
            
            if venta_producto == product_lower:
                ventas_prod.append(v)
        
        print(f"✅ Ventas encontradas: {len(ventas_prod)}")
        
        # Llenar tabla de ventas
        for i, venta in enumerate(ventas_prod):
            self.table_sales.insertRow(i)
            
            fecha = venta.get('fecha', venta.get('date', 'N/A'))
            # Calcular días atrás
            dias_atras = self._calcular_dias_atras(fecha)
            cantidad = venta.get('cantidad', venta.get('quantity', 0))
            precio_unit = float(venta.get('venta', venta.get('price', 0)) or 0)
            total = float(cantidad or 0) * precio_unit
            metodo_pago = venta.get('metodo_pago', venta.get('payment_method', 'Efectivo'))
            
            self._set_cell(self.table_sales, i, 0, str(fecha))
            self._set_cell(self.table_sales, i, 1, f"{dias_atras} días")
            self._set_cell(self.table_sales, i, 2, str(int(cantidad)))
            self._set_cell(self.table_sales, i, 3, f"S/. {precio_unit:,.2f}")
            self._set_cell(self.table_sales, i, 4, f"S/. {total:,.2f}", bold=True)
            self._set_cell(self.table_sales, i, 5, str(metodo_pago))

    def _calcular_dias_atras(self, fecha_str):
        """Calcula cuántos días atrás fue una fecha"""
        try:
            # Parsear fecha en formato DD/MM/YYYY HH:MM:SS
            fecha_obj = datetime.datetime.strptime(str(fecha_str).split()[0], '%d/%m/%Y')
            dias = (datetime.datetime.now() - fecha_obj).days
            return max(0, dias)
        except:
            return 0

    def _set_barcode_cell(self, row, col, code, name):
        """Intenta generar barcode, si falla pone texto - hace clickeable para abrir en navegador"""
        path = self._generate_barcode_img(code, name)
        if path:
            # Crear un widget personalizado clickeable (pasar el código para fallback)
            barcode_widget = ClickableBarcodeLabel(path, code_text=code)
            self.table_products.setCellWidget(row, col, barcode_widget)
        else:
            self._set_cell(self.table_products, row, col, code)

    def _update_financials(self, productos, ventas):
        # Lógica simplificada para ejemplo
        total_inv = sum((float(p.get('venta',0) or 0) * float(p.get('stock',0) or 0)) for p in productos)
        costo_inv = sum((float(p.get('costo',0) or 0) * float(p.get('stock',0) or 0)) for p in productos)
        ganancia_pot = total_inv - costo_inv
        
        roi = (ganancia_pot / costo_inv * 100) if costo_inv > 0 else 0
        
        # Actualizar KPIs
        self.kpi_profit.value_label.setText(f"S/. {ganancia_pot:,.2f}")
        self.kpi_value.value_label.setText(f"S/. {total_inv:,.2f}")
        self.kpi_roi.value_label.setText(f"{roi:.1f}%")
        
        # Tabla resumen (Dummy data para estilo)
        self.table_summary.setRowCount(0)
        data = [
            ("Ganancia Total", f"S/. {ganancia_pot:,.2f}", "+5.2%", "↗️", "S/. 5,000", "success"),
            ("Margen Global", f"32.5%", "+1.2%", "↗️", "30.0%", "success"),
            ("Stock Muerto", "S/. 450.00", "-2.0%", "↘️", "S/. 0.00", "warning")
        ]
        
        for i, row in enumerate(data):
            self.table_summary.insertRow(i)
            self.table_summary.setRowHeight(i, 50)
            self._set_cell(self.table_summary, i, 0, row[0], bold=True)
            self._set_cell(self.table_summary, i, 1, row[1])
            self._set_cell(self.table_summary, i, 2, row[2], color=THEME['success_text'])
            self._set_cell(self.table_summary, i, 3, row[3])
            self._set_cell(self.table_summary, i, 4, row[4])
            
            # Badge para estado
            badge = StatusBadge("OPTIMO" if row[5] == 'success' else "REVISAR", row[5])
            container = QWidget()
            ly = QHBoxLayout(container)
            ly.setContentsMargins(0,0,0,0)
            ly.addWidget(badge)
            ly.addStretch()
            self.table_summary.setCellWidget(i, 5, container)

    def _update_margins(self, productos):
        self.table_margin.setRowCount(0)
        for i, prod in enumerate(productos):
            try:
                c = float(prod.get('costo', 0) or 0)
                p = float(prod.get('venta', 0) or 0)
                m = ((p - c)/p * 100) if p > 0 else 0
                g = p - c
                
                self.table_margin.insertRow(i)
                self.table_margin.setRowHeight(i, 50)
                
                self._set_cell(self.table_margin, i, 0, prod.get('nombre'))
                self._set_cell(self.table_margin, i, 1, f"S/. {c:.2f}")
                self._set_cell(self.table_margin, i, 2, f"S/. {p:.2f}")
                self._set_cell(self.table_margin, i, 3, f"S/. {g:.2f}")
                self._set_cell(self.table_margin, i, 4, f"{m:.1f}%")
                
                # Clasificación visual
                status = "success" if m >= 30 else ("warning" if m > 15 else "danger")
                txt_status = "ALTO" if m >= 30 else ("MEDIO" if m > 15 else "BAJO")
                
                badge = StatusBadge(txt_status, status)
                cont = QWidget()
                l = QHBoxLayout(cont)
                l.setContentsMargins(0,0,0,0)
                l.addWidget(badge)
                l.addStretch()
                self.table_margin.setCellWidget(i, 5, cont)
                
                rec = "Mantener" if m >= 30 else "Revisar Costos"
                self._set_cell(self.table_margin, i, 6, rec)
                
            except: continue

    # ================= UTILS UI =================
    
    def _set_cell(self, table, row, col, text, color=None, bold=False):
        item = QTableWidgetItem(str(text))
        if color:
            item.setForeground(QColor(color))
        if bold:
            item.setFont(QFont("Segoe UI", 10, QFont.Bold))
        else:
            item.setFont(QFont("Segoe UI", 10))
            
        # Alinear números a la derecha (si empieza con S/. o es numero)
        if str(text).startswith("S/.") or str(text).endswith("%") or str(text).replace('.','').isdigit():
             # Excepción para columnas de texto puro
             pass 
             
        table.setItem(row, col, item)

    def _generate_barcode_img(self, code, name):
        """Genera imagen de código de barras y la guarda en carpeta barcodes"""
        if not code or code == 'N/A': 
            return None
        try:
            clean_code = ''.join(c for c in code if c.isdigit())[:13]
            if not clean_code: 
                return None
            if len(clean_code) < 13: 
                clean_code = clean_code.ljust(13, '0')
            
            # Directorio para guardar códigos de barras
            d = os.path.join(VISO_DIR, "barcodes")
            if not os.path.exists(d): 
                os.makedirs(d, exist_ok=True)
            
            # Crear nombre seguro para el archivo
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_')).rstrip()[:40]
            filename = f"{safe_name}_{clean_code}"
            path_without_ext = os.path.join(d, filename)
            path_with_png = path_without_ext + ".png"
            
            # Evitar regenerar si existe
            if os.path.exists(path_with_png): 
                return path_with_png
            
            # Generar código de barras EAN13
            from barcode.writer import ImageWriter
            ean = barcode.get_barcode_class('ean13')
            barcode_instance = ean(clean_code, writer=ImageWriter())
            
            # Guardar (save() añade automáticamente .png)
            saved_path = barcode_instance.save(
                path_without_ext,
                options={
                    'module_height': 20,
                    'module_width': 0.7,
                    'font_size': 14
                }
            )
            
            print(f"✓ Código de barras generado: {saved_path}")
            return path_with_png
        except Exception as e:
            print(f"❌ Error generando código de barras para {name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def export_to_excel(self):
        """Exporta reporte AVANZADO con múltiples hojas, análisis, filtros y gráficos"""
        try:
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            import xlsxwriter
            from collections import defaultdict
            import datetime as dt_module
            
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getSaveFileName(
                self, "Guardar Reporte Completo Avanzado",
                f"Reporte_Completo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            workbook = xlsxwriter.Workbook(file_path)
            
            # ===== FORMATOS PERSONALIZADOS =====
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1F4E78',
                'font_color': 'white',
                'font_size': 12,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D3D3D3',
                'text_wrap': True
            })
            
            subheader_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'font_size': 11,
                'align': 'center',
                'border': 1
            })
            
            money_format = workbook.add_format({
                'num_format': '"S/. "#,##0.00',
                'align': 'right',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D3D3D3',
                'bg_color': '#F5F5F5'
            })
            
            percent_format = workbook.add_format({
                'num_format': '0.0"%"',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D3D3D3',
                'bg_color': '#F5F5F5'
            })
            
            text_format = workbook.add_format({
                'align': 'left',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D3D3D3',
                'bg_color': '#FFFFFF'
            })
            
            text_center = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D3D3D3',
                'bg_color': '#FFFFFF'
            })
            
            link_format = workbook.add_format({
                'align': 'left',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D3D3D3',
                'bg_color': '#FFFFFF',
                'font_color': '#0563C1',
                'underline': True
            })
            
            number_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#D3D3D3',
                'bg_color': '#F5F5F5',
                'num_format': '0'
            })
            
            total_format = workbook.add_format({
                'bold': True,
                'bg_color': '#E7E6E6',
                'num_format': '"S/. "#,##0.00',
                'align': 'right',
                'border': 1
            })
            
            total_percent = workbook.add_format({
                'bold': True,
                'bg_color': '#E7E6E6',
                'num_format': '0.0"%"',
                'align': 'center',
                'border': 1
            })
            
            # ===== HOJA 1: PORTADA CON RESUMEN EJECUTIVO =====
            ws_portada = workbook.add_worksheet("Portada")
            ws_portada.set_column(0, 10, 20)
            
            # Título
            title_fmt = workbook.add_format({
                'bold': True, 'font_size': 24, 'color': '#1F4E78',
                'align': 'center', 'valign': 'vcenter'
            })
            ws_portada.merge_range('A1:E3', ' REPORTE AVANZADO DE GANANCIAS', title_fmt)
            
            # KPIs principales
            row = 8
            
            # Calcular totales generales
            total_inv = sum((float(p.get('venta',0) or 0) * float(p.get('stock',0) or 0)) for p in (cargar_productos(self.username) or []))
            costo_inv = sum((float(p.get('costo',0) or 0) * float(p.get('stock',0) or 0)) for p in (cargar_productos(self.username) or []))
            ganancia_pot = total_inv - costo_inv
            
            resumen_data = [
                ('💰 VALOR INVENTARIO', f'S/. {total_inv:,.2f}'),
                ('📈 GANANCIA POTENCIAL', f'S/. {ganancia_pot:,.2f}'),
                ('📊 COSTO TOTAL', f'S/. {costo_inv:,.2f}'),
                ('📦 TOTAL PRODUCTOS', str(len(cargar_productos(self.username) or []))),
                ('💸 TOTAL VENTAS', f'S/. {sum(float(v.get("subtotal", 0) or 0) for v in self.all_ventas):,.2f}'),
            ]
            
            for label, value in resumen_data:
                kpi_fmt = workbook.add_format({
                    'bold': True, 'font_size': 12, 'border': 1, 'bg_color': '#E8F4F8'
                })
                ws_portada.write(row, 0, label, kpi_fmt)
                ws_portada.write(row, 1, value, workbook.add_format({
                    'font_size': 12, 'bold': True, 'color': '#1F4E78'
                }))
                row += 2
            
            # ===== GRÁFICOS EN PORTADA =====
            # Preparar datos para gráficos
            
            # 1. Gráfico Circular: Métodos de Pago
            pagos_resumen_chart = defaultdict(float)
            for venta in self.all_ventas:
                metodo = venta.get('metodo_pago', 'Efectivo')
                subtotal = float(venta.get('subtotal', 0) or 0)
                pagos_resumen_chart[metodo] += subtotal
            
            # Crear área para gráfico circular
            pie_chart = workbook.add_chart({'type': 'pie'})
            pie_data_row = 20
            ws_portada.write(pie_data_row, 0, 'Método', header_format)
            ws_portada.write(pie_data_row, 1, 'Total', header_format)
            
            pie_row = pie_data_row + 1
            for metodo, valor in sorted(pagos_resumen_chart.items(), key=lambda x: x[1], reverse=True):
                ws_portada.write(pie_row, 0, metodo, text_format)
                ws_portada.write(pie_row, 1, valor, money_format)
                pie_row += 1
            
            pie_chart.add_series({
                'name': 'Métodos de Pago',
                'categories': f"=Portada!$A${pie_data_row + 1}:$A${pie_row}",
                'values': f"=Portada!$B${pie_data_row + 1}:$B${pie_row}",
                'data_labels': {'percentage': True, 'value': True},
                'points': [
                    {'fill': {'color': '#FF6B6B'}},
                    {'fill': {'color': '#4ECDC4'}},
                    {'fill': {'color': '#45B7D1'}},
                    {'fill': {'color': '#FFA07A'}},
                    {'fill': {'color': '#98D8C8'}},
                ],
            })
            pie_chart.set_title({'name': 'Distribución de Ventas por Método de Pago'})
            pie_chart.set_style(11)
            pie_chart.set_size({'width': 500, 'height': 300})
            ws_portada.insert_chart(4, 3, pie_chart)
            
            # 2. Gráfico de Barras: Top 5 Productos
            productos_stats = defaultdict(float)
            for venta in self.all_ventas:
                prod = venta.get('producto', 'N/A')
                subtotal = float(venta.get('subtotal', 0) or 0)
                productos_stats[prod] += subtotal
            
            top_5_productos = sorted(productos_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Crear área para gráfico de barras
            bar_chart = workbook.add_chart({'type': 'bar'})
            bar_data_row = pie_row + 3
            ws_portada.write(bar_data_row, 0, 'Producto', header_format)
            ws_portada.write(bar_data_row, 1, 'Ingresos', header_format)
            
            bar_row = bar_data_row + 1
            for producto, valor in top_5_productos:
                ws_portada.write(bar_row, 0, producto[:30], text_format)
                ws_portada.write(bar_row, 1, valor, money_format)
                bar_row += 1
            
            bar_chart.add_series({
                'name': 'Ingresos por Producto',
                'categories': f"=Portada!$A${bar_data_row + 1}:$A${bar_row}",
                'values': f"=Portada!$B${bar_data_row + 1}:$B${bar_row}",
                'fill': {'color': '#4472C4'},
                'gap': 150,
            })
            bar_chart.set_title({'name': 'Top 5 Productos por Ingresos'})
            bar_chart.set_x_axis({'name': 'Ingresos (S/.)'})
            bar_chart.set_y_axis({'name': 'Productos'})
            bar_chart.set_style(11)
            bar_chart.set_size({'width': 500, 'height': 300})
            ws_portada.insert_chart(4, 8, bar_chart)
            
            # ===== BOTONES DE NAVEGACIÓN =====
            botones_row = 28
            botones_data = [
                ('Productos Detallado', 'Productos Detallado'),
                ('Análisis por Período', 'Análisis por Período'),
                ('Ventas Detalladas', 'Ventas Detalladas'),
                ('Top Productos', 'Top Productos'),
                ('Métodos Pago', 'Métodos Pago'),
                ('Por Categoría', 'Por Categoría'),
                ('Resumen Financiero', 'Resumen Financiero'),
                ('Comparativa', 'Comparativa'),
                ('Por Código (SKU)', 'Por Código'),
                ('Estadísticas', 'Estadísticas'),
            ]
            
            boton_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#1F4E78',
                'bg_color': '#4472C4',
                'font_color': '#FFFFFF',
                'font_size': 11,
                'underline': True,
            })
            
            col = 0
            for i, (etiqueta, hoja) in enumerate(botones_data):
                if col >= 5:
                    col = 0
                    botones_row += 2
                
                # Escribir hipervínculo como botón
                ws_portada.write_url(botones_row, col, f"internal:'{hoja}'!A1", boton_format, string=etiqueta)
                col += 1
            
            # ===== HOJA 2: PRODUCTOS COMPLETA =====
            worksheet = workbook.add_worksheet("Productos Detallado")
            
            columns = [
                "Producto", "Código", "Categoría", "Costo Unitario", "Costo Total", 
                "Valor Venta", "Precio Total", "Ganancia Unit.", "Ganancia Total", 
                "% Margen", "Stock", "Rotación %", "Vendidos"
            ]
            
            for col_idx, header in enumerate(columns):
                worksheet.write(0, col_idx, header, header_format)
            
            row = 1
            total_costo_un = 0
            total_costo_total = 0
            total_venta = 0
            total_precio_total = 0
            total_ganancia_un = 0
            total_ganancia_total = 0
            total_stock = 0
            total_vendidos = 0
            
            for row_idx, prod in enumerate(cargar_productos(self.username) or []):
                nombre = prod.get('nombre', 'N/A')
                codigo = prod.get('codigo', 'N/A')
                categoria = prod.get('categoria', 'Sin categoría')
                
                try:
                    costo = float(prod.get('costo', 0) or 0)
                    precio = float(prod.get('venta', 0) or 0)
                    stock = float(prod.get('stock', 0) or 0)
                except ValueError:
                    continue

                costo_total = costo * stock
                precio_total = precio * stock
                ganancia_unit = precio - costo
                ganancia_total = ganancia_unit * stock
                margen = ((precio - costo) / precio * 100) if precio > 0 else 0
                
                # Contar vendidos
                vendidos = sum(int(v.get('cantidad', 0) or 0) for v in self.all_ventas 
                              if v.get('producto', '').lower() == nombre.lower())
                rotacion = (vendidos / (vendidos + stock) * 100) if (vendidos + stock) > 0 else 0

                worksheet.write(row, 0, nombre, text_format)
                worksheet.write(row, 1, codigo, text_center)
                worksheet.write(row, 2, categoria, text_format)
                worksheet.write(row, 3, costo, money_format)
                worksheet.write(row, 4, costo_total, money_format)
                worksheet.write(row, 5, precio, money_format)
                worksheet.write(row, 6, precio_total, money_format)
                worksheet.write(row, 7, ganancia_unit, money_format)
                worksheet.write(row, 8, ganancia_total, money_format)
                worksheet.write(row, 9, margen, percent_format)
                worksheet.write(row, 10, stock, number_format)
                worksheet.write(row, 11, rotacion, percent_format)
                worksheet.write(row, 12, vendidos, number_format)
                
                total_costo_un += costo
                total_costo_total += costo_total
                total_venta += precio
                total_precio_total += precio_total
                total_ganancia_un += ganancia_unit
                total_ganancia_total += ganancia_total
                total_stock += stock
                total_vendidos += vendidos
                
                row += 1
            
            # Fila de totales
            worksheet.write(row, 0, "TOTALES", header_format)
            worksheet.write(row, 3, total_costo_un, total_format)
            worksheet.write(row, 4, total_costo_total, total_format)
            worksheet.write(row, 5, total_venta, total_format)
            worksheet.write(row, 6, total_precio_total, total_format)
            worksheet.write(row, 7, total_ganancia_un, total_format)
            worksheet.write(row, 8, total_ganancia_total, total_format)
            worksheet.write(row, 10, total_stock, total_format)
            worksheet.write(row, 12, total_vendidos, total_format)
            
            # Ajustar anchos
            widths = [20, 12, 15, 14, 14, 14, 14, 14, 14, 10, 10, 12, 10]
            for col_idx, width in enumerate(widths):
                worksheet.set_column(col_idx, col_idx, width)
            
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(0, 0, row, len(columns) - 1)  # Agregar AutoFilter
            
            # ===== HOJA 3: ANÁLISIS POR PERÍODO =====
            ws_periodos = workbook.add_worksheet("📅 Análisis por Período")
            ws_periodos.write(0, 0, "Período", header_format)
            ws_periodos.write(0, 1, "Tipo", header_format)
            ws_periodos.write(0, 2, "# Ventas", header_format)
            ws_periodos.write(0, 3, "Total Vendido", header_format)
            ws_periodos.write(0, 4, "Promedio Venta", header_format)
            ws_periodos.write(0, 5, "Productos Diferentes", header_format)
            ws_periodos.write(0, 6, "Top Producto", header_format)
            
            # Agrupar por período
            periodos_data = self._agrupar_ventas_por_periodo(self.all_ventas)
            row = 1
            
            for periodo, datos in sorted(periodos_data.items()):
                ws_periodos.write(row, 0, periodo, text_format)
                ws_periodos.write(row, 1, datos['tipo'], text_center)
                ws_periodos.write(row, 2, datos['num_ventas'], number_format)
                ws_periodos.write(row, 3, datos['total'], money_format)
                promedio = datos['total'] / datos['num_ventas'] if datos['num_ventas'] > 0 else 0
                ws_periodos.write(row, 4, promedio, money_format)
                ws_periodos.write(row, 5, datos['productos'], number_format)
                ws_periodos.write(row, 6, datos['top_producto'], text_format)
                row += 1
            
            ws_periodos.set_column(0, 6, 18)
            ws_periodos.freeze_panes(1, 0)
            
            # ===== HOJA 4: VENTAS DETALLADAS CON FILTROS =====
            ws_ventas = workbook.add_worksheet("Ventas Detalladas")
            ws_ventas.write(0, 0, "Fecha", header_format)
            ws_ventas.write(0, 1, "Producto", header_format)
            ws_ventas.write(0, 2, "Código", header_format)
            ws_ventas.write(0, 3, "Cantidad", header_format)
            ws_ventas.write(0, 4, "Precio Unit.", header_format)
            ws_ventas.write(0, 5, "Subtotal", header_format)
            ws_ventas.write(0, 6, "Método Pago", header_format)
            ws_ventas.write(0, 7, "Días Atrás", header_format)
            
            row = 1
            total_ventas_val = 0
            for venta in sorted(self.all_ventas, key=lambda x: x.get('fecha', ''), reverse=True):
                fecha = venta.get('fecha', 'N/A')
                producto = venta.get('producto', 'N/A')
                codigo = venta.get('codigo', 'N/A')
                cantidad = int(venta.get('cantidad', 0) or 0)
                precio_unit = float(venta.get('venta', venta.get('price', 0)) or 0)
                subtotal = cantidad * precio_unit
                metodo = venta.get('metodo_pago', 'Efectivo')
                dias = self._calcular_dias_atras(fecha)
                
                ws_ventas.write(row, 0, str(fecha), text_format)
                ws_ventas.write(row, 1, producto, text_format)
                ws_ventas.write(row, 2, codigo, text_center)
                ws_ventas.write(row, 3, cantidad, number_format)
                ws_ventas.write(row, 4, precio_unit, money_format)
                ws_ventas.write(row, 5, subtotal, money_format)
                ws_ventas.write(row, 6, metodo, text_center)
                ws_ventas.write(row, 7, dias, number_format)
                
                total_ventas_val += subtotal
                row += 1
            
            ws_ventas.write(row, 5, total_ventas_val, total_format)
            ws_ventas.set_column(0, 7, 16)
            ws_ventas.freeze_panes(1, 0)
            ws_ventas.autofilter(0, 0, row, 7)
            
            # ===== HOJA 5: TOP PRODUCTOS =====
            ws_top = workbook.add_worksheet("🏆 Top Productos")
            ws_top.write(0, 0, "Posición", header_format)
            ws_top.write(0, 1, "Producto", header_format)
            ws_top.write(0, 2, "Código", header_format)
            ws_top.write(0, 3, "Cantidad Vendida", header_format)
            ws_top.write(0, 4, "Ingresos", header_format)
            ws_top.write(0, 5, "Ganancia Total", header_format)
            ws_top.write(0, 6, "Margen %", header_format)
            
            # Top 10 productos por ventas
            productos_stats = defaultdict(lambda: {
                'cantidad': 0, 'ingresos': 0, 'codigo': '', 'ganancia': 0
            })
            
            for venta in self.all_ventas:
                prod = venta.get('producto', 'N/A')
                cantidad = int(venta.get('cantidad', 0) or 0)
                subtotal = float(venta.get('subtotal', 0) or 0)
                codigo = venta.get('codigo', 'N/A')
                productos_stats[prod]['cantidad'] += cantidad
                productos_stats[prod]['ingresos'] += subtotal
                productos_stats[prod]['codigo'] = codigo
                
                # Calcular ganancia
                for p_data in (cargar_productos(self.username) or []):
                    if p_data.get('nombre', '').lower() == prod.lower():
                        costo_unit = float(p_data.get('costo', 0) or 0)
                        productos_stats[prod]['ganancia'] += (float(venta.get('venta', 0) or 0) - costo_unit) * cantidad
            
            top_10 = sorted(productos_stats.items(), key=lambda x: x[1]['ingresos'], reverse=True)[:10]
            
            for idx, (prod, stats) in enumerate(top_10, 1):
                margen = (stats['ingresos'] - stats['ganancia']) / stats['ingresos'] * 100 if stats['ingresos'] > 0 else 0
                ws_top.write(idx, 0, idx, number_format)
                ws_top.write(idx, 1, prod, text_format)
                ws_top.write(idx, 2, stats['codigo'], text_center)
                ws_top.write(idx, 3, stats['cantidad'], number_format)
                ws_top.write(idx, 4, stats['ingresos'], money_format)
                ws_top.write(idx, 5, stats['ganancia'], money_format)
                ws_top.write(idx, 6, margen, percent_format)
            
            ws_top.set_column(0, 6, 18)
            ws_top.freeze_panes(1, 0)
            
            # ===== HOJA 6: ANÁLISIS POR MÉTODO DE PAGO =====
            ws_pagos = workbook.add_worksheet("💳 Métodos Pago")
            ws_pagos.write(0, 0, "Método", header_format)
            ws_pagos.write(0, 1, "# Transacciones", header_format)
            ws_pagos.write(0, 2, "Total", header_format)
            ws_pagos.write(0, 3, "Promedio", header_format)
            ws_pagos.write(0, 4, "% del Total", header_format)
            
            pagos_resumen = defaultdict(lambda: {'total': 0, 'cantidad': 0})
            for venta in self.all_ventas:
                metodo = venta.get('metodo_pago', 'Efectivo')
                subtotal = float(venta.get('subtotal', 0) or 0)
                pagos_resumen[metodo]['total'] += subtotal
                pagos_resumen[metodo]['cantidad'] += 1
            
            total_pagos = sum(d['total'] for d in pagos_resumen.values())
            row = 1
            for metodo, datos in sorted(pagos_resumen.items(), key=lambda x: x[1]['total'], reverse=True):
                promedio = datos['total'] / datos['cantidad'] if datos['cantidad'] > 0 else 0
                pct = (datos['total'] / total_pagos * 100) if total_pagos > 0 else 0
                ws_pagos.write(row, 0, metodo, text_format)
                ws_pagos.write(row, 1, datos['cantidad'], number_format)
                ws_pagos.write(row, 2, datos['total'], money_format)
                ws_pagos.write(row, 3, promedio, money_format)
                ws_pagos.write(row, 4, pct, percent_format)
                row += 1
            
            ws_pagos.set_column(0, 4, 18)
            ws_pagos.freeze_panes(1, 0)
            
            # ===== HOJA 7: ANÁLISIS POR CATEGORÍA =====
            ws_cat = workbook.add_worksheet("📂 Por Categoría")
            ws_cat.write(0, 0, "Categoría", header_format)
            ws_cat.write(0, 1, "Productos", header_format)
            ws_cat.write(0, 2, "Stock Total", header_format)
            ws_cat.write(0, 3, "Valor Inventario", header_format)
            ws_cat.write(0, 4, "Ganancia Potencial", header_format)
            
            categorias = defaultdict(lambda: {'productos': 0, 'stock': 0, 'valor': 0, 'ganancia': 0})
            for prod in (cargar_productos(self.username) or []):
                cat = prod.get('categoria', 'Sin categoría')
                stock = float(prod.get('stock', 0) or 0)
                precio = float(prod.get('venta', 0) or 0)
                costo = float(prod.get('costo', 0) or 0)
                
                categorias[cat]['productos'] += 1
                categorias[cat]['stock'] += stock
                categorias[cat]['valor'] += precio * stock
                categorias[cat]['ganancia'] += (precio - costo) * stock
            
            row = 1
            for cat, datos in sorted(categorias.items(), key=lambda x: x[1]['valor'], reverse=True):
                ws_cat.write(row, 0, cat, text_format)
                ws_cat.write(row, 1, datos['productos'], number_format)
                ws_cat.write(row, 2, datos['stock'], number_format)
                ws_cat.write(row, 3, datos['valor'], money_format)
                ws_cat.write(row, 4, datos['ganancia'], money_format)
                row += 1
            
            ws_cat.set_column(0, 4, 20)
            ws_cat.freeze_panes(1, 0)
            
            # ===== HOJA 8: RESUMEN FINANCIERO =====
            ws_fin = workbook.add_worksheet("💹 Resumen Financiero")
            
            fin_fmt = workbook.add_format({
                'bold': True, 'font_size': 12, 'border': 1
            })
            fin_val_fmt = workbook.add_format({
                'font_size': 12, 'bold': True, 'num_format': '"S/. "#,##0.00'
            })
            
            row = 1
            financial_data = [
                ('Valor Total Inventario', total_inv),
                ('Costo Total Inventario', costo_inv),
                ('Ganancia Potencial', ganancia_pot),
                ('Total Vendido (Período)', total_ventas_val),
                ('Margen Promedio', ((total_precio_total - total_costo_total) / total_precio_total * 100) if total_precio_total > 0 else 0),
                ('ROI Estimado', (ganancia_pot / costo_inv * 100) if costo_inv > 0 else 0),
            ]
            
            for label, value in financial_data:
                ws_fin.write(row, 0, label, fin_fmt)
                if isinstance(value, float) and '%' not in label:
                    ws_fin.write(row, 1, value, fin_val_fmt)
                else:
                    pct_fmt = workbook.add_format({
                        'font_size': 12, 'bold': True, 'num_format': '0.0"%"'
                    })
                    ws_fin.write(row, 1, value / 100 if isinstance(value, (int, float)) else value, pct_fmt)
                row += 2
            
            ws_fin.set_column(0, 1, 25)
            
            # ===== HOJA 9: ANÁLISIS COMPARATIVO =====
            ws_comp = workbook.add_worksheet("Comparativa")
            
            ws_comp.write(0, 0, "Producto", header_format)
            ws_comp.write(0, 1, "Stock", header_format)
            ws_comp.write(0, 2, "Vendido", header_format)
            ws_comp.write(0, 3, "Ingresos", header_format)
            ws_comp.write(0, 4, "Ganancia", header_format)
            ws_comp.write(0, 5, "ROI %", header_format)
            ws_comp.write(0, 6, "Recomendación", header_format)
            
            row = 1
            for prod in sorted((cargar_productos(self.username) or []), 
                             key=lambda x: float(x.get('venta', 0) or 0) * float(x.get('stock', 0) or 0), 
                             reverse=True):
                nombre = prod.get('nombre', 'N/A')
                stock = float(prod.get('stock', 0) or 0)
                costo = float(prod.get('costo', 0) or 0)
                precio = float(prod.get('venta', 0) or 0)
                
                vendidos = sum(int(v.get('cantidad', 0) or 0) for v in self.all_ventas 
                             if v.get('producto', '').lower() == nombre.lower())
                
                ingresos = vendidos * precio
                ganancia = (precio - costo) * stock
                roi = (ganancia / (costo * stock) * 100) if (costo * stock) > 0 else 0
                
                # Recomendación
                if stock > 50 and vendidos < 5:
                    recom = "REDUCIR STOCK - Lento"
                elif stock < 3:
                    recom = "REABASTECER - Crítico"
                elif roi > 50:
                    recom = "AMPLIAR - Alto ROI"
                elif vendidos > 10:
                    recom = "POPULAR - Mantener"
                else:
                    recom = "NORMAL"
                
                ws_comp.write(row, 0, nombre, text_format)
                ws_comp.write(row, 1, stock, number_format)
                ws_comp.write(row, 2, vendidos, number_format)
                ws_comp.write(row, 3, ingresos, money_format)
                ws_comp.write(row, 4, ganancia, money_format)
                ws_comp.write(row, 5, roi, percent_format)
                ws_comp.write(row, 6, recom, text_center)
                row += 1
            
            ws_comp.set_column(0, 6, 18)
            ws_comp.freeze_panes(1, 0)
            ws_comp.autofilter(0, 0, row, 6)
            
            # ===== HOJA 10: ANÁLISIS POR CÓDIGO (SKU) =====
            ws_sku = workbook.add_worksheet("🏷️ Por Código (SKU)")
            
            ws_sku.write(0, 0, "Código SKU", header_format)
            ws_sku.write(0, 1, "Producto", header_format)
            ws_sku.write(0, 2, "# Vendidos", header_format)
            ws_sku.write(0, 3, "Ingresos", header_format)
            ws_sku.write(0, 4, "Frecuencia", header_format)
            
            sku_data = defaultdict(lambda: {'producto': '', 'cantidad': 0, 'ingresos': 0, 'frecuencia': 0})
            for venta in self.all_ventas:
                codigo = venta.get('codigo', 'SIN-CODIGO')
                producto = venta.get('producto', 'N/A')
                cantidad = int(venta.get('cantidad', 0) or 0)
                subtotal = float(venta.get('subtotal', 0) or 0)
                
                sku_data[codigo]['producto'] = producto
                sku_data[codigo]['cantidad'] += cantidad
                sku_data[codigo]['ingresos'] += subtotal
                sku_data[codigo]['frecuencia'] += 1
            
            row = 1
            for codigo, datos in sorted(sku_data.items(), key=lambda x: x[1]['ingresos'], reverse=True):
                ws_sku.write(row, 0, codigo, text_center)
                ws_sku.write(row, 1, datos['producto'], text_format)
                ws_sku.write(row, 2, datos['cantidad'], number_format)
                ws_sku.write(row, 3, datos['ingresos'], money_format)
                ws_sku.write(row, 4, datos['frecuencia'], number_format)
                row += 1
            
            ws_sku.set_column(0, 4, 18)
            ws_sku.freeze_panes(1, 0)
            ws_sku.autofilter(0, 0, row, 4)
            
            # ===== HOJA 11: ESTADÍSTICAS GENERALES =====
            ws_stats = workbook.add_worksheet("Estadísticas")
            
            # Calcular estadísticas
            num_productos = len(cargar_productos(self.username) or [])
            num_ventas = len(self.all_ventas)
            num_clientes_unicos = len(set(v.get('cliente', 'N/A') for v in self.all_ventas))
            ticket_promedio = (total_ventas_val / num_ventas) if num_ventas > 0 else 0
            
            stats_data = [
                ('GENERALES', ''),
                ('Total de Productos', num_productos),
                ('Total de Ventas Registradas', num_ventas),
                ('Clientes Únicos Detectados', num_clientes_unicos),
                ('Ticket Promedio', ticket_promedio),
                ('', ''),
                ('INVENTARIO', ''),
                ('Productos con Stock', sum(1 for p in (cargar_productos(self.username) or []) if float(p.get('stock', 0) or 0) > 0)),
                ('Productos sin Stock', sum(1 for p in (cargar_productos(self.username) or []) if float(p.get('stock', 0) or 0) == 0)),
                ('Stock Crítico (<3)', sum(1 for p in (cargar_productos(self.username) or []) if 0 < float(p.get('stock', 0) or 0) < 3)),
                ('Stock Muerto (>30 sin venta)', sum(1 for p in (cargar_productos(self.username) or []) if float(p.get('stock', 0) or 0) > 30)),
                ('', ''),
                ('VENTAS', ''),
                ('Total Ingresos', total_ventas_val),
                ('Ganancia Total', ganancia_pot),
                ('Margen Global', ((total_precio_total - total_costo_total) / total_precio_total * 100) if total_precio_total > 0 else 0),
                ('Costo COGS', total_costo_total),
            ]
            
            stat_title = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#E8E8E8'})
            stat_label = workbook.add_format({'align': 'left'})
            stat_value = workbook.add_format({'bold': True, 'num_format': '#,##0'})
            
            row = 0
            for label, value in stats_data:
                if value == '':
                    row += 1
                    continue
                if isinstance(label, str) and label.isupper() and not label == label.replace(' ', ''):
                    ws_stats.write(row, 0, label, stat_title)
                    row += 1
                elif isinstance(value, (int, float)):
                    ws_stats.write(row, 0, label, stat_label)
                    if 'Promedio' in label or 'Total' in label or 'Ganancia' in label:
                        ws_stats.write(row, 1, value, workbook.add_format({'bold': True, 'num_format': '"S/. "#,##0.00'}))
                    elif 'Margen' in label:
                        ws_stats.write(row, 1, value / 100, workbook.add_format({'bold': True, 'num_format': '0.0"%"'}))
                    else:
                        ws_stats.write(row, 1, value, stat_value)
                    row += 1
            
            ws_stats.set_column(0, 1, 30)
            
            # ===== HOJA 12: TENDENCIAS (Por Semana) =====
            ws_tend = workbook.add_worksheet("📉 Tendencias por Semana")
            
            ws_tend.write(0, 0, "Semana", header_format)
            ws_tend.write(0, 1, "# Ventas", header_format)
            ws_tend.write(0, 2, "Ingresos", header_format)
            ws_tend.write(0, 3, "Promedio/Venta", header_format)
            ws_tend.write(0, 4, "Variación %", header_format)
            
            tendencias = defaultdict(lambda: {'ventas': 0, 'ingresos': 0})
            for venta in self.all_ventas:
                try:
                    fecha_str = venta.get('fecha', '01/01/2024')
                    fecha_obj = datetime.datetime.strptime(str(fecha_str).split()[0], '%d/%m/%Y')
                    semana = f"Sem {fecha_obj.strftime('%U/%Y')}"
                    
                    tendencias[semana]['ventas'] += 1
                    tendencias[semana]['ingresos'] += float(venta.get('subtotal', 0) or 0)
                except:
                    pass
            
            row = 1
            prev_ingresos = 0
            for semana, datos in sorted(tendencias.items()):
                promedio = datos['ingresos'] / datos['ventas'] if datos['ventas'] > 0 else 0
                variacion = ((datos['ingresos'] - prev_ingresos) / prev_ingresos * 100) if prev_ingresos > 0 else 0
                
                ws_tend.write(row, 0, semana, text_format)
                ws_tend.write(row, 1, datos['ventas'], number_format)
                ws_tend.write(row, 2, datos['ingresos'], money_format)
                ws_tend.write(row, 3, promedio, money_format)
                ws_tend.write(row, 4, variacion, percent_format)
                
                prev_ingresos = datos['ingresos']
                row += 1
            
            ws_tend.set_column(0, 4, 18)
            
            workbook.close()
            
            # Mensaje de éxito
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("✅ Reporte Generado")
            msg.setText(f"📊 Reporte avanzado creado exitosamente\n\n{file_path}\n\n✨ Se incluyen 8 hojas con análisis completo")
            msg.setStandardButtons(QMessageBox.Ok)
            
            open_btn = msg.addButton("📂 Abrir", QMessageBox.ActionRole)
            msg.exec_()
            
            if msg.clickedButton() == open_btn:
                import os
                import subprocess
                if os.name == 'nt':
                    os.startfile(file_path)
                else:
                    subprocess.run(['open', file_path])
            
        except ImportError:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "❌ Error",
                "Se requiere xlsxwriter.\nInstálala: pip install xlsxwriter"
            )
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "❌ Error",
                f"Error al exportar: {str(e)}"
            )
    
    def _agrupar_ventas_por_periodo(self, ventas):
        """Agrupa ventas por período (día, semana, mes, año)"""
        from collections import defaultdict
        
        periodos = defaultdict(lambda: {
            'tipo': '', 'num_ventas': 0, 'total': 0, 
            'productos': set(), 'top_producto': ''
        })
        
        productos_periodo = defaultdict(lambda: defaultdict(float))
        
        for venta in ventas:
            try:
                fecha_str = venta.get('fecha', '01/01/2024')
                fecha_obj = datetime.datetime.strptime(str(fecha_str).split()[0], '%d/%m/%Y')
                
                # Por DÍA
                dia_key = fecha_obj.strftime('%d/%m/%Y (Día)')
                periodos[dia_key]['tipo'] = 'Día'
                periodos[dia_key]['num_ventas'] += 1
                periodos[dia_key]['total'] += float(venta.get('subtotal', 0) or 0)
                periodos[dia_key]['productos'].add(venta.get('producto', 'N/A'))
                productos_periodo[dia_key][venta.get('producto', 'N/A')] += float(venta.get('subtotal', 0) or 0)
                
                # Por SEMANA
                sem_key = f"Semana {fecha_obj.strftime('%U/%Y')}"
                periodos[sem_key]['tipo'] = 'Semana'
                periodos[sem_key]['num_ventas'] += 1
                periodos[sem_key]['total'] += float(venta.get('subtotal', 0) or 0)
                periodos[sem_key]['productos'].add(venta.get('producto', 'N/A'))
                productos_periodo[sem_key][venta.get('producto', 'N/A')] += float(venta.get('subtotal', 0) or 0)
                
                # Por MES
                mes_key = fecha_obj.strftime('%B %Y (Mes)')
                periodos[mes_key]['tipo'] = 'Mes'
                periodos[mes_key]['num_ventas'] += 1
                periodos[mes_key]['total'] += float(venta.get('subtotal', 0) or 0)
                periodos[mes_key]['productos'].add(venta.get('producto', 'N/A'))
                productos_periodo[mes_key][venta.get('producto', 'N/A')] += float(venta.get('subtotal', 0) or 0)
                
                # Por AÑO
                año_key = f"Año {fecha_obj.strftime('%Y')}"
                periodos[año_key]['tipo'] = 'Año'
                periodos[año_key]['num_ventas'] += 1
                periodos[año_key]['total'] += float(venta.get('subtotal', 0) or 0)
                periodos[año_key]['productos'].add(venta.get('producto', 'N/A'))
                productos_periodo[año_key][venta.get('producto', 'N/A')] += float(venta.get('subtotal', 0) or 0)
                
            except:
                pass
        
        # Calcular top producto por período
        for periodo in periodos:
            periodos[periodo]['productos'] = len(periodos[periodo]['productos'])
            if periodo in productos_periodo:
                top = max(productos_periodo[periodo].items(), key=lambda x: x[1], default=('N/A', 0))[0]
                periodos[periodo]['top_producto'] = top
        
        return periodos

    def _sanitize_sheet_name(self, name):
        """Convierte un nombre en un nombre válido para hoja de Excel"""
        # Excel permite máximo 31 caracteres y no permite: [ ] : * ? / \
        invalid_chars = r'[\[\]:*?/\\]'
        import re
        sanitized = re.sub(invalid_chars, '', str(name))
        sanitized = sanitized[:31]  # Máximo 31 caracteres
        return sanitized if sanitized else "Ventas"
    
    def generate_barcodes_pdf(self):
        """Genera un PDF de 80mm de ancho con todos los códigos de barras"""
        try:
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            from reportlab.lib.pagesizes import landscape
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            import os
            
            # Recopilar todas las rutas de códigos de barras
            barcodes_dir = os.path.join(VISO_DIR, "barcodes")
            
            if not os.path.exists(barcodes_dir):
                QMessageBox.warning(self, "Aviso", "No hay códigos de barras generados aún")
                return
            
            barcode_files = []
            for file in os.listdir(barcodes_dir):
                if file.endswith('.png'):
                    barcode_files.append(os.path.join(barcodes_dir, file))
            
            if not barcode_files:
                QMessageBox.warning(self, "Aviso", "No hay códigos de barras para generar PDF")
                return
            
            # Diálogo para guardar
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getSaveFileName(
                self,
                "Guardar PDF de Códigos de Barras",
                f"Barcodes_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return
            
            # Dimensiones: 80mm de ancho (papel térmico estándar)
            page_width = 80 * mm
            page_height = 100 * mm  # Altura variable según cantidad
            
            # Crear PDF
            pdf_canvas = canvas.Canvas(file_path, pagesize=(page_width, page_height))
            
            y_position = page_height - 10 * mm  # Empezar desde arriba
            barcode_height = 25 * mm
            
            for idx, barcode_path in enumerate(barcode_files):
                # Si no cabe en la página, crear nueva
                if y_position < barcode_height + 5 * mm:
                    pdf_canvas.showPage()
                    y_position = page_height - 10 * mm
                
                try:
                    # Leer imagen
                    img = ImageReader(barcode_path)
                    img_width, img_height = img.getSize()
                    
                    # Calcular proporción para que quepa en 80mm
                    scale_factor = (75 * mm) / img_width
                    new_width = 75 * mm
                    new_height = img_height * scale_factor
                    
                    # Dibujar imagen centrada
                    x_centered = (page_width - new_width) / 2
                    pdf_canvas.drawImage(
                        barcode_path,
                        x_centered,
                        y_position - new_height,
                        width=new_width,
                        height=new_height,
                        preserveAspectRatio=True
                    )
                    
                    # Obtener nombre del producto del archivo
                    filename = os.path.basename(barcode_path)
                    product_name = filename.split('_')[0] if '_' in filename else 'Producto'
                    
                    # Agregar nombre del producto debajo
                    pdf_canvas.setFont("Helvetica", 8)
                    pdf_canvas.drawCentredString(
                        page_width / 2,
                        y_position - new_height - 3 * mm,
                        product_name[:30]  # Limitar longitud
                    )
                    
                    # Mover a siguiente posición
                    y_position -= (new_height + 5 * mm)
                    
                except Exception as e:
                    print(f"Error procesando {barcode_path}: {e}")
                    continue
            
            # Guardar y cerrar
            pdf_canvas.save()
            
            QMessageBox.information(
                self,
                "✅ Éxito",
                f"PDF generado exitosamente:\n\n{file_path}\n\nTotal: {len(barcode_files)} códigos de barras"
            )
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "❌ Error",
                f"Error al generar PDF: {str(e)}"
            )
        pass
