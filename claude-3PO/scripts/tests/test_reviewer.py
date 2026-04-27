"""Tests for lib/reviewer.py — unified template-agnostic headless reviewer."""

import json
from unittest.mock import patch

import pytest

from lib.reviewer import invoke_reviewer, template_tree_check


# ── helpers ──────────────────────────────────────────────────────────────────


def _jsonl(text: str, thread_id: str | None = "sid-1") -> str:
    """Assemble a mock JSONL blob mimicking codex/claude's streamed output."""
    lines = []
    if thread_id is not None:
        lines.append(json.dumps({"thread_id": thread_id}))
    lines.append(json.dumps({"item": {"text": text}}))
    return "\n".join(lines)


def _always_ok(_response: str) -> tuple[bool, str]:
    return True, ""


def _always_diverges(_response: str) -> tuple[bool, str]:
    return False, "diff-payload"


# ── invoke_reviewer ──────────────────────────────────────────────────────────


class TestInvokeReviewer:
    def test_returns_response_when_conforms(self):
        raw = _jsonl("anything")
        with patch("lib.reviewer.invoke_headless_agent", return_value=raw):
            out = invoke_reviewer("codex", "p", _always_ok, lambda d: "x")
        assert out == "anything"

    def test_failure_returns_sentinel_with_llm_name(self):
        with patch("lib.reviewer.invoke_headless_agent", return_value=None):
            out = invoke_reviewer("codex", "p", _always_ok, lambda d: "x")
        assert "codex" in out
        assert "failed to respond" in out

    def test_missing_session_id_returns_sentinel(self):
        raw = _jsonl("body", thread_id=None)
        with patch("lib.reviewer.invoke_headless_agent", return_value=raw):
            out = invoke_reviewer("claude", "p", _always_ok, lambda d: "x")
        assert "claude" in out
        assert "session id" in out

    def test_recursion_uses_corrected_prompt_and_session(self):
        non_matching = _jsonl("wrong", thread_id="sid-1")
        ok = _jsonl("right", thread_id="sid-2")

        def conforms(response: str) -> tuple[bool, str]:
            return (response == "right", "diff-payload")

        builder = lambda diff: f"corrected::{diff}"
        with patch(
            "lib.reviewer.invoke_headless_agent",
            side_effect=[non_matching, ok],
        ) as m:
            out = invoke_reviewer(
                "codex", "p", conforms, builder, attempts_left=3
            )
        assert out == "right"
        # Second round carries pinned session (inside options) + correction prompt.
        second = m.call_args_list[1]
        assert second.args[0] == "corrected::diff-payload"
        assert second.args[1].session_id == "sid-1"

    def test_recursion_exhausted_returns_last_response(self):
        raw = _jsonl("wrong")
        with patch("lib.reviewer.invoke_headless_agent", return_value=raw):
            out = invoke_reviewer(
                "codex", "p", _always_diverges, lambda d: "x", attempts_left=1
            )
        assert out == "wrong"

    def test_does_not_recurse_when_conforms(self):
        # Conforms on first try → subprocess must be called exactly once.
        raw = _jsonl("right")
        with patch(
            "lib.reviewer.invoke_headless_agent", return_value=raw
        ) as m:
            invoke_reviewer(
                "codex", "p", _always_ok, lambda d: "x", attempts_left=5
            )
        assert m.call_count == 1

    def test_forwards_timeout_and_json_flag(self):
        raw = _jsonl("response")
        with patch("lib.reviewer.invoke_headless_agent", return_value=raw) as m:
            invoke_reviewer(
                "claude", "p", _always_ok, lambda d: "x", timeout=42
            )
        # Timeout stays keyword; JSONL mode now lives on the options dataclass.
        assert m.call_args.kwargs["timeout"] == 42
        assert m.call_args.args[1].output_format == "json"


# ── template_tree_check (adapter for markdown-template use case) ─────────────


class TestTemplateTreeCheck:
    def test_returns_ok_for_identical_markdown(self, tmp_path):
        tpl = tmp_path / "t.md"
        tpl.write_text("# Title\n\n## Section\n")
        check = template_tree_check(tpl)
        ok, feedback = check(tpl.read_text())
        assert ok is True
        assert feedback == ""

    def test_returns_diff_for_divergent_markdown(self, tmp_path):
        tpl = tmp_path / "t.md"
        tpl.write_text("# Title\n\n## Section\n")
        check = template_tree_check(tpl)
        ok, feedback = check("# Something Else\n")
        assert ok is False
        # Diff payload is non-empty so the correction builder has something to work with.
        assert feedback != ""
