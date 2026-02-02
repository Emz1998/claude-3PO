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
from guards.read_order import ReadOrderGuard  # type: ignore
from trackers.release_plan_tracker import ReleasePlanTracker  # type: ignore
from release_plan.getters import get_current_feature_id  # type: ignore
from release_plan.utils import get_feature_test_strategy  # type: ignore

TestStrategy = Literal["tdd", "test-after", "none"]


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
        self._read_guard = ReadOrderGuard()
        self._release_plan_tracker = ReleasePlanTracker()

    def is_active(self) -> bool:
        """Check if handler is active (workflow is active)."""
        return self._state.is_workflow_active()

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

        # Route to appropriate guard based on tool
        if tool_name == "Skill":
            # Check phase transition
            self._phase_guard.run(hook_input)
            # Check release plan logging validation
            self._release_plan_tracker.run_pre_tool(hook_input)

        elif tool_name == "Task":
            # Check subagent access
            self._subagent_guard.run(hook_input)

        elif tool_name == "Read":
            # Check read order (optional enforcement)
            # self._read_guard.run(hook_input)
            pass

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
