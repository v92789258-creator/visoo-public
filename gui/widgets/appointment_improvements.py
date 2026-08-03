"""
WIDGETS MEJORADOS PARA INTERFAZ DE CITAS
==========================================

Componentes visuales mejorados para la página de citas:
- Dashboard de citas con estadísticas
- Calendario avanzado con drag & drop
- Panel de notificaciones de citas
- Filtros y búsqueda avanzada
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit, QSpinBox,
    QDateEdit, QTimeEdit, QMessageBox, QScrollArea, QSizePolicy,
    QHeaderView, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt, QDate, QTime, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QColor, QFont, QIcon
from datetime import datetime, timedelta


class AppointmentDashboard(QFrame):
    """Dashboard principal de citas con estadísticas en tiempo real"""
    
    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.username = username
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            AppointmentDashboard {
                background-color: #f5f5f5;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        titulo = QLabel("📅 Centro de Citas")
        titulo.setFont(QFont("Segoe UI", 18, QFont.Bold))
        titulo.setStyleSheet("color: #1a73e8; margin-bottom: 10px;")
        layout.addWidget(titulo)
        
        # Row 1: Cards de estadísticas
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # Card: Total pendientes
        self.card_pendientes = self._create_stat_card(
            "📋 Pendientes",
            "0",
            "#2196F3"
        )
        stats_layout.addWidget(self.card_pendientes)
        
        # Card: Hoy
        self.card_hoy = self._create_stat_card(
            "📅 Hoy",
            "0",
            "#4CAF50"
        )
        stats_layout.addWidget(self.card_hoy)
        
        # Card: Próximas 24h
        self.card_proximamente = self._create_stat_card(
            "⏰ Próximas 24h",
            "0",
            "#FF9800"
        )
        stats_layout.addWidget(self.card_proximamente)
        
        # Card: No presentados
        self.card_no_show = self._create_stat_card(
            "❌ No presentados",
            "0",
            "#F44336"
        )
        stats_layout.addWidget(self.card_no_show)
        
        layout.addLayout(stats_layout)
        
        # Separador
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setStyleSheet("background-color: #ddd; height: 1px;")
        layout.addWidget(separador)
        
        # Row 2: Filtros y búsqueda
        filtros_layout = QHBoxLayout()
        filtros_layout.setSpacing(10)
        
        # Búsqueda por DNI/Nombre
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por DNI o nombre...")
        self.search_input.setMaximumWidth(250)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background: white;
                font-size: 11px;
            }
        """)
        filtros_layout.addWidget(self.search_input)
        
        # Filtro de estado
        label_estado = QLabel("Estado:")
        label_estado.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.combo_estado = QComboBox()
        self.combo_estado.addItems([
            "Todos",
            "Pendientes",
            "Completadas",
            "Canceladas",
            "No presentados"
        ])
        self.combo_estado.setMaximumWidth(150)
        self.combo_estado.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        """)
        filtros_layout.addWidget(label_estado)
        filtros_layout.addWidget(self.combo_estado)
        
        # Filtro de fecha
        label_fecha = QLabel("Desde:")
        label_fecha.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.date_desde = QDateEdit()
        self.date_desde.setDate(QDate.currentDate())
        self.date_desde.setMaximumWidth(120)
        self.date_desde.setStyleSheet("""
            QDateEdit {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        """)
        filtros_layout.addWidget(label_fecha)
        filtros_layout.addWidget(self.date_desde)
        
        filtros_layout.addStretch()
        
        # Botones de acción
        btn_nueva = QPushButton("➕ Nueva Cita")
        btn_nueva.setMaximumWidth(120)
        btn_nueva.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        filtros_layout.addWidget(btn_nueva)
        
        btn_refrescar = QPushButton("🔄 Refrescar")
        btn_refrescar.setMaximumWidth(100)
        btn_refrescar.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        filtros_layout.addWidget(btn_refrescar)
        
        layout.addLayout(filtros_layout)
        
        # Row 3: Tabla de citas
        self.tabla_citas = QTableWidget()
        self.tabla_citas.setColumnCount(8)
        self.tabla_citas.setHorizontalHeaderLabels([
            "DNI", "Paciente", "Fecha", "Hora", "Tipo", "Estado", "Duración", "Acciones"
        ])
        
        # Configurar tabla
        self.tabla_citas.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_citas.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_citas.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla_citas.setAlternatingRowColors(True)
        self.tabla_citas.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                gridline-color: #eee;
                background: white;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #ddd;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        
        layout.addWidget(self.tabla_citas)
    
    def _create_stat_card(self, titulo: str, valor: str, color: str) -> QFrame:
        """Crea una tarjeta de estadística"""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 8px;
                padding: 12px;
                min-height: 80px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Título
        label_titulo = QLabel(titulo)
        label_titulo.setFont(QFont("Segoe UI", 11, QFont.Bold))
        label_titulo.setStyleSheet(f"color: {color};")
        layout.addWidget(label_titulo)
        
        # Valor
        label_valor = QLabel(valor)
        label_valor.setFont(QFont("Segoe UI", 24, QFont.Bold))
        label_valor.setStyleSheet(f"color: {color};")
        label_valor.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_valor)
        
        # Guardar referencia al label del valor
        card.value_label = label_valor
        
        return card


class AppointmentConflictDetectorWidget(QFrame):
    """Widget para detectar y mostrar conflictos de horario"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            AppointmentConflictDetectorWidget {
                background-color: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Icono y título
        titulo_layout = QHBoxLayout()
        titulo_icon = QLabel("⚠️")
        titulo_icon.setFont(QFont("Segoe UI", 14))
        titulo_text = QLabel("Conflicto de Horario Detectado")
        titulo_text.setFont(QFont("Segoe UI", 12, QFont.Bold))
        titulo_text.setStyleSheet("color: #856404;")
        
        titulo_layout.addWidget(titulo_icon)
        titulo_layout.addWidget(titulo_text)
        titulo_layout.addStretch()
        layout.addLayout(titulo_layout)
        
        # Descripción
        self.description = QLabel()
        self.description.setStyleSheet("color: #856404; font-size: 11px;")
        self.description.setWordWrap(True)
        layout.addWidget(self.description)
        
        # Sugerencias
        sugerencias_label = QLabel("💡 Horarios disponibles:")
        sugerencias_label.setStyleSheet("color: #856404; font-weight: bold; font-size: 11px; margin-top: 8px;")
        layout.addWidget(sugerencias_label)
        
        self.sugerencias_layout = QHBoxLayout()
        self.sugerencias_layout.setSpacing(5)
        layout.addLayout(self.sugerencias_layout)
        
        self.hide()


class AppointmentReminderNotification(QFrame):
    """Notificación de recordatorio de citas próximas"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            AppointmentReminderNotification {
                background-color: #e3f2fd;
                border: 2px solid #2196F3;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Encabezado
        header = QHBoxLayout()
        icon = QLabel("🔔")
        icon.setFont(QFont("Segoe UI", 16))
        titulo = QLabel("Recordatorios Pendientes")
        titulo.setFont(QFont("Segoe UI", 12, QFont.Bold))
        titulo.setStyleSheet("color: #1565c0;")
        header.addWidget(icon)
        header.addWidget(titulo)
        header.addStretch()
        layout.addLayout(header)
        
        # Lista de recordatorios
        self.reminders_container = QWidget()
        self.reminders_layout = QVBoxLayout(self.reminders_container)
        self.reminders_layout.setContentsMargins(0, 0, 0, 0)
        self.reminders_layout.setSpacing(5)
        
        scroll = QScrollArea()
        scroll.setWidget(self.reminders_container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(150)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #e3f2fd;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #2196F3;
                border-radius: 4px;
                min-height: 20px;
            }
        """)
        
        layout.addWidget(scroll)
        
        self.hide()
    
    def add_reminder(self, paciente_nombre: str, hora: str, tipo: str):
        """Agrega un recordatorio a la lista"""
        reminder_widget = QFrame()
        reminder_widget.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 4px;
                padding: 8px;
                border-left: 4px solid #2196F3;
            }
        """)
        
        r_layout = QHBoxLayout(reminder_widget)
        r_layout.setContentsMargins(8, 4, 8, 4)
        
        info = QLabel(f"👤 {paciente_nombre} - 🕐 {hora} ({tipo})")
        info.setStyleSheet("font-size: 11px; color: #333;")
        r_layout.addWidget(info)
        r_layout.addStretch()
        
        self.reminders_layout.addWidget(reminder_widget)
        
        if self.reminders_layout.count() > 0:
            self.show()
