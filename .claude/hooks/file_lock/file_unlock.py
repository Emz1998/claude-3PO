#!/usr/bin/env python3
# .claude/hooks/file_unlock.py
# /// script
# dependencies = ["filelock"]
# ///

import json
import sys
import os
from pathlib import Path

LOCK_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "locks"
LOCKING_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def get_file_path(tool_input: dict) -> str | None:
    return (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("notebook_path")
    )


def release_lock(lock_path_str: str):
    lock_path = Path(lock_path_str)
    lock_path.unlink(missing_ok=True)
    print(f"[file_unlock] Released: {lock_path.name}", file=sys.stderr)


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

    registry = LOCK_DIR / f"{session_id}.registry"
    if not registry.exists():
        sys.exit(0)

    held = json.loads(registry.read_text())
    safe = file_path.replace("/", "_").replace("\\", "_").strip("_")
    target = str(LOCK_DIR / f"{safe}.lock")

    updated = []
    for lp in held:
        if lp == target:
            release_lock(lp)
        else:
            updated.append(lp)

    if updated:
        registry.write_text(json.dumps(updated))
    else:
        registry.unlink(missing_ok=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
