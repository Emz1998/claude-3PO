"""Filesystem path constants used by hooks and async workers."""

from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

COMMIT_BATCH_PATH = SCRIPTS_DIR / "commit_batch.json"

E2E_TEST_REPORT = ".claude/reports/E2E_TEST_REPORT.md"

STALE_THRESHOLD_MINUTES = 10
