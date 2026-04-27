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
    # `milestone` is included so the caller can diff each issue's
    # current milestone against the in-memory value and skip a
    # redundant `gh issue edit` subprocess in Pass 2.
    out = run(
        [
            "gh", "issue", "list", "--repo", repo, "--state", state,
            "--json", "title,number,milestone", "--limit", str(limit),
        ],
        check=False,
    )
    return json.loads(out) if out else []


def fetch_all_open_issues(repo: str) -> dict[str, int]:
    """Fetch all open issues in one call. Returns {title: number} map."""
    return {issue["title"]: issue["number"] for issue in _gh_issue_list(repo, "open")}


def fetch_all_open_issues_full(repo: str) -> list[dict[str, Any]]:
    """Fetch all open issues with title, number, and milestone."""
    return _gh_issue_list(repo, "open")


def build_issue_milestone_map(issues: list[dict[str, Any]]) -> dict[int, str]:
    """Derive ``{issue_number: milestone_title}`` from a ``gh issue list`` payload.

    Used so Pass 2 can skip the ``gh issue edit --milestone`` subprocess when
    the remote value already matches the in-memory one.

    Args:
        issues (list[dict]): Raw ``gh issue list`` entries carrying
            ``number`` and ``milestone`` keys.

    Returns:
        dict[int, str]: Mapping of issue number to milestone title; missing
        or null milestones collapse to an empty string.

    Example:
        >>> build_issue_milestone_map([
        ...     {"number": 1, "milestone": {"title": "v0.1.0"}},
        ...     {"number": 2, "milestone": None},
        ... ])
        {1: 'v0.1.0', 2: ''}
    """
    result: dict[int, str] = {}
    for issue in issues:
        num = issue.get("number")
        if num is None:
            continue
        milestone = issue.get("milestone") or {}
        title = milestone.get("title") if isinstance(milestone, dict) else None
        result[num] = title or ""
    return result


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
    """Write updated story issue_number values back into the backlog file.

    Tasks are decoupled from GitHub now and never carry an
    ``issue_number`` — only stories' numbers are persisted. The ``tasks``
    parameter is retained for signature compatibility with prior callers.
    """
    id_to_num = build_id_to_issue_number_map(stories, [])
    for story in backlog_data.get("stories", []):
        if story["id"] in id_to_num:
            story["issue_number"] = id_to_num[story["id"]]
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
    ids, _, _ = _fetch_node_ids_and_edges(repo, issue_nums)
    return ids


def _fetch_node_ids_and_edges(
    repo: str, issue_nums: set[int]
) -> tuple[dict[int, str], set[tuple[int, int]], dict[int, int]]:
    """Fetch node IDs, blocker edges, and parent links in one GraphQL call.

    Folding the lookups into a single query lets Pass 4 skip already-present
    blocker pairs (``addBlockedBy`` isn't idempotent and rejects the whole
    batch with "Target issue has already been taken"). The ``parent`` link
    in the response is retained for backwards compatibility with the tuple
    shape but is no longer consumed by any sync pass.

    Args:
        repo (str): ``owner/name`` slug.
        issue_nums (set[int]): Issue numbers to resolve.

    Returns:
        tuple[dict[int, str], set[tuple[int, int]], dict[int, int]]:
            ``(num→node_id, {(blocked_num, blocker_num)},
            {child_num: parent_num})``.

    Example:
        >>> _fetch_node_ids_and_edges("o/r", {100})  # doctest: +SKIP
        Return: ({100: "NODE-100"}, {(100, 200)}, {100: 300})
    """
    nums = sorted(set(issue_nums))
    if not nums:
        return {}, set(), {}
    query = _build_node_id_edges_query(repo, nums)
    result = gh_json(["gh", "api", "graphql", "-f", f"query={query}"])
    repo_data = (result or {}).get("data", {}).get("repository") or {}
    return _parse_node_id_edges_response(repo_data)


def _build_node_id_edges_query(repo: str, nums: list[int]) -> str:
    """Build the batched GraphQL query for id + blockedBy + parent per issue."""
    owner, name = repo.split("/", 1)
    # ``blockedBy(first: 100)`` covers the practical fan-in; any issue
    # with >100 blockers is a data-model problem, not an API one.
    # (GitHub renamed this field from ``blockedByIssues`` → ``blockedBy``;
    # the old name now fails the query with "Field doesn't exist".)
    # ``parent { number }`` is retained in the response shape but no
    # longer drives a sync pass (sub-issue Pass 3 was retired).
    aliases = " ".join(
        f"i{n}: issue(number: {n}) {{ id number "
        f"blockedBy(first: 100) {{ nodes {{ number }} }} "
        f"parent {{ number }} }}"
        for n in nums
    )
    return f'{{ repository(owner: "{owner}", name: "{name}") {{ {aliases} }} }}'


