"""
HomePageWidgetImproved - Orquestador de Dashboard
Ensambla componentes especializados para crear el dashboard principal.
Cada componente (cards, charts, rankings, dialogs) estÃ¡ en su propio mÃ³dulo.

ReducciÃ³n de cÃ³digo: 1800+ lÃ­neas â†’ 350 lÃ­neas
Modularidad: Todo estÃ¡ divido en componentes reutilizables
Mantenibilidad: Cambios localizados a archivos especÃ­ficos
"""
import logging
import os
import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QGraphicsDropShadowEffect, QFrame, QApplication, QProgressBar,
    QScrollArea, QPushButton, QMessageBox, QComboBox, QBoxLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtSvg import QSvgWidget

from gui.dialogs.goals_config_dialog import GoalsConfigDialog
from gui.dialogs.goals_calculator import GoalsCalculator, AVAILABLE_GOALS

# Importar componentes especializados
from gui.widgets.components import (
    ModernStatCard,
    ClickableLabel,
    SalesBarChart,
    ComparisonLineChart,
    TopCustomersRanking,
    TopProductsRanking,
    DayPurchasesDialog,
)

logger = logging.getLogger(__name__)


def _load_sales_data(username, allow_remote_restore=True):
    try:
        from utils.file_handler import cargar_ventas_dashboard

        ventas = cargar_ventas_dashboard(
            username,
            allow_remote_restore=allow_remote_restore,
        ) or []
    except Exception:
        ventas = []

    if isinstance(ventas, dict):
        ventas = list(ventas.values())
    return ventas if isinstance(ventas, list) else []

# --- CONFIGURACIÃ“N DE TEMA (MODERNO CLARO) ---
THEME = {
    "bg_app": "#F6F7F9",             # Fondo neutro
    "card_bg": "#FFFFFF",            # Fondo Tarjeta Blanco puro
    "card_hover": "#F3F4F6",         # Fondo Hover sutil
    "card_border": "#E5E7EB",        # Borde de tarjeta
    "accent": "#111827",             # Texto principal (gris/negro)
    "text_main": "#111827",          # Gris oscuro para tÃ­tulos
    "text_dim": "#6B7280",           # Gris para subtÃ­tulos
    "border": "#E5E7EB",             # Borde sutil gris claro
    "border_hover": "#D1D5DB",       # Borde al pasar mouse
    "icon_bg": "#F3F4F6",            # Fondo de Iconos neutro
    "success": "#16A34A",            # Verde Indicador
    "primary": "#1F2937",            # Ã‰nfasis sobrio
}


def _normalize_ui_text(value: str) -> str:
    """Corrige texto mojibake común antes de mostrarlo en la UI."""
    text = str(value or "").strip()
    if not text:
        return ""

    replacements = {
        "Mi Ãƒâ€œptica": "Mi Óptica",
        "Ãƒâ€œ": "Ó",
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã": "Á",
        "Ã‰": "É",
        "Ã": "Í",
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Ã±": "ñ",
        "Ã‘": "Ñ",
        "Â¿": "¿",
        "Â¡": "¡",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    if any(ch in text for ch in ("Ã", "Â", "â")):
        for enc in ("latin1", "cp1252"):
            try:
                candidate = text.encode(enc).decode("utf-8")
            except Exception:
                continue
            if candidate and candidate != text:
                text = candidate
                break

    return text


def _enrich_snapshot_with_sales(usuario_madre: str, branch_code: str, snapshot: dict) -> dict:
    """Asegura que ventas quede sincronizado y limpie caches viejos si ya no existe."""
    normalized = dict(snapshot or {}) if isinstance(snapshot, dict) else {}
    if "ventas" in normalized:
        return normalized

    try:
        from utils.api_handler import descargar_snapshot_dispositivo_nube

        ok_sales, payload_sales, _msg_sales = descargar_snapshot_dispositivo_nube(
            usuario_madre=usuario_madre,
            codigo_dispositivo=branch_code,
            dataset="ventas",
            include_data=True,
        )
        if ok_sales and isinstance(payload_sales, dict):
            if isinstance(payload_sales.get("snapshot"), dict):
                sales_snapshot = payload_sales.get("snapshot") or {}
                if "ventas" in sales_snapshot:
                    normalized["ventas"] = sales_snapshot.get("ventas") or []
                    return normalized
            if "data" in payload_sales:
                normalized["ventas"] = payload_sales.get("data") or []
                return normalized
    except Exception:
        pass

    normalized["ventas"] = []
    return normalized


class BranchSnapshotLoader(QThread):
    """Descarga snapshot de sucursal sin bloquear la UI."""
    loaded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, username: str, branch_code: str, branch_label: str = ""):
        super().__init__()
        self.username = str(username or "").strip()
        self.branch_code = str(branch_code or "").strip().upper()
        self.branch_label = str(branch_label or "").strip()

    def run(self):
        try:
            from utils.file_handler import (
                resolve_username,
                save_branch_snapshot_datasets,
                get_branch_cache_data_dir,
            )
            from utils.api_handler import (
                descargar_snapshot_dispositivo_nube,
                obtener_clientes_remoto,
                obtener_pacientes_remoto,
                obtener_productos_remoto,
            )

            usuario_madre = resolve_username(self.username)
            ok, payload, msg = descargar_snapshot_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=self.branch_code,
                dataset=None,
                include_data=True
            )
            if not ok:
                # Compatibilidad: si no existe carpeta snapshot (404), usar endpoints legacy de BD.
                raw_error = ""
                if isinstance(payload, dict):
                    raw_error = str(payload.get("error", "")).strip()
                msg_text = str(msg or "").strip()
                error_text = f"{msg_text} {raw_error}".lower()
                is_not_found = ("404" in error_text) or ("not found" in error_text) or ("folder not found" in error_text)

                if is_not_found:
                    legacy_snapshot = {
                        "clientes": obtener_clientes_remoto(usuario_madre, codigo_dispositivo=self.branch_code) or [],
                        "pacientes": obtener_pacientes_remoto(usuario_madre, codigo_dispositivo=self.branch_code) or [],
                        "productos": obtener_productos_remoto(usuario_madre, codigo_dispositivo=self.branch_code) or [],
                    }

                    # Si la nube legacy no devolvió nada, no sobreescribir con vacíos:
                    # intentar reutilizar cache local existente de la sucursal.
                    has_legacy_data = any(
                        (isinstance(v, list) and len(v) > 0) or (isinstance(v, dict) and len(v) > 0)
                        for v in legacy_snapshot.values()
                    )

                    if not has_legacy_data:
                        local_summary = {}
                        try:
                            local_dir = Path(get_branch_cache_data_dir(usuario_madre, self.branch_code))
                            for json_file in local_dir.glob("*.json"):
                                name = json_file.stem.lower()
                                try:
                                    with open(json_file, "r", encoding="utf-8") as f:
                                        data = json.load(f)
                                    if isinstance(data, list) and len(data) > 0:
                                        local_summary[name] = len(data)
                                    elif isinstance(data, dict) and len(data) > 0:
                                        local_summary[name] = len(data)
                                except Exception:
                                    continue
                        except Exception:
                            local_summary = {}

                        if local_summary:
                            self.loaded.emit({
                                "username": usuario_madre,
                                "branch_code": self.branch_code,
                                "branch_label": self.branch_label,
                                "summary": local_summary,
                                "raw_payload": payload if isinstance(payload, dict) else {},
                                "fallback_source": "local_cache"
                            })
                            return

                    summary = save_branch_snapshot_datasets(usuario_madre, self.branch_code, legacy_snapshot)
                    self.loaded.emit({
                        "username": usuario_madre,
                        "branch_code": self.branch_code,
                        "branch_label": self.branch_label,
                        "summary": summary,
                        "raw_payload": payload if isinstance(payload, dict) else {},
                        "fallback_source": "legacy_db"
                    })
                    return

                self.failed.emit(msg or "No se pudo descargar datos de la sucursal")
                return

            snapshot = {}
            if isinstance(payload, dict):
                if isinstance(payload.get("snapshot"), dict):
                    snapshot = payload.get("snapshot") or {}
                elif payload.get("dataset") and "data" in payload:
                    ds_name = str(payload.get("dataset")).strip().lower()
                    snapshot = {ds_name: payload.get("data")}

            if not snapshot:
                # Sucursal válida pero sin datasets subidos aún
                snapshot = {}

            snapshot = _enrich_snapshot_with_sales(usuario_madre, self.branch_code, snapshot)
            summary = save_branch_snapshot_datasets(usuario_madre, self.branch_code, snapshot)
            self.loaded.emit({
                "username": usuario_madre,
                "branch_code": self.branch_code,
                "branch_label": self.branch_label,
                "summary": summary,
                "raw_payload": payload if isinstance(payload, dict) else {}
            })
        except Exception as e:
            self.failed.emit(str(e))


