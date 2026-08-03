                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    # gui/dialogs/patient_dialog.py

import sys
import os
import copy
import json
import datetime
import tempfile
import webbrowser
from PyQt5 import QtWidgets, QtCore, sip
from PyQt5.QtWidgets import (
    QMainWindow, QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QDateEdit, QComboBox, QMessageBox, QTableWidget, QHeaderView,
    QAbstractItemView, QHBoxLayout, QPushButton, QTableWidgetItem, QGroupBox, QGridLayout,
    QMenu, QTextEdit, QWidget, QFrame
)
from PyQt5.QtWidgets import QAbstractScrollArea
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5 import QtGui

# Importaciones para el entorno de desarrollo y empaquetado
from utils.data_cache_manager import get_global_cache
from utils.file_handler import (
    resource_path, cargar_nombre_optica, open_pdf_with_chrome, print_pdf_direct,
    cargar_pacientes, guardar_pacientes, cargar_configuracion_optica, get_user_file_path
)
from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
from utils.printer_handler import print_boleta
from utils.whatsapp_handler import open_whatsapp, send_whatsapp_message
from utils.whatsapp_config import get_default_message, save_message
from gui.draggable_title_bar import DraggableTitleBar
from gui.dialogs.adjuntos_dialog import GestorAdjuntosDialog


class _ContractPdfWorker(QtCore.QObject):
    finished = pyqtSignal(str, str)

    def __init__(self, paciente_data, graduacion, nombre_optica, username, contract_number):
        super().__init__()
        self._paciente_data = paciente_data
        self._graduacion = graduacion
        self._nombre_optica = nombre_optica
        self._username = username
        self._contract_number = contract_number

    def run(self):
        try:
            from utils.generador_contrato import generar_contrato_pdf_logic

            pdf_path = generar_contrato_pdf_logic(
                paciente_data=self._paciente_data,
                graduacion=self._graduacion,
                nombre_optica=self._nombre_optica,
                username=self._username,
                contract_number=self._contract_number,
                parent_widget=None,
                return_pdf_path_only=True,
            )
            self.finished.emit(str(pdf_path or ""), "")
        except Exception as e:
            self.finished.emit("", str(e))


def _import_generador_expediente_pdf():
    from utils.generador_expediente import generar_expediente_pdf
    return generar_expediente_pdf


def _normalize_patient_dni(value) -> str:
    return ''.join(filter(str.isdigit, str(value or "").strip()))


def _patient_record_signature(patient) -> str:
    if not isinstance(patient, dict):
        return ""
    try:
        return json.dumps(patient, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return ""


def _is_qt_object_alive(obj) -> bool:
    try:
        return obj is not None and not sip.isdeleted(obj)
    except TypeError:
        return obj is not None
    except Exception:
        return False


def _find_patient_record_index(patients, original_patient, current_patient=None):
    if not isinstance(patients, list) or not isinstance(original_patient, dict):
        return None

    current_patient = current_patient if isinstance(current_patient, dict) else {}

    original_id = str(original_patient.get("id", "")).strip()
    if original_id:
        for idx, patient in enumerate(patients):
            if str(patient.get("id", "")).strip() == original_id:
                return idx

    original_signature = _patient_record_signature(original_patient)
    if original_signature:
        for idx, patient in enumerate(patients):
            if _patient_record_signature(patient) == original_signature:
                return idx

    current_signature = _patient_record_signature(current_patient)
    if current_signature:
        for idx, patient in enumerate(patients):
            if _patient_record_signature(patient) == current_signature:
                return idx

    lookup_dni = _normalize_patient_dni(original_patient.get("dni", "")) or _normalize_patient_dni(
        current_patient.get("dni", "")
    )
    if lookup_dni and lookup_dni != "00000000":
        matching_indexes = [
            idx
            for idx, patient in enumerate(patients)
            if _normalize_patient_dni(patient.get("dni", "")) == lookup_dni
        ]
        if len(matching_indexes) == 1:
            return matching_indexes[0]

    key_fields = ("nombre", "fecha_nacimiento", "genero", "edad")
    for idx, patient in enumerate(patients):
        if lookup_dni and _normalize_patient_dni(patient.get("dni", "")) != lookup_dni:
            continue

        matches = True
        for field in key_fields:
            original_value = str(original_patient.get(field, "") or "").strip()
            if original_value and str(patient.get(field, "") or "").strip() != original_value:
                matches = False
                break

        if matches:
            return idx

    return None


def _safe_float_payment(value) -> float:
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def _parse_patient_date_value(value):
    raw = str(value or "").strip()
    if not raw or raw.upper() == "N/A":
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None


def _resolve_latest_graduacion(patient):
    if not isinstance(patient, dict):
        return {}

    historial = patient.get("historial_graduaciones", [])
    best_entry = None
    best_date = None
    if isinstance(historial, list):
        for entry in historial:
            if not isinstance(entry, dict):
                continue
            current_date = _parse_patient_date_value(entry.get("fecha"))
            if current_date is None:
                continue
            if best_date is None or current_date > best_date:
                best_date = current_date
                best_entry = entry

    if isinstance(best_entry, dict):
        return best_entry
    return {}


def _resolve_patient_last_visit_label(patient):
    if not isinstance(patient, dict):
        return "N/A"

    latest_visit = _parse_patient_date_value(patient.get("ultima_visita"))
    latest_grad = _resolve_latest_graduacion(patient)
    grad_date = _parse_patient_date_value(latest_grad.get("fecha"))

    if latest_visit is not None and grad_date is not None:
        best_date = max(latest_visit, grad_date)
    else:
        best_date = latest_visit or grad_date

    if best_date is None:
        return "N/A"
    return best_date.strftime("%d/%m/%Y")


def _graduacion_payment_summary(graduacion):
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    monto_total = _graduacion_total_amount(graduacion)
    pagos_originales = graduacion.get("pagos_parciales", []) or []
    pagos_visibles = []
    total_pagado = 0.0

    if isinstance(pagos_originales, list) and pagos_originales:
        for pago in pagos_originales:
            pago = pago if isinstance(pago, dict) else {}
            monto = _safe_float_payment(pago.get("monto", 0))
            total_pagado += monto
            pagos_visibles.append({
                "monto": monto,
                "fecha": str(pago.get("fecha", "") or ""),
                "observacion": str(pago.get("observacion", "") or ""),
            })
    else:
        adelanto = _safe_float_payment(graduacion.get("monto_adelanto", 0))
        if adelanto > 0.01:
            total_pagado = adelanto
            pagos_visibles.append({
                "monto": adelanto,
                "fecha": str(graduacion.get("fecha", "") or ""),
                "observacion": "Adelanto inicial",
            })
        elif str(graduacion.get("estado", "") or "").strip().lower() == "completada" and monto_total > 0:
            total_pagado = monto_total
            pagos_visibles.append({
                "monto": monto_total,
                "fecha": str(graduacion.get("fecha", "") or ""),
                "observacion": "Pago completo registrado",
            })

    saldo = max(0.0, monto_total - total_pagado)
    return {
        "monto_total": monto_total,
        "total_pagado": total_pagado,
        "saldo": saldo,
        "pagos": pagos_visibles,
    }


def _graduacion_service_amount(graduacion) -> float:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    return _safe_float_payment(graduacion.get("monto_cobrado", 0))


def _graduacion_items_total(graduacion) -> float:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    total_items, _service_total, _product_total = _graduacion_items_breakdown(graduacion)
    return total_items


def _graduacion_items_breakdown(graduacion):
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    total_items = 0.0
    service_items_total = 0.0
    product_items_total = 0.0
    for item in graduacion.get("items_venta", []) or []:
        if not isinstance(item, dict):
            continue
        cantidad = _safe_float_payment(item.get("cantidad", 1)) or 1.0
        precio = _safe_float_payment(item.get("precio_unitario", item.get("precio", 0)))
        item_total = _safe_float_payment(item.get("subtotal", item.get("total", precio * cantidad)))
        total_items += item_total
        nombre = str(item.get("producto") or item.get("nombre") or "").strip().lower()
        if "servicio de gradu" in nombre or nombre == "graduacion":
            service_items_total += item_total
        else:
            product_items_total += item_total
    return total_items, service_items_total, product_items_total


def _graduacion_items_include_service(graduacion) -> bool:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    for item in graduacion.get("items_venta", []) or []:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("producto") or item.get("nombre") or "").strip().lower()
        if "servicio de gradu" in nombre or nombre == "graduacion":
            return True
    return False


def _graduacion_total_amount(graduacion) -> float:
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    
    # 1. Prioridad máxima: Usar el total ya consolidado si existe
    stored_total = _safe_float_payment(graduacion.get("monto_total_venta"))
    if stored_total > 0.01:
        return stored_total
        
    # 2. Fallback: Sumar items_venta
    total_items, _service_total, _product_total = _graduacion_items_breakdown(graduacion)
    if total_items > 0.01:
        return total_items
        
    # 3. Fallback extremo: Usar monto_cobrado
    return _graduacion_service_amount(graduacion)


def _graduacion_boleta_productos(graduacion):
    graduacion = graduacion if isinstance(graduacion, dict) else {}
    items_raw = graduacion.get('items_venta', [])
    
    # 1. Si hay items consolidados, usarlos directamente (ya traen el servicio)
    if isinstance(items_raw, list) and len(items_raw) > 0:
        productos = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            nombre_p = str(item.get('producto') or item.get('nombre') or 'Producto').strip()
            precio_u = _safe_float_payment(item.get('precio_unitario', item.get('precio', 0)))
            total_i = _safe_float_payment(item.get('total', item.get('subtotal', precio_u)))
            
            productos.append({
                'nombre': nombre_p,
                'cantidad': int(item.get('cantidad', 1) or 1),
                'precio': precio_u,
                'total': total_i,
            })
        return productos

    # 2. Fallback: Si no hay items, crear al menos el de graduación
    productos = []
    monto_servicio = _graduacion_service_amount(graduacion)
    if monto_servicio > 0.01:
        productos.append({
            'nombre': 'Servicio de Graduación',
            'cantidad': 1,
            'precio': monto_servicio,
            'total': monto_servicio,
        })
        
    if not productos:
        productos.append({
            'nombre': 'Servicio de Graduación',
            'cantidad': 1,
            'precio': 0.0,
            'total': 0.0,
        })

    return productos


class TodasBoletasDialog(QDialog):
    """DiÃ¡logo que muestra todas las boletas de un paciente."""
    def __init__(self, paciente_data, parent_app, parent=None):
        super().__init__(parent)
        self.paciente_data = paciente_data
        self.parent_app = parent_app
        self.setWindowTitle(f"Todas las Boletas - {paciente_data.get('nombre')}")
        self.resize(900, 600)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Tabla de boletas
        self.boletas_table = QTableWidget()
        self.boletas_table.setColumnCount(3)
        self.boletas_table.setHorizontalHeaderLabels(["Fecha", "Monto", "OptÃ³metra"])
        self.boletas_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.boletas_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.boletas_table.itemDoubleClicked.connect(self.on_boleta_double_click)
        
        header = self.boletas_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        # Cargar datos
        graduaciones = self.paciente_data.get('historial_graduaciones', [])
        for idx, grad in enumerate(graduaciones):
            monto_total = _graduacion_total_amount(grad)
            self.boletas_table.insertRow(idx)
            self.boletas_table.setItem(idx, 0, QTableWidgetItem(grad.get('fecha', '')))
            self.boletas_table.setItem(idx, 1, QTableWidgetItem(f"S/. {monto_total:.2f}"))
            self.boletas_table.setItem(idx, 2, QTableWidgetItem(grad.get('optometra', '')))
            # Guardar referencia al Ã­ndice de graduaciÃ³n
            self.boletas_table.item(idx, 0).setData(QtCore.Qt.UserRole, idx)
        
        layout.addWidget(self.boletas_table)
        
        # Label de instrucciones
        label_info = QLabel("Haz doble clic en una boleta para ver opciones (Imprimir, Descargar, Ver, WhatsApp)")
        label_info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(label_info)
    
    def on_boleta_double_click(self, item):
        """Muestra opciones de la boleta al hacer doble clic."""
        row = item.row()
        graduacion_idx = self.boletas_table.item(row, 0).data(QtCore.Qt.UserRole)
        graduaciones = self.paciente_data.get('historial_graduaciones', [])
        
        if graduacion_idx < len(graduaciones):
            graduacion = graduaciones[graduacion_idx]
            OpcionesBeletaDialog(self.paciente_data, graduacion, self.parent_app, self).exec_()


