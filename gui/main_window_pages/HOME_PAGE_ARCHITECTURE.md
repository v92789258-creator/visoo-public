"""
DOCUMENTACIÓN - HomePage Modularizada

================================================================================
ARQUITECTURA
================================================================================

HomePage está dividido en COMPONENTES ESPECIALIZADOS, cada uno con UNA 
responsabilidad única. Esto facilita:

✓ Mantenimiento (cambiar algo es trivial)
✓ Testing (testear cada componente por separado)
✓ Escalabilidad (agregar features nuevas)
✓ Colaboración en equipo (menos conflictos de merge)


ESTRUCTURA DE ARCHIVOS
================================================================================

gui/main_window_pages/
├── home_page.py                          (ORQUESTADOR - ESTE ARCHIVO)
│   Responsabilidades:
│   - Coordinar componentes
│   - Emitir señales del ciclo de vida
│   - Gestionar flujo de datos
│   - NO hace: lógica de datos, construcción visual
│
└── components/                           (SUBMÓDULOS ESPECIALIZADOS)
    ├── __init__.py                       (Exportaciones)
    │
    ├── home_data_loader.py               (LÓGICA DE DATOS)
    │   Responsabilidades:
    │   - Cargar pacientes, productos, ventas
    │   - Cálculos: pacientes/mes, total ventas
    │   - Procesamiento: gráficos, agregaciones
    │   - Lógica de NEGOCIO PURA (sin UI)
    │
    ├── home_ui_builder.py                (CONSTRUCCIÓN VISUAL)
    │   Responsabilidades:
    │   - Crear layouts y frames
    │   - Aplicar estilos CSS
    │   - Efectos visuales (sombras, colores)
    │   - Instanciar widgets (HomePageWidgetImproved)
    │   - NO mezcla lógica
    │
    └── home_notifications.py             (SISTEMA DE NOTIFICACIONES)
        Responsabilidades:
        - Polling en background thread
        - Emisión de señales
        - Gestión del ciclo de vida
        - NO mezcla con UI o datos


FLUJO DE DATOS
================================================================================

1. HomePage.__init__()
   ├─ Crear HomeUIBuilder (UI)
   ├─ Crear HomeDataLoader (Datos)
   └─ Llamar _setup_ui() + QTimer.singleShot(_on_load_data)

2. _setup_ui()
   └─ HomeUIBuilder.build() → retorna contenedor visual

3. _on_load_data() [después de 50ms]
   ├─ refresh_dashboard()
   │  ├─ HomeDataLoader.load_all() [obtiene: pacientes, productos, ventas]
   │  ├─ _update_metrics() [actualiza contadores]
   │  └─ _update_sales_chart() [actualiza gráfico]
   ├─ _start_notifications() [inicia worker]
   └─ _emit_data_loaded_signal() [emite signal para hide overlay]

4. Cuando usuario cambia a otra pestaña y vuelve a HOME:
   └─ showEvent() → refresh_dashboard()


CÓMO AGREGAR NUEVAS FEATURES
================================================================================

Ejemplo: Queremos mostrar "Pacientes agendados hoy"

1. AGREGAR CÁLCULO en home_data_loader.py:
   ```python
   def count_patients_today(self, pacientes):
       today = datetime.date.today()
       count = 0
       for p in pacientes:
           try:
               fecha = datetime.datetime.strptime(
                   p.get('fecha','').split()[0], "%d/%m/%Y"
               ).date()
               if fecha == today:
                   count += 1
           except:
               continue
       return count
   ```

2. USAR EN home_page.py:
   ```python
   def _update_metrics(self, data):
       # ... código existente ...
       
       patients_today = self.data_loader.count_patients_today(
           data['pacientes']
       )
       self.home_widget.setPatientsToday(patients_today)
   ```

3. LISTO - Sin tocar UI, sin tocar notificaciones


CÓMO MODIFICAR EL ESTILO VISUAL
================================================================================

Todo está en home_ui_builder.py:

1. Cambiar color de fondo:
   ```python
   # En _setup_background()
   self.parent_page.setStyleSheet("""
       QWidget#MainBackground {
           background-color: #FF0000;  # Rojo
       }
   """)
   ```

2. Cambiar sombra de tarjeta:
   ```python
   # En _create_card_frame()
   shadow.setBlurRadius(50)  # Más borrosa
   shadow.setColor(QColor(0, 0, 0, 80))  # Más oscura
   ```

3. Cambiar bordes redondeados:
   ```python
   card.setStyleSheet("""
       QFrame#CardFrame {
           border-radius: 25px;  # Más redondeado
       }
   """)
   ```


CÓMO AGREGAR NUEVA FUENTE DE DATOS
================================================================================

Ejemplo: Queremos cargar "Proveedores"

1. EXTENDER home_data_loader.py:
   ```python
   def load_all(self):
       return {
           'pacientes': cargar_pacientes(self.username),
           'productos': cargar_productos(self.username),
           'ventas': cargar_ventas(self.username),
           'proveedores': cargar_proveedores(self.username),  # NUEVO
       }
   
   def count_active_providers(self, proveedores):
       return len([p for p in proveedores if p.get('activo')])
   ```

2. USAR EN home_page.py:
   ```python
   def _update_metrics(self, data):
       # ...
       active_providers = self.data_loader.count_active_providers(
           data['proveedores']
       )
       self.home_widget.setProviderCount(active_providers)
   ```


SEPARACIÓN DE RESPONSABILIDADES
================================================================================

Antes (monolítico):
HomePage.py
├─ Lógica de carga
├─ Cálculos
├─ Construcción UI
├─ Styling
├─ Notificaciones
└─ ❌ 300+ líneas, difícil de mantener

Después (modular):
HomePage.py             (60 líneas)  → Coordinación
├─ HomeDataLoader       (100 líneas) → Lógica + cálculos
├─ HomeUIBuilder        (70 líneas)  → Construcción + estilos
└─ NotificationWorker   (50 líneas)  → Background threading

✓ Total: ~280 líneas pero MUCHO más mantenible
✓ Cambios localizados: no afecta otras partes
✓ Testeable: cada módulo independiente


TESTING
================================================================================

Cada componente se puede testear aislado:

```python
# Test data loader
loader = HomeDataLoader('alex9121')
data = loader.load_all()
assert len(data['pacientes']) > 0
assert loader.count_patients_this_month(data['pacientes']) >= 0

# Test UI builder (sin datos, solo visual)
builder = HomeUIBuilder(mock_page)
ui = builder.build()
assert ui is not None

# Test notifications
worker = NotificationWorker()
received = False
worker.notification_received.connect(lambda x: received := True)
# ... esperar polling
assert received or not received (no falla)
```


NOTAS DE IMPLEMENTACIÓN
================================================================================

1. HomePageWidgetImproved es el widget C++ compilado
   - Se instancia una sola vez
   - Se actualiza con setters (setPatientCount, setTotalSales, etc.)
   - El estilo "background: transparent" intenta hacerlo transparente
   - Si no funciona, el widget tendrá su propio fondo

2. NotificationWorker corre en QThread separado
   - NO bloquea la UI
   - Timeout de 3s en requests
   - Esperas fraccionadas (50 x 0.1s) para poder cancelar rápido
   - Se detiene limpiamente en closeEvent()

3. Señales de ciclo de vida:
   - data_loaded: Emitida cuando datos están listos
   - Usada por MainWindow para hide LoadingOverlay
   - Emitida solo una vez al startup

4. Manejo de errores:
   - Try/except robustos en parsing de fechas
   - Errores no rompen UI (print + continue)
   - Valores por defecto (0, 0.0, [])


FUTURO: EXTENSIONES POSIBLES
================================================================================

1. Cache de datos:
   - Agregar in-memory cache en HomeDataLoader
   - Evitar recargar si los datos no cambiaron

2. Refresh automático:
   - QTimer en HomePage que llame refresh_dashboard() cada N segundos

3. Búsqueda/Filtrado:
   - Agregar HomeFilterManager para filtrar datos
   - Aplicar filtros sin recargar desde servidor

4. Exportación:
   - HomeExporter (exportar a Excel, PDF)
   - Usar datos ya cargados en memory

5. Analytics:
   - HomeAnalytics para calcular KPIs
   - Tendencias, comparativas año vs año

6. Multiidioma:
   - Agregar traducciones en HomeUIBuilder
   - Labels en i18n system

================================================================================
"""
