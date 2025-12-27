#!/usr/bin/env python3
"""UserPromptSubmit hook to activate stop guard and init tasks.json when user types /build."""

import sys
import re
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, load_cache, write_cache  # type: ignore
from utils.roadmap import (  # type: ignore
    get_current_version,
    get_roadmap_path,
    load_roadmap,
)

# Command patterns that activate the stop guard
BUILD_COMMANDS = {"/build", "/implement"}
BUILD_SKILL_CACHE_KEY = "build_skill_active"


def activate_build_skill() -> None:
    """Activate build skill in cache."""
    cache = load_cache()
    cache[BUILD_SKILL_CACHE_KEY] = True
    write_cache(cache)


def get_current_phase_milestones() -> list[dict[str, str]]:
    """Get milestones in the current phase with id and name."""
    version = get_current_version()
    if not version:
        return []

    roadmap_path = get_roadmap_path(version)
    roadmap = load_roadmap(roadmap_path)
    if not roadmap:
        return []

    current = roadmap.get("current", {})
    current_phase_id = current.get("phase")
    if not current_phase_id:
        return []

    phases = roadmap.get("phases", [])
    for phase in phases:
        if phase.get("id") == current_phase_id:
            milestones = phase.get("milestones", [])
            return [
                {"id": ms.get("id", ""), "name": ms.get("name", "")}
                for ms in milestones
            ]

    return []


def init_tasks_json_with_worktrees(milestones: list[dict[str, str]]) -> None:
    """Initialize VS Code tasks.json with worktrees for each milestone."""
    project_dir = Path(__file__).parent.parent.parent.parent
    script_path = project_dir / ".claude" / "scripts" / "vscode_setup" / "init_tasks_json.py"

    if not script_path.exists():
        return

    milestones_json = json.dumps(milestones)

    try:
        subprocess.run(
            ["python3", str(script_path), "--milestones", milestones_json, "-f"],
            cwd=str(project_dir),
            capture_output=True,
            timeout=60,  # Longer timeout for worktree creation
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass  # Silently fail - tasks.json init is not critical


def launch_vscode_window() -> None:
    """Launch a new VS Code window in the project directory."""
    project_dir = Path(__file__).parent.parent.parent.parent

    try:
        subprocess.Popen(
            ["code", "-n", str(project_dir)],
            cwd=str(project_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        pass  # Silently fail if VS Code not installed


def extract_command(prompt: str) -> str | None:
    """Extract slash command from user prompt."""
    prompt_stripped = prompt.strip()
    # Match /command at start of prompt
    match = re.match(r"^(/\w+)", prompt_stripped)
    if match:
        return match.group(1).lower()
    return None


def main() -> None:
    """Check if user typed /build command, activate stop guard, and init tasks.json."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "UserPromptSubmit":
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    command = extract_command(prompt)
    if command and command in BUILD_COMMANDS:
        activate_build_skill()
        # Get milestones and initialize tasks.json with worktrees
        milestones = get_current_phase_milestones()
        if milestones:
            init_tasks_json_with_worktrees(milestones)
        # Launch new VS Code window
        launch_vscode_window()

    sys.exit(0)


if __name__ == "__main__":
    main()
