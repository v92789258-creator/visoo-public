import os
import datetime
from PyQt5 import sip
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QHeaderView,
    QGroupBox, QGridLayout, QLineEdit, QAbstractItemView,
    QPushButton, QDialog, QMessageBox, QHBoxLayout, QTableWidgetItem, QComboBox,
    QSizePolicy, QFrame, QGraphicsDropShadowEffect, QToolTip, QProgressBar, QStackedWidget,
    QApplication
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QThread, pyqtSignal, QVariantAnimation
from PyQt5.QtGui import QColor, QPalette, QPixmap, QImage

# Importaciones diferidas para evitar lag inicial
# from gui.dialogs.patient_dialog import EditPatientDialog, PatientDetailsDialog, AddPatientDialog
from utils.file_handler import cargar_pacientes, guardar_pacientes
from gui.styles.button_styles import PRIMARY_BUTTON, SECONDARY_BUTTON, DELETE_BUTTON


_DETACHED_PATIENT_THREADS = set()


def _is_qt_object_alive(obj):
    try:
        return obj is not None and not sip.isdeleted(obj)
    except TypeError:
        return obj is not None
    except Exception:
        return False


def _parse_patient_date(value):
    """Convierte fechas de paciente a `date` soportando formatos comunes."""
    raw = str(value or "").strip()
    if not raw or raw.upper() == "N/A":
        return None

    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    )
    for fmt in formats:
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except Exception:
            continue
    return None


def _resolve_patient_last_visit_date(patient):
    """Obtiene la ultima visita desde el campo dedicado o el historial de graduaciones."""
    if not isinstance(patient, dict):
        return None

    direct_date = _parse_patient_date(patient.get("ultima_visita"))

    history = patient.get("historial_graduaciones", [])
    best_date = None
    if isinstance(history, list):
        for entry in history:
            if not isinstance(entry, dict):
                continue
            current = _parse_patient_date(entry.get("fecha"))
            if current is None:
                continue
            if best_date is None or current > best_date:
                best_date = current
    if direct_date is not None and best_date is not None:
        return max(direct_date, best_date)
    return direct_date or best_date


