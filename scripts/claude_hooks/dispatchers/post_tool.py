#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any, Type
import json
import re
from dataclasses import fields, dataclass

from scripts.claude_hooks.utils.hook_manager import Hook  # type: ignore
from scripts.claude_hooks.recorder.hook_recorder import PhaseRecorder

HOOKS: list[type[Hook]] = [PhaseRecorder]


class PostToolUse(Hook):
    def __init__(self):
        super().__init__()
        self.load_test_data("PostToolUse", "Skill")

    def run(self) -> None:
        if self.input.hook_event_name != "PostToolUse":
            print(f"Skipping {self.input.hook_event_name} hook")
            return


if __name__ == "__main__":
    PostToolUse().run()
