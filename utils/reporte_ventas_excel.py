"""
Generador de Reportes de Ventas en Excel.
Crea reportes detallados de ventas en dos formatos: con diseño o sin diseño.
"""

import os
import sys
import datetime
import subprocess
import platform
from pathlib import Path

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False


def generar_reporte_ventas_excel(username, ventas_data=None, con_diseño=True):
    """
    Genera un reporte de ventas en formato Excel.
    
    Args:
        username: Nombre de usuario
        ventas_data: Lista de ventas (opcional, si es None carga del archivo)
        con_diseño: Si True genera con diseño bonito, si False genera simple
    
    Returns:
        Tupla (éxito: bool, ruta_archivo: str, mensaje: str)
    """
    
    if not HAS_XLSXWRITER:
        return False, "", "Error: xlsxwriter no está instalado. Instálalo con: pip install xlsxwriter"
    
    try:
        # Crear directorio de reportes si no existe
        from utils.file_handler import get_user_file_path
        
        # Crear la carpeta de reportes
        reportes_dir = get_user_file_path(username, "reportes")
        os.makedirs(reportes_dir, exist_ok=True)
        
        # Si no se proporcionan datos, cargar del archivo
        if ventas_data is None:
            from utils.file_handler import cargar_ventas
            ventas_data = cargar_ventas(username)
        
        if not ventas_data:
            return False, "", "No hay datos de ventas para generar el reporte"
        
        # Crear nombre del archivo con timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tipo_diseño = "Diseño" if con_diseño else "Simple"
        filename = f"Reporte_Ventas_{tipo_diseño}_{timestamp}.xlsx"
        filepath = os.path.join(reportes_dir, filename)
        
        # Crear libro de Excel con xlsxwriter
        workbook = xlsxwriter.Workbook(filepath)
        worksheet = workbook.add_worksheet("Ventas")
        
        # Llamar al generador según el tipo de diseño
        if con_diseño:
            _generar_reporte_con_diseño(workbook, worksheet, ventas_data)
        else:
            _generar_reporte_simple(workbook, worksheet, ventas_data)
        
        workbook.close()
        
        # Abrir carpeta en explorador de archivos
        abrir_carpeta_explorador(filepath)
        
        return True, filepath, f"Reporte generado exitosamente: {filename}"
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, "", f"Error al generar reporte: {str(e)}"


