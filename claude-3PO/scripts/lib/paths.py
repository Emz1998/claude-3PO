"""paths.py — Tiny pure path helpers shared across guards, recorders, and resolvers."""

from constants.paths import E2E_TEST_REPORT


def is_e2e_report_path(file_path: str) -> bool:
    """
    Check whether a path refers to the E2E test report.

    Matches any top-level ``E2E*_TEST_REPORT.md`` filename (so per-suite reports
    like ``E2E_BUILD_TEST_REPORT.md`` all qualify) and the legacy
    ``.claude/reports`` path retained for back-compat.

    Args:
        file_path (str): Candidate file path.

    Returns:
        bool: ``True`` when the path matches one of the recognised E2E forms.

    Example:
        >>> is_e2e_report_path("E2E_BUILD_TEST_REPORT.md")
        True
        >>> is_e2e_report_path("")
        False
    """
    if not file_path:
        return False
    # Match both the wildcard per-suite form (E2E_*_TEST_REPORT.md) and the
    # legacy fixed report path so older writers keep working.
    basename = file_path.rsplit("/", 1)[-1]
    if basename.startswith("E2E") and basename.endswith("_TEST_REPORT.md"):
        return True
    return file_path == E2E_TEST_REPORT or file_path.endswith(E2E_TEST_REPORT)


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


def all_revised(to_revise: list[str], revised: list[str]) -> bool:
    """
    True iff every flagged file has been revised (compared by basename).

    Basename comparison is deliberate: the flagged list may store absolute
    paths while the revised list stores workspace-relative ones (or vice
    versa). Returns ``False`` when ``to_revise`` is empty — an empty "still
    to revise" list without an empty "revised" list is a workflow bug, not
    a completion signal.

    Args:
        to_revise (list[str]): Files the reviewer flagged.
        revised (list[str]): Files the author has edited since.

    Returns:
        bool: ``True`` only when ``to_revise`` is non-empty and every
        basename in it appears in ``revised``.

    Example:
        >>> all_revised(["src/a.py"], ["a.py"])
        True
        >>> all_revised([], ["a.py"])
        False
    """
    return bool(to_revise) and not (basenames(to_revise) - basenames(revised))


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
