#!/usr/bin/env python3
"""auto_commit.py — Async hook that auto-commits after TaskCompleted events.

Fires asynchronously after each TaskCompleted. Detects dirty files, claims them
via a batch ledger to prevent cross-batch contamination, invokes headless Claude
to generate a commit message, then commits — all without blocking the main session.
"""

import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

from constants.paths import COMMIT_BATCH_PATH, STALE_THRESHOLD_MINUTES
from lib.hook import Hook
from lib.file_manager import load_file, save_file
from lib.shell import run_git, invoke_claude

# Patterns to exclude from auto-commits
EXCLUDE_PATTERNS = [
    re.compile(r"(^|/)state\.jsonl?$"),
    re.compile(r"\.pyc$"),
    re.compile(r"(^|/)__pycache__/"),
    re.compile(r"(^|/)commit_batch\.json$"),
    re.compile(r"(^|/)workflow\.log$"),
    re.compile(r"(^|/)locks/"),
    re.compile(r"(^|/)settings\.local\.json$"),
    re.compile(r"\.lock$"),
]

# ---------------------------------------------------------------------------
# Ledger I/O
# ---------------------------------------------------------------------------


def load_ledger(ledger_path: Path) -> dict:
    """Load the batch ledger via lib.file_manager; tolerate corrupt/empty files."""
    try:
        data = load_file(ledger_path) or {}
    except ValueError:
        return {"batches": []}
    if not isinstance(data, dict):
        return {"batches": []}
    data.setdefault("batches", [])
    return data


def save_ledger(ledger: dict, ledger_path: Path) -> None:
    """Save the batch ledger via lib.file_manager."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    save_file(ledger, "w", ledger_path)


def cleanup_old_batches(ledger: dict, keep: int = 10) -> dict:
    """Remove old committed batches, keeping only the last `keep`."""
    committed = [b for b in ledger["batches"] if b["status"] == "committed"]
    non_committed = [b for b in ledger["batches"] if b["status"] != "committed"]

    if len(committed) > keep:
        committed = committed[-keep:]

    ledger["batches"] = non_committed + committed
    return ledger


# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------


def _is_excluded(filepath: str) -> bool:
    return any(p.search(filepath) for p in EXCLUDE_PATTERNS)


def _resolve_rename(filepath: str) -> str:
    """'R  old -> new' → 'new'"""
    return filepath.split(" -> ")[-1] if " -> " in filepath else filepath


def _parse_porcelain_line(line: str) -> str | None:
    """Parse a single git status --porcelain line into a filepath, or None if excluded."""
    if not line or len(line) < 4:
        return None

    filepath = _resolve_rename(line[3:].strip())

    if _is_excluded(filepath):
        return None

    return filepath


def _git_status(project_dir: Path) -> str | None:
    """Run git status --porcelain. Returns stdout or None on failure."""
    result = run_git(["status", "--porcelain", "-uall"], cwd=project_dir)
    return result.stdout if result.returncode == 0 else None


def get_dirty_files(project_dir: Path) -> list[str]:
    """Get list of dirty (modified/untracked) files from git status."""
    output = _git_status(project_dir)
    if output is None:
        return []

    lines = output.strip().splitlines()
    return [fp for line in lines if (fp := _parse_porcelain_line(line))]


def _git_add(files: list[str], project_dir: Path) -> bool:
    return run_git(["add", *files], cwd=project_dir).returncode == 0


def _git_commit(message: str, project_dir: Path) -> bool:
    return run_git(["commit", "-m", message], cwd=project_dir).returncode == 0


def commit_files(files: list[str], message: str, project_dir: Path) -> bool:
    """Stage and commit the given files."""
    return _git_add(files, project_dir) and _git_commit(message, project_dir)


# ---------------------------------------------------------------------------
# Batch claiming
# ---------------------------------------------------------------------------


def _is_batch_stale(batch: dict, stale_cutoff: datetime) -> bool:
    """Check if a pending batch has exceeded the stale threshold."""
    try:
        created = datetime.fromisoformat(batch["created_at"])
        return created < stale_cutoff
    except (ValueError, KeyError):
        return True


def _collect_claimed_files(ledger: dict) -> set[str]:
    """Collect files owned by active (non-stale) pending batches. Marks stale batches as failed."""
    stale_cutoff = datetime.now() - timedelta(minutes=STALE_THRESHOLD_MINUTES)
    claimed = set()

    for batch in ledger["batches"]:
        if batch["status"] != "pending":
            continue
        if _is_batch_stale(batch, stale_cutoff):
            batch["status"] = "failed"
            continue
        claimed.update(batch["files"])

    return claimed


def claim_files(dirty_files: list[str], ledger: dict) -> list[str]:
    """Claim files not already owned by a pending (non-stale) batch."""
    claimed = _collect_claimed_files(ledger)
    return [f for f in dirty_files if f not in claimed]


# ---------------------------------------------------------------------------
# Commit message generation
# ---------------------------------------------------------------------------


def _build_commit_prompt(files: list[str], task_subject: str, task_description: str) -> str:
    file_list = "\n".join(f"- {f}" for f in files)
    return (
        "Generate a concise git commit message for the following changes.\n"
        f"Task: {task_subject}\n"
        f"Task Description: {task_description}\n"
        f"Files changed:\n{file_list}\n"
        "Use conventional commit format (feat/fix/chore/refactor/docs/test).\n"
        "Keep the first line under 72 characters. Add a body if the changes warrant it.\n"
        "Respond with ONLY the commit message text, nothing else."
    )


def generate_commit_message(
    files: list[str], task_subject: str, task_description: str, project_dir: Path,
) -> str:
    """Use headless Claude to generate a conventional commit message."""
    prompt = _build_commit_prompt(files, task_subject, task_description)
    output = invoke_claude(prompt, timeout=120, cwd=project_dir)
    return output or f"chore: auto-commit after task ({task_subject})"


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def _make_batch_id() -> str:
    return f"batch-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:4]}"


def _get_unclaimed_files(project_dir: Path, ledger: dict) -> list[str] | None:
    """Get dirty files that aren't claimed by another batch. Returns None if nothing to commit."""
    dirty = get_dirty_files(project_dir)
    if not dirty:
        return None
    claimed = claim_files(dirty, ledger)
    return claimed or None


