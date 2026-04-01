"""agent_guard.py — Phase-based agent validation using flat state model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

EXPLORE_MAX = 3
RESEARCH_MAX = 2
PLAN_MAX = 1
PLAN_REVIEW_MAX = 3
TASK_MANAGER_MAX = 1
TEST_REVIEWER_MAX = 3
VALIDATOR_MAX = 1


def count(agents: list[dict], agent_type: str) -> int:
    return sum(1 for a in agents if a.get("agent_type") == agent_type)


def count_completed(agents: list[dict], agent_type: str) -> int:
    return sum(1 for a in agents if a.get("agent_type") == agent_type and a.get("status") == "completed")


def _record_agent(store: StateStore, agent_type: str, tool_use_id: str) -> None:
    def _update(state: dict) -> None:
        state.setdefault("agents", []).append({
            "agent_type": agent_type,
            "status": "running",
            "tool_use_id": tool_use_id,
        })
    store.update(_update)


def validate(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Validate an Agent tool invocation against the current phase.

    Returns ("allow", "") or ("block", reason).
    Side effect: records the agent as "running" in state on allow.
    """
    tool_input = hook_input.get("tool_input", {})
    agent_type = tool_input.get("subagent_type", "")
    tool_use_id = hook_input.get("tool_use_id", "")
    run_in_background = tool_input.get("run_in_background", False)

    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    phase = state.get("phase", "")
    agents = state.get("agents", [])
    skip_explore = state.get("skip_explore", False)
    skip_research = state.get("skip_research", False)

    # -----------------------------------------------------------------------
    # explore phase: Explore + Research agents
    # -----------------------------------------------------------------------
    if phase == "explore":
        if agent_type in ("Explore", "Research"):
            if run_in_background:
                return "block", f"Agent '{agent_type}' must not run in background — set run_in_background to false"
            if agent_type == "Explore":
                if skip_explore:
                    return "block", "Explore agents skipped (--skip-explore)"
                current = count(agents, "Explore")
                if current >= EXPLORE_MAX:
                    return "block", f"Max agents ({EXPLORE_MAX}) for 'Explore' reached"
            else:  # Research
                if skip_research:
                    return "block", "Research agents skipped (--skip-research)"
                current = count(agents, "Research")
                if current >= RESEARCH_MAX:
                    return "block", f"Max agents ({RESEARCH_MAX}) for 'Research' reached"
            _record_agent(store, agent_type, tool_use_id)
            return "allow", ""
        return "block", f"Agent '{agent_type}' not allowed in phase 'explore'. Allowed: Explore, Research"

    # -----------------------------------------------------------------------
    # plan phase: Plan agent only
    # -----------------------------------------------------------------------
    if phase == "plan":
        if agent_type != "Plan":
            return "block", f"Agent '{agent_type}' not allowed in phase 'plan'. Allowed: Plan"
        current = count(agents, "Plan")
        if current >= PLAN_MAX:
            return "block", f"Max agents ({PLAN_MAX}) for 'Plan' reached"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # -----------------------------------------------------------------------
    # review phase: PlanReview only, requires plan_written
    # -----------------------------------------------------------------------
    if phase == "review":
        if agent_type != "PlanReview":
            return "block", f"Agent '{agent_type}' not allowed in phase 'review'. Allowed: PlanReview"
        if not state.get("plan_written"):
            return "block", "PlanReview requires a written plan first (plan_written must be true)"
        current = count(agents, "PlanReview")
        if current >= PLAN_REVIEW_MAX:
            return "block", f"Max agents ({PLAN_REVIEW_MAX}) for 'PlanReview' reached"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # -----------------------------------------------------------------------
    # task-create phase: TaskManager only
    # -----------------------------------------------------------------------
    if phase == "task-create":
        if agent_type != "TaskManager":
            return "block", f"Agent '{agent_type}' not allowed in phase 'task-create'. Allowed: TaskManager"
        current = count(agents, "TaskManager")
        if current >= TASK_MANAGER_MAX:
            return "block", f"Max agents ({TASK_MANAGER_MAX}) for 'TaskManager' reached"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # -----------------------------------------------------------------------
    # write-tests phase: TestReviewer only, requires test files
    # -----------------------------------------------------------------------
    if phase == "write-tests":
        if agent_type != "TestReviewer":
            return "block", f"Agent '{agent_type}' not allowed in phase 'write-tests'. Allowed: TestReviewer"
        test_files = state.get("test_files_created", [])
        if not test_files:
            return "block", "TestReviewer requires test files to be written first (test_files_created must be non-empty)"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # -----------------------------------------------------------------------
    # write-code phase: Validator only — triggers validate phase transition
    # -----------------------------------------------------------------------
    if phase == "write-code":
        if agent_type != "Validator":
            return "block", f"Agent '{agent_type}' not allowed in phase 'write-code'. Allowed: Validator"
        # Advance to validate phase
        def _advance(s: dict) -> None:
            s["phase"] = "validate"
        store.update(_advance)
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # -----------------------------------------------------------------------
    # validate phase: Validator only
    # -----------------------------------------------------------------------
    if phase == "validate":
        if agent_type != "Validator":
            return "block", f"Agent '{agent_type}' not allowed in phase 'validate'. Allowed: Validator"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # -----------------------------------------------------------------------
    # All other phases: block agents
    # -----------------------------------------------------------------------
    return "block", f"Agent '{agent_type}' not allowed in phase '{phase}'"
