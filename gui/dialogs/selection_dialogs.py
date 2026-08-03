import sys
import os
import datetime
from functools import partial
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QHeaderView, QAbstractItemView,
    QDialogButtonBox, QHBoxLayout, QLineEdit, QLabel, QMessageBox, QWidget,
    QScrollArea, QGridLayout, QGroupBox, QSpinBox, QTableWidgetItem, QPushButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Importaciones absolutas
from utils.data_cache_manager import get_global_cache
from utils.file_handler import guardar_clientes


class PatientClientDataLoader(QThread):
    loaded = pyqtSignal(list, list)
    failed = pyqtSignal(str)

    def __init__(self, username):
        super().__init__()
        self.username = username

    def run(self):
        try:
            cache = get_global_cache()
            pacientes = cache.get_pacientes(self.username) or []
            clientes = cache.get_clientes(self.username) or []
            self.loaded.emit(
                pacientes if isinstance(pacientes, list) else [],
                clientes if isinstance(clientes, list) else []
            )
        except Exception as e:
            self.failed.emit(str(e))

class SeleccionarPacientesDialog(QDialog):
    def __init__(self, parent=None, username=None, clientes_mode=False):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Paciente o Cliente")
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowCloseButtonHint)
        self.setGeometry(100, 100, 700, 580)
        self.username = username
        self.parent_app = parent
        self.selected_dni = None
        self.selected_nombre = None
        self.current_view = "pacientes"  # Track which section is visible
        self.clientes_mode = clientes_mode
        self._data_loader = None
        self.all_pacientes = []
        self.all_clientes = []

        # Aplicar estilo minimalista
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLineEdit {
                padding: 8px 10px;
                border: 1px solid #d0d0d0;
                border-radius: 0px;
                background: white;
                color: #1a1a1a;
                font-size: 12px;
                min-height: 24px;
            }
            QLineEdit:focus {
                border: 1px solid #333333;
                background: white;
            }
            QTableWidget {
                background: white;
                border: 1px solid #d0d0d0;
                gridline-color: #f0f0f0;
                border-radius: 0px;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1a1a1a;
            }
            QHeaderView::section {
                background: #fafafa;
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #d0d0d0;
                font-weight: 600;
                color: #1a1a1a;
                font-size: 12px;
            }
            QTableWidget::item:hover {
                background-color: #f5f5f5;
            }
            QScrollBar:vertical {
                border: none;
                background: white;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bbb;
                min-height: 30px;
                border-radius: 0px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #d0d0d0;
                border-radius: 0px;
                background: #f5f5f5;
                color: #1a1a1a;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #efefef;
                border: 1px solid #999999;
            }
            QPushButton:pressed {
                background: #e8e8e8;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Título
        title = QLabel("Seleccionar Paciente o Cliente")
        title.setStyleSheet("font-weight: 600; color: #1a1a1a; font-size: 14px; margin-bottom: 8px;")
        main_layout.addWidget(title)

        # Botones de sección
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)
        
        self.btn_pacientes = QPushButton("👤 PACIENTES")
        self.btn_pacientes.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                border: 2px solid #2a2a2a;
                background: #2a2a2a;
                color: white;
                font-weight: 600;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #1a1a1a;
            }
        """)
        self.btn_pacientes.clicked.connect(lambda: self.switch_view("pacientes"))
        buttons_layout.addWidget(self.btn_pacientes)
        
        self.btn_clientes = QPushButton("🏢 CLIENTES")
        self.btn_clientes.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                border: 1px solid #d0d0d0;
                background: #f5f5f5;
                color: #1a1a1a;
                font-weight: 500;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #efefef;
            }
        """)
        self.btn_clientes.clicked.connect(lambda: self.switch_view("clientes"))
        buttons_layout.addWidget(self.btn_clientes)
        buttons_layout.addStretch()
        
        main_layout.addLayout(buttons_layout)

        # Search bar
        search_container = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Ingrese DNI o nombre")
        self.search_entry.textChanged.connect(self.filter_patients)
        search_container.addWidget(self.search_entry)
        
        # Botón agregar cliente (solo visible cuando se seleccione "CLIENTES")
        self.btn_add_cliente = QPushButton("➕ Agregar Cliente")
        self.btn_add_cliente.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border: 1px solid #2a8659;
                background: #2a8659;
                color: white;
                font-weight: 600;
                font-size: 11px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #1f6043;
            }
        """)
        self.btn_add_cliente.clicked.connect(self.agregar_cliente_rapido)
        self.btn_add_cliente.hide()  # Oculto por defecto
        search_container.addWidget(self.btn_add_cliente)
        
        main_layout.addLayout(search_container)

        self.content_stack = QtWidgets.QStackedWidget()

        loader_widget = QWidget()
        loader_layout = QVBoxLayout(loader_widget)
        loader_layout.setContentsMargins(0, 24, 0, 24)
        loader_layout.setSpacing(10)
        loader_layout.addStretch()

        self.loader_title = QLabel("Cargando pacientes y clientes")
        self.loader_title.setAlignment(Qt.AlignCenter)
        self.loader_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #1a1a1a;")
        loader_layout.addWidget(self.loader_title)

        self.loader_status = QLabel("Preparando datos...")
        self.loader_status.setAlignment(Qt.AlignCenter)
        self.loader_status.setStyleSheet("font-size: 12px; color: #666666;")
        loader_layout.addWidget(self.loader_status)
        loader_layout.addStretch()

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Tabla
        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(3)
        self.patients_table.setHorizontalHeaderLabels(["DNI", "Nombre", "Teléfono"])
        self.patients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.patients_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.patients_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.patients_table.doubleClicked.connect(self.accept_selection)
        self.patients_table.setShowGrid(False)
        self.patients_table.verticalHeader().setDefaultSectionSize(35)
        self.patients_table.setMaximumHeight(350)
        self.patients_table.setMinimumHeight(200)
        content_layout.addWidget(self.patients_table)

        self.content_stack.addWidget(loader_widget)
        self.content_stack.addWidget(content_widget)
        self.content_stack.setCurrentIndex(0)
        main_layout.addWidget(self.content_stack)

        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #d0d0d0;
                background: #f5f5f5;
                color: #1a1a1a;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #efefef;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("OK")
        btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #333333;
                background: #2a2a2a;
                color: white;
                font-weight: 600;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #1a1a1a;
            }
        """)
        btn_ok.clicked.connect(self.accept_selection)
        
        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_ok)
        main_layout.addLayout(button_layout)

        self.search_entry.setEnabled(False)
        self.btn_pacientes.setEnabled(False)
        self.btn_clientes.setEnabled(False)
        QtCore.QTimer.singleShot(0, self._start_async_load)

    def load_patients_table(self):
        """Carga los datos sin mostrar nada aún"""
        # Mostrar la vista inicial (pacientes)
        self.show_section("pacientes")

    def _start_async_load(self):
        self._data_loader = PatientClientDataLoader(self.username)
        self._data_loader.loaded.connect(self._on_data_loaded)
        self._data_loader.failed.connect(self._on_data_failed)
        self._data_loader.finished.connect(self._on_data_finished)
        self._data_loader.start()

    def _on_data_loaded(self, pacientes, clientes):
        self.all_pacientes = pacientes if isinstance(pacientes, list) else []
        self.all_clientes = clientes if isinstance(clientes, list) else []
        self.load_patients_table()
        self.search_entry.setEnabled(True)
        self.btn_pacientes.setEnabled(True)
        self.btn_clientes.setEnabled(True)
        self.content_stack.setCurrentIndex(1)

    def _on_data_failed(self, error):
        self.loader_title.setText("No se pudieron cargar los datos")
        self.loader_status.setText(str(error))
        QMessageBox.warning(self, "Error", f"No se pudieron cargar pacientes/clientes:\n{error}")

    def _on_data_finished(self):
        self._data_loader = None
    
    def switch_view(self, view_type):
        """Cambia entre vista de pacientes y clientes"""
        self.current_view = view_type
        
        if view_type == "pacientes":
            self.btn_pacientes.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border: 2px solid #2a2a2a;
                    background: #2a2a2a;
                    color: white;
                    font-weight: 600;
                    font-size: 12px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background: #1a1a1a;
                }
            """)
            self.btn_clientes.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border: 1px solid #d0d0d0;
                    background: #f5f5f5;
                    color: #1a1a1a;
                    font-weight: 500;
                    font-size: 12px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background: #efefef;
                }
            """)
            self.btn_add_cliente.hide()  # Ocultar botón
        else:  # clientes
            self.btn_clientes.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border: 2px solid #2a2a2a;
                    background: #2a2a2a;
                    color: white;
                    font-weight: 600;
                    font-size: 12px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background: #1a1a1a;
                }
            """)
            self.btn_pacientes.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border: 1px solid #d0d0d0;
                    background: #f5f5f5;
                    color: #1a1a1a;
                    font-weight: 500;
                    font-size: 12px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background: #efefef;
                }
            """)
            self.btn_add_cliente.show()  # Mostrar botón
        
        # Limpiar búsqueda y mostrar sección
        self.search_entry.clear()
        self.show_section(view_type)
    
    def show_section(self, view_type):
        """Muestra la sección correspondiente (pacientes o clientes)"""
        self.patients_table.setRowCount(0)
        search_text = self.search_entry.text().lower()
        
        if view_type == "pacientes":
            # Filtrar pacientes
            if search_text:
                filtered = [
                    p for p in self.all_pacientes
                    if search_text in p.get('dni', '').lower() or search_text in p.get('nombre', '').lower()
                ]
            else:
                filtered = self.all_pacientes
            
            # Mostrar pacientes
            for i, p in enumerate(filtered):
                self.patients_table.insertRow(i)
                self.patients_table.setItem(i, 0, QTableWidgetItem(p.get('dni', '')))
                self.patients_table.setItem(i, 1, QTableWidgetItem(p.get('nombre', '')))
                self.patients_table.setItem(i, 2, QTableWidgetItem(p.get('telefono', '')))
        
        else:  # clientes
            # Filtrar clientes
            if search_text:
                filtered = [
                    c for c in self.all_clientes
                    if search_text in c.get('dni', '').lower() or search_text in c.get('nombre', '').lower()
                ]
            else:
                filtered = self.all_clientes
            
            # Mostrar clientes
            for i, c in enumerate(filtered):
                self.patients_table.insertRow(i)
                self.patients_table.setItem(i, 0, QTableWidgetItem(c.get('dni', '')))
                self.patients_table.setItem(i, 1, QTableWidgetItem(c.get('nombre', '')))
                self.patients_table.setItem(i, 2, QTableWidgetItem(c.get('telefono', '')))
    
    def filter_patients(self, text):
        """Filtra la sección actual mientras se mantiene visible"""
        self.show_section(self.current_view)

    def agregar_cliente_rapido(self):
        """Abre un diálogo para agregar un cliente rápidamente"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar Cliente Rápido")
        dialog.setGeometry(200, 200, 400, 280)
        dialog.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLabel {
                color: #1a1a1a;
                font-weight: 600;
                font-size: 12px;
            }
            QLineEdit {
                padding: 8px 10px;
                border: 1px solid #d0d0d0;
                border-radius: 0px;
                background: white;
                color: #1a1a1a;
                font-size: 12px;
                min-height: 24px;
            }
            QLineEdit:focus {
                border: 1px solid #333333;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Campo DNI
        label_dni = QLabel("DNI:")
        entry_dni = QLineEdit()
        entry_dni.setPlaceholderText("Ej: 12345678")
        layout.addWidget(label_dni)
        layout.addWidget(entry_dni)
        
        # Campo Nombre
        label_nombre = QLabel("Nombre:")
        entry_nombre = QLineEdit()
        entry_nombre.setPlaceholderText("Nombre del cliente")
        layout.addWidget(label_nombre)
        layout.addWidget(entry_nombre)
        
        # Campo Apellido
        label_apellido = QLabel("Apellido:")
        entry_apellido = QLineEdit()
        entry_apellido.setPlaceholderText("Apellido del cliente")
        layout.addWidget(label_apellido)
        layout.addWidget(entry_apellido)
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #d0d0d0;
                background: #f5f5f5;
                color: #1a1a1a;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #efefef;
            }
        """)
        btn_cancelar.clicked.connect(dialog.reject)
        buttons_layout.addWidget(btn_cancelar)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #2a8659;
                background: #2a8659;
                color: white;
                font-weight: 600;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #1f6043;
            }
        """)
        
        def guardar_cliente():
            dni = entry_dni.text().strip()
            nombre = entry_nombre.text().strip()
            apellido = entry_apellido.text().strip()
            
            if not dni or not nombre or not apellido:
                QMessageBox.warning(dialog, "Error", "Todos los campos son obligatorios.")
                return
            
            try:
                # Verificar si el cliente ya existe
                cache = get_global_cache()
                clientes_existentes = cache.get_clientes(self.username)
                if any(c.get('dni') == dni for c in clientes_existentes):
                    QMessageBox.warning(dialog, "Error", "Este DNI ya está registrado.")
                    return
                
                # Crear nuevo cliente
                nuevo_cliente = {
                    'dni': dni,
                    'nombre': f"{nombre} {apellido}",
                    'apellido': apellido,
                    'fecha_registro': datetime.datetime.now().strftime("%d/%m/%Y"),
                    'edad': '',
                    'genero': '',
                    'fecha_nacimiento': '',
                    'telefono': '',
                    'email': '',
                    'direccion': ''
                }
                
                # Guardar cliente
                clientes_existentes.append(nuevo_cliente)
                guardar_clientes(self.username, clientes_existentes)
                
                # Mostrar mensaje de éxito
                QMessageBox.information(
                    dialog,
                    "✓ Éxito",
                    f"Cliente {nombre} {apellido} creado correctamente"
                )
                
                # Recargar la tabla de clientes desde el archivo
                self.all_clientes = clientes_existentes
                self.show_section("clientes")
                
                # Cerrar el diálogo de agregar cliente
                dialog.accept()
                
            except Exception as e:
                QMessageBox.critical(
                    dialog,
                    "Error",
                    f"Error al guardar cliente:\n{str(e)}"
                )
        
        btn_guardar.clicked.connect(guardar_cliente)
        buttons_layout.addWidget(btn_guardar)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec_()

    def accept_selection(self):
        selected_items = self.patients_table.selectedItems()
        if selected_items:
            self.selected_dni = selected_items[0].text()
            self.selected_nombre = selected_items[1].text()
            self.accept()
        else:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un paciente o cliente.")


class SeleccionarClientesDialog(QDialog):
    def __init__(self, parent=None, username=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Cliente")
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowCloseButtonHint)
        self.setGeometry(100, 100, 500, 450)
        self.username = username
        self.parent_app = parent
        self.selected_dni = None

        # Aplicar estilo minimalista
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLineEdit {
                padding: 8px 10px;
                border: 1px solid #d0d0d0;
                border-radius: 0px;
                background: white;
                color: #1a1a1a;
                font-size: 12px;
                min-height: 24px;
            }
            QLineEdit:focus {
                border: 1px solid #333333;
                background: white;
            }
            QTableWidget {
                background: white;
                border: 1px solid #d0d0d0;
                gridline-color: #f0f0f0;
                border-radius: 0px;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #f5f5f5;
                color: #1a1a1a;
            }
            QHeaderView::section {
                background: #fafafa;
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #d0d0d0;
                font-weight: 600;
                color: #1a1a1a;
                font-size: 12px;
            }
            QTableWidget::item:hover {
                background-color: #fbfbfb;
            }
            QScrollBar:vertical {
                border: none;
                background: white;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bbb;
                min-height: 30px;
                border-radius: 0px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #d0d0d0;
                border-radius: 0px;
                background: #f5f5f5;
                color: #1a1a1a;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #efefef;
                border: 1px solid #999999;
            }
            QPushButton:pressed {
                background: #e8e8e8;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Título
        title = QLabel("Buscar por DNI o Nombre...")
        title.setStyleSheet("font-weight: 600; color: #1a1a1a; font-size: 13px; margin-bottom: 4px;")
        main_layout.addWidget(title)

        # Search bar
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Ingrese DNI o nombre del cliente")
        self.search_entry.textChanged.connect(self.filter_clients)
        main_layout.addWidget(self.search_entry)

        # Tabla
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(2)
        self.clients_table.setHorizontalHeaderLabels(["DNI", "Nombre"])
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.clients_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.clients_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.clients_table.doubleClicked.connect(self.accept_selection)
        self.clients_table.setShowGrid(False)
        self.load_clients_table()
        main_layout.addWidget(self.clients_table)

        # Botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #d0d0d0;
                background: #f5f5f5;
                color: #1a1a1a;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #efefef;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("OK")
        btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #333333;
                background: #2a2a2a;
                color: white;
                font-weight: 600;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #1a1a1a;
            }
        """)
        btn_ok.clicked.connect(self.accept_selection)
        
        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_ok)
        main_layout.addLayout(button_layout)

    def load_clients_table(self):
        self.clients_table.setRowCount(0)
        cache = get_global_cache()
        self.all_clientes = cache.get_clientes(self.username)
        for row_index, cliente in enumerate(self.all_clientes):
            self.clients_table.insertRow(row_index)
            self.clients_table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(cliente.get('dni', '')))
            self.clients_table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(cliente.get('nombre', '')))
        
    def filter_clients(self, text):
        self.clients_table.setRowCount(0)
        filtered_list = [
            c for c in self.all_clientes
            if text.lower() in c['dni'].lower() or text.lower() in c['nombre'].lower()
        ]
        
        for row_index, cliente in enumerate(filtered_list):
            self.clients_table.insertRow(row_index)
            self.clients_table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(cliente.get('dni', '')))
            self.clients_table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(cliente.get('nombre', '')))

    def accept_selection(self):
        selected_items = self.clients_table.selectedItems()
        if selected_items:
            self.selected_dni = selected_items[0].text()
            self.accept()
        else:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un cliente.")

