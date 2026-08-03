"""Configuración centralizada - Rutas, constantes y variables globales"""
import os
import sys

# ============================================================================
# DIRECTORIOS Y RUTAS
# ============================================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ICON_PATH = os.path.join(BASE_DIR, "icon.ico")

# Directorios VISO
VISO_DIR = os.path.join(BASE_DIR, 'VISO')
TEMP_DIR = os.path.join(VISO_DIR, 'temp')
LOG_DIR = TEMP_DIR

FATAL_LOG_FILE = os.path.join(TEMP_DIR, 'fatal.log')

# Crear directorios si no existen
for directory in [VISO_DIR, TEMP_DIR]:
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception:
        pass

# ============================================================================
# CONSTANTES
# ============================================================================
NOTIFICATION_SERVICE_PORT = 55124
SINGLE_INSTANCE_PORT = 55123
APP_NAME = "VISO"

def _load_app_version(default: str = "4.2.4") -> str:
    """
    Carga la version desde VERSION/.version en la raiz del proyecto/ejecutable.
    Si falla, usa el valor por defecto.
    """
    candidates = [
        os.path.join(BASE_DIR, "VERSION"),
        os.path.join(BASE_DIR, ".version"),
        os.path.join(os.path.dirname(BASE_DIR), "VERSION"),
        os.path.join(os.path.dirname(BASE_DIR), ".version"),
    ]

    for path in candidates:
        try:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                value = str(f.read() or "").strip()
            if value:
                return value
        except Exception:
            continue
    return default


APP_VERSION = _load_app_version()

# Timeout para verificación de licencia
LICENSE_VERIFICATION_TIMEOUT = 10
LICENSE_VERIFICATION_LOGIN_TIMEOUT = 5

# ============================================================================
# FLAGS Y OPCIONES
# ============================================================================
IS_FROZEN = getattr(sys, 'frozen', False)
IS_DEVELOPMENT = not IS_FROZEN
ENABLE_STARTUP_TRACE = os.environ.get('STARTUP_TRACE') == '1'
