"""Tests for pr_manager.py — all gh CLI calls are mocked, no real API calls."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent dir so we can import the module directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pr_manager as pr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_create_args(**overrides):
    defaults = dict(title="Fix bug", body="Fixes #123", base="main", head=None)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_view_args(**overrides):
    defaults = dict(pr_number="42")
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_review_args(**overrides):
    defaults = dict(pr_number="42", approve=False, comment=None, request_changes=None)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_merge_args(**overrides):
    defaults = dict(pr_number="42", squash=False, rebase=False, merge=False)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_close_args(**overrides):
    defaults = dict(pr_number="42")
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_list_args(**overrides):
    defaults = dict(active=False)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_is_open_args(**overrides):
    defaults = {}
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


SAMPLE_PR = {
    "number": 42,
    "title": "Fix critical bug",
    "state": "OPEN",
    "body": "This PR fixes the critical bug.",
    "url": "https://github.com/org/repo/pull/42",
    "author": {"login": "alice"},
    "headRefName": "fix/critical-bug",
    "baseRefName": "main",
    "mergeable": "MERGEABLE",
    "reviews": [],
}

SAMPLE_PR_WITH_REVIEWS = {
    **SAMPLE_PR,
    "reviews": [
        {"author": {"login": "bob"}, "state": "APPROVED"},
        {"author": {"login": "carol"}, "state": "CHANGES_REQUESTED"},
    ],
}

SAMPLE_PR_LIST = [
    {
        "number": 42,
        "title": "Fix critical bug",
        "author": {"login": "alice"},
        "state": "OPEN",
    },
    {
        "number": 43,
        "title": "Add feature X",
        "author": {"login": "bob"},
        "state": "CLOSED",
    },
]

REPO = "org/repo"


# ---------------------------------------------------------------------------
# cmd_create
# ---------------------------------------------------------------------------


class TestCmdCreate:
    def test_create_without_head_branch(self, capsys):
        args = _make_create_args()
        with patch.object(pr, "run", return_value="https://github.com/org/repo/pull/10") as mock_run:
            pr.cmd_create(args, REPO)

        out = capsys.readouterr().out
        assert "https://github.com/org/repo/pull/10" in out

        cmd = mock_run.call_args[0][0]
        assert "gh" in cmd
        assert "pr" in cmd
        assert "create" in cmd
        assert "--repo" in cmd
        assert REPO in cmd
        assert "--title" in cmd
        assert "Fix bug" in cmd
        assert "--body" in cmd
        assert "Fixes #123" in cmd
        assert "--base" in cmd
        assert "main" in cmd
        assert "--head" not in cmd

    def test_create_with_head_branch(self, capsys):
        args = _make_create_args(head="feature/my-branch")
        with patch.object(pr, "run", return_value="https://github.com/org/repo/pull/11") as mock_run:
            pr.cmd_create(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--head" in cmd
        assert "feature/my-branch" in cmd

    def test_create_always_includes_base(self):
        args = _make_create_args(base="develop")
        with patch.object(pr, "run", return_value="https://github.com/org/repo/pull/12") as mock_run:
            pr.cmd_create(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--base" in cmd
        base_idx = cmd.index("--base")
        assert cmd[base_idx + 1] == "develop"

    def test_create_prints_run_output(self, capsys):
        args = _make_create_args()
        with patch.object(pr, "run", return_value="PR created: https://github.com/org/repo/pull/5"):
            pr.cmd_create(args, REPO)

        out = capsys.readouterr().out
        assert "PR created: https://github.com/org/repo/pull/5" in out


# ---------------------------------------------------------------------------
# cmd_view
# ---------------------------------------------------------------------------


class TestCmdView:
    def test_view_pr_found_no_reviews(self, capsys):
        args = _make_view_args(pr_number="42")
        with patch.object(pr, "gh_json", return_value=SAMPLE_PR):
            pr.cmd_view(args, REPO)

        out = capsys.readouterr().out
        assert "PR #42: Fix critical bug" in out
        assert "OPEN" in out
        assert "https://github.com/org/repo/pull/42" in out
        assert "alice" in out
        assert "fix/critical-bug" in out
        assert "main" in out
        assert "MERGEABLE" in out
        assert "This PR fixes the critical bug." in out
        assert "Reviews:" not in out

    def test_view_pr_found_with_reviews(self, capsys):
        args = _make_view_args(pr_number="42")
        with patch.object(pr, "gh_json", return_value=SAMPLE_PR_WITH_REVIEWS):
            pr.cmd_view(args, REPO)

        out = capsys.readouterr().out
        assert "Reviews:" in out
        assert "bob" in out
        assert "APPROVED" in out
        assert "carol" in out
        assert "CHANGES_REQUESTED" in out

    def test_view_pr_not_found_exits_with_code_1(self, capsys):
        args = _make_view_args(pr_number="999")
        with patch.object(pr, "gh_json", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                pr.cmd_view(args, REPO)

        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "PR #999 not found" in out

    def test_view_builds_correct_gh_command(self):
        args = _make_view_args(pr_number="42")
        with patch.object(pr, "gh_json", return_value=SAMPLE_PR) as mock_gh_json:
            pr.cmd_view(args, REPO)

        cmd = mock_gh_json.call_args[0][0]
        assert "gh" in cmd
        assert "pr" in cmd
        assert "view" in cmd
        assert "42" in cmd
        assert "--repo" in cmd
        assert REPO in cmd
        assert "--json" in cmd

    def test_view_pr_with_empty_reviews_list(self, capsys):
        pr_data = {**SAMPLE_PR, "reviews": []}
        args = _make_view_args(pr_number="42")
        with patch.object(pr, "gh_json", return_value=pr_data):
            pr.cmd_view(args, REPO)

        out = capsys.readouterr().out
        assert "Reviews:" not in out


# ---------------------------------------------------------------------------
# cmd_review
# ---------------------------------------------------------------------------


class TestCmdReview:
    def test_review_approve(self, capsys):
        args = _make_review_args(approve=True)
        with patch.object(pr, "run", return_value="PR approved") as mock_run:
            pr.cmd_review(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--approve" in cmd
        assert "--comment" not in cmd
        assert "--request-changes" not in cmd
        out = capsys.readouterr().out
        assert "PR approved" in out

    def test_review_comment(self, capsys):
        args = _make_review_args(comment="Looks good to me!")
        with patch.object(pr, "run", return_value="Comment added") as mock_run:
            pr.cmd_review(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--comment" in cmd
        assert "-b" in cmd
        assert "Looks good to me!" in cmd
        assert "--approve" not in cmd

    def test_review_request_changes(self, capsys):
        args = _make_review_args(request_changes="Please fix the tests.")
        with patch.object(pr, "run", return_value="Changes requested") as mock_run:
            pr.cmd_review(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--request-changes" in cmd
        assert "-b" in cmd
        assert "Please fix the tests." in cmd

    def test_review_no_action_exits_with_code_1(self, capsys):
        args = _make_review_args(approve=False, comment=None, request_changes=None)
        with pytest.raises(SystemExit) as exc_info:
            pr.cmd_review(args, REPO)

        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "Error: Must specify --approve, --comment, or --request-changes" in out

    def test_review_approve_takes_priority_over_others(self):
        args = _make_review_args(approve=True, comment="Also a comment")
        with patch.object(pr, "run", return_value="") as mock_run:
            pr.cmd_review(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--approve" in cmd
        assert "--comment" not in cmd

    def test_review_includes_repo_and_pr_number(self):
        args = _make_review_args(pr_number="55", approve=True)
        with patch.object(pr, "run", return_value="") as mock_run:
            pr.cmd_review(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "55" in cmd
        assert "--repo" in cmd
        assert REPO in cmd


# ---------------------------------------------------------------------------
# cmd_merge
# ---------------------------------------------------------------------------


class TestCmdMerge:
    def test_merge_squash(self, capsys):
        args = _make_merge_args(squash=True)
        with patch.object(pr, "run", return_value="PR merged (squash)") as mock_run:
            pr.cmd_merge(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--squash" in cmd
        assert "--rebase" not in cmd
        assert "--merge" not in cmd

    def test_merge_rebase(self, capsys):
        args = _make_merge_args(rebase=True)
        with patch.object(pr, "run", return_value="PR merged (rebase)") as mock_run:
            pr.cmd_merge(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--rebase" in cmd
        assert "--squash" not in cmd
        assert "--merge" not in cmd

    def test_merge_merge_commit(self, capsys):
        args = _make_merge_args(merge=True)
        with patch.object(pr, "run", return_value="PR merged (merge commit)") as mock_run:
            pr.cmd_merge(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--merge" in cmd
        assert "--squash" not in cmd
        assert "--rebase" not in cmd

    def test_merge_no_strategy(self, capsys):
        args = _make_merge_args(squash=False, rebase=False, merge=False)
        with patch.object(pr, "run", return_value="PR merged") as mock_run:
            pr.cmd_merge(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "--squash" not in cmd
        assert "--rebase" not in cmd
        assert "--merge" not in cmd

    def test_merge_includes_pr_number_and_repo(self):
        args = _make_merge_args(pr_number="77", squash=True)
        with patch.object(pr, "run", return_value="") as mock_run:
            pr.cmd_merge(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "77" in cmd
        assert "--repo" in cmd
        assert REPO in cmd

    def test_merge_prints_output(self, capsys):
        args = _make_merge_args(squash=True)
        with patch.object(pr, "run", return_value="Merged successfully"):
            pr.cmd_merge(args, REPO)

        assert "Merged successfully" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cmd_close
# ---------------------------------------------------------------------------


class TestCmdClose:
    def test_close_calls_correct_command(self):
        args = _make_close_args(pr_number="42")
        with patch.object(pr, "run", return_value="PR closed") as mock_run:
            pr.cmd_close(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "gh" in cmd
        assert "pr" in cmd
        assert "close" in cmd
        assert "42" in cmd
        assert "--repo" in cmd
        assert REPO in cmd

    def test_close_prints_output(self, capsys):
        args = _make_close_args()
        with patch.object(pr, "run", return_value="PR #42 closed"):
            pr.cmd_close(args, REPO)

        assert "PR #42 closed" in capsys.readouterr().out

    def test_close_different_pr_number(self):
        args = _make_close_args(pr_number="99")
        with patch.object(pr, "run", return_value="") as mock_run:
            pr.cmd_close(args, REPO)

        cmd = mock_run.call_args[0][0]
        assert "99" in cmd


# ---------------------------------------------------------------------------
# cmd_list
# ---------------------------------------------------------------------------


class TestCmdList:
    def test_list_all_prs(self, capsys):
        args = _make_list_args(active=False)
        with patch.object(pr, "gh_json", return_value=SAMPLE_PR_LIST) as mock_gh_json:
            pr.cmd_list(args, REPO)

        cmd = mock_gh_json.call_args[0][0]
        assert "--state" in cmd
        state_idx = cmd.index("--state")
        assert cmd[state_idx + 1] == "all"

        out = capsys.readouterr().out
        assert "All PRs (2 total)" in out
        assert "PR #42: Fix critical bug" in out
        assert "PR #43: Add feature X" in out
        assert "alice" in out
        assert "bob" in out

    def test_list_active_only_uses_open_state(self, capsys):
        active_prs = [SAMPLE_PR_LIST[0]]
        args = _make_list_args(active=True)
        with patch.object(pr, "gh_json", return_value=active_prs) as mock_gh_json:
            pr.cmd_list(args, REPO)

        cmd = mock_gh_json.call_args[0][0]
        state_idx = cmd.index("--state")
        assert cmd[state_idx + 1] == "open"

        out = capsys.readouterr().out
        assert "Active PRs (1 total)" in out

    def test_list_empty_all(self, capsys):
        args = _make_list_args(active=False)
        with patch.object(pr, "gh_json", return_value=None):
            pr.cmd_list(args, REPO)

        out = capsys.readouterr().out
        assert "No PRs" in out

    def test_list_empty_active(self, capsys):
        args = _make_list_args(active=True)
        with patch.object(pr, "gh_json", return_value=None):
            pr.cmd_list(args, REPO)

        out = capsys.readouterr().out
        assert "No active PRs" in out

    def test_list_empty_list_returned(self, capsys):
        args = _make_list_args(active=False)
        with patch.object(pr, "gh_json", return_value=[]):
            pr.cmd_list(args, REPO)

        out = capsys.readouterr().out
        assert "No PRs" in out

    def test_list_pr_without_author_shows_unknown(self, capsys):
        prs_no_author = [{"number": 10, "title": "Orphan PR", "author": None, "state": "OPEN"}]
        args = _make_list_args(active=False)
        with patch.object(pr, "gh_json", return_value=prs_no_author):
            pr.cmd_list(args, REPO)

        out = capsys.readouterr().out
        assert "unknown" in out

    def test_list_includes_repo_in_command(self):
        args = _make_list_args()
        with patch.object(pr, "gh_json", return_value=SAMPLE_PR_LIST) as mock_gh_json:
            pr.cmd_list(args, REPO)

        cmd = mock_gh_json.call_args[0][0]
        assert "--repo" in cmd
        assert REPO in cmd
        assert "--limit" in cmd
        assert "100" in cmd

    def test_list_shows_pr_state_in_output(self, capsys):
        args = _make_list_args(active=False)
        with patch.object(pr, "gh_json", return_value=SAMPLE_PR_LIST):
            pr.cmd_list(args, REPO)

        out = capsys.readouterr().out
        assert "OPEN" in out
        assert "CLOSED" in out


# ---------------------------------------------------------------------------
# cmd_is_open
# ---------------------------------------------------------------------------


class TestCmdIsOpen:
    def test_is_open_with_open_prs_prints_true_and_exits_0(self, capsys):
        args = _make_is_open_args()
        with patch.object(pr, "gh_json", return_value=[{"number": 42}]):
            with pytest.raises(SystemExit) as exc_info:
                pr.cmd_is_open(args, REPO)

        assert exc_info.value.code == 0
        assert "true" in capsys.readouterr().out

    def test_is_open_with_no_open_prs_prints_false_and_exits_1(self, capsys):
        args = _make_is_open_args()
        with patch.object(pr, "gh_json", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                pr.cmd_is_open(args, REPO)

        assert exc_info.value.code == 1
        assert "false" in capsys.readouterr().out

    def test_is_open_with_empty_list_exits_1(self, capsys):
        args = _make_is_open_args()
        with patch.object(pr, "gh_json", return_value=[]):
            with pytest.raises(SystemExit) as exc_info:
                pr.cmd_is_open(args, REPO)

        assert exc_info.value.code == 1
        assert "false" in capsys.readouterr().out

    def test_is_open_uses_open_state_and_limit_1(self):
        args = _make_is_open_args()
        with patch.object(pr, "gh_json", return_value=None) as mock_gh_json:
            with pytest.raises(SystemExit):
                pr.cmd_is_open(args, REPO)

        cmd = mock_gh_json.call_args[0][0]
        assert "--state" in cmd
        state_idx = cmd.index("--state")
        assert cmd[state_idx + 1] == "open"
        assert "--limit" in cmd
        limit_idx = cmd.index("--limit")
        assert cmd[limit_idx + 1] == "1"

    def test_is_open_includes_repo(self):
        args = _make_is_open_args()
        with patch.object(pr, "gh_json", return_value=None) as mock_gh_json:
            with pytest.raises(SystemExit):
                pr.cmd_is_open(args, REPO)

        cmd = mock_gh_json.call_args[0][0]
        assert "--repo" in cmd
        assert REPO in cmd


# ---------------------------------------------------------------------------
# COMMANDS dict
# ---------------------------------------------------------------------------


class TestCommandsDict:
    def test_all_commands_are_mapped(self):
        expected_commands = {"create", "view", "review", "merge", "close", "list", "any-active"}
        assert set(pr.COMMANDS.keys()) == expected_commands

    def test_command_functions_are_correct(self):
        assert pr.COMMANDS["create"] is pr.cmd_create
        assert pr.COMMANDS["view"] is pr.cmd_view
        assert pr.COMMANDS["review"] is pr.cmd_review
        assert pr.COMMANDS["merge"] is pr.cmd_merge
        assert pr.COMMANDS["close"] is pr.cmd_close
        assert pr.COMMANDS["list"] is pr.cmd_list
        assert pr.COMMANDS["any-active"] is pr.cmd_is_open

    def test_commands_dict_has_exactly_seven_entries(self):
        assert len(pr.COMMANDS) == 7


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_exits_when_repo_missing_from_config(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["pr_manager.py", "list"])
        with patch.object(pr, "load_config", return_value={}):
            with pytest.raises(SystemExit) as exc_info:
                pr.main()

        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "repo" in out
        assert "config.yaml" in out

    def test_main_exits_when_repo_is_none(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["pr_manager.py", "list"])
        with patch.object(pr, "load_config", return_value={"repo": None}):
            with pytest.raises(SystemExit) as exc_info:
                pr.main()

        assert exc_info.value.code == 1

    def test_main_runtime_error_prints_to_stderr_and_exits_1(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["pr_manager.py", "list"])
        with patch.object(pr, "load_config", return_value={"repo": REPO}):
            with patch.object(pr, "gh_json", side_effect=RuntimeError("gh CLI failed")):
                with pytest.raises(SystemExit) as exc_info:
                    pr.main()

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Error: gh CLI failed" in err

    def test_main_no_command_exits_0(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["pr_manager.py"])
        with patch.object(pr, "load_config", return_value={"repo": REPO}):
            with pytest.raises(SystemExit) as exc_info:
                pr.main()

        assert exc_info.value.code == 0

    def test_main_dispatches_list_command(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["pr_manager.py", "list"])
        with patch.object(pr, "load_config", return_value={"repo": REPO}):
            with patch.object(pr, "gh_json", return_value=SAMPLE_PR_LIST):
                pr.main()

        out = capsys.readouterr().out
        assert "All PRs (2 total)" in out

    def test_main_dispatches_any_active_command(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["pr_manager.py", "any-active"])
        with patch.object(pr, "load_config", return_value={"repo": REPO}):
            with patch.object(pr, "gh_json", return_value=[{"number": 1}]):
                with pytest.raises(SystemExit) as exc_info:
                    pr.main()

        assert exc_info.value.code == 0
        assert "true" in capsys.readouterr().out
