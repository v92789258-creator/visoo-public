from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QTableWidget, QTableWidgetItem

from gui.main_window_pages.basic_mode_common import (
    BasicWindowBase,
    current_branch_code,
    load_scoped_list,
    make_button,
    safe_float,
    safe_int,
)
from utils.file_handler import cargar_productos


class BasicInventoryPage(BasicWindowBase):
    DISPLAY_LIMIT = 500

    def __init__(self, parent=None):
        super().__init__(
            parent_app=parent,
            title="Inventario",
            subtitle="Busca productos por nombre o codigo. Se muestran hasta 500 resultados para evitar lentitud.",
            loader_text="Cargando inventario",
        )
        self.all_products = []
        self.only_low_stock = False
        self._create_window = None
        self._build_ui()

    def _build_ui(self):
        toolbar = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Buscar producto o codigo")
        toolbar.addWidget(self.search_entry, 1)
        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self._apply_search)
        self.search_entry.textChanged.connect(lambda: self.search_timer.start())

        self.btn_low = make_button("Ver bajo stock", "#F59E0B", "#D97706")
        self.btn_low.clicked.connect(self._toggle_low_stock)
        toolbar.addWidget(self.btn_low)
        btn_new = make_button("Nuevo producto", "#1F9D55", "#157347")
        btn_new.clicked.connect(self._open_new_product)
        toolbar.addWidget(btn_new)
        btn_refresh = make_button("Recargar")
        btn_refresh.clicked.connect(self.reload_data)
        toolbar.addWidget(btn_refresh)
        btn_close = make_button("Cerrar", "#64748B", "#475569")
        btn_close.clicked.connect(self.exit_basic_page)
        toolbar.addWidget(btn_close)
        self.content_layout.addLayout(toolbar)

        self.summary = QLabel("Productos: 0")
        self.summary.setStyleSheet(
            "font-size: 22px; font-weight: 800; color: #0F172A; "
            "background: #E8F1FF; border: 2px solid #BFD3FF; border-radius: 14px; padding: 12px 16px;"
        )
        self.content_layout.addWidget(self.summary)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Codigo", "Producto", "Stock", "Precio", "Sucursal"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self.content_layout.addWidget(self.table, 1)

    def reload_data(self):
        self.load_async(
            lambda: load_scoped_list(self.parent_app, self.username, "productos.json", cargar_productos)[0],
            self._on_loaded,
            loading_text="Cargando inventario",
        )

    def _on_loaded(self, products):
        self.all_products = [product for product in products if isinstance(product, dict)]
        self._apply_search()

    def _toggle_low_stock(self):
        self.only_low_stock = not self.only_low_stock
        self.btn_low.setText("Ver todos" if self.only_low_stock else "Ver bajo stock")
        self._apply_search()

    def _open_new_product(self):
        try:
            from gui.main_window_pages.basic_product_create_page import BasicProductCreatePage

            if self.parent_app is None or not hasattr(self.parent_app, "show_basic_embedded_page"):
                raise ValueError("La ventana principal no soporta paginas basicas embebidas.")

            page = self.parent_app.show_basic_embedded_page("new_product", BasicProductCreatePage)
            if page is not None and hasattr(page, "saved"):
                try:
                    page.saved.disconnect()
                except Exception:
                    pass
                page.saved.connect(lambda _payload: self.reload_data())
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "Inventario",
                f"No se pudo abrir el formulario de producto.\n\n{exc}",
            )

    def _apply_search(self):
        query = str(self.search_entry.text() or "").strip().casefold()
        filtered = []
        for product in self.all_products:
            stock = safe_int(product.get("stock"))
            if self.only_low_stock and stock > 2:
                continue
            haystack = " ".join(
                str(product.get(key, "") or "")
                for key in ("codigo", "nombre", "marca", "categoria", "seccion")
            ).casefold()
            if query and query not in haystack:
                continue
            filtered.append(product)
            if len(filtered) >= self.DISPLAY_LIMIT:
                break
        self._render(filtered)

    def _render(self, products):
        branch_code = current_branch_code(self.parent_app, self.username)
        branch_label = str(getattr(self.parent_app, "selected_branch_label", "") or "").strip()
        branch = branch_label or branch_code or "Vista actual"
        self.table.setRowCount(0)
        for row, product in enumerate(products):
            self.table.insertRow(row)
            price = safe_float(
                product.get("venta", product.get("precio_venta", product.get("precio_regular", product.get("precio", 0))))
            )
            product_branch = str(
                product.get("branch_name", "")
                or product.get("sucursal", "")
                or product.get("branch_code", "")
                or product.get("codigo_dispositivo", "")
                or branch
            )
            values = [
                str(product.get("codigo", "") or "Sin codigo"),
                str(product.get("nombre", product.get("producto", "")) or "Sin nombre"),
                str(safe_int(product.get("stock"))),
                f"S/ {price:.2f}",
                product_branch,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter if column in (0, 2, 3) else Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row, column, item)
        suffix = " (limite visual 500)" if len(products) >= self.DISPLAY_LIMIT else ""
        self.summary.setText(f"Resultados: {len(products)} de {len(self.all_products)} productos{suffix}")

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_data()
