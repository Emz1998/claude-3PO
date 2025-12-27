#!/usr/bin/env python3
# Slash Command Validator
# UserPromptSubmit hook that validates /log:task, /log:ac, /log:sc commands

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.input import read_stdin_json  # type: ignore
from utils.output import block_response  # type: ignore

# Valid statuses per command type
TASK_STATUSES = ["not_started", "in_progress", "completed", "blocked"]
AC_STATUSES = ["met", "unmet"]
SC_STATUSES = ["met", "unmet"]

# ID format patterns
TASK_PATTERN = re.compile(r"^T\d{3}$")
AC_PATTERN = re.compile(r"^AC-\d{3}$")
SC_PATTERN = re.compile(r"^SC-\d{3}$")

# Command patterns
LOG_COMMAND_WITH_ARGS = re.compile(r"^/log:(task|ac|sc)\s+(.+)$", re.IGNORECASE)
LOG_COMMAND_NO_ARGS = re.compile(r"^/log:(task|ac|sc)\s*$", re.IGNORECASE)

# Command configurations
COMMAND_CONFIG: dict[str, dict[str, object]] = {
    "task": {
        "pattern": TASK_PATTERN,
        "statuses": TASK_STATUSES,
        "id_example": "T001",
        "status_example": "completed",
    },
    "ac": {
        "pattern": AC_PATTERN,
        "statuses": AC_STATUSES,
        "id_example": "AC-001",
        "status_example": "met",
    },
    "sc": {
        "pattern": SC_PATTERN,
        "statuses": SC_STATUSES,
        "id_example": "SC-001",
        "status_example": "met",
    },
}

USAGE_HELP = {
    "task": "Usage: /log:task <task-id> <status>\n  Valid statuses: not_started, in_progress, completed, blocked\n  Example: /log:task T001 completed",
    "ac": "Usage: /log:ac <ac-id> <status>\n  Valid statuses: met, unmet\n  Example: /log:ac AC-001 met",
    "sc": "Usage: /log:sc <sc-id> <status>\n  Valid statuses: met, unmet\n  Example: /log:sc SC-001 met",
}


def parse_args(args_str: str) -> tuple[str, str] | None:
    """Parse args string in format '<id> <status>'."""
    if not args_str:
        return None
    parts = args_str.strip().split()
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def print_help(command_type: str) -> None:
    """Print usage help for a command and block prompt processing."""
    help_text = USAGE_HELP.get(command_type, "Unknown command")
    block_response(help_text)


def validate_command_args(command_type: str, args: str) -> None:
    """Validate args for a given command. Blocks if invalid."""
    config = COMMAND_CONFIG.get(command_type)
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

    # Args are valid, allow the command to proceed
    sys.exit(0)


def main() -> None:
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    # Check if this is a UserPromptSubmit event
    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "UserPromptSubmit":
        sys.exit(0)

    # Get the prompt
    prompt = input_data.get("prompt", "").strip()
    if not prompt:
        sys.exit(0)

    # Check for command without args (show help)
    no_args_match = LOG_COMMAND_NO_ARGS.match(prompt)
    if no_args_match:
        command_type = no_args_match.group(1).lower()
        print_help(command_type)

    # Match /log:* command with args
    match = LOG_COMMAND_WITH_ARGS.match(prompt)
    if not match:
        sys.exit(0)

    command_type = match.group(1).lower()
    args = match.group(2).strip()

    # Validate args
    validate_command_args(command_type, args)


if __name__ == "__main__":
    main()
