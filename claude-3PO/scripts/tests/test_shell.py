"""Tests for lib/shell.py — subprocess wrappers for git and headless Claude."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


from lib.shell import run_git, invoke_claude


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


# ── invoke_claude ────────────────────────────────────────────────


class TestInvokeClaude:
    def test_returns_stdout_on_success(self):
        fake = MagicMock(returncode=0, stdout="feat: add thing\n", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_claude("prompt", timeout=30)
        assert out == "feat: add thing"

    def test_returns_none_on_non_zero_exit(self):
        fake = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_claude("prompt", timeout=30)
        assert out is None

    def test_returns_none_on_empty_stdout(self):
        fake = MagicMock(returncode=0, stdout="   \n", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake):
            out = invoke_claude("prompt", timeout=30)
        assert out is None

    def test_returns_none_on_timeout(self):
        exc = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        with patch("lib.shell.subprocess.run", side_effect=exc):
            out = invoke_claude("prompt", timeout=30)
        assert out is None

    def test_returns_none_when_claude_missing(self):
        with patch("lib.shell.subprocess.run", side_effect=FileNotFoundError):
            out = invoke_claude("prompt", timeout=30)
        assert out is None

    def test_passes_cwd_when_given(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            invoke_claude("p", timeout=10, cwd=tmp_path)
        kwargs = run.call_args.kwargs
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 10

    def test_includes_allowed_tools_flag(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.shell.subprocess.run", return_value=fake) as run:
            invoke_claude("p", timeout=10)
        argv = run.call_args.args[0]
        assert "claude" in argv
        assert "-p" in argv
        assert "--allowedTools" in argv
