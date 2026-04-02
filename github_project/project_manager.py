#!/usr/bin/env python3
"""Manage project tasks and stories via local JSON files.

Reads sprint.json and stories.json from the issues/ directory.
No GitHub CLI interaction -- all data lives locally.

Examples:
    python github_project/project_manager.py list
    python github_project/project_manager.py list -s priority
    python github_project/project_manager.py list --status "In progress" -w
    python github_project/project_manager.py view SK-001
    python github_project/project_manager.py view SK-001 --tasks
    python github_project/project_manager.py view SK-001 --tasks --json
    python github_project/project_manager.py view SK-001 --ac
    python github_project/project_manager.py view SK-001 --ac --json
    python github_project/project_manager.py summary -g priority
    python github_project/project_manager.py progress
    python github_project/project_manager.py update T-017 --status Done
    python github_project/project_manager.py add-task --parent-story-id SK-001 --title "New task"
    python github_project/project_manager.py add-story --type Spike --title "Research X"
    python github_project/project_manager.py create-sprint --number 2 --milestone v0.2.0
    python github_project/project_manager.py view SK-001 --ready-tasks
    python github_project/project_manager.py view SK-001 --ready-tasks --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

ISSUES_DIR = Path(__file__).parent / "issues"
SPRINT_PATH = ISSUES_DIR / "sprint.json"
STORIES_PATH = ISSUES_DIR / "stories.json"
TEMPLATES_DIR = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE = TEMPLATES_DIR / "issue_view.txt"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
STATUS_ORDER = {
    "Done": 0,
    "In review": 1,
    "In progress": 2,
    "Ready": 3,
    "Backlog": 4,
}
COMPLEXITY_ORDER = {"XS": 0, "S": 1, "M": 2, "L": 3, "XL": 4}
ACTIVE_STATUSES = {"Backlog", "Ready"}

VALID_TRANSITIONS: dict[str, set[str]] = {
    "Backlog": {"Ready"},
    "Ready": {"In progress", "Backlog"},
    "In progress": {"In review", "Ready"},
    "In review": {"Done", "In progress"},
    "Done": {"In progress"},
}

STORY_TYPE_PREFIXES: dict[str, str] = {
    "Spike": "SK",
    "Bug": "BG",
    "User Story": "US",
}

DEFAULT_COLUMNS: list[tuple[str, str, int]] = [
    ("ID", "id", 8),
    ("#", "issue_number", 5),
    ("STATUS", "status", 14),
    ("PRI", "priority", 4),
    ("PTS", "points", 4),
    ("CPLX", "complexity", 4),
    ("TITLE", "title", 42),
    ("MILESTONE", "milestone", 10),
]

WIDE_COLUMNS: list[tuple[str, str, int]] = [
    ("ID", "id", 8),
    ("#", "issue_number", 5),
    ("STATUS", "status", 14),
    ("PRI", "priority", 4),
    ("PTS", "points", 4),
    ("CPLX", "complexity", 4),
    ("TYPE", "type", 6),
    ("TITLE", "title", 34),
    ("MILESTONE", "milestone", 10),
    ("START", "start_date", 10),
    ("TARGET", "target_date", 10),
    ("ASSIGNEES", "assignees", 16),
]

# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_sprint(path: Path | None = None) -> dict:
    return _load_json(
        path or SPRINT_PATH,
        {"sprint": 0, "milestone": "", "description": "", "due_date": "", "tasks": []},
    )


def _load_stories(path: Path | None = None) -> dict:
    return _load_json(
        path or STORIES_PATH,
        {"project": "", "goal": "", "dates": {}, "totalPoints": 0, "stories": []},
    )


def _save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _save_sprint(data: dict, path: Path | None = None) -> None:
    _save_json(data, path or SPRINT_PATH)


def _save_stories(data: dict, path: Path | None = None) -> None:
    _save_json(data, path or STORIES_PATH)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _sprint_path(args: argparse.Namespace) -> Path:
    return getattr(args, "_sprint_path", None) or SPRINT_PATH


def _stories_path(args: argparse.Namespace) -> Path:
    return getattr(args, "_stories_path", None) or STORIES_PATH


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def _next_id(prefix: str, existing_ids: list[str]) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    max_num = 0
    for eid in existing_ids:
        m = pattern.match(eid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"{prefix}-{max_num + 1:03d}"


# ---------------------------------------------------------------------------
# Item normalization
# ---------------------------------------------------------------------------


def _normalize_story(story: dict, milestone_fallback: str) -> dict:
    return {
        "id": story.get("id", ""),
        "title": story.get("title", ""),
        "issue_number": story.get("issue_number"),
        "status": story.get("status", ""),
        "priority": story.get("priority", ""),
        "points": story.get("points", ""),
        "complexity": "",
        "type": story.get("type", ""),
        "start_date": story.get("startDate", story.get("start_date", "")),
        "target_date": story.get("targetDate", story.get("target_date", "")),
        "milestone": story.get("milestone", milestone_fallback),
        "labels": story.get("labels", []),
        "assignees": story.get("assignees", []),
        "parent_id": "",
        "description": story.get("description", ""),
        "acceptance_criteria": story.get("acceptance_criteria", []),
        "tdd": story.get("tdd", False),
        "blocked_by": story.get("blocked_by", []),
    }


def _normalize_task(task: dict, milestone_fallback: str) -> dict:
    return {
        "id": task.get("id", ""),
        "title": task.get("title", ""),
        "issue_number": task.get("issue_number"),
        "status": task.get("status", ""),
        "priority": task.get("priority", ""),
        "points": "",
        "complexity": task.get("complexity", ""),
        "type": task.get("type", "task"),
        "start_date": task.get("startDate", task.get("start_date", "")),
        "target_date": task.get("targetDate", task.get("target_date", "")),
        "milestone": task.get("milestone", milestone_fallback),
        "labels": task.get("labels", []),
        "assignees": task.get("assignees", []),
        "parent_id": task.get("parent_story_id", ""),
        "description": task.get("description", ""),
        "acceptance_criteria": task.get("acceptance_criteria", []),
        "blocked_by": task.get("blocked_by", []),
    }


def _load_all_items(
    sprint_path: Path | None = None, stories_path: Path | None = None
) -> list[dict[str, Any]]:
    """Combine sprint tasks + stories into a flat list for display."""
    sprint_data = _load_sprint(sprint_path)
    stories_data = _load_stories(stories_path)

    stories = [
        _normalize_story(s, stories_data.get("milestone", ""))
        for s in stories_data.get("stories", [])
    ]
    tasks = [
        _normalize_task(t, sprint_data.get("milestone", ""))
        for t in sprint_data.get("tasks", [])
    ]
    return stories + tasks


# ---------------------------------------------------------------------------
# Sorting / filtering
# ---------------------------------------------------------------------------


def _sort_key(field: str, task: dict[str, Any]) -> Any:
    val = task.get(field, "")
    if val is None:
        val = ""

    if field == "priority":
        return PRIORITY_ORDER.get(val, 99)
    if field == "status":
        return STATUS_ORDER.get(val, 99)
    if field == "complexity":
        return COMPLEXITY_ORDER.get(val, 99)
    if field in ("points", "issue_number"):
        return val if isinstance(val, (int, float)) else 0

    return str(val).lower()


def _matches(task: dict[str, Any], filters: dict[str, str]) -> bool:
    for field, value in filters.items():
        task_val = task.get(field)
        if task_val is None:
            return False
        if isinstance(task_val, list):
            if value.lower() not in [str(v).lower() for v in task_val]:
                return False
        elif str(task_val).lower() != value.lower():
            return False
    return True


# ---------------------------------------------------------------------------
# Status transitions / dependency helpers
# ---------------------------------------------------------------------------


def _validate_transition(current: str, new: str) -> str | None:
    """Return an error message if the transition is invalid, else None."""
    allowed = VALID_TRANSITIONS.get(current)
    if allowed is None:
        return f"Unknown current status '{current}'"
    if new not in allowed:
        return f"Cannot move from '{current}' to '{new}' (allowed: {', '.join(sorted(allowed))}). Use --force to override."
    return None


def _is_unblocked(item_blocked_by: list[str], status_by_id: dict[str, str]) -> bool:
    """Return True if all items in blocked_by are Done (or list is empty)."""
    return all(status_by_id.get(dep, "") == "Done" for dep in item_blocked_by)


def _build_status_map(stories: list[dict], tasks: list[dict]) -> dict[str, str]:
    return {
        **{s.get("id", ""): s.get("status", "") for s in stories},
        **{t.get("id", ""): t.get("status", "") for t in tasks},
    }


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 1] + "\u2026"


def _format_list(val: Any) -> str:
    if isinstance(val, list):
        return ", ".join(str(v) for v in val) if val else "(none)"
    if val is None or val == "":
        return "(none)"
    return str(val)


def _print_table(
    tasks: list[dict[str, Any]], columns: list[tuple[str, str, int]]
) -> None:
    header = "  ".join(h.ljust(w) for h, _, w in columns)
    print(header)
    print("-" * len(header))

    for t in tasks:
        parts: list[str] = []
        for _, key, width in columns:
            val = t.get(key, "")
            if val is None:
                val = ""
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            parts.append(_truncate(str(val), width).ljust(width))
        print("  ".join(parts))

    print(f"\n{len(tasks)} task(s)")


def _render_template(task: dict[str, Any], template_path: Path) -> str:
    tpl = template_path.read_text(encoding="utf-8")

    values: dict[str, str] = {}
    for k, v in task.items():
        if k == "acceptance_criteria" and isinstance(v, list):
            values[k] = "\n".join(f"  - {i}" for i in v) if v else "-"
        elif isinstance(v, list):
            values[k] = ", ".join(str(i) for i in v) if v else "-"
        elif v is None or v == "":
            values[k] = "-"
        elif k == "points":
            values[k] = f"{v} pts"
        else:
            values[k] = str(v)

    return tpl.format_map(values)


def _view_raw(task: dict[str, Any]) -> None:
    max_label = max(len(k) for k in task) + 1
    for k, v in task.items():
        label = f"{k}:".ljust(max_label)
        print(f"  {label}  {_format_list(v)}")


def _find_task(tasks: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    upper = key.upper()
    for t in tasks:
        if str(t.get("id", "")).upper() == upper:
            return t
        if str(t.get("issue_number", "")) == key:
            return t
    return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_list(tasks: list[dict[str, Any]], args: argparse.Namespace) -> int:
    filters: dict[str, str] = {}
    if args.status:
        filters["status"] = args.status
    if args.priority:
        filters["priority"] = args.priority
    if args.milestone:
        filters["milestone"] = args.milestone
    if args.assignee:
        filters["assignees"] = args.assignee
    if args.label:
        filters["labels"] = args.label
    if getattr(args, "complexity", None):
        filters["complexity"] = args.complexity
    if getattr(args, "type", None):
        filters["type"] = args.type

    story_filter = getattr(args, "story", None)

    filtered = [t for t in tasks if _matches(t, filters)]

    if story_filter:
        story_upper = story_filter.upper()
        filtered = [
            t for t in filtered if t.get("parent_id", "").upper() == story_upper
        ]

    if args.sort_by:
        filtered.sort(key=lambda t: _sort_key(args.sort_by, t), reverse=args.reverse)

    if getattr(args, "json", False):
        print(json.dumps(filtered, indent=2))
        return 0

    if args.keys_only:
        keys = [t.get("id", "") for t in filtered if t.get("id")]
        fmt = getattr(args, "keys_format", "comma")
        if fmt == "newline":
            print("\n".join(keys))
        elif fmt == "json":
            print(json.dumps(keys))
        else:
            print(",".join(keys))
        return 0

    columns = WIDE_COLUMNS if args.wide else DEFAULT_COLUMNS
    _print_table(filtered, columns)
    return 0


def cmd_view(tasks: list[dict[str, Any]], args: argparse.Namespace) -> int:
    task = _find_task(tasks, args.key)
    if not task:
        print(f"Task not found: {args.key}", file=sys.stderr)
        return 1

    key = task.get("id", "")
    tasks_only = getattr(args, "tasks", False)
    ready_tasks = getattr(args, "ready_tasks", False)
    ac_only = getattr(args, "ac", False)
    tdd_only = getattr(args, "tdd", False)
    as_json = getattr(args, "json", False)

    if ready_tasks:
        status_by_key = {t.get("id", ""): t.get("status", "") for t in tasks}
        children = [
            t
            for t in tasks
            if t.get("parent_id") == key
            and t.get("status") in ACTIVE_STATUSES
            and _is_unblocked(t.get("blocked_by", []), status_by_key)
        ]
        if as_json:
            print(json.dumps(children, indent=2))
        else:
            if children:
                print(f"Ready tasks ({key}) — {len(children)}:")
                for c in children:
                    print(
                        f"  {c.get('id', ''):<8} {c.get('status', ''):<14} {c.get('title', '')}"
                    )
            else:
                print("No ready tasks found.")
        return 0

    if tdd_only:
        tdd = task.get("tdd", False)
        if as_json:
            print(json.dumps({"tdd": tdd}, indent=2))
        else:
            print(f"TDD ({key}): {tdd}")
        return 0

    if ac_only:
        ac = task.get("acceptance_criteria", [])
        if as_json:
            print(json.dumps(ac, indent=2))
        else:
            if ac:
                print(f"Acceptance Criteria ({key}):")
                for i, criterion in enumerate(ac, 1):
                    print(f"  {i}. {criterion}")
            else:
                print("No acceptance criteria found.")
        return 0

    if tasks_only:
        children = [t for t in tasks if t.get("parent_id") == key]
        if as_json:
            print(json.dumps(children, indent=2))
        else:
            if children:
                print(f"Child tasks ({len(children)}):")
                for c in children:
                    print(
                        f"  {c.get('id', ''):<8} {c.get('status', ''):<14} {c.get('title', '')}"
                    )
            else:
                print("No child tasks found.")
        return 0

    if as_json:
        print(json.dumps(task, indent=2))
        return 0

    if args.raw:
        _view_raw(task)
    else:
        template = Path(args.template) if args.template else DEFAULT_TEMPLATE
        if not template.exists():
            print(f"Template not found: {template}", file=sys.stderr)
            return 1
        print(_render_template(task, template))

    # If viewing a story, also show its child tasks
    if not key.startswith("T-"):
        children = [t for t in tasks if t.get("parent_id") == key]
        if children:
            print(f"\nChild tasks ({len(children)}):")
            for c in children:
                print(
                    f"  {c.get('id', ''):<8} {c.get('status', ''):<14} {c.get('title', '')}"
                )

    return 0


def cmd_summary(tasks: list[dict[str, Any]], args: argparse.Namespace) -> int:
    group_field = args.group_by

    groups: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        val = t.get(group_field, "(none)")
        if val is None or val == "":
            val = "(none)"
        if isinstance(val, list):
            val = _format_list(val)
        groups.setdefault(str(val), []).append(t)

    order_map = {
        "status": STATUS_ORDER,
        "priority": PRIORITY_ORDER,
        "complexity": COMPLEXITY_ORDER,
    }
    order = order_map.get(group_field, {})
    sorted_keys = sorted(groups.keys(), key=lambda k: order.get(k, 99))

    total_points = sum(
        t.get("points", 0) or 0
        for t in tasks
        if isinstance(t.get("points"), (int, float))
    )

    print(f"Summary by {group_field}  ({len(tasks)} tasks, {total_points} pts total)\n")

    header = f"  {'GROUP'.ljust(16)}  {'COUNT':>5}  {'PTS':>5}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for key in sorted_keys:
        group_tasks = groups[key]
        pts = sum(
            t.get("points", 0) or 0
            for t in group_tasks
            if isinstance(t.get("points"), (int, float))
        )
        print(f"  {key.ljust(16)}  {len(group_tasks):>5}  {pts:>5}")

    return 0


def cmd_create_sprint(args: argparse.Namespace) -> int:
    sprint_path = _sprint_path(args)
    data = {
        "sprint": args.number,
        "milestone": args.milestone or "",
        "description": args.description or "",
        "due_date": args.due_date or "",
        "tasks": [],
    }
    _save_sprint(data, sprint_path)
    print(f"Created sprint {args.number}")
    return 0


def cmd_add_story(args: argparse.Namespace) -> int:
    stories_path = _stories_path(args)
    data = _load_stories(stories_path)

    existing_ids = [s.get("id", "") for s in data.get("stories", [])]
    prefix = STORY_TYPE_PREFIXES.get(args.type, "TS")
    new_id = _next_id(prefix, existing_ids)

    story = {
        "id": new_id,
        "type": args.type,
        "labels": [],
        "title": args.title,
        "description": args.description or "",
        "points": args.points or 0,
        "status": "Backlog",
        "tdd": bool(getattr(args, "tdd", False)),
        "startDate": "",
        "targetDate": "",
        "priority": args.priority or "P2",
        "is_blocking": [],
        "blocked_by": [],
        "acceptance_criteria": [],
        "item_type": "story",
        "milestone": args.milestone or data.get("milestone", ""),
    }

    data.setdefault("stories", []).append(story)
    _save_stories(data, stories_path)
    print(f"Added story {new_id}: {args.title}")
    return 0


def cmd_add_task(args: argparse.Namespace) -> int:
    sprint_path = _sprint_path(args)
    data = _load_sprint(sprint_path)

    existing_ids = [t.get("id", "") for t in data.get("tasks", [])]
    new_id = _next_id("T", existing_ids)

    task = {
        "id": new_id,
        "type": "task",
        "parent_story_id": args.parent_story_id,
        "labels": args.labels or [],
        "title": args.title,
        "description": args.description or "",
        "status": "Backlog",
        "priority": args.priority or "P2",
        "complexity": args.complexity or "",
        "is_blocking": [],
        "blocked_by": [],
        "acceptance_criteria": [],
        "item_type": "task",
        "milestone": data.get("milestone", ""),
        "start_date": "",
        "target_date": "",
    }

    data.setdefault("tasks", []).append(task)
    _save_sprint(data, sprint_path)
    print(f"Added task {new_id}: {args.title}")
    return 0


def cmd_complete_sprint(args: argparse.Namespace) -> int:
    sprint_path = _sprint_path(args)
    stories_path = _stories_path(args)

    if not sprint_path.exists():
        print("No active sprint found.", file=sys.stderr)
        return 1

    data = _load_sprint(sprint_path)
    sprint_num = data.get("sprint", 0)

    archive_dir = sprint_path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    sprint_path.rename(archive_dir / f"sprint-{sprint_num}.json")
    if stories_path.exists():
        stories_path.rename(archive_dir / f"stories-{sprint_num}.json")

    print(f"Archived sprint {sprint_num} to {archive_dir}/")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    sprint_path = _sprint_path(args)
    stories_path = _stories_path(args)

    key = args.key.upper()

    updates: dict[str, Any] = {}
    if args.status is not None:
        updates["status"] = args.status
    if args.priority is not None:
        updates["priority"] = args.priority
    if args.complexity is not None:
        updates["complexity"] = args.complexity
    if args.title is not None:
        updates["title"] = args.title
    if args.description is not None:
        updates["description"] = args.description
    if args.start_date is not None:
        updates["start_date"] = args.start_date
    if args.target_date is not None:
        updates["target_date"] = args.target_date
    if getattr(args, "tdd", None) is not None:
        updates["tdd"] = args.tdd

    if not updates:
        print(
            "Nothing to update. Use --help to see available options.", file=sys.stderr
        )
        return 1

    force = getattr(args, "force", False)

    if key.startswith("T-"):
        data = _load_sprint(sprint_path)
        for task in data.get("tasks", []):
            if task.get("id", "").upper() == key:
                if "status" in updates and not force:
                    err = _validate_transition(
                        task.get("status", ""), updates["status"]
                    )
                    if err:
                        print(err, file=sys.stderr)
                        return 1
                for field, value in updates.items():
                    task[field] = value
                _save_sprint(data, sprint_path)
                print(f"Updated {key}")
                return 0
        print(f"Task not found: {args.key}", file=sys.stderr)
        return 1

    data = _load_stories(stories_path)
    for story in data.get("stories", []):
        if story.get("id", "").upper() == key:
            if "status" in updates and not force:
                err = _validate_transition(story.get("status", ""), updates["status"])
                if err:
                    print(err, file=sys.stderr)
                    return 1
            for field, value in updates.items():
                # Map snake_case to camelCase for stories
                if field == "start_date":
                    story["startDate"] = value
                elif field == "target_date":
                    story["targetDate"] = value
                else:
                    story[field] = value
            _save_stories(data, stories_path)
            print(f"Updated {key}")
            return 0

    print(f"Item not found: {args.key}", file=sys.stderr)
    return 1


def cmd_progress(args: argparse.Namespace) -> int:
    sprint_path = _sprint_path(args)
    stories_path = _stories_path(args)

    sprint_data = _load_sprint(sprint_path)
    stories_data = _load_stories(stories_path)

    tasks = sprint_data.get("tasks", [])
    stories = stories_data.get("stories", [])

    total_tasks = len(tasks)
    done_tasks = sum(1 for t in tasks if t.get("status") == "Done")

    print(
        f"Sprint {sprint_data.get('sprint', '?')} - {sprint_data.get('milestone', '')}"
    )
    print(f"{'=' * 40}")

    if total_tasks > 0:
        pct = done_tasks / total_tasks * 100
        print(f"Overall: {done_tasks}/{total_tasks} tasks done ({pct:.0f}%)")
    else:
        print("Overall: No tasks")

    status_counts: dict[str, int] = {}
    for t in tasks:
        s = t.get("status", "(none)")
        status_counts[s] = status_counts.get(s, 0) + 1

    if status_counts:
        print(f"\nStatus distribution:")
        for status in sorted(status_counts, key=lambda s: STATUS_ORDER.get(s, 99)):
            print(f"  {status:<14} {status_counts[status]}")

    if stories:
        total_stories = len(stories)
        done_stories = sum(1 for s in stories if s.get("status") == "Done")
        print(f"\nStory completion: {done_stories}/{total_stories} stories done")
        for story in sorted(
            stories, key=lambda s: STATUS_ORDER.get(s.get("status", ""), 99)
        ):
            sid = story.get("id", "")
            status = story.get("status", "")
            print(f"  {sid:<8} {status:<14} {story.get('title', '')[:40]}")

    if stories:
        tasks_by_story: dict[str, list[dict]] = {}
        for t in tasks:
            tasks_by_story.setdefault(t.get("parent_story_id", ""), []).append(t)

        print(f"\nPer-story task completion:")
        for story in stories:
            sid = story.get("id", "")
            story_tasks = tasks_by_story.get(sid, [])
            story_done = sum(1 for t in story_tasks if t.get("status") == "Done")
            total = len(story_tasks)
            if total > 0:
                pct = story_done / total * 100
                print(
                    f"  {sid:<8} {story.get('title', '')[:40]:<40} {story_done}/{total} ({pct:.0f}%)"
                )
            else:
                print(f"  {sid:<8} {story.get('title', '')[:40]:<40} (no tasks)")

    return 0


def cmd_unblocked(args: argparse.Namespace) -> int:
    sprint_path = _sprint_path(args)
    stories_path = _stories_path(args)

    sprint_data = _load_sprint(sprint_path)
    stories_data = _load_stories(stories_path)

    tasks = sprint_data.get("tasks", [])
    stories = stories_data.get("stories", [])

    status_by_id = _build_status_map(stories, tasks)

    story_filter = getattr(args, "story", None)
    story_filter_upper = story_filter.upper() if story_filter else None

    unblocked_stories = [
        s
        for s in stories
        if s.get("status") in ACTIVE_STATUSES
        and _is_unblocked(s.get("blocked_by", []), status_by_id)
        and (
            story_filter_upper is None or s.get("id", "").upper() == story_filter_upper
        )
    ]
    unblocked_tasks = [
        t
        for t in tasks
        if t.get("status") in ACTIVE_STATUSES
        and _is_unblocked(t.get("blocked_by", []), status_by_id)
        and (
            story_filter_upper is None
            or t.get("parent_story_id", "").upper() == story_filter_upper
        )
    ]

    all_unblocked = unblocked_stories + unblocked_tasks
    if not all_unblocked:
        print("No unblocked items found.")
        return 0

    if getattr(args, "json", False):
        output = []
        for item in unblocked_stories:
            output.append(
                {
                    "id": item.get("id", ""),
                    "type": item.get("type", "story"),
                    "status": item.get("status", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "blocked_by": item.get("blocked_by", []),
                }
            )
        for item in unblocked_tasks:
            output.append(
                {
                    "id": item.get("id", ""),
                    "type": item.get("type", "task"),
                    "status": item.get("status", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "blocked_by": item.get("blocked_by", []),
                    "parent_story_id": item.get("parent_story_id", ""),
                }
            )
        print(json.dumps(output, indent=2))
        return 0

    print(f"Unblocked items ({len(all_unblocked)}):")
    print("-" * 50)
    for item in unblocked_stories:
        print(
            f"  {item.get('id', ''):<8} {item.get('status', ''):<12} {item.get('title', '')[:50]}"
        )
    for item in unblocked_tasks:
        print(
            f"  {item.get('id', ''):<8} {item.get('status', ''):<12} {item.get('title', '')[:50]}"
        )

    if getattr(args, "promote", False):
        promoted = 0
        unblocked_story_ids = {x.get("id") for x in unblocked_stories}
        for s in stories_data.get("stories", []):
            if s.get("id") in unblocked_story_ids and s.get("status") == "Backlog":
                s["status"] = "Ready"
                promoted += 1
        _save_stories(stories_data, stories_path)

        unblocked_task_ids = {x.get("id") for x in unblocked_tasks}
        for t in sprint_data.get("tasks", []):
            if t.get("id") in unblocked_task_ids and t.get("status") == "Backlog":
                t["status"] = "Ready"
                promoted += 1
        _save_sprint(sprint_data, sprint_path)

        print(f"\nPromoted {promoted} item(s) to Ready.")

    return 0


def cmd_sprint_info(args: argparse.Namespace) -> int:
    sprint_path = _sprint_path(args)
    data = _load_sprint(sprint_path)
    print(data.get("sprint", 1))
    return 0


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Manage project tasks and stories via local JSON files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python github_project/project_manager.py list
  python github_project/project_manager.py list -s priority -w
  python github_project/project_manager.py view SK-001
  python github_project/project_manager.py update T-017 --status Done
  python github_project/project_manager.py progress
  python github_project/project_manager.py add-task --parent-story-id SK-001 --title "New task"
  python github_project/project_manager.py add-story --type Spike --title "Research X"
  python github_project/project_manager.py create-sprint --number 2 --milestone v0.2.0
  python github_project/project_manager.py summary -g priority
  python github_project/project_manager.py unblocked
  python github_project/project_manager.py unblocked --promote
""",
    )

    sub = ap.add_subparsers(dest="command", required=True)

    # --- list ---
    lp = sub.add_parser("list", aliases=["ls"], help="List tasks in a table")
    lp.add_argument("--sort-by", "-s", help="Sort by field")
    lp.add_argument("--reverse", "-r", action="store_true", help="Reverse sort order")
    lp.add_argument("--status", help="Filter by status")
    lp.add_argument("--priority", help="Filter by priority (P0, P1, P2)")
    lp.add_argument("--milestone", help="Filter by milestone")
    lp.add_argument("--assignee", help="Filter by assignee")
    lp.add_argument("--label", help="Filter by label")
    lp.add_argument("--complexity", help="Filter by complexity (XS, S, M, L, XL)")
    lp.add_argument("--type", help="Filter by type (task, Spike, Tech)")
    lp.add_argument("--story", help="Filter tasks by parent story ID (e.g. SK-001)")
    lp.add_argument("--wide", "-w", action="store_true", help="Show all columns")
    lp.add_argument(
        "--keys-only",
        "-k",
        action="store_true",
        help="Output only task keys",
    )
    lp.add_argument(
        "--keys-format",
        choices=["comma", "newline", "json"],
        default="comma",
        help="Format for -k output: comma (default), newline, json",
    )
    lp.add_argument("--json", action="store_true", help="Output results as JSON")

    # --- view ---
    vp = sub.add_parser("view", help="View a single task by key or issue number")
    vp.add_argument("key", help="Task ID (e.g. TS-004) or issue number")
    vp.add_argument("--raw", action="store_true", help="Show raw key-value pairs")
    vp.add_argument("--template", help="Path to a custom template")
    vp.add_argument("--tasks", action="store_true", help="Show only child tasks")
    vp.add_argument(
        "--ready-tasks",
        action="store_true",
        help="Show unblocked child tasks in Backlog/Ready status",
    )
    vp.add_argument("--ac", action="store_true", help="Show only acceptance criteria")
    vp.add_argument("--tdd", action="store_true", help="Show TDD flag value")
    vp.add_argument("--json", action="store_true", help="Output results as JSON")

    # --- update ---
    ep = sub.add_parser("update", help="Update a task or story")
    ep.add_argument("key", help="Task/story ID (e.g. T-017, SK-001)")
    ep.add_argument("--status", help="Set status")
    ep.add_argument("--priority", help="Set priority")
    ep.add_argument("--complexity", help="Set complexity")
    ep.add_argument("--title", help="Set title")
    ep.add_argument("--description", help="Set description")
    ep.add_argument("--start-date", help="Set start date (YYYY-MM-DD)")
    ep.add_argument("--target-date", help="Set target date (YYYY-MM-DD)")
    ep.add_argument(
        "--tdd",
        type=lambda v: v.lower() in ("true", "1", "yes"),
        metavar="BOOL",
        help="Set TDD flag (true/false)",
    )
    ep.add_argument(
        "--force", action="store_true", help="Bypass status transition guardrail"
    )

    # --- summary ---
    sp = sub.add_parser("summary", help="Show task summary grouped by a field")
    sp.add_argument(
        "--group-by", "-g", default="status", help="Field to group by (default: status)"
    )

    # --- create-sprint ---
    cs = sub.add_parser("create-sprint", help="Create a new sprint")
    cs.add_argument("--number", type=int, required=True, help="Sprint number")
    cs.add_argument("--milestone", help="Milestone name")
    cs.add_argument("--description", help="Sprint description")
    cs.add_argument("--due-date", help="Due date (YYYY-MM-DD)")

    # --- complete-sprint ---
    sub.add_parser("complete-sprint", help="Archive current sprint files")

    # --- add-story ---
    ast = sub.add_parser("add-story", help="Add a story to the project")
    ast.add_argument(
        "--type",
        required=True,
        choices=["Spike", "Tech", "Story", "User Story", "Bug"],
        help="Story type",
    )
    ast.add_argument("--title", required=True, help="Story title")
    ast.add_argument("--description", help="Story description")
    ast.add_argument("--points", type=int, help="Story points")
    ast.add_argument("--priority", help="Priority (P0-P3)")
    ast.add_argument("--milestone", help="Milestone")
    ast.add_argument(
        "--tdd", action="store_true", default=False, help="Mark story as TDD"
    )

    # --- add-task ---
    at = sub.add_parser("add-task", help="Add a task to the sprint")
    at.add_argument(
        "--parent-story-id", required=True, help="Parent story ID (e.g. SK-001)"
    )
    at.add_argument("--title", required=True, help="Task title")
    at.add_argument("--description", help="Task description")
    at.add_argument("--priority", help="Priority (P0-P3)")
    at.add_argument("--complexity", help="Complexity (XS, S, M, L, XL)")
    at.add_argument("--labels", nargs="*", help="Labels")

    # --- progress ---
    sub.add_parser("progress", help="Show sprint completion stats")

    # --- sprint-info ---
    sub.add_parser("sprint-info", help="Print current sprint number")

    return ap


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args = _build_parser().parse_args()

    direct_commands = {
        "create-sprint": cmd_create_sprint,
        "complete-sprint": cmd_complete_sprint,
        "add-story": cmd_add_story,
        "add-task": cmd_add_task,
        "update": cmd_update,
        "progress": cmd_progress,
        "sprint-info": cmd_sprint_info,
    }
    if args.command in direct_commands:
        return direct_commands[args.command](args)

    tasks = _load_all_items()
    flat_commands = {
        "list": cmd_list,
        "ls": cmd_list,
        "view": cmd_view,
        "summary": cmd_summary,
    }
    return flat_commands[args.command](tasks, args)


if __name__ == "__main__":
    raise SystemExit(main())
