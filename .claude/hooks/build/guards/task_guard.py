"""task_guard.py — PreToolUse TaskCreate + TaskCompleted hook handler.

Validates that each Claude task maps to a real project task via metadata.
Caches project tasks from project_manager.py and tracks subtask coverage.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from build.session_store import SessionStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
PROJECT_MANAGER = PROJECT_ROOT / "github_project" / "project_manager.py"


def _fetch_project_tasks(story_id: str) -> list[dict]:
    """Call project_manager.py view <story-id> --tasks --json and return parsed tasks."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_MANAGER),
                "view",
                story_id,
                "--tasks",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _ensure_tasks_cache(state: dict, story_id: str) -> list[dict]:
    """Populate state['tasks'] from project_manager on first call, return cached list."""
    if "tasks" in state:
        return state["tasks"]

    raw_tasks = _fetch_project_tasks(story_id)
    tasks = []
    for t in raw_tasks:
        tasks.append(
            {
                "id": t.get("id", ""),
                "subject": t.get("title", ""),
                "description": t.get("description", ""),
                "status": "pending",
                "subtasks": [],
            }
        )
    state["tasks"] = tasks
    return tasks


def _find_task_by_id(tasks: list[dict], task_id: str) -> dict | None:
    """Find a task in the list by id."""
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


def validate(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Validate a PreToolUse TaskCreate event.

    During task-create phase with a story_id set:
    - Requires metadata.parent_task_id and metadata.parent_task_title
    - Validates parent_task_id exists in project tasks
    - Validates parent_task_title matches
    - Records subtask mapping on success

    Returns ("allow", "") or ("block", reason).
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    phase = state.get("phase", "")
    if phase != "task-create":
        return "allow", ""

    story_id = state.get("story_id")
    if not story_id:
        return "allow", ""

    tool_input = hook_input.get("tool_input", {})
    metadata = tool_input.get("metadata", {})

    if not metadata:
        return (
            "block",
            "Blocked: TaskCreate requires metadata with 'parent_task_id' and 'parent_task_title'. "
            "Add metadata: {\"parent_task_id\": \"<task-id>\", \"parent_task_title\": \"<task-title>\"}.",
        )

    parent_task_id = metadata.get("parent_task_id")
    parent_task_title = metadata.get("parent_task_title")

    if not parent_task_id:
        return (
            "block",
            "Blocked: TaskCreate metadata missing 'parent_task_id'. "
            "Add the project task ID to metadata.",
        )

    if not parent_task_title:
        return (
            "block",
            "Blocked: TaskCreate metadata missing 'parent_task_title'. "
            "Add the project task title to metadata.",
        )

    # Ensure tasks cache is populated (uses subprocess on first call)
    def _cache_and_validate(s: dict) -> None:
        _ensure_tasks_cache(s, story_id)

    store.update(_cache_and_validate)

    # Re-load state with cached tasks
    state = store.load()
    tasks = state.get("tasks", [])

    parent_task = _find_task_by_id(tasks, str(parent_task_id))
    if not parent_task:
        task_ids = [t["id"] for t in tasks]
        return (
            "block",
            f"Blocked: parent_task_id '{parent_task_id}' not found in project tasks. "
            f"Available task IDs: {task_ids}.",
        )

    if parent_task["subject"] != parent_task_title:
        return (
            "block",
            f"Blocked: parent_task_title mismatch. Expected '{parent_task['subject']}', "
            f"got '{parent_task_title}'.",
        )

    # Validation passed — record subtask
    subject = tool_input.get("subject", "")
    description = tool_input.get("description", "")

    def _record_subtask_and_maybe_advance(s: dict) -> None:
        for t in s.get("tasks", []):
            if t["id"] == str(parent_task_id):
                subtask = {
                    "id": len(t["subtasks"]) + 1,
                    "subject": subject,
                    "description": description,
                    "status": "pending",
                }
                t["subtasks"].append(subtask)
                break

        # Auto-advance when all project tasks have at least one subtask
        all_covered = all(len(t.get("subtasks", [])) > 0 for t in s.get("tasks", []))
        if all_covered and s.get("phase") == "task-create":
            if s.get("tdd"):
                s["phase"] = "write-tests"
            else:
                s["phase"] = "write-code"

    store.update(_record_subtask_and_maybe_advance)
    return "allow", ""


def validate_completed(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Handle TaskCompleted event — update subtask status to completed.

    If all subtasks under a parent are completed, mark the parent as completed too.
    Always returns ("allow", "") — never blocks task completion.
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    task_subject = hook_input.get("task_subject", "")
    if not task_subject:
        return "allow", ""

    def _update_status(s: dict) -> None:
        for task in s.get("tasks", []):
            for subtask in task.get("subtasks", []):
                if subtask["subject"] == task_subject and subtask["status"] == "pending":
                    subtask["status"] = "completed"
                    # Check if all subtasks are now completed
                    if all(st["status"] == "completed" for st in task["subtasks"]):
                        task["status"] = "completed"
                    return

    store.update(_update_status)
    return "allow", ""
