#!/usr/bin/env python3
# .claude/hooks/session_cleanup.py
# /// script
# dependencies = ["filelock"]
# ///

import json
import sys
import os
from pathlib import Path

LOCK_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "locks"
SESSION_ID = os.environ.get("CLAUDE_SESSION_ID", "unknown")


def main():
    registry = LOCK_DIR / f"{SESSION_ID}.registry"
    if not registry.exists():
        sys.exit(0)

    held = json.loads(registry.read_text())
    for lp in held:
        lock_path = Path(lp)
        lock_path.unlink(missing_ok=True)
        print(
            f"[session_cleanup] Released stale lock: {lock_path.name}", file=sys.stderr
        )

    registry.unlink(missing_ok=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
