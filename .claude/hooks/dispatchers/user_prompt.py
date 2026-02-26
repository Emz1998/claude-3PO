#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass

from scripts.claude_hooks.utils.hook import Hook
from scripts.claude_hooks.entry_point.build import BuildEntryPoint
from scripts.claude_hooks.guardrail.implement_trigger import ImplementTriggerGuard

HOOKS: list = [BuildEntryPoint, ImplementTriggerGuard]


@dataclass
class UserPrompt:
    def __init__(self):
        self.input = Hook._read_stdin()

    def run(self) -> None:
        hook_event_name = self.input.get("hook_event_name")
        if hook_event_name != "UserPromptSubmit":
            print(f"Skipping {hook_event_name} hook")
            return

        for hook in HOOKS:
            hook(hook_input=self.input).run()


if __name__ == "__main__":
    user_prompt = UserPrompt()
    user_prompt.run()
