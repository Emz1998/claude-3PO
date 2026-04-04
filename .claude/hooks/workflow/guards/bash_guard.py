"""bash_guard.py — Phase-based Bash command enforcement using flat state model."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.config import PR_COMMAND_PATTERNS, TEST_RUN_PATTERNS, CI_CHECK_PATTERNS
from workflow.state_store import StateStore


def is_pr_command(command: str) -> bool:
    return any(re.search(p, command) for p in PR_COMMAND_PATTERNS)


def is_test_run(command: str) -> bool:
    return any(re.search(p, command) for p in TEST_RUN_PATTERNS)


def is_ci_check(command: str) -> bool:
    return any(re.search(p, command) for p in CI_CHECK_PATTERNS)


def validate_pre(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Validate a Bash PreToolUse invocation.

    Blocks PR commands outside pr-create phase or without passing validation.
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    command = hook_input.get("tool_input", {}).get("command", "")

    if not is_pr_command(command):
        return "allow", ""

    phase = state.get("phase", "")
    validation_result = state.get("validation_result")

    if phase != "pr-create":
        return "block", f"Blocked: PR commands are only allowed during 'pr-create' phase (current: '{phase}'). Complete validation first to advance."

    if validation_result != "Pass":
        return "block", "Blocked: cannot create PR -- validation has not passed yet. Run the Validator agent to get a 'Pass' result before creating the PR."

    return "allow", ""
