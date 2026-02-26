import re
from typing import Any

from scripts.claude_hooks.utils.hook import UserPromptSubmit
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore


class ImplementTriggerGuard:

    def __init__(self, hook_input: dict[str, Any]):
        self.hook_input = UserPromptSubmit(**hook_input)
        self.sprint = Sprint.create()

    def parse_args(self, prompt: str) -> str | None:
        """Parse user prompt in format '/implement <story_id>'."""

        parts = prompt.strip().split(" ")

        if len(parts) != 2:
            self.hook_input.block("Invalid prompt")
            return None
        return parts[1]

    def validate_args(self, story_id: str) -> tuple[bool, str | None]:
        """Validate args for a given skill. Blocks if invalid."""

        pattern = re.compile(r"^(US|TS|BG|SK)-\d{3}$")

        if not pattern.match(story_id):
            return (
                False,
                f"Invalid ID format: '{story_id}'. Expected format like: US-001 or TS-001 or BG-001 or SK-001",
            )

        # Args are valid, allow the skill to proceed
        return True, None

    def run(self) -> None:

        prompt = self.hook_input.prompt

        if prompt is None:
            print("No prompt found")
            return None

        if not prompt.startswith("/implement"):
            return

        story_id = self.parse_args(prompt)

        if story_id is None:
            self.hook_input.block("No story ID provided")
            return

        is_valid, error = self.validate_args(story_id)
        if error and not is_valid:
            self.hook_input.block(error)

        ok, error = self.sprint.start_story(story_id)
        if not ok:
            self.hook_input.block(error or "Failed to start story")
        print(f"Started story {story_id}\n")

        print(self.sprint.render_context(story_id), "\n")
