#!/usr/bin/env python3
"""Inject roadmap context into Claude session on start."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import print_and_exit, read_stdin_json, load_json  # type: ignore
from utils.roadmap import (  # type: ignore
    get_current_version,
    get_roadmap_path,
    get_project_dir,
    load_roadmap,
    find_task_in_roadmap,
    find_milestone_in_roadmap,
    get_unmet_acs,
    get_unmet_scs,
)


# PRD lookup cache
_prd_cache: dict | None = None


def load_prd() -> dict | None:
    """Load PRD.json and cache it."""
    global _prd_cache
    if _prd_cache is not None:
        return _prd_cache

    project_dir = get_project_dir()
    prd_path = project_dir / "project" / "product" / "PRD.json"
    _prd_cache = load_json(str(prd_path))
    return _prd_cache


def build_ac_sc_lookup(prd: dict) -> tuple[dict, dict]:
    """Build lookup dictionaries for AC and SC from PRD.

    Returns:
        Tuple of (ac_lookup, sc_lookup) where each maps ID to details.
    """
    ac_lookup: dict = {}
    sc_lookup: dict = {}

    for version in prd.get("versions", []):
        for feature in version.get("features", []):
            # Extract acceptance criteria from user stories
            for user_story in feature.get("user_stories", []):
                for ac in user_story.get("acceptance_criteria", []):
                    ac_id = ac.get("id", "")
                    if ac_id:
                        ac_lookup[ac_id] = {
                            "criteria": ac.get("criteria", ""),
                            "user_story": user_story.get("title", ""),
                            "feature": feature.get("name", ""),
                        }

            # Extract success criteria from feature
            for sc in feature.get("success_criteria", []):
                sc_id = sc.get("id", "")
                if sc_id:
                    sc_lookup[sc_id] = {
                        "title": sc.get("title", ""),
                        "description": sc.get("description", ""),
                        "feature": feature.get("name", ""),
                    }

    return ac_lookup, sc_lookup


def get_ac_context(ac_id: str, ac_lookup: dict) -> str:
    """Get full context for an acceptance criterion."""
    ac = ac_lookup.get(ac_id)
    if not ac:
        return ac_id
    return ac.get("criteria", ac_id)


def get_sc_context(sc_id: str, sc_lookup: dict) -> str:
    """Get full context for a success criterion."""
    sc = sc_lookup.get(sc_id)
    if not sc:
        return sc_id
    title = sc.get("title", "")
    desc = sc.get("description", "")
    if title and desc:
        return f"{title}: {desc}"
    return title or desc or sc_id


CONTEXT_TEMPLATE = """\
# Session Context

Project: {project_name}
Version: {version}
Target Release: {target_release}

## Progress
{progress}

## Current Phase
{phase}

## Current Milestone
{milestone}

