import datetime
import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

from utils.file_handler import VISO_DIR, resolve_username

logger = logging.getLogger(__name__)

BACKUP_INTERVAL_DAYS = 7
BACKUP_RETENTION_COUNT = 12
STATE_FILENAME = "backup_schedule.json"
MANIFEST_FILENAME = "manifest.json"


def get_local_backup_dir(username: str) -> Path:
    resolved = resolve_username(username)
    return _user_root(resolved)


def _state_file(username: str) -> Path:
    return get_local_backup_dir(username) / STATE_FILENAME


def _load_state(username: str) -> Dict:
    path = _state_file(username)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
    except Exception:
        logger.exception("[LOCAL_BACKUP] No se pudo leer estado de backups")
    return {}


def _save_state(username: str, state: Dict) -> None:
    path = _state_file(username)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)


def _user_root(username: str) -> Path:
    return Path(VISO_DIR) / resolve_username(username)


def _iter_backup_sources(user_root: Path):
    if not user_root.exists():
        return
    for path in user_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel_parts = path.relative_to(user_root).parts
        except Exception:
            continue
        if not rel_parts:
            continue
        first = str(rel_parts[0]).lower()
        if first in {"temp", "temp_backup", "temp_import", "backups_locales"}:
            continue
        yield path


def _build_manifest(username: str, created_at: datetime.datetime, files: List[Path], user_root: Path) -> Dict:
    entries = []
    total_bytes = 0
    for file_path in files:
        try:
            stat = file_path.stat()
            size = int(stat.st_size or 0)
            total_bytes += size
            entries.append(
                {
                    "path": file_path.relative_to(user_root).as_posix(),
                    "size_bytes": size,
                    "modified_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        except Exception:
            logger.exception("[LOCAL_BACKUP] No se pudo registrar %s", file_path)

    return {
        "username": resolve_username(username),
        "backup_type": "weekly_local_automatic",
        "created_at": created_at.isoformat(),
        "created_at_label": created_at.strftime("%d/%m/%Y %H:%M:%S"),
        "source_root": str(user_root),
        "total_files": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
    }


def _create_zip(zip_path: Path, user_root: Path, files: List[Path], manifest: Dict) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    username_root = resolve_username(user_root.name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            arcname = Path(username_root) / file_path.relative_to(user_root)
            zipf.write(str(file_path), arcname.as_posix())
        zipf.writestr(MANIFEST_FILENAME, json.dumps(manifest, indent=2, ensure_ascii=False))


def _cleanup_old_backups(backup_dir: Path) -> None:
    try:
        zip_files = sorted(backup_dir.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        manifest_files = sorted(backup_dir.glob("backup_*.manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_file in zip_files[BACKUP_RETENTION_COUNT:]:
            try:
                old_file.unlink()
            except Exception:
                logger.exception("[LOCAL_BACKUP] No se pudo borrar %s", old_file)
        for old_file in manifest_files[BACKUP_RETENTION_COUNT:]:
            try:
                old_file.unlink()
            except Exception:
                logger.exception("[LOCAL_BACKUP] No se pudo borrar %s", old_file)
    except Exception:
        logger.exception("[LOCAL_BACKUP] Error limpiando backups antiguos")


def is_weekly_backup_due(username: str, now: datetime.datetime | None = None) -> Tuple[bool, str]:
    now = now or datetime.datetime.now()
    state = _load_state(username)
    last_backup_at = str(state.get("last_backup_at", "") or "").strip()
    if not last_backup_at:
        return True, "sin_backup_previo"
    try:
        last_dt = datetime.datetime.fromisoformat(last_backup_at)
    except Exception:
        return True, "estado_invalido"
    if (now - last_dt).days >= BACKUP_INTERVAL_DAYS:
        return True, "periodo_semanal_cumplido"
    return False, "backup_reciente"


def create_weekly_local_backup(username: str, now: datetime.datetime | None = None) -> Tuple[bool, str, str]:
    now = now or datetime.datetime.now()
    resolved = resolve_username(username)
    user_root = _user_root(resolved)
    if not user_root.exists():
        return False, "No existe la carpeta local del usuario para respaldar.", ""

    files = list(_iter_backup_sources(user_root) or [])
    if not files:
        return False, "No se encontraron archivos para respaldar.", ""

    backup_dir = get_local_backup_dir(resolved)
    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    zip_path = backup_dir / f"backup_{stamp}_{resolved}.zip"
    manifest_path = backup_dir / f"backup_{stamp}_{resolved}.manifest.json"
    manifest = _build_manifest(resolved, now, files, user_root)

    try:
        _create_zip(zip_path, user_root, files, manifest)
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
        _save_state(
            resolved,
            {
                "last_backup_at": now.isoformat(),
                "last_backup_zip": str(zip_path),
                "last_manifest": str(manifest_path),
            },
        )
        _cleanup_old_backups(backup_dir)
        return True, f"Backup local creado: {zip_path.name}", str(zip_path)
    except Exception as exc:
        logger.exception("[LOCAL_BACKUP] Error creando backup semanal")
        return False, f"Error creando backup local: {exc}", ""


def ensure_weekly_local_backup(username: str) -> Tuple[bool, str, str]:
    due, reason = is_weekly_backup_due(username)
    if not due:
        return True, f"Backup semanal omitido: {reason}", ""
    ok, message, backup_path = create_weekly_local_backup(username)
    return ok, f"{message} ({reason})", backup_path
