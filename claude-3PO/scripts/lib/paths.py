"""Pure path helpers shared across guards, recorders, and resolvers."""


def basenames(paths: list[str]) -> set[str]:
    """Return the set of basenames (final path component) from *paths*."""
    return {p.rsplit("/", 1)[-1] for p in paths}


def path_matches(file_path: str, expected: str | None) -> bool:
    """True when *file_path* equals *expected* or ends with it.

    Returns False when either side is falsy — callers can pass an optional
    config value without guarding for None.
    """
    if not file_path or not expected:
        return False
    return file_path == expected or file_path.endswith(expected)
