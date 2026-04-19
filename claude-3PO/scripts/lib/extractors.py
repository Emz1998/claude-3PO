"""extractors.py — Pure extraction helpers for hook payloads and markdown text.

The functions here parse stuff out of strings — agent hook inputs, scoring
text, markdown sections/tables/bullets, ``gh pr checks`` output, ``/build``
prompts. They never touch the filesystem and never raise on malformed input
(returning empty/``None`` instead) so guards and recorders can call them
freely without try/except scaffolding.
"""

import re
from pathlib import Path
from typing import Literal


def strip_namespace(name: str) -> str:
    """Strip a plugin namespace prefix (``'claudeguard:explore' -> 'explore'``).

    Example:
        >>> strip_namespace("claudeguard:explore")
        'explore'
        >>> strip_namespace("explore")
        'explore'
    """
    if ":" in name:
        return name.split(":", 1)[1]
    return name


def extract_skill_name(hook_input: dict) -> str:
    """
    Extract the skill name from a hook payload, dropping any plugin namespace.

    Args:
        hook_input (dict): Raw hook event payload (must have ``tool_input.skill``).

    Returns:
        str: The bare skill name (e.g. ``"explore"``), or ``""`` if absent.

    Example:
        >>> extract_skill_name({"tool_input": {"skill": "claudeguard:explore"}})
        'explore'
    """
    raw = hook_input.get("tool_input", {}).get("skill", "")
    return strip_namespace(raw)


def extract_agent_name(hook_input: dict, key: str = "subagent_type") -> str:
    """
    Extract an agent name from a hook payload, dropping any plugin namespace.

    Two hook events carry the agent name at different paths: ``PreToolUse``
    sends ``tool_input.subagent_type``, while ``SubagentStart`` sends
    ``agent_type`` at the top level. The ``key`` argument selects which schema
    to read.

    Args:
        hook_input (dict): Raw hook event payload.
        key (str): Either ``"subagent_type"`` (default, PreToolUse) or
            ``"agent_type"`` (SubagentStart).

    Returns:
        str: The bare agent name, or ``""`` if absent.

    Example:
        >>> extract_agent_name({"tool_input": {"subagent_type": "QASpecialist"}})
        'QASpecialist'
    """
    if key == "agent_type":
        raw = hook_input.get("agent_type", "")
    else:
        raw = hook_input.get("tool_input", {}).get("subagent_type", "")
    return strip_namespace(raw)


from constants import SCORE_PATTERNS, TABLE_PATTERN


def _extract_last_score(text: str, label: str) -> int | None:
    """Find the last labeled score (e.g. ``Confidence: 85``) in *text*; ``None`` if missing.

    Example:
        >>> _extract_last_score("Confidence: 70 then Confidence: 90", "confidence")
        90
        >>> _extract_last_score("nothing here", "confidence") is None
        True
    """
    matches: list[str] = []
    for pattern in SCORE_PATTERNS:
        matches.extend(re.findall(pattern.format(label=label), text, re.IGNORECASE))
    return int(matches[-1]) if matches else None


def extract_scores(
    text: str,
) -> dict[Literal["confidence_score", "quality_score"], int | None]:
    """
    Extract the latest confidence and quality scores from reviewer text.

    Reviewers may state intermediate scores while reasoning, so the *last*
    occurrence wins — that's the reviewer's final answer.

    Args:
        text (str): Free-form reviewer message body.

    Returns:
        dict[Literal["confidence_score", "quality_score"], int | None]: Both
        keys always present; values are ``None`` when no score was found.

    Example:
        >>> extract_scores("Confidence: 85\\nQuality: 90")
        {'confidence_score': 85, 'quality_score': 90}
    """
    return {
        "confidence_score": _extract_last_score(text, "confidence"),
        "quality_score": _extract_last_score(text, "quality"),
    }


def extract_verdict(message: str) -> str:
    """
    Extract a Pass/Fail verdict from the last non-empty line of *message*.

    Reviewers are required to put their final verdict on the last line. Anything
    that isn't exactly ``"Pass"`` is treated as a failure (fail-closed) so an
    ambiguous or malformed verdict can't accidentally let work through.

    Args:
        message (str): Full reviewer message.

    Returns:
        str: ``"Pass"`` or ``"Fail"``.

    Example:
        >>> extract_verdict("Looks good.\\nPass")
        'Pass'
        >>> extract_verdict("Needs work.\\nReject")
        'Fail'
    """
    lines = [line.strip() for line in message.strip().splitlines() if line.strip()]
    if not lines:
        return "Fail"
    last = lines[-1]
    if last == "Pass":
        return "Pass"
    return "Fail"


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


def _extract_section_bullets(content: str, heading: str) -> list[str]:
    """Extract bullets from the ``## heading`` section in *content*.

    Example:
        >>> _extract_section_bullets("## Tasks\\n- a\\n- b", "Tasks")
        ['a', 'b']
    """
    return extract_bullet_items(extract_section_map(content, 2).get(heading, ""))


def extract_plan_dependencies(content: str) -> list[str]:
    """
    Parse the ``## Dependencies`` bullet list from a plan file.

    Args:
        content (str): Full plan markdown.

    Returns:
        list[str]: Package names; empty if the section is missing.

    Example:
        >>> extract_plan_dependencies("## Dependencies\\n- requests\\n- pytest")
        ['requests', 'pytest']
    """
    return _extract_section_bullets(content, "Dependencies")


def extract_plan_tasks(content: str) -> list[str]:
    """
    Parse the ``## Tasks`` bullet list from a plan file.

    Args:
        content (str): Full plan markdown.

    Returns:
        list[str]: Task subjects; empty if the section is missing.

    Example:
        >>> extract_plan_tasks("## Tasks\\n- Write tests\\n- Implement")
        ['Write tests', 'Implement']
    """
    return _extract_section_bullets(content, "Tasks")


def extract_plan_files_to_modify(content: str) -> list[str]:
    """
    Extract file paths from the plan's ``Files to Create/Modify`` table.

    Accepts either ``Files to Create/Modify`` or the legacy ``Files to Modify``
    heading. Expects an ``Action | Path`` table and returns the Path column.

    Args:
        content (str): Full plan markdown.

    Returns:
        list[str]: File paths in table order; empty if the section or table
        is missing.

    Example:
        >>> md = "## Files to Modify\\n| Action | Path |\\n|---|---|\\n| edit | a.py |"
        >>> extract_plan_files_to_modify(md)
        ['a.py']
    """
    sections = extract_md_sections(content, 2)
    for name, body in sections:
        if name.strip() in ("Files to Create/Modify", "Files to Modify"):
            table = extract_table(body)
            if len(table) < 2:  # header + at least 1 data row
                return []
            # Skip header row, extract Path column (index 1)
            return [row[1].strip() for row in table[1:] if len(row) > 1 and row[1].strip()]
    return []


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


# ---------------------------------------------------------------------------
# Build prompt extraction
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
