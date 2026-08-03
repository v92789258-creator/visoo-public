"""
Herramientas administrativas para gestionar bloqueos de dispositivos.
Permite al administrador ver y modificar los dispositivos registrados para cada usuario.
"""

from utils.device_lock import obtener_archivo_device_lock, obtener_info_dispositivo_actual
import json
from pathlib import Path


def listar_usuarios_bloqueados(base_dir):
    """
    Lista todos los usuarios que tienen un dispositivo registrado.
    
    Retorna un diccionario con la información de cada usuario.
    """
    try:
        lock_file = obtener_archivo_device_lock(base_dir)
        
        if not lock_file.exists():
            return {}
        
        with open(lock_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    except Exception as e:
        print(f"[ERROR] Error listando usuarios bloqueados: {e}")
        return {}


def obtener_info_dispositivo_usuario(base_dir, username):
    """Obtiene la información del dispositivo registrado para un usuario."""
    usuarios = listar_usuarios_bloqueados(base_dir)
    return usuarios.get(username, None)


def permitir_nuevo_dispositivo(base_dir, username, user_id):
    """
    Reinicia el bloqueo de dispositivo para un usuario.
    Permite que se registre en un nuevo dispositivo en el siguiente login.
    
    El usuario deberá hacer login nuevamente para registrarse en el nuevo dispositivo.
    """
    try:
        lock_file = obtener_archivo_device_lock(base_dir)
        
        device_locks = {}
        if lock_file.exists():
            with open(lock_file, 'r', encoding='utf-8') as f:
                device_locks = json.load(f)
        
        # Remover el usuario del lock
        if username in device_locks:
            del device_locks[username]
            
            with open(lock_file, 'w', encoding='utf-8') as f:
                json.dump(device_locks, f, indent=4, ensure_ascii=False)
            
            print(f"[DEVICE_LOCK] Usuario '{username}' desbloqueado - Se puede registrar en nuevo dispositivo")
            return True
        else:
            print(f"[DEVICE_LOCK] Usuario '{username}' no tiene dispositivo registrado")
            return False
    
    except Exception as e:
        print(f"[ERROR] Error desbloqueando usuario: {e}")
        return False


def cambiar_dispositivo_permitido(base_dir, username, user_id):
    """
    Alias para permitir_nuevo_dispositivo.
    Permite que el usuario se registre en un nuevo dispositivo.
    """
    return permitir_nuevo_dispositivo(base_dir, username, user_id)


def obtener_resumen_dispositivo(device_info):
    """
    Crea un resumen legible de la información del dispositivo.
    """
    if not device_info:
        return "Sin información"
    
    return f"""
    MAC Address: {device_info.get('mac', 'N/A')}
    Hostname: {device_info.get('hostname', 'N/A')}
    Hardware ID: {device_info.get('hardware_id', 'N/A')}
    Device Hash: {device_info.get('device_hash', 'N/A')[:16]}...
    Fecha Registro: {device_info.get('fecha_registro', 'N/A')}
    """


def mostrar_info_dispositivo_actual():
    """Muestra la información del dispositivo actual (para debugging)."""
    info = obtener_info_dispositivo_actual()
    print("\n=== INFORMACIÓN DEL DISPOSITIVO ACTUAL ===")
    print(f"MAC Address: {info['mac']}")
    print(f"Hostname: {info['hostname']}")
    print(f"Hardware ID: {info['hardware_id']}")
    print(f"Device Hash: {info['device_hash']}")
    print(f"Device String: {info['device_string']}")
    print("=" * 40)


def limpiar_todos_los_bloqueos(base_dir):
    """
    ⚠️ FUNCIÓN ADMINISTRATIVA - Limpia todos los bloqueos de dispositivos.
    Requiere confirmación.
    """
    try:
        lock_file = obtener_archivo_device_lock(base_dir)
        
        if lock_file.exists():
            respuesta = input("\n⚠️  ¿Estás seguro de que quieres limpiar TODOS los bloqueos de dispositivos? (s/n): ").lower()
            
            if respuesta == 's':
                lock_file.unlink()  # Eliminar archivo
                print("[DEVICE_LOCK] ✅ Todos los bloqueos de dispositivos han sido eliminados")
                return True
            else:
                print("[DEVICE_LOCK] Operación cancelada")
                return False
        else:
            print("[DEVICE_LOCK] No hay bloqueos de dispositivos registrados")
            return False
    
    except Exception as e:
        print(f"[ERROR] Error limpiando bloqueos: {e}")
        return False
