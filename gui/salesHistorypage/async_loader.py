import logging

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer

from utils.file_handler import cargar_ventas, guardar_ventas

logger = logging.getLogger(__name__)


def reload_sales_async(page):
    if getattr(page, "_is_closing", False):
        return
    if not page.username:
        page._all_sales = []
        try:
            page.debug_label.setText("Usuario: <no username>")
        except Exception:
            pass
        page.empty_message.setText("No hay usuario activo.")
        page.empty_message.setVisible(True)
        page.sales_table.setVisible(False)
        page.update_sales_history_table([])
        return

    stop_sales_loader(page)

    page.empty_message.setText("Cargando ventas...")
    page.empty_message.setVisible(True)
    page.sales_table.setVisible(False)

    page._sales_load_thread = QtCore.QThread()
    from gui.main_window_pages.sales_page_parts import _orphan_qthread

    _orphan_qthread(page._sales_load_thread)
    from gui.main_window_pages.sales_page import _SalesHistoryLoaderWorker

    page._sales_load_worker = _SalesHistoryLoaderWorker(page.username)
    page._sales_load_worker.moveToThread(page._sales_load_thread)
    page._sales_load_thread.started.connect(page._sales_load_worker.run)
    page._sales_load_worker.finished.connect(lambda sales, error, source: on_sales_loaded(page, sales, error, source))
    page._sales_load_worker.finished.connect(page._sales_load_thread.quit)
    page._sales_load_worker.finished.connect(page._sales_load_worker.deleteLater)
    page._sales_load_thread.start()


def stop_sales_loader(page):
    thread = getattr(page, "_sales_load_thread", None)
    if thread is not None:
        try:
            thread.quit()
        except Exception:
            pass
    page._sales_load_thread = None
    page._sales_load_worker = None


def on_sales_loaded(page, sales, error, source_text):
    if getattr(page, "_is_closing", False):
        return
    page._all_sales = sales if isinstance(sales, list) else []

    ventas_count = len(page._all_sales)
    try:
        page.debug_label.setText(
            f"Usuario: {page.username} - ventas: {ventas_count} - fuente: {str(source_text or 'desconocido').strip()}"
        )
    except Exception:
        pass

    if error:
        try:
            logger.warning("[VENTAS] Error cargando ventas (username=%s): %s", page.username, error)
        except Exception:
            pass

    if not page._all_sales:
        page.empty_message.setText("No se encontraron ventas para el periodo seleccionado.")
        page.empty_message.setVisible(True)
        page.sales_table.setVisible(False)
        page.update_sales_history_table([])
        return

    if getattr(page, "compare_visible", False):
        try:
            from gui.salesHistorypage.compare_view import refresh_compare_panel

            page.empty_message.setVisible(False)
            if hasattr(page, "sales_table_container"):
                page.sales_table_container.setVisible(False)
            refresh_compare_panel(page, "left")
            refresh_compare_panel(page, "right")
            return
        except Exception:
            pass

    if getattr(page, "_show_all_sales_requested", False):
        page._show_all_sales_requested = False
        try:
            if hasattr(page, "payment_method_combo") and page.payment_method_combo is not None:
                page.payment_method_combo.blockSignals(True)
                try:
                    index_todos = page.payment_method_combo.findData("todos")
                    if index_todos >= 0:
                        page.payment_method_combo.setCurrentIndex(index_todos)
                finally:
                    page.payment_method_combo.blockSignals(False)
        except Exception:
            pass

        try:
            page.empty_message.setVisible(False)
            page.sales_table.setVisible(True)
        except Exception:
            pass
        page.update_sales_history_table(page._all_sales)
        return

    try:
        page.filter_by_dates()
    except Exception:
        page.empty_message.setVisible(False)
        page.sales_table.setVisible(True)
        page.update_sales_history_table(page._all_sales)
