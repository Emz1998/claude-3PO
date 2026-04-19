"""Tests for lib/subprocess_agents.py — git, headless agent, and clarity wrappers."""

import json
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from lib import subprocess_agents
from lib.subprocess_agents import run_git, invoke_headless_agent


# ══════════════════════════════════════════════════════════════════
# run_git
# ══════════════════════════════════════════════════════════════════


class TestRunGit:
    def test_returns_completed_process_on_success(self, tmp_path):
        fake = MagicMock(returncode=0, stdout=" M foo.py\n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            result = run_git(["status", "--porcelain"], cwd=tmp_path)
        assert result.returncode == 0
        assert result.stdout == " M foo.py\n"
        run.assert_called_once()
        args, kwargs = run.call_args
        assert args[0] == ["git", "status", "--porcelain"]
        assert kwargs["cwd"] == tmp_path

    def test_non_zero_exit_returned_not_raised(self, tmp_path):
        fake = MagicMock(returncode=128, stdout="", stderr="fatal")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            result = run_git(["status"], cwd=tmp_path)
        assert result.returncode == 128

    def test_passes_timeout_to_subprocess(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            run_git(["status"], cwd=tmp_path)
        assert run.call_args.kwargs.get("timeout") is not None

    def test_returns_nonzero_on_timeout(self, tmp_path):
        err = subprocess.TimeoutExpired(cmd=["git", "status"], timeout=1)
        with patch("lib.subprocess_agents.subprocess.run", side_effect=err):
            result = run_git(["status"], cwd=tmp_path)
        assert result.returncode != 0


# ══════════════════════════════════════════════════════════════════
# invoke_headless_agent — claude
# ══════════════════════════════════════════════════════════════════


class TestInvokeHeadlessClaude:
    def test_returns_stdout_on_success(self):
        fake = MagicMock(returncode=0, stdout="feat: add thing\n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out == "feat: add thing"

    def test_returns_none_on_non_zero_exit(self):
        fake = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out is None

    def test_returns_none_on_empty_stdout(self):
        fake = MagicMock(returncode=0, stdout="   \n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out is None

    def test_returns_none_on_timeout(self):
        exc = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        with patch("lib.subprocess_agents.subprocess.run", side_effect=exc):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out is None

    def test_returns_none_when_claude_missing(self):
        with patch("lib.subprocess_agents.subprocess.run", side_effect=FileNotFoundError):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out is None

    def test_passes_cwd_when_given(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("claude", "p", timeout=10, cwd=tmp_path)
        kwargs = run.call_args.kwargs
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 10

    def test_includes_allowed_tools_flag(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("claude", "p", timeout=10)
        argv = run.call_args.args[0]
        assert "claude" in argv
        assert "-p" in argv
        assert "--allowedTools" in argv


# ══════════════════════════════════════════════════════════════════
# invoke_headless_agent — codex
# ══════════════════════════════════════════════════════════════════


class TestInvokeHeadlessCodex:
    def test_returns_stdout_on_success(self):
        fake = MagicMock(returncode=0, stdout="report body\n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("codex", "prompt", timeout=30)
        assert out == "report body"

    def test_prompt_passed_via_stdin(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("codex", "PROMPT-XYZ", timeout=30)
        kwargs = run.call_args.kwargs
        assert kwargs["input"] == "PROMPT-XYZ"

    def test_argv_reads_stdin_dash(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("codex", "p", timeout=30)
        argv = run.call_args.args[0]
        assert argv[0] == "codex"
        assert argv[1] == "exec"
        assert argv[-1] == "-"

    def test_argv_includes_skip_git_repo_check(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("codex", "p", timeout=30)
        argv = run.call_args.args[0]
        assert "--skip-git-repo-check" in argv

    def test_returns_none_on_non_zero_exit(self):
        fake = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("codex", "p", timeout=30)
        assert out is None

    def test_returns_none_on_empty_stdout(self):
        fake = MagicMock(returncode=0, stdout="   \n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("codex", "p", timeout=30)
        assert out is None

    def test_returns_none_on_timeout(self):
        exc = subprocess.TimeoutExpired(cmd="codex", timeout=30)
        with patch("lib.subprocess_agents.subprocess.run", side_effect=exc):
            out = invoke_headless_agent("codex", "p", timeout=30)
        assert out is None

    def test_returns_none_when_codex_missing(self):
        with patch("lib.subprocess_agents.subprocess.run", side_effect=FileNotFoundError):
            out = invoke_headless_agent("codex", "p", timeout=30)
        assert out is None

    def test_passes_cwd_and_timeout(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("codex", "p", timeout=7, cwd=tmp_path)
        kwargs = run.call_args.kwargs
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 7


class TestInvokeHeadlessDispatch:
    def test_unknown_name_raises(self):
        with pytest.raises(ValueError):
            invoke_headless_agent("gpt", "p", timeout=5)


# ══════════════════════════════════════════════════════════════════
# Clarity check
# ══════════════════════════════════════════════════════════════════


def _stdout_json(verdict: str, session_id: str = "sess_abc123") -> str:
    """Build a fake `claude -p --output-format json` stdout payload."""
    return json.dumps({
        "session_id": session_id,
        "result": verdict,
    })


class TestRunInitial:
    """run_initial returns (session_id, verdict) and shells to claude -p."""

    @patch("lib.subprocess_agents.subprocess.run")
    def test_clear_verdict(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear"), stderr=""
        )
        sid, verdict = subprocess_agents.run_initial("add /logout endpoint")
        assert verdict == "clear"
        assert sid == "sess_abc123"

    @patch("lib.subprocess_agents.subprocess.run")
    def test_vague_verdict(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("vague"), stderr=""
        )
        sid, verdict = subprocess_agents.run_initial("do the thing")
        assert verdict == "vague"
        assert sid == "sess_abc123"

    @patch("lib.subprocess_agents.subprocess.run")
    def test_passes_prompt_to_claude(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear"), stderr=""
        )
        subprocess_agents.run_initial("my prompt text")
        called_kwargs = mock_run.call_args.kwargs
        stdin_input = called_kwargs.get("input", "")
        assert "my prompt text" in stdin_input

    @patch("lib.subprocess_agents.subprocess.run")
    def test_invokes_claude_with_print_and_json(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear"), stderr=""
        )
        subprocess_agents.run_initial("something")
        cmd = mock_run.call_args.args[0]
        assert "claude" in cmd[0]
        assert "-p" in cmd or "--print" in cmd
        assert any("json" in c for c in cmd)

    @patch("lib.subprocess_agents.subprocess.run")
    def test_unknown_verdict_treated_as_vague(self, mock_run):
        """Fail-closed: anything other than 'clear' is vague."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("maybe"), stderr=""
        )
        _, verdict = subprocess_agents.run_initial("x")
        assert verdict == "vague"

    @patch("lib.subprocess_agents.subprocess.run")
    def test_malformed_json_treated_as_vague(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="not json at all", stderr=""
        )
        sid, verdict = subprocess_agents.run_initial("x")
        assert verdict == "vague"
        assert sid == ""

    @patch("lib.subprocess_agents.subprocess.run")
    def test_subprocess_error_treated_as_vague(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
        sid, verdict = subprocess_agents.run_initial("x")
        assert verdict == "vague"
        assert sid == ""


class TestRunResume:
    """run_resume continues an existing headless session and returns verdict."""

    @patch("lib.subprocess_agents.subprocess.run")
    def test_resume_clear(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear", "sess_xyz"), stderr=""
        )
        verdict = subprocess_agents.run_resume("sess_xyz", "Q: …\nA: …")
        assert verdict == "clear"

    @patch("lib.subprocess_agents.subprocess.run")
    def test_resume_vague(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("vague", "sess_xyz"), stderr=""
        )
        verdict = subprocess_agents.run_resume("sess_xyz", "Q: …\nA: …")
        assert verdict == "vague"

    @patch("lib.subprocess_agents.subprocess.run")
    def test_resume_passes_session_id_via_resume_flag(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear", "sess_xyz"), stderr=""
        )
        subprocess_agents.run_resume("sess_xyz", "payload")
        cmd = mock_run.call_args.args[0]
        assert "--resume" in cmd
        assert "sess_xyz" in cmd

    @patch("lib.subprocess_agents.subprocess.run")
    def test_resume_passes_qa_payload(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_stdout_json("clear", "sess_xyz"), stderr=""
        )
        subprocess_agents.run_resume("sess_xyz", "Q: foo\nA: bar")
        stdin_input = mock_run.call_args.kwargs.get("input", "")
        assert "Q: foo" in stdin_input
        assert "A: bar" in stdin_input

    @patch("lib.subprocess_agents.subprocess.run")
    def test_resume_malformed_treated_as_vague(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="garbage", stderr="")
        verdict = subprocess_agents.run_resume("sess_xyz", "x")
        assert verdict == "vague"

    @patch("lib.subprocess_agents.subprocess.run")
    def test_resume_failure_treated_as_vague(self, mock_run):
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="err")
        verdict = subprocess_agents.run_resume("sess_xyz", "x")
        assert verdict == "vague"
