"""Project manager library: manage a backlog (stories with nested tasks).

Exposes the ``ProjectManager`` class with a ``run(command, **kwargs)``
dispatcher. The CLI wrapper lives in ``project_manager.cli``.
"""
from __future__ import annotations

import json as _json
import re
import sys
from pathlib import Path
from typing import Any

from .config import DATA_PATHS

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

BACKLOG_PATH = Path(DATA_PATHS["backlog"])
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

BACKLOG_DEFAULT: dict[str, Any] = {
    "project": "",
    "goal": "",
    "dates": {},
    "totalPoints": 0,
    "stories": [],
}

# ---------------------------------------------------------------------------
# JSON primitives
# ---------------------------------------------------------------------------


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return _json.loads(_json.dumps(default))
    return _json.loads(path.read_text(encoding="utf-8"))


def _save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(data, indent=2) + "\n", encoding="utf-8")


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
# Item normalization (flattened view)
# ---------------------------------------------------------------------------


def _base_item_fields(item: dict) -> dict:
    # `blocked_by` is story-only — tasks are local-only sub-items now and
    # gain no GitHub-level dependencies. Adding it to the base would
    # silently re-introduce empty blocking arrays on every task row.
    return {
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "issue_number": item.get("issue_number"),
        "status": item.get("status", ""),
        "priority": item.get("priority", ""),
        "start_date": item.get("start_date", ""),
        "target_date": item.get("target_date", ""),
        "milestone": item.get("milestone", ""),
        "labels": item.get("labels", []),
        "assignees": item.get("assignees", []),
        "description": item.get("description", ""),
        "acceptance_criteria": item.get("acceptance_criteria", []),
    }


def _normalize_story(story: dict) -> dict:
    return {
        **_base_item_fields(story),
        "points": story.get("points", ""),
        "complexity": "",
        "type": story.get("type", ""),
        "parent_id": "",
        "tdd": story.get("tdd", False),
        "blocked_by": story.get("blocked_by", []),
    }


def _normalize_task(task: dict, parent_id: str, parent_milestone: str) -> dict:
    fields = _base_item_fields(task)
    if not fields["milestone"]:
        fields["milestone"] = parent_milestone
    return {
        **fields,
        "points": "",
        "complexity": task.get("complexity", ""),
        "type": task.get("type", "task"),
        "parent_id": parent_id,
    }


def _flatten_items(backlog: dict) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for story in backlog.get("stories", []):
        items.append(_normalize_story(story))
    for story in backlog.get("stories", []):
        for task in story.get("tasks", []):
            items.append(
                _normalize_task(task, story.get("id", ""), story.get("milestone", ""))
            )
    return items


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
    allowed = VALID_TRANSITIONS.get(current)
    if allowed is None:
        return f"Unknown current status '{current}'"
    if new not in allowed:
        return (
            f"Cannot move from '{current}' to '{new}' (allowed: "
            f"{', '.join(sorted(allowed))}). Use --force to override."
        )
    return None


def is_unblocked(item_blocked_by: list[str], status_by_id: dict[str, str]) -> bool:
    return all(status_by_id.get(dep, "") == "Done" for dep in item_blocked_by)


def build_status_map_from_backlog(backlog: dict) -> dict[str, str]:
    status: dict[str, str] = {}
    for story in backlog.get("stories", []):
        status[story.get("id", "")] = story.get("status", "")
        for task in story.get("tasks", []):
            status[task.get("id", "")] = task.get("status", "")
    return status


# Back-compat aliases — the `_`-prefixed names are used elsewhere in this
# module and by external callers; resolver.py imports the public names.
_is_unblocked = is_unblocked
_build_status_map_from_backlog = build_status_map_from_backlog


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


def _format_cell(val: Any, width: int) -> str:
    if val is None:
        val = ""
    if isinstance(val, list):
        val = ", ".join(str(v) for v in val)
    return _truncate(str(val), width).ljust(width)


def _print_table(
    tasks: list[dict[str, Any]], columns: list[tuple[str, str, int]]
) -> None:
    header = "  ".join(h.ljust(w) for h, _, w in columns)
    print(header)
    print("-" * len(header))
    for t in tasks:
        parts = [_format_cell(t.get(k, ""), w) for _, k, w in columns]
        print("  ".join(parts))
    print(f"\n{len(tasks)} task(s)")


