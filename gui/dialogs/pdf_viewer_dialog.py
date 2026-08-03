"""
Diálogo para visualizar PDFs dentro de la aplicación VISO.
"""

import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QMessageBox
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

class PDFViewerDialog(QDialog):
    """Diálogo para visualizar y interactuar con PDFs."""
    
    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 100
        
        self.setWindowTitle("Vista Previa de Boleta")
        self.setModal(True)
        self.setMinimumSize(600, 700)
        
        self.setup_ui()
        self.load_pdf()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Encabezado
        header_layout = QHBoxLayout()
        title = QLabel("Vista Previa de Boleta")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Área para mostrar el PDF
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: #f0f0f0;
                border: 1px solid #ddd;
            }
        """)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: white; padding: 10px;")
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        # Barra de navegación
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)
        
        self.btn_prev = QPushButton("◀ Anterior")
        self.btn_prev.setMaximumWidth(100)
        self.btn_prev.clicked.connect(self.previous_page)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-size: 10px;
            }
            QPushButton:hover { background: #5c636a; }
            QPushButton:pressed { background: #4c545d; }
            QPushButton:disabled { background: #c3c6cb; }
        """)
        nav_layout.addWidget(self.btn_prev)
        
        # Indicador de página
        self.page_label = QLabel("Página 1 de 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; color: #495057;")
        nav_layout.addWidget(self.page_label)
        
        self.btn_next = QPushButton("Siguiente ▶")
        self.btn_next.setMaximumWidth(100)
        self.btn_next.clicked.connect(self.next_page)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-size: 10px;
            }
            QPushButton:hover { background: #5c636a; }
            QPushButton:pressed { background: #4c545d; }
            QPushButton:disabled { background: #c3c6cb; }
        """)
        nav_layout.addWidget(self.btn_next)
        
        layout.addLayout(nav_layout)
        
        # Barra de herramientas
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(8)
        
        btn_zoom_out = QPushButton("🔍−")
        btn_zoom_out.setMaximumWidth(50)
        btn_zoom_out.clicked.connect(self.zoom_out)
        btn_zoom_out.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover { background: #0056b3; }
        """)
        tools_layout.addWidget(btn_zoom_out)
        
        btn_zoom_in = QPushButton("🔍+")
        btn_zoom_in.setMaximumWidth(50)
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_in.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover { background: #0056b3; }
        """)
        tools_layout.addWidget(btn_zoom_in)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setStyleSheet("font-size: 10px; color: #666; min-width: 40px;")
        tools_layout.addWidget(self.zoom_label)
        
        tools_layout.addStretch()
        
        layout.addLayout(tools_layout)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        btn_descargar = QPushButton("💾 Descargar")
        btn_descargar.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5c636a; }
        """)
        btn_descargar.clicked.connect(self.download_pdf)
        buttons_layout.addWidget(btn_descargar)
        
        btn_imprimir = QPushButton("🖨️ Imprimir")
        btn_imprimir.setStyleSheet("""
            QPushButton {
                background: #198754;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #157347; }
        """)
        btn_imprimir.clicked.connect(self.print_pdf)
        buttons_layout.addWidget(btn_imprimir)
        
        btn_abrir_navegador = QPushButton("🌐 Abrir en Navegador")
        btn_abrir_navegador.setStyleSheet("""
            QPushButton {
                background: #0d6efd;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #0b5ed7; }
        """)
        btn_abrir_navegador.clicked.connect(self.open_in_browser)
        buttons_layout.addWidget(btn_abrir_navegador)
        
        buttons_layout.addStretch()
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background: #e9ecef;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #dee2e6; }
        """)
        btn_cerrar.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_cerrar)
        
        layout.addLayout(buttons_layout)
    
    def load_pdf(self):
        """Carga el PDF."""
        try:
            if not os.path.exists(self.pdf_path):
                QMessageBox.critical(self, "Error", f"Archivo no encontrado:\n{self.pdf_path}")
                return
            if fitz is None:
                QMessageBox.critical(
                    self,
                    "PDF no disponible",
                    "Esta compilacion fue generada sin el modulo PDF (PyMuPDF).",
                )
                return
            
            self.pdf_document = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_document)
            self.current_page = 0
            
            self.update_page_display()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el PDF:\n{e}")
    
    def update_page_display(self):
        """Actualiza la visualización de la página actual."""
        if fitz is None or not self.pdf_document or self.current_page >= self.total_pages:
            return
        
        try:
            # Renderizar página a imagen
            page = self.pdf_document[self.current_page]
            
            # Calcular zoom
            zoom_factor = self.zoom_level / 100.0
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convertir a QPixmap
            img_data = pix.tobytes("ppm")
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            
            # Mostrar en label
            self.image_label.setPixmap(pixmap)
            
            # Actualizar etiqueta de página
            self.page_label.setText(f"Página {self.current_page + 1} de {self.total_pages}")
            
            # Habilitar/deshabilitar botones
            self.btn_prev.setEnabled(self.current_page > 0)
            self.btn_next.setEnabled(self.current_page < self.total_pages - 1)
            
            # Actualizar zoom label
            self.zoom_label.setText(f"{self.zoom_level}%")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al renderizar página:\n{e}")
    
    def next_page(self):
        """Ir a la siguiente página."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_display()
    
    def previous_page(self):
        """Ir a la página anterior."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_display()
    
    def zoom_in(self):
        """Aumentar zoom."""
        if self.zoom_level < 300:
            self.zoom_level += 25
            self.update_page_display()
    
    def zoom_out(self):
        """Reducir zoom."""
        if self.zoom_level > 50:
            self.zoom_level -= 25
            self.update_page_display()
    
    def download_pdf(self):
        """Descarga el PDF a la carpeta de descargas."""
        try:
            import shutil
            from pathlib import Path
            
            downloads_dir = Path.home() / "Downloads"
            filename = os.path.basename(self.pdf_path)
            dest_path = downloads_dir / filename
            
            shutil.copy2(self.pdf_path, dest_path)
            
            QMessageBox.information(
                self,
                "Éxito",
                f"Boleta descargada en:\n{dest_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al descargar:\n{e}")
    
    def print_pdf(self):
        """Imprime el PDF."""
        from utils.printer_handler import find_available_printers
        from gui.dialogs.printer_selection_dialog import PrinterSelectionDialog
        
        try:
            # Mostrar diálogo de selección de impresora
            printer_dialog = PrinterSelectionDialog(self)
            if printer_dialog.exec_() != QDialog.Accepted:
                return
            
            printer_name = printer_dialog.get_selected_printer()
            if not printer_name:
                QMessageBox.warning(self, "Error", "Por favor selecciona una impresora")
                return
            
            # Importar handler de impresión
            from utils.printer_handler import print_boleta
            
            success, message = print_boleta(self.pdf_path, printer_name)
            
            if success:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Boleta enviada a la impresora\n{message}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo imprimir:\n{message}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al imprimir:\n{e}")
    
    def open_in_browser(self):
        """Abre el PDF en el navegador seleccionado."""
        try:
            from gui.dialogs.browser_selection_dialog import BrowserSelectionDialog
            
            # Mostrar diálogo de selección de navegador
            browser_dialog = BrowserSelectionDialog(self)
            if browser_dialog.exec_() != QDialog.Accepted:
                return
            
            browser_path = browser_dialog.get_selected_browser()
            if not browser_path:
                QMessageBox.warning(self, "Error", "Por favor selecciona un navegador")
                return
            
            # Abrir PDF en navegador
            import subprocess
            subprocess.Popen([browser_path, self.pdf_path])
            
            QMessageBox.information(
                self,
                "Éxito",
                f"PDF abierto en navegador"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir en navegador:\n{e}")
    
    def closeEvent(self, event):
        """Cerrar el documento al cerrar el diálogo."""
        if self.pdf_document:
            self.pdf_document.close()
        event.accept()
