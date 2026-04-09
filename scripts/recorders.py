"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

from typing import Any


from utils import StateStore, is_revision_needed


# ---------------------------------------------------------------------------
# Agent recording
# ---------------------------------------------------------------------------


def record_agent_invocation(
    store: StateStore, agent_type: str, tool_use_id: str
) -> None:
    """Append an agent entry as 'running' to state.agents[]."""

    def _update(state: dict) -> None:
        state.setdefault("agents", []).append(
            {
                "agent_type": agent_type,
                "status": "running",
                "tool_use_id": tool_use_id,
            }
        )

    store.update(_update)


def record_agent_stoppage(store: StateStore, agent_type: str, tool_use_id: str) -> None:
    """Append an agent entry as 'completed' to state.agents[]."""

    def _update(state: dict) -> None:
        agents = state.get("agents", [])
        for agent in agents:
            if (
                agent.get("agent_type") == agent_type
                and agent.get("tool_use_id") == tool_use_id
            ):
                agent["status"] = "completed"
                break
        state["agents"] = agents

    store.update(_update)


def record_agent(hook_input: dict[str, Any], store: StateStore) -> None:

    hook_event_name = hook_input.get("hook_event_name", "")

    if hook_event_name == "PreToolUse":
        tool_name = hook_input.get("tool_name", "")
        if tool_name == "Agent":
            tool_use_id = hook_input.get("tool_use_id", "")
            agent_type = hook_input.get("subagent_type", "")

            record_agent_invocation(store, agent_type, tool_use_id)

    elif hook_event_name == "Stop":
        tool_name = hook_input.get("tool_name", "")
        if tool_name == "Agent":
            tool_use_id = hook_input.get("tool_use_id", "")
            agent_type = hook_input.get("agent_type", "")

            record_agent_stoppage(store, agent_type, tool_use_id)


def record_next_phase(
    next_phase: str,
    phase_order: list[str],
    completed_phases: list[str],
) -> str:
    next_phase_idx = phase_order.index(next_phase)
    phases_before_next = phase_order[:next_phase_idx]
    if not all(phase in completed_phases for phase in phases_before_next):
        raise ValueError(
            f"Cannot move to '{next_phase}' before completing {phases_before_next}"
        )
    return f"Phase {next_phase} recorded"


if __name__ == "__main__":
    print("hello")
