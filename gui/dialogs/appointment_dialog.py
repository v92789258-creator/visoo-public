from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QSpinBox, QDateEdit, QTimeEdit, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QWidget, QGridLayout, QTextEdit, QFrame,
    QCheckBox, QGraphicsDropShadowEffect, QLineEdit
)
from PyQt5.QtCore import Qt, QDate, QTime, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap, QPainterPath
from typing import Optional, List
import datetime

# Importamos modelos y managers (mantenemos tu lógica intacta)
from utils.appointments_model import (
    Appointment, AppointmentStatus, AppointmentType, 
    ReminderType, AppointmentsManager
)
from utils.schedule_manager import ScheduleManager
from utils.file_handler import cargar_optometras
from gui.dialogs.paciente_selector_dialog import PacienteSelectorDialog

# ==============================================================================
# SISTEMA DE DISEÑO (Reutilizado para consistencia)
# ==============================================================================

class PacienteLineEdit(QLineEdit):
    """QLineEdit personalizado para almacenar datos del paciente"""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
        self.setCursor(Qt.PointingHandCursor)
    
    def setData(self, data: dict):
        self._data = data
    
    def data(self) -> dict:
        return self._data

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class SaaSTheme:
    COLOR_BG = "#FFFFFF"
    COLOR_BG_SEC = "#FAFAFA"
    COLOR_CARBON = "#111111"
    COLOR_TEXT = "#111111"
    COLOR_TEXT_LIGHT = "#6B7280"
    COLOR_BORDER = "#E5E7EB"
    COLOR_FOCUS = "#000000"
    COLOR_ERROR = "#EF4444"
    COLOR_SUCCESS = "#10B981"
    
    FONT_MAIN = "Segoe UI, Inter, Arial"

    @staticmethod
    def get_input_style():
        return f"""
            QComboBox, QSpinBox, QDateEdit, QTimeEdit, QTextEdit, QLineEdit {{
                background-color: {SaaSTheme.COLOR_BG};
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 6px;
                padding: 10px;
                color: {SaaSTheme.COLOR_TEXT};
                font-family: '{SaaSTheme.FONT_MAIN}';
                font-size: 13px;
            }}
            QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QTextEdit:focus, QLineEdit:focus {{
                border: 1px solid {SaaSTheme.COLOR_FOCUS};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QDateEdit::drop-down {{ border: none; width: 20px; }}
            QLineEdit[readOnly="true"] {{
                background-color: {SaaSTheme.COLOR_BG_SEC};
            }}
            QLineEdit[readOnly="true"]:hover {{
                border: 1px solid {SaaSTheme.COLOR_CARBON};
                background-color: {SaaSTheme.COLOR_BG};
            }}
        """

    @staticmethod
    def get_label_style():
        return f"""
            color: {SaaSTheme.COLOR_TEXT_LIGHT};
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-family: '{SaaSTheme.FONT_MAIN}';
            margin-bottom: 4px;
        """

