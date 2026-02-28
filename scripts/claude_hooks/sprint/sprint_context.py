#!/usr/bin/env python3
"""Context rendering for sprint stories."""

from pathlib import Path
from typing import Any
import json

from scripts.claude_hooks.sprint.sprint_config import SprintConfig, Story  # type: ignore
from scripts.claude_hooks.sprint.types import SprintState  # type: ignore
from scripts.claude_hooks.context_injector import ContextInjector  # type: ignore

TEMPLATE_DIR = Path(__file__).resolve().parent / "context"
IMPORTANT_NOTE = "Follow the plan. Do not deviate without approval."
BUG_ATTRS = ("severity", "found_in", "whats_broken", "expected", "actual", "reproduce")


class SprintContext:
    """Renders story context templates based on story type."""

    def __init__(self, config: SprintConfig, template_dir: Path = TEMPLATE_DIR):
        self._config = config
        self._injector = ContextInjector(template_dir)

    def render(self, state: SprintState, story_id: str | None = None) -> str:
        story_id = story_id or state.current_story
        if not story_id and state.stories.ready:
            story_id = state.stories.ready[0]
        if not story_id:
            return ""
        story = self._config.sprint.find_story(story_id)
        if not story:
            return ""
        template = f"{story.type.lower().replace(' ', '_')}.md"
        if not self._injector.template_exists(template):
            return ""
        return self._injector.render(template, **_build_kwargs(story))


def _build_kwargs(story: Story) -> dict[str, str]:
    base: dict[str, str] = {
        "story_title": story.title,
        "depends_on": ", ".join(story.depends_on) or "None",
        "blocked_by": ", ".join(story.blocked_by) or "None",
        "points": str(story.points),
    }
    if story.type == "Spike":
        base["timebox"] = story.timebox or "N/A"
        base["deliverables"] = "\n".join(f"- {d}" for d in story.deliverables) or "None"
        return base
    if story.type == "Bug":
        for attr in BUG_ATTRS:
            base[attr] = getattr(story, attr, "Unknown")
    base["priority"] = story.priority or "Medium"
    base["tasks_context"] = _render_tasks(story)
    base["important_note"] = IMPORTANT_NOTE
    return base


def _render_tasks(story: Story) -> str:
    if not story.tasks:
        return "No tasks defined."
    return "\n".join(
        f"- [{t.status}] **{t.id}**: {t.title} ({t.complexity})" for t in story.tasks
    )
