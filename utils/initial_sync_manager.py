"""
Initial Sync Manager - VISO

Reglas:
- Si `upload.json` existe con estado 1, no pedir subida inicial.
- Si la nube ya tiene datos/snapshots, marcar `upload.json` y no pedir subida.
- Si la instalacion local esta vacia, no forzar subida.
- Si hay que pedir subida inicial, crear/actualizar `upload.json` con estado 0.
- Solo pedir subida inicial cuando hay datos locales reales y la nube no tiene respaldo.
"""

import json
import logging
import os

from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


def write_upload_json_for_user(viso_dir, username_or_id, status="1") -> bool:
    """
    Crea o actualiza `upload.json` en:
      {viso_dir}/{resolved_username}/upload.json

    status:
      - "1" => subido / ya resuelto
      - "0" => pendiente
    """
    try:
        from utils.file_handler import resolve_username

        resolved = resolve_username(username_or_id)
        user_dir = os.path.join(str(viso_dir), str(resolved))
        upload_file = os.path.join(user_dir, "upload.json")
        os.makedirs(user_dir, exist_ok=True)

        status_str = str(status).strip() if status is not None else "0"
        uploaded_val = 1 if status_str == "1" else 0
        payload = {"uploaded": uploaded_val, "status": status_str}

        tmp_path = upload_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, upload_file)

        logger.info("upload.json actualizado a %s para %s", status_str, resolved)
        return True
    except Exception as e:
        logger.warning("No se pudo escribir upload.json: %s", e)
        return False


def mark_initial_sync_resolved(
    viso_dir,
    username_or_id,
    source="cloud_restore",
    datasets=None,
    branch_code="",
) -> bool:
    """
    Marca la instalacion como ya resuelta para subida inicial.
    Se usa al detectar datos reales en nube o al restaurarlos localmente.
    """
    ok = write_upload_json_for_user(viso_dir, username_or_id, status="1")

    try:
        from utils.sync_center_state import record_sync_center_event

        payload = {
            "source": str(source or "cloud_restore").strip() or "cloud_restore",
        }
        normalized_datasets = [
            str(ds).strip()
            for ds in (datasets or [])
            if str(ds or "").strip()
        ]
        if normalized_datasets:
            payload["datasets"] = normalized_datasets

        branch_code_text = str(branch_code or "").strip().upper()
        if branch_code_text:
            payload["codigo_dispositivo"] = branch_code_text

        record_sync_center_event(username_or_id, "pull", payload)
    except Exception:
        pass

    return ok


def mark_initial_sync_pending(viso_dir, username_or_id) -> bool:
    """Marca la instalacion como pendiente de subida inicial."""
    return write_upload_json_for_user(viso_dir, username_or_id, status="0")


