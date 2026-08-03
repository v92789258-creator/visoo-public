"""
HomePage - PÃ¡gina Principal con Widget C++ para MÃ¡xima Velocidad

El widget C++ HomePageWidgetImproved carga y renderiza:
- GrÃ¡ficos de ventas
- EstadÃ­sticas
- MÃ©tricas

Todo en C++ para mÃ¡ximo rendimiento
"""

import logging
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QProgressBar, QStackedLayout, QSizePolicy,
    QMessageBox, QInputDialog, QScrollArea, QGridLayout, QHBoxLayout, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QVariantAnimation

logger = logging.getLogger(__name__)
_DETACHED_HOME_THREADS = set()


def _release_detached_home_thread(thread):
    try:
        _DETACHED_HOME_THREADS.discard(thread)
    except Exception:
        pass
    try:
        thread.deleteLater()
    except Exception:
        pass


def _get_home_widget_class():
    from gui.widgets.home_page_widget_improved import HomePageWidgetImproved
    return HomePageWidgetImproved


def _get_home_data_loader_class():
    from .components.home_data_loader import HomeDataLoader
    return HomeDataLoader


def _get_file_handler():
    from utils import file_handler
    return file_handler


class HomeDashboardSkeleton(QWidget):
    """Skeleton completo para el dashboard de inicio."""

    def __init__(self, parent=None, title="Cargando inicio", subtitle="Preparando panel principal..."):
        super().__init__(parent)
        self._pulse_value = 0.0
        self._cards = []
        self._title = str(title or "Cargando inicio")
        self._subtitle = str(subtitle or "Preparando panel principal...")
        self._build_ui()
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(900)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._on_anim_value_changed)
        self._apply_style()
        self.anim.start()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #F8FAFC; }")
        root.addWidget(scroll)

        host = QWidget()
        host.setStyleSheet("background: #F8FAFC;")
        scroll.setWidget(host)

        content = QVBoxLayout(host)
        content.setContentsMargins(28, 28, 28, 28)
        content.setSpacing(24)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        self.title_block = self._make_block(360, 28, radius=8)
        self.subtitle_block = self._make_block(280, 16, radius=6)
        left.addWidget(self.title_block)
        left.addSpacing(8)
        left.addWidget(self.subtitle_block)
        header_layout.addLayout(left, 1)

        branch_card = QFrame()
        branch_card.setObjectName("panel")
        branch_card.setFixedHeight(56)
        branch_layout = QHBoxLayout(branch_card)
        branch_layout.setContentsMargins(14, 10, 14, 10)
        branch_layout.setSpacing(10)
        branch_layout.addWidget(self._make_block(70, 16, radius=6))
        branch_layout.addWidget(self._make_block(300, 34, radius=10), 1)
        branch_layout.addWidget(self._make_block(92, 34, radius=10))
        self._cards.append(branch_card)
        header_layout.addWidget(branch_card, 0)
        content.addWidget(header)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)
        for i in range(4):
            stats_grid.addWidget(self._build_stat_card(), 0, i)
            stats_grid.setColumnStretch(i, 1)
        content.addLayout(stats_grid)

        row = QHBoxLayout()
        row.setSpacing(20)
        chart_panel = self._build_large_panel()
        goals_panel = self._build_side_panel()
        row.addWidget(chart_panel, 65)
        row.addWidget(goals_panel, 35)
        content.addLayout(row)

        comparison_panel = self._build_comparison_panel()
        content.addWidget(comparison_panel)

        rankings = QHBoxLayout()
        rankings.setSpacing(20)
        rankings.addWidget(self._build_ranking_panel(), 1)
        rankings.addWidget(self._build_ranking_panel(), 1)
        content.addLayout(rankings)
        content.addStretch()

    def _make_block(self, width, height, radius=8):
        block = QFrame()
        block.setProperty("skeleton_radius", int(radius))
        block.setFixedHeight(int(height))
        if width:
            block.setFixedWidth(int(width))
        self._cards.append(block)
        return block

    def _build_stat_card(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumHeight(118)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        icon = self._make_block(68, 68, radius=18)
        layout.addWidget(icon, 0, Qt.AlignTop)

        right = QVBoxLayout()
        right.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(self._make_block(120, 14, radius=6))
        top.addStretch()
        top.addWidget(self._make_block(42, 28, radius=14))
        right.addLayout(top)
        right.addWidget(self._make_block(90, 28, radius=7))
        right.addWidget(self._make_block(240, 20, radius=10))
        layout.addLayout(right, 1)
        self._cards.append(panel)
        return panel

    def _build_large_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumHeight(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addWidget(self._make_block(240, 24, radius=7))
        layout.addSpacing(12)
        chart = QFrame()
        chart.setProperty("skeleton_radius", 18)
        chart.setMinimumHeight(250)
        self._cards.append(chart)
        layout.addWidget(chart)
        self._cards.append(panel)
        return panel

    def _build_side_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumHeight(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addWidget(self._make_block(180, 24, radius=7))
        for _ in range(3):
            item = QWidget()
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(8)
            item_layout.addWidget(self._make_block(180, 14, radius=6))
            item_layout.addWidget(self._make_block(1000, 10, radius=5))
            layout.addWidget(item)
        layout.addStretch()
        layout.addWidget(self._make_block(1000, 40, radius=12))
        layout.addWidget(self._make_block(1000, 40, radius=12))
        self._cards.append(panel)
        return panel

    def _build_comparison_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumHeight(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self._make_block(360, 24, radius=7))
        layout.addSpacing(12)
        chart = QFrame()
        chart.setProperty("skeleton_radius", 18)
        chart.setMinimumHeight(220)
        self._cards.append(chart)
        layout.addWidget(chart)
        self._cards.append(panel)
        return panel

    def _build_ranking_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumHeight(240)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(self._make_block(220, 22, radius=7))
        for _ in range(4):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            row_layout.addWidget(self._make_block(42, 42, radius=12))
            inner = QVBoxLayout()
            inner.setSpacing(6)
            inner.addWidget(self._make_block(180, 14, radius=6))
            inner.addWidget(self._make_block(120, 12, radius=6))
            row_layout.addLayout(inner, 1)
            row_layout.addWidget(self._make_block(56, 18, radius=6))
            layout.addWidget(row)
        self._cards.append(panel)
        return panel

    def _on_anim_value_changed(self, value):
        try:
            self._pulse_value = float(value or 0.0)
        except Exception:
            self._pulse_value = 0.0
        self._apply_style()

    def set_loading_text(self, title="", subtitle="", status=""):
        self._title = str(title or "Cargando inicio")
        self._subtitle = str(subtitle or "Preparando panel principal...")

    def _apply_style(self):
        light = 240 + int(8 * self._pulse_value)
        mid = 227 + int(12 * self._pulse_value)
        panel_bg = "#FFFFFF"
        panel_border = "#E2E8F0"
        block_bg = f"rgb({mid},{mid},{mid})"
        chart_bg = f"rgb({light},{light},{light})"
        for widget in self._cards:
            radius = int(widget.property("skeleton_radius") or 10)
            if widget.objectName() == "panel":
                widget.setStyleSheet(
                    f"QFrame#panel {{ background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 20px; }}"
                )
            else:
                widget.setStyleSheet(
                    f"background: {chart_bg if radius >= 18 else block_bg}; border: none; border-radius: {radius}px;"
                )


class BasicHomeSkeleton(QWidget):
    """Skeleton compacto para Home en modo basico."""

    def __init__(self, parent=None, title="Cargando inicio", subtitle="Preparando modo basico..."):
        super().__init__(parent)
        self._pulse_value = 0.0
        self._blocks = []
        self._title = str(title or "Cargando inicio")
        self._subtitle = str(subtitle or "Preparando modo basico...")
        self._build_ui()
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(900)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._on_anim_value_changed)
        self.anim.start()

    def _make_block(self, width, height, radius=10):
        block = QFrame()
        block.setProperty("skeleton_radius", int(radius))
        block.setFixedHeight(int(height))
        if width:
            block.setFixedWidth(int(width))
        self._blocks.append(block)
        return block

    def _build_card(self, title_width, rows=2):
        card = QFrame()
        card.setObjectName("basic_skeleton_card")
        card.setMinimumHeight(140)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self._make_block(title_width, 22, radius=8))
        for _ in range(rows):
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(self._make_block(58, 58, radius=16))
            inner = QVBoxLayout()
            inner.setSpacing(10)
            inner.addWidget(self._make_block(180, 16, radius=7))
            inner.addWidget(self._make_block(240, 14, radius=7))
            row.addLayout(inner, 1)
            layout.addLayout(row)
        self._blocks.append(card)
        return card

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 34, 34, 34)
        root.setSpacing(22)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        content = QWidget()
        content.setObjectName("basic_skeleton_root")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        hero = QFrame()
        hero.setObjectName("basic_skeleton_card")
        hero.setMinimumHeight(220)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 28, 28, 28)
        hero_layout.setSpacing(18)
        hero_layout.addWidget(self._make_block(280, 34, radius=12))
        hero_layout.addWidget(self._make_block(420, 18, radius=9))
        hero_layout.addSpacing(8)
        hero_layout.addWidget(self._make_block(1000, 78, radius=18))
        self._blocks.append(hero)
        layout.addWidget(hero)

        layout.addWidget(self._build_card(210, rows=2))
        layout.addWidget(self._build_card(240, rows=3))
        layout.addStretch()

    def _on_anim_value_changed(self, value):
        try:
            self._pulse_value = float(value or 0.0)
        except Exception:
            self._pulse_value = 0.0
        self._apply_style()

    def set_loading_text(self, title="", subtitle="", status=""):
        self._title = str(title or "Cargando inicio")
        self._subtitle = str(subtitle or "Preparando modo basico...")

    def _apply_style(self):
        light = 242 + int(8 * self._pulse_value)
        mid = 230 + int(10 * self._pulse_value)
        panel_bg = "#FFFFFF"
        panel_border = "#D9E2EC"
        block_bg = f"rgb({mid},{mid},{mid})"
        chart_bg = f"rgb({light},{light},{light})"
        self.setStyleSheet(
            f"QWidget#basic_skeleton_root {{ background: #F6F8FC; }}"
            f"QFrame#basic_skeleton_card {{ background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 24px; }}"
        )
        for widget in self._blocks:
            if widget.objectName() in {"basic_skeleton_card"}:
                continue
            radius = int(widget.property("skeleton_radius") or 10)
            widget.setStyleSheet(
                f"background: {chart_bg if radius >= 16 else block_bg}; border: none; border-radius: {radius}px;"
            )