def _format_last_visit_relative(visit_date, today=None):
    """Devuelve texto relativo de ultima visita para la tabla de pacientes."""
    if visit_date is None:
        return "N/A", None

    if today is None:
        today = datetime.date.today()

    if isinstance(today, datetime.datetime):
        today = today.date()

    delta_days = max(0, (today - visit_date).days)

    if delta_days == 0:
        return "Hoy", delta_days
    if delta_days <= 6:
        suffix = "dia" if delta_days == 1 else "dias"
        return f"Hace {delta_days} {suffix}", delta_days
    if delta_days <= 13:
        return "Hace mas de 1 semana", delta_days
    if delta_days <= 20:
        return "Hace mas de 2 semanas", delta_days
    if delta_days <= 27:
        return "Hace mas de 3 semanas", delta_days
    if delta_days < 365:
        months = max(1, delta_days // 30)
        suffix = "mes" if months == 1 else "meses"
        return f"Hace mas de {months} {suffix}", delta_days

    years = max(1, delta_days // 365)
    suffix = "ano" if years == 1 else "anos"
    return f"Hace mas de {years} {suffix}", delta_days


def _release_detached_patient_thread(thread):
    try:
        _DETACHED_PATIENT_THREADS.discard(thread)
    except Exception:
        pass
    try:
        thread.deleteLater()
    except Exception:
        pass


class PatientsTableSkeleton(QWidget):
    """Skeleton visual con forma de tabla de pacientes."""

    def __init__(self, rows=6, parent=None):
        super().__init__(parent)
        self._rows = max(4, int(rows or 6))
        self._blocks = []
        self._pulse = 0.0
        self._build_ui()
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(950)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._on_anim)
        self._apply_style()
        self.anim.start()

    def _make_block(self, width=None, height=14, radius=6):
        block = QFrame()
        block.setProperty("skeleton_radius", int(radius))
        block.setFixedHeight(int(height))
        if width:
            block.setFixedWidth(int(width))
        self._blocks.append(block)
        return block

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("skeleton_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 12, 8, 12)
        header_layout.setSpacing(14)
        for width in (90, 300, 120, 120, 120, 140, 60):
            header_layout.addWidget(self._make_block(width=width, height=16, radius=6))
        header_layout.addStretch()
        layout.addWidget(header)

        for _ in range(self._rows):
            row = QFrame()
            row.setObjectName("skeleton_row")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 14, 8, 14)
            row_layout.setSpacing(14)
            row_layout.addWidget(self._make_block(width=84, height=14))
            row_layout.addWidget(self._make_block(width=420, height=14))
            row_layout.addWidget(self._make_block(width=100, height=14))
            row_layout.addWidget(self._make_block(width=100, height=14))
            row_layout.addWidget(self._make_block(width=110, height=14))
            row_layout.addWidget(self._make_block(width=110, height=14))
            row_layout.addWidget(self._make_block(width=40, height=14))
            row_layout.addStretch()
            layout.addWidget(row)
        layout.addStretch()

    def set_loading_text(self, title="", subtitle=""):
        return

    def _on_anim(self, value):
        try:
            self._pulse = float(value or 0.0)
        except Exception:
            self._pulse = 0.0
        self._apply_style()

    def _apply_style(self):
        block = 227 + int(12 * self._pulse)
        row_bg = 247 + int(4 * self._pulse)
        self.setStyleSheet(
            f"""
            QFrame#skeleton_header {{
                background: rgb({row_bg},{row_bg},{row_bg});
                border-bottom: 1px solid #E5E7EB;
            }}
            QFrame#skeleton_row {{
                background: white;
                border-bottom: 1px solid #E5E7EB;
            }}
            QFrame[skeleton_radius] {{
                background: rgb({block},{block},{block});
                border: none;
                border-radius: 6px;
            }}
            """
        )


# ============================================================================
# PatientRefreshWorker: Verifica actualizaciones en thread separado
# ============================================================================
class PatientRefreshWorker(QThread):
    """Verifica actualizaciones de pacientes en background sin bloquear UI."""
    refresh_ready = pyqtSignal(list)  # Emite lista actualizada de pacientes
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self._running = True
    
    def run(self):
        """Actualización continua cada 1 segundo (local) + remoto cada 5s."""
        local_last_check = 0
        remote_last_check = 0
        
        while self._running:
            try:
                import time
                now = time.time()
                
                # SIEMPRE leer locales cada 1 segundo (sin esperar a remoto)
                if now - local_last_check >= 1.0:
                    pacientes_locales = cargar_pacientes(self.username)
                    if pacientes_locales:
                        self.refresh_ready.emit(pacientes_locales)
                    local_last_check = now
                
                # Cada 5 segundos, actualizar desde remoto
                if now - remote_last_check >= 5.0:
                    try:
                        from utils.api_handler import obtener_pacientes_remoto
                        from utils.file_handler import get_effective_branch_context

                        ctx = get_effective_branch_context(self.username) or {}
                        branch_code = str(ctx.get("code", "") or "").strip().upper()
                        pacientes_remotos = obtener_pacientes_remoto(
                            self.username,
                            codigo_dispositivo=branch_code or None
                        )
                        
                        if pacientes_remotos is not None:
                            self.refresh_ready.emit(pacientes_remotos)
                    except:
                        pass
                    remote_last_check = now
                
                # Wait 100ms para no usar CPU
                self.msleep(100)
            except Exception as e:
                # Ignorar errores silenciosamente
                self.msleep(100)
    
    def stop(self):
        """Detiene el worker."""
        self._running = False


class PatientLoadThread(QThread):
    loaded = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, username):
        super().__init__()
        self.username = username

    def run(self):
        try:
            pacientes = cargar_pacientes(self.username) or []
            if not isinstance(pacientes, list):
                pacientes = []
            
            # Pre-procesar datos pesados para la tabla en el hilo secundario
            today = datetime.date.today()
            for p in pacientes:
                if not isinstance(p, dict): continue
                
                # Cálculos de última visita
                visit_date = _resolve_patient_last_visit_date(p)
                visit_text, visit_days = _format_last_visit_relative(visit_date, today=today)
                p['_display_visit_text'] = visit_text
                p['_display_visit_days'] = visit_days
                p['_display_visit_iso'] = visit_date.isoformat() if visit_date else ""
                
                # Cálculo de edad
                fecha_nac_raw = p.get('fecha_nacimiento', '')
                if fecha_nac_raw:
                    try:
                        # Cachear el objeto datetime si es posible o al menos el string de edad
                        fecha_nac = datetime.datetime.strptime(fecha_nac_raw, '%Y-%m-%d')
                        p['_display_edad'] = str((datetime.datetime.now() - fecha_nac).days // 365)
                    except:
                        p['_display_edad'] = 'N/A'
                else:
                    p['_display_edad'] = 'N/A'
            
            self.loaded.emit(pacientes)
        except Exception as e:
            self.failed.emit(str(e))


class PatientsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        
        # Inicializar variables para refresh
        self.refresh_worker = None
        self.load_thread = None
        self._patients_loading = False
        self.all_pacientes = []
        self._patient_filter_timer = QTimer(self)
        self._patient_filter_timer.setSingleShot(True)
        self._patient_filter_timer.timeout.connect(self.filter_patients)
        
        self.setup_ui()
        QTimer.singleShot(0, self.load_patients)
        
        # Iniciar auto-refresh
        self._start_refresh_worker()
        
    def setup_ui(self):
        """Configurar la interfaz de usuario"""
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header con título y botón de agregar
        header_layout = QHBoxLayout()
        
        title = QLabel("Gestión de Pacientes")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: normal;
                color: #333333;
            }
        """)
        header_layout.addWidget(title)
        
        # Agregar espacio flexible entre el título y el botón
        header_layout.addStretch()
        
        btn_add = QPushButton("Nuevo")
        btn_add.setFixedWidth(120)  # Ancho fijo para el botón
        btn_add.setFixedHeight(36)  # Altura fija para el botón
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: black;
                border: 1px solid #191919;
                border-radius: 0px;
                padding: 8px 16px;
                font-weight: normal;
                font-size: 14px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        btn_add.clicked.connect(self.add_patient)
        
        # 🛡️ VERIFICAR PERMISO: Deshabilitar botón si no puede crear pacientes
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('pacientes', 'crear'):
                btn_add.setEnabled(False)
                btn_add.setToolTip("No tienes permiso para crear pacientes")
        
        header_layout.addWidget(btn_add)

        # Botón para actualizar la lista de pacientes
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.setFixedWidth(120)
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #191919;
                color: white;
                border: none;
                border-radius: 0px;
                padding: 8px 16px;
                font-weight: normal;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #0B5FB8;
            }
        """)
        self.btn_refresh.clicked.connect(self.load_patients)
        header_layout.addWidget(self.btn_refresh)

        # Botón para ir a Contratos
        btn_contracts = QPushButton("Contratos")
        btn_contracts.setFixedWidth(120)
        btn_contracts.setFixedHeight(36)
        btn_contracts.setStyleSheet("""
            QPushButton {
                background-color: #2157D5;
                color: white;
                border: none;
                border-radius: 0px;
                padding: 8px 16px;
                font-weight: normal;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1B4BBB;
            }
            QPushButton:pressed {
                background-color: #163D9A;
            }
        """)
        btn_contracts.clicked.connect(self.go_to_contracts)
        header_layout.addWidget(btn_contracts)

        layout.addLayout(header_layout)
        
        # Barra de búsqueda y filtros
        search_bar = QGroupBox("Búsqueda y Filtros")
        
        # Agregar efecto de sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 30))
        search_bar.setGraphicsEffect(shadow)
        
        search_bar.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                margin-top: 24px;
                padding: 16px;
            }
            QGroupBox::title {
                color: #333333;
                padding: 8px 16px;
                margin-left: 8px;
                background-color: white;
                border-radius: 4px;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
                background: white;
                min-height: 20px;
                font-size: 13px;
            }
            QLineEdit:hover, QComboBox:hover {
                border-color: #B3D7FF;
                background-color: #F8FBFF;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #0078D4;
                background-color: #FFFFFF;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: url(images/down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QLabel {
                color: #666666;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        
        search_layout = QGridLayout(search_bar)
        search_layout.setSpacing(15)
        
        # DNI
        self.dni_search = QLineEdit()
        self.dni_search.setPlaceholderText("Buscar por DNI...")
        self.dni_search.textChanged.connect(self._schedule_filter_patients)
        search_layout.addWidget(QLabel("DNI:"), 0, 0)
        search_layout.addWidget(self.dni_search, 0, 1)
        
        # Nombre
        self.name_search = QLineEdit()
        self.name_search.setPlaceholderText("Buscar por nombre...")
        self.name_search.textChanged.connect(self._schedule_filter_patients)
        search_layout.addWidget(QLabel("Nombre:"), 0, 2)
        search_layout.addWidget(self.name_search, 0, 3)
        
        # Filtros adicionales
        self.age_filter = QComboBox()
        self.age_filter.addItems(["Todas las edades", "0-18", "19-30", "31-50", "51+"])
        self.age_filter.currentTextChanged.connect(self._schedule_filter_patients)
        search_layout.addWidget(QLabel("Edad:"), 1, 0)
        search_layout.addWidget(self.age_filter, 1, 1)
        
        self.last_visit = QComboBox()
        self.last_visit.addItems(["Todas las visitas", "Último mes", "Últimos 3 meses", "Último año"])
        self.last_visit.currentTextChanged.connect(self._schedule_filter_patients)
        search_layout.addWidget(QLabel("Última visita:"), 1, 2)
        search_layout.addWidget(self.last_visit, 1, 3)
        
        layout.addWidget(search_bar)
        
        # Tabla de pacientes
        table_group = QGroupBox("Lista de Pacientes")
        # Permitir que el grupo de la tabla se expanda para ocupar más espacio
        table_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Agregar efecto de sombra para la tabla
        table_shadow = QGraphicsDropShadowEffect(self)
        table_shadow.setBlurRadius(20)
        table_shadow.setXOffset(0)
        table_shadow.setYOffset(2)
        table_shadow.setColor(QColor(0, 0, 0, 30))
        table_group.setGraphicsEffect(table_shadow)
        
        table_group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                margin-top: 24px;
                padding: 16px;
            }
            QGroupBox::title {
                color: #333333;
                padding: 8px 16px;
                margin-left: 8px;
                background-color: white;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        table_layout = QVBoxLayout(table_group)

        self.patient_content_stack = QStackedWidget()

        loader_page = QWidget()
        loader_layout = QVBoxLayout(loader_page)
        loader_layout.setContentsMargins(0, 0, 0, 0)
        loader_layout.setSpacing(0)
        self.patients_loader_title = None
        self.patients_loader_subtitle = None
        self.patients_loader_bar = None
        self.patients_skeleton = PatientsTableSkeleton(rows=6, parent=loader_page)
        loader_layout.addWidget(self.patients_skeleton)

        table_page = QWidget()
        table_page_layout = QVBoxLayout(table_page)
        table_page_layout.setContentsMargins(0, 0, 0, 0)

        self.patients_table = QTableWidget()
        # Hacer que la tabla pueda expandirse vertical y horizontalmente
        self.patients_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.patients_table.setMinimumHeight(300)
        self.patients_table.setColumnCount(7)
        self.patients_table.setHorizontalHeaderLabels([
            "DNI", "Nombre", "Teléfono", "Email",
            "Fecha Nac.", "Última Visita", "Edad"
        ])
        
        # Estilo de la tabla
        self.patients_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #F0F0F0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #E0E0E0;
                color: #333333;
            }
            QTableWidget::item:last-column {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #E5F3FF;
                color: #000000;
            }
            QTableWidget::item:hover {
                background-color: #F8FBFF;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                color: #666666;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #E0E0E0;
                font-weight: bold;
                font-size: 13px;
            }
            QHeaderView::section:hover {
                background-color: #F0F4F7;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #C0C0C0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A0A0A0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QPushButton {
                padding: 6px 10px;
                border-radius: 6px;
                min-width: 32px;
                min-height: 32px;
            }
            QPushButton[action="edit"] {
                background-color: #0078D4;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton[action="edit"]:hover {
                background-color: #106EBE;
            }
            QPushButton[action="details"] {
                background-color: white;
                color: #0078D4;
                border: 1px solid #0078D4;
                font-size: 16px;
            }
            QPushButton[action="details"]:hover {
                background-color: #E5F3FF;
            }
            QPushButton[action="delete"] {
                background-color: white;
                color: #D83B01;
                border: 1px solid #D83B01;
                font-size: 16px;
            }
            QPushButton[action="delete"]:hover {
                background-color: #FDE7E9;
            }
        """)
        
        # Configuración de la tabla
        header = self.patients_table.horizontalHeader()
        # Configurar el ancho de las columnas
        column_widths = {
            0: 100,  # DNI
            1: 300,  # Nombre
            2: 120,  # Teléfono
            3: 180,  # Email
            4: 150,  # Fecha Nac.
            5: 170,  # Última Visita
            6: 70    # Edad
        }
        
        # Aplicar los anchos y modos de redimensionamiento
        for col, width in column_widths.items():
            # Dejar la columna Nombre (1) como "Stretch" para usar el espacio restante
            if col == 1:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.patients_table.setColumnWidth(col, width)
            
        # Ajustar la altura de las filas para los botones
        self.patients_table.verticalHeader().setDefaultSectionSize(50)
        
        self.patients_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.patients_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.patients_table.verticalHeader().setVisible(False)
        # Abrir detalles al hacer doble clic en una fila
        self.patients_table.cellDoubleClicked.connect(self.on_patient_double_clicked)
        
        table_page_layout.addWidget(self.patients_table)
        self.patient_content_stack.addWidget(loader_page)
        self.patient_content_stack.addWidget(table_page)
        table_layout.addWidget(self.patient_content_stack)
        # Añadir el grupo de la tabla con stretch para que ocupe el espacio disponible
        layout.addWidget(table_group, 1)
        
        # Footer con estadísticas
        stats_layout = QHBoxLayout()
        
        self.total_patients_label = QLabel("Total de pacientes: 0")
        self.total_patients_label.setStyleSheet("color: #666666;")
        stats_layout.addWidget(self.total_patients_label)
        
        stats_layout.addStretch()
        
        self.last_update_label = QLabel("")
        self.last_update_label.setStyleSheet("color: #666666;")
        stats_layout.addWidget(self.last_update_label)
        
        # Label para mostrar distribución de edades en porcentajes (suma 100)
        self.age_distribution_label = QLabel("Distribución edades: -")
        self.age_distribution_label.setStyleSheet("color: #666666;")
        stats_layout.addWidget(self.age_distribution_label)
        
        layout.addLayout(stats_layout)
        self.setLayout(layout)

    def go_to_contracts(self):
        """Navegar a la página de contratos"""
        if self.parent_app and hasattr(self.parent_app, 'mostrar_frame'):
            self.parent_app.mostrar_frame(17) # Índice 17 = ContractsPage

    def _schedule_filter_patients(self, *_args):
        self._patient_filter_timer.start(450)

    def filter_patients(self):
        """Filtrar pacientes según los criterios de búsqueda"""
        search_dni = self.dni_search.text().lower()
        search_name = self.name_search.text().lower()
        age_filter = self.age_filter.currentText()
        visit_filter = self.last_visit.currentText()
        
        for row in range(self.patients_table.rowCount()):
            show_row = True
            
            # Filtrar por DNI
            if search_dni and search_dni not in self.patients_table.item(row, 0).text().lower():
                show_row = False
                
            # Filtrar por nombre
            if show_row and search_name and search_name not in self.patients_table.item(row, 1).text().lower():
                show_row = False
                
            # Filtrar por edad
            if show_row and age_filter != "Todas las edades":
                try:
                    edad = int(self.patients_table.item(row, 6).text())
                    edad_min, edad_max = {
                        "0-18": (0, 18),
                        "19-30": (19, 30),
                        "31-50": (31, 50),
                        "51+": (51, 999)
                    }[age_filter]
                    if not (edad_min <= edad <= edad_max):
                        show_row = False
                except:
                    show_row = False
                    
            # Filtrar por última visita
            if show_row and visit_filter != "Todas las visitas":
                try:
                    visit_item = self.patients_table.item(row, 5)
                    dias_desde_visita = visit_item.data(Qt.UserRole + 1) if visit_item else None
                    if dias_desde_visita is None:
                        show_row = False
                    else:
                        limite_dias = {
                            "Último mes": 30,
                            "Últimos 3 meses": 90,
                            "Último año": 365
                        }[visit_filter]

                        if int(dias_desde_visita) > limite_dias:
                            show_row = False
                except Exception:
                    show_row = False
                    
            self.patients_table.setRowHidden(row, not show_row)
            
        # Actualizar distribución de edades después de filtrar
        try:
            self.update_age_distribution()
        except Exception:
            pass

    def update_age_distribution(self):
        """Calcular la distribución de edades entre las filas visibles y mostrar porcentajes que sumen 100."""
        # Definir buckets
        counts = {"0-18": 0, "19-30": 0, "31-50": 0, "51+": 0, "N/A": 0}
        total_visible = 0

        for row in range(self.patients_table.rowCount()):
            if self.patients_table.isRowHidden(row):
                continue
            total_visible += 1
            item = self.patients_table.item(row, 6)
            if not item:
                counts["N/A"] += 1
                continue
            txt = item.text()
            try:
                edad = int(txt)
                if edad <= 18:
                    counts["0-18"] += 1
                elif edad <= 30:
                    counts["19-30"] += 1
                elif edad <= 50:
                    counts["31-50"] += 1
                else:
                    counts["51+"] += 1
            except Exception:
                counts["N/A"] += 1

        if total_visible == 0:
            self.age_distribution_label.setText("Distribución edades: -")
            return

        # Calcular porcentajes (enteros) y ajustar para que sumen exactamente 100
        perc = {}
        for k, v in counts.items():
            perc[k] = int(round((v * 100.0) / total_visible))

        total_perc = sum(perc.values())
        diff = 100 - total_perc
        if diff != 0:
            # Añadir la diferencia al bucket con mayor conteo (preferir no-N/A)
            # Elegir la clave con mayor prioridad: max count, prefer buckets that are not 'N/A'
            def score(key):
                return (counts[key], 0 if key == 'N/A' else 1)

            best = max(counts.keys(), key=score)
            perc[best] += diff

        # Construir texto mostrando sólo buckets con al menos 1 item visible
        parts = []
        for key in ["0-18", "19-30", "31-50", "51+", "N/A"]:
            if counts.get(key, 0) > 0:
                parts.append(f"{key}: {perc.get(key,0)}%")

        self.age_distribution_label.setText("Distribución edades: " + " | ".join(parts))
            
    def add_patient(self):
        """Navegar a la página de crear nuevo paciente"""
        # 🛡️ VERIFICAR PERMISO: Solo puede crear si tiene permiso 'crear' en pacientes
        if self.parent_app and self.parent_app.is_helper:
            if not self.parent_app.puede_hacer_accion('pacientes', 'crear'):
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Permiso Denegado",
                    "No tienes permiso para crear nuevos pacientes."
                )
                return
        
        if hasattr(self.parent_app, 'mostrar_frame'):
            self.parent_app.mostrar_frame(2)  # Índice 2 = CreatePatientPage
            
    def edit_patient(self, patient):
        """Abrir diálogo para editar paciente"""
        from gui.dialogs.patient_dialog import EditPatientDialog
        dialog = EditPatientDialog(patient, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_patients()
            
    def _open_patient_details_dialog(self, patient):
        """Importa el dialogo en el punto de uso para evitar NameError."""
        from gui.dialogs.patient_dialog import PatientDetailsDialog
        # Usar la ventana principal como padre Qt: no se destruye con PatientsPage
        # y evita que el dialogo quede como ventana suelta al cerrarse.
        dialog_parent = None
        try:
            dialog_parent = self.window() if _is_qt_object_alive(self.window()) else None
        except Exception:
            dialog_parent = None
        if dialog_parent is None:
            try:
                dialog_parent = QApplication.activeWindow()
            except Exception:
                dialog_parent = None
        dialog = PatientDetailsDialog(patient, parent=dialog_parent, context_parent=self)
        dialog.exec_()

    def show_details(self, patient):
        """Mostrar detalles completos del paciente"""
        self._open_patient_details_dialog(patient)

    def abrir_detalles_paciente(self, dni):
        """Abrir detalles del paciente por DNI (método compatible con búsqueda global)"""
        patients = cargar_pacientes(self.username)
        paciente = next((p for p in patients if p.get('dni') == dni), None)
        if paciente:
            self.show_details(paciente)
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "No se encontraron los datos del paciente.")
            
    def button_hover_enter(self, event, button):
        """Efecto al pasar el mouse sobre un botón"""
        effect = button.graphicsEffect()
        if effect:
            animation = QPropertyAnimation(effect, b"color")
            animation.setDuration(200)
            animation.setStartValue(QColor(0, 0, 0, 0))
            animation.setEndValue(QColor(0, 0, 0, 50))
            animation.setEasingCurve(QEasingCurve.InOutCubic)
            animation.start()
            
    def button_hover_leave(self, event, button):
        """Efecto al quitar el mouse de un botón"""
        effect = button.graphicsEffect()
        if effect:
            animation = QPropertyAnimation(effect, b"color")
            animation.setDuration(200)
            animation.setStartValue(QColor(0, 0, 0, 50))
            animation.setEndValue(QColor(0, 0, 0, 0))
            animation.setEasingCurve(QEasingCurve.InOutCubic)
            animation.start()

    def delete_patient(self, patient):
        """Eliminar paciente tras confirmación"""
        # Crear un QMessageBox personalizado
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle('Confirmar eliminación')
        msg.setText(f'¿Está seguro de que desea eliminar al paciente {patient["nombre"]}?')
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
        
        reply = msg.exec_()
        
        if reply == QMessageBox.Yes:
            patients = cargar_pacientes(self.username)
            patient_index = None
            try:
                for idx, existing in enumerate(patients):
                    if existing == patient:
                        patient_index = idx
                        break

                if patient_index is None:
                    target_dni = str(patient.get('dni', '') or '').strip()
                    if target_dni and target_dni != '00000000':
                        matching_indexes = [
                            idx
                            for idx, existing in enumerate(patients)
                            if str(existing.get('dni', '') or '').strip() == target_dni
                        ]
                        if len(matching_indexes) == 1:
                            patient_index = matching_indexes[0]
            except Exception:
                patient_index = None

            if patient_index is None:
                QMessageBox.warning(self, "Error", "No se encontró el paciente exacto para eliminar.")
                return

            from utils.trash_manager import move_to_trash

            move_to_trash(
                self.username,
                "pacientes",
                patients[patient_index],
                source="patients_page.delete",
            )

            del patients[patient_index]
            guardar_pacientes(self.username, patients)
            
            # Actualizar variables en memoria INMEDIATAMENTE
            self.all_pacientes = patients
            self.patients_current = patients
            
            # Mostrar mensaje de éxito
            success = QMessageBox(self)
            success.setIcon(QMessageBox.Information)
            success.setWindowTitle('Éxito')
            success.setText('Paciente eliminado correctamente')
            success.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QPushButton {
                    background-color: #0078D4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #106EBE;
                }
            """)
            success.exec_()
            
            # Actualizar tabla y estadísticas
            self.load_patients()

    def load_patients(self):
        """Carga pacientes en segundo plano para no bloquear la UI."""
        if not _is_qt_object_alive(self):
            return
        if not self.username:
            return
        
        # 🛡️ Verificar permiso "ver" en pacientes
        if self.parent_app and self.parent_app.is_helper:
            from utils.helpers_manager import tiene_accion_permitida
            username_jefe = self.parent_app.username
            username_ayudante = self.parent_app.helper_name
            if not tiene_accion_permitida(username_jefe, username_ayudante, 'pacientes', 'ver'):
                print(f"⚠️ Ayudante no tiene permiso para ver pacientes")
                self.patients_table.setRowCount(0)
                self.total_patients_label.setText("Total de pacientes: 0")
                self._set_loading_state(False)
                return

        if self._patients_loading:
            return

        self._patients_loading = True
        self._set_loading_state(True, "Cargando pacientes...", "Consultando datos locales y preparando la tabla.")

        if hasattr(self, 'btn_refresh') and _is_qt_object_alive(self.btn_refresh):
            try:
                self.btn_refresh.setEnabled(False)
                self.btn_refresh.setText("Cargando...")
            except RuntimeError:
                pass

        self.load_thread = PatientLoadThread(self.username)
        self.load_thread.loaded.connect(self._on_patients_loaded)
        self.load_thread.failed.connect(self._on_patients_load_failed)
        self.load_thread.finished.connect(self._on_patients_load_finished)
        self.load_thread.start()

    def _set_loading_state(self, is_loading: bool, title: str = "", subtitle: str = ""):
        try:
            if hasattr(self, 'patients_skeleton') and self.patients_skeleton is not None:
                self.patients_skeleton.set_loading_text(title, subtitle)
            if hasattr(self, 'patients_loader_title') and self.patients_loader_title is not None and title:
                self.patients_loader_title.setText(title)
            if hasattr(self, 'patients_loader_subtitle') and self.patients_loader_subtitle is not None and subtitle:
                self.patients_loader_subtitle.setText(subtitle)
            if hasattr(self, 'patient_content_stack'):
                self.patient_content_stack.setCurrentIndex(0 if is_loading else 1)
        except Exception:
            pass

    def _populate_patients_table(self, patients):
        patients = patients if isinstance(patients, list) else []
        self.patients_current = patients
        self.patients_table.setRowCount(0)
        
        # Desactivar actualizaciones visuales para ganar velocidad
        self.patients_table.setUpdatesEnabled(False)

        try:
            for patient in patients:
                row = self.patients_table.rowCount()
                self.patients_table.insertRow(row)

                # DNI
                dni_txt = str(patient.get('dni', ''))
                dni_item = QTableWidgetItem(dni_txt)
                # Guardar UUID para identificación única
                dni_item.setData(Qt.UserRole + 5, str(patient.get('uuid', '')))
                self.patients_table.setItem(row, 0, dni_item)

                # Nombre
                nombre_item = QTableWidgetItem(str(patient.get('nombre', '')))
                self.patients_table.setItem(row, 1, nombre_item)

                # Teléfono
                tel_item = QTableWidgetItem(str(patient.get('telefono', '')))
                self.patients_table.setItem(row, 2, tel_item)

                # Email
                email_item = QTableWidgetItem(str(patient.get('email', '')))
                self.patients_table.setItem(row, 3, email_item)

                # Fecha Nac.
                self.patients_table.setItem(row, 4, QTableWidgetItem(str(patient.get('fecha_nacimiento', ''))))

                # Última Visita (USAR DATOS PRE-CALCULADOS)
                visit_text = patient.get('_display_visit_text', 'N/A')
                visit_days = patient.get('_display_visit_days', None)
                visit_iso = patient.get('_display_visit_iso', '')
                
                visita_item = QTableWidgetItem(str(visit_text))
                visita_item.setData(Qt.UserRole, visit_iso)
                visita_item.setData(Qt.UserRole + 1, int(visit_days if visit_days is not None else 0))
                self.patients_table.setItem(row, 5, visita_item)

                # Edad (USAR DATO PRE-CALCULADO)
                edad_item = QTableWidgetItem(str(patient.get('_display_edad', 'N/A')))
                self.patients_table.setItem(row, 6, edad_item)

        finally:
            self.patients_table.setUpdatesEnabled(True)

        self.total_patients_label.setText(f"Total de pacientes: {len(patients)}")
        self.last_update_label.setText(f"Última actualización: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
        try:
            self.update_age_distribution()
        except Exception:
            pass

        self.total_patients_label.setText(f"Total de pacientes: {len(patients)}")
        self.last_update_label.setText(f"Última actualización: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
        try:
            self.update_age_distribution()
        except Exception:
            pass

    def _on_patients_loaded(self, patients):
        if not _is_qt_object_alive(self):
            return
        self.all_pacientes = patients if isinstance(patients, list) else []
        self._populate_patients_table(self.all_pacientes)
        self._set_loading_state(False)

    def _on_patients_load_failed(self, error_message):
        if not _is_qt_object_alive(self):
            return
        self._set_loading_state(False)
        self.patients_table.setRowCount(0)
        self.total_patients_label.setText("Total de pacientes: 0")
        self.last_update_label.setText("No se pudieron cargar los pacientes")
        QMessageBox.warning(self, "Error", f"No se pudieron cargar los pacientes:\n{error_message}")

    def _on_patients_load_finished(self):
        if not _is_qt_object_alive(self):
            return
        self._patients_loading = False
        if hasattr(self, 'btn_refresh') and _is_qt_object_alive(self.btn_refresh):
            try:
                self.btn_refresh.setEnabled(True)
                self.btn_refresh.setText("Actualizar")
            except RuntimeError:
                pass
        try:
            self.load_thread = None
        except Exception:
            pass

    def on_patient_double_clicked(self, row, column):
        """Handler cuando el usuario hace doble click en una fila de la tabla de pacientes.

        Abre el diálogo de detalles del paciente correspondiente.
        """
        try:
            patient = None
            if hasattr(self, 'patients_current') and len(self.patients_current) > row:
                patient = self.patients_current[row]
            else:
                # Intentar identificar por UUID (almacenado en DataRole) o DNI como fallback
                dni_item = self.patients_table.item(row, 0)
                if dni_item:
                    dni = dni_item.text()
                    uuid_val = str(dni_item.data(Qt.UserRole + 5) or "")
                    
                    all_p = cargar_pacientes(self.username)
                    for p in all_p:
                        # Si tenemos UUID, es la forma más segura de identificar
                        if uuid_val and str(p.get('uuid', '')) == uuid_val:
                            patient = p
                            break
                        # Si no hay UUID (registros antiguos), usar DNI como fallback
                        elif not uuid_val and p.get('dni') == dni:
                            patient = p
                            break

            if patient:
                self.show_details(patient)
        except Exception as e:
            try:
                QMessageBox.warning(self if _is_qt_object_alive(self) else None, "Error", f"No se pudo abrir el detalle del paciente: {e}")
            except Exception:
                pass

    # ============================================================================
    # MÉTODOS PARA AUTO-REFRESH DE PACIENTES (1s local + 5s remoto)
    # ============================================================================
    
    def _start_refresh_worker(self):
        """Inicia el worker de refresh en thread separado."""
        if not self.username:
            return
        
        try:
            # ⚠️ DESACTIVADO: PatientRefreshWorker actualizaba cada 10 segundos en background
            # Ahora solo se actualiza cuando el usuario lo solicita explícitamente
            #
            # if self.refresh_worker is not None and self.refresh_worker.isRunning():
            #     self.refresh_worker.stop()
            #     self.refresh_worker.wait()
            #
            # self.refresh_worker = PatientRefreshWorker(self.username)
            # self.refresh_worker.refresh_ready.connect(self._on_refresh_data)
            # self.refresh_worker.start()
            #
            # print(f"[INFO] PatientRefreshWorker iniciado para {self.username}")
            
            self.refresh_worker = None
        except Exception as e:
            print(f"[INFO] Error iniciando PatientRefreshWorker: {e}")
    
    def _on_refresh_data(self, pacientes_remotos):
        """
        Se ejecuta cuando el worker recibe datos actualizados.
        
        Implementa MERGE strategy:
        1. Datos remotos son la fuente de verdad
        2. Pacientes locales que no existen en remoto se mantienen
        3. Guarda merged localmente para persistencia
        """
        try:
            if pacientes_remotos is None:
                return
            
            # ============================================================================
            # PASO 1: Cargar pacientes locales
            # ============================================================================
            pacientes_locales = cargar_pacientes(self.username)
            
            # ============================================================================
            # PASO 2: MERGE STRATEGY - Combinar remotos + locales sin perder datos (USANDO UUID)
            pacientes_merged = []

            # PASO 2A: Agregar TODOS los remotos (fuente de verdad)
            pacientes_merged.extend(pacientes_remotos)

            # PASO 2B: Agregar pacientes locales que NO existen en remoto
            # PRIORIZAR UUID para identificar duplicados, fallback a DNI solo si no hay UUID
            remotos_uuids = set(str(p.get('uuid', '')).strip() for p in pacientes_remotos if p.get('uuid'))
            remotos_dni = set(str(p.get('dni', '')).strip() for p in pacientes_remotos if not p.get('uuid') and p.get('dni') != "00000000")

            for p_local in pacientes_locales:
                l_uuid = str(p_local.get('uuid', '')).strip()
                l_dni = str(p_local.get('dni', '')).strip()

                if l_uuid:
                    if l_uuid not in remotos_uuids:
                        pacientes_merged.append(p_local)
                elif l_dni and l_dni != "00000000":
                    if l_dni not in remotos_dni:
                        pacientes_merged.append(p_local)
                else:
                    # Si es anónimo sin UUID local, lo mantenemos (se sincronizará después)
                    pacientes_merged.append(p_local)

            # ============================================================================
            # PASO 3: GUARDAR merged localmente (CRÍTICO para persistencia)
            # ============================================================================
            guardar_pacientes(self.username, pacientes_merged)
            
            # ============================================================================
            # PASO 4: Actualizar UI
            # ============================================================================
            self.all_pacientes = pacientes_merged
            self.patients_current = pacientes_merged
            
            # Actualizar tabla
            self.load_patients()
            
        except Exception as e:
            # Ignorar errores silenciosamente
            pass
    
    def closeEvent(self, event):
        """Detener refresh worker cuando se cierra la página."""
        try:
            if self.load_thread is not None and self.load_thread.isRunning():
                try:
                    self.load_thread.requestInterruption()
                except Exception:
                    pass
                if not self.load_thread.wait(800):
                    try:
                        self.load_thread.setParent(None)
                    except Exception:
                        pass
                    _DETACHED_PATIENT_THREADS.add(self.load_thread)
                    try:
                        self.load_thread.finished.connect(lambda t=self.load_thread: _release_detached_patient_thread(t))
                    except Exception:
                        pass
                else:
                    try:
                        self.load_thread.deleteLater()
                    except Exception:
                        pass
            self.load_thread = None
        except Exception:
            pass

        try:
            if self.refresh_worker is not None and self.refresh_worker.isRunning():
                self.refresh_worker.stop()
                self.refresh_worker.wait()
        except Exception:
            pass
        
        event.accept()
