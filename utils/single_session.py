"""
Sistema de Single Session - Solo una sesión activa por usuario.
Previene que un usuario esté logueado en múltiples PCs simultáneamente.
"""

import json
import os
import datetime
from pathlib import Path
from utils.device_lock import generar_device_id


def obtener_archivo_sesiones_activas(base_dir):
    """Obtiene la ruta del archivo de sesiones activas."""
    lock_dir = Path(base_dir) / 'VISO' / '.sessions'
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / 'active_sessions.json'


def obtener_sesiones_activas(base_dir):
    """Obtiene todas las sesiones activas actualmente."""
    try:
        session_file = obtener_archivo_sesiones_activas(base_dir)
        
        if not session_file.exists():
            return {}
        
        with open(session_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    except Exception as e:
        print(f"[ERROR] Error leyendo sesiones activas: {e}")
        return {}


def registrar_sesion_activa(base_dir, username, user_id, device_info=None):
    """
    Registra una nueva sesión activa para un usuario.
    
    Args:
        base_dir: Directorio base de la aplicación
        username: Nombre de usuario
        user_id: ID del usuario
        device_info: Información del dispositivo (opcional)
    """
    try:
        if device_info is None:
            device_info = generar_device_id()
        
        session_file = obtener_archivo_sesiones_activas(base_dir)
        
        sesiones = obtener_sesiones_activas(base_dir)
        
        # Registrar la sesión
        sesiones[username] = {
            'user_id': user_id,
            'mac': device_info['mac'],
            'hostname': device_info['hostname'],
            'hardware_id': device_info['hardware_id'],
            'fecha_inicio': datetime.datetime.now().isoformat(),
            'hora_inicio_legible': datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'device_hash': device_info['device_hash']
        }
        
        # Guardar
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(sesiones, f, indent=4, ensure_ascii=False)
        
        print(f"[SESSION] Sesión registrada para '{username}' en {device_info['hostname']}")
        return True
    
    except Exception as e:
        print(f"[ERROR] Error registrando sesión: {e}")
        return False


def cerrar_sesion(base_dir, username):
    """
    Cierra la sesión de un usuario (se llama al logout).
    """
    try:
        session_file = obtener_archivo_sesiones_activas(base_dir)
        
        if not session_file.exists():
            return True
        
        sesiones = obtener_sesiones_activas(base_dir)
        
        if username in sesiones:
            del sesiones[username]
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(sesiones, f, indent=4, ensure_ascii=False)
            
            print(f"[SESSION] Sesión cerrada para '{username}'")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Error cerrando sesión: {e}")
        return False


def validar_sesion_unica(base_dir, username):
    """
    Valida que el usuario no tenga otra sesión activa en otra PC.
    
    Retorna:
        (True, "OK") - El usuario no tiene otra sesión activa
        (False, "Mensaje de error con detalles") - El usuario ya está logueado en otra PC
    """
    try:
        device_actual = generar_device_id()
        sesiones = obtener_sesiones_activas(base_dir)
        
        # Si el usuario no tiene sesión registrada, está bien
        if username not in sesiones:
            print(f"[SESSION] Usuario '{username}' no tiene sesión activa previa")
            return True, "OK"
        
        sesion_activa = sesiones[username]
        
        # Verificar si la sesión activa es en el mismo dispositivo
        if (sesion_activa['mac'] == device_actual['mac'] and 
            sesion_activa['hostname'] == device_actual['hostname']):
            # Mismo dispositivo - permitir
            print(f"[SESSION] Usuario '{username}' reconectando en el mismo dispositivo")
            return True, "OK"
        
        # Sesión activa en otro dispositivo - BLOQUEAR
        print(f"[SESSION] ❌ Usuario '{username}' ya tiene sesión activa en otra PC")
        
        hostname_anterior = sesion_activa['hostname']
        hora_anterior = sesion_activa['hora_inicio_legible']
        mac_anterior = sesion_activa['mac']
        
        mensaje_error = (
            f"❌ Este usuario ya está logueado en otra computadora\n\n"
            f"PC Activa: {hostname_anterior}\n"
            f"MAC: {mac_anterior}\n"
            f"Desde: {hora_anterior}\n\n"
            f"Por seguridad, solo se permite una sesión activa por usuario.\n"
            f"Cierra la sesión anterior e intenta nuevamente."
        )
        
        return False, mensaje_error
    
    except Exception as e:
        print(f"[ERROR] Error validando sesión única: {e}")
        import traceback
        traceback.print_exc()
        return True, "OK"  # No bloquear si hay error


def obtener_info_sesion_activa(base_dir, username):
    """Obtiene la información de la sesión activa de un usuario."""
    sesiones = obtener_sesiones_activas(base_dir)
    return sesiones.get(username, None)


def listar_todas_sesiones_activas(base_dir):
    """Lista todas las sesiones activas (para debugging/admin)."""
    return obtener_sesiones_activas(base_dir)


def limpiar_todas_sesiones(base_dir):
    """
    ⚠️ FUNCIÓN ADMINISTRATIVA - Limpia todas las sesiones activas.
    """
    try:
        session_file = obtener_archivo_sesiones_activas(base_dir)
        
        if session_file.exists():
            session_file.unlink()
            print("[SESSION] Todas las sesiones activas han sido limpias")
            return True
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Error limpiando sesiones: {e}")
        return False
