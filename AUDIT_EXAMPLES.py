"""Ejemplos de cómo integrar auditoría en diferentes módulos."""

def ejemplo_crear_producto(app_instance, username, helper_name, product_data):
    """Ejemplo: Registrar creación de producto."""
    try:
        # ... código para crear producto ...
        
        app_instance.audit_manager.log_action(
            user_id=app_instance.main_window.user_id,
            username=username,
            helper_name=helper_name,
            action='crear',
            module='inventario',
            details=f"Producto creado: {product_data.get('nombre')} (SKU: {product_data.get('sku')})"
        )
    except Exception as e:
        print(f"Error: {e}")


def ejemplo_editar_producto(app_instance, username, helper_name, product_id, cambios):
    """Ejemplo: Registrar edición de producto."""
    try:
        # ... código para editar producto ...
        
        cambios_str = ", ".join([f"{k}: {v}" for k, v in cambios.items()])
        app_instance.audit_manager.log_action(
            user_id=app_instance.main_window.user_id,
            username=username,
            helper_name=helper_name,
            action='editar',
            module='inventario',
            details=f"Producto {product_id} editado: {cambios_str}"
        )
    except Exception as e:
        print(f"Error: {e}")


def ejemplo_eliminar_producto(app_instance, username, helper_name, product_id, product_name):
    """Ejemplo: Registrar eliminación de producto."""
    try:
        # ... código para eliminar producto ...
        
        app_instance.audit_manager.log_action(
            user_id=app_instance.main_window.user_id,
            username=username,
            helper_name=helper_name,
            action='eliminar',
            module='inventario',
            details=f"Producto eliminado: {product_name} (ID: {product_id})"
        )
    except Exception as e:
        print(f"Error: {e}")


def ejemplo_crear_venta(app_instance, username, helper_name, venta_data):
    """Ejemplo: Registrar creación de venta."""
    try:
        # ... código para crear venta ...
        
        app_instance.audit_manager.log_action(
            user_id=app_instance.main_window.user_id,
            username=username,
            helper_name=helper_name,
            action='crear',
            module='ventas',
            details=f"Venta creada - Monto: {venta_data.get('total')}, Paciente: {venta_data.get('paciente')}"
        )
    except Exception as e:
        print(f"Error: {e}")


def ejemplo_crear_paciente(app_instance, username, helper_name, patient_data):
    """Ejemplo: Registrar creación de paciente."""
    try:
        # ... código para crear paciente ...
        
        app_instance.audit_manager.log_action(
            user_id=app_instance.main_window.user_id,
            username=username,
            helper_name=helper_name,
            action='crear',
            module='pacientes',
            details=f"Paciente creado: {patient_data.get('nombre')} - {patient_data.get('dni')}"
        )
    except Exception as e:
        print(f"Error: {e}")


def ejemplo_crear_ayudante(app_instance, username, helper_data):
    """Ejemplo: Registrar creación de ayudante."""
    try:
        # ... código para crear ayudante ...
        
        app_instance.audit_manager.log_action(
            user_id=app_instance.main_window.user_id,
            username=username,
            helper_name=None,
            action='crear',
            module='ayudantes',
            details=f"Ayudante creado: {helper_data.get('username')} - Módulos: {', '.join(helper_data.get('modulos', []))}"
        )
    except Exception as e:
        print(f"Error: {e}")


def ejemplo_cambiar_permisos_ayudante(app_instance, username, helper_name, new_permissions):
    """Ejemplo: Registrar cambio de permisos de ayudante."""
    try:
        # ... código para cambiar permisos ...
        
        perms_str = ", ".join([f"{k}: {v}" for k, v in new_permissions.items()])
        app_instance.audit_manager.log_action(
            user_id=app_instance.main_window.user_id,
            username=username,
            helper_name=None,
            action='editar',
            module='ayudantes',
            details=f"Permisos de {helper_name} modificados: {perms_str}"
        )
    except Exception as e:
        print(f"Error: {e}")


# Integración en el código real:
# 
# En inventory_page.py al guardar un producto:
#     app_instance.audit_manager.log_action(
#         user_id=self.main_window.user_id,
#         username=self.main_window.username,
#         helper_name=self.main_window.helper_name if hasattr(self.main_window, 'is_helper') else None,
#         action='crear',
#         module='inventario',
#         details=f"Producto: {product_name}"
#     )
#
# En helpers_page.py al crear/editar ayudante:
#     app_instance.audit_manager.log_action(
#         user_id=self.main_window.user_id,
#         username=self.main_window.username,
#         helper_name=None,
#         action='crear',
#         module='ayudantes',
#         details=f"Ayudante: {helper_name}"
#     )
