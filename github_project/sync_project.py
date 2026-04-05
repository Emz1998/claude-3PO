#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from config import DATA_PATHS, OWNER, PROJECT_NUMBER, REPO
from utils.gh_utils import gh_json, run

MAX_WORKERS = 8  # concurrent subprocess calls


def issue_url(repo: str, number: int) -> str:
    return f"https://github.com/{repo}/issues/{number}"


def ensure_label(label: str, repo: str) -> None:
    """Create a label if it doesn't already exist."""
    run(
        ["gh", "label", "create", label, "--repo", repo, "--force"],
        check=False,
    )


def fetch_all_open_issues(repo: str) -> dict[str, int]:
    """Fetch all open issues in one call. Returns {title: number} map."""
    out = run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--json",
            "title,number",
            "--limit",
            "500",
        ],
        check=False,
    )
    if not out:
        return {}
    return {issue["title"]: issue["number"] for issue in json.loads(out)}


def fetch_all_open_issues_full(repo: str) -> list[dict[str, Any]]:
    """Fetch all open issues with title and number."""
    out = run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--json",
            "title,number",
            "--limit",
            "500",
        ],
        check=False,
    )
    if not out:
        return []
    return json.loads(out)


def find_existing_issue(repo: str, title: str) -> int | None:
    """Search for an open issue by exact title. Returns issue number if found."""
    out = run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--search",
            f'"{title}" in:title',
            "--state",
            "open",
            "--json",
            "title,number",
        ],
        check=False,
    )
    if not out:
        return None
    for issue in json.loads(out):
        if issue.get("title") == title:
            return issue["number"]
    return None


# ---------------------------------------------------------------------------
# V2 format helpers
# ---------------------------------------------------------------------------


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
        parts.append(checklist)
    return "\n\n".join(parts)


def load_flat_data(
    stories_path: Path, sprint_path: Path
) -> tuple[list[dict], list[dict], dict, dict[str, Any], dict[str, Any]]:
    """Load flat stories and sprint files.

    Returns (stories, tasks, metadata, stories_data, sprint_data).
    """
    stories_data = json.loads(stories_path.read_text(encoding="utf-8"))
    sprint_data = json.loads(sprint_path.read_text(encoding="utf-8"))

    metadata = {
        "milestone": sprint_data.get("milestone", ""),
        "sprint": sprint_data.get("sprint"),
        "goal": stories_data.get("goal", ""),
        "dates": stories_data.get("dates", {}),
        "project": stories_data.get("project", ""),
        "totalPoints": stories_data.get("totalPoints"),
    }

    stories: list[dict] = []
    for story in stories_data.get("stories", []):
        story["item_type"] = "story"
        stories.append(story)

    tasks: list[dict] = []
    for task in sprint_data.get("tasks", []):
        task["item_type"] = "task"
        tasks.append(task)

    return stories, tasks, metadata, stories_data, sprint_data


def build_id_to_issue_number_map(
    stories: list[dict], tasks: list[dict]
) -> dict[str, int]:
    """Build {id: issue_number} map for all items that have an issue_number."""
    id_map: dict[str, int] = {}
    for item in stories + tasks:
        if item.get("issue_number"):
            id_map[item["id"]] = item["issue_number"]
    return id_map


def _get_issue_rest_id(repo: str, issue_num: int) -> int | None:
    """Get the REST API ID for an issue (different from issue number)."""
    out = run(
        ["gh", "api", f"repos/{repo}/issues/{issue_num}", "--jq", ".id"],
        check=False,
    )
    return int(out) if out else None


