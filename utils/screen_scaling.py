"""
Sistema de escalado automático de la interfaz según la resolución de pantalla.
Ajusta tamaños de fuente, iconos, márgenes y otros elementos UI.
"""

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QScreen
import sys


class ScreenScaling:
    """Calcula factores de escalado basados en la resolución de pantalla."""
    
    # Resolución de referencia (1920x1080 a 96 DPI)
    REFERENCE_WIDTH = 1920
    REFERENCE_HEIGHT = 1080
    REFERENCE_DPI = 96
    
    # Tamaños base en la resolución de referencia
    BASE_FONT_SIZE = 11
    BASE_ICON_SIZE = 24
    BASE_BUTTON_HEIGHT = 36
    BASE_PADDING = 16
    BASE_MARGIN = 24
    BASE_SPACING = 12
    
    # Breakpoints para modo compacto
    BREAKPOINT_TABLET = 1024  # Tabletas y pantallas pequeñas
    BREAKPOINT_PHONE = 768    # Teléfonos
    
    def __init__(self):
        """Inicializa el sistema de escalado."""
        self.app = QtWidgets.QApplication.instance()
        if not self.app:
            self.app = QtWidgets.QApplication(sys.argv)
        
        self.screen = self.app.primaryScreen()
        self.update_scaling_factors()
    
    def update_scaling_factors(self):
        """Calcula los factores de escalado actuales."""
        # Obtener dimensiones de pantalla
        screen_geometry = self.screen.geometry()
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()
        
        # Obtener DPI
        try:
            self.dpi = self.screen.logicalDotsPerInch()
        except:
            self.dpi = self.REFERENCE_DPI
        
        # Calcular factores de escalado
        self.scale_factor_width = self.screen_width / self.REFERENCE_WIDTH
        self.scale_factor_height = self.screen_height / self.REFERENCE_HEIGHT
        
        # Usar el factor más pequeño para mantener la proporción
        self.scale_factor = min(self.scale_factor_width, self.scale_factor_height)
        
        # Factor DPI
        self.dpi_scale = self.dpi / self.REFERENCE_DPI
        
        # Combinar factores
        self.combined_scale = self.scale_factor * self.dpi_scale
        
        # Limitar escalado para evitar extremos
        self.combined_scale = max(0.8, min(self.combined_scale, 2.0))
        
        # Determinar modo compacto
        self.is_compact_mode = self.screen_width < self.BREAKPOINT_TABLET
        self.is_mobile_mode = self.screen_width < self.BREAKPOINT_PHONE
    
    def get_font_size(self, base_size=None):
        """Obtiene tamaño de fuente escalado."""
        if base_size is None:
            base_size = self.BASE_FONT_SIZE
        
        # Reducir más en modo compacto
        scale = self.combined_scale
        if self.is_compact_mode:
            scale *= 0.9
        if self.is_mobile_mode:
            scale *= 0.8
        
        return max(8, int(base_size * scale))
    
    def get_icon_size(self, base_size=None):
        """Obtiene tamaño de icono escalado."""
        if base_size is None:
            base_size = self.BASE_ICON_SIZE
        
        scale = self.combined_scale
        if self.is_compact_mode:
            scale *= 0.85
        if self.is_mobile_mode:
            scale *= 0.7
        
        return max(16, int(base_size * scale))
    
    def get_button_height(self, base_height=None):
        """Obtiene altura de botón escalada."""
        if base_height is None:
            base_height = self.BASE_BUTTON_HEIGHT
        
        scale = self.combined_scale
        if self.is_compact_mode:
            scale *= 0.9
        if self.is_mobile_mode:
            scale *= 0.8
        
        return max(24, int(base_height * scale))
    
    def get_padding(self, base_padding=None):
        """Obtiene padding escalado."""
        if base_padding is None:
            base_padding = self.BASE_PADDING
        
        scale = self.combined_scale
        if self.is_compact_mode:
            scale *= 0.7
        if self.is_mobile_mode:
            scale *= 0.5
        
        return max(4, int(base_padding * scale))
    
    def get_margin(self, base_margin=None):
        """Obtiene margen escalado."""
        if base_margin is None:
            base_margin = self.BASE_MARGIN
        
        scale = self.combined_scale
        if self.is_compact_mode:
            scale *= 0.7
        if self.is_mobile_mode:
            scale *= 0.5
        
        return max(8, int(base_margin * scale))
    
    def get_spacing(self, base_spacing=None):
        """Obtiene espaciado escalado."""
        if base_spacing is None:
            base_spacing = self.BASE_SPACING
        
        scale = self.combined_scale
        if self.is_compact_mode:
            scale *= 0.8
        if self.is_mobile_mode:
            scale *= 0.6
        
        return max(4, int(base_spacing * scale))
    
    def get_scalable_stylesheet(self, base_stylesheet):
        """Adapta un stylesheet con variables de escalado."""
        font_size = self.get_font_size()
        padding = self.get_padding()
        margin = self.get_margin()
        
        # Reemplazar variables comunes
        stylesheet = base_stylesheet.replace("${FONT_SIZE}", f"{font_size}px")
        stylesheet = stylesheet.replace("${PADDING}", f"{padding}px")
        stylesheet = stylesheet.replace("${MARGIN}", f"{margin}px")
        
        return stylesheet
    
    def is_wide_screen(self):
        """Retorna True si la pantalla es lo suficientemente ancha para diseño de dos columnas."""
        return self.screen_width >= 1400
    
    def is_large_screen(self):
        """Retorna True si la pantalla es grande."""
        return self.screen_width >= self.REFERENCE_WIDTH
    
    def is_small_screen(self):
        """Retorna True si la pantalla es pequeña."""
        return self.is_compact_mode
    
    def should_use_vertical_layout(self):
        """Retorna True si se debe usar layout vertical en lugar de horizontal."""
        return self.screen_width < 1200
    
    def should_hide_secondary_elements(self):
        """Retorna True si se deben ocultar elementos secundarios."""
        return self.is_compact_mode
    
    def get_max_window_width(self):
        """Obtiene el ancho máximo recomendado para ventanas."""
        return int(self.screen_width * 0.9)
    
    def get_max_window_height(self):
        """Obtiene el alto máximo recomendado para ventanas."""
        return int(self.screen_height * 0.85)
    
    def print_scaling_info(self):
        """Imprime información de escalado (para debugging)."""
        print(f"\n[SCREEN SCALING INFO]")
        print(f"  Resolución: {self.screen_width}x{self.screen_height}")
        print(f"  DPI: {self.dpi}")
        print(f"  Factor escala (resolución): {self.scale_factor:.2f}")
        print(f"  Factor escala (DPI): {self.dpi_scale:.2f}")
        print(f"  Factor combinado: {self.combined_scale:.2f}")
        print(f"  Modo compacto: {'SÍ' if self.is_compact_mode else 'NO'}")
        print(f"  Modo móvil: {'SÍ' if self.is_mobile_mode else 'NO'}")
        print(f"  Pantalla ancha: {'SÍ' if self.is_wide_screen() else 'NO'}")
        print(f"  Usar layout vertical: {'SÍ' if self.should_use_vertical_layout() else 'NO'}")
        print(f"  Tamaño fuente: {self.get_font_size()}px")
        print(f"  Tamaño icono: {self.get_icon_size()}px")
        print(f"  Altura botón: {self.get_button_height()}px")
        print(f"  Padding: {self.get_padding()}px")
        print(f"  Margen: {self.get_margin()}px")
        print(f"  Espaciado: {self.get_spacing()}px\n")


