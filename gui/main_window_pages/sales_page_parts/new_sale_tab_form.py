from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QCheckBox, QComboBox, QDateEdit, QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QToolButton, QWidget

from utils.barcode_scanner import BarcodeLineEdit
from utils.file_handler import cargar_tamano_logo, guardar_tamano_logo


def build_new_sale_form(page):
    sale_form_group = QGroupBox("Datos de la Venta")
    sale_form_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
    sale_form_layout = QGridLayout(sale_form_group)
    sale_form_layout.setContentsMargins(0, 0, 0, 0)
    sale_form_layout.setHorizontalSpacing(10)
    sale_form_layout.setVerticalSpacing(8)

    label_dni = QLabel("DNI del cliente:")
    label_dni.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label_dni.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px;")
    page.entry_venta_paciente = QLineEdit("00000000")
    page.entry_venta_paciente.setPlaceholderText("DNI del cliente (00000000 para genérico)")
    try:
        page.entry_venta_paciente.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    except Exception:
        pass
    sale_form_layout.addWidget(label_dni, 0, 0)
    sale_form_layout.addWidget(page.entry_venta_paciente, 0, 1)

    btn_seleccionar_paciente = QPushButton("Buscar")
    btn_seleccionar_paciente.clicked.connect(page.abrir_seleccion_paciente)
    btn_seleccionar_paciente.setMaximumWidth(80)
    sale_form_layout.addWidget(btn_seleccionar_paciente, 0, 2)

    label_nombre = QLabel("Nombre:")
    label_nombre.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label_nombre.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px;")
    page.label_venta_nombre = QLineEdit("")
    page.label_venta_nombre.setPlaceholderText("Escriba o corrija el nombre del cliente")
    sale_form_layout.addWidget(label_nombre, 1, 0)
    sale_form_layout.addWidget(page.label_venta_nombre, 1, 1, 1, 2)

    label_mp = QLabel("Método de Pago:")
    label_mp.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label_mp.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px;")
    page.metodo_pago_combo = QComboBox()
    page.metodo_pago_combo.setEditable(True)
    page.metodo_pago_combo.setInsertPolicy(QComboBox.NoInsert)
    try:
        page.metodo_pago_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    except Exception:
        pass
    page.update_metodo_pago_combo()
    sale_form_layout.addWidget(label_mp, 2, 0)
    sale_form_layout.addWidget(page.metodo_pago_combo, 2, 1, 1, 2)

    page.checkbox_multi_metodo_pago = QCheckBox("Mas de un metodo")
    page.checkbox_multi_metodo_pago.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px; spacing: 6px;")
    page.checkbox_multi_metodo_pago.toggled.connect(page._toggle_multi_metodo_pago_sale)
    sale_form_layout.addWidget(page.checkbox_multi_metodo_pago, 3, 1)

    page.checkbox_pago_partes = QCheckBox("Pago en Partes")
    page.checkbox_pago_partes.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px; spacing: 6px;")
    page.checkbox_pago_partes.toggled.connect(page.on_pago_partes_toggled)
    sale_form_layout.addWidget(page.checkbox_pago_partes, 3, 2)

    page.multi_metodo_pago_sale_container = QWidget()
    multi_sale_layout = QGridLayout(page.multi_metodo_pago_sale_container)
    multi_sale_layout.setContentsMargins(0, 0, 0, 0)
    multi_sale_layout.setHorizontalSpacing(8)
    multi_sale_layout.setVerticalSpacing(6)
    page.label_multi_metodo_pago_sale_info = QLabel("Distribuye el pago actual entre dos metodos.")
    page.label_multi_metodo_pago_sale_info.setStyleSheet("color: #666666; font-size: 11px;")
    multi_sale_layout.addWidget(page.label_multi_metodo_pago_sale_info, 0, 0, 1, 4)
    multi_sale_layout.addWidget(QLabel("Metodo 1"), 1, 0)
    page.metodo_pago_combo_2 = QComboBox()
    multi_sale_layout.addWidget(page.metodo_pago_combo_2, 1, 1)
    multi_sale_layout.addWidget(QLabel("Monto 1"), 1, 2)
    page.entry_metodo_pago_monto_1 = QtWidgets.QDoubleSpinBox()
    page.entry_metodo_pago_monto_1.setMinimum(0.0)
    page.entry_metodo_pago_monto_1.setMaximum(999999.99)
    page.entry_metodo_pago_monto_1.setDecimals(2)
    page.entry_metodo_pago_monto_1.valueChanged.connect(page._sync_multi_metodo_pago_sale_limits)
    multi_sale_layout.addWidget(page.entry_metodo_pago_monto_1, 1, 3)
    multi_sale_layout.addWidget(QLabel("Metodo 2"), 2, 0)
    page.metodo_pago_combo_3 = QComboBox()
    multi_sale_layout.addWidget(page.metodo_pago_combo_3, 2, 1)
    multi_sale_layout.addWidget(QLabel("Monto 2"), 2, 2)
    page.entry_metodo_pago_monto_2 = QtWidgets.QDoubleSpinBox()
    page.entry_metodo_pago_monto_2.setMinimum(0.0)
    page.entry_metodo_pago_monto_2.setMaximum(999999.99)
    page.entry_metodo_pago_monto_2.setDecimals(2)
    page.entry_metodo_pago_monto_2.valueChanged.connect(page._sync_multi_metodo_pago_sale_limits)
    multi_sale_layout.addWidget(page.entry_metodo_pago_monto_2, 2, 3)
    page.multi_metodo_pago_sale_container.setVisible(False)
    sale_form_layout.addWidget(page.multi_metodo_pago_sale_container, 5, 1, 1, 2)

    label_vendedor = QLabel("Vendedor:")
    label_vendedor.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label_vendedor.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px;")
    page.vendedor_combo = QComboBox()
    page.vendedor_combo.setEditable(True)
    page.vendedor_combo.setInsertPolicy(QComboBox.NoInsert)
    try:
        page.vendedor_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    except Exception:
        pass
    page.update_vendedor_combo()
    page.vendedor_combo.currentTextChanged.connect(page._update_sale_commission_summary)
    sale_form_layout.addWidget(label_vendedor, 6, 0)
    sale_form_layout.addWidget(page.vendedor_combo, 6, 1, 1, 2)

    label_fecha_venta = QLabel("Fecha de Venta:")
    label_fecha_venta.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label_fecha_venta.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px;")
    page.fecha_venta_edit = QDateEdit()
    page.fecha_venta_edit.setCalendarPopup(True)
    page.fecha_venta_edit.setDisplayFormat("dd/MM/yyyy")
    page.fecha_venta_edit.setDate(QDate.currentDate())
    page.fecha_venta_edit.setStyleSheet("color: #333333; font-size: 11px; padding: 4px; border: 1px solid #CCCCCC;")
    try:
        page.fecha_venta_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    except Exception:
        pass
    sale_form_layout.addWidget(label_fecha_venta, 7, 0)
    sale_form_layout.addWidget(page.fecha_venta_edit, 7, 1, 1, 2)

    label_adelanto = QLabel("Monto Adelanto:")
    label_adelanto.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label_adelanto.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px;")
    label_adelanto.setHidden(True)
    page.entry_adelanto = QtWidgets.QDoubleSpinBox()
    page.entry_adelanto.setMinimum(0)
    page.entry_adelanto.setMaximum(999999.99)
    page.entry_adelanto.setDecimals(2)
    page.entry_adelanto.setValue(0.0)
    page.entry_adelanto.setHidden(True)
    sale_form_layout.addWidget(label_adelanto, 4, 0)
    sale_form_layout.addWidget(page.entry_adelanto, 4, 1, 1, 2)
    page.label_adelanto = label_adelanto
    page.entry_adelanto.valueChanged.connect(page._update_multi_metodo_pago_sale_state)
    page.entry_adelanto.valueChanged.connect(page._sync_sale_adelanto_limit)

    page.checkbox_comision_venta = QCheckBox("Activar comisión")
    page.checkbox_comision_venta.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px; spacing: 6px;")
    page.checkbox_comision_venta.toggled.connect(page.on_comision_venta_toggled)
    sale_form_layout.addWidget(page.checkbox_comision_venta, 7, 2)

    label_comision = QLabel("Comisión (S/):")
    label_comision.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label_comision.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px;")
    label_comision.setHidden(True)
    page.entry_comision_venta = QtWidgets.QDoubleSpinBox()
    page.entry_comision_venta.setMinimum(0.0)
    page.entry_comision_venta.setMaximum(999999.99)
    page.entry_comision_venta.setDecimals(2)
    page.entry_comision_venta.setValue(0.0)
    page.entry_comision_venta.setHidden(True)
    page.entry_comision_venta.valueChanged.connect(page._update_sale_commission_summary)
    sale_form_layout.addWidget(label_comision, 8, 0)
    sale_form_layout.addWidget(page.entry_comision_venta, 8, 1)
    page.label_comision_venta = label_comision

    page.label_comision_venta_summary = QLabel("")
    page.label_comision_venta_summary.setStyleSheet("color: #6c757d; font-size: 11px;")
    page.label_comision_venta_summary.setHidden(True)
    sale_form_layout.addWidget(page.label_comision_venta_summary, 8, 2)

    btn_seleccionar_productos = QPushButton("Seleccionar Productos")
    btn_seleccionar_productos.clicked.connect(page.abrir_seleccion_productos)
    btn_seleccionar_productos.setStyleSheet("""
        QPushButton {
            background: #333333;
            color: white;
            border: none;
            padding: 10px;
            font-weight: 500;
            font-size: 11px;
            min-height: 32px;
        }
        QPushButton:hover {
            background: #1a1a1a;
        }
        QPushButton:pressed {
            background: #555555;
        }
    """)
    btn_seleccionar_productos.setCursor(Qt.PointingHandCursor)
    btn_seleccionar_productos.setMinimumHeight(32)
    sale_form_layout.addWidget(btn_seleccionar_productos, 9, 0, 1, 3)

    label_barcode = QLabel("Buscar por Código:")
    label_barcode.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label_barcode.setStyleSheet("font-weight: 500; color: #333333; font-size: 11px;")
    page.barcode_input = BarcodeLineEdit()
    page.barcode_input.setPlaceholderText("Escanea el código de barras del producto")
    page.barcode_input.barcode_captured.connect(page.on_barcode_scanned)
    sale_form_layout.addWidget(label_barcode, 10, 0)
    sale_form_layout.addWidget(page.barcode_input, 10, 1, 1, 2)

    try:
        page.barcode_input.start_scanning()
    except RuntimeError:
        pass

    page._refresh_order_number_preview()
    page._update_multi_metodo_pago_sale_state()
    return sale_form_group