def set_blocking_relationships(
    repo: str, items: list[dict], id_map: dict[str, int]
) -> None:
    """Set blocking relationships using GitHub's addBlockedBy GraphQL mutation.

    Processes only `blocked_by` entries: for each item that is blocked by another,
    calls addBlockedBy(issueId=blocked, blockingIssueId=blocker).
    The `is_blocking` side is the inverse and gets covered when the blocked item
    lists the blocker in its `blocked_by`.
    """
    # Collect all unique issue numbers that participate in blocking relationships
    involved_nums: set[int] = set()
    pairs: list[tuple[int, int, str, str]] = (
        []
    )  # (blocked_num, blocker_num, blocked_id, blocker_id)
    for item in items:
        item_num = item.get("issue_number")
        if not item_num:
            continue
        for blocker_id in item.get("blocked_by", []):
            blocker_num = id_map.get(blocker_id)
            if blocker_num:
                pairs.append((item_num, blocker_num, item.get("id", ""), blocker_id))
                involved_nums.add(item_num)
                involved_nums.add(blocker_num)

    if not pairs:
        print("  No blocking relationships to set.")
        return

    # Batch-fetch node IDs for all involved issues
    print(f"  Fetching node IDs for {len(involved_nums)} issues...")
    num_to_node: dict[int, str] = {}
    for num in involved_nums:
        node_id = _get_issue_node_id(repo, num)
        if node_id:
            num_to_node[num] = node_id

    # Set each blocking relationship via addBlockedBy mutation
    for blocked_num, blocker_num, blocked_id, blocker_id in pairs:
        blocked_node = num_to_node.get(blocked_num)
        blocker_node = num_to_node.get(blocker_num)
        if not blocked_node or not blocker_node:
            print(f"  ⚠ Missing node ID for #{blocked_num} or #{blocker_num}")
            continue
        print(
            f"  #{blocked_num} ({blocked_id}) blocked by #{blocker_num} ({blocker_id})"
        )
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


def save_flat_data(
    stories: list[dict],
    tasks: list[dict],
    stories_path: Path,
    sprint_path: Path,
    stories_data: dict[str, Any],
    sprint_data: dict[str, Any],
) -> None:
    """Write updated issue_number values back into both flat files."""
    id_to_num = build_id_to_issue_number_map(stories, tasks)

    for story in stories_data.get("stories", []):
        if story["id"] in id_to_num:
            story["issue_number"] = id_to_num[story["id"]]

    for task in sprint_data.get("tasks", []):
        if task["id"] in id_to_num:
            task["issue_number"] = id_to_num[task["id"]]

    stories_path.write_text(json.dumps(stories_data, indent=2), encoding="utf-8")
    sprint_path.write_text(json.dumps(sprint_data, indent=2), encoding="utf-8")


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
        # Use GraphQL to create single-select with options
        # Note: color is a GraphQL enum (GRAY, not "GRAY")
        options_str = ", ".join(
            f'{{name: {json.dumps(opt)}, color: GRAY, description: ""}}'
            for opt in options
        )
        mutation = f"""
        mutation {{
          createProjectV2Field(input: {{
            projectId: {json.dumps(project_id)},
            dataType: SINGLE_SELECT,
            name: {json.dumps(field_name)},
            singleSelectOptions: [{options_str}]
          }}) {{
            projectV2Field {{ ... on ProjectV2SingleSelectField {{ id }} }}
          }}
        }}
        """
        run(
            ["gh", "api", "graphql", "-f", f"query={mutation}"],
            check=False,
        )
    elif field_type == "NUMBER":
        mutation = f"""
        mutation {{
          createProjectV2Field(input: {{
            projectId: {json.dumps(project_id)},
            dataType: NUMBER,
            name: {json.dumps(field_name)}
          }}) {{
            projectV2Field {{ ... on ProjectV2Field {{ id }} }}
          }}
        }}
        """
        run(
            ["gh", "api", "graphql", "-f", f"query={mutation}"],
            check=False,
        )
    elif field_type == "TEXT":
        mutation = f"""
        mutation {{
          createProjectV2Field(input: {{
            projectId: {json.dumps(project_id)},
            dataType: TEXT,
            name: {json.dumps(field_name)}
          }}) {{
            projectV2Field {{ ... on ProjectV2Field {{ id }} }}
          }}
        }}
        """
        run(
            ["gh", "api", "graphql", "-f", f"query={mutation}"],
            check=False,
        )

    return True


# ---------------------------------------------------------------------------
# Issue resolution and creation
# ---------------------------------------------------------------------------


def resolve_existing_issues(
    tasks: list[dict[str, Any]], existing_issues: dict[str, int]
) -> list[dict[str, Any]]:
    """
    Resolve tasks that already have an issue (by number or by title match).
    Returns the list of tasks that still need a new issue created.
    """
    needs_creation: list[dict[str, Any]] = []
    for t in tasks:
        if t.get("issue_number"):
            print(f"  ↳ Already has issue: #{t['issue_number']}")
            continue

        full_title = _item_full_title(t)
        if full_title in existing_issues:
            num = existing_issues[full_title]
            t["issue_number"] = num
            print(f"  ↳ Found existing issue: #{num} ({full_title})")
        else:
            needs_creation.append(t)

    return needs_creation


_create_lock = threading.Lock()
_created_titles: set[str] = set()