class OpcionesBeletaDialog(QDialog):
    """DiÃ¡logo con opciones para una boleta."""
    def __init__(self, paciente_data, graduacion, parent_app, parent=None):
        super().__init__(parent)
        self.paciente_data = paciente_data
        self.graduacion = graduacion
        self.parent_app = parent_app
        self.setWindowTitle(f"Opciones de Boleta - {graduacion.get('fecha')}")
        self.resize(400, 200)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Label con info
        monto_total = _graduacion_total_amount(self.graduacion)
        info_label = QLabel(f"Boleta del {self.graduacion.get('fecha')}\nMonto: S/. {monto_total:.2f}")
        layout.addWidget(info_label)
        
        layout.addSpacing(16)
        
        # Botones
        btn_ver = QPushButton("Ver PDF")
        btn_ver.clicked.connect(self.ver_pdf)
        layout.addWidget(btn_ver)
        
        btn_descargar = QPushButton("Descargar")
        btn_descargar.clicked.connect(self.descargar_pdf)
        layout.addWidget(btn_descargar)
        
        btn_imprimir = QPushButton("Imprimir")
        btn_imprimir.clicked.connect(self.imprimir_boleta)
        layout.addWidget(btn_imprimir)
        
        btn_whatsapp = QPushButton("Enviar por WhatsApp")
        btn_whatsapp.clicked.connect(self.enviar_whatsapp)
        layout.addWidget(btn_whatsapp)
        
        layout.addStretch()
    
    def generar_boleta_pdf(self):
        """Genera la boleta PDF usando la plantilla seleccionada."""
        try:
            username = self._get_username()
            print(f"[PatientDetailsDialog] Username resolto: {username}")
            generador = GeneradorBoletasPlantilla(username)
            
            nombre_optica = self._get_nombre_optica()
            paciente_nombre = self.paciente_data.get('nombre', '')
            monto = _graduacion_service_amount(self.graduacion)
            
            # Crear lista de productos (Graduación + Productos)
            productos = _graduacion_boleta_productos(self.graduacion)
            total = _graduacion_total_amount(self.graduacion)

            subtotal = total
            igv = 0.0
            
            # Datos para la boleta
            datos_boleta = {
                'nombre_optica': nombre_optica,
                'ruc': '12345678901',
                'direccion': 'DirecciÃ³n no configurada',
                'numero_boleta': f"EXP-{self.paciente_data.get('id', 'S/N')}",
                'fecha': self.graduacion.get('fecha', ''),
                'cliente': paciente_nombre,
                'productos': productos,
                'subtotal': subtotal,
                'igv': igv,
                'total': total,
                'metodo_pago': 'Efectivo',
                'pie_pagina': 'Gracias por su compra'
            }
            
            pdf_path = generador.generar_boleta(datos_boleta)
            return pdf_path
        except Exception as e:
            import traceback
            error_msg = f"No se pudo generar la boleta: {type(e).__name__}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"\n{'='*70}")
            print(error_msg)
            print(f"{'='*70}\n")
            QMessageBox.critical(self, "Error", error_msg)
            return None
    
    def ver_pdf(self):
        """Abre la boleta en el navegador."""
        pdf_path = self.generar_boleta_pdf()
        if pdf_path:
            open_pdf_with_chrome(pdf_path)
    
    def descargar_pdf(self):
        """Guarda el PDF en una ubicaciÃ³n seleccionada."""
        pdf_path = self.generar_boleta_pdf()
        if pdf_path:
            QMessageBox.information(self, "Ã‰xito", f"Boleta descargada en:\n{pdf_path}")
    
    def imprimir_boleta(self):
        """Imprime la boleta directamente en la impresora tÃ©rmica sin diÃ¡logos."""
        try:
            # Generar PDF
            pdf_path = self.generar_boleta_pdf()
            if not pdf_path:
                return
            
            # Imprimir directamente en la impresora tÃ©rmica
            success, message = print_pdf_direct(pdf_path)
            if success:
                QMessageBox.information(self, "Ã‰xito", "Boleta impresa correctamente")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo imprimir: {message}")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error", f"Error al imprimir:\n{str(e)}\n\n{traceback.format_exc()}")
    
    def enviar_whatsapp(self):
        """EnvÃ­a la boleta por WhatsApp de forma automÃ¡tica."""
        try:
            # Obtener nÃºmero de telÃ©fono del paciente
            telefono = self.paciente_data.get('telefono', '')
            
            # Si no hay nÃºmero registrado, pedir que lo ingrese
            if not telefono:
                numero_ingresado, ok = QtWidgets.QInputDialog.getText(
                    self,
                    "NÃºmero de TelÃ©fono",
                    "El cliente no tiene nÃºmero registrado.\nIngresa el nÃºmero de telÃ©fono (ej: 51999999999):",
                    QtWidgets.QLineEdit.Normal,
                    ""
                )
                
                if not ok or not numero_ingresado:
                    QMessageBox.warning(self, "Cancelado", "No se proporcionó número de teléfono")
                    return
                
                telefono = numero_ingresado
            else:
                # Si hay número registrado, preguntar si está en contactos
                reply = QMessageBox.question(
                    self,
                    "¿Cliente en Contactos?",
                    f"¿El cliente {self.paciente_data.get('nombre', 'desconocido')} está en tus contactos de WhatsApp?\n\nTeléfono: {telefono}",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                # Si dice No, permitir cambiar el número
                if reply == QMessageBox.No:
                    numero_ingresado, ok = QtWidgets.QInputDialog.getText(
                        self,
                        "Número de Teléfono",
                        "Ingresa el número de teléfono del cliente (ej: 51999999999):",
                        QtWidgets.QLineEdit.Normal,
                        telefono
                    )
                    
                    if ok and numero_ingresado:
                        telefono = numero_ingresado
            
            # Generar PDF
            pdf_path = self.generar_boleta_pdf()
            if not pdf_path:
                return
            
            # Obtener el mensaje personalizado
            paciente_nombre = self.paciente_data.get('nombre', 'cliente')
            mensaje_template = get_default_message()
            mensaje = mensaje_template.format(nombre=paciente_nombre)
            
            # Permitir al usuario editar el mensaje
            mensaje_editado, ok = QtWidgets.QInputDialog.getMultiLineText(
                self,
                "Editar Mensaje",
                "Edita el mensaje a enviar por WhatsApp:",
                mensaje
            )
            
            if not ok:
                return  # Usuario canceló
            
            mensaje = mensaje_editado
            
            # Preguntar si guardar como predeterminado
            if mensaje != mensaje_template:
                reply = QMessageBox.question(
                    self,
                    "Guardar como Predeterminado",
                    "¿Deseas guardar este mensaje como predeterminado para futuras boletas?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    save_message(mensaje)
                    QMessageBox.information(self, "Guardado", "Mensaje guardado como predeterminado")
            
            # Enviar por WhatsApp
            if send_whatsapp_message(telefono, mensaje, pdf_path):
                QMessageBox.information(
                    self, 
                    "WhatsApp Abierto", 
                    f"Se abrió WhatsApp.\n\nTeléfono: {telefono}\n\nEl PDF ha sido guardado en tu carpeta de Descargas.\nAhora puedes adjuntarlo manualmente desde WhatsApp."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo abrir WhatsApp.\n\nAsegúrate de tener WhatsApp instalado."
                )
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error", f"Error al enviar por WhatsApp:\n{str(e)}\n\n{traceback.format_exc()}")
    
    def _get_username(self):
        """Resolver el username del contexto."""
        # Primero intentar obtener del parent_app
        if hasattr(self, 'parent_app') and self.parent_app:
            username = getattr(self.parent_app, 'username', None)
            if username:
                return username
            username = getattr(self.parent_app, 'user_id', None)
            if username:
                return username
        
        # Luego intentar del parent dialog
        if hasattr(self, 'parent') and self.parent:
            if hasattr(self.parent, '_get_username'):
                return self.parent._get_username()
        
        # Por defecto retornar 'default'
        return 'default'
    
    def _get_nombre_optica(self):
        """Resolver el nombre de la Ã³ptica."""
        username = self._get_username()
        
        # Intenta cargar desde el archivo de configuraciÃ³n
        try:
            nombre_optica = cargar_nombre_optica(username)
            if nombre_optica and nombre_optica != "Mi Ã“ptica":
                return nombre_optica
        except Exception:
            pass
        
        # Intentar desde UI
        try:
            if hasattr(self.parent_app, 'home_page') and hasattr(self.parent_app.home_page, 'nombre_optica_label'):
                txt = self.parent_app.home_page.nombre_optica_label.text().replace("Bienvenido al Sistema de GestiÃ³n de ", "").strip()
                if txt and txt != username:
                    return txt
        except Exception:
            pass
        
        return 'Mi Ã“ptica'


class PagoEnPartesDialog(QDialog):
    """DiÃ¡logo para registrar un pago en partes (adelanto)."""
    def __init__(self, paciente_data, parent=None):
        super().__init__(parent)
        self.paciente_data = paciente_data
        self.setWindowTitle("Registrar Pago en Partes")
        self.setModal(True)
        self.monto_adelanto = None
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Información del paciente
        info_label = QLabel(f"Paciente: {self.paciente_data.get('nombre', 'Desconocido')}")
        info_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(info_label)
        
        layout.addSpacing(12)
        
        # Pregunta principal
        pregunta_label = QLabel("¿Cuánto dejó como adelanto?")
        pregunta_label.setStyleSheet("font-size: 11pt; color: #333;")
        layout.addWidget(pregunta_label)
        
        layout.addSpacing(8)
        
        # Layout para el input de monto
        monto_layout = QHBoxLayout()
        
        # Símbolo de moneda
        moneda_label = QLabel("S/.")
        moneda_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        monto_layout.addWidget(moneda_label)
        
        # Input para el monto
        self.monto_input = QtWidgets.QDoubleSpinBox()
        self.monto_input.setMinimum(0.0)
        self.monto_input.setMaximum(999999.99)
        self.monto_input.setDecimals(2)
        self.monto_input.setValue(0.0)
        self.monto_input.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 2px solid #1976d2;
                border-radius: 4px;
                font-size: 11pt;
                background: white;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #1565c0;
            }
        """)
        monto_layout.addWidget(self.monto_input)
        
        layout.addLayout(monto_layout)
        
        layout.addSpacing(16)
        
        # Botones
        button_layout = QHBoxLayout()
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_guardar.clicked.connect(self.guardar_pago)
        button_layout.addWidget(btn_guardar)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancelar)
        
        layout.addLayout(button_layout)
        
        self.resize(400, 200)
        
        # Enfocar el input y seleccionar el texto
        self.monto_input.setFocus()
        self.monto_input.selectAll()
    
    def guardar_pago(self):
        """Guarda el monto del adelanto."""
        monto = self.monto_input.value()
        if monto <= 0:
            QMessageBox.warning(self, "Error", "El monto debe ser mayor a 0")
            return
        
        self.monto_adelanto = monto
        self.accept()
    
    def get_monto_adelanto(self):
        """Retorna el monto del adelanto registrado."""
        return self.monto_adelanto


def fill_patient_form_fields(page, prefill_data):
    """
    FunciÃ³n helper que ejecuta el llenado de campos en la pÃ¡gina de creaciÃ³n de pacientes.
    Debe ejecutarse en el thread principal.
    """
    try:
        # Bandera explÃ­cita para distinguir "nueva graduaciÃ³n" vs "ediciÃ³n".
        if hasattr(page, '_modo_edicion_graduacion'):
            page._modo_edicion_graduacion = bool(prefill_data.get('_modo_edicion_graduacion', False))
        if hasattr(page, '_graduacion_edit_index'):
            idx = prefill_data.get('_graduacion_edit_index', None)
            page._graduacion_edit_index = idx if isinstance(idx, int) else None
        if hasattr(page, '_prefilled_contrato_numero'):
            page._prefilled_contrato_numero = str(prefill_data.get('contrato_numero', '') or '').strip()
        if hasattr(page, '_extra_contract_fields'):
            page._extra_contract_fields = page._normalize_extra_contract_fields({
                'telefono': prefill_data.get('telefono', ''),
                'direccion': prefill_data.get('direccion', ''),
                'cristales': prefill_data.get('cristales', ''),
                'resina': prefill_data.get('resina', ''),
                'color': prefill_data.get('color', ''),
                'bifocal_tipo': prefill_data.get('bifocal_tipo', ''),
                'multifocal_tipo': prefill_data.get('multifocal_tipo', ''),
                'altura': prefill_data.get('altura', ''),
                'luna_tipo': prefill_data.get('luna_tipo', ''),
                'luna_costo': prefill_data.get('luna_costo', ''),
                'luna_laboratorio': prefill_data.get('luna_laboratorio', ''),
            })

        # 1. DATOS BÃSICOS DEL PACIENTE
        if hasattr(page, 'entry_dni'):
            page.entry_dni.setText(prefill_data.get('dni', ''))
        
        if hasattr(page, 'entry_paciente'):
            page.entry_paciente.setText(prefill_data.get('nombre', ''))
        
        if hasattr(page, 'entry_fecha_nacimiento'):
            fecha_nac = prefill_data.get('fecha_nacimiento')
            if fecha_nac:
                from PyQt5.QtCore import QDate
                q_date = QDate.fromString(fecha_nac, "yyyy-MM-dd")
                page.entry_fecha_nacimiento.setDate(q_date)
        
        if hasattr(page, 'genero_combo'):
            genero = prefill_data.get('genero')
            if genero:
                index = page.genero_combo.findText(genero)
                if index >= 0:
                    page.genero_combo.setCurrentIndex(index)

        # 2. DATOS DE LA GRADUACIÃ“N (Si existen)
        
        # OptÃ³metra
        if hasattr(page, 'optometra_combo') and 'optometra' in prefill_data:
            optometra = prefill_data['optometra']
            if optometra:
                index = page.optometra_combo.findText(optometra)
                if index >= 0:
                    page.optometra_combo.setCurrentIndex(index)

        # Fecha de Registro (GraduaciÃ³n)
        if hasattr(page, 'entry_fecha') and 'fecha' in prefill_data:
            page.entry_fecha.setText(prefill_data['fecha'])

        # Observaciones
        if hasattr(page, 'text_observacion') and 'observacion' in prefill_data:
            page.text_observacion.setText(prefill_data['observacion'])

        # Monto Cobrado
        if hasattr(page, 'entry_monto_cobrado') and 'monto_cobrado' in prefill_data:
            page.entry_monto_cobrado.setText(str(prefill_data['monto_cobrado']))

        if hasattr(page, '_graduacion_payment_prefill'):
            page._graduacion_payment_prefill = {
                'metodo_pago': str(prefill_data.get('metodo_pago', '') or '').strip(),
                'metodos_pago_detalle': list(prefill_data.get('metodos_pago_detalle') or []),
                'pago_mixto': bool(prefill_data.get('pago_mixto', False)),
                'pagos_parciales': list(prefill_data.get('pagos_parciales') or []),
            }

        if hasattr(page, 'items_venta'):
            items_prefill = []
            for item in prefill_data.get('items_venta', []) or []:
                if not isinstance(item, dict):
                    continue
                nombre_item = str(item.get('producto') or item.get('nombre') or '').strip().lower()
                if nombre_item == 'servicio de graduacion':
                    continue
                items_prefill.append({
                    'nombre': str(item.get('nombre') or item.get('producto') or 'Producto'),
                    'categoria': str(item.get('categoria', '') or ''),
                    'marca': str(item.get('marca', '') or ''),
                    'cantidad': int(item.get('cantidad', 1) or 1),
                    'precio_unitario': float(item.get('precio_unitario', item.get('precio', 0)) or 0),
                    'total': float(item.get('total', item.get('subtotal', 0)) or 0),
                    'codigo': str(item.get('codigo', '') or ''),
                    'stock_original': int(item.get('stock_original', item.get('stock', item.get('cantidad', 1))) or 1),
                })
            page.items_venta = items_prefill

        if hasattr(page, 'check_comision'):
            page.check_comision.setChecked(bool(prefill_data.get('comision_activada', False)))

        if hasattr(page, 'entry_comision_monto'):
            try:
                if 'comision_monto' in prefill_data:
                    page.entry_comision_monto.setText(str(prefill_data.get('comision_monto', 0.0) or 0.0))
                elif 'comision_porcentaje' in prefill_data:
                    page.entry_comision_monto.setText(str(prefill_data.get('comision_porcentaje', 0.0) or 0.0))
            except (TypeError, ValueError):
                page.entry_comision_monto.setText("0.00")

        if hasattr(page, '_update_comision_preview'):
            page._update_comision_preview()
        if hasattr(page, '_update_metodo_pago_visibility'):
            page._update_metodo_pago_visibility()
        elif hasattr(page, '_update_multi_metodo_pago_grad_state'):
            page._update_multi_metodo_pago_grad_state()
        if hasattr(page, '_refresh_contract_number_preview'):
            page._refresh_contract_number_preview()
        if hasattr(page, '_refresh_extra_data_button_tooltip'):
            page._refresh_extra_data_button_tooltip()

        # Pagos Parciales (Checkbox)
        if hasattr(page, 'checkbox_en_partes'):
            es_parcial = prefill_data.get('es_pago_parcial', False)
            if not es_parcial and prefill_data.get('pagos_parciales'):
                es_parcial = True
            page.checkbox_en_partes.setChecked(bool(es_parcial))

        # 3. VALORES RX (Lejos y Cerca)
        def fill_rx_widgets(data_key, widget_collection, suffix):
            if data_key in prefill_data and isinstance(prefill_data[data_key], dict):
                data_dict = prefill_data[data_key]
                for field in ['esferico', 'cilindro', 'eje', 'av', 'adicmedia', 'prisma']:
                    widget_key = f"{field}_{suffix}"
                    if widget_key in widget_collection and field in data_dict:
                        widget_collection[widget_key].setText(str(data_dict[field]))

        # Llenar Lejos OD/OI
        if hasattr(page, 'lejos_form_widgets'):
            fill_rx_widgets('lejos_od', page.lejos_form_widgets, 'OD')
            fill_rx_widgets('lejos_oi', page.lejos_form_widgets, 'OI')
            # DIP Lejos
            if 'lejos_distp' in prefill_data and 'distp' in page.lejos_form_widgets:
                    page.lejos_form_widgets['distp'].setText(str(prefill_data['lejos_distp']))
            elif 'lejos_od' in prefill_data and 'distp' in prefill_data['lejos_od'] and 'distp' in page.lejos_form_widgets:
                    page.lejos_form_widgets['distp'].setText(str(prefill_data['lejos_od']['distp']))

        # Llenar Cerca OD/OI
        if hasattr(page, 'cerca_form_widgets'):
            fill_rx_widgets('cerca_od', page.cerca_form_widgets, 'OD')
            fill_rx_widgets('cerca_oi', page.cerca_form_widgets, 'OI')
            # DIP Cerca
            if 'cerca_distp' in prefill_data and 'distp' in page.cerca_form_widgets:
                    page.cerca_form_widgets['distp'].setText(str(prefill_data['cerca_distp']))
            elif 'cerca_od' in prefill_data and 'distp' in prefill_data['cerca_od'] and 'distp' in page.cerca_form_widgets:
                    page.cerca_form_widgets['distp'].setText(str(prefill_data['cerca_od']['distp']))
                    
    except Exception as e:
        print(f"[ERROR] Error llenando formulario: {e}")


class PrefillWorker(QThread):
    """Worker que ejecuta el pre-llenado en un thread separado sin bloquear la UI."""
    finished = pyqtSignal()
    fill_requested = pyqtSignal(object, dict) # SeÃ±al para pedir actualizaciÃ³n de UI
    
    def __init__(self, main_window, prefill_data):
        super().__init__()
        self.main_window = main_window
        self.prefill_data = prefill_data
    
    def run(self):
        """Ejecuta el pre-llenado en thread background."""
        try:
            # Esperar a que la pÃ¡gina CreatePatientPage exista
            for attempt in range(20):
                if hasattr(self.main_window, 'create_patient_page'):
                    page = self.main_window.create_patient_page
                    # Emitir seÃ±al para que el thread principal haga el llenado
                    self.fill_requested.emit(page, self.prefill_data)
                    break  # Ã‰xito, salir del loop
                
                # Esperar 500ms antes de reintentar
                self.msleep(500)
        
        except Exception as e:
            print(f"[ERROR] Error en PrefillWorker: {e}")
        
        finally:
            self.finished.emit()


class AddPatientDialog(QDialog):
    """DiÃ¡logo para crear un nuevo paciente."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Nuevo Paciente")
        self.parent_app = parent
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        
        form_layout = QFormLayout()

        self.dni_entry = QLineEdit()
        self.dni_entry.setPlaceholderText("8 dÃ­gitos numÃ©ricos")
        self.nombre_entry = QLineEdit()
        self.fecha_nacimiento_date = QDateEdit(calendarPopup=True)
        self.fecha_nacimiento_date.setDate(QtCore.QDate.currentDate().addYears(-20))
        self.genero_combo = QComboBox()
        self.genero_combo.addItems(["Masculino", "Femenino"])

        form_layout.addRow("DNI:", self.dni_entry)
        form_layout.addRow("Nombre:", self.nombre_entry)
        form_layout.addRow("Fecha de Nacimiento:", self.fecha_nacimiento_date)
        form_layout.addRow("GÃ©nero:", self.genero_combo)
        
        main_layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Save).setObjectName("primaryButton")
        button_box.accepted.connect(self.save_new_patient)
        button_box.rejected.connect(self.close)
        main_layout.addWidget(button_box)
        
        main_layout.addStretch()
        
        # Aplicar estilos
        self.setStyleSheet("""
            QLineEdit, QDateEdit, QComboBox {
                padding: 8px;
                border: 1px solid #d6e3ef;
                border-radius: 4px;
                background: #ffffff;
                font-size: 11pt;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 2px solid #1976D2;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton#primaryButton {
                background-color: #1976D2;
                color: white;
            }
            QPushButton#primaryButton:hover {
                background-color: #1565c0;
            }
            QLabel {
                font-size: 11pt;
            }
        """)
        
        self.resize(500, 300)
        
    def save_new_patient(self):
        dni_raw = self.dni_entry.text().strip()
        dni = ''.join(filter(str.isdigit, dni_raw))
        nombre = self.nombre_entry.text().strip()
        fecha_nacimiento = self.fecha_nacimiento_date.date().toString("yyyy-MM-dd")
        genero = self.genero_combo.currentText()
        
        # ValidaciÃ³n del DNI: solo que no estÃ© vacÃ­o
        if not dni:
            QMessageBox.critical(self, "Error", "El DNI es obligatorio.")
            return
        if not nombre:
            QMessageBox.critical(self, "Error", "El nombre es obligatorio.")
            return

        # Cargar pacientes para verificar si el DNI ya existe
        username = getattr(self.parent_app, 'username', 'default_user')
        cache = get_global_cache()
        pacientes = cache.get_pacientes(username)
        if any(p.get('dni') == dni for p in pacientes):
            QMessageBox.critical(self, "Error", "Ya existe un paciente con este DNI.")
            return

        # Calcular edad
        birth_date_obj = datetime.datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
        today = datetime.date.today()
        edad = today.year - birth_date_obj.year - ((today.month, today.day) < (birth_date_obj.month, birth_date_obj.day))

        # Crear nuevo paciente
        new_patient_data = {
            'dni': dni,
            'nombre': nombre,
            'fecha_nacimiento': fecha_nacimiento,
            'genero': genero,
            'edad': edad,
            'fecha': datetime.date.today().strftime('%d/%m/%Y'),
            'historial_graduaciones': []
        }
        
        pacientes.append(new_patient_data)
        cache = get_global_cache()
        cache.update_pacientes(username, pacientes)
        
        # Sincronizar con servidor remoto - IMPORTANTE: hacer esto antes de cerrar el dialog
        sync_success = False
        sync_msg = ""
        try:
            from utils.api_handler import guardar_paciente_remoto
            # Usar el user_id del app (que es el DNI desde login remoto)
            id_usuario = getattr(self.parent_app, 'user_id', None)
            
            # Si no hay user_id, intentar con username
            if not id_usuario:
                id_usuario = getattr(self.parent_app, 'username', username)
            
            print(f"[DEBUG] Sincronizando con id_usuario={id_usuario}, dni={dni}")
            
            success, msg = guardar_paciente_remoto(
                id_usuario=id_usuario,
                dni=dni,
                nombre=nombre,
                fecha_nacimiento=fecha_nacimiento,
                genero=genero,
                edad=edad
            )
            
            sync_success = success
            sync_msg = msg
            
            if success:
                print(f"Cliente sincronizado a BD remota: {msg}")
            else:
                print(f"Error al sincronizar: {msg}")
        except Exception as e:
            print(f"Excepción en sincronización: {str(e)}")
            import traceback
            traceback.print_exc()
            sync_msg = str(e)
        
        # Mostrar resultado al usuario
        if sync_success:
            QMessageBox.information(
                self,
                "Éxito",
                f"Cliente '{nombre}' registrado correctamente.\nSincronizado a BD remota."
            )
        else:
            QMessageBox.warning(
                self,
                "Aviso",
                f"Cliente '{nombre}' registrado localmente.\nPero no se sincronizó a BD remota:\n{sync_msg}"
            )
        
        # Navegar a la página de pacientes
        if hasattr(self.parent_app, 'load_patient_page'):
            self.accept()
            self.parent_app.load_patient_page()
        else:
            self.accept()

