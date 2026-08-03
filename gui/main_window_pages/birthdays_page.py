"""
Página de Cumpleaños - Muestra pacientes con cumpleaños próximos en tarjetas
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QDate, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush, QIcon
from datetime import datetime, timedelta


def get_icon(icon_name):
    """Obtiene el path de un icono SVG."""
    icons_dir = os.path.join(os.path.dirname(__file__), '..', 'icons')
    icon_path = os.path.join(icons_dir, f'{icon_name}.svg')
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    return None


class BirthdayCard(QFrame):
    """Tarjeta individual para mostrar un cumpleaños."""
    
    def __init__(self, nombre, dni, fecha_nacimiento, proximo_cumpleanos, dias_restantes):
        super().__init__()
        self.nombre = nombre
        self.dni = dni
        self.dias_restantes = dias_restantes
        
        # Calcular edad que va a cumplir
        fecha_nac = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
        edad_nueva = proximo_cumpleanos.year - fecha_nac.year
        
        self.setup_ui(proximo_cumpleanos, edad_nueva)
    
    def setup_ui(self, proximo_cumpleanos, edad_nueva):
        """Configurar la tarjeta."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Determinar color según días restantes
        if self.dias_restantes == 0:
            color_bg = "#4CAF50"  # Verde - Hoy
            color_border = "#2E7D32"
            icon_name = "check"
            titulo_dias = "¡HOY ES!"
        elif self.dias_restantes <= 3:
            color_bg = "#FF9800"  # Naranja - Muy próximo
            color_border = "#E65100"
            icon_name = "calendar"
            titulo_dias = f"¡En {self.dias_restantes} días!"
        elif self.dias_restantes <= 7:
            color_bg = "#2196F3"  # Azul - Próxima semana
            color_border = "#1565C0"
            icon_name = "calendar"
            titulo_dias = f"En {self.dias_restantes} días"
        elif self.dias_restantes <= 30:
            color_bg = "#9C27B0"  # Púrpura - Próximo mes
            color_border = "#6A1B9A"
            icon_name = "calendar"
            titulo_dias = f"En {self.dias_restantes} días"
        else:
            color_bg = "#607D8B"  # Gris - Más allá
            color_border = "#37474F"
            icon_name = "calendar"
            titulo_dias = f"En {self.dias_restantes} días"
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {color_bg};
                border: 3px solid {color_border};
                border-radius: 15px;
                padding: 15px;
            }}
        """)
        
        # Icono grande y nombre
        header_layout = QHBoxLayout()
        
        icon_label = QLabel()
        icon = get_icon(icon_name)
        if icon:
            icon_label.setPixmap(icon.pixmap(QSize(48, 48)))
        else:
            icon_label.setText("📅")
            icon_label.setFont(QFont("Arial", 28))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(60, 60)
        header_layout.addWidget(icon_label)
        
        name_layout = QVBoxLayout()
        
        nombre_label = QLabel(self.nombre)
        nombre_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        nombre_label.setStyleSheet("color: white;")
        name_layout.addWidget(nombre_label)
        
        dni_label = QLabel(f"DNI: {self.dni}")
        dni_label.setFont(QFont("Segoe UI", 9))
        dni_label.setStyleSheet("color: rgba(255,255,255,0.8);")
        name_layout.addWidget(dni_label)
        
        header_layout.addLayout(name_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Separador visual
        separador = QFrame()
        separador.setStyleSheet(f"background: rgba(255,255,255,0.3); min-height: 2px;")
        layout.addWidget(separador)
        
        # Información de días
        dias_layout = QHBoxLayout()
        
        # Días restantes grande
        dias_numero = QLabel(str(self.dias_restantes))
        dias_numero.setFont(QFont("Arial", 32, QFont.Bold))
        dias_numero.setStyleSheet("color: white;")
        dias_numero.setAlignment(Qt.AlignCenter)
        dias_layout.addWidget(dias_numero)
        
        # Texto descriptivo
        info_layout = QVBoxLayout()
        
        dias_texto = QLabel("DÍAS")
        dias_texto.setFont(QFont("Segoe UI", 10, QFont.Bold))
        dias_texto.setStyleSheet("color: rgba(255,255,255,0.9);")
        info_layout.addWidget(dias_texto)
        
        titulo_label = QLabel(titulo_dias)
        titulo_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        titulo_label.setStyleSheet("color: white;")
        info_layout.addWidget(titulo_label)
        
        edad_label = QLabel(f"Va a cumplir {edad_nueva} años")
        edad_label.setFont(QFont("Segoe UI", 9))
        edad_label.setStyleSheet("color: rgba(255,255,255,0.8);")
        info_layout.addWidget(edad_label)
        
        dias_layout.addLayout(info_layout)
        dias_layout.addStretch()
        layout.addLayout(dias_layout)
        
        # Fecha del cumpleaños
        fecha_layout = QHBoxLayout()
        
        # Icono de calendario para la fecha
        calendar_icon = QLabel()
        cal_icon = get_icon("calendar")
        if cal_icon:
            calendar_icon.setPixmap(cal_icon.pixmap(QSize(16, 16)))
        calendar_icon.setFixedSize(20, 20)
        fecha_layout.addWidget(calendar_icon)
        
        fecha_label = QLabel(f"{proximo_cumpleanos.strftime('%d de %B de %Y')}")
        fecha_label.setFont(QFont("Segoe UI", 10))
        fecha_label.setStyleSheet("color: rgba(255,255,255,0.9);")
        fecha_layout.addWidget(fecha_label)
        fecha_layout.addStretch()
        layout.addLayout(fecha_layout)
        
        layout.addStretch()


class BirthdaysPage(QWidget):
    """Página que muestra los cumpleaños de los pacientes en tarjetas visibles."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
        self.load_birthdays()
    
    def setup_ui(self):
        """Configurar la interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header con título e icono
        header_layout = QHBoxLayout()
        
        title_icon = QLabel()
        cal_icon = get_icon("calendar")
        if cal_icon:
            title_icon.setPixmap(cal_icon.pixmap(QSize(32, 32)))
        title_icon.setFixedSize(40, 40)
        header_layout.addWidget(title_icon)
        
        title = QLabel("Cumpleaños Próximos")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #333333;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Descripción
        desc = QLabel("Mantente atento a los cumpleaños de tus pacientes")
        desc.setFont(QFont("Segoe UI", 11))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)
        
        # Área con scroll para las tarjetas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: #F5F5F5;
                border: none;
            }
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9E9E9E;
            }
        """)
        
        # Contenedor de tarjetas
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(15)
        
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)
        
        # Botón de actualizar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_refresh = QPushButton()
        btn_refresh.setText("Actualizar")
        refresh_icon = get_icon("refresh")
        if refresh_icon:
            btn_refresh.setIcon(refresh_icon)
            btn_refresh.setIconSize(QSize(16, 16))
        
        btn_refresh.setFixedWidth(150)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background: #0066CC;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 12px;
                padding-left: 35px;
            }
            QPushButton:hover {
                background: #0052A3;
            }
            QPushButton:pressed {
                background: #003D7A;
            }
        """)
        btn_refresh.clicked.connect(self.load_birthdays)
        btn_layout.addWidget(btn_refresh)
        
        layout.addLayout(btn_layout)
    
    def load_birthdays(self):
        """Cargar los cumpleaños de los pacientes desde el caché."""
        try:
            # Limpiar tarjetas anteriores
            while self.cards_layout.count():
                child = self.cards_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Obtener pacientes del caché
            pacientes = self.parent_window.cache.get_pacientes(self.parent_window.username)
            
            if not pacientes:
                no_data = QLabel("No hay pacientes cargados")
                no_data.setFont(QFont("Segoe UI", 12))
                no_data.setStyleSheet("color: #999999;")
                no_data.setAlignment(Qt.AlignCenter)
                self.cards_layout.addWidget(no_data)
                return
            
            # Procesar cumpleaños
            birthdays_list = []
            today = datetime.now().date()
            
            for paciente in pacientes:
                if not isinstance(paciente, dict):
                    continue
                
                # Obtener fecha de nacimiento
                fecha_nacimiento_str = paciente.get('fecha_nacimiento', '')
                
                if not fecha_nacimiento_str:
                    continue
                
                try:
                    # Parsear fecha de nacimiento (formato: YYYY-MM-DD)
                    fecha_nac = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
                    
                    # Calcular próximo cumpleaños
                    anio_actual = today.year
                    cumpleanos_este_anio = fecha_nac.replace(year=anio_actual)
                    
                    # Si ya pasó el cumpleaños este año, usar el del próximo año
                    if cumpleanos_este_anio < today:
                        cumpleanos_este_anio = fecha_nac.replace(year=anio_actual + 1)
                    
                    # Calcular días restantes
                    dias_restantes = (cumpleanos_este_anio - today).days
                    
                    birthdays_list.append({
                        'nombre': paciente.get('nombre', 'Sin nombre'),
                        'dni': paciente.get('dni', 'N/A'),
                        'fecha_nacimiento': fecha_nacimiento_str,
                        'proximo_cumpleanos': cumpleanos_este_anio,
                        'dias_restantes': dias_restantes
                    })
                
                except ValueError:
                    # Ignorar fechas con formato inválido
                    continue
            
            # Ordenar por días restantes
            birthdays_list.sort(key=lambda x: x['dias_restantes'])
            
            if not birthdays_list:
                no_birthdays = QLabel("No hay cumpleaños registrados")
                no_birthdays.setFont(QFont("Segoe UI", 12))
                no_birthdays.setStyleSheet("color: #999999;")
                no_birthdays.setAlignment(Qt.AlignCenter)
                self.cards_layout.addWidget(no_birthdays)
                return
            
            # Crear tarjetas para cada cumpleaños
            for birthday_info in birthdays_list:
                card = BirthdayCard(
                    nombre=birthday_info['nombre'],
                    dni=birthday_info['dni'],
                    fecha_nacimiento=birthday_info['fecha_nacimiento'],
                    proximo_cumpleanos=birthday_info['proximo_cumpleanos'],
                    dias_restantes=birthday_info['dias_restantes']
                )
                self.cards_layout.addWidget(card)
            
            # Agregar un espacio al final
            self.cards_layout.addStretch()
            
        except Exception as e:
            print(f"[BIRTHDAYS] Error cargando cumpleaños: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al cargar cumpleaños: {str(e)}")

