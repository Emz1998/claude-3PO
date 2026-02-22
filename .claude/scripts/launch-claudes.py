#!/usr/bin/env python3
"""Launch multiple tmux windows with claude, each in its own git worktree."""

import argparse
import os
import re
import subprocess

SESSION = "claude"
PROJECT_DIR = os.path.expanduser("~/avaris-ai")
WORKTREE_DIR = os.path.join(PROJECT_DIR, ".worktrees")


def run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, **kwargs)


def session_exists() -> bool:
    result = run(
        ["tmux", "has-session", "-t", SESSION], check=False, capture_output=True
    )
    return result.returncode == 0


def extract_story_id(prompt: str) -> str | None:
    """Extract story ID (e.g. TS-001) from a prompt like '/implement TS-001'."""
    match = re.search(r"((?:US|TS|SK|BG)-\d{3})", prompt)
    return match.group(1) if match else None


def ensure_worktree(story_id: str) -> str:
    """Create a git worktree for the story if it doesn't exist. Returns worktree path."""
    branch = f"feat/{story_id}"
    worktree_path = os.path.join(WORKTREE_DIR, story_id)

    if os.path.isdir(worktree_path):
        return worktree_path

    os.makedirs(WORKTREE_DIR, exist_ok=True)

    # Check if branch exists
    result = run(
        ["git", "-C", PROJECT_DIR, "rev-parse", "--verify", branch],
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        run(["git", "-C", PROJECT_DIR, "worktree", "add", worktree_path, branch])
    else:
        run(["git", "-C", PROJECT_DIR, "worktree", "add", "-b", branch, worktree_path])

    return worktree_path


def build_claude_cmd(prompt: str | None) -> str:
    if prompt:
        return f"claude {prompt}"
    return "claude"


def launch_window(prompt: str | None, is_first: bool = False) -> None:
    """Launch a tmux window, using a worktree if a story ID is found."""
    story_id = extract_story_id(prompt) if prompt else None
    work_dir = ensure_worktree(story_id) if story_id else PROJECT_DIR

    if is_first:
        run(["tmux", "new-session", "-d", "-s", SESSION, "-c", work_dir])
    else:
        run(["tmux", "new-window", "-t", SESSION, "-c", work_dir])

    run(["tmux", "send-keys", "-t", SESSION, build_claude_cmd(prompt), "Enter"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch tmux windows with claude")
    parser.add_argument(
        "prompts",
        nargs="*",
        default=[None],
        help='prompts for each window (e.g. "/implement TS-001" "/implement TS-002")',
    )
    args = parser.parse_args()

    prompts: list[str | None] = args.prompts if args.prompts else [None]

    if session_exists():
        run(["tmux", "kill-session", "-t", SESSION])

    for i, prompt in enumerate(prompts):
        launch_window(prompt, is_first=(i == 0))

    os.execvp("tmux", ["tmux", "attach", "-t", SESSION])


if __name__ == "__main__":
    main()
