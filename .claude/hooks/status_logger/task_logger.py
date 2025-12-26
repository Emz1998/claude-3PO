#!/usr/bin/env python3
# Task Status Logger Module - Updates task status in roadmap

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.output import log, block_response
from utils.validation import validate_task, InvalidFormatError
from utils.roadmap import (
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    save_roadmap,
    find_task_in_roadmap,
    run_auto_resolver,
    all_acs_met,
    get_unmet_acs,
    get_incomplete_task_deps,
    get_incomplete_milestone_deps,
)

VALID_STATUSES = ["not_started", "in_progress", "completed", "blocked"]


def parse_args(args_str: str) -> tuple[str, str] | None:
    """Parse args string in format '<task-id> <status>'."""
    if not args_str:
        return None
    parts = args_str.strip().split()
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def validate_status(status: str) -> bool:
    """Validate status is one of the valid statuses."""
    return status in VALID_STATUSES


def process(args: str) -> None:
    """Process task status update."""
    # Parse args
    parsed = parse_args(args)
    if parsed is None:
        block_response(
            "Invalid args format. Expected: '<task-id> <status>'. Example: 'T001 completed'"
        )

    task_id, status = parsed

    # Validate task ID format
    try:
        validate_task(task_id)
    except InvalidFormatError as e:
        block_response(str(e))

    # Validate status
    if not validate_status(status):
        block_response(
            f"Invalid status: '{status}'. Valid statuses: {', '.join(VALID_STATUSES)}"
        )

    # Get current version
    version = get_current_version()
    if not version:
        block_response(
            "Could not retrieve current_version from project/product/PRD.json"
        )

    # Get roadmap path
    roadmap_path = get_roadmap_path(version)
    if not roadmap_path.exists():
        block_response(f"Roadmap not found at: {roadmap_path}")

    # Load roadmap and validate task exists
    roadmap = load_roadmap(roadmap_path)
    if roadmap is None:
        block_response(f"Could not load roadmap from: {roadmap_path}")

    _phase, milestone, task = find_task_in_roadmap(roadmap, task_id)
    if task is None or milestone is None:
        block_response(f"Task '{task_id}' not found in roadmap")
    assert milestone is not None and task is not None

    # Check dependencies before allowing in_progress
    if status == "in_progress":
        # Check milestone dependencies first
        incomplete_ms_deps = get_incomplete_milestone_deps(roadmap, milestone)
        if incomplete_ms_deps:
            block_response(
                f"Cannot start task '{task_id}'. "
                f"Milestone '{milestone.get('id')}' has incomplete dependencies: "
                f"{', '.join(incomplete_ms_deps)}. Complete them first."
            )

        # Check task dependencies
        incomplete_task_deps = get_incomplete_task_deps(roadmap, task)
        if incomplete_task_deps:
            block_response(
                f"Cannot start task '{task_id}'. "
                f"Incomplete task dependencies: {', '.join(incomplete_task_deps)}. "
                f"Complete them first."
            )

    if status == "completed" and not all_acs_met(task):
        unmet = get_unmet_acs(task)
        block_response(
            f"Cannot mark task '{task_id}' as completed. "
            f"Unmet acceptance criteria: {', '.join(unmet)}. "
            f"Mark all ACs as 'met' first using /log:ac <AC-ID> met"
        )

    task["status"] = status
    if not save_roadmap(roadmap_path, roadmap):
        block_response(f"Failed to update task status for '{task_id}'")

    log(f"Task '{task_id}' status updated to '{status}'")

    # Run auto-resolver
    _success, resolutions = run_auto_resolver()
    for msg in resolutions:
        log(msg)

    sys.exit(0)
