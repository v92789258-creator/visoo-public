"""
SyncQueueManager - Cola centralizada para sincronizaciones
Procesa un trabajo a la vez para evitar lag de múltiples procesos simultáneos
"""

from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, QThreadPool
from queue import Queue, Empty
import time
from threading import Lock, Event

class SyncQueueWorker(QRunnable):
    """Worker que procesa la cola de sincronizaciones"""
    
    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.running = Event()
        self.running.set()
        self.lock = Lock()
        
        # Signals (usamos un QObject para emitirlas)
        self.signals_object = QObject()
        self.signals_object.task_started = pyqtSignal(str)
        self.signals_object.task_completed = pyqtSignal(str, dict)
        self.signals_object.task_error = pyqtSignal(str, str)
        
    def add_task(self, task_name, task_func, *args, **kwargs):
        """Agrega una tarea a la cola (FIFO)"""
        self.queue.put({
            'name': task_name,
            'func': task_func,
            'args': args,
            'kwargs': kwargs,
            'retry_count': 0,
            'max_retries': 2
        })
    
    def run(self):
        """Procesa tareas de la cola una por una"""
        print("[QUEUE] Worker iniciado - procesando tareas...")
        
        while self.running.is_set():
            try:
                # Espera 1s antes de intentar obtener tarea (throttling)
                task = self.queue.get(timeout=1.0)
                
                task_name = task['name']
                print(f"[QUEUE] Procesando: {task_name}")
                
                try:
                    # Ejecuta la tarea
                    result = task['func'](*task['args'], **task['kwargs'])
                    print(f"[QUEUE] {task_name} completado")
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[QUEUE] Error en {task_name}: {error_msg}")
                    
                    # Reintentos
                    if task['retry_count'] < task['max_retries']:
                        task['retry_count'] += 1
                        print(f"[QUEUE] Reintentando {task_name} ({task['retry_count']}/{task['max_retries']})")
                        self.queue.put(task)
                    else:
                        print(f"[QUEUE] Error final en {task_name}")
                        
            except Empty:
                # No hay tareas en la cola
                pass
            except Exception as e:
                print(f"[QUEUE] Error en worker: {e}")
                time.sleep(1)
    
    def stop(self):
        """Detiene el worker"""
        self.running.clear()
        print("[QUEUE] Worker detenido")


class SyncQueueManager:
    """Gestor centralizado de cola de sincronizaciones"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el gestor"""
        if self._initialized:
            return
        
        self.worker = SyncQueueWorker()
        
        # Usar QThreadPool para ejecutar el worker
        from PyQt5.QtCore import QThreadPool
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(1)  # Solo 1 thread para procesar secuencial
        
        # Inicia el worker en el thread pool
        self.thread_pool.start(self.worker)
        self._initialized = True
        
        print("[QUEUE] SyncQueueManager inicializado (procesando en background)")
    
    def add_sync_task(self, task_name, task_func, *args, **kwargs):
        """
        Agrega una tarea de sincronización a la cola
        
        Args:
            task_name: Nombre descriptivo (ej: 'sync_productos', 'upload_images')
            task_func: Función a ejecutar
            *args, **kwargs: Argumentos para la función
        """
        self.worker.add_task(task_name, task_func, *args, **kwargs)
        print(f"[QUEUE] Tarea '{task_name}' agregada a la cola (pendientes: ~{self.worker.queue.qsize()})")
    
    def stop(self):
        """Detiene el gestor"""
        self.worker.stop()
        self.thread_pool.waitForDone()
        print("[QUEUE] SyncQueueManager detenido")


# Función de utilidad para obtener instancia global
def get_sync_queue():
    """Obtiene la instancia global del SyncQueueManager"""
    return SyncQueueManager()
