#!/usr/bin/env python3
"""
ProductRefreshWorker - Auto-actualización de inventario en tiempo real
Sincroniza productos automáticamente sin necesidad de actualizar la app manualmente
"""
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
import time


class ProductRefreshWorker(QThread):
    """
    Worker que verifica actualizaciones de productos en background sin bloquear UI.
    
    Implementa sincronización automática:
    - Cada 1 segundo: recarga productos locales (instantáneo)
    - Cada 5 segundos: sincroniza con servidor remoto
    - Merging strategy: remoto es fuente de verdad, local-only items se mantienen
    """
    
    refresh_ready = pyqtSignal(list)  # Emite lista actualizada de productos
    inventory_updated = pyqtSignal(dict)  # Emite stats de inventario {stock_total, valor_total}
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self._running = True
    
    def run(self):
        """Actualización continua: local cada 10s (optimizado para internet).
        
        CAMBIOS:
        - Ciclo aumentado a 10 segundos (antes 5s)
        - Reduce carga de reloads constantes
        - UI sigue siendo responsiva
        """
        local_last_check = 0
        
        while self._running:
            try:
                now = time.time()
                
                # ================================================================
                # CADA 10 SEGUNDOS: Leer productos locales (reduce consumo internet)
                # ================================================================
                if now - local_last_check >= 10.0:
                    try:
                        from utils.file_handler import cargar_productos
                        productos_locales = cargar_productos(self.username)
                        
                        if productos_locales:
                            self.refresh_ready.emit(productos_locales)
                    except:
                        pass
                    
                    local_last_check = now
                
                # ================================================================
                # CADA 5 SEGUNDOS: Sincronizar desde servidor remoto
                # ================================================================
                if now - remote_last_check >= 5.0:
                    try:
                        from utils.api_handler import obtener_productos_remoto, obtener_inventario_remoto
                        from utils.file_handler import get_effective_branch_context

                        ctx = get_effective_branch_context(self.username) or {}
                        branch_code = str(ctx.get("code", "") or "").strip().upper()
                        
                        # Obtener productos remotos
                        productos_remotos = obtener_productos_remoto(
                            self.username,
                            codigo_dispositivo=branch_code or None
                        )
                        if productos_remotos is not None:
                            self.refresh_ready.emit(productos_remotos)
                        
                        # Obtener stats de inventario
                        inventario_stats = obtener_inventario_remoto(
                            self.username,
                            codigo_dispositivo=branch_code or None
                        )
                        if inventario_stats is not None:
                            # Extraer valores totales
                            stats = {
                                'stock_total': inventario_stats.get('stock_total', 0),
                                'valor_total': inventario_stats.get('valor_total_inventario', 0),
                                'items_count': len(inventario_stats.get('inventario', []))
                            }
                            self.inventory_updated.emit(stats)
                    except:
                        pass
                    
                    remote_last_check = now
                
                # Dormir 100ms para no usar CPU
                self.msleep(100)
                
            except Exception as e:
                # Ignorar errores silenciosamente
                self.msleep(100)
    
    def stop(self):
        """Detiene el worker."""
        self._running = False


