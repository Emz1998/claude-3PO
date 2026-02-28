"""PostToolUse handler — records phase transitions after tool use."""

from typing import Any

from scripts.claude_hooks.constants import PHASES, CODING_PHASES
from scripts.claude_hooks.models import PostToolUse, Skill
from scripts.claude_hooks.state_store import StateStore
from scripts.claude_hooks.paths import ProjectPaths
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import check_workflow_gate


def handle(hook_input: dict[str, Any]) -> None:
    """Session recorder handler."""
    if not check_workflow_gate():
        return
    hook = PostToolUse(**hook_input)
    if not isinstance(hook.tool_input, Skill):
        return

    skill = hook.tool_input.skill
    if skill is None:
        return

    sprint = Sprint.create()
    paths = ProjectPaths(sprint.current_id, hook.session_id or "")
    state = StateStore(paths.current_session_path / "state.json")

    if skill in PHASES:
        state.set("recent_phase", skill)
    elif skill in CODING_PHASES:
        state.set("recent_coding_phase", skill)
    else:
        print(f"Invalid phase name: {skill}", flush=True)
