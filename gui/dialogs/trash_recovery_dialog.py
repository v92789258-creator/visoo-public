import json

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from utils.trash_manager import DATASET_LABELS, list_trash_entries, purge_trash_entry, restore_trash_entry


class TrashRecoveryDialog(QDialog):
    def __init__(self, username: str = "", user_id: str = "", parent=None):
        super().__init__(parent)
        self.username = str(username or "").strip()
        self.user_ref = str(user_id or username or "").strip()
        self._entries = []
        self._setup_ui()
        self.refresh_entries()

    def _setup_ui(self):
        self.setWindowTitle("Papelera y recuperacion")
        self.setModal(True)
        self.resize(1140, 760)
        self.setMinimumSize(980, 680)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #F4F7FB;
            }
            QFrame#Card {
                background-color: #FFFFFF;
                border: 1px solid #E2EAF3;
                border-radius: 18px;
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
                background-color: #EEF5FF;
                color: #2458A6;
                border: 1px solid #D4E1F5;
                border-radius: 11px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#MetaLabel {
                color: #516072;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#MetaValue {
                color: #122136;
                font-size: 12px;
            }
            QComboBox, QPushButton {
                border-radius: 12px;
                min-height: 38px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 700;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #D6E1EE;
                color: #122136;
            }
            QPushButton#PrimaryButton {
                background-color: #2C7BE5;
                color: white;
                border: none;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #1E68D2;
            }
            QPushButton#DangerButton {
                background-color: #FFF3F2;
                color: #B5474F;
                border: 1px solid #F3D0CB;
            }
            QPushButton#DangerButton:hover {
                background-color: #FFE7E4;
            }
            QPushButton#GhostButton {
                background-color: #EEF4FF;
                color: #2458A6;
                border: 1px solid #D7E3F7;
            }
            QPushButton#GhostButton:hover {
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
            QTextEdit {
                background-color: #F8FBFF;
                border: 1px solid #E2EAF3;
                border-radius: 14px;
                padding: 10px;
                color: #1F2937;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 11px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)

        title = QLabel("Papelera y recuperacion")
        title.setObjectName("Title")
        header_layout.addWidget(title)

        subtitle = QLabel(
            "Recupera pacientes, productos y ventas eliminados. La restauracion respeta la sucursal original cuando corresponde."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)

        self.count_badge = QLabel("0 elementos")
        self.count_badge.setObjectName("InfoBadge")
        header_layout.addWidget(self.count_badge, alignment=Qt.AlignLeft)
        root.addWidget(header)

        toolbar = QFrame()
        toolbar.setObjectName("Card")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(18, 14, 18, 14)
        toolbar_layout.setSpacing(10)

        filter_label = QLabel("Filtrar:")
        filter_label.setObjectName("MetaLabel")
        toolbar_layout.addWidget(filter_label)

        self.dataset_filter = QComboBox()
        self.dataset_filter.addItem("Todo", "")
        self.dataset_filter.addItem("Pacientes", "pacientes")
        self.dataset_filter.addItem("Productos", "productos")
        self.dataset_filter.addItem("Ventas", "ventas")
        self.dataset_filter.currentIndexChanged.connect(self.refresh_entries)
        toolbar_layout.addWidget(self.dataset_filter, stretch=1)

        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.setObjectName("GhostButton")
        self.refresh_button.clicked.connect(self.refresh_entries)
        toolbar_layout.addWidget(self.refresh_button)
        root.addWidget(toolbar)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        root.addWidget(splitter, stretch=1)

        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(18, 16, 18, 18)
        left_layout.setSpacing(10)

        left_title = QLabel("Elementos eliminados")
        left_title.setObjectName("SectionTitle")
        left_layout.addWidget(left_title)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["Tipo", "Resumen", "Borrado", "Sucursal", "Origen"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._update_preview)
        left_layout.addWidget(self.table, stretch=1)
        splitter.addWidget(left_panel)

        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(18, 16, 18, 18)
        right_layout.setSpacing(12)

        right_title = QLabel("Vista previa")
        right_title.setObjectName("SectionTitle")
        right_layout.addWidget(right_title)

        meta_grid = QVBoxLayout()
        meta_grid.setSpacing(8)

        self.meta_dataset = self._build_meta_row("Tipo")
        self.meta_deleted = self._build_meta_row("Eliminado")
        self.meta_branch = self._build_meta_row("Sucursal")
        self.meta_source = self._build_meta_row("Origen")
        for row in (self.meta_dataset, self.meta_deleted, self.meta_branch, self.meta_source):
            meta_grid.addWidget(row["widget"])
        right_layout.addLayout(meta_grid)

        self.preview = QTextEdit(self)
        self.preview.setReadOnly(True)
        right_layout.addWidget(self.preview, stretch=1)
        splitter.addWidget(right_panel)
        splitter.setSizes([680, 360])

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch()

        self.restore_button = QPushButton("Restaurar seleccionado")
        self.restore_button.setObjectName("PrimaryButton")
        self.restore_button.setEnabled(False)
        self.restore_button.clicked.connect(self._restore_selected)
        footer.addWidget(self.restore_button)

        self.purge_button = QPushButton("Eliminar definitivamente")
        self.purge_button.setObjectName("DangerButton")
        self.purge_button.setEnabled(False)
        self.purge_button.clicked.connect(self._purge_selected)
        footer.addWidget(self.purge_button)

        close_button = QPushButton("Cerrar")
        close_button.setObjectName("GhostButton")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)

        root.addLayout(footer)

    def _build_meta_row(self, label_text: str):
        row_widget = QWidget(self)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("MetaLabel")
        value = QLabel("-")
        value.setObjectName("MetaValue")
        value.setWordWrap(True)

        row_layout.addWidget(label)
        row_layout.addWidget(value, stretch=1)
        return {"widget": row_widget, "value": value}

    def _make_item(self, text: str, tone: str = ""):
        item = QTableWidgetItem(str(text or ""))
        if tone == "patients":
            item.setForeground(QColor("#2458A6"))
        elif tone == "products":
            item.setForeground(QColor("#257A45"))
        elif tone == "sales":
            item.setForeground(QColor("#B56100"))
        return item

    def refresh_entries(self):
        dataset = self.dataset_filter.currentData()
        self._entries = list_trash_entries(self.user_ref, dataset=str(dataset or ""))
        self.count_badge.setText(f"{len(self._entries)} elemento(s)")

        self.table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            dataset_key = str(entry.get("dataset", "") or "").strip().lower()
            tone = {
                "pacientes": "patients",
                "productos": "products",
                "ventas": "sales",
            }.get(dataset_key, "")

            branch_text = str(entry.get("branch_label", "") or entry.get("branch_code", "") or "Base local").strip()
            source_text = str(entry.get("source", "") or "-").strip()

            self.table.setItem(row, 0, self._make_item(str(entry.get("dataset_label", "") or DATASET_LABELS.get(dataset_key, dataset_key.title())), tone))
            self.table.setItem(row, 1, self._make_item(str(entry.get("summary", "") or "")))
            self.table.setItem(row, 2, self._make_item(str(entry.get("deleted_at", "") or "")))
            self.table.setItem(row, 3, self._make_item(branch_text))
            self.table.setItem(row, 4, self._make_item(source_text))
            self.table.item(row, 0).setData(Qt.UserRole, str(entry.get("trash_id", "") or ""))

        if self._entries:
            self.table.selectRow(0)
        else:
            self._clear_preview()

    def _selected_entry(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._entries):
            return None
        return self._entries[row]

    def _clear_preview(self):
        self.meta_dataset["value"].setText("-")
        self.meta_deleted["value"].setText("-")
        self.meta_branch["value"].setText("-")
        self.meta_source["value"].setText("-")
        self.preview.setPlainText("No hay un elemento seleccionado.")
        self.restore_button.setEnabled(False)
        self.purge_button.setEnabled(False)

    def _update_preview(self):
        entry = self._selected_entry()
        if not entry:
            self._clear_preview()
            return

        branch_text = str(entry.get("branch_label", "") or entry.get("branch_code", "") or "Base local").strip()
        self.meta_dataset["value"].setText(str(entry.get("dataset_label", "") or "-"))
        self.meta_deleted["value"].setText(str(entry.get("deleted_at", "") or "-"))
        self.meta_branch["value"].setText(branch_text)
        self.meta_source["value"].setText(str(entry.get("source", "") or "-"))

        record = entry.get("record")
        try:
            preview_text = json.dumps(record, indent=2, ensure_ascii=False)
        except Exception:
            preview_text = str(record)
        self.preview.setPlainText(preview_text)
        self.restore_button.setEnabled(True)
        self.purge_button.setEnabled(True)

    def _restore_selected(self):
        entry = self._selected_entry()
        if not entry:
            return

        summary = str(entry.get("summary", "") or "este elemento").strip()
        confirm = QMessageBox.question(
            self,
            "Restaurar elemento",
            f"Deseas restaurar:\n\n{summary}\n\nEl registro volvera a su dataset operativo.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        ok, message = restore_trash_entry(self.user_ref, str(entry.get("trash_id", "") or ""))
        if ok:
            QMessageBox.information(self, "Restaurado", message)
            self.refresh_entries()
            return
        QMessageBox.warning(self, "No se pudo restaurar", message)

    def _purge_selected(self):
        entry = self._selected_entry()
        if not entry:
            return

        summary = str(entry.get("summary", "") or "este elemento").strip()
        confirm = QMessageBox.question(
            self,
            "Eliminar definitivamente",
            f"Esto borrara de la papelera:\n\n{summary}\n\nNo se podra recuperar despues.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        ok, message = purge_trash_entry(self.user_ref, str(entry.get("trash_id", "") or ""))
        if ok:
            QMessageBox.information(self, "Papelera", message)
            self.refresh_entries()
            return
        QMessageBox.warning(self, "No se pudo eliminar", message)

