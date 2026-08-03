from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QMenu, QPushButton, QVBoxLayout, QWidget

from gui.main_window_pages.sales_page_parts import SalesTableWidget


def build_table_section(page):
    table_container = QWidget()
    table_container.setStyleSheet(
        """
        QWidget {
            background: white;
            border-radius: 10px;
            padding: 20px;
        }
        QTableWidget {
            border: 1px solid #dee2e6;
            border-radius: 8px;
            gridline-color: #dee2e6;
            background: white;
        }
        QTableWidget::item {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }
        QTableWidget::item:selected {
            background-color: #e7f1ff;
            color: #0d6efd;
        }
        QHeaderView::section {
            background-color: #f8f9fa;
            padding: 12px;
            border: none;
            border-bottom: 2px solid #dee2e6;
            font-weight: bold;
            color: #495057;
        }
        QHeaderView::section:first {
            border-top-left-radius: 8px;
        }
        QHeaderView::section:last {
            border-top-right-radius: 8px;
        }
        QPushButton {
            background: #0d6efd;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background: #0b5ed7;
        }
        """
    )
    table_layout = QVBoxLayout(table_container)
    table_layout.setContentsMargins(0, 0, 0, 0)

    page.sales_table = SalesTableWidget(parent_page=page)
    page.sales_table.setColumnCount(8)
    page.sales_table.setHorizontalHeaderLabels(
        ["Fecha", "N° Orden", "DNI Paciente", "Artículos", "Total", "Método de Pago", "Estado", "Acciones"]
    )

    header = page.sales_table.horizontalHeader()
    header.setVisible(True)
    header.setMinimumHeight(45)
    header.setDefaultAlignment(Qt.AlignCenter)
    header.setHighlightSections(False)
    header.setStretchLastSection(False)

    page.sales_table.verticalHeader().setVisible(False)
    page.sales_table.setShowGrid(True)
    page.sales_table.setGridStyle(Qt.SolidLine)
    page.sales_table.setColumnWidth(0, 130)
    page.sales_table.setColumnWidth(1, 95)
    page.sales_table.setColumnWidth(2, 100)
    page.sales_table.setColumnWidth(4, 120)
    page.sales_table.setColumnWidth(5, 140)
    page.sales_table.setColumnWidth(6, 150)
    page.sales_table.setColumnWidth(7, 100)

    header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
    header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
    header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
    header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
    header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
    header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
    header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
    header.setSectionResizeMode(7, QtWidgets.QHeaderView.Fixed)

    page.sales_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    page.sales_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    page.sales_table.setAlternatingRowColors(True)
    page.sales_table.setMinimumHeight(400)
    page.sales_table.setShowGrid(False)
    page.sales_table.verticalHeader().setDefaultSectionSize(45)
    try:
        page.sales_table.cellClicked.connect(page._on_sales_table_cell_clicked)
    except Exception:
        pass
    page.sales_table.itemSelectionChanged.connect(page._on_sales_selection_changed)
    table_layout.addWidget(page.sales_table)

    page.mass_actions_container = QWidget()
    page.mass_actions_container.setVisible(False)
    mass_layout = QHBoxLayout(page.mass_actions_container)
    mass_layout.setContentsMargins(0, 5, 0, 5)
    mass_layout.addStretch()

    page.btn_mass_rules = QPushButton("Acciones (0)")
    page.btn_mass_rules.setCursor(Qt.PointingHandCursor)
    page.btn_mass_rules.setStyleSheet(
        """
        QPushButton {
            background-color: #212529;
            color: white;
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: bold;
            border: 1px solid #343a40;
        }
        QPushButton:hover { background-color: #343a40; }
        """
    )

    mass_rules_menu = QMenu(page.btn_mass_rules)
    page.btn_mass_rules.setMenu(mass_rules_menu)
    mass_layout.addWidget(page.btn_mass_rules)
    page.btn_mass_rules.setVisible(False)
    table_layout.addWidget(page.mass_actions_container)
    return table_container
