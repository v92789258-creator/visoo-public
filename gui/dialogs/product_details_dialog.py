from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QPushButton, QTabWidget, QWidget, QGridLayout, QFrame,
    QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
import os

class ProductDetailsDialog(QDialog):
    def __init__(self, product_data, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.setup_ui()
        self.load_product_data()

    def setup_ui(self):
        self.setWindowTitle("Detalles del Producto")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        # Removido setFixedSize para permitir redimensionar
        self.resize(1000, 700)  # Tamaño inicial más grande
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            QTabWidget::pane {
                border: none;
                background: white;
                border-radius: 8px;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background: #F8F9FA;
                color: #495057;
                min-width: 120px;
                padding: 12px 20px;
                margin: 0 4px;
                border: none;
                border-radius: 6px 6px 0 0;
            }
            QTabBar::tab:selected {
                background: white;
                color: #0D6EFD;
                font-weight: bold;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        # Layout principal
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Panel izquierdo (imagen)
        left_panel = QWidget()
        left_panel.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(20)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # Sección de imagen
        self.image_label = QLabel()
        self.image_label.setFixedSize(400, 400)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #F8F9FA;
                border: 2px solid #E9ECEF;
                border-radius: 12px;
            }
        """)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        left_layout.addWidget(self.image_label)
        left_layout.addStretch()
        
        # Panel derecho (información en pestañas)
        right_panel = QWidget()
        right_panel.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(20)
        
        # Título del producto
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setSpacing(8)
        
        # Código del producto
        self.code_label = QLabel()
        self.code_label.setStyleSheet("""
            QLabel {
                color: #6C757D;
                font-size: 15px;
                font-weight: 500;
            }
        """)
        title_layout.addWidget(self.code_label)
        
        # Nombre del producto
        self.name_label = QLabel()
        self.name_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #212529;
                padding: 5px 0;
            }
        """)
        title_layout.addWidget(self.name_label)
        
        right_layout.addWidget(title_container)
        
        # Crear pestañas
        tab_widget = QTabWidget()
        
        # Pestaña 1: Información General
        general_tab = QScrollArea()
        general_tab.setWidgetResizable(True)
        general_content = QWidget()
        general_layout = QVBoxLayout(general_content)
        
        # Sección de marca y categoría
        brand_category = self.create_info_section("Información General", [
            ("Marca", "marca"),
            ("Categoría", "categoria")
        ])
        general_layout.addWidget(brand_category)
        
        # Sección de precios
        prices = self.create_info_section("Precios", [
            ("Precio de Venta", "venta", "S/ {:.2f}"),
            ("Precio Regular", "precio_regular", "S/ {:.2f}"),
            ("Precio de Compra", "costo", "S/ {:.2f}")
        ])
        general_layout.addWidget(prices)
        
        # Stock y disponibilidad
        stock = self.create_info_section("Inventario", [
            ("Stock Actual", "stock", "{} unidades")
        ])
        general_layout.addWidget(stock)
        
        general_tab.setWidget(general_content)
        tab_widget.addTab(general_tab, "General")
        
        # Pestaña 2: Detalles Técnicos
        tech_tab = QScrollArea()
        tech_tab.setWidgetResizable(True)
        tech_content = QWidget()
        tech_layout = QVBoxLayout(tech_content)
        
        # Especificaciones técnicas
        specs = self.create_info_section("Especificaciones", [
            ("Material", "material"),
            ("Color", "color"),
            ("Talla", "talla"),
            ("Tipo de Lente", "tipo_lente")
        ])
        tech_layout.addWidget(specs)
        
        # Características
        features = self.create_features_section("Características", [
            ("polarizado", "Polarizado"),
            ("uv", "Protección UV"),
            ("antireflejo", "Antireflejo"),
            ("fotocromático", "Fotocromático"),
            ("blue_light", "Filtro Luz Azul")
        ])
        tech_layout.addWidget(features)
        
        tech_tab.setWidget(tech_content)
        tab_widget.addTab(tech_tab, "Detalles Técnicos")
        
        right_layout.addWidget(tab_widget)
        
        # Botón de cerrar
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                color: #424242;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
        """)
        close_btn.clicked.connect(self.close)
        right_layout.addWidget(close_btn, alignment=Qt.AlignRight)
        
        # Agregar paneles al layout principal
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

    def create_info_section(self, title, fields):
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #E9ECEF;
                border-radius: 12px;
                margin: 5px 0;
            }
        """)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título de la sección
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #0D6EFD;
                padding-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Grid para los campos
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.setColumnStretch(1, 1)
        
        for row, (label, key, *fmt) in enumerate(fields):
            # Contenedor para cada fila
            row_container = QFrame()
            row_container.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            row_layout = QHBoxLayout(row_container)
            row_layout.setContentsMargins(15, 10, 15, 10)
            
            # Etiqueta del campo
            field_label = QLabel(f"{label}:")
            field_label.setStyleSheet("""
                QLabel {
                    color: #495057;
                    font-weight: 600;
                    font-size: 14px;
                }
            """)
            field_label.setMinimumWidth(120)
            row_layout.addWidget(field_label)
            
            # Valor del campo
            value_label = QLabel()
            value_label.setObjectName(f"value_{key}")
            value_label.setStyleSheet("""
                QLabel {
                    color: #212529;
                    font-size: 14px;
                    font-weight: 500;
                }
            """)
            value_label.setWordWrap(True)
            row_layout.addWidget(value_label, 1)
            
            grid.addWidget(row_container, row, 0, 1, 2)
        
        layout.addLayout(grid)
        return section

    def create_features_section(self, title, features):
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin: 5px 0;
            }
        """)
        layout = QVBoxLayout(section)
        
        # Título de la sección
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1976D2;
                padding-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Grid para las características
        grid = QGridLayout()
        grid.setSpacing(10)
        
        for i, (key, label) in enumerate(features):
            row = i // 2
            col = i % 2
            
            feature_label = QLabel()
            feature_label.setObjectName(f"feature_{key}")
            grid.addWidget(feature_label, row, col)
        
        layout.addLayout(grid)
        return section

    def load_product_data(self):
        # Cargar imagen
        image_path = self.product_data.get('image_path') or self.product_data.get('imagen')
        if image_path and os.path.exists(image_path):
            try:
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        self.image_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled_pixmap)
                else:
                    self.image_label.setText("Error al cargar imagen")
            except Exception as e:
                print(f"Error al cargar la imagen: {str(e)}")
                self.image_label.setText("Error al cargar imagen")
        else:
            if image_path:
                print(f"Ruta de imagen no encontrada: {image_path}")
            self.image_label.setText("Sin imagen")
        
        # Cargar título y código
        self.code_label.setText(f"Código: {self.product_data.get('codigo', 'N/A')}")
        self.name_label.setText(self.product_data.get('nombre', 'Sin nombre'))
        
        # Cargar campos básicos
        basic_fields = {
            'marca': ('value_marca', None),
            'categoria': ('value_categoria', None),
            'venta': ('value_venta', lambda x: f"S/ {float(x):.2f}"),
            'precio_regular': ('value_precio_regular', lambda x: f"S/ {float(x):.2f}"),
            'costo': ('value_costo', lambda x: f"S/ {float(x):.2f}"),
            'stock': ('value_stock', lambda x: f"{int(x)} unidades"),
            'material': ('value_material', None),
            'color': ('value_color', None),
            'talla': ('value_talla', None),
            'tipo_lente': ('value_tipo_lente', None)
        }
        
        for key, (widget_name, formatter) in basic_fields.items():
            value = self.product_data.get(key, 'N/A')
            if formatter:
                try:
                    value = formatter(value)
                except:
                    value = 'N/A'
            widget = self.findChild(QLabel, widget_name)
            if widget:
                if key in ['venta', 'precio_regular', 'costo']:
                    # Agregar estilo especial para precios
                    widget.setStyleSheet("""
                        QLabel {
                            color: #198754;
                            font-size: 16px;
                            font-weight: bold;
                        }
                    """)
                elif key == 'stock':
                    # Estilo especial para stock
                    stock_value = int(value.split()[0]) if isinstance(value, str) and value.split()[0].isdigit() else 0
                    if stock_value == 0:
                        color = "#DC3545"  # Rojo para sin stock
                    elif stock_value < 5:
                        color = "#FFC107"  # Amarillo para stock bajo
                    else:
                        color = "#198754"  # Verde para stock normal
                    widget.setStyleSheet(f"""
                        QLabel {{
                            color: {color};
                            font-size: 15px;
                            font-weight: bold;
                            padding: 5px 10px;
                            background: {color}15;
                            border-radius: 4px;
                        }}
                    """)
                widget.setText(str(value))
        
        # Cargar características
        features = ['polarizado', 'uv', 'antireflejo', 'fotocromático', 'blue_light']
        caracteristicas = self.product_data.get('caracteristicas', {})
        
        for feature in features:
            widget = self.findChild(QLabel, f"feature_{feature}")
            if widget:
                is_active = caracteristicas.get(feature, False)
                feature_name = feature.replace('_', ' ').title()
                widget.setText(feature_name)
                widget.setStyleSheet(f"""
                    QLabel {{
                        background-color: {'#E9ECEF' if not is_active else '#0D6EFD15'};
                        color: {'#6C757D' if not is_active else '#0D6EFD'};
                        font-weight: 500;
                        font-size: 14px;
                        padding: 8px 15px;
                        border-radius: 6px;
                        border: {'1px solid #DEE2E6' if not is_active else '1px solid #0D6EFD40'};
                    }}
                """)
                
                # Agregar icono
                icon = "✓" if is_active else "○"
                widget.setText(f"{icon}  {feature_name}")