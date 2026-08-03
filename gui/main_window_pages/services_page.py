import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QLineEdit, QPushButton,
    QListWidget, QHBoxLayout, QMessageBox, QFormLayout, QAbstractItemView
)
from PyQt5.QtCore import Qt

# Importaciones para el entorno de desarrollo y empaquetado
from utils.file_handler import cargar_servicios, guardar_servicios

class ServicesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainContent")
        self.parent_app = parent
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = parent.username
        self.setup_ui()
        self.setup_ui()

    def setup_ui(self):
        page = self
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_label = QLabel("<h1>Gestión de Servicios</h1>")
        title_label.setObjectName("pageTitle")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        services_group = QGroupBox("Agregar Nuevo Servicio")
        services_layout = QVBoxLayout(services_group)

        form_layout = QFormLayout()
        self.entry_servicio = QLineEdit()
        self.entry_servicio.setPlaceholderText("Nombre del nuevo servicio")
        btn_agregar_servicio = QPushButton("Agregar")
        btn_agregar_servicio.setObjectName("primaryButton")
        btn_agregar_servicio.clicked.connect(self.agregar_servicio)
        
        form_layout.addRow(self.entry_servicio, btn_agregar_servicio)
        services_layout.addLayout(form_layout)

        self.services_list = QListWidget()
        self.services_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        services_layout.addWidget(self.services_list)
        
        btn_eliminar_servicio = QPushButton("Eliminar Seleccionado")
        btn_eliminar_servicio.setObjectName("dangerButton")
        btn_eliminar_servicio.clicked.connect(self.eliminar_servicio)
        services_layout.addWidget(btn_eliminar_servicio)
        
        layout.addWidget(services_group)
        layout.addStretch()

        self.update_services_list()

    def agregar_servicio(self):
        nombre = self.entry_servicio.text().strip()
        if not nombre:
            QMessageBox.critical(self, "Error", "El nombre del servicio no puede estar vacío.")
            return

        servicios = cargar_servicios(self.username)
        if nombre in servicios:
            QMessageBox.critical(self, "Error", "Este servicio ya existe.")
            return
        
        servicios.append(nombre)
        guardar_servicios(self.username, servicios)
        self.update_services_list()
        self.entry_servicio.clear()
        QMessageBox.information(self, "Éxito", "Servicio agregado correctamente.")

    def eliminar_servicio(self):
        selected_items = self.services_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Advertencia", "Seleccione un servicio para eliminar.")
            return

        servicio_a_eliminar = selected_items[0].text()
        
        servicios = cargar_servicios(self.username)
        servicios.remove(servicio_a_eliminar)
        guardar_servicios(self.username, servicios)
        self.update_services_list()
        QMessageBox.information(self, "Éxito", "Servicio eliminado correctamente.")
    
    def update_services_list(self):
        self.services_list.clear()
        servicios = cargar_servicios(self.username)
        self.services_list.addItems(servicios)