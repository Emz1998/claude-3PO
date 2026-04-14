"""resolvers.py — Post-recording state resolution.

After a recorder writes raw data to state.json, a resolver evaluates
the updated state and mutates state.json accordingly:
- Complete phases
- Start sub-phases (revisions)
- Increment iterations
- Update review statuses
"""

from typing import Literal

from .state_store import StateStore
from config import Config


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


def resolve_plan_review(config: Config, state: StateStore) -> None:
    """Evaluate plan review scores and update state accordingly."""
    last = state.last_plan_review
    if not last:
        return

    # Already resolved this review
    if last.get("status"):
        return

    scores = last.get("scores", {})
    confidence = scores.get("confidence_score", 0)
    quality = scores.get("quality_score", 0)

    if confidence == 0 and quality == 0:
        return

    try:
        is_revision_needed("plan", confidence, quality, config)
    except ValueError:
        state.set_last_plan_review_status("Fail")
        state.set_plan_revised(False)
        return

    state.set_last_plan_review_status("Pass")
    state.complete_phase("plan-review")


def resolve_code_review(config: Config, state: StateStore) -> None:
    """Evaluate code review scores and update state accordingly."""
    last = state.last_code_review
    if not last:
        return

    # Already resolved this review
    if last.get("status"):
        return

    scores = last.get("scores", {})
    confidence = scores.get("confidence_score", 0)
    quality = scores.get("quality_score", 0)

    if confidence == 0 and quality == 0:
        return

    try:
        is_revision_needed("code", confidence, quality, config)
    except ValueError:
        state.set_last_code_review_status("Fail")
        return

    state.set_last_code_review_status("Pass")
    state.complete_phase("code-review")


def resolve_test_review(config: Config, state: StateStore) -> None:
    """Evaluate test review verdict and update state accordingly."""
    last = state.last_test_review
    if not last:
        return

    verdict = last.get("verdict")

    if verdict == "Fail":
        return

    if verdict == "Pass":
        # Complete whichever variant is the current phase
        phase = state.current_phase
        if phase in ("test-review", "tests-review"):
            state.complete_phase(phase)
        else:
            state.complete_phase("test-review")


def resolve_quality_check(state: StateStore) -> None:
    """Evaluate quality check result and update state accordingly."""
    result = state.quality_check_result

    if result == "Pass":
        state.complete_phase("quality-check")


def resolve_write_code(state: StateStore) -> None:
    """Check if all expected code files are written and complete the phase."""
    to_write = state._basenames(state.code_files_to_write)
    written = state._basenames(state.code_files.get("file_paths", []))

    if to_write and not (to_write - written):
        state.complete_phase("write-code")


def resolve_write_tests(state: StateStore) -> None:
    """Check if tests are written and executed, then complete the phase."""
    tests = state.tests
    file_paths = tests.get("file_paths", [])

    if file_paths and tests.get("executed"):
        state.complete_phase("write-tests")


def resolve_plan(config: Config, state: StateStore) -> None:
    """Check if Plan agent completed and plan is written."""
    agent_name = config.get_required_agent("plan")
    if agent_name:
        agents = [a for a in state.agents if a.get("name") == agent_name]
        if not agents or not all(a.get("status") == "completed" for a in agents):
            return

    plan = state.plan
    if plan.get("written") and plan.get("file_path"):
        state.complete_phase("plan")


def resolve_pr_create(state: StateStore) -> None:
    """Check if PR is created and complete the phase."""
    if state.pr_status == "created":
        state.complete_phase("pr-create")


def resolve_ci_check(state: StateStore) -> None:
    """Check if CI passed and complete the phase."""
    if state.ci_status == "passed":
        state.complete_phase("ci-check")


def resolve_report(state: StateStore) -> None:
    """Check if report is written and complete the phase."""
    if state.report_written:
        state.complete_phase("write-report")


def resolve_explore(config: Config, state: StateStore) -> None:
    """Complete explore once all Explore agents are done."""
    agent_name = config.get_required_agent("explore")
    if not agent_name:
        return
    agents = [a for a in state.agents if a.get("name") == agent_name]
    if agents and all(a.get("status") == "completed" for a in agents):
        state.complete_phase("explore")


def resolve_research(config: Config, state: StateStore) -> None:
    """Complete research once all Research agents are done."""
    agent_name = config.get_required_agent("research")
    if not agent_name:
        return
    agents = [a for a in state.agents if a.get("name") == agent_name]
    if agents and all(a.get("status") == "completed" for a in agents):
        state.complete_phase("research")


def resolve_install_dependencies(state: StateStore) -> None:
    """Complete when dependencies.installed is True."""
    deps = state.dependencies
    if deps.get("installed"):
        state.complete_phase("install-deps")


