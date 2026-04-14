"""validators.py — Orchestrator functions for workflow hooks.

Each public function dispatches to blockers and returns a result.
Handlers (_handle_*) may mutate state for skill commands.

Returns:
    tuple[bool, str]:
        - (True, message) = allowed
        - raises ValueError = blocked
"""

from typing import Literal, Callable

from constants import (
    READ_ONLY_COMMANDS,
    TEST_RUN_PATTERNS,
    COMMANDS_MAP,
)
from .state_store import StateStore
from .extractors import extract_skill_name, extract_agent_name
from .blockers import (
    Result,
    validate_order,
    check_safe_domain,
    check_read_only,
    check_phase_commands,
    check_pr_create_command,
    check_ci_check_command,
    require_agent_completed,
    check_writable_phase,
    check_plan_path,
    validate_contracts_content,
    check_test_path,
    check_code_path,
    check_contract_file,
    check_implement_code_path,
    validate_plan_content,
    check_package_manager_path,
    check_report_path,
    check_editable_phase,
    validate_plan_edit_preserves_sections,
    check_plan_edit_path,
    check_test_edit_path,
    check_code_edit_path,
    check_expected_agent,
    check_agent_count,
    check_revision_done,
    scores_valid,
    verdict_valid,
    is_agent_report_valid,
    validate_review_sections,
)
from config import Config


# Re-export for external consumers
__all__ = [
    "is_phase_allowed",
    "is_command_allowed",
    "is_file_write_allowed",
    "is_file_edit_allowed",
    "is_agent_allowed",
    "is_webfetch_allowed",
    "is_test_executed",
    "scores_valid",
    "verdict_valid",
    "is_agent_report_valid",
    "validate_review_sections",
    "_is_test_command",
]


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — Phase
# ═══════════════════════════════════════════════════════════════════


def _get_workflow_phases(config: Config, state: StateStore) -> list[str]:
    """Get the phase list for the current workflow type."""
    workflow_type = state.get("workflow_type", "build")
    phases = config.get_phases(workflow_type)
    return phases if phases else config.main_phases


REVIEW_PHASES = {
    "plan-review",
    "test-review",
    "tests-review",
    "code-review",
    "quality-check",
    "validate",
}


def _is_review_exhausted(phase: str, state: StateStore) -> bool:
    """Check if a review phase hit max iterations (3)."""
    if phase == "plan-review":
        return (
            state.plan_review_count >= 3
            and state.last_plan_review.get("status") == "Fail"
        )
    if phase in ("test-review", "tests-review"):
        return (
            state.test_review_count >= 3
            and state.last_test_review.get("verdict") == "Fail"
        )
    if phase == "code-review":
        return (
            state.code_review_count >= 3
            and state.last_code_review.get("status") == "Fail"
        )
    if phase in ("quality-check", "validate"):
        return state.qa_specialist_count >= 3 and state.quality_check_result == "Fail"
    return False


def _handle_continue(config: Config, state: StateStore) -> Result:
    """/continue — force-complete the current phase and proceed."""
    current = state.current_phase

    if current == "plan-review":
        raise ValueError(
            "Use '/plan-approved' to approve the plan, or '/revise-plan' to revise it."
        )

    status = state.get_phase_status(current)

    # Phase already completed — auto-start next
    if status == "completed":
        from .resolvers import _auto_start_next

        _auto_start_next(config, state)
        return True, f"Continuing after completed phase: {current}"

    # Phase in progress — force-complete it
    if status == "in_progress":
        state.complete_phase(current)
        from .resolvers import _auto_start_next

        _auto_start_next(config, state)
        return True, f"Force-completed phase: {current}"

    raise ValueError(
        f"'/continue' cannot continue — current phase '{current}' has status '{status}'."
    )


def _handle_plan_approved(config: Config, state: StateStore) -> Result:
    """/plan-approved — user approves plan and proceeds to next phase."""
    current = state.current_phase
    status = state.get_phase_status(current)

    if current != "plan-review":
        raise ValueError(
            "'/plan-approved' can only be used during plan-review. "
            f"Current phase: '{current}'"
        )

    # Case 1: plan-review passed (checkpoint)
    if status == "completed":
        from .resolvers import _auto_start_next

        _auto_start_next(config, state, skip_checkpoint=True)
        return True, "Plan approved. Proceeding to next phase."

    # Case 2: plan-review exhausted (3 fails, user approves anyway)
    if status == "in_progress" and _is_review_exhausted("plan-review", state):
        state.complete_phase("plan-review")
        from .resolvers import _auto_start_next

        _auto_start_next(config, state, skip_checkpoint=True)
        return (
            True,
            "Plan approved (after review exhaustion). Proceeding to next phase.",
        )

    raise ValueError(
        "'/plan-approved' requires plan-review to be at checkpoint (passed) or exhausted (3 fails). "
        f"Current status: {status}, review count: {state.plan_review_count}"
    )


