"""
helpers_manager.py - Gestión de Ayudantes con Permisos Configurables
"""

import json
import os
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from utils.file_handler import VISO_DIR, cargar_usuarios, guardar_usuarios

# ============================================================
# CONSTANTES - PERMISOS DISPONIBLES (GRANULARES)
# ============================================================

PERMISOS_DISPONIBLES = {
    'inventario': {
        'label': 'Inventario',
        'modulos': ['inventory_page'],
        'acciones': {
            'ver': {'label': 'Ver inventario', 'desc': 'Ver productos y stock'},
            'crear': {'label': 'Crear productos', 'desc': 'Agregar nuevos productos'},
            'editar': {'label': 'Editar productos', 'desc': 'Modificar información de productos'},
            'eliminar': {'label': 'Eliminar productos', 'desc': 'Eliminar productos del inventario'},
        }
    },
    'ventas': {
        'label': 'Ventas',
        'modulos': ['sales_page', 'registro_ventas_page'],
        'acciones': {
            'ver': {'label': 'Ver ventas', 'desc': 'Ver historial y reportes de ventas'},
            'ver_deudas': {'label': 'Ver deudas', 'desc': 'Ver deudas pendientes de clientes'},
            'registrar': {'label': 'Registrar ventas', 'desc': 'Crear nuevas ventas'},
            'editar': {'label': 'Editar ventas', 'desc': 'Modificar ventas existentes'},
            'editar_deudas': {'label': 'Editar deudas', 'desc': 'Registrar pagos o cancelaciones de deudas'},
            'eliminar': {'label': 'Eliminar ventas', 'desc': 'Eliminar registros de ventas'},
        }
    },
    'graduaciones': {
        'label': 'Graduaciones',
        'modulos': ['patients_page', 'appointments_page'],
        'acciones': {
            'ver': {'label': 'Ver graduaciones', 'desc': 'Ver graduaciones de pacientes'},
            'crear': {'label': 'Crear graduaciones', 'desc': 'Crear nuevas graduaciones'},
            'editar': {'label': 'Editar graduaciones', 'desc': 'Modificar graduaciones existentes'},
        }
    },
    'pacientes': {
        'label': 'Pacientes',
        'modulos': ['patients_page', 'create_patient_page'],
        'acciones': {
            'ver': {'label': 'Ver pacientes', 'desc': 'Ver lista y detalles de pacientes'},
            'crear': {'label': 'Crear pacientes', 'desc': 'Registrar nuevos pacientes'},
            'editar': {'label': 'Editar pacientes', 'desc': 'Modificar datos de pacientes'},
            'eliminar': {'label': 'Eliminar pacientes', 'desc': 'Eliminar pacientes del sistema'},
        }
    },
    'clientes': {
        'label': 'Clientes',
        'modulos': ['customers_page', 'customer_page'],
        'acciones': {
            'ver': {'label': 'Ver clientes', 'desc': 'Ver lista y detalles de clientes'},
            'crear': {'label': 'Crear clientes', 'desc': 'Registrar nuevos clientes'},
            'editar': {'label': 'Editar clientes', 'desc': 'Modificar datos de clientes'},
            'eliminar': {'label': 'Eliminar clientes', 'desc': 'Eliminar clientes del sistema'},
        }
    },
    'reportes': {
        'label': 'Reportes',
        'modulos': ['reportes_page'],
        'acciones': {
            'ver': {'label': 'Ver reportes', 'desc': 'Ver reportes y estadísticas'},
            'descargar': {'label': 'Descargar reportes', 'desc': 'Exportar reportes a archivo'},
        }
    },
    'configuracion': {
        'label': 'Configuración',
        'modulos': ['config_page'],
        'acciones': {
            'ver': {'label': 'Ver configuración', 'desc': 'Ver configuraciones del sistema'},
            'editar': {'label': 'Editar configuración', 'desc': 'Modificar configuraciones'},
        }
    }
}

# ============================================================
# RUTAS
# ============================================================

HELPERS_FILE = VISO_DIR / ".helpers.json"


# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def hash_password(password: str) -> str:
    """Hashear contraseña con salt."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verificar contraseña contra hash."""
    try:
        salt, hash_hex = hashed.split('$')
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hex() == hash_hex
    except:
        return False


