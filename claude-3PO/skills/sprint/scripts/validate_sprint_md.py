"""Validate sprint.md structure and format against the current schema.

Checks metadata fields, overview table structure, detail section presence,
story/task field values (statuses, priorities, complexities, dates), and
acceptance criteria. Returns a list of human-readable error strings.
"""

import re

VALID_STORY_STATUSES = {"Ready", "In Progress", "Done", "Blocked"}
VALID_TASK_STATUSES = {"Backlog", "In Progress", "In Review", "Done", "Blocked"}
VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_COMPLEXITIES = {"S", "M", "L"}
VALID_STORY_TYPES = {"Story", "Tech", "Bug", "Spike"}

ID_PATTERNS = {
    "Spike": r"^SK-\d+$",
    "Tech": r"^TS-\d+$",
    "Bug": r"^BG-\d+$",
    "Story": r"^US-\d+$",
}
TASK_ID_PATTERN = r"^T-\d+$"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

REQUIRED_TABLE_HEADERS = ["ID", "Type", "Title", "Points", "Status", "Blocked By"]

_REQUIRED_METADATA = {
    "**Sprint #:**": "Sprint #",
    "**Milestone:**": "Milestone",
    "**Goal:**": "Goal",
    "**Due Date:**": "Due Date",
}


def _safe_int(value: str, default: int = -1) -> int:
    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return default


def _parse_field(block: str, label: str) -> str:
    match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", block)
    return match.group(1).strip() if match else ""


def _validate_enum(value: str, valid: set[str], prefix: str, field: str, errors: list[str]) -> None:
    """Check a string value is in the allowed set."""
    if value and value not in valid:
        errors.append(f"{prefix}.{field}: '{value}' not in {valid}")


def _validate_date(value: str, prefix: str, field: str, errors: list[str]) -> None:
    """Check a date string matches YYYY-MM-DD if non-empty."""
    if value and value != "empty" and not re.match(DATE_PATTERN, value):
        errors.append(f"{prefix}.{field}: must be YYYY-MM-DD, got '{value}'")


# ── Entry point ──────────────────────────────────────────────────────────────


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.split("\n")

    _validate_metadata(lines, errors)
    table_items = _validate_table(lines, errors)
    _validate_detail_sections(content, table_items, errors)

    return errors


# ── Metadata ─────────────────────────────────────────────────────────────────


def _validate_metadata(lines: list[str], errors: list[str]) -> dict[str, str]:
    metadata = _extract_metadata_fields(lines, errors)
    _validate_metadata_values(metadata, errors)
    return metadata


def _extract_metadata_fields(lines: list[str], errors: list[str]) -> dict[str, str]:
    """Extract metadata values, reporting missing or empty fields."""
    metadata: dict[str, str] = {}
    for key, label in _REQUIRED_METADATA.items():
        found = [line for line in lines if line.startswith(key)]
        if not found:
            errors.append(f"metadata: missing required field '{label}'")
        else:
            value = found[0].split(key)[1].strip()
            metadata[label] = value
            if not value:
                errors.append(f"metadata.{label}: field is empty")
    return metadata


def _validate_metadata_values(metadata: dict[str, str], errors: list[str]) -> None:
    """Validate sprint number and due date formats."""
    if "Sprint #" in metadata and metadata["Sprint #"]:
        if _safe_int(metadata["Sprint #"]) < 0:
            errors.append(f"metadata.Sprint #: must be a number, got '{metadata['Sprint #']}'")

    if "Due Date" in metadata and metadata["Due Date"]:
        if not re.match(DATE_PATTERN, metadata["Due Date"]):
            errors.append(f"metadata.Due Date: must be YYYY-MM-DD, got '{metadata['Due Date']}'")


# ── Overview Table ───────────────────────────────────────────────────────────


def _validate_table(lines: list[str], errors: list[str]) -> list[dict[str, str]]:
    header_idx = _find_table_header(lines)
    if header_idx < 0:
        errors.append("table: overview table not found (expected '| ID' header row)")
        return []

    _validate_table_headers(lines[header_idx], errors)
    _validate_table_separator(lines, header_idx, errors)
    return _validate_table_rows(lines, header_idx + 2, errors)


