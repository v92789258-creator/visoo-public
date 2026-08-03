"""
SYNC MANAGER - Sistema de sincronizaciÃ³n offline-first CON LOGS
- Guarda cambios localmente si no hay internet
- Sincroniza automÃ¡ticamente cuando hay conexiÃ³n
- Logs detallados en consola de cada cambio
- [NUEVO] RecuperaciÃ³n de inventario remoto si falta el local
"""

import os
import json
import sqlite3
import hashlib
import requests
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import threading
import time
from utils.runtime_status import tracked_operation

# ConfiguraciÃ³n
DB_PATH = Path(__file__).parent.parent / "VISO" / ".sync_queue.db"
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos

# LOCK GLOBAL para evitar "database is locked" con mÃºltiples threads
_DB_LOCK = threading.RLock()
_DB_LOCK_TIMEOUT = 10  # segundos

# THROTTLING para evitar mÃºltiples requests HTTP simultÃ¡neos
_HTTP_REQUEST_LOCK = threading.Semaphore(1)  # Solo 1 request HTTP a la vez
_LAST_SYNC_TIME = 0  # Para throttle entre syncs
_MIN_SYNC_INTERVAL = 30  # MÃ­nimo 30 segundos entre syncs (optimizado para internet)
_INTERNET_CHECK_LOCK = threading.Lock()
_LAST_INTERNET_CHECK_TS = 0.0
_LAST_INTERNET_CHECK_RESULT = None
_MIN_INTERNET_CHECK_INTERVAL = 20.0

# Datasets que se sincronizan en modo "carpeta" hacia upload_device_snapshot.php
FOLDER_SYNC_DATASETS = (
    "clientes",
    "pacientes",
    "productos",
    "ventas",
    "kardex",
    "citas",
    "servicios",
    "metodos_pago",
    "graduaciones",
    "optometras",
    "marcas",
    "brands",
    "config_optica",
    # Datos administrativos/configuracion adicional
    "dispositivos_hijos",
    "config_dispositivo",
    "datos_generales",
    "ayudantes",
)

# Datasets criticos para decidir si una instalacion "realmente tiene datos"
# antes de permitir un respaldo inicial hacia la nube.
INITIAL_SYNC_GUARD_DATASETS = (
    "clientes",
    "pacientes",
    "productos",
    "graduaciones",
)

SYNC_CENTER_DATASETS = (
    "clientes",
    "pacientes",
    "productos",
    "ventas",
)

SYNC_CENTER_DATASET_LABELS = {
    "clientes": "Clientes",
    "pacientes": "Pacientes",
    "productos": "Productos",
    "ventas": "Ventas",
}


