"""Agent type/count guard — validates Agent tool invocations per phase."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

# Phase rules:
#   allowed  — maps agent_type → max count
#   ordered  — list of (dependent_agent, required_agent): dependent requires required to have run first
#   tdd_only — phase only active when TDD=true
PHASE_RULES: dict[str, dict] = {
    "explore": {
        "allowed": {"codebase-explorer": 3, "research-specialist": 2},
    },
    "decision": {
        "allowed": {"tech-lead": 1},
    },
    "plan": {
        "allowed": {"plan-specialist": 3, "plan-reviewer": 3},
        "ordered": [("plan-reviewer", "plan-specialist")],
    },
    "write-tests": {
        "allowed": {"test-engineer": 3, "test-reviewer": 3},
        "ordered": [("test-reviewer", "test-engineer")],
        "tdd_only": True,
    },
    "write-code": {
        "allowed": {},
    },
    "validate": {
        "allowed": {"qa-expert": 1},
    },
    "pr-create": {
        "allowed": {"version-manager": 1},
    },
}


def count(agents: list[dict], agent_type: str) -> int:
    return sum(1 for a in agents if a.get("agent_type") == agent_type)


def count_completed(agents: list[dict], agent_type: str) -> int:
    return sum(1 for a in agents if a.get("agent_type") == agent_type and a.get("status") == "completed")


def validate(hook_input: dict, state_path: Path | None = None) -> tuple[str, str]:
    """Validate an Agent tool invocation against the current phase rules.

    Returns ("allow", "") or ("block", reason).
    Side effect: records the agent as "running" in state on allow.
    """
    tool_input = hook_input.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")
    tool_use_id = hook_input.get("tool_use_id", "")

    path = state_path or DEFAULT_STATE_PATH
    store = StateStore(path)
    state = store.load()
    phases: list[dict] = state.get("phases", [])

    # task-manager runs before any phase — always allow
    if subagent_type == "task-manager":
        return "allow", ""

    # Find current in_progress phase
    current = next((p for p in phases if p["status"] == "in_progress"), None)
    if current is None:
        return "block", "No active phase. Invoke a phase skill first (e.g. /explore)"

    phase_name = current["name"]
    rules = PHASE_RULES.get(phase_name, {})
    allowed = rules.get("allowed", {})
    agents: list[dict] = current.get("agents", [])

    # TDD guard
    if rules.get("tdd_only") and not state.get("TDD", False):
        return "block", f"Phase '{phase_name}' requires TDD=true"

    # write-code blocks all agents
    if phase_name == "write-code":
        return "block", "Phase 'write-code': main agent writes code directly — no subagents allowed"

    # Agent type allowed?
    if subagent_type not in allowed:
        allowed_list = ", ".join(allowed.keys()) if allowed else "none"
        return "block", f"Agent '{subagent_type}' not allowed in phase '{phase_name}'. Allowed: {allowed_list}"

    # Ordering constraint
    for dependent, required in rules.get("ordered", []):
        if subagent_type == dependent:
            completed_required = count_completed(agents, required)
            completed_dependent = count_completed(agents, dependent)
            if completed_required <= completed_dependent:
                return "block", f"'{subagent_type}' requires '{required}' to complete first"

    # Max count check (running + completed)
    current_count = count(agents, subagent_type)
    max_count = allowed[subagent_type]
    if current_count >= max_count:
        return "block", f"Max agents ({max_count}) for '{subagent_type}' in phase '{phase_name}' reached. Iteration limit exceeded."

    # Record invocation as running
    def _record(s: dict) -> None:
        for p in s.get("phases", []):
            if p["name"] == phase_name:
                p["agents"].append({
                    "agent_type": subagent_type,
                    "status": "running",
                    "tool_use_id": tool_use_id,
                })
                break

    store.update(_record)
    return "allow", ""
