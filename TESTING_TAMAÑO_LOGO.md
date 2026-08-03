# Testing Checklist: Control de Tamaño del Logo

## Pre-Testing Setup
- [ ] Asegurar que hay un logo cargado en Configuración → Plantilla
- [ ] Cerrar completamente VISO si está abierto
- [ ] Abrir VISO nuevamente

## Test 1: Carga Inicial del Tamaño
**Objetivo**: Verificar que el spinbox carga el valor guardado o default

- [ ] Abrir Configuración → Plantilla
- [ ] Verificar que el spinbox muestra 150 (default si es primera vez)
- [ ] Verificar que el slider está en la misma posición
- [ ] Verificar que el label dice "Tamaño actual: 150px"

**Resultado esperado**: Todos los controles sincronizados en 150px

---

## Test 2: Cambio Directo via Spinbox
**Objetivo**: Verificar que cambiar el spinbox funciona correctamente

- [ ] Hacer clic en el campo spinbox
- [ ] Cambiar valor a 200
- [ ] Presionar Tab o Enter
- [ ] Verificar que slider se movió a 200
- [ ] Verificar que preview label dice "Tamaño actual: 200px"

**Resultado esperado**: Todos se actualizan, sin errores

---

## Test 3: Cambio via Slider
**Objetivo**: Verificar que el slider funciona correctamente

- [ ] Hacer clic y arrastrar el slider hacia la derecha
- [ ] Soltar en aproximadamente 300px
- [ ] Verificar que spinbox cambió a ~300
- [ ] Verificar que preview label se actualizó

**Resultado esperado**: Spinbox y preview sincronizados con slider

---

## Test 4: Valores Límite (Mínimo)
**Objetivo**: Verificar que no permite valores menores a 50px

- [ ] Hacer clic en spinbox
- [ ] Borrar contenido y escribir: 30
- [ ] Presionar Tab
- [ ] Verificar que cambió a 50 (el mínimo permitido)

**Resultado esperado**: Automáticamente corregido a 50

---

## Test 5: Valores Límite (Máximo)
**Objetivo**: Verificar que no permite valores mayores a 400px

- [ ] Hacer clic en spinbox
- [ ] Borrar y escribir: 500
- [ ] Presionar Tab
- [ ] Verificar que cambió a 400 (el máximo permitido)

**Resultado esperado**: Automáticamente corregido a 400

---

## Test 6: Persistencia - Cierre y Reapertura
**Objetivo**: Verificar que el tamaño se guarda y se carga correctamente

**Pasos A**:
- [ ] Cambiar el spinbox a 250
- [ ] Cerrar la ventana de Configuración
- [ ] Cerrar completamente VISO
- [ ] Abrir VISO nuevamente
- [ ] Ir a Configuración → Plantilla

**Pasos B**:
- [ ] Verificar que spinbox muestra 250
- [ ] Verificar que slider está en 250
- [ ] Verificar que label dice "Tamaño actual: 250px"

**Resultado esperado**: Valor 250 se mantiene después de cerrar y reabrir

---

## Test 7: Generación de Boleta con Tamaño Pequeño
**Objetivo**: Verificar que el logo se vea pequeño en la boleta

- [ ] Ir a Configuración → Plantilla
- [ ] Establecer tamaño a 50px
- [ ] Cerrar Configuración
- [ ] Crear una venta de prueba
- [ ] En diálogo de venta, hacer clic en "Ver Boleta"
- [ ] Verificar que el logo aparece **muy pequeño** en la boleta PDF

**Resultado esperado**: Logo visible pero pequeño (~13mm)

---

## Test 8: Generación de Boleta con Tamaño Estándar
**Objetivo**: Verificar que el logo se vea normal con tamaño estándar

- [ ] Ir a Configuración → Plantilla
- [ ] Establecer tamaño a 150px
- [ ] Cerrar Configuración
- [ ] Crear otra venta de prueba
- [ ] En diálogo de venta, hacer clic en "Ver Boleta"
- [ ] Verificar que el logo aparece **de tamaño normal** en la boleta PDF

