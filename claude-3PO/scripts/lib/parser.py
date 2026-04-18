"""parser.py — Parsers for ``/build`` arguments and plan-file frontmatter.

Two distinct concerns share this module: extracting metadata from a plan's
YAML frontmatter, and parsing the flag-laden ``/build`` slash command. They
sit together because both are pure-string parsers used during workflow
initialization, and keeping them in one tiny module avoids over-fragmentation.
"""

import re

from constants import STORY_ID_PATTERN


def parse_frontmatter(content: str) -> dict[str, str]:
    """
    Extract YAML frontmatter key-value pairs from a markdown string.

    Only handles the simple ``key: value`` shape — nested YAML, lists, or
    multi-line values are not supported because the workflow frontmatter
    schema is intentionally flat. Missing or malformed frontmatter returns
    ``{}`` so callers can blindly ``.get(...)`` without exception handling.

    Args:
        content (str): Markdown text potentially starting with a ``---`` block.

    Returns:
        dict[str, str]: Frontmatter keys → values; empty dict if absent.

    Example:
        >>> parse_frontmatter("---\\nsession_id: abc\\n---\\n# Title")
        {'session_id': 'abc'}
    """
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip()
    return fm


def parse_skip(args: str) -> list[str]:
    """
    Translate ``--skip-*`` flags in a ``/build`` arg string into phase names.

    ``--skip-all`` is shorthand for ``--skip-explore`` and ``--skip-research``
    together; ``--skip-vision`` stands alone. Returns the list rather than a
    set because downstream code occasionally cares about insertion order.

    Args:
        args (str): Raw arg portion of a ``/build`` invocation.

    Returns:
        list[str]: Subset of ``["explore", "research", "vision"]``.

    Example:
        >>> parse_skip("--skip-all --tdd")
        ['explore', 'research']
    """
    skip: list[str] = []
    if "--skip-explore" in args or "--skip-all" in args:
        skip.append("explore")
    if "--skip-research" in args or "--skip-all" in args:
        skip.append("research")
    if "--skip-vision" in args:
        skip.append("vision")
    return skip


def parse_story_id(args: str) -> str | None:
    """
    Pull the first story ID (e.g. ``US-001``) from a ``/build`` arg string.

    Args:
        args (str): Raw arg portion of a ``/build`` invocation.

    Returns:
        str | None: Matched story ID, or ``None`` if none is present.

    Example:
        >>> parse_story_id("US-001 add login")
        'US-001'
    """
    match = re.search(STORY_ID_PATTERN, args)
    return match.group(1) if match else None


def parse_instructions(args: str) -> str:
    """
    Strip flags and story IDs from a ``/build`` arg string, returning the prose.

    The whitelist of recognized flags is hard-coded here (rather than imported
    from a constant) so adding a new ``/build`` flag must be a deliberate edit
    in one obvious place.

    Args:
        args (str): Raw arg portion of a ``/build`` invocation.

    Returns:
        str: Cleaned instruction text with surrounding whitespace stripped.

    Example:
        >>> parse_instructions("US-001 --tdd add login")
        'add login'
    """
    flags = [
        "--skip-explore", "--skip-research", "--skip-vision", "--skip-all",
        "--tdd", "--reset", "--takeover", "--test",
    ]
    text = re.sub(STORY_ID_PATTERN, "", args)
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()
