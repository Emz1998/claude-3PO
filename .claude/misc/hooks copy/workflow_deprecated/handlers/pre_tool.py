#!/usr/bin/env python3
"""PreToolUse handler that routes to appropriate guards.

Consolidated entry point for all PreToolUse validation.
"""

import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from guards.phase_transition import PhaseTransitionGuard  # type: ignore
from guards.subagent_access import SubagentAccessGuard  # type: ignore
from trackers.release_plan_tracker import ReleasePlanTracker  # type: ignore
from release_plan.getters import get_current_feature_id  # type: ignore
from release_plan.utils import get_feature_test_strategy  # type: ignore

TestStrategy = Literal["tdd", "test-after", "none"]

_TOOL_ACTION_MAP: dict[str, str] = {
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Bash": "bash",
    "Skill": "invoke",
}


def _map_tool_to_action(tool_name: str) -> str | None:
    """Map a tool name to a deliverable action."""
    return _TOOL_ACTION_MAP.get(tool_name)


def _get_tool_value(tool_name: str, tool_input: dict) -> str:
    """Extract the relevant value from tool input for matching."""
    if tool_name in ("Read", "Write", "Edit"):
        return tool_input.get("file_path", "")
    if tool_name == "Bash":
        return tool_input.get("command", "")
    if tool_name == "Skill":
        return tool_input.get("skill", "")
    return ""


def _normalize_test_strategy(raw_strategy: str | None) -> TestStrategy:
    """Normalize test strategy from release-plan to internal format.

    Args:
        raw_strategy: Raw strategy value from release-plan ("TDD", "TA", or None)

    Returns:
        Normalized strategy: "tdd", "test-after", or "none"
    """
    if raw_strategy is None:
        return "none"

    strategy_map: dict[str, TestStrategy] = {
        "TDD": "tdd",
        "tdd": "tdd",
        "TA": "test-after",
        "test-after": "test-after",
        "test_after": "test-after",
    }
    return strategy_map.get(raw_strategy, "none")


def _get_current_test_strategy() -> TestStrategy:
    """Get the test strategy for the current feature.

    Returns:
        Normalized test strategy
    """
    feature_id = get_current_feature_id()
    if not feature_id:
        return "none"

    raw_strategy = get_feature_test_strategy(feature_id)
    return _normalize_test_strategy(raw_strategy)


class PreToolHandler:
    """Handler for PreToolUse events."""

    def __init__(self):
        """Initialize the handler."""
        self._state = get_manager()
        self._test_strategy = _get_current_test_strategy()
        self._phase_guard = PhaseTransitionGuard(self._test_strategy)
        self._subagent_guard = SubagentAccessGuard(self._test_strategy)
        self._release_plan_tracker = ReleasePlanTracker()

    def is_active(self) -> bool:
        """Check if handler is active (workflow is active)."""
        return self._state.is_workflow_active()

    def check_strict_order(self, tool_name: str, tool_input: dict) -> None:
        """Block tool if strict_order enforcement applies.

        Args:
            tool_name: Name of the tool being called
            tool_input: Tool input parameters
        """
        action = _map_tool_to_action(tool_name)
        if action is None:
            return
        value = _get_tool_value(tool_name, tool_input)
        reason = self._state.get_strict_order_block_reason(action, value)
        if reason:
            from core.workflow_auditor import get_auditor  # type: ignore

            get_auditor().log_decision("STRICT_ORDER", "BLOCK", f"{action} on {value}")
            print(reason, file=sys.stderr)
            sys.exit(2)

    def run(self, hook_input: dict) -> None:
        """Run the handler against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        hook_event_name = hook_input.get("hook_event_name", "")
        if hook_event_name != "PreToolUse":
            sys.exit(0)

        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})

        # Strict order enforcement for Read/Write/Edit/Bash/Skill
        if tool_name in _TOOL_ACTION_MAP:
            self.check_strict_order(tool_name, tool_input)

        # Route to appropriate guard based on tool
        if tool_name == "Skill":
            # Check phase transition
            self._phase_guard.run(hook_input)
            # Check release plan logging validation
            self._release_plan_tracker.run_pre_tool(hook_input)

        elif tool_name == "Task":
            # Check subagent access
            self._subagent_guard.run(hook_input)

        # All checks passed
        sys.exit(0)


def handle_pre_tool(hook_input: dict) -> None:
    """Handle a PreToolUse event.

    Args:
        hook_input: The hook input dictionary
    """
    handler = PreToolHandler()
    handler.run(hook_input)


def main() -> None:
    """Main entry point for the handler."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    handler = PreToolHandler()
    handler.run(hook_input)


if __name__ == "__main__":
    main()
