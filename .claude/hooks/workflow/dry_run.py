#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state, reset_state, set_state  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json  # type: ignore

VALID_ARGS_PATTERN = r"MS-\d{3}$"


def dry_run_triggered(prompt: str) -> bool:
    if "/dry-run" not in prompt:
        return False
    return True


def main():
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")

    is_dry_run_active = get_state("dry_run_active")
    if hook_event_name != "UserPromptSubmit":
        return
    prompt = hook_input.get("prompt", "")

    if is_dry_run_active:
        return
    if not dry_run_triggered(prompt):
        return
    reset_state()
    set_state("workflow_active", True)
    set_state("dry_run_active", True)


if __name__ == "__main__":
    main()
