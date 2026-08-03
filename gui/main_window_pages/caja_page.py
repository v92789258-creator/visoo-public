import os
import json
import datetime
import subprocess
import tempfile
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QGridLayout,
    QDateEdit, QMessageBox, QFrame, QScrollArea, QComboBox
)
from PyQt5.QtCore import Qt, QDate

from utils.file_handler import (
    get_user_file_path, cargar_ventas, cargar_caja, guardar_caja,
    cargar_configuracion_optica, open_pdf_with_chrome, get_effective_branch_context
)

class CajaPage(QWidget):
    def __init__(self, parent_app=None):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.username = getattr(parent_app, 'username', None)
        self.setObjectName("MainContent")
        
        # Inicializar interfaz
        self.init_ui()
        
    def init_ui(self):
        # Layout principal con scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
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
        """)

        content_widget = QWidget()
        content_widget.setStyleSheet("background: #FAFAFA;")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # --- HEADER ---
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_layout = QVBoxLayout()
        title = QLabel("Control de Caja Diaria")
        title.setStyleSheet("""
            font-size: 25px;
            color: #2C2C2C;
            font-weight: bold;
            margin: 0px;
            background: transparent;
        """)
        title.setAlignment(Qt.AlignLeft)
        
        subtitle = QLabel("Gestiona la apertura, ingresos y egresos de caja de forma diaria")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #6c757d;
            margin: 0px;
        """)
        subtitle.setAlignment(Qt.AlignLeft)
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # BotÃ³n para Imprimir Cierre
        self.btn_imprimir = QPushButton("ðŸ–¨ Imprimir Cierre (80mm)")
        self.btn_imprimir.setStyleSheet("""
            QPushButton {
                background: #0ea5e9;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                border: none;
                margin-right: 15px;
            }
            QPushButton:hover {
                background: #0284c7;
            }
            QPushButton:pressed {
                background: #0369a1;
            }
        """)
        self.btn_imprimir.clicked.connect(self.imprimir_cierre_caja)
        header_layout.addWidget(self.btn_imprimir)
        
        # Selector de Fecha
        date_container = QWidget()
        date_layout = QHBoxLayout(date_container)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(8)
        
        date_label = QLabel("Fecha de Caja:")
        date_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 12px;")
        
        self.date_edit = QLineEdit()
        self.date_edit.setText(QDate.currentDate().toString("dd/MM/yyyy"))
        self.date_edit.setPlaceholderText("dd/mm/aaaa")
        self.date_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                font-size: 12px;
                min-width: 120px;
            }
            QLineEdit:focus {
                border: 2px solid #0d6efd;
            }
        """)
        self.date_edit.returnPressed.connect(self.cargar_datos_caja)
        
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)

        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setToolTip("Recargar los datos de caja desde el archivo")
        self.btn_actualizar.setStyleSheet("""
            QPushButton {
                background: #6b7280;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background: #4b5563;
            }
            QPushButton:pressed {
                background: #374151;
            }
        """)
        self.btn_actualizar.clicked.connect(self.actualizar_caja)
        date_layout.addWidget(self.btn_actualizar)

        header_layout.addWidget(date_container)
        
        layout.addWidget(header)
        
        # --- CARDS DE RESUMEN ---
        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(16)
        
        # Tarjeta 1: Base/Apertura
        self.card_base = self.crear_card("Apertura (Base)", "S/. 0.00", "#6c757d", "#F8F9FA", is_editable=True)
        # Tarjeta 2: Ventas Efectivo (Ingresos)
        self.card_ingresos = self.crear_card("Ventas en Efectivo", "S/. 0.00", "#0284c7", "#F0F9FF")
        # Tarjeta 3: Otros Ingresos (Manuales)
        self.card_otros_ingresos = self.crear_card("Otros Ingresos", "S/. 0.00", "#0d9488", "#F0FDFA")
        # Tarjeta 4: Gastos (Egresos)
        self.card_egresos = self.crear_card("Gastos del DÃ­a", "S/. 0.00", "#ef4444", "#FEE2E2")
        # Tarjeta 5: Deudas del DÃ­a
        self.card_deudas = self.crear_card("Deudas del DÃ­a", "S/. 0.00", "#ea580c", "#FFF7ED")
        # Tarjeta 6: Saldo Final
        self.card_saldo = self.crear_card("Saldo en Caja", "S/. 0.00", "#10b981", "#D1FAE5")
        
        summary_layout.addWidget(self.card_base)
        summary_layout.addWidget(self.card_ingresos)
        summary_layout.addWidget(self.card_otros_ingresos)
        summary_layout.addWidget(self.card_egresos)
        summary_layout.addWidget(self.card_deudas)
        summary_layout.addWidget(self.card_saldo)
        layout.addWidget(summary_widget)
        
        # --- SECCIÃ“N INFERIOR: MOVIMIENTOS ---
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(20)
        
        # Lado Izquierdo: Registrar Movimiento
        movimiento_form = QGroupBox("Registrar Movimiento de Caja")
        movimiento_form.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background: white;
                font-size: 13px;
                color: #2C2C2C;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0px 5px;
            }
        """)
        movimiento_layout = QVBoxLayout(movimiento_form)
        movimiento_layout.setSpacing(12)
        
        lbl_tipo = QLabel("Tipo de Movimiento:")
        lbl_tipo.setStyleSheet("color: #495057; font-weight: bold; font-size: 11px;")
        
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItem("ðŸŸ¢ Ingreso Extra", "ingreso")
        self.cmb_tipo.addItem("ðŸ”´ Gasto / Egreso", "gasto")
        self.cmb_tipo.setStyleSheet("""
            QComboBox {
                padding: 8px 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                font-size: 12px;
            }
            QComboBox:focus {
                border: 2px solid #0d6efd;
            }
        """)
        self.cmb_tipo.currentTextChanged.connect(self.actualizar_color_boton_registro)
        
        lbl_concept = QLabel("Concepto / DescripciÃ³n:")
        lbl_concept.setStyleSheet("color: #495057; font-weight: bold; font-size: 11px;")
        self.txt_concept = QLineEdit()
        self.txt_concept.setPlaceholderText("Ej: Cobro de deuda sr. Juan / Compra de Ãºtiles...")
        self.txt_concept.setStyleSheet("""
            QLineEdit {
                padding: 8px 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #0d6efd;
            }
        """)
        
        lbl_monto = QLabel("Monto (S/.):")
        lbl_monto.setStyleSheet("color: #495057; font-weight: bold; font-size: 11px;")
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("0.00")
        self.txt_monto.setStyleSheet("""
            QLineEdit {
                padding: 8px 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #0d6efd;
            }
        """)
        
        self.btn_registrar = QPushButton("Registrar Movimiento")
        self.btn_registrar.setStyleSheet("""
            QPushButton {
                background: #10b981;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background: #059669;
            }
        """)
        self.btn_registrar.clicked.connect(self.registrar_movimiento)
        
        movimiento_layout.addWidget(lbl_tipo)
        movimiento_layout.addWidget(self.cmb_tipo)
        movimiento_layout.addWidget(lbl_concept)
        movimiento_layout.addWidget(self.txt_concept)
        movimiento_layout.addWidget(lbl_monto)
        movimiento_layout.addWidget(self.txt_monto)
        movimiento_layout.addWidget(self.btn_registrar)
        movimiento_layout.addStretch()
        
        bottom_layout.addWidget(movimiento_form, 1)
        
        # Lado Derecho: Tabla de Movimientos
        table_group = QGroupBox("Movimientos de Caja del DÃ­a")
        table_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background: white;
                font-size: 13px;
                color: #2C2C2C;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0px 5px;
            }
        """)
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(5, 15, 5, 5)
        
        self.table_movimientos = QTableWidget()
        self.table_movimientos.setColumnCount(5)
        self.table_movimientos.setHorizontalHeaderLabels(["Hora", "Tipo", "Concepto / DescripciÃ³n", "Monto", "AcciÃ³n"])
        self.table_movimientos.verticalHeader().setVisible(False)
        self.table_movimientos.setStyleSheet("""
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            QTableWidget::item:selected {
                background-color: #e7f1ff;
                color: #0d6efd;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: bold;
                color: #495057;
            }
        """)
        
        self.table_movimientos.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_movimientos.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table_movimientos.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_movimientos.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table_movimientos.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        
        self.table_movimientos.setColumnWidth(0, 95)
        self.table_movimientos.setColumnWidth(1, 110)
        self.table_movimientos.setColumnWidth(3, 110)
        self.table_movimientos.setColumnWidth(4, 110)
        self.table_movimientos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_movimientos.setSelectionBehavior(QTableWidget.SelectRows)
        
        table_layout.addWidget(self.table_movimientos)
        bottom_layout.addWidget(table_group, 2)
        
        layout.addWidget(bottom_container)
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Cargar los datos iniciales
        self.cargar_datos_caja()

    def _fecha_seleccionada_caja(self):
        texto = str(self.date_edit.text() or "").strip()
        if not texto:
            return QDate.currentDate().toString("dd/MM/yyyy")
        try:
            fecha_dt = datetime.datetime.strptime(texto, "%d/%m/%Y")
            return fecha_dt.strftime("%d/%m/%Y")
        except Exception:
            return QDate.currentDate().toString("dd/MM/yyyy")

    def _resolver_contexto_caja(self):
        usuario_madre = str(self.username or "").strip()
        branch_code = ""
        try:
            branch_ctx = get_effective_branch_context(self.username) or {}
            branch_code = str(branch_ctx.get("code", "") or "").strip().upper()
        except Exception:
            branch_code = ""

        try:
            cfg_path = get_user_file_path(self.username, "config_dispositivo.json")
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if isinstance(cfg, dict):
                    usuario_madre = str(cfg.get("usuario_madre", usuario_madre) or usuario_madre).strip()
                    if not branch_code:
                        branch_code = str(
                            cfg.get("codigo_dispositivo_hijo")
                            or cfg.get("codigo_dispositivo_trabajador")
                            or cfg.get("codigo_dispositivo")
                            or ""
                        ).strip().upper()
        except Exception:
            pass

        return usuario_madre, branch_code

    def _subir_caja_a_nube(self):
        try:
            from utils.api_handler import subir_dataset_dispositivo_nube
        except Exception as e:
            return False, f"No se pudo importar la API: {e}"

        if not self.username:
            return False, "Usuario no definido"

        usuario_madre, branch_code = self._resolver_contexto_caja()
        if not branch_code:
            return False, "No se pudo resolver la sucursal para sincronizar caja"

        caja_data = cargar_caja(self.username) or {}
        now_iso = datetime.datetime.now().isoformat(timespec="seconds")

        ok, msg, _resp = subir_dataset_dispositivo_nube(
            usuario_madre=usuario_madre,
            codigo_dispositivo=branch_code,
            dataset="caja",
            data=caja_data,
            operacion="SYNC_ALL",
            registro_id=f"bulk_caja_{branch_code}",
            contenido={"caja": caja_data},
            updated_at=now_iso,
        )
        if not ok:
            ok2, msg2, _resp2 = subir_dataset_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset="caja",
                data=caja_data,
                operacion="SYNC_ALL",
                registro_id=f"bulk_caja_{branch_code}",
                contenido={"caja": caja_data},
                updated_at=now_iso,
                endpoint_file="upload_device_snapshot_manual.php",
            )
            if ok2:
                return True, msg2
            return False, msg2 or msg
        return True, msg

    def actualizar_caja(self):
        """Recarga la caja local y fuerza la subida completa del archivo a la nube."""
        try:
            ok, msg = self._subir_caja_a_nube()
            if not ok:
                QMessageBox.warning(self, "Caja", f"No se pudo subir la caja a la nube: {msg}")
            self.cargar_datos_caja()
        except Exception as e:
            QMessageBox.critical(self, "Caja", f"No se pudo actualizar la caja: {e}")
        
    def crear_card(self, title, value, color, bg_color, is_editable=False):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1.5px solid {color};
                border-radius: 10px;
                padding: 12px 15px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #4b5563;")
        
        if is_editable:
            container = QWidget()
            layout_edit = QHBoxLayout(container)
            layout_edit.setContentsMargins(0, 0, 0, 0)
            layout_edit.setSpacing(5)
            
            self.txt_base_edit = QLineEdit()
            self.txt_base_edit.setText("500.00")
            self.txt_base_edit.setStyleSheet("""
                QLineEdit {
                    font-size: 20px;
                    font-weight: bold;
                    color: #2C2C2C;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background: white;
                    padding: 2px 5px;
                    max-width: 100px;
                }
            """)
            self.txt_base_edit.returnPressed.connect(self.guardar_base_caja)
            
            btn_save = QPushButton("âœ“")
            btn_save.setToolTip("Guardar base de caja para este dÃ­a")
            btn_save.setStyleSheet("""
                QPushButton {
                    background: #6c757d;
                    color: white;
                    font-weight: bold;
                    border-radius: 4px;
                    border: none;
                    min-width: 28px;
                    min-height: 28px;
                }
                QPushButton:hover { background: #5a6268; }
            """)
            btn_save.clicked.connect(self.guardar_base_caja)
            
            layout_edit.addWidget(self.txt_base_edit)
            layout_edit.addWidget(btn_save)
            layout_edit.addStretch()
            
            card_layout.addWidget(lbl_title)
            card_layout.addWidget(container)
        else:
            lbl_value = QLabel(value)
            lbl_value.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_value)
            
            if "Ventas" in title:
                self.lbl_val_ingresos = lbl_value
            elif "Otros" in title:
                self.lbl_val_otros_ingresos = lbl_value
            elif "Gastos" in title:
                self.lbl_val_egresos = lbl_value
            elif "Deudas" in title:
                self.lbl_val_deudas = lbl_value
            elif "Saldo" in title:
                self.lbl_val_saldo = lbl_value
                
        return card

    def obtener_monto_efectivo_real(self, sale):
        """
        Devuelve SOLO el dinero efectivo que realmente entrÃ³ a caja.
        Si la venta fue parcial, no suma el total de la venta: suma lo pagado.
        """
        try:
            total = float(sale.get("total", 0) or 0)
        except Exception:
            total = 0.0

        try:
            monto_pagado = float(sale.get("monto_pagado", 0) or 0)
        except Exception:
            monto_pagado = 0.0

        try:
            monto_faltante = float(sale.get("monto_faltante", 0) or 0)
        except Exception:
            monto_faltante = 0.0

        es_parcial = (
            bool(sale.get("es_pago_parcial", False))
            or bool(sale.get("es_pago_partes", False))
            or monto_faltante > 0
        )

        detalles = sale.get("metodos_pago_detalle")

        # Caso 1: venta con varios mÃ©todos de pago
        if isinstance(detalles, list) and detalles:
            efectivo = 0.0

            for item in detalles:
                if not isinstance(item, dict):
                    continue

                metodo = str(item.get("metodo", "")).strip().lower()

                if "efectivo" in metodo:
                    try:
                        efectivo += float(item.get("monto", 0) or 0)
                    except Exception:
                        pass

            # Blindaje: si es parcial, caja no puede recibir mÃ¡s que lo pagado
            if es_parcial and monto_pagado > 0:
                efectivo = min(efectivo, monto_pagado)

            return efectivo

        # Caso 2: venta con un solo mÃ©todo de pago
        metodo = str(sale.get("metodo_pago", "")).strip().lower()

        if "efectivo" not in metodo:
            return 0.0

        # Si fue parcial, entra solo lo pagado
        if es_parcial:
            if monto_pagado > 0:
                return monto_pagado

            return max(total - monto_faltante, 0.0)

        # Si no fue parcial, usar lo pagado; si no existe, reciÃ©n usar total
        return monto_pagado if monto_pagado > 0 else total


    def actualizar_color_boton_registro(self, text):
        if "Ingreso" in text:
            self.btn_registrar.setStyleSheet("""
                QPushButton {
                    background: #10b981;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 6px;
                    font-size: 12px;
                    border: none;
                }
                QPushButton:hover { background: #059669; }
            """)
        else:
            self.btn_registrar.setStyleSheet("""
                QPushButton {
                    background: #ef4444;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 6px;
                    font-size: 12px;
                    border: none;
                }
                QPushButton:hover { background: #dc2626; }
            """)

    def cargar_datos_caja(self):
        if not self.username:
            return
            
        fecha_seleccionada = self._fecha_seleccionada_caja()
        
        # 1. Calcular ingresos por ventas en efectivo y deudas del dÃ­a en tiempo real
        ventas_efectivo = 0.0
        deudas_total = 0.0
        ventas_movimientos = []
        try:
            ventas = cargar_ventas(self.username) or []
            for sale in ventas:
                if not isinstance(sale, dict):
                    continue
                fecha_venta = str(sale.get("fecha", "")).strip()
                if fecha_venta.startswith(fecha_seleccionada):
                    # Calcular deuda de esta venta
                    total_val = float(sale.get("total", 0) or 0)
                    es_pago_parcial = sale.get('es_pago_parcial', False) or sale.get('es_pago_partes', False)
                    monto_faltante = float(sale.get('monto_faltante', 0) or 0)
                    pagado = float(sale.get('monto_pagado', total_val) or total_val)
                    pendiente = monto_faltante if es_pago_parcial and monto_faltante > 0 else (total_val - pagado)
                    if pendiente > 0.05:
                        deudas_total += pendiente

 

                    
                    monto_efectivo = self.obtener_monto_efectivo_real(sale)

                    if monto_efectivo > 0.01:
                        ventas_efectivo += monto_efectivo
                        
                        # Extraer hora de la venta
                        hora_str = ""
                        if " " in fecha_venta:
                            parts = fecha_venta.split(" ")
                            if len(parts) >= 2:
                                hora_str = parts[1]
                        if not hora_str:
                            hora_str = "00:00:00"
                            
                        venta_id = str(sale.get("id", ""))
                        n_orden = str(sale.get("numero_orden", "")).strip()
                        contrato = str(sale.get("contrato_numero", "")).strip()
                        id_venta = f"ID: {venta_id}"
                        if contrato:
                            id_venta = f"Contrato: {contrato}"
                        elif n_orden:
                            id_venta = f"Orden: {n_orden}"
                            
                        cliente = str(sale.get("paciente_nombre", "Cliente GenÃ©rico")).strip()
                        concepto = f"Venta en efectivo ({id_venta}) - {cliente}"
                        
                        ventas_movimientos.append({
                            "hora": hora_str,
                            "tipo": "ingreso",
                            "tipo_interno": "venta",
                            "descripcion": concepto,
                            "monto": monto_efectivo,
                            "original_idx": -1
                        })
        except Exception as e:
            print(f"[CAJA] Error calculando ventas en efectivo: {e}")
            
        # Update labels
        self.lbl_val_ingresos.setText(f"S/. {ventas_efectivo:.2f}")
        self.lbl_val_deudas.setText(f"S/. {deudas_total:.2f}")
        
        # 2. Cargar Apertura (Base), Gastos e Ingresos Extras desde caja.json
        base_caja = 0.0
        gastos = []
        ingresos_extras = []
        
        try:
            data = cargar_caja(self.username) or {}
            caja_dia = data.get(fecha_seleccionada, {})
            if isinstance(caja_dia, dict):
                base_caja = float(caja_dia.get("base", 0.0))
                gastos = caja_dia.get("gastos", [])
                ingresos_extras = caja_dia.get("ingresos_extras", [])
        except Exception as e:
            print(f"[CAJA] Error leyendo caja: {e}")
                
        # Update UI Base
        self.txt_base_edit.setText(f"{base_caja:.2f}")
        
        # Calcular sumas de egresos y otros ingresos
        total_egresos = 0.0
        for gasto in gastos:
            if isinstance(gasto, dict):
                total_egresos += float(gasto.get("monto", 0.0) or 0.0)
                
        total_otros_ingresos = 0.0
        for ingreso in ingresos_extras:
            if isinstance(ingreso, dict):
                total_otros_ingresos += float(ingreso.get("monto", 0.0) or 0.0)
                
        self.lbl_val_egresos.setText(f"S/. {total_egresos:.2f}")
        self.lbl_val_otros_ingresos.setText(f"S/. {total_otros_ingresos:.2f}")
        
        # Calcular saldo final
        saldo_final = base_caja + ventas_efectivo + total_otros_ingresos - total_egresos
        self.lbl_val_saldo.setText(f"S/. {saldo_final:.2f}")
        
        # Unificar y ordenar movimientos para la tabla
        movimientos_unificados = []
        movimientos_unificados.extend(ventas_movimientos)
        
        for idx, g in enumerate(gastos):
            if isinstance(g, dict):
                movimientos_unificados.append({
                    "hora": g.get("hora", ""),
                    "tipo": "gasto",
                    "descripcion": g.get("descripcion", ""),
                    "monto": float(g.get("monto", 0.0) or 0.0),
                    "original_idx": idx
                })
                
        for idx, i in enumerate(ingresos_extras):
            if isinstance(i, dict):
                movimientos_unificados.append({
                    "hora": i.get("hora", ""),
                    "tipo": "ingreso",
                    "descripcion": i.get("descripcion", ""),
                    "monto": float(i.get("monto", 0.0) or 0.0),
                    "original_idx": idx
                })
                
        # Ordenar por hora (si la hora tiene formato standard)
        try:
            movimientos_unificados.sort(key=lambda x: x["hora"])
        except Exception:
            pass
            
        # Rellenar la tabla de transacciones
        self.table_movimientos.setRowCount(0)
        for row_idx, mov in enumerate(movimientos_unificados):
            self.table_movimientos.insertRow(row_idx)
            
            # Hora
            hora_item = QTableWidgetItem(str(mov["hora"]))
            hora_item.setTextAlignment(Qt.AlignCenter)
            self.table_movimientos.setItem(row_idx, 0, hora_item)
            
            # Tipo
            tipo_txt = "Ingreso" if mov["tipo"] == "ingreso" else "Gasto"
            tipo_color = "#10b981" if mov["tipo"] == "ingreso" else "#ef4444"
            tipo_item = QTableWidgetItem(tipo_txt)
            tipo_item.setTextAlignment(Qt.AlignCenter)
            tipo_item.setForeground(QBrush(QColor(tipo_color)))
            tipo_font = QFont()
            tipo_font.setBold(True)
            tipo_item.setFont(tipo_font)
            self.table_movimientos.setItem(row_idx, 1, tipo_item)
            
            # Concepto
            concepto_item = QTableWidgetItem(str(mov["descripcion"]))
            self.table_movimientos.setItem(row_idx, 2, concepto_item)
            
            # Monto
            signo = "+" if mov["tipo"] == "ingreso" else "-"
            monto_item = QTableWidgetItem(f"{signo} S/. {mov['monto']:.2f}")
            monto_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            monto_item.setForeground(QBrush(QColor(tipo_color)))
            monto_font = QFont()
            monto_font.setBold(True)
            monto_item.setFont(monto_font)
            self.table_movimientos.setItem(row_idx, 3, monto_item)
            
            # BotÃ³n Eliminar o indicador de venta inmutable
            if mov.get("tipo_interno") == "venta":
                lbl_inmutable = QLabel("Sistema")
                lbl_inmutable.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: bold; padding: 2px 6px;")
                container = QWidget()
                layout_btn = QHBoxLayout(container)
                layout_btn.setContentsMargins(2, 2, 2, 2)
                layout_btn.setAlignment(Qt.AlignCenter)
                layout_btn.addWidget(lbl_inmutable)
                container.setMinimumWidth(96)
                self.table_movimientos.setCellWidget(row_idx, 4, container)
            else:
                btn_eliminar = QPushButton("Eliminar")
                btn_eliminar.setMinimumWidth(72)
                btn_eliminar.setStyleSheet("""
                    QPushButton {
                        background: #ffebee;
                        color: #d32f2f;
                        border: 1px solid #ef5350;
                        border-radius: 4px;
                        font-size: 10px;
                        padding: 3px 5px;
                    }
                    QPushButton:hover {
                        background: #ffcdd2;
                    }
                """)
                btn_eliminar.clicked.connect(
                    lambda checked, t=mov["tipo"], o_idx=mov["original_idx"]: self.eliminar_movimiento(t, o_idx)
                )
                
                container = QWidget()
                layout_btn = QHBoxLayout(container)
                layout_btn.setContentsMargins(2, 2, 2, 2)
                layout_btn.setAlignment(Qt.AlignCenter)
                layout_btn.addWidget(btn_eliminar)
                container.setMinimumWidth(96)
                self.table_movimientos.setCellWidget(row_idx, 4, container)

    def guardar_base_caja(self):
        try:
            base_val = float(self.txt_base_edit.text().strip())
            if base_val < 0:
                QMessageBox.warning(self, "Valor invÃ¡lido", "La apertura de caja no puede ser negativa.")
                return
        except ValueError:
            QMessageBox.critical(self, "Error", "Ingrese un valor numÃ©rico vÃ¡lido para la apertura.")
            return
            
        fecha_seleccionada = self._fecha_seleccionada_caja()
        
        try:
            data = cargar_caja(self.username) or {}
            caja_dia = data.setdefault(fecha_seleccionada, {})
            caja_dia["base"] = base_val
            caja_dia.setdefault("gastos", [])
            caja_dia.setdefault("ingresos_extras", [])
            
            guardar_caja(self.username, data)
            
            # Recargar
            self.cargar_datos_caja()
            QMessageBox.information(self, "Apertura guardada", f"Se actualizÃ³ la base de caja de la fecha {fecha_seleccionada} a S/. {base_val:.2f} y se sincronizÃ³.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuraciÃ³n: {e}")

    def registrar_movimiento(self):
        tipo_mov = self.cmb_tipo.currentData()  # 'ingreso' o 'gasto'
        descripcion = self.txt_concept.text().strip()
        monto_str = self.txt_monto.text().strip()
        
        if not descripcion:
            QMessageBox.warning(self, "Falta descripciÃ³n", "Por favor, ingrese el concepto o descripciÃ³n del movimiento.")
            return
            
        if not monto_str:
            QMessageBox.warning(self, "Falta monto", "Por favor, ingrese el monto del movimiento.")
            return
            
        try:
            monto = float(monto_str)
            if monto <= 0:
                QMessageBox.warning(self, "Monto invÃ¡lido", "El monto debe ser mayor que cero.")
                return
        except ValueError:
            QMessageBox.critical(self, "Error", "Ingrese un monto numÃ©rico vÃ¡lido.")
            return
            
        fecha_seleccionada = self._fecha_seleccionada_caja()
        hora_actual = datetime.datetime.now().strftime("%I:%M %p")
        
        try:
            data = cargar_caja(self.username) or {}
            caja_dia = data.setdefault(fecha_seleccionada, {})
            caja_dia.setdefault("base", 0.0)
            
            if tipo_mov == "ingreso":
                ingresos = caja_dia.setdefault("ingresos_extras", [])
                ingresos.append({
                    "hora": hora_actual,
                    "descripcion": descripcion,
                    "monto": monto
                })
            else:
                gastos = caja_dia.setdefault("gastos", [])
                gastos.append({
                    "hora": hora_actual,
                    "descripcion": descripcion,
                    "monto": monto
                })
            
            guardar_caja(self.username, data)
                
            # Limpiar entradas
            self.txt_concept.clear()
            self.txt_monto.clear()
            
            # Recargar
            self.cargar_datos_caja()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar el movimiento: {e}")

    def eliminar_movimiento(self, tipo, original_idx):
        fecha_seleccionada = self._fecha_seleccionada_caja()
        
        try:
            data = cargar_caja(self.username) or {}
            caja_dia = data.get(fecha_seleccionada, {})
            if not caja_dia:
                return
            
            key = "ingresos_extras" if tipo == "ingreso" else "gastos"
            movimientos_list = caja_dia.get(key, [])
            
            if 0 <= original_idx < len(movimientos_list):
                mov = movimientos_list[original_idx]
                tipo_lbl = "Ingreso Extra" if tipo == "ingreso" else "Gasto"
                
                reply = QMessageBox.question(
                    self, "Confirmar eliminaciÃ³n",
                    f"Â¿EstÃ¡ seguro de que desea eliminar el {tipo_lbl.lower()}?\n\nConcepto: {mov.get('descripcion')}\nMonto: S/. {mov.get('monto'):.2f}",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    movimientos_list.pop(original_idx)
                    guardar_caja(self.username, data)
                    self.cargar_datos_caja()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar el movimiento: {e}")

    def imprimir_cierre_caja(self):
        """Genera un ticket de Cierre de Caja en PDF (80mm) y lo abre en Chrome para impresiÃ³n."""
        fecha_seleccionada = self._fecha_seleccionada_caja()
        
        # 1. Obtener datos de la caja
        base_caja = 0.0
        gastos = []
        ingresos_extras = []
        
        try:
            data = cargar_caja(self.username) or {}
            caja_dia = data.get(fecha_seleccionada, {})
            if isinstance(caja_dia, dict):
                base_caja = float(caja_dia.get("base", 0.0))
                gastos = caja_dia.get("gastos", [])
                ingresos_extras = caja_dia.get("ingresos_extras", [])
        except Exception:
            pass



            
        # Calcular ventas en efectivo
        ventas_efectivo = 0.0

        try:
            ventas = cargar_ventas(self.username) or []

            for sale in ventas:
                if not isinstance(sale, dict):
                    continue

                fecha_venta = str(sale.get("fecha", "")).strip()

                if fecha_venta.startswith(fecha_seleccionada):
                    ventas_efectivo += self.obtener_monto_efectivo_real(sale)

        except Exception:
            pass
            
        # Calcular totales
        total_egresos = sum(float(g.get("monto", 0.0) or 0.0) for g in gastos if isinstance(g, dict))
        total_otros_ingresos = sum(float(i.get("monto", 0.0) or 0.0) for i in ingresos_extras if isinstance(i, dict))
        saldo_final = base_caja + ventas_efectivo + total_otros_ingresos - total_egresos
        
        # Cargar datos de la Ã³ptica
        optica_cfg = cargar_configuracion_optica(self.username) or {}
        optica_name = str(optica_cfg.get("nombre", "Mi Ã“ptica")).strip().upper()
        direccion = str(optica_cfg.get("direccion", "DirecciÃ³n de la Ã“ptica")).strip()
        telefono = str(optica_cfg.get("telefono", "") or optica_cfg.get("whatsapp", "") or "").strip()
        
        # 2. Construir filas de transacciones en HTML
        filas_html = []
        
        # Unificar movimientos
        movs = []
        for g in gastos:
            if isinstance(g, dict):
                movs.append(("ðŸ”´ Egreso", g.get("descripcion", ""), float(g.get("monto", 0.0) or 0.0)))
        for i in ingresos_extras:
            if isinstance(i, dict):
                movs.append(("ðŸŸ¢ Ingreso", i.get("descripcion", ""), float(i.get("monto", 0.0) or 0.0)))
                
        for tipo, desc, monto in movs:
            filas_html.append(
                f"""
                <tr>
                  <td>{tipo}</td>
                  <td>{desc}</td>
                  <td style="text-align: right;">S/. {monto:.2f}</td>
                </tr>
                """
            )
            
        if not filas_html:
            filas_html.append('<tr><td colspan="3" style="text-align: center; color: #666;">Sin movimientos manuales hoy.</td></tr>')
            
        # 3. DiseÃ±o del HTML de Cierre de Caja (Ticket 80mm)
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Cierre de Caja - VISO</title>
    <style>
        @page {{
            size: 80mm auto;
            margin: 0;
        }}
        body {{
            font-family: 'Courier New', Courier, monospace;
            font-size: 11px;
            color: #000;
            margin: 0;
            padding: 8px;
            width: 72mm;
        }}
        .text-center {{
            text-align: center;
        }}
        .header {{
            border-bottom: 1px dashed #000;
            padding-bottom: 8px;
            margin-bottom: 8px;
        }}
        .header h2 {{
            margin: 2px 0;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .header p {{
            margin: 2px 0;
            font-size: 10px;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
        }}
        .summary-table td {{
            padding: 3px 0;
            font-size: 11px;
        }}
        .summary-table .label {{
            text-align: left;
        }}
        .summary-table .value {{
            text-align: right;
            font-weight: bold;
        }}
        .separator {{
            border-top: 1px dashed #000;
            margin: 6px 0;
        }}
        .section-title {{
            font-weight: bold;
            font-size: 11px;
            margin-top: 8px;
            margin-bottom: 4px;
            text-transform: uppercase;
        }}
        .details-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
        }}
        .details-table th {{
            border-bottom: 1px dashed #000;
            text-align: left;
            font-size: 10px;
            padding: 3px 0;
        }}
        .details-table td {{
            padding: 4px 0;
            font-size: 10px;
            vertical-align: top;
        }}
        .signature {{
            margin-top: 30px;
            text-align: center;
        }}
        .signature-line {{
            border-top: 1px dashed #000;
            width: 80%;
            margin: 0 auto;
            padding-top: 4px;
            font-size: 10px;
        }}
    </style>
</head>
<body>
    <div class="header text-center">
        <h2>{optica_name}</h2>
        {f"<p>{direccion}</p>" if direccion else ""}
        {f"<p>Telf: {telefono}</p>" if telefono else ""}
        <div class="separator"></div>
        <h3>CIERRE DE CAJA DIARIA</h3>
        <p><b>Fecha Caja:</b> {fecha_seleccionada}</p>
        <p><b>Impreso el:</b> {datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")}</p>
        <p><b>Cajero:</b> {self.username or "N/A"}</p>
    </div>

    <div class="section-title">Resumen de Caja</div>
    <table class="summary-table">
        <tr>
            <td class="label">(+) Apertura (Base):</td>
            <td class="value">S/. {base_caja:.2f}</td>
        </tr>
        <tr>
            <td class="label">(+) Ventas en Efectivo:</td>
            <td class="value">S/. {ventas_efectivo:.2f}</td>
        </tr>
        <tr>
            <td class="label">(+) Otros Ingresos:</td>
            <td class="value">S/. {total_otros_ingresos:.2f}</td>
        </tr>
        <tr>
            <td class="label">(-) Gastos / Egresos:</td>
            <td class="value">S/. {total_egresos:.2f}</td>
        </tr>
        <tr style="font-size: 12px; font-weight: bold;">
            <td class="label" style="padding-top: 6px;">(=) SALDO EN CAJA:</td>
            <td class="value" style="padding-top: 6px; border-top: 1px dashed #000;">S/. {saldo_final:.2f}</td>
        </tr>
    </table>

    <div class="separator"></div>
    <div class="section-title">Movimientos Manuales</div>
    <table class="details-table">
        <thead>
            <tr>
                <th style="width: 20mm;">Tipo</th>
                <th>Concepto</th>
                <th style="width: 20mm; text-align: right;">Monto</th>
            </tr>
        </thead>
        <tbody>
            {"".join(filas_html)}
        </tbody>
    </table>

    <div class="separator"></div>
    <div class="signature">
        <br><br>
        <div class="signature-line">Firma Cajero Responsable</div>
        <p style="font-size: 8px; color: #555; margin-top: 8px;">VISO Control de Caja Diaria</p>
    </div>
</body>
</html>
"""
        # 4. Compilar PDF con Chrome en segundo plano
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((path for path in chrome_paths if os.path.exists(path)), None)
        if not chrome_exe:
            QMessageBox.critical(self, "Error", "No se encontrÃ³ Google Chrome en el sistema para generar el PDF.")
            return

        try:
            # Crear directorio temporal para el proceso
            with tempfile.TemporaryDirectory(prefix="viso_cierre_caja_") as temp_dir:
                temp_html_path = os.path.join(temp_dir, "cierre_caja.html")
                fecha_pdf = self._fecha_seleccionada_caja().replace("/", "")
                pdf_output_path = os.path.join(tempfile.gettempdir(), f"cierre_caja_{fecha_pdf}.pdf")
                
                with open(temp_html_path, "w", encoding="utf-8") as temp_file:
                    temp_file.write(html_content)
                
                # Ejecutar compilaciÃ³n PDF mediante Chrome headless
                subprocess.run(
                    [
                        chrome_exe,
                        "--headless=new",
                        "--disable-gpu",
                        "--allow-file-access-from-files",
                        "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_output_path}",
                        temp_html_path
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30
                )
                
                # 5. Abrir PDF usando Chrome para su impresiÃ³n
                if os.path.exists(pdf_output_path):
                    open_pdf_with_chrome(pdf_output_path)
                else:
                    QMessageBox.critical(self, "Error", "El archivo PDF de cierre no pudo ser generado.")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"OcurriÃ³ un error al generar o abrir el Cierre de Caja:\n{e}")

