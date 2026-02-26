#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any, Type
import json
import re
from dataclasses import fields, dataclass

from scripts.claude_hooks.utils.hook import Hook
from scripts.claude_hooks.recorder.hook_recorder import SessionRecorder
from scripts.claude_hooks.reminders.log_reminder import LogReminder

HOOKS: list = [SessionRecorder, LogReminder]


class PostToolUse:
    def __init__(self):
        self.input = Hook._read_stdin()

    def run(self) -> None:
        if self.input.get("hook_event_name") != "PostToolUse":
            return

        for hook in HOOKS:
            hook(hook_input=self.input).run()


if __name__ == "__main__":
    PostToolUse().run()
