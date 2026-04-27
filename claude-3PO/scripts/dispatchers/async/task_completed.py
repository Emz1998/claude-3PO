#!/usr/bin/env python3
"""TaskCompleted async dispatcher — auto-commit after a task finishes.

Thin shim that delegates to :func:`utils.auto_commit.main`. Registered with
``async: true`` in ``hooks.json``, so it must never block the live session —
the underlying ``auto_commit`` flow fails silently on every error path
(same pattern as ``utils.summarize_prompt``).

Kept separate from the synchronous ``dispatchers/task_completed.py`` so the
git-commit work runs out-of-band: the sync hook updates state immediately,
this async hook handles the slower commit step.
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from utils.auto_commit import main

if __name__ == "__main__":
    main()
