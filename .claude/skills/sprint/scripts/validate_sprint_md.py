#!/usr/bin/env python3
"""Validate sprint.md structure and format."""

import re
import sys
from pathlib import Path

VALID_STATUSES = {"Todo", "In Progress", "Done", "Blocked"}
VALID_PRIORITIES = {"Must", "Should", "Could", "Won't"}
VALID_COMPLEXITIES = {"S", "M", "L", "XL"}
VALID_ITEM_TYPES = {"Spike", "Tech", "Bug", "User"}

ID_PATTERNS = {
    "Spike": r"^SK-\d+$",
    "Tech": r"^TS-\d+$",
    "Bug": r"^BG-\d+$",
    "User": r"^US-\d+$",
}
TASK_ID_PATTERN = r"^T-\d+$"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

REQUIRED_TABLE_HEADERS = [
    "ID",
    "Type",
    "Epic",
    "Title",
    "Points",
    "Status",
    "Depends On",
]


def _safe_int(value: str, default: int = -1) -> int:
    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return default


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.split("\n")

    metadata = _validate_metadata(lines, errors)
    table_items = _validate_table(lines, errors)
    _validate_detail_sections(content, table_items, errors)
    _validate_points_sum(metadata, table_items, errors)
    _validate_dependency_refs(table_items, errors)

    return errors