## Milestone Tasks
{all_tasks}
{blockers}
"""


def find_next_pending_work(
    roadmap: dict,
) -> tuple[dict | None, dict | None, dict | None]:
    """Find the next pending phase, milestone, and task."""
    for phase in roadmap.get("phases", []):
        if phase.get("status") == "completed":
            continue
        for milestone in phase.get("milestones", []):
            if milestone.get("status") == "completed":
                continue
            for task in milestone.get("tasks", []):
                if task.get("status") != "completed":
                    return phase, milestone, task
    return None, None, None


def get_current_items(roadmap: dict) -> tuple[dict | None, dict | None, dict | None]:
    """Get current phase, milestone, and task from roadmap."""
    current = roadmap.get("current", {})
    phase_id = current.get("phase")
    milestone_id = current.get("milestone")
    task_id = current.get("task")

    if not phase_id or not milestone_id or not task_id:
        return find_next_pending_work(roadmap)

    phase, milestone = find_milestone_in_roadmap(roadmap, milestone_id)
    _, _, task = find_task_in_roadmap(roadmap, task_id)

    if task and task.get("status") == "completed":
        return find_next_pending_work(roadmap)

    return phase, milestone, task


def format_progress(roadmap: dict) -> str:
    """Format roadmap progress summary."""
    summary = roadmap.get("summary", {})
    p = summary.get("phases", {})
    m = summary.get("milestones", {})
    t = summary.get("tasks", {})
    return f"Phases: {p.get('completed', 0)}/{p.get('total', 0)} | Milestones: {m.get('completed', 0)}/{m.get('total', 0)} | Tasks: {t.get('completed', 0)}/{t.get('total', 0)}"


def format_phase(phase: dict) -> str:
    """Format phase information."""
    return f"[{phase.get('id')}] {phase.get('name')} ({phase.get('status')})"


def format_criteria(
    items: list,
    label: str,
    ac_lookup: dict | None = None,
    sc_lookup: dict | None = None,
) -> str:
    """Format success or acceptance criteria list with full context.

    Args:
        items: List of criteria items from roadmap
        label: "Success Criteria" or "Acceptance Criteria"
        ac_lookup: Lookup dict for acceptance criteria from PRD
        sc_lookup: Lookup dict for success criteria from PRD
    """
    if not items:
        return ""

    lines = [f"  {label}:"]
    is_ac = label == "Acceptance Criteria"
    lookup = ac_lookup if is_ac else sc_lookup

    for item in items:
        marker = "[x]" if item.get("status") == "met" else "[ ]"
        id_ref = item.get("id_reference", "")

        # Get full context from PRD lookup
        if lookup and id_ref:
            if is_ac:
                context = get_ac_context(id_ref, lookup)
            else:
                context = get_sc_context(id_ref, lookup)
            lines.append(f"    {marker} {id_ref}: {context}")
        else:
            lines.append(f"    {marker} {id_ref}")

    return "\n".join(lines)


def format_milestone(
    milestone: dict,
    sc_lookup: dict | None = None,
) -> str:
    """Format milestone with feature, goal, and SC."""
    ms_id = milestone.get("id", "")
    name = milestone.get("name", "")
    status = milestone.get("status", "")
    feature = milestone.get("feature", "")
    goal = milestone.get("goal", "")
    scs = milestone.get("success_criteria", [])

    template = f"""\
[{ms_id}] {name} ({status})
  Feature: {feature} (Read from `project/product/PRD.json`)
  Goal: {goal}
{format_criteria(scs, "Success Criteria", sc_lookup=sc_lookup)}"""
    return template


def format_task(
    task: dict,
    ac_lookup: dict | None = None,
) -> str:
    """Format task with owner, deps, and AC."""
    task_id = task.get("id", "")
    desc = task.get("description", "")
    status = task.get("status", "")
    owner = task.get("owner", "")
    deps = task.get("dependencies", [])
    acs = task.get("acceptance_criteria", [])

    deps_str = f"\n  Dependencies: {', '.join(deps)}" if deps else ""
    ac_str = (
        f"\n{format_criteria(acs, 'Acceptance Criteria', ac_lookup=ac_lookup)}"
        if acs
        else ""
    )

    return f"""\
