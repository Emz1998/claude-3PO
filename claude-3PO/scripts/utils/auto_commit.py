#!/usr/bin/env python3
"""auto_commit.py — Async hook that auto-commits after TaskCompleted events.

Fires asynchronously after each TaskCompleted. Detects dirty files, claims them
via a batch ledger to prevent cross-batch contamination, invokes headless Claude
to generate a commit message, then commits — all without blocking the main session.

Flow is split into three phases with the file lock deliberately released
between them:

    Phase 1 (under lock): claim dirty files into a ``pending`` batch entry.
    Phase 2 (no lock):    invoke headless Claude to generate a commit message.
    Phase 3 (under lock): commit and flip the batch entry to ``committed``.

Releasing the lock during Phase 2 matters — the Claude call can take many
seconds, and holding the ledger lock that long would serialize every
concurrent auto-commit. The pending-batch ledger entry written in Phase 1
already prevents another invocation from claiming the same files, so the
lock isn't needed during message generation.
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
from lib.shell import run_git, invoke_headless_agent

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
    """Load the batch ledger, tolerating corrupt/empty files.

    A missing or empty file yields an empty ledger (``{"batches": []}``)
    rather than raising — this hook runs async and must never crash the
    main session. A ``ValueError`` from the file_manager (e.g. malformed
    JSON) is treated the same as missing: start fresh rather than block
    every future commit on the broken file.

    Args:
        ledger_path (Path): Filesystem path to ``commit_batch.json``.

    Returns:
        dict: Ledger dict with at least a ``"batches"`` list key.

    Example:
        >>> ledger = load_ledger(Path("/nonexistent.json"))
        >>> ledger["batches"]
        []
    """
    try:
        data = load_file(ledger_path) or {}
    except ValueError:
        return {"batches": []}
    if not isinstance(data, dict):
        return {"batches": []}
    data.setdefault("batches", [])
    return data


def save_ledger(ledger: dict, ledger_path: Path) -> None:
    """Save the batch ledger, creating parent dirs if needed.

    Args:
        ledger (dict): Ledger payload — typically ``{"batches": [...]}``.
        ledger_path (Path): Destination path for the JSON file.

    Example:
        >>> save_ledger({"batches": []}, Path("/tmp/ledger.json"))  # doctest: +SKIP
    """
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    save_file(ledger, "w", ledger_path)


def cleanup_old_batches(ledger: dict, keep: int = 10) -> dict:
    """Trim committed batches to the most recent ``keep`` entries.

    Pending and failed batches are preserved untouched — only the
    "committed" history is bounded, since it grows unbounded over time
    and provides no further use beyond a short audit window.

    Args:
        ledger (dict): Ledger to mutate; must contain ``"batches"``.
        keep (int): Maximum number of committed batches to retain.

    Returns:
        dict: The same ledger object (mutated in place) for chaining.

    Example:
        >>> ledger = {"batches": [{"status": "committed"}] * 12}
        >>> len(cleanup_old_batches(ledger, keep=10)["batches"])
        10
    """
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
    """Return True if any EXCLUDE_PATTERNS regex matches ``filepath``.

    Example:
        >>> _is_excluded("state.jsonl")
        True
        >>> _is_excluded("src/foo.py")
        False
    """
    return any(p.search(filepath) for p in EXCLUDE_PATTERNS)


def _resolve_rename(filepath: str) -> str:
    """Collapse a porcelain rename token (``old -> new``) down to ``new``.

    Example:
        >>> _resolve_rename("a.py -> b.py")
        'b.py'
        >>> _resolve_rename("c.py")
        'c.py'
    """
    return filepath.split(" -> ")[-1] if " -> " in filepath else filepath


def _parse_porcelain_line(line: str) -> str | None:
    """Parse a single ``git status --porcelain`` line into a filepath.

    Drops lines shorter than 4 chars (porcelain format reserves the first
    three columns for status flags) and applies the EXCLUDE_PATTERNS
    filter so machine-generated paths (state.jsonl, __pycache__, locks)
    never enter a commit batch.

    Args:
        line (str): One raw line from ``git status --porcelain``.

    Returns:
        str | None: The resolved file path, or ``None`` if the line is
        too short or the path is excluded.

    Example:
        >>> _parse_porcelain_line(" M src/foo.py")
        'src/foo.py'
        >>> _parse_porcelain_line("?? state.jsonl") is None
        True
    """
    if not line or len(line) < 4:
        return None

    filepath = _resolve_rename(line[3:].strip())

    if _is_excluded(filepath):
        return None

    return filepath


def _git_status(project_dir: Path) -> str | None:
    """Run ``git status --porcelain -uall`` and return stdout, or ``None`` on failure.

    Example:
        >>> _git_status(Path("/repo"))  # doctest: +SKIP
    """
    result = run_git(["status", "--porcelain", "-uall"], cwd=project_dir)
    return result.stdout if result.returncode == 0 else None


def get_dirty_files(project_dir: Path) -> list[str]:
    """List dirty (modified or untracked) files filtered by EXCLUDE_PATTERNS.

    Args:
        project_dir (Path): Project root passed to ``git -C``.

    Returns:
        list[str]: Repo-relative paths in porcelain order; empty if git
        failed or there are no eligible changes.

    Example:
        >>> get_dirty_files(Path("/repo"))  # doctest: +SKIP
    """
    output = _git_status(project_dir)
    if output is None:
        return []

    lines = output.strip().splitlines()
    return [fp for line in lines if (fp := _parse_porcelain_line(line))]


def _git_add(files: list[str], project_dir: Path) -> bool:
    """Stage ``files``; return True iff git exited 0.

    Example:
        >>> _git_add(["src/foo.py"], Path("/repo"))  # doctest: +SKIP
    """
    return run_git(["add", *files], cwd=project_dir).returncode == 0


def _git_commit(message: str, project_dir: Path) -> bool:
    """Create a commit with ``message``; return True iff git exited 0.

    Example:
        >>> _git_commit("feat: x", Path("/repo"))  # doctest: +SKIP
    """
    return run_git(["commit", "-m", message], cwd=project_dir).returncode == 0


def commit_files(files: list[str], message: str, project_dir: Path) -> bool:
    """Stage ``files`` and commit them with ``message``.

    Args:
        files (list[str]): Paths to stage.
        message (str): Commit message.
        project_dir (Path): Repository root.

    Returns:
        bool: True only if both ``git add`` and ``git commit`` succeed.

    Example:
        >>> commit_files(["a.py"], "feat: a", Path("/repo"))  # doctest: +SKIP
    """
    return _git_add(files, project_dir) and _git_commit(message, project_dir)


# ---------------------------------------------------------------------------
# Batch claiming
# ---------------------------------------------------------------------------


def _is_batch_stale(batch: dict, stale_cutoff: datetime) -> bool:
    """Return True if a pending batch is older than the stale cutoff.

    Missing or unparseable ``created_at`` is treated as stale on purpose
    so a corrupt entry can't permanently lock its files out of future
    batches.

    Args:
        batch (dict): A ledger batch entry.
        stale_cutoff (datetime): Boundary datetime; entries created before
            this are stale.

    Returns:
        bool: True if the batch should be considered abandoned.

    Example:
        >>> from datetime import datetime
        >>> _is_batch_stale({"created_at": "2020-01-01T00:00:00"}, datetime(2025, 1, 1))
        True
        >>> _is_batch_stale({}, datetime(2025, 1, 1))
        True
    """
    try:
        created = datetime.fromisoformat(batch["created_at"])
        return created < stale_cutoff
    except (ValueError, KeyError):
        return True


def _collect_claimed_files(ledger: dict) -> set[str]:
    """Return file paths currently owned by active pending batches.

    Side effect: any pending batch older than STALE_THRESHOLD_MINUTES is
    flipped to ``"failed"`` in place so its files become claimable again.
    This is the GC mechanism for batches whose Phase-2/3 never completed
    (the async hook may be killed mid-run).

    Args:
        ledger (dict): Ledger to scan and mutate.

    Returns:
        set[str]: All file paths currently held by non-stale pending batches.

    Example:
        >>> from datetime import datetime
        >>> ledger = {"batches": [{"status": "pending", "files": ["a.py"],
        ...                         "created_at": datetime.now().isoformat()}]}
        >>> _collect_claimed_files(ledger)
        {'a.py'}
    """
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
    """Filter ``dirty_files`` to those not already owned by a pending batch.

    Args:
        dirty_files (list[str]): Candidate paths from ``get_dirty_files``.
        ledger (dict): Current ledger state (will be mutated to expire
            stale entries — see :func:`_collect_claimed_files`).

    Returns:
        list[str]: Paths the caller may safely claim, preserving the
        input order.

    Example:
        >>> claim_files(["a.py", "b.py"], {"batches": []})
        ['a.py', 'b.py']
    """
    claimed = _collect_claimed_files(ledger)
    return [f for f in dirty_files if f not in claimed]


# ---------------------------------------------------------------------------
# Commit message generation
# ---------------------------------------------------------------------------


def _build_commit_prompt(files: list[str], task_subject: str, task_description: str) -> str:
    """Render the headless-Claude prompt for commit message generation.

    Example:
        >>> "Files changed:" in _build_commit_prompt(["a.py"], "task", "desc")
        True
    """
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
    """Generate a conventional-commit message via headless Claude.

    Falls back to a synthesized ``chore:`` line when the Claude call
    times out or returns empty — the auto-commit must never silently
    drop work, so we always produce *some* message rather than abort.

    Args:
        files (list[str]): Paths included in the batch (informational
            only; not staged here).
        task_subject (str): Short task title for context.
        task_description (str): Longer task description for context.
        project_dir (Path): Working directory for the Claude invocation.

    Returns:
        str: The generated message, or the fallback string.

    Example:
        >>> generate_commit_message(["a.py"], "task", "desc", Path("/repo"))  # doctest: +SKIP
    """
    prompt = _build_commit_prompt(files, task_subject, task_description)
    output = invoke_headless_agent("claude", prompt, timeout=120, cwd=project_dir)
    return output or f"chore: auto-commit after task ({task_subject})"


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def _make_batch_id() -> str:
    """Generate a unique batch id of the form ``batch-<unix_ts>-<rand4>``.

    Example:
        >>> _make_batch_id().startswith("batch-")
        True
    """
    return f"batch-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:4]}"


def _get_unclaimed_files(project_dir: Path, ledger: dict) -> list[str] | None:
    """Return dirty files not held by another batch, or ``None`` if nothing to commit.

    Args:
        project_dir (Path): Repository root.
        ledger (dict): Current ledger state.

    Returns:
        list[str] | None: List of claimable files, or ``None`` when
        either there are no dirty files or all of them are already claimed.

    Example:
        >>> _get_unclaimed_files(Path("/repo"), {"batches": []})  # doctest: +SKIP
    """
    dirty = get_dirty_files(project_dir)
    if not dirty:
        return None
    claimed = claim_files(dirty, ledger)
    return claimed or None


def _add_pending_batch(
    ledger: dict, batch_id: str, task_id: str, task_subject: str, files: list[str],
) -> None:
    """Append a new ``pending`` batch entry to the ledger.

    Args:
        ledger (dict): Ledger to mutate in place.
        batch_id (str): Unique id from :func:`_make_batch_id`.
        task_id (str): Originating task id from the hook payload.
        task_subject (str): Task subject for downstream display.
        files (list[str]): Claimed file paths to record on the entry.

    Example:
        >>> ledger = {"batches": []}
        >>> _add_pending_batch(ledger, "batch-1", "T-1", "task", ["a.py"])
        >>> ledger["batches"][0]["status"]
        'pending'
    """
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
    """Phase 1: acquire the lock and claim dirty files.

    Wraps :func:`_claim_under_lock` with broad exception suppression
    because the async hook must never raise into the parent process.

    Args:
        batch_id (str): Pre-generated batch id.
        task_id (str): Hook ``task_id``.
        task_subject (str): Hook ``task_subject``.
        project_dir (Path): Repository root.
        ledger_path (Path): Path to the ledger JSON.
        lock: A ``filelock.FileLock``-compatible context manager.

    Returns:
        list[str] | None: The claimed files, or ``None`` if nothing was
        claimed or any error occurred.

    Example:
        >>> _claim_phase("b1", "T1", "task", Path("/repo"), Path("/tmp/l.json"), lock)  # doctest: +SKIP
    """
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
    """Inner body of Phase 1, executed while the file lock is held.

    Args:
        batch_id (str): Pre-generated batch id.
        task_id (str): Hook ``task_id``.
        task_subject (str): Hook ``task_subject``.
        project_dir (Path): Repository root.
        ledger_path (Path): Path to the ledger JSON.

    Returns:
        list[str] | None: Claimed files, or ``None`` when there is
        nothing to commit.

    Example:
        >>> _claim_under_lock("b1", "T1", "task", Path("/repo"), Path("/tmp/l.json"))  # doctest: +SKIP
    """
    ledger = load_ledger(ledger_path)
    claimed = _get_unclaimed_files(project_dir, ledger)
    if not claimed:
        return None
    _add_pending_batch(ledger, batch_id, task_id, task_subject, claimed)
    save_ledger(ledger, ledger_path)
    return claimed


def _update_batch_status(ledger: dict, batch_id: str, success: bool, message: str) -> None:
    """Flip a batch entry to ``committed`` or ``failed`` and stash its message.

    Args:
        ledger (dict): Ledger to mutate.
        batch_id (str): Id of the batch to update.
        success (bool): Whether the git commit succeeded.
        message (str): Commit message to record on success.

    Example:
        >>> ledger = {"batches": [{"batch_id": "b1", "status": "pending"}]}
        >>> _update_batch_status(ledger, "b1", True, "feat: x")
        >>> ledger["batches"][0]["status"]
        'committed'
    """
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
    """Phase 3: re-acquire the lock, commit, and update the ledger.

    Reloads the ledger fresh from disk before mutating because Phase 2
    ran with the lock released, so other invocations may have appended
    new batches we need to preserve.

    Args:
        batch_id (str): Id of the pending batch.
        claimed (list[str]): Files to stage and commit.
        message (str): Commit message generated in Phase 2.
        project_dir (Path): Repository root.
        ledger_path (Path): Ledger JSON path.
        lock: File-lock context manager.

    Returns:
        bool: True if the git commit succeeded, False otherwise.

    Example:
        >>> _commit_phase("b1", ["a.py"], "feat: a", Path("/repo"), Path("/tmp/l.json"), lock)  # doctest: +SKIP
    """
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
    """Pull task fields and cwd out of the hook stdin payload.

    Example:
        >>> _read_task_inputs()  # doctest: +SKIP
    """
    raw = Hook.read_stdin()
    return (
        raw.get("task_subject", "unknown task"),
        raw.get("task_id", "unknown"),
        raw.get("task_description", ""),
        Path(raw.get("cwd", os.getcwd())),
    )


def main() -> None:
    """Hook entry point — runs Phase 1 → Phase 2 → Phase 3.

    Returns silently if Phase 1 claims nothing (no dirty files or
    everything is already claimed by another batch). On a successful
    commit, emits a Hook system message so the user sees the auto-commit
    in the session transcript.

    Example:
        >>> main()  # doctest: +SKIP
    """
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
