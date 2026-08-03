"""
Diálogo para visualizar y gestionar adjuntos de pacientes.
Diseño Profesional: Sin emojis, iconos SVG vectoriales, estilo 'Clean'.
"""

import os
import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QAbstractItemView, QHeaderView,
    QGroupBox, QWidget, QLineEdit, QStyle, QApplication, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QSize, QByteArray
from PyQt5.QtGui import QIcon, QColor, QDragEnterEvent, QDropEvent, QDesktopServices, QPixmap, QPainter
from utils.archivo_adjuntos import GestorAdjuntos

# =============================================================================
# DEFINICIÓN DE ICONOS SVG (Vectoriales para máxima calidad)
# =============================================================================
class SvgIcons:
    """Clase estática para proveer iconos SVG generados en código."""
    
    # Colores base
    COLOR_PRIMARY = "#0078d4"
    COLOR_DANGER = "#d13438"
    COLOR_TEXT = "#444444"
    COLOR_SUCCESS = "#107c10"

    @staticmethod
    def get_icon(name, color=None):
        if color is None: color = SvgIcons.COLOR_TEXT
        
        # Diccionario de rutas SVG (Paths)
        paths = {
            'pdf': "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
            'image': "M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z",
            'file': "M6 2c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6H6zm7 7V3.5L18.5 9H13z",
            'eye': "M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z",
            'download': "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
            'trash': "M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z",
            'search': "M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z",
            'add': "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z",
            'folder': "M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"
        }
        
        path = paths.get(name, paths['file'])
        
        # Construir SVG XML
        svg_xml = f"""
        <svg viewBox="0 0 24 24" width="24" height="24" xmlns="http://www.w3.org/2000/svg">
            <path d="{path}" fill="{color}"/>
        </svg>
        """
        
        # Convertir a QIcon
        pm = QPixmap()
        pm.loadFromData(QByteArray(svg_xml.encode('utf-8')))
        return QIcon(pm)

