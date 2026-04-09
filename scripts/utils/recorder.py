"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

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
from .helpers import validate_order
from config import Config


# ── Record Condition Checkers ──────────────────────────────────────────────────────


def is_explore_phase_completed(config: Config, state: StateStore) -> str:
    """Check all Explore agents have completed."""
    agent_name = config.get_required_agent("explore")
    if not agent_name:
        return "No agent required for explore phase"

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agents found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Explore not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    return f"Explore completed: all {len(agents)} '{agent_name}' agent(s) done"


def is_research_phase_completed(config: Config, state: StateStore) -> str:
    """Check all Research agents have completed."""
    agent_name = config.get_required_agent("research")
    if not agent_name:
        return "No agent required for research phase"

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agents found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Research not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    return f"Research completed: all {len(agents)} '{agent_name}' agent(s) done"


def is_content_valid(
    content: str,
    extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
) -> bool:
    scores = extractor(content)

    confidence_score = scores["confidence_score"]
    quality_score = scores["quality_score"]

    if confidence_score is None or quality_score is None:
        raise ValueError("Confidence and quality scores are required")

    return True


def is_plan_phase_completed(config: Config, state: StateStore) -> str:
    """Check the plan has been written to the expected file path."""
    plan = state.plan
    if not plan.get("written"):
        raise ValueError("Plan has not been written yet")

    file_path = plan.get("file_path", "")
    expected = config.plan_file_path
    if file_path != expected:
        raise ValueError(f"Plan written to '{file_path}' but expected '{expected}'")

    return f"Plan completed: written to '{file_path}'"


def is_revision_needed(
    file_type: Literal["plan", "report", "tests", "code"],
    confidence_score: int,
    quality_score: int,
    config: Config,
) -> bool:
    confidence_threshold = config.get_score_threshold(file_type, "confidence_score")
    quality_threshold = config.get_score_threshold(file_type, "quality")

    if confidence_score < confidence_threshold and quality_score < quality_threshold:
        raise ValueError(f"Scores are below the threshold for {file_type}")

    if confidence_score < confidence_threshold:
        raise ValueError(f"Confidence score is below the threshold for {file_type}")
    if quality_score < quality_threshold:
        raise ValueError(f"Quality score is below the threshold for {file_type}")
    return True


def is_plan_review_phase_completed(config: Config, state: StateStore) -> str:
    """Check the plan review agent was invoked and scores meet thresholds."""
    agent_name = config.get_required_agent("plan-review")
    if not agent_name:
        raise ValueError("No agent configured for plan-review phase")

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agent found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Plan review not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    review = state.plan.get("review", {})
    scores = review.get("scores") or {}
    confidence = scores.get("confidence_score", 0)
    quality = scores.get("quality_score", 0)

    is_revision_needed("plan", confidence, quality, config)

    return f"Plan review completed: confidence {confidence}, quality {quality}"


def is_write_test_phase_completed(state: StateStore) -> str:
    """Check that test files have been written."""
    tests = state.tests
    file_paths = tests.get("file_paths", [])

    if not file_paths:
        raise ValueError("No test files have been written")

    return f"Write tests completed: {len(file_paths)} test file(s) written"


def is_test_review_phase_completed(state: StateStore) -> str:
    """Check that test review result is Pass."""
    tests = state.tests
    review_result = tests.get("review_result")

    if review_result is None:
        raise ValueError("Test review has not been performed yet")

    if review_result != "Pass":
        raise ValueError(f"Test review result is '{review_result}', expected 'Pass'")

    return "Test review completed: result is Pass"


def is_write_code_phase_completed(state: StateStore) -> str:
    """Check that all expected code files have been written."""
    to_write = set(state.code_files_to_write)
    written = set(state.code_files.get("file_paths", []))

    if not to_write:
        raise ValueError("No code files expected to be written")

    missing = to_write - written
    if missing:
        raise ValueError(f"Code files not yet written: {sorted(missing)}")

    return f"Write code completed: {len(written)} code file(s) written"


def is_code_review_phase_completed(config: Config, state: StateStore) -> str:
    """Check the code reviewer agent was invoked and scores meet thresholds."""
    agent_name = config.get_required_agent("code-review")
    if not agent_name:
        raise ValueError("No agent configured for code-review phase")

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agent found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Code review not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    review = state.code_files.get("review", {})
    scores = review.get("scores") or {}
    confidence = scores.get("confidence_score", 0)
    quality = scores.get("quality_score", 0)

    is_revision_needed("code", confidence, quality, config)

    return f"Code review completed: confidence {confidence}, quality {quality}"