def _template_value(key: str, val: Any) -> str:
    if key == "acceptance_criteria" and isinstance(val, list):
        return "\n".join(f"  - {i}" for i in val) if val else "-"
    if isinstance(val, list):
        return ", ".join(str(i) for i in val) if val else "-"
    if val is None or val == "":
        return "-"
    if key == "points":
        return f"{val} pts"
    return str(val)


def _render_template(task: dict[str, Any], template_path: Path) -> str:
    tpl = template_path.read_text(encoding="utf-8")
    values = {k: _template_value(k, v) for k, v in task.items()}
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


def _print_child_row(c: dict[str, Any]) -> None:
    print(
        f"  {c.get('id', ''):<8} {c.get('status', ''):<14} {c.get('title', '')}"
    )


def _print_children_block(children: list[dict], header: str, empty_msg: str) -> None:
    if not children:
        print(empty_msg)
        return
    print(header)
    for c in children:
        _print_child_row(c)


# ---------------------------------------------------------------------------
# Backlog navigation
# ---------------------------------------------------------------------------


def _find_story(backlog: dict, story_id: str) -> dict | None:
    upper = story_id.upper()
    for s in backlog.get("stories", []):
        if s.get("id", "").upper() == upper:
            return s
    return None


def _find_story_and_task(backlog: dict, key: str) -> tuple[dict | None, dict | None]:
    upper = key.upper()
    for s in backlog.get("stories", []):
        if s.get("id", "").upper() == upper:
            return s, None
        for t in s.get("tasks", []):
            if t.get("id", "").upper() == upper:
                return s, t
    return None, None


def _all_task_ids(backlog: dict) -> list[str]:
    ids: list[str] = []
    for s in backlog.get("stories", []):
        for t in s.get("tasks", []):
            ids.append(t.get("id", ""))
    return ids


# ---------------------------------------------------------------------------
# list helpers
# ---------------------------------------------------------------------------


_LIST_FILTER_ATTR_TO_FIELD = {
    "status": "status",
    "priority": "priority",
    "milestone": "milestone",
    "assignee": "assignees",
    "label": "labels",
    "complexity": "complexity",
    "type": "type",
}


def _build_list_filters(**kwargs: Any) -> dict[str, str]:
    filters: dict[str, str] = {}
    for attr, field in _LIST_FILTER_ATTR_TO_FIELD.items():
        val = kwargs.get(attr)
        if val:
            filters[field] = val
    return filters


def _apply_story_filter(items: list[dict], story: str | None) -> list[dict]:
    if not story:
        return items
    upper = story.upper()
    return [t for t in items if t.get("parent_id", "").upper() == upper]


def _print_keys(keys: list[str], fmt: str) -> None:
    if fmt == "newline":
        print("\n".join(keys))
    elif fmt == "json":
        print(_json.dumps(keys))
    else:
        print(",".join(keys))


def _list_output(
    items: list[dict], wide: bool, keys_only: bool, keys_format: str, as_json: bool
) -> int:
    if as_json:
        print(_json.dumps(items, indent=2))
        return 0
    if keys_only:
        keys = [t.get("id", "") for t in items if t.get("id")]
        _print_keys(keys, keys_format)
        return 0
    _print_table(items, WIDE_COLUMNS if wide else DEFAULT_COLUMNS)
    return 0


# ---------------------------------------------------------------------------
# view helpers
# ---------------------------------------------------------------------------


def _view_ready_tasks(items: list[dict], key: str, as_json: bool) -> int:
    # Tasks no longer carry blockers — eligibility is just status + parent.
    children = [
        t for t in items
        if t.get("parent_id") == key
        and t.get("status") in ACTIVE_STATUSES
    ]
    if as_json:
        print(_json.dumps(children, indent=2))
        return 0
    _print_children_block(
        children, f"Ready tasks ({key}) — {len(children)}:", "No ready tasks found."
    )
    return 0


def _view_tdd(task: dict, key: str, as_json: bool) -> int:
    tdd = task.get("tdd", False)
    if as_json:
        print(_json.dumps({"tdd": tdd}, indent=2))
    else:
        print(f"TDD ({key}): {tdd}")
    return 0


