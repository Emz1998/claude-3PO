#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass

from scripts.claude_hooks.utils.hook_manager import Hook
from scripts.claude_hooks.guardrail.workflow_trigger import WorkflowTriggerGuard

HOOKS: list[type[Hook]] = [WorkflowTriggerGuard]


@dataclass
class UserPrompt:
    def run(self) -> None:
        for hook in HOOKS:

            hook().run()


if __name__ == "__main__":
    UserPrompt().run()
