"""
CHECKLIST DE PRUEBAS - SISTEMA DE PERMISOS GRANULARES

Sigue estos pasos para verificar que el sistema funciona correctamente.
"""

print("""
╔════════════════════════════════════════════════════════════════════════════════╗
║                        CHECKLIST DE PRUEBAS                                   ║
╚════════════════════════════════════════════════════════════════════════════════╝

PREPARACIÓN
═══════════════════════════════════════════════════════════════════════════════

□ Compilar todos los archivos (sin errores de sintaxis)
  → python -m py_compile utils/helpers_manager.py gui/main_window.py ...
  
□ Iniciar la aplicación
  → python main.py


PRUEBA 1: CREAR AYUDANTE CON PERMISOS LIMITADOS
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Ir a Configuración → Helpers
  2. □ Click en "Nuevo Ayudante"
  3. □ Rellenar datos:
       - Nombre: Carlos Test
       - Usuario: carlos_test
       - Contraseña: test123
  4. □ En Permisos, seleccionar SOLO:
       - Inventario → ☑ Ver
       - Ventas → ☑ Registrar
  5. □ Click Guardar
  
Validar:
  □ Se crea sin errores
  □ Los permisos se muestran cuando se abre de nuevo


PRUEBA 2: VERIFICAR BOTONES DE NAVEGACIÓN
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Cerrar sesión (botón cerrar en la esquina)
  2. □ Login como Carlos Test (usuario: carlos_test, contraseña: test123)
  3. □ Observar barra de navegación izquierda
  
Validar:
  ✓ DEBEN APARECER:
    □ Botón Inicio
    □ Botón Inventario (tiene 'ver')
  ✗ NO DEBEN APARECER:
    □ Botón Ventas (solo tiene 'registrar', no 'ver')
    □ Botón Pacientes (sin permisos)
    □ Botón Graduaciones (sin permisos)
    □ Botón Reportes (sin permisos)
    □ Botón Configuración (sin permisos)


PRUEBA 3: VERIFICAR CARGA DE DATOS - INVENTARIO
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Click en botón Inventario
  2. □ Observar si cargan los productos
  
Validar:
  □ Se muestra la página de inventario
  □ SI hay productos, se cargan (porque tiene 'ver')
  □ Si está vacío, es correcto (es el estado normal)
  □ NO hay mensaje de error


PRUEBA 4: VERIFICAR RESTRICCIÓN - VENTAS
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Intentar acceder a Ventas de alguna forma:
       - ¿Aparece el botón? NO, así que probablemente no puedas
       - Si aparece (error), click en él
  
Validar:
  ✓ CORRECTO:
    □ El botón NO aparece en la barra (no tiene 'ver')
  
  ✗ INCORRECTO:
    □ Si aparece, es un bug


PRUEBA 5: CREAR AYUDANTE COMPLETO
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Volver a login como admin/jefe
  2. □ Ir a Configuración → Helpers
  3. □ Click en "Nuevo Ayudante"
  4. □ Rellenar datos:
       - Nombre: Juan Completo
       - Usuario: juan_full
       - Contraseña: test123
  5. □ En Permisos, seleccionar TODO:
       - Inventario → ☑ Ver ☑ Crear ☑ Editar ☑ Eliminar
       - Ventas → ☑ Ver ☑ Registrar ☑ Editar ☑ Eliminar
       - Graduaciones → ☑ Ver ☑ Crear ☑ Editar
       - Pacientes → ☑ Ver ☑ Crear ☑ Editar ☑ Eliminar
       - Reportes → ☑ Ver ☑ Descargar
       - Configuración → ☑ Ver ☑ Editar
  6. □ Click Guardar
  
Validar:
  □ Se crea sin errores
  □ Juan tiene acceso a TODO


PRUEBA 6: VERIFICAR ACCESO COMPLETO
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Cerrar sesión
  2. □ Login como Juan Completo
  3. □ Observar barra de navegación
  
Validar:
  ✓ TODOS los botones DEBEN APARECER:
    □ Inicio
    □ Clientes
    □ Pacientes
    □ Inventario
    □ Calendario
    □ Nueva Graduación
    □ Configuración


PRUEBA 7: CARGAR DATOS CON ACCESO COMPLETO
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Click en Inventario → debe cargar
  2. □ Click en Pacientes → debe cargar
  3. □ Click en Nueva Graduación → debe funcionar
  4. □ Ir a Ventas (si existe botón) → debe mostrar historial
  
Validar:
  □ Todos los datos cargan sin problemas
  □ Sin mensajes de error


PRUEBA 8: CREACIÓN DE AYUDANTE "SIN PERMISOS"
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Volver a admin
  2. □ Crear nuevo ayudante:
       - Nombre: Diego Limitado
       - Usuario: diego_limit
       - Contraseña: test123
  3. □ NO seleccionar NINGÚN permiso
  4. □ Click Guardar
  
Validar:
  ✓ CORRECTO:
    □ El sistema ACEPTA (aunque no haya sentido)
    □ O muestra error "Seleccione al menos un permiso"
  
  (Cualquiera de estas opciones es aceptable)


PRUEBA 9: VERIFICAR AYUDANTE SIN PERMISOS
═══════════════════════════════════════════════════════════════════════════════

Si la aplicación aceptó crear a Diego sin permisos:

Pasos:
  1. □ Cerrar sesión
  2. □ Login como Diego Limitado
  3. □ Observar barra
  
Validar:
  ✓ CORRECTO:
    □ NO aparece NINGÚN botón excepto Inicio
    □ Dice algo como "Sin permisos" en la barra


PRUEBA 10: EDITAR PERMISOS DE UN AYUDANTE
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Volver a admin
  2. □ Ir a Configuración → Helpers
  3. □ Click en "Carlos Test" (el que creamos primero)
  4. □ AGREGAR nuevos permisos:
       - Pacientes → ☑ Ver ☑ Crear
  5. □ Click Guardar
  
Validar:
  □ Se actualiza correctamente
  □ Sin errores


PRUEBA 11: VERIFICAR CAMBIOS EN CARLOS
═══════════════════════════════════════════════════════════════════════════════

Si Carlos tenía sesión abierta:

Pasos:
  1. □ Cerrar y abrir la aplicación
  2. □ Login como Carlos Test
  3. □ Observar barra
  
Validar:
  ✓ AHORA DEBE APARECER:
    □ Botón Pacientes (nuevamente agregado)
    □ Botón Inventario (ya estaba)
  ✗ SIGUE SIN APARECER:
    □ Botón Ventas (solo tiene 'registrar', no 'ver')


PRUEBA 12: VERIFICAR CARGA DE DATOS - PACIENTES
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Click en botón Pacientes
  2. □ Observar si cargan los pacientes
  
Validar:
  □ Se cargan los pacientes (porque tiene 'ver')
  □ Botón "Nuevo" aparece (porque tiene 'crear')
  □ Sin errores


PRUEBA 13: COMPATIBILIDAD CON HELPERS ANTIGUOS
═══════════════════════════════════════════════════════════════════════════════

Si ya existen helpers con formato viejo (True/False):

Pasos:
  1. □ Verificar archivo .helpers.json
  2. □ Debe tener formato viejo: {'usuario': True, 'inventario': False}
  3. □ Login como ese helper
  
Validar:
  □ La aplicación lo convierte automáticamente
  □ El helper funciona sin cambios
  □ True se convierte a todas las acciones
  □ False se ignora


PRUEBA 14: PERFIL DE SEGURIDAD - INTENTOS NO AUTORIZADOS
═══════════════════════════════════════════════════════════════════════════════

Pasos (con Carlos que solo tiene Inventario + Registrar Ventas):
  1. □ Intentar acceder a /pacientes modificando URL (si es web)
  2. □ Intentar usar console para forzar acceso
  
Validar:
  ✓ DEBE BLOQUEARSE:
    □ Los datos no cargan
    □ Se muestra mensaje de sin permisos
    □ NO muestra error, sino restricción clara


PRUEBA 15: LOGS Y MENSAJES
═══════════════════════════════════════════════════════════════════════════════

Pasos:
  1. □ Abrir consola (si está habilitada)
  2. □ Login como Carlos
  3. □ Observar logs
  
Validar:
  □ Dice algo como:
    "✓ [PERMISOS] Ayudante 'carlos_test' verificado"
  □ Si intenta acceso no autorizado:
    "⚠️ [PERMISOS] Ayudante 'carlos_test' no tiene permiso 'ver' en pacientes"


═══════════════════════════════════════════════════════════════════════════════
RESUMEN DE ESTADO
═══════════════════════════════════════════════════════════════════════════════

Marca los tests completados:

□ Prueba 1: Crear ayudante con permisos limitados
□ Prueba 2: Verificar botones de navegación
□ Prueba 3: Verificar carga - Inventario
□ Prueba 4: Verificar restricción - Ventas
□ Prueba 5: Crear ayudante completo
□ Prueba 6: Verificar acceso completo
□ Prueba 7: Cargar datos con acceso completo
□ Prueba 8: Crear ayudante sin permisos
□ Prueba 9: Verificar ayudante sin permisos
□ Prueba 10: Editar permisos
□ Prueba 11: Verificar cambios
□ Prueba 12: Verificar carga - Pacientes
□ Prueba 13: Compatibilidad con antiguos
□ Prueba 14: Intentos no autorizados
□ Prueba 15: Logs y mensajes

✅ SI PASARON TODAS: El sistema funciona correctamente
⚠️  SI FALLARON ALGUNAS: Revisar los logs y mensajes de error
❌ SI FALLARON MUCHAS: Contactar al desarrollador


═══════════════════════════════════════════════════════════════════════════════
NOTAS IMPORTANTES
═══════════════════════════════════════════════════════════════════════════════

1. El sistema es JERÁRQUICO:
   - Sin 'ver' → no aparece la sección
   - Con 'ver' → aparece pero solo puedes hacer lo permitido

2. Los cambios son INMEDIATOS:
   - Si editas permisos, al cerrar sesión se actualiza
   - No necesitas reiniciar la app

3. Los datos se PROTEGEN en backend:
   - Las validaciones ocurren tanto en UI como en servidor
   - Aunque alguien intente saltarse la UI, el backend lo bloquea

4. Compatibilidad TOTAL:
   - Helpers antiguos (True/False) funcionan
   - Se convierten automáticamente
   - No se necesita migración manual
""")