# =============================================================================
# DIÁLOGO PRINCIPAL
# =============================================================================
class GestorAdjuntosDialog(QDialog):
    
    adjuntos_actualizados = pyqtSignal()
    
    def __init__(self, paciente_dni: str, paciente_nombre: str = "", paciente_data: dict = None, parent=None):
        super().__init__(parent)
        self.paciente_dni = paciente_dni
        self.paciente_nombre = paciente_nombre
        self.paciente_data = paciente_data or {}
        self.gestor = GestorAdjuntos()
        
        # Configuración Ventana
        self.setWindowTitle(f"Expediente Digital - {paciente_nombre}")
        self.resize(1050, 650)
        self.setWindowFlags(Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setAcceptDrops(True)
        
        self.setup_ui()
        self.cargar_adjuntos()
    
    def setup_ui(self):
        """Construye la interfaz con un diseño limpio y moderno."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.aplicar_estilos()

        # --- HEADER (Barra Superior) ---
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Icono Grande + Información del Paciente
        lbl_icon = QLabel()
        lbl_icon.setPixmap(SvgIcons.get_icon('folder', SvgIcons.COLOR_PRIMARY).pixmap(40, 40))
        
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(10, 0, 0, 0)
        info_layout.setSpacing(3)
        
        # Nombre en grande
        lbl_nombre = QLabel(self.paciente_nombre)
        lbl_nombre.setObjectName("headerTitle")
        lbl_nombre.setStyleSheet("font-size: 16px; font-weight: bold; color: #111827;")
        
        # Detalles en una fila
        detalles_layout = QHBoxLayout()
        detalles_layout.setSpacing(20)
        detalles_layout.setContentsMargins(0, 0, 0, 0)
        
        # DNI
        lbl_dni = QLabel(f"DNI: {self.paciente_dni}")
        lbl_dni.setStyleSheet("color: #6b7280; font-size: 12px;")
        
        # Edad
        edad = self.paciente_data.get('edad', 'N/A')
        lbl_edad = QLabel(f"Edad: {edad} años" if edad and edad != 'N/A' else "Edad: N/A")
        lbl_edad.setStyleSheet("color: #6b7280; font-size: 12px;")
        
        # Fecha de Nacimiento
        fecha_nac = self.paciente_data.get('fecha_nacimiento', 'N/A')
        if fecha_nac and fecha_nac != 'N/A':
            lbl_fecha_nac = QLabel(f"Nac: {fecha_nac}")
        else:
            lbl_fecha_nac = QLabel("Nac: N/A")
        lbl_fecha_nac.setStyleSheet("color: #6b7280; font-size: 12px;")
        
        # Última visita
        historial = self.paciente_data.get('historial_graduaciones', [])
        if historial:
            ultima_visita = historial[-1].get('fecha', 'N/A')
            lbl_ultima_visita = QLabel(f"Última visita: {ultima_visita}")
        else:
            lbl_ultima_visita = QLabel("Última visita: N/A")
        lbl_ultima_visita.setStyleSheet("color: #6b7280; font-size: 12px;")
        
        detalles_layout.addWidget(lbl_dni)
        detalles_layout.addWidget(lbl_edad)
        detalles_layout.addWidget(lbl_fecha_nac)
        detalles_layout.addWidget(lbl_ultima_visita)
        detalles_layout.addStretch()
        
        info_layout.addWidget(lbl_nombre)
        info_layout.addLayout(detalles_layout)
        
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(info_container)
        header_layout.addStretch()
        
        # Buscador en el Header
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar documento...")
        self.txt_buscar.setFixedWidth(280)
        # Añadir icono de lupa dentro del lineEdit (acción visual)
        self.txt_buscar.addAction(SvgIcons.get_icon('search', '#999'), QLineEdit.LeadingPosition)
        self.txt_buscar.textChanged.connect(self.filtrar_tabla)
        
        header_layout.addWidget(self.txt_buscar)
        
        layout.addWidget(header_frame)

        # --- CONTENIDO PRINCIPAL ---
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        # Barra de Herramientas
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        
        btn_pdf = self.crear_boton_toolbar("Adjuntar PDF", 'pdf', self.adjuntar_pdf)
        btn_foto = self.crear_boton_toolbar("Adjuntar Imagen", 'image', self.adjuntar_foto)
        btn_otro = self.crear_boton_toolbar("Otros Archivos", 'add', self.adjuntar_otro)
        
        toolbar_layout.addWidget(btn_pdf)
        toolbar_layout.addWidget(btn_foto)
        toolbar_layout.addWidget(btn_otro)
        
        # Label Drag & Drop discreto
        lbl_drag = QLabel("Arrastre archivos aquí para adjuntar")
        lbl_drag.setStyleSheet("color: #888; font-style: italic; font-size: 12px; margin-left: 10px;")
        toolbar_layout.addWidget(lbl_drag)
        toolbar_layout.addStretch()
        
        content_layout.addLayout(toolbar_layout)

        # Tabla
        self.tabla_adjuntos = QTableWidget()
        self.tabla_adjuntos.setColumnCount(5)
        self.tabla_adjuntos.setHorizontalHeaderLabels(["Nombre del Archivo", "Tipo", "Tamaño", "Fecha", ""])
        self.tabla_adjuntos.setFocusPolicy(Qt.NoFocus)
        self.tabla_adjuntos.setShowGrid(False)
        self.tabla_adjuntos.setAlternatingRowColors(True)
        self.tabla_adjuntos.verticalHeader().setVisible(False)
        self.tabla_adjuntos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_adjuntos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Configurar anchos de columna
        header = self.tabla_adjuntos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.tabla_adjuntos.setColumnWidth(4, 120) # Ancho fijo para acciones
        
        content_layout.addWidget(self.tabla_adjuntos)

        # Footer de Estadísticas
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("statsFrame")
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(15, 10, 15, 10)
        
        self.lbl_stats_total = QLabel("0 Archivos")
        self.lbl_stats_size = QLabel("0 MB")
        self.lbl_stats_total.setStyleSheet("font-weight: bold; color: #333;")
        
        stats_layout.addWidget(QLabel("Resumen:"))
        stats_layout.addWidget(self.lbl_stats_total)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.lbl_stats_size)
        stats_layout.addStretch()
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedWidth(100)
        btn_cerrar.clicked.connect(self.close)
        stats_layout.addWidget(btn_cerrar)
        
        content_layout.addWidget(self.stats_frame)
        
        layout.addLayout(content_layout)

    def aplicar_estilos(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f3f4f6;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame#headerFrame {
                background-color: white;
                border-bottom: 1px solid #e5e7eb;
            }
            QLabel#headerTitle {
                font-size: 18px;
                font-weight: bold;
                color: #111827;
            }
            QLabel#headerSub {
                font-size: 13px;
                color: #6b7280;
            }
            QPushButton {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
                color: #374151;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                border-color: #9ca3af;
            }
            QPushButton:pressed {
                background-color: #f3f4f6;
            }
            QLineEdit {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px 8px 8px 30px; /* Padding izquierdo para el icono */
                background-color: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
            QTableWidget {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                background-color: white;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f3f4f6;
                color: #374151;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                font-weight: 600;
                color: #4b5563;
                text-transform: uppercase;
                font-size: 11px;
            }
            QFrame#statsFrame {
                background-color: #e5e7eb;
                border-radius: 6px;
            }
        """)

    def crear_boton_toolbar(self, texto, icono_nombre, slot):
        btn = QPushButton(f"  {texto}")
        btn.setIcon(SvgIcons.get_icon(icono_nombre, SvgIcons.COLOR_PRIMARY))
        btn.setIconSize(QSize(18, 18))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(slot)
        return btn

    # --- LÓGICA DRAG & DROP ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        archivos = [u.toLocalFile() for u in event.mimeData().urls()]
        if archivos:
            self.procesar_archivos(archivos)

    # --- DATOS Y TABLA ---
    def cargar_adjuntos(self):
        self.lista_adjuntos_cache = self.gestor.obtener_adjuntos(self.paciente_dni, self.paciente_nombre)
        self.filtrar_tabla()
        self.actualizar_estadisticas()

    def filtrar_tabla(self):
        texto = self.txt_buscar.text().lower()
        if not texto:
            datos = self.lista_adjuntos_cache
        else:
            datos = [a for a in self.lista_adjuntos_cache if texto in a.get('nombre_original', '').lower()]
        self.poblar_tabla(datos)

    def poblar_tabla(self, datos):
        self.tabla_adjuntos.setRowCount(0)
        self.tabla_adjuntos.setRowCount(len(datos))
        
        for row, adj in enumerate(datos):
            # 1. Icono y Nombre
            tipo = adj.get('tipo', 'OTRO')
            if 'PDF' in tipo:
                icon = SvgIcons.get_icon('pdf', '#d13438') # Rojo para PDF
            elif 'FOTO' in tipo:
                icon = SvgIcons.get_icon('image', '#0078d4') # Azul para Fotos
            else:
                icon = SvgIcons.get_icon('file', '#666')

            item_nombre = QTableWidgetItem(icon, adj.get('nombre_original', ''))
            self.tabla_adjuntos.setItem(row, 0, item_nombre)
            
            # 2. Tipo (Texto discreto)
            item_tipo = QTableWidgetItem(tipo)
            item_tipo.setForeground(QColor("#6b7280"))
            self.tabla_adjuntos.setItem(row, 1, item_tipo)
            
            # 3. Tamaño
            tam = adj.get('tamaño', 0) / (1024 * 1024)
            item_tam = QTableWidgetItem(f"{tam:.2f} MB")
            item_tam.setTextAlignment(Qt.AlignCenter)
            self.tabla_adjuntos.setItem(row, 2, item_tam)
            
            # 4. Fecha
            fecha = adj.get('fecha_adjunto', '').split('T')[0]
            self.tabla_adjuntos.setItem(row, 3, QTableWidgetItem(fecha))
            
            # 5. Acciones (Botones solo iconos)
            widget_acc = QWidget()
            layout_acc = QHBoxLayout(widget_acc)
            layout_acc.setContentsMargins(0, 0, 0, 0)
            layout_acc.setSpacing(4)
            layout_acc.setAlignment(Qt.AlignCenter)
            
            # Botón Ver
            btn_ver = self.crear_boton_accion('eye', 'Abrir', lambda _, r=row: self.abrir_adjunto(r, datos))
            btn_ver.setStyleSheet("QPushButton:hover { background-color: #e0f2fe; border: 1px solid #7dd3fc; }")
            
            # Botón Descargar
            btn_down = self.crear_boton_accion('download', 'Descargar', lambda _, r=row: self.descargar_adjunto(r, datos))
            
            # Botón Eliminar
            btn_del = self.crear_boton_accion('trash', 'Eliminar', lambda _, r=row: self.eliminar_adjunto(r, datos))
            # Estilo especial para borrar (hover rojo)
            btn_del.setStyleSheet("QPushButton:hover { background-color: #fef2f2; border: 1px solid #fecaca; } polygon { fill: red; }")

            layout_acc.addWidget(btn_ver)
            layout_acc.addWidget(btn_down)
            layout_acc.addWidget(btn_del)
            
            self.tabla_adjuntos.setCellWidget(row, 4, widget_acc)

    def crear_boton_accion(self, icon_name, tooltip, callback):
        """Crea botones pequeños y limpios para la tabla."""
        btn = QPushButton()
        # Usamos un color gris oscuro para el estado normal
        btn.setIcon(SvgIcons.get_icon(icon_name, "#4b5563"))
        btn.setToolTip(tooltip)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        # Quitar bordes por defecto para que se vea limpio en la tabla
        btn.setStyleSheet("border: none; background: transparent; border-radius: 4px;")
        btn.clicked.connect(callback)
        return btn

    def actualizar_estadisticas(self):
        stats = self.gestor.obtener_estadisticas(self.paciente_dni, self.paciente_nombre)
        self.lbl_stats_total.setText(f"{stats.get('total_archivos', 0)} Archivos")
        self.lbl_stats_size.setText(f"{stats.get('total_tamaño_mb', 0):.2f} MB utilizados")

    # --- WRAPPERS DE ACCIONES ---
    def adjuntar_pdf(self): self.adjuntar_dialogo('PDF')
    def adjuntar_foto(self): self.adjuntar_dialogo('FOTO')
    def adjuntar_otro(self): self.adjuntar_dialogo('OTRO')

    def adjuntar_dialogo(self, tipo):
        filtros = {
            'PDF': "Documentos PDF (*.pdf)",
            'FOTO': "Imágenes (*.jpg *.png *.jpeg *.bmp)",
            'OTRO': "Todos los archivos (*.*)"
        }
        rutas, _ = QFileDialog.getOpenFileNames(self, f"Seleccionar {tipo}", "", filtros.get(tipo))
        if rutas:
            self.procesar_archivos(rutas)

    def procesar_archivos(self, rutas):
        errs = []
        for ruta in rutas:
            try:
                self.gestor.adjuntar_archivo(self.paciente_dni, ruta, self.paciente_nombre)
            except Exception as e:
                errs.append(f"{os.path.basename(ruta)}: {str(e)}")
        
        if errs:
            QMessageBox.warning(self, "Errores al adjuntar", "\n".join(errs))
        
        self.cargar_adjuntos()
        self.adjuntos_actualizados.emit()

    def abrir_adjunto(self, row, datos):
        adj = datos[row]
        ruta = adj.get('ruta', '')
        if os.path.exists(ruta):
            QDesktopServices.openUrl(QUrl.fromLocalFile(ruta))
        else:
            QMessageBox.warning(self, "Error", "Archivo no encontrado.")

    def descargar_adjunto(self, row, datos):
        adj = datos[row]
        destino, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", adj.get('nombre_original'))
        if destino:
            try:
                self.gestor.descargar_adjunto(self.paciente_dni, adj.get('nombre_almacenado'), destino, self.paciente_nombre)
                QMessageBox.information(self, "Éxito", "Descarga completada.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def eliminar_adjunto(self, row, datos):
        adj = datos[row]
        res = QMessageBox.question(self, "Confirmar", f"¿Eliminar '{adj.get('nombre_original')}'?", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            try:
                self.gestor.eliminar_adjunto(self.paciente_dni, adj.get('nombre_almacenado'), self.paciente_nombre)
                self.cargar_adjuntos()
                self.adjuntos_actualizados.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

# Para pruebas rápidas
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Mock para testing visual sin backend
    class GestorMock:
        def obtener_adjuntos(self, d, n): 
            return [
                {'nombre_original': 'Analisis_Sangre.pdf', 'tipo': 'DOCUMENTO PDF', 'tamaño': 1024*500, 'fecha_adjunto': '2023-10-25', 'ruta': ''},
                {'nombre_original': 'Radiografia_Torax.jpg', 'tipo': 'FOTO IMG', 'tamaño': 1024*2500, 'fecha_adjunto': '2023-10-26', 'ruta': ''},
            ]
        def obtener_estadisticas(self, d, n): return {'total_archivos': 2, 'total_tamaño_mb': 3.5}
    
    GestorAdjuntosDialog.gestor = GestorMock() # Inyeccion de dependencia falsa
    
    dlg = GestorAdjuntosDialog("87654321", "Maria Gonzales")
    dlg.show()
    sys.exit(app.exec_())