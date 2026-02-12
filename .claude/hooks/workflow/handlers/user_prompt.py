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
from config.unified_loader import get_triggers, can_bypass_from  # type: ignore
from core.state_manager import get_manager  # type: ignore
from release_plan.getters import get_current_tasks_ids, get_current_user_story  # type: ignore


class UserPromptHandler:
    """Handler for UserPromptSubmit events."""

    def __init__(self):
        """Initialize the handler."""
        self._state = get_manager()
        self._triggers = get_triggers()

    def _parse_task_ids(self, prompt: str) -> list[str]:
        """Parse task IDs from /implement command.

        Args:
            prompt: The prompt text

        Returns:
            List of task IDs, empty if no args or invalid format
        """
        cmd = self._triggers.implement.command
        parts = prompt.split()

        # No args case
        if len(parts) == 1 and parts[0] == cmd:
            return []

        # Single task or range
        if len(parts) >= 2 and parts[0] == cmd:
            rest = " ".join(parts[1:])
            # Check for range (T001 - T003)
            range_match = re.match(r"(T\d{3})\s*-\s*(T\d{3})$", rest)
            if range_match:
                start, end = range_match.groups()
                start_num = int(start[1:])
                end_num = int(end[1:])
                if start_num > end_num:
                    return []  # Invalid range
                return [f"T{str(i).zfill(3)}" for i in range(start_num, end_num + 1)]
            # Single task
            single_match = re.match(r"T\d{3}$", rest)
            if single_match:
                return [rest]

        return []

    def _validate_tasks_in_current(self, task_ids: list[str]) -> tuple[bool, str]:
        """Validate task IDs exist in current_tasks.

        Args:
            task_ids: List of task IDs to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not task_ids:
            return True, ""  # No args case, will use defaults

        current_tasks = get_current_tasks_ids()

        if not current_tasks:
            return False, "No current tasks available"

        invalid_tasks = [t for t in task_ids if t not in current_tasks]
        if invalid_tasks:
            return (
                False,
                f"Tasks not in current_tasks: {', '.join(invalid_tasks)}. "
                f"Available: {', '.join(current_tasks)}",
            )

        return True, ""

    def is_valid_implement_args(self, prompt: str) -> bool:
        """Validate /implement command arguments.

        Args:
            prompt: The prompt text

        Returns:
            True if valid (no args = default, or task IDs in current_tasks)
        """
        cmd = self._triggers.implement.command
        parts = prompt.split()

        if cmd not in parts:
            return True

        # Command must be first
        if parts[0] != cmd:
            return False

        # No args - valid (defaults to current tasks)
        if len(parts) == 1:
            return True

        # Check for help flag
        if self.is_help_requested(prompt):
            return True

        # Parse and validate task IDs
        task_ids = self._parse_task_ids(prompt)
        if not task_ids:
            return False  # Invalid format

        is_valid, _ = self._validate_tasks_in_current(task_ids)
        return is_valid

    def get_resolved_task_ids(self, prompt: str) -> list[str]:
        """Get task IDs to implement.

        Args:
            prompt: The prompt text

        Returns:
            List of task IDs (from args or current state)
        """
        task_ids = self._parse_task_ids(prompt)
        if not task_ids:
            # No args - return all current tasks
            return get_current_tasks_ids()
        return task_ids

    def is_implement_triggered(self, prompt: str) -> bool:
        """Check if /implement command is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if /implement is triggered
        """
        return self._triggers.implement.command in prompt.split()

    def is_help_requested(self, prompt: str) -> bool:
        """Check if --help flag is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if --help is requested
        """
        cmd = self._triggers.implement.command
        return f"{cmd} --help" in prompt or f"{cmd} -h" in prompt

    def is_continue_requested(self, prompt: str) -> bool:
        """Check if --continue flag is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if --continue is requested
        """
        cmd = self._triggers.implement.command
        return f"{cmd} --continue" in prompt or f"{cmd} -c" in prompt

    def is_deactivate_triggered(self, prompt: str) -> bool:
        """Check if /deactivate-workflow is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if deactivate is triggered
        """
        return self._triggers.deactivate.command in prompt

    def is_dry_run_triggered(self, prompt: str) -> bool:
        """Check if /dry-run is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if dry run is triggered
        """
        return self._triggers.dry_run.command in prompt

    def is_troubleshoot_triggered(self, prompt: str) -> bool:
        """Check if /troubleshoot is in prompt.

        Args:
            prompt: The prompt text

        Returns:
            True if troubleshoot is triggered
        """
        return self._triggers.troubleshoot.command in prompt

    def handle_help(self) -> None:
        """Handle /implement --help command."""
        current_tasks = get_current_tasks_ids()
        current_story = get_current_user_story()

        help_text = f"""
