"""
Diálogo de opciones para una venta específica.
Refactorizado: Estilo Profesional / Enterprise.
"""

import os
import sys
import json
import threading
import time
import shutil
from pathlib import Path

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, 
    QApplication, QSpinBox, QGroupBox, QGridLayout, QStyle, QFrame
)
from PyQt5.QtCore import Qt

from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
from utils.printer_handler import print_boleta
from utils.file_handler import (
    cargar_nombre_optica,
    cargar_ruc,
    cargar_datos_generales,
    cargar_tamano_logo,
    cargar_configuracion_optica,
    cargar_pacientes,
    cargar_clientes,
    get_user_file_path,
    VISO_DIR,
)
from .printer_selection_dialog import PrinterSelectionDialog
from .browser_selection_dialog import BrowserSelectionDialog


class SaleOptionsDialog(QDialog):
    """Diálogo con opciones para gestionar una venta."""
    
    def __init__(self, sale_data, parent_username, parent=None, helper_name=None, is_helper=False):
        super().__init__(parent)
        self.sale_data = sale_data
        self.parent_username = parent_username
        self.helper_name = helper_name
        self.is_helper = is_helper
        self.receipt_width = 80  # Default
        
        # Configuración de ventana
        self.setWindowTitle("Gestión de Documento")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMaximumWidth(600)
         
         
        self.load_receipt_width()
        self.setup_ui()

    def _to_float_safe(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _get_associated_graduation_data(self):
        sale = self._get_normalized_sale_data()
        contrato = str(sale.get("contrato_numero", "") or "").strip()
        dni = str(sale.get("paciente_dni", "") or "").strip()
        if not dni:
            return {}
        try:
            pacientes = cargar_pacientes(self.parent_username) or []
            for pac in pacientes:
                if not isinstance(pac, dict):
                    continue
                if str(pac.get("dni", "")).strip() == dni:
                    historial = pac.get("historial_graduaciones", []) or []
                    for grad in historial:
                        if not isinstance(grad, dict):
                            continue
                        grad_contrato = str(grad.get("contrato_numero", "") or "").strip()
                        if contrato and grad_contrato == contrato:
                            return grad
                        grad_fecha = str(grad.get("fecha", "") or "").strip()
                        sale_fecha = str(sale.get("fecha", "") or "").strip()
                        if grad_fecha and sale_fecha and (grad_fecha in sale_fecha or sale_fecha in grad_fecha):
                            return grad
        except Exception as e:
            print(f"[ERROR] Error al buscar graduación asociada: {e}")
        return {}

    def _get_efectivo_recibido(self, sale):
        detalles = sale.get("metodos_pago_detalle") or []
        efectivo = 0.0
        if detalles:
            for item in detalles:
                if not isinstance(item, dict):
                    continue
                metodo = str(item.get("metodo", "") or "").strip().lower()
                monto = self._to_float_safe(item.get("monto", 0.0))
                if "efectivo" in metodo:
                    efectivo += monto
            return efectivo
        
        metodo = str(sale.get("metodo_pago", "") or "").strip().lower()
        if "efectivo" in metodo:
            total_venta = self._to_float_safe(sale.get("total", 0.0))
            monto_pagado = self._to_float_safe(sale.get("monto_pagado", total_venta))
            return monto_pagado
        
        return 0.0

    def _get_normalized_sale_data(self):
        sale = dict(self.sale_data or {}) if isinstance(self.sale_data, dict) else {}
        items = sale.get("items") or []
        if not isinstance(items, list):
            items = []
        sale["items"] = items

        is_graduacion = str(sale.get("origen", "") or "").strip().lower() == "graduacion" or str(sale.get("tipo_venta", "") or "").strip().lower() == "graduacion"
        if not is_graduacion or not items:
            return sale

        service_index = None
        service_total = 0.0
        productos_total = 0.0

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            nombre_item = str(item.get("nombre") or item.get("producto") or "").strip().lower()
            total_item = self._to_float_safe(
                item.get("total", item.get("subtotal", item.get("precio_unitario", item.get("precio", 0)))),
                0.0,
            )
            if "servicio de gradu" in nombre_item:
                service_index = index
                service_total += total_item
            else:
                productos_total += total_item

        total_guardado = self._to_float_safe(sale.get("total", 0), 0.0)

        if service_index is not None and productos_total > 0.01 and total_guardado > 0.01:
            computed_total = service_total + productos_total
            if abs(computed_total - total_guardado) <= 0.05 and service_total < total_guardado:
                corrected_service = max(0.0, total_guardado - productos_total)
                corrected_total = corrected_service + productos_total

                fixed_items = []
                for index, item in enumerate(items):
                    if not isinstance(item, dict):
                        fixed_items.append(item)
                        continue
                    new_item = dict(item)
                    if index == service_index:
                        new_item["precio_unitario"] = corrected_service
                        new_item["subtotal"] = corrected_service
                        new_item["total"] = corrected_service
                    else:
                        item_total = self._to_float_safe(
                            new_item.get("total", new_item.get("subtotal", new_item.get("precio_unitario", new_item.get("precio", 0)))),
                            0.0,
                        )
                        new_item["subtotal"] = item_total
                        new_item["total"] = item_total
                    fixed_items.append(new_item)

                sale["items"] = fixed_items
                sale["total"] = corrected_total
                sale["subtotal"] = round(corrected_total / 1.18, 2)
                sale["igv"] = round(corrected_total - sale["subtotal"], 2)

                monto_pagado = self._to_float_safe(sale.get("monto_pagado", total_guardado), total_guardado)
                monto_faltante = self._to_float_safe(sale.get("monto_faltante", 0), 0.0)
                if monto_faltante <= 0.05 and monto_pagado >= total_guardado:
                    sale["monto_pagado"] = corrected_total

        return sale
    
    def setup_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 1. Sección de Información (GroupBox)
        info_box = QGroupBox("Detalles de la Operación")
        info_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                font-weight: normal;
                color: #333333;
            }
        """)
        
        grid_layout = QGridLayout(info_box)
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(8)
        
        # Filas de datos
        sale_data = self._get_normalized_sale_data()

        self.add_info_row(grid_layout, 0, "Fecha de Emisión:", sale_data.get('fecha', '-'))
        self.add_info_row(grid_layout, 0, "DNI / RUC:", sale_data.get('paciente_dni', '-'), col_offset=2)
        
        self.add_info_row(grid_layout, 1, "Método de Pago:", sale_data.get('metodo_pago', '-'))
        
        # Vendedor/Trabajador: priorizar la opt?metra cuando la venta venga de graduaci?n.
        vendedor = (
            sale_data.get('optometra')
            or sale_data.get('vendedor')
            or sale_data.get('helper_name')
            or '-'
        )
        self.add_info_row(grid_layout, 1, "Vendedor:", vendedor, col_offset=2)
        
        # Total destacado
        lbl_total_title = QLabel("Importe Total:")
        lbl_total_title.setStyleSheet("font-weight: bold;")
        lbl_total_val = QLabel(f"S/ {self._to_float_safe(sale_data.get('total', 0), 0.0):.2f}")
        lbl_total_val.setStyleSheet("font-weight: bold; color: #000000;")
        
        grid_layout.addWidget(lbl_total_title, 2, 0)
        grid_layout.addWidget(lbl_total_val, 2, 1)
        
        # Calcular deuda (Debe)
        try:
            total_venta = float(sale_data.get('total', 0) or 0)
            # Si no existe monto_pagado, asumir total (pagado) por defecto
            monto_pagado = float(sale_data.get('monto_pagado', total_venta) or 0)
            monto_faltante = float(sale_data.get('monto_faltante', 0) or 0)
            
            # Usar lógica robusta: si hay faltante explícito o calculado
            pendiente = total_venta - monto_pagado
            if monto_faltante > 0:
                pendiente = monto_faltante
            
            if pendiente > 0.05:
                lbl_debe_title = QLabel("Debe:")
                lbl_debe_title.setStyleSheet("font-weight: bold; color: #D32F2F;")
                lbl_debe_val = QLabel(f"S/ {pendiente:.2f}")
                lbl_debe_val.setStyleSheet("font-weight: bold; color: #D32F2F;")
                
                grid_layout.addWidget(lbl_debe_title, 2, 2)
                grid_layout.addWidget(lbl_debe_val, 2, 3)
        except Exception:
            pass
        
        # Costo Luna y Total en Caja si proviene de Graduación
        is_graduacion = (
            str(sale_data.get("origen", "") or "").strip().lower() == "graduacion" or 
            str(sale_data.get("tipo_venta", "") or "").strip().lower() == "graduacion"
        )
        if is_graduacion:
            grad_data = self._get_associated_graduation_data()
            costo_luna = self._to_float_safe(
                grad_data.get("luna_costo") or sale_data.get("luna_costo", 0.0), 
                0.0
            )
            efectivo_recibido = self._get_efectivo_recibido(sale_data)
            if efectivo_recibido <= 0.0:
                total_en_caja = 0.0
            else:
                total_en_caja = max(0.0, efectivo_recibido - costo_luna)
            
            lbl_costo_luna_title = QLabel("Costo Luna:")
            lbl_costo_luna_title.setStyleSheet("font-weight: bold;")
            lbl_costo_luna_val = QLabel(f"S/ {costo_luna:.2f}")
            lbl_costo_luna_val.setStyleSheet("color: #000000;")
            
            lbl_caja_title = QLabel("Total en Caja:")
            lbl_caja_title.setStyleSheet("font-weight: bold; color: #2E7D32;")
            lbl_caja_val = QLabel(f"S/ {total_en_caja:.2f}")
            lbl_caja_val.setStyleSheet("font-weight: bold; color: #2E7D32;")
            
            grid_layout.addWidget(lbl_costo_luna_title, 3, 0)
            grid_layout.addWidget(lbl_costo_luna_val, 3, 1)
            grid_layout.addWidget(lbl_caja_title, 3, 2)
            grid_layout.addWidget(lbl_caja_val, 3, 3)

        layout.addWidget(info_box)
        
        # 2. Configuración (Ancho de papel)
        config_layout = QHBoxLayout()
        config_layout.setContentsMargins(5, 0, 5, 0)
        
        lbl_size = QLabel("Formato de impresión (ancho):")
        self.spinbox_size = QSpinBox()
        self.spinbox_size.setRange(30, 200)
        self.spinbox_size.setValue(self.receipt_width)
        self.spinbox_size.setSuffix(" mm")
        self.spinbox_size.setFixedWidth(100)
        self.spinbox_size.valueChanged.connect(self.on_size_changed)
        
        config_layout.addWidget(lbl_size)
        config_layout.addWidget(self.spinbox_size)
        config_layout.addStretch()
        
        layout.addLayout(config_layout)
        
        # Línea separadora
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #dcdcdc;")
        layout.addWidget(line)
        
        # 3. Botones de Acción
        # Usamos iconos nativos del sistema para un look profesional
        
        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(8)

        # Botón Ver PDF
        self.btn_view = self.create_button("Visualizar Documento", QStyle.SP_FileDialogInfoView)
        self.btn_view.clicked.connect(self.view_boleta)
        btns_layout.addWidget(self.btn_view)

        # Botón Navegador
        self.btn_browser = self.create_button("Abrir en Navegador Externo", QStyle.SP_DriveNetIcon)
        self.btn_browser.clicked.connect(self.view_boleta_in_browser)
        btns_layout.addWidget(self.btn_browser)

        # Botón Descargar
        self.btn_download = self.create_button("Guardar Copia Digital", QStyle.SP_DialogSaveButton)
        self.btn_download.clicked.connect(self.download_boleta)
        btns_layout.addWidget(self.btn_download)

        # Botón Imprimir (Destacado)
        self.btn_print = self.create_button("Imprimir Comprobante", QStyle.SP_DialogOkButton, is_primary=True)
        self.btn_print.clicked.connect(self.print_boleta)
        btns_layout.addWidget(self.btn_print)
        self.btn_print_full = self.create_button("Comprobante Completo", QStyle.SP_FileDialogDetailedView)
        self.btn_print_full.clicked.connect(self.print_boleta_completa)
        btns_layout.addWidget(self.btn_print_full)

        # Botón Enviar a SUNAT
        self.btn_send_sunat = self.create_button("Enviar Boleta a SUNAT", QStyle.SP_ArrowUp)
        self.btn_send_sunat.clicked.connect(self.send_boleta_sunat)
        btns_layout.addWidget(self.btn_send_sunat)
        
        layout.addLayout(btns_layout)
        
        # Botón Cerrar (pie de página)
        layout.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.setFixedWidth(100)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0; 
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        btn_close.clicked.connect(self.accept)
        
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        footer_layout.addWidget(btn_close)
        layout.addLayout(footer_layout)

    def add_info_row(self, layout, row, label_text, value_text, col_offset=0):
        """Helper para añadir filas a la grilla de información."""
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #555555;")
        val = QLabel(str(value_text))
        val.setStyleSheet("color: #000000;")
        layout.addWidget(lbl, row, 0 + col_offset)
        layout.addWidget(val, row, 1 + col_offset)

    def create_button(self, text, icon_enum, is_primary=False):
        """Crea un botón con estilo estandarizado."""
        btn = QPushButton(text)
        btn.setIcon(self.style().standardIcon(icon_enum))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(35)
        
        if is_primary:
            # Estilo sobrio para la acción principal (Azul oscuro / Gris oscuro)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2c3e50;
                    color: white;
                    border: 1px solid #2c3e50;
                    border-radius: 3px;
                    font-weight: bold;
                    text-align: left;
                    padding-left: 15px;
                }
                QPushButton:hover { background-color: #34495e; }
                QPushButton:pressed { background-color: #1a252f; }
            """)
        else:
            # Estilo estándar para acciones secundarias
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    text-align: left;
                    padding-left: 15px;
                }
                QPushButton:hover { 
                    background-color: #f5f5f5; 
                    border-color: #999999;
                }
                QPushButton:pressed { background-color: #e6e6e6; }
            """)
        return btn

    # ----------------------------------------------------------------------
    # LÓGICA DE NEGOCIO (Sin cambios funcionales, solo limpieza)
    # ----------------------------------------------------------------------

    def load_receipt_width(self):
        try:
            config_path = self._get_config_file()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.receipt_width = config.get('receipt_width', 80)
            else:
                self.receipt_width = 80
        except Exception:
            self.receipt_width = 80
    
    def on_size_changed(self, value):
        self.receipt_width = value
        self._save_receipt_width()
    
    def _get_config_file(self):
        user_dir = VISO_DIR / self.parent_username
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, '.receipt_config.json')
    
    def _save_receipt_width(self):
        try:
            config_path = self._get_config_file()
            config = {'receipt_width': self.receipt_width}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando configuración: {e}")
    
    def _generate_boleta_pdf(self):
        try:
            generador = GeneradorBoletasPlantilla(self.parent_username)
            datos_generales = cargar_datos_generales(self.parent_username) or {}

            sale_data = self._get_normalized_sale_data()
            if not isinstance(sale_data, dict):
                raise Exception("Datos de venta inválidos para generar PDF.")

            def _to_float(value, default=0.0):
                try:
                    return float(value)
                except Exception:
                    return default
            
            ruc = datos_generales.get('ruc', '')
            if not ruc:
                ruc = cargar_ruc(self.parent_username)
            
            razon_social = datos_generales.get('razon_social', cargar_nombre_optica(self.parent_username))
            direccion = datos_generales.get('direccion', '')
            
            # Cargar tamaño del logo configurado por el usuario
            tamano_logo_px = cargar_tamano_logo(self.parent_username)
            
            productos = []
            
            # Usar el total guardado en la venta (ya incluye IGV correctamente)
            total_con_igv = _to_float(sale_data.get('total', 0), 0.0)
            
            items = sale_data.get('items') or []
            if not isinstance(items, (list, tuple)):
                items = []

            for item in items:
                if not isinstance(item, dict):
                    continue
                # El precio_unitario es el TOTAL CON IGV
                precio_unitario = _to_float(item.get('precio_unitario', item.get('precio', 0)), 0.0)
                cantidad = _to_float(item.get('cantidad', 1), 1.0)
                total_item = _to_float(item.get('total', 0), 0.0)
                if total_item <= 0:
                    total_item = precio_unitario * cantidad
                
                productos.append({
                    'nombre': item.get('nombre', item.get('producto', 'Item')),
                    'cantidad': cantidad,
                    'precio': precio_unitario,
                    'total': total_item
                })

            # Si no hay items válidos, crear un ítem placeholder para evitar PDFs vacíos/errores en A4
            if not productos and total_con_igv > 0:
                productos = [{
                    'nombre': sale_data.get('descripcion', sale_data.get('detalle', 'Venta')),
                    'cantidad': 1,
                    'precio': total_con_igv,
                    'total': total_con_igv
                }]
            
            # Calcular subtotal y IGV a partir del total guardado
            subtotal_base = total_con_igv / 1.18
            igv = total_con_igv - subtotal_base
            
            # Determinar vendedor (priorizar dato histórico de la venta)
            vendedor_nombre = sale_data.get('vendedor')
            if not vendedor_nombre:
                vendedor_nombre = sale_data.get('helper_name')
            
            # Fallback al contexto actual si no hay datos históricos
            if not vendedor_nombre:
                vendedor_nombre = self.helper_name if self.helper_name else self.parent_username
            
            # Calcular datos de pago y deuda para la boleta
            monto_pagado = _to_float(sale_data.get('monto_pagado', total_con_igv) or 0, 0.0)
            monto_faltante = _to_float(sale_data.get('monto_faltante', 0) or 0, 0.0)
            es_pago_parcial = sale_data.get('es_pago_parcial', False) or sale_data.get('es_pago_partes', False)
            
            # Si hay deuda evidente, forzar flag de pago parcial para que se muestre en boleta
            if (total_con_igv - monto_pagado) > 0.05 or monto_faltante > 0:
                es_pago_parcial = True

            datos_boleta = {
                'nombre_optica': razon_social,
                'ruc': ruc,
                'direccion': direccion,
                'numero_boleta': f"VIS-{sale_data.get('id', 'S/N'):010d}" if isinstance(sale_data.get('id'), int) else f"VIS-{sale_data.get('id', 'S/N')}",
                'fecha': sale_data.get('fecha', ''),
                'cliente': sale_data.get('paciente_nombre', 'Cliente'),
                'productos': productos,
                'subtotal': subtotal_base,
                'igv': igv,
                'total': total_con_igv,
                'metodo_pago': sale_data.get('metodo_pago', 'Efectivo'),
                'pie_pagina': 'Gracias por su preferencia',
                'vendedor': vendedor_nombre,
                'helper_name': self.helper_name,
                'es_pago_parcial': es_pago_parcial,
                'monto_pagado': monto_pagado,
                'monto_faltante': monto_faltante
            }
            
            return generador.generar_boleta(datos_boleta, tamano_logo_px=tamano_logo_px)
        except Exception as e:
            raise Exception(f"Fallo en generación de PDF: {e}")
    
    def _generate_full_receipt_pdf(self):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

            sale_data = self._get_normalized_sale_data()
            if not isinstance(sale_data, dict):
                raise Exception("Datos de venta inválidos para generar el comprobante completo.")

            def txt(value, fallback=""):
                value = str(value or "").strip()
                return value if value else fallback

            def money(value):
                try:
                    return f"S/ {float(value or 0):.2f}"
                except Exception:
                    return "S/ 0.00"

            def format_order_number(value):
                digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
                if not digits:
                    return ""
                return digits.zfill(4) if len(digits) < 4 else digits

            datos_generales = cargar_datos_generales(self.parent_username) or {}
            optica_cfg = cargar_configuracion_optica(self.parent_username) or {}
            nombre_optica = txt(cargar_nombre_optica(self.parent_username), "Mi Óptica")
            slogan_optica = txt(optica_cfg.get("slogan"))
            direccion_optica = txt(optica_cfg.get("direccion") or datos_generales.get("direccion"))
            correo_optica = txt(optica_cfg.get("correo_electronico"))

            telefono_optica = ""
            try:
                whatsapp_json_path = get_user_file_path(self.parent_username, "whatsapp.json")
                if whatsapp_json_path.exists():
                    with open(whatsapp_json_path, "r", encoding="utf-8") as f:
                        whatsapp_data = json.load(f)
                    if isinstance(whatsapp_data, dict):
                        telefono_optica = txt(whatsapp_data.get("whatsapp"))
            except Exception:
                telefono_optica = ""

            paciente_dni = txt(sale_data.get("paciente_dni"))
            paciente_nombre = txt(sale_data.get("paciente_nombre"), "Cliente Genérico")
            paciente_tel = ""
            paciente_dir = ""
            paciente = None
            try:
                source = cargar_pacientes(self.parent_username) or []
                paciente = next((p for p in source if isinstance(p, dict) and txt(p.get("dni")) == paciente_dni), None)
                if paciente is None:
                    source = cargar_clientes(self.parent_username) or []
                    paciente = next((p for p in source if isinstance(p, dict) and txt(p.get("dni")) == paciente_dni), None)
                if isinstance(paciente, dict):
                    paciente_tel = txt(paciente.get("telefono"))
                    paciente_dir = txt(paciente.get("direccion"))
            except Exception:
                paciente_tel = ""
                paciente_dir = ""

            vendedor = (
                txt(sale_data.get("vendedor"))
                or txt(sale_data.get("optometra"))
                or txt(sale_data.get("helper_name"))
                or txt(sale_data.get("usuario"))
                or txt(self.helper_name)
                or txt(self.parent_username)
            )
            numero_orden = format_order_number(sale_data.get("numero_orden"))
            fecha = txt(sale_data.get("fecha"))
            metodo_pago = txt(sale_data.get("metodo_pago"), "Efectivo")
            observacion = txt(sale_data.get("observacion"), "Venta registrada en sistema")
            total = float(sale_data.get("total", 0) or 0)
            monto_pagado = float(sale_data.get("monto_pagado", total) or 0)
            saldo = float(sale_data.get("monto_faltante", max(0.0, total - monto_pagado)) or 0)
            acuenta = monto_pagado if saldo > 0.05 else total

            styles = getSampleStyleSheet()
            products_rows = [[
                Paragraph("<b>Código</b>", styles["BodyText"]),
                Paragraph("<b>Descripción</b>", styles["BodyText"]),
                Paragraph("<b>Marca</b>", styles["BodyText"]),
                Paragraph("<b>Cant.</b>", styles["BodyText"]),
                Paragraph("<b>P.Unit</b>", styles["BodyText"]),
                Paragraph("<b>Total</b>", styles["BodyText"]),
            ]]
            total_items = 0.0
            for item in sale_data.get("items") or []:
                if not isinstance(item, dict):
                    continue
                cantidad = float(item.get("cantidad", 1) or 1)
                total_items += cantidad
                products_rows.append([
                    Paragraph(txt(item.get("codigo"), "-"), styles["BodyText"]),
                    Paragraph(txt(item.get("nombre"), "Producto"), styles["BodyText"]),
                    Paragraph(txt(item.get("marca"), "-"), styles["BodyText"]),
                    Paragraph(str(int(cantidad) if float(cantidad).is_integer() else cantidad), styles["BodyText"]),
                    Paragraph(money(item.get("precio_unitario", item.get("precio", 0))), styles["BodyText"]),
                    Paragraph(money(item.get("total", 0)), styles["BodyText"]),
                ])
            if len(products_rows) == 1:
                products_rows.append([
                    Paragraph("-", styles["BodyText"]),
                    Paragraph(txt(sale_data.get("detalle"), "Venta"), styles["BodyText"]),
                    Paragraph("-", styles["BodyText"]),
                    Paragraph("1", styles["BodyText"]),
                    Paragraph(money(total), styles["BodyText"]),
                    Paragraph(money(total), styles["BodyText"]),
                ])

            navy = colors.HexColor("#23395B")
            blue = colors.HexColor("#2158B7")
            line = colors.HexColor("#C9D7F0")
            soft = colors.HexColor("#F7FAFF")
            red = colors.HexColor("#BA3D3D")
            gray = colors.HexColor("#6B7280")

            styles.add(ParagraphStyle(name="CompTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=30, leading=32, textColor=navy, alignment=1))
            styles.add(ParagraphStyle(name="CompSub", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=12, textColor=gray, alignment=1))
            styles.add(ParagraphStyle(name="BoxTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=20, textColor=blue, alignment=1))
            styles.add(ParagraphStyle(name="BoxSeries", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=11, textColor=gray, alignment=1))
            styles.add(ParagraphStyle(name="BoxNumber", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=18, textColor=red, alignment=1))
            styles.add(ParagraphStyle(name="SectionHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=navy))
            styles.add(ParagraphStyle(name="LineLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=11, textColor=blue))
            styles.add(ParagraphStyle(name="LineValue", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=11, textColor=colors.black))

            def p(text, style_name):
                return Paragraph(str(text or "&nbsp;"), styles[style_name])

            def line_field(label, value, widths, label_align="LEFT", value_align="LEFT"):
                table = Table([[p(label, "LineLabel"), p(value or "&nbsp;", "LineValue")]], colWidths=widths)
                table.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ("ALIGN", (0, 0), (0, 0), label_align),
                    ("ALIGN", (1, 0), (1, 0), value_align),
                    ("LINEBELOW", (1, 0), (1, 0), 0.6, line),
                ]))
                return table

            temp_dir = str(VISO_DIR / str(self.parent_username) / "temp")
            os.makedirs(temp_dir, exist_ok=True)
            venta_id = txt(sale_data.get("id"), "tmp")
            pdf_path = os.path.join(temp_dir, f"comprobante_completo_{venta_id}.pdf")

            doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=8 * mm, rightMargin=8 * mm, topMargin=8 * mm, bottomMargin=8 * mm)

            def draw_page_frame(canvas, doc_obj):
                canvas.saveState()
                canvas.setStrokeColor(colors.HexColor("#4B9FFF"))
                canvas.setLineWidth(3.2)
                frame_pad = 2 * mm
                canvas.rect(doc_obj.leftMargin - frame_pad, doc_obj.bottomMargin - frame_pad, A4[0] - doc_obj.leftMargin - doc_obj.rightMargin + (frame_pad * 2), A4[1] - doc_obj.topMargin - doc_obj.bottomMargin + (frame_pad * 2))
                canvas.restoreState()

            contract_footer = Table([[p("0001", "BoxSeries"), p(f"N°&nbsp;&nbsp;{txt(numero_orden, '0001')}", "BoxNumber")]], colWidths=[14 * mm, 42 * mm], rowHeights=[8 * mm])
            contract_footer.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            contract_box = Table([[p("COMPROBANTE", "BoxTitle")], [contract_footer]], colWidths=[56 * mm], rowHeights=[10 * mm, 10 * mm])
            contract_box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, blue), ("LINEBELOW", (0, 0), (-1, 0), 1, blue), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

            story = []
            header = Table([[[p(nombre_optica, "CompTitle"), Spacer(1, 1.2 * mm), p(slogan_optica or "&nbsp;", "CompSub"), p(direccion_optica or "&nbsp;", "CompSub"), p(correo_optica or "&nbsp;", "CompSub"), p(telefono_optica or "&nbsp;", "CompSub")]], [contract_box]], colWidths=[194 * mm])
            header.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, 0), (-1, 0), 10), ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 1), (-1, 1), 0), ("ALIGN", (0, 0), (-1, 0), "CENTER"), ("ALIGN", (0, 1), (-1, 1), "RIGHT")]))
            story.append(header)
            story.append(Spacer(1, 3 * mm))

            row_1 = Table([[line_field("FECHA:", fecha, [18 * mm, 46 * mm]), line_field("N° ORDEN:", numero_orden, [22 * mm, 42 * mm])]], colWidths=[97 * mm, 97 * mm])
            row_1.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
            story.append(row_1)
            story.append(Spacer(1, 1.5 * mm))
            row_2 = Table([[line_field("Señor (es):", paciente_nombre, [25 * mm, 104 * mm]), line_field("Telf:", paciente_tel, [12 * mm, 53 * mm])]], colWidths=[129 * mm, 65 * mm])
            row_2.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
            story.append(row_2)
            story.append(Spacer(1, 1.5 * mm))
            story.append(line_field("Dirección:", paciente_dir, [22 * mm, 172 * mm]))
            story.append(Spacer(1, 1.5 * mm))
            row_3 = Table([[line_field("DNI / RUC:", paciente_dni, [22 * mm, 48 * mm]), line_field("MÉTODO:", metodo_pago, [20 * mm, 44 * mm]), line_field("VENDEDOR:", vendedor, [22 * mm, 38 * mm])]], colWidths=[70 * mm, 64 * mm, 60 * mm])
            row_3.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
            story.append(row_3)
            story.append(Spacer(1, 5 * mm))

            items_header = Table([[p("DETALLE DEL COMPROBANTE", "SectionHeader")]], colWidths=[194 * mm])
            items_header.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), soft), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("BOX", (0, 0), (-1, -1), 0.6, line)]))
            story.append(items_header)
            story.append(Spacer(1, 1 * mm))

            products_table = Table(products_rows, colWidths=[24 * mm, 70 * mm, 28 * mm, 16 * mm, 26 * mm, 30 * mm])
            products_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.white), ("TEXTCOLOR", (0, 0), (-1, 0), blue), ("BOX", (0, 0), (-1, -1), 0.8, line), ("INNERGRID", (0, 0), (-1, -1), 0.6, line), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (3, 1), (-1, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story.append(products_table)
            story.append(Spacer(1, 4 * mm))

            summary_header = Table([[p("RESUMEN", "SectionHeader")]], colWidths=[194 * mm])
            summary_header.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), soft), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("BOX", (0, 0), (-1, -1), 0.6, line)]))
            story.append(summary_header)
            story.append(Spacer(1, 1 * mm))
            story.append(line_field("Artículos:", str(int(total_items or 0)), [18 * mm, 30 * mm]))
            story.append(Spacer(1, 1.5 * mm))
            story.append(line_field("Observación:", observacion, [24 * mm, 170 * mm]))
            story.append(Spacer(1, 1.5 * mm))
            summary = Table([[line_field("TOTAL:", money(total), [18 * mm, 44 * mm]), line_field("A CTA:", money(acuenta), [18 * mm, 44 * mm]), line_field("SALDO:", money(saldo), [18 * mm, 44 * mm])]], colWidths=[64 * mm, 64 * mm, 66 * mm])
            summary.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            story.append(summary)

            doc.build(story, onFirstPage=draw_page_frame, onLaterPages=draw_page_frame)
            return pdf_path
        except Exception as e:
            raise Exception(f"No se pudo generar el comprobante completo: {e}")

    def view_boleta(self):
        try:
            pdf_path = self._generate_boleta_pdf()
            from .pdf_viewer_dialog import PDFViewerDialog
            viewer = PDFViewerDialog(pdf_path, self)
            viewer.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def view_boleta_in_browser(self):
        try:
            pdf_path = self._generate_boleta_pdf()
            success = BrowserSelectionDialog.open_file_in_browser(pdf_path, self)
            if success:
                QMessageBox.information(self, "Información", "Documento abierto en navegador.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def download_boleta(self):
        try:
            pdf_path = self._generate_boleta_pdf()
            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            filename = os.path.basename(pdf_path)
            dest_path = downloads_dir / filename
            
            shutil.copy2(pdf_path, dest_path)
            try:
                QtCore.QTimer.singleShot(
                    0,
                    lambda p=str(dest_path): QtGui.QDesktopServices.openUrl(
                        QtCore.QUrl.fromLocalFile(p)
                    )
                )
            except Exception:
                pass
            
            QMessageBox.information(self, "Descarga Completa", f"Archivo guardado en:\n{dest_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error de Descarga", str(e))
    
    def print_boleta(self):
        try:
            printer_dialog = PrinterSelectionDialog(self)
            if printer_dialog.exec_() != QDialog.Accepted:
                return
            
            printer_name = printer_dialog.get_selected_printer()
            if not printer_name:
                QMessageBox.warning(self, "Atención", "Seleccione una impresora válida.")
                return
            
            pdf_path = self._generate_boleta_pdf()
            
            result = {'success': False, 'message': 'Operación cancelada', 'done': False}
            
            def print_thread():
                try:
                    success, message = print_boleta(pdf_path, printer_name)
                    result['success'] = success
                    result['message'] = message
                except Exception as ex:
                    result['message'] = str(ex)
                finally:
                    result['done'] = True
            
            t = threading.Thread(target=print_thread, daemon=True)
            t.start()
            
            # Espera activa controlada (timeout 5s)
            start_time = time.time()
            while time.time() - start_time < 5:
                if result['done']:
                    break
                QApplication.processEvents()
                time.sleep(0.1)
            
            if not result['done']:
                QMessageBox.warning(self, "Tiempo de espera", "La impresora no responde. Verifique conexión.")
            elif result['success']:
                QMessageBox.information(self, "Éxito", "Enviado a cola de impresión.")
            else:
                QMessageBox.critical(self, "Error de Impresión", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "Error Crítico", str(e))

    def print_boleta_completa(self):
        try:
            pdf_path = self._generate_full_receipt_pdf()
            success = BrowserSelectionDialog.open_file_in_browser(pdf_path, self)
            if success:
                QMessageBox.information(self, "Información", "Comprobante completo abierto en navegador.")
            else:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(pdf_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _parse_fecha_emision(self, fecha_raw) -> str:
        from datetime import datetime

        fecha_raw = (fecha_raw or "").strip()
        if not fecha_raw:
            return datetime.now().strftime("%Y-%m-%d")

        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return datetime.strptime(fecha_raw, fmt).strftime("%Y-%m-%d")
            except Exception:
                pass

        try:
            return datetime.fromisoformat(fecha_raw).date().isoformat()
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")

    def _persist_sale_updates(self, updates: dict) -> bool:
        try:
            if not isinstance(self.sale_data, dict):
                return False

            sale_id = self.sale_data.get("id")
            if sale_id is None:
                return False

            from utils.file_handler import cargar_ventas, guardar_ventas
            ventas = cargar_ventas(self.parent_username) or []

            updated = False
            for venta in ventas:
                if isinstance(venta, dict) and venta.get("id") == sale_id:
                    venta.update(updates)
                    updated = True
                    break

            if not updated:
                return False

            guardar_ventas(self.parent_username, ventas)
            self.sale_data.update(updates)
            return True
        except Exception as e:
            print(f"[SUNAT] Error persistiendo venta: {e}")
            return False

    def _ensure_sunat_numero(self, generador_sunat):
        if not isinstance(self.sale_data, dict):
            return None, None

        serie = self.sale_data.get("sunat_numero_serie")
        correlativo = self.sale_data.get("sunat_numero_correlativo")
        numero = self.sale_data.get("sunat_numero")

        if serie and correlativo:
            return str(serie), str(correlativo).zfill(8)

        if isinstance(numero, str) and len(numero) > 8:
            serie = numero[:-8]
            correlativo = numero[-8:]
            self._persist_sale_updates(
                {
                    "sunat_numero": numero,
                    "sunat_numero_serie": serie,
                    "sunat_numero_correlativo": correlativo,
                }
            )
            return str(serie), str(correlativo).zfill(8)

        numero_nuevo = generador_sunat.obtener_proximo_numero("boleta")
        serie = numero_nuevo[:-8]
        correlativo = numero_nuevo[-8:]
        self._persist_sale_updates(
            {
                "sunat_numero": numero_nuevo,
                "sunat_numero_serie": serie,
                "sunat_numero_correlativo": correlativo,
            }
        )
        return str(serie), str(correlativo).zfill(8)

    def _build_sunat_datos_boleta(self, numero_serie: str, numero_correlativo: str) -> dict:
        from decimal import Decimal, ROUND_HALF_UP

        sale = self.sale_data if isinstance(self.sale_data, dict) else {}

        def q2(value: Decimal) -> Decimal:
            return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total_venta = Decimal(str(sale.get("total") or 0))
        subtotal_venta_raw = sale.get("subtotal", None)
        subtotal_venta = Decimal(str(subtotal_venta_raw)) if subtotal_venta_raw is not None else Decimal("0")
        if subtotal_venta <= 0 and total_venta > 0:
            subtotal_venta = q2(total_venta / Decimal("1.18"))

        items_raw = sale.get("items") or []
        items = []
        subtotal_sum = Decimal("0")

        for item in items_raw:
            if not isinstance(item, dict):
                continue

            descripcion = (
                item.get("descripcion")
                or item.get("nombre")
                or item.get("producto")
                or "Item"
            )
            try:
                cantidad = Decimal(str(item.get("cantidad") or 1))
            except Exception:
                cantidad = Decimal("1")
            if cantidad <= 0:
                cantidad = Decimal("1")

            line_base = None
            if item.get("subtotal") is not None:
                try:
                    line_base = Decimal(str(item.get("subtotal") or 0))
                except Exception:
                    line_base = Decimal("0")
            elif item.get("total") is not None:
                try:
                    total_item = Decimal(str(item.get("total") or 0))
                except Exception:
                    total_item = Decimal("0")
                if total_venta > 0 and subtotal_venta > 0 and total_venta > subtotal_venta * Decimal("1.01"):
                    line_base = total_item / Decimal("1.18")
                else:
                    line_base = total_item
            else:
                precio_unit = item.get("precio_unitario")
                if precio_unit is None:
                    precio_unit = item.get("precio")
                try:
                    precio_unit = Decimal(str(precio_unit or 0))
                except Exception:
                    precio_unit = Decimal("0")

                if total_venta > 0 and subtotal_venta > 0 and total_venta > subtotal_venta * Decimal("1.01"):
                    line_base = (precio_unit / Decimal("1.18")) * cantidad
                else:
                    line_base = precio_unit * cantidad

            line_base = q2(line_base or Decimal("0"))
            if line_base < 0:
                line_base = Decimal("0.00")

            unit_base = q2(line_base / cantidad)
            subtotal_sum += line_base

            items.append(
                {
                    "descripcion": str(descripcion),
                    "cantidad": str(cantidad),
                    "precio_unitario": str(unit_base),
                    "total": str(line_base),
                    "unidad": "C62",
                }
            )

        if not items and total_venta > 0:
            base_total = q2(total_venta / Decimal("1.18"))
            items = [
                {
                    "descripcion": str(sale.get("descripcion") or sale.get("detalle") or "Venta"),
                    "cantidad": "1",
                    "precio_unitario": str(base_total),
                    "total": str(base_total),
                    "unidad": "C62",
                }
            ]
            subtotal_sum = base_total

        subtotal_sum = q2(subtotal_sum)
        if total_venta <= 0 and subtotal_sum > 0:
            total_venta = q2(subtotal_sum * Decimal("1.18"))

        igv = q2(total_venta - subtotal_sum)

        dni = str(sale.get("paciente_dni") or sale.get("dni") or "").strip()
        if not dni:
            dni = "00000000"
        tipo_cliente = "6" if len(dni) == 11 else "1"

        cliente_nombre = str(sale.get("paciente_nombre") or sale.get("cliente") or "CLIENTE VARIOS").strip()
        if not cliente_nombre:
            cliente_nombre = "CLIENTE VARIOS"

        return {
            "numero_serie": str(numero_serie),
            "numero_correlativo": str(numero_correlativo).zfill(8),
            "tipo_cliente": tipo_cliente,
            "numero_cliente": dni,
            "cliente_nombre": cliente_nombre,
            "fecha_emision": self._parse_fecha_emision(sale.get("fecha")),
            "items": items,
            "subtotal": str(subtotal_sum),
            "igv": str(igv),
            "total": str(q2(total_venta)),
        }

    def send_boleta_sunat(self):
        try:
            if not isinstance(self.sale_data, dict):
                QMessageBox.warning(self, "SUNAT", "No se encontró información de la venta.")
                return

            if self.sale_data.get("id") is None:
                QMessageBox.warning(
                    self,
                    "SUNAT",
                    "Esta venta no tiene ID de historial. Abra esta opción desde el Historial de Ventas.",
                )
                return

            if self.sale_data.get("sunat_enviado"):
                resp = QMessageBox.question(
                    self,
                    "SUNAT",
                    "Esta venta ya figura como enviada a SUNAT. ¿Desea reenviar?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if resp != QMessageBox.Yes:
                    return

            from utils.generador_boletas_sunat import GeneradorBoletasSUNAT
            generador = GeneradorBoletasSUNAT(self.parent_username, str(VISO_DIR))

            if not generador.configurador or not generador.ubl_generator or not generador.digital_signer:
                QMessageBox.warning(self, "SUNAT", "Módulos SUNAT no disponibles en esta instalación.")
                return

            estado = generador.configurador.get_estado_configuracion() or {}
            if not estado.get("habilitado"):
                QMessageBox.warning(self, "SUNAT", "La emisión electrónica no está habilitada en Configuración.")
                return

            numero_serie, numero_correlativo = self._ensure_sunat_numero(generador)
            if not numero_serie or not numero_correlativo:
                QMessageBox.warning(self, "SUNAT", "No se pudo asignar número de boleta SUNAT.")
                return

            datos_boleta = self._build_sunat_datos_boleta(numero_serie, numero_correlativo)
            is_valid, errores = generador.validar_boleta(datos_boleta)
            if not is_valid:
                QMessageBox.critical(
                    self,
                    "SUNAT - Validación",
                    "No se pudo validar la boleta:\n" + "\n".join(str(e) for e in errores),
                )
                return

            self.btn_send_sunat.setEnabled(False)

            progress = QtWidgets.QProgressDialog("Enviando boleta a SUNAT...", None, 0, 0, self)
            progress.setWindowTitle("SUNAT")
            progress.setWindowModality(Qt.WindowModal)
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.show()

            result = {"done": False, "ok": False, "res": None, "err": None}

            def _worker():
                try:
                    ok, res = generador.generar_boleta_electronica(datos_boleta, enviar_a_sunat=True)
                    result["ok"] = ok
                    result["res"] = res
                except Exception as e:
                    result["err"] = str(e)
                finally:
                    result["done"] = True

            threading.Thread(target=_worker, daemon=True).start()

            timer = QtCore.QTimer(self)

            def _check_done():
                if not result["done"]:
                    return

                timer.stop()
                progress.close()
                self.btn_send_sunat.setEnabled(True)

                if result["err"]:
                    QMessageBox.critical(self, "SUNAT", f"Error enviando a SUNAT:\n{result['err']}")
                    return

                res = result["res"] or {}
                errores_envio = res.get("errores") or []

                updates = {
                    "sunat_xml_path": res.get("xml_path"),
                    "sunat_ticket": res.get("ticket_numero"),
                    "sunat_cdr_path": res.get("cdr_path"),
                    "sunat_codigo_respuesta": res.get("codigo_respuesta"),
                    "sunat_errores": errores_envio,
                    "sunat_enviado": len(errores_envio) == 0 and bool(res.get("xml_path")),
                }
                self._persist_sale_updates(updates)

                if errores_envio:
                    QMessageBox.warning(
                        self,
                        "SUNAT - Subida incompleta",
                        "Boleta generada, pero SUNAT reportó errores:\n" + "\n".join(str(e) for e in errores_envio),
                    )
                else:
                    QMessageBox.information(self, "SUNAT", "Boleta enviada a SUNAT correctamente.")

            timer.timeout.connect(_check_done)
            timer.start(150)

        except Exception as e:
            self.btn_send_sunat.setEnabled(True)
            QMessageBox.critical(self, "SUNAT", f"Error inesperado:\n{e}")
