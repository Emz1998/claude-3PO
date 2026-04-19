"""commands.py — Parsers for ``/build`` prompts and ``gh pr checks`` output.

Both concerns parse free-form command text into structured values. Keeping
them co-located avoids spawning single-caller sibling modules for each
command the guardrails need to read.
"""

import re


# ---------------------------------------------------------------------------
# /build prompt extraction
# ---------------------------------------------------------------------------

_BUILD_PATTERN = re.compile(r"^/(?:\w+:)?build\s+(.*)", re.DOTALL)
_STORY_ID_PATTERN = r"\b([A-Z]{2,}-\d+)\b"
_BUILD_FLAGS = [
    "--skip-clarify",
    "--skip-explore",
    "--skip-research",
    "--skip-all",
    "--tdd",
    "--reset",
    "--takeover",
]


def _strip_flags_and_ids(text: str) -> str:
    """Strip recognized ``--flag`` tokens and ``ABC-123`` story IDs from *text*.

    Example:
        >>> _strip_flags_and_ids("US-001 --tdd add login")
        'add login'
    """
    text = re.sub(_STORY_ID_PATTERN, "", text)
    for flag in _BUILD_FLAGS:
        text = text.replace(flag, "")
    return text.strip()


def extract_build_instructions(prompt: str) -> str | None:
    """
    Extract the free-text instructions from a ``/build`` slash-command prompt.

    Story IDs and known flags are stripped so the remainder is just the user's
    actual instruction text. Returns ``None`` (not ``""``) when the prompt
    isn't a ``/build`` command, so callers can branch on "is this a build?"
    independent of "are there instructions?".

    Args:
        prompt (str): Raw user prompt.

    Returns:
        str | None: Cleaned instruction text, or ``None`` if not a build prompt
        or if the instruction is empty after stripping flags/IDs.

    Example:
        >>> extract_build_instructions("/build US-001 --tdd add login")
        'add login'
        >>> extract_build_instructions("hello") is None
        True
    """
    match = _BUILD_PATTERN.match(prompt.strip())
    if not match:
        return None
    return _strip_flags_and_ids(match.group(1)) or None


# ---------------------------------------------------------------------------
# gh pr checks output parsing
# ---------------------------------------------------------------------------


_PENDING_KEYWORDS = ("\tpending", "\tqueued", "\tin_progress", "\twaiting")


def _ci_status_from_tabs(output: str) -> str | None:
    """
    Read CI status from tab-delimited ``gh pr checks`` output.

    Order matters: any failure beats any pending check, which beats a pass.
    Returns ``None`` when the output isn't tab-delimited (caller falls back
    to the summary parser).

    Example:
        >>> _ci_status_from_tabs("ci\\tpass\\tx")
        'passed'
        >>> _ci_status_from_tabs("plain text") is None
        True
    """
    if "\tfail" in output:
        return "failed"
    if any(kw in output for kw in _PENDING_KEYWORDS):
        return "pending"
    if "\tpass" in output:
        return "passed"
    return None


def _ci_status_from_summary(output: str) -> str | None:
    """Read CI status from the human-friendly ``gh pr checks --watch`` summary line.

    Example:
        >>> _ci_status_from_summary("All checks were successful")
        'passed'
        >>> _ci_status_from_summary("nothing relevant") is None
        True
    """
    if "All checks were successful" in output:
        return "passed"
    if "Some checks were not successful" in output:
        return "failed"
    return None


def extract_ci_status(output: str) -> str:
    """
    Parse ``gh pr checks`` output to a single CI status string.

    Tries the tab-delimited format first (default ``gh pr checks`` output)
    then falls back to the summary line (``--watch`` mode). Empty/blank
    output is treated as pending — the most cautious assumption when CI
    hasn't reported yet.

    Args:
        output (str): Combined stdout from ``gh pr checks``.

    Returns:
        str: ``"passed"``, ``"failed"``, or ``"pending"``.

    Example:
        >>> extract_ci_status("ci\\tpass\\t...")
        'passed'
        >>> extract_ci_status("")
        'pending'
    """
    if not output or not output.strip():
        return "pending"

    return (
        _ci_status_from_tabs(output)
        or _ci_status_from_summary(output)
        or "pending"
    )
