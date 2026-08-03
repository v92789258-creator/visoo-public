"""
Utilidades para redistribuir automáticamente elementos de UI según el tamaño de pantalla.
Ayuda a que la interfaz se adapte correctamente en pantallas pequeñas.
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt
from utils.screen_scaling import get_screen_scaling


def apply_adaptive_layout(widget, default_orientation=Qt.Horizontal):
    """
    Convierte un layout de un widget a vertical u horizontal según el tamaño de pantalla.
    
    Args:
        widget: Widget con un layout
        default_orientation: Orientación por defecto (Qt.Horizontal o Qt.Vertical)
    """
    scaling = get_screen_scaling()
    
    # Determinar orientación según pantalla
    if scaling.should_use_vertical_layout():
        target_orientation = Qt.Vertical
    else:
        target_orientation = default_orientation
    
    # Obtener layout actual
    old_layout = widget.layout()
    if not old_layout:
        return
    
    # Crear nuevo layout si es necesario
    if target_orientation == Qt.Vertical:
        if not isinstance(old_layout, QVBoxLayout):
            convert_layout_to_vertical(widget)
    else:
        if not isinstance(old_layout, QHBoxLayout):
            convert_layout_to_horizontal(widget)


def convert_layout_to_vertical(widget):
    """Convierte el layout de un widget a vertical."""
    old_layout = widget.layout()
    if not old_layout:
        return
    
    # Guardar todos los items
    items = []
    while old_layout.count() > 0:
        item = old_layout.takeAt(0)
        if item.widget():
            items.append(item.widget())
        elif item.layout():
            items.append(item.layout())
    
    # Eliminar layout viejo
    old_layout.deleteLater()
    
    # Crear layout vertical
    new_layout = QVBoxLayout(widget)
    new_layout.setContentsMargins(0, 0, 0, 0)
    
    # Agregar items
    for item in items:
        if isinstance(item, QWidget):
            new_layout.addWidget(item)
        else:
            new_layout.addLayout(item)
    
    new_layout.addStretch()


def convert_layout_to_horizontal(widget):
    """Convierte el layout de un widget a horizontal."""
    old_layout = widget.layout()
    if not old_layout:
        return
    
    # Guardar todos los items
    items = []
    while old_layout.count() > 0:
        item = old_layout.takeAt(0)
        if item.widget():
            items.append(item.widget())
        elif item.layout():
            items.append(item.layout())
    
    # Eliminar layout viejo
    old_layout.deleteLater()
    
    # Crear layout horizontal
    new_layout = QHBoxLayout(widget)
    new_layout.setContentsMargins(0, 0, 0, 0)
    
    # Agregar items
    for item in items:
        if isinstance(item, QWidget):
            new_layout.addWidget(item)
        else:
            new_layout.addLayout(item)
    
    new_layout.addStretch()


def set_responsive_margins(widget, base_margin=24):
    """Establece márgenes responsivos para un widget."""
    scaling = get_screen_scaling()
    margin = scaling.get_margin(base_margin)
    
    layout = widget.layout()
    if layout:
        layout.setContentsMargins(margin, margin, margin, margin)


def set_responsive_spacing(widget, base_spacing=12):
    """Establece espaciado responsivo para un widget."""
    scaling = get_screen_scaling()
    spacing = scaling.get_spacing(base_spacing)
    
    layout = widget.layout()
    if layout:
        layout.setSpacing(spacing)


def get_grid_columns():
    """Retorna el número de columnas recomendadas para grillas."""
    scaling = get_screen_scaling()
    
    if scaling.is_mobile_mode:
        return 1
    elif scaling.is_compact_mode:
        return 2
    elif scaling.is_wide_screen():
        return 4
    else:
        return 3


def should_collapse_sidebar():
    """Retorna True si el sidebar debe colapsar."""
    scaling = get_screen_scaling()
    return scaling.screen_width < 1024


def should_hide_footer():
    """Retorna True si el footer debe ocultarse."""
    scaling = get_screen_scaling()
    return scaling.screen_height < 600


def get_optimal_dialog_size():
    """Retorna tamaño óptimo para diálogos."""
    scaling = get_screen_scaling()
    max_width = scaling.get_max_window_width()
    max_height = scaling.get_max_window_height()
    
    # Usar 80% del máximo para dar margen
    width = int(max_width * 0.8)
    height = int(max_height * 0.8)
    
    # Mínimos
    width = max(300, width)
    height = max(200, height)
    
    return width, height


def get_optimal_main_window_size():
    """Retorna tamaño óptimo para ventana principal."""
    scaling = get_screen_scaling()
    return scaling.get_max_window_width(), scaling.get_max_window_height()
