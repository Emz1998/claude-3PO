"""GitHub Projects sync library.

Exposes the :class:`Syncer` class plus stateless module-level helpers that
talk to the ``gh`` CLI. The CLI wrapper lives in ``project_manager.cli``.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .config import DATA_PATHS, OWNER, PROJECT_NUMBER, REPO
from .utils.gh_utils import gh_json, run

MAX_WORKERS = 8
BATCH_SIZE = 30

# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def issue_url(repo: str, number: int) -> str:
    return f"https://github.com/{repo}/issues/{number}"


def _item_full_title(item: dict[str, Any]) -> str:
    """Build the full issue title from id + title using colon format."""
    item_id = item.get("id")
    title = item["title"]
    return f"{item_id}: {title}" if item_id else title


def build_issue_body(item: dict[str, Any]) -> str:
    """Build issue body from description + acceptance_criteria checklist."""
    desc = item.get("description", "") or ""
    criteria = item.get("acceptance_criteria", []) or []
    parts: list[str] = []
    if desc:
        parts.append(desc)
    if criteria:
        checklist = "\n".join(f"- [ ] {ac}" for ac in criteria)
        parts.append(f"## Acceptance Criteria\n\n{checklist}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# GitHub ``gh`` command helpers
# ---------------------------------------------------------------------------


def ensure_label(label: str, repo: str) -> None:
    run(["gh", "label", "create", label, "--repo", repo, "--force"], check=False)


def _gh_issue_list(repo: str, state: str, limit: int = 500) -> list[dict[str, Any]]:
    out = run(
        [
            "gh", "issue", "list", "--repo", repo, "--state", state,
            "--json", "title,number", "--limit", str(limit),
        ],
        check=False,
    )
    return json.loads(out) if out else []


def fetch_all_open_issues(repo: str) -> dict[str, int]:
    """Fetch all open issues in one call. Returns {title: number} map."""
    return {issue["title"]: issue["number"] for issue in _gh_issue_list(repo, "open")}


def fetch_all_open_issues_full(repo: str) -> list[dict[str, Any]]:
    """Fetch all open issues with title and number."""
    return _gh_issue_list(repo, "open")


def find_existing_issue(repo: str, title: str) -> int | None:
    """Search for an open issue by exact title. Returns issue number if found."""
    out = run(
        [
            "gh", "issue", "list", "--repo", repo,
            "--search", f'"{title}" in:title', "--state", "open",
            "--json", "title,number",
        ],
        check=False,
    )
    if not out:
        return None
    for issue in json.loads(out):
        if issue.get("title") == title:
            return issue["number"]
    return None


def _get_issue_rest_id(repo: str, issue_num: int) -> int | None:
    """Get the REST API ID for an issue (different from issue number)."""
    out = run(
        ["gh", "api", f"repos/{repo}/issues/{issue_num}", "--jq", ".id"],
        check=False,
    )
    return int(out) if out else None


def _get_issue_node_id(repo: str, issue_num: int) -> str | None:
    """Get the GraphQL node ID for an issue."""
    out = run(
        ["gh", "api", f"repos/{repo}/issues/{issue_num}", "--jq", ".node_id"],
        check=False,
    )
    return out if out else None


def _fetch_all_issues(repo: str, state: str = "all") -> list[dict[str, Any]]:
    """Fetch issues by state (open, closed, all). Returns list of {title, number}."""
    if state == "all":
        return _gh_issue_list(repo, "open") + _gh_issue_list(repo, "closed")
    return _gh_issue_list(repo, state)


# ---------------------------------------------------------------------------
# Flat data load / save
# ---------------------------------------------------------------------------


def _build_metadata(backlog: dict) -> dict:
    return {
        "goal": backlog.get("goal", ""),
        "dates": backlog.get("dates", {}),
        "project": backlog.get("project", ""),
        "totalPoints": backlog.get("totalPoints"),
    }


def _tag_story(story: dict) -> dict:
    story["item_type"] = "story"
    return story


def _tag_tasks_in_story(story: dict) -> list[dict]:
    tasks: list[dict] = []
    for task in story.get("tasks", []):
        task["item_type"] = "task"
        task["parent_story_id"] = story.get("id", "")
        if not task.get("milestone"):
            task["milestone"] = story.get("milestone", "")
        tasks.append(task)
    return tasks


def load_flat_data(
    backlog_path: Path,
) -> tuple[list[dict], list[dict], dict, dict[str, Any]]:
    """Load the backlog file.

    Returns ``(stories, tasks, metadata, backlog_data)``. Tasks are flattened
    from nested ``story.tasks`` and tagged with ``parent_story_id``.
    """
    backlog_data = json.loads(backlog_path.read_text(encoding="utf-8"))
    metadata = _build_metadata(backlog_data)
    stories: list[dict] = []
    tasks: list[dict] = []
    for story in backlog_data.get("stories", []):
        stories.append(_tag_story(story))
        tasks.extend(_tag_tasks_in_story(story))
    return stories, tasks, metadata, backlog_data


def build_id_to_issue_number_map(
    stories: list[dict], tasks: list[dict]
) -> dict[str, int]:
    """Build {id: issue_number} map for all items that have an issue_number."""
    id_map: dict[str, int] = {}
    for item in stories + tasks:
        if item.get("issue_number"):
            id_map[item["id"]] = item["issue_number"]
    return id_map


def _apply_issue_numbers(bucket: list[dict], id_to_num: dict[str, int]) -> None:
    for entry in bucket:
        if entry["id"] in id_to_num:
            entry["issue_number"] = id_to_num[entry["id"]]


def save_flat_data(
    stories: list[dict],
    tasks: list[dict],
    backlog_path: Path,
    backlog_data: dict[str, Any],
) -> None:
    """Write updated issue_number values back into the backlog file."""
    id_to_num = build_id_to_issue_number_map(stories, tasks)
    for story in backlog_data.get("stories", []):
        if story["id"] in id_to_num:
            story["issue_number"] = id_to_num[story["id"]]
        _apply_issue_numbers(story.get("tasks", []), id_to_num)
    backlog_path.write_text(json.dumps(backlog_data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Blocking relationships
# ---------------------------------------------------------------------------


def _collect_blocking_pairs(
    items: list[dict], id_map: dict[str, int]
) -> tuple[list[tuple[int, int, str, str]], set[int]]:
    pairs: list[tuple[int, int, str, str]] = []
    involved: set[int] = set()
    for item in items:
        item_num = item.get("issue_number")
        if not item_num:
            continue
        for blocker_id in item.get("blocked_by", []):
            blocker_num = id_map.get(blocker_id)
            if blocker_num:
                pairs.append((item_num, blocker_num, item.get("id", ""), blocker_id))
                involved.update({item_num, blocker_num})
    return pairs, involved


def _fetch_node_ids(repo: str, issue_nums: set[int]) -> dict[int, str]:
    """Batched node-ID lookup via a single GraphQL query (instead of N REST calls)."""
    nums = sorted(set(issue_nums))
    if not nums:
        return {}
    owner, name = repo.split("/", 1)
    aliases = " ".join(f"i{n}: issue(number: {n}) {{ id number }}" for n in nums)
    query = f'{{ repository(owner: "{owner}", name: "{name}") {{ {aliases} }} }}'
    result = gh_json(["gh", "api", "graphql", "-f", f"query={query}"])
    repo_data = (result or {}).get("data", {}).get("repository") or {}
    out: dict[int, str] = {}
    for val in repo_data.values():
        if val and val.get("id"):
            out[val["number"]] = val["id"]
    return out


def _add_blocked_by(blocked_node: str, blocker_node: str) -> None:
    mutation = f"""
    mutation {{
      addBlockedBy(input: {{
        issueId: {json.dumps(blocked_node)},
        blockingIssueId: {json.dumps(blocker_node)}
      }}) {{
        issue {{ number }}
        blockingIssue {{ number }}
      }}
    }}
    """
    run(["gh", "api", "graphql", "-f", f"query={mutation}"], check=False)


def _apply_blocking_pair(
    num_to_node: dict[int, str],
    blocked_num: int,
    blocker_num: int,
    blocked_id: str,
    blocker_id: str,
) -> None:
    blocked_node = num_to_node.get(blocked_num)
    blocker_node = num_to_node.get(blocker_num)
    if not blocked_node or not blocker_node:
        print(f"  ⚠ Missing node ID for #{blocked_num} or #{blocker_num}")
        return
    print(f"  #{blocked_num} ({blocked_id}) blocked by #{blocker_num} ({blocker_id})")
    _add_blocked_by(blocked_node, blocker_node)


def set_blocking_relationships(
    repo: str, items: list[dict], id_map: dict[str, int]
) -> None:
    """Set blocking relationships via GitHub's ``addBlockedBy`` GraphQL mutation."""
    pairs, involved = _collect_blocking_pairs(items, id_map)
    if not pairs:
        print("  No blocking relationships to set.")
        return
    print(f"  Fetching node IDs for {len(involved)} issues...")
    num_to_node = _fetch_node_ids(repo, involved)
    for blocked_num, blocker_num, blocked_id, blocker_id in pairs:
        _apply_blocking_pair(num_to_node, blocked_num, blocker_num, blocked_id, blocker_id)


