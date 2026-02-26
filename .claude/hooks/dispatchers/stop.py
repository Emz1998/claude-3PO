#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any, Union, TypedDict
import json
import re

from scripts.claude_hooks.utils.hook import Hook

from scripts.claude_hooks.guardrail.stoppage import StopGuard

HOOKS: list = [StopGuard]


@dataclass
class Stop:
    def __init__(self):
        self.input = Hook._read_stdin()

    def run(self) -> None:
        for hook in HOOKS:

            hook(hook_input=self.input).run()


if __name__ == "__main__":
    Stop().run()
