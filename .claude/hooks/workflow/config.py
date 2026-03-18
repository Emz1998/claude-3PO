"""Centralized config loader — reads config.yaml once and caches it."""

from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
_cache: dict[str, Any] | None = None
_REQUIRED_KEYS = {"paths", "phases", "agents"}


def load() -> dict[str, Any]:
    """Load and cache the full config dict."""
    global _cache
    if _cache is None:
        with open(_CONFIG_PATH) as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            raise ValueError(f"config.yaml must be a dict, got {type(raw)}")
        missing = _REQUIRED_KEYS - raw.keys()
        if missing:
            raise ValueError(f"config.yaml missing required keys: {missing}")
        _cache = raw
    return _cache


def get(dotted_key: str, default: Any = None) -> Any:
    """Dot-notation access into the config dict.

    Example: get("agents.pre_coding") -> ["Explore", "Plan", ...]
    """
    data: Any = load()
    keys = dotted_key.split(".")
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key)
        if data is None:
            return default
    return data


def get_workflow_phases() -> list[str]:
    """Get the workflow phases from the config."""
    from session_state import SessionState  # type: ignore

    session = SessionState()
    phases = get("phases.workflow", [])

    if session.get("dry_run", False):
        return [f"dry-run:{phase}" for phase in phases]
    return phases


def get_reviewers() -> list[str]:
    """Derive reviewer agents from all agent groups by naming convention."""
    agents = get("agents", {})
    return [a for group in agents.values() for a in group if a.endswith("-reviewer")]


def reload() -> dict[str, Any]:
    """Force reload from disk (useful for testing)."""
    global _cache
    _cache = None
    return load()
