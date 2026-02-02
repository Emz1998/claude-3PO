#!/usr/bin/env python3
"""PreToolUse hook for file read validation.

Validates that files are read in the required order during workflow execution.
"""


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from _utils import validate_order  # type: ignore
from state import get_state, set_state  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from roadmap.utils import get_current_version  # type: ignore

REQUIRED_FILES_TO_READ_ORDER = [
    "recap.md",
    "ms-summary.md",
    "tasks.md",
    "codebase-status.md",
    "plan.md",
    "plan-consultation.md",
]


def last_file_read(
    files_read: list[str] | None = None,
    phase: str | None = None,
) -> str | None:
    if phase is None:
        phase = get_state("current_phase")

    if not phase:
        return None

    if files_read is None:
        read_files = get_state("read_files") or {}
        files_read = read_files.get(phase, [])

    return files_read[-1] if files_read else None


def main() -> None:
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")
    if not hook_input:
        sys.exit(0)

    if hook_event_name != "PreToolUse":
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Read":
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})
    next_file = tool_input.get("file_path", None)

    last_file = last_file_read(
        phase=hook_input.get("tool_input", {}).get("phase", None)
    )

    is_valid, error_message = validate_order(
        last_file, next_file, REQUIRED_FILES_TO_READ_ORDER
    )
    if not is_valid:
        print(error_message, file=sys.stderr)
        sys.exit(2)

    print(f"Valid order: {is_valid}")
    sys.exit(0)


if __name__ == "__main__":
    main()