class EditPatientDialog(QDialog):
    """Diálogo para editar la información básica de un paciente existente."""
    def __init__(self, patient_data, parent=None):
        super().__init__(parent)
        self.patient_data = patient_data
        self._original_patient_data = copy.deepcopy(patient_data or {})
        self.setWindowTitle(f"Editar Paciente: {self.patient_data['nombre']}")
        self.parent_app = parent
        
        # Guardar DNI original para poder buscar el registro si se cambia
        self.dni_original = self.patient_data.get('dni', '')
        
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.dni_entry = QLineEdit(self.dni_original)
        self.nombre_entry = QLineEdit(self.patient_data.get('nombre', ''))
        self.fecha_nacimiento_date = QDateEdit(calendarPopup=True)
        if self.patient_data.get('fecha_nacimiento'):
            self.fecha_nacimiento_date.setDate(QtCore.QDate.fromString(self.patient_data['fecha_nacimiento'], "yyyy-MM-dd"))
        self.genero_combo = QComboBox()
        self.genero_combo.addItems(["Masculino", "Femenino"])
        if self.patient_data.get('genero') == 'Femenino':
            self.genero_combo.setCurrentIndex(1)
        
        form_layout.addRow("DNI:", self.dni_entry)
        form_layout.addRow("Nombre:", self.nombre_entry)
        form_layout.addRow("Fecha de Nacimiento:", self.fecha_nacimiento_date)
        form_layout.addRow("GÃ©nero:", self.genero_combo)
        
        main_layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Save).setObjectName("primaryButton")
        button_box.accepted.connect(self.save_changes)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
    def save_changes(self):
        new_nombre = self.nombre_entry.text().strip()
        new_dni = _normalize_patient_dni(self.dni_entry.text())
        new_fecha_nacimiento = self.fecha_nacimiento_date.date().toString("yyyy-MM-dd")
        new_genero = self.genero_combo.currentText()

        if not new_nombre:
            QMessageBox.critical(self, "Error", "El nombre es obligatorio.")
            return
        
        if not new_dni:
            QMessageBox.critical(self, "Error", "El DNI es obligatorio.")
            return

        self.dni_entry.setText(new_dni)

        username = getattr(self.parent_app, 'username', 'default_user')
        if hasattr(self.parent_app, '_get_username'):
            username = self.parent_app._get_username()

        pacientes = cargar_pacientes(username)
        patient_index = _find_patient_record_index(
            pacientes,
            self._original_patient_data,
            self.patient_data,
        )
        if patient_index is None:
            QMessageBox.critical(
                self,
                "Error",
                "No se encontrÃ³ el paciente original para guardar los cambios.",
            )
            return

        if new_dni != '00000000':
            for idx, patient in enumerate(pacientes):
                if idx == patient_index:
                    continue
                if _normalize_patient_dni(patient.get('dni', '')) == new_dni:
                    QMessageBox.critical(self, "Error", "Ya existe otro paciente con este DNI.")
                    return

        # Actualizar datos en el objeto local
        self.patient_data['nombre'] = new_nombre
        self.patient_data['dni'] = new_dni
        self.patient_data['fecha_nacimiento'] = new_fecha_nacimiento
        self.patient_data['genero'] = new_genero
        
        try:
            birth_date_obj = datetime.datetime.strptime(new_fecha_nacimiento, "%Y-%m-%d").date()
            today = datetime.date.today()
            self.patient_data['edad'] = today.year - birth_date_obj.year - ((today.month, today.day) < (birth_date_obj.month, birth_date_obj.day))
        except (ValueError, TypeError):
            self.patient_data['edad'] = 'N/A'
        
        pacientes[patient_index] = copy.deepcopy(self.patient_data)
        guardar_pacientes(username, pacientes)
        
        # Sincronizar con servidor remoto automÃ¡ticamente
        sync_success = False
        sync_msg = ""
        try:
            from utils.api_handler import guardar_paciente_remoto
            # Usar el user_id del app (que es el DNI desde login remoto)
            id_usuario = getattr(self.parent_app, 'user_id', None)
            if not id_usuario:
                id_usuario = getattr(self.parent_app, 'username', 'default_user')
            
            print(f"[DEBUG] Actualizando en BD con id_usuario={id_usuario}, dni={new_dni}")
            
            success, msg = guardar_paciente_remoto(
                id_usuario=id_usuario,
                dni=new_dni,
                nombre=new_nombre,
                fecha_nacimiento=new_fecha_nacimiento,
                genero=new_genero,
                edad=self.patient_data.get('edad', None)
            )
            
            sync_success = success
            sync_msg = msg
            
            if success:
                print(f"Cliente actualizado en BD remota: {msg}")
            else:
                print(f"Error al actualizar en BD: {msg}")
        except Exception as e:
            print(f"Excepción en sincronización: {str(e)}")
            import traceback
            traceback.print_exc()
            sync_msg = str(e)
        
        # Mostrar resultado al usuario (opcional - solo si hubo error)
        if not sync_success:
            print(f"Advertencia: No se sincronizó: {sync_msg}")
            
        self.accept()
      
MOTILIDAD_DIRECCIONES = (
    "arriba",
    "izq_arriba",
    "der_arriba",
    "izq_abajo",
    "der_abajo",
    "abajo",
)


