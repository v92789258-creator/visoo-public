from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtCore import Qt, QTimer
import ctypes
import sys


class DraggableTitleBar(QtWidgets.QWidget):
    """Barra de título personalizada y movible con botones de control."""
    def __init__(self, title, parent_dialog):
        super().__init__()
        self.parent_dialog = parent_dialog
        self.is_dragging = False
        self.drag_start_pos = None
        self.is_maximized = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # Crear el label del título
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        title_label.setCursor(QtCore.Qt.OpenHandCursor)
        
        layout.addWidget(title_label)
        layout.addStretch()
        
        # Botón Minimizar
        self.btn_minimize = QPushButton("−")
        self.btn_minimize.setMaximumWidth(40)
        self.btn_minimize.setMaximumHeight(32)
        self.btn_minimize.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 2px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.btn_minimize.clicked.connect(self._minimize)
        layout.addWidget(self.btn_minimize)
        
        # Botón Maximizar/Restaurar
        self.btn_maximize = QPushButton("□")
        self.btn_maximize.setMaximumWidth(40)
        self.btn_maximize.setMaximumHeight(32)
        self.btn_maximize.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 2px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.btn_maximize.clicked.connect(self._maximize)
        layout.addWidget(self.btn_maximize)
        
        # Botón Cerrar
        self.btn_close = QPushButton("✕")
        self.btn_close.setMaximumWidth(40)
        self.btn_close.setMaximumHeight(32)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 2px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E81123;
            }
        """)
        self.btn_close.clicked.connect(self._close)
        layout.addWidget(self.btn_close)
        
        # Estilo de la barra de título - Azul nativo Windows
        self.setStyleSheet("""
            QWidget {
                background-color: #0078D4;
                border-radius: 0px;
            }
        """)
        self.setMinimumHeight(32)
    
    def _minimize(self):
        """Minimiza la ventana."""
        self.parent_dialog.showMinimized()
    
    def _maximize(self):
        """Alterna entre maximizar y restaurar."""
        if self.is_maximized:
            self.parent_dialog.showNormal()
            self.btn_maximize.setText("□")
            self.is_maximized = False
        else:
            self.parent_dialog.showMaximized()
            self.btn_maximize.setText("❐")
            self.is_maximized = True
    
    def _close(self):
        """Cierra la ventana."""
        self.parent_dialog.close()
        
    def mousePressEvent(self, event: QMouseEvent):
        """Detecta clicks para arrastre."""
        # Solo permitir arrastre si se hace clic en el área del título (no en los botones)
        if event.button() == Qt.LeftButton and event.x() < 300:
            self.is_dragging = True
            self.drag_start_pos = event.globalPos() - self.parent_dialog.frameGeometry().topLeft()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        """Maneja el arrastre de la ventana y snap a bordes."""
        if self.is_dragging and self.drag_start_pos:
            new_pos = event.globalPos() - self.drag_start_pos
            global_pos = event.globalPos()
            
            # Si el cursor llega al top (y=0), activar menú de Windows para snap/maximize/redimensionar
            if global_pos.y() <= 0:
                try:
                    # Liberar el grab del mouse
                    QtWidgets.QApplication.instance().restoreOverrideCursor()
                    
                    # Obtener el handle de la ventana
                    hwnd = int(self.parent_dialog.winId())
                    
                    # Liberar el capture
                    ctypes.windll.user32.ReleaseCapture()
                    
                    # Enviar mensaje de Windows para activar el resize desde la barra de título
                    # WM_NCLBUTTONDOWN = 0xA1, HTCAPTION = 2
                    ctypes.windll.user32.SendMessageW(hwnd, 0xA1, 2, 0)
                    
                    # Detener el arrastre
                    self.is_dragging = False
                    self.drag_start_pos = None
                except Exception as e:
                    pass
                return
            
            # Mover la ventana normalmente si no está en el top
            self.parent_dialog.move(new_pos)
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Detiene el arrastre."""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.drag_start_pos = None
