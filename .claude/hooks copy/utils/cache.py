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


def save_cache(cache: dict, cache_path: Path = CACHE_PATH) -> None:
    """Save cache to file."""
    cache_path.write_text(json.dumps(cache, indent=2))


def get_cache(key: str, cache: dict | None = None) -> Any | None:
    """Get value from cache. Returns None if not found."""
    if not cache:
        cache = load_cache()
    return cache.get(key, None)


def set_cache(key: str, value: Any, cache: dict | None = None) -> None:
    # Set value in shared cache with namespace isolation.

    if not cache:
        cache = load_cache()

    if not key:
        raise ValueError("Cache key is required")
    cache[key] = value
    save_cache(cache)


def append_cache(key: str, value: Any, cache_path: Path = CACHE_PATH) -> None:
    """Append value to a list in cache."""
    try:
        cache = load_cache(cache_path)
        if type(cache.get(key)) is not list:
            raise ValueError(f"Cache key {key} is not a list")
        cache[key].append(value)
        save_cache(cache, cache_path)
    except Exception as e:
        print(f"Error appending to cache list: {e}")


def get_session_id(cache: dict | None = None) -> str | None:
    return get_cache("session_id", cache)
