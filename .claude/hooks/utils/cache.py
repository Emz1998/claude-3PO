import json
from pathlib import Path
from typing import Any

CACHE_PATH = Path(".claude/hooks/cache.json")


def load_cache(file_path: Path = CACHE_PATH) -> dict:
    try:
        cache = json.loads(file_path.read_text())
        return cache
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def get_cache(key: str, cache_path: Path = CACHE_PATH) -> Any:
    """Get value from shared cache. Returns None if not found."""

    cache = load_cache(cache_path)
    if not key:
        raise ValueError("Cache key is required")
    try:
        return cache.get(key)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def write_cache(cache: dict, cache_path: Path = CACHE_PATH) -> None:
    """Write cache to file."""
    cache_path.write_text(json.dumps(cache, indent=2))


def set_cache(key: str, value: Any, cache_path: Path = CACHE_PATH) -> None:
    # Set value in shared cache with namespace isolation.

    if not cache_path.exists():
        cache_path.touch()
        cache_path.write_text(json.dumps({}, indent=2))
        print(f"Cache file created: {cache_path}")
    cache = load_cache(cache_path)

    if not key:
        print("Cache key is required")
        return
    cache[key] = value
    write_cache(cache, cache_path)


def append_cache(key: str, value: Any, cache_path: Path = CACHE_PATH) -> None:
    """Append value to a list in cache."""
    try:
        cache = load_cache(cache_path)
        if type(cache.get(key)) is not list:
            raise ValueError(f"Cache key {key} is not a list")
        cache[key].append(value)
        write_cache(cache, cache_path)
    except Exception as e:
        print(f"Error appending to cache list: {e}")