def _parse_node_id_edges_response(
    repo_data: dict,
) -> tuple[dict[int, str], set[tuple[int, int]], dict[int, int]]:
    """Extract node-id map, existing (blocked, blocker) edges, and parent links."""
    ids: dict[int, str] = {}
    edges: set[tuple[int, int]] = set()
    parents: dict[int, int] = {}
    for val in repo_data.values():
        if not (val and val.get("id")):
            continue
        num = val["number"]
        ids[num] = val["id"]
        for b in (val.get("blockedBy") or {}).get("nodes") or []:
            if b.get("number"):
                edges.add((num, b["number"]))
        parent = val.get("parent") or {}
        if isinstance(parent, dict) and parent.get("number"):
            parents[num] = parent["number"]
    return ids, edges, parents


def _blocking_mutations(
    num_to_node: dict[int, str],
    pairs: list[tuple[int, int, str, str]],
    existing_edges: set[tuple[int, int]],
) -> list[str]:
    mutations: list[str] = []
    for bn, kn, bid, kid in pairs:
        # Skip pairs already set on GitHub — addBlockedBy isn't idempotent
        # and re-asserting fails the whole batch with "already been taken".
        if (bn, kn) in existing_edges:
            print(f"  #{bn} ({bid}) already blocked by #{kn} ({kid}) — skipped")
            continue
        b, k = num_to_node.get(bn), num_to_node.get(kn)
        if not b or not k:
            print(f"  ⚠ Missing node ID for #{bn} or #{kn}")
            continue
        print(f"  #{bn} ({bid}) blocked by #{kn} ({kid})")
        mutations.append(
            f"m{len(mutations)}: addBlockedBy(input: {{"
            f"issueId: {json.dumps(b)}, blockingIssueId: {json.dumps(k)}"
            f"}}) {{ issue {{ number }} blockingIssue {{ number }} }}"
        )
    return mutations


def set_blocking_relationships(
    repo: str,
    items: list[dict],
    id_map: dict[str, int],
    node_ids: dict[int, str] | None = None,
    existing_edges: set[tuple[int, int]] | None = None,
) -> None:
    """Set blocking relationships via batched ``addBlockedBy`` GraphQL mutations.

    If ``node_ids`` / ``existing_edges`` are provided, they're reused as-is;
    otherwise this function fetches both in one GraphQL call. Pairs whose
    edge already exists on GitHub are filtered out before mutating to
    keep ``addBlockedBy`` (non-idempotent) from rejecting the batch.
    """
    pairs, involved = _collect_blocking_pairs(items, id_map)
    if not pairs:
        print("  No blocking relationships to set.")
        return
    if node_ids is None or existing_edges is None:
        print(f"  Fetching node IDs + existing edges for {len(involved)} issues...")
        node_ids, existing_edges, _ = _fetch_node_ids_and_edges(repo, involved)
    execute_batched_mutations(
        _blocking_mutations(node_ids, pairs, existing_edges)
    )


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


def _resolve_one(
    t: dict[str, Any], existing_issues: dict[str, int], live: set[int]
) -> bool:
    """True if linked to a live issue; False if creation needed."""
    num = t.get("issue_number")
    if num and num in live:
        print(f"  ↳ Already has issue: #{num}")
        return True
    if num:
        print(f"  ↳ Stale #{num}; re-linking by title or re-creating")
        t.pop("issue_number", None)
    title = _item_full_title(t)
    if title in existing_issues:
        t["issue_number"] = existing_issues[title]
        print(f"  ↳ Matched existing #{t['issue_number']}")
        return True
    return False


def resolve_existing_issues(
    tasks: list[dict[str, Any]], existing_issues: dict[str, int]
) -> list[dict[str, Any]]:
    """Return tasks that still need a new issue created."""
    live = set(existing_issues.values())
    return [t for t in tasks if not _resolve_one(t, existing_issues, live)]


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


# Keys `gh project item-list --format json` emits alongside `id`/`content`
# when the corresponding project field is set; mapped to the canonical
# field names used in the mutation builder's `_BASE_FIELD_SPECS`.
_REMOTE_RAW_KEYS: list[tuple[str, str]] = [
    ("Status", "status"),
    ("Priority", "priority"),
    ("Points", "points"),
    ("Complexity", "complexity"),
    ("Start date", "start date"),
    ("Target date", "target date"),
]


