#!/usr/bin/env python3
"""Phase engine for workflow orchestration.

Manages phase definitions, ordering, transitions, and subagent mappings.
"""

import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.unified_loader import (  # type: ignore
    load_unified_config,
    get_agent_for_phase,
    clear_unified_cache,
    is_bypass_phase as _is_bypass_phase,
    can_bypass_from as _can_bypass_from,
    get_bypass_config,
)


def _get_phases_from_config(
    strategy: Literal["tdd", "test-after", "none"] = "tdd",
) -> list[str]:
    """Get complete phase order based on test strategy from unified config."""
    config = load_unified_config(validate=False)
    phases = config.phases

    if strategy == "none":
        return phases.get("simple", ["explore", "plan", "execute", "commit"])

    base = phases.get("base", [])
    if "code" not in base:
        return base

    code_idx = base.index("code")
    before = base[:code_idx]
    after = base[code_idx + 1:]

    if strategy == "tdd":
        return before + phases.get("tdd", []) + after
    if strategy == "test-after":
        return before + phases.get("test-after", []) + after

    return before + after


def _get_phase_subagents_from_config() -> dict[str, str]:
    """Get phase to subagent mapping from unified config."""
    config = load_unified_config(validate=False)
    return config.agents

# Type alias for test strategies
TestStrategy = Literal["tdd", "test-after", "none"]


class PhaseEngine:
    """Engine for managing workflow phases and transitions."""

    def __init__(self, test_strategy: TestStrategy = "tdd"):
        """Initialize the phase engine.

        Args:
            test_strategy: The testing strategy to use
        """
        self._test_strategy = test_strategy
        self._phases: list[str] | None = None
        self._subagents: dict[str, str] | None = None

    @property
    def phases(self) -> list[str]:
        """Get the ordered list of phases.

        Returns:
            List of phase names in execution order
        """
        if self._phases is None:
            self._phases = _get_phases_from_config(self._test_strategy)
        return self._phases

    @property
    def subagents(self) -> dict[str, str]:
        """Get the phase to subagent mapping.

        Returns:
            Dictionary mapping phases to subagents
        """
        if self._subagents is None:
            self._subagents = _get_phase_subagents_from_config()
        return self._subagents

    def get_phase_index(self, phase: str) -> int | None:
        """Get the index of a phase.

        Args:
            phase: Phase name

        Returns:
            Index of phase or None if not found
        """
        if phase in self.phases:
            return self.phases.index(phase)
        return None

    def get_subagent(self, phase: str) -> str | None:
        """Get the subagent for a phase.

        Args:
            phase: Phase name

        Returns:
            Subagent name or None if not found
        """
        return self.subagents.get(phase)

    def is_valid_phase(self, phase: str) -> bool:
        """Check if a phase name is valid.

        Args:
            phase: Phase name to validate

        Returns:
            True if phase is valid
        """
        return phase in self.phases

    def is_bypass_phase(self, phase: str) -> bool:
        """Check if a phase is a bypass phase.

        Args:
            phase: Phase name to check

        Returns:
            True if phase is a bypass phase
        """
        return _is_bypass_phase(phase)

    def can_bypass_to(self, current_phase: str, bypass_phase: str) -> tuple[bool, str]:
        """Check if can transition to a bypass phase from current phase.

        Args:
            current_phase: Current phase
            bypass_phase: Target bypass phase

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.is_bypass_phase(bypass_phase):
            return False, f"'{bypass_phase}' is not a bypass phase"

        config = get_bypass_config(bypass_phase)
        if config is None:
            return False, f"No bypass config for '{bypass_phase}'"

        if current_phase in config.cannot_bypass:
            return False, f"Cannot enter {bypass_phase} from '{current_phase}' (pre-coding phase)"

        if current_phase in config.can_bypass:
            return True, ""

        return False, f"Cannot enter {bypass_phase} from '{current_phase}'"

    def is_valid_transition(
        self, current_phase: str | None, next_phase: str
    ) -> tuple[bool, str]:
        """Validate a phase transition.

        Args:
            current_phase: Current phase (None if at start)
            next_phase: Target phase

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if transitioning to a bypass phase
        if self.is_bypass_phase(next_phase) and current_phase is not None:
            return self.can_bypass_to(current_phase, next_phase)

        if next_phase not in self.phases:
            return False, f"Invalid phase: '{next_phase}'"

        if current_phase is None:
            if next_phase == self.phases[0]:
                return True, ""
            return False, f"Must start with '{self.phases[0]}', not '{next_phase}'"

        # Allow returning from bypass phase to stored phase
        if self.is_bypass_phase(current_phase):
            # From bypass phase, can go to any valid phase
            return True, ""

        if current_phase not in self.phases:
            return False, f"Invalid current phase: '{current_phase}'"

        current_idx = self.phases.index(current_phase)
        next_idx = self.phases.index(next_phase)

        if next_idx < current_idx:
            return False, f"Cannot go backwards from '{current_phase}' to '{next_phase}'"

        if next_idx > current_idx + 1:
            skipped = self.phases[current_idx + 1 : next_idx]
            return False, f"Must complete {skipped} before '{next_phase}'"

        return True, ""

    def get_next_phase(self, current_phase: str) -> str | None:
        """Get the next phase after current.

        Args:
            current_phase: Current phase name

        Returns:
            Next phase name or None if at last phase
        """
        idx = self.get_phase_index(current_phase)
        if idx is not None and idx + 1 < len(self.phases):
            return self.phases[idx + 1]
        return None

    def get_previous_phase(self, current_phase: str) -> str | None:
        """Get the previous phase before current.

        Args:
            current_phase: Current phase name

        Returns:
            Previous phase name or None if at first phase
        """
        idx = self.get_phase_index(current_phase)
        if idx is not None and idx > 0:
            return self.phases[idx - 1]
        return None

    def is_first_phase(self, phase: str) -> bool:
        """Check if phase is the first phase.

        Args:
            phase: Phase name

        Returns:
            True if phase is first
        """
        return len(self.phases) > 0 and phase == self.phases[0]

    def is_last_phase(self, phase: str) -> bool:
        """Check if phase is the last phase.

        Args:
            phase: Phase name

        Returns:
            True if phase is last
        """
        return len(self.phases) > 0 and phase == self.phases[-1]

    def is_subagent_allowed(self, phase: str, subagent: str) -> bool:
        """Check if a subagent is allowed for a phase.

        Args:
            phase: Phase name
            subagent: Subagent name

        Returns:
            True if subagent is allowed for phase
        """
        return self.subagents.get(phase) == subagent


