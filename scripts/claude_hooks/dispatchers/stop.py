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
from scripts.claude_hooks.guardrail.stoppage import StopGuard

HOOKS: list[type[Hook]] = [StopGuard]


@dataclass
class Stop:
    def run(self) -> None:
        for hook in HOOKS:

            hook().run()


if __name__ == "__main__":
    Stop().run()
