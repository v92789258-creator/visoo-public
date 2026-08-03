# HomePage - Refactorización Completa ✓

## 🎯 Objetivo Completado

Transformar HomePage de código monolítico (300+ líneas) a **arquitectura modular profesional** con componentes especializados.

---

## 📊 ANTES vs DESPUÉS

### ANTES: Monolítico ❌

```
gui/main_window_pages/home_page.py (300+ líneas)
┣─ NotificationWorker class (50 líneas)
│  ├─ run()
│  ├─ stop()
│  └─ todo mezclado con HomePage
│
└─ HomePage class (250+ líneas)
   ├─ setup_ui_moderna() - Construcción visual
   ├─ load_data() - Carga
   ├─ update_dashboard_data() - Lógica + actualización
   ├─ refresh_sales_chart() - Cálculos complejos
   ├─ start_notification_polling()
   └─ ❌ TODO EN UN SOLO ARCHIVO
      ├─ Lógica de datos
      ├─ Cálculos
      ├─ Construcción visual
      ├─ Estilos CSS
      └─ Notificaciones
```

**Problemas:**
- ❌ Difícil de mantener (cambios locales rompen otra parte)
- ❌ Imposible de testear (todo acoplado)
- ❌ Código duplicado (parsing de fechas, cálculos)
- ❌ Difícil para equipo (conflictos de merge)

---

### DESPUÉS: Modular ✓

```
gui/main_window_pages/
├── home_page.py (60 líneas)
│  └─ HomePage (Orquestador)
│     ├─ refresh_dashboard()
│     ├─ _update_metrics()
│     ├─ _update_sales_chart()
│     └─ Coordina todo
│
└── components/
    ├── __init__.py (Exportaciones limpias)
    │
    ├── home_data_loader.py (100 líneas)
    │  └─ HomeDataLoader (Especialista en DATOS)
    │     ├─ load_all()
    │     ├─ count_patients_this_month()
    │     ├─ calculate_total_sales()
    │     └─ prepare_sales_chart()
    │
    ├── home_ui_builder.py (70 líneas)
    │  └─ HomeUIBuilder (Especialista en VISUAL)
    │     ├─ build()
    │     ├─ _setup_background()
    │     ├─ _create_card_frame()
    │     └─ _insert_home_widget()
    │
    └── home_notifications.py (50 líneas)
       └─ NotificationWorker (Especialista en BACKGROUND)
          ├─ run()
          └─ stop()
```

**Ventajas:**
- ✅ Cada archivo = 1 responsabilidad
- ✅ Cambios localizados (editar datos NO toca UI)
- ✅ Fácil de testear (componentes independientes)
- ✅ Escalable (agregar features es trivial)
- ✅ Profesional (patrón para toda la empresa)

---

## 🔧 Componentes Especializados

### 1️⃣ HomeDataLoader - Lógica de Datos

**Responsabilidad:** TODO sobre datos (carga, cálculos, lógica)

```python
loader = HomeDataLoader(username='alex9121')

# Cargar todo
data = loader.load_all()
# ↓ {
#   'pacientes': [...],
#   'productos': [...],
#   'ventas': [...]
# }

# Cálculos especializados
monthly = loader.count_patients_this_month(data['pacientes'])
total_sales = loader.calculate_total_sales(data['ventas'])
chart_data = loader.prepare_sales_chart(data['ventas'], days=15)
```

**Ventajas:**
- ✅ Lógica pura (sin UI)
- ✅ Fácil de testear
- ✅ Reutilizable en otras páginas
- ✅ Cambios de lógica NO afectan UI

---

### 2️⃣ HomeUIBuilder - Construcción Visual

**Responsabilidad:** TODO sobre interfaz visual

```python
builder = HomeUIBuilder(parent_page)

# Construir toda la UI
container = builder.build()
# ↓ QFrame con:
#   - Fondo gris suave
#   - Tarjeta blanca con sombra
#   - Widget C++ dentro
#   - Estilos CSS aplicados

# Acceder al widget interno
home_widget = builder.home_widget
home_widget.setPatientCount(1000)
```

**Ventajas:**
- ✅ Separación total: visual ≠ lógica
- ✅ Cambiar colores/estilos es trivial
- ✅ Agregar widgets nuevos es fácil
- ✅ NO mezcla con datos

---

### 3️⃣ NotificationWorker - Background Polling

**Responsabilidad:** Polling de notificaciones sin bloquear UI

```python
worker = NotificationWorker()

# Conectar a cambios
worker.notification_received.connect(on_new_notification)

# Corre en thread separado
worker.start()

# Parar limpiamente
worker.stop()
```

**Ventajas:**
- ✅ NO bloquea UI
- ✅ Thread separado
- ✅ Parada elegante
- ✅ Manejo de timeout robusto

---

## 📈 Cómo Funciona

### Flujo de Inicialización