# ---------------------------------------------------------------------------
# Project field creation
# ---------------------------------------------------------------------------


def _create_project_field_mutation(project_id: str, field_name: str, inner: str) -> str:
    return f"""
    mutation {{
      createProjectV2Field(input: {{
        projectId: {json.dumps(project_id)},
        {inner},
        name: {json.dumps(field_name)}
      }}) {{
        projectV2Field {{ ... on ProjectV2Field {{ id }} }}
      }}
    }}
    """


def _create_single_select_field(project_id: str, field_name: str, options: list[str]) -> None:
    options_str = ", ".join(
        f'{{name: {json.dumps(opt)}, color: GRAY, description: ""}}' for opt in options
    )
    mutation = (
        f"mutation {{ createProjectV2Field(input: {{"
        f"projectId: {json.dumps(project_id)},"
        f" dataType: SINGLE_SELECT,"
        f" name: {json.dumps(field_name)},"
        f" singleSelectOptions: [{options_str}]"
        f"}}) {{ projectV2Field {{ ... on ProjectV2SingleSelectField {{ id }} }} }} }}"
    )
    run(["gh", "api", "graphql", "-f", f"query={mutation}"], check=False)


def _create_simple_field(project_id: str, field_name: str, data_type: str) -> None:
    mutation = _create_project_field_mutation(project_id, field_name, f"dataType: {data_type}")
    run(["gh", "api", "graphql", "-f", f"query={mutation}"], check=False)


