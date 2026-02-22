#!/usr/bin/env python3
"""Delete all git worktrees and their associated milestone branches."""

import argparse
import subprocess
from pathlib import Path


def get_project_dir() -> Path:
    # Get project root directory
    return Path(__file__).parent.parent.parent.parent


def get_worktrees() -> list[dict[str, str]]:
    # Get list of worktrees with their paths and branches
    project_dir = get_project_dir()
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=str(project_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return []

    worktrees = []
    current: dict[str, str] = {}

    for line in result.stdout.strip().split("\n"):
        if line.startswith("worktree "):
            current["path"] = line.replace("worktree ", "")
        elif line.startswith("branch "):
            current["branch"] = line.replace("branch refs/heads/", "")
        elif line == "":
            if current.get("path") and current.get("branch"):
                worktrees.append(current)
            current = {}

    # Handle last entry
    if current.get("path") and current.get("branch"):
        worktrees.append(current)

    return worktrees


def remove_worktree(worktree_path: str, force: bool = False) -> tuple[bool, str]:
    # Remove a git worktree
    project_dir = get_project_dir()
    cmd = ["git", "worktree", "remove", worktree_path]
    if force:
        cmd.insert(3, "--force")

    result = subprocess.run(
        cmd,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, f"Removed worktree: {worktree_path}"
    return False, f"Failed to remove worktree: {result.stderr.strip()}"


def delete_branch(branch_name: str, force: bool = False) -> tuple[bool, str]:
    # Delete a git branch
    project_dir = get_project_dir()
    flag = "-D" if force else "-d"
    result = subprocess.run(
        ["git", "branch", flag, branch_name],
        cwd=str(project_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, f"Deleted branch: {branch_name}"
    return False, f"Failed to delete branch: {result.stderr.strip()}"


def cleanup_worktrees_dir() -> tuple[bool, str]:
    # Remove the worktrees directory if empty
    project_dir = get_project_dir()
    worktrees_dir = project_dir / "worktrees"

    if not worktrees_dir.exists():
        return True, "Worktrees directory does not exist"

    # Check if directory is empty
    if any(worktrees_dir.iterdir()):
        return False, "Worktrees directory is not empty"

    worktrees_dir.rmdir()
    return True, "Removed empty worktrees directory"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete all git worktrees and their associated milestone branches"
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force remove worktrees and branches even with uncommitted changes",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--branches-only",
        action="store_true",
        help="Only delete milestone branches (skip worktree removal)",
    )
    args = parser.parse_args()

    project_dir = get_project_dir()
    worktrees_dir = project_dir / "worktrees"

    # Get all worktrees
    worktrees = get_worktrees()

    # Filter to only milestone worktrees (in worktrees/ directory)
    milestone_worktrees = [
        wt
        for wt in worktrees
        if wt["path"].startswith(str(worktrees_dir))
        and wt["branch"].startswith("milestones/")
    ]

    if not milestone_worktrees:
        print("No milestone worktrees found.")
        return

    print(f"Found {len(milestone_worktrees)} milestone worktree(s):\n")

    for wt in milestone_worktrees:
        print(f"  - {wt['path']}")
        print(f"    Branch: {wt['branch']}")

    if args.dry_run:
        print("\n[DRY RUN] Would delete the above worktrees and branches.")
        return

    print("\n" + "=" * 50)

    # Remove worktrees first
    if not args.branches_only:
        print("\nRemoving worktrees...")
        for wt in milestone_worktrees:
            success, msg = remove_worktree(wt["path"], args.force)
            status = "OK" if success else "FAIL"
            print(f"  [{status}] {msg}")

    # Delete branches
    print("\nDeleting branches...")
    for wt in milestone_worktrees:
        success, msg = delete_branch(wt["branch"], args.force)
        status = "OK" if success else "FAIL"
        print(f"  [{status}] {msg}")

    # Cleanup empty worktrees directory
    if not args.branches_only:
        success, msg = cleanup_worktrees_dir()
        if success:
            print(f"\n{msg}")

    print("\nCleanup complete.")


if __name__ == "__main__":
    main()
