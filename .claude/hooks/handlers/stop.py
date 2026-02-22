#!/usr/bin/env python3
"""Stop handler for workflow state management.

Disables workflow when Stop hook is triggered, preserving state for resume.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore


def main() -> None:
    """Main entry point for Stop handler."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    hook_event_name = hook_input.get("hook_event_name", "")
    if hook_event_name != "Stop":
        sys.exit(0)

    state = get_manager()

    # Only act if workflow is active
    if not state.is_workflow_active():
        sys.exit(0)

    # Store stop info for debugging
    state.set("stopped_at", datetime.now().isoformat())
    state.set("stopped_phase", state.get_current_phase())
    state.set("stop_hook_active", hook_input.get("stop_hook_active", False))

    # Disable workflow (preserves current phase and all state)
    state.deactivate_workflow()

    # Allow stop to proceed
    sys.exit(0)


if __name__ == "__main__":
    main()
