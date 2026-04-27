"""Tests for lib/subprocess_agents.py — git, headless agent, and dataclass API."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from lib.subprocess_agents import (
    run_git,
    invoke_headless_agent,
    invoke_agent,
    parse_agent_response,
    ClaudeOptions,
    CodexOptions,
    InvokeConfig,
    AgentResponse,
)


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
# Dataclass defaults
# ══════════════════════════════════════════════════════════════════


class TestClaudeOptionsDefaults:
    def test_defaults_match_read_only_toolset(self):
        opts = ClaudeOptions()
        assert opts.model == "haiku"
        assert opts.bare is False
        assert tuple(opts.tools) == ("Read", "Grep", "Glob")
        assert tuple(opts.allowed_tools) == ("Read", "Grep", "Glob")
        assert opts.output_format == "text"
        assert opts.session_id is None


class TestCodexOptionsDefaults:
    def test_defaults_are_minimal(self):
        opts = CodexOptions()
        assert opts.session_id is None
        assert opts.output_schema is None
        assert opts.json_output is False
        assert opts.model is None


# ══════════════════════════════════════════════════════════════════
# invoke_headless_agent — claude (via ClaudeOptions)
# ══════════════════════════════════════════════════════════════════


class TestInvokeHeadlessClaude:
    def test_returns_stdout_on_success(self):
        fake = MagicMock(returncode=0, stdout="feat: add thing\n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("prompt", ClaudeOptions(), timeout=30)
        assert out == "feat: add thing"

    def test_returns_none_on_non_zero_exit(self):
        fake = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("prompt", ClaudeOptions(), timeout=30)
        assert out is None

    def test_returns_none_on_empty_stdout(self):
        fake = MagicMock(returncode=0, stdout="   \n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("prompt", ClaudeOptions(), timeout=30)
        assert out is None

    def test_returns_none_on_timeout(self):
        exc = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        with patch("lib.subprocess_agents.subprocess.run", side_effect=exc):
            out = invoke_headless_agent("prompt", ClaudeOptions(), timeout=30)
        assert out is None

    def test_returns_none_when_claude_missing(self):
        with patch("lib.subprocess_agents.subprocess.run", side_effect=FileNotFoundError):
            out = invoke_headless_agent("prompt", ClaudeOptions(), timeout=30)
        assert out is None

    def test_passes_cwd_when_given(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("p", ClaudeOptions(), timeout=10, cwd=tmp_path)
        kwargs = run.call_args.kwargs
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 10

    def test_includes_allowed_tools_flag(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("p", ClaudeOptions(), timeout=10)
        argv = run.call_args.args[0]
        assert "claude" in argv
        assert "-p" in argv
        assert "--allowedTools" in argv

    def test_bare_failure_retries_without_bare(self):
        fail = MagicMock(returncode=1, stdout="", stderr="err")
        ok = MagicMock(returncode=0, stdout="recovered", stderr="")
        with patch(
            "lib.subprocess_agents.subprocess.run", side_effect=[fail, ok]
        ) as run:
            out = invoke_headless_agent("p", ClaudeOptions(bare=True), timeout=10)
        assert out == "recovered"
        assert run.call_count == 2
        first_argv = run.call_args_list[0].args[0]
        second_argv = run.call_args_list[1].args[0]
        assert "--bare" in first_argv
        assert "--bare" not in second_argv

    def test_bare_success_does_not_retry(self):
        ok = MagicMock(returncode=0, stdout="first-try", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=ok) as run:
            out = invoke_headless_agent("p", ClaudeOptions(bare=True), timeout=10)
        assert out == "first-try"
        assert run.call_count == 1

    def test_no_retry_when_bare_not_requested(self):
        fail = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fail) as run:
            out = invoke_headless_agent("p", ClaudeOptions(), timeout=10)
        assert out is None
        assert run.call_count == 1

    def test_session_id_appended(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("p", ClaudeOptions(session_id="abc"), timeout=10)
        argv = run.call_args.args[0]
        assert "--session-id" in argv
        assert "abc" in argv


# ══════════════════════════════════════════════════════════════════
# invoke_headless_agent — codex (via CodexOptions)
# ══════════════════════════════════════════════════════════════════


class TestInvokeHeadlessCodex:
    def test_returns_stdout_on_success(self):
        fake = MagicMock(returncode=0, stdout="report body\n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("prompt", CodexOptions(), timeout=30)
        assert out == "report body"

    def test_prompt_passed_via_stdin(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("PROMPT-XYZ", CodexOptions(), timeout=30)
        assert run.call_args.kwargs["input"] == "PROMPT-XYZ"

    def test_argv_reads_stdin_dash(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("p", CodexOptions(), timeout=30)
        argv = run.call_args.args[0]
        assert argv[0] == "codex"
        assert argv[1] == "exec"
        assert argv[-1] == "-"

    def test_argv_includes_skip_git_repo_check(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("p", CodexOptions(), timeout=30)
        argv = run.call_args.args[0]
        assert "--skip-git-repo-check" in argv

    def test_json_flag_toggled_by_option(self):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("p", CodexOptions(json_output=True), timeout=30)
        argv = run.call_args.args[0]
        assert "--json" in argv

    def test_returns_none_on_non_zero_exit(self):
        fake = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("p", CodexOptions(), timeout=30)
        assert out is None

    def test_returns_none_on_empty_stdout(self):
        fake = MagicMock(returncode=0, stdout="   \n", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake):
            out = invoke_headless_agent("p", CodexOptions(), timeout=30)
        assert out is None

    def test_returns_none_on_timeout(self):
        exc = subprocess.TimeoutExpired(cmd="codex", timeout=30)
        with patch("lib.subprocess_agents.subprocess.run", side_effect=exc):
            out = invoke_headless_agent("p", CodexOptions(), timeout=30)
        assert out is None

    def test_returns_none_when_codex_missing(self):
        with patch("lib.subprocess_agents.subprocess.run", side_effect=FileNotFoundError):
            out = invoke_headless_agent("p", CodexOptions(), timeout=30)
        assert out is None

    def test_passes_cwd_and_timeout(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("lib.subprocess_agents.subprocess.run", return_value=fake) as run:
            invoke_headless_agent("p", CodexOptions(), timeout=7, cwd=tmp_path)
        kwargs = run.call_args.kwargs
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 7


class TestInvokeHeadlessDispatch:
    def test_unknown_options_type_raises(self):
        with pytest.raises(TypeError):
            invoke_headless_agent("p", object(), timeout=5)  # type: ignore[arg-type]


# ══════════════════════════════════════════════════════════════════
# parse_agent_response
# ══════════════════════════════════════════════════════════════════


class TestParseAgentResponse:
    def test_extracts_session_id_and_text(self):
        raw = '{"thread_id":"abc"}\n{"item":{"text":"final"}}\n'
        resp = parse_agent_response(raw)
        assert resp.session_id == "abc"
        assert resp.text == "final"
        assert resp.raw == raw

    def test_missing_session_id_is_empty(self):
        raw = '{"item":{"text":"only"}}\n'
        resp = parse_agent_response(raw)
        assert resp.session_id == ""
        assert resp.text == "only"

    def test_last_nonempty_text_wins(self):
        raw = (
            '{"thread_id":"s"}\n'
            '{"item":{"text":"partial"}}\n'
            '{"item":{"text":"final"}}\n'
        )
        resp = parse_agent_response(raw)
        assert resp.text == "final"

    def test_ignores_non_json_lines(self):
        raw = 'banner-line\n{"thread_id":"x"}\n{"item":{"text":"t"}}\n'
        resp = parse_agent_response(raw)
        assert resp.session_id == "x"
        assert resp.text == "t"


# ══════════════════════════════════════════════════════════════════
# invoke_agent
# ══════════════════════════════════════════════════════════════════


RAW_OK = '{"thread_id":"sid-1"}\n{"item":{"text":"response body"}}\n'


class TestInvokeAgent:
    def test_returns_text_when_no_conformance_checks(self):
        with patch(
            "lib.subprocess_agents.invoke_headless_agent", return_value=RAW_OK
        ):
            out = invoke_agent("p", InvokeConfig(llm="codex"))
        assert out == "response body"

    def test_failure_sentinel_when_agent_returns_none(self):
        with patch(
            "lib.subprocess_agents.invoke_headless_agent", return_value=None
        ):
            out = invoke_agent("p", InvokeConfig(llm="claude", model="haiku"))
        assert "claude" in out
        assert "failed to respond" in out

    def test_failure_sentinel_when_session_id_missing(self):
        raw = '{"item":{"text":"t"}}\n'
        with patch(
            "lib.subprocess_agents.invoke_headless_agent", return_value=raw
        ):
            out = invoke_agent("p", InvokeConfig(llm="codex"))
        assert "failed to get session id" in out

    def test_returns_text_when_all_checks_pass(self):
        checks = [lambda r: (True, ""), lambda r: (True, "")]
        with patch(
            "lib.subprocess_agents.invoke_headless_agent", return_value=RAW_OK
        ):
            out = invoke_agent(
                "p", InvokeConfig(llm="codex"), conformance_checks=checks
            )
        assert out == "response body"

    def test_recurses_with_feedback_and_resumes_session(self):
        raw_retry = '{"thread_id":"sid-2"}\n{"item":{"text":"fixed"}}\n'
        calls = []

        def fake_headless(prompt, options, *, timeout, cwd=None):
            calls.append((prompt, options))
            return RAW_OK if len(calls) == 1 else raw_retry

        first_pass = [False]

        def check(_r):
            if not first_pass[0]:
                first_pass[0] = True
                return False, "please fix X"
            return True, ""

        with patch(
            "lib.subprocess_agents.invoke_headless_agent",
            side_effect=fake_headless,
        ):
            out = invoke_agent(
                "initial",
                InvokeConfig(llm="codex", attempts_left=3),
                conformance_checks=[check],
            )
        assert out == "fixed"
        assert len(calls) == 2
        assert "please fix X" in calls[1][0]
        assert calls[1][1].session_id == "sid-1"

    def test_stops_recursing_when_attempts_exhausted(self):
        checks = [lambda r: (False, "fix")]
        with patch(
            "lib.subprocess_agents.invoke_headless_agent", return_value=RAW_OK
        ) as m:
            out = invoke_agent(
                "p",
                InvokeConfig(llm="codex", attempts_left=1),
                conformance_checks=checks,
            )
        assert out == "response body"
        assert m.call_count == 1


# ══════════════════════════════════════════════════════════════════
# AgentResponse is a plain dataclass
# ══════════════════════════════════════════════════════════════════


class TestAgentResponse:
    def test_fields(self):
        r = AgentResponse(session_id="s", text="t", raw="r")
        assert (r.session_id, r.text, r.raw) == ("s", "t", "r")
