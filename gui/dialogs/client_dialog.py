"""
Diálogos para gestión de clientes.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QMessageBox, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt
from utils.file_handler import cargar_clientes, guardar_clientes


class ClientDetailsDialog(QDialog):
    """Diálogo para ver/editar detalles de un cliente."""
    
    def __init__(self, cliente_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detalles del Cliente - {cliente_data.get('nombre', 'Desconocido')}")
        self.setGeometry(100, 100, 600, 400)
        self.parent_app = parent
        self.cliente_data = cliente_data
        self.username = getattr(parent, 'username', None)
        self.modo_edicion = False  # Controlar modo edición
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Crear tabs
        tabs = QTabWidget()
        
        # Tab 1: Información General
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "Información General")
        
        # Tab 2: Contacto
        contact_tab = self.create_contact_tab()
        tabs.addTab(contact_tab, "Contacto")
        
        # Tab 3: Información Adicional
        additional_tab = self.create_additional_tab()
        tabs.addTab(additional_tab, "Información Adicional")
        
        layout.addWidget(tabs)
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.btn_editar = QPushButton("Editar")
        self.btn_editar.setFixedWidth(100)
        self.btn_editar.setStyleSheet("""
            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0d47a1;
            }
        """)
        self.btn_editar.clicked.connect(self.toggle_edicion)
        buttons_layout.addWidget(self.btn_editar)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedWidth(100)
        btn_cerrar.clicked.connect(self.close)
        buttons_layout.addWidget(btn_cerrar)
        
        layout.addLayout(buttons_layout)
    
    def create_general_tab(self):
        """Crea la pestaña de información general."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Nombre
        layout.addWidget(QLabel("Nombre:"))
        self.entry_nombre = QLineEdit()
        layout.addWidget(self.entry_nombre)
        
        # DNI/RUC
        layout.addWidget(QLabel("DNI/RUC:"))
        self.entry_dni_ruc = QLineEdit()
        layout.addWidget(self.entry_dni_ruc)
        
        # Tipo de Cliente
        layout.addWidget(QLabel("Tipo de Cliente:"))
        self.entry_tipo = QLineEdit()
        layout.addWidget(self.entry_tipo)
        
        # Razón Social (si aplica)
        layout.addWidget(QLabel("Razón Social:"))
        self.entry_razon_social = QLineEdit()
        layout.addWidget(self.entry_razon_social)
        
        layout.addStretch()
        return widget
    
    def create_contact_tab(self):
        """Crea la pestaña de contacto."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Teléfono
        layout.addWidget(QLabel("Teléfono:"))
        self.entry_telefono = QLineEdit()
        layout.addWidget(self.entry_telefono)
        
        # Correo
        layout.addWidget(QLabel("Correo:"))
        self.entry_correo = QLineEdit()
        layout.addWidget(self.entry_correo)
        
        # Dirección
        layout.addWidget(QLabel("Dirección:"))
        self.entry_direccion = QLineEdit()
        layout.addWidget(self.entry_direccion)
        
        # Notas
        layout.addWidget(QLabel("Notas:"))
        self.text_notas = QTextEdit()
        layout.addWidget(self.text_notas)
        
        layout.addStretch()
        return widget
    
    def create_additional_tab(self):
        """Crea la pestaña de información adicional."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Edad
        layout.addWidget(QLabel("Edad:"))
        self.entry_edad = QLineEdit()
        layout.addWidget(self.entry_edad)
        
        # Género
        layout.addWidget(QLabel("Género:"))
        self.entry_genero = QLineEdit()
        layout.addWidget(self.entry_genero)
        
        # Fecha de Nacimiento
        layout.addWidget(QLabel("Fecha de Nacimiento:"))
        self.entry_fecha_nacimiento = QLineEdit()
        layout.addWidget(self.entry_fecha_nacimiento)
        
        # Fecha de Registro
        layout.addWidget(QLabel("Fecha de Registro:"))
        self.entry_fecha_registro = QLineEdit()
        layout.addWidget(self.entry_fecha_registro)
        
        layout.addStretch()
        return widget
    
    def load_data(self):
        """Carga los datos del cliente en los campos."""
        self.entry_nombre.setText(self.cliente_data.get('nombre', ''))
        self.entry_dni_ruc.setText(self.cliente_data.get('dni_ruc', self.cliente_data.get('dni', '')))
        self.entry_tipo.setText(self.cliente_data.get('tipo', 'Personal'))
        self.entry_razon_social.setText(self.cliente_data.get('razon_social', ''))
        self.entry_telefono.setText(self.cliente_data.get('telefono', ''))
        self.entry_correo.setText(self.cliente_data.get('correo', ''))
        self.entry_direccion.setText(self.cliente_data.get('direccion', ''))
        self.text_notas.setText(self.cliente_data.get('notas', ''))
        self.entry_edad.setText(str(self.cliente_data.get('edad', '')))
        self.entry_genero.setText(self.cliente_data.get('genero', ''))
        self.entry_fecha_nacimiento.setText(self.cliente_data.get('fecha_nacimiento', ''))
        self.entry_fecha_registro.setText(self.cliente_data.get('fecha_registro', ''))
    
    def editar_cliente(self):
        """Abre diálogo para editar cliente."""
        dialog = EditClientDialog(self.cliente_data, self.parent_app)
        if dialog.exec_() == QDialog.Accepted:
            clientes = cargar_clientes(self.username)
            # Buscar y actualizar cliente
            for i, c in enumerate(clientes):
                if c.get('dni_ruc') == self.cliente_data.get('dni_ruc') or \
                   c.get('dni') == self.cliente_data.get('dni'):
                    clientes[i] = dialog.get_cliente_data()
                    break
            guardar_clientes(self.username, clientes)
            # Limpiar cache global para que se refresque
            try:
                from utils.data_cache_manager import get_global_cache
                cache = get_global_cache()
                cache.clear_data_type(self.username, 'clientes')
            except Exception:
                pass
            self.cliente_data = dialog.get_cliente_data()
            self.load_data()
            QMessageBox.information(self, "Éxito", "Cliente actualizado correctamente.")
    
    def toggle_edicion(self):
        """Alterna entre modo lectura y edición."""
        if not self.modo_edicion:
            # Activar edición
            self.modo_edicion = True
            self.entry_nombre.setReadOnly(False)
            self.entry_dni_ruc.setReadOnly(False)
            self.entry_tipo.setReadOnly(False)
            self.entry_razon_social.setReadOnly(False)
            self.entry_telefono.setReadOnly(False)
            self.entry_correo.setReadOnly(False)
            self.entry_direccion.setReadOnly(False)
            self.text_notas.setReadOnly(False)
            self.entry_edad.setReadOnly(False)
            self.entry_genero.setReadOnly(False)
            self.entry_fecha_nacimiento.setReadOnly(False)
            self.entry_fecha_registro.setReadOnly(False)
            self.btn_editar.setText("Guardar")
            self.btn_editar.setStyleSheet("""
                QPushButton {
                    background: #107c10;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #0a5f0a;
                }
            """)
        else:
            # Guardar cambios
            self.guardar_cambios()
    
    def load_data(self):
        """Carga los datos del cliente en los campos."""
        self.entry_nombre.setText(self.cliente_data.get('nombre', ''))
        self.entry_nombre.setReadOnly(True)
        self.entry_dni_ruc.setText(self.cliente_data.get('dni_ruc', self.cliente_data.get('dni', '')))
        self.entry_dni_ruc.setReadOnly(True)
        self.entry_tipo.setText(self.cliente_data.get('tipo', 'Personal'))
        self.entry_tipo.setReadOnly(True)
        self.entry_razon_social.setText(self.cliente_data.get('razon_social', ''))
        self.entry_razon_social.setReadOnly(True)
        self.entry_telefono.setText(self.cliente_data.get('telefono', ''))
        self.entry_telefono.setReadOnly(True)
        self.entry_correo.setText(self.cliente_data.get('correo', ''))
        self.entry_correo.setReadOnly(True)
        self.entry_direccion.setText(self.cliente_data.get('direccion', ''))
        self.entry_direccion.setReadOnly(True)
        self.text_notas.setText(self.cliente_data.get('notas', ''))
        self.text_notas.setReadOnly(True)
    
    def guardar_cambios(self):
        """Guarda los cambios realizados en los campos editables."""
        try:
            # Actualizar datos locales
            self.cliente_data['nombre'] = self.entry_nombre.text()
            self.cliente_data['dni'] = self.entry_dni_ruc.text()
            self.cliente_data['dni_ruc'] = self.entry_dni_ruc.text()
            self.cliente_data['tipo'] = self.entry_tipo.text()
            self.cliente_data['razon_social'] = self.entry_razon_social.text()
            self.cliente_data['telefono'] = self.entry_telefono.text()
            self.cliente_data['correo'] = self.entry_correo.text()
            self.cliente_data['direccion'] = self.entry_direccion.text()
            self.cliente_data['notas'] = self.text_notas.toPlainText()
            self.cliente_data['edad'] = self.entry_edad.text()
            self.cliente_data['genero'] = self.entry_genero.text()
            self.cliente_data['fecha_nacimiento'] = self.entry_fecha_nacimiento.text()
            self.cliente_data['fecha_registro'] = self.entry_fecha_registro.text()
            
            # Cargar clientes y actualizar
            clientes = cargar_clientes(self.username)
            dni_original = self.cliente_data.get('dni_ruc') or self.cliente_data.get('dni')
            
            encontrado = False
            for i, c in enumerate(clientes):
                if c.get('dni_ruc') == dni_original or c.get('dni') == dni_original:
                    clientes[i] = self.cliente_data
                    encontrado = True
                    break
            
            if encontrado:
                guardar_clientes(self.username, clientes)
                
                # Limpiar cache
                try:
                    from utils.data_cache_manager import get_global_cache
                    cache = get_global_cache()
                    cache.clear_data_type(self.username, 'clientes')
                except Exception:
                    pass
                
                # Desactivar edición
                self.modo_edicion = False
                self.entry_nombre.setReadOnly(True)
                self.entry_dni_ruc.setReadOnly(True)
                self.entry_tipo.setReadOnly(True)
                self.entry_razon_social.setReadOnly(True)
                self.entry_telefono.setReadOnly(True)
                self.entry_correo.setReadOnly(True)
                self.entry_direccion.setReadOnly(True)
                self.text_notas.setReadOnly(True)
                self.btn_editar.setText("Editar")
                self.btn_editar.setStyleSheet("""
                    QPushButton {
                        background: #1976d2;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #0d47a1;
                    }
                """)
                
                QMessageBox.information(self, "Éxito", "Cliente actualizado correctamente.")
            else:
                QMessageBox.warning(self, "Error", "No se encontró el cliente para actualizar.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar cambios: {str(e)}")


