import re

from utils.hook_manager import Hook


class SkillInvocationGuardrail(Hook):
    def __init__(self):
        super().__init__()
        tool_input = self.input.tool_input

        if tool_input is None:
            return None

        self.skill = tool_input.get("skill")
        self.args = tool_input.get("args")

    def parse_args(self) -> tuple[str, str] | None:
        """Parse args string in format '<id> <status>'."""
        if not self.args:
            return None
        parts = self.args.strip().split()
        if len(parts) != 2:
            return None
        return parts[0], parts[1]

    def validate_args(self):
        """Validate args for a given skill. Blocks if invalid."""
        if self.skill != "mark":
            return None

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
