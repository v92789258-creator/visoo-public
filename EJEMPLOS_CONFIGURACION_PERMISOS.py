"""
EJEMPLOS DE CONFIGURACIÓN DE PERMISOS PARA DIFERENTES ROLES

Copia y pega estos permisos cuando crees un nuevo ayudante.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 1. VENDEDOR JUNIOR
# ═══════════════════════════════════════════════════════════════════════════════
# Puede: Registrar ventas y crear pacientes nuevos
# No puede: Ver historial, editar ventas, eliminar nada

VENDEDOR_JUNIOR = {
    'ventas': ['registrar'],  # Solo registrar, no ver historial
    'pacientes': ['ver', 'crear'],  # Ver pacientes y crear nuevos
}
# Resultado en la app:
# ✓ Botones: Ventas, Pacientes
# ✓ En Ventas: Solo tab "Nueva Venta", sin "Historial"
# ✓ En Pacientes: Ver lista completa y crear


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ASISTENTE DE INVENTARIO
# ═══════════════════════════════════════════════════════════════════════════════
# Puede: Ver y editar productos
# No puede: Eliminar, crear sin restricciones

ASISTENTE_INVENTARIO = {
    'inventario': ['ver', 'editar'],  # Ver y editar, no crear/eliminar
    'reportes': ['ver'],  # Puede ver reportes
}
# Resultado en la app:
# ✓ Botones: Inventario, Reportes
# ✓ En Inventario: Ver todos, editar, pero sin botón eliminar
# ✓ En Reportes: Solo lectura


# ═══════════════════════════════════════════════════════════════════════════════
# 3. OPTOMETRISTA ASISTENTE
# ═══════════════════════════════════════════════════════════════════════════════
# Puede: Ver pacientes, crear y editar graduaciones
# No puede: Eliminar pacientes

OPTOMETRISTA_ASISTENTE = {
    'pacientes': ['ver', 'crear', 'editar'],  # Gestión completa
    'graduaciones': ['ver', 'crear', 'editar'],  # Crear y editar graduaciones
}
# Resultado en la app:
# ✓ Botones: Pacientes, Graduaciones
# ✓ En Pacientes: Ver, crear, editar (sin eliminar)
# ✓ En Graduaciones: Crear y editar


# ═══════════════════════════════════════════════════════════════════════════════
# 4. REPORTERO
# ═══════════════════════════════════════════════════════════════════════════════
# Puede: Solo ver y descargar reportes
# No puede: Modificar nada

REPORTERO = {
    'reportes': ['ver', 'descargar'],  # Solo lectura
}
# Resultado en la app:
# ✓ Botones: Reportes
# ✓ En Reportes: Ver y descargar
# ✗ Ningún otro acceso


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GERENTE (Acceso casi completo)
# ═══════════════════════════════════════════════════════════════════════════════
# Puede: Todo excepto configuración
# No puede: Cambiar configuraciones del sistema

GERENTE = {
    'inventario': ['ver', 'crear', 'editar', 'eliminar'],
    'ventas': ['ver', 'registrar', 'editar', 'eliminar'],
    'graduaciones': ['ver', 'crear', 'editar'],
    'pacientes': ['ver', 'crear', 'editar', 'eliminar'],
    'reportes': ['ver', 'descargar'],
    # 'configuracion': NO incluir
}
# Resultado en la app:
# ✓ Acceso total a todo excepto Configuración


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ADMINISTRADOR (Acceso TOTAL)
# ═══════════════════════════════════════════════════════════════════════════════
# Puede: ABSOLUTAMENTE TODO
# No puede: Nada

ADMINISTRADOR = {
    'inventario': ['ver', 'crear', 'editar', 'eliminar'],
    'ventas': ['ver', 'registrar', 'editar', 'eliminar'],
    'graduaciones': ['ver', 'crear', 'editar'],
    'pacientes': ['ver', 'crear', 'editar', 'eliminar'],
    'reportes': ['ver', 'descargar'],
    'configuracion': ['ver', 'editar'],
}
# Resultado en la app:
# ✓ Acceso TOTAL a TODO


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CAJERO
# ═══════════════════════════════════════════════════════════════════════════════
# Puede: Registrar y ver ventas
# No puede: Crear/editar pacientes, tocar inventario

CAJERO = {
    'ventas': ['ver', 'registrar'],  # Registrar ventas y ver historial
    'pacientes': ['ver'],  # Solo ver (no crear ni editar)
}
# Resultado en la app:
# ✓ Botones: Ventas, Pacientes
# ✓ En Ventas: Crear y ver historial
# ✓ En Pacientes: Solo lectura


# ═══════════════════════════════════════════════════════════════════════════════
# ⚠️ EJEMPLOS INCORRECTOS (Evita estos patrones)
# ═══════════════════════════════════════════════════════════════════════════════

# ❌ INCORRECTO: Solo crear sin ver
INCORRECTO_1 = {
    'inventario': ['crear']  # Puede crear pero no ver?
}
# Problema: Botón NO aparecerá (falta 'ver')

# ❌ INCORRECTO: Editar sin ver
INCORRECTO_2 = {
    'ventas': ['editar', 'eliminar']  # Sin 'ver'
}
# Problema: Botón NO aparecerá (falta 'ver')

# ❌ INCORRECTO: Sin ningún permiso
INCORRECTO_3 = {}  # Vacío
# Problema: No aparecerá ningún botón (como se esperaría)


# ═══════════════════════════════════════════════════════════════════════════════
# JERARQUÍA SUGERIDA DE PERMISOS
# ═══════════════════════════════════════════════════════════════════════════════

"""
Para cada sección, la jerarquía sugerida es:

