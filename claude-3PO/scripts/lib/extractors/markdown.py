"""markdown.py — Pure markdown parsers (sections, tables, bullets, bold meta).

None of these helpers touch the filesystem or raise on malformed input —
missing sections / tables / lines yield empty structures so callers can
iterate without guarding every call.
"""

import re

from constants import TABLE_PATTERN


def extract_md_sections(md: str, level: int) -> list[tuple[str, str]]:
    """
    Extract every section at the given heading level from a markdown string.

    A section ends at the next heading of the same-or-higher level (so ``##``
    stops at ``##`` or ``#`` but not ``###``). Windows ``\\r\\n`` line endings
    are normalized first because the regex assumes ``\\n``.

    Args:
        md (str): Full markdown text.
        level (int): Heading depth (1 for ``#``, 2 for ``##``, etc.).

    Returns:
        list[tuple[str, str]]: ``[(heading_text, body), ...]`` in document
        order. Bodies have surrounding whitespace stripped.

    Example:
        >>> extract_md_sections("## A\\nbody-a\\n## B\\nbody-b", 2)
        [('A', 'body-a'), ('B', 'body-b')]
    """
    md = md.replace("\r\n", "\n")
    pattern = re.compile(
        rf"""
        ^[#]{{{level}}}(?![#])[ \t]+([^\n]+?)[ \t]*$  # heading text
        \n?                                             # optional newline after heading
        (.*?)                                           # content (DOTALL)
        (?=
            ^[#]{{1,{level}}}(?![#])[ \t]+              # next same-or-higher heading
            | \Z
        )
        """,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )

    return [(m.group(1), m.group(2).strip()) for m in pattern.finditer(md)]


_TABLE_PATTERN = re.compile(TABLE_PATTERN, re.MULTILINE)


def _parse_table_row(line: str, cols: int | None = None) -> list[str]:
    """Split a markdown ``| a | b | c |`` row into ``["a", "b", "c"]``.

    Example:
        >>> _parse_table_row("| a | b | c |")
        ['a', 'b', 'c']
        >>> _parse_table_row("| a | b | c |", cols=2)
        ['a', 'b']
    """
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells[:cols] if cols is not None else cells


def extract_table(
    md: str,
    rows: int | None = None,
    cols: int | None = None,
) -> list[list[str]]:
    """
    Extract the first markdown table found in *md*.

    The header separator row (``|---|---|``) is dropped so callers always get
    semantic rows. Pass ``rows`` / ``cols`` to truncate large tables — useful
    when only the first few cells matter (e.g. type prefixes from an ID
    conventions table).

    Args:
        md (str): Markdown text to search.
        rows (int | None): Max number of body rows to return (header always kept).
        cols (int | None): Max number of cells per row.

    Returns:
        list[list[str]]: Header row at index 0, then body rows. Empty list if
        no table is present.

    Example:
        >>> extract_table("| A | B |\\n|---|---|\\n| 1 | 2 |")
        [['A', 'B'], ['1', '2']]
    """
    match = _TABLE_PATTERN.search(md)
    if not match:
        return []

    header = _parse_table_row(match.group(1), cols)
    body_lines = match.group(3).strip().splitlines()
    if rows is not None:
        body_lines = body_lines[:rows]

    return [header] + [_parse_table_row(line, cols) for line in body_lines]


def extract_bullet_items(content: str) -> list[str]:
    """
    Extract ``- item`` bullet items from a markdown blob.

    Args:
        content (str): Markdown text.

    Returns:
        list[str]: Bullet text with the leading ``- `` removed, in document order.

    Example:
        >>> extract_bullet_items("- foo\\n- bar\\nplain line")
        ['foo', 'bar']
    """
    return [
        line.lstrip("- ").strip()
        for line in content.splitlines()
        if line.strip().startswith("- ")
    ]


def match_substring(subject: str, candidates: list[str]) -> str | None:
    """
    Find a case-insensitive substring match between subject and any candidate.

    Matches in either direction (subject ⊆ candidate OR candidate ⊆ subject)
    plus equality, so partial titles like ``Add login`` will match the plan
    task ``Add login flow with OTP`` and vice versa.

    Args:
        subject (str): Candidate text to locate.
        candidates (list[str]): Allowed values to match against.

    Returns:
        str | None: The matched candidate (original casing/whitespace), or
        ``None`` if no entry matches.

    Example:
        >>> match_substring("Add login", ["Add login flow"])
        'Add login flow'
        >>> match_substring("totally unrelated", ["a", "b"]) is None
        True
    """
    # Normalize once; compare against each candidate's normalized form so
    # trailing spaces / mixed case never defeat a real match.
    normalized = subject.strip().lower()
    for c in candidates:
        c_lower = c.strip().lower()
        if normalized == c_lower or c_lower in normalized or normalized in c_lower:
            return c
    return None


