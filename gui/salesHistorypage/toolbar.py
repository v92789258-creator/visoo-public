import datetime
import os

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
)


def build_toolbar(page, content_layout, icon_base_dir):
    ventas_count = 0
    page.debug_label = QLabel(f"Usuario: {page.username} - ventas cargadas: {ventas_count} - fuente: preparando...")
    try:
        page.debug_label.setText(f"Usuario: {page.username} - ventas: (cargando...) - fuente: preparando...")
    except Exception:
        pass
    page.debug_label.setStyleSheet("color: #555; font-size: 11px; margin: 4px 0;")
    content_layout.addWidget(page.debug_label)

    page.empty_message = QLabel("Cargando ventas...")
    page.empty_message.setStyleSheet(
        "background: #fff8e1; border: 1px solid #ffe082; color: #6b4f00; padding: 12px; font-weight: 700;"
    )
    page.empty_message.setAlignment(QtCore.Qt.AlignCenter)
    page.empty_message.setVisible(True)
    content_layout.addWidget(page.empty_message)

    btn_reload = QPushButton("↻ Recargar")
    btn_reload.setToolTip("Forzar recarga de ventas desde el archivo")
    btn_reload.clicked.connect(page._reload_sales)
    btn_reload.setStyleSheet(
        """
        QPushButton {
            background: #198754;
            color: white;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 6px;
        }
        QPushButton:hover { background: #157347; }
        """
    )

    btn_compare = QPushButton("Dividir")
    btn_compare.setToolTip("Mostrar vista comparativa con dos paneles")
    btn_compare.clicked.connect(page.toggle_compare_mode)
    btn_compare.setStyleSheet(
        """
        QPushButton {
            background: #6f42c1;
            color: white;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 6px;
        }
        QPushButton:hover { background: #5a34a3; }
        """
    )

    btn_reportes_globales = QPushButton()
    btn_reportes_globales.setToolTip("Generar reportes consolidados")
    btn_reportes_globales.clicked.connect(page._generar_reportes_globales)
    btn_reportes_globales.setStyleSheet(
        "QPushButton { background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 8px; } "
        "QPushButton:hover { background: #f0f0f0; }"
    )
    svg_path = os.path.join(icon_base_dir, "icons", "reporte.svg")
    if os.path.exists(svg_path):
        btn_reportes_globales.setIcon(QIcon(svg_path))
        btn_reportes_globales.setIconSize(QtCore.QSize(24, 24))
    btn_reportes_globales.setFixedSize(40, 40)

    btn_export_more = QToolButton()
    btn_export_more.setText("...")
    btn_export_more.setStyleSheet(
        "QToolButton { background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 6px; font-weight: bold; font-size: 16px; } "
        "QToolButton:hover { background: #f1f3f5; }"
    )
    export_more_menu = QMenu(btn_export_more)
    export_more_menu.addAction("Exportar ventas del día", page._open_today_sales_pdf_customizer)
    export_more_menu.addAction("Exportar ventas de otra fecha", page._open_specific_day_sales_pdf_customizer)
    btn_export_more.setMenu(export_more_menu)
    btn_export_more.setPopupMode(QToolButton.InstantPopup)

    filter_container = QWidget()
    filter_container.setStyleSheet(
        """
        QWidget { background: white; border-radius: 10px; padding: 12px; }
        QLabel { color: #495057; font-weight: bold; font-size: 12px; }
        QLineEdit {
            padding: 7px 10px;
            border: 1px solid #ced4da;
            border-radius: 6px;
            background: white;
            min-width: 140px;
            font-size: 12px;
        }
        QPushButton#filtrarBtn {
            background: #0d6efd;
            color: white;
            font-weight: bold;
            padding: 7px 14px;
            border-radius: 6px;
            font-size: 12px;
            border: none;
        }
        QPushButton#filtrarBtn:hover { background: #0b5ed7; }
        """
    )
    f_layout = QHBoxLayout(filter_container)
    f_layout.setSpacing(10)
    f_layout.addWidget(QLabel("Fecha (dd/mm/aaaa):"))

    page.fecha_texto_input = QLineEdit()
    page.fecha_texto_input.setPlaceholderText("dd/mm/aaaa")
    hoy_str = datetime.date.today().strftime("%d/%m/%Y")
    page.fecha_texto_input.setText(hoy_str)

    btn_filtrar_fecha = QPushButton("Filtrar")
    btn_filtrar_fecha.setObjectName("filtrarBtn")
    btn_filtrar_fecha.clicked.connect(page._apply_text_date_filter)
    page.fecha_texto_input.returnPressed.connect(page._apply_text_date_filter)

    f_layout.addWidget(page.fecha_texto_input)
    f_layout.addWidget(btn_filtrar_fecha)
    f_layout.addStretch()
    f_layout.addWidget(btn_reload)
    f_layout.addWidget(btn_compare)
    f_layout.addWidget(btn_reportes_globales)
    f_layout.addWidget(btn_export_more)
    content_layout.addWidget(filter_container)

    page.date_start = QDateEdit()
    page.date_end = QDateEdit()
    page.date_start.setVisible(False)
    page.date_end.setVisible(False)
    content_layout.addWidget(page.date_start)
    content_layout.addWidget(page.date_end)

    page._apply_text_date_filter()