def ensure_project_field(
    project_id: str,
    field_name: str,
    field_type: str,
    field_map: dict[str, dict],
    options: list[str] | None = None,
) -> bool:
    """Create a project field if it doesn't exist. Returns True if created."""
    if field_name in field_map:
        return False
    print(f"  Creating missing field: {field_name} ({field_type})")
    if field_type == "SINGLE_SELECT" and options:
        _create_single_select_field(project_id, field_name, options)
    elif field_type in ("NUMBER", "TEXT"):
        _create_simple_field(project_id, field_name, field_type)
    return True


# ---------------------------------------------------------------------------
# Issue creation / resolution
# ---------------------------------------------------------------------------


def resolve_existing_issues(
    tasks: list[dict[str, Any]], existing_issues: dict[str, int]
) -> list[dict[str, Any]]:
    """Return tasks that still need a new issue created."""
    needs_creation: list[dict[str, Any]] = []
    for t in tasks:
        if t.get("issue_number"):
            print(f"  ↳ Already has issue: #{t['issue_number']}")
            continue
        full_title = _item_full_title(t)
        if full_title in existing_issues:
            t["issue_number"] = existing_issues[full_title]
            print(f"  ↳ Found existing issue: #{t['issue_number']} ({full_title})")
        else:
            needs_creation.append(t)
    return needs_creation


_create_lock = threading.Lock()
_created_titles: set[str] = set()


def _claim_title(full_title: str) -> None:
    with _create_lock:
        if full_title in _created_titles:
            raise RuntimeError(f"Duplicate title detected, skipping: {full_title}")
        _created_titles.add(full_title)


def _task_labels(task: dict[str, Any]) -> list[str]:
    """Return lowercase labels for an item, appending its ``type`` if missing.

    GitHub label uniqueness is case-insensitive; lowercase avoids
    ``gh issue create --label Spike`` failing when a ``spike`` already exists.
    """
    labels = [str(lab).lower() for lab in (task.get("labels") or [])]
    item_type = str(task.get("type", "")).lower()
    if item_type and item_type not in labels:
        labels.append(item_type)
    return labels


def _build_create_issue_cmd(
    repo: str, title: str, body: str, labels: list[str], assignees: list[str]
) -> list[str]:
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for lab in labels:
        cmd += ["--label", lab]
    for a in assignees:
        cmd += ["--assignee", a]
    return cmd


def _create_issue(task: dict[str, Any], repo: str) -> int:
    """Create a single issue. Returns issue number. Thread-safe with dedup guard."""
    full_title = _item_full_title(task)
    _claim_title(full_title)
    labels = _task_labels(task)
    for lab in labels:
        ensure_label(lab, repo)
    cmd = _build_create_issue_cmd(
        repo, full_title, build_issue_body(task), labels, task.get("assignees") or []
    )
    url = run(cmd).strip()
    if not url:
        raise RuntimeError(f"gh issue create returned no URL for: {full_title}")
    number = int(url.rstrip("/").split("/")[-1])
    task["issue_number"] = number
    return number


def ensure_issue(
    task: dict[str, Any], repo: str, existing_issues: dict[str, int] | None = None
) -> int:
    """Ensure an issue exists. Returns issue number."""
    if task.get("issue_number"):
        return task["issue_number"]
    full_title = _item_full_title(task)
    if existing_issues and full_title in existing_issues:
        num = existing_issues[full_title]
        print(f"  ↳ Found existing issue: #{num}")
        task["issue_number"] = num
        return num
    existing = find_existing_issue(repo, full_title)
    if existing:
        print(f"  ↳ Found existing issue: #{existing}")
        task["issue_number"] = existing
        return existing
    return _create_issue(task, repo)


