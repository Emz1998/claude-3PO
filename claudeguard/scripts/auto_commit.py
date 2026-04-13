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
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.hook import Hook

# Config paths relative to this script
SCRIPTS_DIR = Path(__file__).resolve().parent
COMMIT_BATCH_PATH = SCRIPTS_DIR / "commit_batch.json"


def log(event: str, **kwargs) -> None:
    """Simple logger — print to stderr for hook debugging."""
    import sys as _sys
    parts = [f"{event}"]
    for k, v in kwargs.items():
        parts.append(f"{k}={v}")
    print(" ".join(parts), file=_sys.stderr)

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


def get_dirty_files(project_dir: Path) -> list[str]:
    """Get list of dirty (modified/untracked) files from git status."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    files = []
    for line in result.stdout.strip().splitlines():
        if not line or len(line) < 4:
            continue
        # git status --porcelain: XY filename
        filepath = line[3:].strip()
        # Handle renamed files: "R  old -> new"
        if " -> " in filepath:
            filepath = filepath.split(" -> ")[-1]

        # Apply exclude patterns
        if any(p.search(filepath) for p in EXCLUDE_PATTERNS):
            continue

        files.append(filepath)

    return files


def commit_files(files: list[str], message: str, project_dir: Path) -> bool:
    """Stage and commit the given files."""
    try:
        add_result = subprocess.run(
            ["git", "add"] + files,
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        if add_result.returncode != 0:
            log("AutoCommit:add_failed", error=add_result.stderr)
            return False

        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        if commit_result.returncode != 0:
            log("AutoCommit:commit_failed", error=commit_result.stderr)
            return False

        return True
    except subprocess.CalledProcessError as e:
        log("AutoCommit:error", error=str(e))
        return False


# ---------------------------------------------------------------------------
# Batch claiming
# ---------------------------------------------------------------------------


def claim_files(dirty_files: list[str], ledger: dict) -> list[str]:
    """Claim files not already owned by a pending (non-stale) batch."""
    now = datetime.now()
    stale_cutoff = now - timedelta(minutes=STALE_THRESHOLD_MINUTES)

    # Collect files from non-stale pending batches
    claimed = set()
    for batch in ledger["batches"]:
        if batch["status"] != "pending":
            continue
        # Check for staleness
        try:
            created = datetime.fromisoformat(batch["created_at"])
            if created < stale_cutoff:
                # Mark stale batch as failed so its files are released
                batch["status"] = "failed"
                continue
        except (ValueError, KeyError):
            batch["status"] = "failed"
            continue

        claimed.update(batch["files"])

    return [f for f in dirty_files if f not in claimed]


# ---------------------------------------------------------------------------
# Commit message generation
# ---------------------------------------------------------------------------


def generate_commit_message(
    files: list[str],
    task_subject: str,
    task_description: str,
    project_dir: Path,
) -> str:
    """Use headless Claude to generate a conventional commit message."""
    file_list = "\n".join(f"- {f}" for f in files)

    prompt = (
        "Generate a concise git commit message for the following changes.\n"
        f"Task: {task_subject}\n"
        f"Task Description: {task_description}\n"
        f"Files changed:\n{file_list}\n"
        "Use conventional commit format (feat/fix/chore/refactor/docs/test).\n"
        "Keep the first line under 72 characters. Add a body if the changes warrant it.\n"
        "Respond with ONLY the commit message text, nothing else."
    )

    fallback = f"chore: auto-commit after task ({task_subject})"

    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--tools",
                "Read,Grep,Glob",
                "--allowedTools",
                "Read,Grep,Glob",
                "--output-format",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_dir,
        )
        if result.returncode != 0 or not result.stdout.strip():
            log("AutoCommit:claude_failed", stderr=result.stderr)
            return fallback

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        log("AutoCommit:claude_timeout")
        return fallback
    except FileNotFoundError:
        log("AutoCommit:claude_not_found")
        return fallback


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point — reads TaskCompleted hook input from stdin, runs auto-commit."""
    raw_input = Hook.read_stdin()

    task_subject = raw_input.get("task_subject", "unknown task")
    task_id = raw_input.get("task_id", "unknown")
    task_description = raw_input.get("task_description", "")
    cwd = raw_input.get("cwd", os.getcwd())
    project_dir = Path(cwd)
    ledger_path = COMMIT_BATCH_PATH

    batch_id = f"batch-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:4]}"

    log(
        "AutoCommit:start",
        task_id=task_id,
        task_subject=task_subject,
        batch_id=batch_id,
    )

    # -----------------------------------------------------------------------
    # Phase 1: Claim files (with ledger lock via filelock)
    # -----------------------------------------------------------------------
    from filelock import FileLock

    lock = FileLock(ledger_path.with_suffix(".lock"), timeout=30)

    try:
        with lock:
            ledger = load_ledger(ledger_path)
            dirty = get_dirty_files(project_dir)

            if not dirty:
                log("AutoCommit:skip", reason="no dirty files", batch_id=batch_id)
                return

            claimed = claim_files(dirty, ledger)

            if not claimed:
                log(
                    "AutoCommit:skip",
                    reason="all files claimed by other batches",
                    batch_id=batch_id,
                )
                return

            # Write pending batch to ledger
            batch_entry = {
                "batch_id": batch_id,
                "task_id": task_id,
                "task_subject": task_subject,
                "files": claimed,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
            ledger["batches"].append(batch_entry)
            save_ledger(ledger, ledger_path)

    except Exception as e:
        log("AutoCommit:claim_error", error=str(e), batch_id=batch_id)
        return

    log("AutoCommit:claimed", batch_id=batch_id, files=claimed)

    # -----------------------------------------------------------------------
    # Phase 2: Generate commit message (no lock held)
    # -----------------------------------------------------------------------
    message = generate_commit_message(
        files=claimed,
        task_subject=task_subject,
        task_description=task_description,
        project_dir=project_dir,
    )

    log("AutoCommit:message_generated", batch_id=batch_id, message=message)

    # -----------------------------------------------------------------------
    # Phase 3: Commit (with lock)
    # -----------------------------------------------------------------------
    try:
        with lock:
            success = commit_files(
                files=claimed, message=message, project_dir=project_dir
            )

            ledger = load_ledger(ledger_path)
            for batch in ledger["batches"]:
                if batch["batch_id"] == batch_id:
                    if success:
                        batch["status"] = "committed"
                        batch["commit_message"] = message
                    else:
                        batch["status"] = "failed"
                    break

            ledger = cleanup_old_batches(ledger)
            save_ledger(ledger, ledger_path)

    except Exception as e:
        log("AutoCommit:commit_error", error=str(e), batch_id=batch_id)
        return

    if success:
        log("AutoCommit:success", batch_id=batch_id, message=message, files=claimed)
        Hook.system_message(f"Auto-committed {len(claimed)} file(s): {message}")
    else:
        log("AutoCommit:failed", batch_id=batch_id, files=claimed)


if __name__ == "__main__":
    main()
