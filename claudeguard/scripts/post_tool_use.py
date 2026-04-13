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
    inject_plan_metadata,
    record_plan_sections,
    record_contracts_file,
    record_dependency_install,
)
from utils.validators import _is_test_command
from constants import INSTALL_COMMANDS
from utils.resolvers import resolve
from config import Config


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(Path(__file__).resolve().parent / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    config = Config()

    # Inject metadata into plan file after Write, then auto-parse sections
    if tool_name == "Write":
        file_path = hook_input.get("tool_input", {}).get("file_path", "")
        if file_path and file_path.endswith(config.plan_file_path):
            inject_plan_metadata(file_path, state)
            record_plan_sections(file_path, state)
        if file_path and config.contracts_file_path and file_path.endswith(config.contracts_file_path):
            record_contracts_file(file_path, state)

    if tool_name == "Bash":
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

            if phase == "install-deps" and any(command.startswith(cmd) for cmd in INSTALL_COMMANDS):
                record_dependency_install(command, state)
        except ValueError as e:
            Hook.block(str(e))

    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))

    sys.exit(0)


if __name__ == "__main__":
    main()