class EditClientDialog(QDialog):
    """Diálogo para editar datos de un cliente."""
    
    def __init__(self, cliente_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Cliente - {cliente_data.get('nombre', 'Desconocido')}")
        self.setGeometry(100, 100, 600, 500)
        self.cliente_data = cliente_data.copy()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo de edición."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Nombre
        layout.addWidget(QLabel("Nombre:"))
        self.entry_nombre = QLineEdit()
        layout.addWidget(self.entry_nombre)
        
        # DNI/RUC
        layout.addWidget(QLabel("DNI/RUC:"))
        self.entry_dni_ruc = QLineEdit()
        layout.addWidget(self.entry_dni_ruc)
        
        # Tipo de Cliente
        layout.addWidget(QLabel("Tipo de Cliente:"))
        self.entry_tipo = QLineEdit()
        layout.addWidget(self.entry_tipo)
        
        # Razón Social
        layout.addWidget(QLabel("Razón Social:"))
        self.entry_razon_social = QLineEdit()
        layout.addWidget(self.entry_razon_social)
        
        # Teléfono
        layout.addWidget(QLabel("Teléfono:"))
        self.entry_telefono = QLineEdit()
        layout.addWidget(self.entry_telefono)
        
        # Correo
        layout.addWidget(QLabel("Correo:"))
        self.entry_correo = QLineEdit()
        layout.addWidget(self.entry_correo)
        
        # Dirección
        layout.addWidget(QLabel("Dirección:"))
        self.entry_direccion = QLineEdit()
        layout.addWidget(self.entry_direccion)
        
        # Notas
        layout.addWidget(QLabel("Notas:"))
        self.text_notas = QTextEdit()
        layout.addWidget(self.text_notas)
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setFixedWidth(100)
        btn_guardar.setStyleSheet("""
            QPushButton {
                background: #4caf50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #388e3c;
            }
        """)
        btn_guardar.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_guardar)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedWidth(100)
        btn_cancelar.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancelar)
        
        layout.addLayout(buttons_layout)
    
    def load_data(self):
        """Carga los datos del cliente."""
        self.entry_nombre.setText(self.cliente_data.get('nombre', ''))
        self.entry_dni_ruc.setText(self.cliente_data.get('dni_ruc', self.cliente_data.get('dni', '')))
        self.entry_tipo.setText(self.cliente_data.get('tipo', 'Personal'))
        self.entry_razon_social.setText(self.cliente_data.get('razon_social', ''))
        self.entry_telefono.setText(self.cliente_data.get('telefono', ''))
        self.entry_correo.setText(self.cliente_data.get('correo', ''))
        self.entry_direccion.setText(self.cliente_data.get('direccion', ''))
        self.text_notas.setText(self.cliente_data.get('notas', ''))
    
    def get_cliente_data(self):
        """Retorna los datos del cliente editados."""
        return {
            'nombre': self.entry_nombre.text().strip(),
            'dni_ruc': self.entry_dni_ruc.text().strip(),
            'tipo': self.entry_tipo.text().strip() or 'Personal',
            'razon_social': self.entry_razon_social.text().strip(),
            'telefono': self.entry_telefono.text().strip(),
            'correo': self.entry_correo.text().strip(),
            'direccion': self.entry_direccion.text().strip(),
            'notas': self.text_notas.toPlainText().strip(),
        }
