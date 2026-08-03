"""
Estilos globales con escalado automático para toda la aplicación VISO.
Aplicar al inicio de la aplicación para garantizar consistencia en todas las pantallas.
"""

from utils.screen_scaling import get_screen_scaling


def get_global_stylesheet():
    """Obtiene un stylesheet global con escalado automático."""
    scaling = get_screen_scaling()
    
    font_size = scaling.get_font_size(11)
    small_font = scaling.get_font_size(9)
    large_font = scaling.get_font_size(14)
    title_font = scaling.get_font_size(18)
    
    padding = scaling.get_padding(12)
    margin = scaling.get_margin(16)
    spacing = scaling.get_spacing(8)
    
    button_height = scaling.get_button_height(36)
    icon_size = scaling.get_icon_size(24)
    
    # En pantallas pequeñas, hacer scroll bars más gruesos para facilitar uso
    scrollbar_width = max(12, scaling.get_icon_size(20))
    
    stylesheet = f"""
    /* ===== APLICACIÓN GLOBAL ===== */
    QWidget {{
        font-size: {font_size}px;
        font-family: "Segoe UI", "Helvetica", sans-serif;
    }}
    
    /* ===== BOTONES ===== */
    QPushButton {{
        min-height: {button_height}px;
        padding: {padding // 3}px {padding}px;
        border: none;
        border-radius: 4px;
        font-weight: 500;
    }}
    
    QPushButton:hover {{
        opacity: 0.9;
    }}
    
    QPushButton:pressed {{
        opacity: 0.8;
    }}
    
    QPushButton#primaryButton {{
        background-color: #0d6efd;
        color: white;
    }}
    
    QPushButton#dangerButton {{
        background-color: #dc3545;
        color: white;
    }}
    
    QPushButton#successButton {{
        background-color: #198754;
        color: white;
    }}
    
    /* ===== ETIQUETAS ===== */
    QLabel {{
        color: #333333;
    }}
    
    QLabel[type="title"] {{
        font-size: {title_font}px;
        font-weight: bold;
        color: #2c3e50;
    }}
    
    QLabel[type="subtitle"] {{
        font-size: {large_font}px;
        color: #666666;
    }}
    
    QLabel[type="small"] {{
        font-size: {small_font}px;
        color: #999999;
    }}
    
    /* ===== INPUTS ===== */
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        min-height: {button_height}px;
        padding: {padding // 3}px {padding}px;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        background-color: white;
        selection-background-color: #0d6efd;
    }}
    
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 2px solid #0d6efd;
    }}
    
    /* ===== TABLAS ===== */
    QTableWidget {{
        gridline-color: #e0e0e0;
        background-color: white;
    }}
    
    QTableWidget::item {{
        padding: {spacing}px;
    }}
    
    QTableWidget::item:selected {{
        background-color: #e7f1ff;
    }}
    
    QHeaderView::section {{
        background-color: #f5f5f5;
        padding: {padding // 2}px;
        border: none;
        border-bottom: 2px solid #ddd;
        font-weight: bold;
        color: #333;
    }}
    
    /* ===== CAJAS DE GRUPO ===== */
    QGroupBox {{
        border: 1px solid #ddd;
        border-radius: 4px;
        margin-top: {margin // 2}px;
        padding-top: {padding}px;
        font-weight: 600;
        color: #333;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {padding}px;
        padding: 0 {padding // 2}px;
    }}
    
    /* ===== SCROLL AREA ===== */
    QScrollBar:vertical {{
        width: {scrollbar_width}px;
        background-color: #f5f5f5;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: #ccc;
        border-radius: 4px;
        min-height: {button_height}px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: #999;
    }}
    
    QScrollBar:horizontal {{
        height: {scrollbar_width}px;
        background-color: #f5f5f5;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: #ccc;
        border-radius: 4px;
        min-width: {button_height}px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: #999;
    }}
    
    /* ===== DIÁLOGOS ===== */
    QDialog {{
        background-color: white;
    }}
    
    QMessageBox {{
        background-color: white;
    }}
    
    /* ===== TABS ===== */
    QTabWidget::pane {{
        border: 1px solid #ddd;
    }}
    
    QTabBar::tab {{
        background-color: #f5f5f5;
        padding: {padding}px {margin}px;
        margin-right: {spacing}px;
        border: 1px solid #ddd;
    }}
    
    QTabBar::tab:selected {{
        background-color: white;
        border-bottom: 2px solid #0d6efd;
    }}
    
    /* ===== ADAPTACIONES PARA PANTALLAS PEQUEÑAS ===== """
    
    # Agregar estilos adicionales si es modo compacto
    if scaling.is_compact_mode:
        stylesheet += f"""
    /* Modo compacto: reducir márgenes internos */
    QWidget {{
        margin: 0px;
    }}
    
    /* Ocultar elementos secundarios */
    QToolBar {{
        margin: 0px;
        padding: 0px;
    }}
    
    /* Tabs más compactos en móvil */
    QTabBar::tab {{
        padding: {padding // 2}px {padding}px;
        font-size: {small_font}px;
    }}
    
    /* Hacer inputs más grandes para touch */
    QLineEdit, QComboBox, QPushButton {{
        min-height: {max(44, button_height)}px;
    }}
        """
    
    stylesheet += "\n    \"\"\""
    
    return stylesheet


def apply_scaling_stylesheet(application):
    """Aplica los estilos globales escalados a la aplicación."""
    try:
        stylesheet = get_global_stylesheet()
        application.setStyleSheet(stylesheet)
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo aplicar stylesheet global: {e}")
        return False
