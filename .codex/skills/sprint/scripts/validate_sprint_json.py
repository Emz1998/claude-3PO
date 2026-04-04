#!/usr/bin/env python3
"""Validate sprint JSON against the sample_structure.json schema."""

import json
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


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    _validate_root(data, errors)
    if "items" in data and isinstance(data["items"], list):
        all_item_ids = {
            item.get("id") for item in data["items"] if isinstance(item, dict)
        }
        all_task_ids = set()
        for item in data["items"]:
            if isinstance(item, dict) and isinstance(item.get("tasks"), list):
                for task in item["tasks"]:
                    if isinstance(task, dict):
                        all_task_ids.add(task.get("id"))

        for i, item in enumerate(data["items"]):
            prefix = f"items[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix}: expected object, got {type(item).__name__}")
                continue
            _validate_item(item, prefix, errors, all_item_ids, all_task_ids)

        _validate_points(data, errors)
    return errors


def _validate_root(data: dict, errors: list[str]):
    _require_field(data, "project", str, "root", errors)
    _require_field(data, "sprint", int, "root", errors)
    _require_field(data, "goal", str, "root", errors)
    _require_field(data, "totalPoints", int, "root", errors)
    _require_field(data, "completedPoints", int, "root", errors)
    _require_field(data, "progress", (int, float), "root", errors)

    # dates
    if "dates" not in data:
        errors.append("root: missing required field 'dates'")
    elif not isinstance(data["dates"], dict):
        errors.append("root.dates: expected object")
    else:
        for key in ("start", "end"):
            val = data["dates"].get(key)
            if val is None:
                errors.append(f"root.dates: missing '{key}'")
            elif not isinstance(val, str) or not re.match(DATE_PATTERN, val):
                errors.append(
                    f"root.dates.{key}: must be YYYY-MM-DD format, got '{val}'"
                )

    # capacity
    if "capacity" not in data:
        errors.append("root: missing required field 'capacity'")
    elif not isinstance(data["capacity"], dict):
        errors.append("root.capacity: expected object")
    else:
        _require_field(data["capacity"], "hours", int, "root.capacity", errors)
        _require_field(data["capacity"], "weeks", int, "root.capacity", errors)

    # items
    if "items" not in data:
        errors.append("root: missing required field 'items'")
    elif not isinstance(data["items"], list):
        errors.append("root.items: expected array")


def _validate_item(
    item: dict, prefix: str, errors: list[str], all_item_ids: set, all_task_ids: set
):
    _require_field(item, "id", str, prefix, errors)
    _require_field(item, "type", str, prefix, errors)
    _require_field(item, "title", str, prefix, errors)
    _require_field(item, "points", int, prefix, errors)
    _require_field(item, "status", str, prefix, errors)

    # epic can be string or null
    if "epic" not in item:
        errors.append(f"{prefix}: missing required field 'epic'")
    elif item["epic"] is not None and not isinstance(item["epic"], str):
        errors.append(f"{prefix}.epic: must be string or null")

    item_type = item.get("type")
    item_id = item.get("id", "")

    # type validation
    if isinstance(item_type, str) and item_type not in VALID_ITEM_TYPES:
        errors.append(f"{prefix}.type: '{item_type}' not in {VALID_ITEM_TYPES}")

    # id pattern validation
    if (
        isinstance(item_type, str)
        and item_type in ID_PATTERNS
        and isinstance(item_id, str)
    ):
        if not re.match(ID_PATTERNS[item_type], item_id):
            errors.append(
                f"{prefix}.id: '{item_id}' does not match pattern for type '{item_type}'"
            )

    # status validation
    status = item.get("status")
    if isinstance(status, str) and status not in VALID_STATUSES:
        errors.append(f"{prefix}.status: '{status}' not in {VALID_STATUSES}")

    # dependsOn / blockedBy
    _validate_id_refs(item, "dependsOn", prefix, errors, all_item_ids)
    _validate_id_refs(item, "blockedBy", prefix, errors, all_item_ids)

    # type-specific validation
    if item_type == "Spike":
        _validate_spike(item, prefix, errors)
    else:
        _validate_story(item, prefix, errors, all_task_ids)


def _validate_spike(item: dict, prefix: str, errors: list[str]):
    _require_field(item, "timebox", str, prefix, errors)
    if "deliverables" not in item:
        errors.append(f"{prefix}: missing required field 'deliverables'")
    elif not isinstance(item["deliverables"], list):
        errors.append(f"{prefix}.deliverables: expected array")
    elif not all(isinstance(d, str) for d in item["deliverables"]):
        errors.append(f"{prefix}.deliverables: all entries must be strings")


