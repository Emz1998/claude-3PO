#!/usr/bin/env python3
"""UserPromptSubmit handler for workflow activation and dry run.

Handles:
- Workflow activation via /implement command
- Workflow deactivation via /deactivate-workflow
- Dry run mode via /dry-run
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore


VALID_IMPLEMENT_PATTERN = r"MS-\d{3}$"


class UserPromptHandler:
    """Handler for UserPromptSubmit events."""

    def __init__(self):
        """Initialize the handler."""
        self._state = get_manager()

    def is_valid_implement_args(self, prompt: str) -> bool:
        """Validate /implement command arguments.

        Args:
            prompt: The prompt text

        Returns:
            True if valid or not /implement command
        """
        parts = prompt.split()
        if "/implement" not in parts:
            return True
        if len(parts) != 2:
            return False
        if parts[0] != "/implement":
            return False
        if not re.match(VALID_IMPLEMENT_PATTERN, parts[1]):
            return False
        return True

    def is_implement_triggered(self, prompt: str) -> bool:
        """Check if /implement command is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if /implement is triggered
        """
        return "/implement" in prompt.split()

    def is_deactivate_triggered(self, prompt: str) -> bool:
        """Check if /deactivate-workflow is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if deactivate is triggered
        """
        return "/deactivate-workflow" in prompt

    def is_dry_run_triggered(self, prompt: str) -> bool:
        """Check if /dry-run is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if dry run is triggered
        """
        return "/dry-run" in prompt

    def handle_implement(self, prompt: str) -> None:
        """Handle /implement command.

        Args:
            prompt: The prompt text
        """
        if not self.is_valid_implement_args(prompt):
            print(f"Invalid args: {prompt}", file=sys.stderr)
            sys.exit(2)
        self._state.activate_workflow()

        # Check for pending validation and set flag
        try:
            from validators.criteria_validator import get_pending_validation_type  # type: ignore
            validation_type = get_pending_validation_type()
            if validation_type:
                self._state.set("pending_validation", validation_type)
                # Clear the needs_*_validation flags
                self._state.delete("needs_ac_validation")
                self._state.delete("needs_sc_validation")
                self._state.delete("needs_epic_sc_validation")
        except ImportError:
            pass

    def handle_deactivate(self) -> None:
        """Handle /deactivate-workflow command."""
        self._state.deactivate_workflow()

    def handle_dry_run(self) -> None:
        """Handle /dry-run command."""
        if self._state.is_dry_run_active():
            # Reset deliverables for next dry run iteration
            self._state.reset_deliverables_status()
        else:
            # Start fresh dry run
            self._state.reset()
            self._state.activate_workflow()
            self._state.activate_dry_run()

    def run(self, hook_input: dict) -> None:
        """Run the handler against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        hook_event_name = hook_input.get("hook_event_name", "")
        if hook_event_name != "UserPromptSubmit":
            sys.exit(0)

        prompt = hook_input.get("prompt", "")
        if not prompt:
            sys.exit(0)

        # Handle deactivate first (can happen while workflow is active)
        if self.is_deactivate_triggered(prompt):
            self.handle_deactivate()
            return

        # Handle dry run
        if self.is_dry_run_triggered(prompt):
            self.handle_dry_run()
            return

        # Handle implement
        if self.is_implement_triggered(prompt):
            self.handle_implement(prompt)
            return


def handle_user_prompt(hook_input: dict) -> None:
    """Handle a UserPromptSubmit event.

    Args:
        hook_input: The hook input dictionary
    """
    handler = UserPromptHandler()
    handler.run(hook_input)


def main() -> None:
    """Main entry point for the handler."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    handler = UserPromptHandler()
    handler.run(hook_input)


if __name__ == "__main__":
    main()