def add_to_project(project_number: int, owner: str, url: str) -> None:
    p = subprocess.run(
        [
            "gh", "project", "item-add", str(project_number),
            "--owner", owner, "--url", url,
        ],
        text=True,
        capture_output=True,
    )
    if p.returncode != 0:
        print(f"  ⚠ item-add failed for {url}: {p.stderr.strip()}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------


_PROJECT_ID_QUERY = """
query($owner: String!, $number: Int!) {
  user(login: $owner) {
    projectV2(number: $number) { id }
  }
}
"""


def get_project_id(project_number: int, owner: str) -> str:
    """Get the project node ID via GraphQL."""
    result = gh_json(
        [
            "gh", "api", "graphql",
            "-f", f"query={_PROJECT_ID_QUERY}", "-f", f"owner={owner}",
            "-F", f"number={project_number}",
        ]
    )
    return result["data"]["user"]["projectV2"]["id"]


def get_project_fields(project_number: int, owner: str) -> list[dict]:
    """Get all project fields with their IDs and options."""
    return gh_json(
        [
            "gh", "project", "field-list", str(project_number),
            "--owner", owner, "--format", "json",
        ]
    ).get("fields", [])


def get_project_items(project_number: int, owner: str) -> list[dict]:
    """Get all project items."""
    return gh_json(
        [
            "gh", "project", "item-list", str(project_number),
            "--owner", owner, "--format", "json", "--limit", "200",
        ]
    ).get("items", [])


def _project_issues(project_number: int, owner: str) -> list[dict[str, Any]]:
    """Return ``[{title, number}]`` for every issue attached to the project."""
    items = get_project_items(project_number, owner)
    result: list[dict[str, Any]] = []
    for it in items:
        content = it.get("content") or {}
        number = content.get("number")
        if number:
            result.append({"title": content.get("title", ""), "number": number})
    return result


def build_field_map(fields: list[dict]) -> dict[str, dict]:
    """Build a lookup: ``field_name -> {id, type, options: {option_name: option_id}}``."""
    fmap: dict[str, dict] = {}
    for f in fields:
        entry: dict[str, Any] = {"id": f["id"], "type": f.get("type", "")}
        if "options" in f:
            entry["options"] = {opt["name"]: opt["id"] for opt in f["options"]}
        fmap[f.get("name", "")] = entry
    return fmap


def find_item_id(items: list[dict], number: int) -> str | None:
    """Find the project item ID that matches the given issue number."""
    for item in items:
        if item.get("content", {}).get("number") == number:
            return item["id"]
    return None


# ---------------------------------------------------------------------------
# Field value / mutation helpers
# ---------------------------------------------------------------------------


def _looks_like_date(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-"
    )


def _value_flag(value: Any) -> tuple[str, str] | None:
    if isinstance(value, (int, float)):
        return "--number", str(value)
    if _looks_like_date(value):
        return "--date", value
    if isinstance(value, str):
        return "--text", str(value)
    return None


def _append_value_flag(cmd: list[str], field_name: str, value: Any) -> bool:
    flag = _value_flag(value)
    if flag is None:
        print(f"  ⚠ Unsupported value type for '{field_name}': {type(value)}", file=sys.stderr)
        return False
    cmd += list(flag)
    return True


def _append_option_flag(
    cmd: list[str], field_name: str, options: dict[str, str], value: Any
) -> bool:
    option_id = options.get(value)
    if not option_id:
        print(
            f"  ⚠ Option '{value}' not found for field '{field_name}'. "
            f"Available: {list(options.keys())}",
            file=sys.stderr,
        )
        return False
    cmd += ["--single-select-option-id", option_id]
    return True


def _item_edit_cmd(project_id: str, item_id: str, field_id: str) -> list[str]:
    return [
        "gh", "project", "item-edit", "--id", item_id,
        "--field-id", field_id, "--project-id", project_id,
    ]


def set_field(
    project_id: str,
    item_id: str,
    field_map: dict[str, dict],
    field_name: str,
    value: Any,
) -> None:
    """Set a project field value using the correct flags for its type."""
    if value is None or value == "":
        return
    field = field_map.get(field_name)
    if not field:
        print(f"  ⚠ Field '{field_name}' not found in project", file=sys.stderr)
        return
    cmd = _item_edit_cmd(project_id, item_id, field["id"])
    ok = (
        _append_option_flag(cmd, field_name, field["options"], value)
        if field.get("options")
        else _append_value_flag(cmd, field_name, value)
    )
    if ok:
        run(cmd, check=False)


def _gql_value(
    field_map: dict[str, dict], field_name: str, value: Any
) -> dict[str, str] | None:
    if isinstance(value, (int, float)):
        return {"number": str(value)}
    if _looks_like_date(value):
        return {"date": json.dumps(value)}
    if isinstance(value, str):
        return {"text": json.dumps(value)}
    print(f"  ⚠ Unsupported value type for '{field_name}': {type(value)}", file=sys.stderr)
    return None


def _gql_option_value(
    options: dict[str, str], field_name: str, value: Any
) -> dict[str, str] | None:
    option_id = options.get(value)
    if not option_id:
        print(
            f"  ⚠ Option '{value}' not found for field '{field_name}'. "
            f"Available: {list(options.keys())}",
            file=sys.stderr,
        )
        return None
    return {"singleSelectOptionId": json.dumps(option_id)}


def _build_field_value(
    field_map: dict[str, dict], field_name: str, value: Any
) -> dict[str, str] | None:
    """Convert a field name + value into the GraphQL ``value`` input object."""
    if value is None or value == "":
        return None
    field = field_map.get(field_name)
    if not field:
        print(f"  ⚠ Field '{field_name}' not found in project", file=sys.stderr)
        return None
    if field.get("options"):
        return _gql_option_value(field["options"], field_name, value)
    return _gql_value(field_map, field_name, value)


_BASE_FIELD_SPECS: list[tuple[str, str]] = [
    ("Status", "status"),
    ("Priority", "priority"),
    ("Start date", "start_date"),
    ("Target date", "target_date"),
]


def _field_specs_for_item(item: dict[str, Any]) -> list[tuple[str, str]]:
    specs = list(_BASE_FIELD_SPECS)
    specs.append(("Points", "points") if item.get("item_type") == "story" else ("Complexity", "complexity"))
    return specs


def _mutation_for_field(
    project_id: str, item_id: str, field_id: str, gql_value: dict[str, str], idx: int
) -> str:
    value_parts = ", ".join(f"{k}: {v}" for k, v in gql_value.items())
    return (
        f"m{idx}: updateProjectV2ItemFieldValue(input: {{"
        f"projectId: {json.dumps(project_id)}, "
        f"itemId: {json.dumps(item_id)}, "
        f"fieldId: {json.dumps(field_id)}, "
        f"value: {{{value_parts}}}"
        f"}}) {{ projectV2Item {{ id }} }}"
    )


def _mutations_for_item(
    task: dict[str, Any],
    item_id: str,
    project_id: str,
    field_map: dict[str, dict],
    start_idx: int,
) -> tuple[list[str], int]:
    mutations: list[str] = []
    idx = start_idx
    for field_name, task_key in _field_specs_for_item(task):
        raw = task.get(task_key)
        field = field_map.get(field_name)
        if not field or raw is None or raw == "":
            continue
        gql = _build_field_value(field_map, field_name, raw)
        if gql is None:
            continue
        mutations.append(_mutation_for_field(project_id, item_id, field["id"], gql, idx))
        idx += 1
    return mutations, idx


def _collect_mutations(
    tasks: list[dict[str, Any]],
    items: list[dict],
    project_id: str,
    field_map: dict[str, dict],
) -> list[str]:
    """Build GraphQL mutation aliases for all tasks with known project items."""
    mutations: list[str] = []
    idx = 0
    for t in tasks:
        item_id = find_item_id(items, t["issue_number"])
        if not item_id:
            print(
                f"  ⚠ Could not find item ID for #{t['issue_number']}, skipping fields",
                file=sys.stderr,
            )
            continue
        new_mutations, idx = _mutations_for_item(t, item_id, project_id, field_map, idx)
        mutations.extend(new_mutations)
    return mutations


def _log_batch_errors(stdout: str) -> None:
    if not stdout:
        return
    try:
        resp = json.loads(stdout)
    except json.JSONDecodeError:
        return
    for err in resp.get("errors", []):
        print(f"    GraphQL error: {err.get('message', err)}", file=sys.stderr)


def _run_mutation_batch(batch: list[str], batch_num: int, batch_total: int) -> None:
    body = "mutation {\n  " + "\n  ".join(batch) + "\n}"
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={body}"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(
            f"  ⚠ Batch {batch_num}/{batch_total} failed: {result.stderr.strip()}",
            file=sys.stderr,
        )
        _log_batch_errors(result.stdout)
    else:
        print(f"  ✓ Batch {batch_num}/{batch_total} ({len(batch)} mutations)")


