# Auditoría de Hilos y Rendimiento (Parte 2) - VISO 4.2.4

Este reporte profundiza en las páginas específicas y componentes de la UI donde se han detectado patrones de hilos "sueltos" o temporizadores que afectan la fluidez.

## 📦 Inventario (`inventory_page.py`) - El Punto Más Crítico

El inventario es la página con mayor carga de hilos simultáneos, lo que explica los lagueos al filtrar o cargar productos.

### 1. Hilos "Huérfanos" de Web Scraping e Imágenes
*   **Líneas:** 439 (`WebScraperThread`), 551 (`CombinedWebScraperThread`), 763 (`ImageLoaderThread`).
*   **Problema:** Al cargar el inventario, se lanzan decenas de hilos para buscar imágenes o datos. Si cierras la pestaña o cambias de página, estos hilos siguen corriendo en segundo plano descargando datos de internet, consumiendo ancho de banda y CPU innecesariamente.
*   **Observación:** Aunque existe la función `_cleanup_all_threads` (L3015), no siempre se llama a tiempo si el usuario navega rápido entre pestañas.

### 2. Guardado en Disco mediante `threading.Thread` (Sin control de cola)
*   **Líneas:** 8289 (`_sync_delete_background`), 8398 (`_sync_stock_background`).
*   **Peligro:** Estas funciones lanzan hilos "crudos" de Python para sincronizar stock. Si el usuario actualiza stock de 5 productos rápido, se lanzan 5 hilos que intentan escribir el **mismo archivo JSON** de inventario. Esto causa micro-bloqueos en Windows mientras el sistema operativo gestiona los permisos de escritura.

---

## 💰 Ventas y Cobros (`sales_page.py`)

### 3. El patrón `_orphan_qthread`
*   **Líneas:** 36-63, 7579, 7639.
*   **Observación:** Esta página usa una lista global llamada `_ORPHAN_QTHREADS` para mantener vivos los hilos de carga de ventas aunque cierres la ventana. 
*   **Impacto:** Si la carga de ventas es lenta (muchos datos), y el usuario abre y cierra la pestaña varias veces, se acumulan hilos "fantasma" en memoria RAM procesando los mismos datos de ventas una y otra vez, lagueando la app general.

### 4. Temporizadores en Cascada al Escribir
*   **Línea:** 2376 (`QtCore.QTimer.singleShot(100, self.actualizar_total_venta)`)
*   **Detalle:** Cada vez que el usuario escribe un precio o cantidad, se lanza un timer. Si se escribe rápido, se acumulan llamadas a cálculos matemáticos que, aunque ligeros, al repetirse cientos de veces por segundo, hacen que el cursor "salte" o se sienta pesado.

---

## 🖼️ Diálogos y Popups (`gui/dialogs/`)

### 5. Carga de Productos en Diálogos de Selección
*   **Archivo:** `dialogs/selection_products_v2.py` (L10) y `dialogs/frame_sale_dialog.py` (L25).
*   **Problema:** Ambos usan `ProductLoadWorker`. Al abrir un diálogo de venta (como el de elegir montura), se inicia una carga masiva. Si el diálogo se abre desde una PC lenta, la animación de apertura se corta (stuttering) porque el hilo de carga compite con el hilo de animación.

### 6. Ejecución de Procesos Externos (`subprocess`)
*   **Archivos:** `pdf_viewer_dialog.py` (L380), `browser_selection_dialog.py` (L242).
*   **Observación:** Abrir el navegador o el visor de PDF lanza un proceso de Windows. Esto siempre causa un pico de CPU que laguea la app por 1 segundo mientras Chrome o Edge inician. No es un error de VISO, pero es un "lag" percibido por el usuario.

---

## 📝 Conclusión de la Auditoría 2:
El sistema está muy "fragmentado" en cuanto a cómo maneja los hilos:
- Algunas partes usan `QThread` (Bien manejado).
- Otras usan `threading.Thread` (Peligroso, causa lagueos de disco).
- Otras usan `QTimer` para "parchar" bloqueos de UI.

**Recomendación Final:**
Centralizar el guardado de archivos en una sola cola (Queue) en segundo plano para que nunca, bajo ninguna circunstancia, se escriba un archivo JSON desde el hilo principal o desde múltiples hilos a la vez.

**Reporte generado el:** 1 de junio de 2026
