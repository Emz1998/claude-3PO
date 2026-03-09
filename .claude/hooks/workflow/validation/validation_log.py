"""Validation log — appends timestamped entries to validation.log."""

from datetime import datetime
from pathlib import Path

from workflow.config import get as cfg

LOG_PATH = Path(cfg("paths.validation_log"))


def log(gate: str, action: str, message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{gate}] [{action}] {message}\n"
    with open(LOG_PATH, "a") as f:
        f.write(entry)
