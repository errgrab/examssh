"""Per-user exam state stored outside the candidate's Git repository."""

import json
import os
from pathlib import Path


STATE_DIR = Path(os.environ.get("EXAMSHELL_STATE_DIR", "/var/lib/examshell/sessions"))


def state_path() -> Path:
    return STATE_DIR / f"{os.getuid()}.json"


def load_state() -> dict | None:
    path = state_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)