def _view_ac(task: dict, key: str, as_json: bool) -> int:
    ac = task.get("acceptance_criteria", [])
    if as_json:
        print(_json.dumps(ac, indent=2))
        return 0
    if not ac:
        print("No acceptance criteria found.")
        return 0
    print(f"Acceptance Criteria ({key}):")
    for i, criterion in enumerate(ac, 1):
        print(f"  {i}. {criterion}")
    return 0


def _view_children(items: list[dict], key: str, as_json: bool) -> int:
    children = [t for t in items if t.get("parent_id") == key]
    if as_json:
        print(_json.dumps(children, indent=2))
        return 0
    _print_children_block(
        children, f"Child tasks ({len(children)}):", "No child tasks found."
    )
    return 0


def _view_full_output(task: dict, raw: bool, template: str | None) -> int:
    if raw:
        _view_raw(task)
        return 0
    tpl_path = Path(template) if template else DEFAULT_TEMPLATE
    if not tpl_path.exists():
        print(f"Template not found: {tpl_path}", file=sys.stderr)
        return 1
    print(_render_template(task, tpl_path))
    return 0


def _view_full_with_children(
    task: dict, items: list[dict], key: str, raw: bool, template: str | None
) -> int:
    rc = _view_full_output(task, raw, template)
    if rc != 0 or key.startswith("T-"):
        return rc
    children = [t for t in items if t.get("parent_id") == key]
    if children:
        print(f"\nChild tasks ({len(children)}):")
        for c in children:
            _print_child_row(c)
    return rc


def _dispatch_view(
    task: dict,
    items: list[dict],
    raw: bool,
    template: str | None,
    tasks: bool,
    ready_tasks: bool,
    ac: bool,
    tdd: bool,
    as_json: bool,
) -> int:
    key = task.get("id", "")
    if ready_tasks:
        return _view_ready_tasks(items, key, as_json)
    if tdd:
        return _view_tdd(task, key, as_json)
    if ac:
        return _view_ac(task, key, as_json)
    if tasks:
        return _view_children(items, key, as_json)
    if as_json:
        print(_json.dumps(task, indent=2))
        return 0
    return _view_full_with_children(task, items, key, raw, template)


# ---------------------------------------------------------------------------
# summary helpers
# ---------------------------------------------------------------------------


def _group_items(items: list[dict], field: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for t in items:
        val = t.get(field, "(none)")
        if val is None or val == "":
            val = "(none)"
        if isinstance(val, list):
            val = _format_list(val)
        groups.setdefault(str(val), []).append(t)
    return groups


def _sum_points(items: list[dict]) -> int:
    return sum(
        t.get("points", 0) or 0
        for t in items
        if isinstance(t.get("points"), (int, float))
    )


def _print_summary_rows(groups: dict[str, list[dict]], field: str) -> None:
    order_map = {
        "status": STATUS_ORDER,
        "priority": PRIORITY_ORDER,
        "complexity": COMPLEXITY_ORDER,
    }
    order = order_map.get(field, {})
    sorted_keys = sorted(groups.keys(), key=lambda k: order.get(k, 99))
    header = f"  {'GROUP'.ljust(16)}  {'COUNT':>5}  {'PTS':>5}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for key in sorted_keys:
        print(f"  {key.ljust(16)}  {len(groups[key]):>5}  {_sum_points(groups[key]):>5}")


# ---------------------------------------------------------------------------
# update helpers
# ---------------------------------------------------------------------------


_UPDATE_FIELDS = (
    "status",
    "priority",
    "complexity",
    "title",
    "description",
    "start_date",
    "target_date",
    "tdd",
)


def _collect_updates(values: dict[str, Any]) -> dict[str, Any]:
    return {f: v for f, v in values.items() if f in _UPDATE_FIELDS and v is not None}


def _apply_updates(item: dict, updates: dict) -> None:
    for field, value in updates.items():
        item[field] = value


def _check_status_transition(item: dict, updates: dict, force: bool) -> str | None:
    if "status" not in updates or force:
        return None
    return _validate_transition(item.get("status", ""), updates["status"])


# ---------------------------------------------------------------------------
# progress helpers
# ---------------------------------------------------------------------------


def _all_tasks(backlog: dict) -> list[dict]:
    tasks: list[dict] = []
    for s in backlog.get("stories", []):
        tasks.extend(s.get("tasks", []))
    return tasks


def _print_progress_overall(tasks: list[dict], backlog: dict) -> None:
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("status") == "Done")
    project = backlog.get("project", "")
    goal = backlog.get("goal", "")
    print(f"{project} - {goal}")
    print("=" * 40)
    if total > 0:
        print(f"Overall: {done}/{total} tasks done ({done / total * 100:.0f}%)")
    else:
        print("Overall: No tasks")


