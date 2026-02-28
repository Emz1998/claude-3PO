"""Hook output functions with correct camelCase JSON serialization.

Standalone functions — no classes, no Pydantic. Handles block/succeed/JSON output.
"""

import json
import sys
from typing import Any


# Python field name -> JSON key mapping
_FIELD_MAP = {
    "continue_": "continue",
    "stop_reason": "stopReason",
    "suppress_output": "suppressOutput",
    "system_message": "systemMessage",
    "decision": "decision",
    "reason": "reason",
    "hook_specific_output": "hookSpecificOutput",
}


def build_output(**kwargs: Any) -> str:
    """Build a JSON string with camelCase keys, omitting None values."""
    result = {}
    for py_key, value in kwargs.items():
        if value is None:
            continue
        json_key = _FIELD_MAP.get(py_key, py_key)
        result[json_key] = value
    return json.dumps(result)


def block(reason: str) -> None:
    """Block the hook (exit 2 + stderr message)."""
    print(reason, file=sys.stderr)
    sys.exit(2)


def debug(message: str) -> None:
    """Print a debug message (exit 0 if message given)."""
    if message is None:
        return
    print(message, file=sys.stderr)
    sys.exit(1)


def succeed(context: str | None = None) -> None:
    """Allow the hook, optionally printing context (exit 0 if context given)."""
    if context is None:
        return
    print(context)
    sys.exit(0)


def set_decision(**kwargs: Any) -> None:
    """Print JSON output and exit 0."""
    print(build_output(**kwargs))
    sys.exit(0)