def execute_batched_mutations(mutations: list[str]) -> None:
    """Send mutations in batches using ``gh api graphql``."""
    total = len(mutations)
    if total == 0:
        print("  No field updates to send.")
        return
    print(f"  Sending {total} field updates in batches of {BATCH_SIZE}...")
    batch_total = (total + BATCH_SIZE - 1) // BATCH_SIZE
    for start in range(0, total, BATCH_SIZE):
        _run_mutation_batch(mutations[start : start + BATCH_SIZE], start // BATCH_SIZE + 1, batch_total)


# ---------------------------------------------------------------------------
# Milestones / parent-child / branches
# ---------------------------------------------------------------------------


def ensure_milestone(repo: str, milestone: str) -> None:
    """Create a milestone if it doesn't already exist."""
    if not milestone:
        return
    run(
        [
            "gh", "api", f"repos/{repo}/milestones",
            "-f", f"title={milestone}", "-f", "state=open",
        ],
        check=False,
    )


def set_milestone(repo: str, issue_num: int, milestone: str) -> None:
    """Set the milestone on an issue via ``gh issue edit``."""
    if not milestone:
        return
    ensure_milestone(repo, milestone)
    run(
        ["gh", "issue", "edit", str(issue_num), "--repo", repo, "--milestone", milestone],
        check=False,
    )


def set_parent_issue(repo: str, child_num: int, parent_num: int | str) -> None:
    """Set a parent-child relationship between issues (sub-issues)."""
    if not parent_num:
        return
    child_rest_id = _get_issue_rest_id(repo, child_num)
    if not child_rest_id:
        print(f"  ⚠ Could not get REST ID for #{child_num}", file=sys.stderr)
        return
    run(
        [
            "gh", "api", f"repos/{repo}/issues/{parent_num}/sub_issues",
            "-F", f"sub_issue_id={child_rest_id}", "--method", "POST",
        ],
        check=False,
    )


def create_branch_for_issue(repo: str, issue_num: int, branch_name: str) -> str | None:
    """Create a branch linked to an issue via ``gh issue develop``."""
    if not branch_name:
        return None
    run(
        [
            "gh", "issue", "develop", str(issue_num), "--repo", repo,
            "--name", branch_name, "--base", "main",
        ],
        check=False,
    )
    return branch_name


# ---------------------------------------------------------------------------
# Pass 2: field updates + issue-level edits
# ---------------------------------------------------------------------------


def _issue_level_edit(task: dict[str, Any], repo: str) -> None:
    num = task["issue_number"]
    milestone = task.get("milestone") or ""
    if milestone:
        run(
            [
                "gh", "issue", "edit", str(num), "--repo", repo,
                "--milestone", milestone,
            ],
            check=False,
        )
    set_parent_issue(repo, num, task.get("parent_issue") or "")
    create_branch_for_issue(repo, num, task.get("branch") or "")


def _apply_issue_level_parallel(tasks: list[dict[str, Any]], repo: str) -> None:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_issue_level_edit, t, repo): t for t in tasks}
        for fut in as_completed(futures):
            t = futures[fut]
            fut.result()
            status = t.get("status") or "no status"
            print(f"  ✓ {t.get('id', '')} {t['title']} [{status}]")


