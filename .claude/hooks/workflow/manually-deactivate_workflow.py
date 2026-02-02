#!/usr/bin/env python3
"""Manually deactivate workflow and reset state.

This script can be run directly to deactivate the workflow and reset all state.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from state import reset_state  # type: ignore


def main() -> None:
    reset_state()
    print("Workflow deactivated and state reset", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
