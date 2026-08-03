import datetime
import json

from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import (
    QAction,
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.file_handler import (
    cargar_pacientes,
    cargar_ventas,
    get_active_branch_context,
    get_branch_cache_data_dir,
    get_effective_branch_context,
    guardar_pacientes,
    guardar_ventas,
    get_user_file_path,
)


class _ContractPdfWorker(QObject):
    finished = pyqtSignal(str, str, bool)

    def __init__(self, paciente_data, graduacion, nombre_optica, username, contract_number, open_in_browser):
        super().__init__()
        self._paciente_data = paciente_data
        self._graduacion = graduacion
        self._nombre_optica = nombre_optica
        self._username = username
        self._contract_number = contract_number
        self._open_in_browser = bool(open_in_browser)

    def run(self):
        try:
            from utils.generador_contrato import generar_contrato_pdf_logic

            pdf_path = generar_contrato_pdf_logic(
                paciente_data=self._paciente_data,
                graduacion=self._graduacion,
                nombre_optica=self._nombre_optica,
                username=self._username,
                contract_number=self._contract_number,
                parent_widget=None,
                open_in_browser=self._open_in_browser,
                return_pdf_path_only=True,
            )
            self.finished.emit(str(pdf_path or ""), "", self._open_in_browser)
        except Exception as e:
            self.finished.emit("", str(e), self._open_in_browser)


class ContractAnnulDialog(QDialog):
    def __init__(self, contract_number="", has_active_debt=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Motivo de anulación")
        self.setModal(True)
        self.resize(460, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(f"Contrato {str(contract_number or '').strip()}")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #222;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Indica por qué se está anulando. Puedes omitirlo si no deseas registrar un motivo."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(subtitle)

        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText("Escriba el motivo de la anulación...")
        self.reason_edit.setMinimumHeight(120)
        self.reason_edit.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #D9DDE3;
                border-radius: 6px;
                padding: 8px;
                background: white;
                font-size: 13px;
            }
            """
        )
        layout.addWidget(self.reason_edit)

        self.debt_checkbox = None
        if has_active_debt:
            self.debt_checkbox = QCheckBox("Anular deuda")
            self.debt_checkbox.setChecked(False)
            self.debt_checkbox.setStyleSheet("font-size: 13px; color: #333;")
            layout.addWidget(self.debt_checkbox)

        buttons = QDialogButtonBox()
        self.btn_skip = buttons.addButton("Omitir", QDialogButtonBox.ActionRole)
        self.btn_ok = buttons.addButton("OK", QDialogButtonBox.AcceptRole)
        self.btn_cancel = buttons.addButton("Cancelar", QDialogButtonBox.RejectRole)
        self.btn_skip.clicked.connect(self._accept_without_reason)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        for btn in (self.btn_skip, self.btn_ok, self.btn_cancel):
            btn.setMinimumHeight(34)
        layout.addWidget(buttons)

        self._omit_reason = False

    def _accept_without_reason(self):
        self._omit_reason = True
        self.accept()

    def get_reason(self):
        if self._omit_reason:
            return ""
        return str(self.reason_edit.toPlainText() or "").strip()

    def should_annul_debt(self):
        return bool(self.debt_checkbox and self.debt_checkbox.isChecked())


class MissingContractsDialog(QDialog):
    def __init__(self, page, entries, parent=None):
        super().__init__(parent)
        self.page = page
        self.entries = list(entries or [])
        self.setWindowTitle("Contratos no registrados")
        self.resize(780, 520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Contratos no registrados")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #222;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Aquí se muestran los números faltantes en la secuencia. Puedes anularlos para dejar trazabilidad."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(subtitle)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Contrato", "Estado", "Fecha anulación", "Motivo", "Acciones"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 165)
        self.table.setColumnWidth(4, 80)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.refresh_entries(self.entries)

    def refresh_entries(self, entries):
        self.entries = list(entries or [])
        self.table.setRowCount(0)
        for entry in self.entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(entry.get("numero", "") or "").strip()))
            estado = str(entry.get("estado", "pendiente") or "pendiente").strip().lower()
            estado_label = "Anulado" if estado == "anulado" else "Pendiente"
            estado_item = QTableWidgetItem(estado_label)
            if estado == "anulado":
                estado_item.setForeground(Qt.gray)
            self.table.setItem(row, 1, estado_item)
            self.table.setItem(row, 2, QTableWidgetItem(str(entry.get("fecha_anulacion", "") or "").strip()))
            self.table.setItem(row, 3, QTableWidgetItem(str(entry.get("motivo_anulacion", "") or "").strip()))

            btn_actions = QPushButton("...")
            btn_actions.setFixedWidth(40)
            btn_actions.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    font-weight: bold;
                    font-size: 18px;
                    color: #666666;
                    border: none;
                }
                QPushButton:hover {
                    color: #191919;
                    background-color: #F0F0F0;
                    border-radius: 4px;
                }
                """
            )
            btn_actions.clicked.connect(lambda _checked=False, data=entry: self._show_entry_menu(data))
            self.table.setCellWidget(row, 4, btn_actions)

    def _show_entry_menu(self, entry):
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: white;
                border: 1px solid #E0E0E0;
            }
            QMenu::item {
                padding: 8px 24px;
            }
            QMenu::item:selected {
                background-color: #F0F0F0;
                color: black;
            }
            """
        )
        already_annulled = str(entry.get("estado", "") or "").strip().lower() == "anulado"

        anular_action = QAction("ANULAR CONTRATO", self)
        anular_action.setEnabled(not already_annulled)
        anular_action.triggered.connect(lambda: self._annul_missing_contract(entry))
        menu.addAction(anular_action)

        if already_annulled:
            reason_action = QAction("VER MOTIVO", self)
            reason_action.triggered.connect(
                lambda: QMessageBox.information(
                    self,
                    "Motivo de anulación",
                    str(entry.get("motivo_anulacion", "") or "Sin motivo registrado."),
                )
            )
            menu.addAction(reason_action)

        btn = self.sender()
        if btn:
            menu.exec_(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _annul_missing_contract(self, entry):
        if self.page is None:
            return
        if self.page._annul_missing_contract_entry(entry):
            self.refresh_entries(self.page._build_missing_contract_entries())


class ContractsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.parent_app = parent
        self.username = getattr(parent, "username", None)
        self.all_contracts = []
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self.filter_contracts)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        title = QLabel("Contratos")
        title.setStyleSheet(
            """
            QLabel {
                font-size: 24px;
                font-weight: normal;
                color: #333333;
            }
            """
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_back = QPushButton("Volver a Pacientes")
        btn_back.setFixedWidth(150)
        btn_back.setFixedHeight(36)
        btn_back.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                color: black;
                border: 1px solid #191919;
                border-radius: 0px;
                padding: 8px 16px;
                font-weight: normal;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            """
        )
        btn_back.clicked.connect(self.go_back)
        header_layout.addWidget(btn_back)

        btn_missing_contracts = QPushButton("Anular contratos no registrados")
        btn_missing_contracts.setFixedWidth(230)
        btn_missing_contracts.setFixedHeight(36)
        btn_missing_contracts.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                color: black;
                border: 1px solid #191919;
                border-radius: 0px;
                padding: 8px 16px;
                font-weight: normal;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            """
        )
        btn_missing_contracts.clicked.connect(self.open_missing_contracts_dialog)
        header_layout.addWidget(btn_missing_contracts)
        layout.addLayout(header_layout)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nro. contrato, nombre o DNI...")
        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 14px;
                background-color: white;
            }
            """
        )
        self.search_input.textChanged.connect(self._schedule_filter_contracts)
        search_layout.addWidget(self.search_input)

        btn_refresh = QPushButton("Actualizar")
        btn_refresh.setFixedWidth(100)
        btn_refresh.setFixedHeight(36)
        btn_refresh.setStyleSheet(
            """
            QPushButton {
                background-color: #191919;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
            """
        )
        btn_refresh.clicked.connect(self.load_contracts)
        search_layout.addWidget(btn_refresh)
        layout.addLayout(search_layout)

        self.contracts_table = QTableWidget()
        self.contracts_table.setColumnCount(8)
        self.contracts_table.setHorizontalHeaderLabels(
            ["Nro. Contrato", "Fecha", "Paciente", "DNI", "Total", "Pagado", "Faltante", "Acciones"]
        )

        header = self.contracts_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.contracts_table.setColumnWidth(0, 120)
        self.contracts_table.setColumnWidth(1, 150)
        self.contracts_table.setColumnWidth(3, 100)
        self.contracts_table.setColumnWidth(7, 80)
        self.contracts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.contracts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.contracts_table.verticalHeader().setVisible(False)
        self.contracts_table.setStyleSheet(
            """
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #E0E0E0;
                font-weight: bold;
            }
            """
        )
        layout.addWidget(self.contracts_table)

        self.stats_label = QLabel("Total contratos: 0")
        self.stats_label.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(self.stats_label)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, self.load_contracts)

    def _schedule_filter_contracts(self, *_args):
        self._filter_timer.start(450)

    @staticmethod
    def _extract_contract_sequence(value):
        digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
        if not digits:
            return 0
        try:
            return int(digits)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _format_contract_sequence(value):
        try:
            return f"{max(1, int(value or 1)):07d}"
        except (TypeError, ValueError):
            return "0000001"

    def _get_missing_contracts_file_path(self):
        return get_user_file_path(self.username or "", "contratos_no_registrados_anulados.json")

    def _get_selected_branch_code(self):
        try:
            parent = getattr(self, "parent_app", None)
            if parent is not None and hasattr(parent, "selected_branch_code"):
                return str(getattr(parent, "selected_branch_code", "") or "").strip().upper()
        except Exception:
            pass

        try:
            ctx = get_active_branch_context(self.username or "") or {}
            code = str(ctx.get("code", "") or "").strip().upper()
            if code:
                return code
        except Exception:
            pass

        try:
            ctx = get_effective_branch_context(self.username or "") or {}
            return str(ctx.get("code", "") or "").strip().upper()
        except Exception:
            return ""

    def _load_context_list(self, filename, loader):
        branch_code = self._get_selected_branch_code()
        if branch_code and self.username:
            try:
                fp = get_branch_cache_data_dir(self.username, branch_code) / filename
                if fp.exists():
                    with open(fp, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if isinstance(data, list):
                        return data, True
            except Exception:
                pass
        try:
            data = loader(self.username) or []
        except Exception:
            data = []
        return data if isinstance(data, list) else [], False

    @staticmethod
    def _record_matches_branch(record, branch_code):
        if not branch_code:
            return True
        if not isinstance(record, dict):
            return False
        branch_code = str(branch_code or "").strip().upper()
        for key in (
            "branch_code",
            "codigo_dispositivo",
            "source_branch_code",
            "target_branch_code",
            "inventory_applied_branch_code",
        ):
            value = str(record.get(key, "") or "").strip().upper()
            if value and value == branch_code:
                return True
        meta = record.get("_meta")
        if isinstance(meta, dict):
            value = str(meta.get("branch_code", "") or meta.get("codigo_dispositivo", "") or "").strip().upper()
            if value and value == branch_code:
                return True
        return False

    def _load_annulled_missing_contracts(self):
        path = self._get_missing_contracts_file_path()
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, list):
                    return [item for item in data if isinstance(item, dict)]
        except Exception:
            pass
        return []

    def _save_annulled_missing_contracts(self, entries):
        path = self._get_missing_contracts_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(list(entries or []), fh, indent=4, ensure_ascii=False)

    def _build_missing_contract_entries(self):
        registered_numbers = set()
        highest_sequence = 0

        for contract in self.all_contracts or []:
            seq = self._extract_contract_sequence(contract.get("numero", ""))
            if seq <= 0:
                continue
            registered_numbers.add(seq)
            if seq > highest_sequence:
                highest_sequence = seq

        annulled_records = self._load_annulled_missing_contracts()
        annulled_by_sequence = {}
        for record in annulled_records:
            seq = self._extract_contract_sequence(record.get("numero", ""))
            if seq <= 0:
                continue
            annulled_by_sequence[seq] = record
            if seq > highest_sequence:
                highest_sequence = seq

        entries = []
        for seq in range(1, highest_sequence + 1):
            if seq in registered_numbers:
                continue
            numero = self._format_contract_sequence(seq)
            annulled = annulled_by_sequence.get(seq)
            if annulled:
                entries.append(
                    {
                        "numero": numero,
                        "estado": "anulado",
                        "fecha_anulacion": str(annulled.get("fecha_anulacion", "") or "").strip(),
                        "motivo_anulacion": str(annulled.get("motivo_anulacion", "") or "").strip(),
                    }
                )
            else:
                entries.append(
                    {
                        "numero": numero,
                        "estado": "pendiente",
                        "fecha_anulacion": "",
                        "motivo_anulacion": "",
                    }
                )
        return entries

    def load_contracts(self):
        if not self.username:
            return

        branch_code = self._get_selected_branch_code()
        patients, patients_scoped = self._load_context_list("pacientes.json", cargar_pacientes)
        sales, sales_scoped = self._load_context_list("ventas.json", cargar_ventas)
        contracts_map = {}

        for sale in sales:
            if branch_code and not sales_scoped and not self._record_matches_branch(sale, branch_code):
                continue
            c_num = str(sale.get("contrato_numero", "") or "").strip()
            if not c_num:
                continue

            contracts_map[c_num] = {
                "numero": c_num,
                "fecha": sale.get("fecha", ""),
                "paciente": sale.get("paciente_nombre", "N/A"),
                "dni": sale.get("paciente_dni", "N/A"),
                "total": float(sale.get("total", 0) or 0),
                "pagado": float(sale.get("monto_pagado", 0) or 0),
                "faltante": float(sale.get("monto_faltante", 0) or 0),
                "estado_anulacion": str(sale.get("estado_anulacion", "") or "").strip().lower(),
                "motivo_anulacion": str(sale.get("motivo_anulacion", "") or "").strip(),
                "raw_sale": sale,
            }

        for patient in patients:
            patient_matches_branch = patients_scoped or self._record_matches_branch(patient, branch_code)
            historial = patient.get("historial_graduaciones", [])
            if not isinstance(historial, list):
                continue
            for grad in historial:
                if not isinstance(grad, dict):
                    continue
                if branch_code and not patients_scoped and not (
                    patient_matches_branch or self._record_matches_branch(grad, branch_code)
                ):
                    continue
                c_num = str(grad.get("contrato_numero", "") or "").strip()
                if not c_num:
                    continue
                if c_num in contracts_map:
                    if "raw_grad" not in contracts_map[c_num]:
                        contracts_map[c_num]["raw_grad"] = grad
                    sale_state = str(
                        contracts_map[c_num].get("estado_anulacion", "") or ""
                    ).strip().lower()
                    grad_state = str(grad.get("estado_anulacion", "") or "").strip().lower()
                    if not sale_state and grad_state:
                        contracts_map[c_num]["estado_anulacion"] = grad_state
                    if not contracts_map[c_num].get("motivo_anulacion") and grad.get("motivo_anulacion"):
                        contracts_map[c_num]["motivo_anulacion"] = str(grad.get("motivo_anulacion", "") or "").strip()
                    continue

                total, pagado, faltante = self._resumen_pago_graduacion(grad)
                contracts_map[c_num] = {
                    "numero": c_num,
                    "fecha": grad.get("fecha", ""),
                    "paciente": patient.get("nombre", "N/A"),
                    "dni": patient.get("dni", "N/A"),
                    "total": total,
                    "pagado": pagado,
                    "faltante": faltante,
                    "estado_anulacion": str(grad.get("estado_anulacion", "") or "").strip().lower(),
                    "motivo_anulacion": str(grad.get("motivo_anulacion", "") or "").strip(),
                    "raw_grad": grad,
                }

        self.all_contracts = sorted(contracts_map.values(), key=lambda x: x["fecha"], reverse=True)
        self.display_contracts(self.all_contracts)

    def _resumen_pago_graduacion(self, grad):
        def to_f(value):
            try:
                return float(str(value or 0).replace("S/.", "").replace(",", "").strip())
            except Exception:
                return 0.0

        stored_total = to_f(grad.get("monto_total_venta", 0))
        service_total = to_f(grad.get("monto_cobrado", 0))
        items_total = 0.0
        service_items_total = 0.0
        product_items_total = 0.0
        items_include_service = False

        for item in grad.get("items_venta", []) or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("producto") or item.get("nombre") or "").strip().lower()
            if "servicio de gradu" in name or name == "graduacion":
                items_include_service = True
            qty = to_f(item.get("cantidad", 1)) or 1.0
            price = to_f(item.get("precio_unitario", item.get("precio", 0)))
            item_total = to_f(item.get("subtotal", item.get("total", price * qty)))
            items_total += item_total
            if "servicio de gradu" in name or name == "graduacion":
                service_items_total += item_total
            else:
                product_items_total += item_total

        if items_total > 0.01:
            if items_include_service:
                if service_total > 0.01 and abs(service_items_total - service_total) > 0.05:
                    monto_total = service_total + product_items_total
                else:
                    monto_total = items_total
            else:
                monto_total = service_total + items_total if service_total > 0.01 else items_total
        else:
            monto_total = stored_total if stored_total > 0.01 else service_total

        pagos = grad.get("pagos_parciales", [])
        monto_pagado = 0.0
        if isinstance(pagos, list) and pagos:
            for pago in pagos:
                monto_pagado += to_f(pago.get("monto", 0))
        else:
            monto_pagado = to_f(grad.get("monto_adelanto", 0))
            if not monto_pagado and not grad.get("es_pago_parcial"):
                monto_pagado = monto_total

        return monto_total, monto_pagado, max(0.0, monto_total - monto_pagado)

    def display_contracts(self, contracts):
        self.contracts_table.setRowCount(0)
        for contract in contracts:
            row = self.contracts_table.rowCount()
            self.contracts_table.insertRow(row)

            self.contracts_table.setItem(row, 0, QTableWidgetItem(contract["numero"]))
            self.contracts_table.setItem(row, 1, QTableWidgetItem(contract["fecha"]))
            self.contracts_table.setItem(row, 2, QTableWidgetItem(contract["paciente"]))
            self.contracts_table.setItem(row, 3, QTableWidgetItem(contract["dni"]))

            total_item = QTableWidgetItem(f"S/. {contract['total']:.2f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.contracts_table.setItem(row, 4, total_item)

            pagado_item = QTableWidgetItem(f"S/. {contract['pagado']:.2f}")
            pagado_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.contracts_table.setItem(row, 5, pagado_item)

            faltante_item = QTableWidgetItem(f"S/. {contract['faltante']:.2f}")
            faltante_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if str(contract.get("estado_anulacion", "") or "").strip().lower() == "anulado":
                faltante_item.setForeground(Qt.gray)
            elif contract["faltante"] > 0.05:
                faltante_item.setForeground(Qt.red)
            self.contracts_table.setItem(row, 6, faltante_item)

            if str(contract.get("estado_anulacion", "") or "").strip().lower() == "anulado":
                for col in range(7):
                    item = self.contracts_table.item(row, col)
                    if item:
                        item.setForeground(Qt.gray)
                        item.setToolTip(
                            f"Contrato anulado.\nMotivo: {contract.get('motivo_anulacion', '') or 'Sin motivo registrado.'}"
                        )

            btn_actions = QPushButton("...")
            btn_actions.setFixedWidth(40)
            btn_actions.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    font-weight: bold;
                    font-size: 18px;
                    color: #666666;
                    border: none;
                }
                QPushButton:hover {
                    color: #191919;
                    background-color: #F0F0F0;
                    border-radius: 4px;
                }
                """
            )
            btn_actions.clicked.connect(lambda _checked=False, data=contract: self.show_action_menu(data))
            self.contracts_table.setCellWidget(row, 7, btn_actions)

        self.stats_label.setText(f"Total contratos: {len(contracts)}")

    def show_action_menu(self, contract_data):
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: white;
                border: 1px solid #E0E0E0;
            }
            QMenu::item {
                padding: 8px 24px;
            }
            QMenu::item:selected {
                background-color: #F0F0F0;
                color: black;
            }
            """
        )

        already_annulled = str(contract_data.get("estado_anulacion", "") or "").strip().lower() == "anulado"
        anular_action = QAction("ANULAR CONTRATO", self)
        anular_action.setEnabled(not already_annulled)
        anular_action.triggered.connect(lambda: self.anular_contrato(contract_data))
        menu.addAction(anular_action)

        pdf_action = QAction("EXPORTAR PDF", self)
        pdf_action.triggered.connect(lambda: self.exportar_pdf(contract_data))
        menu.addAction(pdf_action)

        browser_action = QAction("ABRIR EN NAVEGADOR", self)
        browser_action.triggered.connect(lambda: self.abrir_en_navegador(contract_data))
        menu.addAction(browser_action)

        btn = self.sender()
        if btn:
            menu.exec_(btn.mapToGlobal(btn.rect().bottomLeft()))

    def anular_contrato(self, data):
        contract_number = str(data.get("numero", "") or "").strip()
        if not contract_number:
            QMessageBox.warning(self, "Contrato", "No se pudo identificar el contrato a anular.")
            return

        if str(data.get("estado_anulacion", "") or "").strip().lower() == "anulado":
            QMessageBox.information(self, "Contrato", f"El contrato {contract_number} ya está anulado.")
            return

        total_val = float(data.get("total", 0) or 0)
        pagado_val = float(data.get("pagado", 0) or 0)
        faltante_val = float(data.get("faltante", max(0.0, total_val - pagado_val)) or 0)
        has_active_debt = faltante_val > 0.05

        dialog = ContractAnnulDialog(
            contract_number=contract_number,
            has_active_debt=has_active_debt,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        motivo = dialog.get_reason()
        anular_deuda = dialog.should_annul_debt()
        reply = QMessageBox.question(
            self,
            "Confirmar anulación",
            f"Se anulará el contrato {contract_number}.\n\n¿Deseas continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        loader = self._show_contract_action_loader("Anulando contrato...")
        try:
            QApplication.processEvents()
            changed_sales, changed_patients = self._persist_contract_annulment(
                contract_number,
                motivo,
                annular_deuda=anular_deuda,
            )
        finally:
            if loader is not None:
                loader.close()
                loader.deleteLater()

        if not changed_sales and not changed_patients:
            QMessageBox.warning(
                self,
                "Contrato",
                "No se encontró una venta o graduación asociada para guardar la anulación.",
            )
            return

        self.load_contracts()
        QMessageBox.information(
            self,
            "Contrato anulado",
            f"Contrato {contract_number} anulado correctamente.\nMotivo: {motivo or 'Sin motivo registrado.'}",
        )

    def _show_contract_action_loader(self, text="Procesando contrato..."):
        progress = QProgressDialog(str(text or "Procesando contrato..."), None, 0, 0, self)
        progress.setWindowTitle("Procesando")
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.setStyleSheet(
            """
            QProgressDialog {
                background: white;
            }
            QLabel {
                font-size: 13px;
                color: #1f2937;
                min-width: 220px;
            }
            QProgressBar {
                border: 1px solid #D9DDE3;
                border-radius: 5px;
                background: #F3F4F6;
                height: 10px;
            }
            QProgressBar::chunk {
                background: #2563EB;
                border-radius: 5px;
            }
            """
        )
        progress.show()
        return progress

    def _persist_contract_annulment(self, contract_number, motivo="", annular_deuda=False):
        contract_number = str(contract_number or "").strip()
        if not contract_number or not self.username:
            return False, False

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        changed_sales = False
        changed_patients = False

        ventas = cargar_ventas(self.username) or []
        for venta in ventas:
            if not isinstance(venta, dict):
                continue
            if str(venta.get("contrato_numero", "") or "").strip() != contract_number:
                continue
            venta["estado_anulacion"] = "anulado"
            venta["contrato_anulado"] = True
            venta["anulado"] = True
            venta["fecha_anulacion"] = timestamp
            venta["motivo_anulacion"] = str(motivo or "").strip()
            if annular_deuda:
                venta["deuda_anulada"] = True
                venta["estado_deuda"] = "anulada"
                venta["fecha_anulacion_deuda"] = timestamp
                venta["motivo_anulacion_deuda"] = str(motivo or "").strip()
                venta["monto_faltante"] = 0.0
                venta["es_pago_partes"] = False
                venta["es_pago_parcial"] = False
            changed_sales = True
        if changed_sales:
            guardar_ventas(self.username, ventas)

        pacientes = cargar_pacientes(self.username) or []
        for paciente in pacientes:
            historial = paciente.get("historial_graduaciones", [])
            if not isinstance(historial, list):
                continue
            for grad in historial:
                if not isinstance(grad, dict):
                    continue
                if str(grad.get("contrato_numero", "") or "").strip() != contract_number:
                    continue
                grad["estado_anulacion"] = "anulado"
                grad["contrato_anulado"] = True
                grad["anulado"] = True
                grad["fecha_anulacion"] = timestamp
                grad["motivo_anulacion"] = str(motivo or "").strip()
                if annular_deuda:
                    grad["deuda_anulada"] = True
                    grad["estado_deuda"] = "anulada"
                    grad["fecha_anulacion_deuda"] = timestamp
                    grad["motivo_anulacion_deuda"] = str(motivo or "").strip()
                    grad["es_pago_parcial"] = False
                changed_patients = True
        if changed_patients:
            guardar_pacientes(self.username, pacientes)

        return changed_sales, changed_patients

    def _annul_missing_contract_entry(self, entry):
        contract_number = str((entry or {}).get("numero", "") or "").strip()
        if not contract_number:
            QMessageBox.warning(self, "Contrato", "No se pudo identificar el número de contrato.")
            return False

        if str((entry or {}).get("estado", "") or "").strip().lower() == "anulado":
            QMessageBox.information(self, "Contrato", f"El contrato {contract_number} ya está anulado.")
            return False

        dialog = ContractAnnulDialog(contract_number=contract_number, has_active_debt=False, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return False

        motivo = dialog.get_reason()
        reply = QMessageBox.question(
            self,
            "Confirmar anulación",
            f"Se anulará el contrato no registrado {contract_number}.\n\n¿Deseas continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return False

        loader = self._show_contract_action_loader("Anulando contrato no registrado...")
        try:
            QApplication.processEvents()
            records = self._load_annulled_missing_contracts()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record = {
                "numero": contract_number,
                "estado": "anulado",
                "fecha_anulacion": timestamp,
                "motivo_anulacion": str(motivo or "").strip(),
            }
            updated = False
            for idx, existing in enumerate(records):
                if self._extract_contract_sequence(existing.get("numero", "")) == self._extract_contract_sequence(contract_number):
                    records[idx] = record
                    updated = True
                    break
            if not updated:
                records.append(record)
            records.sort(key=lambda item: self._extract_contract_sequence(item.get("numero", "")))
            self._save_annulled_missing_contracts(records)
        finally:
            if loader is not None:
                loader.close()
                loader.deleteLater()

        QMessageBox.information(
            self,
            "Contrato anulado",
            f"Contrato no registrado {contract_number} anulado correctamente.\nMotivo: {motivo or 'Sin motivo registrado.'}",
        )
        return True

    def open_missing_contracts_dialog(self):
        entries = self._build_missing_contract_entries()
        if not entries:
            QMessageBox.information(
                self,
                "Contratos no registrados",
                "No se encontraron huecos en la secuencia de contratos."
            )
            return
        dialog = MissingContractsDialog(self, entries, self)
        dialog.exec_()

    def exportar_pdf(self, data):
        from utils.generador_contrato import (
            build_contract_number,
            resolve_contract_patient_and_graduacion,
        )

        paciente_data, raw_grad, grad_index = resolve_contract_patient_and_graduacion(
            self.username,
            contract_number=data.get("numero", ""),
            preferred_dni=data.get("dni", ""),
            raw_grad=data.get("raw_grad"),
        )

        if not raw_grad or not paciente_data:
            QMessageBox.warning(
                self,
                "Contrato",
                "No se encontró la graduación asociada para generar el contrato PDF.",
            )
            return

        nombre_optica = "Mi Óptica"
        try:
            from utils.file_handler import cargar_datos_optica
            datos = cargar_datos_optica(self.username, prefer_remote=True)
            if datos and datos.get("nombre_optica"):
                nombre_optica = datos["nombre_optica"]
            else:
                from utils.file_handler import cargar_nombre_optica
                nombre_optica = cargar_nombre_optica(self.username)
        except Exception:
            pass
        self._launch_contract_pdf_job(
            paciente_data=paciente_data,
            graduacion=raw_grad,
            nombre_optica=nombre_optica,
            contract_number=build_contract_number(paciente_data, raw_grad, grad_index),
            open_in_browser=False,
        )

    def abrir_en_navegador(self, data):
        from utils.generador_contrato import (
            build_contract_number,
            resolve_contract_patient_and_graduacion,
        )

        paciente_data, raw_grad, grad_index = resolve_contract_patient_and_graduacion(
            self.username,
            contract_number=data.get("numero", ""),
            preferred_dni=data.get("dni", ""),
            raw_grad=data.get("raw_grad"),
        )

        if not raw_grad or not paciente_data:
            QMessageBox.warning(
                self,
                "Contrato",
                "No se encontró la graduación asociada para abrir el contrato.",
            )
            return

        nombre_optica = "Mi Óptica"
        try:
            from utils.file_handler import cargar_datos_optica
            datos = cargar_datos_optica(self.username, prefer_remote=True)
            if datos and datos.get("nombre_optica"):
                nombre_optica = datos["nombre_optica"]
            else:
                from utils.file_handler import cargar_nombre_optica
                nombre_optica = cargar_nombre_optica(self.username)
        except Exception:
            pass
        self._launch_contract_pdf_job(
            paciente_data=paciente_data,
            graduacion=raw_grad,
            nombre_optica=nombre_optica,
            contract_number=build_contract_number(paciente_data, raw_grad, grad_index),
            open_in_browser=True,
        )

    def _launch_contract_pdf_job(self, paciente_data, graduacion, nombre_optica, contract_number, open_in_browser):
        from utils.file_handler import open_pdf_with_chrome
        from gui.dialogs.pdf_viewer_dialog import PDFViewerDialog

        progress = QProgressDialog(
            "Generando contrato..." if not open_in_browser else "Preparando contrato en navegador...",
            None,
            0,
            0,
            self,
        )
        progress.setWindowTitle("Contrato")
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        thread = QThread(self)
        worker = _ContractPdfWorker(
            paciente_data=paciente_data,
            graduacion=graduacion,
            nombre_optica=nombre_optica,
            username=self.username,
            contract_number=contract_number,
            open_in_browser=open_in_browser,
        )
        worker.moveToThread(thread)
        self._contract_pdf_thread = thread
        self._contract_pdf_worker = worker

        def _finish(pdf_path, error, open_browser_flag):
            try:
                progress.close()
            except Exception:
                pass
            try:
                thread.quit()
            except Exception:
                pass
            try:
                worker.deleteLater()
            except Exception:
                pass
            try:
                thread.deleteLater()
            except Exception:
                pass
            self._contract_pdf_thread = None
            self._contract_pdf_worker = None

            if error:
                QMessageBox.critical(self, "Contrato", f"No se pudo generar el contrato.\n\n{error}")
                return
            if not pdf_path:
                QMessageBox.warning(self, "Contrato", "No se generó el archivo del contrato.")
                return
            try:
                if open_browser_flag:
                    open_pdf_with_chrome(pdf_path)
                else:
                    viewer = PDFViewerDialog(pdf_path, self)
                    viewer.exec_()
            except Exception as open_error:
                QMessageBox.critical(self, "Contrato", f"El contrato se generó, pero no se pudo abrir.\n\n{open_error}")

        thread.started.connect(worker.run)
        worker.finished.connect(_finish)
        thread.start()

    def filter_contracts(self):
        text = self.search_input.text().lower().strip()
        if not text:
            self.display_contracts(self.all_contracts)
            return

        filtered = [
            contract
            for contract in self.all_contracts
            if text in contract["numero"].lower()
            or text in contract["paciente"].lower()
            or text in contract["dni"].lower()
        ]
        self.display_contracts(filtered)

    def focus_contract(self, contract_number):
        target = str(contract_number or "").strip()
        if not target:
            return False
        try:
            self.load_contracts()
        except Exception:
            pass

        self.search_input.setText(target)
        self.filter_contracts()

        for row in range(self.contracts_table.rowCount()):
            item = self.contracts_table.item(row, 0)
            if item and str(item.text() or "").strip() == target:
                self.contracts_table.clearSelection()
                self.contracts_table.selectRow(row)
                self.contracts_table.setCurrentCell(row, 0)
                self.contracts_table.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                return True
        return False

    def go_back(self):
        if self.parent_app and hasattr(self.parent_app, "mostrar_frame"):
            self.parent_app.mostrar_frame(1)
