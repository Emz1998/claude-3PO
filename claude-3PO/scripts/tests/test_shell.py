"""Tests for lib/shell.py — subprocess wrappers for git and headless agents."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest


from lib.shell import run_git, invoke_headless_agent


# ── run_git ──────────────────────────────────────────────────────


class TestRunGit:
    def test_returns_completed_process_on_success(self, tmp_path):
        fake = MagicMock(returncode=0, stdout=" M foo.py\n", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            result = run_git(["status", "--porcelain"], cwd=tmp_path)
        assert result.returncode == 0
        assert result.stdout == " M foo.py\n"
        run.assert_called_once()
        args, kwargs = run.call_args
        assert args[0] == ["git", "status", "--porcelain"]
        assert kwargs["cwd"] == tmp_path

    def test_non_zero_exit_returned_not_raised(self, tmp_path):
        fake = MagicMock(returncode=128, stdout="", stderr="fatal")
        with patch("lib.shell.subprocess.run", return_value=fake):
            result = run_git(["status"], cwd=tmp_path)
        assert result.returncode == 128


# ── invoke_headless_agent: claude ────────────────────────────────


class TestInvokeHeadlessClaude:
    def test_returns_stdout_on_success(self):
        fake = MagicMock(returncode=0, stdout="feat: add thing\n", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out == "feat: add thing"

    def test_returns_none_on_non_zero_exit(self):
        fake = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out is None

    def test_returns_none_on_empty_stdout(self):
        fake = MagicMock(returncode=0, stdout="   \n", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out is None

    def test_returns_none_on_timeout(self):
        exc = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        with patch("lib.shell.subprocess.run", side_effect=exc):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out is None

    def test_returns_none_when_claude_missing(self):
        with patch("lib.shell.subprocess.run", side_effect=FileNotFoundError):
            out = invoke_headless_agent("claude", "prompt", timeout=30)
        assert out is None

    def test_passes_cwd_when_given(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("claude", "p", timeout=10, cwd=tmp_path)
        kwargs = run.call_args.kwargs
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 10

    def test_includes_allowed_tools_flag(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("claude", "p", timeout=10)
        argv = run.call_args.args[0]
        assert "claude" in argv
        assert "-p" in argv
        assert "--allowedTools" in argv


# ── invoke_headless_agent: codex ─────────────────────────────────


class TestInvokeHeadlessCodex:
    def test_returns_stdout_on_success(self):
        fake = MagicMock(returncode=0, stdout="report body\n", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_headless_agent("codex", "prompt", timeout=30)
        assert out == "report body"

    def test_prompt_passed_via_stdin(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("codex", "PROMPT-XYZ", timeout=30)
        kwargs = run.call_args.kwargs
        assert kwargs["input"] == "PROMPT-XYZ"

    def test_argv_reads_stdin_dash(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("codex", "p", timeout=30)
        argv = run.call_args.args[0]
        assert argv[0] == "codex"
        assert argv[1] == "exec"
        assert argv[-1] == "-"

    def test_argv_includes_skip_git_repo_check(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("codex", "p", timeout=30)
        argv = run.call_args.args[0]
        assert "--skip-git-repo-check" in argv

    def test_returns_none_on_non_zero_exit(self):
        fake = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_headless_agent("codex", "p", timeout=30)
        assert out is None

    def test_returns_none_on_empty_stdout(self):
        fake = MagicMock(returncode=0, stdout="   \n", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_headless_agent("codex", "p", timeout=30)
        assert out is None

    def test_returns_none_on_timeout(self):
        exc = subprocess.TimeoutExpired(cmd="codex", timeout=30)
        with patch("lib.shell.subprocess.run", side_effect=exc):
            out = invoke_headless_agent("codex", "p", timeout=30)
        assert out is None

    def test_returns_none_when_codex_missing(self):
        with patch("lib.shell.subprocess.run", side_effect=FileNotFoundError):
            out = invoke_headless_agent("codex", "p", timeout=30)
        assert out is None

    def test_passes_cwd_and_timeout(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("codex", "p", timeout=7, cwd=tmp_path)
        kwargs = run.call_args.kwargs
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 7


# ── invoke_headless_agent: dispatch ──────────────────────────────


class TestInvokeHeadlessDispatch:
    def test_unknown_name_raises(self):
        with pytest.raises(ValueError):
            invoke_headless_agent("gpt", "p", timeout=5)
