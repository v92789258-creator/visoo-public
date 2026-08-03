"""
Clase base para todas las plantillas de boletas.
Define la interfaz común y funcionalidad compartida.
"""

import os
import json
from datetime import datetime
from fpdf import FPDF
import qrcode
from io import BytesIO
from abc import ABC, abstractmethod
from utils.file_handler import get_user_file_path, VISO_DIR


class PlantillaBase(ABC):
    """Clase abstracta base para generadores de plantillas de boletas."""

    _REEMPLAZOS_TEXTO = str.maketrans({
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2212": "-",   # minus sign
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2022": "*",
        "\u00a0": " ",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
    })
    
    # Configuración de la plantilla (debe ser sobrescrita por subclases)
    CONFIGURACION = {
        'ancho': 80,
        'alto': 150,
        'margen': 5,
        'font_titulo': 10,
        'font_normal': 8,
        'font_pequeño': 6,
        'lineas_por_producto': 2,
        'mostrar_detalles': False,
    }
    
    def __init__(self, usuario_id):
        """Inicializa la plantilla con el ID del usuario."""
        self.usuario_id = str(usuario_id)
        self.tamano_logo_px = None
    
    @abstractmethod
    def generar(self, datos_boleta, ruta_salida=None):
        """
        Genera la boleta en PDF según la plantilla.
        
        Args:
            datos_boleta (dict): Datos de la boleta
            ruta_salida (str): Ruta donde guardar el PDF (opcional)
        
        Returns:
            str: Ruta del PDF generado
        """
        pass
    
    # ===== MÉTODOS AUXILIARES COMUNES =====
    
    def _limpiar_texto(self, texto):
        """Limpia y normaliza texto para evitar errores de codificacion."""
        if texto is None:
            return ''

        limpio = str(texto).replace('\x00', '').strip()
        limpio = limpio.translate(self._REEMPLAZOS_TEXTO)

        # Evita fallos de FPDF con fuentes core (helvetica, courier, etc.)
        salida = []
        for char in limpio:
            try:
                char.encode('cp1252')
                salida.append(char)
            except UnicodeEncodeError:
                salida.append('?')
        return ''.join(salida)

    def _crear_pdf(self, orientacion='P', unidad='mm', formato='A4'):
        """Crea un FPDF con encoding compatible para fuentes core."""
        pdf = FPDF(orientacion, unidad, formato)
        if hasattr(pdf, 'core_fonts_encoding'):
            pdf.core_fonts_encoding = 'cp1252'
        return pdf
    
    def _guardar_pdf(self, pdf, ruta_salida):
        """Guarda el PDF generado en la ruta especificada."""
        if ruta_salida is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_salida = get_user_file_path(
                self.usuario_id, 
                f"boleta_{timestamp}.pdf"
            )
        
        dirname = os.path.dirname(ruta_salida)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        pdf.output(ruta_salida)
        
        print(f"[OK] Boleta generada: {ruta_salida}")
        return ruta_salida
    
    def _insertar_logo_en_pdf(self, pdf, config, ancho_util, y_actual, tamano_logo_px=None):
        """
        Inserta el logo de la empresa en el PDF.
        
        Args:
            pdf: Objeto FPDF
            config: Configuración de la plantilla
            ancho_util: Ancho disponible
            y_actual: Posición Y actual
            tamano_logo_px: Tamaño del logo en píxeles (opcional)
        
        Returns:
            float: Altura ocupada por el logo
        """
        ruta_logo = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'logos', 'logo_empresa.png')
        
        if not os.path.exists(ruta_logo):
            print(f"[WARN] Logo no encontrado: {ruta_logo}")
            return 0
        
        try:
            # Dimensiones del logo
            if tamano_logo_px:
                tamano_logo = min(50, max(20, tamano_logo_px / 10))
            else:
                tamano_logo = 30  # Default
            
            # Centrar logo
            x_logo = config['margen'] + (ancho_util - tamano_logo) / 2
            
            pdf.image(ruta_logo, x=x_logo, y=y_actual, w=tamano_logo)
            
            print(f"[OK] Logo insertado - Tamaño: {tamano_logo}mm")
            return tamano_logo + 5  # Logo + espaciado
        except Exception as e:
            print(f"[ERROR] No se pudo insertar logo: {e}")
            return 0
    
    def _calcular_altura_logo_dinamica(self, tiene_logo):
        """Calcula la altura aproximada del logo en milímetros."""
        if not tiene_logo:
            return 0
        
        altura_base = 30  # Logo
        espaciado = 5     # Espaciado
        
        if self.tamano_logo_px:
            altura_base = min(50, max(20, self.tamano_logo_px / 10))
        
        return altura_base + espaciado
    
    def _generar_qr(self, datos_qr_str, tamaño_mm=30):
        """
        Genera un código QR y lo convierte a imagen.
        
        Args:
            datos_qr_str (str): Datos para el QR
            tamaño_mm (int): Tamaño en milímetros
        
        Returns:
            BytesIO: Imagen del QR
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(datos_qr_str)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
        except Exception as e:
            print(f"[ERROR] No se pudo generar QR: {e}")
            return None
    
    def _format_moneda(self, valor):
        """Formatea un valor monetario."""
        return f"S/{float(valor):.2f}"
    
    def _obtener_timestamp_actual(self):
        """Obtiene el timestamp actual formateado."""
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    def _obtener_hora_actual(self):
        """Obtiene la hora actual formateada."""
        return datetime.now().strftime("%H:%M:%S")

    def _normalizar_productos(self, productos):
        """
        Normaliza la lista de productos para evitar errores al acceder .get().

        En algunos flujos pueden llegar valores `None` o elementos no-dict dentro
        de `productos`. Esta función filtra y devuelve solo diccionarios.
        """
        if not productos:
            return []
        if not isinstance(productos, (list, tuple)):
            return []

        normalizados = []
        for item in productos:
            if isinstance(item, dict):
                normalizados.append(item)
        return normalizados

