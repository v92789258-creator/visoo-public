"""Página de Libro Contable para ver cambios realizados en el sistema."""
from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime
import os

class AuditPage(QtWidgets.QWidget):
    """Página para visualizar el Libro Contable (registro inmutable de cambios)."""
    
    def __init__(self, main_window=None, username=None):
        super().__init__()
        self.main_window = main_window
        self.username = username or 'alex9121'
        self.audit_manager = None
        
        # Configuración visual global
        self.setFont(QtGui.QFont("Segoe UI", 10))
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                color: #1a1a1a;
            }
            QScrollBar:vertical {
                border: none;
                background: #f1f1f1;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                min-height: 20px;
                border-radius: 5px;
            }
        """)
        
        self.init_ui()
        self.load_audit_log()
    
    def init_ui(self):
        """Inicializa la interfaz con diseño profesional."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)
        
        # --- HEADER SUPERIOR ---
        header_container = QtWidgets.QFrame()
        header_layout = QtWidgets.QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(24)
        
        # Título y Subtítulo
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(6)
        
        title = QtWidgets.QLabel("Libro Contable")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1a1a1a; font-family: 'Segoe UI';")
        
        subtitle_layout = QtWidgets.QHBoxLayout()
        subtitle_layout.setSpacing(12)
        
        subtitle = QtWidgets.QLabel("Registro de Auditoría y Control")
        subtitle.setStyleSheet("font-size: 14px; color: #6c757d;")
        
        # Badge de Seguridad
        lock_badge = QtWidgets.QLabel("Inmutable")
        lock_badge.setStyleSheet("""
            background-color: #F0F0F0;
            color: #666666;
            border-radius: 0px;
            padding: 4px 10px;
            font-size: 10px;
            font-weight: bold;
            border: 1px solid #E0E0E0;
        """)
        lock_badge.setToolTip("Este registro está protegido contra escritura y borrado.")
        
        subtitle_layout.addWidget(subtitle)
        subtitle_layout.addWidget(lock_badge)
        subtitle_layout.addStretch()
        
        title_box.addWidget(title)
        title_box.addLayout(subtitle_layout)
        header_layout.addLayout(title_box)
        
        header_layout.addStretch()
        
        # Botones de Acción Global (Header)
        btn_style = """
            QPushButton {
                background-color: white;
                color: #444;
                border: 1px solid #ddd;
                padding: 12px 24px;
                border-radius: 0px;
                font-weight: 600;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover { background-color: #f8f9fa; border-color: #bbb; }
        """
        
        refresh_btn = QtWidgets.QPushButton("Actualizar")
        refresh_btn.setCursor(QtCore.Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(btn_style)
        refresh_btn.clicked.connect(self.load_audit_log)
        header_layout.addWidget(refresh_btn)
        
        export_menu = QtWidgets.QToolButton()
        export_menu.setText("Exportar")
        export_menu.setCursor(QtCore.Qt.PointingHandCursor)
        export_menu.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        export_menu.setStyleSheet("""
            QToolButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            QToolButton:hover { background-color: #0056b3; }
            QToolButton::menu-indicator { width: 0px; }
        """)
        
        export_menu_items = QtWidgets.QMenu()
        export_menu_items.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #eee; padding: 8px; border-radius: 6px; }
            QMenu::item { padding: 10px 30px; border-radius: 4px; color: #333; }
            QMenu::item:selected { background-color: #f0f7ff; color: #007bff; }
        """)
        
        export_csv = export_menu_items.addAction("CSV")
        export_csv.triggered.connect(self.export_audit_csv)
        export_excel = export_menu_items.addAction("Excel")
        export_excel.triggered.connect(self.export_audit_excel)
        export_pdf = export_menu_items.addAction("PDF")
        export_pdf.triggered.connect(self.export_audit_pdf)
        
        export_menu.setMenu(export_menu_items)
        header_layout.addWidget(export_menu)
        
        main_layout.addWidget(header_container)
        
        # --- TAB WIDGET ESTILIZADO ---
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background: white;
                border-radius: 0px;
                top: -1px;
            }
            QTabBar::tab {
                background: transparent;
                color: #666;
                padding: 14px 28px;
                font-size: 14px;
                font-weight: 600;
                border-bottom: 3px solid transparent;
                margin-right: 4px;
            }
            QTabBar::tab:hover {
                color: #007bff;
                background: #f8f9fa;
            }
            QTabBar::tab:selected {
                color: #007bff;
                border-bottom: 3px solid #007bff;
                background: white;
            }
        """)
        
        # TAB 1: TODAS LAS ACCIONES
        self.setup_tab_all()
        
        # TAB 2: VENTAS
        self.setup_tab_ventas()
        
        # Connect tab changes to load data
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        main_layout.addWidget(self.tab_widget)
        
        # Footer Informativo
        footer_label = QtWidgets.QLabel("Todos los movimientos son registrados localmente.")
        footer_label.setStyleSheet("color: #999; font-size: 11px; margin-top: 12px;")
        footer_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(footer_label)

    def setup_tab_all(self):
        """Configura la pestaña de Todas las Acciones."""
        tab_all = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab_all)
        layout.setContentsMargins(28, 32, 28, 28)
        layout.setSpacing(20)
        
        # --- Barra de Filtros (Estilo Toolbar) ---
        filter_frame = QtWidgets.QFrame()
        filter_frame.setStyleSheet("""
            QFrame { background-color: #f8f9fa; border-radius: 8px; }
            QLabel { color: #555; font-weight: 700; font-size: 12px; }
        """)
        filter_layout = QtWidgets.QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(18, 14, 18, 14)
        filter_layout.setSpacing(16)
        
        # Combo Styles
        combo_style = """
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px 12px;
                background: white;
                min-width: 160px;
                color: #333;
                font-size: 13px;
            }
            QComboBox:hover { border-color: #b3b3b3; }
            QComboBox::drop-down { border: none; width: 20px; }
        """
        
        filter_layout.addWidget(QtWidgets.QLabel("MÓDULO:"))
        self.module_filter = QtWidgets.QComboBox()
        self.module_filter.addItems(["Todos", "inventario", "pacientes", "ventas", "graduaciones", "reportes", "ayudantes"])
        self.module_filter.setStyleSheet(combo_style)
        self.module_filter.currentTextChanged.connect(self.load_audit_log)
        filter_layout.addWidget(self.module_filter)
        
        filter_layout.addSpacing(24)
        
        filter_layout.addWidget(QtWidgets.QLabel("ACCIÓN:"))
        self.action_filter = QtWidgets.QComboBox()
        self.action_filter.addItems(["Todas", "crear", "editar", "eliminar", "ver", "descargar"])
        self.action_filter.setStyleSheet(combo_style)
        self.action_filter.currentTextChanged.connect(self.load_audit_log)
        filter_layout.addWidget(self.action_filter)
        
        filter_layout.addStretch()
        layout.addWidget(filter_frame)
        
        # --- Tabla ---
        self.table = QtWidgets.QTableWidget()
        self.configure_table_style(self.table)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["FECHA", "USUARIO", "ACTOR", "ACCIÓN", "MÓDULO", "DETALLES"])
        self.table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.table)
        
        # --- Stats Footer ---
        self.stats_label = QtWidgets.QLabel()
        self.stats_label.setStyleSheet("color: #666; font-size: 12px; font-weight: 500; margin-top: 6px;")
        layout.addWidget(self.stats_label)
        
        self.tab_widget.addTab(tab_all, "Historial General")

    def setup_tab_ventas(self):
        """Configura la pestaña de Solo Ventas."""
        tab_ventas = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab_ventas)
        layout.setContentsMargins(28, 32, 28, 28)
        layout.setSpacing(20)
        
        # Header de Tab Ventas
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(20)
        
        info_sunat = QtWidgets.QLabel("Facturación Electrónica & Ventas")
        info_sunat.setStyleSheet("font-size: 17px; font-weight: bold; color: #333;")
        header_layout.addWidget(info_sunat)
        
        header_layout.addStretch()
        
        # Botón Recargar
        btn_reload = QtWidgets.QPushButton("↻ Recargar")
        btn_reload.setCursor(QtCore.Qt.PointingHandCursor)
        btn_reload.setStyleSheet("""
            QPushButton {
                background: #00897B;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
            }
            QPushButton:hover { background: #00695C; }
        """)
        btn_reload.clicked.connect(self.load_ventas_tab)
        header_layout.addWidget(btn_reload)

        # Botón SUNAT
        btn_sunat = QtWidgets.QPushButton("SUNAT PLE")
        btn_sunat.setCursor(QtCore.Qt.PointingHandCursor)
        btn_sunat.setStyleSheet("""
            QPushButton {
                background: #0052CC;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover { background: #003D99; }
        """)
        btn_sunat.clicked.connect(self.exportar_sunat_ple)
        header_layout.addWidget(btn_sunat)
        
        # Botón Exportar Solo Ventas
        btn_export_ventas = QtWidgets.QPushButton("Exportar Ventas")
        btn_export_ventas.setCursor(QtCore.Qt.PointingHandCursor)
        btn_export_ventas.setStyleSheet("""
            QPushButton {
                background-color: #0052CC;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover { background-color: #003D99; }
        """)
        btn_export_ventas.clicked.connect(self.exportar_solo_ventas)
        header_layout.addWidget(btn_export_ventas)
        
        # Botón Exportar Combinado
        btn_export_combo = QtWidgets.QPushButton("Ventas + Graduaciones")
        btn_export_combo.setCursor(QtCore.Qt.PointingHandCursor)
        btn_export_combo.setStyleSheet("""
            QPushButton {
                background-color: #0052CC;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 12px;
                min-width: 140px;
            }
            QPushButton:hover { background-color: #003D99; }
        """)
        btn_export_combo.clicked.connect(self.exportar_ventas_graduaciones_combinado)
        header_layout.addWidget(btn_export_combo)
        
        layout.addLayout(header_layout)
        
        # Tabla Ventas
        self.table_ventas = QtWidgets.QTableWidget()
        self.configure_table_style(self.table_ventas)
        self.table_ventas.setColumnCount(6)
        self.table_ventas.setHorizontalHeaderLabels([
            "FECHA", "CAJERO", "CLIENTE / INFO", "TIPO MOV.", "MONTO TOTAL", "MÉTODO"
        ])
        self.table_ventas.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.table_ventas)
        
        # Stats Ventas (Diseño tipo tarjeta pequeña)
        stats_container = QtWidgets.QFrame()
        stats_container.setStyleSheet("""
            QFrame {
                background-color: #F0F0F0;
                border: 1px solid #E0E0E0;
                border-radius: 0px;
                padding: 10px 12px;
                margin-top: 8px;
            }
        """)
        stats_layout = QtWidgets.QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stats_ventas_label = QtWidgets.QLabel()
        self.stats_ventas_label.setStyleSheet("color: #1a1a1a; font-size: 12px; font-weight: bold;")
        stats_layout.addWidget(self.stats_ventas_label)
        
        layout.addWidget(stats_container)
        
        self.tab_widget.addTab(tab_ventas, "Registro de Ventas")
        
        # TAB 3: GRADUACIONES
        self.setup_tab_graduaciones()

    def setup_tab_graduaciones(self):
        """Configura la pestaña de Graduaciones/Consultas."""
        tab_grad = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab_grad)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Header
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(20)
        
        info_label = QtWidgets.QLabel("Graduaciones & Consultas Oftalmológicas")
        info_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #333;")
        header_layout.addWidget(info_label)
        header_layout.addStretch()
        
        # Botón Recargar
        btn_reload = QtWidgets.QPushButton("↻ Recargar")
        btn_reload.setCursor(QtCore.Qt.PointingHandCursor)
        btn_reload.setStyleSheet("""
            QPushButton {
                background: #00897B;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover { background: #00695C; }
        """)
        btn_reload.clicked.connect(self.load_graduaciones_tab)
        header_layout.addWidget(btn_reload)

        # Botón Exportar Graduaciones
        btn_export_grad = QtWidgets.QPushButton("Exportar")
        btn_export_grad.setCursor(QtCore.Qt.PointingHandCursor)
        btn_export_grad.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        btn_export_grad.clicked.connect(self.exportar_graduaciones_excel)
        header_layout.addWidget(btn_export_grad)
        
        layout.addLayout(header_layout)
        
        # Tabla Graduaciones
        self.table_graduaciones = QtWidgets.QTableWidget()
        self.configure_table_style(self.table_graduaciones)
        self.table_graduaciones.setColumnCount(8)
        self.table_graduaciones.setHorizontalHeaderLabels([
            "FECHA", "PACIENTE", "DNI", "ÓPTICA/MÉDICO", "TIPO GRAD.", "INFORMACIÓN", "PRECIO", "PAGO"
        ])
        self.table_graduaciones.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_graduaciones)
        
        # Stats Graduaciones
        stats_container = QtWidgets.QFrame()
        stats_container.setStyleSheet("""
            QFrame {
                background-color: #E1F5FE;
                border: 1px solid #B3E5FC;
                border-radius: 8px;
                padding: 16px 18px;
                margin-top: 8px;
            }
        """)
        stats_layout = QtWidgets.QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stats_graduaciones_label = QtWidgets.QLabel()
        self.stats_graduaciones_label.setStyleSheet("color: #0277BD; font-size: 14px; font-weight: bold;")
        stats_layout.addWidget(self.stats_graduaciones_label)
        
        layout.addWidget(stats_container)
        
        self.tab_widget.addTab(tab_grad, "Graduaciones")

    def configure_table_style(self, table):
        """Aplica estilos CSS profesionales a la QTableWidget."""
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setFrameShape(QtWidgets.QFrame.NoFrame)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        
        # Altura de cabecera generosa
        table.horizontalHeader().setFixedHeight(50)
        
        table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #f0f0f0;
                font-size: 13px;
                selection-background-color: #e3f2fd;
                selection-color: #333;
                border: 1px solid #eee;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding-left: 12px;
                padding-right: 12px;
                border-bottom: 1px solid #f5f5f5;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #555;
                font-weight: 700;
                font-size: 12px;
                text-transform: uppercase;
                border: none;
                border-bottom: 2px solid #ddd;
                padding-left: 12px;
                padding-right: 12px;
            }
        """)

    # ---------------------------------------------------------
    #  LÓGICA DEL SISTEMA (Mantenida intacta pero mejorada)
    # ---------------------------------------------------------

    def set_audit_manager(self, audit_manager):
        self.audit_manager = audit_manager
        self.load_audit_log()
    
    def _on_tab_changed(self, index):
        """Carga datos cuando se cambia de pestaña."""
        if index == 2:  # Graduaciones tab (3er tab, índice 2)
            self.load_graduaciones_tab()
    
    def load_audit_log(self):
        """Carga el registro de auditoría con badges visuales."""
        if not self.audit_manager:
            return
        
        module_filter = self.module_filter.currentText()
        action_filter = self.action_filter.currentText()
        
        module = None if module_filter == "Todos" else module_filter
        action = None if action_filter == "Todas" else action_filter
        
        records = self.audit_manager.get_audit_log(limit=500)
        
        filtered_records = []
        for record in records:
            if module and record.get('module') != module:
                continue
            if action and record.get('action') != action:
                continue
            filtered_records.append(record)
        
        self.table.setRowCount(len(filtered_records))
        
        for row, record in enumerate(filtered_records):
            self.table.setRowHeight(row, 54)  # Filas más altas para mejor espaciado
            
            timestamp = record.get('timestamp', '')
            username = record.get('username', '')
            actor = record.get('actor', '')
            actor_type = record.get('actor_type', '')
            action_type = record.get('action', '')
            module_name = record.get('module', '')
            details = record.get('details', '')
            
            # Crear items
            date_item = QtWidgets.QTableWidgetItem(timestamp[:16]) # Sin segundos para limpieza
            date_item.setForeground(QtGui.QColor("#555"))
            
            user_item = QtWidgets.QTableWidgetItem(username)
            user_item.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold))
            
            actor_item = QtWidgets.QTableWidgetItem(f"{actor} ({actor_type})")
            
            # Action con diseño
            action_text = self._format_action(action_type)
            action_item = QtWidgets.QTableWidgetItem(action_text)
            
            # Colores para acciones
            color_map = {
                'crear': '#2e7d32',    # Verde oscuro
                'editar': '#1976d2',   # Azul fuerte
                'eliminar': '#c62828', # Rojo
                'ver': '#f57f17'       # Naranja
            }
            action_color = color_map.get(action_type, '#666')
            action_item.setForeground(QtGui.QColor(action_color))
            action_item.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold))
            
            module_item = QtWidgets.QTableWidgetItem(module_name.upper())
            module_item.setForeground(QtGui.QColor("#777"))
            module_item.setFont(QtGui.QFont("Segoe UI", 9))
            
            details_item = QtWidgets.QTableWidgetItem(str(details)[:80] + "..." if len(str(details)) > 80 else str(details))
            details_item.setForeground(QtGui.QColor("#555"))
            
            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, user_item)
            self.table.setItem(row, 2, actor_item)
            self.table.setItem(row, 3, action_item)
            self.table.setItem(row, 4, module_item)
            self.table.setItem(row, 5, details_item)
        
        stats = self.audit_manager.get_stats()
        self.stats_label.setText(f"Mostrando {len(filtered_records)} registros recientes | Total histórico: {stats['total_acciones']}")
        
        self.load_ventas_tab()
    
    def load_ventas_tab(self):
        """Carga todas las ventas con formato de tabla financiera."""
        try:
            from utils.file_handler import cargar_ventas
            ventas = cargar_ventas(self.username)
            
            if not ventas:
                self.table_ventas.setRowCount(0)
                self.stats_ventas_label.setText("No hay ventas registradas.")
                return
            
            self.table_ventas.setRowCount(len(ventas))
            
            for row, venta in enumerate(ventas):
                self.table_ventas.setRowHeight(row, 56)  # Filas más altas y espaciadas
                
                fecha = venta.get('fecha', 'N/A')
                usuario = self.username
                cliente = venta.get('cliente', 'Público General')
                dni = venta.get('dni_cliente', '-')
                total = float(venta.get('total', 0))
                metodo = venta.get('metodo_pago', 'Efectivo')
                
                # Fecha
                f_item = QtWidgets.QTableWidgetItem(str(fecha)[:16])
                f_item.setTextAlignment(QtCore.Qt.AlignCenter)
                
                # Usuario
                u_item = QtWidgets.QTableWidgetItem(usuario)
                u_item.setTextAlignment(QtCore.Qt.AlignCenter)
                
                # Cliente con DNI abajo (multilínea simulada en texto)
                c_item = QtWidgets.QTableWidgetItem(f"{cliente}\nDNI: {dni}")
                
                # Tipo
                t_item = QtWidgets.QTableWidgetItem("VENTA POS")
                t_item.setForeground(QtGui.QColor("#666"))
                t_item.setTextAlignment(QtCore.Qt.AlignCenter)
                
                # Monto (Estilo financiero)
                m_item = QtWidgets.QTableWidgetItem(f"S/. {total:,.2f}")
                m_item.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold))
                m_item.setForeground(QtGui.QColor("#2E7D32")) # Verde dinero
                m_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                
                # Método
                p_item = QtWidgets.QTableWidgetItem(metodo.upper())
                p_item.setTextAlignment(QtCore.Qt.AlignCenter)
                p_item.setForeground(QtGui.QColor("#0288D1"))
                
                self.table_ventas.setItem(row, 0, f_item)
                self.table_ventas.setItem(row, 1, u_item)
                self.table_ventas.setItem(row, 2, c_item)
                self.table_ventas.setItem(row, 3, t_item)
                self.table_ventas.setItem(row, 4, m_item)
                self.table_ventas.setItem(row, 5, p_item)
            
            total_ventas = sum(float(v.get('total', 0)) for v in ventas)
            self.stats_ventas_label.setText(f"💵 TOTAL RECAUDADO: S/. {total_ventas:,.2f}  |  CANTIDAD DE VENTAS: {len(ventas)}")
        
        except Exception as e:
            self.stats_ventas_label.setText(f"Error cargando ventas: {e}")
    
    def load_graduaciones_tab(self):
        """Carga todas las graduaciones con formato de tabla médica."""
        try:
            from utils.file_handler import cargar_graduaciones
            graduaciones = cargar_graduaciones(self.username)
            
            self.table_graduaciones.setRowCount(len(graduaciones))
            
            total_pago = 0
            for row, grad in enumerate(graduaciones):
                fecha = grad.get('fecha', '')
                paciente = grad.get('paciente', 'N/A')
                dni = grad.get('dni', '')
                optica_medico = grad.get('optica_medico', 'N/A')
                tipo = grad.get('tipo', 'Graduación')
                info = grad.get('informacion', '')
                precio = grad.get('precio', '0')
                pago = grad.get('pago', '0')
                
                # Convertir pago a float para suma
                try:
                    pago_float = float(str(pago).replace(',', '.'))
                    total_pago += pago_float
                except:
                    pago_float = 0
                
                # Alternancia de colores
                bgcolor = QtGui.QColor("#D9E1F2") if row % 2 == 0 else QtGui.QColor("white")
                
                # Fecha
                f_item = QtWidgets.QTableWidgetItem(fecha)
                f_item.setBackground(bgcolor)
                f_item.setTextAlignment(QtCore.Qt.AlignCenter)
                
                # Paciente
                p_item = QtWidgets.QTableWidgetItem(paciente)
                p_item.setBackground(bgcolor)
                
                # DNI
                d_item = QtWidgets.QTableWidgetItem(dni)
                d_item.setBackground(bgcolor)
                d_item.setTextAlignment(QtCore.Qt.AlignCenter)
                
                # Óptica/Médico
                o_item = QtWidgets.QTableWidgetItem(optica_medico)
                o_item.setBackground(bgcolor)
                
                # Tipo Graduación
                t_item = QtWidgets.QTableWidgetItem(tipo)
                t_item.setBackground(bgcolor)
                t_item.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold))
                t_item.setForeground(QtGui.QColor("#0277BD"))
                t_item.setTextAlignment(QtCore.Qt.AlignCenter)
                
                # Información
                i_item = QtWidgets.QTableWidgetItem(info)
                i_item.setBackground(bgcolor)
                i_item.setForeground(QtGui.QColor("#555"))
                
                # Precio
                pr_item = QtWidgets.QTableWidgetItem(f"S/. {float(precio):,.2f}" if precio else "S/. 0.00")
                pr_item.setBackground(bgcolor)
                pr_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                pr_item.setForeground(QtGui.QColor("#666"))
                
                # Pago
                pa_item = QtWidgets.QTableWidgetItem(f"S/. {pago_float:,.2f}")
                pa_item.setBackground(bgcolor)
                pa_item.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold))
                pa_item.setForeground(QtGui.QColor("#2E7D32"))  # Verde dinero
                pa_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                
                self.table_graduaciones.setItem(row, 0, f_item)
                self.table_graduaciones.setItem(row, 1, p_item)
                self.table_graduaciones.setItem(row, 2, d_item)
                self.table_graduaciones.setItem(row, 3, o_item)
                self.table_graduaciones.setItem(row, 4, t_item)
                self.table_graduaciones.setItem(row, 5, i_item)
                self.table_graduaciones.setItem(row, 6, pr_item)
                self.table_graduaciones.setItem(row, 7, pa_item)
                
                # Altura de fila
                self.table_graduaciones.setRowHeight(row, 56)
            
            total_graduaciones = len(graduaciones)
            self.stats_graduaciones_label.setText(f"👓 TOTAL GRADUACIONES: {total_graduaciones}  |  💵 TOTAL RECAUDADO: S/. {total_pago:,.2f}")
        
        except Exception as e:
            self.stats_graduaciones_label.setText(f"Error cargando graduaciones: {e}")
    
    def _format_action(self, action):
        emojis = {
            'crear': 'Crear',
            'editar': 'Editar',
            'eliminar': 'Eliminar',
            'ver': 'Acceso',
            'descargar': 'Descarga',
            'login': 'Inicio Sesión',
            'logout': 'Cierre Sesión'
        }
        return emojis.get(action, action.capitalize())

    # --- MÉTODOS DE EXPORTACIÓN (Sin cambios lógicos, solo alertas estilizadas) ---
    
    def _show_success(self, msg):
        mbox = QtWidgets.QMessageBox(self)
        mbox.setWindowTitle("Operación Exitosa")
        mbox.setText(msg)
        mbox.setIcon(QtWidgets.QMessageBox.Information)
        mbox.exec_()

    def _show_error(self, msg):
        mbox = QtWidgets.QMessageBox(self)
        mbox.setWindowTitle("Error del Sistema")
        mbox.setText(msg)
        mbox.setIcon(QtWidgets.QMessageBox.Critical)
        mbox.exec_()

    def export_audit_csv(self):
        if not self.audit_manager: return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Exportar CSV", f"Audit_{datetime.now().strftime('%Y%m%d')}.csv", "CSV (*.csv)")
        if file_path:
            if self.audit_manager.export_audit_log(file_path):
                self._show_success(f"Archivo generado correctamente:\n{file_path}")
    
    def export_audit_excel(self):
        if not self.audit_manager: return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Exportar Excel", f"Audit_{datetime.now().strftime('%Y%m%d')}.xlsx", "Excel (*.xlsx)")
        if file_path:
            if self.audit_manager.export_audit_excel(file_path):
                self._show_success(f"Hoja de cálculo generada:\n{file_path}")
            else: self._show_error("No se pudo exportar a Excel.")

    def export_audit_pdf(self):
        if not self.audit_manager: return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Exportar PDF", f"Audit_{datetime.now().strftime('%Y%m%d')}.pdf", "PDF (*.pdf)")
        if file_path:
            if self.audit_manager.export_audit_pdf(file_path):
                self._show_success(f"Documento PDF generado:\n{file_path}")
            else: self._show_error("No se pudo exportar a PDF.")

    def exportar_sunat_ple(self):
        """Diálogo mejorado para seleccionar formato SUNAT PLE."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("📤 Exportar SUNAT PLE")
        dialog.setFixedSize(420, 320)
        dialog.setStyleSheet("background: #f5f5f5;")
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        
        # Encabezado
        header = QtWidgets.QLabel("Seleccione formato de exportación:")
        header.setStyleSheet("font-weight: bold; font-size: 15px; color: #333;")
        layout.addWidget(header)
        
        # Descripción
        desc = QtWidgets.QLabel("Elige el formato que mejor se adapte a tus necesidades:")
        desc.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Botones con mejor espaciado y tamaño
        btn_txt = QtWidgets.QPushButton("Formato TXT (Oficial SUNAT)")
        btn_txt.setMinimumHeight(60)
        btn_txt.setCursor(QtCore.Qt.PointingHandCursor)
        btn_txt.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 15px 20px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        
        btn_xlsx = QtWidgets.QPushButton("Formato Excel (Legible)")
        btn_xlsx.setMinimumHeight(60)
        btn_xlsx.setCursor(QtCore.Qt.PointingHandCursor)
        btn_xlsx.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px 20px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        
        btn_both = QtWidgets.QPushButton("📁  Ambos Formatos (TXT + Excel)")
        btn_both.setMinimumHeight(60)
        btn_both.setCursor(QtCore.Qt.PointingHandCursor)
        btn_both.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 15px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover { background-color: #455A64; }
        """)
        
        layout.addWidget(btn_txt)
        layout.addWidget(btn_xlsx)
        layout.addWidget(btn_both)
        
        layout.addStretch()
        
        btn_txt.clicked.connect(lambda: self._exportar_sunat_formato(dialog, 'txt'))
        btn_xlsx.clicked.connect(lambda: self._exportar_sunat_formato(dialog, 'xlsx'))
        btn_both.clicked.connect(lambda: self._exportar_sunat_formato(dialog, 'ambos'))
        
        dialog.exec_()

    def _exportar_sunat_formato(self, dialog, formato):
        dialog.close()
        try:
            from utils.sunat_ple_generator import generar_libro_ventas_sunat, generar_libro_ventas_sunat_excel
            
            username = getattr(self.main_window, 'username', self.username)
            fecha_str = QtCore.QDate.currentDate().toString('yyyyMMdd')
            
            if formato == 'txt':
                path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "SUNAT TXT", f"LE{username}{fecha_str}.txt", "TXT (*.txt)")
                if path:
                    res = generar_libro_ventas_sunat(username, path)
                    self._mostrar_resultado_sunat(res)
            
            elif formato == 'xlsx':
                path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "SUNAT Excel", f"LE{username}{fecha_str}.xlsx", "Excel (*.xlsx)")
                if path:
                    res = generar_libro_ventas_sunat_excel(username, path)
                    self._mostrar_resultado_sunat(res)
            
            elif formato == 'ambos':
                folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
                if folder:
                    path_txt = os.path.join(folder, f"LE{username}{fecha_str}.txt")
                    path_xls = os.path.join(folder, f"LE{username}{fecha_str}.xlsx")
                    res_txt = generar_libro_ventas_sunat(username, path_txt)
                    res_xls = generar_libro_ventas_sunat_excel(username, path_xls)
                    
                    if res_txt['success']:
                        self._show_success(f"Archivos generados en:\n{folder}")
                    else:
                        self._show_error(res_txt.get('mensaje', 'Error desconocido'))

        except Exception as e:
            self._show_error(f"Error en módulo SUNAT:\n{e}")

    def _mostrar_resultado_sunat(self, resultado):
        if resultado['success']:
            msg = f" Procesado Correctamente\n\nTotal Ventas: S/. {resultado.get('total_ventas', 0):.2f}\nComprobantes: {resultado.get('total_comprobantes', 0)}"
            self._show_success(msg)
        else:
            self._show_error(resultado.get('mensaje', 'Error desconocido'))

    def exportar_graduaciones_excel(self):
        """Exporta graduaciones a Excel."""
        try:
            from utils.sunat_ple_generator import generar_libro_graduaciones_excel
            
            username = getattr(self.main_window, 'username', self.username)
            fecha_str = QtCore.QDate.currentDate().toString('yyyyMMdd')
            
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Exportar Graduaciones", f"Graduaciones_{username}_{fecha_str}.xlsx", "Excel (*.xlsx)"
            )
            if path:
                res = generar_libro_graduaciones_excel(username, path)
                if res['success']:
                    msg = f" Graduaciones Exportadas\n\nTotal Registros: {res.get('total_graduaciones', 0)}\nTotal Recaudado: S/. {res.get('total_recaudado', 0):,.2f}\n\nArchivo:\n{path}"
                    self._show_success(msg)
                else:
                    self._show_error(res.get('error', 'Error desconocido'))
        except Exception as e:
            self._show_error(f"Error al exportar graduaciones:\n{e}")

    def exportar_solo_ventas(self):
        """Exporta solo ventas a Excel."""
        try:
            from utils.sunat_ple_generator import generar_libro_ventas_sunat_excel
            
            username = getattr(self.main_window, 'username', self.username)
            fecha_str = QtCore.QDate.currentDate().toString('yyyyMMdd')
            
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Exportar Ventas", f"Ventas_{username}_{fecha_str}.xlsx", "Excel (*.xlsx)"
            )
            if path:
                res = generar_libro_ventas_sunat_excel(username, path)
                if res['success']:
                    msg = f" Ventas Exportadas\n\nTotal Ventas: {res.get('total_comprobantes', 0)}\nTotal Recaudado: S/. {res.get('total_ventas', 0):,.2f}\n\nArchivo:\n{path}"
                    self._show_success(msg)
                else:
                    self._show_error(res.get('error', 'Error desconocido'))
        except Exception as e:
            self._show_error(f"Error al exportar ventas:\n{e}")

    def exportar_ventas_graduaciones_combinado(self):
        """Exporta Ventas + Graduaciones en un mismo Excel."""
        try:
            from utils.sunat_ple_generator import generar_libro_combinado_excel
            
            username = getattr(self.main_window, 'username', self.username)
            fecha_str = QtCore.QDate.currentDate().toString('yyyyMMdd')
            
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Exportar Combinado", f"Ventas_Graduaciones_{username}_{fecha_str}.xlsx", "Excel (*.xlsx)"
            )
            if path:
                res = generar_libro_combinado_excel(username, path)
                if res['success']:
                    msg = f" Exportación Combinada\n\nVentas: {res.get('total_ventas', 0)}\nGraduaciones: {res.get('total_graduaciones', 0)}\n\nTotal Recaudado: S/. {res.get('total_general', 0):,.2f}\n\nArchivo:\n{path}"
                    self._show_success(msg)
                else:
                    self._show_error(res.get('error', 'Error desconocido'))
        except Exception as e:
            self._show_error(f"Error al exportar combinado:\n{e}")