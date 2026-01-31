#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import re
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from state import set_state  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json  # type: ignore

VALID_ARGS_PATTERN = r"MS-\d{3}$"


def is_valid_args(prompt: str) -> bool:
    splitted_prompt = prompt.split()
    if "/implement" not in splitted_prompt:
        return True
    if len(splitted_prompt) != 2:
        return False
    if not splitted_prompt[0] == "/implement":
        return False
    if not re.match(VALID_ARGS_PATTERN, splitted_prompt[1]):
        return False
    return True


def main():

    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)
    prompt = hook_input.get("prompt", "")
    if not prompt:
        sys.exit(0)
    if not is_valid_args(prompt):
        print(f"Invalid args: {prompt}", file=sys.stderr)
        sys.exit(2)
    set_state("workflow_active", True)


if __name__ == "__main__":
    main()