# ============================================================
# FUNCIONES PRINCIPALES DE GESTIÓN DE AYUDANTES
# ============================================================

def cargar_ayudantes(username: str) -> list:
    """
    Carga los ayudantes de un usuario (jefe).
    Retorna lista de diccionarios con información de ayudantes.
    """
    try:
        # Crear directorio si no existe
        os.makedirs(VISO_DIR, exist_ok=True)
        
        if HELPERS_FILE.exists():
            with open(HELPERS_FILE, 'r', encoding='utf-8') as f:
                all_helpers = json.load(f)
                # Filtrar solo los ayudantes del usuario actual (jefe)
                return all_helpers.get(username, [])
    except (IOError, json.JSONDecodeError):
        pass
    return []


def guardar_ayudantes(username: str, ayudantes: list) -> bool:
    """
    Guarda la lista de ayudantes para un usuario (jefe).
    """
    try:
        os.makedirs(VISO_DIR, exist_ok=True)
        
        # Cargar todos los ayudantes
        all_helpers = {}
        if HELPERS_FILE.exists():
            with open(HELPERS_FILE, 'r', encoding='utf-8') as f:
                all_helpers = json.load(f)
        
        # Actualizar ayudantes del usuario actual
        all_helpers[username] = ayudantes
        
        # Guardar
        with open(HELPERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_helpers, f, indent=4, ensure_ascii=False)

        # Disparar sync cloud para dataset "ayudantes"
        try:
            from utils.sync_manager import get_sync_manager
            sync_mgr = get_sync_manager()
            sync_mgr.queue_change(
                usuario_id=str(username),
                tipo_dato='ayudantes',
                operacion='SYNC_ALL',
                registro_id='bulk',
                contenido={'ayudantes': ayudantes if isinstance(ayudantes, list) else []}
            )
            import threading
            threading.Thread(target=lambda: sync_mgr.sync_now(str(username)), daemon=True).start()
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"Error al guardar ayudantes: {e}")
        return False


def crear_ayudante(
    username_jefe: str,
    nombre_ayudante: str,
    usuario_ayudante: str,
    password_ayudante: str,
    permisos: dict,
    contacto_ayudante: str = "",
    activo: bool = True
) -> dict:
    """
    Crea un nuevo ayudante para un jefe.
    
    Args:
        username_jefe: Usuario del jefe
        nombre_ayudante: Nombre completo del ayudante
        usuario_ayudante: Usuario (login) del ayudante
        password_ayudante: Contraseña del ayudante
        permisos: Dict con permisos granulares
                 Formato: {'inventario': ['ver', 'crear', 'editar'], 'ventas': [...]}
        activo: Si el ayudante está activo
    
    Returns:
        Dict con información del ayudante creado o None si hay error
    """
    try:
        # Validar que el usuario del ayudante no exista en usuarios globales
        usuarios_globales = cargar_usuarios() or {}
        if usuario_ayudante in usuarios_globales:
            return {'error': 'El usuario ya existe en el sistema'}
        
        # Cargar ayudantes actuales
        ayudantes = cargar_ayudantes(username_jefe)
        
        # Verificar que el usuario del ayudante sea único en los ayudantes del jefe
        if any(a['usuario'] == usuario_ayudante for a in ayudantes):
            return {'error': 'Este usuario ya existe como ayudante'}
        
        # Validar y normalizar permisos
        permisos_validos = _normalizar_permisos(permisos)
        
        # Crear nuevo ayudante
        nuevo_ayudante = {
            'id': secrets.token_hex(8),  # ID único
            'nombre': nombre_ayudante,
            'usuario': usuario_ayudante,
            'contacto': contacto_ayudante.strip() if isinstance(contacto_ayudante, str) else "",
            'password_hash': hash_password(password_ayudante),
            'permisos': permisos_validos,  # Formato granular
            'activo': activo,
            'fecha_creacion': datetime.now().isoformat(),
            'fecha_ultima_conexion': None,
            'notas': ''
        }
        
        # Agregar a la lista
        ayudantes.append(nuevo_ayudante)
        
        # Guardar
        if guardar_ayudantes(username_jefe, ayudantes):
            # Retornar sin el hash de contraseña
            resultado = nuevo_ayudante.copy()
            del resultado['password_hash']
            return resultado
        else:
            return {'error': 'Error al guardar el ayudante'}
    
    except Exception as e:
        return {'error': f'Error al crear ayudante: {str(e)}'}


