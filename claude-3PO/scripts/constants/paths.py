"""Filesystem path constants used by hooks and async workers.

``SCRIPTS_DIR`` anchors every other path to the repo's ``scripts/`` directory
so the constants resolve correctly no matter the caller's cwd. Time-based
constants (``STALE_THRESHOLD_MINUTES``) live here too because they parameterise
the same on-disk artefacts.
"""

from pathlib import Path

# Absolute path to the ``scripts/`` directory (parent of ``constants/``).
SCRIPTS_DIR = Path(__file__).resolve().parent.parent

# Absolute path to the plugin root (one level above ``scripts/``); used by
# violations logging and post-task commit hooks.
PLUGIN_ROOT = SCRIPTS_DIR.parent

# Ledger file consumed by the auto-commit batcher; rows are ``BatchEntry`` shapes.
COMMIT_BATCH_PATH = SCRIPTS_DIR / "commit_batch.json"

# Repo-relative path the e2e harness writes its markdown report to.
E2E_TEST_REPORT = ".claude/reports/E2E_TEST_REPORT.md"

# Minutes before an in-progress batch entry is considered abandoned and re-claimable.
STALE_THRESHOLD_MINUTES = 10
