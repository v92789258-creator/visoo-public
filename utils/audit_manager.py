"""Sistema de auditoría para registrar cambios en la aplicación."""
import os
import json
import datetime
from pathlib import Path


class AuditManager:
    """Gestiona el registro de auditoría de cambios."""
    
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.audit_dir = os.path.join(base_dir, 'VISO', 'audit')
        os.makedirs(self.audit_dir, exist_ok=True)
        self.audit_file = os.path.join(self.audit_dir, 'audit.jsonl')
    
    def log_action(self, user_id, username, helper_name, action, module, details):
        """
        Registra una acción en la auditoría.
        
        Args:
            user_id: ID del usuario principal
            username: Nombre del usuario
            helper_name: Nombre del ayudante (si aplica)
            action: Tipo de acción (crear, editar, eliminar, etc)
            module: Módulo donde ocurrió (inventario, pacientes, etc)
            details: Detalles de la acción
        """
        try:
            actor = helper_name if helper_name else username
            actor_type = "Ayudante" if helper_name else "Usuario"
            
            record = {
                "timestamp": datetime.datetime.now().isoformat(),
                "user_id": str(user_id),
                "username": username,
                "actor": actor,
                "actor_type": actor_type,
                "action": action,
                "module": module,
                "details": details
            }
            
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                
            return True
        except Exception as e:
            print(f"[AUDIT] Error al registrar acción: {e}")
            return False
    
    def get_audit_log(self, limit=500, user_id=None, module=None):
        """
        Obtiene el registro de auditoría.
        
        Args:
            limit: Número máximo de registros a retornar
            user_id: Filtrar por user_id (opcional)
            module: Filtrar por módulo (opcional)
        
        Returns:
            Lista de registros de auditoría (más recientes primero)
        """
        records = []
        
        if not os.path.exists(self.audit_file):
            return records
        
        try:
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        
                        if user_id and record.get('user_id') != str(user_id):
                            continue
                        if module and record.get('module') != module:
                            continue
                        
                        records.append(record)
            
            records.reverse()
            return records[:limit]
        
        except Exception as e:
            print(f"[AUDIT] Error al leer log: {e}")
            return []
    
    def export_audit_log(self, output_file, user_id=None, module=None):
        """Exporta el registro de auditoría a un archivo CSV."""
        import csv
        
        records = self.get_audit_log(limit=10000, user_id=user_id, module=module)
        
        if not records:
            return False
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['timestamp', 'username', 'actor', 'actor_type', 'action', 'module', 'details']
                )
                writer.writeheader()
                
                for record in records:
                    writer.writerow({
                        'timestamp': record.get('timestamp', ''),
                        'username': record.get('username', ''),
                        'actor': record.get('actor', ''),
                        'actor_type': record.get('actor_type', ''),
                        'action': record.get('action', ''),
                        'module': record.get('module', ''),
                        'details': str(record.get('details', ''))
                    })
            
            return True
        except Exception as e:
            print(f"[AUDIT] Error al exportar: {e}")
            return False
    
    def get_stats(self, user_id=None):
        """Obtiene estadísticas de auditoría."""
        records = self.get_audit_log(limit=10000, user_id=user_id)
        
        stats = {
            'total_acciones': len(records),
            'acciones_por_actor': {},
            'acciones_por_modulo': {},
            'acciones_por_tipo': {}
        }
        
        for record in records:
            actor = record.get('actor', 'desconocido')
            module = record.get('module', 'desconocido')
            action = record.get('action', 'desconocido')
            
            stats['acciones_por_actor'][actor] = stats['acciones_por_actor'].get(actor, 0) + 1
            stats['acciones_por_modulo'][module] = stats['acciones_por_modulo'].get(module, 0) + 1
            stats['acciones_por_tipo'][action] = stats['acciones_por_tipo'].get(action, 0) + 1
        
        return stats


# Instancia global para usar en toda la app
audit_manager = None

def init_audit_manager(base_dir):
    """Inicializa el gestor de auditoría."""
    global audit_manager
    audit_manager = AuditManager(base_dir)
    return audit_manager
