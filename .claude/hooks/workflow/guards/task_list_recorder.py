"""task_list_recorder.py — PostToolUse TaskList recorder.

Writes the full tasks array from a TaskList response to TMPDIR/task_list_snapshot.json.
Overwrites on each call (latest snapshot wins).
"""

import json
import os
from pathlib import Path


def _default_snapshot_path() -> Path:
    state_path = os.environ.get("GUARDRAIL_STATE_PATH")
    base = Path(state_path).parent if state_path else Path(__file__).resolve().parent.parent
    return base / "task_list_snapshot.json"


def record(hook_input: dict, snapshot_path: Path | None = None) -> tuple[str, str]:
    """Record a TaskList tool response as a snapshot JSON file.

    Always returns ("allow", "") — PostToolUse cannot block.
    """
    path = snapshot_path or _default_snapshot_path()
    tool_response = hook_input.get("tool_response", {})
    tasks = tool_response.get("tasks", [])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tasks, ensure_ascii=False), encoding="utf-8")

    return "allow", ""
