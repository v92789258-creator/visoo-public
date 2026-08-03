"""
csharp_embed_wrapper.py

Wrapper para embeber componentes C# en PyQt5
Proporciona acceso a la página de clientes desde C# dentro de Python

Este módulo crea un contenedor PyQt5 que puede embeber la aplicación C#
o proporcionar una alternativa Python pura si no está disponible.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox, QAbstractItemView, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import time

try:
    from utils.data_handler_optimized import search_patients, load_json_data, get_cache
    HAS_OPTIMIZED_DATA = True
except ImportError:
    HAS_OPTIMIZED_DATA = False

try:
    from gui.dialogs.client_dialog import ClientDetailsDialog
    HAS_CLIENT_DIALOG = True
except ImportError:
    HAS_CLIENT_DIALOG = False


class ClientsPageEmbedded(QWidget):
    """
    Página de clientes embebida en PyQt5.
    
    Usa el optimizador de datos para búsquedas ultra-rápidas.
    Si C# está disponible, lo embebe; si no, usa versión Python pura.
    """
    
    patient_selected = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.current_patients = []
        self.setup_ui()
        self.load_patients()
    
    def setup_ui(self):
        """Configura la interfaz de usuarios."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("Gestión de Clientes/Pacientes")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Barra de búsqueda
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre o DNI...")
        self.search_input.setMinimumHeight(35)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_input)
        
        refresh_btn = QPushButton("Actualizar")
        refresh_btn.setMaximumWidth(120)
        refresh_btn.clicked.connect(self.load_patients)
        search_layout.addWidget(refresh_btn)
        
        layout.addLayout(search_layout)
        
        # Tabla de pacientes
        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(3)
        self.patients_table.setHorizontalHeaderLabels(["DNI", "Nombre", "Email"])
        self.patients_table.horizontalHeader().setStretchLastSection(True)
        self.patients_table.setMinimumHeight(400)
        self.patients_table.itemClicked.connect(self.on_patient_selected)
        layout.addWidget(self.patients_table)
        
        # Estadísticas
        self.stats_label = QLabel("Cargando datos...")
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.stats_label)
        
        layout.addStretch()
    
    def load_patients(self):
        """Carga la lista de pacientes desde la base de datos optimizada."""
        try:
            if not HAS_OPTIMIZED_DATA:
                QMessageBox.warning(self, "Error", "Módulo de datos no disponible")
                return
            
            # Cargar con optimizador
            start_time = time.time()
            self.current_patients = load_json_data("patients.json", [])
            elapsed = (time.time() - start_time) * 1000
            
            # Mostrar en tabla
            self.update_patients_table(self.current_patients)
            
            # Actualizar estadísticas
            if self.current_patients:
                self.stats_label.setText(
                    f"Total: {len(self.current_patients)} pacientes | "
                    f"Tiempo carga: {elapsed:.2f}ms"
                )
            else:
                self.stats_label.setText("No hay pacientes registrados")
        
        except Exception as e:
            self.stats_label.setText(f"Error cargando datos: {str(e)}")
    
    def on_search_text_changed(self, text):
        """Realiza búsqueda en tiempo real."""
        if not text.strip():
            # Si está vacío, mostrar todos
            self.update_patients_table(self.current_patients)
            return
        
        if not HAS_OPTIMIZED_DATA:
            return
        
        try:
            # Búsqueda ultra-rápida con C++
            start_time = time.time()
            success, results = search_patients(text)
            elapsed = (time.time() - start_time) * 1000
            
            if success:
                self.update_patients_table(results)
                self.stats_label.setText(
                    f"Encontrados: {len(results)} | "
                    f"Tiempo búsqueda: {elapsed:.2f}ms"
                )
            else:
                self.stats_label.setText("Error en búsqueda")
        
        except Exception as e:
            self.stats_label.setText(f"Error: {str(e)}")
    
    def update_patients_table(self, patients):
        """Actualiza la tabla con los pacientes."""
        self.patients_table.setRowCount(0)
        
        for patient in patients:
            row = self.patients_table.rowCount()
            self.patients_table.insertRow(row)
            
            # DNI
            dni_item = QTableWidgetItem(str(patient.get("dni", "")))
            self.patients_table.setItem(row, 0, dni_item)
            
            # Nombre
            nombre = f"{patient.get('nombre', '')} {patient.get('apellido', '')}".strip()
            nombre_item = QTableWidgetItem(nombre)
            self.patients_table.setItem(row, 1, nombre_item)
            
            # Email
            email_item = QTableWidgetItem(patient.get("email", ""))
            self.patients_table.setItem(row, 2, email_item)
            
            # Guardar referencia al paciente
            self.patients_table.item(row, 0).patient_data = patient
    
    def on_patient_selected(self, item):
        """Maneja cuando se selecciona un paciente."""
        row = item.row()
        patient_data = self.patients_table.item(row, 0).patient_data
        self.patient_selected.emit(patient_data)


