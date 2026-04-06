"""paths.py — Canonical path constants for the build system."""

from pathlib import Path

BUILD_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_STATE_JSONL_PATH = BUILD_ROOT / "state.jsonl"
COMMIT_BATCH_PATH = BUILD_ROOT / "commit_batch.json"
LOG_FILE = BUILD_ROOT / "build.log"
DEBUG_LOG_FILE = Path("DEBUG.log")

# Keep WORKFLOW_ROOT alias for compatibility with copied code
WORKFLOW_ROOT = BUILD_ROOT