class InventoryAutoSyncWorker(QThread):
    """
    Worker que sincroniza productos desde BD remota cada 60 segundos + sube imágenes.
    
    OPTIMIZACIONES PARA REDUCIR CONSUMO INTERNET:
    - Ciclo ampliado a 60 segundos (antes 3s, antes 15s)
    - Usa SyncQueueManager para serializar procesos (una tarea a la vez)
    - Cache de productos por 30 segundos
    - Solo sube imágenes si hay cambios reales
    - Reduce requests HTTP significativamente
    
    Procesa:
    1. Obtiene productos desde la BD de internet (obtener_productos_remoto)
    2. Sincroniza cambios locales al servidor
    3. Sube imágenes automáticamente
    4. Ejecuta cada 15 segundos en background
    """
    
    sync_completed = pyqtSignal(dict)  # Emite resultado {productos, imagenes_subidas}
    sync_error = pyqtSignal(str)  # Emite mensaje de error
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self._running = True
    
    def run(self):
        """
        Ciclo cada 60 segundos (throttled para reducir consumo internet):
        1. Obtener productos (BD remota o locales)
        2. Sincronizar cambios con servidor
        3. Subir imágenes con image_path
        
        Usa SyncQueueManager para serializar en lugar de paralelo
        """
        from utils.sync_queue_manager import get_sync_queue
        
        sync_queue = get_sync_queue()
        last_sync = 0
        
        while self._running:
            try:
                now = time.time()
                
                # Cada 60 segundos: agregar tarea a la cola (NO ejecutar directamente)
                if now - last_sync >= 60.0:
                    try:
                        # Define la función que se ejecutará en la cola
                        def perform_auto_sync():
                            from utils.file_handler import cargar_productos
                            from utils.api_handler import (
                                obtener_productos_remoto,
                                subir_imagenes_productos
                            )
                            from utils.sync_manager import SyncManager
                            
                            # Obtener usuario_id para API calls
                            usuario_id = self._get_usuario_id()
                            
                            if usuario_id:
                                # 1️⃣ OBTENER PRODUCTOS (intenta remoto primero, luego local)
                                productos = obtener_productos_remoto(usuario_id)
                                
                                if not productos:
                                    # Si no hay en remoto, usar locales
                                    productos = cargar_productos(self.username)
                                
                                if productos:
                                    # 2️⃣ SINCRONIZAR CAMBIOS LOCALES CON SERVIDOR
                                    sync_result = None
                                    try:
                                        sync_manager = SyncManager(self.username)
                                        sync_result = sync_manager.sync()
                                    except:
                                        pass
                                    
                                    # 3️⃣ SUBIR IMÁGENES DE PRODUCTOS
                                    image_stats = subir_imagenes_productos(usuario_id, productos)
                                    
                                    # Emitir resultado
                                    self.sync_completed.emit({
                                        'productos_count': len(productos),
                                        'imagenes_subidas': image_stats.get('subidas', 0),
                                        'imagenes_errores': image_stats.get('errores', 0),
                                        'imagenes_pendientes': image_stats.get('pendientes', 0),
                                        'sync_status': 'OK' if sync_result else 'PENDING'
                                    })
                            
                            return {'status': 'completed'}
                        
                        # Agregar a la cola (se ejecutará cuando sea su turno)
                        sync_queue.add_sync_task(
                            'auto_sync_inventory',
                            perform_auto_sync
                        )
                    
                    except Exception as e:
                        self.sync_error.emit(f"Error agregando tarea a cola: {str(e)}")
                    
                    last_sync = now
                
                self.msleep(1000)  # Revisar cada 1 segundo, pero sincronizar cada 15s
                
            except Exception as e:
                self.sync_error.emit(f"Error en auto sync worker: {str(e)}")
                self.msleep(1000)
    
    def _get_usuario_id(self):
        """
        Obtiene el usuario_id del username.
        El usuario_id es la KEY del diccionario usuarios.
        Si username es numérico (RUC), directo.
        Si no, buscar por campo username.
        """
        try:
            # Intentar interpretar username directamente como usuario_id
            if self.username.isdigit():
                return int(self.username)
            
            # Si no, buscar en el diccionario usuarios
            from utils.file_handler import cargar_usuarios
            usuarios = cargar_usuarios() or {}
            for uid, info in usuarios.items():
                if isinstance(info, dict) and info.get('username') == self.username:
                    return int(uid)
        except:
            pass
        return None
    
    def stop(self):
        """Detiene el worker."""
        self._running = False


class PageRefreshWorker(QThread):
    """
    Worker para actualizar la página de inventario en background.
    Emite señales para cambiar el botón a loader y volver a la normalidad.
    """
    
    refresh_started = pyqtSignal()  # Emite cuando comienza
    refresh_completed = pyqtSignal(dict)  # Emite cuando termina con stats
    refresh_error = pyqtSignal(str)  # Emite si hay error
    
    def __init__(self, username):
        super().__init__()
        self.username = username
    
    def run(self):
        """Ejecuta la actualización completa en background"""
        try:
            # Emitir que comenzó
            self.refresh_started.emit()
            
            from utils.file_handler import cargar_usuarios, cargar_productos, guardar_productos
            from utils.api_handler import obtener_productos_remoto, subir_imagenes_productos
            from utils.sync_manager import SyncManager
            
            username = self.username
            
            # 1. Obtener usuario_id
            usuarios = cargar_usuarios() or {}
            usuario_id = None
            
            if username and username.isdigit():
                usuario_id = int(username)
            else:
                for uid, info in usuarios.items():
                    if isinstance(info, dict) and info.get('username') == username:
                        usuario_id = int(uid)
                        break
            
            if not usuario_id:
                self.refresh_error.emit("No se pudo obtener usuario_id")
                return
            
            stats = {
                'productos': 0,
                'imagenes_subidas': 0,
                'imagenes_errores': 0,
                'sync_ok': False
            }
            
            # 2. Obtener productos de BD remota
            productos_remotos = obtener_productos_remoto(usuario_id)
            
            if productos_remotos:
                productos = productos_remotos
            else:
                # Fallback a locales
                productos = cargar_productos(username)
            
            stats['productos'] = len(productos or [])
            
            # 3. Guardar localmente
            if productos:
                guardar_productos(username, productos)
            
            # 4. Sincronizar cambios
            try:
                sync_manager = SyncManager(username)
                sync_result = sync_manager.sync()
                stats['sync_ok'] = sync_result is not None
            except Exception as e:
                pass
            
            # 5. Subir imágenes
            if productos:
                image_stats = subir_imagenes_productos(usuario_id, productos)
                stats['imagenes_subidas'] = image_stats.get('subidas', 0)
                stats['imagenes_errores'] = image_stats.get('errores', 0)
            
            # Emitir que terminó
            self.refresh_completed.emit(stats)
        
        except Exception as e:
            import traceback
            self.refresh_error.emit(f"Error: {str(e)}")
            traceback.print_exc()
