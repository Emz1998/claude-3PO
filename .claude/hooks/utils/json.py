import json
import sys
from pathlib import Path
from typing import Any, Optional


def load_json(file_path: str) -> dict:
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        return {}
    try:
        return json.loads(Path(file_path).read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def get_json(key: str, default: Optional[Any] = None, file_path: str = "") -> Any:
    data = load_json(file_path)
    return data.get(key, default)


def set_json(
    key: str,
    value: Any,
    file_path: str,
) -> None:
    data = load_json(file_path)
    data[key] = value
    Path(file_path).write_text(json.dumps(data, indent=2))


def read_stdin_json() -> dict:
    """Parse JSON from stdin. Returns empty dict on error."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}
