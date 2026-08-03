import sys
import os
import datetime
import csv
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QHeaderView,
    QAbstractItemView, QTableWidgetItem, QHBoxLayout, QFrame,
    QDateEdit, QLineEdit, QPushButton, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor, QFont, QBrush
from PyQt5 import QtCore

# Importaciones para el entorno de desarrollo y empaquetado
from utils.file_handler import cargar_kardex

_ORPHAN_QTHREADS = []
logger = logging.getLogger(__name__)


def _orphan_qthread(thread) -> None:
    """Evita crash al destruir widgets: mantiene vivo el QThread hasta que termine."""
    if thread is None:
        return
    try:
        for t in _ORPHAN_QTHREADS:
            if t is thread:
                return
    except Exception:
        pass
    try:
        thread.setParent(None)
    except Exception:
        pass
    try:
        _ORPHAN_QTHREADS.append(thread)
    except Exception:
        return

    def _cleanup():
        try:
            _ORPHAN_QTHREADS.remove(thread)
        except Exception:
            pass
        try:
            thread.deleteLater()
        except Exception:
            pass

    try:
        thread.finished.connect(_cleanup)
    except Exception:
        pass


class _KardexLoaderWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(list, str)

    def __init__(self, username: str):
        super().__init__()
        self._username = username

    @staticmethod
    def _date_key_from_fecha(fecha_str: str) -> int:
        """Convierte 'DD/MM/YYYY ...' a llave int YYYYMMDD para filtrar rÃ¡pido."""
        try:
            s = str(fecha_str or "").strip()
            if not s:
                return 0
            date_part = s.split(" ")[0]
            dd, mm, yy = date_part.split("/")
            return (int(yy) * 10000) + (int(mm) * 100) + int(dd)
        except Exception:
            return 0

    @staticmethod
    def _sort_key_from_fecha(fecha_str: str) -> int:
        """Llave int YYYYMMDDHHMMSS para ordenar desc sin strptime."""
        try:
            s = str(fecha_str or "").strip()
            if not s:
                return 0
            s = s.split(".")[0]
            parts = s.split(" ")
            date_part = parts[0] if parts else ""
            time_part = parts[1] if len(parts) > 1 else "00:00:00"
            dd, mm, yy = date_part.split("/")
            hh, mi, ss = (time_part.split(":") + ["0", "0", "0"])[:3]
            return (
                (int(yy) * 10000000000)
                + (int(mm) * 100000000)
                + (int(dd) * 1000000)
                + (int(hh) * 10000)
                + (int(mi) * 100)
                + int(ss)
            )
        except Exception:
            return 0

    @QtCore.pyqtSlot()
    def run(self):
        try:
            data = cargar_kardex(self._username)
            if not isinstance(data, list):
                data = []

            for e in data:
                if not isinstance(e, dict):
                    continue
                if "_viso_kardex_date_key" not in e:
                    e["_viso_kardex_date_key"] = self._date_key_from_fecha(e.get("fecha"))
                if "_viso_kardex_sort_key" not in e:
                    e["_viso_kardex_sort_key"] = self._sort_key_from_fecha(e.get("fecha"))
                if "_viso_kardex_prod_lower" not in e:
                    e["_viso_kardex_prod_lower"] = str(e.get("producto", "") or "").lower()

            try:
                data.sort(key=lambda x: int(x.get("_viso_kardex_sort_key", 0) or 0), reverse=True)
            except Exception:
                pass

            self.finished.emit(data, "")
        except Exception as e:
            self.finished.emit([], str(e))

class KardexPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = parent.username # <-- Obtener el nombre de usuario de la ventana principal
        self.setObjectName("MainContent")
        self.all_kardex_data = [] # Almacenar todos los datos cargados
        self._kardex_load_thread = None
        self._kardex_load_worker = None
        self._kardex_fill_timer = None
        self._kardex_fill_data = []
        self._kardex_fill_pos = 0
        self._kardex_fill_chunk_size = 40
        self._is_closing = False
        self.setup_ui()
        # Cargar en background solo cuando la pÃ¡gina ya estÃ¡ en pantalla (evita crashes si se descarga rÃ¡pido).
        self._kardex_autoload_scheduled = False

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_is_closing", False):
            return
        if not getattr(self, "_kardex_autoload_scheduled", False):
            self._kardex_autoload_scheduled = True
            try:
                QTimer.singleShot(0, self.update_kardex_table)
            except Exception:
                self.update_kardex_table()

    def closeEvent(self, event):
        self._is_closing = True
        self._cleanup_async()
        try:
            super().closeEvent(event)
        except Exception:
            pass

    def event(self, event):
        # deleteLater() genera DeferredDelete; limpiamos threads/timers antes que Qt destruya el objeto.
        try:
            if event is not None and int(event.type()) == int(QtCore.QEvent.DeferredDelete):
                self._is_closing = True
                self._cleanup_async()
        except Exception:
            pass
        return super().event(event)

    def _cleanup_async(self):
        self._cancel_kardex_fill()
        t = getattr(self, "_kardex_load_thread", None)
        if t is not None:
            try:
                if t.isRunning():
                    t.quit()
                    t.wait(200)
            except Exception:
                pass
            # Fallback seguro: si sigue vivo, "huÃ©rfano" para que no crashee al destruir el widget.
            try:
                if hasattr(t, "isRunning") and t.isRunning():
                    _orphan_qthread(t)
            except Exception:
                pass
        self._kardex_load_thread = None
        self._kardex_load_worker = None

    # Compat: llamado por main_window al descargar pÃ¡ginas
    def _cleanup_all_threads(self):
        return self._cleanup_async()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título mejorado
        title = QLabel("📊 Kardex de Inventario")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # --- SECCIÓN DE FILTROS ---
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 10, 15, 10)
        filter_layout.setSpacing(15)

        # Filtro de Fechas
        lbl_from = QLabel("Desde:")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30)) # Últimos 30 días por defecto
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        
        lbl_to = QLabel("Hasta:")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd/MM/yyyy")

        # Búsqueda de Producto
        lbl_search = QLabel("Producto:")
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por nombre...")
        self.txt_search.setMinimumWidth(200)

        # Botones
        self.btn_filter = QPushButton("🔍 Filtrar")
        self.btn_filter.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        self.btn_filter.clicked.connect(self.apply_filters)

        self.btn_export = QPushButton("📥 Exportar Excel")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #388E3C;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2E7D32;
            }
        """)
        self.btn_export.clicked.connect(self.export_to_excel)

        # Agregar widgets al layout de filtros
        filter_layout.addWidget(lbl_from)
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(lbl_to)
        filter_layout.addWidget(self.date_to)
        filter_layout.addWidget(lbl_search)
        filter_layout.addWidget(self.txt_search)
        filter_layout.addWidget(self.btn_filter)
        filter_layout.addStretch() # Espacio flexible
        filter_layout.addWidget(self.btn_export)

        layout.addWidget(filter_frame)
        # ---------------------------

        self.status_label = QLabel("Cargando kardex...")
        self.status_label.setStyleSheet("color:#6B7280; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Tabla mejorada
        self.tree_kardex = QTableWidget()
        self.tree_kardex.setColumnCount(6)
        self.tree_kardex.setHorizontalHeaderLabels(["📅 Fecha", "🔄 Movimiento", "📦 Producto", "📊 Cantidad", "💰 Costo Total", "📈 Stock Final"])
        
        # Configurar estilo de encabezado
        header = self.tree_kardex.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #0D47A1;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
        # Configurar tabla
        self.tree_kardex.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_kardex.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_kardex.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree_kardex.setAlternatingRowColors(True)
        self.tree_kardex.setStyleSheet("""
            QTableWidget {
                gridline-color: #E0E0E0;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F0F0F0;
            }
            QTableWidget::item:selected {
                background-color: #BBDEFB;
                color: #0D47A1;
            }
            QTableWidget::item:hover {
                background-color: #E3F2FD;
            }
            /* Filas alternadas */
            QTableWidget::item:alternate {
                background-color: #F9F9F9;
            }
        """)
        
        # Altura de filas
        self.tree_kardex.verticalHeader().setDefaultSectionSize(35)
        
        layout.addWidget(self.tree_kardex)

    def update_kardex_table(self):
        """Carga el kardex en background para evitar 'No responde'."""
        self._reload_kardex_async()

    def _reload_kardex_async(self):
        if getattr(self, "_is_closing", False):
            return
        if not getattr(self, "username", None):
            self.all_kardex_data = []
            self.apply_filters()
            return

        self._stop_kardex_loader()
        self._cancel_kardex_fill()

        try:
            self.status_label.setText("Cargando kardex...")
        except Exception:
            pass

        # Importante: NO parentear el QThread al widget, porque si el widget se destruye
        # mientras el thread estÃ¡ corriendo, Qt puede abortar el proceso.
        self._kardex_load_thread = QtCore.QThread()
        _orphan_qthread(self._kardex_load_thread)
        self._kardex_load_worker = _KardexLoaderWorker(self.username)
        self._kardex_load_worker.moveToThread(self._kardex_load_thread)
        self._kardex_load_thread.started.connect(self._kardex_load_worker.run)
        self._kardex_load_worker.finished.connect(self._on_kardex_loaded)
        self._kardex_load_worker.finished.connect(self._kardex_load_thread.quit)
        self._kardex_load_worker.finished.connect(self._kardex_load_worker.deleteLater)
        self._kardex_load_thread.start()

    def _stop_kardex_loader(self):
        t = getattr(self, "_kardex_load_thread", None)
        if t is not None:
            try:
                t.quit()
            except Exception:
                pass
        self._kardex_load_thread = None
        self._kardex_load_worker = None

    def _on_kardex_loaded(self, data: list, error: str):
        if getattr(self, "_is_closing", False):
            return
        self.all_kardex_data = data if isinstance(data, list) else []
        try:
            if error:
                self.status_label.setText(f"Error cargando kardex: {error}")
            else:
                self.status_label.setText(f"Registros: {len(self.all_kardex_data)}")
        except Exception:
            pass

        try:
            self.apply_filters()
        except Exception:
            self.populate_table(self.all_kardex_data)

    def apply_filters(self):
        """Filtra los datos según los controles y actualiza la tabla."""
        start_date = self.date_from.date()
        end_date = self.date_to.date()
        # Ajustar end_date para incluir todo el día (hasta 23:59:59)
        end_date_py = end_date.toPyDate()
        start_date_py = start_date.toPyDate()

        search_text = self.txt_search.text().lower().strip()
        
        start_key = (start_date_py.year * 10000) + (start_date_py.month * 100) + start_date_py.day
        end_key = (end_date_py.year * 10000) + (end_date_py.month * 100) + end_date_py.day

        filtered_data = []
        for entry in (self.all_kardex_data or []):
            if not isinstance(entry, dict):
                continue

            # 1. Filtro de Producto (Búsqueda)
            prod_name = str(entry.get("_viso_kardex_prod_lower", "") or "")
            if not prod_name:
                prod_name = str(entry.get("producto", "") or "").lower()
            if search_text and search_text not in prod_name:
                continue

            # 2. Filtro de Fechas (comparación por llave int, sin strptime)
            key = int(entry.get("_viso_kardex_date_key", 0) or 0)
            if not key:
                key = _KardexLoaderWorker._date_key_from_fecha(entry.get("fecha"))
            if key and not (start_key <= key <= end_key):
                continue

            filtered_data.append(entry)
        
        self.populate_table(filtered_data)

    def populate_table(self, data):
        """Llena la tabla con los datos proporcionados (no-bloqueante)."""
        return self._populate_table_chunked(data)
        self.tree_kardex.setRowCount(0)
        
        for i, entry in enumerate(data):
            self.tree_kardex.insertRow(i)
            
            # Fecha
            fecha_item = QTableWidgetItem(entry.get('fecha', ''))
            fecha_item.setFont(self._get_font(10))
            self.tree_kardex.setItem(i, 0, fecha_item)
            
            # Movimiento con color
            movimiento = entry.get('movimiento', '')
            movimiento_item = QTableWidgetItem(f"▼ {movimiento}" if str(movimiento).lower().startswith("salida") else f"▲ {movimiento}")
            movimiento_font = QFont()
            movimiento_font.setBold(True)
            movimiento_item.setFont(movimiento_font)
            
            # Colorear según tipo de movimiento
            if str(movimiento).lower().startswith("salida"):
                movimiento_item.setForeground(QBrush(QColor("#D32F2F")))  # Rojo para salidas
            elif str(movimiento).lower().startswith("entrada"):
                movimiento_item.setForeground(QBrush(QColor("#388E3C")))  # Verde para entradas
            else:
                movimiento_item.setForeground(QBrush(QColor("#F57C00")))  # Naranja para otros
            
            self.tree_kardex.setItem(i, 1, movimiento_item)
            
            # Producto
            producto_item = QTableWidgetItem(entry.get('producto', ''))
            producto_item.setFont(self._get_font(10))
            self.tree_kardex.setItem(i, 2, producto_item)
            
            # Cantidad (centrada)
            cantidad_item = QTableWidgetItem(str(entry.get('cantidad', '')))
            cantidad_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            cantidad_font = QFont()
            cantidad_font.setBold(True)
            cantidad_item.setFont(cantidad_font)
            self.tree_kardex.setItem(i, 3, cantidad_item)
            
            # Costo Total (alineado a la derecha)
            try:
                # Usar valor_total si existe, sino recalcular con fallback
                if 'valor_total' in entry:
                    valor_total = float(entry['valor_total'])
                else:
                    cantidad = entry.get('cantidad', 0)
                    cantidad_num = float(cantidad) if cantidad else 0
                    precio = float(entry.get('costo_unitario', entry.get('precio', entry.get('costo', 0))) or 0)
                    valor_total = cantidad_num * precio
            except (ValueError, TypeError):
                valor_total = 0.0
            
            costo_item = QTableWidgetItem(f"S/{valor_total:.2f}")
            costo_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            costo_font = QFont()
            costo_font.setBold(True)
            costo_item.setFont(costo_font)
            self.tree_kardex.setItem(i, 4, costo_item)
            
            # Stock Final (centrado y remarcado)
            stock_final = entry.get('stock_final', '')
            stock_item = QTableWidgetItem(str(stock_final))
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stock_font = QFont()
            stock_font.setBold(True)
            stock_item.setFont(stock_font)
            
            # Colorear stock según nivel
            try:
                stock_num = int(stock_final)
                if stock_num <= 5:
                    stock_item.setForeground(QBrush(QColor("#D32F2F")))  # Rojo crítico
                    stock_item.setBackground(QBrush(QColor("#FFEBEE")))
                elif stock_num <= 10:
                    stock_item.setForeground(QBrush(QColor("#F57C00")))  # Naranja bajo
                    stock_item.setBackground(QBrush(QColor("#FFF3E0")))
                else:
                    stock_item.setForeground(QBrush(QColor("#388E3C")))  # Verde normal
            except:
                pass
            
            self.tree_kardex.setItem(i, 5, stock_item)

    def _populate_table_chunked(self, data):
        self._cancel_kardex_fill()
        self.tree_kardex.setRowCount(0)
        try:
            self.tree_kardex.setSortingEnabled(False)
        except Exception:
            pass

        self._kardex_fill_data = list(data) if isinstance(data, (list, tuple)) else []
        self._kardex_fill_pos = 0
        self._kardex_fill_chunk_size = 40 if len(self._kardex_fill_data) <= 2000 else 18

        if not self._kardex_fill_data:
            try:
                self.status_label.setText("No hay registros para el filtro.")
            except Exception:
                pass
            return

        self._fill_kardex_chunk()
        if self._kardex_fill_pos < len(self._kardex_fill_data):
            self._kardex_fill_timer = QTimer(self)
            self._kardex_fill_timer.timeout.connect(self._fill_kardex_chunk)
            self._kardex_fill_timer.start(10)

    def _cancel_kardex_fill(self):
        timer = getattr(self, "_kardex_fill_timer", None)
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
            try:
                timer.deleteLater()
            except Exception:
                pass
        self._kardex_fill_timer = None
        self._kardex_fill_data = []
        self._kardex_fill_pos = 0
        self._kardex_fill_chunk_size = 40

    def _fill_kardex_chunk(self):
        if getattr(self, "_is_closing", False):
            try:
                self._cancel_kardex_fill()
            except Exception:
                pass
            return

        try:
            chunk_size = int(getattr(self, "_kardex_fill_chunk_size", 40) or 40)
            data = getattr(self, "_kardex_fill_data", []) or []
            pos = int(getattr(self, "_kardex_fill_pos", 0) or 0)
            if pos >= len(data):
                timer = getattr(self, "_kardex_fill_timer", None)
                if timer is not None:
                    try:
                        timer.stop()
                    except Exception:
                        pass
                    self._kardex_fill_timer = None
                return

            end = min(pos + chunk_size, len(data))
            try:
                self.tree_kardex.setUpdatesEnabled(False)
            except Exception:
                pass

            try:
                current_rows = int(self.tree_kardex.rowCount() or 0)
                missing = int(end) - current_rows
                for _ in range(max(0, missing)):
                    self.tree_kardex.insertRow(current_rows)
                    current_rows += 1
            except Exception:
                pass

            for i in range(pos, end):
                entry = data[i]
                if isinstance(entry, dict):
                    try:
                        self._render_kardex_row(i, entry)
                    except Exception:
                        logger.exception("[KARDEX] Error renderizando fila %s", i)

            self._kardex_fill_pos = end
            try:
                self.tree_kardex.setUpdatesEnabled(True)
            except Exception:
                pass
        except Exception:
            logger.exception("[KARDEX] Error en _fill_kardex_chunk()")
            try:
                self._cancel_kardex_fill()
            except Exception:
                pass
            try:
                self.tree_kardex.setUpdatesEnabled(True)
            except Exception:
                pass

    def _render_kardex_row(self, i: int, entry: dict):
        fecha_item = QTableWidgetItem(str(entry.get("fecha", "") or ""))
        self.tree_kardex.setItem(i, 0, fecha_item)

        movimiento = str(entry.get("movimiento", "") or "")
        es_salida = movimiento.lower().startswith("salida")
        movimiento_item = QTableWidgetItem(f"▼ {movimiento}" if es_salida else f"▲ {movimiento}")
        movimiento_font = QFont()
        movimiento_font.setBold(True)
        movimiento_item.setFont(movimiento_font)
        if es_salida:
            movimiento_item.setForeground(QBrush(QColor("#D32F2F")))
        elif movimiento.lower().startswith("entrada"):
            movimiento_item.setForeground(QBrush(QColor("#388E3C")))
        else:
            movimiento_item.setForeground(QBrush(QColor("#F57C00")))
        self.tree_kardex.setItem(i, 1, movimiento_item)

        self.tree_kardex.setItem(i, 2, QTableWidgetItem(str(entry.get("producto", "") or "")))

        cantidad_item = QTableWidgetItem(str(entry.get("cantidad", "") or ""))
        cantidad_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tree_kardex.setItem(i, 3, cantidad_item)

        try:
            if "valor_total" in entry:
                valor_total = float(entry.get("valor_total") or 0)
            else:
                cantidad_num = float(entry.get("cantidad", 0) or 0)
                precio = float(entry.get("costo_unitario", entry.get("precio", entry.get("costo", 0))) or 0)
                valor_total = cantidad_num * precio
        except Exception:
            valor_total = 0.0
        costo_item = QTableWidgetItem(f"S/{valor_total:.2f}")
        costo_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tree_kardex.setItem(i, 4, costo_item)

        stock_final = entry.get("stock_final", "")
        stock_item = QTableWidgetItem(str(stock_final))
        stock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        stock_font = QFont()
        stock_font.setBold(True)
        stock_item.setFont(stock_font)
        try:
            stock_num = int(stock_final)
            if stock_num <= 5:
                stock_item.setForeground(QBrush(QColor("#D32F2F")))
                stock_item.setBackground(QBrush(QColor("#FFEBEE")))
            elif stock_num <= 10:
                stock_item.setForeground(QBrush(QColor("#F57C00")))
                stock_item.setBackground(QBrush(QColor("#FFF3E0")))
            else:
                stock_item.setForeground(QBrush(QColor("#388E3C")))
        except Exception:
            pass
        self.tree_kardex.setItem(i, 5, stock_item)

    def export_to_excel(self):
        """Exporta los datos visibles a un archivo CSV (Excel compatible)."""
        if self.tree_kardex.rowCount() == 0:
            QMessageBox.warning(self, "Exportar", "No hay datos para exportar.")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte Kardex", "", 
                                                 "Archivos CSV (*.csv);;Todos los archivos (*)", options=options)
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile, delimiter=';') # Punto y coma para Excel en español
                    
                    # Encabezados
                    headers = []
                    for col in range(self.tree_kardex.columnCount()):
                        headers.append(self.tree_kardex.horizontalHeaderItem(col).text())
                    writer.writerow(headers)
                    
                    # Datos
                    for row in range(self.tree_kardex.rowCount()):
                        row_data = []
                        for col in range(self.tree_kardex.columnCount()):
                            item = self.tree_kardex.item(row, col)
                            text = item.text() if item else ""
                            # Limpiar símbolos de moneda o flechas para que Excel lo lea mejor
                            if col == 1: # Movimiento
                                text = text.replace("▼ ", "").replace("▲ ", "")
                            if col == 4: # Costo
                                text = text.replace("S/", "").strip()
                            row_data.append(text)
                        writer.writerow(row_data)
                
                QMessageBox.information(self, "Éxito", f"Reporte guardado correctamente en:\n{file_path}")
                
                # Intentar abrir el archivo
                try:
                    os.startfile(file_path)
                except:
                    pass
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al exportar: {str(e)}")

    def _get_font(self, size=10):
        """Retorna una fuente estándar."""
        font = QFont()
        font.setPointSize(size)
        return font

