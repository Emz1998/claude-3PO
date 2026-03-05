#!/usr/bin/env python3
"""Update the status of a GitHub Projects item by issue number or key."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys


def run(cmd: list[str], *, check: bool = True) -> str:
    p = subprocess.run(cmd, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(
            f"Command failed ({p.returncode}): {' '.join(cmd)}\n\nSTDERR:\n{p.stderr}"
        )
    return p.stdout.strip()


def get_project_id(project_number: int, owner: str) -> str:
    query = """
    query($owner: String!, $number: Int!) {
      user(login: $owner) {
        projectV2(number: $number) {
          id
        }
      }
    }
    """
    result = json.loads(
        run(
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
    )
    return result["data"]["user"]["projectV2"]["id"]


def get_project_fields(project_number: int, owner: str) -> list[dict]:
    out = run(
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
    )
    return json.loads(out).get("fields", [])


def get_project_items(project_number: int, owner: str) -> list[dict]:
    out = run(
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
    )
    return json.loads(out).get("items", [])


def find_status_field(fields: list[dict]) -> dict | None:
    for f in fields:
        if f.get("name") == "Status":
            return f
    return None


def find_item(items: list[dict], issue_number: int) -> dict | None:
    for item in items:
        if item.get("content", {}).get("number") == issue_number:
            return item
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Update the status of a GitHub Projects item.",
        epilog="Example: python scripts/update_status.py --issue 5 --status 'In progress'",
    )
    ap.add_argument("--issue", required=True, type=int, help="Issue number")
    ap.add_argument("--status", required=True, help="New status value")
    ap.add_argument("--project", required=True, type=int, help="Project number (v2)")
    ap.add_argument("--owner", required=True, help="Project owner (user or org)")
    ap.add_argument(
        "--repo", help="owner/repo — also update tasks.json if --tasks is given"
    )
    ap.add_argument("--tasks", help="Path to tasks.json to keep in sync")
    ap.add_argument(
        "--list-statuses", action="store_true", help="List available statuses and exit"
    )
    args = ap.parse_args()

    # Fetch project metadata
    fields = get_project_fields(args.project, args.owner)
    status_field = find_status_field(fields)
    if not status_field:
        print("ERROR: No 'Status' field found in project", file=sys.stderr)
        return 1

    options = {opt["name"]: opt["id"] for opt in status_field.get("options", [])}

    if args.list_statuses:
        print("Available statuses:")
        for name in options:
            print(f"  - {name}")
        return 0

    if args.status not in options:
        print(
            f"ERROR: '{args.status}' is not a valid status.\n"
            f"Available: {', '.join(options.keys())}",
            file=sys.stderr,
        )
        return 1

    # Find the item
    items = get_project_items(args.project, args.owner)
    item = find_item(items, args.issue)
    if not item:
        print(f"ERROR: Issue #{args.issue} not found in project", file=sys.stderr)
        return 1

    project_id = get_project_id(args.project, args.owner)

    # Update status
    run(
        [
            "gh",
            "project",
            "item-edit",
            "--id",
            item["id"],
            "--field-id",
            status_field["id"],
            "--project-id",
            project_id,
            "--single-select-option-id",
            options[args.status],
        ]
    )

    print(f"✓ Issue #{args.issue} → {args.status}")

    # Optionally update tasks.json
    if args.tasks:
        from pathlib import Path

        tasks_path = Path(args.tasks)
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        for t in tasks:
            if t.get("issue_number") == args.issue:
                t["status"] = args.status
                tasks_path.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
                print(f"✓ Updated {tasks_path}")
                break

    return 0


# if __name__ == "__main__":
#     try:
#         raise SystemExit(main())
#     except Exception as e:
#         print(f"\nERROR: {e}", file=sys.stderr)
#         raise

if __name__ == "__main__":
    print(json.dumps(get_project_fields(4, "Emz1998"), indent=2))
