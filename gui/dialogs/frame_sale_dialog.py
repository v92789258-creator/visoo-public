"""
Dialogo para seleccionar productos del inventario para agregar a la venta de graduacion.
"""

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QSpinBox,
    QHeaderView,
    QProgressBar,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from utils.file_handler import get_active_branch_context


class ProductLoadWorker(QThread):
    loaded = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username

    def _product_dedupe_key(self, producto):
        codigo = str(producto.get("codigo", "") or "").strip().upper()
        if codigo:
            return f"codigo:{codigo}"

        nombre = str(producto.get("nombre", "") or "").strip().upper()
        categoria = str(producto.get("categoria", "") or "").strip().upper()
        try:
            precio = float(producto.get("venta", 0) or 0)
        except (TypeError, ValueError):
            precio = 0.0
        return f"nombre:{nombre}|cat:{categoria}|precio:{precio:.2f}"

    def _dedupe_productos(self, productos):
        merged = {}
        ordered_keys = []

        for producto in productos if isinstance(productos, list) else []:
            if not isinstance(producto, dict):
                continue

            key = self._product_dedupe_key(producto)
            if key not in merged:
                merged[key] = dict(producto)
                try:
                    merged[key]["stock"] = int(producto.get("stock", 0) or 0)
                except (TypeError, ValueError):
                    merged[key]["stock"] = 0
                ordered_keys.append(key)
                continue

            current = merged[key]
            try:
                current_stock = int(current.get("stock", 0) or 0)
            except (TypeError, ValueError):
                current_stock = 0
            try:
                extra_stock = int(producto.get("stock", 0) or 0)
            except (TypeError, ValueError):
                extra_stock = 0
            current["stock"] = current_stock + extra_stock

            for field in ("nombre", "categoria", "codigo"):
                if not str(current.get(field, "") or "").strip() and str(producto.get(field, "") or "").strip():
                    current[field] = producto.get(field)

            try:
                if float(current.get("venta", 0) or 0) <= 0 and float(producto.get("venta", 0) or 0) > 0:
                    current["venta"] = producto.get("venta", 0)
            except (TypeError, ValueError):
                pass

        return [merged[key] for key in ordered_keys]

    def run(self):
        try:
            # Forzar obtención desde el servidor (phpMyAdmin/MySQL)
            # Ya no queremos cargar desde el JSON local
            productos = None
            try:
                from utils.file_handler import cargar_productos

                productos = cargar_productos(self.username, prefer_cloud=True)

            except Exception as e:
                print(f"[ERROR] No se pudo obtener productos desde phpMyAdmin: {e}")
                productos = None

            if not isinstance(productos, list):
                # Si falló la API, no cargamos desde JSON local por pedido del usuario
                # pero emitimos lista vacía para no romper el diálogo
                productos = []

            productos = self._dedupe_productos(productos)
            self.loaded.emit(list(productos or []))
        except Exception as e:
            self.error.emit(str(e))


