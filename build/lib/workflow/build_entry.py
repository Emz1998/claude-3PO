"""UserPromptSubmit handler — intercepts /build and prepares parallel implement prompts."""

from typing import Any

from workflow.hook import Hook, UserPromptSubmit
from workflow.state_store import StateStore
from workflow.sprint.sprint import Sprint
from workflow.workflow_gate import activate_workflow
from workflow.paths import ProjectPaths
from workflow.lib.parallel_session import parallel_sessions


class BuildEntry:
    def __init__(self):
        self._hook = Hook[UserPromptSubmit]().create()
        self._sprint = Sprint.create()
        self._state = StateStore(
            state_path=self.get_project_paths().current_session_path
        )
        activate_workflow()

    def get_project_paths(self) -> ProjectPaths:
        return ProjectPaths(
            sprint_id=self._sprint.state.sprint_id,
            session_id=self._hook.input.session_id,
        )

    def validate_prompt(self) -> bool:
        return self._hook.input.prompt.startswith("/build")

    @property
    def prompts(self) -> list[str]:
        args = self._sprint.story.ready_stories
        print("Ready stories: ", args)

        prompts = [
            f"/implement {story_id} --worktree {self._sprint.state.sprint_id}/{story_id}"
            for story_id in args
        ]
        return prompts

    @staticmethod
    def launch_sessions(prompts: list[str]) -> None:
        # parallel_sessions(prompts)
        print("Launching sessions: ", "\n".join(prompts))

    def run(self) -> None:
        valid_prompt = self.validate_prompt()
        if not valid_prompt:
            return
        self.launch_sessions(self.prompts)


if __name__ == "__main__":
    build_entry = BuildEntry()
    build_entry.run()
