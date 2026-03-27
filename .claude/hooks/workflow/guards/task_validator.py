"""task_validator.py — SubagentStop task-manager validator.

Merges task_tracker.jsonl (descriptions) and task_list_snapshot.json (blockedBy),
compares against project tasks, and blocks if any mismatch is found.

On success, sets state["task_manager_completed"] = True.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore


def _default_tracker_path() -> Path:
    state_path = os.environ.get("GUARDRAIL_STATE_PATH")
    base = Path(state_path).parent if state_path else Path(__file__).resolve().parent.parent
    return base / "task_tracker.jsonl"


def _default_snapshot_path() -> Path:
    state_path = os.environ.get("GUARDRAIL_STATE_PATH")
    base = Path(state_path).parent if state_path else Path(__file__).resolve().parent.parent
    return base / "task_list_snapshot.json"


def _get_project_tasks(story_id: str) -> list[dict]:
    """Run project_manager.py view <story_id> --tasks --json and return tasks."""
    pm_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "github_project" / "project_manager.py"
    result = subprocess.run(
        [sys.executable, str(pm_path), "view", story_id, "--tasks", "--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def _get_story_id(hook_input: dict) -> str | None:
    """Extract story ID from env var STORY_ID or last_assistant_message."""
    story_id = os.environ.get("STORY_ID")
    if story_id:
        return story_id
    # Try to find SK-\d+ or similar in last message
    import re
    msg = hook_input.get("last_assistant_message", "")
    m = re.search(r'\b([A-Z]{2}-\d{3})\b', msg)
    if m:
        return m.group(1)
    return None


def validate(
    hook_input: dict,
    state_path: Path | None = None,
    tracker_path: Path | None = None,
    snapshot_path: Path | None = None,
) -> tuple[str, str]:
    """Validate that Claude tasks match project tasks.

    Returns ("allow", "") on pass, ("block", reason) on fail.
    Non-task-manager agents are passed through immediately.
    """
    agent_type = hook_input.get("agent_type", "")
    if agent_type != "task-manager":
        return "allow", ""

    t_path = tracker_path or _default_tracker_path()
    s_path = snapshot_path or _default_snapshot_path()

    # Check snapshot exists
    if not s_path.exists():
        return "block", (
            "Task validation failed: no TaskList snapshot found. "
            "Call TaskList at the end to verify tasks before stopping."
        )

    # Load tracker entries
    claude_tasks_by_id: dict[str, dict] = {}
    if t_path.exists():
        for line in t_path.read_text(encoding="utf-8").strip().splitlines():
            if line.strip():
                entry = json.loads(line)
                claude_tasks_by_id[entry["id"]] = entry

    # Load snapshot
    snapshot: list[dict] = json.loads(s_path.read_text(encoding="utf-8"))

    # Get project tasks
    story_id = _get_story_id(hook_input)
    if not story_id:
        return "block", "Task validation failed: could not determine story ID. Include story ID in final message."

    project_tasks = _get_project_tasks(story_id)
    if not project_tasks:
        return "block", f"Task validation failed: could not load project tasks for {story_id}."

    errors: list[str] = []

    # Build snapshot lookup by id
    snapshot_by_id: dict[str, dict] = {t["id"]: t for t in snapshot}

    # Count check
    if len(snapshot) != len(project_tasks):
        errors.append(
            f"Task count mismatch: expected {len(project_tasks)} tasks, "
            f"got {len(snapshot)} Claude tasks. Create exactly one Claude task per project task."
        )
        # Return early — positional checks below would be misleading
        return "block", "\n".join(errors)

    # Build positional ID mapping: project task index (0-based) → Claude task id
    # Claude assigns sequential IDs "1", "2", "3"... matching creation order
    id_map: dict[str, str] = {}  # project_task_id → claude_task_id
    for i, pt in enumerate(project_tasks):
        claude_id = str(i + 1)
        id_map[pt["id"]] = claude_id

    # Per-task checks
    for i, pt in enumerate(project_tasks):
        claude_id = str(i + 1)
        expected_subject_prefix = f"{pt['id']}:"

        # Subject check (from snapshot or tracker)
        snapshot_task = snapshot_by_id.get(claude_id)
        if snapshot_task is None:
            errors.append(f"Claude task '{claude_id}' not found in TaskList snapshot.")
            continue

        subject = snapshot_task.get("subject", "")
        if not subject.startswith(expected_subject_prefix):
            errors.append(
                f"Task '{claude_id}' subject mismatch: expected to start with '{expected_subject_prefix}', "
                f"got '{subject}'."
            )

        # Description check (from tracker)
        tracker_entry = claude_tasks_by_id.get(claude_id)
        if tracker_entry is None:
            errors.append(f"Claude task '{claude_id}' not found in task tracker (TaskCreate was not recorded).")
        else:
            actual_desc = tracker_entry.get("description", "")
            expected_desc = pt.get("description", "")
            if expected_desc and expected_desc not in actual_desc:
                errors.append(
                    f"Task '{claude_id}' ({pt['id']}) description mismatch: "
                    f"expected to contain project description."
                )

        # blockedBy check
        expected_blocked_by = sorted(id_map[dep] for dep in pt.get("blocked_by", []) if dep in id_map)
        actual_blocked_by = sorted(snapshot_task.get("blockedBy", []))
        if expected_blocked_by != actual_blocked_by:
            errors.append(
                f"Task '{claude_id}' ({pt['id']}) blockedBy mismatch: "
                f"expected {expected_blocked_by}, got {actual_blocked_by}."
            )

    if errors:
        return "block", "Task validation failed:\n" + "\n".join(f"  - {e}" for e in errors)

    # Pass — set state flag and clean up temp files
    if state_path:
        store = StateStore(state_path)
        store.update(lambda s: s.update({"task_manager_completed": True}))

    # Clean up
    try:
        t_path.unlink(missing_ok=True)
        s_path.unlink(missing_ok=True)
    except OSError:
        pass

    return "allow", ""