def _find_table_header(lines: list[str]) -> int:
    """Return the index of the table header row, or -1 if not found."""
    for i, line in enumerate(lines):
        if line.startswith("| ID"):
            return i
    return -1


def _validate_table_headers(header_line: str, errors: list[str]) -> None:
    """Check all required columns are present in the header."""
    headers = [h.strip() for h in header_line.split("|")[1:-1]]
    for req in REQUIRED_TABLE_HEADERS:
        if req not in headers:
            errors.append(f"table.header: missing required column '{req}'")


def _validate_table_separator(lines: list[str], header_idx: int, errors: list[str]) -> None:
    """Check the separator row exists after the header."""
    sep_idx = header_idx + 1
    if sep_idx >= len(lines) or not lines[sep_idx].startswith("| --"):
        errors.append("table: missing separator row after header")


def _validate_table_rows(lines: list[str], start: int, errors: list[str]) -> list[dict[str, str]]:
    """Parse and validate each data row in the overview table."""
    items: list[dict[str, str]] = []
    for i in range(start, len(lines)):
        if not lines[i].startswith("|"):
            break
        row = _parse_table_row(lines[i], i, errors)
        if row:
            items.append(row)

    if not items:
        errors.append("table: no data rows found")
    return items


def _parse_table_row(line: str, line_idx: int, errors: list[str]) -> dict[str, str] | None:
    """Parse a single table row and validate its values."""
    cols = [c.strip() for c in line.split("|")[1:-1]]
    if len(cols) < 6:
        errors.append(f"table.row[{line_idx}]: expected at least 6 columns, got {len(cols)}")
        return None

    item_id, item_type, title, points, status = cols[0], cols[1], cols[2], cols[3], cols[4]
    prefix = f"table.{item_id}"

    _validate_table_row_values(item_id, item_type, title, points, status, prefix, errors)

    return {"id": item_id, "type": item_type, "title": title,
            "points": points, "status": status, "line": str(line_idx + 1)}


def _validate_table_row_values(
    item_id: str, item_type: str, title: str, points: str,
    status: str, prefix: str, errors: list[str],
) -> None:
    """Validate field values for a single table row."""
    _validate_enum(item_type, VALID_STORY_TYPES, prefix, "type", errors)

    if item_type in ID_PATTERNS and not re.match(ID_PATTERNS[item_type], item_id):
        errors.append(f"{prefix}.id: '{item_id}' doesn't match pattern for '{item_type}'")

    if not title:
        errors.append(f"{prefix}.title: is empty")
    if _safe_int(points) < 0:
        errors.append(f"{prefix}.points: must be a number, got '{points}'")

    _validate_enum(status, VALID_STORY_STATUSES, prefix, "status", errors)


# ── Detail Sections ──────────────────────────────────────────────────────────


def _validate_detail_sections(
    content: str, table_items: list[dict[str, str]], errors: list[str],
) -> None:
    """Validate each story's detail section exists and is well-formed."""
    for item in table_items:
        item_id = item["id"]
        prefix = f"detail.{item_id}"
        block = _extract_detail_block(content, item_id, prefix, errors)
        if block is not None:
            _validate_story_section(block, prefix, errors)


def _extract_detail_block(content: str, item_id: str, prefix: str, errors: list[str]) -> str | None:
    """Extract the markdown block for a story's detail section."""
    pattern = rf"#### {re.escape(item_id)}:"
    if not re.search(pattern, content):
        errors.append(f"{prefix}: missing detail section (expected '#### {item_id}: ...')")
        return None

    block_pattern = rf"#### {re.escape(item_id)}:.*?\n(.*?)(?=\n---|\n#### [A-Z]{{2,}}-\d|\Z)"
    block_match = re.search(block_pattern, content, re.DOTALL)
    return block_match.group(1) if block_match else None


# ── Story Section ────────────────────────────────────────────────────────────


def _validate_story_section(block: str, prefix: str, errors: list[str]) -> None:
    _validate_story_required_fields(block, prefix, errors)
    _validate_story_field_values(block, prefix, errors)
    _validate_story_ac_section(block, prefix, errors)
    _validate_story_task_sections(block, prefix, errors)