def _log(msg: str):
    """Log con timestamp - ASCII only para Windows - CON FLUSH"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    replacements = {
        '📝': '*',
        '➕': '+',
        '📤': '^',
        '📥': '[DOWN]',
        '🔌': '[OFFLINE]',
        '⏱️': '[TIMEOUT]',
        '⚠️': '[WARN]',
        '🔄': '[SYNC]',
        '📊': '[RESULT]',
        '⏹️': '[STOP]',
        '✅': 'OK',
        '❌': 'XX',
        '✓': 'OK',
        '✗': 'XX',
        '→': '->',
        # Variantes mojibake observadas en runtime
        'ðŸ“': '*',
        'âž•': '+',
        'ðŸ“¤': '^',
        'âœ…': 'OK',
        'âŒ': 'XX',
        'ðŸ”Œ': '[OFFLINE]',
        'â±ï¸': '[TIMEOUT]',
        'âš ï¸': '[WARN]',
        'ðŸ”„': '[SYNC]',
        'ðŸ“Š': '[RESULT]',
        'â¹ï¸': '[STOP]',
        'ðŸ“¥': '[DOWN]',
        'â†’': '->',
    }

    msg_ascii = str(msg)
    for src, dst in replacements.items():
        msg_ascii = msg_ascii.replace(src, dst)

    line = f"[{timestamp}] [SYNC] {msg_ascii}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode('ascii', errors='replace').decode('ascii'), flush=True)


class SyncQueue:
    """Gestiona la cola de cambios pendientes de sincronizar"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self, timeout: int = _DB_LOCK_TIMEOUT):
        """Obtiene conexiÃ³n a SQLite con reintentos y timeout"""
        conn = sqlite3.connect(self.db_path, timeout=timeout, check_same_thread=False)
        conn.isolation_level = None  # Autocommit mode
        conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging para concurrencia
        return conn
    
    def _init_db(self):
        """Crea la tabla de cola si no existe"""
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sync_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id TEXT NOT NULL,
                        tipo_dato TEXT NOT NULL,
                        operacion TEXT NOT NULL,
                        registro_id TEXT,
                        contenido TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        estado TEXT DEFAULT 'pendiente',
                        intentos INTEGER DEFAULT 0,
                        ultimo_error TEXT,
                        UNIQUE(usuario_id, tipo_dato, registro_id, timestamp)
                    )
                ''')
                
                conn.commit()
                conn.close()
            except Exception as e:
                _log(f"âŒ Error inicializando DB: {e}")
    
    def add_to_queue(self, usuario_id: str, tipo_dato: str, operacion: str, 
                     registro_id: str, contenido: Dict[str, Any]) -> bool:
        """Agrega un cambio a la cola de sincronizaciÃ³n"""
        # âš ï¸âš ï¸ PROTECCIÃ“N CRÃTICA: BLOQUEAR COMPLETAMENTE SYNC_ALL de productos
        # RazÃ³n: El endpoint PHP sync_data_inv.php tiene un bug donde SYNC_ALL reemplaza/vacÃ­a datos
        # SoluciÃ³n: Siempre usar CREATE/UPDATE individuales
        try:
            if tipo_dato == 'productos' and operacion == 'SYNC_ALL':
                _log(f"â›” [BLOQUEO] SYNC_ALL de productos BLOQUEADO COMPLETAMENTE (endpoint PHP tiene bug conocido)")
                
                # Intentar convertir a CREATE individuales
                if isinstance(contenido, dict) and contenido.get('productos'):
                    productos = contenido.get('productos') or []
                    if productos and isinstance(productos, list) and len(productos) > 0:
                        _log(f"âš ï¸ [CONVERT] Convirtiendo {len(productos)} items a CREATE individuales (por seguridad)")
                        converted = 0
                        for prod in productos:
                            try:
                                if not isinstance(prod, dict):
                                    continue
                                nombre = prod.get('nombre')
                                registro = nombre or prod.get('id') or ''
                                # Insertar CREATE individual (evita recursiÃ³n porque no es SYNC_ALL)
                                conn = self._get_connection()
                                cursor = conn.cursor()
                                ts = int(time.time())
                                contenido_json = json.dumps(prod, default=str)
                                cursor.execute('''
                                    INSERT OR IGNORE INTO sync_queue (usuario_id, tipo_dato, operacion, registro_id, contenido, timestamp)
                                    VALUES (?, 'productos', 'CREATE', ?, ?, ?)
                                ''', (usuario_id, registro or '', contenido_json, ts))
                                conn.commit()
                                conn.close()
                                converted += 1
                            except Exception as e:
                                _log(f"  âš ï¸ Error convirtiendo item: {e}")
                                pass
                        _log(f"âœ… [CONVERT] {converted} items encolados como CREATE (SYNC_ALL rechazado)")
                        return True
                
                # Si no hay contenido vÃ¡lido, simplemente rechazar
                _log(f"â›” [BLOQUEO] SYNC_ALL vacÃ­o o sin estructura vÃ¡lida - rechazado")
                return False
        except Exception as e:
            _log(f"Error en protecciÃ³n SYNC_ALL: {e}")
            pass
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                timestamp = int(time.time())
                contenido_json = json.dumps(contenido, default=str)
                
                cursor.execute('''
                    INSERT INTO sync_queue 
                    (usuario_id, tipo_dato, operacion, registro_id, contenido, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (usuario_id, tipo_dato, operacion, registro_id or '', contenido_json, timestamp))
                
                conn.commit()
                conn.close()
                
                _log(f"âž• Agregado a cola: {tipo_dato} ({operacion})")
                return True
            except sqlite3.IntegrityError:
                return True
            except Exception as e:
                _log(f"âŒ Error al agregar a cola: {e}")
                return False
    
    def get_pending_items(self, usuario_id: str, limit: int = 100) -> List[Dict]:
        """Obtiene los items pendientes de sincronizaciÃ³n"""
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM sync_queue 
                    WHERE usuario_id = ? AND estado = 'pendiente'
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (usuario_id, limit))
                
                items = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                for item in items:
                    try:
                        item['contenido'] = json.loads(item['contenido'])
                    except:
                        pass
                return items
            except Exception as e:
                print(f"Error obteniendo items pendientes: {e}")
                return []
    

    def clear_pending_sync_all_for_dataset(self, usuario_id: str, tipo_dato: str, registro_id: str = "") -> int:
        """Elimina SYNC_ALL pendientes/erroneos previos para el mismo usuario+dataset+registro_id."""
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM sync_queue
                    WHERE usuario_id = ?
                      AND tipo_dato = ?
                      AND operacion = 'SYNC_ALL'
                      AND registro_id = ?
                      AND estado IN ('pendiente', 'error')
                    """,
                    (str(usuario_id), str(tipo_dato), str(registro_id or "")),
                )
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                return int(deleted or 0)
            except Exception:
                return 0

    def mark_synced(self, queue_id: int, respuesta_servidor: str = None):
        """Marca un item como sincronizado"""
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE sync_queue SET estado = 'sincronizado', ultimo_error = NULL WHERE id = ?",
                    (queue_id,)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                _log(f"âŒ Error marcando como sincronizado: {e}")
    
    def mark_error(self, queue_id: int, error_msg: str):
        """Marca un item con error"""
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sync_queue 
                    SET intentos = intentos + 1, 
                        ultimo_error = ?,
                        estado = CASE WHEN intentos >= ? THEN 'error' ELSE 'pendiente' END
                    WHERE id = ?
                ''', (error_msg, MAX_RETRIES - 1, queue_id))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error marcando error: {e}")

    def clear_product_deletes(self, usuario_id: str):
        """âš ï¸ Limpia todos los DELETE pendientes de productos (seguridad)"""
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM sync_queue 
                    WHERE usuario_id = ? AND tipo_dato = 'productos' AND operacion = 'DELETE'
                    AND estado IN ('pendiente', 'error')
                ''', (usuario_id,))
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                return deleted_count
            except Exception as e:
                print(f"Error limpiando DELETE de productos: {e}")
                return 0

    def clear_sync_all_pending(self, usuario_id: str):
        """Elimina SYNC_ALL pendientes SOLO de productos (protecciÃ³n)."""
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM sync_queue
                    WHERE usuario_id = ? AND operacion = 'SYNC_ALL' AND tipo_dato = 'productos' AND estado IN ('pendiente', 'error')
                ''', (usuario_id,))
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                return deleted_count
            except Exception as e:
                print(f"Error limpiando SYNC_ALL pendientes: {e}")
                return 0

    def clear_empty_sync_all_pending(self, usuario_id: str):
        """Elimina SYNC_ALL pendientes de productos cuyo contenido estÃ© vacÃ­o.

        Scanea items pendientes SYNC_ALL y elimina aquellos cuyo `contenido`
        no tenga la clave 'productos' o tenga lista vacÃ­a.
        """
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, contenido FROM sync_queue
                    WHERE usuario_id = ? AND operacion = 'SYNC_ALL' AND tipo_dato = 'productos' AND estado IN ('pendiente', 'error')
                ''', (usuario_id,))
                rows = cursor.fetchall()

                to_delete = []
                for row in rows:
                    try:
                        contenido = json.loads(row['contenido']) if row['contenido'] else {}
                        productos = contenido.get('productos') if isinstance(contenido, dict) else None
                        if not productos:
                            to_delete.append(row['id'])
                    except Exception:
                        # Si no podemos decodificar, no tocar (no asumimos borrado)
                        pass

                deleted = 0
                if to_delete:
                    placeholders = ','.join('?' for _ in to_delete)
                    cursor.execute(f"DELETE FROM sync_queue WHERE id IN ({placeholders})", tuple(to_delete))
                    deleted = cursor.rowcount
                    conn.commit()

                conn.close()
                return deleted
            except Exception as e:
                _log(f"Error limpiando SYNC_ALL vacÃ­os: {e}")
                return 0

    def convert_pending_sync_all_to_creates(self, usuario_id: str) -> int:
        """Convierte SYNC_ALL pendientes en CREATE individuales y elimina los SYNC_ALL originales."""
        with _DB_LOCK:
            try:
                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, contenido FROM sync_queue
                    WHERE usuario_id = ? AND operacion = 'SYNC_ALL' AND tipo_dato = 'productos' AND estado IN ('pendiente', 'error')
                ''', (usuario_id,))
                rows = cursor.fetchall()

                total_converted = 0
                to_delete = []
                for row in rows:
                    try:
                        contenido = json.loads(row['contenido']) if row['contenido'] else {}
                        productos = contenido.get('productos') if isinstance(contenido, dict) else None
                        if productos and isinstance(productos, list):
                            for prod in productos:
                                try:
                                    registro = prod.get('nombre') if isinstance(prod, dict) else ''
                                    ts = int(time.time())
                                    contenido_json = json.dumps(prod, default=str)
                                    cursor.execute('''
                                        INSERT OR IGNORE INTO sync_queue (usuario_id, tipo_dato, operacion, registro_id, contenido, timestamp)
                                        VALUES (?, 'productos', 'CREATE', ?, ?, ?)
                                    ''', (usuario_id, registro or '', contenido_json, ts))
                                    total_converted += 1
                                except Exception:
                                    pass
                            to_delete.append(row['id'])
                    except Exception:
                        pass

                if to_delete:
                    placeholders = ','.join('?' for _ in to_delete)
                    cursor.execute(f"DELETE FROM sync_queue WHERE id IN ({placeholders})", tuple(to_delete))
                    conn.commit()

                conn.close()
                if total_converted:
                    _log(f"âš ï¸ [CONVERT] Convertidos {total_converted} items desde SYNC_ALL pendientes a CREATE individuales")
                return total_converted
            except Exception as e:
                _log(f"Error convertiendo SYNC_ALL pendientes: {e}")
                return 0


class SyncManager:
    """Gestor principal de sincronizaciÃ³n"""
    
    def __init__(self):
        self.queue = SyncQueue()
        self._sync_thread = None
        self._running = False
    
    def queue_change(self, usuario_id: str, tipo_dato: str, operacion: str,
                     registro_id: str, contenido: Dict[str, Any]) -> bool:
        """Agrega un cambio a la cola de sync"""
        return self.queue.add_to_queue(usuario_id, tipo_dato, operacion, 
                                       registro_id, contenido)
    
    @staticmethod
    def check_internet(force: bool = False) -> bool:
        """
        Verifica conectividad real con reintentos.
        Evita falsos negativos cuando Google falla pero la API propia esta accesible.
        """
        global _LAST_INTERNET_CHECK_TS, _LAST_INTERNET_CHECK_RESULT

        now = time.time()
        with _INTERNET_CHECK_LOCK:
            cached_result = _LAST_INTERNET_CHECK_RESULT
            cached_age = now - float(_LAST_INTERNET_CHECK_TS or 0.0)
            if (not force) and cached_result is not None and cached_age < _MIN_INTERNET_CHECK_INTERVAL:
                return bool(cached_result)

        targets = (
            "https://api.yhana.cloud/win/new/upload_device_snapshot.php",
            "https://api.yhana.cloud/win/new/download_device_snapshot.php",
            "https://www.google.com/generate_204",
        )

        # Este metodo se llama desde varias pantallas. Con internet lento, varios
        # intentos largos hacen que la UI parezca congelada; preferimos fallar
        # rapido y dejar que el siguiente refresco vuelva a intentar.
        max_attempts = 1
        timeout = 1.2
        last_error = None

        for attempt in range(max_attempts):
            for url in targets:
                try:
                    # Cualquier respuesta HTTP implica conectividad (incluso 4xx/5xx).
                    resp = requests.head(url, timeout=timeout, allow_redirects=True)
                    _ = resp.status_code
                    try:
                        resp.close()
                    except Exception:
                        pass
                    with _INTERNET_CHECK_LOCK:
                        _LAST_INTERNET_CHECK_TS = time.time()
                        _LAST_INTERNET_CHECK_RESULT = True
                    return True
                except Exception as err_head:
                    last_error = err_head
                    try:
                        resp = requests.get(url, timeout=timeout, stream=True)
                        _ = resp.status_code
                        try:
                            resp.close()
                        except Exception:
                            pass
                        with _INTERNET_CHECK_LOCK:
                            _LAST_INTERNET_CHECK_TS = time.time()
                            _LAST_INTERNET_CHECK_RESULT = True
                        return True
                    except Exception as err_get:
                        last_error = err_get

            # Backoff corto para nuevos intentos
            time.sleep(0.35 * (attempt + 1))

        try:
            _log(f"[NET] check_internet fallo tras {max_attempts} intentos: {last_error}")
        except Exception:
            pass
        with _INTERNET_CHECK_LOCK:
            _LAST_INTERNET_CHECK_TS = time.time()
            _LAST_INTERNET_CHECK_RESULT = False
        return False

    def _is_missing_snapshot_message(self, message: str) -> bool:
        text = str(message or "").strip().lower()
        if not text:
            return False
        markers = (
            "device snapshot folder not found",
            "dataset not found",
            "snapshot folder not found",
            "snapshot not found",
            "folder not found",
        )
        return any(marker in text for marker in markers)

    def _extract_productos_from_snapshot_payload(self, payload: Any) -> Optional[List[Dict]]:
        if not isinstance(payload, dict):
            return None

        data = payload.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            maybe = data.get("productos")
            if isinstance(maybe, list):
                return maybe

        snapshot = payload.get("snapshot")
        if isinstance(snapshot, dict):
            maybe = snapshot.get("productos")
            if isinstance(maybe, list):
                return maybe

        return None

    def _download_remote_inventory_for_code(
        self,
        usuario_madre: str,
        branch_code: str,
    ) -> Optional[List[Dict]]:
        branch_code = str(branch_code or "").strip().upper()
        if not branch_code:
            return None

        try:
            from utils.api_handler import descargar_snapshot_dispositivo_nube

            ok_meta, payload_meta, msg_meta = descargar_snapshot_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset=None,
                include_data=False,
            )
            if ok_meta and isinstance(payload_meta, dict):
                ds_list = payload_meta.get("datasets") or []
                has_productos = False
                if isinstance(ds_list, list):
                    for ds in ds_list:
                        if not isinstance(ds, dict):
                            continue
                        name = str(ds.get("dataset") or ds.get("name") or "").strip().lower()
                        if name == "productos":
                            has_productos = True
                            break
                if not has_productos:
                    _log(
                        "Inventario snapshot: dataset 'productos' aun no existe "
                        f"(sucursal={branch_code})"
                    )
                    return []
            elif self._is_missing_snapshot_message(msg_meta):
                _log(
                    "Inventario snapshot: folder remoto aun no existe "
                    f"(sucursal={branch_code})"
                )
                return []
            else:
                _log(
                    "No se pudo consultar resumen snapshot de inventario "
                    f"(sucursal={branch_code}): {msg_meta}"
                )
                return None

            ok, payload, msg = descargar_snapshot_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset="productos",
                include_data=True,
            )
            if ok and isinstance(payload, dict):
                productos = self._extract_productos_from_snapshot_payload(payload)
                if isinstance(productos, list):
                    _log(
                        f"Inventario snapshot descargado: {len(productos)} productos "
                        f"(sucursal={branch_code})"
                    )
                    return productos

            if self._is_missing_snapshot_message(msg):
                _log(
                    "Inventario snapshot: dataset 'productos' aun no existe "
                    f"(sucursal={branch_code})"
                )
                return []

            _log(
                f"Snapshot de inventario no disponible para sucursal {branch_code}: {msg}"
            )
            return None
        except Exception as snapshot_err:
            _log(f"Error consultando snapshot por sucursal: {snapshot_err}")
            return None

    def _download_global_inventory_snapshots(
        self,
        resolved_username: str,
        usuario_madre: str,
    ) -> Optional[List[Dict]]:
        """
        Restaura inventario global desde snapshots cloud:
        - Primero la sucursal madre (MADRE-USER)
        - Luego todas las sucursales activas/listadas
        Guarda cada dataset en branch_cache y retorna el consolidado.
        """
        try:
            from utils.api_handler import listar_dispositivos_hijos_remoto, listar_snapshots_dispositivos_nube
            from utils.file_handler import (
                get_user_file_path,
                save_branch_snapshot_datasets,
                clear_branch_runtime_caches,
                _load_consolidated_branch_list_dataset,
            )
        except Exception as e:
            _log(f"No se pudo preparar restore global de inventario: {e}")
            return None

        inspected_any = False
        restored_any = False
        candidate_codes: List[str] = []

        def _add_code(value: Any) -> None:
            code = str(value or "").strip().upper()
            if code and code not in candidate_codes:
                candidate_codes.append(code)

        try:
            base = re.sub(r"[^A-Za-z0-9]+", "", str(resolved_username).upper()) or "USER"
            _add_code(f"MADRE-{base}"[:80])
        except Exception:
            pass

        try:
            cfg_path = get_user_file_path(resolved_username, "config_dispositivo.json")
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if isinstance(cfg, dict):
                    _add_code(cfg.get("codigo_dispositivo"))
        except Exception:
            pass

        for code_try in list(candidate_codes):
            productos = self._download_remote_inventory_for_code(usuario_madre, code_try)
            if productos is None:
                continue
            inspected_any = True
            try:
                save_branch_snapshot_datasets(resolved_username, code_try, {"productos": productos})
            except Exception:
                pass
            if productos:
                restored_any = True

        ok, devices, _msg = listar_dispositivos_hijos_remoto(usuario_madre)
        if not ok or not isinstance(devices, list) or not devices:
            try:
                ok_s, snap_devices, _msg_s = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
                if ok_s and isinstance(snap_devices, list) and snap_devices:
                    ok, devices = True, snap_devices
            except Exception:
                pass

        if ok and isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                if str(device.get("estado", "activo")).strip().lower() == "bloqueado":
                    continue
                code = str(device.get("codigo_dispositivo", "")).strip().upper()
                if not code or code in candidate_codes:
                    continue
                candidate_codes.append(code)
                productos = self._download_remote_inventory_for_code(usuario_madre, code)
                if productos is None:
                    continue
                inspected_any = True
                try:
                    save_branch_snapshot_datasets(resolved_username, code, {"productos": productos})
                except Exception:
                    pass
                if productos:
                    restored_any = True

        if not inspected_any:
            return None

        try:
            clear_branch_runtime_caches()
        except Exception:
            pass

        try:
            merged = _load_consolidated_branch_list_dataset(
                resolved_username,
                "productos.json",
                include_local=False,
            )
            if isinstance(merged, list):
                _log(
                    f"Inventario global restaurado desde snapshots: {len(merged)} productos "
                    f"(codes={','.join(candidate_codes)})"
                )
                return merged
        except Exception as e:
            _log(f"Error consolidando inventario global restaurado: {e}")

        return [] if restored_any else []

    def download_remote_inventory(
        self,
        usuario_id: str,
        target_branch_code: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Descarga inventario remoto de forma segura.
        Prioridad:
        1) Snapshot por sucursal activa (/win/new/download_device_snapshot.php)
        2) Endpoint legacy de productos (GET)
        """
        if not self.check_internet():
            _log("No se puede restaurar inventario: sin internet")
            return None

        try:
            resolved_username = self._resolve_username(str(usuario_id))
            _log(f"Descargando inventario remoto para usuario: {resolved_username}")
            ctx = self._load_device_sync_context(str(usuario_id)) or {}
            usuario_madre = str(ctx.get("usuario_madre", resolved_username)).strip() or resolved_username

            branch_code = ""

            # 1) Snapshot por sucursal activa (modo carpeta)
            try:
                from utils.file_handler import get_active_branch_context

                branch_code = str(target_branch_code or "").strip().upper()
                if not branch_code:
                    active = get_active_branch_context(resolved_username)
                    branch_code = str((active or {}).get("code", "")).strip().upper()

                # Fallback para trabajador: usar codigo de config_dispositivo.json
                # cuando aun no existe contexto activo en memoria.
                if not branch_code:
                    role = str((ctx or {}).get("tipo_dispositivo", "madre")).strip().lower()
                    if role == "trabajador":
                        branch_code = str((ctx or {}).get("codigo_dispositivo", "")).strip().upper()
                        if branch_code:
                            _log(
                                "Contexto de sucursal no activo; usando codigo de trabajador "
                                f"desde config_dispositivo: {branch_code}"
                            )

                if branch_code:
                    productos_snapshot = self._download_remote_inventory_for_code(
                        usuario_madre=usuario_madre,
                        branch_code=branch_code,
                    )
                    if productos_snapshot is not None or target_branch_code:
                        return productos_snapshot

                # Vista global madre: restaurar MADRE-<USER> + sucursales remotas.
                productos_globales = self._download_global_inventory_snapshots(
                    resolved_username=resolved_username,
                    usuario_madre=usuario_madre,
                )
                if productos_globales is not None:
                    return productos_globales
            except Exception as snapshot_err:
                _log(f"Error consultando snapshot por sucursal: {snapshot_err}")

            # 2) Fallback legacy
            from utils.api_handler import obtener_productos_remoto

            productos = obtener_productos_remoto(
                resolved_username,
                codigo_dispositivo=branch_code or None,
            )
            if productos is None:
                _log("obtener_productos_remoto() retorno None")
                return None

            if isinstance(productos, list):
                _log(f"Inventario legacy descargado: {len(productos)} productos")
                return productos

            _log(f"obtener_productos_remoto() retorno tipo invalido: {type(productos).__name__}")
            return None

        except Exception as e:
            _log(f"Error descargando inventario: {e}")
            return None

    def upload_inventory_direct(self, usuario_id: str, productos: List[Dict]) -> Tuple[bool, str]:
        """
        Sube inventario completo haciendo MERGE con lo remoto.

        Reglas:
        - No elimina productos remotos.
        - Si un producto local tiene el mismo identificador que uno remoto, se actualiza (local gana).
        - Si no existe en remoto, se agrega.
        - Si la madre está en modo global, usa el destino estable MADRE-<USER>.
        """
        if not self.check_internet():
            _log("[UPLOAD_INV] No se puede subir inventario: sin internet")
            return False, "Sin internet"

        if not isinstance(productos, list) or len(productos) == 0:
            _log("[UPLOAD_INV] Bloqueado: inventario local vacio")
            return False, "Inventario local vacio"

        resolved_username = self._resolve_username(str(usuario_id))
        ctx = self._load_device_sync_context(str(usuario_id)) or {}
        branch_code = ""
        try:
            from utils.file_handler import get_active_branch_context

            active = get_active_branch_context(resolved_username) or {}
            branch_code = str(active.get("code", "")).strip().upper()
        except Exception:
            branch_code = ""
        if not branch_code:
            try:
                role = str(ctx.get("tipo_dispositivo", "madre")).strip().lower()
                if role == "trabajador":
                    branch_code = str(ctx.get("codigo_dispositivo", "")).strip().upper()
            except Exception:
                branch_code = ""
        if not branch_code:
            try:
                branch_code = self._resolve_effective_device_code(str(usuario_id), ctx)
            except Exception:
                branch_code = ""
        if not branch_code:
            return False, "No se pudo resolver el destino de sincronizacion"

        # 1) Descargar remoto del destino real para merge (sin borrar por accidente).
        remote_current = self.download_remote_inventory(
            usuario_id,
            target_branch_code=branch_code,
        )
        if remote_current is None:
            return False, f"No se pudo leer inventario en linea para el destino {branch_code}"
        if not isinstance(remote_current, list):
            remote_current = []

        def _key(prod: Any) -> str:
            if not isinstance(prod, dict):
                return ""
            # En este proyecto el identificador mas estable es 'nombre'.
            for k in ("nombre", "codigo", "id"):
                v = str(prod.get(k, "")).strip().lower()
                if v:
                    return f"{k}:{v}"
            return ""

        merged: List[Dict] = []
        index: Dict[str, int] = {}

        # Primero remoto (para conservar productos remotos que no esten localmente).
        for item in remote_current:
            k = _key(item)
            if not k:
                continue
            index[k] = len(merged)
            merged.append(item)

        # Luego local (reemplaza o agrega).
        for item in productos:
            k = _key(item)
            if not k:
                continue
            if k in index:
                merged[index[k]] = item
            else:
                index[k] = len(merged)
                merged.append(item)

        # 2) Subir dataset completo ya mergeado (sin eliminar productos remotos).
        try:
            from utils.api_handler import subir_dataset_dispositivo_nube

            usuario_madre = str(ctx.get("usuario_madre", resolved_username)).strip() or resolved_username
            device_info = {
                "tipo_dispositivo": str(ctx.get("tipo_dispositivo", "madre")),
                "dispositivo_hijo_id": str(ctx.get("dispositivo_hijo_id", "")),
                "dispositivo_hijo_nombre": str(ctx.get("dispositivo_hijo_nombre", "")),
                "dispositivo_hijo_ciudad": str(ctx.get("dispositivo_hijo_ciudad", "")),
                "username_local": resolved_username,
            }

            ok, msg, _resp = subir_dataset_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=branch_code,
                dataset="productos",
                data=merged,
                operacion="SYNC_ALL",
                registro_id="bulk_merge",
                contenido=merged,
                device_info=device_info,
                updated_at=datetime.now().isoformat(timespec="seconds"),
            )
            if not ok:
                return False, msg or "No se pudo subir inventario"

            # Guardar localmente el resultado mergeado usando la misma ruta efectiva del UI.
            try:
                from utils.file_handler import get_user_file_path

                out_file = get_user_file_path(resolved_username, "productos.json")
                os.makedirs(out_file.parent, exist_ok=True)
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(merged, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

            try:
                from utils.sync_center_state import record_sync_center_event

                record_sync_center_event(
                    resolved_username,
                    "upload",
                    {
                        "source": "inventory_direct",
                        "codigo_dispositivo": branch_code,
                        "usuario_madre": usuario_madre,
                        "datasets": ["productos"],
                        "counts": {"productos": len(merged)},
                        "message": msg or f"Inventario subido a {branch_code}",
                    },
                )
            except Exception:
                pass

            return True, msg or f"Inventario subido (merge) a {branch_code}: {len(merged)} productos"
        except Exception as e:
            _log(f"[UPLOAD_INV] Error en upload_inventory_direct: {e}")
            return False, str(e)

    def _resolve_username(self, usuario_id: str) -> str:
        """Resuelve username a partir de usuario_id usando .usuarios.json mapping."""
        try:
            from utils.file_handler import cargar_usuarios
            usuarios = cargar_usuarios() or {}
            if usuario_id in usuarios:
                entry = usuarios.get(usuario_id)
                if isinstance(entry, dict) and entry.get('username'):
                    return entry.get('username')
            # intentar bÃºsqueda por valor
            for uid, info in usuarios.items():
                if isinstance(info, dict) and info.get('username') and str(uid) == str(usuario_id):
                    return info.get('username')
        except Exception:
            pass
        return str(usuario_id)

    def _load_device_sync_context(self, usuario_id: str) -> Dict[str, str]:
        """
        Carga metadatos de dispositivo para etiquetar la sincronizacion cloud.

        Si el equipo esta en modo trabajador, adjunta el codigo de dispositivo hijo
        para que el servidor pueda distinguir sucursal/origen.
        """
        username = self._resolve_username(str(usuario_id))
        context = {
            "tipo_dispositivo": "madre",
            "usuario_madre": str(username),
            "codigo_dispositivo": "",
            "dispositivo_hijo_id": "",
            "dispositivo_hijo_nombre": "",
            "dispositivo_hijo_ciudad": "",
            "nube_sync_modo": "carpeta",
        }

        data = {}
        try:
            config_path = Path(__file__).parent.parent / "VISO" / str(username) / "data" / "config_dispositivo.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        data = loaded
        except Exception:
            data = {}

        if isinstance(data, dict) and data:
            role = str(data.get("tipo_dispositivo", "madre")).strip().lower()
            if role in ("madre", "trabajador"):
                context["tipo_dispositivo"] = role

            usuario_madre = str(data.get("usuario_madre", "")).strip()
            if usuario_madre:
                context["usuario_madre"] = usuario_madre

            raw_codigo = (
                data.get("codigo_dispositivo_hijo")
                or data.get("codigo_dispositivo_trabajador")
                or data.get("codigo_dispositivo")
                or ""
            )
            context["codigo_dispositivo"] = str(raw_codigo).strip().upper()
            context["dispositivo_hijo_id"] = str(data.get("dispositivo_hijo_id", "")).strip()
            context["dispositivo_hijo_nombre"] = str(data.get("dispositivo_hijo_nombre", "")).strip()
            context["dispositivo_hijo_ciudad"] = str(data.get("dispositivo_hijo_ciudad", "")).strip()
            nube_sync_modo = str(data.get("nube_sync_modo", data.get("cloud_sync_mode", "carpeta"))).strip().lower()
            if nube_sync_modo in ("carpeta", "legacy"):
                # Migracion transparente: el modo legacy ya no se usa.
                context["nube_sync_modo"] = "carpeta"

        # Para dispositivo madre, priorizar sucursal activa seleccionada en UI.
        # Esto asegura sync por optica para datasets como optometras.
        try:
            if str(context.get("tipo_dispositivo", "madre")).strip().lower() != "trabajador":
                from utils.file_handler import get_active_branch_context
                active = get_active_branch_context(username)
                active_code = str((active or {}).get("code", "")).strip().upper()
                if active_code:
                    context["codigo_dispositivo"] = active_code
                else:
                    # Vista global madre: no heredar una sucursal desde config.
                    # Sin sucursal activa, el destino correcto es MADRE-<USER>.
                    context["codigo_dispositivo"] = ""
        except Exception:
            pass

        return context

    def _resolve_effective_device_code(self, usuario_id: str, device_ctx: Dict[str, str]) -> str:
        """Obtiene cÃ³digo de dispositivo para sync por carpetas."""
        raw_code = str(device_ctx.get("codigo_dispositivo", "")).strip().upper()
        if raw_code:
            return raw_code

        role = str(device_ctx.get("tipo_dispositivo", "madre")).strip().lower()
        username = self._resolve_username(str(usuario_id))
        base = re.sub(r'[^A-Za-z0-9]+', '', str(username).upper()) or "USER"
        machine = re.sub(r'[^A-Za-z0-9]+', '', os.environ.get("COMPUTERNAME", "LOCAL").upper()) or "LOCAL"

        if role == "trabajador":
            return f"WORKER-{base}-{machine}"[:80]
        # Madre debe ser estable entre PCs cuando no hay sucursal seleccionada
        return f"MADRE-{base}"[:80]

    def _load_dataset_for_folder_sync(self, username: str, tipo_dato: str) -> Any:
        """Carga dataset local completo para sincronizarlo como snapshot."""
        from utils.file_handler import (
            cargar_pacientes,
            cargar_productos,
            cargar_ventas,
            cargar_kardex,
            cargar_citas,
            cargar_servicios,
            cargar_metodos_pago,
            cargar_graduaciones,
            cargar_optometras,
            cargar_datos_generales,
            cargar_nombre_optica,
            get_user_file_path,
        )

        if tipo_dato == "clientes":
            # IMPORTANTE: no usar cargar_clientes() aqui porque intenta descarga remota
            # y puede generar "sesion no valida" durante sync de carpeta.
            try:
                fp = get_user_file_path(username, "clientes.json")
                if fp.exists():
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data if isinstance(data, (list, dict)) else []
            except Exception:
                return []
            return []
        if tipo_dato == "pacientes":
            return cargar_pacientes(username)
        if tipo_dato == "productos":
            return cargar_productos(username, prefer_cloud=False)
        if tipo_dato == "ventas":
            return cargar_ventas(username)
        if tipo_dato == "kardex":
            return cargar_kardex(username)
        if tipo_dato == "citas":
            return cargar_citas(username)
        if tipo_dato == "servicios":
            return cargar_servicios(username)
        if tipo_dato == "metodos_pago":
            return cargar_metodos_pago(username)
        if tipo_dato == "graduaciones":
            return cargar_graduaciones(username)
        if tipo_dato == "optometras":
            return cargar_optometras(username)
        if tipo_dato == "datos_generales":
            return cargar_datos_generales(username)
        if tipo_dato == "dispositivos_hijos":
            try:
                fp = get_user_file_path(username, "dispositivos_hijos.json")
                if fp.exists():
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data if isinstance(data, (list, dict)) else []
            except Exception:
                return []
            return []
        if tipo_dato == "config_dispositivo":
            try:
                fp = get_user_file_path(username, "config_dispositivo.json")
                if fp.exists():
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data if isinstance(data, dict) else {}
            except Exception:
                return {}
            return {}
        if tipo_dato == "ayudantes":
            try:
                from utils.helpers_manager import cargar_ayudantes
                return cargar_ayudantes(username) or []
            except Exception:
                return []
        if tipo_dato == "config_optica":
            try:
                # No subir el default si el archivo local no existe: eso puede
                # borrar el nombre real guardado en nube desde una instalacion nueva.
                fp = get_user_file_path(username, "configuracion_optica.txt")
                if not fp.exists():
                    return ""
                # Leer con helper (soporta almacenamiento local en base64).
                return cargar_nombre_optica(username)
            except Exception:
                return ""
        return None

    def _count_guard_records(self, dataset: str, data: Any) -> int:
        """Cuenta registros reales para proteger la subida inicial.

        Detecta listas vacias y tambien estructuras tipo {"productos": []}
        que antes pasaban como "dict no vacio" y podian borrar la nube.
        """
        def _count_any(value: Any) -> int:
            if value is None:
                return 0
            if isinstance(value, list):
                return len([item for item in value if item is not None])
            if isinstance(value, dict):
                clean = {
                    str(k): v
                    for k, v in value.items()
                    if not str(k).startswith("_")
                }
                if not clean:
                    return 0

                preferred_keys = (
                    dataset,
                    "data",
                    "items",
                    "rows",
                    "records",
                )
                for key in preferred_keys:
                    if key in clean:
                        nested = _count_any(clean.get(key))
                        if nested >= 0:
                            return nested

                values = list(clean.values())
                if values and all(isinstance(v, dict) for v in values):
                    return len(values)

                nested_best = 0
                for value_item in values:
                    nested_best = max(nested_best, _count_any(value_item))
                return nested_best

            if isinstance(value, str):
                return 1 if value.strip() else 0

            return 1

        try:
            return int(_count_any(data))
        except Exception:
            return 0

    def _extract_dataset_from_snapshot_payload(self, dataset: str, payload: Any) -> Any:
        """Extrae el dataset real desde distintas formas de respuesta de snapshot."""
        if not isinstance(payload, dict):
            return None

        dataset = str(dataset or "").strip().lower()
        direct = payload.get("data")
        if direct is not None:
            return direct

        snapshot = payload.get("snapshot")
        if isinstance(snapshot, dict) and dataset in snapshot:
            return snapshot.get(dataset)

        if dataset in payload:
            return payload.get(dataset)

        return None

    def _inspect_local_initial_counts(self, username: str) -> Dict[str, int]:
        """
        Cuenta datos locales reales sin usar loaders que intenten restaurar desde nube.

        Tambien inspecciona branch_cache porque una instalacion nueva puede
        restaurar datos remotos hacia snapshots locales antes de persistirlos en
        data/, y ese caso debe bloquear la subida inicial vacia.
        """
        try:
            from utils.file_handler import resolve_username

            resolved = str(resolve_username(username) or "").strip() or str(username or "").strip()
        except Exception:
            resolved = str(username or "").strip()

        user_root = Path(__file__).resolve().parent.parent / "VISO" / resolved
        base_dir = user_root / "data"
        branch_root = user_root / "branch_cache"
        dataset_files = {
            "clientes": ("clientes.json",),
            "pacientes": ("pacientes.json",),
            "productos": ("productos.json", "products.json"),
            "graduaciones": ("graduaciones.json",),
        }

        counts: Dict[str, int] = {}
        for dataset, candidates in dataset_files.items():
            best_count = 0
            for filename in candidates:
                fp = base_dir / filename
                if not fp.exists():
                    continue
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    best_count = max(best_count, self._count_guard_records(dataset, loaded))
                except Exception:
                    continue

            if branch_root.exists():
                for filename in candidates:
                    try:
                        for fp in branch_root.glob(f"*/data/{filename}"):
                            if not fp.exists():
                                continue
                            try:
                                with open(fp, "r", encoding="utf-8") as f:
                                    loaded = json.load(f)
                                best_count = max(best_count, self._count_guard_records(dataset, loaded))
                            except Exception:
                                continue
                    except Exception:
                        continue

            counts[dataset] = int(best_count or 0)

        return counts

    def _inspect_cloud_initial_counts(self, usuario_madre: str, username: str) -> Dict[str, Any]:
        """Cuenta datos reales en nube para impedir subidas iniciales desde PCs vacias."""
        result: Dict[str, Any] = {
            "cloud_counts": {dataset: 0 for dataset in INITIAL_SYNC_GUARD_DATASETS},
            "cloud_has_data": False,
            "cloud_has_snapshots": False,
            "cloud_has_remote_devices": False,
            "cloud_devices": 0,
            "cloud_inspected": False,
            "cloud_codes_checked": [],
            "cloud_codes_with_data": [],
        }

        try:
            from utils.api_handler import (
                descargar_snapshot_dispositivo_nube,
                listar_dispositivos_hijos_remoto,
                listar_snapshots_dispositivos_nube,
                obtener_resumen_snapshot_nube,
            )
        except Exception as e:
            result["error"] = str(e)
            return result

        candidate_codes: List[str] = []
        codes_with_data = set()

        def _add_code(value: Any) -> None:
            code = str(value or "").strip().upper()
            if code and code not in candidate_codes:
                candidate_codes.append(code)

        try:
            base = re.sub(r"[^A-Za-z0-9]+", "", str(username).upper()) or "USER"
            _add_code(f"MADRE-{base}"[:80])
        except Exception:
            pass

        ok_summary, summary, _msg_summary = obtener_resumen_snapshot_nube(usuario_madre)
        if ok_summary and isinstance(summary, list):
            result["cloud_inspected"] = True
            result["cloud_devices"] = len(summary)
            result["cloud_has_snapshots"] = len(summary) > 0

            for device in summary:
                if not isinstance(device, dict):
                    continue
                _add_code(device.get("codigo_dispositivo"))
                counts = device.get("counts") if isinstance(device.get("counts"), dict) else {}
                for dataset in INITIAL_SYNC_GUARD_DATASETS:
                    try:
                        result["cloud_counts"][dataset] += int(counts.get(dataset, 0) or 0)
                    except Exception:
                        pass

        ok_list, devices, _msg_list = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
        if ok_list and isinstance(devices, list):
            result["cloud_inspected"] = True
            result["cloud_devices"] = max(int(result.get("cloud_devices", 0)), len(devices))
            result["cloud_has_snapshots"] = bool(result.get("cloud_has_snapshots")) or len(devices) > 0
            for device in devices:
                if isinstance(device, dict):
                    _add_code(device.get("codigo_dispositivo"))

        ok_devices, legacy_devices, _msg_devices = listar_dispositivos_hijos_remoto(usuario_madre)
        if ok_devices and isinstance(legacy_devices, list):
            result["cloud_inspected"] = True
            active_device_count = 0
            for device in legacy_devices:
                if not isinstance(device, dict):
                    continue
                if str(device.get("estado", "activo")).strip().lower() == "bloqueado":
                    continue
                code = str(device.get("codigo_dispositivo", "")).strip().upper()
                if not code:
                    continue
                active_device_count += 1
                _add_code(code)
            if active_device_count > 0:
                result["cloud_has_remote_devices"] = True
                result["cloud_devices"] = max(int(result.get("cloud_devices", 0)), active_device_count)

        # Si el resumen ya trajo conteos > 0, no hace falta descargar datasets.
        if any(int(v or 0) > 0 for v in result["cloud_counts"].values()):
            result["cloud_has_data"] = True
            return result

        # Fallback fuerte: descargar datasets criticos y contar contenido real.
        for code in list(candidate_codes):
            for dataset in INITIAL_SYNC_GUARD_DATASETS:
                try:
                    ok_dl, payload_dl, _msg_dl = descargar_snapshot_dispositivo_nube(
                        usuario_madre=usuario_madre,
                        codigo_dispositivo=code,
                        dataset=dataset,
                        include_data=True,
                    )
                    if not ok_dl or not isinstance(payload_dl, dict):
                        continue
                    result["cloud_inspected"] = True
                    value = self._extract_dataset_from_snapshot_payload(dataset, payload_dl)
                    count = self._count_guard_records(dataset, value)
                    result["cloud_counts"][dataset] += count
                    if count > 0:
                        codes_with_data.add(code)
                except Exception:
                    continue

        result["cloud_codes_checked"] = list(candidate_codes)
        result["cloud_codes_with_data"] = sorted(codes_with_data)
        result["cloud_has_data"] = any(int(v or 0) > 0 for v in result["cloud_counts"].values())
        if result["cloud_has_data"] and not result["cloud_has_snapshots"]:
            result["cloud_has_snapshots"] = True
        if codes_with_data and int(result.get("cloud_devices", 0) or 0) <= 0:
            result["cloud_devices"] = len(codes_with_data)
        return result

    def inspect_initial_sync_state(self, usuario_id: str) -> Dict[str, Any]:
        """
        Inspecciona si una instalacion local tiene datos reales y si la nube ya
        contiene snapshots/datos para el mismo usuario madre.

        Se usa para evitar que una PC nueva y vacia sobrescriba una nube que ya
        tiene informacion de otra computadora.
        """
        state: Dict[str, Any] = {
            "usuario_id": str(usuario_id or "").strip(),
            "username": "",
            "usuario_madre": "",
            "local_counts": {},
            "cloud_counts": {},
            "local_has_data": False,
            "cloud_has_data": False,
            "cloud_has_snapshots": False,
            "cloud_devices": 0,
            "cloud_inspected": False,
        }

        uid = state["usuario_id"]
        if not uid:
            return state

        username = self._resolve_username(uid)
        state["username"] = username

        local_counts = self._inspect_local_initial_counts(username)
        state["local_counts"] = local_counts
        state["local_has_data"] = any(int(v or 0) > 0 for v in local_counts.values())

        try:
            device_ctx = self._load_device_sync_context(uid)
            usuario_madre = str(device_ctx.get("usuario_madre", username)).strip() or username
            state["usuario_madre"] = usuario_madre
            cloud_state = self._inspect_cloud_initial_counts(usuario_madre, username)
            state.update(cloud_state)
        except Exception as e:
            state["error"] = str(e)

        return state

    def _read_sync_center_local_dataset(self, username: str, dataset: str) -> Dict[str, Any]:
        from utils.file_handler import get_user_file_path

        filename = f"{str(dataset or '').strip().lower()}.json"
        path = get_user_file_path(username, filename)
        info: Dict[str, Any] = {
            "dataset": str(dataset or "").strip().lower(),
            "path": str(path),
            "exists": path.exists(),
            "count": 0,
            "modified_at": "",
        }

        try:
            if path.exists():
                info["modified_at"] = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                info["count"] = self._count_guard_records(dataset, loaded)
        except Exception as e:
            info["error"] = str(e)

        return info

    def _coerce_sync_center_timestamp(self, value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value)).isoformat(timespec="seconds")
            except Exception:
                return ""

        text = str(value or "").strip()
        if not text:
            return ""

        if re.fullmatch(r"\d{10,13}", text):
            try:
                epoch = float(text[:10]) if len(text) > 10 else float(text)
                return datetime.fromtimestamp(epoch).isoformat(timespec="seconds")
            except Exception:
                pass

        for candidate in (text, text.replace("Z", "+00:00")):
            try:
                parsed = datetime.fromisoformat(candidate)
                return parsed.isoformat(timespec="seconds")
            except Exception:
                continue

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
        ):
            try:
                parsed = datetime.strptime(text, fmt)
                return parsed.isoformat(timespec="seconds")
            except Exception:
                continue

        return text

    def _sync_center_timestamp_sort_key(self, value: Any) -> float:
        normalized = self._coerce_sync_center_timestamp(value)
        if not normalized:
            return 0.0

        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass

        try:
            return float(normalized)
        except Exception:
            return 0.0

    def _pick_latest_sync_center_timestamp(self, *values: Any) -> str:
        best_value = ""
        best_key = 0.0
        for value in values:
            if isinstance(value, list):
                for nested in value:
                    ts = self._pick_latest_sync_center_timestamp(nested)
                    key = self._sync_center_timestamp_sort_key(ts)
                    if key > best_key:
                        best_key = key
                        best_value = ts
                continue

            if isinstance(value, dict):
                candidates = []
                for key_name in (
                    "updated_at",
                    "uploaded_at",
                    "last_upload_at",
                    "last_updated_at",
                    "ultima_sincronizacion",
                    "timestamp",
                    "created_at",
                    "generated_at",
                    "modified_at",
                    "last_modified",
                    "date",
                    "fecha",
                ):
                    if key_name in value:
                        candidates.append(value.get(key_name))
                for nested_key in ("meta", "device_info"):
                    nested_value = value.get(nested_key)
                    if isinstance(nested_value, dict):
                        candidates.append(nested_value)
                if isinstance(value.get("datasets"), list):
                    candidates.append(value.get("datasets"))
                ts = self._pick_latest_sync_center_timestamp(candidates)
                key = self._sync_center_timestamp_sort_key(ts)
                if key > best_key:
                    best_key = key
                    best_value = ts
                continue

            ts = self._coerce_sync_center_timestamp(value)
            key = self._sync_center_timestamp_sort_key(ts)
            if key > best_key:
                best_key = key
                best_value = ts

        return best_value

    def _normalize_sync_center_cloud_device(self, device: Dict[str, Any]) -> Dict[str, Any]:
        normalized_counts = {dataset: 0 for dataset in SYNC_CENTER_DATASETS}
        datasets_raw = device.get("datasets") if isinstance(device.get("datasets"), list) else []

        for ds in datasets_raw:
            if not isinstance(ds, dict):
                continue
            name = str(ds.get("dataset", "") or ds.get("name", "")).strip().lower()
            if name not in normalized_counts:
                continue
            try:
                normalized_counts[name] = int(ds.get("rows", 0) or 0)
            except Exception:
                normalized_counts[name] = 0

        last_update = self._pick_latest_sync_center_timestamp(
            device,
            device.get("meta"),
            datasets_raw,
        )

        return {
            "codigo_dispositivo": str(device.get("codigo_dispositivo", "")).strip().upper(),
            "folder": str(device.get("folder", "") or "").strip(),
            "dataset_count": int(device.get("dataset_count", 0) or 0),
            "counts": normalized_counts,
            "meta": device.get("meta") if isinstance(device.get("meta"), dict) else {},
            "last_update": last_update,
        }

    def _build_sync_center_file_entry(self, path: Path, label: str, required: bool = False) -> Dict[str, Any]:
        exists = False
        modified_at = ""
        size_bytes = 0
        path_str = str(path)

        try:
            exists = path.exists()
            if exists:
                stat = path.stat()
                modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
                size_bytes = int(stat.st_size or 0)
        except Exception:
            exists = False

        if exists:
            tone = "ok"
            status = "Presente"
        elif required:
            tone = "danger"
            status = "Falta"
        else:
            tone = "warn"
            status = "No encontrado"

        return {
            "label": label,
            "path": path_str,
            "exists": exists,
            "required": bool(required),
            "status": status,
            "tone": tone,
            "modified_at": modified_at,
            "size_bytes": size_bytes,
        }

    def _build_sync_center_health(self, uid: str, username: str, state: Dict[str, Any]) -> Dict[str, Any]:
        from utils.file_handler import VISO_DIR, USUARIOS_FILE, SESION_FILE, resolve_username

        resolved = str(resolve_username(username) or username or "").strip()
        user_root = Path(VISO_DIR) / resolved
        user_data_dir = user_root / "data"
        effective_code = str(state.get("effective_code", "") or "").strip().upper()
        cache_dir = user_root / "branch_cache" / effective_code / "data"

        health: Dict[str, Any] = {
            "items": [],
            "critical_files": [],
            "overall_tone": "ok",
        }

        def add_item(component: str, status: str, detail: str, tone: str = "info") -> None:
            health["items"].append(
                {
                    "component": component,
                    "status": status,
                    "detail": detail,
                    "tone": tone,
                }
            )

        internet_ok = bool(state.get("internet_ok"))
        add_item(
            "Conectividad",
            "Conectado" if internet_ok else "Sin internet",
            "El sistema puede consultar nube y licencias." if internet_ok else "No se pudo validar acceso a internet.",
            "ok" if internet_ok else "danger",
        )

        cloud = state.get("cloud") if isinstance(state.get("cloud"), dict) else {}
        cloud_devices = int(cloud.get("device_count", 0) or 0)
        cloud_msg = str(cloud.get("message", "") or "").strip()
        if bool(cloud.get("inspected")):
            add_item(
                "Nube",
                "Verificada",
                cloud_msg or f"Snapshots detectados: {cloud_devices}. Destino actual: {state.get('effective_code', '')}",
                "ok" if cloud_devices > 0 else "warn",
            )
        else:
            add_item(
                "Nube",
                "Sin verificar",
                cloud_msg or "No se pudo consultar el estado cloud en este momento.",
                "warn" if internet_ok else "danger",
            )

        cache_json_count = 0
        cache_last = ""
        try:
            if cache_dir.exists():
                for fp in cache_dir.glob("*.json"):
                    cache_json_count += 1
                    cache_last = self._pick_latest_sync_center_timestamp(
                        cache_last,
                        datetime.fromtimestamp(fp.stat().st_mtime).isoformat(timespec="seconds"),
                    )
        except Exception:
            cache_json_count = 0
            cache_last = ""

        add_item(
            "Caché local",
            "Disponible" if cache_json_count > 0 else "Vacío",
            (
                f"{cache_json_count} datasets cacheados en {cache_dir}"
                + (f" | Último cambio: {cache_last}" if cache_last else "")
            ),
            "ok" if cache_json_count > 0 else "warn",
        )

        route_ok = user_data_dir.exists()
        route_writable = os.access(user_data_dir, os.W_OK) if route_ok else False
        add_item(
            "Rutas locales",
            "Listas" if route_ok and route_writable else "Revisar rutas",
            f"Data dir: {user_data_dir}",
            "ok" if route_ok and route_writable else "danger",
        )

        session_detail = "No se detectó sesión activa."
        session_tone = "warn"
        session_status = "Sin sesión"
        try:
            if Path(SESION_FILE).exists():
                with open(SESION_FILE, "r", encoding="utf-8") as f:
                    raw_session = str(f.read() or "").strip()

                session_tokens = {
                    token.strip()
                    for token in raw_session.split(":")
                    if str(token or "").strip()
                }
                valid_session_tokens = {
                    str(uid).strip(),
                    str(username).strip(),
                    resolved,
                }
                valid_session_tokens = {
                    token
                    for token in valid_session_tokens
                    if token
                }

                if raw_session and (
                    raw_session in valid_session_tokens
                    or bool(session_tokens.intersection(valid_session_tokens))
                ):
                    session_status = "Activa"
                    session_detail = f"Sesión local válida para {raw_session}."
                    session_tone = "ok"
                elif raw_session:
                    session_status = "Otra sesión"
                    session_detail = f"sesion.txt apunta a {raw_session}."
                    session_tone = "danger"
        except Exception as e:
            session_status = "Error"
            session_detail = str(e)
            session_tone = "danger"

        add_item("Sesión", session_status, session_detail, session_tone)

        license_status = "Sin verificar"
        license_detail = "No se validó la licencia todavía."
        license_tone = "warn"
        if internet_ok:
            try:
                from utils.api_handler import verificar_estado_licencia

                ok_license, license_data = verificar_estado_licencia(
                    username=username,
                    id_usuario=uid,
                    timeout=10,
                )
                if ok_license and isinstance(license_data, dict):
                    tiene_licencia = bool(license_data.get("tiene_licencia"))
                    licencia_vigente = bool(license_data.get("licencia_vigente"))
                    if tiene_licencia and licencia_vigente:
                        license_status = "Activa"
                        license_detail = (
                            f"Plan {license_data.get('plan_type', 'N/A')} | "
                            f"Vence: {license_data.get('vigencia', 'Desconocida')}"
                        )
                        license_tone = "ok"
                    elif tiene_licencia:
                        license_status = "Expirada"
                        license_detail = (
                            f"Plan {license_data.get('plan_type', 'N/A')} | "
                            f"Vencida: {license_data.get('vigencia', 'Desconocida')}"
                        )
                        license_tone = "danger"
                    else:
                        license_status = "Sin licencia"
                        license_detail = "El servidor respondió que el usuario no tiene licencia activa."
                        license_tone = "danger"
                else:
                    license_status = "No verificada"
                    license_detail = "No se pudo confirmar la licencia con el servidor."
                    license_tone = "warn"
            except Exception as e:
                license_status = "Error"
                license_detail = str(e)
                license_tone = "warn"
        add_item("Licencia", license_status, license_detail, license_tone)

        critical_files = [
            self._build_sync_center_file_entry(Path(USUARIOS_FILE), ".usuarios.json", required=True),
            self._build_sync_center_file_entry(Path(SESION_FILE), "sesion.txt", required=False),
            self._build_sync_center_file_entry(user_data_dir / "clientes.json", "clientes.json", required=False),
            self._build_sync_center_file_entry(user_data_dir / "pacientes.json", "pacientes.json", required=False),
            self._build_sync_center_file_entry(user_data_dir / "productos.json", "productos.json", required=False),
            self._build_sync_center_file_entry(user_data_dir / "ventas.json", "ventas.json", required=False),
            self._build_sync_center_file_entry(user_data_dir / "config_dispositivo.json", "config_dispositivo.json", required=False),
            self._build_sync_center_file_entry(user_data_dir / "dispositivos_hijos.json", "dispositivos_hijos.json", required=False),
        ]
        health["critical_files"] = critical_files

        missing_required = len([item for item in critical_files if item.get("required") and not item.get("exists")])
        missing_optional = len([item for item in critical_files if (not item.get("required")) and not item.get("exists")])
        if missing_required > 0:
            files_tone = "danger"
            files_status = "Crítico"
        elif missing_optional > 0:
            files_tone = "warn"
            files_status = "Incompleto"
        else:
            files_tone = "ok"
            files_status = "Completo"

        add_item(
            "Archivos críticos",
            files_status,
            (
                f"Presentes: {len([i for i in critical_files if i.get('exists')])}/{len(critical_files)}"
                f" | Faltantes opcionales: {missing_optional}"
            ),
            files_tone,
        )

        tones = [str(item.get("tone", "")) for item in health["items"]]
        if "danger" in tones:
            health["overall_tone"] = "danger"
        elif "warn" in tones:
            health["overall_tone"] = "warn"
        else:
            health["overall_tone"] = "ok"

        return health

    def inspect_sync_center_state(self, usuario_id: str) -> Dict[str, Any]:
        """
        Construye una vista comparativa segura para el centro de sincronizacion.

        No dispara restores silenciosos ni modifica archivos locales/remotos.
        """
        state: Dict[str, Any] = {
            "usuario_id": str(usuario_id or "").strip(),
            "username": "",
            "usuario_madre": "",
            "device_ctx": {},
            "active_branch": {},
            "effective_code": "",
            "internet_ok": False,
            "local": {"datasets": {}, "total_counts": {}, "last_local_change": ""},
            "cloud": {
                "devices": [],
                "target_counts": {dataset: 0 for dataset in SYNC_CENTER_DATASETS},
                "total_counts": {dataset: 0 for dataset in SYNC_CENTER_DATASETS},
                "target_last_update": "",
                "device_count": 0,
                "inspected": False,
                "message": "",
            },
            "comparison": [],
            "queue": {"total": 0, "by_dataset": {}},
            "last_upload": {},
            "last_pull": {},
            "rules": {
                "empty_overwrite_blocked": False,
                "empty_overwrite_title": "",
                "empty_overwrite_reason": "",
                "guard_local_counts": {},
                "guard_cloud_counts": {},
            },
        }

        uid = state["usuario_id"]
        if not uid:
            return state

        username = self._resolve_username(uid)
        state["username"] = username

        try:
            from utils.file_handler import get_active_branch_context

            active_branch = get_active_branch_context(username) or {}
            if isinstance(active_branch, dict):
                state["active_branch"] = {
                    "code": str(active_branch.get("code", "")).strip().upper(),
                    "label": str(active_branch.get("label", "")).strip(),
                }
        except Exception:
            state["active_branch"] = {}

        device_ctx = self._load_device_sync_context(uid)
        state["device_ctx"] = device_ctx
        state["usuario_madre"] = str(device_ctx.get("usuario_madre", username)).strip() or username
        state["effective_code"] = self._resolve_effective_device_code(uid, device_ctx)
        state["internet_ok"] = bool(self.check_internet())

        local_last_change = ""
        for dataset in SYNC_CENTER_DATASETS:
            entry = self._read_sync_center_local_dataset(username, dataset)
            state["local"]["datasets"][dataset] = entry
            state["local"]["total_counts"][dataset] = int(entry.get("count", 0) or 0)
            local_last_change = self._pick_latest_sync_center_timestamp(
                local_last_change,
                entry.get("modified_at"),
            )
        state["local"]["last_local_change"] = local_last_change

        try:
            pending_items = self.queue.get_pending_items(uid, limit=5000)
            queue_by_dataset: Dict[str, int] = {}
            for item in pending_items:
                dataset = str(item.get("tipo_dato", "")).strip().lower()
                queue_by_dataset[dataset] = int(queue_by_dataset.get(dataset, 0) or 0) + 1
            state["queue"] = {
                "total": len(pending_items),
                "by_dataset": queue_by_dataset,
            }
        except Exception as e:
            state["queue"] = {"total": 0, "by_dataset": {}, "error": str(e)}

        try:
            from utils.api_handler import (
                descargar_snapshot_dispositivo_nube,
                listar_snapshots_dispositivos_nube,
            )

            cloud_devices: List[Dict[str, Any]] = []
            ok_snap, raw_devices, snap_msg = listar_snapshots_dispositivos_nube(
                state["usuario_madre"],
                include_meta=True,
            )
            if ok_snap and isinstance(raw_devices, list):
                state["cloud"]["inspected"] = True
                for raw in raw_devices:
                    if isinstance(raw, dict):
                        cloud_devices.append(self._normalize_sync_center_cloud_device(raw))
            else:
                state["cloud"]["message"] = str(snap_msg or "No se pudo listar snapshots")

            target_code = str(state["effective_code"] or "").strip().upper()
            target_device = next(
                (device for device in cloud_devices if str(device.get("codigo_dispositivo", "")).strip().upper() == target_code),
                None,
            )

            if target_device is None and state["internet_ok"] and target_code:
                try:
                    ok_meta, payload_meta, meta_msg = descargar_snapshot_dispositivo_nube(
                        usuario_madre=state["usuario_madre"],
                        codigo_dispositivo=target_code,
                        dataset=None,
                        include_data=False,
                    )
                    if ok_meta and isinstance(payload_meta, dict):
                        target_device = self._normalize_sync_center_cloud_device(
                            {
                                "codigo_dispositivo": target_code,
                                "datasets": payload_meta.get("datasets") or [],
                                "meta": payload_meta.get("meta") if isinstance(payload_meta.get("meta"), dict) else {},
                            }
                        )
                        cloud_devices.append(target_device)
                        state["cloud"]["inspected"] = True
                    elif not state["cloud"]["message"]:
                        state["cloud"]["message"] = str(meta_msg or "No se pudo leer metadata del destino actual")
                except Exception as e:
                    if not state["cloud"]["message"]:
                        state["cloud"]["message"] = str(e)

            total_counts = {dataset: 0 for dataset in SYNC_CENTER_DATASETS}
            for device in cloud_devices:
                counts = device.get("counts") if isinstance(device.get("counts"), dict) else {}
                for dataset in SYNC_CENTER_DATASETS:
                    total_counts[dataset] += int(counts.get(dataset, 0) or 0)

            state["cloud"]["devices"] = sorted(
                cloud_devices,
                key=lambda item: str(item.get("codigo_dispositivo", "")),
            )
            state["cloud"]["total_counts"] = total_counts
            state["cloud"]["device_count"] = len(cloud_devices)

            if isinstance(target_device, dict):
                state["cloud"]["target_counts"] = {
                    dataset: int((target_device.get("counts") or {}).get(dataset, 0) or 0)
                    for dataset in SYNC_CENTER_DATASETS
                }
                state["cloud"]["target_last_update"] = str(target_device.get("last_update", "") or "")
            elif not state["cloud"]["message"] and state["internet_ok"]:
                state["cloud"]["message"] = (
                    f"No se detectó snapshot en nube para el destino actual {target_code}."
                )
        except Exception as e:
            state["cloud"]["message"] = str(e)

        try:
            from utils.sync_center_state import load_sync_center_state

            persisted = load_sync_center_state(username)
            state["last_upload"] = persisted.get("last_upload") if isinstance(persisted.get("last_upload"), dict) else {}
            state["last_pull"] = persisted.get("last_pull") if isinstance(persisted.get("last_pull"), dict) else {}
        except Exception:
            state["last_upload"] = {}
            state["last_pull"] = {}

        if not state["last_pull"]:
            try:
                from utils.file_handler import VISO_DIR, resolve_username

                branch_dir = (
                    Path(VISO_DIR)
                    / str(resolve_username(username) or username)
                    / "branch_cache"
                    / str(state["effective_code"] or "").strip().upper()
                    / "data"
                )
                latest_cache_ts = ""
                datasets_found = []
                if branch_dir.exists():
                    for dataset in SYNC_CENTER_DATASETS:
                        file_path = branch_dir / f"{dataset}.json"
                        if not file_path.exists():
                            continue
                        datasets_found.append(dataset)
                        latest_cache_ts = self._pick_latest_sync_center_timestamp(
                            latest_cache_ts,
                            datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(timespec="seconds"),
                        )
                if latest_cache_ts:
                    state["last_pull"] = {
                        "at": latest_cache_ts,
                        "source": "branch_cache_mtime",
                        "codigo_dispositivo": state["effective_code"],
                        "datasets": datasets_found,
                    }
            except Exception:
                pass

        if not state["last_upload"] and state["cloud"]["target_last_update"]:
            state["last_upload"] = {
                "at": state["cloud"]["target_last_update"],
                "source": "cloud_snapshot_meta",
                "codigo_dispositivo": state["effective_code"],
            }

        try:
            guard_state = self.inspect_initial_sync_state(uid)
            guard_local_has_data = bool(guard_state.get("local_has_data"))
            guard_cloud_has_data = bool(guard_state.get("cloud_has_data"))
            guard_cloud_has_snapshots = bool(guard_state.get("cloud_has_snapshots"))
            empty_blocked = (not guard_local_has_data) and (guard_cloud_has_data or guard_cloud_has_snapshots)

            if empty_blocked:
                title = "Protección activa"
                reason = (
                    "Esta PC no tiene datos locales reales, pero la nube sí contiene información. "
                    "El sistema debe bloquear cualquier subida vacía para no sobrescribir pacientes, "
                    "clientes, inventario u otros datasets existentes."
                )
            elif not guard_local_has_data:
                title = "Sin datos locales"
                reason = (
                    "Esta instalación aún no tiene datos reales. La subida inicial seguirá bloqueada "
                    "hasta que exista información local válida."
                )
            else:
                title = "Sin riesgo actual"
                reason = (
                    "No se detecta el escenario crítico de sobrescritura vacía para este equipo en este momento."
                )

            state["rules"] = {
                "empty_overwrite_blocked": empty_blocked,
                "empty_overwrite_title": title,
                "empty_overwrite_reason": reason,
                "guard_local_counts": guard_state.get("local_counts", {}) if isinstance(guard_state.get("local_counts"), dict) else {},
                "guard_cloud_counts": guard_state.get("cloud_counts", {}) if isinstance(guard_state.get("cloud_counts"), dict) else {},
            }
        except Exception as e:
            state["rules"] = {
                "empty_overwrite_blocked": False,
                "empty_overwrite_title": "Regla no disponible",
                "empty_overwrite_reason": str(e),
                "guard_local_counts": {},
                "guard_cloud_counts": {},
            }

        for dataset in SYNC_CENTER_DATASETS:
            local_count = int(state["local"]["total_counts"].get(dataset, 0) or 0)
            cloud_count = int(state["cloud"]["target_counts"].get(dataset, 0) or 0)
            delta = local_count - cloud_count

            if local_count == cloud_count:
                status = "Igual"
                tone = "ok"
            elif delta > 0:
                status = "Local tiene más"
                tone = "warn"
            else:
                status = "Nube tiene más"
                tone = "info"

            state["comparison"].append(
                {
                    "dataset": dataset,
                    "label": SYNC_CENTER_DATASET_LABELS.get(dataset, dataset.title()),
                    "local_count": local_count,
                    "cloud_count": cloud_count,
                    "delta": delta,
                    "status": status,
                    "tone": tone,
                    "path": str((state["local"]["datasets"].get(dataset) or {}).get("path", "")),
                    "modified_at": str((state["local"]["datasets"].get(dataset) or {}).get("modified_at", "")),
                }
            )

        try:
            state["health"] = self._build_sync_center_health(uid, username, state)
        except Exception as e:
            state["health"] = {
                "items": [
                    {
                        "component": "Salud del sistema",
                        "status": "Error",
                        "detail": str(e),
                        "tone": "danger",
                    }
                ],
                "critical_files": [],
                "overall_tone": "danger",
            }

        return state

    def _extract_branch_code_from_content(self, contenido: Any) -> str:
        """Intenta extraer codigo de sucursal/dispositivo desde metadata en cola."""
        if not isinstance(contenido, dict):
            return ""
        meta = contenido.get("_meta")
        if not isinstance(meta, dict):
            return ""
        code = str(
            meta.get("branch_code")
            or meta.get("codigo_dispositivo")
            or ""
        ).strip().upper()
        return code

    def _extract_dataset_from_content(self, tipo_dato: str, contenido: Any) -> Optional[Any]:
        """
        Extrae dataset desde el contenido encolado.

        Esto evita perder datos cuando el archivo local cambia de ruta/contexto
        antes de que se procese el item pendiente.
        """
        if contenido is None:
            return None

        if tipo_dato == "config_optica":
            if isinstance(contenido, str):
                return contenido.strip()
            if isinstance(contenido, dict):
                for key in ("config_optica", "nombre_optica", "nombre", "data"):
                    if key in contenido:
                        value = contenido.get(key)
                        if value is None:
                            return ""
                        if isinstance(value, str):
                            return value.strip()
                snapshot = contenido.get("snapshot")
                if isinstance(snapshot, dict) and "config_optica" in snapshot:
                    value = snapshot.get("config_optica")
                    return str(value or "").strip()

        # Caso comun: {"ventas": [...]} o {"clientes": [...], "_meta": {...}}
        if isinstance(contenido, dict):
            if tipo_dato in contenido:
                data = contenido.get(tipo_dato)
                if isinstance(data, (list, dict)):
                    return data
                if data is None:
                    return []

            # Compatibilidad: payloads que usan "data" o "snapshot"
            data = contenido.get("data")
            if isinstance(data, (list, dict)):
                return data
            snapshot = contenido.get("snapshot")
            if isinstance(snapshot, dict):
                ds = snapshot.get(tipo_dato)
                if isinstance(ds, (list, dict)):
                    return ds
                if ds is None and tipo_dato in snapshot:
                    return []
            return None

        # Si contenido ya es lista/dict del dataset
        if isinstance(contenido, (list, dict)):
            return contenido

        return None

    def _sync_item_folder_cloud(self, item: Dict, device_ctx: Dict[str, str]) -> Tuple[bool, str]:
        """
        Sincroniza cambios al storage por carpetas.
        Estrategia:
        - CREATE/UPDATE/DELETE: envia delta puntual (sin subir dataset completo).
        - SYNC_ALL u otros: fallback a subida completa del dataset local.
        """
        tipo_dato = str(item.get("tipo_dato", "")).strip().lower()
        supported = FOLDER_SYNC_DATASETS
        if tipo_dato not in supported:
            return False, "Tipo no soportado por folder sync"

        username = self._resolve_username(str(item.get("usuario_id", "")))
        usuario_madre = str(device_ctx.get("usuario_madre", username)).strip() or username
        codigo_dispositivo = self._resolve_effective_device_code(str(item.get("usuario_id", "")), device_ctx)

        device_info = {
            "tipo_dispositivo": str(device_ctx.get("tipo_dispositivo", "madre")),
            "dispositivo_hijo_id": str(device_ctx.get("dispositivo_hijo_id", "")),
            "dispositivo_hijo_nombre": str(device_ctx.get("dispositivo_hijo_nombre", "")),
            "dispositivo_hijo_ciudad": str(device_ctx.get("dispositivo_hijo_ciudad", "")),
            "username_local": username,
        }

        from utils.api_handler import subir_dataset_dispositivo_nube
        operacion = str(item.get("operacion", "")).strip().upper()
        registro_id = str(item.get("registro_id", "")).strip()
        contenido = item.get("contenido")

        # Si el item trae metadata de sucursal, priorizarla.
        branch_code_hint = self._extract_branch_code_from_content(contenido)
        if branch_code_hint:
            codigo_dispositivo = branch_code_hint

        # Modo delta: no sube dataset completo; solo el cambio puntual.
        if operacion in ("CREATE", "UPDATE", "DELETE"):
            # Por defecto enviamos SOLO delta (payload pequeño).
            # Si el backend devuelve un error tipo "No dataset to upload"/"Dataset not found",
            # hacemos retry con snapshot local completo como compatibilidad.
            compat_data = None
            include_snapshot = (tipo_dato == "productos")
            if include_snapshot:
                compat_data = self._load_dataset_for_folder_sync(username, tipo_dato)
                if not isinstance(compat_data, (list, dict)):
                    compat_data = []

            # Caso inicial: si no existe productos.json para esa sucursal y llega CREATE,
            # mandar al menos el contenido del item para forzar creacion del dataset remoto.
            if (
                tipo_dato == "productos"
                and operacion in ("CREATE", "UPDATE")
                and isinstance(contenido, dict)
                and contenido
            ):
                if isinstance(compat_data, list):
                    if len(compat_data) == 0:
                        compat_data = [contenido]
                elif isinstance(compat_data, dict):
                    # Estandarizamos productos como lista para el backend.
                    compat_data = [contenido]

            # Para evitar borrar productos remotos cuando el cache local esta incompleto,
            # intentamos usar lo remoto como base y luego aplicar el delta.
            if tipo_dato == "productos":
                try:
                    cache = getattr(self, "_remote_productos_cache", None)
                    if not isinstance(cache, dict):
                        cache = {}
                        setattr(self, "_remote_productos_cache", cache)

                    cache_key = f"{usuario_madre}|{codigo_dispositivo}"
                    now_ts = int(time.time())
                    remote_base = None

                    cached = cache.get(cache_key)
                    if isinstance(cached, dict) and (now_ts - int(cached.get("ts", 0) or 0)) < 60:
                        remote_base = cached.get("data")
                    else:
                        from utils.api_handler import descargar_snapshot_dispositivo_nube

                        ok_meta, payload_meta, _msg_meta = descargar_snapshot_dispositivo_nube(
                            usuario_madre=usuario_madre,
                            codigo_dispositivo=codigo_dispositivo,
                            dataset=None,
                            include_data=False,
                        )
                        has_productos = False
                        if ok_meta and isinstance(payload_meta, dict):
                            ds_list = payload_meta.get("datasets") or []
                            if isinstance(ds_list, list):
                                for ds in ds_list:
                                    if not isinstance(ds, dict):
                                        continue
                                    name = str(ds.get("dataset") or ds.get("name") or "").strip().lower()
                                    if name == "productos":
                                        has_productos = True
                                        break

                        if not has_productos:
                            remote_base = []
                        else:
                            ok_dl, payload_dl, _msg_dl = descargar_snapshot_dispositivo_nube(
                                usuario_madre=usuario_madre,
                                codigo_dispositivo=codigo_dispositivo,
                                dataset="productos",
                                include_data=True,
                            )
                            remote_list: List[Dict] = []
                            if ok_dl and isinstance(payload_dl, dict):
                                if isinstance(payload_dl.get("data"), list):
                                    remote_list = payload_dl.get("data") or []
                                elif isinstance(payload_dl.get("snapshot"), dict):
                                    snap = payload_dl.get("snapshot") or {}
                                    maybe = snap.get("productos")
                                    if isinstance(maybe, list):
                                        remote_list = maybe
                            remote_base = remote_list

                        cache[cache_key] = {"ts": now_ts, "data": remote_base}

                    if isinstance(remote_base, list) and remote_base:
                        # Merge: remoto primero, luego local (local gana).
                        def _pkey(prod: Any) -> str:
                            if not isinstance(prod, dict):
                                return ""
                            for k in ("nombre", "codigo", "id"):
                                v = str(prod.get(k, "")).strip().lower()
                                if v:
                                    return f"{k}:{v}"
                            return ""

                        merged_local: List[Dict] = []
                        idx_map: Dict[str, int] = {}

                        for it in remote_base:
                            kk = _pkey(it)
                            if not kk:
                                continue
                            idx_map[kk] = len(merged_local)
                            merged_local.append(it)

                        if isinstance(compat_data, list):
                            for it in compat_data:
                                kk = _pkey(it)
                                if not kk:
                                    continue
                                if kk in idx_map:
                                    merged_local[idx_map[kk]] = it
                                else:
                                    idx_map[kk] = len(merged_local)
                                    merged_local.append(it)
                            compat_data = merged_local
                except Exception:
                    pass

            # Algunos servidores ignoran operacion/contenido y persisten SOLO `data`.
            # Por eso aplicamos el delta localmente sobre compat_data antes del POST.
            if tipo_dato == "productos":
                if not isinstance(compat_data, list):
                    compat_data = []

                def _key(prod: Any) -> str:
                    if not isinstance(prod, dict):
                        return ""
                    for k in ("id", "codigo", "nombre"):
                        v = str(prod.get(k, "")).strip().lower()
                        if v:
                            return f"{k}:{v}"
                    return ""

                target_key = ""
                if isinstance(contenido, dict):
                    target_key = _key(contenido)
                if not target_key and registro_id:
                    rid = str(registro_id).strip().lower()
                    if rid:
                        target_key = f"rid:{rid}"

                def _matches(prod: Any) -> bool:
                    if not isinstance(prod, dict):
                        return False
                    if target_key.startswith("rid:"):
                        rid = target_key[4:]
                        for k in ("id", "codigo", "nombre", "registro_id"):
                            if str(prod.get(k, "")).strip().lower() == rid and rid:
                                return True
                        return False
                    if target_key:
                        return _key(prod) == target_key
                    return False

                if operacion in ("CREATE", "UPDATE") and isinstance(contenido, dict) and contenido:
                    updated = False
                    for idx_item, item_data in enumerate(compat_data):
                        if _matches(item_data):
                            compat_data[idx_item] = contenido
                            updated = True
                            break
                    if not updated:
                        compat_data.append(contenido)
                elif operacion == "DELETE":
                    compat_data = [p for p in compat_data if not _matches(p)]

            ok, msg, _resp = subir_dataset_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=codigo_dispositivo,
                dataset=tipo_dato,
                data=compat_data,
                operacion=operacion,
                registro_id=registro_id,
                contenido=contenido,
                device_info=device_info,
                updated_at=datetime.now().isoformat(timespec="seconds"),
            )

            # Retry compat: si no mandamos snapshot y el backend lo exige, reintentar con dataset completo.
            if (not ok) and (not include_snapshot):
                try:
                    msg_l = str(msg or "").strip().lower()
                    needs_data = any(
                        s in msg_l
                        for s in (
                            "no dataset to upload",
                            "dataset not found",
                            "not found",
                            "use dataset+data",
                            "use dataset + data",
                            "use snapshot",
                        )
                    )
                    if needs_data:
                        dataset_full = self._load_dataset_for_folder_sync(username, tipo_dato)
                        if not isinstance(dataset_full, (list, dict)):
                            dataset_full = []
                        # Enviar como SYNC_ALL para evitar inconsistencias si el backend ignora delta params.
                        ok2, msg2, _resp2 = subir_dataset_dispositivo_nube(
                            usuario_madre=usuario_madre,
                            codigo_dispositivo=codigo_dispositivo,
                            dataset=tipo_dato,
                            data=dataset_full,
                            operacion="SYNC_ALL",
                            registro_id="bulk",
                            contenido=dataset_full,
                            device_info=device_info,
                            updated_at=datetime.now().isoformat(timespec="seconds"),
                        )
                        if ok2:
                            ok, msg = True, msg2
                except Exception:
                    pass
            if ok:
                if tipo_dato == "productos":
                    verified, verify_msg = self._verify_folder_delta_applied(
                        usuario_madre=usuario_madre,
                        codigo_dispositivo=codigo_dispositivo,
                        dataset=tipo_dato,
                        operacion=operacion,
                        registro_id=registro_id,
                        contenido=contenido,
                    )
                    if not verified:
                        _log(
                            f"[FOLDER_SYNC][DELTA] ERROR verificacion {tipo_dato} "
                            f"-> {usuario_madre}/{codigo_dispositivo} [{registro_id}]: {verify_msg}"
                        )
                        return False, verify_msg

                _log(
                    f"[FOLDER_SYNC][DELTA] OK {operacion} {tipo_dato} "
                    f"-> {usuario_madre}/{codigo_dispositivo} [{registro_id}]"
                )
                return True, msg or "OK folder sync delta"

            _log(f"[FOLDER_SYNC][DELTA] ERROR {tipo_dato}: {msg}")
            return False, msg or "Error folder sync delta"

        # Fallback: carga y sube dataset completo
        try:
            dataset_data = None
            if operacion == "SYNC_ALL":
                dataset_data = self._extract_dataset_from_content(tipo_dato, contenido)
                if dataset_data is not None:
                    _log(
                        f"[FOLDER_SYNC] Usando contenido encolado para {tipo_dato} "
                        f"(evita perdida por cambio de contexto local)"
                    )
            if dataset_data is None:
                dataset_data = self._load_dataset_for_folder_sync(username, tipo_dato)
            if dataset_data is None:
                dataset_data = []
        except Exception as e:
            _log(f"[FOLDER_SYNC] Error cargando dataset local ({tipo_dato}): {e}")
            return False, f"Error cargando dataset local: {e}"

        # Permitir datasets escalares (ej: config_optica puede ser string).
        if dataset_data is None:
            dataset_data = []

        # SAFETY: No subir SYNC_ALL vacio (instalaciones nuevas con 0 datos)
        # porque puede borrar datos remotos por accidente.
        # Para permitir "vaciar" intencionalmente, enviar _meta.force_empty_sync=true.
        try:
            force_empty = False
            if isinstance(contenido, dict):
                meta = contenido.get("_meta")
                if isinstance(meta, dict):
                    raw = meta.get("force_empty_sync")
                    if raw is None:
                        raw = meta.get("allow_empty_sync")
                    if isinstance(raw, bool):
                        force_empty = raw
                    else:
                        force_empty = str(raw).strip().lower() in ("1", "true", "yes", "si")

            is_empty = (
                (isinstance(dataset_data, list) and len(dataset_data) == 0)
                or (isinstance(dataset_data, dict) and len(dataset_data) == 0)
                or (isinstance(dataset_data, str) and dataset_data.strip() == "")
            )
            if operacion == "SYNC_ALL" and (not force_empty) and is_empty:
                _log(
                    f"[SAFETY] Ignorando SYNC_ALL vacio para {tipo_dato} "
                    f"-> {usuario_madre}/{codigo_dispositivo} (evita borrado remoto)"
                )
                return True, "Ignored empty SYNC_ALL (safety)"
        except Exception:
            pass

        ok, msg, _resp = subir_dataset_dispositivo_nube(
            usuario_madre=usuario_madre,
            codigo_dispositivo=codigo_dispositivo,
            dataset=tipo_dato,
            data=dataset_data,
            operacion="SYNC_ALL",
            registro_id="bulk",
            contenido=dataset_data,
            device_info=device_info,
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )

        if ok:
            size_info = len(dataset_data) if isinstance(dataset_data, list) else 1
            _log(
                f"[FOLDER_SYNC] OK {tipo_dato} -> {usuario_madre}/{codigo_dispositivo} "
                f"({size_info} registros)"
            )
            return True, msg or "OK folder sync"

        _log(f"[FOLDER_SYNC] ERROR {tipo_dato}: {msg}")
        return False, msg or "Error folder sync"

    def _verify_folder_delta_applied(
        self,
        usuario_madre: str,
        codigo_dispositivo: str,
        dataset: str,
        operacion: str,
        registro_id: str,
        contenido: Any,
    ) -> Tuple[bool, str]:
        """
        Verifica que el cambio delta realmente se reflejo en nube.
        Evita falsos "OK" cuando el endpoint responde 200 pero no aplica cambios.
        """
        try:
            from utils.api_handler import descargar_snapshot_dispositivo_nube
        except Exception as e:
            return False, f"No se pudo importar verificacion remota: {e}"

        op = str(operacion or "").strip().upper()
        rid = str(registro_id or "").strip().lower()
        dataset_name = str(dataset or "").strip().lower()

        def _item_matches(item: Any) -> bool:
            if not isinstance(item, dict):
                return False
            # Match principal por registro_id
            if rid:
                for k in ("id", "codigo", "nombre", "registro_id"):
                    v = str(item.get(k, "")).strip().lower()
                    if v and v == rid:
                        return True
            # Fallback por contenido puntual
            if isinstance(contenido, dict):
                for k in ("id", "codigo", "nombre"):
                    expected = str(contenido.get(k, "")).strip().lower()
                    current = str(item.get(k, "")).strip().lower()
                    if expected and current and expected == current:
                        return True
            return False

        # Reintento corto porque el backend puede tardar milisegundos en persistir
        for attempt in range(2):
            ok, payload, msg = descargar_snapshot_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=codigo_dispositivo,
                dataset=dataset_name,
                include_data=True
            )
            if not ok:
                if attempt == 0:
                    time.sleep(0.4)
                    continue
                return False, f"No se pudo verificar en nube: {msg}"

            data_remote = payload.get("data") if isinstance(payload, dict) else None
            if isinstance(data_remote, list):
                found = any(_item_matches(x) for x in data_remote)
                if op in ("CREATE", "UPDATE"):
                    if found:
                        return True, "Delta verificado en nube"
                elif op == "DELETE":
                    if not found:
                        return True, "Delete verificado en nube"
                else:
                    return True, "Operacion sin verificacion estricta"
            elif isinstance(data_remote, dict):
                # Para datasets objeto (no lista), si existe data consideramos aplicado
                return True, "Dataset objeto verificado en nube"
            else:
                # dataset vacio/no presente
                if op == "DELETE":
                    return True, "Delete verificado (dataset vacio)"

            if attempt == 0:
                time.sleep(0.4)

        return False, (
            f"Cambio no reflejado en nube: dataset={dataset_name}, "
            f"op={op}, registro={registro_id or 'N/A'}"
        )

    def _sync_all_folder_datasets(
        self,
        usuario_id: str,
        device_ctx: Dict[str, str],
        endpoint_file: str = "upload_device_snapshot.php",
    ) -> Dict[str, Any]:
        """
        Sincroniza todos los datasets soportados en modo carpeta.
        Esto garantiza subida completa aunque no haya cambios en cola.
        """
        username = self._resolve_username(str(usuario_id))
        usuario_madre = str(device_ctx.get("usuario_madre", username)).strip() or username
        codigo_dispositivo = self._resolve_effective_device_code(str(usuario_id), device_ctx)
        stats: Dict[str, Any] = {"sincronizados": 0, "errores": 0, "fallidos": []}

        device_info = {
            "tipo_dispositivo": str(device_ctx.get("tipo_dispositivo", "madre")),
            "dispositivo_hijo_id": str(device_ctx.get("dispositivo_hijo_id", "")),
            "dispositivo_hijo_nombre": str(device_ctx.get("dispositivo_hijo_nombre", "")),
            "dispositivo_hijo_ciudad": str(device_ctx.get("dispositivo_hijo_ciudad", "")),
            "username_local": username,
        }

        from utils.api_handler import subir_dataset_dispositivo_nube

        for dataset in FOLDER_SYNC_DATASETS:
            try:
                data = self._load_dataset_for_folder_sync(username, dataset)
                if data is None:
                    data = []

                # config_optica es dataset escalar en backend (string).
                # Se sube tal cual; el handler HTTP agrega un fallback por snapshot.

                # SAFETY: En respaldo completo, omitir datasets vacios para evitar borrar nube por accidente.
                try:
                    empty_ds = (
                        (isinstance(data, list) and len(data) == 0)
                        or (isinstance(data, dict) and len(data) == 0)
                        or (isinstance(data, str) and data.strip() == "")
                    )
                    if empty_ds:
                        _log(
                            f"[SAFETY] Omitido dataset vacio en respaldo completo: {dataset} "
                            f"-> {usuario_madre}/{codigo_dispositivo}"
                        )
                        stats["sincronizados"] += 1
                        continue
                except Exception:
                    pass

                with _HTTP_REQUEST_LOCK:
                    time.sleep(0.15)
                    ok, msg, _resp = subir_dataset_dispositivo_nube(
                        usuario_madre=usuario_madre,
                        codigo_dispositivo=codigo_dispositivo,
                        dataset=dataset,
                        data=data,
                        device_info=device_info,
                        updated_at=datetime.now().isoformat(timespec="seconds"),
                        endpoint_file=endpoint_file,
                    )

                if ok:
                    stats["sincronizados"] += 1
                    rows = len(data) if isinstance(data, list) else 1
                    _log(
                        f"[FOLDER_SYNC][FULL] OK {dataset} -> {usuario_madre}/{codigo_dispositivo} "
                        f"({rows} registros)"
                    )
                else:
                    # Compatibilidad: algunos backends antiguos no aceptan config_optica como dataset.
                    # No debe bloquear el respaldo inicial (no es crítico para integridad de datos).
                    msg_text = str(msg or "")
                    if dataset == "config_optica" and "No dataset to upload" in msg_text:
                        stats["sincronizados"] += 1
                        _log(f"[FOLDER_SYNC][FULL] WARN {dataset}: omitido (backend no soporta dataset escalar)")
                    else:
                        stats["errores"] += 1
                        _log(f"[FOLDER_SYNC][FULL] ERROR {dataset}: {msg}")
                        try:
                            stats["fallidos"].append({"dataset": dataset, "message": msg_text})
                        except Exception:
                            pass
            except Exception as e:
                stats["errores"] += 1
                _log(f"[FOLDER_SYNC][FULL] EXCEPTION {dataset}: {e}")
                try:
                    stats["fallidos"].append({"dataset": dataset, "message": str(e)})
                except Exception:
                    pass

        return stats

    def force_cloud_backup(self, usuario_id: str) -> Dict[str, Any]:
        """
        Ejecuta respaldo manual inmediato hacia nube.
        - Sube snapshot completo por dataset (modo carpeta).
        - Luego sincroniza cola pendiente forzando throttle.
        """
        result: Dict[str, Any] = {
            "ok": False,
            "message": "",
            "guard_blocked": False,
            "full": {"sincronizados": 0, "errores": 0},
            "queue": {"sincronizados": 0, "errores": 0, "pendientes": 0},
            "usuario_madre": "",
            "codigo_dispositivo": "",
            "portal_url": "",
        }

        uid = str(usuario_id or "").strip()
        if not uid:
            result["message"] = "usuario_id vacio"
            return result

        if not self.check_internet():
            result["message"] = "Sin internet"
            return result

        try:
            guard_state = self.inspect_initial_sync_state(uid)
            result["initial_guard"] = guard_state

            local_has_data = bool(guard_state.get("local_has_data"))
            cloud_has_data = bool(guard_state.get("cloud_has_data"))
            cloud_has_snapshots = bool(guard_state.get("cloud_has_snapshots"))

            if not local_has_data:
                if cloud_has_data or cloud_has_snapshots:
                    result["guard_blocked"] = True
                    result["message"] = (
                        "Bloqueado por seguridad: esta PC no tiene datos locales reales, "
                        "pero la nube ya contiene informacion. No se subio nada para evitar "
                        "sobrescribir pacientes, clientes o inventario existentes."
                    )
                    _log(
                        "[INITIAL_GUARD] Respaldo cancelado: local vacio y nube con datos/snapshots. "
                        f"uid={uid} cloud={guard_state.get('cloud_counts', {})}"
                    )
                    return result

                result["message"] = (
                    "No hay datos locales reales para subir todavia. "
                    "La instalacion parece vacia."
                )
                result["guard_blocked"] = True
                _log(f"[INITIAL_GUARD] Respaldo omitido: local vacio para uid={uid}")
                return result

            device_ctx = self._load_device_sync_context(uid)
            folder_mode = str(device_ctx.get("nube_sync_modo", "carpeta")).strip().lower() == "carpeta"
            usuario_madre = str(device_ctx.get("usuario_madre", self._resolve_username(uid))).strip() or self._resolve_username(uid)
            codigo_dispositivo = self._resolve_effective_device_code(uid, device_ctx)
            result["usuario_madre"] = usuario_madre
            result["codigo_dispositivo"] = codigo_dispositivo

            try:
                from urllib.parse import quote_plus
                base_url = "https://api.yhana.cloud/win/new"
                result["portal_url"] = (
                    f"{base_url}/manual_backup_portal.php"
                    f"?usuario_madre={quote_plus(usuario_madre)}"
                    f"&codigo_dispositivo={quote_plus(codigo_dispositivo)}"
                )
            except Exception as e:
                _log(f"[BACKUP] Error construyendo portal_url: {e}")
                result["portal_url"] = ""

            if folder_mode:
                _log("[MANUAL_BACKUP] Iniciando respaldo completo de datasets...")
                full_stats = self._sync_all_folder_datasets(
                    uid,
                    device_ctx,
                    endpoint_file="upload_device_snapshot_manual.php",
                )
                result["full"] = {
                    "sincronizados": int(full_stats.get("sincronizados", 0)),
                    "errores": int(full_stats.get("errores", 0)),
                }
                fallidos = full_stats.get("fallidos", [])
                if isinstance(fallidos, list) and fallidos:
                    result["full"]["fallidos"] = fallidos

            # El respaldo manual sube snapshot completo por endpoint dedicado.
            # No forzamos sync_now para evitar que este boton use upload_device_snapshot.php.
            try:
                pendientes = len(self.queue.get_pending_items(uid, limit=5000))
            except Exception:
                pendientes = 0
            result["queue"] = {"sincronizados": 0, "errores": 0, "pendientes": int(pendientes)}

            total_errors = int(result["full"]["errores"])
            total_ok = int(result["full"]["sincronizados"])
            pending = int(result["queue"]["pendientes"])

            result["ok"] = total_errors == 0
            error_word = "error" if total_errors == 1 else "errores"
            pending_word = "pendiente" if pending == 1 else "pendientes"
            result["message"] = (
                f"Respaldo completado: {total_ok} OK, {total_errors} {error_word}, {pending} {pending_word}"
            )
            if result["ok"] and total_ok > 0:
                try:
                    from utils.sync_center_state import record_sync_center_event

                    record_sync_center_event(
                        self._resolve_username(uid),
                        "upload",
                        {
                            "source": "manual_backup",
                            "codigo_dispositivo": codigo_dispositivo,
                            "usuario_madre": usuario_madre,
                            "counts": dict(result.get("full", {})),
                            "message": result["message"],
                        },
                    )
                except Exception:
                    pass
            return result
        except Exception as e:
            result["message"] = f"Error en respaldo manual: {e}"
            return result

    def sync_item(self, item: Dict) -> Tuple[bool, str]:
        """Sincroniza un item individual al servidor."""
        try:
            # Defensa extra: No enviar SYNC_ALL de productos vacÃ­os (por seguridad)
            try:
                if item.get('tipo_dato') == 'productos' and item.get('operacion') == 'SYNC_ALL':
                    contenido = item.get('contenido') or {}
                    if not isinstance(contenido, dict) or not contenido.get('productos'):
                        _log(f"â›” [PROTECCIÃ“N] Ignorando SYNC_ALL vacÃ­o (id={item.get('id')})")
                        return True, "Ignored empty SYNC_ALL"
            except Exception:
                pass
            if item['tipo_dato'] == 'productos' and item['operacion'] == 'DELETE':
                # ProtecciÃ³n adicional: verificar consistencia si fuera necesario
                pass

            device_ctx = self._load_device_sync_context(item.get('usuario_id', ''))
            if item.get('tipo_dato') in FOLDER_SYNC_DATASETS:
                with _HTTP_REQUEST_LOCK:
                    time.sleep(0.05)
                    registro_info = f" [{item['registro_id'][:20]}]" if item.get('registro_id') else ""
                    _log(
                        f"[SEND][FOLDER] {item.get('operacion')} {item.get('tipo_dato')}{registro_info} "
                        f"-> /api/win/new/upload_device_snapshot.php"
                    )
                    return self._sync_item_folder_cloud(item, device_ctx)
            unsupported_type = str(item.get('tipo_dato', '') or '').strip().lower() or "desconocido"
            _log(
                f"[SEND][UNSUPPORTED] {unsupported_type} no esta migrado al sync cloud actual. "
                "Se omite envio."
            )
            return False, f"Tipo no soportado por sync cloud actual: {unsupported_type}"
        
        except Exception as e:
            _log(f"[EXCEPTION] sync_item: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    def sync_now(self, usuario_id: str, force: bool = False) -> Dict[str, int]:
        """Sincroniza todos los items pendientes."""
        global _LAST_SYNC_TIME
        
        # âš ï¸ PROTECCIONES CRÃTICAS: limpiar solo SYNC_ALL inseguros/vacios.
        # IMPORTANTE: NO limpiar DELETE de productos; eso impedÃ­a borrar en nube.
        syncall_count = self.queue.clear_sync_all_pending(usuario_id)
        if syncall_count > 0:
            _log(f"â›” [PROTECCIÃ“N] Limpiados {syncall_count} SYNC_ALL de productos (seguridad)")
        
        # ProtecciÃ³n adicional: eliminar SYNC_ALL que estÃ©n vacÃ­os (contenido sin 'productos')
        empty_cleaned = self.queue.clear_empty_sync_all_pending(usuario_id)
        if empty_cleaned > 0:
            _log(f"â›” [PROTECCIÃ“N] Eliminados {empty_cleaned} SYNC_ALL vacÃ­os (evita borrados accidentales)")
        # Convertir SYNC_ALL pendientes (no vacÃ­os) en CREATEs para evitar envÃ­os masivos
        try:
            converted = self.queue.convert_pending_sync_all_to_creates(usuario_id)
            if converted > 0:
                _log(f"âš ï¸ [PROTECCIÃ“N] Convertidos {converted} items desde SYNC_ALL pendientes a CREATE individuales")
        except Exception:
            pass
        now = time.time()
        if (not force) and (now - _LAST_SYNC_TIME < _MIN_SYNC_INTERVAL):
            _log(f"[THROTTLE] sync_now bloqueado por throttle (Ãºltima sync hace {now - _LAST_SYNC_TIME:.1f}s)")
            return {'sincronizados': 0, 'errores': 0, 'pendientes': 0}
        
        internet_ok = self.check_internet()
        _log(f"[DEBUG] check_internet => {internet_ok}")
        if not internet_ok:
            _log("[SYNC] âš ï¸ Sin internet - sync bloqueado")
            return {'sincronizados': 0, 'errores': 0, 'pendientes': 0}
        
        stats = {'sincronizados': 0, 'errores': 0, 'pendientes': 0}

        # En modo carpeta, por defecto NO forzar subida masiva completa.
        # Para depuracion/migracion se puede habilitar con:
        # VISO_FORCE_FULL_FOLDER_SYNC=1
        try:
            device_ctx_sync = self._load_device_sync_context(usuario_id)
            folder_mode_sync = str(device_ctx_sync.get("nube_sync_modo", "carpeta")).strip().lower() == "carpeta"
            force_full_sync = str(os.getenv("VISO_FORCE_FULL_FOLDER_SYNC", "0")).strip() == "1"
            if folder_mode_sync and force_full_sync:
                _log("[FOLDER_SYNC][FULL] Iniciando sincronizacion completa de datasets...")
                full_stats = self._sync_all_folder_datasets(usuario_id, device_ctx_sync)
                stats['sincronizados'] += int(full_stats.get('sincronizados', 0))
                stats['errores'] += int(full_stats.get('errores', 0))
                _log(
                    f"[FOLDER_SYNC][FULL] Resultado: "
                    f"{full_stats.get('sincronizados', 0)} OK, {full_stats.get('errores', 0)} errores"
                )
            elif folder_mode_sync:
                _log("[FOLDER_SYNC][FULL] Omitido (modo delta activo)")
        except Exception as e:
            _log(f"[FOLDER_SYNC][FULL] Error en sincronizacion completa: {e}")
        
        # Prioridad a productos (aumentar lÃ­mites para evitar truncar sincronizaciones grandes)
        productos_items = self.queue.get_pending_items(usuario_id, limit=1000)
        otros_items = self.queue.get_pending_items(usuario_id, limit=100)

        _log(f"[DEBUG] items sin filtrar: {len(productos_items)} de productos + {len(otros_items)} otros")
        try:
            sample = (productos_items + otros_items)[:10]
            for it in sample:
                _log(f"[DEBUG_ITEM] id={it.get('id')} tipo={it.get('tipo_dato')} op={it.get('operacion')} registro={it.get('registro_id')} estado={it.get('estado')}")
        except Exception:
            pass
        
        productos_items = [i for i in productos_items if i['tipo_dato'] == 'productos']
        otros_items = [i for i in otros_items if i['tipo_dato'] != 'productos']
        
        _log(f"[DEBUG] items filtrados: {len(productos_items)} productos + {len(otros_items)} otros")
        
        # âš ï¸ VALIDACIÃ“N INTELIGENTE: SYNC_ALL/DELETE ya fueron limpiadas arriba
        # CREATE/UPDATE siempre son seguras y se sincronizan aunque no haya JSON
        # (ej: primer producto que crea el usuario)
        _log(f"[DEBUG] {len(productos_items)} CREATE/UPDATE de productos listas para sincronizar")
        
        items = productos_items + otros_items
        
        if not items:
            _log(f"[SYNC] â„¹ï¸  No hay items pendientes para sincronizar")
            _LAST_SYNC_TIME = now
            return stats
            
        _log(f"[SYNC] ====== Iniciando sincronizaciÃ³n de {len(items)} cambios ({len(productos_items)} productos + {len(otros_items)} otros) ======")
        
        for idx, item in enumerate(items, 1):
            _log(f"[SYNC] [{idx}/{len(items)}] Procesando {item['operacion']} de {item['tipo_dato']}")
            success, msg = self.sync_item(item)
            if success:
                self.queue.mark_synced(item['id'], msg)
                stats['sincronizados'] += 1
                _log(f"[SYNC] [{idx}/{len(items)}] âœ“ Sincronizado")
            else:
                self.queue.mark_error(item['id'], msg)
                stats['errores'] += 1
                _log(f"[SYNC] [{idx}/{len(items)}] âœ— Error: {msg}")
        
        _LAST_SYNC_TIME = now
        if stats.get('sincronizados', 0) > 0:
            try:
                device_ctx_done = self._load_device_sync_context(usuario_id)
                record_username = self._resolve_username(str(usuario_id))
                from utils.sync_center_state import record_sync_center_event

                record_sync_center_event(
                    record_username,
                    "upload",
                    {
                        "source": "delta_sync",
                        "codigo_dispositivo": self._resolve_effective_device_code(usuario_id, device_ctx_done),
                        "usuario_madre": str(device_ctx_done.get("usuario_madre", record_username)).strip() or record_username,
                        "counts": dict(stats),
                        "message": (
                            f"Delta sync: {int(stats.get('sincronizados', 0) or 0)} OK, "
                            f"{int(stats.get('errores', 0) or 0)} errores"
                        ),
                    },
                )
            except Exception:
                pass
        return stats
    
    def start_auto_sync(self, usuario_id: str, interval: int = 30):
        """Inicia sincronizaciÃ³n automÃ¡tica en background"""
        if self._running: return
        self._running = True
        
        def _auto_sync_worker():
            while self._running:
                try:
                    if self.check_internet():
                        self.sync_now(usuario_id)
                except Exception:
                    pass
                time.sleep(interval)
        
        self._sync_thread = threading.Thread(target=_auto_sync_worker, daemon=True)
        self._sync_thread.start()
    
    def stop_auto_sync(self):
        self._running = False


# Instancia global
_sync_manager = None

def get_sync_manager() -> SyncManager:
    """Obtiene o crea la instancia global de SyncManager"""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
        # Mantenimiento: limpiar SYNC_ALL vacÃ­os al iniciar (evita borrados accidentales)
        try:
            from utils.file_handler import cargar_usuarios
            usuarios = cargar_usuarios() or {}
            for uid in usuarios.keys():
                try:
                    cleaned = _sync_manager.queue.clear_empty_sync_all_pending(str(uid))
                    if cleaned > 0:
                        _log(f"â›” [INICIO] Limpieza preventiva: eliminados {cleaned} SYNC_ALL vacÃ­os para usuario {uid}")
                    # TambiÃ©n convertir SYNC_ALL pendientes a CREATEs para mayor seguridad
                    try:
                        converted = _sync_manager.queue.convert_pending_sync_all_to_creates(str(uid))
                        if converted > 0:
                            _log(f"âš ï¸ [INICIO] Convertidos {converted} items desde SYNC_ALL pendientes a CREATE individuales para usuario {uid}")
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass
    return _sync_manager


# --- FUNCIONES PÃšBLICAS Y HELPERS ---

def auto_seed_inventario_precargado(username: str, branch_codes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Sube automaticamente el inventario local (precargado) a la nube por sucursal.

    Objetivo:
    - Si un branch tiene productos localmente pero en la nube aun no existe dataset 'productos'
      (o tiene menos filas que el local), sube el dataset completo haciendo merge (sin borrar lo remoto).
    - Evita subir repetidamente lo mismo guardando un estado simple en disco.

    Nota:
    - La nube guarda inventario por sucursal (codigo_dispositivo).
    """
    summary: Dict[str, Any] = {
        "total_branches": 0,
        "attempted": 0,
        "uploaded": 0,
        "skipped": 0,
        "errors": 0,
        "details": [],
    }

    try:
        from utils.file_handler import VISO_DIR, resolve_username
        from utils.api_handler import descargar_snapshot_dispositivo_nube, subir_dataset_dispositivo_nube

        resolved = resolve_username(username)
        branch_root = VISO_DIR / resolved / "branch_cache"
        if not branch_root.exists():
            return summary

        state_path = VISO_DIR / resolved / "data" / "auto_seed_inventario.json"
        state: Dict[str, Any] = {}
        try:
            if state_path.exists():
                with open(state_path, "r", encoding="utf-8") as f:
                    state = json.load(f) if f else {}
            if not isinstance(state, dict):
                state = {}
        except Exception:
            state = {}

        per_branch = state.get("per_branch") if isinstance(state.get("per_branch"), dict) else {}
        now_epoch = int(time.time())

        codes: List[str] = []
        if isinstance(branch_codes, list) and branch_codes:
            codes = [str(c or "").strip().upper() for c in branch_codes if str(c or "").strip()]
        else:
            try:
                for p in branch_root.glob("*/data/productos.json"):
                    try:
                        codes.append(str(p.parent.parent.name).strip().upper())
                    except Exception:
                        continue
            except Exception:
                codes = []

        codes = sorted(list({c for c in codes if c}))
        summary["total_branches"] = len(codes)

        mgr = get_sync_manager()
        if not mgr.check_internet():
            return summary

        for code in codes:
            detail = {"code": code, "local_count": 0, "remote_rows": None, "action": None, "msg": ""}
            try:
                local_path = branch_root / code / "data" / "productos.json"
                if not local_path.exists():
                    detail["action"] = "skip_no_local_file"
                    summary["skipped"] += 1
                    summary["details"].append(detail)
                    continue

                try:
                    with open(local_path, "r", encoding="utf-8") as f:
                        local_data = json.load(f)
                except Exception:
                    local_data = []

                if not isinstance(local_data, list):
                    local_data = []
                local_count = len(local_data)
                detail["local_count"] = local_count
                if local_count <= 0:
                    detail["action"] = "skip_empty_local"
                    summary["skipped"] += 1
                    summary["details"].append(detail)
                    continue

                prev = per_branch.get(code) if isinstance(per_branch, dict) else None
                if isinstance(prev, dict):
                    prev_count = int(prev.get("last_local_count", -1) or -1)
                    prev_ts = int(prev.get("last_ok_epoch", 0) or 0)
                    if prev_count == local_count and (now_epoch - prev_ts) < 600:
                        detail["action"] = "skip_recent_ok"
                        summary["skipped"] += 1
                        summary["details"].append(detail)
                        continue

                summary["attempted"] += 1

                remote_rows = None
                ok_meta, payload_meta, _msg_meta = descargar_snapshot_dispositivo_nube(
                    usuario_madre=resolved,
                    codigo_dispositivo=code,
                    dataset=None,
                    include_data=False,
                )
                if ok_meta and isinstance(payload_meta, dict):
                    ds_list = payload_meta.get("datasets") or []
                    if isinstance(ds_list, list):
                        for ds in ds_list:
                            if not isinstance(ds, dict):
                                continue
                            name = str(ds.get("dataset") or ds.get("name") or "").strip().lower()
                            if name == "productos":
                                try:
                                    remote_rows = int(ds.get("rows", 0) or 0)
                                except Exception:
                                    remote_rows = 0
                                break
                detail["remote_rows"] = remote_rows

                if remote_rows is not None and remote_rows >= local_count:
                    detail["action"] = "skip_remote_has_data"
                    summary["skipped"] += 1
                    per_branch[code] = {"last_local_count": local_count, "last_ok_epoch": now_epoch}
                    summary["details"].append(detail)
                    continue

                # Si no podemos verificar remoto, evitamos subir para no borrar por accidente.
                if remote_rows is None:
                    detail["action"] = "skip_remote_unknown"
                    summary["skipped"] += 1
                    summary["details"].append(detail)
                    continue

                remote_data: List[Dict] = []
                if remote_rows > 0:
                    ok_dl, payload_dl, msg_dl = descargar_snapshot_dispositivo_nube(
                        usuario_madre=resolved,
                        codigo_dispositivo=code,
                        dataset="productos",
                        include_data=True,
                    )
                    if ok_dl and isinstance(payload_dl, dict):
                        if isinstance(payload_dl.get("data"), list):
                            remote_data = payload_dl.get("data") or []
                        elif isinstance(payload_dl.get("snapshot"), dict):
                            snap = payload_dl.get("snapshot") or {}
                            maybe = snap.get("productos")
                            if isinstance(maybe, list):
                                remote_data = maybe
                    else:
                        detail["action"] = "skip_cannot_download_remote"
                        detail["msg"] = msg_dl
                        summary["skipped"] += 1
                        summary["details"].append(detail)
                        continue

                def _key(prod: Any) -> str:
                    if not isinstance(prod, dict):
                        return ""
                    for k in ("nombre", "codigo", "id"):
                        v = str(prod.get(k, "")).strip().lower()
                        if v:
                            return f"{k}:{v}"
                    return ""

                merged: List[Dict] = []
                idx: Dict[str, int] = {}

                for item in remote_data:
                    k = _key(item)
                    if not k:
                        continue
                    idx[k] = len(merged)
                    merged.append(item)

                for item in local_data:
                    k = _key(item)
                    if not k:
                        continue
                    if k in idx:
                        merged[idx[k]] = item
                    else:
                        idx[k] = len(merged)
                        merged.append(item)

                ok_up, msg_up, _resp = subir_dataset_dispositivo_nube(
                    usuario_madre=resolved,
                    codigo_dispositivo=code,
                    dataset="productos",
                    data=merged,
                    operacion="SYNC_ALL",
                    registro_id="bulk_merge",
                    contenido=merged,
                    updated_at=datetime.now().isoformat(timespec="seconds"),
                )
                if ok_up:
                    detail["action"] = "uploaded"
                    detail["msg"] = msg_up
                    summary["uploaded"] += 1
                    per_branch[code] = {"last_local_count": local_count, "last_ok_epoch": now_epoch}
                else:
                    detail["action"] = "error_upload"
                    detail["msg"] = msg_up
                    summary["errors"] += 1

                summary["details"].append(detail)
            except Exception as e:
                detail["action"] = "error_exception"
                detail["msg"] = str(e)
                summary["errors"] += 1
                summary["details"].append(detail)
                continue

        try:
            state["per_branch"] = per_branch
            state["last_run_epoch"] = now_epoch
            state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=True)
        except Exception:
            pass

        return summary
    except Exception:
        return summary

def restore_products_from_cloud(username: str) -> Optional[List[Dict]]:
    """
    IMPORTANTE: Llama a esta funciÃ³n al iniciar tu app si 'products.json' no existe.
    Descarga el inventario remoto en lugar de iniciar con una lista vacÃ­a.
    """
    try:
        from utils.file_handler import cargar_usuarios
        
        usuarios = cargar_usuarios() or {}
        usuario_id = None
        for uid, info in usuarios.items():
            if isinstance(info, dict) and info.get('username') == username:
                usuario_id = uid
                break
        
        if not usuario_id:
            _log("Usuario no encontrado por ID; intentando restauracion con username directo")
            usuario_id = str(username)
            
        mgr = get_sync_manager()
        return mgr.download_remote_inventory(str(usuario_id))
        
    except Exception as e:
        _log(f"Error en restore_products: {e}")
        return None

def sync_product_change(
    username: str,
    operacion: str,
    producto_data: dict = None,
    producto_nombre: str = None,
    producto_codigo: str = None,
) -> bool:
    """
    Helper para sincronizar cambios de productos.
    INCLUYE PROTECCIÃ“N: Evita encolar DELETEs si no hay nombre especÃ­fico.
    """
    try:
        from utils.file_handler import cargar_usuarios
        
        usuarios = cargar_usuarios() or {}
        usuario_id = None
        for uid, info in usuarios.items():
            if isinstance(info, dict) and info.get('username') == username:
                usuario_id = uid
                break
        
        if not usuario_id:
            return False
        
        # PROTECCIÃ“N CONTRA BORRADO MASIVO
        # Si la operaciÃ³n es DELETE pero no tenemos nombre, es peligroso.
        producto_nombre = str(producto_nombre or "").strip()
        producto_codigo = str(producto_codigo or "").strip()

        if operacion == 'DELETE' and not producto_nombre and not producto_codigo:
            _log("â›” [SEGURIDAD] sync_product_change bloqueÃ³ un DELETE sin nombre de producto.")
            return False

        sync_mgr = get_sync_manager()
        
        # Encolar cambio
        if operacion == 'DELETE':
            sync_mgr.queue_change(
                usuario_id=str(usuario_id),
                tipo_dato='productos',
                operacion='DELETE',
                registro_id=producto_codigo or producto_nombre,
                contenido={
                    'codigo': producto_codigo,
                    'nombre': producto_nombre,
                }
            )
        else:
            if not producto_data: return False
            sync_mgr.queue_change(
                usuario_id=str(usuario_id),
                tipo_dato='productos',
                operacion=operacion,
                registro_id=producto_data.get('nombre', ''),
                contenido=producto_data
            )
        
        # Sync en background (no bloqueante)
        threading.Thread(target=lambda: sync_mgr.sync_now(str(usuario_id)), daemon=True).start()
        
        return True
        
    except Exception as e:
        _log(f"Error en sync_product_change: {e}")
        return False




