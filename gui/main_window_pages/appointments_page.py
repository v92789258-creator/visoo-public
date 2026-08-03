from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCalendarWidget,
    QPushButton, QFrame, QScrollArea, QSizePolicy, QMessageBox,
    QDialog, QTableWidget, QHeaderView, QGroupBox, QFormLayout,
    QLineEdit, QDateEdit, QTimeEdit, QTextEdit, QStackedWidget,
    QComboBox, QSpinBox, QCheckBox, QAbstractItemView, QCompleter
)
from PyQt5.QtCore import Qt, QDate, QSize, QTime, QRectF, QStringListModel
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPainterPath, QPixmap

# Importaciones necesarias
from gui.dialogs.selection_dialogs import SeleccionarPacientesDialog
from gui.dialogs.appointment_dialog import AppointmentDialog
from utils.data_cache_manager import get_global_cache
from utils.appointments_stats import AppointmentsStatistics
from utils.appointments_model import AppointmentStatus

# ==============================================================================
# SISTEMA DE DISEÑO & TEMAS (SaaS STYLE)
# ==============================================================================

class SaaSTheme:
    """Gestor de estilos centralizado tipo 'Carbon & White'."""
    
    # Paleta de colores Carbono/Blanco
    COLOR_BG_MAIN = "#FFFFFF"
    COLOR_BG_SECONDARY = "#FAFAFA"  # Gris muy pálido para fondos secundarios
    COLOR_CARBON = "#111111"        # Negro casi puro para texto principal y botones primarios
    COLOR_TEXT_SECONDARY = "#595959" # Gris oscuro para subtítulos
    COLOR_BORDER = "#E1E3E5"        # Borde sutil tipo Shopify
    COLOR_ACCENT = "#000000"        # Acento serio (negro)
    COLOR_HOVER = "#F1F2F3"         # Hover sutil
    COLOR_DANGER = "#D82C0D"        # Rojo profesional (no brillante)
    COLOR_SUCCESS = "#008060"       # Verde Shopify
    
    FONT_FAMILY = "Segoe UI, Inter, Arial"

    @staticmethod
    def get_stylesheet():
        return f"""
            QWidget {{
                font-family: '{SaaSTheme.FONT_FAMILY}';
                color: {SaaSTheme.COLOR_CARBON};
            }}
            QFrame {{
                background-color: {SaaSTheme.COLOR_BG_MAIN};
                border: none;
            }}
            /* Scrollbar minimalista */
            QScrollBar:vertical {{
                border: none;
                background: {SaaSTheme.COLOR_BG_SECONDARY};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #CCCCCC;
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """

    @staticmethod
    def btn_primary():
        return f"""
            QPushButton {{
                background-color: {SaaSTheme.COLOR_CARBON};
                color: white;
                border: 1px solid {SaaSTheme.COLOR_CARBON};
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 13px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: #333333;
                border-color: #333333;
            }}
            QPushButton:pressed {{
                background-color: #000000;
            }}
        """

    @staticmethod
    def btn_secondary():
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {SaaSTheme.COLOR_CARBON};
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {SaaSTheme.COLOR_BG_SECONDARY};
                border-color: #D1D1D1;
            }}
        """

    @staticmethod
    def btn_danger():
        return f"""
            QPushButton {{
                background-color: white;
                color: {SaaSTheme.COLOR_DANGER};
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {SaaSTheme.COLOR_DANGER};
                background-color: #FFF5F5;
            }}
        """
    
    @staticmethod
    def input_style():
        return f"""
            QLineEdit, QTextEdit, QDateEdit, QTimeEdit, QComboBox {{
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                color: {SaaSTheme.COLOR_CARBON};
                selection-background-color: {SaaSTheme.COLOR_CARBON};
                selection-color: white;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {SaaSTheme.COLOR_CARBON};
            }}
        """

# Helper para dibujar iconos vectoriales programáticos (SVG simulación)
class ProIcon:
    @staticmethod
    def draw(name, size=16, color=SaaSTheme.COLOR_CARBON):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        
        path = QPainterPath()
        
        if name == "user":
            # Silueta minimalista de usuario
            path.addEllipse(size//2 - 3, 2, 6, 6)
            path.moveTo(3, size-2)
            path.quadTo(size//2, size-6, size-3, size-2)
        elif name == "calendar":
            # Calendario cuadrado
            painter.drawRect(2, 4, size-4, size-6)
            painter.drawLine(size//3, 2, size//3, 5)
            painter.drawLine(size*2//3, 2, size*2//3, 5)
            painter.drawLine(2, 8, size-2, 8)
            path = None # Ya dibujado directamente
        elif name == "clock":
            # Reloj
            path.addEllipse(1, 1, size-2, size-2)
            path.moveTo(size//2, size//2)
            path.lineTo(size//2, 4)
            path.moveTo(size//2, size//2)
            path.lineTo(size-4, size//2)
        elif name == "plus":
            path.moveTo(size//2, 3)
            path.lineTo(size//2, size-3)
            path.moveTo(3, size//2)
            path.lineTo(size-3, size//2)
        elif name == "chart":
            path.moveTo(2, size-2)
            path.lineTo(2, 2)
            path.moveTo(2, size-2)
            path.lineTo(size-2, size-2)
            painter.drawPolyline(
                QtCore.QPoint(4, size-4),
                QtCore.QPoint(8, size-8),
                QtCore.QPoint(12, size-6),
                QtCore.QPoint(16, 4)
            )
            
        if path:
            painter.drawPath(path)
        painter.end()
        return QtGui.QIcon(pixmap)

# ==============================================================================
# COMPONENTES REFACTORIZADOS
# ==============================================================================

class CustomCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.appointments = {}
        
        # Eliminar bordes nativos y cabeceras feas
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames)
        self.setGridVisible(False)
        self.setNavigationBarVisible(True)
        
        # Estilo profesional serio
        self.setStyleSheet(f"""
            QCalendarWidget QWidget {{ 
                alternate-background-color: {SaaSTheme.COLOR_BG_MAIN}; 
                background-color: {SaaSTheme.COLOR_BG_MAIN};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {SaaSTheme.COLOR_BG_MAIN};
                border-bottom: 1px solid {SaaSTheme.COLOR_BORDER};
                padding: 8px 0px;
            }}
            QToolButton {{
                color: {SaaSTheme.COLOR_CARBON};
                background-color: transparent;
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: bold;
                margin: 2px;
            }}
            QToolButton:hover {{
                border-color: {SaaSTheme.COLOR_CARBON};
            }}
            QToolButton::menu-indicator {{ image: none; }}
            QToolButton#qt_calendar_monthbutton {{ width: 100px; }}
            QToolButton#qt_calendar_yearbutton {{ width: 60px; }}
            QSpinBox {{
                {SaaSTheme.input_style()}
                border: none;
                font-weight: bold;
            }}
            QTableView {{
                outline: none;
                border: none;
                selection-background-color: {SaaSTheme.COLOR_CARBON};
                selection-color: white;
            }}
        """)

    def paintCell(self, painter, rect, date):
        # Renderizado personalizado ultra-minimalista
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Fondo (detectar hoy)
        if date == QDate.currentDate():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#F5F5F5"))
            painter.drawRect(rect)
        
        # 2. Texto de la fecha
        painter.setPen(QColor(SaaSTheme.COLOR_CARBON))
        font = painter.font()
        font.setPixelSize(13)
        if self.selectedDate() == date:
            font.setBold(True)
            # Fondo negro para selección
            painter.setBrush(QColor(SaaSTheme.COLOR_CARBON))
            painter.drawRoundedRect(rect.adjusted(4,4,-4,-4), 4, 4)
            painter.setPen(Qt.white)
        else:
            font.setBold(False)
            
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, str(date.day()))

        # 3. Indicador de evento (punto discreto, no colores brillantes)
        if date in self.appointments:
            count = len(self.appointments[date])
            if count > 0:
                dot_size = 4
                # Si está seleccionado el día, el punto es blanco, sino negro
                dot_color = Qt.white if self.selectedDate() == date else QColor(SaaSTheme.COLOR_CARBON)
                
                painter.setBrush(dot_color)
                painter.setPen(Qt.NoPen)
                
                # Dibujar punto debajo del número
                cx = rect.center().x()
                cy = rect.bottom() - 8
                painter.drawEllipse(QtCore.QPointF(cx, cy), dot_size/2, dot_size/2)

        painter.restore()

    def add_appointment(self, date, time, patient, appointment_type, appointment_data=None):
        if date not in self.appointments:
            self.appointments[date] = []
        self.appointments[date].append((time, patient, appointment_type, appointment_data))
        self.updateCell(date)


class EditAppointmentDialog(QDialog):
    def __init__(self, parent=None, username=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("Modificar Cita")
        self.setMinimumWidth(450)
        self.setStyleSheet(f"background-color: {SaaSTheme.COLOR_BG_MAIN}; {SaaSTheme.get_stylesheet()}")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Editar Registro")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {SaaSTheme.COLOR_CARBON}; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Form Container
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        
        # Estilo labels
        lbl_style = f"font-weight: 600; color: {SaaSTheme.COLOR_TEXT_SECONDARY}; font-size: 12px; text-transform: uppercase;"
        
        # Widgets
        self.patient_dni_entry = QLineEdit()
        self.patient_dni_entry.setStyleSheet(SaaSTheme.input_style())
        
        btn_select = QPushButton("Buscar Paciente")
        btn_select.setCursor(Qt.PointingHandCursor)
        btn_select.setStyleSheet(SaaSTheme.btn_secondary())
        btn_select.clicked.connect(self.select_patient)
        
        self.patient_name_label = QLabel("—")
        self.patient_name_label.setStyleSheet(f"color: {SaaSTheme.COLOR_CARBON}; font-weight: bold;")
        
        self.date_edit = QDateEdit(calendarPopup=True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setStyleSheet(SaaSTheme.input_style())
        
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setStyleSheet(SaaSTheme.input_style())
        
        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText("Ingrese notas clínicas o administrativas...")
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setStyleSheet(SaaSTheme.input_style())
        
        # Añadir filas
        l1 = QLabel("DNI Paciente"); l1.setStyleSheet(lbl_style)
        form_layout.addRow(l1, self.patient_dni_entry)
        form_layout.addRow("", btn_select)
        
        l2 = QLabel("Nombre"); l2.setStyleSheet(lbl_style)
        form_layout.addRow(l2, self.patient_name_label)
        
        l3 = QLabel("Fecha Programada"); l3.setStyleSheet(lbl_style)
        form_layout.addRow(l3, self.date_edit)
        
        l4 = QLabel("Hora"); l4.setStyleSheet(lbl_style)
        form_layout.addRow(l4, self.time_edit)
        
        l5 = QLabel("Observaciones"); l5.setStyleSheet(lbl_style)
        form_layout.addRow(l5, self.notes_text)
        
        layout.addLayout(form_layout)
        
        # Botones Footer
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(SaaSTheme.btn_secondary())
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Guardar Cambios")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(SaaSTheme.btn_primary())
        save_btn.clicked.connect(self.accept)
        
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        layout.addLayout(btn_box)

    def select_patient(self):
        dialog = SeleccionarPacientesDialog(self, username=self.username)
        if dialog.exec_() == QDialog.Accepted:
            selected_dni = dialog.selected_dni
            if selected_dni:
                self.patient_dni_entry.setText(selected_dni)
                self.update_patient_name(selected_dni)

    def update_patient_name(self, dni):
        cache = get_global_cache()
        pacientes = cache.get_pacientes(self.username)
        paciente_data = next((p for p in pacientes if p.get('dni') == dni), None)
        if paciente_data:
            self.patient_name_label.setText(paciente_data.get('nombre', '—'))
        else:
            self.patient_name_label.setText("—")

    def set_appointment_data(self, data):
        self.patient_dni_entry.setText(data.get('dni', ''))
        self.update_patient_name(data.get('dni', ''))
        if 'fecha' in data:
            self.date_edit.setDate(QDate.fromString(data['fecha'], "yyyy-MM-dd"))
        if 'hora' in data:
            self.time_edit.setTime(QTime.fromString(data['hora'], "hh:mm"))
        self.notes_text.setPlainText(data.get('notas', ''))

    def get_appointment_data(self):
        return {
            'dni': self.patient_dni_entry.text().strip(),
            'fecha': self.date_edit.date().toString("yyyy-MM-dd"),
            'hora': self.time_edit.time().toString("hh:mm"),
            'notas': self.notes_text.toPlainText().strip()
        }


class PendingAppointmentsDialog(QDialog):
    """Diálogo para ver lista detallada de citas pendientes."""
    def __init__(self, title, appointments, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)
        self.appointments = appointments
        self.selected_date = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        lbl = QLabel(f"{len(self.appointments)} Citas Pendientes")
        lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {SaaSTheme.COLOR_CARBON};")
        layout.addWidget(lbl)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Fecha", "Hora", "Paciente", "DNI"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.on_row_double_clicked)
        
        # Style table
        self.table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 4px;
                gridline-color: {SaaSTheme.COLOR_BORDER};
            }}
            QHeaderView::section {{
                background-color: {SaaSTheme.COLOR_BG_SECONDARY};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
        """)
        
        # Populate
        self.table.setRowCount(len(self.appointments))
        for i, appt in enumerate(self.appointments):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(appt.get('fecha', '')))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(appt.get('hora', '')))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(appt.get('nombre_paciente', '')))
            self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(appt.get('dni', '')))
            
        layout.addWidget(self.table)
        
        help_lbl = QLabel("💡 Doble clic en una cita para ir a ella en el calendario.")
        help_lbl.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(help_lbl)
        
        btn_close = QPushButton("Cerrar")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(SaaSTheme.btn_secondary())
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def on_row_double_clicked(self, index):
        row = index.row()
        date_str = self.table.item(row, 0).text()
        if date_str:
            self.selected_date = date_str
            self.accept()