class BranchListLoader(QThread):
    """Descarga lista de sucursales desde nube sin bloquear la UI."""
    loaded = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, username: str):
        super().__init__()
        self.username = str(username or "").strip()

    def run(self):
        try:
            from utils.api_handler import listar_dispositivos_hijos_remoto

            ok, remote_devices, msg = listar_dispositivos_hijos_remoto(self.username)
            if not ok:
                self.failed.emit(str(msg or "No se pudo obtener sucursales desde la nube"))
                return

            devices = remote_devices if isinstance(remote_devices, list) else []
            filtered = [d for d in devices if isinstance(d, dict)]
            self.loaded.emit(filtered)
        except Exception as e:
            self.failed.emit(str(e))


class AllBranchesSnapshotLoader(QThread):
    """Refresca el cache local de todas las sucursales visibles para el dashboard global."""
    loaded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, username: str, devices: list):
        super().__init__()
        self.username = str(username or "").strip()
        self.devices = [d for d in (devices or []) if isinstance(d, dict)]

    def run(self):
        try:
            from utils.file_handler import resolve_username, save_branch_snapshot_datasets
            from utils.api_handler import (
                descargar_snapshot_dispositivo_nube,
                obtener_clientes_remoto,
                obtener_pacientes_remoto,
                obtener_productos_remoto,
            )

            usuario_madre = resolve_username(self.username)
            summary = {}

            for device in self.devices:
                estado = str(device.get("estado", "activo")).strip().lower()
                if estado == "bloqueado":
                    continue

                branch_code = str(device.get("codigo_dispositivo", "")).strip().upper()
                if not branch_code:
                    continue

                ok, payload, msg = descargar_snapshot_dispositivo_nube(
                    usuario_madre=usuario_madre,
                    codigo_dispositivo=branch_code,
                    dataset=None,
                    include_data=True,
                )

                if ok:
                    snapshot = {}
                    if isinstance(payload, dict):
                        if isinstance(payload.get("snapshot"), dict):
                            snapshot = payload.get("snapshot") or {}
                        elif payload.get("dataset") and "data" in payload:
                            ds_name = str(payload.get("dataset")).strip().lower()
                            snapshot = {ds_name: payload.get("data")}
                    snapshot = _enrich_snapshot_with_sales(usuario_madre, branch_code, snapshot or {})
                    branch_summary = save_branch_snapshot_datasets(usuario_madre, branch_code, snapshot)
                    summary[branch_code] = branch_summary
                    continue

                raw_error = ""
                if isinstance(payload, dict):
                    raw_error = str(payload.get("error", "")).strip()
                msg_text = str(msg or "").strip()
                error_text = f"{msg_text} {raw_error}".lower()
                is_not_found = ("404" in error_text) or ("not found" in error_text) or ("folder not found" in error_text)
                if not is_not_found:
                    raise RuntimeError(msg or f"No se pudo descargar datos de {branch_code}")

                legacy_snapshot = {
                    "clientes": obtener_clientes_remoto(usuario_madre, codigo_dispositivo=branch_code) or [],
                    "pacientes": obtener_pacientes_remoto(usuario_madre, codigo_dispositivo=branch_code) or [],
                    "productos": obtener_productos_remoto(usuario_madre, codigo_dispositivo=branch_code) or [],
                }
                branch_summary = save_branch_snapshot_datasets(usuario_madre, branch_code, legacy_snapshot)
                summary[branch_code] = branch_summary

            self.loaded.emit(summary)
        except Exception as e:
            self.failed.emit(str(e))