def is_quality_check_phase_completed(config: Config, state: StateStore) -> str:
    """Check QA specialist was invoked and quality check result is Pass."""
    agent_name = config.get_required_agent("quality-check")
    if not agent_name:
        raise ValueError("No agent configured for quality-check phase")

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agent found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Quality check not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    result = state.quality_check_result
    if result is None:
        raise ValueError("Quality check has not been performed yet")

    if result != "Pass":
        raise ValueError(f"Quality check result is '{result}', expected 'Pass'")

    return "Quality check completed: result is Pass"


def is_pr_create_phase_completed(state: StateStore) -> str:
    """Check that PR has been created."""
    status = state.pr_status
    if status != "created":
        raise ValueError(f"PR status is '{status}', expected 'created'")

    return "PR create completed: status is 'created'"


def is_ci_check_phase_completed(state: StateStore) -> str:
    """Check that CI has passed."""
    status = state.ci_status
    if status != "passed":
        raise ValueError(f"CI status is '{status}', expected 'passed'")

    return "CI check completed: status is 'passed'"


def is_test_executed(command: str) -> str:
    """Check if the command is a valid test command."""
    import re

    for pattern in TEST_RUN_PATTERNS:
        if re.search(pattern, command):
            return f"Test command recognized: '{command}'"

    raise ValueError(
        f"Command '{command}' is not a valid test command"
        f"\nExpected patterns: {TEST_RUN_PATTERNS}"
    )


# ── Recorders ──────────────────────────────────────────────────────


def record_file_write(hook_input: dict, state: StateStore) -> None:
    """Record the file write."""
    phase = state.current_phase
    file_path = hook_input.get("file_path", "")

    if phase == "plan":
        state.set_plan_file_path(file_path)
        state.set_plan_written(True)
    elif phase == "write-tests":
        state.add_test_file(file_path)
    elif phase == "write-code":
        state.add_code_file(file_path)
    elif phase == "write-report":
        state.set_report_written(True)


def record_agent_transition(agent: str, phase: str, state: StateStore) -> None:
    """Record an agent invocation in state and update the current phase."""
    state.add_agent(Agent(name=agent, status="in_progress"))
    state.add_phase(phase)


def record_plan(file_path: str, state: StateStore) -> None:
    """Record plan file path and mark as written."""
    state.set_plan_file_path(file_path)
    state.set_plan_written(True)


def record_test_execution(state: StateStore) -> None:
    """Mark tests as executed."""
    state.set_tests_executed(True)


def record_test_review_result(
    result: Literal["Pass", "Fail"], state: StateStore
) -> None:
    """Record test review result."""
    state.set_tests_review_result(result)


def record_plan_review_scores(scores: dict[str, int], state: StateStore) -> None:
    """Record plan review scores."""
    state.set_plan_review_scores(scores)


def record_iteration(review_type: Literal["plan", "code"], state: StateStore) -> None:
    """Record an iteration."""
    if review_type == "plan":
        state.increment_plan_review_iteration()
    else:
        state.increment_code_review_iteration()


def record_plan_review_status(
    status: Literal["Pass", "Fail"], state: StateStore
) -> None:
    """Record plan review status."""
    state.set_plan_review_status(status)


def record_code_file_to_write(file_path: str, state: StateStore) -> None:
    """Record a code file that is expected to be written."""
    state.add_code_file_to_write(file_path)


def record_code_review_scores(scores: dict[str, int], state: StateStore) -> None:
    """Record code review scores."""
    state.set_code_review_scores(scores)


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


def record_phase_completion(phase: str, state: StateStore) -> None:
    """Mark a phase as completed and clear sub_phase."""
    state.complete_phase(phase)


def record_agent_completion(agent_name: str, state: StateStore) -> None:
    """Mark an agent as completed."""
    state.update_agent_status(agent_name, "completed")


def record_sub_phase(sub_phase: str, state: StateStore) -> None:
    """Append a sub-phase."""
    state.add_sub_phase(sub_phase)


def record_pr_status(
    status: Literal["pending", "created", "merged"], state: StateStore
) -> None:
    """Record PR status."""
    state.set_pr_status(status)


def record_ci_status(
    status: Literal["pending", "passed", "failed"], state: StateStore
) -> None:
    """Record CI status."""
    state.set_ci_status(status)
