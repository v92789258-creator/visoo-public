import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _resolve_state_path(username: str) -> Path:
    from utils.file_handler import VISO_DIR, resolve_username

    resolved = str(resolve_username(username) or username or "").strip()
    return Path(VISO_DIR) / resolved / "data" / "sync_center_state.json"


def load_sync_center_state(username: str) -> Dict[str, Any]:
    path = _resolve_state_path(username)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_sync_center_state(username: str, state: Dict[str, Any]) -> bool:
    path = _resolve_state_path(username)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state or {}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def record_sync_center_event(
    username: str,
    event_type: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    state = load_sync_center_state(username)
    history = state.get("history") if isinstance(state.get("history"), list) else []

    normalized_type = str(event_type or "").strip().lower() or "unknown"
    entry: Dict[str, Any] = {
        "type": normalized_type,
        "at": str((payload or {}).get("at") or datetime.now().isoformat()),
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "at":
                continue
            entry[key] = value

    history = [entry] + [item for item in history if isinstance(item, dict)]
    state["history"] = history[:50]
    state[f"last_{normalized_type}"] = entry
    state["updated_at"] = entry["at"]
    save_sync_center_state(username, state)
    return entry