class HomePageWidgetImproved(QWidget):
    """PÃ¡gina principal Dashboard Pro - Orquestador de componentes"""
    
    def __init__(
        self,
        optica_name: str = "VISO",
        username: str = "default",
        parent=None,
        parent_window=None,
    ):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.optica_name = _normalize_ui_text(optica_name)
        self.username = username
        # parent_window: referencia a la ventana principal para navegaciÃ³n/diÃ¡logos
        # parent (Qt): padre real para que el layout lo maneje correctamente
        self.parent_window = parent_window or parent
        self.goals_container = None
        self.goals_layout = None
        self.goals_widgets = []
        self.chart_widget = None  # Inicializar para evitar AttributeError
        self.selected_branch_code = ""
        self.selected_branch_label = self._default_global_branch_label()
        self._last_applied_branch_code = ""
        self._branch_loader_thread = None
        self._branch_bulk_loader_thread = None
        self._branch_list_loader_thread = None
        self._branch_request_seq = 0
        self._branch_request_show_error = {}
        self._branch_snapshot_loading = False
        self._branch_list_loading = False
        self._branch_combo_backup = {"items": [], "current_code": ""}
        self._suppress_branch_change = False
        self._pending_global_branch_refresh = False
        self._did_first_show_reload = False
        self._latest_sales_data = []
        self._latest_sales_data_initialized = False
        self._latest_sales_allow_remote_restore = True
        self._deferred_sections_built = False
        self._deferred_sections_host = None
        self._deferred_sections_layout = None
        try:
            from utils.file_handler import get_active_branch_context
            ctx = get_active_branch_context(self.username)
            self.selected_branch_code = str(ctx.get("code", "")).strip().upper()
            self.selected_branch_label = str(ctx.get("label", "")).strip() or self._default_global_branch_label()
            self._last_applied_branch_code = self.selected_branch_code
        except Exception:
            pass
        
        # Estilo global
        self.setStyleSheet(f"""
            QWidget#MainContent {{
                background-color: {THEME['bg_app']};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {THEME['bg_app']};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: #D1D5DB;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #9CA3AF;
            }}
        """)
        
        self.stat_cards = {}
        self.setup_ui_with_scroll()
    
    def setup_ui_with_scroll(self):
        """Configura la UI con soporte para scroll vertical"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {THEME['bg_app']};
            }}
        """)
        # Guardar referencia para cÃ¡lculos responsivos (ancho real del viewport)
        self._scroll_area = scroll
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet(f"background-color: {THEME['bg_app']};")
        content_layout = QVBoxLayout(scroll_widget)
        content_layout.setContentsMargins(28, 28, 28, 28)
        content_layout.setSpacing(24)
        self._content_layout = content_layout
        
        # === HEADER ===
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_box = QVBoxLayout()
        self.title_label = QLabel(f"Bienvenido {self.optica_name}")
        self.title_label.setFont(QFont("Segoe UI", 24, QFont.DemiBold))
        self.title_label.setStyleSheet(f"color: {THEME['accent']};")
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.title_label.setMinimumWidth(0)
        
        sub = QLabel("Visión general del sistema y métricas clave")
        sub.setFont(QFont("Segoe UI", 11))
        sub.setStyleSheet(f"color: {THEME['text_dim']};")
        sub.setWordWrap(True)
        
        title_box.addWidget(self.title_label)
        title_box.addWidget(sub)
        header_layout.addLayout(title_box)

        # Selector de sucursal (solo para dispositivo madre)
        self.branch_selector_container = QWidget()
        self.branch_selector_container.setObjectName("HomeBranchSelector")
        branch_layout = QHBoxLayout(self.branch_selector_container)
        branch_layout.setContentsMargins(14, 10, 14, 10)
        branch_layout.setSpacing(10)
        self.branch_selector_container.setStyleSheet(f"""
            QWidget#HomeBranchSelector {{
                background: {THEME['card_bg']};
                border: 1px solid {THEME['border']};
                border-radius: 16px;
            }}
        """)

        self.branch_label_widget = QLabel(f"{self._branch_input_label_text()}:")
        self.branch_label_widget.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.branch_label_widget.setStyleSheet(f"color: {THEME['text_dim']};")

        self.branch_combo = QComboBox()
        self.branch_combo.setMinimumWidth(240)
        self.branch_combo.setFixedHeight(34)
        self.branch_combo.setFont(QFont("Segoe UI", 10))
        self.branch_combo.setStyleSheet(f"""
            QComboBox {{
                background: #F7FAFF;
                border: 1px solid #D7E5FF;
                border-radius: 10px;
                padding: 6px 10px;
                color: {THEME['text_main']};
            }}
            QComboBox:hover {{
                border: 1px solid #BFD3FF;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}
            QComboBox QAbstractItemView {{
                background: {THEME['card_bg']};
                border: 1px solid {THEME['border']};
                selection-background-color: #EFF6FF;
                selection-color: {THEME['text_main']};
                outline: 0;
            }}
        """)
        self.branch_combo.currentIndexChanged.connect(self._on_branch_selected)

        self.branch_refresh_btn = QPushButton("Actualizar")
        self.branch_refresh_btn.setFixedHeight(34)
        self.branch_refresh_btn.setCursor(Qt.PointingHandCursor)
        self.branch_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['accent']};
                border: 1px solid {THEME['accent']};
                border-radius: 10px;
                padding: 0 12px;
                color: white;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {THEME['primary']};
                border: 1px solid {THEME['primary']};
            }}
        """)
        self.branch_refresh_btn.clicked.connect(lambda: self._reload_branch_selector(fetch_remote=True))

        branch_layout.addWidget(self.branch_label_widget)
        branch_layout.addWidget(self.branch_combo)
        branch_layout.addWidget(self.branch_refresh_btn)

        # Ocultar inmediatamente si no es dispositivo madre para evitar parpadeo
        if not self._is_madre_device():
            self.branch_selector_container.setVisible(False)

        header_layout.addStretch()
        header_layout.addWidget(self.branch_selector_container, 0, Qt.AlignVCenter)
        content_layout.addWidget(header_container)
        self._reload_branch_selector(fetch_remote=False)
        
        # === STAT CARDS ===
        cards_grid = QGridLayout()
        cards_grid.setSpacing(16)
        
        icons_dir = os.path.join(os.path.dirname(__file__), '..', 'icons')
        self.stat_cards['patients'] = ModernStatCard("Total Pacientes", "0", os.path.join(icons_dir, 'patients.svg'), "")
        self.stat_cards['stock'] = ModernStatCard("Stock Total", "0", os.path.join(icons_dir, 'stock.svg'), "")
        self.stat_cards['monthly'] = ModernStatCard("Pacientes Mes", "0", os.path.join(icons_dir, 'monthly.svg'), "")
        self.stat_cards['sales'] = ModernStatCard("Ventas Totales", "S/. 0.00", os.path.join(icons_dir, 'ventas_card.svg'), "")
        
        cards_grid.addWidget(self.stat_cards['patients'], 0, 0)
        cards_grid.addWidget(self.stat_cards['stock'], 0, 1)
        cards_grid.addWidget(self.stat_cards['monthly'], 0, 2)
        cards_grid.addWidget(self.stat_cards['sales'], 0, 3)
        
        for i in range(4):
            cards_grid.setColumnStretch(i, 1)
        
        self.cards_grid = cards_grid
        content_layout.addLayout(cards_grid)

        self._deferred_sections_host = QWidget()
        self._deferred_sections_layout = QVBoxLayout(self._deferred_sections_host)
        self._deferred_sections_layout.setContentsMargins(0, 0, 0, 0)
        self._deferred_sections_layout.setSpacing(0)
        content_layout.addWidget(self._deferred_sections_host)
        
        content_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        self._apply_responsive_layout()
        QTimer.singleShot(0, self._build_deferred_sections)

    def _build_deferred_sections(self):
        if self._deferred_sections_built:
            return
        host_layout = getattr(self, "_deferred_sections_layout", None)
        if host_layout is None:
            return

        self._deferred_sections_built = True

        self._charts_layout = QHBoxLayout()
        self._charts_layout.setSpacing(20)

        self._chart_panel = self._create_chart_panel()
        self._chart_panel.setMinimumWidth(0)
        self._charts_layout.addWidget(self._chart_panel, 65)

        self._goals_panel = self._create_goals_panel()
        self._goals_panel.setMinimumWidth(0)
        self._charts_layout.addWidget(self._goals_panel, 35)

        host_layout.addLayout(self._charts_layout)
        host_layout.addSpacing(30)

        self._comparison_panel = self._create_comparison_panel()
        host_layout.addWidget(self._comparison_panel)
        host_layout.addSpacing(30)

        self._rankings_layout = self._create_rankings_layout()
        host_layout.addLayout(self._rankings_layout)

        if self._latest_sales_data_initialized:
            self.set_sales_data(
                self._latest_sales_data,
                allow_remote_restore=self._latest_sales_allow_remote_restore,
            )
            try:
                if hasattr(self, "comparison_chart") and hasattr(self.comparison_chart, "load_real_data"):
                    self.comparison_chart.load_real_data(
                        sales_data=self._latest_sales_data,
                        allow_remote_restore=self._latest_sales_allow_remote_restore,
                    )
                if hasattr(self, "top_customers") and hasattr(self.top_customers, "load_data"):
                    self.top_customers.load_data(
                        sales_data=self._latest_sales_data,
                        allow_remote_restore=self._latest_sales_allow_remote_restore,
                    )
                if hasattr(self, "top_products") and hasattr(self.top_products, "load_data"):
                    self.top_products.load_data(
                        sales_data=self._latest_sales_data,
                        allow_remote_restore=self._latest_sales_allow_remote_restore,
                    )
            except Exception:
                logger.exception("[HOME] Error construyendo secciones diferidas")

        self._apply_responsive_layout()

    def updateOpticalName(self, name):
        """Actualiza el nombre de la optica en el titulo"""
        self.optica_name = _normalize_ui_text(name)
        if hasattr(self, 'title_label'):
            self.title_label.setText(f"Bienvenido {self.optica_name}")

    def _apply_responsive_layout(self):
        """Ajusta layouts segÃºn ancho disponible (evita clipping horizontal)."""
        try:
            width = 0
            try:
                scroll = getattr(self, "_scroll_area", None)
                if scroll is not None and hasattr(scroll, "viewport"):
                    width = int(scroll.viewport().width() or 0)
            except Exception:
                width = 0

            self_w = int(self.width() or 0)
            if width > 200 and self_w > 0:
                width = max(self_w, width)
            elif width <= 200:
                width = self_w
            if width <= 0:
                return

            charts_layout = getattr(self, "_charts_layout", None)
            chart_panel = getattr(self, "_chart_panel", None)
            goals_panel = getattr(self, "_goals_panel", None)

            min_side_by_side = 1100
            try:
                if chart_panel is not None and goals_panel is not None and charts_layout is not None:
                    min_side_by_side = int(
                        (chart_panel.minimumSizeHint().width() or 0)
                        + (goals_panel.minimumSizeHint().width() or 0)
                        + int(charts_layout.spacing() or 0)
                        + 64
                    )
            except Exception:
                min_side_by_side = 1100

            narrow = width < min_side_by_side
            very_narrow = width < 900

            if charts_layout is not None:
                charts_layout.setDirection(QBoxLayout.TopToBottom if narrow else QBoxLayout.LeftToRight)
                charts_layout.setSpacing(16 if narrow else 20)
                try:
                    charts_layout.setStretch(0, 0 if narrow else 65)
                    charts_layout.setStretch(1, 0 if narrow else 35)
                except Exception:
                    pass

            rankings_layout = getattr(self, "_rankings_layout", None)
            if rankings_layout is not None:
                rankings_layout.setDirection(QBoxLayout.TopToBottom if narrow else QBoxLayout.LeftToRight)
                rankings_layout.setSpacing(16 if narrow else 20)

            content_layout = getattr(self, "_content_layout", None)
            if content_layout is not None:
                if very_narrow:
                    content_layout.setContentsMargins(18, 18, 18, 18)
                    content_layout.setSpacing(18)
                else:
                    content_layout.setContentsMargins(28, 28, 28, 28)
                    content_layout.setSpacing(24)

            branch_combo = getattr(self, "branch_combo", None)
            if branch_combo is not None:
                branch_combo.setMinimumWidth(180 if very_narrow else 240)
        except Exception as e:
            logger.error(f"[HOME] Error aplicando layout responsivo: {e}")

    def _config_dispositivo_path(self) -> Path:
        root = Path(__file__).resolve().parents[2]
        return root / "VISO" / str(self.username) / "data" / "config_dispositivo.json"

    def _dispositivos_hijos_path(self) -> Path:
        root = Path(__file__).resolve().parents[2]
        return root / "VISO" / str(self.username) / "data" / "dispositivos_hijos.json"

    def _load_device_config(self) -> dict:
        path = self._config_dispositivo_path()
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            # Si el archivo queda vacio/corrupto, resetear a {} para evitar warnings repetidos.
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            logger.warning(f"[HOME] Error leyendo config_dispositivo (se reseteo a default): {e}")
            return {}

    def _resolve_worker_branch_code(self, config: dict | None = None) -> str:
        cfg = config if isinstance(config, dict) else self._load_device_config()
        raw = (
            cfg.get("codigo_dispositivo_hijo")
            or cfg.get("codigo_dispositivo_trabajador")
            or cfg.get("codigo_dispositivo")
            or ""
        )
        return str(raw or "").strip().upper()

    def _looks_like_worker_device(self, config: dict | None = None) -> bool:
        cfg = config if isinstance(config, dict) else self._load_device_config()
        role = str(cfg.get("tipo_dispositivo", "")).strip().lower()
        if role in ["trabajador", "hijo", "dispositivo hijo", "dispositivo trabajador"]:
            return True

        worker_code = self._resolve_worker_branch_code(cfg)
        worker_id = str(cfg.get("dispositivo_hijo_id", "")).strip()
        linked_from_login = bool(cfg.get("vinculado_desde_login"))
        worker_name = str(cfg.get("dispositivo_hijo_nombre", "")).strip()

        return bool(worker_code and (worker_id or linked_from_login or worker_name))

    def _is_madre_device(self) -> bool:
        parent = self.parent_window
        if parent is not None and hasattr(parent, "es_dispositivo_madre"):
            try:
                return bool(parent.es_dispositivo_madre())
            except Exception:
                pass

        return not self._looks_like_worker_device()

    def _is_single_branch_mode(self) -> bool:
        parent = self.parent_window
        if parent is not None and hasattr(parent, "_get_madre_label"):
            try:
                return str(parent._get_madre_label()).strip().lower().endswith("unico")
            except Exception:
                pass
        return len(self._load_local_child_devices()) == 0

    def _default_global_branch_label(self) -> str:
        return "Sucursal unica" if self._is_single_branch_mode() else "Todas las sucursales"

    def _branch_input_label_text(self) -> str:
        return "Sucursal unica" if self._is_single_branch_mode() else "Sucursal"

    def _load_local_child_devices(self) -> list:
        path = self._dispositivos_hijos_path()
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            return [d for d in data if isinstance(d, dict)]
        except Exception as e:
            logger.warning(f"[HOME] Error leyendo dispositivos_hijos: {e}")
            return []

    def _save_local_child_devices(self, devices: list):
        try:
            path = self._dispositivos_hijos_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(devices, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[HOME] Error guardando dispositivos_hijos local: {e}")

    def _populate_branch_combo_from_devices(self, devices: list):
        if not hasattr(self, "branch_combo"):
            return

        previous_code = str(self.selected_branch_code or "").strip().upper()
        self._suppress_branch_change = True
        self.branch_combo.blockSignals(True)
        self.branch_combo.clear()
        self.branch_combo.addItem(self._default_global_branch_label(), "")

        seen_codes = set()
        for d in (devices or []):
            if not isinstance(d, dict):
                continue
            estado = str(d.get("estado", "activo")).strip().lower()
            if estado == "bloqueado":
                continue
            code = str(d.get("codigo_dispositivo", "")).strip().upper()
            if not code or code in seen_codes:
                continue
            seen_codes.add(code)

            nombre = str(d.get("nombre_optica", "Sucursal")).strip() or "Sucursal"
            ciudad = str(d.get("ciudad", "")).strip()
            if ciudad:
                label = f"{nombre} - {ciudad} ({code})"
            else:
                label = f"{nombre} ({code})"
            self.branch_combo.addItem(label, code)

        index = self.branch_combo.findData(previous_code) if previous_code else 0
        if index < 0:
            index = 0
        self.branch_combo.setCurrentIndex(index)
        self.branch_combo.blockSignals(False)
        self._suppress_branch_change = False
        self._on_branch_selected(self.branch_combo.currentIndex())

    def _reload_branch_selector(self, fetch_remote: bool = False):
        if not hasattr(self, "branch_selector_container"):
            return

        if hasattr(self, "branch_label_widget"):
            self.branch_label_widget.setText(f"{self._branch_input_label_text()}:")

        if not self._is_madre_device():
            self.branch_selector_container.setVisible(False)
            config = self._load_device_config() or {}
            worker_code = self._resolve_worker_branch_code(config)
            worker_owner = str(config.get("usuario_madre", self.username)).strip() or str(self.username)
            worker_name = str(config.get("dispositivo_hijo_nombre", "Sucursal")).strip() or "Sucursal"
            worker_city = str(config.get("dispositivo_hijo_ciudad", "")).strip()
            if worker_code:
                if worker_city:
                    worker_label = f"{worker_name} - {worker_city} ({worker_code})"
                else:
                    worker_label = f"{worker_name} ({worker_code})"
            else:
                worker_label = "Sucursal asignada"

            previous_code = str(self._last_applied_branch_code or "").strip().upper()
            context_changed = worker_code != previous_code
            try:
                from utils.file_handler import (
                    set_active_branch_context,
                    clear_active_branch_context,
                    clear_branch_runtime_caches,
                )
                if worker_code:
                    set_active_branch_context(self.username, worker_code, worker_label)
                    self.selected_branch_code = worker_code
                    self.selected_branch_label = worker_label
                    self._last_applied_branch_code = worker_code
                else:
                    clear_active_branch_context(self.username)
                    self.selected_branch_code = ""
                    self.selected_branch_label = self._default_global_branch_label()
                    self._last_applied_branch_code = ""
                clear_branch_runtime_caches()
            except Exception:
                pass

            if self.parent_window is not None:
                setattr(self.parent_window, "selected_branch_code", self.selected_branch_code)
                setattr(self.parent_window, "selected_branch_label", self.selected_branch_label)

            should_refresh = bool(context_changed or fetch_remote)
            if should_refresh and self.parent_window is not None and hasattr(self.parent_window, "on_branch_context_changed"):
                self.parent_window.on_branch_context_changed(self.selected_branch_code, self.selected_branch_label)

            # En modo trabajador siempre intentar bajar snapshot remoto de su sucursal
            # para no depender solo de cache local.
            if worker_code and fetch_remote:
                self._start_branch_snapshot_download(
                    branch_code=worker_code,
                    branch_label=worker_label,
                    source_username=worker_owner,
                    show_error=False,
                    force_restart=bool(fetch_remote),
                )
            return

        self.branch_selector_container.setVisible(True)
        self._populate_branch_combo_from_devices(self._load_local_child_devices())
        if fetch_remote:
            current_code = str(self.selected_branch_code or "").strip().upper()
            current_label = str(self.selected_branch_label or "").strip()
            if current_code:
                self._start_branch_snapshot_download(
                    branch_code=current_code,
                    branch_label=current_label,
                    source_username=str(self.username),
                    show_error=True,
                    force_restart=True,
                )
            else:
                self._pending_global_branch_refresh = True
        if fetch_remote:
            self._fetch_branch_list_from_cloud()

    def _set_branch_loading_ui(self, loading: bool):
        self._branch_snapshot_loading = bool(loading)
        self._apply_branch_controls_ui()

    def _set_branch_list_loading_ui(self, loading: bool):
        self._branch_list_loading = bool(loading)
        self._apply_branch_controls_ui()

    def _apply_branch_controls_ui(self):
        loading = bool(self._branch_snapshot_loading or self._branch_list_loading)
        if hasattr(self, "branch_combo"):
            self.branch_combo.setEnabled(not loading)
        if hasattr(self, "branch_refresh_btn"):
            self.branch_refresh_btn.setEnabled(not loading)
            if self._branch_list_loading:
                self.branch_refresh_btn.setText("Buscando...")
            elif self._branch_snapshot_loading:
                self.branch_refresh_btn.setText("Cargando...")
            else:
                self.branch_refresh_btn.setText("Actualizar")

    def _fetch_branch_list_from_cloud(self):
        if self._branch_list_loader_thread is not None and self._branch_list_loader_thread.isRunning():
            return

        self._set_branch_list_loading_ui(True)
        self._backup_branch_combo_state()
        self._suppress_branch_change = True
        self.branch_combo.blockSignals(True)
        self.branch_combo.clear()
        loading_label = "Cargando sucursal unica..." if self._is_single_branch_mode() else "Buscando sucursales..."
        self.branch_combo.addItem(loading_label, "")
        self.branch_combo.setCurrentIndex(0)
        self.branch_combo.blockSignals(False)

        loader = BranchListLoader(username=str(self.username))
        self._branch_list_loader_thread = loader
        loader.loaded.connect(self._on_branch_list_loaded)
        loader.failed.connect(self._on_branch_list_failed)
        loader.finished.connect(lambda current_loader=loader: self._on_branch_list_loader_finished(current_loader))
        loader.start()

    def _on_branch_list_loaded(self, devices: list):
        try:
            if isinstance(devices, list):
                self._save_local_child_devices(devices)
        except Exception:
            pass
        self._populate_branch_combo_from_devices(devices)
        if self._pending_global_branch_refresh:
            self._pending_global_branch_refresh = False
            self._start_all_branch_snapshots_refresh(devices)

    def _on_branch_list_failed(self, error_msg: str):
        logger.warning(f"[HOME] Error consultando sucursales en nube: {error_msg}")
        self._pending_global_branch_refresh = False
        self._restore_branch_combo_state()

    def _on_branch_list_loader_finished(self, finished_loader):
        if self._branch_list_loader_thread is finished_loader:
            self._branch_list_loader_thread = None
        self._set_branch_list_loading_ui(False)

    def _backup_branch_combo_state(self):
        if not hasattr(self, "branch_combo"):
            return
        try:
            items = []
            for i in range(self.branch_combo.count()):
                text = self.branch_combo.itemText(i)
                data = self.branch_combo.itemData(i) or ""
                items.append((text, str(data).strip().upper() if data else ""))
            current_data = self.branch_combo.currentData() or ""
            self._branch_combo_backup = {
                "items": items,
                "current_code": str(current_data).strip().upper() if current_data else ""
            }
        except Exception:
            self._branch_combo_backup = {"items": [], "current_code": ""}

    def _restore_branch_combo_state(self):
        backup = self._branch_combo_backup if isinstance(self._branch_combo_backup, dict) else {}
        items = backup.get("items") if isinstance(backup.get("items"), list) else []
        current_code = str(backup.get("current_code", "")).strip().upper()

        self._suppress_branch_change = True
        self.branch_combo.blockSignals(True)
        self.branch_combo.clear()
        if not items:
            self.branch_combo.addItem(self._default_global_branch_label(), "")
        else:
            for text, code in items:
                self.branch_combo.addItem(str(text), str(code))
        idx = self.branch_combo.findData(current_code) if current_code else 0
        if idx < 0:
            idx = 0
        self.branch_combo.setCurrentIndex(idx)
        self.branch_combo.blockSignals(False)
        self._suppress_branch_change = False
        self._on_branch_selected(self.branch_combo.currentIndex())

    def _on_branch_loader_finished(self, finished_loader):
        if self._branch_loader_thread is finished_loader:
            self._branch_loader_thread = None
        self._set_branch_loading_ui(
            self._branch_loader_thread is not None and self._branch_loader_thread.isRunning()
        )

    def _start_all_branch_snapshots_refresh(self, devices: list):
        if self._branch_bulk_loader_thread is not None and self._branch_bulk_loader_thread.isRunning():
            return

        loader = AllBranchesSnapshotLoader(username=str(self.username), devices=devices)
        self._branch_bulk_loader_thread = loader
        self._set_branch_loading_ui(True)
        loader.loaded.connect(self._on_all_branch_snapshots_loaded)
        loader.failed.connect(self._on_all_branch_snapshots_failed)
        loader.finished.connect(lambda current_loader=loader: self._on_all_branch_snapshots_finished(current_loader))
        loader.start()

    def _on_all_branch_snapshots_loaded(self, _summary: dict):
        try:
            from utils.file_handler import clear_branch_runtime_caches
            clear_branch_runtime_caches()
        except Exception:
            pass

        self._last_applied_branch_code = ""
        if self.parent_window is not None and hasattr(self.parent_window, "on_branch_context_changed"):
            self.parent_window.on_branch_context_changed("", self._default_global_branch_label())

    def _on_all_branch_snapshots_failed(self, error_msg: str):
        try:
            QMessageBox.warning(self, "Sucursales", f"No se pudieron refrescar todas las sucursales.\n{error_msg}")
        except Exception:
            logger.warning(f"[HOME] Error refrescando snapshots globales: {error_msg}")

    def _on_all_branch_snapshots_finished(self, finished_loader):
        if self._branch_bulk_loader_thread is finished_loader:
            self._branch_bulk_loader_thread = None
        self._set_branch_loading_ui(
            self._branch_loader_thread is not None and self._branch_loader_thread.isRunning()
        )

    def _start_branch_snapshot_download(
        self,
        branch_code: str,
        branch_label: str,
        source_username: str = None,
        show_error: bool = True,
        force_restart: bool = False,
    ):
        code = str(branch_code or "").strip().upper()
        label = str(branch_label or "").strip()
        if not code:
            return

        # Descargar snapshot en hilo aparte
        self._set_branch_loading_ui(True)
        if self._branch_loader_thread is not None and self._branch_loader_thread.isRunning():
            if not force_restart:
                return
            try:
                self._branch_loader_thread.quit()
                self._branch_loader_thread.wait(1000)
            except Exception:
                pass

        self._branch_request_seq += 1
        request_seq = self._branch_request_seq
        self._branch_request_show_error[request_seq] = bool(show_error)

        loader = BranchSnapshotLoader(
            username=str(source_username or self.username),
            branch_code=code,
            branch_label=label,
        )
        self._branch_loader_thread = loader
        loader.loaded.connect(lambda result, seq=request_seq: self._on_branch_snapshot_loaded(seq, result))
        loader.failed.connect(lambda error_msg, seq=request_seq: self._on_branch_snapshot_failed(seq, error_msg))
        loader.finished.connect(lambda current_loader=loader: self._on_branch_loader_finished(current_loader))
        loader.start()

    def _on_branch_selected(self, index: int):
        if index < 0:
            code = ""
            label = self._default_global_branch_label()
        else:
            code = self.branch_combo.itemData(index) or ""
            label = self.branch_combo.itemText(index)

        new_code = str(code).strip().upper()
        new_label = str(label).strip()
        self.selected_branch_code = new_code
        self.selected_branch_label = new_label

        if self.parent_window is not None:
            setattr(self.parent_window, "selected_branch_code", self.selected_branch_code)
            setattr(self.parent_window, "selected_branch_label", self.selected_branch_label)

        if self._suppress_branch_change:
            return

        # Evitar trabajo duplicado cuando no cambi? la selecci?n
        if new_code == self._last_applied_branch_code:
            return

        if new_code == "":
            self._apply_branch_context_cleared()
            return

        self._start_branch_snapshot_download(
            branch_code=new_code,
            branch_label=new_label,
            source_username=str(self.username),
            show_error=True,
            force_restart=True,
        )

    def _apply_branch_context_cleared(self):
        try:
            from utils.file_handler import clear_active_branch_context, clear_branch_runtime_caches
            clear_active_branch_context(self.username)
            clear_branch_runtime_caches()
        except Exception as e:
            logger.warning(f"[HOME] Error limpiando contexto de sucursal: {e}")

        self._last_applied_branch_code = ""
        if self.parent_window is not None and hasattr(self.parent_window, "on_branch_context_changed"):
            self.parent_window.on_branch_context_changed("", self._default_global_branch_label())

    def _on_branch_snapshot_loaded(self, request_seq: int, result: dict):
        self._branch_request_show_error.pop(request_seq, None)
        if request_seq != self._branch_request_seq:
            # Resultado antiguo; el usuario ya pidió otra sucursal.
            return
        try:
            from utils.file_handler import set_active_branch_context, clear_branch_runtime_caches

            branch_code = str((result or {}).get("branch_code", self.selected_branch_code)).strip().upper()
            branch_label = str((result or {}).get("branch_label", self.selected_branch_label)).strip()
            set_active_branch_context(self.username, branch_code, branch_label)
            clear_branch_runtime_caches()

            self._last_applied_branch_code = branch_code
            if self.parent_window is not None and hasattr(self.parent_window, "on_branch_context_changed"):
                self.parent_window.on_branch_context_changed(branch_code, branch_label)

            summary = (result or {}).get("summary") or {}
            if isinstance(summary, dict):
                logger.info(f"[HOME] Sucursal cargada {branch_code}: {summary}")
        except Exception as e:
            logger.error(f"[HOME] Error aplicando snapshot de sucursal: {e}")

    def _on_branch_snapshot_failed(self, request_seq: int, error_msg: str):
        show_error = self._branch_request_show_error.pop(request_seq, True)
        if request_seq != self._branch_request_seq:
            return
        if show_error:
            try:
                QMessageBox.warning(self, "Sucursal", f"No se pudo cargar la sucursal seleccionada.\n{error_msg}")
            except Exception:
                pass
        else:
            logger.warning(f"[HOME] No se pudo cargar snapshot remoto de sucursal trabajadora: {error_msg}")

        # Revertir selecci?n visual al ?ltimo c?digo aplicado
        prev = str(self._last_applied_branch_code or "").strip().upper()
        self._suppress_branch_change = True
        self.branch_combo.blockSignals(True)
        idx = self.branch_combo.findData(prev) if prev else 0
        if idx < 0:
            idx = 0
        self.branch_combo.setCurrentIndex(idx)
        self.branch_combo.blockSignals(False)
        self._suppress_branch_change = False

    def get_selected_branch_code(self) -> str:
        return str(self.selected_branch_code or "").strip().upper()

    def _panel_style_sheet(self) -> str:
        return f"""
            QFrame {{
                background-color: {THEME['card_bg']};
                border: 1px solid {THEME['border']};
                border-radius: 20px;
            }}
        """

    def _apply_panel_shadow(self, panel: QFrame):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(15, 23, 42, 16))
        shadow.setOffset(0, 10)
        panel.setGraphicsEffect(shadow)

    def _add_panel_header(self, layout, title: str, subtitle: str = "", badge_text: str = ""):
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(4)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        title_label.setStyleSheet(f"color: {THEME['accent']}; border: none;")
        text_box.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setFont(QFont("Segoe UI", 10))
            subtitle_label.setStyleSheet(f"color: {THEME['text_dim']}; border: none;")
            text_box.addWidget(subtitle_label)

        header_layout.addLayout(text_box, 1)

        if badge_text:
            badge = QLabel(badge_text)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"""
                color: {THEME['primary']};
                background: #EFF6FF;
                border: 1px solid #D7E5FF;
                border-radius: 12px;
                padding: 6px 10px;
                font-size: 10px;
                font-weight: 700;
                """
            )
            header_layout.addWidget(badge, 0, Qt.AlignTop)

        layout.addWidget(header)

    def _create_chart_panel(self):
        """Crea el panel del grÃ¡fico de ventas"""
        chart_panel = QFrame()
        chart_panel.setStyleSheet(self._panel_style_sheet())
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(24, 24, 24, 24)
        chart_layout.setSpacing(18)
        
        c_title = QLabel("Ventas Últimos 15 Días")
        c_title.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        c_title.setStyleSheet(f"color: {THEME['accent']}; border: none;")
        
        chart_layout.addWidget(c_title)
        chart_layout.addSpacing(20)
        
        self.chart_widget = SalesBarChart()
        chart_layout.addWidget(self.chart_widget)
        
        # Sombra
        self._apply_panel_shadow(chart_panel)
        
        return chart_panel
    
    def _create_goals_panel(self):
        """Crea el panel de metas"""
        side_panel = QFrame()
        side_panel.setStyleSheet(self._panel_style_sheet())
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(24, 24, 24, 24)
        side_layout.setSpacing(20)
        
        s_title = QLabel("Metas del Mes")
        s_title.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        s_title.setStyleSheet(f"color: {THEME['accent']}; border: none;")
        side_layout.addWidget(s_title)
        
        self.goals_container = QWidget()
        self.goals_layout = QVBoxLayout(self.goals_container)
        self.goals_layout.setContentsMargins(0, 0, 0, 0)
        self.goals_layout.setSpacing(12)
        
        side_layout.addWidget(self.goals_container)
        self.refresh_goals_display()
        side_layout.addStretch()
        
        # Buttons
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_goals = QPushButton("Decidir mis Metas")
        btn_goals.setFixedHeight(40)
        btn_goals.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        btn_goals.setCursor(Qt.PointingHandCursor)
        btn_goals.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['primary']};
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {THEME['accent']};
            }}
        """)
        btn_goals.clicked.connect(self.open_goals_config)
        buttons_layout.addWidget(btn_goals)

        btn_action = ClickableLabel("Ver Reporte Completo")
        btn_action.setAlignment(Qt.AlignCenter)
        btn_action.setCursor(Qt.PointingHandCursor)
        btn_action.setFixedHeight(40)
        btn_action.clicked.connect(self.go_to_advanced_reports)
        buttons_layout.addWidget(btn_action)
        
        side_layout.addWidget(buttons_container)
        
        self._apply_panel_shadow(side_panel)
        
        return side_panel
    
    def _create_comparison_panel(self):
        """Crea el panel del grÃ¡fico de comparaciÃ³n"""
        comparison_panel = QFrame()
        comparison_panel.setStyleSheet(self._panel_style_sheet())
        comparison_layout = QVBoxLayout(comparison_panel)
        comparison_layout.setContentsMargins(24, 24, 24, 24)
        comparison_layout.setSpacing(16)
        
        comp_title = QLabel("Comparación: Mes Anterior vs Mes Actual")
        comp_title.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        comp_title.setStyleSheet(f"color: {THEME['accent']}; border: none;")
        
        comparison_layout.addWidget(comp_title)
        comparison_layout.addSpacing(15)
        
        self.comparison_chart = ComparisonLineChart(username=self.username)
        self.comparison_chart.day_clicked.connect(self.on_chart_day_clicked)
        comparison_layout.addWidget(self.comparison_chart)
        
        self._apply_panel_shadow(comparison_panel)
        
        return comparison_panel
    
    def _create_rankings_layout(self):
        """Crea el layout de rankings"""
        rankings_layout = QHBoxLayout()
        rankings_layout.setSpacing(20)
        
        # Customers Panel
        customers_panel = QFrame()
        customers_panel.setMinimumWidth(0)
        customers_panel.setStyleSheet(self._panel_style_sheet())
        customers_layout = QVBoxLayout(customers_panel)
        customers_layout.setContentsMargins(20, 20, 20, 20)
        customers_layout.setSpacing(14)
        
        customers_title = QLabel("Mejores Clientes del Mes")
        customers_title.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        customers_title.setStyleSheet(f"color: {THEME['accent']};")
        customers_layout.addWidget(customers_title)
        
        self.top_customers = TopCustomersRanking(username=self.username, parent=self)
        customers_layout.addWidget(self.top_customers)
        
        self._apply_panel_shadow(customers_panel)
        rankings_layout.addWidget(customers_panel)
        
        # Products Panel
        products_panel = QFrame()
        products_panel.setMinimumWidth(0)
        products_panel.setStyleSheet(self._panel_style_sheet())
        products_layout = QVBoxLayout(products_panel)
        products_layout.setContentsMargins(20, 20, 20, 20)
        products_layout.setSpacing(14)
        
        products_title = QLabel("Mejores Productos del Mes")
        products_title.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        products_title.setStyleSheet(f"color: {THEME['accent']};")
        products_layout.addWidget(products_title)
        
        self.top_products = TopProductsRanking(username=self.username, parent=self)
        products_layout.addWidget(self.top_products)
        
        self._apply_panel_shadow(products_panel)
        rankings_layout.addWidget(products_panel)
        
        return rankings_layout

    def set_sales_data(self, sales_data=None, allow_remote_restore=True):
        if isinstance(sales_data, dict):
            sales_data = list(sales_data.values())
        if isinstance(sales_data, list):
            self._latest_sales_data = list(sales_data)
        else:
            self._latest_sales_data = []
        self._latest_sales_data_initialized = True
        self._latest_sales_allow_remote_restore = bool(allow_remote_restore)

        if hasattr(self, "comparison_chart") and hasattr(self.comparison_chart, "set_sales_data"):
            self.comparison_chart.set_sales_data(
                self._latest_sales_data,
                allow_remote_restore=self._latest_sales_allow_remote_restore,
            )
        if hasattr(self, "top_customers") and hasattr(self.top_customers, "set_sales_data"):
            self.top_customers.set_sales_data(
                self._latest_sales_data,
                allow_remote_restore=self._latest_sales_allow_remote_restore,
            )
        if hasattr(self, "top_products") and hasattr(self.top_products, "set_sales_data"):
            self.top_products.set_sales_data(
                self._latest_sales_data,
                allow_remote_restore=self._latest_sales_allow_remote_restore,
            )
    
    # === PUBLIC API ===
    def go_to_advanced_reports(self):
        """Navega a la pÃ¡gina de Reportes Generales"""
        if self.parent_window and hasattr(self.parent_window, 'mostrar_frame'):
            self.parent_window.mostrar_frame(14)
    
    def open_goals_config(self):
        """Abre el diÃ¡logo para configurar metas"""
        dialog = GoalsConfigDialog(self.username, self.parent_window)
        dialog.goals_saved.connect(self.refresh_goals_display)
        dialog.exec_()
    
    def on_chart_day_clicked(self, day):
        """Maneja click en un dÃ­a del grÃ¡fico de comparaciÃ³n"""
        purchases = self.comparison_chart.purchase_data.get(day, [])
        
        sales_data = list(self._latest_sales_data)
        if not self._latest_sales_data_initialized:
            sales_data = _load_sales_data(
                self.username,
                allow_remote_restore=self._latest_sales_allow_remote_restore,
            )
            self.set_sales_data(
                sales_data,
                allow_remote_restore=self._latest_sales_allow_remote_restore,
            )
        
        dialog = DayPurchasesDialog(day, purchases, sales_data=sales_data, username=self.username, parent=self)
        dialog.exec_()
    
    def refresh_goals_display(self, goals_list=None):
        """Recarga y actualiza las metas en tiempo real"""
        try:
            # Si el layout de metas no existe (UI incompleta), no hacer nada
            if getattr(self, 'goals_layout', None) is None:
                return

            icons_dir = os.path.join(os.path.dirname(__file__), '..', 'icons')
            goal_icons = {
                'ventas_totales': os.path.join(icons_dir, 'goal_sales.svg'),
                'margen_ganancia': os.path.join(icons_dir, 'goal_margin.svg'),
                'ventas_por_dia': os.path.join(icons_dir, 'goal_daily.svg'),
                'Ventas por Día': os.path.join(icons_dir, 'goal_daily.svg'),
            }
            
            while self.goals_layout.count():
                widget = self.goals_layout.takeAt(0).widget()
                if widget:
                    widget.deleteLater()
            
            self.goals_widgets = []
            
            self.goals_calculator = GoalsCalculator(self.username)
            user_goals = self.goals_calculator.get_all_goals_progress()

            if not user_goals:
                empty_label = QLabel("Aun no hay metas para mostrar")
                empty_label.setWordWrap(True)
                empty_label.setAlignment(Qt.AlignCenter)
                empty_label.setStyleSheet(
                    f"color: {THEME['text_dim']}; border: 1px dashed {THEME['border']}; "
                    "border-radius: 10px; padding: 18px;"
                )
                self.goals_layout.addWidget(empty_label)
                self.goals_widgets.append((empty_label, None, None))
                return
            
            for goal_id, goal_name, actual_value, target_value, progress_pct in user_goals:
                try:
                    item_wid = QWidget()
                    item_l = QVBoxLayout(item_wid)
                    item_l.setContentsMargins(0, 0, 0, 0)
                    item_l.setSpacing(8)
                    
                    row = QHBoxLayout()
                    row.setSpacing(8)
                    
                    icon_path = goal_icons.get(goal_id) or goal_icons.get(goal_name)
                    if icon_path and os.path.exists(icon_path):
                        icon_svg = QSvgWidget(icon_path)
                        icon_svg.setFixedSize(18, 18)
                        row.addWidget(icon_svg)
                    
                    lbl = QLabel(goal_name)
                    lbl.setStyleSheet(f"color: {THEME['text_main']}; border: none; font-weight: 500;")
                    
                    if goal_id in AVAILABLE_GOALS:
                        unit = AVAILABLE_GOALS[goal_id]['unit']
                        if AVAILABLE_GOALS[goal_id]['type'] in ['currency', 'count']:
                            val_text = f"{actual_value:.0f}/{target_value:.0f} {unit}"
                        else:
                            val_text = f"{actual_value:.1f}/{target_value:.1f} {unit}"
                    else:
                        val_text = f"{progress_pct}%"
                    
                    v = QLabel(val_text)
                    v.setStyleSheet(f"color: {THEME['primary']}; font-weight: bold; border: none; font-size: 10px;")
                    row.addWidget(lbl)
                    row.addStretch()
                    row.addWidget(v)
                    
                    prog = QProgressBar()
                    prog.setFixedHeight(6)
                    prog.setTextVisible(False)
                    prog.setValue(min(progress_pct, 100))
                    prog.setStyleSheet(f"""
                        QProgressBar {{
                            background-color: {THEME['card_border']};
                            border-radius: 3px;
                            border: none;
                        }}
                        QProgressBar::chunk {{
                            background-color: {THEME['primary']};
                            border-radius: 3px;
                        }}
                    """)
                    
                    item_l.addLayout(row)
                    item_l.addWidget(prog)
                    self.goals_layout.addWidget(item_wid)
                    self.goals_widgets.append((item_wid, v, prog))
                    
                except Exception as e:
                    logger.error(f"Error cargando meta: {e}")
        except Exception as e:
            logger.error(f"Error refrescando metas: {e}")
    
    def showEvent(self, event):
        """Se ejecuta cuando el widget se muestra"""
        super().showEvent(event)
        if not self._did_first_show_reload:
            self._did_first_show_reload = True
            should_refresh_remote = False
            try:
                if not self._is_madre_device():
                    should_refresh_remote = not bool(str(self.selected_branch_code or "").strip().upper())
                else:
                    should_refresh_remote = not bool(self._load_local_child_devices())
            except Exception:
                should_refresh_remote = False
            if should_refresh_remote:
                QTimer.singleShot(900, lambda: self._reload_branch_selector(fetch_remote=True))
        self.refresh_goals_display()
        try:
            self.setEnabled(True)
            self.setMouseTracking(True)
            self.setFocus()
        except Exception as e:
            logger.error(f"Error en showEvent: {e}")
    
    def setPatientCount(self, count: int):
        self.stat_cards['patients'].setValue(str(count))
    
    def setProductCount(self, count: int):
        self.stat_cards['stock'].setValue(str(count))
    
    def setMonthlyPatients(self, count: int):
        self.stat_cards['monthly'].setValue(str(count))
    
    def setTotalSales(self, amount: float):
        self.stat_cards['sales'].setValue(f"S/. {amount:,.2f}")
    
    def updateSalesChart(self, sales, labels):
        """Actualiza el grÃ¡fico de ventas"""
        chart = getattr(self, 'chart_widget', None)
        if chart and sales:
            chart.setSalesData(sales)
    
    def resizeEvent(self, event):
        """Ajusta el layout cuando se redimensiona"""
        super().resizeEvent(event)
        try:
            self._apply_responsive_layout()
            if hasattr(self, 'cards_grid') and self.width() > 0:
                card_width = 250
                spacing = 20
                available_width = int(self.width() or 0) - 40
                
                max_cols = max(1, (available_width + spacing) // (card_width + spacing))
                cols_needed = min(4, max_cols)
                
                if not hasattr(self, '_last_cols') or self._last_cols != cols_needed:
                    self._reorganize_grid(cols_needed)
                    self._last_cols = cols_needed
        except Exception as e:
            logger.error(f"Error en resizeEvent: {e}")
    
    def _reorganize_grid(self, cols):
        """Reorganiza las tarjetas segÃºn columnas"""
        try:
            while self.cards_grid.count():
                self.cards_grid.takeAt(0)
            
            cards_list = [
                self.stat_cards['patients'],
                self.stat_cards['stock'],
                self.stat_cards['monthly'],
                self.stat_cards['sales']
            ]
            
            row = 0
            col = 0
            for card in cards_list:
                self.cards_grid.addWidget(card, row, col)
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            
            for i in range(cols):
                self.cards_grid.setColumnStretch(i, 1)
        except Exception as e:
            logger.error(f"Error reorganizando grid: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.resize(1280, 800)
    window.setWindowTitle("Sistema VISO - Dashboard Pro")
    
    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    
    dash = HomePageWidgetImproved()
    layout.addWidget(dash)
    
    dash.setPatientCount(1245)
    dash.setProductCount(843)
    dash.setMonthlyPatients(128)
    dash.setTotalSales(24500.50)
    
    window.show()
    sys.exit(app.exec_())

