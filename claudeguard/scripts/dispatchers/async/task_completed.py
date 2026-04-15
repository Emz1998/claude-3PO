#!/usr/bin/env python3
"""TaskCompleted async dispatcher — auto-commits after task completion."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from utils.auto_commit import main

if __name__ == "__main__":
    main()
