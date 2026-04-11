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


def extract_scores(
    text: str,
) -> dict[Literal["confidence_score", "quality_score"], int | None]:
    """Extract confidence and quality scores from free-form reviewer text."""
    confidence = None
    quality = None

    def _last_score(label: str) -> int | None:
        patterns = [
            rf"{label}\s*(?:score|rating)?\s*(?:\*\*)?\s*[:=\-]?\s*(?:\*\*)?\s*(\d+)(?:\s*/\s*100)?",
            rf"{label}\s*(?:score|rating)?\s+(?:is\s+)?(?:\*\*)?\s*(\d+)(?:\s*/\s*100)?",
        ]
        matches: list[str] = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        if not matches:
            return None
        return int(matches[-1])

    confidence = _last_score("confidence")
    quality = _last_score("quality")
    return {"confidence_score": confidence, "quality_score": quality}


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


def extract_table(
    md: str,
    rows: int | None = None,
    cols: int | None = None,
) -> list[list[str]]:
    """Extract the first markdown table from text.

    Returns a list of rows, each row a list of cell strings (stripped).
    The separator row (---) is excluded.

    Args:
        md:   markdown text containing a table
        rows: if set, return only the first N data rows (header excluded)
        cols: if set, return only the first N columns
    """
    table_match = re.search(
        r"^(\|.+\|[ \t]*\n)(\|[ \t]*[-:]+.*\|[ \t]*\n)((?:\|.+\|[ \t]*\n?)*)",
        md,
        re.MULTILINE,
    )
    if not table_match:
        return []

    def _parse_row(line: str) -> list[str]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        return cells[:cols] if cols is not None else cells

    header = _parse_row(table_match.group(1))
    body_lines = table_match.group(3).strip().splitlines()
    if rows is not None:
        body_lines = body_lines[:rows]
    body = [_parse_row(line) for line in body_lines]

    return [header] + body


def extract_ci_status(output: str) -> str:
    """Parse gh pr checks output to determine CI status.

    Returns "passed", "failed", or "pending".

    gh pr checks output format: "name\\tstatus\\tduration\\turl\\t" per line.
    Status values: pass, fail, pending, queued, in_progress, etc.
    Uses simple tab-delimited keyword search — no column-position dependency.
    """
    if not output or not output.strip():
        return "pending"

    # Any line with a fail status → failed
    if "\tfail" in output:
        return "failed"

    # Any line with pending/queued/in_progress → still pending
    if (
        "\tpending" in output
        or "\tqueued" in output
        or "\tin_progress" in output
        or "\twaiting" in output
    ):
        return "pending"

    # If we see pass statuses and nothing failed/pending → passed
    if "\tpass" in output:
        return "passed"

    # Summary format fallback (gh pr checks --watch)
    if "All checks were successful" in output:
        return "passed"
    if "Some checks were not successful" in output:
        return "failed"

    return "pending"
