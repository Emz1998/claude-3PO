#!/usr/bin/env python3
"""UserPromptSubmit hook to detect /implement workflow trigger.

When user submits a prompt containing /implement:
- Activates the implement workflow state machine
- Resets to IMPLEMENT_ACTIVE state
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json  # type: ignore
from workflow.implement_state import activate_workflow  # type: ignore

# Command patterns that activate the implement workflow
IMPLEMENT_COMMANDS = {"/implement", "/build"}


def extract_command(prompt: str) -> str | None:
    """Extract slash command from user prompt."""
    prompt_stripped = prompt.strip()
    # Match /command at start of prompt
    match = re.match(r"^(/[\w:-]+)", prompt_stripped)
    if match:
        return match.group(1).lower()
    return None


def main() -> None:
    """Check if user typed /implement command and activate workflow."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "UserPromptSubmit":
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    command = extract_command(prompt)
    if command and command in IMPLEMENT_COMMANDS:
        # Activate the workflow (resets state to IMPLEMENT_ACTIVE)
        activate_workflow()

    sys.exit(0)


if __name__ == "__main__":
    main()
