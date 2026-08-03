import copy

from PyQt5 import QtCore
from PyQt5.QtWidgets import QMenu, QMessageBox, QToolButton

from gui.dialogs.sale_options_dialog import SaleOptionsDialog


def create_sale_row_actions_button(page, row_index):
    button = QToolButton(page)
    button.setAutoRaise(True)
    button.setPopupMode(QToolButton.InstantPopup)
    button.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
    button.setCursor(QtCore.Qt.PointingHandCursor)
    button.setIcon(page._guia_create_kebab_icon())
    button.setIconSize(QtCore.QSize(18, 18))
    button.setStyleSheet(
        """
        QToolButton {
            border: none;
            border-radius: 6px;
            padding: 4px;
            background: transparent;
        }
        QToolButton:hover {
            background: #F3F4F6;
        }
        """
    )
    button.setProperty("sale_row_index", row_index)

    menu = QMenu(button)
    menu.setStyleSheet(
        """
        QMenu {
            background: white;
            border: 1px solid #E5E7EB;
            padding: 6px 0;
        }
        QMenu::item {
            padding: 8px 16px;
        }
        QMenu::item:selected {
            background: #F3F4F6;
        }
        """
    )
    stock_action = menu.addAction("Ver stock disponible")
    stock_action.triggered.connect(lambda _checked=False, btn=button: show_sale_row_stock(page, btn))
    menu.addSeparator()
    reset_action = menu.addAction("Restablecer precio original")
    reset_action.triggered.connect(lambda _checked=False, btn=button: reset_sale_row_original_price(page, btn))
    menu.addSeparator()
    move_up_action = menu.addAction("Mover arriba")
    move_up_action.triggered.connect(lambda _checked=False, btn=button: move_sale_row_from_button(page, btn, -1))
    move_down_action = menu.addAction("Mover abajo")
    move_down_action.triggered.connect(lambda _checked=False, btn=button: move_sale_row_from_button(page, btn, 1))
    menu.addSeparator()
    remove_action = menu.addAction("Quitar producto")
    remove_action.triggered.connect(lambda _checked=False, btn=button: remove_sale_row_from_button(page, btn))
    button.setMenu(menu)
    return button


def get_sale_row_from_button(page, button):
    if button is None:
        return -1
    try:
        index = page.venta_table.indexAt(button.pos())
        row = index.row()
    except Exception:
        row = -1
    if row < 0:
        try:
            vp = page.venta_table.viewport()
            mapped = button.mapTo(vp, QtCore.QPoint(0, 0))
            row = page.venta_table.rowAt(mapped.y())
        except Exception:
            row = -1
    return row


def remove_sale_row_from_button(page, button):
    row = get_sale_row_from_button(page, button)
    if row < 0:
        return
    page.venta_table.blockSignals(True)
    try:
        page.venta_table.removeRow(row)
    finally:
        page.venta_table.blockSignals(False)
    page.actualizar_total_venta()


def show_sale_row_stock(page, button):
    row = get_sale_row_from_button(page, button)
    if row < 0:
        return
    producto_item = page.venta_table.item(row, 0)
    producto = str(producto_item.text() if producto_item else "Producto").strip()
    stock = 0
    try:
        stock = page._parse_quantity_value(producto_item.data(QtCore.Qt.UserRole) if producto_item else 0, 0)
    except Exception:
        stock = 0
    QMessageBox.information(page, "Stock disponible", f"{producto}\n\nStock disponible: {stock}")


def reset_sale_row_original_price(page, button):
    row = get_sale_row_from_button(page, button)
    if row < 0:
        return
    precio_item = page.venta_table.item(row, 2)
    subtotal_item = page.venta_table.item(row, 3)
    descuento_item = page.venta_table.item(row, 4)
    cantidad_item = page.venta_table.item(row, 1)
    if precio_item is None or subtotal_item is None or descuento_item is None:
        return
    precio_original = page._parse_money_text(
        descuento_item.data(QtCore.Qt.UserRole),
        page._parse_money_text(precio_item.text(), 0.0),
    )
    cantidad = page._parse_quantity_value(cantidad_item.text() if cantidad_item else 1, 1)
    page.venta_table.blockSignals(True)
    try:
        precio_item.setText(f"{precio_original:.2f}")
        precio_item.setData(QtCore.Qt.UserRole, precio_original)
        subtotal_item.setText(f"{(precio_original * cantidad):.2f}")
        subtotal_item.setData(QtCore.Qt.UserRole, precio_original * cantidad)
        descuento_item.setText("0.0%")
    finally:
        page.venta_table.blockSignals(False)
    page.actualizar_total_venta()


def move_sale_row_from_button(page, button, direction):
    row = get_sale_row_from_button(page, button)
    if row < 0:
        return
    target_row = row + int(direction)
    if target_row < 0 or target_row >= page.venta_table.rowCount():
        return
    row_items = []
    for col in range(page.venta_table.columnCount()):
        item = page.venta_table.item(row, col)
        row_items.append(item.clone() if item is not None else None)

    page.venta_table.blockSignals(True)
    try:
        page.venta_table.removeCellWidget(row, 5)
        page.venta_table.removeRow(row)
        page.venta_table.insertRow(target_row)
        for col, item in enumerate(row_items):
            if item is not None:
                page.venta_table.setItem(target_row, col, item)
        page.venta_table.setCellWidget(target_row, 5, create_sale_row_actions_button(page, target_row))
    finally:
        page.venta_table.blockSignals(False)
    page.venta_table.selectRow(target_row)


def on_sales_table_cell_clicked(page, row, col):
    try:
        if int(col) != 7:
            return
    except Exception:
        return

    try:
        sale = (page.filtered_sales or [])[int(row)]
    except Exception:
        return

    if isinstance(sale, dict):
        page.eliminar_venta(sale)


def show_sale_options(page, sale):
    if getattr(page, "_is_closing", False):
        return
    if not isinstance(sale, dict):
        return
    if page._sales_fill_in_progress():
        return

    existing_dialog = getattr(page, "_sale_options_dialog", None)
    if existing_dialog is not None:
        try:
            existing_dialog.raise_()
            existing_dialog.activateWindow()
            return
        except Exception:
            page._sale_options_dialog = None

    try:
        sale_payload = copy.deepcopy(sale)
    except Exception:
        sale_payload = dict(sale)

    dialog = SaleOptionsDialog(sale_payload, page.username, parent=page)
    dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def _clear_dialog_ref(*_args):
        if getattr(page, "_sale_options_dialog", None) is dialog:
            page._sale_options_dialog = None

    try:
        dialog.finished.connect(_clear_dialog_ref)
    except Exception:
        pass

    page._sale_options_dialog = dialog
    try:
        dialog.open()
    except Exception:
        page._sale_options_dialog = None
        raise
