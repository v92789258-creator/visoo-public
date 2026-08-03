def borrar_todos_menos_ultimos_remoto(username, endpoint_list, endpoint_delete, keep_last=2):
    """
    Borra todos los respaldos de un usuario en la nube, menos los ÃƒÆ’Ã†â€™Ã‚Âºltimos 'keep_last'.
    endpoint_list: URL para obtener la lista de archivos (debe devolver JSON con lista ordenada por fecha ascendente)
    endpoint_delete: URL para borrar un archivo (POST: id, filename)
    """
    # Obtener lista de archivos
    try:
        resp = requests.post(endpoint_list, data={"id": username})
        files = resp.json().get("files", [])
        # Mantener solo los ÃƒÆ’Ã†â€™Ã‚Âºltimos 'keep_last'
        to_delete = files[:-keep_last] if len(files) > keep_last else []
        deleted = 0
        for fname in to_delete:
            del_resp = requests.post(endpoint_delete, data={"id": username, "filename": fname})
            if del_resp.json().get("success"):
                deleted += 1
        return True, deleted
    except Exception as e:
        return False, f"Error al borrar respaldos: {e}"
import json
import os
import sys
import requests
import datetime
import base64
import binascii
from pathlib import Path
import zipfile
from dateutil.relativedelta import relativedelta
import shutil
import re
import time
import random
import threading
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from utils.runtime_status import tracked_operation
try:
    # Optional: used for DNI lookup "nitro" via eldni.com HTML parsing.
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None

# --- Constantes y Rutas Base ---


