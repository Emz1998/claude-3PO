#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import re
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from state import reset_state  # type: ignore


def main():
    reset_state()
    print("State reset successfully. Stopping execution.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
