"""
Manejador de API con reintentos, timeouts y validación robusta.
"""

import requests
import os
import json
import time
import re
import threading
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse
from utils.error_logger import get_logger

logger = get_logger('API')

# Configuración de reintentos (preferir config_license.py si existe)
try:
    from config_license import get_config as _get_license_config  # type: ignore
except Exception:
    def _get_license_config(key: str, default=None):
        return default

MAX_RETRIES = int(_get_license_config('MAX_RETRIES', 1) or 1)
RETRY_DELAY = 0.5  # segundos
TIMEOUT = int(_get_license_config('API_TIMEOUT', 5) or 5)  # segundos
BACKOFF_FACTOR = float(_get_license_config('BACKOFF_FACTOR', 2) or 2)  # Factor exponencial

# Códigos de error recuperables
RECOVERABLE_CODES = {408, 429, 502, 503, 504}

# CACHE para reducir consumo de internet
# Cachea productos remotos por 30 segundos
_CACHE_PRODUCTOS_REMOTO = {}
_CACHE_TIMEOUT = 30  # segundos

# Track de imágenes ya subidas para evitar re-uploads innecesarios
_UPLOADED_IMAGES = {}  # {codigo: timestamp}

# Cache negativa para evitar castigar la red cuando un snapshot aun no existe.
_MISSING_SNAPSHOT_CACHE: Dict[str, Tuple[float, str]] = {}
_MISSING_SNAPSHOT_CACHE_TTL = 90  # segundos
_MISSING_SNAPSHOT_CACHE_LOCK = threading.Lock()


def _is_missing_snapshot_message(message: str) -> bool:
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


def _build_missing_snapshot_cache_key(
    usuario_madre: str,
    codigo_dispositivo: str,
    dataset: Optional[str],
    include_data: bool,
) -> str:
    _ = include_data
    return "|".join(
        [
            str(usuario_madre or "").strip().lower(),
            str(codigo_dispositivo or "").strip().upper(),
            str(dataset or "").strip().lower() or "*",
        ]
    )


def _get_missing_snapshot_cached_message(cache_key: str) -> Optional[str]:
    now = time.time()
    with _MISSING_SNAPSHOT_CACHE_LOCK:
        cached = _MISSING_SNAPSHOT_CACHE.get(cache_key)
        if not cached:
            return None
        ts, message = cached
        if (now - float(ts or 0.0)) > _MISSING_SNAPSHOT_CACHE_TTL:
            _MISSING_SNAPSHOT_CACHE.pop(cache_key, None)
            return None
        return str(message or "Device snapshot folder not found")


def _remember_missing_snapshot(cache_key: str, message: str) -> None:
    with _MISSING_SNAPSHOT_CACHE_LOCK:
        _MISSING_SNAPSHOT_CACHE[cache_key] = (
            time.time(),
            str(message or "Device snapshot folder not found"),
        )


def _clear_missing_snapshot_cache_for_device(
    usuario_madre: str,
    codigo_dispositivo: str,
) -> None:
    usuario_madre = str(usuario_madre or "").strip().lower()
    codigo_dispositivo = str(codigo_dispositivo or "").strip().upper()
    if not usuario_madre or not codigo_dispositivo:
        return
    prefix = f"{usuario_madre}|{codigo_dispositivo}|"
    with _MISSING_SNAPSHOT_CACHE_LOCK:
        stale_keys = [key for key in _MISSING_SNAPSHOT_CACHE if key.startswith(prefix)]
        for key in stale_keys:
            _MISSING_SNAPSHOT_CACHE.pop(key, None)


def validate_api_url(url: str) -> bool:
    """Valida que la URL sea segura y válida."""
    if not url:
        logger.warning("URL vacía")
        return False
    
    if len(url) > 2048:
        logger.warning(f"URL demasiado larga: {len(url)} caracteres")
        return False
    
    try:
        parsed = urlparse(url)
        
        # Validar protocolo
        if parsed.scheme.lower() not in ('http', 'https'):
            logger.warning(f"Protocolo no permitido: {parsed.scheme}")
            return False
        
        # Validar que tenga netloc
        if not parsed.netloc:
            logger.warning("URL sin dominio")
            return False
        
        # Validar caracteres de control
        if any(ord(c) < 32 for c in url):
            logger.warning("URL contiene caracteres de control")
            return False
        
        logger.debug(f"URL validada: {parsed.netloc}")
        return True
    
    except Exception as e:
        logger.error(f"Error validando URL: {e}")
        return False


def validate_payload(payload: Any) -> bool:
    """Valida que el payload sea JSON serializable."""
    try:
        json.dumps(payload)
        return True
    except (TypeError, ValueError) as e:
        logger.error(f"Payload no es JSON serializable: {e}")
        return False


def _resolve_local_offline_login(username: str, password: str) -> Tuple[bool, str]:
    """Valida credenciales contra el cache local solo si existe coincidencia exacta."""
    try:
        from utils.file_handler import cargar_usuarios

        usuarios = cargar_usuarios() or {}
        username_norm = str(username or "").strip()
        password_norm = str(password or "").strip()

        for user_id, info in usuarios.items():
            if not isinstance(info, dict):
                continue
            saved_username = str(info.get("username", "")).strip()
            saved_password = str(info.get("password", "")).strip()
            if saved_username == username_norm and saved_password == password_norm:
                return True, str(user_id)
    except Exception as e:
        logger.warning(f"No se pudo validar login offline local: {e}")

    return False, ""


