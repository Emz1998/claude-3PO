#!/usr/bin/env python3
# User Prompt Dispatcher for Status Logger
# UserPromptSubmit hook that routes /log:* commands to appropriate logger

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.input import read_stdin_json  # type: ignore
from status_logger import task_logger, ac_logger, sc_logger  # type: ignore

# Pattern to match /log:task, /log:ac, /log:sc commands with args
LOG_COMMAND_WITH_ARGS = re.compile(r"^/log:(task|ac|sc)\s+(.+)$", re.IGNORECASE)
# Pattern to match /log:task, /log:ac, /log:sc commands without args (for help)
LOG_COMMAND_NO_ARGS = re.compile(r"^/log:(task|ac|sc)\s*$", re.IGNORECASE)

COMMAND_HANDLERS = {
    "task": task_logger.process,
    "ac": ac_logger.process,
    "sc": sc_logger.process,
}

USAGE_HELP = {
    "task": "Usage: /log:task <task-id> <status>\n  Valid statuses: not_started, in_progress, completed, blocked\n  Example: /log:task T001 completed",
    "ac": "Usage: /log:ac <ac-id> <status>\n  Valid statuses: met, unmet\n  Example: /log:ac AC-001 met",
    "sc": "Usage: /log:sc <sc-id> <status>\n  Valid statuses: met, unmet\n  Example: /log:sc SC-001 met",
}


def print_help(command_type: str) -> None:
    """Print usage help for a command and block prompt processing."""
    help_text = USAGE_HELP.get(command_type, "Unknown command")
    print(help_text, file=sys.stderr)
    # Exit code 2 blocks the prompt and shows stderr to user
    sys.exit(2)


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

    # Route to appropriate handler
    handler = COMMAND_HANDLERS.get(command_type)
    if handler is None:
        sys.exit(0)

    # Process the request
    handler(args)


if __name__ == "__main__":
    main()
