import datetime
import uuid

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.main_window_pages.basic_mode_common import (
    BasicWindowBase,
    load_scoped_list,
    make_button,
    set_button_busy,
)
from utils.file_handler import cargar_pacientes, guardar_pacientes


class BasicPatientsPage(BasicWindowBase):
    def __init__(self, parent=None, initial_mode="search"):
        super().__init__(
            parent_app=parent,
            title="Pacientes",
            subtitle="Busca pacientes o registra uno nuevo sin entrar a la pantalla profesional.",
            loader_text="Cargando pacientes",
        )
        self.all_patients = []
        self.selected_patient = None
        self._saving = False
        self.initial_mode = initial_mode
        self._build_ui()

    def _build_ui(self):
        toolbar = QHBoxLayout()
        self.btn_search_mode = make_button("Buscar paciente", "#0EA5A4", "#0F766E")
        self.btn_search_mode.clicked.connect(lambda: self._set_mode("search"))
        toolbar.addWidget(self.btn_search_mode)
        self.btn_new_mode = make_button("Nuevo paciente", "#2563EB", "#1D4ED8")
        self.btn_new_mode.clicked.connect(lambda: self._set_mode("new"))
        toolbar.addWidget(self.btn_new_mode)
        toolbar.addStretch()
        btn_close = make_button("Cerrar", "#64748B", "#475569")
        btn_close.clicked.connect(self.exit_basic_page)
        toolbar.addWidget(btn_close)
        self.content_layout.addLayout(toolbar)

        self.views = QStackedWidget()
        self.content_layout.addWidget(self.views, 1)
        self._build_search_view()
        self._build_form_view()

        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self._apply_search)
        self._set_mode(self.initial_mode)

    def _build_search_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        row = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Escribe nombre, DNI o telefono")
        self.search_entry.textChanged.connect(lambda: self.search_timer.start())
        row.addWidget(self.search_entry, 1)
        btn_refresh = make_button("Recargar")
        btn_refresh.clicked.connect(self.reload_data)
        row.addWidget(btn_refresh)
        layout.addLayout(row)

        self.search_summary = QLabel("Pacientes: 0")
        self.search_summary.setStyleSheet("font-size: 21px; font-weight: 800; color: #0F172A;")
        layout.addWidget(self.search_summary)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["DNI", "Nombre", "Telefono", "Direccion"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_patient_selected)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.btn_history = make_button("Ver historial", "#7C3AED", "#6D28D9")
        self.btn_history.clicked.connect(self._show_selected_details)
        actions.addWidget(self.btn_history)
        self.btn_sale = make_button("Nueva venta", "#1F9D55", "#157347")
        self.btn_sale.clicked.connect(self._open_sale_for_selected)
        actions.addWidget(self.btn_sale)
        self.btn_edit = make_button("Editar paciente", "#F59E0B", "#D97706")
        self.btn_edit.clicked.connect(self._edit_selected)
        actions.addWidget(self.btn_edit)
        actions.addStretch()
        layout.addLayout(actions)
        self.views.addWidget(view)
        self.search_view = view

    def _build_form_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        self.form_fields = {}
        fields = (
            ("nombre", "Nombre", "Nombre completo"),
            ("dni", "DNI", "00000000"),
            ("telefono", "Telefono", "Telefono opcional"),
            ("direccion", "Direccion", "Direccion opcional"),
            ("edad", "Edad", "Edad opcional"),
            ("od", "OD", "Dato simple de ojo derecho"),
            ("oi", "OI", "Dato simple de ojo izquierdo"),
        )
        for key, label, placeholder in fields:
            entry = QLineEdit()
            entry.setPlaceholderText(placeholder)
            self.form_fields[key] = entry
            form.addRow(label, entry)
        layout.addLayout(form)

        layout.addWidget(QLabel("Observacion"))
        self.observation_edit = QTextEdit()
        self.observation_edit.setMinimumHeight(120)
        layout.addWidget(self.observation_edit)

        actions = QHBoxLayout()
        self.btn_save = make_button("Guardar paciente", "#1F9D55", "#157347")
        self.btn_save.clicked.connect(self._save_patient)
        actions.addWidget(self.btn_save)
        btn_clear = make_button("Limpiar", "#F59E0B", "#D97706")
        btn_clear.clicked.connect(self._clear_form)
        actions.addWidget(btn_clear)
        btn_back = make_button("Volver a buscar", "#64748B", "#475569")
        btn_back.clicked.connect(lambda: self._set_mode("search"))
        actions.addWidget(btn_back)
        actions.addStretch()
        layout.addLayout(actions)
        self.views.addWidget(view)
        self.form_view = view

    def _set_mode(self, mode):
        if mode == "new":
            self.selected_patient = None
            self._clear_form()
            self.views.setCurrentWidget(self.form_view)
        else:
            self.views.setCurrentWidget(self.search_view)
            if not self.all_patients:
                self.reload_data()

    def reload_data(self):
        self.load_async(
            lambda: load_scoped_list(self.parent_app, self.username, "pacientes.json", cargar_pacientes)[0],
            self._on_patients_loaded,
            loading_text="Cargando pacientes",
        )

    def _on_patients_loaded(self, patients):
        self.all_patients = [patient for patient in patients if isinstance(patient, dict)]
        self._apply_search()

    def _apply_search(self):
        query = str(self.search_entry.text() or "").strip().casefold()
        if not query:
            filtered = self.all_patients[:500]
        else:
            filtered = []
            for patient in self.all_patients:
                haystack = " ".join(
                    str(patient.get(key, "") or "")
                    for key in ("nombre", "dni", "telefono", "celular")
                ).casefold()
                if query in haystack:
                    filtered.append(patient)
                if len(filtered) >= 500:
                    break
        self._render_patients(filtered)

    def _render_patients(self, patients):
        self.table.setRowCount(0)
        for row, patient in enumerate(patients):
            self.table.insertRow(row)
            values = [
                str(patient.get("dni", "") or "Sin DNI"),
                str(patient.get("nombre", "") or "Sin nombre"),
                str(patient.get("telefono", patient.get("celular", "")) or ""),
                str(patient.get("direccion", "") or ""),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            self.table.item(row, 0).setData(Qt.UserRole, patient)
        self.search_summary.setText(f"Resultados: {len(patients)} de {len(self.all_patients)} pacientes")

    def _on_patient_selected(self):
        items = self.table.selectedItems()
        self.selected_patient = items[0].data(Qt.UserRole) if items else None

    def _show_selected_details(self):
        patient = self.selected_patient
        if not isinstance(patient, dict):
            QMessageBox.information(self, "Pacientes", "Selecciona un paciente primero.")
            return
        graduations = patient.get("historial_graduaciones", []) or []
        if not isinstance(graduations, list):
            graduations = []
        recent = []
        for graduation in reversed(graduations[-5:]):
            if not isinstance(graduation, dict):
                continue
            contract = str(graduation.get("contrato_numero", "") or "Sin contrato")
            date = str(graduation.get("fecha", "") or "Sin fecha")
            recent.append(f"- {date} | Contrato {contract}")
        history_text = "\n".join(recent) if recent else "Sin graduaciones registradas."
        message = (
            f"Nombre: {patient.get('nombre', 'Sin nombre')}\n"
            f"DNI: {patient.get('dni', 'Sin DNI')}\n"
            f"Telefono: {patient.get('telefono', patient.get('celular', '')) or 'No registrado'}\n"
            f"Direccion: {patient.get('direccion', '') or 'No registrada'}\n"
            f"Graduaciones: {len(graduations)}\n"
            f"Observacion: {patient.get('observacion', '') or 'Sin observacion'}\n\n"
            f"Ultimas graduaciones:\n{history_text}"
        )
        QMessageBox.information(self, "Datos del paciente", message)

    def _open_sale_for_selected(self):
        patient = self.selected_patient
        if not isinstance(patient, dict):
            QMessageBox.information(self, "Pacientes", "Selecciona un paciente primero.")
            return
        try:
            self.parent_app.mostrar_frame(4)
            dni = str(patient.get("dni", "") or "00000000")
            name = str(patient.get("nombre", "") or "")

            def fill_sale(attempt=0):
                sale_page = getattr(self.parent_app, "sales_page", None) or getattr(self.parent_app, "page_4", None)
                if sale_page is None and attempt < 8:
                    QtCore.QTimer.singleShot(150, lambda: fill_sale(attempt + 1))
                    return
                if sale_page is None:
                    QMessageBox.warning(self, "Pacientes", "La pantalla de venta no termino de cargar.")
                    return
                if hasattr(sale_page, "entry_dni"):
                    sale_page.entry_dni.setText(dni)
                if hasattr(sale_page, "entry_nombre"):
                    sale_page.entry_nombre.setText(name)

            fill_sale()
        except Exception as exc:
            QMessageBox.warning(self, "Pacientes", f"No se pudo abrir la venta.\n\n{exc}")

    def _edit_selected(self):
        if not isinstance(self.selected_patient, dict):
            QMessageBox.information(self, "Pacientes", "Selecciona un paciente primero.")
            return
        patient = self.selected_patient
        for key, field in self.form_fields.items():
            field.setText(str(patient.get(key, "") or ""))
        self.observation_edit.setPlainText(str(patient.get("observacion", "") or ""))
        self.views.setCurrentWidget(self.form_view)

    def _clear_form(self):
        for field in self.form_fields.values():
            field.clear()
        self.form_fields["dni"].setText("00000000")
        self.observation_edit.clear()

    def _set_saving(self, saving):
        self._saving = saving
        set_button_busy(self.btn_save, saving, "Guardar paciente", "Guardando")
        QtWidgets.QApplication.processEvents()

    def _save_patient(self):
        if self._saving:
            return
        self._set_saving(True)
        try:
            values = {key: str(field.text() or "").strip() for key, field in self.form_fields.items()}
            name = values["nombre"]
            dni = "".join(char for char in values["dni"] if char.isdigit())
            if not name:
                raise ValueError("Escribe el nombre del paciente.")
            if not dni:
                dni = "00000000"
            if len(dni) != 8:
                raise ValueError("El DNI debe tener 8 digitos. Puedes usar 00000000.")

            patients = cargar_pacientes(self.username) or []
            if not isinstance(patients, list):
                patients = []
            current = self.selected_patient if isinstance(self.selected_patient, dict) else None
            current_uuid = str(current.get("uuid", "") or "").strip() if current else ""
            current_dni = str(current.get("dni", "") or "").strip() if current else ""
            current_name = str(current.get("nombre", "") or "").strip().casefold() if current else ""
            persisted_current = None
            for patient in patients:
                if not isinstance(patient, dict):
                    continue
                patient_uuid = str(patient.get("uuid", "") or "").strip()
                patient_dni = str(patient.get("dni", "") or "").strip()
                patient_name = str(patient.get("nombre", "") or "").strip().casefold()
                is_current = bool(
                    current
                    and (
                        (current_uuid and patient_uuid == current_uuid)
                        or (current_dni != "00000000" and patient_dni == current_dni)
                        or (
                            current_dni == "00000000"
                            and patient_dni == current_dni
                            and patient_name == current_name
                        )
                    )
                )
                if is_current:
                    persisted_current = patient
                    continue
                same_real_dni = dni != "00000000" and str(patient.get("dni", "") or "").strip() == dni
                same_generic = (
                    dni == "00000000"
                    and str(patient.get("dni", "") or "").strip() == dni
                    and str(patient.get("nombre", "") or "").strip().casefold() == name.casefold()
                )
                if same_real_dni or same_generic:
                    raise ValueError("Ese paciente ya existe. Usa Buscar paciente para editarlo.")

            if current is not None and persisted_current is None:
                raise ValueError("No se encontro el paciente original. Recarga la lista e intenta nuevamente.")

            payload = persisted_current or {
                "uuid": str(uuid.uuid4()),
                "fecha": datetime.datetime.now().strftime("%d/%m/%Y"),
                "historial_graduaciones": [],
            }
            payload.update(
                {
                    "nombre": name,
                    "dni": dni,
                    "telefono": values["telefono"],
                    "direccion": values["direccion"],
                    "edad": values["edad"],
                    "od": values["od"],
                    "oi": values["oi"],
                    "observacion": str(self.observation_edit.toPlainText() or "").strip(),
                }
            )
            if persisted_current is None:
                patients.append(payload)
            guardar_pacientes(self.username, patients)
            QMessageBox.information(self, "Pacientes", f"Paciente guardado correctamente.\n\n{name}")
            self.selected_patient = None
            self._set_mode("search")
            self.reload_data()
        except Exception as exc:
            QMessageBox.warning(self, "Pacientes", str(exc))
        finally:
            self._set_saving(False)

    def showEvent(self, event):
        super().showEvent(event)
        if self.views.currentWidget() is self.search_view:
            self.reload_data()
