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

HOOKS: list[type[Hook]] = [Workflow]


@dataclass
class PreToolUse:
    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    def run_with_test(self) -> None:
        for hook in HOOKS:
            hook().load_test_data("PreToolUse", self.tool_name)
            hook().run()

    def run(self) -> None:
        for hook in HOOKS:
            hook().run()


if __name__ == "__main__":
    PreToolUse("read").run_with_test()
