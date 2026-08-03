# PERE.MD - Instrucciones finales obligatorias

Después de terminar todos los cambios solicitados, haz lo siguiente:

## 1. Revisión general obligatoria

Revisa que no hayas roto nada del flujo actual. No rediseñes toda la app. Solo cambios pequeños, directos y funcionales.

Prioridad:

* No cambiar nombres de botones innecesariamente.
* No cambiar diseño completo.
* No eliminar funciones existentes.
* No mover lógica sin necesidad.
* No crear archivos duplicados si se puede corregir el existente.

## 2. Validaciones específicas

Verifica punto por punto:

### Contratos en pacientes

* Los contratos deben filtrarse por la sucursal activa o seleccionada.
* Un usuario de una sucursal no debe ver contratos de otra sucursal, salvo que sea admin general.

### Revisión de deudas

* Corregir el lag.
* Revisar hilos, loops infinitos, cargas pesadas en UI y procesos bloqueantes.
* La ventana no debe congelarse al abrir.

### Selección de productos en ventas

* Optimizar la carga.
* Usar cache, lazy loading o búsqueda eficiente si aplica.
* No cargar todo innecesariamente si eso causa demora.

### Exportación de guía de remisión

* Corregir el límite de 10 filas.
* Debe exportar todas las filas reales de la guía.
* Probar con más de 10, 20 y 50 productos.

### Historial de ventas

* Mejorar solo la sección de días.
* Primero debe seleccionarse un mes desde una lista.
* Luego seleccionar un día perteneciente a ese mes.
* Desde ahí exportar ventas de ese día.
* No agregar botones de “hoy”, “ayer”, “mañana”.
* No cambiar demasiado la interfaz.

### Guía de remisión enviada a inventario

* Los productos deben entrar estrictamente a la sucursal destino correcta.
* Nunca deben irse a otra sucursal.
* Validar `sucursal_id`, nombre de sucursal y cualquier campo relacionado antes de guardar.
* Si falta sucursal destino, bloquear el envío y mostrar error claro.

## 3. Pruebas obligatorias

Antes de terminar, ejecutar pruebas manuales reales:

* Crear o usar una guía con más de 10 productos y exportarla.
* Enviar una guía al inventario de una sucursal específica y verificar que no aparezca en otra.
* Abrir revisión de deudas y confirmar que no se congele.
* Entrar a pacientes > contratos y confirmar filtro por sucursal.
* Abrir ventas y probar selección de productos.
* Exportar historial de ventas seleccionando primero mes y luego día.

## 4. Limpieza final

Al terminar:

* Eliminar prints/debugs innecesarios.
* No dejar código comentado basura.
* No crear documentación excesiva.
* Solo dejar un resumen corto en un archivo llamado `RESUMEN_CAMBIOS.md`.

 
 
Si algo no se pudo corregir, explicar claramente por qué y en qué archivo está el problema.

No inventes que algo funciona si no fue probado.



UNA VES TERMINADO ESE TRABAJO CONTINUA LEYENDO EL :    md2.md