def run_pass2_batched(
    tasks: list[dict[str, Any]],
    items: list[dict],
    project_id: str,
    field_map: dict[str, dict],
    repo: str,
) -> None:
    """Pass 2: batched GraphQL field updates, then parallel issue-level edits."""
    execute_batched_mutations(_collect_mutations(tasks, items, project_id, field_map))
    for ms in {t["milestone"] for t in tasks if t.get("milestone")}:
        ensure_milestone(repo, ms)
    print("  Setting issue-level fields (parallel)...")
    _apply_issue_level_parallel(tasks, repo)


# ---------------------------------------------------------------------------
# Delete workflow
# ---------------------------------------------------------------------------


def _close_issue(repo: str, issue_num: int) -> None:
    """Close a single issue."""
    run(["gh", "issue", "close", str(issue_num), "--repo", repo], check=False)


def _delete_issue(repo: str, issue_num: int) -> None:
    """Permanently delete an issue via GraphQL ``deleteIssue`` mutation."""
    node_id = _get_issue_node_id(repo, issue_num)
    if not node_id:
        print(f"  ⚠ Could not get node ID for #{issue_num}", file=sys.stderr)
        return
    mutation = f'mutation {{ deleteIssue(input: {{issueId: "{node_id}"}}) {{ clientMutationId }} }}'
    run(["gh", "api", "graphql", "-f", f"query={mutation}"], check=False)


def _delete_branch(repo: str, branch_name: str) -> None:
    """Delete a remote branch."""
    run(
        [
            "gh", "api", f"repos/{repo}/git/refs/heads/{branch_name}",
            "--method", "DELETE",
        ],
        check=False,
    )


def _remove_from_project(project_number: int, owner: str, item_id: str) -> None:
    """Remove an item from the project."""
    run(
        [
            "gh", "project", "item-delete", str(project_number),
            "--owner", owner, "--id", item_id,
        ],
        check=False,
    )


def _branches_for_issues(
    issues: list[dict[str, Any]], items: list[dict]
) -> list[str]:
    branch_by_title: dict[str, str] = {}
    for item in items:
        if item.get("branch"):
            branch_by_title[_item_full_title(item)] = item["branch"]
    return [branch_by_title[i["title"]] for i in issues if i["title"] in branch_by_title]


def _print_delete_dry_run(issues: list[dict], branches: list[str]) -> None:
    for issue in issues:
        print(f"  [dry-run] Would delete #{issue['number']}: {issue['title']}")
    for b in branches:
        print(f"  [dry-run] Would delete branch: {b}")


