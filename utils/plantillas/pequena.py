"""
Plantilla de boleta pequeña para impresoras térmicas (80mm).
Diseño profesional con Logo, QR, y detalles completos.
"""

import os
import tempfile
from datetime import datetime
from .base import PlantillaBase


class PlantillaPequena(PlantillaBase):
    """Genera boletas pequeñas profesionales para impresoras térmicas."""
    
    CONFIGURACION = {
        'ancho': 80,
        'alto': 200,  # Altura inicial referencial
        'margen': 3,  # Margen reducido para aprovechar espacio
        'font_titulo': 10,
        'font_subtitulo': 9,
        'font_normal': 8,
        'font_pequeño': 7,
        'font_micro': 6,
        'lineas_por_producto': 2,
        'mostrar_detalles': True,
    }
    
    def generar(self, datos_boleta, ruta_salida=None):
        """Genera la boleta pequeña con altura exacta (Simulación previa)."""
        config = self.CONFIGURACION
        
        # Cargar datos SUNAT para completar información de la empresa
        config_sunat = self._cargar_config_sunat()
        
        print(f"\n{'='*70}")
        print(f"[BOLETA PEQUEÑA] INICIANDO GENERACIÓN OPTIMIZADA...")
        
        # 1. PREPARACIÓN DE RECURSOS
        # Verificar logo
        ruta_logo = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'logos', 'logo_empresa.png'
        )
        tiene_logo = os.path.exists(ruta_logo)
        
        # Preparar QR
        qr_data = datos_boleta.get('qr_data', self._construir_qr_data(datos_boleta, config_sunat))
        img_qr = self._generar_qr(qr_data) if qr_data else None
        
        # 2. CÁLCULO DE ALTURA EXACTA (SIMULACIÓN)
        print("[BOLETA] Simulando impresión para cálculo de papel...")
        # Usamos un PDF temporal muy alto para medir
        pdf_simul = self._crear_pdf('P', 'mm', (config['ancho'], 2000))
        pdf_simul.add_page()
        pdf_simul.set_margins(config['margen'], config['margen'], config['margen'])
        pdf_simul.set_auto_page_break(auto=False)
        
        # Ejecutamos dibujo simulado
        y_final_simulado = self._ejecutar_dibujo(
            pdf_simul, datos_boleta, config, 
            tiene_logo, ruta_logo, img_qr, config_sunat
        )
        
        # Calculamos altura final exacta + pequeño margen inferior (3mm)
        altura_real = y_final_simulado + 3
        print(f"[BOLETA] Altura exacta calculada: {altura_real:.2f} mm")
        
        # 3. GENERACIÓN FINAL
        pdf = self._crear_pdf('P', 'mm', (config['ancho'], altura_real))
        pdf.add_page()
        pdf.set_margins(config['margen'], config['margen'], config['margen'])
        pdf.set_auto_page_break(auto=False)
        
        # Dibujo real
        self._ejecutar_dibujo(
            pdf, datos_boleta, config, 
            tiene_logo, ruta_logo, img_qr, config_sunat
        )
        
        # Guardar
        result = self._guardar_pdf(pdf, ruta_salida)
        print(f"[EXITO] Boleta optimizada generada: {os.path.basename(result)}")
        print(f"{'='*70}\n")
        
        return result

    def _ejecutar_dibujo(self, pdf, datos, config, tiene_logo, ruta_logo, img_qr, config_sunat=None):
        """Orquesta el dibujo de todos los componentes y retorna la Y final."""
        y = config['margen']
        ancho_util = config['ancho'] - (config['margen'] * 2)
        
        # 1. Logo y Encabezado
        y = self._dibujar_encabezado(pdf, datos, config, y, ancho_util, tiene_logo, ruta_logo, config_sunat)
        
        # 2. Información del Documento y Cliente
        y = self._dibujar_info_documento(pdf, datos, config, y, ancho_util)
        
        # 3. Detalles de Productos
        y = self._dibujar_productos(pdf, datos, config, y, ancho_util)
        
        # 4. Totales
        y = self._dibujar_totales(pdf, datos, config, y, ancho_util)
        
        # 5. Código QR
        if img_qr:
            y = self._dibujar_qr(pdf, img_qr, config, y, ancho_util)
        
        # 6. Pie de página
        self._dibujar_pie(pdf, datos, config, y, ancho_util)
        
        # Retornamos la posición Y final real (donde termina el contenido)
        return pdf.get_y()
    
    def _cargar_config_sunat(self):
        """Carga la configuración de SUNAT para obtener RUC y datos de la empresa."""
        try:
            import json
            from utils.file_handler import VISO_DIR, resolve_username
            username_canonico = resolve_username(self.usuario_id)
            ruta_config = os.path.join(VISO_DIR, username_canonico, 'data', 'sunat', 'config_sunat.json')
            
            if os.path.exists(ruta_config):
                with open(ruta_config, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"[WARN] config_sunat.json no encontrado en: {ruta_config}")
        except Exception as e:
            print(f"[WARN] No se pudo cargar config_sunat.json: {e}")
        return {}
    
    def _construir_qr_data(self, datos, config_sunat=None):
        """Construye una cadena para el QR con los datos disponibles."""
        # Prioridad para RUC de la empresa
        ruc_empresa = (
            datos.get('ruc') or 
            (config_sunat.get('ruc') if config_sunat else None) or 
            '00000000000'
        )
        
        parts = [
            str(ruc_empresa),
            '03',  # Tipo Boleta
            datos.get('numero_boleta', 'B000-00000000')[:4],
            datos.get('numero_boleta', 'B000-00000000')[5:],
            f"{datos.get('igv', 0):.2f}",
            f"{datos.get('total', 0):.2f}",
            datos.get('fecha', datetime.now().strftime('%Y-%m-%d')),
            '1',  # Tipo Doc Cliente (1=DNI)
            str(datos.get('dni', '00000000'))
        ]
        return '|'.join(parts)


    def _dibujar_encabezado(self, pdf, datos, config, y, ancho, tiene_logo, ruta_logo, config_sunat=None):
        """Dibuja logo y datos de la empresa."""
        # Nombre de la óptica (Prioridad: datos > config_sunat > 'ÓPTICA')
        nombre_empresa = (
            datos.get('nombre_optica') or 
            (config_sunat.get('razon_social') if config_sunat else None) or 
            'ÓPTICA'
        )
        
        # Dirección (Prioridad: datos > config_sunat > 'Dirección Principal')
        direccion = (
            datos.get('direccion_empresa') or 
            (config_sunat.get('direccion') if config_sunat else None) or 
            'Dirección Principal'
        )
        
        # RUC (Prioridad: datos.ruc > datos.ruc_empresa > config_sunat.ruc > '00000000000')
        ruc = (
            datos.get('ruc') or 
            datos.get('ruc_empresa') or 
            (config_sunat.get('ruc') if config_sunat else None) or 
            '00000000000'
        )

        if tiene_logo:
            try:
                # Calcular tamaño del logo respetando configuración
                if self.tamano_logo_px:
                    # Convertir aprox de px a mm (dividido por 10 y limitado entre 20 y 55mm)
                    w_logo = min(55, max(20, self.tamano_logo_px / 10))
                else:
                    w_logo = 30 # Default más conservador
                
                x_logo = config['margen'] + (ancho - w_logo) / 2
                pdf.image(ruta_logo, x=x_logo, y=y, w=w_logo)
                y += w_logo + 2
            except:
                y += 5
        
        # Nombre Empresa
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_xy(config['margen'], y)
        pdf.multi_cell(ancho, 5, self._limpiar_texto(nombre_empresa), 0, 'C')
        y = pdf.get_y() + 1
        
        # Dirección y Contacto
        pdf.set_font('Helvetica', '', 7)
        telefono = self._limpiar_texto(datos.get('telefono_empresa', ''))
        
        pdf.set_xy(config['margen'], y)
        pdf.multi_cell(ancho, 3.5, self._limpiar_texto(direccion), 0, 'C')
        y = pdf.get_y()
        
        if telefono:
            pdf.set_xy(config['margen'], y)
            pdf.cell(ancho, 3.5, f"Telf: {telefono}", 0, 1, 'C')
            y += 3.5
            
        # RUC
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_xy(config['margen'], y + 1)
        pdf.cell(ancho, 4, f"RUC: {ruc}", 0, 1, 'C')
        y += 6
        
        self._dibujar_separador(pdf, config, y, ancho, doble=True)
        y += 2
        
        return y

    def _dibujar_info_documento(self, pdf, datos, config, y, ancho):
        """Dibuja número de boleta, fecha y cliente."""
        # Título del documento
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_xy(config['margen'], y)
        pdf.cell(ancho, 5, "BOLETA DE VENTA ELECTRÓNICA", 0, 1, 'C')
        y += 5
        
        pdf.set_font('Helvetica', '', 9)
        serie_numero = self._limpiar_texto(datos.get('numero_boleta', 'B000-000000'))
        pdf.cell(ancho, 5, serie_numero, 0, 1, 'C')
        y += 7
        
        # Tabla de datos (Fecha, Cliente, DNI)
        pdf.set_font('Helvetica', '', 8)
        
        # Función helper para filas de datos
        def fila_dato(etiqueta, valor):
            pdf.set_font('Helvetica', 'B', 8)
            pdf.cell(18, 4, etiqueta, 0, 0, 'L')
            pdf.set_font('Helvetica', '', 8)
            # Ajustar ancho restante
            pdf.multi_cell(ancho - 18, 4, str(valor), 0, 'L')
            
        pdf.set_xy(config['margen'], y)
        fila_dato("Fecha:", datos.get('fecha', ''))
        y = pdf.get_y()
        
        pdf.set_xy(config['margen'], y)
        fila_dato("Cliente:", self._limpiar_texto(datos.get('cliente', 'VARIOS')))
        y = pdf.get_y()
        
        # Intentar obtener DNI o RUC del cliente
        doc_identidad = datos.get('dni') or datos.get('ruc_cliente') or ''
        if doc_identidad:
            pdf.set_xy(config['margen'], y)
            fila_dato("DNI/RUC:", doc_identidad)
            y = pdf.get_y()
            
        vendedor = datos.get('vendedor', '')
        if vendedor:
            pdf.set_xy(config['margen'], y)
            fila_dato("Vendedor:", self._limpiar_texto(vendedor))
            y = pdf.get_y()

        condicion = datos.get('metodo_pago', 'Contado')
        pdf.set_xy(config['margen'], y)
        fila_dato("Condición:", condicion)
        y = pdf.get_y() + 2
        
        self._dibujar_separador(pdf, config, y, ancho)
        y += 2
        return y

    def _dibujar_productos(self, pdf, datos, config, y, ancho):
        """Dibuja la lista de productos."""
        # Encabezados
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(config['margen'], y)
        
        col_cant = 8
        col_tot = 15
        col_desc = ancho - col_cant - col_tot
        
        pdf.cell(col_cant, 4, "CANT.", 0, 0, 'C')
        pdf.cell(col_desc, 4, "DESCRIPCIÓN", 0, 0, 'L')
        pdf.cell(col_tot, 4, "TOTAL", 0, 1, 'R')
        y += 5
        
        # Productos
        pdf.set_font('Helvetica', '', 7)
        
        for p in self._normalizar_productos(datos.get('productos', [])):
            nombre = self._limpiar_texto(p.get('nombre', 'Producto'))
            cant = p.get('cantidad', 1)
            total = p.get('total', 0)
            
            # Guardar Y inicial de la fila
            y_inicio = y
            
            # Imprimir cantidad y total alineados arriba
            pdf.set_xy(config['margen'], y)
            pdf.cell(col_cant, 4, f"{cant}", 0, 0, 'C')
            
            # Imprimir Total a la derecha
            pdf.set_xy(config['margen'] + col_cant + col_desc, y)
            pdf.cell(col_tot, 4, f"{total:.2f}", 0, 0, 'R')
            
            # Imprimir descripción (puede ser multilinea)
            pdf.set_xy(config['margen'] + col_cant, y)
            pdf.multi_cell(col_desc, 4, nombre, 0, 'L')
            
            # Nueva Y será la mayor entre lo que ocupó la descripción y una línea simple
            y = max(pdf.get_y(), y_inicio + 4)
            
        y += 2
        self._dibujar_separador(pdf, config, y, ancho)
        y += 2
        return y

    def _dibujar_totales(self, pdf, datos, config, y, ancho):
        """Dibuja los totales alineados a la derecha."""
        pdf.set_font('Helvetica', '', 8)
        
        # Helper para líneas de totales
        def linea_total(texto, valor, bold=False):
            pdf.set_font('Helvetica', 'B' if bold else '', 8 if not bold else 9)
            pdf.set_xy(config['margen'] + (ancho * 0.4), y_local)
            pdf.cell(ancho * 0.35, 4, texto, 0, 0, 'R')
            pdf.cell(ancho * 0.25, 4, f"{valor:.2f}", 0, 1, 'R')
            return 4

        y_local = y
        subtotal = datos.get('subtotal', 0)
        igv = datos.get('igv', 0)
        total = datos.get('total', 0)
        descuento = datos.get('descuento', 0)
        
        # Op. Gravada (Subtotal)
        y_local += linea_total("OP. GRAVADA: S/", subtotal)
        
        # IGV
        y_local += linea_total("IGV (18%): S/", igv)
        
        # Descuento si existe
        if descuento > 0:
            y_local += linea_total("DESCUENTO: -S/", descuento)
        
        # Mostrar pago parcial si existe o si hay deuda pendiente
        monto_pagado = float(datos.get('monto_pagado', total))
        monto_debe = total - monto_pagado
        es_pago_parcial = datos.get('es_pago_parcial', False)
        
        if es_pago_parcial or monto_debe > 0.05:
            pdf.set_font('Helvetica', '', 7)
            # Línea de lo que pagó
            y_local = y_local + 1  # Pequeño espacio
            pdf.set_xy(config['margen'] + (ancho * 0.4), y_local)
            pdf.cell(ancho * 0.35, 4, "PAGADO: S/", 0, 0, 'R')
            pdf.cell(ancho * 0.25, 4, f"{monto_pagado:.2f}", 0, 1, 'R')
            y_local += 4
            
            # Línea de lo que debe (solo si es mayor a 0)
            if monto_debe > 0.05:
                pdf.set_font('Helvetica', 'B', 7)
                pdf.set_xy(config['margen'] + (ancho * 0.4), y_local)
                pdf.cell(ancho * 0.35, 4, "DEBE: S/", 0, 0, 'R')
                pdf.cell(ancho * 0.25, 4, f"{monto_debe:.2f}", 0, 1, 'R')
                y_local += 4
            
        # Total
        y_local += 1 # Espacio
        y = y_local
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_xy(config['margen'] + (ancho * 0.3), y)
        pdf.cell(ancho * 0.45, 5, "IMPORTE TOTAL: S/", 0, 0, 'R')
        pdf.cell(ancho * 0.25, 5, f"{total:.2f}", 0, 1, 'R')
        y += 6
        

        # Monto en letras
        letras = self._limpiar_texto(datos.get('monto_letras', ''))
        if letras:
            pdf.set_font('Helvetica', 'I', 7)
            pdf.set_xy(config['margen'], y)
            pdf.multi_cell(ancho, 3.5, f"SON: {letras}", 0, 'L')
            y = pdf.get_y() + 2
            
        self._dibujar_separador(pdf, config, y, ancho)
        y += 2
        return y

    def _dibujar_qr(self, pdf, img_qr_bytes, config, y, ancho):
        """Dibuja el código QR centrado."""
        try:
            # Guardar bytes en archivo temporal porque FPDF image() prefiere paths
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                tmp.write(img_qr_bytes.getvalue())
                tmp_path = tmp.name
            
            size = 30
            x = config['margen'] + (ancho - size) / 2
            pdf.image(tmp_path, x=x, y=y, w=size)
            
            # Limpiar temp
            try:
                os.unlink(tmp_path)
            except:
                pass
                
            y += size + 2
        except Exception as e:
            print(f"[ERROR] Al dibujar QR: {e}")
            pdf.set_xy(config['margen'], y)
            pdf.cell(ancho, 5, "[QR ERROR]", 0, 1, 'C')
            y += 5
            
        return y

    def _dibujar_pie(self, pdf, datos, config, y, ancho):
        """Pie de página con textos legales."""
        pdf.set_font('Helvetica', '', 7)
        pdf.set_xy(config['margen'], y)
        
        # Texto legal
        texto_legal = (
            "Representación impresa de la BOLETA DE VENTA ELECTRÓNICA. "
        )
        pdf.multi_cell(ancho, 3, texto_legal, 0, 'C')
        y = pdf.get_y() + 3
        
        # Mensaje final
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_xy(config['margen'], y)
        pdf.cell(ancho, 4, "¡GRACIAS POR SU PREFERENCIA!", 0, 1, 'C')
        y += 4
        
        # Timestamp
        pdf.set_font('Helvetica', 'I', 6)
        pdf.set_text_color(100, 100, 100)
        pdf.set_xy(config['margen'], y)
        pdf.cell(ancho, 3, f"Impreso: {self._obtener_timestamp_actual()}", 0, 1, 'C')

    def _dibujar_separador(self, pdf, config, y, ancho, doble=False):
        """Dibuja una línea separadora punteada."""
        pdf.set_line_width(0.2)
        pdf.set_draw_color(0, 0, 0)
        
        # Simular línea punteada con guiones
        pdf.set_font('Courier', '', 8) # Courier es monoespaciada, bueno para guiones
        texto_linea = "-" * int(ancho / 2) # Aprox
        
        pdf.set_xy(config['margen'], y)
        # Usamos line() de FPDF mejor para control
        if doble:
            pdf.line(config['margen'], y, config['margen'] + ancho, y)
            pdf.line(config['margen'], y+0.5, config['margen'] + ancho, y+0.5)
        else:
            # Línea discontinua manual
            start_x = config['margen']
            end_x = config['margen'] + ancho
            curr_x = start_x
            while curr_x < end_x:
                pdf.line(curr_x, y, min(curr_x + 1, end_x), y)
                curr_x += 2 # 1mm linea, 1mm espacio 
