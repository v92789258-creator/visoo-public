import os
import json

VISO_DATA_DIR = os.path.join("VISO", "data")

def ensure_data_directory():
    """Asegura que el directorio de datos existe"""
    os.makedirs(VISO_DATA_DIR, exist_ok=True)

def load_json_data(filename, default_data=None):
    """Carga datos de un archivo JSON, creándolo si no existe"""
    file_path = os.path.join(VISO_DATA_DIR, filename)
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            if default_data is not None:
                save_json_data(filename, default_data)
                return default_data
            return []
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return default_data if default_data is not None else []

def save_json_data(filename, data):
    """Guarda datos en un archivo JSON"""
    ensure_data_directory()
    file_path = os.path.join(VISO_DATA_DIR, filename)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False

# Funciones específicas para materiales
def load_materials():
    # No crear datos por defecto - dejar que el usuario configure
    return load_json_data("materials.json", None)

def save_materials(materials):
    return save_json_data("materials.json", materials)

# Funciones específicas para tallas
def load_sizes():
    # No crear datos por defecto - dejar que el usuario configure
    return load_json_data("sizes.json", None)

def save_sizes(sizes):
    return save_json_data("sizes.json", sizes)

# Funciones específicas para tipos de lente
def load_lens_types():
    # No crear datos por defecto - dejar que el usuario configure
    return load_json_data("lens_types.json", None)

def save_lens_types(lens_types):
    return save_json_data("lens_types.json", lens_types)