def _delete_branches_parallel(repo: str, branches: list[str]) -> None:
    if not branches:
        return
    print(f"\nDeleting {len(branches)} branches (parallel)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_delete_branch, repo, b): b for b in branches}
        for fut in as_completed(futures):
            b = futures[fut]
            fut.result()
            print(f"  ✗ Deleted branch: {b}")


def _remove_issues_from_project(
    project_number: int, owner: str, issues: list[dict[str, Any]]
) -> None:
    print("\nRemoving from project...")
    items = get_project_items(project_number, owner)
    to_remove = [(iss, find_item_id(items, iss["number"])) for iss in issues]
    to_remove = [(iss, item_id) for iss, item_id in to_remove if item_id]
    if not to_remove:
        return
    # Serialized: GitHub secondary rate limits penalize concurrent project mutations.
    for iss, item_id in to_remove:
        _remove_from_project(project_number, owner, item_id)
        print(f"  ✗ Removed #{iss['number']} from project")


def _delete_issues_parallel(repo: str, issues: list[dict[str, Any]]) -> None:
    print(f"\nDeleting {len(issues)} issues permanently...")
    # Serialized: avoid GitHub secondary rate limits on content-deleting mutations.
    for iss in issues:
        _delete_issue(repo, iss["number"])
        print(f"  ✗ Deleted #{iss['number']}: {iss['title']}")


def _clear_issue_numbers(backlog_data: dict[str, Any], backlog_path: Path) -> None:
    for story in backlog_data.get("stories", []):
        story.pop("issue_number", None)
        for task in story.get("tasks", []):
            task.pop("issue_number", None)
    backlog_path.write_text(json.dumps(backlog_data, indent=2), encoding="utf-8")
    print(f"\nCleared issue numbers from {backlog_path}")


# ---------------------------------------------------------------------------
# Sync workflow helpers
# ---------------------------------------------------------------------------


def _apply_sync_scope(
    stories: list[dict], tasks: list[dict], scope: str
) -> tuple[list[dict], list[dict]]:
    if scope == "stories":
        return stories, []
    if scope == "tasks":
        return [], tasks
    return stories, tasks


def _ensure_titles_present(items: list[dict], label: str) -> None:
    for t in items:
        if "title" not in t:
            raise ValueError(f"Item missing 'title': {t}")


def _pre_create_labels(items: list[dict], repo: str) -> None:
    """Ensure all labels exist before we fan out parallel issue creates."""
    unique: set[str] = set()
    for t in items:
        unique.update(_task_labels(t))
    for lab in sorted(unique):
        ensure_label(lab, repo)


def _create_missing_in_parallel(items: list[dict], repo: str, label: str) -> None:
    print(f"\nPass 1b: Creating {len(items)} new {label} (parallel)...")
    _pre_create_labels(items, repo)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_create_issue, t, repo): t for t in items}
        for fut in as_completed(futures):
            t = futures[fut]
            num = fut.result()
            print(f"  + {t.get('id','')} {t['title']} -> #{num}")


def _resolve_or_create(
    items: list[dict], existing_issues: dict[str, int], repo: str, label: str
) -> bool:
    print(f"\nPass 1a: Resolving existing {label}...")
    _ensure_titles_present(items, label)
    needs_creation = resolve_existing_issues(items, existing_issues)
    if needs_creation:
        _create_missing_in_parallel(needs_creation, repo, label)
        return True
    print(f"  All {label} already have issues.")
    return False


def _add_all_to_project_parallel(
    all_items: list[dict], project: int, owner: str, repo: str
) -> None:
    print("\nAdding issues to project...")
    # Serialized: GitHub secondary rate limits penalize concurrent project mutations.
    for t in all_items:
        add_to_project(project, owner, issue_url(repo, t["issue_number"]))
    print(f"  ✓ {len(all_items)} items added/verified")


def _fetch_rest_ids_parallel(repo: str, issue_nums: list[int]) -> dict[int, int]:
    """Parallel REST-ID lookups (reads only — safe to fan out)."""
    nums = list({n for n in issue_nums if n})
    if not nums:
        return {}
    result: dict[int, int] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_get_issue_rest_id, repo, n): n for n in nums}
        for fut in as_completed(futures):
            rid = fut.result()
            if rid:
                result[futures[fut]] = rid
    return result


def _post_sub_issue(repo: str, parent_num: int | str, child_rest_id: int) -> None:
    run(
        [
            "gh", "api", f"repos/{repo}/issues/{parent_num}/sub_issues",
            "-F", f"sub_issue_id={child_rest_id}", "--method", "POST",
        ],
        check=False,
    )


def _apply_parent_child(
    tasks: list[dict], id_map: dict[str, int], repo: str
) -> None:
    print("\nPass 3: Setting parent-child relationships...")
    pending = [
        (t, id_map[t["parent_story_id"]])
        for t in tasks
        if t.get("parent_story_id") and t.get("issue_number")
        and id_map.get(t.get("parent_story_id"))
    ]
    rest_ids = _fetch_rest_ids_parallel(repo, [t["issue_number"] for t, _ in pending])
    for task, parent_num in pending:
        _commit_sub_issue(repo, task, parent_num, rest_ids)


def _commit_sub_issue(
    repo: str, task: dict, parent_num: int, rest_ids: dict[int, int]
) -> None:
    child_num = task["issue_number"]
    rid = rest_ids.get(child_num)
    if rid is None:
        print(f"  ⚠ Could not get REST ID for #{child_num}", file=sys.stderr)
        return
    print(
        f"  Setting #{child_num} ({task['id']}) as sub-issue of "
        f"#{parent_num} ({task['parent_story_id']})"
    )
    _post_sub_issue(repo, parent_num, rid)


def _writeback_numbers(
    stories: list[dict],
    tasks: list[dict],
    backlog_data: dict[str, Any],
    backlog_path: Path,
) -> None:
    save_flat_data(stories, tasks, backlog_path, backlog_data)
    print(f"\nUpdated: {backlog_path}")


_REQUIRED_FIELDS: list[tuple[str, str, list[str] | None]] = [
    ("Points", "NUMBER", None),
    ("Complexity", "SINGLE_SELECT", ["XS", "S", "M", "L", "XL"]),
]


# ---------------------------------------------------------------------------
# Syncer
# ---------------------------------------------------------------------------