def validate_bullet_section(section_name: str, body: str) -> None:
    """
    Enforce that a markdown section uses ``- item`` bullets (not ``###`` subsections).

    Args:
        section_name (str): Heading of the section being checked (for the error
            message — not used to look up the body).
        body (str): Markdown body of the section.

    Raises:
        ValueError: If ``###`` subsections appear in the body, or if no bullet
            items are present.

    Example:
        >>> validate_bullet_section("Tasks", "- one\\n- two")
        >>> # Raises ValueError when body has ### subsections or no bullets.
    """
    # Subsection + empty-bullets are separate authoring mistakes — two distinct
    # error messages so the writer knows which rule to fix.
    if "### " in body:
        raise ValueError(
            f"'{section_name}' must use bullet items (- item), not ### subsections. "
            f"See the plan template for the correct format."
        )
    if not any(line.strip().startswith("- ") for line in body.splitlines()):
        raise ValueError(
            f"'{section_name}' must have at least one bullet item (- item). "
            f"See the plan template for the correct format."
        )


def require_section(sections: dict[str, str], heading: str) -> list[str]:
    """
    Return non-empty bullet items from a required H2 section, or raise.

    Missing *and* empty sections both raise — callers use this to enforce that
    a review report actually lists file paths under a given heading.

    Args:
        sections (dict[str, str]): Section-map produced by
            :func:`extract_section_map`.
        heading (str): Required H2 heading text.

    Returns:
        list[str]: Bullet items found under the heading.

    Raises:
        ValueError: If the section is missing or contains no bullet items.

    Example:
        >>> require_section({"Files to revise": "- a.py"}, "Files to revise")
        ['a.py']
    """
    # Missing section short-circuits before the bullet walk — distinct error message
    # keeps the two failure modes diagnosable by the caller.
    if heading not in sections:
        raise ValueError(f"'{heading}' section is required")
    items = extract_bullet_items(sections[heading])
    if not items:
        raise ValueError(f"'{heading}' section is empty — provide file paths")
    return items


def extract_section_map(content: str, level: int) -> dict[str, str]:
    """
    Return ``{heading.strip(): body}`` for every section at the given heading level.

    Args:
        content (str): Full markdown text.
        level (int): Heading depth (1 for ``#``, 2 for ``##``, etc.).

    Returns:
        dict[str, str]: Heading-to-body map. Later sections with the same
        heading clobber earlier ones — by design, since duplicate headings
        in a single doc are an authoring bug.

    Example:
        >>> extract_section_map("## A\\nbody", 2)
        {'A': 'body'}
    """
    return {name.strip(): body for name, body in extract_md_sections(content, level)}


# Back-compat alias retained for callers that imported the private name.
_extract_bullet_items = extract_bullet_items


def extract_md_body(content: str) -> str:
    """
    Strip a YAML frontmatter block (``---ed ... ---``) and return the markdown body.

    Args:
        content (str): Full markdown including optional frontmatter.

    Returns:
        str: Body with leading newlines trimmed; the unchanged input if no
        frontmatter is present.

    Example:
        >>> extract_md_body("---\\nkey: val\\n---\\n# Title")
        '# Title'
    """
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return content


_BOLD_METADATA_PATTERN = re.compile(r"^\*\*([^*:]+?):\*\*\s*(.*)$")


def extract_bold_metadata(content: str) -> dict[str, str]:
    """
    Parse bold-label metadata rows (``**Key:** value``) into a dict.

    Values are stripped of surrounding whitespace and backticks; placeholders
    like ``[your project]`` or ``<TBD>`` are returned as-is so callers can flag
    them as un-filled-in.

    Args:
        content (str): Markdown text containing bold metadata lines.

    Returns:
        dict[str, str]: ``{label: value}`` for every recognized line.

    Example:
        >>> extract_bold_metadata("**Status:** Draft\\n**Owner:** Alice")
        {'Status': 'Draft', 'Owner': 'Alice'}
    """
    meta: dict[str, str] = {}
    for line in content.splitlines():
        match = _BOLD_METADATA_PATTERN.match(line.strip())
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip().strip("`")
            meta[key] = value
    return meta
