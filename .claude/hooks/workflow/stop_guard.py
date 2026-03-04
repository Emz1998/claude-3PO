"""Stop handler — blocks stoppage when the current story is not completed."""

import sys
from typing import Any

from workflow.hook import Hook, Stop
from workflow.sprint import Sprint
from workflow.workflow_gate import check_workflow_gate


class StopGuard:
    def __init__(self):
        self._hook = Hook[Stop]().create()
        self._is_workflow_active = check_workflow_gate()
        self._sprint = Sprint.create()

    @property
    def check_story_completion(self) -> tuple[bool, str]:
        current_story = self._sprint.state.current_story

        return (
            current_story in self._sprint.state.stories.completed,
            f"Story '{current_story}' is not completed. ",
        )

    def run(self) -> None:
        if not self._is_workflow_active:
            return
        is_completed, reason = self.check_story_completion
        if not is_completed:
            self._hook.block(reason)


if __name__ == "__main__":
    StopGuard().run()
