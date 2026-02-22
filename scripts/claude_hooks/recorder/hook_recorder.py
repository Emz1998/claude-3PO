#!/usr/bin/env python3
"""Recorder for hook events."""

import sys
from pathlib import Path
from typing import Any

from scripts.claude_hooks.utils.hook_manager import Hook, StateStore

STATE_PATH = Path(".claude/hooks/state.json")


PHASES: list[str] = ["explore", "plan", "code" "push"]


CODING_PHASES: list[str] = ["log", "validate", "review"]


class PhaseRecorder(Hook):

    def __init__(self):
        super().__init__()
        self.load_test_data("PostToolUse", "Skill")
        self._state = StateStore(STATE_PATH)

    def record_coding_phase(self, skill: str) -> None:
        if skill not in CODING_PHASES:
            return

        self._state.set("recent_coding_phase", skill)
        print("Coding phase recorded")

    def record_main_phase(self, skill: str) -> None:
        if skill not in PHASES:
            return

        self._state.set("recent_phase", skill)
        print("Main phase recorded")

    def run(self) -> None:

        if self.input.tool_name != "Skill":
            print("Skill tool not invoked")
            return

        tool_input = self.input.tool_input
        if tool_input is None:
            print("No tool input found")
            return

        skill = tool_input.skill
        if skill is None:
            print("No skill found")
            return

        if skill not in PHASES and skill not in CODING_PHASES:
            print(f"Invalid phase name: {skill}")
            return

        self.record_coding_phase(tool_input.skill)
        self.record_main_phase(tool_input.skill)


if __name__ == "__main__":
    recorder = PhaseRecorder()
    recorder.run()