def _field_specs_for_item(item: dict[str, Any]) -> list[tuple[str, str]]:
    specs = list(_BASE_FIELD_SPECS)
    specs.append(("Points", "points") if item.get("item_type") == "story" else ("Complexity", "complexity"))
    return specs


def _normalize_field_value(field_name: str, raw: Any) -> Any:
    """Coerce a field value to its canonical comparison form.

    Date fields get truncated to ``YYYY-MM-DD`` so an ISO timestamp from
    remote (``"2026-02-17T00:00:00Z"``) compares equal to the 10-char
    in-memory form. Other types pass through untouched — Python's ``==``
    already bridges ``int``/``float`` and string equality.

    Args:
        field_name (str): Canonical project field name (e.g. ``"Start date"``).
        raw (Any): Value as it arrived from remote or in-memory.

    Returns:
        Any: Normalized value ready for equality comparison.

    Example:
        >>> _normalize_field_value("Start date", "2026-02-17T00:00:00Z")
        '2026-02-17'
    """
    if raw is None:
        return None
    if field_name in ("Start date", "Target date") and isinstance(raw, str):
        return raw[:10]
    return raw


def _extract_item_field_values(raw_item: dict[str, Any]) -> dict[str, Any]:
    """Pull known project-field values from a ``gh project item-list`` entry.

    Reads the top-level keys the CLI emits (``status``, ``priority``,
    ``points``, ``complexity``, ``start date``, ``target date``) and
    translates them to the canonical field names the mutation builder
    uses. Absent / empty values are dropped so the caller can treat
    ``key in result`` as "remote has a value for this field".

    Args:
        raw_item (dict): One item dict from ``gh project item-list``.

    Returns:
        dict[str, Any]: ``{canonical_field_name: normalized_value}``.

    Example:
        >>> _extract_item_field_values(
        ...     {"id": "X", "status": "Ready", "start date": "2026-02-17"}
        ... )
        {'Status': 'Ready', 'Start date': '2026-02-17'}
    """
    result: dict[str, Any] = {}
    for canonical, raw_key in _REMOTE_RAW_KEYS:
        val = raw_item.get(raw_key)
        if val is None or val == "":
            continue
        result[canonical] = _normalize_field_value(canonical, val)
    return result


def _build_remote_values_map(items: list[dict]) -> dict[str, dict[str, Any]]:
    """Build ``{item_id: {field_name: current_value}}`` for all project items.

    The outer key matches the ``item_id`` used as the mutation target in
    ``_mutations_for_item``, so the diff filter can look up the remote
    snapshot in O(1) per field.

    Args:
        items (list[dict]): Items from :func:`get_project_items`.

    Returns:
        dict[str, dict[str, Any]]: Nested map of project-item id to
        per-field normalized remote value.

    Example:
        >>> _build_remote_values_map([{"id": "I1", "status": "Ready"}])
        {'I1': {'Status': 'Ready'}}
    """
    return {
        item["id"]: _extract_item_field_values(item)
        for item in items if item.get("id")
    }


def _should_skip_field(
    field_name: str, raw: Any, remote_values: dict[str, Any]
) -> bool:
    """True when the in-memory value already matches the remote snapshot."""
    if field_name not in remote_values:
        return False
    return remote_values[field_name] == _normalize_field_value(field_name, raw)


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
    remote_values: dict[str, Any],
) -> tuple[list[str], int]:
    mutations: list[str] = []
    idx = start_idx
    for field_name, task_key in _field_specs_for_item(task):
        raw = task.get(task_key)
        field = field_map.get(field_name)
        if not field or raw is None or raw == "":
            continue
        # Skip the write if the remote snapshot already matches — cheaper
        # than letting GitHub accept the redundant mutation silently.
        if _should_skip_field(field_name, raw, remote_values):
            print(f"  {task.get('id', '')} {field_name} already {raw!r} — skipped")
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
    remote_by_item: dict[str, dict[str, Any]],
) -> list[str]:
    """Build GraphQL mutation aliases for all tasks with known project items.

    ``remote_by_item`` is the ``{item_id: {field_name: value}}`` map produced
    by :func:`_build_remote_values_map`; fields whose in-memory value already
    matches the remote snapshot are filtered out before a mutation is built.
    """
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
        per_item_remote = remote_by_item.get(item_id, {})
        new_mutations, idx = _mutations_for_item(
            t, item_id, project_id, field_map, idx, per_item_remote
        )
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


