"""paths.py — Canonical path constants for the workflow system."""

from pathlib import Path

WORKFLOW_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_STATE_PATH = WORKFLOW_ROOT / "state.json"
LOG_FILE = WORKFLOW_ROOT / "workflow.log"
DEBUG_LOG_FILE = Path("DEBUG.log")
