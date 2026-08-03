from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QFrame,
    QApplication,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import webbrowser


class LazyScrollArea(QScrollArea):
    load_more = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_more.connect(self._on_load_more)

    def _on_load_more(self):
        pass

    def wheelEvent(self, event):
        super().wheelEvent(event)
        if self.verticalScrollBar().value() >= self.verticalScrollBar().maximum() - 50:
            self.load_more.emit()


class LoadNotificationsWorker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, notifications):
        super().__init__()
        self.notifications = notifications

    def run(self):
        self.finished.emit(self.notifications)


class NotificationItem(QFrame):
    open_link = pyqtSignal(str)

    def __init__(self, notif_data):
        super().__init__()
        self.notif_data = dict(notif_data or {})
        self.setObjectName("notificationCard")
        self.setStyleSheet(
            """
            QFrame#notificationCard {
                background: #FFFFFF;
                border: 1px solid #E5EAF3;
                border-radius: 10px;
            }
            QLabel#notifTitle {
                color: #0F172A;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#notifMessage {
                color: #475569;
                font-size: 12px;
            }
            QLabel#notifMeta {
                color: #94A3B8;
                font-size: 11px;
            }
            QLabel#notifBadge {
                background: #EFF6FF;
                color: #2563EB;
                border-radius: 8px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton#notifAction {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#notifAction:hover {
                background: #1D4ED8;
            }
            QPushButton#notifAction:disabled {
                background: #CBD5E1;
                color: #F8FAFC;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 12, 14, 12)

        avatar = QLabel()
        avatar.setFixedSize(42, 42)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            """
            QLabel {
                background: #DBEAFE;
                color: #1D4ED8;
                border-radius: 21px;
                font-size: 16px;
                font-weight: 800;
            }
            """
        )
        avatar.setText(self._build_avatar_text())
        layout.addWidget(avatar, 0, Qt.AlignTop)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 0, 0, 0)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        title = QLabel(self._title_text())
        title.setObjectName("notifTitle")
        title.setWordWrap(True)
        top_row.addWidget(title, 1)

        badge = QLabel(self._category_text())
        badge.setObjectName("notifBadge")
        top_row.addWidget(badge, 0, Qt.AlignTop)
        content_layout.addLayout(top_row)

        msg = QLabel(self._message_text())
        msg.setObjectName("notifMessage")
        msg.setWordWrap(True)
        content_layout.addWidget(msg)

        meta = QLabel(self._meta_text())
        meta.setObjectName("notifMeta")
        meta.setWordWrap(True)
        content_layout.addWidget(meta)

        layout.addLayout(content_layout, 1)

        action_btn = QPushButton("Abrir" if self.notif_data.get("enlace") else "Ver")
        action_btn.setObjectName("notifAction")
        action_btn.setEnabled(bool(self.notif_data.get("enlace")))
        if self.notif_data.get("enlace"):
            action_btn.clicked.connect(lambda: self.open_link.emit(str(self.notif_data.get("enlace") or "").strip()))
        layout.addWidget(action_btn, 0, Qt.AlignVCenter)

    def _build_avatar_text(self):
        titulo = str(self.notif_data.get("titulo", "") or "").strip()
        if titulo:
            return titulo[:1].upper()
        return "N"

    def _title_text(self):
        return str(self.notif_data.get("titulo", "Notificación") or "Notificación").strip()

    def _message_text(self):
        return str(self.notif_data.get("mensaje", "Sin detalle") or "Sin detalle").strip()

    def _category_text(self):
        titulo = self._title_text().lower()
        if "producto" in titulo:
            return "Inventario"
        if "venta" in titulo:
            return "Ventas"
        if "paciente" in titulo or "cliente" in titulo:
            return "Pacientes"
        return "General"

    def _meta_text(self):
        fecha = str(self.notif_data.get("fecha", "") or "").strip()
        relative = NotificationsPopup.format_relative_time(fecha)
        return f"{relative}  |  {fecha}" if fecha else relative


class NotificationsPopup(QWidget):
    unread_count_changed = pyqtSignal(int)
    NOTIFICATIONS_FILE = Path(os.path.expanduser("~")) / ".viso" / "notifications_history.json"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notificaciones")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.load_worker = None
        self.all_notifications = []
        self.filtered_notifications = []
        self.displayed_count = 0
        self.items_per_load = 15
        self.unread_notifications = set()
        self.filter_mode = "all"
        self.period_days = 15

        self.NOTIFICATIONS_FILE.parent.mkdir(exist_ok=True)

        self.setup_ui()
        self.set_position()
        self._load_notifications_from_file()

    @staticmethod
    def _shadow():
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(26)
        effect.setOffset(0, 8)
        effect.setColor(QColor(15, 23, 42, 45))
        return effect

    @staticmethod
    def _parse_datetime(value):
        raw = str(value or "").strip()
        if not raw:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt)
            except Exception:
                pass
        try:
            return datetime.fromisoformat(raw)
        except Exception:
            return None

    @staticmethod
    def format_relative_time(value):
        dt = NotificationsPopup._parse_datetime(value)
        if dt is None:
            return "Sin fecha"
        now = datetime.now()
        delta = now - dt
        if delta < timedelta(minutes=1):
            return "Hace un momento"
        if delta < timedelta(hours=1):
            minutes = max(1, int(delta.total_seconds() // 60))
            return f"Hace {minutes} min"
        if delta < timedelta(days=1):
            hours = max(1, int(delta.total_seconds() // 3600))
            return f"Hace {hours} h"
        if delta < timedelta(days=30):
            return f"Hace {delta.days} día(s)"
        return dt.strftime("%d/%m/%Y")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        container = QFrame()
        container.setObjectName("notificationsContainer")
        container.setGraphicsEffect(self._shadow())
        container.setStyleSheet(
            """
            QFrame#notificationsContainer {
                background: #F8FAFC;
                border: 1px solid #DCE5F1;
                border-radius: 14px;
            }
            """
        )

        c = QVBoxLayout(container)
        c.setContentsMargins(0, 0, 0, 0)
        c.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border-bottom: 1px solid #E5EAF3;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }
            """
        )
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(18, 16, 18, 14)
        h_layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        title = QLabel("Notificaciones")
        title.setStyleSheet("color: #0F172A; font-size: 16px; font-weight: 800;")
        title_col.addWidget(title)

        self.summary_label = QLabel("Sin actividad reciente")
        self.summary_label.setStyleSheet("color: #64748B; font-size: 11px;")
        title_col.addWidget(self.summary_label)
        top_row.addLayout(title_col, 1)

        self.btn_mark_read = QPushButton("Marcar leídas")
        self.btn_mark_read.setCursor(Qt.PointingHandCursor)
        self.btn_mark_read.clicked.connect(self.clear_unread_count)
        self.btn_mark_read.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: #475569;
                border: none;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 6px;
            }
            QPushButton:hover {
                color: #0F172A;
            }
            """
        )
        top_row.addWidget(self.btn_mark_read)

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)
        self.btn_close.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                border-radius: 14px;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #EFF6FF;
                color: #0F172A;
            }
            """
        )
        top_row.addWidget(self.btn_close)
        h_layout.addLayout(top_row)

        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 0, 0, 0)
        stats_row.setSpacing(8)

        self.stats_total = self._build_stat_chip("Total", "0")
        self.stats_unread = self._build_stat_chip("Nuevas", "0")
        self.stats_visible = self._build_stat_chip("Visibles", "0")
        stats_row.addWidget(self.stats_total)
        stats_row.addWidget(self.stats_unread)
        stats_row.addWidget(self.stats_visible)
        stats_row.addStretch()
        h_layout.addLayout(stats_row)

        filters_row = QHBoxLayout()
        filters_row.setContentsMargins(0, 0, 0, 0)
        filters_row.setSpacing(8)

        self.btn_all = self._build_filter_button("Todas")
        self.btn_all.clicked.connect(lambda: self._set_filter_mode("all"))
        filters_row.addWidget(self.btn_all)

        self.btn_unread = self._build_filter_button("No leídas")
        self.btn_unread.clicked.connect(lambda: self._set_filter_mode("unread"))
        filters_row.addWidget(self.btn_unread)

        filters_row.addStretch()

        self.btn_period = self._build_secondary_button("Últimos 15 días")
        self.btn_period.clicked.connect(self._cycle_period_filter)
        filters_row.addWidget(self.btn_period)

        self.btn_clear = self._build_secondary_button("Limpiar historial")
        self.btn_clear.clicked.connect(self._clear_history)
        filters_row.addWidget(self.btn_clear)

        h_layout.addLayout(filters_row)
        c.addWidget(header)

        scroll = LazyScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                border-radius: 4px;
            }
            """
        )
        scroll.load_more.connect(self._load_more_notifications)

        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setContentsMargins(14, 14, 14, 14)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        c.addWidget(scroll)

        layout.addWidget(container)
        self.setFixedSize(430, 620)
        self._refresh_filter_buttons()

    def _build_stat_chip(self, title, value):
        chip = QFrame()
        chip.setStyleSheet(
            """
            QFrame {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            """
        )
        layout = QVBoxLayout(chip)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(0)

        lbl_title = QLabel(str(title))
        lbl_title.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 700;")
        layout.addWidget(lbl_title)

        lbl_value = QLabel(str(value))
        lbl_value.setStyleSheet("color: #0F172A; font-size: 14px; font-weight: 800;")
        layout.addWidget(lbl_value)

        chip.value_label = lbl_value
        return chip

    def _build_filter_button(self, text):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setCheckable(True)
        btn.setStyleSheet(
            """
            QPushButton {
                background: #FFFFFF;
                color: #334155;
                border: 1px solid #D6E0EC;
                border-radius: 9px;
                padding: 7px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:checked {
                background: #DBEAFE;
                color: #1D4ED8;
                border-color: #BFDBFE;
            }
            QPushButton:hover {
                background: #F8FBFF;
            }
            """
        )
        return btn

    def _build_secondary_button(self, text):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: #475569;
                border: none;
                padding: 6px 4px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                color: #0F172A;
            }
            """
        )
        return btn

    def _refresh_filter_buttons(self):
        self.btn_all.setChecked(self.filter_mode == "all")
        self.btn_unread.setChecked(self.filter_mode == "unread")
        label = "Todo el historial" if self.period_days is None else f"Últimos {self.period_days} días"
        self.btn_period.setText(label)

    def _set_filter_mode(self, mode):
        self.filter_mode = str(mode or "all")
        self._refresh_filter_buttons()
        self._apply_filters()

    def _cycle_period_filter(self):
        if self.period_days == 15:
            self.period_days = 30
        elif self.period_days == 30:
            self.period_days = None
        else:
            self.period_days = 15
        self._refresh_filter_buttons()
        self._apply_filters()

    def _clear_history(self):
        self.all_notifications = []
        self.filtered_notifications = []
        self.displayed_count = 0
        self.unread_notifications.clear()
        self._save_notifications_to_file()
        self.unread_count_changed.emit(0)
        self._apply_filters()

    def set_position(self, anchor_global_pos=None):
        if anchor_global_pos is not None:
            try:
                self.move(int(anchor_global_pos.x()), int(anchor_global_pos.y()))
                return
            except Exception:
                pass

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)

    def _filter_notifications(self):
        now = datetime.now()
        result = []
        for notif in self.all_notifications:
            if not isinstance(notif, dict):
                continue
            notif_id = notif.get("id")
            if self.filter_mode == "unread" and notif_id not in self.unread_notifications:
                continue

            if self.period_days is not None:
                dt = self._parse_datetime(notif.get("fecha"))
                if dt is not None and dt < now - timedelta(days=self.period_days):
                    continue

            result.append(notif)
        return result

    def _update_summary(self):
        total = len(self.all_notifications)
        unread = len(self.unread_notifications)
        visible = len(self.filtered_notifications)

        self.stats_total.value_label.setText(str(total))
        self.stats_unread.value_label.setText(str(unread))
        self.stats_visible.value_label.setText(str(visible))

        if total <= 0:
            self.summary_label.setText("Sin actividad reciente")
        elif unread > 0:
            self.summary_label.setText(f"{unread} notificación(es) nueva(s) pendientes")
        else:
            self.summary_label.setText(f"{visible} notificación(es) visibles en esta vista")

    def _apply_filters(self):
        self.filtered_notifications = self._filter_notifications()
        self.displayed_count = 0
        self._update_summary()
        self._render_current_page(reset=True)

    def _render_current_page(self, reset=False):
        if reset:
            while self.scroll_layout.count() > 1:
                item = self.scroll_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        if not self.filtered_notifications:
            empty = QLabel("No hay notificaciones para este filtro.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #94A3B8; padding: 34px 12px; font-size: 13px; font-weight: 600;"
            )
            self.scroll_layout.insertWidget(0, empty)
            return

        end = min(self.displayed_count + self.items_per_load, len(self.filtered_notifications))
        for notif in self.filtered_notifications[self.displayed_count:end]:
            item = NotificationItem(notif)
            item.open_link.connect(self._handle_link_click)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, item)
        self.displayed_count = end

    def load_notifications(self, notifications):
        server_ids = {n.get("id"): n for n in notifications if isinstance(n, dict)}
        history_ids = {n.get("id"): n for n in self.all_notifications if isinstance(n, dict)}

        for notif_id, notif in server_ids.items():
            if notif_id not in history_ids:
                self.all_notifications.insert(0, notif)

        self.all_notifications.sort(key=lambda x: x.get("id", 0), reverse=True)
        if len(self.all_notifications) > 500:
            self.all_notifications = self.all_notifications[:500]

        self._save_notifications_to_file()
        self._apply_filters()

    def _handle_link_click(self, link):
        webbrowser.open(link)

    def add_notification_new(self, notif):
        self._add_to_history(notif)
        notif_id = notif.get("id", str(datetime.now().timestamp()))
        self.unread_notifications.add(notif_id)
        self.unread_count_changed.emit(len(self.unread_notifications))
        self._apply_filters()

    def clear_unread_count(self):
        self.unread_notifications.clear()
        self.unread_count_changed.emit(0)
        self._update_summary()
        if self.filter_mode == "unread":
            self._apply_filters()

    def _load_more_notifications(self):
        if not self.filtered_notifications or self.displayed_count >= len(self.filtered_notifications):
            return
        self._render_current_page(reset=False)

    def _save_notifications_to_file(self):
        try:
            with open(self.NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.all_notifications, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando notificaciones: {e}")

    def _load_notifications_from_file(self):
        try:
            if self.NOTIFICATIONS_FILE.exists():
                if self.NOTIFICATIONS_FILE.stat().st_size <= 0:
                    self.all_notifications = []
                    return
                with open(self.NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
                    self.all_notifications = json.load(f)
        except Exception as e:
            print(f"Error cargando notificaciones: {e}")

    def load_notifications_from_history(self):
        self._apply_filters()
        self.unread_notifications.clear()
        self.unread_count_changed.emit(0)

    def _add_to_history(self, notif):
        self.all_notifications.insert(0, notif)
        if len(self.all_notifications) > 500:
            self.all_notifications = self.all_notifications[:500]
        self._save_notifications_to_file()
