#!/usr/bin/env python3
"""Manually deactivate workflow."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from state import set_state  # type: ignore


def main():
    set_state("workflow_active", False)
    print("Workflow deactivated")
    sys.exit(1)


if __name__ == "__main__":
    main()