**Resultado esperado**: Logo visible y bien proporcionado (~40mm)

---

## Test 9: Generación de Boleta con Tamaño Grande
**Objetivo**: Verificar que el logo se vea grande en la boleta

- [ ] Ir a Configuración → Plantilla
- [ ] Establecer tamaño a 350px
- [ ] Cerrar Configuración
- [ ] Crear otra venta de prueba
- [ ] En diálogo de venta, hacer clic en "Ver Boleta"
- [ ] Verificar que el logo aparece **muy grande** en la boleta PDF

**Resultado esperado**: Logo visible y prominente (~92mm, casi máximo)

---

## Test 10: Descarga de Boleta
**Objetivo**: Verificar que descarga funciona con tamaño configurado

- [ ] Establecer tamaño a 200px
- [ ] Crear una venta
- [ ] En diálogo, hacer clic en "Descargar"
- [ ] Verificar que se descarga en Descargas
- [ ] Abrir PDF descargado
- [ ] Verificar que el logo tiene el tamaño correcto (200px)

**Resultado esperado**: PDF descargado con logo del tamaño correcto

---

## Test 11: Impresión de Boleta
**Objetivo**: Verificar que la impresión respeta el tamaño del logo

- [ ] Establecer tamaño a 180px
- [ ] Crear una venta
- [ ] En diálogo, hacer clic en "Imprimir"
- [ ] Seleccionar impresora (o "Print to File")
- [ ] Completar impresión
- [ ] Verificar que el logo imprime con tamaño correcto

**Resultado esperado**: Logo impreso con tamaño configurado

---

## Test 12: Múltiples Plantillas
**Objetivo**: Verificar que el tamaño funciona en todas las plantillas

**Para cada plantilla (pequeña, larga, extra-larga)**:
- [ ] Ir a Configuración → Plantilla → Seleccionar plantilla
- [ ] Establecer tamaño a 160px
- [ ] Crear una venta
- [ ] Generar boleta
- [ ] Verificar que el logo tiene tamaño consistente (160px en todas)

**Resultado esperado**: Logo del mismo tamaño en las 3 plantillas

---

## Test 13: Sincronización Spinbox-Slider
**Objetivo**: Verificar que ambos controles siempre están sincronizados

- [ ] Mover slider a posición aleatoria
- [ ] Verificar que spinbox cambió
- [ ] Cambiar spinbox a número diferente
- [ ] Verificar que slider se movió
- [ ] Repetir 5 veces con diferentes valores

**Resultado esperado**: Siempre sincronizados sin retrasos

---

## Test 14: Manejo de Errores - Logo Faltante
**Objetivo**: Verificar que funciona si no hay logo cargado

- [ ] Ir a Configuración → Plantilla
- [ ] Hacer clic en "Eliminar" (logo)
- [ ] Confirmar eliminación
- [ ] Cambiar tamaño a 200px
- [ ] Cerrar configuración
- [ ] Crear una venta
- [ ] Generar boleta
- [ ] Verificar que aparece placeholder gris (no errores)

**Resultado esperado**: Funciona correctamente sin logo, mostrando placeholder

---

## Test 15: Compatibilidad con Múltiples Usuarios
**Objetivo**: Verificar que cada usuario tiene su propio tamaño configurado

**Usuario A**:
- [ ] Login como Usuario A
- [ ] Configuración → Plantilla
- [ ] Establecer tamaño a 100px
- [ ] Logout

**Usuario B**:
- [ ] Login como Usuario B
- [ ] Configuración → Plantilla
- [ ] Verificar que muestra valor diferente (default 150 o anterior de Usuario B)
- [ ] Establecer tamaño a 300px
- [ ] Logout

