"""Tests for responses.py — output functions with correct camelCase serialization."""

import json
import pytest


def test_block_exits_with_code_2(capsys):
    from scripts.claude_hooks.responses import block

    with pytest.raises(SystemExit) as exc_info:
        block("Phase guard: cannot skip explore")
    assert exc_info.value.code == 2
    assert "Phase guard: cannot skip explore" in capsys.readouterr().err


def test_succeed_with_none_does_not_exit():
    from scripts.claude_hooks.responses import succeed

    # Should return without exiting
    succeed(None)


def test_succeed_with_message_exits_0(capsys):
    from scripts.claude_hooks.responses import succeed

    with pytest.raises(SystemExit) as exc_info:
        succeed("Use this commit template")
    assert exc_info.value.code == 0
    assert "Use this commit template" in capsys.readouterr().out


def test_output_json_uses_camel_case():
    """Key serialization bug fix: Python fields -> JSON camelCase."""
    from scripts.claude_hooks.responses import build_output

    result = build_output(continue_=False, stop_reason="story incomplete")
    parsed = json.loads(result)

    assert "continue" in parsed
    assert "stopReason" in parsed
    # Must NOT contain Python-style keys
    assert "_continue" not in parsed
    assert "stop_reason" not in parsed


def test_output_json_omits_none_fields():
    from scripts.claude_hooks.responses import build_output

    result = build_output(continue_=True)
    parsed = json.loads(result)

    assert "continue" in parsed
    assert parsed["continue"] is True
    assert "stopReason" not in parsed
    assert "suppressOutput" not in parsed


def test_output_json_suppress_output():
    from scripts.claude_hooks.responses import build_output

    result = build_output(suppress_output=True)
    parsed = json.loads(result)

    assert "suppressOutput" in parsed
    assert parsed["suppressOutput"] is True


def test_output_json_hook_specific_output():
    from scripts.claude_hooks.responses import build_output

    result = build_output(
        hook_specific_output={
            "hookEventName": "PreToolUse",
            "additionalContext": "some context",
        }
    )
    parsed = json.loads(result)

    assert "hookSpecificOutput" in parsed
    assert parsed["hookSpecificOutput"]["additionalContext"] == "some context"
    # Must NOT use snake_case key
    assert "hook_specific_output" not in parsed


def test_set_decision_exits_0_with_json(capsys):
    from scripts.claude_hooks.responses import set_decision

    with pytest.raises(SystemExit) as exc_info:
        set_decision(continue_=False, stop_reason="blocked")
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    parsed = json.loads(output)
    assert parsed["continue"] is False
    assert parsed["stopReason"] == "blocked"