def _create_issue(task: dict[str, Any], repo: str) -> int:
    """Create a single issue. Returns issue number. Thread-safe with dedup guard."""
    full_title = _item_full_title(task)

    # Prevent duplicate creation across threads
    with _create_lock:
        if full_title in _created_titles:
            raise RuntimeError(f"Duplicate title detected, skipping: {full_title}")
        _created_titles.add(full_title)

    body = build_issue_body(task)
    labels = list(task.get("labels") or [])
    assignees = task.get("assignees") or []

    # Append type as a label if present
    item_type = task.get("type", "")
    if item_type and item_type not in labels:
        labels.append(item_type)

    # Ensure labels exist first
    for lab in labels:
        ensure_label(lab, repo)

    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        full_title,
        "--body",
        body,
    ]
    for lab in labels:
        cmd += ["--label", lab]
    for a in assignees:
        cmd += ["--assignee", a]

    url = run(cmd).strip()
    if not url:
        raise RuntimeError(f"gh issue create returned no URL for: {full_title}")
    number = int(url.rstrip("/").split("/")[-1])
    task["issue_number"] = number
    return number


def ensure_issue(
    task: dict[str, Any], repo: str, existing_issues: dict[str, int] | None = None
) -> int:
    """
    Ensure an issue exists. Returns issue number.
    If task['issue_number'] already present, keep it.
    Otherwise check existing_issues cache, then create.
    """
    if task.get("issue_number"):
        return task["issue_number"]

    full_title = _item_full_title(task)

    # Check bulk-fetched cache first (no API call)
    if existing_issues and full_title in existing_issues:
        num = existing_issues[full_title]
        print(f"  ↳ Found existing issue: #{num}")
        task["issue_number"] = num
        return num

    # Fallback: search API (for titles not in cache)
    existing = find_existing_issue(repo, full_title)
    if existing:
        print(f"  ↳ Found existing issue: #{existing}")
        task["issue_number"] = existing
        return existing

    return _create_issue(task, repo)


def add_to_project(project_number: int, owner: str, url: str) -> None:
    p = subprocess.run(
        [
            "gh",
            "project",
            "item-add",
            str(project_number),
            "--owner",
            owner,
            "--url",
            url,
        ],
        text=True,
        capture_output=True,
    )
    if p.returncode != 0:
        print(f"  ⚠ item-add failed for {url}: {p.stderr.strip()}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Project field helpers
# ---------------------------------------------------------------------------


def get_project_id(project_number: int, owner: str) -> str:
    """Get the project node ID via GraphQL."""
    query = """
    query($owner: String!, $number: Int!) {
      user(login: $owner) {
        projectV2(number: $number) {
          id
        }
      }
    }
    """
    result = gh_json(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"owner={owner}",
            "-F",
            f"number={project_number}",
        ]
    )
    return result["data"]["user"]["projectV2"]["id"]


def get_project_fields(project_number: int, owner: str) -> list[dict]:
    """Get all project fields with their IDs and options."""
    return gh_json(
        [
            "gh",
            "project",
            "field-list",
            str(project_number),
            "--owner",
            owner,
            "--format",
            "json",
        ]
    ).get("fields", [])


def get_project_items(project_number: int, owner: str) -> list[dict]:
    """Get all project items."""
    return gh_json(
        [
            "gh",
            "project",
            "item-list",
            str(project_number),
            "--owner",
            owner,
            "--format",
            "json",
            "--limit",
            "200",
        ]
    ).get("items", [])


def build_field_map(fields: list[dict]) -> dict[str, dict]:
    """
    Build a lookup: field_name -> {id, type, options: {option_name: option_id}}.
    """
    fmap: dict[str, dict] = {}
    for f in fields:
        name = f.get("name", "")
        entry: dict[str, Any] = {"id": f["id"], "type": f.get("type", "")}
        if "options" in f:
            entry["options"] = {opt["name"]: opt["id"] for opt in f["options"]}
        fmap[name] = entry
    return fmap


