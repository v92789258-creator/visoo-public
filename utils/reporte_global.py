"""
Generador de Reportes Globales de Ventas.
Crea reportes consolidados con estadísticas y resúmenes finales.
"""

import os
import datetime
from datetime import timedelta
from collections import defaultdict


def generar_reporte_global(username, ventas_data, parameters):
    """
    Genera un reporte global con resúmenes de ventas.
    
    Args:
        username: Nombre de usuario
        ventas_data: Lista de todas las ventas
        parameters: Dict con 'period', 'year', 'start_date', 'end_date', 'format'
    
    Returns:
        Dict con estadísticas consolidadas
    """
    try:
        import xlsxwriter
        
        from utils.file_handler import get_user_file_path
        
        # Debug: mostrar datos recibidos
        print(f"DEBUG - Total de ventas: {len(ventas_data)}")
        print(f"DEBUG - Período: {parameters['period']}")
        print(f"DEBUG - Año: {parameters['year']}")
        print(f"DEBUG - Fecha inicio: {parameters['start_date']}")
        print(f"DEBUG - Fecha fin: {parameters['end_date']}")
        
        # Crear carpeta de reportes
        reportes_dir = get_user_file_path(username, "reportes")
        os.makedirs(reportes_dir, exist_ok=True)
        
        # Filtrar ventas según período
        ventas_filtradas = _filtrar_ventas(ventas_data, parameters)
        
        print(f"DEBUG - Ventas filtradas: {len(ventas_filtradas)}")
        
        if not ventas_filtradas:
            # Mostrar primera venta para debug
            if ventas_data:
                print(f"DEBUG - Primera venta: {ventas_data[0]}")
            return False, "", "No hay datos de ventas para el período seleccionado. Por favor verifica el rango de fechas."
        
        # Crear nombre del archivo
        period_name = parameters['period']
        format_name = parameters.get('format', 'con_diseño')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Reporte_Global_{period_name}_{format_name}_{timestamp}.xlsx"
        filepath = os.path.join(reportes_dir, filename)
        
        # Crear libro Excel
        workbook = xlsxwriter.Workbook(filepath)
        
        # Determinar si usar diseño
        con_diseño = parameters.get('format') == 'con_diseño'
        
        # Generar reportes según período
        if parameters['period'] == "Anuales":
            _generar_reporte_anual(workbook, ventas_filtradas, parameters, con_diseño)
        elif parameters['period'] == "Mensuales":
            _generar_reporte_mensual(workbook, ventas_filtradas, parameters, con_diseño)
        elif parameters['period'] == "Semanales":
            _generar_reporte_semanal(workbook, ventas_filtradas, parameters, con_diseño)
        else:  # Rango Personalizado
            _generar_reporte_rango(workbook, ventas_filtradas, parameters, con_diseño)
        
        workbook.close()
        
        # Abrir carpeta
        _abrir_carpeta_explorador(filepath)
        
        return True, filepath, f"Reporte generado exitosamente: {filename}"
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, "", f"Error al generar reporte: {str(e)}"


