"""Tests for lib/parallel_check.py — parallel explore+research predicate."""

import pytest

from lib.parallel_check import is_parallel_explore_research


@pytest.mark.parametrize(
    "phase,status,skill,expected",
    [
        ("explore", "in_progress", "research", True),
        ("explore", "completed", "research", False),
        ("explore", "in_progress", "plan", False),
        ("research", "in_progress", "research", False),
        (None, "in_progress", "research", False),
        ("explore", None, "research", False),
        ("", "", "", False),
    ],
)
def test_is_parallel_explore_research(phase, status, skill, expected):
    assert is_parallel_explore_research(phase, status, skill) is expected
