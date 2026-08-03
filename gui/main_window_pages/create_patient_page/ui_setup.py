import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.selection_dialogs import SeleccionarPacientesDialog
from utils.file_handler import cargar_metodos_pago, cargar_optometras


class CreatePatientPageUiSetupMixin:
    def _safe_float_value(self, value):
        try:
            return float(str(value or "0").strip().replace("S/.", "").replace("S/", "").replace(",", ""))
        except (TypeError, ValueError):
            return 0.0

    def _update_comision_preview(self):
        if not hasattr(self, "check_comision"):
            return

        activa = self.check_comision.isChecked()
        if hasattr(self, "entry_comision_monto"):
            self.entry_comision_monto.setEnabled(activa)

        monto_comision = self._safe_float_value(
            self.entry_comision_monto.text() if hasattr(self, "entry_comision_monto") else 0
        ) if activa else 0.0
        beneficiario = getattr(self, "_current_comision_beneficiario_name", lambda: "Optómetra")()

        if hasattr(self, "label_comision_resumen"):
            if activa:
                self.label_comision_resumen.setText(
                    f"Comisión fija: S/. {monto_comision:.2f} para {beneficiario}"
                )
            else:
                self.label_comision_resumen.setText("Comisión desactivada")

    def _cargar_metodos_pago_graduacion(self):
        if not hasattr(self, "metodo_pago_combo_grad"):
            return
        try:
            metodos = cargar_metodos_pago(self.username)
        except Exception:
            metodos = []
        self._populate_metodo_pago_combo(self.metodo_pago_combo_grad, metodos)
        if hasattr(self, "metodo_pago_combo_grad_2"):
            self._populate_metodo_pago_combo(self.metodo_pago_combo_grad_2, metodos)
        if hasattr(self, "metodo_pago_combo_grad_3"):
            self._populate_metodo_pago_combo(self.metodo_pago_combo_grad_3, metodos)

    def _populate_metodo_pago_combo(self, combo, metodos=None):
        if combo is None:
            return
        combo.clear()
        if metodos is None:
            try:
                metodos = cargar_metodos_pago(self.username)
            except Exception:
                metodos = []
        if metodos:
            combo.addItems(metodos)
            combo.setDisabled(False)
        else:
            combo.addItem("Sin métodos de pago")
            combo.setDisabled(True)

    def _toggle_multi_metodo_pago_grad(self, checked=None):
        _ = checked
        enabled = bool(
            hasattr(self, "check_multi_metodo_pago_grad")
            and self.check_multi_metodo_pago_grad.isChecked()
            and hasattr(self, "metodo_pago_container")
            and self.metodo_pago_container.isVisible()
        )
        if hasattr(self, "multi_metodo_pago_grad_container"):
            self.multi_metodo_pago_grad_container.setVisible(enabled)
        self._update_multi_metodo_pago_grad_state()

    def _update_multi_metodo_pago_grad_state(self):
        if not hasattr(self, "label_multi_metodo_pago_grad_info"):
            return
        monto_base = self._safe_float_value(
            self.entry_monto_cobrado.text() if hasattr(self, "entry_monto_cobrado") else 0
        )
        productos_total = 0.0
        for item in getattr(self, "items_venta", []) or []:
            if isinstance(item, dict):
                productos_total += self._safe_float_value(
                    item.get("total", item.get("subtotal", item.get("precio_unitario", 0)))
                )
        total_estimado = monto_base + productos_total
        if hasattr(self, "checkbox_en_partes") and self.checkbox_en_partes.isChecked():
            self.label_multi_metodo_pago_grad_info.setText(
                "Pago mixto del adelanto actual. La suma debe coincidir con el adelanto al guardar."
            )
        else:
            self.label_multi_metodo_pago_grad_info.setText(
                f"Distribuye el pago total actual: S/. {total_estimado:.2f}"
            )

    def _update_metodo_pago_visibility(self):
        if not hasattr(self, "metodo_pago_container"):
            return
        monto = self._safe_float_value(
            self.entry_monto_cobrado.text() if hasattr(self, "entry_monto_cobrado") else 0
        )
        mostrar = monto > 0.0
        self.metodo_pago_container.setVisible(mostrar)
        if mostrar:
            self._cargar_metodos_pago_graduacion()
        if hasattr(self, "check_multi_metodo_pago_grad"):
            self.check_multi_metodo_pago_grad.setVisible(mostrar)
        self._toggle_multi_metodo_pago_grad()

    def setup_ui(self):
        self.setStyleSheet(
            """
            QWidget {
                background-color: #f5f5f5;
            }
            QScrollArea {
                background-color: #f5f5f5;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 12px;
                padding: 16px;
                color: #191919;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: #191919;
                font-weight: 600;
                font-size: 13px;
            }
            QLabel {
                color: #424242;
                font-size: 12px;
            }
            QLineEdit, QDateEdit, QComboBox {
                padding: 8px 12px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #ffffff;
                color: #191919;
                font-size: 12px;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 1px solid #191919;
            }
            QLineEdit:disabled, QDateEdit:disabled, QComboBox:disabled {
                background-color: #f5f5f5;
                color: #9e9e9e;
            }
            QTextEdit {
                padding: 8px 12px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #ffffff;
                color: #191919;
                font-size: 12px;
            }
            QCheckBox {
                color: #191919;
                spacing: 6px;
            }
        """
        )

        scroll_area = QtWidgets.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(24, 24, 24, 24)

        title_label = QLabel("Registrar Nueva Graduacion")
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        font = title_label.font()
        font.setPointSize(25)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #191919; margin-bottom: 0px;")

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(10)
        header_layout.addWidget(title_label, 1)

        self.btn_guardar_paciente_top = QPushButton("Guardar")
        self.btn_guardar_paciente_top.setToolTip("Guardar Graduacion")
        self.btn_guardar_paciente_top.clicked.connect(self.guardar_paciente)
        self.btn_guardar_paciente_top.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.btn_guardar_paciente_top.setStyleSheet(
            """
            QPushButton {
                background-color: #191919;
                color: white;
                border: none;
                padding: 0 16px;
                font-weight: 600;
                font-size: 13px;
                border-radius: 0px;
                min-height: 36px;
                max-height: 36px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
            QPushButton:pressed {
                background-color: #0f0f0f;
            }
        """
        )
        self.label_contrato_numero_top = QLabel("Contrato: 0000001")
        self.label_contrato_numero_top.setStyleSheet(
            """
            QLabel {
                color: #1f3f75;
                font-size: 13px;
                font-weight: 700;
                padding: 6px 10px;
                background: #f3f8ff;
                border: 1px solid #d7e6ff;
                border-radius: 4px;
            }
        """
        )
        self.label_contrato_numero_top.setAlignment(Qt.AlignCenter)
        self.btn_editar_contrato_top = QPushButton()
        self.btn_editar_contrato_top.setToolTip("Editar número de contrato")
        self.btn_editar_contrato_top.setIcon(
            self.create_svg_icon(
                """
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zm14.71-9.04a1.003 1.003 0 000-1.42l-2.5-2.5a1.003 1.003 0 00-1.42 0l-1.96 1.96 3.75 3.75 2.13-2.09z"/>
                </svg>
                """,
                16,
            )
        )
        self.btn_editar_contrato_top.setCursor(Qt.PointingHandCursor)
        self.btn_editar_contrato_top.setFixedSize(32, 32)
        self.btn_editar_contrato_top.setStyleSheet(
            """
            QPushButton {
                background: #ffffff;
                border: 1px solid #d7e6ff;
                border-radius: 4px;
                color: #1f3f75;
                padding: 0px;
            }
            QPushButton:hover {
                background: #eef5ff;
                border-color: #b8d2ff;
            }
            QPushButton:pressed {
                background: #ddeaff;
            }
        """
        )
        self.btn_editar_contrato_top.clicked.connect(self._editar_contrato_numero)
        header_layout.addWidget(self.label_contrato_numero_top, 0, Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(self.btn_editar_contrato_top, 0, Qt.AlignRight | Qt.AlignVCenter)

        self.btn_limpiar_graduacion = QToolButton()
        self.btn_limpiar_graduacion.setText("Limpiar")
        self.btn_limpiar_graduacion.setToolTip("Limpiar el formulario actual")
        self.btn_limpiar_graduacion.setCursor(Qt.PointingHandCursor)
        self.btn_limpiar_graduacion.setFixedHeight(32)
        self.btn_limpiar_graduacion.setStyleSheet(
            """
            QToolButton {
                background: transparent;
                border: 1px solid #e3e8ef;
                border-radius: 4px;
                color: #7a8594;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QToolButton:hover {
                background: #f7f9fc;
                border-color: #d3dbe6;
                color: #4f5b68;
            }
            QToolButton:pressed {
                background: #eef2f7;
            }
        """
        )
        self.btn_limpiar_graduacion.clicked.connect(self.clear_patient_form_with_loader)
        header_layout.addWidget(self.btn_limpiar_graduacion, 0, Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(self.btn_guardar_paciente_top, 0, Qt.AlignRight | Qt.AlignVCenter)
        content_layout.addLayout(header_layout)
        if hasattr(self, "_refresh_contract_number_preview"):
            self._refresh_contract_number_preview()

        form_group = QGroupBox("Datos del Paciente")
        form_group.setObjectName("patientForm")
        form_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        form_layout = QGridLayout(form_group)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)
        form_layout.setContentsMargins(12, 12, 12, 12)

        form_layout.addWidget(QLabel("<b>DNI:</b>"), 0, 0)
        self.entry_dni = QLineEdit()
        self.entry_dni.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        from PyQt5.QtGui import QDoubleValidator, QIntValidator

        self.entry_dni.setValidator(QIntValidator(0, 2147483647))
        form_layout.addWidget(self.entry_dni, 0, 1)
        self.entry_dni.textChanged.connect(self.on_dni_changed)

        btn_layout_top = QtWidgets.QHBoxLayout()
        btn_layout_top.setSpacing(0)
        btn_layout_top.setContentsMargins(0, 0, 0, 0)
        self.btn_buscar_dni = QPushButton()
        self.btn_buscar_dni.clicked.connect(self.buscar_por_dni)
        self.btn_buscar_dni.setIcon(
            self.create_svg_icon(
                """
            <svg viewBox="0 0 24 24" fill="white" stroke="white" stroke-width="1.5">
                <circle cx="9" cy="9" r="6" fill="none"/>
                <path d="M15 15l6 6"/>
            </svg>
        """,
                24,
            )
        )
        self.btn_buscar_dni.setToolTip("Busqueda Automatica")

        btn_convertir_cliente = QPushButton()
        btn_convertir_cliente.clicked.connect(self.convertir_cliente_en_paciente)
        btn_convertir_cliente.setIcon(
            self.create_svg_icon(
                """
            <svg viewBox="0 0 24 24" fill="white">
                <circle cx="12" cy="8" r="4"/>
                <path d="M4 20c0-4 3.5-7 8-7s8 3 8 7"/>
            </svg>
        """,
                24,
            )
        )
        btn_convertir_cliente.setToolTip("Convertir Cliente en Paciente")

        btn_style = """
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                padding: 0px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
                min-height: 36px;
                max-height: 36px;
                min-width: 36px;
                max-width: 36px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """
        self.btn_buscar_dni.setStyleSheet(btn_style)
        btn_convertir_cliente.setStyleSheet(btn_style)
        self.btn_buscar_dni.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        btn_convertir_cliente.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        btn_layout_top.addWidget(self.btn_buscar_dni)
        btn_layout_top.addWidget(btn_convertir_cliente)
        btn_layout_top.addStretch()
        form_layout.addLayout(btn_layout_top, 0, 2, 1, 2)

        form_layout.addWidget(QLabel("<b>Costo Servicio (S/):</b>"), 0, 4)
        monto_layout = QtWidgets.QHBoxLayout()
        self.entry_monto_cobrado = QLineEdit()
        self.entry_monto_cobrado.setPlaceholderText("0.00")
        self.entry_monto_cobrado.setToolTip("Ingrese SOLO el costo de la graduación. Los productos extra se suman solos.")
        self.entry_monto_cobrado.setValidator(QtGui.QDoubleValidator(0.0, 9999.99, 2))
        self.entry_monto_cobrado.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        monto_layout.addWidget(self.entry_monto_cobrado)
        self.checkbox_en_partes = QCheckBox("En Partes")
        self.checkbox_en_partes.setToolTip("Marcar si el pago es en cuotas/adelanto")
        self.checkbox_en_partes.toggled.connect(self._update_multi_metodo_pago_grad_state)
        monto_layout.addWidget(self.checkbox_en_partes)
        form_layout.addLayout(monto_layout, 0, 5)
        self.entry_monto_cobrado.textChanged.connect(self._update_comision_preview)
        self.entry_monto_cobrado.textChanged.connect(self._update_multi_metodo_pago_grad_state)

        form_layout.addWidget(QLabel("<b>Nombre:</b>"), 1, 0)
        self.entry_paciente = QLineEdit()
        self.entry_paciente.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.entry_paciente, 1, 1, 1, 2)

        form_layout.addWidget(QLabel("<b>Fecha Registro:</b>"), 1, 3)
        self.entry_fecha = QLineEdit(datetime.date.today().strftime("%d/%m/%Y"))
        self.entry_fecha.setReadOnly(False)
        self.entry_fecha.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.entry_fecha, 1, 4, 1, 2)

        form_layout.addWidget(QLabel("<b>Fecha Nacimiento:</b>"), 2, 0)
        self.entry_fecha_nacimiento = QDateEdit(calendarPopup=True)
        self.entry_fecha_nacimiento.setDate(QDate.currentDate())
        self.entry_fecha_nacimiento.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.entry_fecha_nacimiento, 2, 1)

        form_layout.addWidget(QLabel("<b>Genero:</b>"), 2, 2)
        self.genero_combo = QComboBox()
        self.genero_combo.addItems(["Masculino", "Femenino", "No especificado"])
        self.genero_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.genero_combo, 2, 3)

        form_layout.addWidget(QLabel("<b>Optometra:</b>"), 2, 4)
        self.optometra_combo = QComboBox()
        self.optometra_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.cargar_optometras_en_combo()
        form_layout.addWidget(self.optometra_combo, 2, 5)
        self.optometra_combo.currentTextChanged.connect(self._update_comision_preview)

        form_layout.addWidget(QLabel("<b>Comisión (S/):</b>"), 5, 2)
        comision_layout = QtWidgets.QHBoxLayout()
        comision_layout.setContentsMargins(0, 0, 0, 0)
        comision_layout.setSpacing(8)
        self.check_comision = QCheckBox("Activar")
        self.check_comision.setToolTip("Aplica comisión a la optómetra seleccionada")
        comision_layout.addWidget(self.check_comision)
        self.entry_comision_monto = QLineEdit()
        self.entry_comision_monto.setPlaceholderText("Ej: 10.00")
        self.entry_comision_monto.setText("0.00")
        self.entry_comision_monto.setValidator(QtGui.QDoubleValidator(0.0, 9999.99, 2))
        self.entry_comision_monto.setEnabled(False)
        self.entry_comision_monto.setMaximumWidth(110)
        self.entry_comision_monto.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        comision_layout.addWidget(self.entry_comision_monto)
        comision_layout.addStretch()
        form_layout.addLayout(comision_layout, 5, 3)
        self.label_comision_resumen = QLabel("Comisión desactivada")
        self.label_comision_resumen.setStyleSheet("color: #5f6b7a; font-size: 11px;")
        form_layout.addWidget(self.label_comision_resumen, 5, 4, 1, 2)
        self.check_comision.toggled.connect(self._update_comision_preview)
        self.entry_comision_monto.textChanged.connect(self._update_comision_preview)

        form_layout.addWidget(QLabel("<b>Proxima Cita:</b>"), 3, 0)
        self.check_proxima_cita = QCheckBox("Si")
        self.check_proxima_cita.setChecked(False)
        self.check_proxima_cita.stateChanged.connect(self.toggle_proxima_cita_date)
        form_layout.addWidget(self.check_proxima_cita, 3, 1)

        self.label_proxima_cita = QLabel("<b>Fecha Proxima Cita:</b>")
        self.entry_proxima_cita = QDateEdit(calendarPopup=True)
        self.entry_proxima_cita.setDate(QDate.currentDate().addDays(30))
        self.label_proxima_cita.setHidden(True)
        self.entry_proxima_cita.setHidden(True)
        self.entry_proxima_cita.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.label_proxima_cita, 3, 3)
        form_layout.addWidget(self.entry_proxima_cita, 3, 4, 1, 2)

        lejos_group = QGroupBox("Vision de Lejos")
        lejos_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        lejos_layout = QGridLayout(lejos_group)
        self.lejos_form_widgets = self.create_graduacion_widgets(lejos_layout, 0, "lejos")
        form_layout.addWidget(lejos_group, 6, 0, 1, 6)

        cerca_group = QGroupBox("Vision de Cerca")
        cerca_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        cerca_layout = QGridLayout(cerca_group)
        self.cerca_form_widgets = self.create_graduacion_widgets(cerca_layout, 0, "cerca")
        form_layout.addWidget(cerca_group, 7, 0, 1, 6)
        self.setup_graduacion_keyboard_navigation()

        observacion_group = QGroupBox("Observaciones")
        observacion_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        observacion_layout = QVBoxLayout(observacion_group)
        self.text_observacion = QTextEdit()
        self.text_observacion.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.text_observacion.setMinimumHeight(80)
        observacion_layout.addWidget(self.text_observacion)
        form_layout.addWidget(observacion_group, 8, 0, 1, 6)

        content_layout.addWidget(form_group)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_datos_extra = QToolButton()
        self.btn_datos_extra.setText("⋯")
        self.btn_datos_extra.setToolTip("Completar datos extra opcionales")
        self.btn_datos_extra.setCursor(Qt.PointingHandCursor)
        self.btn_datos_extra.setFixedSize(40, 36)
        self.btn_datos_extra.setStyleSheet(
            """
            QToolButton {
                background-color: white;
                color: #495057;
                border: 1px solid #d6dce5;
                border-radius: 4px;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
            }
            QToolButton:hover {
                background-color: #f5f8fc;
                border-color: #b8c7db;
            }
            QToolButton:pressed {
                background-color: #e9f0f8;
            }
        """
        )
        self.btn_datos_extra.clicked.connect(self._editar_datos_extra)
        btn_layout.addWidget(self.btn_datos_extra)

        self.btn_vender_montura = QPushButton("Seleccionar un Producto")
        self.btn_vender_montura.setToolTip("Seleccionar Producto para Agregar a la Venta")
        self.btn_vender_montura.setObjectName("successButton")
        self.btn_vender_montura.clicked.connect(self.seleccionar_producto)
        self.btn_vender_montura.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.btn_vender_montura.setStyleSheet(
            """
            QPushButton {
                background-color: #198754;
                color: white;
                border: none;
                padding: 0 16px;
                font-weight: 600;
                font-size: 13px;
                border-radius: 0px;
                min-height: 36px;
                max-height: 36px;
                min-width: 220px;
            }
            QPushButton:hover {
                background-color: #157347;
            }
            QPushButton:pressed {
                background-color: #11543b;
            }
        """
        )
        btn_layout.addWidget(self.btn_vender_montura)

        btn_motilidad = QPushButton("Motilidad")
        btn_motilidad.setToolTip("Abrir ventana de motilidad")
        btn_motilidad.clicked.connect(self.abrir_ventana_motilidad)
        btn_motilidad.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        btn_motilidad.setStyleSheet(
            """
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 0 16px;
                font-weight: 600;
                font-size: 13px;
                border-radius: 0px;
                min-height: 36px;
                max-height: 36px;
                min-width: 130px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
        """
        )
        btn_layout.addWidget(btn_motilidad)
        content_layout.addLayout(btn_layout)

        scroll_area.setWidget(content_widget)
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)
        self._update_comision_preview()
        self._update_multi_metodo_pago_grad_state()

        if self.parent_app is not None and hasattr(self.parent_app, "findChildren"):
            for widget in self.parent_app.findChildren(QtWidgets.QTableWidget):
                widget.verticalHeader().setDefaultSectionSize(54)

    def convertir_cliente_en_paciente(self):
        dialog = SeleccionarPacientesDialog(self, username=self.username, clientes_mode=True)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_dni = dialog.selected_dni
            if selected_dni:
                clientes = [c for c in dialog.all_pacientes if c["dni"] == selected_dni]
                if clientes:
                    cliente = clientes[0]
                    self.entry_dni.setText(cliente.get("dni", ""))
                    self.entry_paciente.setText(cliente.get("nombre", ""))
                    if cliente.get("fecha_nacimiento"):
                        birth_qdate = QDate.fromString(cliente["fecha_nacimiento"], "yyyy-MM-dd")
                        self.entry_fecha_nacimiento.setDate(birth_qdate)
                    if cliente.get("genero") == "Femenino":
                        self.genero_combo.setCurrentIndex(1)
                    else:
                        self.genero_combo.setCurrentIndex(0)
                    self.entry_fecha.setReadOnly(False)
                    QMessageBox.information(
                        self,
                        "Cliente Cargado",
                        "Datos del cliente cargados correctamente. Por favor, complete el formulario de graduacion.",
                    )

    def cargar_optometras_en_combo(self):
        self.optometra_combo.clear()
        optometras = cargar_optometras(self.username)
        for opto in optometras:
            self.optometra_combo.addItem(opto)
        if self.optometra_combo.count() == 0:
            self.optometra_combo.addItem("Sin Optometras")
            self.optometra_combo.setDisabled(True)
        else:
            self.optometra_combo.setDisabled(False)

    def toggle_proxima_cita_date(self, state):
        self.label_proxima_cita.setHidden(not state)
        self.entry_proxima_cita.setHidden(not state)
