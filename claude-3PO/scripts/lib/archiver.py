"""archiver.py — Archive plan and contracts files before starting a new workflow.

Each ``/build`` invocation gets a fresh ``latest-plan.md`` and
``latest-contracts.md``. To avoid clobbering prior workflow output, this module
copies the existing files into a dated archive directory and then removes the
originals so the next workflow starts from a clean slate.
"""

import shutil
from datetime import datetime
from pathlib import Path

from .parser import parse_frontmatter
from config import Config


def archive_plan(config: Config) -> None:
    """
    Archive the existing ``latest-plan.md`` before starting a new workflow.

    The archive filename embeds today's date and the *previous* workflow's
    ``session_id`` (read from the plan's frontmatter) so each archived plan is
    traceable back to the run that produced it. If the plan file does not exist
    the call is a no-op — first-ever runs have nothing to archive.

    Args:
        config (Config): Project config providing ``plan_file_path`` and
            ``plan_archive_dir``.

    Returns:
        None: Side-effects only — copies the file and deletes the original.

    Example:
        >>> archive_plan(Config())  # doctest: +SKIP
    """
    plan_path = Path(config.plan_file_path)
    if not plan_path.exists():
        return

    content = plan_path.read_text()
    fm = parse_frontmatter(content)
    session_id = fm.get("session_id", "unknown")
    date = datetime.now().strftime("%Y-%m-%d")

    archive_dir = Path(config.plan_archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"plan_{date}_{session_id}.md"
    shutil.copy2(plan_path, archive_dir / archive_name)
    plan_path.unlink()


def archive_contracts(config: Config) -> None:
    """
    Archive the existing ``latest-contracts.md`` before starting a new workflow.

    Unlike plans, the contracts file is not session-tagged in its frontmatter,
    so the archive name uses only the date. If two workflows archive on the
    same day the second copy overwrites the first — this is intentional since
    contracts describe the project state at a point in time, not a single run.

    Args:
        config (Config): Project config providing ``contracts_file_path`` and
            ``contracts_archive_dir``.

    Returns:
        None: Side-effects only — copies the file and deletes the original.

    Example:
        >>> archive_contracts(Config())  # doctest: +SKIP
    """
    contracts_path = Path(config.contracts_file_path)
    if not contracts_path.exists():
        return

    date = datetime.now().strftime("%Y-%m-%d")

    archive_dir = Path(config.contracts_archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"contracts_{date}.md"
    shutil.copy2(contracts_path, archive_dir / archive_name)
    contracts_path.unlink()
