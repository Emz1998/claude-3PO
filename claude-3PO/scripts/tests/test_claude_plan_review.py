"""Tests for headless/claude/claude_plan_review.py — plan-review orchestration.

The subprocess contract lives in ``lib.shell.invoke_claude`` and is covered by
``test_shell.py``. These tests patch ``invoke_claude`` at the import site so
they only verify orchestration: template loading, plan substitution, forwarding
of ``timeout``/``cwd``, and fail-open on a missing plan file.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from headless.claude.claude_plan_review import (
    invoke_claude_plan_review,
    _build_prompt,
    _load_template,
    PROMPT_PATH,
)


PATCH_TARGET = "headless.claude.claude_plan_review.invoke_claude"


@pytest.fixture
def plan_file(tmp_path: Path) -> Path:
    """Write a minimal plan markdown file and return its path."""
    p = tmp_path / "plan.md"
    p.write_text("# Plan\n\n- Step 1: do the thing\n- Step 2: verify\n")
    return p


# ── prompt template ──────────────────────────────────────────────


class TestPromptTemplate:
    def test_template_file_exists(self):
        assert PROMPT_PATH.is_file()

    def test_template_has_plan_placeholder(self):
        assert "{plan}" in _load_template()

    def test_build_prompt_substitutes_plan(self):
        out = _build_prompt("PLAN-BODY-XYZ")
        assert "PLAN-BODY-XYZ" in out
        assert "{plan}" not in out


# ── invoke_claude_plan_review ────────────────────────────────────


class TestInvokeClaudePlanReview:
    def test_returns_review_on_success(self, plan_file):
        with patch(PATCH_TARGET, return_value="VERDICT: PASS") as inv:
            out = invoke_claude_plan_review(plan_file, timeout=30)
        assert out == "VERDICT: PASS"
        inv.assert_called_once()

    def test_prompt_contains_plan_text(self, plan_file):
        with patch(PATCH_TARGET, return_value="ok") as inv:
            invoke_claude_plan_review(plan_file, timeout=30)
        prompt = inv.call_args.args[0]
        assert "Step 1: do the thing" in prompt

    def test_forwards_cwd_and_timeout(self, plan_file, tmp_path):
        with patch(PATCH_TARGET, return_value="ok") as inv:
            invoke_claude_plan_review(plan_file, timeout=7, cwd=tmp_path)
        kwargs = inv.call_args.kwargs
        assert kwargs["timeout"] == 7
        assert kwargs["cwd"] == tmp_path

    def test_passes_through_none_from_invoke_claude(self, plan_file):
        with patch(PATCH_TARGET, return_value=None):
            out = invoke_claude_plan_review(plan_file, timeout=30)
        assert out is None

    def test_returns_none_when_plan_missing(self, tmp_path):
        missing = tmp_path / "nope.md"
        with patch(PATCH_TARGET) as inv:
            out = invoke_claude_plan_review(missing, timeout=30)
        assert out is None
        inv.assert_not_called()
