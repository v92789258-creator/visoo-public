import sys
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QScrollArea,
    QMessageBox, QTabWidget, QGridLayout, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QFrame, QListWidget, QListWidgetItem,
    QSlider, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QDrag, QCursor

from utils.file_handler import (
    cargar_plantilla_boleta, guardar_plantilla_boleta,
    cargar_nombre_optica, cargar_datos_generales,
    cargar_impresora_predeterminada, guardar_impresora_predeterminada,
    open_pdf_with_chrome
)


class DraggableSectionWidget(QFrame):
    """Widget que representa una sección arrastrable de la boleta con diseño mejorado de card."""
    
    def __init__(self, section_id, title, description, icon_emoji="📄"):
        super().__init__()
        self.section_id = section_id
        self.title = title
        self.description = description
        self.icon_emoji = icon_emoji
        
        self.setStyleSheet("""
            QFrame {
                background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                border: 2px solid #e0e7ff;
                border-radius: 12px;
                padding: 0px;
                margin: 0px;
            }
            QFrame:hover {
                border: 2px solid #4F46E5;
                background: linear-gradient(135deg, #f0f4ff 0%, #f8f9fa 100%);
                box-shadow: 0 10px 25px rgba(79, 70, 229, 0.1);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        
        # Icono + Título
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        lbl_icon = QLabel(icon_emoji)
        lbl_icon.setStyleSheet("font-size: 24px;")
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setMaximumWidth(40)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("""
            color: #1F2937;
            font-weight: 700;
            font-size: 13px;
            line-height: 1.4;
        """)
        lbl_title.setWordWrap(True)
        lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(lbl_title)
        layout.addLayout(header_layout)
        
        # Descripción
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet("""
            color: #6B7280;
            font-size: 11px;
            line-height: 1.3;
        """)
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)
        
        # Indicador de arrastre
        lbl_drag = QLabel("⇧ Arrastra para agregar")
        lbl_drag.setStyleSheet("""
            color: #9CA3AF;
            font-size: 9px;
            font-style: italic;
            text-align: center;
        """)
        lbl_drag.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_drag)
        
        self.setCursor(QtGui.QCursor(Qt.OpenHandCursor))
        self.setMinimumHeight(90)
        self.setMaximumHeight(110)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.section_id)
            drag.setMimeData(mime_data)
            
            # Crear pixmap para el drag
            pixmap = QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            
            drag.exec_(Qt.MoveAction)


class DropZoneWidget(QFrame):
    """Área donde se pueden soltar las secciones - se parece a una boleta térmica real con datos de ejemplo."""
    
    section_dropped = pyqtSignal(str)
    section_clicked = pyqtSignal(str)
    
    # Datos de ejemplo para vista previa
    SAMPLE_DATA = {
        'encabezado': 'ÓPTICA VISIÓN CLARA\nRUC: 12345678901\nTel: 987654321',
        'fecha': 'Fecha: 05/12/2025\nHora: 14:30',
        'cliente': 'Cliente: Juan Pérez\nDNI: 12345678',
        'optometra': 'Optómetra: Dr. García',
        'tabla': 'Montura .................. 150.00\nLentes Oftálmicos ...... 200.00\nArmazón ................. 80.00',
        'totales': 'Subtotal: 430.00\nTotal: 430.00',
        'monto_letras': 'Cuatrocientos treinta soles',
        'qr': '█ █ ███ █ █\n █ █  █ ███\n██ ██ █ █ █',
        'pie': 'Gracias por su compra\nVisítanos nuevamente',
    }
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #333;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(2)
        
        self.sections_container = QVBoxLayout()
        self.sections_container.setSpacing(2)
        self.sections_container.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addLayout(self.sections_container)
        
        self.placeholder = QLabel("↓ ARRASTRA SECCIONES ↓")
        self.placeholder.setStyleSheet("""
            color: #bbb;
            font-size: 11px;
            text-align: center;
            padding: 80px 15px;
            font-style: italic;
            font-family: Courier New;
            font-weight: bold;
        """)
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.sections_container.addWidget(self.placeholder)
        
        self.dropped_sections = {}  # {section_id: widget}
        self.section_configs = {}   # {section_id: config}
        self.setMinimumHeight(200)
        self.setMaximumWidth(260)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        if event.mimeData().hasText():
            section_id = event.mimeData().text()
            self.section_dropped.emit(section_id)
            event.acceptProposedAction()
    
    def add_section(self, section_id, title, description, icon_emoji):
        """Agrega una sección a la zona de drop con datos de ejemplo."""
        if self.placeholder in [self.sections_container.itemAt(i).widget() for i in range(self.sections_container.count()) if self.sections_container.itemAt(i).widget()]:
            self.sections_container.removeWidget(self.placeholder)
            self.placeholder.deleteLater()
        
        # Crear widget para la sección en el drop zone
        section_frame = QFrame()
        section_frame.setObjectName(f"section_{section_id}")
        section_frame.setStyleSheet(f"""
            QFrame#{section_id} {{
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-bottom: 1px dashed #ccc;
                padding: 0px;
                margin: 0px;
            }}
            QFrame#{section_id}:hover {{
                background: #f5f5f5;
                border: 1px solid #2a7f2a;
            }}
        """)
        section_frame.setMinimumHeight(55)
        section_frame.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(4, 3, 4, 3)
        section_layout.setSpacing(2)
        
        # Header con título y botón eliminar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("""
            font-family: 'Courier New', monospace;
            font-size: 8px;
            color: #333;
            font-weight: bold;
        """)
        
        btn_remove = QPushButton("✕")
        btn_remove.setMaximumWidth(20)
        btn_remove.setMaximumHeight(20)
        btn_remove.setStyleSheet("""
            QPushButton {
                background: #ffebee;
                border: 1px solid #ffcdd2;
                border-radius: 2px;
                color: #c62828;
                font-weight: bold;
                padding: 0px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: #ff5252;
                color: white;
                border: 1px solid #ff5252;
            }
        """)
        btn_remove.clicked.connect(lambda: self.remove_section(section_id, section_frame))
        
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_remove)
        section_layout.addLayout(header_layout)
        
        # Datos de ejemplo
        sample_text = self.SAMPLE_DATA.get(section_id, '...')
        lbl_sample = QLabel(sample_text)
        lbl_sample.setStyleSheet("""
            font-family: 'Courier New', monospace;
            font-size: 7px;
            color: #666;
            padding: 2px;
            line-height: 1.2;
        """)
        lbl_sample.setWordWrap(True)
        lbl_sample.setMaximumHeight(30)
        section_layout.addWidget(lbl_sample)
        
        # Evento click en el frame
        section_frame.section_id = section_id
        section_frame.mousePressEvent = lambda e: self.on_section_clicked(section_id)
        
        self.sections_container.addWidget(section_frame)
        self.dropped_sections[section_id] = section_frame
        
        # Configuración inicial
        default_config = {
            'width': 100,
            'alignment': 'center',
            'row': len(self.dropped_sections),
        }
        self.section_configs[section_id] = default_config
    
    def on_section_clicked(self, section_id):
        """Se dispara cuando se hace click en una sección."""
        self.section_clicked.emit(section_id)
    
    def remove_section(self, section_id, widget):
        """Elimina una sección del drop zone."""
        self.sections_container.removeWidget(widget)
        widget.deleteLater()
        if section_id in self.dropped_sections:
            del self.dropped_sections[section_id]
        if section_id in self.section_configs:
            del self.section_configs[section_id]
        
        # Si no hay secciones, mostrar placeholder
        if not self.dropped_sections:
            self.sections_container.addWidget(self.placeholder)
    
    def get_sections_order(self):
        """Retorna las secciones en orden."""
        return list(self.dropped_sections.keys())
    
    def clear_sections(self):
        """Limpia todas las secciones."""
        for i in reversed(range(self.sections_container.count())):
            widget = self.sections_container.itemAt(i).widget()
            if widget:
                self.sections_container.removeWidget(widget)
                widget.deleteLater()
        self.dropped_sections.clear()
        self.section_configs.clear()
        self.sections_container.addWidget(self.placeholder)


class PlantillaBobetaPage(QWidget):
    """
    Página para personalizar la plantilla/diseño de las boletas con constructor visual avanzado.
    El usuario arrastra secciones y puede personalizar posición, alineación y tamaño de cada una.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        self.setObjectName("PlantillaBobetaPage")
        
        # Secciones disponibles
        self.sections_available = {
            'encabezado': ('🏢 Encabezado (Nombre Óptica)', 'Nombre y datos de tu óptica', '🏢'),
            'fecha': ('📅 Fecha', 'Fecha de la transacción', '📅'),
            'cliente': ('👤 Datos del Cliente', 'Nombre y DNI del cliente', '👤'),
            'optometra': ('👨‍⚕️ Optómetra', 'Nombre del profesional', '👨‍⚕️'),
            'tabla': ('📊 Tabla de Productos', 'Listado de artículos', '📊'),
            'totales': ('💰 Totales', 'Subtotal, total y forma de pago', '💰'),
            'monto_letras': ('📝 Monto en Letras', 'Cantidad en palabras', '📝'),
            'qr': ('🔗 Código QR', 'Código para escanear', '🔗'),
            'pie': ('🔚 Pie de Página', 'Texto final y contacto', '🔚'),
        }
        
        self.current_selected_section = None
        
        self.setup_ui()
        self.cargar_configuracion()
    
    def setup_ui(self):
        """Crea la interfaz de usuario."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Título
        titulo = QLabel("🎨 Constructor Avanzado de Plantilla de Boleta")
        titulo_font = QFont()
        titulo_font.setPointSize(14)
        titulo_font.setBold(True)
        titulo.setFont(titulo_font)
        main_layout.addWidget(titulo)
        
        # Descripción
        desc = QLabel(
            "Personaliza tu boleta térmica. Arrastra las secciones, luego ajusta su posición, alineación y tamaño."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 10px; padding: 8px; background: #f9f9f9; border-radius: 4px;")
        main_layout.addWidget(desc)
        
        # Contenedor principal con tres paneles
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # ========== PANEL IZQUIERDO: Secciones Disponibles ==========
        left_panel = QVBoxLayout()
        
        lbl_disponibles = QLabel("📚 Secciones Disponibles")
        lbl_disponibles_font = QFont()
        lbl_disponibles_font.setBold(True)
        lbl_disponibles_font.setPointSize(11)
        lbl_disponibles.setFont(lbl_disponibles_font)
        left_panel.addWidget(lbl_disponibles)
        
        lbl_instrucciones = QLabel("Haz clic y arrastra→")
        lbl_instrucciones.setStyleSheet("color: #999; font-size: 9px; font-style: italic;")
        left_panel.addWidget(lbl_instrucciones)
        
        scroll_disponibles = QScrollArea()
        scroll_disponibles.setWidgetResizable(True)
        scroll_disponibles.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                background: white;
                border-radius: 4px;
            }
        """)
        
        container_disponibles = QWidget()
        layout_disponibles = QVBoxLayout(container_disponibles)
        layout_disponibles.setSpacing(8)
        layout_disponibles.setContentsMargins(4, 4, 4, 4)
        
        # Agregar cada sección disponible
        for section_id, (title, description, emoji) in self.sections_available.items():
            widget = DraggableSectionWidget(section_id, title, description, emoji)
            layout_disponibles.addWidget(widget)
        
        layout_disponibles.addStretch()
        scroll_disponibles.setWidget(container_disponibles)
        scroll_disponibles.setMinimumWidth(260)
        left_panel.addWidget(scroll_disponibles)
        
        # ========== PANEL CENTRAL: Vista Previa de Boleta ==========
        center_panel = QVBoxLayout()
        
        lbl_preview = QLabel("📋 Vista Previa - Boleta Térmica (80mm)")
        lbl_preview_font = QFont()
        lbl_preview_font.setBold(True)
        lbl_preview_font.setPointSize(11)
        lbl_preview.setFont(lbl_preview_font)
        center_panel.addWidget(lbl_preview)
        
        # Contenedor centrado para simular papel de impresora térmica
        boleta_container = QWidget()
        boleta_container.setStyleSheet("background: #f5f5f5;")
        boleta_container_layout = QVBoxLayout(boleta_container)
        boleta_container_layout.setContentsMargins(20, 20, 20, 20)
        boleta_container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        # Frame que simula la boleta térmica
        self.drop_zone = DropZoneWidget()
        self.drop_zone.section_dropped.connect(self.on_section_dropped)
        self.drop_zone.section_clicked.connect(self.on_section_selected)
        self.drop_zone.setMaximumWidth(260)
        
        boleta_container_layout.addWidget(self.drop_zone, alignment=Qt.AlignHCenter)
        boleta_container_layout.addStretch()
        
        # Scroll para poder ver toda la boleta
        scroll_boleta = QScrollArea()
        scroll_boleta.setWidgetResizable(True)
        scroll_boleta.setWidget(boleta_container)
        scroll_boleta.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #f5f5f5;
            }
            QScrollBar:vertical {
                border: 1px solid #ddd;
                background: #f5f5f5;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #999;
            }
        """)
        scroll_boleta.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        
        center_panel.addWidget(scroll_boleta)
        
        # ========== PANEL DERECHO: Configuración Avanzada ==========
        right_panel = QVBoxLayout()
        
        lbl_config = QLabel("⚙️ Configuración Avanzada")
        lbl_config_font = QFont()
        lbl_config_font.setBold(True)
        lbl_config_font.setPointSize(11)
        lbl_config.setFont(lbl_config_font)
        right_panel.addWidget(lbl_config)
        
        lbl_select = QLabel("(Haz clic en una sección para configurarla)")
        lbl_select.setStyleSheet("color: #999; font-size: 9px; font-style: italic;")
        right_panel.addWidget(lbl_select)
        
        # Scroll para la configuración
        scroll_config = QScrollArea()
        scroll_config.setWidgetResizable(True)
        scroll_config.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                background: white;
                border-radius: 4px;
            }
        """)
        
        self.config_widget = QWidget()
        self.config_layout = QVBoxLayout(self.config_widget)
        self.config_layout.setSpacing(12)
        self.config_layout.setContentsMargins(8, 8, 8, 8)
        
        # Panel vacío inicial
        self.config_empty = QLabel("Selecciona una sección para\nconfigurarla")
        self.config_empty.setStyleSheet("color: #999; text-align: center; padding: 60px 20px;")
        self.config_empty.setAlignment(Qt.AlignCenter)
        self.config_layout.addWidget(self.config_empty)
        self.config_layout.addStretch()
        
        scroll_config.setWidget(self.config_widget)
        scroll_config.setMinimumWidth(260)
        right_panel.addWidget(scroll_config)
        
        content_layout.addLayout(left_panel, 1)
        content_layout.addLayout(center_panel, 1)
        content_layout.addLayout(right_panel, 1)
        
        main_layout.addLayout(content_layout)
        
        # Separador elegante
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: linear-gradient(90deg, transparent 0%, #ddd 20%, #ddd 80%, transparent 100%);")
        sep.setMaximumHeight(1)
        main_layout.addWidget(sep)
        
        # Panel de configuración - Cards mejoradas
        config_frame = QFrame()
        config_frame.setStyleSheet("""
            QFrame {
                background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        config_layout = QVBoxLayout(config_frame)
        config_layout.setSpacing(16)
        config_layout.setContentsMargins(20, 20, 20, 20)
        
        # Título de configuración
        lbl_config_title = QLabel("⚙️ Configuración de Tamaños")
        lbl_config_title.setStyleSheet("""
            color: #1F2937;
            font-weight: 700;
            font-size: 12px;
        """)
        config_layout.addWidget(lbl_config_title)
        
        # Grid de opciones
        config_grid = QGridLayout()
        config_grid.setSpacing(16)
        config_grid.setContentsMargins(0, 0, 0, 0)
        
        # Tarjeta 1: Ancho de boleta
        card1 = QFrame()
        card1.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
            }
            QFrame:hover {
                border: 2px solid #3b82f6;
                background: #f0f9ff;
            }
        """)
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(8, 8, 8, 8)
        card1_layout.setSpacing(6)
        
        lbl_ancho_title = QLabel("📏 Ancho de Boleta")
        lbl_ancho_title.setStyleSheet("font-weight: 600; color: #1F2937; font-size: 11px;")
        card1_layout.addWidget(lbl_ancho_title)
        
        self.spin_ancho = QSpinBox()
        self.spin_ancho.setMinimum(40)
        self.spin_ancho.setMaximum(200)
        self.spin_ancho.setValue(80)
        self.spin_ancho.setSuffix(" mm")
        self.spin_ancho.setStyleSheet("""
            QSpinBox {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 6px 8px;
                background: white;
                color: #374151;
                font-weight: 500;
            }
            QSpinBox:focus {
                border: 2px solid #3b82f6;
            }
        """)
        card1_layout.addWidget(self.spin_ancho)
        
        lbl_ancho_desc = QLabel("Ancho estándar para impresoras térmicas")
        lbl_ancho_desc.setStyleSheet("color: #9CA3AF; font-size: 9px;")
        card1_layout.addWidget(lbl_ancho_desc)
        
        config_grid.addWidget(card1, 0, 0)
        
        # Tarjeta 2: Margen interno
        card2 = QFrame()
        card2.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
            }
            QFrame:hover {
                border: 2px solid #8b5cf6;
                background: #faf5ff;
            }
        """)
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(8, 8, 8, 8)
        card2_layout.setSpacing(6)
        
        lbl_margen_title = QLabel("↔️ Margen Interno")
        lbl_margen_title.setStyleSheet("font-weight: 600; color: #1F2937; font-size: 11px;")
        card2_layout.addWidget(lbl_margen_title)
        
        self.spin_margen = QDoubleSpinBox()
        self.spin_margen.setMinimum(0.5)
        self.spin_margen.setMaximum(10)
        self.spin_margen.setValue(2.5)
        self.spin_margen.setSingleStep(0.5)
        self.spin_margen.setSuffix(" mm")
        self.spin_margen.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 6px 8px;
                background: white;
                color: #374151;
                font-weight: 500;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        card2_layout.addWidget(self.spin_margen)
        
        lbl_margen_desc = QLabel("Espacio entre contenido y bordes")
        lbl_margen_desc.setStyleSheet("color: #9CA3AF; font-size: 9px;")
        card2_layout.addWidget(lbl_margen_desc)
        
        config_grid.addWidget(card2, 0, 1)
        
        config_layout.addLayout(config_grid)
        main_layout.addWidget(config_frame)
        
        # Botones de acción - Cards mejoradas
        btn_frame = QFrame()
        btn_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setSpacing(12)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        # Botón Imprimir Prueba
        btn_imprimir = QPushButton("🖨️ Imprimir Prueba")
        btn_imprimir.setMinimumHeight(40)
        btn_imprimir.setMinimumWidth(150)
        btn_imprimir.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 10px 20px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            }
            QPushButton:pressed {
                background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
            }
        """)
        btn_imprimir.setCursor(QtCore.Qt.PointingHandCursor)
        btn_imprimir.clicked.connect(self.imprimir_prueba)
        btn_layout.addWidget(btn_imprimir)
        
        # Botón Limpiar
        btn_limpiar = QPushButton("  Limpiar")
        btn_limpiar.setMinimumHeight(40)
        btn_limpiar.setMinimumWidth(130)
        btn_limpiar.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 10px 20px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
            }
            QPushButton:pressed {
                background: linear-gradient(135deg, #c2410c 0%, #92400e 100%);
            }
        """)
        btn_limpiar.setCursor(QtCore.Qt.PointingHandCursor)
        btn_limpiar.clicked.connect(self.limpiar_construccion)
        btn_layout.addWidget(btn_limpiar)
        
        # Botón Guardar (Primario)
        btn_guardar = QPushButton("💾 Guardar Plantilla")
        btn_guardar.setMinimumHeight(40)
        btn_guardar.setMinimumWidth(150)
        btn_guardar.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 10px 20px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #059669 0%, #047857 100%);
            }
            QPushButton:pressed {
                background: linear-gradient(135deg, #047857 0%, #065f46 100%);
            }
        """)
        btn_guardar.setCursor(QtCore.Qt.PointingHandCursor)
        btn_guardar.clicked.connect(self.guardar_configuracion)
        btn_layout.addWidget(btn_guardar)
        
        btn_frame.setLayout(btn_layout)
        main_layout.addWidget(btn_frame)
    
    def on_section_dropped(self, section_id):
        """Manejador cuando se suelta una sección."""
        if section_id not in self.drop_zone.dropped_sections:
            title, description, emoji = self.sections_available[section_id]
            self.drop_zone.add_section(section_id, title, description, emoji)
    
    def on_section_selected(self, section_id):
        """Muestra configuración cuando se selecciona una sección."""
        self.current_selected_section = section_id
        self.show_section_config(section_id)
    
    def show_section_config(self, section_id):
        """Muestra los controles de configuración para una sección."""
        # Limpiar layout actual
        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if section_id not in self.sections_available:
            return
        
        title, description, emoji = self.sections_available[section_id]
        config = self.drop_zone.section_configs.get(section_id, {})
        
        # Título de la sección
        lbl_title = QLabel(f"{emoji} {title}")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #333; padding: 8px 0px;")
        self.config_layout.addWidget(lbl_title)
        
        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        self.config_layout.addWidget(sep)
        
        # ========== ALINEACIÓN ==========
        lbl_alignment = QLabel("Alineación Horizontal:")
        lbl_alignment.setStyleSheet("font-weight: bold; font-size: 10px; color: #555;")
        self.config_layout.addWidget(lbl_alignment)
        
        alignment_layout = QHBoxLayout()
        alignment_layout.setSpacing(4)
        
        btn_left = QPushButton("← Izq")
        btn_left.setMinimumHeight(32)
        alignment = config.get('alignment', 'center')
        bg_left = "#e8f5e9" if alignment == 'left' else "#f5f5f5"
        border_left = "#c8e6c9" if alignment == 'left' else "#ddd"
        btn_left.setStyleSheet(f"""
            QPushButton {{
                background: {bg_left};
                border: 1px solid {border_left};
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{ background: #c8e6c9; }}
        """)
        btn_left.clicked.connect(lambda: self.set_section_config(section_id, 'alignment', 'left'))
        alignment_layout.addWidget(btn_left)
        
        btn_center = QPushButton("⊕ Centro")
        btn_center.setMinimumHeight(32)
        bg_center = "#e8f5e9" if alignment == 'center' else "#f5f5f5"
        border_center = "#c8e6c9" if alignment == 'center' else "#ddd"
        btn_center.setStyleSheet(f"""
            QPushButton {{
                background: {bg_center};
                border: 1px solid {border_center};
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{ background: #c8e6c9; }}
        """)
        btn_center.clicked.connect(lambda: self.set_section_config(section_id, 'alignment', 'center'))
        alignment_layout.addWidget(btn_center)
        
        btn_right = QPushButton("Der →")
        btn_right.setMinimumHeight(32)
        bg_right = "#e8f5e9" if alignment == 'right' else "#f5f5f5"
        border_right = "#c8e6c9" if alignment == 'right' else "#ddd"
        btn_right.setStyleSheet(f"""
            QPushButton {{
                background: {bg_right};
                border: 1px solid {border_right};
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{ background: #c8e6c9; }}
        """)
        btn_right.clicked.connect(lambda: self.set_section_config(section_id, 'alignment', 'right'))
        alignment_layout.addWidget(btn_right)
        
        self.config_layout.addLayout(alignment_layout)
        
        # ========== ANCHO ==========
        lbl_width = QLabel("Ancho en Boleta:")
        lbl_width.setStyleSheet("font-weight: bold; font-size: 10px; color: #555; margin-top: 16px;")
        self.config_layout.addWidget(lbl_width)
        
        width_layout = QHBoxLayout()
        width_layout.setSpacing(8)
        
        slider_width = QSlider(Qt.Horizontal)
        slider_width.setMinimum(20)
        slider_width.setMaximum(100)
        slider_width.setValue(config.get('width', 100))
        slider_width.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #c8e6c9;
                height: 8px;
                background: #e8f5e9;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2a7f2a;
                border: 1px solid #1f5f1f;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        slider_width.valueChanged.connect(lambda v: self.set_section_config(section_id, 'width', v))
        width_layout.addWidget(slider_width)
        
        lbl_width_value = QLabel(f"{config.get('width', 100)}%")
        lbl_width_value.setStyleSheet("font-weight: bold; font-size: 10px; min-width: 40px;")
        width_layout.addWidget(lbl_width_value)
        
        # Actualizar label cuando cambia el slider
        slider_width.valueChanged.connect(lambda v: lbl_width_value.setText(f"{v}%"))
        
        self.config_layout.addLayout(width_layout)
        
        # ========== INFORMACIÓN ==========
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background: #e3f2fd;
                border: 1px solid #bbdefb;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(4)
        
        lbl_info_title = QLabel("ℹ️ Información de Sección")
        lbl_info_title.setStyleSheet("font-weight: bold; font-size: 10px; color: #1565c0;")
        info_layout.addWidget(lbl_info_title)
        
        lbl_info_desc = QLabel(description)
        lbl_info_desc.setStyleSheet("font-size: 9px; color: #424242;")
        lbl_info_desc.setWordWrap(True)
        info_layout.addWidget(lbl_info_desc)
        
        self.config_layout.addWidget(info_frame)
        
        self.config_layout.addStretch()
    
    def set_section_config(self, section_id, key, value):
        """Actualiza la configuración de una sección."""
        if section_id in self.drop_zone.section_configs:
            self.drop_zone.section_configs[section_id][key] = value
            # Actualizar vista
            self.show_section_config(section_id)
    
    def cargar_configuracion(self):
        """Carga la configuración actual de la plantilla."""
        try:
            plantilla = cargar_plantilla_boleta(self.username)
            
            # Tamaños
            self.spin_ancho.setValue(plantilla.get('ancho_mm', 80))
            self.spin_margen.setValue(plantilla.get('margen_mm', 2.5))
            
            # Secciones en orden
            secciones = plantilla.get('secciones_orden', [
                'encabezado', 'fecha', 'cliente', 'tabla', 'totales', 'qr', 'pie'
            ])
            
            self.drop_zone.clear_sections()
            for section_id in secciones:
                if section_id in self.sections_available:
                    title, description, emoji = self.sections_available[section_id]
                    self.drop_zone.add_section(section_id, title, description, emoji)
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
    
    def guardar_configuracion(self):
        """Guarda la configuración de la plantilla."""
        try:
            plantilla = {
                'ancho_mm': self.spin_ancho.value(),
                'margen_mm': self.spin_margen.value(),
                'secciones_orden': self.drop_zone.get_sections_order(),
                'secciones_config': self.drop_zone.section_configs,
            }
            
            guardar_plantilla_boleta(self.username, plantilla)
            
            QMessageBox.information(
                self,
                "✅ Configuración Guardada",
                "La configuración de tu plantilla de boleta se ha guardado correctamente.\n"
                "Los próximos recibos que generes utilizarán esta personalización."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "❌ Error al Guardar",
                f"No se pudo guardar la configuración:\n{str(e)}"
            )
    
    def restaurar_predeterminados(self):
        """Restaura los valores predeterminados."""
        reply = QMessageBox.question(
            self,
            "🔄 Restaurar Valores Predeterminados",
            "¿Deseas restaurar la plantilla a los valores predeterminados?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.spin_ancho.setValue(80)
            self.spin_margen.setValue(2.5)
            
            self.drop_zone.clear_sections()
            
            # Agregar orden predeterminado
            default_sections = ['encabezado', 'fecha', 'cliente', 'tabla', 'totales', 'qr', 'pie']
            for section_id in default_sections:
                title, description, emoji = self.sections_available[section_id]
                self.drop_zone.add_section(section_id, title, description, emoji)
    
    def limpiar_construccion(self):
        """Limpia la construcción actual."""
        self.drop_zone.clear_sections()
        self.current_selected_section = None
        # Resetear panel de configuración
        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.config_layout.addWidget(self.config_empty)
        self.config_layout.addStretch()
    
    def imprimir_prueba(self):
        """Abre diálogo para seleccionar impresora e imprime una boleta de prueba."""
        try:
            from gui.dialogs.printer_selection_dialog import PrinterSelectionDialog
            
            # Abrir diálogo de selección de impresora
            dialog = PrinterSelectionDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                printer_name = dialog.selected_printer
                
                if not printer_name:
                    return
                
                # Guardar impresora seleccionada como predeterminada
                guardar_impresora_predeterminada(self.username, printer_name)
                
                # Generar PDF de prueba
                pdf_path = self.generar_pdf_prueba()
                
                if not pdf_path:
                    QMessageBox.critical(
                        self,
                        "❌ Error",
                        "No se pudo generar el PDF de prueba."
                    )
                    return
                
                # Imprimir PDF
                self.imprimir_pdf(pdf_path, printer_name)
                
                QMessageBox.information(
                    self,
                    "✅ Impresión Enviada",
                    f"Boleta de prueba enviada a: {printer_name}"
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "❌ Error al Imprimir",
                f"Ocurrió un error:\n{str(e)}"
            )
    
    def generar_pdf_prueba(self):
        """Genera un PDF de prueba leyendo EXACTAMENTE la configuración de plantilla_boleta.json."""
        try:
            from fpdf import FPDF
            import tempfile
            from pathlib import Path
            from datetime import datetime
            import json
            import os
            
            # 1. LEER LA CONFIGURACIÓN GUARDADA
            print("\n" + "="*60)
            print("GENERANDO PDF DE PRUEBA")
            print("="*60)
            
            # Buscar en la ruta relativa al directorio actual
            plantilla_path = Path(f"VISO/{self.username}/data/plantilla_boleta.json")
            
            print(f"\n1️⃣ BUSCANDO ARCHIVO:")
            print(f"   Ruta: {plantilla_path}")
            print(f"   Existe: {plantilla_path.exists()}")
            
            # Si no existe, intentar desde la ruta absoluta
            if not plantilla_path.exists():
                from utils.file_handler import get_user_file_path
                plantilla_path = get_user_file_path(self.username, "plantilla_boleta.json")
                print(f"   Intentando ruta absoluta: {plantilla_path}")
                print(f"   Existe: {plantilla_path.exists()}")
            
            if not plantilla_path.exists():
                print(f"\n❌ Archivo NO ENCONTRADO: {plantilla_path}")
                QMessageBox.warning(
                    self,
                    "⚠️ Configuración no encontrada",
                    f"No se encontró el archivo de plantilla.\n\nRuta: {plantilla_path}\n\nGuarda la configuración primero."
                )
                return None
            
            with open(plantilla_path, 'r', encoding='utf-8') as f:
                plantilla = json.load(f)
            
            print(f"   ✅ Archivo cargado")
            
            # Extraer configuración
            ancho = plantilla.get('ancho_mm', 80)
            margen = plantilla.get('margen_mm', 2.5)
            secciones_orden = plantilla.get('secciones_orden', [])
            secciones_config = plantilla.get('secciones_config', {})
            
            print(f"\n2️⃣ CONFIGURACIÓN:")
            print(f"   Ancho: {ancho}mm")
            print(f"   Margen: {margen}mm")
            print(f"   Secciones: {secciones_orden}")
            print(f"   Config guardada: {list(secciones_config.keys())}")
            
            # Validar que hay secciones
            if not secciones_orden:
                print("\n❌ NO HAY SECCIONES")
                QMessageBox.warning(
                    self,
                    "⚠️ Sin secciones",
                    "No hay secciones. Arrastra secciones y guarda primero."
                )
                return None
            
            # 2. CREAR PDF
            pdf = FPDF('P', 'mm', (ancho, 280))
            pdf.add_page()
            pdf.set_left_margin(margen)
            pdf.set_right_margin(margen)
            pdf.set_top_margin(margen)
            pdf.set_auto_page_break(auto=True, margin=margen)
            
            ancho_disponible = ancho - (2 * margen)
            
            # 3. DATOS
            datos_seccion = {
                'encabezado': [
                    'ÓPTICA VISIÓN CLARA',
                    'RUC: 12345678901',
                    'Tel: 987654321'
                ],
                'fecha': [
                    f'Fecha: {datetime.now().strftime("%d/%m/%Y")}',
                    f'Hora: {datetime.now().strftime("%H:%M:%S")}'
                ],
                'cliente': [
                    'Cliente: JUAN PÉREZ GARCÍA',
                    'DNI: 12345678',
                    'Email: juan@example.com'
                ],
                'optometra': [
                    'Atendido por: Dr. Carlos López'
                ],
                'tabla': [
                    'DESCRIPCIÓN                    CANT      P.U.       TOTAL',
                    'Montura Titanio Deportiva        1       350.00      350.00',
                    'Lentes Oftálmicos Anti-Reflejo   1       450.00      450.00',
                    'Tratamiento Anti-Rayos Azules    1       150.00      150.00'
                ],
                'totales': [
                    'Subtotal:                              950.00',
                    'IGV (18%):                             171.00'
                ],
                'monto_letras': [
                    'TOTAL: MIL CIENTO VEINTIUNO CON 00/100',
                    ' '
                ],
                'qr': [
                    '[QR: 00121202512050001]'
                ],
                'pie': [
                    '¡Gracias por su compra!',
                    'Garantía 2 años en monturas',
                    'Forma de pago: Efectivo'
                ]
            }
            
            # 4. RENDERIZAR
            print(f"\n3️⃣ RENDERIZANDO {len(secciones_orden)} SECCIONES:")
            
            for idx, section_id in enumerate(secciones_orden, 1):
                config = secciones_config.get(section_id, {})
                width_percent = config.get('width', 100) / 100.0
                alignment = config.get('alignment', 'center')
                
                lineas = datos_seccion.get(section_id, [])
                
                print(f"\n   [{idx}] {section_id.upper()}")
                print(f"       Width: {width_percent*100:.0f}% | Align: {alignment}")
                
                if not lineas:
                    print(f"       ⚠️ Sin datos")
                    continue
                
                print(f"       Líneas: {len(lineas)}")
                
                ancho_seccion = ancho_disponible * width_percent
                
                if alignment == 'left':
                    align_fpdf = 'L'
                    x_pos = margen
                elif alignment == 'right':
                    align_fpdf = 'R'
                    x_pos = margen + (ancho_disponible - ancho_seccion)
                else:
                    align_fpdf = 'C'
                    x_pos = margen + (ancho_disponible - ancho_seccion) / 2
                
                pdf.set_font("Courier", "", 7)
                for linea in lineas:
                    linea_limpia = ''.join(c for c in linea if ord(c) < 128)
                    pdf.set_x(x_pos)
                    pdf.cell(ancho_seccion, 4, linea_limpia, 0, 1, align=align_fpdf)
                
                if idx < len(secciones_orden):
                    y_actual = pdf.get_y()
                    pdf.set_line_width(0.2)
                    pdf.line(margen, y_actual + 1, ancho - margen, y_actual + 1)
                    pdf.ln(2)
            
            # 5. GUARDAR
            temp_dir = Path(tempfile.gettempdir())
            pdf_path = temp_dir / "boleta_prueba.pdf"
            pdf.output(str(pdf_path))
            
            print(f"\n✅ PDF GUARDADO: {pdf_path}")
            print("="*60 + "\n")
            
            return str(pdf_path)
        
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "❌ Error", f"Error al generar PDF:\n{str(e)}")
            return None
    
    def imprimir_pdf(self, pdf_path, printer_name):
        """Imprime un PDF usando la impresora especificada (Bluetooth o Cableada)."""
        # Ejecutar en thread separado para no congelar la GUI
        from PyQt5.QtCore import QThread, pyqtSignal
        
        class PrintThread(QThread):
            finished = pyqtSignal(bool, str)  # success, message
            
            def __init__(self, pdf_path, printer_name, parent_widget):
                super().__init__()
                self.pdf_path = pdf_path
                self.printer_name = printer_name
                self.parent_widget = parent_widget
            
            def run(self):
                try:
                    import platform
                    system = platform.system()
                    
                    if system == "Windows":
                        # Detectar tipo de impresora automáticamente
                        is_bluetooth = any(x in self.printer_name.upper() for x in ['BT-', 'BLUETOOTH', 'HOCO', 'THERMAL'])
                        
                        if is_bluetooth:
                            # IMPRESORA BLUETOOTH (Térmica)
                            try:
                                from utils.escpos_thermal_printer import ThermalBluetoothPrinter
                                success, message = ThermalBluetoothPrinter.print_pdf_to_thermal(self.pdf_path)
                                self.finished.emit(success, message)
                            except Exception as e:
                                self.finished.emit(False, f"Error en impresión Bluetooth: {str(e)}")
                        else:
                            # IMPRESORA CABLEADA (USB/Red)
                            try:
                                self.parent_widget._print_via_windows_api(self.pdf_path, self.printer_name)
                                self.finished.emit(True, f"Boleta enviada a {self.printer_name}")
                            except Exception as e:
                                self.finished.emit(False, f"Error en impresión cableada: {str(e)}")
                    
                    elif system == "Darwin":  # macOS
                        import subprocess
                        subprocess.run(
                            ["lp", "-d", self.printer_name, self.pdf_path],
                            timeout=10, capture_output=True
                        )
                        self.finished.emit(True, f"Impresión enviada a {self.printer_name}")
                    
                    else:  # Linux
                        import subprocess
                        subprocess.run(
                            ["lp", "-d", self.printer_name, self.pdf_path],
                            timeout=10, capture_output=True
                        )
                        self.finished.emit(True, f"Impresión enviada a {self.printer_name}")
                
                except Exception as e:
                    self.finished.emit(False, f"Error al imprimir: {str(e)}")
        
        # Crear y ejecutar thread
        print_thread = PrintThread(pdf_path, printer_name, self)
        
        def on_print_finished(success, message):
            from PyQt5.QtWidgets import QMessageBox
            
            if success:
                print(f"✓ {message}")
                QMessageBox.information(self, "✅ Impresión Completada", message)
            else:
                print(f"❌ {message}")
                # Mostrar error con opción de reintentar
                reply = QMessageBox.critical(
                    self,
                    "❌ Error en Impresora",
                    f"{message}\n\n¿Deseas intentar nuevamente?",
                    QMessageBox.Retry | QMessageBox.Open | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Retry:
                    # Reintentar
                    self.imprimir_pdf(pdf_path, printer_name)
                elif reply == QMessageBox.Open:
                    # Abrir PDF para impresión manual
                    self._open_pdf_with_viewer(pdf_path)
            
            # Limpiar thread
            print_thread.deleteLater()
        
        print_thread.finished.connect(on_print_finished)
        print_thread.start()
        print(f"📤 Enviando a impresora {printer_name}...")
    
    def _print_via_windows_api(self, pdf_path, printer_name):
        """Intenta imprimir usando varios métodos de Windows sin bloquear."""
        import subprocess
        import os
        import time
        
        pdf_path = os.path.abspath(pdf_path)
        
        # Opción 1: Usar PowerShell SIN esperar (sin -Wait)
        try:
            powershell_cmd = f'''
            $PDFFile = '{pdf_path}'
            $PrinterName = '{printer_name}'
            Start-Process -FilePath $PDFFile -Verb PrintTo -ArgumentList $PrinterName
            '''
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", powershell_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"✓ Impresión enviada via PowerShell")
            return
        except Exception as e:
            print(f"PowerShell falló: {e}")
        
        # Opción 2: Usar comando print directo
        try:
            import shutil
            import tempfile
            
            # Copiar a temporal para evitar problemas de acceso
            temp_dir = tempfile.gettempdir()
            temp_pdf = os.path.join(temp_dir, "viso_boleta_temp.pdf")
            shutil.copy2(pdf_path, temp_pdf)
            
            cmd = f'print /d:"{printer_name}" "{temp_pdf}"'
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✓ Impresión enviada via print")
            return
        except Exception as e:
            print(f"Print command falló: {e}")
        
        # Opción 3: Abrir directamente
        try:
            os.startfile(pdf_path, "print")
            print(f"✓ Impresión enviada via startfile")
            return
        except Exception as e:
            print(f"Startfile falló: {e}")
        
        # Opción 4: Fallback final
        try:
            subprocess.Popen(f'start "" "{pdf_path}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✓ Impresión enviada via start")
            return
        except Exception as e:
            print(f"Start falló: {e}")
            raise Exception("No se pudo enviar a imprimir")
    
    def _open_pdf_with_viewer(self, pdf_path):
        """Abre el PDF con Chrome."""
        open_pdf_with_chrome(pdf_path)
