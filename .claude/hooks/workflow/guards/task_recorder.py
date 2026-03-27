"""task_recorder.py — PostToolUse TaskCreate recorder.

Appends a JSON line to TMPDIR/task_tracker.jsonl for every TaskCreate call.
"""

import json
import os
from pathlib import Path


def _default_tracker_path() -> Path:
    state_path = os.environ.get("GUARDRAIL_STATE_PATH")
    base = Path(state_path).parent if state_path else Path(__file__).resolve().parent.parent
    return base / "task_tracker.jsonl"


def record(hook_input: dict, tracker_path: Path | None = None) -> tuple[str, str]:
    """Record a TaskCreate tool call to the JSONL tracker.

    Always returns ("allow", "") — PostToolUse cannot block.
    """
    path = tracker_path or _default_tracker_path()
    tool_input = hook_input.get("tool_input", {})
    tool_response = hook_input.get("tool_response", {})
    task = tool_response.get("task", {})

    entry = {
        "id": str(task.get("id", "")),
        "subject": tool_input.get("subject", ""),
        "description": tool_input.get("description", ""),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return "allow", ""
