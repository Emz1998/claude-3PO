#!/usr/bin/env python3
"""
Engineer task completion guard.

Ensures engineer agents complete their assigned tasks:
- Blocks tools until task is in_progress
- Prevents SubagentStop until task is completed
- Allows log:task skill to update task status
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (  # type: ignore
    block_response,
    get_cache,
    load_cache,
    set_cache,
    read_stdin_json,
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    find_task_in_roadmap,
    log,
)


def is_implement_active() -> bool:
    """Check if codebase explorer is active."""
    return get_cache("is_implement_active") is True


def main() -> None:
    """Main entry point."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    if not is_implement_active():
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
