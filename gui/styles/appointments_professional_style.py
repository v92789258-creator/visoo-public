"""
ESTILOS PROFESIONALES PARA PÁGINA DE CITAS
============================================

Diseño limpio, minimalista y serio.
Colores: Grises, azules corporativos, blancos
Sin animaciones innecesarias
Tipografía profesional
"""

# Estilos para AppointmentsPage - Diseño Profesional
APPOINTMENTS_PAGE_STYLE = """
QWidget {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}

/* ========== PANEL IZQUIERDO (CALENDARIO) ========== */
QFrame#left_panel {
    background-color: #f8f9fa;
    border-right: 1px solid #dee2e6;
}

QLabel#calendar_title {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 8px;
}

QLabel#calendar_subtitle {
    font-size: 12px;
    color: #6c757d;
    margin-bottom: 12px;
}

/* ========== CALENDARIO ========== */
QCalendarWidget {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 8px;
}

QCalendarWidget QWidget {
    background-color: transparent;
    alternate-background-color: transparent;
}

QCalendarWidget QToolButton {
    color: #495057;
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 6px 4px;
    margin: 2px;
    font-weight: 500;
    font-size: 11px;
}

QCalendarWidget QToolButton:hover {
    background-color: #e7f1ff;
    color: #0d47a1;
}

QCalendarWidget QToolButton:pressed {
    background-color: #d6e4f5;
    color: #0d47a1;
}

QCalendarWidget QToolButton:focus {
    outline: none;
}

QCalendarWidget QMenu {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    color: #495057;
}

QCalendarWidget QSpinBox {
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 4px;
    color: #495057;
    background-color: #ffffff;
}

QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    selection-background-color: #0d47a1;
    selection-color: #ffffff;
    font-size: 12px;
    font-weight: 500;
    border: none;
}

QCalendarWidget QAbstractItemView::item:selected {
    background-color: #0d47a1;
    color: #ffffff;
    border-radius: 4px;
}

QCalendarWidget QAbstractItemView::item:hover {
    background-color: #e7f1ff;
    color: #0d47a1;
}

QCalendarWidget QHeaderView::section {
    background-color: #f8f9fa;
    color: #495057;
    padding: 6px;
    border: none;
    font-weight: 600;
    font-size: 11px;
    text-align: center;
}

/* ========== BOTONES PRINCIPALES ========== */
QPushButton#btn_new_appointment {
    background-color: #0d47a1;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#btn_new_appointment:hover {
    background-color: #0a3d91;
}

QPushButton#btn_new_appointment:pressed {
    background-color: #082d75;
}

QPushButton#btn_statistics {
    background-color: #1b5e20;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#btn_statistics:hover {
    background-color: #165021;
}

QPushButton#btn_statistics:pressed {
    background-color: #0d401a;
}

/* ========== PANEL DERECHO (DETALLES DE CITAS) ========== */
QFrame#appointment_details {
    background-color: #ffffff;
    border: none;
}

QLabel#appointment_title {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
    padding: 0px 0px 12px 0px;
}

/* ========== TARJETA DE CITA ========== */
QFrame.appointment_card {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 14px;
    margin: 6px 0px;
}

QFrame.appointment_card:hover {
    border: 1px solid #0d47a1;
    background-color: #f8fbff;
    border-radius: 6px;
}

QFrame.appointment_card_past {
    background-color: #fef5f5;
    border: 1px solid #d9534f;
    border-radius: 6px;
    padding: 14px;
    margin: 6px 0px;
}

QFrame.appointment_card_past:hover {
    background-color: #fbedeb;
    border: 1px solid #c9302c;
}

/* ========== ELEMENTOS DENTRO DE TARJETA ========== */
QLabel#appointment_time {
    font-weight: 600;
    color: #0d47a1;
    font-size: 13px;
}

QLabel#appointment_status_completed {
    color: #1b5e20;
    font-weight: 600;
    font-size: 11px;
}

QLabel#appointment_status_pending {
    color: #f57f17;
    font-weight: 600;
    font-size: 11px;
}

QLabel#appointment_status_past {
    color: #d9534f;
    font-weight: 600;
    font-size: 11px;
}

QLabel#appointment_patient_name {
    color: #1a1a1a;
    font-weight: 500;
    font-size: 12px;
}

QLabel#appointment_type {
    color: #6c757d;
    font-size: 11px;
}

QLabel#no_appointments_message {
    color: #999999;
    font-style: italic;
    font-size: 13px;
}

/* ========== BOTONES DE ACCIÓN ========== */
QPushButton#btn_edit_appointment {
    background-color: #0d47a1;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 10px;
    min-width: 60px;
}

QPushButton#btn_edit_appointment:hover {
    background-color: #0a3d91;
}

QPushButton#btn_edit_appointment:pressed {
    background-color: #082d75;
}

QPushButton#btn_complete_appointment {
    background-color: #1b5e20;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 10px;
    min-width: 60px;
}

QPushButton#btn_complete_appointment:hover {
    background-color: #165021;
}

QPushButton#btn_complete_appointment:pressed {
    background-color: #0d401a;
}

QPushButton#btn_cancel_appointment {
    background-color: #d9534f;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 10px;
    min-width: 60px;
}

QPushButton#btn_cancel_appointment:hover {
    background-color: #c9302c;
}

QPushButton#btn_cancel_appointment:pressed {
    background-color: #ac2925;
}

/* ========== LÍNEAS SEPARADORAS ========== */
QFrame.separator {
    background-color: #dee2e6;
    border: none;
    height: 1px;
}

/* ========== SCROLL BARS ========== */
QScrollBar:vertical {
    border: none;
    background-color: #f8f9fa;
    width: 8px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background-color: #bdbdbd;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9e9e9e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

/* ========== DIÁLOGOS ========== */
QDialog {
    background-color: #ffffff;
}

QGroupBox {
    color: #495057;
    font-weight: 600;
    font-size: 12px;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QLineEdit, QDateEdit, QTimeEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    color: #495057;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 8px;
    font-size: 11px;
    selection-background-color: #0d47a1;
    selection-color: #ffffff;
}

QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 2px solid #0d47a1;
    background-color: #f8fbff;
}

QLineEdit::placeholder {
    color: #999999;
}

QComboBox::drop-down {
    border: none;
    background-color: transparent;
}

QComboBox::down-arrow {
    image: none;
    width: 0px;
}

/* ========== TABLAS ========== */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    gridline-color: #e7e7e7;
    font-size: 11px;
}

QTableWidget::item {
    padding: 8px;
    color: #495057;
}

QTableWidget::item:selected {
    background-color: #e7f1ff;
    color: #0d47a1;
    font-weight: 500;
}

QTableWidget::item:hover {
    background-color: #f8fbff;
}

QHeaderView::section {
    background-color: #f8f9fa;
    color: #495057;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #dee2e6;
    font-weight: 600;
    font-size: 11px;
    text-align: left;
}

/* ========== MENSAJES ========== */
QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #495057;
    font-size: 12px;
}
"""

