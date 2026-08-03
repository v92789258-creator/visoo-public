import datetime
import json
from pathlib import Path

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from utils.file_handler import (
    get_active_branch_context,
    get_branch_cache_data_dir,
    get_effective_branch_context,
)


BASIC_WINDOW_STYLE = """
QWidget {
    background: #F7F4EC;
    color: #102A43;
    font-size: 18px;
}
QLabel {
    color: #243B53;
}
QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit {
    background: #FFFDF8;
    border: 2px solid #BCCCDC;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 19px;
    color: #102A43;
    min-height: 32px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 2px solid #2563EB;
    background: white;
}
QPushButton {
    min-height: 50px;
    border-radius: 13px;
    font-size: 18px;
    font-weight: 700;
    padding: 8px 16px;
}
QTableWidget {
    background: white;
    border: 2px solid #D9E2EC;
    border-radius: 16px;
    gridline-color: #E2E8F0;
    font-size: 17px;
}
QHeaderView::section {
    background: #0F172A;
    color: white;
    padding: 11px;
    border: none;
    font-size: 16px;
    font-weight: 700;
}
QTableWidget::item {
    padding: 8px;
}
QGroupBox {
    background: white;
    border: 2px solid #D9E2EC;
    border-radius: 16px;
    margin-top: 16px;
    padding-top: 16px;
    font-size: 20px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 7px;
}
"""


def safe_float(value, default=0.0):
    try:
        text = str(value if value is not None else default)
        text = text.replace("S/.", "").replace("S/", "").replace(",", "").strip()
        return float(text or default)
    except (TypeError, ValueError):
        return float(default)


def safe_int(value, default=0):
    try:
        return int(float(str(value if value is not None else default).replace(",", "").strip()))
    except (TypeError, ValueError):
        return int(default)


def sale_total_safe(sale):
    if not isinstance(sale, dict):
        return 0.0
    total = safe_float(sale.get("total"))
    if total <= 0:
        total = safe_float(sale.get("monto_total_venta"))
    if total > 0:
        return total

    total = 0.0
    items = sale.get("items", []) or []
    if not isinstance(items, list):
        return 0.0
    for item in items:
        if not isinstance(item, dict):
            continue
        item_total = safe_float(item.get("total"))
        if item_total <= 0:
            item_total = safe_float(item.get("subtotal"))
        if item_total <= 0:
            quantity = max(safe_float(item.get("cantidad"), 1.0), 0.0)
            price = safe_float(item.get("precio_unitario", item.get("precio", 0)))
            item_total = quantity * price
        total += item_total
    return round(max(total, 0.0), 2)


def parse_date_safe(value):
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)

    text = str(value or "").strip()
    if not text:
        return None

    normalized = text.replace("T", " ").replace("Z", "").strip()
    formats = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return datetime.datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def date_in_filter(value, filter_key="today", specific_date=None):
    dt = parse_date_safe(value)
    if dt is None:
        return False

    target = dt.date()
    today = datetime.date.today()
    key = str(filter_key or "all").strip().lower()
    if key == "all":
        return True
    if key == "today":
        return target == today
    if key == "specific":
        return target == (specific_date or today)

    this_monday = today - datetime.timedelta(days=today.weekday())
    if key == "this_week":
        return this_monday <= target <= today
    if key == "previous_week":
        previous_monday = this_monday - datetime.timedelta(days=7)
        previous_sunday = this_monday - datetime.timedelta(days=1)
        return previous_monday <= target <= previous_sunday
    if key == "tomorrow":
        return target == today + datetime.timedelta(days=1)
    return True


def current_branch_code(parent_app, username):
    try:
        code = str(getattr(parent_app, "selected_branch_code", "") or "").strip().upper()
        if code:
            return code
    except Exception:
        pass
    for resolver in (get_active_branch_context, get_effective_branch_context):
        try:
            ctx = resolver(username or "") or {}
            code = str(ctx.get("code", "") or "").strip().upper()
            if code:
                return code
        except Exception:
            continue
    return ""


def record_matches_branch(record, branch_code):
    if not branch_code:
        return True
    if not isinstance(record, dict):
        return False
    expected = str(branch_code or "").strip().upper()
    for key in (
        "branch_code",
        "codigo_dispositivo",
        "source_branch_code",
        "target_branch_code",
        "inventory_applied_branch_code",
    ):
        value = str(record.get(key, "") or "").strip().upper()
        if value:
            return value == expected
    meta = record.get("_meta")
    if isinstance(meta, dict):
        value = str(meta.get("branch_code", "") or meta.get("codigo_dispositivo", "") or "").strip().upper()
        if value:
            return value == expected
    # Archivos antiguos no siempre incluian la sucursal en cada registro.
    # Si el archivo ya fue resuelto por contexto, no debemos ocultarlos.
    return True


def load_scoped_list(parent_app, username, filename, fallback_loader):
    branch_code = current_branch_code(parent_app, username)
    if branch_code and username:
        try:
            path = get_branch_cache_data_dir(username, branch_code) / filename
            if path.exists():
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, list):
                    return [item for item in data if isinstance(item, dict)], branch_code
        except Exception:
            pass

    try:
        data = fallback_loader(username) or []
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    records = [item for item in data if isinstance(item, dict)]
    if branch_code:
        records = [item for item in records if record_matches_branch(item, branch_code)]
    return records, branch_code


def make_button(text, color="#2563EB", hover="#1D4ED8"):
    button = QtWidgets.QPushButton(text)
    button.setStyleSheet(
        "QPushButton {"
        f"background: {color}; color: white; border: 3px solid {hover};"
        "}"
        f"QPushButton:hover {{ background: {hover}; }}"
        "QPushButton:disabled { background: #94A3B8; border-color: #64748B; }"
    )
    return button


