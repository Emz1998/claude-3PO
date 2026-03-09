"""Centralized config loader — reads config.yaml once and caches it."""

from pathlib import Path
from typing import Any

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

    Example: get("agents.reviewers") -> ["code-reviewer", ...]
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


def reload() -> dict[str, Any]:
    """Force reload from disk (useful for testing)."""
    global _cache
    _cache = None
    return load()
