"""logger.py — Workflow event logger for full observability.

Writes JSONL to workflow.log. Always on.
Use `tail -f .claude/hooks/workflow/workflow.log` to observe.
"""

import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "workflow.log"


def log(event: str, **kwargs) -> None:
    """Append a structured log entry to workflow.log."""
    entry = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "event": event,
        **kwargs,
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
