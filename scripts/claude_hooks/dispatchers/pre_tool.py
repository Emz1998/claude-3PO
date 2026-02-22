#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any, Union, TypedDict
import json
import re

from scripts.claude_hooks.utils.hook_manager import Hook
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.guardrail.workflow import Workflow
from scripts.claude_hooks.guardrail.phase_guard import PhaseGuard

HOOKS: list[type[Hook]] = [Workflow, PhaseGuard]


@dataclass
class PreToolUse(Hook):
    def __init__(self):
        super().__init__()
        self.load_test_data("PostToolUse", "Skill")

    def run(self) -> None:
        if self.input.hook_event_name != "PreToolUse":
            print(f"Skipping {self.input.hook_event_name} hook")
            return

        for hook in HOOKS:

            hook().run()


if __name__ == "__main__":
    PreToolUse().run()
