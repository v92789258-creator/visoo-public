import sys
import os
import json
import datetime
import uuid
import logging
import copy
import re
import shutil
import calendar
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QBrush, QColor, QIcon, QMovie, QPixmap, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QHeaderView,
    QGroupBox, QGridLayout, QLineEdit, QComboBox, QAbstractItemView,
    QHBoxLayout, QMessageBox, QTabWidget, QDialog, QTableWidgetItem, QDateEdit,
    QFrame,
    QSpinBox, QScrollArea, QToolButton, QMenu, QFileDialog, QCheckBox, QStackedWidget
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QThread, QObject, QTimer
from PyQt5.QtSvg import QSvgRenderer

# Importaciones de clases de utilidades y diálogos.
from gui.dialogs.selection_dialogs import SeleccionarPacientesDialog, SeleccionarProductosDialog
from gui.dialogs.selection_products_v2 import SeleccionarProductosDialogV2
from gui.dialogs.sale_options_dialog import SaleOptionsDialog
from gui.main_window_pages.sales_page_parts import (
    AgregarStockDialog,
    DNISearchWorker,
    DebtLoadWorker,
    DeudaPaymentDialog,
    SalesTableWidget,
    _orphan_qthread,
)
from gui.main_window_pages.sales_page_parts.new_sale_tab import build_new_sale_tab
from gui.main_window_pages.sales_page_parts.sale_deletion import eliminar_venta as salespage_eliminar_venta
from gui.main_window_pages.sales_page_parts.sale_row_actions import (
    create_sale_row_actions_button as salespage_create_sale_row_actions_button,
    get_sale_row_from_button as salespage_get_sale_row_from_button,
    move_sale_row_from_button as salespage_move_sale_row_from_button,
    on_sales_table_cell_clicked as salespage_on_sales_table_cell_clicked,
    remove_sale_row_from_button as salespage_remove_sale_row_from_button,
    reset_sale_row_original_price as salespage_reset_sale_row_original_price,
    show_sale_options as salespage_show_sale_options,
    show_sale_row_stock as salespage_show_sale_row_stock,
)
from gui.salesHistorypage import build_sales_history_page, initialize_sales_history_state
from gui.salesHistorypage.compare_view import toggle_compare_mode as saleshistory_toggle_compare_mode
from gui.salesHistorypage.async_loader import on_sales_loaded as saleshistory_on_sales_loaded
from gui.salesHistorypage.async_loader import reload_sales_async as saleshistory_reload_sales_async
from gui.salesHistorypage.async_loader import stop_sales_loader as saleshistory_stop_sales_loader
from gui.salesHistorypage.filters import (
    apply_text_date_filter as saleshistory_apply_text_date_filter,
    filter_by_dates as saleshistory_filter_by_dates,
    mass_action_change_date as saleshistory_mass_action_change_date,
    on_payment_method_changed as saleshistory_on_payment_method_changed,
    on_sales_selection_changed as saleshistory_on_sales_selection_changed,
)
from gui.salesHistorypage.payment_filter import show_all_sales_history as saleshistory_show_all_sales_history
from gui.salesHistorypage.table_render import (
    cancel_sales_fill as saleshistory_cancel_sales_fill,
    fill_sales_chunk as saleshistory_fill_sales_chunk,
    on_sales_table_cell_clicked as saleshistory_on_sales_table_cell_clicked,
    render_sale_row_fast as saleshistory_render_sale_row_fast,
    sales_fill_in_progress as saleshistory_sales_fill_in_progress,
    update_sales_history_table as saleshistory_update_sales_history_table,
    update_sales_history_table_chunked as saleshistory_update_sales_history_table_chunked,
)
from utils.barcode_scanner import BarcodeLineEdit
from utils.file_handler import (
    cargar_ventas, cargar_ventas_dashboard, guardar_ventas, cargar_pacientes, guardar_pacientes, cargar_clientes,
    cargar_productos, guardar_productos, cargar_nombre_optica, cargar_ruc,
    cargar_metodos_pago, cargar_kardex, guardar_kardex, cargar_tamano_logo, guardar_tamano_logo, cargar_optometras,
    get_active_branch_context, get_effective_branch_context, get_branch_cache_data_dir, open_pdf_with_chrome,
    obtener_ruta_plantilla_ventas, obtener_ruta_recurso
)
from utils.file_handler import get_user_file_path
from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla
from utils.liquid_renderer import render_liquid_template

logger = logging.getLogger(__name__)

USE_MODERN_DAILY_SALES_PDF_LAYOUT = True


class SalesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        self.setObjectName("MainContent")
        self.last_sale = None
        self._prefilled_order_number = ""
        
        # Variables para el búsqueda de DNI
        self.dni_search_worker = None
        self.dni_search_thread = None
        self._deudas_load_thread = None
        self._deudas_load_worker = None
        
        # Inicialización diferida para evitar congelar UI al navegar a Ventas.
        self._deferred_initialized = False
        self._setup_shell_ui()
        try:
            QTimer.singleShot(0, self._deferred_init)
        except Exception:
            self._deferred_init()
        return

    def _setup_shell_ui(self):
        """UI mínima mientras se prepara el módulo de Ventas."""
        try:
            layout = self.layout()
            if layout is None:
                layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            shell = QWidget()
            shell_layout = QVBoxLayout(shell)
            shell_layout.setAlignment(Qt.AlignCenter)
            shell_layout.setContentsMargins(24, 24, 24, 24)

            title = QLabel("Cargando Ventas...")
            title.setStyleSheet("font-size: 18px; font-weight: 700; color: #172b4d;")
            subtitle = QLabel("Preparando interfaz en segundo plano. Un momento...")
            subtitle.setStyleSheet("font-size: 12px; color: #5e6c84;")
            subtitle.setWordWrap(True)
            subtitle.setAlignment(Qt.AlignCenter)

            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 0)
            bar.setMaximumWidth(320)

            shell_layout.addWidget(title, alignment=Qt.AlignCenter)
            shell_layout.addWidget(subtitle, alignment=Qt.AlignCenter)
            shell_layout.addWidget(bar, alignment=Qt.AlignCenter)

            self._shell_container = shell
            layout.addWidget(shell)
        except Exception:
            self._shell_container = None

    def _deferred_init(self):
        if getattr(self, "_deferred_initialized", False):
            return
        self._deferred_initialized = True

        # Remover placeholder si existe
        try:
            shell = getattr(self, "_shell_container", None)
            if shell is not None:
                layout = self.layout()
                if layout is not None:
                    layout.removeWidget(shell)
                shell.deleteLater()
            self._shell_container = None
        except Exception:
            pass

        self.setup_ui()

    def _cleanup_all_threads(self):
        self._stop_deudas_loader()
        try:
            thread = getattr(self, "dni_search_thread", None)
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait(300)
        except Exception:
            pass

    def _generar_id_venta_unico(self, ventas):
        """Genera ID de venta incremental único, sin depender del tamaño de la lista."""
        max_id = 364
        for venta in ventas:
            try:
                vid = int(venta.get('id', 0) or 0)
                if vid > max_id:
                    max_id = vid
            except (TypeError, ValueError, AttributeError):
                continue
        return max_id + 1

    def _normalizar_deuda_id(self, deuda_id):
        """Normaliza deuda_id para comparaciones robustas."""
        return str(deuda_id or '').strip()

    def _generar_deuda_id_unico(self, ids_existentes=None):
        """Genera un deuda_id único global."""
        usados = ids_existentes if isinstance(ids_existentes, set) else set()
        while True:
            candidato = f"DEU-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
            if candidato not in usados:
                usados.add(candidato)
                return candidato

    def _colectar_ids_deuda_existentes(self, ventas=None, pacientes=None):
        """Recolecta deuda_id ya existentes en ventas y graduaciones."""
        ids = set()

        for venta in (ventas or []):
            if not isinstance(venta, dict):
                continue
            deuda_id = self._normalizar_deuda_id(venta.get('deuda_id'))
            if deuda_id:
                ids.add(deuda_id)

        for paciente in (pacientes or []):
            if not isinstance(paciente, dict):
                continue
            for grad in (paciente.get('historial_graduaciones', []) or []):
                if not isinstance(grad, dict):
                    continue
                deuda_id = self._normalizar_deuda_id(grad.get('deuda_id'))
                if deuda_id:
                    ids.add(deuda_id)

        return ids

    def _to_float_safe(self, value, default=0.0):
        """Convierte a float de forma segura."""
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return float(default)

    def _parse_money_text(self, value, default=0.0):
        """
        Convierte montos mostrados en UI a float de forma robusta.
        Maneja símbolos de moneda, espacios y separadores de miles (comas).
        """
        try:
            if value is None:
                return float(default)
            
            # Limpiar símbolos comunes, espacios y normalizar
            text = str(value).strip().upper()
            text = text.replace("S/.", "").replace("S/", "").replace("$", "").replace(" ", "")
            
            if not text:
                return float(default)

            # Manejar separadores de miles (comas)
            if "," in text and "." in text:
                # Caso 1,200.50 -> eliminar coma de miles
                text = text.replace(",", "")
            elif "," in text:
                # Caso 12,50 (decimal) o 1,000 (miles)
                parts = text.split(",")
                if len(parts[-1]) <= 2:
                    text = text.replace(",", ".")
                else:
                    text = text.replace(",", "")
            
            return float(text)
        except (TypeError, ValueError):
            return float(default)

    def _parse_quantity_value(self, value, default=0):
        """Convierte cantidades a entero positivo."""
        try:
            qty = int(round(float(str(value or "").strip())))
            return qty if qty >= 0 else int(default)
        except (TypeError, ValueError):
            return int(default)

    def _graduacion_total_canonico(self, graduacion):
        """
        Calcula el total real de una graduacion sin duplicar el servicio.
        Historicos afectados pueden tener `monto_total_venta` inflado y
        `items_venta` ya incluyendo "Servicio de Graduacion".
        """
        if not isinstance(graduacion, dict):
            return 0.0, False

        stored_total = self._to_float_safe(graduacion.get('monto_total_venta', 0), 0.0)
        service_amount = self._to_float_safe(graduacion.get('monto_cobrado', 0), 0.0)
        items_total = 0.0
        service_items_total = 0.0
        product_items_total = 0.0
        items_include_service = False

        for item in graduacion.get('items_venta', []) or []:
            if not isinstance(item, dict):
                continue
            nombre_item = str(item.get('producto') or item.get('nombre') or '').strip().lower()
            if "servicio de gradu" in nombre_item or nombre_item == "graduacion":
                items_include_service = True
            cantidad = self._to_float_safe(item.get('cantidad', 1), 1.0)
            precio = self._to_float_safe(item.get('precio_unitario', item.get('precio', 0)), 0.0)
            item_total = self._to_float_safe(
                item.get('subtotal', item.get('total', precio * cantidad)),
                0.0
            )
            items_total += item_total
            if "servicio de gradu" in nombre_item or nombre_item == "graduacion":
                service_items_total += item_total
            else:
                product_items_total += item_total

        if items_total > 0.01:
            if items_include_service:
                # Historicos viejos guardaron el servicio como "total - productos".
                # Si no coincide con monto_cobrado, usar servicio real + productos.
                if service_amount > 0.01 and abs(service_items_total - service_amount) > 0.05:
                    canonical = service_amount + product_items_total
                else:
                    canonical = items_total
            elif service_amount > 0.01:
                canonical = service_amount + items_total
            else:
                canonical = items_total
        elif stored_total > 0.01:
            canonical = stored_total
        else:
            canonical = service_amount

        was_inflated = bool(
            stored_total > 0.01
            and canonical > 0.01
            and stored_total - canonical > 0.05
        )
        return canonical, was_inflated

    def _normalize_selected_sale_item(self, item):
        """Normaliza productos agregados a venta para evitar cantidades corruptas."""
        if not isinstance(item, dict):
            return None

        codigo = str(item.get('codigo', '') or '').strip()
        nombre = str(item.get('nombre', '') or '').strip()
        if not nombre:
            return None

        precio_unitario = self._parse_money_text(item.get('precio_unitario', 0), 0.0)
        cantidad = self._parse_quantity_value(item.get('cantidad', 1), 1)
        subtotal = self._parse_money_text(item.get('subtotal', 0), 0.0)
        stock_disponible = self._parse_quantity_value(item.get('stock_disponible', 0), 0)

        if precio_unitario > 0 and subtotal > 0:
            derived_qty_float = subtotal / precio_unitario
            derived_qty = int(round(derived_qty_float))
            if derived_qty >= 1 and abs(derived_qty_float - derived_qty) < 0.01:
                raw_expected = precio_unitario * max(1, cantidad)
                if abs(subtotal - raw_expected) > 0.01:
                    cantidad = derived_qty

        if cantidad <= 0:
            cantidad = 1

        if stock_disponible > 0 and cantidad > stock_disponible:
            cantidad = stock_disponible

        subtotal_normalizado = subtotal
        if precio_unitario > 0 and cantidad > 0:
            subtotal_normalizado = round(precio_unitario * cantidad, 2)
        elif subtotal_normalizado <= 0:
            subtotal_normalizado = 0.0

        return {
            'codigo': codigo,
            'nombre': nombre,
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'subtotal': subtotal_normalizado,
            'stock_disponible': stock_disponible,
        }

    def _resumen_pago_graduacion(self, graduacion):
        """
        Retorna (monto_total, monto_pagado, monto_faltante) para una graduacion.
        - Prioriza `pagos_parciales` cuando existe.
        - Usa `monto_adelanto` como compatibilidad si no hay pagos.
        - Si no es pago en partes y no hay datos de pago, asume pagado total.
        """
        if not isinstance(graduacion, dict):
            return 0.0, 0.0, 0.0

        monto_total, _inflated = self._graduacion_total_canonico(graduacion)
        pagos = graduacion.get('pagos_parciales', [])
        monto_pagado = 0.0

        if isinstance(pagos, list) and len(pagos) > 0:
            for pago in pagos:
                if isinstance(pago, dict):
                    monto_pagado += self._to_float_safe(pago.get('monto', 0))
        else:
            adelanto_raw = graduacion.get('monto_adelanto', None)
            if adelanto_raw not in (None, ''):
                monto_pagado = self._to_float_safe(adelanto_raw, 0.0)
            else:
                es_pago_parcial = bool(graduacion.get('es_pago_parcial', False))
                estado = str(graduacion.get('estado', '') or '').strip().lower()
                if (not es_pago_parcial and monto_total > 0) or estado == 'completada':
                    monto_pagado = monto_total

        if monto_pagado < 0:
            monto_pagado = 0.0

        monto_faltante = max(0.0, monto_total - monto_pagado)
        return monto_total, monto_pagado, monto_faltante

    def setup_ui(self):
        page = self
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
        else:
            try:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            except Exception:
                pass
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Crear TabWidget para las dos secciones
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                border: none; 
                background: #FFFFFF; 
            }
            QTabBar::tab {
                background: #F5F5F5;
                border: none;
                padding: 16px 28px;
                color: #666666;
                font-weight: 700;
                font-size: 14px;
                margin-right: 2px;
                min-width: 150px;
                min-height: 40px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #1a1a1a;
                border-bottom: 3px solid #1a1a1a;
                font-weight: 700;
            }
            QTabBar::tab:hover:!selected {
                background: #EFEFEF;
                color: #555555;
            }
        """)
        
        def _placeholder(text: str):
            w = QWidget()
            l = QVBoxLayout(w)
            l.setAlignment(Qt.AlignCenter)
            l.setContentsMargins(24, 24, 24, 24)
            lbl = QLabel(str(text or "Cargando..."))
            lbl.setStyleSheet("color:#5e6c84; font-size: 12px;")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            l.addWidget(lbl)
            return w

        # Lazy tabs: construir solo cuando se abre el tab (evita congelar UI)
        lazy_builders = {}
        tab_titles = []

        tab_titles.append("Nueva Venta")
        lazy_builders[len(tab_titles) - 1] = ("Nueva Venta", self.create_sales_tab)

        tab_titles.append("Venta Manual")
        lazy_builders[len(tab_titles) - 1] = ("Venta Manual", self.create_manual_sales_tab)

        if self._puede_ver_deudas():
            tab_titles.append("Revisión de Deudas")
            lazy_builders[len(tab_titles) - 1] = ("Revisión de Deudas", self.create_deudas_tab)

        puede_ver_historial = True
        try:
            if self.parent_app and self.parent_app.is_helper:
                from utils.helpers_manager import puede_ver_seccion
                puede_ver_historial = puede_ver_seccion(
                    self.parent_app.helper_name,
                    self.parent_app.username,
                    'ventas'
                )
        except Exception:
            puede_ver_historial = True

        if puede_ver_historial:
            tab_titles.append("Historial de Ventas")
            lazy_builders[len(tab_titles) - 1] = ("Historial de Ventas", lambda: SalesHistoryPage(self.parent_app))

        tab_titles.append("Caja")
        lazy_builders[len(tab_titles) - 1] = ("Caja", lambda: self.create_caja_tab())

        tab_titles.append("Guia de Remision")
        lazy_builders[len(tab_titles) - 1] = ("Guia de Remision", self.create_guia_remision_tab)

        self._lazy_sales_tab_builders = lazy_builders
        self._lazy_sales_tabs_built = set()

        for title in tab_titles:
            self.tab_widget.addTab(_placeholder(f"Cargando {title}..."), title)

        try:
            self.tab_widget.currentChanged.connect(self._ensure_lazy_sales_tab_built)
        except Exception:
            pass

        try:
            QTimer.singleShot(0, lambda: self._ensure_lazy_sales_tab_built(self.tab_widget.currentIndex()))
        except Exception:
            self._ensure_lazy_sales_tab_built(self.tab_widget.currentIndex())

        layout.addWidget(self.tab_widget)

    def _ensure_lazy_sales_tab_built(self, index: int):
        """Construye el contenido real del tab cuando el usuario lo abre por primera vez."""
        try:
            idx = int(index)
        except Exception:
            return

        built = getattr(self, "_lazy_sales_tabs_built", set()) or set()
        if idx in built:
            return

        building = getattr(self, "_lazy_sales_tabs_building", set()) or set()
        if idx in building:
            return

        builders = getattr(self, "_lazy_sales_tab_builders", {}) or {}
        if idx not in builders:
            return

        title, builder = builders.get(idx)
        building.add(idx)
        self._lazy_sales_tabs_building = building
        try:
            real_widget = builder() if callable(builder) else None
        except Exception:
            logger.exception("[VENTAS] Error construyendo tab idx=%s title=%s", idx, title)
            real_widget = None

        if real_widget is None:
            try:
                building.discard(idx)
                self._lazy_sales_tabs_building = building
            except Exception:
                pass
            return

        try:
            # Reemplazar placeholder sin disparar currentChanged recursivamente
            blocker = QtCore.QSignalBlocker(self.tab_widget)
            try:
                placeholder = self.tab_widget.widget(idx)
                current_idx = int(self.tab_widget.currentIndex() or 0)
                self.tab_widget.removeTab(idx)
                self.tab_widget.insertTab(idx, real_widget, str(title))

                # Restaurar tab actual (por si remove/insert movió el índice)
                if current_idx >= 0 and current_idx < self.tab_widget.count():
                    self.tab_widget.setCurrentIndex(current_idx if current_idx != idx else idx)
                else:
                    self.tab_widget.setCurrentIndex(min(idx, max(0, self.tab_widget.count() - 1)))

                if placeholder is not None:
                    placeholder.deleteLater()

                # Marcar como construido solo si el reemplazo fue exitoso.
                built.add(idx)
                self._lazy_sales_tabs_built = built
            finally:
                del blocker

            if str(title).lower().startswith("historial") and isinstance(real_widget, SalesHistoryPage):
                self.sales_history = real_widget
        except Exception:
            logger.exception("[VENTAS] Error reemplazando placeholder tab idx=%s title=%s", idx, title)
        finally:
            try:
                building.discard(idx)
                self._lazy_sales_tabs_building = building
            except Exception:
                pass

    def create_sales_tab(self):
        return build_new_sale_tab(self)

    def abrir_seleccion_paciente(self):
        dialog = SeleccionarPacientesDialog(self, username=self.username)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_dni = dialog.selected_dni
            selected_nombre = dialog.selected_nombre if hasattr(dialog, 'selected_nombre') else ""
            if selected_dni:
                self.entry_venta_paciente.setText(selected_dni)
                self.label_venta_nombre.setText(selected_nombre if selected_nombre else "")

    def on_pago_partes_toggled(self, checked):
        """Muestra/oculta el campo de adelanto cuando se toglea pago en partes."""
        if hasattr(self, 'entry_adelanto'):
            self.entry_adelanto.setHidden(not checked)
        if hasattr(self, 'label_adelanto'):
            self.label_adelanto.setHidden(not checked)
        if not checked and hasattr(self, 'entry_adelanto'):
            self.entry_adelanto.setValue(0.0)
        self._update_multi_metodo_pago_sale_state()

    def _get_sale_commission_beneficiary(self):
        if hasattr(self, 'vendedor_combo'):
            vendedor = str(self.vendedor_combo.currentText() or "").strip()
            if vendedor and vendedor != "Sin vendedores":
                return vendedor
        if self.parent_app and getattr(self.parent_app, 'is_helper', False) and getattr(self.parent_app, 'helper_name', None):
            return str(self.parent_app.helper_name).strip()
        return str(self.username or "").strip()

    def _get_selected_sale_vendedor(self):
        if hasattr(self, 'vendedor_combo'):
            vendedor = str(self.vendedor_combo.currentText() or "").strip()
            if vendedor and vendedor != "Sin vendedores":
                return vendedor
        if self.parent_app and getattr(self.parent_app, 'is_helper', False) and getattr(self.parent_app, 'helper_name', None):
            return str(self.parent_app.helper_name).strip()
        return str(self.username or "").strip()

    def _set_register_sale_busy(self, busy, base_text="Registrando venta"):
        button = getattr(self, "btn_registrar_venta", None)
        if button is None:
            return

        if busy:
            try:
                button.setEnabled(False)
                button.setProperty("_busy_base_text", base_text)
                button.setText(f"{base_text}.")
            except Exception:
                pass

            timer = getattr(self, "_register_sale_busy_timer", None)
            if timer is None:
                timer = QTimer(self)
                timer.setInterval(220)

                def _tick():
                    try:
                        dots = int(getattr(self, "_register_sale_busy_dots", 0) or 0)
                        dots = (dots % 3) + 1
                        self._register_sale_busy_dots = dots
                        base = str(button.property("_busy_base_text") or base_text)
                        button.setText(f"{base}{'.' * dots}")
                    except Exception:
                        pass

                timer.timeout.connect(_tick)
                self._register_sale_busy_timer = timer

            self._register_sale_busy_dots = 1
            try:
                self._register_sale_busy_timer.start()
            except Exception:
                pass
            try:
                QApplication.processEvents()
            except Exception:
                pass
            return

        timer = getattr(self, "_register_sale_busy_timer", None)
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
        try:
            button.setEnabled(True)
            button.setText("Registrar Venta")
            button.setProperty("_busy_base_text", None)
        except Exception:
            pass
        try:
            QApplication.processEvents()
        except Exception:
            pass

    def _set_clear_sale_busy(self, busy, base_text="Limpiando"):
        button = getattr(self, "btn_limpiar_venta", None)
        if button is None:
            return

        if busy:
            try:
                button.setEnabled(False)
                button.setProperty("_busy_base_text", base_text)
                button.setText(f"{base_text}.")
            except Exception:
                pass

            timer = getattr(self, "_clear_sale_busy_timer", None)
            if timer is None:
                timer = QTimer(self)
                timer.setInterval(180)

                def _tick():
                    try:
                        dots = int(getattr(self, "_clear_sale_busy_dots", 0) or 0)
                        dots = (dots % 3) + 1
                        self._clear_sale_busy_dots = dots
                        base = str(button.property("_busy_base_text") or base_text)
                        button.setText(f"{base}{'.' * dots}")
                    except Exception:
                        pass

                timer.timeout.connect(_tick)
                self._clear_sale_busy_timer = timer

            self._clear_sale_busy_dots = 1
            try:
                self._clear_sale_busy_timer.start()
            except Exception:
                pass
            return

        timer = getattr(self, "_clear_sale_busy_timer", None)
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
        try:
            button.setEnabled(True)
            button.setText("Limpiar")
            button.setProperty("_busy_base_text", None)
        except Exception:
            pass

    def _extract_order_sequence(self, value):
        text = str(value or "").strip()
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0

    def _format_order_number(self, value):
        sequence = self._extract_order_sequence(value)
        if sequence <= 0:
            return "0001"
        digits = str(sequence)
        return digits.zfill(4) if len(digits) < 4 else digits

    def _compute_next_order_sequence(self, ventas=None):
        if ventas is None:
            try:
                ventas = cargar_ventas(self.username) or []
            except Exception:
                ventas = []
        max_order = 0
        for venta in ventas if isinstance(ventas, list) else []:
            if not isinstance(venta, dict):
                continue
            max_order = max(max_order, self._extract_order_sequence(venta.get("numero_orden", "")))
        return max_order + 1 if max_order > 0 else 1

    def _resolve_order_number_for_sale(self, ventas=None):
        existing = str(getattr(self, "_prefilled_order_number", "") or "").strip()
        if existing:
            return self._format_order_number(existing)
        return self._format_order_number(self._compute_next_order_sequence(ventas=ventas))

    def _refresh_order_number_preview(self, ventas=None):
        if not hasattr(self, "label_numero_orden_venta"):
            return
        numero = self._resolve_order_number_for_sale(ventas=ventas)
        self.label_numero_orden_venta.setText(f"N° Orden: {numero}")

    def _editar_order_number(self):
        current_value = self._resolve_order_number_for_sale()
        value, accepted = QtWidgets.QInputDialog.getText(
            self,
            "N° de Orden",
            "Editar número de orden:",
            text=str(current_value),
        )
        if not accepted:
            return
        digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
        if not digits:
            return
        self._prefilled_order_number = digits
        self._refresh_order_number_preview()

    def _update_sale_commission_summary(self):
        if not hasattr(self, 'label_comision_venta_summary'):
            return
        if not getattr(self, 'checkbox_comision_venta', None) or not self.checkbox_comision_venta.isChecked():
            self.label_comision_venta_summary.setText("")
            self.label_comision_venta_summary.setHidden(True)
            return
        monto = float(self.entry_comision_venta.value()) if hasattr(self, 'entry_comision_venta') else 0.0
        beneficiario = self._get_sale_commission_beneficiary() or "Sin asignar"
        self.label_comision_venta_summary.setText(f"Comisión fija: S/. {monto:.2f} para {beneficiario}")
        self.label_comision_venta_summary.setHidden(False)

    def on_comision_venta_toggled(self, checked):
        if hasattr(self, 'entry_comision_venta'):
            self.entry_comision_venta.setHidden(not checked)
        if hasattr(self, 'label_comision_venta'):
            self.label_comision_venta.setHidden(not checked)
        if not checked and hasattr(self, 'entry_comision_venta'):
            self.entry_comision_venta.setValue(0.0)
        self._update_sale_commission_summary()

    def on_barcode_scanned(self, barcode):
        """Maneja el código de barras escaneado."""
        # Implementar búsqueda de producto por código
        try:
            productos = cargar_productos(self.username)
            for prod in productos:
                if prod.get('codigo_barras', '') == barcode or prod.get('codigo', '') == barcode:
                    # Agregar este producto a la tabla (cantidad 1)
                    try:
                        cantidad = 1
                        precio_unitario = float(prod.get('venta', 0))
                    except (ValueError, TypeError):
                        precio_unitario = 0.0
                    
                    subtotal = cantidad * precio_unitario
                    
                    self.add_products_to_sale_table([{
                        'codigo': prod.get('codigo'),
                        'nombre': prod.get('nombre'),
                        'cantidad': cantidad,
                        'precio_unitario': precio_unitario,
                        'subtotal': subtotal
                    }], append=True)
                    
                    # Limpiar el input
                    if hasattr(self, 'barcode_input'):
                        self.barcode_input.clear()
                    break
        except Exception:
            pass

    def abrir_seleccion_productos(self):
        try:
            # Usar el nuevo dialog V2 que es más robusto
            dialog = SeleccionarProductosDialogV2(self, username=self.username)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                if dialog.selected_products:
                    self.add_products_to_sale_table(dialog.selected_products)
                else:
                    QtWidgets.QMessageBox.warning(self, "Sin Productos", 
                        "No se seleccionaron productos.")
        except Exception as e:
            import traceback
            print(f"Error al abrir diálogo de productos: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"Error al seleccionar productos: {str(e)}")

    def add_products_to_sale_table(self, selected_products, append=False):
        # Bloquear todas las señales durante la carga para evitar recursión
        self.venta_table.blockSignals(True)
        
        try:
            if not append:
                self.venta_table.setRowCount(0)
            
            if not selected_products:
                print("WARNING: No hay productos seleccionados")
                self.venta_table.blockSignals(False)
                return
            
            for raw_item in selected_products:
                try:
                    item = self._normalize_selected_sale_item(raw_item)
                    if not item:
                        print(f"WARNING: Item inválido al agregar a venta: {raw_item}")
                        continue

                    row_count = self.venta_table.rowCount()
                    self.venta_table.insertRow(row_count)
                    
                    # Producto (no editable)
                    codigo = str(item.get('codigo', '') or '').strip()
                    nombre = str(item.get('nombre', 'N/A') or 'N/A').strip()
                    producto_display = f"{codigo} - {nombre}" if codigo else nombre
                    producto_item = QTableWidgetItem(producto_display)
                    producto_item.setFlags(producto_item.flags() & ~QtCore.Qt.ItemIsEditable)
                    producto_item.setData(QtCore.Qt.UserRole, self._parse_quantity_value(item.get('stock_disponible', 0), 0))
                    producto_item.setData(QtCore.Qt.UserRole + 1, codigo)
                    self.venta_table.setItem(row_count, 0, producto_item)
                    
                    # Cantidad (editable)
                    cantidad = self._parse_quantity_value(item.get('cantidad', 1), 1)
                    cantidad_item = QTableWidgetItem(str(cantidad))
                    cantidad_item.setFlags(cantidad_item.flags() | QtCore.Qt.ItemIsEditable)
                    self.venta_table.setItem(row_count, 1, cantidad_item)
                    
                    # Precio Unitario
                    try:
                        precio_unitario = float(item.get('precio_unitario', 0))
                    except (ValueError, TypeError, KeyError):
                        precio_unitario = 0.0
                    
                    precio_item = QTableWidgetItem(f"{precio_unitario:.2f}")
                    precio_item.setFlags(precio_item.flags() | QtCore.Qt.ItemIsEditable)
                    precio_item.setData(QtCore.Qt.UserRole, precio_unitario)
                    self.venta_table.setItem(row_count, 2, precio_item)
                    
                    # Subtotal
                    subtotal = self._parse_money_text(item.get('subtotal', 0), 0.0)
                    if subtotal <= 0:
                        subtotal = cantidad * precio_unitario

                    subtotal_item = QTableWidgetItem(f"{subtotal:.2f}")
                    subtotal_item.setFlags(subtotal_item.flags() | QtCore.Qt.ItemIsEditable)
                    subtotal_item.setData(QtCore.Qt.UserRole, subtotal)
                    self.venta_table.setItem(row_count, 3, subtotal_item)
                    
                    # Descuento %
                    descuento_percent = 0.0
                    descuento_item = QTableWidgetItem(f"{descuento_percent:.1f}%")
                    descuento_item.setFlags(descuento_item.flags() & ~QtCore.Qt.ItemIsEditable)
                    # Guardar precio original para cálculos
                    descuento_item.setData(QtCore.Qt.UserRole, precio_unitario)
                    self.venta_table.setItem(row_count, 4, descuento_item)

                    # Acciones
                    self.venta_table.setCellWidget(row_count, 5, self._create_sale_row_actions_button(row_count))
                except Exception as e:
                    print(f"Error al agregar producto a tabla: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        except Exception as e:
            print(f"Error general en add_products_to_sale_table: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Desbloquear todas las señales
            self.venta_table.blockSignals(False)
            # Actualizar totales una sola vez
            self.actualizar_total_venta()

    def update_sales_page(self):
        # When showing sales page, reset form and totals
        try:
            self.entry_venta_paciente.setText("00000000")
            self.venta_table.setRowCount(0)
            self.actualizar_total_venta()
            self.btn_generar_boleta.setHidden(True)
            if hasattr(self, 'checkbox_pago_partes'):
                self.checkbox_pago_partes.setChecked(False)
            if hasattr(self, 'entry_adelanto'):
                self.entry_adelanto.setValue(0.0)
            if hasattr(self, 'checkbox_multi_metodo_pago'):
                self.checkbox_multi_metodo_pago.setChecked(False)
            if hasattr(self, 'entry_metodo_pago_monto_1'):
                self.entry_metodo_pago_monto_1.setValue(0.0)
            if hasattr(self, 'entry_metodo_pago_monto_2'):
                self.entry_metodo_pago_monto_2.setValue(0.0)
            self.update_metodo_pago_combo()
            self.update_vendedor_combo()
            self._prefilled_order_number = ""
            self._refresh_order_number_preview()
            self._update_multi_metodo_pago_sale_state()
        except Exception:
            pass

    def update_metodo_pago_combo(self):
        metodos = cargar_metodos_pago(self.username)
        self._populate_sale_payment_combo(self.metodo_pago_combo, metodos)
        if hasattr(self, 'metodo_pago_combo_2'):
            self._populate_sale_payment_combo(self.metodo_pago_combo_2, metodos)
        if hasattr(self, 'metodo_pago_combo_3'):
            self._populate_sale_payment_combo(self.metodo_pago_combo_3, metodos)
        # actualizar el completer para reflejar la lista actual
        try:
            if self.metodo_pago_combo.completer() is None:
                completer = QtWidgets.QCompleter(self.metodo_pago_combo.model(), self.metodo_pago_combo)
            else:
                completer = self.metodo_pago_combo.completer()
            completer.setModel(self.metodo_pago_combo.model())
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            self.metodo_pago_combo.setCompleter(completer)
        except Exception:
            pass

    def _populate_sale_payment_combo(self, combo, metodos=None):
        if combo is None:
            return
        combo.clear()
        if metodos is None:
            metodos = cargar_metodos_pago(self.username)
        if not metodos:
            combo.addItem("Sin métodos de pago")
            combo.setCurrentIndex(0)
            combo.setDisabled(True)
        else:
            combo.addItems(metodos)
            combo.setDisabled(False)

    def _toggle_multi_metodo_pago_sale(self, checked):
        _ = checked
        visible = bool(hasattr(self, 'checkbox_multi_metodo_pago') and self.checkbox_multi_metodo_pago.isChecked())
        if visible:
            self.update_metodo_pago_combo()
        if hasattr(self, 'multi_metodo_pago_sale_container'):
            self.multi_metodo_pago_sale_container.setVisible(visible)
        if hasattr(self, 'metodo_pago_combo'):
            self.metodo_pago_combo.setEnabled(not visible)
        self._refresh_sale_scroll_layout()
        self._update_multi_metodo_pago_sale_state()

    def _refresh_sale_scroll_layout(self):
        try:
            if hasattr(self, 'multi_metodo_pago_sale_container'):
                self.multi_metodo_pago_sale_container.updateGeometry()
                self.multi_metodo_pago_sale_container.adjustSize()
            if hasattr(self, 'sales_new_content_widget'):
                self.sales_new_content_widget.updateGeometry()
                self.sales_new_content_widget.adjustSize()
            if hasattr(self, 'sales_new_scroll_area'):
                self.sales_new_scroll_area.widget().adjustSize() if self.sales_new_scroll_area.widget() else None
                self.sales_new_scroll_area.viewport().update()
        except Exception:
            pass

    def _update_multi_metodo_pago_sale_state(self):
        if not hasattr(self, 'label_multi_metodo_pago_sale_info'):
            return
        target = 0.0
        if hasattr(self, 'checkbox_pago_partes') and self.checkbox_pago_partes.isChecked():
            target = float(self.entry_adelanto.value()) if hasattr(self, 'entry_adelanto') else 0.0
            self.label_multi_metodo_pago_sale_info.setText(
                f"Distribuye el adelanto actual: S/. {target:.2f}"
            )
        else:
            raw_total = str(getattr(self, 'total_venta_label', QLabel()).text() if hasattr(self, 'total_venta_label') else '0')
            target = self._parse_money_text(raw_total, 0.0)
            self.label_multi_metodo_pago_sale_info.setText(
                f"Distribuye el total actual: S/. {target:.2f}"
            )
        self._sync_multi_metodo_pago_sale_limits()

    def _sync_multi_metodo_pago_sale_limits(self):
        if not hasattr(self, 'entry_metodo_pago_monto_1') or not hasattr(self, 'entry_metodo_pago_monto_2'):
            return

        if hasattr(self, 'checkbox_pago_partes') and self.checkbox_pago_partes.isChecked():
            limite_total = float(self.entry_adelanto.value()) if hasattr(self, 'entry_adelanto') else 0.0
        else:
            raw_total = str(getattr(self, 'total_venta_label', QLabel()).text() if hasattr(self, 'total_venta_label') else '0')
            limite_total = self._parse_money_text(raw_total, 0.0)

        limite_total = max(0.0, round(limite_total, 2))
        self.entry_metodo_pago_monto_1.blockSignals(True)
        self.entry_metodo_pago_monto_2.blockSignals(True)
        try:
            valor_1 = min(float(self.entry_metodo_pago_monto_1.value() or 0.0), limite_total)
            valor_2 = min(float(self.entry_metodo_pago_monto_2.value() or 0.0), limite_total)

            max_para_1 = max(0.0, round(limite_total - valor_2, 2))
            if valor_1 > max_para_1:
                valor_1 = max_para_1

            max_para_2 = max(0.0, round(limite_total - valor_1, 2))
            if valor_2 > max_para_2:
                valor_2 = max_para_2

            self.entry_metodo_pago_monto_1.setMaximum(max(0.0, round(limite_total - valor_2, 2)))
            self.entry_metodo_pago_monto_2.setMaximum(max(0.0, round(limite_total - valor_1, 2)))
            self.entry_metodo_pago_monto_1.setValue(round(valor_1, 2))
            self.entry_metodo_pago_monto_2.setValue(round(valor_2, 2))
        finally:
            self.entry_metodo_pago_monto_1.blockSignals(False)
            self.entry_metodo_pago_monto_2.blockSignals(False)

    def _sync_sale_adelanto_limit(self):
        if not hasattr(self, 'entry_adelanto'):
            return
        raw_total = str(getattr(self, 'total_venta_label', QLabel()).text() if hasattr(self, 'total_venta_label') else '0')
        total_actual = max(0.0, round(self._parse_money_text(raw_total, 0.0), 2))
        self.entry_adelanto.blockSignals(True)
        try:
            self.entry_adelanto.setMaximum(total_actual)
            valor = min(float(self.entry_adelanto.value() or 0.0), total_actual)
            self.entry_adelanto.setValue(round(valor, 2))
        finally:
            self.entry_adelanto.blockSignals(False)

    def _format_sale_payment_summary(self, details):
        labels = []
        for item in details if isinstance(details, list) else []:
            if not isinstance(item, dict):
                continue
            metodo = str(item.get('metodo', '') or '').strip()
            monto = float(item.get('monto', 0) or 0)
            if metodo and monto > 0:
                labels.append(f"{metodo}: S/. {monto:.2f}")
        if not labels:
            return ""
        if len(labels) == 1:
            return labels[0].split(': ', 1)[0]
        return "Mixto - " + " | ".join(labels)

    def _build_sale_payment_details(self, target_amount):
        target = float(target_amount or 0.0)
        if target <= 0:
            return "", []

        metodo_1 = str(self.metodo_pago_combo.currentText() or "").strip()
        if metodo_1 == "Sin métodos de pago":
            metodo_1 = ""

        mixed = bool(hasattr(self, 'checkbox_multi_metodo_pago') and self.checkbox_multi_metodo_pago.isChecked())
        if not mixed:
            if not metodo_1:
                raise ValueError("Debe seleccionar un método de pago.")
            return metodo_1, [{"metodo": metodo_1, "monto": round(target, 2)}]

        metodo_2 = str(self.metodo_pago_combo_2.currentText() or "").strip() if hasattr(self, 'metodo_pago_combo_2') else ""
        metodo_3 = str(self.metodo_pago_combo_3.currentText() or "").strip() if hasattr(self, 'metodo_pago_combo_3') else ""
        if metodo_2 == "Sin métodos de pago":
            metodo_2 = ""
        if metodo_3 == "Sin métodos de pago":
            metodo_3 = ""
        monto_1 = float(self.entry_metodo_pago_monto_1.value()) if hasattr(self, 'entry_metodo_pago_monto_1') else 0.0
        monto_2 = float(self.entry_metodo_pago_monto_2.value()) if hasattr(self, 'entry_metodo_pago_monto_2') else 0.0

        if not metodo_2 or not metodo_3:
            raise ValueError("Selecciona los dos métodos para el pago mixto.")
        if metodo_2 == metodo_3:
            raise ValueError("Los métodos del pago mixto deben ser distintos.")
        if monto_1 <= 0 or monto_2 <= 0:
            raise ValueError("Los montos del pago mixto deben ser mayores a 0.")

        total_entered = round(monto_1 + monto_2, 2)
        if abs(total_entered - round(target, 2)) > 0.05:
            raise ValueError(f"El pago mixto debe sumar S/. {target:.2f}.")

        details = [
            {"metodo": metodo_2, "monto": round(monto_1, 2)},
            {"metodo": metodo_3, "monto": round(monto_2, 2)},
        ]
        return self._format_sale_payment_summary(details), details

    def update_vendedor_combo(self):
        if not hasattr(self, 'vendedor_combo'):
            return

        current_value = str(self.vendedor_combo.currentText() or "").strip()
        self.vendedor_combo.clear()
        vendedores = [str(v or "").strip() for v in (cargar_optometras(self.username) or []) if str(v or "").strip()]

        if not vendedores:
            fallback = ""
            if self.parent_app and getattr(self.parent_app, 'is_helper', False) and getattr(self.parent_app, 'helper_name', None):
                fallback = str(self.parent_app.helper_name).strip()
            if not fallback:
                fallback = str(self.username or "").strip()
            vendedores = [fallback] if fallback else []

        if not vendedores:
            self.vendedor_combo.addItem("Sin vendedores")
            self.vendedor_combo.setCurrentIndex(0)
            self.vendedor_combo.setDisabled(True)
        else:
            self.vendedor_combo.addItems(vendedores)
            self.vendedor_combo.setDisabled(False)
            target_value = current_value if current_value else vendedores[0]
            index = self.vendedor_combo.findText(target_value)
            self.vendedor_combo.setCurrentIndex(index if index >= 0 else 0)

        try:
            if self.vendedor_combo.completer() is None:
                completer = QtWidgets.QCompleter(self.vendedor_combo.model(), self.vendedor_combo)
            else:
                completer = self.vendedor_combo.completer()
            completer.setModel(self.vendedor_combo.model())
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            self.vendedor_combo.setCompleter(completer)
        except Exception:
            pass

    def _create_sale_row_actions_button(self, row_index):
        return salespage_create_sale_row_actions_button(self, row_index)

    def _get_sale_row_from_button(self, button):
        return salespage_get_sale_row_from_button(self, button)

    def _remove_sale_row_from_button(self, button):
        return salespage_remove_sale_row_from_button(self, button)

    def _show_sale_row_stock(self, button):
        return salespage_show_sale_row_stock(self, button)

    def _reset_sale_row_original_price(self, button):
        return salespage_reset_sale_row_original_price(self, button)

    def _move_sale_row_from_button(self, button, direction):
        return salespage_move_sale_row_from_button(self, button, direction)

    def on_venta_table_item_changed(self, item):
        """Valida cambios en la tabla de ventas y actualiza descuentos y totales"""
        if item is None:
            return
            
        row = item.row()
        col = item.column()
        
        # No permitir edición en la columna de Producto (columna 0)
        if col == 0:
            return
        
        # Bloquear señales para evitar recursión
        self.venta_table.blockSignals(True)
        
        try:
            # Validar números en columnas editables (1=Cantidad, 2=Precio, 3=Subtotal)
            try:
                value = self._parse_money_text(item.text(), 0.0)
                
                # Asegurar valores positivos
                if value < 0:
                    value = 0

                if col == 1:
                    cantidad = max(1, self._parse_quantity_value(value, 1))
                    item.setText(str(cantidad))

                    precio_item = self.venta_table.item(row, 2)
                    subtotal_item = self.venta_table.item(row, 3)
                    descuento_item = self.venta_table.item(row, 4)

                    precio_original = self._parse_money_text(
                        descuento_item.data(QtCore.Qt.UserRole) if descuento_item else 0,
                        self._parse_money_text(precio_item.text(), 0.0) if precio_item else 0.0
                    )
                    descuento_text = descuento_item.text() if descuento_item else "0%"
                    try:
                        descuento_percent = float(str(descuento_text).replace('%', '').strip() or 0)
                    except (TypeError, ValueError):
                        descuento_percent = 0.0

                    precio_efectivo = precio_original * max(0.0, 1.0 - (descuento_percent / 100.0))
                    if precio_efectivo <= 0 and precio_item:
                        precio_efectivo = self._parse_money_text(precio_item.text(), 0.0)

                    if subtotal_item:
                        subtotal_item.setText(f"{(precio_efectivo * cantidad):.2f}")
                else:
                    # Mostrar sin formato (sin "S/")
                    item.setText(f"{value:.2f}")
                
                # Recalcular descuento cuando se cambia el precio unitario (columna 2)
                if col == 2:
                    descuento_item = self.venta_table.item(row, 4)
                    if descuento_item:
                        # Obtener precio original guardado
                        precio_original = descuento_item.data(QtCore.Qt.UserRole)
                        if precio_original is None or precio_original == 0:
                            precio_original = value
                        
                        # Calcular porcentaje de descuento
                        if precio_original > 0:
                            descuento_percent = ((precio_original - value) / precio_original) * 100
                        else:
                            descuento_percent = 0.0
                        
                        # Asegurar que no sea negativo
                        if descuento_percent < 0:
                            descuento_percent = 0.0
                        
                        # Actualizar la columna de descuento
                        descuento_item.setText(f"{descuento_percent:.1f}%")
                
                # Recalcular descuento cuando se cambia el subtotal (columna 3)
                elif col == 3:
                    # Obtener cantidad y precio unitario
                    cant_item = self.venta_table.item(row, 1)
                    precio_item = self.venta_table.item(row, 2)
                    descuento_item = self.venta_table.item(row, 4)
                    
                    if cant_item and precio_item and descuento_item:
                        try:
                            cantidad = max(1, self._parse_quantity_value(cant_item.text(), 1))
                            precio_actual = self._parse_money_text(precio_item.text(), 0.0)
                            subtotal_nuevo = value
                            
                            # Calcular el precio unitario implícito del nuevo subtotal
                            if cantidad > 0:
                                precio_implicito = subtotal_nuevo / cantidad
                            else:
                                precio_implicito = precio_actual
                            
                            # Obtener precio original
                            precio_original = descuento_item.data(QtCore.Qt.UserRole)
                            if precio_original is None or precio_original == 0:
                                precio_original = precio_actual
                            
                            # Calcular descuento basado en el precio implicito
                            if precio_original > 0:
                                descuento_percent = ((precio_original - precio_implicito) / precio_original) * 100
                            else:
                                descuento_percent = 0.0
                            
                            # Asegurar que no sea negativo
                            if descuento_percent < 0:
                                descuento_percent = 0.0
                            
                            # Actualizar la columna de descuento
                            descuento_item.setText(f"{descuento_percent:.1f}%")
                        except (ValueError, TypeError):
                            pass
                
            except ValueError:
                # Si no es número válido, revertir al valor anterior
                item.setText("0.00")
        finally:
            # Desbloquear señales
            self.venta_table.blockSignals(False)
        
        # Actualizar totales después de cualquier cambio
        QtCore.QTimer.singleShot(100, self.actualizar_total_venta)

    def actualizar_total_venta(self):
        total_con_igv = 0.0  # Suma de todos los precios finales (con IGV incluido)
        items_count = 0
        
        for row in range(self.venta_table.rowCount()):
            # Contar items - verificar si el item existe
            cant_item = self.venta_table.item(row, 1)
            if cant_item:
                items_count += self._parse_quantity_value(cant_item.text(), 0)
            
            # Sumar total (que es el precio FINAL con IGV incluido)
            total_item = self.venta_table.item(row, 3)
            if total_item:
                total_con_igv += self._parse_money_text(total_item.text(), 0.0)
        
        # El total_con_igv incluye IGV, entonces debemos extraerlo
        # subtotal = total / 1.18  (para extraer el IGV que está incluido)
        subtotal = total_con_igv / 1.18  # Precio SIN IGV
        igv = total_con_igv - subtotal  # IGV que está incluido en el total
        
        # Actualizar labels
        self.items_count_label.setText(str(items_count))
        self.subtotal_label.setText(f"S/. {subtotal:.2f}")
        self.igv_label.setText(f"S/. {igv:.2f}")
        self.total_venta_label.setText(f"S/. {total_con_igv:.2f}")
        self._sync_sale_adelanto_limit()
        self._update_multi_metodo_pago_sale_state()

    def registrar_venta(self):
        # 🛡️ VERIFICAR PERMISO: Solo puede registrar ventas si tiene permiso 'registrar'
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('ventas', 'registrar'):
                QMessageBox.warning(
                    self,
                    "Permiso Denegado",
                    "No tienes permiso para registrar ventas."
                )
                return
        self._set_register_sale_busy(True)
        try:
            paciente_dni = self.entry_venta_paciente.text().strip()
            nombre_editado = self.label_venta_nombre.text().strip() if hasattr(self, 'label_venta_nombre') else ""
            metodo_pago = self.metodo_pago_combo.currentText()
            vendedor_nombre = self._get_selected_sale_vendedor()

            if self.venta_table.rowCount() == 0:
                QMessageBox.critical(self, "Error", "Agregue al menos un producto a la venta.")
                return

            if self.metodo_pago_combo.count() == 0 or metodo_pago == "Sin métodos de pago":
                QMessageBox.critical(self, "Error", "Debe seleccionar un método de pago.")
                return

            # Buscar en pacientes y clientes
            pacientes = cargar_pacientes(self.username)
            paciente_existente = next((p for p in pacientes if p.get('dni') == paciente_dni), None)

            # Si no encuentra en pacientes, buscar en clientes
            if not paciente_existente:
                clientes = cargar_clientes(self.username)
                paciente_existente = next((c for c in clientes if c.get('dni') == paciente_dni), None)

            if not paciente_existente and paciente_dni != "00000000":
                QMessageBox.critical(self, "Error", "Paciente/Cliente no encontrado. Por favor, regístrelo primero.")
                return

            if paciente_dni == "00000000":
                paciente_nombre = nombre_editado or "Cliente Genérico"
            else:
                paciente_nombre = nombre_editado or paciente_existente.get('nombre', 'Desconocido')

            if hasattr(self, 'fecha_venta_edit'):
                sale_date_str = self.fecha_venta_edit.date().toString("dd/MM/yyyy")
                if sale_date_str == datetime.datetime.now().strftime("%d/%m/%Y"):
                    final_fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                else:
                    final_fecha_str = f"{sale_date_str} {datetime.datetime.now().strftime('%H:%M:%S')}"
            else:
                final_fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            items = []
            productos = cargar_productos(self.username)
            productos_por_codigo = {}
            productos_por_nombre = {}
            for producto in productos:
                if not isinstance(producto, dict):
                    continue
                codigo_ref = str(producto.get('codigo', '') or '').strip()
                nombre_ref = str(producto.get('nombre', '') or '').strip()
                if codigo_ref:
                    productos_por_codigo[codigo_ref] = producto
                if nombre_ref:
                    productos_por_nombre[nombre_ref] = producto

            for row in range(self.venta_table.rowCount()):
                QtWidgets.QApplication.processEvents()
                producto_item = self.venta_table.item(row, 0)
                cantidad_item = self.venta_table.item(row, 1)
                subtotal_item = self.venta_table.item(row, 3)
                precio_item = self.venta_table.item(row, 2)
                prod_display = str(producto_item.text() if producto_item else '').strip()
                prod_codigo = str(producto_item.data(QtCore.Qt.UserRole + 1) if producto_item else '' or '').strip()
                prod_nombre = prod_display
                if prod_display and " - " in prod_display:
                    _, parsed_name = prod_display.split(" - ", 1)
                    prod_nombre = str(parsed_name or '').strip() or prod_display

                cantidad = self._parse_quantity_value(cantidad_item.text() if cantidad_item else 0, 0)
                if cantidad <= 0:
                    QMessageBox.warning(self, "Cantidad inválida", f"La cantidad para '{prod_display or prod_nombre}' debe ser mayor a 0.")
                    return

                prod_en_stock = productos_por_codigo.get(prod_codigo) if prod_codigo else None
                if prod_en_stock is None:
                    prod_en_stock = productos_por_nombre.get(prod_nombre)

                try:
                    precio_venta_actual = self._parse_money_text(precio_item.text() if precio_item else 0, 0.0)
                except (ValueError, AttributeError):
                    precio_venta_actual = 0.0

                if prod_en_stock and int(prod_en_stock.get('stock', 0)) >= cantidad:
                    items.append({
                        'nombre': prod_nombre,
                        'codigo': prod_codigo,
                        'cantidad': cantidad,
                        'total': self._parse_money_text(subtotal_item.text() if subtotal_item else 0, 0.0),
                        'precio_unitario': precio_venta_actual
                    })
                    prod_en_stock['stock'] = int(prod_en_stock.get('stock', 0)) - cantidad
                    self.add_kardex_entry('Salida', prod_nombre, cantidad, precio_venta_actual, fecha=final_fecha_str)
                else:
                    stock_actual = int(prod_en_stock.get('stock', 0)) if prod_en_stock else 0
                    dialog = AgregarStockDialog(prod_nombre, stock_actual, cantidad, self)

                    while True:
                        if dialog.exec_() == QDialog.Accepted:
                            unidades_agregar = dialog.get_unidades()
                            if unidades_agregar > 0 and prod_en_stock is not None:
                                prod_en_stock['stock'] = int(prod_en_stock.get('stock', 0)) + unidades_agregar
                                self.add_kardex_entry('Entrada', prod_nombre, unidades_agregar, prod_en_stock.get('costo', 0), fecha=final_fecha_str)
                                items.append({
                                    'nombre': prod_nombre,
                                    'codigo': prod_codigo,
                                    'cantidad': cantidad,
                                    'total': self._parse_money_text(subtotal_item.text() if subtotal_item else 0, 0.0),
                                    'precio_unitario': precio_venta_actual
                                })
                                prod_en_stock['stock'] = int(prod_en_stock.get('stock', 0)) - cantidad
                                self.add_kardex_entry('Salida', prod_nombre, cantidad, precio_venta_actual, fecha=final_fecha_str)
                                break

                            QMessageBox.warning(
                                self,
                                "Stock Requerido",
                                f"Debe agregar al menos 1 unidad de {prod_nombre} para continuar con la venta."
                            )
                            dialog = AgregarStockDialog(prod_nombre, int(prod_en_stock.get('stock', 0)) if prod_en_stock else 0, cantidad, self)
                        else:
                            QMessageBox.warning(
                                self,
                                "Venta Cancelada",
                                f"Stock insuficiente para {prod_nombre}. Venta cancelada."
                            )
                            return

            guardar_productos(self.username, productos)
            QtWidgets.QApplication.processEvents()

            total = 0.0
            for row in range(self.venta_table.rowCount()):
                subtotal_item = self.venta_table.item(row, 3)
                total += self._parse_money_text(subtotal_item.text() if subtotal_item else 0, 0.0)

            descuento_total = 0.0
            for row in range(self.venta_table.rowCount()):
                cant_item = self.venta_table.item(row, 1)
                descuento_item = self.venta_table.item(row, 4)
                subtotal_item = self.venta_table.item(row, 3)

                if cant_item and descuento_item:
                    try:
                        cantidad = max(1, self._parse_quantity_value(cant_item.text(), 1))
                        precio_original = descuento_item.data(QtCore.Qt.UserRole) or 0
                        subtotal_row = self._parse_money_text(subtotal_item.text() if subtotal_item else 0, 0.0)
                        if cantidad > 0:
                            precio_actual = subtotal_row / cantidad
                            descuento_total += (precio_original - precio_actual) * cantidad
                    except (ValueError, TypeError):
                        pass

            subtotal = total / 1.18
            igv = total - subtotal

            es_pago_parcial = bool(getattr(self, 'checkbox_pago_partes', None) and self.checkbox_pago_partes.isChecked())
            monto_pagado = total
            if es_pago_parcial:
                try:
                    monto_pagado = float(self.entry_adelanto.value())
                except (ValueError, TypeError):
                    monto_pagado = 0.0

            monto_faltante = max(0.0, total - monto_pagado) if es_pago_parcial else 0.0
            es_pago_partes = bool(es_pago_parcial and monto_faltante > 0.05)
            try:
                metodo_pago, metodos_pago_detalle = self._build_sale_payment_details(monto_pagado if es_pago_parcial else total)
            except ValueError as exc:
                QMessageBox.critical(self, "Error", str(exc))
                return
            comision_activada = bool(getattr(self, 'checkbox_comision_venta', None) and self.checkbox_comision_venta.isChecked())
            comision_monto = float(self.entry_comision_venta.value()) if comision_activada and hasattr(self, 'entry_comision_venta') else 0.0
            comision_usuario = vendedor_nombre if comision_activada and comision_monto > 0 else ""

            ventas = cargar_ventas(self.username)
            numero_orden = self._resolve_order_number_for_sale(ventas=ventas)

            nueva_venta = {
                'fecha': final_fecha_str,
                'paciente_dni': paciente_dni,
                'paciente_nombre': paciente_nombre,
                'usuario': self.username,
                'helper_name': self.parent_app.helper_name if (self.parent_app and self.parent_app.is_helper) else None,
                'numero_orden': numero_orden,
                'items': items,
                'subtotal': subtotal,
                'igv': igv,
                'total': total,
                'descuento_total': descuento_total,
                'metodo_pago': metodo_pago,
                'metodos_pago_detalle': metodos_pago_detalle,
                'pago_mixto': bool(len(metodos_pago_detalle) > 1),
                'es_pago_partes': es_pago_partes,
                'es_pago_parcial': es_pago_partes,
                'monto_adelanto': monto_pagado if es_pago_partes else 0.0,
                'monto_faltante': monto_faltante,
                'monto_pagado': monto_pagado,
                'comision_activada': comision_activada,
                'comision_monto': comision_monto,
                'comision_usuario': comision_usuario,
                'vendedor': vendedor_nombre
            }

            if es_pago_partes:
                nueva_venta['deuda_id'] = self._generar_deuda_id_unico()

            nueva_venta['id'] = self._generar_id_venta_unico(ventas)
            ventas.append(nueva_venta)
            guardar_ventas(self.username, ventas)
            QtWidgets.QApplication.processEvents()

            try:
                audit_mgr = None
                if hasattr(self.parent_app, 'app_instance') and hasattr(self.parent_app.app_instance, 'audit_manager'):
                    audit_mgr = self.parent_app.app_instance.audit_manager
                elif hasattr(self.parent_app, 'audit_manager'):
                    audit_mgr = self.parent_app.audit_manager

                if audit_mgr:
                    helper_name = getattr(self.parent_app, 'helper_name', None)
                    user_id = getattr(self.parent_app, 'user_id', 'unknown')
                    audit_mgr.log_action(
                        user_id=user_id,
                        username=self.username,
                        helper_name=helper_name,
                        action='crear',
                        module='ventas',
                        details=f"Venta de S/. {total:.2f} a {paciente_nombre} ({paciente_dni}) - Método: {metodo_pago}"
                    )
                    print(f"[LIBRO CONTABLE] ✅ Venta registrada: S/. {total:.2f}")
                else:
                    print("[LIBRO CONTABLE] audit_manager no disponible (se omite auditoria)")
            except Exception as e:
                print(f"[LIBRO CONTABLE] Error al registrar venta: {e}")
                import traceback
                traceback.print_exc()

            QMessageBox.information(self, "Éxito", "Venta registrada correctamente.")

            self.last_sale = nueva_venta
            self.last_sale_paciente_name = paciente_nombre
            self.btn_generar_boleta.setHidden(False)
            self._prefilled_order_number = ""
            self._refresh_order_number_preview(ventas=ventas)

            try:
                self.sales_history._reload_sales()
            except Exception as e:
                print(f"Error al recargar historial: {e}")
        finally:
            self._set_register_sale_busy(False)

    def generar_boleta(self):
        if hasattr(self, 'last_sale') and self.last_sale:
            nombre_optica = cargar_nombre_optica(self.username)
            
            # Mostrar diálogo para seleccionar tamaño de boleta
            try:
                from gui.dialogs.receipt_size_dialog import ReceiptSizeDialog
                size_dialog = ReceiptSizeDialog(self.username, self)
                if size_dialog.exec_() != ReceiptSizeDialog.Accepted:
                    return  # Usuario canceló
                
                receipt_width = size_dialog.get_selected_width()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error al abrir configuración de tamaño:\n{e}")
                receipt_width = 80  # Usar default si hay error
            
            try:
                # Usar GeneradorBoletasPlantilla para respetar la plantilla del usuario
                generador = GeneradorBoletasPlantilla(self.username)
                print(f"[SalesPage] GeneradorBoletasPlantilla creado. Plantilla: {generador.plantilla_seleccionada}")
                
                # Convertir items al formato correcto
                items = self.last_sale.get('items', [])
                productos = []
                print(f"[DEBUG] Items raw: {items}")
                for item in items:
                    if isinstance(item, dict):
                        # Intentar obtener el nombre del producto de varias claves posibles
                        nombre_p = str(item.get('producto') or item.get('nombre') or 'Producto').strip()
                        precio_u = float(item.get('precio_unitario', item.get('precio', 0)) or 0)
                        subtotal_item = float(item.get('subtotal', item.get('total', precio_u)) or 0)

                        prod = {
                            'nombre': nombre_p,
                            'cantidad': int(item.get('cantidad', 1) or 1),
                            'precio': precio_u,
                            'total': subtotal_item
                        }
                        print(f"[DEBUG] Producto formateado: {prod}")
                        productos.append(prod)
                
                print(f"[DEBUG] Productos finales: {productos}")
                
                # Calcular totales usando los valores de la venta para mayor precisión
                total_final = float(self.last_sale.get('total', sum(p.get('total', 0) for p in productos)))
                subtotal = float(self.last_sale.get('subtotal', total_final / 1.18))
                igv = float(self.last_sale.get('igv', total_final - subtotal))
                
                print(f"[DEBUG] Total Final (con IGV): {total_final:.2f}")
                print(f"[DEBUG] Subtotal (sin IGV): {subtotal:.2f}")
                print(f"[DEBUG] IGV 18%: {igv:.2f}")
                
                # Preparar datos de la boleta
                # Determinar vendedor: si es ayudante, mostrar su nombre; si no, mostrar usuario
                vendedor_nombre = self.last_sale.get('helper_name') if self.last_sale.get('helper_name') else self.username
                ruc_empresa = cargar_ruc(self.username)
                
                datos_boleta = {
                    'nombre_optica': nombre_optica,
                    'ruc': ruc_empresa,
                    'ruc_empresa': ruc_empresa,
                    'direccion': 'Dirección no configurada',
                    'numero_boleta': f"VENTA-{self.last_sale.get('id', 'S/N')}",
                    'fecha': self.last_sale.get('fecha', ''),
                    'cliente': self.last_sale_paciente_name,
                    'productos': productos,
                    'subtotal': subtotal,
                    'igv': igv,
                    'total': total_final,
                    'descuento': self.last_sale.get('descuento_total', 0),
                    'metodo_pago': self.last_sale.get('metodo_pago', 'Efectivo'),
                    'pie_pagina': 'Gracias por su compra',
                    'es_pago_parcial': self.last_sale.get('es_pago_parcial', False),
                    'monto_pagado': self.last_sale.get('monto_pagado', 0),
                    'vendedor': vendedor_nombre  # Mostrar ayudante si existe, si no usuario
                }
                
                print(f"[SalesPage] Productos: {len(productos)}, Subtotal: {subtotal:.2f}, IGV: {igv:.2f}, Total: {total_final:.2f}")
                # Obtener tamaño del logo de la UI
                tamano_logo_px = self.slider_logo_tamano_venta.value() if hasattr(self, 'slider_logo_tamano_venta') else cargar_tamano_logo(self.username)
                print(f"[SalesPage] Tamaño del logo: {tamano_logo_px}px")
                filepath = generador.generar_boleta(datos_boleta, tamano_logo_px=tamano_logo_px)
                print(f"[SalesPage] Boleta generada: {filepath}")
                
                if not os.path.exists(filepath):
                    QMessageBox.critical(self, "Error de Archivo", f"El archivo PDF no se encontró en la ruta: {filepath}")
                    return
            except Exception as e:
                QMessageBox.critical(self, "Error al generar PDF", f"No se pudo generar el PDF: {e}")
                import traceback
                print(traceback.format_exc())
                return
            
            try:
                # Abrir con PDFViewerDialog dentro de VISO
                from gui.dialogs.pdf_viewer_dialog import PDFViewerDialog
                viewer = PDFViewerDialog(filepath, self)
                viewer.exec_()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo PDF: {e}")
        else:
            QMessageBox.warning(self, "Advertencia", "No hay una venta reciente para generar la boleta.")

    def clear_sales_form_and_table(self):
        self.entry_venta_paciente.setText("00000000")
        self.label_venta_nombre.setText("")
        self.venta_table.setRowCount(0)
        if hasattr(self, "barcode_input"):
            self.barcode_input.clear()
        if hasattr(self, "checkbox_pago_partes"):
            self.checkbox_pago_partes.setChecked(False)
        if hasattr(self, "entry_adelanto"):
            self.entry_adelanto.setValue(0.0)
        if hasattr(self, "checkbox_multi_metodo_pago"):
            self.checkbox_multi_metodo_pago.setChecked(False)
        if hasattr(self, "metodo_pago_combo_2") and self.metodo_pago_combo_2.count() > 0:
            self.metodo_pago_combo_2.setCurrentIndex(0)
        if hasattr(self, "metodo_pago_combo_3") and self.metodo_pago_combo_3.count() > 0:
            self.metodo_pago_combo_3.setCurrentIndex(0)
        if hasattr(self, "entry_metodo_pago_monto_1"):
            self.entry_metodo_pago_monto_1.setValue(0.0)
        if hasattr(self, "entry_metodo_pago_monto_2"):
            self.entry_metodo_pago_monto_2.setValue(0.0)
        if hasattr(self, "checkbox_comision_venta"):
            self.checkbox_comision_venta.setChecked(False)
        if hasattr(self, "entry_comision_venta"):
            self.entry_comision_venta.setValue(0.0)
        if hasattr(self, "discount_input"):
            self.discount_input.setText("0")
        if hasattr(self, "fecha_venta_edit"):
            from PyQt5.QtCore import QDate
            self.fecha_venta_edit.setDate(QDate.currentDate())
        self.update_metodo_pago_combo()
        self.update_vendedor_combo()
        self._prefilled_order_number = ""
        self._refresh_order_number_preview()
        self.actualizar_total_venta()
        self.btn_generar_boleta.setHidden(True)
        self._update_multi_metodo_pago_sale_state()

    def clear_sales_form_and_table_with_loader(self):
        if getattr(self, "_clear_sale_in_progress", False):
            return

        self._clear_sale_in_progress = True
        self._set_clear_sale_busy(True)

        def _run_clear():
            try:
                self.clear_sales_form_and_table()
            finally:
                QTimer.singleShot(320, _finish_clear)

        def _finish_clear():
            self._clear_sale_in_progress = False
            self._set_clear_sale_busy(False)

        QTimer.singleShot(0, _run_clear)

    def add_kardex_entry(self, movimiento, producto_nombre, cantidad, costo_unitario, fecha=None):
        productos = cargar_productos(self.username)
        prod_info = next((p for p in productos if p['nombre'] == producto_nombre), None)
        stock_final = prod_info['stock'] if prod_info else 0

        # Si el costo es 0, usar precio de venta como referencia
        real_costo = costo_unitario
        if real_costo == 0 and prod_info:
            real_costo = float(prod_info.get('venta', 0) or 0)

        entry = {
            'fecha': fecha if fecha else datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'movimiento': movimiento,
            'producto': producto_nombre,
            'cantidad': cantidad,
            'costo_unitario': real_costo,
            'valor_total': real_costo * cantidad,
            'stock_final': stock_final
        }

        try:
            from utils.file_handler import agregar_movimiento_kardex

            if agregar_movimiento_kardex(self.username, entry):
                return
        except Exception:
            pass

        kardex_data = cargar_kardex(self.username)
        kardex_data.append(entry)
        guardar_kardex(self.username, kardex_data)

    def create_manual_sales_tab(self):
        """Crea la pestaña de Venta Manual."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header minimalista
        header = QWidget()
        header.setStyleSheet("background: white;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(0)
        
        # Título
        title_layout = QVBoxLayout()
        title = QLabel("Venta Manual")
        title.setStyleSheet("font-size: 18px; color: #333333; font-weight: 600;")
        subtitle = QLabel("Ingrese los datos de la venta manualmente")
        subtitle.setStyleSheet("font-size: 12px; color: #999999; margin-top:4px; font-weight: 400;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_layout.setSpacing(2)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addWidget(header)
        
        # Separador
        separator = QWidget()
        separator.setStyleSheet("background: #EEEEEE;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Contenedor con scroll
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: white; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)
        
        # ===== SECCIÓN DE DATOS DEL CLIENTE =====
        client_group = QGroupBox("Datos del Cliente")
        client_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: 600;
                color: #333333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)
        client_layout = QGridLayout(client_group)
        client_layout.setSpacing(12)
        client_layout.setContentsMargins(15, 15, 15, 15)
        
        # DNI
        client_layout.addWidget(QLabel("DNI del Cliente:"), 0, 0)
        
        # Contenedor horizontal para DNI + botón de búsqueda
        dni_container = QWidget()
        dni_layout = QHBoxLayout(dni_container)
        dni_layout.setContentsMargins(0, 0, 0, 0)
        dni_layout.setSpacing(8)
        
        self.manual_dni_input = QLineEdit()
        self.manual_dni_input.setPlaceholderText("Ej: 12345678 o 00000000 para cliente genérico")
        self.manual_dni_input.setText("00000000")
        self.manual_dni_input.setMinimumHeight(35)
        dni_layout.addWidget(self.manual_dni_input)
        
        # Botón de búsqueda
        self.manual_search_dni_btn = QPushButton("Buscar")
        self.manual_search_dni_btn.setMinimumHeight(35)
        self.manual_search_dni_btn.setMaximumWidth(100)
        self.manual_search_dni_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #1565C0;
            }
            QPushButton:pressed {
                background: #0D47A1;
            }
        """)
        self.manual_search_dni_btn.clicked.connect(self.buscar_dni_cliente)
        dni_layout.addWidget(self.manual_search_dni_btn)
        
        client_layout.addWidget(dni_container, 0, 1)
        
        # Nombre del Cliente
        client_layout.addWidget(QLabel("Nombre del Cliente:"), 1, 0)
        self.manual_nombre_input = QLineEdit()
        self.manual_nombre_input.setPlaceholderText("Ej: Juan Pérez")
        self.manual_nombre_input.setMinimumHeight(35)
        client_layout.addWidget(self.manual_nombre_input, 1, 1)
        
        # Teléfono (opcional)
        client_layout.addWidget(QLabel("Teléfono (opcional):"), 2, 0)
        self.manual_telefono_input = QLineEdit()
        self.manual_telefono_input.setPlaceholderText("Ej: 987654321")
        self.manual_telefono_input.setMinimumHeight(35)
        client_layout.addWidget(self.manual_telefono_input, 2, 1)
        
        content_layout.addWidget(client_group)
        
        # ===== SECCIÓN DE PRODUCTOS =====
        product_group = QGroupBox("Datos del Producto")
        product_group.setStyleSheet(client_group.styleSheet())
        product_layout = QGridLayout(product_group)
        product_layout.setSpacing(12)
        product_layout.setContentsMargins(15, 15, 15, 15)
        
        # Nombre del Producto
        product_layout.addWidget(QLabel("Nombre del Producto:"), 0, 0)
        self.manual_producto_input = QLineEdit()
        self.manual_producto_input.setPlaceholderText("Ej: Gafas Cat Eyes")
        self.manual_producto_input.setMinimumHeight(35)
        product_layout.addWidget(self.manual_producto_input, 0, 1)
        
        # Descripción (opcional)
        product_layout.addWidget(QLabel("Descripción (opcional):"), 1, 0)
        self.manual_descripcion_input = QLineEdit()
        self.manual_descripcion_input.setPlaceholderText("Ej: Monturas polarizadas")
        self.manual_descripcion_input.setMinimumHeight(35)
        product_layout.addWidget(self.manual_descripcion_input, 1, 1)
        
        # Cantidad
        product_layout.addWidget(QLabel("Cantidad:"), 2, 0)
        self.manual_cantidad_spin = QSpinBox()
        self.manual_cantidad_spin.setMinimum(1)
        self.manual_cantidad_spin.setValue(1)
        self.manual_cantidad_spin.setMinimumHeight(35)
        self.manual_cantidad_spin.valueChanged.connect(self.actualizar_total_manual)
        product_layout.addWidget(self.manual_cantidad_spin, 2, 1)
        
        # Precio Unitario
        product_layout.addWidget(QLabel("Precio Unitario (con IGV):"), 3, 0)
        self.manual_precio_input = QtWidgets.QDoubleSpinBox()
        self.manual_precio_input.setMinimum(0.00)
        self.manual_precio_input.setMaximum(99999.99)
        self.manual_precio_input.setDecimals(2)
        self.manual_precio_input.setValue(0.00)
        self.manual_precio_input.setMinimumHeight(35)
        self.manual_precio_input.valueChanged.connect(self.actualizar_total_manual)
        product_layout.addWidget(self.manual_precio_input, 3, 1)
        
        # Total
        product_layout.addWidget(QLabel("Subtotal (sin IGV):"), 4, 0)
        self.manual_subtotal_label = QLabel("S/. 0.00")
        self.manual_subtotal_label.setStyleSheet("font-weight: 600; color: #1976D2; font-size: 14px;")
        product_layout.addWidget(self.manual_subtotal_label, 4, 1)
        
        content_layout.addWidget(product_group)
        
        # ===== SECCIÓN DE PAGO =====
        payment_group = QGroupBox("Datos de Pago")
        payment_group.setStyleSheet(client_group.styleSheet())
        payment_layout = QGridLayout(payment_group)
        payment_layout.setSpacing(12)
        payment_layout.setContentsMargins(15, 15, 15, 15)
        
        # Método de Pago
        payment_layout.addWidget(QLabel("Método de Pago:"), 0, 0)
        self.manual_metodo_combo = QComboBox()
        
        # Cargar métodos de pago dinámicamente desde la configuración del usuario
        metodos_pago = self._cargar_metodos_pago()
        if metodos_pago:
            self.manual_metodo_combo.addItems(metodos_pago)
        else:
            # Si no hay métodos configurados, usar valores por defecto
            self.manual_metodo_combo.addItems(["Efectivo", "Tarjeta", "Transferencia", "Cheque"])
        
        self.manual_metodo_combo.setMinimumHeight(35)
        payment_layout.addWidget(self.manual_metodo_combo, 0, 1)
        
        # ¿Pago en Partes?
        payment_layout.addWidget(QLabel("¿Pago en Partes?"), 1, 0)
        self.manual_pago_partes_check = QtWidgets.QCheckBox("Sí, el cliente pagará en cuotas")
        self.manual_pago_partes_check.setMinimumHeight(35)
        self.manual_pago_partes_check.stateChanged.connect(self._toggle_monto_adelanto)
        payment_layout.addWidget(self.manual_pago_partes_check, 1, 1)
        
        # ¿Cuánto dejó de adelanto? (inicialmente oculto)
        payment_layout.addWidget(QLabel("¿Cuánto dejó de adelanto?"), 2, 0)
        self.manual_monto_adelanto_input = QtWidgets.QDoubleSpinBox()
        self.manual_monto_adelanto_input.setMinimum(0.00)
        self.manual_monto_adelanto_input.setMaximum(99999.99)
        self.manual_monto_adelanto_input.setDecimals(2)
        self.manual_monto_adelanto_input.setValue(0.00)
        self.manual_monto_adelanto_input.setMinimumHeight(35)
        self.manual_monto_adelanto_input.setVisible(False)
        payment_layout.addWidget(self.manual_monto_adelanto_input, 2, 1)
        
        # IGV
        payment_layout.addWidget(QLabel("IGV (18%):"), 3, 0)
        self.manual_igv_label = QLabel("S/. 0.00")
        self.manual_igv_label.setStyleSheet("font-weight: 600; color: #D32F2F; font-size: 14px;")
        payment_layout.addWidget(self.manual_igv_label, 3, 1)
        
        # Total con IGV
        payment_layout.addWidget(QLabel("Total (con IGV):"), 4, 0)
        self.manual_total_label = QLabel("S/. 0.00")
        self.manual_total_label.setStyleSheet("font-weight: 700; color: #2E7D32; font-size: 16px;")
        payment_layout.addWidget(self.manual_total_label, 4, 1)
        
        content_layout.addWidget(payment_group)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # ===== BOTONES =====
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 0, 20, 20)
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.setMinimumWidth(120)
        btn_limpiar.setMinimumHeight(40)
        btn_limpiar.clicked.connect(self.limpiar_venta_manual)
        button_layout.addWidget(btn_limpiar)
        
        btn_registrar = QPushButton("✓ Registrar Venta Manual")
        btn_registrar.setObjectName("primaryButton")
        btn_registrar.setMinimumWidth(180)
        btn_registrar.setMinimumHeight(40)
        btn_registrar.clicked.connect(self.registrar_venta_manual)
        button_layout.addWidget(btn_registrar)
        
        layout.addLayout(button_layout)
         
        return tab

    def create_caja_tab(self):
        """Crea la pestaña de Caja Diaria."""
        from gui.main_window_pages.caja_page import CajaPage
        return CajaPage(self)

    def create_guia_remision_tab(self):
        """Crea la pestaña historial de guías de remisión."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background: white;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(10)

        title_layout = QVBoxLayout()
        title = QLabel("Historial de Guias de Remision")
        title.setStyleSheet("font-size: 18px; color: #333333; font-weight: 600;")
        subtitle = QLabel("Revisa solicitudes enviadas y abre el formulario cuando necesites crear o recibir una guía")
        subtitle.setStyleSheet("font-size: 12px; color: #999999; margin-top:4px; font-weight: 400;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_layout.setSpacing(2)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.guia_hist_refresh_btn = QPushButton("Actualizar")
        self.guia_hist_refresh_btn.setMinimumHeight(36)
        self.guia_hist_refresh_btn.clicked.connect(lambda: self._guia_reload_requests_from_cloud(silent=False))
        header_layout.addWidget(self.guia_hist_refresh_btn)

        self.guia_hist_open_btn = QPushButton("Abrir guía")
        self.guia_hist_open_btn.setMinimumHeight(36)
        self.guia_hist_open_btn.clicked.connect(self._guia_open_selected_dialog)
        header_layout.addWidget(self.guia_hist_open_btn)

        self.guia_hist_new_btn = QPushButton("Nueva guía")
        self.guia_hist_new_btn.setMinimumHeight(36)
        self.guia_hist_new_btn.clicked.connect(self._guia_open_new_dialog)
        self.guia_hist_new_btn.setVisible(True)
        header_layout.addWidget(self.guia_hist_new_btn)
        layout.addWidget(header)

        separator = QWidget()
        separator.setStyleSheet("background: #EEEEEE;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        self.guia_hist_global_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self.guia_hist_global_placeholder)
        placeholder_layout.setContentsMargins(40, 40, 40, 40)
        placeholder_layout.setSpacing(16)
        placeholder_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.guia_hist_global_text = QLabel(
            "No has seleccionado ninguna sucursal; puedes ingresar una guía directamente a una."
        )
        self.guia_hist_global_text.setAlignment(Qt.AlignCenter)
        self.guia_hist_global_text.setWordWrap(True)
        self.guia_hist_global_text.setStyleSheet(
            "font-size: 14px; color: #6B7280; font-weight: 500; padding-top: 8px;"
        )
        placeholder_layout.addWidget(self.guia_hist_global_text)

        self.guia_hist_global_new_btn = QPushButton("Crear nueva guía")
        self.guia_hist_global_new_btn.setMinimumHeight(42)
        self.guia_hist_global_new_btn.setMinimumWidth(220)
        self.guia_hist_global_new_btn.clicked.connect(self._guia_open_new_dialog)
        placeholder_layout.addWidget(self.guia_hist_global_new_btn, alignment=Qt.AlignHCenter)
        layout.addWidget(self.guia_hist_global_placeholder)

        self.guia_history_table = QTableWidget()
        self.guia_history_table.setColumnCount(7)
        self.guia_history_table.setHorizontalHeaderLabels([
            "Fecha",
            "Serie/Número",
            "Sucursal destino",
            "Destinatario",
            "Estado",
            "Unidades",
            "",
        ])
        self.guia_history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.guia_history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.guia_history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.guia_history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.guia_history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.guia_history_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.guia_history_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.guia_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.guia_history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.guia_history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.guia_history_table.setAlternatingRowColors(True)
        self.guia_history_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: none;
                gridline-color: #F0F0F0;
            }
            QTableWidget::item {
                padding: 8px 10px;
            }
            QHeaderView::section {
                background: #FAFAFA;
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #E0E0E0;
                font-weight: 600;
            }
        """)
        self.guia_history_table.cellDoubleClicked.connect(lambda *_: self._guia_open_selected_dialog())
        layout.addWidget(self.guia_history_table)

        self._guia_update_history_mode()
        self._guia_refresh_history_table()
        if not self._guia_is_madre_user():
            self._guia_reload_requests_from_cloud(silent=True)
        return tab

    def _build_guia_remision_form_widget(self):
        form_root = QWidget()
        layout = QVBoxLayout(form_root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: white; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        group_style = """
            QGroupBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: 600;
                color: #333333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """

        self.guia_serie_input = QLineEdit()
        self.guia_numero_input = QLineEdit()
        self.guia_fecha_emision = QDateEdit(calendarPopup=True)
        self.guia_fecha_traslado = QDateEdit(calendarPopup=True)
        self.guia_motivo_combo = QComboBox()
        self.guia_doc_ref_input = QLineEdit()
        self.guia_observaciones_input = QtWidgets.QTextEdit()
        self.guia_dest_doc_input = QLineEdit()
        self.guia_dest_nombre_input = QLineEdit()
        self.guia_source_dispatch_input = QLineEdit()
        self.guia_punto_partida_input = QLineEdit()
        self.guia_punto_llegada_input = QLineEdit()
        self.guia_transportista_doc_input = QLineEdit()
        self.guia_transportista_nombre_input = QLineEdit()
        self.guia_placa_input = QLineEdit()
        self.guia_conductor_input = QLineEdit()
        self.guia_selector_combo = QComboBox()
        self.guia_target_branch_combo = QComboBox()
        self.guia_detalle_table = QTableWidget()
        self.guia_total_items_label = QLabel("0")
        self.guia_total_lineas_label = QLabel("0")

        self.guia_fecha_emision.setDate(QDate.currentDate())
        self.guia_fecha_traslado.setDate(QDate.currentDate())
        self.guia_fecha_emision.setDisplayFormat("dd/MM/yyyy")
        self.guia_fecha_traslado.setDisplayFormat("dd/MM/yyyy")
        self.guia_serie_input.setPlaceholderText("Ej: T001")
        self.guia_numero_input.setPlaceholderText("Ej: 000123")
        self.guia_doc_ref_input.setPlaceholderText("Factura, boleta, pedido o documento interno")
        self.guia_observaciones_input.setPlaceholderText("Observaciones adicionales del traslado...")
        self.guia_observaciones_input.setFixedHeight(90)
        self.guia_dest_doc_input.setPlaceholderText("DNI o RUC del destinatario")
        self.guia_dest_nombre_input.setPlaceholderText("Nombre o razón social")
        self.guia_source_dispatch_input.setPlaceholderText("Ej: Almacén central / Sucursal origen")
        self.guia_punto_partida_input.setPlaceholderText("Dirección exacta de salida")
        self.guia_punto_llegada_input.setPlaceholderText("Dirección exacta de destino")
        self.guia_transportista_doc_input.setPlaceholderText("Dato opcional")
        self.guia_transportista_nombre_input.setPlaceholderText("Nombre de la empresa de transporte")
        self.guia_placa_input.setPlaceholderText("Opcional")
        self.guia_conductor_input.setPlaceholderText("Opcional")
        self.guia_selector_combo.setMinimumHeight(35)
        self.guia_selector_combo.currentIndexChanged.connect(self._guia_on_request_selected)
        self.guia_target_branch_combo.setMinimumHeight(35)

        self.guia_motivo_combo.addItems([
            "Venta",
            "Traslado entre sucursales",
            "Compra",
            "Consignacion",
            "Devolucion",
            "Traslado para transformacion",
            "Otros",
        ])

        for widget in [
            self.guia_serie_input,
            self.guia_numero_input,
            self.guia_doc_ref_input,
            self.guia_dest_doc_input,
            self.guia_dest_nombre_input,
            self.guia_source_dispatch_input,
            self.guia_punto_partida_input,
            self.guia_punto_llegada_input,
            self.guia_transportista_doc_input,
            self.guia_transportista_nombre_input,
            self.guia_placa_input,
            self.guia_conductor_input,
        ]:
            widget.setMinimumHeight(35)

        self.guia_motivo_combo.setMinimumHeight(35)
        self.guia_fecha_emision.setMinimumHeight(35)
        self.guia_fecha_traslado.setMinimumHeight(35)

        self.guia_target_group = QGroupBox("Origen y Destino")
        self.guia_target_group.setStyleSheet(group_style)
        target_layout = QGridLayout(self.guia_target_group)
        target_layout.setSpacing(12)
        target_layout.setContentsMargins(15, 15, 15, 15)
        target_layout.addWidget(QLabel("Enviar desde:"), 0, 0)
        target_layout.addWidget(self.guia_source_dispatch_input, 0, 1, 1, 3)
        target_layout.addWidget(QLabel("Llega a:"), 1, 0)
        target_layout.addWidget(self.guia_target_branch_combo, 1, 1, 1, 3)
        content_layout.addWidget(self.guia_target_group)

        self.guia_child_group = QGroupBox("Solicitud Recibida")
        self.guia_child_group.setStyleSheet(group_style)
        child_layout = QGridLayout(self.guia_child_group)
        child_layout.setSpacing(12)
        child_layout.setContentsMargins(15, 15, 15, 15)
        child_layout.addWidget(QLabel("Guía solicitada:"), 0, 0)
        child_layout.addWidget(self.guia_selector_combo, 0, 1, 1, 2)
        self.guia_cargar_btn = QPushButton("Cargar solicitudes de nube")
        self.guia_cargar_btn.setMinimumHeight(35)
        self.guia_cargar_btn.clicked.connect(self._guia_reload_requests_from_cloud)
        child_layout.addWidget(self.guia_cargar_btn, 0, 3)
        content_layout.addWidget(self.guia_child_group)

        info_group = QGroupBox("Datos de la Guía")
        info_group.setStyleSheet(group_style)
        info_layout = QGridLayout(info_group)
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(15, 15, 15, 15)
        info_layout.addWidget(QLabel("Serie:"), 0, 0)
        info_layout.addWidget(self.guia_serie_input, 0, 1)
        info_layout.addWidget(QLabel("Número:"), 0, 2)
        info_layout.addWidget(self.guia_numero_input, 0, 3)
        info_layout.addWidget(QLabel("Fecha de Emisión:"), 1, 0)
        info_layout.addWidget(self.guia_fecha_emision, 1, 1)
        info_layout.addWidget(QLabel("Fecha de Traslado:"), 1, 2)
        info_layout.addWidget(self.guia_fecha_traslado, 1, 3)
        info_layout.addWidget(QLabel("Motivo de Traslado:"), 2, 0)
        info_layout.addWidget(self.guia_motivo_combo, 2, 1, 1, 3)
        info_layout.addWidget(QLabel("Documento de Referencia:"), 3, 0)
        info_layout.addWidget(self.guia_doc_ref_input, 3, 1, 1, 3)
        info_layout.addWidget(QLabel("Observaciones:"), 4, 0)
        info_layout.addWidget(self.guia_observaciones_input, 4, 1, 1, 3)
        content_layout.addWidget(info_group)

        dest_group = QGroupBox("Destinatario y Ruta")
        dest_group.setStyleSheet(group_style)
        dest_layout = QGridLayout(dest_group)
        dest_layout.setSpacing(12)
        dest_layout.setContentsMargins(15, 15, 15, 15)
        dest_layout.addWidget(QLabel("Documento:"), 0, 0)
        dest_layout.addWidget(self.guia_dest_doc_input, 0, 1)
        dest_layout.addWidget(QLabel("Nombre / Razón Social:"), 0, 2)
        dest_layout.addWidget(self.guia_dest_nombre_input, 0, 3)
        dest_layout.addWidget(QLabel("Dirección de Partida:"), 1, 0)
        dest_layout.addWidget(self.guia_punto_partida_input, 1, 1, 1, 3)
        dest_layout.addWidget(QLabel("Dirección de Llegada:"), 2, 0)
        dest_layout.addWidget(self.guia_punto_llegada_input, 2, 1, 1, 3)
        content_layout.addWidget(dest_group)

        transport_group = QGroupBox("Datos del Transporte")
        transport_group.setStyleSheet(group_style)
        transport_layout = QGridLayout(transport_group)
        transport_layout.setSpacing(12)
        transport_layout.setContentsMargins(15, 15, 15, 15)
        transport_layout.addWidget(QLabel("Empresa de Transporte:"), 0, 0)
        transport_layout.addWidget(self.guia_transportista_doc_input, 0, 1)
        transport_layout.addWidget(QLabel("Nombre Empresa:"), 0, 2)
        transport_layout.addWidget(self.guia_transportista_nombre_input, 0, 3)
        transport_layout.addWidget(QLabel("Placa Vehículo (opcional):"), 1, 0)
        transport_layout.addWidget(self.guia_placa_input, 1, 1)
        transport_layout.addWidget(QLabel("Conductor (opcional):"), 1, 2)
        transport_layout.addWidget(self.guia_conductor_input, 1, 3)
        content_layout.addWidget(transport_group)

        detail_group = QGroupBox("Detalle de Productos")
        detail_group.setStyleSheet(group_style)
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.setContentsMargins(15, 15, 15, 15)
        detail_layout.setSpacing(12)
        detail_toolbar = QHBoxLayout()
        detail_toolbar.setSpacing(8)
        detail_toolbar.addWidget(QLabel("En madre es opcional. En hijo aquí registras lo que realmente llegó."))
        detail_toolbar.addStretch()
        btn_add_row = QPushButton("+ Agregar fila")
        btn_add_row.setMinimumHeight(34)
        btn_add_row.clicked.connect(self._guia_add_detail_row)
        detail_toolbar.addWidget(btn_add_row)
        btn_remove_row = QPushButton("Quitar seleccionada")
        btn_remove_row.setMinimumHeight(34)
        btn_remove_row.clicked.connect(self._guia_remove_selected_row)
        detail_toolbar.addWidget(btn_remove_row)
        detail_layout.addLayout(detail_toolbar)
        self.guia_detalle_table.setColumnCount(8)
        self.guia_detalle_table.setHorizontalHeaderLabels(["Código", "Descripción", "Marca", "Precio compra", "Precio venta", "Cantidad", "Unidad", "Peso Ref."])
        self.guia_detalle_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.guia_detalle_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.guia_detalle_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.guia_detalle_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.guia_detalle_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.guia_detalle_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.guia_detalle_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.guia_detalle_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.guia_detalle_table.horizontalHeader().setMinimumHeight(32)
        self.guia_detalle_table.verticalHeader().setDefaultSectionSize(28)
        self.guia_detalle_table.verticalHeader().setMinimumSectionSize(26)
        self.guia_detalle_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.guia_detalle_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.guia_detalle_table.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.EditKeyPressed |
            QAbstractItemView.AnyKeyPressed
        )
        self.guia_detalle_table.setMinimumHeight(120)
        self.guia_detalle_table.setMaximumHeight(150)
        self.guia_detalle_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #E0E0E0;
                gridline-color: #F0F0F0;
            }
            QTableWidget::item {
                padding: 4px 6px;
            }
            QHeaderView::section {
                background: #FAFAFA;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #E0E0E0;
                font-weight: 600;
            }
        """)
        self.guia_detalle_table.itemChanged.connect(self._guia_update_summary)
        detail_layout.addWidget(self.guia_detalle_table)
        summary_row = QHBoxLayout()
        summary_row.setSpacing(20)
        sum_style_label = "font-weight: 600; color: #666666; font-size: 12px;"
        sum_style_value = "font-weight: 700; color: #1a1a1a; font-size: 13px;"
        label_lineas = QLabel("Líneas:")
        label_lineas.setStyleSheet(sum_style_label)
        self.guia_total_lineas_label.setStyleSheet(sum_style_value)
        label_items = QLabel("Total unidades:")
        label_items.setStyleSheet(sum_style_label)
        self.guia_total_items_label.setStyleSheet(sum_style_value)
        summary_row.addWidget(label_lineas)
        summary_row.addWidget(self.guia_total_lineas_label)
        summary_row.addWidget(label_items)
        summary_row.addWidget(self.guia_total_items_label)
        summary_row.addStretch()
        detail_layout.addLayout(summary_row)
        content_layout.addWidget(detail_group)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        button_layout.addStretch()
        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.setMinimumWidth(120)
        btn_limpiar.setMinimumHeight(40)
        btn_limpiar.clicked.connect(self._guia_clear_form)
        button_layout.addWidget(btn_limpiar)
        self.guia_solicitar_btn = QPushButton("Solicitar guia y subir a nube")
        self.guia_solicitar_btn.setMinimumWidth(220)
        self.guia_solicitar_btn.setMinimumHeight(40)
        self.guia_solicitar_btn.setStyleSheet("""
            QPushButton {
                background: #1f7a3d;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #16632f;
            }
        """)
        self.guia_solicitar_btn.clicked.connect(self._guia_submit_request)
        button_layout.addWidget(self.guia_solicitar_btn)
        self.guia_recepcion_btn = QPushButton("Registrar productos recibidos")
        self.guia_recepcion_btn.setMinimumWidth(230)
        self.guia_recepcion_btn.setMinimumHeight(40)
        self.guia_recepcion_btn.setStyleSheet("""
            QPushButton {
                background: #1d4ed8;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #1e40af;
            }
        """)
        self.guia_recepcion_btn.clicked.connect(self._guia_submit_reception)
        button_layout.addWidget(self.guia_recepcion_btn)
        content_layout.addLayout(button_layout)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        self._guia_add_detail_row()
        self._guia_apply_role_mode()
        return form_root

    def _guia_open_new_dialog(self):
        if (not self._guia_is_madre_user()) and (not self._guia_get_current_child_branch_code()):
            QMessageBox.warning(
                self,
                "Guia de Remision",
                "No se pudo identificar la sucursal actual del trabajador para crear la guía."
            )
            return
        self._guia_open_form_dialog(mode="new")

    def _guia_open_selected_dialog(self):
        requests_list = self._guia_get_filtered_requests()
        row = self.guia_history_table.currentRow() if hasattr(self, "guia_history_table") else -1
        if row < 0 or row >= len(requests_list):
            QMessageBox.information(self, "Guia de Remision", "Selecciona una guía del historial.")
            return
        guide = requests_list[row]
        self._guia_open_form_dialog(mode="existing", guide=guide)

    def _guia_open_form_dialog(self, mode="new", guide=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Formulario de Guía de Remisión")
        dialog.resize(1200, 820)
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.setSpacing(0)
        self.guia_dialog = dialog
        self.guia_dialog_mode = mode
        self.guia_dialog_guide = guide if isinstance(guide, dict) else None
        dialog_layout.addWidget(self._build_guia_remision_form_widget())
        if mode == "existing" and isinstance(guide, dict):
            self._guia_load_request_into_form(guide)
        else:
            self._guia_clear_form()
        dialog.exec_()
        for attr in [
            "guia_serie_input",
            "guia_numero_input",
            "guia_fecha_emision",
            "guia_fecha_traslado",
            "guia_motivo_combo",
            "guia_doc_ref_input",
            "guia_observaciones_input",
            "guia_dest_doc_input",
            "guia_dest_nombre_input",
            "guia_source_dispatch_input",
            "guia_punto_partida_input",
            "guia_punto_llegada_input",
            "guia_transportista_doc_input",
            "guia_transportista_nombre_input",
            "guia_placa_input",
            "guia_conductor_input",
            "guia_selector_combo",
            "guia_target_branch_combo",
            "guia_detalle_table",
            "guia_total_items_label",
            "guia_total_lineas_label",
            "guia_target_group",
            "guia_child_group",
            "guia_cargar_btn",
            "guia_solicitar_btn",
            "guia_recepcion_btn",
        ]:
            setattr(self, attr, None)
        self.guia_dialog = None
        self.guia_dialog_mode = None
        self.guia_dialog_guide = None

    def _guia_get_filtered_requests(self):
        items = self._guia_load_local_requests()
        if self._guia_is_madre_user():
            selected_code = ""
            try:
                selected_code = str(getattr(self.parent_app, "selected_branch_code", "") or "").strip().upper()
            except Exception:
                selected_code = ""
            if not selected_code:
                return [item for item in items if isinstance(item, dict)]
            return [
                item for item in items
                if isinstance(item, dict)
                and (
                    str(item.get("target_branch_code", "")).strip().upper() == selected_code
                    or str(item.get("source_branch_code", "")).strip().upper() == selected_code
                )
            ]
        child_code = self._guia_get_current_child_branch_code()
        return [
            item for item in items
            if isinstance(item, dict)
            and (
                str(item.get("target_branch_code", "")).strip().upper() == child_code
                or str(item.get("source_branch_code", "")).strip().upper() == child_code
            )
        ]

    def _guia_refresh_history_table(self):
        self._guia_update_history_mode()
        table = getattr(self, "guia_history_table", None)
        if table is None:
            return
        items = self._guia_get_filtered_requests()
        table.setRowCount(0)
        for row_idx, guide in enumerate(items):
            table.insertRow(row_idx)
            fecha = str(guide.get("fecha_emision", "") or "")
            serie = str(guide.get("serie", "") or "")
            numero = str(guide.get("numero", "") or "")
            sucursal = str(guide.get("target_branch_name", "") or guide.get("target_branch_code", "") or "")
            destinatario = str((guide.get("destinatario") or {}).get("nombre", "") or "")
            estado = str(guide.get("estado_solicitud", "") or "")
            unidades = str(
                guide.get("recepcion_total_unidades", guide.get("total_unidades", 0)) or 0
            )
            values = [fecha, f"{serie}-{numero}", sucursal, destinatario, estado, unidades]
            for col, value in enumerate(values):
                table.setItem(row_idx, col, QTableWidgetItem(value))
            table.setCellWidget(row_idx, 6, self._guia_create_history_actions_button(guide))

    def _guia_create_history_actions_button(self, guide):
        button = QToolButton(self)
        button.setAutoRaise(True)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.setCursor(Qt.PointingHandCursor)
        button.setIcon(self._guia_create_kebab_icon())
        button.setIconSize(QtCore.QSize(18, 18))
        button.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 4px;
                background: transparent;
            }
            QToolButton:hover {
                background: #F3F4F6;
            }
        """)

        menu = QMenu(button)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #E5E7EB;
                padding: 6px 0;
            }
            QMenu::item {
                padding: 8px 16px;
            }
            QMenu::item:selected {
                background: #F3F4F6;
            }
        """)
        export_action = menu.addAction("Abrir en navegador")
        export_action.triggered.connect(lambda _checked=False, g=copy.deepcopy(guide): self._guia_open_history_in_browser(g))
        send_inventory_action = menu.addAction("Enviar al inventario")
        send_inventory_action.triggered.connect(
            lambda _checked=False, g=copy.deepcopy(guide): self._guia_send_to_inventory(g)
        )
        button.setMenu(menu)
        return button

    def _guia_create_kebab_icon(self):
        svg_code = """
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="5" r="1.8" fill="#111827"/>
                <circle cx="12" cy="12" r="1.8" fill="#111827"/>
                <circle cx="12" cy="19" r="1.8" fill="#111827"/>
            </svg>
        """
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        renderer = QSvgRenderer(svg_code.encode())
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)

    def _build_guia_rendered_html(self, guide, include_print_button=False):
        import base64
        import io
        import qrcode
        from utils.file_handler import cargar_configuracion_optica, cargar_datos_optica, cargar_logo_optica

        template_html_path = obtener_ruta_recurso("guia.html")
        if not os.path.exists(template_html_path):
            raise FileNotFoundError(f"No se encontró guia.html.\nRuta buscada: {template_html_path}")

        with open(template_html_path, "r", encoding="utf-8", errors="replace") as tpl_file:
            template_html = tpl_file.read()
        if "Ã" in template_html:
            try:
                template_html = template_html.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            except Exception:
                pass

        cfg = cargar_configuracion_optica(self.username) or {}
        company_name = str(cargar_nombre_optica(self.username) or "MI OPTICA").strip().upper()
        company_ruc = str(cargar_ruc(self.username) or "").strip()
        company_address = str(cfg.get("direccion", "") or "").strip()
        company_branch = str(guide.get("source_dispatch_label", "") or cfg.get("direccion_sucursal", "") or "").strip()
        logo_path = cargar_logo_optica(self.username) or str(get_user_file_path(self.username, "logo.png"))

        serie = str(guide.get("serie", "") or "").strip() or "GUIA"
        numero = str(guide.get("numero", "") or "").strip() or "0000"
        destino = str(guide.get("target_branch_name", "") or guide.get("target_branch_code", "") or "").strip()
        destinatario = str((guide.get("destinatario") or {}).get("nombre", "") or destino or "").strip()
        destinatario_doc = str((guide.get("destinatario") or {}).get("documento", "") or "").strip()
        punto_partida = str((guide.get("ruta") or {}).get("punto_partida", "") or guide.get("source_dispatch_label", "") or "").strip()
        punto_llegada = str((guide.get("ruta") or {}).get("punto_llegada", "") or destino).strip()
        nombre_transporte = str((guide.get("transporte") or {}).get("nombre", "") or "").strip()
        placa = str((guide.get("transporte") or {}).get("placa", "") or "").strip()
        conductor = str((guide.get("transporte") or {}).get("conductor", "") or "").strip()
        motivo = str(guide.get("motivo_traslado", "") or "").strip()
        observaciones = str(guide.get("observaciones", "") or "").strip()
        doc_ref = str(guide.get("documento_referencia", "") or "").strip()
        fecha_traslado = str(guide.get("fecha_traslado", "") or guide.get("fecha_emision", "") or "").strip()
        items = guide.get("recepcion_items") or guide.get("items") or []

        def _fit_html_text(text, max_chars):
            value = str(text or "").strip()
            return value[: max_chars - 3] + "..." if len(value) > max_chars and max_chars > 3 else value

        def _html_escape(value):
            return (
                str(value or "")
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        def _split_address_lines(text, first_limit=70, second_limit=70):
            value = str(text or "").strip()
            if not value:
                return "", ""
            if len(value) <= first_limit:
                return value, ""
            first = value[:first_limit].rsplit(" ", 1)[0] or value[:first_limit]
            rest = value[len(first):].strip()
            second = _fit_html_text(rest, second_limit)
            return first, second

        def _build_items_rows_html(items_list):
            rows_html = []
            for idx, item in enumerate(items_list, start=1):
                if not isinstance(item, dict):
                    continue
                codigo_item = _html_escape(item.get("codigo", "") or "")
                descripcion = _html_escape(item.get("descripcion", "") or item.get("nombre", "") or "")
                marca_item = _html_escape(item.get("marca", "") or "")
                precio_unitario = item.get("precio_venta", item.get("precio", item.get("precio_unitario", "")))
                try:
                    precio_unitario = f"{float(precio_unitario or 0):.2f}" if str(precio_unitario).strip() != "" else ""
                except Exception:
                    precio_unitario = _html_escape(precio_unitario)
                cantidad_item = _html_escape(item.get("cantidad", "") or "")
                unidad_item = _html_escape(item.get("unidad", "") or "UND")
                rows_html.append(
                    f"""
                    <tr>
                      <td>{idx}</td>
                      <td>{codigo_item}</td>
                      <td class="desc">{descripcion}</td>
                      <td>{marca_item}</td>
                      <td>{precio_unitario}</td>
                      <td>{cantidad_item}</td>
                      <td>{unidad_item}</td>
                    </tr>
                    """
                )
            if not rows_html:
                rows_html.append('<tr><td colspan="7" style="height:32px;"></td></tr>')
            return "\n".join(rows_html)

        qr_payload = f"{serie}|{numero}|{fecha_traslado}|{destinatario_doc}|{destinatario}|{punto_partida}|{punto_llegada}"
        qr = qrcode.QRCode(border=1, box_size=4)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_b64 = base64.b64encode(qr_buffer.getvalue()).decode("ascii")

        logo_html = ""
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as logo_file:
                    logo_b64 = base64.b64encode(logo_file.read()).decode("ascii")
                logo_html = (
                    f'<img src="data:image/png;base64,{logo_b64}" '
                    'style="width:100%;height:100%;object-fit:cover;border-radius:50%;" alt="Logo">'
                )
            except Exception:
                pass

        fiscal_line_1, fiscal_line_2 = _split_address_lines(company_address)
        sucursal_line_1, sucursal_line_2 = _split_address_lines(company_branch or punto_partida)
        llegada_line_1, llegada_line_2 = _split_address_lines(punto_llegada, 56, 64)
        motives = {
            "Venta": "",
            "Venta sujeta a confirmacion del comprador": "",
            "Compra": "",
            "Traslado entre establecimientos de la misma": "",
            "Importacion": "",
            "Traslado emisor itinerante CP": "",
            "Exportacion": "",
            "Traslado a zona primaria": "",
            "Otros": "",
        }
        checked_map = {
            "venta": "Venta",
            "traslado entre sucursales": "Traslado entre establecimientos de la misma",
            "compra": "Compra",
            "consignacion": "Venta sujeta a confirmacion del comprador",
            "devolucion": "Otros",
            "traslado para transformacion": "Traslado emisor itinerante CP",
            "otros": "Otros",
        }
        label = checked_map.get(motivo.strip().lower(), "Otros" if motivo.strip() else "")
        if label:
            motives[label] = " on"

        total_peso = 0.0
        for item in items:
            try:
                total_peso += float(item.get("peso_ref", 0) or 0)
            except Exception:
                pass

        rendered_html = template_html
        if not include_print_button:
            rendered_html = rendered_html.replace('<button class="print-btn" onclick="window.print()">Descargar PDF</button>', "")

        replacements = {
            "MULTIDISTRIBUCIONES": _html_escape(company_name),
            "20200200200": _html_escape(company_ruc or "00000000000"),
            "N° TS01 - 00000022": f"N° {_html_escape(serie)} - {_html_escape(numero)}",
            "20/09/2024": _html_escape(fecha_traslado or guide.get("fecha_emision", "")),
            "JAYCO SOCIEDAD ANONIMA CERRADA": _html_escape(destinatario or destino),
            "20602640281": _html_escape(destinatario_doc),
            "150141 - AV LOS GERANIOS 330": _html_escape(punto_partida),
            "150140 - AV. CAMINOS DEL INCA NRO. 3140 DPTO. 401 URB.": _html_escape(llegada_line_1),
            "PROLONGACION BENAVIDES - LIMA LIMA SANTIAGO DE SURCO": _html_escape(llegada_line_2),
            "Factura:F001-00000067": _html_escape(doc_ref),
            "85": _html_escape(f"{total_peso:.0f}" if total_peso > 0 else ""),
            "TRANSPORTE PRIVADO": _html_escape(nombre_transporte or "TRANSPORTE PRIVADO"),
        }
        for old, new in replacements.items():
            rendered_html = rendered_html.replace(old, new)

        rendered_html = re.sub(
            r'<div class="logo">.*?</div>',
            (
                f'<div class="logo">{logo_html}</div>'
                if logo_html
                else '<div class="logo" style="background:transparent;border:none;"></div>'
            ),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'Dirección fiscal : .*?<br>\s*Trujillo - La Libertad<br>',
            f'Dirección fiscal : {_html_escape(fiscal_line_1)}<br>\n        {_html_escape(fiscal_line_2)}<br>',
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'Sucursal : .*?<br>\s*Trujillo- La Libertad',
            f'Sucursal : {_html_escape(sucursal_line_1)}<br>\n        {_html_escape(sucursal_line_2)}',
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'<div class="check"><span class="square on"></span>Venta</div>',
            f'<div class="check"><span class="square{motives["Venta"]}"></span>Venta</div>',
            rendered_html,
            count=1,
        )
        for motive_label in [
            "Venta sujeta a confirmacion del comprador",
            "Compra",
            "Traslado entre establecimientos de la misma",
            "Importacion",
            "Traslado emisor itinerante CP",
            "Exportacion",
            "Traslado a zona primaria",
            "Otros",
        ]:
            rendered_html = rendered_html.replace(
                f'<div class="check"><span class="square"></span>{motive_label}</div>',
                f'<div class="check"><span class="square{motives[motive_label]}"></span>{motive_label}</div>',
            )
        rendered_html = re.sub(
            r'<tbody>.*?</tbody>',
            f'<tbody>{_build_items_rows_html(items)}</tbody>',
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'<div class="qr"></div>',
            f'<div class="qr" style="background:none;"><img src="data:image/png;base64,{qr_b64}" style="width:105px;height:105px;display:block;" alt="QR"></div>',
            rendered_html,
            count=1,
        )
        rendered_html = rendered_html.replace(
            '<div><b>Observaciones</b></div>\n        <div><b>Doc. Referencia:</b> Factura:F001-00000067</div>',
            f'<div><b>Observaciones</b></div>\n        <div>{_html_escape(observaciones)}</div>\n        <div><b>Doc. Referencia:</b> {_html_escape(doc_ref)}</div>',
        )
        rendered_html = rendered_html.replace(
            '<b>Placa del vehículo</b>\n        &nbsp;&nbsp;&nbsp;&nbsp;\n        <b>DNI del Conductor:</b>',
            f'<b>Placa del vehículo</b> &nbsp;&nbsp;&nbsp;&nbsp; {_html_escape(placa)} &nbsp;&nbsp;&nbsp;&nbsp; <b>DNI del Conductor:</b> {_html_escape(conductor)}',
        )
        return rendered_html

    def _guia_open_history_in_browser(self, guide):
        if not isinstance(guide, dict):
            QMessageBox.warning(self, "Guia de Remision", "No se encontró la guía para abrir.")
            return
        try:
            import tempfile
            import subprocess

            serie = str(guide.get("serie", "") or "").strip() or "GUIA"
            numero = str(guide.get("numero", "") or "").strip() or "0000"
            rendered_html = self._build_guia_rendered_html(guide, include_print_button=False)
            temp_dir = tempfile.mkdtemp(prefix="viso_guia_view_")
            html_path = os.path.join(temp_dir, f"guia_{serie}_{numero}.html")
            with open(html_path, "w", encoding="utf-8") as temp_html_file:
                temp_html_file.write(rendered_html)

            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ]
            chrome_exe = next((path for path in chrome_paths if os.path.exists(path)), None)
            if chrome_exe:
                subprocess.Popen([chrome_exe, os.path.abspath(html_path), "--new-window"])
            else:
                os.startfile(os.path.abspath(html_path))
        except Exception as e:
            QMessageBox.critical(self, "Guia de Remision", f"No se pudo abrir la guía en el navegador.\n\n{e}")

    def _guia_backup_local_requests_file(self, suffix: str = "backup") -> str:
        path = self._guia_storage_path()
        if not path.exists():
            return ""
        try:
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.with_name(f"{path.stem}.{suffix}_{stamp}{path.suffix}")
            shutil.copy2(str(path), str(backup_path))
            return str(backup_path)
        except Exception:
            return ""

    def _guia_find_inventory_match(self, productos_destino, item):
        if not isinstance(productos_destino, list) or not isinstance(item, dict):
            return None

        codigo = str(item.get("codigo", "") or "").strip()
        descripcion = str(item.get("descripcion", "") or item.get("nombre", "") or "").strip().lower()
        marca = str(item.get("marca", "") or "").strip().lower()

        for producto in productos_destino:
            if not isinstance(producto, dict):
                continue
            codigo_producto = str(producto.get("codigo", "") or "").strip()
            if codigo and codigo_producto and codigo_producto == codigo:
                return producto

        if not descripcion:
            return None

        for producto in productos_destino:
            if not isinstance(producto, dict):
                continue
            nombre_producto = str(producto.get("nombre", "") or "").strip().lower()
            marca_producto = str(producto.get("marca", "") or "").strip().lower()
            if nombre_producto == descripcion and (not marca or not marca_producto or marca_producto == marca):
                return producto
        return None

    def _guia_send_to_inventory(self, guide):
        if not isinstance(guide, dict):
            QMessageBox.warning(self, "Guía de Remisión", "No se encontró la guía seleccionada.")
            return

        guide_id = str(guide.get("id", "") or "").strip()
        if not guide_id:
            QMessageBox.warning(self, "Guía de Remisión", "La guía no tiene identificador válido.")
            return

        estado_actual = str(guide.get("estado_solicitud", "") or "").strip().lower()
        if estado_actual == "en inventario":
            QMessageBox.information(
                self,
                "Guía de Remisión",
                "Esta guía ya fue aplicada al inventario destino. No se volverá a procesar para evitar duplicar stock.",
            )
            return

        target_branch_code = str(guide.get("target_branch_code", "") or "").strip().upper()
        target_branch_name = str(guide.get("target_branch_name", "") or target_branch_code).strip()
        if not target_branch_code:
            QMessageBox.warning(self, "Guía de Remisión", "La guía no tiene una sucursal destino válida.")
            return

        if not self._guia_is_madre_user():
            current_child_code = self._guia_get_current_child_branch_code()
            if not current_child_code or target_branch_code != current_child_code:
                QMessageBox.warning(
                    self,
                    "Guía de Remisión",
                    "Esta guía no pertenece a la sucursal actual. No se modificó ningún inventario.",
                )
                return
        else:
            selected_code = str(getattr(self.parent_app, "selected_branch_code", "") or "").strip().upper()
            if selected_code and target_branch_code != selected_code:
                QMessageBox.warning(
                    self,
                    "Guía de Remisión",
                    "La sucursal seleccionada no coincide con el destino de la guía. No se modificó ningún inventario.",
                )
                return

        items_fuente = guide.get("recepcion_items") or guide.get("items") or []
        if not isinstance(items_fuente, list) or not items_fuente:
            QMessageBox.warning(self, "Guía de Remisión", "La guía no tiene productos para enviar al inventario.")
            return

        serie = str(guide.get("serie", "") or "").strip()
        numero = str(guide.get("numero", "") or "").strip()
        usar_recepcion = isinstance(guide.get("recepcion_items"), list) and bool(guide.get("recepcion_items"))
        confirmacion = QMessageBox.question(
            self,
            "Enviar al inventario",
            (
                f"Se actualizará el inventario de {target_branch_name} con los productos de la guía {serie}-{numero}.\n\n"
                f"Fuente de productos: {'recepción confirmada' if usar_recepcion else 'detalle solicitado'}.\n"
                f"Estado actual: {str(guide.get('estado_solicitud', '') or 'sin estado')}.\n\n"
                "La guía quedará marcada como 'en inventario'.\n"
                "Este paso no se podrá repetir sin riesgo de duplicar stock.\n\n"
                "¿Deseas continuar?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirmacion != QMessageBox.Yes:
            return

        progress = QtWidgets.QProgressDialog("Enviando productos al inventario destino...", None, 0, 0, self)
        progress.setWindowTitle("Guía de Remisión")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QtWidgets.QApplication.processEvents()

        try:
            from utils.api_handler import subir_dataset_dispositivo_nube
            from utils.file_handler import (
                _download_snapshot_payload_for_dataset,
                _extract_list_dataset_from_snapshot,
                clear_branch_runtime_caches,
                save_branch_snapshot_datasets,
                cargar_kardex,
                guardar_kardex,
            )

            usuario_madre = self._guia_get_usuario_madre()
            payload_dest = _download_snapshot_payload_for_dataset(usuario_madre, target_branch_code, "productos")
            productos_destino = _extract_list_dataset_from_snapshot(payload_dest, "productos") if payload_dest else []
            if not isinstance(productos_destino, list):
                productos_destino = []

            # Cargar Kardex de la sucursal destino
            payload_kardex = _download_snapshot_payload_for_dataset(usuario_madre, target_branch_code, "kardex")
            kardex_destino = _extract_list_dataset_from_snapshot(payload_kardex, "kardex") if payload_kardex else []
            if not isinstance(kardex_destino, list):
                kardex_destino = []

            now_iso = datetime.datetime.now().isoformat()
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            inserted = 0
            updated = 0
            total_unidades = 0

            for idx, item in enumerate(items_fuente, start=1):
                if not isinstance(item, dict):
                    continue
                try:
                    cantidad = int(float(item.get("cantidad", 0) or 0))
                except Exception:
                    cantidad = 0
                if cantidad <= 0:
                    continue

                total_unidades += cantidad
                descripcion_item = str(item.get("descripcion", "") or item.get("codigo", "") or "Producto").strip()
                precio_compra_raw = item.get("precio_compra", "")
                precio_venta_raw = item.get("precio_venta", item.get("precio", ""))
                try:
                    precio_compra = float(precio_compra_raw or 0)
                except Exception:
                    precio_compra = 0.0
                try:
                    precio_venta = float(precio_venta_raw or 0)
                except Exception:
                    precio_venta = 0.0

                producto_existente = self._guia_find_inventory_match(productos_destino, item)
                stock_previo = 0
                if producto_existente is not None:
                    try:
                        stock_previo = int(float(producto_existente.get("stock", 0) or 0))
                    except Exception:
                        stock_previo = 0
                    producto_existente["stock"] = stock_previo + cantidad
                    # ... (rest of field updates)
                    if str(producto_existente.get("nombre", "") or "").strip() == "":
                        producto_existente["nombre"] = descripcion_item
                    if str(producto_existente.get("marca", "") or "").strip() == "" and str(item.get("marca", "") or "").strip():
                        producto_existente["marca"] = str(item.get("marca", "") or "").strip()
                    if str(producto_existente.get("codigo", "") or "").strip() == "" and str(item.get("codigo", "") or "").strip():
                        producto_existente["codigo"] = str(item.get("codigo", "") or "").strip()
                    if precio_compra > 0:
                        producto_existente["costo"] = precio_compra
                        producto_existente["precio_compra"] = precio_compra
                    if precio_venta > 0:
                        producto_existente["venta"] = precio_venta
                        producto_existente["precio"] = precio_venta
                        producto_existente["precio_regular"] = precio_venta
                        producto_existente["precio_venta"] = precio_venta
                    if str(item.get("unidad", "") or "").strip():
                        producto_existente["unidad"] = str(item.get("unidad", "") or "").strip()
                    if str(item.get("peso_ref", "") or "").strip():
                        producto_existente["peso_ref"] = str(item.get("peso_ref", "") or "").strip()
                    producto_existente["updated_at"] = now_iso
                    updated += 1
                else:
                    codigo_nuevo = str(item.get("codigo", "") or "").strip() or f"GRI-{guide_id[-6:]}-{idx:02d}"
                    nombre_nuevo = descripcion_item
                    producto_existente = {
                        "codigo": codigo_nuevo,
                        "nombre": nombre_nuevo,
                        "marca": str(item.get("marca", "") or "").strip(),
                        "categoria": "General",
                        "material": "",
                        "colors": [],
                        "talla": "",
                        "tipo_lente": "",
                        "stock": cantidad,
                        "costo": precio_compra,
                        "venta": precio_venta,
                        "precio": precio_venta,
                        "precio_regular": precio_venta,
                        "precio_compra": precio_compra,
                        "precio_venta": precio_venta,
                        "unidad": str(item.get("unidad", "") or "UND").strip() or "UND",
                        "peso_ref": str(item.get("peso_ref", "") or "").strip(),
                        "caracteristicas": {
                            "polarizado": False, "uv": False, "antireflejo": False, "fotocromatico": False, "blue_light": False,
                        },
                        "variantes": {
                            "material": False, "colores": False, "talla": False, "tipo_lente": False,
                        },
                        "created_at": now_iso,
                        "updated_at": now_iso,
                        "image_path": "",
                    }
                    productos_destino.append(producto_existente)
                    inserted += 1

                # Registrar en Kardex
                kardex_destino.append({
                    "fecha": now_str,
                    "tipo": "Entrada (Guía)",
                    "detalle": f"Ingreso por Guía {serie}-{numero}",
                    "producto": producto_existente.get("nombre", "Sin nombre"),
                    "codigo": producto_existente.get("codigo", ""),
                    "cantidad": cantidad,
                    "stock_final": stock_previo + cantidad,
                    "costo_unitario": precio_compra,
                    "usuario": str(self.username or "Sistema"),
                    "sucursal_origen": str(guide.get("branch_name", "Almacén Principal")),
                })

            if total_unidades <= 0:
                QMessageBox.warning(self, "Guía de Remisión", "La guía no tiene cantidades válidas para enviar al inventario.")
                return

            # Subir Productos a la nube
            remote_ok, remote_msg, _remote_data = subir_dataset_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=target_branch_code,
                dataset="productos",
                data=productos_destino,
                operacion="SYNC_ALL",
                registro_id=f"bulk_prod_{target_branch_code}_{guide_id}",
                contenido={"productos": productos_destino},
                updated_at=now_iso,
            )
            if not remote_ok:
                raise RuntimeError(f"Error al subir productos a la nube: {remote_msg}")

            # Subir Kardex a la nube
            k_ok, k_msg, _k_data = subir_dataset_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=target_branch_code,
                dataset="kardex",
                data=kardex_destino,
                operacion="SYNC_ALL",
                registro_id=f"bulk_kardex_{target_branch_code}_{guide_id}",
                contenido={"kardex": kardex_destino},
                updated_at=now_iso,
            )

            # Guardar snapshots locales para la sucursal destino
            try:
                save_branch_snapshot_datasets(self.username, target_branch_code, {
                    "productos": productos_destino,
                    "kardex": kardex_destino
                })
                clear_branch_runtime_caches()
            except Exception:
                pass

            local_items = self._guia_load_local_requests()
            backup_path = self._guia_backup_local_requests_file("before_inventory_apply")
            guide_found = False
            for local_guide in local_items:
                if not isinstance(local_guide, dict):
                    continue
                if str(local_guide.get("id", "") or "").strip() != guide_id:
                    continue
                local_guide["estado_solicitud"] = "en inventario"
                local_guide["inventory_applied_at"] = now_iso
                local_guide["inventory_applied_branch_code"] = target_branch_code
                local_guide["inventory_applied_branch_name"] = target_branch_name
                local_guide["inventory_applied_by"] = str(self.username or "").strip()
                local_guide["inventory_source"] = "recepcion_items" if usar_recepcion else "items"
                local_guide["inventory_products_inserted"] = inserted
                local_guide["inventory_products_updated"] = updated
                local_guide["inventory_units_applied"] = total_unidades
                local_guide["updated_at"] = now_iso
                guide_found = True
                break

            if not guide_found:
                QMessageBox.warning(
                    self,
                    "Guía de Remisión",
                    "Se actualizó el inventario destino, pero no se encontró la guía local para marcar el estado.",
                )
                return

            self._guia_save_local_requests(local_items)

            branch_items = [
                item for item in local_items
                if isinstance(item, dict)
                and str(item.get("target_branch_code", "")).strip().upper() == target_branch_code
            ]
            guides_ok, guides_msg, _guides_resp = subir_dataset_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=target_branch_code,
                dataset="guias_remision",
                data=branch_items,
                operacion="SYNC_ALL",
                registro_id=f"bulk:{target_branch_code}",
                contenido={"guias_remision": branch_items},
                updated_at=now_iso,
            )
            if guides_ok:
                try:
                    save_branch_snapshot_datasets(self.username, target_branch_code, {"guias_remision": branch_items})
                except Exception:
                    pass

            self._guia_refresh_selector()
            self._guia_refresh_history_table()

            mensaje = (
                f"Inventario destino actualizado correctamente.\n\n"
                f"Sucursal: {target_branch_name}\n"
                f"Unidades aplicadas: {total_unidades}\n"
                f"Productos nuevos: {inserted}\n"
                f"Productos actualizados: {updated}\n"
                f"Estado final de la guía: en inventario"
            )
            if backup_path:
                mensaje += f"\nBackup local: {backup_path}"
            if not guides_ok:
                mensaje += f"\n\nAviso: el estado local se guardó, pero la guía no pudo subirse de nuevo a la nube.\nDetalle: {guides_msg}"
            QMessageBox.information(self, "Guía de Remisión", mensaje)
        except Exception as e:
            QMessageBox.critical(self, "Guía de Remisión", f"No se pudo enviar la guía al inventario.\n{e}")
        finally:
            try:
                progress.close()
            except Exception:
                pass

    def _guia_export_history_pdf(self, guide):
        if not isinstance(guide, dict):
            QMessageBox.warning(self, "Guia de Remision", "No se encontró la guía para exportar.")
            return
        serie = str(guide.get("serie", "") or "").strip() or "GUIA"
        numero = str(guide.get("numero", "") or "").strip() or "0000"
        default_name = f"guia_remision_{serie}_{numero}.pdf".replace("/", "_").replace("\\", "_")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar guía en PDF",
            default_name,
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        try:
            import base64
            import io
            import subprocess
            import tempfile
            import qrcode
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
            from utils.file_handler import cargar_configuracion_optica, cargar_logo_optica

            pdf = canvas.Canvas(file_path, pagesize=A4)
            page_w, page_h = A4

            cfg = cargar_configuracion_optica(self.username) or {}
            company_name = str(cargar_nombre_optica(self.username) or "MI OPTICA").strip().upper()
            company_ruc = str(cargar_ruc(self.username) or "").strip()
            company_address = str(cfg.get("direccion", "") or "").strip()
            company_branch = str(guide.get("source_dispatch_label", "") or cfg.get("direccion_sucursal", "") or "").strip()
            logo_path = cargar_logo_optica(self.username) or str(get_user_file_path(self.username, "logo.png"))

            destino = str(guide.get("target_branch_name", "") or guide.get("target_branch_code", "") or "").strip()
            destinatario = str((guide.get("destinatario") or {}).get("nombre", "") or destino or "").strip()
            destinatario_doc = str((guide.get("destinatario") or {}).get("documento", "") or "").strip()
            punto_partida = str((guide.get("ruta") or {}).get("punto_partida", "") or guide.get("source_dispatch_label", "") or "").strip()
            punto_llegada = str((guide.get("ruta") or {}).get("punto_llegada", "") or destino).strip()
            empresa_transporte = str((guide.get("transporte") or {}).get("documento", "") or "").strip()
            nombre_transporte = str((guide.get("transporte") or {}).get("nombre", "") or "").strip()
            placa = str((guide.get("transporte") or {}).get("placa", "") or "").strip()
            conductor = str((guide.get("transporte") or {}).get("conductor", "") or "").strip()
            motivo = str(guide.get("motivo_traslado", "") or "").strip()
            observaciones = str(guide.get("observaciones", "") or "").strip()
            doc_ref = str(guide.get("documento_referencia", "") or "").strip()
            fecha_traslado = str(guide.get("fecha_traslado", "") or guide.get("fecha_emision", "") or "").strip()
            template_html_path = obtener_ruta_recurso("guia.html")

            def _find_chrome_executable():
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
                ]
                for candidate in chrome_paths:
                    if os.path.exists(candidate):
                        return candidate
                return None

            def _fit_html_text(text, max_chars):
                value = str(text or "").strip()
                return value[: max_chars - 3] + "..." if len(value) > max_chars and max_chars > 3 else value

            def _html_escape(value):
                return (
                    str(value or "")
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )

            def _split_address_lines(text, first_limit=70, second_limit=70):
                value = str(text or "").strip()
                if not value:
                    return "", ""
                if len(value) <= first_limit:
                    return value, ""
                first = value[:first_limit].rsplit(" ", 1)[0] or value[:first_limit]
                rest = value[len(first):].strip()
                second = _fit_html_text(rest, second_limit)
                return first, second

            def _build_items_rows_html(items_list):
                rows_html = []
                for idx, item in enumerate(items_list, start=1):
                    if not isinstance(item, dict):
                        continue
                    codigo_item = _html_escape(item.get("codigo", "") or "")
                    descripcion = _html_escape(item.get("descripcion", "") or item.get("nombre", "") or "")
                    cantidad_item = _html_escape(item.get("cantidad", "") or "")
                    unidad_item = _html_escape(item.get("unidad", "") or "UND")
                    rows_html.append(
                        f"""
                        <tr>
                          <td>{idx}</td>
                          <td>{codigo_item}</td>
                          <td class="desc">{descripcion}</td>
                          <td>{cantidad_item}</td>
                          <td>{unidad_item}</td>
                        </tr>
                        """
                    )
                rows_html.append('<tr class="empty-row"><td colspan="5"></td></tr>')
                return "\n".join(rows_html)

            if os.path.exists(template_html_path):
                chrome_exe = _find_chrome_executable()
                if chrome_exe:
                    with open(template_html_path, "r", encoding="utf-8", errors="replace") as tpl_file:
                        template_html = tpl_file.read()

                    if "Ã" in template_html:
                        try:
                            template_html = template_html.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
                        except Exception:
                            pass

                    qr_payload = f"{serie}|{numero}|{fecha_traslado}|{destinatario_doc}|{destinatario}|{punto_partida}|{punto_llegada}"
                    qr = qrcode.QRCode(border=1, box_size=4)
                    qr.add_data(qr_payload)
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color="black", back_color="white")
                    qr_buffer = io.BytesIO()
                    qr_img.save(qr_buffer, format="PNG")
                    qr_b64 = base64.b64encode(qr_buffer.getvalue()).decode("ascii")

                    logo_html = "TU<br>LOGO<br>AQUÍ"
                    if logo_path and os.path.exists(logo_path):
                        try:
                            with open(logo_path, "rb") as logo_file:
                                logo_b64 = base64.b64encode(logo_file.read()).decode("ascii")
                            logo_html = (
                                f'<img src="data:image/png;base64,{logo_b64}" '
                                'style="width:100%;height:100%;object-fit:cover;border-radius:50%;" alt="Logo">'
                            )
                        except Exception:
                            pass

                    fiscal_line_1, fiscal_line_2 = _split_address_lines(company_address)
                    sucursal_line_1, sucursal_line_2 = _split_address_lines(company_branch or punto_partida)
                    llegada_line_1, llegada_line_2 = _split_address_lines(punto_llegada, 56, 64)
                    motives = {
                        "Venta": "",
                        "Venta sujeta a confirmacion del comprador": "",
                        "Compra": "",
                        "Traslado entre establecimientos de la misma": "",
                        "Importacion": "",
                        "Traslado emisor itinerante CP": "",
                        "Exportacion": "",
                        "Traslado a zona primaria": "",
                        "Otros": "",
                    }
                    checked_map = {
                        "venta": "Venta",
                        "traslado entre sucursales": "Traslado entre establecimientos de la misma",
                        "compra": "Compra",
                        "consignacion": "Venta sujeta a confirmacion del comprador",
                        "devolucion": "Otros",
                        "traslado para transformacion": "Traslado emisor itinerante CP",
                        "otros": "Otros",
                    }
                    label = checked_map.get(motivo.strip().lower(), "Otros" if motivo.strip() else "")
                    if label:
                        motives[label] = " on"

                    items = guide.get("recepcion_items") or guide.get("items") or []
                    total_peso = 0.0
                    for item in items:
                        try:
                            total_peso += float(item.get("peso_ref", 0) or 0)
                        except Exception:
                            pass

                    rendered_html = template_html
                    replacements = {
                        '<button class="print-btn" onclick="window.print()">Descargar PDF</button>': "",
                        "MULTIDISTRIBUCIONES": _html_escape(company_name),
                        "20200200200": _html_escape(company_ruc or "00000000000"),
                        "N° TS01 - 00000022": f"N° {_html_escape(serie)} - {_html_escape(numero)}",
                        "20/09/2024": _html_escape(fecha_traslado or guide.get("fecha_emision", "")),
                        "JAYCO SOCIEDAD ANONIMA CERRADA": _html_escape(destinatario or destino),
                        "20602640281": _html_escape(destinatario_doc),
                        "150141 - AV LOS GERANIOS 330": _html_escape(punto_partida),
                        "150140 - AV. CAMINOS DEL INCA NRO. 3140 DPTO. 401 URB.": _html_escape(llegada_line_1),
                        "PROLONGACION BENAVIDES - LIMA LIMA SANTIAGO DE SURCO": _html_escape(llegada_line_2),
                        "Factura:F001-00000067": _html_escape(doc_ref),
                        "85": _html_escape(f"{total_peso:.0f}" if total_peso > 0 else "50"),
                        "TRANSPORTE PRIVADO": _html_escape(nombre_transporte or "TRANSPORTE PRIVADO"),
                        "Documento creado por <b>Viso</b>": "Documento creado por <b>Viso</b>",
                    }
                    for old, new in replacements.items():
                        rendered_html = rendered_html.replace(old, new)

                    rendered_html = re.sub(
                        r'<div class="logo">.*?</div>',
                        f'<div class="logo">{logo_html}</div>',
                        rendered_html,
                        count=1,
                        flags=re.S,
                    )
                    rendered_html = re.sub(
                        r'Dirección fiscal : .*?<br>\s*Trujillo - La Libertad<br>',
                        f'Dirección fiscal : {_html_escape(fiscal_line_1)}<br>\n        {_html_escape(fiscal_line_2)}<br>',
                        rendered_html,
                        count=1,
                        flags=re.S,
                    )
                    rendered_html = re.sub(
                        r'Sucursal : .*?<br>\s*Trujillo- La Libertad',
                        f'Sucursal : {_html_escape(sucursal_line_1)}<br>\n        {_html_escape(sucursal_line_2)}',
                        rendered_html,
                        count=1,
                        flags=re.S,
                    )
                    rendered_html = re.sub(
                        r'<div class="check"><span class="square on"></span>Venta</div>',
                        f'<div class="check"><span class="square{motives["Venta"]}"></span>Venta</div>',
                        rendered_html,
                        count=1,
                    )
                    for motive_label in [
                        "Venta sujeta a confirmacion del comprador",
                        "Compra",
                        "Traslado entre establecimientos de la misma",
                        "Importacion",
                        "Traslado emisor itinerante CP",
                        "Exportacion",
                        "Traslado a zona primaria",
                        "Otros",
                    ]:
                        rendered_html = rendered_html.replace(
                            f'<div class="check"><span class="square"></span>{motive_label}</div>',
                            f'<div class="check"><span class="square{motives[motive_label]}"></span>{motive_label}</div>',
                        )

                    rendered_html = re.sub(
                        r'<tbody>.*?</tbody>',
                        f'<tbody>{_build_items_rows_html(items)}</tbody>',
                        rendered_html,
                        count=1,
                        flags=re.S,
                    )
                    rendered_html = re.sub(
                        r'<div class="qr"></div>',
                        f'<div class="qr" style="background:none;"><img src="data:image/png;base64,{qr_b64}" style="width:105px;height:105px;display:block;" alt="QR"></div>',
                        rendered_html,
                        count=1,
                    )
                    rendered_html = rendered_html.replace(
                        '<div><b>Observaciones</b></div>\n        <div><b>Doc. Referencia:</b> Factura:F001-00000067</div>',
                        f'<div><b>Observaciones</b></div>\n        <div>{_html_escape(observaciones)}</div>\n        <div><b>Doc. Referencia:</b> {_html_escape(doc_ref)}</div>',
                    )
                    rendered_html = rendered_html.replace(
                        '<b>Placa del vehículo</b>\n        &nbsp;&nbsp;&nbsp;&nbsp;\n        <b>DNI del Conductor:</b>',
                        f'<b>Placa del vehículo</b> &nbsp;&nbsp;&nbsp;&nbsp; {_html_escape(placa)} &nbsp;&nbsp;&nbsp;&nbsp; <b>DNI del Conductor:</b> {_html_escape(conductor)}',
                    )

                    with tempfile.TemporaryDirectory(prefix="viso_guia_") as temp_dir:
                        temp_html_path = os.path.join(temp_dir, f"guia_{serie}_{numero}.html")
                        with open(temp_html_path, "w", encoding="utf-8") as temp_html_file:
                            temp_html_file.write(rendered_html)

                        subprocess.run(
                            [
                                chrome_exe,
                                "--headless=new",
                                "--disable-gpu",
                                "--allow-file-access-from-files",
                                "--no-pdf-header-footer",
                                f"--print-to-pdf={os.path.abspath(file_path)}",
                                os.path.abspath(temp_html_path),
                            ],
                            check=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=60,
                        )
                    QMessageBox.information(self, "Guia de Remision", f"PDF generado correctamente.\n\n{file_path}")
                    return

            green = colors.HexColor("#4FA34F")
            border = colors.black
            gray = colors.HexColor("#444444")

            def draw_text(x, y, text, size=9, font="Helvetica", color=colors.black, align="left"):
                pdf.setFillColor(color)
                pdf.setFont(font, size)
                if align == "center":
                    pdf.drawCentredString(x, y, str(text or ""))
                elif align == "right":
                    pdf.drawRightString(x, y, str(text or ""))
                else:
                    pdf.drawString(x, y, str(text or ""))

            def draw_box(x, y_top, w, h, radius=0):
                y = y_top - h
                pdf.setStrokeColor(border)
                pdf.setLineWidth(0.8)
                if radius > 0:
                    pdf.roundRect(x, y, w, h, radius, stroke=1, fill=0)
                else:
                    pdf.rect(x, y, w, h, stroke=1, fill=0)

            def draw_green_box(x, y_top, w, h, radius=2):
                y = y_top - h
                pdf.setStrokeColor(green)
                pdf.setLineWidth(0.8)
                pdf.roundRect(x, y, w, h, radius, stroke=1, fill=0)

            def fit_text(text, max_chars):
                value = str(text or "").strip()
                return value[: max_chars - 3] + "..." if len(value) > max_chars and max_chars > 3 else value

            def draw_checkbox(x, y, label, checked=False):
                pdf.setStrokeColor(border)
                pdf.rect(x, y - 7, 7, 7, stroke=1, fill=0)
                if checked:
                    pdf.setFont("Helvetica-Bold", 8)
                    pdf.drawString(x + 1.2, y - 6.2, "X")
                draw_text(x + 10, y - 5, label, size=8)

            left = 14
            right = page_w - 14
            top = page_h - 16

            draw_box(left + 470, top + 2, 260, 88, radius=10)

            if logo_path and os.path.exists(logo_path):
                try:
                    pdf.drawImage(logo_path, left + 8, top - 52, width=78, height=78, preserveAspectRatio=True, mask='auto')
                except Exception:
                    draw_box(left + 8, top, 78, 78, radius=39)
                    draw_text(left + 47, top - 20, "LOGO", size=12, font="Helvetica-Bold", align="center")
                    draw_text(left + 47, top - 38, "AQUI", size=12, font="Helvetica-Bold", align="center")
            else:
                draw_box(left + 8, top, 78, 78, radius=39)
                draw_text(left + 47, top - 20, "TU", size=12, font="Helvetica-Bold", align="center")
                draw_text(left + 47, top - 38, "LOGO", size=12, font="Helvetica-Bold", align="center")
                draw_text(left + 47, top - 56, "AQUI", size=12, font="Helvetica-Bold", align="center")

            center_x = left + 250
            draw_text(center_x, top - 5, company_name, size=16, font="Helvetica-Bold", align="center")
            draw_text(center_x, top - 20, "EMPRESA SIMPLE SAC", size=10, font="Helvetica-Bold", align="center")
            draw_text(center_x, top - 34, f"Dirección fiscal : {fit_text(company_address, 72)}", size=7.5, align="center")
            draw_text(center_x, top - 46, fit_text(company_address, 72), size=7.5, align="center")
            draw_text(center_x, top - 58, f"Sucursal : {fit_text(company_branch or punto_partida, 74)}", size=7.5, align="center")
            draw_text(center_x, top - 70, fit_text(company_branch or punto_partida, 74), size=7.5, align="center")

            draw_text(left + 600, top - 12, f"R.U.C. {company_ruc or '00000000000'}", size=15, font="Helvetica-Bold", align="center")
            draw_text(left + 600, top - 42, "GUIA DE REMISION", size=13, font="Helvetica-Bold", align="center")
            draw_text(left + 600, top - 58, "ELECTRONICA REMITENTE", size=13, font="Helvetica-Bold", align="center")
            draw_text(left + 600, top - 80, f"N° {serie} - {numero}", size=14, font="Helvetica-Bold", align="center")

            section_y = top - 118
            draw_text(left, section_y, "Fecha de inicio de traslado:", size=9, font="Helvetica-Bold")
            draw_text(left + 135, section_y, fecha_traslado, size=9)

            draw_text(left, section_y - 18, "Destinatario", size=9, font="Helvetica-Bold")
            draw_text(left + 75, section_y - 18, fit_text(destinatario, 42), size=9)
            draw_text(left + 310, section_y - 18, "Punto de partida", size=9, font="Helvetica-Bold")
            draw_text(left + 410, section_y - 18, fit_text(punto_partida, 42), size=9)

            draw_text(left, section_y - 38, "RUC", size=9, font="Helvetica-Bold")
            draw_text(left + 65, section_y - 38, destinatario_doc, size=9)
            draw_text(left + 310, section_y - 38, "Punto de llegada", size=9, font="Helvetica-Bold")
            draw_text(left + 410, section_y - 38, fit_text(punto_llegada, 52), size=9)
            draw_text(left + 410, section_y - 50, fit_text(punto_llegada[48:], 52) if len(punto_llegada) > 48 else "", size=9)

            motives_top = section_y - 64
            draw_text(left, motives_top, "Motivo de traslado", size=9, font="Helvetica-Bold")
            draw_green_box(left, motives_top - 4, right - left - 12, 38)

            motive_norm = motivo.strip().lower()
            motive_labels = [
                ("Venta", 0, 0),
                ("Venta sujeta a confirmacion del comprador", 95, 0),
                ("Compra", 335, 0),
                ("Traslado entre establecimientos de la misma", 420, 0),
                ("Importacion", 0, 16),
                ("Traslado emisor itinerante CP", 95, 16),
                ("Exportacion", 335, 16),
                ("Traslado a zona primaria", 420, 16),
                ("Otros", 0, 32),
            ]
            checked_map = {
                "venta": "Venta",
                "traslado entre sucursales": "Traslado entre establecimientos de la misma",
                "compra": "Compra",
                "consignacion": "Venta sujeta a confirmacion del comprador",
                "devolucion": "Otros",
                "traslado para transformacion": "Traslado emisor itinerante CP",
                "otros": "Otros",
            }
            checked_label = checked_map.get(motive_norm, "Otros" if motive_norm else "")
            for label, dx, dy in motive_labels:
                draw_checkbox(left + 5 + dx, motives_top - 10 - dy, label, checked=(label == checked_label))

            table_top = motives_top - 52
            draw_text(left, table_top, "Datos del bien transportado", size=9, font="Helvetica-Bold")
            table_y_top = table_top - 4
            table_height = 268
            draw_box(left, table_y_top, right - left - 12, table_height)

            col_x = [left, left + 28, left + 88, left + 540, left + 590, left + 638, right - 12]
            for x in col_x[1:-1]:
                pdf.line(x, table_y_top, x, table_y_top - table_height)
            pdf.line(left, table_y_top - 20, right - 12, table_y_top - 20)

            draw_text(left + 13, table_y_top - 14, "N°", size=8, font="Helvetica-Bold", align="center")
            draw_text(left + 58, table_y_top - 14, "CÓDIGO", size=8, font="Helvetica-Bold", align="center")
            draw_text(left + 314, table_y_top - 14, "DESCRIPCIÓN", size=8, font="Helvetica-Bold", align="center")
            draw_text(left + 565, table_y_top - 14, "CANTIDAD", size=8, font="Helvetica-Bold", align="center")
            draw_text(left + 614, table_y_top - 10, "UNIDAD DE", size=7, font="Helvetica-Bold", align="center")
            draw_text(left + 614, table_y_top - 18, "DESPACHO", size=7, font="Helvetica-Bold", align="center")

            items = guide.get("recepcion_items") or guide.get("items") or []
            row_y = table_y_top - 34
            for idx, item in enumerate(items, start=1):
                if not isinstance(item, dict):
                    continue
                codigo_item = fit_text(item.get("codigo", ""), 16)
                descripcion = fit_text(item.get("descripcion", "") or item.get("nombre", ""), 78)
                cantidad_item = str(item.get("cantidad", "") or "").strip()
                unidad_item = fit_text(item.get("unidad", "") or "UND", 12)
                draw_text(left + 13, row_y, str(idx), size=8, align="center")
                draw_text(left + 33, row_y, codigo_item, size=8)
                draw_text(left + 92, row_y, descripcion, size=8)
                draw_text(left + 565, row_y, cantidad_item, size=8, align="center")
                draw_text(left + 614, row_y, unidad_item, size=8, align="center")
                row_y -= 16

            transport_top = table_y_top - table_height - 12
            draw_text(left, transport_top, "UNIDAD DE TRANSPORTE Y CONDUCTOR", size=9, font="Helvetica-Bold")
            draw_green_box(left, transport_top - 6, 370, 20)
            draw_text(left + 4, transport_top - 14, "Placa del vehículo", size=8, font="Helvetica-Bold")
            draw_text(left + 104, transport_top - 14, "DNI del Conductor:", size=8, font="Helvetica-Bold")
            draw_text(left + 110, transport_top - 14, conductor or "", size=8)
            draw_text(left + 4, transport_top - 25, placa or "", size=8)

            draw_green_box(left + 410, transport_top - 6, right - (left + 410) - 12, 20)
            draw_text(left + 414, transport_top - 12, "Modalidad de transporte", size=8, font="Helvetica-Bold")
            draw_text(right - 20, transport_top - 12, "TRANSPORTE PRIVADO", size=8, align="right")
            draw_text(left + 414, transport_top - 24, "Peso Total Aprox. (KGM):", size=8, font="Helvetica-Bold")
            total_peso = 0.0
            for item in items:
                try:
                    total_peso += float(item.get("peso_ref", 0) or 0)
                except Exception:
                    pass
            draw_text(left + 565, transport_top - 24, f"{total_peso:.0f}" if total_peso > 0 else "50", size=8)

            obs_top = transport_top - 32
            draw_green_box(left, obs_top, right - left - 12, 20)
            draw_text(left + 4, obs_top - 11, "Observaciones", size=8, font="Helvetica-Bold")
            draw_text(left + 4, obs_top - 22, fit_text(observaciones, 120), size=8)
            draw_text(left + 4, obs_top - 33, f"Doc. Referencia: {doc_ref}", size=8, font="Helvetica-Bold")

            qr_top = obs_top - 48
            qr_payload = f"{serie}|{numero}|{fecha_traslado}|{destinatario_doc}|{destinatario}|{punto_partida}|{punto_llegada}"
            qr = qrcode.QRCode(border=1, box_size=4)
            qr.add_data(qr_payload)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)
            pdf.drawImage(ImageReader(qr_buffer), left, qr_top - 70, width=72, height=72, mask='auto')

            draw_box(left + 250, qr_top, right - (left + 250) - 12, 72, radius=12)
            pdf.line(left + 270, qr_top - 38, right - 30, qr_top - 38)
            draw_text(left + 455, qr_top - 48, "Conformidad del cliente :", size=8)
            draw_text(left + 455, qr_top - 62, "Nombre:", size=8)
            draw_text(left + 455, qr_top - 76, "DNI:", size=8)

            footer_y = qr_top - 92
            draw_text(left, footer_y, "Representación Impresa de la GUIA DE REMISIÓN", size=8, font="Helvetica-Bold")
            draw_text(left, footer_y - 11, "ELECTRÓNICA", size=8, font="Helvetica-Bold")
            draw_text(left, footer_y - 22, "Autorizado mediante Resolución 0340050007241", size=7.5, font="Helvetica-Bold")
            draw_text(left + 105, footer_y - 40, "GRACIAS POR SU COMPRA!", size=15, font="Helvetica-Bold", align="center")
            draw_text(left + 105, footer_y - 53, "NOTA", size=11, font="Helvetica-Bold", align="center")
            draw_text(left + 105, footer_y - 66, "NO SE ACEPTAN DEVOLUCIONES", size=13, font="Helvetica-Bold", align="center")
            pdf.line(left, footer_y - 80, right - 12, footer_y - 80)
            draw_text(left, footer_y - 90, "LA MERCADERIA VIAJA POR CUENTA Y RIESGO DEL COMPRADOR NO ADMITIMOS RECLAMO POR ROBO O AVERIA", size=6.4)
            draw_text(left, footer_y - 106, "Documento creado por", size=6.5)
            draw_text(left + 110, footer_y - 106, "MiFact", size=8, font="Helvetica-Bold")
            draw_text(left + 155, footer_y - 106, "Proveedor de facturación electrónica - www.mifact.net", size=6.5)

            pdf.save()
            QMessageBox.information(self, "Guia de Remision", f"PDF generado correctamente.\n\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Guia de Remision", f"No se pudo exportar la guía a PDF.\n\n{e}")

    def _guia_load_request_into_form(self, guide):
        if not isinstance(guide, dict):
            return
        self.guia_current_request_id = str(guide.get("id", "") or "").strip()
        self.guia_serie_input.setText(str(guide.get("serie", "") or ""))
        self.guia_numero_input.setText(str(guide.get("numero", "") or ""))
        self.guia_doc_ref_input.setText(str(guide.get("documento_referencia", "") or ""))
        self.guia_observaciones_input.setPlainText(str(guide.get("observaciones", "") or ""))
        self.guia_dest_doc_input.setText(str((guide.get("destinatario") or {}).get("documento", "") or ""))
        self.guia_dest_nombre_input.setText(str((guide.get("destinatario") or {}).get("nombre", "") or ""))
        self.guia_source_dispatch_input.setText(
            str(guide.get("source_dispatch_label", "") or guide.get("source_branch_name", "") or "")
        )
        self.guia_punto_partida_input.setText(str((guide.get("ruta") or {}).get("punto_partida", "") or ""))
        self.guia_punto_llegada_input.setText(str((guide.get("ruta") or {}).get("punto_llegada", "") or ""))
        if hasattr(self, "guia_selector_combo"):
            selected_id = self.guia_current_request_id
            idx_selector = self.guia_selector_combo.findData(selected_id)
            if idx_selector >= 0:
                self.guia_selector_combo.setCurrentIndex(idx_selector)
        target_code = str(guide.get("target_branch_code", "") or "").strip().upper()
        idx_target = self.guia_target_branch_combo.findData(target_code)
        if idx_target >= 0:
            self.guia_target_branch_combo.setCurrentIndex(idx_target)
        fecha_emision = QDate.fromString(str(guide.get("fecha_emision", "") or ""), "dd/MM/yyyy")
        if fecha_emision.isValid():
            self.guia_fecha_emision.setDate(fecha_emision)
        fecha_traslado = QDate.fromString(str(guide.get("fecha_traslado", "") or ""), "dd/MM/yyyy")
        if fecha_traslado.isValid():
            self.guia_fecha_traslado.setDate(fecha_traslado)
        self.guia_transportista_doc_input.setText(str((guide.get("transporte") or {}).get("documento", "") or ""))
        self.guia_transportista_nombre_input.setText(str((guide.get("transporte") or {}).get("nombre", "") or ""))
        self.guia_placa_input.setText(str((guide.get("transporte") or {}).get("placa", "") or ""))
        self.guia_conductor_input.setText(str((guide.get("transporte") or {}).get("conductor", "") or ""))
        motivo = str(guide.get("motivo_traslado", "") or "")
        idx = self.guia_motivo_combo.findText(motivo)
        self.guia_motivo_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.guia_detalle_table.setRowCount(0)
        for item in (guide.get("recepcion_items") or guide.get("items") or []):
            row = self.guia_detalle_table.rowCount()
            self.guia_detalle_table.insertRow(row)
            values = [
                str(item.get("codigo", "") or ""),
                str(item.get("descripcion", "") or ""),
                str(item.get("marca", "") or ""),
                str(item.get("precio_compra", "") or ""),
                str(item.get("precio_venta", item.get("precio", "")) or ""),
                str(item.get("cantidad", "") or ""),
                str(item.get("unidad", "") or "UND"),
                str(item.get("peso_ref", "") or ""),
            ]
            for col, value in enumerate(values):
                self.guia_detalle_table.setItem(row, col, QTableWidgetItem(value))
        if self.guia_detalle_table.rowCount() == 0:
            self._guia_add_detail_row()
        if self._guia_is_current_branch_target(guide):
            self._guia_apply_fixed_destination_for_child()
        self._guia_update_summary()

    def _guia_is_madre_user(self) -> bool:
        parent = getattr(self, "parent_app", None)
        if parent is not None and hasattr(parent, "es_dispositivo_madre"):
            try:
                return bool(parent.es_dispositivo_madre())
            except Exception:
                return False
        return False

    def _guia_is_madre_global_view(self) -> bool:
        if not self._guia_is_madre_user():
            return False
        parent = getattr(self, "parent_app", None)
        branch_code = str(getattr(parent, "selected_branch_code", "") or "").strip().upper()
        return not bool(branch_code)

    def _guia_update_history_mode(self):
        show_placeholder = self._guia_is_madre_global_view()
        placeholder = getattr(self, "guia_hist_global_placeholder", None)
        if placeholder is not None:
            placeholder.setVisible(show_placeholder)
        table = getattr(self, "guia_history_table", None)
        if table is not None:
            table.setVisible(not show_placeholder)
        open_btn = getattr(self, "guia_hist_open_btn", None)
        if open_btn is not None:
            open_btn.setVisible(not show_placeholder)

    def _guia_storage_path(self):
        return get_user_file_path(self.username, "guias_remision.json")

    def _guia_get_usuario_madre(self) -> str:
        try:
            cfg_path = get_user_file_path(self.username, "config_dispositivo.json")
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if isinstance(cfg, dict):
                    madre = str(cfg.get("usuario_madre", "") or "").strip()
                    if madre:
                        return madre
        except Exception:
            pass
        return str(self.username or "").strip()

    def _guia_get_cloud_code(self) -> str:
        usuario_madre = self._guia_get_usuario_madre()
        base = ''.join(ch for ch in str(usuario_madre or "").upper() if ch.isalnum()) or "USER"
        return f"MADRE-{base}"[:80]

    def _guia_get_current_child_branch_label(self) -> str:
        try:
            cfg_path = get_user_file_path(self.username, "config_dispositivo.json")
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if isinstance(cfg, dict):
                    raw_name = (
                        cfg.get("dispositivo_hijo_nombre")
                        or cfg.get("nombre_optica")
                        or cfg.get("sucursal_nombre")
                        or ""
                    )
                    branch_name = str(raw_name or "").strip()
                    if branch_name:
                        return branch_name
        except Exception:
            pass

        child_code = self._guia_get_current_child_branch_code()
        for item in self._guia_load_target_branches_local():
            if not isinstance(item, dict):
                continue
            item_code = str(item.get("codigo_dispositivo", "") or "").strip().upper()
            if item_code != child_code:
                continue
            name = str(item.get("nombre_optica", "") or "").strip()
            city = str(item.get("ciudad", "") or "").strip()
            if name and city:
                return f"{name} - {city}"
            if name:
                return name
        return child_code

    def _guia_apply_fixed_destination_for_child(self):
        if self._guia_is_madre_user():
            return
        destino = self._guia_get_current_child_branch_label()
        widget = getattr(self, "guia_punto_llegada_input", None)
        if widget is not None:
            widget.setText(str(destino or "").strip())
            widget.setReadOnly(True)

    def _guia_merge_local_requests(self, incoming_items):
        current_items = self._guia_load_local_requests()
        merged = {}
        ordered_ids = []

        for row in current_items:
            if not isinstance(row, dict):
                continue
            gid = str(row.get("id", "")).strip()
            if not gid:
                continue
            merged[gid] = row
            ordered_ids.append(gid)

        for row in (incoming_items or []):
            if not isinstance(row, dict):
                continue
            gid = str(row.get("id", "")).strip()
            if not gid:
                continue
            if gid not in merged:
                ordered_ids.append(gid)
            merged[gid] = row

        return [merged[gid] for gid in ordered_ids if gid in merged]

    def _guia_load_local_requests(self):
        path = self._guia_storage_path()
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def _guia_save_local_requests(self, payload_list):
        path = self._guia_storage_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload_list, f, ensure_ascii=False, indent=2)

    def _guia_load_target_branches_local(self):
        local_devices = []
        try:
            path = get_user_file_path(self.username, "dispositivos_hijos.json")
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if not isinstance(item, dict):
                            continue
                        if str(item.get("estado", "activo")).strip().lower() == "bloqueado":
                            continue
                        code = str(item.get("codigo_dispositivo", "")).strip().upper()
                        if not code:
                            continue
                        local_devices.append(item)
        except Exception:
            pass

        usuario_madre = self._guia_get_usuario_madre() or str(self.username or "").strip()
        try:
            from utils.api_handler import listar_dispositivos_hijos_remoto

            ok, remote_devices, _msg = listar_dispositivos_hijos_remoto(usuario_madre)
            if ok and isinstance(remote_devices, list):
                normalized_remote = []
                seen_codes = set()
                for item in remote_devices:
                    if not isinstance(item, dict):
                        continue
                    if str(item.get("estado", "activo")).strip().lower() == "bloqueado":
                        continue
                    code = str(item.get("codigo_dispositivo", "")).strip().upper()
                    if not code or code in seen_codes:
                        continue
                    seen_codes.add(code)
                    normalized_item = dict(item)
                    normalized_item["codigo_dispositivo"] = code
                    normalized_remote.append(normalized_item)

                if normalized_remote:
                    try:
                        path = get_user_file_path(self.username, "dispositivos_hijos.json")
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(normalized_remote, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                    return normalized_remote
        except Exception:
            pass

        return local_devices

    def _guia_refresh_target_branch_selector(self):
        combo = getattr(self, "guia_target_branch_combo", None)
        if combo is None:
            return
        try:
            current_code = str(combo.currentData() or "").strip().upper()
        except RuntimeError:
            self.guia_target_branch_combo = None
            return
        devices = self._guia_load_target_branches_local()
        own_child_code = self._guia_get_current_child_branch_code() if not self._guia_is_madre_user() else ""
        own_child_label = self._guia_get_current_child_branch_label() if own_child_code else ""
        try:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Selecciona una sucursal destino", "")
            added_codes = set()

            # En trabajador, la sucursal propia también debe estar disponible como destino.
            if own_child_code:
                own_label = str(own_child_label or own_child_code).strip()
                if own_label and own_child_code:
                    if own_child_code in own_label:
                        combo.addItem(own_label, own_child_code)
                    else:
                        combo.addItem(f"{own_label} ({own_child_code})", own_child_code)
                    added_codes.add(own_child_code)

            for device in devices:
                code = str(device.get("codigo_dispositivo", "")).strip().upper()
                if not code or code in added_codes:
                    continue
                name = str(device.get("nombre_optica", "Sucursal")).strip() or "Sucursal"
                city = str(device.get("ciudad", "")).strip()
                label = f"{name} ({code})" if not city else f"{name} - {city} ({code})"
                combo.addItem(label, code)
                added_codes.add(code)
            idx = combo.findData(current_code) if current_code else 0
            if idx < 0:
                idx = 1 if own_child_code and combo.count() > 1 else 0
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        except RuntimeError:
            self.guia_target_branch_combo = None

    def _guia_get_current_child_branch_code(self) -> str:
        try:
            cfg_path = get_user_file_path(self.username, "config_dispositivo.json")
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if isinstance(cfg, dict):
                    raw = (
                        cfg.get("codigo_dispositivo_hijo")
                        or cfg.get("codigo_dispositivo_trabajador")
                        or cfg.get("codigo_dispositivo")
                        or ""
                    )
                    code = str(raw or "").strip().upper()
                    if code:
                        return code
        except Exception:
            pass
        return ""

    def _guia_is_current_branch_target(self, guide=None) -> bool:
        if self._guia_is_madre_user():
            return False
        branch_code = self._guia_get_current_child_branch_code()
        ref = guide if isinstance(guide, dict) else getattr(self, "guia_dialog_guide", None)
        target_code = str((ref or {}).get("target_branch_code", "") or "").strip().upper()
        return bool(branch_code and target_code and target_code == branch_code)

    def _guia_is_current_branch_source(self, guide=None) -> bool:
        if self._guia_is_madre_user():
            return False
        branch_code = self._guia_get_current_child_branch_code()
        ref = guide if isinstance(guide, dict) else getattr(self, "guia_dialog_guide", None)
        source_code = str((ref or {}).get("source_branch_code", "") or "").strip().upper()
        return bool(branch_code and source_code and source_code == branch_code)

    def _guia_refresh_selector(self):
        combo = getattr(self, "guia_selector_combo", None)
        if combo is None:
            return
        try:
            current_id = str(combo.currentData() or "").strip()
        except RuntimeError:
            self.guia_selector_combo = None
            return
        items = self._guia_load_local_requests()
        child_code = self._guia_get_current_child_branch_code() if not self._guia_is_madre_user() else ""
        try:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Selecciona una guía", "")
            for item in items:
                if not isinstance(item, dict):
                    continue
                target_code = str(item.get("target_branch_code", "")).strip().upper()
                if child_code and target_code and target_code != child_code:
                    continue
                gid = str(item.get("id", "")).strip()
                serie = str(item.get("serie", "")).strip()
                numero = str(item.get("numero", "")).strip()
                destino = str(item.get("target_branch_name", "") or ((item.get("destinatario") or {}).get("nombre", ""))).strip()
                combo.addItem(f"{serie}-{numero} | {destino}", gid)
            idx = combo.findData(current_id) if current_id else 0
            if idx < 0:
                idx = 0
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        except RuntimeError:
            self.guia_selector_combo = None

    def _guia_apply_role_mode(self):
        is_madre = self._guia_is_madre_user()
        mode = str(getattr(self, "guia_dialog_mode", "") or "").strip().lower()
        guide = getattr(self, "guia_dialog_guide", None)
        worker_new_mode = (not is_madre) and mode == "new"
        worker_receive_mode = (not is_madre) and mode == "existing" and self._guia_is_current_branch_target(guide)
        worker_sent_view_mode = (not is_madre) and mode == "existing" and self._guia_is_current_branch_source(guide)
        read_only_for_child = [
            "guia_serie_input",
            "guia_numero_input",
            "guia_doc_ref_input",
            "guia_dest_doc_input",
            "guia_dest_nombre_input",
            "guia_source_dispatch_input",
            "guia_punto_partida_input",
            "guia_punto_llegada_input",
            "guia_transportista_doc_input",
            "guia_transportista_nombre_input",
            "guia_placa_input",
            "guia_conductor_input",
        ]
        for attr in read_only_for_child:
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setReadOnly((not is_madre) and (not worker_new_mode))
        if hasattr(self, "guia_observaciones_input"):
            self.guia_observaciones_input.setReadOnly((not is_madre) and (not worker_new_mode))
        if hasattr(self, "guia_motivo_combo"):
            self.guia_motivo_combo.setEnabled(is_madre or worker_new_mode)
        if hasattr(self, "guia_fecha_emision"):
            self.guia_fecha_emision.setEnabled(is_madre or worker_new_mode)
        if hasattr(self, "guia_fecha_traslado"):
            self.guia_fecha_traslado.setEnabled(is_madre or worker_new_mode)
        if hasattr(self, "guia_detalle_table"):
            self.guia_detalle_table.setEnabled(True)
        if hasattr(self, "guia_target_group"):
            self.guia_target_group.setVisible(is_madre or worker_new_mode or worker_sent_view_mode)
        if hasattr(self, "guia_child_group"):
            self.guia_child_group.setVisible((not is_madre) and worker_receive_mode)
        if hasattr(self, "guia_solicitar_btn"):
            self.guia_solicitar_btn.setVisible(is_madre or worker_new_mode)
        if hasattr(self, "guia_recepcion_btn"):
            self.guia_recepcion_btn.setVisible((not is_madre) and worker_receive_mode)
        if hasattr(self, "guia_hist_new_btn"):
            self.guia_hist_new_btn.setVisible(True)
        self._guia_refresh_target_branch_selector()
        self._guia_refresh_selector()
        if not is_madre:
            origen = self._guia_get_current_child_branch_label()
            if hasattr(self, "guia_source_dispatch_input") and self.guia_source_dispatch_input is not None:
                self.guia_source_dispatch_input.setText(str(origen or "").strip())
            if hasattr(self, "guia_punto_partida_input") and self.guia_punto_partida_input is not None:
                self.guia_punto_partida_input.setText(str(origen or "").strip())
                self.guia_punto_partida_input.setReadOnly(True)
            if worker_receive_mode:
                self._guia_apply_fixed_destination_for_child()
            self._guia_reload_requests_from_cloud(silent=True)

    def _guia_collect_payload(self):
        existing_guide = getattr(self, "guia_dialog_guide", None)
        existing_guide = existing_guide if isinstance(existing_guide, dict) else {}
        existing_id = str(getattr(self, "guia_current_request_id", "") or existing_guide.get("id", "") or "").strip()
        serie = str(getattr(self, "guia_serie_input", QLineEdit()).text() if hasattr(self, "guia_serie_input") else "").strip().upper()
        numero = str(getattr(self, "guia_numero_input", QLineEdit()).text() if hasattr(self, "guia_numero_input") else "").strip()
        documento_ref = str(getattr(self, "guia_doc_ref_input", QLineEdit()).text() if hasattr(self, "guia_doc_ref_input") else "").strip()
        destinatario_doc = str(getattr(self, "guia_dest_doc_input", QLineEdit()).text() if hasattr(self, "guia_dest_doc_input") else "").strip()
        destinatario_nombre = str(getattr(self, "guia_dest_nombre_input", QLineEdit()).text() if hasattr(self, "guia_dest_nombre_input") else "").strip()
        source_dispatch_label = str(getattr(self, "guia_source_dispatch_input", QLineEdit()).text() if hasattr(self, "guia_source_dispatch_input") else "").strip()
        punto_partida = str(getattr(self, "guia_punto_partida_input", QLineEdit()).text() if hasattr(self, "guia_punto_partida_input") else "").strip()
        punto_llegada = str(getattr(self, "guia_punto_llegada_input", QLineEdit()).text() if hasattr(self, "guia_punto_llegada_input") else "").strip()
        transportista_doc = str(getattr(self, "guia_transportista_doc_input", QLineEdit()).text() if hasattr(self, "guia_transportista_doc_input") else "").strip()
        transportista_nombre = str(getattr(self, "guia_transportista_nombre_input", QLineEdit()).text() if hasattr(self, "guia_transportista_nombre_input") else "").strip()
        placa = str(getattr(self, "guia_placa_input", QLineEdit()).text() if hasattr(self, "guia_placa_input") else "").strip().upper()
        conductor = str(getattr(self, "guia_conductor_input", QLineEdit()).text() if hasattr(self, "guia_conductor_input") else "").strip()
        observaciones = str(self.guia_observaciones_input.toPlainText()).strip() if hasattr(self, "guia_observaciones_input") else ""
        motivo = str(self.guia_motivo_combo.currentText()).strip() if hasattr(self, "guia_motivo_combo") else ""
        fecha_emision = self.guia_fecha_emision.date().toString("dd/MM/yyyy") if hasattr(self, "guia_fecha_emision") else ""
        fecha_traslado = self.guia_fecha_traslado.date().toString("dd/MM/yyyy") if hasattr(self, "guia_fecha_traslado") else ""
        target_branch_code = str(self.guia_target_branch_combo.currentData() or "").strip().upper() if hasattr(self, "guia_target_branch_combo") else ""
        target_branch_name = str(self.guia_target_branch_combo.currentText() or "").strip() if hasattr(self, "guia_target_branch_combo") else ""
        source_branch_code = self._guia_get_cloud_code() if self._guia_is_madre_user() else self._guia_get_current_child_branch_code()
        source_branch_name = str(self._guia_get_current_child_branch_label() if not self._guia_is_madre_user() else (self.username or "")).strip()
        if source_dispatch_label and self._guia_is_madre_user():
            source_branch_name = source_dispatch_label
        if not punto_partida:
            punto_partida = source_dispatch_label

        if not serie or not numero:
            return False, "Debes ingresar serie y número de la guía.", None
        if not source_dispatch_label:
            return False, "Debes indicar desde dónde se envía la guía.", None
        if not destinatario_nombre:
            return False, "Debes ingresar el destinatario.", None
        if not punto_partida or not punto_llegada:
            return False, "Debes ingresar punto de partida y punto de llegada.", None
        if not target_branch_code:
            return False, "Debes seleccionar la sucursal a la que enviarás la guía.", None

        items = []
        table = getattr(self, "guia_detalle_table", None)
        if table is not None:
            for row in range(table.rowCount()):
                codigo = str(table.item(row, 0).text()).strip() if table.item(row, 0) else ""
                descripcion = str(table.item(row, 1).text()).strip() if table.item(row, 1) else ""
                marca = str(table.item(row, 2).text()).strip() if table.item(row, 2) else ""
                precio_compra = str(table.item(row, 3).text()).strip() if table.item(row, 3) else ""
                precio_venta = str(table.item(row, 4).text()).strip() if table.item(row, 4) else ""
                cantidad_raw = str(table.item(row, 5).text()).strip() if table.item(row, 5) else ""
                unidad = str(table.item(row, 6).text()).strip() if table.item(row, 6) else ""
                peso_ref = str(table.item(row, 7).text()).strip() if table.item(row, 7) else ""
                if not codigo and not descripcion:
                    continue
                try:
                    cantidad = int(float(cantidad_raw or "0"))
                except Exception:
                    cantidad = 0
                if cantidad <= 0:
                    return False, f"La cantidad de la fila {row + 1} debe ser mayor a 0.", None
                items.append({
                    "codigo": codigo,
                    "descripcion": descripcion,
                    "marca": marca,
                    "precio": precio_venta,
                    "precio_compra": precio_compra,
                    "precio_venta": precio_venta,
                    "cantidad": cantidad,
                    "unidad": unidad or "UND",
                    "peso_ref": peso_ref,
                })

        payload = {
            "id": existing_id or f"GR-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}",
            "serie": serie,
            "numero": numero,
            "fecha_emision": fecha_emision,
            "fecha_traslado": fecha_traslado,
            "motivo_traslado": motivo,
            "documento_referencia": documento_ref,
            "destinatario": {
                "documento": destinatario_doc,
                "nombre": destinatario_nombre,
            },
            "ruta": {
                "punto_partida": punto_partida,
                "punto_llegada": punto_llegada,
            },
            "transporte": {
                "documento": transportista_doc,
                "nombre": transportista_nombre,
                "placa": placa,
                "conductor": conductor,
            },
            "observaciones": observaciones,
            "source_dispatch_label": source_dispatch_label,
            "source_branch_code": source_branch_code,
            "source_branch_name": source_branch_name,
            "target_branch_code": target_branch_code,
            "target_branch_name": target_branch_name,
            "items": items,
            "total_lineas": len(items),
            "total_unidades": sum(int(i.get("cantidad", 0) or 0) for i in items),
            "estado_solicitud": str(existing_guide.get("estado_solicitud", "") or "solicitada"),
            "created_at": str(existing_guide.get("created_at", "") or datetime.datetime.now().isoformat()),
            "updated_at": datetime.datetime.now().isoformat(),
            "usuario_solicitante": str(self.username or "").strip(),
        }
        return True, "", payload

    def _guia_submit_request(self):
        ok, msg, payload = self._guia_collect_payload()
        if not ok:
            QMessageBox.warning(self, "Guia de Remision", msg)
            return

        try:
            local_items = self._guia_load_local_requests()
            payload_id = str(payload.get("id", "") or "").strip()
            updated = False
            for idx, item in enumerate(local_items):
                if not isinstance(item, dict):
                    continue
                if str(item.get("id", "") or "").strip() != payload_id:
                    continue
                # Mantener datos ya generados por el flujo si existen.
                if item.get("recepcion_items") and not payload.get("recepcion_items"):
                    payload["recepcion_items"] = item.get("recepcion_items")
                if item.get("recepcion_total_lineas") and not payload.get("recepcion_total_lineas"):
                    payload["recepcion_total_lineas"] = item.get("recepcion_total_lineas")
                if item.get("recepcion_total_unidades") and not payload.get("recepcion_total_unidades"):
                    payload["recepcion_total_unidades"] = item.get("recepcion_total_unidades")
                if item.get("recepcion_updated_at") and not payload.get("recepcion_updated_at"):
                    payload["recepcion_updated_at"] = item.get("recepcion_updated_at")
                payload["created_at"] = str(item.get("created_at", "") or payload.get("created_at", ""))
                payload["estado_solicitud"] = str(item.get("estado_solicitud", "") or payload.get("estado_solicitud", "solicitada"))
                local_items[idx] = payload
                updated = True
                break
            if not updated:
                local_items.append(payload)
            self._guia_save_local_requests(local_items)
        except Exception as e:
            QMessageBox.critical(self, "Guia de Remision", f"No se pudo guardar localmente la guía.\n{e}")
            return

        try:
            from utils.api_handler import subir_dataset_dispositivo_nube

            branch_code = str(payload.get("target_branch_code", "") or "").strip().upper()
            branch_label = str(payload.get("target_branch_name", "") or branch_code).strip()
            branch_items = [
                item for item in local_items
                if isinstance(item, dict)
                and str(item.get("target_branch_code", "")).strip().upper() == branch_code
            ]

            self.guia_solicitar_btn.setEnabled(False)
            QtWidgets.QApplication.processEvents()
            remote_ok, remote_msg, _remote_data = subir_dataset_dispositivo_nube(
                usuario_madre=self._guia_get_usuario_madre(),
                codigo_dispositivo=branch_code,
                dataset="guias_remision",
                data=branch_items,
                operacion="SYNC_ALL",
                registro_id=f"bulk:{branch_code}",
                contenido={"guias_remision": branch_items},
                updated_at=datetime.datetime.now().isoformat(),
            )
        except Exception as e:
            remote_ok = False
            remote_msg = str(e)
        finally:
            if hasattr(self, "guia_solicitar_btn"):
                self.guia_solicitar_btn.setEnabled(True)

        if not remote_ok:
            QMessageBox.warning(
                self,
                "Guia de Remision",
                f"La guía se guardó localmente, pero no se pudo subir a la nube.\n\nDetalle: {remote_msg}"
            )
            self._guia_refresh_history_table()
            return

        self._guia_refresh_selector()
        self._guia_refresh_history_table()
        QMessageBox.information(
            self,
            "Guia de Remision",
            f"{'Guía actualizada' if updated else 'Solicitud de guía registrada'} y subida a la nube correctamente.\n\nDestino: {branch_label}"
        )
        if getattr(self, "guia_dialog", None) is not None:
            self.guia_dialog.accept()

    def _guia_reload_requests_from_cloud(self, silent: bool = False):
        try:
            if self._guia_is_madre_user():
                self._guia_refresh_selector()
                self._guia_refresh_history_table()
                if not silent:
                    QMessageBox.information(self, "Guia de Remision", "Historial actualizado.")
                return
            from utils.api_handler import descargar_snapshot_dispositivo_nube

            usuario_madre = self._guia_get_usuario_madre()
            branch_code = self._guia_get_current_child_branch_code() if not self._guia_is_madre_user() else ""
            if not branch_code:
                branch_code = self._guia_get_cloud_code()
            ok, payload, msg = descargar_snapshot_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset="guias_remision",
                include_data=True,
            )
            if not ok:
                if not silent:
                    QMessageBox.warning(self, "Guia de Remision", msg or "No se pudo cargar guías desde la nube.")
                return

            remote_items = []
            if isinstance(payload, dict):
                if isinstance(payload.get("data"), list):
                    remote_items = payload.get("data") or []
                elif isinstance(payload.get("snapshot"), dict):
                    remote_items = payload.get("snapshot", {}).get("guias_remision") or []
                elif isinstance(payload.get("guias_remision"), list):
                    remote_items = payload.get("guias_remision") or []

            if isinstance(remote_items, list):
                merged_items = self._guia_merge_local_requests(remote_items)
                self._guia_save_local_requests(merged_items)
                self._guia_refresh_selector()
                self._guia_refresh_history_table()
                if not silent:
                    QMessageBox.information(self, "Guia de Remision", "Guías cargadas desde la nube.")
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, "Guia de Remision", f"No se pudo cargar guías desde la nube.\n{e}")

    def _guia_on_request_selected(self, _index):
        if self._guia_is_madre_user():
            return
        combo = getattr(self, "guia_selector_combo", None)
        if combo is None:
            return
        selected_id = str(combo.currentData() or "").strip()
        if not selected_id:
            self._guia_clear_form()
            return
        items = self._guia_load_local_requests()
        guide = next((g for g in items if isinstance(g, dict) and str(g.get("id", "")).strip() == selected_id), None)
        if not isinstance(guide, dict):
            return
        self._guia_load_request_into_form(guide)

    def _guia_submit_reception(self):
        if self._guia_is_madre_user():
            QMessageBox.warning(self, "Guia de Remision", "Esta acción es para el dispositivo hijo.")
            return
        selected_id = str(getattr(self, "guia_current_request_id", "") or "").strip()
        if not selected_id and hasattr(self, "guia_selector_combo"):
            selected_id = str(self.guia_selector_combo.currentData() or "").strip()
        if not selected_id:
            QMessageBox.warning(self, "Guia de Remision", "Selecciona una guía recibida.")
            return

        recepcion_items = []
        for row in range(self.guia_detalle_table.rowCount()):
            codigo = str(self.guia_detalle_table.item(row, 0).text()).strip() if self.guia_detalle_table.item(row, 0) else ""
            descripcion = str(self.guia_detalle_table.item(row, 1).text()).strip() if self.guia_detalle_table.item(row, 1) else ""
            marca = str(self.guia_detalle_table.item(row, 2).text()).strip() if self.guia_detalle_table.item(row, 2) else ""
            precio_compra = str(self.guia_detalle_table.item(row, 3).text()).strip() if self.guia_detalle_table.item(row, 3) else ""
            precio_venta = str(self.guia_detalle_table.item(row, 4).text()).strip() if self.guia_detalle_table.item(row, 4) else ""
            cantidad_txt = str(self.guia_detalle_table.item(row, 5).text()).strip() if self.guia_detalle_table.item(row, 5) else ""
            unidad = str(self.guia_detalle_table.item(row, 6).text()).strip() if self.guia_detalle_table.item(row, 6) else ""
            peso_ref = str(self.guia_detalle_table.item(row, 7).text()).strip() if self.guia_detalle_table.item(row, 7) else ""
            if not codigo and not descripcion:
                continue
            try:
                cantidad = int(float(cantidad_txt or "0"))
            except Exception:
                cantidad = 0
            if cantidad <= 0:
                QMessageBox.warning(self, "Guia de Remision", f"La cantidad de la fila {row + 1} debe ser mayor a 0.")
                return
            recepcion_items.append({
                "codigo": codigo,
                "descripcion": descripcion,
                "marca": marca,
                "precio": precio_venta,
                "precio_compra": precio_compra,
                "precio_venta": precio_venta,
                "cantidad": cantidad,
                "unidad": unidad or "UND",
                "peso_ref": peso_ref,
            })
        if not recepcion_items:
            QMessageBox.warning(self, "Guia de Remision", "Debes registrar los productos que llegaron.")
            return

        requests_list = self._guia_load_local_requests()
        updated = False
        for guide in requests_list:
            if not isinstance(guide, dict):
                continue
            if str(guide.get("id", "")).strip() != selected_id:
                continue
            guide["recepcion_items"] = recepcion_items
            guide["recepcion_total_lineas"] = len(recepcion_items)
            guide["recepcion_total_unidades"] = sum(int(i.get("cantidad", 0) or 0) for i in recepcion_items)
            guide["estado_solicitud"] = "productos_recibidos"
            guide["recepcion_updated_at"] = datetime.datetime.now().isoformat()
            updated = True
            break

        if not updated:
            QMessageBox.warning(self, "Guia de Remision", "No se encontró la guía seleccionada.")
            return

        try:
            self._guia_save_local_requests(requests_list)
            from utils.api_handler import subir_dataset_dispositivo_nube
            branch_code = self._guia_get_current_child_branch_code()
            branch_items = [
                item for item in requests_list
                if isinstance(item, dict)
                and str(item.get("target_branch_code", "")).strip().upper() == branch_code
            ]
            remote_ok, remote_msg, _remote_data = subir_dataset_dispositivo_nube(
                usuario_madre=self._guia_get_usuario_madre(),
                codigo_dispositivo=branch_code,
                dataset="guias_remision",
                data=branch_items,
                operacion="SYNC_ALL",
                registro_id=f"bulk:{branch_code}",
                contenido={"guias_remision": branch_items},
                updated_at=datetime.datetime.now().isoformat(),
            )
        except Exception as e:
            remote_ok = False
            remote_msg = str(e)

        if not remote_ok:
            QMessageBox.warning(
                self,
                "Guia de Remision",
                f"La recepción se guardó localmente, pero no se pudo subir a la nube.\n\nDetalle: {remote_msg}"
            )
            self._guia_refresh_history_table()
            return

        self._guia_refresh_selector()
        self._guia_refresh_history_table()
        QMessageBox.information(self, "Guia de Remision", "Productos recibidos registrados y subidos a la nube.")
        if getattr(self, "guia_dialog", None) is not None:
            self.guia_dialog.accept()

    def _guia_add_detail_row(self):
        table = getattr(self, "guia_detalle_table", None)
        if table is None:
            return
        row = table.rowCount()
        table.insertRow(row)
        defaults = ["", "", "", "", "", "1", "UND", ""]
        for col, value in enumerate(defaults):
            table.setItem(row, col, QTableWidgetItem(value))
        self._guia_update_summary()

    def _guia_remove_selected_row(self):
        table = getattr(self, "guia_detalle_table", None)
        if table is None:
            return
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)
        self._guia_update_summary()

    def _guia_update_summary(self, *_args):
        table = getattr(self, "guia_detalle_table", None)
        if table is None:
            return
        total_lineas = table.rowCount()
        total_items = 0
        for row in range(total_lineas):
            item = table.item(row, 5)
            try:
                qty = int(float(str(item.text()).strip())) if item and str(item.text()).strip() else 0
            except Exception:
                qty = 0
            total_items += max(0, qty)
        if hasattr(self, "guia_total_lineas_label"):
            self.guia_total_lineas_label.setText(str(total_lineas))
        if hasattr(self, "guia_total_items_label"):
            self.guia_total_items_label.setText(str(total_items))

    def _guia_clear_form(self):
        self.guia_current_request_id = ""
        for widget in [
            getattr(self, "guia_serie_input", None),
            getattr(self, "guia_numero_input", None),
            getattr(self, "guia_doc_ref_input", None),
            getattr(self, "guia_dest_doc_input", None),
            getattr(self, "guia_dest_nombre_input", None),
            getattr(self, "guia_source_dispatch_input", None),
            getattr(self, "guia_punto_partida_input", None),
            getattr(self, "guia_punto_llegada_input", None),
            getattr(self, "guia_transportista_doc_input", None),
            getattr(self, "guia_transportista_nombre_input", None),
            getattr(self, "guia_placa_input", None),
            getattr(self, "guia_conductor_input", None),
        ]:
            if widget is not None:
                widget.clear()

        if hasattr(self, "guia_motivo_combo"):
            self.guia_motivo_combo.setCurrentIndex(0)
        if hasattr(self, "guia_target_branch_combo"):
            self.guia_target_branch_combo.setCurrentIndex(0)
        if hasattr(self, "guia_selector_combo") and not self._guia_is_madre_user():
            self.guia_selector_combo.setCurrentIndex(0)
        if hasattr(self, "guia_fecha_emision"):
            self.guia_fecha_emision.setDate(QDate.currentDate())
        if hasattr(self, "guia_fecha_traslado"):
            self.guia_fecha_traslado.setDate(QDate.currentDate())
        if hasattr(self, "guia_observaciones_input"):
            self.guia_observaciones_input.clear()
        if hasattr(self, "guia_detalle_table"):
            self.guia_detalle_table.setRowCount(0)
            if self._guia_is_madre_user():
                self._guia_add_detail_row()
            else:
                if str(getattr(self, "guia_dialog_mode", "") or "").strip().lower() == "new":
                    if hasattr(self, "guia_source_dispatch_input") and self.guia_source_dispatch_input is not None:
                        self.guia_source_dispatch_input.setText(str(self._guia_get_current_child_branch_label() or "").strip())
                    if hasattr(self, "guia_punto_partida_input") and self.guia_punto_partida_input is not None:
                        self.guia_punto_partida_input.setText(str(self._guia_get_current_child_branch_label() or "").strip())
                    if hasattr(self, "guia_punto_llegada_input") and self.guia_punto_llegada_input is not None:
                        self.guia_punto_llegada_input.clear()
                else:
                    self._guia_apply_fixed_destination_for_child()
    
    def create_deudas_tab(self):
        """Crea la pestaña de Revisión de Deudas."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setStyleSheet("background: white;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(0)
        
        # Título
        title_layout = QVBoxLayout()
        title = QLabel("Revisión de Deudas")
        title.setStyleSheet("font-size: 18px; color: #333333; font-weight: 600;")
        subtitle = QLabel("Consulta las deudas pendientes de los clientes")
        subtitle.setStyleSheet("font-size: 12px; color: #999999; margin-top:4px; font-weight: 400;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_layout.setSpacing(2)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addWidget(header)
        
        # Separador
        separator = QWidget()
        separator.setStyleSheet("background: #EEEEEE;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        self.deudas_stack = QStackedWidget()
        layout.addWidget(self.deudas_stack)

        # Vista principal de deudas
        deudas_page = QWidget()
        deudas_layout = QVBoxLayout(deudas_page)
        deudas_layout.setContentsMargins(0, 0, 0, 0)
        deudas_layout.setSpacing(0)

        search_widget = QWidget()
        search_widget.setStyleSheet("background: white;")
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(20, 12, 20, 12)
        search_layout.setSpacing(10)

        search_layout.addWidget(QLabel("Buscar:"))
        self._deudas_filter_timer = QTimer(self)
        self._deudas_filter_timer.setSingleShot(True)
        self._deudas_filter_timer.timeout.connect(self.filtrar_deudas)
        self.deudas_dni_input = QLineEdit()
        self.deudas_dni_input.setPlaceholderText("Ej: DNI, contrato o cliente")
        self.deudas_dni_input.setMaximumWidth(200)
        self.deudas_dni_input.textChanged.connect(self._schedule_filtrar_deudas)
        search_layout.addWidget(self.deudas_dni_input)

        search_layout.addStretch()
        deudas_layout.addWidget(search_widget)

        self.deudas_mode_notice = QLabel("")
        self.deudas_mode_notice.setWordWrap(True)
        self.deudas_mode_notice.setStyleSheet(
            "background: #FFF8E1; color: #8A5A00; border: 1px solid #F2D38B; "
            "border-radius: 6px; padding: 10px 12px; margin: 0 20px 12px 20px;"
        )
        self.deudas_mode_notice.hide()
        deudas_layout.addWidget(self.deudas_mode_notice)

        self.deudas_table = QTableWidget()
        self.deudas_table.setColumnCount(8)
        self.deudas_table.setHorizontalHeaderLabels(["DNI", "Cliente", "N° Contrato", "Total", "Adelanto", "Falta Pagar", "Fecha", "Deuda ID"])
        self.deudas_table.setColumnWidth(0, 100)
        self.deudas_table.setColumnWidth(1, 180)
        self.deudas_table.setColumnWidth(2, 100)
        self.deudas_table.setColumnWidth(3, 100)
        self.deudas_table.setColumnWidth(4, 100)
        self.deudas_table.setColumnWidth(5, 120)
        self.deudas_table.setColumnWidth(6, 150)
        self.deudas_table.setColumnWidth(7, 240)
        self.deudas_table.horizontalHeader().setStretchLastSection(False)
        self.deudas_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.deudas_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.deudas_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E0E0;
                background: white;
            }
            QHeaderView::section {
                background: #F5F5F5;
                color: #333333;
                padding: 8px;
                border: none;
                font-weight: 600;
            }
        """)
        deudas_layout.addWidget(self.deudas_table)
        self.deudas_table.cellClicked.connect(self._on_deuda_row_clicked)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 16, 20, 16)
        button_layout.setSpacing(10)
        button_layout.addStretch()

        self.deudas_info_btn = QPushButton("Selecciona una fila para ver detalles de pago")
        self.deudas_info_btn.setMinimumWidth(250)
        self.deudas_info_btn.setMinimumHeight(40)
        self.deudas_info_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 16px;
            }
        """)
        self.deudas_info_btn.setEnabled(False)
        button_layout.addWidget(self.deudas_info_btn)

        self.deudas_refresh_btn = QPushButton("Actualizar")
        self.deudas_refresh_btn.setMinimumWidth(120)
        self.deudas_refresh_btn.setMinimumHeight(40)
        self.deudas_refresh_btn.clicked.connect(self.cargar_deudas)
        button_layout.addWidget(self.deudas_refresh_btn)

        self.deudas_history_btn = QPushButton("Historial de Pagos")
        self.deudas_history_btn.setMinimumWidth(170)
        self.deudas_history_btn.setMinimumHeight(40)
        self.deudas_history_btn.setStyleSheet("""
            QPushButton {
                background: #6D4C41;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #5D4037;
            }
        """)
        self.deudas_history_btn.clicked.connect(self._abrir_historial_pagos_deuda)
        button_layout.addWidget(self.deudas_history_btn)

        self.deudas_rebuild_btn = QPushButton("Subir Todas las Deudas")
        self.deudas_rebuild_btn.setMinimumWidth(190)
        self.deudas_rebuild_btn.setMinimumHeight(40)
        self.deudas_rebuild_btn.setStyleSheet("""
            QPushButton {
                background: #0F766E;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #0B5E58;
            }
        """)
        self.deudas_rebuild_btn.clicked.connect(self._regularizar_y_subir_todas_las_deudas)
        button_layout.addWidget(self.deudas_rebuild_btn)

        if not self._puede_editar_deudas():
            aviso_perm = QLabel("Sin permiso para registrar pagos de deudas (solo lectura).")
            aviso_perm.setStyleSheet("color: #D32F2F; font-weight: 600;")
            button_layout.insertWidget(0, aviso_perm)

        deudas_layout.addLayout(button_layout)
        self.deudas_stack.addWidget(deudas_page)

        # Vista de historial de pagos
        historial_page = QWidget()
        historial_layout = QVBoxLayout(historial_page)
        historial_layout.setContentsMargins(0, 0, 0, 0)
        historial_layout.setSpacing(0)

        historial_header = QWidget()
        historial_header.setStyleSheet("background: white;")
        historial_header_layout = QHBoxLayout(historial_header)
        historial_header_layout.setContentsMargins(20, 16, 20, 16)
        historial_header_layout.setSpacing(0)

        historial_title_layout = QVBoxLayout()
        historial_title = QLabel("Historial de Pagos")
        historial_title.setStyleSheet("font-size: 18px; color: #333333; font-weight: 600;")
        historial_subtitle = QLabel("Pagos de deuda registrados por sucursal")
        historial_subtitle.setStyleSheet("font-size: 12px; color: #999999; margin-top:4px; font-weight: 400;")
        historial_title_layout.addWidget(historial_title)
        historial_title_layout.addWidget(historial_subtitle)
        historial_title_layout.setSpacing(2)
        historial_header_layout.addLayout(historial_title_layout)
        historial_header_layout.addStretch()

        self.historial_back_btn = QPushButton("Volver a Deudas")
        self.historial_back_btn.setMinimumWidth(150)
        self.historial_back_btn.setMinimumHeight(40)
        self.historial_back_btn.clicked.connect(self._volver_a_deudas)
        historial_header_layout.addWidget(self.historial_back_btn)
        historial_layout.addWidget(historial_header)

        historial_sep = QWidget()
        historial_sep.setStyleSheet("background: #EEEEEE;")
        historial_sep.setFixedHeight(1)
        historial_layout.addWidget(historial_sep)

        self.historial_pagos_notice = QLabel("")
        self.historial_pagos_notice.setWordWrap(True)
        self.historial_pagos_notice.setStyleSheet(
            "background: #EEF6FF; color: #23527C; border: 1px solid #BFD9F3; "
            "border-radius: 6px; padding: 10px 12px; margin: 12px 20px 12px 20px;"
        )
        self.historial_pagos_notice.hide()
        historial_layout.addWidget(self.historial_pagos_notice)

        self.historial_pagos_table = QTableWidget()
        self.historial_pagos_table.setColumnCount(10)
        self.historial_pagos_table.setHorizontalHeaderLabels([
            "Fecha", "Accion", "Cliente", "DNI", "Contrato",
            "Monto", "Saldo Final", "Usuario", "Observaciones", "Deuda ID"
        ])
        self.historial_pagos_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.historial_pagos_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.historial_pagos_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.historial_pagos_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E0E0;
                background: white;
            }
            QHeaderView::section {
                background: #F5F5F5;
                color: #333333;
                padding: 8px;
                border: none;
                font-weight: 600;
            }
        """)
        historial_layout.addWidget(self.historial_pagos_table)
        self.historial_pagos_table.cellClicked.connect(self._on_historial_pago_row_clicked)

        historial_button_layout = QHBoxLayout()
        historial_button_layout.setContentsMargins(20, 16, 20, 16)
        historial_button_layout.setSpacing(10)
        historial_button_layout.addStretch()

        self.historial_pagos_refresh_btn = QPushButton("Actualizar Historial")
        self.historial_pagos_refresh_btn.setMinimumWidth(170)
        self.historial_pagos_refresh_btn.setMinimumHeight(40)
        self.historial_pagos_refresh_btn.clicked.connect(self._cargar_historial_pagos_deuda)
        historial_button_layout.addWidget(self.historial_pagos_refresh_btn)

        historial_layout.addLayout(historial_button_layout)
        self.deudas_stack.addWidget(historial_page)
        self.deudas_stack.setCurrentIndex(0)

        # Cargar deudas al iniciar
        self.cargar_deudas()

        return tab

    def _es_ayudante_activo(self, parent_app):
        """Evalúa si el usuario actual es ayudante evitando falsos positivos por tipo."""
        flag = getattr(parent_app, 'is_helper', False)
        if isinstance(flag, bool):
            return flag
        if isinstance(flag, str):
            return flag.strip().lower() in ('1', 'true', 'yes', 'si', 'sí')
        return bool(flag)

    def _tiene_permiso_ventas(self, accion_nueva, accion_legacy):
        """Verifica permiso de ventas con fallback para compatibilidad."""
        parent_app = getattr(self, 'parent_app', None)
        if not parent_app:
            return True

        helper_name = str(getattr(parent_app, 'helper_name', '') or '').strip()
        if (not self._es_ayudante_activo(parent_app)) or (not helper_name):
            return True

        username_jefe = str(getattr(parent_app, 'username', '') or '').strip()
        if not username_jefe:
            return False

        try:
            from utils.helpers_manager import tiene_accion_permitida
            if tiene_accion_permitida(username_jefe, helper_name, 'ventas', accion_nueva):
                return True
            return bool(tiene_accion_permitida(username_jefe, helper_name, 'ventas', accion_legacy))
        except Exception:
            return False

    def _puede_ver_deudas(self):
        """Determina si el usuario actual puede ver la pestaña de deudas."""
        return self._tiene_permiso_ventas('ver_deudas', 'ver')

    def _puede_editar_deudas(self):
        """Determina si el usuario actual puede editar pagos de deudas."""
        return self._tiene_permiso_ventas('editar_deudas', 'editar')

    def _obtener_contexto_deudas(self):
        """Devuelve el contexto actual para la revisión de deudas."""
        try:
            ctx = get_effective_branch_context(self.username) or {}
        except Exception:
            ctx = {}

        branch_code = str((ctx or {}).get('code', '')).strip().upper()
        branch_label = str((ctx or {}).get('label', '')).strip() or branch_code

        # Fallback 1: usar el contexto ya resuelto por la ventana principal.
        if not branch_code:
            try:
                parent = getattr(self, 'parent_app', None)
                parent_code = str(getattr(parent, 'selected_branch_code', '') or '').strip().upper()
                parent_label = str(getattr(parent, 'selected_branch_label', '') or '').strip()
                if parent_code:
                    branch_code = parent_code
                    branch_label = parent_label or parent_code
            except Exception:
                pass

        vista_global = not bool(branch_code)

        has_multiple_branches = False
        try:
            checker = getattr(self.parent_app, "_has_multiple_branches", None)
            if callable(checker):
                has_multiple_branches = bool(checker())
        except Exception:
            has_multiple_branches = False

        requiere_sucursal_explica = bool(vista_global and has_multiple_branches)
        return branch_code, branch_label, vista_global, requiere_sucursal_explica

    def _actualizar_estado_ui_deudas(self):
        """Refleja en la UI si la revisión de deudas está disponible."""
        branch_code, branch_label, vista_global, requiere_sucursal_explica = self._obtener_contexto_deudas()
        puede_editar = self._puede_editar_deudas()

        if hasattr(self, 'deudas_mode_notice'):
            if requiere_sucursal_explica:
                self.deudas_mode_notice.setText(
                    "Selecciona una sucursal para revisar y registrar pagos de deudas. "
                    "Las deudas se gestionan por sucursal y se sincronizan dentro de ese contexto."
                )
                self.deudas_mode_notice.show()
            else:
                self.deudas_mode_notice.hide()

        if hasattr(self, 'deudas_dni_input'):
            self.deudas_dni_input.setEnabled(not requiere_sucursal_explica)
            if requiere_sucursal_explica:
                self.deudas_dni_input.clear()

        if hasattr(self, 'deudas_table'):
            self.deudas_table.setEnabled(not requiere_sucursal_explica)

        if hasattr(self, 'deudas_refresh_btn'):
            self.deudas_refresh_btn.setEnabled(not requiere_sucursal_explica)

        if hasattr(self, 'deudas_history_btn'):
            self.deudas_history_btn.setEnabled(not requiere_sucursal_explica)

        if hasattr(self, 'deudas_rebuild_btn'):
            self.deudas_rebuild_btn.setEnabled((not requiere_sucursal_explica) and puede_editar)

        if hasattr(self, 'deudas_info_btn'):
            self.deudas_info_btn.setText(
                "Selecciona una sucursal para habilitar la revisión de deudas"
                if requiere_sucursal_explica
                else "Selecciona una fila para ver detalles de pago"
            )

        if hasattr(self, 'historial_pagos_refresh_btn'):
            self.historial_pagos_refresh_btn.setEnabled(not requiere_sucursal_explica)

        if hasattr(self, 'historial_back_btn'):
            self.historial_back_btn.setEnabled(True)

        return branch_code, branch_label, vista_global, requiere_sucursal_explica

    def _asegurar_sucursal_para_deudas(self):
        """Bloquea acciones de deuda en vista global."""
        _, _, _, requiere_sucursal_explica = self._actualizar_estado_ui_deudas()
        if requiere_sucursal_explica:
            QMessageBox.information(
                self,
                "Selecciona una sucursal",
                "Revisión de deudas solo está disponible por sucursal. "
                "Selecciona una sucursal para cargar, cobrar y sincronizar deudas correctamente."
            )
            return False
        return True

    def _historial_pagos_deuda_cloud_context(self):
        """Resuelve el contexto cloud de la sucursal activa para historial de pagos."""
        branch_code = ""
        branch_label = ""
        try:
            branch_code, branch_label, _, _ = self._obtener_contexto_deudas()
        except Exception:
            branch_code = ""
            branch_label = ""
        branch_code = str(branch_code or "").strip().upper()
        branch_label = str(branch_label or "").strip()

        usuario_madre = str(self.username or "").strip()
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
                    if not branch_label:
                        branch_label = str(
                            cfg.get("dispositivo_hijo_nombre")
                            or cfg.get("nombre_optica")
                            or cfg.get("sucursal_nombre")
                            or ""
                        ).strip()
        except Exception:
            pass

        return usuario_madre, branch_code, branch_label

    def _abrir_historial_pagos_deuda(self):
        """Muestra la vista de historial de pagos dentro de la misma pestaña."""
        if not self._asegurar_sucursal_para_deudas():
            return
        if hasattr(self, "deudas_stack"):
            self.deudas_stack.setCurrentIndex(1)
        self._cargar_historial_pagos_deuda()

    def _volver_a_deudas(self):
        """Regresa a la vista principal de deudas."""
        if hasattr(self, "deudas_stack"):
            self.deudas_stack.setCurrentIndex(0)

    def _sort_key_historial_pago(self, item):
        """Clave robusta para ordenar el historial de pagos."""
        if not isinstance(item, dict):
            return datetime.datetime.min
        fecha_txt = (
            item.get("fecha_pago")
            or item.get("timestamp_iso")
            or item.get("fecha_registro")
            or item.get("fecha")
            or ""
        )
        dt = self._parsear_fecha(fecha_txt)
        if dt:
            return dt
        try:
            if isinstance(fecha_txt, str) and "T" in fecha_txt:
                return datetime.datetime.fromisoformat(fecha_txt.replace("Z", ""))
        except Exception:
            pass
        return datetime.datetime.min

    def _cargar_historial_pagos_deuda(self):
        """Carga el historial de pagos de deuda directamente desde la nube."""
        if not hasattr(self, "historial_pagos_table"):
            return

        self.historial_pagos_table.setRowCount(0)
        usuario_madre, branch_code, branch_label = self._historial_pagos_deuda_cloud_context()
        if not branch_code:
            self.historial_pagos_notice.setText("Selecciona una sucursal para ver su historial de pagos en la nube.")
            self.historial_pagos_notice.show()
            return

        try:
            from utils.api_handler import descargar_snapshot_dispositivo_nube
            ok, payload, msg = descargar_snapshot_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset="historial_pagos_deuda",
                include_data=True,
            )
            if not ok:
                self.historial_pagos_notice.setText(
                    f"No se pudo cargar el historial desde la nube{f' ({branch_label})' if branch_label else ''}: {msg}"
                )
                self.historial_pagos_notice.show()
                return

            data = []
            if isinstance(payload, dict):
                if isinstance(payload.get("data"), list):
                    data = payload.get("data") or []
                elif isinstance(payload.get("snapshot"), dict):
                    snap = payload.get("snapshot") or {}
                    maybe = snap.get("historial_pagos_deuda")
                    if isinstance(maybe, list):
                        data = maybe
                elif isinstance(payload.get("historial_pagos_deuda"), list):
                    data = payload.get("historial_pagos_deuda") or []
            elif isinstance(payload, list):
                data = payload
            if not isinstance(data, list):
                data = []
        except Exception as e:
            self.historial_pagos_notice.setText(f"No se pudo cargar el historial desde la nube: {e}")
            self.historial_pagos_notice.show()
            return

        self.historial_pagos_notice.hide()
        data = [
            item for item in data
            if isinstance(item, dict)
            and str(item.get("accion", "") or "").strip().lower() != "regresar_a_deudor"
        ]
        data.sort(key=self._sort_key_historial_pago, reverse=True)

        self.historial_pagos_table.setRowCount(len(data))
        for row, item in enumerate(data):
            fecha = str(item.get("fecha_pago", "") or item.get("fecha_registro", "") or item.get("timestamp_iso", "") or item.get("fecha", "") or "").strip()
            accion = str(item.get("accion", "") or "").strip().replace("_", " ").title()
            cliente = str(item.get("paciente_nombre", "") or "").strip()
            dni = str(item.get("paciente_dni", "") or "").strip()
            contrato = str(item.get("contrato_numero", "") or item.get("numero_orden", "") or "").strip()
            monto = float(item.get("monto_pagado", 0) or 0)
            saldo_final = float(item.get("saldo_final", 0) or 0)
            usuario = str(item.get("usuario", "") or "").strip()
            observaciones = str(item.get("observaciones", "") or "").strip()
            deuda_id = str(item.get("deuda_id", "") or "").strip()

            values = [
                fecha,
                accion,
                cliente,
                dni,
                contrato,
                f"S/. {monto:.2f}",
                f"S/. {saldo_final:.2f}",
                usuario,
                observaciones,
                deuda_id,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col in (5, 6):
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 0:
                    cell.setData(Qt.UserRole, item)
                self.historial_pagos_table.setItem(row, col, cell)

        try:
            self.historial_pagos_table.resizeColumnsToContents()
            self.historial_pagos_table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass

    def _on_historial_pago_row_clicked(self, row, col):
        """Abre acciones para un registro del historial de pagos."""
        try:
            if row < 0 or not hasattr(self, "historial_pagos_table"):
                return
            cell = self.historial_pagos_table.item(row, 0)
            if cell is None:
                return
            registro = cell.data(Qt.UserRole) or {}
            if not isinstance(registro, dict):
                return

            menu = QMenu(self)
            act_regresar = menu.addAction("Regresar a deudor")
            menu.addSeparator()
            menu.addAction("Cancelar")
            action = menu.exec_(QtGui.QCursor.pos())
            if action == act_regresar:
                self._revertir_pago_desde_historial(registro)
        except Exception as e:
            QMessageBox.warning(self, "Historial de Pagos", f"No se pudo abrir opciones.\n{e}")

    def _guardar_registro_historial_deuda_en_nube(self, registro):
        """Agrega un registro al historial de pagos de deuda en la nube."""
        try:
            from utils.api_handler import descargar_snapshot_dispositivo_nube, subir_dataset_dispositivo_nube
        except Exception as e:
            print(f"[SYNC] No se pudo importar API para historial: {e}")
            return False

        try:
            usuario_madre, branch_code, _branch_label = self._historial_pagos_deuda_cloud_context()
            if not branch_code:
                return False

            now_iso = datetime.datetime.now().isoformat(timespec="seconds")
            registro = dict(registro or {})
            registro.setdefault("id", uuid.uuid4().hex)
            registro.setdefault("timestamp_iso", now_iso)
            registro.setdefault("fecha_registro", datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

            historial = []
            ok_dl, payload, _msg = descargar_snapshot_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset="historial_pagos_deuda",
                include_data=True,
            )
            if ok_dl and isinstance(payload, dict):
                if isinstance(payload.get("data"), list):
                    historial = payload.get("data") or []
                elif isinstance(payload.get("snapshot"), dict):
                    maybe = (payload.get("snapshot") or {}).get("historial_pagos_deuda")
                    if isinstance(maybe, list):
                        historial = maybe
                elif isinstance(payload.get("historial_pagos_deuda"), list):
                    historial = payload.get("historial_pagos_deuda") or []
            elif ok_dl and isinstance(payload, list):
                historial = payload
            if not isinstance(historial, list):
                historial = []
            historial = [item for item in historial if isinstance(item, dict)]
            historial.append(registro)

            try:
                local_path = get_branch_cache_data_dir(self.username, branch_code) / "historial_pagos_deuda.json"
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(historial, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            ok_up, msg_up, _resp = subir_dataset_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset="historial_pagos_deuda",
                data=historial,
                operacion="SYNC_ALL",
                registro_id=f"bulk_historial_deuda_{branch_code}",
                contenido={"historial_pagos_deuda": historial},
                updated_at=now_iso,
            )
            if not ok_up:
                ok_up2, msg_up2, _resp2 = subir_dataset_dispositivo_nube(
                    usuario_madre=usuario_madre,
                    codigo_dispositivo=branch_code,
                    dataset="historial_pagos_deuda",
                    data=historial,
                    operacion="SYNC_ALL",
                    registro_id=f"bulk_historial_deuda_{branch_code}",
                    contenido={"historial_pagos_deuda": historial},
                    updated_at=now_iso,
                    endpoint_file="upload_device_snapshot_manual.php",
                )
                if ok_up2:
                    ok_up, msg_up = ok_up2, msg_up2

            if not ok_up:
                print(f"[SYNC] No se pudo actualizar historial en nube: {msg_up}")
                return False
            return True
        except Exception as e:
            print(f"[SYNC] Error al guardar historial en nube: {e}")
            return False

    def _reemplazar_historial_pagos_deuda_en_nube(self, historial):
        """Reemplaza por completo el historial de pagos de deuda en la nube."""
        try:
            from utils.api_handler import subir_dataset_dispositivo_nube
        except Exception as e:
            print(f"[SYNC] No se pudo importar API para historial: {e}")
            return False

        try:
            usuario_madre, branch_code, _branch_label = self._historial_pagos_deuda_cloud_context()
            if not branch_code:
                return False

            now_iso = datetime.datetime.now().isoformat(timespec="seconds")
            historial = [item for item in (historial or []) if isinstance(item, dict)]

            try:
                local_path = get_branch_cache_data_dir(self.username, branch_code) / "historial_pagos_deuda.json"
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(historial, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            ok_up, msg_up, _resp = subir_dataset_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset="historial_pagos_deuda",
                data=historial,
                operacion="SYNC_ALL",
                registro_id=f"bulk_historial_deuda_{branch_code}",
                contenido={"historial_pagos_deuda": historial},
                updated_at=now_iso,
            )
            if not ok_up:
                ok_up2, msg_up2, _resp2 = subir_dataset_dispositivo_nube(
                    usuario_madre=usuario_madre,
                    codigo_dispositivo=branch_code,
                    dataset="historial_pagos_deuda",
                    data=historial,
                    operacion="SYNC_ALL",
                    registro_id=f"bulk_historial_deuda_{branch_code}",
                    contenido={"historial_pagos_deuda": historial},
                    updated_at=now_iso,
                    endpoint_file="upload_device_snapshot_manual.php",
                )
                if ok_up2:
                    ok_up, msg_up = ok_up2, msg_up2

            if not ok_up:
                print(f"[SYNC] No se pudo reemplazar historial en nube: {msg_up}")
                return False
            return True
        except Exception as e:
            print(f"[SYNC] Error reemplazando historial en nube: {e}")
            return False

    def _revertir_pago_desde_historial(self, registro_historial):
        """Revierte un pago del historial eliminando sus registros en nube."""
        try:
            if not self._asegurar_sucursal_para_deudas():
                return

            registro_historial = dict(registro_historial or {})
            tipo_norm = self._normalizar_tipo_deuda(registro_historial.get("tipo"))
            if tipo_norm not in ("", "venta", "graduacion"):
                QMessageBox.warning(self, "Historial de Pagos", "Ese tipo de registro no admite reversión.")
                return

            deuda_id = self._normalizar_deuda_id(registro_historial.get("deuda_id"))
            dni = str(registro_historial.get("paciente_dni", "") or "").strip()
            nombre = str(registro_historial.get("paciente_nombre", "") or "").strip()
            contrato = str(registro_historial.get("contrato_numero", "") or registro_historial.get("numero_orden", "") or "").strip()
            accion_original = str(registro_historial.get("accion", "") or "").strip()
            registro_id = str(registro_historial.get("id", "") or "").strip()
            usuario_madre, branch_code, branch_label = self._historial_pagos_deuda_cloud_context()

            historial_cloud = []
            try:
                from utils.api_handler import descargar_snapshot_dispositivo_nube
                ok_hist, payload_hist, _msg_hist = descargar_snapshot_dispositivo_nube(
                    usuario_madre=usuario_madre,
                    codigo_dispositivo=branch_code,
                    dataset="historial_pagos_deuda",
                    include_data=True,
                )
                if ok_hist and isinstance(payload_hist, dict):
                    if isinstance(payload_hist.get("data"), list):
                        historial_cloud = payload_hist.get("data") or []
                    elif isinstance(payload_hist.get("snapshot"), dict):
                        maybe_hist = (payload_hist.get("snapshot") or {}).get("historial_pagos_deuda")
                        if isinstance(maybe_hist, list):
                            historial_cloud = maybe_hist
                    elif isinstance(payload_hist.get("historial_pagos_deuda"), list):
                        historial_cloud = payload_hist.get("historial_pagos_deuda") or []
            except Exception:
                historial_cloud = []

            def _es_registro_relacionado(item):
                if not isinstance(item, dict):
                    return False
                if str(item.get("accion", "") or "").strip().lower() == "regresar_a_deudor":
                    return False
                item_id = str(item.get("id", "") or "").strip()
                if registro_id and item_id and item_id == registro_id:
                    return True

                # Fallback estricto si el id no quedó guardado en el historial visible.
                item_fecha = str(item.get("fecha_registro", "") or item.get("timestamp_iso", "") or item.get("fecha", "") or "").strip()
                reg_fecha = str(registro_historial.get("fecha_registro", "") or registro_historial.get("timestamp_iso", "") or registro_historial.get("fecha", "") or "").strip()
                item_monto = float(item.get("monto_pagado", 0) or 0)
                reg_monto = float(registro_historial.get("monto_pagado", 0) or 0)
                if registro_id:
                    return False
                if deuda_id and self._normalizar_deuda_id(item.get("deuda_id")) != deuda_id:
                    return False
                if dni and str(item.get("paciente_dni", "") or "").strip() != dni:
                    return False
                if contrato and str(item.get("contrato_numero", "") or item.get("numero_orden", "") or "").strip() != contrato:
                    return False
                if tipo_norm and self._normalizar_tipo_deuda(item.get("tipo")) not in ("", tipo_norm):
                    return False
                return self._fechas_equivalentes(item_fecha, reg_fecha) and abs(item_monto - reg_monto) <= 0.01

            def _es_registro_fallback_exacto(item):
                if not isinstance(item, dict):
                    return False
                if str(item.get("accion", "") or "").strip().lower() == "regresar_a_deudor":
                    return False
                if deuda_id and self._normalizar_deuda_id(item.get("deuda_id")) != deuda_id:
                    return False
                if dni and str(item.get("paciente_dni", "") or "").strip() != dni:
                    return False
                if contrato and str(item.get("contrato_numero", "") or item.get("numero_orden", "") or "").strip() != contrato:
                    return False
                if tipo_norm and self._normalizar_tipo_deuda(item.get("tipo")) not in ("", tipo_norm):
                    return False
                item_fecha = str(item.get("fecha_registro", "") or item.get("timestamp_iso", "") or item.get("fecha", "") or "").strip()
                reg_fecha = str(registro_historial.get("fecha_registro", "") or registro_historial.get("timestamp_iso", "") or registro_historial.get("fecha", "") or "").strip()
                item_monto = float(item.get("monto_pagado", 0) or 0)
                reg_monto = float(registro_historial.get("monto_pagado", 0) or 0)
                return self._fechas_equivalentes(item_fecha, reg_fecha) and abs(item_monto - reg_monto) <= 0.01

            relacionados = [registro_historial]
            monto_revertir = float(registro_historial.get("monto_pagado", 0) or 0)
            if monto_revertir <= 0.0:
                QMessageBox.warning(self, "Historial de Pagos", "No se encontró un monto válido para revertir.")
                return

            confirm = QMessageBox.question(
                self,
                "Regresar a deudor",
                (
                    f"Se eliminará 1 registro del historial.\n"
                    f"Total a revertir: S/. {monto_revertir:.2f}\n\n"
                    f"Cliente: {nombre or 'N/D'}\n"
                    f"DNI: {dni or 'N/D'}\n"
                    f"Contrato: {contrato or 'N/D'}\n\n"
                    "La deuda volverá a quedar activa, la caja se ajustará y el historial se limpiará en la nube."
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

            encontrada = False

            if tipo_norm in ("", "venta"):
                ventas = cargar_ventas(self.username)
                for venta in ventas:
                    if self._coincide_venta_deuda(
                        venta,
                        dni,
                        registro_historial.get("fecha"),
                        registro_historial.get("id"),
                        registro_historial.get("total"),
                        deuda_id
                    ):
                        total = float(venta.get("total", 0) or 0)
                        monto_actual = float(venta.get("monto_adelanto", venta.get("monto_pagado", 0)) or 0)
                        nuevo_pagado = max(0.0, monto_actual - monto_revertir)
                        venta["monto_adelanto"] = nuevo_pagado
                        venta["monto_pagado"] = nuevo_pagado
                        venta["monto_faltante"] = max(0.0, total - nuevo_pagado) if total > 0 else max(0.0, monto_revertir)
                        venta["es_pago_parcial"] = nuevo_pagado > 0.05 and venta["monto_faltante"] > 0.05
                        venta["es_pago_partes"] = venta["es_pago_parcial"]
                        guardar_ventas(self.username, ventas)
                        encontrada = True
                        break

                if (not encontrada) and dni:
                    candidatos = []
                    for v in ventas:
                        if str(v.get("paciente_dni", "")).strip() != dni:
                            continue
                        total_v = float(v.get("total", 0) or 0)
                        pagado_v = float(v.get("monto_pagado", v.get("monto_adelanto", total_v)) or 0)
                        faltante_v = float(v.get("monto_faltante", max(0, total_v - pagado_v)) or 0)
                        if faltante_v <= 0.05 and total_v > 0:
                            candidatos.append(v)
                    if candidatos:
                        venta = candidatos[0]
                        total = float(venta.get("total", 0) or 0)
                        monto_actual = float(venta.get("monto_adelanto", venta.get("monto_pagado", 0)) or 0)
                        nuevo_pagado = max(0.0, monto_actual - monto_revertir)
                        venta["monto_adelanto"] = nuevo_pagado
                        venta["monto_pagado"] = nuevo_pagado
                        venta["monto_faltante"] = max(0.0, total - nuevo_pagado) if total > 0 else max(0.0, monto_revertir)
                        venta["es_pago_parcial"] = nuevo_pagado > 0.05 and venta["monto_faltante"] > 0.05
                        venta["es_pago_partes"] = venta["es_pago_parcial"]
                        guardar_ventas(self.username, ventas)
                        encontrada = True

            if tipo_norm in ("", "graduacion"):
                pacientes = cargar_pacientes(self.username)
                for paciente in pacientes:
                    if str(paciente.get("dni", "")).strip() != dni:
                        continue
                    historial = paciente.get("historial_graduaciones", []) or []
                    for grad in historial:
                        grad_deuda_id = self._normalizar_deuda_id(grad.get("deuda_id"))
                        if deuda_id:
                            coincide = bool(grad_deuda_id and grad_deuda_id == deuda_id)
                        else:
                            coincide = bool(
                                self._fechas_equivalentes(grad.get("fecha"), registro_historial.get("fecha"))
                                or str(grad.get("contrato_numero", "") or "").strip() == contrato
                            )
                        if not coincide:
                            continue

                        pagos = grad.get("pagos_parciales", [])
                        if not isinstance(pagos, list):
                            pagos = []
                        pagos_filtrados = []
                        eliminado = False
                        for pago in pagos:
                            if not isinstance(pago, dict):
                                pagos_filtrados.append(pago)
                                continue
                            monto_pago = float(pago.get("monto", 0) or 0)
                            if (not eliminado) and abs(monto_pago - monto_revertir) <= 0.01:
                                eliminado = True
                                continue
                            pagos_filtrados.append(pago)

                        if not eliminado and pagos_filtrados:
                            pagos_filtrados.pop()

                        grad["pagos_parciales"] = pagos_filtrados
                        total_grad, monto_pagado_grad, falta_grad = self._resumen_pago_graduacion(grad)
                        grad["monto_adelanto"] = monto_pagado_grad
                        grad["es_pago_parcial"] = falta_grad > 0.05
                        guardar_pacientes(self.username, pacientes)
                        encontrada = True
                        break
                    if encontrada:
                        break

            if not encontrada:
                QMessageBox.warning(self, "Historial de Pagos", "No se encontró la deuda para revertir.")
                return

            caja_anulada = False
            item = registro_historial
            fecha_caja = str(item.get("fecha_pago", "") or item.get("fecha_registro", "") or item.get("timestamp_iso", "") or item.get("fecha", "") or "").strip()
            if fecha_caja and " " in fecha_caja:
                fecha_caja = fecha_caja.split(" ", 1)[0].strip()
            item_tipo = self._normalizar_tipo_deuda(item.get("tipo"))
            item_nombre = str(item.get("paciente_nombre", "") or nombre).strip()
            item_contrato = str(item.get("contrato_numero", "") or item.get("numero_orden", "") or contrato).strip()
            item_monto = float(item.get("monto_pagado", 0) or 0)
            conceptos_caja = []
            if item_tipo in ("", "venta"):
                conceptos_caja.append(f"Cobro Deuda Venta {item_contrato} - {item_nombre}")
                conceptos_caja.append(f"Cobro Deuda Venta (Fallback) {item_contrato} - {item_nombre}")
            if item_tipo in ("", "graduacion"):
                conceptos_caja.append(f"Cobro Deuda Contrato {item_contrato} - {item_nombre}")
            for concepto in conceptos_caja:
                if self._anular_ingreso_caja_automatico(concepto, item_monto, fecha_caja=fecha_caja):
                    caja_anulada = True
                    break

            historial_restante = []
            eliminado_por_id = False
            for item in historial_cloud:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id", "") or "").strip()
                if registro_id and item_id and item_id == registro_id:
                    eliminado_por_id = True
                    continue
                if (not registro_id) and _es_registro_relacionado(item):
                    continue

                historial_restante.append(item)

            if registro_id and not eliminado_por_id:
                historial_restante = [
                    item for item in historial_cloud
                    if not _es_registro_fallback_exacto(item)
                ]

            if self._reemplazar_historial_pagos_deuda_en_nube(historial_restante):
                self._cargar_historial_pagos_deuda()
                self.cargar_deudas()
        except Exception as e:
            QMessageBox.critical(self, "Historial de Pagos", f"No se pudo revertir el pago: {e}")

    def _sort_key_fecha_deuda(self, deuda):
        """Clave de ordenamiento robusta para deudas."""
        fecha_txt = ''
        if isinstance(deuda, dict):
            fecha_txt = deuda.get('fecha', '') or deuda.get('fecha_graduacion', '')
        return self._parsear_fecha(fecha_txt) or datetime.datetime.min

    def _resumen_items_deuda(self, items):
        partes = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            nombre = str(item.get('producto') or item.get('nombre') or '').strip()
            if not nombre:
                continue
            try:
                cantidad = int(float(item.get('cantidad', 1) or 1))
            except (TypeError, ValueError):
                cantidad = 1
            partes.append(f"{nombre} (x{cantidad})" if cantidad > 1 else nombre)
        return ", ".join(partes)

    def _sort_key_fecha_venta(self, venta):
        """Clave de ordenamiento robusta para ventas."""
        fecha_txt = ''
        if isinstance(venta, dict):
            fecha_txt = venta.get('fecha', '')
        return self._parsear_fecha(fecha_txt) or datetime.datetime.min

    def _regularizar_y_subir_todas_las_deudas(self):
        """Reconstruye deudas activas en ventas/graduaciones y fuerza su guardado/sync."""
        try:
            if not self._asegurar_sucursal_para_deudas():
                return
            if not self._puede_editar_deudas():
                QMessageBox.warning(
                    self,
                    "Permiso denegado",
                    "No tienes permiso para regularizar o subir deudas."
                )
                return

            from utils.file_handler import _queue_sync_all_dataset_bg, _resolve_branch_code_for_sync

            ventas = cargar_ventas(self.username)
            try:
                pacientes = cargar_pacientes(self.username)
            except Exception:
                pacientes = []

            ids_existentes = self._colectar_ids_deuda_existentes(ventas, pacientes)
            ventas_actualizadas = 0
            grads_actualizadas = 0
            ventas_deuda_activas = 0
            grads_deuda_activas = 0
            ventas_infladas_corregidas = 0
            grads_infladas_corregidas = 0

            graduaciones_por_deuda = {}
            graduaciones_por_venta = {}
            graduaciones_por_dni_fecha = {}
            for paciente in (pacientes or []):
                if not isinstance(paciente, dict):
                    continue
                paciente_dni = str(paciente.get('dni', '') or '').strip()
                for grad in (paciente.get('historial_graduaciones', []) or []):
                    if not isinstance(grad, dict):
                        continue
                    deuda_id = self._normalizar_deuda_id(grad.get('deuda_id'))
                    venta_id = str(grad.get('venta_relacionada_id', '') or '').strip()
                    fecha_grad_dt = self._parsear_fecha(grad.get('fecha', ''))
                    fecha_grad_key = fecha_grad_dt.date().isoformat() if fecha_grad_dt else str(grad.get('fecha', '') or '').strip()
                    if deuda_id:
                        graduaciones_por_deuda[deuda_id] = grad
                    if venta_id:
                        graduaciones_por_venta[venta_id] = grad
                    if paciente_dni and fecha_grad_key:
                        graduaciones_por_dni_fecha.setdefault((paciente_dni, fecha_grad_key), []).append(grad)

            for venta in (ventas or []):
                if not isinstance(venta, dict):
                    continue

                changed = False
                total = self._to_float_safe(venta.get('total', 0), 0.0)
                is_grad_sale = (
                    str(venta.get('origen', '') or '').strip().lower() == 'graduacion'
                    or str(venta.get('tipo_venta', '') or '').strip().lower() == 'graduacion'
                )

                linked_grad = None
                venta_deuda_id = self._normalizar_deuda_id(venta.get('deuda_id'))
                venta_id = str(venta.get('id', '') or '').strip()
                if venta_deuda_id:
                    linked_grad = graduaciones_por_deuda.get(venta_deuda_id)
                if linked_grad is None and venta_id:
                    linked_grad = graduaciones_por_venta.get(venta_id)
                if linked_grad is None and is_grad_sale:
                    venta_dni = str(venta.get('paciente_dni', '') or venta.get('dni', '') or '').strip()
                    fecha_venta_dt = self._parsear_fecha(venta.get('fecha', ''))
                    fecha_venta_key = fecha_venta_dt.date().isoformat() if fecha_venta_dt else str(venta.get('fecha', '') or '').strip()
                    candidatos = graduaciones_por_dni_fecha.get((venta_dni, fecha_venta_key), []) if venta_dni and fecha_venta_key else []
                    if len(candidatos) == 1:
                        linked_grad = candidatos[0]
                    elif candidatos:
                        linked_grad = min(
                            candidatos,
                            key=lambda g: abs(self._resumen_pago_graduacion(g)[0] - total)
                        )

                if is_grad_sale:
                    total_canonico = 0.0
                    if isinstance(linked_grad, dict):
                        total_canonico, _monto_pagado_ref, _faltante_ref = self._resumen_pago_graduacion(linked_grad)
                    if total_canonico <= 0.01:
                        items_total = 0.0
                        for sale_item in venta.get('items', []) or []:
                            if not isinstance(sale_item, dict):
                                continue
                            cantidad = self._to_float_safe(sale_item.get('cantidad', 1), 1.0)
                            precio = self._to_float_safe(
                                sale_item.get('precio_unitario', sale_item.get('precio', 0)),
                                0.0
                            )
                            items_total += self._to_float_safe(
                                sale_item.get('subtotal', sale_item.get('total', precio * cantidad)),
                                0.0
                            )
                        total_canonico = items_total

                    if total_canonico > 0.01 and abs(total - total_canonico) > 0.05:
                        if total > total_canonico:
                            ventas_infladas_corregidas += 1
                        total = total_canonico
                        venta['total'] = total
                        venta['subtotal'] = round(total / 1.18, 2) if total > 0 else 0.0
                        venta['igv'] = round(total - float(venta.get('subtotal', 0) or 0), 2)
                        venta['monto_total_venta'] = total
                        changed = True

                monto_pagado = self._to_float_safe(venta.get('monto_pagado', 0), 0.0)
                monto_adelanto = self._to_float_safe(venta.get('monto_adelanto', monto_pagado), monto_pagado)
                pagado = max(monto_pagado, monto_adelanto)
                if pagado > total and total > 0:
                    pagado = total
                faltante = max(0.0, total - pagado)
                deuda_activa = faltante > 0.05

                if deuda_activa:
                    ventas_deuda_activas += 1

                if deuda_activa:
                    if not venta.get('es_pago_partes'):
                        venta['es_pago_partes'] = True
                        changed = True
                    if not venta.get('es_pago_parcial'):
                        venta['es_pago_parcial'] = True
                        changed = True
                    if abs(self._to_float_safe(venta.get('monto_adelanto', 0), 0.0) - pagado) > 0.01:
                        venta['monto_adelanto'] = pagado
                        changed = True
                    if abs(self._to_float_safe(venta.get('monto_pagado', 0), 0.0) - pagado) > 0.01:
                        venta['monto_pagado'] = pagado
                        changed = True
                    if abs(self._to_float_safe(venta.get('monto_faltante', 0), 0.0) - faltante) > 0.01:
                        venta['monto_faltante'] = faltante
                        changed = True
                    deuda_id = self._normalizar_deuda_id(venta.get('deuda_id'))
                    if not deuda_id:
                        venta['deuda_id'] = self._generar_deuda_id_unico(ids_existentes)
                        changed = True
                else:
                    if venta.get('es_pago_partes') or venta.get('es_pago_parcial'):
                        venta['es_pago_partes'] = False
                        venta['es_pago_parcial'] = False
                        changed = True
                    if abs(self._to_float_safe(venta.get('monto_faltante', 0), 0.0)) > 0.01:
                        venta['monto_faltante'] = 0.0
                        changed = True
                    if abs(self._to_float_safe(venta.get('monto_pagado', total), total) - (total if total > 0 else pagado)) > 0.01 and total > 0:
                        venta['monto_pagado'] = total
                        venta['monto_adelanto'] = total
                        changed = True

                if changed:
                    ventas_actualizadas += 1

            for paciente in (pacientes or []):
                if not isinstance(paciente, dict):
                    continue
                historial = paciente.get('historial_graduaciones', []) or []
                for grad in historial:
                    if not isinstance(grad, dict):
                        continue
                    monto_total, monto_pagado, monto_faltante = self._resumen_pago_graduacion(grad)
                    if monto_total <= 0:
                        continue

                    changed = False
                    stored_total = self._to_float_safe(grad.get('monto_total_venta', 0), 0.0)
                    if abs(stored_total - monto_total) > 0.05:
                        if stored_total > monto_total:
                            grads_infladas_corregidas += 1
                        grad['monto_total_venta'] = monto_total
                        changed = True

                    deuda_activa = monto_faltante > 0.05
                    if deuda_activa:
                        grads_deuda_activas += 1

                    if deuda_activa:
                        if not grad.get('es_pago_parcial'):
                            grad['es_pago_parcial'] = True
                            changed = True
                        deuda_id = self._normalizar_deuda_id(grad.get('deuda_id'))
                        if not deuda_id:
                            grad['deuda_id'] = self._generar_deuda_id_unico(ids_existentes)
                            changed = True
                        if 'pagos_parciales' not in grad or not isinstance(grad.get('pagos_parciales'), list):
                            grad['pagos_parciales'] = []
                            changed = True
                        adelanto_actual = self._to_float_safe(grad.get('monto_adelanto', 0), 0.0)
                        if abs(adelanto_actual - monto_pagado) > 0.01:
                            grad['monto_adelanto'] = monto_pagado
                            changed = True
                    else:
                        if grad.get('es_pago_parcial'):
                            grad['es_pago_parcial'] = False
                            changed = True
                        if monto_total > 0 and self._to_float_safe(grad.get('monto_adelanto', 0), 0.0) > monto_total:
                            grad['monto_adelanto'] = monto_total
                            changed = True

                    if changed:
                        grads_actualizadas += 1

            branch_code = _resolve_branch_code_for_sync(self.username)

            if ventas_actualizadas > 0:
                guardar_ventas(self.username, ventas)
            elif ventas_deuda_activas > 0:
                _queue_sync_all_dataset_bg(self.username, "ventas", "ventas", ventas, branch_code=branch_code)
            if grads_actualizadas > 0:
                guardar_pacientes(self.username, pacientes)
            elif grads_deuda_activas > 0:
                _queue_sync_all_dataset_bg(self.username, "pacientes", "pacientes", pacientes, branch_code=branch_code)

            self.cargar_deudas()

            QMessageBox.information(
                self,
                "Deudas regularizadas",
                (
                    f"Ventas actualizadas: {ventas_actualizadas}\n"
                    f"Graduaciones actualizadas: {grads_actualizadas}\n\n"
                    f"Ventas infladas corregidas: {ventas_infladas_corregidas}\n"
                    f"Graduaciones infladas corregidas: {grads_infladas_corregidas}\n\n"
                    f"Ventas con deuda detectadas: {ventas_deuda_activas}\n"
                    f"Graduaciones con deuda detectadas: {grads_deuda_activas}\n\n"
                    "Las deudas detectadas se guardaron o se encolaron para sincronización."
                ) if (ventas_actualizadas or grads_actualizadas or ventas_deuda_activas or grads_deuda_activas) else
                "No se encontraron deudas activas en este contexto."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo regularizar las deudas: {str(e)}")
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

    def _start_deudas_loader(self):
        if not getattr(self, "username", None):
            return

        self._stop_deudas_loader()
        try:
            self.deudas_table.setRowCount(0)
            self.deudas_table.insertRow(0)
            loading_item = QTableWidgetItem("Cargando deudas...")
            loading_item.setTextAlignment(Qt.AlignCenter)
            self.deudas_table.setItem(0, 0, loading_item)
            self.deudas_table.setSpan(0, 0, 1, self.deudas_table.columnCount())
        except Exception:
            pass

        try:
            if hasattr(self, "deudas_refresh_btn"):
                self.deudas_refresh_btn.setEnabled(False)
            if hasattr(self, "deudas_rebuild_btn"):
                self.deudas_rebuild_btn.setEnabled(False)
            if hasattr(self, "deudas_info_btn"):
                self.deudas_info_btn.setEnabled(False)
        except Exception:
            pass

        thread = QtCore.QThread()
        _orphan_qthread(thread)
        worker = DebtLoadWorker(self.username)
        worker.moveToThread(thread)
        self._deudas_load_thread = thread
        self._deudas_load_worker = worker
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_deudas_loaded)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.start()

    def _stop_deudas_loader(self):
        thread = getattr(self, "_deudas_load_thread", None)
        if thread is not None:
            try:
                thread.quit()
            except Exception:
                pass
        self._deudas_load_thread = None
        self._deudas_load_worker = None

    def _on_deudas_loaded(self, ventas, pacientes, error):
        self._deudas_load_thread = None
        self._deudas_load_worker = None
        self.cargar_deudas(ventas=ventas, pacientes=pacientes, error=error)
    
    def cargar_deudas(self, *args, ventas=None, pacientes=None, error=""):
        """Carga todas las deudas pendientes de ventas y graduaciones."""
        try:
            self.deudas_table.setRowCount(0)

            _, _, _, requiere_sucursal_explica = self._actualizar_estado_ui_deudas()
            if requiere_sucursal_explica:
                return
            puede_editar = self._puede_editar_deudas()

            if ventas is None and pacientes is None and not error:
                self._start_deudas_loader()
                return
            if error:
                print(f"[DEUDAS] Error cargando datos: {error}")
            ventas = ventas if isinstance(ventas, list) else []
            pacientes = pacientes if isinstance(pacientes, list) else []

            deudas = []
            agregados_por_id = {}
            agregados_legacy = []
            ventas_por_id = {}
            for venta in ventas if isinstance(ventas, list) else []:
                if isinstance(venta, dict):
                    venta_id = str(venta.get('id', '') or '').strip()
                    if venta_id:
                        ventas_por_id[venta_id] = venta

            ids_existentes = self._colectar_ids_deuda_existentes(ventas, pacientes)
            ventas_actualizadas = False
            pacientes_actualizados = False
            
            # Agregar deudas de ventas
            for venta in ventas:
                if bool(venta.get('deuda_anulada')) or str(venta.get('estado_deuda', '') or '').strip().lower() == 'anulada':
                    continue
                # Calcular montos para verificar deuda real
                total = float(venta.get('total', 0) or 0)
                # Compatibilidad histórica:
                # - versiones antiguas usaban monto_adelanto
                # - algunas ventas no tenían monto_pagado
                tiene_pagado = 'monto_pagado' in venta
                tiene_adelanto = 'monto_adelanto' in venta
                monto_pagado = float(venta.get('monto_pagado', 0) or 0)
                monto_adelanto = float(venta.get('monto_adelanto', 0) or 0)
                if not tiene_pagado and not tiene_adelanto:
                    pagado = total
                else:
                    pagado = max(monto_pagado, monto_adelanto)
                
                if pagado > total and total > 0:
                    pagado = total
                pendiente = max(0.0, total - pagado)
                
                es_parcial = venta.get('es_pago_partes', False)
                faltante_explicito = float(venta.get('monto_faltante', 0) or 0)
                
                # Considerar deuda si tiene flag explícito o si hay diferencia calculada
                if pendiente > 0.05:
                    deuda_venta = dict(venta)
                    deuda_venta['tipo'] = 'venta'
                    deuda_venta['numero_orden'] = self._format_order_number(venta.get('numero_orden', '')) if str(venta.get('numero_orden', '') or '').strip() else ''
                    deuda_venta['contrato_numero'] = str(venta.get('contrato_numero', '') or '').strip()
                    deuda_venta['descripcion_compra'] = self._resumen_items_deuda(venta.get('items', []))
                    deuda_id = self._normalizar_deuda_id(deuda_venta.get('deuda_id'))
                    if not deuda_id:
                        deuda_id = self._generar_deuda_id_unico(ids_existentes)
                        deuda_venta['deuda_id'] = deuda_id
                        if puede_editar:
                            venta['deuda_id'] = deuda_id
                            ventas_actualizadas = True
                    else:
                        deuda_venta['deuda_id'] = deuda_id
                    # Asegurar que los campos necesarios para la tabla existan
                    if abs(faltante_explicito - pendiente) > 0.01:
                        deuda_venta['monto_faltante'] = pendiente
                        if puede_editar:
                            venta['monto_faltante'] = pendiente
                            ventas_actualizadas = True
                    if 'monto_adelanto' not in deuda_venta:
                        deuda_venta['monto_adelanto'] = pagado
                        if puede_editar:
                            venta['monto_adelanto'] = pagado
                            ventas_actualizadas = True
                        
                    deudas.append(deuda_venta)
                    agregados_por_id[deuda_id] = deuda_venta
                    agregados_legacy.append({
                        'dni': str(deuda_venta.get('paciente_dni', '')).strip(),
                        'fecha': str(deuda_venta.get('fecha', '')).strip(),
                        'total': total,
                        'ref': deuda_venta
                    })
            
            # Agregar deudas de graduaciones - cargar directamente desde pacientes
            try:
                for paciente in pacientes:
                    historial = paciente.get('historial_graduaciones', [])
                    for grad in historial:
                        if not isinstance(grad, dict):
                            continue
                        if bool(grad.get('deuda_anulada')) or str(grad.get('estado_deuda', '') or '').strip().lower() == 'anulada':
                            continue

                        cobro_total, monto_pagado, monto_faltante = self._resumen_pago_graduacion(grad)
                        if cobro_total <= 0:
                            continue

                        # Sincronizar flag legacy para mantener consistencia del historial.
                        es_parcial_real = monto_faltante > 0.05
                        if puede_editar and bool(grad.get('es_pago_parcial', False)) != es_parcial_real:
                            grad['es_pago_parcial'] = es_parcial_real
                            pacientes_actualizados = True

                        if es_parcial_real:
                            deuda_id = self._normalizar_deuda_id(grad.get('deuda_id'))
                            dni_grad = str(paciente.get('dni', '')).strip()
                            fecha_grad = str(grad.get('fecha', '')).strip()

                            duplicado_ref = None
                            if deuda_id and deuda_id in agregados_por_id:
                                duplicado_ref = agregados_por_id[deuda_id]
                            else:
                                for leg in agregados_legacy:
                                    if leg['dni'] == dni_grad and self._fechas_equivalentes(leg['fecha'], fecha_grad):
                                        if abs(leg['total'] - cobro_total) < 0.05:
                                            duplicado_ref = leg['ref']
                                            break

                            if duplicado_ref is not None:
                                duplicado_ref['tipo'] = ''
                                if not deuda_id and duplicado_ref.get('deuda_id') and puede_editar:
                                    grad['deuda_id'] = duplicado_ref.get('deuda_id')
                                    pacientes_actualizados = True
                                continue

                            if not deuda_id:
                                deuda_id = self._generar_deuda_id_unico(ids_existentes)
                                if puede_editar:
                                    grad['deuda_id'] = deuda_id
                                    pacientes_actualizados = True

                            deuda_grad = {
                                'tipo': 'graduacion',
                                'deuda_id': deuda_id,
                                'paciente_dni': dni_grad,
                                'paciente_nombre': paciente.get('nombre', ''),
                                'total': cobro_total,
                                'monto_adelanto': monto_pagado,
                                'monto_faltante': monto_faltante,
                                'fecha': fecha_grad,
                                'descripcion': f"Graduación - {grad.get('optometra', 'N/A')}",
                                'contrato_numero': str(grad.get('contrato_numero', '') or '').strip(),
                                'descripcion_compra': self._resumen_items_deuda(grad.get('items_venta', [])),
                            }
                            venta_relacionada_id = str(grad.get('venta_relacionada_id', '') or '').strip()
                            venta_relacionada = ventas_por_id.get(venta_relacionada_id)
                            if isinstance(venta_relacionada, dict):
                                deuda_grad['numero_orden'] = self._format_order_number(venta_relacionada.get('numero_orden', '')) if str(venta_relacionada.get('numero_orden', '') or '').strip() else ''
                                if not deuda_grad.get('contrato_numero'):
                                    deuda_grad['contrato_numero'] = str(venta_relacionada.get('contrato_numero', '') or '').strip()
                                if not deuda_grad.get('descripcion_compra'):
                                    deuda_grad['descripcion_compra'] = self._resumen_items_deuda(venta_relacionada.get('items', []))
                            deudas.append(deuda_grad)
                            agregados_por_id[deuda_id] = deuda_grad
                            agregados_legacy.append({
                                'dni': dni_grad,
                                'fecha': fecha_grad,
                                'total': cobro_total,
                                'ref': deuda_grad
                            })
            except Exception as e:
                print(f"[DEBUG] Error cargando deudas de graduaciones: {e}")
                import traceback
                traceback.print_exc()

            if puede_editar and ventas_actualizadas:
                guardar_ventas(self.username, ventas)
            if puede_editar and pacientes_actualizados:
                guardar_pacientes(self.username, pacientes)
            
            # Ordenar por fecha descendente usando fechas reales.
            deudas.sort(key=self._sort_key_fecha_deuda, reverse=True)
            
            # Llenar tabla
            for idx, deuda in enumerate(deudas):
                self.deudas_table.insertRow(idx)
                
                # DNI
                dni_item = QTableWidgetItem(deuda.get('paciente_dni', ''))
                self.deudas_table.setItem(idx, 0, dni_item)
                
                # Cliente
                cliente_item = QTableWidgetItem(deuda.get('paciente_nombre', ''))
                self.deudas_table.setItem(idx, 1, cliente_item)
                
                # N° Contrato
                contrato_item = QTableWidgetItem(str(deuda.get('contrato_numero', '') or '').strip())
                self.deudas_table.setItem(idx, 2, contrato_item)
                
                # Total
                total = deuda.get('total', 0)
                total_item = QTableWidgetItem(f"S/. {total:.2f}")
                total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.deudas_table.setItem(idx, 3, total_item)
                
                # Adelanto
                adelanto = deuda.get('monto_adelanto', 0)
                adelanto_item = QTableWidgetItem(f"S/. {adelanto:.2f}")
                adelanto_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.deudas_table.setItem(idx, 4, adelanto_item)
                
                # Falta Pagar
                falta = deuda.get('monto_faltante', 0)
                falta_item = QTableWidgetItem(f"S/. {falta:.2f}")
                falta_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                falta_item.setForeground(QBrush(QColor("#D32F2F")))  # Rojo
                falta_item.setFont(QFont("Arial", 10, QFont.Bold))
                self.deudas_table.setItem(idx, 5, falta_item)
                
                # Fecha
                fecha = deuda.get('fecha', '') or deuda.get('fecha_graduacion', '')
                tipo_str = deuda.get('tipo', 'venta')
                if tipo_str == '':
                    tipo_str = 'venta y graduación'
                tipo_item = QTableWidgetItem(f"{fecha} ({tipo_str})")
                self.deudas_table.setItem(idx, 6, tipo_item)

                # Deuda ID
                deuda_id = self._normalizar_deuda_id(deuda.get('deuda_id')) or "-"
                deuda_id_item = QTableWidgetItem(deuda_id)
                deuda_id_item.setToolTip(deuda_id)
                self.deudas_table.setItem(idx, 7, deuda_id_item)
                
                # Guardar la deuda completa en el item para referencia
                self.deudas_table.item(idx, 0).setData(Qt.UserRole, deuda)
                self.deudas_table.item(idx, 0).deuda_completa = deuda
        
        except Exception as e:
            print(f"Error cargando deudas: {e}")
            import traceback
            traceback.print_exc()
    
    def _schedule_filtrar_deudas(self, *_args):
        timer = getattr(self, "_deudas_filter_timer", None)
        if timer is None:
            self.filtrar_deudas()
            return
        timer.start(350)

    def filtrar_deudas(self):
        """Filtra las deudas por DNI, Cliente o N° Contrato."""
        filtro = self.deudas_dni_input.text().strip().lower()
        
        for row in range(self.deudas_table.rowCount()):
            dni_item = self.deudas_table.item(row, 0)
            cliente_item = self.deudas_table.item(row, 1)
            contrato_item = self.deudas_table.item(row, 2)
            
            debe_mostrar = False
            if filtro == "":
                debe_mostrar = True
            else:
                if dni_item and filtro in dni_item.text().lower():
                    debe_mostrar = True
                if cliente_item and filtro in cliente_item.text().lower():
                    debe_mostrar = True
                if contrato_item and filtro in contrato_item.text().lower():
                    debe_mostrar = True
            
            self.deudas_table.setRowHidden(row, not debe_mostrar)
    
    def _registrar_ingreso_caja_automatico(self, concepto, monto, fecha_caja=None):
        """Registra un cobro de deuda automáticamente en la caja del día actual."""
        try:
            if monto <= 0.01:
                return
            from utils.file_handler import cargar_caja, guardar_caja
            import datetime
            ahora = datetime.datetime.now()
            fecha_hoy = str(fecha_caja or "").strip() or ahora.strftime("%d/%m/%Y")
            hora_actual = ahora.strftime("%I:%M %p")
            
            caja_data = cargar_caja(self.username) or {}
            caja_dia = caja_data.setdefault(fecha_hoy, {})
            caja_dia.setdefault("base", 500.0)
            ingresos = caja_dia.setdefault("ingresos_extras", [])
            
            # Evitar duplicados simples (mismo concepto y monto registrado hoy)
            duplicado = False
            for ing in ingresos:
                if ing.get("descripcion") == concepto and abs(float(ing.get("monto", 0.0) or 0.0) - monto) < 0.01:
                    duplicado = True
                    break
            
            if not duplicado:
                ingresos.append({
                    "hora": hora_actual,
                    "descripcion": concepto,
                    "monto": monto
                })
                guardar_caja(self.username, caja_data)
                print(f"[CAJA] Se registró ingreso automático en caja: {concepto} por S/. {monto:.2f}")
        except Exception as e:
            print(f"[CAJA] Error al registrar ingreso automático: {e}")

    def _anular_ingreso_caja_automatico(self, concepto, monto, fecha_caja=None):
        """Elimina el ingreso automático de caja asociado a un cobro de deuda."""
        try:
            if monto <= 0.01:
                return False
            from utils.file_handler import cargar_caja, guardar_caja
            fecha_hoy = str(fecha_caja or "").strip() or datetime.datetime.now().strftime("%d/%m/%Y")
            caja_data = cargar_caja(self.username) or {}
            caja_dia = caja_data.get(fecha_hoy, {})
            if not isinstance(caja_dia, dict):
                return False

            ingresos = caja_dia.get("ingresos_extras", [])
            if not isinstance(ingresos, list) or not ingresos:
                return False

            removed = False
            remaining = []
            for ing in ingresos:
                if not isinstance(ing, dict):
                    remaining.append(ing)
                    continue
                desc = str(ing.get("descripcion", "") or "").strip()
                amt = float(ing.get("monto", 0.0) or 0.0)
                if (not removed) and desc == concepto and abs(amt - float(monto)) < 0.01:
                    removed = True
                    continue
                remaining.append(ing)

            if not removed:
                # Fallback: retirar la primera coincidencia por monto y texto de cobro deuda.
                for idx, ing in enumerate(list(remaining)):
                    if not isinstance(ing, dict):
                        continue
                    desc = str(ing.get("descripcion", "") or "").strip().lower()
                    amt = float(ing.get("monto", 0.0) or 0.0)
                    if abs(amt - float(monto)) < 0.01 and "cobro deuda" in desc:
                        remaining.pop(idx)
                        removed = True
                        break

            if not removed:
                return False

            caja_dia["ingresos_extras"] = remaining
            caja_data[fecha_hoy] = caja_dia
            guardar_caja(self.username, caja_data)
            print(f"[CAJA] Se anuló ingreso automático: {concepto} por S/. {monto:.2f}")
            return True
        except Exception as e:
            print(f"[CAJA] Error al anular ingreso automático: {e}")
            return False

    def marcar_deuda_pagada(self):
        """Marca una deuda como pagada (venta o graduación)."""
        from utils.file_handler import cargar_pacientes, guardar_pacientes

        if not self._asegurar_sucursal_para_deudas():
            return
        
        fila = self.deudas_table.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Seleccionar", "Selecciona una deuda para marcar como pagada.")
            return
        
        try:
            # Obtener el item con la información de la deuda
            dni_item = self.deudas_table.item(fila, 0)
            deuda_info = dni_item.data(Qt.UserRole) or getattr(dni_item, 'deuda_completa', None)
            dni_deuda = dni_item.text()
            
            if not dni_deuda:
                QMessageBox.warning(self, "Error", "No se pudo obtener el DNI de la deuda.")
                return
            
            tipo_encontrado_venta = False
            tipo_encontrado_grad = False
            
            # 1. Intentar actualizar en VENTAS
            ventas = cargar_ventas(self.username)
            deuda_id_ref = self._normalizar_deuda_id(deuda_info.get('deuda_id')) if deuda_info else ''
            id_venta = deuda_info.get('id') if deuda_info else None
            fecha_deuda = deuda_info.get('fecha') if deuda_info else None
            
            for v in ventas:
                # Buscar por ID si existe, sino por DNI y otros campos
                matches = False
                if deuda_id_ref and self._normalizar_deuda_id(v.get('deuda_id')) == deuda_id_ref:
                    matches = True
                elif id_venta and str(v.get('id', '')).strip() == str(id_venta).strip():
                    matches = True
                elif v.get('paciente_dni') == dni_deuda and (not fecha_deuda or v.get('fecha') == fecha_deuda):
                    matches = True
                
                if matches:
                    total = float(v.get('total', 0))
                    v['es_pago_partes'] = False
                    v['es_pago_parcial'] = False
                    v['monto_faltante'] = 0
                    v['monto_adelanto'] = total
                    v['monto_pagado'] = total
                    guardar_ventas(self.username, ventas)
                    tipo_encontrado_venta = True
                    break
            
            # 2. Intentar actualizar en GRADUACIONES
            pacientes = cargar_pacientes(self.username)
            for paciente in pacientes:
                if paciente.get('dni') == dni_deuda:
                    historial = paciente.get('historial_graduaciones', [])
                    for grad in historial:
                        grad_deuda_id = self._normalizar_deuda_id(grad.get('deuda_id'))
                        if (deuda_id_ref and grad_deuda_id == deuda_id_ref) or ((not deuda_id_ref) and ((fecha_deuda and grad.get('fecha') == fecha_deuda) or grad.get('es_pago_parcial'))):
                            grad['es_pago_parcial'] = False
                            tipo_encontrado_grad = True
                    if tipo_encontrado_grad:
                        guardar_pacientes(self.username, pacientes)
                        break
            
            if tipo_encontrado_venta or tipo_encontrado_grad:
                # Registrar en caja diaria
                monto_faltante = 0.0
                if deuda_info:
                    monto_faltante = float(deuda_info.get('monto_faltante', 0.0) or 0.0)
                nombre_cliente = deuda_info.get('paciente_nombre', 'Cliente') if deuda_info else 'Cliente'
                nro_orden = deuda_info.get('numero_orden', '') or deuda_info.get('contrato_numero', '') if deuda_info else ''
                tipo_txt = "Venta" if tipo_encontrado_venta else "Contrato"
                concepto = f"Cobro Deuda {tipo_txt} {nro_orden} - {nombre_cliente}"
                self._registrar_ingreso_caja_automatico(concepto, monto_faltante)

                self.cargar_deudas()
                tipo_msg = "venta y graduación" if (tipo_encontrado_venta and tipo_encontrado_grad) else ("venta" if tipo_encontrado_venta else "graduación")
                QMessageBox.information(self, "Éxito", f"Deuda de {tipo_msg} marcada como pagada.")
            else:
                QMessageBox.warning(self, "Error", "No se encontró la deuda en la base de datos.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo marcar la deuda: {str(e)}")
            import traceback
            traceback.print_exc()

    def _on_deuda_row_clicked(self, row, col):
        """Se ejecuta cuando se hace clic en una fila de deudas. Abre el diálogo de pago."""
        try:
            if not self._asegurar_sucursal_para_deudas():
                return

            if not self._puede_editar_deudas():
                QMessageBox.warning(
                    self,
                    "Permiso denegado",
                    "No tienes permiso para registrar pagos de deudas."
                )
                return

            # Obtener información de la fila
            dni_item = self.deudas_table.item(row, 0)
            if not dni_item:
                return
            
            # Recuperar la deuda completa guardada
            deuda_info = dni_item.data(Qt.UserRole) or getattr(dni_item, 'deuda_completa', None)
            
            if deuda_info:
                # Usar la información guardada preferentemente
                deuda = deuda_info.copy()
            else:
                # Fallback: Reconstruir la deuda desde la información visible
                dni = self.deudas_table.item(row, 0).text()
                nombre = self.deudas_table.item(row, 1).text()
                contrato = self.deudas_table.item(row, 2).text()
                total_text = self.deudas_table.item(row, 3).text().replace("S/. ", "").strip()
                adelanto_text = self.deudas_table.item(row, 4).text().replace("S/. ", "").strip()
                falta_text = self.deudas_table.item(row, 5).text().replace("S/. ", "").strip()
                fecha_col = self.deudas_table.item(row, 6).text()
                
                try:
                    total = float(total_text)
                    adelanto = float(adelanto_text)
                    falta = float(falta_text)
                except ValueError:
                    QMessageBox.warning(self, "Error", "No se pudo procesar los valores de la deuda.")
                    return
 
                # Extraer fecha y tipo desde la columna "Fecha (tipo)"
                tipo = 'venta'
                fecha = str(fecha_col or '').strip()
                if fecha.endswith(')') and ' (' in fecha:
                    fecha_base, tipo_raw = fecha.rsplit(' (', 1)
                    fecha = fecha_base.strip()
                    tipo = self._normalizar_tipo_deuda(tipo_raw[:-1].strip())
                
                deuda = {
                    'paciente_dni': dni,
                    'paciente_nombre': nombre,
                    'contrato_numero': contrato,
                    'total': total,
                    'monto_adelanto': adelanto,
                    'monto_faltante': falta,
                    'fecha': fecha,
                    'tipo': tipo
                }
            
            # Abrir diálogo
            dialog = DeudaPaymentDialog(deuda, self)
            if dialog.exec_() == QDialog.Accepted:
                # Procesar el resultado
                accion = deuda.get('_accion')
                procesado = False
                
                if accion == 'cancelar_todo':
                    procesado = bool(self._procesar_cancelar_todo(deuda))
                
                elif accion == 'pago_parcial':
                    monto_pagado = deuda.get('_monto_pagado', 0)
                    observaciones = deuda.get('_observaciones', '')
                    procesado = bool(self._procesar_pago_parcial(deuda, monto_pagado, observaciones))

                if procesado:
                    self._guardar_historial_pago_deuda(deuda)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar la deuda: {str(e)}")
            print(f"[ERROR] {e}")

    def abrir_contrato_desde_deuda(self, contract_number):
        contract_number = str(contract_number or "").strip()
        if not contract_number:
            return
        main_window = self.parent_app if self.parent_app is not None else self.window()
        if main_window is None or not hasattr(main_window, "mostrar_frame"):
            QMessageBox.warning(self, "Contratos", "No se pudo abrir la sección de contratos.")
            return

        loader = self._show_contract_navigation_loader("Llevando al contrato...")

        try:
            main_window.mostrar_frame(17)
        except Exception:
            try:
                if loader is not None:
                    loader.close()
                    loader.deleteLater()
            except Exception:
                pass
            QMessageBox.warning(self, "Contratos", "No se pudo navegar a la sección de contratos.")
            return

        def _focus():
            try:
                if loader is not None:
                    loader.close()
                    loader.deleteLater()
            except Exception:
                pass
            contracts_page = getattr(main_window, "page_17", None)
            if contracts_page is None or not hasattr(contracts_page, "focus_contract"):
                return
            try:
                contracts_page.focus_contract(contract_number)
            except Exception:
                pass

        QTimer.singleShot(250, _focus)

    def _show_contract_navigation_loader(self, text="Llevando al contrato..."):
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setModal(True)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog.setStyleSheet(
            """
            QDialog {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }
            QLabel {
                color: #111827;
                font-size: 13px;
            }
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #E5E7EB;
                min-height: 10px;
                max-height: 10px;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: #2563EB;
            }
            """
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        bar = QtWidgets.QProgressBar()
        bar.setRange(0, 0)
        bar.setTextVisible(False)
        layout.addWidget(label)
        layout.addWidget(bar)
        dialog.resize(260, 84)
        dialog.show()
        QtWidgets.QApplication.processEvents()
        return dialog

    def _normalizar_tipo_deuda(self, tipo):
        """Normaliza tipo de deuda para comparaciones robustas."""
        txt = str(tipo or '').strip().lower()
        txt = (
            txt.replace('á', 'a')
               .replace('é', 'e')
               .replace('í', 'i')
               .replace('ó', 'o')
               .replace('ú', 'u')
        )
        if txt == 'graduacion':
            return 'graduacion'
        if txt == 'venta':
            return 'venta'
        return txt

    def _parsear_fecha(self, fecha_txt):
        """Parsea fecha soportando formatos históricos del sistema."""
        txt = str(fecha_txt or '').strip()
        if not txt:
            return None
        if txt.endswith(')') and ' (' in txt:
            txt = txt.rsplit(' (', 1)[0].strip()

        formatos = (
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y",
            "%Y-%m-%d",
        )
        for fmt in formatos:
            try:
                return datetime.datetime.strptime(txt, fmt)
            except ValueError:
                continue
        return None

    def _fechas_equivalentes(self, f1, f2):
        """Compara fechas con tolerancia para datos antiguos."""
        s1 = str(f1 or '').strip()
        s2 = str(f2 or '').strip()
        if not s1 or not s2:
            return False

        if s1.endswith(')') and ' (' in s1:
            s1 = s1.rsplit(' (', 1)[0].strip()
        if s2.endswith(')') and ' (' in s2:
            s2 = s2.rsplit(' (', 1)[0].strip()

        if s1 == s2:
            return True

        d1 = self._parsear_fecha(s1)
        d2 = self._parsear_fecha(s2)
        if d1 and d2:
            return abs((d1 - d2).total_seconds()) <= 60
        return False

    def _coincide_venta_deuda(self, venta, dni_ref, fecha_ref=None, id_ref=None, total_ref=None, deuda_id_ref=None):
        """Determina si una venta del JSON corresponde a la deuda seleccionada."""
        deuda_id_venta = self._normalizar_deuda_id(venta.get('deuda_id'))
        deuda_id_obj = self._normalizar_deuda_id(deuda_id_ref)
        if deuda_id_obj:
            return bool(deuda_id_venta and deuda_id_venta == deuda_id_obj)

        venta_id = str(venta.get('id', '')).strip()
        ref_id = str(id_ref).strip() if id_ref is not None else ''
        if ref_id:
            if not (venta_id and venta_id == ref_id):
                return False
            # Si hay ID, pero también tenemos fecha/total, validarlos para evitar
            # choques de datos históricos con IDs duplicados.
            if fecha_ref and not self._fechas_equivalentes(venta.get('fecha', ''), fecha_ref):
                return False
            if total_ref is not None:
                try:
                    total_venta = float(venta.get('total', 0) or 0)
                    total_obj = float(total_ref or 0)
                    if abs(total_venta - total_obj) > 0.05:
                        return False
                except (TypeError, ValueError):
                    pass
            return True

        dni_venta = str(venta.get('paciente_dni', '')).strip()
        dni_ref_txt = str(dni_ref or '').strip()
        if dni_ref_txt and dni_venta != dni_ref_txt:
            return False

        if fecha_ref and not self._fechas_equivalentes(venta.get('fecha', ''), fecha_ref):
            return False

        if total_ref is not None:
            try:
                total_venta = float(venta.get('total', 0) or 0)
                total_obj = float(total_ref or 0)
                if abs(total_venta - total_obj) > 0.05:
                    return False
            except (TypeError, ValueError):
                pass

        return True
    
    def _procesar_cancelar_todo(self, deuda_obj):
        """Procesa el pago completo de una deuda."""
        try:
            if not self._asegurar_sucursal_para_deudas():
                return

            dni = deuda_obj.get('paciente_dni')
            tipo = deuda_obj.get('tipo')
            fecha = deuda_obj.get('fecha')
            fecha_caja = str(deuda_obj.get('_fecha_pago', '') or '').strip()
            id_venta = deuda_obj.get('id')
            total_ref = deuda_obj.get('total')
            deuda_id = self._normalizar_deuda_id(deuda_obj.get('deuda_id'))
            tipo_norm = self._normalizar_tipo_deuda(tipo)
            
            encontrada_venta = False
            encontrada_grad = False
            
            monto_faltante = float(deuda_obj.get('monto_faltante', 0.0) or 0.0)
            
            # 1. Actualizar en ventas solo si corresponde
            if tipo_norm in ('', 'venta'):
                ventas = cargar_ventas(self.username)
                for venta in ventas:
                    if self._coincide_venta_deuda(venta, dni, fecha, id_venta, total_ref, deuda_id):
                        # Limpiar TODOS los flags de deuda
                        venta['es_pago_partes'] = False
                        venta['es_pago_parcial'] = False
                        venta['monto_faltante'] = 0
                        
                        # Actualizar ambos campos de monto pagado al total
                        total = float(venta.get('total', 0))
                        venta['monto_adelanto'] = total
                        venta['monto_pagado'] = total
                        
                        guardar_ventas(self.username, ventas)
                        
                        # Registrar en caja diaria
                        nombre_cliente = deuda_obj.get('paciente_nombre', 'Cliente')
                        nro_orden = venta.get('numero_orden', '') or deuda_obj.get('contrato_numero', '')
                        concepto = f"Cobro Deuda Venta {nro_orden} - {nombre_cliente}"
                        self._registrar_ingreso_caja_automatico(concepto, monto_faltante, fecha_caja=fecha_caja)
                        
                        if tipo_norm == 'venta':
                            QMessageBox.information(self, "Éxito", "Venta marcada como completamente pagada.")
                        encontrada_venta = True
                        break

                # Fallback defensivo para datos antiguos/inconsistentes:
                # aplicar a la deuda activa más reciente del mismo DNI.
                if (not encontrada_venta) and (not deuda_id) and str(dni or '').strip():
                    candidatos = []
                    for v in ventas:
                        if str(v.get('paciente_dni', '')).strip() != str(dni).strip():
                            continue
                        total_v = float(v.get('total', 0) or 0)
                        pagado_v = float(v.get('monto_pagado', v.get('monto_adelanto', total_v)) or 0)
                        faltante_v = float(v.get('monto_faltante', max(0, total_v - pagado_v)) or 0)
                        if faltante_v > 0.05 or bool(v.get('es_pago_partes')) or bool(v.get('es_pago_parcial')):
                            candidatos.append(v)

                    if candidatos:
                        candidatos.sort(key=self._sort_key_fecha_venta, reverse=True)
                        venta = candidatos[0]
                        total = float(venta.get('total', 0) or 0)
                        venta['es_pago_partes'] = False
                        venta['es_pago_parcial'] = False
                        venta['monto_faltante'] = 0
                        venta['monto_adelanto'] = total
                        venta['monto_pagado'] = total
                        guardar_ventas(self.username, ventas)
                        
                        # Registrar en caja diaria
                        nombre_cliente = deuda_obj.get('paciente_nombre', 'Cliente')
                        nro_orden = venta.get('numero_orden', '') or deuda_obj.get('contrato_numero', '')
                        concepto = f"Cobro Deuda Venta (Fallback) {nro_orden} - {nombre_cliente}"
                        self._registrar_ingreso_caja_automatico(concepto, monto_faltante, fecha_caja=fecha_caja)
                        
                        if tipo_norm == 'venta':
                            QMessageBox.information(self, "Éxito", "Venta marcada como completamente pagada.")
                        encontrada_venta = True
            
            # 2. Actualizar graduaciones solo si corresponde
            if tipo_norm in ('', 'graduacion'):
                pacientes = cargar_pacientes(self.username)
                for paciente in pacientes:
                    if str(paciente.get('dni', '')).strip() == str(dni or '').strip():
                        historial = paciente.get('historial_graduaciones', [])
                        for grad in historial:
                            grad_deuda_id = self._normalizar_deuda_id(grad.get('deuda_id'))
                            if deuda_id:
                                coincide = bool(grad_deuda_id and grad_deuda_id == deuda_id)
                            elif fecha:
                                coincide = self._fechas_equivalentes(grad.get('fecha'), fecha)
                            else:
                                coincide = bool(grad.get('es_pago_parcial'))
                            if coincide:
                                if 'pagos_parciales' not in grad or not isinstance(grad.get('pagos_parciales'), list):
                                    grad['pagos_parciales'] = []

                                monto_total_grad, monto_pagado_grad, monto_faltante_grad = self._resumen_pago_graduacion(grad)
                                if monto_faltante_grad > 0.05:
                                    grad['pagos_parciales'].append({
                                        'fecha': (fecha_caja + " " + datetime.datetime.now().strftime("%H:%M")) if fecha_caja else datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                                        'monto': monto_faltante_grad,
                                        'observacion': 'Cancelacion total'
                                    })
                                    monto_pagado_grad += monto_faltante_grad

                                grad['monto_adelanto'] = monto_total_grad if monto_total_grad > 0 else monto_pagado_grad
                                grad['es_pago_parcial'] = False
                                encontrada_grad = True
                                break
                        if encontrada_grad:
                            guardar_pacientes(self.username, pacientes)
                            
                            # Registrar en caja diaria si no se procesó en ventas
                            if not encontrada_venta:
                                nombre_cliente = deuda_obj.get('paciente_nombre', 'Cliente')
                                nro_orden = deuda_obj.get('contrato_numero', '') or deuda_obj.get('numero_orden', '')
                                concepto = f"Cobro Deuda Contrato {nro_orden} - {nombre_cliente}"
                                self._registrar_ingreso_caja_automatico(concepto, monto_faltante, fecha_caja=fecha_caja)
                                
                            if tipo_norm == 'graduacion':
                                QMessageBox.information(self, "Éxito", "Graduación marcada como completamente pagada.")
                            break
            
            if not encontrada_venta and not encontrada_grad:
                QMessageBox.warning(self, "Error", "No se encontró la deuda en los archivos.")
                return False
            
            # Recargar tabla
            self.cargar_deudas()
            self.deudas_dni_input.clear()
            return True
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo procesar el pago: {str(e)}")
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            return False

    def _procesar_pago_parcial(self, deuda_obj, monto_pagado, observaciones):
        """Procesa un pago parcial de una deuda."""
        try:
            if not self._asegurar_sucursal_para_deudas():
                return

            if monto_pagado <= 0:
                QMessageBox.warning(self, "Error", "El monto debe ser mayor a 0.")
                return
            
            dni = deuda_obj.get('paciente_dni')
            tipo = deuda_obj.get('tipo')
            fecha = deuda_obj.get('fecha')
            fecha_caja = str(deuda_obj.get('_fecha_pago', '') or '').strip()
            id_venta = deuda_obj.get('id')
            total_ref = deuda_obj.get('total')
            deuda_id = self._normalizar_deuda_id(deuda_obj.get('deuda_id'))
            tipo_norm = self._normalizar_tipo_deuda(tipo)
            
            encontrada_venta = False
            encontrada_grad = False
            
            if tipo_norm in ('', 'venta'):
                ventas = cargar_ventas(self.username)
                for venta in ventas:
                    if self._coincide_venta_deuda(venta, dni, fecha, id_venta, total_ref, deuda_id):
                        # Actualizar venta con pago parcial
                        monto_previo = float(venta.get('monto_adelanto', 0) or 0)
                        # Si no hay monto_adelanto pero sí monto_pagado (compatibilidad)
                        if 'monto_adelanto' not in venta and 'monto_pagado' in venta:
                            monto_previo = float(venta.get('monto_pagado', 0) or 0)
                            
                        nuevo_adelanto = monto_previo + monto_pagado
                        venta['monto_adelanto'] = nuevo_adelanto
                        venta['monto_pagado'] = nuevo_adelanto # Actualizar ambos para consistencia
                        
                        total = float(venta.get('total', 0))
                        nuevo_faltante = max(0, total - nuevo_adelanto)
                        venta['monto_faltante'] = nuevo_faltante
                        
                        # Si no queda nada por pagar, marcar como completamente pagada
                        if nuevo_faltante <= 0.05:
                            venta['es_pago_partes'] = False
                            venta['es_pago_parcial'] = False
                            venta['monto_faltante'] = 0
                        else:
                            venta['es_pago_partes'] = True
                            venta['es_pago_parcial'] = True
                        
                        guardar_ventas(self.username, ventas)
                        
                        # Registrar en caja diaria
                        nombre_cliente = deuda_obj.get('paciente_nombre', 'Cliente')
                        nro_orden = venta.get('numero_orden', '') or deuda_obj.get('contrato_numero', '')
                        concepto = f"Cobro Deuda Venta {nro_orden} - {nombre_cliente}"
                        self._registrar_ingreso_caja_automatico(concepto, monto_pagado, fecha_caja=fecha_caja)
                        
                        if tipo_norm == 'venta':
                            QMessageBox.information(self, "Éxito", f"Pago de S/. {monto_pagado:.2f} registrado en venta.")
                        encontrada_venta = True
                        break

                # Fallback defensivo para datos antiguos/inconsistentes:
                # aplicar al registro de deuda activa más reciente del mismo DNI.
                if (not encontrada_venta) and (not deuda_id) and str(dni or '').strip():
                    candidatos = []
                    for v in ventas:
                        if str(v.get('paciente_dni', '')).strip() != str(dni).strip():
                            continue
                        total_v = float(v.get('total', 0) or 0)
                        pagado_v = float(v.get('monto_pagado', v.get('monto_adelanto', total_v)) or 0)
                        faltante_v = float(v.get('monto_faltante', max(0, total_v - pagado_v)) or 0)
                        if faltante_v > 0.05 or bool(v.get('es_pago_partes')) or bool(v.get('es_pago_parcial')):
                            candidatos.append(v)

                    if candidatos:
                        candidatos.sort(key=self._sort_key_fecha_venta, reverse=True)
                        venta = candidatos[0]
                        monto_previo = float(venta.get('monto_adelanto', venta.get('monto_pagado', 0)) or 0)
                        nuevo_adelanto = monto_previo + monto_pagado
                        total = float(venta.get('total', 0) or 0)
                        nuevo_faltante = max(0, total - nuevo_adelanto)
                        venta['monto_adelanto'] = nuevo_adelanto
                        venta['monto_pagado'] = nuevo_adelanto
                        venta['monto_faltante'] = 0 if nuevo_faltante <= 0.05 else nuevo_faltante
                        venta['es_pago_partes'] = nuevo_faltante > 0.05
                        venta['es_pago_parcial'] = nuevo_faltante > 0.05
                        guardar_ventas(self.username, ventas)
                        
                        # Registrar en caja diaria
                        nombre_cliente = deuda_obj.get('paciente_nombre', 'Cliente')
                        nro_orden = venta.get('numero_orden', '') or deuda_obj.get('contrato_numero', '')
                        concepto = f"Cobro Deuda Venta (Fallback) {nro_orden} - {nombre_cliente}"
                        self._registrar_ingreso_caja_automatico(concepto, monto_pagado, fecha_caja=fecha_caja)
                        
                        if tipo_norm == 'venta':
                            QMessageBox.information(self, "Éxito", f"Pago de S/. {monto_pagado:.2f} registrado en venta.")
                        encontrada_venta = True
            
            # Buscar en graduaciones solo si corresponde
            if tipo_norm in ('', 'graduacion'):
                pacientes = cargar_pacientes(self.username)
                for paciente in pacientes:
                    if str(paciente.get('dni', '')).strip() == str(dni or '').strip():
                        historial = paciente.get('historial_graduaciones', [])
                        for grad in historial:
                            grad_deuda_id = self._normalizar_deuda_id(grad.get('deuda_id'))
                            if deuda_id:
                                coincide = bool(grad_deuda_id and grad_deuda_id == deuda_id)
                            elif fecha:
                                coincide = self._fechas_equivalentes(grad.get('fecha'), fecha)
                            else:
                                coincide = bool(grad.get('es_pago_parcial'))
                            if coincide:
                                # Agregar pago parcial
                                if 'pagos_parciales' not in grad or not isinstance(grad.get('pagos_parciales'), list):
                                    grad['pagos_parciales'] = []

                                # Compatibilidad: si habia adelanto legacy sin lista de pagos, migrarlo.
                                if len(grad['pagos_parciales']) == 0:
                                    adelanto_legacy = self._to_float_safe(grad.get('monto_adelanto', 0), 0.0)
                                    if adelanto_legacy > 0.05:
                                        grad['pagos_parciales'].append({
                                            'fecha': (fecha_caja + " " + datetime.datetime.now().strftime("%H:%M")) if fecha_caja else (grad.get('fecha') or datetime.datetime.now().strftime("%d/%m/%Y %H:%M")),
                                            'monto': adelanto_legacy,
                                            'observacion': 'Adelanto inicial'
                                        })

                                grad['pagos_parciales'].append({
                                    'fecha': (fecha_caja + " " + datetime.datetime.now().strftime("%H:%M")) if fecha_caja else datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    'monto': monto_pagado,
                                    'observacion': observaciones or 'Pago adicional'
                                })
                                
                                # Recalcular montos
                                cobro_total, total_pagado_grad, falta = self._resumen_pago_graduacion(grad)
                                grad['monto_adelanto'] = total_pagado_grad
                                
                                # Si no queda nada por pagar, marcar como completamente pagada
                                if falta <= 0.05:
                                    grad['es_pago_parcial'] = False
                                else:
                                    grad['es_pago_parcial'] = True
                                
                                encontrada_grad = True
                                break
                        if encontrada_grad:
                            guardar_pacientes(self.username, pacientes)
                            
                            # Registrar en caja diaria si no se procesó en ventas
                            if not encontrada_venta:
                                nombre_cliente = deuda_obj.get('paciente_nombre', 'Cliente')
                                nro_orden = deuda_obj.get('contrato_numero', '') or deuda_obj.get('numero_orden', '')
                                concepto = f"Cobro Deuda Contrato {nro_orden} - {nombre_cliente}"
                                self._registrar_ingreso_caja_automatico(concepto, monto_pagado, fecha_caja=fecha_caja)
                                
                            if tipo_norm == 'graduacion':
                                QMessageBox.information(self, "Éxito", f"Pago de S/. {monto_pagado:.2f} registrado en graduación.")
                            break
            
            if not encontrada_venta and not encontrada_grad:
                QMessageBox.warning(self, "Error", "No se encontró la deuda en los archivos.")
                return False
            
            # Recargar tabla
            self.cargar_deudas()
            self.deudas_dni_input.clear()
            return True
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo procesar el pago: {str(e)}")
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            return False

    def _guardar_historial_pago_deuda(self, deuda_obj):
        """Guarda localmente y sincroniza a la nube el historial del pago de deuda."""
        try:
            from utils.api_handler import subir_dataset_dispositivo_nube
        except Exception as e:
            print(f"[SYNC] No se pudo importar el uploader de deuda: {e}")
            return

        try:
            deuda = dict(deuda_obj or {})
            accion = str(deuda.get("_accion", "") or "").strip().lower()
            if accion not in ("cancelar_todo", "pago_parcial"):
                return

            fecha_pago_txt = str(deuda.get("_fecha_pago", "") or "").strip()
            fecha_pago_dt = datetime.datetime.now()
            if fecha_pago_txt:
                try:
                    fecha_pago_dt = datetime.datetime.strptime(fecha_pago_txt, "%d/%m/%Y")
                except Exception:
                    fecha_pago_dt = datetime.datetime.now()

            total = float(deuda.get("total", 0) or 0)
            monto_faltante = float(deuda.get("monto_faltante", 0) or 0)
            monto_pagado = float(deuda.get("_monto_pagado", 0) or 0)
            if accion == "cancelar_todo":
                monto_pagado = monto_faltante
            monto_pagado = max(0.0, monto_pagado)

            branch_ctx = {}
            try:
                branch_ctx = get_effective_branch_context(self.username) or {}
            except Exception:
                branch_ctx = {}
            codigo_dispositivo = str((branch_ctx or {}).get("code", "") or "").strip().upper()
            if not codigo_dispositivo:
                try:
                    ctx_deudas = self._obtener_contexto_deudas()
                    codigo_dispositivo = str((ctx_deudas or ("", "", False, False))[0] or "").strip().upper()
                except Exception:
                    pass
            if not codigo_dispositivo:
                codigo_dispositivo = str(getattr(self.parent_app, "selected_branch_code", "") or "").strip().upper()

            usuario_madre = str(self.username or "").strip()
            try:
                cfg_path = get_user_file_path(self.username, "config_dispositivo.json")
                if cfg_path.exists():
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    if isinstance(cfg, dict):
                        usuario_madre = str(cfg.get("usuario_madre", usuario_madre) or usuario_madre).strip()
                        if not codigo_dispositivo:
                            codigo_dispositivo = str(
                                cfg.get("codigo_dispositivo_hijo")
                                or cfg.get("codigo_dispositivo_trabajador")
                                or cfg.get("codigo_dispositivo")
                                or ""
                            ).strip().upper()
            except Exception:
                pass

            if not codigo_dispositivo:
                print("[SYNC] No se pudo resolver la sucursal para guardar el historial de deuda.")
                return

            historial_path = get_branch_cache_data_dir(self.username, codigo_dispositivo) / "historial_pagos_deuda.json"
            try:
                if historial_path.exists():
                    with open(historial_path, "r", encoding="utf-8") as f:
                        historial = json.load(f)
                    if not isinstance(historial, list):
                        historial = []
                else:
                    historial = []
            except Exception:
                historial = []

            now = fecha_pago_dt.replace(
                hour=datetime.datetime.now().hour,
                minute=datetime.datetime.now().minute,
                second=datetime.datetime.now().second,
                microsecond=0,
            )
            now_iso = now.isoformat(timespec="seconds")
            registro = {
                "id": uuid.uuid4().hex,
                "deuda_id": str(deuda.get("deuda_id", "") or deuda.get("id", "") or "").strip(),
                "tipo": str(deuda.get("tipo", "") or "").strip(),
                "accion": accion,
                "paciente_dni": str(deuda.get("paciente_dni", "") or "").strip(),
                "paciente_nombre": str(deuda.get("paciente_nombre", "") or "").strip(),
                "contrato_numero": str(deuda.get("contrato_numero", "") or "").strip(),
                "numero_orden": str(deuda.get("numero_orden", "") or "").strip(),
                "total": total,
                "monto_pagado": monto_pagado,
                "saldo_anterior": monto_faltante if accion == "cancelar_todo" else max(0.0, total - float(deuda.get("monto_adelanto", 0) or 0)),
                "saldo_final": 0.0 if accion == "cancelar_todo" else max(0.0, monto_faltante - monto_pagado),
                "observaciones": str(deuda.get("_observaciones", "") or "").strip(),
                "usuario": str(self.username or "").strip(),
                "usuario_madre": usuario_madre,
                "codigo_dispositivo": codigo_dispositivo,
                "fecha_pago": fecha_pago_txt or now.strftime("%d/%m/%Y"),
                "fecha_registro": now.strftime("%d/%m/%Y %H:%M:%S"),
                "timestamp_iso": now_iso,
            }
            historial.append(registro)

            historial_path.parent.mkdir(parents=True, exist_ok=True)
            with open(historial_path, "w", encoding="utf-8") as f:
                json.dump(historial, f, indent=2, ensure_ascii=False)

            def _subir_historial():
                try:
                    ok, msg, _resp = subir_dataset_dispositivo_nube(
                        usuario_madre=usuario_madre,
                        codigo_dispositivo=codigo_dispositivo,
                        dataset="historial_pagos_deuda",
                        data=historial,
                        operacion="SYNC_ALL",
                        registro_id=f"bulk_historial_deuda_{codigo_dispositivo}",
                        contenido={"historial_pagos_deuda": historial},
                        updated_at=now_iso,
                    )
                    if not ok:
                        ok2, msg2, _resp2 = subir_dataset_dispositivo_nube(
                            usuario_madre=usuario_madre,
                            codigo_dispositivo=codigo_dispositivo,
                            dataset="historial_pagos_deuda",
                            data=historial,
                            operacion="SYNC_ALL",
                            registro_id=f"bulk_historial_deuda_{codigo_dispositivo}",
                            contenido={"historial_pagos_deuda": historial},
                            updated_at=now_iso,
                            endpoint_file="upload_device_snapshot_manual.php",
                        )
                        if ok2:
                            ok, msg = ok2, msg2
                    if not ok:
                        print(f"[SYNC] No se pudo subir historial de deuda a la nube: {msg}")
                    else:
                        print(f"[SYNC] Historial de deuda subido a la nube: {codigo_dispositivo}")
                except Exception as e:
                    print(f"[SYNC] Error subiendo historial de deuda a la nube: {e}")

            try:
                import threading
                threading.Thread(target=_subir_historial, daemon=True).start()
            except Exception:
                _subir_historial()
        except Exception as e:
            print(f"[SYNC] Error guardando historial de deuda: {e}")

    
    
    def buscar_dni_cliente(self):
        """Busca el DNI del cliente en la API de boletaspe.com (en otro thread)."""
        dni = self.manual_dni_input.text().strip()
        
        # Validar que el DNI sea válido
        if not dni or len(dni) != 8 or not dni.isdigit():
            QMessageBox.warning(self, "DNI Inválido", "Ingrese un DNI válido de 8 dígitos.")
            return
        
        # Mostrar spinner en el botón
        self._start_button_spinner()
        
        # Crear y ejecutar worker en thread separado
        self.dni_search_thread = QThread()
        self.dni_search_worker = DNISearchWorker(dni)
        self.dni_search_worker.moveToThread(self.dni_search_thread)
        
        # Conectar signals
        self.dni_search_worker.success.connect(self._on_dni_found)
        self.dni_search_worker.error.connect(self._on_dni_error)
        self.dni_search_worker.finished.connect(self._stop_button_spinner)
        self.dni_search_worker.finished.connect(self.dni_search_thread.quit)
        self.dni_search_thread.started.connect(self.dni_search_worker.run)
        
        # Iniciar thread
        self.dni_search_thread.start()
    
    def _start_button_spinner(self):
        """Muestra un spinner animado en el botón."""
        self.manual_search_dni_btn.setEnabled(False)
        
        # Crear un SVG de spinner
        spinner_svg = """
        <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <style>
                @keyframes spin {{ animation: spin 1s linear infinite; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                .spinner {{ animation: spin 1s linear infinite; transform-origin: 12px 12px; }}
            </style>
            <circle class="spinner" cx="12" cy="12" r="10" fill="none" stroke="white" stroke-width="2" stroke-dasharray="15.7 47.1"/>
        </svg>
        """
        
        # Guardar el texto original
        self.manual_search_dni_btn._original_text = "Buscar"
        self.manual_search_dni_btn.setText("⟳")
        self.manual_search_dni_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 16px;
                font-size: 16px;
            }
            QPushButton:disabled {
                background: #1565C0;
            }
        """)
        
        # Crear animación de rotación
        self._spinner_angle = 0
        self._spinner_timer = QtCore.QTimer()
        self._spinner_timer.timeout.connect(self._rotate_spinner)
        self._spinner_timer.start(50)
    
    def _rotate_spinner(self):
        """Rota el spinner."""
        # Caracteres Unicode de rotación suave
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.manual_search_dni_btn.setText(spinner_chars[self._spinner_angle % len(spinner_chars)])
        self._spinner_angle += 1
    
    def _stop_button_spinner(self):
        """Detiene el spinner y restaura el botón."""
        if hasattr(self, '_spinner_timer'):
            self._spinner_timer.stop()
        
        self.manual_search_dni_btn.setEnabled(True)
        self.manual_search_dni_btn.setText(getattr(self.manual_search_dni_btn, '_original_text', 'Buscar'))
        self.manual_search_dni_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #1565C0;
            }
            QPushButton:pressed {
                background: #0D47A1;
            }
        """)
    
    def _on_dni_found(self, data):
        """Maneja el resultado exitoso de búsqueda."""
        nombre_completo = f"{data['nombres']} {data['apellidos']}".strip()
        self.manual_nombre_input.setText(nombre_completo)
        QMessageBox.information(self, "Éxito", f"Cliente encontrado: {nombre_completo}")
    
    def _on_dni_error(self, error_msg):
        """Maneja los errores de búsqueda."""
        if error_msg == "cliente_generico":
            QMessageBox.information(self, "Información", "Este es el cliente genérico. Ingrese los datos manualmente.")
        else:
            QMessageBox.critical(self, "Error", error_msg)
    
    
    def _toggle_monto_adelanto(self):
        """Muestra/oculta el campo de adelanto según el checkbox."""
        es_pago_partes = self.manual_pago_partes_check.isChecked()
        self.manual_monto_adelanto_input.setVisible(es_pago_partes)
    
    def actualizar_total_manual(self):
        """Actualiza el total en la venta manual.
        
        El precio ingresado es el TOTAL (con IGV incluido).
        Se desglosal en subtotal (sin IGV) e IGV.
        """
        cantidad = self.manual_cantidad_spin.value()
        total_con_igv = cantidad * self.manual_precio_input.value()
        
        # El precio ingresado es el total con IGV
        # Calcular el subtotal (sin IGV) dividiendo por 1.18
        subtotal = total_con_igv / 1.18
        igv = total_con_igv - subtotal
        
        self.manual_subtotal_label.setText(f"S/. {subtotal:.2f}")
        self.manual_igv_label.setText(f"S/. {igv:.2f}")
        self.manual_total_label.setText(f"S/. {total_con_igv:.2f}")
    
    def limpiar_venta_manual(self):
        """Limpia los campos de la venta manual."""
        self.manual_dni_input.setText("00000000")
        self.manual_nombre_input.setText("")
        self.manual_telefono_input.setText("")
        self.manual_producto_input.setText("")
        self.manual_descripcion_input.setText("")
        self.manual_cantidad_spin.setValue(1)
        self.manual_precio_input.setValue(0.00)
        self.manual_metodo_combo.setCurrentIndex(0)
        self.manual_pago_partes_check.setChecked(False)
        self.manual_monto_adelanto_input.setValue(0.00)
        self.actualizar_total_manual()
    
    def registrar_venta_manual(self):
        """Registra una venta ingresada manualmente."""
        # 🛡️ VERIFICAR PERMISO
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('ventas', 'registrar'):
                QMessageBox.warning(self, "Permiso Denegado", "No tienes permiso para registrar ventas.")
                return
        
        # Validar datos
        dni = self.manual_dni_input.text().strip()
        nombre = self.manual_nombre_input.text().strip()
        producto = self.manual_producto_input.text().strip()
        cantidad = self.manual_cantidad_spin.value()
        precio = self.manual_precio_input.value()
        metodo = self.manual_metodo_combo.currentText()
        es_pago_partes = self.manual_pago_partes_check.isChecked()
        monto_adelanto = self.manual_monto_adelanto_input.value() if es_pago_partes else 0.00
        
        if not producto:
            QMessageBox.critical(self, "Error", "El nombre del producto es obligatorio.")
            return
        
        if precio <= 0:
            QMessageBox.critical(self, "Error", "El precio debe ser mayor a 0.")
            return
        
        if cantidad <= 0:
            QMessageBox.critical(self, "Error", "La cantidad debe ser mayor a 0.")
            return
        
        # Determinar nombre del paciente
        if nombre:
            paciente_nombre = nombre
        elif dni == "00000000":
            paciente_nombre = "Cliente Genérico"
        else:
            paciente_nombre = f"Cliente {dni}"
        
        # Crear venta
        total_con_igv = cantidad * precio
        subtotal = total_con_igv / 1.18
        igv = total_con_igv - subtotal
        
        # Calcular monto faltante (si es pago en partes)
        monto_faltante = total_con_igv - monto_adelanto if es_pago_partes else 0
        
        ventas = cargar_ventas(self.username)
        numero_orden = self._format_order_number(self._compute_next_order_sequence(ventas=ventas))

        nueva_venta = {
            'fecha': datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'paciente_dni': dni,
            'paciente_nombre': paciente_nombre,
            'usuario': self.username,
            'helper_name': self.parent_app.helper_name if (self.parent_app and self.parent_app.is_helper) else None,
            'numero_orden': numero_orden,
            'items': [
                {
                    'producto': producto,
                    'cantidad': cantidad,
                    'precio_unitario': precio,
                    'subtotal': subtotal
                }
            ],
            'subtotal': subtotal,
            'igv': igv,
            'total': total_con_igv,
            'metodo_pago': metodo.lower(),
            'es_pago_partes': es_pago_partes,
            'monto_adelanto': monto_adelanto if es_pago_partes else 0,
            'monto_faltante': monto_faltante,
            'es_pago_parcial': es_pago_partes and monto_faltante > 0,
            # Determinar vendedor: si es ayudante, usar su nombre; si no, usar usuario
            'vendedor': self.parent_app.helper_name if (self.parent_app and self.parent_app.is_helper and self.parent_app.helper_name) else self.username
        }

        if es_pago_partes and monto_faltante > 0.05:
            nueva_venta['deuda_id'] = self._generar_deuda_id_unico()
        
        # Guardar venta
        try:
            nueva_venta['id'] = self._generar_id_venta_unico(ventas)
            ventas.append(nueva_venta)
            guardar_ventas(self.username, ventas)
            
            # Registrar en libro contable
            try:
                if hasattr(self.parent_app, 'audit_manager'):
                    self.parent_app.audit_manager.log_action(
                        user_id=getattr(self.parent_app, 'user_id', 'unknown'),
                        username=self.username,
                        helper_name=getattr(self.parent_app, 'helper_name', None),
                        action='crear',
                        module='ventas',
                        details=f"Venta Manual: {producto} x{cantidad} - S/. {total_con_igv:.2f} - {paciente_nombre}"
                    )
            except:
                pass
            
            # Crear mensaje con información del pago
            if es_pago_partes and monto_faltante > 0:
                mensaje_texto = f"""Venta de S/. {total_con_igv:.2f} registrada correctamente.

INFORMACIÓN DE PAGO EN PARTES:
Adelanto: S/. {monto_adelanto:.2f}
Falta pagar: S/. {monto_faltante:.2f}"""
            else:
                mensaje_texto = f"Venta de S/. {total_con_igv:.2f} registrada correctamente.\n\nPago completo."
            
            # Crear un diálogo personalizado con botones "Opciones" y "OK"
            msg = QMessageBox(self)
            msg.setWindowTitle("Venta Registrada")
            msg.setText(mensaje_texto)
            msg.setIcon(QMessageBox.Information)
            
            # Agregar botones personalizados
            btn_opciones = msg.addButton("Opciones", QMessageBox.AcceptRole)
            btn_ok = msg.addButton("OK", QMessageBox.RejectRole)
            
            msg.exec_()
            
            # Verificar cuál botón fue presionado
            if msg.clickedButton() == btn_opciones:
                # Mostrar diálogo de opciones para la venta
                from gui.dialogs.sale_options_dialog import SaleOptionsDialog
                # Obtener helper_name si es un ayudante
                helper_name = self.parent_app.helper_name if (self.parent_app and self.parent_app.is_helper) else None
                is_helper = self.parent_app.is_helper if self.parent_app else False
                options_dialog = SaleOptionsDialog(nueva_venta, self.username, parent=self, helper_name=helper_name, is_helper=is_helper)
                options_dialog.exec_()
            
            self.limpiar_venta_manual()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo registrar la venta:\n{str(e)}")
    
    def _cargar_metodos_pago(self):
        """Carga los métodos de pago configurados por el usuario."""
        try:
            if not self.username:
                return []
            
            from utils.file_handler import cargar_metodos_pago
            metodos = cargar_metodos_pago(self.username)
            
            # Si la lista está vacía o es None, retornar una lista vacía
            if not metodos:
                return []
            
            # Asegurar que es una lista de strings
            return [str(m) for m in metodos]
        except Exception as e:
            print(f"[ERROR] Error al cargar métodos de pago: {e}")
            return []

class _SalesHistoryLoaderWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(list, str, str)

    def __init__(self, username: str):
        super().__init__()
        self._username = username

    @staticmethod
    def _date_key_from_fecha(fecha_value) -> int:
        """Convierte 'dd/mm/YYYY ...' a int YYYYMMDD (0 si no se puede)."""
        try:
            raw = str(fecha_value or "").strip()
            if not raw:
                return 0
            raw = raw.split()[0]
            parts = raw.split("/")
            if len(parts) != 3:
                return 0
            dd = int(parts[0])
            mm = int(parts[1])
            yy = int(parts[2])
            if yy <= 0 or mm <= 0 or dd <= 0:
                return 0
            return (yy * 10000) + (mm * 100) + dd
        except Exception:
            return 0

    @QtCore.pyqtSlot()
    def run(self):
        try:
            sales = cargar_ventas(self._username)
            if not isinstance(sales, list):
                sales = []

            try:
                from utils.sync_manager import get_sync_manager
                has_internet = bool(get_sync_manager().check_internet())
            except Exception:
                has_internet = False

            try:
                branch_ctx = get_active_branch_context(self._username) or {}
            except Exception:
                branch_ctx = {}

            branch_code = str((branch_ctx or {}).get("code", "") or "").strip().upper()
            branch_label = str((branch_ctx or {}).get("label", "") or "").strip() or branch_code
            source_text = "local (sin internet)"
            if has_internet:
                source_text = f"nube ({branch_label})" if branch_code else "nube (todas las sucursales)"

            # Precomputar llave de fecha para filtrar sin strptime (mejora performance y evita "No responde").
            for s in sales:
                if not isinstance(s, dict):
                    continue
                if "_viso_date_key" in s:
                    continue
                s["_viso_date_key"] = self._date_key_from_fecha(s.get("fecha"))
            self.finished.emit(sales, "", source_text)
        except Exception as e:
            self.finished.emit([], str(e), "desconocido")


class _PdfJobWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str, str)

    def __init__(self, job_callable):
        super().__init__()
        self._job_callable = job_callable

    @QtCore.pyqtSlot()
    def run(self):
        try:
            result_path = self._job_callable()
            self.finished.emit(str(result_path or ""), "")
        except Exception as e:
            self.finished.emit("", str(e))


class SalesHistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        initialize_sales_history_state(self, parent)
        build_sales_history_page(self, parent)

    def _extract_order_sequence(self, value):
        text = str(value or "").strip()
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0

    def _format_order_number(self, value):
        sequence = self._extract_order_sequence(value)
        if sequence <= 0:
            return "0001"
        digits = str(sequence)
        return digits.zfill(4) if len(digits) < 4 else digits

    def closeEvent(self, event):
        self._is_closing = True
        self._cleanup_async()
        try:
            super().closeEvent(event)
        except Exception:
            pass

    def event(self, event):
        try:
            if event is not None and int(event.type()) == int(QtCore.QEvent.DeferredDelete):
                self._is_closing = True
                self._cleanup_async()
        except Exception:
            pass
        return super().event(event)

    def _cleanup_async(self):
        try:
            self._cancel_sales_fill()
        except Exception:
            pass

        dialog = getattr(self, "_sale_options_dialog", None)
        if dialog is not None:
            try:
                dialog.close()
            except Exception:
                pass
        self._sale_options_dialog = None

        thread = getattr(self, "_sales_load_thread", None)
        if thread is not None:
            try:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(300)
            except Exception:
                pass
            try:
                if hasattr(thread, "isRunning") and thread.isRunning():
                    _orphan_qthread(thread)
            except Exception:
                pass
        self._sales_load_thread = None
        self._sales_load_worker = None

    # Compat: llamado por main_window al descargar pÃ¡ginas
    def _cleanup_all_threads(self):
        return self._cleanup_async()

    def _reload_sales(self):
        """Forzar recarga del archivo de ventas y actualizar UI."""
        if getattr(self, "_is_closing", False):
            return
        # Evitar congelar el UI leyendo/parseando JSON en el hilo principal
        self._reload_sales_async()
        return
        try:
            sales = cargar_ventas(self.username)
            ventas_count = len(sales)
        except Exception:
            sales = []
            ventas_count = 0

        ventas_path = str(get_user_file_path(self.username, "ventas.json")) if self.username else "<no username>"
        self.debug_label.setText(f"Usuario: {self.username} — ventas cargadas: {ventas_count} — ruta: {ventas_path}")

        if not sales:
            self.empty_message.setVisible(True)
            self.sales_table.setVisible(False)
            self.update_sales_history_table([])
        else:
            self.empty_message.setVisible(False)
            self.sales_table.setVisible(True)
            self.update_sales_history_table(sales)

    def _reload_sales_async(self):
        return saleshistory_reload_sales_async(self)

    def _stop_sales_loader(self):
        return saleshistory_stop_sales_loader(self)

    def _on_sales_loaded(self, sales: list, error: str, source_text: str):
        return saleshistory_on_sales_loaded(self, sales, error, source_text)

    def _generar_reporte_excel(self):
        """Abre diálogo para seleccionar formato de reporte y genera el reporte en Excel."""
        try:
            from gui.dialogs.reporte_formato_dialog import ReporteFormatoDialog
            from utils.reporte_ventas_excel import generar_reporte_ventas_excel
            
            # Cargar las ventas actuales (usar cache si existe)
            ventas_data = getattr(self, "_all_sales", None)
            if ventas_data is None:
                ventas_data = cargar_ventas(self.username)
            
            if not ventas_data:
                QMessageBox.warning(self, "Advertencia", "No hay ventas para generar el reporte.")
                return
            
            # Mostrar diálogo para seleccionar formato
            dialog = ReporteFormatoDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                # Determinar si usar diseño o no
                con_diseño = dialog.selected_format == "con_diseño"
                
                # Generar el reporte con el formato seleccionado
                success, filepath, message = generar_reporte_ventas_excel(
                    self.username, 
                    ventas_data,
                    con_diseño=con_diseño
                )
                
                if success:
                    QMessageBox.information(
                        self, 
                        "Éxito", 
                        f"✅ {message}\n\nEl archivo se ha abierto en el explorador de archivos."
                    )
                else:
                    QMessageBox.critical(self, "Error", f"❌ {message}")
        
        except ImportError as e:
            QMessageBox.critical(self, "Error", f"Error de importación:\n{str(e)}\n\nIntenta instalar las dependencias necesarias.")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error", f"Error al generar reporte:\n{str(e)}")

    def _generar_reportes_globales(self):
        """Abre diálogo para generar reportes globales consolidados."""
        try:
            from gui.dialogs.reporte_global_dialog import ReporteGlobalDialog
            from utils.reporte_global import generar_reporte_global
            
            # Cargar las ventas actuales (usar cache si existe)
            ventas_data = getattr(self, "_all_sales", None)
            if ventas_data is None:
                ventas_data = cargar_ventas(self.username)
            
            if not ventas_data:
                QMessageBox.warning(self, "Advertencia", "No hay ventas para generar el reporte.")
                return
            
            # Mostrar diálogo para seleccionar parámetros
            dialog = ReporteGlobalDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                parameters = dialog.get_parameters()
                
                if parameters:
                    # Generar el reporte global
                    success, filepath, message = generar_reporte_global(
                        self.username,
                        ventas_data,
                        parameters
                    )
                    
                    if success:
                        QMessageBox.information(
                            self,
                            "Éxito",
                            f"✅ {message}\n\nEl archivo se ha abierto en el explorador de archivos."
                        )
                    else:
                        QMessageBox.critical(self, "Error", f"❌ {message}")
        
        except ImportError as e:
            QMessageBox.critical(self, "Error", f"Error de importación:\n{str(e)}\n\nIntenta instalar las dependencias necesarias.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al generar reporte global:\n{str(e)}")

    def _open_today_sales_pdf_customizer(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Personalizar PDF de ventas del día")
        dialog.setMinimumWidth(460)
        dialog.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
            }
            QGroupBox {
                font-weight: 700;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        info = QLabel("Elige qué datos quieres mostrar en el PDF de ventas del día.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #4B5563;")
        layout.addWidget(info)

        group = QGroupBox("Columnas")
        group_layout = QGridLayout(group)
        group_layout.setHorizontalSpacing(16)
        group_layout.setVerticalSpacing(10)

        column_specs = [
            ("fecha", "Fecha", True),
            ("numero_orden", "N° Orden", True),
            ("dni", "DNI", True),
            ("cliente", "Cliente", True),
            ("articulos", "Artículos", True),
            ("metodo", "Método", True),
            ("estado", "Estado", True),
            ("total", "Total", True),
            ("contrato_numero", "N° Contrato", True),
            ("comision", "Comisión", False),
            ("comision_usuario", "Beneficiario Comisión", False),
        ]
        column_checks = {}
        for idx, (key, label, checked) in enumerate(column_specs):
            checkbox = QCheckBox(label)
            checkbox.setChecked(checked)
            group_layout.addWidget(checkbox, idx // 2, idx % 2)
            column_checks[key] = checkbox
        layout.addWidget(group)

        orientation_group = QGroupBox("Orientación")
        orientation_layout = QHBoxLayout(orientation_group)
        orientation_layout.setContentsMargins(14, 14, 14, 14)
        orientation_layout.setSpacing(10)
        orientation_layout.addWidget(QLabel("Formato:"))
        orientation_combo = QComboBox()
        orientation_combo.addItem("Vertical", "portrait")
        orientation_combo.addItem("Horizontal", "landscape")
        orientation_layout.addWidget(orientation_combo)
        orientation_layout.addStretch(1)
        layout.addWidget(orientation_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(dialog.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_generate = QPushButton("Generar PDF")
        btn_generate.setStyleSheet("""
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1D4ED8;
            }
        """)
        buttons_layout.addWidget(btn_generate)
        layout.addLayout(buttons_layout)

        def _generate():
            selected_columns = [
                key for key, checkbox in column_checks.items()
                if checkbox.isChecked()
            ]
            if not selected_columns:
                QMessageBox.warning(dialog, "Ventas del día", "Selecciona al menos una columna.")
                return
            dialog.accept()
            
            # Obtener la fecha escrita en el input de la UI
            fecha_export = datetime.date.today()
            if hasattr(self, "fecha_texto_input"):
                try:
                    fecha_export = datetime.datetime.strptime(self.fecha_texto_input.text().strip(), "%d/%m/%Y").date()
                except Exception:
                    pass

            self._export_today_sales_pdf({
                "columns": selected_columns,
                "orientation": orientation_combo.currentData() or "portrait",
                "_export_date": fecha_export,
            })

        btn_generate.clicked.connect(_generate)
        dialog.exec_()

    def _open_specific_day_sales_pdf_customizer(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Exportar ventas de otra fecha")
        dialog.setMinimumWidth(480)
        dialog.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
            }
            QGroupBox {
                font-weight: 700;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        info = QLabel("Selecciona la fecha exacta que deseas exportar y las columnas que quieres mostrar.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #4B5563;")
        layout.addWidget(info)

        date_group = QGroupBox("Fecha a exportar")
        date_layout = QHBoxLayout(date_group)
        date_layout.setContentsMargins(14, 14, 14, 14)
        date_layout.setSpacing(10)
        date_label = QLabel("Día:")
        date_edit = QDateEdit(calendarPopup=True)
        date_edit.setDate(QDate.currentDate())
        date_edit.setDisplayFormat("dd/MM/yyyy")
        date_edit.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #fff;
                min-width: 140px;
            }
        """)
        date_layout.addWidget(date_label)
        date_layout.addWidget(date_edit)
        date_layout.addStretch(1)
        layout.addWidget(date_group)

        group = QGroupBox("Columnas")
        group_layout = QGridLayout(group)
        group_layout.setHorizontalSpacing(16)
        group_layout.setVerticalSpacing(10)

        column_specs = [
            ("fecha", "Fecha", True),
            ("numero_orden", "N° Orden", True),
            ("dni", "DNI", True),
            ("cliente", "Cliente", True),
            ("articulos", "Artículos", True),
            ("metodo", "Método", True),
            ("estado", "Estado", True),
            ("total", "Total", True),
            ("contrato_numero", "N° Contrato", True),
            ("comision", "Comisión", False),
            ("comision_usuario", "Beneficiario Comisión", False),
        ]
        column_checks = {}
        for idx, (key, label, checked) in enumerate(column_specs):
            checkbox = QCheckBox(label)
            checkbox.setChecked(checked)
            group_layout.addWidget(checkbox, idx // 2, idx % 2)
            column_checks[key] = checkbox
        layout.addWidget(group)

        orientation_group = QGroupBox("Orientación")
        orientation_layout = QHBoxLayout(orientation_group)
        orientation_layout.setContentsMargins(14, 14, 14, 14)
        orientation_layout.setSpacing(10)
        orientation_layout.addWidget(QLabel("Formato:"))
        orientation_combo = QComboBox()
        orientation_combo.addItem("Vertical", "portrait")
        orientation_combo.addItem("Horizontal", "landscape")
        orientation_layout.addWidget(orientation_combo)
        orientation_layout.addStretch(1)
        layout.addWidget(orientation_group)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(dialog.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_generate = QPushButton("Generar PDF")
        btn_generate.setStyleSheet("""
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1D4ED8;
            }
        """)
        buttons_layout.addWidget(btn_generate)
        layout.addLayout(buttons_layout)

        def _generate():
            selected_columns = [
                key for key, checkbox in column_checks.items()
                if checkbox.isChecked()
            ]
            if not selected_columns:
                QMessageBox.warning(dialog, "Ventas por fecha", "Selecciona al menos una columna.")
                return
            selected_date = date_edit.date().toPyDate()
            dialog.accept()
            self._export_day_sales_pdf(selected_date, {
                "columns": selected_columns,
                "orientation": orientation_combo.currentData() or "portrait",
            })

        btn_generate.clicked.connect(_generate)
        dialog.exec_()

    def _get_daily_sales_report_header_context(self):
        try:
            optica_name = str(cargar_nombre_optica(self.username) or "Mi Óptica").strip() or "Mi Óptica"
        except Exception:
            optica_name = "Mi Óptica"

        branch_name = ""
        try:
            ctx = get_effective_branch_context(self.username)
            if ctx and ctx.get("label"):
                branch_name = str(ctx.get("label", "")).strip()
        except Exception:
            branch_name = ""

        if branch_name:
            branch_name = re.sub(r"\s*\([A-Z0-9\-]+\)\s*$", "", branch_name).strip()
        if not branch_name:
            try:
                branch_name = str(self._guia_get_current_child_branch_label() or "").strip()
            except Exception:
                branch_name = ""
        if not branch_name:
            try:
                branch_name = str(getattr(self, "selected_branch_name", "") or "").strip()
            except Exception:
                branch_name = ""
        if not branch_name:
            branch_name = "Principal"

        return {
            "optica_name": optica_name,
            "branch_name": branch_name,
        }

    def _build_daily_sales_html_template_pdf(self, pdf_path, export_date, sales_today, row_payloads, summary):
        import base64
        import io
        import subprocess
        import tempfile
        import qrcode
        from utils.file_handler import cargar_configuracion_optica, cargar_logo_optica

        template_html_path = obtener_ruta_plantilla_ventas(self.username)
        if not os.path.exists(template_html_path):
            return False

        if str(template_html_path).lower().endswith(".liquid"):
            return self._build_daily_sales_liquid_template_pdf(
                pdf_path,
                export_date,
                sales_today,
                row_payloads,
                summary,
                template_html_path,
            )

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((path for path in chrome_paths if os.path.exists(path)), None)
        if not chrome_exe:
            return False

        with open(template_html_path, "r", encoding="utf-8", errors="replace") as tpl_file:
            template_html = tpl_file.read()
        if "Ã" in template_html:
            try:
                template_html = template_html.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            except Exception:
                pass

        if os.path.basename(str(template_html_path)).lower() == "cuadernillo.html":
            return self._build_daily_sales_cuadernillo_html_template_pdf(
                chrome_exe,
                template_html,
                pdf_path,
                export_date,
                sales_today,
                row_payloads,
                summary,
            )

        def _esc(value):
            return (
                str(value or "")
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        def _money(value):
            try:
                return f"S/ {float(value or 0):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
            except Exception:
                return "S/ 0.00"

        def _fit(text, max_chars):
            value = str(text or "").strip()
            return value[: max_chars - 3] + "..." if len(value) > max_chars and max_chars > 3 else value

        cfg = cargar_configuracion_optica(self.username) or {}
        optica_data = cfg
        optica_name = str(summary.get("optica_name", "") or "Mi Óptica").strip().upper()
        branch_name = str(summary.get("branch_name", "") or "Principal").strip()
        company_ruc = str(cargar_ruc(self.username) or "").strip() or "00000000000"
        company_address = str(optica_data.get("direccion", "") or cfg.get("direccion", "") or "").strip()
        phone = str(optica_data.get("whatsapp", "") or cfg.get("telefono", "") or cfg.get("whatsapp", "") or "").strip()
        email = str(optica_data.get("correo_electronico", "") or cfg.get("correo_electronico", "") or cfg.get("correo", "") or cfg.get("email", "") or "").strip()
        logo_path = cargar_logo_optica(self.username) or str(get_user_file_path(self.username, "logo.png"))

        logo_html = ""
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as logo_file:
                    logo_b64 = base64.b64encode(logo_file.read()).decode("ascii")
                logo_html = (
                    f'<img src="data:image/png;base64,{logo_b64}" '
                    'style="width:100%;height:100%;object-fit:cover;border-radius:50%;" alt="Logo">'
                )
            except Exception:
                logo_html = ""

        generated_at = summary.get("generated_at") or datetime.datetime.now()
        cashier = ""
        commissions_by_vendor = {}
        contract_rows = []
        loose_rows = []
        lab_rows = []
        contract_total = 0.0
        loose_total = 0.0
        contract_count = 0
        loose_count = 0

        def _sale_item_code(item):
            if not isinstance(item, dict):
                return ""
            producto = item.get("producto")
            if isinstance(producto, dict):
                for key in ("codigo", "code", "sku"):
                    value = str(producto.get(key, "") or "").strip()
                    if value:
                        return value
            return str(item.get("codigo", "") or item.get("code", "") or "").strip()

        def _sale_item_name(item):
            if not isinstance(item, dict):
                return "Producto"
            producto = item.get("producto")
            if isinstance(producto, dict):
                for key in ("nombre", "producto", "descripcion"):
                    value = str(producto.get(key, "") or "").strip()
                    if value:
                        return value
            for key in ("nombre", "producto", "descripcion"):
                value = str(item.get(key, "") or "").strip()
                if value:
                    return value
            return "Producto"

        def _sale_item_qty(item):
            try:
                qty = float(item.get("cantidad", 1) or 1) if isinstance(item, dict) else 1.0
            except (TypeError, ValueError):
                qty = 1.0
            return int(qty) if qty.is_integer() else qty

        def _sale_item_price(item):
            if not isinstance(item, dict):
                return 0.0
            try:
                return float(item.get("precio_unitario", item.get("precio", 0)) or 0)
            except (TypeError, ValueError):
                return 0.0

        def _sale_item_total(item):
            if not isinstance(item, dict):
                return 0.0
            try:
                total_item = item.get("total", item.get("subtotal", None))
                if total_item is not None and str(total_item).strip() != "":
                    return float(total_item or 0)
            except (TypeError, ValueError):
                pass
            return round(_sale_item_price(item) * float(item.get("cantidad", 1) or 1), 2)

        def _build_contract_items_row(items):
            items = [item for item in (items or []) if isinstance(item, dict)]
            if not items:
                return ""
            detail_rows = []
            for item in items:
                detalle = _fit(_sale_item_name(item), 32)
                codigo = _fit(_sale_item_code(item) or "-", 14)
                cantidad = _sale_item_qty(item)
                precio_unitario = _sale_item_price(item)
                total_item = _sale_item_total(item)
                detail_rows.append(
                    f"""
                    <tr>
                      <td style="padding:2px 4px;border-top:1px solid #cfcfcf;">{_esc(codigo)}</td>
                      <td style="padding:2px 4px;border-top:1px solid #cfcfcf;">{_esc(detalle)}</td>
                      <td class="center" style="padding:2px 4px;border-top:1px solid #cfcfcf;">{_esc(cantidad)}</td>
                      <td class="right" style="padding:2px 4px;border-top:1px solid #cfcfcf;">{_money(precio_unitario).replace('S/ ', '')}</td>
                      <td class="right" style="padding:2px 4px;border-top:1px solid #cfcfcf;">{_money(total_item).replace('S/ ', '')}</td>
                    </tr>
                    """
                )
            return (
                '<tr class="contract-detail-row">'
                '<td colspan="9" style="padding:0;background:#fafafa;">'
                '<table style="width:100%;border-collapse:collapse;font-size:8px;table-layout:fixed;">'
                '<thead>'
                '<tr>'
                '<th style="width:12%;background:#444;color:#fff;border:1px solid #cfcfcf;padding:2px;font-size:5px;">CODIGO</th>'
                '<th style="width:58%;background:#444;color:#fff;border:1px solid #cfcfcf;padding:2px;font-size:5px;">PRODUCTO</th>'
                '<th style="width:10%;background:#444;color:#fff;border:1px solid #cfcfcf;padding:2px;font-size:5px;">CANT.</th>'
                '<th style="width:10%;background:#444;color:#fff;border:1px solid #cfcfcf;padding:2px;font-size:5px;">P. UNIT.</th>'
                '<th style="width:10%;background:#444;color:#fff;border:1px solid #cfcfcf;padding:2px;font-size:5px;">TOTAL</th>'
                '</tr>'
                '</thead>'
                '<tbody>'
                + "".join(detail_rows)
                + '</tbody>'
                '</table>'
                '</td>'
                '</tr>'
            )

        for idx, sale in enumerate(sales_today, start=1):
            if not isinstance(sale, dict):
                continue
            total_val = float(sale.get("total", 0) or 0)
            monto_pagado = float(sale.get("monto_pagado", total_val) or total_val)
            monto_faltante = float(sale.get("monto_faltante", 0) or 0)
            if monto_faltante < 0:
                monto_faltante = 0.0
            contrato_numero = ""
            if idx - 1 < len(row_payloads):
                contrato_numero = str(row_payloads[idx - 1].get("contrato_numero", "") or "").strip()
            vendedor = (
                str(sale.get("vendedor", "") or "").strip()
                or str(sale.get("optometra", "") or "").strip()
                or str(sale.get("usuario", "") or "").strip()
                or "N/A"
            )
            if not cashier and vendedor and vendedor != "N/A":
                cashier = vendedor

            comision_monto = 0.0
            try:
                if idx - 1 < len(row_payloads):
                    raw_com = str(row_payloads[idx - 1].get("comision", "") or "").replace("S/", "").replace("S/ ", "").strip()
                    comision_monto = float(raw_com or 0)
            except Exception:
                comision_monto = 0.0
            if comision_monto > 0:
                commissions_by_vendor.setdefault(vendedor, {"contracts": 0, "loose": 0, "total": 0.0, "commission": 0.0})
                commissions_by_vendor[vendedor]["commission"] += comision_monto

            if contrato_numero:
                contract_count += 1
                contract_total += total_val
                estado = "Pagado" if monto_faltante <= 0.05 else ("Pendiente" if monto_pagado > 0 else "Debe")
                contract_rows.append(
                    f"""
                    <tr style="background-color: #a7ddff;">
                      <td class="center">{contract_count}</td>
                      <td class="center">{_esc(contrato_numero)}</td>
                      <td>{_esc(_fit(sale.get('paciente_nombre', 'Cliente Genérico'), 34))}</td>
                      <td class="center">Con medida</td>
                      <td class="center">{_esc(vendedor)}</td>
                      <td class="right">{_money(total_val).replace('S/ ', '')}</td>
                      <td class="right">{_money(monto_pagado).replace('S/ ', '')}</td>
                      <td class="right">{_money(monto_faltante).replace('S/ ', '')}</td>
                      <td class="estado">{_esc(estado)}</td>
                    </tr>
                    """
                )
                contract_items = sale.get("items") or []
                if not isinstance(contract_items, (list, tuple)):
                    contract_items = []
                detail_block = _build_contract_items_row(contract_items)
                if detail_block:
                    contract_rows.append(detail_block)
                commissions_by_vendor.setdefault(vendedor, {"contracts": 0, "loose": 0, "total": 0.0, "commission": 0.0})
                commissions_by_vendor[vendedor]["contracts"] += 1
                commissions_by_vendor[vendedor]["total"] += total_val

                # Extraer datos de laboratorio del payload de fila coincidente
                row_values = row_payloads[idx - 1] if idx - 1 < len(row_payloads) else {}
                luna_lab = str(row_values.get("luna_laboratorio", "") or "").strip()
                luna_tipo = str(row_values.get("luna_tipo", "") or "").strip()
                luna_precio_raw = str(row_values.get("luna_costo", "") or "").strip()
                if not luna_lab:
                    luna_lab = "N/A"
                if not luna_tipo:
                    luna_tipo = "N/A"
                luna_precio_text = "N/A"
                try:
                    if luna_precio_raw:
                        luna_precio = float(luna_precio_raw)
                        if luna_precio > 0:
                            luna_precio_text = _money(luna_precio).replace('S/ ', '')
                except Exception:
                    luna_precio_text = "N/A"
                lab_rows.append(
                    f"""
                    <tr>
                      <td class="center">{_esc(contrato_numero)}</td>
                      <td class="center">{_esc(luna_lab)}</td>
                      <td class="center">{_esc(luna_tipo)}</td>
                      <td class="right">{_esc(luna_precio_text)}</td>
                    </tr>
                    """
                )
            else:
                loose_count += 1
                loose_total += total_val
                monto_faltante = float(sale.get("monto_faltante", 0) or 0)
                if monto_faltante < 0:
                    monto_faltante = 0.0
                monto_pagado_loose = float(sale.get("monto_pagado", total_val) or total_val)
                estado_loose = "Pagado" if monto_faltante <= 0.05 else ("Pendiente" if monto_pagado_loose > 0 else "Debe")
                items = sale.get("items") or []
                if not isinstance(items, list):
                    items = []
                detail = ", ".join(
                    f"{str(item.get('nombre') or item.get('producto') or 'Producto').strip()} x{item.get('cantidad', 1)}"
                    for item in items if isinstance(item, dict)
                ) or "Sin detalle"
                metodo = str(sale.get("metodo_pago", "") or "N/A").strip().title()
                loose_rows.append(
                    f"""
                    <tr>
                      <td class="center">{loose_count}</td>
                      <td class="center">{_esc(self._format_order_number(sale.get('numero_orden', '')) if str(sale.get('numero_orden', '') or '').strip() else f'V-{loose_count:03d}')}</td>
                      <td>{_esc(_fit(detail, 58))}</td>
                      <td class="center">{_esc(_fit(sale.get('paciente_nombre', 'Cliente varios'), 16))}</td>
                      <td class="center">{_esc(vendedor)}</td>
                      <td class="center">{_esc(metodo)}</td>
                      <td class="right">{_money(total_val).replace('S/ ', '')}</td>
                      <td class="right">{_money(monto_faltante).replace('S/ ', '')}</td>
                      <td class="estado">{_esc(estado_loose)}</td>
                    </tr>
                    """
                )
                commissions_by_vendor.setdefault(vendedor, {"contracts": 0, "loose": 0, "total": 0.0, "commission": 0.0})
                commissions_by_vendor[vendedor]["loose"] += 1
                commissions_by_vendor[vendedor]["total"] += total_val

        if not contract_rows:
            contract_rows.append('<tr><td colspan="9" class="center">No hubo contratos ópticos en esta fecha.</td></tr>')
        if not loose_rows:
            loose_rows.append('<tr><td colspan="9" class="center">No hubo ventas sueltas en esta fecha.</td></tr>')
        if not lab_rows:
            lab_rows.append('<tr><td colspan="4" class="center">No hubo detalles de laboratorio en esta fecha.</td></tr>')

        commission_rows = []
        for vendedor, data in sorted(commissions_by_vendor.items(), key=lambda pair: pair[1]["total"], reverse=True):
            commission_rows.append(
                f"""
                <tr>
                  <td>{_esc(vendedor)}</td>
                  <td class="center">{int(data['contracts'])}</td>
                  <td class="center">{int(data['loose'])}</td>
                  <td class="right">{_money(data['total']).replace('S/ ', '')}</td>
                  <td class="right">{_money(data['commission']).replace('S/ ', '')}</td>
                </tr>
                """
            )
        if not commission_rows:
            commission_rows.append('<tr><td colspan="5" class="center">No se registraron comisiones en esta fecha.</td></tr>')

        qr_payload = f"{optica_name}|{branch_name}|{export_date.strftime('%d/%m/%Y')}|{summary.get('cantidad_ventas', 0)}|{summary.get('total_hoy', 0)}"
        qr = qrcode.QRCode(border=1, box_size=4)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_b64 = base64.b64encode(qr_buffer.getvalue()).decode("ascii")

        rendered_html = template_html
        rendered_html = rendered_html.replace('<button class="print-btn" onclick="window.print()">Descargar PDF</button>', "")
        rendered_html = re.sub(
            r'<div class="logo">.*?</div>',
            (
                f'<div class="logo">{logo_html}</div>'
                if logo_html
                else '<div class="logo" style="background:transparent;border:none;"></div>'
            ),
            rendered_html,
            count=1,
            flags=re.S,
        )
        # Calcular saldo de caja diaria para inyectar en TOTAL CAJA
        saldo_caja = 0.0
        try:
            from utils.file_handler import cargar_caja
            caja_data = cargar_caja(self.username) or {}
            fecha_str = export_date.strftime("%d/%m/%Y")
            caja_dia = caja_data.get(fecha_str, {})
            
            base_caja = 0.0
            gastos = []
            ingresos_extras = []
            
            if isinstance(caja_dia, dict):
                base_caja = float(caja_dia.get("base", 0.0))
                gastos = caja_dia.get("gastos", [])
                ingresos_extras = caja_dia.get("ingresos_extras", [])
                
            # Calcular ventas en efectivo de hoy
            ventas_efectivo = 0.0
            for sale in sales_today:
                if not isinstance(sale, dict):
                    continue
                detalles = sale.get("metodos_pago_detalle")
                if isinstance(detalles, list) and len(detalles) > 0:
                    for item in detalles:
                        if isinstance(item, dict):
                            m_metodo = str(item.get("metodo", "")).strip().lower()
                            if "efectivo" in m_metodo:
                                try:
                                    ventas_efectivo += float(item.get("monto", 0.0) or 0.0)
                                except Exception:
                                    pass
                else:
                    metodo = str(sale.get("metodo_pago", "")).strip().lower()
                    if "efectivo" in metodo:
                        try:
                            total_venta = float(sale.get("total", 0) or 0)
                            pagado = float(sale.get("monto_pagado", total_venta) or 0)
                            ventas_efectivo += pagado
                        except Exception:
                            pass
                    
            total_egresos = sum(float(g.get("monto", 0.0) or 0.0) for g in gastos if isinstance(g, dict))
            total_otros_ingresos = sum(float(i.get("monto", 0.0) or 0.0) for i in ingresos_extras if isinstance(i, dict))
            
            saldo_caja = base_caja + ventas_efectivo + total_otros_ingresos - total_egresos
        except Exception as e_caja:
            print(f"[REPORTE] Error al obtener saldo de caja para reporte: {e_caja}")

        replacements = {
            "ÓPTICA VISIÓN CENTER": _esc(optica_name),
            "20200200200": _esc(company_ruc),
            "Av. Los Geranios 330 - Lima": _esc(company_address),
            "Tienda Principal": _esc(branch_name),
            "999 888 777 | ventas@optica.com": _esc(" | ".join([part for part in [phone, email] if part]) or "-"),
            "02/06/2026": _esc(export_date.strftime("%d/%m/%Y")),
            "Alex Administrador": _esc(cashier or "N/A"),
            "08:45 PM": _esc(generated_at.strftime("%I:%M %p")),
            "00:00 - 23:59": "00:00 - 23:59",
            "S/ 2,180.00": _money(summary.get("cobrado_total", 0.0)),
            "S/ 870.00": _money(summary.get("pendiente_total", 0.0)),
            "RD01-00000025": f"RD01-{export_date.strftime('%Y%m%d')}",
            "S/ 1,740.00": _money(contract_total),
            "S/ 395.00": _money(loose_total),
            "S/ 105.75": _money(summary.get("total_comisiones", 0.0)),
            "S/ {{TOTAL_CAJA}}": _money(saldo_caja),
            "S/ {{SUMA_TOTAL}}": _money(summary.get("total_hoy", 0.0)),
            "S/ 500.00": _money(saldo_caja),
        }
        for old, new in replacements.items():
            rendered_html = rendered_html.replace(old, new)

        rendered_html = re.sub(
            r'(<div class="card">Contratos ópticos<b>)(.*?)(</b></div>)',
            lambda m: m.group(1) + str(contract_count) + m.group(3),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'(<div class="card">Ventas sueltas<b>)(.*?)(</b></div>)',
            lambda m: m.group(1) + str(loose_count) + m.group(3),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'(<div class="card">Cobrado hoy<b>)(.*?)(</b></div>)',
            lambda m: m.group(1) + _esc(_money(summary.get("cobrado_total", 0.0))) + m.group(3),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'(<div class="card">Debe total<b>)(.*?)(</b></div>)',
            lambda m: m.group(1) + _esc(_money(summary.get("pendiente_total", 0.0))) + m.group(3),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'(<div class="card">Comisiones<b>)(.*?)(</b></div>)',
            lambda m: m.group(1) + _esc(_money(summary.get("total_comisiones", 0.0))) + m.group(3),
            rendered_html,
            count=1,
            flags=re.S,
        )

        rendered_html = re.sub(
            r'<table>\s*<thead>\s*<tr>\s*<th style="width:30px">N°</th>.*?</thead>\s*<tbody>.*?</tbody>\s*</table>',
            lambda m: m.group(0).split("<tbody>")[0] + "<tbody>" + "".join(contract_rows) + "</tbody></table>",
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'<div class="section-title">Ventas sueltas del día</div>\s*<table>.*?<tbody>.*?</tbody>\s*</table>',
            lambda m: re.sub(r'<tbody>.*?</tbody>', "<tbody>" + "".join(loose_rows) + "</tbody>", m.group(0), flags=re.S),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'(<div class="section-title">Ventas sueltas del día</div>\s*<table>\s*<thead>\s*<tr>.*?<th style="width:75px">PAGO</th>\s*)<th style="width:70px">TOTAL</th>',
            r'\1<th style="width:70px">TOTAL</th>\n        <th style="width:70px">DEBE</th>\n        <th style="width:75px">ESTADO</th>',
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'<div class="section-title">Comisiones por vendedor</div>\s*<table>.*?<tbody>.*?</tbody>\s*</table>',
            lambda m: re.sub(r'<tbody>.*?</tbody>', "<tbody>" + "".join(commission_rows) + "</tbody>", m.group(0), flags=re.S),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'<div class="section-title">Detalle de Laboratorio y Lunas \(Contratos\)</div>\s*<table>.*?<tbody>.*?</tbody>\s*</table>',
            lambda m: re.sub(r'<tbody>.*?</tbody>', "<tbody>" + "".join(lab_rows) + "</tbody>", m.group(0), flags=re.S),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'<div class="qr"></div>',
            f'<div class="qr" style="background:none;"><img src="data:image/png;base64,{qr_b64}" style="width:110px;height:110px;display:block;" alt="QR"></div>',
            rendered_html,
            count=1,
        )

        with tempfile.TemporaryDirectory(prefix="viso_ventas_dia_") as temp_dir:
            temp_html_path = os.path.join(temp_dir, f"ventas_dia_{export_date.strftime('%Y%m%d')}.html")
            with open(temp_html_path, "w", encoding="utf-8") as temp_html_file:
                temp_html_file.write(rendered_html)

            subprocess.run(
                [
                    chrome_exe,
                    "--headless=new",
                    "--disable-gpu",
                    "--allow-file-access-from-files",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={os.path.abspath(pdf_path)}",
                    os.path.abspath(temp_html_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=90,
            )
        return True

    def _build_daily_sales_cuadernillo_html_template_pdf(self, chrome_exe, template_html, pdf_path, export_date, sales_today, row_payloads, summary):
        import subprocess
        import tempfile

        def _esc(value):
            return (
                str(value or "")
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        def _money_plain(value):
            try:
                return f"{float(value or 0):.2f}"
            except Exception:
                return "0.00"

        def _sale_code(sale, row_values=None):
            contrato_numero = str((row_values or {}).get("contrato_numero", "") or sale.get("contrato_numero", "") or "").strip()
            if contrato_numero:
                return _esc(contrato_numero)

            order_number = str((row_values or {}).get("numero_orden", "") or sale.get("numero_orden", "") or "").strip()
            if order_number:
                formatted_order = order_number if "-" in order_number else self._format_order_number(order_number)
                return _esc(formatted_order)
            sale_id = str(sale.get("id", "") or "").strip()
            return _esc(sale_id or "-")

        def _sale_detail(sale):
            items = sale.get("items") or []
            if not isinstance(items, (list, tuple)):
                items = []

            parts = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                nombre = str(item.get("nombre") or item.get("producto") or "Producto").strip()
                cantidad = item.get("cantidad", 1)
                if nombre:
                    parts.append(f"{nombre} (x{cantidad})")

            if parts:
                return _esc(", ".join(parts))

            if str(sale.get("tipo_venta", "") or "").strip().lower() == "graduacion":
                return "Servicio de Graduacion"

            return "Sin detalle"

        rendered_html = template_html
        if "@page" not in rendered_html:
            rendered_html = rendered_html.replace(
                "<style>",
                "<style>\n@page{ size:A4 landscape; margin:10mm; }\n",
                1,
            )
        rows_html = []
        for idx, sale in enumerate(sales_today or []):
            row_values = row_payloads[idx] if idx < len(row_payloads or []) and isinstance(row_payloads[idx], dict) else {}
            try:
                total_val = float(sale.get("total", 0) or 0)
            except Exception:
                total_val = 0.0

            try:
                pagado = float(sale.get("monto_pagado", total_val) or total_val)
            except Exception:
                pagado = total_val
            pagado = max(0.0, min(total_val, pagado))

            try:
                faltante = float(sale.get("monto_faltante", 0) or 0)
            except Exception:
                faltante = 0.0
            debe = faltante if faltante > 0.05 else max(0.0, total_val - pagado)

            rows_html.append(
                "<tr>"
                f'<td class="col-codigo">{_sale_code(sale, row_values)}</td>'
                f'<td class="col-nombre">{_esc(sale.get("paciente_nombre", "Cliente Genérico"))}</td>'
                f'<td class="col-detalle">{_sale_detail(sale)}</td>'
                f'<td class="col-precio">{_money_plain(total_val)}</td>'
                f'<td class="col-pago">{_money_plain(pagado)}</td>'
                f'<td class="col-debe">{_money_plain(debe) if debe > 0.05 else ""}</td>'
                "</tr>"
            )

        if not rows_html:
            rows_html.append(
                '<tr><td class="col-codigo">-</td><td class="col-nombre">Sin ventas</td>'
                '<td class="col-detalle">No se registraron operaciones en esta fecha.</td>'
                '<td class="col-precio">0.00</td><td class="col-pago">0.00</td><td class="col-debe"></td></tr>'
            )

        rendered_html = re.sub(
            r'(<div class="fecha">).*?(</div>)',
            lambda m: m.group(1) + _esc(export_date.strftime("%d-%m-%y")) + m.group(2),
            rendered_html,
            count=1,
            flags=re.S,
        )
        rendered_html = re.sub(
            r'(<table class="tabla">\s*<tr>.*?</tr>)(.*?)(</table>)',
            lambda m: m.group(1) + "".join(rows_html) + m.group(3),
            rendered_html,
            count=1,
            flags=re.S,
        )

        gastos_rows_html = (
            "<tr>"
            "<td>Sin gastos registrados</td>"
            '<td class="monto">0.00</td>'
            "</tr>"
        )
        rendered_html = re.sub(
            r'(<div class="gastos">.*?<table>)(.*?)(</table>)',
            lambda m: m.group(1) + gastos_rows_html + m.group(3),
            rendered_html,
            count=1,
            flags=re.S,
        )

        total_venta = float(summary.get("total_hoy", 0) or 0)
        total_abonos = float(summary.get("cobrado_total", 0) or 0)
        total_gastos = 0.0
        total_neto = total_abonos - total_gastos
        total_values = [_money_plain(total_venta), _money_plain(total_abonos), _money_plain(total_gastos), _money_plain(total_neto)]

        def _replace_total(match):
            index = _replace_total.index
            replacement = total_values[index] if index < len(total_values) else match.group(2)
            _replace_total.index += 1
            return match.group(1) + replacement + match.group(3)

        _replace_total.index = 0
        rendered_html = re.sub(
            r'(<span class="valor">)(.*?)(</span>)',
            _replace_total,
            rendered_html,
            count=4,
            flags=re.S,
        )

        with tempfile.TemporaryDirectory(prefix="viso_ventas_cuadernillo_") as temp_dir:
            temp_html_path = os.path.join(temp_dir, f"ventas_cuadernillo_{export_date.strftime('%Y%m%d')}.html")
            with open(temp_html_path, "w", encoding="utf-8") as temp_html_file:
                temp_html_file.write(rendered_html)

            subprocess.run(
                [
                    chrome_exe,
                    "--headless=new",
                    "--disable-gpu",
                    "--allow-file-access-from-files",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={os.path.abspath(pdf_path)}",
                    os.path.abspath(temp_html_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=90,
            )
        return True

    def _build_daily_sales_liquid_template_pdf(self, pdf_path, export_date, sales_today, row_payloads, summary, template_path):
        import base64
        import io
        import subprocess
        import tempfile
        import qrcode
        from utils.file_handler import cargar_configuracion_optica, cargar_datos_optica, cargar_logo_optica

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((path for path in chrome_paths if os.path.exists(path)), None)
        if not chrome_exe:
            return False

        with open(template_path, "r", encoding="utf-8", errors="replace") as tpl_file:
            template_text = tpl_file.read()

        def _money(value):
            try:
                return f"{float(value or 0):.2f}"
            except Exception:
                return "0.00"

        def _safe_float(value):
            try:
                return float(value or 0)
            except Exception:
                return 0.0

        cfg = cargar_configuracion_optica(self.username) or {}
        optica_data = cargar_datos_optica(self.username, prefer_remote=True) or {}
        optica_data = cargar_datos_optica(self.username, prefer_remote=True) or {}
        logo_path = cargar_logo_optica(self.username) or str(get_user_file_path(self.username, "logo.png"))
        logo_data_uri = ""
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as logo_file:
                    logo_b64 = base64.b64encode(logo_file.read()).decode("ascii")
                logo_data_uri = f"data:image/png;base64,{logo_b64}"
            except Exception:
                logo_data_uri = ""

        qr_payload = (
            f"{summary.get('optica_name', '')}|{summary.get('branch_name', '')}|"
            f"{export_date.strftime('%d/%m/%Y')}|{summary.get('cantidad_ventas', 0)}|"
            f"{_money(summary.get('total_hoy', 0))}"
        )
        qr = qrcode.QRCode(border=1, box_size=4)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_data_uri = f"data:image/png;base64,{base64.b64encode(qr_buffer.getvalue()).decode('ascii')}"

        sales_context = []
        contratos_context = []
        ventas_sueltas_context = []
        comisiones_map = {}
        total_contratos = 0.0
        total_ventas_sueltas = 0.0
        total_abonos = 0.0

        for sale, row_values in zip(sales_today, row_payloads):
            pendiente = 0.0
            try:
                total_val = float(sale.get("total", 0) or 0)
                monto_pagado = float(sale.get("monto_pagado", total_val) or total_val)
                monto_faltante = float(sale.get("monto_faltante", 0) or 0)
                pendiente = monto_faltante if monto_faltante > 0 else max(0.0, total_val - monto_pagado)
            except Exception:
                pendiente = 0.0
                total_val = 0.0
                monto_pagado = 0.0

            vendedor = (
                str(sale.get("vendedor", "") or "").strip()
                or str(sale.get("optometra", "") or "").strip()
                or str(sale.get("helper_name", "") or "").strip()
                or "Sin asignar"
            )
            contrato_numero = str(row_values.get("contrato_numero", "") or "").strip()
            es_contrato = bool(contrato_numero)
            detalle = str(row_values.get("articulos", "") or "Sin detalle").replace("\n", ", ")
            cliente = str(row_values.get("cliente", "") or "Cliente")
            pago_metodo = str(row_values.get("metodo", "") or "N/A")
            estado = str(row_values.get("estado", "") or "")
            comision_monto = _safe_float(str(row_values.get("comision", "")).replace("S/.", "").replace("S/", "").strip())

            sales_context.append({
                "numero_orden": str(row_values.get("numero_orden", "") or sale.get("id", "")),
                "cliente": cliente,
                "detalle": detalle,
                "precio": _money(total_val),
                "pago": _money(total_val - pendiente),
                "debe": _money(pendiente) if pendiente > 0.009 else "",
            })

            seller_bucket = comisiones_map.setdefault(vendedor, {
                "vendedor": vendedor,
                "contratos": 0,
                "ventas_sueltas": 0,
                "total_vendido_raw": 0.0,
                "comision_raw": 0.0,
            })
            seller_bucket["total_vendido_raw"] += total_val
            seller_bucket["comision_raw"] += comision_monto

            if es_contrato:
                total_contratos += total_val
                total_abonos += max(0.0, total_val - pendiente)
                seller_bucket["contratos"] += 1
                contratos_context.append({
                    "index": len(contratos_context) + 1,
                    "contrato": contrato_numero,
                    "cliente": cliente,
                    "medida": "Con medida" if str(sale.get("tipo_venta", "") or "").strip().lower() == "graduacion" else "Sin medida",
                    "vendedor": vendedor,
                    "total": _money(total_val),
                    "a_cuenta": _money(max(0.0, total_val - pendiente)),
                    "debe": _money(pendiente),
                    "estado": estado or ("Pendiente" if pendiente > 0.009 else "Pagado"),
                })
            else:
                total_ventas_sueltas += total_val
                seller_bucket["ventas_sueltas"] += 1
                ventas_sueltas_context.append({
                    "index": len(ventas_sueltas_context) + 1,
                    "venta": str(row_values.get("numero_orden", "") or sale.get("id", "")),
                    "detalle": detalle,
                    "cliente": cliente,
                    "vendedor": vendedor,
                    "pago": pago_metodo,
                    "total": _money(total_val),
                })

        gastos_context = []
        metodo_totales = summary.get("metodo_totales", {}) if isinstance(summary.get("metodo_totales"), dict) else {}
        for metodo, monto in sorted(metodo_totales.items(), key=lambda pair: pair[0].lower()):
            if float(monto or 0) <= 0:
                continue
            gastos_context.append({"nombre": str(metodo), "monto": _money(monto)})

        total_hoy = float(summary.get("total_hoy", 0) or 0)
        pendiente_total = float(summary.get("pendiente_total", 0) or 0)
        cobrado_total = float(summary.get("cobrado_total", max(0.0, total_hoy - pendiente_total)) or 0)
        total_gastos = sum(float(item.get("monto", 0) or 0) for item in gastos_context)
        total_neto = cobrado_total - total_gastos
        comisiones_context = []
        for item in sorted(comisiones_map.values(), key=lambda row: row["vendedor"].lower()):
            comisiones_context.append({
                "vendedor": item["vendedor"],
                "contratos": str(item["contratos"]),
                "ventas_sueltas": str(item["ventas_sueltas"]),
                "total_vendido": _money(item["total_vendido_raw"]),
                "comision": _money(item["comision_raw"]),
            })

        context = {
            "report_date_short": export_date.strftime("%d-%m-%y"),
            "report_date": export_date.strftime("%d/%m/%Y"),
            "report_code": f"RD01-{export_date.strftime('%d%m%Y')}",
            "generated_hour": summary.get("generated_at").strftime("%I:%M %p") if summary.get("generated_at") else "",
            "generated_by": str(getattr(self, "username", "") or "Sistema"),
            "report_period": "00:00 - 23:59",
            "optica_name": str(summary.get("optica_name", "") or "Mi Óptica").strip().upper(),
            "branch_name": str(summary.get("branch_name", "") or "Principal").strip(),
            "company_ruc": str(cargar_ruc(self.username) or "").strip() or "00000000000",
            "company_address": str(optica_data.get("direccion", "") or cfg.get("direccion", "") or "").strip(),
            "phone": str(optica_data.get("whatsapp", "") or cfg.get("telefono", "") or cfg.get("whatsapp", "") or "").strip(),
            "email": str(optica_data.get("correo_electronico", "") or cfg.get("correo_electronico", "") or cfg.get("correo", "") or cfg.get("email", "") or "").strip(),
            "logo_data_uri": logo_data_uri,
            "qr_data_uri": qr_data_uri,
            "sales": sales_context,
            "contratos": contratos_context,
            "ventas_sueltas": ventas_sueltas_context,
            "comisiones": comisiones_context,
            "contratos_count": str(len(contratos_context)),
            "ventas_sueltas_count": str(len(ventas_sueltas_context)),
            "gastos": gastos_context,
            "observations": (
                "Este reporte separa contratos ópticos de ventas sueltas. "
                "Los contratos muestran total, a cuenta, saldo pendiente y estado. "
                "Las ventas sueltas se registran como operaciones directas del día."
            ),
            "total_contratos": _money(total_contratos),
            "total_ventas_sueltas": _money(total_ventas_sueltas),
            "total_venta": _money(total_hoy),
            "total_abonos": _money(cobrado_total),
            "total_gastos": _money(total_gastos),
            "total_neto": _money(total_neto),
            "cobrado_total": _money(cobrado_total),
            "pendiente_total": _money(pendiente_total),
            "total_comisiones": _money(summary.get("total_comisiones", 0)),
        }

        rendered_html = render_liquid_template(template_text, context)
        html_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = os.path.join(
            tempfile.gettempdir(),
            f"ventas_dia_{export_date.strftime('%Y%m%d')}_{html_stamp}.html"
        )
        with open(html_path, "w", encoding="utf-8") as html_file:
            html_file.write(rendered_html)

        subprocess.run(
            [
                chrome_exe,
                "--headless",
                "--disable-gpu",
                f"--print-to-pdf={pdf_path}",
                "--print-to-pdf-no-header",
                html_path,
            ],
            check=True,
            timeout=90,
        )
        return os.path.exists(pdf_path)

    def _build_daily_sales_pdf_legacy(self, pdf_path, export_date, active_columns, column_defs, row_payloads, summary, orientation="portrait"):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        page_size = A4 if orientation != "landscape" else landscape(A4)
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=page_size,
            leftMargin=10 * mm,
            rightMargin=10 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )

        styles = getSampleStyleSheet()
        table_header_style = ParagraphStyle(
            "VentasDiaHeaderLegacy",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.white,
            leading=9,
            alignment=1,
        )
        table_cell_style = ParagraphStyle(
            "VentasDiaCellLegacy",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            wordWrap="CJK",
        )
        metodo_lines = "<br/>".join(
            f"- {metodo}: S/. {monto:.2f}"
            for metodo, monto in sorted(summary["metodo_totales"].items(), key=lambda pair: pair[0].lower())
        ) or "- Sin método"

        story = [
            Paragraph("<b>Ventas del día</b>", styles["Title"]),
            Spacer(1, 4 * mm),
            Paragraph(
                f"Fecha: {export_date.strftime('%d/%m/%Y')}<br/>"
                f"Total de ventas: {summary['cantidad_ventas']}<br/>"
                f"Total cobrado del día: S/. {summary['total_hoy']:.2f}<br/>"
                f"Total comisión vendedores: S/. {summary['total_comisiones']:.2f}<br/>"
                f"Métodos de pago usados:<br/>{metodo_lines}",
                styles["Normal"],
            ),
            Spacer(1, 5 * mm),
        ]

        if not row_payloads:
            story.append(Paragraph("No se registraron ventas en esta fecha.", styles["Normal"]))
            doc.build(story)
            return

        formatted_rows = [[Paragraph(str(column_defs[key]["label"]), table_header_style) for key in active_columns]]
        for row_values in row_payloads:
            formatted_rows.append([
                Paragraph(str(row_values.get(key, "")).replace("\n", "<br/>"), table_cell_style)
                for key in active_columns
            ])

        page_width = page_size[0] - (20 * mm)
        total_ratio = sum(column_defs[key]["width"] for key in active_columns) or 1.0
        col_widths = [
            page_width * (column_defs[key]["width"] / total_ratio)
            for key in active_columns
        ]

        table = Table(formatted_rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        doc.build(story)

    def _build_daily_sales_pdf_modern(self, pdf_path, export_date, active_columns, column_defs, row_payloads, summary, orientation="portrait"):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        generated_at = summary["generated_at"]
        optica_name = summary["optica_name"]
        branch_name = summary["branch_name"]
        page_size = A4 if orientation != "landscape" else landscape(A4)
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=page_size,
            leftMargin=11 * mm,
            rightMargin=11 * mm,
            topMargin=13 * mm,
            bottomMargin=14 * mm,
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="DailySalesHeaderMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#4B5563"),
        ))
        styles.add(ParagraphStyle(
            name="DailySalesBranch",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=colors.HexColor("#111111"),
            alignment=1,
        ))
        styles.add(ParagraphStyle(
            name="DailySalesTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#374151"),
            alignment=1,
        ))
        styles.add(ParagraphStyle(
            name="DailySalesCardLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=8.4,
            textColor=colors.HexColor("#6B7280"),
        ))
        styles.add(ParagraphStyle(
            name="DailySalesCardValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=15,
            textColor=colors.HexColor("#111111"),
        ))
        styles.add(ParagraphStyle(
            name="DailySalesCardSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.4,
            textColor=colors.HexColor("#6B7280"),
        ))
        styles.add(ParagraphStyle(
            name="DailySalesTableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.6,
            leading=9,
            alignment=1,
            textColor=colors.HexColor("#111111"),
        ))
        styles.add(ParagraphStyle(
            name="DailySalesCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.4,
            textColor=colors.HexColor("#111111"),
            wordWrap="CJK",
        ))
        styles.add(ParagraphStyle(
            name="DailySalesCellCenter",
            parent=styles["DailySalesCell"],
            alignment=1,
        ))
        styles.add(ParagraphStyle(
            name="DailySalesCellRight",
            parent=styles["DailySalesCell"],
            alignment=2,
        ))
        styles.add(ParagraphStyle(
            name="DailySalesCellTotal",
            parent=styles["DailySalesCellRight"],
            fontName="Helvetica-Bold",
        ))
        styles.add(ParagraphStyle(
            name="DailySalesEmptyTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#111111"),
            alignment=1,
        ))
        styles.add(ParagraphStyle(
            name="DailySalesEmptyText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#6B7280"),
            alignment=1,
        ))

        def metric_card(title, value, subtitle=""):
            content = [
                Paragraph(title, styles["DailySalesCardLabel"]),
                Spacer(1, 1.5 * mm),
                Paragraph(value, styles["DailySalesCardValue"]),
            ]
            if subtitle:
                content.extend([Spacer(1, 1.2 * mm), Paragraph(subtitle, styles["DailySalesCardSub"])])
            card = Table([[content]], colWidths=[None])
            card.setStyle(TableStyle([
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6D6D6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            return card

        def draw_footer(canvas, doc_obj):
            canvas.saveState()
            footer_y = 7 * mm
            canvas.setStrokeColor(colors.HexColor("#D6D6D6"))
            canvas.setLineWidth(0.4)
            canvas.line(doc_obj.leftMargin, footer_y + 5, page_size[0] - doc_obj.rightMargin, footer_y + 5)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#6B7280"))
            canvas.drawString(doc_obj.leftMargin, footer_y, f"Viso | Emitido: {generated_at.strftime('%d/%m/%Y %H:%M:%S')}")
            canvas.drawRightString(page_size[0] - doc_obj.rightMargin, footer_y, f"Página {canvas.getPageNumber()}")
            canvas.restoreState()

        principal_metodo = summary["principal_metodo"]
        metodo_lines = [
            f"{metodo}: S/. {monto:.2f}"
            for metodo, monto in sorted(summary["metodo_totales"].items(), key=lambda pair: pair[1], reverse=True)
            if monto > 0
        ]
        page_width = page_size[0] - doc.leftMargin - doc.rightMargin
        cards_col_width = (page_width - (2 * mm)) / 3.0
        half_col_width = (page_width - (1 * mm)) / 2.0

        story = [
            Paragraph(optica_name, styles["DailySalesBranch"]),
            Spacer(1, 1.5 * mm),
            Paragraph(branch_name, styles["DailySalesTitle"]),
            Spacer(1, 1 * mm),
            Paragraph("Reporte de Ventas del Día", styles["DailySalesTitle"]),
            Spacer(1, 2 * mm),
            Paragraph(
                f"Fecha consultada: {export_date.strftime('%d/%m/%Y')}<br/>"
                f"Generado: {generated_at.strftime('%d/%m/%Y %H:%M:%S')}",
                styles["DailySalesHeaderMeta"],
            ),
            Spacer(1, 4 * mm),
        ]

        first_row_cards = Table([[
            metric_card("Total vendido", f"S/. {summary['total_hoy']:.2f}", "Importe bruto del día"),
            metric_card("Cantidad de ventas", str(summary["cantidad_ventas"]), "Registros encontrados"),
            metric_card("Cobrado", f"S/. {summary['cobrado_total']:.2f}", "Ingreso confirmado"),
        ]], colWidths=[cards_col_width, cards_col_width, cards_col_width])
        first_row_cards.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        second_row_cards = Table([[
            metric_card("Pendiente", f"S/. {summary['pendiente_total']:.2f}", "Monto por cobrar"),
            metric_card(
                "Método principal",
                principal_metodo,
                metodo_lines[0] if metodo_lines else "Sin pagos registrados",
            ),
        ]], colWidths=[half_col_width, half_col_width])
        second_row_cards.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.extend([first_row_cards, Spacer(1, 2 * mm), second_row_cards, Spacer(1, 4 * mm)])

        if not row_payloads:
            empty_box = Table([[
                [
                    Spacer(1, 8 * mm),
                    Paragraph("No se registraron ventas en esta fecha", styles["DailySalesEmptyTitle"]),
                    Spacer(1, 1.5 * mm),
                    Paragraph("El sistema no encontró operaciones para la fecha seleccionada.", styles["DailySalesEmptyText"]),
                    Spacer(1, 8 * mm),
                ]
            ]], colWidths=[page_width])
            empty_box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D6D6D6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(empty_box)
            doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
            return

        total_ratio = sum(column_defs[key]["width"] for key in active_columns) or 1.0
        col_widths = [
            page_width * (column_defs[key]["width"] / total_ratio)
            for key in active_columns
        ]

        def cell_style_for_column(column_key):
            if column_key in {"fecha", "numero_orden", "dni", "metodo", "estado", "contrato_numero", "comision_usuario"}:
                return styles["DailySalesCellCenter"]
            if column_key in {"total", "comision"}:
                return styles["DailySalesCellTotal"]
            return styles["DailySalesCell"]

        formatted_rows = [[Paragraph(str(column_defs[key]["label"]), styles["DailySalesTableHeader"]) for key in active_columns]]
        for row_values in row_payloads:
            formatted_rows.append([
                Paragraph(str(row_values.get(key, "")).replace("\n", "<br/>"), cell_style_for_column(key))
                for key in active_columns
            ])

        table = Table(formatted_rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFEFEF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#CFCFCF")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")]),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D0D0D0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E1E1E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        story.append(Spacer(1, 4 * mm))

        totals_rows = [
            [Paragraph("<b>Resumen final</b>", styles["DailySalesTableHeader"]), ""],
            [Paragraph("Cantidad de ventas", styles["DailySalesCell"]), Paragraph(str(summary["cantidad_ventas"]), styles["DailySalesCellTotal"])],
            [Paragraph("Total vendido", styles["DailySalesCell"]), Paragraph(f"S/. {summary['total_hoy']:.2f}", styles["DailySalesCellTotal"])],
            [Paragraph("Total cobrado", styles["DailySalesCell"]), Paragraph(f"S/. {summary['cobrado_total']:.2f}", styles["DailySalesCellTotal"])],
            [Paragraph("Total pendiente", styles["DailySalesCell"]), Paragraph(f"S/. {summary['pendiente_total']:.2f}", styles["DailySalesCellTotal"])],
        ]
        if "comision" in active_columns and summary["total_comisiones"] > 0:
            totals_rows.append([
                Paragraph("Total comisiones", styles["DailySalesCell"]),
                Paragraph(f"S/. {summary['total_comisiones']:.2f}", styles["DailySalesCellTotal"]),
            ])

        totals_table = Table(totals_rows, colWidths=[page_width * 0.68, page_width * 0.32])
        totals_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F5F5")),
            ("SPAN", (0, 0), (1, 0)),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D0D0D0")),
            ("INNERGRID", (0, 1), (-1, -1), 0.35, colors.HexColor("#E1E1E1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(totals_table)
        doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)

    def _run_pdf_background_job(self, title, label, job_callable, open_on_success=True):
        progress = QtWidgets.QProgressDialog(label, None, 0, 0, self)
        progress.setWindowTitle(title)
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()
        QtWidgets.QApplication.processEvents()

        thread = QtCore.QThread(self)
        worker = _PdfJobWorker(job_callable)
        worker.moveToThread(thread)

        self._pdf_job_thread = thread
        self._pdf_job_worker = worker

        def _finish(path, error):
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
            self._pdf_job_thread = None
            self._pdf_job_worker = None

            if error:
                QMessageBox.critical(self, title, f"No se pudo generar el PDF.\n\n{error}")
                return
            if open_on_success and path:
                try:
                    open_pdf_with_chrome(path)
                except Exception as open_error:
                    QMessageBox.critical(self, title, f"El PDF se generó, pero no se pudo abrir.\n\n{open_error}")

        thread.started.connect(worker.run)
        worker.finished.connect(_finish)
        worker.finished.connect(lambda *_args: _orphan_qthread(thread))
        thread.start()

    def _export_today_sales_pdf(self, options=None):
        options = options or {}
        orientation = str(options.get("orientation") or "portrait").strip().lower()
        all_sales = getattr(self, "_all_sales", None)
        if all_sales is None:
            all_sales = cargar_ventas(self.username)
        export_date = options.get("_export_date") or datetime.date.today()
        prefiltered_sales = options.get("_sales_override")
        sales_today = []

        if isinstance(prefiltered_sales, list):
            sales_today = [sale for sale in prefiltered_sales if isinstance(sale, dict)]
        else:
            today_key = (export_date.year * 10000) + (export_date.month * 100) + export_date.day
            for sale in (all_sales or []):
                if not isinstance(sale, dict):
                    continue
                key = int(sale.get("_viso_date_key", 0) or 0)
                if not key:
                    try:
                        sale_date = datetime.datetime.strptime(
                            sale.get("fecha", "").split()[0],
                            "%d/%m/%Y"
                        ).date()
                        if sale_date == export_date:
                            sales_today.append(sale)
                    except Exception:
                        continue
                elif key == today_key:
                    sales_today.append(sale)

        pacientes_lookup = {}
        try:
            for paciente in (cargar_pacientes(self.username) or []):
                if not isinstance(paciente, dict):
                    continue
                dni_key = str(paciente.get("dni", "")).strip()
                if dni_key:
                    pacientes_lookup[dni_key] = paciente
        except Exception:
            pacientes_lookup = {}

        total_hoy = 0.0
        total_comisiones = 0.0
        metodo_totales = {}
        pendiente_total = 0.0
        column_defs = {
            "fecha": {"label": "Fecha", "width": 0.14},
            "numero_orden": {"label": "N° Orden", "width": 0.10},
            "dni": {"label": "DNI", "width": 0.10},
            "cliente": {"label": "Cliente", "width": 0.18},
            "articulos": {"label": "Artículos", "width": 0.26},
            "metodo": {"label": "Método", "width": 0.10},
            "estado": {"label": "Estado", "width": 0.12},
            "total": {"label": "Total", "width": 0.10},
            "contrato_numero": {"label": "N° Contrato", "width": 0.11},
            "comision": {"label": "Comisión", "width": 0.10},
            "comision_usuario": {"label": "Beneficiario Comisión", "width": 0.16},
        }
        active_columns = [
            key for key in (options.get("columns") or ["fecha", "numero_orden", "dni", "cliente", "articulos", "metodo", "estado", "total", "contrato_numero"])
            if key in column_defs
        ]
        if not active_columns:
            active_columns = ["fecha", "articulos", "total"]

        row_payloads = []

        def _sale_commission_value(sale):
            """Extrae la comisión desde distintas claves posibles de la venta."""
            if not isinstance(sale, dict):
                return 0.0
            for key in ("comision_monto", "comision", "commission", "comision_total"):
                raw_value = sale.get(key, None)
                if raw_value is None:
                    continue
                try:
                    text = str(raw_value).replace("S/.", "").replace("S/", "").replace("S ", "").strip()
                    if not text:
                        continue
                    return float(text)
                except (TypeError, ValueError):
                    continue
            return 0.0

        for sale in sales_today:
            try:
                total_val = float(sale.get("total", 0) or 0)
            except Exception:
                total_val = 0.0
            total_hoy += total_val
            metodo_normalizado = str(sale.get("metodo_pago", "N/A") or "N/A").strip().title()
            metodo_totales[metodo_normalizado] = float(metodo_totales.get(metodo_normalizado, 0.0) or 0.0) + total_val

            items = sale.get("items") or []
            if not isinstance(items, (list, tuple)):
                items = []
            parts = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                nombre = item.get("nombre", item.get("producto", "Producto"))
                cantidad = item.get("cantidad", 1)
                parts.append(f"{nombre} (x{cantidad})")
            items_str = "\n".join(parts) or "Sin detalle"

            es_pago_parcial = sale.get('es_pago_parcial', False) or sale.get('es_pago_partes', False)
            monto_faltante = float(sale.get('monto_faltante', 0) or 0)
            pagado = float(sale.get('monto_pagado', total_val) or total_val)
            pendiente = monto_faltante if es_pago_parcial and monto_faltante > 0 else (total_val - pagado)
            if pendiente > 0:
                pendiente_total += pendiente
            if pendiente > 0.05:
                estado = f"Por cobrar S/. {pendiente:.2f}" if pagado > 0 else "No pagado"
            else:
                estado = "Cobrado"

            comision_monto = _sale_commission_value(sale)
            comision_usuario = str(sale.get("comision_usuario", "") or "").strip()
            if not comision_usuario:
                comision_usuario = (
                    str(sale.get("vendedor", "") or "").strip()
                    or str(sale.get("optometra", "") or "").strip()
                    or str(sale.get("helper_name", "") or "").strip()
                    or str(sale.get("usuario", "") or "").strip()
                )
            contrato_numero = str(sale.get("contrato_numero", "") or "").strip()
            matched_grad = None

            if comision_monto <= 0 or not contrato_numero:
                paciente = pacientes_lookup.get(str(sale.get("paciente_dni", "")).strip())
                historial = paciente.get("historial_graduaciones", []) if isinstance(paciente, dict) else []
                venta_id = str(sale.get("id", "")).strip()
                sale_fecha = str(sale.get("fecha", "") or "").strip()
                sale_fecha_corta = sale_fecha.split()[0] if sale_fecha else ""
                sale_optometra = str(sale.get("optometra", "") or "").strip().lower()
                matched_grad = None

                for grad in historial if isinstance(historial, list) else []:
                    if not isinstance(grad, dict):
                        continue
                    grad_venta_id = str(grad.get("venta_relacionada_id", "")).strip()
                    if venta_id and grad_venta_id and grad_venta_id == venta_id:
                        matched_grad = grad
                        break
                if matched_grad is None:
                    for grad in historial if isinstance(historial, list) else []:
                        if not isinstance(grad, dict):
                            continue
                        grad_fecha = str(grad.get("fecha", "") or "").strip()
                        grad_optometra = str(grad.get("optometra", "") or "").strip().lower()
                        try:
                            grad_monto = float(grad.get("monto_cobrado", 0) or 0)
                        except Exception:
                            grad_monto = 0.0
                        if (
                            grad_fecha == sale_fecha_corta
                            and abs(grad_monto - total_val) <= 0.05
                            and (not sale_optometra or grad_optometra == sale_optometra)
                        ):
                            matched_grad = grad
                            break
                if matched_grad is not None:
                    if comision_monto <= 0:
                        comision_monto = float(matched_grad.get("comision_monto", 0) or 0)
                    if not comision_usuario:
                        comision_usuario = (
                            str(matched_grad.get("comision_usuario", "") or "").strip()
                            or str(matched_grad.get("optometra", "") or "").strip()
                            or str(matched_grad.get("vendedor", "") or "").strip()
                        )
                    if not contrato_numero:
                        contrato_numero = str(matched_grad.get("contrato_numero", "") or "").strip()
            if comision_monto > 0:
                total_comisiones += comision_monto

            row_values = {
                "fecha": str(sale.get("fecha", "")),
                "numero_orden": self._format_order_number(sale.get("numero_orden", "")) if str(sale.get("numero_orden", "") or "").strip() else "",
                "dni": str(sale.get("paciente_dni", "")),
                "cliente": str(sale.get("paciente_nombre", "Cliente Genérico")),
                "articulos": items_str,
                "metodo": metodo_normalizado,
                "estado": estado,
                "total": f"S/. {total_val:.2f}",
                "contrato_numero": contrato_numero,
                "comision": f"S/. {comision_monto:.2f}" if comision_monto > 0 else "",
                "comision_usuario": comision_usuario,
                "luna_tipo": str(matched_grad.get("luna_tipo", "") or "").strip() if matched_grad else "",
                "luna_laboratorio": str(matched_grad.get("luna_laboratorio", "") or "").strip() if matched_grad else "",
                "luna_costo": str(matched_grad.get("luna_costo", "") or "").strip() if matched_grad else "",
            }
            row_payloads.append(row_values)

        temp_dir = os.path.join("VISO", str(self.username), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        pdf_path = os.path.join(
            temp_dir,
            f"ventas_dia_{export_date.strftime('%Y%m%d')}.pdf"
        )
        summary = {
            "generated_at": datetime.datetime.now(),
            **self._get_daily_sales_report_header_context(),
            "cantidad_ventas": len(sales_today),
            "total_hoy": total_hoy,
            "total_comisiones": total_comisiones,
            "metodo_totales": metodo_totales,
            "pendiente_total": max(0.0, pendiente_total),
            "cobrado_total": max(0.0, total_hoy - max(0.0, pendiente_total)),
            "principal_metodo": max(metodo_totales.items(), key=lambda pair: pair[1])[0] if metodo_totales else "Sin método",
        }

        def _job():
            used_html_template = False
            try:
                used_html_template = self._build_daily_sales_html_template_pdf(
                    pdf_path,
                    export_date,
                    sales_today,
                    row_payloads,
                    summary,
                )
            except Exception:
                used_html_template = False

            if not used_html_template:
                if USE_MODERN_DAILY_SALES_PDF_LAYOUT:
                    self._build_daily_sales_pdf_modern(
                        pdf_path,
                        export_date,
                        active_columns,
                        column_defs,
                        row_payloads,
                        summary,
                        orientation=orientation,
                    )
                else:
                    self._build_daily_sales_pdf_legacy(
                        pdf_path,
                        export_date,
                        active_columns,
                        column_defs,
                        row_payloads,
                        summary,
                        orientation=orientation,
                    )
            return pdf_path

        self._run_pdf_background_job(
            "Ventas del día",
            "Generando PDF de ventas del día...",
            _job,
            open_on_success=True,
        )

    def _export_day_sales_pdf(self, target_date, options=None):
        options = options or {}
        all_sales = getattr(self, "_all_sales", None)
        if all_sales is None:
            all_sales = cargar_ventas(self.username)

        target_key = (target_date.year * 10000) + (target_date.month * 100) + target_date.day
        sales_for_day = []

        for sale in (all_sales or []):
            if not isinstance(sale, dict):
                continue
            key = int(sale.get("_viso_date_key", 0) or 0)
            if not key:
                try:
                    sale_date = datetime.datetime.strptime(
                        sale.get("fecha", "").split()[0],
                        "%d/%m/%Y"
                    ).date()
                    if sale_date == target_date:
                        sales_for_day.append(sale)
                except Exception:
                    continue
            elif key == target_key:
                sales_for_day.append(sale)

        export_options = dict(options)
        export_options["_sales_override"] = sales_for_day
        export_options["_export_date"] = target_date
        self._export_today_sales_pdf(export_options)

    def _apply_text_date_filter(self):
        return saleshistory_apply_text_date_filter(self)

    def filter_by_dates(self):
        return saleshistory_filter_by_dates(self)

    def _on_payment_method_changed(self, text):
        return saleshistory_on_payment_method_changed(self, text)

    def _on_sales_selection_changed(self):
        return saleshistory_on_sales_selection_changed(self)

    def show_all_sales_history(self):
        return saleshistory_show_all_sales_history(self)

    def toggle_compare_mode(self):
        return saleshistory_toggle_compare_mode(self)

    def _mass_action_change_date(self):
        return saleshistory_mass_action_change_date(self)

    def update_sales_history_table(self, sales):
        return saleshistory_update_sales_history_table(self, sales)

    def _update_sales_history_table_chunked(self, sales):
        return saleshistory_update_sales_history_table_chunked(self, sales)

    def _cancel_sales_fill(self):
        return saleshistory_cancel_sales_fill(self)

    def _sales_fill_in_progress(self) -> bool:
        return saleshistory_sales_fill_in_progress(self)

    def _fill_sales_chunk(self):
        return saleshistory_fill_sales_chunk(self)

    def _render_sale_row_fast(self, i: int, sale: dict):
        return saleshistory_render_sale_row_fast(self, i, sale)

    def _on_sales_table_cell_clicked(self, row: int, col: int):
        return salespage_on_sales_table_cell_clicked(self, row, col)

    def eliminar_venta(self, sale):
        return salespage_eliminar_venta(self, sale)

    def show_sale_options(self, sale):
        return salespage_show_sale_options(self, sale)
