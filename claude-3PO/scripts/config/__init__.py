from functools import lru_cache

from .config import Config


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return a process-wide cached Config instance.

    Tests that mutate config or rely on isolated defaults must call
    ``get_config.cache_clear()`` (the conftest ``config`` fixture does this).
    """
    return Config()


__all__ = ["Config", "get_config"]