def resolve_define_contracts(state: StateStore) -> None:
    """Complete when all contract names are found in written code files."""
    from pathlib import Path

    contracts = state.contracts
    if not contracts.get("written"):
        return

    # If already validated, just check completion
    if contracts.get("validated"):
        state.complete_phase("define-contracts")
        return

    # Validate: each contract name must appear in a written code file
    names = contracts.get("names", [])
    code_files = contracts.get("code_files", [])

    if not names or not code_files:
        return

    # Read each code file and check for contract names
    found_names = set()
    for fp in code_files:
        path = Path(fp)
        if path.exists():
            content = path.read_text()
            for name in names:
                if name in content:
                    found_names.add(name)

    if found_names >= set(names):
        state.set_contracts_validated(True)
        state.complete_phase("define-contracts")


def resolve_create_tasks(state: StateStore) -> None:
    """Complete create-tasks based on workflow type.

    Build: all plan ## Tasks bullets have a matching created task.
    Implement: all project tasks have at least one subtask.
    """
    workflow_type = state.get("workflow_type", "build")
    if workflow_type == "implement":
        if state.all_project_tasks_have_subtasks:
            state.complete_phase("create-tasks")
    else:
        if state.all_tasks_created:
            state.complete_phase("create-tasks")


def resolve_validate(state: StateStore) -> None:
    """Evaluate validate result (same as quality-check)."""
    result = state.quality_check_result
    if result == "Pass":
        state.complete_phase("validate")


def _auto_start_next(config: Config, state: StateStore, skip_checkpoint: bool = False) -> None:
    """If the current phase just completed and the next is an auto-phase, start it."""
    phase = state.current_phase
    if not phase:
        return
    if state.get_phase_status(phase) != "completed":
        return

    # Checkpoint: plan-review pass pauses for user to /plan-approved or /revise-plan
    if phase == "plan-review" and not skip_checkpoint:
        return

    workflow_type = state.get("workflow_type", "build")
    phases = config.get_phases(workflow_type) or config.main_phases

    if phase not in phases:
        return

    idx = phases.index(phase)
    if idx + 1 >= len(phases):
        return

    next_phase = phases[idx + 1]
    if not config.is_auto_phase(next_phase):
        return

    # For TDD: skip write-tests / test-review / tests-review if tdd=False
    tdd = state.get("tdd", False)
    if not tdd and next_phase in ("write-tests",):
        # Skip write-tests and the following test-review/tests-review
        skip_idx = idx + 1
        while skip_idx < len(phases) and phases[skip_idx] in ("write-tests", "test-review", "tests-review"):
            skip_idx += 1
        if skip_idx < len(phases) and config.is_auto_phase(phases[skip_idx]):
            next_phase = phases[skip_idx]
        else:
            return

    state.add_phase(next_phase)


def _check_workflow_complete(config: Config, state: StateStore) -> None:
    """If all required phases are completed, mark workflow as completed."""
    if state.get("status") == "completed":
        return

    workflow_type = state.get("workflow_type", "build")
    phases = config.get_phases(workflow_type) or config.main_phases
    skip = state.get("skip", [])
    tdd = state.get("tdd", False)

    required = [p for p in phases if p not in skip]
    if not tdd:
        required = [p for p in required if p not in ("write-tests", "test-review", "tests-review")]

    completed = {p["name"] for p in state.phases if p["status"] == "completed"}
    if all(p in completed for p in required):
        state.set("status", "completed")
        state.set("workflow_active", False)


def resolve(config: Config, state: StateStore) -> None:
    """Main resolver — dispatch based on current phase."""
    phase = state.current_phase

    resolvers = {
        "explore": lambda: resolve_explore(config, state),
        "research": lambda: resolve_research(config, state),
        "plan": lambda: resolve_plan(config, state),
        "plan-review": lambda: resolve_plan_review(config, state),
        "install-deps": lambda: resolve_install_dependencies(state),
        "define-contracts": lambda: resolve_define_contracts(state),
        "create-tasks": lambda: resolve_create_tasks(state),
        "write-tests": lambda: resolve_write_tests(state),
        "test-review": lambda: resolve_test_review(config, state),
        "tests-review": lambda: resolve_test_review(config, state),
        "write-code": lambda: resolve_write_code(state),
        "code-review": lambda: resolve_code_review(config, state),
        "quality-check": lambda: resolve_quality_check(state),
        "validate": lambda: resolve_validate(state),
        "pr-create": lambda: resolve_pr_create(state),
        "ci-check": lambda: resolve_ci_check(state),
        "write-report": lambda: resolve_report(state),
    }

    resolver = resolvers.get(phase)
    if resolver:
        resolver()

    # Parallel case: resolve explore if it's still in_progress while research is current
    if phase == "research" and state.get_phase_status("explore") == "in_progress":
        resolve_explore(config, state)

    # Auto-start next phase if it's an auto-phase
    _auto_start_next(config, state)

    # Check if all required phases are done
    _check_workflow_complete(config, state)
