"""Tests for BuildEntry handler — PR check and prompt generation."""

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from workflow.models.hook_input import UserPromptSubmitInput
from workflow.handlers.build_entry import BuildEntry
from helpers import make_user_prompt_input


def _make_entry(prompt="/build"):
    hook_input = UserPromptSubmitInput.model_validate(make_user_prompt_input(prompt))
    return BuildEntry(hook_input)


# ─── _get_open_prs ───────────────────────────────────────────────────────────


class TestGetOpenPrs:
    @patch("workflow.handlers.build_entry.subprocess.run")
    def test_parses_pr_numbers(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "\n"
                "================================================================================\n"
                "Active PRs (2 total)\n"
                "================================================================================\n"
                "PR #42: Fix login bug (alice) - OPEN\n"
                "PR #99: Add feature (bob) - OPEN\n"
                "================================================================================\n"
            ),
        )
        assert BuildEntry._get_open_prs() == ["42", "99"]

    @patch("workflow.handlers.build_entry.subprocess.run")
    def test_returns_empty_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert BuildEntry._get_open_prs() == []

    @patch("workflow.handlers.build_entry.subprocess.run")
    def test_returns_empty_on_no_prs(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="No active PRs\n")
        assert BuildEntry._get_open_prs() == []


# ─── prompts property ────────────────────────────────────────────────────────


class TestPrompts:
    @patch("workflow.handlers.build_entry.BuildEntry._get_open_prs", return_value=["42", "99"])
    def test_returns_review_prompts_when_prs_exist(self, _mock_prs):
        entry = _make_entry()
        assert entry.prompts == ["/review 42", "/review 99"]

    @patch("workflow.handlers.build_entry.subprocess.run")
    @patch("workflow.handlers.build_entry.BuildEntry._get_open_prs", return_value=[])
    def test_falls_back_to_implement_when_no_prs(self, _mock_prs, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="S-1, S-2")
        entry = _make_entry()
        assert entry.prompts == ["/implement S-1", "/implement S-2"]

    @patch("workflow.handlers.build_entry.subprocess.run")
    @patch("workflow.handlers.build_entry.BuildEntry._get_open_prs", return_value=[])
    def test_filters_out_tasks(self, _mock_prs, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="S-1, T-1, S-2")
        entry = _make_entry()
        assert entry.prompts == ["/implement S-1", "/implement S-2"]

    @patch("workflow.handlers.build_entry.subprocess.run")
    @patch("workflow.handlers.build_entry.BuildEntry._get_open_prs", return_value=[])
    def test_returns_empty_when_no_stories(self, _mock_prs, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        entry = _make_entry()
        assert entry.prompts == []
