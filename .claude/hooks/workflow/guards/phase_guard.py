"""Phase order guard — validates Skill tool invocations against the workflow phase sequence."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

# Maps skill name → phase name (phase skills that must follow the workflow order)
SKILL_TO_PHASE: dict[str, str] = {
    "explore":     "explore",
    "decision":    "decision",
    "plan":        "plan",
    "write-tests": "write-tests",
    "write-code":  "write-code",
    "validate":    "validate",
    "pr-create":   "pr-create",
}

PHASE_ORDER = [
    "explore",
    "decision",
    "plan",
    "write-tests",
    "write-code",
    "validate",
    "pr-create",
]


def validate(hook_input: dict, state_path: Path | None = None) -> tuple[str, str]:
    """Validate a Skill tool invocation against the current phase order.

    Returns ("allow", "") or ("block", reason).
    Side effect: sets the matching phase to "in_progress" on allow.
    """
    skill_name = hook_input.get("tool_input", {}).get("skill", "")
    phase_name = SKILL_TO_PHASE.get(skill_name)

    # Unknown skills are not workflow-phase skills — let them through
    if phase_name is None:
        return "allow", ""

    path = state_path or DEFAULT_STATE_PATH
    store = StateStore(path)
    state = store.load()
    phases = state.get("phases", [])

    # task-manager prerequisite: explore requires task_manager_completed = True
    if phase_name == "explore" and not state.get("task_manager_completed"):
        return "block", "task-manager agent must complete before /explore. Launch the task-manager agent first."

    phase_map = {p["name"]: p for p in phases}
    target = phase_map.get(phase_name)
    if target is None:
        return "block", f"Phase '{phase_name}' not found in state"

    # Already in_progress or completed — allow re-entry (idempotent)
    if target["status"] in ("in_progress", "completed"):
        return "allow", ""

    # Check all prior phases are completed
    target_idx = PHASE_ORDER.index(phase_name)
    for prior_name in PHASE_ORDER[:target_idx]:
        prior = phase_map.get(prior_name, {})
        if prior.get("status") != "completed":
            return "block", f"Phase '{prior_name}' must be completed, before '{phase_name}'"

    # Transition to in_progress
    def _activate(s: dict) -> None:
        for p in s.get("phases", []):
            if p["name"] == phase_name:
                p["status"] = "in_progress"
                break

    store.update(_activate)
    return "allow", ""
