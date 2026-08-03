from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


def build_new_sale_table(page):
    table_container = QWidget()
    table_container.setMinimumHeight(320)
    table_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)
    table_container.setStyleSheet("""
        QWidget {
            background: white;
            border: 1px solid #DDDDDD;
            padding: 0px;
        }
        QTableWidget {
            background-color: white;
            border: none;
            gridline-color: #F5F5F5;
            border-radius: 0px;
        }
        QTableWidget::item {
            padding: 8px 10px;
            border: none;
            border-bottom: 1px solid #f0f0f0;
        }
        QTableWidget::item:selected {
            background-color: #f5f5f5;
            color: #1a1a1a;
        }
        QHeaderView::section {
            background: #fafafa;
            padding: 8px 10px;
            border: none;
            border-bottom: 1px solid #d0d0d0;
            font-weight: 600;
            color: #1a1a1a;
            font-size: 12px;
        }
        QTableWidget::item:hover {
            background-color: #fbfbfb;
        }
        QScrollBar:vertical {
            border: none;
            background: white;
            width: 8px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #bbb;
            min-height: 30px;
            border-radius: 0px;
        }
        QScrollBar::handle:vertical:hover {
            background: #888;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """)
    table_layout = QVBoxLayout(table_container)
    table_layout.setContentsMargins(0, 0, 0, 0)

    page.venta_table = QTableWidget()
    page.venta_table.setColumnCount(6)
    page.venta_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio Unitario", "Subtotal", "Descuento %", ""])
    page.venta_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    page.venta_table.setEditTriggers(
        QtWidgets.QAbstractItemView.DoubleClicked |
        QtWidgets.QAbstractItemView.EditKeyPressed |
        QtWidgets.QAbstractItemView.AnyKeyPressed
    )
    page.venta_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    page.venta_table.itemChanged.connect(page.on_venta_table_item_changed)
    page.venta_table.setAlternatingRowColors(False)
    page.venta_table.setShowGrid(False)
    page.venta_table.setMinimumHeight(280)
    table_layout.addWidget(page.venta_table)
    return table_container
