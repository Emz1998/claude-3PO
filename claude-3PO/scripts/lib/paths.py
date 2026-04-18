"""paths.py — Tiny pure path helpers shared across guards, recorders, and resolvers."""


def basenames(paths: list[str]) -> set[str]:
    """
    Return the set of basenames (final ``/``-separated component) from *paths*.

    Args:
        paths (list[str]): Path-like strings.

    Returns:
        set[str]: The trailing component of each path; duplicates collapsed.

    Example:
        >>> basenames(["a/b/c.py", "x/c.py"]) == {"c.py"}
        True
    """
    return {p.rsplit("/", 1)[-1] for p in paths}


def path_matches(file_path: str, expected: str | None) -> bool:
    """
    True when *file_path* equals *expected* or ends with it.

    Both sides falling-through-to-False when empty/``None`` is deliberate
    convenience: callers can pass an optional config value (which may be unset)
    without writing ``if expected and ...`` guards everywhere.

    Args:
        file_path (str): Path being checked.
        expected (str | None): Path or path suffix to match. ``None`` / ``""``
            yields ``False``.

    Returns:
        bool: ``True`` if there's an exact or suffix match.

    Example:
        >>> path_matches("/a/b/c.py", "b/c.py")
        True
        >>> path_matches("c.py", None)
        False
    """
    if not file_path or not expected:
        return False
    return file_path == expected or file_path.endswith(expected)