# Module-level singleton
_engine: PhaseEngine | None = None
_engine_strategy: TestStrategy | None = None


def get_engine(test_strategy: TestStrategy = "tdd") -> PhaseEngine:
    """Get the phase engine instance for the given strategy.

    Recreates the engine if the strategy differs from the cached one.

    Args:
        test_strategy: Testing strategy

    Returns:
        PhaseEngine instance
    """
    global _engine, _engine_strategy
    if _engine is None or _engine_strategy != test_strategy:
        _engine = PhaseEngine(test_strategy)
        _engine_strategy = test_strategy
    return _engine


# Convenience functions for backward compatibility
def get_phase_order(test_strategy: TestStrategy = "tdd") -> list[str]:
    """Get phase order for strategy."""
    return _get_phases_from_config(test_strategy)


def get_all_phases(test_strategy: str = "tdd") -> list[str]:
    """Get all phases (backward compatible alias)."""
    strategy_map = {
        "TDD": "tdd",
        "TA": "test-after",
        "test_after": "test-after",
    }
    normalized = strategy_map.get(test_strategy, test_strategy)
    return get_phase_order(normalized)  # type: ignore


def get_phase_subagent(phase: str) -> str | None:
    """Get subagent for a phase."""
    return get_agent_for_phase(phase)


def is_valid_transition(
    current_phase: str | None, next_phase: str
) -> tuple[bool, str]:
    """Validate a phase transition."""
    return get_engine().is_valid_transition(current_phase, next_phase)


def validate_order(
    current_item: str | None, next_item: str, order: list[str]
) -> tuple[bool, str]:
    """Validate transition based on item order (generic).

    Args:
        current_item: Current item (None if at start)
        next_item: Target item
        order: List of items in valid order

    Returns:
        Tuple of (is_valid, error_message)
    """
    if next_item not in order:
        return False, f"Invalid next item: '{next_item}'"

    if current_item is None:
        if next_item == order[0]:
            return True, ""
        return False, f"Must start with '{order[0]}', not '{next_item}'"

    if current_item not in order:
        return False, f"Invalid current item: '{current_item}'"

    current_idx = order.index(current_item)
    new_idx = order.index(next_item)

    if new_idx < current_idx:
        return False, f"Cannot go backwards from '{current_item}' to '{next_item}'"

    if new_idx > current_idx + 1:
        skipped = order[current_idx + 1 : new_idx]
        return False, f"Must complete {skipped} before '{next_item}'"

    return True, ""


if __name__ == "__main__":
    engine = PhaseEngine("tdd")
    print(f"Phases: {engine.phases}")
    print(f"Subagents: {engine.subagents}")
    print(f"Valid transition explore -> plan: {engine.is_valid_transition('explore', 'plan')}")
    print(f"Invalid transition explore -> commit: {engine.is_valid_transition('explore', 'commit')}")
