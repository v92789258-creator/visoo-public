# Mejoras en el Diálogo de Citas - Selector de Pacientes

## Cambios Realizados

### 1. Nuevo Archivo: `gui/dialogs/paciente_selector_dialog.py`
Creado un diálogo profesional para seleccionar pacientes con las siguientes características:

**Características:**
- ✅ Ventana modal con lista completa de pacientes
- ✅ Buscador en tiempo real (busca por DNI, nombre, email)
- ✅ Información en tooltips (DNI, nombre, email, teléfono)
- ✅ Doble click para seleccionar rápidamente
- ✅ Estilos profesionales SaaS (diseño limpio, colores corporativos)
- ✅ Botones Cancelar/Seleccionar

**Clase Principal:**
```python
class PacienteSelectorDialog(QDialog)
```

### 2. Modificaciones: `gui/dialogs/appointment_dialog.py`

#### a) Nuevo QLineEdit personalizado
```python
class PacienteLineEdit(QLineEdit):
    """QLineEdit personalizado para almacenar datos del paciente"""
    - Método setData(dict): Guarda datos del paciente seleccionado
    - Método data(): Devuelve los datos almacenados
```

#### b) Cambio del input de pacientes
**Antes:** ComboBox editable con lista desplegable
**Ahora:** QLineEdit read-only clickeable que abre un diálogo

```python
# Nuevo comportamiento
self.dni_input = PacienteLineEdit()
self.dni_input.setReadOnly(True)
self.dni_input.setCursor(Qt.PointingHandCursor)
self.dni_input.mousePressEvent = self.abrir_selector_pacientes
```

#### c) Nuevos métodos
- `abrir_selector_pacientes(event)`: Abre el diálogo de selección
- `paciente_seleccionado(dni, nombre)`: Callback cuando se selecciona un paciente
- `cargar_pacientes()`: Carga la lista de pacientes disponibles

#### d) Estilos actualizados
Se agregaron estilos específicos para QLineEdit read-only:
```css
QLineEdit[readOnly="true"] {
    background-color: #FAFAFA;
    cursor: pointer;
}
QLineEdit[readOnly="true"]:hover {
    border: 1px solid #000000;
    background-color: #FFFFFF;
}
```

## Flujo de Uso

1. Usuario hace click en el campo "PACIENTE"
2. Se abre `PacienteSelectorDialog` modal
3. Usuario puede:
   - Escribir en el buscador (busca por DNI, nombre, email)
   - Ver tooltips con información completa
   - Hacer doble click para seleccionar
   - Click en "Seleccionar" después de elegir
   - Click en "Cancelar" para cerrar sin seleccionar
4. El paciente seleccionado aparece en el campo
5. Los datos se almacenan en `PacienteLineEdit._data`

## Ventajas

✅ **Mejor UX**: Vista completa de todos los pacientes
✅ **Búsqueda mejorada**: Filtra por DNI, nombre, email
✅ **Información visible**: Tooltips con datos completos
✅ **Selección más rápida**: Doble click para confirmar
✅ **Diseño profesional**: Estilos SaaS consistentes
✅ **Accesibilidad**: Interfaz clara y responsiva

## Archivos Modificados/Creados

1. ✅ Creado: `gui/dialogs/paciente_selector_dialog.py` (130 líneas)
2. ✅ Modificado: `gui/dialogs/appointment_dialog.py`
   - Agregada importación de `PacienteSelectorDialog`
   - Creada clase `PacienteLineEdit`
   - Actualizado método `init_ui()` 
   - Agregados métodos `abrir_selector_pacientes()`, `paciente_seleccionado()`
   - Actualizado método `cargar_datos()`
   - Actualizado método `guardar_cita()`
   - Actualizado `get_input_style()` con estilos para QLineEdit read-only

## Testing

Para probar:
1. Ejecutar `python main.py`
2. Ir a la página de Citas
3. Hacer click en "Crear Cita" o "Editar Cita"
4. Hacer click en el campo "PACIENTE"
5. Se debe abrir un diálogo con la lista de pacientes
6. Buscar/seleccionar un paciente
7. Verificar que aparezca en el campo

---
**Fecha de implementación:** 21/01/2026
**Estado:** ✅ Completo y funcional
