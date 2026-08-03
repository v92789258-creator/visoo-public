"""
Diálogo para seleccionar pacientes con búsqueda avanzada
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, 
    QListWidgetItem, QPushButton, QLabel, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

class PacienteSelectorDialog(QDialog):
    """Diálogo profesional para seleccionar pacientes"""
    
    paciente_selected = pyqtSignal(str, str)  # dni, nombre completo
    
    def __init__(self, parent=None, username: str = "default", pacientes: list = None):
        super().__init__(parent)
        self.username = username
        self.pacientes = pacientes or []
        self.selected_dni = None
        self.selected_nombre = None
        
        self.setModal(True)
        self.setWindowTitle("Seleccionar Paciente")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 12px;
                color: #111111;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #000000;
            }
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #F3F4F6;
            }
            QListWidget::item:hover {
                background-color: #FAFAFA;
            }
            QListWidget::item:selected {
                background-color: #000000;
                color: white;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
        """)
        
        self.init_ui()
        self.buscar_lista.setFocus()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Header
        title = QLabel("Seleccionar Paciente")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #111111;")
        layout.addWidget(title)
        
        # Buscador
        self.buscar_lista = QLineEdit()
        self.buscar_lista.setPlaceholderText("Buscar por nombre, DNI o email...")
        self.buscar_lista.textChanged.connect(self.filtrar_pacientes)
        layout.addWidget(self.buscar_lista)
        
        # Lista de pacientes
        self.lista_pacientes = QListWidget()
        self.lista_pacientes.itemDoubleClicked.connect(self.seleccionar_paciente)
        self.lista_pacientes.itemClicked.connect(self.actualizar_seleccion)
        layout.addWidget(self.lista_pacientes)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #111111;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 10px 30px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #FAFAFA; }
        """)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_seleccionar = QPushButton("Seleccionar")
        btn_seleccionar.setStyleSheet("""
            QPushButton {
                background-color: #000000;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 30px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #333333; }
        """)
        btn_seleccionar.clicked.connect(self.confirmar_seleccion)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_seleccionar)
        layout.addLayout(btn_layout)
        
        # Cargar pacientes
        self.cargar_todos_pacientes()
    
    def cargar_todos_pacientes(self):
        """Carga todos los pacientes en la lista"""
        self.lista_pacientes.clear()
        
        if not self.pacientes:
            item = QListWidgetItem("No hay pacientes disponibles")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self.lista_pacientes.addItem(item)
            return
        
        for paciente in sorted(self.pacientes, key=lambda p: p.get('nombre', '')):
            dni = paciente.get('dni', '')
            nombre = paciente.get('nombre', '')
            email = paciente.get('email', '')
            telefono = paciente.get('telefono', '')
            
            # Formato: "Nombre (DNI)" con datos completos en tooltip
            display_text = f"{nombre} ({dni})"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, {'dni': dni, 'nombre': nombre, 'email': email, 'telefono': telefono})
            
            # Tooltip con información completa
            tooltip = f"DNI: {dni}\nNombre: {nombre}"
            if email:
                tooltip += f"\nEmail: {email}"
            if telefono:
                tooltip += f"\nTeléfono: {telefono}"
            item.setToolTip(tooltip)
            
            self.lista_pacientes.addItem(item)
    
    def filtrar_pacientes(self, texto):
        """Filtra la lista de pacientes según el texto ingresado"""
        texto_lower = texto.lower()
        
        for i in range(self.lista_pacientes.count()):
            item = self.lista_pacientes.item(i)
            data = item.data(Qt.UserRole)
            
            if not data:
                continue
            
            # Buscar en DNI, nombre, email
            dni = data.get('dni', '').lower()
            nombre = data.get('nombre', '').lower()
            email = data.get('email', '').lower()
            
            coincide = (
                texto_lower in dni or 
                texto_lower in nombre or 
                texto_lower in email
            )
            
            item.setHidden(not coincide)
    
    def actualizar_seleccion(self, item):
        """Guarda la selección actual"""
        data = item.data(Qt.UserRole)
        if data:
            self.selected_dni = data.get('dni')
            self.selected_nombre = data.get('nombre')
    
    def seleccionar_paciente(self, item):
        """Selecciona un paciente al hacer doble click"""
        self.actualizar_seleccion(item)
        self.confirmar_seleccion()
    
    def confirmar_seleccion(self):
        """Confirma la selección y cierra el diálogo"""
        if not self.selected_dni:
            return
        
        self.paciente_selected.emit(self.selected_dni, self.selected_nombre)
        self.accept()