class StockAlertPopover(QtWidgets.QDialog):
    product_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(470, 300)
        self.setMinimumSize(430, 240)
        self.setStyleSheet("""
            QDialog {
                background: transparent;
            }
            QFrame#stockAlertCard {
                background: #FAFCFF;
                border: 1px solid #DCE5F2;
                border-radius: 14px;
            }
            QLabel#stockAlertTitle {
                color: #0F172A;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#stockAlertCaption {
                color: #64748B;
                font-size: 11px;
            }
            QLabel#stockAlertEmpty {
                color: #64748B;
                font-size: 12px;
                font-weight: 600;
                padding: 18px;
                border: 1px dashed #D7E0EC;
                border-radius: 10px;
                background: #FFFFFF;
            }
            QTableWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                gridline-color: #EDF2F7;
                selection-background-color: #FEECEC;
                selection-color: #0F172A;
            }
            QHeaderView::section {
                background: #F8FAFD;
                color: #475569;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                padding: 7px 8px;
                font-weight: 700;
            }
            QPushButton {
                min-height: 32px;
                padding: 0 14px;
                border-radius: 9px;
            }
            QPushButton#stockAlertCloseTop {
                min-height: 24px;
                min-width: 24px;
                max-width: 24px;
                padding: 0;
                border-radius: 12px;
                border: none;
                background: transparent;
                color: #64748B;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton#stockAlertCloseTop:hover {
                background: #EEF2F8;
                color: #0F172A;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("stockAlertCard")
        root_layout.addWidget(self.card)

        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QtGui.QColor(15, 23, 42, 42))
        self.card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        header_text_layout = QVBoxLayout()
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        header_text_layout.setSpacing(2)

        self.title_label = QLabel("Productos sin stock")
        self.title_label.setObjectName("stockAlertTitle")
        header_text_layout.addWidget(self.title_label)

        self.caption_label = QLabel("Estos productos ya no tienen unidades disponibles.")
        self.caption_label.setObjectName("stockAlertCaption")
        header_text_layout.addWidget(self.caption_label)

        header_layout.addLayout(header_text_layout, 1)

        close_top_button = QtWidgets.QPushButton("×")
        close_top_button.setObjectName("stockAlertCloseTop")
        close_top_button.setCursor(Qt.PointingHandCursor)
        close_top_button.clicked.connect(self.accept)
        header_layout.addWidget(close_top_button, 0, Qt.AlignTop)

        layout.addLayout(header_layout)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Producto", "Codigo", "Marca", "Stock"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.table.cellClicked.connect(self._emit_selected_row)
        layout.addWidget(self.table, 1)

        self.empty_label = QLabel("No hay productos sin stock en este momento.")
        self.empty_label.setObjectName("stockAlertEmpty")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.addStretch()
        close_button = QtWidgets.QPushButton("Cerrar")
        close_button.clicked.connect(self.accept)
        footer_layout.addWidget(close_button)
        layout.addLayout(footer_layout)
        self._rows = []

    def _emit_selected_row(self, row, _column):
        try:
            payload = dict((self._rows or [])[row] or {})
        except Exception:
            payload = {}
        if payload:
            self.product_selected.emit(payload)

    def set_items(self, rows):
        rows = list(rows or [])
        self._rows = rows
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(row.get("nombre", ""))))
            self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(str(row.get("codigo", ""))))
            self.table.setItem(row_index, 2, QtWidgets.QTableWidgetItem(str(row.get("marca", ""))))
            self.table.setItem(row_index, 3, QtWidgets.QTableWidgetItem(str(row.get("stock", ""))))

        total = len(rows)
        if total == 1:
            self.title_label.setText("1 producto sin stock")
        else:
            self.title_label.setText(f"{total} productos sin stock")
        self.caption_label.setText(
            "Revisa estos productos antes de seguir vendiendo."
            if total else
            "No hay alertas de stock agotado por ahora."
        )
        self.table.setVisible(bool(rows))
        self.empty_label.setVisible(not bool(rows))
        if rows:
            self.table.selectRow(0)
        visible_rows = min(max(total, 1), 6)
        target_height = 178 + (visible_rows * 34)
        self.resize(self.width(), min(360, target_height))


class DataLoaderThread(QThread):
    """Thread para cargar datos sin bloquear UI - Optimizado"""
    data_ready = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, username, allow_remote_restore=True, fast_start=False, parent=None):
        super().__init__(parent)
        self.username = username
        self.allow_remote_restore = bool(allow_remote_restore)
        self.fast_start = bool(fast_start)
    
    def run(self):
        try:
            HomeDataLoader = _get_home_data_loader_class()
            loader = HomeDataLoader(self.username)
            data = loader.load_all(
                allow_remote_restore=self.allow_remote_restore,
                fast_start=self.fast_start,
            )
            if isinstance(data, dict):
                data["_allow_remote_restore"] = self.allow_remote_restore
                data["_fast_start"] = self.fast_start
            self.data_ready.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class HomePage(QWidget):
    """PÃ¡gina Home - Widget C++ + Carga rÃ¡pida de datos
    
    Optimizado para velocidad:
    - Widget C++ renderiza grÃ¡ficos ultra rÃ¡pido
    - Datos cargados en background thread
    - Sin bloqueos UI
    """
    
    # SeÃ±al: emitida cuando UI estÃ¡ lista
    data_loaded = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        self.home_widget = None
        self.loader_thread = None
        self._content_stack = None
        self._home_loader_widget = None
        self._home_loader_title_label = None
        self._home_loader_subtitle_label = None
        self._home_loader_status_label = None
        self._home_loader_timer = None
        self._home_loader_step = 0
        self._load_request_id = 0
        self._data_loaded_emitted = False
        self._is_closing = False
        self._stock_alert_rows = []
        self._stock_alert_popover = None
        self._deferred_home_refresh_token = 0
        self._last_loaded_ventas = [] # Almacenar para carga diferida de graficos
        self._home_remote_refresh_scheduled = False
        self._show_loader_request_id = None
        
        # Inicializar UI mÃ­nimo
        self._setup_ui()
        
        # Construir la home pesada en el siguiente tick para que el loader pinte primero.
        QTimer.singleShot(0, self._prepare_initial_home_load)

    def _is_basic_mode_enabled(self):
        try:
            from utils.file_handler import is_modo_basico
            return bool(is_modo_basico(self.username))
        except Exception:
            return False
    
    def _setup_ui(self):
        """Configura solo el contenedor mínimo; la home pesada se difiere."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        stack_host = QWidget(self)
        self._content_stack = QStackedLayout(stack_host)
        self._content_stack.setContentsMargins(0, 0, 0, 0)
        self._content_stack.setSpacing(0)

        self._home_loader_widget = self._build_home_loader_widget()
        self._content_stack.addWidget(self._home_loader_widget)

        layout.addWidget(stack_host)
        self._show_home_loader()

    def _prepare_initial_home_load(self):
        if self._is_closing:
            return
        # Primero mostrar solo el loader y cargar datos en background.
        # El widget pesado se construye cuando ya hay datos listos para evitar
        # congelar el arranque con red lenta o equipos justos.
        QTimer.singleShot(
            0,
            lambda: self._load_data_background(
                allow_remote_restore=False,
                show_loader=True,
                fast_start=True,
            ),
        )

    def _ensure_home_widget_ready(self):
        if self.home_widget is not None or self._is_closing:
            return

        optica_name = "VISO"
        try:
            file_handler = _get_file_handler()
            # No consultar remoto en el hilo principal durante el arranque.
            # Con internet lento esto congelaba la app justo al abrir Home.
            datos_optica = file_handler.cargar_datos_optica(self.username, prefer_remote=False) or {}
            optica_name = (
                str(datos_optica.get("nombre_optica", "") or "").strip()
                or file_handler.cargar_nombre_optica(self.username)
                or "VISO"
            )
        except Exception:
            optica_name = "VISO"

        if self._is_basic_mode_enabled():
            self.home_widget = ModoBasicoWidget(
                parent_app=self.parent_app,
                optica_name=optica_name,
                parent=self
            )
        else:
            HomePageWidgetImproved = _get_home_widget_class()
            self.home_widget = HomePageWidgetImproved(
                optica_name=optica_name,
                username=self.username,
                parent=self
            )
        self.home_widget.parent_window = self.parent_app

        if self._content_stack is not None and self._content_stack.indexOf(self.home_widget) == -1:
            self._content_stack.insertWidget(0, self.home_widget)
        self._bind_dashboard_actions()

    def _bind_dashboard_actions(self):
        if self.home_widget is None:
            return
        try:
            stock_card = getattr(self.home_widget, "stat_cards", {}).get("stock")
            if stock_card is not None and hasattr(stock_card, "trend_clicked"):
                stock_card.trend_clicked.connect(self._open_stock_alert_popover)
                if hasattr(stock_card, "setTrendInteractive"):
                    stock_card.setTrendInteractive(False)
        except Exception:
            pass

    def _build_home_loader_widget(self):
        """Construye loader visual de Home."""
        if self._is_basic_mode_enabled():
            widget = BasicHomeSkeleton(
                self,
                title="Cargando inicio",
                subtitle="Preparando modo basico...",
            )
        else:
            widget = HomeDashboardSkeleton(
                self,
                title="Cargando inicio",
                subtitle="Preparando panel principal...",
            )
        self._home_loader_title_label = None
        self._home_loader_subtitle_label = None
        self._home_loader_status_label = widget
        return widget

    def _show_home_loader(self, title="Cargando inicio", subtitle="Preparando panel principal..."):
        if self._home_loader_widget is not None and hasattr(self._home_loader_widget, "set_loading_text"):
            self._home_loader_widget.set_loading_text(
                str(title or "Cargando inicio"),
                str(subtitle or "Preparando panel principal..."),
                "Conectando con la nube",
            )
        else:
            if self._home_loader_title_label is not None:
                self._home_loader_title_label.setText(str(title or "Cargando inicio"))
            if self._home_loader_subtitle_label is not None:
                self._home_loader_subtitle_label.setText(str(subtitle or "Preparando panel principal..."))

        if self._content_stack is not None and self._home_loader_widget is not None:
            self._content_stack.setCurrentWidget(self._home_loader_widget)
        self._start_home_loader_animation()

    def _hide_home_loader(self):
        self._stop_home_loader_animation()
        if self._content_stack is not None and self.home_widget is not None:
            self._content_stack.setCurrentWidget(self.home_widget)

    def _start_home_loader_animation(self):
        self._stop_home_loader_animation()
        self._home_loader_step = 0
        self._home_loader_timer = QTimer(self)
        self._home_loader_timer.setInterval(340)
        self._home_loader_timer.timeout.connect(self._tick_home_loader)
        self._home_loader_timer.start()
        self._tick_home_loader()

    def _stop_home_loader_animation(self):
        try:
            if self._home_loader_timer is not None:
                self._home_loader_timer.stop()
                self._home_loader_timer.deleteLater()
        except Exception:
            pass
        self._home_loader_timer = None
        self._home_loader_step = 0

    def _tick_home_loader(self):
        label = self._home_loader_status_label
        if label is None:
            return

        frames = (
            "Conectando con la nube",
            "Conectando con la nube.",
            "Conectando con la nube..",
            "Conectando con la nube...",
            "Cargando metricas",
            "Cargando metricas.",
            "Cargando metricas..",
            "Cargando metricas...",
        )
        idx = int(getattr(self, "_home_loader_step", 0)) % len(frames)
        try:
            if hasattr(label, "set_loading_text"):
                label.set_loading_text("Cargando inicio", "Sincronizando datos de sucursales...", frames[idx])
            else:
                label.setText(frames[idx])
        except Exception:
            pass
        self._home_loader_step = idx + 1
    
    def _load_data_background(self, allow_remote_restore=True, show_loader=True, fast_start=False):
        """Carga datos en thread separado para no bloquear UI"""
        if self._is_closing:
            return
        self._load_request_id += 1
        request_id = self._load_request_id
        if show_loader or self.home_widget is None:
            self._show_home_loader(
                title="Cargando inicio",
                subtitle="Sincronizando datos de sucursales..."
            )
            self._show_loader_request_id = request_id
        else:
            if self._show_loader_request_id is not None:
                self._hide_home_loader()
            self._show_loader_request_id = None

        self._dispose_loader_thread(wait_ms=500, detach_if_running=True)
        
        # Cargar datos en thread
        self.loader_thread = DataLoaderThread(
            self.username,
            allow_remote_restore=allow_remote_restore,
            fast_start=fast_start,
            parent=self,
        )
        self.loader_thread.data_ready.connect(
            lambda dashboard_data, rid=request_id: self._on_data_loaded(rid, dashboard_data)
        )
        self.loader_thread.error.connect(
            lambda error_msg, rid=request_id: self._on_data_error(rid, error_msg)
        )
        self.loader_thread.finished.connect(
            lambda rid=request_id: self._on_loader_finished(rid)
        )
        self.loader_thread.start()

    def _dispose_loader_thread(self, wait_ms: int = 500, detach_if_running: bool = False):
        thread = self.loader_thread
        if thread is None:
            return

        try:
            running = thread.isRunning()
        except RuntimeError:
            self.loader_thread = None
            return

        if running:
            try:
                thread.requestInterruption()
            except Exception:
                pass
            try:
                thread.quit()
            except Exception:
                pass
            try:
                finished = thread.wait(int(wait_ms))
            except Exception:
                finished = False
            if not finished and detach_if_running:
                try:
                    thread.setParent(None)
                except Exception:
                    pass
                _DETACHED_HOME_THREADS.add(thread)
                try:
                    thread.finished.connect(lambda t=thread: _release_detached_home_thread(t))
                except Exception:
                    pass
                self.loader_thread = None
                return

        try:
            thread.deleteLater()
        except Exception:
            pass
        self.loader_thread = None

    def _on_loader_finished(self, request_id):
        if self._is_closing:
            return
        if request_id != self._load_request_id:
            return
        try:
            if self.loader_thread is not None and not self.loader_thread.isRunning():
                self.loader_thread = None
        except RuntimeError:
            self.loader_thread = None
        finally:
            if self._show_loader_request_id == request_id:
                self._ensure_home_widget_ready()
                self._hide_home_loader()
                self._show_loader_request_id = None

    def _schedule_silent_remote_refresh_once(self):
        if self._home_remote_refresh_scheduled or self._is_closing:
            return
        self._home_remote_refresh_scheduled = True
        QTimer.singleShot(1200, lambda: self._load_data_background(allow_remote_restore=True, show_loader=False))

    @staticmethod
    def _trend_colors():
        return {
            "positive": "#16A34A",
            "negative": "#DC2626",
            "warning": "#D97706",
            "neutral": "#6B7280",
        }

    def _set_card_trend(self, card_key, text, color):
        try:
            card = getattr(self.home_widget, "stat_cards", {}).get(card_key)
            if card is not None and hasattr(card, "setTrend"):
                card.setTrend(str(text or ""), color=color)
        except Exception:
            pass

    def _build_out_of_stock_rows(self, productos):
        rows = []
        for producto in productos or []:
            if not isinstance(producto, dict):
                continue
            try:
                stock_value = float(producto.get("stock") or 0)
            except (TypeError, ValueError):
                stock_value = 0.0
            if stock_value > 0:
                continue
            nombre = str(producto.get("nombre", "") or "").strip() or "Producto"
            codigo = str(producto.get("codigo", "") or "").strip()
            marca = str(producto.get("marca", "") or "").strip()
            if float(stock_value).is_integer():
                stock_label = str(int(stock_value))
            else:
                stock_label = f"{stock_value:.2f}"
            rows.append({
                "nombre": nombre,
                "codigo": codigo,
                "marca": marca,
                "stock": stock_label,
                "producto": dict(producto),
            })
        rows.sort(key=lambda item: (str(item.get("nombre", "")).lower(), str(item.get("codigo", "")).lower()))
        return rows

    def _set_stock_card_interactive(self, enabled: bool):
        try:
            stock_card = getattr(self.home_widget, "stat_cards", {}).get("stock")
            if stock_card is not None and hasattr(stock_card, "setTrendInteractive"):
                stock_card.setTrendInteractive(bool(enabled))
        except Exception:
            pass

    def _open_stock_alert_popover(self):
        rows = list(getattr(self, "_stock_alert_rows", []) or [])
        if not rows:
            return

        dialog = StockAlertPopover(self)
        dialog.set_items(rows)
        dialog.product_selected.connect(lambda row, d=dialog: self._handle_stock_alert_product_clicked(row, d))

        try:
            stock_card = getattr(self.home_widget, "stat_cards", {}).get("stock")
            anchor_widget = getattr(stock_card, "lbl_trend", None) if stock_card is not None else None
            if anchor_widget is not None:
                anchor_bottom_right = anchor_widget.mapToGlobal(anchor_widget.rect().bottomRight())
                screen = QtWidgets.QApplication.screenAt(anchor_bottom_right)
                if screen is None:
                    screen = QtWidgets.QApplication.primaryScreen()
                available = screen.availableGeometry() if screen is not None else self.geometry()
                dialog_width = dialog.width()
                dialog_height = dialog.height()
                x = anchor_bottom_right.x() - dialog_width
                y = anchor_bottom_right.y() + 8
                if y + dialog_height > available.bottom() - 8:
                    y = anchor_bottom_right.y() - dialog_height - anchor_widget.height() - 8
                x = max(available.left() + 8, min(x, available.right() - dialog_width - 8))
                y = max(available.top() + 8, min(y, available.bottom() - dialog_height - 8))
                dialog.move(x, y)
        except Exception:
            pass

        self._stock_alert_popover = dialog
        dialog.exec_()
        self._stock_alert_popover = None

    def _is_global_stock_edit_blocked(self):
        try:
            selected_code = str(getattr(self.home_widget, "selected_branch_code", "") or "").strip().upper()
            selected_label = str(getattr(self.home_widget, "selected_branch_label", "") or "").strip().lower()
            if selected_code:
                return False
            return selected_label == "todas las sucursales"
        except Exception:
            return False

    def _handle_stock_alert_product_clicked(self, row, dialog):
        payload = dict(row or {})
        producto_ref = payload.get("producto") if isinstance(payload.get("producto"), dict) else {}
        if not producto_ref:
            return

        if self._is_global_stock_edit_blocked():
            QMessageBox.warning(
                self,
                "Selecciona una sucursal",
                "Para añadir stock desde este resumen primero selecciona una sucursal concreta.",
            )
            return

        dialog.accept()

        nombre = str(producto_ref.get("nombre", "") or "Producto").strip()
        codigo = str(producto_ref.get("codigo", "") or "").strip()
        try:
            stock_actual = float(producto_ref.get("stock") or 0)
        except (TypeError, ValueError):
            stock_actual = 0.0

        cantidad, ok = QInputDialog.getDouble(
            self,
            "Añadir stock",
            f"{nombre}\n\nStock actual: {stock_actual:g}\nCantidad a agregar:",
            1.0,
            0.01,
            1000000.0,
            2,
        )
        if not ok:
            return

        cantidad = float(cantidad or 0)
        if cantidad <= 0:
            return

        try:
            file_handler = _get_file_handler()
            productos = file_handler.cargar_productos(self.username) or []
            if not isinstance(productos, list):
                productos = []

            target_index = -1
            target_codigo = str(producto_ref.get("codigo", "") or "").strip().upper()
            target_id = str(producto_ref.get("id", "") or "").strip()
            target_nombre = str(producto_ref.get("nombre", "") or "").strip().lower()

            for idx, producto in enumerate(productos):
                if not isinstance(producto, dict):
                    continue
                codigo_cmp = str(producto.get("codigo", "") or "").strip().upper()
                id_cmp = str(producto.get("id", "") or "").strip()
                nombre_cmp = str(producto.get("nombre", "") or "").strip().lower()
                if target_codigo and codigo_cmp == target_codigo:
                    target_index = idx
                    break
                if target_id and id_cmp == target_id:
                    target_index = idx
                    break
                if target_nombre and nombre_cmp == target_nombre:
                    target_index = idx
                    break

            if target_index < 0:
                QMessageBox.warning(
                    self,
                    "Producto no encontrado",
                    "No se encontró el producto en el inventario actual para actualizar stock.",
                )
                return

            producto_actual = dict(productos[target_index])
            try:
                stock_existente = float(producto_actual.get("stock") or 0)
            except (TypeError, ValueError):
                stock_existente = 0.0
            nuevo_stock = stock_existente + cantidad
            if float(nuevo_stock).is_integer():
                producto_actual["stock"] = int(nuevo_stock)
            else:
                producto_actual["stock"] = round(nuevo_stock, 2)

            productos[target_index] = producto_actual
            file_handler.guardar_productos(self.username, productos)

            QMessageBox.information(
                self,
                "Stock actualizado",
                f"Se añadieron {cantidad:g} unidades a {nombre}.",
            )
            self._load_data_background(allow_remote_restore=True)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo actualizar el stock: {str(exc)}",
            )

    def _apply_dashboard_card_trends(self, loader, pacientes, productos, ventas):
        colors = self._trend_colors()
        patient_summary = loader.summarize_patients(pacientes)
        inventory_summary = loader.summarize_inventory(productos)
        sales_summary = loader.summarize_sales(ventas)

        last_30_patients = patient_summary.get("last_30_days", 0)
        if last_30_patients > 0:
            self._set_card_trend("patients", f"{last_30_patients} nuevos en 30 dias", colors["positive"])
        else:
            self._set_card_trend("patients", "Sin nuevos en 30 dias", colors["neutral"])

        out_of_stock = inventory_summary.get("out_of_stock", 0)
        low_stock = inventory_summary.get("low_stock", 0)
        if out_of_stock > 0:
            self._set_card_trend("stock", f"{out_of_stock} productos sin stock", colors["negative"])
            self._set_stock_card_interactive(True)
        elif low_stock > 0:
            self._set_card_trend("stock", f"{low_stock} productos con stock bajo", colors["warning"])
            self._set_stock_card_interactive(False)
        else:
            self._set_card_trend("stock", "Inventario sin alertas", colors["positive"])
            self._set_stock_card_interactive(False)

        current_month = patient_summary.get("current_month", 0)
        previous_month = patient_summary.get("previous_month", 0)
        if previous_month > 0:
            delta = ((current_month - previous_month) / previous_month) * 100
            color = colors["positive"] if delta > 0 else colors["negative"] if delta < 0 else colors["neutral"]
            prefix = "+" if delta > 0 else ""
            self._set_card_trend("monthly", f"{prefix}{delta:.1f}% vs mes anterior", color)
        elif current_month > 0:
            self._set_card_trend("monthly", f"{current_month} registrados este mes", colors["positive"])
        else:
            self._set_card_trend("monthly", "Sin registros este mes", colors["neutral"])

        current_week = sales_summary.get("current_week", 0.0)
        previous_week = sales_summary.get("previous_week", 0.0)
        if previous_week > 0:
            delta = ((current_week - previous_week) / previous_week) * 100
            color = colors["positive"] if delta > 0 else colors["negative"] if delta < 0 else colors["neutral"]
            prefix = "+" if delta > 0 else ""
            self._set_card_trend("sales", f"{prefix}{delta:.1f}% vs 7 dias previos", color)
        elif current_week > 0:
            self._set_card_trend("sales", f"S/. {current_week:,.2f} esta semana", colors["positive"])
        else:
            self._set_card_trend("sales", "Sin ventas esta semana", colors["neutral"])

    def _schedule_deferred_home_components(self, request_id):
        self._deferred_home_refresh_token += 1
        token = self._deferred_home_refresh_token

        def _run(stage):
            if self._is_closing:
                return
            if request_id != self._load_request_id:
                return
            if token != self._deferred_home_refresh_token:
                return
            try:
                stage()
            except Exception:
                logger.exception("[HOME] Error en carga diferida")

        QTimer.singleShot(120, lambda: _run(self._refresh_comparison_chart))
        QTimer.singleShot(240, lambda: _run(self._refresh_top_customers))
        QTimer.singleShot(360, lambda: _run(self._refresh_top_products))

    def _refresh_comparison_chart(self):
        if hasattr(self.home_widget, 'comparison_chart') and hasattr(self.home_widget.comparison_chart, 'load_real_data'):
            self.home_widget.comparison_chart.load_real_data(sales_data=self._last_loaded_ventas)
            self.home_widget.comparison_chart.update()

    def _refresh_top_customers(self):
        if hasattr(self.home_widget, 'top_customers') and hasattr(self.home_widget.top_customers, 'load_data'):
            self.home_widget.top_customers.load_data(sales_data=self._last_loaded_ventas)

    def _refresh_top_products(self):
        if hasattr(self.home_widget, 'top_products') and hasattr(self.home_widget.top_products, 'load_data'):
            self.home_widget.top_products.load_data(sales_data=self._last_loaded_ventas)
    
    def _on_data_loaded(self, request_id, dashboard_data):
        """Callback cuando datos estÃ¡n listos - Enviar al widget C++"""
        if self._is_closing:
            return
        if request_id != self._load_request_id:
            return

        try:
            self._ensure_home_widget_ready()
            HomeDataLoader = _get_home_data_loader_class()
            loader = HomeDataLoader(self.username)

            # 1. Total Pacientes
            pacientes = dashboard_data.get('pacientes', [])
            if hasattr(self.home_widget, 'setPatientCount'):
                self.home_widget.setPatientCount(len(pacientes))
            
            # 2. Total Productos
            productos = dashboard_data.get('productos', [])
            self._stock_alert_rows = self._build_out_of_stock_rows(productos)
            if hasattr(self.home_widget, 'setProductCount'):
                self.home_widget.setProductCount(len(productos))
            
            # 3. Pacientes del Mes (Nuevo cÃ¡lculo)
            if hasattr(self.home_widget, 'setMonthlyPatients'):
                count_month = loader.count_patients_this_month(pacientes)
                self.home_widget.setMonthlyPatients(count_month)
            
            # 4. Ventas Totales
            ventas = dashboard_data.get('ventas', [])
            self._last_loaded_ventas = ventas # Guardar para carga diferida de otros componentes
            
            allow_remote_restore = bool(dashboard_data.get("_allow_remote_restore"))
            if hasattr(self.home_widget, 'set_sales_data'):
                self.home_widget.set_sales_data(
                    ventas,
                    allow_remote_restore=allow_remote_restore,
                )
            if hasattr(self.home_widget, 'setTotalSales'):
                total = loader.calculate_total_sales(ventas)
                self.home_widget.setTotalSales(total)
            self._apply_dashboard_card_trends(loader, pacientes, productos, ventas)
            
            # 5. GrÃ¡fico de Ventas
            if hasattr(self.home_widget, 'updateSalesChart'):
                # Usar el helper del loader para preparar datos consistentes
                chart_data = loader.prepare_sales_chart(ventas, days=15)
                self.home_widget.updateSalesChart(chart_data['amounts'], chart_data['labels'])

            logger.info(
                "[HOME] Dashboard refrescado: pacientes=%s productos=%s ventas=%s",
                len(pacientes) if isinstance(pacientes, list) else 0,
                len(productos) if isinstance(productos, list) else 0,
                len(ventas) if isinstance(ventas, list) else 0
            )
        except Exception as e:
            logger.exception("[HOME] Error procesando datos: %s", e)
        finally:
            if self._show_loader_request_id == request_id:
                self._hide_home_loader()
                self._show_loader_request_id = None
            self._emit_data_loaded()
            self._schedule_deferred_home_components(request_id)
            if not bool(dashboard_data.get("_allow_remote_restore")):
                self._schedule_silent_remote_refresh_once()
    
    def _on_data_error(self, request_id, error_msg):
        """Error cargando datos"""
        if self._is_closing:
            return
        if request_id != self._load_request_id:
            return
        logger.warning("[HOME] Error cargando datos: %s", error_msg)
        if self._show_loader_request_id == request_id:
            self._ensure_home_widget_ready()
            self._hide_home_loader()
            self._show_loader_request_id = None
        self._emit_data_loaded()
    
    def _emit_data_loaded(self):
        """Emite seÃ±al UNA SOLA VEZ"""
        if self._is_closing:
            return
        if not self._data_loaded_emitted:
            self._data_loaded_emitted = True
            QTimer.singleShot(50, self.data_loaded.emit)

    def closeEvent(self, event):
        self._is_closing = True
        self._stop_home_loader_animation()
        self._dispose_loader_thread(wait_ms=750, detach_if_running=True)

        try:
            if self.home_widget is not None:
                for ranking_attr in ("top_customers", "top_products"):
                    ranking = getattr(self.home_widget, ranking_attr, None)
                    if ranking is not None and hasattr(ranking, "cleanup"):
                        ranking.cleanup()
        except Exception:
            pass

        super().closeEvent(event)

