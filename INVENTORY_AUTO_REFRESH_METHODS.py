"""
Métodos para agregar a InventoryPage para auto-refresh de productos

Este módulo contiene los métodos que se deben agregar a la clase InventoryPage
para implementar sincronización automática de inventario sin necesidad de 
actualizar la app manualmente.

Copiar estos métodos a InventoryPage en gui/main_window_pages/inventory_page.py

NOTA: Este es un archivo de referencia/documentación. Los métodos reales 
ya están implementados en inventory_page.py
"""

from PyQt5 import QtWidgets


def _init_refresh_workers(self):
    """
    Inicializa los workers de refresh automático.
    
    Llama desde __init__ del InventoryPage después de setup_ui()
    """
    if not self.username:
        return
    
    try:
        from gui.workers.product_refresh_worker import ProductRefreshWorker, InventoryAutoSyncWorker
        
        # Worker para actualizar lista de productos
        self.product_refresh_worker = ProductRefreshWorker(self.username)
        self.product_refresh_worker.refresh_ready.connect(self._on_products_refreshed)
        self.product_refresh_worker.inventory_updated.connect(self._on_inventory_stats_updated)
        self.product_refresh_worker.start()
        
        print(f"[INFO] ProductRefreshWorker iniciado para {self.username}")
        
        # Worker para sincronización automática de cambios
        self.inventory_sync_worker = InventoryAutoSyncWorker(self.username)
        self.inventory_sync_worker.sync_completed.connect(self._on_auto_sync_completed)
        self.inventory_sync_worker.sync_error.connect(self._on_auto_sync_error)
        self.inventory_sync_worker.start()
        
        print(f"[INFO] InventoryAutoSyncWorker iniciado para {self.username}")
        
    except Exception as e:
        print(f"[ERROR] Error iniciando refresh workers: {e}")


def _on_products_refreshed(self, productos_remotos):
    """
    Se ejecuta cuando se reciben productos actualizados.
    
    Implementa MERGE strategy:
    1. Productos remotos son fuente de verdad
    2. Productos locales que no existen en remoto se mantienen
    3. Guarda merged localmente para persistencia
    """
    try:
        if productos_remotos is None:
            return
        
        # ========================================================================
        # PASO 1: Cargar productos locales
        # ========================================================================
        from utils.file_handler import cargar_productos, guardar_productos
        
        productos_locales = cargar_productos(self.username)
        
        # ========================================================================
        # PASO 2: MERGE STRATEGY - Combinar remotos + locales sin perder datos
        # ========================================================================
        productos_merged = []
        
        # PASO 2A: Agregar TODOS los remotos (fuente de verdad)
        productos_merged.extend(productos_remotos)
        
        # PASO 2B: Agregar productos locales que NO existen en remoto
        codigos_remotos = {p.get('codigo') for p in productos_remotos if p.get('codigo')}
        for producto_local in productos_locales:
            if producto_local.get('codigo') not in codigos_remotos:
                productos_merged.append(producto_local)
        
        # ========================================================================
        # PASO 3: Persistencia - Guardar merged localmente
        # ========================================================================
        guardar_productos(self.username, productos_merged)
        self.all_productos = productos_merged
        
        # ========================================================================
        # PASO 4: Actualizar UI - Refrescar tabla sin perder focus
        # ========================================================================
        self._refresh_table_with_merge(productos_merged)
        
    except Exception as e:
        print(f"[ERROR] Error en _on_products_refreshed: {e}")


def _refresh_table_with_merge(self, productos):
    """
    Actualiza la tabla de productos sin perder el focus o scroll position.
    
    Solo actualiza si hay cambios reales (no constantemente).
    """
    try:
        if not hasattr(self, 'products_table'):
            return
        
        # Guardar estado actual
        current_scroll = self.products_table.verticalScrollBar().value() if hasattr(self, 'products_table') else 0
        
        # Limpiar y recargar
        self.products_table.setRowCount(0)
        
        for producto in productos:
            row = self.products_table.rowCount()
            self.products_table.insertRow(row)
            
            # Rellenar datos
            self.products_table.setItem(row, 0, QtWidgets.QTableWidgetItem(producto.get('codigo', '')))
            self.products_table.setItem(row, 1, QtWidgets.QTableWidgetItem(producto.get('nombre', '')))
            self.products_table.setItem(row, 2, QtWidgets.QTableWidgetItem(producto.get('marca', '')))
            self.products_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(producto.get('stock', 0))))
            self.products_table.setItem(row, 4, QtWidgets.QTableWidgetItem(f"${float(producto.get('venta', 0)):.2f}"))
        
        # Restaurar scroll
        self.products_table.verticalScrollBar().setValue(current_scroll)
        
    except Exception as e:
        print(f"[ERROR] Error actualizando tabla: {e}")


def _on_inventory_stats_updated(self, stats):
    """
    Se ejecuta cuando se reciben estadísticas de inventario.
    
    Actualiza:
    - Stock total
    - Valor total del inventario
    - Cantidad de items
    """
    try:
        # Actualizar labels si existen
        if hasattr(self, 'label_stock_total'):
            self.label_stock_total.setText(f"Stock Total: {stats['stock_total']} unidades")
        
        if hasattr(self, 'label_valor_total'):
            valor_formateado = f"${stats['valor_total']:,.2f}".replace(',', '.')
            self.label_valor_total.setText(f"Valor Total: {valor_formateado}")
        
        if hasattr(self, 'label_items_count'):
            self.label_items_count.setText(f"Items en Inventario: {stats['items_count']}")
        
        print(f"[INFO] Inventario actualizado - Stock: {stats['stock_total']}, Valor: ${stats['valor_total']:,.2f}")
        
    except Exception as e:
        print(f"[ERROR] Error actualizando stats: {e}")


def _on_auto_sync_completed(self, result):
    """
    Se ejecuta cuando la sincronización automática completa.
    
    Args:
        result: dict con {sincronizados, errores, pendientes}
    """
    try:
        sincronizados = result.get('sincronizados', 0)
        errores = result.get('errores', 0)
        pendientes = result.get('pendientes', 0)
        
        if sincronizados > 0:
            print(f"[SYNC] Inventario sincronizado - {sincronizados} items, {errores} errores, {pendientes} pendientes")
        
        # Actualizar contador de items pendientes si existe
        if hasattr(self, 'label_pending_sync'):
            if pendientes > 0:
                self.label_pending_sync.setText(f"⏳ {pendientes} items pendientes de sincronizar")
                self.label_pending_sync.show()
            else:
                self.label_pending_sync.hide()
        
    except Exception as e:
        print(f"[ERROR] Error en auto sync completed: {e}")


def _on_auto_sync_error(self, error_msg):
    """Se ejecuta cuando hay error en sincronización automática."""
    print(f"[ERROR] Auto sync error: {error_msg}")


def closeEvent(self, event):
    """
    Detiene los workers al cerrar la página.
    
    Agregar a InventoryPage (reemplazar si ya existe):
    """
    try:
        if hasattr(self, 'product_refresh_worker') and self.product_refresh_worker:
            if self.product_refresh_worker.isRunning():
                self.product_refresh_worker.stop()
                self.product_refresh_worker.wait()
        
        if hasattr(self, 'inventory_sync_worker') and self.inventory_sync_worker:
            if self.inventory_sync_worker.isRunning():
                self.inventory_sync_worker.stop()
                self.inventory_sync_worker.wait()
    except:
        pass
    
    super().closeEvent(event) if hasattr(super(), 'closeEvent') else None