def _validate_story(item: dict, prefix: str, errors: list[str], all_task_ids: set):
    # priority
    priority = item.get("priority")
    if priority is None:
        errors.append(f"{prefix}: missing required field 'priority'")
    elif isinstance(priority, str) and priority not in VALID_PRIORITIES:
        errors.append(f"{prefix}.priority: '{priority}' not in {VALID_PRIORITIES}")

    # tasks
    if "tasks" not in item:
        errors.append(f"{prefix}: missing required field 'tasks'")
    elif not isinstance(item["tasks"], list):
        errors.append(f"{prefix}.tasks: expected array")
    else:
        for j, task in enumerate(item["tasks"]):
            tp = f"{prefix}.tasks[{j}]"
            if not isinstance(task, dict):
                errors.append(f"{tp}: expected object")
                continue
            _validate_task(task, tp, errors, all_task_ids)


def _validate_task(task: dict, prefix: str, errors: list[str], all_task_ids: set):
    _require_field(task, "id", str, prefix, errors)
    _require_field(task, "title", str, prefix, errors)
    _require_field(task, "status", str, prefix, errors)
    _require_field(task, "complexity", str, prefix, errors)

    task_id = task.get("id", "")
    if isinstance(task_id, str) and not re.match(TASK_ID_PATTERN, task_id):
        errors.append(f"{prefix}.id: '{task_id}' does not match pattern T-NNN")

    status = task.get("status")
    if isinstance(status, str) and status not in VALID_STATUSES:
        errors.append(f"{prefix}.status: '{status}' not in {VALID_STATUSES}")

    complexity = task.get("complexity")
    if isinstance(complexity, str) and complexity not in VALID_COMPLEXITIES:
        errors.append(
            f"{prefix}.complexity: '{complexity}' not in {VALID_COMPLEXITIES}"
        )

    _validate_id_refs(task, "dependsOn", prefix, errors, all_task_ids)
    _validate_loop_field(task, "qaLoops", prefix, errors)
    _validate_loop_field(task, "codeReviewLoops", prefix, errors)


def _validate_loop_field(obj: dict, field: str, prefix: str, errors: list[str]):
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
        return
    val = obj[field]
    if (
        not isinstance(val, list)
        or len(val) != 2
        or not all(isinstance(v, int) for v in val)
    ):
        errors.append(f"{prefix}.{field}: must be [current, max] array of 2 integers")
    elif val[0] < 0 or val[1] < 0:
        errors.append(f"{prefix}.{field}: values must be non-negative")
    elif val[0] > val[1]:
        errors.append(f"{prefix}.{field}: current ({val[0]}) exceeds max ({val[1]})")


def _validate_id_refs(
    obj: dict, field: str, prefix: str, errors: list[str], valid_ids: set
):
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
        return
    val = obj[field]
    if not isinstance(val, list):
        errors.append(f"{prefix}.{field}: expected array")
        return
    for ref in val:
        if not isinstance(ref, str):
            errors.append(f"{prefix}.{field}: all entries must be strings")
            break
        if ref not in valid_ids:
            errors.append(f"{prefix}.{field}: '{ref}' references unknown ID")


def _validate_points(data: dict, errors: list[str]):
    items = data.get("items", [])
    total = data.get("totalPoints")
    completed = data.get("completedPoints")
    progress = data.get("progress")

    actual_total = sum(i.get("points", 0) for i in items if isinstance(i, dict))
    if isinstance(total, int) and total != actual_total:
        errors.append(
            f"root.totalPoints: declared {total} but items sum to {actual_total}"
        )

    done_points = sum(
        i.get("points", 0)
        for i in items
        if isinstance(i, dict) and i.get("status") == "Done"
    )
    if isinstance(completed, int) and completed != done_points:
        errors.append(
            f"root.completedPoints: declared {completed} but done items sum to {done_points}"
        )

    if isinstance(progress, (int, float)) and isinstance(total, int) and total > 0:
        expected = round(done_points / total * 100)
        if round(progress) != expected:
            errors.append(f"root.progress: declared {progress} but expected {expected}")


def _require_field(
    obj: dict, field: str, expected_type, prefix: str, errors: list[str]
):
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], expected_type):
        errors.append(
            f"{prefix}.{field}: expected {expected_type.__name__ if isinstance(expected_type, type) else expected_type}, got {type(obj[field]).__name__}"
        )


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_sprint_json.py <path/to/sprint.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1]).resolve()
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    errors = validate(data)

    if errors:
        print(f"FAIL - {len(errors)} error(s) found:\n")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS - sprint JSON is valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
