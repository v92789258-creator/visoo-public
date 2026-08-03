"""
Sistema de bloqueo de dispositivo - Restringe el acceso de usuarios a una PC específica.
Genera un ID único basado en MAC address, hostname y hardware ID.
"""

import socket
import platform
import uuid
import json
import os
import hashlib
from pathlib import Path


def obtener_mac_address():
    """Obtiene la dirección MAC de la red."""
    try:
        mac = uuid.getnode()
        mac_str = ':'.join(['{:02x}'.format((mac >> ele) & 0xff) for ele in range(0, 8*6, 8)][::-1])
        return mac_str
    except Exception as e:
        print(f"[ERROR] Error obteniendo MAC address: {e}")
        return "UNKNOWN_MAC"


def obtener_hostname():
    """Obtiene el nombre de la computadora."""
    try:
        return socket.gethostname()
    except Exception as e:
        print(f"[ERROR] Error obteniendo hostname: {e}")
        return "UNKNOWN_HOST"


def obtener_hardware_id():
    """Obtiene un ID de hardware basado en el sistema operativo."""
    try:
        if platform.system() == "Windows":
            # En Windows, usar el ID de volumen del disco C:
            import subprocess
            result = subprocess.run(
                ['wmic', 'logicaldisk', 'where', 'name="C:"', 'get', 'volumeserialnumber'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].strip()
        elif platform.system() == "Linux":
            # En Linux, usar el serial number del disco
            import subprocess
            result = subprocess.run(['lsblk', '-d', '-o', 'SERIAL'], capture_output=True, text=True, timeout=5)
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].strip()
    except Exception as e:
        print(f"[ERROR] Error obteniendo hardware ID: {e}")
    
    return "UNKNOWN_HW"


def generar_device_id():
    """Genera un ID único del dispositivo combinando MAC, hostname y hardware."""
    mac = obtener_mac_address()
    hostname = obtener_hostname()
    hw_id = obtener_hardware_id()
    
    # Combinar los tres componentes
    device_string = f"{mac}:{hostname}:{hw_id}"
    
    # Crear hash para hacerlo más corto pero único
    device_hash = hashlib.sha256(device_string.encode()).hexdigest()[:32]
    
    return {
        'mac': mac,
        'hostname': hostname,
        'hardware_id': hw_id,
        'device_hash': device_hash,
        'device_string': device_string
    }


def obtener_archivo_device_lock(base_dir):
    """Obtiene la ruta del archivo de bloqueo de dispositivo."""
    lock_dir = Path(base_dir) / 'VISO' / '.device_lock'
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / 'device_lock.json'


def registrar_usuario_en_dispositivo(base_dir, username, user_id):
    """
    Registra un usuario para estar bloqueado a este dispositivo.
    Se llama cuando el usuario hace login por primera vez en esta PC.
    """
    try:
        device_info = generar_device_id()
        lock_file = obtener_archivo_device_lock(base_dir)
        
        # Cargar archivo actual
        device_locks = {}
        if lock_file.exists():
            with open(lock_file, 'r', encoding='utf-8') as f:
                device_locks = json.load(f)
        
        # Guardar información del usuario
        device_locks[username] = {
            'user_id': user_id,
            'mac': device_info['mac'],
            'hostname': device_info['hostname'],
            'hardware_id': device_info['hardware_id'],
            'device_hash': device_info['device_hash'],
            'fecha_registro': __import__('datetime').datetime.now().isoformat()
        }
        
        # Guardar archivo
        with open(lock_file, 'w', encoding='utf-8') as f:
            json.dump(device_locks, f, indent=4, ensure_ascii=False)
        
        print(f"[DEVICE_LOCK] Usuario '{username}' registrado en este dispositivo")
        return True
    
    except Exception as e:
        print(f"[ERROR] Error registrando usuario en dispositivo: {e}")
        return False


def validar_dispositivo_usuario(base_dir, username):
    """
    Valida que el usuario esté intentando acceder desde el dispositivo registrado.
    
    Retorna:
        (True, "Dispositivo válido") - Si el dispositivo coincide
        (False, "Dispositivo no registrado") - Si el usuario nunca ha hecho login en esta PC
        (False, "Dispositivo no coincide") - Si intenta acceder desde otra PC
    """
    try:
        lock_file = obtener_archivo_device_lock(base_dir)
        
        # Si el archivo no existe, es la primera vez que este usuario intenta acceder
        if not lock_file.exists():
            print(f"[DEVICE_LOCK] Primer login de '{username}' en esta PC - Se registrará")
            return True, "Primer acceso - Se registrará este dispositivo"
        
        # Cargar información de bloqueos
        with open(lock_file, 'r', encoding='utf-8') as f:
            device_locks = json.load(f)
        
        # Si el usuario no está registrado
        if username not in device_locks:
            print(f"[DEVICE_LOCK] Usuario '{username}' no está registrado en esta PC")
            return True, "Usuario nuevo en esta PC - Se registrará"
        
        # Obtener el device ID actual
        device_actual = generar_device_id()
        device_registrado = device_locks[username]
        
        # Validar cada componente
        componentes_validos = []
        componentes_invalidos = []
        
        if device_actual['mac'] == device_registrado['mac']:
            componentes_validos.append('MAC')
        else:
            componentes_invalidos.append(f"MAC (registrada: {device_registrado['mac']}, actual: {device_actual['mac']})")
        
        if device_actual['hostname'] == device_registrado['hostname']:
            componentes_validos.append('Hostname')
        else:
            componentes_invalidos.append(f"Hostname (registrado: {device_registrado['hostname']}, actual: {device_actual['hostname']})")
        
        if device_actual['hardware_id'] == device_registrado['hardware_id']:
            componentes_validos.append('Hardware ID')
        else:
            componentes_invalidos.append(f"Hardware ID (registrado: {device_registrado['hardware_id']}, actual: {device_actual['hardware_id']})")
        
        # Si al menos 2 de 3 componentes coinciden, es válido (en caso de cambios de red, etc)
        if len(componentes_validos) >= 2:
            print(f"[DEVICE_LOCK] Dispositivo válido para '{username}' - Componentes: {', '.join(componentes_validos)}")
            return True, "Dispositivo válido"
        else:
            print(f"[DEVICE_LOCK] ❌ Dispositivo NO coincide para '{username}'")
            print(f"  Componentes válidos: {componentes_validos}")
            print(f"  Componentes inválidos: {componentes_invalidos}")
            return False, f"Este usuario está registrado en otra PC.\nComponentes no coinciden: {', '.join(componentes_invalidos)}"
    
    except Exception as e:
        print(f"[ERROR] Error validando dispositivo: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error al validar dispositivo: {str(e)}"


def obtener_info_dispositivo_registrado(base_dir, username):
    """Obtiene la información del dispositivo registrado para un usuario."""
    try:
        lock_file = obtener_archivo_device_lock(base_dir)
        
        if not lock_file.exists():
            return None
        
        with open(lock_file, 'r', encoding='utf-8') as f:
            device_locks = json.load(f)
        
        return device_locks.get(username, None)
    
    except Exception as e:
        print(f"[ERROR] Error obteniendo info de dispositivo: {e}")
        return None


def obtener_info_dispositivo_actual():
    """Obtiene la información del dispositivo actual."""
    return generar_device_id()
