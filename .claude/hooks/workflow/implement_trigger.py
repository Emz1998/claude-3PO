"""UserPromptSubmit handler — intercepts /implement and starts a story."""

import re
from typing import Any

from workflow.hook import Hook, UserPromptSubmit
from workflow.sprint import Sprint
from workflow.workflow_gate import activate_workflow


class ImplementTrigger:
    def __init__(self):
        self._hook = Hook[UserPromptSubmit]().create()
        self._sprint = Sprint.create()
        activate_workflow()

    @staticmethod
    def parse_prompt(prompt: str) -> tuple[str, str]:
        parts = prompt.strip().split(" ")
        if len(parts) != 2:
            raise ValueError("Args shouldnt be more than 1")
        return parts[0], parts[1]

    @property
    def story_id(self) -> str:
        _, story_id = self.parse_prompt(self._hook.input.prompt)
        return story_id

    def validate_prompt(self) -> bool:
        return self._hook.input.prompt.startswith("/implement")

    @staticmethod
    def validate_story_id(story_id: str) -> bool:
        pattern = re.compile(r"^(US|TS|BG|SK)-\d{3}$")
        return pattern.match(story_id) is not None

    def run(self) -> None:
        valid_prompt = self.validate_prompt()
        if not valid_prompt:
            self._hook.block("Invalid prompt")

        valid_story_id = self.validate_story_id(self.story_id)
        if not valid_story_id:
            self._hook.block("Invalid story ID")

        ok, error = self._sprint.start_story(self.story_id)
        if not ok:
            self._hook.block(error or "Failed to start story")

        self._hook.success_response(f"{self._sprint.render_context(self.story_id)}")


if __name__ == "__main__":
    implement_trigger = ImplementTrigger()
    implement_trigger.run()
