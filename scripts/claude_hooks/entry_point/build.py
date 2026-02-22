import re
import json

from scripts.claude_hooks.utils.hook_manager import Hook  # type: ignore
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore
from scripts.claude_hooks.lib.parallel_session import parallel_sessions


class BuildEntryPoint(Hook):
    def __init__(self):
        super().__init__()
        self.load_test_data("user_prompt")
        self.sprint = Sprint.create()

    def run(self) -> None:
        args = self.sprint.story.ready_stories
        prompts = [
            f"/implement {story_id} --worktree {self.sprint.state.sprint_id}/{story_id}"
            for story_id in args
        ]
        print(prompts)
        parallel_sessions(prompts)


if __name__ == "__main__":
    BuildEntryPoint().run()
