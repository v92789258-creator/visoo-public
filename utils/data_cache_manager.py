"""
Sistema de carga perezosa y caché para datos grandes (clientes, pacientes, productos).
Evita cargar todos los JSON al inicio de la aplicación y cierra instancias innecesarias.
"""

import threading
import time
from typing import Dict, List, Any, Optional
from pathlib import Path


class DataCacheManager:
    """
    Gestor de caché con carga perezosa (lazy loading).
    
    Características:
    - Carga datos solo cuando se solicitan
    - Mantiene caché en memoria
    - Libera memoria si los datos no se usan durante cierto tiempo
    - Thread-safe para evitar condiciones de carrera
    - Permite actualizar datos y sincronizar con archivo
    
    Uso:
        cache = DataCacheManager()
        
        # Cargar clientes (carga del JSON la primera vez)
        clientes = cache.get_clientes(username)
        
        # Actualizar datos
        cache.update_clientes(username, new_data)
        
        # Liberar memoria para un usuario específico
        cache.clear_user(username)
        
        # Liberar toda la memoria de caché
        cache.clear_all()
    """
    
    def __init__(self, timeout_seconds: int = 300, import_file_handler: bool = True):
        """
        Inicializa el gestor de caché.
        
        Args:
            timeout_seconds: Tiempo en segundos sin acceso antes de liberar caché (0 = nunca)
            import_file_handler: Si es True, importa file_handler localmente (para evitar imports circulares)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}  # {username: {tipo_dato: (data, timestamp)}}
        self._lock = threading.RLock()
        self._timeout = timeout_seconds
        self._import_file_handler = import_file_handler
        self._file_handler = None
        self._stop_event = threading.Event()
        self._cleaner_thread = None
        
        # Iniciar limpiador de caché en background
        if self._timeout > 0:
            self._start_cache_cleaner()
    
    def _get_file_handler(self):
        """Importa file_handler de forma diferida."""
        if self._file_handler is None and self._import_file_handler:
            try:
                from utils import file_handler
                self._file_handler = file_handler
            except ImportError:
                pass
        return self._file_handler
    
    def _start_cache_cleaner(self):
        """Inicia thread daemon para limpiar caché expirado."""
        def cleaner():
            while not self._stop_event.wait(self._timeout):
                self._cleanup_expired()

        thread = threading.Thread(target=cleaner, daemon=True, name="VISO-DataCacheCleaner")
        self._cleaner_thread = thread
        thread.start()
    
    def _cleanup_expired(self):
        """Elimina datos del caché que han expirado."""
        if self._timeout <= 0:
            return
        
        current_time = time.time()
        with self._lock:
            expired_users = []
            for username, user_data in self._cache.items():
                expired_keys = []
                for key, (data, timestamp) in user_data.items():
                    if current_time - timestamp > self._timeout:
                        expired_keys.append(key)
                
                # Remover entradas expiradas
                for key in expired_keys:
                    del user_data[key]
                
                # Remover usuario si no tiene datos en caché
                if not user_data:
                    expired_users.append(username)
            
            for username in expired_users:
                del self._cache[username]
    
    def _update_timestamp(self, username: str, data_type: str):
        """Actualiza el timestamp de acceso para un dato."""
        if username not in self._cache:
            self._cache[username] = {}
        
        if data_type in self._cache[username]:
            data, _ = self._cache[username][data_type]
            self._cache[username][data_type] = (data, time.time())
    
    def _get_from_cache(self, username: str, data_type: str) -> Optional[Any]:
        """Obtiene datos del caché si existen."""
        with self._lock:
            if username in self._cache and data_type in self._cache[username]:
                self._update_timestamp(username, data_type)
                data, _ = self._cache[username][data_type]
                return data
        return None
    
    def _set_cache(self, username: str, data_type: str, data: Any):
        """Guarda datos en caché."""
        with self._lock:
            if username not in self._cache:
                self._cache[username] = {}
            self._cache[username][data_type] = (data, time.time())
    
    # ============ CLIENTES ============
    def get_clientes(self, username: str) -> List[Dict]:
        """
        Obtiene clientes con carga perezosa.
        Carga del JSON solo la primera vez.
        """
        cached = self._get_from_cache(username, 'clientes')
        if cached is not None:
            return cached
        
        # Cargar del archivo
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                data = file_handler.cargar_clientes(username)
                self._set_cache(username, 'clientes', data)
                return data
            except Exception as e:
                print(f"Error cargando clientes: {e}")
        
        return []
    
    def update_clientes(self, username: str, data: List[Dict]):
        """Actualiza clientes en caché y archivo."""
        self._set_cache(username, 'clientes', data)
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                file_handler.guardar_clientes(username, data)
            except Exception as e:
                print(f"Error guardando clientes: {e}")
    
    # ============ PACIENTES ============
    def get_pacientes(self, username: str) -> List[Dict]:
        """
        Obtiene pacientes con carga perezosa.
        """
        cached = self._get_from_cache(username, 'pacientes')
        if cached is not None:
            return cached
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                data = file_handler.cargar_pacientes(username)
                self._set_cache(username, 'pacientes', data)
                return data
            except Exception as e:
                print(f"Error cargando pacientes: {e}")
        
        return []
    
    def update_pacientes(self, username: str, data: List[Dict]):
        """Actualiza pacientes en caché y archivo."""
        self._set_cache(username, 'pacientes', data)
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                file_handler.guardar_pacientes(username, data)
            except Exception as e:
                print(f"Error guardando pacientes: {e}")
    
    # ============ PRODUCTOS (INVENTARIO) ============
    def get_productos(self, username: str) -> List[Dict]:
        """
        Obtiene productos/inventario con carga perezosa.
        """
        cached = self._get_from_cache(username, 'productos')
        if cached is not None:
            return cached
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                data = file_handler.cargar_productos(username)
                self._set_cache(username, 'productos', data)
                return data
            except Exception as e:
                print(f"Error cargando productos: {e}")
        
        return []
    
    def update_productos(self, username: str, data: List[Dict]):
        """Actualiza productos en caché y archivo."""
        self._set_cache(username, 'productos', data)
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                file_handler.guardar_productos(username, data)
            except Exception as e:
                print(f"Error guardando productos: {e}")
    
    # ============ OTROS DATOS ============
    def get_ventas(self, username: str) -> List[Dict]:
        """Obtiene ventas con caché."""
        cached = self._get_from_cache(username, 'ventas')
        if cached is not None:
            return cached
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                data = file_handler.cargar_ventas(username)
                self._set_cache(username, 'ventas', data)
                return data
            except Exception as e:
                print(f"Error cargando ventas: {e}")
        
        return []
    
    def update_ventas(self, username: str, data: List[Dict]):
        """Actualiza ventas en caché y archivo."""
        self._set_cache(username, 'ventas', data)
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                file_handler.guardar_ventas(username, data)
            except Exception as e:
                print(f"Error guardando ventas: {e}")
    
    def get_citas(self, username: str) -> List[Dict]:
        """Obtiene citas con caché."""
        cached = self._get_from_cache(username, 'citas')
        if cached is not None:
            return cached
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                data = file_handler.cargar_citas(username)
                self._set_cache(username, 'citas', data)
                return data
            except Exception as e:
                print(f"Error cargando citas: {e}")
        
        return []
    
    def update_citas(self, username: str, data: List[Dict]):
        """Actualiza citas en caché y archivo."""
        self._set_cache(username, 'citas', data)
        
        file_handler = self._get_file_handler()
        if file_handler:
            try:
                file_handler.guardar_citas(username, data)
            except Exception as e:
                print(f"Error guardando citas: {e}")
    
    # ============ CONTROL DE CACHÉ ============
    def clear_user(self, username: str):
        """Libera toda la caché de un usuario específico."""
        with self._lock:
            if username in self._cache:
                del self._cache[username]
    
    def clear_data_type(self, username: str, data_type: str):
        """Libera caché de un tipo de dato específico para un usuario."""
        with self._lock:
            if username in self._cache and data_type in self._cache[username]:
                del self._cache[username][data_type]
    
    def clear_all(self):
        """Libera toda la caché."""
        with self._lock:
            self._cache.clear()
    
    def shutdown(self):
        """Detiene el limpiador en background y libera caché."""
        try:
            self._stop_event.set()
        except Exception:
            pass
        self.clear_all()

    def get_cache_info(self) -> Dict[str, Any]:
        """Devuelve información sobre el estado actual del caché."""
        with self._lock:
            info = {
                'total_users': len(self._cache),
                'users': {}
            }
            for username, user_data in self._cache.items():
                info['users'][username] = list(user_data.keys())
            return info
    
    def preload(self, username: str, data_types: List[str] = None):
        """
        Precarga datos en el caché para optimizar acceso futuro.
        
        Args:
            username: Usuario para el que cargar datos
            data_types: Lista de tipos de datos a precargar.
                       Si es None, precarga los principales: clientes, pacientes, productos
        """
        if data_types is None:
            data_types = ['clientes', 'pacientes', 'productos']
        
        for data_type in data_types:
            if data_type == 'clientes':
                self.get_clientes(username)
            elif data_type == 'pacientes':
                self.get_pacientes(username)
            elif data_type == 'productos':
                self.get_productos(username)
            elif data_type == 'ventas':
                self.get_ventas(username)
            elif data_type == 'citas':
                self.get_citas(username)


# Instancia global del gestor de caché (singleton)
_global_cache = None

def get_global_cache() -> DataCacheManager:
    """Obtiene o crea la instancia global del gestor de caché."""
    global _global_cache
    if _global_cache is None:
        # Timeout de 5 minutos sin acceso para liberar memoria
        _global_cache = DataCacheManager(timeout_seconds=300)
    return _global_cache


def clear_global_cache():
    """Limpia toda la caché global."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear_all()


def shutdown_global_cache():
    """Detiene el caché global y su hilo limpiador."""
    global _global_cache
    if _global_cache is not None:
        try:
            _global_cache.shutdown()
        except Exception:
            pass
        _global_cache = None
