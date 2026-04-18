"""Tests for lib/clarity_check.py — headless Claude review wrapper.

The module shells out to ``claude -p --output-format json`` to evaluate a
user prompt and return either ``"clear"`` or ``"vague"``. Tests fully mock
``subprocess.run`` so they stay deterministic and offline.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from lib import clarity_check


def _stdout_json(verdict: str, session_id: str = "sess_abc123") -> str:
    """Build a fake `claude -p --output-format json` stdout payload."""
    return json.dumps({
        "session_id": session_id,
        "result": verdict,
    })


class TestRunInitial:
    """run_initial returns (session_id, verdict) and shells to claude -p."""

    @patch("lib.clarity_check.subprocess.run")
    def test_clear_verdict(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear"), stderr=""
        )
        sid, verdict = clarity_check.run_initial("add /logout endpoint")
        assert verdict == "clear"
        assert sid == "sess_abc123"

    @patch("lib.clarity_check.subprocess.run")
    def test_vague_verdict(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("vague"), stderr=""
        )
        sid, verdict = clarity_check.run_initial("do the thing")
        assert verdict == "vague"
        assert sid == "sess_abc123"

    @patch("lib.clarity_check.subprocess.run")
    def test_passes_prompt_to_claude(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear"), stderr=""
        )
        clarity_check.run_initial("my prompt text")
        # The user's prompt should be present in the stdin sent to claude.
        called_kwargs = mock_run.call_args.kwargs
        stdin_input = called_kwargs.get("input", "")
        assert "my prompt text" in stdin_input

    @patch("lib.clarity_check.subprocess.run")
    def test_invokes_claude_with_print_and_json(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear"), stderr=""
        )
        clarity_check.run_initial("something")
        cmd = mock_run.call_args.args[0]
        assert "claude" in cmd[0]
        assert "-p" in cmd or "--print" in cmd
        assert any("json" in c for c in cmd)

    @patch("lib.clarity_check.subprocess.run")
    def test_unknown_verdict_treated_as_vague(self, mock_run):
        """Fail-closed: anything other than 'clear' is vague."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("maybe"), stderr=""
        )
        _, verdict = clarity_check.run_initial("x")
        assert verdict == "vague"

    @patch("lib.clarity_check.subprocess.run")
    def test_malformed_json_treated_as_vague(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="not json at all", stderr=""
        )
        sid, verdict = clarity_check.run_initial("x")
        assert verdict == "vague"
        assert sid == ""

    @patch("lib.clarity_check.subprocess.run")
    def test_subprocess_error_treated_as_vague(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
        sid, verdict = clarity_check.run_initial("x")
        assert verdict == "vague"
        assert sid == ""


class TestRunResume:
    """run_resume continues an existing headless session and returns verdict."""

    @patch("lib.clarity_check.subprocess.run")
    def test_resume_clear(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear", "sess_xyz"), stderr=""
        )
        verdict = clarity_check.run_resume("sess_xyz", "Q: …\nA: …")
        assert verdict == "clear"

    @patch("lib.clarity_check.subprocess.run")
    def test_resume_vague(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("vague", "sess_xyz"), stderr=""
        )
        verdict = clarity_check.run_resume("sess_xyz", "Q: …\nA: …")
        assert verdict == "vague"

    @patch("lib.clarity_check.subprocess.run")
    def test_resume_passes_session_id_via_resume_flag(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear", "sess_xyz"), stderr=""
        )
        clarity_check.run_resume("sess_xyz", "payload")
        cmd = mock_run.call_args.args[0]
        assert "--resume" in cmd
        assert "sess_xyz" in cmd

    @patch("lib.clarity_check.subprocess.run")
    def test_resume_passes_qa_payload(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear", "sess_xyz"), stderr=""
        )
        clarity_check.run_resume("sess_xyz", "Q: foo\nA: bar")
        stdin_input = mock_run.call_args.kwargs.get("input", "")
        assert "Q: foo" in stdin_input
        assert "A: bar" in stdin_input

    @patch("lib.clarity_check.subprocess.run")
    def test_resume_malformed_treated_as_vague(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="garbage", stderr="")
        verdict = clarity_check.run_resume("sess_xyz", "x")
        assert verdict == "vague"

    @patch("lib.clarity_check.subprocess.run")
    def test_resume_failure_treated_as_vague(self, mock_run):
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="err")
        verdict = clarity_check.run_resume("sess_xyz", "x")
        assert verdict == "vague"
