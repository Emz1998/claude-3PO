#!/usr/bin/env python3
"""Reactivate previously deactivated hooks from cache."""

import json
from pathlib import Path

SETTINGS_FILE = ".claude/settings.local.json"
CACHE_FILE = ".claude/scripts/hooks_toggler/cache.json"


def load_json(file_path: str) -> dict:
    """Load JSON file, return empty dict if missing/invalid."""
    path = Path(file_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def reactivate_hooks() -> None:
    cache = load_json(CACHE_FILE)
    hooks = cache.get("hooks", {})
    if not hooks:
        print("No hooks to reactivate")
        return

    settings = load_json(SETTINGS_FILE)
    settings["hooks"] = hooks
    Path(SETTINGS_FILE).write_text(json.dumps(settings, indent=2))
    print("Hooks reactivated successfully")


if __name__ == "__main__":
    reactivate_hooks()
