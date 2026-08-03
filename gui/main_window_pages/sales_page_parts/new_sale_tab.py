from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from gui.main_window_pages.sales_page_parts.new_sale_tab_form import build_new_sale_form
from gui.main_window_pages.sales_page_parts.new_sale_tab_summary import build_new_sale_summary
from gui.main_window_pages.sales_page_parts.new_sale_tab_table import build_new_sale_table


def build_new_sale_tab(page):
    tab = QWidget()
    tab_layout = QVBoxLayout(tab)
    tab_layout.setContentsMargins(0, 0, 0, 0)
    tab_layout.setSpacing(0)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setStyleSheet("""
        QScrollArea {
            border: none;
            background: white;
        }
        QScrollBar:vertical {
            border: none;
            background: #F5F5F5;
            width: 10px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #CCCCCC;
            border-radius: 5px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #999999;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
    """)

    content_widget = QWidget()
    page.sales_new_content_widget = content_widget
    layout = QVBoxLayout(content_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)

    header = QWidget()
    header.setStyleSheet("background: white;")
    header_layout = QVBoxLayout(header)
    header_layout.setContentsMargins(20, 16, 20, 16)
    title = QLabel("Registro de Nueva Venta")
    title.setStyleSheet("font-size: 18px; color: #333333; font-weight: 600;")
    subtitle = QLabel("Complete los datos de la venta")
    subtitle.setStyleSheet("font-size: 12px; color: #999999; margin-top:4px; font-weight: 400;")
    header_layout.addWidget(title)
    header_layout.addWidget(subtitle)
    layout.addWidget(header)

    separator = QWidget()
    separator.setStyleSheet("background: #EEEEEE;")
    separator.setFixedHeight(1)
    layout.addWidget(separator)

    main_container = QWidget()
    main_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
    main_container.setStyleSheet("""
        QWidget {
            background: white;
            border: none;
            padding: 0px;
        }
        QGroupBox {
            background: white;
            border: 1px solid #DDDDDD;
            border-radius: 0px;
            padding: 14px;
            margin: 0px;
            margin-top: 0px;
        }
        QGroupBox::title {
            color: #333333;
            font-weight: 600;
            padding: 0px 4px;
            background: white;
            margin-left: 0px;
            font-size: 12px;
        }
        QLineEdit, QComboBox {
            padding: 8px 10px;
            border: 1px solid #CCCCCC;
            border-radius: 0px;
            min-height: 22px;
            background: white;
            color: #333333;
            font-size: 11px;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #666666;
            background: white;
        }
        QPushButton {
            padding: 8px 12px;
            border: 1px solid #CCCCCC;
            border-radius: 0px;
            color: #333333;
            background: #F8F8F8;
            min-height: 28px;
            font-weight: 500;
            font-size: 11px;
        }
        QPushButton:hover {
            background: #F0F0F0;
            border: 1px solid #999999;
        }
        QPushButton:pressed {
            background: #EBEBEB;
        }
    """)
    main_layout = QVBoxLayout(main_container)
    main_layout.addWidget(build_new_sale_form(page))
    layout.addWidget(main_container)
    layout.addWidget(build_new_sale_table(page))
    layout.addWidget(build_new_sale_summary(page))
    layout.addStretch()

    page.sales_new_scroll_area = scroll_area
    scroll_area.setWidget(content_widget)
    tab_layout.addWidget(scroll_area)
    return tab
