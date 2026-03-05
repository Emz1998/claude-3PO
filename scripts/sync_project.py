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

MAX_WORKERS = 8  # concurrent subprocess calls


def run(cmd: list[str], *, check: bool = True) -> str:
    """Run a command and return stdout."""
    p = subprocess.run(cmd, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(
            f"Command failed ({p.returncode}): {' '.join(cmd)}\n\nSTDERR:\n{p.stderr}"
        )
    return p.stdout.strip()


def gh_json(cmd: list[str]) -> Any:
    out = run(cmd)
    if not out:
        return None
    return json.loads(out)


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


def _task_full_title(task: dict[str, Any]) -> str:
    """Build the full issue title from key + title."""
    key = task.get("key")
    title = task["title"]
    return f"{key} {title}".strip() if key else title


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

        full_title = _task_full_title(t)
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
    full_title = _task_full_title(task)

    # Prevent duplicate creation across threads
    with _create_lock:
        if full_title in _created_titles:
            raise RuntimeError(f"Duplicate title detected, skipping: {full_title}")
        _created_titles.add(full_title)

    body = task.get("body") or ""
    labels = task.get("labels") or []
    assignees = task.get("assignees") or []

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

    full_title = _task_full_title(task)

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
    field_specs = [
        ("Status", "status"),
        ("Priority", "priority"),
        ("Size", "size"),
        ("Estimate", "estimate"),
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
            print(f"  ✓ {t.get('key','')} {t['title']} [{status_value or 'no status'}]")


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
    run(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{parent_num}/sub_issues",
            "-f",
            f"sub_issue_id={child_num}",
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


def _delete_all_tasks(
    tasks: list[dict[str, Any]], tasks_path: Path, args: argparse.Namespace
) -> int:
    """Close all issues and remove them from the project."""
    issues_with_numbers = [t for t in tasks if t.get("issue_number")]

    if not issues_with_numbers:
        print("No tasks with issue numbers to delete.")
        return 0

    print(f"Deleting {len(issues_with_numbers)} issues...")

    if args.dry_run:
        for t in issues_with_numbers:
            print(f"  [dry-run] Would close #{t['issue_number']}: {t['title']}")
        return 0

    # 1. Close issues in parallel
    print("\nClosing issues (parallel)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_close_issue, args.repo, t["issue_number"]): t
            for t in issues_with_numbers
        }
        for fut in as_completed(futures):
            t = futures[fut]
            fut.result()
            print(f"  ✗ Closed #{t['issue_number']}: {t.get('key','')} {t['title']}")

    # 2. Remove from project in parallel
    print("\nRemoving from project...")
    items = get_project_items(args.project, args.owner)
    items_to_remove: list[tuple[dict[str, Any], str]] = []
    for t in issues_with_numbers:
        item_id = find_item_id(items, t["issue_number"])
        if item_id:
            items_to_remove.append((t, item_id))

    if items_to_remove:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(_remove_from_project, args.project, args.owner, item_id): t
                for t, item_id in items_to_remove
            }
            for fut in as_completed(futures):
                t = futures[fut]
                fut.result()
                print(f"  ✗ Removed #{t['issue_number']} from project")

    # 3. Clear issue_number from tasks.json
    for t in tasks:
        t.pop("issue_number", None)
    tasks_path.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    print(f"\nCleared issue numbers from {tasks_path}")

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True, help="Path to tasks.json")
    ap.add_argument("--repo", required=True, help="owner/repo, e.g. Emz1998/avaris-ai")
    ap.add_argument("--project", required=True, type=int, help="Project number (v2)")
    ap.add_argument("--owner", required=True, help="Project owner (user or org)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write changes back to tasks.json",
    )
    ap.add_argument(
        "--delete-all",
        action="store_true",
        help="Close all issues listed in tasks.json and remove them from the project",
    )
    args = ap.parse_args()

    tasks_path = Path(args.tasks)
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))

    # --- Delete mode ---
    if args.delete_all:
        return _delete_all_tasks(tasks, tasks_path, args)

    # Fetch project metadata once
    print("Fetching project metadata...")
    project_id = get_project_id(args.project, args.owner)
    fields = get_project_fields(args.project, args.owner)
    field_map = build_field_map(fields)
    print(f"  Project ID: {project_id}")
    print(f"  Fields: {list(field_map.keys())}")

    # --- Pre-fetch all open issues in one call ---
    print("\nFetching existing issues...")
    existing_issues = fetch_all_open_issues(args.repo)
    print(f"  Found {len(existing_issues)} open issues")

    # --- Pass 1: Ensure issues exist ---
    changed = False
    print("\nPass 1a: Resolving existing issues...")
    for t in tasks:
        if "title" not in t:
            raise ValueError(f"Task missing 'title': {t}")

    needs_creation = resolve_existing_issues(tasks, existing_issues)
    # Mark changed if any tasks got matched from cache
    changed = any(
        t.get("issue_number") and t.get("issue_number") != None
        for t in tasks
        if t not in needs_creation
    )

    # --- Parallel issue creation for tasks that need it ---
    if needs_creation:
        print(f"\nPass 1b: Creating {len(needs_creation)} new issues (parallel)...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(_create_issue, t, args.repo): t for t in needs_creation
            }
            for fut in as_completed(futures):
                t = futures[fut]
                num = fut.result()
                print(f"  + {t.get('key','')} {t['title']} -> #{num}")
        changed = True
    else:
        print("  All tasks already have issues.")

    # --- Add all issues to project in parallel ---
    print("\nAdding issues to project (parallel)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                add_to_project,
                args.project,
                args.owner,
                issue_url(args.repo, t["issue_number"]),
            ): t
            for t in tasks
        }
        for fut in as_completed(futures):
            fut.result()
    print(f"  ✓ {len(tasks)} items added/verified")

    # --- Fetch all project items once after all adds ---
    print("\nFetching project items...")
    items = get_project_items(args.project, args.owner)
    print(f"  Found {len(items)} items in project")

    # --- Pass 2: Set fields via batched GraphQL ---
    print("\nPass 2: Setting project fields (batched GraphQL)...")
    run_pass2_batched(tasks, items, project_id, field_map, args.repo)

    if changed and not args.dry_run:
        tasks_path.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        print(f"\nUpdated: {tasks_path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        raise

# if __name__ == "__main__":
#     print(json.dumps(get_project_fields(4, "Emz1998"), indent=2))