def find_item_id(items: list[dict], number: int) -> str | None:
    """Find the project item ID that matches the given issue number."""
    for item in items:
        if item.get("content", {}).get("number") == number:
            return item["id"]
    return None


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

    field_id = field["id"]
    cmd = [
        "gh",
        "project",
        "item-edit",
        "--id",
        item_id,
        "--field-id",
        field_id,
        "--project-id",
        project_id,
    ]

    has_options = bool(field.get("options"))

    if has_options:
        options = field["options"]
        option_id = options.get(value)
        if not option_id:
            print(
                f"  ⚠ Option '{value}' not found for field '{field_name}'. "
                f"Available: {list(options.keys())}",
                file=sys.stderr,
            )
            return
        cmd += ["--single-select-option-id", option_id]

    elif isinstance(value, (int, float)):
        cmd += ["--number", str(value)]

    elif (
        isinstance(value, str)
        and len(value) == 10
        and value[4] == "-"
        and value[7] == "-"
    ):
        cmd += ["--date", value]

    elif isinstance(value, str):
        cmd += ["--text", str(value)]

    else:
        print(
            f"  ⚠ Unsupported value type for '{field_name}': {type(value)}",
            file=sys.stderr,
        )
        return

    run(cmd, check=False)


# ---------------------------------------------------------------------------
# GraphQL batched field updates
# ---------------------------------------------------------------------------

BATCH_SIZE = 30  # mutations per GraphQL request


def _build_field_value(
    field_map: dict[str, dict], field_name: str, value: Any
) -> dict[str, str] | None:
    """
    Convert a field name + value into the GraphQL `value` input object.
    Returns None if the value should be skipped.
    """
    if value is None or value == "":
        return None

    field = field_map.get(field_name)
    if not field:
        print(f"  ⚠ Field '{field_name}' not found in project", file=sys.stderr)
        return None

    has_options = bool(field.get("options"))

    if has_options:
        option_id = field["options"].get(value)
        if not option_id:
            print(
                f"  ⚠ Option '{value}' not found for field '{field_name}'. "
                f"Available: {list(field['options'].keys())}",
                file=sys.stderr,
            )
            return None
        return {"singleSelectOptionId": json.dumps(option_id)}

    elif isinstance(value, (int, float)):
        return {"number": str(value)}

    elif (
        isinstance(value, str)
        and len(value) == 10
        and value[4] == "-"
        and value[7] == "-"
    ):
        return {"date": json.dumps(value)}

    elif isinstance(value, str):
        return {"text": json.dumps(value)}

    else:
        print(
            f"  ⚠ Unsupported value type for '{field_name}': {type(value)}",
            file=sys.stderr,
        )
        return None


def _collect_mutations(
    tasks: list[dict[str, Any]],
    items: list[dict],
    project_id: str,
    field_map: dict[str, dict],
) -> list[str]:
    """
    Build a list of individual GraphQL mutation aliases like:
      m0: updateProjectV2ItemFieldValue(input:{...}) { projectV2Item { id } }
    """
    base_field_specs = [
        ("Status", "status"),
        ("Priority", "priority"),
        ("Start date", "start_date"),
        ("Target date", "target_date"),
    ]

    mutations: list[str] = []
    idx = 0

    for t in tasks:
        num = t["issue_number"]
        item_id = find_item_id(items, num)
        if not item_id:
            print(
                f"  ⚠ Could not find item ID for #{num}, skipping fields",
                file=sys.stderr,
            )
            continue

        # Build field specs based on item type
        item_type = t.get("item_type", "task")
        field_specs = list(base_field_specs)
        if item_type == "story":
            field_specs.append(("Points", "points"))
        else:
            field_specs.append(("Complexity", "complexity"))

        for field_name, task_key in field_specs:
            raw_value = t.get(task_key)
            field = field_map.get(field_name)
            if not field or raw_value is None or raw_value == "":
                continue

            gql_value = _build_field_value(field_map, field_name, raw_value)
            if gql_value is None:
                continue

            field_id = field["id"]
            # Build the value object string, e.g. {singleSelectOptionId: "..."}
            value_parts = ", ".join(f"{k}: {v}" for k, v in gql_value.items())
            mutations.append(
                f"m{idx}: updateProjectV2ItemFieldValue(input: {{"
                f"projectId: {json.dumps(project_id)}, "
                f"itemId: {json.dumps(item_id)}, "
                f"fieldId: {json.dumps(field_id)}, "
                f"value: {{{value_parts}}}"
                f"}}) {{ projectV2Item {{ id }} }}"
            )
            idx += 1

    return mutations


