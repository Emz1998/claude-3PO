#!/usr/bin/env python3
"""PreToolUse hook to activate guardrails when /build skill is triggered."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, load_cache, write_cache  # type: ignore

SKILL_NAME = "implement"
GUARDRAIL_KEYS = [
    "is_implement_skill_active",
]


def main() -> None:
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    skill = input_data.get("tool_input", {}).get("skill", "")
    if skill == SKILL_NAME:
        cache = load_cache()
        cache.update({key: True for key in GUARDRAIL_KEYS})
        write_cache(cache)

    sys.exit(0)


if __name__ == "__main__":
    main()
