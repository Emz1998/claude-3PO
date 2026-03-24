#!/usr/bin/env python3
# .claude/hooks/file_lock.py
# /// script
# dependencies = ["filelock"]
# ///

import json
import sys
import os
import time
from pathlib import Path
from filelock import SoftFileLock, Timeout

LOCK_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "locks"
LOCK_TIMEOUT = 1
LOCKING_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def get_file_path(tool_input: dict) -> str | None:
    return (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("notebook_path")
    )


def lock_path_for(file_path: str) -> Path:
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    safe = file_path.replace("/", "_").replace("\\", "_").strip("_")
    return LOCK_DIR / f"{safe}.lock"


def main():
    hook_input = json.load(sys.stdin)
    session_id = hook_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")

    if hook_input.get("tool_name") not in LOCKING_TOOLS:
        sys.exit(0)

    file_path = get_file_path(hook_input.get("tool_input", {}))
    if not file_path:
        sys.exit(0)

    lock_path = lock_path_for(file_path)
    lock = SoftFileLock(lock_path, timeout=LOCK_TIMEOUT)

    try:
        lock.acquire()  # blocks and polls until acquired or timeout
    except Timeout:
        print(
            f"[file_lock] TIMEOUT: could not acquire lock on '{file_path}' "
            f"after {LOCK_TIMEOUT}s. Another session may be editing it.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Write session metadata into the lock file for visibility
    lock_path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "pid": os.getpid(),
                "file": file_path,
                "acquired_at": time.time(),
            }
        )
    )

    # Track held locks for this session so PostToolUse + SessionEnd can clean up
    registry = LOCK_DIR / f"{session_id}.registry"
    held = json.loads(registry.read_text()) if registry.exists() else []
    if str(lock_path) not in held:
        held.append(str(lock_path))
    registry.write_text(json.dumps(held))

    print(
        json.dumps(
            {"additionalContext": f"[file_lock] Lock acquired on '{file_path}'."}
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
