import os
import datetime
import qrcode
from fpdf import FPDF
from io import BytesIO

# Para la conversión de números a palabras
try:
    from num2words import num2words
except ImportError:
    print("Advertencia: La biblioteca 'num2words' no está instalada.")
    num2words = None

from utils.file_handler import get_user_file_path, VISO_DIR

def _set_pdf_page_size(pdf_path, ancho_mm, alto_mm):
    """
    Modifica el PDF para establecer el tamaño de página exacto.
    Esto permite que Chrome detecte correctamente el tamaño personalizado.
    """
    try:
        try:
            from pypdf import PdfReader, PdfWriter
            from pypdf.generic import RectangleObject
        except ImportError:
            # Fallback a PyPDF2 si pypdf no está disponible
            try:
                from PyPDF2 import PdfReader, PdfWriter
                from PyPDF2.generic import RectangleObject
            except ImportError:
                print("[WARN] ni pypdf ni PyPDF2 están instalados, saltando configuración de tamaño")
                return False
        
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Convertir mm a puntos (1mm = 2.834645669 puntos)
        pt_width = ancho_mm * 2.834645669
        pt_height = alto_mm * 2.834645669
        
        # Copiar páginas y establecer tamaño
        for page in reader.pages:
            page.mediabox = RectangleObject([0, 0, pt_width, pt_height])
            page.cropbox = RectangleObject([0, 0, pt_width, pt_height])
            writer.add_page(page)
        
        # Escribir el PDF modificado
        with open(pdf_path, 'wb') as f:
            writer.write(f)
        
        print(f"[PDF] Tamaño de página establecido: {ancho_mm}mm × {alto_mm:.2f}mm")
        return True
        
    except Exception as e:
        print(f"[WARN] Error estableciendo tamaño: {e}")
        return False

def _limpiar_texto(texto):
    """Limpia caracteres especiales que causan problemas de codificación."""
    if not isinstance(texto, str):
        texto = str(texto)
    
    # Reemplazar caracteres problemáticos
    reemplazos = {
        '—': '-',      # Raya larga
        '–': '-',      # En-dash
        '…': '...',    # Elipsis
        '"': '"',      # Comilla izquierda
        '"': '"',      # Comilla derecha
        ''': "'",      # Apóstrofo
        ''': "'",      # Apóstrofo derecho
        '€': 'EUR',    # Euro
        '±': '+/-',    # Más-menos
    }
    
    for char, reemplazo in reemplazos.items():
        texto = texto.replace(char, reemplazo)
    
    # Remover cualquier carácter no ASCII o que no sea imprimible
    texto = ''.join(c for c in texto if ord(c) < 128 or c in 'áéíóúñÁÉÍÓÚÑ')
    
    return texto

def number_to_words(number):
    """Convierte un número a palabras en español."""
    if num2words is None:
        return "ERROR: Instale 'num2words' para esta función."
    
    try:
        entero = int(number)
        decimal = int(round((number - entero) * 100))
        centimos_texto = str(decimal).zfill(2)
        return f"{num2words(entero, lang='es').upper()} CON {centimos_texto}/100 SOLES"
    except Exception as e:
        return f"Error en la conversión: {e}"

class BfoletaPDF(FPDF):
    """Clase personalizada para generar boletas con medidas exactas y diseño profesional."""
    
    def __init__(self, ancho_mm, alto_mm):
        super().__init__(format=(ancho_mm, alto_mm))
        self.set_auto_page_break(auto=False)
        # Configuración para impresión óptima
        self.compress = False  # No comprimir para mejor calidad de impresión
        self.set_display_mode('fullpage')  # Mostrar página completa

def _dibujar_separador(pdf, margen_mm, ancho_mm):
    """Dibuja una línea separadora profesional."""
    pdf.set_draw_color(100, 100, 100)
    pdf.line(margen_mm + 1, pdf.get_y(), ancho_mm - margen_mm - 1, pdf.get_y())