def _add_pending_batch(
    ledger: dict, batch_id: str, task_id: str, task_subject: str, files: list[str],
) -> None:
    """Write a pending batch entry to the ledger."""
    from models.batch import BatchEntry

    entry = BatchEntry(
        batch_id=batch_id, task_id=task_id, task_subject=task_subject,
        files=files, status="pending",
    )
    ledger["batches"].append(entry.model_dump(exclude_none=True))


def _claim_phase(
    batch_id: str, task_id: str, task_subject: str,
    project_dir: Path, ledger_path: Path, lock,
) -> list[str] | None:
    """Phase 1: Claim dirty files under a ledger lock. Returns claimed files or None."""
    try:
        with lock:
            return _claim_under_lock(
                batch_id, task_id, task_subject, project_dir, ledger_path
            )
    except Exception:
        return None


def _claim_under_lock(
    batch_id: str, task_id: str, task_subject: str,
    project_dir: Path, ledger_path: Path,
) -> list[str] | None:
    ledger = load_ledger(ledger_path)
    claimed = _get_unclaimed_files(project_dir, ledger)
    if not claimed:
        return None
    _add_pending_batch(ledger, batch_id, task_id, task_subject, claimed)
    save_ledger(ledger, ledger_path)
    return claimed


def _update_batch_status(ledger: dict, batch_id: str, success: bool, message: str) -> None:
    """Update a batch entry's status after commit attempt."""
    for batch in ledger["batches"]:
        if batch["batch_id"] == batch_id:
            batch["status"] = "committed" if success else "failed"
            if success:
                batch["commit_message"] = message
            break


def _commit_phase(
    batch_id: str, claimed: list[str], message: str,
    project_dir: Path, ledger_path: Path, lock,
) -> bool:
    """Phase 3: Commit files and update ledger under lock."""
    try:
        with lock:
            success = commit_files(claimed, message, project_dir)

            ledger = load_ledger(ledger_path)
            _update_batch_status(ledger, batch_id, success, message)
            save_ledger(cleanup_old_batches(ledger), ledger_path)
            return success
    except Exception:
        return False


def _read_task_inputs() -> tuple[str, str, str, Path]:
    raw = Hook.read_stdin()
    return (
        raw.get("task_subject", "unknown task"),
        raw.get("task_id", "unknown"),
        raw.get("task_description", ""),
        Path(raw.get("cwd", os.getcwd())),
    )


def main() -> None:
    """Entry point — reads TaskCompleted hook input from stdin, runs auto-commit."""
    from filelock import FileLock

    task_subject, task_id, task_description, project_dir = _read_task_inputs()
    ledger_path = COMMIT_BATCH_PATH
    lock = FileLock(ledger_path.with_suffix(".lock"), timeout=30)
    batch_id = _make_batch_id()
    claimed = _claim_phase(batch_id, task_id, task_subject, project_dir, ledger_path, lock)
    if not claimed:
        return
    message = generate_commit_message(claimed, task_subject, task_description, project_dir)
    if _commit_phase(batch_id, claimed, message, project_dir, ledger_path, lock):
        Hook.system_message(f"Auto-committed {len(claimed)} file(s): {message}")


if __name__ == "__main__":
    main()
