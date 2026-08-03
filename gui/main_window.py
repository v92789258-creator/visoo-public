import sys
import os
import datetime
import time
import shutil
import json
import re
import socket
import webbrowser
import ctypes
import subprocess
from ctypes import wintypes
from PyQt5 import QtWidgets, QtCore, QtGui, sip
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDialog, QLineEdit, QMessageBox, QDockWidget, QTabWidget,
    QApplication, QTextBrowser, QSizePolicy, QFrame, QStackedWidget, QShortcut, QScrollArea
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer, pyqtSignal, QThread
from gui.animated_stack import AnimatedStackedWidget
from gui.lazy_page_loader import load_page_on_demand
from gui.async_page_loader import LoadingPage, ASYNC_PAGE_INDICES
from gui.notifications_popup import NotificationsPopup
from gui.loading_overlay import LoadingOverlay
from PyQt5.QtGui import QIcon, QKeySequence
from utils.data_cache_manager import get_global_cache
from utils.runtime_status import begin_operation, end_operation, get_active_operations
from utils.text_normalizer import maybe_normalize_ui_text
import logging

logger = logging.getLogger(__name__)


def _is_qt_object_alive(obj):
    try:
        return obj is not None and not sip.isdeleted(obj)
    except TypeError:
        return obj is not None
    except Exception:
        return False

try:
    from core.config.settings import APP_VERSION
except Exception:
    APP_VERSION = "0.0.0"

# --- Clase custom para botÃ³n de cerrar con cambio de icono en hover ---
class CloseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_dark = None
        self.icon_light = None
        self.is_hovering = False
    
    def set_icons(self, dark_icon, light_icon):
        self.icon_dark = dark_icon
        self.icon_light = light_icon
        self.setIcon(dark_icon)
    
    def enterEvent(self, event):
        self.is_hovering = True
        if self.icon_light:
            self.setIcon(self.icon_light)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.is_hovering = False
        if self.icon_dark:
            self.setIcon(self.icon_dark)
        super().leaveEvent(event)