def set_button_busy(button, busy, normal_text=None, busy_text="Guardando"):
    if button is None:
        return
    if normal_text is not None:
        button._basic_normal_text = str(normal_text)
    elif not hasattr(button, "_basic_normal_text"):
        button._basic_normal_text = str(button.text() or "")

    timer = getattr(button, "_basic_busy_timer", None)
    if timer is None:
        timer = QtCore.QTimer(button)
        timer.setInterval(300)
        button._basic_busy_step = 0

        def animate():
            button._basic_busy_step = (button._basic_busy_step + 1) % 4
            base = str(getattr(button, "_basic_busy_text", "Guardando") or "Guardando")
            button.setText(base + ("." * button._basic_busy_step))

        timer.timeout.connect(animate)
        button._basic_busy_timer = timer

    if busy:
        button._basic_busy_text = str(busy_text or "Guardando")
        button._basic_busy_step = 0
        button.setEnabled(False)
        button.setText(button._basic_busy_text)
        timer.start()
    else:
        timer.stop()
        button.setEnabled(True)
        button.setText(str(getattr(button, "_basic_normal_text", "") or ""))


class BasicDataWorker(QtCore.QThread):
    loaded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, loader, parent=None):
        super().__init__(parent)
        self.loader = loader

    def run(self):
        try:
            result = self.loader()
            if not self.isInterruptionRequested():
                self.loaded.emit(result)
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))


class BasicLoadingPanel(QFrame):
    def __init__(self, text="Cargando...", parent=None):
        super().__init__(parent)
        self._base_text = str(text or "Cargando...")
        self._step = 0
        self.setStyleSheet(
            "QFrame { background: #F7F4EC; }"
            "QLabel { color: #0F172A; font-size: 28px; font-weight: 800; }"
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.label = QLabel(self._base_text)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(350)
        self.timer.timeout.connect(self._animate)

    def start(self, text=None):
        if text:
            self._base_text = str(text)
        self._step = 0
        self.label.setText(self._base_text)
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def _animate(self):
        self._step = (self._step + 1) % 4
        self.label.setText(self._base_text + ("." * self._step))


class BasicWindowBase(QWidget):
    def __init__(self, parent_app=None, title="Modo Basico", subtitle="", loader_text="Cargando..."):
        super().__init__(None)
        self.parent_app = parent_app
        self.username = getattr(parent_app, "username", None)
        self._worker = None
        self._closed = False
        self._embedded_mode = False
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._apply_window_mode()
        self.setWindowTitle(title)
        self.resize(1280, 800)
        self.setStyleSheet(BASIC_WINDOW_STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 20)
        outer.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 34px; font-weight: 800; color: #0B1F33;")
        outer.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("font-size: 19px; color: #486581;")
            subtitle_label.setWordWrap(True)
            outer.addWidget(subtitle_label)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(14)
        self.stack.addWidget(self.content)

        self.loading_panel = BasicLoadingPanel(loader_text)
        self.stack.addWidget(self.loading_panel)

    def _apply_window_mode(self):
        if self._embedded_mode:
            self.setWindowFlags(Qt.Widget)
        else:
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowTitleHint
                | Qt.WindowSystemMenuHint
                | Qt.WindowCloseButtonHint
                | Qt.WindowMinMaxButtonsHint
            )

    def set_embedded_mode(self, embedded=True):
        self._embedded_mode = bool(embedded)
        self._apply_window_mode()
        self.showNormal()

    def exit_basic_page(self):
        if self._embedded_mode and self.parent_app is not None and hasattr(self.parent_app, "go_to_home"):
            self.parent_app.go_to_home()
            return
        self.close()

    def show_loading(self, text="Cargando..."):
        self.loading_panel.start(text)
        self.stack.setCurrentWidget(self.loading_panel)

    def hide_loading(self):
        self.loading_panel.stop()
        self.stack.setCurrentWidget(self.content)

    def load_async(self, loader, on_success, loading_text="Cargando...", on_error=None):
        if self._worker is not None and self._worker.isRunning():
            return False
        self.show_loading(loading_text)
        worker = BasicDataWorker(loader, self)
        self._worker = worker

        def handle_success(result):
            if self._closed:
                return
            try:
                on_success(result)
            except Exception as exc:
                if on_error is not None:
                    on_error(str(exc))
                else:
                    QtWidgets.QMessageBox.warning(
                        self,
                        self.windowTitle(),
                        f"No se pudieron procesar los datos.\n\n{exc}",
                    )
            finally:
                self.hide_loading()

        def handle_error(message):
            if self._closed:
                return
            self.hide_loading()
            if on_error is not None:
                on_error(message)
            else:
                QtWidgets.QMessageBox.warning(self, self.windowTitle(), f"No se pudieron cargar los datos.\n\n{message}")

        worker.loaded.connect(handle_success)
        worker.failed.connect(handle_error)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: setattr(self, "_worker", None))
        worker.start()
        return True

    def showEvent(self, event):
        super().showEvent(event)
        self._closed = False
        if self._embedded_mode:
            return
        try:
            screen = QtWidgets.QApplication.screenAt(self.mapToGlobal(self.rect().center()))
            if screen is None:
                screen = QtWidgets.QApplication.primaryScreen()
            if screen is not None:
                geometry = self.frameGeometry()
                geometry.moveCenter(screen.availableGeometry().center())
                self.move(geometry.topLeft())
        except Exception:
            pass

    def closeEvent(self, event):
        self._closed = True
        self.loading_panel.stop()
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            if not worker.wait(600):
                worker.setParent(None)
        super().closeEvent(event)
