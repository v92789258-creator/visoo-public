"""
Componente de loader animado con 3 puntos que se hacen grandes y pequeños
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication, QPushButton
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette


class AnimatedLoaderButton(QPushButton):
    """Botón con loader animado integrado."""
    
    def __init__(self, text="Registrar Venta", parent=None):
        super().__init__(text, parent)
        self.original_text = text
        self.animation_step = 0
        
        # Timer para la animación
        self.timer = QTimer()
        self.timer.timeout.connect(self._animate_dots)
        self.timer.setInterval(200)
        
    def start_loading(self):
        """Inicia la animación del loader."""
        self.setEnabled(False)
        self.animation_step = 0
        self.timer.start()
        self._animate_dots()
    
    def _animate_dots(self):
        """Anima los 3 puntos haciéndolos alternativamente grandes y pequeños."""
        dots = []
        
        for i in range(3):
            if (self.animation_step // 2) == i:
                dots.append("●")
            else:
                dots.append("○")
        
        loader_text = "  ".join(dots)
        self.setText(loader_text)
        self.animation_step = (self.animation_step + 1) % 6
    
    def show_success(self, duration=1000):
        """Muestra un checkmark durante el tiempo especificado."""
        self.timer.stop()
        self.setText("✓")
        
        # Timer para volver al texto original
        QTimer.singleShot(duration, self.reset_button)
    
    def reset_button(self):
        """Vuelve el botón al estado original."""
        self.setText(self.original_text)
        self.setEnabled(True)
        self.animation_step = 0


class AnimatedLoaderDialog(QDialog):
    """Diálogo con loader animado de 3 puntos pulsantes."""
    
    def __init__(self, title="Procesando...", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 350, 180)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f8f8;
                border-radius: 15px;
                border: 2px solid #e0e0e0;
            }
        """)
        
        # Desactivar el botón de cerrar
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Etiqueta de título
        self.title_label = QLabel(title)
        title_font = QFont("Segoe UI", 13)
        title_font.setWeight(QFont.DemiBold)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #333333; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        
        # Etiqueta para el loader con animación
        self.loader_label = QLabel("●  ●  ●")
        loader_font = QFont("Arial", 28)
        loader_font.setBold(True)
        self.loader_label.setFont(loader_font)
        self.loader_label.setAlignment(Qt.AlignCenter)
        self.loader_label.setStyleSheet("""
            color: #1976D2;
            letter-spacing: 8px;
            min-height: 50px;
        """)
        layout.addWidget(self.loader_label)
        
        # Etiqueta de submensaje (opcional)
        self.status_label = QLabel("Por favor espera...")
        status_font = QFont("Segoe UI", 10)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666666; margin-top: 10px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Variables para la animación
        self.animation_step = 0
        self.dot_sizes = [1.0, 1.0, 1.0]  # Tamaño relativo de cada punto (1.0 = normal)
        self.dot_states = ["◯", "◉", "●"]  # Estados visuales: pequeño, mediano, grande
        
        # Timer para la animación
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_dots)
        self.timer.start(200)  # Cambiar cada 200ms para animación suave
    
    def animate_dots(self):
        """Anima los 3 puntos haciéndolos alternativamente grandes y pequeños."""
        self.animation_step = (self.animation_step + 1) % 6  # Ciclo de 6 pasos
        
        # Crear los caracteres animados
        dots = []
        
        for i in range(3):
            # Calcular cuándo este punto debe estar activo/grande
            # Punto 1 activo: pasos 0-1
            # Punto 2 activo: pasos 2-3
            # Punto 3 activo: pasos 4-5
            if (self.animation_step // 2) == i:
                # Este punto está activo (agrandarse)
                progress = (self.animation_step % 2)  # 0 o 1
                if progress == 0:
                    dots.append("●")  # Punto grande
                else:
                    dots.append("●")  # Punto grande con más énfasis
            else:
                # Este punto está inactivo (pequeño)
                dots.append("○")  # Punto pequeño
        
        # Crear el texto con los puntos animados
        loader_text = "  ".join(dots)
        self.loader_label.setText(loader_text)
        
        # Cambiar color levemente para más dinamismo
        colors = ["#1976D2", "#1565C0", "#0D47A1", "#1976D2", "#1565C0", "#0D47A1"]
        self.loader_label.setStyleSheet(f"""
            color: {colors[self.animation_step]};
            letter-spacing: 8px;
            min-height: 50px;
        """)
    
    def set_status(self, status_text):
        """Actualiza el mensaje de estado."""
        self.status_label.setText(status_text)
    
    def closeEvent(self, event):
        """Detener el timer al cerrar."""
        self.timer.stop()
        event.accept()


class LoaderWorker(QThread):
    """Worker thread para ejecutar tareas en segundo plano."""
    
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # Para mensajes de progreso
    
    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.result = None
    
    def run(self):
        """Ejecutar la tarea en el thread."""
        try:
            # Ejecutar la tarea
            self.result = self.task_func(*self.args, **self.kwargs)
            self.finished.emit()
        except Exception as e:
            error_msg = str(e)
            self.error.emit(error_msg)
            import traceback
            traceback.print_exc()
