"""agent_guard.py — Phase-based agent validation using nested state model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from build.config import (
    EXPLORE_MAX,
    RESEARCH_MAX,
    PLAN_MAX,
    PLAN_REVIEW_MAX,
    TEST_REVIEWER_MAX,
    QA_MAX,
)
from build.session_store import SessionStore


def count(agents: list[dict], agent_type: str) -> int:
    return sum(1 for a in agents if a.get("agent_type") == agent_type)


def count_completed(agents: list[dict], agent_type: str) -> int:
    return sum(
        1
        for a in agents
        if a.get("agent_type") == agent_type and a.get("status") == "completed"
    )


def validate(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Validate an Agent tool invocation against the current phase.

    Returns ("allow", "") or ("block", reason).
    Pure validation — no recording side effects.
    """
    tool_input = hook_input.get("tool_input", {})
    agent_type = tool_input.get("subagent_type", "")
    run_in_background = tool_input.get("run_in_background", False)

    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    # No agents may run in background during workflow
    if run_in_background:
        return (
            "block",
            f"Blocked: '{agent_type}' agent must run in foreground. Background agents are not allowed during workflow.",
        )

    phase = state.get("phase", "")
    agents = state.get("agents", [])
    skip = state.get("skip", [])

    # -----------------------------------------------------------------------
    # explore phase: Explore + Research agents
    # -----------------------------------------------------------------------
    if phase == "explore":
        if agent_type in ("Explore", "Research"):
            if agent_type == "Explore":
                if "explore" in skip:
                    return (
                        "block",
                        "Blocked: Explore agents skipped via --skip-explore. Remove the flag to use Explore agents.",
                    )
                current = count(agents, "Explore")
                if current >= EXPLORE_MAX:
                    return (
                        "block",
                        f"Blocked: max Explore agents ({EXPLORE_MAX}) reached. Proceed to the next phase.",
                    )
            else:  # Research
                if "research" in skip:
                    return (
                        "block",
                        "Blocked: Research agents skipped via --skip-research. Remove the flag to use Research agents.",
                    )
                current = count(agents, "Research")
                if current >= RESEARCH_MAX:
                    return (
                        "block",
                        f"Blocked: max Research agents ({RESEARCH_MAX}) reached. Proceed to the next phase.",
                    )
            return "allow", ""
        return (
            "block",
            f"Blocked: '{agent_type}' agent is not allowed during 'explore' phase. Only Explore and Research agents may run now.",
        )

    # -----------------------------------------------------------------------
    # plan phase: Plan agent only
    # -----------------------------------------------------------------------
    if phase == "plan":
        if agent_type != "Plan":
            return (
                "block",
                f"Blocked: '{agent_type}' agent is not allowed during 'plan' phase. Only the Plan agent may run now -- launch a Plan agent to proceed.",
            )
        current = count(agents, "Plan")
        if current >= PLAN_MAX:
            return (
                "block",
                f"Blocked: max Plan agents ({PLAN_MAX}) reached. Proceed to writing the plan.",
            )
        return "allow", ""

    # -----------------------------------------------------------------------
    # review phase: PlanReview only, requires plan_written
    # -----------------------------------------------------------------------
    if phase == "review":
        if agent_type != "PlanReview":
            return (
                "block",
                f"Blocked: '{agent_type}' agent is not allowed during 'review' phase. Only the PlanReview agent may run now.",
            )
        if not state.get("plan", {}).get("written"):
            return (
                "block",
                "Blocked: PlanReview requires a written plan. Write the plan to .claude/plans/ first.",
            )
        current = count(agents, "PlanReview")
        if current >= PLAN_REVIEW_MAX:
            return (
                "block",
                f"Blocked: max PlanReview agents ({PLAN_REVIEW_MAX}) reached. Proceed to the next phase.",
            )
        return "allow", ""

    # -----------------------------------------------------------------------
    # write-tests phase: TestReviewer only, requires test files
    # -----------------------------------------------------------------------
    if phase == "write-tests":
        if agent_type != "TestReviewer":
            return (
                "block",
                f"Blocked: '{agent_type}' agent is not allowed during 'write-tests' phase. Only the TestReviewer agent may run now.",
            )
        test_files = state.get("tests", {}).get("file_paths", [])
        if not test_files:
            return (
                "block",
                "Blocked: TestReviewer requires test files to be written first. Write test files before launching TestReviewer.",
            )
        return "allow", ""

    # -----------------------------------------------------------------------
    # write-code phase: QualityAssurance only — triggers validate phase transition
    # -----------------------------------------------------------------------
    if phase == "write-code":
        if agent_type != "QualityAssurance":
            return (
                "block",
                f"Blocked: '{agent_type}' agent is not allowed during 'write-code' phase. Only the QualityAssurance agent may run now.",
            )
        return "allow", ""

    # -----------------------------------------------------------------------
    # validate phase: QualityAssurance only
    # -----------------------------------------------------------------------
    if phase == "validate":
        if agent_type != "QualityAssurance":
            return (
                "block",
                f"Blocked: '{agent_type}' agent is not allowed during 'validate' phase. Only the QualityAssurance agent may run now.",
            )
        return "allow", ""

    # -----------------------------------------------------------------------
    # All other phases: block agents
    # -----------------------------------------------------------------------
    return (
        "block",
        f"Blocked: '{agent_type}' agent is not allowed during '{phase}' phase. No agents may run in this phase.",
    )