def _validate_story_required_fields(block: str, prefix: str, errors: list[str]) -> None:
    """Check all required story-level fields are present."""
    for field in ("Labels", "Points", "Status", "TDD", "Priority", "Is Blocking", "Blocked By"):
        if not _parse_field(block, field):
            errors.append(f"{prefix}: missing **{field}:**")


def _validate_story_field_values(block: str, prefix: str, errors: list[str]) -> None:
    """Validate story field values against allowed sets."""
    _validate_enum(_parse_field(block, "Status"), VALID_STORY_STATUSES, prefix, "status", errors)
    _validate_enum(_parse_field(block, "Priority"), VALID_PRIORITIES, prefix, "priority", errors)
    _validate_story_tdd(block, prefix, errors)
    _validate_date(_parse_field(block, "Start Date"), prefix, "Start Date", errors)
    _validate_date(_parse_field(block, "Target Date"), prefix, "Target Date", errors)


def _validate_story_tdd(block: str, prefix: str, errors: list[str]) -> None:
    """Validate TDD field is 'true' or 'false'."""
    tdd = _parse_field(block, "TDD").lower()
    if tdd and tdd not in ("true", "false"):
        errors.append(f"{prefix}.tdd: must be 'true' or 'false', got '{tdd}'")


def _validate_story_ac_section(block: str, prefix: str, errors: list[str]) -> None:
    """Check the Acceptance Criteria section exists."""
    if not re.search(r"\*\*Acceptance Criteria", block):
        errors.append(f"{prefix}: missing **Acceptance Criteria:** section")


def _validate_story_task_sections(block: str, prefix: str, errors: list[str]) -> None:
    """Find and validate each task within a story block."""
    task_ids = re.findall(r"- \*\*T-(\d+):\*\*", block)
    if not task_ids:
        errors.append(f"{prefix}: no tasks found (expected '- **T-NNN:** ...')")
        return

    for task_num in task_ids:
        task_id = f"T-{task_num}"
        task_block = _extract_task_block(block, task_id)
        if task_block is not None:
            _validate_task_section(task_block, f"{prefix}.{task_id}", errors)


def _extract_task_block(block: str, task_id: str) -> str | None:
    """Extract the text block for a single task."""
    pattern = rf"- \*\*{re.escape(task_id)}:\*\*(.*?)(?=\n- \*\*T-\d+:\*\*|\n---|\n####|\Z)"
    match = re.search(pattern, block, re.DOTALL)
    return match.group(1) if match else None


# ── Task Section ─────────────────────────────────────────────────────────────


def _validate_task_section(block: str, prefix: str, errors: list[str]) -> None:
    _validate_task_required_fields(block, prefix, errors)
    _validate_task_field_values(block, prefix, errors)
    _validate_task_ac(block, prefix, errors)


def _validate_task_required_fields(block: str, prefix: str, errors: list[str]) -> None:
    """Check all required task-level fields are present."""
    for field in ("Description", "Status", "Priority", "Complexity", "Labels", "Blocked by"):
        if not _parse_field(block, field):
            errors.append(f"{prefix}: missing **{field}:**")


def _validate_task_field_values(block: str, prefix: str, errors: list[str]) -> None:
    """Validate task field values against allowed sets."""
    _validate_enum(_parse_field(block, "Status"), VALID_TASK_STATUSES, prefix, "status", errors)
    _validate_enum(_parse_field(block, "Priority"), VALID_PRIORITIES, prefix, "priority", errors)
    _validate_enum(_parse_field(block, "Complexity"), VALID_COMPLEXITIES, prefix, "complexity", errors)
    _validate_date(_parse_field(block, "Start date"), prefix, "Start date", errors)
    _validate_date(_parse_field(block, "Target date"), prefix, "Target date", errors)


def _validate_task_ac(block: str, prefix: str, errors: list[str]) -> None:
    """Check task has at least one acceptance criteria item."""
    if not re.findall(r"- \[[ x]\] (.+)", block):
        errors.append(f"{prefix}: no acceptance criteria checklist items found")