**Usuario A (nuevamente)**:
- [ ] Login como Usuario A
- [ ] Configuración → Plantilla
- [ ] Verificar que muestra 100px (su configuración)

**Resultado esperado**: Cada usuario tiene su propia configuración independiente

---

## Test 16: Intervalo de Ticks del Slider
**Objetivo**: Verificar que los ticks marcan correctamente cada 50px

- [ ] Abrir Configuración → Plantilla
- [ ] Observar el slider
- [ ] Verificar que hay marcas (ticks) cada 50px
- [ ] Contar visualmente: debería haber 8 marcas (50, 100, 150, 200, 250, 300, 350, 400)

**Resultado esperado**: 8 ticks visibles espaciados uniformemente

---

## Test 17: Actualización en Tiempo Real
**Objetivo**: Verificar que el label se actualiza instantáneamente

- [ ] Hacer clic en el slider
- [ ] Arrastrar lentamente de un extremo al otro
- [ ] Observar que el label actualiza en cada movimiento
- [ ] No debe haber retrasos perceptibles

**Resultado esperado**: Preview label se actualiza al instante sin lag

---

## Test 18: Validación de Entrada - Caracteres Inválidos
**Objetivo**: Verificar que rechaza entrada no numérica

- [ ] Hacer clic en el spinbox
- [ ] Intentar escribir: "abc"
- [ ] Presionar Tab
- [ ] Verificar que mantiene valor anterior (no cambia a "abc")

**Resultado esperado**: Entrada rechazada, valor no cambia

---

## Test 19: Borrado de Valor
**Objetivo**: Verificar que no permite dejar el campo vacío

- [ ] Hacer clic en spinbox
- [ ] Seleccionar todo (Ctrl+A)
- [ ] Borrar (Delete/Backspace)
- [ ] Presionar Tab
- [ ] Verificar que se restaura a valor anterior

**Resultado esperado**: Campo no queda vacío

---

## Test 20: Archivo de Configuración
**Objetivo**: Verificar que el archivo se crea correctamente

- [ ] Abrir Explorador de Archivos
- [ ] Navegar a: `C:\Users\[tu-usuario]\AppData\Roaming\VISO\[tu-usuario]\`
- [ ] Verificar que existe archivo: `logo_config.json`
- [ ] Abrir con bloc de notas
- [ ] Verificar que contiene: `{"tamaño_logo": XXX}`

**Resultado esperado**: Archivo existe y contiene JSON válido

---

## Resumen de Resultados

| Test | Estado | Notas |
|------|--------|-------|
| 1    | [ ]    |       |
| 2    | [ ]    |       |
| 3    | [ ]    |       |
| 4    | [ ]    |       |
| 5    | [ ]    |       |
| 6    | [ ]    |       |
| 7    | [ ]    |       |
| 8    | [ ]    |       |
| 9    | [ ]    |       |
| 10   | [ ]    |       |
| 11   | [ ]    |       |
| 12   | [ ]    |       |
| 13   | [ ]    |       |
| 14   | [ ]    |       |
| 15   | [ ]    |       |
| 16   | [ ]    |       |
| 17   | [ ]    |       |
| 18   | [ ]    |       |
| 19   | [ ]    |       |
| 20   | [ ]    |       |

**Total Tests Pasados**: ___/20

---

## Criterios de Éxito

✅ **TODOS** los tests deben pasar sin excepciones
✅ Sin mensajes de error en la consola
✅ El logo debe ser visible en boletas con tamaño correcto
✅ La configuración debe persistir entre sesiones
✅ No debe haber lag o demoras en la interfaz
✅ Compatible con todas las plantillas de boleta

---

## Notas Adicionales

- Ejecutar en Windows 10/11
- Probar con pantallas de diferentes DPI (96 DPI, 125 DPI, 150 DPI)
- Probar con resoluciones: 1920x1080, 1366x768, 1024x768
- Usar diferentes tipos de logos (rectangular, cuadrado, vertical)

