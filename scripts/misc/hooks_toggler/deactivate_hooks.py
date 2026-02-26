#!/usr/bin/env python3
"""Deactivate hooks by caching them and clearing settings."""

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


def deactivate_hooks() -> None:
    settings = load_json(SETTINGS_FILE)
    hooks = settings.get("hooks", {})
    if not hooks:
        print("No hooks to deactivate")
        return

    # Cache current hooks
    cache = load_json(CACHE_FILE)
    cache["hooks"] = hooks
    Path(CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(CACHE_FILE).write_text(json.dumps(cache, indent=2))

    # Clear hooks from settings
    settings["hooks"] = {}
    Path(SETTINGS_FILE).write_text(json.dumps(settings, indent=2))
    print("Hooks deactivated successfully")


if __name__ == "__main__":
    deactivate_hooks()
