"""logger.py — Workflow event logger for full observability.

Writes JSONL to workflow.log. Always on.
Use `tail -f .claude/hooks/workflow/workflow.log` to observe.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.config import LOG_FILE


def log(event: str, **kwargs) -> None:
    """Append a structured log entry to workflow.log."""
    entry = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "event": event,
        **kwargs,
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
