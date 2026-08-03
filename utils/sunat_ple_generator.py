"""
Generador de Libro de Ventas e Ingresos - Formato SUNAT PLE
Cumple con los requerimientos de la Administración Tributaria de Perú

Referencia: https://www.sunat.gob.pe/
Formato: TXT con separador | (pipe)
"""

import os
import json
from datetime import datetime
from pathlib import Path


def parse_fecha_flexible(fecha_str):
    """Parsea fecha en múltiples formatos."""
    if not fecha_str:
        return datetime.now()
    
    # Limpiar solo la fecha si viene con hora
    if ' ' in str(fecha_str):
        fecha_str = str(fecha_str).split()[0]
    
    # Formatos a intentar
    formatos = [
        '%Y-%m-%d',      # 2025-12-09
        '%d/%m/%Y',      # 09/12/2025
        '%m/%d/%Y',      # 12/09/2025
        '%d-%m-%Y',      # 09-12-2025
        '%Y/%m/%d',      # 2025/12/09
    ]
    
    for formato in formatos:
        try:
            return datetime.strptime(fecha_str, formato)
        except ValueError:
            continue
    
    # Si ningún formato funciona, retorna hoy
    return datetime.now()


def es_dni_valido(dni):
    """Valida si un DNI es válido para SUNAT (no genérico, no vacío)."""
    if not dni:
        return False
    
    dni_str = str(dni).strip()
    
    # DNI genérico (todos ceros)
    if dni_str == '00000000' or dni_str == '0':
        return False
    
    # DNI vacío o con solo espacios
    if not dni_str or dni_str.isspace():
        return False
    
    # DNI debe tener al menos 8 dígitos para Perú
    if len(dni_str) < 8:
        return False
    
    # DNI no debe ser todo ceros
    if all(c == '0' for c in dni_str if c.isdigit()):
        return False
    
    return True


