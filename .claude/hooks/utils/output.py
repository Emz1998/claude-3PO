import json
import sys
from typing import NoReturn

DEFAULT_HOOK_SPECIFIC_OUTPUT = {
    "hookSpecificOutput": {"hookEventName": "", "additionalContext": ""}
}


def log(msg: str) -> None:
    """Print to stderr for hook system visibility."""
    print(msg, file=sys.stderr, flush=True)


def success_response(hook_event: str, context: str = "") -> NoReturn:
    """Output JSON success response and exit 0."""
    response = {"hookSpecificOutput": {"hookEventName": hook_event}}
    if context:
        response["hookSpecificOutput"]["additionalContext"] = context
    print(json.dumps(response))
    print(context)
    sys.exit(0)


def success_output(context: str | dict) -> NoReturn:
    print(context)
    sys.exit(0)


def add_context(context: str) -> NoReturn:
    DEFAULT_HOOK_SPECIFIC_OUTPUT["hookSpecificOutput"]["additionalContext"] = context
    print(json.dumps(DEFAULT_HOOK_SPECIFIC_OUTPUT))
    sys.exit(0)


def print_and_exit(message: str) -> NoReturn:
    """Simple output: print message to stdout and exit 0."""
    print(message)
    sys.exit(0)


def block_response(reason: str) -> NoReturn:
    """Output error to stderr and exit 2 (blocking)."""
    print(reason, file=sys.stderr)
    sys.exit(2)


def continue_response() -> None:
    """Output continue signal for SubagentStop."""
    print(json.dumps({"continue": True}))
