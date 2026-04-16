"""Validate sprint JSON dicts against the sample_structure.json schema.

Checks field presence, types, allowed values (statuses, priorities,
complexities, story types), ID patterns, date formats, and cross-task
reference integrity. Returns a list of human-readable error strings.
"""

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
        all_task_ids = _collect_task_ids(data["stories"])
        _validate_stories(data["stories"], errors, all_task_ids)

    return errors


def _collect_task_ids(stories: list) -> set[str]:
    """Gather all task IDs across stories for cross-reference validation."""
    ids: set[str] = set()
    for story in stories:
        if isinstance(story, dict) and isinstance(story.get("tasks"), list):
            for task in story["tasks"]:
                if isinstance(task, dict) and isinstance(task.get("id"), str):
                    ids.add(task["id"])
    return ids


def _validate_stories(stories: list, errors: list[str], all_task_ids: set[str]) -> None:
    """Validate each story in the stories array."""
    for i, story in enumerate(stories):
        prefix = f"stories[{i}]"
        if not isinstance(story, dict):
            errors.append(f"{prefix}: expected object, got {type(story).__name__}")
            continue
        _validate_story(story, prefix, errors, all_task_ids)


def _validate_root(data: dict, errors: list[str]) -> None:
    _require_field(data, "sprint", int, "root", errors)
    _require_field(data, "milestone", str, "root", errors)
    _require_field(data, "description", str, "root", errors)
    _require_field(data, "due_date", str, "root", errors)
    _validate_date_field(data, "due_date", "root", errors)

    if "stories" not in data:
        errors.append("root: missing required field 'stories'")
    elif not isinstance(data["stories"], list):
        errors.append("root.stories: expected array")


def _validate_story(
    story: dict, prefix: str, errors: list[str], all_task_ids: set[str],
) -> None:
    _validate_story_required_fields(story, prefix, errors)
    _validate_story_item_type(story, prefix, errors)
    _validate_story_values(story, prefix, errors)
    _validate_story_tasks(story, prefix, errors, all_task_ids)


def _validate_story_required_fields(story: dict, prefix: str, errors: list[str]) -> None:
    """Check all required fields exist with correct types."""
    for field, typ in (
        ("id", str), ("type", str), ("title", str), ("description", str),
        ("points", int), ("status", str), ("tdd", bool), ("priority", str),
        ("milestone", str), ("start_date", str), ("target_date", str),
    ):
        _require_field(story, field, typ, prefix, errors)

    for field in ("labels", "is_blocking", "blocked_by", "acceptance_criteria"):
        _require_list_field(story, field, str, prefix, errors)


def _validate_story_item_type(story: dict, prefix: str, errors: list[str]) -> None:
    """Validate item_type is present and equals 'story'."""
    if "item_type" not in story:
        errors.append(f"{prefix}: missing required field 'item_type'")
    elif story["item_type"] != "story":
        errors.append(f"{prefix}.item_type: must be 'story', got '{story['item_type']}'")


def _validate_story_values(story: dict, prefix: str, errors: list[str]) -> None:
    """Validate story field values against allowed sets."""
    _validate_enum(story, "type", VALID_STORY_TYPES, prefix, errors)
    _validate_enum(story, "status", VALID_STORY_STATUSES, prefix, errors)
    _validate_enum(story, "priority", VALID_PRIORITIES, prefix, errors)
    _validate_story_id_pattern(story, prefix, errors)
    _validate_date_field(story, "start_date", prefix, errors)
    _validate_date_field(story, "target_date", prefix, errors)


def _validate_story_id_pattern(story: dict, prefix: str, errors: list[str]) -> None:
    """Check story ID matches the expected pattern for its type."""
    story_type = story.get("type")
    story_id = story.get("id", "")
    if isinstance(story_type, str) and story_type in ID_PATTERNS and isinstance(story_id, str):
        if not re.match(ID_PATTERNS[story_type], story_id):
            errors.append(f"{prefix}.id: '{story_id}' does not match pattern for '{story_type}'")


