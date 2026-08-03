import os
import datetime
import unicodedata
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QHeaderView,
    QGroupBox, QGridLayout, QLineEdit, QAbstractItemView, QDateEdit,
    QPushButton, QDialog, QMessageBox, QHBoxLayout, QTableWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt, QDate

from gui.dialogs.patient_dialog import EditPatientDialog, PatientDetailsDialog
from utils.file_handler import cargar_pacientes, guardar_pacientes

class PatientsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.parent_app = parent
        self.username = getattr(parent, 'username', None)
        self.setContentsMargins(0, 0, 0, 0)
        self.setup_ui()
        self.update_patients_table()
        
    def _resolve_username(self):
        """Resolver el username del contexto."""
        try:
            if getattr(self.parent_app, 'username', None):
                return getattr(self.parent_app, 'username')
        except Exception:
            pass
        return getattr(self, 'username', None)

    def setup_ui(self):
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Tabla de pacientes
        self.tree_pacientes = QTableWidget()
        self.tree_pacientes.setStyleSheet("""
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
        self.tree_pacientes.setColumnCount(4)
        self.tree_pacientes.setHorizontalHeaderLabels(["DNI", "Nombre", "Edad", "Acciones"])
        self.tree_pacientes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_pacientes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_pacientes.verticalHeader().setDefaultSectionSize(30)
        self.tree_pacientes.verticalHeader().setVisible(False)
        self.tree_pacientes.setWordWrap(True)
        self.tree_pacientes.doubleClicked.connect(self.abrir_detalles_paciente_con_doble_clic)
        
        # Configurar columnas
        self.tree_pacientes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # DNI
        self.tree_pacientes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nombre
        self.tree_pacientes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Edad
        self.tree_pacientes.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Acciones
        
        self.tree_pacientes.setColumnWidth(0, 80)   # DNI
        self.tree_pacientes.setColumnWidth(2, 60)   # Edad
        self.tree_pacientes.setColumnWidth(3, 140)  # Acciones
        
        main_layout.addWidget(self.tree_pacientes)

    def abrir_detalles_paciente_con_doble_clic(self):
        selected_rows = self.tree_pacientes.selectedItems()
        if not selected_rows:
            return
        row_index = selected_rows[0].row()
        dni = self.tree_pacientes.item(row_index, 0).text()
        self.abrir_detalles_paciente(dni)

    def abrir_detalles_paciente(self, dni):
        username = getattr(self.parent_app, 'username', self.username)
        pacientes = cargar_pacientes(username)
        paciente_data = next((p for p in pacientes if p.get('dni') == dni), None)
        if paciente_data:
            dialog = PatientDetailsDialog(paciente_data, self.parent_app)
            dialog.exec_()
            self.update_patients_table()
        else:
            QMessageBox.warning(self, "Error", "No se encontraron los datos del paciente.")

    def abrir_edicion_paciente(self, dni):
        username = getattr(self.parent_app, 'username', self.username)
        pacientes = cargar_pacientes(username)
        paciente_data = next((p for p in pacientes if p.get('dni') == dni), None)
        if paciente_data:
            dialog = EditPatientDialog(paciente_data, self.parent_app)
            if dialog.exec_() == QDialog.Accepted:
                guardar_pacientes(username, pacientes)
                self.update_patients_table()
                QMessageBox.information(self, "Éxito", "Paciente actualizado correctamente.")
        else:
            QMessageBox.warning(self, "Error", "No se encontraron los datos del paciente.")

    def update_patients_table(self):
        self.tree_pacientes.setRowCount(0)
        username = self._resolve_username()
        datos = cargar_pacientes(username) if username else []
        
        for i, fila in enumerate(datos):
            self.tree_pacientes.insertRow(i)
            self.tree_pacientes.setItem(i, 0, QTableWidgetItem(str(fila.get('dni', ''))))
            self.tree_pacientes.setItem(i, 1, QTableWidgetItem(str(fila.get('nombre', ''))))
            self.tree_pacientes.setItem(i, 2, QTableWidgetItem(str(fila.get('edad', ''))))
            
            # Botones de acción
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(4)
            
            btn_ver = QPushButton("Ver")
            btn_ver.setObjectName("primaryButton")
            btn_ver.setFixedWidth(60)
            btn_ver.clicked.connect(lambda _, d=fila.get('dni'): self.abrir_detalles_paciente(d))
            
            btn_editar = QPushButton("Editar")
            btn_editar.setFixedWidth(60)
            btn_editar.clicked.connect(lambda _, d=fila.get('dni'): self.abrir_edicion_paciente(d))
            
            action_layout.addWidget(btn_ver)
            action_layout.addWidget(btn_editar)
            self.tree_pacientes.setCellWidget(i, 3, action_widget)

    def buscar_pacientes(self):
        username = self._resolve_username()
        pacientes = cargar_pacientes(username) if username else []
        texto_busqueda = self.side_search_entry.text().strip().lower()
        
        def _normalize(text: str) -> str:
            if not text:
                return ""
            try:
                t = str(text)
                t = t.strip().lower()
                t = unicodedata.normalize('NFKD', t)
                t = ''.join(ch for ch in t if not unicodedata.combining(ch))
                t = ' '.join(t.split())
                return t
            except Exception:
                return str(text).strip().lower()

        norm_search = _normalize(texto_busqueda)
        resultados = []

        for paciente in pacientes:
            nombre = str(paciente.get('nombre', ''))
            dni = str(paciente.get('dni', ''))
            norm_nombre = _normalize(nombre)
            norm_dni = dni.strip()
            
            if not texto_busqueda:
                resultados.append(paciente)
                continue

            if texto_busqueda.isdigit() and texto_busqueda in norm_dni:
                resultados.append(paciente)
                continue
                
            tokens = norm_search.split()
            if all(tok in norm_nombre for tok in tokens):
                resultados.append(paciente)

        self.update_table_with_data(resultados)

    def update_table_with_data(self, datos):
        self.tree_clientes.setRowCount(0)
        for i, fila in enumerate(datos):
            self.tree_clientes.insertRow(i)
            self.tree_clientes.setItem(i, 0, QTableWidgetItem(str(fila.get('dni', ''))))
            self.tree_clientes.setItem(i, 1, QTableWidgetItem(str(fila.get('nombre', ''))))
            self.tree_clientes.setItem(i, 2, QTableWidgetItem(str(fila.get('edad', ''))))
            
            # Botones de acción
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(4)
            
            btn_ver = QPushButton("Ver")
            btn_ver.setObjectName("primaryButton")
            btn_ver.setFixedWidth(60)
            btn_ver.clicked.connect(lambda _, d=fila.get('dni'): self.abrir_detalles_paciente(d))
            
            btn_editar = QPushButton("Editar")
            btn_editar.setFixedWidth(60)
            btn_editar.clicked.connect(lambda _, d=fila.get('dni'): self.abrir_edicion_paciente(d))
            
            action_layout.addWidget(btn_ver)
            action_layout.addWidget(btn_editar)
            self.tree_clientes.setCellWidget(i, 3, action_widget)