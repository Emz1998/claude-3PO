"""Single source of truth for workflow phase and status constants."""

from workflow.config import get

PHASES: list[str] = get("phases.workflow")

CODING_PHASES: list[str] = get("phases.coding")

# Statuses
STATUS_READY = "Ready"
STATUS_DONE = "Done"
STATUS_IN_PROGRESS = "In progress"
