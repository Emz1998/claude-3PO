#!/usr/bin/env python3
"""UserPromptSubmit async dispatcher — summarizes build prompts."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from utils.summarize_prompt import main

if __name__ == "__main__":
    main()
