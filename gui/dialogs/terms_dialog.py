"""
Diálogo emergente de Términos y Condiciones.
Aparece al iniciar la aplicación por primera vez.
"""
import os
import json
import sys  # Importado para manejar rutas de recursos en PyInstaller
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QCheckBox,
    QLabel, QMessageBox, QApplication, QWidget # Se añade QWidget, aunque no se usa en el diálogo principal, es buena práctica
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from datetime import datetime # Importación directa y limpia

def get_base_dir():
    """Obtiene el directorio base, ya sea en entorno de desarrollo o empaquetado."""
    if getattr(sys, 'frozen', False):
        # En entorno empaquetado, el ejecutable está en el directorio raíz
        return os.path.dirname(sys.executable)
    else:
        # En desarrollo, subimos dos niveles desde gui/dialogs para llegar a la raíz
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Usar el directorio 'VISO' dentro del directorio base de la aplicación
VISO_DIR = os.path.join(get_base_dir(), "VISO")


class TermsDialog(QDialog):
    """Diálogo para aceptar Términos y Condiciones de Uso."""
    
    TERMS_FILE = os.path.join(VISO_DIR, "terms_accepted.json")
    
    @staticmethod
    def get_terms_text():
        """Carga el texto de términos desde archivo o usa un fallback.

        La lógica original incrustaba el texto de términos dentro de esta función,
        lo cual era un error de sintaxis grave. Ahora, el texto incrustado se
        usa solo como último recurso (fallback).
        """
        # 1. Intentar cargar desde data/terms.txt (mejor práctica)
        try:
            # Determinar el directorio base para entornos normales y PyInstaller
            base_dir = get_base_dir()
            terms_path = os.path.join(base_dir, "data", "terms.txt")
            
            if os.path.exists(terms_path):
                with open(terms_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            # Imprimir el error para depuración, pero no bloquear la aplicación
            print(f"Error loading terms from file: {e}")
        
        # 2. Fallback a texto por defecto (el texto que estaba incrustado y causaba error)
        # Se ha reformateado para ser una cadena multilinea estándar de Python.
        return """
Términos y Condiciones de Uso

1. Aceptación
Al utilizar este software, usted acepta íntegramente los presentes Términos y Condiciones de Uso. Si no está de acuerdo con alguno de ellos, deberá abstenerse de instalar, acceder o usar la aplicación.

2. Licencia y Propiedad Intelectual
El software es propiedad exclusiva del proveedor y está protegido por la Ley sobre el Derecho de Autor (Decreto Legislativo N° 822) y demás normas aplicables en el Perú.
Se concede al usuario una licencia de uso limitada, no exclusiva, revocable e intransferible, que le permite ejecutar el programa únicamente conforme a su finalidad.

Queda estrictamente prohibido sin autorización expresa y por escrito del titular:
• Copiar, reproducir, distribuir o redistribuir total o parcialmente el software.
• Modificar, adaptar o crear obras derivadas.
• Descompilar, realizar ingeniería inversa o intentar acceder al código fuente.
• Vender, arrendar, sublicenciar o transferir de cualquier modo la aplicación o sus componentes.

La licencia no implica cesión ni transferencia de derechos de propiedad intelectual.

3. Uso Permitido y Obligaciones del Usuario
El usuario se compromete a utilizar la aplicación de manera responsable, conforme a la ley y a estos términos. Está obligado a:
• Mantener la confidencialidad de sus credenciales de acceso.
• Comunicar de inmediato cualquier acceso no autorizado o vulnerabilidad detectada.
• No utilizar el software para actividades ilegales, fraudulentas, maliciosas o que perjudiquen a terceros.
• No interferir ni intentar comprometer la seguridad, estabilidad o disponibilidad del sistema.

4. Protección y Tratamiento de Datos Personales
La aplicación puede recopilar, procesar o almacenar datos personales, incluyendo información sensible. El proveedor adopta medidas razonables de seguridad —como cifrado en tránsito y en reposo, control de accesos y registros de auditoría— para proteger los datos.

No obstante, ninguna medida es completamente infalible. El usuario es responsable de realizar copias de seguridad periódicas.

El tratamiento de los datos se efectúa conforme a la Ley N° 29733 - Ley de Protección de Datos Personales, su Reglamento y la Política de Privacidad del proveedor. El usuario es igualmente responsable de cumplir con la normativa de protección de datos que le sea aplicable.

5. Confidencialidad
Toda información relacionada con pacientes, clientes, operaciones o cualquier otro dato sensible es confidencial.
El acceso y uso de dicha información se limita a personal autorizado, y su divulgación a terceros está prohibida salvo por obligación legal o consentimiento expreso del titular.

6. Registro y Auditoría
El software registra automáticamente eventos relevantes (inicios de sesión, modificaciones de configuración, importaciones, exportaciones, entre otros) con fines de seguridad, trazabilidad y auditoría.
Dichos registros podrán ser utilizados para investigar usos indebidos, incidentes o violaciones de estos términos.

7. Responsabilidad y Limitación de Daños
En la máxima medida permitida por la ley, el proveedor no será responsable por pérdidas indirectas, lucro cesante, daños emergentes, pérdida de datos o interrupciones del servicio.
El usuario es responsable de mantener respaldos actualizados y de garantizar la integridad de su entorno tecnológico.

El proveedor no garantiza la disponibilidad continua de los servidores, la correcta operación del software ni el funcionamiento del servicio de extracción de datos en línea, los cuales pueden experimentar fallas, interrupciones o errores que afecten su operación. El usuario acepta que estos riesgos son propios del uso del software y que el proveedor no será responsable por ellos.

El proveedor no garantiza la ausencia total de errores en el software ni la disponibilidad ininterrumpida del servicio.

8. Medidas ante Uso Indebido
Cualquier uso indebido —incluyendo, sin limitarse a, acceso no autorizado, suplantación de identidad, distribución de malware, extracción masiva de datos o uso con fines ilícitos— podrá dar lugar a:
• Cancelación inmediata de la licencia de uso.
• Bloqueo temporal o permanente del acceso del usuario.
• Comunicación a las autoridades competentes y cooperación en las investigaciones correspondientes.

9. Actualizaciones y Modificación de los Términos
El proveedor podrá actualizar la aplicación y modificar estos términos en cualquier momento.
Las modificaciones serán efectivas desde su publicación. El uso continuado de la aplicación implica la aceptación de las nuevas condiciones.

10. Seguridad y Buenas Prácticas
Se recomienda a los usuarios:
• Mantener el sistema operativo y el software actualizados.
• Utilizar contraseñas robustas y autenticación de doble factor cuando sea posible.
• Limitar el acceso físico y lógico a los dispositivos donde se ejecute la aplicación.
• Realizar copias de seguridad periódicas y verificar su restauración.

11. Soporte y Contacto
Para consultas relacionadas con seguridad, privacidad o soporte técnico, comuníquese a través de la sección de contacto disponible dentro de la aplicación.

12. Ley Aplicable y Jurisdicción
Estos Términos se rigen por las leyes de la República del Perú.
Cualquier controversia derivada de la interpretación o ejecución de este documento será sometida a la jurisdicción de los tribunales competentes de Lima, Perú.

13. Disposiciones Finales
Si alguna cláusula de estos términos se considera inválida o inaplicable, las demás disposiciones permanecerán vigentes.
La falta de ejercicio de cualquier derecho por parte del proveedor no constituye renuncia al mismo.

Al aceptar estos Términos y Condiciones, usted declara haber leído, comprendido y aceptado todas las disposiciones aquí contenidas.
"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Términos y Condiciones de Uso")
        self.setGeometry(100, 100, 800, 600)
        self.setModal(True)
        
        # Uso de sys en lugar de 'import sys' dentro de la función, ya está importado arriba.
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "icon.ico")
        
        # No es necesario re-importar QIcon, ya está arriba
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_ui()
        
    def init_ui(self):
        """Inicializar la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("TÉRMINOS Y CONDICIONES DE USO")
        title_font = QFont()
        title_font.setPointSize(16) # Tamaño ligeramente más grande para el título
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter) # Centrar el título
        layout.addWidget(title)
        
        # Texto de términos (solo lectura)
        self.terms_text = QTextEdit()
        self.terms_text.setReadOnly(True)
        self.terms_text.setPlainText(self.get_terms_text().strip()) # .strip() para limpiar el texto fallback
        self.terms_text.setStyleSheet("""
            QTextEdit {
                background-color: #F8F8F8; /* Color suave para fondo */
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 15px;
                font-size: 12px;
                color: #222222;
                line-height: 1.5; /* Propiedad CSS solo para HTML, pero buena idea */
            }
        """)
        layout.addWidget(self.terms_text)
        
        # Checkbox de aceptación
        self.checkbox_accept = QCheckBox("He leído y **Acepto** los Términos y Condiciones de Uso")
        self.checkbox_accept.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #000000;
                padding-top: 5px;
                font-weight: normal;
            }
        """)
        layout.addWidget(self.checkbox_accept)
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(15)
        
        # Spacer para empujar los botones a la derecha
        buttons_layout.addStretch() 
        
        btn_reject = QPushButton("No Acepto y Salir")
        btn_reject.setStyleSheet("""
            QPushButton {
                background-color: #6C757D; /* Gris más profesional */
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
            QPushButton:pressed {
                background-color: #494F54;
            }
        """)
        btn_reject.clicked.connect(self.reject_terms)
        buttons_layout.addWidget(btn_reject)
        
        btn_accept = QPushButton("Acepto y Continuar")
        btn_accept.setStyleSheet("""
            QPushButton {
                background-color: #007BFF; /* Azul de énfasis */
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0056B3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled { /* Estilo para cuando está deshabilitado */
                background-color: #90BEE0;
            }
        """)
        btn_accept.clicked.connect(self.accept_terms)
        
        # Desactivar el botón de Aceptar por defecto hasta que se marque la casilla
        btn_accept.setEnabled(False) 
        self.checkbox_accept.stateChanged.connect(lambda state: btn_accept.setEnabled(state == Qt.Checked))
        
        buttons_layout.addWidget(btn_accept)
        
        layout.addLayout(buttons_layout)
        
    def accept_terms(self):
        """Aceptar los términos y guardar en archivo."""
        # La verificación de la casilla ya no es estrictamente necesaria aquí
        # porque el botón se habilita/deshabilita con el checkbox.
        
        self.save_acceptance()
        self.accept() # Cierra el diálogo con resultado QDialog.Accepted
    
    def reject_terms(self):
        """Rechazar los términos y cerrar la aplicación."""
        reply = QMessageBox.question(
            self,
            "Confirmar Salida",
            "Si selecciona **'No Acepto'**, la aplicación se cerrará inmediatamente.\n\n"
            "Deberá aceptar los términos en un inicio posterior para poder usar la aplicación. ¿Desea continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QApplication.quit()
    
    @staticmethod
    def save_acceptance():
        """Guardar la aceptación en un archivo JSON."""
        os.makedirs(VISO_DIR, exist_ok=True)
        acceptance_data = {
            "accepted": True,
            "timestamp": str(datetime.now()) # Uso de datetime importado
        }
        try:
            with open(TermsDialog.TERMS_FILE, 'w', encoding='utf-8') as f:
                json.dump(acceptance_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # En una aplicación real, usar logging o una alerta más seria aquí.
            print(f"Error guardando aceptación de términos: {e}")
    
    @staticmethod
    def has_accepted():
        """Verificar si el usuario ya aceptó los términos."""
        if not os.path.exists(TermsDialog.TERMS_FILE):
            return False
        try:
            with open(TermsDialog.TERMS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Verifica que el campo 'accepted' exista y sea True
                return data.get("accepted", False)
        except json.JSONDecodeError:
            print(f"Error: El archivo {TermsDialog.TERMS_FILE} no es un JSON válido.")
            return False
        except Exception as e:
            print(f"Error leyendo aceptación de términos: {e}")
            return False

# --- EJEMPLO DE USO (Opcional, para demostrar el funcionamiento) ---

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
    
#     if not TermsDialog.has_accepted():
#         dialog = TermsDialog()
#         # exec_() es obsoleto, usar exec()
#         if dialog.exec() == QDialog.Accepted:
#             print("Términos aceptados. La aplicación puede continuar.")
#         else:
#             print("Términos rechazados o ventana cerrada. La aplicación ha salido.")
#     else:
#         print("Términos ya aceptados. Continuando con la aplicación.")
#         # Aquí iría el código para iniciar la ventana principal
    
#     sys.exit(app.exec_())