#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import re
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from state import get_state, set_state  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json  # type: ignore

VALID_ARGS_PATTERN = r"MS-\d{3}$"


def is_deactivate_workflow_triggered(prompt: str) -> bool:
    if "/deactivate-workflow" not in prompt:
        return False
    return True


def main():
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)
    prompt = hook_input.get("prompt", "")
    if not prompt:
        sys.exit(0)
    if not is_deactivate_workflow_triggered(prompt):
        return
    set_state("workflow_active", False)


if __name__ == "__main__":
    main()
