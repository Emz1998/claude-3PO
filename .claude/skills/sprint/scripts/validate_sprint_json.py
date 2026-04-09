"""Validate sprint JSON against the sample_structure.json schema."""

import re

VALID_STORY_STATUSES = {"Ready", "In Progress", "Done", "Blocked"}
VALID_TASK_STATUSES = {
    "Backlog",
    "Ready",
    "In Progress",
    "In Review",
    "Done",
    "Blocked",
}
VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_COMPLEXITIES = {"S", "M", "L"}
VALID_STORY_TYPES = {"User Story", "Technical Story", "Bug", "Spike"}

ID_PATTERNS = {
    "Spike": r"^SK-\d+$",
    "Technical Story": r"^TS-\d+$",
    "Bug": r"^BG-\d+$",
    "User Story": r"^US-\d+$",
}
TASK_ID_PATTERN = r"^T-\d+$"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    _validate_root(data, errors)

    if "stories" in data and isinstance(data["stories"], list):
        all_task_ids: set[str] = set()
        for story in data["stories"]:
            if isinstance(story, dict) and isinstance(story.get("tasks"), list):
                for task in story["tasks"]:
                    if isinstance(task, dict) and isinstance(task.get("id"), str):
                        all_task_ids.add(task["id"])

        for i, story in enumerate(data["stories"]):
            prefix = f"stories[{i}]"
            if not isinstance(story, dict):
                errors.append(f"{prefix}: expected object, got {type(story).__name__}")
                continue
            _validate_story(story, prefix, errors, all_task_ids)

    return errors


def _validate_root(data: dict, errors: list[str]) -> None:
    _require_field(data, "sprint", int, "root", errors)
    _require_field(data, "milestone", str, "root", errors)
    _require_field(data, "description", str, "root", errors)
    _require_field(data, "due_date", str, "root", errors)

    due = data.get("due_date")
    if isinstance(due, str) and due and not re.match(DATE_PATTERN, due):
        errors.append(f"root.due_date: must be YYYY-MM-DD, got '{due}'")

    if "stories" not in data:
        errors.append("root: missing required field 'stories'")
    elif not isinstance(data["stories"], list):
        errors.append("root.stories: expected array")


def _validate_story(
    story: dict,
    prefix: str,
    errors: list[str],
    all_task_ids: set[str],
) -> None:
    _require_field(story, "id", str, prefix, errors)
    _require_field(story, "type", str, prefix, errors)
    _require_field(story, "title", str, prefix, errors)
    _require_field(story, "description", str, prefix, errors)
    _require_field(story, "points", int, prefix, errors)
    _require_field(story, "status", str, prefix, errors)
    _require_field(story, "tdd", bool, prefix, errors)
    _require_field(story, "priority", str, prefix, errors)
    _require_field(story, "milestone", str, prefix, errors)
    _require_list_field(story, "labels", str, prefix, errors)
    _require_list_field(story, "is_blocking", str, prefix, errors)
    _require_list_field(story, "blocked_by", str, prefix, errors)
    _require_list_field(story, "acceptance_criteria", str, prefix, errors)
    _require_field(story, "start_date", str, prefix, errors)
    _require_field(story, "target_date", str, prefix, errors)

    # item_type must be "story"
    if "item_type" in story and story["item_type"] != "story":
        errors.append(
            f"{prefix}.item_type: must be 'story', got '{story['item_type']}'"
        )
    elif "item_type" not in story:
        errors.append(f"{prefix}: missing required field 'item_type'")

    story_type = story.get("type")
    story_id = story.get("id", "")

    if isinstance(story_type, str) and story_type not in VALID_STORY_TYPES:
        errors.append(f"{prefix}.type: '{story_type}' not in {VALID_STORY_TYPES}")

    if (
        isinstance(story_type, str)
        and story_type in ID_PATTERNS
        and isinstance(story_id, str)
    ):
        if not re.match(ID_PATTERNS[story_type], story_id):
            errors.append(
                f"{prefix}.id: '{story_id}' does not match pattern for '{story_type}'"
            )

    status = story.get("status")
    if isinstance(status, str) and status not in VALID_STORY_STATUSES:
        errors.append(f"{prefix}.status: '{status}' not in {VALID_STORY_STATUSES}")

    priority = story.get("priority")
    if isinstance(priority, str) and priority not in VALID_PRIORITIES:
        errors.append(f"{prefix}.priority: '{priority}' not in {VALID_PRIORITIES}")

    # Validate date fields
    for date_field in ("start_date", "target_date"):
        val = story.get(date_field)
        if isinstance(val, str) and val and not re.match(DATE_PATTERN, val):
            errors.append(f"{prefix}.{date_field}: must be YYYY-MM-DD, got '{val}'")

    # Story-level is_blocking/blocked_by can reference stories outside this sprint,
    # so we only validate that entries are strings (already done by _require_list_field)

    # Tasks
    if "tasks" not in story:
        errors.append(f"{prefix}: missing required field 'tasks'")
    elif not isinstance(story["tasks"], list):
        errors.append(f"{prefix}.tasks: expected array")
    else:
        for j, task in enumerate(story["tasks"]):
            tp = f"{prefix}.tasks[{j}]"
            if not isinstance(task, dict):
                errors.append(f"{tp}: expected object")
                continue
            _validate_task(task, tp, errors, all_task_ids)


