"""archiver.py — Archive plan and contracts files before starting a new workflow."""

import shutil
from datetime import datetime
from pathlib import Path

from .parser import parse_frontmatter
from config import Config


def archive_plan(config: Config) -> None:
    """Archive existing latest-plan.md before starting a new workflow."""
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
    """Archive existing latest-contracts.md before starting a new workflow."""
    contracts_path = Path(config.contracts_file_path)
    if not contracts_path.exists():
        return

    date = datetime.now().strftime("%Y-%m-%d")

    archive_dir = Path(config.contracts_archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"contracts_{date}.md"
    shutil.copy2(contracts_path, archive_dir / archive_name)
    contracts_path.unlink()
