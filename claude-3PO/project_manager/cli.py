#!/usr/bin/env python3
"""Command-line wrapper for :class:`project_manager.ProjectManager`.

Parses arguments with ``argparse`` and delegates to ``ProjectManager.run``.
All business logic lives in ``project_manager.manager``.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from .manager import ProjectManager

_EPILOG = """\
examples:
  python -m project_manager.cli list
  python -m project_manager.cli list -s priority -w
  python -m project_manager.cli view SK-001
  python -m project_manager.cli update T-017 --status Done
  python -m project_manager.cli progress
  python -m project_manager.cli add-task --parent-story-id SK-001 --title "New task"
  python -m project_manager.cli add-story --type Spike --title "Research X"
  python -m project_manager.cli summary -g priority
  python -m project_manager.cli unblocked
  python -m project_manager.cli unblocked --promote
  python -m project_manager.cli sync --dry-run
  python -m project_manager.cli sync --delete-all
"""


def _add_list_filter_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--status", help="Filter by status")
    p.add_argument("--priority", help="Filter by priority (P0, P1, P2)")
    p.add_argument("--milestone", help="Filter by milestone")
    p.add_argument("--assignee", help="Filter by assignee")
    p.add_argument("--label", help="Filter by label")
    p.add_argument("--complexity", help="Filter by complexity (XS, S, M, L, XL)")
    p.add_argument("--type", help="Filter by type (task, Spike, Tech)")
    p.add_argument("--story", help="Filter tasks by parent story ID (e.g. SK-001)")


def _add_list_display_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--sort-by", "-s", help="Sort by field")
    p.add_argument("--reverse", "-r", action="store_true", help="Reverse sort order")
    p.add_argument("--wide", "-w", action="store_true", help="Show all columns")
    p.add_argument("--keys-only", "-k", action="store_true", help="Output only task keys")
    p.add_argument(
        "--keys-format", choices=["comma", "newline", "json"], default="comma",
        help="Format for -k output: comma (default), newline, json",
    )
    p.add_argument("--json", action="store_true", help="Output results as JSON")


def _add_list_parser(sub: Any) -> None:
    p = sub.add_parser("list", aliases=["ls"], help="List stories and tasks in a table")
    _add_list_filter_flags(p)
    _add_list_display_flags(p)


def _add_view_parser(sub: Any) -> None:
    p = sub.add_parser("view", help="View a single story or task by key or issue number")
    p.add_argument("key", help="Story/task ID (e.g. SK-001, T-017) or issue number")
    p.add_argument("--raw", action="store_true", help="Show raw key-value pairs")
    p.add_argument("--template", help="Path to a custom template")
    p.add_argument("--tasks", action="store_true", help="Show only child tasks")
    p.add_argument(
        "--ready-tasks", action="store_true",
        help="Show unblocked child tasks in Backlog/Ready status",
    )
    p.add_argument("--ac", action="store_true", help="Show only acceptance criteria")
    p.add_argument("--tdd", action="store_true", help="Show TDD flag value")
    p.add_argument("--json", action="store_true", help="Output results as JSON")


def _add_update_parser(sub: Any) -> None:
    p = sub.add_parser("update", help="Update a story or task")
    p.add_argument("key", help="Story/task ID (e.g. T-017, SK-001)")
    p.add_argument("--status", help="Set status")
    p.add_argument("--priority", help="Set priority")
    p.add_argument("--complexity", help="Set complexity")
    p.add_argument("--title", help="Set title")
    p.add_argument("--description", help="Set description")
    p.add_argument("--start-date", help="Set start date (YYYY-MM-DD)")
    p.add_argument("--target-date", help="Set target date (YYYY-MM-DD)")
    p.add_argument(
        "--tdd", type=lambda v: v.lower() in ("true", "1", "yes"), metavar="BOOL",
        help="Set TDD flag (true/false)",
    )
    p.add_argument("--force", action="store_true", help="Bypass status transition guardrail")


def _add_summary_parser(sub: Any) -> None:
    p = sub.add_parser("summary", help="Show item summary grouped by a field")
    p.add_argument(
        "--group-by", "-g", default="status", help="Field to group by (default: status)"
    )


def _add_add_story_parser(sub: Any) -> None:
    p = sub.add_parser("add-story", help="Add a story to the backlog")
    p.add_argument(
        "--type", required=True,
        choices=["Spike", "Tech", "Story", "User Story", "Bug"], help="Story type",
    )
    p.add_argument("--title", required=True, help="Story title")
    p.add_argument("--description", help="Story description")
    p.add_argument("--points", type=int, help="Story points")
    p.add_argument("--priority", help="Priority (P0-P3)")
    p.add_argument("--milestone", help="Milestone")
    p.add_argument("--tdd", action="store_true", default=False, help="Mark story as TDD")


def _add_add_task_parser(sub: Any) -> None:
    p = sub.add_parser("add-task", help="Add a task under a parent story")
    p.add_argument("--parent-story-id", required=True, help="Parent story ID")
    p.add_argument("--title", required=True, help="Task title")
    p.add_argument("--description", help="Task description")
    p.add_argument("--priority", help="Priority (P0-P3)")
    p.add_argument("--complexity", help="Complexity (XS, S, M, L, XL)")
    p.add_argument("--labels", nargs="*", help="Labels")


def _add_sync_override_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--repo", help="Override repo (e.g. owner/repo)")
    p.add_argument("--project", type=int, help="Override project number")
    p.add_argument("--owner", help="Override project owner (user or org)")


def _add_sync_parser(sub: Any) -> None:
    p = sub.add_parser("sync", help="Sync issues to GitHub Projects")
    p.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    p.add_argument(
        "--sync-scope", choices=["all", "stories", "tasks"], default="all",
        help="Which items to sync: all (default), stories only, or tasks only",
    )
    p.add_argument(
        "--delete-all", action="store_true",
        help="Close all issues and remove them from the project",
    )
    _add_sync_override_flags(p)


def _add_unblocked_parser(sub: Any) -> None:
    p = sub.add_parser("unblocked", help="List items whose dependencies are Done")
    p.add_argument("--story", help="Filter to a single story ID (e.g. SK-001)")
    p.add_argument("--promote", action="store_true", help="Promote unblocked Backlog items to Ready")
    p.add_argument("--json", action="store_true", help="Output results as JSON")


def _register_subparsers(sub: Any) -> None:
    _add_list_parser(sub)
    _add_view_parser(sub)
    _add_update_parser(sub)
    _add_summary_parser(sub)
    _add_add_story_parser(sub)
    _add_add_task_parser(sub)
    sub.add_parser("progress", help="Show backlog completion stats")
    _add_sync_parser(sub)
    _add_unblocked_parser(sub)


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Manage a backlog (stories with nested tasks) via local JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOG,
    )
    _register_subparsers(ap.add_subparsers(dest="command", required=True))
    return ap


def _args_to_kwargs(args: argparse.Namespace) -> tuple[str, dict]:
    kwargs = {k: v for k, v in vars(args).items() if not k.startswith("_")}
    command = kwargs.pop("command")
    return command, kwargs


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    command, kwargs = _args_to_kwargs(args)
    return ProjectManager().run(command, **kwargs)


if __name__ == "__main__":
    raise SystemExit(main())