def _validate_task(
    task: dict, prefix: str, errors: list[str], all_task_ids: set[str]
) -> None:
    _require_field(task, "id", str, prefix, errors)
    _require_field(task, "type", str, prefix, errors)
    _require_field(task, "title", str, prefix, errors)
    _require_field(task, "description", str, prefix, errors)
    _require_field(task, "status", str, prefix, errors)
    _require_field(task, "priority", str, prefix, errors)
    _require_field(task, "complexity", str, prefix, errors)
    _require_field(task, "milestone", str, prefix, errors)
    _require_list_field(task, "labels", str, prefix, errors)
    _require_list_field(task, "is_blocking", str, prefix, errors)
    _require_list_field(task, "blocked_by", str, prefix, errors)
    _require_list_field(task, "acceptance_criteria", str, prefix, errors)
    _require_field(task, "start_date", str, prefix, errors)
    _require_field(task, "target_date", str, prefix, errors)

    # item_type must be "task"
    if "item_type" in task and task["item_type"] != "task":
        errors.append(f"{prefix}.item_type: must be 'task', got '{task['item_type']}'")
    elif "item_type" not in task:
        errors.append(f"{prefix}: missing required field 'item_type'")

    # type must be "task"
    if "type" in task and task["type"] != "task":
        errors.append(f"{prefix}.type: must be 'task', got '{task['type']}'")

    task_id = task.get("id", "")
    if isinstance(task_id, str) and not re.match(TASK_ID_PATTERN, task_id):
        errors.append(f"{prefix}.id: '{task_id}' does not match pattern T-NNN")

    status = task.get("status")
    if isinstance(status, str) and status not in VALID_TASK_STATUSES:
        errors.append(f"{prefix}.status: '{status}' not in {VALID_TASK_STATUSES}")

    priority = task.get("priority")
    if isinstance(priority, str) and priority not in VALID_PRIORITIES:
        errors.append(f"{prefix}.priority: '{priority}' not in {VALID_PRIORITIES}")

    complexity = task.get("complexity")
    if isinstance(complexity, str) and complexity not in VALID_COMPLEXITIES:
        errors.append(
            f"{prefix}.complexity: '{complexity}' not in {VALID_COMPLEXITIES}"
        )

    for date_field in ("start_date", "target_date"):
        val = task.get(date_field)
        if isinstance(val, str) and val and not re.match(DATE_PATTERN, val):
            errors.append(f"{prefix}.{date_field}: must be YYYY-MM-DD, got '{val}'")

    _validate_id_refs(task, "is_blocking", prefix, errors, all_task_ids)
    _validate_id_refs(task, "blocked_by", prefix, errors, all_task_ids)


def _validate_id_refs(
    obj: dict, field: str, prefix: str, errors: list[str], valid_ids: set[str]
) -> None:
    val = obj.get(field)
    if val is None or not isinstance(val, list):
        return
    for ref in val:
        if not isinstance(ref, str):
            errors.append(f"{prefix}.{field}: all entries must be strings")
            break
        if ref not in valid_ids:
            errors.append(f"{prefix}.{field}: '{ref}' references unknown ID")


def _require_field(
    obj: dict, field: str, expected_type: type, prefix: str, errors: list[str]
) -> None:
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], expected_type):
        errors.append(
            f"{prefix}.{field}: expected {expected_type.__name__}, got {type(obj[field]).__name__}"
        )


def _require_list_field(
    obj: dict, field: str, item_type: type, prefix: str, errors: list[str]
) -> None:
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], list):
        errors.append(f"{prefix}.{field}: expected array")
    elif not all(isinstance(v, item_type) for v in obj[field]):
        errors.append(f"{prefix}.{field}: all entries must be {item_type.__name__}")
