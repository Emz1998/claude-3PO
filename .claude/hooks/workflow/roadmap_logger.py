#!/usr/bin/env python3
"""Roadmap logger hook for validating log:sc and log:task skills."""

import re
import sys
from pathlib import Path
from typing import Tuple


sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state  # type: ignore

VALID_SC_ARGS_PATTERN = r"SC-\d{3}"
VALID_TASK_ARGS_PATTERN = r"T\d{3}"
VALID_SC_STATUS_PATTERN = r"met|unmet"
VALID_TASK_STATUS_PATTERN = r"not_started|in_progress|completed|blocked"

FULL_VALID_SC_ARGS_PATTERN = r"/log:sc\s+SC-\d{3}\s+(met|unmet)"
FULL_VALID_TASK_ARGS_PATTERN = (
    r"/log:task\s+T\d{3}\s+(not_started|in_progress|completed|blocked)"
)


def validate_log_sc_prompt(prompt: str) -> Tuple[bool, str]:
    if "/log:sc" not in prompt:
        return True, ""
    if not re.search(FULL_VALID_SC_ARGS_PATTERN, prompt):
        return False, "Invalid log:sc prompt. Expected format: /log:sc SC-XXX met|unmet"
    return True, ""


def validate_log_task_prompt(prompt: str) -> Tuple[bool, str]:
    if "/log:task" not in prompt:
        return True, ""
    if not re.search(FULL_VALID_TASK_ARGS_PATTERN, prompt):
        return (
            False,
            "Invalid log:task prompt. Expected: /log:task TXXX not_started|in_progress|completed|blocked",
        )
    return True, ""


def validate_log_sc_skill(name: str, args: str) -> Tuple[bool, str]:
    if name != "log:sc":
        return True, ""
    if not args:
        return False, "Missing log:sc args"
    parts = args.split()
    if len(parts) < 2:
        return False, "Invalid log:sc args. Expected: SC-XXX met|unmet"
    if not re.match(VALID_SC_ARGS_PATTERN, parts[0]):
        return False, "Invalid SC code format. Expected: SC-XXX"
    if not re.match(VALID_SC_STATUS_PATTERN, parts[1]):
        return False, "Invalid status. Expected: met|unmet"
    return True, ""


def validate_log_task_skill(name: str, args: str) -> Tuple[bool, str]:
    if name != "log:task":
        return True, ""
    if not args:
        return False, "Missing log:task args"
    parts = args.split()
    if len(parts) < 2:
        return (
            False,
            "Invalid log:task args. Expected: TXXX not_started|in_progress|completed|blocked",
        )
    if not re.match(VALID_TASK_ARGS_PATTERN, parts[0]):
        return False, "Invalid task code format. Expected: TXXX"
    if not re.match(VALID_TASK_STATUS_PATTERN, parts[1]):
        return (
            False,
            "Invalid status. Expected: not_started|in_progress|completed|blocked",
        )
    return True, ""


def main() -> None:
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    hook_event_name = hook_input.get("hook_event_name", "")

    if hook_event_name == "PreToolUse":
        tool_name = hook_input.get("tool_name", "")
        if tool_name != "Skill":
            sys.exit(0)

        skill_name = hook_input.get("tool_input", {}).get("skill", "")
        skill_args = hook_input.get("tool_input", {}).get("args", "")

        is_valid, reason = validate_log_sc_skill(skill_name, skill_args)
        if not is_valid:
            print(reason, file=sys.stderr)
            sys.exit(2)

        is_valid, reason = validate_log_task_skill(skill_name, skill_args)
        if not is_valid:
            print(reason, file=sys.stderr)
            sys.exit(2)

    if hook_event_name == "UserPromptSubmit":
        prompt = hook_input.get("prompt", "")

        is_valid, reason = validate_log_sc_prompt(prompt)
        if not is_valid:
            print(reason, file=sys.stderr)
            sys.exit(2)

        is_valid, reason = validate_log_task_prompt(prompt)
        if not is_valid:
            print(reason, file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
