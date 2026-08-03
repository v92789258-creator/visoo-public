"""Sistema de instancia única"""
import os
import logging
from contextlib import contextmanager

from core.config.settings import TEMP_DIR
from core.exceptions import SingleInstanceError

logger = logging.getLogger(__name__)

@contextmanager
def single_instance():
    """
    Sistema de instancia única usando archivo lock.
    Garantiza que solo una instancia de VISO se ejecute.
    """
    lock_file = os.path.join(TEMP_DIR, '.viso.lock')
    lock_acquired = False
    
    try:
        # Intentar crear archivo lock exclusivo
        try:
            lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, f"{os.getpid()}".encode())
            os.close(lock_fd)
            lock_acquired = True
            logger.info("✅ Instancia única adquirida")
        
        except FileExistsError:
            # Verificar si el proceso anterior aún está activo
            if _is_previous_instance_active(lock_file):
                logger.warning("⚠️ VISO ya está en ejecución")
                lock_acquired = False
            else:
                # Proceso anterior no está activo, limpiar y reclamar lock
                try:
                    os.remove(lock_file)
                    lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(lock_fd, f"{os.getpid()}".encode())
                    os.close(lock_fd)
                    lock_acquired = True
                    logger.info("✅ Proceso anterior inactivo, instancia única adquirida")
                except Exception as e:
                    logger.error(f"❌ No se pudo adquirir lock: {e}")
                    lock_acquired = False
        
        yield lock_acquired
    
    except Exception as e:
        logger.error(f"❌ Error en single_instance: {e}")
        yield False
    
    finally:
        # Limpiar lock
        if lock_acquired:
            try:
                os.remove(lock_file)
            except Exception:
                pass

def _is_previous_instance_active(lock_file):
    """Verifica si el proceso del lock anterior aún está activo"""
    import sys
    
    try:
        with open(lock_file, 'r') as f:
            old_pid_str = f.read().strip()
            if not old_pid_str:
                return False
            
            old_pid = int(old_pid_str)
            
            # En Windows, usar tasklist
            if sys.platform == 'win32':
                try:
                    import subprocess
                    result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {old_pid}'],
                        capture_output=True, text=True, timeout=2
                    )
                    return f"{old_pid}" in result.stdout
                except Exception:
                    return False
            else:
                # En Linux/Mac, usar /proc
                return os.path.exists(f'/proc/{old_pid}')
    
    except Exception:
        return False
