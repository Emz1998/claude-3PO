import re

from utils.hook_manager import Hook
from


class StopGuard(Hook):
    def __init__(self):
        super().__init__()
        tool_input = self.input.tool_input

        if tool_input is None:
            return None

        self.reason = tool_input.get("reason")