# Instancia global
_screen_scaling = None


def get_screen_scaling():
    """Obtiene la instancia global de ScreenScaling."""
    global _screen_scaling
    if _screen_scaling is None:
        _screen_scaling = ScreenScaling()
    return _screen_scaling


def apply_scaling_to_widget(widget):
    """Aplica escalado a un widget y todos sus hijos."""
    scaling = get_screen_scaling()
    
    # Escalar fuente
    font = widget.font()
    font.setPointSize(scaling.get_font_size())
    widget.setFont(font)
    
    # Aplicar recursivamente a hijos
    for child in widget.findChildren(QtWidgets.QWidget):
        if child != widget:
            try:
                font = child.font()
                font.setPointSize(scaling.get_font_size())
                child.setFont(font)
            except:
                pass


def scale_size(base_size):
    """Escala un tamaño base."""
    scaling = get_screen_scaling()
    return int(base_size * scaling.combined_scale)


def scale_icon_size(base_size=24):
    """Escala tamaño de icono."""
    return scale_size(base_size)


def scale_font_size(base_size=11):
    """Escala tamaño de fuente."""
    return scale_size(base_size)


def scale_dimensions(width, height):
    """Escala dimensiones (ancho y alto)."""
    scaling = get_screen_scaling()
    return int(width * scaling.scale_factor_width), int(height * scaling.scale_factor_height)


# Inicializar al importar
try:
    get_screen_scaling()
except:
    pass