```
1. HomePage.__init__()
   │
   ├─ HomeUIBuilder(self)
   │  └─ Crea estructura visual
   │
   ├─ HomeDataLoader(username)
   │  └─ Prepara data loader
   │
   └─ QTimer.singleShot(50ms, _on_load_data)
      │
      └─ _on_load_data()
         ├─ refresh_dashboard()
         │  ├─ load_all() → obtiene datos
         │  ├─ _update_metrics() → actualiza contadores
         │  └─ _update_sales_chart() → actualiza gráfico
         ├─ _start_notifications() → inicia background worker
         └─ _emit_data_loaded_signal() → emite signal
            (LoadingOverlay se oculta aquí)

2. Usuario navega a otra pestaña y vuelve a HOME
   └─ showEvent() → refresh_dashboard() [recargar datos]
```

---

## 🚀 Ejemplos de Uso

### Ejemplo 1: Agregar métrica nueva

**Quieres:** Mostrar "Pacientes registrados hoy"

**Paso 1:** Agregar método en `HomeDataLoader`
```python
# components/home_data_loader.py
def count_patients_today(self, pacientes):
    today = datetime.date.today()
    count = 0
    for p in pacientes:
        try:
            fecha_str = p.get('fecha', '').split()[0]
            fecha = datetime.datetime.strptime(fecha_str, "%d/%m/%Y").date()
            if fecha == today:
                count += 1
        except:
            continue
    return count
```

**Paso 2:** Usar en `HomePage`
```python
# home_page.py - en _update_metrics()
patients_today = self.data_loader.count_patients_today(data['pacientes'])
self.home_widget.setPatientsToday(patients_today)
```

**✅ Listo** - 5 líneas, sin tocar UI, sin riesgos

---

### Ejemplo 2: Cambiar color de fondo

**Quieres:** Cambiar fondo gris a azul

**Editar:** `HomeUIBuilder._setup_background()`
```python
self.parent_page.setStyleSheet("""
    QWidget#MainBackground {
        background-color: #0066FF;  # Azul
    }
""")
```

**✅ Listo** - 1 línea, solo visual, sin afectar datos

---

### Ejemplo 3: Agregar nueva fuente de datos

**Quieres:** Mostrar "Cantidad de proveedores activos"

**Paso 1:** Extender `load_all()`
```python
def load_all(self):
    return {
        'pacientes': cargar_pacientes(self.username),
        'productos': cargar_productos(self.username),
        'ventas': cargar_ventas(self.username),
        'proveedores': cargar_proveedores(self.username),  # NUEVO
    }
```

**Paso 2:** Agregar cálculo
```python
def count_active_providers(self, proveedores):
    return len([p for p in proveedores if p.get('activo')])
```

**Paso 3:** Usar en HomePage
```python
active_providers = self.data_loader.count_active_providers(data['proveedores'])
self.home_widget.setProviderCount(active_providers)
```

**✅ Listo** - Completamente desacoplado

---

## 📚 Documentación

**Guía completa:** Leer `HOME_PAGE_ARCHITECTURE.md` en el mismo directorio

Contiene:
- Arquitectura detallada
- Flujo de datos completo
- Cómo agregar features
- Cómo testear
- Ideas para futuro

---

## ✨ Resumen de Cambios

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Archivos** | 1 | 4 |
| **Líneas** | 300+ | ~280 (pero MUCHO más limpio) |
| **Responsabilidades** | Mezcladas | Claras |
| **Testeable** | ❌ No | ✅ Sí |
| **Escalable** | ❌ Difícil | ✅ Fácil |
| **Equipos** | ❌ Conflictos | ✅ Sin conflictos |
| **Mantenible** | ❌ Frágil | ✅ Robusto |

---

## 🎓 Patrón para Toda la Empresa

Este patrón modular debe aplicarse a:

- [ ] InventoryPage
- [ ] PatientsPage
- [ ] SalesPage
- [ ] ConfigPage
- [ ] ReportsPage
- [ ] etc.

Así toda la app será:
- **Profesional**
- **Mantenible**
- **Escalable**
- **Testeable**

---

## 🚨 Testing (Próximo Paso)

Crear test suite para validar:

```python
# test_home_data_loader.py
def test_count_patients_this_month():
    loader = HomeDataLoader('test_user')
    assert loader.count_patients_this_month([...]) >= 0

def test_calculate_total_sales():
    loader = HomeDataLoader('test_user')
    assert loader.calculate_total_sales([...]) >= 0

# test_home_ui_builder.py
def test_ui_builder_creates_frame():
    builder = HomeUIBuilder(mock_page)
    ui = builder.build()
    assert ui is not None
    assert hasattr(builder, 'home_widget')
```

---

**Status:** ✅ COMPLETADO - HomePage 100% modularizado y funcional

Para preguntas → Leer documentación en el directorio `gui/main_window_pages/`
