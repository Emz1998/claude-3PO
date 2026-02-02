#!/usr/bin/env python3
"""PreToolUse guard for file read order validation.

Validates that files are read in the required order during workflow execution.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from core.phase_engine import validate_order  # type: ignore
from config.loader import get_required_read_order  # type: ignore


class ReadOrderGuard:
    """Guard for validating file read order."""

    def __init__(self):
        """Initialize the guard."""
        self._state = get_manager()
        self._required_order = get_required_read_order()

    def is_active(self) -> bool:
        """Check if guard is active (workflow is active)."""
        return self._state.is_workflow_active()

    def get_last_file_read(self, phase: str | None = None) -> str | None:
        """Get the last file read in the current or specified phase.

        Args:
            phase: Optional phase to check

        Returns:
            Last file read or None
        """
        if phase is None:
            phase = self._state.get_current_phase()

        if not phase:
            return None

        read_files = self._state.get("read_files") or {}
        files_read = read_files.get(phase, [])
        return files_read[-1] if files_read else None

    def validate(self, last_file: str | None, next_file: str) -> tuple[bool, str]:
        """Validate file read order.

        Args:
            last_file: Last file read
            next_file: Next file to read

        Returns:
            Tuple of (is_valid, error_message)
        """
        return validate_order(last_file, next_file, self._required_order)

    def run(self, hook_input: dict) -> None:
        """Run the guard against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        hook_event_name = hook_input.get("hook_event_name", "")
        if hook_event_name != "PreToolUse":
            sys.exit(0)

        tool_name = hook_input.get("tool_name", "")
        if tool_name != "Read":
            sys.exit(0)

        tool_input = hook_input.get("tool_input", {})
        next_file = tool_input.get("file_path", None)
        if not next_file:
            sys.exit(0)

        # Extract just the filename for matching
        next_file_name = Path(next_file).name

        # Check if this file is in our required order
        if next_file_name not in self._required_order:
            # File not in required order, allow it
            sys.exit(0)

        phase = tool_input.get("phase", None)
        last_file = self.get_last_file_read(phase)

        is_valid, error_message = self.validate(last_file, next_file_name)
        if not is_valid:
            print(error_message, file=sys.stderr)
            sys.exit(2)

        sys.exit(0)


def validate_read_order(last_file: str | None, next_file: str) -> tuple[bool, str]:
    """Validate file read order.

    Args:
        last_file: Last file read
        next_file: Next file to read

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_order = get_required_read_order()
    return validate_order(last_file, next_file, required_order)


def main() -> None:
    """Main entry point for the guard."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    guard = ReadOrderGuard()
    guard.run(hook_input)


if __name__ == "__main__":
    main()
