import datetime
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton, 
    QTableWidget, QHeaderView, QTableWidgetItem, QAbstractItemView, QInputDialog, QMessageBox, QSizePolicy,
    QComboBox, QFileDialog, QMenu, QScrollArea, QSystemTrayIcon
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread, QTimer
from PyQt5 import QtCore
import os
from PyQt5.QtGui import QCursor, QIcon, QColor
import requests
import json
import subprocess
import winsound
import threading
import webbrowser
import time

# Importar el nuevo widget de gráfico (C++ Python wrapper)
from gui.widgets.sales_chart_widget import SalesChartWidgetPy

# Lock global para evitar múltiples sonidos simultáneos
notification_sound_lock = threading.Lock()

# Importaciones para el entorno de desarrollo y empaquetado
from utils.file_handler import cargar_pacientes, cargar_productos, cargar_ventas, cargar_nombre_optica, guardar_productos

NOTIFICATION_POLL_INTERVAL_SECONDS = 45 * 60

class NotificationWorker(QThread):
    """Worker que corre en thread separado para polling de notificaciones sin bloquear UI."""
    notification_found = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.last_notification_id = 0
    
    def run(self):
        """Loop de polling en thread separado."""
        while self.running:
            try:
                response = requests.get("https://api.yhana.cloud/api/win/notis.php", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    notifications = data if isinstance(data, list) else data.get("notificaciones", [])
                    
                    for notif in notifications:
                        if notif.get('id', 0) > self.last_notification_id and self.running:
                            self.notification_found.emit(notif)
                            self.last_notification_id = notif.get('id', 0)
            except Exception as e:
                pass
            
            # Sleep sin bloquear thread
            if self.running:
                time.sleep(NOTIFICATION_POLL_INTERVAL_SECONDS)
    
    def stop(self):
        """Detiene el worker."""
        self.running = False
        self.wait()

class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        self.setObjectName("MainContent")
        self.last_notification_id = self._load_last_notification_id()  # Cargar desde archivo
        self.notification_worker = None  # Worker thread para polling
        self.setup_ui()
        # Cargar datos inmediatamente después de configurar la UI
        self.update_dashboard_data()
        # Cargar notificaciones actuales del servidor
        self._load_initial_notifications()
        self.start_notification_polling()

    def setup_ui(self):
        page = self
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(0)
        layout.setContentsMargins(40, 40, 40, 40)

        # ========================
        # HEADER MINIMALISTA
        # ========================
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Título principal
        nombre_optica = cargar_nombre_optica(self.username)
        self.nombre_optica_label = QLabel(f"Bienvenido — {nombre_optica}")
        self.nombre_optica_label.setStyleSheet("""
            color: #1a1a1a;
            font-size: 28px;
            font-weight: 600;
        """)
        header_layout.addWidget(self.nombre_optica_label)

        # Línea separadora sutil
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #e0e0e0;")
        header_layout.addWidget(separator)

        layout.addWidget(header_container)
        layout.addSpacing(30)

        # ========================
        # TARJETAS DE ESTADÍSTICAS - MINIMALISTA
        # ========================
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setSpacing(24)
        stats_layout.setContentsMargins(0, 0, 0, 0)

        self.total_pacientes_label = QLabel("0")
        self.total_pacientes_label.setObjectName("SummaryNumber")
        stats_layout.addWidget(self.create_stat_card_minimal(
            "Pacientes",
            self.total_pacientes_label
        ))

        self.total_productos_label = QLabel("0")
        self.total_productos_label.setObjectName("SummaryNumber")
        stats_layout.addWidget(self.create_stat_card_minimal(
            "Productos",
            self.total_productos_label
        ))

        self.pacientes_mes_label = QLabel("0")
        self.pacientes_mes_label.setObjectName("SummaryNumber")
        stats_layout.addWidget(self.create_stat_card_minimal(
            "Nuevos (30d)",
            self.pacientes_mes_label
        ))

        self.total_ventas_label = QLabel("S/ 0.00")
        self.total_ventas_label.setObjectName("SummaryNumber")
        stats_layout.addWidget(self.create_stat_card_minimal(
            "Ventas",
            self.total_ventas_label
        ))

        layout.addWidget(stats_container)
        layout.addSpacing(30)

        # ========================
        # GRÁFICO DE VENTAS
        # ========================
        chart_header = QHBoxLayout()
        chart_title = QLabel("Gráfico de Ventas")
        chart_title.setStyleSheet("""
            color: #1a1a1a;
            font-size: 18px;
            font-weight: 600;
        """)
        chart_header.addWidget(chart_title)
        chart_header.addStretch()

        # Botón de configuración simple
        self.toggle_chart_config_button = QPushButton("⚙")
        self.toggle_chart_config_button.setCheckable(True)
        self.toggle_chart_config_button.setChecked(False)
        self.toggle_chart_config_button.setFixedSize(36, 36)
        self.toggle_chart_config_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_chart_config_button.setStyleSheet('''
            QPushButton {
                border: 1px solid #d0d0d0;
                background: white;
                border-radius: 6px;
                color: #666;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #f5f5f5;
            }
            QPushButton:checked {
                background: #f0f0f0;
                border-color: #999;
            }
        ''')
        chart_header.addWidget(self.toggle_chart_config_button)

        layout.addLayout(chart_header)
        layout.addSpacing(15)

        # Controles del gráfico (ocultos por defecto)
        self.chart_config_container = QWidget()
        chart_controls_layout = QHBoxLayout(self.chart_config_container)
        chart_controls_layout.setContentsMargins(0, 10, 0, 10)
        chart_controls_layout.setSpacing(12)
        chart_controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.chart_config_container.setVisible(False)

        self.toggle_chart_config_button.toggled.connect(self.chart_config_container.setVisible)

        # Selector de período
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Últimos 7 días", "Últimos 15 días", "Últimos 30 días"])
        self.period_combo.setCurrentIndex(1)
        self.period_combo.currentIndexChanged.connect(self.on_period_changed)
        self.period_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background: white;
                font-size: 13px;
            }
        """)
        chart_controls_layout.addWidget(self.period_combo)

        # Botón para exportar
        self.export_button = QPushButton("Guardar")
        self.export_button.clicked.connect(self.export_chart)
        self.export_button.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                background: white;
                color: #333;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #f5f5f5;
            }
        """)
        chart_controls_layout.addWidget(self.export_button)

        # Barra de herramientas para futuros controles
        self.chart_toolbar_widget = QWidget()
        self.chart_toolbar_layout = QHBoxLayout(self.chart_toolbar_widget)
        self.chart_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_toolbar_layout.setSpacing(5)
        chart_controls_layout.addWidget(self.chart_toolbar_widget)

        layout.addWidget(self.chart_config_container)

        # Gráfico
        self.sales_chart_widget = QWidget()
        self.chart_layout = QHBoxLayout(self.sales_chart_widget)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_layout.setSpacing(0)
        self.chart_layout.setAlignment(Qt.AlignLeft)
        self.create_interactive_sales_chart()
        layout.addWidget(self.sales_chart_widget, alignment=Qt.AlignLeft)

        layout.addStretch()

    def load_notifications(self):
        """Carga las notificaciones desde la API."""
        try:
            response = requests.get("https://api.yhana.cloud/api/win/notis.php", timeout=5)
            if response.status_code == 200:
                data = response.json()
                notifications = data if isinstance(data, list) else data.get("notificaciones", [])
                self.display_notifications(notifications)
            else:
                self.show_no_notifications("Error al cargar notificaciones")
        except requests.exceptions.RequestException as e:
            print(f"Error conectando a notificaciones: {e}")
            self.show_no_notifications("No se pudo conectar a notificaciones")
        except json.JSONDecodeError:
            print("Error decodificando JSON de notificaciones")
            self.show_no_notifications("Error al procesar notificaciones")
        except Exception as e:
            print(f"Error inesperado al cargar notificaciones: {e}")
            self.show_no_notifications("Error al cargar notificaciones")

    def display_notifications(self, notifications):
        """COMENTADO: Ahora las notificaciones se muestran en popup, no en pantalla principal."""
        pass
        #while self.notifications_layout.count():
        #    child = self.notifications_layout.takeAt(0)
        #    if child.widget():
        #        child.widget().deleteLater()
        #
        #if not notifications:
        #    self.show_no_notifications("Sin notificaciones")
        #    return
        #
        #for notif in notifications:
        #    if isinstance(notif, dict):
        #        self.add_notification_item(notif)
        #    else:
        #        print(f"Notificación inválida: {notif}")

    def add_notification_item(self, notif):
        """Crea un widget de notificación individual."""
        # Extraer datos
        title = notif.get("titulo", "Notificación")
        message = notif.get("mensaje", "")
        notif_type = notif.get("tipo", "info").lower()  # success, warning, error, info
        
        # Contenedor de la notificación
        notif_widget = QWidget()
        notif_layout = QHBoxLayout(notif_widget)
        notif_layout.setContentsMargins(12, 12, 12, 12)
        notif_layout.setSpacing(12)
        
        # Color según tipo
        color_map = {
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#f44336",
            "info": "#2196F3"
        }
        color = color_map.get(notif_type, "#2196F3")
        
        # Indicador de color
        indicator = QWidget()
        indicator.setFixedWidth(4)
        indicator.setStyleSheet(f"background: {color}; border-radius: 2px;")
        notif_layout.addWidget(indicator)
        
        # Contenido
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        
        # Título
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            color: #1a1a1a;
            font-weight: 600;
            font-size: 13px;
        """)
        content_layout.addWidget(title_label)
        
        # Mensaje
        if message:
            msg_label = QLabel(message)
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet("""
                color: #666;
                font-size: 12px;
            """)
            content_layout.addWidget(msg_label)
        
        notif_layout.addLayout(content_layout, 1)
        
        # Separador
        notif_widget.setStyleSheet("""
            QWidget {
                background: white;
                border-bottom: 1px solid #f0f0f0;
            }
        """)
        
        self.notifications_layout.addWidget(notif_widget)

    def show_no_notifications(self, message):
        """Muestra un mensaje cuando no hay notificaciones."""
        # Limpiar
        while self.notifications_layout.count():
            child = self.notifications_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        empty_label = QLabel(message)
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("""
            color: #999;
            font-size: 13px;
            padding: 30px;
        """)
        self.notifications_layout.addWidget(empty_label)
        self.notifications_layout.addStretch()


    def create_stat_card_minimal(self, title, value_label):
        """Crea una tarjeta de estadística minimalista."""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        card.setMinimumHeight(80)
        
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(4)

        # Título
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #888;
            font-size: 11px;
            font-weight: 500;
        """)
        card_layout.addWidget(title_label)

        # Valor
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("""
            color: #1a1a1a;
            font-size: 20px;
            font-weight: 700;
        """)
        card_layout.addWidget(value_label)

        return card

        """Crea una tarjeta de estadística con diseño moderno."""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background: white;
                border-radius: 12px;
                border-left: 5px solid {color};
                padding: 0px;
            }}
        """)
        card.setMinimumHeight(140)
        
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)

        # Título
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet("""
            color: #666;
            font-size: 13px;
            font-weight: 500;
        """)
        card_layout.addWidget(title_label)

        # Valor
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        value_label.setStyleSheet(f"""
            color: {color};
            font-size: 32px;
            font-weight: 700;
        """)
        card_layout.addWidget(value_label)

        return card

    def create_interactive_sales_chart(self):
        """Crea gráfico interactivo de ventas (versión C++ con PyQt5)"""
        # Limpiar layout anterior del gráfico
        while self.chart_layout.count():
            child = self.chart_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Obtener días según período seleccionado
        period_idx = self.period_combo.currentIndex()
        days_count = [7, 15, 30][period_idx]

        ventas = cargar_ventas(self.username)
        today = datetime.date.today()
        # Últimos N días: desde (N-1 días atrás) hasta hoy
        days = [today - datetime.timedelta(days=i) for i in range(days_count-1, -1, -1)]
        day_labels = [d.strftime("%d/%m") for d in days]
        sales_by_day = {d: 0.0 for d in days}

        # Agregar ventas por día
        for venta in ventas:
            try:
                fecha_str = venta.get('fecha', '')
                fecha_part = str(fecha_str).split()[0] if fecha_str else ''
                try:
                    fecha = datetime.datetime.strptime(fecha_part, "%d/%m/%Y").date()
                except Exception:
                    continue

                try:
                    monto = float(venta.get('total') or venta.get('monto') or 0.0)
                except Exception:
                    monto = 0.0

                if fecha in sales_by_day:
                    sales_by_day[fecha] += monto
            except Exception:
                continue

        # Crear array ordenado por día
        sales = [sales_by_day[d] for d in days]

        # Crear widget del gráfico C++
        chart_widget = SalesChartWidgetPy(self)
        chart_widget.setMinimumHeight(400)
        chart_widget.setData(sales, day_labels)
        
        periodo_text = ["Últimos 7 días", "Últimos 15 días", "Últimos 30 días"][period_idx]
        chart_widget.setTitle(f'Gráfico de Ventas — {periodo_text}')
        chart_widget.setLineColor(QColor(25, 118, 210))  # #1976d2
        
        # Actualizar etiquetas informativas
        try:
            self.chart_title_label.setText(f'📊 Gráfico de Ventas — {periodo_text}')
            
            if sales:
                last_sales = float(sales[-1]) if sales[-1] else 0.0
                avg = sum(sales) / len(sales) if sales else 0.0
                status = 'Arriba del promedio' if last_sales > avg else 'Debajo del promedio' if last_sales < avg else 'En el promedio'
                color = '#2e7d32' if last_sales > avg else '#c62828' if last_sales < avg else '#616161'
                subtitle_html = f"Ventas hoy: <b>S/. {last_sales:,.2f}</b> — <span style='color:{color};'>{status}</span>"
                try:
                    self.chart_subtitle_label.setText(subtitle_html)
                except Exception:
                    self.chart_subtitle_label.setText(f"Ventas hoy: S/. {last_sales:,.2f} — {status}")
        except Exception:
            pass
        
        # Insertar el nuevo widget en el layout
        self.chart_layout.addWidget(chart_widget)
        self.chart_layout.addStretch()
        
        self.current_chart_widget = chart_widget
        
        # Limpiar la barra de herramientas (no la usamos con C++)
        if hasattr(self, 'chart_toolbar_layout'):
            while self.chart_toolbar_layout.count():
                child = self.chart_toolbar_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
    
    def setup_chart_interactivity(self, canvas, ax, days, day_labels, sales, tickets=None):
        """DEPRECADO: Ya no se necesita con el nuevo widget C++"""
        pass
    
    def on_period_changed(self):
        """Refresca el gráfico cuando cambia el período"""
        self.create_interactive_sales_chart()
    
    def export_chart(self):
        """Exporta el gráfico a imagen PNG"""
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, 
                "Guardar Gráfico", 
                "", 
                "Imágenes PNG (*.png);;Imágenes JPG (*.jpg)"
            )
            
            if filepath:
                if not filepath.endswith(('.png', '.jpg')):
                    filepath += '.png'
                
                # Exportar el widget como imagen
                if hasattr(self, 'current_chart_widget') and self.current_chart_widget:
                    pixmap = self.current_chart_widget.grab()
                    pixmap.save(filepath)
                    QMessageBox.information(self, "Éxito", f"Gráfico exportado a:\n{filepath}")
                else:
                    QMessageBox.warning(self, "Error", "No hay gráfico disponible para exportar")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al exportar: {str(e)}")

    def create_low_stock_alerts(self):
        group = QGroupBox("Inventario Bajo (< 5 Unidades)")
        group.setObjectName("contentGroup")
        self.low_stock_layout = QVBoxLayout(group)
        return group

    def update_dashboard_data(self):
        pacientes = cargar_pacientes(self.username)
        productos = cargar_productos(self.username)
        ventas = cargar_ventas(self.username)
        
        self.total_pacientes_label.setText(str(len(pacientes)))
        self.total_productos_label.setText(str(len(productos)))

        today = datetime.date.today()
        one_month_ago = today - datetime.timedelta(days=30)
        pacientes_mes = 0
        for paciente in pacientes:
            try:
                fecha = datetime.datetime.strptime(paciente.get('fecha', '').split()[0], "%d/%m/%Y").date()
                if fecha >= one_month_ago:
                    pacientes_mes += 1
            except (ValueError, TypeError):
                continue
        self.pacientes_mes_label.setText(str(pacientes_mes))

        # Calcular ventas totales
        try:
            total_ventas = sum(float(v.get('total', 0)) for v in ventas if isinstance(v, dict))
            self.total_ventas_label.setText(f"S/ {total_ventas:,.2f}")
        except (ValueError, TypeError):
            self.total_ventas_label.setText("S/ 0.00")

        # Refrescar el gráfico de ventas con los datos más recientes
        try:
            self.refresh_sales_chart()
        except Exception:
            pass

    def refresh_sales_chart(self):
        """Regenera el gráfico interactivo de ventas"""
        try:
            self.create_interactive_sales_chart()
        except Exception as e:
            print("Error refrescando gráfico:", e)
    
    def update_low_stock_alerts(self):
        for i in reversed(range(self.low_stock_layout.count())):
            widget = self.low_stock_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        productos = cargar_productos(self.username)
        # Si el JSON contiene entradas corruptas (no-dict), sanitizar automáticamente
        corrupted_found = any(not isinstance(p, dict) for p in productos)
        if corrupted_found:
            try:
                from utils.file_handler import sanitizar_productos
                cleaned, removed, backup = sanitizar_productos(self.username, backup=True)
                if removed:
                    msg = f"Se detectaron y limpiaron {removed} entradas corruptas en productos.json."
                    if backup:
                        msg += f" Backup: {backup}"
                    QMessageBox.information(self, 'Sanitizado', msg)
                    # recargar productos
                    productos = cargar_productos(self.username)
            except Exception:
                # si falla la sanitización, continuar sin romper
                pass

        low_stock_products = [p for p in productos if isinstance(p, dict) and int(p.get('stock', 0) or 0) < 5]
        
        if not low_stock_products:
            label = QLabel("No hay productos con stock bajo.")
            label.setObjectName("successLabel")
            self.low_stock_layout.addWidget(label)
        else:
            for prod in low_stock_products:
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(4, 4, 4, 4)

                lbl = QLabel(f"❌ <b>{prod['nombre']}</b>: {prod['stock']} unidades")
                lbl.setObjectName("alertLabel")
                row_layout.addWidget(lbl)

                # Botón para ir al producto (abre la edición en Inventario)
                btn_ir = QPushButton("Ir")
                def _go(p=prod):
                    try:
                        # Mostrar la página de Inventario y abrir editor
                        if hasattr(self.parent_app, 'mostrar_frame'):
                            try:
                                self.parent_app.mostrar_frame(3)
                            except Exception:
                                try:
                                    self.parent_app.stacked_widget.setCurrentWidget(self.parent_app.inventory_page)
                                except Exception:
                                    pass
                        if hasattr(self.parent_app, 'inventory_page'):
                            try:
                                self.parent_app.inventory_page.abrir_edicion_producto(p)
                            except Exception:
                                pass
                    except Exception:
                        pass
                btn_ir.clicked.connect(_go)
                row_layout.addWidget(btn_ir)

                # Botón para reponer rápido: solicitar cantidad y actualizar
                btn_reponer = QPushButton("Reponer")
                def _reponer(p=prod):
                    """Reponer stock de forma segura: validamos tipos y protegemos contra datos corruptos."""
                    try:
                        prod_name = p.get('nombre') if isinstance(p, dict) else None
                        prompt_name = prod_name or str(p)
                        qty, ok = QInputDialog.getInt(self, "Reponer stock", f"Agregar unidades a {prompt_name}", 1, 1)
                        if not ok or qty <= 0:
                            return

                        productos = cargar_productos(self.username) or []
                        # Asegurarnos de trabajar solo con dicts
                        updated = False
                        for i, pp in enumerate(productos):
                            if not isinstance(pp, dict):
                                # ignorar entradas corruptas
                                continue
                            if pp.get('nombre') == prod_name:
                                try:
                                    current_stock = int(pp.get('stock', 0) or 0)
                                except Exception:
                                    current_stock = 0
                                productos[i]['stock'] = current_stock + int(qty)
                                try:
                                    guardar_productos(self.username, productos)
                                except Exception as e:
                                    QMessageBox.critical(self, 'Error', f'No se pudo guardar productos: {e}')
                                    return
                                # registrar kardex si existe el método
                                try:
                                    self.add_kardex_entry('Entrada', pp.get('nombre'), int(qty), float(pp.get('costo', 0) or 0))
                                except Exception:
                                    pass
                                updated = True
                                break

                        if not updated:
                            QMessageBox.warning(self, 'Atención', f'No se encontró el producto {prompt_name} para reponer.')
                            return

                        # Refrescar vistas (intentar, ignorar fallos)
                        try:
                            if hasattr(self.parent_app, 'inventory_page'):
                                self.parent_app.inventory_page.update_inventory_gallery()
                        except Exception:
                            pass
                        try:
                            self.update_low_stock_alerts()
                        except Exception:
                            pass

                        QMessageBox.information(self, 'Éxito', f'Se agregaron {qty} unidades a {prompt_name}')
                    except Exception as e:
                        QMessageBox.critical(self, 'Error', f'No se pudo reponer: {e}')
                btn_reponer.clicked.connect(_reponer)
                row_layout.addWidget(btn_reponer)

                # Spacer para alinear a la izquierda
                row_layout.addStretch()

                self.low_stock_layout.addWidget(row)

    def start_notification_polling(self):
        """Inicia el worker thread para polling de notificaciones."""
        self.notification_worker = NotificationWorker()
        self.notification_worker.last_notification_id = self.last_notification_id
        self.notification_worker.notification_found.connect(self.on_notification_received)
        self.notification_worker.start()
    
    def _load_initial_notifications(self):
        """Carga las notificaciones iniciales del servidor."""
        try:
            response = requests.get("https://api.yhana.cloud/api/win/notis.php", timeout=5)
            if response.status_code == 200:
                data = response.json()
                notifications = data if isinstance(data, list) else data.get("notificaciones", [])
                
                # Pasar al popup para mostrar las notificaciones actuales
                if hasattr(self.parent_app, 'notifications_popup') and notifications:
                    self.parent_app.notifications_popup.load_notifications(notifications)
        except Exception:
            pass
    
    def on_notification_received(self, notif):
        """Slot que recibe notificaciones desde el worker thread."""
        self.last_notification_id = notif.get('id', 0)
        self._save_last_notification_id(self.last_notification_id)
        self.show_notification_popup(notif)
        
        # Agregar notificación a popup sin abrir (silenciosamente en background)
        if hasattr(self.parent_app, 'notifications_popup'):
            self.parent_app.notifications_popup.add_notification_new(notif)
            # NO abrir popup automáticamente para evitar lag
            # El usuario puede hacer click en 🔔 si quiere ver las notificaciones
    
    def check_new_notifications(self):
        """COMENTADO: El worker thread ya verifica notificaciones en background.
        Este método no se usa, lo dejo como referencia."""
        pass
        #try:
        #    response = requests.get("https://api.yhana.cloud/api/win/notis.php", timeout=5)
        #    if response.status_code == 200:
        #        data = response.json()
        #        notifications = data if isinstance(data, list) else data.get("notificaciones", [])
        #        
        #        # Buscar notificaciones nuevas (ID mayor al último visto)
        #        for notif in notifications:
        #            if notif.get('id', 0) > self.last_notification_id:
        #                # Nueva notificación encontrada
        #                self.show_notification_popup(notif)
        #                self.last_notification_id = notif.get('id', 0)
        #                self._save_last_notification_id(self.last_notification_id)  # Guardar en archivo
        #        
        #        # Recargar la lista completa de notificaciones
        #        self.display_notifications(notifications)
        #except Exception:
        #    # Silenciar errores de conexión
        #    pass
    
    def show_notification_popup(self, notif):
        """Muestra una notificación nativa de Windows (sin sonido)."""
        try:
            title = notif.get('titulo', 'Nueva notificación')
            message = notif.get('mensaje', '')
            notif_type = notif.get('tipo', 'info')
            enlace = notif.get('enlace', '')
            accion = notif.get('accion', 'ninguno')
            
            # Solo mostrar notificación sin sonido
            with notification_sound_lock:
                self.show_windows_notification(title, message, notif_type)
            
            # Ejecutar acción asociada inmediatamente
            if accion and accion != 'ninguno':
                self.execute_notification_action(accion, enlace)
        except Exception as e:
            print(f"Error mostrando notificación: {e}")
    
    def show_windows_notification(self, title, message, notif_type='info'):
        """Muestra una notificación nativa de Windows 10/11 visualmente en la esquina."""
        try:
            # Script PowerShell simple y directo para notificaciones visibles
            ps_command = f"""
            Add-Type -AssemblyName System.Windows.Forms
            $notifyIcon = New-Object System.Windows.Forms.NotifyIcon
            $notifyIcon.Icon = [System.Drawing.SystemIcons]::Information
            $notifyIcon.Visible = $true
            $notifyIcon.ShowBalloonTip(5000, \"📢 visoo\", \"{message}\", [System.Windows.Forms.ToolTipIcon]::Info)
            Start-Sleep -Milliseconds 5000
            $notifyIcon.Dispose()
            """
            
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_command],
                capture_output=True,
                timeout=10
            )
        except Exception as e:
            print(f"Error en notificación Windows: {e}")
    
    def play_notification_sound(self):
        """Reproduce un sonido de notificación profesional."""
        try:
            # Sonido melódico profesional (Do, Mi, Sol - acorde Do Mayor)
            winsound.Beep(262, 200)  # Do (C4)
            time.sleep(0.1)
            winsound.Beep(330, 200)  # Mi (E4)
            time.sleep(0.1)
            winsound.Beep(392, 300)  # Sol (G4) - más largo
        except Exception:
            pass
    
    def execute_notification_action(self, accion, enlace):
        """Ejecuta la acción asociada a la notificación."""
        try:
            if accion == 'abrir_url' and enlace:
                # Usar start en Windows para abrir URL en navegador predeterminado
                subprocess.Popen(['cmd', '/c', 'start', enlace], shell=False)
                print(f"Abriendo URL: {enlace}")
            elif accion == 'abrir_viso':
                if self.parent_app:
                    self.parent_app.raise_()
                    self.parent_app.activateWindow()
                print("VISO traído al frente")
        except Exception as e:
            print(f"Error ejecutando acción: {e}")

    def _load_last_notification_id(self):
        """Carga el último ID de notificación visto desde el archivo de estado."""
        try:
            from pathlib import Path
            state_file = Path(os.path.expanduser("~")) / ".viso" / "notification_state.json"
            if state_file.exists():
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_id', 0)
        except Exception:
            pass
        return 0
    
    def _save_last_notification_id(self, notif_id):
        """Guarda el último ID de notificación visto en el archivo de estado."""
        try:
            from pathlib import Path
            from datetime import datetime as dt
            state_dir = Path(os.path.expanduser("~")) / ".viso"
            state_dir.mkdir(exist_ok=True)
            state_file = state_dir / "notification_state.json"
            data = {'last_id': notif_id, 'timestamp': dt.now().isoformat()}
            with open(state_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    def closeEvent(self, event):
        """Detiene el worker cuando se cierra la ventana."""
        if self.notification_worker:
            self.notification_worker.stop()
        super().closeEvent(event)
