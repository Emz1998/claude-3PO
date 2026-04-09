"""Validate sprint.md structure and format against the current schema."""

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


def _safe_int(value: str, default: int = -1) -> int:
    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return default


def _parse_field(block: str, label: str) -> str:
    match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", block)
    return match.group(1).strip() if match else ""


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.split("\n")

    _validate_metadata(lines, errors)
    table_items = _validate_table(lines, errors)
    _validate_detail_sections(content, table_items, errors)

    return errors


def _validate_metadata(lines: list[str], errors: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    required = {
        "**Sprint #:**": "Sprint #",
        "**Milestone:**": "Milestone",
        "**Goal:**": "Goal",
        "**Due Date:**": "Due Date",
    }

    for key, label in required.items():
        found = [line for line in lines if line.startswith(key)]
        if not found:
            errors.append(f"metadata: missing required field '{label}'")
        else:
            value = found[0].split(key)[1].strip()
            metadata[label] = value
            if not value:
                errors.append(f"metadata.{label}: field is empty")

    if "Sprint #" in metadata and metadata["Sprint #"]:
        if _safe_int(metadata["Sprint #"]) < 0:
            errors.append(
                f"metadata.Sprint #: must be a number, got '{metadata['Sprint #']}'"
            )

    if "Due Date" in metadata and metadata["Due Date"]:
        if not re.match(DATE_PATTERN, metadata["Due Date"]):
            errors.append(
                f"metadata.Due Date: must be YYYY-MM-DD, got '{metadata['Due Date']}'"
            )

    return metadata


def _validate_table(lines: list[str], errors: list[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    header_line_idx: int = -1

    for i, line in enumerate(lines):
        if line.startswith("| ID"):
            header_line_idx = i
            break

    if header_line_idx < 0:
        errors.append("table: overview table not found (expected '| ID' header row)")
        return items

    headers = [h.strip() for h in lines[header_line_idx].split("|")[1:-1]]
    for req in REQUIRED_TABLE_HEADERS:
        if req not in headers:
            errors.append(f"table.header: missing required column '{req}'")

    sep_idx = header_line_idx + 1
    if sep_idx >= len(lines) or not lines[sep_idx].startswith("| --"):
        errors.append("table: missing separator row after header")

    for i in range(sep_idx + 1, len(lines)):
        line = lines[i]
        if not line.startswith("|"):
            break
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 6:
            errors.append(
                f"table.row[{i}]: expected at least 6 columns, got {len(cols)}"
            )
            continue

        item_id = cols[0]
        item_type = cols[1]
        title = cols[2]
        points = cols[3]
        status = cols[4]

        row_prefix = f"table.{item_id}"

        if item_type not in VALID_STORY_TYPES:
            errors.append(f"{row_prefix}.type: '{item_type}' not in {VALID_STORY_TYPES}")

        if item_type in ID_PATTERNS:
            if not re.match(ID_PATTERNS[item_type], item_id):
                errors.append(
                    f"{row_prefix}.id: '{item_id}' doesn't match pattern for '{item_type}'"
                )

        if not title:
            errors.append(f"{row_prefix}.title: is empty")

        if _safe_int(points) < 0:
            errors.append(f"{row_prefix}.points: must be a number, got '{points}'")

        if status not in VALID_STORY_STATUSES:
            errors.append(f"{row_prefix}.status: '{status}' not in {VALID_STORY_STATUSES}")

        items.append({
            "id": item_id,
            "type": item_type,
            "title": title,
            "points": points,
            "status": status,
            "line": str(i + 1),
        })

    if not items:
        errors.append("table: no data rows found")

    return items


def _validate_detail_sections(
    content: str, table_items: list[dict[str, str]], errors: list[str]
) -> None:
    for item in table_items:
        item_id = item["id"]
        prefix = f"detail.{item_id}"

        pattern = rf"#### {re.escape(item_id)}:"
        if not re.search(pattern, content):
            errors.append(
                f"{prefix}: missing detail section (expected '#### {item_id}: ...')"
            )
            continue

        block_pattern = (
            rf"#### {re.escape(item_id)}:.*?\n(.*?)(?=\n---|\n#### [A-Z]{{2,}}-\d|\Z)"
        )
        block_match = re.search(block_pattern, content, re.DOTALL)
        if not block_match:
            continue

        block = block_match.group(1)
        _validate_story_section(block, prefix, errors)


def _validate_story_section(block: str, prefix: str, errors: list[str]) -> None:
    # Required story-level fields
    for field in ("Labels", "Points", "Status", "TDD", "Priority", "Is Blocking", "Blocked By"):
        if not _parse_field(block, field):
            errors.append(f"{prefix}: missing **{field}:**")

    # Validate status
    status = _parse_field(block, "Status")
    if status and status not in VALID_STORY_STATUSES:
        errors.append(f"{prefix}.status: '{status}' not in {VALID_STORY_STATUSES}")

    # Validate priority
    priority = _parse_field(block, "Priority")
    if priority and priority not in VALID_PRIORITIES:
        errors.append(f"{prefix}.priority: '{priority}' not in {VALID_PRIORITIES}")

    # Validate TDD
    tdd = _parse_field(block, "TDD").lower()
    if tdd and tdd not in ("true", "false"):
        errors.append(f"{prefix}.tdd: must be 'true' or 'false', got '{tdd}'")

    # Validate dates if present
    for date_field in ("Start Date", "Target Date"):
        val = _parse_field(block, date_field)
        if val and val != "empty" and not re.match(DATE_PATTERN, val):
            errors.append(f"{prefix}.{date_field}: must be YYYY-MM-DD, got '{val}'")

    # Acceptance criteria
    if not re.search(r"\*\*Acceptance Criteria", block):
        errors.append(f"{prefix}: missing **Acceptance Criteria:** section")

    # Tasks section
    task_ids = re.findall(r"- \*\*T-(\d+):\*\*", block)
    if not task_ids:
        errors.append(f"{prefix}: no tasks found (expected '- **T-NNN:** ...')")
        return

    for task_num in task_ids:
        task_id = f"T-{task_num}"
        tp = f"{prefix}.{task_id}"

        task_pattern = rf"- \*\*{re.escape(task_id)}:\*\*(.*?)(?=\n- \*\*T-\d+:\*\*|\n---|\n####|\Z)"
        task_match = re.search(task_pattern, block, re.DOTALL)
        if not task_match:
            continue

        task_block = task_match.group(1)
        _validate_task_section(task_block, tp, errors)


def _validate_task_section(block: str, prefix: str, errors: list[str]) -> None:
    for field in ("Description", "Status", "Priority", "Complexity", "Labels", "Blocked by"):
        if not _parse_field(block, field):
            errors.append(f"{prefix}: missing **{field}:**")

    status = _parse_field(block, "Status")
    if status and status not in VALID_TASK_STATUSES:
        errors.append(f"{prefix}.status: '{status}' not in {VALID_TASK_STATUSES}")

    priority = _parse_field(block, "Priority")
    if priority and priority not in VALID_PRIORITIES:
        errors.append(f"{prefix}.priority: '{priority}' not in {VALID_PRIORITIES}")

    complexity = _parse_field(block, "Complexity")
    if complexity and complexity not in VALID_COMPLEXITIES:
        errors.append(f"{prefix}.complexity: '{complexity}' not in {VALID_COMPLEXITIES}")

    for date_field in ("Start date", "Target date"):
        val = _parse_field(block, date_field)
        if val and val != "empty" and not re.match(DATE_PATTERN, val):
            errors.append(f"{prefix}.{date_field}: must be YYYY-MM-DD, got '{val}'")

    ac_items = re.findall(r"- \[[ x]\] (.+)", block)
    if not ac_items:
        errors.append(f"{prefix}: no acceptance criteria checklist items found")
