# Auditoría de Hilos y Rendimiento - VISO 4.2.4

Este archivo detalla los hilos ("threads") y procesos en segundo plano encontrados en el sistema que podrían estar causando pequeños bloqueos o lagueos en la interfaz de usuario (UI).

## ⚠️ Problemas Críticos (Bloqueos de UI)

### 1. Sincronización en el Hilo Principal (Main Thread)
Muchos procesos de guardado y carga de archivos JSON pesados se realizan directamente en el hilo de la interfaz, lo que causa micro-congelamientos.

*   **Archivo:** `utils/file_handler.py`
*   **Línea(s):** ~3000 (Funciones `cargar_ventas`, `cargar_pacientes`, `guardar_pacientes`)
*   **Observación:** Estas funciones leen/escriben archivos grandes. Si el archivo JSON crece mucho, la UI se congela mientras Windows termina de escribir en el disco.
*   **Solución sugerida:** Envolver estas llamadas en un `QThread` o `threading.Thread` con señales de retorno.

### 2. Uso Excesivo de `threading.Thread` (Hilos Sueltos)
Se encontraron múltiples hilos creados con la librería estándar de Python que se lanzan y se "olvidan" (`daemon=True`), lo que puede saturar la CPU en computadoras con pocos núcleos.

*   **Archivo:** `utils/file_handler.py`
*   **Línea:** 2261, 3732, 4007, 4072, 4771
*   **Código:** `threading.Thread(target=sync_in_background, daemon=True).start()`
*   **Peligro:** Si el usuario hace muchas acciones rápido, se pueden acumular 10 o 20 hilos de sincronización peleándose por el mismo archivo JSON, causando un lagueo masivo por "Race Conditions".

---

## 🕒 Temporizadores y Animaciones (Lag Visual)

### 3. Cascada de `QTimer.singleShot` en el Inicio
Al cargar el Dashboard (Home), se lanzan múltiples temporizadores casi al mismo tiempo, lo que satura el procesador justo cuando la app intenta mostrarse.

*   **Archivo:** `gui/main_window_pages/home_page.py`
*   **Línea(s):** 1048, 1049, 1050
*   **Código:**
    ```python
    QTimer.singleShot(120, lambda: self._refresh_comparison_chart())
    QTimer.singleShot(240, lambda: self._refresh_top_customers())
    QTimer.singleShot(360, lambda: self._refresh_top_products())
    ```
*   **Observación:** Cada una de estas funciones procesa datos pesados de ventas. Al ejecutarse con solo milisegundos de diferencia, el usuario siente un "tirón" en el scroll o en los botones.

---

## 🔄 Sincronización Automática (Lag Intermitente)

### 4. Hilo de Recordatorios de Citas
Hay un hilo constante revisando recordatorios que podría optimizarse.

*   **Archivo:** `utils/appointment_reminders.py`
*   **Línea:** 232
*   **Código:** `self.reminder_thread = threading.Thread(target=worker, daemon=True)`
*   **Observación:** Si el bucle del `worker` no tiene un `time.sleep()` adecuado o si la lista de citas es de miles, la CPU subirá su consumo cada pocos segundos.


---

## 📋 Resumen de Archivos a Revisar para Optimización:

1.  `utils/file_handler.py`: **(Prioridad Alta)** Mover operaciones de disco a segundo plano de forma ordenada (usando una cola/queue).
2.  `gui/main_window_pages/home_page.py`: **(Prioridad Media)** Espaciar más los tiempos de carga del dashboard o usar un solo hilo para procesar los 3 gráficos.
3.  `utils/sync_manager.py`: **(Prioridad Media)** Controlar que no se lancen hilos de sincronización si ya hay uno activo.

**Reporte generado el:** 1 de junio de 2026
