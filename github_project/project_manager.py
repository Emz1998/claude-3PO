#!/usr/bin/env python3
"""View and manage project tasks fetched directly from GitHub Projects.

Reads defaults from config.yaml (same directory as this script).
All CLI flags are optional when config.yaml is present.

Examples:
    python github_project/project_manager.py list
    python github_project/project_manager.py list -s priority
    python github_project/project_manager.py list --status "In progress" -w
    python github_project/project_manager.py view TS-004
    python github_project/project_manager.py summary -g priority

    # Override config
    python github_project/project_manager.py --project 5 list

    # Use local file instead of GitHub
    python github_project/project_manager.py --issues-data issues_v2.json list
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# GitHub fetching
# ---------------------------------------------------------------------------


MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]


def _run(cmd: list[str], *, retries: int = MAX_RETRIES) -> str:
    for attempt in range(retries + 1):
        p = subprocess.run(cmd, text=True, capture_output=True)
        if p.returncode == 0:
            return p.stdout.strip()

        is_transient = any(
            s in p.stderr
            for s in ("500 Internal Server Error", "502 ", "503 ", "timeout")
        )
        if is_transient and attempt < retries:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            print(
                f"  Retrying in {delay}s (attempt {attempt + 1}/{retries})...",
                file=sys.stderr,
            )
            time.sleep(delay)
            continue

        raise RuntimeError(
            f"Command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr}"
        )
    raise RuntimeError(f"Command failed after {retries} retries: {' '.join(cmd)}")


def fetch_project_items(project: int, owner: str, limit: int = 500) -> list[dict]:
    out = _run(
        [
            "gh",
            "project",
            "item-list",
            str(project),
            "--owner",
            owner,
            "--format",
            "json",
            "--limit",
            str(limit),
        ]
    )
    if not out:
        return []
    return json.loads(out).get("items", [])


def _parse_key_title(full_title: str) -> tuple[str, str]:
    """Split 'SK-001: Some title' into ('SK-001', 'Some title')."""
    m = re.match(r"^([A-Z]+-\d+):\s+(.+)$", full_title)
    if m:
        return m.group(1), m.group(2)
    return "", full_title


def normalize_items(items: list[dict]) -> list[dict[str, Any]]:
    """Convert raw gh project item-list JSON into a uniform task list."""
    tasks: list[dict[str, Any]] = []
    for item in items:
        content = item.get("content") or {}
        if content.get("type") != "Issue":
            continue

        full_title = item.get("title", "")
        key, title = _parse_key_title(full_title)

        milestone_raw = item.get("milestone")
        milestone = ""
        if isinstance(milestone_raw, dict):
            milestone = milestone_raw.get("title", "")
        elif isinstance(milestone_raw, str):
            milestone = milestone_raw

        tasks.append(
            {
                "key": key,
                "title": title,
                "issue_number": content.get("number"),
                "status": item.get("status", ""),
                "priority": item.get("priority", ""),
                "points": item.get("points", ""),
                "complexity": item.get("complexity", ""),
                "type": item.get("type", ""),
                "start_date": item.get("start date", ""),
                "target_date": item.get("target date", ""),
                "milestone": milestone,
                "labels": item.get("labels") or [],
                "assignees": item.get("assignees") or [],
                "body": content.get("body", ""),
                "url": content.get("url", ""),
            }
        )

    return tasks


# ---------------------------------------------------------------------------
# V2 display flattening
# ---------------------------------------------------------------------------


def flatten_v2_for_display(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten v2 hierarchical data into a flat list for display."""
    result: list[dict[str, Any]] = []

    for story in data.get("stories", []):
        result.append({
            "key": story.get("id", ""),
            "title": story.get("title", ""),
            "issue_number": story.get("issue_number"),
            "status": story.get("status", ""),
            "priority": story.get("priority", ""),
            "points": story.get("points", ""),
            "complexity": "",
            "type": story.get("type", ""),
            "start_date": story.get("startDate", ""),
            "target_date": story.get("targetDate", ""),
            "milestone": data.get("milestone", ""),
            "labels": story.get("labels", []),
            "assignees": story.get("assignees", []),
            "parent_id": "",
        })

        for task in story.get("tasks", []):
            result.append({
                "key": task.get("id", ""),
                "title": task.get("title", ""),
                "issue_number": task.get("issue_number"),
                "status": task.get("status", ""),
                "priority": task.get("priority", ""),
                "points": "",
                "complexity": task.get("complexity", ""),
                "type": task.get("type", "task"),
                "start_date": task.get("startDate", ""),
                "target_date": task.get("targetDate", ""),
                "milestone": data.get("milestone", ""),
                "labels": task.get("labels", []),
                "assignees": task.get("assignees", []),
                "parent_id": story.get("id", ""),
            })

    return result


