"""
Manejador de seguridad centralizado para VISO.
Proporciona validación de permisos, encriptación y control de acceso.
"""

import os
import hashlib
import hmac
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from utils.error_logger import get_logger

logger = get_logger('SECURITY')

# Directorio de configuración segura
SECURITY_DIR = Path(os.path.expanduser("~")) / ".viso" / "security"
SECURITY_DIR.mkdir(parents=True, exist_ok=True)

# Permisos de usuario
ROLE_ADMIN = 'admin'
ROLE_OPTOMETRIST = 'optometrist'
ROLE_RECEPTIONIST = 'receptionist'
ROLE_VIEWER = 'viewer'

VALID_ROLES = {ROLE_ADMIN, ROLE_OPTOMETRIST, ROLE_RECEPTIONIST, ROLE_VIEWER}

# Permisos por rol
ROLE_PERMISSIONS = {
    ROLE_ADMIN: {
        'users_manage', 'users_view', 'patients_create', 'patients_edit',
        'patients_delete', 'patients_view', 'sales_create', 'sales_edit',
        'sales_delete', 'sales_view', 'reports_view', 'settings_manage'
    },
    ROLE_OPTOMETRIST: {
        'patients_create', 'patients_edit', 'patients_view', 'sales_create',
        'sales_edit', 'sales_view', 'reports_view'
    },
    ROLE_RECEPTIONIST: {
        'patients_create', 'patients_view', 'sales_create', 'sales_view'
    },
    ROLE_VIEWER: {
        'patients_view', 'sales_view'
    }
}


class SecurityManager:
    """Gestor centralizado de seguridad para VISO."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.current_user = None
        self.current_role = None
        self.permissions = set()
    
    def set_user_context(self, user_id: str, user_role: str) -> bool:
        """
        Establece el contexto de usuario actual.
        
        Args:
            user_id: ID del usuario
            user_role: Rol del usuario
        
        Returns:
            True si es válido
        """
        if not self._validate_role(user_role):
            logger.error(f"Rol inválido: {user_role}")
            return False
        
        self.current_user = user_id
        self.current_role = user_role
        self.permissions = ROLE_PERMISSIONS.get(user_role, set()).copy()
        
        logger.info(f"Contexto de usuario establecido: {user_id} ({user_role})")
        return True
    
    def check_permission(self, permission: str) -> bool:
        """
        Verifica si el usuario actual tiene permiso.
        
        Args:
            permission: Nombre del permiso a verificar
        
        Returns:
            True si tiene permiso
        """
        if not self.current_user:
            logger.warning("Sin contexto de usuario")
            return False
        
        has_permission = permission in self.permissions
        
        if not has_permission:
            logger.warning(f"Permiso denegado: {self.current_user} -> {permission}")
        
        return has_permission
    
    def require_permission(self, permission: str) -> bool:
        """
        Requiere un permiso o lanza excepción.
        
        Args:
            permission: Nombre del permiso requerido
        
        Raises:
            PermissionError si no tiene permiso
        """
        if not self.check_permission(permission):
            raise PermissionError(f"Permiso requerido: {permission}")
        return True
    
    def get_user_role(self) -> Optional[str]:
        """Obtiene el rol del usuario actual."""
        return self.current_role
    
    def get_user_id(self) -> Optional[str]:
        """Obtiene el ID del usuario actual."""
        return self.current_user
    
    def get_user_permissions(self) -> set:
        """Obtiene los permisos del usuario actual."""
        return self.permissions.copy()
    
    def _validate_role(self, role: str) -> bool:
        """Valida que el rol sea válido."""
        if role not in VALID_ROLES:
            logger.warning(f"Rol no válido: {role}")
            return False
        return True
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Genera hash seguro de contraseña con salt.
        
        Args:
            password: Contraseña a hashear
            salt: Salt opcional (se genera si no se proporciona)
        
        Returns:
            (hash, salt)
        """
        if not password:
            logger.warning("Contraseña vacía")
            return "", ""
        
        if salt is None:
            salt = os.urandom(32).hex()
        
        # Usar PBKDF2 con SHA-256
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8') if isinstance(salt, str) else salt,
            100000  # Iteraciones
        )
        
        return hash_obj.hex(), salt
    
    @staticmethod
    def verify_password(password: str, stored_hash: str, salt: str) -> bool:
        """
        Verifica que una contraseña coincida con su hash.
        
        Args:
            password: Contraseña a verificar
            stored_hash: Hash almacenado
            salt: Salt usado para hashear
        
        Returns:
            True si coincide
        """
        if not password or not stored_hash or not salt:
            logger.warning("Parámetros incompletos para verificación")
            return False
        
        try:
            computed_hash, _ = SecurityManager.hash_password(password, salt)
            # Usar comparación segura contra timing attacks
            return hmac.compare_digest(computed_hash, stored_hash)
        except Exception as e:
            logger.error(f"Error verificando contraseña: {e}")
            return False
    
    @staticmethod
    def validate_input(value: str, max_length: int = 255, allow_special: bool = False) -> bool:
        """
        Valida entrada de usuario contra inyecciones.
        
        Args:
            value: Valor a validar
            max_length: Longitud máxima permitida
            allow_special: Si se permiten caracteres especiales
        
        Returns:
            True si es válida
        """
        if not value:
            return False
        
        if len(value) > max_length:
            logger.warning(f"Entrada demasiado larga: {len(value)}")
            return False
        
        # Verificar caracteres de control
        if any(ord(c) < 32 and c not in '\n\t\r' for c in value):
            logger.warning("Entrada contiene caracteres de control")
            return False
        
        if not allow_special:
            # Permitir solo alfanuméricos, espacios y puntuación básica
            forbidden_chars = '<>\"\'|&;()[]{}\\`'
            if any(c in value for c in forbidden_chars):
                logger.warning("Entrada contiene caracteres prohibidos")
                return False
        
        return True
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitiza nombre de archivo.
        
        Args:
            filename: Nombre original
        
        Returns:
            Nombre sanitizado
        """
        # Remover caracteres peligrosos
        forbidden_chars = '<>:"/\\|?*\x00'
        for char in forbidden_chars:
            filename = filename.replace(char, '_')
        
        # Limitar longitud
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        return filename.strip()


# Instancia global singleton
_security_manager = SecurityManager()


def get_security_manager() -> SecurityManager:
    """Obtiene la instancia del gestor de seguridad."""
    return _security_manager


def set_user_context(user_id: str, user_role: str) -> bool:
    """Establece el contexto de usuario."""
    return _security_manager.set_user_context(user_id, user_role)


def check_permission(permission: str) -> bool:
    """Verifica si el usuario tiene permiso."""
    return _security_manager.check_permission(permission)


def require_permission(permission: str) -> bool:
    """Requiere un permiso o lanza excepción."""
    return _security_manager.require_permission(permission)


def hash_password(password: str) -> Tuple[str, str]:
    """Genera hash de contraseña."""
    return SecurityManager.hash_password(password)


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifica contraseña."""
    return SecurityManager.verify_password(password, stored_hash, salt)


def validate_input(value: str, max_length: int = 255, allow_special: bool = False) -> bool:
    """Valida entrada de usuario."""
    return SecurityManager.validate_input(value, max_length, allow_special)


def sanitize_filename(filename: str) -> str:
    """Sanitiza nombre de archivo."""
    return SecurityManager.sanitize_filename(filename)