/implement - Implement tasks from the current user story

Usage:
  /implement              Implement all current tasks ({', '.join(current_tasks) if current_tasks else 'none'})
  /implement TNNN         Implement a specific task
  /implement TNNN - TNNN  Implement a range of tasks
  /implement --continue   Resume workflow from where it stopped
  /implement --help       Show this help message

Current User Story: {current_story}
Available Tasks: {', '.join(current_tasks) if current_tasks else 'No tasks available'}
"""
        print(help_text, file=sys.stderr)
        sys.exit(2)

    def handle_continue(self) -> None:
        """Handle /implement --continue command - resume without reset."""
        if self._state.is_workflow_active():
            print("Workflow already active.", file=sys.stderr)
            sys.exit(2)

        # Get stop info if available
        stopped_phase = self._state.get("stopped_phase", "")
        stopped_at = self._state.get("stopped_at", "")

        # Re-activate without resetting state
        self._state.activate_workflow()

        # Clear stop info
        self._state.delete("stopped_at")
        self._state.delete("stopped_phase")
        self._state.delete("stop_hook_active")

        if stopped_phase:
            print(f"Resumed from '{stopped_phase}' (stopped at {stopped_at})", file=sys.stderr)

    def handle_implement(self, prompt: str) -> None:
        """Handle /implement command.

        Args:
            prompt: The prompt text
        """
        cmd = self._triggers.implement.command
        parts = prompt.split()

        # Check if args were provided but couldn't be parsed (invalid format)
        has_args = len(parts) > 1 and parts[0] == cmd
        task_ids = self._parse_task_ids(prompt)

        if has_args and not task_ids:
            # Args provided but invalid format
            print(f"Invalid args: Invalid task format. Use TNNN or TNNN - TNNN", file=sys.stderr)
            sys.exit(2)

        is_valid, error_msg = self._validate_tasks_in_current(task_ids)

        if not is_valid:
            print(f"Invalid args: {error_msg}", file=sys.stderr)
            sys.exit(2)

        # Reset state before activating (fresh start)
        self._state.reset()
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

    def handle_troubleshoot(self) -> None:
        """Handle /troubleshoot command."""
        if self._state.is_troubleshoot_active():
            # Exit troubleshoot mode and return to previous phase
            self._state.deactivate_troubleshoot()
        else:
            # Check if we can enter troubleshoot from current phase
            current_phase = self._state.get_current_phase()
            if can_bypass_from("troubleshoot", current_phase):
                self._state.activate_troubleshoot()
            else:
                print(
                    f"Cannot enter troubleshoot from '{current_phase}' (pre-coding phase)",
                    file=sys.stderr,
                )
                sys.exit(2)

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

        # Handle troubleshoot (only when workflow is active)
        if self.is_troubleshoot_triggered(prompt):
            if self._state.is_workflow_active():
                self.handle_troubleshoot()
            return

        # Handle continue (resume without reset)
        if self.is_continue_requested(prompt):
            self.handle_continue()
            return

        # Handle implement help
        if self.is_help_requested(prompt):
            self.handle_help()
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
