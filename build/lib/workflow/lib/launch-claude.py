#!/usr/bin/env python3
"""Launch multiple tmux windows with claude."""

import argparse
import json
import os
import re
import subprocess

SESSION = "claude"
PROJECT_DIR = os.path.expanduser("~/avaris-ai")
SPRINT_STATUS_PATH = os.path.join(PROJECT_DIR, "project/sprints/SPRINT-001/sprint-status.json")


def run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, **kwargs)


def session_exists() -> bool:
    result = run(
        ["tmux", "has-session", "-t", SESSION], check=False, capture_output=True
    )
    return result.returncode == 0


def load_sprint_id() -> str:
    """Read sprint_id directly from the sprint status JSON."""
    with open(SPRINT_STATUS_PATH) as f:
        return json.load(f).get("sprint_id", "SPRINT-001")


def extract_story_id(prompt: str) -> str | None:
    """Extract story ID (e.g. TS-001) from a prompt like '/implement TS-001'."""
    match = re.search(r"((?:US|TS|SK|BG)-\d{3})", prompt)
    return match.group(1) if match else None


def build_worktree_name(sprint_id: str, story_id: str) -> str:
    """Build worktree name as sprint_id/story_id (e.g. SPRINT-001/TS-001)."""
    return f"{sprint_id}/{story_id}"


def build_claude_cmd(prompt: str | None, worktree_name: str | None = None) -> str:
    parts = ["claude"]
    if prompt:
        parts.append(f'"{prompt}"')
    if worktree_name:
        parts.extend(["--worktree", worktree_name])
    return " ".join(parts)


def launch_window(
    prompt: str | None, sprint_id: str, is_first: bool = False
) -> None:
    """Launch a tmux window with claude in its own worktree."""
    story_id = extract_story_id(prompt) if prompt else None
    worktree_name = build_worktree_name(sprint_id, story_id) if story_id else None
    window_name = story_id or "main"

    if is_first:
        run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                SESSION,
                "-n",
                window_name,
                "-c",
                PROJECT_DIR,
            ]
        )
    else:
        run(["tmux", "new-window", "-t", SESSION, "-n", window_name, "-c", PROJECT_DIR])

    run(["tmux", "send-keys", "-t", SESSION, build_claude_cmd(prompt, worktree_name), "Enter"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch tmux windows with claude")
    parser.add_argument(
        "prompts",
        nargs="*",
        default=[None],
        help='prompts for each window (e.g. "/implement TS-001" "/implement TS-002")',
    )
    args = parser.parse_args()

    sprint_id = load_sprint_id()
    prompts: list[str | None] = args.prompts if args.prompts else [None]

    if session_exists():
        run(["tmux", "kill-session", "-t", SESSION])

    for i, prompt in enumerate(prompts):
        launch_window(prompt, sprint_id, is_first=(i == 0))

    os.execvp("tmux", ["tmux", "attach", "-t", SESSION])


if __name__ == "__main__":
    main()