class Syncer:
    """Orchestrates syncing sprint/stories JSON files to GitHub Projects."""

    _MODE_MAP: dict[str, str] = {
        "sync": "sync",
        "delete-all": "delete_all",
        "delete_all": "delete_all",
    }

    def __init__(
        self,
        *,
        backlog_path: Path | None = None,
        repo: str | None = None,
        project: int | None = None,
        owner: str | None = None,
    ) -> None:
        self.backlog_path = Path(backlog_path or DATA_PATHS["backlog"])
        self.repo = repo or REPO
        self.project = project or PROJECT_NUMBER
        self.owner = owner or OWNER

    def run(self, mode: str, **kwargs: Any) -> int:
        method_name = self._MODE_MAP.get(mode)
        if method_name is None:
            raise ValueError(f"Unknown sync mode: {mode}")
        return getattr(self, method_name)(**kwargs)

    def sync(self, *, dry_run: bool = False, sync_scope: str = "all") -> int:
        stories, tasks, _, backlog_data = load_flat_data(self.backlog_path)
        stories, tasks = _apply_sync_scope(stories, tasks, sync_scope)
        print(f"Sync mode: {sync_scope} ({len(stories)} stories, {len(tasks)} tasks)")
        all_items = stories + tasks
        project_id, field_map = self._fetch_project_metadata()
        changed = self._ensure_all_issues(stories, tasks)
        self._run_remote_passes(stories, tasks, all_items, project_id, field_map, backlog_data)
        self._maybe_writeback(stories, tasks, backlog_data, changed, dry_run)
        return 0

    def _maybe_writeback(
        self,
        stories: list[dict],
        tasks: list[dict],
        backlog_data: dict,
        changed: bool,
        dry_run: bool,
    ) -> None:
        if not changed or dry_run:
            return
        _writeback_numbers(stories, tasks, backlog_data, self.backlog_path)

    def delete_all(self, *, dry_run: bool = False) -> int:
        stories, tasks, _, backlog_data = load_flat_data(self.backlog_path)
        print(f"Fetching issues currently in project {self.project}...")
        issues = _project_issues(self.project, self.owner)
        if not issues:
            print("No issues found in the project.")
            return 0
        print(f"Found {len(issues)} project issue(s) to delete.")
        branches = _branches_for_issues(issues, stories + tasks)
        if dry_run:
            _print_delete_dry_run(issues, branches)
            return 0
        self._perform_delete(issues, branches, backlog_data)
        return 0

    def _perform_delete(
        self, issues: list[dict], branches: list[str], backlog_data: dict
    ) -> None:
        _delete_branches_parallel(self.repo, branches)
        _remove_issues_from_project(self.project, self.owner, issues)
        _delete_issues_parallel(self.repo, issues)
        _clear_issue_numbers(backlog_data, self.backlog_path)

    def _fetch_project_metadata(self) -> tuple[str, dict[str, dict]]:
        print("Fetching project metadata...")
        project_id = get_project_id(self.project, self.owner)
        fields = get_project_fields(self.project, self.owner)
        field_map = build_field_map(fields)
        print(f"  Project ID: {project_id}")
        print(f"  Fields: {list(field_map.keys())}")
        if self._ensure_required_fields(project_id, field_map):
            field_map = build_field_map(get_project_fields(self.project, self.owner))
            print(f"  Fields: {list(field_map.keys())}")
        return project_id, field_map

    def _ensure_required_fields(self, project_id: str, field_map: dict[str, dict]) -> bool:
        created = False
        for fname, ftype, foptions in _REQUIRED_FIELDS:
            if ensure_project_field(project_id, fname, ftype, field_map, foptions):
                created = True
        if created:
            print("  Re-fetching fields after creation...")
        return created

    def _ensure_all_issues(self, stories: list[dict], tasks: list[dict]) -> bool:
        print("\nFetching existing issues...")
        existing = fetch_all_open_issues(self.repo)
        print(f"  Found {len(existing)} open issues")
        changed = False
        for label, items in [("stories", stories), ("tasks", tasks)]:
            if _resolve_or_create(items, existing, self.repo, label):
                changed = True
        return changed

    def _run_remote_passes(
        self,
        stories: list[dict],
        tasks: list[dict],
        all_items: list[dict],
        project_id: str,
        field_map: dict[str, dict],
        backlog_data: dict,
    ) -> None:
        _add_all_to_project_parallel(all_items, self.project, self.owner, self.repo)
        print("\nFetching project items...")
        items = get_project_items(self.project, self.owner)
        print(f"  Found {len(items)} items in project")
        print("\nPass 2: Setting project fields (batched GraphQL)...")
        run_pass2_batched(all_items, items, project_id, field_map, self.repo)
        # Build the id->issue_number map from in-memory items (disk isn't
        # written back until the end of sync, so reading the file here
        # would miss newly created numbers).
        full_id_map = build_id_to_issue_number_map(stories, tasks)
        _apply_parent_child(tasks, full_id_map, self.repo)
        print("\nPass 4: Setting blocking relationships...")
        set_blocking_relationships(self.repo, all_items, full_id_map)