def _attempt_login_request(url: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict], str]:
    """Prueba variantes de POST para evitar bloqueos de hosting/WAF."""
    attempts = [
        {
            "label": "json",
            "kwargs": {
                "json": payload,
                "timeout": TIMEOUT,
            },
        },
        {
            "label": "form",
            "kwargs": {
                "data": payload,
                "timeout": TIMEOUT,
                "headers": {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            },
        },
        {
            "label": "form_no_ssl_verify",
            "kwargs": {
                "data": payload,
                "timeout": TIMEOUT,
                "verify": False,
                "headers": {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            },
        },
    ]

    last_success = False
    last_data: Optional[Dict] = None
    last_message = "No se pudo conectar"

    for attempt in attempts:
        label = attempt["label"]
        kwargs = dict(attempt["kwargs"])
        logger.info(f"Intentando login remoto via {label}: {url}")
        success, data, message = make_request_with_retry(
            method='POST',
            url=url,
            **kwargs
        )

        last_success, last_data, last_message = success, data, message
        if success:
            return success, data, message

        text = str(message or "")
        if "401" in text or "inválidas" in text.lower() or "invalidas" in text.lower():
            return success, data, message

    return last_success, last_data, last_message


def make_request_with_retry(
    method: str,
    url: str,
    max_retries: int = MAX_RETRIES,
    timeout: int = TIMEOUT,
    **kwargs
) -> Tuple[bool, Optional[Dict], str]:
    """
    Realiza una solicitud HTTP con reintentos exponenciales.
    
    Args:
        method: GET, POST, PUT, DELETE, etc
        url: URL de la solicitud
        max_retries: Número máximo de reintentos
        timeout: Timeout en segundos
        **kwargs: Argumentos adicionales para requests (json, headers, params, etc)
    
    Returns:
        (success, data, message)
    """
    # Validar URL
    if not validate_api_url(url):
        return False, None, "URL inválida"
    
    # Validar payload si existe
    if 'json' in kwargs and not validate_payload(kwargs['json']):
        return False, None, "Payload inválido"
    
    attempt = 0
    last_error = None
    
    while attempt <= max_retries:
        try:
            logger.debug(f"[Intento {attempt + 1}/{max_retries + 1}] {method} {url}")
            
            # Realizar solicitud
            response = requests.request(
                method,
                url,
                timeout=timeout,
                **kwargs
            )
            
            # Validar código de respuesta
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"[OK] {method} {url} - 200 OK")
                    return True, data, "Éxito"
                except json.JSONDecodeError as e:
                    logger.warning(f"Respuesta 200 no JSON en {url}")
                    raw_text = str(response.text or "")
                    raw_payload: Dict[str, Any] = {"_raw_text": raw_text}
                    return False, raw_payload, f"Respuesta no JSON: {str(e)}"
            
            response_data: Optional[Dict] = None
            response_detail = ""
            try:
                parsed_json = response.json()
                if isinstance(parsed_json, dict):
                    response_data = parsed_json
                    response_detail = str(
                        parsed_json.get("error")
                        or parsed_json.get("message")
                        or ""
                    ).strip()
            except Exception:
                response_data = None

            if not response_detail:
                body_preview = str(response.text or "").strip().replace("\r", " ").replace("\n", " ")
                if body_preview:
                    response_detail = body_preview[:200]

            status_msg = f"Error {response.status_code}: {response.reason}"
            if response_detail:
                status_msg = f"{status_msg} - {response_detail}"

            if response.status_code in RECOVERABLE_CODES:
                last_error = status_msg
                logger.warning(f"Error recuperable: {last_error}")
                
                # Reintentar
                if attempt < max_retries:
                    wait_time = RETRY_DELAY * (BACKOFF_FACTOR ** attempt)
                    logger.info(f"Esperando {wait_time}s antes de reintentar...")
                    time.sleep(wait_time)
                    attempt += 1
                    continue
                else:
                    return False, response_data, last_error

            # 404 on download_device_snapshot is expected if no snapshot exists yet.
            if response.status_code == 404 and "download_device_snapshot.php" in url:
                if _is_missing_snapshot_message(status_msg):
                    logger.debug(f"Snapshot aun no disponible: {status_msg}")
                    return False, response_data, status_msg

            logger.error(status_msg)
            return False, response_data, status_msg
        
        except requests.exceptions.Timeout as e:
            last_error = f"Timeout ({timeout}s)"
            logger.warning(f"Timeout en intento {attempt + 1}")
            
            if attempt < max_retries:
                wait_time = RETRY_DELAY * (BACKOFF_FACTOR ** attempt)
                logger.info(f"Esperando {wait_time}s antes de reintentar...")
                time.sleep(wait_time)
                attempt += 1
                continue
            else:
                return False, None, last_error
        
        except requests.exceptions.ConnectionError as e:
            last_error = "Error de conexión"
            logger.warning(f"Error de conexión: {e}")
            
            if attempt < max_retries:
                wait_time = RETRY_DELAY * (BACKOFF_FACTOR ** attempt)
                logger.info(f"Esperando {wait_time}s antes de reintentar...")
                time.sleep(wait_time)
                attempt += 1
                continue
            else:
                return False, None, last_error
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en solicitud: {e}")
            return False, None, str(e)
        
        except Exception as e:
            logger.exception(f"Error inesperado: {e}")
            return False, None, f"Error inesperado: {str(e)}"
    
    return False, None, last_error or "Fallos en todos los reintentos"


def get_request(
    url: str,
    timeout: int = TIMEOUT,
    **kwargs
) -> Tuple[bool, Optional[Dict], str]:
    """Realiza GET con reintentos."""
    return make_request_with_retry('GET', url, timeout=timeout, **kwargs)


def post_request(
    url: str,
    data: Dict,
    timeout: int = TIMEOUT,
    **kwargs
) -> Tuple[bool, Optional[Dict], str]:
    """Realiza POST con reintentos."""
    if not validate_payload(data):
        return False, None, "Datos inválidos"
    return make_request_with_retry('POST', url, json=data, timeout=timeout, **kwargs)


def put_request(
    url: str,
    data: Dict,
    timeout: int = TIMEOUT,
    **kwargs
) -> Tuple[bool, Optional[Dict], str]:
    """Realiza PUT con reintentos."""
    if not validate_payload(data):
        return False, None, "Datos inválidos"
    return make_request_with_retry('PUT', url, json=data, timeout=timeout, **kwargs)


def delete_request(
    url: str,
    timeout: int = TIMEOUT,
    **kwargs
) -> Tuple[bool, Optional[Dict], str]:
    """Realiza DELETE con reintentos."""
    return make_request_with_retry('DELETE', url, timeout=timeout, **kwargs)



SYNC_CHILD_DEVICES_ENDPOINTS = [
    "https://api.yhana.cloud/win/new/sync_child_devices.php",
]


def _endpoint_requires_insecure_ssl(url: str) -> bool:
    """
    api.yhana.cloud actualmente presenta cert mismatch en algunos entornos.
    Para mantener servicio, se permite verify=False solo en ese host.
    """
    try:
        host = (urlparse(url).hostname or "").strip().lower()
        return host == "api.yhana.cloud"
    except Exception:
        return False


def _post_sync_child_devices(payload: Dict[str, Any], timeout: int) -> Tuple[bool, Optional[Dict], str]:
    """Intenta endpoint nuevo y cae al anterior si falla; evita ruido de logs por 500 temporales."""
    last_data: Optional[Dict] = None
    last_message = "Error desconocido"

    for idx, endpoint in enumerate(SYNC_CHILD_DEVICES_ENDPOINTS):
        try:
            verify_ssl = not _endpoint_requires_insecure_ssl(endpoint)
            response = requests.post(endpoint, json=payload, timeout=timeout, verify=verify_ssl)
        except requests.exceptions.RequestException as e:
            last_message = f"Error de conexion: {e}"
            if idx < len(SYNC_CHILD_DEVICES_ENDPOINTS) - 1:
                logger.debug(
                    f"sync_child_devices fallback desde {endpoint}: {last_message}"
                )
            continue

        data: Optional[Dict] = None
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                data = parsed
                last_data = data
        except Exception:
            data = None

        if response.status_code == 200:
            return True, data, "Exito"

        last_message = f"Error {response.status_code}: {response.reason}"
        if idx < len(SYNC_CHILD_DEVICES_ENDPOINTS) - 1:
            logger.debug(
                f"sync_child_devices fallback desde {endpoint}: {last_message}"
            )

    return False, last_data, last_message


NEW_SNAPSHOT_ENDPOINT_BASES = [
    "https://api.yhana.cloud/win/new",
]

# Si un endpoint devuelve errores de infraestructura (500/SSL), se pausa temporalmente
# para evitar reintentos ruidosos en cada dataset.
_NEW_ENDPOINT_FAIL_UNTIL: Dict[str, float] = {}
_NEW_ENDPOINT_COOLDOWN_SECONDS = 180

DATOS_OPTICA_ENDPOINTS = [
    "https://api.yhana.cloud/win/datos.php",
]

PRODUCTOS_ENDPOINT = "https://api.yhana.cloud/win/get_productos.php"
KARDEX_ENDPOINT = "https://api.yhana.cloud/win/kardex.php"


def _new_endpoints_have_fallback() -> bool:
    """Solo aplicar cooldown si hay al menos 2 endpoints para fallback real."""
    return len(NEW_SNAPSHOT_ENDPOINT_BASES) > 1


def _endpoint_temporarily_disabled(base: str) -> bool:
    if not _new_endpoints_have_fallback():
        return False
    until = float(_NEW_ENDPOINT_FAIL_UNTIL.get(base, 0.0) or 0.0)
    return time.time() < until


def _register_endpoint_failure(base: str, message: str) -> None:
    if not _new_endpoints_have_fallback():
        return
    msg = str(message or "").lower()
    should_cooldown = any(token in msg for token in (
        "error 500",
        "error 502",
        "error 503",
        "error 504",
        "certificate verify failed",
        "ssl",
    ))
    if not should_cooldown:
        return

    _NEW_ENDPOINT_FAIL_UNTIL[base] = time.time() + _NEW_ENDPOINT_COOLDOWN_SECONDS
    logger.warning(
        f"Endpoint temporalmente pausado por {_NEW_ENDPOINT_COOLDOWN_SECONDS}s: {base} ({message})"
    )


def _post_datos_optica_endpoint(payload: Dict[str, Any], timeout: int) -> Tuple[bool, Optional[Dict], str]:
    last_data: Optional[Dict] = None
    last_message = "Error desconocido"

    for endpoint in DATOS_OPTICA_ENDPOINTS:
        try:
            verify_ssl = not _endpoint_requires_insecure_ssl(endpoint)
            success, data, message = post_request(
                endpoint,
                payload,
                timeout=timeout,
                verify=verify_ssl,
            )
            last_data = data
            last_message = message
            if success:
                return True, data, message
        except Exception as e:
            last_message = str(e)

    return False, last_data, last_message


def _invalidate_productos_cache(usuario_id: str = "", codigo_dispositivo: Optional[str] = None) -> None:
    global _CACHE_PRODUCTOS_REMOTO
    usuario_id = str(usuario_id or "").strip()
    branch_code = str(codigo_dispositivo or "").strip().upper()
    if not usuario_id:
        _CACHE_PRODUCTOS_REMOTO.clear()
        return

    cache_key = f"productos_{usuario_id}_{branch_code}"
    _CACHE_PRODUCTOS_REMOTO.pop(cache_key, None)

    if branch_code:
        _CACHE_PRODUCTOS_REMOTO.pop(f"productos_{usuario_id}_", None)


def guardar_datos_optica_remoto(
    username: str,
    datos: Dict[str, Any],
    usuario_id: str = "",
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    try:
        username = str(username or "").strip()
        usuario_id = str(usuario_id or "").strip()
        if not username and not usuario_id:
            return False, "username/usuario_id vacio", None

        payload = {
            "action": "upsert",
            "usuario_ref": username or usuario_id,
            "username": username,
            "usuario_id": usuario_id,
            "nombre_optica": str((datos or {}).get("nombre_optica", "") or "").strip(),
            "slogan": str((datos or {}).get("slogan", "") or "").strip(),
            "direccion": str((datos or {}).get("direccion", "") or "").strip(),
            "correo_electronico": str((datos or {}).get("correo_electronico", "") or "").strip(),
            "whatsapp": str((datos or {}).get("whatsapp", "") or "").strip(),
        }
        success, data, message = _post_datos_optica_endpoint(payload, timeout=max(TIMEOUT, 8))
        if success and isinstance(data, dict) and data.get("success"):
            return True, str(data.get("message", "Datos guardados")), data.get("datos")
        err = ""
        if isinstance(data, dict):
            err = str(data.get("error") or data.get("message") or "").strip()
        return False, err or message or "No se pudo guardar datos", None
    except Exception as e:
        logger.error(f"Error guardar_datos_optica_remoto: {e}")
        return False, str(e), None


def obtener_datos_optica_remoto(
    username: str = "",
    usuario_id: str = "",
) -> Tuple[bool, Dict[str, Any], str]:
    try:
        username = str(username or "").strip()
        usuario_id = str(usuario_id or "").strip()
        if not username and not usuario_id:
            return False, {}, "username/usuario_id vacio"

        payload = {
            "action": "get",
            "usuario_ref": username or usuario_id,
            "username": username,
            "usuario_id": usuario_id,
        }
        success, data, message = _post_datos_optica_endpoint(payload, timeout=max(TIMEOUT, 8))
        if success and isinstance(data, dict) and data.get("success"):
            datos = data.get("datos") if isinstance(data.get("datos"), dict) else {}
            found = bool(data.get("found"))
            return True, (datos or {}), ("OK" if found else "NOT_FOUND")
        err = ""
        if isinstance(data, dict):
            err = str(data.get("error") or data.get("message") or "").strip()
        return False, {}, err or message or "No se pudo obtener datos"
    except Exception as e:
        logger.error(f"Error obtener_datos_optica_remoto: {e}")
        return False, {}, str(e)


def _extract_expected_datasets_from_payload(payload: Dict[str, Any]) -> List[str]:
    datasets: List[str] = []

    ds = str(payload.get("dataset") or "").strip().lower()
    if ds:
        datasets.append(ds)

    snapshot = payload.get("snapshot")
    if isinstance(snapshot, dict):
        for key, value in snapshot.items():
            # Formato 1: {"clientes":[...]}
            if not (isinstance(value, dict) and "dataset" in value):
                name = str(key or "").strip().lower()
                if name:
                    datasets.append(name)
                continue

            # Formato 2: {"item":{"dataset":"clientes","data":[...]}}
            name = str(value.get("dataset") or "").strip().lower()
            if name:
                datasets.append(name)

    # Deduplicar preservando orden
    unique: List[str] = []
    seen = set()
    for name in datasets:
        if name in seen:
            continue
        seen.add(name)
        unique.append(name)
    return unique


def _verify_uploaded_datasets_exist(payload: Dict[str, Any], timeout: int) -> Tuple[bool, str]:
    """
    Verifica en nube que los datasets enviados existan realmente.
    Se usa cuando el backend responde HTTP 200 sin JSON.
    """
    usuario_madre = str(payload.get("usuario_madre") or payload.get("username") or "").strip()
    codigo_dispositivo = str(payload.get("codigo_dispositivo") or "").strip().upper()
    if not usuario_madre or not codigo_dispositivo:
        return False, "Payload sin usuario_madre/codigo_dispositivo"

    datasets = _extract_expected_datasets_from_payload(payload)
    if not datasets:
        return False, "Payload sin datasets para verificar"

    missing: List[str] = []
    verify_timeout = max(6, min(timeout, 15))
    for dataset in datasets:
        ok, data, _ = _get_new_snapshot_endpoint(
            "download_device_snapshot.php",
            {
                "usuario_madre": usuario_madre,
                "codigo_dispositivo": codigo_dispositivo,
                "dataset": dataset,
                "include_data": 0,
            },
            timeout=verify_timeout
        )
        exists = bool(ok and isinstance(data, dict) and data.get("success", True) is not False)
        if not exists:
            missing.append(dataset)

    if missing:
        return False, f"No se confirmaron en nube: {', '.join(missing)}"
    return True, "Datasets verificados en nube"


def _post_new_snapshot_endpoint(endpoint_file: str, payload: Dict[str, Any], timeout: int) -> Tuple[bool, Optional[Dict], str]:
    """POST a endpoints /win/new con fallback entre dominios."""
    endpoint_file = str(endpoint_file or "").strip().lstrip('/')
    last_data: Optional[Dict] = None
    last_message = "Error desconocido"
    attempted = False

    for idx, base in enumerate(NEW_SNAPSHOT_ENDPOINT_BASES):
        if _endpoint_temporarily_disabled(base):
            logger.debug(f"new endpoint POST omitido por cooldown: {base}")
            continue

        attempted = True
        url = f"{base}/{endpoint_file}"
        verify_ssl = not _endpoint_requires_insecure_ssl(url)
        success, data, message = post_request(url, payload, timeout=timeout, verify=verify_ssl)
        if success:
            return True, data, message

        message_text = str(message or "")
        if "respuesta no json" in message_text.lower():
            if endpoint_file.lower() in ("upload_device_snapshot.php", "upload_device_snapshot_manual.php"):
                verified, verify_msg = _verify_uploaded_datasets_exist(payload, timeout=timeout)
                if verified:
                    logger.warning(
                        f"POST {url} devolvio 200 sin JSON, pero se verifico guardado en nube."
                    )
                    synthetic_data: Dict[str, Any] = data if isinstance(data, dict) else {}
                    synthetic_data.setdefault("success", True)
                    synthetic_data.setdefault("message", "OK (200 sin JSON, verificado)")
                    return True, synthetic_data, "Exito (200 sin JSON, verificado)"

                last_message = f"HTTP 200 sin JSON y no guardo en nube: {verify_msg}"
                logger.error(last_message)
                _register_endpoint_failure(base, last_message)
                if isinstance(data, dict):
                    last_data = data
                continue

        if isinstance(data, dict):
            last_data = data
        last_message = message_text or "Error desconocido"
        _register_endpoint_failure(base, last_message)

        if idx < len(NEW_SNAPSHOT_ENDPOINT_BASES) - 1:
            logger.debug(
                f"new endpoint fallback POST desde {url}: {last_message}"
            )

    if not attempted:
        return False, last_data, "Todos los endpoints /win/new estan temporalmente pausados"
    return False, last_data, last_message


def _get_new_snapshot_endpoint(endpoint_file: str, params: Dict[str, Any], timeout: int) -> Tuple[bool, Optional[Dict], str]:
    """GET a endpoints /win/new con fallback entre dominios."""
    endpoint_file = str(endpoint_file or "").strip().lstrip('/')
    last_data: Optional[Dict] = None
    last_message = "Error desconocido"
    attempted = False

    for idx, base in enumerate(NEW_SNAPSHOT_ENDPOINT_BASES):
        if _endpoint_temporarily_disabled(base):
            logger.debug(f"new endpoint GET omitido por cooldown: {base}")
            continue

        attempted = True
        url = f"{base}/{endpoint_file}"
        verify_ssl = not _endpoint_requires_insecure_ssl(url)
        success, data, message = get_request(url, params=params, timeout=timeout, verify=verify_ssl)
        if success:
            return True, data, message

        if isinstance(data, dict):
            last_data = data
        last_message = str(message or "Error desconocido")
        _register_endpoint_failure(base, last_message)

        if idx < len(NEW_SNAPSHOT_ENDPOINT_BASES) - 1:
            logger.debug(
                f"new endpoint fallback GET desde {url}: {last_message}"
            )

    if not attempted:
        return False, last_data, "Todos los endpoints /win/new estan temporalmente pausados"
    return False, last_data, last_message

def validar_clave_activacion_api(clave: str) -> Tuple[bool, str]:
    """
    Valida la clave de activación contra la API con reintentos.
    
    Args:
        clave: Clave de activación a validar
    
    Returns:
        (válida, mensaje)
    """
    if not clave or len(clave.strip()) == 0:
        logger.warning("Clave de activación vacía")
        return False, "Clave vacía"
    
    api_url = "https://api.yhana.cloud/api/win/validar_clave.php"
    payload = {"clave": clave.strip()}
    
    # Mostrar en consola qué clave se está verificando
    print(f"[VERIFICANDO] Clave de activación: {clave.strip()}")
    logger.info(f"Validando clave de activación...")
    success, data, message = post_request(api_url, payload, timeout=15)
    
    if success and data:
        if data.get("success") is True:
            print(f"[ÉXITO] ✓ Clave de activación validada correctamente")
            logger.info("✓ Clave de activación validada")
            return True, "Clave válida"
        else:
            error_msg = data.get('message', 'Clave no válida')
            print(f"[ERROR] ✗ Validación fallida: {error_msg}")
            logger.warning(f"Clave rechazada: {error_msg}")
            return False, error_msg
    else:
        print(f"[ERROR] ✗ Error validando clave: {message}")
        logger.error(f"Error validando clave: {message}")
        return False, f"Error: {message}"


def obtener_detalles_licencia(clave: str) -> Tuple[bool, dict, str]:
    """
    Obtiene los detalles completos de una licencia (incluye fecha vencimiento, tipo, etc).
    
    Args:
        clave: Clave de activación
        
    Returns:
        (éxito, datos_licencia, mensaje)
    """
    if not clave or len(clave.strip()) == 0:
        logger.warning("Clave de licencia vacía")
        return False, {}, "Clave vacía"
    
    api_url = "https://api.yhana.cloud/api/win/validar_clave.php"
    payload = {"clave": clave.strip()}
    
    logger.info(f"Obteniendo detalles de licencia...")
    success, data, message = post_request(api_url, payload, timeout=15)
    
    if success and data:
        if data.get("success") is True:
            logger.info(f"✓ Licencia válida - Vence: {data.get('fecha_vencimiento', 'N/A')}")
            return True, data, "Licencia válida"
        else:
            error_msg = data.get('message', 'No se pudo obtener detalles')
            logger.warning(f"Error obteniendo detalles: {error_msg}")
            return False, {}, error_msg
    else:
        logger.error(f"Error obteniendo detalles: {message}")
        return False, {}, f"Error: {message}"


def crear_prueba_gratis(usuario_id: str, email: str = "", nombre_optica: str = "") -> Tuple[bool, str, str]:
    """
    Crea una prueba gratuita de 1 mes para un nuevo usuario.
    
    Args:
        usuario_id: ID del usuario
        email: Email del usuario (opcional)
        nombre_optica: Nombre de la óptica (opcional)
        
    Returns:
        (éxito, clave_prueba, mensaje)
    """
    if not usuario_id:
        logger.warning("ID de usuario vacío para crear prueba gratis")
        return False, "", "ID de usuario requerido"
    
    api_url = "https://api.yhana.cloud/api/win/crear_clave.php"
    payload = {
        "usuario_id": usuario_id.strip(),
        "tipo": "prueba",
        "dias_duracion": 30,
        "descripcion": "Prueba gratuita de 1 mes",
        "admin_token": os.getenv("VISO_ADMIN_TOKEN", ""),
        "email": email.strip() if email else "",
        "nombre_optica": nombre_optica.strip() if nombre_optica else ""
    }
    
    logger.info(f"Creando prueba gratuita para usuario {usuario_id}...")
    success, data, message = post_request(api_url, payload, timeout=15)
    
    if success and data:
        if data.get("success") is True:
            clave_prueba = data.get('clave', '')
            valida_hasta = data.get('expira', 'N/A')
            logger.info(f"✓ Prueba gratis creada - Vence: {valida_hasta}")
            return True, clave_prueba, f"Prueba activada hasta {valida_hasta}"
        else:
            error_msg = data.get('message', 'No se pudo crear prueba')
            logger.warning(f"Error creando prueba: {error_msg}")
            return False, "", error_msg
    else:
        logger.error(f"Error creando prueba: {message}")
        return False, "", f"Error: {message}"


def extender_licencia(clave: str, dias_adicionales: int = 30) -> Tuple[bool, str]:
    """
    Extiende el período de una licencia existente.
    
    Args:
        clave: Clave de activación
        dias_adicionales: Días a agregar (default 30)
        
    Returns:
        (éxito, mensaje)
    """
    if not clave or len(clave.strip()) == 0:
        logger.warning("Clave vacía para extender licencia")
        return False, "Clave vacía"
    
    if dias_adicionales <= 0:
        logger.warning("Días adicionales inválido")
        return False, "Días adicionales debe ser > 0"
    
    api_url = "https://api.yhana.cloud/api/win/extender_licencia.php"
    payload = {
        "clave": clave.strip(),
        "dias_adicionales": dias_adicionales
    }
    
    logger.info(f"Extendiendo licencia {dias_adicionales} días...")
    success, data, message = post_request(api_url, payload, timeout=15)
    
    if success and data:
        if data.get("success") is True:
            nueva_fecha = data.get('nueva_fecha_vencimiento', 'N/A')
            logger.info(f"✓ Licencia extendida - Nueva fecha: {nueva_fecha}")
            return True, f"Licencia extendida hasta {nueva_fecha}"
        else:
            error_msg = data.get('message', 'No se pudo extender')
            logger.warning(f"Error extendiendo licencia: {error_msg}")
            return False, error_msg
    else:
        logger.error(f"Error extendiendo licencia: {message}")
        return False, f"Error: {message}"


def verificar_dias_restantes(clave: str) -> Tuple[bool, int, str]:
    """
    Verifica cuántos días quedan en una licencia.
    
    Args:
        clave: Clave de activación
        
    Returns:
        (válida, dias_restantes, mensaje)
    """
    if not clave or len(clave.strip()) == 0:
        logger.warning("Clave vacía para verificar días")
        return False, 0, "Clave vacía"
    
    success, datos, mensaje = obtener_detalles_licencia(clave)
    
    if success:
        dias_restantes = datos.get('dias_restantes', 0)
        logger.info(f"Días restantes: {dias_restantes}")
        return True, dias_restantes, mensaje
    else:
        return False, 0, mensaje


def registrar_usuario_remoto(
    id_usuario: str,
    username: str,
    password: str,
    email: str = "",
    nombre_optica: str = "",
    telefono: str = "",
    ciudad: str = ""
) -> Tuple[bool, str, str]:
    """
    Registra un nuevo usuario en la base de datos remota (api.yhana.cloud/win/login.php).
    
    Args:
        id_usuario: ID de 9 dígitos
        username: Nombre de usuario
        password: Contraseña
        email: Email (opcional)
        nombre_optica: Nombre de la óptica (opcional)
        telefono: Teléfono (opcional)
        ciudad: Ciudad (opcional)
        
    Returns:
        (éxito, id_usuario_registrado, mensaje)
    """
    if not id_usuario or not username or not password:
        logger.warning("Campos requeridos faltando en registro remoto")
        return False, "", "ID, username y password son requeridos"
    
    if not id_usuario.isdigit() or len(id_usuario) != 9:
        logger.warning(f"ID inválido: {id_usuario}")
        return False, "", "El ID debe ser exactamente 9 dígitos"
    
    if len(username) < 3:
        logger.warning(f"Username muy corto: {username}")
        return False, "", "El username debe tener al menos 3 caracteres"
    
    if len(password) < 6:
        logger.warning("Contraseña muy corta")
        return False, "", "La contraseña debe tener al menos 6 caracteres"
    
    api_url = "https://api.yhana.cloud/win/login.php"
    payload = {
        "id_usuario": id_usuario.strip(),
        "username": username.strip(),
        "password": password.strip(),
        "email": email.strip() if email else "",
        "nombre_optica": nombre_optica.strip() if nombre_optica else "",
        "telefono": telefono.strip() if telefono else "",
        "ciudad": ciudad.strip() if ciudad else ""
    }
    
    logger.info(f"Registrando usuario remoto: {id_usuario}")
    success, data, message = post_request(api_url, payload, timeout=15)
    
    if success and data:
        if data.get("id_usuario"):
            logger.info(f"✓ Usuario registrado en servidor remoto: {id_usuario}")
            return True, data.get("id_usuario"), "Usuario registrado en api.yhana.cloud"
        else:
            error_msg = data.get('error', message)
            logger.warning(f"Error en respuesta: {error_msg}")
            return False, "", error_msg
    else:
        # 409 = usuario ya existe (puede ser esperado si se registró localmente primero)
        if "409" in message or "ya existe" in message.lower():
            logger.info(f"Usuario ya existe en servidor: {id_usuario}")
            return True, id_usuario, "Usuario ya existe en el servidor"
        
        logger.error(f"Error registrando usuario remoto: {message}")
        return False, "", f"Error al registrar: {message}"


def login_remoto(username: str, password: str) -> Tuple[bool, str, str, Dict[str, Any]]:
    """
    Autentica al usuario contra el servidor remoto (api.yhana.cloud).
    
    Args:
        username: Nombre de usuario
        password: Contraseña
        
    Returns:
        (éxito, id_usuario, mensaje, datos_licencia)
    """
    if not username or not password:
        return False, "", "Username y password requeridos", {}
    
    # Endpoint centralizado para login/licencia
    url = _get_license_config(
        'LICENSE_CHECK_API_URL',
        "https://api.yhana.cloud/win/login.php"
    )
    payload = {
        "username": username.strip(),
        "password": password.strip()
    }
    
    logger.info(f"Intentando login remoto: {username}")
    
    success, data, message = _attempt_login_request(url, payload)

    # Fallback ante problemas de SSL/certificado en api.yhana.cloud.
    ssl_markers = (
        "CERTIFICATE_VERIFY_FAILED",
        "certificate verify failed",
        "hostname mismatch",
        "WRONG_PRINCIPAL",
        "SSL:"
    )
    possible_ssl_issue = (
        (not success) and (
            "error de conex" in str(message).lower()
            or any(marker in str(message) for marker in ssl_markers)
        )
    )
    if possible_ssl_issue:
        logger.warning(
            "Posible error SSL en api.yhana.cloud; reintentando sin verificacion SSL de forma temporal"
        )
        success, data, message = make_request_with_retry(
            method='POST',
            url=url,
            data=payload,
            timeout=TIMEOUT,
            verify=False,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
        )

    # Inicializar datos de licencia por defecto
    datos_licencia = {
        'tiene_licencia': False,
        'licencia_vigente': False,
        'plan_type': 'Gratis',
        'fecha_vencimiento': None,
        'dias_restantes': 0
    }
    
    if success and data:
        # Buscar id_usuario (puede venir como 'id_usuario', 'id', o 'dni')
        id_usuario = data.get("id_usuario") or data.get("id") or data.get("dni")
        
        if data.get("success") and id_usuario:
            # Extraer información de licencia si viene en la respuesta
            if 'tiene_licencia' in data:
                datos_licencia['tiene_licencia'] = data.get('tiene_licencia', False)
                datos_licencia['licencia_vigente'] = data.get('licencia_vigente', False)
                datos_licencia['plan_type'] = data.get('plan_type', 'Gratis')
                datos_licencia['fecha_vencimiento'] = data.get('fecha_vencimiento')
                datos_licencia['dias_restantes'] = data.get('dias_restantes', 0)
            
            logger.info(f"✓ Login exitoso en servidor remoto: {username} (ID: {id_usuario})")
            return True, str(id_usuario), "Login exitoso", datos_licencia
        else:
            error_msg = data.get('error', 'Error en login')
            logger.warning(f"Error en login: {error_msg}")
            return False, "", error_msg, {}
    else:
        if "401" in message or "inválidas" in message.lower():
            logger.warning(f"Credenciales inválidas para: {username}")
            return False, "", "Credenciales inválidas", {}
        
        logger.error(f"Error login remoto: {message}")
        
        allow_offline = bool(_get_license_config('ALLOW_OFFLINE_FALLBACK', False))
        server_error = str(message or "")
        is_server_failure = any(code in server_error for code in ("500", "502", "503", "504"))

        if allow_offline and is_server_failure:
            offline_ok, local_user_id = _resolve_local_offline_login(username, password)
            if offline_ok:
                logger.warning(
                    "Servidor no disponible; usando login offline con credenciales locales verificadas."
                )
                return True, local_user_id, "Login offline local", {
                    'tiene_licencia': True,
                    'licencia_vigente': True,
                    'plan_type': 'Offline',
                    'fecha_vencimiento': '2099-12-31',
                    'dias_restantes': 999
                }
            
        return False, "", f"Error al conectar: {message}", {}


def guardar_paciente_remoto(id_usuario: str, dni: str, nombre: str, 
                            fecha_nacimiento: Optional[str] = None,
                            genero: Optional[str] = None,
                            edad: Optional[int] = None) -> Tuple[bool, str]:
    """
    Sincroniza paciente a BD remota en api.yhana.cloud/api/win/patients_upload.php
    
    Args:
        id_usuario: Username del usuario propietario del paciente (NO DNI)
        dni: DNI del paciente
        nombre: Nombre completo del paciente
        fecha_nacimiento: Fecha en formato YYYY-MM-DD (opcional)
        genero: "M", "F", "Masculino", "Femenino" (se convierte a M/F) (opcional)
        edad: Edad del paciente (opcional)
    
    Returns:
        Tuple[bool, str]: (éxito, mensaje)
    """
    if not id_usuario or not dni or not nombre:
        logger.warning("Faltan datos requeridos para guardar paciente")
        return False, "Faltan datos: id_usuario, dni, nombre"
    
    url = "https://api.yhana.cloud/api/win/patients_upload.php"
    payload = {
        "id_usuario": id_usuario.strip(),  # Será el username del usuario
        "dni": dni.strip(),
        "nombre": nombre.strip(),
    }
    
    # Convertir género a formato estándar M/F
    if genero:
        genero_normalized = genero.strip()
        # Si viene como "Masculino" o "Femenino", convertir a M/F
        if genero_normalized.lower().startswith('m'):
            genero_normalized = 'M'
        elif genero_normalized.lower().startswith('f'):
            genero_normalized = 'F'
        payload["genero"] = genero_normalized
    
    # Añadir campos opcionales si están presentes
    if fecha_nacimiento:
        payload["fecha_nacimiento"] = fecha_nacimiento.strip()
    if edad:
        payload["edad"] = int(edad)
    
    logger.info(f"Sincronizando paciente: {dni} ({nombre}) de usuario {id_usuario}")
    logger.debug(f"Payload enviado: {payload}")
    
    success, data, message = make_request_with_retry(
        method='POST',
        url=url,
        json=payload,
        timeout=TIMEOUT
    )
    
    if success and data:
        operacion = data.get("operacion", "?")
        msg = data.get("mensaje", "Paciente sincronizado")
        logger.info(f"✓ Paciente {operacion}: {dni} en servidor remoto")
        return True, msg
    else:
        logger.error(f"Error al sincronizar paciente {dni}: {message}")
        return False, f"Error: {message}"


def verificar_estado_licencia(username: str = None, id_usuario: int = None, timeout: int = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Verifica el estado de la licencia/clave de activación del usuario
    usando el endpoint check_user_license.php
    
    Args:
        username: Nombre de usuario
        id_usuario: ID del usuario (DNI)
        timeout: Timeout en segundos (por defecto usa TIMEOUT global)
    
    Returns:
        Tuple[bool, dict]: (es_exitosa_la_peticion, datos_de_respuesta)
        
    Datos de respuesta:
        - tiene_licencia: bool - Si el usuario tiene una licencia asignada
        - licencia_vigente: bool - Si la licencia no ha vencido
        - plan_type: str - Tipo de plan (Permanente, Mensual, Semanal, etc)
        - fecha_vencimiento: str - Fecha de vencimiento
        - dias_restantes: int - Días restantes (negativo si expiró)
    """
    
    if not username and not id_usuario:
        logger.error("Se requiere username o id_usuario para verificar licencia")
        return False, {
            'tiene_licencia': False,
            'licencia_vigente': False,
            'plan_type': 'Gratis'
        }
    
    # Usar timeout personalizado o el global
    if timeout is None:
        timeout = TIMEOUT
    
    try:
        # BYPASS TEMPORAL DE SEGURIDAD (Solicitado por usuario)
        # Si se permite offline, asumimos éxito inmediato para evitar bloqueos por servidor caído
        allow_offline = bool(_get_license_config('ALLOW_OFFLINE_FALLBACK', True))
        if allow_offline:
            logger.warning("BYPASS: Saltando verificación remota de licencia para evitar bloqueo por error 500.")
            return True, {
                'tiene_licencia': True,
                'licencia_vigente': True,
                'plan_type': 'Premium (Offline)',
                'vigencia': '2099-12-31',
                'dias_restantes': 9999,
                'active': True
            }

        # URL del nuevo endpoint de verificación
        url = "https://api.yhana.cloud/api/win/check_user_license.php"
        
        payload = {}
        if username:
            payload['username'] = username.strip()
        if id_usuario:
            payload['dni'] = id_usuario
        
        logger.info(f"Verificando licencia via check_user_license.php para: {username or id_usuario}")
        
        # Hacer POST request con parámetros en el body
        success, data, message = make_request_with_retry(
            method='POST',
            url=url,
            json=payload,
            timeout=timeout
        )
        
        if success and data:
            tiene_licencia = data.get('tiene_licencia', False)
            licencia_vigente = data.get('licencia_vigente', False)
            plan_type = data.get('plan_type', 'Gratis')
            dias = data.get('dias_restantes', 0)
            vigencia = data.get('fecha_vencimiento', 'Desconocida')
            
            if tiene_licencia and licencia_vigente:
                # Calcular días, horas y minutos restantes
                total_minutos = dias * 24 * 60
                dias_calc = total_minutos // (24 * 60)
                horas_calc = (total_minutos % (24 * 60)) // 60
                minutos_calc = total_minutos % 60
                
                tiempo_str = f"{int(dias_calc)}d {int(horas_calc)}h {int(minutos_calc)}m"
                
                # Calcular día de semana para mostrar en consola
                try:
                    from datetime import datetime
                    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                    fecha_obj = datetime.strptime(vigencia, '%Y-%m-%d %H:%M:%S')
                    dia_semana = dias_semana[fecha_obj.weekday()]
                    logger.info(f"✓ Licencia activa - Se vence {dia_semana} ({vigencia}) - Tiempo restante: {tiempo_str}")
                except:
                    logger.info(f"✓ Licencia activa - Vencimiento: {vigencia} - Tiempo restante: {tiempo_str}")
            elif tiene_licencia and not licencia_vigente:
                logger.warning(f"⚠ Licencia expirada hace {abs(dias)} días")
            else:
                logger.warning(f"⚠ Usuario sin licencia activa")
            
            return True, {
                'tiene_licencia': tiene_licencia,
                'licencia_vigente': licencia_vigente,
                'plan_type': plan_type,
                'vigencia': vigencia,
                'dias_restantes': dias,
                'active': licencia_vigente  # Para compatibilidad con código antiguo
            }
        else:
            allow_offline = bool(_get_license_config('ALLOW_OFFLINE_FALLBACK', True))
            status_match = re.match(r"^Error\s+(\d{3}):", (message or "").strip())
            status_code = int(status_match.group(1)) if status_match else None

            is_recoverable = (
                (status_code in RECOVERABLE_CODES)
                or ("timeout" in (message or "").lower())
                or ("conexión" in (message or "").lower())
                or ("conexion" in (message or "").lower())
            )

            # Si hay fallback offline, no tratar fallos recuperables como error fatal
            if allow_offline and is_recoverable:
                logger.warning(
                    f"Servidor de licencias no disponible (HTTP {status_code}). "
                    f"Continuando en modo offline. Detalle: {message}"
                )
            else:
                logger.error(f"Error verificando licencia: {message}")
            return False, {
                'tiene_licencia': False,
                'licencia_vigente': False,
                'plan_type': 'Gratis',
                'active': False
            }
            
    except Exception as e:
        logger.error(f"Excepción verificando licencia: {e}")
        return False, {
            'tiene_licencia': False,
            'licencia_vigente': False,
            'plan_type': 'Gratis',
            'active': False
        }


def update_license_dates(id_usuario: str, start_date: str, end_date: str) -> Tuple[bool, str]:
    """Actualiza las fechas de inicio y vencimiento de la licencia en el servidor remoto.
    
    Args:
        id_usuario: ID del usuario (DNI)
        start_date: Fecha de inicio (formato YYYY-MM-DD)
        end_date: Fecha de vencimiento (formato YYYY-MM-DD)
    
    Returns:
        Tupla (éxito: bool, mensaje: str)
    """
    url = "https://api.yhana.cloud/api/win/update_license_dates.php"
    payload = {
        "id_usuario": id_usuario,
        "fecha_inicio": start_date,
        "fecha_vencimiento": end_date
    }
    
    logger.info(f"Actualizando fechas de licencia para usuario: {id_usuario}")
    logger.info(f"Nuevas fechas - Inicio: {start_date}, Vencimiento: {end_date}")
    
    success, data, message = make_request_with_retry(
        method='POST',
        url=url,
        json=payload,
        timeout=TIMEOUT
    )
    
    if success:
        logger.info(f"✓ Fechas de licencia actualizadas correctamente")
        return True, message or "Fechas actualizadas correctamente"
    else:
        logger.error(f"✗ Error actualizando fechas: {message}")
        return False, message or "Error al actualizar las fechas"


def obtener_clientes_remoto(usuario_id: str, codigo_dispositivo: Optional[str] = None) -> list:
    """    Descarga la lista de clientes del usuario desde la BD remota.
    Retorna lista de clientes o [] si hay error.

    Compatibilidad: se acepta `username` (ej: "alex") y se intenta resolver a `usuario_id` numerico.
    """
    try:
        usuario_id_in = str(usuario_id or "").strip()
        usuario_id = usuario_id_in

        if usuario_id and not usuario_id.isdigit():
            # Compatibilidad: a veces se pasa username en vez de ID.
            try:
                from utils.file_handler import cargar_usuarios
                usuarios = cargar_usuarios() or {}
                for uid, info in usuarios.items():
                    if isinstance(info, dict) and str(info.get("username", "")).strip() == usuario_id_in:
                        usuario_id = str(uid).strip()
                        break
            except Exception:
                pass

        if not str(usuario_id or "").strip():
            return []

        url = "https://api.yhana.cloud/api/win/get_clientes.php"
        payload: Dict[str, Any] = {"usuario_id": usuario_id}
        if codigo_dispositivo:
            payload["codigo_dispositivo"] = str(codigo_dispositivo).strip().upper()

        response = requests.post(url, json=payload, timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                clientes = data.get("clientes", [])
                logger.info(f"Obtenidos {len(clientes)} clientes remotos")
                return clientes

        logger.warning(f"Error obteniendo clientes: {response.text}")
        return []

    except Exception as e:
        logger.error(f"Error descargando clientes: {e}")
        return []
def obtener_pacientes_remoto(usuario_id: str, codigo_dispositivo: Optional[str] = None) -> Optional[list]:
    """    Descarga la lista de PACIENTES con sus GRADUACIONES del usuario desde la BD remota.

    Retorna:
    - list: si la API responde success (puede ser lista vacia).
    - None: si hay error / usuario_id invalido (para no vaciar la UI por accidente).

    Compatibilidad: se acepta `username` (ej: "alex") y se intenta resolver a `usuario_id` numerico.
    """
    try:
        usuario_id_in = str(usuario_id or "").strip()
        usuario_id = usuario_id_in

        if usuario_id and not usuario_id.isdigit():
            try:
                from utils.file_handler import cargar_usuarios
                usuarios = cargar_usuarios() or {}
                for uid, info in usuarios.items():
                    if isinstance(info, dict) and str(info.get("username", "")).strip() == usuario_id_in:
                        usuario_id = str(uid).strip()
                        break
            except Exception:
                pass

        if not str(usuario_id or "").strip():
            return None

        url = "https://api.yhana.cloud/api/win/get_pacientes.php"
        params: Dict[str, Any] = {"usuario_id": usuario_id}
        if codigo_dispositivo:
            params["codigo_dispositivo"] = str(codigo_dispositivo).strip().upper()

        response = requests.get(url, params=params, timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                pacientes = data.get("pacientes", [])
                logger.info(f"Obtenidos {len(pacientes)} pacientes remotos con graduaciones")
                return pacientes

        logger.warning(f"Error obteniendo pacientes: {response.text}")
        return None

    except Exception as e:
        logger.error(f"Error descargando pacientes: {e}")
        return None
def obtener_productos_remoto(usuario_id: str, codigo_dispositivo: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Optional[list]:
    """
    Descarga la lista de PRODUCTOS con INVENTARIO del usuario desde la BD remota.
    
    OPTIMIZACIÓN: Cachea resultados por 30 segundos para reducir consumo de internet.
    """
    global _CACHE_PRODUCTOS_REMOTO
    import os
    import json as json_mod
    
    # 🔍 RESOLUCIÓN DE DNI: El servidor PHP espera el DNI numérico (ej: 71357081)
    # Si recibimos un username (ej: alex9121), lo convertimos al ID real.
    dni_para_api = str(usuario_id or "").strip()
    if dni_para_api and not dni_para_api.isdigit():
        try:
            from utils.file_handler import _resolve_usuario_id_for_sync
            dni_para_api = _resolve_usuario_id_for_sync(dni_para_api)
        except Exception:
            pass
            
    cache_suffix = str(codigo_dispositivo or "").strip().upper()
    cache_key = f"productos_{dni_para_api}_{cache_suffix}_{limit}_{offset}"
    now = time.time()
    
    # Audit log para registrar solicitud
    audit_dir = os.path.join('VISO', 'temp')
    os.makedirs(audit_dir, exist_ok=True)
    audit_file = os.path.join(audit_dir, 'api_audit.log')
    
    def log_audit(event, **kwargs):
        try:
            entry = {"ts": int(now), "event": event, "usuario_id": dni_para_api, **kwargs}
            with open(audit_file, 'a', encoding='utf-8') as f:
                f.write(json_mod.dumps(entry, ensure_ascii=False) + '\n')
        except Exception:
            pass
    
    # Verificar si hay cache válido
    if cache_key in _CACHE_PRODUCTOS_REMOTO:
        cached_data, cached_time = _CACHE_PRODUCTOS_REMOTO[cache_key]
        if now - cached_time < _CACHE_TIMEOUT:
            logger.info(f"✓ Usando cache de productos para {dni_para_api}")
            log_audit("CACHE_HIT", productos_count=len(cached_data))
            return cached_data
    
    # Cache expirado o no existe - descargar desde servidor
    try:
        url = PRODUCTOS_ENDPOINT
        # ✅ CAMBIO CRÍTICO: Usar el DNI resuelto para el parámetro 'username'
        params: Dict[str, Any] = {"username": dni_para_api}
        if codigo_dispositivo:
            params["codigo_dispositivo"] = str(codigo_dispositivo).strip().upper()
        else:
            params["solo_madre"] = "1"
            
        if limit is not None:
            params["limit"] = int(limit)
        if offset is not None:
            params["offset"] = int(offset)
        
        print(f"[API] Consultando productos para ID: {dni_para_api} (Sucursal: {codigo_dispositivo or 'MADRE'}) | Limit: {limit} | Offset: {offset}")
        log_audit("REQUEST_SENT", url=url, params=params)
        
        response = requests.get(url, params=params, timeout=TIMEOUT)
        
        log_audit("RESPONSE_RECEIVED", status_code=response.status_code, response_size=len(response.text))
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                productos = data.get('productos', [])
                _CACHE_PRODUCTOS_REMOTO[cache_key] = (productos, now)
                log_audit("SUCCESS", productos_count=len(productos))
                return productos
            else:
                log_audit("API_ERROR", message=data.get('message', 'sin mensaje'))
        else:
            log_audit("HTTP_ERROR", status_code=response.status_code)
    
    except Exception as e:
        log_audit("EXCEPTION", error=str(e))
        logger.error(f"Error descargando productos: {e}")
    
    return []


def guardar_producto_remoto(
    usuario_id: str,
    producto: Dict[str, Any],
    *,
    username: str = "",
    codigo_dispositivo: Optional[str] = None,
    dispositivo_nombre: str = "",
    tipo_dispositivo: str = "",
) -> Tuple[bool, str]:
    try:
        usuario_id = str(usuario_id or "").strip()
        username = str(username or "").strip()
        if not usuario_id and not username:
            return False, "usuario_id/username vacio"

        payload = {
            "action": "upsert",
            "usuario_id": usuario_id,
            "username": username,
            "codigo_dispositivo": str(codigo_dispositivo or "").strip().upper(),
            "dispositivo_nombre": str(dispositivo_nombre or "").strip(),
            "tipo_dispositivo": str(tipo_dispositivo or "").strip(),
            "producto": producto if isinstance(producto, dict) else {},
        }
        success, data, message = post_request(PRODUCTOS_ENDPOINT, payload, timeout=max(TIMEOUT, 12))
        if success and isinstance(data, dict) and data.get("success"):
            _invalidate_productos_cache(usuario_id or username, codigo_dispositivo)
            return True, str(data.get("message", "Producto guardado"))

        err = ""
        if isinstance(data, dict):
            err = str(data.get("error") or data.get("message") or "").strip()
        return False, err or message or "No se pudo guardar producto"
    except Exception as e:
        logger.error(f"Error guardar_producto_remoto: {e}")
        return False, str(e)


def reemplazar_productos_remoto(
    usuario_id: str,
    productos: List[Dict[str, Any]],
    *,
    username: str = "",
    codigo_dispositivo: Optional[str] = None,
    dispositivo_nombre: str = "",
    tipo_dispositivo: str = "",
) -> Tuple[bool, str, int]:
    try:
        usuario_id = str(usuario_id or "").strip()
        username = str(username or "").strip()
        if not usuario_id and not username:
            return False, "usuario_id/username vacio", 0

        payload = {
            "action": "replace_all",
            "usuario_id": usuario_id,
            "username": username,
            "codigo_dispositivo": str(codigo_dispositivo or "").strip().upper(),
            "dispositivo_nombre": str(dispositivo_nombre or "").strip(),
            "tipo_dispositivo": str(tipo_dispositivo or "").strip(),
            "productos": productos if isinstance(productos, list) else [],
        }
        success, data, message = post_request(PRODUCTOS_ENDPOINT, payload, timeout=max(TIMEOUT, 20))
        if success and isinstance(data, dict) and data.get("success"):
            _invalidate_productos_cache(usuario_id or username, codigo_dispositivo)
            return True, str(data.get("message", "Inventario guardado")), int(data.get("saved", 0) or 0)

        err = ""
        if isinstance(data, dict):
            err = str(data.get("error") or data.get("message") or "").strip()
        return False, err or message or "No se pudo reemplazar inventario", 0
    except Exception as e:
        logger.error(f"Error reemplazar_productos_remoto: {e}")
        return False, str(e), 0


def eliminar_producto_remoto(
    usuario_id: str,
    codigo: str,
    *,
    username: str = "",
    codigo_dispositivo: Optional[str] = None,
) -> Tuple[bool, str, int]:
    try:
        usuario_id = str(usuario_id or "").strip()
        username = str(username or "").strip()
        codigo = str(codigo or "").strip()
        if not codigo:
            return False, "codigo vacio", 0
        if not usuario_id and not username:
            return False, "usuario_id/username vacio", 0

        payload = {
            "action": "delete",
            "usuario_id": usuario_id,
            "username": username,
            "codigo": codigo,
            "codigo_dispositivo": str(codigo_dispositivo or "").strip().upper(),
        }
        success, data, message = post_request(PRODUCTOS_ENDPOINT, payload, timeout=max(TIMEOUT, 12))
        if success and isinstance(data, dict) and data.get("success"):
            _invalidate_productos_cache(usuario_id or username, codigo_dispositivo)
            return True, "Producto eliminado", int(data.get("deleted", 0) or 0)

        err = ""
        if isinstance(data, dict):
            err = str(data.get("error") or data.get("message") or "").strip()
        return False, err or message or "No se pudo eliminar producto", 0
    except Exception as e:
        logger.error(f"Error eliminar_producto_remoto: {e}")
        return False, str(e), 0


def obtener_kardex_remoto(usuario_id: str, codigo_dispositivo: Optional[str] = None) -> Optional[list]:
    try:
        usuario_ref = str(usuario_id or "").strip()
        if not usuario_ref:
            return None
        if not usuario_ref.isdigit():
            try:
                from utils.file_handler import _resolve_usuario_id_for_sync
                usuario_ref = str(_resolve_usuario_id_for_sync(usuario_ref) or "").strip()
            except Exception:
                pass
        if not usuario_ref:
            return None

        params: Dict[str, Any] = {"username": usuario_ref}
        if codigo_dispositivo:
            params["codigo_dispositivo"] = str(codigo_dispositivo).strip().upper()
        else:
            params["solo_madre"] = "1"

        response = requests.get(KARDEX_ENDPOINT, params=params, timeout=max(TIMEOUT, 12))
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                kardex = data.get("kardex", [])
                return kardex if isinstance(kardex, list) else []
        logger.warning(f"Error obteniendo kardex remoto: {response.text}")
        return []
    except Exception as e:
        logger.error(f"Error obtener_kardex_remoto: {e}")
        return None


def reemplazar_kardex_remoto(
    usuario_id: str,
    kardex: List[Dict[str, Any]],
    *,
    username: str = "",
    codigo_dispositivo: Optional[str] = None,
    dispositivo_nombre: str = "",
    tipo_dispositivo: str = "",
) -> Tuple[bool, str, int]:
    try:
        usuario_id = str(usuario_id or "").strip()
        username = str(username or "").strip()
        if not usuario_id and not username:
            return False, "usuario_id/username vacio", 0

        payload = {
            "action": "replace_all",
            "usuario_id": usuario_id,
            "username": username,
            "codigo_dispositivo": str(codigo_dispositivo or "").strip().upper(),
            "dispositivo_nombre": str(dispositivo_nombre or "").strip(),
            "tipo_dispositivo": str(tipo_dispositivo or "").strip(),
            "kardex": kardex if isinstance(kardex, list) else [],
        }
        success, data, message = post_request(KARDEX_ENDPOINT, payload, timeout=max(TIMEOUT, 20))
        if success and isinstance(data, dict) and data.get("success"):
            return True, str(data.get("message", "Kardex guardado")), int(data.get("saved", 0) or 0)

        err = ""
        if isinstance(data, dict):
            err = str(data.get("error") or data.get("message") or "").strip()
        return False, err or message or "No se pudo reemplazar kardex", 0
    except Exception as e:
        logger.error(f"Error reemplazar_kardex_remoto: {e}")
        return False, str(e), 0


def agregar_movimiento_kardex_remoto(
    usuario_id: str,
    entry: Dict[str, Any],
    *,
    username: str = "",
    codigo_dispositivo: Optional[str] = None,
    dispositivo_nombre: str = "",
    tipo_dispositivo: str = "",
) -> Tuple[bool, str]:
    try:
        usuario_id = str(usuario_id or "").strip()
        username = str(username or "").strip()
        if not usuario_id and not username:
            return False, "usuario_id/username vacio"

        payload = {
            "action": "append",
            "usuario_id": usuario_id,
            "username": username,
            "codigo_dispositivo": str(codigo_dispositivo or "").strip().upper(),
            "dispositivo_nombre": str(dispositivo_nombre or "").strip(),
            "tipo_dispositivo": str(tipo_dispositivo or "").strip(),
            "entry": entry if isinstance(entry, dict) else {},
        }
        success, data, message = post_request(KARDEX_ENDPOINT, payload, timeout=max(TIMEOUT, 15))
        if success and isinstance(data, dict) and data.get("success"):
            return True, str(data.get("message", "Movimiento kardex guardado"))

        err = ""
        if isinstance(data, dict):
            err = str(data.get("error") or data.get("message") or "").strip()
        return False, err or message or "No se pudo agregar movimiento kardex"
    except Exception as e:
        logger.error(f"Error agregar_movimiento_kardex_remoto: {e}")
        return False, str(e)


def obtener_inventario_remoto(
    usuario_id: str,
    codigo_producto: Optional[str] = None,
    codigo_dispositivo: Optional[str] = None
) -> Optional[dict]:
    """
    Descarga el INVENTARIO/STOCK de productos del usuario desde la BD remota.
    
    Args:
        usuario_id: ID del usuario
        codigo_producto: (Opcional) Código específico de producto para obtener su stock
    
    Returns:
        Dict con inventario y estadísticas (stock_total, valor_total, etc.)
        None si hay error de conexión
    """
    try:
        url = "https://api.yhana.cloud/api/win/get_inventario.php"
        params: Dict[str, Any] = {"usuario_id": usuario_id}
        
        if codigo_producto:
            params["codigo_producto"] = codigo_producto
        if codigo_dispositivo:
            params["codigo_dispositivo"] = str(codigo_dispositivo).strip().upper()
        
        response = requests.get(url, params=params, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.info(f"✓ Obtenido inventario remoto - Stock total: {data.get('stock_total', 0)}")
                return data
        
        
        logger.warning(f"Error obteniendo inventario: {response.text}")
        return {}
    
    except Exception as e:
        logger.error(f"Error descargando inventario: {e}")
        return None


def subir_imagen_producto(usuario_id: int, codigo_producto: str, ruta_imagen: str) -> Optional[dict]:
    """
    Sube la imagen de un producto al servidor.
    
    Args:
        usuario_id: ID del usuario
        codigo_producto: Código del producto
        ruta_imagen: Ruta local de la imagen a subir
    
    Returns:
        Dict con response del servidor, None si hay error
    """
    try:
        import os
        
        # Verificar que el archivo existe
        if not os.path.exists(ruta_imagen):
            logger.warning(f"Archivo de imagen no encontrado: {ruta_imagen}")
            return None
        
        url = "https://api.yhana.cloud/api/win/upload_product_image.php"
        
        # Preparar datos
        with open(ruta_imagen, 'rb') as f:
            files = {
                'imagen': (os.path.basename(ruta_imagen), f, 'image/jpeg')
            }
            data = {
                'usuario_id': usuario_id,
                'codigo_producto': codigo_producto
            }
            
            response = requests.post(url, files=files, data=data, timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                logger.info(f"✓ Imagen de producto {codigo_producto} subida correctamente")
                return result
        
        logger.warning(f"Error subiendo imagen: {response.text}")
        return None
    
    except Exception as e:
        logger.error(f"Error subiendo imagen de producto: {e}")
        return None


def subir_imagenes_productos(usuario_id: int, productos: list) -> dict:
    """
    Sube imágenes de múltiples productos al servidor.
    
    OPTIMIZACIÓN: Solo sube imágenes que realmente cambiaron
    (no re-sube cada 60 segundos si nada cambió).
    
    Retorna estadísticas de carga.
    
    Args:
        usuario_id: ID del usuario
        productos: Lista de dicts con al menos 'codigo' e 'image_path'
    
    Returns:
        Dict con {subidas: int, errores: int, pendientes: int}
    """
    global _UPLOADED_IMAGES
    
    try:
        stats = {
            'subidas': 0,
            'errores': 0,
            'pendientes': 0,
            'skipped': 0  # Salteadas porque ya estaban subidas
        }
        
        for producto in productos:
            codigo = producto.get('codigo')
            image_path = producto.get('image_path')
            
            # Validar que tenga código e imagen
            if not codigo or not image_path:
                stats['pendientes'] += 1
                continue
            
            # Verificar si ya fue subida recientemente (últimos 5 minutos)
            now = time.time()
            if codigo in _UPLOADED_IMAGES:
                last_upload_time = _UPLOADED_IMAGES[codigo]
                if now - last_upload_time < 300:  # 5 minutos
                    # Ya se subió hace poco, saltar
                    stats['skipped'] += 1
                    continue
            
            # Intentar subir (realmente nueva o pasaron 5+ minutos)
            result = subir_imagen_producto(usuario_id, codigo, image_path)
            
            if result:
                stats['subidas'] += 1
                _UPLOADED_IMAGES[codigo] = now  # Marcar como subida
            else:
                stats['errores'] += 1
        
        if stats['subidas'] > 0 or stats['errores'] > 0:
            logger.info(f"Upload imágenes: {stats['subidas']} subidas, {stats['errores']} errores, {stats['skipped']} saltadas")
        
        return stats
    
    except Exception as e:
        logger.error(f"Error en subir_imagenes_productos: {e}")
        return {'subidas': 0, 'errores': len(productos), 'pendientes': 0}


def guardar_productos_local(username: str, productos: list) -> bool:
    """
    Guarda productos en almacenamiento local (JSON).
    Usado por InventoryAutoSyncWorker para cachear productos obtenidos de BD remota.
    
    Args:
        username: Usuario actual
        productos: Lista de productos desde BD remota
    
    Returns:
        True si se guardó correctamente
    """
    try:
        from utils.file_handler import guardar_productos
        guardar_productos(username, productos)
        return True
    except Exception as e:
        logger.error(f"Error guardando productos localmente: {e}")
        return False


def sync_dispositivo_hijo_remoto(usuario_madre: str, dispositivo: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Crea/actualiza un dispositivo hijo en la nube (MySQL + PHP endpoint).

    Returns:
        (ok, mensaje, dispositivo_remoto)
    """
    try:
        if not usuario_madre:
            return False, "usuario_madre vacío", None

        if not isinstance(dispositivo, dict) or not dispositivo:
            return False, "Dispositivo inválido", None

        url = "https://api.yhana.cloud/win/new/sync_child_devices.php"
        payload = {
            "action": "upsert",
            "usuario_madre": usuario_madre,
            "id": dispositivo.get("id"),
            "nombre_optica": dispositivo.get("nombre_optica", ""),
            "ciudad": dispositivo.get("ciudad", ""),
            "codigo_dispositivo": str(dispositivo.get("codigo_dispositivo", "")).upper(),
            "estado": dispositivo.get("estado", "activo"),
            "cloud_sync_enabled": bool(dispositivo.get("cloud_sync_enabled", True)),
            "ultima_sincronizacion": dispositivo.get("ultima_sincronizacion"),
            "created_at": dispositivo.get("created_at"),
            "updated_at": dispositivo.get("updated_at"),
        }

        success, data, message = _post_sync_child_devices(payload, timeout=max(TIMEOUT, 8))
        if success and data and data.get("success"):
            return True, data.get("message", "Sincronizado"), data.get("dispositivo")

        server_error = ""
        if isinstance(data, dict):
            server_error = data.get("error") or data.get("message") or ""
        return False, server_error or message or "No se pudo sincronizar", None
    except Exception as e:
        logger.error(f"Error sync_dispositivo_hijo_remoto: {e}")
        return False, str(e), None


def eliminar_dispositivo_hijo_remoto(
    usuario_madre: str,
    device_id: Optional[str] = None,
    codigo_dispositivo: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Elimina un dispositivo hijo en la nube por id o código.
    """
    try:
        if not usuario_madre:
            return False, "usuario_madre vacío"
        if not device_id and not codigo_dispositivo:
            return False, "Debe enviar device_id o codigo_dispositivo"

        url = "https://api.yhana.cloud/win/new/sync_child_devices.php"
        payload: Dict[str, Any] = {
            "action": "delete",
            "usuario_madre": usuario_madre,
        }
        if device_id:
            payload["id"] = device_id
        if codigo_dispositivo:
            payload["codigo_dispositivo"] = str(codigo_dispositivo).upper()

        success, data, message = _post_sync_child_devices(payload, timeout=max(TIMEOUT, 8))
        if success and data and data.get("success"):
            base_msg = str(data.get("message", "Eliminado en nube"))
            snap_msg = str(data.get("snapshot_message", "") or "").strip()
            if snap_msg:
                base_msg = f"{base_msg} | Snapshot: {snap_msg}"
            return True, base_msg

        server_error = ""
        if isinstance(data, dict):
            server_error = data.get("error") or data.get("message") or ""
        return False, server_error or message or "No se pudo eliminar en nube"
    except Exception as e:
        logger.error(f"Error eliminar_dispositivo_hijo_remoto: {e}")
        return False, str(e)


def validar_codigo_dispositivo_hijo_remoto(
    usuario_madre: str,
    codigo_dispositivo: str
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Valida si un código de dispositivo hijo existe en nube y pertenece al usuario madre.

    Returns:
        (es_valido, dispositivo, mensaje)
    """
    try:
        usuario_madre = str(usuario_madre or "").strip()
        codigo_dispositivo = str(codigo_dispositivo or "").strip().upper()

        if not usuario_madre or not codigo_dispositivo:
            return False, None, "Faltan datos para validar el código"

        url = "https://api.yhana.cloud/win/new/sync_child_devices.php"
        payload = {
            "action": "validate",
            "usuario_madre": usuario_madre,
            "codigo_dispositivo": codigo_dispositivo
        }

        success, data, message = _post_sync_child_devices(payload, timeout=max(TIMEOUT, 8))
        if success and data and data.get("success"):
            if data.get("found"):
                dispositivo = data.get("dispositivo") or {}
                return True, dispositivo, data.get("message", "Código válido")
            return False, None, data.get("message", "Código no encontrado")

        server_error = ""
        if isinstance(data, dict):
            server_error = data.get("error") or data.get("message") or ""
        return False, None, server_error or message or "No se pudo validar el código"
    except Exception as e:
        logger.error(f"Error validar_codigo_dispositivo_hijo_remoto: {e}")
        return False, None, str(e)


def listar_dispositivos_hijos_remoto_con_limite(
    usuario_madre: str,
) -> Tuple[bool, List[Dict[str, Any]], int, str]:
    """
    Lista los dispositivos hijos en nube para un usuario madre e incluye
    el maximo de sucursales permitido (si el backend lo expone).
    """
    try:
        usuario_madre = str(usuario_madre or "").strip()
        if not usuario_madre:
            return False, [], 0, "usuario_madre vacio"

        payload = {
            "action": "list",
            "usuario_madre": usuario_madre
        }

        success, data, message = _post_sync_child_devices(payload, timeout=max(TIMEOUT, 8))
        if success and isinstance(data, dict) and data.get("success"):
            devices = data.get("dispositivos") or []
            if not isinstance(devices, list):
                devices = []

            max_sucursales = 0
            if "max_sucursales" in data:
                try:
                    parsed = int(data.get("max_sucursales"))
                    if parsed > 0:
                        max_sucursales = parsed
                except Exception:
                    max_sucursales = 0

            return True, devices, max_sucursales, data.get("message", "OK")

        server_error = ""
        if isinstance(data, dict):
            server_error = data.get("error") or data.get("message") or ""
        return False, [], 0, server_error or message or "No se pudo listar dispositivos"
    except Exception as e:
        logger.error(f"Error listar_dispositivos_hijos_remoto_con_limite: {e}")
        return False, [], 0, str(e)


def listar_dispositivos_hijos_remoto(usuario_madre: str) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Compatibilidad: lista de dispositivos hijos (sin exponer el limite).
    """
    ok, devices, _max_sucursales, msg = listar_dispositivos_hijos_remoto_con_limite(usuario_madre)
    return ok, devices, msg


def obtener_resumen_nube_dispositivos(usuario_madre: str) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Obtiene un resumen por dispositivo hijo (clientes, pacientes, productos)
    consultando la nube con filtros por codigo_dispositivo.
    """
    try:
        ok, devices, msg = listar_dispositivos_hijos_remoto(usuario_madre)
        if not ok:
            return False, [], msg

        # Preferir conteos del nuevo storage por carpetas (/api/win/new)
        snapshots_by_code: Dict[str, Dict[str, int]] = {}
        try:
            ok_snap, snap_devices, _ = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=False)
            if ok_snap:
                for sd in snap_devices:
                    if not isinstance(sd, dict):
                        continue
                    code = str(sd.get("codigo_dispositivo", "")).strip().upper()
                    if not code:
                        continue
                    ds_list = sd.get("datasets") or []
                    if not isinstance(ds_list, list):
                        ds_list = []

                    counts: Dict[str, int] = {}
                    for ds in ds_list:
                        if not isinstance(ds, dict):
                            continue
                        ds_name = str(ds.get("dataset", "")).strip().lower()
                        if not ds_name:
                            continue
                        try:
                            counts[ds_name] = int(ds.get("rows") or 0)
                        except Exception:
                            counts[ds_name] = 0
                    snapshots_by_code[code] = counts
        except Exception:
            snapshots_by_code = {}

        resumen: List[Dict[str, Any]] = []
        for device in devices:
            codigo = str(device.get("codigo_dispositivo", "")).strip().upper()
            if not codigo:
                continue

            if codigo in snapshots_by_code:
                counts = snapshots_by_code.get(codigo, {})
                clientes_count = int(counts.get("clientes", 0))
                pacientes_count = int(counts.get("pacientes", 0))
                productos_count = int(counts.get("productos", 0))
            else:
                clientes = obtener_clientes_remoto(usuario_madre, codigo_dispositivo=codigo) or []
                pacientes = obtener_pacientes_remoto(usuario_madre, codigo_dispositivo=codigo) or []
                productos = obtener_productos_remoto(usuario_madre, codigo_dispositivo=codigo) or []
                clientes_count = len(clientes)
                pacientes_count = len(pacientes)
                productos_count = len(productos)

            resumen.append({
                "id": device.get("id"),
                "nombre_optica": device.get("nombre_optica", ""),
                "ciudad": device.get("ciudad", ""),
                "codigo_dispositivo": codigo,
                "estado": device.get("estado", "activo"),
                "clientes": clientes_count,
                "pacientes": pacientes_count,
                "productos": productos_count,
            })

        return True, resumen, "OK"
    except Exception as e:
        logger.error(f"Error obtener_resumen_nube_dispositivos: {e}")
        return False, [], str(e)


def subir_snapshot_dispositivo_nube(
    usuario_madre: str,
    codigo_dispositivo: str,
    snapshot: Dict[str, Any],
    device_info: Optional[Dict[str, Any]] = None,
    updated_at: Optional[str] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Sube snapshot completo por dispositivo a /api/win/new/upload_device_snapshot.php
    """
    try:
        usuario_madre = str(usuario_madre or "").strip()
        codigo_dispositivo = str(codigo_dispositivo or "").strip().upper()
        if not usuario_madre or not codigo_dispositivo:
            return False, "usuario_madre/codigo_dispositivo vacio", {}
        if not isinstance(snapshot, dict) or not snapshot:
            return False, "snapshot invalido", {}

        payload: Dict[str, Any] = {
            "usuario_madre": usuario_madre,
            "codigo_dispositivo": codigo_dispositivo,
            "snapshot": snapshot,
            "device_info": device_info or {}
        }
        if updated_at:
            payload["updated_at"] = str(updated_at)

        url = "https://api.yhana.cloud/win/new/upload_device_snapshot.php"
        success, data, message = _post_new_snapshot_endpoint("upload_device_snapshot.php", payload, timeout=max(TIMEOUT, 20))
        if success and isinstance(data, dict) and data.get("success"):
            _clear_missing_snapshot_cache_for_device(usuario_madre, codigo_dispositivo)
            return True, data.get("message", "Snapshot subido"), data

        server_error = ""
        if isinstance(data, dict):
            server_error = data.get("error") or data.get("message") or ""
        return False, server_error or message or "No se pudo subir snapshot", data or {}
    except Exception as e:
        logger.error(f"Error subir_snapshot_dispositivo_nube: {e}")
        return False, str(e), {}


def subir_dataset_dispositivo_nube(
    usuario_madre: str,
    codigo_dispositivo: str,
    dataset: str,
    data: Any,
    operacion: Optional[str] = None,
    registro_id: Optional[str] = None,
    contenido: Any = None,
    device_info: Optional[Dict[str, Any]] = None,
    updated_at: Optional[str] = None,
    endpoint_file: str = "upload_device_snapshot.php"
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Sube un dataset individual por dispositivo a /api/win/new/upload_device_snapshot.php
    """
    try:
        usuario_madre = str(usuario_madre or "").strip()
        codigo_dispositivo = str(codigo_dispositivo or "").strip().upper()
        dataset = str(dataset or "").strip().lower()

        if not usuario_madre or not codigo_dispositivo or not dataset:
            return False, "usuario_madre/codigo_dispositivo/dataset vacio", {}

        payload: Dict[str, Any] = {
            "usuario_madre": usuario_madre,
            "codigo_dispositivo": codigo_dispositivo,
            "dataset": dataset,
            "device_info": device_info or {}
        }
        if data is not None:
            payload["data"] = data
            # Compatibilidad extra: el backend también soporta formato "snapshot".
            # Para datasets escalares (ej: config_optica), algunos servidores/proxys
            # pueden perder el campo `data`; enviar snapshot evita el 400 "No dataset to upload".
            if dataset in ("config_optica", "guias_remision"):
                payload["snapshot"] = {dataset: data}
        op_norm = str(operacion or "").strip().upper()
        if op_norm:
            payload["operacion"] = op_norm
        if registro_id is not None and str(registro_id).strip() != "":
            payload["registro_id"] = str(registro_id).strip()
        if contenido is not None:
            payload["contenido"] = contenido
        if updated_at:
            payload["updated_at"] = str(updated_at)

        endpoint_name = str(endpoint_file or "upload_device_snapshot.php").strip().lstrip('/')
        url = f"https://api.yhana.cloud/win/new/{endpoint_name}"
        success, resp, message = _post_new_snapshot_endpoint(endpoint_name, payload, timeout=max(TIMEOUT, 15))
        if success and isinstance(resp, dict) and resp.get("success"):
            _clear_missing_snapshot_cache_for_device(usuario_madre, codigo_dispositivo)
            return True, resp.get("message", "Dataset subido"), resp

        server_error = ""
        if isinstance(resp, dict):
            server_error = resp.get("error") or resp.get("message") or ""
        return False, server_error or message or "No se pudo subir dataset", resp or {}
    except Exception as e:
        logger.error(f"Error subir_dataset_dispositivo_nube: {e}")
        return False, str(e), {}


def descargar_snapshot_dispositivo_nube(
    usuario_madre: str,
    codigo_dispositivo: str,
    dataset: Optional[str] = None,
    include_data: bool = True
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Descarga snapshot (completo o por dataset) desde /api/win/new/download_device_snapshot.php
    """
    try:
        usuario_madre = str(usuario_madre or "").strip()
        codigo_dispositivo = str(codigo_dispositivo or "").strip().upper()
        if not usuario_madre or not codigo_dispositivo:
            return False, {}, "usuario_madre/codigo_dispositivo vacio"

        cache_key = _build_missing_snapshot_cache_key(
            usuario_madre,
            codigo_dispositivo,
            dataset,
            include_data,
        )
        wildcard_cache_key = _build_missing_snapshot_cache_key(
            usuario_madre,
            codigo_dispositivo,
            None,
            include_data,
        )
        cached_missing = _get_missing_snapshot_cached_message(cache_key)
        if not cached_missing and wildcard_cache_key != cache_key:
            cached_missing = _get_missing_snapshot_cached_message(wildcard_cache_key)
        if cached_missing:
            logger.debug(
                "Snapshot omitido por cache negativa: usuario=%s sucursal=%s dataset=%s include_data=%s",
                usuario_madre,
                codigo_dispositivo,
                str(dataset or "*").strip().lower() or "*",
                1 if include_data else 0,
            )
            return False, {}, cached_missing

        params: Dict[str, Any] = {
            "usuario_madre": usuario_madre,
            "codigo_dispositivo": codigo_dispositivo,
            "include_data": 1 if include_data else 0
        }
        if dataset:
            params["dataset"] = str(dataset).strip().lower()

        url = "https://api.yhana.cloud/win/new/download_device_snapshot.php"
        success, data, message = _get_new_snapshot_endpoint("download_device_snapshot.php", params, timeout=max(TIMEOUT, 20))
        if success and isinstance(data, dict) and data.get("success"):
            _clear_missing_snapshot_cache_for_device(usuario_madre, codigo_dispositivo)
            return True, data, data.get("message", "OK")

        server_error = ""
        if isinstance(data, dict):
            server_error = data.get("error") or data.get("message") or ""
        final_message = server_error or message or "No se pudo descargar snapshot"
        if _is_missing_snapshot_message(final_message):
            _remember_missing_snapshot(cache_key, final_message)
            if "dataset not found" not in str(final_message).lower():
                _remember_missing_snapshot(wildcard_cache_key, final_message)
        return False, data or {}, final_message
    except Exception as e:
        logger.error(f"Error descargar_snapshot_dispositivo_nube: {e}")
        return False, {}, str(e)


def listar_snapshots_dispositivos_nube(
    usuario_madre: str,
    include_meta: bool = False
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Lista carpetas snapshot por usuario madre en /api/win/new/list_device_snapshots.php
    """
    try:
        usuario_madre = str(usuario_madre or "").strip()
        if not usuario_madre:
            return False, [], "usuario_madre vacio"

        params = {
            "usuario_madre": usuario_madre,
            "include_meta": 1 if include_meta else 0
        }
        url = "https://api.yhana.cloud/win/new/list_device_snapshots.php"
        success, data, message = _get_new_snapshot_endpoint("list_device_snapshots.php", params, timeout=max(TIMEOUT, 15))
        if success and isinstance(data, dict) and data.get("success"):
            devices = data.get("devices") or []
            if not isinstance(devices, list):
                devices = []
            return True, devices, data.get("message", "OK")

        server_error = ""
        if isinstance(data, dict):
            server_error = data.get("error") or data.get("message") or ""
        return False, [], server_error or message or "No se pudo listar snapshots"
    except Exception as e:
        logger.error(f"Error listar_snapshots_dispositivos_nube: {e}")
        return False, [], str(e)


def listar_eventos_dispositivos_nube(
    usuario_madre: str,
    since_epoch: int = 0,
    limit: int = 50,
    event_type: Optional[str] = None
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Lista eventos emitidos por dispositivos hijos (ej: producto_creado).
    Endpoint: /api/win/new/list_device_events.php
    """
    def _parse_events_payload(payload: Any, default_message: str = "OK") -> Tuple[bool, List[Dict[str, Any]], str]:
        if isinstance(payload, list):
            events = [e for e in payload if isinstance(e, dict)]
            return True, events, default_message

        if isinstance(payload, dict):
            if payload.get("success", True) is False:
                err = str(payload.get("error") or payload.get("message") or default_message or "Error")
                return False, [], err

            raw_events = payload.get("events") or payload.get("data") or []
            if isinstance(raw_events, list):
                events = [e for e in raw_events if isinstance(e, dict)]
                return True, events, str(payload.get("message") or default_message or "OK")
            return True, [], str(payload.get("message") or default_message or "OK")

        return False, [], "Respuesta invalida list_device_events"

    def _try_parse_json_from_text(raw_text: str) -> Optional[Any]:
        text = str(raw_text or "").lstrip("\ufeff").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            pass

        # Si hay ruido antes/despues del JSON (warnings PHP/HTML), extraer bloque JSON.
        start_candidates = [i for i in (text.find("{"), text.find("[")) if i >= 0]
        if not start_candidates:
            return None
        start = min(start_candidates)
        for end_char in ("}", "]"):
            end = text.rfind(end_char)
            if end <= start:
                continue
            chunk = text[start:end + 1].strip()
            if not chunk:
                continue
            try:
                return json.loads(chunk)
            except Exception:
                continue
        return None

    try:
        usuario_madre = str(usuario_madre or "").strip()
        if not usuario_madre:
            return False, [], "usuario_madre vacio"

        params: Dict[str, Any] = {
            "usuario_madre": usuario_madre,
            "since_epoch": max(0, int(since_epoch or 0)),
            "limit": max(1, min(int(limit or 50), 200)),
        }
        if event_type:
            params["type"] = str(event_type).strip().lower()

        success, data, message = _get_new_snapshot_endpoint(
            "list_device_events.php",
            params,
            timeout=max(TIMEOUT, 12)
        )
        if success:
            return _parse_events_payload(data, str(message or "OK"))

        # Intentar parsear JSON aunque venga mezclado con warnings/HTML.
        if isinstance(data, dict):
            maybe_payload = _try_parse_json_from_text(str(data.get("_raw_text", "")))
            if maybe_payload is not None:
                ok_parsed, events_parsed, msg_parsed = _parse_events_payload(maybe_payload, str(message or "OK"))
                if ok_parsed:
                    logger.warning("list_device_events: respuesta no JSON limpia, pero JSON recuperado desde raw_text")
                    return True, events_parsed, msg_parsed

        # Fallback adicional: algunos hosts aceptan este endpoint solo por POST.
        success_post, data_post, message_post = _post_new_snapshot_endpoint(
            "list_device_events.php",
            params,
            timeout=max(TIMEOUT, 12)
        )
        if success_post:
            return _parse_events_payload(data_post, str(message_post or "OK"))

        if isinstance(data_post, dict):
            maybe_payload_post = _try_parse_json_from_text(str(data_post.get("_raw_text", "")))
            if maybe_payload_post is not None:
                ok_parsed, events_parsed, msg_parsed = _parse_events_payload(maybe_payload_post, str(message_post or "OK"))
                if ok_parsed:
                    logger.warning("list_device_events POST: JSON recuperado desde raw_text")
                    return True, events_parsed, msg_parsed

        server_error = ""
        if isinstance(data, dict):
            server_error = str(data.get("error") or data.get("message") or "")
        if not server_error and isinstance(data_post, dict):
            server_error = str(data_post.get("error") or data_post.get("message") or "")
        return False, [], server_error or message_post or message or "No se pudo listar eventos"
    except Exception as e:
        logger.error(f"Error listar_eventos_dispositivos_nube: {e}")
        return False, [], str(e)


def obtener_resumen_snapshot_nube(usuario_madre: str) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Resumen rapido de datasets por dispositivo desde storage por carpetas.
    """
    try:
        ok, devices, msg = listar_snapshots_dispositivos_nube(usuario_madre, include_meta=True)
        if not ok:
            return False, [], msg

        resumen: List[Dict[str, Any]] = []
        for d in devices:
            codigo = str(d.get("codigo_dispositivo", "")).strip().upper()
            datasets = d.get("datasets") or []
            if not isinstance(datasets, list):
                datasets = []

            counts: Dict[str, int] = {}
            for ds in datasets:
                if not isinstance(ds, dict):
                    continue
                ds_name = str(ds.get("dataset", "")).strip()
                if not ds_name:
                    continue
                rows = ds.get("rows")
                try:
                    counts[ds_name] = int(rows) if rows is not None else 0
                except Exception:
                    counts[ds_name] = 0

            resumen.append({
                "codigo_dispositivo": codigo,
                "folder": d.get("folder", ""),
                "dataset_count": int(d.get("dataset_count", 0) or 0),
                "counts": counts,
                "meta": d.get("meta") if isinstance(d.get("meta"), dict) else {}
            })

        return True, resumen, "OK"
    except Exception as e:
        logger.error(f"Error obtener_resumen_snapshot_nube: {e}")
        return False, [], str(e)



