"""Excepciones personalizadas de VISO"""

class VISOException(Exception):
    """Excepción base de VISO"""
    pass

class ConfigurationError(VISOException):
    """Error de configuración"""
    pass

class DependencyError(VISOException):
    """Error de dependencias"""
    pass

class SingleInstanceError(VISOException):
    """Error de instancia única"""
    pass
