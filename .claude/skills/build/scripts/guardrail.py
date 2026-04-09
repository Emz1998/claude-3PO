"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

from pathlib import Path
from typing import Literal, get_args, Any
import sys


from scripts.recorders.utils import (
    is_file_write_allowed,
    is_file_edit_allowed,
    is_agent_allowed,
    is_pr_commands_allowed,
)


def validate(hook_input: dict, state: dict[str, Any]) -> tuple[str, str]:

    phase = state.get("phase", "")

    try:
        validators = [
            is_file_write_allowed,
            is_file_edit_allowed,
            is_agent_allowed,
            is_pr_commands_allowed,
        ]

        for validator in validators:
            if validator(state, hook_input):
                return "allow", validator(phase, hook_input)
    except ValueError as e:
        return "block", str(e)
    except Exception as e:
        return "block", str(e)

    return "allow", "All validators passed"


if __name__ == "__main__":
    hook_input = {
        "hook_event_name": "PostToolUse",
        "tool_name": "FileWrite",
        "tool_input": {
            "file_path": "test.txt",
            "content": "Hello, world!",
        },
    }
    state: dict[str, Any] = {"phase": "write-plan"}
    print(validate(hook_input, state))