def _filtrar_ventas(ventas_data, parameters):
    """Filtra las ventas según los parámetros."""
    period = parameters['period']
    year = parameters['year']
    start_date = parameters['start_date']
    end_date = parameters['end_date']
    
    ventas_filtradas = []
    
    # Intentar múltiples formatos de fecha (con y sin hora)
    formatos_fecha = [
        '%d/%m/%Y %H:%M:%S',  # 02/12/2025 22:41:28
        '%d/%m/%Y',           # 02/12/2025
        '%Y-%m-%d %H:%M:%S',  # 2025-12-02 22:41:28
        '%Y-%m-%d',           # 2025-12-02
        '%d-%m-%Y %H:%M:%S',  # 02-12-2025 22:41:28
        '%d-%m-%Y',           # 02-12-2025
        '%Y/%m/%d %H:%M:%S',  # 2025/12/02 22:41:28
        '%Y/%m/%d',           # 2025/12/02
    ]
    
    for venta in ventas_data:
        try:
            fecha_str = venta.get('fecha', '').strip()
            fecha = None
            
            # Intentar parsear con diferentes formatos
            for fmt in formatos_fecha:
                try:
                    fecha = datetime.datetime.strptime(fecha_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if fecha is None:
                # Si no se puede parsear, saltar esta venta
                print(f"[DEBUG] No se pudo parsear fecha: '{fecha_str}'")
                continue
        except Exception as e:
            print(f"[DEBUG] Error al parsear fecha '{fecha_str}': {e}")
            continue
        
        # Aplicar filtro según el período
        incluir = False
        
        if period == "Anuales":
            if fecha.year == year:
                incluir = True
        elif period == "Mensuales":
            if fecha.year == year:
                incluir = True
        elif period == "Semanales":
            if fecha.year == year:
                incluir = True
        else:  # Rango Personalizado
            if start_date <= fecha <= end_date:
                incluir = True
        
        if incluir:
            ventas_filtradas.append(venta)
    
    return ventas_filtradas


def _generar_reporte_anual(workbook, ventas_data, parameters, con_diseño=True):
    """Genera reporte anual con detalle de todas las ventas."""
    worksheet = workbook.add_worksheet("Anual")
    _escribir_reporte_detalle(workbook, worksheet, ventas_data, "Anual", con_diseño)


def _generar_reporte_mensual(workbook, ventas_data, parameters, con_diseño=True):
    """Genera reporte mensual con detalle de todas las ventas."""
    worksheet = workbook.add_worksheet("Mensual")
    _escribir_reporte_detalle(workbook, worksheet, ventas_data, "Mensual", con_diseño)


def _generar_reporte_semanal(workbook, ventas_data, parameters, con_diseño=True):
    """Genera reporte semanal con detalle de todas las ventas."""
    worksheet = workbook.add_worksheet("Semanal")
    _escribir_reporte_detalle(workbook, worksheet, ventas_data, "Semanal", con_diseño)


def _generar_reporte_rango(workbook, ventas_data, parameters, con_diseño=True):
    """Genera reporte de rango personalizado con detalle de todas las ventas."""
    worksheet = workbook.add_worksheet("Rango")
    _escribir_reporte_detalle(workbook, worksheet, ventas_data, "Rango", con_diseño)


def _escribir_reporte_detalle(workbook, worksheet, ventas_data, tipo_periodo, con_diseño=True):
    """Escribe reporte detallado con todas las ventas listadas como en Historial."""
    
    # Definir formatos profesionales
    if con_diseño:
        # Título del reporte
        title_format = workbook.add_format({
            'bg_color': '#00B0D0',
            'font_color': 'white',
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Encabezados principales
        header_format = workbook.add_format({
            'bg_color': '#00B0D0',
            'font_color': 'white',
            'bold': True,
            'border': 1,
            'border_color': '#0096B3',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12,
            'text_wrap': True
        })
        
        # Filas normales
        row_format = workbook.add_format({
            'border': 1,
            'border_color': '#E0E0E0',
            'align': 'left',
            'valign': 'top',
            'font_size': 10,
            'text_wrap': True
        })
        
        # Filas alternadas (color celeste suave)
        row_alt_format = workbook.add_format({
            'bg_color': '#E0F7FA',
            'border': 1,
            'border_color': '#E0E0E0',
            'align': 'left',
            'valign': 'top',
            'font_size': 10,
            'text_wrap': True
        })
        
        # Fila de total
        total_format = workbook.add_format({
            'bg_color': '#00B0D0',
            'font_color': 'white',
            'bold': True,
            'border': 1,
            'border_color': '#0096B3',
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        # Moneda normal
        currency_format = workbook.add_format({
            'num_format': '[$$-809]#,##0.00;[$$-809]-#,##0.00',
            'border': 1,
            'border_color': '#E0E0E0',
            'align': 'right',
            'font_size': 10
        })
        
        # Moneda alternada
        currency_alt_format = workbook.add_format({
            'num_format': '[$$-809]#,##0.00;[$$-809]-#,##0.00',
            'bg_color': '#E0F7FA',
            'border': 1,
            'border_color': '#E0E0E0',
            'align': 'right',
            'font_size': 10
        })
        
        # Moneda en total
        currency_total_format = workbook.add_format({
            'num_format': '[$$-809]#,##0.00;[$$-809]-#,##0.00',
            'bg_color': '#00B0D0',
            'font_color': 'white',
            'bold': True,
            'border': 1,
            'border_color': '#0096B3',
            'align': 'right',
            'font_size': 11
        })
        
        # Estadísticas
        stat_label_format = workbook.add_format({
            'bg_color': '#F5F5F5',
            'bold': True,
            'border': 1,
            'border_color': '#E0E0E0',
            'align': 'right',
            'font_size': 10
        })
        
        stat_value_format = workbook.add_format({
            'bg_color': '#F5F5F5',
            'bold': True,
            'border': 1,
            'border_color': '#E0E0E0',
            'align': 'center',
            'font_size': 10,
            'num_format': '#,##0'
        })
    else:
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'font_size': 11})
        row_format = workbook.add_format({'border': 1, 'align': 'left', 'font_size': 10})
        row_alt_format = workbook.add_format({'border': 1, 'align': 'left', 'font_size': 10})
        total_format = workbook.add_format({'bold': True, 'border': 1, 'font_size': 11})
        currency_format = workbook.add_format({'num_format': '[$$-809]#,##0.00;[$$-809]-#,##0.00', 'border': 1, 'align': 'right', 'font_size': 10})
        currency_alt_format = currency_format
        currency_total_format = workbook.add_format({'num_format': '[$$-809]#,##0.00;[$$-809]-#,##0.00', 'bold': True, 'border': 1, 'font_size': 11})
        stat_label_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right'})
        stat_value_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
    
    # Ancho de columnas
    worksheet.set_column('A:A', 22)
    worksheet.set_column('B:B', 15)
    worksheet.set_column('C:C', 55)
    worksheet.set_column('D:D', 16)
    worksheet.set_column('E:E', 16)
    
    # TÍTULO
    row = 0
    worksheet.set_row(row, 25)
    worksheet.merge_range(row, 0, row, 4, f"📊 Reporte de Ventas - {tipo_periodo}", title_format)
    
    row += 1
    worksheet.set_row(row, 5)  # Fila espaciadora
    
    # ENCABEZADOS
    row += 1
    worksheet.set_row(row, 22)
    headers = ['Fecha', 'Paciente DNI', 'Productos', 'Total', 'Método Pago']
    for col_idx, header in enumerate(headers):
        worksheet.write(row, col_idx, header, header_format)
    
    # DATOS
    row += 1
    ventas_ordenadas = sorted(ventas_data, key=lambda x: x.get('fecha', ''))
    
    total_general = 0
    cantidad_ventas = 0
    montos = []
    
    for idx, venta in enumerate(ventas_ordenadas):
        fecha = venta.get('fecha', '')
        dni = venta.get('paciente_dni', '')
        total = float(venta.get('total', 0))
        metodo_pago = venta.get('metodo_pago', '')
        
        # Construir lista de productos
        items = venta.get('items', [])
        productos_str = ", ".join([f"{item.get('producto', '')} (x{item.get('cantidad', 1)})" for item in items])
        
        # Altura de fila adaptable según contenido
        worksheet.set_row(row, 25)
        
        # Formato alternado
        fmt = row_alt_format if (idx % 2 == 0) else row_format
        curr_fmt = currency_alt_format if (idx % 2 == 0) else currency_format
        
        worksheet.write(row, 0, fecha, fmt)
        worksheet.write(row, 1, dni, fmt)
        worksheet.write(row, 2, productos_str, fmt)
        worksheet.write(row, 3, total, curr_fmt)
        worksheet.write(row, 4, metodo_pago, fmt)
        
        total_general += total
        cantidad_ventas += 1
        montos.append(total)
        row += 1
    
    # ESPACIADOR
    row += 1
    
    # FILA DE TOTAL GENERAL
    worksheet.set_row(row, 20)
    worksheet.write(row, 0, "📈 TOTAL GENERAL", total_format)
    worksheet.write(row, 1, cantidad_ventas, total_format)
    worksheet.write(row, 2, f"{cantidad_ventas} venta(s)", total_format)
    worksheet.write(row, 3, total_general, currency_total_format)
    worksheet.write(row, 4, "", total_format)
    
    # ESTADÍSTICAS
    row += 2
    worksheet.set_row(row, 18)
    worksheet.write(row, 0, "📊 ESTADÍSTICAS", header_format)
    
    row += 1
    if montos:
        venta_maxima = max(montos)
        venta_minima = min(montos)
        promedio = total_general / cantidad_ventas if cantidad_ventas > 0 else 0
    else:
        venta_maxima = 0
        venta_minima = 0
        promedio = 0
    
    stats = [
        ("Cantidad de Ventas:", cantidad_ventas),
        ("Venta Promedio:", promedio),
        ("Venta Máxima:", venta_maxima),
        ("Venta Mínima:", venta_minima),
    ]
    
    for stat_label, stat_value in stats:
        worksheet.set_row(row, 16)
        worksheet.write(row, 0, stat_label, stat_label_format)
        
        if isinstance(stat_value, float):
            # Formato moneda para valores decimales
            curr_fmt_stat = workbook.add_format({
                'bg_color': '#F5F5F5',
                'bold': True,
                'border': 1,
                'border_color': '#E0E0E0',
                'align': 'center',
                'font_size': 10,
                'num_format': '[$$-809]#,##0.00;[$$-809]-#,##0.00'
            })
            worksheet.write(row, 1, stat_value, curr_fmt_stat)
        else:
            worksheet.write(row, 1, stat_value, stat_value_format)
        
        row += 1


def _escribir_reporte_consolidado(workbook, worksheet, ventas_agrupadas, tipo_agrupacion, con_diseño=True):
    """Escribe un reporte consolidado con totales."""
    
    if con_diseño:
        # Formatos con diseño (celeste)
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#00B0D0',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11,
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
        })
        
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E0F2F1',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '[$$-809]#,##0.00;[$$-809]-#,##0.00',
            'font_size': 10,
        })
        
        total_label_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E0F2F1',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 10,
        })
        
        summary_header = workbook.add_format({
            'bold': True,
            'bg_color': '#00B0D0',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
        })
    else:
        # Formatos simple (sin diseño)
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11,
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
        })
        
        total_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '[$$-809]#,##0.00;[$$-809]-#,##0.00',
            'font_size': 10,
        })
        
        total_label_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 10,
        })
        
        summary_header = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
        })
    
    # Encabezados principales
    headers = [tipo_agrupacion, "Total Ventas", "Cantidad Ventas", "Promedio", "IGV Total"]
    
    for col_idx, header in enumerate(headers):
        worksheet.write(0, col_idx, header, header_format)
    
    worksheet.set_row(0, 20)
    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:B', 18)
    worksheet.set_column('C:C', 18)
    worksheet.set_column('D:D', 18)
    worksheet.set_column('E:E', 18)
    
    # Escribir datos agrupados
    row = 1
    gran_total_ventas = 0
    gran_total_cantidad = 0
    gran_total_igv = 0
    
    # Ordenar las claves correctamente según el tipo
    if tipo_agrupacion == "Mes":
        # Ordenar por número de mes (01, 02, ..., 12)
        claves_ordenadas = sorted(ventas_agrupadas.keys(), key=lambda x: int(x.split()[0]))
    elif tipo_agrupacion == "Semana":
        # Ordenar por número de semana
        claves_ordenadas = sorted(ventas_agrupadas.keys(), key=lambda x: int(x.split()[1]))
    elif tipo_agrupacion == "Día":
        # Ordenar por fecha (DD/MM/YYYY)
        claves_ordenadas = sorted(ventas_agrupadas.keys(), key=lambda x: datetime.datetime.strptime(x, '%d/%m/%Y'))
    else:
        claves_ordenadas = sorted(ventas_agrupadas.keys())
    
    for periodo in claves_ordenadas:
        ventas = ventas_agrupadas[periodo]
        
        # Calcular totales - usar .get() con valores por defecto
        total_ventas = sum(v.get('total', 0) for v in ventas)
        cantidad = len(ventas)
        promedio = total_ventas / cantidad if cantidad > 0 else 0
        
        # IGV: si no existe el campo, calcular como 18% del total
        total_igv = 0
        for v in ventas:
            if 'impuesto' in v:
                total_igv += v.get('impuesto', 0)
            else:
                # Si no hay campo impuesto, asumir 18% de IGV (Perú)
                total_igv += v.get('total', 0) * 0.18 / 1.18
        
        gran_total_ventas += total_ventas
        gran_total_cantidad += cantidad
        gran_total_igv += total_igv
        
        # Escribir fila
        worksheet.write(row, 0, str(periodo), data_format)
        worksheet.write(row, 1, total_ventas, total_format)
        worksheet.write(row, 2, cantidad, data_format)
        worksheet.write(row, 3, promedio, total_format)
        worksheet.write(row, 4, total_igv, total_format)
        
        row += 1
    
    # Fila en blanco
    row += 1
    
    # RESUMEN FINAL
    worksheet.write(row, 0, "TOTAL GENERAL", summary_header)
    worksheet.write(row, 1, gran_total_ventas, summary_header)
    worksheet.write(row, 2, gran_total_cantidad, summary_header)
    promedio_general = gran_total_ventas / gran_total_cantidad if gran_total_cantidad > 0 else 0
    worksheet.write(row, 3, promedio_general, summary_header)
    worksheet.write(row, 4, gran_total_igv, summary_header)
    
    row += 2
    
    # ESTADÍSTICAS ADICIONALES
    worksheet.write(row, 0, "ESTADÍSTICAS", summary_header)
    row += 1
    
    # Contar ventas completadas/pendientes - si el campo no existe, asumir completada
    completadas = 0
    pendientes = 0
    for v in ventas_agrupadas.values():
        for vv in v:
            estado = vv.get('estado', 'Completada')  # Por defecto completada
            if estado == 'Completada':
                completadas += 1
            elif estado == 'Pendiente':
                pendientes += 1
    
    # Encontrar venta máxima y mínima
    todas_las_ventas = [vv.get('total', 0) for v in ventas_agrupadas.values() for vv in v]
    venta_maxima = max(todas_las_ventas) if todas_las_ventas else 0
    venta_minima = min((v for v in todas_las_ventas if v > 0), default=0)
    
    stats = [
        ("Ventas Completadas", completadas),
        ("Ventas Pendientes", pendientes),
        ("Venta Máxima", venta_maxima),
        ("Venta Mínima", venta_minima),
    ]
    
    for stat_label, stat_value in stats:
        worksheet.write(row, 0, stat_label, data_format)
        if stat_label in ["Venta Máxima", "Venta Mínima"]:
            worksheet.write(row, 1, stat_value, total_format)
        else:
            worksheet.write(row, 1, stat_value, data_format)
        row += 1


def _abrir_carpeta_explorador(filepath):
    """Abre la carpeta del archivo en el explorador."""
    import subprocess
    import platform
    
    try:
        if platform.system() == "Windows":
            os.startfile(os.path.dirname(filepath))
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", filepath])
        elif platform.system() == "Linux":
            subprocess.Popen(["xdg-open", os.path.dirname(filepath)])
    except Exception as e:
        print(f"Error al abrir carpeta: {e}")
