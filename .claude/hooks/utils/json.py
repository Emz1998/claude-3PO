import json
import sys
from pathlib import Path
from typing import Any, Optional


def load_json(file_path: Path) -> dict:
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def read_stdin_json() -> dict:
    """Parse JSON from stdin. Returns empty dict on error."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def save_json(data: dict, file_path: Path) -> None:
    file_path.write_text(json.dumps(data, indent=2))
