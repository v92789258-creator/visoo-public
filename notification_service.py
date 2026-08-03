"""
Servicio de notificaciones VISO que corre en background
Se ejecuta cada 2 segundos aunque la aplicación esté cerrada
"""

import requests
import json
import os
import time
import subprocess
import winsound
import threading
import socket
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any

try:
    from utils.error_logger import get_logger
except ImportError:
    # Fallback si error_logger no está disponible
    import logging
    logging.basicConfig(level=logging.INFO)
    get_logger = logging.getLogger

logger = get_logger('NOTIFICATION_SERVICE')

NOTIFICATION_POLL_INTERVAL_SECONDS = 45 * 60

# Puerto para indicar que el servicio está corriendo
SERVICE_PORT = 55124

# Lock para evitar múltiples sonidos simultáneos
notification_lock = threading.Lock()
notification_event = threading.Event()

# Archivo para guardar el último ID de notificación visto
STATE_FILE = Path(os.path.expanduser("~")) / ".viso" / "notification_state.json"
STATE_FILE.parent.mkdir(exist_ok=True)

# Protocolos permitidos para URLs
ALLOWED_PROTOCOLS = ('http', 'https')
WHITELIST_DOMAINS = [
    'boletaspe.com',
    'api.yhana.cloud',
    'localhost',
    '127.0.0.1'
]

def start_service_listener():
    """Inicia un listener de socket para indicar que el servicio está corriendo."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('localhost', SERVICE_PORT))
        sock.listen(1)
        sock.settimeout(1)
        
        def listener():
            while True:
                try:
                    conn, addr = sock.accept()
                    conn.close()
                except socket.timeout:
                    continue
                except Exception:
                    break
        
        thread = threading.Thread(target=listener, daemon=True)
        thread.start()
    except Exception:
        pass

def load_last_notification_id():
    """Carga el último ID de notificación visto."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_id', 0)
    except Exception:
        pass
    return 0

def save_last_notification_id(notif_id):
    """Guarda el último ID de notificación visto de forma thread-safe."""
    try:
        # Usar lock para evitar race conditions
        with notification_lock:
            data = {'last_id': notif_id, 'timestamp': datetime.now().isoformat()}
            # Crear archivo temporalmente y luego renombrar (operación atómica)
            temp_file = STATE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            # Renombrar es operación atómica en la mayoría de SO
            temp_file.replace(STATE_FILE)
            logger.debug(f"Guardado último ID: {notif_id}")
    except Exception as e:
        logger.error(f"Error guardando estado: {e}")

def validate_url(url: str) -> bool:
    """
    Valida una URL para evitar XSS y path traversal.
    
    Verificaciones:
    - Protocolo permitido (http/https)
    - Dominio en whitelist o es URL local
    - Sin caracteres peligrosos
    - Longitud máxima respetada
    """
    if not url or not isinstance(url, str):
        logger.warning(f"URL inválida: tipo={type(url)}")
        return False
    
    try:
        # Validar que no esté vacía o sea muy larga (posible ataque)
        if len(url) > 2048:
            logger.warning(f"URL demasiado larga: {len(url)} caracteres")
            return False
        
        # Parsear URL
        parsed = urlparse(url)
        
        # Validar protocolo
        if parsed.scheme.lower() not in ALLOWED_PROTOCOLS:
            logger.warning(f"Protocolo no permitido: {parsed.scheme}")
            return False
        
        # Validar que tenga netloc (dominio)
        if not parsed.netloc:
            logger.warning("URL sin dominio")
            return False
        
        # Extraer dominio sin puerto
        domain = parsed.netloc.split(':')[0].lower()
        
        # Validar dominio - debe estar en whitelist o ser localhost
        domain_valid = False
        for allowed_domain in WHITELIST_DOMAINS:
            if domain.endswith(allowed_domain) or domain == allowed_domain:
                domain_valid = True
                break
        
        if not domain_valid:
            logger.warning(f"Dominio no autorizado: {domain}")
            return False
        
        # Validar que no contenga caracteres de control
        if any(ord(c) < 32 for c in url):
            logger.warning("URL contiene caracteres de control")
            return False
        
        logger.debug(f"URL validada: {domain}{parsed.path}")
        return True
        
    except Exception as e:
        logger.error(f"Error validando URL: {e}")
        return False