def _generar_reporte_con_diseño(workbook, worksheet, ventas_data):
    """
    Genera un reporte con diseño profesional (Estilo Énfasis 1 Celeste) usando xlsxwriter.
    """
    # ========== DEFINIR FORMATOS ==========
    
    # Encabezado celeste
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#00B0D0',  # Celeste
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'font_size': 12,
        'text_wrap': True,
    })
    
    # Filas alternas - celeste suave
    data_format_alt = workbook.add_format({
        'font_size': 10,
        'font_color': '#333333',
        'bg_color': '#E0F2F1',  # Celeste muy suave
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    
    # Filas normales - blanco
    data_format = workbook.add_format({
        'font_size': 10,
        'font_color': '#333333',
        'bg_color': 'white',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    
    # Total con celeste
    total_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#00B0D0',  # Celeste igual al encabezado
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '"S/. "#,##0.00;"S/. "-#,##0.00',
    })
    
    # Verde para completada
    completada_format = workbook.add_format({
        'bold': True,
        'font_color': '#06640D',
        'bg_color': '#C6EFCE',  # Verde claro
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
    })
    
    # Amarillo para pendiente
    pendiente_format = workbook.add_format({
        'bold': True,
        'font_color': '#9C6500',
        'bg_color': '#FFEB9C',  # Amarillo suave
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
    })
    
    # Verde para métodos de pago
    pago_format = workbook.add_format({
        'font_size': 10,
        'font_color': '#333333',
        'bg_color': '#D4EDDA',  # Verde muy suave
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
    })
    
    # Moneda para subtotal, igv
    currency_format = workbook.add_format({
        'font_size': 10,
        'font_color': '#333333',
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '"S/. "#,##0.00;"S/. "-#,##0.00',
    })
    
    currency_format_alt = workbook.add_format({
        'font_size': 10,
        'font_color': '#333333',
        'bg_color': '#E0F2F1',
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '"S/. "#,##0.00;"S/. "-#,##0.00',
    })
    
    # Encabezados
    headers = [
        "Fecha", "DNI", "Paciente", "Optómetra",
        "Productos", "Subtotal", "IGV", "Total", "Pago", "Estado"
    ]
    
    # ========== ESCRIBIR ENCABEZADOS ==========
    
    for col_idx, header in enumerate(headers):
        worksheet.write(0, col_idx, header, header_format)
    
    worksheet.set_row(0, 28)  # Altura del encabezado
    
    # ========== ESCRIBIR DATOS ==========
    
    for row_idx, venta in enumerate(ventas_data, 1):
        is_even_row = (row_idx - 1) % 2 == 0
        row_format = data_format_alt if is_even_row else data_format
        row_currency_format = currency_format_alt if is_even_row else currency_format
        
        # Fecha
        worksheet.write(row_idx, 0, venta.get('fecha', ''), row_format)
        
        # DNI
        worksheet.write(row_idx, 1, venta.get('paciente_dni', ''), row_format)
        
        # Paciente
        worksheet.write(row_idx, 2, venta.get('paciente_nombre', ''), row_format)
        
        # Optómetra
        worksheet.write(row_idx, 3, venta.get('optometra', ''), row_format)
        
        # Productos
        items = venta.get('items', [])
        productos_texto = ", ".join([f"{item.get('producto', '')} (x{item.get('cantidad', 1)})" for item in items])
        worksheet.write(row_idx, 4, productos_texto, row_format)
        worksheet.set_row(row_idx, 25)  # Altura de filas de datos
        
        # Subtotal
        worksheet.write(row_idx, 5, venta.get('subtotal', 0), row_currency_format)
        
        # IGV
        worksheet.write(row_idx, 6, venta.get('impuesto', 0), row_currency_format)
        
        # Total - Celeste
        worksheet.write(row_idx, 7, venta.get('total', 0), total_format)
        
        # Método de pago
        metodo = venta.get('metodo_pago', 'No especificado')
        if metodo in ['Efectivo', 'Tarjeta', 'Transferencia']:
            worksheet.write(row_idx, 8, metodo, pago_format)
        else:
            worksheet.write(row_idx, 8, metodo, row_format)
        
        # Estado
        estado = venta.get('estado', 'Completada')
        if estado == 'Completada':
            worksheet.write(row_idx, 9, estado, completada_format)
        elif estado == 'Pendiente':
            worksheet.write(row_idx, 9, estado, pendiente_format)
        else:
            worksheet.write(row_idx, 9, estado, row_format)
    
    # ========== AJUSTES DE COLUMNAS ==========
    
    worksheet.set_column('A:A', 13)  # Fecha
    worksheet.set_column('B:B', 13)  # DNI
    worksheet.set_column('C:C', 22)  # Paciente
    worksheet.set_column('D:D', 16)  # Optómetra
    worksheet.set_column('E:E', 38)  # Productos
    worksheet.set_column('F:F', 14)  # Subtotal
    worksheet.set_column('G:G', 14)  # IGV
    worksheet.set_column('H:H', 14)  # Total
    worksheet.set_column('I:I', 14)  # Pago
    worksheet.set_column('J:J', 14)  # Estado
    
    # Congelar primera fila
    worksheet.freeze_panes(1, 0)


def _generar_reporte_simple(workbook, worksheet, ventas_data):
    """
    Genera un reporte simple sin estilos especiales usando xlsxwriter.
    """
    # Formato para encabezados
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
    })
    
    # Formato para datos
    data_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    
    # Formato para números
    currency_format = workbook.add_format({
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '"S/. "#,##0.00;"S/. "-#,##0.00',
    })
    
    # Encabezados
    headers = [
        "Fecha", "DNI", "Paciente", "Optómetra",
        "Productos", "Subtotal", "IGV", "Total", "Pago", "Estado"
    ]
    
    # Escribir encabezados
    for col_idx, header in enumerate(headers):
        worksheet.write(0, col_idx, header, header_format)
    
    # Escribir datos
    for row_idx, venta in enumerate(ventas_data, 1):
        # Fecha
        worksheet.write(row_idx, 0, venta.get('fecha', ''), data_format)
        
        # DNI
        worksheet.write(row_idx, 1, venta.get('paciente_dni', ''), data_format)
        
        # Paciente
        worksheet.write(row_idx, 2, venta.get('paciente_nombre', ''), data_format)
        
        # Optómetra
        worksheet.write(row_idx, 3, venta.get('optometra', ''), data_format)
        
        # Productos
        items = venta.get('items', [])
        productos_texto = ", ".join([f"{item.get('producto', '')} (x{item.get('cantidad', 1)})" for item in items])
        worksheet.write(row_idx, 4, productos_texto, data_format)
        
        # Subtotal
        worksheet.write(row_idx, 5, venta.get('subtotal', 0), currency_format)
        
        # IGV
        worksheet.write(row_idx, 6, venta.get('impuesto', 0), currency_format)
        
        # Total
        worksheet.write(row_idx, 7, venta.get('total', 0), currency_format)
        
        # Pago
        worksheet.write(row_idx, 8, venta.get('metodo_pago', ''), data_format)
        
        # Estado
        worksheet.write(row_idx, 9, venta.get('estado', ''), data_format)
    
    # Ajustar ancho de columnas
    worksheet.set_column('A:A', 13)
    worksheet.set_column('B:B', 13)
    worksheet.set_column('C:C', 22)
    worksheet.set_column('D:D', 16)
    worksheet.set_column('E:E', 38)
    worksheet.set_column('F:F', 14)
    worksheet.set_column('G:G', 14)
    worksheet.set_column('H:H', 14)
    worksheet.set_column('I:I', 14)
    worksheet.set_column('J:J', 14)


def abrir_carpeta_explorador(filepath):
    """
    Abre el administrador de archivos mostrando el archivo generado.
    
    Args:
        filepath: Ruta completa del archivo
    """
    try:
        if platform.system() == "Windows":
            os.startfile(os.path.dirname(filepath))
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", filepath])
        elif platform.system() == "Linux":
            subprocess.Popen(["xdg-open", os.path.dirname(filepath)])
    except Exception as e:
        print(f"Error al abrir carpeta: {e}")
