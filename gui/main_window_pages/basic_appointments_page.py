import datetime
import uuid

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
)

from gui.main_window_pages.basic_mode_common import (
    BasicWindowBase,
    date_in_filter,
    load_scoped_list,
    make_button,
    parse_date_safe,
    set_button_busy,
)
from utils.file_handler import cargar_citas, guardar_citas


class BasicAppointmentsPage(BasicWindowBase):
    def __init__(self, parent=None):
        super().__init__(
            parent_app=parent,
            title="Citas",
            subtitle="Consulta y crea citas con los datos esenciales.",
            loader_text="Cargando citas",
        )
        self.all_appointments = []
        self._saving = False
        self._build_ui()

    def _build_ui(self):
        toolbar = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Hoy", "today")
        self.filter_combo.addItem("Manana", "tomorrow")
        self.filter_combo.addItem("Esta semana", "this_week")
        self.filter_combo.addItem("Dia especifico", "specific")
        self.filter_combo.addItem("Todas", "all")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_combo)
        self.filter_date = QDateEdit(QtCore.QDate.currentDate())
        self.filter_date.setCalendarPopup(True)
        self.filter_date.setDisplayFormat("dd/MM/yyyy")
        self.filter_date.hide()
        self.filter_date.dateChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_date)
        self.summary = QLabel("Citas: 0")
        self.summary.setStyleSheet(
            "font-size: 22px; font-weight: 800; color: #0F172A; "
            "background: #E8F1FF; border: 2px solid #BFD3FF; border-radius: 14px; padding: 12px 16px;"
        )
        toolbar.addWidget(self.summary, 1)
        btn_refresh = make_button("Recargar")
        btn_refresh.clicked.connect(self.reload_data)
        toolbar.addWidget(btn_refresh)
        btn_close = make_button("Cerrar", "#64748B", "#475569")
        btn_close.clicked.connect(self.exit_basic_page)
        toolbar.addWidget(btn_close)
        self.content_layout.addLayout(toolbar)

        body = QHBoxLayout()
        body.setSpacing(16)

        form_box = QtWidgets.QGroupBox("Nueva cita")
        form_layout = QVBoxLayout(form_box)
        form = QFormLayout()
        self.dni_entry = QLineEdit("00000000")
        self.name_entry = QLineEdit()
        self.date_entry = QDateEdit(QtCore.QDate.currentDate())
        self.date_entry.setCalendarPopup(True)
        self.date_entry.setDisplayFormat("dd/MM/yyyy")
        self.time_entry = QTimeEdit(QtCore.QTime.currentTime())
        self.time_entry.setDisplayFormat("HH:mm")
        self.reason_entry = QLineEdit()
        self.reason_entry.setPlaceholderText("Revision, graduacion, entrega...")
        self.notes_entry = QTextEdit()
        self.notes_entry.setMinimumHeight(100)
        form.addRow("DNI", self.dni_entry)
        form.addRow("Paciente", self.name_entry)
        form.addRow("Fecha", self.date_entry)
        form.addRow("Hora", self.time_entry)
        form.addRow("Motivo", self.reason_entry)
        form.addRow("Observacion", self.notes_entry)
        form_layout.addLayout(form)
        self.btn_save = make_button("Guardar cita", "#1F9D55", "#157347")
        self.btn_save.clicked.connect(self._save_appointment)
        form_layout.addWidget(self.btn_save)
        body.addWidget(form_box, 1)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Fecha", "Hora", "Paciente", "DNI", "Motivo", "Estado"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        body.addWidget(self.table, 2)
        self.content_layout.addLayout(body, 1)

    def reload_data(self):
        self.load_async(
            lambda: load_scoped_list(self.parent_app, self.username, "citas.json", cargar_citas)[0],
            self._on_loaded,
            loading_text="Cargando citas",
        )

    def _on_loaded(self, appointments):
        self.all_appointments = sorted(
            [appointment for appointment in appointments if isinstance(appointment, dict)],
            key=lambda appointment: (
                parse_date_safe(appointment.get("fecha")) or datetime.datetime.min,
                str(appointment.get("hora", "") or ""),
            ),
        )
        self._apply_filter()

    def _apply_filter(self):
        if not hasattr(self, "table"):
            return
        key = str(self.filter_combo.currentData() or "today")
        self.filter_date.setVisible(key == "specific")
        selected = self.filter_date.date().toPyDate()
        filtered = [
            appointment
            for appointment in self.all_appointments
            if date_in_filter(appointment.get("fecha"), key, selected)
        ]
        self._render(filtered)

    def _render(self, appointments):
        self.table.setRowCount(0)
        for row, appointment in enumerate(appointments):
            self.table.insertRow(row)
            values = [
                str(appointment.get("fecha", "") or "Sin fecha"),
                str(appointment.get("hora", "") or "Sin hora"),
                str(appointment.get("nombre_paciente", appointment.get("paciente", "")) or "Sin paciente"),
                str(appointment.get("dni", "") or "Sin DNI"),
                str(appointment.get("tipo", appointment.get("motivo", "")) or "Sin motivo"),
                str(appointment.get("estado", "") or "Pendiente"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter if column in (0, 1, 3, 5) else Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row, column, item)
        self.summary.setText(f"Citas: {len(appointments)}")

    def _set_saving(self, saving):
        self._saving = saving
        set_button_busy(self.btn_save, saving, "Guardar cita", "Guardando")
        QtWidgets.QApplication.processEvents()

    def _save_appointment(self):
        if self._saving:
            return
        self._set_saving(True)
        try:
            dni = "".join(char for char in str(self.dni_entry.text() or "") if char.isdigit()) or "00000000"
            name = str(self.name_entry.text() or "").strip()
            date_value = self.date_entry.date().toString("yyyy-MM-dd")
            time_value = self.time_entry.time().toString("HH:mm")
            reason = str(self.reason_entry.text() or "").strip() or "Consulta"
            if len(dni) != 8:
                raise ValueError("El DNI debe tener 8 digitos. Puedes usar 00000000.")
            if not name:
                raise ValueError("Escribe el nombre del paciente.")

            appointments = cargar_citas(self.username) or []
            if not isinstance(appointments, list):
                appointments = []
            duplicate = any(
                isinstance(item, dict)
                and str(item.get("fecha", "") or "") == date_value
                and str(item.get("hora", "") or "") == time_value
                and str(item.get("dni", "") or "") == dni
                for item in appointments
            )
            if duplicate:
                raise ValueError("Ya existe una cita para ese paciente en la misma fecha y hora.")
            appointments.append(
                {
                    "cita_id": f"CITA_{uuid.uuid4().hex}",
                    "dni": dni,
                    "nombre_paciente": name,
                    "fecha": date_value,
                    "hora": time_value,
                    "duracion_minutos": 30,
                    "tipo": reason,
                    "estado": "Pendiente",
                    "notas": str(self.notes_entry.toPlainText() or "").strip(),
                    "created_at": datetime.datetime.now().isoformat(),
                    "updated_at": datetime.datetime.now().isoformat(),
                }
            )
            guardar_citas(self.username, appointments)
            QMessageBox.information(self, "Citas", "La cita fue guardada correctamente.")
            self.name_entry.clear()
            self.reason_entry.clear()
            self.notes_entry.clear()
            self.reload_data()
        except Exception as exc:
            QMessageBox.warning(self, "Citas", str(exc))
        finally:
            self._set_saving(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_data()
