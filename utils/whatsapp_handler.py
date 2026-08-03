"""
Manejador global de WhatsApp para VISO.
Localiza y abre WhatsApp desde ubicaciones comunes en Windows.
"""

import os
import sys
import subprocess
import platform
import logging
import webbrowser
import time
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_whatsapp_exe() -> Optional[str]:
    r"""
    Busca la ubicación de whatsapp.exe en el sistema Windows.
    
    Busca en:
    1. %APPDATA%\WhatsApp
    2. %PROGRAMFILES%\WhatsApp
    3. %PROGRAMFILES(X86)%\WhatsApp
    4. Carpeta de aplicaciones locales
    
    Returns:
        str: Ruta completa a whatsapp.exe o None si no se encuentra
    """
    if platform.system() != "Windows":
        return None
    
    # Ubicaciones comunes donde se instala WhatsApp
    posibles_rutas = [
        # AppData (instalación de Microsoft Store)
        Path(os.getenv('APPDATA', '')) / 'WhatsApp' / 'WhatsApp.exe',
        Path(os.getenv('LOCALAPPDATA', '')) / 'WhatsApp' / 'app' / 'WhatsApp.exe',
        
        # Program Files
        Path(os.getenv('PROGRAMFILES', 'C:\\Program Files')) / 'WhatsApp' / 'WhatsApp.exe',
        
        # Program Files (x86)
        Path(os.getenv('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')) / 'WhatsApp' / 'WhatsApp.exe',
        
        # Ubicación alternativa en AppData
        Path(os.getenv('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'WhatsApp' / 'WhatsApp.lnk',
    ]
    
    for ruta in posibles_rutas:
        if ruta.exists():
            logger.info(f"WhatsApp encontrado en: {ruta}")
            return str(ruta)
    
    # Si no se encuentra en las rutas comunes, intentar con el comando directo
    logger.warning("WhatsApp no encontrado en ubicaciones estándar, intentando con comando directo")
    return None


def copy_pdf_to_shared_location(pdf_path: str) -> Optional[str]:
    """
    Copia el PDF a la carpeta de Descargas para facilitar el acceso.
    
    Args:
        pdf_path: Ruta original del PDF
    
    Returns:
        str: Ruta de la copia en Descargas, o None si falla
    """
    try:
        if not os.path.exists(pdf_path):
            logger.error(f"PDF no existe: {pdf_path}")
            return None
        
        # Obtener carpeta de Descargas
        downloads_path = Path.home() / 'Downloads'
        downloads_path.mkdir(exist_ok=True)
        
        # Obtener nombre del archivo
        filename = os.path.basename(pdf_path)
        dest_path = downloads_path / filename
        
        # Copiar archivo
        shutil.copy2(pdf_path, dest_path)
        logger.info(f"PDF copiado a: {dest_path}")
        
        return str(dest_path)
    except Exception as e:
        logger.error(f"Error copiando PDF: {e}")
        return None


def send_whatsapp_message(phone_number: str, message: str = "", pdf_path: str = "") -> bool:
    """
    Envía un mensaje a través de WhatsApp Desktop con el archivo adjunto.
    
    Args:
        phone_number: Número de teléfono (ej: 51999999999)
        message: Mensaje opcional a enviar
        pdf_path: Ruta del PDF a compartir
    
    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    try:
        # Limpiar número de espacios y caracteres especiales
        phone_clean = ''.join(c for c in phone_number if c.isdigit())
        
        # Copiar PDF a una ubicación accesible
        pdf_accessible = pdf_path
        if pdf_path and os.path.exists(pdf_path):
            copied_path = copy_pdf_to_shared_location(pdf_path)
            if copied_path:
                pdf_accessible = copied_path
        
        # Abrir WhatsApp Desktop
        whatsapp_exe = find_whatsapp_exe()
        if whatsapp_exe and whatsapp_exe.endswith('.exe'):
            try:
                subprocess.Popen([whatsapp_exe])
                logger.info(f"WhatsApp Desktop abierto")
                
                # Esperar a que se abra
                time.sleep(2)
                
                # Crear URL para abrir el chat
                webbrowser.open(f"whatsapp://send?phone={phone_clean}&text={message}")
                
                return True
            except Exception as e:
                logger.error(f"Error abriendo WhatsApp Desktop: {e}")
                # Fallback a Web
                pass
        
        # Fallback: Abrir WhatsApp Web
        import urllib.parse
        message_encoded = urllib.parse.quote(message)
        whatsapp_url = f"https://wa.me/{phone_clean}?text={message_encoded}"
        webbrowser.open(whatsapp_url, new=2)
        
        logger.info(f"WhatsApp Web abierto para {phone_clean}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar mensaje de WhatsApp: {e}")
        return False



def open_whatsapp() -> bool:
    """
    Abre la aplicación de WhatsApp.
    
    Returns:
        bool: True si se abrió correctamente, False en caso contrario
    """
    try:
        if platform.system() == "Windows":
            whatsapp_path = find_whatsapp_exe()
            
            if whatsapp_path and whatsapp_path.endswith('.exe'):
                # Abrir directamente si es un .exe
                subprocess.Popen(whatsapp_path)
                logger.info("WhatsApp abierto exitosamente")
                return True
            else:
                # Intentar con el protocolo whatsapp:
                os.startfile("whatsapp:")
                logger.info("WhatsApp abierto con protocolo whatsapp:")
                return True
                
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(['open', '/Applications/WhatsApp.app'], check=True)
            logger.info("WhatsApp abierto en macOS")
            return True
            
        elif platform.system() == "Linux":
            subprocess.run(['whatsapp'], check=True)
            logger.info("WhatsApp abierto en Linux")
            return True
            
    except FileNotFoundError:
        logger.error("WhatsApp no encontrado. Asegúrate de tenerlo instalado.")
        return False
    except Exception as e:
        logger.error(f"Error al abrir WhatsApp: {e}")
        return False
    
    return False


def get_whatsapp_message_url(phone_number: str, message: str = "") -> str:
    """
    Genera una URL para abrir WhatsApp con un número específico.
    
    Args:
        phone_number: Número de teléfono (ej: 51999999999)
        message: Mensaje opcional a enviar
    
    Returns:
        str: URL de WhatsApp Web o protocolo whatsapp://
    """
    # Limpiar número de espacios y caracteres especiales
    phone_clean = ''.join(c for c in phone_number if c.isdigit())
    
    if message:
        # Encoded message for URL
        import urllib.parse
        message_encoded = urllib.parse.quote(message)
        return f"https://wa.me/{phone_clean}?text={message_encoded}"
    else:
        return f"whatsapp://send?phone={phone_clean}"

