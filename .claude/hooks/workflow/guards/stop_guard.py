"""Stop guard — blocks Claude from stopping when workflow phases are incomplete."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


def validate(hook_input: dict, state_path: Path | None = None) -> tuple[str, str]:
    """Validate a Stop event against the current workflow state.

    Returns ("allow", "") or ("block", reason).
    """
    # Prevent infinite loop if stop hook itself triggered this
    if hook_input.get("stop_hook_active"):
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

    reason = f"Workflow incomplete. Phases not completed: {', '.join(incomplete)}"
    return "block", reason