class SunatPLEGenerator:
    """Generador de Libro de Ventas en formato SUNAT PLE"""
    
    # Constantes SUNAT
    TIPO_COMPROBANTE = {
        'factura': '01',
        'boleta': '03',
        'nota_credito': '07',
        'nota_debito': '08'
    }
    
    TIPO_DOCUMENTO = {
        'ruc': '6',
        'dni': '1',
        'pasaporte': '3'
    }
    
    def __init__(self, usuario_id, ruc_empresa='12345678901', nombre_empresa='EMPRESA'):
        self.usuario_id = usuario_id
        self.ruc_empresa = ruc_empresa
        self.nombre_empresa = nombre_empresa
        self.registros = []
    
    def agregar_venta(self, venta, numero_comprobante, tipo_comprobante='boleta'):
        """
        Agrega una venta al libro en formato SUNAT
        
        Args:
            venta: Dict con datos de la venta
            numero_comprobante: Número secuencial del comprobante
            tipo_comprobante: 'factura', 'boleta', 'nota_credito', 'nota_debito'
        """
        try:
            # Parsear fecha
            fecha_str = venta.get('fecha', '')
            if fecha_str:
                fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y %H:%M:%S")
            else:
                fecha_obj = datetime.now()
            
            # Extraer datos
            paciente_dni = venta.get('paciente_dni', '00000000')
            items = venta.get('items', [])
            
            # Obtener total - intentar varias fuentes
            total = float(venta.get('total', 0))
            if total == 0:
                total = float(venta.get('monto_pagado', 0))
            
            # Calcular subtotal e IGV correctamente
            # IMPORTANTE: Las ventas pueden tener subtotal/igv en 0, 
            # así que verificamos si el total es válido primero
            if total > 0:
                # Si tenemos subtotal e IGV, úsalos SOLO si no están en 0
                subtotal = float(venta.get('subtotal', 0))
                igv = float(venta.get('igv', 0))
                
                # Si ambos están en 0, calcularlos del total
                if subtotal == 0 and igv == 0:
                    subtotal = total / 1.18
                    igv = total - subtotal
                elif subtotal > 0 and igv == 0:
                    # Si solo subtotal está presente, calcular IGV
                    igv = subtotal * 0.18
                elif igv > 0 and subtotal == 0:
                    # Si solo IGV está presente, calcular subtotal
                    subtotal = igv / 0.18
            else:
                subtotal = 0.0
                igv = 0.0
            
            # Obtener nombre del cliente (desde la venta o por defecto)
            nombre_cliente = venta.get('paciente_nombre', f"Cliente {paciente_dni}")
            
            # Determinar tipo documento
            tipo_doc = '1' if len(paciente_dni) == 8 else '6'  # DNI o RUC
            
            # Construir registro SUNAT (25 campos)
            periodo = fecha_obj.strftime("%Y%m")  # YYYYMM sincronizado con fecha de emisión
            cuo = f"{numero_comprobante:06d}"  # Correlativo único operativo
            correlativo = f"{numero_comprobante:06d}"
            fecha_emision = fecha_obj.strftime("%d/%m/%Y")
            fecha_vencimiento = ""  # Vacío para boletas
            tipo_comp = self.TIPO_COMPROBANTE.get(tipo_comprobante, '03')
            serie = f"B{fecha_obj.strftime('%y')}"  # B26, B27, etc.
            numero = f"{numero_comprobante:06d}"
            
            # Valores en soles (sin exportación)
            valor_exportacion = "0.00"
            base_gravada = f"{subtotal:.2f}"
            igv_str = f"{igv:.2f}"
            exonerado = "0.00"
            inafecto = "0.00"
            isc = "0.00"
            otros_tributos = "0.00"
            importe_total = f"{total:.2f}"
            tipo_cambio = ""  # No aplica PEN
            
            # Documentos modificados (vacío si no es nota de crédito/débito)
            fecha_doc_mod = ""
            tipo_doc_mod = ""
            serie_mod = ""
            numero_mod = ""
            
            # ✅ VALIDACIÓN 1: DNI 00000000 solo válido si boleta Y monto ≤ 700
            estado = "1"  # 1 = válido, 2 = anulado
            
            if paciente_dni == '00000000':
                # Es DNI genérico - validar reglas SUNAT
                es_boleta = tipo_comp == '03'
                monto_ok = total <= 700.00
                
                if not es_boleta:
                    # SUNAT rechaza DNI genérico en facturas
                    estado = "2"  # Marcar como anulado/rechazado
                    print(f"[SUNAT] DNI genérico solo permitido en boletas: {numero_comprobante}")
                elif not monto_ok:
                    # SUNAT alerta si monto > 700 con DNI genérico
                    print(f"[SUNAT] ⚠️ Advertencia: DNI genérico con monto S/. {total:.2f} (límite S/. 700)")
            
            # ✅ VALIDACIÓN 2: Registros con todos los montos en 0.00 → anulado
            if total == 0 and subtotal == 0 and igv == 0:
                estado = "2"  # Marcar como anulado/error corregido
                print(f"[SUNAT] Registro con montos en 0.00 marcado como anulado: {numero_comprobante}")
            
            # Construir línea en formato SUNAT
            registro = "|".join([
                periodo,                    # 1
                cuo,                         # 2
                correlativo,                 # 3
                fecha_emision,              # 4
                fecha_vencimiento,          # 5
                tipo_comp,                  # 6
                serie,                      # 7
                numero,                     # 8
                tipo_doc,                   # 9
                paciente_dni,               # 10
                nombre_cliente,             # 11
                valor_exportacion,          # 12
                base_gravada,               # 13
                igv_str,                    # 14
                exonerado,                  # 15
                inafecto,                   # 16
                isc,                        # 17
                otros_tributos,             # 18
                importe_total,              # 19
                tipo_cambio,                # 20
                fecha_doc_mod,              # 21
                tipo_doc_mod,               # 22
                serie_mod,                  # 23
                numero_mod,                 # 24
                estado                      # 25
            ])
            
            self.registros.append({
                'linea': registro,
                'numero': numero_comprobante,
                'cliente': nombre_cliente,
                'total': total,
                'fecha': fecha_emision,
                'estado': estado,
                'periodo': periodo,
                'dni': paciente_dni
            })
            
            return True
        except Exception as e:
            print(f"[SUNAT] Error al agregar venta: {e}")
            return False
    
    def generar_archivo(self, output_path):
        """
        Genera el archivo TXT en formato SUNAT
        
        Args:
            output_path: Ruta donde guardar el archivo
            
        Returns:
            bool: True si fue exitoso
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for registro in self.registros:
                    f.write(registro['linea'] + '\n')
            
            return True
        except Exception as e:
            print(f"[SUNAT] Error al generar archivo: {e}")
            return False
    
    def obtener_resumen(self):
        """Retorna resumen de registros para el Libro Contable"""
        if not self.registros:
            return {
                'total_comprobantes': 0,
                'total_validos': 0,
                'total_anulados': 0,
                'total_ventas': 0.00,
                'total_igv': 0.00,
                'registros_con_advertencia': []
            }
        
        total_validos = sum(1 for r in self.registros if r.get('estado') == '1')
        total_anulados = sum(1 for r in self.registros if r.get('estado') == '2')
        
        # Sumar ventas válidas solo
        total_ventas = 0.0
        for r in self.registros:
            if r.get('estado') == '1':
                try:
                    total_ventas += float(r.get('total', 0))
                except (ValueError, TypeError):
                    pass
        
        # Recopilar advertencias y errores
        advertencias = []
        errores = []
        
        for r in self.registros:
            try:
                monto = float(r.get('total', 0))
                dni = r.get('dni', '')
                # ERRORES CRÍTICOS: Monto > 700 sin DNI válido
                if monto > 700 and not es_dni_valido(dni):
                    errores.append(f"Comprobante {r.get('numero', 'N/A')}: COMPRA S/. {monto:.2f} SIN DNI VÁLIDO - SUNAT lo rechazará")
            except (ValueError, TypeError):
                pass
            
            # ADVERTENCIAS: Registros anulados
            if r.get('estado') == '2':
                try:
                    monto = float(r.get('total', 0))
                    if monto == 0:
                        advertencias.append(f"Comprobante {r.get('numero', 'N/A')}: Anulado (montos en 0.00)")
                    else:
                        advertencias.append(f"Comprobante {r.get('numero', 'N/A')}: Anulado (validación SUNAT)")
                except (ValueError, TypeError):
                    advertencias.append(f"Comprobante {r.get('numero', 'N/A')}: Anulado")
        
        return {
            'total_comprobantes': len(self.registros),
            'total_validos': total_validos,
            'total_anulados': total_anulados,
            'total_ventas': total_ventas,
            'total_igv': total_ventas * 0.18 if total_ventas > 0 else 0.00,
            'primer_comprobante': self.registros[0].get('numero') if self.registros else 0,
            'ultimo_comprobante': self.registros[-1].get('numero') if self.registros else 0,
            'registros_con_advertencia': advertencias,
            'registros_con_error': errores
        }


def generar_libro_ventas_sunat(username, output_path):
    """
    Genera el archivo SUNAT PLE con todas las ventas del usuario
    
    Args:
        username: Usuario dueño de las ventas
        output_path: Ruta del archivo a generar
        
    Returns:
        dict: Información de generación o error
    """
    try:
        from utils.file_handler import cargar_ventas
        
        # Cargar ventas
        ventas = cargar_ventas(username)
        
        if not ventas:
            return {
                'success': False,
                'mensaje': 'No hay ventas para exportar',
                'total_comprobantes': 0
            }
        
        # Crear generador
        generador = SunatPLEGenerator(
            usuario_id=username,
            ruc_empresa='12345678901',
            nombre_empresa='EMPRESA'
        )
        
        # Agregar ventas
        for i, venta in enumerate(ventas, 1):
            generador.agregar_venta(venta, i, tipo_comprobante='boleta')
        
        # Generar archivo
        if generador.generar_archivo(output_path):
            resumen = generador.obtener_resumen()
            return {
                'success': True,
                'mensaje': f'Libro SUNAT generado exitosamente',
                'archivo': output_path,
                'total_comprobantes': resumen['total_comprobantes'],
                'total_validos': resumen.get('total_validos', 0),
                'total_anulados': resumen.get('total_anulados', 0),
                'total_ventas': resumen['total_ventas'],
                'total_igv': resumen['total_igv'],
                'registros_con_advertencia': resumen.get('registros_con_advertencia', [])
            }
        else:
            return {
                'success': False,
                'mensaje': 'Error al generar el archivo SUNAT'
            }
    
    except Exception as e:
        return {
            'success': False,
            'mensaje': f'Error en generación SUNAT: {str(e)}'
        }


def generar_libro_ventas_sunat_excel(username, output_path):
    """
    Genera el archivo SUNAT PLE en formato Excel con xlsxwriter
    
    Args:
        username: Usuario dueño de las ventas
        output_path: Ruta del archivo Excel a generar
        
    Returns:
        dict: Información de generación o error
    """
    try:
        import xlsxwriter
        from utils.file_handler import cargar_ventas
        
        # Cargar ventas
        ventas = cargar_ventas(username)
        
        if not ventas:
            return {
                'success': False,
                'mensaje': 'No hay ventas para exportar',
                'total_comprobantes': 0
            }
        
        # Crear generador SUNAT
        generador = SunatPLEGenerator(
            usuario_id=username,
            ruc_empresa='12345678901',
            nombre_empresa='EMPRESA'
        )
        
        # Procesar ventas
        for i, venta in enumerate(ventas, 1):
            generador.agregar_venta(venta, i, tipo_comprobante='boleta')
        
        # Obtener resumen
        resumen = generador.obtener_resumen()
        
        # Crear workbook
        workbook = xlsxwriter.Workbook(output_path)
        
        # ===== FORMATOS =====
        header_format = workbook.add_format({
            'bg_color': '#1F4E78',
            'font_color': '#FFFFFF',
            'bold': True,
            'border': 1,
            'border_color': '#000000',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        data_format_blue = workbook.add_format({
            'bg_color': '#D9E1F2',
            'font_color': '#000000',
            'border': 1,
            'border_color': '#000000',
            'valign': 'vcenter',
            'font_size': 10
        })
        
        data_format_white = workbook.add_format({
            'bg_color': '#FFFFFF',
            'font_color': '#000000',
            'border': 1,
            'border_color': '#000000',
            'valign': 'vcenter',
            'font_size': 10
        })
        
        money_format_blue = workbook.add_format({
            'bg_color': '#D9E1F2',
            'font_color': '#000000',
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 10
        })
        
        money_format_white = workbook.add_format({
            'bg_color': '#FFFFFF',
            'font_color': '#000000',
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 10
        })
        
        # ===== HOJA 1: LIBRO VENTAS =====
        ws = workbook.add_worksheet('Libro Ventas SUNAT')
        
        headers = [
            'Período', 'CUO', 'Correlativo', 'Fecha Emisión', 'Fecha Vencimiento',
            'Tipo Comprobante', 'Serie', 'Número', 'Tipo Doc', 'DNI/RUC',
            'Cliente', 'Exportación', 'Base Gravada', 'IGV', 'Exonerado',
            'Inafecto', 'ISC', 'Otros Tributos', 'Total', 'Tipo Cambio',
            'Fecha Doc Mod', 'Tipo Doc Mod', 'Serie Mod', 'Número Mod', 'Estado'
        ]
        
        # Escribir headers
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_format)
        
        # Congelar filas
        ws.freeze_panes(1, 0)
        
        # Escribir datos
        for row_idx, registro in enumerate(generador.registros, 1):
            linea = registro['linea'].split('|')
            
            # Alternar colores
            use_blue = row_idx % 2 == 1
            data_fmt = data_format_blue if use_blue else data_format_white
            money_fmt = money_format_blue if use_blue else money_format_white
            
            for col_idx, valor in enumerate(linea):
                # Formateo especial para montos (columnas 12-18 en 0-indexed)
                if col_idx in [12, 13, 14, 15, 16, 17, 18]:
                    try:
                        num_valor = float(valor)
                        ws.write_number(row_idx, col_idx, num_valor, money_fmt)
                    except (ValueError, TypeError):
                        ws.write(row_idx, col_idx, valor, data_fmt)
                else:
                    ws.write(row_idx, col_idx, valor, data_fmt)
        
        # Ajustar anchos
        ws.set_column('A:A', 12)
        ws.set_column('B:B', 10)
        ws.set_column('C:C', 12)
        ws.set_column('D:D', 14)
        ws.set_column('E:E', 14)
        ws.set_column('F:F', 12)
        ws.set_column('G:G', 8)
        ws.set_column('H:H', 10)
        ws.set_column('I:I', 10)
        ws.set_column('J:J', 12)
        ws.set_column('K:K', 20)
        ws.set_column('L:L', 12)
        ws.set_column('M:M', 14)
        ws.set_column('N:N', 12)
        ws.set_column('O:O', 12)
        ws.set_column('P:P', 12)
        ws.set_column('Q:Q', 10)
        ws.set_column('R:R', 12)
        ws.set_column('S:S', 12)
        ws.set_column('T:T', 12)
        ws.set_column('U:U', 12)
        ws.set_column('V:V', 12)
        ws.set_column('W:W', 10)
        ws.set_column('X:X', 12)
        ws.set_column('Y:Y', 10)
        
        # ===== HOJA 2: RESUMEN =====
        ws_resumen = workbook.add_worksheet('Resumen')
        
        title_format = workbook.add_format({
            'bg_color': '#0070C0',
            'font_color': '#FFFFFF',
            'bold': True,
            'border': 1,
            'border_color': '#000000',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 13
        })
        
        label_format = workbook.add_format({
            'bg_color': '#E8F1F8',
            'font_color': '#1F4E78',
            'bold': True,
            'border': 1,
            'border_color': '#000000',
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        value_format = workbook.add_format({
            'bg_color': '#E8F1F8',
            'font_color': '#000000',
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 11
        })
        
        value_text_format = workbook.add_format({
            'bg_color': '#E8F1F8',
            'font_color': '#000000',
            'border': 1,
            'border_color': '#000000',
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        adv_format = workbook.add_format({
            'bg_color': '#FFFF99',
            'font_color': '#CC0000',
            'bold': True,
            'border': 1,
            'border_color': '#000000',
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        adv_item_format = workbook.add_format({
            'font_color': '#CC0000',
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
            'font_size': 10
        })
        
        # Título
        ws_resumen.merge_range('A1:B1', 'RESUMEN LIBRO VENTAS SUNAT', title_format)
        ws_resumen.set_row(0, 25)
        
        # Datos resumen
        data_resumen = [
            ['Total Comprobantes', resumen['total_comprobantes']],
            ['Comprobantes Válidos', resumen['total_validos']],
            ['Comprobantes Anulados', resumen['total_anulados']],
            ['Total Ventas', resumen['total_ventas']],
            ['Total IGV', resumen['total_igv']],
            ['Primer Comprobante', str(resumen.get('primer_comprobante', 'N/A')).zfill(6)],
            ['Último Comprobante', str(resumen.get('ultimo_comprobante', 'N/A')).zfill(6)],
        ]
        
        row = 2
        for label, valor in data_resumen:
            ws_resumen.write(row, 0, label, label_format)
            
            if isinstance(valor, float):
                ws_resumen.write_number(row, 1, valor, value_format)
            elif isinstance(valor, int):
                ws_resumen.write_number(row, 1, valor, value_text_format)
            else:
                ws_resumen.write(row, 1, valor, value_text_format)
            
            row += 1
        
        # Errores (DNI genérico > 700)
        if resumen.get('registros_con_error'):
            row += 1
            error_format = workbook.add_format({
                'bg_color': '#FF9999',
                'font_color': '#990000',
                'bold': True,
                'border': 1,
                'border_color': '#000000',
                'align': 'left',
                'valign': 'vcenter',
                'font_size': 11
            })
            
            error_item_format = workbook.add_format({
                'font_color': '#990000',
                'align': 'left',
                'valign': 'vcenter',
                'text_wrap': True,
                'font_size': 10
            })
            
            error_title = f'ERRORES ({len(resumen["registros_con_error"])})'
            ws_resumen.merge_range(row, 0, row, 1, error_title, error_format)
            row += 1
            
            for error in resumen['registros_con_error'][:15]:
                ws_resumen.write(row, 0, f'• {error}', error_item_format)
                row += 1
        
        # Advertencias
        if resumen['registros_con_advertencia']:
            row += 1
            adv_title = f'ADVERTENCIAS ({len(resumen["registros_con_advertencia"])})'
            ws_resumen.merge_range(row, 0, row, 1, adv_title, adv_format)
            row += 1
            
            for advertencia in resumen['registros_con_advertencia'][:15]:
                ws_resumen.write(row, 0, f'• {advertencia}', adv_item_format)
                row += 1
        
        # Ajustar columnas
        ws_resumen.set_column('A:A', 25)
        ws_resumen.set_column('B:B', 20)
        
        # Cerrar workbook
        workbook.close()
        
        return {
            'success': True,
            'mensaje': f'Archivo generado exitosamente',
            'archivo': output_path,
            'total_comprobantes': resumen['total_comprobantes'],
            'total_validos': resumen['total_validos'],
            'total_anulados': resumen['total_anulados'],
            'total_ventas': resumen['total_ventas'],
            'total_igv': resumen['total_igv'],
            'registros_con_advertencia': resumen['registros_con_advertencia'],
            'registros_con_error': resumen.get('registros_con_error', [])
        }
        
    except ImportError:
        return {
            'success': False,
            'error': 'Se requiere instalar xlsxwriter: pip install xlsxwriter',
            'total_comprobantes': 0
        }
    except Exception as e:
        print(f"Error al generar Excel: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'total_comprobantes': 0
        }


def generar_libro_graduaciones_excel(username, filepath):
    """Exporta graduaciones a Excel con formato profesional."""
    try:
        import xlsxwriter
        from utils.file_handler import cargar_graduaciones
        
        graduaciones = cargar_graduaciones(username) or []
        
        workbook = xlsxwriter.Workbook(filepath)
        worksheet = workbook.add_worksheet("Libro Graduaciones")
        
        # Estilos
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#1F4E78',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        money_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 11,
            'num_format': 'S/ #,##0.00'
        })
        
        center_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        # Headers
        headers = ["FECHA", "PACIENTE", "DNI", "ÓPTICA/MÉDICO", "TIPO", "INFORMACIÓN", "PRECIO", "PAGO"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Ancho de columnas
        worksheet.set_column('A:A', 18)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 14)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 12)
        worksheet.set_column('H:H', 12)
        
        total_pago = 0
        
        # Datos
        for row, grad in enumerate(graduaciones, start=1):
            if not isinstance(grad, dict): continue
            
            fecha = str(grad.get('fecha', ''))
            paciente = str(grad.get('paciente', 'N/A'))
            dni = str(grad.get('dni', ''))
            optica_medico = str(grad.get('optica_medico', 'N/A'))
            tipo = str(grad.get('tipo', 'Graduación'))
            info = str(grad.get('informacion', ''))
            
            try:
                precio = float(grad.get('precio', 0) or 0)
                pago = float(grad.get('pago', 0) or 0)
            except (ValueError, TypeError):
                precio = 0.0
                pago = 0.0
            
            total_pago += pago
            
            # Alternancia de colores
            if row % 2 == 0:
                row_format = workbook.add_format({
                    'border': 1,
                    'bg_color': '#D9E1F2',
                    'align': 'left',
                    'valign': 'vcenter',
                    'font_size': 11
                })
                money_alt_format = workbook.add_format({
                    'border': 1,
                    'bg_color': '#D9E1F2',
                    'align': 'right',
                    'valign': 'vcenter',
                    'font_size': 11,
                    'num_format': 'S/ #,##0.00'
                })
                center_alt_format = workbook.add_format({
                    'border': 1,
                    'bg_color': '#D9E1F2',
                    'align': 'center',
                    'valign': 'vcenter',
                    'font_size': 11
                })
            else:
                row_format = data_format
                money_alt_format = money_format
                center_alt_format = center_format
            
            worksheet.write(row, 0, fecha, center_alt_format)
            worksheet.write(row, 1, paciente, row_format)
            worksheet.write(row, 2, dni, center_alt_format)
            worksheet.write(row, 3, optica_medico, row_format)
            worksheet.write(row, 4, tipo, center_alt_format)
            worksheet.write(row, 5, info, row_format)
            worksheet.write(row, 6, precio, money_alt_format)
            worksheet.write(row, 7, pago, money_alt_format)
        
        # Footer con totales
        footer_row = len(graduaciones) + 2
        footer_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E78',
            'font_color': 'white',
            'border': 1,
            'align': 'right',
            'font_size': 12
        })
        
        worksheet.write(footer_row, 5, "TOTAL RECAUDADO:", footer_format)
        worksheet.write(footer_row, 7, total_pago, workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E78',
            'font_color': 'white',
            'border': 1,
            'align': 'right',
            'font_size': 12,
            'num_format': 'S/ #,##0.00'
        }))
        
        workbook.close()
        
        return {
            'success': True,
            'filepath': filepath,
            'total_graduaciones': len(graduaciones),
            'total_recaudado': total_pago,
            'mensaje': f'Graduaciones exportadas: {len(graduaciones)} registros'
        }
        
    except ImportError:
        return {'success': False, 'error': 'El módulo xlsxwriter no está instalado'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generar_libro_combinado_excel(username, filepath):
    """Exporta Ventas + Graduaciones en un mismo Excel con 2 worksheets."""
    try:
        import xlsxwriter
        from utils.file_handler import cargar_ventas, cargar_graduaciones
        
        # Cargar datos con fallback a lista vacía
        ventas = cargar_ventas(username) or []
        graduaciones = cargar_graduaciones(username) or []
        
        workbook = xlsxwriter.Workbook(filepath)
        
        # Estilos
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#1F4E78',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12
        })
        
        money_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 11,
            'num_format': 'S/ #,##0.00'
        })
        
        center_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        
        # ===== WORKSHEET 1: VENTAS =====
        ws_ventas = workbook.add_worksheet("Libro Ventas")
        
        # Headers Ventas
        ventas_headers = ["FECHA", "USUARIO", "CLIENTE", "TIPO", "MONTO", "MÉTODO"]
        for col, header in enumerate(ventas_headers):
            ws_ventas.write(0, col, header, header_format)
        
        ws_ventas.set_column('A:A', 18)
        ws_ventas.set_column('B:B', 15)
        ws_ventas.set_column('C:C', 20)
        ws_ventas.set_column('D:D', 12)
        ws_ventas.set_column('E:E', 14)
        ws_ventas.set_column('F:F', 12)
        
        total_ventas = 0
        for row, venta in enumerate(ventas, start=1):
            if not isinstance(venta, dict): continue
            
            fecha = str(venta.get('fecha', ''))
            usuario = str(venta.get('usuario', 'N/A'))
            # Intentar obtener nombre de cliente desde varios campos posibles
            cliente = str(venta.get('paciente_nombre') or venta.get('cliente') or 'Público General')
            tipo = "VENTA POS"
            
            # Manejo seguro de float
            try:
                total = float(venta.get('total', 0) or 0)
            except (ValueError, TypeError):
                total = 0.0
                
            metodo = str(venta.get('metodo_pago') or venta.get('metodo') or '').upper()
            
            total_ventas += total
            
            # Estilo alternado (zebra)
            if row % 2 == 0:
                row_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2', 'align': 'left'})
                money_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2', 'align': 'right', 'num_format': 'S/ #,##0.00'})
                center_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2', 'align': 'center'})
            else:
                row_fmt = data_format
                money_fmt = money_format
                center_fmt = center_format
            
            ws_ventas.write(row, 0, fecha, center_fmt)
            ws_ventas.write(row, 1, usuario, row_fmt)
            ws_ventas.write(row, 2, cliente, row_fmt)
            ws_ventas.write(row, 3, tipo, center_fmt)
            ws_ventas.write(row, 4, total, money_fmt)
            ws_ventas.write(row, 5, metodo, center_fmt)
        
        footer_row = len(ventas) + 2
        ws_ventas.write(footer_row, 3, "TOTAL:", header_format)
        ws_ventas.write(footer_row, 4, total_ventas, workbook.add_format({
            'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1,
            'align': 'right', 'num_format': 'S/ #,##0.00'
        }))
        
        # ===== WORKSHEET 2: GRADUACIONES =====
        ws_grad = workbook.add_worksheet("Libro Graduaciones")
        
        grad_headers = ["FECHA", "PACIENTE", "DNI", "ÓPTICA/MÉDICO", "TIPO", "INFORMACIÓN", "PRECIO", "PAGO"]
        for col, header in enumerate(grad_headers):
            ws_grad.write(0, col, header, header_format)
        
        ws_grad.set_column('A:A', 18)
        ws_grad.set_column('B:B', 25)
        ws_grad.set_column('C:C', 14)
        ws_grad.set_column('D:D', 18)
        ws_grad.set_column('E:E', 15)
        ws_grad.set_column('F:F', 20)
        ws_grad.set_column('G:G', 12)
        ws_grad.set_column('H:H', 12)
        
        total_graduaciones = 0
        for row, grad in enumerate(graduaciones, start=1):
            if not isinstance(grad, dict): continue
            
            fecha = str(grad.get('fecha', ''))
            paciente = str(grad.get('paciente', 'N/A'))
            dni = str(grad.get('dni', ''))
            optica_medico = str(grad.get('optica_medico', 'N/A'))
            tipo = str(grad.get('tipo', 'Graduación'))
            info = str(grad.get('informacion', ''))
            
            try:
                precio = float(grad.get('precio', 0) or 0)
                pago = float(grad.get('pago', 0) or 0)
            except (ValueError, TypeError):
                precio = 0.0
                pago = 0.0
            
            total_graduaciones += pago
            
            if row % 2 == 0:
                row_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2', 'align': 'left'})
                money_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2', 'align': 'right', 'num_format': 'S/ #,##0.00'})
                center_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2', 'align': 'center'})
            else:
                row_fmt = data_format
                money_fmt = money_format
                center_fmt = center_format
            
            ws_grad.write(row, 0, fecha, center_fmt)
            ws_grad.write(row, 1, paciente, row_fmt)
            ws_grad.write(row, 2, dni, center_fmt)
            ws_grad.write(row, 3, optica_medico, row_fmt)
            ws_grad.write(row, 4, tipo, center_fmt)
            ws_grad.write(row, 5, info, row_fmt)
            ws_grad.write(row, 6, precio, money_fmt)
            ws_grad.write(row, 7, pago, money_fmt)
        
        footer_row = len(graduaciones) + 2
        ws_grad.write(footer_row, 5, "TOTAL RECAUDADO:", header_format)
        ws_grad.write(footer_row, 7, total_graduaciones, workbook.add_format({
            'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1,
            'align': 'right', 'num_format': 'S/ #,##0.00'
        }))
        
        workbook.close()
        
        return {
            'success': True, 
            'total_ventas': len(ventas), 
            'total_graduaciones': len(graduaciones),
            'total_general': total_ventas + total_graduaciones
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}
        
        # ===== WORKSHEET 3: SUNAT PLE (Formato Oficial) =====
        ws_sunat = workbook.add_worksheet("SUNAT PLE")
        
        # Headers SUNAT PLE (25 campos)
        sunat_headers = [
            "Período", "RUC", "Correlativo", "Fecha Emisión", "Fecha Vencimiento",
            "Tipo Comprobante", "Serie", "Número", "Tipo Doc", "DNI/RUC",
            "Cliente", "Importaciones", "Fase Gravada", "IGV", "Exonerado",
            "Inafecto", "ISC", "Otros Tributos", "Total", "Moneda",
            "Estado", "Referencia", "Período Ref", "Número Ref", "Observaciones"
        ]
        
        for col, header in enumerate(sunat_headers):
            ws_sunat.write(0, col, header, header_format)
        
        # Ajustar ancho de columnas
        ancho_cols = [12, 12, 14, 14, 14, 14, 10, 12, 10, 12, 20, 12, 14, 12, 12, 12, 10, 12, 14, 10, 10, 15, 12, 12, 20]
        for col, ancho in enumerate(ancho_cols):
            ws_sunat.set_column(col, col, ancho)
        
        # Generar datos SUNAT
        periodo = datetime.now().strftime('%Y%m')
        ruc_empresa = '12345678901'
        estado_format = workbook.add_format({'border': 1, 'align': 'center', 'font_size': 10})
        
        sunat_row = 1
        
        # Procesar ventas
        for idx, venta in enumerate(ventas, start=1):
            fecha_obj = parse_fecha_flexible(venta.get('fecha', ''))
            fecha_format = fecha_obj.strftime('%d/%m/%Y')
            
            cliente_dni = venta.get('paciente_dni', venta.get('cliente_dni', '00000000'))
            items = venta.get('items', [])
            cliente_nombre = venta.get('paciente_nombre', venta.get('cliente', 'CLIENTE GENÉRICO'))
            cliente = cliente_nombre if cliente_nombre != 'Público General' else ', '.join([f"{item.get('producto', 'Producto')} (x{item.get('cantidad', 1)})" for item in items[:2]]) if items else 'CLIENTE GENÉRICO'
            total = float(venta.get('total', 0))
            
            # Calcular IGV (18%)
            subtotal = total / 1.18
            igv = total - subtotal
            
            row_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2'}) if sunat_row % 2 == 0 else data_format
            money_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2' if sunat_row % 2 == 0 else 'white', 'align': 'right', 'num_format': '#,##0.00'})
            
            ws_sunat.write(sunat_row, 0, periodo, row_fmt)                    # Período
            ws_sunat.write(sunat_row, 1, ruc_empresa, row_fmt)                # RUC
            ws_sunat.write(sunat_row, 2, str(idx).zfill(7), row_fmt)          # Correlativo
            ws_sunat.write(sunat_row, 3, fecha_format, row_fmt)               # Fecha Emisión
            ws_sunat.write(sunat_row, 4, fecha_format, row_fmt)               # Fecha Vencimiento
            ws_sunat.write(sunat_row, 5, '03', row_fmt)                       # Tipo Comprobante (Boleta)
            ws_sunat.write(sunat_row, 6, 'B001', row_fmt)                     # Serie
            ws_sunat.write(sunat_row, 7, str(idx).zfill(8), row_fmt)          # Número
            ws_sunat.write(sunat_row, 8, '1', row_fmt)                        # Tipo Doc (DNI)
            ws_sunat.write(sunat_row, 9, cliente_dni, row_fmt)                # DNI/RUC
            ws_sunat.write(sunat_row, 10, cliente[:50], row_fmt)              # Cliente
            ws_sunat.write(sunat_row, 11, 0, money_fmt)                       # Importaciones
            ws_sunat.write(sunat_row, 12, subtotal, money_fmt)                # Fase Gravada
            ws_sunat.write(sunat_row, 13, igv, money_fmt)                     # IGV
            ws_sunat.write(sunat_row, 14, 0, money_fmt)                       # Exonerado
            ws_sunat.write(sunat_row, 15, 0, money_fmt)                       # Inafecto
            ws_sunat.write(sunat_row, 16, 0, money_fmt)                       # ISC
            ws_sunat.write(sunat_row, 17, 0, money_fmt)                       # Otros Tributos
            ws_sunat.write(sunat_row, 18, total, money_fmt)                   # Total
            ws_sunat.write(sunat_row, 19, 'S/', row_fmt)                      # Moneda
            ws_sunat.write(sunat_row, 20, '1', row_fmt)                       # Estado (1=válido)
            ws_sunat.write(sunat_row, 21, '', row_fmt)                        # Referencia
            ws_sunat.write(sunat_row, 22, '', row_fmt)                        # Período Ref
            ws_sunat.write(sunat_row, 23, '', row_fmt)                        # Número Ref
            ws_sunat.write(sunat_row, 24, 'VENTA POS', row_fmt)              # Observaciones
            
            sunat_row += 1
        
        # Procesar graduaciones como ingresos por servicios
        for idx, grad in enumerate(graduaciones, start=len(ventas)+1):
            fecha_obj = parse_fecha_flexible(grad.get('fecha', ''))
            fecha_format = fecha_obj.strftime('%d/%m/%Y')
            
            paciente_dni = grad.get('dni', '00000000')
            paciente = grad.get('paciente', 'PACIENTE')
            pago = float(grad.get('pago', 0))
            
            # Calcular IGV (18%)
            subtotal = pago / 1.18
            igv = pago - subtotal
            
            row_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2'}) if sunat_row % 2 == 0 else data_format
            money_fmt = workbook.add_format({'border': 1, 'bg_color': '#D9E1F2' if sunat_row % 2 == 0 else 'white', 'align': 'right', 'num_format': '#,##0.00'})
            
            ws_sunat.write(sunat_row, 0, periodo, row_fmt)                    # Período
            ws_sunat.write(sunat_row, 1, ruc_empresa, row_fmt)                # RUC
            ws_sunat.write(sunat_row, 2, str(idx).zfill(7), row_fmt)          # Correlativo
            ws_sunat.write(sunat_row, 3, fecha_format, row_fmt)               # Fecha Emisión
            ws_sunat.write(sunat_row, 4, fecha_format, row_fmt)               # Fecha Vencimiento
            ws_sunat.write(sunat_row, 5, '03', row_fmt)                       # Tipo Comprobante (Boleta)
            ws_sunat.write(sunat_row, 6, 'G001', row_fmt)                     # Serie (G para graduaciones)
            ws_sunat.write(sunat_row, 7, str(idx).zfill(8), row_fmt)          # Número
            ws_sunat.write(sunat_row, 8, '1', row_fmt)                        # Tipo Doc (DNI)
            ws_sunat.write(sunat_row, 9, paciente_dni, row_fmt)               # DNI/RUC
            ws_sunat.write(sunat_row, 10, paciente, row_fmt)                  # Cliente
            ws_sunat.write(sunat_row, 11, 0, money_fmt)                       # Importaciones
            ws_sunat.write(sunat_row, 12, subtotal, money_fmt)                # Fase Gravada
            ws_sunat.write(sunat_row, 13, igv, money_fmt)                     # IGV
            ws_sunat.write(sunat_row, 14, 0, money_fmt)                       # Exonerado
            ws_sunat.write(sunat_row, 15, 0, money_fmt)                       # Inafecto
            ws_sunat.write(sunat_row, 16, 0, money_fmt)                       # ISC
            ws_sunat.write(sunat_row, 17, 0, money_fmt)                       # Otros Tributos
            ws_sunat.write(sunat_row, 18, pago, money_fmt)                    # Total
            ws_sunat.write(sunat_row, 19, 'S/', row_fmt)                      # Moneda
            ws_sunat.write(sunat_row, 20, '1', row_fmt)                       # Estado (1=válido)
            ws_sunat.write(sunat_row, 21, '', row_fmt)                        # Referencia
            ws_sunat.write(sunat_row, 22, '', row_fmt)                        # Período Ref
            ws_sunat.write(sunat_row, 23, '', row_fmt)                        # Número Ref
            ws_sunat.write(sunat_row, 24, 'GRADUACIÓN', row_fmt)             # Observaciones
            
            sunat_row += 1
        
        # ===== WORKSHEET 4: RESUMEN CON ERRORES Y ADVERTENCIAS =====
        ws_resumen = workbook.add_worksheet("Resumen")
        
        # Título
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#1F4E78',
            'font_color': 'white',
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        
        ws_resumen.set_column('A:A', 80)
        ws_resumen.write('A1', 'RESUMEN DE VALIDACIÓN - VENTAS + GRADUACIONES', title_format)
        
        # Estadísticas
        stats_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#D9E1F2',
            'border': 1,
            'align': 'left'
        })
        
        value_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'font_size': 11
        })
        
        money_format_resumen = workbook.add_format({
            'border': 1,
            'align': 'right',
            'font_size': 11,
            'num_format': 'S/ #,##0.00'
        })
        
        row = 3
        ws_resumen.write(row, 0, '📊 ESTADÍSTICAS GENERALES', stats_format)
        row += 1
        
        ws_resumen.write(row, 0, 'Total de Ventas:', stats_format)
        ws_resumen.write(row, 1, len(ventas), value_format)
        row += 1
        
        ws_resumen.write(row, 0, 'Total de Graduaciones:', stats_format)
        ws_resumen.write(row, 1, len(graduaciones), value_format)
        row += 1
        
        ws_resumen.write(row, 0, 'Total General de Registros:', stats_format)
        ws_resumen.write(row, 1, len(ventas) + len(graduaciones), value_format)
        row += 1
        
        ws_resumen.write(row, 0, 'Total Recaudado Ventas:', stats_format)
        ws_resumen.write(row, 1, total_ventas, money_format_resumen)
        row += 1
        
        ws_resumen.write(row, 0, 'Total Recaudado Graduaciones:', stats_format)
        ws_resumen.write(row, 1, total_graduaciones, money_format_resumen)
        row += 1
        
        ws_resumen.write(row, 0, 'Total General Recaudado:', stats_format)
        ws_resumen.write(row, 1, total_ventas + total_graduaciones, money_format_resumen)
        row += 2
        
        # Detectar errores y advertencias
        errores = []
        advertencias = []
        
        # Validar ventas
        for idx, venta in enumerate(ventas, start=1):
            try:
                monto = float(venta.get('total', 0))
                dni = venta.get('paciente_dni', venta.get('cliente_dni', ''))
                
                # ERROR CRÍTICO: Monto > 700 sin DNI válido (SUNAT lo rechaza)
                if monto > 700 and not es_dni_valido(dni):
                    errores.append(f"❌ Venta #{idx}: COMPRA S/. {monto:.2f} SIN DNI VÁLIDO - SUNAT lo rechazará")
                
                # ADVERTENCIA: Monto 0.00
                if monto == 0:
                    advertencias.append(f"Venta #{idx}: Monto en 0.00")
            except (ValueError, TypeError):
                pass
        
        # Validar graduaciones
        for idx, grad in enumerate(graduaciones, start=1):
            try:
                pago = float(grad.get('pago', 0))
                dni = grad.get('dni', '')
                
                # ERROR CRÍTICO: Monto > 700 sin DNI válido (SUNAT lo rechaza)
                if pago > 700 and not es_dni_valido(dni):
                    errores.append(f"❌ Graduación #{idx}: COMPRA S/. {pago:.2f} SIN DNI VÁLIDO - SUNAT lo rechazará")
                
                # ADVERTENCIA: Monto 0.00
                if pago == 0:
                    advertencias.append(f"Graduación #{idx}: Monto en 0.00")
            except (ValueError, TypeError):
                pass
        
        # Sección ERRORES
        error_title_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#FF9999',
            'font_color': '#990000',
            'border': 1,
            'align': 'left'
        })
        
        error_text_format = workbook.add_format({
            'border': 1,
            'bg_color': '#FFCCCC',
            'font_color': '#990000',
            'align': 'left',
            'valign': 'top',
            'text_wrap': True
        })
        
        ws_resumen.write(row, 0, f'🚨 ERRORES ({len(errores)})', error_title_format)
        row += 1
        
        if errores:
            for error in errores:
                ws_resumen.write(row, 0, error, error_text_format)
                ws_resumen.set_row(row, 20)
                row += 1
        else:
            ws_resumen.write(row, 0, 'No hay errores', error_text_format)
            row += 1
        
        row += 1
        
        # Sección ADVERTENCIAS
        warning_title_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#FFFF99',
            'font_color': '#CC0000',
            'border': 1,
            'align': 'left'
        })
        
        warning_text_format = workbook.add_format({
            'border': 1,
            'bg_color': '#FFFFCC',
            'font_color': '#CC0000',
            'align': 'left',
            'valign': 'top',
            'text_wrap': True
        })
        
        ws_resumen.write(row, 0, f'⚠️ ADVERTENCIAS ({len(advertencias)})', warning_title_format)
        row += 1
        
        if advertencias:
            for adv in advertencias:
                ws_resumen.write(row, 0, adv, warning_text_format)
                ws_resumen.set_row(row, 20)
                row += 1
        else:
            ws_resumen.write(row, 0, 'No hay advertencias', warning_text_format)
            row += 1
        
        workbook.close()
        
        return {
            'success': True,
            'filepath': filepath,
            'total_ventas': len(ventas),
            'total_graduaciones': len(graduaciones),
            'total_recaudado_ventas': total_ventas,
            'total_recaudado_graduaciones': total_graduaciones,
            'total_general': total_ventas + total_graduaciones,
            'mensaje': f'Exportación combinada: {len(ventas)} ventas + {len(graduaciones)} graduaciones + SUNAT PLE'
        }
        
    except ImportError:
        return {
            'success': False,
            'error': 'Se requiere instalar xlsxwriter: pip install xlsxwriter'
        }
    except Exception as e:
        print(f"Error al generar Excel combinado: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