class ClientsPage(QWidget):
    """
    Página de gestión de clientes en Python puro.
    Permite visualizar, buscar y editar clientes.
    Doble clic abre ventana de detalles similar a pacientes.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        self.setContentsMargins(0, 0, 0, 0)
        self.setup_ui()
        self.update_clients_table()
    
    def setup_ui(self):
        """Configura la interfaz de gestión de clientes."""
        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView
        from PyQt5.QtCore import Qt
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Tabla de clientes
        self.tree_clientes = QTableWidget()
        self.tree_clientes.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                font-size: 12px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
        self.tree_clientes.setColumnCount(3)
        self.tree_clientes.setHorizontalHeaderLabels(["DNI/RUC", "Nombre", "Correo"])
        self.tree_clientes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_clientes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_clientes.verticalHeader().setDefaultSectionSize(30)
        self.tree_clientes.verticalHeader().setVisible(False)
        self.tree_clientes.setWordWrap(True)
        # Conectar doble clic para abrir detalles
        self.tree_clientes.doubleClicked.connect(self.abrir_detalles_cliente_con_doble_clic)
        
        # Configurar columnas
        self.tree_clientes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tree_clientes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree_clientes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        self.tree_clientes.setColumnWidth(0, 100)
        self.tree_clientes.setColumnWidth(1, 200)
        self.tree_clientes.setColumnWidth(2, 200)
        
        main_layout.addWidget(self.tree_clientes)
    
    def abrir_detalles_cliente_con_doble_clic(self):
        """Abre ventana de detalles al hacer doble clic en una fila."""
        selected_rows = self.tree_clientes.selectedItems()
        if not selected_rows:
            return
        row_index = selected_rows[0].row()
        dni_ruc = self.tree_clientes.item(row_index, 0).text()
        self.abrir_detalles_cliente(dni_ruc)
    
    def abrir_detalles_cliente(self, dni_ruc):
        """Abre un diálogo con los detalles del cliente."""
        from utils.file_handler import cargar_clientes
        
        username = getattr(self.parent_app, 'username', self.username)
        clientes = cargar_clientes(username)
        cliente_data = next((c for c in clientes if c.get('dni_ruc') == dni_ruc or c.get('dni') == dni_ruc), None)
        
        if cliente_data:
            # Crear diálogo de detalles
            dialog = ClientDetailsDialog(cliente_data, self.parent_app)
            dialog.exec_()
            self.update_clients_table()
        else:
            QMessageBox.warning(self, "Error", "No se encontraron los datos del cliente.")
    
    def update_clients_table(self):
        """Actualiza la tabla con los clientes cargados."""
        from utils.file_handler import cargar_clientes
        
        self.tree_clientes.setRowCount(0)
        username = getattr(self.parent_app, 'username', self.username)
        
        if not username:
            return
        
        clientes = cargar_clientes(username)
        
        for i, cliente in enumerate(clientes):
            self.tree_clientes.insertRow(i)
            
            dni_ruc = cliente.get('dni_ruc') or cliente.get('dni', '')
            nombre = cliente.get('nombre', '')
            correo = cliente.get('correo', '')
            
            self.tree_clientes.setItem(i, 0, QTableWidgetItem(str(dni_ruc)))
            self.tree_clientes.setItem(i, 1, QTableWidgetItem(str(nombre)))
            self.tree_clientes.setItem(i, 2, QTableWidgetItem(str(correo)))
