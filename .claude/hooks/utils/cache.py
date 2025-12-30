import json
import os
import tempfile
from pathlib import Path
from typing import Any

CACHE_PATH = Path(".claude/hooks/cache.json")


def load_cache(file_path: Path = CACHE_PATH) -> dict:
    try:
        cache = json.loads(file_path.read_text())
        return cache
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def get_cache(key: str, cache: dict = load_cache()) -> Any:
    """Get value from shared cache. Returns None if not found."""
    if not key:
        raise ValueError("Cache key is required")
    try:
        return cache.get(key)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def write_cache(cache: dict, cache_path: Path = CACHE_PATH) -> None:
    """Write cache to file."""
    cache_path.write_text(json.dumps(cache, indent=2))


def set_cache(key: str, value: Any, cache: dict = load_cache()) -> None:
    """Set value in shared cache with namespace isolation."""
    if not key:
        print("Cache key is required")
        return

    if key not in cache:
        print(f"Cache key {key} not found")
        return

    cache[key] = value
    write_cache(cache)


def append_cache(key: str, value: Any, cache: dict = load_cache()) -> None:
    """Append value to a list in cache."""
    try:
        if type(cache.get(key)) is not list:
            raise ValueError(f"Cache key {key} is not a list")
        cache[key].append(value)
        write_cache(cache)
    except Exception as e:
        print(f"Error appending to cache list: {e}")
