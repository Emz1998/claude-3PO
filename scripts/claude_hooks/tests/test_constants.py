"""Tests for constants.py — single source of truth for phases."""

import pytest


def test_phases_order():
    from scripts.claude_hooks.constants import PHASES

    assert PHASES == ["explore", "plan", "code", "validate", "push"]


def test_phases_no_concatenated_strings():
    """Regression: old code had 'validate' 'push' -> 'validatepush'."""
    from scripts.claude_hooks.constants import PHASES

    for phase in PHASES:
        assert len(phase) < 12, f"Suspiciously long phase name: '{phase}'"
    assert "validatepush" not in PHASES


def test_coding_phases():
    from scripts.claude_hooks.constants import CODING_PHASES

    assert CODING_PHASES == ["log", "commit"]


def test_coding_phases_no_stale_entries():
    """Regression: hook_recorder.py had ['mark', 'validate', 'commit']."""
    from scripts.claude_hooks.constants import CODING_PHASES

    assert "mark" not in CODING_PHASES
    assert "validate" not in CODING_PHASES
