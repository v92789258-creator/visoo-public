"""
Selector de productos para nueva venta.
Diseno cercano al selector usado en graduaciones, manteniendo el mismo contrato de salida.
"""

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt


class ProductLoadWorker(QtCore.QThread):
    loaded = QtCore.pyqtSignal(list, bool) # lista de productos, tiene_mas
    failed = QtCore.pyqtSignal(str)

    def __init__(self, username="", parent=None, limit=None, offset=None):
        super().__init__(parent)
        self.username = str(username or "").strip()
        self.limit = limit
        self.offset = offset

    def run(self):
        try:
            from utils.file_handler import cargar_productos

            # Cargar productos con los parametros de paginacion
            productos = cargar_productos(self.username, prefer_cloud=True, limit=self.limit, offset=self.offset)
            if not isinstance(productos, list):
                productos = []
            
            # Si pedimos un limite y nos devolvieron esa cantidad, asumimos que hay mas
            has_more = bool(self.limit and len(productos) >= self.limit)
            
            self.loaded.emit(list(productos), has_more)
        except Exception as e:
            self.failed.emit(str(e))


class SeleccionarProductosDialogV2(QtWidgets.QDialog):
    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.username = username
        self.selected_products = []
        self.productos = []
        self.filtered_productos = []
        self.visible_productos = []
        self._max_visible_products = 300
        self._loader_started = False
        self._load_worker = None
        self._render_index = 0
        self._render_chunk_size = 24
        self._filter_timer = QtCore.QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self.apply_filter)
        
        # Paginacion de API
        self.current_offset = 0
        self.page_size = 30
        self.has_more_remoto = True
        self.loading_more = False

        self.setWindowTitle("Seleccionar Productos")
        self.setModal(True)
        self.setMinimumSize(1180, 680)

        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Seleccionar Productos")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f2937;")
        layout.addWidget(title)

        filters_layout = QtWidgets.QHBoxLayout()
        filters_layout.setSpacing(10)
        filters_layout.addWidget(QtWidgets.QLabel("Buscar:"))

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Cargando productos...")
        self.search_input.setEnabled(False)
        self.search_input.textChanged.connect(self._schedule_apply_filter)
        filters_layout.addWidget(self.search_input, 1)

        self.brand_filter = QtWidgets.QComboBox()
        self.brand_filter.setEnabled(False)
        self.brand_filter.setMinimumWidth(190)
        self.brand_filter.currentIndexChanged.connect(self._schedule_apply_filter)
        filters_layout.addWidget(self.brand_filter)
        layout.addLayout(filters_layout)

        self.content_stack = QtWidgets.QStackedWidget()
        self.loader_page = self._build_loader_page()
        self.table_page = self._build_table_page()
        self.content_stack.addWidget(self.loader_page)
        self.content_stack.addWidget(self.table_page)
        self.content_stack.setCurrentWidget(self.loader_page)
        layout.addWidget(self.content_stack, 1)

        buttons_layout = QtWidgets.QHBoxLayout()
        
        self.load_more_btn = QtWidgets.QPushButton("Cargar más productos...")
        self.load_more_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #2563eb;
                font-weight: bold;
                padding: 6px 15px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #e5e7eb; }
            QPushButton:disabled { color: #9ca3af; border: 1px solid #e5e7eb; }
        """)
        self.load_more_btn.setVisible(False)
        self.load_more_btn.clicked.connect(self.load_next_page)
        buttons_layout.addWidget(self.load_more_btn)
        
        buttons_layout.addStretch()

        self.btn_clear = QtWidgets.QPushButton("Limpiar")
        self.btn_clear.clicked.connect(self.clear_selected_products)
        buttons_layout.addWidget(self.btn_clear)

        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        self.btn_ok = QtWidgets.QPushButton("Aceptar")
        self.btn_ok.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold; padding: 8px 20px;")
        self.btn_ok.clicked.connect(self.accept)
        buttons_layout.addWidget(self.btn_ok)
        layout.addLayout(buttons_layout)

        self._refresh_summary()

    def _build_loader_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        card = QtWidgets.QFrame()
        card.setFixedWidth(360)
        card.setStyleSheet(
            """
            QFrame { background: white; border: 1px solid #E5E7EB; border-radius: 14px; }
            QLabel#LoaderTitle { font-size: 15px; font-weight: 700; color: #111827; }
            QLabel#LoaderSubtitle { font-size: 11px; color: #6B7280; }
            QProgressBar { border: none; border-radius: 5px; background: #E5E7EB; height: 10px; }
            QProgressBar::chunk { border-radius: 5px; background: #2563EB; }
            """
        )

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(10)

        self.loader_title = QtWidgets.QLabel("Cargando productos")
        self.loader_title.setObjectName("LoaderTitle")
        self.loader_title.setAlignment(Qt.AlignCenter)

        self.loader_bar = QtWidgets.QProgressBar()
        self.loader_bar.setRange(0, 0)
        self.loader_bar.setTextVisible(False)

        self.loader_subtitle = QtWidgets.QLabel("Leyendo inventario y preparando la tabla...")
        self.loader_subtitle.setObjectName("LoaderSubtitle")
        self.loader_subtitle.setAlignment(Qt.AlignCenter)
        self.loader_subtitle.setWordWrap(True)

        card_layout.addWidget(self.loader_title)
        card_layout.addWidget(self.loader_bar)
        card_layout.addWidget(self.loader_subtitle)
        layout.addWidget(card, alignment=Qt.AlignCenter)
        return page

    def _build_table_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.inline_loader_widget = QtWidgets.QWidget()
        inline_loader_layout = QtWidgets.QHBoxLayout(self.inline_loader_widget)
        inline_loader_layout.setContentsMargins(0, 0, 0, 0)
        inline_loader_layout.setSpacing(10)

        self.inline_loader_label = QtWidgets.QLabel("Preparando tabla...")
        self.inline_loader_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        inline_loader_layout.addWidget(self.inline_loader_label)

        self.inline_loader_bar = QtWidgets.QProgressBar()
        self.inline_loader_bar.setTextVisible(False)
        self.inline_loader_bar.setFixedHeight(8)
        self.inline_loader_bar.setRange(0, 100)
        self.inline_loader_bar.setValue(0)
        self.inline_loader_bar.setStyleSheet(
            """
            QProgressBar { border: none; border-radius: 4px; background: #E5E7EB; }
            QProgressBar::chunk { border-radius: 4px; background: #2563EB; }
            """
        )
        inline_loader_layout.addWidget(self.inline_loader_bar, 1)
        self.inline_loader_widget.setVisible(False)
        left_layout.addWidget(self.inline_loader_widget)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Nombre", "Marca", "Stock", "Precio", "Cantidad", "Accion"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        self.table.setColumnWidth(3, 110) # Precio
        left_layout.addWidget(self.table, 1)

        right_panel = QtWidgets.QFrame()
        right_panel.setStyleSheet("QFrame { background: #f8fbff; border: 1px solid #d7e7ff; border-radius: 6px; }")
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        summary_title = QtWidgets.QLabel("Resumen agregado")
        summary_title.setStyleSheet("font-weight: 700; color: #1f3b64; font-size: 12px;")
        right_layout.addWidget(summary_title)

        stats_layout = QtWidgets.QHBoxLayout()
        self.summary_products_label = QtWidgets.QLabel("Productos: 0")
        self.summary_units_label = QtWidgets.QLabel("Unidades: 0")
        self.summary_amount_label = QtWidgets.QLabel("Monto: S/. 0.00")
        self.summary_products_label.setStyleSheet("color: #0d6efd; font-weight: 600;")
        self.summary_units_label.setStyleSheet("color: #475467; font-weight: 600;")
        self.summary_amount_label.setStyleSheet("color: #198754; font-weight: 700;")
        stats_layout.addWidget(self.summary_products_label)
        stats_layout.addWidget(self.summary_units_label)
        stats_layout.addWidget(self.summary_amount_label)
        stats_layout.addStretch()
        right_layout.addLayout(stats_layout)

        self.selected_table = QtWidgets.QTableWidget()
        self.selected_table.setColumnCount(5)
        self.selected_table.setHorizontalHeaderLabels(["Nombre", "Cantidad", "Precio Unit.", "Subtotal", "Quitar"])
        self.selected_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.selected_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.selected_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.selected_table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.selected_table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.selected_table.setColumnWidth(2, 100) # Precio unitario
        self.selected_table.setColumnWidth(3, 110) # Subtotal
        self.selected_table.verticalHeader().setVisible(False)
        self.selected_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.selected_table.setFocusPolicy(Qt.NoFocus)
        self.selected_table.setMinimumHeight(420)
        right_layout.addWidget(self.selected_table, 1)

        self.selected_hint = QtWidgets.QLabel("Sin productos agregados aun.")
        self.selected_hint.setStyleSheet("color: #667085; font-size: 12px;")
        right_layout.addWidget(self.selected_hint)

        layout.addWidget(left_panel, 5)
        layout.addWidget(right_panel, 2)
        return page

    def showEvent(self, event):
        super().showEvent(event)
        if not self._loader_started:
            self._loader_started = True
            QtCore.QTimer.singleShot(0, self.start_loading_products)

    def closeEvent(self, event):
        try:
            if self._load_worker is not None and self._load_worker.isRunning():
                self._load_worker.quit()
                self._load_worker.wait(300)
        except Exception:
            pass
        super().closeEvent(event)

    def start_loading_products(self):
        self.search_input.setEnabled(False)
        self.brand_filter.setEnabled(False)
        self.search_input.setPlaceholderText("Cargando productos...")
        self.content_stack.setCurrentWidget(self.loader_page)
        self.loader_title.setText("Cargando productos")
        self.loader_subtitle.setText("Leyendo inventario y preparando la tabla...")

        # Cargar primera pagina (30)
        self._load_worker = ProductLoadWorker(username=self.username, parent=self, limit=self.page_size, offset=0)
        self._load_worker.loaded.connect(self.on_products_loaded)
        self._load_worker.failed.connect(self.on_products_failed)
        self._load_worker.start()

    def load_next_page(self):
        if self.loading_more or not self.has_more_remoto:
            return
            
        self.loading_more = True
        self.load_more_btn.setEnabled(False)
        self.load_more_btn.setText("Cargando...")
        
        self.current_offset += self.page_size
        worker = ProductLoadWorker(username=self.username, parent=self, limit=self.page_size, offset=self.current_offset)
        worker.loaded.connect(self.on_more_products_loaded)
        worker.failed.connect(self.on_products_failed)
        worker.start()
        # Evitar garbage collection
        self._last_worker = worker

    def on_products_loaded(self, productos, has_more):
        self.productos = list(productos or [])
        self.has_more_remoto = has_more
        self.loading_more = False
        
        self.populate_brand_filter()
        self.loader_title.setText("Preparando lista")
        self.loader_subtitle.setText(f"Se encontraron {len(self.productos)} productos. Armando tabla...")
        
        # Resetear filtros para ver lo cargado
        self.brand_filter.setCurrentIndex(0)
        self.search_input.clear()
        
        self.apply_filter()
        self._update_load_more_visibility()

    def on_more_products_loaded(self, productos, has_more):
        if productos:
            existing_ids = {str(p.get('id', '')) for p in self.productos}
            for p in productos:
                pid = str(p.get('id', ''))
                if pid not in existing_ids:
                    self.productos.append(p)
                    existing_ids.add(pid)
                    
        self.has_more_remoto = has_more
        self.loading_more = False
        
        self.populate_brand_filter()
        self.apply_filter()
        self._update_load_more_visibility()

    def _update_load_more_visibility(self):
        self.load_more_btn.setVisible(self.has_more_remoto)
        self.load_more_btn.setEnabled(True)
        self.load_more_btn.setText(f"Cargar más (Página { (self.current_offset // self.page_size) + 2 })")

    def on_products_failed(self, error_msg):
        self.productos = []
        self.filtered_productos = []
        self.search_input.setEnabled(True)
        self.brand_filter.setEnabled(False)
        self.search_input.setPlaceholderText("Buscar por nombre, marca...")
        self.loader_title.setText("No se pudieron cargar los productos")
        self.loader_subtitle.setText(str(error_msg or "Error desconocido"))
        QtWidgets.QMessageBox.critical(self, "Error", f"Error cargando productos: {error_msg}")

    def populate_brand_filter(self):
        current_brand = self.brand_filter.currentText()
        marcas = sorted(
            {
                str(prod.get("marca", "") or "").strip()
                for prod in self.productos
                if str(prod.get("marca", "") or "").strip()
            },
            key=lambda x: x.lower(),
        )
        self.brand_filter.blockSignals(True)
        self.brand_filter.clear()
        self.brand_filter.addItem("Todas las marcas")
        for marca in marcas:
            self.brand_filter.addItem(marca)
        
        # Intentar mantener la marca seleccionada si existía
        idx = self.brand_filter.findText(current_brand)
        if idx >= 0:
            self.brand_filter.setCurrentIndex(idx)
        self.brand_filter.blockSignals(False)

    def _schedule_apply_filter(self, *_args):
        self._filter_timer.start(350)

    def apply_filter(self, *_args):
        query = str(self.search_input.text() or "").strip().lower()
        selected_brand = str(self.brand_filter.currentText() or "").strip().lower()
        filtered = []
        for prod in self.productos:
            nombre = str(prod.get("nombre", "") or "").lower()
            marca = str(prod.get("marca", "") or "").lower()
            codigo = str(prod.get("codigo", "") or "").lower()
            categoria = str(prod.get("categoria", "") or "").lower()
            if query and query not in nombre and query not in marca and query not in codigo and query not in categoria:
                continue
            if selected_brand and selected_brand != "todas las marcas" and marca != selected_brand:
                continue
            filtered.append(prod)
        self.filtered_productos = filtered
        self._start_incremental_render()

    def _start_incremental_render(self):
        # Limpiar tabla para re-dibujar según filtros
        self.table.setRowCount(0)
        self._render_index = 0
        
        # Sincronizar visualización (máximo 300 para no laguear scroll)
        self._max_visible_products = max(300, len(self.productos))
        self.visible_productos = list(self.filtered_productos[: self._max_visible_products])
        
        self.content_stack.setCurrentWidget(self.table_page)
        # ✅ FIX: Mantener habilitado el input para que el usuario no deje de escribir
        self.search_input.setEnabled(True)
        self.brand_filter.setEnabled(True)
        
        self.inline_loader_widget.setVisible(True)
        total_visibles = len(self.visible_productos)
        self.inline_loader_label.setText(f"Mostrando {total_visibles} resultados...")
        self.inline_loader_bar.setValue(0)
        
        # Detener renderizado previo si estaba en curso
        if hasattr(self, "_render_timer") and self._render_timer.isActive():
            self._render_timer.stop()
            
        QtCore.QTimer.singleShot(0, self._render_next_chunk)

    def _render_next_chunk(self):
        total = len(self.visible_productos)
        if self._render_index >= total:
            # Finalizado
            if total > 0:
                self.inline_loader_bar.setValue(100)
                self.inline_loader_label.setText(f"Lista lista ({total} productos)")
                QtCore.QTimer.singleShot(800, lambda: self.inline_loader_widget.setVisible(False))
            else:
                self.inline_loader_widget.setVisible(False)
            return

        end = min(self._render_index + self._render_chunk_size, total)
        for row in range(self._render_index, end):
            prod = self.visible_productos[row]
            target_row = self.table.rowCount()
            self.table.insertRow(target_row)
            self._populate_row(target_row, prod)

        self._render_index = end
        if total > 0:
            progress = int((self._render_index / total) * 100)
            self.inline_loader_bar.setValue(progress)
            self.inline_loader_label.setText(f"Preparando tabla... {self._render_index}/{total}")

        # ✅ Renderizado asíncrono real: un timer de 2ms deja procesar teclas entre chunks
        if not hasattr(self, "_render_timer"):
            self._render_timer = QtCore.QTimer(self)
            self._render_timer.setSingleShot(True)
            self._render_timer.timeout.connect(self._render_next_chunk)
        
        self._render_timer.start(2)

    def start_loading_products(self):
        self.search_input.setEnabled(False)
        self.brand_filter.setEnabled(False)
        self.search_input.setPlaceholderText("Cargando productos...")
        self.content_stack.setCurrentWidget(self.loader_page)
        self.loader_title.setText("Cargando productos")
        self.loader_subtitle.setText("Leyendo inventario y preparando la tabla...")

        # Cargar primera pagina (30) para velocidad
        self._load_worker = ProductLoadWorker(username=self.username, parent=self, limit=self.page_size, offset=0)
        self._load_worker.loaded.connect(self.on_products_loaded)
        self._load_worker.failed.connect(self.on_products_failed)
        self._load_worker.start()

    def on_products_loaded(self, productos, has_more):
        self.productos = list(productos or [])
        self.has_more_remoto = has_more
        self.loading_more = False
        
        self.populate_brand_filter()
        self.loader_title.setText("Preparando lista")
        self.loader_subtitle.setText(f"Se encontraron {len(self.productos)} productos. Armando tabla...")
        
        # Resetear filtros para ver lo cargado de inicio
        self.brand_filter.blockSignals(True)
        self.brand_filter.setCurrentIndex(0)
        self.brand_filter.blockSignals(False)
        self.search_input.clear()
        
        self.apply_filter()
        self._update_load_more_visibility()
        
        # ✅ BUSQUEDA GLOBAL: Si hay más, cargarlos silenciosamente en segundo plano
        if has_more:
            QtCore.QTimer.singleShot(2000, self._start_background_full_load)

    def _start_background_full_load(self):
        """Descarga el resto del inventario sin bloquear nada para permitir búsqueda global."""
        # Usamos un limite alto pero razonable para el buscador local
        self._bg_worker = ProductLoadWorker(username=self.username, parent=self, limit=5000, offset=self.page_size)
        self._bg_worker.loaded.connect(self.on_background_products_loaded)
        self._bg_worker.start()

    def on_background_products_loaded(self, productos, _has_more):
        if productos:
            existing_ids = {str(p.get('id', '')) for p in self.productos}
            for p in productos:
                if str(p.get('id', '')) not in existing_ids:
                    self.productos.append(p)
            
            self.populate_brand_filter()
            # No aplicamos filtro aquí para no interrumpir al usuario, pero la próxima tecla buscará en TODO.
            print(f"[SELECTOR] Búsqueda global activa: {len(self.productos)} productos cargados.")
        
        self.has_more_remoto = False
        self._update_load_more_visibility()
        self._refresh_summary()

    def _populate_row(self, row, prod):
        codigo = str(prod.get("codigo", "") or "").strip()
        nombre = str(prod.get("nombre", "Producto") or "Producto").strip()
        nombre_mostrado = f"{codigo} - {nombre}" if codigo else nombre
        marca = str(prod.get("marca", "") or "N/A")
        try:
            stock = int(float(prod.get("stock", 0) or 0))
        except (TypeError, ValueError):
            stock = 0
        try:
            precio = float(prod.get("venta", 0) or 0)
        except (TypeError, ValueError):
            precio = 0.0

        self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(nombre_mostrado))
        self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(marca))
        self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(stock)))
        
        precio_item = QtWidgets.QTableWidgetItem(f"S/. {precio:.2f}")
        precio_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.table.setItem(row, 3, precio_item)

        spinbox = QtWidgets.QSpinBox()
        spinbox.setMinimum(1)
        spinbox.setMaximum(max(1, stock))
        spinbox.setValue(1)
        spinbox.setEnabled(stock > 0)
        spinbox.setProperty("product_index", row)
        self.table.setCellWidget(row, 4, spinbox)

        btn = QtWidgets.QPushButton("Añadir" if stock > 0 else "Sin stock")
        btn.setEnabled(stock > 0)
        btn.setProperty("product_index", row)
        btn.clicked.connect(self.on_add_clicked)
        self.table.setCellWidget(row, 5, btn)

    def on_add_clicked(self):
        sender = self.sender()
        if not sender:
            return
        product_index = sender.property("product_index")
        if product_index is None or product_index < 0 or product_index >= len(self.visible_productos):
            return

        prod = self.visible_productos[product_index]
        spinbox = self.table.cellWidget(product_index, 4)
        if not spinbox:
            return

        cantidad = int(spinbox.value() or 0)
        if cantidad <= 0:
            return

        codigo = str(prod.get("codigo", "") or "").strip()
        nombre = str(prod.get("nombre", "") or "").strip() or "Producto"
        try:
            precio = float(prod.get("venta", 0) or 0)
        except (TypeError, ValueError):
            precio = 0.0
        try:
            stock_disponible = int(float(prod.get("stock", 0) or 0))
        except (TypeError, ValueError):
            stock_disponible = 0

        existing = None
        for item in self.selected_products:
            if str(item.get("codigo", "") or "").strip() == codigo:
                existing = item
                break

        if existing is not None:
            nueva_cantidad = int(existing.get("cantidad", 0) or 0) + cantidad
            if nueva_cantidad > stock_disponible:
                QtWidgets.QMessageBox.warning(self, "Stock insuficiente", f"No puedes exceder el stock disponible ({stock_disponible}).")
                return
            existing["cantidad"] = nueva_cantidad
            existing["subtotal"] = round(nueva_cantidad * precio, 2)
            existing["stock_disponible"] = stock_disponible
        else:
            self.selected_products.append(
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "cantidad": cantidad,
                    "precio_unitario": precio,
                    "subtotal": round(precio * cantidad, 2),
                    "stock_disponible": stock_disponible,
                }
            )

        self.refresh_selected_table()

    def refresh_selected_table(self):
        self.selected_table.setRowCount(len(self.selected_products))
        for row, item in enumerate(self.selected_products):
            codigo = str(item.get("codigo", "") or "").strip()
            nombre = str(item.get("nombre", "") or "").strip()
            nombre_mostrado = f"{codigo} - {nombre}" if codigo else nombre
            self.selected_table.setItem(row, 0, QtWidgets.QTableWidgetItem(nombre_mostrado))

            spin_qty = QtWidgets.QSpinBox()
            spin_qty.setMinimum(1)
            spin_qty.setMaximum(max(1, int(item.get("stock_disponible", 1) or 1)))
            spin_qty.setValue(int(item.get("cantidad", 1) or 1))
            spin_qty.valueChanged.connect(lambda value, idx=row: self.on_selected_qty_changed(idx, value))
            self.selected_table.setCellWidget(row, 1, spin_qty)

            spin_price = QtWidgets.QDoubleSpinBox()
            spin_price.setMinimum(0.0)
            spin_price.setMaximum(999999.99)
            spin_price.setDecimals(2)
            spin_price.setValue(float(item.get("precio_unitario", 0) or 0))
            spin_price.valueChanged.connect(lambda value, idx=row: self.on_selected_price_changed(idx, value))
            self.selected_table.setCellWidget(row, 2, spin_price)

            sub_item = QtWidgets.QTableWidgetItem(f"S/. {float(item.get('subtotal', 0) or 0):.2f}")
            sub_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.selected_table.setItem(row, 3, sub_item)

            btn_quitar = QtWidgets.QPushButton("Quitar")
            btn_quitar.setProperty("row_index", row)
            btn_quitar.clicked.connect(self.on_remove_clicked)
            btn_quitar.setStyleSheet("background-color: #dc3545; color: white;")
            self.selected_table.setCellWidget(row, 4, btn_quitar)

        self._refresh_summary()

    def on_selected_qty_changed(self, row, value):
        if row < 0 or row >= len(self.selected_products):
            return
        item = self.selected_products[row]
        item["cantidad"] = int(value or 1)
        subtotal = round(float(item.get("precio_unitario", 0) or 0) * item["cantidad"], 2)
        item["subtotal"] = subtotal
        
        # ✅ SURGICAL UPDATE: Solo actualizar la celda de subtotal
        self.selected_table.blockSignals(True)
        sub_item = QtWidgets.QTableWidgetItem(f"S/. {subtotal:.2f}")
        sub_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.selected_table.setItem(row, 3, sub_item)
        self.selected_table.blockSignals(False)
        
        self._refresh_summary()

    def on_selected_price_changed(self, row, value):
        if row < 0 or row >= len(self.selected_products):
            return
        item = self.selected_products[row]
        item["precio_unitario"] = float(value or 0.0)
        subtotal = round(item["precio_unitario"] * int(item.get("cantidad", 1) or 1), 2)
        item["subtotal"] = subtotal
        
        # ✅ SURGICAL UPDATE: Solo actualizar la celda de subtotal
        self.selected_table.blockSignals(True)
        sub_item = QtWidgets.QTableWidgetItem(f"S/. {subtotal:.2f}")
        sub_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.selected_table.setItem(row, 3, sub_item)
        self.selected_table.blockSignals(False)
        
        self._refresh_summary()

    def on_remove_clicked(self):
        sender = self.sender()
        if not sender:
            return
        row_index = sender.property("row_index")
        if row_index is None or row_index < 0 or row_index >= len(self.selected_products):
            return
        self.selected_products.pop(row_index)
        self.refresh_selected_table()

    def clear_selected_products(self):
        self.selected_products = []
        self.refresh_selected_table()

    def _refresh_summary(self):
        total_productos = len(self.selected_products)
        total_unidades = 0
        total_monto = 0.0
        for item in self.selected_products:
            try:
                total_unidades += int(item.get("cantidad", 0) or 0)
            except Exception:
                pass
            try:
                total_monto += float(item.get("subtotal", 0) or 0)
            except Exception:
                pass

        self.summary_products_label.setText(f"Productos: {total_productos}")
        self.summary_units_label.setText(f"Unidades: {total_unidades}")
        self.summary_amount_label.setText(f"Monto: S/. {total_monto:.2f}")
        self.selected_hint.setText(
            "Sin productos agregados aun." if not self.selected_products else "Puedes ajustar cantidad, precio o quitar productos."
        )
        self.btn_clear.setEnabled(bool(self.selected_products))
        self.btn_ok.setEnabled(bool(self.selected_products))
