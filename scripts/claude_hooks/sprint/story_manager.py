from typing import Literal


from scripts.claude_hooks.sprint.types import Bucket, SprintState
from scripts.claude_hooks.sprint.sprint_config import SprintConfig


class StoryManager:
    """Sprint manager for workflow orchestration."""

    def __init__(self, state: SprintState, config: SprintConfig):
        """Initialize the state manager.

        Args:
            state_path: Path to the state.json file
        """
        self._state = state
        self._config = config

    # ----------------------------------------

    @property
    def pending_stories(self) -> list[str]:
        """Get stories not yet ready, in progress, or completed."""
        stories = self._state.stories
        exclude = (
            set(stories.in_progress) | set(stories.completed) | set(self.ready_stories)
        )

        all_stories = self._config.sprint.get_story_ids()
        return [s for s in all_stories if s not in exclude]

    @property
    def ready_stories(self) -> list[str]:
        """Get stories whose deps are met and aren't already started or done."""
        stories = self._state.stories
        exclude = set(stories.in_progress) | set(stories.completed)
        sprint = self._config.sprint

        candidates = sprint.get_stories_without_deps()
        for story_id in sprint.get_stories_with_deps():
            story = sprint.find_story(story_id)
            if story and all(dep in stories.completed for dep in story.depends_on):
                candidates.append(story_id)

        return [s for s in candidates if s not in exclude]

    # ----------------------------------------
    ## Resolvers

    def resolve(self) -> None:
        """Resolve the current story.

        Returns:
            The current story
        """
        stories = self._state.stories
        stories.ready = self.ready_stories
        stories.pending = self.pending_stories
        self._state.stories = stories

    # ----------------------------------------
    ## Status Markers

    def mark_story(
        self, story_id: str, status: Literal["ready", "in_progress", "completed"]
    ) -> tuple[bool, str]:
        """Transition a story: pending->ready->in_progress->completed."""
        stories = self._state.stories

        if status == "ready":
            if story_id in stories.ready:
                return False, f"Story '{story_id}' is already ready"
            if story_id in stories.in_progress or story_id in stories.completed:
                return False, f"Story '{story_id}' cannot move to ready"
            if story_id not in stories.pending:
                return False, f"Story '{story_id}' is not pending"
            stories.pending.remove(story_id)
            stories.ready.append(story_id)
            self._state.stories = stories
            return True, f"Story '{story_id}' marked as ready"

        if status == "in_progress":
            if story_id in stories.in_progress:
                return False, f"Story '{story_id}' is already in progress"
            if story_id in stories.completed:
                return False, f"Story '{story_id}' is already completed"
            if story_id not in stories.ready:
                return False, f"Story '{story_id}' must be ready before starting"
            stories.ready.remove(story_id)
            stories.in_progress.append(story_id)
            self._state.current_story = story_id
            self._state.stories = stories
            # Init task bucket for stories with tasks
            story = self._config.sprint.find_story(story_id)
            if story and story.tasks and story_id not in self._state.tasks:
                self._state.tasks[story_id] = Bucket()
            return True, f"Story '{story_id}' marked as in progress"

        if story_id not in stories.in_progress:
            return False, f"Story '{story_id}' must be in progress before completing"
        stories.in_progress.remove(story_id)
        stories.completed.append(story_id)
        self._state.stories = stories
        self.resolve()
        return True, f"Story '{story_id}' marked as completed"
