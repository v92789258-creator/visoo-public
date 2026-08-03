#!/usr/bin/env python3
"""
EJEMPLO PRÁCTICO: Cómo funciona la lógica de permisos granulares

Este script demuestra cómo funciona el sistema de permisos granulares
cuando un ayudante solo tiene ciertas acciones en un módulo.
"""

from utils.helpers_manager import (
    puede_ver_seccion,
    tiene_accion_permitida,
    obtener_modulos_permitidos,
    PERMISOS_DISPONIBLES
)

def ejemplo_1_solo_crear():
    """
    CASO 1: Ayudante solo puede CREAR productos, no VER
    
    Permisos asignados:
    {
        "inventario": ["crear"]
    }
    """
    print("=" * 80)
    print("CASO 1: Vendedor que solo REGISTRA ventas, no ve historial")
    print("=" * 80)
    
    # Simulación
    username_jefe = 'admin'
    username_ayudante = 'juan'
    
    print("\n📋 Permisos asignados:")
    print("   ventas: ['registrar']")
    
    print("\n🔍 Verificaciones:")
    
    # Esta es la lógica que usa obtener_modulos_permitidos()
    print("\n1️⃣ ¿Aparece el botón 'Ventas' en la barra?")
    print("   → SÍ, porque tiene al menos una acción ['registrar']")
    
    # Esta es la lógica que usa puede_ver_seccion()
    print("\n2️⃣ ¿Se cargan las ventas anteriores cuando entra?")
    print("   → NO, porque NO tiene la acción 'ver'")
    print("   → La página estará vacía")
    
    # Esta es la lógica específica para registrar
    print("\n3️⃣ ¿Puede registrar una nueva venta?")
    print("   → SÍ, porque tiene la acción 'registrar'")
    
    print("\n✅ Resultado final:")
    print("   - Botón 'Ventas' visible")
    print("   - Historial vacío")
    print("   - Puede crear nuevas ventas")
    print("   - No puede ver ventas antiguas")

def ejemplo_2_ver_y_editar():
    """
    CASO 2: Ayudante puede VER y EDITAR, pero no CREAR
    
    Permisos asignados:
    {
        "inventario": ["ver", "editar"]
    }
    """
    print("\n" + "=" * 80)
    print("CASO 2: Supervisor que REVISA y EDITA inventario")
    print("=" * 80)
    
    print("\n📋 Permisos asignados:")
    print("   inventario: ['ver', 'editar']")
    
    print("\n🔍 Verificaciones:")
    
    print("\n1️⃣ ¿Aparece el botón 'Inventario'?")
    print("   → SÍ, tiene ['ver', 'editar']")
    
    print("\n2️⃣ ¿Se carga la lista de productos?")
    print("   → SÍ, porque tiene 'ver'")
    
    print("\n3️⃣ ¿Puede crear nuevos productos?")
    print("   → NO, porque NO tiene 'crear'")
    
    print("\n4️⃣ ¿Puede editar productos?")
    print("   → SÍ, porque tiene 'editar'")
    
    print("\n✅ Resultado final:")
    print("   - Botón 'Inventario' visible")
    print("   - Lista de productos cargada")
    print("   - Puede editar precios/cantidad")
    print("   - No puede agregar productos nuevos")

def ejemplo_3_sin_permisos():
    """
    CASO 3: Ayudante sin permisos en una sección
    
    Permisos asignados:
    {
        "ventas": ["registrar"]
    }
    (NO tiene permisos en 'inventario')
    """
    print("\n" + "=" * 80)
    print("CASO 3: Vendedor que no tiene permiso en INVENTARIO")
    print("=" * 80)
    
    print("\n📋 Permisos asignados:")
    print("   ventas: ['registrar']")
    print("   (inventario: NO ASIGNADO)")
    
    print("\n🔍 Verificaciones:")
    
    print("\n1️⃣ ¿Aparece el botón 'Inventario'?")
    print("   → NO, porque no tiene ninguna acción en inventario")
    
    print("\n2️⃣ ¿Puede acceder a la página de inventario?")
    print("   → NO, el botón ni siquiera aparece")
    
    print("\n✅ Resultado final:")
    print("   - Botón 'Inventario' NO visible")
    print("   - No puede acceder a esa sección")

