"""PostToolUse handler — blocks tools if no task is in progress."""

from pathlib import Path
from typing import Any

from workflow.hook import Hook
from workflow.sprint import Sprint
from workflow.lib.context_injector import ContextInjector


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "reminders"

REMINDERS_MAP = {
    ("skill", "code"): "phase_reminder.md",
    "coding_phase_reminder": "coding_phase_reminder.md",
}


def send_reminder(reminder_name: str, **kwargs: Any) -> str:
    context_injector = ContextInjector(TEMPLATE_DIR)
    placeholder_exists = context_injector.placeholder_exists(f"{reminder_name}.md")
    if not placeholder_exists:
        raise ValueError(f"No placeholder found in {reminder_name}.md")
    template = context_injector.render(f"{reminder_name}.md", **kwargs)
    return template