def _validate_metadata(lines: list[str], errors: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    required = {
        "**Project:**": "Project",
        "**Sprint #:**": "Sprint #",
        "**Goal:**": "Goal",
        "**Dates:**": "Dates",
        "**Capacity:**": "Capacity",
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

    # Validate Sprint # is numeric
    if "Sprint #" in metadata and metadata["Sprint #"]:
        if _safe_int(metadata["Sprint #"]) < 0:
            errors.append(
                f"metadata.Sprint #: must be a number, got '{metadata['Sprint #']}'"
            )

    # Validate Dates format
    if "Dates" in metadata and metadata["Dates"]:
        parts = [d.strip() for d in re.split(r"→|->|to", metadata["Dates"])]
        if len(parts) < 2:
            errors.append(
                "metadata.Dates: must contain start and end separated by arrow or 'to'"
            )
        else:
            if not re.match(DATE_PATTERN, parts[0]):
                errors.append(
                    f"metadata.Dates.start: must be YYYY-MM-DD, got '{parts[0]}'"
                )
            if not re.match(DATE_PATTERN, parts[1]):
                errors.append(
                    f"metadata.Dates.end: must be YYYY-MM-DD, got '{parts[1]}'"
                )

    # Validate Capacity has hours
    if "Capacity" in metadata and metadata["Capacity"]:
        if not re.search(r"\d+\s*hours", metadata["Capacity"]):
            errors.append("metadata.Capacity: must include hours (e.g. '80 hours')")

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

    # Validate header columns
    headers = [h.strip() for h in lines[header_line_idx].split("|")[1:-1]]
    for req in REQUIRED_TABLE_HEADERS:
        if req not in headers:
            errors.append(f"table.header: missing required column '{req}'")

    # Validate separator row
    sep_idx = header_line_idx + 1
    if sep_idx >= len(lines) or not lines[sep_idx].startswith("| --"):
        errors.append("table: missing separator row after header")

    # Validate data rows
    total_points_line = [line for line in lines if line.startswith("**Total Points:**")]
    has_total = len(total_points_line) > 0

    for i in range(sep_idx + 1, len(lines)):
        line = lines[i]
        if not line.startswith("|"):
            break
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 7:
            errors.append(
                f"table.row[{i}]: expected at least 7 columns, got {len(cols)}"
            )
            continue

        item_id = cols[0]
        item_type = cols[1]
        title = cols[3]
        points = cols[4]
        status = cols[5]

        row_prefix = f"table.{item_id}"

        # Validate type
        if item_type not in VALID_ITEM_TYPES:
            errors.append(f"{row_prefix}.type: '{item_type}' not in {VALID_ITEM_TYPES}")

        # Validate ID pattern matches type
        if item_type in ID_PATTERNS:
            if not re.match(ID_PATTERNS[item_type], item_id):
                errors.append(
                    f"{row_prefix}.id: '{item_id}' doesn't match pattern for '{item_type}'"
                )

        # Validate title not empty
        if not title:
            errors.append(f"{row_prefix}.title: is empty")

        # Validate points is numeric
        if _safe_int(points) < 0:
            errors.append(f"{row_prefix}.points: must be a number, got '{points}'")

        # Validate status
        if status not in VALID_STATUSES:
            errors.append(f"{row_prefix}.status: '{status}' not in {VALID_STATUSES}")

        items.append(
            {
                "id": item_id,
                "type": item_type,
                "title": title,
                "points": points,
                "status": status,
                "line": str(i + 1),
            }
        )

    if not items:
        errors.append("table: no data rows found")

    if not has_total:
        errors.append("table: missing **Total Points:** after overview table")

    return items


def _validate_detail_sections(
    content: str, table_items: list[dict[str, str]], errors: list[str]
) -> None:
    for item in table_items:
        item_id = item["id"]
        item_type = item["type"]
        prefix = f"detail.{item_id}"

        # Check detail section exists
        pattern = rf"#### {re.escape(item_id)}:"
        if not re.search(pattern, content):
            errors.append(
                f"{prefix}: missing detail section (expected '#### {item_id}: ...')"
            )
            continue

        # Extract block
        block_pattern = (
            rf"#### {re.escape(item_id)}:.*?\n(.*?)(?=\n---|\n#### [A-Z]{{2,}}-\d|\Z)"
        )
        block_match = re.search(block_pattern, content, re.DOTALL)
        if not block_match:
            continue

        block = block_match.group(1)

        if item_type == "Spike":
            _validate_spike_section(block, prefix, errors)
        else:
            _validate_story_section(block, prefix, item_id, errors)


def _validate_spike_section(block: str, prefix: str, errors: list[str]) -> None:
    # Required fields
    if not re.search(r"\*\*Status:\*\*", block):
        errors.append(f"{prefix}: missing **Status:**")
    else:
        status_match = re.search(r"\*\*Status:\*\*\s*(.+)", block)
        if status_match and status_match.group(1).strip() not in VALID_STATUSES:
            errors.append(
                f"{prefix}.status: '{status_match.group(1).strip()}' not in {VALID_STATUSES}"
            )

    if not re.search(r"\*\*Timebox:\*\*", block):
        errors.append(f"{prefix}: missing **Timebox:**")

    if not re.search(r"\*\*Deliverable", block):
        errors.append(f"{prefix}: missing **Deliverable:** section")

    deliverables = re.findall(r"- \[[ x]\] (.+)", block)
    if not deliverables:
        errors.append(
            f"{prefix}: no deliverable checklist items found (expected '- [ ] ...')"
        )


def _validate_story_section(
    block: str, prefix: str, _story_id: str, errors: list[str]
) -> None:
    # Required fields
    if not re.search(r"\*\*Priority:\*\*", block):
        errors.append(f"{prefix}: missing **Priority:**")
    else:
        pri_match = re.search(r"\*\*Priority:\*\*\s*(.+)", block)
        if pri_match and pri_match.group(1).strip() not in VALID_PRIORITIES:
            errors.append(
                f"{prefix}.priority: '{pri_match.group(1).strip()}' not in {VALID_PRIORITIES}"
            )

    if not re.search(r"\*\*Status:\*\*", block):
        errors.append(f"{prefix}: missing **Status:**")

    if not re.search(r"\*\*Story Points:\*\*", block):
        errors.append(f"{prefix}: missing **Story Points:**")

    # Acceptance criteria
    if not re.search(r"\*\*Acceptance Criteria", block):
        errors.append(
            f"{prefix}: missing **Acceptance Criteria (Story Level):** section"
        )

    # Tasks section
    task_ids = re.findall(r"- \*\*T-(\d+):\*\*", block)
    if not task_ids:
        errors.append(f"{prefix}: no tasks found (expected '- **T-NNN:** ...')")
        return

    for task_num in task_ids:
        task_id = f"T-{task_num}"
        tp = f"{prefix}.{task_id}"

        # Extract task block
        task_pattern = rf"- \*\*{re.escape(task_id)}:\*\*(.*?)(?=\n- \*\*T-\d+:\*\*|\n---|\n####|\Z)"
        task_match = re.search(task_pattern, block, re.DOTALL)
        if not task_match:
            continue

        task_block = task_match.group(1)

        if not re.search(r"\*\*Status:\*\*", task_block):
            errors.append(f"{tp}: missing **Status:**")
        else:
            st_match = re.search(r"\*\*Status:\*\*\s*(.+)", task_block)
            if st_match and st_match.group(1).strip() not in VALID_STATUSES:
                errors.append(
                    f"{tp}.status: '{st_match.group(1).strip()}' not in {VALID_STATUSES}"
                )

        if not re.search(r"\*\*Complexity:\*\*", task_block):
            errors.append(f"{tp}: missing **Complexity:**")
        else:
            cx_match = re.search(r"\*\*Complexity:\*\*\s*(.+)", task_block)
            if cx_match and cx_match.group(1).strip() not in VALID_COMPLEXITIES:
                errors.append(
                    f"{tp}.complexity: '{cx_match.group(1).strip()}' not in {VALID_COMPLEXITIES}"
                )

        if not re.search(r"\*\*Depends on:\*\*", task_block):
            errors.append(f"{tp}: missing **Depends on:**")

        if not re.search(r"\*\*QA loops:\*\*", task_block):
            errors.append(f"{tp}: missing **QA loops:**")

        if not re.search(r"\*\*Code Review loops:\*\*", task_block):
            errors.append(f"{tp}: missing **Code Review loops:**")

        # Task-level acceptance criteria
        if not re.search(r"\*\*Acceptance Criteria \(Task Level\):\*\*", task_block):
            errors.append(f"{tp}: missing **Acceptance Criteria (Task Level):**")


def _validate_points_sum(
    metadata: dict[str, str], table_items: list[dict[str, str]], errors: list[str]
) -> None:
    if not table_items:
        return

    actual_sum = sum(_safe_int(item["points"], 0) for item in table_items)

    if actual_sum == 0:
        errors.append("points: all table items have 0 points")


def _validate_dependency_refs(
    table_items: list[dict[str, str]], _errors: list[str]
) -> None:
    # Placeholder - dependency ref validation is limited at md level
    # since we'd need to re-parse full content for task-level deps.
    # The JSON validator handles cross-reference checks.
    _ = {item["id"] for item in table_items}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python validate_sprint_md.py <path/to/sprint.md>")
        sys.exit(1)

    md_path = Path(sys.argv[1]).resolve()
    if not md_path.exists():
        print(f"Error: {md_path} not found")
        sys.exit(1)

    content = md_path.read_text(encoding="utf-8")
    errors = validate(content)

    if errors:
        print(f"FAIL - {len(errors)} error(s) found:\n")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS - sprint.md structure is valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
