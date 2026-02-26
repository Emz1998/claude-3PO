from typing import Any
import json

from scripts.claude_hooks.utils.hook import UserPromptSubmit
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.lib.parallel_session import parallel_sessions
from scripts.claude_hooks.project.paths import ProjectPaths
from scripts.claude_hooks.utils.state_store import StateStore


class BuildEntryPoint:
    def __init__(self, hook_input: dict[str, Any]):
        self._hook = UserPromptSubmit(**hook_input)
        self.sprint = Sprint.create()
        project_paths = ProjectPaths(
            sprint_id=self.sprint.state.sprint_id,
            session_id=self._hook.session_id,
        )
        session_path = project_paths.current_session_path / "state.json"
        self._state = StateStore(state_path=session_path)

    def record_activation(self) -> None:
        self._state.set("build_active", True)
        self._state.save()

    def run(self) -> None:
        if self._hook.prompt is None:
            print("Prompt is None")
            return
        if not self._hook.prompt.startswith("/build"):
            return
        args = self.sprint.story.ready_stories
        prompts = [
            f"/implement {story_id} --worktree {self.sprint.state.sprint_id}/{story_id}"
            for story_id in args
        ]

        print("Build Entry Point successful")
        # parallel_sessions(prompts)