def _repair_mojibake_text(value):
    """Corrige texto mojibake frecuente en datos guardados."""
    text = str(value or "").strip()
    if not text:
        return ""

    replacements = {
        "Mi ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œptica": "Mi Ãƒâ€œptica",
        "ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ": "Ãƒâ€œ",
        "ÃƒÆ’Ã‚Â¡": "ÃƒÂ¡",
        "ÃƒÆ’Ã‚Â©": "ÃƒÂ©",
        "ÃƒÆ’Ã‚Â­": "ÃƒÂ­",
        "ÃƒÆ’Ã‚Â³": "ÃƒÂ³",
        "ÃƒÆ’Ã‚Âº": "ÃƒÂº",
        "ÃƒÆ’Ã‚Â": "ÃƒÂ",
        "ÃƒÆ’Ã¢â‚¬Â°": "Ãƒâ€°",
        "ÃƒÆ’Ã‚Â": "ÃƒÂ",
        "ÃƒÆ’Ã¢â‚¬Å“": "Ãƒâ€œ",
        "ÃƒÆ’Ã…Â¡": "ÃƒÅ¡",
        "ÃƒÆ’Ã‚Â±": "ÃƒÂ±",
        "ÃƒÆ’Ã¢â‚¬Ëœ": "Ãƒâ€˜",
        "Ãƒâ€šÃ‚Â¿": "Ã‚Â¿",
        "Ãƒâ€šÃ‚Â¡": "Ã‚Â¡",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    if any(ch in text for ch in ("ÃƒÆ’", "Ãƒâ€š", "ÃƒÂ¢")):
        for enc in ("latin1", "cp1252"):
            try:
                candidate = text.encode(enc).decode("utf-8")
            except Exception:
                continue
            if candidate and candidate != text:
                text = candidate
                break

    return text


def _decode_configuracion_optica_content(raw_text):
    """
    Decodifica contenido de configuracion_optica.txt.
    Soporta:
    - texto plano historico
    - contenido base64 (actual)
    - variante con prefijo 'b64:'
    """
    text = str(raw_text or "").strip()
    if not text:
        return ""

    candidate = text[4:].strip() if text.lower().startswith("b64:") else text
    compact = "".join(candidate.split())

    # Si no luce base64 valido, retornar tal cual.
    if not compact or (len(compact) % 4 != 0):
        return text
    if not re.fullmatch(r"[A-Za-z0-9+/=]+", compact):
        return text

    try:
        decoded_bytes = base64.b64decode(compact, validate=True)
        decoded = decoded_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return text

    # Heuristica: evitar falsos positivos con basura binaria.
    if any((ord(ch) < 32 and ch not in "\r\n\t") for ch in decoded):
        return text
    printable = sum(1 for ch in decoded if ch.isprintable() or ch in "\r\n\t")
    if decoded and (printable / max(1, len(decoded))) < 0.85:
        return text

    return decoded


def _encode_configuracion_optica_content(plain_text):
    """Codifica contenido a base64 UTF-8 para almacenamiento local."""
    text = str(plain_text or "")
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _extract_nombre_optica_from_content(content):
    """Extrae nombre_optica desde texto plano o formato key=value."""
    text = str(content or "").strip()
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""

    if len(lines) == 1 and "=" not in lines[0]:
        return lines[0]

    parsed = {}
    for line in lines:
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[str(k).strip()] = str(v).strip()

    if parsed:
        if parsed.get("nombre_optica"):
            return parsed["nombre_optica"]
        # Fallback: primer valor no vacio
        for v in parsed.values():
            if str(v).strip():
                return str(v).strip()

    return lines[0]


def _parse_configuracion_optica_content(content):
    """Parsea configuracion_optica.txt en formato key=value o texto plano."""
    text = str(content or "").strip()
    parsed = {
        "nombre_optica": "",
        "slogan": "",
        "direccion": "",
        "correo_electronico": "",
    }
    if not text:
        return parsed

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return parsed

    if len(lines) == 1 and "=" not in lines[0]:
        parsed["nombre_optica"] = _repair_mojibake_text(lines[0]).strip()
        return parsed

    extras = {}
    for line in lines:
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = str(k).strip()
        value = _repair_mojibake_text(v).strip()
        if key:
            extras[key] = value

    parsed["nombre_optica"] = str(
        extras.get("nombre_optica")
        or extras.get("nombre")
        or extras.get("config_optica")
        or ""
    ).strip()
    parsed["slogan"] = str(extras.get("slogan", "") or "").strip()
    parsed["direccion"] = str(extras.get("direccion", "") or "").strip()
    parsed["correo_electronico"] = str(
        extras.get("correo_electronico")
        or extras.get("correo")
        or extras.get("email")
        or ""
    ).strip()
    return parsed


def _build_configuracion_optica_plain_content(data, existing_plain=""):
    """Construye el contenido key=value preservando claves desconocidas."""
    preserved = {}
    try:
        for line in str(existing_plain or "").splitlines():
            line = line.strip()
            if line and "=" in line:
                k, v = line.split("=", 1)
                key = str(k).strip()
                if key:
                    preserved[key] = str(v).strip()
    except Exception:
        preserved = {}

    normalized = {
        "nombre_optica": _repair_mojibake_text(str(data.get("nombre_optica", "") or "")).strip() or "Mi Ã“ptica",
        "slogan": _repair_mojibake_text(str(data.get("slogan", "") or "")).strip(),
        "direccion": _repair_mojibake_text(str(data.get("direccion", "") or "")).strip(),
        "correo_electronico": _repair_mojibake_text(str(data.get("correo_electronico", "") or "")).strip(),
    }

    for key, value in normalized.items():
        preserved[key] = value

    ordered_keys = ["nombre_optica", "slogan", "direccion", "correo_electronico"]
    lines = [f"{key}={preserved.get(key, '')}" for key in ordered_keys]
    for key, value in preserved.items():
        if key not in ordered_keys:
            lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _is_default_optica_name(value):
    text = _repair_mojibake_text(value).strip().lower()
    normalized = re.sub(r"\s+", " ", text)
    return normalized in {"", "mi optica", "mi Ã³ptica", "viso"}

def is_program_files_path(path):
    """Verifica si una ruta estÃƒÆ’Ã†â€™Ã‚Â¡ dentro de Program Files"""
    program_files = Path("C:/Program Files")
    return Path(path).resolve().is_relative_to(program_files)

if getattr(sys, 'frozen', False):
    # Si estamos en el ejecutable congelado
    exe_dir = Path(sys.executable).parent
    if not is_program_files_path(exe_dir):
        # Si estamos fuera de Program Files (ej: en el escritorio), usar Program Files para internal
        INTERNAL_DIR = Path("C:/Program Files/VISO/_internal")
        BASE_DIR = exe_dir
    else:
        # Si estamos en Program Files, usar la misma ubicaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n
        BASE_DIR = exe_dir
        INTERNAL_DIR = BASE_DIR / "_internal"
else:
    # En desarrollo
    BASE_DIR = Path(__file__).resolve().parent.parent
    INTERNAL_DIR = BASE_DIR / "_internal"

# SIEMPRE usar BASE_DIR/VISO para datos de usuarios, no _internal
VISO_DIR = BASE_DIR / "VISO"
USUARIOS_FILE = VISO_DIR / ".usuarios.json"
SESION_FILE = VISO_DIR / "sesion.txt"
CLAVE_FILE = VISO_DIR / "clave_activacion.txt"
PASSWORD_SETUP_FILE = "password_setup.txt"
USER_PREFERENCES_FILE = VISO_DIR / "user_preferences.json"

# Compatibilidad: algunas partes del cÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³digo (legacy) esperan una constante
# llamada `VISO_DATA_DIR` que apuntaba a la carpeta de datos (string).
# Definimos un alias para no romper imports antiguos.
VISO_DATA_DIR = str(VISO_DIR / "data")
try:
    os.makedirs(VISO_DATA_DIR, exist_ok=True)
except Exception:
    pass

_CORRUPTION_LOGGER = logging.getLogger("viso.json_corruption")


def _safe_default_json_value(default):
    if isinstance(default, list):
        return []
    if isinstance(default, dict):
        return {}
    return default


def _corruption_log_file() -> Path:
    try:
        temp_dir = Path(VISO_DIR) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir / "json_corruption.log"
    except Exception:
        return Path("json_corruption.log")


def _report_json_corruption(message: str) -> None:
    line = f"[JSON_CORRUPT] {message}"
    try:
        print(line)
    except Exception:
        pass
    try:
        _CORRUPTION_LOGGER.warning(line)
    except Exception:
        pass
    try:
        with open(_corruption_log_file(), "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.datetime.now().isoformat()} {line}\n")
    except Exception:
        pass


def _quarantine_corrupt_json_file(path: Path) -> Path | None:
    try:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target = path.with_name(f"{path.stem}.corrupt_{stamp}{path.suffix}")
        shutil.move(str(path), str(target))
        return target
    except Exception:
        return None


def _read_json_file_raw(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_username_from_data_path(path: Path) -> str:
    try:
        relative = path.relative_to(VISO_DIR)
        parts = list(relative.parts)
        if parts:
            return str(parts[0] or "").strip()
    except Exception:
        pass
    return ""


def _restore_json_from_local_backups(path: Path):
    username = _extract_username_from_data_path(path)
    if not username:
        return None

    parent = path.parent
    backup_candidates = []
    backup_candidates.extend(parent.glob(f"{path.name}.bak_*"))
    backup_candidates.extend(parent.glob(f"{path.stem}.json.bak_*"))
    backup_candidates = sorted(backup_candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in backup_candidates:
        try:
            data = _read_json_file_raw(candidate)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            return str(candidate)
        except Exception:
            continue

    user_root = Path(VISO_DIR) / username
    zip_candidates = sorted(user_root.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    try:
        relative_inside_user = path.relative_to(user_root).as_posix()
    except Exception:
        relative_inside_user = ""
    if not relative_inside_user:
        return None

    expected_member = f"{resolve_username(username)}/{relative_inside_user}"
    for zip_path in zip_candidates:
        try:
            with zipfile.ZipFile(zip_path, "r") as zipf:
                if expected_member not in zipf.namelist():
                    continue
                raw = zipf.read(expected_member)
                parsed = json.loads(raw.decode("utf-8"))
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(parsed, fh, indent=2, ensure_ascii=False)
                return str(zip_path)
        except Exception:
            continue
    return None


def _load_json_file_safe(path: Path, default, expected_type=None):
    default_value = _safe_default_json_value(default)
    try:
        if not path.exists():
            return default_value
        data = _read_json_file_raw(path)
        if expected_type is not None and not isinstance(data, expected_type):
            return default_value
        return data
    except json.JSONDecodeError as exc:
        quarantined = _quarantine_corrupt_json_file(path)
        restored_from = _restore_json_from_local_backups(path)
        _report_json_corruption(
            f"Archivo corrupto detectado: {path}. "
            f"Movido a: {quarantined or 'no disponible'}. "
            f"Restaurado desde: {restored_from or 'sin respaldo'}. "
            f"Detalle: {exc}"
        )
        if restored_from:
            try:
                data = _read_json_file_raw(path)
                if expected_type is not None and not isinstance(data, expected_type):
                    return default_value
                return data
            except Exception:
                return default_value
        return default_value
    except (IOError, OSError):
        return default_value
    except Exception:
        return default_value

# Contexto de sucursal activo por usuario (en memoria, por sesiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n)
_BRANCH_CONTEXT_LOCK = threading.RLock()
_ACTIVE_BRANCH_BY_USER = {}  # {resolved_username: {"code": "...", "label": "..."}}

# Evitar que loaders (ej: refresh workers) disparen restores desde nube en bucle.
# Key: (resolved_username, dataset) -> epoch seconds.
_CLOUD_RESTORE_LAST = {}

def _should_attempt_cloud_restore(username: str, dataset: str, cooldown_seconds: int = 30) -> bool:
    try:
        key = (str(resolve_username(username)), str(dataset or "").strip().lower())
        now = float(time.time())
        last = float(_CLOUD_RESTORE_LAST.get(key, 0) or 0)
        if now - last < float(cooldown_seconds):
            return False
        _CLOUD_RESTORE_LAST[key] = now
        return True
    except Exception:
        return False


def _mark_initial_sync_resolved_local(username: str, source: str = "", datasets=None, branch_code: str = "") -> bool:
    """
    Marca la instalaciÃ³n local como ya resuelta para el flujo de subida inicial.
    Se usa cuando esta PC confirma datos reales desde la nube.
    """
    try:
        from utils.initial_sync_manager import mark_initial_sync_resolved

        return bool(
            mark_initial_sync_resolved(
                str(VISO_DIR),
                username,
                source=source or "cloud_restore",
                datasets=list(datasets or []),
                branch_code=branch_code,
            )
        )
    except Exception:
        return False

# Archivos que se redirigen al cache de sucursal cuando hay una sucursal activa
_BRANCH_REDIRECT_FILES = {
    "clientes.json",
    "pacientes.json",
    "productos.json",
    "ventas.json",
    "kardex.json",
    "citas.json",
    "metodos_pago.json",
    "servicios.json",
    "graduaciones.json",
    "optometras.json",
    "brands.json",
    "caja.json",
}

def cargar_preferencias():
    """Carga las preferencias del usuario desde el archivo."""
    try:
        if os.path.exists(USER_PREFERENCES_FILE):
            with open(USER_PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

def guardar_preferencias(preferencias):
    """Guarda las preferencias del usuario en el archivo."""
    try:
        with open(USER_PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(preferencias, f, indent=2)
        return True
    except Exception:
        return False

def crear_directorios():
    """Crea la estructura de directorios base de la aplicaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n si no existe."""
    os.makedirs(VISO_DIR, exist_ok=True)
    os.makedirs(VISO_DIR / "boletas", exist_ok=True)
    os.makedirs(VISO_DIR / "expedientes", exist_ok=True)
    os.makedirs(VISO_DIR / "images", exist_ok=True)
    os.makedirs(VISO_DIR / "reportes" / "expedientes", exist_ok=True)
    os.makedirs(VISO_DIR / "reportes" / "boletas", exist_ok=True)

def crear_directorios_usuario(username):
    """Crea la carpeta de datos para un usuario espec?fico y su estructura interna."""
    resolved = resolve_username(username)
    user_data_dir = VISO_DIR / resolved / "data"
    os.makedirs(user_data_dir, exist_ok=True)
    return user_data_dir


def get_branch_cache_data_dir(username, branch_code):
    """Ruta del cache local para una sucursal seleccionada."""
    resolved = resolve_username(username)
    code = str(branch_code or "").strip().upper()
    if not code:
        return VISO_DIR / resolved / "data"
    return VISO_DIR / resolved / "branch_cache" / code / "data"


def _load_json_list_file(path: Path) -> list:
    """Carga una lista JSON desde disco; retorna [] en error o tipo invalido."""
    data = _load_json_file_safe(path, [], expected_type=list)
    return data if isinstance(data, list) else []


def _merge_unique_items(items: list) -> list:
    """
    Mezcla listas evitando solo duplicados exactos.

    Importante: no deduplicar por nombre/codigo entre sucursales, porque
    el dashboard global debe consolidar registros de todas las opticas.
    """
    merged = []
    seen = set()

    for item in items:
        try:
            key = f"raw:{json.dumps(item, ensure_ascii=False, sort_keys=True)}"
        except Exception:
            key = f"raw:{str(item)}"

        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    return merged


def _merge_unique_productos(items: list) -> list:
    """
    Dedup especial para productos en vistas globales/dashboard.

    Objetivo:
    - Evitar mezclar el mismo catalogo cuando existe en local, branch_cache y nube.
    - Mantener un solo registro por producto real.
    - No sumar stock entre duplicados; se conserva el mayor stock encontrado.
    """
    merged: list = []
    by_key: dict = {}

    def _norm(value) -> str:
        return str(value or "").strip()

    def _is_empty(value) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, dict)):
            return len(value) == 0
        return False

    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _key(item) -> str:
        if not isinstance(item, dict):
            return ""

        for key_name in ("codigo", "id", "producto_id", "sku"):
            value = _norm(item.get(key_name, ""))
            if value:
                return f"{key_name}:{value.lower()}"

        nombre = _norm(item.get("nombre", "")).lower()
        categoria = _norm(item.get("categoria", "")).lower()
        marca = _norm(item.get("marca", "")).lower()
        material = _norm(item.get("material", "")).lower()
        precio = _norm(item.get("precio_venta", "") or item.get("precio", "")).lower()

        if nombre:
            return f"fallback:{nombre}|{categoria}|{marca}|{material}|{precio}"
        return ""

    for item in items or []:
        key = _key(item)
        if not key:
            merged.append(item)
            continue

        idx = by_key.get(key)
        if idx is None:
            by_key[key] = len(merged)
            merged.append(item)
            continue

        base = merged[idx]
        if isinstance(base, dict) and isinstance(item, dict):
            out = dict(base)
            for field_name, field_value in item.items():
                if field_name == "stock":
                    current_stock = _safe_float(out.get("stock"))
                    incoming_stock = _safe_float(field_value)
                    if incoming_stock is not None and (
                        current_stock is None or incoming_stock > current_stock
                    ):
                        out["stock"] = field_value
                    continue

                if field_name not in out or _is_empty(out.get(field_name)):
                    out[field_name] = field_value

            merged[idx] = out

    return _merge_unique_items(merged)


def _merge_unique_clientes(items: list) -> list:
    """
    Dedup especial para clientes en vista global (Todas las sucursales).

    Objetivo:
    - Evitar duplicados por DNI/DNI_RUC al consolidar branch_cache.
    - Mantener un registro por persona y completar campos faltantes cuando sea posible.

    Nota: Esto aplica SOLO a la lista consolidada (read-only); no toca archivos en disco.
    """
    merged: list = []
    by_key: dict = {}

    def _norm(v) -> str:
        return str(v or "").strip()

    def _key(item) -> str:
        if not isinstance(item, dict):
            return ""
        for k in ("dni", "dni_ruc", "id", "codigo"):
            v = _norm(item.get(k, ""))
            if v:
                return f"{k}:{v.lower()}"
        correo = _norm(item.get("correo", ""))
        if correo:
            return f"correo:{correo.lower()}"
        nombre = _norm(item.get("nombre", ""))
        if nombre:
            return f"nombre:{nombre.lower()}"
        return ""

    def _is_empty(v) -> bool:
        if v is None:
            return True
        if isinstance(v, str):
            return v.strip() == ""
        if isinstance(v, (list, dict)):
            return len(v) == 0
        return False

    for item in items or []:
        k = _key(item)
        if not k:
            # Sin clave, caer a comportamiento legacy (dedup exacto) para no perder items raros.
            merged.append(item)
            continue

        idx = by_key.get(k)
        if idx is None:
            by_key[k] = len(merged)
            merged.append(item)
            continue

        # Fusion: completar faltantes del existente con el duplicado
        base = merged[idx]
        if isinstance(base, dict) and isinstance(item, dict):
            out = dict(base)
            for kk, vv in item.items():
                if kk not in out or _is_empty(out.get(kk)):
                    out[kk] = vv
            merged[idx] = out

    # Segunda pasada: quitar duplicados exactos introducidos por items sin clave
    return _merge_unique_items(merged)


def _load_consolidated_branch_list_dataset(username: str, filename: str, include_local: bool = True) -> list:
    """
    Carga dataset combinado (local madre + cache de todas las sucursales).
    Usado solo para vistas globales (read-only).
    """
    resolved = resolve_username(username)
    merged = []

    if include_local:
        local_file = VISO_DIR / resolved / "data" / str(filename)
        merged = list(_load_json_list_file(local_file))

    branch_root = VISO_DIR / resolved / "branch_cache"
    try:
        if branch_root.exists():
            for fp in branch_root.glob(f"*/data/{filename}"):
                merged.extend(_load_json_list_file(fp))
    except Exception:
        pass

    try:
        base = str(filename or "").strip().lower()
        if base == "productos.json":
            return _merge_unique_productos(merged)
        if base == "clientes.json":
            return _merge_unique_clientes(merged)
    except Exception:
        pass

    return _merge_unique_items(merged)


def get_active_branch_context(username):
    """Obtiene contexto activo de sucursal para el usuario."""
    resolved = resolve_username(username)
    with _BRANCH_CONTEXT_LOCK:
        ctx = _ACTIVE_BRANCH_BY_USER.get(resolved, {})
        if isinstance(ctx, dict):
            return {
                "code": str(ctx.get("code", "")).strip().upper(),
                "label": str(ctx.get("label", "")).strip()
            }
        return {"code": "", "label": ""}


def get_effective_branch_context(username):
    """
    Resuelve la sucursal efectiva para el usuario actual.
    Prioridad:
    1) contexto activo en memoria
    2) config_dispositivo del equipo trabajador/hijo
    3) unica sucursal activa conocida del usuario
    """
    ctx = get_active_branch_context(username) or {}
    code = str((ctx or {}).get("code", "")).strip().upper()
    label = str((ctx or {}).get("label", "")).strip()
    if code:
        return {"code": code, "label": label or code}

    try:
        cfg_path = get_user_file_path(username, "config_dispositivo.json")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                raw = (
                    cfg.get("codigo_dispositivo_hijo")
                    or cfg.get("codigo_dispositivo_trabajador")
                    or cfg.get("codigo_dispositivo")
                    or ""
                )
                code = str(raw or "").strip().upper()
                if code:
                    name = str(
                        cfg.get("dispositivo_hijo_nombre")
                        or cfg.get("nombre_optica")
                        or cfg.get("sucursal_nombre")
                        or "Sucursal"
                    ).strip() or "Sucursal"
                    city = str(
                        cfg.get("dispositivo_hijo_ciudad")
                        or cfg.get("ciudad")
                        or ""
                    ).strip()
                    label = f"{name} - {city} ({code})" if city else f"{name} ({code})"
                    return {"code": code, "label": label}
    except Exception:
        pass

    try:
        dh_path = get_user_file_path(username, "dispositivos_hijos.json")
        if dh_path.exists():
            with open(dh_path, "r", encoding="utf-8") as f:
                dh = json.load(f)
            if isinstance(dh, list):
                activos = [
                    d for d in dh
                    if isinstance(d, dict)
                    and str(d.get("estado", "activo")).strip().lower() != "bloqueado"
                    and str(d.get("codigo_dispositivo", "")).strip()
                ]
                if len(activos) == 1:
                    item = activos[0]
                    code = str(item.get("codigo_dispositivo", "")).strip().upper()
                    name = str(item.get("nombre_optica", "") or "Sucursal").strip() or "Sucursal"
                    city = str(item.get("ciudad", "") or "").strip()
                    label = f"{name} - {city} ({code})" if city else f"{name} ({code})"
                    return {"code": code, "label": label}
    except Exception:
        pass

    return {"code": "", "label": ""}


def set_active_branch_context(username, branch_code="", branch_label=""):
    """Activa contexto de sucursal para redirigir datos operativos."""
    resolved = resolve_username(username)
    code = str(branch_code or "").strip().upper()
    label = str(branch_label or "").strip()

    with _BRANCH_CONTEXT_LOCK:
        if code:
            _ACTIVE_BRANCH_BY_USER[resolved] = {"code": code, "label": label}
        else:
            _ACTIVE_BRANCH_BY_USER.pop(resolved, None)


def clear_active_branch_context(username):
    """Limpia contexto activo de sucursal (vuelve a datos locales madre)."""
    set_active_branch_context(username, "", "")


def get_branch_cache_tag(username) -> str:
    """Sufijo para claves de cache que dependen de sucursal."""
    ctx = get_active_branch_context(username)
    code = str(ctx.get("code", "")).strip().upper()
    return f"|branch:{code}" if code else ""


def save_branch_snapshot_datasets(username, branch_code, snapshot):
    """
    Guarda datasets descargados para una sucursal en cache local.

    Args:
        username: usuario madre
        branch_code: c?digo de sucursal/dispositivo
        snapshot: dict {dataset: data}

    Returns:
        dict resumen {dataset: rows}
    """
    if not isinstance(snapshot, dict):
        return {}

    target_dir = get_branch_cache_data_dir(username, branch_code)
    os.makedirs(target_dir, exist_ok=True)
    summary = {}

    for dataset, data in snapshot.items():
        name = str(dataset or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9_]{2,64}", name):
            continue

        file_path = target_dir / f"{name}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            summary[name] = len(data) if isinstance(data, list) else (1 if data is not None else 0)
        except Exception:
            continue

    if summary:
        try:
            from utils.sync_center_state import record_sync_center_event

            record_sync_center_event(
                username,
                "pull",
                {
                    "source": "snapshot_cache",
                    "codigo_dispositivo": str(branch_code or "").strip().upper(),
                    "datasets": sorted(summary.keys()),
                    "counts": summary,
                },
            )
        except Exception:
            pass

    return summary


def clear_branch_runtime_caches():
    """Limpia caches en memoria para forzar recarga desde disco."""
    try:
        from utils.fast_loader import _inventory_cache
        _inventory_cache.clear()
    except Exception:
        pass

    try:
        from utils.data_cache_manager import clear_global_cache
        clear_global_cache()
    except Exception:
        pass


def _resolve_usuario_madre_cloud(username):
    """Resuelve el usuario madre correcto para consultar snapshots cloud."""
    try:
        cfg_path = get_user_file_path(username, "config_dispositivo.json")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                madre = str(cfg.get("usuario_madre", "") or "").strip()
                if madre:
                    return madre
    except Exception:
        pass
    return str(resolve_username(username) or "").strip() or str(username or "").strip()


def _download_snapshot_payload_for_dataset(usuario_madre: str, code: str, dataset_name: str):
    """Descarga payload de snapshot intentando varias convenciones de dataset."""
    try:
        from utils.api_handler import descargar_snapshot_dispositivo_nube
    except Exception:
        return None

    code = str(code or "").strip().upper()
    if not code:
        return None

    base = str(dataset_name or "").strip().lower()
    for ds in (base, f"{base}.json", None):
        try:
            ok_dl, payload_dl, _msg_dl = descargar_snapshot_dispositivo_nube(
                usuario_madre=usuario_madre,
                codigo_dispositivo=code,
                dataset=ds,
                include_data=True,
            )
            if ok_dl and isinstance(payload_dl, dict):
                return payload_dl
        except Exception:
            continue
    return None


def _normalize_snapshot_list_dataset(value, dataset_name: str):
    """Normaliza respuestas snapshot de datasets tipo lista."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        dataset_name = str(dataset_name or "").strip().lower()
        if dataset_name and dataset_name in value:
            return _normalize_snapshot_list_dataset(value.get(dataset_name), dataset_name)
        if "data" in value:
            return _normalize_snapshot_list_dataset(value.get("data"), dataset_name)
        vals = list(value.values())
        if vals and all(isinstance(v, dict) for v in vals):
            return vals
        return []
    return []


def _extract_list_dataset_from_snapshot(payload, dataset_name: str):
    """Extrae dataset tipo lista desde payload cloud."""
    if not isinstance(payload, dict):
        return None

    data = payload.get("data")
    if isinstance(data, (list, dict)) or data is None:
        return _normalize_snapshot_list_dataset(data, dataset_name)

    snap = payload.get("snapshot")
    if isinstance(snap, dict):
        val = snap.get(str(dataset_name or "").strip().lower())
        if isinstance(val, (list, dict)) or val is None:
            return _normalize_snapshot_list_dataset(val, dataset_name)

    val2 = payload.get(str(dataset_name or "").strip().lower())
    if isinstance(val2, (list, dict)) or val2 is None:
        return _normalize_snapshot_list_dataset(val2, dataset_name)

    return None


def _resolve_restore_branch_code(username):
    """Obtiene la sucursal activa/configurada para restores puntuales."""
    try:
        ctx = get_active_branch_context(username) or {}
        code = str(ctx.get("code", "")).strip().upper()
        if code:
            return code
    except Exception:
        pass

    try:
        cfg_path = get_user_file_path(username, "config_dispositivo.json")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                raw = (
                    cfg.get("codigo_dispositivo_hijo")
                    or cfg.get("codigo_dispositivo")
                    or cfg.get("codigo_dispositivo_trabajador")
                    or ""
                )
                code = str(raw or "").strip().upper()
                if code:
                    return code
    except Exception:
        pass

    try:
        dh_path = get_user_file_path(username, "dispositivos_hijos.json")
        if dh_path.exists():
            with open(dh_path, "r", encoding="utf-8") as f:
                dh = json.load(f)
            if isinstance(dh, list):
                activos = [
                    d for d in dh
                    if isinstance(d, dict)
                    and str(d.get("estado", "activo")).strip().lower() != "bloqueado"
                    and str(d.get("codigo_dispositivo", "")).strip()
                ]
                if len(activos) == 1:
                    return str(activos[0].get("codigo_dispositivo", "")).strip().upper()
    except Exception:
        pass

    return ""


def _restore_list_dataset_from_cloud(username, dataset_name: str, filename: str, remote_only: bool = False):
    """
    Restaura un dataset tipo lista desde snapshots cloud.
    Soporta:
    - sucursal activa/configurada
    - madre global (MADRE-USER)
    - sucursales remotas activas
    """
    with tracked_operation(
        f"cloud-restore:{dataset_name}:{username}",
        f"Descargando {dataset_name} desde nube",
        "download",
    ):
        try:
            from utils.api_handler import listar_dispositivos_hijos_remoto, listar_snapshots_dispositivos_nube
        except Exception:
            return []

        usuario_madre = _resolve_usuario_madre_cloud(username)

        def _load_from_branch_cache(code):
            try:
                branch_dir = get_branch_cache_data_dir(username, code)
                fp = Path(branch_dir) / str(filename)
                if fp.exists():
                    with open(fp, "r", encoding="utf-8") as f:
                        data_local = json.load(f)
                    if isinstance(data_local, list):
                        return data_local
            except Exception:
                pass
            return None

        branch_code = _resolve_restore_branch_code(username)
        if branch_code:
            payload = _download_snapshot_payload_for_dataset(usuario_madre, branch_code, dataset_name)
            if payload is not None:
                dataset_data = _extract_list_dataset_from_snapshot(payload, dataset_name)
                if dataset_data is not None:
                    try:
                        save_branch_snapshot_datasets(username, branch_code, {dataset_name: dataset_data})
                        clear_branch_runtime_caches()
                    except Exception:
                        pass
                    if remote_only:
                        if isinstance(dataset_data, list):
                            return dataset_data
                        return []
                    restored = _load_from_branch_cache(branch_code)
                    if restored is not None:
                        if isinstance(restored, list) and restored:
                            _mark_initial_sync_resolved_local(
                                username,
                                source="cloud_snapshot_restore",
                                datasets=[dataset_name],
                                branch_code=branch_code,
                            )
                        return restored
            if remote_only:
                return []
            restored = _load_from_branch_cache(branch_code)
            if restored is not None:
                if isinstance(restored, list) and restored:
                    _mark_initial_sync_resolved_local(
                        username,
                        source="cloud_snapshot_cache",
                        datasets=[dataset_name],
                        branch_code=branch_code,
                    )
                return restored
            return []

        if not branch_code:
            candidate_codes = []
            remote_items = []

            def _add_code(value):
                code = str(value or "").strip().upper()
                if code and code not in candidate_codes:
                    candidate_codes.append(code)

            try:
                base = re.sub(r"[^A-Za-z0-9]+", "", str(resolve_username(username)).upper()) or "USER"
                _add_code(f"MADRE-{base}"[:80])
            except Exception:
                pass

            try:
                cfg_path = get_user_file_path(username, "config_dispositivo.json")
                if cfg_path.exists():
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    if isinstance(cfg, dict):
                        _add_code(cfg.get("codigo_dispositivo"))
            except Exception:
                pass

            for code_try in list(candidate_codes):
                payloadm = _download_snapshot_payload_for_dataset(usuario_madre, code_try, dataset_name)
                if payloadm is None:
                    continue
                dataset_madre = _extract_list_dataset_from_snapshot(payloadm, dataset_name)
                if dataset_madre is None:
                    continue
                if isinstance(dataset_madre, list):
                    remote_items.extend(dataset_madre)
                try:
                    save_branch_snapshot_datasets(username, code_try, {dataset_name: dataset_madre})
                except Exception:
                    pass

            ok, devices, _msg = listar_dispositivos_hijos_remoto(usuario_madre)
            if not ok or not isinstance(devices, list) or not devices:
                try:
                    ok_s, snap_devices, _msg_s = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
                    if ok_s and isinstance(snap_devices, list) and snap_devices:
                        ok, devices = True, snap_devices
                except Exception:
                    pass

            if ok and isinstance(devices, list):
                for d in devices:
                    if not isinstance(d, dict):
                        continue
                    if str(d.get("estado", "activo")).strip().lower() == "bloqueado":
                        continue
                    code = str(d.get("codigo_dispositivo", "")).strip().upper()
                    if not code:
                        continue
                    payload2 = _download_snapshot_payload_for_dataset(usuario_madre, code, dataset_name)
                    if payload2 is None:
                        continue
                    dataset_data = _extract_list_dataset_from_snapshot(payload2, dataset_name)
                    if dataset_data is None:
                        continue
                    if isinstance(dataset_data, list):
                        remote_items.extend(dataset_data)
                    try:
                        save_branch_snapshot_datasets(username, code, {dataset_name: dataset_data})
                    except Exception:
                        pass

            try:
                clear_branch_runtime_caches()
            except Exception:
                pass

            if remote_only:
                try:
                    base = str(filename or "").strip().lower()
                    if base == "productos.json":
                        return _merge_unique_productos(remote_items)
                    if base == "clientes.json":
                        return _merge_unique_clientes(remote_items)
                except Exception:
                    pass
                return _merge_unique_items(remote_items)

            try:
                merged = _load_consolidated_branch_list_dataset(username, filename)
                if isinstance(merged, list):
                    if merged:
                        _mark_initial_sync_resolved_local(
                            username,
                            source="cloud_snapshot_restore",
                            datasets=[dataset_name],
                        )
                    return merged
            except Exception:
                pass

        return []


MODO_BASICO_PAGE_OPTIONS = {
    0: "Inicio",
    4: "Ventas",
    1: "Pacientes",
    2: "Nueva Graduacion",
    9: "Clientes",
    3: "Inventario",
    6: "Calendario",
    10: "Configuracion",
}

MODO_BASICO_HOME_ACTION_OPTIONS = {
    4: "Registrar venta",
    2: "Nueva graduacion",
    1: "Pacientes",
    9: "Clientes",
    3: "Inventario",
    6: "Calendario",
    10: "Configuracion",
}

MODO_BASICO_DEFAULT_CONFIG = {
    "modo_basico": False,
    "visible_pages": [0, 4, 1, 2, 10],
    "quick_actions": [4, 2],
}

PLANTILLAS_VENTAS_DISPONIBLES = {
    "ventas_default": {
        "nombre": "Ventas ClÃ¡sica",
        "descripcion": "Resumen diario en una sola pÃ¡gina con diseÃ±o comercial.",
        "ruta": os.path.join("DISEÑOSPDF", "ventas.html"),
    },
    "ventas_cuadernillo": {
        "nombre": "Ventas Cuadernillo",
        "descripcion": "Formato tipo cuadernillo para reportes diarios mÃ¡s extensos.",
        "ruta": os.path.join("DISEÑOSPDF", "ventasdeldia", "cuadernillo.html"),
    },
}


def _sanitize_modo_basico_pages(values, allowed_options, fallback):
    allowed = set(allowed_options.keys())
    sanitized = []
    for value in values if isinstance(values, list) else []:
        try:
            page = int(value)
        except (TypeError, ValueError):
            continue
        if page in allowed and page not in sanitized:
            sanitized.append(page)
    if not sanitized:
        sanitized = [int(v) for v in fallback if int(v) in allowed]
    return sanitized


def get_modo_basico_config(username):
    """Obtiene la configuraciÃ³n consolidada del modo bÃ¡sico."""
    config = dict(MODO_BASICO_DEFAULT_CONFIG)
    try:
        modo_file = get_user_file_path(username, "modo_basico.json")
        if modo_file.exists():
            with open(modo_file, 'r', encoding='utf-8') as f:
                stored = json.load(f) or {}
            if isinstance(stored, dict):
                config["modo_basico"] = bool(stored.get("modo_basico", config["modo_basico"]))
                config["visible_pages"] = _sanitize_modo_basico_pages(
                    stored.get("visible_pages"),
                    MODO_BASICO_PAGE_OPTIONS,
                    MODO_BASICO_DEFAULT_CONFIG["visible_pages"],
                )
                config["quick_actions"] = _sanitize_modo_basico_pages(
                    stored.get("quick_actions"),
                    MODO_BASICO_HOME_ACTION_OPTIONS,
                    MODO_BASICO_DEFAULT_CONFIG["quick_actions"],
                )
    except Exception:
        pass

    visible_pages = list(config.get("visible_pages", []) or [])
    for forced_page in (0, 10):
        if forced_page not in visible_pages:
            visible_pages.append(forced_page)
    config["visible_pages"] = visible_pages

    quick_actions = [
        page for page in list(config.get("quick_actions", []) or [])
        if page in MODO_BASICO_HOME_ACTION_OPTIONS
    ]
    if not quick_actions:
        quick_actions = list(MODO_BASICO_DEFAULT_CONFIG["quick_actions"])
    config["quick_actions"] = quick_actions
    return config


def save_modo_basico_config(username, config_updates=None):
    """Guarda la configuraciÃ³n del modo bÃ¡sico preservando valores existentes."""
    try:
        current = get_modo_basico_config(username)
        updates = config_updates if isinstance(config_updates, dict) else {}

        if "modo_basico" in updates:
            current["modo_basico"] = bool(updates.get("modo_basico"))

        if "visible_pages" in updates:
            current["visible_pages"] = _sanitize_modo_basico_pages(
                updates.get("visible_pages"),
                MODO_BASICO_PAGE_OPTIONS,
                current.get("visible_pages", MODO_BASICO_DEFAULT_CONFIG["visible_pages"]),
            )
            for forced_page in (0, 10):
                if forced_page not in current["visible_pages"]:
                    current["visible_pages"].append(forced_page)

        if "quick_actions" in updates:
            current["quick_actions"] = _sanitize_modo_basico_pages(
                updates.get("quick_actions"),
                MODO_BASICO_HOME_ACTION_OPTIONS,
                current.get("quick_actions", MODO_BASICO_DEFAULT_CONFIG["quick_actions"]),
            )

        modo_file = get_user_file_path(username, "modo_basico.json")
        os.makedirs(modo_file.parent, exist_ok=True)
        with open(modo_file, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando modo_basico: {e}")
        return False


def is_modo_basico(username):
    """Verifica si el modo bÃ¡sico estÃ¡ activado para el usuario."""
    return bool(get_modo_basico_config(username).get("modo_basico", False))


def set_modo_basico(username, is_active):
    """Guarda el estado del modo bÃ¡sico para el usuario."""
    return save_modo_basico_config(username, {"modo_basico": bool(is_active)})


def get_modo_basico_visible_pages(username):
    return list(get_modo_basico_config(username).get("visible_pages", []) or [])


def get_modo_basico_quick_actions(username):
    return list(get_modo_basico_config(username).get("quick_actions", []) or [])


def get_plantillas_ventas_disponibles():
    return dict(PLANTILLAS_VENTAS_DISPONIBLES)


def obtener_ruta_recurso(*relative_parts):
    """
    Resuelve recursos empaquetados o en desarrollo sin depender de os.getcwd().
    Prioriza:
    1. BASE_DIR
    2. INTERNAL_DIR
    3. sys._MEIPASS
    4. cwd actual (fallback legacy)
    """
    cleaned_parts = []
    for part in relative_parts:
        text = str(part or "").strip()
        if text:
            cleaned_parts.extend(Path(text).parts)

    if not cleaned_parts:
        return str(BASE_DIR)

    candidates = []
    roots_to_try = [BASE_DIR]
    try:
        roots_to_try.append(BASE_DIR.parent)
        roots_to_try.append(BASE_DIR.parent.parent)
    except Exception:
        pass
    roots_to_try.append(INTERNAL_DIR)

    for root in roots_to_try:
        try:
            candidates.append(Path(root, *cleaned_parts))
        except Exception:
            pass

    try:
        meipass_root = getattr(sys, "_MEIPASS", None)
        if meipass_root:
            candidates.append(Path(meipass_root, *cleaned_parts))
    except Exception:
        pass

    try:
        candidates.append(Path(os.getcwd(), *cleaned_parts))
    except Exception:
        pass

    seen = set()
    fallback = None
    for candidate in candidates:
        try:
            normalized = str(candidate.resolve(strict=False))
        except Exception:
            normalized = str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        if fallback is None:
            fallback = candidate
        if candidate.exists():
            return str(candidate)

    return str(fallback or Path(*cleaned_parts))


def cargar_plantilla_ventas_seleccionada(username):
    try:
        config_path = get_user_file_path(username, "plantilla_reportes_config.json")
        if config_path.exists():
            config = _load_json_file_safe(config_path, {}, expected_type=dict)
            template_key = str(config.get("plantilla_ventas", "") or "").strip()
            if template_key in PLANTILLAS_VENTAS_DISPONIBLES:
                return template_key
    except Exception:
        pass
    return "ventas_default"


def guardar_plantilla_ventas_seleccionada(username, template_key):
    key = str(template_key or "").strip()
    if key not in PLANTILLAS_VENTAS_DISPONIBLES:
        raise ValueError(f"Plantilla de ventas invÃ¡lida: {template_key}")

    config_path = get_user_file_path(username, "plantilla_reportes_config.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = _load_json_file_safe(config_path, {}, expected_type=dict)
    if not isinstance(config, dict):
        config = {}
    config["plantilla_ventas"] = key
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    return True


def obtener_ruta_plantilla_ventas(username):
    template_key = cargar_plantilla_ventas_seleccionada(username)
    template_info = PLANTILLAS_VENTAS_DISPONIBLES.get(template_key) or PLANTILLAS_VENTAS_DISPONIBLES["ventas_default"]
    template_relative_path = template_info.get("ruta", os.path.join("DISEÑOSPDF", "ventas.html"))
    resolved = obtener_ruta_recurso(template_relative_path)
    if os.path.exists(resolved):
        return resolved

    fallback_paths = [
        obtener_ruta_recurso(os.path.join("DISEÑOSPDF", "ventas.html")),
        obtener_ruta_recurso(os.path.join("DISEÑOSPDF", "venta.html")),
        obtener_ruta_recurso(os.path.join("DISEÑOSPDF", "ventasdeldia", "cuadernillo.html")),
    ]
    for candidate in fallback_paths:
        if os.path.exists(candidate):
            return candidate
    return resolved

def get_user_file_path(username, filename):
    """
    Genera la ruta completa a un archivo de datos para un usuario espec?fico.

    Si hay una sucursal activa, redirige archivos operativos al cache de esa sucursal.
    """
    resolved = resolve_username(username)
    base_data_dir = VISO_DIR / resolved / "data"
    name = str(filename or "")

    # Redirecci?n a sucursal seleccionada (solo para datasets operativos)
    if name:
        basename = Path(name).name.lower()
        branch_ctx = get_active_branch_context(resolved)
        branch_code = str(branch_ctx.get("code", "")).strip().upper()
        if branch_code and basename:
            branch_dir = get_branch_cache_data_dir(resolved, branch_code)
            # 1) RedirecciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n explÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­cita de datasets operativos principales.
            if basename in _BRANCH_REDIRECT_FILES:
                return branch_dir / basename
            # 2) Soporte "absoluto": si el dataset JSON existe en cache de sucursal,
            #    usarlo aunque no estÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© en la lista principal.
            if basename.endswith(".json"):
                branch_file = branch_dir / basename
                if branch_file.exists():
                    return branch_file

    return base_data_dir / name


def resolve_username(username_or_id):
    """Resuelve si el valor dado es un user_id (clave en .usuarios.json) y devuelve
    el nombre de usuario canÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³nico. Si no estÃƒÆ’Ã†â€™Ã‚Â¡ en .usuarios.json, devuelve el valor tal cual.
    Esto permite que las funciones que aceptan 'username' trabajen con tanto el id como
    el nombre real sin romper la ubicaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de datos.
    """
    try:
        # Si el valor ya es None o vacÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­o, devolver 'default' para evitar errores
        if not username_or_id:
            return str(username_or_id)
        # Intentar leer el mapeo de usuarios
        if USUARIOS_FILE.exists():
            data = _load_json_file_safe(USUARIOS_FILE, {}, expected_type=dict)
            # Si username_or_id es una clave en el JSON (user id), devolver su username
            if username_or_id in data:
                entry = data.get(username_or_id)
                if isinstance(entry, dict) and entry.get('username'):
                    return str(entry.get('username'))
        # Si no estÃƒÆ’Ã†â€™Ã‚Â¡ mapeado, devolver tal cual
        return str(username_or_id)
    except Exception:
        return str(username_or_id)

def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso, funciona para desarrollo y para PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = str(Path(__file__).resolve().parent.parent)
    return os.path.join(base_path, relative_path)


def ensure_placeholder_in_project_images():
    """Copia el placeholder interno (utils/img/placeholder.png) a la carpeta principal `images/`
    dentro del proyecto (`BASE_DIR/images/`) si no existe allÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­. Esto facilita que la UI cargue
    imÃƒÆ’Ã†â€™Ã‚Â¡genes desde una ubicaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n conocida (VISO/images/). La funciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n es segura y silenciosa.
    Retorna la ruta destino final (string).
    """
    try:
        # Ruta al placeholder empaquetado
        placeholder_src = resource_path(os.path.join('utils', 'img', 'placeholder.png'))
        # Ruta destino en la carpeta images del proyecto (no la carpeta VISO/images)
        # Usaremos BASE_DIR/`images` en lugar de VISO/images para respetar la peticiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n del usuario
        project_root = Path(__file__).resolve().parent.parent
        dest_dir = project_root / 'images'
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = dest_dir / 'placeholder.png'

        # Copiar solo si no existe o si el archivo de origen es mÃƒÆ’Ã†â€™Ã‚Â¡s nuevo
        if os.path.exists(placeholder_src):
            try:
                src_mtime = os.path.getmtime(placeholder_src)
            except Exception:
                src_mtime = None
            if not dest_path.exists():
                shutil.copy2(placeholder_src, dest_path)
            else:
                try:
                    dest_mtime = os.path.getmtime(dest_path)
                except Exception:
                    dest_mtime = None
                if src_mtime and dest_mtime and src_mtime > dest_mtime:
                    shutil.copy2(placeholder_src, dest_path)
        return str(dest_path)
    except Exception:
        # No queremos que falle el inicio de la app por esto; retornar ruta por defecto
        try:
            return str(project_root / 'images' / 'placeholder.png')
        except Exception:
            return os.path.join(os.path.dirname(__file__), 'img', 'placeholder.png')

# --- Funciones de Carga y Guardado ---

def cargar_usuarios():
    """Carga la lista de usuarios y contraseÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±as (global)."""
    data = _load_json_file_safe(USUARIOS_FILE, {}, expected_type=dict)
    return data if isinstance(data, dict) else {}



def _resolve_usuario_id_for_sync(username: str) -> str:
    """Resuelve el usuario_id (clave de .usuarios.json) para usarlo como llave estable.

    Si no existe mapeo, usa el username como fallback (compatibilidad).
    """
    target = str(username or "").strip()
    if not target:
        return ""
    if target.isdigit():
        return target
    try:
        usuarios = cargar_usuarios() or {}
        for uid, info in usuarios.items():
            if isinstance(info, dict) and str(info.get('username', '')).strip() == target:
                return str(uid)
    except Exception:
        pass
    try:
        if SESION_FILE.exists():
            raw = SESION_FILE.read_text(encoding="utf-8", errors="ignore").strip()
            parts = raw.split(":")
            if len(parts) >= 2 and str(parts[0]).strip() == target:
                candidate = str(parts[1]).strip()
                if candidate:
                    return candidate
    except Exception:
        pass
    return target


def _resolve_branch_code_for_sync(username: str, branch_code: str = "") -> str:
    """Resuelve el codigo de sucursal/dispositivo para asociar el dataset a la tienda correcta."""
    bc = str(branch_code or "").strip().upper()
    if bc == "__GLOBAL__":
        return ""
    if bc:
        return bc
    try:
        ctx = get_active_branch_context(username) or {}
        bc = str(ctx.get("code", "")).strip().upper()
    except Exception:
        bc = ""
    if bc:
        return bc
    try:
        cfg_path = get_user_file_path(username, "config_dispositivo.json")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                raw = (
                    cfg.get("codigo_dispositivo_hijo")
                    or cfg.get("codigo_dispositivo_trabajador")
                    or cfg.get("codigo_dispositivo")
                    or ""
                )
                bc = str(raw or "").strip().upper()
    except Exception:
        bc = ""
    if bc:
        return bc
    try:
        fp = get_user_file_path(username, "dispositivos_hijos.json")
        if fp.exists():
            with open(fp, "r", encoding="utf-8") as f:
                devs = json.load(f)
            if isinstance(devs, list):
                activos = [
                    d for d in devs
                    if isinstance(d, dict)
                    and str(d.get("estado", "activo")).strip().lower() != "bloqueado"
                    and str(d.get("codigo_dispositivo", "")).strip()
                ]
                if len(activos) == 1:
                    bc = str(activos[0].get("codigo_dispositivo", "")).strip().upper()
    except Exception:
        bc = ""
    return bc


def _queue_sync_all_dataset_bg(username: str, tipo_dato: str, dataset_key: str, dataset_value, branch_code: str = ""):
    """Encola SYNC_ALL para un dataset y dispara sync_now en background."""

    def _worker():
        with tracked_operation(
            f"cloud-upload:{tipo_dato}:{username}",
            f"Subiendo {tipo_dato} a la nube",
            "upload",
        ):
            try:
                from utils.sync_manager import get_sync_manager

                sync_mgr = get_sync_manager()
                usuario_id = _resolve_usuario_id_for_sync(username)
                bc = _resolve_branch_code_for_sync(username, branch_code=branch_code)
                registro_id = f"bulk:{bc}" if bc else "bulk"

                contenido = {str(dataset_key): dataset_value}
                meta = {}
                if bc:
                    meta["branch_code"] = bc
                try:
                    is_empty_dataset = (
                        (isinstance(dataset_value, list) and len(dataset_value) == 0)
                        or (isinstance(dataset_value, dict) and len(dataset_value) == 0)
                        or (isinstance(dataset_value, str) and dataset_value.strip() == "")
                    )
                except Exception:
                    is_empty_dataset = False
                if str(tipo_dato or "").strip().lower() == "ventas" and is_empty_dataset:
                    # Permitir que una anulacion de la ultima venta vacie el dataset remoto.
                    meta["force_empty_sync"] = True
                if meta:
                    contenido["_meta"] = meta

                # Coalescer: mantener solo el ultimo SYNC_ALL por dataset+sucursal
                try:
                    if hasattr(sync_mgr, "queue") and hasattr(sync_mgr.queue, "clear_pending_sync_all_for_dataset"):
                        sync_mgr.queue.clear_pending_sync_all_for_dataset(
                            usuario_id=str(usuario_id),
                            tipo_dato=str(tipo_dato),
                            registro_id=str(registro_id),
                        )
                except Exception:
                    pass

                sync_mgr.queue_change(
                    usuario_id=str(usuario_id),
                    tipo_dato=str(tipo_dato),
                    operacion='SYNC_ALL',
                    registro_id=str(registro_id),
                    contenido=contenido,
                )
                sync_mgr.sync_now(str(usuario_id))
            except Exception:
                pass

    try:
        threading.Thread(target=_worker, daemon=True).start()
    except Exception:
        pass

def guardar_usuarios(usuarios):
    """Guarda la lista de usuarios y contraseÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±as (global)."""
    with open(USUARIOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

def cargar_clave_activacion():
    """Carga la clave de activaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n si existe."""
    try:
        if CLAVE_FILE.exists():
            with open(CLAVE_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except (IOError, json.JSONDecodeError):
        pass
    return None

def guardar_clave_activacion(clave):
    """Guarda la clave de activaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n en un archivo local."""
    os.makedirs(CLAVE_FILE.parent, exist_ok=True)
    with open(CLAVE_FILE, 'w', encoding='utf-8') as f:
        f.write(clave)
        
def cargar_password_setup(username):
    """Carga la contraseÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±a de un solo uso de un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    password_file = get_user_file_path(username, "password_setup.txt")
    try:
        if password_file.exists():
            with open(password_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except IOError:
        pass
    return None

def guardar_password_setup(username, password):
    """Guarda la contraseÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±a de un solo uso para un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    password_file = get_user_file_path(username, "password_setup.txt")
    os.makedirs(password_file.parent, exist_ok=True)
    with open(password_file, "w", encoding='utf-8') as f:
        f.write(password)

def cargar_logo_optica(username):
    """Carga la ruta del logo de un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    logo_file_path = get_user_file_path(username, "logo.png")
    if logo_file_path.exists():
        return str(logo_file_path)
    return ""

def guardar_logo_optica(username, source_path):
    """Guarda una imagen como logo en la carpeta del usuario."""
    logo_dir = get_user_file_path(username, "")
    os.makedirs(logo_dir, exist_ok=True)
    destination_path = os.path.join(logo_dir, "logo.png")
    shutil.copy2(source_path, destination_path)
    return destination_path

def cargar_tamano_logo(username):
    """Carga el tamaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±o guardado del logo (en pÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­xeles)."""
    config_file = get_user_file_path(username, "logo_config.json")
    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tamano = data.get('tamano_logo', 150)
                print(f"[LOGO_CONFIG] TamaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±o del logo cargado: {tamano}px desde {config_file}")
                return tamano
        else:
            print(f"[LOGO_CONFIG] Archivo no existe: {config_file}, usando default 150px")
    except (IOError, json.JSONDecodeError) as e:
        print(f"[LOGO_CONFIG] Error cargando tamaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±o: {e}, usando default 150px")
    return 150  # Default size

def guardar_tamano_logo(username, tamano):
    """Guarda el tamaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±o del logo (en pÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­xeles)."""
    config_file = get_user_file_path(username, "logo_config.json")
    os.makedirs(config_file.parent, exist_ok=True)
    
    # Cargar config existente
    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
    except (IOError, json.JSONDecodeError):
        config = {}
    
    # Actualizar tamaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±o
    tamano_limitado = max(50, min(400, tamano))
    config['tamano_logo'] = tamano_limitado
    
    # Guardar
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"[LOGO_CONFIG] TamaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±o del logo guardado: {tamano_limitado}px en {config_file}")

def cargar_pacientes(username):
    """Carga pacientes del contexto actual.

    Orden de prioridad:
    1) Si hay internet: nube solamente.
       - Con sucursal activa/configurada: descarga snapshot de esa sucursal.
       - En modo global (sin sucursal activa): descarga de sucursal madre + todas las sucursales activas y consolida solo lo remoto.
    2) Si no hay internet: local (fast_loader / archivo).
    3) Fallback legacy (API antigua) si existe usuario_id numerico y hay conectividad.

    Nota: La restauracion por snapshot no encola sync.
    """

    pacientes_file = get_user_file_path(username, "pacientes.json")
    has_internet = False

    try:
        from utils.sync_manager import get_sync_manager

        sync_mgr = get_sync_manager()
        has_internet = bool(sync_mgr.check_internet())
    except Exception:
        has_internet = False

    def _load_local_pacientes():
        try:
            from utils.fast_loader import cargar_pacientes_rapido
            pacientes_locales = cargar_pacientes_rapido(username)
            if isinstance(pacientes_locales, list) and pacientes_locales:
                return pacientes_locales
        except ImportError:
            pass
        except Exception:
            pass

        try:
            if pacientes_file.exists():
                pacientes_locales = _load_json_file_safe(pacientes_file, [], expected_type=list)
                if isinstance(pacientes_locales, list):
                    return pacientes_locales
        except Exception:
            pass
        return []

    def _merge_remote_patient_lists(items: list) -> list:
        merged = []
        by_key = {}

        def _norm(v) -> str:
            return str(v or "").strip()

        def _is_empty(v) -> bool:
            if v is None:
                return True
            if isinstance(v, str):
                return v.strip() == ""
            if isinstance(v, (list, dict)):
                return len(v) == 0
            return False

        def _key(item) -> str:
            if not isinstance(item, dict):
                return ""
            # PRIORIDAD 1: UUID (CÃ³digo Ãºnico absoluto)
            uuid_val = _norm(item.get("uuid", ""))
            if uuid_val:
                return f"uuid:{uuid_val}"
            
            # PRIORIDAD 2: DNI Real
            dni = _norm(item.get("dni", ""))
            nombre = _norm(item.get("nombre", "")).lower()
            if dni and dni != "00000000":
                return f"dni:{dni}"
            
            # PRIORIDAD 3: Casos anÃ³nimos (DNI 00000000)
            if dni == "00000000":
                fecha = _norm(item.get("fecha", ""))
                return f"anon:{nombre}|{fecha}|{id(item)}"
            
            if nombre:
                return f"nombre:{nombre}"
            return ""

        for item in items or []:
            key = _key(item)
            if not key:
                merged.append(item)
                continue

            idx = by_key.get(key)
            if idx is None:
                by_key[key] = len(merged)
                merged.append(item)
                continue

            base = merged[idx]
            if isinstance(base, dict) and isinstance(item, dict):
                out = dict(base)
                for field_name, field_value in item.items():
                    if field_name not in out or _is_empty(out.get(field_name)):
                        out[field_name] = field_value
                merged[idx] = out

        return merged

    if not has_internet:
        return _load_local_pacientes()

    # 1) Snapshot remoto (modo carpeta). Este restore NO encola sync.
    try:
        from utils.api_handler import descargar_snapshot_dispositivo_nube, listar_dispositivos_hijos_remoto

        def _resolve_usuario_madre_cloud():
            # En dispositivos hijo/trabajador, el folder en nube esta bajo el usuario_madre.
            try:
                cfg_path = get_user_file_path(username, "config_dispositivo.json")
                if cfg_path.exists():
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    if isinstance(cfg, dict):
                        madre = str(cfg.get("usuario_madre", "") or "").strip()
                        if madre:
                            return madre
            except Exception:
                pass
            return str(resolve_username(username) or "").strip() or str(username or "").strip()

        usuario_madre = _resolve_usuario_madre_cloud()

        def _download_snapshot_payload(code: str, dataset_name: str):
            """Intenta varias convenciones de nombre de dataset y fallback a snapshot completo."""
            code = str(code or "").strip().upper()
            if not code:
                return None
            base = str(dataset_name or "").strip().lower()
            for ds in (base, f"{base}.json", None):
                try:
                    ok_dl, payload_dl, _msg_dl = descargar_snapshot_dispositivo_nube(
                        usuario_madre=usuario_madre,
                        codigo_dispositivo=code,
                        dataset=ds,  # None => snapshot completo
                        include_data=True,
                    )
                    if ok_dl and isinstance(payload_dl, dict):
                        return payload_dl
                except Exception:
                    continue
            return None

        def _normalize_pacientes(value):
            if value is None:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                if "pacientes" in value:
                    return _normalize_pacientes(value.get("pacientes"))
                if "data" in value:
                    return _normalize_pacientes(value.get("data"))
                vals = list(value.values())
                if vals and all(isinstance(v, dict) for v in vals):
                    return vals
                return []
            return []

        def _extract_pacientes(payload):
            if not isinstance(payload, dict):
                return None
            data = payload.get("data")
            if isinstance(data, (list, dict)) or data is None:
                return _normalize_pacientes(data)
            snap = payload.get("snapshot")
            if isinstance(snap, dict):
                val = snap.get("pacientes")
                if isinstance(val, (list, dict)) or val is None:
                    return _normalize_pacientes(val)
            val2 = payload.get("pacientes")
            if isinstance(val2, (list, dict)) or val2 is None:
                return _normalize_pacientes(val2)
            return None

        def _resolve_branch_code():
            try:
                ctx = get_active_branch_context(username) or {}
                code = str(ctx.get("code", "")).strip().upper()
                if code:
                    return code
            except Exception:
                pass
            try:
                cfg_path = get_user_file_path(username, "config_dispositivo.json")
                if cfg_path.exists():
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    if isinstance(cfg, dict):
                        raw = (
                            cfg.get("codigo_dispositivo_hijo")
                            or cfg.get("codigo_dispositivo")
                            or cfg.get("codigo_dispositivo_trabajador")
                            or ""
                        )
                        code = str(raw or "").strip().upper()
                        if code:
                            return code
            except Exception:
                pass
            try:
                dh_path = get_user_file_path(username, "dispositivos_hijos.json")
                if dh_path.exists():
                    with open(dh_path, "r", encoding="utf-8") as f:
                        dh = json.load(f)
                    if isinstance(dh, list):
                        activos = [
                            d
                            for d in dh
                            if isinstance(d, dict)
                            and str(d.get("estado", "activo")).strip().lower() != "bloqueado"
                            and str(d.get("codigo_dispositivo", "")).strip()
                        ]
                        if len(activos) == 1:
                            return str(activos[0].get("codigo_dispositivo", "")).strip().upper()
            except Exception:
                pass
            return ""

        def _load_from_branch_cache(code):
            try:
                branch_dir = get_branch_cache_data_dir(username, code)
                fp = Path(branch_dir) / "pacientes.json"
                if fp.exists():
                    with open(fp, "r", encoding="utf-8") as f:
                        data_local = json.load(f)
                    if isinstance(data_local, list):
                        return data_local
            except Exception:
                pass
            return None

        branch_code = _resolve_branch_code()
        if branch_code:
            payload = _download_snapshot_payload(branch_code, "pacientes")
            if payload is not None:
                pacientes_data = _extract_pacientes(payload)
                if pacientes_data is not None:
                    try:
                        save_branch_snapshot_datasets(username, branch_code, {"pacientes": pacientes_data})
                        clear_branch_runtime_caches()
                    except Exception:
                        pass
                    return pacientes_data
            return []

        if not branch_code:
            remote_lists = []
            # Intentar primero el dataset de la sucursal madre (modo global).
            try:
                base = re.sub(r"[^A-Za-z0-9]+", "", str(resolve_username(username)).upper()) or "USER"
                madre_code = f"MADRE-{base}"[:80]

                # Compatibilidad: restaurar tambien si el madre guardo con codigo_dispositivo VISO-... (config).
                extra_codes = []
                try:
                    cfg_path = get_user_file_path(username, "config_dispositivo.json")
                    if cfg_path.exists():
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        if isinstance(cfg, dict):
                            cfg_code = str(cfg.get("codigo_dispositivo", "") or "").strip().upper()
                            if cfg_code and cfg_code != madre_code:
                                extra_codes.append(cfg_code)
                except Exception:
                    pass

                for code_try in [madre_code] + extra_codes:
                    payloadm = _download_snapshot_payload(code_try, "pacientes")
                    if payloadm is None:
                        continue
                    pacientes_madre = _extract_pacientes(payloadm)
                    if pacientes_madre is None:
                        continue
                    remote_lists.extend(pacientes_madre if isinstance(pacientes_madre, list) else [])
                    try:
                        save_branch_snapshot_datasets(username, code_try, {"pacientes": pacientes_madre})
                    except Exception:
                        pass
            except Exception:
                pass

            ok, devices, _msg = listar_dispositivos_hijos_remoto(usuario_madre)

            # Fallback: si el listado legacy falla, listar directamente los snapshots existentes en nube.
            if not ok or not isinstance(devices, list) or not devices:
                try:
                    from utils.api_handler import listar_snapshots_dispositivos_nube
                    ok_s, snap_devices, _msg_s = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
                    if ok_s and isinstance(snap_devices, list) and snap_devices:
                        ok, devices = True, snap_devices
                except Exception:
                    pass

            if ok and isinstance(devices, list):
                for d in devices:
                    if not isinstance(d, dict):
                        continue
                    if str(d.get("estado", "activo")).strip().lower() == "bloqueado":
                        continue
                    code = str(d.get("codigo_dispositivo", "")).strip().upper()
                    if not code:
                        continue
                    payload2 = _download_snapshot_payload(code, "pacientes")
                    if payload2 is None:
                        continue
                    pacientes_data = _extract_pacientes(payload2)
                    if pacientes_data is None:
                        continue
                    remote_lists.extend(pacientes_data if isinstance(pacientes_data, list) else [])
                    try:
                        save_branch_snapshot_datasets(username, code, {"pacientes": pacientes_data})
                    except Exception:
                        pass

            try:
                clear_branch_runtime_caches()
            except Exception:
                pass

            merged = _merge_remote_patient_lists(remote_lists)
            if isinstance(merged, list):
                return merged
    except Exception:
        pass

    # 3) Fallback legacy (API antigua). Evitar errores si usuario_id no es numerico.
    try:
        from utils.api_handler import obtener_pacientes_remoto

        usuario_id = None
        try:
            usuarios = cargar_usuarios() or {}
            for uid, info in usuarios.items():
                if isinstance(info, dict) and str(info.get("username", "")).strip() == str(username or "").strip():
                    usuario_id = str(uid)
                    break
        except Exception:
            usuario_id = None

        branch_code = ""
        try:
            branch_ctx = get_effective_branch_context(username) or {}
            branch_code = str((branch_ctx or {}).get("code", "")).strip().upper()
        except Exception:
            branch_code = ""

        pacientes_remotos = obtener_pacientes_remoto(
            str(usuario_id or "").strip() or str(username or "").strip(),
            codigo_dispositivo=branch_code or None,
        )
        if isinstance(pacientes_remotos, list) and pacientes_remotos:
            guardar_pacientes(username, pacientes_remotos)
            _mark_initial_sync_resolved_local(
                username,
                source="legacy_remote_restore",
                datasets=["pacientes"],
            )
            return pacientes_remotos
    except Exception:
        pass

    return _load_local_pacientes()

def _load_dashboard_local_list(username, filename: str, fast_loader_name: str = "", fast_start: bool = False):
    """
    Carga una lista para dashboard usando solo datos locales/branch_cache.
    No hace requests ni restores remotos.
    """
    try:
        ctx = get_active_branch_context(username)
        branch_code = str((ctx or {}).get("code", "")).strip().upper()
    except Exception:
        branch_code = ""

    if branch_code:
        if fast_loader_name:
            try:
                from utils import fast_loader
                fast_loader_fn = getattr(fast_loader, fast_loader_name, None)
                if callable(fast_loader_fn):
                    data = fast_loader_fn(username)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass

        try:
            data = _load_json_list_file(get_user_file_path(username, filename))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    if fast_start:
        if fast_loader_name:
            try:
                from utils import fast_loader
                fast_loader_fn = getattr(fast_loader, fast_loader_name, None)
                if callable(fast_loader_fn):
                    data = fast_loader_fn(username)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass

        try:
            data = _load_json_list_file(get_user_file_path(username, filename))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    try:
        merged = _load_consolidated_branch_list_dataset(username, filename)
        if isinstance(merged, list) and merged:
            return merged
    except Exception:
        pass

    try:
        data = _load_json_list_file(get_user_file_path(username, filename))
        if isinstance(data, list):
            return data
    except Exception:
        pass

    return []


def _dashboard_has_internet() -> bool:
    try:
        from utils.sync_manager import get_sync_manager

        return bool(get_sync_manager().check_internet())
    except Exception:
        return False

def cargar_pacientes_dashboard(username, allow_remote_restore: bool = True, fast_start: bool = False):
    """
    Carga pacientes para dashboard:
    - Prioriza datos locales para velocidad.
    - Si se permite, intenta actualizar desde la nube.
    """
    local_data = _load_dashboard_local_list(
        username,
        "pacientes.json",
        fast_loader_name="cargar_pacientes_rapido",
        fast_start=fast_start,
    )
    
    if allow_remote_restore and _dashboard_has_internet():
        try:
            restored = cargar_pacientes(username)
            if isinstance(restored, list) and restored:
                return restored
        except Exception:
            pass

    return local_data if isinstance(local_data, list) else []


def cargar_clientes_dashboard(username, allow_remote_restore: bool = True, fast_start: bool = False):
    """
    Carga clientes para vistas de UI priorizando datos locales/branch_cache.
    Solo intenta restore remoto si no hay nada local y se permite expresamente.
    """
    local_data = _load_dashboard_local_list(username, "clientes.json", fast_start=fast_start)
    if isinstance(local_data, list) and local_data:
        return local_data

    if not allow_remote_restore:
        return local_data if isinstance(local_data, list) else []

    try:
        restored = cargar_clientes(username)
        if isinstance(restored, list):
            return restored
    except Exception:
        pass

    return local_data if isinstance(local_data, list) else []


def cargar_clientes_editable(username):
    """
    Carga solo el dataset local editable de clientes para la vista actual.
    - Con sucursal activa: usa el archivo redirigido de esa sucursal.
    - En madre/global: usa solo `data/clientes.json` local.
    Nunca consolida sucursales ni hace restore remoto.
    """
    try:
        clientes_file = get_user_file_path(username, "clientes.json")
        if clientes_file.exists():
            with open(clientes_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []

def guardar_pacientes(username, pacientes, branch_code: str = ""):
    """
    Guarda los pacientes para un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico.
    Intenta sincronizar con servidor si hay internet, sino guarda localmente.
    """
    try:
        # Guardar localmente primero (SIEMPRE)
        pacientes_file = get_user_file_path(username, "pacientes.json")
        os.makedirs(pacientes_file.parent, exist_ok=True)

        # Snapshot previo para detectar deltas y evitar SYNC_ALL en ediciones simples.
        pacientes_previos = []
        try:
            if pacientes_file.exists():
                with open(pacientes_file, 'r', encoding='utf-8') as f:
                    prev = json.load(f)
                if isinstance(prev, list):
                    pacientes_previos = prev
        except Exception:
            pacientes_previos = []

        payload = pacientes if isinstance(pacientes, list) else []
        try:
            payload = [dict(p) if isinstance(p, dict) else p for p in payload]
        except Exception:
            payload = pacientes if isinstance(pacientes, list) else []

        tmp_path = pacientes_file.with_suffix('.json.tmp')
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            os.replace(str(tmp_path), str(pacientes_file))
            
            # ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ LIMPIAR CACHE despuÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s de guardar para que los cambios se vean en la UI
            try:
                from utils.fast_loader import _inventory_cache
                cache_key = f"pacientes:{username}"
                _inventory_cache._cache.pop(cache_key, None)
                print(f"[CACHE] ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Cache de pacientes limpiado para {username}", flush=True)
            except ImportError:
                pass
            except Exception as e:
                print(f"[CACHE] ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡Ãƒâ€šÃ‚Â  Error limpiando cache: {e}", flush=True)
                
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
        
        # Detectar deltas (CREATE/UPDATE/DELETE) por clave estable (uuid/dni/id/codigo)
        def _paciente_registro_id(item):
            if not isinstance(item, dict):
                return ""
            # PRIORIDAD 1: UUID (Identificador universal Ãºnico)
            uuid_val = str(item.get("uuid", "")).strip()
            if uuid_val:
                return uuid_val
            # PRIORIDAD 2: Otros campos estables para pacientes antiguos
            for key in ("dni", "id", "codigo", "nombre"):
                value = str(item.get(key, "")).strip()
                if value:
                    return value
            return ""

        def _paciente_key(item):
            if not isinstance(item, dict):
                return ""
            # PRIORIDAD 1: UUID (Permite diferenciar pacientes con el mismo DNI)
            uuid_val = str(item.get("uuid", "")).strip().lower()
            if uuid_val:
                return f"uuid:{uuid_val}"
            # PRIORIDAD 2: DNI (Para compatibilidad con registros antiguos)
            for key in ("dni", "id", "codigo"):
                value = str(item.get(key, "")).strip().lower()
                if value:
                    return f"{key}:{value}"
            nombre = str(item.get("nombre", "")).strip().lower()
            if nombre:
                return f"nombre:{nombre}"
            return ""

        old_map = {}
        new_map = {}
        try:
            for p in pacientes_previos:
                k = _paciente_key(p)
                if k:
                    old_map[k] = p
            for p in payload:
                k = _paciente_key(p)
                if k:
                    new_map[k] = p
        except Exception:
            old_map = {}
            new_map = {}

        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())
        create_keys = new_keys - old_keys
        delete_keys = old_keys - new_keys
        common_keys = old_keys & new_keys

        update_keys = set()
        for k in common_keys:
            try:
                old_s = json.dumps(old_map.get(k, {}), ensure_ascii=False, sort_keys=True, default=str)
                new_s = json.dumps(new_map.get(k, {}), ensure_ascii=False, sort_keys=True, default=str)
                if old_s != new_s:
                    update_keys.add(k)
            except Exception:
                update_keys.add(k)

        # Sincronizar en BACKGROUND (thread separado, no bloquea)
        def sync_in_background():
            with tracked_operation(
                f"cloud-upload:pacientes:{username}",
                "Subiendo pacientes a la nube",
                "upload",
            ):
                try:
                    from utils.sync_manager import get_sync_manager
                    sync_mgr = get_sync_manager()

                    usuario_id = str(_resolve_usuario_id_for_sync(username))
                    bc = _resolve_branch_code_for_sync(username, branch_code=branch_code)
                    registro_bulk = (f"bulk:{bc}" if bc else "bulk")

                    delta_ops = int(len(create_keys) + len(update_keys) + len(delete_keys))
                    if delta_ops <= 0:
                        return

                    use_full_sync = delta_ops > 50  # cargas masivas/import

                    def _with_meta(item_dict):
                        if not isinstance(item_dict, dict):
                            return {}
                        out = dict(item_dict)
                        if not bc:
                            return out
                        meta = out.get("_meta")
                        merged_meta = dict(meta) if isinstance(meta, dict) else {}
                        merged_meta["branch_code"] = bc
                        out["_meta"] = merged_meta
                        return out

                    if not use_full_sync:
                        try:
                            for key in sorted(create_keys):
                                pac = new_map.get(key, {})
                                rid = _paciente_registro_id(pac) or key
                                sync_mgr.queue_change(
                                    usuario_id=str(usuario_id),
                                    tipo_dato='pacientes',
                                    operacion='CREATE',
                                    registro_id=str(rid),
                                    contenido=_with_meta(pac),
                                )
                            for key in sorted(update_keys):
                                pac = new_map.get(key, {})
                                rid = _paciente_registro_id(pac) or key
                                sync_mgr.queue_change(
                                    usuario_id=str(usuario_id),
                                    tipo_dato='pacientes',
                                    operacion='UPDATE',
                                    registro_id=str(rid),
                                    contenido=_with_meta(pac),
                                )
                            for key in sorted(delete_keys):
                                pac = old_map.get(key, {})
                                rid = _paciente_registro_id(pac) or key
                                sync_mgr.queue_change(
                                    usuario_id=str(usuario_id),
                                    tipo_dato='pacientes',
                                    operacion='DELETE',
                                    registro_id=str(rid),
                                    contenido=_with_meta(pac),
                                )
                        except Exception:
                            pass
                    else:
                        contenido = {'pacientes': payload}
                        if bc:
                            contenido['_meta'] = {'branch_code': bc}

                        # Coalescer: mantener solo el ultimo SYNC_ALL por dataset+sucursal
                        try:
                            if hasattr(sync_mgr, "queue") and hasattr(sync_mgr.queue, "clear_pending_sync_all_for_dataset"):
                                sync_mgr.queue.clear_pending_sync_all_for_dataset(
                                    usuario_id=str(usuario_id),
                                    tipo_dato="pacientes",
                                    registro_id=str(registro_bulk),
                                )
                        except Exception:
                            pass

                        sync_mgr.queue_change(
                            usuario_id=str(usuario_id),
                            tipo_dato='pacientes',
                            operacion='SYNC_ALL',
                            registro_id=str(registro_bulk),
                            contenido=contenido
                        )

                    sync_mgr.sync_now(str(usuario_id), force=True)
                except Exception:
                    pass
        
        import threading
        sync_thread = threading.Thread(target=sync_in_background, daemon=True)
        sync_thread.start()
    
    except Exception as e:
        # Fallback: solo guardar localmente
        pacientes_file = get_user_file_path(username, "pacientes.json")
        os.makedirs(pacientes_file.parent, exist_ok=True)
        with open(pacientes_file, 'w', encoding='utf-8') as f:
            json.dump(pacientes, f, indent=4, ensure_ascii=False)

def _get_productos_mysql_context(username):
    resolved = resolve_username(username)
    branch_ctx = get_active_branch_context(resolved) or {}
    active_branch_code = str((branch_ctx or {}).get("code", "") or "").strip().upper()
    branch_label = str((branch_ctx or {}).get("label", "") or "").strip()
    branch_code = _resolve_branch_code_for_sync(resolved, active_branch_code)
    branch_code = "" if branch_code == "__GLOBAL__" else str(branch_code or "").strip().upper()
    branch_type = "hijo" if branch_code else "madre"
    return {
        "resolved_username": resolved,
        "usuario_id": _resolve_usuario_id_for_sync(resolved),
        "branch_code": branch_code,
        "branch_label": branch_label,
        "branch_type": branch_type,
    }


def _get_productos_migration_marker_path(username, branch_code=""):
    resolved = resolve_username(username)
    safe_branch = re.sub(r"[^A-Z0-9_-]+", "_", str(branch_code or "").strip().upper() or "__MADRE__")
    return VISO_DIR / resolved / "migration" / f"productos_mysql_{safe_branch}.json"


def _mark_productos_mysql_migrated(username, branch_code="", source="mysql", total=0):
    try:
        marker_path = _get_productos_migration_marker_path(username, branch_code)
        os.makedirs(marker_path.parent, exist_ok=True)
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "migrated": True,
                    "source": str(source or "").strip(),
                    "total": int(total or 0),
                    "updated_at": datetime.datetime.now().isoformat(),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception:
        pass


def _is_productos_mysql_migrated(username, branch_code=""):
    try:
        marker_path = _get_productos_migration_marker_path(username, branch_code)
        if not marker_path.exists():
            return False
        with open(marker_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data.get("migrated"):
            return False

        source = str(data.get("source", "") or "").strip().lower()
        total = int(data.get("total", 0) or 0)

        # `mysql_empty` solo significa que en ese intento remoto vino vacio.
        # Si todavia existe inventario legacy local, no debe bloquear la migracion real.
        if source == "mysql_empty" and total <= 0:
            return False
        return True
    except Exception:
        return False


def _get_legacy_productos_file(username):
    resolved = resolve_username(username)
    try:
        mysql_ctx = _get_productos_mysql_context(resolved)
        branch_code = str((mysql_ctx or {}).get("branch_code", "") or "").strip().upper()
    except Exception:
        branch_ctx = get_active_branch_context(resolved) or {}
        branch_code = str((branch_ctx or {}).get("code", "") or "").strip().upper()

    candidates = []
    if branch_code:
        branch_dir = get_branch_cache_data_dir(resolved, branch_code)
        candidates.extend([
            branch_dir / "productos.json",
            branch_dir / "products.json",
        ])

    base_dir = VISO_DIR / resolved / "data"
    candidates.extend([
        base_dir / "productos.json",
        base_dir / "products.json",
        VISO_DIR / resolved / "branch_cache" / f"MADRE-{resolved}" / "data" / "productos.json",
        VISO_DIR / resolved / "branch_cache" / f"MADRE-{resolved}" / "data" / "products.json",
    ])

    for path in candidates:
        try:
            if path.exists():
                return path
        except Exception:
            continue
    return None


def _load_legacy_productos_for_migration(username):
    productos_file = _get_legacy_productos_file(username)
    if not productos_file:
        return [], None

    try:
        productos = _load_json_file_safe(productos_file, [], expected_type=list)
        if isinstance(productos, list):
            return productos, productos_file
    except Exception:
        pass
    return [], productos_file


def _sanitize_productos_for_mysql(productos):
    valid = []
    skipped = []

    for idx, item in enumerate(productos or []):
        if not isinstance(item, dict):
            skipped.append({"index": idx, "reason": "not_dict"})
            continue

        codigo = str(item.get("codigo", "") or "").strip()
        nombre = str(item.get("nombre", "") or "").strip()
        if not codigo:
            skipped.append({"index": idx, "reason": "missing_codigo", "nombre": nombre})
            continue
        if not nombre:
            skipped.append({"index": idx, "reason": "missing_nombre", "codigo": codigo})
            continue

        valid.append(item)

    return valid, skipped


def get_productos_mysql_migration_info(username):
    """
    Devuelve informacion local para decidir si corresponde mostrar modal de migracion.
    No consulta la red: solo revisa marker y legado JSON del contexto actual.
    """
    ctx = _get_productos_mysql_context(username)
    branch_code = ctx["branch_code"]
    migrated = _is_productos_mysql_migrated(username, branch_code)
    productos_legacy, source_path = _load_legacy_productos_for_migration(username)
    valid_productos, skipped_productos = _sanitize_productos_for_mysql(productos_legacy or [])
    valid_count = len(valid_productos)
    estimated_seconds = max(6, min(75, 6 + int(valid_count / 18))) if valid_count > 0 else 0
    return {
        "needs_migration": bool((not migrated) and valid_count > 0),
        "migrated": bool(migrated),
        "legacy_count": int(valid_count),
        "skipped_count": int(len(skipped_productos)),
        "estimated_seconds": int(estimated_seconds),
        "branch_code": branch_code,
        "branch_label": ctx["branch_label"],
        "source_path": str(source_path) if source_path else "",
    }


def _migrate_productos_json_to_mysql(username):
    ctx = _get_productos_mysql_context(username)
    branch_code = ctx["branch_code"]

    if _is_productos_mysql_migrated(username, branch_code):
        return []

    productos_legacy, source_path = _load_legacy_productos_for_migration(username)
    productos_legacy, skipped = _sanitize_productos_for_mysql(productos_legacy or [])

    if not productos_legacy:
        _mark_productos_mysql_migrated(username, branch_code, source="legacy_empty", total=0)
        return []

    try:
        from utils.api_handler import reemplazar_productos_remoto

        ok, message, saved = reemplazar_productos_remoto(
            ctx["usuario_id"],
            productos_legacy,
            username=ctx["resolved_username"],
            codigo_dispositivo=branch_code or None,
            dispositivo_nombre=ctx["branch_label"],
            tipo_dispositivo=ctx["branch_type"],
        )
        if ok:
            _mark_productos_mysql_migrated(
                username,
                branch_code,
                source=f"legacy_json:{source_path.name if source_path else 'desconocido'}|skipped:{len(skipped)}",
                total=saved or len(productos_legacy),
            )
            if skipped:
                print(f"[MYSQL][PRODUCTOS] Migracion con {len(skipped)} registros omitidos por datos invalidos", flush=True)
            return _merge_unique_productos(productos_legacy)
        print(f"[MYSQL][PRODUCTOS] No se pudo migrar inventario de {ctx['resolved_username']}: {message}", flush=True)
    except Exception as e:
        print(f"[MYSQL][PRODUCTOS] Error migrando inventario: {e}", flush=True)

    return []


def _migrate_productos_cloud_snapshots_to_mysql(username):
    """
    Migra inventarios desde snapshots cloud por tienda hacia MySQL.
    Prioriza la nube porque alli los productos ya estan separados por codigo_dispositivo.
    """
    ctx = _get_productos_mysql_context(username)
    usuario_madre = _resolve_usuario_madre_cloud(username)

    try:
        from utils.api_handler import (
            listar_dispositivos_hijos_remoto,
            listar_snapshots_dispositivos_nube,
            reemplazar_productos_remoto,
        )
    except Exception as e:
        print(f"[MYSQL][PRODUCTOS] Helpers cloud no disponibles: {e}", flush=True)
        return []

    branch_meta = {}
    candidate_codes = []

    def _register_code(code, label="", branch_type="hijo"):
        code = str(code or "").strip().upper()
        if not code:
            return
        if code not in candidate_codes:
            candidate_codes.append(code)
        current = branch_meta.get(code, {})
        if label and not current.get("label"):
            current["label"] = str(label).strip()
        if branch_type:
            current["type"] = str(branch_type).strip() or current.get("type") or "hijo"
        branch_meta[code] = current

    try:
        base = re.sub(r"[^A-Za-z0-9]+", "", str(resolve_username(username)).upper()) or "USER"
        _register_code(f"MADRE-{base}"[:80], label="Sucursal madre", branch_type="madre")
    except Exception:
        pass

    try:
        ok_dev, devices, _msg = listar_dispositivos_hijos_remoto(usuario_madre)
        if ok_dev and isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                if str(device.get("estado", "activo")).strip().lower() == "bloqueado":
                    continue
                code = str(device.get("codigo_dispositivo", "")).strip().upper()
                label = str(device.get("nombre_optica", "") or device.get("ciudad", "") or "").strip()
                _register_code(code, label=label, branch_type="hijo")
    except Exception as e:
        print(f"[MYSQL][PRODUCTOS] No se pudo listar dispositivos_hijos remotos: {e}", flush=True)

    try:
        ok_snap, snap_devices, _msg = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
        if ok_snap and isinstance(snap_devices, list):
            for snap in snap_devices:
                if not isinstance(snap, dict):
                    continue
                code = str(snap.get("codigo_dispositivo", "")).strip().upper()
                _register_code(code, branch_type=("madre" if code.startswith("MADRE-") else "hijo"))
    except Exception as e:
        print(f"[MYSQL][PRODUCTOS] No se pudo listar snapshots cloud: {e}", flush=True)

    current_branch_products = []
    migrated_any = False

    for code in candidate_codes:
        payload = _download_snapshot_payload_for_dataset(usuario_madre, code, "productos")
        if payload is None:
            continue
        productos = _extract_list_dataset_from_snapshot(payload, "productos")
        if productos is None:
            continue

        productos_validos, skipped = _sanitize_productos_for_mysql(productos or [])
        if not productos_validos and not skipped:
            continue

        meta = branch_meta.get(code, {})
        branch_type = str(meta.get("type", "hijo") or "hijo").strip().lower()
        branch_label = str(meta.get("label", "") or "").strip()

        ok, message, saved = reemplazar_productos_remoto(
            ctx["usuario_id"],
            productos_validos,
            username=ctx["resolved_username"],
            codigo_dispositivo=code,
            dispositivo_nombre=branch_label,
            tipo_dispositivo=branch_type,
        )
        if not ok:
            print(f"[MYSQL][PRODUCTOS] Fallo migrando snapshot cloud {code}: {message}", flush=True)
            continue

        migrated_any = True
        _mark_productos_mysql_migrated(
            username,
            code,
            source=f"cloud_snapshot:productos|skipped:{len(skipped)}",
            total=saved or len(productos_validos),
        )
        try:
            save_branch_snapshot_datasets(username, code, {"productos": productos_validos})
        except Exception:
            pass

        if skipped:
            print(f"[MYSQL][PRODUCTOS] Snapshot {code}: {len(skipped)} registro(s) omitidos por datos invalidos", flush=True)

        if code == str(ctx.get("branch_code", "") or "").strip().upper():
            current_branch_products = _merge_unique_productos(productos_validos)

    if migrated_any:
        try:
            clear_branch_runtime_caches()
        except Exception:
            pass
        return current_branch_products

    return []


def cargar_productos(username, prefer_cloud: bool = True, limit: Optional[int] = None, offset: Optional[int] = None):
    """
    Carga productos desde MySQL.

    Si el usuario aun tenia inventario solo en JSON, lo migra una sola vez
    hacia MySQL y desde ese momento trabaja solo contra la BD.
    """
    _ = prefer_cloud
    ctx = _get_productos_mysql_context(username)

    try:
        from utils.api_handler import obtener_productos_remoto

        productos = obtener_productos_remoto(
            ctx["usuario_id"],
            codigo_dispositivo=ctx["branch_code"] or None,
            limit=limit,
            offset=offset
        )
        if isinstance(productos, list) and productos:
            if limit is None and offset is None:
                _mark_productos_mysql_migrated(username, ctx["branch_code"], source="mysql", total=len(productos))
            
            merged = _merge_unique_productos(productos)
            # âœ… PAGINACIÃ“N REAL: Aplicar limit y offset a la lista final
            if limit is not None or offset is not None:
                start = int(offset or 0)
                end = start + int(limit or len(merged))
                return merged[start:end]
            return merged

        if isinstance(productos, list):
            migrated_cloud = _migrate_productos_cloud_snapshots_to_mysql(username)
            if migrated_cloud:
                return _merge_unique_productos(migrated_cloud)

            productos_retry = obtener_productos_remoto(
                ctx["usuario_id"],
                codigo_dispositivo=ctx["branch_code"] or None,
                limit=limit,
                offset=offset
            )
            if isinstance(productos_retry, list) and productos_retry:
                if limit is None and offset is None:
                    _mark_productos_mysql_migrated(username, ctx["branch_code"], source="mysql", total=len(productos_retry))
                return _merge_unique_productos(productos_retry)

            migrated = _migrate_productos_json_to_mysql(username)
            if migrated:
                return _merge_unique_productos(migrated)
            _mark_productos_mysql_migrated(username, ctx["branch_code"], source="mysql_empty", total=0)
            return []
    except Exception as e:
        print(f"[MYSQL][PRODUCTOS] Error cargando inventario remoto: {e}", flush=True)

    return []


def cargar_productos_dashboard(username, allow_remote_restore: bool = True, fast_start: bool = False):
    """
    Carga productos para dashboard.
    En el primer pintado usa cache local para no bloquear Inicio con internet lento;
    el refresco remoto silencioso actualiza MySQL despues.
    """
    local_data = _load_dashboard_local_list(
        username,
        "productos.json",
        fast_loader_name="cargar_productos_rapido",
        fast_start=fast_start,
    )
    if fast_start or not allow_remote_restore:
        return _merge_unique_productos(local_data or [])

    try:
        remote_data = cargar_productos(username, prefer_cloud=True) or []
        if isinstance(remote_data, list) and remote_data:
            return _merge_unique_productos(remote_data)
    except Exception:
        pass
    return _merge_unique_productos(local_data or [])

def _clear_inventory_cache_keys(prefix, username):
    """Limpia claves de cache de fast_loader para un dataset/usuario."""
    try:
        from utils.fast_loader import _inventory_cache
        base_key = f"{prefix}:{username}"
        keys = list(_inventory_cache._cache.keys())
        for key in keys:
            key_str = str(key)
            if key_str == base_key or key_str.startswith(f"{base_key}|branch:"):
                _inventory_cache._cache.pop(key, None)
        print(f"[CACHE] Cache '{prefix}' limpiado para {username}", flush=True)
    except ImportError:
        pass
    except Exception as e:
        print(f"[CACHE] Error limpiando cache '{prefix}': {e}", flush=True)


def _append_items_json_array(file_path, new_items):
    """
    Agrega elementos al final de un JSON array sin reescribir todo el archivo.
    Devuelve True si el append fue exitoso.
    """
    try:
        if not isinstance(new_items, list) or not new_items:
            return False

        os.makedirs(file_path.parent, exist_ok=True)

        # Si no existe o esta vacio, crear array nuevo
        if not file_path.exists() or file_path.stat().st_size == 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(new_items, f, indent=4, ensure_ascii=False)
            return True

        encoded_items = [
            json.dumps(item, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            for item in new_items
        ]
        encoded_join = b','.join(encoded_items)

        with open(file_path, 'rb+') as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            if file_size <= 0:
                return False

            # Buscar ultimo caracter no whitespace desde el final
            pos = file_size - 1
            last_char = None
            while pos >= 0:
                f.seek(pos)
                b = f.read(1)
                if b not in b' \t\r\n':
                    last_char = b
                    break
                pos -= 1

            if pos < 0 or last_char != b']':
                return False

            close_bracket_pos = pos

            # Detectar si el array esta vacio (char no-whitespace previo es '[')
            pos -= 1
            prev_char = None
            while pos >= 0:
                f.seek(pos)
                b = f.read(1)
                if b not in b' \t\r\n':
                    prev_char = b
                    break
                pos -= 1

            is_empty = (prev_char == b'[')

            # Escribir justo antes del ']'
            f.seek(close_bracket_pos)
            if is_empty:
                f.write(encoded_join + b']')
            else:
                f.write(b',' + encoded_join + b']')
            f.truncate()

        return True
    except Exception:
        return False


def _trigger_sync_now_background(username):
    """
    Dispara sync_now en background.
    En modo carpeta, por defecto sincroniza por delta (sin full sync forzado).
    """
    def _worker():
        try:
            from utils.sync_manager import get_sync_manager
            sync_mgr = get_sync_manager()
            usuario_id = _resolve_usuario_id_for_sync(username)
            sync_mgr.sync_now(str(usuario_id))
            if str(usuario_id) != str(username):
                sync_mgr.sync_now(str(username), force=True)
        except Exception:
            pass

    try:
        threading.Thread(target=_worker, daemon=True).start()
    except Exception:
        pass


def agregar_producto(username, producto):
    """
    Agrega un producto directamente en MySQL.
    """
    if not isinstance(producto, dict):
        return False

    nombre = str(producto.get('nombre', '')).strip().lower()
    codigo = str(producto.get('codigo', '')).strip()
    productos_actuales = cargar_productos(username) or []

    for item in productos_actuales:
        if not isinstance(item, dict):
            continue
        nombre_item = str(item.get('nombre', '')).strip().lower()
        codigo_item = str(item.get('codigo', '')).strip()
        if codigo and codigo_item and codigo_item == codigo:
            return False
        if nombre and nombre_item == nombre:
            return False
    try:
        from utils.api_handler import guardar_producto_remoto

        ctx = _get_productos_mysql_context(username)
        ok, message = guardar_producto_remoto(
            ctx["usuario_id"],
            producto,
            username=ctx["resolved_username"],
            codigo_dispositivo=ctx["branch_code"] or None,
            dispositivo_nombre=ctx["branch_label"],
            tipo_dispositivo=ctx["branch_type"],
        )
        if ok:
            _mark_productos_mysql_migrated(username, ctx["branch_code"], source="mysql", total=len(productos_actuales) + 1)
            return True
        print(f"[MYSQL][PRODUCTOS] No se pudo agregar producto: {message}", flush=True)
    except Exception as e:
        print(f"[MYSQL][PRODUCTOS] Error agregando producto: {e}", flush=True)
    return False

def guardar_productos(username, productos, queue_sync: bool = True):
    """
    Guarda el inventario completo del contexto activo directamente en MySQL.

    `queue_sync` se mantiene solo por compatibilidad de llamadas existentes.
    """
    payload = productos if isinstance(productos, list) else []
    payload, skipped = _sanitize_productos_for_mysql(payload)
    _ = queue_sync
    try:
        from utils.api_handler import reemplazar_productos_remoto

        ctx = _get_productos_mysql_context(username)
        ok, message, saved = reemplazar_productos_remoto(
            ctx["usuario_id"],
            payload,
            username=ctx["resolved_username"],
            codigo_dispositivo=ctx["branch_code"] or None,
            dispositivo_nombre=ctx["branch_label"],
            tipo_dispositivo=ctx["branch_type"],
        )
        if ok:
            _mark_productos_mysql_migrated(username, ctx["branch_code"], source="mysql", total=saved or len(payload))
            if skipped:
                print(f"[MYSQL][PRODUCTOS] Se omitieron {len(skipped)} productos invalidos al guardar inventario", flush=True)
            return
        print(f"[MYSQL][PRODUCTOS] No se pudo guardar inventario completo: {message}", flush=True)
    except Exception as e:
        print(f"[MYSQL][PRODUCTOS] Error guardando inventario completo: {e}", flush=True)
def guardar_remote_backup(username, productos):
    """Guarda una copia de respaldo del inventario remoto en la carpeta del usuario.

    Retorna la ruta al archivo guardado (Path) o None si falla.
    """
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"productos_remote_backup_{timestamp}.json"
        backup_file = get_user_file_path(username, backup_name)
        os.makedirs(backup_file.parent, exist_ok=True)
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(productos, f, indent=2, ensure_ascii=False)
        return backup_file
    except Exception:
        return None


def sanitizar_productos(username, backup=True):
    """Sanitiza el archivo `productos.json` del usuario.

    - Hace backup (si backup=True) a `productos.json.bak_<timestamp>` antes de modificar.
    - Elimina entradas que no sean dicts o que no tengan al menos la llave 'nombre'.
    - Devuelve una tupla (cleaned_count, removed_count, backup_path_or_None)
    """
    # Soportar ambos nombres: `productos.json` (preferido) y `products.json` (legacy)
    productos_file = get_user_file_path(username, "productos.json")
    alt_file = get_user_file_path(username, "products.json")
    if not productos_file.exists() and alt_file.exists():
        productos_file = alt_file
    if not productos_file.exists():
        return 0, 0, None

    try:
        with open(productos_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        # Si no podemos leer, no tocar nada
        return 0, 0, None

    # Si no es una lista, nada que hacer
    if not isinstance(data, list):
        return 0, 0, None

    # Detectar entradas vÃƒÆ’Ã†â€™Ã‚Â¡lidas
    valid = []
    removed = []
    for item in data:
        if isinstance(item, dict) and item.get('nombre'):
            valid.append(item)
        else:
            removed.append(item)

    if not removed:
        return len(valid), 0, None

    backup_path = None
    try:
        if backup:
            ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            backup_name = f"productos.json.bak_{ts}"
            backup_path = str(get_user_file_path(username, backup_name))
            shutil.copy2(str(productos_file), backup_path)
    except Exception:
        backup_path = None

    try:
        # Reescribir con solo items vÃƒÆ’Ã†â€™Ã‚Â¡lidos
        with open(productos_file, 'w', encoding='utf-8') as f:
            json.dump(valid, f, indent=4, ensure_ascii=False)
    except Exception:
        # Si falla escritura, intentar restaurar desde backup si existe
        try:
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, str(productos_file))
        except Exception:
            pass
        return 0, len(removed), backup_path

    return len(valid), len(removed), backup_path

def cargar_ventas(username):
    """Carga las ventas priorizando la nube como unica fuente de verdad cuando hay internet."""
    def _normalize_sales_list(ventas):
        if not isinstance(ventas, list):
            return [], False
        needs_changes = False
        out = list(ventas)
        for idx, venta in enumerate(out, start=1):
            if not isinstance(venta, dict):
                continue
            if 'id' not in venta:
                venta['id'] = idx + 365
                needs_changes = True

            normalized = _normalize_venta_payment_fields(venta)
            if normalized != venta:
                out[idx - 1] = normalized
                needs_changes = True
        return out, needs_changes

    # 1. Cargar ventas locales primero (SIEMPRE)
    ventas_locales = []
    ventas_file = get_user_file_path(username, "ventas.json")
    try:
        if ventas_file.exists():
            ventas_locales = _load_json_file_safe(ventas_file, [], expected_type=list)
            ventas_locales, needs_save = _normalize_sales_list(ventas_locales)
            if needs_save:
                try:
                    guardar_ventas(username, ventas_locales)
                except Exception:
                    pass
    except Exception:
        ventas_locales = []

    # 2. Intentar cargar ventas de la nube si hay internet
    has_internet = False
    try:
        from utils.sync_manager import get_sync_manager
        has_internet = bool(get_sync_manager().check_internet())
    except Exception:
        has_internet = False

    if has_internet:
        try:
            ventas_remotas = _restore_list_dataset_from_cloud(
                username,
                "ventas",
                "ventas.json",
                remote_only=True,
            )
            if isinstance(ventas_remotas, list):
                ventas_remotas, needs_save_remote = _normalize_sales_list(ventas_remotas)
                try:
                    ventas_remotas.sort(key=lambda x: x.get('fecha', ''), reverse=True)
                except Exception:
                    pass

                # Refrescar espejo local para que el ultimo estado cloud quede cacheado.
                try:
                    os.makedirs(ventas_file.parent, exist_ok=True)
                    with open(ventas_file, 'w', encoding='utf-8') as f:
                        json.dump(ventas_remotas, f, indent=4, ensure_ascii=False)
                except Exception as cache_error:
                    print(f"[VENTAS][CACHE] No se pudo actualizar cache local desde nube: {cache_error}", flush=True)

                # Si la nube vino con normalizaciones pendientes, sincronizarlas en background.
                if needs_save_remote:
                    try:
                        branch_code = _resolve_branch_code_for_sync(username)
                    except Exception:
                        branch_code = ""
                    try:
                        _queue_sync_all_dataset_bg(username, "ventas", "ventas", ventas_remotas, branch_code=branch_code)
                    except Exception:
                        pass

                return ventas_remotas
        except Exception as e:
            print(f"[ERROR] Error cargando ventas desde nube: {e}")
            return ventas_locales

    # 3. Si no hay internet, devolver el ultimo cache local disponible.
    if ventas_locales:
        return ventas_locales

    # Snapshot remoto/cache de sucursal como ultimo recurso.
    try:
        ventas_restauradas = _restore_list_dataset_from_cloud(username, "ventas", "ventas.json")
        if isinstance(ventas_restauradas, list) and ventas_restauradas:
            ventas_restauradas, _ = _normalize_sales_list(ventas_restauradas)
            return ventas_restauradas
    except Exception:
        pass
    return []


def cargar_ventas_dashboard(username, allow_remote_restore: bool = True, fast_start: bool = False):
    """
    Carga ventas para dashboard:
    - Prioriza datos locales para velocidad.
    - Si se permite, intenta actualizar desde la nube.
    """
    local_data = _load_dashboard_local_list(username, "ventas.json", fast_start=fast_start)
    
    if allow_remote_restore and _dashboard_has_internet():
        try:
            restored = cargar_ventas(username)
            if isinstance(restored, list) and restored:
                return restored
        except Exception:
            pass

    return local_data if isinstance(local_data, list) else []

def _normalize_venta_payment_fields(venta):
    """Normaliza campos de deuda/pago parcial en una venta para mantener consistencia."""
    if not isinstance(venta, dict):
        return venta

    item = dict(venta)

    def _to_float(value, default=0.0):
        try:
            if value in (None, ""):
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    items = item.get("items")
    if not isinstance(items, list):
        items = []
        item["items"] = items

    total_items = 0.0
    service_index = None
    service_total = 0.0
    productos_total = 0.0
    total_changed = False

    for idx, sale_item in enumerate(items):
        if not isinstance(sale_item, dict):
            continue
        current = dict(sale_item)
        cantidad = _to_float(current.get("cantidad", 1), 1.0)
        precio_unitario = _to_float(
            current.get("precio_unitario", current.get("precio", 0)),
            0.0,
        )
        total_item = _to_float(
            current.get("total", current.get("subtotal", precio_unitario * cantidad)),
            0.0,
        )
        if abs(_to_float(current.get("subtotal", total_item), total_item) - total_item) > 0.01:
            current["subtotal"] = total_item
            total_changed = True
        if "total" in current and abs(_to_float(current.get("total", total_item), total_item) - total_item) > 0.01:
            current["total"] = total_item
            total_changed = True
        elif "total" not in current:
            current["total"] = total_item
            total_changed = True
        items[idx] = current
        total_items += total_item

        nombre_item = str(current.get("nombre") or current.get("producto") or "").strip().lower()
        if "servicio de gradu" in nombre_item:
            service_index = idx
            service_total += total_item
        else:
            productos_total += total_item

    total = _to_float(item.get("total", 0), 0.0)

    is_graduacion = (
        str(item.get("origen", "") or "").strip().lower() == "graduacion"
        or str(item.get("tipo_venta", "") or "").strip().lower() == "graduacion"
    )

    if is_graduacion and total_items > 0.01:
        # No inflar historicos. Si los items ya tienen servicio + productos,
        # el total canonico debe seguir a la suma real de items, no duplicar
        # el servicio para "cuadrar" datos antiguos.
        if total <= 0.01 or abs(total - total_items) > 0.05:
            item["total"] = total_items
            total = total_items
            total_changed = True
    elif total <= 0 and total_items > 0:
        item["total"] = total_items
        total = total_items
        total_changed = True

    raw_pagado = item.get("monto_pagado", None)
    raw_adelanto = item.get("monto_adelanto", None)
    raw_faltante = item.get("monto_faltante", None)

    tiene_pagado = raw_pagado not in (None, "")
    tiene_adelanto = raw_adelanto not in (None, "")

    monto_pagado = _to_float(raw_pagado, 0.0)
    monto_adelanto = _to_float(raw_adelanto, 0.0)

    if not tiene_pagado and not tiene_adelanto:
        monto_pagado = total

    pagado = max(monto_pagado, monto_adelanto)
    faltante_calculado = max(0.0, total - pagado)
    if total_changed:
        faltante = faltante_calculado
    else:
        faltante = _to_float(raw_faltante, faltante_calculado) if raw_faltante not in (None, "") else faltante_calculado
    if faltante < 0:
        faltante = 0.0

    es_parcial = bool(
        item.get("es_pago_partes")
        or item.get("es_pago_parcial")
        or faltante > 0.05
    )

    if es_parcial:
        deuda_activa = faltante > 0.05
        item["monto_pagado"] = pagado
        item["monto_adelanto"] = pagado if deuda_activa else max(monto_adelanto, pagado)
        item["monto_faltante"] = faltante if deuda_activa else 0.0
        item["es_pago_partes"] = deuda_activa
        item["es_pago_parcial"] = deuda_activa
    else:
        item["monto_pagado"] = pagado if (tiene_pagado or tiene_adelanto) else total
        item["monto_faltante"] = 0.0
        if "monto_adelanto" not in item:
            item["monto_adelanto"] = 0.0
        item["es_pago_partes"] = False
        item["es_pago_parcial"] = False

    subtotal_calculado = round(total / 1.18, 2) if total > 0 else 0.0
    igv_calculado = round(total - subtotal_calculado, 2)
    if abs(_to_float(item.get("subtotal", subtotal_calculado), subtotal_calculado) - subtotal_calculado) > 0.01:
        item["subtotal"] = subtotal_calculado
        total_changed = True
    if abs(_to_float(item.get("igv", igv_calculado), igv_calculado) - igv_calculado) > 0.01:
        item["igv"] = igv_calculado
        total_changed = True

    if total_items > 0.01:
        item["items"] = items

    if is_graduacion and total_items > 0.01:
        item["monto_total_venta"] = total
    elif "monto_total_venta" in item and not is_graduacion:
        item.pop("monto_total_venta", None)

    return item

def cargar_caja(username):
    """Carga los datos de caja diaria desde el archivo local caja.json."""
    try:
        path = get_user_file_path(username, "caja.json")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}

def guardar_caja(username, caja_data):
    """Guarda los datos de caja diaria localmente."""
    try:
        path = get_user_file_path(username, "caja.json")
        os.makedirs(path.parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(caja_data, f, indent=4, ensure_ascii=False)

        # Mantener cache de sucursal
        try:
            branch_code = _resolve_branch_code_for_sync(username)
            if branch_code:
                save_branch_snapshot_datasets(username, branch_code, {"caja": caja_data})
                clear_branch_runtime_caches()
        except Exception:
            pass
    except Exception as e:
        print(f"[CAJA] Error al guardar caja: {e}")

def guardar_ventas(username, ventas):
    """
    Guarda las ventas para un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico.
    Intenta sincronizar con servidor si hay internet, sino guarda localmente.
    """
    try:
        # Obtener usuario_id (ID numÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rico)
        usuarios = cargar_usuarios() or {}
        usuario_id = None
        for uid, info in usuarios.items():
            if isinstance(info, dict) and info.get('username') == username:
                usuario_id = uid
                break
        
        if not usuario_id:
            usuario_id = username
        
        payload = ventas if isinstance(ventas, list) else []
        try:
            payload = [
                _normalize_venta_payment_fields(item) if isinstance(item, dict) else item
                for item in payload
            ]
        except Exception:
            payload = ventas if isinstance(ventas, list) else []

        # Guardar localmente primero (SIEMPRE)
        ventas_file = get_user_file_path(username, "ventas.json")
        os.makedirs(ventas_file.parent, exist_ok=True)
        with open(ventas_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        
        # Mantener cache local de sucursal consistente para dashboards del madre.
        try:
            branch_code = _resolve_branch_code_for_sync(username)
            if branch_code:
                save_branch_snapshot_datasets(username, branch_code, {"ventas": payload})
                clear_branch_runtime_caches()
        except Exception:
            branch_code = ""

        # Sincronizar en background usando la misma resoluciÃ³n de sucursal
        # que ya usan pacientes y otros datasets.
        try:
            _queue_sync_all_dataset_bg(username, "ventas", "ventas", payload, branch_code=branch_code)
        except Exception:
            pass
    except Exception:
        ventas_file = get_user_file_path(username, "ventas.json")
        os.makedirs(ventas_file.parent, exist_ok=True)
        with open(ventas_file, 'w', encoding='utf-8') as f:
            json.dump(ventas, f, indent=4, ensure_ascii=False)

def _get_kardex_migration_marker_path(username, branch_code=""):
    resolved = resolve_username(username)
    safe_branch = re.sub(r"[^A-Z0-9_-]+", "_", str(branch_code or "").strip().upper() or "__MADRE__")
    return VISO_DIR / resolved / "migration" / f"kardex_mysql_{safe_branch}.json"


def _mark_kardex_mysql_migrated(username, branch_code="", source="mysql", total=0):
    try:
        marker_path = _get_kardex_migration_marker_path(username, branch_code)
        os.makedirs(marker_path.parent, exist_ok=True)
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "migrated": True,
                    "source": str(source or "").strip(),
                    "total": int(total or 0),
                    "updated_at": datetime.datetime.now().isoformat(),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception:
        pass


def _is_kardex_mysql_migrated(username, branch_code=""):
    try:
        marker_path = _get_kardex_migration_marker_path(username, branch_code)
        if not marker_path.exists():
            return False
        with open(marker_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data.get("migrated"):
            return False
        source = str(data.get("source", "") or "").strip().lower()
        total = int(data.get("total", 0) or 0)
        if source == "mysql_empty" and total <= 0:
            return False
        return True
    except Exception:
        return False


def _get_legacy_kardex_file(username):
    resolved = resolve_username(username)
    try:
        ctx = _get_productos_mysql_context(resolved)
        branch_code = str((ctx or {}).get("branch_code", "") or "").strip().upper()
    except Exception:
        branch_ctx = get_active_branch_context(resolved) or {}
        branch_code = str((branch_ctx or {}).get("code", "") or "").strip().upper()

    candidates = []
    if branch_code:
        branch_dir = get_branch_cache_data_dir(resolved, branch_code)
        candidates.append(branch_dir / "kardex.json")

    candidates.extend([
        VISO_DIR / resolved / "data" / "kardex.json",
        VISO_DIR / resolved / "branch_cache" / f"MADRE-{resolved}" / "data" / "kardex.json",
    ])

    for path in candidates:
        try:
            if path.exists():
                return path
        except Exception:
            continue
    return None


def _load_legacy_kardex_for_migration(username):
    kardex_file = _get_legacy_kardex_file(username)
    if not kardex_file:
        return [], None
    try:
        kardex = _load_json_file_safe(kardex_file, [], expected_type=list)
        if isinstance(kardex, list):
            return kardex, kardex_file
    except Exception:
        pass
    return [], kardex_file


def _sanitize_kardex_for_mysql(kardex):
    valid = []
    for item in kardex or []:
        if not isinstance(item, dict):
            continue
        if not str(item.get("fecha", "") or "").strip() and not str(item.get("producto", "") or "").strip():
            continue
        valid.append(item)
    return valid


def _migrate_kardex_cloud_snapshots_to_mysql(username):
    ctx = _get_productos_mysql_context(username)
    usuario_madre = _resolve_usuario_madre_cloud(username)

    try:
        from utils.api_handler import (
            listar_dispositivos_hijos_remoto,
            listar_snapshots_dispositivos_nube,
            reemplazar_kardex_remoto,
        )
    except Exception as e:
        print(f"[MYSQL][KARDEX] Helpers cloud no disponibles: {e}", flush=True)
        return []

    branch_meta = {}
    candidate_codes = []

    def _register_code(code, label="", branch_type="hijo"):
        code = str(code or "").strip().upper()
        if not code:
            return
        if code not in candidate_codes:
            candidate_codes.append(code)
        current = branch_meta.get(code, {})
        if label and not current.get("label"):
            current["label"] = str(label).strip()
        if branch_type:
            current["type"] = str(branch_type).strip() or current.get("type") or "hijo"
        branch_meta[code] = current

    try:
        base = re.sub(r"[^A-Za-z0-9]+", "", str(resolve_username(username)).upper()) or "USER"
        _register_code(f"MADRE-{base}"[:80], label="Sucursal madre", branch_type="madre")
    except Exception:
        pass

    try:
        ok_dev, devices, _msg = listar_dispositivos_hijos_remoto(usuario_madre)
        if ok_dev and isinstance(devices, list):
            for device in devices:
                if not isinstance(device, dict):
                    continue
                if str(device.get("estado", "activo")).strip().lower() == "bloqueado":
                    continue
                _register_code(
                    device.get("codigo_dispositivo", ""),
                    label=str(device.get("nombre_optica", "") or device.get("ciudad", "") or "").strip(),
                    branch_type="hijo",
                )
    except Exception:
        pass

    try:
        ok_snap, snap_devices, _msg = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
        if ok_snap and isinstance(snap_devices, list):
            for snap in snap_devices:
                if not isinstance(snap, dict):
                    continue
                code = str(snap.get("codigo_dispositivo", "")).strip().upper()
                _register_code(code, branch_type=("madre" if code.startswith("MADRE-") else "hijo"))
    except Exception:
        pass

    current_branch_items = []
    migrated_any = False

    for code in candidate_codes:
        payload = _download_snapshot_payload_for_dataset(usuario_madre, code, "kardex")
        if payload is None:
            continue
        items = _extract_list_dataset_from_snapshot(payload, "kardex")
        if items is None:
            continue
        valid_items = _sanitize_kardex_for_mysql(items)
        if not valid_items:
            continue

        meta = branch_meta.get(code, {})
        ok, message, saved = reemplazar_kardex_remoto(
            ctx["usuario_id"],
            valid_items,
            username=ctx["resolved_username"],
            codigo_dispositivo=code,
            dispositivo_nombre=str(meta.get("label", "") or "").strip(),
            tipo_dispositivo=str(meta.get("type", "hijo") or "hijo").strip(),
        )
        if not ok:
            print(f"[MYSQL][KARDEX] Fallo migrando snapshot cloud {code}: {message}", flush=True)
            continue

        migrated_any = True
        _mark_kardex_mysql_migrated(username, code, source="cloud_snapshot:kardex", total=saved or len(valid_items))
        if code == str(ctx.get("branch_code", "") or "").strip().upper():
            current_branch_items = list(valid_items)

    return current_branch_items if migrated_any else []


def _migrate_kardex_json_to_mysql(username):
    ctx = _get_productos_mysql_context(username)
    branch_code = ctx["branch_code"]

    if _is_kardex_mysql_migrated(username, branch_code):
        return []

    items, source_path = _load_legacy_kardex_for_migration(username)
    valid_items = _sanitize_kardex_for_mysql(items)
    if not valid_items:
        _mark_kardex_mysql_migrated(username, branch_code, source="legacy_empty", total=0)
        return []

    try:
        from utils.api_handler import reemplazar_kardex_remoto

        ok, message, saved = reemplazar_kardex_remoto(
            ctx["usuario_id"],
            valid_items,
            username=ctx["resolved_username"],
            codigo_dispositivo=branch_code or None,
            dispositivo_nombre=ctx["branch_label"],
            tipo_dispositivo=ctx["branch_type"],
        )
        if ok:
            _mark_kardex_mysql_migrated(
                username,
                branch_code,
                source=f"legacy_json:{source_path.name if source_path else 'desconocido'}",
                total=saved or len(valid_items),
            )
            return valid_items
        print(f"[MYSQL][KARDEX] No se pudo migrar kardex local: {message}", flush=True)
    except Exception as e:
        print(f"[MYSQL][KARDEX] Error migrando kardex local: {e}", flush=True)
    return []


def agregar_movimiento_kardex(username, entry):
    """Agrega un movimiento de kardex directo a MySQL."""
    if not isinstance(entry, dict):
        return False
    try:
        from utils.api_handler import agregar_movimiento_kardex_remoto

        ctx = _get_productos_mysql_context(username)
        ok, message = agregar_movimiento_kardex_remoto(
            ctx["usuario_id"],
            entry,
            username=ctx["resolved_username"],
            codigo_dispositivo=ctx["branch_code"] or None,
            dispositivo_nombre=ctx["branch_label"],
            tipo_dispositivo=ctx["branch_type"],
        )
        if ok:
            return True
        print(f"[MYSQL][KARDEX] No se pudo agregar movimiento: {message}", flush=True)
    except Exception as e:
        print(f"[MYSQL][KARDEX] Error agregando movimiento: {e}", flush=True)
    return False


def cargar_kardex(username):
    """Carga el kardex desde MySQL."""
    ctx = _get_productos_mysql_context(username)
    try:
        from utils.api_handler import obtener_kardex_remoto

        kardex = obtener_kardex_remoto(ctx["usuario_id"], codigo_dispositivo=ctx["branch_code"] or None)
        if isinstance(kardex, list) and kardex:
            _mark_kardex_mysql_migrated(username, ctx["branch_code"], source="mysql", total=len(kardex))
            return kardex

        if isinstance(kardex, list):
            migrated_cloud = _migrate_kardex_cloud_snapshots_to_mysql(username)
            if migrated_cloud:
                return migrated_cloud

            retry = obtener_kardex_remoto(ctx["usuario_id"], codigo_dispositivo=ctx["branch_code"] or None)
            if isinstance(retry, list) and retry:
                _mark_kardex_mysql_migrated(username, ctx["branch_code"], source="mysql", total=len(retry))
                return retry

            migrated_local = _migrate_kardex_json_to_mysql(username)
            if migrated_local:
                return migrated_local

            _mark_kardex_mysql_migrated(username, ctx["branch_code"], source="mysql_empty", total=0)
            return []
    except Exception as e:
        print(f"[MYSQL][KARDEX] Error cargando kardex remoto: {e}", flush=True)
    return []


def guardar_kardex(username, kardex):
    """Guarda el kardex en MySQL para el contexto activo."""
    payload = kardex if isinstance(kardex, list) else []
    try:
        from utils.api_handler import reemplazar_kardex_remoto

        ctx = _get_productos_mysql_context(username)
        ok, message, saved = reemplazar_kardex_remoto(
            ctx["usuario_id"],
            payload,
            username=ctx["resolved_username"],
            codigo_dispositivo=ctx["branch_code"] or None,
            dispositivo_nombre=ctx["branch_label"],
            tipo_dispositivo=ctx["branch_type"],
        )
        if ok:
            _mark_kardex_mysql_migrated(username, ctx["branch_code"], source="mysql", total=saved or len(payload))
            return
        print(f"[MYSQL][KARDEX] No se pudo guardar kardex: {message}", flush=True)
    except Exception as e:
        print(f"[MYSQL][KARDEX] Error guardando kardex: {e}", flush=True)

def cargar_nombre_optica(username):
    """Carga el nombre de la optica de un usuario especifico."""
    config_file = get_user_file_path(username, "configuracion_optica.txt")
    backup_file = get_user_file_path(username, "configuracion_optica.backup.txt")
    fallback_name = ""

    def _read_config_name(path):
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                decoded_content = _decode_configuracion_optica_content(raw_content)
                nombre = _extract_nombre_optica_from_content(decoded_content)
                return _repair_mojibake_text(nombre).strip()
        except IOError:
            return ""
        except Exception:
            return ""
        return ""

    for path in (config_file, backup_file):
        nombre = _read_config_name(path)
        if nombre and not _is_default_optica_name(nombre):
            return nombre
        if nombre and not fallback_name:
            fallback_name = nombre

    try:
        datos_file = get_user_file_path(username, "datos_generales.json")
        if datos_file.exists():
            with open(datos_file, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if isinstance(datos, dict):
                for key in ("nombre_optica", "nombre_comercial", "razon_social"):
                    nombre = _repair_mojibake_text(datos.get(key, "")).strip()
                    if nombre and not _is_default_optica_name(nombre):
                        return nombre
    except Exception:
        pass

    return fallback_name or "Mi \u00d3ptica"


def cargar_configuracion_optica(username):
    """Carga la configuraciÃ³n extendida de la Ã³ptica desde configuracion_optica.txt."""
    config_file = get_user_file_path(username, "configuracion_optica.txt")
    backup_file = get_user_file_path(username, "configuracion_optica.backup.txt")
    fallback = {
        "nombre_optica": "Mi Ã“ptica",
        "slogan": "",
        "direccion": "",
        "correo_electronico": "",
    }

    for path in (config_file, backup_file):
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    raw_content = f.read()
                decoded_content = _decode_configuracion_optica_content(raw_content)
                parsed = _parse_configuracion_optica_content(decoded_content)
                if any(str(v or "").strip() for v in parsed.values()):
                    if not parsed.get("nombre_optica"):
                        parsed["nombre_optica"] = fallback["nombre_optica"]
                    return parsed
        except Exception:
            continue

    try:
        datos = cargar_datos_generales(username)
        if isinstance(datos, dict):
            fallback["nombre_optica"] = _repair_mojibake_text(str(datos.get("nombre_optica", "") or fallback["nombre_optica"])).strip() or fallback["nombre_optica"]
            fallback["direccion"] = _repair_mojibake_text(str(datos.get("direccion", "") or "")).strip()
            fallback["slogan"] = _repair_mojibake_text(str(datos.get("slogan", "") or "")).strip()
            fallback["correo_electronico"] = _repair_mojibake_text(str(datos.get("correo_electronico", "") or datos.get("correo", "") or "")).strip()
    except Exception:
        pass

    return fallback

def guardar_nombre_optica(username, nombre_optica):
    """Guarda el nombre de la optica para un usuario especifico."""
    guardar_configuracion_optica(username, {"nombre_optica": nombre_optica})


def cargar_whatsapp_optica(username):
    """Carga el WhatsApp principal de la Ã³ptica desde cache local."""
    whatsapp_json_path = get_user_file_path(username, "whatsapp.json")
    try:
        if whatsapp_json_path.exists():
            data = _load_json_file_safe(whatsapp_json_path, {}, expected_type=dict)
            if isinstance(data, dict):
                return str(data.get("whatsapp", "") or "").strip()
    except Exception:
        pass
    return ""


def guardar_whatsapp_optica(username, numero):
    """Guarda el WhatsApp principal de la Ã³ptica en cache local."""
    whatsapp_json_path = get_user_file_path(username, "whatsapp.json")
    os.makedirs(whatsapp_json_path.parent, exist_ok=True)
    with open(whatsapp_json_path, "w", encoding="utf-8") as f:
        json.dump({"whatsapp": str(numero or "").strip()}, f, ensure_ascii=False, indent=2)


def cargar_datos_optica(username, prefer_remote: bool = False):
    """
    Carga datos comerciales de la Ã³ptica.
    Prioriza remoto solo cuando se solicita explÃ­citamente y cae a cache local.
    """
    local_payload = {}
    try:
        cfg = cargar_configuracion_optica(username) or {}
        dg = cargar_datos_generales(username) or {}
        local_payload = {
            "nombre_optica": str(cfg.get("nombre_optica") or dg.get("nombre_optica") or cargar_nombre_optica(username) or "").strip(),
            "slogan": str(cfg.get("slogan") or dg.get("slogan") or "").strip(),
            "direccion": str(cfg.get("direccion") or dg.get("direccion") or "").strip(),
            "correo_electronico": str(cfg.get("correo_electronico") or dg.get("correo_electronico") or dg.get("correo") or "").strip(),
            "whatsapp": cargar_whatsapp_optica(username),
        }
    except Exception:
        local_payload = {
            "nombre_optica": cargar_nombre_optica(username),
            "slogan": "",
            "direccion": "",
            "correo_electronico": "",
            "whatsapp": "",
        }

    if not prefer_remote:
        return local_payload

    try:
        from utils.api_handler import obtener_datos_optica_remoto

        usuario_id = str(_resolve_usuario_id_for_sync(username))
        ok, remote_data, _msg = obtener_datos_optica_remoto(username=str(username), usuario_id=usuario_id)
        if ok and isinstance(remote_data, dict) and any(str(v or "").strip() for v in remote_data.values()):
            merged = dict(local_payload)
            for key in ("nombre_optica", "slogan", "direccion", "correo_electronico", "whatsapp"):
                value = str(remote_data.get(key, "") or "").strip()
                if value:
                    merged[key] = value
            return merged
    except Exception:
        pass

    return local_payload


def guardar_datos_optica(username, datos, sync_remote: bool = True):
    """Guarda datos comerciales en cache local y opcionalmente en MySQL remoto."""
    payload = {
        "nombre_optica": str((datos or {}).get("nombre_optica", "") or "").strip(),
        "slogan": str((datos or {}).get("slogan", "") or "").strip(),
        "direccion": str((datos or {}).get("direccion", "") or "").strip(),
        "correo_electronico": str((datos or {}).get("correo_electronico", "") or "").strip(),
        "whatsapp": str((datos or {}).get("whatsapp", "") or "").strip(),
    }

    guardar_configuracion_optica(
        username,
        {
            "nombre_optica": payload["nombre_optica"],
            "slogan": payload["slogan"],
            "direccion": payload["direccion"],
            "correo_electronico": payload["correo_electronico"],
        }
    )

    datos_gen = cargar_datos_generales(username)
    datos_gen["nombre_optica"] = payload["nombre_optica"]
    datos_gen["slogan"] = payload["slogan"]
    datos_gen["direccion"] = payload["direccion"]
    datos_gen["correo_electronico"] = payload["correo_electronico"]
    guardar_datos_generales(username, datos_gen)
    guardar_whatsapp_optica(username, payload["whatsapp"])

    if not sync_remote:
        return True

    def _sync_remote():
        try:
            from utils.api_handler import guardar_datos_optica_remoto

            guardar_datos_optica_remoto(
                username=str(username),
                usuario_id=str(_resolve_usuario_id_for_sync(username)),
                datos=payload,
            )
        except Exception:
            pass

    try:
        threading.Thread(target=_sync_remote, daemon=True).start()
    except Exception:
        pass
    return True


def guardar_configuracion_optica(username, config_data):
    """Guarda configuraciÃ³n extendida de la Ã³ptica para un usuario especÃ­fico."""
    config_file = get_user_file_path(username, "configuracion_optica.txt")
    os.makedirs(config_file.parent, exist_ok=True)
    existing_plain = ""
    try:
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                existing_raw = f.read()
            existing_plain = _decode_configuracion_optica_content(existing_raw)
    except Exception:
        existing_plain = ""

    merged = _parse_configuracion_optica_content(existing_plain)
    if not isinstance(config_data, dict):
        config_data = {"nombre_optica": config_data}
    for key in ("nombre_optica", "slogan", "direccion", "correo_electronico"):
        if key in config_data:
            merged[key] = config_data.get(key, "")

    plain_content = _build_configuracion_optica_plain_content(merged, existing_plain)

    encoded_content = _encode_configuracion_optica_content(plain_content)
    with open(config_file, "w", encoding='utf-8') as f:
        f.write(encoded_content)
    try:
        backup_file = get_user_file_path(username, "configuracion_optica.backup.txt")
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(encoded_content)
    except Exception:
        pass

# ============================================================================
# DATOS GENERALES (RUC, RazÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n Social, etc.)
# ============================================================================

def cargar_datos_generales(username):
    """
    Carga datos generales de la empresa (RUC, razÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n social, direcciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n, etc.)
    Retorna un diccionario con configuraciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n general.
    """
    config_file = get_user_file_path(username, "datos_generales.json")
    try:
        if config_file.exists():
            data = _load_json_file_safe(config_file, {}, expected_type=dict)
            if isinstance(data, dict):
                if isinstance(data.get("razon_social"), str):
                    data["razon_social"] = _repair_mojibake_text(data["razon_social"])
                if isinstance(data.get("nombre_comercial"), str):
                    data["nombre_comercial"] = _repair_mojibake_text(data["nombre_comercial"])
            return data if isinstance(data, dict) else {}
    except (IOError, json.JSONDecodeError):
        pass
    
    # Retornar estructura por defecto
    estructura_minima = {
        "ruc": "",
        "razon_social": "Mi Optica",
        "nombre_comercial": "Mi Optica",
        "nombre_optica": "Mi Optica",
        "slogan": "",
        "direccion": "",
        "correo_electronico": "",
        "departamento": "",
        "provincia": "",
        "distrito": "",
        "ubigeo": "",
        "estado": "",
        "condicion": "",
        "token_sunat": "",
        "ultima_actualizacion": ""
    }
    return estructura_minima


def guardar_datos_generales(username, datos):
    """
    Guarda datos generales de la empresa (RUC, razÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n social, direcciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n, etc.)
    """
    config_file = get_user_file_path(username, "datos_generales.json")
    os.makedirs(config_file.parent, exist_ok=True)
    
    # Asegurar que datos tiene estructura mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­nima
    estructura_minima = {
        "ruc": "",
        "razon_social": "Mi Optica",
        "nombre_comercial": "Mi Optica",
        "nombre_optica": "Mi Optica",
        "slogan": "",
        "direccion": "",
        "correo_electronico": "",
        "departamento": "",
        "provincia": "",
        "distrito": "",
        "ubigeo": "",
        "estado": "",
        "condicion": "",
        "token_sunat": "",
        "ultima_actualizacion": ""
    }
    
    # Normalizar campos de texto frecuentes antes de guardar
    if isinstance(datos, dict):
        if isinstance(datos.get("razon_social"), str):
            datos["razon_social"] = _repair_mojibake_text(datos["razon_social"])
        if isinstance(datos.get("nombre_comercial"), str):
            datos["nombre_comercial"] = _repair_mojibake_text(datos["nombre_comercial"])

    # Merge con datos existentes
    datos_completos = {**estructura_minima, **datos}
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(datos_completos, f, indent=4, ensure_ascii=False)
    _queue_sync_all_dataset_bg(username, "datos_generales", "datos_generales", datos_completos)


def actualizar_datos_sunat(username, datos_sunat):
    """
    Actualiza los datos generales con informaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n obtenida de SUNAT.
    
    Args:
        username: Usuario actual
        datos_sunat: Diccionario con datos del RUC de SUNAT
    """
    import time
    
    # Cargar datos actuales
    datos = cargar_datos_generales(username)
    
    # Actualizar con datos de SUNAT
    datos.update({
        "ruc": datos_sunat.get("ruc", ""),
        "razon_social": datos_sunat.get("razonSocial", ""),
        "nombre_comercial": datos_sunat.get("nombreComercial") or datos_sunat.get("razonSocial", ""),
        "direccion": datos_sunat.get("direccion", ""),
        "departamento": datos_sunat.get("departamento", ""),
        "provincia": datos_sunat.get("provincia", ""),
        "distrito": datos_sunat.get("distrito", ""),
        "ubigeo": datos_sunat.get("ubigeo", ""),
        "estado": datos_sunat.get("estado", ""),
        "condicion": datos_sunat.get("condicion", ""),
        "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Guardar
    guardar_datos_generales(username, datos)


def cargar_ruc(username):
    """Carga el RUC guardado."""
    datos = cargar_datos_generales(username)
    return datos.get("ruc", "")


def guardar_ruc(username, ruc):
    """Guarda el RUC."""
    datos = cargar_datos_generales(username)
    datos["ruc"] = ruc
    guardar_datos_generales(username, datos)


def cargar_razon_social(username):
    """Carga la razÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n social guardada."""
    datos = cargar_datos_generales(username)
    return _repair_mojibake_text(datos.get("razon_social", "Mi Ãƒâ€œptica")) or "Mi Ãƒâ€œptica"


def guardar_razon_social(username, razon_social):
    """Guarda la razÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n social."""
    datos = cargar_datos_generales(username)
    datos["razon_social"] = razon_social
    guardar_datos_generales(username, datos)


def cargar_token_sunat(username):
    """Carga el token SUNAT guardado."""
    datos = cargar_datos_generales(username)
    return datos.get("token_sunat", "")


def guardar_token_sunat(username, token):
    """Guarda el token SUNAT."""
    datos = cargar_datos_generales(username)
    datos["token_sunat"] = token
    guardar_datos_generales(username, datos)

def cargar_optometras(username):
    """Carga la lista de optÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³metras de un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    optometras_file = get_user_file_path(username, "optometras.json")
    try:
        if optometras_file.exists():
            data = _load_json_file_safe(optometras_file, [], expected_type=list)
            return data if isinstance(data, list) else []
    except (IOError, json.JSONDecodeError):
        pass
    return []

def guardar_optometras(username, optometras, queue_sync: bool = True):
    """Guarda la lista de optÃƒÂ³metras para un usuario especÃƒÂ­fico."""
    optometras_file = get_user_file_path(username, "optometras.json")
    os.makedirs(optometras_file.parent, exist_ok=True)
    payload = optometras if isinstance(optometras, list) else []

    # Guardado atÃƒÂ³mico para evitar corrupciÃƒÂ³n por cierres inesperados
    tmp_path = optometras_file.with_suffix('.json.tmp')
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        os.replace(str(tmp_path), str(optometras_file))
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

    # Sincronizar en background (no bloquea UI)
    if not queue_sync:
        return

    try:
        _queue_sync_all_dataset_bg(username, "optometras", "optometras", payload)
    except Exception:
        pass


def agregar_optometra(username, nombre):
    """
    Agrega un optometra sin reescribir el JSON completo.
    Retorna True si se agrego, False si ya existe o error.
    """
    nombre_limpio = str(nombre or "").strip()
    if not nombre_limpio:
        return False

    optometras = cargar_optometras(username)
    if nombre_limpio in optometras:
        return False

    optometras_file = get_user_file_path(username, "optometras.json")
    appended = _append_items_json_array(optometras_file, [nombre_limpio])
    if not appended:
        # Fallback seguro: mantener flujo previo
        optometras.append(nombre_limpio)
        guardar_optometras(username, optometras)
        return True

    # Sincronizar alta individual en background
    def sync_in_background():
        try:
            from utils.sync_manager import get_sync_manager
            sync_mgr = get_sync_manager()
            bc = _resolve_branch_code_for_sync(username)
            contenido = {'nombre': nombre_limpio}
            if bc:
                contenido['_meta'] = {'branch_code': bc}
            sync_mgr.queue_change(
                usuario_id=str(_resolve_usuario_id_for_sync(username)),
                tipo_dato='optometras',
                operacion='CREATE',
                registro_id=nombre_limpio,
                contenido=contenido
            )
            sync_mgr.sync_now(str(_resolve_usuario_id_for_sync(username)), force=True)
        except Exception:
            pass

    try:
        import threading
        threading.Thread(target=sync_in_background, daemon=True).start()
    except Exception:
        pass

    return True


def eliminar_optometra(username, nombre):
    """
    Elimina un optometra localmente y sincroniza como DELETE puntual (delta).
    Retorna True si se elimino, False si no existia o error.
    """
    nombre_limpio = str(nombre or "").strip()
    if not nombre_limpio:
        return False

    optometras = cargar_optometras(username) or []
    filtrados = [
        o for o in optometras
        if str(o or "").strip().lower() != nombre_limpio.lower()
    ]

    if len(filtrados) == len(optometras):
        return False

    # Guardar local sin SYNC_ALL (evitar reemplazo completo remoto)
    guardar_optometras(username, filtrados, queue_sync=False)

    def sync_in_background():
        try:
            from utils.sync_manager import get_sync_manager
            sync_mgr = get_sync_manager()
            bc = _resolve_branch_code_for_sync(username)
            contenido = {'nombre': nombre_limpio}
            if bc:
                contenido['_meta'] = {'branch_code': bc}
            usuario_id = str(_resolve_usuario_id_for_sync(username))
            sync_mgr.queue_change(
                usuario_id=usuario_id,
                tipo_dato='optometras',
                operacion='DELETE',
                registro_id=nombre_limpio,
                contenido=contenido
            )

            # Fallback: asegurar que la lista final quede igual a la local (por sucursal).
            # Esto evita casos donde el backend ignore el delta o no exista el dataset aÃºn.
            registro_bulk = f"bulk:{bc}" if bc else "bulk"
            contenido_bulk = {"optometras": filtrados}
            if bc:
                contenido_bulk["_meta"] = {"branch_code": bc}
            sync_mgr.queue_change(
                usuario_id=usuario_id,
                tipo_dato="optometras",
                operacion="SYNC_ALL",
                registro_id=registro_bulk,
                contenido=contenido_bulk,
            )

            sync_mgr.sync_now(usuario_id, force=True)
        except Exception:
            pass

    try:
        import threading
        threading.Thread(target=sync_in_background, daemon=True).start()
    except Exception:
        pass

    return True

def cargar_citas(username):
    """Carga la lista de citas de un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    citas_file = get_user_file_path(username, "citas.json")
    try:
        if citas_file.exists():
            data = _load_json_file_safe(citas_file, [], expected_type=list)
            return data if isinstance(data, list) else []
    except (IOError, json.JSONDecodeError):
        pass
    return []

def guardar_citas(username, citas):
    """Guarda la lista de citas para un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    citas_file = get_user_file_path(username, "citas.json")
    with open(citas_file, 'w', encoding='utf-8') as f:
        json.dump(citas, f, indent=4, ensure_ascii=False)
    _queue_sync_all_dataset_bg(username, "citas", "citas", citas)


DEFAULT_CLIENT_TAGS = ("Falta pagar", "Pagado")


def _normalizar_lista_etiquetas_clientes(etiquetas):
    """Normaliza etiquetas de clientes: strings, sin vacios, unicas (case-insensitive)."""
    resultado = []
    vistos = set()
    for etiqueta in etiquetas or []:
        txt = str(etiqueta or "").strip()
        if not txt:
            continue
        key = txt.casefold()
        if key in vistos:
            continue
        vistos.add(key)
        resultado.append(txt)
    return resultado


def cargar_etiquetas_clientes(username):
    """Carga etiquetas configuradas para clientes del usuario e incluye defaults obligatorios."""
    base = list(DEFAULT_CLIENT_TAGS)
    if not username:
        return base

    etiquetas_file = get_user_file_path(username, "clientes_etiquetas.json")
    etiquetas_usuario = []

    try:
        if etiquetas_file.exists():
            data = _load_json_file_safe(etiquetas_file, [], expected_type=None)
            if isinstance(data, list):
                etiquetas_usuario = data
            elif isinstance(data, dict):
                etiquetas_usuario = data.get("etiquetas", [])
    except Exception:
        etiquetas_usuario = []

    etiquetas_finales = _normalizar_lista_etiquetas_clientes(base + list(etiquetas_usuario or []))

    try:
        os.makedirs(etiquetas_file.parent, exist_ok=True)
        with open(etiquetas_file, "w", encoding="utf-8") as f:
            json.dump(etiquetas_finales, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

    return etiquetas_finales


def guardar_etiquetas_clientes(username, etiquetas):
    """Guarda etiquetas de clientes del usuario manteniendo etiquetas por defecto."""
    if not username:
        return False

    etiquetas_file = get_user_file_path(username, "clientes_etiquetas.json")
    etiquetas_finales = _normalizar_lista_etiquetas_clientes(list(DEFAULT_CLIENT_TAGS) + list(etiquetas or []))

    try:
        os.makedirs(etiquetas_file.parent, exist_ok=True)
        with open(etiquetas_file, "w", encoding="utf-8") as f:
            json.dump(etiquetas_finales, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


def cargar_clientes(username):
    """
    Carga la lista de clientes. Si no hay datos locales, restaura desde la nube.
    - Con sucursal activa/configurada: descarga snapshot de esa sucursal.
    - En modo global (sin sucursal activa): descarga de todas las sucursales activas y consolida.
    """
    clientes_file = get_user_file_path(username, 'clientes.json')

    # 1) Local primero (pero en modo global priorizamos consolidado/restore)
    local_clientes = []
    try:
        if clientes_file.exists():
            clientes = _load_json_file_safe(clientes_file, [], expected_type=list)
            if isinstance(clientes, list):
                local_clientes = clientes
    except Exception:
        local_clientes = []

    branch_code = ""
    try:
        ctx = get_active_branch_context(username) or {}
        branch_code = str(ctx.get("code", "") or "").strip().upper()
    except Exception:
        branch_code = ""

    # Si hay sucursal seleccionada, respetar el archivo redirigido (branch_cache) y retornar local.
    if branch_code and isinstance(local_clientes, list) and local_clientes:
        return local_clientes

    # En modo global ("Todas las sucursales"), si ya hay cache de sucursales, devolver consolidado.
    if not branch_code and isinstance(local_clientes, list) and local_clientes:
        try:
            resolved = resolve_username(username)
            branch_root = VISO_DIR / resolved / "branch_cache"
            has_cached = False
            if branch_root.exists():
                for fp in branch_root.glob("*/data/clientes.json"):
                    try:
                        if fp.exists() and fp.stat().st_size > 5:
                            has_cached = True
                            break
                    except Exception:
                        continue
            if has_cached:
                merged = _load_consolidated_branch_list_dataset(username, "clientes.json")
                if isinstance(merged, list) and merged:
                    return merged
        except Exception:
            pass

        # Si solo hay local pero no hay cache, intentar restore desde nube (throttled).
        if not _should_attempt_cloud_restore(username, "clientes", cooldown_seconds=20):
            return local_clientes

    # 2) Snapshot remoto (modo carpeta). Este restore NO encola sync.
    try:
        with tracked_operation(
            f"cloud-restore:clientes:{username}",
            "Descargando clientes desde nube",
            "download",
        ):
            from utils.api_handler import descargar_snapshot_dispositivo_nube, listar_dispositivos_hijos_remoto

            def _resolve_usuario_madre_cloud():
                # En dispositivos hijo/trabajador, el folder en nube esta bajo el usuario_madre.
                try:
                    cfg_path = get_user_file_path(username, "config_dispositivo.json")
                    if cfg_path.exists():
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        if isinstance(cfg, dict):
                            madre = str(cfg.get("usuario_madre", "") or "").strip()
                            if madre:
                                return madre
                except Exception:
                    pass
                return str(resolve_username(username) or "").strip() or str(username or "").strip()

            usuario_madre = _resolve_usuario_madre_cloud()

            def _download_snapshot_payload(code: str, dataset_name: str):
                """Intenta varias convenciones de nombre de dataset y fallback a snapshot completo."""
                code = str(code or "").strip().upper()
                if not code:
                    return None
                base = str(dataset_name or "").strip().lower()
                for ds in (base, f"{base}.json", None):
                    try:
                        ok_dl, payload_dl, _msg_dl = descargar_snapshot_dispositivo_nube(
                            usuario_madre=usuario_madre,
                            codigo_dispositivo=code,
                            dataset=ds,  # None => snapshot completo
                            include_data=True,
                        )
                        if ok_dl and isinstance(payload_dl, dict):
                            return payload_dl
                    except Exception:
                        continue
                return None

            def _normalize_clientes(value):
                if value is None:
                    return []
                if isinstance(value, list):
                    return value
                if isinstance(value, dict):
                    # Formatos comunes: {"clientes":[...]}, {"data":[...]}, {"data":{"clientes":[...]}}
                    if "clientes" in value:
                        return _normalize_clientes(value.get("clientes"))
                    if "data" in value:
                        return _normalize_clientes(value.get("data"))
                    # Mapping id -> cliente
                    vals = list(value.values())
                    if vals and all(isinstance(v, dict) for v in vals):
                        return vals
                    return []
                return []

            def _extract_clientes(payload):
                if not isinstance(payload, dict):
                    return None
                data = payload.get('data')
                if isinstance(data, (list, dict)) or data is None:
                    return _normalize_clientes(data)
                snap = payload.get('snapshot')
                if isinstance(snap, dict):
                    val = snap.get('clientes')
                    if isinstance(val, (list, dict)) or val is None:
                        return _normalize_clientes(val)
                val2 = payload.get('clientes')
                if isinstance(val2, (list, dict)) or val2 is None:
                    return _normalize_clientes(val2)
                return None

            def _resolve_branch_code():
                # a) contexto activo
                try:
                    ctx = get_active_branch_context(username) or {}
                    code = str(ctx.get('code', '')).strip().upper()
                    if code:
                        return code
                except Exception:
                    pass
                # b) config_dispositivo
                try:
                    cfg_path = get_user_file_path(username, 'config_dispositivo.json')
                    if cfg_path.exists():
                        with open(cfg_path, 'r', encoding='utf-8') as f:
                            cfg = json.load(f)
                        if isinstance(cfg, dict):
                            raw = cfg.get('codigo_dispositivo_hijo') or cfg.get('codigo_dispositivo') or cfg.get('codigo_dispositivo_trabajador') or ''
                            code = str(raw or '').strip().upper()
                            if code:
                                return code
                except Exception:
                    pass
                # c) si hay 1 sucursal activa en local
                try:
                    dh_path = get_user_file_path(username, 'dispositivos_hijos.json')
                    if dh_path.exists():
                        with open(dh_path, 'r', encoding='utf-8') as f:
                            dh = json.load(f)
                        if isinstance(dh, list):
                            activos = [d for d in dh if isinstance(d, dict) and str(d.get('estado', 'activo')).strip().lower() != 'bloqueado' and str(d.get('codigo_dispositivo', '')).strip()]
                            if len(activos) == 1:
                                return str(activos[0].get('codigo_dispositivo', '')).strip().upper()
                except Exception:
                    pass
                return ''

            def _load_from_branch_cache(code):
                try:
                    branch_dir = get_branch_cache_data_dir(username, code)
                    fp = Path(branch_dir) / 'clientes.json'
                    if fp.exists():
                        with open(fp, 'r', encoding='utf-8') as f:
                            data_local = json.load(f)
                        if isinstance(data_local, list):
                            return data_local
                except Exception:
                    pass
                return None

            branch_code = _resolve_branch_code()
            if branch_code:
                payload = _download_snapshot_payload(branch_code, "clientes")
                if payload is not None:
                    clientes_data = _extract_clientes(payload)
                    if clientes_data is not None:
                        try:
                            save_branch_snapshot_datasets(username, branch_code, {'clientes': clientes_data})
                            clear_branch_runtime_caches()
                        except Exception:
                            pass
                        restored = _load_from_branch_cache(branch_code)
                        if restored is not None:
                            return restored
                restored = _load_from_branch_cache(branch_code)
                if restored is not None:
                    return restored
                return []

            if not branch_code:
                # Intentar primero el dataset de la sucursal madre (modo global).
                # Esto cubre instalaciones donde se subio clientes sin sucursal seleccionada.
                try:
                    base = re.sub(r'[^A-Za-z0-9]+', '', str(resolve_username(username)).upper()) or "USER"
                    madre_code = f"MADRE-{base}"[:80]

                    # Compatibilidad: si el madre ya subio usando su codigo_dispositivo VISO-... (config),
                    # intentar tambien ese codigo para restaurar instalaciones antiguas.
                    extra_codes = []
                    try:
                        cfg_path = get_user_file_path(username, "config_dispositivo.json")
                        if cfg_path.exists():
                            with open(cfg_path, "r", encoding="utf-8") as f:
                                cfg = json.load(f)
                            if isinstance(cfg, dict):
                                cfg_code = str(cfg.get("codigo_dispositivo", "") or "").strip().upper()
                                if cfg_code and cfg_code != madre_code:
                                    extra_codes.append(cfg_code)
                    except Exception:
                        pass

                    for code_try in [madre_code] + extra_codes:
                        payloadm = _download_snapshot_payload(code_try, "clientes")
                        if payloadm is None:
                            continue
                        clientes_madre = _extract_clientes(payloadm)
                        if clientes_madre is None:
                            continue
                        try:
                            save_branch_snapshot_datasets(username, code_try, {'clientes': clientes_madre})
                        except Exception:
                            pass
                except Exception:
                    pass

                ok, devices, _msg = listar_dispositivos_hijos_remoto(usuario_madre)

                # Fallback: si el listado legacy falla, listar directamente los snapshots existentes en nube.
                if not ok or not isinstance(devices, list) or not devices:
                    try:
                        from utils.api_handler import listar_snapshots_dispositivos_nube
                        ok_s, snap_devices, _msg_s = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
                        if ok_s and isinstance(snap_devices, list) and snap_devices:
                            ok, devices = True, snap_devices
                    except Exception:
                        pass

                if ok and isinstance(devices, list):
                    for d in devices:
                        if not isinstance(d, dict):
                            continue
                        if str(d.get('estado', 'activo')).strip().lower() == 'bloqueado':
                            continue
                        code = str(d.get('codigo_dispositivo', '')).strip().upper()
                        if not code:
                            continue
                        payload2 = _download_snapshot_payload(code, "clientes")
                        if payload2 is None:
                            continue
                        clientes_data = _extract_clientes(payload2)
                        if clientes_data is None:
                            continue
                        try:
                            save_branch_snapshot_datasets(username, code, {'clientes': clientes_data})
                        except Exception:
                            pass

                # Consolidar lo que haya quedado en cache (incluye madre_code si existia)
                try:
                    clear_branch_runtime_caches()
                except Exception:
                    pass

                try:
                    merged = _load_consolidated_branch_list_dataset(username, 'clientes.json')
                    if isinstance(merged, list) and merged:
                        return merged
                except Exception:
                    pass
    except Exception:
        pass

    # 3) Fallback legacy
    try:
        from utils.api_handler import obtener_clientes_remoto
        ctx = get_effective_branch_context(username) or {}
        branch_code = str(ctx.get("code", "") or "").strip().upper()
        clientes_remotos = obtener_clientes_remoto(
            username,
            codigo_dispositivo=branch_code or None
        )
        if isinstance(clientes_remotos, list) and clientes_remotos:
            guardar_clientes(username, clientes_remotos)
            _mark_initial_sync_resolved_local(
                username,
                source="legacy_remote_restore",
                datasets=["clientes"],
            )
            return clientes_remotos
    except Exception:
        pass

    return []


def guardar_clientes(username, clientes, branch_code: str = ""):
    """Guarda la lista de clientes para un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    try:
        clientes_file = get_user_file_path(username, "clientes.json")
        # Asegurar que el directorio existe
        os.makedirs(clientes_file.parent, exist_ok=True)
        try:
            active_ctx = get_active_branch_context(username) or {}
        except Exception:
            active_ctx = {}
        active_branch_code = str((active_ctx or {}).get("code", "") or "").strip().upper()
        resolved_sync_branch_code = _resolve_branch_code_for_sync(username, branch_code=branch_code)
        snapshot_source_file = clientes_file
        if not active_branch_code and resolved_sync_branch_code:
            try:
                branch_snapshot_file = get_branch_cache_data_dir(username, resolved_sync_branch_code) / "clientes.json"
                if branch_snapshot_file.exists():
                    snapshot_source_file = branch_snapshot_file
            except Exception:
                snapshot_source_file = clientes_file

        # Snapshot previo para detectar deltas (CREATE/UPDATE/DELETE) y asegurar que
        # la nube refleje ediciones/eliminaciones incluso si el backend no "reemplaza"
        # correctamente con SYNC_ALL.
        clientes_previos = []
        try:
            if snapshot_source_file.exists():
                with open(snapshot_source_file, 'r', encoding='utf-8') as f:
                    prev = json.load(f)
                if isinstance(prev, list):
                    clientes_previos = prev
        except Exception:
            clientes_previos = []

        payload = clientes if isinstance(clientes, list) else []
        # Copia superficial de dicts para evitar que la UI mutile datos mientras sincroniza en background.
        try:
            payload = [dict(c) if isinstance(c, dict) else c for c in payload]
        except Exception:
            payload = clientes if isinstance(clientes, list) else []

        # Guardado atÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³mico: escribir en un archivo temporal y luego reemplazar
        tmp_path = clientes_file.with_suffix('.json.tmp')
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            os.replace(str(tmp_path), str(clientes_file))
            if resolved_sync_branch_code:
                try:
                    save_branch_snapshot_datasets(username, resolved_sync_branch_code, {"clientes": payload})
                    clear_branch_runtime_caches()
                except Exception:
                    pass
             
            # ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ LIMPIAR CACHE despuÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s de guardar para reflejar cambios en UI
            try:
                # Nota: 'clientes' y 'pacientes' usan el mismo loader si se configura asÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­,
                # pero por seguridad limpiamos ambos keys posibles si existieran
                from utils.fast_loader import _inventory_cache
                # Clientes podrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­an estar cacheados como 'pacientes' en algunas versiones
                _inventory_cache._cache.pop(f"pacientes:{username}", None) 
                _inventory_cache._cache.pop(f"clientes:{username}", None)
            except ImportError:
                pass
            except Exception:
                pass
                
        finally:
            # Asegurar que no quede el archivo temporal en caso de error
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
        
        # Detectar deltas para asegurar que ediciones/eliminaciones se reflejen en nube.
        # (Algunos backends hacen "merge" en SYNC_ALL y pueden no borrar faltantes).
        def _cliente_registro_id(item):
            if not isinstance(item, dict):
                return ""
            for key in ("dni", "dni_ruc", "id", "codigo", "correo", "nombre"):
                value = str(item.get(key, "")).strip()
                if value:
                    return value
            return ""

        def _cliente_key(item):
            if not isinstance(item, dict):
                return ""
            for key in ("dni", "dni_ruc", "id", "codigo"):
                value = str(item.get(key, "")).strip().lower()
                if value:
                    return f"{key}:{value}"
            correo = str(item.get("correo", "")).strip().lower()
            if correo:
                return f"correo:{correo}"
            nombre = str(item.get("nombre", "")).strip().lower()
            if nombre:
                return f"nombre:{nombre}"
            return ""

        old_map = {}
        new_map = {}
        try:
            for c in clientes_previos:
                k = _cliente_key(c)
                if k:
                    old_map[k] = c
            for c in payload:
                k = _cliente_key(c)
                if k:
                    new_map[k] = c
        except Exception:
            old_map = {}
            new_map = {}

        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())
        create_keys = new_keys - old_keys
        delete_keys = old_keys - new_keys
        common_keys = old_keys & new_keys

        update_keys = set()
        for k in common_keys:
            try:
                old_s = json.dumps(old_map.get(k, {}), ensure_ascii=False, sort_keys=True, default=str)
                new_s = json.dumps(new_map.get(k, {}), ensure_ascii=False, sort_keys=True, default=str)
                if old_s != new_s:
                    update_keys.add(k)
            except Exception:
                update_keys.add(k)

        # Sincronizar en BACKGROUND (thread separado, no bloquea)
        def sync_in_background():
            try:
                from utils.sync_manager import get_sync_manager
                import threading
                
                sync_mgr = get_sync_manager()
                
                # Resolver codigo de sucursal para que el server lo asocie a una tienda real.
                bc = str(resolved_sync_branch_code or "").strip().upper()

                # Agregar a cola de sync
                usuario_id = str(_resolve_usuario_id_for_sync(username))
                registro_id = (f"bulk:{bc}" if bc else "bulk")
                contenido = {'clientes': payload}
                if bc:
                    contenido['_meta'] = {'branch_code': bc}

                delta_ops = int(len(create_keys) + len(update_keys) + len(delete_keys))
                use_full_sync = delta_ops > 50  # Evitar 100+ deltas en cargas masivas (primer sync/import).

                # Encolar deltas puntuales (edicion/eliminacion) para que el servidor los aplique
                # aun cuando el SYNC_ALL sea ignorado o haga merge sin borrar.
                def _with_meta(item_dict):
                    if not isinstance(item_dict, dict):
                        return {}
                    out = dict(item_dict)
                    if not bc:
                        return out
                    meta = out.get("_meta")
                    merged_meta = dict(meta) if isinstance(meta, dict) else {}
                    merged_meta["branch_code"] = bc
                    out["_meta"] = merged_meta
                    return out

                if not use_full_sync:
                    try:
                        for key in sorted(create_keys):
                            cli = new_map.get(key, {})
                            rid = _cliente_registro_id(cli) or key
                            sync_mgr.queue_change(
                                usuario_id=str(usuario_id),
                                tipo_dato='clientes',
                                operacion='CREATE',
                                registro_id=str(rid),
                                contenido=_with_meta(cli),
                            )
                        for key in sorted(update_keys):
                            cli = new_map.get(key, {})
                            rid = _cliente_registro_id(cli) or key
                            sync_mgr.queue_change(
                                usuario_id=str(usuario_id),
                                tipo_dato='clientes',
                                operacion='UPDATE',
                                registro_id=str(rid),
                                contenido=_with_meta(cli),
                            )
                        for key in sorted(delete_keys):
                            cli = old_map.get(key, {})
                            rid = _cliente_registro_id(cli) or key
                            sync_mgr.queue_change(
                                usuario_id=str(usuario_id),
                                tipo_dato='clientes',
                                operacion='DELETE',
                                registro_id=str(rid),
                                contenido=_with_meta(cli),
                            )
                    except Exception:
                        pass

                # Solo usar SYNC_ALL en cargas masivas/import; en ediciÃ³n normal evitamos reemplazar dataset completo.
                if use_full_sync:
                    # Coalescer: mantener solo el ultimo SYNC_ALL por dataset+sucursal
                    try:
                        if hasattr(sync_mgr, "queue") and hasattr(sync_mgr.queue, "clear_pending_sync_all_for_dataset"):
                            sync_mgr.queue.clear_pending_sync_all_for_dataset(
                                usuario_id=str(usuario_id),
                                tipo_dato="clientes",
                                registro_id=str(registro_id),
                            )
                    except Exception:
                        pass

                    sync_mgr.queue_change(
                        usuario_id=usuario_id,
                        tipo_dato='clientes',
                        operacion='SYNC_ALL',
                        registro_id=registro_id,
                        contenido=contenido,
                    )
                
                # Intentar sincronizar ahora
                sync_mgr.sync_now(usuario_id, force=True)
            except Exception:
                pass
        
        # Lanzar sync en thread separado (daemon=True para que no bloquee)
        import threading
        sync_thread = threading.Thread(target=sync_in_background, daemon=True)
        sync_thread.start()
        
    except Exception as e:
        # Fallback: solo guardar localmente
        clientes_file = get_user_file_path(username, "clientes.json")
        os.makedirs(clientes_file.parent, exist_ok=True)
        with open(clientes_file, 'w', encoding='utf-8') as f:
            json.dump(clientes, f, indent=4, ensure_ascii=False)

def cargar_metodos_pago(username):
    """Carga la lista de mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©todos de pago de un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    pagos_file = get_user_file_path(username, "metodos_pago.json")
    try:
        if pagos_file.exists():
            data = _load_json_file_safe(pagos_file, [], expected_type=list)
            return data if isinstance(data, list) else []
    except (IOError, json.JSONDecodeError):
        pass
    return []

def guardar_metodos_pago(username, metodos):
    """Guarda la lista de mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©todos de pago para un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    pagos_file = get_user_file_path(username, "metodos_pago.json")
    os.makedirs(pagos_file.parent, exist_ok=True)
    payload = metodos if isinstance(metodos, list) else []
    with open(pagos_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    def sync_in_background():
        try:
            from utils.sync_manager import get_sync_manager

            # Resolver usuario_id si existe mapeo en .usuarios.json
            usuarios = cargar_usuarios() or {}
            usuario_id = None
            for uid, info in usuarios.items():
                if isinstance(info, dict) and info.get('username') == username:
                    usuario_id = uid
                    break
            if not usuario_id:
                usuario_id = username

            contenido_sync = {'metodos_pago': payload}
            try:
                branch_ctx = get_active_branch_context(username)
                branch_code = str((branch_ctx or {}).get("code", "")).strip().upper()
                branch_label = str((branch_ctx or {}).get("label", "")).strip()
                if branch_code:
                    contenido_sync["_meta"] = {
                        "branch_code": branch_code,
                        "branch_label": branch_label
                    }
            except Exception:
                pass

            sync_mgr = get_sync_manager()
            sync_mgr.queue_change(
                usuario_id=str(usuario_id),
                tipo_dato='metodos_pago',
                operacion='SYNC_ALL',
                registro_id='bulk',
                contenido=contenido_sync
            )
            sync_mgr.sync_now(str(usuario_id), force=True)
        except Exception:
            pass

    try:
        threading.Thread(target=sync_in_background, daemon=True).start()
    except Exception:
        pass

def cargar_servicios(username):
    servicios_file = get_user_file_path(username, "servicios.json")
    try:
        if servicios_file.exists():
            with open(servicios_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (IOError, json.JSONDecodeError):
        pass
    return []

def guardar_servicios(username, servicios):
    servicios_file = get_user_file_path(username, "servicios.json")
    os.makedirs(servicios_file.parent, exist_ok=True)
    with open(servicios_file, 'w', encoding='utf-8') as f:
        json.dump(servicios, f, indent=4, ensure_ascii=False)
    _queue_sync_all_dataset_bg(username, "servicios", "servicios", servicios)

def cargar_graduaciones(username):
    """
    Carga la lista de graduaciones de un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico.
    Extrae automÃƒÆ’Ã†â€™Ã‚Â¡ticamente todas las graduaciones del historial de pacientes.
    """
    try:
        # Intentar cargar desde archivo de graduaciones.json primero
        graduaciones_file = get_user_file_path(username, "graduaciones.json")
        if graduaciones_file.exists():
            try:
                data = _load_json_file_safe(graduaciones_file, [], expected_type=list)
                if data:  # Si hay datos en el archivo, usarlos
                    return data
            except (IOError, json.JSONDecodeError):
                pass
        
        # Si no existe o estÃƒÆ’Ã†â€™Ã‚Â¡ vacÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­o, extraer de pacientes
        pacientes = cargar_pacientes(username)
        graduaciones = []
        
        for paciente in pacientes:
            historial = paciente.get('historial_graduaciones', [])
            for grad in historial:
                # Enriquecer con datos del paciente
                # Mapear monto_cobrado a precio y pago
                monto_total = str(grad.get('monto_cobrado', '0'))
                monto_pagado = str(grad.get('monto_adelanto') if grad.get('monto_adelanto') else monto_total)

                grad_completa = {
                    'fecha': grad.get('fecha', ''),
                    'paciente': paciente.get('nombre', 'N/A'),
                    'dni': paciente.get('dni', ''),
                    'optica_medico': grad.get('medico_optometra', grad.get('optometra', grad.get('optica_medico', 'N/A'))),
                    'tipo': grad.get('tipo', 'GraduaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n'),
                    'informacion': grad.get('prescripcion', grad.get('informacion', '')),
                    'precio': monto_total,
                    'pago': monto_pagado,
                    'id_paciente': paciente.get('id', ''),
                }
                graduaciones.append(grad_completa)
        
        return graduaciones
    except Exception:
        return []

def guardar_graduaciones(username, graduaciones):
    """Guarda la lista de graduaciones para un usuario especÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­fico."""
    graduaciones_file = get_user_file_path(username, "graduaciones.json")
    os.makedirs(graduaciones_file.parent, exist_ok=True)
    with open(graduaciones_file, 'w', encoding='utf-8') as f:
        json.dump(graduaciones, f, indent=4, ensure_ascii=False)
    _queue_sync_all_dataset_bg(username, "graduaciones", "graduaciones", graduaciones)

# ============================================================================
# PLANTILLA DE BOLETA (PersonalizaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de diseÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â±o de recibos)
# ============================================================================

def cargar_plantilla_boleta(username):
    """
    Carga la configuraciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n personalizada de la plantilla de boleta del usuario.
    
    Retorna un diccionario con:
    - ancho_mm: Ancho de la boleta en milÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­metros (default: 80)
    - margen_mm: Margen de la boleta en milÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­metros (default: 2.5)
    - secciones_orden: Lista de secciones en orden ['encabezado', 'fecha', 'cliente', ...]
    - secciones_config: ConfiguraciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n individual de cada secciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n
    """
    plantilla_file = get_user_file_path(username, "plantilla_boleta.json")
    try:
        if plantilla_file.exists():
            plantilla = _load_json_file_safe(plantilla_file, {}, expected_type=dict)
            if True:
                
                # Validar que tenga las claves importantes
                if 'secciones_orden' in plantilla and 'secciones_config' in plantilla:
                    print(f"ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Plantilla cargada: {len(plantilla['secciones_orden'])} secciones")
                    return plantilla
                else:
                    print("ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â Plantilla incompleta, usando valores por defecto")
    except (IOError, json.JSONDecodeError) as e:
        print(f"ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â Error al cargar plantilla: {e}")
    
    # Estructura por defecto
    return {
        "ancho_mm": 80,
        "margen_mm": 2.5,
        "secciones_orden": [
            "encabezado", "fecha", "cliente", "tabla", "totales", "qr", "pie"
        ],
        "secciones_config": {}
    }

def guardar_plantilla_boleta(username, plantilla):
    """
    Guarda la configuraciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n personalizada de la plantilla de boleta del usuario.
    
    Args:
        username: Usuario actual
        plantilla: Diccionario con configuraciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de la plantilla
    """
    plantilla_file = get_user_file_path(username, "plantilla_boleta.json")
    os.makedirs(plantilla_file.parent, exist_ok=True)
    
    # GUARDAR SOLO LO QUE EL USUARIO CONFIGURÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ (sin mezclar con valores antiguos)
    with open(plantilla_file, 'w', encoding='utf-8') as f:
        json.dump(plantilla, f, indent=4, ensure_ascii=False)
    
    print(f"ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Plantilla guardada en: {plantilla_file}")
    print(f"  Secciones guardadas: {plantilla.get('secciones_orden', [])}")
    print(f"  Configuraciones: {plantilla.get('secciones_config', {})}")


def cargar_impresora_predeterminada(username):
    """
    Carga la impresora predeterminada del usuario.
    
    Args:
        username: Usuario actual
        
    Returns:
        Nombre de la impresora (string) o None si no hay guardada
    """
    try:
        printer_file = get_user_file_path(username, "impresora_predeterminada.json")
        if printer_file.exists():
            with open(printer_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('printer_name')
    except Exception as e:
        print(f"Error al cargar impresora predeterminada: {e}")
    
    return None


def guardar_impresora_predeterminada(username, printer_name):
    """
    Guarda la impresora predeterminada del usuario.
    
    Args:
        username: Usuario actual
        printer_name: Nombre de la impresora
    """
    try:
        printer_file = get_user_file_path(username, "impresora_predeterminada.json")
        os.makedirs(printer_file.parent, exist_ok=True)
        
        data = {
            'printer_name': printer_name,
            'fecha_cambio': datetime.datetime.now().isoformat()
        }
        
        with open(printer_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error al guardar impresora predeterminada: {e}")
        return False

        
def comprimir_y_subir_datos(username):
    """
    Sube los archivos de datos del usuario preservando la estructura de carpetas.
    - Mantiene la estructura: data/, reports/, images/, etc.
    - Sube cada archivo individualmente con su ruta relativa
    - El servidor recibe: usuario/data/archivo.json, usuario/reports/doc.pdf, etc.
    """
    try:
        # Resolver username si se recibe un ID
        usuarios = cargar_usuarios() or {}
        resolved_username = username
        if username in usuarios:
            info = usuarios.get(username)
            if isinstance(info, dict) and info.get('username'):
                resolved_username = info.get('username')

        # Obtener la carpeta del usuario
        user_dir = VISO_DIR / resolved_username
        if not user_dir.exists():
            return False, f"La carpeta del usuario no existe: {user_dir}"

        from utils.sync_manager import get_sync_manager

        sync_mgr = get_sync_manager()
        result = sync_mgr.force_cloud_backup(str(username))
        ok = bool(result.get("ok"))
        message = str(result.get("message") or "").strip() or "Respaldo cloud finalizado"
        return ok, message
        
        # Recolectar todos los archivos con su ruta relativa
        files_to_upload_list = []
        total_size = 0
        
        for root, dirs, files in os.walk(user_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Calcular ruta relativa desde la carpeta del usuario
                relative_path = os.path.relpath(file_path, user_dir)
                files_to_upload_list.append((file_path, relative_path))
                total_size += os.path.getsize(file_path)
        
        if not files_to_upload_list:
            return False, "No hay archivos para respaldar."
        
        # Subir cada archivo manteniendo su ruta
        uploaded_count = 0
        errors = []
        
        for file_path, relative_path in files_to_upload_list:
            try:
                # Verificar que el archivo existe y es legible
                if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
                    continue

                file_size = os.path.getsize(file_path)
                
                # Calcular MD5
                try:
                    md5 = hashlib.md5()
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            md5.update(chunk)
                    md5_hash = md5.hexdigest()
                except Exception:
                    md5_hash = None

                # Preparar archivo para subir
                with open(file_path, 'rb') as f:
                    files = {'archivo': (file_path, f, 'application/octet-stream')}
                    headers = {
                        'X-User-Viso': str(username),
                        'X-File-Path': relative_path,  # Ruta relativa para el servidor
                        'X-File-Size': str(file_size),
                    }
                    if md5_hash is not None:
                        headers['X-File-MD5'] = md5_hash

                    # Subir con timeout
                    response = requests.post(upload_url, files=files, headers=headers, timeout=30)

                    # Verificar respuesta
                    try:
                        response_json = response.json()
                        if response_json.get('success'):
                            uploaded_count += 1
                        else:
                            error_msg = response_json.get('error', 'Error desconocido')
                            errors.append(f"{relative_path}: {error_msg}")
                    except Exception as e:
                        errors.append(f"{relative_path}: Error ({response.status_code})")

            except Exception as e:
                errors.append(f"{relative_path}: {str(e)[:50]}")

        # Devolver resultado
        if uploaded_count > 0:
            msg = f"ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Subidos {uploaded_count} archivos ({total_size} bytes)"
            if errors:
                msg += f" - {len(errors)} errores ignorados"
            return True, msg
        else:
            if errors:
                return False, f"Error: No se pudo subir ningÃƒÆ’Ã†â€™Ã‚Âºn archivo. {', '.join(errors[:3])}"
            return False, "No se subiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³ ningÃƒÆ’Ã†â€™Ã‚Âºn archivo."

    except Exception as e:
        import traceback
        return False, f"Error inesperado en respaldo: {e}\n{traceback.format_exc()[:200]}"

def descargar_y_descomprimir_datos(username):
    """
    Descarga el ÃƒÆ’Ã†â€™Ã‚Âºltimo archivo de respaldo del usuario y lo descomprime.
    """
    try:
        url = f'https://boletaspe.com/recibir.php?username={username}'
        headers = {
            'Authorization': os.getenv('VISO_BACKUP_TOKEN', '')
        }
        
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        if response.headers['Content-Type'] == 'application/json':
            response_json = response.json()
            return False, response_json.get('message', 'Error desconocido del servidor.'), None

        temp_zip_path = VISO_DIR / "temp" / f"backup_{username}_downloaded.zip"
        os.makedirs(temp_zip_path.parent, exist_ok=True)

        with open(temp_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True, "Archivo descargado correctamente.", temp_zip_path
    
    except requests.exceptions.RequestException as e:
        return False, f"Error de conexiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n o del servidor: {e}", None
    except zipfile.BadZipFile:
        return False, "El archivo descargado no es un archivo ZIP vÃƒÆ’Ã†â€™Ã‚Â¡lido.", None
    except Exception as e:
        return False, f"Error al descargar y descomprimir los datos: {e}", None

def crear_tabla_usuarios_remoto():
    """
    Llama al script en la nube para crear la tabla de usuarios.
    """
    url = 'https://boletaspe.com/crear_tabla_usuarios.php'
    headers = {
        'X-Auth-Key': 'TU_CLAVE_DE_SEGURIDAD' 
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['success'], data['message']
    except requests.exceptions.RequestException as e:
        return False, f"Error de conexiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n con el servidor: {e}"
    except Exception as e:
        return False, f"Error inesperado: {e}"
        
# --- Nuevas funciones para exportar e importar datos generales ---

def borrar_respaldos_antiguos_remoto(username, max_backups=30):
    """
    Solicita al servidor que borre los respaldos antiguos y conserve solo los mÃƒÆ’Ã†â€™Ã‚Â¡s recientes.
    """
    # Algunos servidores no exponen un endpoint "borrar_antiguos.php".
    # En su lugar listamos los backups y borramos los mÃƒÆ’Ã†â€™Ã‚Â¡s antiguos usando
    # los endpoints conocidos: listar_backups.php y borrar_backup.php
    try:
        endpoint_list = "https://boletaspe.com/listar_backups.php"
        endpoint_delete = "https://boletaspe.com/borrar_backup.php"
        success, deleted = borrar_todos_menos_ultimos_remoto(username, endpoint_list, endpoint_delete, keep_last=max_backups)
        return success, deleted
    except Exception as e:
        return False, f"Error al borrar respaldos: {e}"


def comprimir_y_subir_todos(output_log=None, only_numeric_users=True, include_list=None, use_usuarios_file=True):
    """Comprime y sube todos los usuarios encontrados en la carpeta VISO/.
    Por defecto solo procesa carpetas cuyo nombre es numÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rico (p.ej. '384793982'),
    que corresponde al ID de cada usuario. Esto evita subir carpetas globales
    como 'images', 'boletas' o 'reportes'.

    ParÃƒÆ’Ã†â€™Ã‚Â¡metros:
      output_log: funciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n opcional para logging (acepta str).
      only_numeric_users: si True, procesa solo carpetas cuyo nombre contenga solo dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­gitos.
      include_list: lista opcional de nombres de carpetas adicionales a incluir (ej: ['boletas']).

    Retorna un dict con resultados por usuario.
    """
    resultados = {}
    try:
        include_list = include_list or []
        # Si existe el archivo .usuarios.json y use_usuarios_file estÃƒÆ’Ã†â€™Ã‚Â¡ activado,
        # preferimos respaldar por los nombres de usuario definidos ahÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­ (campo 'username').
        usuarios_map = {}
        if use_usuarios_file and USUARIOS_FILE.exists():
            try:
                usuarios_map = cargar_usuarios() or {}
            except Exception:
                usuarios_map = {}

        # Si usuarios_map no estÃƒÆ’Ã†â€™Ã‚Â¡ vacÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­o, construir la lista de nombres reales
        if usuarios_map:
            # usuarios_map tiene claves (IDs) y valores con 'username'
            usernames = []
            for k, v in usuarios_map.items():
                if isinstance(v, dict) and 'username' in v and v['username']:
                    usernames.append(v['username'])

            for username in usernames:
                user_dir = VISO_DIR / username
                if not user_dir.exists() or not user_dir.is_dir():
                    if output_log:
                        output_log(f"No existe carpeta para usuario listado: {username}")
                    continue
                if output_log:
                    output_log(f"Iniciando respaldo para usuario (desde .usuarios.json): {username}")
                success, info = comprimir_y_subir_datos(username)
                resultados[username] = {'success': success, 'info': info}
                if output_log:
                    output_log(f"Resultado {username}: {success} - {info}")

            return resultados

        # Fallback: iterar carpetas en VISO_DIR
        for child in VISO_DIR.iterdir():
            if not child.is_dir():
                continue
            username = child.name
            # Siempre ignorar carpetas internas temporales
            if username in ('.cache', 'temp'):
                continue

            # Si only_numeric_users estÃƒÆ’Ã†â€™Ã‚Â¡ activado, aceptar solo nombres que sean dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­gitos
            if only_numeric_users and not re.fullmatch(r"\d+", username):
                # Permitir explÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­citamente nombres en include_list
                if username not in include_list:
                    if output_log:
                        output_log(f"Omitiendo carpeta no-usuario: {username}")
                    continue

            if output_log:
                output_log(f"Iniciando respaldo para usuario: {username}")
            success, info = comprimir_y_subir_datos(username)
            resultados[username] = {'success': success, 'info': info}
            if output_log:
                output_log(f"Resultado {username}: {success} - {info}")
    except Exception as e:
        if output_log:
            output_log(f"Error al respaldar todos los usuarios: {e}")
    return resultados

def exportar_datos_generales(username, destination_dir):
    """
    Exporta todos los archivos de datos de un usuario a un archivo ZIP.
    Retorna la ruta del archivo ZIP creado.
    """
    try:
        user_data_path = VISO_DIR / username / "data"
        if not user_data_path.exists():
            return False, "La carpeta de datos del usuario no existe.", None
        
        zip_filename = f"backup_{username}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
        zip_filepath = Path(destination_dir) / zip_filename
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(user_data_path):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), user_data_path.parent))

        return True, "Datos exportados correctamente.", str(zip_filepath)
    
    except Exception as e:
        return False, f"Error al exportar los datos: {e}", None

def importar_datos_generales(username, source_zip_path, modo='reemplazar'):
    """
    Importa datos de un archivo ZIP, reemplazando o agregando a los datos locales.
    """
    temp_dir = VISO_DIR / "temp_import"
    
    try:
        os.makedirs(temp_dir, exist_ok=True)
        
        with zipfile.ZipFile(source_zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        zip_content_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
        if not zip_content_dirs:
            shutil.rmtree(temp_dir)
            return False, "El archivo ZIP no contiene una estructura de datos vÃƒÆ’Ã†â€™Ã‚Â¡lida."

        backup_username = zip_content_dirs[0]
        backup_user_data_path = temp_dir / backup_username / "data"

        if not backup_user_data_path.exists():
             shutil.rmtree(temp_dir)
             return False, "El archivo ZIP no contiene una estructura de datos vÃƒÆ’Ã†â€™Ã‚Â¡lida."

        if modo == 'reemplazar':
            user_data_path = VISO_DIR / username
            if user_data_path.exists():
                shutil.rmtree(user_data_path)
            shutil.copytree(backup_user_data_path.parent, user_data_path)
            shutil.rmtree(temp_dir)
            return True, "Datos reemplazados correctamente."
        
        elif modo == 'agregar':
            data_types = ['pacientes', 'productos', 'ventas', 'optometras', 'metodos_pago', 'clientes']
            for data_type in data_types:
                local_file_path = get_user_file_path(username, f"{data_type}.json")
                backup_file_path = backup_user_data_path / f"{data_type}.json"
                
                if backup_file_path.exists():
                    try:
                        with open(local_file_path, 'r') as local_file:
                            local_data = json.load(local_file)
                    except (IOError, json.JSONDecodeError):
                        local_data = []

                    with open(backup_file_path, 'r') as backup_file:
                        try:
                            backup_data = json.load(backup_file)
                        except json.JSONDecodeError:
                            backup_data = []
                    
                    if isinstance(local_data, list) and isinstance(backup_data, list):
                        local_data.extend(backup_data)
                    
                    with open(local_file_path, 'w') as local_file:
                        json.dump(local_data, local_file, indent=4)
            
            shutil.rmtree(temp_dir)
            return True, "Datos agregados correctamente."
        
        shutil.rmtree(temp_dir)
        return True, "OperaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de importaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n completada."

    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False, f"Error al importar los datos: {e}"
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# --- Funciones de LÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³gica de Negocio ---

def buscar_dni_api(dni):
    """
    Busca informaciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de un DNI usando la API de boletaspe.com.
    Retorna (nombre_completo, None).
    """
    try:
        # Opcion 1 (nitro): eldni.com (HTML con token). Si falla, se usa boletaspe.
        try:
            if BeautifulSoup is not None:
                dni_txt = str(dni or "").strip()
                if dni_txt:
                    url_nitro = "https://eldni.com/pe/buscar-datos-por-dni"
                    headers = {
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"
                        ),
                        "Referer": url_nitro,
                        "Origin": "https://eldni.com",
                    }

                    with requests.Session() as s:
                        r = s.get(url_nitro, headers=headers, timeout=7)
                        soup = BeautifulSoup(r.text or "", "html.parser")
                        token_el = soup.find("input", {"name": "_token"})
                        token = ""
                        if token_el is not None:
                            try:
                                token = str(token_el.get("value", "") or "").strip()
                            except Exception:
                                token = ""

                        if token:
                            # Small delay to reduce bot detection.
                            try:
                                time.sleep(0.1)
                            except Exception:
                                pass

                            payload = {"_token": token, "dni": dni_txt}
                            r2 = s.post(url_nitro, data=payload, headers=headers, timeout=7)
                            soup2 = BeautifulSoup(r2.text or "", "html.parser")
                            tabla = soup2.find("table")
                            if tabla is not None:
                                tds = tabla.find_all("td")
                                vals = [str(td.get_text(" ", strip=True) or "").strip() for td in tds]
                                if len(vals) >= 4:
                                    nombres = vals[1]
                                    ap_pat = vals[2]
                                    ap_mat = vals[3]
                                    full_name_nitro = f"{nombres} {ap_pat} {ap_mat}".strip()
                                    if full_name_nitro:
                                        return full_name_nitro, None
        except Exception:
            # Silent fallback to legacy provider below.
            pass

        url = f"https://boletaspe.com/buscar_dni.php?dni={dni}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        nombres = data.get("nombres", "").strip()
        apellidos = data.get("apellidos", "").strip()
        full_name = f"{nombres} {apellidos}".strip()

        if full_name:
            return full_name, None
        else:
            return None, None

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error en buscar_dni_api: {e}")
        return None, None

def calcular_vision_cerca(esferico, adicion):
    """Calcula la visiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de cerca a partir de los valores de lejos y adiciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n.
    FÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³rmula: EsfÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rico de Cerca = EsfÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rico de Lejos + AdiciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n
    """
    try:
        esferico_val = float(esferico) if esferico else 0
        adicion_val = float(adicion) if adicion else 0
        resultado = esferico_val + adicion_val
        if resultado == int(resultado):
            return f"{int(resultado)}.0"
        return f"{resultado:.2f}"
    except ValueError:
        return ""

def calcular_vision_lejos_con_adicion(esferico, adicion):
    """Calcula la visiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de lejos sumando la adiciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n al esfÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rico."""
    try:
        esferico_val = float(esferico) if esferico else 0
        adicion_val = float(adicion) if adicion else 0
        resultado = esferico_val + adicion_val
        if resultado == int(resultado):
            return f"{int(resultado)}.0"
        return f"{resultado:.2f}"
    except ValueError:
        return ""

def generar_expediente_pdf(paciente_data, nombre_optica):
    print("FunciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de expediente PDF llamada.")
    return "expediente.pdf"

def generar_boleta(venta, paciente_nombre, nombre_optica, username):
    print("FunciÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n de boleta llamada.")
    return "boleta.pdf"

def open_pdf_with_chrome(pdf_path, auto_print=False):
    """
    Abre un PDF con Google Chrome en lugar del navegador predeterminado.
    
    Args:
        pdf_path: Ruta al archivo PDF
        auto_print: Si True, abre el diÃƒÆ’Ã†â€™Ã‚Â¡logo de impresiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n automÃƒÆ’Ã†â€™Ã‚Â¡ticamente
    """
    import subprocess
    import os
    
    # Convertir a ruta absoluta
    abs_path = os.path.abspath(pdf_path)
    
    # Rutas comunes de Chrome en Windows
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    
    # Buscar Chrome instalado
    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            break
    
    # Si Chrome no se encuentra, intentar con el navegador predeterminado
    if chrome_exe is None:
        try:
            os.startfile(abs_path)
            return
        except Exception as e:
            print(f"Error al abrir PDF: {e}")
            return
    
    # Abrir con Chrome directamente
    try:
        args = [
            chrome_exe,
            f"file:///{abs_path}",
            "--new-window"  # Abre en nueva ventana
        ]
        
        subprocess.Popen(args)
    except Exception as e:
        print(f"Error al abrir con Chrome: {e}")
        # Fallback
        try:
            os.startfile(abs_path)
        except Exception as e2:
            print(f"Error al abrir: {e2}")

def print_pdf_direct(pdf_path, printer_name=None):
    """
    Imprime un PDF directamente en la impresora tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rmica sin diÃƒÆ’Ã†â€™Ã‚Â¡logos.
    Usa impresoras Bluetooth tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rmicas (80mm, 58mm).
    
    Args:
        pdf_path: Ruta al archivo PDF
        printer_name: Nombre de la impresora (si None, usa la predeterminada)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    import os
    
    if not os.path.exists(pdf_path):
        return False, f"Archivo PDF no encontrado: {pdf_path}"
    
    pdf_path = os.path.abspath(pdf_path)
    
    try:
        # Intentar usar el printer_handler que ya existe
        from utils.printer_handler import print_boleta
        success, message = print_boleta(pdf_path, printer_name)
        return success, message
        
    except ImportError:
        print("[WARN] printer_handler no disponible, intentando mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©todo alternativo")
    except Exception as e:
        print(f"[ERROR] Error en impresiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n directa: {e}")
    
    # Fallback: Intentar con escpos directamente
    try:
        from utils.escpos_thermal_printer import ThermalBluetoothPrinter
        return ThermalBluetoothPrinter.print_pdf_to_thermal(pdf_path)
    except Exception as e:
        return False, f"Error en impresiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³n tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rmica: {e}"










# MOCK PARA EVITAR BLOQUEO
def is_modo_basico_safe(username):
    try:
        from pathlib import Path
        import json
        # Usar ruta absoluta directa para evitar dependencias circulares
        modo_file = Path(r'C:\Users\USUARIO.DESKTOP-NOO0BDB\Desktop\VISO') / username / 'data' / 'modo_basico.json'
        if modo_file.exists():
            with open(modo_file, 'r', encoding='utf-8') as f:
                return bool(json.load(f).get('modo_basico', False))
    except: pass
    return False
# FIX PARA BLOQUEO - VERSIÃ“N 2
def is_modo_basico_safe(username):
    try:
        from pathlib import Path
        import json
        p = Path(r'C:\Users\USUARIO.DESKTOP-NOO0BDB\Desktop\VISO') / str(username) / 'data' / 'modo_basico.json'
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                return bool(json.load(f).get('modo_basico', False))
    except: pass
    return False