def _issue_level_edit(
    task: dict[str, Any], repo: str, remote_milestone: str | None = None,
) -> None:
    num = task["issue_number"]
    milestone = task.get("milestone") or ""
    if milestone and milestone != remote_milestone:
        # Skip the fresh `gh` subprocess (~200–500ms per call) when the
        # remote already holds this milestone; only fire on a genuine diff.
        run(
            [
                "gh", "issue", "edit", str(num), "--repo", repo,
                "--milestone", milestone,
            ],
            check=False,
        )
    elif milestone:
        print(f"  {task.get('id', '')} milestone already {milestone!r} — skipped")
    set_parent_issue(repo, num, task.get("parent_issue") or "")
    create_branch_for_issue(repo, num, task.get("branch") or "")


def _apply_issue_level_parallel(
    tasks: list[dict[str, Any]],
    repo: str,
    remote_milestones: dict[int, str] | None = None,
) -> None:
    # Keep the per-task remote lookup out of the worker closure so each
    # future gets a plain string (or None) rather than a shared dict ref.
    remote_milestones = remote_milestones or {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                _issue_level_edit, t, repo,
                remote_milestones.get(t.get("issue_number")),
            ): t
            for t in tasks
        }
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
    remote_by_item: dict[str, dict[str, Any]] | None = None,
    remote_milestones: dict[int, str] | None = None,
) -> None:
    """Pass 2: batched GraphQL field updates, then parallel issue-level edits.

    When ``remote_by_item`` / ``remote_milestones`` are provided, fields and
    milestone edits that already match the remote snapshot are skipped — the
    common case for a no-op re-sync (e.g. the watcher echoing its own
    writeback) collapses to zero API calls.
    """
    remote_by_item = remote_by_item or {}
    remote_milestones = remote_milestones or {}
    execute_batched_mutations(
        _collect_mutations(tasks, items, project_id, field_map, remote_by_item)
    )
    for ms in {t["milestone"] for t in tasks if t.get("milestone")}:
        ensure_milestone(repo, ms)
    print("  Setting issue-level fields (parallel)...")
    _apply_issue_level_parallel(tasks, repo, remote_milestones)


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


def _remove_item_mutations(project_id: str, item_ids: list[str]) -> list[str]:
    return [
        f"m{i}: deleteProjectV2Item(input: {{"
        f"projectId: {json.dumps(project_id)}, itemId: {json.dumps(iid)}"
        f"}}) {{ deletedItemId }}"
        for i, iid in enumerate(item_ids)
    ]


def _remove_issues_from_project(
    project_number: int, owner: str, issues: list[dict[str, Any]]
) -> None:
    print("\nRemoving from project (batched)...")
    project_id = get_project_id(project_number, owner)
    items = get_project_items(project_number, owner)
    item_ids = [find_item_id(items, iss["number"]) for iss in issues]
    item_ids = [iid for iid in item_ids if iid]
    if not item_ids:
        return
    for iss in issues:
        print(f"  ✗ #{iss['number']}")
    execute_batched_mutations(_remove_item_mutations(project_id, item_ids))


def _delete_issue_mutations(node_ids: dict[int, str]) -> list[str]:
    return [
        f"m{i}: deleteIssue(input: {{issueId: {json.dumps(nid)}}}) {{ clientMutationId }}"
        for i, nid in enumerate(node_ids.values())
    ]


def _delete_issues_batched(repo: str, issues: list[dict[str, Any]]) -> None:
    nums = {iss["number"] for iss in issues if iss.get("number")}
    node_ids = _fetch_node_ids(repo, nums)
    print(f"\nDeleting {len(issues)} issues permanently (batched)...")
    for iss in issues:
        print(f"  ✗ #{iss['number']}: {iss['title']}")
    execute_batched_mutations(_delete_issue_mutations(node_ids))


def _clear_issue_numbers(backlog_data: dict[str, Any], backlog_path: Path) -> None:
    # Tasks are decoupled from GitHub now — only stories carry an
    # `issue_number`, so only stories need clearing on `delete-all`.
    for story in backlog_data.get("stories", []):
        story.pop("issue_number", None)
    backlog_path.write_text(json.dumps(backlog_data, indent=2), encoding="utf-8")
    print(f"\nCleared issue numbers from {backlog_path}")


# ---------------------------------------------------------------------------
# Sync workflow helpers
# ---------------------------------------------------------------------------


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