# Helper para iconos vectoriales sin emojis
class ProIcon:
    @staticmethod
    def draw(name, size=14, color="#111111"):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(2)
        painter.setPen(pen)
        
        if name == "clock":
            painter.drawEllipse(1, 1, size-2, size-2)
            painter.drawLine(size//2, size//2, size//2, 3)
            painter.drawLine(size//2, size//2, size-3, size//2)
        elif name == "check":
            path = QPainterPath()
            path.moveTo(2, size//2)
            path.lineTo(size//2-1, size-3)
            path.lineTo(size-2, 3)
            painter.drawPath(path)
        elif name == "close":
            painter.drawLine(3, 3, size-3, size-3)
            painter.drawLine(3, size-3, size-3, 3)
            
        painter.end()
        return pixmap

# ==============================================================================
# DIÁLOGO PRINCIPAL
# ==============================================================================

class AppointmentDialog(QDialog):
    """Diálogo profesional para gestión de citas SaaS Style"""
    
    appointment_saved = pyqtSignal(Appointment)
    
    def __init__(self, parent=None, username: str = "default", 
                 appointment: Optional[Appointment] = None,
                 initial_date: Optional['QDate'] = None):
        super().__init__(parent)
        self.username = username
        self.appointment = appointment
        self.initial_date = initial_date
        
        # Managers
        self.appointments_manager = AppointmentsManager(username)
        self.schedule_manager = ScheduleManager(username)
        
        # Configuración Ventana
        self.setModal(True)
        self.setWindowTitle("Gestión de Cita")
        self.setMinimumSize(850, 600)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {SaaSTheme.COLOR_BG}; }}
            QLabel {{ font-family: '{SaaSTheme.FONT_MAIN}'; }}
            QCheckBox {{ spacing: 8px; color: {SaaSTheme.COLOR_TEXT}; font-size: 13px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {SaaSTheme.COLOR_BORDER}; border-radius: 4px; }}
            QCheckBox::indicator:checked {{ background-color: {SaaSTheme.COLOR_CARBON}; border-color: {SaaSTheme.COLOR_CARBON}; }}
        """)
        
        self.init_ui()
        if appointment:
            self.cargar_datos()
        else:
            # Para nuevas citas, actualizar disponibilidad con la fecha inicial
            self.actualizar_disponibilidad()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # =================================================
        # COLUMNA IZQUIERDA: FORMULARIO (60%)
        # =================================================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 40, 40, 40)
        left_layout.setSpacing(25)
        
        # Header
        header_layout = QVBoxLayout()
        title = QLabel("Detalles de la Cita")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {SaaSTheme.COLOR_CARBON};")
        subtitle = QLabel("Complete la información requerida para agendar.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {SaaSTheme.COLOR_TEXT_LIGHT};")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        left_layout.addLayout(header_layout)
        
        # Grid Form
        form_grid = QGridLayout()
        form_grid.setVerticalSpacing(20)
        form_grid.setHorizontalSpacing(20)
        
        # Helper para crear campos con etiquetas pro
        def create_field(label_text, widget, row, col, colspan=1):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(SaaSTheme.get_label_style())
            widget.setStyleSheet(SaaSTheme.get_input_style())
            wrapper = QVBoxLayout()
            wrapper.setSpacing(6)
            wrapper.setContentsMargins(0,0,0,0)
            wrapper.addWidget(lbl)
            wrapper.addWidget(widget)
            form_grid.addLayout(wrapper, row, col, 1, colspan)

        # 1. Paciente (Full width)
        self.dni_input = PacienteLineEdit()
        self.dni_input.setPlaceholderText("Seleccionar paciente...")
        self.dni_input.setReadOnly(True)
        self.dni_input.clicked.connect(self.abrir_selector_pacientes)
        self.pacientes_disponibles = []
        
        # Cargar pacientes al inicializar
        self.cargar_pacientes()
        
        create_field("PACIENTE", self.dni_input, 0, 0, 2)
        
        # 2. Doctor (Full width)
        self.doctor_input = QComboBox()
        self.doctor_input.setEditable(True)
        create_field("ESPECIALISTA ASIGNADO", self.doctor_input, 1, 0, 2)
        self.cargar_oftalmologos()
        
        # 3. Fecha y Hora
        self.fecha_input = QDateEdit()
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setDisplayFormat("dd/MM/yyyy")
        if self.initial_date and self.initial_date.isValid():
            self.fecha_input.setDate(self.initial_date)
        else:
            self.fecha_input.setDate(QDate.currentDate())
        self.fecha_input.dateChanged.connect(self.actualizar_disponibilidad)
        
        self.hora_input = QTimeEdit()
        self.hora_input.setDisplayFormat("HH:mm")
        self.hora_input.setTime(QTime(9, 0))
        
        create_field("FECHA", self.fecha_input, 2, 0)
        create_field("HORA INICIO", self.hora_input, 2, 1)
        
        # 4. Duración y Tipo
        self.duracion_input = QSpinBox()
        self.duracion_input.setRange(15, 180)
        self.duracion_input.setValue(30)
        self.duracion_input.setSingleStep(15)
        self.duracion_input.setSuffix(" min")
        self.duracion_input.valueChanged.connect(self.actualizar_disponibilidad)
        
        self.tipo_input = QComboBox()
        self.tipo_input.addItems([t.value for t in AppointmentType])
        
        create_field("DURACIÓN", self.duracion_input, 3, 0)
        create_field("TIPO DE SERVICIO", self.tipo_input, 3, 1)
        
        left_layout.addLayout(form_grid)
        
        # 5. Notas (Text Area)
        lbl_notes = QLabel("NOTAS INTERNAS")
        lbl_notes.setStyleSheet(SaaSTheme.get_label_style())
        self.notas_input = QTextEdit()
        self.notas_input.setPlaceholderText("Alergias, observaciones previas...")
        self.notas_input.setMinimumHeight(80)
        self.notas_input.setStyleSheet(SaaSTheme.get_input_style())
        
        left_layout.addWidget(lbl_notes)
        left_layout.addWidget(self.notas_input)
        
        left_layout.addStretch()

        # =================================================
        # COLUMNA DERECHA: DISPONIBILIDAD (40%)
        # =================================================
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background-color: {SaaSTheme.COLOR_BG_SEC}; border-left: 1px solid {SaaSTheme.COLOR_BORDER};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(30, 40, 30, 40)
        right_layout.setSpacing(15)
        
        # Título Disponibilidad
        lbl_avail = QLabel("Disponibilidad")
        lbl_avail.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {SaaSTheme.COLOR_CARBON}; text-transform: uppercase;")
        right_layout.addWidget(lbl_avail)
        
        # Lista de Franjas (Estilo custom)
        self.disponibilidad_list = QListWidget()
        self.disponibilidad_list.setFrameShape(QFrame.NoFrame)
        self.disponibilidad_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                outline: none;
            }}
            QListWidget::item {{
                background-color: {SaaSTheme.COLOR_BG};
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
                color: {SaaSTheme.COLOR_TEXT};
            }}
            QListWidget::item:hover {{
                border-color: {SaaSTheme.COLOR_CARBON};
            }}
            QListWidget::item:selected {{
                background-color: {SaaSTheme.COLOR_CARBON};
                color: white;
                border: 1px solid {SaaSTheme.COLOR_CARBON};
            }}
        """)
        self.disponibilidad_list.itemClicked.connect(self.aplicar_franja)
        right_layout.addWidget(self.disponibilidad_list)
        
        # Widget de Conflicto (Alert Box)
        self.conflict_widget = QFrame()
        self.conflict_widget.setStyleSheet(f"""
            QFrame {{
                background-color: #FEF2F2;
                border: 1px solid #FCA5A5;
                border-radius: 6px;
            }}
            QLabel {{ color: {SaaSTheme.COLOR_ERROR}; font-weight: 600; border: none; }}
        """)
        self.conflict_widget.hide()
        cw_layout = QHBoxLayout(self.conflict_widget)
        self.conflict_label = QLabel("Conflicto detectado")
        cw_layout.addWidget(self.conflict_label)
        right_layout.addWidget(self.conflict_widget)

        right_layout.addStretch()
        
        # Botones de Acción (En columna derecha para flujo visual)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        self.guardar_btn = QPushButton("Guardar Cita")
        self.guardar_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SaaSTheme.COLOR_CARBON};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 14px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #333333; }}
            QPushButton:pressed {{ background-color: #000000; }}
        """)
        self.guardar_btn.clicked.connect(self.guardar_cita)
        
        self.cancelar_btn = QPushButton("Cancelar")
        self.cancelar_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {SaaSTheme.COLOR_CARBON};
                border: 1px solid {SaaSTheme.COLOR_BORDER};
                border-radius: 6px;
                padding: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {SaaSTheme.COLOR_BG_SEC}; }}
        """)
        self.cancelar_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.guardar_btn)
        btn_layout.addWidget(self.cancelar_btn)
        right_layout.addLayout(btn_layout)

        # Agregar paneles al layout principal
        main_layout.addWidget(left_panel, stretch=6)
        main_layout.addWidget(right_panel, stretch=4)
        
        # Inicializar
        self.actualizar_disponibilidad()

    # ==========================================================================
    # LÓGICA (Mantenida igual pero adaptada a UI nueva)
    # ==========================================================================
    
    def abrir_selector_pacientes(self):
        """Abre el diálogo de selección de pacientes"""
        print("[DEBUG] Abriendo selector de pacientes...")
        selector = PacienteSelectorDialog(self, self.username, self.pacientes_disponibles)
        selector.paciente_selected.connect(self.paciente_seleccionado)
        selector.exec_()
    
    def paciente_seleccionado(self, dni: str, nombre: str):
        """Se ejecuta cuando se selecciona un paciente"""
        print(f"[DEBUG] Paciente seleccionado: {nombre} ({dni})")
        self.dni_input.setText(f"{nombre} ({dni})")
        self.dni_input.setData({'dni': dni, 'nombre': nombre})
        self.actualizar_disponibilidad()
    
    def cargar_pacientes(self):
        try:
            from utils.data_cache_manager import get_global_cache
            cache = get_global_cache()
            self.pacientes_disponibles = cache.get_pacientes(self.username)
        except Exception as e:
            print(f"Error loading patients: {e}")
            self.pacientes_disponibles = []
    
    def cargar_oftalmologos(self):
        try:
            oftalmologos = cargar_optometras(self.username)
            self.doctor_input.blockSignals(True)
            self.doctor_input.clear()
            if oftalmologos:
                for doc in oftalmologos:
                    name = doc.get('nombre', str(doc)) if isinstance(doc, dict) else str(doc)
                    if name: self.doctor_input.addItem(name)
            else:
                self.doctor_input.addItems(["Dr. General"])
            self.doctor_input.blockSignals(False)
        except Exception:
            self.doctor_input.addItems(["Dr. General"])
    
    def actualizar_disponibilidad(self):
        try:
            fecha = self.fecha_input.date().toPyDate().isoformat()
            duracion = self.duracion_input.value()
            franjas = self.schedule_manager.obtener_franjas_disponibles(fecha, duracion)
            
            self.disponibilidad_list.clear()
            if not franjas:
                item = QListWidgetItem("No hay franjas disponibles")
                item.setFlags(Qt.NoItemFlags)
                self.disponibilidad_list.addItem(item)
            else:
                for franja in franjas:
                    # Formato limpio: "09:00 - 09:30"
                    item = QListWidgetItem(franja)
                    # Añadir icono de reloj programático
                    item.setIcon(QHbIcon(ProIcon.draw("clock", 12, SaaSTheme.COLOR_TEXT_LIGHT)))
                    self.disponibilidad_list.addItem(item)
            
            self.verificar_conflictos()
        except Exception as e:
            print(f"Error updating availability: {e}")
    
    def verificar_conflictos(self):
        try:
            fecha = self.fecha_input.date().toPyDate().isoformat()
            hora = self.hora_input.time().toString("HH:mm")
            duracion = self.duracion_input.value()
            
            hay_conflicto = self.appointments_manager.hay_conflicto(
                fecha, hora, duracion,
                excluir_cita_id=self.appointment.cita_id if self.appointment else None
            )
            
            if hay_conflicto:
                self.conflict_widget.show()
                self.conflict_label.setText("⚠️ Horario ocupado (Se guardará de todos modos)")
            else:
                self.conflict_widget.hide()
                
            # Siempre mantener el botón con estilo activo
            self.guardar_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {SaaSTheme.COLOR_CARBON};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 14px;
                    font-weight: 600;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: #333333; }}
                QPushButton:pressed {{ background-color: #000000; }}
            """)
        except Exception:
            pass
    
    def aplicar_franja(self, item: QListWidgetItem):
        txt = item.text()
        if " - " in txt:
            hora = txt.split(" - ")[0]
            self.hora_input.setTime(QTime.fromString(hora, "HH:mm"))
            self.verificar_conflictos()
    
    def cargar_datos(self):
        if not self.appointment: return
        
        # Cargar DNI y nombre
        paciente_data = next((p for p in self.pacientes_disponibles if p.get('dni') == self.appointment.dni), None)
        if paciente_data:
            nombre = paciente_data.get('nombre', '')
            self.dni_input.setText(f"{nombre} ({self.appointment.dni})")
            self.dni_input.setData({'dni': self.appointment.dni, 'nombre': nombre})
        else:
            self.dni_input.setText(f"({self.appointment.dni})")
            self.dni_input.setData({'dni': self.appointment.dni, 'nombre': ''})
        
        f = datetime.datetime.strptime(self.appointment.fecha, "%Y-%m-%d").date()
        self.fecha_input.setDate(f)
        
        h = datetime.datetime.strptime(self.appointment.hora, "%H:%M").time()
        self.hora_input.setTime(QTime(h.hour, h.minute))
        
        self.duracion_input.setValue(self.appointment.duracion_minutos)
        
        # Handle potential list type for doctor (legacy data fix)
        doctor_val = self.appointment.doctor
        if isinstance(doctor_val, list):
            doctor_val = doctor_val[0] if doctor_val else ""
        self.doctor_input.setCurrentText(str(doctor_val))
        
        self.notas_input.setText(self.appointment.notas)
        
        self.tipo_input.setCurrentText(self.appointment.tipo.value)
        
        self.actualizar_disponibilidad()

    def guardar_cita(self):
        try:
            # Obtener el DNI del QLineEdit
            data = self.dni_input.data() if hasattr(self.dni_input, 'data') else None
            dni = data.get('dni') if data else None
            nombre_paciente = data.get('nombre') if data else ""
            
            if not dni:
                QMessageBox.warning(self, "Requerido", "Por favor seleccione un paciente.")
                return
            
            fecha = self.fecha_input.date().toPyDate().isoformat()
            hora = self.hora_input.time().toString("HH:mm")
            duracion = self.duracion_input.value()
            
            # Validar Tipo
            tipo_txt = self.tipo_input.currentText()
            tipo = next((t for t in AppointmentType if t.value == tipo_txt), None)
            if not tipo: return

            doctor = self.doctor_input.currentText()
            notas = self.notas_input.toPlainText()
            
            # Simple y directo: Guardar sin preguntas bloqueantes
            if self.appointment:
                # Actualizar objeto local
                self.appointment.dni = dni
                self.appointment.nombre_paciente = nombre_paciente
                self.appointment.fecha = fecha
                self.appointment.hora = hora
                self.appointment.duracion_minutos = duracion
                self.appointment.tipo = tipo
                self.appointment.doctor = doctor
                self.appointment.notas = notas
                
                # Actualizar en el manager pasando el ID y los campos a actualizar
                self.appointments_manager.actualizar_cita(
                    self.appointment.cita_id,
                    dni=dni,
                    nombre_paciente=nombre_paciente,
                    fecha=fecha,
                    hora=hora,
                    duracion_minutos=duracion,
                    tipo=tipo,
                    doctor=doctor,
                    notas=notas
                )
                print(f"[DEBUG] Cita actualizada: {self.appointment.cita_id}")
            else:
                # Crear nueva cita usando argumentos con nombre para evitar errores de orden
                appt = Appointment(
                    dni=dni,
                    nombre_paciente=nombre_paciente,
                    fecha=fecha, 
                    hora=hora, 
                    duracion_minutos=duracion, 
                    tipo=tipo, 
                    doctor=doctor, 
                    notas=notas, 
                    estado=AppointmentStatus.PENDING,
                    recordatorios=[]
                )
                self.appointments_manager.agregar_cita(appt)
                self.appointment = appt
                print(f"[DEBUG] Cita creada: {appt.cita_id} - {nombre_paciente}")
            
            # IMPORTANTE: Actualizar la caché global para sincronizar con el resto de la aplicación
            try:
                from utils.data_cache_manager import get_global_cache
                cache = get_global_cache()
                # Obtener todas las citas del manager y guardarlas en la caché
                citas_dict = [c.to_dict() for c in self.appointments_manager.citas]
                print(f"[DEBUG] Guardando {len(citas_dict)} citas en caché")
                cache.update_citas(self.username, citas_dict)
                print(f"[DEBUG] Caché actualizada correctamente")
            except Exception as cache_error:
                print(f"❌ Advertencia: No se pudo actualizar caché global: {cache_error}")
                # No interrumpir el guardado si la caché falla
            
            # Mostrar confirmación con detalles de la cita
            self._mostrar_confirmacion_cita(self.appointment)
            
            self.appointment_saved.emit(self.appointment)
            self.accept()
            
        except Exception as e:
            print(f"[ERROR] Error guardando cita: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"No se pudo guardar la cita: {str(e)}")

    def _mostrar_confirmacion_cita(self, appointment):
        """Muestra una ventana de confirmación con los detalles de la cita registrada"""
        try:
            # Crear diálogo personalizado
            dialog = QDialog(self)
            dialog.setModal(True)
            dialog.setWindowTitle("✓ Cita Registrada")
            dialog.setMinimumWidth(450)
            dialog.setStyleSheet(f"""
                QDialog {{
                    background-color: {SaaSTheme.COLOR_BG};
                }}
            """)
            
            layout = QVBoxLayout()
            layout.setSpacing(15)
            layout.setContentsMargins(30, 30, 30, 30)
            
            # Título de éxito
            titulo = QLabel("✓ Cita Registrada Exitosamente")
            titulo.setStyleSheet(f"""
                color: {SaaSTheme.COLOR_SUCCESS};
                font-size: 16px;
                font-weight: 700;
            """)
            layout.addWidget(titulo)
            
            # Separador
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet(f"background-color: {SaaSTheme.COLOR_BORDER};")
            layout.addWidget(sep)
            
            # Detalles de la cita
            detalles_layout = QGridLayout()
            detalles_layout.setSpacing(12)
            
            # Paciente
            label_paciente = QLabel("Paciente:")
            label_paciente.setStyleSheet(f"color: {SaaSTheme.COLOR_TEXT_LIGHT}; font-weight: 600; font-size: 11px;")
            valor_paciente = QLabel(f"{appointment.nombre_paciente} ({appointment.dni})")
            valor_paciente.setStyleSheet(f"color: {SaaSTheme.COLOR_CARBON}; font-size: 13px;")
            detalles_layout.addWidget(label_paciente, 0, 0)
            detalles_layout.addWidget(valor_paciente, 0, 1)
            
            # Fecha y hora
            label_fecha = QLabel("Fecha y Hora:")
            label_fecha.setStyleSheet(f"color: {SaaSTheme.COLOR_TEXT_LIGHT}; font-weight: 600; font-size: 11px;")
            valor_fecha = QLabel(f"{appointment.fecha} a las {appointment.hora}")
            valor_fecha.setStyleSheet(f"color: {SaaSTheme.COLOR_CARBON}; font-size: 13px;")
            detalles_layout.addWidget(label_fecha, 1, 0)
            detalles_layout.addWidget(valor_fecha, 1, 1)
            
            # Duración
            label_duracion = QLabel("Duración:")
            label_duracion.setStyleSheet(f"color: {SaaSTheme.COLOR_TEXT_LIGHT}; font-weight: 600; font-size: 11px;")
            valor_duracion = QLabel(f"{appointment.duracion_minutos} minutos")
            valor_duracion.setStyleSheet(f"color: {SaaSTheme.COLOR_CARBON}; font-size: 13px;")
            detalles_layout.addWidget(label_duracion, 2, 0)
            detalles_layout.addWidget(valor_duracion, 2, 1)
            
            # Tipo de cita
            label_tipo = QLabel("Tipo:")
            label_tipo.setStyleSheet(f"color: {SaaSTheme.COLOR_TEXT_LIGHT}; font-weight: 600; font-size: 11px;")
            valor_tipo = QLabel(appointment.tipo.value)
            valor_tipo.setStyleSheet(f"color: {SaaSTheme.COLOR_CARBON}; font-size: 13px;")
            detalles_layout.addWidget(label_tipo, 3, 0)
            detalles_layout.addWidget(valor_tipo, 3, 1)
            
            # Doctor
            label_doctor = QLabel("Doctor:")
            label_doctor.setStyleSheet(f"color: {SaaSTheme.COLOR_TEXT_LIGHT}; font-weight: 600; font-size: 11px;")
            valor_doctor = QLabel(appointment.doctor if appointment.doctor else "Sin asignar")
            valor_doctor.setStyleSheet(f"color: {SaaSTheme.COLOR_CARBON}; font-size: 13px;")
            detalles_layout.addWidget(label_doctor, 4, 0)
            detalles_layout.addWidget(valor_doctor, 4, 1)
            
            # ID de cita
            label_id = QLabel("ID Cita:")
            label_id.setStyleSheet(f"color: {SaaSTheme.COLOR_TEXT_LIGHT}; font-weight: 600; font-size: 11px;")
            valor_id = QLabel(appointment.cita_id)
            valor_id.setStyleSheet(f"color: {SaaSTheme.COLOR_TEXT_LIGHT}; font-size: 11px; font-family: monospace;")
            detalles_layout.addWidget(label_id, 5, 0)
            detalles_layout.addWidget(valor_id, 5, 1)
            
            layout.addLayout(detalles_layout)
            
            # Botón de cierre
            btn_ok = QPushButton("Cerrar")
            btn_ok.setStyleSheet(f"""
                QPushButton {{
                    background-color: {SaaSTheme.COLOR_CARBON};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{ background-color: #333333; }}
            """)
            btn_ok.clicked.connect(dialog.accept)
            layout.addWidget(btn_ok)
            
            dialog.setLayout(layout)
            dialog.exec_()
        
        except Exception as e:
            print(f"Error mostrando confirmación: {e}")
            # Fallback a simple message box
            QMessageBox.information(self, "✓ Cita Registrada", 
                f"Cita registrada exitosamente\n\n"
                f"Paciente: {appointment.nombre_paciente}\n"
                f"Fecha: {appointment.fecha}\n"
                f"Hora: {appointment.hora}")

# Wrapper para compatibilidad de iconos en QListWidget si es necesario
from PyQt5.QtGui import QIcon as QHbIcon