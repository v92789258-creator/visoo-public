"""Set the new UI layout with vertical toolbar replacing side menu."""

from PyQt5 import QtWidgets, QtCore
import os
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDialog, QLineEdit, QMessageBox, QDockWidget, QTabWidget,
    QApplication, QTextBrowser, QToolBar, QSizePolicy
)
from PyQt5.QtCore import Qt

def update_main_window(window):
    # Create main horizontal container for toolbar + content
    main_container = QHBoxLayout()
    main_container.setContentsMargins(0, 0, 0, 0)
    main_container.setSpacing(0)

    # Remove stacked widget from main layout
    window.stacked_widget.setParent(None)
    
    # Create and add vertical toolbar
    toolbar = create_side_toolbar(window)
    main_container.addWidget(toolbar)

    # Add stacked widget back in horizontal container
    main_container.addWidget(window.stacked_widget)
    
    # Add horizontal container to main layout
    window.main_layout.addLayout(main_container)

def create_side_toolbar(window):
    """Create vertical toolbar with navigation icons."""
    toolbar = QToolBar()
    toolbar.setOrientation(Qt.Vertical)
    toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
    toolbar.setIconSize(QtCore.QSize(32, 32))
    toolbar.setMovable(False)
    toolbar.setFixedWidth(60)  # Ancho fijo para el menú lateral
    toolbar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)  # Altura flexible
    
    # Style the toolbar
    toolbar.setStyleSheet("""
        QToolBar {
            background: #f8f9fa;
            border-right: 1px solid #dee2e6;
            padding: 8px 4px;
            spacing: 4px;
        }
        QToolButton {
            border: none;
            border-radius: 6px;
            padding: 8px;
            margin: 2px 0px;
            background: transparent;
        }
        /* Disable hover for unchecked buttons */
        QToolButton:hover {
            background: transparent;
        }
        QToolButton:pressed {
            background: #dee2e6;
        }
        /* Styling for the active (checked) button */
        QToolButton:checked {
            background: #e3f2fd;
            border: 1px solid #90caf9;
        }
        QToolButton:checked:hover {
            /* Slightly stronger hover only for the active button */
            background: #d0ecff;
        }
    """)

    # Add navigation buttons with icons
    style = QApplication.style()
    # Determine icons directory relative to this file
    base_dir = os.path.dirname(__file__)
    icons_dir = os.path.join(base_dir, "icons")
    
    # Create an exclusive action group so only one action is checked at a time
    action_group = QtWidgets.QActionGroup(toolbar)
    action_group.setExclusive(True)

    # Home
    act_home = toolbar.addAction(QIcon(os.path.join(icons_dir, "home.svg")), "Inicio")
    act_home.setToolTip("Inicio")
    act_home.triggered.connect(lambda: window.mostrar_frame(0))
    act_home.setCheckable(True)
    action_group.addAction(act_home)
    
    # Clients
    act_clients = toolbar.addAction(QIcon(os.path.join(icons_dir, "clients.svg")), "Clientes")
    act_clients.setToolTip("Gestión de Clientes")
    act_clients.triggered.connect(lambda: window.mostrar_frame(9))
    act_clients.setCheckable(True)
    action_group.addAction(act_clients)
    
    # Create Patient
    act_create_patient = toolbar.addAction(QIcon(os.path.join(icons_dir, "new_patient.svg")), "Crear Paciente")
    act_create_patient.setToolTip("Crear Nuevo Paciente")
    act_create_patient.triggered.connect(lambda: window.mostrar_frame(2))
    act_create_patient.setCheckable(True)
    action_group.addAction(act_create_patient)
    
    # Patient History
    act_patients = toolbar.addAction(QIcon(os.path.join(icons_dir, "history.svg")), "Historial")
    act_patients.setToolTip("Historial de Pacientes")
    act_patients.triggered.connect(lambda: window.mostrar_frame(1))
    act_patients.setCheckable(True)
    action_group.addAction(act_patients)
    
    toolbar.addSeparator()
    
    # Inventory
    act_inventory = toolbar.addAction(QIcon(os.path.join(icons_dir, "inventory.svg")), "Inventario")
    act_inventory.setToolTip("Gestión de Inventario")
    act_inventory.triggered.connect(lambda: window.mostrar_frame(3))
    act_inventory.setCheckable(True)
    action_group.addAction(act_inventory)
    
    # Sales
    act_sales = toolbar.addAction(QIcon(os.path.join(icons_dir, "sales.svg")), "Ventas")
    act_sales.setToolTip("Registro de Ventas")
    act_sales.triggered.connect(lambda: window.mostrar_frame(4))
    act_sales.setCheckable(True)
    action_group.addAction(act_sales)
    
    toolbar.addSeparator()

    # Calendario de Citas
    act_calendar = toolbar.addAction(QIcon(os.path.join(icons_dir, "calendar.svg")), "Calendario")
    act_calendar.setToolTip("Calendario de Citas")
    act_calendar.triggered.connect(lambda: window.mostrar_frame(6))
    act_calendar.setCheckable(True)
    action_group.addAction(act_calendar)
    
    # Historial de Citas
    act_appointments_history = toolbar.addAction(QIcon(os.path.join(icons_dir, "appointments_history.svg")), "Historial")
    act_appointments_history.setToolTip("Historial de Citas")
    act_appointments_history.triggered.connect(lambda: window.mostrar_frame(7))
    act_appointments_history.setCheckable(True)
    action_group.addAction(act_appointments_history)
    
    toolbar.addSeparator()
    
    # Configuration
    act_config = toolbar.addAction(QIcon(os.path.join(icons_dir, "config.svg")), "Configuración")
    act_config.setToolTip("Configuración")
    act_config.triggered.connect(lambda: window.mostrar_frame(10))
    act_config.setCheckable(True)
    action_group.addAction(act_config)
    # Set a default checked action (home) so there's a visible active tab at start
    act_home.setChecked(True)

    return toolbar