class InitialSyncWorker(QThread):
    """Hilo para realizar la subida de datos sin congelar la UI."""

    finished = pyqtSignal(bool, str)

    def __init__(self, username, viso_dir, parent=None):
        super().__init__(parent)
        self.username = username
        self.viso_dir = viso_dir

    def run(self):
        try:
            logger.info("Iniciando subida inicial para: %s", self.username)

            from utils.file_handler import resolve_username
            from utils.api_handler import subir_dataset_dispositivo_nube
            from utils.sync_manager import get_sync_manager

            success_count = 0
            modules_attempted = 0
            modules_map = (
                ("clientes", "clientes.json"),
                ("pacientes", "pacientes.json"),
                ("graduaciones", "graduaciones.json"),
                ("productos", "productos.json"),
            )

            resolved_username = str(resolve_username(self.username) or "").strip() or str(self.username or "").strip()
            user_data_dir = os.path.join(self.viso_dir, resolved_username, "data")
            sync_mgr = get_sync_manager()
            device_ctx = sync_mgr._load_device_sync_context(str(self.username)) or {}
            usuario_madre = str(device_ctx.get("usuario_madre", resolved_username)).strip() or resolved_username
            codigo_dispositivo = sync_mgr._resolve_effective_device_code(str(self.username), device_ctx)
            device_info = {
                "tipo_dispositivo": str(device_ctx.get("tipo_dispositivo", "madre") or "madre"),
                "dispositivo_hijo_id": str(device_ctx.get("dispositivo_hijo_id", "") or ""),
                "dispositivo_hijo_nombre": str(device_ctx.get("dispositivo_hijo_nombre", "") or ""),
                "dispositivo_hijo_ciudad": str(device_ctx.get("dispositivo_hijo_ciudad", "") or ""),
                "username_local": resolved_username,
            }

            if not usuario_madre or not codigo_dispositivo:
                self.finished.emit(False, "No se pudo resolver el destino cloud de la subida inicial")
                return

            for dataset_name, filename in modules_map:
                file_path = os.path.join(user_data_dir, filename)
                if not os.path.exists(file_path):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if not data or (isinstance(data, list) and len(data) == 0):
                        continue
                except Exception:
                    continue

                modules_attempted += 1
                ok, message, _resp = subir_dataset_dispositivo_nube(
                    usuario_madre=usuario_madre,
                    codigo_dispositivo=codigo_dispositivo,
                    dataset=dataset_name,
                    data=data,
                    device_info=device_info,
                    endpoint_file="upload_device_snapshot_manual.php",
                )
                if ok:
                    success_count += 1
                else:
                    logger.error("Error subiendo %s a api.yhana.cloud: %s", filename, message)

            if modules_attempted > 0 and success_count >= modules_attempted:
                self.mark_as_uploaded("1")
                self.finished.emit(True, "Sincronizacion inicial exitosa")
            elif modules_attempted == 0:
                self.finished.emit(False, "No hay datos para subir todavia")
            else:
                self.finished.emit(False, f"Subida incompleta: {success_count}/{modules_attempted}")

        except Exception as e:
            logger.error("Error critico en InitialSyncWorker: %s", e)
            self.finished.emit(False, f"Error: {e}")

    def mark_as_uploaded(self, status="1"):
        """Actualiza upload.json al finalizar una subida inicial real."""
        write_upload_json_for_user(self.viso_dir, self.username, status=status)


class InitialSyncManager:
    """Orquestador de la sincronizacion inicial."""

    def __init__(self, username, viso_dir):
        self.username = username
        self.viso_dir = viso_dir
        try:
            from utils.file_handler import resolve_username

            resolved = resolve_username(username)
        except Exception:
            resolved = username

        self.resolved_username = str(resolved or "").strip() or str(username or "").strip()
        self.user_dir = os.path.join(viso_dir, self.resolved_username)
        self.upload_file = os.path.join(self.user_dir, "upload.json")
        self.worker = None

    def should_upload(self) -> bool:
        """Verifica si es necesario subir los datos."""
        if os.path.exists(self.upload_file):
            try:
                with open(self.upload_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                status = str(data.get("uploaded") or data.get("status") or "0")
                if status == "1":
                    return False
            except Exception:
                pass

        try:
            from utils.sync_manager import get_sync_manager

            sync_mgr = get_sync_manager()
            guard = sync_mgr.inspect_initial_sync_state(self.username)
            local_has_data = bool(guard.get("local_has_data"))
            cloud_has_data = bool(guard.get("cloud_has_data"))
            cloud_has_snapshots = bool(guard.get("cloud_has_snapshots"))
            cloud_inspected = bool(guard.get("cloud_inspected"))

            if cloud_has_data or cloud_has_snapshots:
                mark_initial_sync_resolved(
                    self.viso_dir,
                    self.username,
                    source="cloud_detected_on_startup",
                    datasets=list((guard.get("cloud_counts") or {}).keys()),
                )
                logger.info(
                    "Se detecto respaldo remoto real en la nube. "
                    "Se omite subida inicial por seguridad."
                )
                return False

            if bool(guard.get("cloud_has_remote_devices")) or int(guard.get("cloud_devices", 0) or 0) > 0:
                logger.info(
                    "Se detectaron dispositivos remotos pero sin datos/snapshots. "
                    "No se considerara sincronizacion inicial resuelta."
                )

            if not local_has_data:
                logger.info(
                    "Instalacion local sin datos reales. "
                    "Se omite subida inicial para evitar respaldos vacios."
                )
                return False

            if not cloud_inspected:
                logger.warning(
                    "No se pudo verificar la nube con certeza. "
                    "Por seguridad no se forzara subida inicial."
                )
                return False
        except Exception as e:
            logger.warning("Error en inspeccion de sincronizacion inicial: %s", e)
            return False

        mark_initial_sync_pending(self.viso_dir, self.username)
        logger.info("No se detecto subida previa local ni en nube")
        return True

    def start_sync_if_needed(self, callback=None):
        """Inicia el proceso de subida si es necesario."""
        if self.should_upload():
            return True
        return False
