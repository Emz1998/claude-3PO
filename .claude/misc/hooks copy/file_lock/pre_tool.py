#!/usr/bin/env python3
import sys
import json
import os
import time
import hashlib
from pathlib import Path
from filelock import FileLock, Timeout

input_data = json.load(sys.stdin)
file_path = input_data.get("tool_input", {}).get("file_path", "")
session_id = input_data.get("session_id", "unknown")

if not file_path:
    sys.exit(0)

lock_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "locks"
lock_dir.mkdir(parents=True, exist_ok=True)

short_name = Path(file_path).name
hash_id = hashlib.sha256(file_path.encode()).hexdigest()[:8]
safe_name = f"{short_name}_{hash_id}"
lock_path = lock_dir / f"{safe_name}.lock"
meta_path = lock_dir / f"{safe_name}.meta"

try:
    lock = FileLock(lock_path, timeout=0)
    lock.acquire()

    meta_path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "file_path": file_path,
                "status": "in_progress",
                "locked_at": time.time(),
            }
        )
    )
    sys.exit(0)

except Timeout:
    try:
        info = json.loads(meta_path.read_text())
        holder = info.get("session_id", "unknown")
        status = info.get("status", "unknown")
        age = time.time() - info.get("locked_at", 0)
    except Exception:
        holder, status, age = "unknown", "unknown", 999

    if status == "done" or age > 30:
        FileLock(lock_path, timeout=2).acquire()
        meta_path.write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "file_path": file_path,
                    "status": "in_progress",
                    "locked_at": time.time(),
                }
            )
        )
        sys.exit(0)

    print(f"Blocked: {file_path} locked by {holder} ({age:.0f}s ago)", file=sys.stderr)
    sys.exit(2)

except Exception as e:
    print(f"Lock error: {e}", file=sys.stderr)
    sys.exit(0)
