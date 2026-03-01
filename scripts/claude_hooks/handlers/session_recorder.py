"""PostToolUse handler — records phase transitions after tool use."""

from typing import Any

from scripts.claude_hooks.constants import PHASES, CODING_PHASES
from scripts.claude_hooks.models import PostToolUse, Skill
from scripts.claude_hooks.handlers.phase_guard import PHASE_FLAG
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

    if skill in PHASES:
        PHASE_FLAG.update("recent_phase", skill)
    elif skill in CODING_PHASES:
        PHASE_FLAG.update("recent_coding_phase", skill)
    else:
        print(f"Invalid phase name: {skill}", flush=True)
