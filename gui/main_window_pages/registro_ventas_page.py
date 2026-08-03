import sys
import os
import json
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QHeaderView,
    QAbstractItemView, QTableWidgetItem, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer

# Importaciones para manejo de archivos
from utils.file_handler import (
    VISO_DIR,
    open_pdf_with_chrome,
    get_user_file_path,
    cargar_nombre_optica,
    cargar_ruc,
    cargar_ventas,
    guardar_ventas,
)
from utils.generador_boletas_plantilla import GeneradorBoletasPlantilla

class RegistroVentasPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.username = parent.username
        self.setObjectName("MainContent")
        self.setup_ui()
        self.load_ventas()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("<h1>Historial de Ventas</h1>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Tabla de ventas
        self.ventas_table = QTableWidget()
        self.ventas_table.setColumnCount(6)
        self.ventas_table.setHorizontalHeaderLabels(["ID Venta", "Fecha", "Total", "Productos", "Boleta", "Eliminar"])
        self.ventas_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ventas_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ventas_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ventas_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f5f5f5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #191919;
                color: white;
                padding: 8px;
                border: none;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.ventas_table)

    def _render_svg_to_pixmap(self, svg_data, size=20):
        """Convierte SVG a QPixmap."""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(255, 255, 255, 0))
        painter = QPainter(pixmap)
        renderer = QSvgRenderer()
        renderer.load(svg_data.encode())
        renderer.render(painter)
        painter.end()
        return pixmap

    def load_ventas(self):
        """Carga todas las ventas registradas."""
        self.ventas_table.setRowCount(0)
        
        try:
            ventas = cargar_ventas(self.username) or []
            if not isinstance(ventas, list) or not ventas:
                self.ventas_table.insertRow(0)
                item = QTableWidgetItem("No hay ventas registradas")
                item.setForeground(QColor(150, 150, 150))
                self.ventas_table.setItem(0, 0, item)
                return
            
            for idx, venta in enumerate(ventas):
                self.ventas_table.insertRow(idx)
                
                # ID Venta
                id_item = QTableWidgetItem(venta.get('id', ''))
                self.ventas_table.setItem(idx, 0, id_item)
                
                # Fecha
                fecha_item = QTableWidgetItem(venta.get('fecha', ''))
                self.ventas_table.setItem(idx, 1, fecha_item)
                
                # Total
                total = venta.get('total', 0)
                total_item = QTableWidgetItem(f"S/ {total:.2f}")
                self.ventas_table.setItem(idx, 2, total_item)
                
                # Cantidad de productos
                cantidad_items = len(venta.get('items', []))
                productos_item = QTableWidgetItem(str(cantidad_items))
                self.ventas_table.setItem(idx, 3, productos_item)
                
                # Botón de generar PDF con ícono SVG
                btn_generar = QPushButton()
                btn_generar.setText("")
                
                # SVG ícono de documento
                svg_icon = """
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
                    <path fill="#191919" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-8-6z"/>
                    <line x1="8" y1="12" x2="16" y2="12" stroke="white" stroke-width="1.5"/>
                    <line x1="8" y1="15" x2="16" y2="15" stroke="white" stroke-width="1.5"/>
                    <line x1="8" y1="18" x2="13" y2="18" stroke="white" stroke-width="1.5"/>
                </svg>
                """
                
                pixmap = self._render_svg_to_pixmap(svg_icon)
                btn_generar.setIcon(QIcon(pixmap))
                btn_generar.setIconSize(QSize(20, 20))
                btn_generar.setFixedSize(32, 32)
                btn_generar.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                        border-radius: 4px;
                    }
                    QPushButton:pressed {
                        background-color: #e0e0e0;
                    }
                """)
                btn_generar.clicked.connect(lambda checked, v=venta: self.generar_boleta_venta(v))
                
                # Contenedor para centrar el botón
                container = QWidget()
                container_layout = QHBoxLayout(container)
                container_layout.addStretch()
                container_layout.addWidget(btn_generar)
                container_layout.addStretch()
                container_layout.setContentsMargins(0, 0, 0, 0)
                
                self.ventas_table.setCellWidget(idx, 4, container)
                
                # Botón de eliminar con ícono SVG
                btn_eliminar = QPushButton()
                btn_eliminar.setText("")
                
                # SVG ícono de papelera
                svg_trash = """
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
                    <path fill="#d32f2f" d="M19 6.4V19a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6.4M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M4 6h16M10 11v6M14 11v6"/>
                </svg>
                """
                
                pixmap_trash = self._render_svg_to_pixmap(svg_trash)
                btn_eliminar.setIcon(QIcon(pixmap_trash))
                btn_eliminar.setIconSize(QSize(20, 20))
                btn_eliminar.setFixedSize(32, 32)
                btn_eliminar.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #ffebee;
                        border-radius: 4px;
                    }
                    QPushButton:pressed {
                        background-color: #ffcdd2;
                    }
                """)
                btn_eliminar.clicked.connect(lambda checked, v=venta: self.eliminar_venta(v))
                
                # Contenedor para centrar el botón de eliminar
                container_eliminar = QWidget()
                container_eliminar_layout = QHBoxLayout(container_eliminar)
                container_eliminar_layout.addStretch()
                container_eliminar_layout.addWidget(btn_eliminar)
                container_eliminar_layout.addStretch()
                container_eliminar_layout.setContentsMargins(0, 0, 0, 0)
                
                self.ventas_table.setCellWidget(idx, 5, container_eliminar)
                
        except Exception as e:
            print(f"[ERROR] Error cargando ventas: {str(e)}")
            self.ventas_table.insertRow(0)
            item = QTableWidgetItem(f"Error: {str(e)}")
            item.setForeground(QColor(255, 0, 0))
            self.ventas_table.setItem(0, 0, item)


    def generar_boleta_venta(self, venta):
        """Genera la boleta PDF para una venta específica usando la plantilla seleccionada."""
        try:
            # Crear generador con plantilla seleccionada
            generador = GeneradorBoletasPlantilla(self.username)
            
            # Preparar datos de la boleta
            productos = []
            
            # Usar los items de la venta
            for item in venta.get('items', []):
                # Intentar obtener el nombre del producto de varias claves posibles
                nombre_p = str(item.get('producto') or item.get('nombre') or 'Producto').strip()
                precio_u = float(item.get('precio_unitario', item.get('precio', 0)) or 0)
                subtotal_item = float(item.get('subtotal', item.get('total', precio_u)) or 0)
                
                productos.append({
                    'nombre': nombre_p,
                    'cantidad': int(item.get('cantidad', 1) or 1),
                    'precio': precio_u,
                    'total': subtotal_item
                })
            
            # USAR LOS VALORES YA ALMACENADOS PARA EVITAR INFLACIÓN POR IGV
            total = float(venta.get('total', 0) or 0)
            subtotal = float(venta.get('subtotal', total / 1.18) or 0)
            igv = float(venta.get('igv', total - subtotal) or 0)

            nombre_optica = cargar_nombre_optica(self.username)
            ruc_empresa = cargar_ruc(self.username)
            
            # Datos para la boleta
            datos_boleta = {
                'nombre_optica': nombre_optica,
                'ruc': ruc_empresa,
                'ruc_empresa': ruc_empresa,
                'direccion': 'Dirección no configurada',
                'numero_boleta': str(venta.get('id', 'S/N')),
                'fecha': venta.get('fecha', ''),
                'cliente': str(venta.get('paciente_nombre') or venta.get('cliente') or 'Cliente General'),
                'productos': productos,
                'subtotal': subtotal,
                'igv': igv,
                'total': total,
                'metodo_pago': str(venta.get('metodo_pago', 'Efectivo')),
                'pie_pagina': 'Gracias por su compra',
                'vendedor': str(venta.get('vendedor') or nombre_optica)
            }
            
            # Generar boleta con la plantilla seleccionada
            pdf_path = generador.generar_boleta(datos_boleta)
            
            # Abrir la boleta generada
            if os.path.exists(pdf_path):
                open_pdf_with_chrome(pdf_path)
                QMessageBox.information(self, "Éxito", "Boleta generada exitosamente.")
            else:
                QMessageBox.warning(self, "Advertencia", "No se pudo generar la boleta.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar la boleta: {str(e)}")

    def refresh_table(self):
        """Recarga la tabla de ventas."""
        self.load_ventas()

    def eliminar_venta(self, venta):
        """Elimina un registro de venta después de confirmar."""
        try:
            # Solicitar confirmación
            reply = QMessageBox.question(
                self,
                "Confirmar eliminación",
                f"¿Está seguro que desea eliminar la venta {venta.get('id', '')} del {venta.get('fecha', '')}?\n\nEsta acción no se puede deshacer.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Cargar el archivo de ventas
            ventas = cargar_ventas(self.username) or []
            
            if not isinstance(ventas, list) or not ventas:
                QMessageBox.warning(self, "Error", "No se encontró el archivo de ventas.")
                return
            
            # Leer todas las ventas
            
            # Filtrar la venta que se desea eliminar
            venta_id = venta.get('id', '')
            ventas_filtradas = [v for v in ventas if v.get('id', '') != venta_id]
            
            # Si la cantidad de ventas no cambió, significa que no se encontró
            if len(ventas) == len(ventas_filtradas):
                QMessageBox.warning(self, "Error", "No se pudo encontrar la venta para eliminar.")
                return
            
            from utils.trash_manager import move_to_trash

            move_to_trash(
                self.username,
                "ventas",
                venta,
                source="registro_ventas_page.delete",
                extra={"stock_adjusted_on_delete": False},
            )

            # Guardar el archivo actualizado
            guardar_ventas(self.username, ventas_filtradas)
            
            # Recargar la tabla
            self.load_ventas()
            
            QMessageBox.information(
                self,
                "Éxito",
                f"Venta {venta_id} eliminada correctamente."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al eliminar la venta: {str(e)}"
            )