def editar_ayudante(
    username_jefe: str,
    id_ayudante: str,
    datos_actualizacion: dict
) -> dict:
    """
    Edita un ayudante existente.
    
    Args:
        username_jefe: Usuario del jefe
        id_ayudante: ID del ayudante
        datos_actualizacion: Dict con campos a actualizar
    
    Returns:
        Dict con información actualizada o error
    """
    try:
        ayudantes = cargar_ayudantes(username_jefe)
        
        # Buscar el ayudante
        ayudante = None
        for i, a in enumerate(ayudantes):
            if a['id'] == id_ayudante:
                ayudante = a
                idx = i
                break
        
        if not ayudante:
            return {'error': 'Ayudante no encontrado'}
        
        # Actualizar campos permitidos
        campos_permitidos = ['nombre', 'contacto', 'permisos', 'activo', 'notas']
        
        for campo, valor in datos_actualizacion.items():
            if campo in campos_permitidos:
                if campo == 'password':  # Si se intenta cambiar contraseña
                    ayudante['password_hash'] = hash_password(valor)
                else:
                    ayudante[campo] = valor
        
        # Actualizar fecha de modificación
        ayudante['fecha_ultima_modificacion'] = datetime.now().isoformat()
        
        # Guardar
        if guardar_ayudantes(username_jefe, ayudantes):
            resultado = ayudante.copy()
            if 'password_hash' in resultado:
                del resultado['password_hash']
            return resultado
        else:
            return {'error': 'Error al guardar cambios'}
    
    except Exception as e:
        return {'error': f'Error al editar ayudante: {str(e)}'}


def eliminar_ayudante(username_jefe: str, id_ayudante: str) -> dict:
    """
    Elimina un ayudante.
    """
    try:
        ayudantes = cargar_ayudantes(username_jefe)
        
        # Filtrar el ayudante a eliminar
        ayudantes_filtrados = [a for a in ayudantes if a['id'] != id_ayudante]
        
        if len(ayudantes_filtrados) == len(ayudantes):
            return {'error': 'Ayudante no encontrado'}
        
        # Guardar
        if guardar_ayudantes(username_jefe, ayudantes_filtrados):
            return {'success': 'Ayudante eliminado correctamente'}
        else:
            return {'error': 'Error al eliminar ayudante'}
    
    except Exception as e:
        return {'error': f'Error al eliminar ayudante: {str(e)}'}


def obtener_ayudante_por_usuario(username_jefe: str, usuario_ayudante: str):
    """
    Obtiene información de un ayudante por su usuario.
    """
    ayudantes = cargar_ayudantes(username_jefe)
    for ayudante in ayudantes:
        if ayudante['usuario'] == usuario_ayudante:
            return ayudante
    return None


def _normalizar_permisos(permisos: dict) -> dict:
    """
    Normaliza permisos al formato granular.
    
    Convierte permisos viejos (binarios) o nuevos al formato estándar:
    {'inventario': ['ver', 'crear', 'editar'], 'ventas': [...]}
    """
    if not permisos:
        return {}
    
    permisos_normalizados = {}
    
    for permiso, valor in permisos.items():
        if permiso not in PERMISOS_DISPONIBLES:
            continue
        
        # Si es una lista (formato nuevo)
        if isinstance(valor, list):
            # Validar que todas las acciones existan
            acciones_validas = [a for a in valor 
                              if a in PERMISOS_DISPONIBLES[permiso].get('acciones', {})]
            if acciones_validas:
                permisos_normalizados[permiso] = acciones_validas
        # Si es booleano (formato viejo), convertir a todas las acciones si es True
        elif isinstance(valor, bool) and valor:
            acciones = list(PERMISOS_DISPONIBLES[permiso].get('acciones', {}).keys())
            if acciones:
                permisos_normalizados[permiso] = acciones
    
    return permisos_normalizados