def _validate_story_tasks(
    story: dict, prefix: str, errors: list[str], all_task_ids: set[str],
) -> None:
    """Validate the tasks array within a story."""
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
    task: dict, prefix: str, errors: list[str], all_task_ids: set[str],
) -> None:
    _validate_task_required_fields(task, prefix, errors)
    _validate_task_item_type(task, prefix, errors)
    _validate_task_type_field(task, prefix, errors)
    _validate_task_values(task, prefix, errors)
    _validate_id_refs(task, "is_blocking", prefix, errors, all_task_ids)
    _validate_id_refs(task, "blocked_by", prefix, errors, all_task_ids)


def _validate_task_required_fields(task: dict, prefix: str, errors: list[str]) -> None:
    """Check all required task fields exist with correct types."""
    for field, typ in (
        ("id", str), ("type", str), ("title", str), ("description", str),
        ("status", str), ("priority", str), ("complexity", str),
        ("milestone", str), ("start_date", str), ("target_date", str),
    ):
        _require_field(task, field, typ, prefix, errors)

    for field in ("labels", "is_blocking", "blocked_by", "acceptance_criteria"):
        _require_list_field(task, field, str, prefix, errors)


def _validate_task_item_type(task: dict, prefix: str, errors: list[str]) -> None:
    """Validate item_type is present and equals 'task'."""
    if "item_type" not in task:
        errors.append(f"{prefix}: missing required field 'item_type'")
    elif task["item_type"] != "task":
        errors.append(f"{prefix}.item_type: must be 'task', got '{task['item_type']}'")


def _validate_task_type_field(task: dict, prefix: str, errors: list[str]) -> None:
    """Validate type field equals 'task'."""
    if "type" in task and task["type"] != "task":
        errors.append(f"{prefix}.type: must be 'task', got '{task['type']}'")


def _validate_task_values(task: dict, prefix: str, errors: list[str]) -> None:
    """Validate task field values against allowed sets."""
    _validate_task_id_pattern(task, prefix, errors)
    _validate_enum(task, "status", VALID_TASK_STATUSES, prefix, errors)
    _validate_enum(task, "priority", VALID_PRIORITIES, prefix, errors)
    _validate_enum(task, "complexity", VALID_COMPLEXITIES, prefix, errors)
    _validate_date_field(task, "start_date", prefix, errors)
    _validate_date_field(task, "target_date", prefix, errors)


def _validate_task_id_pattern(task: dict, prefix: str, errors: list[str]) -> None:
    """Check task ID matches T-NNN pattern."""
    task_id = task.get("id", "")
    if isinstance(task_id, str) and not re.match(TASK_ID_PATTERN, task_id):
        errors.append(f"{prefix}.id: '{task_id}' does not match pattern T-NNN")


# ── Shared helpers ───────────────────────────────────────────────────────────


def _validate_enum(
    obj: dict, field: str, valid: set[str], prefix: str, errors: list[str],
) -> None:
    """Check a string field is in the allowed set."""
    val = obj.get(field)
    if isinstance(val, str) and val not in valid:
        errors.append(f"{prefix}.{field}: '{val}' not in {valid}")


def _validate_date_field(
    obj: dict, field: str, prefix: str, errors: list[str],
) -> None:
    """Check a date field matches YYYY-MM-DD if non-empty."""
    val = obj.get(field)
    if isinstance(val, str) and val and not re.match(DATE_PATTERN, val):
        errors.append(f"{prefix}.{field}: must be YYYY-MM-DD, got '{val}'")


def _validate_id_refs(
    obj: dict, field: str, prefix: str, errors: list[str], valid_ids: set[str],
) -> None:
    """Check that ID references point to known task IDs."""
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
    obj: dict, field: str, expected_type: type, prefix: str, errors: list[str],
) -> None:
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], expected_type):
        errors.append(
            f"{prefix}.{field}: expected {expected_type.__name__}, got {type(obj[field]).__name__}"
        )


def _require_list_field(
    obj: dict, field: str, item_type: type, prefix: str, errors: list[str],
) -> None:
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], list):
        errors.append(f"{prefix}.{field}: expected array")
    elif not all(isinstance(v, item_type) for v in obj[field]):
        errors.append(f"{prefix}.{field}: all entries must be {item_type.__name__}")