def execute_batched_mutations(mutations: list[str]) -> None:
    """Send mutations in batches using `gh api graphql`."""
    total = len(mutations)
    if total == 0:
        print("  No field updates to send.")
        return

    print(f"  Sending {total} field updates in batches of {BATCH_SIZE}...")

    for start in range(0, total, BATCH_SIZE):
        batch = mutations[start : start + BATCH_SIZE]
        body = "mutation {\n  " + "\n  ".join(batch) + "\n}"

        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={body}"],
            text=True,
            capture_output=True,
        )

        batch_num = start // BATCH_SIZE + 1
        batch_total = (total + BATCH_SIZE - 1) // BATCH_SIZE

        if result.returncode != 0:
            print(
                f"  ⚠ Batch {batch_num}/{batch_total} failed: {result.stderr.strip()}",
                file=sys.stderr,
            )
            # Try to parse partial errors from the response
            if result.stdout:
                try:
                    resp = json.loads(result.stdout)
                    for err in resp.get("errors", []):
                        print(
                            f"    GraphQL error: {err.get('message', err)}",
                            file=sys.stderr,
                        )
                except json.JSONDecodeError:
                    pass
        else:
            print(f"  ✓ Batch {batch_num}/{batch_total} ({len(batch)} mutations)")


def run_pass2_batched(
    tasks: list[dict[str, Any]],
    items: list[dict],
    project_id: str,
    field_map: dict[str, dict],
    repo: str,
) -> None:
    """
    Pass 2: Set project fields via batched GraphQL, then handle
    issue-level fields (milestone, parent issue, branch) sequentially.
    """
    # 1. Batched GraphQL for project fields
    mutations = _collect_mutations(tasks, items, project_id, field_map)
    execute_batched_mutations(mutations)

    # 2. Issue-level fields in parallel (not supported by project GraphQL)
    # Pre-create unique milestones once to avoid duplicate API calls
    unique_milestones: set[str] = {t["milestone"] for t in tasks if t.get("milestone")}
    for ms in unique_milestones:
        ensure_milestone(repo, ms)

    def _issue_level_work(t: dict[str, Any]) -> None:
        num = t["issue_number"]
        milestone = t.get("milestone") or ""
        if milestone:
            run(
                [
                    "gh",
                    "issue",
                    "edit",
                    str(num),
                    "--repo",
                    repo,
                    "--milestone",
                    milestone,
                ],
                check=False,
            )
        set_parent_issue(repo, num, t.get("parent_issue") or "")
        create_branch_for_issue(repo, num, t.get("branch") or "")

    print("  Setting issue-level fields (parallel)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_issue_level_work, t): t for t in tasks}
        for fut in as_completed(futures):
            t = futures[fut]
            fut.result()
            status_value = t.get("status") or ""
            print(f"  ✓ {t.get('id','')} {t['title']} [{status_value or 'no status'}]")


def ensure_milestone(repo: str, milestone: str) -> None:
    """Create a milestone if it doesn't already exist."""
    if not milestone:
        return
    run(
        [
            "gh",
            "api",
            f"repos/{repo}/milestones",
            "-f",
            f"title={milestone}",
            "-f",
            "state=open",
        ],
        check=False,
    )


def set_milestone(repo: str, issue_num: int, milestone: str) -> None:
    """Set the milestone on an issue via gh issue edit."""
    if not milestone:
        return
    ensure_milestone(repo, milestone)
    run(
        [
            "gh",
            "issue",
            "edit",
            str(issue_num),
            "--repo",
            repo,
            "--milestone",
            milestone,
        ],
        check=False,
    )


def set_parent_issue(repo: str, child_num: int, parent_num: int | str) -> None:
    """Set a parent-child relationship between issues (sub-issues)."""
    if not parent_num:
        return
    # The sub_issues API requires the REST issue ID, not the issue number
    child_rest_id = _get_issue_rest_id(repo, child_num)
    if not child_rest_id:
        print(f"  ⚠ Could not get REST ID for #{child_num}", file=sys.stderr)
        return
    run(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{parent_num}/sub_issues",
            "-F",
            f"sub_issue_id={child_rest_id}",
            "--method",
            "POST",
        ],
        check=False,
    )


def create_branch_for_issue(repo: str, issue_num: int, branch_name: str) -> str | None:
    """Create a branch linked to an issue via `gh issue develop`. Returns branch name."""
    if not branch_name:
        return None
    run(
        [
            "gh",
            "issue",
            "develop",
            str(issue_num),
            "--repo",
            repo,
            "--name",
            branch_name,
            "--base",
            "main",
        ],
        check=False,
    )
    return branch_name


# ---------------------------------------------------------------------------
# Delete all tasks
# ---------------------------------------------------------------------------


def _close_issue(repo: str, issue_num: int) -> None:
    """Close a single issue."""
    run(
        ["gh", "issue", "close", str(issue_num), "--repo", repo],
        check=False,
    )


