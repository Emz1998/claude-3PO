"""PostToolUse handler — records phase transitions after tool use."""

from typing import Any

from workflow.hook import Hook, PostToolUse
from workflow.constants import PHASES, CODING_PHASES
from workflow.phase_guard import PHASE_FLAG
from workflow.workflow_gate import check_workflow_gate


class PhaseRecorder(PostToolUse):
    def __init__(self):
        self._hook = Hook[PostToolUse]().create()
        self._is_workflow_active = check_workflow_gate()
        self._skill = self._hook.input.tool_input.skill

    def run(self) -> None:
        if not self._is_workflow_active:
            return
        skill = self._skill
        if skill in PHASES:
            PHASE_FLAG.update("recent_phase", skill)
            return
        if skill in CODING_PHASES:
            PHASE_FLAG.update("recent_coding_phase", skill)
            return
        self._hook.block(f"Invalid phase name: {skill}")