def _handle_revise_plan(state: StateStore) -> Result:
    """/revise-plan — reopen plan-review for editing after pass or exhaustion."""
    current = state.current_phase
    status = state.get_phase_status(current)

    if current != "plan-review":
        raise ValueError(
            "'/revise-plan' can only be used during plan-review. "
            f"Current phase: '{current}'"
        )

    is_checkpoint = status == "completed"
    is_exhausted = status == "in_progress" and _is_review_exhausted(
        "plan-review", state
    )

    if not is_checkpoint and not is_exhausted:
        raise ValueError(
            "'/revise-plan' requires plan-review to be at checkpoint (passed) or exhausted (3 fails). "
            f"Current status: {status}, review count: {state.plan_review_count}"
        )

    # Reopen the phase and reset reviews for fresh cycle
    def _reopen(d: dict) -> None:
        for p in d.get("phases", []):
            if p["name"] == "plan-review":
                p["status"] = "in_progress"
                break
        plan = d.setdefault("plan", {})
        plan["revised"] = False
        plan["reviews"] = []  # reset for fresh review cycle

    state.update(_reopen)
    return (
        True,
        "Plan-review reopened for revision. Edit the plan, then re-invoke PlanReview.",
    )


def is_phase_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate phase transition (skill invocation)."""

    current = state.current_phase
    status = state.get_phase_status(current)
    next_phase = extract_skill_name(hook_input)
    phases = _get_workflow_phases(config, state)

    # /continue — force-complete a stuck review phase (not plan-review)
    if next_phase == "continue":
        return _handle_continue(config, state)

    # /plan-approved — user approves plan and proceeds
    if next_phase == "plan-approved":
        return _handle_plan_approved(config, state)

    # /revise-plan — reopen plan-review after pass or exhaustion
    if next_phase == "revise-plan":
        return _handle_revise_plan(state)

    # /reset-plan-review — test-only state reset
    if next_phase == "reset-plan-review":
        if state.get("test_mode"):
            return True, "Test-mode reset allowed"
        raise ValueError("'/reset-plan-review' is only available in test mode.")

    # Block auto-phases from being invoked as skills
    if config.is_auto_phase(next_phase):
        raise ValueError(
            f"'{next_phase}' is an auto-phase — it starts automatically after the previous phase completes. "
            f"Do not invoke it as a skill."
        )

    # No phases yet — allow the first one
    if not current:
        _, message = validate_order(None, next_phase, phases)
        return True, message

    # Special case: research can run in parallel with explore
    if current == "explore" and status == "in_progress" and next_phase == "research":
        return True, "Running Research in parallel with Explore"

    # Block if current phase isn't done
    if next_phase and status != "completed":
        if next_phase == current:
            raise ValueError(
                f"Already in '{current}' phase. Complete the phase tasks instead of re-invoking the skill."
            )
        raise ValueError(
            f"Phase '{current}' is not completed. Finish it before transitioning to '{next_phase}'."
        )

    # Filter out auto-phases for skill-invoked ordering — they're handled by resolvers
    skill_phases = [p for p in phases if not config.is_auto_phase(p)]
    # When TDD is disabled, test-review/tests-review are skipped — remove from ordering
    if not state.get("tdd", False):
        skill_phases = [
            p for p in skill_phases if p not in ("test-review", "tests-review")
        ]
    prev_for_ordering = current
    if config.is_auto_phase(current):
        completed = [p["name"] for p in state.phases if p["status"] == "completed"]
        for p in reversed(completed):
            if p in skill_phases:
                prev_for_ordering = p
                break
    _, message = validate_order(prev_for_ordering, next_phase, skill_phases)
    return True, message


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — Commands (Bash)
# ═══════════════════════════════════════════════════════════════════


def is_command_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate Bash commands against phase restrictions."""

    phase = state.current_phase
    command = hook_input.get("tool_input", {}).get("command", "")

    # Read-only phases (also allow phase-specific commands like test runners)
    if phase in config.read_only_phases:
        phase_cmds = COMMANDS_MAP.get(phase, [])
        if phase_cmds and any(command.startswith(cmd) for cmd in phase_cmds):
            return True, f"Command allowed in phase: {phase}"
        return check_read_only(command, phase)

    # Docs phases
    if phase in config.docs_write_phases:
        return check_read_only(command, phase)

    # Read-only commands allowed in any phase
    if any(command.startswith(cmd) for cmd in READ_ONLY_COMMANDS):
        return True, f"Read-only command allowed in phase: {phase}"

    # Phase-specific whitelist
    check_phase_commands(command, phase)

    # PR create must use --json
    if phase == "pr-create":
        check_pr_create_command(command)

    # CI check must use --json
    if phase == "ci-check":
        check_ci_check_command(command)

    return True, f"Command '{command}' allowed in phase: {phase}"


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — File Write
# ═══════════════════════════════════════════════════════════════════