def _print_status_distribution(tasks: list[dict]) -> None:
    counts: dict[str, int] = {}
    for t in tasks:
        s = t.get("status", "(none)")
        counts[s] = counts.get(s, 0) + 1
    if not counts:
        return
    print("\nStatus distribution:")
    for status in sorted(counts, key=lambda s: STATUS_ORDER.get(s, 99)):
        print(f"  {status:<14} {counts[status]}")


def _print_story_completion(stories: list[dict]) -> None:
    total = len(stories)
    done = sum(1 for s in stories if s.get("status") == "Done")
    print(f"\nStory completion: {done}/{total} stories done")
    for story in sorted(stories, key=lambda s: STATUS_ORDER.get(s.get("status", ""), 99)):
        sid = story.get("id", "")
        status = story.get("status", "")
        print(f"  {sid:<8} {status:<14} {story.get('title', '')[:40]}")


def _print_per_story_row(story: dict) -> None:
    sid = story.get("id", "")
    title = story.get("title", "")[:40]
    story_tasks = story.get("tasks", [])
    total = len(story_tasks)
    if total == 0:
        print(f"  {sid:<8} {title:<40} (no tasks)")
        return
    done = sum(1 for t in story_tasks if t.get("status") == "Done")
    print(f"  {sid:<8} {title:<40} {done}/{total} ({done / total * 100:.0f}%)")


def _print_per_story(stories: list[dict]) -> None:
    print("\nPer-story task completion:")
    for story in stories:
        _print_per_story_row(story)


# ---------------------------------------------------------------------------
# unblocked helpers
# ---------------------------------------------------------------------------


def _filter_unblocked_stories(
    stories: list[dict], status_by_id: dict[str, str], story_filter: str | None
) -> list[dict]:
    upper = story_filter.upper() if story_filter else None
    return [
        s for s in stories
        if s.get("status") in ACTIVE_STATUSES
        and _is_unblocked(s.get("blocked_by", []), status_by_id)
        and (upper is None or s.get("id", "").upper() == upper)
    ]


def _story_unblocked_json(item: dict) -> dict:
    return {
        "id": item.get("id", ""),
        "type": item.get("type", "story"),
        "status": item.get("status", ""),
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "blocked_by": item.get("blocked_by", []),
    }


def _unblocked_to_json(stories: list[dict]) -> list[dict]:
    return [_story_unblocked_json(s) for s in stories]


def _print_unblocked_row(item: dict) -> None:
    print(
        f"  {item.get('id', ''):<8} {item.get('status', ''):<12} "
        f"{item.get('title', '')[:50]}"
    )


def _print_unblocked_list(stories: list[dict]) -> None:
    print(f"Unblocked items ({len(stories)}):")
    print("-" * 50)
    for item in stories:
        _print_unblocked_row(item)


def _promote_story(story: dict) -> int:
    if story.get("status") == "Backlog":
        story["status"] = "Ready"
        return 1
    return 0


def _promote_unblocked_in_place(unblocked_stories: list[dict]) -> int:
    return sum(_promote_story(s) for s in unblocked_stories)


# ---------------------------------------------------------------------------
# Add-story / add-task builders
# ---------------------------------------------------------------------------


def _new_story_defaults() -> dict:
    # Stories own GitHub-level dependencies — keep blocking arrays.
    return {
        "status": "Backlog",
        "is_blocking": [],
        "blocked_by": [],
        "acceptance_criteria": [],
    }


def _new_task_defaults() -> dict:
    # Tasks are local-only sub-items; no `is_blocking`/`blocked_by` since
    # they are decoupled from GitHub issues now.
    return {
        "status": "Backlog",
        "acceptance_criteria": [],
    }


def _build_new_story(
    new_id: str,
    *,
    type: str,
    title: str,
    description: str | None,
    points: int | None,
    priority: str | None,
    milestone: str | None,
    tdd: bool,
) -> dict:
    return {
        **_new_story_defaults(),
        "id": new_id,
        "type": type,
        "labels": [],
        "title": title,
        "description": description or "",
        "points": points or 0,
        "tdd": bool(tdd),
        "start_date": "",
        "target_date": "",
        "priority": priority or "P2",
        "milestone": milestone or "",
        "tasks": [],
    }


