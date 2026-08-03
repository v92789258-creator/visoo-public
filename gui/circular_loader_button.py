"""
Botón con loader circular animado para navegación.
El botón muestra un loader mientras la página carga.
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QRect, QSize, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QFont
from PyQt5.QtWidgets import QPushButton


class CircularLoaderButton(QPushButton):
    """Botón con loader circular animado para navegación."""
    
    def __init__(self, icon_path=None, callback=None, tooltip="", parent=None):
        super().__init__(parent)
        
        self.icon_path = icon_path
        self.callback = callback
        self.tooltip = tooltip
        self.is_loading = False
        self.rotation = 0
        
        # Cargar ícono original
        self.original_icon = None
        if icon_path and self.icon_path:
            try:
                self.original_icon = QIcon(icon_path)
                self.setIcon(self.original_icon)
            except:
                pass
        
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setIconSize(QtCore.QSize(32, 32))
        
        # Timer para animación del loader
        self.loader_timer = QTimer()
        self.loader_timer.timeout.connect(self._update_loader)
        self.loader_timer.setInterval(50)  # 50ms
        
        # Timer para detener automáticamente
        self.auto_stop_timer = QTimer()
        self.auto_stop_timer.timeout.connect(self._auto_stop_loader)
        self.auto_stop_timer.setSingleShot(True)
        
        # Conectar click
        self.clicked.connect(self._on_clicked)
        
        # Estilos
        self.setStyleSheet("""
            QPushButton {
                padding: 15px;
                border: none;
                border-radius: 15px;
                background: transparent;
                margin: 8px 0;
            }
            QPushButton:hover:!checked {
                background: rgba(0,0,0,0.05);
            }
            QPushButton:pressed:!checked {
                background: rgba(0,0,0,0.1);
            }
            QPushButton:checked {
                background: #2C2C2C;
            }
            QPushButton:checked:hover {
                background: #404040;
            }
        """)
    
    def _on_clicked(self):
        """Llamado cuando se presiona el botón."""
        if not self.is_loading:
            self.start_loading()
            # Ejecutar callback en el siguiente evento
            if self.callback:
                QtCore.QTimer.singleShot(100, self.callback)
    
    def start_loading(self):
        """Comienza la animación del loader."""
        if self.is_loading:
            return
        
        self.is_loading = True
        self.rotation = 0
        
        # Ocultar el ícono actual
        self.setIcon(QIcon())
        
        # Asegurarse de que el timer no está activo
        if self.loader_timer.isActive():
            self.loader_timer.stop()
        
        # Iniciar timer de animación
        self.loader_timer.start(50)
        
        # Auto-detener después de 2.5 segundos
        if self.auto_stop_timer.isActive():
            self.auto_stop_timer.stop()
        self.auto_stop_timer.start(2500)
        
        # Forzar repintado inicial
        self.update()
    
    def stop_loading(self):
        """Detiene el loader y restaura el ícono."""
        if not self.is_loading:
            return
        
        self.is_loading = False
        
        # Detener timers
        if self.loader_timer.isActive():
            self.loader_timer.stop()
        
        if self.auto_stop_timer.isActive():
            self.auto_stop_timer.stop()
        
        # Restaurar el ícono original
        if self.original_icon:
            self.setIcon(self.original_icon)
        
        # Forzar repintado
        self.update()
    
    def _auto_stop_loader(self):
        """Auto-detiene el loader."""
        self.stop_loading()
    
    def _update_loader(self):
        """Actualiza la rotación del loader."""
        if self.is_loading:
            self.rotation = (self.rotation + 15) % 360
            self.update()
        else:
            # Si no está cargando, detener el timer
            if self.loader_timer.isActive():
                self.loader_timer.stop()
    
    def paintEvent(self, event):
        """Dibuja el botón y el loader si está activo."""
        # Dibujar el botón base
        super().paintEvent(event)
        
        # Si está cargando, dibujar el loader circular
        if self.is_loading:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            rect = self.rect()
            center = QPoint(rect.width() // 2, rect.height() // 2)
            radius = 14
            
            # Dibujar círculo gris (fondo)
            painter.setPen(QPen(QColor(200, 200, 200), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center, radius, radius)
            
            # Dibujar arco azul (loader)
            painter.setPen(QPen(QColor(33, 150, 243), 3))
            
            # Crear rect para el arco
            arc_rect = QRect(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2
            )
            
            # Aplicar rotación
            painter.save()
            painter.translate(center)
            painter.rotate(self.rotation)
            painter.translate(-center.x(), -center.y())
            
            # Dibujar arco (120 grados)
            painter.drawArc(arc_rect, 0, 120 * 16)
            
            painter.restore()
            painter.end()
