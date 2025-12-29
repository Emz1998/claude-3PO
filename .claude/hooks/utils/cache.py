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


def write_cache(cache: dict) -> None:
    """Write cache atomically using temp file to prevent corruption."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first, then atomic rename
    fd, temp_path = tempfile.mkstemp(dir=CACHE_PATH.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(cache, f, indent=2)
        os.replace(temp_path, CACHE_PATH)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def get_cache(key: str, cache: dict = load_cache()) -> Any:
    """Get value from shared cache. Returns None if not found."""
    if not key:
        raise ValueError("Cache key is required")
    try:
        return cache.get(key)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


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


def append_to_cache_list(key: str, value: Any, cache: dict = load_cache()) -> None:
    """Append value to a list in cache."""
    try:
        if type(cache.get(key)) is not list:
            raise ValueError(f"Cache key {key} is not a list")
        cache[key].append(value)
        write_cache(cache)
    except Exception as e:
        print(f"Error appending to cache list: {e}")
