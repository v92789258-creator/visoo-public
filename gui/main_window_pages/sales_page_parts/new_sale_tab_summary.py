from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolButton, QVBoxLayout, QWidget

from utils.file_handler import cargar_tamano_logo, guardar_tamano_logo


def build_new_sale_summary(page):
    summary_container = QWidget()
    summary_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    summary_container.setStyleSheet("""
        QWidget {
            background: white;
            border-top: 1px solid #e0e0e0;
            padding: 12px 0px;
        }
        QLabel {
            font-size: 14px;
            color: #1a1a1a;
        }
        QPushButton#primaryButton {
            background: #2a2a2a;
            color: white;
            padding: 10px 18px;
            border: 1px solid #1a1a1a;
            font-weight: 500;
            min-width: 140px;
            font-size: 12px;
        }
        QPushButton#primaryButton:hover {
            background: #1a1a1a;
        }
        QPushButton#secondaryButton {
            background: #e0e0e0;
            color: #1a1a1a;
            padding: 10px 18px;
            border: 1px solid #d0d0d0;
            font-weight: 500;
            min-width: 130px;
            font-size: 12px;
        }
        QPushButton#secondaryButton:hover {
            background: #d0d0d0;
        }
    """)
    summary_layout = QHBoxLayout(summary_container)
    summary_layout.setContentsMargins(20, 12, 20, 12)
    summary_layout.setSpacing(20)

    details_layout = QGridLayout()
    details_layout.setHorizontalSpacing(30)
    details_layout.setVerticalSpacing(8)
    details_layout.setContentsMargins(0, 0, 0, 0)

    label_items = QLabel("Artículos:")
    label_items.setStyleSheet("font-weight: 600; color: #666666; font-size: 12px;")
    page.items_count_label = QLabel("0")
    page.items_count_label.setStyleSheet("color: #1a1a1a; font-size: 13px;")
    details_layout.addWidget(label_items, 0, 0)
    details_layout.addWidget(page.items_count_label, 0, 1)

    label_subtotal = QLabel("Subtotal:")
    label_subtotal.setStyleSheet("font-weight: 600; color: #666666; font-size: 12px;")
    page.subtotal_label = QLabel("S/0.00")
    page.subtotal_label.setStyleSheet("color: #1a1a1a; font-size: 13px;")
    details_layout.addWidget(label_subtotal, 0, 2)
    details_layout.addWidget(page.subtotal_label, 0, 3)

    label_igv = QLabel("IGV (18%):")
    label_igv.setStyleSheet("font-weight: 600; color: #666666; font-size: 12px;")
    page.igv_label = QLabel("S/0.00")
    page.igv_label.setStyleSheet("color: #1a1a1a; font-size: 13px;")
    details_layout.addWidget(label_igv, 1, 2)
    details_layout.addWidget(page.igv_label, 1, 3)

    label_discount = QLabel("Descuento en %:")
    label_discount.setStyleSheet("font-weight: 600; color: #666666; font-size: 12px;")
    discount_layout = QHBoxLayout()
    page.discount_input = QLineEdit()
    page.discount_input.setText("0")
    page.discount_input.setMaximumWidth(80)
    page.discount_input.setStyleSheet("""
        QLineEdit {
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 4px;
            font-size: 12px;
        }
        QLineEdit:focus {
            border: 2px solid #0d6efd;
        }
    """)
    discount_layout.addWidget(page.discount_input)
    discount_layout.addStretch()
    discount_widget = QWidget()
    discount_widget.setLayout(discount_layout)
    details_layout.addWidget(label_discount, 2, 2)
    details_layout.addWidget(discount_widget, 2, 3)

    logo_size_container = QWidget()
    logo_size_layout = QHBoxLayout(logo_size_container)
    logo_size_layout.setContentsMargins(0, 0, 0, 0)
    logo_size_layout.setSpacing(12)
    label_logo_size = QLabel("Tamaño Logo:")
    label_logo_size.setStyleSheet("font-weight: 600; color: #666666; font-size: 12px;")
    logo_size_layout.addWidget(label_logo_size)

    page.slider_logo_tamano_venta = QtWidgets.QSlider(Qt.Horizontal)
    page.slider_logo_tamano_venta.setMinimum(50)
    page.slider_logo_tamano_venta.setMaximum(400)
    page.slider_logo_tamano_venta.setValue(cargar_tamano_logo(page.username))
    page.slider_logo_tamano_venta.setTickPosition(QtWidgets.QSlider.TicksBelow)
    page.slider_logo_tamano_venta.setTickInterval(50)
    page.slider_logo_tamano_venta.setStyleSheet("""
        QSlider::groove:horizontal {
            border: 1px solid #ddd;
            background: linear-gradient(to right, #e0e0e0, #f5f5f5);
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2);
            border: 2px solid #1565C0;
            width: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }
        QSlider::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1976D2, stop:1 #1565C0);
            border: 2px solid #0d47a1;
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(to right, #42a5f5, #1976D2);
            border-radius: 3px;
        }
    """)
    page.slider_logo_tamano_venta.setMaximumWidth(200)
    logo_size_layout.addWidget(page.slider_logo_tamano_venta, 1)
    page.lbl_logo_size_venta = QLabel(f"{page.slider_logo_tamano_venta.value()}px")
    page.lbl_logo_size_venta.setStyleSheet("color: #1976D2; font-weight: bold; font-size: 11px; min-width: 40px;")
    logo_size_layout.addWidget(page.lbl_logo_size_venta)
    page.slider_logo_tamano_venta.valueChanged.connect(lambda v: page.lbl_logo_size_venta.setText(f"{v}px"))
    page.slider_logo_tamano_venta.valueChanged.connect(lambda v: guardar_tamano_logo(page.username, v))
    details_layout.addWidget(logo_size_container, 2, 0, 1, 4)

    separator = QWidget()
    separator.setStyleSheet("background: #DDDDDD;")
    separator.setFixedWidth(1)

    totals_layout = QVBoxLayout()
    totals_layout.setContentsMargins(20, 0, 0, 0)
    totals_layout.setSpacing(4)
    label_total = QLabel("TOTAL A PAGAR")
    label_total.setStyleSheet("font-size: 11px; color: #666666; font-weight: 600;")
    page.total_venta_label = QLabel("S/0.00")
    page.total_venta_label.setStyleSheet("font-size: 24px; font-weight: 700; color: #1a1a1a;")
    totals_layout.addWidget(label_total)
    totals_layout.addWidget(page.total_venta_label)

    buttons_layout = QHBoxLayout()
    buttons_layout.setSpacing(8)
    order_layout = QHBoxLayout()
    order_layout.setSpacing(6)
    page.label_numero_orden_venta = QLabel("N° Orden: 0001")
    page.label_numero_orden_venta.setStyleSheet("font-size: 11px; color: #666666; font-weight: 600;")
    page.btn_editar_orden_venta = QToolButton()
    page.btn_editar_orden_venta.setText("✎")
    page.btn_editar_orden_venta.setToolTip("Editar N° de orden")
    page.btn_editar_orden_venta.setCursor(Qt.PointingHandCursor)
    page.btn_editar_orden_venta.setStyleSheet("""
        QToolButton {
            background: #F8F8F8;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 4px;
            color: #333333;
            min-width: 24px;
            min-height: 24px;
        }
        QToolButton:hover {
            background: #F0F0F0;
            border: 1px solid #999999;
        }
    """)
    page.btn_editar_orden_venta.clicked.connect(page._editar_order_number)
    order_layout.addWidget(page.label_numero_orden_venta)
    order_layout.addWidget(page.btn_editar_orden_venta)

    page.btn_limpiar_venta = QToolButton()
    page.btn_limpiar_venta.setText("Limpiar")
    page.btn_limpiar_venta.setToolTip("Limpiar la venta actual")
    page.btn_limpiar_venta.setCursor(Qt.PointingHandCursor)
    page.btn_limpiar_venta.setStyleSheet("""
        QToolButton {
            background: transparent;
            border: 1px solid #D8DDE3;
            border-radius: 4px;
            padding: 4px 10px;
            color: #6B7280;
            min-height: 24px;
            font-size: 11px;
            font-weight: 600;
        }
        QToolButton:hover {
            background: #F7F7F7;
            border: 1px solid #C8CED6;
            color: #333333;
        }
    """)
    page.btn_limpiar_venta.clicked.connect(page.clear_sales_form_and_table_with_loader)
    order_layout.addWidget(page.btn_limpiar_venta)

    page.btn_generar_boleta = QPushButton("Generar Boleta")
    page.btn_generar_boleta.setObjectName("secondaryButton")
    page.btn_generar_boleta.setHidden(True)
    page.btn_generar_boleta.clicked.connect(page.generar_boleta)

    page.btn_registrar_venta = QPushButton("Registrar Venta")
    page.btn_registrar_venta.setObjectName("primaryButton")
    page.btn_registrar_venta.clicked.connect(page.registrar_venta)

    buttons_layout.addLayout(order_layout)
    buttons_layout.addWidget(page.btn_generar_boleta)
    buttons_layout.addWidget(page.btn_registrar_venta)

    summary_layout.addLayout(details_layout)
    summary_layout.addWidget(separator)
    summary_layout.addLayout(totals_layout)
    summary_layout.addStretch()
    summary_layout.addLayout(buttons_layout)
    page._refresh_order_number_preview()
    page._update_multi_metodo_pago_sale_state()
    return summary_container
