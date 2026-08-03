"""
helpers_page.py - Página de Gestión de Ayudantes con Permisos Configurables
"""

import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout, QCheckBox,
    QGroupBox, QMessageBox, QInputDialog, QHeaderView, QFrame,
    QScrollArea, QSpacerItem, QSizePolicy, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QColor, QFont, QBrush

from utils.helpers_manager import (
    cargar_ayudantes, guardar_ayudantes, crear_ayudante, editar_ayudante,
    eliminar_ayudante, PERMISOS_DISPONIBLES, verify_password, hash_password
)


# ============================================================
# DIÁLOGO PARA CREAR/EDITAR AYUDANTE
# ============================================================

class AyudanteDialog(QDialog):
    """Diálogo para crear o editar un ayudante."""
    
    def __init__(self, parent=None, ayudante=None):
        super().__init__(parent)
        self.ayudante = ayudante
        self.permisos_widgets = {}  # Almacenaremos los widgets de permisos granulares
        self.setWindowTitle('Crear Ayudante' if not ayudante else 'Editar Ayudante')
        self.setGeometry(100, 100, 700, 650)
        self.setup_ui()
        
        # Si es edición, llenar con datos existentes
        if ayudante:
            self.nombre_input.setText(ayudante.get('nombre', ''))
            self.usuario_input.setText(ayudante.get('usuario', ''))
            self.contacto_input.setText(ayudante.get('contacto', ''))
            self.usuario_input.setReadOnly(True)  # No permitir cambiar usuario
            self.notas_input.setPlainText(ayudante.get('notas', ''))
            
            # Cargar permisos existentes (formato granular)
            permisos = ayudante.get('permisos', {})
            self._cargar_permisos_en_ui(permisos)
    
    def _cargar_permisos_en_ui(self, permisos: dict):
        """Carga los permisos en los widgets de la UI."""
        print(f"[DEBUG] Cargando permisos: {permisos}")
        for seccion, acciones in permisos.items():
            print(f"[DEBUG] Sección: {seccion}, acciones: {acciones}")
            if seccion in self.permisos_widgets:
                # Manejo de ambos formatos: lista o dict
                if isinstance(acciones, list):
                    for accion in acciones:
                        if accion in self.permisos_widgets[seccion]:
                            print(f"[DEBUG] Marcando {seccion}/{accion}")
                            self.permisos_widgets[seccion][accion].setChecked(True)
                elif isinstance(acciones, dict):
                    # Si es dict {accion: True/False}
                    for accion, estado in acciones.items():
                        if accion in self.permisos_widgets[seccion] and estado:
                            print(f"[DEBUG] Marcando {seccion}/{accion}")
                            self.permisos_widgets[seccion][accion].setChecked(True)
                elif isinstance(acciones, bool) and acciones:
                    # Si acciones directamente es True (permiso global)
                    for checkbox in self.permisos_widgets[seccion].values():
                        checkbox.setChecked(True)
    
    def setup_ui(self):
        """Configura la interfaz del diálogo."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # --- Formulario de datos básicos mejorado ---
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Nombre
        label_nombre = QLabel("👤 Nombre del Ayudante:")
        label_nombre.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.nombre_input = QLineEdit()
        self.nombre_input.setMinimumHeight(35)
        self.nombre_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
            }
        """)
        form_layout.addRow(label_nombre, self.nombre_input)
        
        # Usuario (login)
        label_usuario = QLabel("🔐 Usuario (login):")
        label_usuario.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.usuario_input = QLineEdit()
        self.usuario_input.setMinimumHeight(35)
        self.usuario_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
            }
        """)
        form_layout.addRow(label_usuario, self.usuario_input)

        # Contacto
        label_contacto = QLabel("Contacto:")
        label_contacto.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.contacto_input = QLineEdit()
        self.contacto_input.setMinimumHeight(35)
        self.contacto_input.setPlaceholderText("Telefono, email o referencia")
        self.contacto_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
            }
        """)
        form_layout.addRow(label_contacto, self.contacto_input)
        
        # Contraseña (solo en creación)
        if not self.ayudante:
            label_password = QLabel("🔑 Contraseña:")
            label_password.setFont(QFont("Segoe UI", 11, QFont.Bold))
            self.password_input = QLineEdit()
            self.password_input.setMinimumHeight(35)
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #e0e0e0;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 11px;
                }
                QLineEdit:focus {
                    border: 2px solid #1976D2;
                }
            """)
            form_layout.addRow(label_password, self.password_input)
            
            label_password_confirm = QLabel("🔑 Confirmar Contraseña:")
            label_password_confirm.setFont(QFont("Segoe UI", 11, QFont.Bold))
            self.password_confirm = QLineEdit()
            self.password_confirm.setMinimumHeight(35)
            self.password_confirm.setEchoMode(QLineEdit.Password)
            self.password_confirm.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #e0e0e0;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 11px;
                }
                QLineEdit:focus {
                    border: 2px solid #1976D2;
                }
            """)
            form_layout.addRow(label_password_confirm, self.password_confirm)
        else:
            label_password_info = QLabel("🔑 Contraseña:")
            label_password_info.setFont(QFont("Segoe UI", 11, QFont.Bold))
            self.label_password_change = QLabel(
                "Para cambiar la contraseña, contacte al administrador"
            )
            self.label_password_change.setStyleSheet("color: #FF9800; font-style: italic; font-size: 11px;")
            form_layout.addRow(label_password_info, self.label_password_change)
        
        # Notas
        label_notas = QLabel("📝 Notas:")
        label_notas.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.notas_input = __import__('PyQt5.QtWidgets', fromlist=['QPlainTextEdit']).QPlainTextEdit()
        self.notas_input.setFixedHeight(70)
        self.notas_input.setStyleSheet("""
            QPlainTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
            }
            QPlainTextEdit:focus {
                border: 2px solid #1976D2;
            }
        """)
        form_layout.addRow(label_notas, self.notas_input)
        
        layout.addLayout(form_layout)
        
        # --- PESTAÑAS DE PERMISOS (Tab Widget) ---
        from PyQt5.QtWidgets import QTabWidget
        self.tabs_permisos = QTabWidget()
        self.tabs_permisos.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CCC;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #F5F5F5;
                padding: 8px 20px;
                border: 1px solid #CCC;
                border-bottom: none;
                border-radius: 5px 5px 0px 0px;
            }
            QTabBar::tab:selected {
                background-color: #1976D2;
                color: white;
                border: 1px solid #1565C0;
            }
            QTabBar::tab:hover:!selected {
                background-color: #E8E8E8;
            }
        """)
        
        # Crear una pestaña para cada sección de permisos
        for seccion, config in PERMISOS_DISPONIBLES.items():
            tab_widget = QWidget()
            tab_layout = QVBoxLayout()
            tab_layout.setContentsMargins(15, 15, 15, 15)
            tab_layout.setSpacing(10)
            
            # Almacenar los checkboxes de acciones para esta sección
            self.permisos_widgets[seccion] = {}
            
            # Crear checkboxes para cada acción disponible
            acciones = config.get('acciones', {})
            for accion, accion_config in acciones.items():
                checkbox = QCheckBox()
                checkbox.setText(f"{accion_config['label']}")
                checkbox.setToolTip(accion_config.get('desc', ''))
                checkbox.setEnabled(True)  # Asegurar que esté habilitado
                checkbox.setStyleSheet("""
                    QCheckBox {
                        spacing: 8px;
                        padding: 8px;
                        font-size: 13px;
                        color: #333;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                        border-radius: 3px;
                    }
                    QCheckBox::indicator:unchecked {
                        background-color: #ffffff;
                        border: 2px solid #bdbdbd;
                    }
                    QCheckBox::indicator:unchecked:hover {
                        border: 2px solid #1976D2;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #1976D2;
                        border: 2px solid #1565C0;
                        image: url(:/check);
                    }
                    QCheckBox::indicator:checked:hover {
                        background-color: #1565C0;
                    }
                    QCheckBox:hover {
                        background-color: #f5f5f5;
                        border-radius: 3px;
                    }
                """)
                
                self.permisos_widgets[seccion][accion] = checkbox
                tab_layout.addWidget(checkbox)
            
            tab_layout.addStretch()
            tab_widget.setLayout(tab_layout)
            
            # Agregar la pestaña
            self.tabs_permisos.addTab(tab_widget, config['label'])
        
        layout.addWidget(self.tabs_permisos)
        
        # --- Botones mejorados ---
        botones_layout = QHBoxLayout()
        
        btn_guardar = QPushButton("Guardar Cambios")
        btn_guardar.setMinimumWidth(140)
        btn_guardar.setMinimumHeight(38)
        btn_guardar.setFont(QFont("Segoe UI", 11, QFont.Bold))
        btn_guardar.clicked.connect(self.guardar)
        btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
        """)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setMinimumWidth(140)
        btn_cancelar.setMinimumHeight(38)
        btn_cancelar.setFont(QFont("Segoe UI", 11, QFont.Bold))
        btn_cancelar.clicked.connect(self.reject)
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
        """)
        
        botones_layout.addStretch()
        botones_layout.addWidget(btn_guardar)
        botones_layout.addWidget(btn_cancelar)
        
        layout.addLayout(botones_layout)
        
        self.setLayout(layout)
        
        # Ajustar tamaño del diálogo para que sea más manejable
        self.setGeometry(100, 100, 700, 650)
    
    def guardar(self):
        """Valida y guarda el ayudante."""
        nombre = self.nombre_input.text().strip()
        usuario = self.usuario_input.text().strip()
        contacto = self.contacto_input.text().strip()
        notas = self.notas_input.toPlainText().strip()
        
        # Validaciones
        if not nombre:
            QMessageBox.warning(self, "Error", "Ingrese el nombre del ayudante")
            return
        
        if not usuario:
            QMessageBox.warning(self, "Error", "Ingrese el usuario (login)")
            return
        
        # Si es creación, validar contraseña
        if not self.ayudante:
            password = getattr(self, 'password_input', None)
            password_confirm = getattr(self, 'password_confirm', None)
            
            if not password or not password.text():
                QMessageBox.warning(self, "Error", "Ingrese una contraseña")
                return
            
            if password.text() != password_confirm.text():
                QMessageBox.warning(self, "Error", "Las contraseñas no coinciden")
                return
            
            if len(password.text()) < 6:
                QMessageBox.warning(self, "Error", "La contraseña debe tener al menos 6 caracteres")
                return
        
        # Obtener permisos seleccionados (formato granular)
        permisos = {}
        for seccion, acciones_dict in self.permisos_widgets.items():
            acciones_seleccionadas = [accion for accion, checkbox in acciones_dict.items() 
                                     if checkbox.isChecked()]
            if acciones_seleccionadas:
                permisos[seccion] = acciones_seleccionadas
        
        if not permisos:
            QMessageBox.warning(self, "Error", "Seleccione al menos un permiso")
            return
        
        # Guardar datos
        self.datos = {
            'nombre': nombre,
            'usuario': usuario,
            'contacto': contacto,
            'password': getattr(self, 'password_input', None).text() if not self.ayudante else None,
            'permisos': permisos,
            'notas': notas
        }
        
        self.accept()
    
    def get_datos(self):
        """Retorna los datos del ayudante."""
        return self.datos if hasattr(self, 'datos') else None


# ============================================================
# PÁGINA PRINCIPAL DE GESTIÓN DE AYUDANTES
# ============================================================

class HelpersPage(QWidget):
    """Página de gestión de ayudantes."""
    
    def __init__(self, parent=None, username=None):
        super().__init__(parent)
        self.username = username  # Usuario del jefe
        self.setup_ui()
        self.cargar_ayudantes_tabla()
    
    def setup_ui(self):
        """Configura la interfaz."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # --- Encabezado mejorado ---
        encabezado_layout = QHBoxLayout()
        encabezado_layout.setSpacing(15)
        
        titulo = QLabel("👥 Gestión de Ayudantes")
        titulo_font = QFont("Segoe UI", 24, QFont.Bold)
        titulo.setFont(titulo_font)
        titulo.setStyleSheet("color: #1a237e;")
        encabezado_layout.addWidget(titulo)
        
        encabezado_layout.addStretch()
        
        btn_nuevo = QPushButton("Nuevo Ayudante")
        btn_nuevo.setMinimumWidth(180)
        btn_nuevo.setMinimumHeight(40)
        btn_nuevo.setFont(QFont("Segoe UI", 11, QFont.Bold))
        btn_nuevo.clicked.connect(self.crear_ayudante)
        btn_nuevo.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        encabezado_layout.addWidget(btn_nuevo)
        
        layout.addLayout(encabezado_layout)
        
        # --- Separador visual ---
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setStyleSheet("background-color: #e0e0e0; height: 1px;")
        layout.addWidget(separador)
        
        # --- Tabla mejorada ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "👤 Nombre", "🔐 Usuario", "📋 Permisos", "✓ Activo", "⏰ Última Conexión", "📝 Notas", "⚙️ Acciones"
        ])
        
        # Configurar ancho de columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        # Altura de filas
        self.tabla.verticalHeader().setDefaultSectionSize(50)
        
        self.tabla.setStyleSheet("""
            QTableWidget {
                gridline-color: #e8e8e8;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #fafafa;
                selection-background-color: #e3f2fd;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 10px;
                border: none;
                font-weight: bold;
                color: #424242;
                border-right: 1px solid #e0e0e0;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1a237e;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f5f5f5;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #bdbdbd;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9e9e9e;
            }
        """)
        
        layout.addWidget(self.tabla, 1)
        
        self.setLayout(layout)
        self.setStyleSheet("QWidget { background-color: #ffffff; }")
    
    def cargar_ayudantes_tabla(self):
        """Carga los ayudantes en la tabla."""
        ayudantes = cargar_ayudantes(self.username)
        
        self.tabla.setRowCount(len(ayudantes))
        
        for row, ayudante in enumerate(ayudantes):
            # Nombre
            item_nombre = QTableWidgetItem(ayudante.get('nombre', ''))
            self.tabla.setItem(row, 0, item_nombre)
            
            # Usuario
            item_usuario = QTableWidgetItem(ayudante.get('usuario', ''))
            self.tabla.setItem(row, 1, item_usuario)
            
            # Permisos (contar cuántos tiene)
            permisos = ayudante.get('permisos', {})
            permisos_activos = [p for p, v in permisos.items() if v]
            item_permisos = QTableWidgetItem(f"{len(permisos_activos)}/{len(PERMISOS_DISPONIBLES)}")
            self.tabla.setItem(row, 2, item_permisos)
            
            # Activo (checkbox)
            activo = ayudante.get('activo', False)
            item_activo = QTableWidgetItem("✓" if activo else "✕")
            item_activo.setBackground(QBrush(QColor("#E8F5E9" if activo else "#FFEBEE")))
            self.tabla.setItem(row, 3, item_activo)
            
            # Última conexión
            fecha_conexion = ayudante.get('fecha_ultima_conexion')
            if fecha_conexion:
                fecha_conexion = fecha_conexion.split('T')[0]  # Solo la fecha
            item_conexion = QTableWidgetItem(fecha_conexion or "Nunca")
            self.tabla.setItem(row, 4, item_conexion)
            
            # Notas
            item_notas = QTableWidgetItem(ayudante.get('notas', ''))
            self.tabla.setItem(row, 5, item_notas)
            
            # Acciones (botones mejorados)
            botones_layout = QHBoxLayout()
            botones_layout.setContentsMargins(4, 4, 4, 4)
            botones_layout.setSpacing(6)
            
            btn_editar = QPushButton("Editar")
            btn_editar.setMaximumWidth(100)
            btn_editar.setMinimumHeight(32)
            btn_editar.clicked.connect(lambda checked, a=ayudante: self.editar_ayudante(a))
            btn_editar.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
                QPushButton:pressed {
                    background-color: #E65100;
                }
            """)
            
            btn_eliminar = QPushButton("Borrar")
            btn_eliminar.setMaximumWidth(100)
            btn_eliminar.setMinimumHeight(32)
            btn_eliminar.clicked.connect(lambda checked, a=ayudante: self.eliminar_ayudante(a))
            btn_eliminar.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e53935;
                }
                QPushButton:pressed {
                    background-color: #c62828;
                }
            """)
            
            botones_layout.addWidget(btn_editar)
            botones_layout.addWidget(btn_eliminar)
            
            contenedor = QWidget()
            contenedor.setLayout(botones_layout)
            self.tabla.setCellWidget(row, 6, contenedor)
    
    def crear_ayudante(self):
        """Abre el diálogo para crear un nuevo ayudante."""
        dialogo = AyudanteDialog(self)
        if dialogo.exec_() == QDialog.Accepted:
            datos = dialogo.get_datos()
            if datos:
                resultado = crear_ayudante(
                    username_jefe=self.username,
                    nombre_ayudante=datos['nombre'],
                    usuario_ayudante=datos['usuario'],
                    contacto_ayudante=datos['contacto'],
                    password_ayudante=datos['password'],
                    permisos=datos['permisos']
                )
                
                if 'error' in resultado:
                    QMessageBox.critical(self, "Error", resultado['error'])
                else:
                    QMessageBox.information(self, "Éxito", 
                        f"Ayudante '{datos['nombre']}' creado correctamente")
                    self.cargar_ayudantes_tabla()
    
    def editar_ayudante(self, ayudante):
        """Abre el diálogo para editar un ayudante."""
        dialogo = AyudanteDialog(self, ayudante)
        if dialogo.exec_() == QDialog.Accepted:
            datos = dialogo.get_datos()
            if datos:
                resultado = editar_ayudante(
                    username_jefe=self.username,
                    id_ayudante=ayudante['id'],
                    datos_actualizacion={
                        'nombre': datos['nombre'],
                        'contacto': datos['contacto'],
                        'permisos': datos['permisos'],
                        'notas': datos['notas']
                    }
                )
                
                if 'error' in resultado:
                    QMessageBox.critical(self, "Error", resultado['error'])
                else:
                    QMessageBox.information(self, "Éxito", "Ayudante actualizado correctamente")
                    self.cargar_ayudantes_tabla()
    
    def eliminar_ayudante(self, ayudante):
        """Elimina un ayudante después de confirmación."""
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Desea eliminar el ayudante '{ayudante['nombre']}'?\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            resultado = eliminar_ayudante(self.username, ayudante['id'])
            
            if 'error' in resultado:
                QMessageBox.critical(self, "Error", resultado['error'])
            else:
                QMessageBox.information(self, "Éxito", "Ayudante eliminado correctamente")
                self.cargar_ayudantes_tabla()