def _add_to_project_mutations(
    project_id: str, node_ids: dict[int, str], items: list[dict]
) -> list[str]:
    mutations: list[str] = []
    idx = 0
    for t in items:
        cid = node_ids.get(t.get("issue_number"))
        if not cid:
            continue
        mutations.append(
            f"m{idx}: addProjectV2ItemById(input: {{"
            f"projectId: {json.dumps(project_id)}, contentId: {json.dumps(cid)}"
            f"}}) {{ item {{ id }} }}"
        )
        idx += 1
    return mutations


def _add_all_to_project_batched(
    all_items: list[dict], project_id: str, repo: str
) -> tuple[dict[int, str], set[tuple[int, int]], dict[int, int]]:
    """Batched addProjectV2ItemById; also returns blocker edges + parents.

    The single node-id fetch here also surfaces each issue's current
    ``blockedBy`` edges (Pass 4 diff). The ``parent`` link is also
    returned for tuple compatibility but is no longer consumed.
    """
    print("\nAdding issues to project (batched)...")
    nums = {t["issue_number"] for t in all_items if t.get("issue_number")}
    node_ids, existing_edges, existing_parents = _fetch_node_ids_and_edges(repo, nums)
    mutations = _add_to_project_mutations(project_id, node_ids, all_items)
    execute_batched_mutations(mutations)
    print(f"  ✓ {len(mutations)} items added/verified")
    return node_ids, existing_edges, existing_parents


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
        # Reset the process-global title dedup set so a long-running
        # watcher doesn't carry forward claims from earlier syncs.
        _created_titles.clear()
        return getattr(self, method_name)(**kwargs)

    def sync(self, *, dry_run: bool = False) -> int:
        # Tasks are loaded so the writeback file structure is preserved,
        # but only stories are pushed to GitHub — sub-issue / per-task
        # syncing was retired.
        stories, tasks, _, backlog_data = load_flat_data(self.backlog_path)
        print(f"Sync mode: stories ({len(stories)} stories)")
        project_id, field_map = self._fetch_project_metadata()
        changed, remote_milestones = self._ensure_all_issues(stories)
        self._run_remote_passes(
            stories, project_id, field_map, backlog_data, remote_milestones,
        )
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
        _delete_issues_batched(self.repo, issues)
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

    def _ensure_all_issues(
        self, stories: list[dict]
    ) -> tuple[bool, dict[int, str]]:
        print("\nFetching existing issues...")
        # Single `gh issue list` fetch feeds both the title→number cache
        # (used to resolve existing issues) and the number→milestone map
        # (used by Pass 2 to skip redundant `gh issue edit` calls).
        issues = fetch_all_open_issues_full(self.repo)
        existing = {issue["title"]: issue["number"] for issue in issues}
        remote_milestones = build_issue_milestone_map(issues)
        print(f"  Found {len(existing)} open issues")
        changed = _resolve_or_create(stories, existing, self.repo, "stories")
        return changed, remote_milestones

    def _run_remote_passes(
        self,
        stories: list[dict],
        project_id: str,
        field_map: dict[str, dict],
        backlog_data: dict,
        remote_milestones: dict[int, str],
    ) -> None:
        node_ids, existing_edges, _ = _add_all_to_project_batched(
            stories, project_id, self.repo
        )
        items = self._fetch_project_items_for_pass2()
        remote_by_item = _build_remote_values_map(items)
        self._run_pass2(
            stories, items, project_id, field_map, remote_by_item, remote_milestones,
        )
        # Build the id->issue_number map from in-memory stories (disk isn't
        # written back until the end of sync, so reading the file here
        # would miss newly created numbers).
        full_id_map = build_id_to_issue_number_map(stories, [])
        print("\nPass 4: Setting blocking relationships...")
        set_blocking_relationships(
            self.repo, stories, full_id_map,
            node_ids=node_ids, existing_edges=existing_edges,
        )

    def _fetch_project_items_for_pass2(self) -> list[dict]:
        print("\nFetching project items...")
        items = get_project_items(self.project, self.owner)
        print(f"  Found {len(items)} items in project")
        return items

    def _run_pass2(
        self,
        stories: list[dict],
        items: list[dict],
        project_id: str,
        field_map: dict[str, dict],
        remote_by_item: dict[str, dict[str, Any]],
        remote_milestones: dict[int, str],
    ) -> None:
        print("\nPass 2: Setting project fields (batched GraphQL)...")
        run_pass2_batched(
            stories, items, project_id, field_map, self.repo,
            remote_by_item=remote_by_item, remote_milestones=remote_milestones,
        )