def _get_issue_node_id(repo: str, issue_num: int) -> str | None:
    """Get the GraphQL node ID for an issue."""
    out = run(
        ["gh", "api", f"repos/{repo}/issues/{issue_num}", "--jq", ".node_id"],
        check=False,
    )
    return out if out else None


def _delete_issue(repo: str, issue_num: int) -> None:
    """Permanently delete an issue via GraphQL deleteIssue mutation."""
    node_id = _get_issue_node_id(repo, issue_num)
    if not node_id:
        print(f"  ⚠ Could not get node ID for #{issue_num}", file=sys.stderr)
        return
    mutation = f'mutation {{ deleteIssue(input: {{issueId: "{node_id}"}}) {{ clientMutationId }} }}'
    run(
        ["gh", "api", "graphql", "-f", f"query={mutation}"],
        check=False,
    )


def _delete_branch(repo: str, branch_name: str) -> None:
    """Delete a remote branch."""
    run(
        [
            "gh",
            "api",
            f"repos/{repo}/git/refs/heads/{branch_name}",
            "--method",
            "DELETE",
        ],
        check=False,
    )


def _remove_from_project(project_number: int, owner: str, item_id: str) -> None:
    """Remove an item from the project."""
    run(
        [
            "gh",
            "project",
            "item-delete",
            str(project_number),
            "--owner",
            owner,
            "--id",
            item_id,
        ],
        check=False,
    )


def _fetch_all_issues(repo: str, state: str = "all") -> list[dict[str, Any]]:
    """Fetch issues by state (open, closed, all). Returns list of {title, number}."""
    if state == "all":
        open_issues = _fetch_all_issues(repo, "open")
        closed_issues = _fetch_all_issues(repo, "closed")
        return open_issues + closed_issues
    out = run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            state,
            "--json",
            "title,number",
            "--limit",
            "500",
        ],
        check=False,
    )
    if not out:
        return []
    return json.loads(out)


def _delete_all_tasks(
    stories: list[dict],
    tasks: list[dict],
    stories_path: Path,
    sprint_path: Path,
    stories_data: dict[str, Any],
    sprint_data: dict[str, Any],
    args: argparse.Namespace,
) -> int:
    """Fetch all issues (open + closed) from GitHub and permanently delete them."""
    print("Fetching all issues (open + closed) from GitHub...")
    issues = _fetch_all_issues(args.repo, "all")

    if not issues:
        print("No issues found in the repo.")
        return 0

    print(f"Found {len(issues)} issues to delete.")

    # Collect branches from local JSON (keyed by title for matching)
    all_items = stories + tasks

    branch_by_title: dict[str, str] = {}
    for t in all_items:
        if t.get("branch"):
            full_title = _item_full_title(t)
            branch_by_title[full_title] = t["branch"]

    branches: list[str] = []
    for issue in issues:
        b = branch_by_title.get(issue["title"], "")
        if b:
            branches.append(b)

    if args.dry_run:
        for issue in issues:
            print(f"  [dry-run] Would delete #{issue['number']}: {issue['title']}")
        for b in branches:
            print(f"  [dry-run] Would delete branch: {b}")
        return 0

    # 1. Delete linked branches in parallel
    if branches:
        print(f"\nDeleting {len(branches)} branches (parallel)...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            branch_futures = {
                pool.submit(_delete_branch, args.repo, b): b for b in branches
            }
            for bf in as_completed(branch_futures):
                b = branch_futures[bf]
                bf.result()
                print(f"  ✗ Deleted branch: {b}")

    # 2. Remove from project in parallel (before deleting issues)
    print("\nRemoving from project...")
    items = get_project_items(args.project, args.owner)
    items_to_remove: list[tuple[dict[str, Any], str]] = []
    for issue in issues:
        item_id = find_item_id(items, issue["number"])
        if item_id:
            items_to_remove.append((issue, item_id))

    if items_to_remove:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            remove_futures = {
                pool.submit(
                    _remove_from_project, args.project, args.owner, item_id
                ): issue
                for issue, item_id in items_to_remove
            }
            for rf in as_completed(remove_futures):
                issue = remove_futures[rf]
                rf.result()
                print(f"  ✗ Removed #{issue['number']} from project")

    # 3. Permanently delete all issues via GraphQL (handles both open and closed)
    print(f"\nDeleting {len(issues)} issues permanently (parallel)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        delete_futures = {
            pool.submit(_delete_issue, args.repo, issue["number"]): issue
            for issue in issues
        }
        for df in as_completed(delete_futures):
            issue = delete_futures[df]
            df.result()
            print(f"  ✗ Deleted #{issue['number']}: {issue['title']}")

    # 4. Clear issue_number from both flat files
    for story in stories_data.get("stories", []):
        story.pop("issue_number", None)
    for task in sprint_data.get("tasks", []):
        task.pop("issue_number", None)
    stories_path.write_text(json.dumps(stories_data, indent=2), encoding="utf-8")
    sprint_path.write_text(json.dumps(sprint_data, indent=2), encoding="utf-8")
    print(f"\nCleared issue numbers from {stories_path} and {sprint_path}")

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _load_config() -> dict[str, Any]:
    return {
        "repo": REPO,
        "owner": OWNER,
        "project": PROJECT_NUMBER,
        "data_paths": DATA_PATHS,
    }


