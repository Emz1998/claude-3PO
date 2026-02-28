#!/usr/bin/env python3
"""Sprint facade — thin orchestrator over story, task, and context modules."""

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from scripts.claude_hooks.sprint.types import SprintState  # type: ignore
from scripts.claude_hooks.sprint.sprint_config import SprintConfig  # type: ignore
from scripts.claude_hooks.sprint.sprint_context import SprintContext  # type: ignore
from scripts.claude_hooks.sprint.story_manager import StoryManager  # type: ignore
from scripts.claude_hooks.sprint.task_manager import TaskManager  # type: ignore
from scripts.claude_hooks.state_store import StateStore  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SPRINTS_DIR = PROJECT_ROOT / "project/sprints"
HISTORY_PATH = SPRINTS_DIR / "history.jsonl"
DEFAULT_SPRINT = "SPRINT-001"
STATE_FILENAME = "state.json"
CONFIG_FILENAME = "overview/sprint.json"


@dataclass
class Sprint:
    """Single entry point for sprint lifecycle."""

    config: SprintConfig
    store: StateStore
    state: SprintState
    story: StoryManager
    task: TaskManager
    context: SprintContext

    @staticmethod
    def _resolve_paths() -> tuple[Path, Path]:
        """Resolve sprint state path. Defaults to SPRINT-001."""
        last_sprint_data = StateStore.latest_from_history(HISTORY_PATH)
        if last_sprint_data is None:
            return (
                SPRINTS_DIR / DEFAULT_SPRINT / STATE_FILENAME,
                SPRINTS_DIR / DEFAULT_SPRINT / CONFIG_FILENAME,
            )
        last_sprint_id = last_sprint_data.get("sprint_id")
        if last_sprint_id is None:
            raise ValueError("Last sprint ID is not set")
        next_sprint = SprintState.next_sprint_id(last_sprint_id)
        return (
            SPRINTS_DIR / next_sprint / STATE_FILENAME,
            SPRINTS_DIR / next_sprint / CONFIG_FILENAME,
        )

    @classmethod
    def create(
        cls, state_path: Path | None = None, config_path: Path | None = None
    ) -> "Sprint":

        if state_path is None:
            state_path, _ = cls._resolve_paths()
        if config_path is None:
            _, config_path = cls._resolve_paths()

        config = SprintConfig(config_path)
        store = StateStore(state_path, default_state=SprintState().to_dict())
        state = SprintState.from_dict(store.load())
        sprint = cls(
            config=config,
            store=store,
            state=state,
            story=StoryManager(state, config),
            task=TaskManager(state, config),
            context=SprintContext(config),
        )
        sprint.resolve()
        return sprint

    # -- persistence --

    def save(self) -> None:
        self.store.save(self.state.to_dict())

    # -- story commands --

    def start_story(self, story_id: str) -> tuple[bool, str]:
        ok, msg = self.story.mark_story(story_id, "in_progress")
        if ok:
            self.task.resolve_tasks(story_id)
            self.save()
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
        print(f"Completing sprint {self.state.sprint_id}")
        self.state.status = "completed"
        self.state.metadata.updated_at = datetime.now().isoformat()

        self.save()
        self.store.archive(HISTORY_PATH)
        return True

    @property
    def current_id(self) -> str:
        return self.state.sprint_id
