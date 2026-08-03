"""
ESTRUCTURA MODULAR - HomePage (Página Principal)

¿QUÉ CAMBIÓ?
============

ANTES: 1 archivo monolítico (300+ líneas)
┣─ Lógica de datos
┣─ Cálculos
┣─ Construcción UI
┣─ Estilos CSS
┣─ Notificaciones
└─ ❌ Difícil de mantener/testear

DESPUÉS: Arquitectura MODULAR (dividida en 4 especialistas)
┣─ home_page.py (60 líneas)
│  └─ Orquestador: Coordina todo
│
├─ components/home_data_loader.py (100 líneas)
│  └─ Especialista en DATOS: Carga, cálculos, lógica
│
├─ components/home_ui_builder.py (70 líneas)
│  └─ Especialista en VISUAL: Layouts, estilos, sombras
│
└─ components/home_notifications.py (50 líneas)
   └─ Especialista en NOTIFICACIONES: Background polling


VENTAJAS
========

✓ MANTENIBLE
  - Cambiar color → editas solo home_ui_builder.py
  - Agregar métrica → editas solo home_data_loader.py
  - No hay código "enredado"

✓ TESTEABLE
  - Testear cálculos sin crear UI
  - Testear UI sin cargar datos
  - Cada componente independiente

✓ ESCALABLE
  - Agregar feature es trivial
  - Ejemplo: queres mostrar "Pacientes hoy"
    1. Agregar método en HomeDataLoader
    2. Usarlo en HomePage._update_metrics()
    3. Listo

✓ TRABAJO EN EQUIPO
  - Un dev trabaja en datos
  - Otro dev trabaja en UI
  - Cero conflictos de merge

✓ PROFESIONAL
  - Código limpio
  - Seguir este patrón en TODA la empresa
  - Fácil para nuevos developers


RESPONSABILIDADES CLARAS
========================

┌─ home_page.py (ORQUESTADOR)
│  
│  ¿QUÉ HACE?
│  • Coordina carga de datos
│  • Gestiona UI (delegando a builder)
│  • Emite señales de ciclo de vida
│  • Refresca dashboard cuando necesario
│
│  ¿QUÉ NO HACE?
│  ✗ Lógica de datos (delegada a HomeDataLoader)
│  ✗ Construcción visual (delegada a HomeUIBuilder)
│  ✗ Polling de notificaciones (delegada a NotificationWorker)
│
│
├─ components/home_data_loader.py (ESPECIALISTA EN DATOS)
│  
│  ¿QUÉ HACE?
│  • Cargar pacientes, productos, ventas
│  • Calcular: pacientes/mes, total ventas
│  • Preparar datos para gráficos
│  • Lógica de NEGOCIO pura
│
│  ¿QUÉ NO HACE?
│  ✗ Mostrar nada en pantalla
│  ✗ Crear widgets
│  ✗ Hacer polling
│
│
├─ components/home_ui_builder.py (ESPECIALISTA EN VISUAL)
│  
│  ¿QUÉ HACE?
│  • Crear estructura de layouts
│  • Aplicar estilos CSS
│  • Efectos visuales (sombras, colores)
│  • Instanciar HomePageWidgetImproved
│
│  ¿QUÉ NO HACE?
│  ✗ Calcular nada
│  ✗ Conectar a base de datos
│  ✗ Mezclar lógica con UI
│
│
└─ components/home_notifications.py (ESPECIALISTA EN BACKGROUND)
   
   ¿QUÉ HACE?
   • Polling de notificaciones en thread separado
   • Emitir señales cuando hay notificaciones nuevas
   • Gestionar ciclo de vida del worker
   • No bloquear UI
   
   ¿QUÉ NO HACE?
   ✗ Mostrar notificaciones (eso es job de otra parte)
   ✗ Procesar datos
   ✗ Crear UI


FLUJO TÍPICO
============

1. App inicia → crea HomePage
2. HomePage.__init__() 
   ├─ Crea UI (HomeUIBuilder)
   ├─ Crea Data Manager (HomeDataLoader)
   └─ QTimer.singleShot(50ms) → _on_load_data()

3. _on_load_data() [después de mostrar UI]
   ├─ refresh_dashboard()
   │  ├─ HomeDataLoader.load_all() [obtiene datos]
   │  ├─ _update_metrics() [actualiza contadores]
   │  └─ _update_sales_chart() [actualiza gráfico]
   ├─ _start_notifications() [inicia background worker]
   └─ data_loaded.emit() [señal para hide LoadingOverlay]

4. Usuario hace clic en otro tab y vuelve a HOME
   └─ showEvent() → refresh_dashboard()


EJEMPLO: AGREGAR NUEVA MÉTRICA
==============================

Quieres mostrar "Pacientes agendados hoy"

Antes (monolítico):
┌─────────────────────────────────────┐
│ Editarías home_page.py              │
│ ├─ Agregar lógica de filtrado       │
│ ├─ Crear variable temporal          │
│ ├─ Buscar donde actualizar UI       │
│ ├─ Arriesgar romper algo existente  │
│ └─ 300+ líneas de código            │
└─────────────────────────────────────┘

Después (modular):
┌─────────────────────────────────────────────────┐
│ 1. Editar home_data_loader.py (100 líneas)      │
│                                                 │
│    def count_patients_today(self, pacientes):   │
│        today = datetime.date.today()            │
│        count = 0                                │
│        for p in pacientes:                      │
│            try:                                 │
│                fecha_str = p.get('fecha','')    │
│                fecha = datetime.datetime...     │
│                if fecha == today:               │
│                    count += 1                   │
│            except: continue                     │
│        return count                             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 2. Editar home_page.py (60 líneas)              │
│                                                 │
│    def _update_metrics(self, data):             │
│        # ... código existente ...               │
│                                                 │
│        patients_today = (                       │
│            self.data_loader.count_patients_today│
│            (data['pacientes'])                  │
│        )                                        │
│        self.home_widget.setPatientsToday(...)   │
└─────────────────────────────────────────────────┘

✓ LISTO - 5 líneas nuevas, sin tocar UI, sin riesgos


ARCHIVO DE DOCUMENTACIÓN COMPLETA
==================================

Lee: HOME_PAGE_ARCHITECTURE.md (en este mismo directorio)

Contiene:
- Arquitectura detallada
- Flujo de datos completo
- Cómo agregar features nuevas
- Cómo modificar estilos
- Cómo agregar nuevas fuentes de datos
- Ejemplos de testing
- Ideas para futuro


NOTAS IMPORTANTES
=================

1. HomePageWidgetImproved
   - Es el widget C++ compilado
   - Se actualiza con setters (NO directamente)
   - Instanciado una sola vez
   - Guardado en self.home_widget

2. NotificationWorker
   - Corre en thread SEPARADO
   - NO bloquea UI
   - Se detiene limpiamente
   - Emite signals cuando hay notificaciones

3. Señales
   - data_loaded: Emitida cuando datos listos
   - Usada por MainWindow para hide LoadingOverlay
   - Emitida solo una vez

4. Errores
   - Manejo robusto de parsing de fechas
   - Los errores NO rompen la UI
   - Siempre hay valores por defecto


PRÓXIMOS PASOS
==============

Ahora que HomePage está MODULAR y LIMPIO:

1. Aplicar mismo patrón a otras páginas (inventory, patients, etc.)
2. Crear test suite para cada componente
3. Documentar arquitectura de TODA la app
4. Setup CI/CD para testing automático
5. Crear guía de style para equipo


================================================================================
Por preguntas → Ver HOME_PAGE_ARCHITECTURE.md
================================================================================
"""
