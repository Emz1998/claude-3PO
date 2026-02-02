#!/usr/bin/env python3
"""Centralized phase configuration for workflow orchestration.

This module is the single source of truth for all phase definitions.
All phase names use kebab-case for consistency.
"""

from typing import Literal

# Base phases (always present in workflow)
PHASES: list[str] = ["explore", "plan", "plan-consult", "code", "commit"]

# TDD (Test-Driven Development) sub-phases - replace "code" phase
TDD_PHASES: list[str] = [
    "write-test",
    "review-test",
    "write-code",
    "code-review",
    "refactor",
    "validate",
]

# TA (Test-After) sub-phases - replace "code" phase
TA_PHASES: list[str] = [
    "write-code",
    "write-test",
    "review-test",
    "code-review",
    "refactor",
    "validate",
]

# Default phases when no test strategy specified
DEFAULT_PHASES: list[str] = ["explore", "plan", "plan-consult", "execute", "commit"]

# Type alias for test strategies
TestStrategy = Literal["tdd", "test-after", "none"]


def get_phase_order(test_strategy: TestStrategy = "tdd") -> list[str]:
    """Get complete phase order based on test strategy.

    Args:
        test_strategy: The testing strategy to use ("tdd", "test-after", or "none")

    Returns:
        Complete list of phases in execution order
    """
    code_idx = PHASES.index("code")
    before = PHASES[:code_idx]
    after = PHASES[code_idx + 1 :]  # skips "code"

    if test_strategy == "tdd":
        return before + TDD_PHASES + after

    if test_strategy == "test-after":
        return before + TA_PHASES + after

    # No test strategy - use base phases without "code" expansion
    return before + after


def get_all_phases(test_strategy: str = "tdd") -> list[str]:
    """Get all phases in order based on test strategy.

    This is an alias for get_phase_order for backward compatibility.

    Args:
        test_strategy: The testing strategy ("tdd", "test-after", or "none")

    Returns:
        Complete list of phases in execution order
    """
    # Normalize strategy names for backward compatibility
    strategy_map = {
        "TDD": "tdd",
        "TA": "test-after",
        "test_after": "test-after",
    }
    normalized = strategy_map.get(test_strategy, test_strategy)
    return get_phase_order(normalized)  # type: ignore


# Phase to subagent mapping (using kebab-case phase names)
PHASE_SUBAGENTS: dict[str, str] = {
    "explore": "codebase-explorer",
    "plan": "planner",
    "plan-consult": "plan-consultant",
    "commit": "version-manager",
    "write-test": "test-engineer",
    "review-test": "test-reviewer",
    "write-code": "main-agent",
    "code-review": "code-reviewer",
    "refactor": "main-agent",
    "validate": "validator",
}
