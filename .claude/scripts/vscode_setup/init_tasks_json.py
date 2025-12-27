#!/usr/bin/env python3
"""Initialize VS Code tasks.json with Claude Code launcher tasks."""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def sanitize_name(name: str) -> str:
    # Sanitize milestone name for branch/directory naming
    return name.lower().replace(" ", "-").replace("/", "-").replace("\\", "-")


def create_worktree(project_dir: Path, milestone_id: str, milestone_name: str) -> Path | None:
    # Create a git worktree for a milestone
    worktrees_dir = project_dir / "worktrees"
    worktrees_dir.mkdir(exist_ok=True)

    safe_name = sanitize_name(milestone_name)
    branch_name = f"milestones/{milestone_id}_{safe_name}"
    worktree_path = worktrees_dir / f"{milestone_id}_{safe_name}"

    if worktree_path.exists():
        return worktree_path

    # Check if branch exists
    result = subprocess.run(
        ["git", "rev-parse", "--verify", branch_name],
        cwd=str(project_dir),
        capture_output=True,
    )
    branch_exists = result.returncode == 0

    try:
        if branch_exists:
            # Use existing branch
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch_name],
                cwd=str(project_dir),
                capture_output=True,
                check=True,
            )
        else:
            # Create new branch from current HEAD
            subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_path)],
                cwd=str(project_dir),
                capture_output=True,
                check=True,
            )
        return worktree_path
    except subprocess.CalledProcessError:
        return None


def create_claude_task(
    label: str,
    worktree_path: Path | None = None,
    run_on_open: bool = True
) -> dict[str, Any]:
    # Creates a VS Code task configuration for launching Claude Code
    if worktree_path:
        command = f"cd {worktree_path} && claude"
    else:
        command = "claude"

    task: dict[str, Any] = {
        "label": label,
        "type": "shell",
        "command": command,
        "presentation": {
            "reveal": "always",
            "panel": "new"
        },
        "isBackground": True,
        "problemMatcher": []
    }
    if run_on_open:
        task["runOptions"] = {"runOn": "folderOpen"}
    return task


def create_tasks_json(
    num_tasks: int = 2,
    run_on_open: bool = True,
    milestones: list[dict[str, str]] | None = None,
    project_dir: Path | None = None
) -> dict[str, Any]:
    # Creates the complete tasks.json structure
    tasks = []

    if milestones and project_dir:
        for ms in milestones:
            ms_id = ms.get("id", "")
            ms_name = ms.get("name", "")
            worktree_path = create_worktree(project_dir, ms_id, ms_name)
            label = f"Launch Claude - {ms_id}"
            tasks.append(create_claude_task(label, worktree_path, run_on_open))
    else:
        tasks = [
            create_claude_task(f"Launch Claude {i + 1}", None, run_on_open)
            for i in range(num_tasks)
        ]

    return {
        "version": "2.0.0",
        "tasks": tasks
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize VS Code tasks.json with Claude Code launcher tasks"
    )
    parser.add_argument(
        "-n", "--num-tasks",
        type=int,
        default=2,
        help="Number of Claude launcher tasks to create (default: 2)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output path for tasks.json (default: .vscode/tasks.json)"
    )
    parser.add_argument(
        "--no-auto-run",
        action="store_true",
        help="Disable automatic run on folder open"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing tasks.json without prompting"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the tasks.json content without writing to file"
    )
    parser.add_argument(
        "--milestones",
        type=str,
        default=None,
        help="JSON array of milestones [{\"id\": \"MS-001\", \"name\": \"Name\"}]"
    )
    args = parser.parse_args()

    # Determine project root and output path
    project_root = Path(__file__).parent.parent.parent.parent
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project_root / ".vscode" / "tasks.json"

    # Parse milestones if provided
    milestones = None
    if args.milestones:
        try:
            milestones = json.loads(args.milestones)
        except json.JSONDecodeError:
            milestones = None

    # Create tasks.json content
    run_on_open = not args.no_auto_run
    tasks_json = create_tasks_json(
        args.num_tasks,
        run_on_open,
        milestones,
        project_root if milestones else None
    )
    json_content = json.dumps(tasks_json, indent=2)

    # Dry run - just print
    if args.dry_run:
        print(json_content)
        return

    # Check if file exists
    if output_path.exists() and not args.force:
        response = input(f"{output_path} already exists. Overwrite? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    output_path.write_text(json_content + "\n")
    task_count = len(tasks_json.get("tasks", []))
    print(f"Created {output_path} with {task_count} Claude launcher task(s)")


if __name__ == "__main__":
    main()