class AppointmentDetailsWidget(QFrame):
    def __init__(self, parent=None, appointments_page=None):
        super().__init__(parent)
        self.appointments_page = appointments_page
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"background-color: {SaaSTheme.COLOR_BG_SECONDARY};")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)
        
        # --- HEADER CON NOTIFICACIONES ---
        header_layout = QHBoxLayout()
        
        self.header_label = QLabel("Agenda Diaria")
        self.header_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {SaaSTheme.COLOR_CARBON}; border: none;")
        header_layout.addWidget(self.header_label)
        
        # Badge Esta Semana (Rojo) - CLICKABLE
        self.weekly_badge = QPushButton("")
        self.weekly_badge.setCursor(Qt.PointingHandCursor)
        self.weekly_badge.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F; 
                color: white; 
                font-weight: bold; 
                font-size: 11px; 
                padding: 4px 8px; 
                border-radius: 8px;
                border: none;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
        """)
        self.weekly_badge.setVisible(False)
        self.weekly_badge.clicked.connect(lambda: self.show_pending_details("current"))
        header_layout.addWidget(self.weekly_badge)

        # Badge Próxima Semana (Azul) - CLICKABLE
        self.next_week_badge = QPushButton("")
        self.next_week_badge.setCursor(Qt.PointingHandCursor)
        self.next_week_badge.setStyleSheet("""
            QPushButton {
                background-color: #1976D2; 
                color: white; 
                font-weight: bold; 
                font-size: 11px; 
                padding: 4px 8px; 
                border-radius: 8px;
                border: none;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        self.next_week_badge.setVisible(False)
        self.next_week_badge.clicked.connect(lambda: self.show_pending_details("next"))
        header_layout.addWidget(self.next_week_badge)
        
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # --- BUSCADOR GLOBAL (Fluido con QCompleter) ---
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText("🔍 Buscar cita por nombre o DNI (Escribe para ver sugerencias)...")
        self.global_search.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 8px;
                padding: 10px 15px;
                background-color: white;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {SaaSTheme.COLOR_CARBON}; }}
        """)
        
        # Mapa para vincular texto -> objeto cita
        self.search_map = {}
        
        # Configurar Completer
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.activated.connect(self.on_search_selected)
        self.global_search.setCompleter(self.completer)
        
        # Actualizar sugerencias con una espera corta para no bloquear al escribir.
        self._search_suggestions_timer = QtCore.QTimer(self)
        self._search_suggestions_timer.setSingleShot(True)
        self._search_suggestions_timer.timeout.connect(
            lambda: self.update_search_suggestions(self.global_search.text())
        )
        self.global_search.textChanged.connect(self._schedule_search_suggestions)
        
        self.layout.addWidget(self.global_search)
        
        # Área de scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        self.appointments_container = QWidget()
        self.appointments_container.setStyleSheet("background: transparent;")
        self.appointments_layout = QVBoxLayout(self.appointments_container)
        self.appointments_layout.setContentsMargins(0, 0, 0, 0)
        self.appointments_layout.setSpacing(12)
        self.appointments_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.appointments_container)
        self.layout.addWidget(scroll)

    def show_pending_details(self, period):
        """Muestra un diálogo con las citas pendientes del periodo seleccionado."""
        if not self.appointments_page: return
        
        cache = get_global_cache()
        todas_citas = cache.get_citas(self.appointments_page.username)
        
        today = QDate.currentDate()
        start_this = today.addDays(-(today.dayOfWeek() - 1))
        end_this = start_this.addDays(6)
        start_next = start_this.addDays(7)
        end_next = start_next.addDays(6)
        
        filtered_list = []
        title = ""
        
        for cita in todas_citas:
            if cita.get('estado') != 'Pendiente': continue
            
            fecha_str = cita.get('fecha', '')
            if not fecha_str: continue
            q_date = QDate.fromString(fecha_str, "yyyy-MM-dd")
            
            if period == "current":
                if start_this <= q_date <= end_this:
                    filtered_list.append(cita)
                title = "Pendientes - Esta Semana"
            elif period == "next":
                if start_next <= q_date <= end_next:
                    filtered_list.append(cita)
                title = "Pendientes - Próxima Semana"
        
        # Ordenar por fecha y hora
        filtered_list.sort(key=lambda x: (x.get('fecha'), x.get('hora')))
        
        if not filtered_list:
            return

        dialog = PendingAppointmentsDialog(title, filtered_list, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_date:
             # Saltar a la fecha seleccionada
             q_date = QDate.fromString(dialog.selected_date, "yyyy-MM-dd")
             if q_date.isValid():
                 self.appointments_page.calendar.setSelectedDate(q_date)

    def update_weekly_badge(self):
        """Calcula y muestra las citas pendientes de esta semana y la próxima."""
        if not self.appointments_page: return
        
        cache = get_global_cache()
        todas_citas = cache.get_citas(self.appointments_page.username)
        
        today = QDate.currentDate()
        # Esta semana (Lunes a Domingo)
        start_this = today.addDays(-(today.dayOfWeek() - 1))
        end_this = start_this.addDays(6)
        # Próxima semana
        start_next = start_this.addDays(7)
        end_next = start_next.addDays(6)
        
        c_this = 0
        c_next = 0
        
        for cita in todas_citas:
            if cita.get('estado') != 'Pendiente': continue
            
            fecha_str = cita.get('fecha', '')
            if not fecha_str: continue
            q_date = QDate.fromString(fecha_str, "yyyy-MM-dd")
            
            if start_this <= q_date <= end_this:
                c_this += 1
            elif start_next <= q_date <= end_next:
                c_next += 1
        
        # Actualizar Badges
        if c_this > 0:
            self.weekly_badge.setText(f"Tienes ({c_this}) esta semana")
            self.weekly_badge.setVisible(True)
        else:
            self.weekly_badge.setVisible(False)
            
        if c_next > 0:
            self.next_week_badge.setText(f"Tienes ({c_next}) próxima semana")
            self.next_week_badge.setVisible(True)
        else:
            self.next_week_badge.setVisible(False)

    def _schedule_search_suggestions(self, *_args):
        self._search_suggestions_timer.start(300)

    def update_search_suggestions(self, text):
        """Actualiza la lista del autocompletado sin bloquear la UI."""
        if len(text) < 2 or not self.appointments_page: return

        cache = get_global_cache()
        todas_citas = cache.get_citas(self.appointments_page.username)
        
        suggestions = []
        self.search_map = {}
        text_lower = text.lower()
        
        # Ordenar por fecha (reciente primero)
        citas_ordenadas = sorted(todas_citas, key=lambda x: x.get('fecha', ''), reverse=True)
        
        for cita in citas_ordenadas:
            if len(suggestions) > 15: break
            
            nombre = str(cita.get('nombre_paciente', '')).upper()
            dni = str(cita.get('dni', ''))
            fecha = cita.get('fecha', '')
            
            if text_lower in nombre.lower() or text_lower in dni:
                display_text = f"{nombre} ({dni}) - {fecha}"
                suggestions.append(display_text)
                self.search_map[display_text] = cita
        
        model = QStringListModel(suggestions)
        self.completer.setModel(model)

    def on_search_selected(self, text):
        """Maneja la selección de una sugerencia."""
        cita = self.search_map.get(text)
        if cita:
            self.ir_a_cita(cita)

    def ir_a_cita(self, cita):
        """Salta a la fecha de la cita seleccionada en el buscador."""
        try:
            if not self.appointments_page: return
            fecha_str = cita.get('fecha', '')
            if fecha_str:
                q_date = QDate.fromString(fecha_str, "yyyy-MM-dd")
                if q_date.isValid():
                    self.appointments_page.calendar.setSelectedDate(q_date)
                    self.global_search.clear()
        except Exception as e:
            print(f"Error al ir a cita: {e}")

    def create_card(self, idx, time, patient, appt_type, appointment_data=None):
        """Crea una tarjeta de cita estilo 'Card' profesional"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {SaaSTheme.COLOR_BG_MAIN};
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 6px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        
        # Fila superior: Hora y Estado
        top_row = QHBoxLayout()
        time_lbl = QLabel(time)
        time_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {SaaSTheme.COLOR_CARBON}; border: none;")
        
        # Estado badge dinámico
        estado = appointment_data.get('estado', 'Pendiente') if appointment_data else 'Pendiente'
        status_badge = QLabel(estado.upper())
        
        # Estilos según el estado
        if estado == AppointmentStatus.COMPLETED.value or estado == 'Completada':
            badge_style = f"""
                background-color: #E8F5E9; 
                color: #1B5E20; 
                border: 1px solid #C8E6C9;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 700;
            """
        elif estado == AppointmentStatus.CANCELLED.value or estado == 'Cancelada':
            badge_style = f"""
                background-color: #FFEBEE; 
                color: #C62828; 
                border: 1px solid #FFCDD2;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 700;
            """
        else:  # PENDING (default)
            badge_style = f"""
                background-color: #FFF4E5; 
                color: #663C00; 
                border: 1px solid #FFE0B2;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 700;
            """
        
        status_badge.setStyleSheet(badge_style)
        
        top_row.addWidget(time_lbl)
        top_row.addWidget(status_badge)
        top_row.addStretch()
        
        # Fila media: Paciente
        mid_row = QVBoxLayout()
        mid_row.setSpacing(2)
        p_name = QLabel(patient)
        p_name.setStyleSheet(f"font-size: 14px; font-weight: 500; color: {SaaSTheme.COLOR_CARBON}; border: none;")
        p_type = QLabel(appt_type)
        p_type.setStyleSheet(f"font-size: 12px; color: {SaaSTheme.COLOR_TEXT_SECONDARY}; border: none;")
        
        mid_row.addWidget(p_name)
        mid_row.addWidget(p_type)
        
        # Fila inferior: Acciones
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 10, 0, 0)
        
        btn_edit = QPushButton("Editar")
        btn_edit.setStyleSheet(SaaSTheme.btn_secondary())
        btn_edit.clicked.connect(lambda: self.edit_appointment(appointment_data))
        
        btn_complete = QPushButton("Completar")
        btn_complete.setStyleSheet(SaaSTheme.btn_secondary())
        btn_complete.clicked.connect(lambda: self.complete_appointment(appointment_data))
        
        # Deshabilitar botón completar solo si está completado
        is_completed = (estado and 
                       (estado == AppointmentStatus.COMPLETED.value or 
                        estado == 'Completada'))
        
        if is_completed:
            btn_complete.setEnabled(False)
            btn_complete.setStyleSheet(f"""
                QPushButton {{
                    background-color: #E0E0E0;
                    color: #999999;
                    border: 1px solid #CCCCCC;
                    border-radius: 6px;
                    padding: 10px 16px;
                    font-weight: 600;
                    font-size: 13px;
                }}
            """)
        
        action_row.addWidget(btn_edit)
        action_row.addWidget(btn_complete)
        action_row.addStretch()
        
        card_layout.addLayout(top_row)
        card_layout.addLayout(mid_row)
        card_layout.addLayout(action_row)
        
        return card
    
    def edit_appointment(self, appointment_data):
        """Abre el diálogo para editar una cita"""
        if not appointment_data or not self.appointments_page:
            return
        
        # Convertir diccionario a objeto Appointment
        from utils.appointments_model import Appointment, AppointmentType, AppointmentStatus
        try:
            appt = Appointment(
                dni=appointment_data.get('dni', ''),
                nombre_paciente=appointment_data.get('nombre_paciente', ''),
                fecha=appointment_data.get('fecha', ''),
                hora=appointment_data.get('hora', ''),
                duracion_minutos=appointment_data.get('duracion_minutos', 30),
                tipo=AppointmentType(appointment_data.get('tipo', 'Consulta General')),
                estado=AppointmentStatus(appointment_data.get('estado', 'Pendiente')),
                doctor=appointment_data.get('doctor', ''),
                notas=appointment_data.get('notas', ''),
                recordatorios=[]
            )
            if 'cita_id' in appointment_data:
                appt.cita_id = appointment_data['cita_id']
        except:
            appt = None
        
        if not appt:
            return
        
        dialog = AppointmentDialog(self.appointments_page.parent_app, username=self.appointments_page.username, appointment=appt)
        if dialog.exec_() == QDialog.Accepted:
            # Limpiar caché para asegurar que se vean los cambios guardados por el diálogo
            from utils.data_cache_manager import get_global_cache
            get_global_cache().clear_data_type(self.appointments_page.username, 'citas')
            
            # Recargar citas después de editar
            self.appointments_page.load_appointments()
            self.appointments_page.update_selected_date()
    
    def complete_appointment(self, appointment_data):
        """Marca una cita como completada"""
        if not appointment_data or not self.appointments_page:
            return
        
        try:
            # Guardar en cache
            cache = get_global_cache()
            citas = cache.get_citas(self.appointments_page.username)
            
            cita_id = appointment_data.get('cita_id')
            encontrada = False
            
            # Intento 1: Buscar por ID único (más seguro)
            if cita_id:
                for cita in citas:
                    if cita.get('cita_id') == cita_id:
                        cita['estado'] = AppointmentStatus.COMPLETED.value
                        cita['updated_at'] = QtCore.QDateTime.currentDateTime().toString(Qt.ISODate)
                        encontrada = True
                        break
            
            # Intento 2: Fallback a búsqueda por datos (legacy)
            if not encontrada:
                print("[DEBUG] Cita ID no encontrado, usando búsqueda por campos")
                for cita in citas:
                    if (cita.get('fecha') == appointment_data.get('fecha') and 
                        cita.get('hora') == appointment_data.get('hora') and
                        cita.get('dni') == appointment_data.get('dni')):
                        cita['estado'] = AppointmentStatus.COMPLETED.value
                        cita['updated_at'] = QtCore.QDateTime.currentDateTime().toString(Qt.ISODate)
                        encontrada = True
                        break
            
            if encontrada:
                cache.update_citas(self.appointments_page.username, citas)
                print(f"[DEBUG] Cita completada exitosamente: {cita_id}")
                
                # Recargar vista
                self.appointments_page.load_appointments()
                self.appointments_page.update_selected_date()
                
                # Feedback visual
                QMessageBox.information(self, "Éxito", "La cita ha sido marcada como completada.")
            else:
                print(f"[ERROR] No se encontró la cita para actualizar: {appointment_data}")
                QMessageBox.warning(self, "Error", "No se pudo encontrar la cita para actualizar.")
                
        except Exception as e:
            print(f"Error completando cita: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Ocurrió un error al completar la cita: {e}")

    def update_appointments(self, date, appointments):
        # Limpiar
        for i in reversed(range(self.appointments_layout.count())):
            w = self.appointments_layout.itemAt(i).widget()
            if w: w.deleteLater()
            
        date_str = date.toString('dddd, d MMMM yyyy').upper()
        self.header_label.setText(date_str)
        
        if not appointments:
            empty_state = QLabel("Sin actividades programadas")
            empty_state.setAlignment(Qt.AlignCenter)
            empty_state.setStyleSheet(f"color: {SaaSTheme.COLOR_TEXT_SECONDARY}; font-size: 14px; margin-top: 40px; border: none;")
            self.appointments_layout.addWidget(empty_state)
            return
            
        # Lógica de prioridad: Pendiente (0), Otros (1), Completada (2)
        def get_priority(appt_tuple):
            data = appt_tuple[3] if len(appt_tuple) > 3 else {}
            estado = data.get('estado', 'Pendiente')
            if estado == 'Pendiente': return 0
            if estado == 'Completada': return 2
            return 1

        # Ordenar por prioridad y luego por hora
        appointments_sorted = sorted(appointments, key=lambda x: (get_priority(x), x[0]))

        for idx, appt_info in enumerate(appointments_sorted):
            time, patient, appt_type, appointment_data = appt_info if len(appt_info) > 3 else (*appt_info, None)
            card = self.create_card(idx, time, patient, appt_type, appointment_data)
            self.appointments_layout.addWidget(card)


class AppointmentsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = parent.username if parent else None
        
        # Layout principal dividido (Sidebar + Detalles)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- SIDEBAR (Izquierda) ---
        sidebar = QFrame()
        sidebar.setStyleSheet(f"background-color: {SaaSTheme.COLOR_BG_MAIN}; border-right: 1px solid {SaaSTheme.COLOR_BORDER};")
        sidebar.setFixedWidth(380) # Ancho fijo pro
        
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(25, 30, 25, 30)
        side_layout.setSpacing(20)
        
        # Título Sección
        lbl_cal = QLabel("Calendario")
        lbl_cal.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {SaaSTheme.COLOR_CARBON};")
        side_layout.addWidget(lbl_cal)
        
        # Calendario
        self.calendar = CustomCalendarWidget()
        side_layout.addWidget(self.calendar)
        
        side_layout.addSpacing(20)
        
        # Botonera Acciones (Stack Vertical)
        btn_new_appt = QPushButton("Nueva Cita")
        btn_new_appt.setIcon(ProIcon.draw("plus", color="#FFFFFF"))
        btn_new_appt.setStyleSheet(SaaSTheme.btn_primary())
        btn_new_appt.clicked.connect(self.show_appointment_dialog_with_date)
        
        btn_new_patient = QPushButton("Nuevo Paciente")
        btn_new_patient.setIcon(ProIcon.draw("user", color=SaaSTheme.COLOR_CARBON))
        btn_new_patient.setStyleSheet(SaaSTheme.btn_secondary())
        btn_new_patient.clicked.connect(self.show_new_patient_form)
        
        btn_stats = QPushButton("Reportes")
        btn_stats.setIcon(ProIcon.draw("chart", color=SaaSTheme.COLOR_CARBON))
        btn_stats.setStyleSheet(SaaSTheme.btn_secondary())
        btn_stats.clicked.connect(self.show_statistics)
        
        btn_refresh = QPushButton("Recargar Datos")
        try:
            btn_refresh.setIcon(ProIcon.draw("clock", color=SaaSTheme.COLOR_CARBON)) 
        except:
            pass
        btn_refresh.setStyleSheet(SaaSTheme.btn_secondary())
        btn_refresh.clicked.connect(self.refresh_data)
        
        side_layout.addWidget(btn_new_appt)
        side_layout.addWidget(btn_new_patient)
        side_layout.addWidget(btn_stats)
        side_layout.addWidget(btn_refresh)
        side_layout.addStretch()
        
        # Footer Sidebar
        lbl_ver = QLabel("v2.0.0 Pro")
        lbl_ver.setStyleSheet(f"color: {SaaSTheme.COLOR_BORDER}; font-size: 10px;")
        side_layout.addWidget(lbl_ver)
        
        # --- MAIN CONTENT (Derecha) ---
        self.appointment_details = AppointmentDetailsWidget(appointments_page=self)
        
        layout.addWidget(sidebar)
        layout.addWidget(self.appointment_details)
        
        # Conexiones y Carga
        self.calendar.selectionChanged.connect(self.update_selected_date)
        self.load_appointments()

    def refresh_data(self):
        """Recarga forzada de datos desde disco"""
        try:
            from utils.data_cache_manager import get_global_cache
            cache = get_global_cache()
            
            # Limpiar caché específica de este usuario
            cache.clear_data_type(self.username, 'citas')
            cache.clear_data_type(self.username, 'pacientes')
            
            # Recargar
            self.load_appointments()
            self.update_selected_date()
            
            # Feedback visual opcional
            # QMessageBox.information(self, "Actualizado", "Datos recargados correctamente.")
        except Exception as e:
            print(f"Error recargando datos: {e}")

    def show_appointment_dialog_with_date(self):
        """Abre el diálogo de cita con la fecha seleccionada en el calendario"""
        selected_date = self.calendar.selectedDate()
        dialog = AppointmentDialog(self, username=self.username, initial_date=selected_date)
        
        # Conectar señal para recargar cuando se guarde una cita
        dialog.appointment_saved.connect(lambda appt: self._on_appointment_saved(appt))
        
        if dialog.exec_() == QDialog.Accepted:
            # El diálogo ya actualiza la caché, solo recargar la vista
            self.load_appointments()
            self.update_selected_date()

    def show_appointment_dialog(self):
        dialog = AppointmentDialog(self, username=self.username)
        
        # Conectar señal para recargar cuando se guarde una cita
        dialog.appointment_saved.connect(lambda appt: self._on_appointment_saved(appt))
        
        if dialog.exec_() == QDialog.Accepted:
            # El diálogo ya actualiza la caché, solo recargar la vista
            self.load_appointments()
            self.update_selected_date()
    
    def _on_appointment_saved(self, appointment):
        """Se ejecuta cuando se guarda una cita desde el diálogo"""
        print(f"[DEBUG] Cita guardada en signal: {appointment.cita_id}")
        self.load_appointments()
        self.update_selected_date()
            
    def show_new_patient_form(self):
        main_window = self.parent_app
        if hasattr(main_window, 'switch_to_page'):
            main_window.switch_to_page('create_patient')
            
    def load_appointments(self):
        self.calendar.appointments.clear()
        cache = get_global_cache()
        citas = cache.get_citas(self.username)
        pacientes = cache.get_pacientes(self.username)
        
        for cita in citas:
            try:
                f = QDate.fromString(cita['fecha'], "yyyy-MM-dd")
                
                # Preferir el nombre guardado en la cita (snapshot)
                p_name = cita.get('nombre_paciente', '')
                
                # Si no hay nombre guardado (legacy), buscar por DNI
                if not p_name or p_name == 'Desconocido':
                    p_data = next((p for p in pacientes if p.get('dni') == cita['dni']), None)
                    p_name = p_data.get('nombre', 'Desconocido') if p_data else "Desconocido"
                
                self.calendar.add_appointment(f, cita['hora'], f"{p_name}", "Consulta General", cita)
            except:
                continue
        
        # Actualizar notificaciones semanales
        if hasattr(self, 'appointment_details'):
            self.appointment_details.update_weekly_badge()
            
        self.update_selected_date()
        
    def update_selected_date(self):
        date = self.calendar.selectedDate()
        appts = self.calendar.appointments.get(date, [])
        try:
            appts_sorted = sorted(appts, key=lambda x: x[0])
        except:
            appts_sorted = appts
        self.appointment_details.update_appointments(date, appts_sorted)

    def show_statistics(self):
        stats = AppointmentsStatistics(self.username)
        resumen = stats.obtener_resumen_dashboard()
        # Aquí podrías abrir un QDialog personalizado con el estilo nuevo
        QMessageBox.information(self, "Reporte", f"Total Citas: {resumen['total_citas']}")

