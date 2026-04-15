#!/usr/bin/env python3
"""auto_commit.py — Async hook that auto-commits after TaskCompleted events.

Fires asynchronously after each TaskCompleted. Detects dirty files, claims them
via a batch ledger to prevent cross-batch contamination, invokes headless Claude
to generate a commit message, then commits — all without blocking the main session.
"""

import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

from lib.hook import Hook

COMMIT_BATCH_PATH = SCRIPTS_DIR / "commit_batch.json"

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

STALE_THRESHOLD_MINUTES = 10


# ---------------------------------------------------------------------------
# Ledger I/O
# ---------------------------------------------------------------------------


def load_ledger(ledger_path: Path) -> dict:
    """Load the batch ledger from disk."""
    if not ledger_path.exists():
        return {"batches": []}
    try:
        content = ledger_path.read_text(encoding="utf-8").strip()
        if not content:
            return {"batches": []}
        data = json.loads(content)
        if "batches" not in data:
            data["batches"] = []
        return data
    except (json.JSONDecodeError, OSError):
        return {"batches": []}


def save_ledger(ledger: dict, ledger_path: Path) -> None:
    """Save the batch ledger to disk."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


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
    result = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def get_dirty_files(project_dir: Path) -> list[str]:
    """Get list of dirty (modified/untracked) files from git status."""
    output = _git_status(project_dir)
    if output is None:
        return []

    lines = output.strip().splitlines()
    return [fp for line in lines if (fp := _parse_porcelain_line(line))]


def _git_add(files: list[str], project_dir: Path) -> bool:
    result = subprocess.run(
        ["git", "add"] + files,
        cwd=project_dir, capture_output=True, text=True,
    )
    return result.returncode == 0


def _git_commit(message: str, project_dir: Path) -> bool:
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=project_dir, capture_output=True, text=True,
    )
    return result.returncode == 0


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


def _invoke_claude(prompt: str, project_dir: Path) -> str | None:
    """Run headless Claude to generate text. Returns output or None on failure."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt,
             "--tools", "Read,Grep,Glob",
             "--allowedTools", "Read,Grep,Glob",
             "--output-format", "text"],
            capture_output=True, text=True, timeout=120, cwd=project_dir,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def generate_commit_message(
    files: list[str], task_subject: str, task_description: str, project_dir: Path,
) -> str:
    """Use headless Claude to generate a conventional commit message."""
    prompt = _build_commit_prompt(files, task_subject, task_description)
    return _invoke_claude(prompt, project_dir) or f"chore: auto-commit after task ({task_subject})"


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
    ledger["batches"].append({
        "batch_id": batch_id,
        "task_id": task_id,
        "task_subject": task_subject,
        "files": files,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    })


def _claim_phase(
    batch_id: str, task_id: str, task_subject: str,
    project_dir: Path, ledger_path: Path, lock,
) -> list[str] | None:
    """Phase 1: Claim dirty files under a ledger lock. Returns claimed files or None."""
    try:
        with lock:
            ledger = load_ledger(ledger_path)
            claimed = _get_unclaimed_files(project_dir, ledger)
            if not claimed:
                return None

            _add_pending_batch(ledger, batch_id, task_id, task_subject, claimed)
            save_ledger(ledger, ledger_path)
            return claimed
    except Exception:
        return None


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


def main() -> None:
    """Entry point — reads TaskCompleted hook input from stdin, runs auto-commit."""
    from filelock import FileLock

    raw_input = Hook.read_stdin()
    task_subject = raw_input.get("task_subject", "unknown task")
    task_id = raw_input.get("task_id", "unknown")
    task_description = raw_input.get("task_description", "")
    project_dir = Path(raw_input.get("cwd", os.getcwd()))
    ledger_path = COMMIT_BATCH_PATH
    lock = FileLock(ledger_path.with_suffix(".lock"), timeout=30)
    batch_id = _make_batch_id()

    # Phase 1: Claim files
    claimed = _claim_phase(batch_id, task_id, task_subject, project_dir, ledger_path, lock)
    if not claimed:
        return

    # Phase 2: Generate commit message (no lock held)
    message = generate_commit_message(claimed, task_subject, task_description, project_dir)

    # Phase 3: Commit
    success = _commit_phase(batch_id, claimed, message, project_dir, ledger_path, lock)

    if success:
        Hook.system_message(f"Auto-committed {len(claimed)} file(s): {message}")


if __name__ == "__main__":
    main()
