"""Utility functions for reading project status."""

import json
from pathlib import Path
from typing import Any, Optional

DEFAULT_STATUS_PATH = Path("project").absolute() / "status.json"


def get_status(
    key: str, default: Optional[Any] = None, file_path: Path = DEFAULT_STATUS_PATH
) -> Any:
    try:
        status_data = json.loads(file_path.read_text()) if file_path.exists() else {}

    except json.JSONDecodeError:
        status_data = {}
    if not key:
        return status_data
    else:
        return status_data.get(key, default)


def set_status(key: str, value: Any, file_path: Path = DEFAULT_STATUS_PATH) -> bool:
    if not file_path.parent.exists():
        print(f"Directory not found: {file_path.parent}")
        return False

    if not file_path.exists():
        file_path.touch()

    status = {}
    content = file_path.read_text().strip()
    if content:
        try:
            status = json.loads(content)
        except json.JSONDecodeError:
            print(f"Error decoding status from {file_path}")
            return False

    status[key] = value

    try:
        file_path.write_text(json.dumps(status, indent=4))
        return True
    except OSError as e:
        print(f"Error writing status to {file_path}: {e}")
        return False
