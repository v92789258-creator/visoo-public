"""
Módulo de estilos para la interfaz de VISO.
"""

from .button_styles import (
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    DELETE_BUTTON,
    ACTION_BUTTON,
    ICON_BUTTON,
    SIDEBAR_BUTTON
)

# Intentar exponer QSS_STYLE definido en el módulo de estilos principal `gui/styles.py`.
# Algunas partes del proyecto importan `gui.styles` (paquete) esperando encontrar QSS_STYLE;
# cargamos el archivo `gui/styles.py` desde la ruta superior si está disponible.
try:
    import os
    from importlib.util import spec_from_file_location, module_from_spec
    parent_styles_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'styles.py'))
    if os.path.exists(parent_styles_path):
        spec = spec_from_file_location('gui._styles_file', parent_styles_path)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        QSS_STYLE = getattr(mod, 'QSS_STYLE', '')
    else:
        QSS_STYLE = ''
except Exception:
    QSS_STYLE = ''