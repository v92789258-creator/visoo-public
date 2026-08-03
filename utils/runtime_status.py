import threading
import time
from contextlib import contextmanager


_LOCK = threading.RLock()
_ACTIVE_OPERATIONS = {}


def begin_operation(key: str, label: str, kind: str = "info") -> str:
    op_key = str(key or "").strip() or f"op:{int(time.time() * 1000)}"
    payload = {
        "key": op_key,
        "label": str(label or "").strip() or "Procesando...",
        "kind": str(kind or "info").strip().lower() or "info",
        "started_at": time.time(),
    }
    with _LOCK:
        _ACTIVE_OPERATIONS[op_key] = payload
    return op_key


def update_operation(key: str, label: str = None, kind: str = None) -> None:
    op_key = str(key or "").strip()
    if not op_key:
        return
    with _LOCK:
        current = dict(_ACTIVE_OPERATIONS.get(op_key, {}))
        if not current:
            return
        if label is not None:
            current["label"] = str(label or "").strip() or current.get("label", "Procesando...")
        if kind is not None:
            current["kind"] = str(kind or "").strip().lower() or current.get("kind", "info")
        _ACTIVE_OPERATIONS[op_key] = current


def end_operation(key: str) -> None:
    op_key = str(key or "").strip()
    if not op_key:
        return
    with _LOCK:
        _ACTIVE_OPERATIONS.pop(op_key, None)


def get_active_operations():
    with _LOCK:
        items = [dict(item) for item in _ACTIVE_OPERATIONS.values()]
    items.sort(key=lambda item: float(item.get("started_at", 0) or 0))
    return items


@contextmanager
def tracked_operation(key: str, label: str, kind: str = "info"):
    op_key = begin_operation(key, label, kind)
    try:
        yield op_key
    finally:
        end_operation(op_key)