[{task_id}] {desc} ({status})
  Owner: {owner}{deps_str}{ac_str}"""


def format_all_tasks(
    milestone: dict,
    current_task_id: str,
    ac_lookup: dict | None = None,
) -> str:
    """Format all tasks in milestone with status indicators."""
    tasks = milestone.get("tasks", [])
    if not tasks:
        return "No tasks in milestone"

    lines = []
    for task in tasks:
        task_id = task.get("id", "")
        desc = task.get("description", "")
        status = task.get("status", "not_started")
        owner = task.get("owner", "")

        # Status indicator
        if status == "completed":
            marker = "[x]"
        elif status == "in_progress":
            marker = "[~]"
        else:
            marker = "[ ]"

        # Current task indicator
        current = " <-- CURRENT" if task_id == current_task_id else ""

        # Format task line
        lines.append(f"{marker} [{task_id}] {desc}{current}")

        # Build metadata lines
        parallel = task.get("parallel", False)
        deps = task.get("dependencies", [])
        parallel_str = "Yes" if parallel else "No"
        deps_str = ", ".join(deps) if deps else "None"
        lines.append(f"    Status: {status}")
        lines.append(f"    Owner: {owner}")
        lines.append(f"    Parallel: {parallel_str}")
        lines.append(f"    Deps: {deps_str}")

        # Show acceptance criteria for all tasks
        acs = task.get("acceptance_criteria", [])
        if acs:
            lines.append("    Acceptance Criteria:")
            for ac in acs:
                ac_marker = "[x]" if ac.get("status") == "met" else "[ ]"
                ac_id = ac.get("id_reference", "")
                if ac_lookup and ac_id:
                    context = get_ac_context(ac_id, ac_lookup)
                    lines.append(f"      {ac_marker} {ac_id}: {context}")
                else:
                    lines.append(f"      {ac_marker} {ac_id}")

        lines.append("")  # Empty line between tasks

    return "\n".join(lines).rstrip()


def format_blockers(
    task: dict,
    milestone: dict,
    ac_lookup: dict | None = None,
    sc_lookup: dict | None = None,
) -> str:
    """Format blockers section with full context from PRD."""
    unmet_acs = get_unmet_acs(task)
    unmet_scs = get_unmet_scs(milestone)

    if not unmet_acs and not unmet_scs:
        return ""

    lines = ["\n--- Blockers ---"]

    if unmet_acs:
        lines.append("Unmet Acceptance Criteria:")
        for ac_id in unmet_acs:
            if ac_lookup:
                context = get_ac_context(ac_id, ac_lookup)
                lines.append(f"  - {ac_id}: {context}")
            else:
                lines.append(f"  - {ac_id}")

    if unmet_scs:
        lines.append("Unmet Success Criteria:")
        for sc_id in unmet_scs:
            if sc_lookup:
                context = get_sc_context(sc_id, sc_lookup)
                lines.append(f"  - {sc_id}: {context}")
            else:
                lines.append(f"  - {sc_id}")

    return "\n".join(lines)


def build_roadmap_context() -> tuple[str, str]:
    """Build roadmap context using template. Returns (context, version)."""
    version = get_current_version()
    if not version:
        return "Roadmap context unavailable: no current version found", ""

    roadmap_path = get_roadmap_path(version)
    roadmap = load_roadmap(roadmap_path)
    if not roadmap:
        return f"Roadmap context unavailable: could not load {roadmap_path}", ""

    phase, milestone, task = get_current_items(roadmap)
    if not phase or not milestone or not task:
        return "Roadmap context unavailable: no current phase/milestone/task", ""

    # Load PRD and build AC/SC lookups for full context
    ac_lookup: dict = {}
    sc_lookup: dict = {}
    prd = load_prd()
    if prd:
        ac_lookup, sc_lookup = build_ac_sc_lookup(prd)

    context = CONTEXT_TEMPLATE.format(
        project_name=roadmap.get("name", "Unknown"),
        version=roadmap.get("version", version),
        target_release=roadmap.get("target_release", "Not set"),
        progress=format_progress(roadmap),
        phase=format_phase(phase),
        milestone=format_milestone(milestone, sc_lookup=sc_lookup),
        all_tasks=format_all_tasks(milestone, task.get("id", ""), ac_lookup),
        blockers=format_blockers(task, milestone, ac_lookup, sc_lookup),
    )
    return context, version


def write_todo_file(context: str, version: str, session_id: str) -> None:
    """Write context to project/{version}/todos/todo_{date}_{session_id}.md."""
    if not version or not session_id:
        return

    project_dir = get_project_dir()
    todos_dir = project_dir / "project" / version / "todos"
    todos_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    short_session = session_id[:8] if len(session_id) > 8 else session_id
    filename = f"todo_{date_str}_{short_session}.md"
    filepath = todos_dir / filename

    filepath.write_text(context)


def main() -> None:
    """Main entry point for roadmap context injection."""
    try:
        hook_input = read_stdin_json()
        if not hook_input:
            sys.exit(0)

        hook_event = hook_input.get("hook_event_name", "")
        if hook_event != "SessionStart":
            sys.exit(0)

        session_id = hook_input.get("session_id", "")
        context, version = build_roadmap_context()

        write_todo_file(context, version, session_id)
        print_and_exit(context)

    except Exception as e:
        print(f"Roadmap context error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