E2E_TEST_REPORT = ".claude/reports/E2E_TEST_REPORT.md"


def is_file_write_allowed(
    hook_input: dict, config: Config, state: StateStore
) -> Result:
    """Validate file write against phase and path restrictions."""

    phase = state.current_phase
    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    # Test mode: always allow writing the E2E test report
    if state.get("test_mode") and (
        file_path == E2E_TEST_REPORT or file_path.endswith(E2E_TEST_REPORT)
    ):
        return True, "E2E test report write allowed (test mode)"

    check_writable_phase(phase, config)

    if phase == "plan":
        require_agent_completed("Plan", state)
        check_plan_path(file_path, config)
        content = hook_input.get("tool_input", {}).get("content", "")
        if file_path == config.plan_file_path or file_path.endswith(
            config.plan_file_path
        ):
            workflow_type = state.get("workflow_type", "build")
            validate_plan_content(content, config, workflow_type)
        if config.contracts_file_path and (
            file_path == config.contracts_file_path
            or file_path.endswith(config.contracts_file_path)
        ):
            workflow_type = state.get("workflow_type", "build")
            if workflow_type == "build":
                validate_contracts_content(content)
    elif phase == "install-deps":
        check_package_manager_path(file_path)
    elif phase == "define-contracts":
        contract_files = state.get("contract_files", [])
        if contract_files:
            check_contract_file(file_path, contract_files)
        else:
            check_code_path(file_path)
    elif phase == "write-tests":
        check_test_path(file_path)
    elif phase == "write-code":
        workflow_type = state.get("workflow_type", "build")
        if workflow_type == "implement":
            check_implement_code_path(file_path, state)
        else:
            check_code_path(file_path)
    elif phase == "write-report":
        check_report_path(file_path, config)

    return True, f"File write allowed in phase: {phase}"


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — File Edit
# ═══════════════════════════════════════════════════════════════════


def is_file_edit_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate file edit against phase and path restrictions."""

    phase = state.current_phase
    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    # Test mode: always allow editing the E2E test report
    if state.get("test_mode") and (
        file_path == E2E_TEST_REPORT or file_path.endswith(E2E_TEST_REPORT)
    ):
        return True, "E2E test report edit allowed (test mode)"

    check_editable_phase(phase, config)

    if phase == "plan-review":
        check_plan_edit_path(file_path, config)
        workflow_type = state.get("workflow_type", "build")
        validate_plan_edit_preserves_sections(
            hook_input, file_path, config, workflow_type
        )
    elif phase in ("test-review", "tests-review"):
        check_test_edit_path(file_path, state)
    elif phase == "code-review":
        check_code_edit_path(file_path, state)

    return True, f"File edit allowed in phase: {phase}"


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — Agent
# ═══════════════════════════════════════════════════════════════════


def _is_parallel_research_allowed(state: StateStore, next_agent: str) -> bool:
    """Check if Research can run in parallel with an in-progress Explore."""
    explore = state.get_agent("Explore")
    return (
        explore is not None
        and explore.get("status") == "in_progress"
        and next_agent == "Research"
    )


def is_agent_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate agent invocation against phase and count restrictions."""

    phase = state.current_phase
    next_agent = extract_agent_name(hook_input)

    if phase == "explore" and _is_parallel_research_allowed(state, next_agent):
        return True, "Running Research in parallel with Explore"

    # Parallel case: research is running but user wants more Explore agents
    if (
        next_agent == "Explore"
        and phase == "research"
        and state.get_phase_status("explore") is not None
    ):
        phase = "explore"

    check_expected_agent(next_agent, phase, config)
    check_agent_count(next_agent, phase, config, state)
    check_revision_done(next_agent, phase, state)

    return True, f"{next_agent} agent allowed in phase: {phase}"


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — WebFetch
# ═══════════════════════════════════════════════════════════════════


def is_webfetch_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate that a WebFetch URL targets a safe domain."""

    url = hook_input.get("tool_input", {}).get("url", "")
    return check_safe_domain(url, config)


# ═══════════════════════════════════════════════════════════════════
# PostToolUse — Test execution
# ═══════════════════════════════════════════════════════════════════


def _is_test_command(command: str) -> bool:
    import re

    return any(re.search(pattern, command) for pattern in TEST_RUN_PATTERNS)


def is_test_executed(command: str) -> Result:
    """Check if the command is a valid test runner."""

    if _is_test_command(command):
        return True, f"Test command recognized: '{command}'"

    raise ValueError(
        f"Command '{command}' is not a valid test command"
        f"\nExpected patterns: {TEST_RUN_PATTERNS}"
    )
