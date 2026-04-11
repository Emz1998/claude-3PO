#!/usr/bin/env python3
"""PostToolUse hook — records tool results and runs resolvers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.hook import Hook
from utils.state_store import StateStore
from utils.recorder import (
    record_pr_create_output,
    record_ci_check_output,
    record_test_execution,
)
from utils.validators import _is_test_command
from utils.resolvers import resolve
from config import Config


def main() -> None:
    hook_input = Hook.read_stdin()

    state = StateStore(Path(__file__).resolve().parent / "state.json")
    if not state.get("workflow_active"):
        sys.exit(0)
    if hook_input.get("session_id") != state.get("session_id"):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    if tool_name != "Bash":
        sys.exit(0)

    config = Config()

    phase = state.current_phase
    command = hook_input.get("tool_input", {}).get("command", "")
    tool_output = hook_input.get("tool_result", "")

    try:
        if phase == "pr-create" and command.startswith("gh pr create"):
            record_pr_create_output(tool_output, state)

        if phase == "ci-check" and command.startswith("gh pr checks"):
            record_ci_check_output(tool_output, state)

        if phase in ("write-tests", "test-review") and _is_test_command(command):
            record_test_execution(state)

        resolve(config, state)

    except ValueError as e:
        Hook.block(str(e))

    sys.exit(0)


if __name__ == "__main__":
    main()
