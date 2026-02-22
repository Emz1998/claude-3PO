import re
import json

from scripts.claude_hooks.utils.hook_manager import Hook  # type: ignore
from scripts.claude_hooks.lib.parallel_session import parallel_sessions
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore


class ImplementTriggerGuard(Hook):
    def __init__(self):
        super().__init__()
        self.load_test_data("user_prompt")
        self.sprint = Sprint.create()

    def parse_args(self) -> str | None:
        """Parse user prompt in format '/implement <story_id>'."""
        prompt = self.input.prompt

        if prompt is None:
            print("No prompt found")
            return None

        if not prompt.startswith("/implement"):
            print("Invalid prompt")
            return None

        parts = prompt.strip().split(" ")

        if len(parts) != 2:
            print("Invalid prompt")
            return None
        return parts[1]

    def validate_args(self, story_id: str) -> tuple[bool, str | None]:
        """Validate args for a given skill. Blocks if invalid."""

        pattern = re.compile(r"^(US|TS|BG|SK)-\d{3}$")

        if not pattern.match(story_id):
            self.block(
                f"Invalid ID format: '{story_id}'. Expected format like: US-001 or TS-001 or BG-001 or SK-001"
            )

        # Args are valid, allow the skill to proceed
        return True, None

    def run(self) -> None:
        story_id = self.parse_args()

        if story_id is None:
            self.block("No story ID provided")
            return

        is_valid, error = self.validate_args(story_id)
        if error and not is_valid:
            self.block(error)

        ok, error = self.sprint.start_story(story_id)
        if not ok:
            print(error)
            return
        print(f"Started story {story_id}")
        print(self.sprint.render_context(story_id))


if __name__ == "__main__":
    ImplementTriggerGuard().run()