# ==============================================================================
# CLASES DE COMPATIBILIDAD Y PÁGINAS ADICIONALES
# ==============================================================================

class AppointmentHistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = parent.username if parent else None
        self.all_appointments_data = [] # Cache para filtrado local
        self._filter_timer = QtCore.QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self.filter_data)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Historial Completo")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {SaaSTheme.COLOR_CARBON};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # --- FILTROS Y BUSCADOR ---
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)
        
        # Buscador
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por paciente, DNI o notas...")
        self.search_input.setStyleSheet(SaaSTheme.input_style())
        self.search_input.textChanged.connect(self._schedule_filter_data)
        
        # Filtro de Estado
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Todos los Estados", "Pendiente", "Completada", "Cancelada", "No-Show"])
        self.status_filter.setStyleSheet(SaaSTheme.input_style())
        self.status_filter.currentIndexChanged.connect(self.filter_data)
        self.status_filter.setFixedWidth(180)
        
        filters_layout.addWidget(self.search_input, 1) # Expandible
        filters_layout.addWidget(self.status_filter, 0)
        layout.addLayout(filters_layout)
        
        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(5) # Agregamos columna Estado
        self.table.setHorizontalHeaderLabels(["FECHA", "HORA", "PACIENTE", "ESTADO", "NOTAS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Hora
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents) # Estado
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Estilo de tabla profesional
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {SaaSTheme.COLOR_BG_MAIN};
                gridline-color: {SaaSTheme.COLOR_BORDER};
            }}
            QHeaderView::section {{
                background-color: {SaaSTheme.COLOR_BG_MAIN};
                color: {SaaSTheme.COLOR_TEXT_SECONDARY};
                padding: 12px;
                border: none;
                border-bottom: 2px solid {SaaSTheme.COLOR_BORDER};
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {SaaSTheme.COLOR_BORDER};
                color: {SaaSTheme.COLOR_CARBON};
            }}
            QTableWidget::item:selected {{
                background-color: {SaaSTheme.COLOR_BG_SECONDARY};
                color: {SaaSTheme.COLOR_CARBON};
            }}
        """)
        layout.addWidget(self.table)
        
    def load_appointments(self):
        """Carga datos, los ordena y los guarda en memoria."""
        if not self.username: return
        
        cache = get_global_cache()
        todas_citas = cache.get_citas(self.username)
        pacientes = cache.get_pacientes(self.username)
        
        # Lógica de prioridad: Pendiente (0), Otros (1), Completada (2)
        def get_priority(cita):
            estado = cita.get('estado', 'Pendiente')
            if estado == 'Pendiente': return 0
            if estado == 'Completada': return 2
            return 1

        # Ordenar: Prioridad -> Fecha (Desc)
        # Usamos reverse=False porque prioridad 0 (Pendiente) debe ir primero
        citas_sorted = sorted(
            todas_citas, 
            key=lambda x: (get_priority(x), x['fecha']), 
            reverse=False 
        )
        
        # Preparar datos completos en memoria
        self.all_appointments_data = []
        
        for cita in citas_sorted:
            # Buscar nombre de paciente
            p_name = cita.get('nombre_paciente', '')
            if not p_name:
                p_data = next((p for p in pacientes if p.get('dni') == cita.get('dni')), None)
                p_name = p_data.get('nombre', 'N/A') if p_data else "N/A"
            
            self.all_appointments_data.append({
                "fecha": cita.get("fecha", ""),
                "hora": cita.get("hora", ""),
                "paciente": p_name,
                "dni": cita.get("dni", ""),
                "estado": cita.get("estado", "Pendiente"),
                "notas": cita.get("notas", ""),
                "raw_data": cita
            })
            
        # Aplicar filtro inicial
        self.filter_data()

    def _schedule_filter_data(self, *_args):
        self._filter_timer.start(350)

    def filter_data(self):
        """Filtra y muestra los datos en la tabla."""
        self.table.setRowCount(0)
        
        search_text = self.search_input.text().lower().strip()
        status_filter = self.status_filter.currentText()
        
        filtered_rows = []
        
        for item in self.all_appointments_data:
            # 1. Filtro de Texto
            match_text = (
                search_text in item['paciente'].lower() or
                search_text in item['dni'].lower() or
                search_text in item['notas'].lower()
            )
            
            # 2. Filtro de Estado
            match_status = True
            if status_filter != "Todos los Estados":
                # Comparar con el estado del item (puede venir en inglés o español, normalizamos un poco)
                status_item = item['estado']
                # Mapeo simple por si acaso (aunque los datos deberían ser consistentes)
                if status_filter == "Pendiente" and status_item != "Pendiente": match_status = False
                elif status_filter == "Completada" and status_item != "Completada": match_status = False
                elif status_filter == "Cancelada" and status_item != "Cancelada": match_status = False
                elif status_filter == "No-Show" and status_item not in ["No-Show", "No presentado"]: match_status = False
            
            if match_text and match_status:
                filtered_rows.append(item)
        
        # Renderizar en tabla
        for row, item in enumerate(filtered_rows):
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(item["fecha"]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(item["hora"]))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(item["paciente"]))
            
            # Item Estado con Color
            est_item = QtWidgets.QTableWidgetItem(item["estado"])
            est_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            if item["estado"] == "Pendiente":
                est_item.setForeground(QColor(SaaSTheme.COLOR_ACCENT)) # Negro/Oscuro
            elif item["estado"] == "Completada":
                est_item.setForeground(QColor(SaaSTheme.COLOR_SUCCESS)) # Verde
            elif item["estado"] in ["Cancelada", "No-Show"]:
                est_item.setForeground(QColor(SaaSTheme.COLOR_DANGER)) # Rojo
                
            self.table.setItem(row, 3, est_item)
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(item["notas"]))

class PastAppointmentsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_widget = AppointmentHistoryWidget(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.history_widget)

    def load_past_appointments(self):
        self.history_widget.load_appointments()

# Wrappers para mantener compatibilidad con tu sistema de navegación
class CreateAppointmentPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page = AppointmentsPage(parent)
        QVBoxLayout(self).addWidget(self.page)

class UpcomingAppointmentsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page = AppointmentsPage(parent)
        QVBoxLayout(self).addWidget(self.page)
