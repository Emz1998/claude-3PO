#!/usr/bin/env python3
"""UserPromptSubmit async dispatcher — summarize ``/build`` prompts.

Thin shim that delegates to :func:`utils.summarize_prompt.main`. Registered
with ``async: true`` in ``hooks.json``, so it must never block the live
session — the underlying summarizer fails silently on every error path
(timeout, missing CLI, empty output) and falls back to a hard-truncated
copy of the original instructions.

See ``utils.summarize_prompt`` for the full numbered flow (``/build`` filter
→ headless Claude call → state write + violations.md back-fill).
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from utils.summarize_prompt import main

if __name__ == "__main__":
    main()