# ---------------------------------------------------------------------------
# Sorting helpers
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
STATUS_ORDER = {
    "Done": 0,
    "In progress": 1,
    "Ready": 2,
    "Backlog": 3,
}
COMPLEXITY_ORDER = {"XS": 0, "S": 1, "M": 2, "L": 3, "XL": 4}


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


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


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
# Display helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 1] + "\u2026"


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


DEFAULT_COLUMNS: list[tuple[str, str, int]] = [
    ("KEY", "key", 8),
    ("#", "issue_number", 5),
    ("STATUS", "status", 14),
    ("PRI", "priority", 4),
    ("PTS", "points", 4),
    ("CPLX", "complexity", 4),
    ("TITLE", "title", 42),
    ("MILESTONE", "milestone", 10),
]

WIDE_COLUMNS: list[tuple[str, str, int]] = [
    ("KEY", "key", 8),
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

    filtered = [t for t in tasks if _matches(t, filters)]

    if args.sort_by:
        filtered.sort(key=lambda t: _sort_key(args.sort_by, t), reverse=args.reverse)

    if args.keys_only:
        keys = [t.get("key", "") for t in filtered if t.get("key")]
        print(",".join(keys))
        return 0

    columns = WIDE_COLUMNS if args.wide else DEFAULT_COLUMNS
    _print_table(filtered, columns)
    return 0


def _find_task(tasks: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    upper = key.upper()
    for t in tasks:
        if str(t.get("key", "")).upper() == upper:
            return t
        if str(t.get("issue_number", "")) == key:
            return t
    return None


def _format_list(val: Any) -> str:
    if isinstance(val, list):
        return ", ".join(str(v) for v in val) if val else "(none)"
    if val is None or val == "":
        return "(none)"
    return str(val)


TEMPLATES_DIR = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE = TEMPLATES_DIR / "issue_view.txt"


def _render_template(task: dict[str, Any], template_path: Path) -> str:
    tpl = template_path.read_text(encoding="utf-8")

    values: dict[str, str] = {}
    for k, v in task.items():
        if isinstance(v, list):
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


def cmd_view(tasks: list[dict[str, Any]], args: argparse.Namespace) -> int:
    task = _find_task(tasks, args.key)
    if not task:
        print(f"Task not found: {args.key}", file=sys.stderr)
        return 1

    if args.raw:
        _view_raw(task)
    else:
        template = Path(args.template) if args.template else DEFAULT_TEMPLATE
        if not template.exists():
            print(f"Template not found: {template}", file=sys.stderr)
            return 1
        print(_render_template(task, template))
    return 0


# ---------------------------------------------------------------------------
# Edit / Update helpers
# ---------------------------------------------------------------------------


def _gh_json(cmd: list[str]) -> Any:
    out = _run(cmd)
    if not out:
        return None
    return json.loads(out)


def _get_project_id(project_number: int, owner: str) -> str:
    query = """
    query($owner: String!, $number: Int!) {
      user(login: $owner) {
        projectV2(number: $number) { id }
      }
    }
    """
    result = _gh_json([
        "gh", "api", "graphql",
        "-f", f"query={query}",
        "-f", f"owner={owner}",
        "-F", f"number={project_number}",
    ])
    return result["data"]["user"]["projectV2"]["id"]


def _get_project_fields(project_number: int, owner: str) -> dict[str, dict]:
    fields = _gh_json([
        "gh", "project", "field-list",
        str(project_number), "--owner", owner, "--format", "json",
    ]).get("fields", [])
    fmap: dict[str, dict] = {}
    for f in fields:
        entry: dict[str, Any] = {"id": f["id"], "type": f.get("type", "")}
        if "options" in f:
            entry["options"] = {opt["name"]: opt["id"] for opt in f["options"]}
        fmap[f.get("name", "")] = entry
    return fmap


def _get_project_items(project_number: int, owner: str) -> list[dict]:
    return _gh_json([
        "gh", "project", "item-list",
        str(project_number), "--owner", owner,
        "--format", "json", "--limit", "200",
    ]).get("items", [])



def _set_project_field(
    project_id: str,
    item_id: str,
    field_map: dict[str, dict],
    field_name: str,
    value: Any,
) -> bool:
    """Set a project field value. Returns True on success."""
    field = field_map.get(field_name)
    if not field:
        print(f"Field '{field_name}' not found in project", file=sys.stderr)
        return False

    field_id = field["id"]
    cmd = [
        "gh", "project", "item-edit",
        "--id", item_id,
        "--field-id", field_id,
        "--project-id", project_id,
    ]

    has_options = bool(field.get("options"))

    if has_options:
        option_id = field["options"].get(value)
        if not option_id:
            print(
                f"Option '{value}' not found for '{field_name}'. "
                f"Available: {list(field['options'].keys())}",
                file=sys.stderr,
            )
            return False
        cmd += ["--single-select-option-id", option_id]
    elif isinstance(value, (int, float)):
        cmd += ["--number", str(value)]
    elif isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-":
        cmd += ["--date", value]
    elif isinstance(value, str):
        cmd += ["--text", value]
    else:
        print(f"Unsupported value type for '{field_name}': {type(value)}", file=sys.stderr)
        return False

    _run(cmd)
    return True


def _find_item_id(items: list[dict], issue_number: int) -> str | None:
    for item in items:
        if item.get("content", {}).get("number") == issue_number:
            return item["id"]
    return None


def cmd_update(_tasks: list[dict[str, Any]], args: argparse.Namespace) -> int:
    """Update command fetches its own data in parallel for speed."""
    if not args.project or not args.owner:
        print("Provide --project and --owner (or set them in config.yaml).", file=sys.stderr)
        return 1

    repo = args.repo
    if not repo:
        print("Provide --repo (or set it in config.yaml).", file=sys.stderr)
        return 1

    # --- Collect what needs updating ---
    issue_edits: list[str] = []
    if args.milestone is not None:
        issue_edits += ["--milestone", args.milestone]
    if args.add_label:
        for label in args.add_label:
            issue_edits += ["--add-label", label]
    if args.remove_label:
        for label in args.remove_label:
            issue_edits += ["--remove-label", label]
    if args.add_assignee:
        for assignee in args.add_assignee:
            issue_edits += ["--add-assignee", assignee]
    if args.remove_assignee:
        for assignee in args.remove_assignee:
            issue_edits += ["--remove-assignee", assignee]
    if args.title:
        issue_edits += ["--title", args.title]

    project_fields: list[tuple[str, Any]] = []
    if args.status is not None:
        project_fields.append(("Status", args.status))
    if args.priority is not None:
        project_fields.append(("Priority", args.priority))
    if args.complexity is not None:
        project_fields.append(("Complexity", args.complexity))
    if args.points is not None:
        project_fields.append(("Points", args.points))
    if args.start_date is not None:
        project_fields.append(("Start date", args.start_date))
    if args.target_date is not None:
        project_fields.append(("Target date", args.target_date))

    if not issue_edits and not project_fields:
        print("Nothing to update. Use --help to see available options.", file=sys.stderr)
        return 1

    # --- Fetch items, project ID, and fields in parallel ---
    with ThreadPoolExecutor(max_workers=3) as pool:
        items_fut = pool.submit(fetch_project_items, args.project, args.owner)
        pid_fut = pool.submit(_get_project_id, args.project, args.owner)
        fields_fut = pool.submit(_get_project_fields, args.project, args.owner)

        raw_items = items_fut.result()
        project_id = pid_fut.result()
        field_map = fields_fut.result()

    # --- Find the task ---
    tasks = normalize_items(raw_items)
    task = _find_task(tasks, args.key)
    if not task:
        print(f"Task not found: {args.key}", file=sys.stderr)
        return 1

    issue_num = task.get("issue_number")
    if not issue_num:
        print(f"Task {args.key} has no issue number", file=sys.stderr)
        return 1

    # --- Issue-level fields (gh issue edit) ---
    if issue_edits:
        cmd = ["gh", "issue", "edit", str(issue_num), "--repo", repo] + issue_edits
        _run(cmd)
        print(f"Updated issue #{issue_num}")

    # --- Project-level fields ---
    if project_fields:
        item_id = _find_item_id(raw_items, issue_num)
        if not item_id:
            print(f"Could not find project item for issue #{issue_num}", file=sys.stderr)
            return 1

        for field_name, value in project_fields:
            if _set_project_field(project_id, item_id, field_map, field_name, value):
                print(f"Set {field_name} = {value}")

    return 0


def cmd_summary(tasks: list[dict[str, Any]], args: argparse.Namespace) -> int:
    group_field = args.group_by

    groups: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        val = t.get(group_field, "(none)")
        if val is None or val == "":
            val = "(none)"
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val) or "(none)"
        groups.setdefault(str(val), []).append(t)

    order_map = {"status": STATUS_ORDER, "priority": PRIORITY_ORDER, "complexity": COMPLEXITY_ORDER}
    order = order_map.get(group_field, {})
    sorted_keys = sorted(groups.keys(), key=lambda k: order.get(k, 99))

    total_points = sum(
        t.get("points", 0) or 0
        for t in tasks
        if isinstance(t.get("points"), (int, float))
    )

    print(
        f"Summary by {group_field}  ({len(tasks)} tasks, {total_points} pts total)\n"
    )

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


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_FILE = Path(__file__).parent / "config.yaml"


def _load_config() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
    return {}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _load_tasks(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Load tasks from local file or GitHub Projects API."""
    if args.issues_data:
        tasks_path = Path(args.issues_data)
        if not tasks_path.exists():
            print(f"File not found: {tasks_path}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(tasks_path.read_text(encoding="utf-8"))

        # Detect v2 format
        if isinstance(data, dict) and "stories" in data:
            return flatten_v2_for_display(data)

        return data

    if not args.project or not args.owner:
        print(
            "Provide --project and --owner (or set them in config.yaml).",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Fetching from GitHub project {args.owner}/{args.project}...", file=sys.stderr
    )
    raw_items = fetch_project_items(args.project, args.owner)
    tasks = normalize_items(raw_items)
    print(f"Fetched {len(tasks)} tasks\n", file=sys.stderr)
    return tasks


def main() -> int:
    cfg = _load_config()

    ap = argparse.ArgumentParser(
        description="View and manage project tasks from GitHub Projects (or a local issues_v2.json).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  # List all tasks (fetches from GitHub or uses config issues_data path)
  python github_project/project_manager.py list

  # List with sorting (-s/--sort-by) and wide view (-w/--wide shows all columns)
  python github_project/project_manager.py list -s priority
  python github_project/project_manager.py list --status "In progress" -w
  python github_project/project_manager.py list --priority P0 -s status -w

  # View a single task
  python github_project/project_manager.py view TS-004
  python github_project/project_manager.py view 12 --raw

  # Update a task's fields
  python github_project/project_manager.py update TS-004 --status "In progress"
  python github_project/project_manager.py update TS-004 --priority P0 --complexity M
  python github_project/project_manager.py update TS-004 --milestone "Sprint 1"
  python github_project/project_manager.py update TS-004 --add-label bug --add-assignee username
  python github_project/project_manager.py update TS-004 --points 5 --start-date 2026-03-04

  # Summary grouped by field
  python github_project/project_manager.py summary
  python github_project/project_manager.py summary -g priority

  # Override config
  python github_project/project_manager.py --project 5 list
  python github_project/project_manager.py --issues-data path/to/issues_v2.json list
""",
    )
    ap.add_argument(
        "--repo", default=cfg.get("repo"), help="owner/repo (e.g. Emz1998/avaris-ai)"
    )
    ap.add_argument(
        "--project",
        type=int,
        default=cfg.get("project"),
        help="GitHub Project number (v2)",
    )
    ap.add_argument(
        "--owner", default=cfg.get("owner"), help="Project owner (user or org)"
    )
    ap.add_argument("--issues-data", help="Path to local issues_v2.json (overrides GitHub fetch)")

    sub = ap.add_subparsers(dest="command", required=True)

    # --- list ---
    lp = sub.add_parser("list", aliases=["ls"], help="List tasks in a table")
    lp.add_argument(
        "--sort-by",
        "-s",
        help="Sort by field (key, status, priority, complexity, points, title, milestone, start_date, target_date)",
    )
    lp.add_argument("--reverse", "-r", action="store_true", help="Reverse sort order")
    lp.add_argument("--status", help="Filter by status")
    lp.add_argument("--priority", help="Filter by priority (P0, P1, P2)")
    lp.add_argument("--milestone", help="Filter by milestone")
    lp.add_argument("--assignee", help="Filter by assignee")
    lp.add_argument("--label", help="Filter by label")
    lp.add_argument("--complexity", help="Filter by complexity (XS, S, M, L, XL)")
    lp.add_argument("--type", help="Filter by type (task, Spike, Tech)")
    lp.add_argument("--wide", "-w", action="store_true", help="Show all columns")
    lp.add_argument("--keys-only", "-k", action="store_true", help="Output only task keys (comma-separated)")

    # --- view ---
    vp = sub.add_parser("view", help="View a single task by key or issue number")
    vp.add_argument("key", help="Task key (e.g. TS-004) or issue number")
    vp.add_argument(
        "--raw",
        action="store_true",
        help="Show raw key-value pairs instead of formatted view",
    )
    vp.add_argument(
        "--template",
        help="Path to a custom .md template (default: templates/issue_view.md)",
    )

    # --- update ---
    ep = sub.add_parser("update", help="Update a task's fields (issue-level and project-level)")
    ep.add_argument("key", help="Task key (e.g. TS-004) or issue number")
    ep.add_argument("--status", help="Set status (e.g. 'In progress', 'Done', 'Ready', 'Backlog')")
    ep.add_argument("--priority", help="Set priority (P0, P1, P2, P3)")
    ep.add_argument("--complexity", help="Set complexity (XS, S, M, L, XL)")
    ep.add_argument("--points", type=float, help="Set points")
    ep.add_argument("--milestone", help="Set milestone")
    ep.add_argument("--title", help="Set issue title")
    ep.add_argument("--start-date", help="Set start date (YYYY-MM-DD)")
    ep.add_argument("--target-date", help="Set target date (YYYY-MM-DD)")
    ep.add_argument("--add-label", action="append", help="Add a label (repeatable)")
    ep.add_argument("--remove-label", action="append", help="Remove a label (repeatable)")
    ep.add_argument("--add-assignee", action="append", help="Add an assignee (repeatable)")
    ep.add_argument("--remove-assignee", action="append", help="Remove an assignee (repeatable)")

    # --- summary ---
    sp = sub.add_parser("summary", help="Show task summary grouped by a field")
    sp.add_argument(
        "--group-by", "-g", default="status", help="Field to group by (default: status)"
    )

    args = ap.parse_args()

    # update fetches its own data in parallel, skip _load_tasks
    if args.command == "update":
        return cmd_update([], args)

    tasks = _load_tasks(args)
    commands = {
        "list": cmd_list,
        "ls": cmd_list,
        "view": cmd_view,
        "summary": cmd_summary,
    }
    return commands[args.command](tasks, args)


if __name__ == "__main__":
    raise SystemExit(main())