class MotilidadReadOnlyEyeWidget(QWidget):
    """Vista de motilidad por ojo: ejes + 6 casillas de solo lectura."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(236, 198)
        self.setStyleSheet("""
            QWidget {
                background: #F8FAFC;
                border: 1px solid #D9E1EC;
                border-radius: 12px;
            }
        """)
        self.checks = {}
        self._build_checks()

    def _add_check(self, key, x, y):
        check = QtWidgets.QCheckBox(self)
        check.setText("")
        check.setEnabled(False)
        check.setFixedSize(34, 34)
        check.move(x, y)
        check.setStyleSheet("""
            QCheckBox {
                background: transparent;
                padding-left: 5px;
                padding-top: 5px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 4px;
                border: 1px solid #9FB0C5;
                background: #FFFFFF;
            }
            QCheckBox::indicator:disabled:checked {
                background: #1F7AE0;
                border: 1px solid #1565C0;
            }
            QCheckBox::indicator:disabled:unchecked {
                background: #FFFFFF;
                border: 1px solid #9FB0C5;
            }
        """)
        self.checks[key] = check

    def _build_checks(self):
        self._add_check("arriba", 101, 24)
        self._add_check("izq_arriba", 34, 64)
        self._add_check("der_arriba", 170, 64)
        self._add_check("izq_abajo", 34, 106)
        self._add_check("der_abajo", 170, 106)
        self._add_check("abajo", 101, 148)

    def set_values(self, values):
        values = values or {}
        for key in MOTILIDAD_DIRECCIONES:
            self.checks[key].setChecked(bool(values.get(key, False)))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor("#8EA1B8"), 2)
        painter.setPen(pen)

        center_x = self.width() // 2
        center_y = self.height() // 2
        margin = 24
        painter.drawLine(margin, margin, self.width() - margin, self.height() - margin)
        painter.drawLine(self.width() - margin, margin, margin, self.height() - margin)
        painter.drawLine(margin, center_y, self.width() - margin, center_y)
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#6D819A")))
        painter.drawEllipse(QtCore.QPoint(center_x, center_y), 4, 4)


class MotilidadReadOnlyDialog(QDialog):
    """Modal de solo lectura para mostrar motilidad de una graduaciÃ³n."""
 
    def __init__(self, motilidad_data, fecha="", parent=None):
        super().__init__(parent)
        self.motilidad_data = self._normalize(motilidad_data)
        self.fecha = fecha or ""
        self.setWindowTitle("Motilidad")
        self.setModal(True)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.resize(740, 500)
        self.setMinimumSize(700, 470)
        self._build_ui()

    def _normalize(self, data):
        base = {
            "od": {k: False for k in MOTILIDAD_DIRECCIONES},
            "oi": {k: False for k in MOTILIDAD_DIRECCIONES},
        }
        if not isinstance(data, dict):
            return base
        for eye in ("od", "oi"):
            eye_data = data.get(eye, {})
            if not isinstance(eye_data, dict):
                continue
            for key in MOTILIDAD_DIRECCIONES:
                base[eye][key] = bool(eye_data.get(key, False))
        return base

    def _eye_column(self, title, eye_widget):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        eye_card = QFrame()
        eye_card.setObjectName("eyeCard")
        eye_layout = QVBoxLayout(eye_card)
        eye_layout.setContentsMargins(12, 10, 12, 10)
        eye_layout.setSpacing(4)

        full_label = "OJO DERECHO" if title == "OD" else "OJO IZQUIERDO"
        lbl = QLabel(f"{full_label} ({title})")
        lbl.setObjectName("eyeTitle")
        lbl.setAlignment(Qt.AlignHCenter)
        hint = QLabel("Registro visual de posiciones")
        hint.setObjectName("eyeHint")
        hint.setAlignment(Qt.AlignHCenter)

        eye_layout.addWidget(lbl)
        eye_layout.addWidget(hint)
        eye_layout.addWidget(eye_widget, alignment=Qt.AlignHCenter)
        layout.addWidget(eye_card)
        return container

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #EEF3F9;
                font-family: "Segoe UI";
            }
            QWidget#motHeader {
                border-radius: 12px;
                border: 1px solid #D6E0ED;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F7FAFF, stop:1 #EAF2FF);
            }
            QLabel#motBadge {
                background: #1F7AE0;
                color: #FFFFFF;
                border-radius: 16px;
                font-size: 15px;
                font-weight: 800;
                min-width: 32px;
                min-height: 32px;
                max-width: 32px;
                max-height: 32px;
                qproperty-alignment: AlignCenter;
            }
            QGroupBox#motilidadCard {
                border: 1px solid #D4DDEA;
                border-radius: 12px;
                background: #FFFFFF;
            }
            QFrame#eyeCard {
                border: 1px solid #D7E1EE;
                border-radius: 12px;
                background: #F9FBFF;
            }
            QLabel#motHeading {
                font-size: 26px;
                font-weight: 800;
                color: #1F2D3D;
            }
            QLabel#motSubHeading {
                font-size: 13px;
                color: #4F6175;
            }
            QLabel#eyeTitle {
                font-size: 17px;
                font-weight: 800;
                color: #1D3557;
                letter-spacing: 0.5px;
            }
            QLabel#eyeHint {
                font-size: 11px;
                color: #6E7F92;
            }
            QFrame#legendDotOn {
                min-width: 12px;
                max-width: 12px;
                min-height: 12px;
                max-height: 12px;
                border-radius: 6px;
                background: #1F7AE0;
                border: 1px solid #1565C0;
            }
            QFrame#legendDotOff {
                min-width: 12px;
                max-width: 12px;
                min-height: 12px;
                max-height: 12px;
                border-radius: 6px;
                background: #FFFFFF;
                border: 1px solid #9FB0C5;
            }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        header = QWidget()
        header.setObjectName("motHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(10)
        badge = QLabel("M")
        badge.setObjectName("motBadge")
        header_layout.addWidget(badge, 0, Qt.AlignTop)
        header_text_layout = QVBoxLayout()
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        header_text_layout.setSpacing(2)
        title = QLabel("MOTILIDAD - VERSIONES")
        title.setObjectName("motHeading")
        header_text_layout.addWidget(title)
        subtitle = QLabel("Vista de motilidad registrada para esta graduacion.")
        subtitle.setObjectName("motSubHeading")
        header_text_layout.addWidget(subtitle)
        header_layout.addLayout(header_text_layout, 1)
        root.addWidget(header)

        if self.fecha:
            fecha_lbl = QLabel(f"Fecha: {self.fecha}")
            fecha_lbl.setObjectName("motSubHeading")
            root.addWidget(fecha_lbl)

        card = QGroupBox()
        card.setObjectName("motilidadCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(16)

        od_widget = MotilidadReadOnlyEyeWidget()
        oi_widget = MotilidadReadOnlyEyeWidget()
        od_widget.set_values(self.motilidad_data.get("od", {}))
        oi_widget.set_values(self.motilidad_data.get("oi", {}))

        card_layout.addWidget(self._eye_column("OD", od_widget), 1)
        card_layout.addWidget(self._eye_column("OI", oi_widget), 1)
        root.addWidget(card, 1)

        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(2, 0, 2, 0)
        legend_layout.setSpacing(14)
        legend_layout.addWidget(self._build_legend_item("legendDotOn", "Marcado"))
        legend_layout.addWidget(self._build_legend_item("legendDotOff", "Sin marcar"))
        legend_layout.addStretch()
        root.addLayout(legend_layout)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch()
        btn_cerrar = QPushButton("Aceptar")
        btn_cerrar.setFixedHeight(38)
        btn_cerrar.setMinimumWidth(130)
        btn_cerrar.clicked.connect(self.accept)
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #1F7AE0;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        footer.addWidget(btn_cerrar)
        root.addLayout(footer)

    def _build_legend_item(self, dot_name, text):
        item = QWidget()
        layout = QHBoxLayout(item)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        dot = QFrame()
        dot.setObjectName(dot_name)
        txt = QLabel(text)
        txt.setObjectName("motSubHeading")
        layout.addWidget(dot)
        layout.addWidget(txt)
        return item


class GraduacionDetalleDialog(QDialog):
    """Muestra el detalle completo de una graduacion en una ventana separada."""

    def __init__(self, paciente_data, graduacion_data, parent=None, graduacion_index=None):
        super().__init__(parent)
        self.paciente_data = paciente_data or {}
        self.graduacion_data = graduacion_data or {}
        self.graduacion_index = graduacion_index
        fecha = self.graduacion_data.get("fecha", "")
        self.setWindowTitle(f"Detalle de Graduacion - {fecha}")
        self.setWindowFlags(
            QtCore.Qt.Dialog
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.resize(980, 720)
        self._build_ui()

    def _safe_float(self, value):
        try:
            return float(value or 0)
        except (ValueError, TypeError):
            return 0.0

    def _estado_pago_texto(self):
        resumen = _graduacion_payment_summary(self.graduacion_data)
        monto_total = resumen["monto_total"]
        total_pagado = resumen["total_pagado"]
        saldo = resumen["saldo"]

        if total_pagado >= monto_total > 0:
            return "PAGADO"
        if total_pagado > 0:
            return f"PENDIENTE: S/. {saldo:.2f}"
        return f"SIN PAGAR: S/. {monto_total:.2f}"

    def _get_username_for_report(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "_get_username"):
            try:
                return parent._get_username()
            except Exception:
                pass
        if parent is not None and hasattr(parent, "username"):
            return getattr(parent, "username", None)
        return None

    def _get_nombre_optica_for_report(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "_get_nombre_optica"):
            try:
                return parent._get_nombre_optica()
            except Exception:
                pass
        return "Mi Ã“ptica"

    def generar_expediente_solo_graduacion(self):
        """Genera expediente PDF usando solo la graduacion actual."""
        try:
            generar_expediente_pdf = _import_generador_expediente_pdf()
            username = self._get_username_for_report()
            nombre_optica = self._get_nombre_optica_for_report()

            paciente_filtrado = dict(self.paciente_data)
            paciente_filtrado["historial_graduaciones"] = [dict(self.graduacion_data)]

            pdf_path = generar_expediente_pdf(paciente_filtrado, nombre_optica, username)
            QMessageBox.information(self, "Ã‰xito", f"Expediente generado en:\n{pdf_path}")
            open_pdf_with_chrome(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el expediente:\n{e}")

    def generar_boleta_solo_graduacion(self):
        """Genera boleta PDF con la plantilla configurada para esta graduacion."""
        try:
            parent = self.parent()
            # Reutilizar la logica existente del dialogo principal de detalles.
            if parent is not None and hasattr(parent, "generar_boleta_pdf"):
                parent.generar_boleta_pdf(self.graduacion_data)
                return

            # Fallback si se abre fuera de PatientDetailsDialog.
            username = self._get_username_for_report()
            nombre_optica = self._get_nombre_optica_for_report()
            paciente_nombre = self.paciente_data.get('nombre', '')
            monto = _graduacion_service_amount(self.graduacion_data)

            productos = _graduacion_boleta_productos(self.graduacion_data)
            total = _graduacion_total_amount(self.graduacion_data)

            subtotal = total
            igv = 0.0

            generador = GeneradorBoletasPlantilla(username)
            datos_boleta = {
                'nombre_optica': nombre_optica,
                'ruc': '12345678901',
                'direccion': 'DirecciÃ³n no configurada',
                'numero_boleta': f"GRAD-{self.paciente_data.get('id', 'S/N')}",
                'fecha': self.graduacion_data.get('fecha', ''),
                'cliente': paciente_nombre,
                'productos': productos,
                'subtotal': subtotal,
                'igv': igv,
                'total': total,
                'metodo_pago': 'Efectivo',
                'pie_pagina': 'Gracias por su compra'
            }
            pdf_path = generador.generar_boleta(datos_boleta)
            QMessageBox.information(self, "Ã‰xito", f"Boleta generada en:\n{pdf_path}")
            open_pdf_with_chrome(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la boleta:\n{e}")

    def editar_graduacion(self):
        """Abre la pagina de graduacion con los datos actuales precargados."""
        parent = self.parent()
        if parent is not None and hasattr(parent, "abrir_graduacion_en_formulario"):
            parent.abrir_graduacion_en_formulario(self.graduacion_data, self.graduacion_index)
            self.accept()
            return
        QMessageBox.warning(self, "Editar", "No se pudo abrir el formulario de ediciÃ³n.")

    def _build_rx_table(self, title, od_data, oi_data):
        group = QGroupBox(title)
        layout = QGridLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)

        headers = ["Ojo", "Esferico", "Cilindro", "Eje", "AV", "DIP", "Adicion", "Prisma"]
        for col_idx, header in enumerate(headers):
            lbl = QLabel(f"<b>{header}</b>")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl, 0, col_idx)
            layout.setColumnStretch(col_idx, 1)

        rows = [("OD", od_data or {}), ("OI", oi_data or {})]
        for row_idx, (eye, data) in enumerate(rows, start=1):
            values = [
                eye,
                str(data.get("esferico", "")),
                str(data.get("cilindro", "")),
                str(data.get("eje", "")),
                str(data.get("av", "")),
                str(data.get("distp", "")),
                str(data.get("adicmedia", "")),
                str(data.get("prisma", "")),
            ]
            for col_idx, value in enumerate(values):
                lbl = QLabel(value if value else "-")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("padding: 4px 6px; border: 1px solid #e0e0e0; border-radius: 3px;")
                layout.addWidget(lbl, row_idx, col_idx)

        return group

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll_area = QtWidgets.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        root.addWidget(scroll_area)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        scroll_area.setWidget(content_widget)

        info_group = QGroupBox("Datos Generales")
        info_layout = QGridLayout(info_group)
        info_layout.setHorizontalSpacing(16)
        info_layout.setVerticalSpacing(8)

        nombre = self.paciente_data.get("nombre", "N/A")
        dni = self.paciente_data.get("dni", "N/A")
        fecha = self.graduacion_data.get("fecha", "")
        optometra = self.graduacion_data.get("optometra", "")
        proxima = self.graduacion_data.get("proxima_cita", "")
        cobro = _graduacion_total_amount(self.graduacion_data)

        info_layout.addWidget(QLabel("<b>Paciente:</b>"), 0, 0)
        info_layout.addWidget(QLabel(str(nombre)), 0, 1)
        info_layout.addWidget(QLabel("<b>DNI:</b>"), 0, 2)
        info_layout.addWidget(QLabel(str(dni)), 0, 3)

        info_layout.addWidget(QLabel("<b>Fecha:</b>"), 1, 0)
        info_layout.addWidget(QLabel(str(fecha)), 1, 1)
        info_layout.addWidget(QLabel("<b>Optometra:</b>"), 1, 2)
        info_layout.addWidget(QLabel(str(optometra)), 1, 3)

        info_layout.addWidget(QLabel("<b>Proxima Cita:</b>"), 2, 0)
        info_layout.addWidget(QLabel(str(proxima or "-")), 2, 1)
        info_layout.addWidget(QLabel("<b>Total Venta:</b>"), 2, 2)
        info_layout.addWidget(QLabel(f"S/. {cobro:.2f}"), 2, 3)

        info_layout.addWidget(QLabel("<b>Estado Pago:</b>"), 3, 0)
        info_layout.addWidget(QLabel(self._estado_pago_texto()), 3, 1, 1, 3)
        content_layout.addWidget(info_group)

        content_layout.addWidget(
            self._build_rx_table(
                "Vision de Lejos",
                self.graduacion_data.get("lejos_od", {}),
                self.graduacion_data.get("lejos_oi", {}),
            )
        )
        content_layout.addWidget(
            self._build_rx_table(
                "Vision de Cerca",
                self.graduacion_data.get("cerca_od", {}),
                self.graduacion_data.get("cerca_oi", {}),
            )
        )

        obs_group = QGroupBox("Observacion")
        obs_layout = QVBoxLayout(obs_group)
        txt_obs = QTextEdit()
        txt_obs.setReadOnly(True)
        txt_obs.setMinimumHeight(80)
        txt_obs.setPlainText(str(self.graduacion_data.get("observacion", "")))
        obs_layout.addWidget(txt_obs)
        content_layout.addWidget(obs_group)

        items = self.graduacion_data.get("items_venta", []) or []
        pagos = _graduacion_payment_summary(self.graduacion_data)["pagos"]
        monto_graduacion = _graduacion_service_amount(self.graduacion_data)

        productos_group = QGroupBox("Productos Vendidos")
        productos_layout = QVBoxLayout(productos_group)
        total_items = 0.0
        desglose_lineas = [f"GraduaciÃ³n: S/. {monto_graduacion:.2f}"]

        if items:
            for it in items:
                nombre = str(it.get("nombre", "Producto"))
                codigo = str(it.get("codigo", ""))
                categoria = str(it.get("categoria", ""))
                cantidad = int(it.get("cantidad", 0) or 0)
                precio_unit = self._safe_float(it.get("precio_unitario", 0))
                total = self._safe_float(it.get("total", 0))
                total_items += total

                card = QtWidgets.QFrame()
                card.setStyleSheet(
                    "QFrame {"
                    "background-color: #fafafa;"
                    "border: 1px solid #e0e0e0;"
                    "border-radius: 6px;"
                    "}"
                )
                card_layout = QGridLayout(card)
                card_layout.setContentsMargins(10, 8, 10, 8)
                card_layout.setHorizontalSpacing(12)
                card_layout.setVerticalSpacing(4)

                card_layout.addWidget(QLabel(f"<b>Producto:</b> {nombre}"), 0, 0, 1, 2)
                card_layout.addWidget(QLabel(f"<b>CÃ³digo:</b> {codigo or '-'}"), 1, 0)
                card_layout.addWidget(QLabel(f"<b>CategorÃ­a:</b> {categoria or '-'}"), 1, 1)
                card_layout.addWidget(QLabel(f"<b>Cantidad:</b> {cantidad}"), 2, 0)
                card_layout.addWidget(QLabel(f"<b>P. Unit:</b> S/. {precio_unit:.2f}"), 2, 1)
                card_layout.addWidget(QLabel(f"<b>Total:</b> S/. {total:.2f}"), 3, 0, 1, 2)

                productos_layout.addWidget(card)
                desglose_lineas.append(f"{nombre} x{cantidad}: S/. {total:.2f}")

            productos_layout.addWidget(QLabel(f"<b>Total Productos:</b> S/. {total_items:.2f}"))
        else:
            productos_layout.addWidget(QLabel("Sin productos vendidos"))

        total_general = _graduacion_total_amount(self.graduacion_data)
        resumen_frame = QtWidgets.QFrame()
        resumen_frame.setStyleSheet(
            "QFrame {"
            "background-color: #f3f6fb;"
            "border: 1px solid #d8e2f0;"
            "border-radius: 6px;"
            "}"
        )
        resumen_layout = QVBoxLayout(resumen_frame)
        resumen_layout.setContentsMargins(10, 8, 10, 8)
        resumen_layout.setSpacing(4)
        resumen_layout.addWidget(QLabel("<b>Desglose de Cobro</b>"))
        for linea in desglose_lineas:
            resumen_layout.addWidget(QLabel(linea))
        resumen_layout.addWidget(QLabel(f"<b>Total General: S/. {total_general:.2f}</b>"))
        productos_layout.addWidget(resumen_frame)

        content_layout.addWidget(productos_group)

        pagos_group = QGroupBox("Pagos Parciales")
        pagos_layout = QVBoxLayout(pagos_group)
        if pagos:
            table_pagos = QTableWidget()
            table_pagos.setColumnCount(3)
            table_pagos.setRowCount(len(pagos))
            table_pagos.setHorizontalHeaderLabels(["Fecha", "Monto", "Observacion"])
            table_pagos.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table_pagos.setSelectionMode(QAbstractItemView.NoSelection)
            table_pagos.verticalHeader().setVisible(False)
            table_pagos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table_pagos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            table_pagos.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table_pagos.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            table_pagos.setMaximumHeight(150)

            total_pagado = 0.0
            for row_idx, pago in enumerate(pagos):
                pago = pago or {}
                monto = self._safe_float(pago.get("monto", 0))
                total_pagado += monto
                table_pagos.setItem(row_idx, 0, QTableWidgetItem(str(pago.get("fecha", ""))))
                table_pagos.setItem(row_idx, 1, QTableWidgetItem(f"S/. {monto:.2f}"))
                table_pagos.setItem(row_idx, 2, QTableWidgetItem(str(pago.get("observacion", ""))))

            pagos_layout.addWidget(table_pagos)
            pagos_layout.addWidget(QLabel(f"<b>Total Pagado:</b> S/. {total_pagado:.2f}"))
        else:
            pagos_layout.addWidget(QLabel("Sin pagos parciales"))
        content_layout.addWidget(pagos_group)

        footer = QHBoxLayout()
        footer.setContentsMargins(12, 10, 12, 12)
        footer.addStretch()

        btn_expediente = QPushButton("Generar Expediente")
        btn_expediente.setMinimumWidth(170)
        btn_expediente.setMinimumHeight(34)
        btn_expediente.clicked.connect(self.generar_expediente_solo_graduacion)
        footer.addWidget(btn_expediente)

        btn_boleta = QPushButton("Generar Boleta")
        btn_boleta.setMinimumWidth(150)
        btn_boleta.setMinimumHeight(34)
        btn_boleta.clicked.connect(self.generar_boleta_solo_graduacion)
        footer.addWidget(btn_boleta)

        btn_editar = QPushButton("Editar")
        btn_editar.setMinimumWidth(120)
        btn_editar.setMinimumHeight(34)
        btn_editar.clicked.connect(self.editar_graduacion)
        footer.addWidget(btn_editar)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setMinimumWidth(120)
        btn_cerrar.setMinimumHeight(34)
        btn_cerrar.clicked.connect(self.accept)
        footer.addWidget(btn_cerrar)
        root.addLayout(footer)


class PatientDetailsDialog(QDialog):
    """DiÃ¡logo para ver los detalles y el historial de graduaciones de un paciente."""
    def __init__(self, paciente_data, parent=None, context_parent=None):
        super().__init__(parent)
        self.paciente_data = paciente_data
        self._original_patient_data = copy.deepcopy(paciente_data or {})
        self.setWindowTitle(f"Detalles del Paciente: {self.paciente_data.get('nombre')}")
        self.parent_app = context_parent or parent
        
        # Obtener username de varias fuentes posibles
        self.username = None
        context = self.parent_app
        if context:
            # Intentar obtener del parent directo
            if hasattr(context, 'username'):
                self.username = context.username
            # Si parent tiene parent_app, obtener de ahÃ­
            elif hasattr(context, 'parent_app') and hasattr(context.parent_app, 'username'):
                self.username = context.parent_app.username
        
        
        # Configurar la ventana para permitir maximizar/minimizar
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.WindowMaximizeButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowCloseButtonHint
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        
        # Establecer un tamaÃ±o inicial razonable
        self.resize(900, 700)
        self.setMinimumSize(760, 560)
        self.setSizeGripEnabled(True)
        
        self.setup_ui()

    def create_svg_icon(self, svg_str, size=24):
        """Crea un QIcon a partir de un string SVG."""
        from PyQt5.QtGui import QIcon, QPixmap, QPainter
        pixmap = QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        renderer = QSvgRenderer(svg_str.encode())
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)

    def _register_sidebar_button(self, button, label):
        if not hasattr(self, "_sidebar_buttons"):
            self._sidebar_buttons = []
        button.setProperty("_sidebar_label", str(label or ""))
        self._sidebar_buttons.append(button)

    def _position_sidebar_toggle(self):
        sidebar_widget = getattr(self, "sidebar_widget", None)
        toggle_btn = getattr(self, "sidebar_toggle_btn", None)
        if not sidebar_widget or not toggle_btn:
            return
        try:
            # Reserve a small gutter on the right so the toggle never sits on top of sidebar labels.
            x = max(0, sidebar_widget.width() - toggle_btn.width() - 2)
            y = max(8, (sidebar_widget.height() - toggle_btn.height()) // 2)
            toggle_btn.move(x, y)
            toggle_btn.raise_()
        except RuntimeError:
            pass

    def _apply_sidebar_button_state(self, show_labels, button_width):
        for button in getattr(self, "_sidebar_buttons", []):
            label = str(button.property("_sidebar_label") or "")
            button.setText(label if show_labels else "")
            button.setFixedWidth(button_width)
            button.setFixedHeight(48)
            button.setToolTip(label)
            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 8px;
                    text-align: left;
                    color: #111827;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.1);
                }
                QPushButton:disabled {
                    color: #9CA3AF;
                }
            """)

    def _set_sidebar_expanded(self, expanded, animate=True):
        self._sidebar_expanded = bool(expanded)
        width = 224 if self._sidebar_expanded else 80
        button_width = 154 if self._sidebar_expanded else 48

        sidebar_widget = getattr(self, "sidebar_widget", None)
        if sidebar_widget and not animate:
            sidebar_widget.setMinimumWidth(width)
            sidebar_widget.setMaximumWidth(width)

        if self._sidebar_expanded:
            self._apply_sidebar_button_state(True, button_width)

        toggle_btn = getattr(self, "sidebar_toggle_btn", None)
        if toggle_btn:
            toggle_btn.setText("‹" if self._sidebar_expanded else "›")
            toggle_btn.setToolTip("Comprimir opciones" if self._sidebar_expanded else "Expandir opciones")

        if sidebar_widget and animate:
            try:
                start_width = max(1, sidebar_widget.width())
                sidebar_widget.setMinimumWidth(start_width)
                sidebar_widget.setMaximumWidth(start_width)

                group = QtCore.QParallelAnimationGroup(self)
                for prop_name in (b"minimumWidth", b"maximumWidth"):
                    anim = QtCore.QPropertyAnimation(sidebar_widget, prop_name, self)
                    anim.setDuration(210)
                    anim.setStartValue(start_width)
                    anim.setEndValue(width)
                    anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
                    anim.valueChanged.connect(lambda _value: self._position_sidebar_toggle())
                    group.addAnimation(anim)

                def _finish_sidebar_animation():
                    sidebar_widget.setMinimumWidth(width)
                    sidebar_widget.setMaximumWidth(width)
                    if not self._sidebar_expanded:
                        self._apply_sidebar_button_state(False, button_width)
                    self._position_sidebar_toggle()

                group.finished.connect(_finish_sidebar_animation)
                self._sidebar_anim = group
                group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
            except RuntimeError:
                pass
        elif not self._sidebar_expanded:
            self._apply_sidebar_button_state(False, button_width)

        self._position_sidebar_toggle()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "sidebar_widget", None) and event.type() == QtCore.QEvent.Resize:
            QtCore.QTimer.singleShot(0, self._position_sidebar_toggle)
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            event.accept()
            self.done(QDialog.Rejected)
            return
        super().keyPressEvent(event)

    def reject(self):
        # QDialog ejecuta reject() al presionar Esc o cerrar con la X.
        # done() termina solo el event-loop del modal, sin cerrar la app.
        try:
            self.done(QDialog.Rejected)
        except RuntimeError:
            pass

    def closeEvent(self, event):
        event.accept()
        try:
            self.done(QDialog.Rejected)
        except RuntimeError:
            pass

    def _safe_parent_app(self):
        parent = getattr(self, "parent_app", None)
        return parent if _is_qt_object_alive(parent) else None

    def _safe_message(self, icon, title, text):
        parent = self if _is_qt_object_alive(self) else None
        try:
            if icon == "warning":
                QMessageBox.warning(parent, title, text)
            elif icon == "critical":
                QMessageBox.critical(parent, title, text)
            else:
                QMessageBox.information(parent, title, text)
        except RuntimeError:
            pass

    def _run_dialog_action(self, callback):
        if not _is_qt_object_alive(self):
            return
        try:
            callback()
        except RuntimeError as exc:
            if "wrapped C/C++ object" not in str(exc):
                self._safe_message("critical", "Error", str(exc))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._safe_message("critical", "Error", str(exc))

    def _safe_load_parent_patients(self):
        parent = self._safe_parent_app()
        if parent is None or not hasattr(parent, "load_patients"):
            return
        try:
            parent.load_patients()
        except RuntimeError:
            pass

    def _get_username(self):
        """Resolver el username del contexto de forma segura."""
        if getattr(self, 'username', None):
            return self.username
        try:
            parent = self._safe_parent_app()
            username = getattr(parent, 'username', None) or getattr(parent, 'user_id', None) or getattr(parent, 'user', None)
            return username if username else 'default'
        except Exception:
            return 'default'

    def _find_patient_index(self, patients):
        return _find_patient_record_index(
            patients,
            getattr(self, "_original_patient_data", {}),
            self.paciente_data,
        )

    def _refresh_original_patient_data(self):
        self._original_patient_data = copy.deepcopy(self.paciente_data or {})

    def _build_graduacion_payment_summary(self, graduacion):
        return _graduacion_payment_summary(graduacion)

    def _get_nombre_optica(self):
        """Resolver el nombre de la óptica de forma segura desde distintos contextos.

        Intenta obtenerlo desde:
        1. cargar_datos_optica (remoto/local consolidado)
        2. El archivo de configuración de la óptica (configuracion_optica.txt)
        3. self.parent_app.home_page.nombre_optica_label si existe
        4. Fallback a 'Mi Óptica'
        """
        username = self._get_username()
        
        # 1. Intenta cargar desde el orquestador de datos (soporta remoto para NANCY)
        try:
            from utils.file_handler import cargar_datos_optica
            datos = cargar_datos_optica(username, prefer_remote=True)
            if datos and datos.get("nombre_optica") and datos.get("nombre_optica") != "Mi Óptica":
                return datos["nombre_optica"]
        except Exception:
            pass

        # 2. Intenta cargar desde el archivo de configuración directo
        try:
            from utils.file_handler import cargar_nombre_optica
            nombre_optica = cargar_nombre_optica(username)
            if nombre_optica and nombre_optica != "Mi Óptica":
                return nombre_optica
        except Exception:
            pass
        
        # Caso ventana principal con atributo home_page
        try:
            parent_app = self._safe_parent_app()
            if parent_app and getattr(parent_app, 'home_page', None):
                home = parent_app.home_page
                if hasattr(home, 'nombre_optica_label') and home.nombre_optica_label:
                    txt = home.nombre_optica_label.text().replace("Bienvenido al Sistema de GestiÃ³n de ", "").strip()
                    if txt and txt != username:
                        return txt
        except Exception:
            pass

        # Intentar otras rutas comunes
        try:
            # A veces parent_app es la ventana principal en un atributo distinto
            main_win = self._safe_parent_app()
            if main_win and hasattr(main_win, 'nombre_optica_label'):
                return main_win.nombre_optica_label.text().strip()
        except Exception:
            pass

        # Fallback al nombre por defecto
        return 'Mi Ã“ptica'

    def _get_contract_graduacion(self):
        graduaciones = self.paciente_data.get('historial_graduaciones', []) or []
        row = -1
        try:
            if hasattr(self, "graduaciones_table") and self.graduaciones_table is not None:
                row = self.graduaciones_table.currentRow()
        except Exception:
            row = -1

        if 0 <= row < len(graduaciones) and isinstance(graduaciones[row], dict):
            return graduaciones[row], row

        latest = _resolve_latest_graduacion(self.paciente_data)
        if isinstance(latest, dict) and latest:
            for idx, grad in enumerate(graduaciones):
                if grad is latest or grad == latest:
                    return grad, idx
            return latest, None

        if graduaciones and isinstance(graduaciones[-1], dict):
            return graduaciones[-1], len(graduaciones) - 1

        return {}, None

    def _build_contract_number(self, graduacion, grad_index=None):
        existing = str((graduacion or {}).get("contrato_numero", "") or "").strip()
        if existing:
            return existing

        dni_digits = ''.join(filter(str.isdigit, str(self.paciente_data.get("dni", "") or "")))
        dni_tail = (dni_digits[-3:] if dni_digits else "000").rjust(3, "0")
        seq = (grad_index + 1) if isinstance(grad_index, int) and grad_index >= 0 else 1
        return f"{seq:03d}{dni_tail}"

    def _build_contract_products_summary(self, graduacion):
        items = (graduacion or {}).get("items_venta", []) or []
        names = []
        for item in items:
            if not isinstance(item, dict):
                continue
            nombre = str(item.get("nombre", "") or "").strip()
            if nombre:
                names.append(nombre)
        return names

    def generar_contrato_pdf(self):
        graduacion, grad_index = self._get_contract_graduacion()
        if not graduacion:
            QMessageBox.warning(self, "Contrato", "No hay una graduación disponible para generar el contrato.")
            return

        from utils.generador_contrato import build_contract_number
        from gui.dialogs.pdf_viewer_dialog import PDFViewerDialog

        contract_number = build_contract_number(self.paciente_data, graduacion, grad_index)
        nombre_optica = self._get_nombre_optica()
        progress = QtWidgets.QProgressDialog("Generando contrato...", None, 0, 0, self)
        progress.setWindowTitle("Contrato")
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()
        QtWidgets.QApplication.processEvents()

        thread = QThread(self)
        worker = _ContractPdfWorker(
            paciente_data=self.paciente_data,
            graduacion=graduacion,
            nombre_optica=nombre_optica,
            username=self._get_username(),
            contract_number=contract_number,
        )
        worker.moveToThread(thread)
        self._contract_pdf_thread = thread
        self._contract_pdf_worker = worker

        def _finish(pdf_path, error):
            try:
                progress.close()
            except Exception:
                pass
            try:
                thread.quit()
            except Exception:
                pass
            try:
                worker.deleteLater()
            except Exception:
                pass
            try:
                thread.deleteLater()
            except Exception:
                pass
            self._contract_pdf_thread = None
            self._contract_pdf_worker = None

            if error:
                QMessageBox.critical(self, "Contrato", f"No se pudo generar el contrato.\n\n{error}")
                return
            if not pdf_path:
                QMessageBox.warning(self, "Contrato", "No se generó el archivo del contrato.")
                return
            try:
                viewer = PDFViewerDialog(pdf_path, self)
                viewer.exec_()
            except Exception as open_error:
                QMessageBox.critical(self, "Contrato", f"El contrato se generó, pero no se pudo abrir.\n\n{open_error}")

        thread.started.connect(worker.run)
        worker.finished.connect(_finish)
        thread.start()

    def setup_ui(self):
        # Establecer estilo moderno
        self.setStyleSheet("""
            QDialog { 
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
                font-size: 14px;
            }
            QLabel { 
                color: #424242;
                font-size: 12px;
            }
            QTableWidget { 
                border: 1px solid #e0e0e0;
                background-color: #ffffff;
                gridline-color: #f5f5f5;
                border-radius: 4px;
            }
            QTableWidget::item { 
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #fafafa;
                border: none;
                padding: 10px;
                font-weight: 600;
                color: #191919;
                font-size: 11px;
                border-bottom: 2px solid #e0e0e0;
            }
        """)
        
        # Layout principal con sidebar
        main_container = QHBoxLayout(self)
        main_container.setSpacing(0)
        main_container.setContentsMargins(0, 0, 0, 0)
        
        # ===== SIDEBAR LATERAL (EXPANDIDO POR DEFECTO) =====
        self._sidebar_buttons = []
        self._sidebar_expanded = False
        sidebar = QVBoxLayout()
        sidebar.setSpacing(12)
        sidebar.setContentsMargins(12, 24, 12, 24)
        
