"""
Gestor de licencias local con verificación offline
Guarda la fecha de vencimiento de forma segura y verifica localmente
"""

import os
import json
import hashlib
import threading
import time
from datetime import datetime
from typing import Tuple, Dict, Any

# Lock para evitar acceso concurrente al archivo de licencia
_license_lock = threading.Lock()
_lock_timeout = 5  # segundos

# Archivo de licencia (oculto) - Usar VISO/ directory en lugar de _internal
# porque _internal es un directorio de PyInstaller que no siempre es accesible
VISO_DIR = os.path.join(os.path.expanduser('~'), 'VISO') if not os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'VISO')) else os.path.join(os.path.dirname(__file__), '..', 'VISO')

# Intentar usar VISO en el mismo directorio que el proyecto, si no, usar home
if os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'VISO')):
    LICENSES_DIR = os.path.join(os.path.dirname(__file__), '..', 'VISO')
else:
    # PyInstaller: usar directorio en home
    LICENSES_DIR = os.path.join(os.path.expanduser('~'), 'VISO')

os.makedirs(LICENSES_DIR, exist_ok=True)

LICENSE_FILE = os.path.join(LICENSES_DIR, '.lic')  # Archivo oculto

def get_machine_id() -> str:
    """Genera un ID único de la máquina para vincular licencias"""
    try:
        import uuid
        # Usar MAC address como identificador
        mac = uuid.getnode()
        return hashlib.sha256(str(mac).encode()).hexdigest()[:16]
    except:
        return "LOCAL"

def save_license_info(user_id: str, username: str, plan_type: str, 
                      fecha_vencimiento: str, dias_restantes: int) -> bool:
    """
    Guarda la información de licencia localmente de forma segura
    
    Args:
        user_id: ID del usuario (DNI)
        username: Nombre de usuario
        plan_type: Tipo de plan
        fecha_vencimiento: Fecha de vencimiento (YYYY-MM-DD HH:MM:SS)
        dias_restantes: Días restantes
    
    Returns:
        bool: True si se guardó correctamente
    """
    try:
        # Adquirir lock con timeout
        acquired = _license_lock.acquire(timeout=_lock_timeout)
        if not acquired:
            print(f"[LICENCIA] No se pudo adquirir lock para guardar licencia (timeout)")
            return False
        
        try:
            # Crear estructura de licencia
            license_data = {
                'user_id': user_id,
                'username': username,
                'plan_type': plan_type,
                'fecha_vencimiento': fecha_vencimiento,
                'dias_restantes': dias_restantes,
                'fecha_guardado': datetime.now().isoformat(),
                'machine_id': get_machine_id(),
                'version': 1
            }
            
            # Guardar en archivo temporal primero
            temp_file = LICENSE_FILE + '.tmp'
            max_retries = 3
            
            for intento in range(max_retries):
                try:
                    # Escribir en archivo temporal
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(license_data, f, indent=2, ensure_ascii=False)
                    
                    # Reemplazar archivo original con temporal (operación atómica en Windows)
                    if os.path.exists(LICENSE_FILE):
                        try:
                            os.remove(LICENSE_FILE)
                        except:
                            pass  # Ignorar si no se puede eliminar
                    
                    os.rename(temp_file, LICENSE_FILE)
                    
                    # Hacer archivo oculto en Windows
                    if os.name == 'nt':  # Windows
                        import ctypes
                        FILE_ATTRIBUTE_HIDDEN = 0x02
                        try:
                            ctypes.windll.kernel32.SetFileAttributesW(LICENSE_FILE, FILE_ATTRIBUTE_HIDDEN)
                        except:
                            pass  # Ignorar si no se puede hacer oculto
                    
                    print(f"[LICENCIA] OK Licencia actualizada desde servidor")
                    return True
                    
                except (PermissionError, OSError) as e:
                    if intento < max_retries - 1:
                        time.sleep(0.5)  # Esperar antes de reintentar
                        continue
                    else:
                        raise
        finally:
            _license_lock.release()
        
    except Exception as e:
        print(f"[LICENCIA] Error guardando licencia: {e}")
        # Limpiar archivo temporal si existe
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass
        return False

def load_license_info() -> Tuple[bool, Dict[str, Any]]:
    """
    Carga la información de licencia guardada localmente
    
    Returns:
        Tuple[bool, dict]: (existe_licencia, datos_licencia)
    """
    try:
        # Adquirir lock con timeout
        acquired = _license_lock.acquire(timeout=_lock_timeout)
        if not acquired:
            print(f"[LICENCIA] No se pudo adquirir lock para cargar licencia (timeout)")
            return False, {}
        
        try:
            if not os.path.exists(LICENSE_FILE):
                return False, {}
            
            with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
                license_data = json.load(f)
            
            return True, license_data
        finally:
            _license_lock.release()
        
    except Exception as e:
        print(f"[LICENCIA] Error cargando licencia: {e}")
        return False, {}

def verify_local_license(user_id: str) -> Tuple[bool, str, int]:
    """
    Verifica la licencia guardada localmente
    
    Args:
        user_id: ID del usuario a verificar
    
    Returns:
        Tuple[bool, str, int]: (es_valida, razon, dias_restantes)
            - es_valida: True si la licencia es válida
            - razon: Razón si no es válida (expirada, no_existe, etc)
            - dias_restantes: Días restantes (negativo si expiró)
    """
    exists, license_data = load_license_info()
    
    if not exists:
        return False, "sin_licencia", 0
    
    # Verificar que sea para el usuario correcto
    if license_data.get('user_id') != user_id:
        return False, "usuario_incorrecto", 0
    
    try:
        # Parsear fecha de vencimiento
        fecha_vencimiento_str = license_data.get('fecha_vencimiento', '').strip()
        
        # Si fecha está vacía, archivo corrupto o incompleto - ignorar
        if not fecha_vencimiento_str:
            return False, "licencia_incompleta", 0
        
        fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d %H:%M:%S')
        
        # Fecha actual
        hoy = datetime.now()
        
        # Verificar si venció
        if hoy > fecha_vencimiento:
            # Licencia expirada
            dias_expirados = (hoy - fecha_vencimiento).days
            return False, "expirada", -dias_expirados
        else:
            # Licencia válida
            dias_restantes = (fecha_vencimiento - hoy).days
            plan = license_data.get('plan_type', 'Desconocido')
            print(f"[LICENCIA] OK Licencia local valida ({plan}) - {dias_restantes} dias restantes")
            return True, "valida", dias_restantes
            
    except Exception as e:
        print(f"[LICENCIA] Error en verificacion: {e}")
        return False, "error", 0

def clear_license():
    """Elimina la información de licencia guardada"""
    try:
        # Adquirir lock con timeout
        acquired = _license_lock.acquire(timeout=_lock_timeout)
        if not acquired:
            print(f"[LICENCIA] No se pudo adquirir lock para eliminar licencia (timeout)")
            return False
        
        try:
            if os.path.exists(LICENSE_FILE):
                os.remove(LICENSE_FILE)
                print(f"[LICENCIA] Licencia eliminada")
                return True
        finally:
            _license_lock.release()
    except Exception as e:
        print(f"[LICENCIA] Error eliminando licencia: {e}")
    return False

def get_license_info() -> Dict[str, Any]:
    """Obtiene la información de licencia guardada"""
    exists, license_data = load_license_info()
    if exists:
        return license_data
    return {}
