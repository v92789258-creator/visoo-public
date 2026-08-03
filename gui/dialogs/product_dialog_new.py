from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget,
    QWidget, QGridLayout, QCheckBox, QFrame, QScrollArea, QFileDialog,
    QMessageBox, QListWidget
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon
from .category_manager_dialog import CategoryManagerDialog
from .brand_manager_dialog import BrandManagerDialog
from .colors_manager_dialog import ColorsManagerDialog
from .material_manager_dialog import MaterialManagerDialog
from .color_manager_dialog import ColorManagerDialog
from utils.barcode_scanner import BarcodeLineEdit
import os
import random
import json
from pathlib import Path


class SelectAllDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox personalizado que selecciona todo el texto al hacer focus."""
    
    def focusInEvent(self, event):
        super().focusInEvent(event)
        # Seleccionar todo el texto del campo de entrada
        self.lineEdit().selectAll()
    
    def keyPressEvent(self, event):
        """Interceptar pulsación de teclas para reemplazar el texto seleccionado."""
        line_edit = self.lineEdit()
        
        # Si hay texto seleccionado y se presiona un número o punto
        if line_edit.selectedText() and (event.text().isdigit() or event.text() == '.'):
            # Reemplazar la selección con el nuevo carácter
            line_edit.cut()
            line_edit.insert(event.text())
            return 
        
        # Para otras teclas, usar el comportamiento normal
        super().keyPressEvent(event)


class OpticalProductDialog(QDialog):
    def __init__(self, product_data=None, parent=None):
        super().__init__(parent)
        # Detectar si es un producto nuevo ANTES de asignar product_data
        self.is_new_product = product_data is None or not product_data
        print(f"[DEBUG] OpticalProductDialog.__init__: product_data={product_data}, is_new_product={self.is_new_product}")
        self.product_data = product_data or {}
        self.setup_ui()
        self.load_available_colors()  # Cargar colores disponibles
        if product_data:
            self.load_product_data()

    def generate_random_code(self):
        """Genera un código aleatorio de entre 10 y 12 dígitos."""
        length = random.randint(10, 12)
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

    def _resolve_username_from_parents(self):
        """Busca el username recorriendo la cadena de padres del diálogo."""
        username = None
        current = self.parent()
        while current and not username:
            username = getattr(current, 'username', None)
            try:
                current = current.parent() if hasattr(current, 'parent') and callable(current.parent) else None
            except Exception:
                current = None
        return str(username or "").strip()

    def _load_local_products_for_code_generation(self, username):
        """
        Carga solo el JSON local editable del contexto actual.
        No usa restore remoto ni consolidado para no frenar la apertura del diálogo.
        """
        if not username:
            return []

        try:
            from utils.file_handler import get_user_file_path

            productos_file = Path(get_user_file_path(username, "productos.json"))
            if productos_file.exists():
                with open(productos_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data

            alt_file = Path(get_user_file_path(username, "products.json"))
            if alt_file.exists():
                with open(alt_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"[WARNING] Error cargando productos locales para código secuencial: {e}")

        return []
    
    def _load_products_for_code_generation(self, username):
        """Carga productos desde la fuente actual del inventario."""
        if not username:
            return []

        try:
            from utils.file_handler import cargar_productos

            data = cargar_productos(username, prefer_cloud=True)
            if isinstance(data, list):
                return data
        except Exception as e:
            print(f"[WARNING] Error cargando productos para cÃ³digo secuencial: {e}")

        return []

    def generate_next_sequential_code(self):
        """Genera el siguiente código secuencial basado en los códigos existentes.
        
        Busca todos los códigos en formato NNNNNN (números de 0-7 dígitos)
        y retorna el siguiente en la secuencia, con el formato 0000001, 0000002, etc.
        """
        try:
            username = self._resolve_username_from_parents()
            if not username:
                return "0000001"

            productos = self._load_products_for_code_generation(username)
            if not productos:
                return "0000001"
            
            # Extraer códigos numéricos de máximo 7 dígitos (formato secuencial)
            numeric_codes = []
            for prod in productos:
                codigo = prod.get('codigo', '').strip()
                # Solo procesar códigos que sean números y tengan máximo 7 dígitos
                if codigo and codigo.isdigit() and len(codigo) <= 7:
                    try:
                        numeric_codes.append(int(codigo))
                    except (ValueError, TypeError):
                        pass
            
            # Si hay códigos numéricos, obtener el máximo y sumar 1
            if numeric_codes:
                max_code = max(numeric_codes)
                next_code = max_code + 1
            else:
                next_code = 1
            
            return f"{next_code:07d}"
        except Exception as e:
            # Si hay error, devolver el código por defecto
            print(f"[ERROR] Error al generar código secuencial: {e}")
            import traceback
            traceback.print_exc()
            return "0000001"
    
    def update_brands_combo(self):
        """Actualiza la lista de marcas en el combo box."""
        current_text = self.marca.currentText()
        try:
            with open(os.path.join("VISO", "data", "brands.json"), 'r', encoding='utf-8') as f:
                brands = json.load(f)
                self.marca.clear()
                self.marca.addItems(sorted(brands.keys()))
        except:
            # No agregar marcas por defecto si el archivo no existe.
            # Dejar la lista vacía para que el usuario añada sus propias marcas.
            try:
                self.marca.clear()
            except Exception:
                pass
        if current_text:
            index = self.marca.findText(current_text)
            if index >= 0:
                self.marca.setCurrentIndex(index)
    
    def update_categories_combo(self):
        """Actualiza la lista de categorías en el combo box."""
        current_text = self.categoria.currentText()
        try:
            with open(os.path.join("VISO", "data", "categories.json"), 'r', encoding='utf-8') as f:
                categories = json.load(f)
                self.categoria.clear()
                self.categoria.addItems(sorted(categories))
        except:
            # Si no existe el archivo, usar categorías por defecto
            self.categoria.clear()
            self.categoria.addItems([
                "Monturas", "Lunas", "Lentes de Contacto", 
                "Gafas de Sol", "Accesorios", "Líquidos de Limpieza"
            ])
        if current_text:
            index = self.categoria.findText(current_text)
            if index >= 0:
                self.categoria.setCurrentIndex(index)
    
    def _extract_material_names_safe(self, data):
        """Extrae nombres de materiales de forma segura."""
        if not data or not isinstance(data, list):
            return []
        
        try:
            result = []
            for i, item in enumerate(data):
                try:
                    if isinstance(item, dict):
                        name = item.get('name', '')
                        if isinstance(name, str) and name:
                            result.append(name)
                    elif isinstance(item, str):
                        if item:
                            result.append(item)
                except Exception as item_error:
                    print(f"[WARNING] Error procesando item {i}: {item_error}")
                    continue
            return result
        except Exception as e:
            print(f"[ERROR] Error en _extract_material_names_safe: {e}")
            return []
                
    def update_materials_combo(self):
        """Actualiza la lista de materiales en el combo box desde el usuario."""
        current_text = self.material.currentText()
        try:
            # Obtener username del parent
            username = None
            current = self.parent()
            while current and not username:
                username = getattr(current, 'username', None)
                current = current.parent() if hasattr(current, 'parent') else None
            
            if not username:
                # Si no hay username, cargar archivo global
                materials_path = os.path.join("VISO", "data", "materials.json")
            else:
                # Cargar del usuario específico
                materials_path = os.path.join("VISO", username, "data", "materials.json")
            
            if os.path.exists(materials_path):
                with open(materials_path, 'r', encoding='utf-8') as f:
                    materials_data = json.load(f)
                    # Extraer nombres de forma segura
                    materials = self._extract_material_names_safe(materials_data)
                    self.material.clear()
                    if materials:
                        self.material.addItems(sorted(materials))
            else:
                # Si no existe el archivo, usar combo vacío
                self.material.clear()
        except Exception as e:
            print(f"[ERROR] Error en update_materials_combo: {e}")
            import traceback
            traceback.print_exc()
            self.material.clear()
        
        if current_text:
            index = self.material.findText(current_text)
            if index >= 0:
                self.material.setCurrentIndex(index)

    def update_sizes_combo(self):
        """Actualiza la lista de tallas en el combo box."""
        current_text = self.talla.currentText()
        try:
            with open(os.path.join("VISO", "data", "sizes.json"), 'r', encoding='utf-8') as f:
                sizes = json.load(f)
                self.talla.clear()
                self.talla.addItems(sorted(sizes))
        except:
            # Si no existe el archivo, usar tallas por defecto
            self.talla.clear()
            self.talla.addItems([
                "S", "M", "L", "XL", "XXL", "Única"
            ])
        if current_text:
            index = self.talla.findText(current_text)
            if index >= 0:
                self.talla.setCurrentIndex(index)

    def update_lens_types_combo(self):
        """Actualiza la lista de tipos de lente en el combo box."""
        current_text = self.tipo_lente.currentText()
        try:
            with open(os.path.join("VISO", "data", "lens_types.json"), 'r', encoding='utf-8') as f:
                lens_types = json.load(f)
                self.tipo_lente.clear()
                self.tipo_lente.addItems(sorted(lens_types))
        except:
            # Si no existe el archivo, usar tipos por defecto
            self.tipo_lente.clear()
            self.tipo_lente.addItems([
                "Monofocal", "Bifocal", "Multifocal", "Progresivo",
                "Fotocromático", "Polarizado", "No es lente"
            ])
        if current_text:
            index = self.tipo_lente.findText(current_text)
            if index >= 0:
                self.tipo_lente.setCurrentIndex(index)
    
    def manage_brands(self):
        """Abre el diálogo de gestión de marcas."""
        dialog = BrandManagerDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_brands_combo()
    
    def manage_categories(self):
        """Abre el diálogo de gestión de categorías."""
        dialog = CategoryManagerDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_categories_combo()
    
    def manage_materials(self):
        """Abre el diálogo de gestión de materiales."""
        dialog = MaterialManagerDialog(self)
        result = dialog.exec_()
        # Siempre recargar los materiales después de cerrar el diálogo
        self.update_materials_combo()
        if result == QDialog.Accepted:
            pass  # Ya se recargaron arriba
    
    def manage_colors(self):
        """Abre el diálogo de gestión de colores."""
        dialog = ColorManagerDialog(self)
        result = dialog.exec_()
        # Siempre recargar los colores después de cerrar el diálogo
        self.load_available_colors()
        if result == QDialog.Accepted:
            pass  # Ya se recargaron arriba
    
    def on_colors_toggle_changed(self, state):
        """Habilita/deshabilita la lista de colores según el toggle."""
        self.colors_list.setEnabled(state == Qt.Checked)
    
    def on_size_toggle_changed(self, state):
        """Habilita/deshabilita el selector de talla según el toggle."""
        self.talla.setEnabled(state == Qt.Checked)
    
    def on_lens_toggle_changed(self, state):
        """Habilita/deshabilita el selector de tipo de lente según el toggle."""
        self.tipo_lente.setEnabled(state == Qt.Checked)
    
    def on_material_toggle_changed(self, state):
        """Habilita/deshabilita el selector de material según el toggle."""
        self.material.setEnabled(state == Qt.Checked)

    def setup_ui(self):
        self.setWindowTitle("Producto Óptico")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # Configurar botones de la ventana (minimizar, maximizar, cerrar)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)
        
        # Layout principal
        main_layout = QHBoxLayout(self)
        
        # Panel izquierdo (imagen y detalles básicos)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        
        # Sección de imagen
        self.image_label = QLabel()
        self.image_label.setFixedSize(300, 300)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
            }
        """)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        # Botón para seleccionar imagen
        self.btn_select_image = QPushButton("Seleccionar Imagen")
        self.btn_select_image.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_select_image.clicked.connect(self.select_image)
        
        left_layout.addWidget(self.image_label)
        left_layout.addWidget(self.btn_select_image)
        left_layout.addStretch()
        
        # Panel derecho (formulario con pestañas)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Crear pestañas
        tab_widget = QTabWidget()
        
        # Pestaña 1: Información General
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        general_layout.setSpacing(15)
        
        # Crear campo de código con botón de escanear
        codigo_widget = QWidget()
        codigo_layout = QHBoxLayout(codigo_widget)
        codigo_layout.setContentsMargins(0, 0, 0, 0)
        
        self.codigo = BarcodeLineEdit()
        self.codigo.setPlaceholderText("Escanea el código de barras")
        # Si es un producto nuevo, generar el código secuencial automáticamente
        print(f"[DEBUG] setup_ui: self.is_new_product={self.is_new_product}")
        if self.is_new_product:
            next_code = self.generate_next_sequential_code()
            print(f"[DEBUG] Generated next_code: {next_code}")
            self.codigo.setText(next_code)
            print(f"[DEBUG] Set codigo text to: {self.codigo.text()}")
        
        self.codigo.barcode_captured.connect(self.on_barcode_scanned)
        
        codigo_layout.addWidget(self.codigo)
        
        self.nombre = QLineEdit()
        
        # Widget para marca con botón de gestión
        marca_widget = QWidget()
        marca_layout = QHBoxLayout(marca_widget)
        marca_layout.setContentsMargins(0, 0, 0, 0)
        
        self.marca = QComboBox()
        self.marca.setEditable(True)
        self.update_brands_combo()
        
        manage_brands_btn = QPushButton("Gestionar")
        manage_brands_btn.setMaximumWidth(80)
        manage_brands_btn.clicked.connect(self.manage_brands)
        
        marca_layout.addWidget(self.marca)
        marca_layout.addWidget(manage_brands_btn)
        
        # Widget para categoría con botón de gestión
        categoria_widget = QWidget()
        categoria_layout = QHBoxLayout(categoria_widget)
        categoria_layout.setContentsMargins(0, 0, 0, 0)
        
        self.categoria = QComboBox()
        self.update_categories_combo()
        
        manage_categories_btn = QPushButton("Gestionar")
        manage_categories_btn.setMaximumWidth(80)
        manage_categories_btn.clicked.connect(self.manage_categories)
        
        categoria_layout.addWidget(self.categoria)
        categoria_layout.addWidget(manage_categories_btn)
        
        # Crear componentes para material, talla y tipo de lente
        self.material = QComboBox()
        self.talla = QComboBox()
        self.tipo_lente = QComboBox()
        
        # Cargar valores iniciales
        self.update_materials_combo()
        self.update_sizes_combo()
        self.update_lens_types_combo()
        
        general_layout.addRow("Código:", codigo_widget)
        general_layout.addRow("Nombre:", self.nombre)
        general_layout.addRow("Marca:", marca_widget)
        general_layout.addRow("Categoría:", categoria_widget)
        
        # Pestaña 2: Detalles Técnicos
        tech_tab = QWidget()
        tech_layout = QVBoxLayout(tech_tab)
        tech_layout.setSpacing(15)
        
        # Sección de Variantes
        variants_label = QLabel("Variantes del Producto")
        variants_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        tech_layout.addWidget(variants_label)
        
        # Grid para toggles de variantes
        variants_grid = QGridLayout()
        
        # Toggle para Material
        self.toggle_material = QCheckBox("Activar Variante de Material")
        self.toggle_material.setChecked(False)
        self.toggle_material.stateChanged.connect(self.on_material_toggle_changed)
        variants_grid.addWidget(self.toggle_material, 0, 0, 1, 2)
        
        # Selector de material (inicialmente deshabilitado)
        material_label = QLabel("Material:")
        material_label.setStyleSheet("margin-left: 20px;")
        variants_grid.addWidget(material_label, 1, 0)
        
        # Botón de gestión de materiales
        manage_materials_btn = QPushButton("Gestionar")
        manage_materials_btn.setMaximumWidth(100)
        manage_materials_btn.clicked.connect(self.manage_materials)
        
        # Layout para material + botón
        material_widget = QWidget()
        material_widget_layout = QHBoxLayout(material_widget)
        material_widget_layout.setContentsMargins(0, 0, 0, 0)
        
        # No recrear el material combo, usar el que ya existe
        self.material.setEnabled(False)
        self.material.setStyleSheet("margin-left: 20px;")
        material_widget_layout.addWidget(self.material)
        material_widget_layout.addWidget(manage_materials_btn)
        material_widget_layout.addStretch()
        
        variants_grid.addWidget(material_widget, 1, 0, 1, 2)
        
        # Toggle para Colores
        self.toggle_colors = QCheckBox("Activar Variante de Colores")
        self.toggle_colors.setChecked(False)
        self.toggle_colors.stateChanged.connect(self.on_colors_toggle_changed)
        variants_grid.addWidget(self.toggle_colors, 2, 0, 1, 2)
        
        # Lista de colores (inicialmente deshabilitada)
        color_label = QLabel("Colores:")
        color_label.setStyleSheet("margin-left: 20px;")
        variants_grid.addWidget(color_label, 3, 0)
        
        # Botón de gestión de colores
        manage_colors_btn = QPushButton("Gestionar")
        manage_colors_btn.setMaximumWidth(100)
        manage_colors_btn.clicked.connect(self.manage_colors)
        variants_grid.addWidget(manage_colors_btn, 3, 1)
        
        color_widget = QWidget()
        color_layout = QVBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        
        self.colors_list = QListWidget()
        self.colors_list.setSelectionMode(QListWidget.MultiSelection)
        self.colors_list.setMaximumHeight(100)
        self.colors_list.setEnabled(False)
        self.colors_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 5px;
                background: white;
                margin-left: 20px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #F0F0F0;
            }
            QListWidget::item:selected {
                background: #E3F2FD;
                color: #1976D2;
            }
        """)
        
        self.load_available_colors()
        color_layout.addWidget(self.colors_list)
        variants_grid.addWidget(color_widget, 4, 0, 1, 2)
        
        # Toggle para Talla
        self.toggle_size = QCheckBox("Activar Variante de Talla")
        self.toggle_size.setChecked(False)
        self.toggle_size.stateChanged.connect(self.on_size_toggle_changed)
        variants_grid.addWidget(self.toggle_size, 5, 0, 1, 2)
        
        # Selector de talla (inicialmente deshabilitado)
        size_label = QLabel("Talla:")
        size_label.setStyleSheet("margin-left: 20px;")
        variants_grid.addWidget(size_label, 6, 0)
        
        self.talla = QComboBox()
        self.talla.addItems(["S", "M", "L", "XL", "Universal"])
        self.talla.setEnabled(False)
        self.talla.setStyleSheet("margin-left: 20px;")
        variants_grid.addWidget(self.talla, 6, 1)
        
        # Toggle para Tipo de Lente
        self.toggle_lens = QCheckBox("Activar Variante de Tipo de Lente")
        self.toggle_lens.setChecked(False)
        self.toggle_lens.stateChanged.connect(self.on_lens_toggle_changed)
        variants_grid.addWidget(self.toggle_lens, 7, 0, 1, 2)
        
        # Selector de tipo de lente (inicialmente deshabilitado)
        lens_label = QLabel("Tipo de Lente:")
        lens_label.setStyleSheet("margin-left: 20px;")
        variants_grid.addWidget(lens_label, 8, 0)
        
        self.tipo_lente = QComboBox()
        self.tipo_lente.addItems([
            "Monofocal", "Bifocal", "Progresivo", "Fotocromático",
            "Polarizado", "Anti Blue-Light"
        ])
        self.tipo_lente.setEnabled(False)
        self.tipo_lente.setStyleSheet("margin-left: 20px;")
        variants_grid.addWidget(self.tipo_lente, 8, 1)
        
        tech_layout.addLayout(variants_grid)
        tech_layout.addStretch()
        
        # Pestaña 3: Inventario y Precios
        inventory_tab = QWidget()
        inventory_layout = QFormLayout(inventory_tab)
        inventory_layout.setSpacing(15)
        
        self.stock = QSpinBox()
        self.stock.setRange(0, 9999)
        
        self.precio_compra = SelectAllDoubleSpinBox()
        self.precio_compra.setRange(0, 99999.99)
        self.precio_compra.setDecimals(2)
        self.precio_compra.setSuffix(" PEN")
        
        self.precio_venta = SelectAllDoubleSpinBox()
        self.precio_venta.setRange(0, 99999.99)
        self.precio_venta.setDecimals(2)
        self.precio_venta.setSuffix(" PEN")
        
        self.precio_regular = SelectAllDoubleSpinBox()
        self.precio_regular.setRange(0, 99999.99)
        self.precio_regular.setDecimals(2)
        self.precio_regular.setSuffix(" PEN")
        
        inventory_layout.addRow("Stock:", self.stock)
        inventory_layout.addRow("Precio de Compra:", self.precio_compra)
        inventory_layout.addRow("Precio de Venta:", self.precio_venta)
        inventory_layout.addRow("Precio Regular:", self.precio_regular)
        
        # Pestaña 4: Características Adicionales
        features_tab = QWidget()
        features_layout = QVBoxLayout(features_tab)
        
        # Grupo de características para monturas
        frame_group = QWidget()
        frame_layout = QGridLayout(frame_group)
        
        self.features = {
            'polarizado': QCheckBox("Polarizado"),
            'uv': QCheckBox("Protección UV"),
            'antireflejo': QCheckBox("Antireflejo"),
            'fotocromático': QCheckBox("Fotocromático"),
            'blue_light': QCheckBox("Filtro Luz Azul")
        }
        
        row = 0
        col = 0
        for feature in self.features.values():
            frame_layout.addWidget(feature, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        features_layout.addWidget(frame_group)
        features_layout.addStretch()
        
        # Agregar todas las pestañas
        tab_widget.addTab(general_tab, "General")
        tab_widget.addTab(tech_tab, "Detalles Técnicos")
        tab_widget.addTab(inventory_tab, "Inventario y Precios")
        
        # Solo agregar la pestaña de características si no es un producto nuevo
        if not self.is_new_product:
            tab_widget.addTab(features_tab, "Características")
        
        right_layout.addWidget(tab_widget)
        
        # Botones de acción
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 15, 0, 0)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                color: #424242;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton("Guardar")
        self.btn_save.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                background-color: #191919;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #191919;
            }
        """)
        self.btn_save.clicked.connect(self.save_product)
        
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_save)
        
        right_layout.addWidget(button_container)
        
        # Agregar paneles al layout principal
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
        # Establecer el foco en el campo de código por defecto
        self.codigo.setFocus()
        
        # Solo iniciar modo de escaneo si es un producto existente (no nuevo)
        # Si es nuevo, ya tiene el código generado y no queremos que se borre
        if not self.is_new_product:
            self.codigo.start_scanning()

    def select_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Imagen",
            "",
            "Imágenes (*.png *.jpg *.jpeg);;Todos los archivos (*.*)"
        )
        if file_name:
            pixmap = QPixmap(file_name)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.selected_image_path = file_name

    def load_available_colors(self):
        """Cargar la lista de colores disponibles desde el archivo."""
        try:
            file_path = os.path.join("VISO", "data", "colors.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    colors = json.load(f)
                    print(f"[DEBUG] Colores cargados desde JSON: {colors}")
            else:
                colors = [
                    "Negro", "Blanco", "Dorado", "Plateado", "Azul", "Verde",
                    "Rojo", "Rosa", "Morado", "Marrón", "Gris", "Transparente"
                ]
            # Limpiar lista y agregar colores nuevamente
            self.colors_list.blockSignals(True)
            self.colors_list.clear()
            self.colors_list.addItems(sorted(colors))
            self.colors_list.blockSignals(False)
            print(f"[DEBUG] Lista de colores actualizada con {self.colors_list.count()} items")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar colores: {str(e)}")
            print(f"[DEBUG] Error al cargar colores: {e}")

    def load_product_data(self):
        # Cargar datos existentes en el formulario
        self.codigo.setText(self.product_data.get('codigo', ''))
        self.nombre.setText(self.product_data.get('nombre', ''))
        
        # Cargar estado de variantes (Activar/Desactivar)
        variantes = self.product_data.get('variantes', {})
        self.toggle_material.setChecked(variantes.get('material', False))
        self.toggle_colors.setChecked(variantes.get('colores', False))
        self.toggle_size.setChecked(variantes.get('talla', False))
        self.toggle_lens.setChecked(variantes.get('tipo_lente', False))
        
        # Seleccionar los colores guardados
        saved_colors = self.product_data.get('colors', [])
        for i in range(self.colors_list.count()):
            item = self.colors_list.item(i)
            if item.text() in saved_colors:
                item.setSelected(True)
        
        # Establecer marca si existe
        marca = self.product_data.get('marca', '')
        index = self.marca.findText(marca)
        if index >= 0:
            self.marca.setCurrentIndex(index)
        else:
            self.marca.setEditText(marca)
            
        # Establecer categoría
        categoria = self.product_data.get('categoria', '')
        index = self.categoria.findText(categoria)
        if index >= 0:
            self.categoria.setCurrentIndex(index)
            
        # Cargar datos técnicos
        material = self.product_data.get('material', '')
        index = self.material.findText(material)
        if index >= 0:
            self.material.setCurrentIndex(index)
            
        talla = self.product_data.get('talla', '')
        index = self.talla.findText(talla)
        if index >= 0:
            self.talla.setCurrentIndex(index)
            
        tipo_lente = self.product_data.get('tipo_lente', '')
        index = self.tipo_lente.findText(tipo_lente)
        if index >= 0:
            self.tipo_lente.setCurrentIndex(index)
            
        # Cargar datos de inventario (convertir strings seguros a número antes de setValue)
        try:
            stock_val = int(float(self.product_data.get('stock', 0) or 0))
        except (ValueError, TypeError):
            stock_val = 0
        self.stock.setValue(stock_val)
        try:
            costo_val = float(self.product_data.get('costo', 0) or 0)
        except (ValueError, TypeError):
            costo_val = 0.0
        self.precio_compra.setValue(costo_val)
        try:
            venta_val = float(self.product_data.get('venta', 0) or 0)
        except (ValueError, TypeError):
            venta_val = 0.0
        self.precio_venta.setValue(venta_val)
        try:
            precio_r_val = float(self.product_data.get('precio_regular', 0) or 0)
        except (ValueError, TypeError):
            precio_r_val = 0.0
        self.precio_regular.setValue(precio_r_val)
        
        # Cargar características
        features_data = self.product_data.get('caracteristicas', {})
        for key, checkbox in self.features.items():
            checkbox.setChecked(features_data.get(key, False))
            
        # Cargar imagen si existe
        # Buscar primero en 'image_path' (nuevo), luego en 'imagen' (antiguo)
        image_path = self.product_data.get('image_path') or self.product_data.get('imagen')
        if image_path:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
                # Guardar la ruta para posible edición
                self.selected_image_path = image_path

    def save_product(self):
        # 🛡️ VERIFICAR PERMISOS antes de guardar
        parent = self.parent()
        parent_app = getattr(parent, 'parent_app', None) if parent else None
        if parent_app and parent_app.is_helper:
            if self.is_new_product:
                # CREAR
                if not parent_app.puede_hacer_accion('inventario', 'crear'):
                    QMessageBox.warning(
                        self,
                        "Permiso Denegado",
                        "No tienes permiso para crear productos."
                    )
                    return
            else:
                # EDITAR
                if not parent_app.puede_hacer_accion('inventario', 'editar'):
                    QMessageBox.warning(
                        self,
                        "Permiso Denegado",
                        "No tienes permiso para editar productos."
                    )
                    return
        
        # Validar campos requeridos
        if not self.nombre.text().strip():
            QMessageBox.warning(self, "Error", "El nombre del producto es obligatorio.")
            return
            
        if not self.codigo.text().strip():
            QMessageBox.warning(self, "Error", "El código del producto es obligatorio.")
            return

        # Recopilar datos del formulario
        # Obtener colores seleccionados
        selected_colors = [item.text() for item in self.colors_list.selectedItems()]
        
        # Si es un producto nuevo, inicializar características como desactivadas
        if self.is_new_product:
            caracteristicas = {key: False for key in self.features.keys()}
            variantes = {
                'material': False,
                'colores': False,
                'talla': False,
                'tipo_lente': False
            }
        else:
            # Si es un producto existente, usar los valores de los checkboxes
            caracteristicas = {
                key: checkbox.isChecked()
                for key, checkbox in self.features.items()
            }
            # Obtener estado de los toggles de variantes
            variantes = {
                'material': self.toggle_material.isChecked(),
                'colores': self.toggle_colors.isChecked(),
                'talla': self.toggle_size.isChecked(),
                'tipo_lente': self.toggle_lens.isChecked()
            }
        
        self.product_data = {
            'codigo': self.codigo.text().strip(),
            'nombre': self.nombre.text().strip(),
            'marca': self.marca.currentText().strip(),
            'categoria': self.categoria.currentText(),
            'material': self.material.currentText(),
            'colors': selected_colors,  # Lista de colores seleccionados
            'talla': self.talla.currentText(),
            'tipo_lente': self.tipo_lente.currentText(),
            'stock': self.stock.value(),
            'costo': self.precio_compra.value(),
            'venta': self.precio_venta.value(),
            'precio_regular': self.precio_regular.value(),
            'caracteristicas': caracteristicas,
            'variantes': variantes  # Guardar estado de variantes
        }

        # Guardar la imagen si se seleccionó una nueva
        if hasattr(self, 'selected_image_path'):
            self.product_data['image_path'] = self.selected_image_path

        self.accept()

    def get_product_data(self):
        return self.product_data
    
    def on_barcode_scanned(self, barcode: str):
        """Se ejecuta cuando se detecta un código de barras."""
        self.codigo.stop_scanning()
