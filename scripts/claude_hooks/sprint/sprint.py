#!/usr/bin/env python3
"""Sprint facade — thin orchestrator over story, task, and context modules."""

from dataclasses import dataclass
from pathlib import Path

from scripts.claude_hooks.sprint.types import SprintState  # type: ignore
from scripts.claude_hooks.sprint.sprint_config import SprintConfig  # type: ignore
from scripts.claude_hooks.sprint.sprint_context import SprintContext  # type: ignore
from scripts.claude_hooks.sprint.story_manager import StoryManager  # type: ignore
from scripts.claude_hooks.sprint.task_manager import TaskManager  # type: ignore
from scripts.claude_hooks.utils.state_store import StateStore  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_PATH = PROJECT_ROOT / "project/sprints/SPRINT-001/sprint-status.json"


@dataclass
class Sprint:
    """Single entry point for sprint lifecycle."""

    config: SprintConfig
    store: StateStore
    state: SprintState
    story: StoryManager
    task: TaskManager
    context: SprintContext

    @classmethod
    def create(
        cls, state_path: Path = STATE_PATH, config_path: Path | None = None
    ) -> "Sprint":
        config = SprintConfig(config_path) if config_path else SprintConfig()
        store = StateStore(state_path, default_state=SprintState().to_dict())
        state = SprintState.from_dict(store.load())
        return cls(
            config=config,
            store=store,
            state=state,
            story=StoryManager(state, config),
            task=TaskManager(state, config),
            context=SprintContext(config),
        )

    # -- persistence --

    def save(self) -> None:
        self.store.save(self.state.to_dict())

    # -- story commands --

    def start_story(self, story_id: str) -> tuple[bool, str]:
        ok, msg = self.story.mark_story(story_id, "in_progress")
        if ok:
            self.task.resolve_tasks(story_id)
            self.save()
        print(f"Failed to start story {story_id}")
        return ok, msg

    def complete_story(self, story_id: str) -> tuple[bool, str]:
        ok, msg = self.story.mark_story(story_id, "completed")
        if not ok:
            return ok, msg
        if self.state.current_story == story_id:
            self.state.current_story = ""
        self.save()
        return ok, msg

    # -- task commands --

    def start_task(self, task_id: str, story_id: str | None = None) -> tuple[bool, str]:
        ok, msg = self.task.mark_task(task_id, "in_progress", story_id)
        if ok:
            self.save()
        return ok, msg

    def complete_task(
        self, task_id: str, story_id: str | None = None
    ) -> tuple[bool, str]:
        ok, msg = self.task.mark_task(task_id, "completed", story_id)
        if ok:
            self.save()
        return ok, msg

    # -- resolve --

    def resolve(self) -> None:
        self.story.resolve()
        if self.state.current_story:
            self.task.resolve_tasks(self.state.current_story)
        self.save()

    # -- context --

    def render_context(self, story_id: str | None = None) -> str:
        return self.context.render(self.state, story_id)

    # -- sprint-level --

    def complete_sprint(self) -> bool:
        self.state.sprint_completed = True
        self.save()
        return True


if __name__ == "__main__":
    sprint = Sprint.create()
    sprint.complete_story("SK-002")
    sprint.start_task("T-001")
    print(f"Current story: {sprint.state.current_story}")
    print(f"Ready stories: {sprint.state.stories.ready}")
    print(f"Context:\n{sprint.render_context()}")
