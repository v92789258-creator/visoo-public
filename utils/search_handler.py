# utils/search_handler.py

"""Manejadores de búsqueda: búsqueda web y búsqueda local en datos del usuario.

Exporta:
- search_google(query) -> (bool, results_or_error)
- buscar_general_local(username, termino) -> (True, {'pacientes': [...], 'productos': [...]})
"""

try:
    from googlesearch import search as google_search
except Exception:
    google_search = None


def search_google(query):
    """Realiza una búsqueda en Google y devuelve una lista de URLs.

    Si la librería no está disponible devuelve (False, mensaje).
    """
    if google_search is None:
        return False, "La librería de búsqueda web no está instalada."
    try:
        results = list(google_search(query, num_results=5, lang='es'))
        return True, results
    except Exception as e:
        return False, f"Ocurrió un error al buscar: {e}"


def buscar_general_local(username, termino):
    """
    Busca localmente en archivos del usuario: pacientes y productos.
    
    OPTIMIZACIÓN: Usa fast_loader.buscar_productos_rapido() y buscar_pacientes_rapido()
    para búsquedas ultra-rápidas (<10ms para 5000+ items).
    
    Args:
        username: nombre de usuario para localizar archivos.
        termino: cadena de búsqueda.

    Returns:
        (True, {'pacientes': [...], 'productos': [...]})
    """
    termino_norm = (termino or '').strip().lower()
    if not termino_norm:
        return True, {'pacientes': [], 'productos': []}

    try:
        # Intentar usar versión rápida
        from utils.fast_loader import buscar_pacientes_rapido, buscar_productos_rapido
        use_fast_loader = True
    except ImportError:
        use_fast_loader = False
    
    if use_fast_loader:
        try:
            # Búsqueda ultra-rápida con fast_loader
            if username is not None:
                pacientes = buscar_pacientes_rapido(username, termino_norm)
                productos = buscar_productos_rapido(username, termino_norm)
            else:
                pacientes = []
                productos = []
            
            pacientes_encontrados = []
            for p in pacientes:
                pacientes_encontrados.append({'dni': p.get('dni'), 'nombre': p.get('nombre')})
            
            productos_encontrados = []
            for prod in productos:
                productos_encontrados.append({'nombre': prod.get('nombre'), 'marca': prod.get('marca'), 'meta': prod})
            
            return True, {'pacientes': pacientes_encontrados, 'productos': productos_encontrados}
        except Exception as e:
            print(f"[WARNING] fast_loader búsqueda falló, usando método lento: {e}")
            use_fast_loader = False
    
    # Fallback a método lento si fast_loader no disponible
    try:
        from utils.file_handler import cargar_pacientes, cargar_productos
    except Exception:
        return True, {'pacientes': [], 'productos': []}

    pacientes = cargar_pacientes(username) if username is not None else []
    productos = cargar_productos(username) if username is not None else []

    pacientes_encontrados = []
    for p in pacientes:
        nombre = str(p.get('nombre', '')).lower()
        dni = str(p.get('dni', '')).lower()
        if termino_norm in nombre or termino_norm in dni:
            pacientes_encontrados.append({'dni': p.get('dni'), 'nombre': p.get('nombre')})

    productos_encontrados = []
    for prod in productos:
        nombre = str(prod.get('nombre', '')).lower()
        marca = str(prod.get('marca', '')).lower()
        if termino_norm in nombre or termino_norm in marca:
            productos_encontrados.append({'nombre': prod.get('nombre'), 'marca': prod.get('marca'), 'meta': prod})

    return True, {'pacientes': pacientes_encontrados, 'productos': productos_encontrados}