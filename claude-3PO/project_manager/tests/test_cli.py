"""Tests for project_manager.cli — argparse wrapper."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from project_manager import cli


class _FakePM:
    def __init__(self, *_args, **_kwargs) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, command: str, **kwargs) -> int:
        self.calls.append((command, kwargs))
        return 0


@pytest.fixture
def fake_pm(monkeypatch):
    instance = _FakePM()
    monkeypatch.setattr(cli, "ProjectManager", lambda *a, **k: instance)
    return instance


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestParser:
    def test_has_core_commands(self):
        help_text = cli._build_parser().format_help()
        for cmd in [
            "list", "view", "update", "summary", "add-story", "add-task",
            "progress", "sync", "unblocked",
        ]:
            assert cmd in help_text

    def test_sprint_commands_removed(self):
        help_text = cli._build_parser().format_help()
        for cmd in ["create-sprint", "complete-sprint", "sprint-info"]:
            assert cmd not in help_text

    def test_ls_alias(self):
        args = cli._build_parser().parse_args(["ls"])
        assert args.command == "ls"

    def test_list_flags(self):
        args = cli._build_parser().parse_args(
            ["list", "--status", "Done", "--sort-by", "priority", "--wide"]
        )
        assert args.status == "Done"
        assert args.sort_by == "priority"
        assert args.wide is True

    def test_view_positional_key(self):
        args = cli._build_parser().parse_args(["view", "SK-001", "--raw"])
        assert args.key == "SK-001"
        assert args.raw is True

    def test_update_tdd_bool(self):
        args = cli._build_parser().parse_args(["update", "T-001", "--tdd", "true"])
        assert args.tdd is True
        args = cli._build_parser().parse_args(["update", "T-001", "--tdd", "no"])
        assert args.tdd is False

    def test_unblocked_flags(self):
        args = cli._build_parser().parse_args(["unblocked", "--promote", "--json"])
        assert args.promote is True
        assert args.json is True

    def test_sync_accepts_overrides(self):
        args = cli._build_parser().parse_args(
            ["sync", "--repo", "me/r", "--project", "7", "--owner", "me"]
        )
        assert args.repo == "me/r"
        assert args.project == 7
        assert args.owner == "me"


# ---------------------------------------------------------------------------
# _args_to_kwargs
# ---------------------------------------------------------------------------


class TestArgsToKwargs:
    def test_strips_command(self):
        args = cli._build_parser().parse_args(["list", "--wide"])
        command, kwargs = cli._args_to_kwargs(args)
        assert command == "list"
        assert "command" not in kwargs
        assert kwargs["wide"] is True

    def test_hyphens_to_underscores(self):
        args = cli._build_parser().parse_args(
            ["list", "--sort-by", "priority", "--keys-only"]
        )
        _, kwargs = cli._args_to_kwargs(args)
        assert kwargs["sort_by"] == "priority"
        assert kwargs["keys_only"] is True

    def test_add_task_kwargs(self):
        args = cli._build_parser().parse_args(
            ["add-task", "--parent-story-id", "SK-001", "--title", "Hi"]
        )
        command, kwargs = cli._args_to_kwargs(args)
        assert command == "add-task"
        assert kwargs["parent_story_id"] == "SK-001"
        assert kwargs["title"] == "Hi"


# ---------------------------------------------------------------------------
# main() dispatch
# ---------------------------------------------------------------------------


class TestMain:
    def test_dispatches_progress(self, fake_pm):
        assert cli.main(["progress"]) == 0
        assert fake_pm.calls == [("progress", {})]

    def test_dispatches_list_kwargs(self, fake_pm):
        cli.main(["list", "--status", "Done", "--wide"])
        command, kwargs = fake_pm.calls[0]
        assert command == "list"
        assert kwargs["status"] == "Done"
        assert kwargs["wide"] is True

    def test_dispatches_view(self, fake_pm):
        cli.main(["view", "SK-001", "--raw"])
        command, kwargs = fake_pm.calls[0]
        assert command == "view"
        assert kwargs["key"] == "SK-001"
        assert kwargs["raw"] is True

    def test_dispatches_update(self, fake_pm):
        cli.main(["update", "T-001", "--status", "Done", "--force"])
        command, kwargs = fake_pm.calls[0]
        assert command == "update"
        assert kwargs["key"] == "T-001"
        assert kwargs["status"] == "Done"
        assert kwargs["force"] is True

    def test_dispatches_add_story(self, fake_pm):
        cli.main(["add-story", "--type", "Bug", "--title", "Crash"])
        command, kwargs = fake_pm.calls[0]
        assert command == "add-story"
        assert kwargs["type"] == "Bug"
        assert kwargs["title"] == "Crash"

    def test_dispatches_add_task(self, fake_pm):
        cli.main(["add-task", "--parent-story-id", "SK-001", "--title", "T"])
        command, kwargs = fake_pm.calls[0]
        assert command == "add-task"
        assert kwargs["parent_story_id"] == "SK-001"

    def test_dispatches_unblocked_promote(self, fake_pm):
        cli.main(["unblocked", "--promote"])
        command, kwargs = fake_pm.calls[0]
        assert command == "unblocked"
        assert kwargs["promote"] is True

    def test_sync_dry_run(self, fake_pm):
        cli.main(["sync", "--dry-run"])
        command, kwargs = fake_pm.calls[0]
        assert command == "sync"
        assert kwargs["dry_run"] is True
        assert "sync_scope" not in kwargs

    def test_sync_overrides(self, fake_pm):
        cli.main(["sync", "--repo", "o/r", "--project", "5", "--owner", "me"])
        _, kwargs = fake_pm.calls[0]
        assert kwargs["repo"] == "o/r"
        assert kwargs["project"] == 5
        assert kwargs["owner"] == "me"


class TestWatchDispatch:
    def test_watch_routes_to_watcher_main(self, monkeypatch, fake_pm):
        # The `watch` subcommand must bypass ProjectManager.run and invoke
        # watcher.main_from_args directly — it's a long-running foreground
        # process, not a one-shot command.
        from project_manager import watcher

        captured: dict = {}

        def fake(args):
            captured["backlog_path"] = args.backlog_path
            captured["repo"] = args.repo
            return 0

        monkeypatch.setattr(watcher, "main_from_args", fake)
        rc = cli.main(["watch", "--backlog-path", "/tmp/p.json", "--repo", "o/r"])
        assert rc == 0
        assert captured == {"backlog_path": "/tmp/p.json", "repo": "o/r"}
        assert fake_pm.calls == []  # ProjectManager must not be touched