def execute_notification_action(accion: str, enlace: str = '') -> None:
    """
    Ejecuta la acción asociada a la notificación de forma segura.
    
    Args:
        accion: Tipo de acción (abrir_url, abrir_viso, etc)
        enlace: URL o parámetro de la acción
    """
    if not isinstance(accion, str) or not isinstance(enlace, str):
        logger.warning(f"Parámetros inválidos: accion={type(accion)}, enlace={type(enlace)}")
        return
    
    try:
        if accion == 'abrir_url' and enlace:
            # Validar URL antes de abrir
            if not validate_url(enlace):
                logger.warning(f"URL rechazada por validación: {enlace}")
                return
            
            # Abrir URL en navegador (subprocess es más seguro que webbrowser)
            try:
                subprocess.run(
                    ['cmd', '/c', 'start', enlace],
                    shell=False,
                    timeout=5,
                    check=False,
                    capture_output=True
                )
                logger.info(f"URL abierta: {enlace}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout abriendo URL: {enlace}")
            except Exception as e:
                logger.error(f"Error abriendo URL: {e}")
                
        elif accion == 'abrir_viso':
            # Abrir VISO de forma segura
            try:
                viso_paths = [
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "VISO.exe"),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "VISO.exe"),
                ]
                
                viso_path = None
                for path in viso_paths:
                    if os.path.exists(path) and os.path.isfile(path):
                        viso_path = path
                        break
                
                if viso_path:
                    subprocess.Popen(
                        [viso_path],
                        shell=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    logger.info(f"VISO lanzado desde: {viso_path}")
                else:
                    logger.warning("VISO.exe no encontrado")
            except Exception as e:
                logger.error(f"Error lanzando VISO: {e}")
        else:
            if accion and accion != 'ninguno':
                logger.debug(f"Acción desconocida: {accion}")
    
    except Exception as e:
        logger.error(f"Error ejecutando acción {accion}: {e}")

def show_windows_notification(title: str, message: str, enlace: str = None) -> None:
    """
    Muestra una notificación nativa de Windows 10/11 de forma segura.
    
    Args:
        title: Título de la notificación
        message: Cuerpo del mensaje
        enlace: URL opcional a abrir
    """
    if not isinstance(title, str) or not isinstance(message, str):
        logger.warning(f"Parámetros inválidos: title={type(title)}, message={type(message)}")
        return
    
    try:
        # Sanitizar título y mensaje (escapar comillas para PowerShell)
        safe_title = title.replace('"', '\"').replace('$', '`$')[:100]  # Limitar longitud
        safe_message = message.replace('"', '\"').replace('$', '`$')[:500]  # Limitar longitud
        
        ps_command = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $notifyIcon = New-Object System.Windows.Forms.NotifyIcon
        $notifyIcon.Icon = [System.Drawing.SystemIcons]::Information
        $notifyIcon.Visible = $true
        $notifyIcon.ShowBalloonTip(5000, "{safe_title}", "{safe_message}", [System.Windows.Forms.ToolTipIcon]::Info)
        Start-Sleep -Milliseconds 5000
        $notifyIcon.Dispose()
        """
        
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            timeout=10,
            check=False
        )
        
        logger.info(f"Notificación mostrada: {safe_title}")
        
        # Si hay un enlace, abrirlo después de mostrar la notificación
        if enlace:
            time.sleep(1)
            if isinstance(enlace, str) and enlace.lower() == "viso":
                # Abrir VISO directamente
                execute_notification_action('abrir_viso', '')
            elif isinstance(enlace, str):
                # Abrir URL en navegador (con validación)
                execute_notification_action('abrir_url', enlace)
                
    except subprocess.TimeoutExpired:
        logger.warning("Timeout mostrando notificación")
    except Exception as e:
        logger.error(f"Error en notificación Windows: {e}")

def play_sound():
    """Reproduce sonido de notificación profesional."""
    try:
        # Sonido más profesional y agradable (secuencia melódica)
        # Notas: Do, Mi, Sol (acorde Do Mayor)
        winsound.Beep(262, 200)  # Do (C4)
        time.sleep(0.1)
        winsound.Beep(330, 200)  # Mi (E4)
        time.sleep(0.1)
        winsound.Beep(392, 300)  # Sol (G4) - más largo
    except Exception:
        pass

def check_notifications() -> None:
    """Verifica si hay notificaciones nuevas de forma segura."""
    try:
        response = requests.get("https://api.yhana.cloud/api/win/notis.php", timeout=5)
        if response.status_code == 200:
            data = response.json()
            notifications = data if isinstance(data, list) else data.get("notificaciones", [])
            
            # Validar que sea una lista
            if not isinstance(notifications, list):
                logger.warning("Respuesta de notificaciones no es una lista")
                return
            
            last_id = load_last_notification_id()
            
            # Buscar notificaciones nuevas
            for notif in notifications:
                try:
                    # Validar estructura de notificación
                    if not isinstance(notif, dict):
                        logger.debug(f"Notificación ignorada (no es dict): {type(notif)}")
                        continue
                    
                    notif_id = notif.get('id', 0)
                    
                    # Validar que el ID sea un número
                    if not isinstance(notif_id, (int, float)):
                        logger.warning(f"ID de notificación inválido: {notif_id}")
                        continue
                    
                    if notif_id > last_id and notif.get('activo', 1):
                        # Nueva notificación encontrada
                        title = str(notif.get('titulo', 'Nueva notificación VISO'))[:100]
                        message = str(notif.get('mensaje', ''))[:500]
                        enlace = str(notif.get('enlace', '')) if notif.get('enlace') else None
                        accion = str(notif.get('accion', 'ninguno')).lower()
                        
                        logger.info(f"Nueva notificación (ID {notif_id}): {title}")
                        
                        # Usar lock para evitar múltiples sonidos
                        with notification_lock:
                            show_windows_notification(title, message, enlace)
                            play_sound()
                        
                        # Ejecutar acción asociada inmediatamente (con validación)
                        if accion and accion != 'ninguno':
                            execute_notification_action(accion, enlace if enlace else '')
                        
                        save_last_notification_id(int(notif_id))
                        
                        # Esperar un poco entre notificaciones
                        time.sleep(1)
                        
                except ValueError as e:
                    logger.warning(f"Error de conversión de tipo en notificación: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error procesando notificación: {e}")
                    continue
    
    except requests.exceptions.Timeout:
        logger.debug("Timeout conectando a servidor de notificaciones")
    except requests.exceptions.ConnectionError as e:
        logger.debug(f"Error de conexión: {e}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error de request: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decodificando JSON de notificaciones: {e}")
    except Exception as e:
        logger.error(f"Error verificando notificaciones: {e}")

def main() -> None:
    """Loop principal con manejo de errores robusto."""
    logger.info("=" * 60)
    logger.info("Servicio de notificaciones VISO iniciado")
    logger.info("=" * 60)
    
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while True:
        try:
            check_notifications()
            consecutive_errors = 0  # Reset contador de errores
            
        except KeyboardInterrupt:
            logger.info("Servicio interrumpido por usuario")
            break
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error en loop principal (intento {consecutive_errors}): {e}")
            
            # Si hay demasiados errores consecutivos, esperar más tiempo
            if consecutive_errors >= max_consecutive_errors:
                logger.critical(f"Demasiados errores consecutivos ({consecutive_errors}), esperando...")
                time.sleep(10)
                consecutive_errors = 0
        
        # Esperar 2 segundos antes de verificar de nuevo (como WhatsApp)
        try:
            time.sleep(NOTIFICATION_POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Servicio interrumpido durante sleep")
            break

if __name__ == "__main__":
    try:
        # Iniciar listener de socket para indicar que el servicio está corriendo
        start_service_listener()
        logger.info("Service listener iniciado")
        main()
    except KeyboardInterrupt:
        logger.info("Servicio finalizado por usuario")
    except Exception as e:
        logger.critical(f"Error crítico en servicio: {e}")
        raise
    finally:
        logger.info("=" * 60)
        logger.info("Servicio de notificaciones VISO finalizado")
        logger.info("=" * 60)
