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


from utils import (
    is_file_write_allowed,
    record_file_write,
    StateStore,
    Config,
)


def validate(hook_input: dict, state: StateStore, config: Config) -> tuple[bool, str]:
    """Validate the file write."""
    try:

        allow_message = is_file_write_allowed(hook_input, config, state)

        if allow_message:
            record_file_write(hook_input, state)

    except ValueError as e:
        return False, str(e)

    return True, allow_message
