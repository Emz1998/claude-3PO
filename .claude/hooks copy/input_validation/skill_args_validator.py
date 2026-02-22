#!/usr/bin/env python3
# Skill Args Validator
# PreToolUse hook that validates args format for log:task, log:ac, log:sc skills

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.input import read_stdin_json  # type: ignore
from utils.output import block_response  # type: ignore

# Valid statuses per skill
TASK_STATUSES = ["not_started", "in_progress", "completed", "blocked"]
AC_STATUSES = ["met", "unmet"]
SC_STATUSES = ["met", "unmet"]

# ID format patterns
TASK_PATTERN = re.compile(r"^T\d{3}$")
AC_PATTERN = re.compile(r"^AC-\d{3}$")
SC_PATTERN = re.compile(r"^SC-\d{3}$")

# Skill configurations
SKILL_CONFIG: dict[str, dict[str, object]] = {
    "log:task": {
        "pattern": TASK_PATTERN,
        "statuses": TASK_STATUSES,
        "id_example": "T001",
        "status_example": "completed",
    },
    "log:ac": {
        "pattern": AC_PATTERN,
        "statuses": AC_STATUSES,
        "id_example": "AC-001",
        "status_example": "met",
    },
    "log:sc": {
        "pattern": SC_PATTERN,
        "statuses": SC_STATUSES,
        "id_example": "SC-001",
        "status_example": "met",
    },
}


def parse_args(args_str: str) -> tuple[str, str] | None:
    """Parse args string in format '<id> <status>'."""
    if not args_str:
        return None
    parts = args_str.strip().split()
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def validate_skill_args(skill_name: str, args: str) -> None:
    """Validate args for a given skill. Blocks if invalid."""
    config = SKILL_CONFIG.get(skill_name)
    if config is None:
        sys.exit(0)

    pattern: re.Pattern[str] = config["pattern"]  # type: ignore
    statuses: list[str] = config["statuses"]  # type: ignore
    id_example: str = config["id_example"]  # type: ignore
    status_example: str = config["status_example"]  # type: ignore

    parsed = parse_args(args)
    if parsed is None:
        block_response(
            f"Invalid args format. Expected: '<id> <status>'. "
            f"Example: '{id_example} {status_example}'"
        )

    item_id, status = parsed

    if not pattern.match(item_id):
        block_response(
            f"Invalid ID format: '{item_id}'. Expected format like: {id_example}"
        )

    if status not in statuses:
        block_response(
            f"Invalid status: '{status}'. Valid statuses: {', '.join(statuses)}"
        )

    # Args are valid, allow the skill to proceed
    sys.exit(0)


def main() -> None:
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    # Check if this is a Skill tool call
    tool_name = input_data.get("tool_name", "")
    if tool_name != "Skill":
        sys.exit(0)

    # Get tool_input
    tool_input = input_data.get("tool_input", {})
    skill_name = tool_input.get("skill", "")
    args = tool_input.get("args", "")

    # Only validate known log skills
    if skill_name not in SKILL_CONFIG:
        sys.exit(0)

    # Validate args
    validate_skill_args(skill_name, args)


class Skill()

if __name__ == "__main__":
    main()
