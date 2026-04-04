"""Tests for guards/webfetch_guard.py."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import webfetch_guard
from workflow.session_store import SessionStore


def make_state(active: bool = True) -> dict:
    return {"workflow_active": active}


def write_state(tmp_state_file, state: dict) -> None:
    SessionStore("s", tmp_state_file).save(state)


def webfetch_hook(url: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "WebFetch",
        "tool_input": {"url": url},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


class TestWebfetchGuard:
    def test_safe_domain_github_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = SessionStore("s", tmp_state_file)
        decision, _ = webfetch_guard.validate(webfetch_hook("https://github.com/foo/bar"), store)
        assert decision == "allow"

    def test_safe_domain_docs_anthropic_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = SessionStore("s", tmp_state_file)
        decision, _ = webfetch_guard.validate(webfetch_hook("https://docs.anthropic.com/api"), store)
        assert decision == "allow"

    def test_safe_subdomain_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = SessionStore("s", tmp_state_file)
        decision, _ = webfetch_guard.validate(webfetch_hook("https://api.github.com/repos"), store)
        assert decision == "allow"

    def test_unsafe_domain_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = SessionStore("s", tmp_state_file)
        decision, reason = webfetch_guard.validate(webfetch_hook("https://evil.example.com"), store)
        assert decision == "block"
        assert "domain" in reason.lower() or "allowed" in reason.lower()

    def test_workflow_inactive_allows_all(self, tmp_state_file):
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        decision, _ = webfetch_guard.validate(webfetch_hook("https://evil.example.com"), store)
        assert decision == "allow"

    def test_empty_url_blocked_when_active(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = SessionStore("s", tmp_state_file)
        decision, _ = webfetch_guard.validate(webfetch_hook(""), store)
        assert decision == "block"

    @pytest.mark.parametrize("url", [
        "https://docs.python.org/3/library/json.html",
        "https://reactjs.org/docs/hooks.html",
        "https://react.dev/reference",
        "https://nextjs.org/docs",
        "https://tailwindcss.com/docs",
        "https://stackoverflow.com/questions/12345",
        "https://pypi.org/project/requests/",
        "https://npmjs.com/package/react",
        "https://typescriptlang.org/docs",
        "https://nodejs.org/api",
        "https://firebase.google.com/docs",
        "https://supabase.com/docs",
        "https://expo.dev/docs",
        "https://reactnative.dev/docs",
        "https://developer.mozilla.org/en-US",
    ])
    def test_all_safe_domains_allowed(self, url, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = SessionStore("s", tmp_state_file)
        decision, _ = webfetch_guard.validate(webfetch_hook(url), store)
        assert decision == "allow"
