import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .header import build_header
from .compare_view import build_compare_view
from .payment_filter import build_payment_filter
from .table_section import build_table_section
from .toolbar import build_toolbar


def build_sales_history_page(page, parent):
    main_layout = QVBoxLayout(page)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setStyleSheet(
        """
        QScrollArea {
            border: none;
            background: #FAFAFA;
        }
        QScrollBar:vertical {
            border: none;
            background: #FAFAFA;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #CCCCCC;
            min-height: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #999999;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """
    )

    content_widget = QWidget()
    content_widget.setStyleSheet("background: #FAFAFA;")
    content_layout = QVBoxLayout(content_widget)
    content_layout.setContentsMargins(24, 24, 24, 24)
    content_layout.setSpacing(20)

    content_layout.addWidget(build_header(page))
    icon_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    build_toolbar(page, content_layout, icon_base_dir)
    page.payment_filter_container = build_payment_filter(page)
    content_layout.addWidget(page.payment_filter_container)
    page.sales_table_container = build_table_section(page)
    content_layout.addWidget(page.sales_table_container)
    page.compare_view_container = build_compare_view(page)
    content_layout.addWidget(page.compare_view_container)

    puede_ver_ventas = True
    if hasattr(parent, "is_helper") and parent.is_helper:
        from utils.helpers_manager import tiene_accion_permitida

        username_jefe = parent.username
        username_ayudante = parent.helper_name
        puede_ver_ventas = tiene_accion_permitida(username_jefe, username_ayudante, "ventas", "ver")

    if not puede_ver_ventas:
        page.empty_message.setText("No tienes permiso para ver el historial de ventas")
        page.empty_message.setVisible(True)
        page.sales_table.setVisible(False)
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        return

    page.empty_message.setText("Cargando ventas...")
    page.empty_message.setVisible(True)
    page.sales_table.setVisible(False)

    scroll_area.setWidget(content_widget)
    main_layout.addWidget(scroll_area)
    QTimer.singleShot(0, page._reload_sales)