VER (lectura) → CREAR → EDITAR → ELIMINAR (destrucción)

En general, si tienes EDITAR, deberías tener VER.
Si tienes ELIMINAR, deberías tener EDITAR.

Ejemplos válidos:
✓ ['ver']                                      (solo lectura)
✓ ['ver', 'crear']                             (crear requiere ver)
✓ ['ver', 'crear', 'editar']                   (progresivo)
✓ ['ver', 'crear', 'editar', 'eliminar']       (acceso total)

Ejemplos inválidos (aunque técnicamente funcionan):
✗ ['crear'] sin ver                            (no puedes crear lo que no ves)
✗ ['editar'] sin ver                           (no puedes editar lo que no ves)
✗ ['eliminar'] sin editar                      (peligroso, sin restricción)
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CÓMO USAR ESTOS EJEMPLOS
# ═══════════════════════════════════════════════════════════════════════════════

"""
1. Abre VISO y ve a Configuración → Helpers
2. Haz clic en "Nuevo Ayudante"
3. Rellena datos básicos:
   - Nombre: Carlos Mendoza
   - Usuario: carlos
   - Contraseña: (segura)

4. En la sección "Permisos", selecciona las acciones:
   
   Para VENDEDOR JUNIOR:
   ☐ Inventario - Ver
   ☐ Inventario - Crear
   ☐ Inventario - Editar
   ☐ Inventario - Eliminar
   ☑ Ventas - Ver           ← MARCAR
   ☑ Ventas - Registrar     ← MARCAR
   ☐ Ventas - Editar
   ☐ Ventas - Eliminar
   ☑ Pacientes - Ver        ← MARCAR
   ☑ Pacientes - Crear      ← MARCAR
   ☐ Pacientes - Editar
   ☐ Pacientes - Eliminar
   ... (resto sin marcar)

5. Haz clic en "Guardar"

¡Listo! El ayudante tiene los permisos configurados.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# TABLA RÁPIDA DE REFERENCIA
# ═══════════════════════════════════════════════════════════════════════════════

"""
┌──────────────────────┬─────┬─────┬─────┬─────┬──────┬──────┐
│ Rol                  │ Ver │ Crear│ Edit│ Elim│ Informes│ Config│
├──────────────────────┼─────┼─────┼─────┼─────┼──────┼──────┤
│ Vendedor Junior      │  ✓  │     │     │     │      │      │
│ Asistente Inventario │  ✓  │     │  ✓  │     │  ✓  │      │
│ Optometrista Ast.    │  ✓  │  ✓  │  ✓  │     │      │      │
│ Reportero            │  ✓  │     │     │     │  ✓  │      │
│ Cajero               │  ✓  │  ✓  │     │     │      │      │
│ Gerente              │  ✓  │  ✓  │  ✓  │  ✓  │  ✓  │      │
│ Administrador        │  ✓  │  ✓  │  ✓  │  ✓  │  ✓  │  ✓  │
└──────────────────────┴─────┴─────┴─────┴─────┴──────┴──────┘

Notas:
- "Ver" es OBLIGATORIO para que aparezca la sección
- Si no tienes "Ver", el botón no aparecerá
- Las restricciones se aplican tanto en UI como en backend
"""
