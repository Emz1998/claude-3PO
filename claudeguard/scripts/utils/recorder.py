"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

from datetime import datetime
from pathlib import Path
from typing import Literal, get_args, Any, TypeVar, Generic, Callable
import sys
import tomllib


from constants import (
    PR_COMMANDS,
    TEST_FILE_PATTERNS,
    CODE_EXTENSIONS,
    TEST_RUN_PATTERNS,
)

from models.state import *
from .state_store import StateStore
from config import Config


# ── Recorders ──────────────────────────────────────────────────────


def record_file_write(hook_input: dict, state: StateStore) -> None:
    """Record the file write."""
    phase = state.current_phase
    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    if phase == "plan":
        state.set_plan_file_path(file_path)
        state.set_plan_written(True)
    elif phase == "define-contracts":
        state.add_contract_code_file(file_path)
        state.set_contracts_written(True)
    elif phase == "write-tests":
        state.add_test_file(file_path)
    elif phase == "write-code":
        state.add_code_file(file_path)
    elif phase == "write-report":
        state.set_report_written(True)


def record_agent_start(agent_type: str, agent_id: str, state: StateStore) -> None:
    """Record an agent start with its unique agent_id."""
    state.add_agent(Agent(name=agent_type, status="in_progress", tool_use_id=agent_id))


def inject_plan_metadata(file_path: str, state: StateStore) -> None:
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


def record_plan(file_path: str, state: StateStore) -> None:
    """Record plan file path and mark as written."""
    state.set_plan_file_path(file_path)


def record_plan_written(state: StateStore) -> None:
    """Record plan as written."""
    state.set_plan_written(True)


def record_test_execution(state: StateStore) -> None:
    """Mark tests as executed."""
    state.set_tests_executed(True)


def record_test_review_result(
    result: Literal["Pass", "Fail"], state: StateStore
) -> None:
    """Record test review result as a new review entry."""
    state.add_test_review(result)


def record_plan_review_scores(
    scores: dict[Literal["confidence_score", "quality_score"], int], state: StateStore
) -> None:
    """Record plan review scores as a new review entry."""
    state.add_plan_review(scores)


def record_code_file_to_write(file_path: str, state: StateStore) -> None:
    """Record a code file that is expected to be written."""
    state.add_code_file_to_write(file_path)


def record_code_review_scores(
    scores: dict[Literal["confidence_score", "quality_score"], int], state: StateStore
) -> None:
    """Record code review scores as a new review entry."""
    state.add_code_review(scores)


def record_scores(
    phase: Literal["plan-review", "code-review"],
    scores: dict[Literal["confidence_score", "quality_score"], int],
    state: StateStore,
) -> None:
    """Record scores as a new review entry."""
    if phase == "plan-review":
        state.add_plan_review(scores)
    elif phase == "code-review":
        state.add_code_review(scores)


def record_code_review_status(
    status: Literal["Pass", "Fail"], state: StateStore
) -> None:
    """Record code review status."""
    state.set_code_review_status(status)


def record_quality_check_result(
    result: Literal["Pass", "Fail"], state: StateStore
) -> None:
    """Record quality check result."""
    state.set_quality_check_result(result)


def record_phase_transition(
    next_phase: str, state: StateStore, parallel: bool = False
) -> None:
    """Complete the current phase and start the next one.

    If parallel=True, the current phase stays in_progress (e.g. explore + research).
    """
    current = state.current_phase
    if current and not parallel:
        state.complete_phase(current)
    state.add_phase(next_phase)


def record_phase_completion(phase: str, state: StateStore) -> None:
    """Mark a phase as completed."""
    state.complete_phase(phase)


def record_agent_completion(agent_id: str, state: StateStore) -> None:
    """Mark an agent as completed by its agent_id."""
    state.update_agent_status(agent_id, "completed")


def record_pr_status(
    status: Literal["pending", "created", "merged"], state: StateStore
) -> None:
    """Record PR status."""
    state.set_pr_status(status)


def record_pr_number(number: int, state: StateStore) -> None:
    """Record PR number."""
    state.set_pr_number(number)


def record_ci_status(
    status: Literal["pending", "passed", "failed"], state: StateStore
) -> None:
    """Record CI status."""
    state.set_ci_status(status)


def record_ci_results(results: list[dict], state: StateStore) -> None:
    """Record CI check results (gh pr checks JSON output)."""
    state.set_ci_results(results)


def record_pr_create_output(output: str, state: StateStore) -> None:
    """Parse gh pr create --json output and record PR number + status."""
    import json

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse PR create output as JSON: {output}")

    number = data.get("number")
    if number is None:
        raise ValueError("PR create output missing 'number' field")

    state.set_pr_number(number)
    state.set_pr_status("created")


def record_plan_sections(file_path: str, state: StateStore) -> None:
    """Auto-parse Dependencies and Tasks from plan and store in state."""
    from .extractors import extract_plan_dependencies, extract_plan_tasks

    path = Path(file_path)
    if not path.exists():
        return

    content = path.read_text()
    deps = extract_plan_dependencies(content)
    tasks = extract_plan_tasks(content)

    state.set_dependencies_packages(deps)
    state.set_tasks(tasks)


def record_contracts_file(file_path: str, state: StateStore) -> None:
    """Auto-parse contract names from contracts.md and store in state."""
    from .extractors import extract_contract_names

    path = Path(file_path)
    if not path.exists():
        return

    content = path.read_text()
    names = extract_contract_names(content)

    state.set_contracts_file_path(file_path)
    state.set_contracts_names(names)


def record_dependency_install(command: str, state: StateStore) -> None:
    """Mark dependencies as installed when install command runs."""
    state.set_dependencies_installed()


def record_ci_check_output(output: str, state: StateStore) -> None:
    """Parse gh pr checks --json output and record CI results + status."""
    import json

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
