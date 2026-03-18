"""Validation log — appends timestamped entries to validation.log."""

from datetime import datetime
from pathlib import Path

# from workflow.config import get as cfg
PARENT_DIR = Path(__file__).parent

LOG_PATH = PARENT_DIR / "workflow.log"


def log(hook_name: str, status: str, message: str, log_path: Path = LOG_PATH) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} | {hook_name} | {status} | {message}\n"
    with open(log_path, "a") as f:
        f.write(entry)
