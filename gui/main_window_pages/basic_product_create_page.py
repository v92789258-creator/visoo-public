import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from gui.main_window_pages.basic_mode_common import (
    BasicWindowBase,
    current_branch_code,
    load_scoped_list,
    make_button,
    safe_float,
    safe_int,
    set_button_busy,
)
from utils.file_handler import (
    agregar_producto,
    cargar_productos,
    clear_branch_runtime_caches,
    save_branch_snapshot_datasets,
)


class BasicProductCreatePage(BasicWindowBase):
    saved = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(
            parent_app=parent,
            title="Nuevo Producto",
            subtitle="Registra un producto simple sin entrar al inventario profesional.",
            loader_text="Preparando formulario",
        )
        self._saving = False
        self.all_products = []
        self._build_ui()

    def _build_ui(self):
        self.summary = QLabel("Completa los datos principales del producto.")
        self.summary.setStyleSheet(
            "font-size: 22px; font-weight: 800; color: #0F172A; "
            "background: #E8F1FF; border: 2px solid #BFD3FF; border-radius: 14px; padding: 12px 16px;"
        )
        self.content_layout.addWidget(self.summary)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.entry_codigo = QLineEdit()
        self.entry_codigo.setPlaceholderText("Codigo unico")
        self.entry_nombre = QLineEdit()
        self.entry_nombre.setPlaceholderText("Nombre del producto")
        self.entry_marca = QLineEdit()
        self.entry_marca.setPlaceholderText("Marca opcional")
        self.entry_categoria = QLineEdit("Monturas")
        self.entry_seccion = QLineEdit("Monturas")
        self.entry_stock = QLineEdit("1")
        self.entry_precio = QLineEdit()
        self.entry_precio.setPlaceholderText("Precio de venta")
        self.entry_costo = QLineEdit("0")

        form.addRow("Codigo", self.entry_codigo)
        form.addRow("Nombre", self.entry_nombre)
        form.addRow("Marca", self.entry_marca)
        form.addRow("Categoria", self.entry_categoria)
        form.addRow("Seccion", self.entry_seccion)
        form.addRow("Stock", self.entry_stock)
        form.addRow("Precio venta", self.entry_precio)
        form.addRow("Costo", self.entry_costo)
        self.content_layout.addLayout(form)

        self.content_layout.addWidget(QLabel("Observacion"))
        self.notes = QTextEdit()
        self.notes.setMinimumHeight(120)
        self.content_layout.addWidget(self.notes)

        actions = QHBoxLayout()
        self.btn_save = make_button("Guardar producto", "#1F9D55", "#157347")
        self.btn_save.clicked.connect(self._save_product)
        actions.addWidget(self.btn_save)

        btn_clear = make_button("Limpiar", "#F59E0B", "#D97706")
        btn_clear.clicked.connect(self._reset_form)
        actions.addWidget(btn_clear)

        btn_close = make_button("Cerrar", "#64748B", "#475569")
        btn_close.clicked.connect(self.exit_basic_page)
        actions.addWidget(btn_close)
        actions.addStretch()
        self.content_layout.addLayout(actions)

    def reload_data(self):
        self.load_async(
            lambda: load_scoped_list(self.parent_app, self.username, "productos.json", cargar_productos)[0],
            self._on_loaded,
            loading_text="Cargando productos",
        )

    def _on_loaded(self, products):
        self.all_products = [product for product in products if isinstance(product, dict)]
        self.summary.setText(
            f"Productos actuales: {len(self.all_products)} | La sucursal actual recibira este nuevo producto."
        )

    def _reset_form(self):
        self.entry_codigo.clear()
        self.entry_nombre.clear()
        self.entry_marca.clear()
        self.entry_categoria.setText("Monturas")
        self.entry_seccion.setText("Monturas")
        self.entry_stock.setText("1")
        self.entry_precio.clear()
        self.entry_costo.setText("0")
        self.notes.clear()

    def _set_saving(self, saving):
        self._saving = saving
        set_button_busy(self.btn_save, saving, "Guardar producto", "Guardando")
        QtWidgets.QApplication.processEvents()

    def _build_payload(self):
        code = str(self.entry_codigo.text() or "").strip()
        name = str(self.entry_nombre.text() or "").strip()
        brand = str(self.entry_marca.text() or "").strip()
        category = str(self.entry_categoria.text() or "").strip() or "General"
        section = str(self.entry_seccion.text() or "").strip() or category
        stock = safe_int(self.entry_stock.text(), 0)
        price = safe_float(self.entry_precio.text(), 0.0)
        cost = safe_float(self.entry_costo.text(), 0.0)

        if not code:
            raise ValueError("Escribe un codigo para el producto.")
        if not name:
            raise ValueError("Escribe el nombre del producto.")
        if stock < 0:
            raise ValueError("El stock no puede ser negativo.")
        if price <= 0:
            raise ValueError("El precio de venta debe ser mayor a 0.")
        if cost < 0:
            raise ValueError("El costo no puede ser negativo.")

        code_cmp = code.casefold()
        name_cmp = name.casefold()
        for product in self.all_products:
            product_code = str(product.get("codigo", "") or "").strip().casefold()
            product_name = str(product.get("nombre", "") or "").strip().casefold()
            if product_code and product_code == code_cmp:
                raise ValueError(f"Ya existe un producto con codigo {code}.")
            if product_name and product_name == name_cmp:
                raise ValueError(f"Ya existe un producto con nombre {name}.")

        branch_code = current_branch_code(self.parent_app, self.username)
        return {
            "codigo": code,
            "nombre": name,
            "marca": brand,
            "categoria": category,
            "seccion": section,
            "stock": stock,
            "costo": round(cost, 2),
            "venta": round(price, 2),
            "precio_regular": round(price, 2),
            "material": "",
            "talla": "",
            "tipo_lente": "",
            "colors": [],
            "caracteristicas": {
                "polarizado": False,
                "uv": False,
                "antireflejo": False,
                "fotocromatico": False,
                "blue_light": False,
            },
            "variantes": {
                "material": False,
                "colores": False,
                "talla": False,
                "tipo_lente": False,
            },
            "created_at": datetime.datetime.now().isoformat(),
            "observacion": str(self.notes.toPlainText() or "").strip(),
            "branch_code": branch_code,
            "codigo_dispositivo": branch_code,
        }

    def _save_product(self):
        if self._saving:
            return
        self._set_saving(True)
        try:
            payload = self._build_payload()
            if not agregar_producto(self.username, payload):
                raise ValueError("No se pudo guardar el producto. Revisa si el codigo o nombre ya existen.")

            updated_products = list(self.all_products)
            updated_products.append(payload)
            branch_code = current_branch_code(self.parent_app, self.username)
            save_branch_snapshot_datasets(self.username, branch_code, {"productos": updated_products})
            clear_branch_runtime_caches()

            self.all_products = updated_products
            self.saved.emit(payload)
            QMessageBox.information(
                self,
                "Producto",
                f"Producto guardado correctamente.\n\nCodigo: {payload['codigo']}\nNombre: {payload['nombre']}",
            )
            self._reset_form()
            self._on_loaded(self.all_products)
        except Exception as exc:
            QMessageBox.warning(self, "Producto", str(exc))
        finally:
            self._set_saving(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_data()