def main() -> int:
    cfg = _load_config()
    data_paths = cfg.get("data_paths", {})

    ap = argparse.ArgumentParser(
        description="Sync issues from flat JSON files to GitHub Projects.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  # Sync issues to GitHub Projects (uses config.py defaults)
  python github_project/sync_project.py

  # With explicit data paths
  python github_project/sync_project.py --stories-data path/to/stories.json --sprint-data path/to/sprint.json

  # Dry run — preview changes without modifying anything
  python github_project/sync_project.py --dry-run

  # Delete all issues, branches, and remove from project
  python github_project/sync_project.py --delete-all

  # Sync only stories
  python github_project/sync_project.py --sync stories

  # Sync only sprint tasks
  python github_project/sync_project.py --sync sprint

  # Delete dry run — preview what would be deleted
  python github_project/sync_project.py --delete-all --dry-run

  # Override config
  python github_project/sync_project.py --repo owner/repo --project 5 --owner owner
""",
    )
    ap.add_argument(
        "--stories-data",
        default=data_paths.get("stories"),
        help="Path to stories.json",
    )
    ap.add_argument(
        "--sprint-data",
        default=data_paths.get("sprint"),
        help="Path to sprint.json",
    )
    ap.add_argument(
        "--repo", default=cfg.get("repo"), help="owner/repo, e.g. Emz1998/avaris-ai"
    )
    ap.add_argument(
        "--project", type=int, default=cfg.get("project"), help="Project number (v2)"
    )
    ap.add_argument(
        "--owner", default=cfg.get("owner"), help="Project owner (user or org)"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write changes back to JSON",
    )
    ap.add_argument(
        "--sync",
        choices=["all", "stories", "sprint"],
        default="all",
        help="Which items to sync: all (default), stories only, or sprint tasks only",
    )
    ap.add_argument(
        "--delete-all",
        action="store_true",
        help="Close all issues and remove them from the project",
    )
    args = ap.parse_args()

    if not args.stories_data or not args.sprint_data:
        print(
            "Provide --stories-data and --sprint-data (or set data_paths in config.py).",
            file=sys.stderr,
        )
        return 1

    if not args.repo or not args.project or not args.owner:
        print(
            "Provide --repo, --project, and --owner (or set them in config.py).",
            file=sys.stderr,
        )
        return 1

    stories_path = Path(args.stories_data)
    sprint_path = Path(args.sprint_data)

    # Load both flat files
    stories, tasks, metadata, stories_data, sprint_data = load_flat_data(
        stories_path, sprint_path
    )

    # --- Delete mode ---
    if args.delete_all:
        return _delete_all_tasks(
            stories, tasks, stories_path, sprint_path, stories_data, sprint_data, args
        )

    # Filter items based on --sync
    sync_stories = args.sync in ("all", "stories")
    sync_tasks = args.sync in ("all", "sprint")
    if not sync_stories:
        stories = []
    if not sync_tasks:
        tasks = []
    print(f"Sync mode: {args.sync} ({len(stories)} stories, {len(tasks)} tasks)")

    all_items = stories + tasks
    milestone = metadata.get("milestone", "")

    # Set milestone on all items
    if milestone:
        for item in all_items:
            item["milestone"] = milestone

    # Fetch project metadata once
    print("Fetching project metadata...")
    project_id = get_project_id(args.project, args.owner)
    fields = get_project_fields(args.project, args.owner)
    field_map = build_field_map(fields)
    print(f"  Project ID: {project_id}")
    print(f"  Fields: {list(field_map.keys())}")

    # --- Ensure required fields exist ---
    required_fields = [
        ("Points", "NUMBER", None),
        ("Complexity", "SINGLE_SELECT", ["XS", "S", "M", "L", "XL"]),
    ]
    fields_created = False
    for fname, ftype, foptions in required_fields:
        if ensure_project_field(project_id, fname, ftype, field_map, foptions):
            fields_created = True

    if fields_created:
        print("  Re-fetching fields after creation...")
        fields = get_project_fields(args.project, args.owner)
        field_map = build_field_map(fields)
        print(f"  Fields: {list(field_map.keys())}")

    # --- Pre-fetch all open issues in one call ---
    print("\nFetching existing issues...")
    existing_issues = fetch_all_open_issues(args.repo)
    print(f"  Found {len(existing_issues)} open issues")

    # --- Pass 1: Ensure issues exist (stories first, then tasks) ---
    changed = False

    for label, item_list in [("stories", stories), ("tasks", tasks)]:
        print(f"\nPass 1a: Resolving existing {label}...")
        for t in item_list:
            if "title" not in t:
                raise ValueError(f"Item missing 'title': {t}")

        needs_creation = resolve_existing_issues(item_list, existing_issues)
        changed = changed or any(
            t.get("issue_number") and t.get("issue_number") is not None
            for t in item_list
            if t not in needs_creation
        )

        if needs_creation:
            print(
                f"\nPass 1b: Creating {len(needs_creation)} new {label} (parallel)..."
            )
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = {
                    pool.submit(_create_issue, t, args.repo): t for t in needs_creation
                }
                for fut in as_completed(futures):
                    t = futures[fut]
                    num = fut.result()
                    print(f"  + {t.get('id','')} {t['title']} -> #{num}")
            changed = True
        else:
            print(f"  All {label} already have issues.")

    # --- Add all issues to project in parallel ---
    print("\nAdding issues to project (parallel)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        add_futures = {
            pool.submit(
                add_to_project,
                args.project,
                args.owner,
                issue_url(args.repo, t["issue_number"]),
            ): t
            for t in all_items
        }
        for add_fut in as_completed(add_futures):
            add_fut.result()
    print(f"  ✓ {len(all_items)} items added/verified")

    # --- Fetch all project items once after all adds ---
    print("\nFetching project items...")
    items = get_project_items(args.project, args.owner)
    print(f"  Found {len(items)} items in project")

    # --- Pass 2: Set fields via batched GraphQL ---
    # Map start/target dates for GraphQL field specs
    for s in stories:
        s["start_date"] = s.get("startDate", "")
        s["target_date"] = s.get("targetDate", "")
    for t in tasks:
        t["start_date"] = t.get("startDate", "")
        t["target_date"] = t.get("targetDate", "")

    print("\nPass 2: Setting project fields (batched GraphQL)...")
    run_pass2_batched(all_items, items, project_id, field_map, args.repo)

    # --- Pass 3: Set parent-child relationships (tasks under stories) ---
    print("\nPass 3: Setting parent-child relationships...")
    # Build id_map from both files so relationship lookups work even in partial sync
    all_stories_items = [s for s in stories_data.get("stories", [])]
    all_tasks_items = [t for t in sprint_data.get("tasks", [])]
    id_map = build_id_to_issue_number_map(all_stories_items, all_tasks_items)
    for t in tasks:
        story_id = t.get("parent_story_id")
        if story_id:
            story_num = id_map.get(story_id)
            if story_num and t.get("issue_number"):
                print(
                    f"  Setting #{t['issue_number']} ({t['id']}) as sub-issue of #{story_num} ({story_id})"
                )
                set_parent_issue(args.repo, t["issue_number"], story_num)

    # --- Pass 4: Set blocking relationships ---
    print("\nPass 4: Setting blocking relationships...")
    set_blocking_relationships(args.repo, all_items, id_map)

    # --- Write back updated issue numbers ---
    if changed and not args.dry_run:
        id_to_num = build_id_to_issue_number_map(stories, tasks)
        if sync_stories:
            for story in stories_data.get("stories", []):
                if story["id"] in id_to_num:
                    story["issue_number"] = id_to_num[story["id"]]
            stories_path.write_text(
                json.dumps(stories_data, indent=2), encoding="utf-8"
            )
            print(f"\nUpdated: {stories_path}")
        if sync_tasks:
            for task in sprint_data.get("tasks", []):
                if task["id"] in id_to_num:
                    task["issue_number"] = id_to_num[task["id"]]
            sprint_path.write_text(json.dumps(sprint_data, indent=2), encoding="utf-8")
            print(f"\nUpdated: {sprint_path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        raise
