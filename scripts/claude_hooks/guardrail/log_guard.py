import re
import json

from scripts.claude_hooks.utils.hook_manager import Hook  # type: ignore


class LoggingGuard(Hook):
    def __init__(self):
        super().__init__()
        self.load_test_data("PreToolUse", "Skill")

    def parse_args(self) -> tuple[str, str] | None:
        """Parse args string in format '<id> <status>'."""
        if not self.input.tool_input:
            return None

        if not self.input.tool_input.args:
            return None

        parts = self.input.tool_input.args.strip().split()

        if len(parts) != 2:
            return None
        return parts[0], parts[1]

    def validate_args(self) -> tuple[bool, str | None]:
        """Validate args for a given skill. Blocks if invalid."""
        print(self.input.tool_input)
        if not self.input.tool_input:

            return False, "No tool input"

        if self.input.tool_input.skill != "log":
            return False, "Invalid skill"

        pattern = re.compile(r"^T-\d{3}$")
        statuses = ["in_progress", "completed"]

        parsed = self.parse_args()
        if parsed is None:
            self.block("Invalid args format. Expected: '<id> <status>'")

        item_id, status = parsed or ("", "")

        if not pattern.match(item_id):
            self.block(f"Invalid ID format: '{item_id}'. Expected format like: T001")

        if status not in statuses:
            self.block(
                f"Invalid status: '{status}'. Valid statuses: {', '.join(statuses)}"
            )

        # Args are valid, allow the skill to proceed
        return True, None

    def run(self) -> None:
        if self.input.hook_event_name != "PreToolUse":
            return

        if self.input.tool_input is None:
            return

        if self.input.tool_input.skill != "log":
            return

        is_valid, error = self.validate_args()
        if error is None:
            return
        if not is_valid:
            self.block(error)
            return

        print("args are valid")
