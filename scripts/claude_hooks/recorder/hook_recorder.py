#!/usr/bin/env python3
"""Recorder for hook events. Records phase transitions after tool use."""

from typing import Any

from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.project.paths import ProjectPaths
from scripts.claude_hooks.utils.state_store import StateStore
from scripts.claude_hooks.utils.hook import PostToolUse, Skill


PHASES: list[str] = ["explore", "plan", "code", "push"]

CODING_PHASES: list[str] = ["mark", "validate", "commit"]


class SessionRecorder:

    def __init__(self, hook_input: dict[str, Any]):
        self._hook = PostToolUse(**hook_input)
        sprint = Sprint.create()
        self._paths = ProjectPaths(sprint.current_id, self._hook.session_id or "")
        self._state = StateStore(self._paths.current_session_path / "state.json")

    def run(self) -> None:
        if not isinstance(self._hook.tool_input, Skill):
            return

        skill = self._hook.tool_input.skill
        if skill is None:
            return

        if skill in PHASES:
            self._state.set("recent_phase", skill)
        elif skill in CODING_PHASES:
            self._state.set("recent_coding_phase", skill)
        else:
            print(f"Invalid phase name: {skill}", flush=True)
