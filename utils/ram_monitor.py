"""
Monitor de uso de RAM y caché para VISO.
Muestra estadísticas en tiempo real del consumo de memoria.

Nota: Requiere psutil. Instalar con: pip install psutil
"""

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Advertencia: psutil no está instalado. El monitoreo de RAM estará deshabilitado.")
    print("Instala con: pip install psutil")

import os
from PyQt5.QtCore import QTimer, pyqtSignal, QObject


class RAMMonitor(QObject):
    """
    Monitor de RAM que rastrea el uso de memoria de la aplicación.
    
    Señales:
    - ram_updated: (used_mb, total_mb, percent)
    - cache_updated: (cache_info)
    
    Uso:
        monitor = RAMMonitor()
        monitor.ram_updated.connect(on_ram_update)
        monitor.start()
    """
    
    ram_updated = pyqtSignal(float, float, float)  # used_mb, total_mb, percent
    cache_updated = pyqtSignal(dict)  # cache_info
    
    def __init__(self, update_interval_ms=2000):
        super().__init__()
        self.update_interval = update_interval_ms
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        
        if HAS_PSUTIL:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = None
    
    def start(self):
        """Inicia el monitoreo de RAM."""
        if not HAS_PSUTIL:
            print("Advertencia: psutil no disponible, monitoreo de RAM deshabilitado")
            return
        self.timer.start(self.update_interval)
    
    def stop(self):
        """Detiene el monitoreo de RAM."""
        self.timer.stop()
    
    def _update(self):
        """Actualiza las métricas de RAM."""
        if not HAS_PSUTIL or not self.process:
            return
        
        try:
            # Información de memoria del proceso
            memory_info = self.process.memory_info()
            rss_mb = memory_info.rss / 1024 / 1024  # RAM utilizado por el proceso
            
            # Información de memoria del sistema
            virtual_memory = psutil.virtual_memory()
            total_mb = virtual_memory.total / 1024 / 1024
            available_mb = virtual_memory.available / 1024 / 1024
            percent = virtual_memory.percent
            
            self.ram_updated.emit(rss_mb, total_mb, percent)
            
        except Exception as e:
            print(f"Error monitoreando RAM: {e}")
    
    def get_current_usage(self):
        """Retorna el uso actual de RAM en MB."""
        if not HAS_PSUTIL or not self.process:
            return 0.0
        
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / 1024 / 1024
        except Exception:
            return 0.0


class CacheMonitor:
    """
    Monitor del estado del caché de datos.
    Útil para debugging y monitoreo de consumo de memoria por caché.
    
    Uso:
        monitor = CacheMonitor(cache_instance)
        info = monitor.get_cache_info()
        print(info)
    """
    
    def __init__(self, cache_manager):
        self.cache = cache_manager
    
    def get_cache_info(self):
        """Obtiene información detallada del caché."""
        try:
            info = self.cache.get_cache_info()
            
            # Estimar tamaño en memoria (aproximado)
            estimated_size = self._estimate_cache_size(info)
            
            return {
                'total_users': info['total_users'],
                'users': info['users'],
                'estimated_size_mb': estimated_size,
                'detailed': self._get_detailed_info(info)
            }
        except Exception as e:
            print(f"Error obteniendo info de caché: {e}")
            return {}
    
    def _estimate_cache_size(self, cache_info):
        """Estima el tamaño del caché en MB."""
        try:
            total_bytes = 0
            
            # Cada lista de 100 items ≈ 50KB (aproximación)
            for username, data_types in cache_info.get('users', {}).items():
                for data_type in data_types:
                    total_bytes += 50 * 1024
            
            return total_bytes / 1024 / 1024
        except Exception:
            return 0.0
    
    def _get_detailed_info(self, cache_info):
        """Retorna información detallada por usuario y tipo de dato."""
        detailed = {}
        for username, data_types in cache_info.get('users', {}).items():
            detailed[username] = {
                'cached_types': data_types,
                'count': len(data_types),
                'estimated_size_kb': len(data_types) * 50
            }
        return detailed
    
    def clear_specific(self, username, data_type):
        """Limpia un tipo de dato específico para un usuario."""
        try:
            self.cache.clear_data_type(username, data_type)
            return True
        except Exception as e:
            print(f"Error limpiando caché: {e}")
            return False
    
    def clear_user(self, username):
        """Limpia todo el caché de un usuario."""
        try:
            self.cache.clear_user(username)
            return True
        except Exception as e:
            print(f"Error limpiando caché de usuario: {e}")
            return False
    
    def print_report(self):
        """Imprime un reporte del estado actual del caché."""
        info = self.get_cache_info()
        
        print("\n" + "="*50)
        print("📊 REPORTE DE CACHÉ")
        print("="*50)
        print(f"Usuarios en caché: {info.get('total_users', 0)}")
        print(f"Tamaño estimado: {info.get('estimated_size_mb', 0):.2f} MB")
        
        detailed = info.get('detailed', {})
        if detailed:
            print("\nDetalle por usuario:")
            for username, details in detailed.items():
                print(f"\n  👤 {username}:")
                print(f"    - Tipos en caché: {', '.join(details['cached_types'])}")
                print(f"    - Tamaño estimado: {details['estimated_size_kb']:.1f} KB")
        
        print("\n" + "="*50 + "\n")


def get_memory_usage_report():
    """
    Función auxiliar que retorna un reporte del uso de memoria.
    
    Retorna:
        dict: {
            'process_mb': RAM usada por el proceso,
            'system_mb': RAM total disponible,
            'percent': % del sistema siendo usado,
            'available_mb': RAM disponible en el sistema
        }
    """
    if not HAS_PSUTIL:
        return {
            'process_mb': 0.0,
            'system_mb': 0.0,
            'percent': 0.0,
            'available_mb': 0.0,
            'error': 'psutil no instalado'
        }
    
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        virtual_memory = psutil.virtual_memory()
        
        return {
            'process_mb': memory_info.rss / 1024 / 1024,
            'system_mb': virtual_memory.total / 1024 / 1024,
            'percent': virtual_memory.percent,
            'available_mb': virtual_memory.available / 1024 / 1024
        }
    except Exception as e:
        print(f"Error obteniendo reporte de memoria: {e}")
        return {}