class SystemStatusSnapshotWorker(QThread):
    snapshot_ready = pyqtSignal(dict)

    def __init__(self, user_id=None, username=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username

    def run(self):
        snapshot = {
            "internet_ok": None,
            "queue_total": 0,
            "queue_by_dataset": {},
            "error": "",
        }
        try:
            from utils.sync_manager import get_sync_manager

            sync_mgr = get_sync_manager()
            ids_to_check = []
            for raw in (self.user_id, self.username):
                value = str(raw or "").strip()
                if value and value not in ids_to_check:
                    ids_to_check.append(value)

            seen_queue_ids = set()
            all_items = []
            for uid in ids_to_check:
                try:
                    pending_items = sync_mgr.queue.get_pending_items(uid, limit=5000)
                except Exception:
                    pending_items = []
                for item in pending_items or []:
                    queue_id = item.get("id")
                    if queue_id in seen_queue_ids:
                        continue
                    seen_queue_ids.add(queue_id)
                    all_items.append(item)

            queue_by_dataset = {}
            for item in all_items:
                dataset = str(item.get("tipo_dato", "otros") or "otros").strip().lower() or "otros"
                queue_by_dataset[dataset] = int(queue_by_dataset.get(dataset, 0) or 0) + 1

            snapshot["queue_total"] = len(all_items)
            snapshot["queue_by_dataset"] = queue_by_dataset

            try:
                snapshot["internet_ok"] = bool(sync_mgr.check_internet())
            except Exception as exc:
                snapshot["internet_ok"] = None
                snapshot["error"] = str(exc)
        except Exception as exc:
            snapshot["error"] = str(exc)

        self.snapshot_ready.emit(snapshot)


class PendingSyncForceWorker(QThread):
    sync_finished = pyqtSignal(dict)

    def __init__(self, user_id=None, username=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username

    def run(self):
        result = {
            "sincronizados": 0,
            "errores": 0,
            "pendientes": 0,
            "message": "",
        }
        op_key = begin_operation("manual-force-sync", "Subiendo cambios pendientes", "upload")
        try:
            from utils.sync_manager import get_sync_manager

            sync_mgr = get_sync_manager()
            ids_to_check = []
            for raw in (self.user_id, self.username):
                value = str(raw or "").strip()
                if value and value not in ids_to_check:
                    ids_to_check.append(value)

            if not ids_to_check:
                result["message"] = "No se encontró el usuario para sincronizar."
                self.sync_finished.emit(result)
                return

            for uid in ids_to_check:
                try:
                    stats = sync_mgr.sync_now(uid, force=True) or {}
                except Exception as exc:
                    result["errores"] += 1
                    result["message"] = str(exc)
                    continue
                result["sincronizados"] += int(stats.get("sincronizados", 0) or 0)
                result["errores"] += int(stats.get("errores", 0) or 0)
                result["pendientes"] += int(stats.get("pendientes", 0) or 0)

            if not result["message"]:
                result["message"] = (
                    f"Sincronizados: {result['sincronizados']} | "
                    f"Errores: {result['errores']} | "
                    f"Pendientes: {result['pendientes']}"
                )
        finally:
            end_operation(op_key)

        self.sync_finished.emit(result)


class InitialSyncCheckWorker(QThread):
    check_ready = pyqtSignal(dict)

    def __init__(self, username=None, user_id=None, viso_dir=None, parent=None):
        super().__init__(parent)
        self.username = str(username or "").strip()
        self.user_id = str(user_id or "").strip()
        self.viso_dir = str(viso_dir or "").strip()

    @staticmethod
    def _quick_cloud_probe(timeout: float = 0.45) -> bool:
        """
        Sonda corta para decidir si vale la pena intentar checks remotos
        durante el arranque. Si la red esta lenta, se considera no lista
        para startup y se reintenta ya dentro del sistema.
        """
        try:
            with socket.create_connection(("api.yhana.cloud", 443), timeout=timeout):
                return True
        except Exception:
            return False

    def run(self):
        result = {
            "should_upload": False,
            "offline": False,
            "deferred": False,
            "checked": False,
            "reason": "",
        }

        try:
            if not self.username or not self.viso_dir:
                result["reason"] = "Faltan datos de usuario para verificar sincronizacion inicial."
                self.check_ready.emit(result)
                return

            if not self._quick_cloud_probe():
                result["offline"] = True
                result["deferred"] = True
                result["reason"] = (
                    "Sin internet o conexion lenta. "
                    "Se omite el chequeo inicial y se entra directo en modo offline."
                )
                self.check_ready.emit(result)
                return

            from utils.initial_sync_manager import InitialSyncManager

            manager = InitialSyncManager(self.username, self.viso_dir)
            result["should_upload"] = bool(manager.should_upload())
            result["checked"] = True
            result["reason"] = (
                "Datos pendientes de subida inicial."
                if result["should_upload"] else
                "Sincronizacion inicial ya resuelta o no necesaria."
            )
        except Exception as e:
            result["reason"] = str(e)

        self.check_ready.emit(result)


class PendingSyncDialog(QDialog):
    force_sync_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(470, 310)
        self.setMinimumSize(430, 250)
        self.setStyleSheet("""
            QDialog {
                background: transparent;
            }
            QFrame#pendingSyncCard {
                background: #FAFCFF;
                border: 1px solid #DCE5F2;
                border-radius: 14px;
            }
            QLabel#pendingSyncSummary {
                color: #0F172A;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#pendingSyncCaption {
                color: #64748B;
                font-size: 11px;
            }
            QLabel#pendingSyncStatus {
                color: #64748B;
                font-size: 11px;
            }
            QLabel#pendingSyncEmpty {
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
                selection-background-color: #E8F0FF;
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
            QPushButton#pendingSyncCloseTop {
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
            QPushButton#pendingSyncCloseTop:hover {
                background: #EEF2F8;
                color: #0F172A;
            }
            QPushButton#pendingSyncPrimary {
                background: #2157D5;
                color: white;
                border: none;
                font-weight: 700;
            }
            QPushButton#pendingSyncPrimary:disabled {
                background: #BFD0F8;
                color: #F8FAFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("pendingSyncCard")
        layout.addWidget(self.card)

        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QtGui.QColor(15, 23, 42, 42))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        header_text_layout = QVBoxLayout()
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        header_text_layout.setSpacing(2)

        self.summary_label = QLabel("No hay cambios pendientes.")
        self.summary_label.setObjectName("pendingSyncSummary")
        header_text_layout.addWidget(self.summary_label)

        self.caption_label = QLabel("Cambios guardados localmente pendientes de nube")
        self.caption_label.setObjectName("pendingSyncCaption")
        header_text_layout.addWidget(self.caption_label)

        header_layout.addLayout(header_text_layout, 1)

        close_top_button = QPushButton("×")
        close_top_button.setObjectName("pendingSyncCloseTop")
        close_top_button.setCursor(Qt.PointingHandCursor)
        close_top_button.clicked.connect(self.accept)
        header_layout.addWidget(close_top_button, 0, Qt.AlignTop)

        card_layout.addLayout(header_layout)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Tipo", "Operacion", "Detalle", "Hora"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        card_layout.addWidget(self.table, 1)

        self.empty_label = QLabel("No hay cambios pendientes por subir.")
        self.empty_label.setObjectName("pendingSyncEmpty")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        card_layout.addWidget(self.empty_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("pendingSyncStatus")
        card_layout.addWidget(self.status_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.sync_button = QPushButton("Subir ahora")
        self.sync_button.setObjectName("pendingSyncPrimary")
        self.sync_button.setMinimumWidth(120)
        self.sync_button.clicked.connect(self.force_sync_requested.emit)
        buttons_layout.addWidget(self.sync_button)

        close_button = QPushButton("Cerrar")
        close_button.setMinimumWidth(110)
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)

        card_layout.addLayout(buttons_layout)

    def set_items(self, items, summary_text="", status_text=""):
        rows = list(items or [])
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(item.get("dataset_label", ""))))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(item.get("operation_label", ""))))
            detail_item = QtWidgets.QTableWidgetItem(str(item.get("detail", "")))
            detail_item.setToolTip(str(item.get("detail", "")))
            self.table.setItem(row, 2, detail_item)
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(item.get("timestamp_label", ""))))

        self.summary_label.setText(summary_text or "No hay cambios pendientes.")
        self.status_label.setText(status_text or "")
        self.sync_button.setEnabled(bool(rows))
        self.table.setVisible(bool(rows))
        self.empty_label.setVisible(not bool(rows))
        self.caption_label.setText(
            "Pulsa 'Subir ahora' para enviarlos a la nube."
            if rows else
            "Todo esta sincronizado por ahora."
        )
        if rows:
            self.table.selectRow(0)
        visible_rows = min(max(len(rows), 1), 6)
        target_height = 180 + (visible_rows * 34)
        self.resize(self.width(), min(360, target_height))

# --- Obtener ruta del Ã­cono ---
def get_icon_path():
    """Obtiene la ruta del archivo icon.ico considerando si estÃ¡ empaquetado o en desarrollo."""
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icon_path = os.path.join(base_dir, "icon.ico")
    return icon_path

class OpticaApp(QMainWindow):
    # Signals para comunicaciÃ³n thread-safe desde threads de verificaciÃ³n
    license_expired = pyqtSignal(dict)
    no_license = pyqtSignal()
    ui_ready = pyqtSignal()  # Emitida cuando la UI estÃ¡ completamente lista
    update_notification_ready = pyqtSignal(dict)
    update_popup_ready = pyqtSignal(dict)
    manual_backup_finished = pyqtSignal(bool, str, str)
    branch_quota_selection_needed = pyqtSignal(dict)
    branch_recovery_selection_needed = pyqtSignal(dict)
    UPDATE_INFO_URL = "https://api.yhana.cloud/v.json"
    DEVICE_EVENTS_POLL_MS = 12000
    UPDATE_CHECK_STARTUP_DELAY_MS = 6500
    DEVICE_EVENTS_STARTUP_DELAY_MS = 12000
    SYSTEM_STATUS_INITIAL_SNAPSHOT_DELAY_MS = 3500
    SYSTEM_STATUS_SNAPSHOT_POLL_MS = 30000
    DEVICE_EVENTS_FALLBACK_MIN_INTERVAL_SEC = 180.0
    
    def __init__(self, user_id=None, username=None, is_helper=False, helper_name=None, allowed_modules=None):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.is_helper = is_helper  # Si el usuario actual es ayudante
        self.helper_name = helper_name  # Nombre del ayudante (si aplica)
        self.allowed_modules = allowed_modules or []  # MÃ³dulos permitidos para el ayudante
        self.device_role = "madre"
        self.device_role_label = self._get_madre_label()
        self.worker_restricted_pages = {11, 13, 14, 15, 16}
        self.selected_branch_code = ""
        self.selected_branch_label = "Todas las sucursales"
        self._detached_page_widgets = []
        self._basic_embedded_pages = {}
        self._basic_embedded_page_ids = {}
        self._load_device_role()
        # Si aplica, configurar codigo de sync para madre cuando hay 1 sola sucursal activa.
        self._ensure_madre_sync_device_code()

        # Agregar el mÃ©todo load_page_on_demand
        self.load_page_on_demand = load_page_on_demand.__get__(self)

        # Async page loading (evita congelar UI al navegar)
        self._async_page_workers = {}
        self._async_page_placeholders = {}
        self._system_status_snapshot = {
            "internet_ok": None,
            "queue_total": 0,
            "queue_by_dataset": {},
            "error": "",
        }
        self._system_status_worker = None
        self._system_status_poll_timer = None
        self._system_status_snapshot_timer = None
        self._system_status_visual_timer = None
        self._system_status_progress_value = 0
        self._system_status_progress_color = "#2563EB"
        self._system_status_active_signature = ""
        self._system_status_completion_until = 0.0
        self._system_status_snapshot_refresh_pending = False
        
        # Inicializar gestor de cachÃ© global
        self.cache = get_global_cache()
        
        # Inicializar zoom (factor de escala)
        self.zoom_factor = 1.0
        self.zoom_last_action = None  # Para prevenir acciones simultÃ¡neas
        self._device_events_timer = None
        self._device_events_last_epoch = 0
        self._device_events_fetching = False
        self._device_events_endpoint_available = False
        self._device_events_bootstrap_done = False
        self._device_events_last_fallback_ts = 0.0
        self._branch_product_state_loaded = False
        self._branch_product_state = {}
        self._branch_product_state_path = os.path.join(
            os.path.expanduser("~"),
            ".viso",
            "branch_product_state.json"
        )
        self._branch_quota_last_check_ts = 0.0
        self._branch_quota_prompt_open = False
        self._branch_quota_last_signature = ""
        self._branch_quota_last_prompt_ts = 0.0
        self._branch_recovery_last_check_ts = 0.0
        self._branch_recovery_prompt_open = False
        self._branch_recovery_last_signature = ""
        self._branch_recovery_last_prompt_ts = 0.0
        self._last_branch_context_refresh_key = None
        self._last_branch_context_refresh_ts = 0.0
        self._branch_context_change_in_progress = False
        self._pending_branch_context_change = None
        self._branch_context_defer_active = False
        self.initial_sync_mgr = None
        self._initial_sync_check_worker = None
        self._initial_sync_check_started = False
        self._initial_sync_check_retry_count = 0
        
        # Loading overlay (deshabilitado). Instanciarlo puede crear ventanas nativas extra.
        self.loading_overlay = None
        self._initial_load = True  # Flag legacy; overlay no se muestra
        
        # Conectar signals a slots
        self.license_expired.connect(self._force_close_expired)
        self.no_license.connect(self._force_close_no_license)
        self.update_notification_ready.connect(self._push_update_notification)
        self.update_popup_ready.connect(self._show_update_popup)
        self.manual_backup_finished.connect(self._on_manual_backup_finished)
        self.branch_quota_selection_needed.connect(self._show_branch_quota_qml_modal)
        self.branch_recovery_selection_needed.connect(self._show_branch_recovery_qml_modal)
        
        # --- INICIALIZAR SINCRONIZACIÓN INICIAL (Upload Total) ---
        
        # Configurar la ventana principal
        self.setup_main_window()
        self.setup_pages()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        QtCore.QTimer.singleShot(900, self._start_initial_sync_check_async)

    def _start_initial_sync_check(self):
        """Inicia el chequeo de sincronizaciÃ³n y muestra el modal si es necesario"""
        try:
            from utils.initial_sync_manager import InitialSyncManager
            from core.config.settings import BASE_DIR
            from gui.dialogs.upload_initial_dialog import UploadInitialDialog
            
            # El directorio VISO estÃ¡ en BASE_DIR/VISO segÃºn main.py
            viso_dir = os.path.join(BASE_DIR, "VISO")
            
            self.initial_sync_mgr = InitialSyncManager(self.username, viso_dir)
            
            # Verificar si es necesario subir (ahora consulta la nube si no hay archivo local)
            if self.initial_sync_mgr.should_upload():
                self.initial_sync_mgr = InitialSyncManager(self.username, viso_dir)
                if not self.initial_sync_mgr.should_upload():
                    logger.info("[INITIAL SYNC] La sincronizacion inicial se resolvio antes de abrir el modal.")
                    return
                logger.info(f"🚨 [INITIAL SYNC] Datos pendientes para {self.username}. Mostrando modal obligatorio.")
                
                # Obtener el ID de usuario para el diálogo (usamos self.user_id si existe)
                usuario_id = getattr(self, "user_id", self.username)
                
                # Mostrar el diálogo modal de forma síncrona (bloqueante)
                # Esto cumple con "debe abrir el modal"
                dialog = UploadInitialDialog(usuario_id, self)
                dialog.exec_()
            else:
                logger.info(f"✅ [INITIAL SYNC] Los datos de {self.username} ya estÃ¡n sincronizados (confirmado por nube/archivo)")
                
        except Exception as e:
            logger.error(f"❌ Error al iniciar chequeo de sincronizaciÃ³n: {e}")
        
    def _start_initial_sync_check_async(self):
        """Version no bloqueante del chequeo inicial para arranque rapido."""
        try:
            from core.config.settings import BASE_DIR

            if self._initial_sync_check_started:
                return
            self._initial_sync_check_started = True

            existing_worker = getattr(self, "_initial_sync_check_worker", None)
            if existing_worker is not None:
                try:
                    if existing_worker.isRunning():
                        return
                except Exception:
                    pass

            viso_dir = os.path.join(BASE_DIR, "VISO")
            worker = InitialSyncCheckWorker(
                username=self.username,
                user_id=getattr(self, "user_id", self.username),
                viso_dir=viso_dir,
                parent=self,
            )
            self._initial_sync_check_worker = worker

            def _cleanup_worker():
                if self._initial_sync_check_worker is worker:
                    self._initial_sync_check_worker = None

            worker.finished.connect(_cleanup_worker)
            worker.check_ready.connect(self._on_initial_sync_check_ready)
            worker.start()
        except Exception as e:
            logger.error(f"âŒ Error al iniciar chequeo async de sincronizaciÃƒÂ³n: {e}")

    def _on_initial_sync_check_ready(self, result):
        """Procesa el resultado del chequeo inicial con la UI ya visible."""
        try:
            payload = dict(result or {})
            reason = str(payload.get("reason") or "").strip()

            if payload.get("offline"):
                self._initial_sync_check_started = False
                logger.info(
                    "â„¹ï¸ [INITIAL SYNC] %s",
                    reason or "Sin internet. Se omite el chequeo inicial y se entra en modo offline.",
                )
                if bool(payload.get("deferred")) and self._initial_sync_check_retry_count < 3:
                    self._initial_sync_check_retry_count += 1
                    QtCore.QTimer.singleShot(15000, self._start_initial_sync_check_async)
                return

            self._initial_sync_check_retry_count = 0

            if payload.get("should_upload"):
                try:
                    from core.config.settings import BASE_DIR
                    from utils.initial_sync_manager import InitialSyncManager

                    viso_dir = os.path.join(BASE_DIR, "VISO")
                    self.initial_sync_mgr = InitialSyncManager(self.username, viso_dir)
                    if not self.initial_sync_mgr.should_upload():
                        logger.info(
                            "[INITIAL SYNC] El modal se omitio porque la sincronizacion ya quedo resuelta."
                        )
                        return
                except Exception as recheck_error:
                    logger.warning(
                        "[INITIAL SYNC] No se pudo revalidar antes del modal: %s",
                        recheck_error,
                    )
                logger.info(
                    "ðŸš¨ [INITIAL SYNC] Datos pendientes para %s. Mostrando modal obligatorio.",
                    self.username,
                )
                from gui.dialogs.upload_initial_dialog import UploadInitialDialog

                usuario_id = getattr(self, "user_id", self.username)
                dialog = UploadInitialDialog(usuario_id, self)
                dialog.exec_()
                return

            logger.info(
                "âœ… [INITIAL SYNC] %s",
                reason or "Los datos de la cuenta ya estaban sincronizados.",
            )
        except Exception as e:
            logger.error(f"âŒ Error procesando chequeo inicial de sincronizaciÃƒÂ³n: {e}")

    def nativeEvent(self, eventType, message):
        """Intercepta WM_NCHITTEST para permitir arrastre en la barra de menÃº y redimensionamiento en bordes."""
        try:
            # En Windows, el mensaje es WM_NCHITTEST (0x84)
            if eventType == 0:  # QEvent.Type para mensajes nativos en Windows
                # Acceder al mensaje de Windows de forma segura
                msg = ctypes.cast(message, ctypes.POINTER(ctypes.wintypes.MSG)).contents
                
                # WM_NCHITTEST = 0x84
                if msg.message == 0x84:
                    # Obtener posiciÃ³n del cursor en coordenadas de la ventana
                    pos = self.mapFromGlobal(QtGui.QCursor.pos())
                    
                    rect = self.rect()
                    margin = 8
                    
                    # Constantes de hit testing de Windows
                    HTCLIENT = 1
                    HTCAPTION = 2
                    HTLEFT = 10
                    HTRIGHT = 11
                    HTTOP = 12
                    HTTOPLEFT = 13
                    HTTOPRIGHT = 14
                    HTBOTTOM = 15
                    HTBOTTOMLEFT = 16
                    HTBOTTOMRIGHT = 17
                    
                    # Zona de menÃº donde permitimos drag (HTCAPTION = arrastrar)
                    menu_height = 70
                    
                    # Detectar posiciÃ³n del cursor
                    hit = HTCLIENT
                    
                    # PRIORIDAD: Si estamos en el menÃº (top), permitir arrastre
                    if pos.y() < menu_height and pos.x() > margin and pos.x() < rect.width() - margin:
                        hit = HTCAPTION  # Permitir arrastrar
                    # Esquinas para redimensionamiento
                    elif pos.y() < margin and pos.x() < margin:
                        hit = HTTOPLEFT
                    elif pos.y() < margin and pos.x() > rect.width() - margin:
                        hit = HTTOPRIGHT
                    elif pos.y() > rect.height() - margin and pos.x() < margin:
                        hit = HTBOTTOMLEFT
                    elif pos.y() > rect.height() - margin and pos.x() > rect.width() - margin:
                        hit = HTBOTTOMRIGHT
                    # Bordes
                    elif pos.y() < margin:
                        hit = HTTOP
                    elif pos.y() > rect.height() - margin:
                        hit = HTBOTTOM
                    elif pos.x() < margin:
                        hit = HTLEFT
                    elif pos.x() > rect.width() - margin:
                        hit = HTRIGHT
                    
                    # Retornar el resultado del hit test
                    if hit != HTCLIENT:
                        return True, hit
                        
        except Exception as e:
            pass
        
        try:
            return super().nativeEvent(eventType, message)
        except Exception:
            return False, 0

    def eventFilter(self, obj, event):
        """
        Normaliza textos también en diálogos/ventanas que se crean dinámicamente.
        """
        try:
            evt_type = event.type() if event is not None else None
            if evt_type in (QtCore.QEvent.Show, QtCore.QEvent.Polish):
                if isinstance(obj, QtWidgets.QWidget):
                    QtCore.QTimer.singleShot(0, lambda w=obj: self._normalize_ui_texts(w))
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def puede_ver_seccion(self, seccion: str) -> bool:
        """
        Verifica si el ayudante puede VER una secciÃ³n.
        
        Args:
            seccion: Nombre de la secciÃ³n ('inventario', 'ventas', etc.)
        
        Returns:
            True si puede ver, False si no
        """
        if not self.is_helper or not self.helper_name:
            return True  # Usuarios normales tienen acceso a todo
        
        try:
            from utils.helpers_manager import tiene_accion_permitida
            return tiene_accion_permitida(self.username, self.helper_name, seccion, 'ver')
        except Exception as e:
            print(f"[ERROR] Verificando permisos de {seccion}: {e}")
            return False
    
    def puede_hacer_accion(self, seccion: str, accion: str) -> bool:
        """
        Verifica si el ayudante puede hacer una acciÃ³n especÃ­fica en una secciÃ³n.
        
        Args:
            seccion: Nombre de la secciÃ³n ('inventario', 'ventas', etc.)
            accion: Nombre de la acciÃ³n ('ver', 'crear', 'editar', 'eliminar')
        
        Returns:
            True si puede hacer la acciÃ³n, False si no
        """
        if not self.is_helper or not self.helper_name:
            return True  # Usuarios normales tienen acceso a todo
        
        try:
            from utils.helpers_manager import tiene_accion_permitida
            # Primero verificar que pueda VER, luego la acciÃ³n especÃ­fica
            if not tiene_accion_permitida(self.username, self.helper_name, seccion, 'ver'):
                return False
            return tiene_accion_permitida(self.username, self.helper_name, seccion, accion)
        except Exception as e:
            print(f"[ERROR] Verificando acciÃ³n {accion} en {seccion}: {e}")
            return False

    def _get_device_config_path(self):
        """Retorna la ruta del JSON de configuraciÃ³n de dispositivo."""
        if not self.username:
            return None
        try:
            from utils.file_handler import VISO_DIR
            return os.path.join(VISO_DIR, self.username, "data", "config_dispositivo.json")
        except Exception:
            return None

    def _has_multiple_branches(self) -> bool:
        """Determina si la cuenta usa mas de una sucursal."""
        if not self.username:
            return False

        try:
            from utils.file_handler import get_user_file_path
            branch_file = get_user_file_path(self.username, "dispositivos_hijos.json")
            if branch_file.exists():
                with open(branch_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    branch_count = sum(1 for item in data if isinstance(item, dict))
                    if branch_count > 0:
                        return True
        except Exception:
            pass

        try:
            from utils.file_handler import cargar_usuarios
            usuarios = cargar_usuarios() or {}
            username = str(self.username).strip()
            entry = None

            for _, info in usuarios.items():
                if isinstance(info, dict) and str(info.get("username", "")).strip() == username:
                    entry = info
                    break

            if entry is None and isinstance(usuarios.get(username), dict):
                entry = usuarios.get(username)

            max_sucursales = int((entry or {}).get("max_sucursales", 0))
            return max_sucursales > 1
        except Exception:
            return False

    def _get_madre_label(self) -> str:
        return "Dispositivo madre" if self._has_multiple_branches() else "Dispositivo unico"

    def _load_device_role(self):
        """Carga el rol de dispositivo desde disco (madre/trabajador)."""
        self.device_role = "madre"
        self.device_role_label = self._get_madre_label()
        try:
            config_path = self._get_device_config_path()
            if not config_path or not os.path.exists(config_path):
                return

            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            role = str(data.get("tipo_dispositivo", "madre")).strip().lower()
            raw_worker_code = (
                data.get("codigo_dispositivo_hijo")
                or data.get("codigo_dispositivo_trabajador")
                or data.get("codigo_dispositivo")
                or ""
            )
            worker_code = str(raw_worker_code or "").strip().upper()
            worker_id = str(data.get("dispositivo_hijo_id", "")).strip()
            linked_from_login = bool(data.get("vinculado_desde_login"))
            worker_name = str(data.get("dispositivo_hijo_nombre", "")).strip()

            looks_like_worker = role in [
                "trabajador",
                "hijo",
                "dispositivo hijo",
                "dispositivo trabajador",
            ] or bool(worker_code and (worker_id or linked_from_login or worker_name))

            if looks_like_worker:
                self.device_role = "trabajador"
                self.device_role_label = "Dispositivo trabajador"
        except Exception as e:
            logger.warning("No se pudo cargar config de dispositivo: %s", e)

    def _ensure_madre_sync_device_code(self):
        """
        Si este equipo es madre y la cuenta solo tiene 1 sucursal activa,
        guardar su codigo en config_dispositivo.json para que el sync use un
        codigo real (VISO-...) en vez de MADRE-...
        """
        if not self.username:
            return
        if not self.es_dispositivo_madre():
            return

        try:
            config_path = self._get_device_config_path()
            if not config_path:
                return
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            data = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    if isinstance(loaded, dict):
                        data = loaded
                except Exception:
                    data = {}

            # Si ya tiene codigo, no tocar.
            existing_code = str(data.get("codigo_dispositivo", "") or "").strip().upper()
            if existing_code:
                return

            from utils.file_handler import get_user_file_path
            fp = get_user_file_path(self.username, "dispositivos_hijos.json")
            if not fp.exists():
                return
            with open(fp, "r", encoding="utf-8") as f:
                devs = json.load(f)
            if not isinstance(devs, list):
                return

            activos = [
                d for d in devs
                if isinstance(d, dict)
                and str(d.get("estado", "activo")).strip().lower() != "bloqueado"
                and str(d.get("codigo_dispositivo", "")).strip()
            ]
            if len(activos) != 1:
                return

            code = str(activos[0].get("codigo_dispositivo", "")).strip().upper()
            if not code:
                return

            data.update({
                "tipo_dispositivo": "madre",
                "tipo_dispositivo_label": self._get_madre_label(),
                "usuario_madre": str(self.username),
                "codigo_dispositivo": code,
                "nube_sync_modo": str(data.get("nube_sync_modo", "carpeta") or "carpeta"),
                "updated_at": QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate),
            })
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            return

    def es_dispositivo_madre(self):
        return self.device_role == "madre"

    def _has_device_access_to_page(self, page_index: int) -> bool:
        if self.es_dispositivo_madre():
            return True
        return page_index not in self.worker_restricted_pages

    def _get_window_title(self):
        titulo = "VISO - Sistema de gestión para ópticas"
        if self.is_helper and self.helper_name:
            titulo += f" [Ayudante: {self.helper_name}]"
        if self.es_dispositivo_madre():
            self.device_role_label = self._get_madre_label()
        titulo += f" [{self.device_role_label}]"
        return titulo

    def on_device_role_changed(self, tipo_dispositivo=None):
        """
        Actualiza el rol de dispositivo en memoria y el tÃ­tulo.
        Los menÃºs completos se aplican al reiniciar.
        """
        if tipo_dispositivo is None:
            self._load_device_role()
        else:
            role = str(tipo_dispositivo).strip().lower()
            self.device_role = "trabajador" if role == "trabajador" else "madre"
            self.device_role_label = (
                "Dispositivo trabajador" if self.device_role == "trabajador" else self._get_madre_label()
            )
        self.setWindowTitle(self._get_window_title())
        self._refresh_top_branch_status_badge()
        if hasattr(self, "_backup_button") and self._backup_button is not None:
            self._backup_button.setVisible(self.es_dispositivo_madre())
        if self.es_dispositivo_madre():
            self._start_device_event_polling()
        else:
            self._stop_device_event_polling()

    def _shorten_status_text(self, text: str, max_len: int = 64) -> str:
        value = str(text or "").strip()
        if len(value) <= max_len:
            return value
        return value[: max_len - 3].rstrip() + "..."

    def _build_top_branch_status_text(self) -> str:
        if self.es_dispositivo_madre():
            branch_label = str(self.selected_branch_label or "Todas las sucursales").strip() or "Todas las sucursales"
            if branch_label.lower().startswith("todas"):
                return f"{self._get_madre_label()}: vista global de todas las sucursales"
            return f"{self._get_madre_label()}: datos cargados de {self._shorten_status_text(branch_label)}"
        return "Dispositivo trabajador: modo local activo"

    def _refresh_top_branch_status_badge(self):
        badge = getattr(self, "top_branch_status_badge", None)
        if badge is not None:
            text = self._build_top_branch_status_text()
            badge.setText(text)
            badge.setToolTip(text)

        combo = getattr(self, "top_branch_status_combo", None)
        if combo is not None:
            combo.blockSignals(True)
            current_code = str(self.selected_branch_code or "").strip().upper()
            index = combo.findData(current_code)
            if index >= 0:
                combo.setCurrentIndex(index)
            else:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def _init_top_branch_status_combo(self):
        if not hasattr(self, "top_branch_status_combo") or self.top_branch_status_combo is None:
            return
        self.top_branch_status_combo.blockSignals(True)
        self.top_branch_status_combo.clear()
        
        self.top_branch_status_combo.addItem("Vista global de todas las sucursales", "")
        
        try:
            from utils.file_handler import get_user_file_path
            fp = get_user_file_path(self.username, "dispositivos_hijos.json")
            if fp.exists():
                with open(fp, "r", encoding="utf-8") as f:
                    devs = json.load(f)
                if isinstance(devs, list):
                    for d in devs:
                        if (
                            isinstance(d, dict)
                            and str(d.get("estado", "activo")).strip().lower() != "bloqueado"
                        ):
                            code = str(d.get("codigo_dispositivo", "")).strip().upper()
                            name = str(d.get("nombre_optica", d.get("nombre_dispositivo", d.get("nombre", "")))).strip()
                            direccion = str(d.get("direccion", d.get("ciudad", ""))).strip()
                            
                            display_text = name
                            if direccion:
                                display_text = f"{name} - {direccion}"
                            if not display_text:
                                display_text = code
                                
                            if code:
                                self.top_branch_status_combo.addItem(display_text, code)
        except Exception as e:
            print(f"Error cargando sucursales para combo: {e}")
            
        current_code = str(self.selected_branch_code or "").strip().upper()
        index = self.top_branch_status_combo.findData(current_code)
        if index >= 0:
            self.top_branch_status_combo.setCurrentIndex(index)
        else:
            self.top_branch_status_combo.setCurrentIndex(0)
            
        self.top_branch_status_combo.blockSignals(False)
        try:
            self.top_branch_status_combo.currentIndexChanged.disconnect()
        except Exception:
            pass
        self.top_branch_status_combo.currentIndexChanged.connect(self._on_top_branch_combo_changed)

    def _on_top_branch_combo_changed(self, index):
        if index < 0:
            return
        code = self.top_branch_status_combo.itemData(index)
        label = self.top_branch_status_combo.itemText(index)
        
        if not code:
            label = "Todas las sucursales"
        else:
            if " - " in label:
                label = label.split(" - ", 1)[0].strip()
        
        self.on_branch_context_changed(code, label)

    def _normalize_ui_texts(self, root_widget=None):
        """
        Corrige texto mojibake en widgets visibles (tildes/caracteres rotos).
        """
        root = root_widget if isinstance(root_widget, QtWidgets.QWidget) else self
        if root is None:
            return

        def _normalize_get_set(getter, setter):
            try:
                original = getter()
            except Exception:
                return
            if not isinstance(original, str) or not original:
                return
            fixed = maybe_normalize_ui_text(original)
            if fixed != original:
                try:
                    setter(fixed)
                except Exception:
                    pass

        widgets = [root]
        try:
            widgets.extend(root.findChildren(QtWidgets.QWidget))
        except Exception:
            pass

        for widget in widgets:
            if isinstance(widget, (QtWidgets.QLabel, QtWidgets.QPushButton, QtWidgets.QCheckBox, QtWidgets.QRadioButton)):
                _normalize_get_set(widget.text, widget.setText)

            if isinstance(widget, QtWidgets.QGroupBox):
                _normalize_get_set(widget.title, widget.setTitle)

            if isinstance(widget, QtWidgets.QLineEdit):
                _normalize_get_set(widget.placeholderText, widget.setPlaceholderText)

            if isinstance(widget, QtWidgets.QComboBox):
                try:
                    for i in range(widget.count()):
                        item_text = widget.itemText(i)
                        fixed = maybe_normalize_ui_text(item_text)
                        if fixed != item_text:
                            widget.setItemText(i, fixed)
                except Exception:
                    pass

            if isinstance(widget, QtWidgets.QTabWidget):
                try:
                    for i in range(widget.count()):
                        tab_text = widget.tabText(i)
                        fixed = maybe_normalize_ui_text(tab_text)
                        if fixed != tab_text:
                            widget.setTabText(i, fixed)
                except Exception:
                    pass

            if isinstance(widget, QtWidgets.QTableWidget):
                try:
                    for i in range(widget.columnCount()):
                        item = widget.horizontalHeaderItem(i)
                        if item is None:
                            continue
                        txt = item.text()
                        fixed = maybe_normalize_ui_text(txt)
                        if fixed != txt:
                            item.setText(fixed)
                except Exception:
                    pass

        try:
            for action in self.findChildren(QtWidgets.QAction):
                txt = action.text()
                fixed = maybe_normalize_ui_text(txt)
                if fixed != txt:
                    action.setText(fixed)
        except Exception:
            pass

    def _schedule_ui_text_normalization(self, root_widget=None, delay_ms=0):
        QtCore.QTimer.singleShot(int(delay_ms), lambda: self._normalize_ui_texts(root_widget))
        
    def setup_main_window(self):
        """Configura la ventana principal y carga solo los componentes esenciales."""
        # Propiedades de la ventana
        self.setWindowTitle(self._get_window_title())
        self.setMinimumSize(800, 500)
        self.resize(1200, 700)
        
        # Mostrar barra nativa de Windows
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, False)
        self.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, True)
        
        # Variable para el overlay de maximizaciÃ³n
        self._snap_overlay = None
        self._snap_active = False
        
        # Establecer Ã­cono de la ventana
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Widget principal
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(main_widget)
        
        # Layout principal: barra superior full-width + Ã¡rea horizontal (sidebar + contenido)
        outer_layout = QVBoxLayout(main_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        # Crear el widget de la barra lateral
        toolbar = QWidget()
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 15, 8, 15)
        toolbar_layout.setSpacing(10)

        # Establecer un ancho fijo para la barra lateral (ligeramente mÃ¡s ancho)
        toolbar.setFixedWidth(69)
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #FCFDFE;
                border-right: 1px solid #E6ECF5;
            }
        """)

        # Configurar la barra lateral
        self.setup_toolbar(toolbar, toolbar_layout)

        # Contenedor principal para el contenido
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Barra de menÃº superior estilo Office/Adobe (ajustada altura)
        menu_bar = QWidget()
        menu_bar.setFixedHeight(60)
        menu_bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #FFFFFF, stop:1 #F7FAFE);
                border-bottom: 1px solid #E8EEF6;
            }
            QFrame {
                background-color: transparent;
            }
            QPushButton {
                padding: 6px 14px;
                border: none;
                color: #263142;
                font-size: 13px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
                background: transparent;
                text-align: left;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #EEF4FF;
                color: #2157D5;
            }
            QPushButton:pressed {
                background-color: #DCE9FF;
                color: #1B4BBB;
            }
            QLabel {
                color: #64748B;
                padding: 0 8px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        menu_layout = QHBoxLayout(menu_bar)
        menu_layout.setContentsMargins(15, 8, 15, 8)
        menu_layout.setSpacing(2)

        # Logo/Nombre de la empresa al lado izquierdo
        logo_label = QLabel("VISO")
        logo_label.setStyleSheet("""
            QLabel {
                color: #2157D5;
                font-size: 17px;
                font-weight: bold;
                padding: 0 15px 0 5px;
                border-right: 1px solid #E6ECF5;
            }
        """)
        menu_layout.addWidget(logo_label)

        # Grupo de botones principales
        main_buttons = QFrame()
        main_buttons_layout = QHBoxLayout(main_buttons)
        main_buttons_layout.setContentsMargins(0, 0, 10, 0)
        main_buttons_layout.setSpacing(3)
        self._topbar_main_buttons = main_buttons

        # Crear menÃºs desplegables segÃºn tipo de dispositivo.
        # "trabajador": funciones operativas, "madre": ademÃ¡s funciones administrativas.
        inventario_items = [
            ('Ver Inventario', lambda: self.mostrar_frame(3)),
        ]
        if self.es_dispositivo_madre():
            inventario_items.extend([
                ('CategorÃ­as', lambda: self.mostrar_frame(16)),
                ('Reportes', lambda: self.mostrar_frame(14)),
            ])

        herramientas_items = [
            ('Generador de CÃ³digos de Barras', lambda: self.open_barcode_generator()),
            ('Centro de sincronizaciÃ³n', lambda: self.open_sync_center()),
            ('Papelera y recuperaciÃ³n', lambda: self.open_trash_recovery()),
        ]
        if self.es_dispositivo_madre():
            herramientas_items.extend([
                ('Datos y libro contable', lambda: self.open_audit_page()),
                ('CumpleaÃ±os', lambda: self.open_birthdays_page()),
            ])

        nav_items = [
            ('Inicio', [
                ('Panel Principal', lambda: self.mostrar_frame(0)),
                ('ConfiguraciÃ³n', lambda: self.mostrar_frame(10)),
            ]),
            ('Inventario', inventario_items),
            ('Ventas', [
                ('Nueva Venta', lambda: self.mostrar_frame(4)),
                ('Venta Manual', lambda: self.ir_a_venta_manual()),
                ('Historial de Deudas', lambda: self.ir_a_historial_deudas()),
                ('Historial de Ventas', lambda: self.ir_a_historial_ventas()),
                ('Guia de Remision', lambda: self.ir_a_guia_remision()),
                ('Generar Reporte', lambda: self.ir_a_historial_ventas()),
            ]),
            ('Herramientas', herramientas_items),
        ]
        
        for menu_name, items in nav_items:
            # Crear el menÃº desplegable
            menu = QtWidgets.QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: white;
                    border: 1px solid #E6ECF5;
                    border-radius: 10px;
                    padding: 8px;
                }
                QMenu::item {
                    padding: 8px 20px 8px 20px;
                    color: #263142;
                    font-size: 13px;
                    border-radius: 8px;
                }
                QMenu::item:selected {
                    background-color: #EEF4FF;
                    color: #2157D5;
                }
                QMenu::item:hover {
                    background-color: #EEF4FF;
                }
            """)
            
            # Agregar las opciones al menÃº
            for item_name, callback in items:
                action = menu.addAction(item_name)
                action.triggered.connect(callback)
            
            # Crear el botÃ³n del menÃº
            btn = QPushButton(menu_name)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 14px;
                    border: none;
                    color: #263142;
                    font-size: 13px;
                    background: transparent;
                    border-radius: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #EEF4FF;
                    color: #2157D5;
                }
                QPushButton:pressed {
                    background-color: #DCE9FF;
                    color: #1B4BBB;
                }
            """)
            
            # Conectar el menÃº al botÃ³n
            btn.clicked.connect(lambda checked, m=menu, b=btn: m.exec_(b.mapToGlobal(QtCore.QPoint(0, b.height()))))
            main_buttons_layout.addWidget(btn)
        menu_layout.addWidget(main_buttons)

        # Boton hamburguesa (visible solo en pantallas angostas)
        self._topbar_hamburger_btn = QtWidgets.QToolButton()
        self._topbar_hamburger_btn.setObjectName("topbarHamburger")
        self._topbar_hamburger_btn.setFixedSize(40, 40)
        self._topbar_hamburger_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            self._topbar_hamburger_btn.setIcon(
                QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_TitleBarMenuButton)
            )
        except Exception:
            self._topbar_hamburger_btn.setText("|||")
        self._topbar_hamburger_btn.setStyleSheet("""
            QToolButton#topbarHamburger {
                background: transparent;
                border: none;
                padding: 6px;
                border-radius: 10px;
            }
            QToolButton#topbarHamburger:hover {
                background: #EEF4FF;
            }
            QToolButton#topbarHamburger:pressed {
                background: #DCE9FF;
            }
        """)
        self._topbar_hamburger_btn.clicked.connect(self._open_topbar_hamburger_menu)
        self._topbar_hamburger_btn.setVisible(False)
        menu_layout.insertWidget(0, self._topbar_hamburger_btn)

        # Badge de contexto sucursal/rol (top bar)
        self.top_branch_status_badge = QLabel()
        self.top_branch_status_badge.setObjectName("topBranchStatusBadge")
        self.top_branch_status_badge.setFixedHeight(30)
        self.top_branch_status_badge.setMinimumWidth(320)
        self.top_branch_status_badge.setMaximumWidth(560)
        self.top_branch_status_badge.setAlignment(Qt.AlignCenter)
        self.top_branch_status_badge.setStyleSheet("""
            QLabel#topBranchStatusBadge {
                color: #1E3A5F;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #EEF4FF, stop:1 #F8FBFF);
                border: 1px solid #D7E5FF;
                border-radius: 15px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 700;
            }
        """)

        # Si es madre (administrador), habilitamos el combo box de selección de sucursal
        self.top_branch_status_combo = QtWidgets.QComboBox()
        self.top_branch_status_combo.setObjectName("topBranchStatusCombo")
        self.top_branch_status_combo.setFixedHeight(30)
        self.top_branch_status_combo.setMinimumWidth(320)
        self.top_branch_status_combo.setMaximumWidth(560)
        self.top_branch_status_combo.setStyleSheet("""
            QComboBox#topBranchStatusCombo {
                color: #1E3A5F;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #EEF4FF, stop:1 #F8FBFF);
                border: 1px solid #D7E5FF;
                border-radius: 15px;
                padding: 2px 25px 2px 15px;
                font-size: 12px;
                font-weight: 700;
            }
            QComboBox#topBranchStatusCombo::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 0px;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
            }
            QComboBox#topBranchStatusCombo::down-arrow {
                image: none;
                border: none;
            }
        """)

        if self.es_dispositivo_madre():
            self._init_top_branch_status_combo()
            menu_layout.addWidget(self.top_branch_status_combo)
            self._topbar_branch_badge = self.top_branch_status_combo
            self.top_branch_status_badge.setVisible(False)
        else:
            self._refresh_top_branch_status_badge()
            menu_layout.addWidget(self.top_branch_status_badge)
            self._topbar_branch_badge = self.top_branch_status_badge

        # Controles de ventana personalizados (izquierda del buscador)
        left_controls = QFrame()
        left_controls_layout = QHBoxLayout(left_controls)
        left_controls_layout.setContentsMargins(0, 0, 0, 0)
        left_controls_layout.setSpacing(6)
        left_controls_layout.setAlignment(Qt.AlignTop)
        # Guardar referencia para modo responsive (ocultar/mostrar en pantallas angostas).
        self._topbar_right_controls = left_controls

        # BotÃ³n de notificaciones (nuevo)
        self.notifications_popup = NotificationsPopup(self)
        # Cargar notificaciones histÃ³ricas apenas se crea la popup (pero NO mostrar popup aÃºn)
        self.notifications_popup.load_notifications_from_history()
        # Mantener popup cerrada por defecto
        self.notifications_popup.hide()
        
        btn_notifications = QPushButton()
        notifications_icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'bell.svg')
        self.notification_badge = QLabel("0")
        self.notification_badge.setStyleSheet("""
            QLabel {
                background: #E11D48;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 10px;
                padding: 2px 5px;
                min-width: 16px;
                text-align: center;
            }
        """)
        self.notification_badge.setAlignment(Qt.AlignCenter)
        self.notification_badge.hide()  # Ocultar inicialmente
        
        # Widget contenedor para botÃ³n y badge
        notif_container = QWidget()
        notif_layout = QHBoxLayout(notif_container)
        notif_layout.setContentsMargins(0, 0, 0, 0)
        notif_layout.setSpacing(-15)  # Superponer el badge
        notif_layout.addWidget(btn_notifications)
        notif_layout.addWidget(self.notification_badge, alignment=Qt.AlignTop | Qt.AlignRight)
        notif_container.setFixedSize(44, 44)
        
        # Conectar para actualizar badge
        self.notifications_popup.unread_count_changed.connect(self.update_notification_badge)
        if os.path.exists(notifications_icon_path):
            btn_notifications.setIcon(QIcon(notifications_icon_path))
            btn_notifications.setIconSize(QtCore.QSize(22, 22))
        else:
            btn_notifications.setText("\U0001F514")
        btn_notifications.setFixedSize(44, 44)
        btn_notifications.setFlat(True)
        btn_notifications.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_notifications = btn_notifications
        btn_notifications.setStyleSheet('''
            QPushButton {
                background: transparent;
                border: none;
                padding: 10px;
                margin: 0px;
                border-radius: 12px;
                font-size: 20px;
            }
            QPushButton:hover {
                background: rgba(13, 110, 253, 0.08);
            }
            QPushButton:pressed {
                background: rgba(13, 110, 253, 0.14);
            }
        ''')
        btn_notifications.clicked.connect(lambda: self.toggle_notifications_popup())
        left_controls_layout.addWidget(notif_container)

        # Definir ruta de iconos
        icons_dir_ctrl = os.path.join(os.path.dirname(__file__), 'icons')

        # BotÃ³n de Guardar/Backup Manual
        self._backup_button = QPushButton()
        
        # Cargar icono SVG de guardar
        save_icon_path = os.path.join(icons_dir_ctrl, 'save.svg')
        if os.path.exists(save_icon_path):
            self._backup_button.setIcon(QIcon(save_icon_path))
            self._backup_button.setIconSize(QtCore.QSize(16, 16))
        else:
            self._backup_button.setText("\U0001F4BE")
        
        self._backup_button.setFixedSize(44, 44)
        self._backup_button.setFlat(True)
        self._backup_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._backup_button.setToolTip("Guardar respaldo manual")
        self._backup_button.setStyleSheet('''
            QPushButton {
                background: transparent;
                border: none;
                padding: 10px;
                margin: 0px;
                border-radius: 12px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: rgba(13, 110, 253, 0.08);
            }
            QPushButton:pressed {
                background: rgba(13, 110, 253, 0.14);
            }
        ''')
        
        # Guardar icono original para restaurar despuÃ©s
        self._backup_button_original_icon = QIcon(save_icon_path) if os.path.exists(save_icon_path) else None
        self._backup_button.setVisible(self.es_dispositivo_madre())
        
        # Conectar botÃ³n de guardar
        self._backup_button.clicked.connect(self.manual_backup)
        left_controls_layout.addWidget(self._backup_button)

        self._sync_center_button = QPushButton()
        sync_icon_path = os.path.join(icons_dir_ctrl, 'refresh.svg')
        if os.path.exists(sync_icon_path):
            self._sync_center_button.setIcon(QIcon(sync_icon_path))
            self._sync_center_button.setIconSize(QtCore.QSize(16, 16))
        else:
            self._sync_center_button.setText("SC")

        self._sync_center_button.setFixedSize(44, 44)
        self._sync_center_button.setFlat(True)
        self._sync_center_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sync_center_button.setToolTip("Centro de sincronizaciÃ³n")
        self._sync_center_button.setStyleSheet('''
            QPushButton {
                background: transparent;
                border: none;
                padding: 10px;
                margin: 0px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(13, 110, 253, 0.08);
            }
            QPushButton:pressed {
                background: rgba(13, 110, 253, 0.14);
            }
        ''')
        self._sync_center_button.clicked.connect(self.open_sync_center)
        left_controls_layout.addWidget(self._sync_center_button)

        # BotÃ³n de perfil al final de la fila
        profile_top_btn = QPushButton()
        profile_top_btn.setFixedSize(44, 44)
        profile_top_icon = os.path.join(os.path.dirname(__file__), 'icons', 'profile.svg')
        if os.path.exists(profile_top_icon):
            profile_top_btn.setIcon(QIcon(profile_top_icon))
            profile_top_btn.setIconSize(QtCore.QSize(22, 22))
        profile_top_btn.setToolTip("Mi perfil")
        profile_top_btn.clicked.connect(lambda: self.mostrar_frame(12))
        profile_top_btn.setStyleSheet('''
            QPushButton {
                background: transparent;
                border: none;
                padding: 6px;
                margin-right: 5px;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(13, 110, 253, 0.08);
            }
            QPushButton:pressed {
                background: rgba(13, 110, 253, 0.14);
            }
        ''')
        left_controls_layout.addWidget(profile_top_btn)
        tools_frame = QFrame()
        tools_frame.setObjectName("toolsFrame")
        tools_layout = QHBoxLayout(tools_frame)
        tools_layout.setContentsMargins(10, 0, 10, 0)
        tools_layout.setSpacing(10)
        tools_frame.setStyleSheet("""
            #toolsFrame {
                background: #FFFFFF;
                border: 1px solid #E6ECF5;
                border-radius: 16px;
                min-height: 48px;
            }
        """)
        self._topbar_tools_frame = tools_frame

        # Contenedor del buscador con estilo moderno
        search_container = QFrame()
        search_container.setObjectName("searchContainer")
        search_container_layout = QHBoxLayout(search_container)
        search_container_layout.setContentsMargins(0, 0, 0, 0)
        search_container_layout.setSpacing(0)
        
        # Campo de bÃºsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar pacientes, productos o DNI")
        self.search_input.setFixedWidth(320)
        self.search_input.setObjectName("searchInput")
        
        # BotÃ³n de bÃºsqueda con Ã­cono SVG
        search_btn = QPushButton()
        search_btn.setObjectName("searchButton")
        search_icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'search.svg')
        if os.path.exists(search_icon_path):
            search_btn.setIcon(QIcon(search_icon_path))
            search_btn.setIconSize(QtCore.QSize(18, 18))
        
        # Agregar widgets al contenedor
        search_container_layout.addWidget(self.search_input)
        search_container_layout.addWidget(search_btn)
        self._topbar_search_container = search_container
        
        # Agregar el contenedor de bÃºsqueda al layout de herramientas
        tools_layout.addWidget(search_container)
        
        # Estilos modernos para el buscador
        search_container.setStyleSheet("""
            #searchContainer {
                background: transparent;
                border: none;
                margin: 8px 0;
            }
            #searchInput {
                background: #F8FAFD;
                border: 1px solid #E2E8F0;
                padding: 4px 14px;
                font-size: 13px;
                color: #263142;
                min-height: 34px;
                border-radius: 12px 0 0 12px;
            }
            #searchInput:focus {
                border: 1px solid #C9DBFF;
            }
            #searchInput::placeholder {
                color: #7C8CA3;
            }
            #searchButton {
                background: #F8FAFD;
                border: 1px solid #E2E8F0;
                border-left: none;
                padding: 4px 12px;
                border-radius: 0 12px 12px 0;
                min-width: 36px;
                min-height: 34px;
                icon-size: 16px;
            }
            #searchButton:hover {
                background: #EEF4FF;
            }
            #searchButton:pressed {
                background: #DCE9FF;
            }
            #searchButton:focus {
                outline: none;
            }
        """)
        
        # Conectar eventos de busqueda
        self._search_results_menu = None

        def cerrar_resultados_busqueda():
            menu_actual = getattr(self, "_search_results_menu", None)
            if menu_actual is not None and menu_actual.isVisible():
                menu_actual.close()

        def realizar_busqueda():
            texto = self.search_input.text().strip()
            if not texto:
                cerrar_resultados_busqueda()
                return

            # Buscar en pacientes y productos (usando cache)
            pacientes = self.cache.get_pacientes(self.username)
            productos = self.cache.get_productos(self.username)

            resultados = []

            # Buscar en pacientes
            for p in pacientes:
                if not isinstance(p, dict):
                    continue
                if texto.lower() in str(p.get('nombre', '')).lower() or \
                   texto.lower() in str(p.get('dni', '')).lower():
                    resultados.append(('Paciente', p))

            # Buscar en productos
            for p in productos:
                if not isinstance(p, dict):
                    continue
                if texto.lower() in str(p.get('nombre', '')).lower() or \
                   texto.lower() in str(p.get('codigo', '')).lower():
                    resultados.append(('Producto', p))

            if not resultados:
                QtWidgets.QMessageBox.information(
                    self,
                    "BÃºsqueda",
                    "No se encontraron resultados."
                )
                return

            # Cerrar popup anterior si seguÃ­a abierto
            cerrar_resultados_busqueda()

            # Popup con lista y scrollbar real
            popup = QtWidgets.QFrame(self, QtCore.Qt.Popup)
            popup.setObjectName("globalSearchPopup")
            popup.setStyleSheet("""
                QFrame#globalSearchPopup {
                    background: white;
                    border: 1px solid #DADADA;
                    border-radius: 8px;
                }
                QLabel#globalSearchTitle {
                    font-size: 12px;
                    color: #666666;
                    padding: 8px 10px 6px 10px;
                }
                QListWidget {
                    border: none;
                    outline: none;
                    background: white;
                }
                QListWidget::item {
                    padding: 8px 10px;
                    color: #2C2C2C;
                    border-bottom: 1px solid #F3F3F3;
                }
                QListWidget::item:selected {
                    background: #E5F3FF;
                    color: #0078D4;
                }
                QScrollBar:vertical {
                    width: 10px;
                    background: #FAFAFA;
                }
                QScrollBar::handle:vertical {
                    background: #CFCFCF;
                    border-radius: 5px;
                    min-height: 30px;
                }
            """)

            popup_layout = QtWidgets.QVBoxLayout(popup)
            popup_layout.setContentsMargins(0, 0, 0, 0)
            popup_layout.setSpacing(0)

            total_resultados = len(resultados)
            lbl_title = QtWidgets.QLabel(f"Resultados: {total_resultados}")
            lbl_title.setObjectName("globalSearchTitle")
            popup_layout.addWidget(lbl_title)

            list_widget = QtWidgets.QListWidget(popup)
            list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            list_widget.setMinimumWidth(420)
            list_widget.setMaximumHeight(360)
            popup_layout.addWidget(list_widget)

            for tipo, item in resultados:
                if tipo == 'Paciente':
                    nombre = item.get('nombre', '')
                    dni = item.get('dni', '')
                    texto_item = f"Paciente: {nombre} (DNI: {dni})"
                else:
                    nombre = item.get('nombre', '')
                    stock = item.get('stock', '0')
                    texto_item = f"Producto: {nombre} (Stock: {stock})"

                fila = QtWidgets.QListWidgetItem(texto_item)
                fila.setData(QtCore.Qt.UserRole, {'tipo': tipo, 'item': item})
                list_widget.addItem(fila)

            def abrir_resultado(fila):
                if fila is None:
                    return
                payload = fila.data(QtCore.Qt.UserRole) or {}
                tipo_sel = payload.get('tipo')
                item_sel = payload.get('item')
                cerrar_resultados_busqueda()
                if tipo_sel == 'Paciente':
                    self.mostrar_paciente(item_sel)
                elif tipo_sel == 'Producto':
                    self.mostrar_producto(item_sel)

            list_widget.itemClicked.connect(abrir_resultado)
            list_widget.itemActivated.connect(abrir_resultado)
            if list_widget.count() > 0:
                list_widget.setCurrentRow(0)
            list_widget.setFocus()

            self._search_results_menu = popup
            popup.destroyed.connect(lambda: setattr(self, "_search_results_menu", None))

            # Mostrar popup debajo del buscador (o debajo del ancla alternativa si existe).
            anchor = getattr(self, "_search_popup_anchor_widget", None) or search_container
            try:
                popup.move(anchor.mapToGlobal(QtCore.QPoint(0, anchor.height() + 2)))
            except Exception:
                popup.move(search_container.mapToGlobal(QtCore.QPoint(0, search_container.height() + 2)))
            popup.show()

        search_btn.clicked.connect(realizar_busqueda)
        self.search_input.returnPressed.connect(realizar_busqueda)  # Buscar al presionar Enter
        self.search_input.textEdited.connect(lambda _: cerrar_resultados_busqueda())
        self.search_escape_shortcut = QShortcut(QKeySequence("Esc"), self.search_input)
        self.search_escape_shortcut.activated.connect(cerrar_resultados_busqueda)

        # Exponer busqueda global para QML (menu hamburguesa).
        def _global_search_with_text(text):
            self.search_input.setText(str(text or "").strip())
            # Si el topbar estÃ¡ en modo compacto, anclar el popup de resultados al botÃ³n hamburguesa.
            anchor = None
            try:
                hb = getattr(self, "_topbar_hamburger_btn", None)
                if hb is not None and hb.isVisible():
                    anchor = hb
            except Exception:
                anchor = None
            self._search_popup_anchor_widget = anchor
            try:
                realizar_busqueda()
            finally:
                self._search_popup_anchor_widget = None
        self._global_search_with_text = _global_search_with_text

        # AÃ±adir el tools_frame (contiene el buscador). Lo colocamos entre dos stretches
        # para que quede centrado horizontalmente en la barra superior.
        menu_layout.addStretch()
        menu_layout.addWidget(tools_frame)
        menu_layout.addStretch()
        # Mover los controles de ventana al extremo derecho
        menu_layout.addWidget(left_controls)

        # Agregar barra de menÃº al layout exterior (full-width)
        outer_layout.addWidget(menu_bar)
        # Ajustar visibilidad inicial segun ancho (modo compacto vs normal).
        try:
            self._update_topbar_responsive()
        except Exception:
            pass

        # Stacked Widget para las pÃ¡ginas con scroll area
        self.stacked_widget = AnimatedStackedWidget()
        self.stacked_widget.setMinimumSize(0, 0)
        
        # Envolver el stacked widget en un scroll area para pantallas pequeÃ±as
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                width: 12px;
                background-color: #f5f5f5;
            }
            QScrollBar::handle:vertical {
                background-color: #ccc;
                border-radius: 6px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #999;
            }
        """)
        scroll_area.setWidget(self.stacked_widget)
        try:
            self.stacked_widget.currentChanged.connect(lambda *_: self._refresh_system_status_bar())
        except Exception:
            pass
        content_layout.addWidget(scroll_area)

        # Montar la zona central (sidebar + contenido)
        middle_layout.addWidget(toolbar)
        middle_layout.addWidget(self.content_widget)
        outer_layout.addLayout(middle_layout)

        # Barra de estado inferior del sistema
        self.system_status_bar = QFrame()
        self.system_status_bar.setObjectName("systemStatusBar")
        self.system_status_bar.setFixedHeight(22)
        self.system_status_bar.setStyleSheet("""
            QFrame#systemStatusBar {
                background: #F8FAFD;
                border-top: 1px solid #E6ECF5;
            }
            QLabel#systemPageLabel {
                color: #5B677A;
                font-size: 11px;
                font-weight: 600;
                padding-left: 8px;
            }
            QPushButton#systemStatusButton {
                color: #4B5565;
                font-size: 11px;
                padding: 0 8px 0 0;
                border: none;
                background: transparent;
                text-align: right;
            }
            QPushButton#systemStatusButton:hover {
                color: #2157D5;
            }
            QLabel#systemStatusIcon {
                color: transparent;
                background: #9AA7B8;
                border-radius: 5px;
                min-width: 10px;
                max-width: 10px;
                min-height: 10px;
                max-height: 10px;
            }
            QProgressBar#systemStatusProgress {
                border: none;
                background: #E5EBF3;
                border-radius: 2px;
            }
            QProgressBar#systemStatusProgress::chunk {
                background: #2563EB;
                border-radius: 2px;
            }
        """)
        system_status_layout = QHBoxLayout(self.system_status_bar)
        system_status_layout.setContentsMargins(6, 0, 6, 0)
        system_status_layout.setSpacing(6)

        self.system_page_label = QLabel("Pagina: Inicio")
        self.system_page_label.setObjectName("systemPageLabel")
        system_status_layout.addWidget(self.system_page_label, 0, Qt.AlignVCenter)
        system_status_layout.addStretch()

        self.system_status_icon = QLabel("")
        self.system_status_icon.setObjectName("systemStatusIcon")
        self.system_status_icon.setAlignment(Qt.AlignCenter)
        self.system_status_icon.setFixedSize(10, 10)
        system_status_layout.addWidget(self.system_status_icon, 0, Qt.AlignVCenter)

        self.system_status_text = QPushButton("Iniciando sistema...")
        self.system_status_text.setObjectName("systemStatusButton")
        self.system_status_text.setFlat(True)
        self.system_status_text.setCursor(Qt.PointingHandCursor)
        self.system_status_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.system_status_text.clicked.connect(self.open_pending_sync_dialog)
        system_status_layout.addWidget(self.system_status_text, 1)

        self.system_status_progress = QtWidgets.QProgressBar()
        self.system_status_progress.setObjectName("systemStatusProgress")
        self.system_status_progress.setRange(0, 100)
        self.system_status_progress.setValue(0)
        self.system_status_progress.setTextVisible(False)
        self.system_status_progress.setFixedSize(72, 4)
        self.system_status_progress.hide()
        system_status_layout.addWidget(self.system_status_progress, 0, Qt.AlignVCenter)

        outer_layout.addWidget(self.system_status_bar)

        # NO crear pÃ¡ginas en setup_pages() - se cargarÃ¡n on-demand despuÃ©s de mostrar ventana
        # Esto permite que la ventana se muestre INMEDIATAMENTE sin esperar a cargar datos
        
        # Configurar atajos de teclado de navegacion y zoom
        self.setup_navigation_shortcuts()
        self.setup_zoom_shortcuts()

        # Verificar licencia en background DESPUÃ‰S de mostrar la ventana
        # Usar QTimer para postponer y que la ventana se renderice primero
        QtCore.QTimer.singleShot(100, self._verify_license_on_startup)
        
        # Cargar home page despuÃ©s de mostrar ventana (evita delay en startup)
        QtCore.QTimer.singleShot(100, self.go_to_home)
        # Reparar textos con tildes/codificacion al inicio.
        self._schedule_ui_text_normalization(delay_ms=600)
        self._schedule_ui_text_normalization(delay_ms=2200)
        # Verificar nueva versiÃ³n en background y notificar por campanita
        QtCore.QTimer.singleShot(int(self.UPDATE_CHECK_STARTUP_DELAY_MS), self._check_update_on_startup)
        # Polling de eventos de sucursales para dispositivo madre
        QtCore.QTimer.singleShot(int(self.DEVICE_EVENTS_STARTUP_DELAY_MS), self._start_device_event_polling)
        self._start_system_status_polling()
        self._refresh_system_status_bar()

    def _resolve_current_page_name(self):
        page_names_by_index = {
            0: "Inicio",
            1: "Pacientes",
            2: "Nueva graduacion",
            3: "Inventario",
            4: "Ventas",
            5: "Kardex",
            6: "Calendario",
            7: "Historial de citas",
            9: "Clientes",
            10: "Configuracion",
            11: "Servicios",
            12: "Perfil",
            13: "Registro de ventas",
            14: "Reportes",
            15: "Plantilla de boleta",
            16: "Categorias",
        }
        widget_names = {
            "HomePage": "Inicio",
            "PatientsPage": "Pacientes",
            "CreatePatientPage": "Nueva graduacion",
            "InventoryPage": "Inventario",
            "SalesPage": "Ventas",
            "KardexPage": "Kardex",
            "AppointmentsPage": "Calendario",
            "AppointmentHistoryWidget": "Historial de citas",
            "CustomersPage": "Clientes",
            "ConfigPage": "Configuracion",
            "ServicesPage": "Servicios",
            "ProfilePage": "Perfil",
            "RegistroVentasPage": "Registro de ventas",
            "AdvancedReportsPage": "Reportes",
            "PlantillaBobetaPage": "Plantilla de boleta",
            "CategoriesPage": "Categorias",
            "BirthdaysPage": "Cumpleanos",
            "AuditPage": "Libro contable",
        }

        try:
            current_widget = self.stacked_widget.currentWidget()
        except Exception:
            current_widget = None

        if current_widget is not None:
            try:
                if bool(current_widget.property("_is_loading_placeholder")):
                    title_label = getattr(current_widget, "title_label", None)
                    title_text = str(title_label.text() if title_label is not None else "").strip()
                    if title_text:
                        return title_text.replace("Cargando ", "").replace("...", "").strip() or "Cargando"
            except Exception:
                pass

            class_name = current_widget.__class__.__name__
            if class_name in widget_names:
                return widget_names[class_name]

        try:
            current_page = getattr(self, "current_page", None)
            if isinstance(current_page, int) and current_page in page_names_by_index:
                return page_names_by_index[current_page]
        except Exception:
            pass

        return "Sistema"

    def _format_pending_queue_summary(self, queue_by_dataset):
        if not isinstance(queue_by_dataset, dict) or not queue_by_dataset:
            return ""
        ordered = sorted(
            ((str(k or "otros"), int(v or 0)) for k, v in queue_by_dataset.items() if int(v or 0) > 0),
            key=lambda item: (-item[1], item[0]),
        )
        parts = [f"{name} {count}" for name, count in ordered[:3]]
        extra = max(0, len(ordered) - 3)
        if extra:
            parts.append(f"+{extra} mas")
        return ", ".join(parts)

    def _apply_system_status_style(self, color_hex: str):
        color = str(color_hex or "#9AA7B8")
        try:
            if hasattr(self, "system_status_text") and self.system_status_text is not None:
                self.system_status_text.setStyleSheet(
                    f"QPushButton#systemStatusButton {{ color: {color}; font-size: 11px; padding: 0 8px 0 0; border: none; background: transparent; text-align: right; }}"
                    "QPushButton#systemStatusButton:hover { color: #2157D5; }"
                )
        except Exception:
            pass

    def _set_system_status_icon_state(self, mode="dot", color_hex="#9AA7B8"):
        icon = getattr(self, "system_status_icon", None)
        if icon is None:
            return

        color = str(color_hex or "#9AA7B8")
        mode = str(mode or "dot").strip().lower()

        try:
            icon.show()
            if mode == "warning":
                icon.setFixedSize(14, 14)
                icon.setText("!")
                icon.setStyleSheet(
                    f"QLabel#systemStatusIcon {{ color: white; background: {color}; border: 1px solid {color}; border-radius: 7px; font-size: 10px; font-weight: 700; }}"
                )
            elif mode == "check":
                icon.setFixedSize(14, 14)
                icon.setText("✓")
                icon.setStyleSheet(
                    f"QLabel#systemStatusIcon {{ color: white; background: {color}; border: 1px solid {color}; border-radius: 7px; font-size: 10px; font-weight: 700; }}"
                )
            else:
                icon.setFixedSize(10, 10)
                icon.setText("")
                icon.setStyleSheet(
                    f"QLabel#systemStatusIcon {{ color: transparent; background: {color}; border: none; border-radius: 5px; }}"
                )
        except Exception:
            pass

    def _set_system_status_progress_state(self, value=0, color_hex="#2563EB", visible=False):
        bar = getattr(self, "system_status_progress", None)
        if bar is None:
            return

        try:
            safe_value = max(0, min(100, int(round(float(value or 0)))))
        except Exception:
            safe_value = 0
        color = str(color_hex or "#2563EB")

        try:
            bar.setStyleSheet(
                f"QProgressBar#systemStatusProgress {{ border: none; background: transparent; }}"
                f"QProgressBar#systemStatusProgress::chunk {{ background: {color}; border-radius: 1px; }}"
            )
            bar.setValue(safe_value)
            bar.setVisible(bool(visible))
        except Exception:
            pass

    def _resolve_system_status_progress_color(self, active_ops):
        kinds = {
            str(item.get("kind", "") or "").strip().lower()
            for item in (active_ops or [])
            if isinstance(item, dict)
        }
        if "upload" in kinds:
            return "#0EA5A4"
        if "download" in kinds:
            return "#2563EB"
        if "loading" in kinds:
            return "#2563EB"
        return "#2563EB"

    def _advance_system_status_progress(self, active_ops):
        now = time.time()
        signature = "|".join(
            str(item.get("key", "") or "").strip()
            for item in (active_ops or [])
            if isinstance(item, dict)
        )

        if active_ops:
            if signature != self._system_status_active_signature:
                self._system_status_progress_value = max(8, min(self._system_status_progress_value or 0, 22))
                self._system_status_active_signature = signature
            if self._system_status_progress_value < 55:
                self._system_status_progress_value += 7
            elif self._system_status_progress_value < 82:
                self._system_status_progress_value += 4
            elif self._system_status_progress_value < 94:
                self._system_status_progress_value += 1
            self._system_status_progress_value = min(94, self._system_status_progress_value)
            self._system_status_progress_color = self._resolve_system_status_progress_color(active_ops)
            self._system_status_completion_until = 0.0
            self._system_status_snapshot_refresh_pending = True
            return

        if self._system_status_active_signature:
            self._system_status_active_signature = ""
            self._system_status_progress_value = 100
            self._system_status_progress_color = "#16A34A"
            self._system_status_completion_until = now + 1.6
            if self._system_status_snapshot_refresh_pending:
                self._system_status_snapshot_refresh_pending = False
                try:
                    QTimer.singleShot(150, self._queue_system_status_snapshot)
                except Exception:
                    pass
            return

        if self._system_status_completion_until and now >= self._system_status_completion_until:
            self._system_status_completion_until = 0.0
            self._system_status_progress_value = 0

    def _collect_pending_sync_items(self):
        try:
            from utils.sync_manager import get_sync_manager

            sync_mgr = get_sync_manager()
            ids_to_check = []
            for raw in (self.user_id, self.username):
                value = str(raw or "").strip()
                if value and value not in ids_to_check:
                    ids_to_check.append(value)

            seen_queue_ids = set()
            items = []
            for uid in ids_to_check:
                try:
                    pending_items = sync_mgr.queue.get_pending_items(uid, limit=5000)
                except Exception:
                    pending_items = []
                for item in pending_items or []:
                    queue_id = item.get("id")
                    if queue_id in seen_queue_ids:
                        continue
                    seen_queue_ids.add(queue_id)
                    items.append(dict(item))

            items.sort(key=lambda item: str(item.get("timestamp", "")))
            return items
        except Exception:
            return []

    def _dataset_label_for_queue_item(self, dataset):
        mapping = {
            "productos": "Productos",
            "pacientes": "Pacientes",
            "clientes": "Clientes",
            "ventas": "Ventas",
            "kardex": "Kardex",
            "citas": "Citas",
            "graduaciones": "Graduaciones",
            "optometras": "Optometras",
            "datos_generales": "Datos generales",
        }
        key = str(dataset or "").strip().lower()
        return mapping.get(key, key.title() or "Otros")

    def _format_pending_queue_timestamp(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        if text.isdigit():
            try:
                epoch = int(text)
                if epoch > 10_000_000_000:
                    epoch = epoch / 1000.0
                parsed = datetime.datetime.fromtimestamp(epoch)
                return parsed.strftime("%d/%m %H:%M")
            except Exception:
                pass
        normalized = text.replace("T", " ")
        parsed = None
        try:
            parsed = datetime.datetime.fromisoformat(normalized)
        except Exception:
            parsed = None
        if parsed is not None:
            return parsed.strftime("%d/%m %H:%M")
        if len(normalized) >= 16:
            return normalized[:16]
        return normalized

    def _operation_label_for_queue_item(self, operation):
        mapping = {
            "CREATE": "Crear",
            "UPDATE": "Actualizar",
            "DELETE": "Eliminar",
            "SYNC_ALL": "Subida completa",
        }
        return mapping.get(str(operation or "").strip().upper(), str(operation or "").strip() or "Pendiente")

    def _describe_pending_queue_item(self, item):
        dataset = str(item.get("tipo_dato", "") or "").strip().lower()
        operation = str(item.get("operacion", "") or "").strip().upper()
        record_id = str(item.get("registro_id", "") or "").strip()
        content = item.get("contenido")
        if not isinstance(content, dict):
            content = {}

        if operation == "SYNC_ALL":
            for key in ("productos", "pacientes", "clientes", "ventas", "kardex", "citas"):
                dataset_value = content.get(key)
                if isinstance(dataset_value, list):
                    return f"{len(dataset_value)} registros listos para subir"
            return record_id or "Sincronizacion completa pendiente"

        if dataset == "productos":
            nombre = str(content.get("nombre", "") or "").strip()
            codigo = str(content.get("codigo", "") or "").strip()
            if nombre and codigo:
                return f"{nombre} ({codigo})"
            return nombre or codigo or record_id or "Producto pendiente"

        if dataset in ("pacientes", "clientes"):
            nombre = str(content.get("nombre", "") or "").strip()
            dni = str(content.get("dni", "") or "").strip()
            if nombre and dni:
                return f"{nombre} | DNI {dni}"
            return nombre or dni or record_id or "Registro pendiente"

        if dataset == "ventas":
            nombre = str(content.get("paciente_nombre", "") or "").strip()
            dni = str(content.get("paciente_dni", "") or "").strip()
            total = content.get("total", None)
            if nombre and total not in (None, ""):
                return f"{nombre} | S/. {total}"
            return nombre or dni or record_id or "Venta pendiente"

        return record_id or "Cambio pendiente"

    def _build_pending_sync_rows(self, items):
        rows = []
        for item in items or []:
            rows.append({
                "dataset_label": self._dataset_label_for_queue_item(item.get("tipo_dato", "")),
                "operation_label": self._operation_label_for_queue_item(item.get("operacion", "")),
                "detail": self._describe_pending_queue_item(item),
                "timestamp_label": self._format_pending_queue_timestamp(item.get("timestamp", "")),
            })
        return rows

    def open_pending_sync_dialog(self):
        items = self._collect_pending_sync_items()
        rows = self._build_pending_sync_rows(items)
        total = len(rows)
        queue_by_dataset = {}
        for item in items:
            dataset = str(item.get("tipo_dato", "otros") or "otros").strip().lower() or "otros"
            queue_by_dataset[dataset] = int(queue_by_dataset.get(dataset, 0) or 0) + 1

        summary = (
            f"Hay {total} cambio pendiente por subir."
            if total == 1
            else f"Hay {total} cambios pendientes por subir."
        ) if total else "No hay cambios pendientes en cola."

        detail_resume = self._format_pending_queue_summary(queue_by_dataset)
        if detail_resume:
            summary += f"  {detail_resume}"

        internet_ok = dict(getattr(self, "_system_status_snapshot", {}) or {}).get("internet_ok", None)
        if total and internet_ok is False:
            status_text = "Sin internet. Estos cambios siguen guardados localmente hasta que puedas subirlos."
        elif total:
            status_text = "Pulsa 'Subir ahora' para forzar la sincronización de lo pendiente."
        else:
            status_text = "Todo esta sincronizado por ahora."

        dialog = PendingSyncDialog(self)
        dialog.set_items(rows, summary_text=summary, status_text=status_text)
        dialog.force_sync_requested.connect(lambda d=dialog: self._force_pending_sync_from_dialog(d))
        try:
            anchor_top_right = self.system_status_text.mapToGlobal(self.system_status_text.rect().topRight())
            screen = QtWidgets.QApplication.screenAt(anchor_top_right)
            if screen is None:
                screen = QtWidgets.QApplication.primaryScreen()
            available = screen.availableGeometry() if screen is not None else self.geometry()
            dialog_width = dialog.width()
            dialog_height = dialog.height()
            x = anchor_top_right.x() - dialog_width
            y = anchor_top_right.y() - dialog_height - 8
            x = max(available.left() + 8, min(x, available.right() - dialog_width - 8))
            y = max(available.top() + 8, min(y, available.bottom() - dialog_height - 8))
            dialog.move(x, y)
        except Exception:
            pass
        dialog.exec_()

    def _force_pending_sync_from_dialog(self, dialog):
        if getattr(self, "_pending_sync_force_worker", None) is not None:
            return

        dialog.sync_button.setEnabled(False)
        dialog.status_label.setText("Subiendo cambios pendientes...")

        worker = PendingSyncForceWorker(
            user_id=getattr(self, "user_id", None),
            username=getattr(self, "username", None),
            parent=self,
        )
        self._pending_sync_force_worker = worker

        def _finished(result):
            self._pending_sync_force_worker = None
            try:
                self._queue_system_status_snapshot()
                self._refresh_system_status_bar()
            except Exception:
                pass

            items = self._collect_pending_sync_items()
            rows = self._build_pending_sync_rows(items)
            queue_by_dataset = {}
            for item in items:
                dataset = str(item.get("tipo_dato", "otros") or "otros").strip().lower() or "otros"
                queue_by_dataset[dataset] = int(queue_by_dataset.get(dataset, 0) or 0) + 1

            total = len(rows)
            summary = (
                f"Hay {total} cambio pendiente por subir."
                if total == 1
                else f"Hay {total} cambios pendientes por subir."
            ) if total else "No hay cambios pendientes en cola."
            detail_resume = self._format_pending_queue_summary(queue_by_dataset)
            if detail_resume:
                summary += f"  {detail_resume}"

            dialog.set_items(rows, summary_text=summary, status_text=str((result or {}).get("message", "") or ""))

        worker.sync_finished.connect(_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _refresh_system_status_bar(self):
        page_name = self._resolve_current_page_name()
        try:
            self.system_page_label.setText(f"Pagina: {page_name}")
        except Exception:
            pass

        active_ops = []
        try:
            active_ops = get_active_operations()
        except Exception:
            active_ops = []
        self._advance_system_status_progress(active_ops)

        snapshot = dict(getattr(self, "_system_status_snapshot", {}) or {})
        internet_ok = snapshot.get("internet_ok", None)
        queue_total = int(snapshot.get("queue_total", 0) or 0)
        queue_by_dataset = snapshot.get("queue_by_dataset", {}) or {}
        queue_resume = self._format_pending_queue_summary(queue_by_dataset)
        recent_completion = bool(getattr(self, "_system_status_completion_until", 0.0) and time.time() < self._system_status_completion_until)

        color = "#9AA7B8"
        message = "Estado del sistema iniciando..."
        icon_mode = "dot"
        progress_visible = False
        progress_value = int(getattr(self, "_system_status_progress_value", 0) or 0)
        progress_color = str(getattr(self, "_system_status_progress_color", "#2563EB") or "#2563EB")

        if active_ops:
            labels = [str(item.get("label", "")).strip() for item in active_ops if str(item.get("label", "")).strip()]
            if labels:
                message = " | ".join(labels[:2])
                if len(labels) > 2:
                    message += f" | +{len(labels) - 2} mas"
            else:
                message = "Procesando datos..."
            color = progress_color
            icon_mode = "dot"
            progress_visible = True
        elif internet_ok is False and queue_total > 0:
            message = "Sin internet"
            if queue_resume:
                message += f" | pendiente: {queue_resume}"
            else:
                message += f" | {queue_total} cambios en cola"
            color = "#D97706"
            icon_mode = "warning"
        elif internet_ok is False:
            message = "Sin internet | trabajando localmente"
            color = "#D97706"
            icon_mode = "dot"
        elif queue_total > 0:
            message = f"Pendiente de sincronizar: {queue_resume or f'{queue_total} cambios'}"
            color = "#0EA5A4"
            icon_mode = "dot"
        elif internet_ok is True:
            message = "En linea | sin cargas pendientes"
            color = "#16A34A"
            icon_mode = "dot"

        if recent_completion and not (internet_ok is False and queue_total > 0):
            icon_mode = "check"
            progress_visible = True
            progress_value = 100
            progress_color = "#16A34A"

        try:
            self.system_status_text.setText(message)
            self.system_status_text.setToolTip(message)
            self.system_status_text.setCursor(Qt.PointingHandCursor if queue_total > 0 else Qt.ArrowCursor)
        except Exception:
            pass
        self._apply_system_status_style(color)
        self._set_system_status_icon_state(icon_mode, color)
        self._set_system_status_progress_state(progress_value, progress_color, progress_visible)

    def _queue_system_status_snapshot(self):
        worker = getattr(self, "_system_status_worker", None)
        try:
            if worker is not None and worker.isRunning():
                return
        except Exception:
            pass

        worker = SystemStatusSnapshotWorker(
            user_id=getattr(self, "user_id", None),
            username=getattr(self, "username", None),
            parent=self,
        )
        worker.snapshot_ready.connect(self._on_system_status_snapshot_ready)
        worker.finished.connect(worker.deleteLater)
        self._system_status_worker = worker
        worker.start()

    def _on_system_status_snapshot_ready(self, snapshot):
        self._system_status_snapshot = dict(snapshot or {})
        self._system_status_worker = None
        self._refresh_system_status_bar()

    def _start_system_status_polling(self):
        if self._system_status_poll_timer is not None:
            return
        self._system_status_poll_timer = QTimer(self)
        self._system_status_poll_timer.setInterval(180)
        self._system_status_poll_timer.timeout.connect(self._refresh_system_status_bar)
        self._system_status_poll_timer.start()
        QTimer.singleShot(int(self.SYSTEM_STATUS_INITIAL_SNAPSHOT_DELAY_MS), self._queue_system_status_snapshot)

        self._system_status_snapshot_timer = QTimer(self)
        self._system_status_snapshot_timer.setInterval(int(self.SYSTEM_STATUS_SNAPSHOT_POLL_MS))
        self._system_status_snapshot_timer.timeout.connect(self._queue_system_status_snapshot)
        self._system_status_snapshot_timer.start()

    def _parse_version_tuple(self, value):
        """Convierte una versiÃ³n tipo '4.2.10' a tupla comparable."""
        text = str(value or "").strip()
        if not text:
            return tuple()
        nums = re.findall(r"\d+", text)
        if not nums:
            return tuple()
        return tuple(int(n) for n in nums)

    def _is_remote_version_newer(self, remote_version):
        local_t = self._parse_version_tuple(APP_VERSION)
        remote_t = self._parse_version_tuple(remote_version)
        if not local_t or not remote_t:
            return False
        max_len = max(len(local_t), len(remote_t))
        local_pad = local_t + (0,) * (max_len - len(local_t))
        remote_pad = remote_t + (0,) * (max_len - len(remote_t))
        return remote_pad > local_pad

    def _is_remote_version_mismatch(self, remote_version):
        """True cuando la versiÃ³n remota NO coincide con la versiÃ³n local."""
        local_t = self._parse_version_tuple(APP_VERSION)
        remote_t = self._parse_version_tuple(remote_version)
        if local_t and remote_t:
            max_len = max(len(local_t), len(remote_t))
            local_pad = local_t + (0,) * (max_len - len(local_t))
            remote_pad = remote_t + (0,) * (max_len - len(remote_t))
            return remote_pad != local_pad
        return str(remote_version or "").strip() != str(APP_VERSION or "").strip()

    def _push_update_notification(self, notif):
        """Inserta notificaciÃ³n de actualizaciÃ³n evitando duplicados."""
        popup = getattr(self, "notifications_popup", None)
        if popup is None:
            return
        try:
            notif_id = str((notif or {}).get("id", "")).strip()
            if notif_id:
                for existing in (getattr(popup, "all_notifications", []) or []):
                    if str(existing.get("id", "")).strip() == notif_id:
                        return
            popup.add_notification_new(notif)
            logger.info("[UPDATE] NotificaciÃ³n agregada al popup: %s", notif_id or "sin-id")
        except Exception as e:
            logger.warning("[UPDATE] No se pudo agregar notificaciÃ³n: %s", e)

    def _show_update_popup(self, notif):
        """Muestra ventana emergente de actualizacion (thread-safe via signal)."""
        try:
            if not isinstance(notif, dict):
                return

            titulo_notif = str(notif.get("titulo") or "Nueva actualizacion disponible").strip()
            mensaje_notif = str(notif.get("mensaje") or "").strip()
            enlace = str(notif.get("enlace") or "").strip()
            fecha = str(notif.get("fecha") or "").strip()
            remote_version = str(notif.get("version_remota") or "").strip()

            body = mensaje_notif or "Hay una nueva version disponible."
            if fecha:
                body = f"{body}\n\nFecha: {fecha}"
            if enlace:
                body = (
                    f"{body}\n\n"
                    "Presiona 'Copiar enlace' para descargar la actualizacion manualmente."
                )

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Actualizacion del sistema")
            msg.setText(titulo_notif)
            msg.setInformativeText(body)
            msg.setStandardButtons(QMessageBox.No)

            copy_btn = None
            if enlace:
                copy_btn = msg.addButton("Copiar enlace", QMessageBox.AcceptRole)

            msg.exec_()
            if copy_btn is not None and msg.clickedButton() == copy_btn:
                try:
                    QApplication.clipboard().setText(enlace)
                    QMessageBox.information(
                        self,
                        "Actualizacion",
                        "El enlace de descarga fue copiado al portapapeles."
                    )
                except Exception as e:
                    logger.warning("[UPDATE] No se pudo copiar enlace de actualizacion: %s", e)
                    QMessageBox.warning(
                        self,
                        "Actualizacion",
                        f"No se pudo copiar el enlace:\n{e}"
                    )
        except Exception as e:
            logger.warning("[UPDATE] No se pudo mostrar popup de actualizacion: %s", e)

    def _get_current_app_binary_path(self):
        try:
            if getattr(sys, "frozen", False):
                return os.path.abspath(sys.executable)
            return os.path.abspath(sys.argv[0])
        except Exception:
            return os.path.abspath(sys.argv[0])

    def _can_self_update_current_runtime(self):
        target_file_path = self._get_current_app_binary_path()
        is_frozen = bool(getattr(sys, "frozen", False))
        is_exe = str(target_file_path or "").lower().endswith(".exe")
        return is_frozen and is_exe

    def _parse_update_manifest_text(self, raw_text):
        text = str(raw_text or "").lstrip("\ufeff").strip()
        if not text:
            raise ValueError("Respuesta vacia en v.json")

        try:
            data = json.loads(text)
        except Exception:
            data = {}
            body = text.strip().strip("{}").strip()
            for raw_line in body.splitlines():
                line = raw_line.strip().rstrip(",")
                if not line or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = str(key or "").strip().strip("\"' ")
                value = str(value or "").strip().rstrip(",").strip()
                if not key:
                    continue
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                data[key] = value

        if not isinstance(data, dict):
            raise ValueError("v.json no es un objeto JSON")
        return data

    def _build_update_helper_bat(self, downloaded_file_path, target_file_path):
        app_dir = os.path.dirname(target_file_path)
        helper_path = os.path.join(app_dir, "Actualizacion VISO.bat")
        current_pid = os.getpid()
        downloaded_norm = os.path.normpath(downloaded_file_path)
        target_norm = os.path.normpath(target_file_path)
        helper_lines = [
            "@echo off",
            "setlocal enableextensions",
            f"set \"SOURCE_FILE={downloaded_norm}\"",
            f"set \"TARGET_FILE={target_norm}\"",
            f"set \"TARGET_PID={current_pid}\"",
            "",
            ":waitclose",
            "tasklist /FI \"PID eq %TARGET_PID%\" | find \"%TARGET_PID%\" >nul",
            "if not errorlevel 1 (",
            "    timeout /t 1 /nobreak >nul",
            "    goto waitclose",
            ")",
            "",
            ":deleteold",
            "if exist \"%TARGET_FILE%\" (",
            "    del /F /Q \"%TARGET_FILE%\" >nul 2>&1",
            "    timeout /t 1 /nobreak >nul",
            "    goto deleteold",
            ")",
            "",
            "copy /Y \"%SOURCE_FILE%\" \"%TARGET_FILE%\" >nul",
            "if exist \"%TARGET_FILE%\" (",
            "    start \"\" \"%TARGET_FILE%\"",
            ")",
            "exit /b 0",
        ]
        with open(helper_path, "w", encoding="utf-8", newline="\r\n") as bat_file:
            bat_file.write("\r\n".join(helper_lines) + "\r\n")
        return helper_path

    def _download_update_file(self, download_url, remote_version):
        import requests
        from urllib.parse import urlparse

        parsed = urlparse(download_url)
        file_name = os.path.basename(parsed.path or "").strip()
        if not file_name:
            clean_version = str(remote_version or "nuevo").replace(" ", "_")
            file_name = f"viso_update_{clean_version}.bin"

        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_dir, exist_ok=True)

        destination_path = os.path.join(downloads_dir, file_name)
        base_name, ext = os.path.splitext(file_name)
        counter = 1
        while os.path.exists(destination_path):
            suffix = ext or ".bin"
            destination_path = os.path.join(downloads_dir, f"{base_name}_{counter}{suffix}")
            counter += 1

        response = requests.get(download_url, timeout=30, stream=True)
        response.raise_for_status()
        with open(destination_path, "wb") as downloaded_file:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    downloaded_file.write(chunk)
        return destination_path

    def _validate_downloaded_executable(self, downloaded_file_path):
        if not os.path.exists(downloaded_file_path):
            raise ValueError("La descarga no existe.")
        file_size = os.path.getsize(downloaded_file_path)
        if file_size <= 0:
            raise ValueError("La descarga llego vacia.")
        with open(downloaded_file_path, "rb") as downloaded_file:
            signature = downloaded_file.read(2)
        if signature != b"MZ":
            raise ValueError(
                "El archivo descargado no es un ejecutable Windows valido.\n"
                "Se bloqueo el reemplazo para proteger VISO."
            )

    def _start_external_update_flow(self, download_url, remote_version):
        if not download_url:
            raise ValueError("El servidor no envio el enlace de descarga.")

        if not self._can_self_update_current_runtime():
            raise ValueError(
                "La actualizacion automatica esta bloqueada en modo desarrollo.\n"
                "Solo se permite cuando VISO esta ejecutandose como archivo .exe."
            )

        target_file_path = self._get_current_app_binary_path()
        if not os.path.exists(target_file_path):
            raise ValueError(f"No se encontro el archivo actual de VISO:\n{target_file_path}")

        wait_msg = QMessageBox(self)
        wait_msg.setIcon(QMessageBox.Information)
        wait_msg.setWindowTitle("Actualizacion")
        wait_msg.setText("Descargando actualizacion...")
        wait_msg.setInformativeText("Espera un momento. Cuando termine, VISO se cerrara para reemplazarse.")
        wait_msg.setStandardButtons(QMessageBox.NoButton)
        wait_msg.show()
        QApplication.processEvents()

        try:
            downloaded_file_path = self._download_update_file(download_url, remote_version)
            self._validate_downloaded_executable(downloaded_file_path)
            helper_bat_path = self._build_update_helper_bat(downloaded_file_path, target_file_path)
        finally:
            wait_msg.close()

        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Information)
        confirm.setWindowTitle("Actualizacion lista")
        confirm.setText("La actualizacion ya se descargo.")
        confirm.setInformativeText(
            "VISO se cerrara ahora para ejecutar 'Actualizacion VISO.bat' y reemplazar el archivo actual."
        )
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setDefaultButton(QMessageBox.Yes)
        if confirm.exec_() != QMessageBox.Yes:
            return

        subprocess.Popen(
            ["cmd.exe", "/c", "start", "", helper_bat_path],
            cwd=os.path.dirname(helper_bat_path) or None,
        )
        QtCore.QTimer.singleShot(200, self.close)

    def _check_update_on_startup(self):
        """Consulta v.json remoto y notifica si hay versiÃ³n mÃ¡s nueva."""
        import threading
        import time

        def check_remote_update():
            import requests

            last_error = None
            for attempt in range(1, 4):
                try:
                    response = requests.get(self.UPDATE_INFO_URL, timeout=8)
                    response.raise_for_status()

                    raw_text = str(response.text or "").lstrip("\ufeff").strip()
                    if not raw_text:
                        raise ValueError("Respuesta vacÃ­a en v.json")

                    data = self._parse_update_manifest_text(raw_text)

                    remote_version = str(
                        data.get("V")
                        or data.get("v")
                        or data.get("version")
                        or data.get("latest_version")
                        or data.get("app_version")
                        or ""
                    ).strip()
                    if not remote_version:
                        raise ValueError("v.json no incluye 'version'")
                    if not self._is_remote_version_mismatch(remote_version):
                        logger.info("[UPDATE] Version coincide. Local=%s Remoto=%s", APP_VERSION, remote_version)
                        return

                    download_url = str(
                        data.get("enlace")
                        or data.get("download_url")
                        or data.get("exe_url")
                        or data.get("url")
                        or data.get("link")
                        or ""
                    ).strip()
                    notes = str(
                        data.get("notes")
                        or data.get("message")
                        or data.get("mensaje")
                        or data.get("changelog")
                        or ""
                    ).strip()

                    notif = {
                        "id": f"update:{remote_version}",
                        "titulo": "(1) Actualizacion disponible",
                        "mensaje": notes or f"Version actual: {APP_VERSION}\nVersion nueva: {remote_version}\n\nSe copiara el enlace de descarga para actualizar manualmente.",
                        "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "enlace": download_url,
                        "version_remota": remote_version,
                    }
                    self.update_notification_ready.emit(notif)
                    self.update_popup_ready.emit(notif)
                    logger.info("[UPDATE] NotificaciÃ³n de actualizaciÃ³n enviada: %s", remote_version)
                    return
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "[UPDATE] Intento %s/3 fallÃ³ consultando v.json: %s",
                        attempt, e
                    )
                    if attempt < 3:
                        time.sleep(3 * attempt)

            logger.warning("[UPDATE] No se pudo verificar actualizaciÃ³n tras 3 intentos: %s", last_error)

        threading.Thread(target=check_remote_update, daemon=True).start()

    def _infer_last_device_event_epoch(self):
        popup = getattr(self, "notifications_popup", None)
        if popup is None:
            return 0
        max_epoch = 0
        try:
            for notif in list(getattr(popup, "all_notifications", []) or []):
                if not isinstance(notif, dict):
                    continue
                notif_id = str(notif.get("id", "")).strip()
                if not notif_id.startswith("dev_evt:"):
                    continue
                epoch = int(notif.get("epoch", 0) or 0)
                if epoch > max_epoch:
                    max_epoch = epoch
        except Exception:
            return 0
        return max_epoch

    def _build_device_event_notification(self, event):
        if not isinstance(event, dict):
            return None

        event_type = str(event.get("type", "")).strip().lower()
        if event_type != "producto_creado":
            return None

        event_id = str(event.get("id", "")).strip()
        if event_id == "":
            return None

        codigo = str(event.get("codigo_dispositivo", "")).strip().upper()
        nombre_optica = str(event.get("nombre_optica", "")).strip() or "Sucursal"
        ciudad = str(event.get("ciudad", "")).strip()
        producto = str(event.get("producto_nombre", "")).strip() or "producto"
        created_at = str(event.get("created_at", "")).strip()
        if "T" in created_at:
            created_at = created_at.replace("T", " ")[:19]
        if not created_at:
            created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sucursal = nombre_optica
        if ciudad:
            sucursal = f"{nombre_optica} - {ciudad}"
        if codigo:
            sucursal = f"{sucursal} ({codigo})"

        return {
            "id": f"dev_evt:{event_id}",
            "titulo": "Producto creado en dispositivo hijo",
            "mensaje": f"Se creo '{producto}' en {sucursal}.",
            "fecha": created_at,
            "enlace": "",
            "epoch": int(event.get("epoch", 0) or 0),
        }

    def _build_branch_quota_payload(self):
        """
        Revisa si la cantidad de sucursales activas supera el limite del plan.
        Si hay sobrecupo, retorna payload para solicitar seleccion en UI.
        """
        try:
            from utils.api_handler import listar_dispositivos_hijos_remoto_con_limite

            ok, devices, max_sucursales, _msg = listar_dispositivos_hijos_remoto_con_limite(
                str(self.username or "").strip()
            )
            if not ok:
                return None

            try:
                max_limit = int(max_sucursales or 0)
            except Exception:
                max_limit = 0

            if max_limit <= 0:
                return None

            valid_devices = [d for d in (devices or []) if isinstance(d, dict)]
            active_devices = [
                d for d in valid_devices
                if str(d.get("estado", "activo")).strip().lower() != "bloqueado"
            ]

            if len(active_devices) <= max_limit:
                # Si ya no hay sobrecupo, permitir futuras alertas nuevas.
                self._branch_quota_last_signature = ""
                self._branch_quota_last_prompt_ts = 0.0
                return None

            overflow = len(active_devices) - max_limit
            sig_parts = []
            for d in active_devices:
                did = str(d.get("id", "")).strip()
                code = str(d.get("codigo_dispositivo", "")).strip().upper()
                sig_parts.append(f"{did}|{code}")
            signature = f"{max_limit}|{'#'.join(sorted(sig_parts))}"

            last_sig = str(self._branch_quota_last_signature or "").strip()
            last_ts = float(getattr(self, "_branch_quota_last_prompt_ts", 0.0) or 0.0)
            if signature == last_sig and (time.time() - last_ts) < 300.0:
                return None

            return {
                "signature": signature,
                "max_sucursales": max_limit,
                "overflow": overflow,
                "devices": active_devices,
            }
        except Exception as e:
            logger.debug("[BRANCH_QUOTA] No se pudo evaluar sobrecupo: %s", e)
            return None

    def _show_branch_quota_qml_modal(self, payload):
        """Muestra modal QML para que el usuario elija que sucursal desactivar."""
        if not isinstance(payload, dict):
            return
        if self._branch_quota_prompt_open:
            return

        devices = payload.get("devices") if isinstance(payload.get("devices"), list) else []
        if not devices:
            return

        signature = str(payload.get("signature", "")).strip()
        self._branch_quota_prompt_open = True

        try:
            from gui.dialogs.branch_quota_qml_dialog import BranchQuotaQmlDialog

            dialog = BranchQuotaQmlDialog(
                devices=devices,
                overflow=int(payload.get("overflow", 1) or 1),
                max_sucursales=int(payload.get("max_sucursales", 0) or 0),
                parent=self,
            )
            chosen = None
            if dialog.exec_() == QDialog.Accepted:
                chosen = dialog.get_selected_device()

            if not isinstance(chosen, dict):
                # Si cancela, recordar firma para no insistir en cada ciclo.
                self._branch_quota_last_signature = signature
                self._branch_quota_last_prompt_ts = time.time()
                return

            from utils.api_handler import sync_dispositivo_hijo_remoto

            updated = dict(chosen)
            updated["estado"] = "bloqueado"
            updated["updated_at"] = datetime.datetime.now().isoformat()
            ok, msg, _remote = sync_dispositivo_hijo_remoto(str(self.username or "").strip(), updated)

            if not ok:
                QMessageBox.warning(
                    self,
                    "No se pudo desactivar sucursal",
                    f"No se pudo aplicar el cambio en nube.\nDetalle: {msg}"
                )
                # Permitir reintentar en el proximo ciclo.
                self._branch_quota_last_signature = signature
                self._branch_quota_last_prompt_ts = time.time()
                return

            code = str(chosen.get("codigo_dispositivo", "")).strip().upper()
            if code and code == str(self.selected_branch_code or "").strip().upper():
                try:
                    from utils.file_handler import clear_active_branch_context, clear_branch_runtime_caches
                    clear_active_branch_context(self.username)
                    clear_branch_runtime_caches()
                except Exception:
                    pass
                default_label = "Sucursal unica" if str(self._get_madre_label()).lower().endswith("unico") else "Todas las sucursales"
                self.on_branch_context_changed("", default_label)

            try:
                home_page = getattr(self, "home_page", None)
                home_widget = getattr(home_page, "home_widget", None)
                if home_widget is not None and hasattr(home_widget, "_reload_branch_selector"):
                    home_widget._reload_branch_selector(fetch_remote=True)
            except Exception:
                pass

            self.on_device_role_changed("madre")
            self._branch_quota_last_signature = ""
            self._branch_quota_last_prompt_ts = 0.0
            QMessageBox.information(
                self,
                "Sucursal desactivada",
                "La sucursal seleccionada fue desactivada para cumplir el nuevo limite."
            )
        except Exception as e:
            logger.warning("[BRANCH_QUOTA] Error mostrando modal QML: %s", e)
            # No bloquear futuras alertas si falla el modal.
            self._branch_quota_last_signature = signature
            self._branch_quota_last_prompt_ts = time.time()
        finally:
            self._branch_quota_prompt_open = False

    def _build_branch_recovery_payload(self):
        """
        Si el plan tiene cupos disponibles y existen sucursales bloqueadas,
        retorna payload para permitir al usuario recuperar una o crear nueva.
        """
        try:
            from utils.api_handler import listar_dispositivos_hijos_remoto_con_limite

            ok, devices, max_sucursales, _msg = listar_dispositivos_hijos_remoto_con_limite(
                str(self.username or "").strip()
            )
            if not ok:
                return None

            try:
                max_limit = int(max_sucursales or 0)
            except Exception:
                max_limit = 0
            if max_limit <= 0:
                return None

            valid_devices = [d for d in (devices or []) if isinstance(d, dict)]
            active_devices = [
                d for d in valid_devices
                if str(d.get("estado", "activo")).strip().lower() != "bloqueado"
            ]
            blocked_devices = [
                d for d in valid_devices
                if str(d.get("estado", "")).strip().lower() == "bloqueado"
            ]

            free_slots = max_limit - len(active_devices)
            if free_slots <= 0 or not blocked_devices:
                # Si ya no aplica, permitir futuras alertas nuevas.
                self._branch_recovery_last_signature = ""
                self._branch_recovery_last_prompt_ts = 0.0
                return None

            sig_parts = []
            for d in blocked_devices:
                did = str(d.get("id", "")).strip()
                code = str(d.get("codigo_dispositivo", "")).strip().upper()
                sig_parts.append(f"{did}|{code}")
            signature = f"{max_limit}|{free_slots}|{'#'.join(sorted(sig_parts))}"

            last_sig = str(self._branch_recovery_last_signature or "").strip()
            last_ts = float(getattr(self, "_branch_recovery_last_prompt_ts", 0.0) or 0.0)
            if signature == last_sig and (time.time() - last_ts) < 300.0:
                return None

            return {
                "signature": signature,
                "max_sucursales": max_limit,
                "free_slots": int(free_slots),
                "active_count": len(active_devices),
                "blocked_devices": blocked_devices,
            }
        except Exception as e:
            logger.debug("[BRANCH_RECOVERY] No se pudo evaluar recuperacion: %s", e)
            return None

    def _show_branch_recovery_qml_modal(self, payload):
        """Modal QML para recuperar una sucursal bloqueada o crear una nueva."""
        if not isinstance(payload, dict):
            return
        if self._branch_recovery_prompt_open:
            return

        blocked = payload.get("blocked_devices") if isinstance(payload.get("blocked_devices"), list) else []
        if not blocked:
            return

        signature = str(payload.get("signature", "")).strip()
        self._branch_recovery_prompt_open = True

        try:
            from gui.dialogs.branch_recovery_qml_dialog import BranchRecoveryQmlDialog
            dialog = BranchRecoveryQmlDialog(
                blocked_devices=blocked,
                free_slots=int(payload.get("free_slots", 0) or 0),
                max_sucursales=int(payload.get("max_sucursales", 0) or 0),
                active_count=int(payload.get("active_count", 0) or 0),
                parent=self,
            )

            result = {}
            if dialog.exec_() == QDialog.Accepted:
                result = dialog.get_result() or {}

            action = str((result or {}).get("action", "") or "").strip()
            if action == "create_new":
                # Llevar a Configuracion para crear una nueva sucursal/dispositivo.
                self._branch_recovery_last_signature = signature
                self._branch_recovery_last_prompt_ts = time.time()
                try:
                    self.mostrar_frame(10)
                except Exception:
                    pass
                try:
                    QMessageBox.information(
                        self,
                        "Crear nueva sucursal",
                        "Ve a Configuracion > Dispositivos hijos para crear una nueva sucursal."
                    )
                except Exception:
                    pass
                return

            if action != "recover":
                self._branch_recovery_last_signature = signature
                self._branch_recovery_last_prompt_ts = time.time()
                return

            chosen = (result or {}).get("device")
            if not isinstance(chosen, dict):
                self._branch_recovery_last_signature = signature
                self._branch_recovery_last_prompt_ts = time.time()
                return

            from utils.api_handler import sync_dispositivo_hijo_remoto
            updated = dict(chosen)
            updated["estado"] = "activo"
            updated["updated_at"] = datetime.datetime.now().isoformat()
            ok, msg, _remote = sync_dispositivo_hijo_remoto(str(self.username or "").strip(), updated)
            if not ok:
                QMessageBox.warning(
                    self,
                    "No se pudo recuperar sucursal",
                    f"No se pudo aplicar el cambio en nube.\nDetalle: {msg}"
                )
                self._branch_recovery_last_signature = signature
                self._branch_recovery_last_prompt_ts = time.time()
                return

            try:
                home_page = getattr(self, "home_page", None)
                home_widget = getattr(home_page, "home_widget", None)
                if home_widget is not None and hasattr(home_widget, "_reload_branch_selector"):
                    home_widget._reload_branch_selector(fetch_remote=True)
            except Exception:
                pass

            self._branch_recovery_last_signature = ""
            self._branch_recovery_last_prompt_ts = 0.0
            QMessageBox.information(
                self,
                "Sucursal recuperada",
                "La sucursal seleccionada fue activada nuevamente."
            )
        except Exception as e:
            logger.warning("[BRANCH_RECOVERY] Error mostrando modal QML: %s", e)
            self._branch_recovery_last_signature = signature
            self._branch_recovery_last_prompt_ts = time.time()
        finally:
            self._branch_recovery_prompt_open = False

    def _start_device_event_polling(self):
        if not self.es_dispositivo_madre():
            return
        if not str(self.username or "").strip():
            return
        if self._device_events_timer is not None:
            return

        self._device_events_last_epoch = max(
            int(self._device_events_last_epoch or 0),
            int(self._infer_last_device_event_epoch() or 0)
        )
        # Si por alguna razÃ³n quedÃ³ un epoch futuro/corrupto, resetear para no perder eventos.
        now_epoch = int(time.time())
        if int(self._device_events_last_epoch or 0) > (now_epoch + 86400):
            logger.warning(
                "[DEVICE_EVENTS] epoch local invalido (%s), reseteando a 0",
                self._device_events_last_epoch
            )
            self._device_events_last_epoch = 0

        self._device_events_bootstrap_done = False

        self._poll_device_events_once()
        self._device_events_timer = QtCore.QTimer(self)
        self._device_events_timer.setInterval(int(self.DEVICE_EVENTS_POLL_MS))
        self._device_events_timer.timeout.connect(self._poll_device_events_once)
        self._device_events_timer.start()

    def _load_branch_product_state(self):
        if self._branch_product_state_loaded:
            return
        self._branch_product_state_loaded = True
        self._branch_product_state = {}
        try:
            path = str(self._branch_product_state_path or "")
            if not path or not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            branches = payload.get("branches") if isinstance(payload, dict) else {}
            if not isinstance(branches, dict):
                return
            for code, keys in branches.items():
                c = str(code or "").strip().upper()
                if not c or not isinstance(keys, list):
                    continue
                self._branch_product_state[c] = set(str(k or "").strip() for k in keys if str(k or "").strip())
        except Exception:
            self._branch_product_state = {}

    def _save_branch_product_state(self):
        try:
            path = str(self._branch_product_state_path or "")
            if not path:
                return
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            serial = {
                "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "branches": {
                    code: sorted(list(keys))
                    for code, keys in (self._branch_product_state or {}).items()
                    if code
                }
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(serial, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _extract_product_identity(self, product):
        if not isinstance(product, dict):
            return "", ""
        pid = ""
        for key in (
            "id",
            "codigo",
            "codigo_producto",
            "sku",
            "barcode",
            "id_producto",
            "product_code",
            "nombre",
        ):
            val = str(product.get(key, "")).strip()
            if val:
                pid = f"{key}:{val.lower()}"
                break
        name = str(
            product.get("nombre")
            or product.get("name")
            or product.get("nombre_producto")
            or product.get("codigo")
            or product.get("codigo_producto")
            or "producto"
        ).strip()
        if not name:
            name = "producto"
        return pid, name

    def _extract_products_from_snapshot_payload(self, payload):
        """
        Normaliza diferentes formatos de respuesta de download_device_snapshot.php
        y retorna una lista de productos.
        """
        if not isinstance(payload, dict):
            return []

        def _as_product_list(value):
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                # Formatos esperados: {"data":[...]} o {"items":[...]}
                for key in ("data", "items", "rows", "registros"):
                    inner = value.get(key)
                    if isinstance(inner, list):
                        return [item for item in inner if isinstance(item, dict)]
                # Caso mapa {id: {...}}
                values = [v for v in value.values() if isinstance(v, dict)]
                if values:
                    return values
            return []

        # Formato dataset unico: {"dataset":"productos","data":[...]}
        ds_name = str(payload.get("dataset", "")).strip().lower()
        if ds_name == "productos":
            products = _as_product_list(payload.get("data"))
            if products:
                return products

        # Formato snapshot completo: {"snapshot":{"productos":[...]}}
        snapshot = payload.get("snapshot")
        if isinstance(snapshot, dict):
            products = _as_product_list(snapshot.get("productos"))
            if products:
                return products

        # Fallback por claves comunes
        for key in ("productos", "data", "items", "rows", "registros"):
            products = _as_product_list(payload.get(key))
            if products:
                return products

        return []

    def _poll_device_product_creations_fallback(self):
        """
        Fallback cuando list_device_events.php no estÃ¡ desplegado.
        Detecta productos nuevos comparando snapshot remoto por sucursal.
        """
        try:
            from utils.api_handler import (
                listar_dispositivos_hijos_remoto,
                descargar_snapshot_dispositivo_nube,
                obtener_productos_remoto,
            )
        except Exception:
            return

        self._load_branch_product_state()

        ok, devices, msg = listar_dispositivos_hijos_remoto(str(self.username or "").strip())
        if not ok:
            logger.debug("[DEVICE_EVENTS][FALLBACK] %s", msg)
            return

        changed = False
        active_codes = set()

        for device in (devices or []):
            if not isinstance(device, dict):
                continue
            estado = str(device.get("estado", "activo")).strip().lower()
            if estado == "bloqueado":
                continue

            code = str(device.get("codigo_dispositivo", "")).strip().upper()
            if not code:
                continue
            active_codes.add(code)

            name = str(device.get("nombre_optica", "Sucursal")).strip() or "Sucursal"
            city = str(device.get("ciudad", "")).strip()
            label = f"{name} - {city}" if city else name

            productos = []
            ok_snap, payload_snap, msg_snap = descargar_snapshot_dispositivo_nube(
                usuario_madre=str(self.username or "").strip(),
                codigo_dispositivo=code,
                dataset="productos",
                include_data=True,
            )
            if ok_snap:
                productos = self._extract_products_from_snapshot_payload(payload_snap)
            else:
                logger.debug(
                    "[DEVICE_EVENTS][FALLBACK] snapshot productos fallo %s: %s",
                    code,
                    msg_snap,
                )
                # Compatibilidad legacy si el endpoint nuevo falla.
                productos = obtener_productos_remoto(
                    str(self.username or "").strip(),
                    codigo_dispositivo=code
                ) or []

            current_map = {}
            for prod in productos:
                pid, pname = self._extract_product_identity(prod)
                if pid:
                    current_map[pid] = pname

            current_keys = set(current_map.keys())
            prev_keys = self._branch_product_state.get(code, None)

            if prev_keys is None:
                self._branch_product_state[code] = current_keys
                changed = True
                continue

            new_keys = [k for k in sorted(current_keys - prev_keys)]
            if new_keys:
                now_txt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                now_epoch = int(time.time())
                for k in new_keys[:8]:
                    pname = current_map.get(k, "producto")
                    notif = {
                        "id": f"prod_create:{code}:{k}",
                        "titulo": "Producto creado en dispositivo hijo",
                        "mensaje": f"Se creo '{pname}' en {label} ({code}).",
                        "fecha": now_txt,
                        "enlace": "",
                        "epoch": now_epoch,
                    }
                    self.update_notification_ready.emit(notif)
                    logger.info(
                        "[DEVICE_EVENTS][FALLBACK] Nuevo producto detectado en %s: %s",
                        code,
                        pname,
                    )

            if current_keys != prev_keys:
                self._branch_product_state[code] = current_keys
                changed = True

        # Limpiar sucursales eliminadas del estado
        existing_codes = set(self._branch_product_state.keys())
        for old_code in list(existing_codes - active_codes):
            self._branch_product_state.pop(old_code, None)
            changed = True

        if changed:
            self._save_branch_product_state()

    def _stop_device_event_polling(self):
        try:
            if self._device_events_timer is not None:
                self._device_events_timer.stop()
                self._device_events_timer.deleteLater()
        except Exception:
            pass
        self._device_events_timer = None
        self._device_events_fetching = False
        self._device_events_bootstrap_done = False

    def _should_run_device_events_fallback(self, force=False):
        now_ts = float(time.time())
        last_ts = float(getattr(self, "_device_events_last_fallback_ts", 0.0) or 0.0)
        min_interval = 45.0 if force else float(self.DEVICE_EVENTS_FALLBACK_MIN_INTERVAL_SEC)
        if last_ts > 0 and (now_ts - last_ts) < min_interval:
            return False
        self._device_events_last_fallback_ts = now_ts
        return True

    def _poll_device_events_once(self):
        if not self.es_dispositivo_madre():
            return
        if self._device_events_fetching:
            return

        self._device_events_fetching = True
        import threading

        def worker():
            try:
                from utils.api_handler import listar_eventos_dispositivos_nube

                should_run_fallback = False
                since_epoch = int(self._device_events_last_epoch or 0)
                # Primera pasada: traer histÃ³rico reciente sin depender de since_epoch local.
                if not self._device_events_bootstrap_done:
                    since_epoch = 0

                ok, events, msg = listar_eventos_dispositivos_nube(
                    usuario_madre=str(self.username or "").strip(),
                    since_epoch=since_epoch,
                    limit=60,
                    # Filtramos por tipo en cliente para no depender del nombre exacto del parÃ¡metro PHP.
                    event_type=None,
                )
                if not ok:
                    msg_txt = str(msg or "")
                    if "404" in msg_txt or "Not Found" in msg_txt:
                        self._device_events_endpoint_available = False
                    logger.debug("[DEVICE_EVENTS] %s", msg_txt)
                    should_run_fallback = True
                else:
                    self._device_events_endpoint_available = True
                    self._device_events_bootstrap_done = True
                    max_epoch = int(self._device_events_last_epoch or 0)
                    ordered = list(events or [])
                    ordered.reverse()  # oldest -> newest (add_notification_new inserta al inicio)
                    emitted = 0
                    for event in ordered:
                        notif = self._build_device_event_notification(event)
                        if notif:
                            self.update_notification_ready.emit(notif)
                            emitted += 1
                        try:
                            epoch = int((event or {}).get("epoch", 0) or 0)
                            if epoch > max_epoch:
                                max_epoch = epoch
                        except Exception:
                            pass
                    self._device_events_last_epoch = max_epoch
                    logger.info(
                        "[DEVICE_EVENTS] recibidos=%s emitidos=%s since=%s last_epoch=%s",
                        len(ordered),
                        emitted,
                        since_epoch,
                        self._device_events_last_epoch,
                    )
                    # Si el endpoint existe pero no trae eventos, usar detector por snapshot.
                    if len(ordered) == 0:
                        should_run_fallback = True

                # Fallback por snapshot cuando el endpoint falle o lleve tiempo sin eventos.
                fallback_force = not self._device_events_endpoint_available
                should_run_snapshot_fallback = bool(should_run_fallback or fallback_force)
                if should_run_snapshot_fallback and self._should_run_device_events_fallback(force=fallback_force):
                    self._poll_device_product_creations_fallback()

                # Revisar sobrecupo de sucursales cada cierto tiempo.
                try:
                    now_ts = float(time.time())
                    last_ts = float(getattr(self, "_branch_quota_last_check_ts", 0.0) or 0.0)
                    if (now_ts - last_ts) >= 45.0:
                        self._branch_quota_last_check_ts = now_ts
                        quota_payload = self._build_branch_quota_payload()
                        if isinstance(quota_payload, dict):
                            self.branch_quota_selection_needed.emit(quota_payload)
                        else:
                            recovery_payload = self._build_branch_recovery_payload()
                            if isinstance(recovery_payload, dict):
                                self.branch_recovery_selection_needed.emit(recovery_payload)
                except Exception as e:
                    logger.debug("[BRANCH_QUOTA] Error en check periodico: %s", e)
            except Exception as e:
                logger.debug("[DEVICE_EVENTS] error: %s", e)
            finally:
                self._device_events_fetching = False

        threading.Thread(target=worker, daemon=True).start()
    
    def _verify_license_on_startup(self):
        """Verifica la licencia en un thread separado al inicio de la app."""
        import threading
        from utils.api_handler import verificar_estado_licencia
        from utils.license_manager import save_license_info
        
        def check_license():
            """Verifica licencia sin bloquear UI."""
            try:
                success, license_data = verificar_estado_licencia(
                    username=self.username,
                    id_usuario=self.user_id
                )
                
                if success and license_data:
                    # âœ… ACTUALIZAR LICENCIA LOCAL SIEMPRE (sea vigente o expirada)
                    # Esto asegura que el archivo local refleja el estado actual del servidor
                    save_license_info(
                        user_id=self.user_id,
                        username=self.username,
                        plan_type=license_data.get('plan_type', 'Desconocido'),
                        fecha_vencimiento=license_data.get('fecha_vencimiento', ''),
                        dias_restantes=license_data.get('dias_restantes', 0)
                    )
                    
                    # Si licencia estÃ¡ expirada, bloquear app INMEDIATAMENTE
                    if not license_data.get('licencia_vigente', False):
                        # Usar signal para llamar desde thread de forma segura
                        self.license_expired.emit(license_data)
                        return
                    
                    # Si no tiene licencia, bloquear app
                    if not license_data.get('tiene_licencia', False):
                        self.no_license.emit()
                        return
            except Exception as e:
                print(f"[APP] ERROR verificando licencia en startup: {e}")
                import traceback
                traceback.print_exc()
        
        # Ejecutar en thread separado (daemon=True para que no bloquee cierre de app)
        license_thread = threading.Thread(target=check_license, daemon=True)
        license_thread.start()
    
    def _force_close_expired(self, license_data):
        """Fuerza el cierre de la app por licencia expirada - BLOQUEANTE."""
        from gui.suspension_dialog import SuspensionDialog
        
        try:
            # Deshabilitar toda la UI primero
            self.setEnabled(False)
            
            dialog = SuspensionDialog(
                parent=self,
                reason='expired',
                dias_restantes=abs(license_data.get('dias_restantes', 0)),
                vigencia=license_data.get('fecha_vencimiento', 'Desconocida')
            )
            
            # Modal + bloqueante
            dialog.setWindowModality(QtCore.Qt.ApplicationModal)
            dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            
            result = dialog.exec_()
        except Exception as e:
            print(f"[APP] ERROR en diÃ¡logo de licencia expirada: {e}")
            import traceback
            traceback.print_exc()
        
        # DespuÃ©s de cerrar el diÃ¡logo, CIERRA LA APP FORZADAMENTE
        QtCore.QCoreApplication.quit()
    
    def _force_close_no_license(self):
        """Fuerza el cierre de la app por falta de licencia - BLOQUEANTE."""
        from gui.suspension_dialog import SuspensionDialog
        
        try:
            # Deshabilitar toda la UI primero
            self.setEnabled(False)
            
            dialog = SuspensionDialog(
                parent=self,
                reason='no_activation',
                dias_restantes=0,
                vigencia='No tiene'
            )
            
            # Modal + bloqueante
            dialog.setWindowModality(QtCore.Qt.ApplicationModal)
            dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            
            result = dialog.exec_()
        except Exception as e:
            print(f"[APP] ERROR en diÃ¡logo de sin licencia: {e}")
            import traceback
            traceback.print_exc()
        
        # DespuÃ©s de cerrar el diÃ¡logo, CIERRA LA APP FORZADAMENTE
        QtCore.QCoreApplication.quit()
    
    def setup_zoom_shortcuts(self):
        """Configura los atajos de teclado para zoom (Ctrl++ y Ctrl+-)"""
        # Atajo para aumentar zoom: Ctrl++
        zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in_shortcut.activated.connect(self.increase_zoom)
        
        # Atajo para aumentar zoom: Ctrl+=
        zoom_in_shortcut2 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in_shortcut2.activated.connect(self.increase_zoom)
        
        # Atajo para disminuir zoom: Ctrl+-
        zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out_shortcut.activated.connect(self.decrease_zoom)
        
        # Atajo para resetear zoom: Ctrl+0
        zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_reset_shortcut.activated.connect(self.reset_zoom)

    def setup_navigation_shortcuts(self):
        """Configura atajos globales de navegacion para paginas clave."""
        self.navigation_shortcuts = []
        shortcut_specs = (
            ("Ctrl+A", self._handle_home_shortcut),
            ("Ctrl+I", lambda: self.mostrar_frame(3)),
            ("Ctrl+P", lambda: self.mostrar_frame(1)),
        )

        for sequence, handler in shortcut_specs:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.WindowShortcut)
            shortcut.activated.connect(handler)
            self.navigation_shortcuts.append(shortcut)

    def _focus_widget_is_text_editable(self):
        """Devuelve True si el foco actual esta en un campo editable de texto."""
        widget = QApplication.focusWidget()
        if widget is None:
            return False

        editable_types = (
            QtWidgets.QLineEdit,
            QtWidgets.QTextEdit,
            QtWidgets.QPlainTextEdit,
            QtWidgets.QAbstractSpinBox,
        )
        if isinstance(widget, editable_types):
            return True

        return isinstance(widget, QtWidgets.QComboBox) and widget.isEditable()

    def _handle_home_shortcut(self):
        """
        Ctrl+A abre Inicio salvo cuando el foco esta en un input editable,
        donde se conserva el comportamiento natural de seleccionar todo.
        """
        focus_widget = QApplication.focusWidget()
        if self._focus_widget_is_text_editable():
            select_all = getattr(focus_widget, "selectAll", None)
            if callable(select_all):
                try:
                    select_all()
                    return
                except Exception:
                    pass

        self.go_to_home()
    
    def mostrar_paciente(self, paciente):
        """Muestra los detalles de un paciente."""
        try:
            # Ir a la pÃ¡gina de pacientes y mostrar el detalle
            self.mostrar_frame(1)  # PÃ¡gina de pacientes
            if hasattr(self, 'patients_page') and hasattr(self.patients_page, 'abrir_detalles_paciente'):
                self.patients_page.abrir_detalles_paciente(paciente.get('dni', ''))
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                f"No se pudo mostrar el paciente: {str(e)}"
            )

    def mostrar_producto(self, producto):
        """Muestra los detalles de un producto."""
        try:
            # Ir a la pÃ¡gina de inventario y mostrar el producto
            self.mostrar_frame(3)  # PÃ¡gina de inventario
            if hasattr(self, 'inventory_page'):
                self.inventory_page.abrir_edicion_producto(producto)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                f"No se pudo mostrar el producto: {str(e)}"
            )

    def _open_topbar_hamburger_menu(self):
        try:
            from gui.dialogs.topbar_hamburger_qml_dialog import TopbarHamburgerQmlDialog
            dialog = TopbarHamburgerQmlDialog(self)
            dialog.exec_()
        except Exception as e:
            try:
                QtWidgets.QMessageBox.warning(self, "Menu", f"No se pudo abrir el menu: {e}")
            except Exception:
                pass

    def _update_topbar_responsive(self):
        # Mostrar hamburger y ocultar elementos del top bar cuando no hay espacio.
        compact = False
        try:
            compact = self.width() < 1060
        except Exception:
            compact = False

        btn = getattr(self, "_topbar_hamburger_btn", None)
        main_buttons = getattr(self, "_topbar_main_buttons", None)
        badge = getattr(self, "_topbar_branch_badge", None)
        search_container = getattr(self, "_topbar_search_container", None)
        tools_frame = getattr(self, "_topbar_tools_frame", None)
        right_controls = getattr(self, "_topbar_right_controls", None)

        if btn is not None:
            btn.setVisible(compact)
        if main_buttons is not None:
            main_buttons.setVisible(not compact)
        if badge is not None:
            badge.setVisible(not compact)
        if search_container is not None:
            search_container.setVisible(not compact)
        if tools_frame is not None:
            tools_frame.setVisible(not compact)
        if right_controls is not None:
            right_controls.setVisible(not compact)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self._update_topbar_responsive()
        except Exception:
            pass

    def setup_toolbar(self, toolbar, toolbar_layout):
        """Configura la barra lateral de navegaciÃ³n con iconos."""
        # (Se removiÃ³ el botÃ³n de perfil por solicitud del usuario)
        
        # Mapeo de botones a mÃ³dulos para verificar permisos de ayudantes
        button_to_module_map = {
            0: 'home_page',  # Inicio (siempre visible)
            9: 'customers_page',  # Clientes
            1: 'patients_page',  # Pacientes
            3: 'inventory_page',  # Inventario
            6: 'appointments_page',  # Calendario
            2: 'create_patient_page',  # Nueva GraduaciÃ³n
            10: 'config_page',  # ConfiguraciÃ³n
        }
        
        # AÃ±adir botones de navegaciÃ³n usando iconos SVG en gui/icons/
        icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
        # Orden de botones: poner 'ConfiguraciÃ³n' al final para que sea el Ãºltimo icono
        self.nav_button_configs = [
            (os.path.join(icons_dir, 'home.svg'), lambda: self.mostrar_frame(0), 'Inicio', 0),
            (os.path.join(icons_dir, 'clients.svg'), lambda: self.mostrar_frame(9), 'Clientes', 9),
            (os.path.join(icons_dir, 'new_patient.svg'), lambda: self.mostrar_frame(1), 'Pacientes', 1),
            (os.path.join(icons_dir, 'inventory.svg'), lambda: self.mostrar_frame(3), 'Inventario', 3),
            (os.path.join(icons_dir, 'calendar.svg'), lambda: self.mostrar_frame(6), 'Calendario', 6),
            (os.path.join(icons_dir, 'add_patient.svg'), lambda: self.mostrar_frame(2), 'Nueva GraduaciÃ³n', 2),
            (os.path.join(icons_dir, 'config.svg'), lambda: self.mostrar_frame(10), 'ConfiguraciÃ³n', 10),
        ]

        from utils.file_handler import is_modo_basico
        if is_modo_basico(self.username):
            # En modo basico no se deben exponer accesos avanzados desde la barra lateral.
            allowed_pages = {0, 1, 2, 3, 6}
            self.nav_button_configs = [btn for btn in self.nav_button_configs if btn[3] in allowed_pages]

        self.nav_buttons = []  # Lista para mantener referencia a los botones
        for icon_path, callback, tooltip, page_index in self.nav_button_configs:
            if not self._has_device_access_to_page(page_index):
                continue

            # Verificar permisos si es ayudante
            if self.is_helper and page_index != 0:  # PÃ¡gina 0 (Inicio) siempre visible
                module_name = button_to_module_map.get(page_index)
                if module_name and module_name not in self.allowed_modules:
                    # Omitir este botÃ³n si no tiene permiso
                    continue
            
            btn = QPushButton()
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QtCore.QSize(32, 32))  # Iconos mÃ¡s grandes
            else:
                # Fallback: mostrar texto corto si no encuentra el SVG
                btn.setText(tooltip[0])
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 15px;
                    border: none;
                    border-radius: 18px;
                    background: transparent;
                    margin: 8px 0;
                }
                QPushButton:hover:!checked {
                    background: #EEF4FF;
                }
                QPushButton:pressed:!checked {
                    background: #DCE9FF;
                }
                QPushButton:checked {
                    background: #2157D5;
                }
                QPushButton:checked:hover {
                    background: #1B4BBB;
                }
            """)
            def _make_safe(cb, tip):
                def _wrapped():
                    try:
                        cb()
                    except Exception:
                        import traceback
                        traceback.print_exc()
                        logger.exception("Error navegando a %s", tip)
                        QMessageBox.critical(
                            self,
                            "Error",
                            f"OcurriÃ³ un error al abrir '{tip}'."
                        )
                return _wrapped

            btn.clicked.connect(_make_safe(callback, tooltip))
            btn.setFixedSize(56, 65)  # MÃ¡s alto manteniendo el mismo ancho
            toolbar_layout.addWidget(btn)
            self.nav_buttons.append((btn, page_index))  # Guardar referencia al botÃ³n y su pÃ¡gina
        
        # Espacio flexible
        toolbar_layout.addStretch()

        logout_btn = QPushButton()
        logout_icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'logout.svg')

        if os.path.exists(logout_icon_path):
            logout_btn.setIcon(QIcon(logout_icon_path))
            logout_btn.setIconSize(QtCore.QSize(28, 28))
        else:
            logout_btn.setText('Salir')
        logout_btn.setToolTip("Cerrar sesión")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                padding: 12px;
                border: none;
                border-radius: 14px;
                background: transparent;
                margin: 4px 0;
            }
            QPushButton:hover {
                background: #FFF1F2;
            }
            QPushButton:pressed {
                background: #FFE4E6;
            }
        """)
        def confirmar_cerrar_sesion():
            # Mostrar diálogo de confirmación antes de cerrar sesión
            resp = QMessageBox.question(
                self,
                "Confirmar cierre de sesión",
                "¿Estás seguro de querer cerrar sesión?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if resp == QMessageBox.Yes:
                try:
                    import os
                    import shutil
                    from utils.file_handler import SESION_FILE, VISO_DATA_DIR
                    
                    # Marcar como logout explícito para que closeEvent NO vuelva a guardar sesión
                    self._explicit_logout = True
                    
                    # Convertir a string para evitar issues con Path objects
                    sesion_file_path = str(SESION_FILE)
                    
                    # Borrar archivo de sesión (con manejo robusto)
                    if os.path.exists(sesion_file_path):
                        try:
                            os.remove(sesion_file_path)
                            print(f"[LOGOUT] OK Archivo de sesión borrado: {sesion_file_path}")
                        except Exception as e:
                            print(f"[LOGOUT] Error borrando sesión: {e}")
                            # Intentar forzado
                            try:
                                shutil.rmtree(os.path.dirname(sesion_file_path))
                                os.makedirs(os.path.dirname(sesion_file_path), exist_ok=True)
                            except:
                                pass
                    else:
                        print(f"[LOGOUT] Info: Archivo de sesión no existe: {sesion_file_path}")
                    
                    # Borrar caché de usuario actual (para forzar recarga)
                    try:
                        username_file = os.path.join(VISO_DATA_DIR, '.last_username')
                        if os.path.exists(username_file):
                            os.remove(username_file)
                    except:
                        pass
                    
                except Exception as e:
                    print(f"[LOGOUT] Error al cerrar sesión: {e}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.warning(self, "Error", f"Error al cerrar sesión: {e}")
                
                # Detener auto-sync antes de cerrar
                try:
                    from utils.sync_manager import get_sync_manager
                    sync_mgr = get_sync_manager()
                    sync_mgr.stop_auto_sync()
                except:
                    pass
                
                # Cerrar la ventana principal y mostrar login
                print(f"[LOGOUT] Cerrando sesiÃ³n y volviendo a login...")
                self.close()
                
                # Importar y mostrar LoginWindow
                try:
                    from gui.login_window import LoginWindow
                    login_window = LoginWindow()
                    login_window.show()
                except Exception as e:
                    print(f"[LOGOUT] Error mostrando login: {e}")
                    import traceback
                    traceback.print_exc()

        logout_btn.clicked.connect(confirmar_cerrar_sesion)
        logout_btn.setFixedSize(48, 48)
        toolbar_layout.addWidget(logout_btn)
    
    def open_birthdays_page(self):
        """Abre la pÃ¡gina de cumpleaÃ±os."""
        if not self.es_dispositivo_madre():
            QMessageBox.information(
                self,
                "Solo dispositivo madre",
                "Esta funciÃ³n estÃ¡ disponible Ãºnicamente para el dispositivo madre."
            )
            return

        from gui.main_window_pages.birthdays_page import BirthdaysPage
        if not hasattr(self, 'birthdays_page'):
            self.birthdays_page = BirthdaysPage(self)
            self.stacked_widget.addWidget(self.birthdays_page)
        index = self.stacked_widget.indexOf(self.birthdays_page)
        if index != -1:
            self.stacked_widget.setCurrentIndex(index)
            self.current_page = index
    
    def setup_pages(self):
        """Configura las pÃ¡ginas de la aplicaciÃ³n usando lazy loading."""
        # Inicializar el estado
        self.current_page = None
        
        # ðŸ”§ OPTIMIZACIÃ“N: Cargar home de forma asincrÃ³nica despuÃ©s de mostrar la ventana
        # Esto hace que el startup sea casi instantÃ¡neo
        # (Ya no lo hacemos aquÃ­ - se llama desde setup_main_window para mejor timing)

    def _get_available_geometry_for_rect(self, rect):
        """Obtiene el area disponible de la pantalla que contiene el rect."""
        screen = None
        try:
            screen = QtWidgets.QApplication.screenAt(rect.center())
        except Exception:
            screen = None

        if screen is None and self.windowHandle() is not None:
            screen = self.windowHandle().screen()

        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()

        return screen.availableGeometry() if screen else QtCore.QRect()

    def _frame_margins(self):
        """Calcula margenes del frame (borde del sistema) respecto al area cliente."""
        try:
            frame = self.frameGeometry()
            geom = self.geometry()
            return (
                geom.left() - frame.left(),
                geom.top() - frame.top(),
                frame.right() - geom.right(),
                frame.bottom() - geom.bottom(),
            )
        except Exception:
            return (0, 0, 0, 0)

    def _clamp_geometry_to_available(self, rect):
        """Ajusta el rect para que el frame no se salga del area disponible."""
        available = self._get_available_geometry_for_rect(rect)
        if available.isNull():
            return rect

        left_margin, top_margin, right_margin, bottom_margin = self._frame_margins()
        min_left = available.left() + left_margin
        min_top = available.top() + top_margin
        max_right = available.right() - right_margin
        max_bottom = available.bottom() - bottom_margin

        if max_right < min_left or max_bottom < min_top:
            return rect

        if rect.left() < min_left:
            rect.setLeft(min_left)
        if rect.top() < min_top:
            rect.setTop(min_top)
        if rect.right() > max_right:
            rect.setRight(max_right)
        if rect.bottom() > max_bottom:
            rect.setBottom(max_bottom)

        return rect

    # Eventos para permitir arrastrar la ventana desde Ã¡reas no interactivas
    # Funciona en conjunto con la barra de tÃ­tulo personalizada
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            try:
                # Detectar si estamos en un borde para redimensionar
                rect = self.rect()
                pos = event.pos()
                margin = 8
                
                self._resize_edge = None
                
                # Detectar quÃ© borde fue presionado
                if pos.y() < margin and pos.x() < margin:
                    self._resize_edge = "topleft"
                elif pos.y() < margin and pos.x() > rect.width() - margin:
                    self._resize_edge = "topright"
                elif pos.y() > rect.height() - margin and pos.x() < margin:
                    self._resize_edge = "bottomleft"
                elif pos.y() > rect.height() - margin and pos.x() > rect.width() - margin:
                    self._resize_edge = "bottomright"
                elif pos.y() < margin:
                    self._resize_edge = "top"
                elif pos.y() > rect.height() - margin:
                    self._resize_edge = "bottom"
                elif pos.x() < margin:
                    self._resize_edge = "left"
                elif pos.x() > rect.width() - margin:
                    self._resize_edge = "right"
                
                # Si estamos en un borde, iniciar redimensionamiento
                if self._resize_edge:
                    self._resize_start_pos = event.globalPos()
                    self._resize_start_rect = self.geometry()
                    self._drag_pos = None
                else:
                    # Detectar si estamos en un Ã¡rea arrastrabel (no sobre widgets interactivos)
                    widget = self.childAt(pos)
                    if widget is None or not self._is_interactive_widget(widget):
                        self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                    else:
                        self._drag_pos = None
            except Exception:
                self._drag_pos = None
                self._resize_edge = None
            event.accept()

    def mouseMoveEvent(self, event):
        """Permite arrastrar la ventana desde Ã¡reas no interactivas y redimensionar desde bordes."""
        # Redimensionamiento desde bordes
        if event.buttons() & Qt.LeftButton and getattr(self, '_resize_edge', None) is not None:
            delta = event.globalPos() - self._resize_start_pos
            rect = self._resize_start_rect
            
            new_rect = QtCore.QRect(rect)
            
            if self._resize_edge == "left":
                new_rect.setLeft(rect.left() + delta.x())
            elif self._resize_edge == "right":
                new_rect.setRight(rect.right() + delta.x())
            elif self._resize_edge == "top":
                new_rect.setTop(rect.top() + delta.y())
            elif self._resize_edge == "bottom":
                new_rect.setBottom(rect.bottom() + delta.y())
            elif self._resize_edge == "topleft":
                new_rect.setLeft(rect.left() + delta.x())
                new_rect.setTop(rect.top() + delta.y())
            elif self._resize_edge == "topright":
                new_rect.setRight(rect.right() + delta.x())
                new_rect.setTop(rect.top() + delta.y())
            elif self._resize_edge == "bottomleft":
                new_rect.setLeft(rect.left() + delta.x())
                new_rect.setBottom(rect.bottom() + delta.y())
            elif self._resize_edge == "bottomright":
                new_rect.setRight(rect.right() + delta.x())
                new_rect.setBottom(rect.bottom() + delta.y())
            
            # Aplicar tamaÃ±o mÃ­nimo
            if new_rect.width() >= self.minimumWidth() and new_rect.height() >= self.minimumHeight():
                new_rect = self._clamp_geometry_to_available(new_rect)
                if new_rect.width() >= self.minimumWidth() and new_rect.height() >= self.minimumHeight():
                    self.setGeometry(new_rect)
            
            event.accept()
        # Arrastre desde Ã¡reas no interactivas
        elif event.buttons() & Qt.LeftButton and getattr(self, '_drag_pos', None) is not None:
            try:
                global_pos = event.globalPos()
                new_pos = global_pos - self._drag_pos
                
                # Si el cursor llega al top (y = 0), activar menÃº de Windows para snap/maximize/redimensionar
                if global_pos.y() <= 0:
                    try:
                        # Liberar el grab del mouse
                        QtWidgets.QApplication.instance().restoreOverrideCursor()
                        
                        # Obtener el handle de la ventana
                        hwnd = int(self.winId())
                        
                        # Liberar el capture
                        ctypes.windll.user32.ReleaseCapture()
                        
                        # Enviar mensaje de Windows para activar el resize desde la barra de tÃ­tulo
                        # WM_NCLBUTTONDOWN = 0xA1, HTCAPTION = 2
                        ctypes.windll.user32.SendMessageW(hwnd, 0xA1, 2, 0)
                    except Exception as e:
                        pass
                    
                    self._drag_pos = None
                    event.accept()
                    return
                
                # Si no estamos en el top, mover la ventana normalmente
                self.move(new_pos)
            except Exception as e:
                print(f"Error en arrastre: {e}")
            event.accept()
        else:
            # Actualizar cursor segÃºn posiciÃ³n de los bordes para redimensionamiento
            rect = self.rect()
            pos = event.pos()
            margin = 8
            
            cursor = Qt.ArrowCursor
            
            # Detectar bordes para cambiar el cursor y permitir redimensionamiento
            if pos.y() < margin and pos.x() < margin:
                cursor = Qt.SizeFDiagCursor
            elif pos.y() < margin and pos.x() > rect.width() - margin:
                cursor = Qt.SizeBDiagCursor
            elif pos.y() > rect.height() - margin and pos.x() < margin:
                cursor = Qt.SizeBDiagCursor
            elif pos.y() > rect.height() - margin and pos.x() > rect.width() - margin:
                cursor = Qt.SizeFDiagCursor
            elif pos.y() < margin or pos.y() > rect.height() - margin:
                cursor = Qt.SizeVerCursor
            elif pos.x() < margin or pos.x() > rect.width() - margin:
                cursor = Qt.SizeHorCursor
            
            self.setCursor(cursor)
        
    def mouseReleaseEvent(self, event):
        """Resetea el estado cuando se suelta el botÃ³n del mouse."""
        if event.button() == Qt.LeftButton:
            try:
                # Limpiar estado
                self._drag_pos = None
                self._resize_edge = None
                self._resize_start_pos = None
                self._resize_start_rect = None
                
                # Resetear cursor al pointer normal
                self.setCursor(Qt.ArrowCursor)
            except Exception as e:
                print(f"Error en mouseReleaseEvent: {e}")
        
        event.accept()

    def _is_interactive_widget(self, widget):
        """Verifica si un widget es interactivo (botÃ³n, input, scroll, etc)."""
        if widget is None:
            return False
        
        # Tipos de widgets considerados interactivos
        interactive_types = (
            QPushButton, QLineEdit, QtWidgets.QScrollBar, 
            QtWidgets.QScrollArea, QTextBrowser, QtWidgets.QComboBox,
            QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox, QtWidgets.QCheckBox,
            QtWidgets.QRadioButton, QtWidgets.QSlider, QtWidgets.QMenu,
            QtWidgets.QMenuBar, QtWidgets.QTabBar, QtWidgets.QDockWidget
        )
        
        # Verificar si el widget o algÃºn padre es interactivo
        current = widget
        while current is not None:
            if isinstance(current, interactive_types):
                return True
            # TambiÃ©n verificar por nombre para elementos personalizados
            if 'scroll' in current.__class__.__name__.lower():
                return True
            if 'button' in current.__class__.__name__.lower():
                return True
            if 'input' in current.__class__.__name__.lower():
                return True
            current = current.parent()
        
        return False

    def _show_snap_overlay(self):
        """Muestra un overlay visual que indica dÃ³nde se maximizarÃ¡ la ventana."""
        try:
            screen = self._get_available_geometry_for_rect(self.geometry())
            
            # Crear overlay si no existe
            if self._snap_overlay is None:
                self._snap_overlay = QWidget()
                self._snap_overlay.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
                self._snap_overlay.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                self._snap_overlay.setStyleSheet('''
                    QWidget {
                        background: rgba(33, 150, 243, 0.2);
                        border: 2px solid rgba(33, 150, 243, 0.5);
                        border-radius: 8px;
                    }
                ''')
            
            # Posicionar overlay en toda la pantalla (tamaÃ±o maximizado)
            self._snap_overlay.setGeometry(screen)
            self._snap_overlay.show()
        except Exception:
            pass

    def _hide_snap_overlay(self):
        """Oculta el overlay visual."""
        try:
            if self._snap_overlay is not None:
                self._snap_overlay.hide()
        except Exception:
            pass

    def _get_resize_edge(self, pos):
        """Detecta si el cursor estÃ¡ en un borde de la ventana (excluye zona de controles)."""
        margin = 8  # pÃ­xeles desde el borde (aumentado para mejor detectabilidad)
        rect = self.rect()
        edge = ''
        
        # Solo permitir redimensionado desde bordes verticales (no desde la barra de menÃº)
        # Excluir la zona superior donde estÃ¡ el menÃº (primeros 70 pÃ­xeles aprox)
        menu_height = 70  # Altura aproximada de la barra de menÃº
        
        if pos.y() < margin:
            # Solo redimensionar desde el borde superior si NO estamos en la zona del menÃº
            if pos.y() < margin and pos.x() < rect.width() * 0.15:  # Solo esquina izquierda
                edge += 'top'
            elif pos.y() < margin and pos.x() > rect.width() * 0.85:  # Solo esquina derecha
                edge += 'top'
        elif pos.y() > rect.height() - margin:
            edge += 'bottom'
        
        # Permitir redimensionado desde bordes horizontales
        if pos.x() < margin:
            edge += 'left'
        elif pos.x() > rect.width() - margin:
            edge += 'right'
        
        return edge if edge else None

    def toggle_notifications_popup(self):
        """Muestra/oculta la popup de notificaciones."""
        popup = getattr(self, "notifications_popup", None)
        if popup is None:
            return

        if popup.isVisible():
            popup.hide()
            return

        self._position_notifications_popup()
        popup.show()
        popup.raise_()
        popup.activateWindow()
        self._schedule_ui_text_normalization(popup, delay_ms=0)
        # Al abrir campana, forzar lectura inmediata de eventos remotos.
        try:
            self._poll_device_events_once()
        except Exception:
            pass

        # Limpiar badge cuando se abre la popup
        self.notification_badge.hide()
        popup.clear_unread_count()

    def _position_notifications_popup(self):
        """Ancla la popup de notificaciones al botÃ³n campana y la mantiene en pantalla."""
        popup = getattr(self, "notifications_popup", None)
        bell = getattr(self, "btn_notifications", None)
        if popup is None:
            return

        if bell is None:
            popup.set_position()
            return

        try:
            # Coordenadas globales del botÃ³n
            top_left = bell.mapToGlobal(QtCore.QPoint(0, 0))
            rect = bell.rect()
            anchor_x = top_left.x() + rect.width() - popup.width()
            anchor_y = top_left.y() + rect.height() + 8

            # Clamp al Ã¡rea visible de la pantalla activa
            screen = QtWidgets.QApplication.screenAt(top_left)
            if screen is None:
                screen = QtWidgets.QApplication.primaryScreen()
            available = screen.availableGeometry()

            x = max(available.left() + 8, min(anchor_x, available.right() - popup.width() - 8))
            y = max(available.top() + 8, min(anchor_y, available.bottom() - popup.height() - 8))
            popup.set_position(QtCore.QPoint(int(x), int(y)))
        except Exception:
            popup.set_position()

    def update_notification_badge(self, count):
        """Actualiza el badge de notificaciones no leÃ­das."""
        if count > 0:
            self.notification_badge.setText(str(count))
            self.notification_badge.show()
        else:
            self.notification_badge.hide()

    def _toggle_maximize_minimize(self):
        """Toggle: maximiza si estÃ¡ pequeÃ±o, minimiza si estÃ¡ maximizado con animaciÃ³n."""
        screen = self._get_available_geometry_for_rect(self.geometry())
        
        # Crear animaciÃ³n
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(400)  # 0.4 segundos
        self.anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        
        if self.isMaximized():
            # Restaurar a tamaÃ±o normal animado
            self.showNormal()  # Salir de maximized primero
            if not hasattr(self, '_normal_geometry'):
                self._normal_geometry = QRect(200, 100, 1000, 600)
            self.anim.setStartValue(screen)
            self.anim.setEndValue(self._normal_geometry)
        else:
            # Maximizar animado
            self._normal_geometry = self.geometry()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(screen)
        
        self.anim.start()
    
    def go_to_home(self):
        """Navega a la pÃ¡gina de inicio."""
        self.mostrar_frame(0)
        try:
            def _refresh_home():
                for attr_name in ("page_0", "home_page"):
                    home = getattr(self, attr_name, None)
                    if home is None or not hasattr(home, "_load_data_background"):
                        continue
                    try:
                        home._load_data_background(allow_remote_restore=True, show_loader=False)
                        break
                    except Exception:
                        continue
            QtCore.QTimer.singleShot(120, _refresh_home)
        except Exception:
            pass

    def show_basic_embedded_page(self, page_key, page_class, **kwargs):
        """Muestra una pagina del modo basico dentro del stacked principal."""
        try:
            page = self._basic_embedded_pages.get(page_key)
            if page is None or not _is_qt_object_alive(page):
                page = page_class(self, **kwargs)
                if hasattr(page, "set_embedded_mode"):
                    page.set_embedded_mode(True)
                self._basic_embedded_pages[page_key] = page
                if self.stacked_widget.indexOf(page) == -1:
                    self.stacked_widget.addWidget(page)
            elif kwargs and hasattr(page, "_set_mode") and "initial_mode" in kwargs:
                try:
                    page._set_mode(kwargs.get("initial_mode"))
                except Exception:
                    pass

            if page_key not in self._basic_embedded_page_ids:
                self._basic_embedded_page_ids[page_key] = -1000 - len(self._basic_embedded_page_ids) - 1
            self.stacked_widget.setCurrentWidget(page)
            self.stacked_widget.updateGeometry()
            self.current_page = self._basic_embedded_page_ids[page_key]
            self._schedule_ui_text_normalization(page, delay_ms=0)
            self._schedule_ui_text_normalization(self, delay_ms=120)
            return page
        except Exception:
            logger.exception("[BASIC] Error mostrando pagina basica embebida: %s", page_key)
            raise
    
    # =========================
    # Async loading de páginas (evita congelar la UI al navegar)
    # =========================
    def _get_loading_text_for_page(self, page_index: int):
        mapping = {
            0: ("Cargando Inicio...", "Preparando dashboard y resumen general en segundo plano."),
            1: ("Cargando Pacientes...", "Preparando lista e historial de pacientes en segundo plano."),
            3: ("Cargando Inventario...", "Preparando inventario en segundo plano."),
            4: ("Cargando Ventas...", "Preparando módulo de ventas en segundo plano."),
            5: ("Cargando Kardex...", "Preparando kardex en segundo plano."),
            9: ("Cargando Clientes...", "Preparando clientes y estadisticas en segundo plano."),
        }
        return mapping.get(page_index, ("Cargando...", "Preparando interfaz en segundo plano."))

    def _ensure_loading_placeholder(self, page_index: int):
        placeholder = self._async_page_placeholders.get(page_index)
        if placeholder is not None and _is_qt_object_alive(placeholder):
            return placeholder
        if placeholder is not None:
            self._async_page_placeholders.pop(page_index, None)

        title, subtitle = self._get_loading_text_for_page(page_index)
        placeholder = LoadingPage(title=title, subtitle=subtitle, parent=self)
        placeholder.setProperty("_is_loading_placeholder", True)
        self._async_page_placeholders[page_index] = placeholder
        return placeholder

    def _start_async_page_import(self, page_index: int):
        # Import/instanciación en el thread principal pero diferido al siguiente tick,
        # para que la pantalla de carga se pinte primero (evita "No responde" y bugs de Qt-thread).
        if page_index in self._async_page_workers:
            return

        self._async_page_workers[page_index] = True
        try:
            title, _subtitle = self._get_loading_text_for_page(page_index)
            begin_operation(f"page-load:{page_index}", title, "loading")
            self._refresh_system_status_bar()
        except Exception:
            pass

        def _do_load(idx=page_index):
            try:
                self._finish_async_page_load(idx)
            finally:
                # liberar marca
                try:
                    self._async_page_workers.pop(idx, None)
                except Exception:
                    pass
                try:
                    end_operation(f"page-load:{idx}")
                    self._refresh_system_status_bar()
                except Exception:
                    pass

        QTimer.singleShot(35, _do_load)

    def _finish_async_page_load(self, page_index: int):
        placeholder = self._async_page_placeholders.get(page_index)
        if placeholder is not None and not _is_qt_object_alive(placeholder):
            placeholder = None
            self._async_page_placeholders.pop(page_index, None)
        try:
            # Si ya fue reemplazado por la página real, no hacer nada.
            existing_page = getattr(self, f"page_{page_index}", None)
            if existing_page is not None and not _is_qt_object_alive(existing_page):
                try:
                    delattr(self, f"page_{page_index}")
                except Exception:
                    pass
                existing_page = None
            if existing_page is not None and not bool(existing_page.property("_is_loading_placeholder")):
                return

            page_widget = self.load_page_on_demand(page_index)
            if page_widget is None:
                if placeholder is not None and _is_qt_object_alive(placeholder):
                    placeholder.set_status("Error cargando la página. Revise consola.")
                return

            was_current = False
            placeholder_index = -1
            if placeholder is not None:
                try:
                    placeholder_index = self.stacked_widget.indexOf(placeholder)
                except Exception:
                    placeholder_index = -1
                try:
                    was_current = self.stacked_widget.currentWidget() is placeholder
                except Exception:
                    was_current = False

            try:
                if placeholder is not None and placeholder_index != -1:
                    self.stacked_widget.insertWidget(placeholder_index, page_widget)
                    self.stacked_widget.removeWidget(placeholder)
                else:
                    if self.stacked_widget.indexOf(page_widget) == -1:
                        self.stacked_widget.addWidget(page_widget)
            except Exception:
                if self.stacked_widget.indexOf(page_widget) == -1:
                    self.stacked_widget.addWidget(page_widget)

            if placeholder is not None and _is_qt_object_alive(placeholder):
                try:
                    placeholder.deleteLater()
                except Exception:
                    pass
            if placeholder is not None:
                self._async_page_placeholders.pop(page_index, None)

            setattr(self, f"page_{page_index}", page_widget)

            should_activate = False
            try:
                should_activate = bool(placeholder is not None and was_current)
                if not should_activate:
                    should_activate = int(getattr(self, "current_page", -1) or -1) == int(page_index)
            except Exception:
                should_activate = False

            if should_activate:
                self.stacked_widget.setCurrentWidget(page_widget)
                self.stacked_widget.updateGeometry()
                self.current_page = page_index
                self._schedule_ui_text_normalization(page_widget, delay_ms=0)
                self._schedule_ui_text_normalization(self, delay_ms=120)

        except Exception as e:
            logger.error(f"[ASYNC LOAD] Error cargando página {page_index}: {e}", exc_info=True)
            if placeholder is not None and _is_qt_object_alive(placeholder):
                placeholder.set_status("Error cargando la página. Revise consola.")

    def _on_async_page_import_finished(self, page_index: int, module_name: str, class_name: str, ctor_kind: str, error: str):
        # Obsoleto: antes se importaba en QThread. Se mantiene para compatibilidad.
        try:
            logger.info("[ASYNC LOAD] Callback legacy ignorado.")
        except Exception:
            pass

    def mostrar_frame(self, page_index):
        """Muestra una pÃ¡gina especÃ­fica, cargÃ¡ndola si es necesario.
        
        TambiÃ©n maneja la liberaciÃ³n de cachÃ© de pÃ¡ginas anteriores para ahorrar RAM.
        """
        # Mapeo de Ã­ndices de pÃ¡gina a mÃ³dulos
        try:
            logger.info("[NAV] mostrar_frame page_index=%s", page_index)
        except Exception:
            pass
        page_to_module_map = {
            0: 'home_page',  # Inicio
            1: 'patients_page',  # Pacientes
            2: 'create_patient_page',  # Nueva GraduaciÃ³n
            3: 'inventory_page',  # Inventario
            4: 'sales_page',  # Ventas
            5: 'kardex_page',  # Kardex
            6: 'appointments_page',  # Citas
            9: 'customers_page',  # Clientes
            10: 'config_page',  # ConfiguraciÃ³n
            17: 'contracts_page',  # Contratos
        }

        if not self._has_device_access_to_page(page_index):
            QMessageBox.information(
                self,
                "Solo dispositivo madre",
                "Esta opciÃ³n estÃ¡ disponible Ãºnicamente para el dispositivo madre."
            )
            return
        
        # Verificar permisos si es ayudante
        if self.is_helper:
            module_name = page_to_module_map.get(page_index)
            
            # PÃ¡gina 0 (Inicio) siempre permitida
            if page_index != 0 and module_name and module_name not in self.allowed_modules:
                QMessageBox.warning(
                    self,
                    "Acceso Denegado",
                    f"No tienes permiso para acceder a este mÃ³dulo.\n\nContacta a tu jefe para solicitar acceso."
                )
                return
        
        page_attr = f'page_{page_index}'
        existing_page = getattr(self, page_attr, None)
        if existing_page is not None and not _is_qt_object_alive(existing_page):
            try:
                delattr(self, page_attr)
            except Exception:
                pass
            self._async_page_placeholders.pop(page_index, None)
            existing_page = None

        # Mostrar loading overlay SOLO en el primer acceso (startup)
        is_new_page = existing_page is None
        # DESHABILITADO: no queremos mostrar loading overlay
        # if is_new_page and page_index in [0, 1, 3, 4] and self._initial_load:  # Solo en primera carga
        #     self.loading_overlay.show_loading(f"Cargando datos...")
        self._initial_load = False  # No volver a mostrar
        
        # Si la página aún no está cargada, cargarla
        if is_new_page:
            if page_index in ASYNC_PAGE_INDICES:
                page = self._ensure_loading_placeholder(page_index)
                setattr(self, page_attr, page)
                if self.stacked_widget.indexOf(page) == -1:
                    self.stacked_widget.addWidget(page)
                self._start_async_page_import(page_index)
            else:
                page = self.load_page_on_demand(page_index)
                if page is not None:  # El load_page_on_demand retorna None si el índice no es válido
                    setattr(self, page_attr, page)
                    self.stacked_widget.addWidget(page)
                else:
                    # Si el índice no es válido o hay error al cargar, salir
                    return
        
        # Si la página es async y todavía está en placeholder, asegurar que el import siga/corra.
        if (not is_new_page) and (page_index in ASYNC_PAGE_INDICES):
            try:
                existing_page = getattr(self, f'page_{page_index}', None)
                if (
                    existing_page is not None
                    and bool(existing_page.property("_is_loading_placeholder"))
                    and (page_index not in self._async_page_workers)
                ):
                    self._start_async_page_import(page_index)
            except Exception:
                pass

        # Obtener el widget de la pÃ¡gina
        page = getattr(self, page_attr, None)
        if page is None or not _is_qt_object_alive(page):
            try:
                delattr(self, page_attr)
            except Exception:
                pass
            self._async_page_placeholders.pop(page_index, None)
            QTimer.singleShot(0, lambda idx=page_index: self.mostrar_frame(idx))
            return
        
        # Encontrar el Ã­ndice del widget en el stacked widget
        try:
            widget_index = self.stacked_widget.indexOf(page)
        except RuntimeError:
            try:
                delattr(self, page_attr)
            except Exception:
                pass
            self._async_page_placeholders.pop(page_index, None)
            QTimer.singleShot(0, lambda idx=page_index: self.mostrar_frame(idx))
            return
        if widget_index != -1:
            self.stacked_widget.setCurrentIndex(widget_index)
            self.stacked_widget.updateGeometry()
            self.current_page = page_index
            self._schedule_ui_text_normalization(page, delay_ms=0)
            self._schedule_ui_text_normalization(self, delay_ms=120)
            
        # ============ LIBERAR CACHÃ‰ DE PÃGINAS ANTERIORES ============
            # Detectar quÃ© tipo de pÃ¡gina es esta para liberar los datos asociados
            self._clean_unused_cache(page_index)
            
            # Actualizar el estado de los botones de navegaciÃ³n
            if hasattr(self, 'nav_buttons'):
                for btn, btn_page_index in self.nav_buttons:
                    btn.setChecked(btn_page_index == page_index)
                    # Actualizar el color del icono cuando estÃ¡ activo/inactivo
                    icon_path = [path for path, _, _, idx in self.nav_button_configs if idx == btn_page_index][0]
                    if os.path.exists(icon_path):
                        if btn_page_index == page_index:
                            # Para el botÃ³n activo, crear un icono con color blanco
                            icon = QIcon(icon_path)
                            pixmap = icon.pixmap(QtCore.QSize(28, 28))
                            white_pixmap = QtGui.QPixmap(pixmap.size())
                            white_pixmap.fill(Qt.transparent)
                            painter = QtGui.QPainter(white_pixmap)
                            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
                            painter.drawPixmap(0, 0, pixmap)
                            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
                            painter.fillRect(white_pixmap.rect(), QtGui.QColor(255, 255, 255))
                            painter.end()
                            btn.setIcon(QIcon(white_pixmap))
                        else:
                            # Para los botones inactivos, usar el icono original negro
                            btn.setIcon(QIcon(icon_path))
            
            # Ocultar loading overlay cuando la pÃ¡gina se muestre
            # (La seÃ±al data_loaded de HomePage se conectarÃ¡ a hide_loading())
            if is_new_page and page_index in [0, 1, 3, 4]:
                pass  # El overlay se ocultarÃ¡ automÃ¡ticamente cuando se muestre la pÃ¡gina

    def _clean_unused_cache(self, current_page_index):
        """
        Libera el cachÃ© de pÃ¡ginas que no estamos usando para ahorrar RAM.
        
        Mapeo de Ã­ndices a tipos de datos:
        - Ãndice 1 (Pacientes) -> libera cachÃ© de pacientes
        - Ãndice 3 (Inventario) -> libera cachÃ© de productos
        - Ãndice 9 (Clientes) -> libera cachÃ© de clientes
        - Ãndice 4 (Ventas) -> libera cachÃ© de ventas
        - Ãndice 6 (Citas) -> libera cachÃ© de citas
        """
        
        cache = self.cache
         
        # Mapeo de Ã­ndice de pÃ¡gina a tipos de datos a liberar
        cache_mapping = {
            0: [],  # Home - no liberar nada
            1: ['pacientes'],  # Pacientes
            2: [],  # Crear Paciente - no liberar nada
            3: ['productos'],  # Inventario
            4: ['ventas'],  # Ventas
            5: [],  # Kardex - no liberar nada
            6: ['citas'],  # Citas
            7: ['citas'],  # Citas HistÃ³ricas
            9: ['clientes'],  # Clientes
            10: [],  # Config - no liberar nada
            11: [],  # Servicios - no liberar nada
            12: [],  # Profile - no liberar nada
            13: [],  # Registro de Ventas - no liberar nada
            14: [],  # Advanced Reports - no liberar nada
            15: [],  # Plantilla de Boleta - no liberar nada
            16: [],  # CategorÃ­as - no liberar nada
        }
        
        # Obtener los tipos de datos que debe liberar esta pÃ¡gina
        data_types_to_keep = cache_mapping.get(current_page_index, [])
        
        # Lista de todos los tipos de datos que pueden estar en cachÃ©
        all_data_types = ['clientes', 'pacientes', 'productos', 'ventas', 'citas']
        
        # Liberar los datos que NO son necesarios en la pÃ¡gina actual
        for data_type in all_data_types:
            if data_type not in data_types_to_keep:
                try:
                    cache.clear_data_type(self.username, data_type)
                except Exception as e:
                    print(f"Error al limpiar cachÃ© de {data_type}: {e}")

    def _get_lazy_attr_name_for_page(self, page_index: int):
        """Retorna el nombre de atributo lazy_loader para un Ã­ndice de pÃ¡gina."""
        mapping = {
            0: 'home_page',
            1: 'patients_page',
            2: 'create_patient_page',
            3: 'inventory_page',
            4: 'sales_page',
            5: 'kardex_page',
            6: 'appointments_page',
            7: 'appointments_history_page',
            9: 'customers_page',
            10: 'config_page',
            11: 'services_page',
            12: 'profile_page',
            13: 'sales_register_page',
            14: 'advanced_reports_page',
            15: 'plantilla_boleta_page',
            16: 'categories_page',
        }
        return mapping.get(page_index)

    def _unload_page_widget(self, page_index: int):
        """Descarga una pÃ¡gina cargada para forzar recarga limpia al cambiar sucursal."""
        page_attr = f'page_{page_index}'
        page = getattr(self, page_attr, None)
        if _is_qt_object_alive(page):
            # Detener threads/timers internos ANTES del deleteLater para evitar crash tipo:
            # "QThread: Destroyed while thread is still running"
            try:
                for cleanup_name in ("cleanup", "_cleanup_all_threads", "_cleanup_async"):
                    fn = getattr(page, cleanup_name, None)
                    if callable(fn):
                        fn()
            except Exception:
                pass
            try:
                if hasattr(page, "hide"):
                    page.hide()
            except Exception:
                pass
            try:
                idx = self.stacked_widget.indexOf(page)
                if idx != -1:
                    self.stacked_widget.removeWidget(page)
                page.deleteLater()
            except Exception:
                pass
            try:
                delattr(self, page_attr)
            except Exception:
                pass

        lazy_attr = self._get_lazy_attr_name_for_page(page_index)
        if lazy_attr and hasattr(self, lazy_attr):
            try:
                delattr(self, lazy_attr)
            except Exception:
                pass

    def on_branch_context_changed(self, branch_code="", branch_label=""):
        """
        Callback global cuando cambia la sucursal seleccionada en Home.
        - Limpia caches
        - Descarga paginas cargadas (excepto Home)
        - Refresca Home en segundo plano
        """
        if getattr(self, "_branch_context_change_in_progress", False):
            self._pending_branch_context_change = (branch_code, branch_label)
            if not getattr(self, "_branch_context_defer_active", False):
                self._branch_context_defer_active = True

                def _retry_pending_branch_change():
                    self._branch_context_defer_active = False
                    if getattr(self, "_branch_context_change_in_progress", False):
                        QTimer.singleShot(250, _retry_pending_branch_change)
                        return
                    pending = getattr(self, "_pending_branch_context_change", None)
                    if not pending:
                        return
                    self._pending_branch_context_change = None
                    self.on_branch_context_changed(pending[0], pending[1])

                QTimer.singleShot(250, _retry_pending_branch_change)
            return

        self._branch_context_change_in_progress = True
        try:
            try:
                active_modal = QApplication.activeModalWidget()
            except Exception:
                active_modal = None
            if active_modal is not None and active_modal is not self and active_modal.isVisible():
                self._pending_branch_context_change = (branch_code, branch_label)
                if not getattr(self, "_branch_context_defer_active", False):
                    self._branch_context_defer_active = True

                    def _retry_deferred_branch_context():
                        self._branch_context_defer_active = False
                        pending = getattr(self, "_pending_branch_context_change", None)
                        if not pending:
                            return
                        self._pending_branch_context_change = None
                        self.on_branch_context_changed(pending[0], pending[1])

                    QTimer.singleShot(650, _retry_deferred_branch_context)
                return

            page_before = getattr(self, "current_page", 0)
            self.selected_branch_code = str(branch_code or "").strip().upper()
            self.selected_branch_label = str(branch_label or "Todas las sucursales").strip()
            self._refresh_top_branch_status_badge()

            # Sincronizar el contexto activo en memoria (redirige datasets de file_handler)
            try:
                from utils.file_handler import set_active_branch_context
                set_active_branch_context(self.username, self.selected_branch_code, self.selected_branch_label)
            except Exception as e:
                try:
                    logger.error("[BRANCH] Error sincronizando contexto activo en memoria: %s", e)
                except Exception:
                    pass

            try:
                if self.es_dispositivo_madre() and self.selected_branch_code:
                    config_path = self._get_device_config_path()
                    if config_path:
                        os.makedirs(os.path.dirname(config_path), exist_ok=True)
                        data = {}
                        if os.path.exists(config_path):
                            try:
                                with open(config_path, "r", encoding="utf-8") as f:
                                    loaded = json.load(f)
                                if isinstance(loaded, dict):
                                    data = loaded
                            except Exception:
                                data = {}
                        data.update({
                            "tipo_dispositivo": "madre",
                            "tipo_dispositivo_label": self._get_madre_label(),
                            "usuario_madre": str(self.username),
                            "codigo_dispositivo": self.selected_branch_code,
                            "nube_sync_modo": str(data.get("nube_sync_modo", "carpeta") or "carpeta"),
                            "updated_at": QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate),
                        })
                        with open(config_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            refresh_key = f"{self.selected_branch_code}|{self.selected_branch_label}"
            now = time.monotonic()
            if (
                self._last_branch_context_refresh_key == refresh_key
                and (now - float(self._last_branch_context_refresh_ts or 0.0)) < 1.2
            ):
                logger.debug(
                    "[HOME] Refresco de sucursal omitido por throttling (%s)",
                    refresh_key or "ALL"
                )
                return
            self._last_branch_context_refresh_key = refresh_key
            self._last_branch_context_refresh_ts = now

            try:
                self.cache.clear_all()
            except Exception:
                pass
            try:
                from utils.data_cache_manager import shutdown_global_cache
                shutdown_global_cache()
            except Exception:
                pass

            page_indexes = [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 13, 14, 15, 16]
            for idx in page_indexes:
                self._unload_page_widget(idx)

            def _refresh_home_once():
                for attr_name in ("page_0", "home_page"):
                    home = getattr(self, attr_name, None)
                    if not _is_qt_object_alive(home) or not hasattr(home, "_load_data_background"):
                        continue
                    try:
                        home._load_data_background(allow_remote_restore=True)
                        return True
                    except RuntimeError as e:
                        logger.warning("[HOME] No se pudo refrescar %s: %s", attr_name, e)
                    except Exception:
                        logger.exception("[HOME] Error refrescando %s", attr_name)
                return False

            refreshed = _refresh_home_once()
            if not refreshed:
                logger.warning(
                    "[HOME] No se encontro instancia activa de Home para refrescar (sucursal=%s)",
                    self.selected_branch_code or "ALL",
                )
            QTimer.singleShot(180, _refresh_home_once)

            try:
                page_before = int(page_before) if page_before is not None else 0
            except Exception:
                page_before = 0
            if page_before not in (None, 0) and page_before != 0:
                def _reload_current_page_once():
                    try:
                        if int(getattr(self, "current_page", 0) or 0) == 0:
                            return
                        if page_before == 9:
                            self.go_to_create_cliente()
                            return
                        self.mostrar_frame(page_before)
                    except Exception:
                        pass
                QTimer.singleShot(0, _reload_current_page_once)
        finally:
            self._branch_context_change_in_progress = False
            pending = getattr(self, "_pending_branch_context_change", None)
            if pending and pending != (self.selected_branch_code, self.selected_branch_label):
                self._pending_branch_context_change = None
                QTimer.singleShot(0, lambda p=pending: self.on_branch_context_changed(p[0], p[1]))

    def go_to_create_cliente(self):
        self.mostrar_frame(9)
        return
        # Cargar la pÃ¡gina de clientes si aÃºn no estÃ¡ cargada
        from gui.main_window_pages.customer_page import CustomersPage
        if not hasattr(self, 'customers_page'):
            self.customers_page = CustomersPage(self)
            self.stacked_widget.addWidget(self.customers_page)
            
        # Encontrar el Ã­ndice de la pÃ¡gina de clientes y mostrarla
        index = self.stacked_widget.indexOf(self.customers_page)
        if index != -1:
            self.stacked_widget.setCurrentIndex(index)
            self.current_page = index
            
            # Actualizar el estado de los botones de navegaciÃ³n
            if hasattr(self, 'nav_buttons'):
                for btn, btn_page_index in self.nav_buttons:
                    btn.setChecked(btn_page_index == -1)  # -1 es el Ã­ndice especial para la pÃ¡gina de clientes
                    # Actualizar el color del icono cuando estÃ¡ activo/inactivo
                    icon_path = [path for path, _, _, idx in self.nav_button_configs if idx == btn_page_index][0]
                    if os.path.exists(icon_path):
                        if btn_page_index == -1:
                            # Para el botÃ³n activo, crear un icono con color blanco
                            icon = QIcon(icon_path)
                            pixmap = icon.pixmap(QtCore.QSize(28, 28))
                            white_pixmap = QtGui.QPixmap(pixmap.size())
                            white_pixmap.fill(Qt.transparent)
                            painter = QtGui.QPainter(white_pixmap)
                            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
                            painter.drawPixmap(0, 0, pixmap)
                            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
                            painter.fillRect(white_pixmap.rect(), QtGui.QColor(255, 255, 255))
                            painter.end()
                            btn.setIcon(QIcon(white_pixmap))
                        else:
                            # Para los botones inactivos, usar el icono original negro
                            btn.setIcon(QIcon(icon_path))
    
    def ir_a_historial_ventas(self):
        """Navega a la pÃ¡gina de ventas y cambia al tab de Historial de Ventas."""
        # Primero mostrar la pÃ¡gina de ventas (frame 4)
        try:
            logger.info("[NAV] ir_a_historial_ventas")
        except Exception:
            pass
        self.mostrar_frame(4)
        
        # Luego cambiar al tab de Historial de Ventas si la pÃ¡gina ya estÃ¡ cargada
        if hasattr(self, 'page_4') and hasattr(self.page_4, 'tab_widget'):
            # Nueva Venta = 0, Venta Manual = 1, RevisiÃ³n de Deudas = 2, Historial = 3
            self.page_4.tab_widget.setCurrentIndex(3)
            try:
                QtCore.QTimer.singleShot(
                    0,
                    lambda: getattr(self.page_4, "_ensure_lazy_sales_tab_built", lambda *_: None)(3)
                )
            except Exception:
                pass
    
    def ir_a_historial_deudas(self):
        """Navega a la pÃ¡gina de ventas y cambia al tab de RevisiÃ³n de Deudas."""
        # Primero mostrar la pÃ¡gina de ventas (frame 4)
        self.mostrar_frame(4)
        
        # Luego cambiar al tab de RevisiÃ³n de Deudas si la pÃ¡gina ya estÃ¡ cargada
        if hasattr(self, 'page_4') and hasattr(self.page_4, 'tab_widget'):
            # Nueva Venta = 0, Venta Manual = 1, RevisiÃ³n de Deudas = 2
            self.page_4.tab_widget.setCurrentIndex(2)
    
    def ir_a_venta_manual(self):
        """Navega a la pÃ¡gina de ventas y cambia al tab de Venta Manual."""
        # Primero mostrar la pÃ¡gina de ventas (frame 4)
        self.mostrar_frame(4)
        
        # Luego cambiar al tab de Venta Manual si la pÃ¡gina ya estÃ¡ cargada
        if hasattr(self, 'page_4') and hasattr(self.page_4, 'tab_widget'):
            # Nueva Venta = 0, Venta Manual = 1
            self.page_4.tab_widget.setCurrentIndex(1)

    def ir_a_guia_remision(self):
        """Navega a la página de ventas y cambia al tab de Guía de Remisión."""
        self.mostrar_frame(4)

        if hasattr(self, 'page_4') and hasattr(self.page_4, 'tab_widget'):
            try:
                tab_widget = self.page_4.tab_widget
                for idx in range(tab_widget.count()):
                    if str(tab_widget.tabText(idx)).strip().lower() == "guia de remision":
                        tab_widget.setCurrentIndex(idx)
                        try:
                            QtCore.QTimer.singleShot(
                                0,
                                lambda i=idx: getattr(self.page_4, "_ensure_lazy_sales_tab_built", lambda *_: None)(i)
                            )
                        except Exception:
                            pass
                        break
            except Exception:
                pass
    
    def open_barcode_generator(self):
        """Abre la ventana del generador de cÃ³digos de barras"""
        try:
            from gui.dialogs.barcode_generator_new import BarcodeGeneratorDialog
            dialog = BarcodeGeneratorDialog(self)
            dialog.exec_()
        except ImportError as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el generador de cÃ³digos de barras:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir el generador:\n{str(e)}")

    def open_sync_center(self):
        """Abre el centro de sincronizaciÃ³n."""
        try:
            from gui.dialogs.sync_center_dialog import SyncCenterDialog

            dialog = SyncCenterDialog(
                username=str(getattr(self, "username", "") or "").strip(),
                user_id=str(getattr(self, "user_id", "") or getattr(self, "username", "")).strip(),
                parent=self,
            )
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el centro de sincronizaciÃ³n:\n{str(e)}")

    def open_trash_recovery(self):
        """Abre la papelera y recuperacion."""
        try:
            from gui.dialogs.trash_recovery_dialog import TrashRecoveryDialog

            dialog = TrashRecoveryDialog(
                username=str(getattr(self, "username", "") or "").strip(),
                user_id=str(getattr(self, "user_id", "") or getattr(self, "username", "")).strip(),
                parent=self,
            )
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la papelera:\n{str(e)}")

    def open_audit_page(self):
        """Abre la ventana del Libro Contable"""
        if not self.es_dispositivo_madre():
            QMessageBox.information(
                self,
                "Solo dispositivo madre",
                "El Libro Contable estÃ¡ habilitado solo en el dispositivo madre."
            )
            return

        try:
            from gui.dialogs.audit_page import AuditPage
            
            audit_dialog = QtWidgets.QDialog(self)
            audit_dialog.setWindowTitle("ðŸ“– Libro Contable - VISO")
            audit_dialog.setGeometry(100, 100, 1200, 700)
            
            layout = QtWidgets.QVBoxLayout(audit_dialog)
            
            audit_page = AuditPage(self, username=self.username)
            
            # Obtener audit_manager desde la referencia a app_instance
            audit_mgr = None
            if hasattr(self, 'app_instance') and hasattr(self.app_instance, 'audit_manager'):
                audit_mgr = self.app_instance.audit_manager
            elif hasattr(self, 'audit_manager'):
                audit_mgr = self.audit_manager
            
            if audit_mgr:
                audit_page.set_audit_manager(audit_mgr)
            else:
                # Si no hay audit_manager disponible, mostrar mensaje
                QtWidgets.QMessageBox.warning(
                    self, 
                    "Advertencia",
                    "No se pudo cargar el gestor de auditorÃ­a. Verifique que la sesiÃ³n se iniciÃ³ correctamente."
                )
                return
            
            layout.addWidget(audit_page)
            
            audit_dialog.exec_()
        except ImportError as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el Libro Contable:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir Libro Contable:\n{str(e)}")
    
    def load_patient_page(self):
        """Navega a la pÃ¡gina de pacientes (Ã­ndice 1) y recarga los datos."""
        self.mostrar_frame(1)
        # Recargar la lista de pacientes si la pÃ¡gina ya estÃ¡ cargada
        if hasattr(self, 'patients_page') and hasattr(self.patients_page, 'load_patients'):
            self.patients_page.load_patients()
    
    def manual_backup(self):
        """Ejecuta respaldo manual inmediato a nube."""
        try:
            if not self.es_dispositivo_madre():
                return
            if not hasattr(self, "_backup_button") or self._backup_button is None:
                return
            if getattr(self, "_backup_active", False):
                return

            usuario_sync = str(getattr(self, "user_id", "") or getattr(self, "username", "")).strip()
            if not usuario_sync:
                QMessageBox.warning(self, "Respaldo", "No se pudo identificar el usuario para respaldar.")
                return

            self._backup_active = True
            self._backup_button_original_text = self._backup_button.text()
            self._backup_button_original_style = self._backup_button.styleSheet()
            self._backup_button.setEnabled(False)
            self._show_loading_animation()

            def _worker():
                ok = False
                message = "Error desconocido"
                portal_url = ""
                try:
                    from utils.sync_manager import get_sync_manager
                    sync_mgr = get_sync_manager()
                    result = sync_mgr.force_cloud_backup(usuario_sync)
                    ok = bool((result or {}).get("ok"))
                    message = str((result or {}).get("message", "Respaldo sin detalle"))
                    portal_url = str((result or {}).get("portal_url", "")).strip()
                except Exception as e:
                    message = str(e)

                try:
                    self.manual_backup_finished.emit(ok, message, portal_url)
                except Exception:
                    # Fallback defensivo: no dejar UI en estado cargando.
                    QtCore.QTimer.singleShot(
                        0,
                        lambda: self._on_manual_backup_finished(ok, message, portal_url)
                    )

            import threading
            threading.Thread(target=_worker, daemon=True).start()
        except Exception as e:
            self._backup_active = False
            self._restore_backup_button()
            print(f"[ERROR] Error en manual_backup: {e}")

    def _show_loading_animation(self):
        """Muestra animaciÃ³n de carga en el botÃ³n."""
        try:
            if hasattr(self, '_backup_button'):
                self._animation_counter = 0
                self._animation_timer = QtCore.QTimer()
                self._animation_timer.timeout.connect(self._update_loading_animation)
                # Usar texto para la animaciÃ³n del loader
                self._backup_button.setIcon(QIcon())
                self._backup_button.setText("")
                self._animation_timer.start(100)
        except Exception:
            pass
    
    def _update_loading_animation(self):
        """Actualiza la animaciÃ³n del loader."""
        try:
            if hasattr(self, '_backup_button'):
                frames = ['|', '/', '-', '\\']
                self._animation_counter = (self._animation_counter + 1) % len(frames)
                self._backup_button.setText(frames[self._animation_counter])
        except Exception:
            pass
    
    def _show_checkmark(self):
        """Muestra checkmark de Ã©xito con SVG."""
        try:
            if hasattr(self, '_backup_button'):
                # Mostrar icono de checkmark SVG
                icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
                check_icon_path = os.path.join(icons_dir, 'check.svg')
                
                if os.path.exists(check_icon_path):
                    check_icon = QIcon(check_icon_path)
                    self._backup_button.setIcon(check_icon)
                    self._backup_button.setIconSize(QtCore.QSize(16, 16))
                    self._backup_button.setText("")
                else:
                    self._backup_button.setText("OK")
                
                # Volver al icono original despuÃ©s de 2 segundos
                def restore_button():
                    self._restore_backup_button()
                
                QtCore.QTimer.singleShot(2000, restore_button)
        except Exception as e:
            print(f"[ERROR] Error en _show_checkmark: {e}")
        except Exception:
            pass

    def _restore_backup_button(self):
        try:
            if not hasattr(self, "_backup_button") or self._backup_button is None:
                return
            if hasattr(self, '_backup_button_original_icon') and self._backup_button_original_icon:
                self._backup_button.setIcon(self._backup_button_original_icon)
                self._backup_button.setIconSize(QtCore.QSize(16, 16))
                self._backup_button.setText("")
            elif hasattr(self, '_backup_button_original_text'):
                self._backup_button.setText(self._backup_button_original_text)

            if hasattr(self, '_backup_button_original_style'):
                self._backup_button.setStyleSheet(self._backup_button_original_style)
            self._backup_button.setEnabled(True)
        except Exception:
            pass

    def _show_manual_backup_success_dialog(self, message: str, portal_url: str = ""):
        """Muestra confirmacion de respaldo manual con opcion Open."""
        try:
            from urllib.parse import quote_plus
            usuario_madre = str(getattr(self, "username", "alex9121")).strip()
            
            # Si no viene URL, la construimos con el ID de esta PC que vimos en los logs
            if not portal_url:
                # Intentar obtener el codigo efectivo (el mismo que usa el SyncManager)
                import os
                import re
                base = re.sub(r"[^A-Za-z0-9]+", "", usuario_madre.upper()) or "USER"
                machine = re.sub(r"[^A-Za-z0-9]+", "", os.environ.get("COMPUTERNAME", "LOCAL").upper()) or "LOCAL"
                codigo_pc = f"MADRE-{base}-{machine}"[:80]
                
                portal_url = f"https://api.yhana.cloud/win/new/manual_backup_portal.php?usuario_madre={quote_plus(usuario_madre)}&codigo_dispositivo={quote_plus(codigo_pc)}"

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Respaldo Manual Exitoso")
            msg.setText("<b>¡Respaldo completado!</b><br><br>Tus datos han sido asegurados en la nube de Yhana Cloud.")
            
            if message:
                msg.setInformativeText(message)

            # Botones
            btn_open = msg.addButton("Ver Respaldo en Nube", QMessageBox.AcceptRole)
            btn_open.setStyleSheet("background-color: #2196F3; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;")
            msg.addButton("Cerrar", QMessageBox.RejectRole)

            msg.exec_()

            if msg.clickedButton() == btn_open:
                import webbrowser
                webbrowser.open(portal_url)
                
        except Exception as e:
            print(f"Error en dialogo de respaldo: {e}")

    def _show_manual_backup_blocked_dialog(self, message: str):
        """Muestra un bloqueo de seguridad visible para evitar sobrescrituras vacías."""
        try:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Respaldo bloqueado por seguridad")
            msg.setText(
                "<b>La subida fue bloqueada.</b><br><br>"
                "Esta PC no puede subir datos vacíos si la nube ya contiene información."
            )
            if message:
                msg.setInformativeText(message)

            btn_sync_center = msg.addButton("Abrir centro de sincronización", QMessageBox.AcceptRole)
            btn_sync_center.setStyleSheet(
                "background-color: #2C7BE5; color: white; padding: 6px 12px; "
                "font-weight: bold; border-radius: 4px;"
            )
            msg.addButton("Cerrar", QMessageBox.RejectRole)
            msg.exec_()

            if msg.clickedButton() == btn_sync_center:
                self.open_sync_center()
        except Exception as e:
            print(f"Error en dialogo de bloqueo de respaldo: {e}")

    def _on_manual_backup_finished(self, ok: bool, message: str, portal_url: str = ""):
        self._backup_active = False
        try:
            if hasattr(self, "_animation_timer") and self._animation_timer is not None:
                self._animation_timer.stop()
        except Exception:
            pass

        normalized_message = str(message or "").strip().lower()
        is_guard_block = (
            "bloqueado por seguridad" in normalized_message
            or ("nube ya contiene informacion" in normalized_message and "no se subio nada" in normalized_message)
            or "no hay datos locales reales para subir" in normalized_message
        )

        if ok:
            self._show_checkmark()
            self._show_manual_backup_success_dialog(message, portal_url)
        elif is_guard_block:
            self._show_manual_backup_blocked_dialog(message)
        else:
            QMessageBox.warning(
                self,
                "Respaldo no completado",
                message or "No se pudo completar el respaldo manual."
            )
        self._restore_backup_button()
    
    def _trigger_backup(self):
        """Dispara el respaldo manual."""
        try:
            # Acceder a la funciÃ³n respaldo_automatico desde el contexto global
            if hasattr(self, '_backup_trigger_func'):
                self._backup_trigger_func()
        except Exception as e:
            print(f"[ERROR] Error al disparar respaldo: {e}")
    
    def increase_zoom(self):
        """Aumenta el tamaÃ±o de fuente (zoom) en toda la aplicaciÃ³n"""
        import time
        current_time = time.time()
        
        # Evitar que se ejecute si hace poco se hizo una acciÃ³n de zoom (200ms de delay)
        if self.zoom_last_action and (current_time - self.zoom_last_action) < 0.2:
            return
        
        # Solo aumentar si no estÃ¡ al mÃ¡ximo
        if self.zoom_factor < 2.0:
            self.zoom_factor = min(self.zoom_factor + 0.1, 2.0)
            percentage = int(self.zoom_factor * 100)
            print(f"[ZOOM] Aumentado: {percentage}%")
            self.zoom_last_action = current_time
            self.apply_zoom()
        else:
            print(f"[ZOOM] Ya estÃ¡ al mÃ¡ximo (200%)")
    
    def decrease_zoom(self):
        """Disminuye el tamaÃ±o de fuente (zoom) en toda la aplicaciÃ³n"""
        import time
        current_time = time.time()
        
        # Evitar que se ejecute si hace poco se hizo una acciÃ³n de zoom (200ms de delay)
        if self.zoom_last_action and (current_time - self.zoom_last_action) < 0.2:
            return
        
        # Solo disminuir si no estÃ¡ al mÃ­nimo
        if self.zoom_factor > 0.5:
            self.zoom_factor = max(self.zoom_factor - 0.1, 0.5)
            percentage = int(self.zoom_factor * 100)
            print(f"[ZOOM] Disminuido: {percentage}%")
            self.zoom_last_action = current_time
            self.apply_zoom()
        else:
            print(f"[ZOOM] Ya estÃ¡ al mÃ­nimo (50%)")
    
    def reset_zoom(self):
        """Resetea el zoom a 100%"""
        self.zoom_factor = 1.0
        print(f"[ZOOM] Resetado: 100%")
        self.apply_zoom()
    
    def apply_zoom(self):
        """Aplica el factor de zoom a toda la aplicaciÃ³n (versiÃ³n optimizada)"""
        try:
            # Solo cambiar tamaÃ±o de fuente base
            font = QtGui.QFont()
            base_font_size = 10
            new_font_size = int(base_font_size * self.zoom_factor)
            font.setPointSize(new_font_size)
            
            # Aplicar la fuente a toda la aplicaciÃ³n (esto es lo principal)
            QApplication.instance().setFont(font)
            
            # Forzar actualizaciÃ³n visual sin recursiÃ³n (mÃ¡s rÃ¡pido)
            QtCore.QTimer.singleShot(50, lambda: self.update() or self.repaint())
        except Exception as e:
            print(f"[ERROR] Error al aplicar zoom: {e}")
    
    def _apply_zoom_recursive(self, widget, zoom_factor):
        """MÃ©todo deprecado - ya no se usa"""
        pass
    
    def restart_app(self):
        """Reinicia la aplicaciÃ³n automÃ¡ticamente"""
        import subprocess
        try:
            # Obtener el ejecutable actual
            app_path = sys.argv[0]
            print(f"[INFO] Reiniciando aplicaciÃ³n: {app_path}")
            
            # Iniciar nueva instancia del programa
            if sys.platform.startswith('win'):
                # En Windows, usar subprocess.Popen
                subprocess.Popen([sys.executable, app_path])
            else:
                # En Linux/Mac
                subprocess.Popen([sys.executable, app_path])
            
            # Cerrar la aplicaciÃ³n actual
            self.close()
        except Exception as e:
            print(f"[ERROR] No se pudo reiniciar la aplicaciÃ³n: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo reiniciar la aplicaciÃ³n: {e}")
    
    def closeEvent(self, event):
        """Limpia threads, cachÃ© y GUARDA LA SESIÃ“N antes de cerrar la ventana (SOLO si no fue logout)."""
        try:
            # GUARDAR SESIÃ“N AUTOMÃTICAMENTE AL CERRAR (IMPORTANTE PARA .EXE)
            # PERO solo si NO fue un logout explÃ­cito (que tiene su propio flujo)
            is_explicit_logout = getattr(self, '_explicit_logout', False)
            
            if not is_explicit_logout:
                # Guardar sesiÃ³n SOLO si fue cierre normal (sin logout)
                try:
                    from utils.file_handler import SESION_FILE
                    sesion_file_path = str(SESION_FILE)
                    
                    # Guardar el usuario en el archivo de sesiÃ³n con formato correcto
                    if hasattr(self, 'user_id') and self.user_id:
                        # Formato: username:user_id:user (o ayudante format si es helper)
                        if hasattr(self, 'is_helper') and self.is_helper:
                            # Guardar sesiÃ³n de ayudante: jefe_username:helper_username:helper
                            if hasattr(self, 'helper_name') and self.helper_name:
                                jefe_username = getattr(self, 'username', self.user_id)
                                session_content = f"{jefe_username}:{self.helper_name}:helper"
                            else:
                                session_content = self.user_id  # Fallback
                        else:
                            # Guardar sesiÃ³n de usuario normal: username:user_id:user
                            username = getattr(self, 'username', self.user_id)
                            session_content = f"{username}:{self.user_id}:user"
                        
                        with open(sesion_file_path, "w", encoding="utf-8") as f:
                            f.write(session_content)
                except Exception as e:
                    print(f"[WARNING] No se pudo guardar sesiÃ³n al cerrar: {e}")
            else:
                print(f"[LOGOUT] No guardando sesiÃ³n (fue logout explÃ­cito)")
            
            # CERRAR SESIÃ“N ACTIVA (limpieza de single session)
            try:
                from utils.single_session import cerrar_sesion
                from utils.file_handler import SESION_FILE
                
                base_dir = os.path.dirname(os.path.dirname(str(SESION_FILE)))
                username = getattr(self, 'username', None)
                
                if username:
                    cerrar_sesion(base_dir, username)
                    print(f"[SESSION] SesiÃ³n cerrada para '{username}'")
            except Exception as e:
                print(f"[SESSION] Error cerrando sesiÃ³n: {e}")
            
            # Limpiar todo el cachÃ© (sin print)
            try:
                self.cache.clear_all()
            except Exception:
                pass
            
            # Detener timer de backup
            if hasattr(self, '_backup_timer'):
                try:
                    self._backup_timer.stop()
                except Exception:
                    pass

            if hasattr(self, '_system_status_poll_timer') and self._system_status_poll_timer:
                try:
                    self._system_status_poll_timer.stop()
                except Exception:
                    pass
            if hasattr(self, '_system_status_snapshot_timer') and self._system_status_snapshot_timer:
                try:
                    self._system_status_snapshot_timer.stop()
                except Exception:
                    pass
            if hasattr(self, '_system_status_worker') and self._system_status_worker:
                try:
                    if self._system_status_worker.isRunning():
                        self._system_status_worker.quit()
                        self._system_status_worker.wait(300)
                except Exception:
                    pass

            # Detener polling de eventos de dispositivos hijos
            try:
                self._stop_device_event_polling()
            except Exception:
                pass
            
            # Cancelar y limpiar thread de backup
            if hasattr(self, '_backup_thread') and self._backup_thread:
                try:
                    if hasattr(self._backup_thread, 'cleanup'):
                        self._backup_thread.cleanup()
                    elif self._backup_thread.isRunning():
                        self._backup_thread.cancel()
                        self._backup_thread.quit()
                        self._backup_thread.wait(100)
                except Exception:
                    pass
            
            # Limpiar threads en home_page
            if hasattr(self, 'home_page'):
                try:
                    if hasattr(self.home_page, 'notification_worker') and self.home_page.notification_worker:
                        self.home_page.notification_worker.stop()
                        self.home_page.notification_worker.wait(500)
                except Exception:
                    pass

            # Evitar draw_idle pendiente de matplotlib sobre canvas ya destruido
            try:
                home = getattr(self, "page_0", None) or getattr(self, "home_page", None)
                if home is not None and hasattr(home, "home_widget"):
                    hw = home.home_widget
                    for ranking_attr in ("top_customers", "top_products"):
                        ranking = getattr(hw, ranking_attr, None)
                        if ranking is not None and hasattr(ranking, "cleanup"):
                            ranking.cleanup()
            except Exception:
                pass
            
            # Limpiar threads en inventory_page si estÃ¡ activa
            if hasattr(self, 'inventory_page') and hasattr(self.inventory_page, '_cleanup_all_threads'):
                try:
                    self.inventory_page._cleanup_all_threads()
                except Exception:
                    pass
            
            # Limpiar threads en otras pÃ¡ginas que lo necesiten
            if hasattr(self, 'customer_page') and hasattr(self.customer_page, 'cleanup'):
                try:
                    self.customer_page.cleanup()
                except Exception:
                    pass
            
            for page_name in ['sales_page', 'customers_page', 'patients_page']:
                if hasattr(self, page_name):
                    page = getattr(self, page_name)
                    if hasattr(page, '_cleanup_all_threads'):
                        try:
                            page._cleanup_all_threads()
                        except Exception:
                            pass
        except Exception:
            pass
        finally:
            event.accept()

