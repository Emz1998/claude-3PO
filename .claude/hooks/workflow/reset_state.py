#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import re
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from state import get_state, set_state, initialize_state  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json  # type: ignore


def is_implement_triggered(prompt: str) -> bool:
    if prompt not in ["--reset-state", "/implement"]:
        return False
    return True


def main():
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    print("is this working")
    if not hook_input:
        sys.exit(0)
    if not is_implement_triggered(hook_input.get("prompt", "")):
        sys.exit(0)
    initialize_state()


if __name__ == "__main__":
    main()
