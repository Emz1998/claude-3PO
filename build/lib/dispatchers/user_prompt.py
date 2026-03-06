#!/usr/bin/env python3
"""UserPromptSubmit dispatcher — thin entry point with error isolation."""

import os
import sys
import json
import traceback
from pathlib import Path

project_dir = os.environ.get(
    "CLAUDE_PROJECT_DIR",
    str(Path(__file__).resolve().parents[3]),
)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from scripts.claude_hooks.handlers import get_handlers


def main() -> None:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    for handler in get_handlers("UserPromptSubmit"):
        try:
            handler(hook_input)
        except SystemExit:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
