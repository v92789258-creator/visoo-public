"""
Plantilla de boleta A4 para impresoras convencionales.
Formato profesional completo de 210x297mm.
Diseño: Réplica exacta Estilo Hotel Sillustani / Facturación SUNAT.
"""

import os
from datetime import datetime
from .base import PlantillaBase

class PlantillaA4(PlantillaBase):
    """Genera boletas en formato A4 con diseño profesional réplica SUNAT/Sillustani."""
    
    CONFIGURACION = {
        'ancho': 210,
        'alto': 297,
        'margen': 10,  # Margen reducido para aprovechar espacio como en la imagen
        'font_titulo': 14,
        'font_normal': 8,   # Letra más pequeña como en la factura técnica
        'font_pequeño': 7,
        'lineas_por_producto': 1,
        'mostrar_detalles': True,
    }
    
    def generar(self, datos_boleta, ruta_salida=None):
        """Genera la boleta en formato A4."""
        config = self.CONFIGURACION
        
        print(f"\n{'='*70}")
        print(f"[BOLETA A4] GENERANDO REPLICA FORMATO FACTURA...")
        print(f"{'='*70}")
        
        pdf = self._crear_pdf('P', 'mm', 'A4')
        pdf.add_page()
        pdf.set_margins(config['margen'], config['margen'], config['margen'])
        pdf.set_auto_page_break(auto=False)
        
        y = config['margen']
        ancho_util = config['ancho'] - (config['margen'] * 2)
        
        # --- 1. Encabezado (Logo + Empresa + Cuadro RUC) ---
        y = self._dibujar_encabezado_a4(pdf, datos_boleta, config, y, ancho_util)
        
        # --- 2. Información del Cliente (Cuadro grande) ---
        y = self._dibujar_informacion_a4(pdf, datos_boleta, config, y, ancho_util)
        
        # --- 3. Tabla de productos (Grilla con líneas verticales) ---
        y = self._dibujar_tabla_productos_a4(pdf, datos_boleta, config, y, ancho_util)
        
        # --- 4. Resumen (Son..., Observaciones, QR, Totales) ---
        y = self._dibujar_resumen_a4(pdf, datos_boleta, config, y, ancho_util)
        
        # --- 5. Pie de página (Hash, Web, Usuario) ---
        self._dibujar_pie_a4(pdf, datos_boleta, config, y, ancho_util)
        
        result = self._guardar_pdf(pdf, ruta_salida)
        
        print(f"[EXITO] Boleta A4 generada: {os.path.basename(result)}")
        return result
    
    def _dibujar_encabezado_a4(self, pdf, datos_boleta, config, y, ancho_util):
        """Dibuja el logo a la izquierda y el cuadro de RUC a la derecha."""
        start_y = y
        
        # Cargar configuración SUNAT
        config_sunat = self._cargar_config_sunat()
        
        # 1. LOGO (Izquierda)
        ruta_logo = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'logos', 'logo_empresa.png')
        # Si no existe logo, dejar espacio
        if os.path.exists(ruta_logo):
            pdf.image(ruta_logo, x=config['margen'], y=y, w=40) # Ajustar ancho según tu logo real
        
        # 2. CUADRO RUC (Derecha) - Estilo SUNAT
        ancho_ruc = 75
        x_ruc = config['margen'] + ancho_util - ancho_ruc
        alto_ruc = 35
        
        # Borde del cuadro RUC (Rectángulo redondeado simulado o simple)
        pdf.set_draw_color(100, 100, 100) # Gris oscuro
        pdf.set_line_width(0.3)
        pdf.rect(x_ruc, y, ancho_ruc, alto_ruc)
        
        # Contenido del Cuadro RUC
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_xy(x_ruc, y + 4)
        # Buscar RUC en orden de prioridad: datos_boleta > config_sunat > default
        ruc_empresa = (
            datos_boleta.get('ruc_empresa') or 
            datos_boleta.get('ruc') or 
            (config_sunat.get('ruc') if config_sunat else None) or 
            '20000000000'
        )
        pdf.cell(ancho_ruc, 6, f"RUC {ruc_empresa}", 0, 1, 'C')
        
        # Caja gris o texto "FACTURA ELECTRONICA" / "BOLETA"
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(x_ruc, y + 12, ancho_ruc, 10, 'F')
        
        pdf.set_font('Helvetica', 'B', 12)
        tipo_doc = "BOLETA DE VENTA ELECTRÓNICA" # O Factura según lógica
        pdf.set_xy(x_ruc, y + 14)
        pdf.cell(ancho_ruc, 6, tipo_doc, 0, 1, 'C')
        
        # Numero de comprobante
        pdf.set_font('Helvetica', '', 12)
        numero = datos_boleta.get('numero_boleta', 'B001-00000000')
        pdf.set_xy(x_ruc, y + 24)
        pdf.cell(ancho_ruc, 6, numero, 0, 1, 'C')
        
        # 3. DATOS DE LA EMPRESA EMISORA (Debajo del logo)
        # Bajamos un poco para no chocar con el logo si es muy alto, 
        # pero según la imagen, el texto empieza alineado abajo del logo o a su lado.
        # Asumiremos que el texto va DEBAJO del logo o centrado si no hay logo.
        y_texto = y + 30 # Ajuste manual para que quede bajo el logo
        if not os.path.exists(ruta_logo):
            y_texto = y
            
        pdf.set_xy(config['margen'], y_texto)
        pdf.set_font('Helvetica', 'B', 10)
        nombre_comercial = self._limpiar_texto(datos_boleta.get('nombre_optica', 'NOMBRE COMERCIAL'))
        razon_social = self._limpiar_texto(datos_boleta.get('razon_social', nombre_comercial))
        
        pdf.multi_cell(ancho_util - ancho_ruc - 5, 5, razon_social, 0, 'L')
        
        pdf.set_font('Helvetica', '', 8)
        direccion = self._limpiar_texto(datos_boleta.get('direccion_empresa', 'DIRECCIÓN DE LA EMPRESA - LIMA - PERU'))
        pdf.set_x(config['margen'])
        pdf.multi_cell(ancho_util - ancho_ruc - 5, 4, direccion, 0, 'L')
        
        # Devolver la posición Y más baja para continuar (el cuadro RUC suele ser lo más alto o el texto)
        return max(y + alto_ruc, pdf.get_y()) + 5
    
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
    
    def _dibujar_informacion_a4(self, pdf, datos_boleta, config, y, ancho_util):
        """Dibuja el cuadro rectangular con datos del cliente y fechas con mejor espaciado."""
        alto_caja = 35
        
        # Dibujar rectángulo contenedor
        pdf.set_draw_color(100, 100, 100)
        pdf.set_line_width(0.5)
        pdf.rect(config['margen'], y, ancho_util, alto_caja)
        
        # Línea vertical divisoria (al 50% del ancho)
        x_div = config['margen'] + (ancho_util / 2)
        pdf.line(x_div, y, x_div, y + alto_caja)
        
        # Línea horizontal divisoria (para separar filas)
        y_div1 = y + 8.5
        y_div2 = y + 17
        pdf.line(config['margen'], y_div1, config['margen'] + ancho_util, y_div1)
        pdf.line(config['margen'], y_div2, config['margen'] + ancho_util, y_div2)
        
        # --- COLUMNA IZQUIERDA (Cliente, RUC/DNI, Dirección) ---
        x_left = config['margen'] + 3
        h_row = 7
        
        # FILA 1: CLIENTE
        y_row = y + 1
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(x_left, y_row)
        pdf.cell(20, h_row, "CLIENTE:", 0, 0, 'L')
        pdf.set_font('Helvetica', '', 7)
        cliente = self._limpiar_texto(datos_boleta.get('cliente', 'CLIENTE'))
        pdf.set_xy(x_left + 22, y_row)
        ancho_valor_left = (ancho_util / 2) - 28
        pdf.cell(ancho_valor_left, h_row, cliente, 0, 1, 'L')
        
        # FILA 2: RUC/DNI
        y_row = y + 8.8
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(x_left, y_row)
        pdf.cell(20, h_row, "RUC/DNI:", 0, 0, 'L')
        pdf.set_font('Helvetica', '', 7)
        dni_valor = datos_boleta.get('dni', datos_boleta.get('ruc_cliente', None))
        
        # Si no hay DNI, mostrar guión
        if not dni_valor or dni_valor is None or str(dni_valor).strip() == '':
            dni_valor = '-'
        else:
            dni_valor = self._limpiar_texto(str(dni_valor))
            # Solo mostrar "AI CLIENTE GENERICO" si es explícitamente 00000000
            if dni_valor == '00000000':
                dni_valor = 'AI CLIENTE GENERICO'
        
        pdf.set_xy(x_left + 22, y_row)
        pdf.cell(ancho_valor_left, h_row, dni_valor, 0, 1, 'L')
        
        # FILA 3: DIRECCIÓN
        y_row = y + 17.3
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(x_left, y_row)
        pdf.cell(20, h_row, "DIRECCIÓN:", 0, 0, 'L')
        pdf.set_font('Helvetica', '', 6)
        direccion = self._limpiar_texto(datos_boleta.get('direccion_cliente', '-'))
        pdf.set_xy(x_left + 22, y_row)
        pdf.multi_cell(ancho_valor_left, 3, direccion, 0, 'L')
        
        # --- COLUMNA DERECHA (Fechas y Moneda) ---
        x_right = x_div + 3
        h_row = 7
        
        # FILA 1: FECHA EMISIÓN
        y_row = y + 1
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(x_right, y_row)
        pdf.cell(28, h_row, "FECHA EMISIÓN:", 0, 0, 'L')
        pdf.set_font('Helvetica', '', 7)
        fecha = datos_boleta.get('fecha', datetime.now().strftime("%d/%m/%Y"))
        pdf.set_xy(x_right + 30, y_row)
        pdf.cell(35, h_row, str(fecha), 0, 1, 'L')
        
        # FILA 2: FECHA VENCIMIENTO
        y_row = y + 8.8
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(x_right, y_row)
        pdf.cell(28, h_row, "FECHA VENCIMIENTO:", 0, 0, 'L')
        pdf.set_font('Helvetica', '', 7)
        fecha_venc = datos_boleta.get('fecha_vencimiento', datetime.now().strftime("%d/%m/%Y"))
        pdf.set_xy(x_right + 30, y_row)
        pdf.cell(35, h_row, str(fecha_venc), 0, 1, 'L')
        
        # FILA 3: MONEDA y FORMA DE PAGO
        y_row = y + 17.3
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(x_right, y_row)
        pdf.cell(28, h_row, "MONEDA:", 0, 0, 'L')
        pdf.set_font('Helvetica', '', 7)
        moneda = datos_boleta.get('moneda', 'SOLES')
        pdf.set_xy(x_right + 30, y_row)
        pdf.cell(35, h_row, str(moneda), 0, 1, 'L')
        
        y_row = y + 26
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(x_right, y_row)
        pdf.cell(28, h_row, "FORMA DE PAGO:", 0, 0, 'L')
        pdf.set_font('Helvetica', '', 7)
        forma_pago = datos_boleta.get('metodo_pago', 'CONTADO')
        pdf.set_xy(x_right + 30, y_row)
        pdf.cell(35, h_row, str(forma_pago), 0, 1, 'L')
            
        return y + alto_caja + 2
    
    def _dibujar_tabla_productos_a4(self, pdf, datos_boleta, config, y, ancho_util):
        """Dibuja la tabla con estilo de grilla (bordes grises y fondo encabezado)."""
        
        # Definición de columnas y anchos (Proporcionales al 100%)
        # N, CANT, UD, CODIGO, DESCRIPCION, V.UNIT, IGV (18%), P.UNIT, TOTAL
        cols = [
            {'name': 'N°', 'w': 0.05, 'align': 'C'},
            {'name': 'CANT.', 'w': 0.08, 'align': 'C'},
            {'name': 'UD.', 'w': 0.06, 'align': 'C'},
            {'name': 'CODIGO', 'w': 0.10, 'align': 'C'},
            {'name': 'DESCRIPCIÓN', 'w': 0.35, 'align': 'L'},  # El más ancho
            {'name': 'V.UNIT', 'w': 0.10, 'align': 'R'},
            {'name': 'IGV 18%', 'w': 0.08, 'align': 'R'},
            {'name': 'P.UNIT', 'w': 0.10, 'align': 'R'},  # Con IGV
            {'name': 'TOTAL', 'w': 0.08, 'align': 'R'}
        ]
        
        # Calcular anchos en mm
        widths = [ancho_util * c['w'] for c in cols]
        
        # --- ENCABEZADO ---
        alto_header = 6
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_fill_color(200, 200, 200)  # Gris claro
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(150, 150, 150)
        
        x_curr = config['margen']
        pdf.set_y(y)
        
        # Dibujar celdas de encabezado con borde y fondo
        for i, col in enumerate(cols):
            pdf.set_x(x_curr)
            pdf.cell(widths[i], alto_header, col['name'], 1, 0, 'C', True)
            x_curr += widths[i]
        
        y += alto_header
        
        # --- PRODUCTOS ---
        y_inicio_tabla = y
        alto_minimo_tabla = 80  # Espacio mínimo para la tabla
        
        pdf.set_font('Helvetica', '', 7)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(150, 150, 150)
        
        items = self._normalizar_productos(datos_boleta.get('productos', []))
        
        # Tasa IGV (18%)
        TASA_IGV = 0.18
        
        for idx, prod in enumerate(items, 1):
            x_curr = config['margen']
            
            # Calcular valores de IGV
            cantidad = float(prod.get('cantidad', 1))
            precio_unitario = float(prod.get('precio', 0))
            
            # Valor unitario SIN IGV (precio / 1.18)
            valor_unitario = precio_unitario / (1 + TASA_IGV)
            
            # IGV por unidad
            igv_unitario = valor_unitario * TASA_IGV
            
            # Total sin IGV
            valor_total = valor_unitario * cantidad
            
            # IGV total
            igv_total = igv_unitario * cantidad
            
            # Precio total con IGV
            precio_total = precio_unitario * cantidad
            
            # Datos formateados
            vals = [
                str(idx),
                f"{cantidad:.2f}",
                prod.get('unidad', 'UNI'),
                prod.get('codigo', '-'),
                self._limpiar_texto(prod.get('nombre', 'Producto')),
                f"{valor_unitario:.2f}",      # Valor sin IGV
                f"{igv_unitario:.2f}",        # IGV unitario (18%)
                f"{precio_unitario:.2f}",      # Precio unitario con IGV
                f"{precio_total:.2f}"          # Total con IGV
            ]
            
            # Altura de la fila
            pdf.set_xy(x_curr + sum(widths[:4]), y)
            lines = pdf.multi_cell(widths[4], 4, vals[4], 0, 'L', split_only=True)
            row_h = max(5, len(lines) * 4)
            
            # Verificar salto de página
            if y + row_h > 270:
                pdf.add_page()
                y = config['margen']
            
            # Dibujar celdas
            for i, val in enumerate(vals):
                pdf.set_xy(x_curr, y)
                align = cols[i]['align']
                # Si es descripción usamos multicell, resto cell
                if i == 4:
                    pdf.multi_cell(widths[i], 4, val, 0, align)
                else:
                    pdf.cell(widths[i], row_h, val, 0, 0, align)
                x_curr += widths[i]
            
            y += row_h
            
        # --- FINALIZAR TABLA ---
        y_final_tabla = max(y, y_inicio_tabla + alto_minimo_tabla)
        
        # Dibujar el rectángulo exterior de la tabla
        pdf.set_draw_color(100, 100, 100)
        pdf.rect(config['margen'], y_inicio_tabla, ancho_util, y_final_tabla - y_inicio_tabla)
        
        # Dibujar líneas verticales
        x_line = config['margen']
        for w in widths[:-1]:
            x_line += w
            pdf.line(x_line, y_inicio_tabla, x_line, y_final_tabla)
            
        return y_final_tabla + 2

    def _dibujar_resumen_a4(self, pdf, datos_boleta, config, y, ancho_util):
        """Dibuja 'SON: ...', Observaciones, QR y Cuadro de Totales."""
        
        # 1. TEXTO MONTO EN LETRAS
        pdf.set_font('Helvetica', 'B', 9)  # Negrita
        pdf.set_xy(config['margen'], y)
        # Borde superior e inferior para esta linea
        pdf.line(config['margen'], y, config['margen'] + ancho_util, y)
        
        monto_letras = datos_boleta.get('monto_letras', 'CERO CON 00/100 SOLES')
        pdf.cell(ancho_util, 8, f"SON: {monto_letras}", 0, 1, 'L')
        
        y += 8
        pdf.line(config['margen'], y, config['margen'] + ancho_util, y)
        y += 2
        
        # Dividimos espacio inferior: Izquierda (Observaciones + QR), Derecha (Totales)
        y_start_bottom = y
        ancho_totales = 75
        ancho_obs = ancho_util - ancho_totales - 5
        
        # --- OBSERVACIONES ---
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_xy(config['margen'], y)
        pdf.cell(ancho_obs, 5, "OBSERVACIONES:", 0, 1, 'L')
        
        # Caja de observaciones (Solo borde)
        pdf.set_draw_color(150, 150, 150)
        pdf.rect(config['margen'], y + 5, ancho_obs, 12)
        # Texto observación
        pdf.set_font('Helvetica', '', 7)
        pdf.set_xy(config['margen'] + 1, y + 6)
        obs = datos_boleta.get('observaciones', '')
        pdf.multi_cell(ancho_obs - 2, 4, obs, 0, 'L')
        
        # --- CUADRO DE TOTALES (Derecha) ---
        x_totales = config['margen'] + ancho_util - ancho_totales
        y_tot = y_start_bottom
        
        # Marco del cuadro totales
        pdf.set_draw_color(100, 100, 100)
        pdf.rect(x_totales, y_tot, ancho_totales, 45)
        
        # Calcular totales desde productos
        TASA_IGV = 0.18
        subtotal_sin_igv = 0
        igv_total = 0
        
        productos = self._normalizar_productos(datos_boleta.get('productos', []))
        for prod in productos:
            precio = float(prod.get('precio', 0))
            cantidad = float(prod.get('cantidad', 1))
            
            # Precio unitario sin IGV
            precio_sin_igv = precio / (1 + TASA_IGV)
            
            # Acumular
            subtotal_sin_igv += precio_sin_igv * cantidad
            igv_total += (precio_sin_igv * TASA_IGV) * cantidad
        
        descuento = float(datos_boleta.get('descuento', 0))
        total_final = subtotal_sin_igv + igv_total - descuento
        
        # Filas de totales
        totales_map = [
            ("OP. GRAVADAS: S/", f"{subtotal_sin_igv:.2f}"),
            ("OP. EXONERADAS: S/", "0.00"),
            ("SUB TOTAL: S/", f"{subtotal_sin_igv:.2f}"),
            ("DESCUENTOS: S/", f"{descuento:.2f}"),
            ("IGV 18%: S/", f"{igv_total:.2f}"),
        ]
        
        pdf.set_font('Helvetica', '', 7)
        h_row = 4.5
        curr_y_tot = y_tot + 1
        
        for label, val in totales_map:
            pdf.set_xy(x_totales + 1, curr_y_tot)
            pdf.cell(45, h_row, label, 0, 0, 'L')
            pdf.set_xy(x_totales + 47, curr_y_tot)
            pdf.cell(27, h_row, val, 0, 1, 'R')
            curr_y_tot += h_row
            
        # TOTAL FINAL (Fondo Gris)
        pdf.set_fill_color(200, 200, 200)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_xy(x_totales, curr_y_tot)
        pdf.cell(45, 7, "TOTAL: S/", 1, 0, 'L', True)
        pdf.cell(27, 7, f"{total_final:.2f}", 1, 1, 'R', True)
        curr_y_tot += 7
        
        # Mostrar pago parcial si existe o si hay deuda pendiente
        monto_pagado = float(datos_boleta.get('monto_pagado', total_final))
        monto_debe = total_final - monto_pagado
        es_pago_parcial = datos_boleta.get('es_pago_parcial', False)
        
        if es_pago_parcial or monto_debe > 0.05:
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('Helvetica', '', 7)
            
            # PAGADO
            pdf.set_xy(x_totales + 1, curr_y_tot)
            pdf.cell(45, h_row, "PAGADO: S/", 0, 0, 'L')
            pdf.set_xy(x_totales + 47, curr_y_tot)
            pdf.cell(27, h_row, f"{monto_pagado:.2f}", 0, 1, 'R')
            curr_y_tot += h_row
            
            # DEBE (solo si es mayor a 0)
            if monto_debe > 0.05:
                pdf.set_font('Helvetica', 'B', 7)
                pdf.set_xy(x_totales + 1, curr_y_tot)
                pdf.cell(45, h_row, "DEBE: S/", 0, 0, 'L')
                pdf.set_xy(x_totales + 47, curr_y_tot)
                pdf.cell(27, h_row, f"{monto_debe:.2f}", 0, 1, 'R')
        
        return max(y + 35, curr_y_tot + 10)

    
    def _dibujar_pie_a4(self, pdf, datos_boleta, config, y, ancho_util):
        """Pie de página con usuario, hash y branding."""
        y = 275 # Forzamos al final de la hoja A4
        
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_xy(config['margen'], y)
        
        # Info Usuario y Fecha Impresión
        usuario = datos_boleta.get('vendedor', 'admin')
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        pdf.cell(ancho_util, 3, f"USUARIO: {usuario} {ahora}", 0, 1, 'L')
        
        # Texto Legal SUNAT
        pdf.set_font('Helvetica', '', 7)
        texto_legal = "Representación impresa del Comprobante Electrónico."
        pdf.cell(ancho_util, 3, texto_legal, 0, 1, 'L')
        
        # Hash (Simulado) y URL Consulta
        hash_code = "Consulte su comprobante."
        pdf.cell(ancho_util, 3, hash_code, 0, 1, 'L')
        
        # Branding Centrado
        y += 10
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_xy(config['margen'], y)
        pdf.cell(ancho_util, 4, "VISO", 0, 1, 'C')
        
        pdf.set_font('Helvetica', '', 7)
        pdf.cell(ancho_util, 3, "Comprobante emitido a través de api.yhana.cloud", 0, 1, 'C')
