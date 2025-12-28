#!/usr/bin/env python3
"""Block stoppage if /build skill is active and milestone is in_progress."""

import json
import sys
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, get_cache, load_cache, write_cache  # type: ignore
from utils.roadmap import (  # type: ignore
    find_milestone_in_roadmap,
    get_current_version,
    get_roadmap_path,
    load_roadmap,
)

# Cache key to track if /build skill is active
BUILD_SKILL_CACHE_KEY = "build_skill_active"


def is_build_skill_active() -> bool:
    """Check if /build skill is currently active."""
    return get_cache(BUILD_SKILL_CACHE_KEY) is True


def deactivate_build_skill() -> None:
    """Deactivate /build skill tracking in cache."""
    cache = load_cache()
    cache[BUILD_SKILL_CACHE_KEY] = False
    write_cache(cache)


def block_stoppage(reason: str) -> NoReturn:
    """Output JSON to block stoppage and exit 0."""
    output = {"decision": "block", "reason": reason}
    print(json.dumps(output))
    sys.exit(0)


def allow_stoppage() -> NoReturn:
    """Output JSON to allow stoppage with continue: true."""
    output = {"continue": True}
    print(json.dumps(output))
    sys.exit(0)


def main() -> None:
    """Main stop guard logic. Only runs if /build skill is active."""
    try:
        read_stdin_json()

        # Only check milestone status if /build skill is active
        if not is_build_skill_active():
            allow_stoppage()

        # Get current version and roadmap
        version = get_current_version()
        if not version:
            deactivate_build_skill()
            allow_stoppage()

        roadmap_path = get_roadmap_path(version)
        if not roadmap_path.exists():
            deactivate_build_skill()
            allow_stoppage()

        roadmap = load_roadmap(roadmap_path)
        if roadmap is None:
            deactivate_build_skill()
            allow_stoppage()

        # Get current milestone from roadmap
        current = roadmap.get("current", {})
        current_milestone_id = current.get("milestone")

        if not current_milestone_id:
            deactivate_build_skill()
            allow_stoppage()

        # Find the current milestone
        _, milestone = find_milestone_in_roadmap(roadmap, current_milestone_id)
        if milestone is None:
            deactivate_build_skill()
            allow_stoppage()

        # Only block if milestone is in_progress (active work happening)
        milestone_status = milestone.get("status", "pending")
        if milestone_status == "in_progress":
            reason = (
                f"Cannot stop. Current milestone '{current_milestone_id}' "
                f"is 'in_progress'. Complete the milestone before stopping."
            )
            block_stoppage(reason)

        # Current milestone is completed, deactivate and allow stoppage
        deactivate_build_skill()
        allow_stoppage()

    except Exception as e:
        # On error, log and allow stoppage to avoid blocking indefinitely
        print(f"Stop guard error: {e}", file=sys.stderr)
        allow_stoppage()


if __name__ == "__main__":
    main()
