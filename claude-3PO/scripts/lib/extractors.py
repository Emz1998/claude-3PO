"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

import re
from pathlib import Path
from typing import Literal


def strip_namespace(name: str) -> str:
    """Strip plugin namespace prefix. 'claudeguard:explore' → 'explore'."""
    if ":" in name:
        return name.split(":", 1)[1]
    return name


def extract_skill_name(hook_input: dict) -> str:
    """Extract skill name from hook input, stripping plugin namespace prefix."""
    raw = hook_input.get("tool_input", {}).get("skill", "")
    return strip_namespace(raw)


def extract_agent_name(hook_input: dict, key: str = "subagent_type") -> str:
    """Extract agent name from hook input, stripping plugin namespace prefix.

    PreToolUse sends 'subagent_type' in tool_input.
    SubagentStart sends 'agent_type' at top level.
    """
    if key == "agent_type":
        raw = hook_input.get("agent_type", "")
    else:
        raw = hook_input.get("tool_input", {}).get("subagent_type", "")
    return strip_namespace(raw)


from constants import SCORE_PATTERNS, TABLE_PATTERN


def _extract_last_score(text: str, label: str) -> int | None:
    """Find the last occurrence of a labeled score (e.g. 'Confidence: 85') in text."""
    matches: list[str] = []
    for pattern in SCORE_PATTERNS:
        matches.extend(re.findall(pattern.format(label=label), text, re.IGNORECASE))
    return int(matches[-1]) if matches else None


def extract_scores(
    text: str,
) -> dict[Literal["confidence_score", "quality_score"], int | None]:
    """Extract confidence and quality scores from free-form reviewer text."""
    return {
        "confidence_score": _extract_last_score(text, "confidence"),
        "quality_score": _extract_last_score(text, "quality"),
    }


def extract_verdict(message: str) -> str:
    """Extract Pass/Fail from the last non-empty line of an agent message."""
    lines = [line.strip() for line in message.strip().splitlines() if line.strip()]
    if not lines:
        return "Fail"
    last = lines[-1]
    if last == "Pass":
        return "Pass"
    return "Fail"


def extract_md_sections(md: str, level: int) -> list[tuple[str, str]]:
    """Extract sections from MD file. Returns heading and content."""
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
    """Parse a single markdown table row into a list of cell strings."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells[:cols] if cols is not None else cells


def extract_table(
    md: str,
    rows: int | None = None,
    cols: int | None = None,
) -> list[list[str]]:
    """Extract the first markdown table from text.

    Returns a list of rows, each row a list of cell strings (stripped).
    The separator row (---) is excluded.
    """
    match = _TABLE_PATTERN.search(md)
    if not match:
        return []

    header = _parse_table_row(match.group(1), cols)
    body_lines = match.group(3).strip().splitlines()
    if rows is not None:
        body_lines = body_lines[:rows]

    return [header] + [_parse_table_row(line, cols) for line in body_lines]


def _extract_bullet_items(content: str) -> list[str]:
    """Extract bullet list items (- item) from markdown content."""
    return [
        line.lstrip("- ").strip()
        for line in content.splitlines()
        if line.strip().startswith("- ")
    ]


def _extract_section_bullets(content: str, heading: str) -> list[str]:
    """Extract bullet items from a specific ## section in markdown."""
    sections = extract_md_sections(content, 2)
    for name, body in sections:
        if name.strip() == heading:
            return _extract_bullet_items(body)
    return []


def extract_plan_dependencies(content: str) -> list[str]:
    """Parse ## Dependencies section from plan — extract bullet items as package names."""
    return _extract_section_bullets(content, "Dependencies")


def extract_plan_tasks(content: str) -> list[str]:
    """Parse ## Tasks section from plan — extract bullet items as task subjects."""
    return _extract_section_bullets(content, "Tasks")


def _extract_names_from_specs_table(sections: list[tuple[str, str]]) -> list[str] | None:
    """Extract names from ## Specifications table. Returns None if no section found."""
    for name, body in sections:
        if name.strip() == "Specifications":
            table = extract_table(body)
            if len(table) >= 2:
                return [row[0].strip() for row in table[1:] if row and row[0].strip()]
            return []
    return None


def extract_contract_names(content: str) -> list[str]:
    """Parse contract names from latest-contracts.md.

    Priority: specs table → bullet items → heading names.
    """
    sections = extract_md_sections(content, 2)

    from_table = _extract_names_from_specs_table(sections)
    if from_table is not None:
        return from_table

    bullets = _extract_bullet_items(content)
    if bullets:
        return bullets

    return [name.strip() for name, _ in sections]


def extract_plan_files_to_modify(content: str) -> list[str]:
    """Extract file paths from ## Files to Create/Modify table.

    Expects a markdown table with columns: Action | Path.
    Returns the Path column values.
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


def extract_contract_files(content: str) -> list[str]:
    """Extract file paths from ## Specifications table (File column, index 2)."""
    sections = extract_md_sections(content, 2)
    for name, body in sections:
        if name.strip() == "Specifications":
            table = extract_table(body)
            if len(table) >= 2 and len(table[0]) > 2:
                return [row[2].strip() for row in table[1:] if len(row) > 2 and row[2].strip()]
    return []


_PENDING_KEYWORDS = ("\tpending", "\tqueued", "\tin_progress", "\twaiting")


def _ci_status_from_tabs(output: str) -> str | None:
    """Check tab-delimited status keywords. Returns status or None if inconclusive."""
    if "\tfail" in output:
        return "failed"
    if any(kw in output for kw in _PENDING_KEYWORDS):
        return "pending"
    if "\tpass" in output:
        return "passed"
    return None


def _ci_status_from_summary(output: str) -> str | None:
    """Check summary format (gh pr checks --watch). Returns status or None."""
    if "All checks were successful" in output:
        return "passed"
    if "Some checks were not successful" in output:
        return "failed"
    return None


def extract_ci_status(output: str) -> str:
    """Parse gh pr checks output to determine CI status.

    Returns "passed", "failed", or "pending".
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
    "--skip-explore",
    "--skip-research",
    "--skip-all",
    "--tdd",
    "--reset",
    "--takeover",
]


def _strip_flags_and_ids(text: str) -> str:
    """Remove CLI flags and story IDs from raw instructions."""
    text = re.sub(_STORY_ID_PATTERN, "", text)
    for flag in _BUILD_FLAGS:
        text = text.replace(flag, "")
    return text.strip()


def extract_build_instructions(prompt: str) -> str | None:
    """Extract instructions from a /build prompt. Returns None if not a /build."""
    match = _BUILD_PATTERN.match(prompt.strip())
    if not match:
        return None
    return _strip_flags_and_ids(match.group(1)) or None


def extract_md_body(content: str) -> str:
    """Remove YAML frontmatter (--- ... ---) and return the markdown body."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return content
