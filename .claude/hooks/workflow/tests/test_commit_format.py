"""Tests for commit message format validation in bash_guard.py."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import bash_guard
from workflow.session_store import SessionStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": kwargs.get("workflow_active", True),
        "workflow_type": "implement",
        "phase": phase,
        "validation_result": kwargs.get("validation_result", None),
        "pr_status": kwargs.get("pr_status", "pending"),
        "ci_status": kwargs.get("ci_status", "pending"),
        "ci_check_executed": kwargs.get("ci_check_executed", False),
        "test_run_executed": kwargs.get("test_run_executed", False),
    }


def write_state(tmp_state_file, state: dict) -> None:
    tmp_state_file.write_text(json.dumps(state))


def bash_hook(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"output": ""},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


# ---------------------------------------------------------------------------
# Valid conventional commits -> allowed
# ---------------------------------------------------------------------------


class TestCommitFormatValidation:
    def test_valid_feat_commit(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(
            bash_hook("git commit -m 'feat: add user auth'"), store
        )
        assert decision == "allow"

    def test_valid_fix_with_scope(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(
            bash_hook('git commit -m "fix(api): resolve null pointer"'), store
        )
        assert decision == "allow"

    def test_valid_chore_commit(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(
            bash_hook("git commit -m 'chore: update dependencies'"), store
        )
        assert decision == "allow"

    def test_valid_breaking_change(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(
            bash_hook("git commit -m 'feat!: drop legacy API'"), store
        )
        assert decision == "allow"

    @pytest.mark.parametrize(
        "msg_type",
        ["refactor", "docs", "test", "style", "perf", "ci", "build", "revert"],
    )
    def test_valid_all_types(self, msg_type, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(
            bash_hook(f"git commit -m '{msg_type}: some description'"), store
        )
        assert decision == "allow"

    # -----------------------------------------------------------------------
    # Invalid commits -> blocked
    # -----------------------------------------------------------------------

    def test_missing_type_prefix(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = bash_guard.validate_pre(
            bash_hook("git commit -m 'added new feature'"), store
        )
        assert decision == "block"
        assert "conventional commit" in reason.lower()

    def test_missing_colon_space(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = bash_guard.validate_pre(
            bash_hook("git commit -m 'feat add new feature'"), store
        )
        assert decision == "block"

    def test_invalid_type(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = bash_guard.validate_pre(
            bash_hook("git commit -m 'update: change config'"), store
        )
        assert decision == "block"

    def test_empty_description(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = bash_guard.validate_pre(
            bash_hook("git commit -m 'feat: '"), store
        )
        assert decision == "block"

    # -----------------------------------------------------------------------
    # Non-commit commands -> allowed (pass-through)
    # -----------------------------------------------------------------------

    def test_non_commit_command_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(
            bash_hook("git status"), store
        )
        assert decision == "allow"

    def test_git_commit_without_m_flag_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(
            bash_hook("git commit --amend"), store
        )
        assert decision == "allow"

    # -----------------------------------------------------------------------
    # Workflow inactive -> allowed regardless
    # -----------------------------------------------------------------------

    def test_commit_allowed_when_workflow_inactive(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code", workflow_active=False))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(
            bash_hook("git commit -m 'bad format no type'"), store
        )
        assert decision == "allow"

    # -----------------------------------------------------------------------
    # Multiline commit messages (heredoc) -> validate first line only
    # -----------------------------------------------------------------------

    def test_multiline_commit_first_line_valid(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        cmd = """git commit -m "$(cat <<'EOF'
feat: add user authentication

This adds JWT-based auth with refresh tokens.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
"""
        decision, _ = bash_guard.validate_pre(bash_hook(cmd), store)
        assert decision == "allow"