# SVGs para los iconos (Actualizados segÃºn tus indicaciones visuales)

        # 1. Documento (Hoja con texto) - Para Expediente
        svg_expediente = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
        </svg>"""
        
        # 2. Boleta Ãºnica (Recibo con borde dentado)
        svg_boleta = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M18 17H6v-2h12v2zm0-4H6v-2h12v2zm0-4H6V7h12v2zM3 22l1.5-1.5L6 22l1.5-1.5L9 22l1.5-1.5L12 22l1.5-1.5L15 22l1.5-1.5L18 22l1.5-1.5L21 22V2l-1.5 1.5L18 2l-1.5 1.5L15 2l-1.5 1.5L12 2l-1.5 1.5L9 2 7.5 3.5 6 2 4.5 3.5 3 2v20z"/>
        </svg>"""
        
        # 3. Signo MÃ¡s (Add)
        svg_mas = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
        </svg>"""
        
        # 4. Varias Boletas (Pila de documentos/Capas)
        svg_boletas = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H8V4h12v12z"/>
        </svg>"""
        
        # 5. Imprimir
        svg_imprimir = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 8h-1V3H6v5H5c-1.66 0-3 1.34-3 3v6h4v4h12v-4h4v-6c0-1.66-1.34-3-3-3zM8 5h8v3H8V5zm8 12v5H8v-5h8zm2-2v-2H6v2H4v-4c0-.55.45-1 1-1h14c.55 0 1 .45 1 1v4h-2z"/>
        </svg>"""
        
        # 6. Pago en Partes (Bolsa de Dinero)
        svg_pago_partes = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
        </svg>"""
        
        # 7. Explorador de Archivos (Carpeta con documentos)
        svg_explorador = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <defs>
                <linearGradient id="folderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#42a5f5;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#1976d2;stop-opacity:1" />
                </linearGradient>
            </defs>
            <path d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z" fill="url(#folderGrad)"/>
            <rect x="6" y="10" width="3" height="4" fill="white" opacity="0.7" rx="0.5"/>
            <rect x="10.5" y="10" width="3" height="4" fill="white" opacity="0.7" rx="0.5"/>
            <rect x="15" y="10" width="3" height="4" fill="white" opacity="0.7" rx="0.5"/>
        </svg>"""
        
        # 8. Cerrar (X)
        svg_cerrar = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/>
        </svg>"""

        # 9. Motilidad (ojo)
        svg_motilidad = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 5c-5 0-9.27 3.11-11 7 1.73 3.89 6 7 11 7s9.27-3.11 11-7c-1.73-3.89-6-7-11-7zm0 12c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8a3 3 0 100 6 3 3 0 000-6z"/>
        </svg>"""
        
        # BotÃ³n cerrar sidebar
        # BotÃ³n Expediente
        btn_expediente = QPushButton()
        btn_expediente.setIcon(self.create_svg_icon(svg_expediente))
        btn_expediente.setIconSize(QtCore.QSize(28, 28))
        btn_expediente.setFixedWidth(48)
        btn_expediente.setFixedHeight(48)
        btn_expediente.setToolTip("Generar Expediente PDF")
        btn_expediente.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_expediente.clicked.connect(lambda _checked=False: self._run_dialog_action(self.generar_expediente_pdf))
        self._register_sidebar_button(btn_expediente, "Expediente PDF")
        sidebar.addWidget(btn_expediente, 0, QtCore.Qt.AlignHCenter)
        
        # BotÃ³n Ver Boleta
        btn_boleta = QPushButton()
        btn_boleta.setIcon(self.create_svg_icon(svg_boleta))
        btn_boleta.setIconSize(QtCore.QSize(28, 28))
        btn_boleta.setFixedWidth(48)
        btn_boleta.setFixedHeight(48)
        btn_boleta.setToolTip("Ver Ãšltima Boleta")
        btn_boleta.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_boleta.clicked.connect(lambda _checked=False: self._run_dialog_action(self.ver_boleta_ultima_graduacion))
        self._register_sidebar_button(btn_boleta, "Ultima boleta")
        sidebar.addWidget(btn_boleta, 0, QtCore.Qt.AlignHCenter)
        
        # Separador
        separator1 = QtWidgets.QFrame()
        separator1.setFrameShape(QtWidgets.QFrame.HLine)
        separator1.setStyleSheet("color: #e0e0e0;")
        sidebar.addWidget(separator1)
        
        # BotÃ³n Nueva GraduaciÃ³n (con SVG +)
        btn_graduacion = QPushButton()
        btn_graduacion.setIcon(self.create_svg_icon(svg_mas))
        btn_graduacion.setIconSize(QtCore.QSize(28, 28))
        btn_graduacion.setFixedWidth(48)
        btn_graduacion.setFixedHeight(48)
        btn_graduacion.setToolTip("Registrar Nueva GraduaciÃ³n")
        btn_graduacion.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_graduacion.clicked.connect(lambda _checked=False: self._run_dialog_action(self.registrar_nueva_visita))
        self._register_sidebar_button(btn_graduacion, "Nueva graduacion")
        sidebar.addWidget(btn_graduacion, 0, QtCore.Qt.AlignHCenter)
        
        # BotÃ³n Ver todas las boletas
        btn_todas_boletas = QPushButton()
        btn_todas_boletas.setIcon(self.create_svg_icon(svg_boletas))
        btn_todas_boletas.setIconSize(QtCore.QSize(28, 28))
        btn_todas_boletas.setFixedWidth(48)
        btn_todas_boletas.setFixedHeight(48)
        btn_todas_boletas.setToolTip("Ver Todas las Boletas")
        btn_todas_boletas.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_todas_boletas.clicked.connect(lambda _checked=False: self._run_dialog_action(self.ver_todas_boletas))
        self._register_sidebar_button(btn_todas_boletas, "Todas las boletas")
        sidebar.addWidget(btn_todas_boletas, 0, QtCore.Qt.AlignHCenter)
        
        # BotÃ³n Historial de Citas (Calendario)
        btn_historial_citas = QPushButton()
        svg_calendario = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="16" rx="2"/>
            <path d="M 3 9 L 21 9"/>
            <line x1="9" y1="1" x2="9" y2="3"/>
            <line x1="15" y1="1" x2="15" y2="3"/>
            <circle cx="7" cy="12" r="1"/>
            <circle cx="12" cy="12" r="1"/>
            <circle cx="17" cy="12" r="1"/>
            <circle cx="7" cy="16.5" r="1"/>
            <circle cx="12" cy="16.5" r="1"/>
        </svg>"""
        btn_historial_citas.setIcon(self.create_svg_icon(svg_calendario))
        btn_historial_citas.setIconSize(QtCore.QSize(28, 28))
        btn_historial_citas.setFixedWidth(48)
        btn_historial_citas.setFixedHeight(48)
        btn_historial_citas.setToolTip("Historial de Citas")
        btn_historial_citas.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_historial_citas.clicked.connect(lambda _checked=False: self._run_dialog_action(self.ver_historial_citas))
        self._register_sidebar_button(btn_historial_citas, "Historial citas")
        sidebar.addWidget(btn_historial_citas, 0, QtCore.Qt.AlignHCenter)

        # BotÃ³n Motilidad (segÃºn fila seleccionada de graduaciÃ³n)
        btn_motilidad = QPushButton()
        btn_motilidad.setIcon(self.create_svg_icon(svg_motilidad))
        btn_motilidad.setIconSize(QtCore.QSize(28, 28))
        btn_motilidad.setFixedWidth(48)
        btn_motilidad.setFixedHeight(48)
        btn_motilidad.setToolTip("Ver Motilidad de la graduaciÃ³n seleccionada")
        btn_motilidad.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_motilidad.clicked.connect(lambda _checked=False: self._run_dialog_action(self.ver_motilidad_graduacion))
        self._register_sidebar_button(btn_motilidad, "Motilidad")
        sidebar.addWidget(btn_motilidad, 0, QtCore.Qt.AlignHCenter)
        
        # BotÃ³n Imprimir
        btn_imprimir = QPushButton()
        btn_imprimir.setIcon(self.create_svg_icon(svg_imprimir))
        btn_imprimir.setIconSize(QtCore.QSize(28, 28))
        btn_imprimir.setFixedWidth(48)
        btn_imprimir.setFixedHeight(48)
        btn_imprimir.setToolTip("Imprimir Boleta")
        btn_imprimir.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_imprimir.clicked.connect(lambda _checked=False: self._run_dialog_action(self.imprimir_ultima_boleta))
        self._register_sidebar_button(btn_imprimir, "Imprimir")
        sidebar.addWidget(btn_imprimir, 0, QtCore.Qt.AlignHCenter)
        
        # BotÃ³n Pago en Partes
        btn_pago_parcial = QPushButton()
        # SVG para pago en partes (moneda con dos partes)
        svg_pago_parcial = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 1C6.48 1 2 5.48 2 11s4.48 10 10 10 10-4.48 10-10S17.52 1 12 1zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 7 15.5 7 14 7.67 14 8.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 7 8.5 7 7 7.67 7 8.5 7.67 10 8.5 10zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z"/>
        </svg>"""
        btn_pago_parcial.setIcon(self.create_svg_icon(svg_pago_parcial))
        btn_pago_parcial.setIconSize(QtCore.QSize(28, 28))
        btn_pago_parcial.setFixedWidth(48)
        btn_pago_parcial.setFixedHeight(48)
        btn_pago_parcial.setToolTip("Registrar Pago en Partes")
        btn_pago_parcial.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_pago_parcial.clicked.connect(lambda _checked=False: self._run_dialog_action(self.pago_en_partes))
        self._register_sidebar_button(btn_pago_parcial, "Pago en partes")
        sidebar.addWidget(btn_pago_parcial, 0, QtCore.Qt.AlignHCenter)
        
        # BotÃ³n Adjuntos (PDFs y Fotos)
        btn_adjuntos = QPushButton()
        svg_adjuntos = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" opacity="0.3"/><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zm-5.04-6.71l-2.75 3.54h2.63v2h-8v-2h2.04l2.75-3.54-1.97-2.36H6.5v-2h8v2h-2.63l1.97 2.36z"/>
        </svg>"""
        btn_adjuntos.setIcon(self.create_svg_icon(svg_adjuntos))
        btn_adjuntos.setIconSize(QtCore.QSize(28, 28))
        btn_adjuntos.setFixedWidth(48)
        btn_adjuntos.setFixedHeight(48)
        btn_adjuntos.setToolTip("Gestionar Adjuntos (PDFs y Fotos)")
        btn_adjuntos.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_adjuntos.clicked.connect(lambda _checked=False: self._run_dialog_action(self.abrir_gestor_adjuntos))
        self._register_sidebar_button(btn_adjuntos, "Adjuntos")
        sidebar.addWidget(btn_adjuntos, 0, QtCore.Qt.AlignHCenter)

        # Botón Contrato
        btn_contrato = QPushButton()
        svg_contrato = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm1 16H9v-2h6v2zm0-4H9v-2h6v2zm-2-5V3.5L18.5 9H13z"/>
        </svg>"""
        btn_contrato.setIcon(self.create_svg_icon(svg_contrato))
        btn_contrato.setIconSize(QtCore.QSize(28, 28))
        btn_contrato.setFixedWidth(48)
        btn_contrato.setFixedHeight(48)
        btn_contrato.setToolTip("Contrato")
        btn_contrato.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_contrato.clicked.connect(lambda _checked=False: self._run_dialog_action(self.generar_contrato_pdf))
        self._register_sidebar_button(btn_contrato, "Contrato")
        sidebar.addWidget(btn_contrato, 0, QtCore.Qt.AlignHCenter)

        # BotÃ³n Editar
        btn_editar = QPushButton()
        svg_editar = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
        </svg>"""
        btn_editar.setIcon(self.create_svg_icon(svg_editar))
        btn_editar.setIconSize(QtCore.QSize(28, 28))
        btn_editar.setFixedWidth(48)
        btn_editar.setFixedHeight(48)
        btn_editar.setToolTip("Editar Paciente")
        btn_editar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        btn_editar.clicked.connect(lambda _checked=False: self._run_dialog_action(self.editar_paciente))
        self._register_sidebar_button(btn_editar, "Editar")
        
        # Verificar permiso editar
        parent_app = self._safe_parent_app()
        if parent_app and hasattr(parent_app, 'is_helper') and parent_app.is_helper:
             if hasattr(parent_app, 'puede_hacer_accion') and not parent_app.puede_hacer_accion('pacientes', 'editar'):
                btn_editar.setEnabled(False)
                btn_editar.setToolTip("No tienes permiso para editar pacientes")
        
        sidebar.addWidget(btn_editar, 0, QtCore.Qt.AlignHCenter)

        # BotÃ³n Eliminar
        btn_eliminar = QPushButton()
        svg_eliminar = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
        </svg>"""
        btn_eliminar.setIcon(self.create_svg_icon(svg_eliminar))
        btn_eliminar.setIconSize(QtCore.QSize(28, 28))
        btn_eliminar.setFixedWidth(48)
        btn_eliminar.setFixedHeight(48)
        btn_eliminar.setToolTip("Eliminar Paciente")
        btn_eliminar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #ffebee;
            }
            QPushButton:pressed {
                background-color: #ffcdd2;
            }
        """)
        btn_eliminar.clicked.connect(lambda _checked=False: self._run_dialog_action(self.eliminar_paciente))
        self._register_sidebar_button(btn_eliminar, "Eliminar")
        
        # Verificar permiso eliminar
        parent_app = self._safe_parent_app()
        if parent_app and hasattr(parent_app, 'is_helper') and parent_app.is_helper:
             if hasattr(parent_app, 'puede_hacer_accion') and not parent_app.puede_hacer_accion('pacientes', 'eliminar'):
                btn_eliminar.setEnabled(False)
                btn_eliminar.setToolTip("No tienes permiso para eliminar pacientes")

        sidebar.addWidget(btn_eliminar, 0, QtCore.Qt.AlignHCenter)
        
        sidebar.addStretch()
        
        # Widget contenedor para el sidebar
        sidebar_widget = QtWidgets.QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border-right: 1px solid #e0e0e0;
            }
        """)
        sidebar_widget.setMinimumWidth(80)
        sidebar_widget.setMaximumWidth(80)
        
        self.sidebar_widget = sidebar_widget
        sidebar_widget.installEventFilter(self)
        self.sidebar_toggle_btn = QPushButton("›", sidebar_widget)
        self.sidebar_toggle_btn.setFixedSize(24, 56)
        self.sidebar_toggle_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.sidebar_toggle_btn.setToolTip("Expandir opciones")
        self.sidebar_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 12px;
                font-size: 18px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
        """)
        self.sidebar_toggle_btn.clicked.connect(
            lambda _checked=False: self._set_sidebar_expanded(not getattr(self, "_sidebar_expanded", False))
        )
        self._set_sidebar_expanded(False, animate=False)
        main_container.addWidget(sidebar_widget, 0)
        
        # ===== CONTENIDO PRINCIPAL =====
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # ===== CABECERA CON INFORMACIÃ“N BÃSICA =====
        header_group = QGroupBox("InformaciÃ³n del Paciente")
        header_layout = QtWidgets.QHBoxLayout(header_group)
        header_layout.setSpacing(20)
        header_layout.setContentsMargins(12, 12, 12, 12)

        # Avatar circular con iniciales
        nombre_paciente = str(self.paciente_data.get('nombre', '') or '')
        initials = ''.join([p[0].upper() for p in nombre_paciente.split()[:2] if p]) or 'P'
        avatar = QLabel(initials)
        avatar.setFixedSize(90, 90)
        avatar.setAlignment(QtCore.Qt.AlignCenter)
        avatar.setStyleSheet('''
            QLabel {
                border-radius: 45px; 
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #42a5f5, stop:1 #1976d2); 
                color: white; 
                font-weight: 700; 
                font-size: 32px;
            }
        ''')

        # InformaciÃ³n en columnas
        info_layout = QGridLayout()
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Fila 1
        dni_label = QLabel("<b>DNI:</b>")
        dni_label.setStyleSheet("color: #191919; font-weight: 600;")
        self.dni_value = QLabel(self.paciente_data.get('dni', 'N/A'))
        self.dni_value.setWordWrap(True)
        
        nombre_label = QLabel("<b>Nombre:</b>")
        nombre_label.setStyleSheet("color: #191919; font-weight: 600;")
        self.nombre_value = QLabel(nombre_paciente or 'N/A')
        self.nombre_value.setWordWrap(True)
        
        info_layout.addWidget(dni_label, 0, 0)
        info_layout.addWidget(self.dni_value, 0, 1)
        info_layout.addWidget(nombre_label, 0, 2)
        info_layout.addWidget(self.nombre_value, 0, 3)
        info_layout.setColumnStretch(0, 0)
        info_layout.setColumnStretch(1, 1)
        info_layout.setColumnStretch(2, 0)
        info_layout.setColumnStretch(3, 1)
        
        # Fila 2
        fecha_label = QLabel("<b>Fecha Nacimiento:</b>")
        fecha_label.setStyleSheet("color: #191919; font-weight: 600;")
        self.fecha_value = QLabel(self.paciente_data.get('fecha_nacimiento', 'N/A'))
        self.fecha_value.setWordWrap(True)
        
        edad_label = QLabel("<b>Edad:</b>")
        edad_label.setStyleSheet("color: #191919; font-weight: 600;")
        self.edad_value = QLabel(f"{self.paciente_data.get('edad', 'N/A')} aÃ±os")
        
        info_layout.addWidget(fecha_label, 1, 0)
        info_layout.addWidget(self.fecha_value, 1, 1)
        info_layout.addWidget(edad_label, 1, 2)
        info_layout.addWidget(self.edad_value, 1, 3)
        
        # Fila 3
        telefono_label = QLabel("<b>TelÃ©fono:</b>")
        telefono_label.setStyleSheet("color: #191919; font-weight: 600;")
        self.telefono_value = QLabel(str(self.paciente_data.get('telefono', '') or 'N/A'))
        self.telefono_value.setWordWrap(True)

        email_label = QLabel("<b>Email:</b>")
        email_label.setStyleSheet("color: #191919; font-weight: 600;")
        self.email_value = QLabel(str(self.paciente_data.get('email', '') or 'N/A'))
        self.email_value.setWordWrap(True)

        info_layout.addWidget(telefono_label, 2, 0)
        info_layout.addWidget(self.telefono_value, 2, 1)
        info_layout.addWidget(email_label, 2, 2)
        info_layout.addWidget(self.email_value, 2, 3)

        # Fila 4
        ultima_visita_label = QLabel("<b>Ãšltima Visita:</b>")
        ultima_visita_label.setStyleSheet("color: #191919; font-weight: 600;")
        self.ultima_visita_value = QLabel(_resolve_patient_last_visit_label(self.paciente_data))
        self.ultima_visita_value.setWordWrap(True)

        latest_grad = _resolve_latest_graduacion(self.paciente_data)
        monto_label = QLabel("<b>Ãšltimo Cobro:</b>")
        monto_label.setStyleSheet("color: #191919; font-weight: 600;")
        monto_cobrado = _graduacion_total_amount(latest_grad)
        self.monto_value = QLabel(f"S/. {monto_cobrado:.2f}")

        info_layout.addWidget(ultima_visita_label, 3, 0)
        info_layout.addWidget(self.ultima_visita_value, 3, 1)
        info_layout.addWidget(monto_label, 3, 2)
        info_layout.addWidget(self.monto_value, 3, 3)
        
        header_layout.addWidget(avatar, 0, QtCore.Qt.AlignTop)
        header_layout.addLayout(info_layout, 1)
        header_layout.addStretch()
        
        main_layout.addWidget(header_group)
        
        # ===== TABLA DE HISTORIAL DE GRADUACIONES =====
        graduaciones_group = QGroupBox("Historial de Graduaciones")
        graduaciones_layout = QVBoxLayout(graduaciones_group)
        graduaciones_layout.setContentsMargins(8, 8, 8, 8)
        
        self.graduaciones_table = QTableWidget()
        self.graduaciones_table.setColumnCount(38)
        headers = [
            "Fecha", "Optómetra", "Próxima Cita",
            "Lejos OD Esf", "Lejos OD Cil", "Lejos OD Eje", "Lejos OD AV", "Lejos OD DP", "Lejos OD Prism", "Lejos OD Adic",
            "Lejos OI Esf", "Lejos OI Cil", "Lejos OI Eje", "Lejos OI AV", "Lejos OI DP", "Lejos OI Prism", "Lejos OI Adic",
            "Cerca OD Esf", "Cerca OD Cil", "Cerca OD Eje", "Cerca OD AV", "Cerca OD DP", "Cerca OD Prism", "Cerca OD Adic",
            "Cerca OI Esf", "Cerca OI Cil", "Cerca OI Eje", "Cerca OI AV", "Cerca OI DP", "Cerca OI Prism", "Cerca OI Adic",
            "Observación", "Cobro", "Productos Vendidos", "Pagos Parciales", "Estado Pago", "Comisión", "Nro. Contrato"
        ]
        self.graduaciones_table.setHorizontalHeaderLabels(headers)
        self.graduaciones_table.setAlternatingRowColors(True)
        self.graduaciones_table.verticalHeader().setDefaultSectionSize(36)
        self.graduaciones_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.graduaciones_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.graduaciones_table.itemDoubleClicked.connect(self.on_graduacion_double_click)
        
        header = self.graduaciones_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.graduaciones_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.graduaciones_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.load_graduaciones()
        self._insertar_columna_paciente_en_graduaciones()
        graduaciones_layout.addWidget(self.graduaciones_table)
        main_layout.addWidget(graduaciones_group, 1)

        # Agregar main_layout al contenedor principal
        main_content = QtWidgets.QWidget()
        main_content.setLayout(main_layout)
        main_container.addWidget(main_content, 1)

    def load_graduaciones(self):
        self.graduaciones_table.setRowCount(0)
        graduaciones = self.paciente_data.get('historial_graduaciones', [])
        for row_index, graduacion in enumerate(graduaciones):
            self.graduaciones_table.insertRow(row_index)
            
            fecha_item = QTableWidgetItem(graduacion.get("fecha", ""))
            fecha_item.setData(QtCore.Qt.UserRole, row_index)
            self.graduaciones_table.setItem(row_index, 0, fecha_item)
            self.graduaciones_table.setItem(row_index, 1, QTableWidgetItem(graduacion.get("optometra", "")))
            self.graduaciones_table.setItem(row_index, 2, QTableWidgetItem(graduacion.get("proxima_cita", "")))
            
            # VisiÃ³n de Lejos OD
            lejos_od = graduacion.get("lejos_od", {})
            self.graduaciones_table.setItem(row_index, 3, QTableWidgetItem(lejos_od.get("esferico", "")))
            self.graduaciones_table.setItem(row_index, 4, QTableWidgetItem(lejos_od.get("cilindro", "")))
            self.graduaciones_table.setItem(row_index, 5, QTableWidgetItem(lejos_od.get("eje", "")))
            self.graduaciones_table.setItem(row_index, 6, QTableWidgetItem(lejos_od.get("av", "")))
            self.graduaciones_table.setItem(row_index, 7, QTableWidgetItem(lejos_od.get("distp", "")))
            self.graduaciones_table.setItem(row_index, 8, QTableWidgetItem(lejos_od.get("prisma", "")))
            self.graduaciones_table.setItem(row_index, 9, QTableWidgetItem(lejos_od.get("adicmedia", "")))
            
            # VisiÃ³n de Lejos OI
            lejos_oi = graduacion.get("lejos_oi", {})
            self.graduaciones_table.setItem(row_index, 10, QTableWidgetItem(lejos_oi.get("esferico", "")))
            self.graduaciones_table.setItem(row_index, 11, QTableWidgetItem(lejos_oi.get("cilindro", "")))
            self.graduaciones_table.setItem(row_index, 12, QTableWidgetItem(lejos_oi.get("eje", "")))
            self.graduaciones_table.setItem(row_index, 13, QTableWidgetItem(lejos_oi.get("av", "")))
            self.graduaciones_table.setItem(row_index, 14, QTableWidgetItem(lejos_oi.get("distp", "")))
            self.graduaciones_table.setItem(row_index, 15, QTableWidgetItem(lejos_oi.get("prisma", "")))
            self.graduaciones_table.setItem(row_index, 16, QTableWidgetItem(lejos_oi.get("adicmedia", "")))
            
            # VisiÃ³n de Cerca OD
            cerca_od = graduacion.get("cerca_od", {})
            self.graduaciones_table.setItem(row_index, 17, QTableWidgetItem(cerca_od.get("esferico", "")))
            self.graduaciones_table.setItem(row_index, 18, QTableWidgetItem(cerca_od.get("cilindro", "")))
            self.graduaciones_table.setItem(row_index, 19, QTableWidgetItem(cerca_od.get("eje", "")))
            self.graduaciones_table.setItem(row_index, 20, QTableWidgetItem(cerca_od.get("av", "")))
            self.graduaciones_table.setItem(row_index, 21, QTableWidgetItem(cerca_od.get("distp", "")))
            self.graduaciones_table.setItem(row_index, 22, QTableWidgetItem(cerca_od.get("prisma", "")))
            self.graduaciones_table.setItem(row_index, 23, QTableWidgetItem(cerca_od.get("adicmedia", "")))
            
            # VisiÃ³n de Cerca OI
            cerca_oi = graduacion.get("cerca_oi", {})
            self.graduaciones_table.setItem(row_index, 24, QTableWidgetItem(cerca_oi.get("esferico", "")))
            self.graduaciones_table.setItem(row_index, 25, QTableWidgetItem(cerca_oi.get("cilindro", "")))
            self.graduaciones_table.setItem(row_index, 26, QTableWidgetItem(cerca_oi.get("eje", "")))
            self.graduaciones_table.setItem(row_index, 27, QTableWidgetItem(cerca_oi.get("av", "")))
            self.graduaciones_table.setItem(row_index, 28, QTableWidgetItem(cerca_oi.get("distp", "")))
            self.graduaciones_table.setItem(row_index, 29, QTableWidgetItem(cerca_oi.get("prisma", "")))
            self.graduaciones_table.setItem(row_index, 30, QTableWidgetItem(cerca_oi.get("adicmedia", "")))
            
            # ObservaciÃ³n, Cobro e Items Vendidos
            self.graduaciones_table.setItem(row_index, 31, QTableWidgetItem(graduacion.get("observacion", "")))
            self.graduaciones_table.setItem(row_index, 32, QTableWidgetItem(str(graduacion.get("monto_cobrado", ""))))
            
            # Mostrar items vendidos (si existen)
            items_venta = graduacion.get("items_venta", [])
            items_texto_list = []
            for item in items_venta:
                i_nombre = item.get('producto') or item.get('nombre') or 'Producto'
                i_cant = item.get('cantidad', 1)
                i_sub = float(item.get('subtotal') or item.get('total', 0) or 0)
                items_texto_list.append(f"{i_nombre} (x{i_cant} - S/. {i_sub:.2f})")
            
            items_texto = ", ".join(items_texto_list)
            item_prod = QTableWidgetItem(items_texto)
            item_prod.setFlags(item_prod.flags() ^ QtCore.Qt.ItemIsEditable) # Read-only
            self.graduaciones_table.setItem(row_index, 33, item_prod)
            
            # Mostrar pagos parciales / adelantos legacy
            resumen_pago = self._build_graduacion_payment_summary(graduacion)
            pagos_parciales = resumen_pago["pagos"]
            if pagos_parciales:
                pagos_texto_list = []
                for pago in pagos_parciales:
                    monto_pago = _safe_float_payment(pago.get('monto', 0))
                    pagos_texto_list.append(f"S/. {monto_pago:.2f} ({pago.get('fecha', '')})")
                pagos_texto = "; ".join(pagos_texto_list)
                item_pago = QTableWidgetItem(pagos_texto)
            else:
                item_pago = QTableWidgetItem("")
            
            item_pago.setFlags(item_pago.flags() ^ QtCore.Qt.ItemIsEditable) # Read-only
            self.graduaciones_table.setItem(row_index, 34, item_pago)
            
            # ===== ESTADO DE PAGO =====
            monto_total = _graduacion_total_amount(graduacion)
            
            # Calcular total pagado
            total_pagado = 0
            if pagos_parciales:
                for pago in pagos_parciales:
                    monto_pago = pago.get('monto', 0)
                    if isinstance(monto_pago, str):
                        try:
                            monto_pago = float(monto_pago)
                        except (ValueError, TypeError):
                            monto_pago = 0
                    total_pagado += monto_pago
            
            # Determinar estado
            if total_pagado >= monto_total:
                estado_texto = "PAGADO"
                estado_color = (0, 150, 0)  # Verde
            elif total_pagado > 0:
                saldo = monto_total - total_pagado
                estado_texto = f"PENDIENTE: S/. {saldo:.2f}"
                estado_color = (255, 165, 0)  # Naranja
            else:
                estado_texto = f"SIN PAGAR: S/. {monto_total:.2f}"
                estado_color = (200, 0, 0)  # Rojo
            
            monto_total = resumen_pago["monto_total"]
            total_pagado = resumen_pago["total_pagado"]
            saldo = resumen_pago["saldo"]
            if total_pagado >= monto_total > 0:
                estado_texto = "PAGADO"
            elif total_pagado > 0:
                estado_texto = f"PENDIENTE: S/. {saldo:.2f}"
            else:
                estado_texto = f"SIN PAGAR: S/. {monto_total:.2f}"

            item_estado = QTableWidgetItem(estado_texto)
            item_estado.setForeground(QtGui.QColor(*estado_color))
            item_estado.setFont(QtGui.QFont("Arial", 9, QtGui.QFont.Bold))
            item_estado.setFlags(item_estado.flags() ^ QtCore.Qt.ItemIsEditable) # Read-only
            self.graduaciones_table.setItem(row_index, 35, item_estado)

            comision_monto = _safe_float_payment(graduacion.get("comision_monto", 0))
            item_comision = QTableWidgetItem(f"S/. {comision_monto:.2f}" if comision_monto > 0 else "")
            item_comision.setFlags(item_comision.flags() ^ QtCore.Qt.ItemIsEditable)
            self.graduaciones_table.setItem(row_index, 36, item_comision)

            contrato_numero = str(graduacion.get("contrato_numero", "") or "").strip()
            if not contrato_numero:
                contrato_numero = self._build_contract_number(graduacion, row_index)
            item_contrato = QTableWidgetItem(contrato_numero)
            item_contrato.setFlags(item_contrato.flags() ^ QtCore.Qt.ItemIsEditable)
            self.graduaciones_table.setItem(row_index, 37, item_contrato)

    def _insertar_columna_paciente_en_graduaciones(self):
        """Inserta una columna visible con el nombre del paciente."""
        try:
            if self.graduaciones_table.columnCount() >= 39:
                return

            self.graduaciones_table.insertColumn(1)
            self.graduaciones_table.setHorizontalHeaderItem(1, QTableWidgetItem("Paciente"))

            paciente_nombre_base = str(self.paciente_data.get("nombre", "") or "").strip()
            graduaciones = self.paciente_data.get('historial_graduaciones', []) or []
            for row_index, graduacion in enumerate(graduaciones):
                nombre_fila = str(
                    graduacion.get("paciente_nombre")
                    or graduacion.get("nombre")
                    or paciente_nombre_base
                    or ""
                ).strip()
                self.graduaciones_table.setItem(row_index, 1, QTableWidgetItem(nombre_fila))

            self.graduaciones_table.setColumnCount(39)
        except Exception:
            pass

    def on_graduacion_double_click(self, item):
        """Abre una ventana con el detalle completo de la graduacion seleccionada."""
        try:
            row = item.row()
            fecha_item = self.graduaciones_table.item(row, 0)
            grad_index = fecha_item.data(QtCore.Qt.UserRole) if fecha_item else row

            graduaciones = self.paciente_data.get('historial_graduaciones', [])
            if grad_index is None:
                grad_index = row
            if grad_index < 0 or grad_index >= len(graduaciones):
                QMessageBox.warning(self, "Detalle", "No se encontro la graduacion seleccionada.")
                return

            graduacion = graduaciones[grad_index]
            dialog = GraduacionDetalleDialog(self.paciente_data, graduacion, self, grad_index)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el detalle:\n{e}")
            
    def generar_boleta_pdf(self, graduacion):
        try:
            generador = GeneradorBoletasPlantilla(self._get_username())
            
            nombre_optica = self._get_nombre_optica()
            paciente_nombre = self.paciente_data.get('nombre', '')
            monto = _graduacion_service_amount(graduacion)
            
            # Crear lista de productos (graduaciÃ³n + productos vendidos)
            productos = _graduacion_boleta_productos(graduacion)

            # Los precios ya incluyen IGV; no sumar IGV adicional al total final.
            subtotal = _graduacion_total_amount(graduacion)
            igv = 0.0
            total = subtotal
            
            # Datos para la boleta
            datos_boleta = {
                'nombre_optica': nombre_optica,
                'ruc': '12345678901',
                'direccion': 'DirecciÃ³n no configurada',
                'numero_boleta': f"GRAD-{self.paciente_data.get('id', 'S/N')}",
                'fecha': graduacion.get('fecha', ''),
                'cliente': paciente_nombre,
                'productos': productos,
                'subtotal': subtotal,
                'igv': igv,
                'total': total,
                'metodo_pago': 'Efectivo',
                'pie_pagina': 'Gracias por su compra'
            }
            
            pdf_path = generador.generar_boleta(datos_boleta)
            QMessageBox.information(self, "Ã‰xito", f"Boleta generada correctamente en:\n{pdf_path}")
            open_pdf_with_chrome(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la boleta: {e}")
    
    def imprimir_ultima_boleta(self):
        """Imprime la Ãºltima boleta generada en la impresora Bluetooth."""
        try:
            generador = GeneradorBoletasPlantilla(self._get_username())
            
            # Obtener Ãºltima graduaciÃ³n
            graduaciones = self.paciente_data.get('historial_graduaciones', [])
            if not graduaciones:
                QMessageBox.warning(self, "Advertencia", "No hay graduaciones registradas para este paciente")
                return
            
            # Usar la Ãºltima graduaciÃ³n
            graduacion = graduaciones[-1]
            
            # Generar la boleta
            nombre_optica = self._get_nombre_optica()
            paciente_nombre = self.paciente_data.get('nombre', '')
            monto = _graduacion_service_amount(graduacion)
            
            # Crear lista de productos
            productos = _graduacion_boleta_productos(graduacion)

            # Datos para la boleta
            datos_boleta = {
                'nombre_optica': nombre_optica,
                'ruc': '12345678901',
                'direccion': 'DirecciÃ³n no configurada',
                'numero_boleta': f"GRAD-{self.paciente_data.get('id', 'S/N')}",
                'fecha': graduacion.get('fecha', ''),
                'cliente': paciente_nombre,
                'productos': productos,
                'subtotal': _graduacion_total_amount(graduacion),
                'igv': 0.0,
                'total': _graduacion_total_amount(graduacion),
                'metodo_pago': 'Efectivo',
                'pie_pagina': 'Gracias por su compra'
            }
            
            # Generar PDF
            pdf_path = generador.generar_boleta(datos_boleta)
            
            # Mostrar diÃ¡logo de selecciÃ³n de impresora
            from gui.dialogs.printer_selection_dialog import PrinterSelectionDialog
            printer_dialog = PrinterSelectionDialog(self)
            if printer_dialog.exec_() != QDialog.Accepted:
                return
            
            printer_name = printer_dialog.get_selected_printer()
            
            # Imprimir con la impresora seleccionada
            success, message = print_boleta(pdf_path, printer_name)
            
            if success:
                QMessageBox.information(self, "Ã‰xito", f"Boleta enviada a la impresora\n{message}")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo imprimir la boleta:\n{message}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al imprimir boleta: {e}")

    def generar_nota_venta_pdf(self, graduacion):
        try:
            generar_expediente_pdf = _import_generador_expediente_pdf()
            nombre_optica = self._get_nombre_optica()
            paciente_data = self.paciente_data.copy()
            paciente_data['historial_graduaciones'] = [graduacion]
            pdf_path = generar_expediente_pdf(paciente_data, nombre_optica, self._get_username())
            QMessageBox.information(self, "Ã‰xito", f"Nota de venta generada correctamente en:\n{pdf_path}")
            open_pdf_with_chrome(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la nota de venta: {e}")
            
    def save_changes(self):
        cache = get_global_cache()
        pacientes = cache.get_pacientes(self._get_username())
        patient_index = self._find_patient_index(pacientes)
        if patient_index is None:
            QMessageBox.warning(self, "Error", "No se encontrÃ³ el paciente original para guardar el historial.")
            return
        
        # Obtener historial original para comparar
        original_historial = self.paciente_data.get('historial_graduaciones', [])
        
        new_graduaciones = []
        for row in range(self.graduaciones_table.rowCount()):
            # Recolectar datos de la tabla con los Ã­ndices ACTUALIZADOS
            current_data = {
                "fecha": self.graduaciones_table.item(row, 0).text(),
                "optometra": self.graduaciones_table.item(row, 1).text(),
                "proxima_cita": self.graduaciones_table.item(row, 2).text(),
                "lejos_od": {
                    "esferico": self.graduaciones_table.item(row, 3).text(),
                    "cilindro": self.graduaciones_table.item(row, 4).text(),
                    "eje": self.graduaciones_table.item(row, 5).text(),
                    "av": self.graduaciones_table.item(row, 6).text(),
                    "distp": self.graduaciones_table.item(row, 7).text(),
                    "prisma": self.graduaciones_table.item(row, 8).text(),
                    "adicmedia": self.graduaciones_table.item(row, 9).text(),
                },
                "lejos_oi": {
                    "esferico": self.graduaciones_table.item(row, 10).text(),
                    "cilindro": self.graduaciones_table.item(row, 11).text(),
                    "eje": self.graduaciones_table.item(row, 12).text(),
                    "av": self.graduaciones_table.item(row, 13).text(),
                    "distp": self.graduaciones_table.item(row, 14).text(),
                    "prisma": self.graduaciones_table.item(row, 15).text(),
                    "adicmedia": self.graduaciones_table.item(row, 16).text(),
                },
                "cerca_od": {
                    "esferico": self.graduaciones_table.item(row, 17).text(),
                    "cilindro": self.graduaciones_table.item(row, 18).text(),
                    "eje": self.graduaciones_table.item(row, 19).text(),
                    "av": self.graduaciones_table.item(row, 20).text(),
                    "distp": self.graduaciones_table.item(row, 21).text(),
                    "prisma": self.graduaciones_table.item(row, 22).text(),
                    "adicmedia": self.graduaciones_table.item(row, 23).text(),
                },
                "cerca_oi": {
                    "esferico": self.graduaciones_table.item(row, 24).text(),
                    "cilindro": self.graduaciones_table.item(row, 25).text(),
                    "eje": self.graduaciones_table.item(row, 26).text(),
                    "av": self.graduaciones_table.item(row, 27).text(),
                    "distp": self.graduaciones_table.item(row, 28).text(),
                    "prisma": self.graduaciones_table.item(row, 29).text(),
                    "adicmedia": self.graduaciones_table.item(row, 30).text(),
                },
                "observacion": self.graduaciones_table.item(row, 31).text(),
                "monto_cobrado": self.graduaciones_table.item(row, 32).text(),
                "contrato_numero": self.graduaciones_table.item(row, 37).text() if self.graduaciones_table.item(row, 37) else "",
            }
            
            # Preservar datos no editables (items, pagos, etc) y detectar cambios
            if row < len(original_historial):
                original = original_historial[row]
                current_data['items_venta'] = original.get('items_venta', [])
                current_data['pagos_parciales'] = original.get('pagos_parciales', [])
                current_data['es_pago_parcial'] = original.get('es_pago_parcial', False)
                current_data['motilidad_versiones'] = original.get('motilidad_versiones', {})
                current_data['registrado_por'] = original.get('registrado_por', '')
                current_data['venta_relacionada_id'] = original.get('venta_relacionada_id')
                current_data['comision_activada'] = original.get('comision_activada', False)
                current_data['comision_porcentaje'] = original.get('comision_porcentaje', 0.0)
                current_data['comision_monto'] = original.get('comision_monto', 0.0)
                current_data['comision_usuario'] = original.get('comision_usuario', '')
                current_data['fue_editado'] = original.get('fue_editado', False)
                if not current_data.get('contrato_numero'):
                    current_data['contrato_numero'] = original.get('contrato_numero', '')
                
                # Detectar si hubo cambios sustanciales
                has_changes = False
                
                # Comparar campos principales
                fields_to_compare = ['fecha', 'optometra', 'proxima_cita', 'monto_cobrado', 'observacion']
                for field in fields_to_compare:
                    val_orig = str(original.get(field, '') or '').strip()
                    val_curr = str(current_data.get(field, '') or '').strip()
                    if val_orig != val_curr:
                        print(f"[DEBUG] Cambio detectado en '{field}': '{val_orig}' -> '{val_curr}'")
                        has_changes = True
                        break
                
                # Comparar diccionarios RX
                if not has_changes:
                    for rx in ['lejos_od', 'lejos_oi', 'cerca_od', 'cerca_oi']:
                        orig_rx = original.get(rx, {})
                        curr_rx = current_data.get(rx, {})
                        for k, v in curr_rx.items():
                            val_orig = str(orig_rx.get(k, '') or '').strip()
                            val_curr = str(v or '').strip()
                            if val_orig != val_curr:
                                print(f"[DEBUG] Cambio detectado en '{rx}.{k}': '{val_orig}' -> '{val_curr}'")
                                has_changes = True
                                break
                        if has_changes:
                            break
                
                # Si hay cambios, marcar flag de editado
                if has_changes:
                    print(f"[DEBUG] Marcando fila {row} como EDITADA")
                    current_data['fue_editado'] = True
                else:
                    print(f"[DEBUG] Fila {row} sin cambios")

            new_graduaciones.append(current_data)

        pacientes[patient_index]['historial_graduaciones'] = new_graduaciones
        
        # Actualizar tambiÃ©n el objeto local por si acaso
        self.paciente_data['historial_graduaciones'] = new_graduaciones

        cache = get_global_cache()
        cache.update_pacientes(self._get_username(), pacientes)
        self._refresh_original_patient_data()
        QMessageBox.information(self, "Ã‰xito", "Cambios en el historial guardados correctamente.")
        self.accept()

    def ver_boleta_ultima_graduacion(self):
        graduaciones = self.paciente_data.get('historial_graduaciones', [])
        if graduaciones:
            self.generar_boleta_pdf(graduaciones[-1])
        else:
            QMessageBox.information(self, "Boleta", "No hay graduaciones registradas para generar la boleta.")

    def registrar_nueva_visita(self):
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer
        from gui.widgets.circular_loader import LoaderOverlay
        
        # Encontrar la ventana principal navegando la jerarquÃ­a de parents
        main_window = None
        widget = self._safe_parent_app()
        
        while widget is not None:
            if hasattr(widget, 'mostrar_frame'):
                main_window = widget
                break
            widget = widget.parent() if hasattr(widget, 'parent') else None
        
        if not main_window:
            main_window = QApplication.activeWindow()
        
        if main_window and hasattr(main_window, 'mostrar_frame'):
            # Guardar los datos
            prefill_data = {
                'dni': self.paciente_data.get('dni', ''),
                'nombre': self.paciente_data.get('nombre', ''),
                'fecha_nacimiento': self.paciente_data.get('fecha_nacimiento', ''),
                'genero': self.paciente_data.get('genero', ''),
                '_modo_edicion_graduacion': False,
                '_graduacion_edit_index': None,
            }
            
            # Navegar a la pÃ¡gina
            main_window.mostrar_frame(2)
            
            # Mostrar el loader despuÃ©s de que la pÃ¡gina se cargue
            QTimer.singleShot(1000, lambda: self._show_loader_and_prefill_in_thread(main_window, prefill_data))
    
    def _show_loader_and_prefill_in_thread(self, main_window, prefill_data, attempt=0):
        """Muestra el loader y ejecuta el pre-llenado en un thread separado."""
        from PyQt5.QtCore import QTimer
        from gui.widgets.circular_loader import LoaderOverlay
        
        max_attempts = 10
        
        # Verificar si la pÃ¡gina CreatePatientPage existe
        if hasattr(main_window, 'create_patient_page'):
            page = main_window.create_patient_page
            
            # Mostrar loader circular
            overlay = LoaderOverlay(page, "Cargando graduaciÃ³n...")
            overlay.raise_()
            overlay.show()
            page.repaint()
            
            # Crear y ejecutar el worker en un thread separado
            self.prefill_worker = PrefillWorker(main_window, prefill_data)
            # Conectar la seÃ±al a un mÃ©todo de la instancia (Auto-Queued -> Thread Safe)
            self.prefill_worker.fill_requested.connect(self._do_actual_fill)
            self.prefill_worker.finished.connect(lambda: self._on_prefill_finished(overlay))
            self.prefill_worker.start()
        elif attempt < max_attempts:
            # Si aÃºn no existe, reintentar
            QTimer.singleShot(500, lambda: self._show_loader_and_prefill_in_thread(main_window, prefill_data, attempt + 1))
    
    def _do_actual_fill(self, page, data):
        """Ejecuta el llenado de campos. Se ejecuta en el thread principal."""
        fill_patient_form_fields(page, data)

    def _on_prefill_finished(self, overlay):
        """Se ejecuta cuando el worker termina de pre-llenar los datos."""
        # Ocultar el loader de forma segura
        if overlay:
            try:
                overlay.loader.stop()
                overlay.hide()
                overlay.deleteLater()
            except Exception:
                pass
        
        # Ahora que terminÃ³ el pre-llenado, podemos cerrar el diÃ¡logo de detalles
        self.close()
    
    def pago_en_partes(self):
        """Registra un pago en partes (adelanto) para el paciente."""
        try:
            # Mostrar el diÃ¡logo de pago en partes
            dialog = PagoEnPartesDialog(self.paciente_data, self)
            if dialog.exec_() != QDialog.Accepted:
                return
            
            monto_adelanto = dialog.get_monto_adelanto()
            if monto_adelanto is None or monto_adelanto <= 0:
                QMessageBox.warning(self, "Error", "Monto invÃ¡lido")
                return
            
            # Verificar que haya graduaciones registradas
            graduaciones = self.paciente_data.get('historial_graduaciones', [])
            if not graduaciones:
                QMessageBox.warning(self, "Error", "No hay graduaciones registradas para este paciente")
                return
            
            # Obtener la Ãºltima graduaciÃ³n
            ultima_graduacion = graduaciones[-1]
            
            # Si no existe "pagos_parciales", crearlo
            if 'pagos_parciales' not in ultima_graduacion:
                ultima_graduacion['pagos_parciales'] = []
            
            # Registrar el nuevo pago parcial
            from datetime import datetime
            pago = {
                'fecha': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'monto': monto_adelanto,
                'observacion': 'Adelanto registrado'
            }
            
            ultima_graduacion['pagos_parciales'].append(pago)
            
            # Guardar los cambios en la base de datos
            cache = get_global_cache()
            pacientes = cache.get_pacientes(self._get_username())
            patient_index = self._find_patient_index(pacientes)
            if patient_index is None:
                QMessageBox.warning(self, "Error", "No se encontrÃ³ el paciente original para registrar el pago.")
                return
            pacientes[patient_index]['historial_graduaciones'] = self.paciente_data.get('historial_graduaciones', [])
            
            cache.update_pacientes(self._get_username(), pacientes)
            self._refresh_original_patient_data()
            
            # Mostrar confirmaciÃ³n
            QMessageBox.information(
                self, 
                "Ã‰xito", 
                f"Pago en partes registrado:\nMonto: S/. {monto_adelanto:.2f}\nFecha: {pago['fecha']}"
            )
            
            # Actualizar la tabla de graduaciones
            self.load_graduaciones()
            
        except Exception as e:
            import traceback
            QMessageBox.critical(
                self, 
                "Error", 
                f"No se pudo registrar el pago en partes:\n{str(e)}\n\n{traceback.format_exc()}"
            )
    
    def abrir_gestor_adjuntos(self):
        """Abre el diÃ¡logo de gestiÃ³n de adjuntos."""
        try:
            paciente_nombre = self.paciente_data.get('nombre', 'Paciente')
            paciente_dni = self.paciente_data.get('dni', '')
            
            # Pasar todos los datos del paciente al diÃ¡logo
            dialog = GestorAdjuntosDialog(paciente_dni, paciente_nombre, self.paciente_data, self)
            dialog.exec_()
        except Exception as e:
            import traceback
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir el gestor de adjuntos:\n{str(e)}\n\n{traceback.format_exc()}"
            )

    def ver_motilidad_graduacion(self):
        """Muestra la motilidad de la graduaciÃ³n seleccionada (o la Ãºltima)."""
        graduaciones = self.paciente_data.get('historial_graduaciones', [])
        if not graduaciones:
            QMessageBox.information(self, "Motilidad", "No hay graduaciones registradas.")
            return

        selected_row = -1
        if hasattr(self, 'graduaciones_table') and self.graduaciones_table is not None:
            selected_row = self.graduaciones_table.currentRow()

        if selected_row < 0 or selected_row >= len(graduaciones):
            selected_row = len(graduaciones) - 1

        graduacion = graduaciones[selected_row]
        motilidad_data = graduacion.get('motilidad_versiones', {})
        fecha = graduacion.get('fecha', '')

        dialog = MotilidadReadOnlyDialog(motilidad_data, fecha, self)
        dialog.exec_()
    
    def toggle_sidebar(self):
        """Alterna entre sidebar compacto y expandido."""
        self._set_sidebar_expanded(not getattr(self, "_sidebar_expanded", False))
    
    def ver_todas_boletas(self):
        """Abre un diÃ¡logo mostrando todas las boletas del paciente."""
        dialog = TodasBoletasDialog(self.paciente_data, self._safe_parent_app(), self)
        dialog.exec_()
    
    def _guardar_paciente_data(self):
        """Guarda los datos del paciente en el JSON."""
        try:
            username = self._get_username()
            if not username:
                print("Error: No se pudo obtener el username")
                return False
            
            # Cargar todos los pacientes
            todos_pacientes = cargar_pacientes(username)
            patient_index = self._find_patient_index(todos_pacientes)
            if patient_index is None:
                print("Error: No se encontrÃ³ el paciente original para guardar")
                return False

            # Encontrar y actualizar el paciente actual
            todos_pacientes[patient_index] = copy.deepcopy(self.paciente_data)
            
            # Guardar todos los pacientes
            guardar_pacientes(username, todos_pacientes)
            self._refresh_original_patient_data()
            print(f"Paciente {self.paciente_data.get('nombre')} guardado correctamente.")
            return True
        except Exception as e:
            print(f"Error al guardar paciente: {str(e)}")
            return False
    
    def generar_expediente_pdf(self):
        try:
            generar_expediente_pdf = _import_generador_expediente_pdf()
            nombre_optica = self._get_nombre_optica()
            pdf_path = generar_expediente_pdf(self.paciente_data, nombre_optica, self._get_username())
            
            self._safe_message("information", "Exito", f"Expediente generado correctamente en:\n{pdf_path}")
            open_pdf_with_chrome(pdf_path)
        except ImportError:
            self._safe_message("critical", "Error", "La biblioteca 'generador_expediente' no se encontro. Asegurate de tener el archivo correcto.")
        except Exception as e:
            self._safe_message("critical", "Error", f"No se pudo generar el expediente: {e}")
    
    
    def ver_historial_citas(self):
        """Muestra el historial COMPLETO de citas del paciente (pendientes y completadas) buscando por DNI y nombre."""
        try:
            dni = self.paciente_data.get('dni', '')
            nombre_paciente = self.paciente_data.get('nombre', 'Paciente')
            
            print(f"[DEBUG ver_historial] Abriendo historial para: {nombre_paciente}, DNI: {dni}")
            
            # Obtener citas desde el sistema de citas
            from utils.data_cache_manager import get_global_cache
            from utils.appointments_model import AppointmentStatus
            
            cache = get_global_cache()
            
            # Obtener username - intentar de varias formas
            username = self.username
            if not username:
                username = getattr(self._safe_parent_app(), 'username', None)
            if not username:
                # Intentar obtener del parent
                if self.parent():
                    username = getattr(self.parent(), 'username', None)
            
            print(f"[DEBUG ver_historial] Username final: {username}")
            
            # Obtener TODAS las citas del usuario actual (sin filtrar por estado)
            todas_citas = cache.get_citas(username) if username else []
            
            if todas_citas:
                print(f"[DEBUG ver_historial] Primeras citas del cache:")
                for c in todas_citas[:3]:
                    print(f"  - DNI: {c.get('dni')}, Nombre: {c.get('nombre_paciente')}, Fecha: {c.get('fecha')}")
            
            # Filtrar citas por DNI - INCLUYENDO pendientes, completadas, canceladas, no-show
            citas_paciente = [c for c in todas_citas if c.get('dni') == dni]
            
            print(f"[DEBUG ver_historial] Buscando DNI: {dni}, Citas encontradas: {len(citas_paciente)}")
            
            # Mostrar citas antes del filtro de nombre
            print(f"[DEBUG] Citas antes de filtrar por nombre:")
            for c in citas_paciente:
                print(f"  - Nombre en cita: '{c.get('nombre_paciente')}', Paciente actual: '{nombre_paciente}'")
            
            # Filtrar por nombre si hay mÃºltiples pacientes con el mismo DNI
            # Aceptar citas que:
            # 1. Tengan el nombre del paciente exactamente, O
            # 2. Tengan nombre_paciente vacÃ­o (se asume que es del paciente actual)
            citas_filtradas = []
            for c in citas_paciente:
                nombre_en_cita = c.get('nombre_paciente', '').strip()
                # Si la cita tiene nombre vacÃ­o O el nombre coincide exactamente
                if not nombre_en_cita or nombre_en_cita.lower() == nombre_paciente.lower():
                    citas_filtradas.append(c)
            
            citas_paciente = citas_filtradas
            print(f"[DEBUG ver_historial] DespuÃ©s de filtrar por nombre: {len(citas_paciente)} citas")
            
            # Ordenar: Primero Pendientes, luego por fecha mÃ¡s reciente
            citas_paciente = sorted(
                citas_paciente, 
                key=lambda x: (
                    0 if x.get('estado') == 'Pendiente' else 1,  # Pendientes (0) primero
                    x.get('fecha', '')
                ), 
                reverse=True
            )
            # Ordenar estrictamente: Pendientes (arriba), Otros (medio), Completadas (abajo)
            def prioridad_estado(cita):
                estado = cita.get('estado', 'Pendiente')
                if estado == 'Pendiente':
                    return 2
                elif estado == 'Completada':
                    return 0
                else:
                    return 1

            citas_paciente = sorted(
                citas_paciente, 
                key=lambda x: (
                    prioridad_estado(x),
                    x.get('fecha', '')
                ), 
                reverse=True
            )
            
            print(f"[DEBUG ver_historial] Citas finales para mostrar: {len(citas_paciente)}")
            
            # Crear diÃ¡logo para mostrar historial
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Historial de Citas - {nombre_paciente}")
            dialog.setGeometry(100, 100, 1000, 700)
            
            layout = QVBoxLayout(dialog)
            
            # Tabla de citas
            table = QTableWidget()
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels(["Fecha", "Hora", "Doctor", "Tipo", "Estado", "Notas", "Acciones"])
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            
            # Llenar tabla si hay citas
            if citas_paciente:
                for i, cita in enumerate(citas_paciente):
                    table.insertRow(i)
                    
                    fecha = cita.get('fecha', 'N/A')
                    hora = cita.get('hora', 'N/A')
                    doctor = cita.get('doctor', 'Sin asignar')
                    tipo = cita.get('tipo', 'N/A')
                    estado = cita.get('estado', 'Pendiente')
                    notas = cita.get('notas', '')
                    cita_id = cita.get('cita_id', '')
                    
                    table.setItem(i, 0, QTableWidgetItem(fecha))
                    table.setItem(i, 1, QTableWidgetItem(hora))
                    table.setItem(i, 2, QTableWidgetItem(doctor))
                    table.setItem(i, 3, QTableWidgetItem(tipo))
                    table.setItem(i, 4, QTableWidgetItem(estado))
                    table.setItem(i, 5, QTableWidgetItem(notas))
                    
                    # Crear widget con botones de acciones
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout(actions_widget)
                    actions_layout.setContentsMargins(2, 2, 2, 2)
                    
                    # Botón Completada
                    btn_completada = QPushButton("Completada")
                    btn_completada.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 3px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #45a049;
                        }
                    """)
                    btn_completada.clicked.connect(lambda checked, cid=cita_id: self._cambiar_estado_cita(cid, 'Completada'))
                    actions_layout.addWidget(btn_completada)
                    
                    # Botón Cancelada
                    btn_cancelada = QPushButton("Cancelada")
                    btn_cancelada.setStyleSheet("""
                        QPushButton {
                            background-color: #f44336;
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 3px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #da190b;
                        }
                    """)
                    btn_cancelada.clicked.connect(lambda checked, cid=cita_id: self._cambiar_estado_cita(cid, 'Cancelada'))
                    actions_layout.addWidget(btn_cancelada)
                    
                    # Botón Pendiente
                    btn_pendiente = QPushButton("Pendiente")
                    btn_pendiente.setStyleSheet("""
                        QPushButton {
                            background-color: #FFC107;
                            color: black;
                            border: none;
                            padding: 5px;
                            border-radius: 3px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #ffb300;
                        }
                    """)
                    btn_pendiente.clicked.connect(lambda checked, cid=cita_id: self._cambiar_estado_cita(cid, 'Pendiente'))
                    actions_layout.addWidget(btn_pendiente)
                    
                    # Botón No-Show
                    btn_noshow = QPushButton("No-Show")
                    btn_noshow.setStyleSheet("""
                        QPushButton {
                            background-color: #FF9800;
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 3px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #e68900;
                        }
                    """)
                    btn_noshow.clicked.connect(lambda checked, cid=cita_id: self._cambiar_estado_cita(cid, 'No-Show'))
                    actions_layout.addWidget(btn_noshow)
                    
                    actions_layout.addStretch()
                    table.setCellWidget(i, 6, actions_widget)
            else:
                table.insertRow(0)
                item = QTableWidgetItem("No hay citas registradas")
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                table.setItem(0, 0, item)
                table.setSpan(0, 0, 1, 7)
            
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Stretch)
            
            layout.addWidget(table)
            
            # BotÃ³n para cerrar
            btn_cerrar = QPushButton("Cerrar")
            btn_cerrar.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0b7dda;
                }
            """)
            btn_cerrar.clicked.connect(dialog.close)
            layout.addWidget(btn_cerrar)
            
            dialog.exec_()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERROR] Error cargando historial de citas: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo cargar el historial de citas:\n{str(e)}")

    def _cambiar_estado_cita(self, cita_id, nuevo_estado):
        """Cambia el estado de una cita y actualiza el sistema."""
        try:
            from utils.data_cache_manager import get_global_cache
            from utils.appointments_model import AppointmentsManager
            from datetime import datetime
            
            print(f"[DEBUG] Cambiando estado de cita {cita_id} a {nuevo_estado}")
            
            # Obtener el manager de citas
            manager = AppointmentsManager(self.username)
            
            # Obtener todas las citas
            citas = manager.cargar_citas()
            
            # Buscar la cita y actualizar su estado
            cita_encontrada = None
            for cita in citas:
                if cita.get('cita_id') == cita_id:
                    cita['estado'] = nuevo_estado
                    cita['updated_at'] = datetime.now().isoformat()
                    cita_encontrada = cita
                    break
            
            if cita_encontrada:
                # Guardar las citas actualizadas
                manager.guardar_citas(citas)
                
                # Actualizar el cache global
                cache = get_global_cache()
                cache.actualizar_cita(self.username, cita_encontrada)
                
                print(f"[DEBUG] Cita {cita_id} actualizada a {nuevo_estado}")
                
                QMessageBox.information(self, "Ã‰xito", f"Cita actualizada a: {nuevo_estado}")
                
                # Recargar el historial
                self.ver_historial_citas()
            else:
                QMessageBox.warning(self, "Error", "No se encontrÃ³ la cita")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERROR] Error al cambiar estado de cita: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo cambiar el estado:\n{str(e)}")


    
    def _registrar_nueva_cita(self, parent_dialog, table):
        """Registra una nueva cita del paciente."""
        try:
            from datetime import datetime
            
            # Crear diÃ¡logo para nueva cita
            dialog = QDialog(parent_dialog)
            dialog.setWindowTitle("Registrar Nueva Cita")
            dialog.setGeometry(200, 150, 450, 350)
            
            layout = QVBoxLayout(dialog)
            
            # Label y input para motivo
            layout.addWidget(QLabel("Motivo de la visita:"))
            input_motivo = QTextEdit()
            input_motivo.setPlaceholderText("Ingrese el motivo de la visita...")
            input_motivo.setMaximumHeight(80)
            layout.addWidget(input_motivo)
            
            # Label y input para hora
            layout.addWidget(QLabel("Hora de la visita:"))
            input_hora = QLineEdit()
            hora_actual = datetime.now().strftime("%H:%M")
            input_hora.setText(hora_actual)
            layout.addWidget(input_hora)
            
            # Label y input para precio
            layout.addWidget(QLabel("Monto cobrado:"))
            input_precio = QLineEdit()
            input_precio.setText("0")
            input_precio.setPlaceholderText("Ingrese el monto...")
            layout.addWidget(input_precio)
            
            # Botones
            btn_layout = QHBoxLayout()
            
            btn_guardar = QPushButton("Guardar")
            btn_guardar.clicked.connect(lambda: self._guardar_cita(dialog, input_motivo.toPlainText(), input_hora.text(), input_precio.text(), table))
            btn_layout.addWidget(btn_guardar)
            
            btn_cancelar = QPushButton("Cancelar")
            btn_cancelar.clicked.connect(dialog.close)
            btn_layout.addWidget(btn_cancelar)
            
            layout.addLayout(btn_layout)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(parent_dialog, "Error", f"No se pudo crear el diÃ¡logo:\n{str(e)}")
    
    def _guardar_cita(self, dialog, motivo, hora, precio, table):
        """Guarda la nueva cita."""
        try:
            from datetime import datetime
            
            if not motivo.strip():
                QMessageBox.warning(dialog, "Error", "El motivo de la visita no puede estar vacÃ­o.")
                return
            
            if not hora.strip():
                QMessageBox.warning(dialog, "Error", "La hora no puede estar vacÃ­a.")
                return
            
            # Validar precio
            try:
                precio_float = float(precio.strip()) if precio.strip() else 0
            except ValueError:
                QMessageBox.warning(dialog, "Error", "El monto debe ser un nÃºmero vÃ¡lido.")
                return
            
            # Crear nueva cita
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            nueva_cita = {
                'fecha': fecha_hoy,
                'hora': hora,
                'optometra': self._get_username(),
                'observacion': motivo,
                'monto_cobrado': str(precio_float),
                'proxima_cita': 'Por agendar'
            }
            
            # Agregar a historial
            if 'historial_graduaciones' not in self.paciente_data:
                self.paciente_data['historial_graduaciones'] = []
            
            self.paciente_data['historial_graduaciones'].insert(0, nueva_cita)
            
            # Actualizar tabla
            table.insertRow(0)
            table.setItem(0, 0, QTableWidgetItem(nueva_cita['fecha']))
            table.setItem(0, 1, QTableWidgetItem(nueva_cita['optometra']))
            table.setItem(0, 2, QTableWidgetItem(nueva_cita['observacion']))
            table.setItem(0, 3, QTableWidgetItem(f"S/. {nueva_cita['monto_cobrado']}"))
            table.setItem(0, 4, QTableWidgetItem(nueva_cita['proxima_cita']))
            
            # Guardar en archivo
            self._guardar_paciente_data()
            
            QMessageBox.information(dialog, "Ã‰xito", "Cita registrada correctamente.")
            dialog.close()
            
        except Exception as e:
            QMessageBox.critical(dialog, "Error", f"No se pudo guardar la cita:\n{str(e)}")

    def abrir_graduacion_en_formulario(self, graduacion, grad_index=None):
        """Navega a la pagina de graduacion y precarga datos para editar."""
        try:
            if not isinstance(graduacion, dict):
                QMessageBox.warning(self, "Error", "No se encontraron datos de graduaciÃ³n.")
                return

            full_data = {
                'dni': self.paciente_data.get('dni', ''),
                'nombre': self.paciente_data.get('nombre', ''),
                'fecha_nacimiento': self.paciente_data.get('fecha_nacimiento', ''),
                'genero': self.paciente_data.get('genero', ''),
                'telefono': self.paciente_data.get('telefono', ''),
                'direccion': self.paciente_data.get('direccion', ''),
                'fecha': graduacion.get('fecha', ''),
                'optometra': graduacion.get('optometra', ''),
                'observacion': graduacion.get('observacion', ''),
                'monto_cobrado': graduacion.get('monto_cobrado', ''),
                'contrato_numero': graduacion.get('contrato_numero', ''),
                'cristales': graduacion.get('cristales', ''),
                'resina': graduacion.get('resina', ''),
                'color': graduacion.get('color', ''),
                'bifocal_tipo': graduacion.get('bifocal_tipo', ''),
                'multifocal_tipo': graduacion.get('multifocal_tipo', ''),
                'altura': graduacion.get('altura', ''),
                'luna_tipo': graduacion.get('luna_tipo', ''),
                'luna_costo': graduacion.get('luna_costo', ''),
                'luna_laboratorio': graduacion.get('luna_laboratorio', ''),
                'es_pago_parcial': graduacion.get('es_pago_parcial', False),
                'pagos_parciales': copy.deepcopy(graduacion.get('pagos_parciales', [])),
                'metodo_pago': graduacion.get('metodo_pago', ''),
                'metodos_pago_detalle': copy.deepcopy(graduacion.get('metodos_pago_detalle', [])),
                'pago_mixto': graduacion.get('pago_mixto', False),
                'items_venta': copy.deepcopy(graduacion.get('items_venta', [])),
                'comision_activada': graduacion.get('comision_activada', False),
                'comision_monto': graduacion.get('comision_monto', 0.0),
                'comision_porcentaje': graduacion.get('comision_porcentaje', 0.0),
                'comision_usuario': graduacion.get('comision_usuario', ''),
                'venta_relacionada_id': graduacion.get('venta_relacionada_id', ''),
                'deuda_id': graduacion.get('deuda_id', ''),
                'lejos_od': copy.deepcopy(graduacion.get('lejos_od', {})),
                'lejos_oi': copy.deepcopy(graduacion.get('lejos_oi', {})),
                'lejos_distp': graduacion.get('lejos_distp', ''),
                'cerca_od': copy.deepcopy(graduacion.get('cerca_od', {})),
                'cerca_oi': copy.deepcopy(graduacion.get('cerca_oi', {})),
                'cerca_distp': graduacion.get('cerca_distp', ''),
                '_modo_edicion_graduacion': True,
                '_graduacion_edit_index': grad_index if isinstance(grad_index, int) else None,
            }

            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtCore import QTimer

            main_window = None
            widget = self._safe_parent_app()
            while widget is not None:
                if hasattr(widget, 'mostrar_frame'):
                    main_window = widget
                    break
                widget = widget.parent() if hasattr(widget, 'parent') else None

            if not main_window:
                main_window = QApplication.activeWindow()

            if main_window and hasattr(main_window, 'mostrar_frame'):
                main_window.mostrar_frame(2)  # CreatePatientPage
                QTimer.singleShot(1000, lambda: self._show_loader_and_prefill_in_thread(main_window, full_data))
            else:
                QMessageBox.warning(self, "Error", "No se pudo encontrar la ventana principal para navegar.")
        except Exception as e:
            print(f"Error al abrir graduaciÃ³n en formulario: {e}")
            QMessageBox.critical(self, "Error", f"OcurriÃ³ un error al cargar los datos: {e}")

    def editar_paciente(self):
        """
        Maneja la acciÃ³n del botÃ³n Editar.
        - Si hay una fila de graduaciÃ³n seleccionada: Abre el formulario de graduaciÃ³n (CreatePatientPage) 
          con los datos de esa graduaciÃ³n precargados para ediciÃ³n/clonaciÃ³n.
        - Si NO hay fila seleccionada: Abre el diÃ¡logo de ediciÃ³n bÃ¡sica del paciente.
        """
        # Verificar si hay una fila seleccionada en la tabla de graduaciones
        current_row = self.graduaciones_table.currentRow()
        
        if current_row >= 0:
            # --- CASO A: EDITAR GRADUACIÃ“N (Cargar datos en formulario) ---
            try:
                # Obtener la graduaciÃ³n correspondiente
                # Nota: Asumimos que el orden en la tabla coincide con el historial.
                # Si se implementÃ³ ordenamiento inverso en la tabla, esto necesitarÃ­a ajuste.
                # En load_graduaciones se inserta en orden (row_index = index en lista), 
                # asÃ­ que currentRow deberÃ­a coincidir con el Ã­ndice del historial.
                historial = self.paciente_data.get('historial_graduaciones', [])
                
                if current_row < len(historial):
                    graduacion = historial[current_row]
                    self.abrir_graduacion_en_formulario(graduacion, current_row)
                else:
                    QMessageBox.warning(self, "Error", "No se pudo sincronizar la selecciÃ³n con el historial.")
            except Exception as e:
                print(f"Error al preparar ediciÃ³n de graduaciÃ³n: {e}")
                QMessageBox.critical(self, "Error", f"OcurriÃ³ un error al cargar los datos: {e}")

        else:
            # --- CASO B: EDITAR DATOS BÃSICOS (LÃ³gica original) ---
            dialog = EditPatientDialog(self.paciente_data, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self._refresh_original_patient_data()
                # Recargar la informaciÃ³n en el header
                self.actualizar_header()
                # Si el parent contextual es PatientsPage, recargar la lista.
                self._safe_load_parent_patients()

    def actualizar_header(self):
        """Actualiza los labels del header con los nuevos datos."""
        try:
            if hasattr(self, 'nombre_value'):
                self.nombre_value.setText(self.paciente_data.get('nombre', 'N/A'))
            if hasattr(self, 'dni_value'):
                self.dni_value.setText(self.paciente_data.get('dni', 'N/A'))
            if hasattr(self, 'fecha_value'):
                self.fecha_value.setText(self.paciente_data.get('fecha_nacimiento', 'N/A'))
            if hasattr(self, 'edad_value'):
                self.edad_value.setText(f"{self.paciente_data.get('edad', 'N/A')} aÃ±os")
            if hasattr(self, 'telefono_value'):
                self.telefono_value.setText(str(self.paciente_data.get('telefono', '') or 'N/A'))
            if hasattr(self, 'email_value'):
                self.email_value.setText(str(self.paciente_data.get('email', '') or 'N/A'))
            if hasattr(self, 'ultima_visita_value'):
                self.ultima_visita_value.setText(_resolve_patient_last_visit_label(self.paciente_data))
            if hasattr(self, 'monto_value'):
                latest_grad = _resolve_latest_graduacion(self.paciente_data)
                monto_cobrado = _graduacion_total_amount(latest_grad)
                self.monto_value.setText(f"S/. {monto_cobrado:.2f}")
        except Exception as e:
            print(f"Error actualizando header: {e}")

    def eliminar_paciente(self):
        """Elimina el paciente actual tras confirmaciÃ³n."""
        # Verificar permiso
        parent_app = self._safe_parent_app()
        if parent_app and hasattr(parent_app, 'is_helper') and parent_app.is_helper:
             if hasattr(parent_app, 'puede_hacer_accion') and not parent_app.puede_hacer_accion('pacientes', 'eliminar'):
                QMessageBox.warning(self, "Permiso Denegado", "No tienes permiso para eliminar pacientes.")
                return

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle('Confirmar eliminación')
        msg.setText(f'¿Está seguro de que desea eliminar al paciente {self.paciente_data.get("nombre")}?')
        msg.setInformativeText("Esta acción no se puede deshacer.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        # Estilo del diálogo
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 80px;
            }
            QMessageBox QPushButton[text="Yes"] {
                background-color: #D83B01;
                color: white;
                border: none;
            }
            QMessageBox QPushButton[text="Yes"]:hover {
                background-color: #C43601;
            }
            QMessageBox QPushButton[text="No"] {
                background-color: white;
                color: #333333;
                border: 1px solid #E0E0E0;
            }
            QMessageBox QPushButton[text="No"]:hover {
                background-color: #F0F0F0;
            }
        """)

        if msg.exec_() == QMessageBox.Yes:
            try:
                username = self._get_username()
                patients = cargar_pacientes(username)

                patient_index = self._find_patient_index(patients)
                if patient_index is None:
                    QMessageBox.warning(self, "Error", "No se encontrÃ³ el paciente original para eliminar.")
                    return

                from utils.trash_manager import move_to_trash

                move_to_trash(
                    username,
                    "pacientes",
                    patients[patient_index],
                    source="patient_dialog.delete",
                )

                del patients[patient_index]
                guardar_pacientes(username, patients)
                
                QMessageBox.information(self, "Ã‰xito", "Paciente eliminado correctamente")
                
                # Actualizar lista en parent si es posible
                self._safe_load_parent_patients()
                
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al eliminar paciente: {e}")

