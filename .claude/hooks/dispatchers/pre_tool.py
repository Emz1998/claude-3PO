#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass

from scripts.claude_hooks.utils.hook import Hook
from scripts.claude_hooks.guardrail.phase_guard import PhaseGuard
from scripts.claude_hooks.guardrail.log_guard import LogGuard
from scripts.claude_hooks.guardrail.commit_guard import CommitGuard

HOOKS: list = [PhaseGuard, LogGuard, CommitGuard]


@dataclass
class PreToolUse:
    def __init__(self):
        self.input = Hook._read_stdin()

    def run(self) -> None:
        hook_event_name = self.input.get("hook_event_name")
        if hook_event_name != "PreToolUse":
            print(f"Skipping {hook_event_name} hook")
            return

        for hook in HOOKS:

            hook(hook_input=self.input).run()


if __name__ == "__main__":
    PreToolUse().run()
