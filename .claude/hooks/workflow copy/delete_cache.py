#!/usr/bin/env python3
"""Delete workflow cache file."""

import sys
from pathlib import Path

CACHE_PATH = Path(".claude/hooks/cache.json")


def delete_cache() -> None:
    """Delete the cache file entirely."""
    try:
        if CACHE_PATH.exists():
            CACHE_PATH.unlink()
            print("Cache deleted successfully")
        else:
            print("Cache file does not exist")
    except Exception as e:
        print(f"Cache deletion error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    delete_cache()
