"""Bash guard — blocks git push / gh pr create before all workflow phases are complete."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

BLOCKED_PATTERNS = [r"\bgit\s+push\b", r"\bgh\s+pr\s+create\b"]


def validate(hook_input: dict, state_path: Path | None = None) -> tuple[str, str]:
    """Validate a Bash tool invocation against the current workflow state.

    Returns ("allow", "") or ("block", reason).
    """
    command = hook_input.get("tool_input", {}).get("command", "")

    # Only care about blocked patterns
    if not any(re.search(p, command) for p in BLOCKED_PATTERNS):
        return "allow", ""

    path = state_path or DEFAULT_STATE_PATH
    store = StateStore(path)
    state = store.load()

    if not state.get("workflow_active", False):
        return "allow", ""

    phases: list[dict] = state.get("phases", [])
    incomplete = [p["name"] for p in phases if p["status"] != "completed"]

    if not incomplete:
        return "allow", ""

    reason = f"Cannot push before all workflow phases are completed. Incomplete: {', '.join(incomplete)}"
    return "block", reason
