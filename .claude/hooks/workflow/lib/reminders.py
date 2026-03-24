"""PostToolUse handler — blocks tools if no task is in progress."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
from typing import Any

from workflow.hook import Hook
from workflow.lib.file_manager import FileManager
from workflow.models.hook_input import PreToolUseInput, PostToolUseInput
from workflow.config import get as cfg
from workflow.workflow_gate import check_workflow_gate
from workflow.workflow_log import log

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "reminders"

# Build tuple-keyed dict from config list
# Qualifier is either "agent" (for Agent tool) or "skill" (for Skill tool)
_reminder_entries = cfg("reminders.map", [])
REMINDERS_MAP = {
    (
        entry["event"],
        entry["tool"],
        entry.get("agent") or entry.get("skill"),
    ): entry["template"]
    for entry in _reminder_entries
}

REMINDERS_DIR = Path(cfg("paths.templates_reminders"))


class Reminders:
    def __init__(self, hook_input: PreToolUseInput | PostToolUseInput):
        self._hook_input = hook_input
        self._file_manager = FileManager(TEMPLATE_DIR, lock=False)

    def load_template(self, reminder_name: str) -> str:
        return self._file_manager.load(reminder_name) or ""

    def send_reminder(self, hook_event_name: str, reminder: str) -> None:
        Hook.advanced_output(
            {
                "hookSpecificOutput": {
                    "hookEventName": hook_event_name,
                    "additionalContext": reminder,
                }
            }
        )

    def run(self) -> None:
        if not check_workflow_gate():
            log("Reminders", "Skipped", "Workflow is not active")
            return

        hook_event_name = self._hook_input.hook_event_name
        tool_name = self._hook_input.tool_name

        qualifier = None
        if tool_name == "Agent":
            qualifier = self._hook_input.tool_input.subagent_type or None
        elif tool_name == "Skill":
            qualifier = self._hook_input.tool_input.skill or None

        reminder = REMINDERS_MAP.get((hook_event_name, tool_name, qualifier))  # type: ignore
        if not reminder:
            log("Reminders", "Skipped", "No reminder found")
            return
        reminder_path = REMINDERS_DIR / reminder
        reminder_text = reminder_path.read_text()
        self.send_reminder(hook_event_name, reminder_text)
        log(
            "Reminders",
            "Sent",
            f"Reminder '{reminder_text}' sent for {hook_event_name}",
        )


def main():
    stdin_input = Hook.read_stdin()
    if stdin_input.get("hook_event_name") == "PreToolUse":
        hook_input = PreToolUseInput.model_validate(stdin_input)
    else:
        hook_input = PostToolUseInput.model_validate(stdin_input)
    reminders = Reminders(hook_input)
    reminders.run()


if __name__ == "__main__":
    main()