# ============================================================================
# CONSTANTES DE COLORES CORPORATIVOS
# ============================================================================

COLORS = {
    # Primarios
    "primary_dark": "#0d47a1",      # Azul oscuro corporativo
    "primary": "#1565c0",            # Azul corporativo
    "primary_light": "#42a5f5",     # Azul claro
    
    # Secundarios
    "success": "#1b5e20",            # Verde oscuro
    "warning": "#f57f17",            # Naranja/Amarillo
    "danger": "#d9534f",             # Rojo
    "info": "#0d47a1",               # Azul
    
    # Neutros
    "dark": "#1a1a1a",               # Negro
    "gray_dark": "#495057",          # Gris oscuro
    "gray": "#6c757d",               # Gris
    "gray_light": "#bdbdbd",         # Gris claro
    "light": "#f8f9fa",              # Gris muy claro
    "white": "#ffffff",              # Blanco
    
    # Bordes
    "border": "#dee2e6",             # Gris borde
    
    # Estados
    "state_hover": "#e7f1ff",        # Hover azul
    "state_selected": "#e7f1ff",     # Seleccionado
    "state_disabled": "#e7e7e7",     # Deshabilitado
}

# ============================================================================
# ESTILOS COMUNES REUTILIZABLES
# ============================================================================

BUTTON_PRIMARY = """
    background-color: {primary};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-weight: 600;
    font-size: 12px;
""".format(**COLORS)

BUTTON_PRIMARY_HOVER = """
    background-color: {primary_dark};
""".format(**COLORS)

BUTTON_SUCCESS = """
    background-color: {success};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-weight: 600;
    font-size: 12px;
""".format(**COLORS)

BUTTON_DANGER = """
    background-color: {danger};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-weight: 600;
    font-size: 12px;
""".format(**COLORS)

CARD_FRAME = """
    background-color: {white};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 14px;
""".format(**COLORS)

CARD_FRAME_HOVER = """
    border: 1px solid {primary};
    background-color: {state_hover};
""".format(**COLORS)

INPUT_FIELD = """
    background-color: {white};
    color: {gray_dark};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 8px;
    font-size: 11px;
""".format(**COLORS)

INPUT_FIELD_FOCUS = """
    border: 2px solid {primary};
    background-color: {state_hover};
""".format(**COLORS)

TITLE = """
    font-size: 16px;
    font-weight: 600;
    color: {dark};
""".format(**COLORS)

SUBTITLE = """
    font-size: 12px;
    color: {gray};
""".format(**COLORS)
