"""
Gestor de configuración de mensajes para WhatsApp.
Permite guardar y cargar mensajes personalizados.
"""

import json
import os
from pathlib import Path

# Ruta del archivo de configuración
CONFIG_DIR = Path.home() / '.viso_config'
WHATSAPP_CONFIG_FILE = CONFIG_DIR / 'whatsapp_messages.json'


def create_config_dir():
    """Crea el directorio de configuración si no existe."""
    CONFIG_DIR.mkdir(exist_ok=True)


def get_default_message() -> str:
    """
    Obtiene el mensaje predeterminado para WhatsApp.
    
    Returns:
        str: Mensaje guardado o mensaje por defecto
    """
    try:
        create_config_dir()
        
        if WHATSAPP_CONFIG_FILE.exists():
            with open(WHATSAPP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('default_message', get_factory_default_message())
    except Exception as e:
        print(f"Error leyendo configuración: {e}")
    
    return get_factory_default_message()


def get_factory_default_message() -> str:
    """
    Retorna el mensaje por defecto de fábrica.
    
    Returns:
        str: Mensaje por defecto
    """
    return "Hola {nombre}.\n\nAdjunto tu boleta de compra."


def save_message(message: str) -> bool:
    """
    Guarda un mensaje personalizado como predeterminado.
    
    Args:
        message: Mensaje a guardar
    
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    try:
        create_config_dir()
        
        config = {}
        if WHATSAPP_CONFIG_FILE.exists():
            with open(WHATSAPP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        config['default_message'] = message
        
        with open(WHATSAPP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Error guardando configuración: {e}")
        return False


def reset_to_default() -> bool:
    """
    Restablece el mensaje al valor por defecto de fábrica.
    
    Returns:
        bool: True si se reinició correctamente
    """
    return save_message(get_factory_default_message())
