"""
EJEMPLO: Cómo funciona la lógica de permisos granulares

ESCENARIO:
- Un ayudante solo tiene permiso para "registrar" ventas
- NO tiene permiso para "ver" el historial de ventas
- NO tiene permisos en otras secciones

RESULTADO ESPERADO:
- La sección de Ventas APARECE en la barra de navegación (porque tiene permiso "registrar")
- El ayudante SOLO ve la pestaña "Nueva Venta"
- El ayudante NO ve la pestaña "Historial de Ventas"
- Si intenta acceder directamente a historial, se le bloquea
"""

# ============================================================
# PERMISOS DEL AYUDANTE
# ============================================================

permisos_carlos = {
    'ventas': ['registrar']  # SOLO puede registrar, no ver
}

# ============================================================
# LÓGICA EN obtener_modulos_permitidos()
# ============================================================

def obtener_modulos_permitidos_DEMO(permisos):
    """
    Simula la lógica de obtener módulos permitidos.
    
    CLAVE: Un módulo SOLO aparece si tiene permiso "ver"
    """
    modulos = []
    
    for seccion, acciones in permisos.items():
        # Verificar si tiene "ver" en la sección
        if 'ver' in acciones:
            print(f"✓ {seccion.upper()}: Tiene permiso 'ver', agregar módulo")
            modulos.append(f"{seccion}_page")
        else:
            print(f"✗ {seccion.upper()}: NO tiene permiso 'ver', NO agregar módulo")
    
    return modulos

# Probar con los permisos de Carlos
print("=" * 70)
print("PASO 1: Obtener módulos permitidos")
print("=" * 70)
print(f"\nPermisos de Carlos: {permisos_carlos}")
modulos = obtener_modulos_permitidos_DEMO(permisos_carlos)
print(f"\nMódulos que aparecen en la barra: {modulos}")

# ============================================================
# PROBLEMA: Carlos tiene "registrar" pero NO "ver"
# ============================================================

print("\n" + "=" * 70)
print("ANÁLISIS: ¿Debería aparecer la sección de Ventas?")
print("=" * 70)

tiene_registrar = 'registrar' in permisos_carlos.get('ventas', [])
tiene_ver = 'ver' in permisos_carlos.get('ventas', [])

print(f"\n✓ ¿Tiene permiso 'registrar'?: {tiene_registrar}")
print(f"✗ ¿Tiene permiso 'ver'?: {tiene_ver}")

if tiene_ver:
    print("\n→ RESULTADO: Sección SÍ aparece en la barra")
else:
    print("\n→ RESULTADO: Sección NO aparece en la barra")

# ============================================================
# SOLUCIÓN CORRECTA
# ============================================================

print("\n" + "=" * 70)
print("SOLUCIÓN: Agregar 'ver' además de 'registrar'")
print("=" * 70)

permisos_carlos_correcto = {
    'ventas': ['ver', 'registrar']  # Ahora SÍ tiene ver
}

print(f"\nPermisos actualizados: {permisos_carlos_correcto}")
modulos_correcto = obtener_modulos_permitidos_DEMO(permisos_carlos_correcto)
print(f"Módulos disponibles: {modulos_correcto}")

# ============================================================
# LÓGICA EN sales_page.py
# ============================================================

print("\n" + "=" * 70)
print("PASO 2: Mostrar pestañas en la página de Ventas")
print("=" * 70)

def setup_sales_page_tabs_DEMO(permisos_ventas):
    """
    Simula cómo setup_ui() en SalesPage muestra las pestañas.
    """
    print("\nConfigurando pestañas de Ventas:")
    print("  ✓ Tab 1: 'Nueva Venta' (siempre visible)")
    
    # Verificar si tiene permiso 'ver' en ventas
    puede_ver_historial = 'ver' in permisos_ventas
    
    if puede_ver_historial:
        print("  ✓ Tab 2: 'Historial de Ventas' (VISIBLE)")
    else:
        print("  ✗ Tab 2: 'Historial de Ventas' (OCULTO)")
    
    return {
        'nueva_venta': True,
        'historial': puede_ver_historial
    }

print("\nCon permisos ['registrar'] (INCORRECTO):")
tabs = setup_sales_page_tabs_DEMO(['registrar'])
print(f"Resultado: {tabs}")

print("\nCon permisos ['ver', 'registrar'] (CORRECTO):")
tabs = setup_sales_page_tabs_DEMO(['ver', 'registrar'])
print(f"Resultado: {tabs}")

# ============================================================
# RESUMEN
# ============================================================

print("\n" + "=" * 70)
print("RESUMEN DE LA LÓGICA")
print("=" * 70)

print("""
1. REGISTRACIÓN DE PERMISOS (en la interfaz de Helpers):
   Se asignan acciones granulares: ['ver', 'registrar', 'editar']

2. OBTENER MÓDULOS PERMITIDOS (al iniciar sesión):
   - Se lee el archivo .helpers.json
   - Se verifica si tiene 'ver' en cada sección
   - SOLO se agregan módulos que tengan 'ver'
   - Resultado: lista de módulos que aparecen en la barra

3. MOSTRAR EN LA INTERFAZ (en cada página):
   - Se verifica si puede hacer cada acción específica
   - Se ocultan/habilitan botones según sus permisos
   - Ejemplo en Ventas: 'Historial' solo aparece si tiene 'ver'

4. VERIFICACIÓN EN BACKEND:
   - Si intenta acceder a un módulo sin 'ver', se bloquea
   - Si intenta hacer una acción sin permiso, se rechaza
   - Las restricciones son a nivel de UI y backend
""")

# ============================================================
# COMPATIBILIDAD HACIA ATRÁS
# ============================================================

print("\n" + "=" * 70)
print("COMPATIBILIDAD CON PERMISOS VIEJOS (True/False)")
print("=" * 70)

permisos_viejos = {
    'ventas': True,  # Formato viejo
    'inventario': False
}

def normalizar_permisos_DEMO(permisos):
    """Convierte permisos viejos a nuevo formato."""
    resultado = {}
    
    acciones_por_seccion = {
        'ventas': ['ver', 'registrar', 'editar', 'eliminar'],
        'inventario': ['ver', 'crear', 'editar', 'eliminar'],
    }
    
    for seccion, valor in permisos.items():
        if isinstance(valor, bool) and valor:
            # Si es True, agregar todas las acciones
            resultado[seccion] = acciones_por_seccion.get(seccion, [])
        elif isinstance(valor, bool) and not valor:
            # Si es False, no agregar nada
            pass
    
    return resultado

print(f"\nPermisos viejos: {permisos_viejos}")
permisos_normalizados = normalizar_permisos_DEMO(permisos_viejos)
print(f"Permisos normalizados: {permisos_normalizados}")
print("\nNota: True se convierte a todas las acciones, False se ignora")

print("\n" + "=" * 70)
