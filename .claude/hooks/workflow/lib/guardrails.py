# .claude/hooks/lib/guardrails.py
import json
import yaml
from pathlib import Path
from typing import Tuple

CONFIG_PATH = Path(__file__).parent.parent / "config/workflow.yaml"


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def get_phase(config: dict, phase_name: str) -> dict | None:
    return next((p for p in config["phases"] if p["name"] == phase_name), None)


def check_tool_allowed(config: dict, state: dict, tool_name: str) -> Tuple[bool, str]:
    """Returns (allowed, reason)"""
    phase = get_phase(config, state["current_phase"])

    if not phase:
        return False, f"Unknown phase: {state['current_phase']}"

    if tool_name not in phase["allowed_tools"]:
        return (
            False,
            f"Tool '{tool_name}' not allowed in phase '{state['current_phase']}'. Allowed: {phase['allowed_tools']}",
        )

    return True, ""


def check_subagent_allowed(
    config: dict, state: dict, subagent: str
) -> Tuple[bool, str]:
    """Check subagent is allowed and in correct order"""
    phase = get_phase(config, state["current_phase"])

    if not phase:
        return False, f"Unknown phase: {state['current_phase']}"

    # Check phase allows this subagent
    if subagent not in phase["allowed_subagents"]:
        return (
            False,
            f"Subagent '{subagent}' not allowed in phase '{state['current_phase']}'",
        )

    # Check order
    order = config.get("subagent_order", [])
    if subagent in order:
        expected_idx = order.index(subagent)
        current_idx = state.get("subagent_order_index", 0)

        if expected_idx < current_idx:
            return (
                False,
                f"Subagent '{subagent}' already completed. Cannot go backwards.",
            )

        # Allow skipping forward but warn? Or strict order?
        # Strict:
        if expected_idx > current_idx + 1:
            skipped = order[current_idx:expected_idx]
            return False, f"Must invoke {skipped} before '{subagent}'"

    return True, ""


def check_phase_transition(
    config: dict, state: dict, new_phase: str
) -> Tuple[bool, str]:
    """Check if transitioning to new phase is allowed"""
    new_phase_config = get_phase(config, new_phase)

    if not new_phase_config:
        return False, f"Unknown phase: {new_phase}"

    # Check prerequisite phase
    requires = new_phase_config.get("requires_phase")
    if requires and requires not in state["phase_history"]:
        return False, f"Phase '{new_phase}' requires completing '{requires}' first"

    # Check required tools were used in current phase
    current_phase = get_phase(config, state["current_phase"])
    if not current_phase:
        return False, f"Unknown current phase: {state['current_phase']}"

    required = current_phase.get("required_before_next", [])
    used = state["tools_used"]

    missing = [t for t in required if t not in used]
    if missing:
        return (
            False,
            f"Must use {missing} before leaving phase '{state['current_phase']}'",
        )

    return True, ""


def check_can_stop(config: dict, state: dict) -> Tuple[bool, str]:
    """Check if stopping is allowed"""
    conditions = config.get("stop_conditions", {})

    # Check required tools
    required_tools = conditions.get("require_tools_used", [])
    missing = [t for t in required_tools if t not in state["tools_used"]]
    if missing:
        return False, f"Cannot stop: must use tools {missing} first"

    # Check required phase reached
    required_phase = conditions.get("require_phase")
    if required_phase and required_phase not in state["phase_history"]:
        return False, f"Cannot stop: must reach phase '{required_phase}' first"

    # Check actual work done
    work = state.get("work_done", {})
    if not work.get("files_written") and not work.get("commands_run"):
        return False, "Cannot stop: no files written or commands executed"

    return True, ""


if __name__ == "__main__":
    config = load_config()
    print(json.dumps(config, indent=2))
