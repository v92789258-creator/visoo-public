from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidget


class SalesTableWidget(QTableWidget):
    """Tabla personalizada que detecta doble clic para mostrar opciones de venta."""

    def __init__(self, parent_page=None):
        super().__init__(parent_page)
        self.parent_page = parent_page

    def mouseDoubleClickEvent(self, event):
        """Maneja el evento de doble clic en la tabla."""
        sale_to_open = None
        try:
            item = self.itemAt(event.pos())
            if item and self.parent_page:
                row = self.row(item)
                col = self.column(item)
                if col != 6:
                    filtered_sales = getattr(self.parent_page, "filtered_sales", []) or []
                    is_loading = False
                    try:
                        is_loading = bool(self.parent_page._sales_fill_in_progress())
                    except Exception:
                        is_loading = False
                    if (not is_loading) and 0 <= row < len(filtered_sales):
                        candidate = filtered_sales[row]
                        if isinstance(candidate, dict):
                            sale_to_open = candidate
        except Exception:
            sale_to_open = None

        try:
            super().mouseDoubleClickEvent(event)
        except Exception:
            pass

        if sale_to_open is not None and self.parent_page:
            try:
                QtCore.QTimer.singleShot(
                    0,
                    lambda sale=sale_to_open: self.parent_page.show_sale_options(sale)
                )
            except Exception:
                pass
