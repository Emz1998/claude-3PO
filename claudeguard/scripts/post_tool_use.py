#!/usr/bin/env python3
"""PostToolUse hook — records tool results and runs resolvers."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.hook import Hook
from utils.state_store import StateStore
from utils.extractors import (
    extract_plan_dependencies,
    extract_plan_tasks,
    extract_plan_files_to_modify,
    extract_contract_names,
    extract_contract_files,
)
from utils.validators import _is_test_command
from constants import INSTALL_COMMANDS
from utils.resolvers import resolve
from config import Config


# ── Write recorders ───────────────────────────────────────────────


def _inject_plan_metadata(file_path: str, state: StateStore) -> None:
    """Inject frontmatter metadata into the plan file after it's written."""
    path = Path(file_path)
    if not path.exists():
        return

    content = path.read_text()

    # Strip existing frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].lstrip("\n")

    metadata = {
        "session_id": state.get("session_id"),
        "workflow_type": state.get("workflow_type"),
        "story_id": state.get("story_id"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
    }

    fm_lines = ["---"]
    for key, val in metadata.items():
        if val is not None:
            fm_lines.append(f"{key}: {val}")
    fm_lines.append("---\n")

    path.write_text("\n".join(fm_lines) + content)


def _record_plan_sections(file_path: str, state: StateStore) -> None:
    """Auto-parse Dependencies, Tasks, and Files to Modify from plan."""
    path = Path(file_path)
    if not path.exists():
        return

    content = path.read_text()
    state.set_dependencies_packages(extract_plan_dependencies(content))
    state.set_tasks(extract_plan_tasks(content))

    for f in extract_plan_files_to_modify(content):
        state.add_code_file_to_write(f)


def _record_contracts_file(file_path: str, state: StateStore) -> None:
    """Auto-parse contract names and file paths from contracts.md."""
    path = Path(file_path)
    if not path.exists():
        return

    content = path.read_text()
    state.set_contracts_file_path(file_path)
    state.set_contracts_names(extract_contract_names(content))

    files = extract_contract_files(content)
    if files:
        state.set("contract_files", files)


# ── Bash recorders ────────────────────────────────────────────────


def _record_pr_create_output(output: str, state: StateStore) -> None:
    """Parse gh pr create --json output and record PR number + status."""
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse PR create output as JSON: {output}")

    number = data.get("number")
    if number is None:
        raise ValueError("PR create output missing 'number' field")

    state.set_pr_number(number)
    state.set_pr_status("created")


def _record_ci_check_output(output: str, state: StateStore) -> None:
    """Parse gh pr checks --json output and record CI results + status."""
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse CI check output as JSON: {output}")

    results = data if isinstance(data, list) else data.get("checks", [])
    state.set_ci_results(results)

    if any(r.get("conclusion") == "FAILURE" for r in results):
        state.set_ci_status("failed")
    elif all(r.get("conclusion") == "SUCCESS" for r in results):
        state.set_ci_status("passed")
    else:
        state.set_ci_status("pending")


# ── Main ──────────────────────────────────────────────────────────


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
            _inject_plan_metadata(file_path, state)
            _record_plan_sections(file_path, state)
        if file_path and config.contracts_file_path and file_path.endswith(config.contracts_file_path):
            _record_contracts_file(file_path, state)

    if tool_name == "Bash":
        phase = state.current_phase
        command = hook_input.get("tool_input", {}).get("command", "")
        tool_output = hook_input.get("tool_result", "")

        try:
            if phase == "pr-create" and command.startswith("gh pr create"):
                _record_pr_create_output(tool_output, state)

            if phase == "ci-check" and command.startswith("gh pr checks"):
                _record_ci_check_output(tool_output, state)

            if phase in ("write-tests", "test-review") and _is_test_command(command):
                state.set_tests_executed(True)

            if phase == "install-deps" and any(command.startswith(cmd) for cmd in INSTALL_COMMANDS):
                state.set_dependencies_installed()
        except ValueError as e:
            Hook.block(str(e))

    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))

    sys.exit(0)


if __name__ == "__main__":
    main()