def tiene_accion_permitida(username_jefe: str, usuario_ayudante: str, 
                           seccion: str, accion: str) -> bool:
    """
    Verifica si un ayudante tiene una acción específica en una sección.
    
    Args:
        username_jefe: Usuario del jefe
        usuario_ayudante: Usuario del ayudante
        seccion: Sección del permiso (e.g., 'ventas', 'inventario')
        accion: Acción específica (e.g., 'registrar', 'ver', 'editar')
    
    Returns:
        True si el ayudante tiene la acción permitida
    """
    ayudante = obtener_ayudante_por_usuario(username_jefe, usuario_ayudante)
    
    if not ayudante or not ayudante.get('activo', False):
        return False
    
    # Obtener las acciones permitidas para esta sección
    acciones_permitidas = ayudante.get('permisos', {}).get(seccion, [])
    
    # Si es una lista (formato nuevo), verificar si la acción está en la lista
    if isinstance(acciones_permitidas, list):
        return accion in acciones_permitidas
    
    # Si es boolean (formato viejo compatible), acepta cualquier acción
    return bool(acciones_permitidas)


def verificar_permisos_ayudante(username_jefe: str, usuario_ayudante: str, permiso: str) -> bool:
    """
    Verifica si un ayudante tiene un permiso específico (compatibilidad hacia atrás).
    Ahora retorna True si tiene al menos una acción en esa sección.
    """
    ayudante = obtener_ayudante_por_usuario(username_jefe, usuario_ayudante)
    
    if not ayudante:
        return False
    
    if not ayudante.get('activo', False):
        return False
    
    # Verificar que el permiso tenga al menos una acción permitida
    acciones = ayudante.get('permisos', {}).get(permiso, [])
    return bool(acciones) and isinstance(acciones, list) and len(acciones) > 0


def obtener_modulos_permitidos(username_jefe: str, usuario_ayudante: str) -> list:
    """
    Obtiene la lista de módulos a los que tiene acceso un ayudante.
    
    LÓGICA: El ayudante puede ACCEDER a la página si tiene CUALQUIER acción,
    pero dentro de la página se verifica si tiene "ver" para cargar datos.
    
    Esto permite: crear/editar sin poder ver datos existentes.
    """
    ayudante = obtener_ayudante_por_usuario(username_jefe, usuario_ayudante)
    
    if not ayudante or not ayudante.get('activo', False):
        return []
    
    modulos = []
    permisos = ayudante.get('permisos', {})
    
    # Iterar sobre los permisos del ayudante
    for seccion, acciones in permisos.items():
        if seccion in PERMISOS_DISPONIBLES:
            # Si tiene al menos una acción en esa sección, agregar sus módulos
            # Esto permite acceder a la página, aunque sea solo para crear/editar
            if isinstance(acciones, list) and len(acciones) > 0:
                modulos.extend(PERMISOS_DISPONIBLES[seccion]['modulos'])
            elif isinstance(acciones, bool) and acciones:  # Compatibilidad hacia atrás
                modulos.extend(PERMISOS_DISPONIBLES[seccion]['modulos'])
    
    return list(set(modulos))  # Remover duplicados


def puede_ver_seccion(username_jefe: str, usuario_ayudante: str, seccion: str) -> bool:
    """
    Verifica si un ayudante tiene permiso "ver" en una sección específica.
    Esto se usa para determinar si cargar/mostrar datos en una página.
    
    Args:
        username_jefe: Usuario del jefe
        usuario_ayudante: Usuario del ayudante
        seccion: Sección a verificar (inventario, ventas, etc.)
    
    Returns:
        True si puede ver la sección, False si no
    """
    return tiene_accion_permitida(username_jefe, usuario_ayudante, seccion, 'ver')


def registrar_conexion_ayudante(username_jefe: str, usuario_ayudante: str):
    """
    Registra la última conexión de un ayudante.
    """
    try:
        ayudantes = cargar_ayudantes(username_jefe)
        
        for ayudante in ayudantes:
            if ayudante['usuario'] == usuario_ayudante:
                ayudante['fecha_ultima_conexion'] = datetime.now().isoformat()
                guardar_ayudantes(username_jefe, ayudantes)
                return True
        
        return False
    except:
        return False
