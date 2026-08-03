from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QWidget,
    QScrollArea,
)


_DETACHED_SYNC_CENTER_THREADS = set()


def _release_detached_sync_center_thread(thread):
    try:
        _DETACHED_SYNC_CENTER_THREADS.discard(thread)
    except Exception:
        pass
    try:
        thread.deleteLater()
    except Exception:
        pass


class SyncCenterLoaderThread(QThread):
    loaded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, usuario_id: str, parent=None):
        super().__init__(parent)
        self.usuario_id = str(usuario_id or "").strip()

    def run(self):
        try:
            from utils.sync_manager import get_sync_manager

            state = get_sync_manager().inspect_sync_center_state(self.usuario_id)
            self.loaded.emit(state or {})
        except Exception as e:
            self.failed.emit(str(e))


class SyncCenterDialog(QDialog):
    def __init__(self, username: str = "", user_id: str = "", parent=None):
        super().__init__(parent)
        self.username = str(username or "").strip()
        self.user_id = str(user_id or username or "").strip()
        self._loader_thread = None
        self._summary_widgets = {}
        self._setup_ui()
        self.refresh_state()

    def _setup_ui(self):
        self.setWindowTitle("Centro de sincronización")
        self.setModal(True)
        self.resize(1120, 760)
        self.setMinimumSize(980, 680)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #F4F7FB;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #EEF3FA;
                width: 10px;
                margin: 4px 0 4px 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #C8D6EA;
                min-height: 28px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #B6C8E0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QFrame#Card {
                background-color: #FFFFFF;
                border: 1px solid #E2EAF3;
                border-radius: 20px;
            }
            QLabel#Title {
                color: #142235;
                font-size: 24px;
                font-weight: 800;
            }
            QLabel#Subtitle {
                color: #6F7E90;
                font-size: 12px;
            }
            QLabel#SectionTitle {
                color: #142235;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#InfoBadge {
                background-color: #EAF2FF;
                color: #2458A6;
                border: 1px solid #D2E2FB;
                border-radius: 11px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QFrame#RuleBanner {
                border-radius: 18px;
                border: 1px solid #D7E3F7;
            }
            QLabel#RuleTitle {
                font-size: 14px;
                font-weight: 800;
            }
            QLabel#RuleText {
                font-size: 11px;
                color: #4C5A6C;
            }
            QLabel#SummaryTitle {
                color: #7A8797;
                font-size: 10px;
                font-weight: 700;
            }
            QLabel#SummaryValue {
                color: #122136;
                font-size: 17px;
                font-weight: 800;
            }
            QLabel#SummaryNote {
                color: #6F7E90;
                font-size: 11px;
            }
            QLabel#StatusLine {
                color: #445468;
                font-size: 11px;
                background-color: #F7FAFE;
                border: 1px solid #E1EAF4;
                border-radius: 12px;
                padding: 10px 12px;
            }
            QPushButton {
                border-radius: 14px;
                padding: 11px 18px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#RefreshButton {
                background-color: #2C7BE5;
                color: white;
                border: none;
            }
            QPushButton#RefreshButton:hover {
                background-color: #1E68D2;
            }
            QPushButton#CloseButton {
                background-color: #EEF4FF;
                color: #2458A6;
                border: 1px solid #D7E3F7;
            }
            QPushButton#CloseButton:hover {
                background-color: #E5EFFD;
            }
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2EAF3;
                border-radius: 14px;
                gridline-color: #EDF2F7;
                color: #1F2937;
                font-size: 11px;
                selection-background-color: #E8F0FE;
                selection-color: #132238;
            }
            QHeaderView::section {
                background-color: #F7FAFE;
                color: #516072;
                border: none;
                border-bottom: 1px solid #E2EAF3;
                padding: 10px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(16)
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, stretch=1)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)

        title = QLabel("Centro de sincronización")
        title.setObjectName("Title")
        header_layout.addWidget(title)

        subtitle = QLabel(
            "Compara lo que existe en esta PC contra el snapshot de nube del destino actual antes de sincronizar."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("Subtitle")
        header_layout.addWidget(subtitle)

        self.header_badge = QLabel("Cargando estado")
        self.header_badge.setObjectName("InfoBadge")
        header_layout.addWidget(self.header_badge, alignment=Qt.AlignLeft)
        content_layout.addWidget(header)

        self.rule_banner = QFrame()
        self.rule_banner.setObjectName("RuleBanner")
        rule_layout = QVBoxLayout(self.rule_banner)
        rule_layout.setContentsMargins(18, 16, 18, 16)
        rule_layout.setSpacing(6)

        self.rule_title_label = QLabel("Evaluando protección")
        self.rule_title_label.setObjectName("RuleTitle")
        rule_layout.addWidget(self.rule_title_label)

        self.rule_text_label = QLabel("Consultando si este equipo puede subir o si debe bloquearse por seguridad.")
        self.rule_text_label.setObjectName("RuleText")
        self.rule_text_label.setWordWrap(True)
        rule_layout.addWidget(self.rule_text_label)
        content_layout.addWidget(self.rule_banner)

        summary_wrap = QFrame()
        summary_wrap.setObjectName("Card")
        summary_layout = QGridLayout(summary_wrap)
        summary_layout.setContentsMargins(18, 18, 18, 18)
        summary_layout.setHorizontalSpacing(14)
        summary_layout.setVerticalSpacing(14)

        summary_specs = [
            ("user", "Usuario / Madre"),
            ("target", "Destino actual"),
            ("upload", "Última subida"),
            ("pull", "Último pull"),
            ("queue", "Pendientes"),
            ("cloud", "Nube detectada"),
        ]
        for index, (key, title_text) in enumerate(summary_specs):
            card = self._create_summary_card(title_text)
            summary_layout.addWidget(card["frame"], index // 3, index % 3)
            self._summary_widgets[key] = card
        content_layout.addWidget(summary_wrap)

        self.status_line = QLabel("Consultando estado local y nube...")
        self.status_line.setObjectName("StatusLine")
        self.status_line.setWordWrap(True)
        content_layout.addWidget(self.status_line)

        health_section = self._create_table_section(
            "Panel de salud del sistema",
            "Revisa licencia, nube, caché, sesión, rutas locales, conectividad y archivos clave.",
        )
        self.health_table = self._build_table(
            ["Componente", "Estado", "Detalle"],
            stretch_columns=(2,),
        )
        self.health_table.setMinimumHeight(230)
        health_section["layout"].addWidget(self.health_table)
        content_layout.addWidget(health_section["frame"])

        files_section = self._create_table_section(
            "Estado de archivos críticos",
            "Muestra si los archivos base del sistema y los JSON principales del usuario existen localmente.",
        )
        self.files_table = self._build_table(
            ["Archivo", "Estado", "Modificado", "Ruta"],
            stretch_columns=(3,),
        )
        self.files_table.setMinimumHeight(230)
        files_section["layout"].addWidget(self.files_table)
        content_layout.addWidget(files_section["frame"])

        comparison_section = self._create_table_section(
            "Comparación por dataset",
            "Se compara la carpeta local actual contra el destino cloud que este equipo usaría ahora mismo.",
        )
        self.comparison_table = self._build_table(
            ["Dataset", "Local", "Nube destino", "Diferencia", "Estado", "Ruta local"],
            stretch_columns=(5,),
        )
        self.comparison_table.setMinimumHeight(260)
        comparison_section["layout"].addWidget(self.comparison_table)
        content_layout.addWidget(comparison_section["frame"])

        devices_section = self._create_table_section(
            "Snapshots detectados en nube",
            "Vista resumida por código de dispositivo para verificar si ya existe información remota.",
        )
        self.devices_table = self._build_table(
            ["Código", "Clientes", "Pacientes", "Productos", "Ventas", "Última actualización"],
            stretch_columns=(5,),
        )
        self.devices_table.setMinimumHeight(220)
        devices_section["layout"].addWidget(self.devices_table)
        content_layout.addWidget(devices_section["frame"])

        content_layout.addStretch(1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch()

        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.setObjectName("RefreshButton")
        self.refresh_button.clicked.connect(self.refresh_state)
        footer.addWidget(self.refresh_button)

        close_button = QPushButton("Cerrar")
        close_button.setObjectName("CloseButton")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)

        root.addLayout(footer)

    def _create_summary_card(self, title_text: str):
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel(title_text)
        title.setObjectName("SummaryTitle")
        layout.addWidget(title)

        value = QLabel("...")
        value.setObjectName("SummaryValue")
        value.setWordWrap(True)
        layout.addWidget(value)

        note = QLabel("")
        note.setObjectName("SummaryNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        return {"frame": frame, "value": value, "note": note}

    def _create_table_section(self, title_text: str, subtitle_text: str):
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        return {"frame": frame, "layout": layout}

    def _build_table(self, headers, stretch_columns=()):
        table = QTableWidget(0, len(headers), self)
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        for idx in range(len(headers)):
            mode = QHeaderView.Stretch if idx in stretch_columns else QHeaderView.ResizeToContents
            table.horizontalHeader().setSectionResizeMode(idx, mode)

        return table

    def refresh_state(self):
        if self._loader_thread is not None and self._loader_thread.isRunning():
            return

        self.refresh_button.setEnabled(False)
        self.header_badge.setText("Actualizando")
        self.status_line.setText("Consultando estado local, cola pendiente y snapshots en nube...")

        self._loader_thread = SyncCenterLoaderThread(self.user_id, self)
        self._loader_thread.loaded.connect(self._on_state_loaded)
        self._loader_thread.failed.connect(self._on_state_failed)
        self._loader_thread.finished.connect(self._on_loader_finished)
        self._loader_thread.start()

    def _on_loader_finished(self):
        self.refresh_button.setEnabled(True)
        self._loader_thread = None

    def _format_event(self, event: dict, empty_text: str):
        if not isinstance(event, dict) or not event:
            return empty_text, "Sin registro todavía."

        at = str(event.get("at", "") or "").strip() or empty_text
        source = str(event.get("source", "") or "").strip()
        code = str(event.get("codigo_dispositivo", "") or "").strip()
        message = str(event.get("message", "") or "").strip()
        note_parts = [part for part in (source, code, message) if part]
        return at, " | ".join(note_parts) if note_parts else "Registro local del centro."

    def _set_summary_card(self, key: str, value: str, note: str):
        card = self._summary_widgets.get(key) or {}
        if card.get("value") is not None:
            card["value"].setText(str(value or "-"))
        if card.get("note") is not None:
            card["note"].setText(str(note or ""))

    def _make_item(self, text, align=Qt.AlignLeft | Qt.AlignVCenter, tone=""):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(int(align))

        if tone == "ok":
            item.setForeground(QColor("#257A45"))
        elif tone == "warn":
            item.setForeground(QColor("#B56100"))
        elif tone == "info":
            item.setForeground(QColor("#2458A6"))
        elif tone == "danger":
            item.setForeground(QColor("#B5474F"))

        return item

    def _set_rule_banner(self, tone: str, title: str, text: str):
        palettes = {
            "danger": {
                "bg": "#FFF3F2",
                "border": "#F3D0CB",
                "title": "#B5474F",
                "text": "#6E4B4E",
            },
            "warn": {
                "bg": "#FFF8ED",
                "border": "#F0DDB8",
                "title": "#A66A00",
                "text": "#6A5735",
            },
            "ok": {
                "bg": "#F0F9F2",
                "border": "#CFE7D4",
                "title": "#257A45",
                "text": "#466152",
            },
            "info": {
                "bg": "#EEF5FF",
                "border": "#D4E1F5",
                "title": "#2458A6",
                "text": "#4E5D75",
            },
        }
        palette = palettes.get(tone, palettes["info"])
        self.rule_banner.setStyleSheet(
            f"""
            QFrame#RuleBanner {{
                background-color: {palette['bg']};
                border: 1px solid {palette['border']};
                border-radius: 18px;
            }}
            QLabel#RuleTitle {{
                color: {palette['title']};
                font-size: 14px;
                font-weight: 800;
            }}
            QLabel#RuleText {{
                color: {palette['text']};
                font-size: 11px;
            }}
            """
        )
        self.rule_title_label.setText(str(title or "Estado de protección"))
        self.rule_text_label.setText(str(text or ""))

    def _on_state_loaded(self, state: dict):
        username = str(state.get("username", "") or "").strip() or "No disponible"
        usuario_madre = str(state.get("usuario_madre", "") or "").strip() or "No disponible"
        effective_code = str(state.get("effective_code", "") or "").strip() or "Sin código"
        device_ctx = state.get("device_ctx") if isinstance(state.get("device_ctx"), dict) else {}
        active_branch = state.get("active_branch") if isinstance(state.get("active_branch"), dict) else {}
        queue = state.get("queue") if isinstance(state.get("queue"), dict) else {}
        cloud = state.get("cloud") if isinstance(state.get("cloud"), dict) else {}
        rules = state.get("rules") if isinstance(state.get("rules"), dict) else {}

        branch_label = str(active_branch.get("label", "") or "").strip()
        branch_code = str(active_branch.get("code", "") or "").strip().upper()
        role = str(device_ctx.get("tipo_dispositivo", "madre") or "madre").strip().lower()
        mode = str(device_ctx.get("nube_sync_modo", "carpeta") or "carpeta").strip().lower()

        self.header_badge.setText("Nube verificada" if cloud.get("inspected") else "Nube no verificada")
        self._set_summary_card("user", username, f"Usuario madre: {usuario_madre}")

        target_note_parts = [
            f"Rol: {role}",
            f"Modo: {mode}",
        ]
        if branch_code or branch_label:
            target_note_parts.append(f"Sucursal activa: {branch_label or branch_code}")
        self._set_summary_card("target", effective_code, " | ".join(target_note_parts))

        upload_value, upload_note = self._format_event(state.get("last_upload"), "No registrada")
        self._set_summary_card("upload", upload_value, upload_note)

        pull_value, pull_note = self._format_event(state.get("last_pull"), "No registrado")
        self._set_summary_card("pull", pull_value, pull_note)

        queue_total = int(queue.get("total", 0) or 0)
        queue_note = ", ".join(
            f"{dataset}: {count}"
            for dataset, count in sorted((queue.get("by_dataset") or {}).items())
            if int(count or 0) > 0
        ) or "No hay cambios pendientes."
        self._set_summary_card("queue", str(queue_total), queue_note)

        cloud_devices = cloud.get("devices") if isinstance(cloud.get("devices"), list) else []
        target_last_update = str(cloud.get("target_last_update", "") or "").strip() or "Sin fecha"
        cloud_note = str(cloud.get("message", "") or "").strip() or f"Último cambio del destino: {target_last_update}"
        self._set_summary_card("cloud", str(len(cloud_devices)), cloud_note)

        rule_title = str(rules.get("empty_overwrite_title", "") or "Estado de protección")
        rule_reason = str(rules.get("empty_overwrite_reason", "") or "").strip()
        guard_local = rules.get("guard_local_counts") if isinstance(rules.get("guard_local_counts"), dict) else {}
        guard_cloud = rules.get("guard_cloud_counts") if isinstance(rules.get("guard_cloud_counts"), dict) else {}
        guard_note = (
            f"Local crítico: {guard_local} | Nube crítica: {guard_cloud}"
            if (guard_local or guard_cloud)
            else ""
        )
        if guard_note:
            rule_reason = f"{rule_reason}\n\n{guard_note}" if rule_reason else guard_note
        self._set_rule_banner(
            "danger" if rules.get("empty_overwrite_blocked") else ("warn" if not any(int(v or 0) > 0 for v in (guard_local or {}).values()) else "ok"),
            rule_title,
            rule_reason,
        )

        health = state.get("health") if isinstance(state.get("health"), dict) else {}
        health_items = health.get("items") if isinstance(health.get("items"), list) else []
        self.health_table.setRowCount(len(health_items))
        for row, item in enumerate(health_items):
            tone = str(item.get("tone", "") or "")
            self.health_table.setItem(row, 0, self._make_item(str(item.get("component", "") or "")))
            self.health_table.setItem(row, 1, self._make_item(str(item.get("status", "") or ""), Qt.AlignCenter, tone))
            self.health_table.setItem(row, 2, self._make_item(str(item.get("detail", "") or ""), Qt.AlignLeft | Qt.AlignVCenter, tone))

        critical_files = health.get("critical_files") if isinstance(health.get("critical_files"), list) else []
        self.files_table.setRowCount(len(critical_files))
        for row, item in enumerate(critical_files):
            tone = str(item.get("tone", "") or "")
            self.files_table.setItem(row, 0, self._make_item(str(item.get("label", "") or "")))
            self.files_table.setItem(row, 1, self._make_item(str(item.get("status", "") or ""), Qt.AlignCenter, tone))
            self.files_table.setItem(row, 2, self._make_item(str(item.get("modified_at", "") or "Sin fecha")))
            self.files_table.setItem(row, 3, self._make_item(str(item.get("path", "") or "")))

        status_parts = [
            f"Internet: {'sí' if state.get('internet_ok') else 'no'}",
            f"Destino actual: {effective_code}",
            f"Snapshots detectados: {int(cloud.get('device_count', 0) or 0)}",
        ]
        local_last_change = str((state.get("local") or {}).get("last_local_change", "") or "").strip()
        if local_last_change:
            status_parts.append(f"Último cambio local: {local_last_change}")
        self.status_line.setText(" | ".join(status_parts))

        comparison = state.get("comparison") if isinstance(state.get("comparison"), list) else []
        self.comparison_table.setRowCount(len(comparison))
        for row, item in enumerate(comparison):
            dataset_label = str(item.get("label", "") or "")
            local_count = int(item.get("local_count", 0) or 0)
            cloud_count = int(item.get("cloud_count", 0) or 0)
            delta = int(item.get("delta", 0) or 0)
            delta_text = f"{delta:+d}"
            tone = str(item.get("tone", "") or "")

            self.comparison_table.setItem(row, 0, self._make_item(dataset_label))
            self.comparison_table.setItem(row, 1, self._make_item(local_count, Qt.AlignCenter, tone))
            self.comparison_table.setItem(row, 2, self._make_item(cloud_count, Qt.AlignCenter, tone))
            self.comparison_table.setItem(row, 3, self._make_item(delta_text, Qt.AlignCenter, tone))
            self.comparison_table.setItem(row, 4, self._make_item(str(item.get("status", "") or ""), Qt.AlignCenter, tone))
            self.comparison_table.setItem(row, 5, self._make_item(str(item.get("path", "") or "")))

        self.devices_table.setRowCount(len(cloud_devices))
        for row, device in enumerate(cloud_devices):
            counts = device.get("counts") if isinstance(device.get("counts"), dict) else {}
            self.devices_table.setItem(row, 0, self._make_item(str(device.get("codigo_dispositivo", "") or "")))
            self.devices_table.setItem(row, 1, self._make_item(int(counts.get("clientes", 0) or 0), Qt.AlignCenter))
            self.devices_table.setItem(row, 2, self._make_item(int(counts.get("pacientes", 0) or 0), Qt.AlignCenter))
            self.devices_table.setItem(row, 3, self._make_item(int(counts.get("productos", 0) or 0), Qt.AlignCenter))
            self.devices_table.setItem(row, 4, self._make_item(int(counts.get("ventas", 0) or 0), Qt.AlignCenter))
            self.devices_table.setItem(row, 5, self._make_item(str(device.get("last_update", "") or "Sin fecha")))

    def _on_state_failed(self, error_message: str):
        self.header_badge.setText("Error")
        self._set_rule_banner("danger", "No se pudo evaluar la regla", error_message)
        self.status_line.setText(f"No se pudo cargar el centro de sincronización: {error_message}")
        self.health_table.setRowCount(0)
        self.files_table.setRowCount(0)

    def closeEvent(self, event):
        try:
            if self._loader_thread is not None and self._loader_thread.isRunning():
                try:
                    self._loader_thread.requestInterruption()
                except Exception:
                    pass
                try:
                    self._loader_thread.quit()
                except Exception:
                    pass
                if not self._loader_thread.wait(800):
                    try:
                        self._loader_thread.setParent(None)
                    except Exception:
                        pass
                    _DETACHED_SYNC_CENTER_THREADS.add(self._loader_thread)
                    try:
                        self._loader_thread.finished.connect(
                            lambda t=self._loader_thread: _release_detached_sync_center_thread(t)
                        )
                    except Exception:
                        pass
                else:
                    try:
                        self._loader_thread.deleteLater()
                    except Exception:
                        pass
            self._loader_thread = None
        except Exception:
            pass
        super().closeEvent(event)
