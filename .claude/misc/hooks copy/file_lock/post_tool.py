#!/usr/bin/env python3
import sys
import json
import os
import hashlib
from pathlib import Path
from filelock import FileLock

input_data = json.load(sys.stdin)
file_path = input_data.get("tool_input", {}).get("file_path", "")
session_id = input_data.get("session_id", "unknown")

if not file_path:
    sys.exit(0)

lock_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "locks"
short_name = Path(file_path).name
hash_id = hashlib.sha256(file_path.encode()).hexdigest()[:8]
safe_name = f"{short_name}_{hash_id}"
meta_path = lock_dir / f"{safe_name}.meta"

try:
    if meta_path.exists():
        info = json.loads(meta_path.read_text())
        if info.get("session_id") == session_id:
            info["status"] = "done"
            meta_path.write_text(json.dumps(info))
except Exception:
    pass

sys.exit(0)