class FrameSaleDialog(QDialog):
    """Dialogo para seleccionar productos del inventario."""

    product_selected = pyqtSignal(dict)
    selection_finalized = pyqtSignal(list)

    def __init__(self, paciente_dni, paciente_nombre, optometra, username, parent=None, preselected_items=None):
        super().__init__(parent)
        self.paciente_dni = paciente_dni
        self.paciente_nombre = paciente_nombre
        self.optometra = optometra
        self.username = username
        self.selected_product = None
        self.items_agregados = 0
        self._added_items_summary = [self._normalize_added_item(item) for item in (preselected_items or []) if isinstance(item, dict)]
        self._added_items_summary = [item for item in self._added_items_summary if item]
        self.productos_disponibles = []
        self.filtered_productos = []
        self._loading_products = False
        self._load_worker = None
        self._render_items = []
        self._render_index = 0
        self._render_batch_size = 40
        self._render_timer = QtCore.QTimer(self)
        self._render_timer.timeout.connect(self._render_next_batch)
        self._filter_timer = QtCore.QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self.apply_filter)
        self.setWindowTitle("Seleccionar Producto")
        self.setModal(True)
        self.setMinimumSize(1220, 620)
        self.setup_ui()
        self.load_products()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Seleccionar Producto para la Venta")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2a2a2a;")
        layout.addWidget(title)

        info_frame = QtWidgets.QFrame()
        info_frame.setStyleSheet(
            """
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 14px;
            }
        """
        )
        info_layout = QHBoxLayout(info_frame)
        info_layout.setSpacing(20)
        info_layout.addWidget(QLabel(f"<b>Paciente:</b> {self.paciente_nombre}"))
        info_layout.addWidget(QLabel(f"<b>DNI:</b> {self.paciente_dni}"))
        info_layout.addWidget(QLabel(f"<b>Optómetra:</b> {self.optometra}"))
        layout.addWidget(info_frame)

        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por codigo, nombre, categoria o marca...")
        self.search_input.setEnabled(False)
        self.search_input.textChanged.connect(self._schedule_apply_filter)
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #d9dee5;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:focus {
                border: 1px solid #0d6efd;
            }
        """
        )
        filters_layout.addWidget(self.search_input, 1)

        self.brand_filter_combo = QtWidgets.QComboBox()
        self.brand_filter_combo.setEnabled(False)
        self.brand_filter_combo.setMinimumWidth(180)
        self.brand_filter_combo.currentIndexChanged.connect(self._schedule_apply_filter)
        self.brand_filter_combo.setStyleSheet(
            """
            QComboBox {
                border: 1px solid #d9dee5;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 12px;
                background: white;
            }
            QComboBox:focus {
                border: 1px solid #0d6efd;
            }
            """
        )
        filters_layout.addWidget(self.brand_filter_combo)
        layout.addLayout(filters_layout)

        self.loader_label = QLabel("Preparando productos...")
        self.loader_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        layout.addWidget(self.loader_label)

        self.loader_bar = QProgressBar()
        self.loader_bar.setRange(0, 0)
        self.loader_bar.setTextVisible(False)
        self.loader_bar.setFixedHeight(10)
        self.loader_bar.setStyleSheet(
            """
            QProgressBar {
                background: #e9ecef;
                border: none;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background: #2f66e0;
                border-radius: 5px;
            }
        """
        )
        layout.addWidget(self.loader_bar)

        content_split_layout = QHBoxLayout()
        content_split_layout.setSpacing(14)

        left_column = QtWidgets.QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        tabla_label = QLabel("Selecciona un producto:")
        tabla_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 12px;")
        left_layout.addWidget(tabla_label)

        self.tabla_productos = QTableWidget()
        self.tabla_productos.setColumnCount(6)
        self.tabla_productos.setHorizontalHeaderLabels(["Nombre", "Categoría", "Precio", "Stock", "Total", "Acción"])
        self.tabla_productos.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla_productos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tabla_productos.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tabla_productos.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabla_productos.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tabla_productos.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tabla_productos.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.tabla_productos.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        self.tabla_productos.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.tabla_productos.itemSelectionChanged.connect(self.on_product_selected)
        left_layout.addWidget(self.tabla_productos, 1)
        content_split_layout.addWidget(left_column, 5)

        self.summary_frame = QtWidgets.QFrame()
        self.summary_frame.setStyleSheet(
            """
            QFrame {
                background: #f8fbff;
                border: 1px solid #d7e7ff;
                border-radius: 6px;
                padding: 10px;
            }
            """
        )
        summary_layout = QVBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(6)

        summary_title = QLabel("Resumen agregado")
        summary_title.setStyleSheet("font-weight: bold; color: #1f3b64; font-size: 12px;")
        summary_title_layout = QHBoxLayout()
        summary_title_layout.setContentsMargins(0, 0, 0, 0)
        summary_title_layout.setSpacing(8)
        summary_title_layout.addWidget(summary_title)
        summary_title_layout.addStretch()

        self.btn_limpiar_resumen = QPushButton("Limpiar")
        self.btn_limpiar_resumen.setCursor(Qt.PointingHandCursor)
        self.btn_limpiar_resumen.setFixedHeight(28)
        self.btn_limpiar_resumen.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: #667085;
                border: 1px solid #d0d5dd;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: #f8fafc; color: #344054; }
            QPushButton:pressed { background: #eef2f6; }
            """
        )
        self.btn_limpiar_resumen.clicked.connect(self._clear_added_items)
        summary_title_layout.addWidget(self.btn_limpiar_resumen)
        summary_layout.addLayout(summary_title_layout)

        summary_stats_layout = QHBoxLayout()
        summary_stats_layout.setContentsMargins(0, 0, 0, 0)
        summary_stats_layout.setSpacing(14)

        self.label_summary_items = QLabel("Productos: 0")
        self.label_summary_items.setStyleSheet("color: #0d6efd; font-weight: bold;")
        summary_stats_layout.addWidget(self.label_summary_items)

        self.label_summary_units = QLabel("Unidades: 0")
        self.label_summary_units.setStyleSheet("color: #495057; font-weight: bold;")
        summary_stats_layout.addWidget(self.label_summary_units)

        self.label_summary_amount = QLabel("Monto: S/ 0.00")
        self.label_summary_amount.setStyleSheet("color: #198754; font-weight: bold;")
        summary_stats_layout.addWidget(self.label_summary_amount)
        summary_stats_layout.addStretch()
        summary_layout.addLayout(summary_stats_layout)

        self.selected_table = QTableWidget()
        self.selected_table.setColumnCount(6)
        self.selected_table.setHorizontalHeaderLabels(["Producto", "Marca", "Cant.", "Precio", "Total", ""])
        self.selected_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.selected_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.selected_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.selected_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.selected_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.selected_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.selected_table.verticalHeader().setVisible(False)
        self.selected_table.setMinimumHeight(132)
        self.selected_table.setMaximumHeight(190)
        self.selected_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.selected_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.selected_table.setFocusPolicy(Qt.NoFocus)
        summary_layout.addWidget(self.selected_table)

        self.label_summary_detail = QLabel("Sin productos agregados aún.")
        self.label_summary_detail.setWordWrap(True)
        self.label_summary_detail.setStyleSheet("color: #6c757d; font-size: 12px;")
        summary_layout.addWidget(self.label_summary_detail)

        cantidad_frame = QtWidgets.QFrame()
        cantidad_frame.setStyleSheet(
            """
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 10px;
            }
        """
        )
        cantidad_layout = QHBoxLayout(cantidad_frame)
        cantidad_layout.setContentsMargins(0, 0, 0, 0)
        cantidad_layout.addWidget(QLabel("Cantidad:"))

        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setMinimum(1)
        self.spin_cantidad.setValue(1)
        self.spin_cantidad.setEnabled(False)
        self.spin_cantidad.valueChanged.connect(self.on_cantidad_changed)
        cantidad_layout.addWidget(self.spin_cantidad)

        cantidad_layout.addWidget(QLabel("Precio Total:"))
        self.label_total = QLabel("S/ 0.00")
        self.label_total.setStyleSheet("color: #198754; font-weight: bold; font-size: 14px;")
        cantidad_layout.addWidget(self.label_total)

        cantidad_layout.addStretch()
        self.label_items_agregados = QLabel("Agregados: 0")
        self.label_items_agregados.setStyleSheet("color: #0d6efd; font-weight: bold;")
        cantidad_layout.addWidget(self.label_items_agregados)

        right_column = QtWidgets.QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.addWidget(self.summary_frame, 1)
        right_layout.addWidget(cantidad_frame, 0)
        content_split_layout.addWidget(right_column, 2)

        layout.addLayout(content_split_layout, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setMinimumHeight(40)
        btn_cancelar.setStyleSheet(
            """
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5c636a; }
            QPushButton:pressed { background: #4c545d; }
        """
        )
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        self.btn_seleccionar = QPushButton("Agregar Producto")
        self.btn_seleccionar.setMinimumHeight(40)
        self.btn_seleccionar.setEnabled(False)
        self.btn_seleccionar.setStyleSheet(
            """
            QPushButton {
                background: #0d6efd;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #0b5ed7; }
            QPushButton:pressed { background: #0a58ca; }
            QPushButton:disabled {
                background: #a9c7fb;
                color: #eef4ff;
            }
        """
        )
        self.btn_seleccionar.clicked.connect(self.seleccionar_producto)
        btn_layout.addWidget(self.btn_seleccionar)

        self.btn_finalizar = QPushButton("Finalizar")
        self.btn_finalizar.setMinimumHeight(40)
        self.btn_finalizar.setEnabled(False)
        self.btn_finalizar.setStyleSheet(
            """
            QPushButton {
                background: #198754;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #157347; }
            QPushButton:pressed { background: #11543b; }
            QPushButton:disabled {
                background: #92c6a7;
                color: #edf7f0;
            }
        """
        )
        self.btn_finalizar.clicked.connect(self.finalizar_seleccion)
        btn_layout.addWidget(self.btn_finalizar)
        layout.addLayout(btn_layout)
        self.items_agregados = len(self._added_items_summary)
        self.label_items_agregados.setText(f"Agregados: {self.items_agregados}")
        self._refresh_selected_table()
        self._refresh_added_summary()

    def _normalize_added_item(self, item):
        if not isinstance(item, dict):
            return None
        nombre = str(item.get("nombre", item.get("producto", "")) or "").strip()
        if not nombre:
            return None
        categoria = str(item.get("categoria", "") or "").strip()
        marca = str(item.get("marca", "") or "").strip()
        codigo = str(item.get("codigo", "") or "").strip()
        try:
            cantidad = max(1, int(item.get("cantidad", 1) or 1))
        except (TypeError, ValueError):
            cantidad = 1
        try:
            precio = float(item.get("precio_unitario", item.get("precio", 0)) or 0)
        except (TypeError, ValueError):
            precio = 0.0
        try:
            stock_original = int(item.get("stock_original", item.get("stock", cantidad)) or cantidad)
        except (TypeError, ValueError):
            stock_original = cantidad
        total = round(precio * cantidad, 2)
        return {
            "nombre": nombre,
            "categoria": categoria,
            "marca": marca,
            "cantidad": cantidad,
            "precio_unitario": precio,
            "total": total,
            "codigo": codigo,
            "stock_original": max(cantidad, stock_original),
        }

    def _refresh_added_summary(self):
        items = list(self._added_items_summary)
        total_productos = len(items)
        total_unidades = 0
        total_monto = 0.0
        nombres = []

        for item in items:
            try:
                total_unidades += int(item.get("cantidad", 0) or 0)
            except (TypeError, ValueError):
                pass
            try:
                total_monto += float(item.get("total", 0) or 0)
            except (TypeError, ValueError):
                pass

            nombre = str(item.get("nombre", "") or "").strip()
            if nombre:
                nombres.append(nombre)

        self.label_summary_items.setText(f"Productos: {total_productos}")
        self.label_summary_units.setText(f"Unidades: {total_unidades}")
        self.label_summary_amount.setText(f"Monto: S/ {total_monto:.2f}")
        self.btn_limpiar_resumen.setEnabled(bool(items))

        if not nombres:
            self.label_summary_detail.setText("Sin productos agregados aún.")
            self.btn_finalizar.setEnabled(False)
            return

        visibles = nombres[-3:]
        detalle = ", ".join(visibles)
        extra = total_productos - len(visibles)
        if extra > 0:
            detalle = f"{detalle} +{extra} más"
        self.label_summary_detail.setText(f"Últimos agregados: {detalle}")
        self.btn_finalizar.setEnabled(True)

    def _set_loading_state(self, loading, message=""):
        self._loading_products = loading
        self.search_input.setEnabled(not loading and bool(self.productos_disponibles))
        self.brand_filter_combo.setEnabled(not loading and bool(self.productos_disponibles))
        self.spin_cantidad.setEnabled(not loading and self.tabla_productos.currentRow() >= 0)
        self.btn_seleccionar.setEnabled(not loading and self.tabla_productos.currentRow() >= 0)
        self.btn_finalizar.setEnabled((not loading) and bool(self._added_items_summary))
        self.loader_label.setText(message or ("Cargando productos..." if loading else ""))
        if loading:
            self.loader_bar.setRange(0, 0)

    def _render_product_row(self, row, producto):
        codigo = str(producto.get("codigo", "") or "").strip()
        nombre = str(producto.get("nombre", "Producto") or "Producto")
        nombre_mostrado = f"{codigo} - {nombre}" if codigo else nombre
        categoria = str(producto.get("categoria", "—") or "—")
        try:
            precio = float(producto.get("venta", 0) or 0)
        except (TypeError, ValueError):
            precio = 0.0
        try:
            stock = int(producto.get("stock", 0) or 0)
        except (TypeError, ValueError):
            stock = 0

        self.tabla_productos.setItem(row, 0, QTableWidgetItem(nombre_mostrado))
        self.tabla_productos.setItem(row, 1, QTableWidgetItem(categoria))
        self.tabla_productos.setItem(row, 2, QTableWidgetItem(f"S/ {precio:.2f}"))
        self.tabla_productos.setItem(row, 3, QTableWidgetItem(str(stock)))
        self.tabla_productos.setItem(row, 4, QTableWidgetItem(f"S/ {precio * self.spin_cantidad.value():.2f}"))
        if stock <= 0:
            btn_stock = QPushButton("Rellenar stock")
            btn_stock.setStyleSheet(
                "QPushButton { background: #fff7e6; color: #b26a00; border: 1px solid #f5d08a; border-radius: 4px; padding: 4px 8px; }"
                "QPushButton:hover { background: #ffefc8; }"
            )
            btn_stock.clicked.connect(lambda _checked=False, idx=row: self._open_fill_stock_dialog(idx))
            self.tabla_productos.setCellWidget(row, 5, btn_stock)
        else:
            badge = QLabel("Disponible")
            badge.setStyleSheet("color: #157347; font-size: 11px; font-weight: 600; padding: 2px 4px;")
            badge.setAlignment(Qt.AlignCenter)
            self.tabla_productos.setCellWidget(row, 5, badge)

    def _start_render_products(self, productos):
        self._render_timer.stop()
        self._render_items = list(productos or [])
        self._render_index = 0
        self.tabla_productos.clearSelection()
        self.tabla_productos.setRowCount(len(self._render_items))
        self.label_total.setText("S/ 0.00")
        self.spin_cantidad.setEnabled(False)
        self.btn_seleccionar.setEnabled(False)

        total = len(self._render_items)
        if total <= 0:
            self.loader_bar.setRange(0, 100)
            self.loader_bar.setValue(0)
            self.loader_label.setText("No hay productos que coincidan con la búsqueda.")
            self.btn_finalizar.setEnabled(bool(self._added_items_summary))
            return

        self.loader_bar.setRange(0, total)
        self.loader_bar.setValue(0)
        self.loader_label.setText(f"Preparando tabla... 0/{total}")
        self._render_timer.start(0)

    def _render_next_batch(self):
        total = len(self._render_items)
        end = min(self._render_index + self._render_batch_size, total)
        for row in range(self._render_index, end):
            self._render_product_row(row, self._render_items[row])

        self._render_index = end
        self.loader_bar.setValue(end)
        self.loader_label.setText(f"Preparando tabla... {end}/{total}")

        if end >= total:
            self._render_timer.stop()
            self.loader_label.setText(f"Productos listos: {total}")
            self.search_input.setEnabled(bool(self.productos_disponibles))
            self.brand_filter_combo.setEnabled(bool(self.productos_disponibles))
            self.btn_finalizar.setEnabled(bool(self._added_items_summary))
            if total > 0:
                self.tabla_productos.selectRow(0)
                self.on_product_selected()

    def _schedule_apply_filter(self, *_args):
        self._filter_timer.start(350)

    def apply_filter(self):
        query = self.search_input.text().strip().lower()
        selected_brand = str(self.brand_filter_combo.currentText() if hasattr(self, "brand_filter_combo") else "" or "").strip().lower()
        if not query:
            base = list(self.productos_disponibles)
        else:
            base = []
            for producto in self.productos_disponibles:
                codigo = str(producto.get("codigo", "") or "").lower()
                nombre = str(producto.get("nombre", "") or "").lower()
                categoria = str(producto.get("categoria", "") or "").lower()
                marca = str(producto.get("marca", "") or "").lower()
                if query in codigo or query in nombre or query in categoria or query in marca:
                    base.append(producto)
        if selected_brand and selected_brand != "todas las marcas":
            self.filtered_productos = [
                producto for producto in base
                if str(producto.get("marca", "") or "").strip().lower() == selected_brand
            ]
        else:
            self.filtered_productos = base
        self._start_render_products(self.filtered_productos)

    def load_products(self):
        self._set_loading_state(True, "Cargando productos desde inventario...")
        self._load_worker = ProductLoadWorker(self.username)
        self._load_worker.loaded.connect(self._on_products_loaded)
        self._load_worker.error.connect(self._on_products_error)
        self._load_worker.finished.connect(self._on_products_worker_finished)
        self._load_worker.start()

    def _on_products_loaded(self, productos):
        self.productos_disponibles = list(productos or [])
        self._populate_brand_filter()
        self.filtered_productos = list(self.productos_disponibles)
        self._set_loading_state(False, "")
        if not self.productos_disponibles:
            QMessageBox.information(self, "Sin Stock", "No hay productos disponibles en el inventario.")
            self.reject()
            return
        self._start_render_products(self.filtered_productos)

    def _on_products_error(self, error_msg):
        self._set_loading_state(False, "")
        QMessageBox.critical(self, "Error", f"Error al cargar productos: {error_msg}")
        self.reject()

    def _on_products_worker_finished(self):
        if self._load_worker is not None:
            self._load_worker.deleteLater()
            self._load_worker = None

    def on_product_selected(self):
        current_row = self.tabla_productos.currentRow()
        if current_row < 0 or current_row >= len(self.filtered_productos):
            return
        producto = self.filtered_productos[current_row]
        try:
            stock_actual = int(producto.get("stock", 0) or 0)
        except (TypeError, ValueError):
            stock_actual = 0
        codigo = str(producto.get("codigo", "") or "").strip()
        existente = self._find_added_item(codigo, str(producto.get("nombre", "") or "").strip())
        if existente is not None:
            cantidad_actual = int(existente.get("cantidad", 1) or 1)
            self.spin_cantidad.setValue(cantidad_actual)
        else:
            self.spin_cantidad.setValue(1)
        max_cantidad = max(1, stock_actual)
        self.spin_cantidad.setMaximum(max_cantidad)
        self.spin_cantidad.setEnabled(stock_actual > 0)
        self.btn_seleccionar.setEnabled((not self._loading_products) and stock_actual > 0)
        self.on_cantidad_changed()

    def on_cantidad_changed(self):
        current_row = self.tabla_productos.currentRow()
        if current_row < 0:
            self.label_total.setText("S/ 0.00")
            return

        if current_row >= len(self.filtered_productos):
            self.label_total.setText("S/ 0.00")
            return

        try:
            stock_actual = int(self.filtered_productos[current_row].get("stock", 0) or 0)
        except (TypeError, ValueError):
            stock_actual = 0
        if stock_actual <= 0:
            self.label_total.setText("S/ 0.00")
            return

        precio_item = self.tabla_productos.item(current_row, 2)
        total_item = self.tabla_productos.item(current_row, 4)
        if precio_item is None or total_item is None:
            return

        precio_str = precio_item.text().replace("S/ ", "")
        try:
            precio = float(precio_str)
        except ValueError:
            precio = 0.0
        cantidad = self.spin_cantidad.value()
        total = precio * cantidad
        self.label_total.setText(f"S/ {total:.2f}")
        total_item.setText(f"S/ {total:.2f}")

    def seleccionar_producto(self):
        current_row = self.tabla_productos.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selección", "Por favor selecciona un producto.")
            return

        try:
            if current_row >= len(self.filtered_productos):
                QMessageBox.warning(self, "Error", "Producto no encontrado.")
                return

            producto_seleccionado = self.filtered_productos[current_row]
            nombre = str(producto_seleccionado.get("nombre", "") or "").strip()
            if not nombre:
                nombre = self.tabla_productos.item(current_row, 0).text()
            categoria = self.tabla_productos.item(current_row, 1).text()
            precio_str = self.tabla_productos.item(current_row, 2).text().replace("S/ ", "")
            precio = float(precio_str)
            cantidad = self.spin_cantidad.value()
            total = precio * cantidad

            stock_actual = int(producto_seleccionado.get("stock", 0) or 0)
            if stock_actual < cantidad:
                QMessageBox.warning(
                    self,
                    "Stock Insuficiente",
                    f"Stock insuficiente. Disponible: {stock_actual}, Solicitado: {cantidad}",
                )
                return

            item_data = {
                "nombre": nombre,
                "categoria": categoria,
                "marca": str(producto_seleccionado.get("marca", "") or "").strip(),
                "cantidad": cantidad,
                "precio_unitario": precio,
                "total": total,
                "codigo": producto_seleccionado.get("codigo", ""),
                "stock_original": stock_actual,
            }

            existente = self._find_added_item(item_data.get("codigo", ""), nombre)
            if existente is not None:
                nueva_cantidad = cantidad
                if stock_actual > 0 and nueva_cantidad > stock_actual:
                    QMessageBox.warning(
                        self,
                        "Stock Insuficiente",
                        f"No puedes agregar '{nombre}' porque excede el stock disponible ({stock_actual}).",
                    )
                    return
                existente["cantidad"] = nueva_cantidad
                existente["precio_unitario"] = precio
                existente["total"] = round(nueva_cantidad * precio, 2)
                existente["stock_original"] = stock_actual
                existente["marca"] = item_data["marca"]
            else:
                self._added_items_summary.append(dict(item_data))

            self.items_agregados = len(self._added_items_summary)
            self.label_items_agregados.setText(f"Agregados: {self.items_agregados}")
            self._refresh_selected_table()
            self._refresh_added_summary()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al seleccionar producto: {str(e)}")

    def _populate_brand_filter(self):
        marcas = sorted({
            str(producto.get("marca", "") or "").strip()
            for producto in self.productos_disponibles
            if str(producto.get("marca", "") or "").strip()
        }, key=lambda x: x.lower())
        self.brand_filter_combo.blockSignals(True)
        self.brand_filter_combo.clear()
        self.brand_filter_combo.addItem("Todas las marcas")
        for marca in marcas:
            self.brand_filter_combo.addItem(marca)
        self.brand_filter_combo.blockSignals(False)

    def _find_added_item(self, codigo, nombre):
        codigo = str(codigo or "").strip()
        nombre = str(nombre or "").strip()
        for item in self._added_items_summary:
            if codigo and str(item.get("codigo", "") or "").strip() == codigo:
                return item
            if not codigo and str(item.get("nombre", "") or "").strip() == nombre:
                return item
        return None

    def _refresh_selected_table(self):
        items = list(self._added_items_summary)
        self.selected_table.setRowCount(len(items))
        for row, item in enumerate(items):
            nombre = str(item.get("nombre", "") or "").strip()
            codigo = str(item.get("codigo", "") or "").strip()
            marca = str(item.get("marca", "") or "—").strip() or "—"
            nombre_mostrado = f"{codigo} - {nombre}" if codigo else nombre
            self.selected_table.setItem(row, 0, QTableWidgetItem(nombre_mostrado))
            self.selected_table.setItem(row, 1, QTableWidgetItem(marca))

            spin_cantidad = QtWidgets.QSpinBox()
            spin_cantidad.setMinimum(1)
            spin_cantidad.setMaximum(max(1, int(item.get("stock_original", 0) or 1)))
            spin_cantidad.setValue(int(item.get("cantidad", 1) or 1))
            spin_cantidad.valueChanged.connect(lambda value, idx=row: self._on_added_qty_changed(idx, value))
            self.selected_table.setCellWidget(row, 2, spin_cantidad)

            spin_precio = QtWidgets.QDoubleSpinBox()
            spin_precio.setMinimum(0.0)
            spin_precio.setMaximum(999999.99)
            spin_precio.setDecimals(2)
            spin_precio.setValue(float(item.get("precio_unitario", 0) or 0))
            spin_precio.valueChanged.connect(lambda value, idx=row: self._on_added_price_changed(idx, value))
            self.selected_table.setCellWidget(row, 3, spin_precio)

            self.selected_table.setItem(row, 4, QTableWidgetItem(f"S/ {float(item.get('total', 0) or 0):.2f}"))

            btn_quitar = QPushButton("Quitar")
            btn_quitar.setStyleSheet(
                "QPushButton { background: #fbe9eb; color: #b42318; border: 1px solid #f5c2c7; border-radius: 4px; padding: 4px 8px; }"
                "QPushButton:hover { background: #f8d7da; }"
            )
            btn_quitar.clicked.connect(lambda _checked=False, idx=row: self._remove_added_item(idx))
            self.selected_table.setCellWidget(row, 5, btn_quitar)

    def _on_added_qty_changed(self, row, value):
        if row < 0 or row >= len(self._added_items_summary):
            return
        item = self._added_items_summary[row]
        item["cantidad"] = int(value or 1)
        item["total"] = round(float(item.get("precio_unitario", 0) or 0) * item["cantidad"], 2)
        self._refresh_selected_table()
        self._refresh_added_summary()

    def _on_added_price_changed(self, row, value):
        if row < 0 or row >= len(self._added_items_summary):
            return
        item = self._added_items_summary[row]
        item["precio_unitario"] = float(value or 0)
        item["total"] = round(item["precio_unitario"] * int(item.get("cantidad", 1) or 1), 2)
        self._refresh_selected_table()
        self._refresh_added_summary()

    def _remove_added_item(self, row):
        if row < 0 or row >= len(self._added_items_summary):
            return
        self._added_items_summary.pop(row)
        self.items_agregados = len(self._added_items_summary)
        self.label_items_agregados.setText(f"Agregados: {self.items_agregados}")
        self._refresh_selected_table()
        self._refresh_added_summary()

    def _clear_added_items(self):
        if not self._added_items_summary:
            return
        self._added_items_summary = []
        self.items_agregados = 0
        self.label_items_agregados.setText("Agregados: 0")
        self._refresh_selected_table()
        self._refresh_added_summary()
        if self.tabla_productos.currentRow() >= 0:
            self.on_product_selected()

    def _open_fill_stock_dialog(self, row):
        if row < 0 or row >= len(self.filtered_productos):
            return

        producto = self.filtered_productos[row]
        nombre = str(producto.get("nombre", "Producto") or "Producto").strip()
        try:
            stock_actual = int(producto.get("stock", 0) or 0)
        except (TypeError, ValueError):
            stock_actual = 0

        try:
            from gui.main_window_pages.sales_page import AgregarStockDialog

            dialog = AgregarStockDialog(nombre, stock_actual, 1, self)
            if dialog.exec_() != QDialog.Accepted:
                return

            unidades_agregar = int(dialog.get_unidades() or 0)
            if unidades_agregar <= 0:
                return

            producto["stock"] = stock_actual + unidades_agregar

            try:
                from utils.file_handler import cargar_productos, guardar_productos

                productos = cargar_productos(self.username, prefer_cloud=True) or []
                codigo_objetivo = str(producto.get("codigo", "") or "").strip()
                nombre_objetivo = str(producto.get("nombre", "") or "").strip()
                actualizado = False
                for prod in productos:
                    if not isinstance(prod, dict):
                        continue
                    codigo_prod = str(prod.get("codigo", "") or "").strip()
                    nombre_prod = str(prod.get("nombre", "") or "").strip()
                    if (codigo_objetivo and codigo_prod == codigo_objetivo) or (not codigo_objetivo and nombre_prod == nombre_objetivo):
                        try:
                            prod["stock"] = int(prod.get("stock", 0) or 0) + unidades_agregar
                        except (TypeError, ValueError):
                            prod["stock"] = unidades_agregar
                        actualizado = True
                        break
                if actualizado:
                    guardar_productos(self.username, productos)
            except Exception as save_err:
                QMessageBox.warning(self, "Stock", f"Se actualizó el stock en la ventana, pero no se pudo guardar: {save_err}")

            self._render_product_row(row, producto)
            if self.tabla_productos.currentRow() == row:
                self.on_product_selected()
            QMessageBox.information(self, "Stock actualizado", f"Se agregaron {unidades_agregar} unidad(es) a {nombre}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo rellenar stock: {e}")

    def finalizar_seleccion(self):
        if not self._added_items_summary:
            QMessageBox.information(self, "Sin productos", "Agrega al menos un producto antes de finalizar.")
            return
        items = [dict(item) for item in self._added_items_summary]
        self.selection_finalized.emit(items)
        for item in items:
            self.product_selected.emit(dict(item))
        self.accept()

    def closeEvent(self, event):
        try:
            self._render_timer.stop()
            if self._load_worker is not None and self._load_worker.isRunning():
                self._load_worker.quit()
                self._load_worker.wait(1500)
        except Exception:
            pass
        super().closeEvent(event)
