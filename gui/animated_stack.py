"""Implementa un QStackedWidget con transiciones animadas."""

from PyQt5.QtWidgets import QStackedWidget, QSizePolicy
from PyQt5.QtCore import QTimer, QPropertyAnimation, QEasingCurve, Qt, QPoint, QSize

class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._next_index = 0
        self._animation_duration = 300  # Más rápido
        self._animation = None
        self._block_animation = False
        
        # Asegurar que el widget tenga un fondo sólido
        self.setStyleSheet("""
            QStackedWidget {
                background: white;
            }
            QWidget {
                background: white;
            }
        """)

        # Permitir que el stack se adapte al viewport actual
        # y no conserve el ancho maximo de otra pagina.
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self):
        """Usa el sizeHint del widget actual."""
        current = self.currentWidget()
        if current is not None:
            hint = current.sizeHint()
            if hint.isValid():
                return QSize(max(0, hint.width()), max(0, hint.height()))
        return super().sizeHint()

    def minimumSizeHint(self):
        """Evita que una pagina ancha fije el min-width del stack."""
        current = self.currentWidget()
        if current is not None:
            min_hint = current.minimumSizeHint()
            if min_hint.isValid():
                return QSize(max(0, min_hint.width()), max(0, min_hint.height()))
            hint = current.sizeHint()
            if hint.isValid():
                return QSize(max(0, hint.width()), max(0, hint.height()))
        return super().minimumSizeHint()

    def slide_in_next(self):
        """Anima la transición al siguiente widget."""
        if self._block_animation:
            super().setCurrentIndex(self._next_index)
            return
            
        if self._animation and self._animation.state() == QPropertyAnimation.Running:
            self._animation.stop()
        
        next_widget = self.widget(self._next_index)
        current_widget = self.currentWidget()
        
        if next_widget is None:
            return

        # Asegurar que ambos widgets tengan fondo sólido
        next_widget.setAutoFillBackground(True)
        if current_widget:
            current_widget.setAutoFillBackground(True)

        # Configurar widget siguiente
        width = self.width()
        next_widget.setGeometry(width, 0, width, self.height())
        
        # Hacer visible el widget siguiente
        next_widget.show()
        next_widget.raise_()

        # Crear y configurar la animación
        self._animation = QPropertyAnimation(next_widget, b"pos")
        self._animation.finished.connect(self.animation_finished)
        self._animation.setDuration(self._animation_duration)
        self._animation.setStartValue(QPoint(width, 0))
        self._animation.setEndValue(QPoint(0, 0))
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Iniciar animación
        self._animation.start()

    def slide_in_prev(self):
        """Anima la transición al widget anterior."""
        if self._block_animation:
            super().setCurrentIndex(self._next_index)
            return
            
        if self._animation and self._animation.state() == QPropertyAnimation.Running:
            self._animation.stop()
        
        next_widget = self.widget(self._next_index)
        current_widget = self.currentWidget()
        
        if next_widget is None:
            return

        # Asegurar que ambos widgets tengan fondo sólido
        next_widget.setAutoFillBackground(True)
        if current_widget:
            current_widget.setAutoFillBackground(True)

        # Configurar widget siguiente
        width = self.width()
        next_widget.setGeometry(-width, 0, width, self.height())
        
        # Hacer visible el widget siguiente
        next_widget.show()
        next_widget.raise_()

        # Crear y configurar la animación
        self._animation = QPropertyAnimation(next_widget, b"pos")
        self._animation.finished.connect(self.animation_finished)
        self._animation.setDuration(self._animation_duration)
        self._animation.setStartValue(QPoint(-width, 0))
        self._animation.setEndValue(QPoint(0, 0))
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Iniciar animación
        self._animation.start()

    def setCurrentIndex(self, index):
        """Sobrescribe setCurrentIndex para agregar animación."""
        current_idx = self.currentIndex()
        
        # Si es el primer widget, o mismo índice, o índice inválido: usar método estándar sin animación
        if self.count() <= 1 or current_idx == index or index < 0 or index >= self.count():
            super().setCurrentIndex(index)
            self.updateGeometry()
            parent = self.parentWidget()
            if parent is not None:
                parent.updateGeometry()
            return

        self._next_index = index
        
        # Determinar dirección de la animación basado en el índice
        if self._next_index > current_idx:
            self.slide_in_next()
        else:
            self.slide_in_prev()

    def animation_finished(self):
        """Limpia después de que termina la animación."""
        # Establecer el índice oficialmente usando la implementación base
        super().setCurrentIndex(self._next_index)
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None:
            parent.updateGeometry()
        
        # Restaurar geometría del widget (por si acaso QStackedWidget no lo hace)
        widget = self.widget(self._next_index)
        if widget:
            widget.move(0, 0)
        
        # Limpiar animación
        self._animation = None
