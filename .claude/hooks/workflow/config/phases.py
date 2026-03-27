"""Single source of truth for workflow phase and status constants."""

from workflow.config import get

PHASES: list[str] = get("phases.workflow")

# Story statuses
STATUS_READY = "Ready"
STATUS_DONE = "Done"
STATUS_IN_PROGRESS = "In progress"

# Session control statuses
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_ABORTED = "aborted"

# CI statuses
CI_PENDING = "pending"
CI_PASS = "pass"
CI_FAIL = "fail"
