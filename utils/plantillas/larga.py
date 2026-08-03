"""
Plantilla de boleta larga para impresoras térmicas.
Formato de 80mm x 250mm con detalles completos.
"""

from fpdf import FPDF
from .pequena import PlantillaPequena


class PlantillaLarga(PlantillaPequena):
    """Genera boletas largas con detalles completos."""
    
    CONFIGURACION = {
        'ancho': 80,
        'alto': 250,
        'margen': 5,
        'font_titulo': 10,
        'font_normal': 8,
        'font_pequeño': 7,
        'lineas_por_producto': 2,
        'mostrar_detalles': True,
    }
    
    def _calcular_altura_exacta(self, datos_boleta, config, tiene_logo):
        """Calcula altura con espacio adicional para detalles."""
        altura = super()._calcular_altura_exacta(datos_boleta, config, tiene_logo)
        altura += 20  # Espacio adicional para detalles
        return altura