class ModoBasicoWidget(QWidget):
    def __init__(self, parent_app, optica_name, parent=None):
        super().__init__(parent)
        self.parent_app = parent_app
        self.optica_name = optica_name
        self.username = getattr(parent_app, "username", "")
        self._hidden_sales_exporter = None
        self._basic_sales_history_window = None
        self._basic_windows = {}
        self._setup_ui()

    def _get_basic_action_definitions(self):
        return {
            4: ("REGISTRAR VENTA", "#2196F3"),
            2: ("NUEVA GRADUACION", "#4CAF50"),
            1: ("VER PACIENTES", "#0EA5A4"),
            3: ("VER INVENTARIO", "#7C3AED"),
            6: ("ABRIR CALENDARIO", "#EC4899"),
        }

    def _load_quick_actions(self):
        try:
            from utils.file_handler import get_modo_basico_quick_actions
            actions = get_modo_basico_quick_actions(self.username)
        except Exception:
            actions = [4, 2]
        valid_actions = [page for page in actions if page in self._get_basic_action_definitions()]
        return valid_actions or [4, 2]

    def _create_action_button(self, page_index, title, color):
        btn = QPushButton(title)
        btn.setMinimumSize(260, 120)
        btn.setStyleSheet(
            "QPushButton {"
            f"font-size: 22px; font-weight: bold; background-color: {color}; color: white; "
            "border-radius: 18px; padding: 18px; text-align: center;"
            "}"
            "QPushButton:hover { border: 2px solid rgba(255, 255, 255, 0.55); }"
        )
        btn.clicked.connect(lambda _=False, idx=page_index: self._open_basic_action(idx))
        return btn

    def _create_callback_button(self, title, color, callback):
        btn = QPushButton(title)
        btn.setMinimumSize(250, 88)
        btn.setStyleSheet(
            "QPushButton {"
            f"font-size: 19px; font-weight: bold; background-color: {color}; color: white; "
            "border-radius: 17px; padding: 14px; text-align: center;"
            "}"
            "QPushButton:hover { border: 3px solid rgba(255, 255, 255, 0.60); }"
        )
        btn.clicked.connect(callback)
        return btn

    def _open_basic_action(self, page_index):
        if not self.parent_app:
            return
        if page_index == 1:
            self._open_basic_patients_search()
            return
        if page_index == 3:
            self._open_basic_inventory()
            return
        if page_index == 6:
            self._open_basic_appointments()
            return
        self.parent_app.mostrar_frame(page_index)

    def _show_basic_window(self, key, window_class, **kwargs):
        try:
            if self.parent_app is None or not hasattr(self.parent_app, "show_basic_embedded_page"):
                raise ValueError("La pagina basica no se pudo integrar en la ventana principal.")
            page = self.parent_app.show_basic_embedded_page(key, window_class, **kwargs)
            if page is not None:
                self._basic_windows[key] = page
        except Exception as exc:
            QMessageBox.warning(self, "Modo basico", f"No se pudo abrir la pantalla.\n\n{exc}")

    def _open_basic_patients_search(self):
        from gui.main_window_pages.basic_patients_page import BasicPatientsPage
        self._show_basic_window("patients_search", BasicPatientsPage, initial_mode="search")

    def _open_basic_patient_new(self):
        from gui.main_window_pages.basic_patients_page import BasicPatientsPage
        self._show_basic_window("patients_new", BasicPatientsPage, initial_mode="new")
        page = self._basic_windows.get("patients_new")
        if page is not None and hasattr(page, "_set_mode"):
            page._set_mode("new")

    def _open_basic_debts(self):
        from gui.main_window_pages.basic_debts_page import BasicDebtsPage
        self._show_basic_window("debts", BasicDebtsPage)

    def _open_basic_contracts(self):
        from gui.main_window_pages.basic_contracts_page import BasicContractsPage
        self._show_basic_window("contracts", BasicContractsPage)

    def _open_basic_appointments(self):
        from gui.main_window_pages.basic_appointments_page import BasicAppointmentsPage
        self._show_basic_window("appointments", BasicAppointmentsPage)

    def _open_basic_inventory(self):
        from gui.main_window_pages.basic_inventory_page import BasicInventoryPage
        self._show_basic_window("inventory", BasicInventoryPage)

    def _open_basic_new_product(self):
        from gui.main_window_pages.basic_product_create_page import BasicProductCreatePage
        self._show_basic_window("new_product", BasicProductCreatePage)

    def _open_basic_daily_report(self):
        from gui.main_window_pages.basic_daily_report_page import BasicDailyReportPage
        self._show_basic_window("daily_report", BasicDailyReportPage)

    def _exit_basic_mode(self):
        answer = QMessageBox.question(
            self,
            "Salir del modo basico",
            "VISO se reiniciara para volver al modo profesional. Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            from utils.file_handler import set_modo_basico
            if not set_modo_basico(self.username, False):
                raise ValueError("No se pudo guardar el cambio de modo.")
            if self.parent_app is not None and hasattr(self.parent_app, "restart_app"):
                self.parent_app.restart_app()
        except Exception as exc:
            QMessageBox.warning(self, "Modo basico", f"No se pudo salir del modo basico.\n\n{exc}")

    def _open_today_sales_in_browser(self):
        sales_page = getattr(self.parent_app, "page_4", None) or getattr(self.parent_app, "sales_page", None)
        if sales_page is None or not hasattr(sales_page, "_export_today_sales_pdf"):
            try:
                from gui.main_window_pages.sales_page import SalesHistoryPage
                if self._hidden_sales_exporter is None or not hasattr(self._hidden_sales_exporter, "_export_today_sales_pdf"):
                    self._hidden_sales_exporter = SalesHistoryPage(self.parent_app)
                    self._hidden_sales_exporter.hide()
                sales_page = self._hidden_sales_exporter
            except Exception as exc:
                QMessageBox.warning(self, "Ventas del dia", f"No se pudo preparar el generador de ventas del dia.\n\n{exc}")
                return

        try:
            sales_page._export_today_sales_pdf()
        except Exception as exc:
            QMessageBox.critical(self, "Ventas del dia", f"No se pudo generar el PDF de ventas del dia.\n\n{exc}")

    def _open_basic_sales_history(self):
        try:
            from gui.main_window_pages.basic_sales_page_history import BasicSalesHistoryPage
            self._show_basic_window("sales_history", BasicSalesHistoryPage)
            self._basic_sales_history_window = self._basic_windows.get("sales_history")
            if self._basic_sales_history_window is not None and hasattr(self._basic_sales_history_window, "reload_data"):
                self._basic_sales_history_window.reload_data()
        except Exception as exc:
            QMessageBox.warning(self, "Ventas", f"No se pudo abrir la vista de ventas.\n\n{exc}")

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 30, 36, 40)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Saludo
        saludo = QLabel(f"Hola, {self.optica_name}")
        saludo.setStyleSheet("font-size: 36px; font-weight: bold; color: #1976d2;")
        saludo.setAlignment(Qt.AlignCenter)
        layout.addWidget(saludo)

        # Estad�sticas (se llenar�n luego)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(40)
        stats_layout.setAlignment(Qt.AlignCenter)

        self.lbl_ganancias = QLabel("Hoy ganaste: S/ 0.00")
        self.lbl_ganancias.setStyleSheet("font-size: 24px; color: #2E7D32; font-weight: bold; background: #E8F5E9; padding: 20px; border-radius: 10px;")
        self.lbl_ganancias.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.lbl_ganancias)

        self.lbl_pacientes = QLabel("Registraste: 0 pacientes")
        self.lbl_pacientes.setStyleSheet("font-size: 24px; color: #1565C0; font-weight: bold; background: #E3F2FD; padding: 20px; border-radius: 10px;")
        self.lbl_pacientes.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.lbl_pacientes)

        layout.addLayout(stats_layout)

        layout.addSpacing(20)

        subtitle = QLabel("Accesos rápidos del modo fácil")
        subtitle.setStyleSheet("font-size: 18px; color: #475569; font-weight: 600;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        actions_grid = QGridLayout()
        actions_grid.setHorizontalSpacing(24)
        actions_grid.setVerticalSpacing(24)

        actions = self._load_quick_actions()
        definitions = self._get_basic_action_definitions()
        for idx, page_index in enumerate(actions):
            title, color = definitions.get(page_index, (f"ABRIR {page_index}", "#475569"))
            button = self._create_action_button(page_index, title, color)
            row = idx // 2
            col = idx % 2
            actions_grid.addWidget(button, row, col)

        layout.addLayout(actions_grid)

        tools_title = QLabel("Herramientas basicas")
        tools_title.setStyleSheet("font-size: 24px; color: #0F172A; font-weight: 800;")
        tools_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(tools_title)

        tools = [
            ("NUEVO PACIENTE", "#0284C7", self._open_basic_patient_new),
            ("BUSCAR PACIENTE", "#0F766E", self._open_basic_patients_search),
            ("NUEVO PRODUCTO", "#0F9D58", self._open_basic_new_product),
            ("VER VENTAS", "#2563EB", self._open_basic_sales_history),
            ("DEUDAS", "#DC2626", self._open_basic_debts),
            ("CONTRATOS", "#7C3AED", self._open_basic_contracts),
            ("CITAS", "#DB2777", self._open_basic_appointments),
            ("INVENTARIO BASICO", "#B45309", self._open_basic_inventory),
            ("REPORTE DEL DIA", "#15803D", self._open_basic_daily_report),
            ("ABRIR PDF DEL DIA", "#0F172A", self._open_today_sales_in_browser),
            ("SALIR DEL MODO BASICO", "#475569", self._exit_basic_mode),
        ]
        tools_grid = QGridLayout()
        tools_grid.setHorizontalSpacing(18)
        tools_grid.setVerticalSpacing(18)
        for index, (title, color, callback) in enumerate(tools):
            tools_grid.addWidget(self._create_callback_button(title, color, callback), index // 3, index % 3)
        layout.addLayout(tools_grid)

        layout.addStretch()

    def setTotalSales(self, total):
        pass # Se calcula en set_sales_data

    def setPatientCount(self, count):
        pass

    def setMonthlyPatients(self, count):
        pass

    def _get_today_str(self):
        from datetime import datetime
        return datetime.now().strftime("%d/%m/%Y")

    def set_sales_data(self, ventas, allow_remote_restore=False):
        from gui.main_window_pages.basic_mode_common import date_in_filter, safe_float

        total_hoy = 0.0
        count_pacientes = 0

        for v in ventas:
            if not isinstance(v, dict): continue
            if date_in_filter(v.get("fecha"), "today"):
                total_hoy += safe_float(v.get("total"))

                # Aprovechar las ventas/graduaciones de hoy para contar pacientes
                if str(v.get("tipo_venta", "")).lower() == "graduacion" or str(v.get("origen", "")).lower() == "graduacion":
                    count_pacientes += 1

        self.lbl_ganancias.setText(f"Hoy ganaste: S/ {total_hoy:.2f}")
        self.lbl_pacientes.setText(f"Registraste: {count_pacientes} pacientes")

    # Mocks para no romper _on_data_loaded
    def setProductCount(self, count): pass
    def updateSalesChart(self, amounts, labels): pass