def _calcular_tamaño_fuente(tamaño_base, ancho_mm):
    """
    Calcula el tamaño de fuente ajustado según el ancho de la boleta.
    Los tamaños base están calibrados para 80mm.
    """
    # Factor de escala basado en el ancho (80mm es el base)
    factor = ancho_mm / 80.0
    # Limitar escala mínima a 0.7 para legibilidad (para boletas muy pequeñas)
    factor = max(factor, 0.7)
    return max(tamaño_base * factor, 4)  # Mínimo 4pt para legibilidad

def _render_section(pdf, section_id, venta, paciente_nombre, nombre_optica, 
                    ANCHO_MM, ANCHO_TEXTO, MARGEN_MM,
                    FONT_TITLE, FONT_SUBTITLE, FONT_NORMAL, FONT_NORMAL_SM, 
                    FONT_LABEL, FONT_TOTAL, FONT_SMALL, FONT_TINY, FONT_EXTRA_TINY, username):
    """Renderiza una sección específica de la boleta según su tipo."""
    pass  # Por ahora, usaremos el sistema clásico


def generar_boleta(venta, paciente_nombre, nombre_optica, username, receipt_width=None):
    """
    Genera una boleta profesional con medidas EXACTAS usando FPDF2.
    Diseño: Estilo empresa moderna similar a tiendas profesionales.
    
    Args:
        venta: Diccionario con datos de la venta
        paciente_nombre: Nombre del paciente
        nombre_optica: Nombre de la óptica
        username: Usuario que realiza la venta
        receipt_width: Ancho de la boleta en milímetros (default: carga desde configuración)
    """
    """
    Genera una boleta profesional con medidas EXACTAS usando FPDF2.
    Diseño: Estilo empresa moderna similar a tiendas profesionales.
    
    Args:
        venta: Diccionario con datos de la venta
        paciente_nombre: Nombre del paciente
        nombre_optica: Nombre de la óptica
        username: Usuario que realiza la venta
        receipt_width: Ancho de la boleta en milímetros (default: carga desde configuración)
    """
    try:
        # Cargar plantilla personalizada del usuario
        from utils.file_handler import cargar_plantilla_boleta
        plantilla = cargar_plantilla_boleta(username)
        
        # Si no se especifica receipt_width, usar el de la plantilla
        if receipt_width is None:
            receipt_width = plantilla.get('ancho_mm', 80)
        
        # Limpiar textos de entrada
        paciente_nombre = _limpiar_texto(paciente_nombre)
        nombre_optica = _limpiar_texto(nombre_optica)
        
        # Validar que username no sea None o string vacío
        if not username or username is None or username == '':
            print("[WARN] Username es None o vacío, usando 'default'")
            username = 'default'
        
        # Asegurar que username es string
        username = str(username).strip()
        
        # Sanitizar los items - asegurar que cantidad y subtotal sean válidos
        items_sanitizados = []
        items_raw = venta.get('items') or []
        if not isinstance(items_raw, (list, tuple)):
            items_raw = []

        for item in items_raw:
            if not isinstance(item, dict):
                continue
            cantidad = item.get('cantidad')
            if cantidad is None or cantidad == '' or cantidad == 0:
                cantidad = 1
            else:
                try:
                    cantidad = float(cantidad)
                    if cantidad == 0:
                        cantidad = 1
                except (ValueError, TypeError):
                    cantidad = 1
            
            subtotal = item.get('subtotal', 0)
            try:
                subtotal = float(subtotal)
            except (ValueError, TypeError):
                subtotal = 0
            
            precio = item.get('precio', 0)
            try:
                precio = float(precio)
            except (ValueError, TypeError):
                precio = 0
            
            items_sanitizados.append({
                'producto': _limpiar_texto(item.get('producto', 'Producto')),
                'descripcion': _limpiar_texto(item.get('descripcion', '')),
                'precio': precio,
                'cantidad': cantidad,
                'subtotal': subtotal
            })
        
        venta['items'] = items_sanitizados
        
        # Limpiar datos de venta
        venta['fecha'] = _limpiar_texto(venta.get('fecha', ''))
        venta['paciente_dni'] = _limpiar_texto(venta.get('paciente_dni', ''))
        venta['optometra'] = _limpiar_texto(venta.get('optometra', ''))
        
        # Convertir valores monetarios a float
        try:
            venta['monto_cobrado'] = float(venta.get('monto_cobrado', 0) or 0)
        except (ValueError, TypeError):
            venta['monto_cobrado'] = 0.0
        
        try:
            venta['subtotal'] = float(venta.get('subtotal', 0) or 0)
        except (ValueError, TypeError):
            venta['subtotal'] = 0.0
        
        try:
            venta['total'] = float(venta.get('total', 0) or 0)
        except (ValueError, TypeError):
            venta['total'] = 0.0
        
        metodo_pago = venta.get('metodo_pago', 'No especificado')
        doc_dir = VISO_DIR / username / "boletas"
        os.makedirs(doc_dir, exist_ok=True)
        
        # Usar un nombre de archivo más simple para evitar problemas con impresoras Bluetooth
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dni = venta.get('paciente_dni', 'cliente')
        # Limpiar el nombre para que sea compatible con todos los sistemas de archivos
        dni_limpio = ''.join(c for c in str(dni) if c.isalnum())
        doc_path = os.path.join(doc_dir, f"boleta_{dni_limpio}_{timestamp}.pdf")

        # Dimensiones profesionales
        ANCHO_MM = receipt_width  # Ancho configurable por el usuario (default: 80mm)
        MARGEN_MM = 2.5
        ANCHO_TEXTO = ANCHO_MM - (MARGEN_MM * 2)
        
        # Tamaños de fuente ajustados proporcionalmente al ancho
        # Los valores base están calibrados para 80mm
        factor_escala = ANCHO_MM / 80.0
        
        # Tamaños de fuente escalados
        FONT_TITLE = max(_calcular_tamaño_fuente(14, ANCHO_MM), 7)      # Título principal
        FONT_SUBTITLE = max(_calcular_tamaño_fuente(8, ANCHO_MM), 5)    # Subtítulos
        FONT_NORMAL = max(_calcular_tamaño_fuente(7, ANCHO_MM), 4.5)    # Texto normal
        FONT_NORMAL_SM = max(_calcular_tamaño_fuente(7.5, ANCHO_MM), 4.8) # Texto pequeño normal
        FONT_LABEL = max(_calcular_tamaño_fuente(8, ANCHO_MM), 5)       # Etiquetas
        FONT_TOTAL = max(_calcular_tamaño_fuente(9, ANCHO_MM), 6)       # Totales destacados
        FONT_SMALL = max(_calcular_tamaño_fuente(6.5, ANCHO_MM), 4.5)   # Texto pequeño
        FONT_TINY = max(_calcular_tamaño_fuente(6, ANCHO_MM), 4)        # Texto muy pequeño
        FONT_EXTRA_TINY = max(_calcular_tamaño_fuente(5.5, ANCHO_MM), 3.5) # Texto extra pequeño
        
        # ======================================================================
        # PASO 1: CALCULAR ALTURA EXACTA
        # ======================================================================
        print(f"\n{'='*70}")
        print(f"[BOLETA] GENERANDO BOLETA PROFESIONAL - FPDF2")
        print(f"[BOLETA] Plantilla personalizada: ancho={ANCHO_MM}mm")
        print(f"{'='*70}")
        
        # Crear PDF temporal para medir altura
        pdf_temp = BfoletaPDF(ANCHO_MM, 297)
        pdf_temp.add_page()
        pdf_temp.set_margins(MARGEN_MM, MARGEN_MM, MARGEN_MM)
        
        # ===== ENCABEZADO =====
        if plantilla.get('mostrar_optica', True):
            # Fondo del título
            pdf_temp.set_fill_color(0, 51, 102)  # Azul oscuro profesional
            pdf_temp.set_text_color(255, 255, 255)  # Texto blanco
            pdf_temp.set_font("Helvetica", "B", FONT_TITLE)
            pdf_temp.cell(0, 6, f"ÓPTICA {nombre_optica.upper()}", ln=True, align="C", fill=True)
            
            pdf_temp.set_fill_color(220, 230, 240)  # Azul claro de fondo
            pdf_temp.set_text_color(0, 51, 102)
            pdf_temp.set_font("Helvetica", "B", FONT_SUBTITLE)
            pdf_temp.cell(0, 4, "RECIBO DE COMPRA", ln=True, align="C", fill=True)
            
            pdf_temp.set_text_color(0, 0, 0)
            pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
            pdf_temp.cell(0, 2.5, "Boleta Electrónica", ln=True, align="C")
            
            _dibujar_separador(pdf_temp, MARGEN_MM, ANCHO_MM)
            pdf_temp.ln(1.5)
        
        # ===== INFORMACIÓN ADMINISTRATIVA =====
        pdf_temp.set_font("Helvetica", "B", FONT_LABEL)
        pdf_temp.set_text_color(0, 51, 102)
        pdf_temp.cell(ANCHO_TEXTO * 0.5, 2.5, "BOLETA #", border=0)
        pdf_temp.set_font("Helvetica", "", FONT_LABEL)
        pdf_temp.set_text_color(0, 0, 0)
        pdf_temp.cell(ANCHO_TEXTO * 0.5, 2.5, f"{venta['fecha'].replace('/', '')}-{venta['paciente_dni']}", ln=True, align="R")
        
        if plantilla.get('mostrar_fecha', True):
            pdf_temp.set_font("Helvetica", "B", FONT_LABEL)
            pdf_temp.set_text_color(0, 51, 102)
            pdf_temp.cell(ANCHO_TEXTO * 0.5, 2.5, "FECHA", border=0)
            pdf_temp.set_font("Helvetica", "", FONT_LABEL)
            pdf_temp.set_text_color(0, 0, 0)
            pdf_temp.cell(ANCHO_TEXTO * 0.5, 2.5, venta['fecha'], ln=True, align="R")
        
        pdf_temp.ln(0.5)
        
        # ===== DATOS DEL CLIENTE =====
        pdf_temp.set_font("Helvetica", "B", FONT_NORMAL_SM)
        pdf_temp.set_text_color(0, 51, 102)
        pdf_temp.cell(0, 2.3, "CLIENTE:", border=0)
        pdf_temp.ln()
        
        pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
        pdf_temp.set_text_color(0, 0, 0)
        pdf_temp.cell(ANCHO_TEXTO * 0.35, 2.2, "Nombre:")
        pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
        pdf_temp.cell(ANCHO_TEXTO * 0.65, 2.2, paciente_nombre, ln=True)
        
        if plantilla.get('mostrar_dni', True):
            pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
            pdf_temp.cell(ANCHO_TEXTO * 0.35, 2.2, "DNI:")
            pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
            pdf_temp.cell(ANCHO_TEXTO * 0.65, 2.2, venta['paciente_dni'], ln=True)
        pdf_temp.ln(0.5)
        
        # ===== TABLA DE PRODUCTOS =====
        _dibujar_separador(pdf_temp, MARGEN_MM, ANCHO_MM)
        pdf_temp.ln(1.0)
        
        # Headers con fondo
        pdf_temp.set_font("Helvetica", "B", FONT_NORMAL)
        pdf_temp.set_fill_color(220, 230, 240)  # Azul claro
        pdf_temp.set_text_color(0, 51, 102)
        col1 = ANCHO_TEXTO * 0.5
        col2 = ANCHO_TEXTO * 0.15
        col3 = ANCHO_TEXTO * 0.175
        col4 = ANCHO_TEXTO * 0.175
        
        pdf_temp.cell(col1, 3.5, "ARTICULO", border=0, fill=True)
        pdf_temp.cell(col2, 3.5, "CANT", border=0, align="C", fill=True)
        pdf_temp.cell(col3, 3.5, "UNITARIO", border=0, align="R", fill=True)
        pdf_temp.cell(col4, 3.5, "TOTAL", border=0, align="R", fill=True)
        pdf_temp.ln()
        
        # Productos
        pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
        pdf_temp.set_text_color(0, 0, 0)
        for item in venta['items']:
            precio_unit = item['subtotal'] / item['cantidad']
            
            pdf_temp.cell(col1, 3.5, item['producto'][:28], border=0)
            pdf_temp.cell(col2, 3.5, str(item['cantidad']), border=0, align="C")
            pdf_temp.cell(col3, 3.5, f"S/ {precio_unit:.2f}", border=0, align="R")
            pdf_temp.cell(col4, 3.5, f"S/ {item['subtotal']:.2f}", border=0, align="R")
            pdf_temp.ln()
            pdf_temp.ln()
        
        pdf_temp.ln(0.5)
        _dibujar_separador(pdf_temp, MARGEN_MM, ANCHO_MM)
        pdf_temp.ln(1.2)
        
        # ===== TOTALES MEJORADO =====
        # Subtotal
        pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
        pdf_temp.set_text_color(100, 100, 100)
        pdf_temp.cell(col1 + col2 + col3, 2.8, "Subtotal:")
        pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
        pdf_temp.set_text_color(0, 0, 0)
        pdf_temp.cell(col4, 2.8, f"S/ {venta['total']:.2f}", align="R")
        pdf_temp.ln()
        
        # IGV (si aplica)
        igv = venta['total'] * 0.18
        if igv > 0:
            pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
            pdf_temp.set_text_color(100, 100, 100)
            pdf_temp.cell(col1 + col2 + col3, 2.8, "IGV (18%):")
            pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
            pdf_temp.set_text_color(0, 0, 0)
            pdf_temp.cell(col4, 2.8, f"S/ {igv:.2f}", align="R")
            pdf_temp.ln()
        
        # Línea separadora antes del total
        pdf_temp.set_draw_color(0, 0, 0)
        pdf_temp.line(MARGEN_MM, pdf_temp.get_y() + 0.5, ANCHO_MM - MARGEN_MM, pdf_temp.get_y() + 0.5)
        pdf_temp.ln(0.8)
        
        # Total principal DESTACADO
        pdf_temp.set_font("Helvetica", "B", FONT_TOTAL + 2)
        pdf_temp.set_text_color(0, 51, 102)  # Azul oscuro profesional
        total_amount = venta['total'] * 1.18 if igv > 0 else venta['total']
        pdf_temp.cell(col1 + col2 + col3, 4, "TOTAL:")
        pdf_temp.cell(col4, 4, f"S/ {total_amount:.2f}", align="R")
        pdf_temp.ln()
        
        pdf_temp.set_text_color(0, 0, 0)
        pdf_temp.ln(0.8)
        
        # Información de pago
        pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
        pdf_temp.cell(ANCHO_TEXTO * 0.4, 2.3, "Forma de Pago:")
        pdf_temp.set_font("Helvetica", "B", FONT_NORMAL)
        pdf_temp.cell(ANCHO_TEXTO * 0.6, 2.3, metodo_pago, align="R")
        pdf_temp.ln()
        
        # Vuelto
        vuelto = venta.get('monto_contado', 0) - venta['total']
        if vuelto > 0:
            pdf_temp.set_font("Helvetica", "", FONT_NORMAL)
            pdf_temp.cell(ANCHO_TEXTO * 0.4, 2.3, "Vuelto:")
            pdf_temp.set_font("Helvetica", "B", FONT_NORMAL)
            pdf_temp.cell(ANCHO_TEXTO * 0.6, 2.3, f"S/ {vuelto:.2f}", align="R")
            pdf_temp.ln()
        
        pdf_temp.ln(0.8)
        
        # ===== MONTO EN LETRAS =====
        pdf_temp.set_font("Helvetica", "I", FONT_SMALL)
        monto_letras = number_to_words(venta['total'])
        pdf_temp.multi_cell(0, 2.2, f"Son: {monto_letras}")
        
        pdf_temp.ln(0.8)
        
        # ===== QR CODE =====
        qr_path = None
        if plantilla.get('mostrar_qr', True):
            _dibujar_separador(pdf_temp, MARGEN_MM, ANCHO_MM)
            pdf_temp.ln(1.2)
            
            qr_data_string = f"BOLETA:VENTA-{venta['fecha'].replace('/', '')}-{venta['paciente_dni']}|TOTAL:{venta['total']:.2f}|DNI:{venta['paciente_dni']}"
            qr_img = qrcode.make(qr_data_string)
            qr_path = os.path.join(doc_dir, "temp_qr.png")
            qr_img.save(qr_path)
            
            qr_size = 18  # mm
            x_qr = (ANCHO_MM - qr_size) / 2
            pdf_temp.image(qr_path, x=x_qr, y=pdf_temp.get_y(), w=qr_size)
            pdf_temp.ln(qr_size + 0.5)
            
            # ===== PIE DE PÁGINA =====
            pdf_temp.set_font("Helvetica", "B", FONT_LABEL)
            pdf_temp.cell(0, 2.5, "Escanea para verificar", ln=True, align="C")
        
        pdf_temp.ln(0.5)
        pie_text = plantilla.get('texto_pie_personalizado', 'Visite nuestro sitio web')
        if plantilla.get('mostrar_pie', True):
            pdf_temp.set_font("Helvetica", "I", FONT_TINY)
            pdf_temp.cell(0, 2, "Gracias por su compra", ln=True, align="C")
            if pie_text:
                pdf_temp.cell(0, 2, pie_text, ln=True, align="C")
            pdf_temp.cell(0, 2, f"Visite: {nombre_optica}", ln=True, align="C")
        
        pdf_temp.set_font("Helvetica", "", FONT_EXTRA_TINY)
        pdf_temp.cell(0, 1.8, "(Nota de venta sin validez legal)", ln=True, align="C")
        
        altura_usada = pdf_temp.get_y() + 1
        
        print(f"\n[BOLETA] MEDICIONES EXACTAS:")
        print(f"  - Ancho: {ANCHO_MM} mm")
        print(f"  - Altura calculada: {altura_usada:.2f} mm")
        print(f"  - Conversión: {altura_usada / 25.4:.3f}\" ({altura_usada / 25.4 * 2.54:.2f}cm)")
        
        if altura_usada > 279.4:
            print(f"  [ADVERTENCIA] Excede 1 página ({altura_usada:.2f}mm > 279.4mm)")
        else:
            print(f"  [OK] Cabe en 1 página")
        
        # ======================================================================
        # PASO 2: CREAR PDF FINAL CON MEDIDAS EXACTAS
        # ======================================================================
        print(f"\n[BOLETA] Creando PDF final...")
        
        # Crear PDF con altura ajustada con pequeño margen de seguridad
        altura_final = min(altura_usada + 2, 297)  # Máximo A4
        pdf = BfoletaPDF(ANCHO_MM, altura_final)
        pdf.add_page()
        pdf.set_margins(MARGEN_MM, MARGEN_MM, MARGEN_MM)
        
        # Repetir exactamente el mismo contenido
        if plantilla.get('mostrar_optica', True):
            pdf.set_font("Helvetica", "B", FONT_TITLE)
            pdf.cell(0, 5, f"ÓPTICA {nombre_optica.upper()}", ln=True, align="C")
            
            pdf.set_font("Helvetica", "I", FONT_SUBTITLE)
            pdf.cell(0, 3, "RECIBO DE COMPRA", ln=True, align="C")
            pdf.set_font("Helvetica", "", FONT_NORMAL)
            pdf.cell(0, 2.5, "Boleta Electrónica", ln=True, align="C")
            
            _dibujar_separador(pdf, MARGEN_MM, ANCHO_MM)
            pdf.ln(1.5)
        
        pdf.set_font("Helvetica", "B", FONT_LABEL)
        pdf.cell(ANCHO_TEXTO * 0.5, 2.5, "BOLETA #", border=0)
        pdf.set_font("Helvetica", "", FONT_LABEL)
        pdf.cell(ANCHO_TEXTO * 0.5, 2.5, f"{venta['fecha'].replace('/', '')}-{venta['paciente_dni']}", ln=True, align="R")
        
        if plantilla.get('mostrar_fecha', True):
            pdf.set_font("Helvetica", "B", FONT_LABEL)
            pdf.cell(ANCHO_TEXTO * 0.5, 2.5, "FECHA", border=0)
            pdf.set_font("Helvetica", "", FONT_LABEL)
            pdf.cell(ANCHO_TEXTO * 0.5, 2.5, venta['fecha'], ln=True, align="R")
        
        pdf.ln(0.5)
        
        pdf.set_font("Helvetica", "B", FONT_NORMAL_SM)
        pdf.cell(0, 2.3, "CLIENTE:", border=0)
        pdf.ln()
        
        pdf.set_font("Helvetica", "", FONT_NORMAL)
        pdf.cell(ANCHO_TEXTO * 0.35, 2.2, "Nombre:")
        pdf.set_font("Helvetica", "", FONT_NORMAL)
        pdf.cell(ANCHO_TEXTO * 0.65, 2.2, paciente_nombre, ln=True)
        
        if plantilla.get('mostrar_dni', True):
            pdf.set_font("Helvetica", "", FONT_NORMAL)
            pdf.cell(ANCHO_TEXTO * 0.35, 2.2, "DNI:")
            pdf.set_font("Helvetica", "", FONT_NORMAL)
            pdf.cell(ANCHO_TEXTO * 0.65, 2.2, venta['paciente_dni'], ln=True)
        
        pdf.ln(0.5)
        
        _dibujar_separador(pdf, MARGEN_MM, ANCHO_MM)
        pdf.ln(0.8)
        
        pdf.set_font("Helvetica", "B", FONT_NORMAL)
        pdf.set_text_color(0, 0, 0)
        
        pdf.cell(col1, 2.8, "ARTICULO", border=0)
        pdf.cell(col2, 2.8, "CANT", border=0, align="C")
        pdf.cell(col3, 2.8, "UNITARIO", border=0, align="R")
        pdf.cell(col4, 2.8, "TOTAL", border=0, align="R")
        pdf.ln()
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", FONT_NORMAL)
        for item in venta['items']:
            precio_unit = item['subtotal'] / item['cantidad']
            
            pdf.cell(col1, 3.2, item['producto'][:28], border=0)
            pdf.cell(col2, 3.2, str(item['cantidad']), border=0, align="C")
            pdf.cell(col3, 3.2, f"S/ {precio_unit:.2f}", border=0, align="R")
            pdf.cell(col4, 3.2, f"S/ {item['subtotal']:.2f}", border=0, align="R")
            pdf.ln()
        
        pdf.ln(0.5)
        _dibujar_separador(pdf, MARGEN_MM, ANCHO_MM)
        pdf.ln(0.8)
        
        pdf.set_font("Helvetica", "", FONT_NORMAL)
        pdf.cell(col1 + col2 + col3, 2.5, "SUBTOTAL:")
        pdf.set_font("Helvetica", "B", FONT_NORMAL)
        pdf.cell(col4, 2.5, f"S/ {venta['total']:.2f}", align="R")
        pdf.ln()
        
        pdf.set_font("Helvetica", "B", FONT_TOTAL)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(col1 + col2 + col3, 3.2, "TOTAL A PAGAR:")
        pdf.cell(col4, 3.2, f"S/ {venta['total']:.2f}", align="R")
        pdf.ln()
        
        pdf.set_text_color(0, 0, 0)
        pdf.ln(0.5)
        
        pdf.set_font("Helvetica", "", FONT_NORMAL)
        pdf.cell(ANCHO_TEXTO * 0.4, 2.3, "Forma de Pago:")
        pdf.set_font("Helvetica", "B", FONT_NORMAL)
        pdf.cell(ANCHO_TEXTO * 0.6, 2.3, metodo_pago, align="R")
        pdf.ln()
        
        if vuelto > 0:
            pdf.set_font("Helvetica", "", FONT_NORMAL)
            pdf.cell(ANCHO_TEXTO * 0.4, 2.3, "Vuelto:")
            pdf.set_font("Helvetica", "B", FONT_NORMAL)
            pdf.cell(ANCHO_TEXTO * 0.6, 2.3, f"S/ {vuelto:.2f}", align="R")
            pdf.ln()
        
        # ===== A CUENTA Y SALDO =====
        monto_cobrado = venta.get('monto_cobrado', 0) if venta.get('monto_cobrado', 0) else 0
        try:
            monto_cobrado = float(monto_cobrado)
        except (ValueError, TypeError):
            monto_cobrado = 0
        
        total_venta = venta['total']
        
        if monto_cobrado > 0 and monto_cobrado < total_venta:
            pdf.ln(0.3)
            # A CUENTA
            pdf.set_font("Helvetica", "", FONT_NORMAL)
            pdf.cell(ANCHO_TEXTO * 0.4, 2.3, "A CUENTA:")
            pdf.set_font("Helvetica", "B", FONT_NORMAL)
            pdf.set_text_color(0, 102, 51)  # Verde
            pdf.cell(ANCHO_TEXTO * 0.6, 2.3, f"S/ {monto_cobrado:.2f}", align="R")
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
            
            # SALDO
            saldo = total_venta - monto_cobrado
            pdf.set_font("Helvetica", "", FONT_NORMAL)
            pdf.cell(ANCHO_TEXTO * 0.4, 2.3, "SALDO:")
            pdf.set_font("Helvetica", "B", FONT_NORMAL)
            pdf.set_text_color(204, 0, 0)  # Rojo
            pdf.cell(ANCHO_TEXTO * 0.6, 2.3, f"S/ {saldo:.2f}", align="R")
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
        
        pdf.ln(0.8)
        
        if plantilla.get('mostrar_monto_letras', True):
            pdf.set_font("Helvetica", "I", FONT_SMALL)
            pdf.multi_cell(0, 2.2, f"Son: {monto_letras}")
        
        pdf.ln(0.8)
        
        if plantilla.get('mostrar_qr', True) and qr_path:
            _dibujar_separador(pdf, MARGEN_MM, ANCHO_MM)
            pdf.ln(1.2)
            
            pdf.image(qr_path, x=x_qr, y=pdf.get_y(), w=qr_size)
            pdf.ln(qr_size + 0.5)
            
            pdf.set_font("Helvetica", "B", FONT_LABEL)
            pdf.cell(0, 2.5, "Escanea para verificar", ln=True, align="C")
        
        pdf.ln(0.5)
        if plantilla.get('mostrar_pie', True):
            pdf.set_font("Helvetica", "I", FONT_TINY)
            pdf.cell(0, 2, "Gracias por su compra", ln=True, align="C")
            if pie_text:
                pdf.cell(0, 2, pie_text, ln=True, align="C")
            pdf.cell(0, 2, f"Visite: {nombre_optica}", ln=True, align="C")
        
        # ===== VENDEDOR =====
        if username and username != 'default':
            pdf.ln(0.5)
            _dibujar_separador(pdf, MARGEN_MM, ANCHO_MM)
            pdf.ln(0.5)
            pdf.set_font("Helvetica", "B", FONT_NORMAL_SM)
            pdf.cell(ANCHO_TEXTO * 0.35, 2.2, "Vendedor:")
            pdf.set_font("Helvetica", "", FONT_NORMAL)
            pdf.cell(ANCHO_TEXTO * 0.65, 2.2, username, ln=True)
        
        pdf.set_font("Helvetica", "", FONT_EXTRA_TINY)
        pdf.cell(0, 1.8, "(Nota de venta sin validez legal)", ln=True, align="C")
        
        pdf.output(doc_path)
        
        # Establecer tamaño de página exacto para impresión
        _set_pdf_page_size(doc_path, ANCHO_MM, altura_usada)
        
        try:
            os.remove(qr_path)
        except:
            pass
        
        print(f"[EXITO] Boleta generada: {os.path.basename(doc_path)}")
        print(f"[BOLETA] Tamaño: {ANCHO_MM}mm × {altura_usada:.2f}mm")
        print(f"{'='*70}\n")
        
        return doc_path
        
    except Exception as e:
        import traceback
        print(f"\n{'='*70}")
        print(f"[ERROR] Fallo al generar boleta:")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        print(f"\nTraceback completo:")
        traceback.print_exc()
        print(f"{'='*70}\n")
        raise
