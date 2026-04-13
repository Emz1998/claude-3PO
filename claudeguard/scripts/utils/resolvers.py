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
        if state.plan_review_count >= 3:
            raise ValueError("Plan review reached max iterations (3). Discontinuing.")
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
        if state.code_review_count >= 3:
            raise ValueError("Code review reached max iterations (3). Discontinuing.")
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
        if state.test_review_count >= 3:
            raise ValueError("Test review reached max iterations (3). Discontinuing.")
        return

    if verdict == "Pass":
        state.complete_phase("test-review")


def resolve_quality_check(state: StateStore) -> None:
    """Evaluate quality check result and update state accordingly."""
    result = state.quality_check_result

    if result == "Pass":
        state.complete_phase("quality-check")


def resolve_write_code(state: StateStore) -> None:
    """Check if all expected code files are written and complete the phase."""
    to_write = set(state.code_files_to_write)
    written = set(state.code_files.get("file_paths", []))

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
    """Complete when contracts are validated and written as code."""
    contracts = state.contracts
    if contracts.get("written") and contracts.get("validated"):
        state.complete_phase("define-contracts")


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
        "write-tests": lambda: resolve_write_tests(state),
        "test-review": lambda: resolve_test_review(config, state),
        "write-code": lambda: resolve_write_code(state),
        "code-review": lambda: resolve_code_review(config, state),
        "quality-check": lambda: resolve_quality_check(state),
        "pr-create": lambda: resolve_pr_create(state),
        "ci-check": lambda: resolve_ci_check(state),
        "write-report": lambda: resolve_report(state),
    }

    resolver = resolvers.get(phase)
    if resolver:
        resolver()