def ejemplo_4_completo():
    """
    CASO 4: Gerente con acceso completo
    """
    print("\n" + "=" * 80)
    print("CASO 4: Gerente con acceso COMPLETO")
    print("=" * 80)
    
    print("\n📋 Permisos asignados:")
    print("""
   inventario: ['ver', 'crear', 'editar', 'eliminar']
   ventas: ['ver', 'registrar', 'editar', 'eliminar']
   graduaciones: ['ver', 'crear', 'editar']
   pacientes: ['ver', 'crear', 'editar', 'eliminar']
   reportes: ['ver', 'descargar']
   configuracion: ['ver', 'editar']
    """)
    
    print("\n✅ Resultado final:")
    print("   - Todos los botones visibles")
    print("   - Acceso completo a todas las secciones")
    print("   - Puede hacer cualquier acción")

def mostrar_flujo_tecnico():
    """Muestra el flujo técnico de cómo se verifican los permisos"""
    print("\n" + "=" * 80)
    print("⚙️ FLUJO TÉCNICO DE VERIFICACIÓN")
    print("=" * 80)
    
    print("""
1. CUANDO INICIA LA APLICACIÓN (main.py):
   - Lee permisos del ayudante desde .helpers.json
   - Obtiene lista de módulos permitidos con obtener_modulos_permitidos()
   - Los botones se crean/ocultan basado en esta lista

2. CUANDO EL USUARIO ABRE UNA PÁGINA:
   - Se llama el __init__ o setup_ui() de la página
   - Se verifica puede_ver_seccion() específicamente
   - Si NO tiene "ver" → No cargar datos
   - Si SÍ tiene "ver" → Cargar datos normalmente

EJEMPLO: Página de Inventario

   __init__() llamado
   ↓
   _safe_initial_load()
   ↓
   ¿Es ayudante? ¿Tiene 'ver' en inventario?
   ↓
   SÍ → Cargar productos
   NO → Mostrar página vacía
   
EJEMPLO: Página de Ventas (Historial)

   setup_ui() llamado
   ↓
   ¿Es ayudante? ¿Tiene 'ver' en ventas?
   ↓
   SÍ → Crear tab "Historial de Ventas"
   NO → Tab "Historial" no aparece
    """)

def mostrar_codigo_ejemplo():
    """Muestra el código que se usa internamente"""
    print("\n" + "=" * 80)
    print("💻 CÓDIGO QUE SE USA INTERNAMENTE")
    print("=" * 80)
    
    print("""
# En inventory_page.py - _safe_initial_load()
if self.parent_app.is_helper:
    from utils.helpers_manager import puede_ver_seccion
    
    if not puede_ver_seccion(
        self.parent_app.username_jefe,
        self.parent_app.username,
        'inventario'
    ):
        print("Sin permiso para ver inventario")
        self.all_productos = []
        return
    
    # Cargar productos normalmente
    self.all_productos = cargar_productos(self.username)

---

# En sales_page.py - setup_ui()
puede_ver_historial = True
if self.parent_app.is_helper:
    from utils.helpers_manager import puede_ver_seccion
    puede_ver_historial = puede_ver_seccion(
        self.parent_app.username_jefe,
        self.parent_app.username,
        'ventas'
    )

if puede_ver_historial:
    # Agregar el tab de historial
    self.tab_widget.addTab(
        SalesHistoryPage(self.parent_app),
        "Historial de Ventas"
    )

---

# En patients_page.py - load_patients()
if self.parent_app.is_helper:
    from utils.helpers_manager import puede_ver_seccion
    if not puede_ver_seccion(
        self.parent_app.username_jefe,
        self.parent_app.username,
        'pacientes'
    ):
        self.patients_table.setRowCount(0)
        return
    
    # Cargar pacientes
    patients = cargar_pacientes(self.username)
    """)

def main():
    print("\n╔" + "=" * 78 + "╗")
    print("║" + " EJEMPLO PRÁCTICO: PERMISOS GRANULARES - VISO 4.2.3".center(78) + "║")
    print("╚" + "=" * 78 + "╝\n")
    
    ejemplo_1_solo_crear()
    ejemplo_2_ver_y_editar()
    ejemplo_3_sin_permisos()
    ejemplo_4_completo()
    mostrar_flujo_tecnico()
    mostrar_codigo_ejemplo()
    
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print("""
La lógica es simple pero poderosa:

1. El BOTÓN aparece si el ayudante tiene CUALQUIER acción
2. Los DATOS se cargan si el ayudante tiene LA ACCIÓN "ver"

Esto permite casos como:
- Registrar sin ver historial
- Crear sin ver existentes
- Editar sin poder eliminar
- Acceder a la página pero sin datos

Mejor control = Más seguridad = Sistema más granular
    """)

if __name__ == '__main__':
    main()