class SeleccionarProductosDialog(QDialog):
    def __init__(self, parent=None, username=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Productos")
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowMaximizeButtonHint | QtCore.Qt.WindowCloseButtonHint)
        self.setGeometry(100, 100, 900, 700)
        self.username = username
        
        self.selected_products = []
        cache = get_global_cache()
        self.productos_inventario = cache.get_productos(self.username)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Header con título
        header_layout = QHBoxLayout()
        title_label = QLabel("Seleccionar Productos")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #212529;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Búsqueda con mejor estilo
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Buscar:")
        search_label.setStyleSheet("color: #495057; font-weight: 500;")
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Escribe el nombre del producto...")
        self.search_entry.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #0d6efd;
                background-color: #f8f9fa;
            }
        """)
        self.search_entry.textChanged.connect(self.filter_products)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_entry)
        main_layout.addLayout(search_layout)

        # Galería de productos con mejor estilo
        gallery_label = QLabel("Productos Disponibles")
        gallery_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #495057; margin-top: 8px;")
        main_layout.addWidget(gallery_label)
        
        self.product_gallery_area = QtWidgets.QScrollArea()
        self.product_gallery_area.setWidgetResizable(True)
        self.product_gallery_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9E9E9E;
            }
        """)
        self.product_gallery_widget = QtWidgets.QWidget()
        self.product_gallery_layout = QtWidgets.QGridLayout(self.product_gallery_widget)
        self.product_gallery_layout.setSpacing(12)
        self.product_gallery_layout.setContentsMargins(10, 10, 10, 10)
        self.product_gallery_area.setWidget(self.product_gallery_widget)
        main_layout.addWidget(self.product_gallery_area)
        
        self.load_product_gallery(self.productos_inventario)

        # Resumen de productos seleccionados
        selected_label = QLabel("Productos Seleccionados")
        selected_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #495057; margin-top: 12px;")
        main_layout.addWidget(selected_label)
        
        selected_group = QtWidgets.QGroupBox()
        selected_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
                padding: 12px;
            }
        """)
        selected_layout = QtWidgets.QVBoxLayout(selected_group)
        self.selected_table = QtWidgets.QTableWidget()
        self.selected_table.setColumnCount(4)
        self.selected_table.setHorizontalHeaderLabels(["Producto", "Cantidad", "Precio Unit.", "Subtotal"])
        self.selected_table.setMaximumHeight(150)
        self.selected_table.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #E0E0E0;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #E0E0E0;
                font-weight: bold;
                color: #495057;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #F0F0F0;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
            }
        """)
        self.selected_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        # Permitir edición con doble clic
        self.selected_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked | 
            QtWidgets.QAbstractItemView.EditKeyPressed | 
            QtWidgets.QAbstractItemView.AnyKeyPressed
        )
        # Conectar señal de cambio de items para validar ediciones
        self.selected_table.itemChanged.connect(self.on_table_item_changed)
        selected_layout.addWidget(self.selected_table)
        
        # Agregar campo de descuento en porcentaje
        discount_layout = QtWidgets.QHBoxLayout()
        discount_label = QLabel("Descuento en %:")
        discount_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 12px;")
        discount_layout.addWidget(discount_label)
        
        self.discount_input = QtWidgets.QLineEdit()
        self.discount_input.setText("0")
        self.discount_input.setMaximumWidth(80)
        self.discount_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #0d6efd;
            }
        """)
        discount_layout.addWidget(self.discount_input)
        discount_layout.addStretch()
        
        selected_layout.addLayout(discount_layout)
        main_layout.addWidget(selected_group)

        # Botones personalizados
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_cancel = QPushButton("✕ Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
            QPushButton:pressed {
                background-color: #4E555B;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("✓ Aceptar")
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
        """)
        btn_ok.clicked.connect(self.validate_and_accept)
        
        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_ok)
        main_layout.addLayout(button_layout)

    def load_product_gallery(self, productos):
        for i in reversed(range(self.product_gallery_layout.count())):
            widget = self.product_gallery_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        row, col = 0, 0
        for prod in productos:
            card = self.create_product_card(prod)
            self.product_gallery_layout.addWidget(card, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

    def create_product_card(self, prod):
        card = QtWidgets.QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        # Imagen del producto
        image_label = QtWidgets.QLabel()
        image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        image_label.setMinimumHeight(120)
        image_label.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        if prod.get('image_path') and os.path.exists(prod['image_path']):
            pixmap = QtGui.QPixmap(prod['image_path'])
            image_label.setPixmap(pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        else:
            image_label.setText("📷\nSin imagen")
            image_label.setStyleSheet("""
                QLabel {
                    background-color: #F5F5F5;
                    border-radius: 6px;
                    padding: 10px;
                    color: #BDBDBD;
                    font-size: 12px;
                }
            """)
        card_layout.addWidget(image_label)

        # Información del producto con indicador de stock
        try:
            stock_actual = int(prod.get('stock', 0))
        except (ValueError, TypeError):
            stock_actual = 0
        
        try:
            precio_venta = float(prod.get('venta', 0))
        except (ValueError, TypeError):
            precio_venta = 0.0
        
        stock_color = "#28a745" if stock_actual > 0 else "#dc3545"
        info_text = f"<b>{prod['nombre'][:25]}{'...' if len(prod['nombre']) > 25 else ''}</b><br>"
        info_text += f"<span style='color: #666; font-size: 12px;'>Marca: {prod.get('marca', 'N/A')[:15]}</span><br>"
        info_text += f"<span style='font-weight: bold; color: #0d6efd;'>S/{precio_venta:.2f}</span><br>"
        info_text += f"<span style='color: {stock_color}; font-weight: bold;'>Stock: {stock_actual}</span>"
        
        info_label = QtWidgets.QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #333; font-size: 11px;")
        card_layout.addWidget(info_label)

        # Si hay stock, mostrar selector de cantidad y botón agregar
        if stock_actual > 0:
            # Selector de cantidad
            add_layout = QtWidgets.QHBoxLayout()
            add_layout.setContentsMargins(0, 0, 0, 0)
            add_layout.setSpacing(6)
            
            qty_label = QtWidgets.QLabel("Cant:")
            qty_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 11px;")
            add_layout.addWidget(qty_label)
            
            spin_box = QtWidgets.QSpinBox()
            spin_box.setStyleSheet("""
                QSpinBox {
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 11px;
                    min-width: 50px;
                }
                QSpinBox:focus {
                    border: 1px solid #0d6efd;
                }
            """)
            spin_box.setMinimum(1)
            spin_box.setMaximum(stock_actual)
            spin_box.setValue(1)
            
            add_layout.addWidget(spin_box)
            add_layout.addStretch()
            card_layout.addLayout(add_layout)
            
            # Botón de agregar
            btn_add = QtWidgets.QPushButton("✓ Añadir")
            btn_add.setStyleSheet("""
                QPushButton {
                    background-color: #0d6efd;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #0b5ed7;
                }
                QPushButton:pressed {
                    background-color: #0a58ca;
                }
            """)
            # Guardar referencias en el botón para evitar issues con lambda y garbage collection
            btn_add._prod = prod
            btn_add._spin_box = spin_box
            btn_add.clicked.connect(self._on_add_product_clicked)
            card_layout.addWidget(btn_add)
        else:
            # Si no hay stock, mostrar opción para agregar stock
            no_stock_label = QtWidgets.QLabel("⚠️ Sin Stock")
            no_stock_label.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 12px; text-align: center;")
            card_layout.addWidget(no_stock_label)
            
            btn_add_stock = QtWidgets.QPushButton("+ Agregar Stock")
            btn_add_stock.setStyleSheet("""
                QPushButton {
                    background-color: #FFC107;
                    color: #333;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #FFB300;
                }
                QPushButton:pressed {
                    background-color: #FFA500;
                }
            """)
            btn_add_stock.clicked.connect(lambda: self.agregar_stock_desde_dialog(prod))
            card_layout.addWidget(btn_add_stock)
        
        return card

    def filter_products(self, text):
        filtered_products = [
            p for p in self.productos_inventario
            if text.lower() in p['nombre'].lower()
        ]
        self.load_product_gallery(filtered_products)
    
    def _on_add_product_clicked(self):
        """Manejador intermediario para evitar issues con lambda en PyQt5"""
        try:
            sender = self.sender()
            if sender and hasattr(sender, '_prod') and hasattr(sender, '_spin_box'):
                prod = sender._prod
                quantity = sender._spin_box.value()
                self.add_to_selected(prod, quantity)
        except Exception as e:
            import traceback
            print(f"[ERROR] Error en _on_add_product_clicked: {e}")
            traceback.print_exc()
        
    def add_to_selected(self, prod, quantity):
        try:
            # Validar que no exceda el stock disponible
            try:
                stock_disponible = int(prod.get('stock', 0))
            except (ValueError, TypeError):
                stock_disponible = 0
            
            if quantity <= 0:
                QtWidgets.QMessageBox.warning(self, "Cantidad Inválida", "Debe seleccionar al menos 1 unidad.")
                return
            
            if quantity > stock_disponible:
                QtWidgets.QMessageBox.critical(self, "Stock Insuficiente", 
                    f"El producto '{prod['nombre']}' tiene solo {stock_disponible} unidades disponibles.\n"
                    f"No se puede agregar {quantity} unidades.")
                return
            
            existing_item = next((item for item in self.selected_products if item['nombre'] == prod['nombre']), None)

            if existing_item:
                nueva_cantidad = existing_item['cantidad'] + quantity
                # Validar que la cantidad total no exceda el stock
                if nueva_cantidad > stock_disponible:
                    QtWidgets.QMessageBox.critical(self, "Stock Insuficiente",
                        f"Ya has seleccionado {existing_item['cantidad']} unidades de '{prod['nombre']}'.\n"
                        f"El stock total es solo {stock_disponible} unidades.\n"
                        f"No se puede agregar {quantity} más.")
                    return
                
                existing_item['cantidad'] = nueva_cantidad
                # Recalcular subtotal al actualizar la cantidad
                try:
                    existing_item['subtotal'] = existing_item['cantidad'] * float(prod.get('venta', 0))
                except Exception:
                    existing_item['subtotal'] = existing_item['cantidad'] * prod.get('venta', 0)
            else:
                try:
                    precio = float(prod.get('venta', 0))
                except (ValueError, TypeError):
                    precio = 0.0
                self.selected_products.append({
                    'nombre': prod['nombre'],
                    'cantidad': quantity,
                    'precio_unitario': precio,
                    'subtotal': precio * quantity
                })
            
            self.update_selected_table()
        
        except Exception as e:
            import traceback
            print(f"[ERROR] Error en add_to_selected: {e}")
            print(f"[ERROR] Producto: {prod}")
            print(f"[ERROR] Cantidad: {quantity}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"Error al agregar producto: {str(e)}")

    def update_selected_table(self):
        self.selected_table.setRowCount(len(self.selected_products))
        for row, item in enumerate(self.selected_products):
            # Columna 0: Producto (no editable)
            product_item = QtWidgets.QTableWidgetItem(item['nombre'])
            product_item.setFlags(product_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.selected_table.setItem(row, 0, product_item)
            
            # Columna 1: Cantidad (no editable)
            qty_item = QtWidgets.QTableWidgetItem(str(item['cantidad']))
            qty_item.setFlags(qty_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.selected_table.setItem(row, 1, qty_item)
            
            # Columna 2: Precio unitario (no editable)
            try:
                price_str = f"S/{float(item['precio_unitario']):.2f}"
            except Exception:
                price_str = str(item['precio_unitario'])
            price_item = QtWidgets.QTableWidgetItem(price_str)
            price_item.setFlags(price_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.selected_table.setItem(row, 2, price_item)
            
            # Columna 3: Subtotal (EDITABLE)
            try:
                subtotal_value = float(item['subtotal'])
                subtotal_str = f"{subtotal_value:.2f}"
            except Exception:
                subtotal_str = str(item['subtotal'])
            subtotal_item = QtWidgets.QTableWidgetItem(subtotal_str)
            # Permitir edición
            subtotal_item.setFlags(subtotal_item.flags() | QtCore.Qt.ItemIsEditable)
            self.selected_table.setItem(row, 3, subtotal_item)
    
    def on_table_item_changed(self, item):
        """Valida cambios en la tabla y permite edición solo del subtotal"""
        row = item.row()
        col = item.column()
        
        # Solo permitir edición en la columna de Subtotal (columna 3)
        if col != 3:
            # Si no es subtotal, revertir cambios
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            return
        
        # Validar que sea un número válido
        try:
            value = float(item.text().replace('S/', '').strip())
            # Actualizar el valor en selected_products
            if row < len(self.selected_products):
                self.selected_products[row]['subtotal'] = value
                # Mostrar el valor con formato
                item.setText(f"{value:.2f}")
        except ValueError:
            # Si no es número válido, revertir al valor anterior
            if row < len(self.selected_products):
                try:
                    prev_value = float(self.selected_products[row]['subtotal'])
                    item.setText(f"{prev_value:.2f}")
                except:
                    item.setText("0.00")
    
    def agregar_stock_desde_dialog(self, prod):
        """Abre un diálogo para agregar stock al producto."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"Agregar Stock - {prod['nombre']}")
        dialog.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowCloseButtonHint)
        dialog.setMinimumWidth(350)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Información
        info_label = QtWidgets.QLabel(f"<b>Producto:</b> {prod['nombre']}")
        layout.addWidget(info_label)
        
        try:
            display_stock = int(prod.get('stock', 0))
        except (ValueError, TypeError):
            display_stock = 0
        current_stock_label = QtWidgets.QLabel(f"<b>Stock actual:</b> {display_stock} unidades")
        current_stock_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        layout.addWidget(current_stock_label)
        
        # Input para cantidad
        qty_layout = QtWidgets.QHBoxLayout()
        qty_label = QtWidgets.QLabel("¿Cuántas unidades deseas agregar?")
        spinbox = QtWidgets.QSpinBox()
        spinbox.setMinimum(1)
        spinbox.setMaximum(10000)
        spinbox.setValue(1)
        qty_layout.addWidget(qty_label)
        qty_layout.addStretch()
        qty_layout.addWidget(spinbox)
        layout.addLayout(qty_layout)
        
        # Total
        try:
            current_stock = int(prod.get('stock', 0))
        except (ValueError, TypeError):
            current_stock = 0
        total_label = QtWidgets.QLabel(f"<b>Nuevo stock:</b> {current_stock + 1} unidades")
        layout.addWidget(total_label)
        
        def update_total(value):
            new_total = current_stock + value
            total_label.setText(f"<b>Nuevo stock:</b> {new_total} unidades")
        
        spinbox.valueChanged.connect(update_total)
        
        # Botones
        button_layout = QtWidgets.QHBoxLayout()
        btn_cancel = QtWidgets.QPushButton("✕ Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        btn_cancel.clicked.connect(dialog.reject)
        
        btn_ok = QtWidgets.QPushButton("✓ Agregar")
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        btn_ok.clicked.connect(dialog.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_ok)
        layout.addLayout(button_layout)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            cantidad_agregar = spinbox.value()
            # Actualizar el producto
            cache = get_global_cache()
            prod['stock'] += cantidad_agregar
            
            # Guardar cambios
            productos = cache.get_productos(self.username)
            prod_index = next((i for i, p in enumerate(productos) if p['nombre'] == prod['nombre']), -1)
            if prod_index != -1:
                productos[prod_index] = prod
                cache.update_productos(self.username, productos)
                
                QtWidgets.QMessageBox.information(dialog, "Éxito", 
                    f"Se agregaron {cantidad_agregar} unidades a '{prod['nombre']}'.")
                
                # Recargar la galería
                self.productos_inventario = cache.get_productos(self.username)
                self.load_product_gallery(self.productos_inventario)

    def validate_and_accept(self):
        """Valida que haya productos seleccionados antes de aceptar el diálogo."""
        if not self.selected_products:
            QtWidgets.QMessageBox.warning(self, "Sin Productos", 
                "Por favor selecciona al menos un producto antes de continuar.")
            return
        self.accept()