def _build_new_task(
    new_id: str,
    *,
    title: str,
    description: str | None,
    priority: str | None,
    complexity: str | None,
    labels: list[str] | None,
) -> dict:
    return {
        **_new_task_defaults(),
        "id": new_id,
        "type": "task",
        "labels": labels or [],
        "title": title,
        "description": description or "",
        "priority": priority or "P2",
        "complexity": complexity or "",
        "item_type": "task",
        "start_date": "",
        "target_date": "",
    }


# ---------------------------------------------------------------------------
# ProjectManager
# ---------------------------------------------------------------------------


class ProjectManager:
    """Manage a backlog (stories with nested tasks) stored in a single JSON file."""

    _COMMAND_MAP: dict[str, str] = {
        "list": "list_items",
        "ls": "list_items",
        "view": "view",
        "summary": "summary",
        "update": "update",
        "add-story": "add_story",
        "add-task": "add_task",
        "progress": "progress",
        "sync": "sync",
        "unblocked": "unblocked",
    }

    def __init__(self, backlog_path: Path | None = None) -> None:
        self.backlog_path = Path(backlog_path) if backlog_path else BACKLOG_PATH

    # -- dispatch ----------------------------------------------------------

    def run(self, command: str, **kwargs: Any) -> int:
        method_name = self._COMMAND_MAP.get(command)
        if method_name is None:
            raise ValueError(f"Unknown command: {command}")
        return getattr(self, method_name)(**kwargs)

    # -- I/O ---------------------------------------------------------------

    def load_backlog(self) -> dict:
        return _load_json(self.backlog_path, BACKLOG_DEFAULT)

    def save_backlog(self, data: dict) -> None:
        _save_json(data, self.backlog_path)

    def load_all_items(self) -> list[dict[str, Any]]:
        return _flatten_items(self.load_backlog())

    # -- list --------------------------------------------------------------

    def list_items(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        milestone: str | None = None,
        assignee: str | None = None,
        label: str | None = None,
        complexity: str | None = None,
        type: str | None = None,
        story: str | None = None,
        sort_by: str | None = None,
        reverse: bool = False,
        wide: bool = False,
        keys_only: bool = False,
        keys_format: str = "comma",
        json: bool = False,
    ) -> int:
        items = self.load_all_items()
        filters = _build_list_filters(
            status=status, priority=priority, milestone=milestone,
            assignee=assignee, label=label, complexity=complexity, type=type,
        )
        items = [t for t in items if _matches(t, filters)]
        items = _apply_story_filter(items, story)
        if sort_by:
            items.sort(key=lambda t: _sort_key(sort_by, t), reverse=reverse)
        return _list_output(items, wide, keys_only, keys_format, json)

    # -- view --------------------------------------------------------------

    def view(
        self,
        *,
        key: str,
        raw: bool = False,
        template: str | None = None,
        tasks: bool = False,
        ready_tasks: bool = False,
        ac: bool = False,
        tdd: bool = False,
        json: bool = False,
    ) -> int:
        items = self.load_all_items()
        task = _find_task(items, key)
        if not task:
            print(f"Task not found: {key}", file=sys.stderr)
            return 1
        return _dispatch_view(task, items, raw, template, tasks, ready_tasks, ac, tdd, json)

    # -- summary -----------------------------------------------------------

    def summary(self, *, group_by: str = "status") -> int:
        items = self.load_all_items()
        groups = _group_items(items, group_by)
        total_pts = _sum_points(items)
        print(f"Summary by {group_by}  ({len(items)} tasks, {total_pts} pts total)\n")
        _print_summary_rows(groups, group_by)
        return 0

    # -- add-story / add-task ---------------------------------------------

    def add_story(
        self,
        *,
        type: str,
        title: str,
        description: str | None = None,
        points: int | None = None,
        priority: str | None = None,
        milestone: str | None = None,
        tdd: bool = False,
    ) -> int:
        data = self.load_backlog()
        prefix = STORY_TYPE_PREFIXES.get(type, "TS")
        new_id = _next_id(prefix, [s.get("id", "") for s in data.get("stories", [])])
        story = _build_new_story(
            new_id, type=type, title=title, description=description,
            points=points, priority=priority, milestone=milestone, tdd=tdd,
        )
        data.setdefault("stories", []).append(story)
        self.save_backlog(data)
        print(f"Added story {new_id}: {title}")
        return 0

    def add_task(
        self,
        *,
        parent_story_id: str,
        title: str,
        description: str | None = None,
        priority: str | None = None,
        complexity: str | None = None,
        labels: list[str] | None = None,
    ) -> int:
        data = self.load_backlog()
        story = _find_story(data, parent_story_id)
        if story is None:
            print(f"Parent story not found: {parent_story_id}", file=sys.stderr)
            return 1
        new_id = _next_id("T", _all_task_ids(data))
        task = _build_new_task(
            new_id, title=title, description=description,
            priority=priority, complexity=complexity, labels=labels,
        )
        story.setdefault("tasks", []).append(task)
        self.save_backlog(data)
        print(f"Added task {new_id}: {title}")
        return 0

    # -- update ------------------------------------------------------------

    def update(
        self,
        *,
        key: str,
        status: str | None = None,
        priority: str | None = None,
        complexity: str | None = None,
        title: str | None = None,
        description: str | None = None,
        start_date: str | None = None,
        target_date: str | None = None,
        tdd: bool | None = None,
        force: bool = False,
    ) -> int:
        updates = _collect_updates(
            {"status": status, "priority": priority, "complexity": complexity,
             "title": title, "description": description, "start_date": start_date,
             "target_date": target_date, "tdd": tdd}
        )
        if not updates:
            print("Nothing to update. Use --help to see available options.", file=sys.stderr)
            return 1
        return self._apply_update(key, updates, force)

    def _apply_update(self, key: str, updates: dict, force: bool) -> int:
        data = self.load_backlog()
        story, task = _find_story_and_task(data, key)
        if task is not None:
            return self._commit_update(data, task, updates, force, key)
        if story is not None:
            return self._commit_update(data, story, updates, force, key)
        print(f"Item not found: {key}", file=sys.stderr)
        return 1

    def _commit_update(
        self, data: dict, item: dict, updates: dict, force: bool, key: str
    ) -> int:
        err = _check_status_transition(item, updates, force)
        if err:
            print(err, file=sys.stderr)
            return 1
        _apply_updates(item, updates)
        self.save_backlog(data)
        print(f"Updated {key}")
        return 0

    # -- progress ----------------------------------------------------------

    def progress(self) -> int:
        backlog = self.load_backlog()
        stories = backlog.get("stories", [])
        tasks = _all_tasks(backlog)
        _print_progress_overall(tasks, backlog)
        _print_status_distribution(tasks)
        if stories:
            _print_story_completion(stories)
            _print_per_story(stories)
        return 0

    # -- unblocked ---------------------------------------------------------

    def unblocked(
        self, *, story: str | None = None, promote: bool = False, json: bool = False
    ) -> int:
        backlog = self.load_backlog()
        stories = backlog.get("stories", [])
        status_by_id = _build_status_map_from_backlog(backlog)
        # Tasks are local-only now and never appear in unblocked output.
        unblocked_stories = _filter_unblocked_stories(stories, status_by_id, story)
        return self._render_unblocked(unblocked_stories, backlog, promote, json)

    def _render_unblocked(
        self,
        stories: list[dict],
        backlog: dict,
        promote: bool,
        as_json: bool,
    ) -> int:
        if not stories:
            print("No unblocked items found.")
            return 0
        if as_json:
            print(_json.dumps(_unblocked_to_json(stories), indent=2))
            return 0
        _print_unblocked_list(stories)
        if promote:
            promoted = _promote_unblocked_in_place(stories)
            self.save_backlog(backlog)
            print(f"\nPromoted {promoted} item(s) to Ready.")
        return 0

    # -- sync --------------------------------------------------------------

    def sync(
        self,
        *,
        dry_run: bool = False,
        delete_all: bool = False,
        repo: str | None = None,
        project: int | None = None,
        owner: str | None = None,
    ) -> int:
        from .sync import Syncer

        syncer = Syncer(
            backlog_path=self.backlog_path,
            repo=repo, project=project, owner=owner,
        )
        if delete_all:
            return syncer.run("delete-all", dry_run=dry_run)
        return syncer.run("sync", dry_run=dry_run)
