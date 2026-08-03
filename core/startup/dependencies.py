"""Verificacion de dependencias"""
import logging
import importlib.util

logger = logging.getLogger(__name__)

CRITICAL_MODULES = ["PyQt5"]
OPTIONAL_MODULES = ["requests", "flask", "google-generativeai"]


def _module_exists(module_import_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_import_name) is not None
    except Exception:
        return False


def check_dependencies():
    """Verifica que esten instaladas las dependencias criticas."""
    missing = []

    for module_name in CRITICAL_MODULES:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)
            logger.warning(f"Modulo no encontrado: {module_name}")

    if missing:
        error_msg = f"Faltan dependencias criticas: {', '.join(missing)}\n"
        error_msg += "Por favor ejecute: pip install -r requirements.txt"
        logger.error(error_msg)
        return False

    # Verificar modulos opcionales sin importarlos para evitar bloqueos en startup.
    optional_import_names = {
        "requests": "requests",
        "flask": "flask",
        "google-generativeai": "google.generativeai",
    }
    for module_name in OPTIONAL_MODULES:
        import_name = optional_import_names.get(module_name, module_name)
        if not _module_exists(import_name):
            logger.debug(f"Modulo opcional no encontrado: {module_name}")

    logger.info("Todas las dependencias criticas estan instaladas")
    return True
