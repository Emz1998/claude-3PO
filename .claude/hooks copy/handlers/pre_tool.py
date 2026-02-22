#!/usr/bin/env python3
"""PreToolUse handler that routes to appropriate guards.

Consolidated entry point for all PreToolUse validation.
"""

import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json, Hook  # type: ignore


def main() -> None:
    """Main entry point for the handler."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    handler = PreToolHandler()
    handler.run(hook_input)b


if __name__ == "__main__":
    main()
