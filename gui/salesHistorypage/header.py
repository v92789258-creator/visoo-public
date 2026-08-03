from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


def build_header(page):
    header = QWidget()
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(0, 0, 0, 0)

    title_layout = QVBoxLayout()
    title = QLabel("Historial de Ventas")
    title.setStyleSheet(
        """
        font-size: 25px;
        color: #2C2C2C;
        margin: 0px;
        background: transparent;
        """
    )
    title.setAlignment(Qt.AlignLeft)

    subtitle = QLabel("Consulta y gestiona el registro de ventas")
    subtitle.setStyleSheet(
        """
        font-size: 14px;
        color: #6c757d;
        margin: 0px;
        """
    )
    subtitle.setAlignment(Qt.AlignLeft)

    title_layout.addWidget(title)
    title_layout.addWidget(subtitle)
    header_layout.addLayout(title_layout)
    header_layout.addStretch()

    totals_widget = QWidget()
    totals_layout = QVBoxLayout(totals_widget)
    totals_layout.setContentsMargins(0, 0, 0, 0)
    totals_layout.setSpacing(2)

    total_label = QLabel("Total del período:")
    total_label.setStyleSheet("color: #495057;")
    page.total_amount_label = QLabel("S/0.00")
    page.total_amount_label.setObjectName("total_amount")
    page.total_amount_label.setStyleSheet("font-size: 18px; color: #0d6efd; font-weight: bold;")

    total_efectivo_title_label = QLabel("Total de caja (Efectivo):")
    total_efectivo_title_label.setStyleSheet("color: #495057; margin-top: 5px;")
    page.total_efectivo_label = QLabel("S/0.00")
    page.total_efectivo_label.setObjectName("total_efectivo")
    page.total_efectivo_label.setStyleSheet("font-size: 18px; color: #198754; font-weight: bold;")

    totals_layout.addWidget(total_label, alignment=Qt.AlignRight)
    totals_layout.addWidget(page.total_amount_label, alignment=Qt.AlignRight)
    totals_layout.addWidget(total_efectivo_title_label, alignment=Qt.AlignRight)
    totals_layout.addWidget(page.total_efectivo_label, alignment=Qt.AlignRight)
    header_layout.addWidget(totals_widget)
    return header
