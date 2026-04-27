"""Validate backlog JSON against the sample_structure.json schema.

Checks field presence, types, enum values, ID-pattern consistency,
and date formats. Returns a list of human-readable error strings.
"""

import re

VALID_STATUSES = {"Backlog", "In Progress", "Done", "Blocked"}
VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_ITEM_TYPES = {"User Story", "Technical Story", "Bug", "Spike"}

ID_PATTERNS = {
    "Spike": r"^SK-\d+$",
    "Technical Story": r"^TS-\d+$",
    "Bug": r"^BG-\d+$",
    "User Story": r"^US-\d+$",
}
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def validate(data: dict) -> list[str]:
    """Validate a backlog JSON dict and return a list of error messages.

    An empty list means the data is valid. Each error string includes
    a dotted path prefix (e.g. 'stories[0].status') for easy location.
    """
    errors: list[str] = []
    _validate_root(data, errors)

    if "stories" in data and isinstance(data["stories"], list):
        for i, story in enumerate(data["stories"]):
            prefix = f"stories[{i}]"
            if not isinstance(story, dict):
                errors.append(
                    f"{prefix}: expected object, got {type(story).__name__}"
                )
                continue
            _validate_story(story, prefix, errors)

    return errors


def _validate_root(data: dict, errors: list[str]) -> None:
    """Check root-level fields: project, goal, dates, totalPoints, stories."""
    _require_field(data, "project", str, "root", errors)
    _require_field(data, "goal", str, "root", errors)
    _validate_dates(data, errors)

    if "totalPoints" not in data:
        errors.append("root: missing required field 'totalPoints'")
    elif not isinstance(data["totalPoints"], int):
        errors.append(
            f"root.totalPoints: expected int, got {type(data['totalPoints']).__name__}"
        )

    if "stories" not in data:
        errors.append("root: missing required field 'stories'")
    elif not isinstance(data["stories"], list):
        errors.append("root.stories: expected array")


def _validate_dates(data: dict, errors: list[str]) -> None:
    """Validate the root 'dates' object and its start/end YYYY-MM-DD fields."""
    if "dates" not in data:
        errors.append("root: missing required field 'dates'")
    elif not isinstance(data["dates"], dict):
        errors.append("root.dates: expected object")
    else:
        for date_field in ("start", "end"):
            val = data["dates"].get(date_field)
            if val is None:
                errors.append(f"root.dates: missing required field '{date_field}'")
            elif not isinstance(val, str):
                errors.append(
                    f"root.dates.{date_field}: expected string, got {type(val).__name__}"
                )
            elif val and not re.match(DATE_PATTERN, val):
                errors.append(
                    f"root.dates.{date_field}: must be YYYY-MM-DD, got '{val}'"
                )


def _validate_story(story: dict, prefix: str, errors: list[str]) -> None:
    """Run all story-level validations: fields, item_type, type/id, values."""
    _validate_story_required_fields(story, prefix, errors)
    _validate_story_item_type(story, prefix, errors)
    _validate_story_type_and_id(story, prefix, errors)
    _validate_story_values(story, prefix, errors)


def _validate_story_required_fields(
    story: dict, prefix: str, errors: list[str]
) -> None:
    """Verify all required story fields exist with the correct types."""
    _require_field(story, "id", str, prefix, errors)
    _require_field(story, "type", str, prefix, errors)
    _require_field(story, "title", str, prefix, errors)
    _require_field(story, "description", str, prefix, errors)
    _require_field(story, "status", str, prefix, errors)
    _require_field(story, "priority", str, prefix, errors)
    _require_field(story, "milestone", str, prefix, errors)
    _require_list_field(story, "is_blocking", str, prefix, errors)
    _require_list_field(story, "blocked_by", str, prefix, errors)
    _require_list_field(story, "acceptance_criteria", str, prefix, errors)
    _require_field(story, "start_date", str, prefix, errors)
    _require_field(story, "target_date", str, prefix, errors)


def _validate_story_item_type(
    story: dict, prefix: str, errors: list[str]
) -> None:
    """Ensure item_type is present and equals 'story'."""
    if "item_type" in story and story["item_type"] != "story":
        errors.append(
            f"{prefix}.item_type: must be 'story', got '{story['item_type']}'"
        )
    elif "item_type" not in story:
        errors.append(f"{prefix}: missing required field 'item_type'")


def _validate_story_type_and_id(
    story: dict, prefix: str, errors: list[str]
) -> None:
    """Check that type is a known item type and id matches its regex pattern."""
    story_type = story.get("type")
    story_id = story.get("id", "")

    if isinstance(story_type, str) and story_type not in VALID_ITEM_TYPES:
        errors.append(f"{prefix}.type: '{story_type}' not in {VALID_ITEM_TYPES}")

    if (
        isinstance(story_type, str)
        and story_type in ID_PATTERNS
        and isinstance(story_id, str)
    ):
        if not re.match(ID_PATTERNS[story_type], story_id):
            errors.append(
                f"{prefix}.id: '{story_id}' does not match pattern for '{story_type}'"
            )


def _validate_story_values(
    story: dict, prefix: str, errors: list[str]
) -> None:
    """Validate enum values for status, priority, and date formats."""
    status = story.get("status")
    if isinstance(status, str) and status not in VALID_STATUSES:
        errors.append(f"{prefix}.status: '{status}' not in {VALID_STATUSES}")

    priority = story.get("priority")
    if isinstance(priority, str) and priority not in VALID_PRIORITIES:
        errors.append(f"{prefix}.priority: '{priority}' not in {VALID_PRIORITIES}")

    for date_field in ("start_date", "target_date"):
        val = story.get(date_field)
        if isinstance(val, str) and val and not re.match(DATE_PATTERN, val):
            errors.append(f"{prefix}.{date_field}: must be YYYY-MM-DD, got '{val}'")


def _require_field(
    obj: dict, field: str, expected_type: type, prefix: str, errors: list[str]
) -> None:
    """Append an error if the field is missing or has the wrong type."""
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], expected_type):
        errors.append(
            f"{prefix}.{field}: expected {expected_type.__name__}, got {type(obj[field]).__name__}"
        )


def _require_list_field(
    obj: dict, field: str, item_type: type, prefix: str, errors: list[str]
) -> None:
    """Append an error if the field is missing, not a list, or has wrong item types."""
    if field not in obj:
        errors.append(f"{prefix}: missing required field '{field}'")
    elif not isinstance(obj[field], list):
        errors.append(f"{prefix}.{field}: expected array")
    elif not all(isinstance(v, item_type) for v in obj[field]):
        errors.append(f"{prefix}.{field}: all entries must be {item_type.__name__}")
