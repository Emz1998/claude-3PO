#!/usr/bin/env python3
"""Query roadmap.json for project status, phases, milestones, tasks, AC, and SC."""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ID patterns
PHASE_PATTERN = r"^PH-\d{3}$"
MILESTONE_PATTERN = r"^MS-\d{3}$"
TASK_PATTERN = r"^T\d{3}$"
AC_PATTERN = r"^AC-\d{3}$"
SC_PATTERN = r"^SC-\d{3}$"


def get_project_dir() -> Path:
    """Get project directory from environment or cwd."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir)


def load_prd() -> dict | None:
    """Load PRD.json file."""
    prd_path = get_project_dir() / "project" / "product" / "PRD.json"
    if not prd_path.exists():
        return None
    try:
        with open(prd_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_current_version() -> str:
    """Retrieve current_version from PRD.json."""
    prd = load_prd()
    if prd is None:
        return ""
    return prd.get("current_version", "")


def get_roadmap_path(version: str) -> Path:
    """Get roadmap.json path for the given version."""
    return get_project_dir() / "project" / version / "release-plan" / "roadmap.json"


def load_roadmap(roadmap_path: Path) -> dict | None:
    """Load roadmap.json file."""
    if not roadmap_path.exists():
        return None
    try:
        with open(roadmap_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def detect_query_type(query_id: str) -> str | None:
    """Detect the type of query based on ID pattern."""
    if re.match(PHASE_PATTERN, query_id):
        return "phase"
    elif re.match(MILESTONE_PATTERN, query_id):
        return "milestone"
    elif re.match(TASK_PATTERN, query_id):
        return "task"
    elif re.match(AC_PATTERN, query_id):
        return "ac"
    elif re.match(SC_PATTERN, query_id):
        return "sc"
    return None


def find_phase(roadmap: dict, phase_id: str) -> dict | None:
    """Find phase by ID."""
    for phase in roadmap.get("phases", []):
        if phase.get("id") == phase_id:
            return phase
    return None


def find_milestone(roadmap: dict, milestone_id: str) -> tuple[dict | None, dict | None]:
    """Find milestone by ID. Returns (phase, milestone)."""
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            if milestone.get("id") == milestone_id:
                return phase, milestone
    return None, None


def find_task(roadmap: dict, task_id: str) -> tuple[dict | None, dict | None, dict | None]:
    """Find task by ID. Returns (phase, milestone, task)."""
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            for task in milestone.get("tasks", []):
                if task.get("id") == task_id:
                    return phase, milestone, task
    return None, None, None


def find_ac(roadmap: dict, ac_id: str) -> tuple[dict | None, dict | None, dict | None, dict | None]:
    """Find AC by ID. Returns (phase, milestone, task, ac)."""
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            for task in milestone.get("tasks", []):
                for ac in task.get("acceptance_criteria", []):
                    if ac.get("id") == ac_id:
                        return phase, milestone, task, ac
    return None, None, None, None


def find_sc(roadmap: dict, sc_id: str) -> tuple[dict | None, dict | None, dict | None]:
    """Find SC by ID. Returns (phase, milestone, sc)."""
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            for sc in milestone.get("success_criteria", []):
                if sc.get("id") == sc_id:
                    return phase, milestone, sc
    return None, None, None


def format_status(status: str) -> str:
    """Format status with indicator."""
    indicators = {
        "completed": "[✓]",
        "in_progress": "[~]",
        "not_started": "[ ]",
        "blocked": "[!]",
        "pending": "[ ]",
        "met": "[✓]",
        "unmet": "[ ]",
    }
    return f"{indicators.get(status, '[?]')} {status}"


def query_version(roadmap: dict) -> str:
    """Query version information."""
    lines = [
        f"Project: {roadmap.get('name', 'Unknown')}",
        f"Version: {roadmap.get('version', 'Unknown')}",
        f"Target Release: {roadmap.get('target_release', 'Unknown')}",
        f"Status: {format_status(roadmap.get('status', 'unknown'))}",
        "",
        "Summary:",
    ]
    summary = roadmap.get("summary", {})
    phases = summary.get("phases", {})
    milestones = summary.get("milestones", {})
    tasks = summary.get("tasks", {})
    lines.append(f"  Phases: {phases.get('completed', 0)}/{phases.get('total', 0)} completed")
    lines.append(f"  Milestones: {milestones.get('completed', 0)}/{milestones.get('total', 0)} completed")
    lines.append(f"  Tasks: {tasks.get('completed', 0)}/{tasks.get('total', 0)} completed")
    return "\n".join(lines)


def query_current(roadmap: dict) -> str:
    """Query current phase/milestone/task."""
    current = roadmap.get("current", {})
    lines = ["Current Focus:"]
    phase_id = current.get("phase")
    milestone_id = current.get("milestone")
    task_id = current.get("task")

    if phase_id:
        phase = find_phase(roadmap, phase_id)
        if phase:
            lines.append(f"  Phase: [{phase_id}] {phase.get('name', 'Unknown')}")
            lines.append(f"    Status: {format_status(phase.get('status', 'unknown'))}")

    if milestone_id:
        _, milestone = find_milestone(roadmap, milestone_id)
        if milestone:
            lines.append(f"  Milestone: [{milestone_id}] {milestone.get('name', 'Unknown')}")
            lines.append(f"    Status: {format_status(milestone.get('status', 'unknown'))}")
            lines.append(f"    Goal: {milestone.get('goal', 'None')}")

    if task_id:
        _, _, task = find_task(roadmap, task_id)
        if task:
            lines.append(f"  Task: [{task_id}] {task.get('description', 'Unknown')}")
            lines.append(f"    Status: {format_status(task.get('status', 'unknown'))}")
            lines.append(f"    Owner: {task.get('owner', 'Unknown')}")

    return "\n".join(lines)


def query_phases(roadmap: dict) -> str:
    """Query all phases."""
    lines = ["Phases:"]
    for phase in roadmap.get("phases", []):
        status = format_status(phase.get("status", "unknown"))
        milestones = phase.get("milestones", [])
        completed = sum(1 for m in milestones if m.get("status") == "completed")
        lines.append(f"  {status} [{phase.get('id')}] {phase.get('name', 'Unknown')}")
        lines.append(f"      Milestones: {completed}/{len(milestones)}")
    return "\n".join(lines)


def query_milestones(roadmap: dict, phase_id: str | None = None) -> str:
    """Query milestones, optionally filtered by phase."""
    lines = ["Milestones:"]
    for phase in roadmap.get("phases", []):
        if phase_id and phase.get("id") != phase_id:
            continue
        if not phase_id:
            lines.append(f"\n[{phase.get('id')}] {phase.get('name', 'Unknown')}:")
        for ms in phase.get("milestones", []):
            status = format_status(ms.get("status", "unknown"))
            tasks = ms.get("tasks", [])
            completed = sum(1 for t in tasks if t.get("status") == "completed")
            lines.append(f"  {status} [{ms.get('id')}] {ms.get('name', 'Unknown')}")
            lines.append(f"      Goal: {ms.get('goal', 'None')}")
            lines.append(f"      Tasks: {completed}/{len(tasks)}")
    return "\n".join(lines)


def query_tasks(roadmap: dict, milestone_id: str | None = None) -> str:
    """Query tasks, optionally filtered by milestone."""
    lines = ["Tasks:"]
    for phase in roadmap.get("phases", []):
        for ms in phase.get("milestones", []):
            if milestone_id and ms.get("id") != milestone_id:
                continue
            if not milestone_id:
                lines.append(f"\n[{ms.get('id')}] {ms.get('name', 'Unknown')}:")
            for task in ms.get("tasks", []):
                status = format_status(task.get("status", "unknown"))
                acs = task.get("acceptance_criteria", [])
                ac_met = sum(1 for ac in acs if ac.get("status") == "met")
                lines.append(f"  {status} [{task.get('id')}] {task.get('description', 'Unknown')}")
                lines.append(f"      Owner: {task.get('owner', 'Unknown')}")
                lines.append(f"      ACs: {ac_met}/{len(acs)} met")
                if task.get("dependencies"):
                    lines.append(f"      Deps: {', '.join(task.get('dependencies', []))}")
    return "\n".join(lines)


def query_acs(roadmap: dict, task_id: str | None = None) -> str:
    """Query acceptance criteria, optionally filtered by task."""
    lines = ["Acceptance Criteria:"]
    for phase in roadmap.get("phases", []):
        for ms in phase.get("milestones", []):
            for task in ms.get("tasks", []):
                if task_id and task.get("id") != task_id:
                    continue
                acs = task.get("acceptance_criteria", [])
                if acs:
                    if not task_id:
                        lines.append(f"\n[{task.get('id')}] {task.get('description', 'Unknown')[:50]}...")
                    for ac in acs:
                        status = format_status(ac.get("status", "unknown"))
                        lines.append(f"  {status} [{ac.get('id')}]")
    return "\n".join(lines)


def query_scs(roadmap: dict, milestone_id: str | None = None) -> str:
    """Query success criteria, optionally filtered by milestone."""
    lines = ["Success Criteria:"]
    for phase in roadmap.get("phases", []):
        for ms in phase.get("milestones", []):
            if milestone_id and ms.get("id") != milestone_id:
                continue
            scs = ms.get("success_criteria", [])
            if scs:
                if not milestone_id:
                    lines.append(f"\n[{ms.get('id')}] {ms.get('name', 'Unknown')}:")
                for sc in scs:
                    status = format_status(sc.get("status", "unknown"))
                    lines.append(f"  {status} [{sc.get('id')}]")
    return "\n".join(lines)


def query_phase_detail(roadmap: dict, phase_id: str) -> str:
    """Query detailed phase info."""
    phase = find_phase(roadmap, phase_id)
    if not phase:
        return f"Phase '{phase_id}' not found"

    milestones = phase.get("milestones", [])
    ms_completed = sum(1 for m in milestones if m.get("status") == "completed")
    total_tasks = sum(len(m.get("tasks", [])) for m in milestones)
    tasks_completed = sum(
        sum(1 for t in m.get("tasks", []) if t.get("status") == "completed")
        for m in milestones
    )

    lines = [
        f"Phase: [{phase_id}] {phase.get('name', 'Unknown')}",
        f"Status: {format_status(phase.get('status', 'unknown'))}",
        f"Milestones: {ms_completed}/{len(milestones)} completed",
        f"Tasks: {tasks_completed}/{total_tasks} completed",
        "",
        "Milestones:",
    ]

    for ms in milestones:
        status = format_status(ms.get("status", "unknown"))
        tasks = ms.get("tasks", [])
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        lines.append(f"  {status} [{ms.get('id')}] {ms.get('name', 'Unknown')}")
        lines.append(f"      Goal: {ms.get('goal', 'None')}")
        lines.append(f"      Tasks: {completed}/{len(tasks)}")
        if ms.get("dependencies"):
            lines.append(f"      Deps: {', '.join(ms.get('dependencies', []))}")

    return "\n".join(lines)


def query_milestone_detail(roadmap: dict, milestone_id: str) -> str:
    """Query detailed milestone info."""
    phase, milestone = find_milestone(roadmap, milestone_id)
    if not milestone:
        return f"Milestone '{milestone_id}' not found"

    tasks = milestone.get("tasks", [])
    tasks_completed = sum(1 for t in tasks if t.get("status") == "completed")
    scs = milestone.get("success_criteria", [])
    scs_met = sum(1 for sc in scs if sc.get("status") == "met")

    lines = [
        f"Milestone: [{milestone_id}] {milestone.get('name', 'Unknown')}",
        f"Phase: [{phase.get('id')}] {phase.get('name', 'Unknown')}" if phase else "",
        f"Feature: {milestone.get('feature', 'None')}",
        f"Goal: {milestone.get('goal', 'None')}",
        f"Status: {format_status(milestone.get('status', 'unknown'))}",
        f"Tasks: {tasks_completed}/{len(tasks)} completed",
        f"Success Criteria: {scs_met}/{len(scs)} met",
    ]

    if milestone.get("dependencies"):
        lines.append(f"Dependencies: {', '.join(milestone.get('dependencies', []))}")

    lines.append("")
    lines.append("Tasks:")
    for task in tasks:
        status = format_status(task.get("status", "unknown"))
        acs = task.get("acceptance_criteria", [])
        ac_met = sum(1 for ac in acs if ac.get("status") == "met")
        lines.append(f"  {status} [{task.get('id')}] {task.get('description', 'Unknown')}")
        lines.append(f"      Owner: {task.get('owner', 'Unknown')}, ACs: {ac_met}/{len(acs)}")

    lines.append("")
    lines.append("Success Criteria:")
    for sc in scs:
        status = format_status(sc.get("status", "unknown"))
        lines.append(f"  {status} [{sc.get('id')}]")

    return "\n".join([l for l in lines if l])


def query_task_detail(roadmap: dict, task_id: str) -> str:
    """Query detailed task info."""
    phase, milestone, task = find_task(roadmap, task_id)
    if not task:
        return f"Task '{task_id}' not found"

    acs = task.get("acceptance_criteria", [])
    acs_met = sum(1 for ac in acs if ac.get("status") == "met")

    lines = [
        f"Task: [{task_id}] {task.get('description', 'Unknown')}",
        f"Milestone: [{milestone.get('id')}] {milestone.get('name', 'Unknown')}" if milestone else "",
        f"Phase: [{phase.get('id')}] {phase.get('name', 'Unknown')}" if phase else "",
        f"Status: {format_status(task.get('status', 'unknown'))}",
        f"Owner: {task.get('owner', 'Unknown')}",
        f"Parallel: {task.get('parallel', False)}",
        f"Acceptance Criteria: {acs_met}/{len(acs)} met",
    ]

    if task.get("dependencies"):
        lines.append(f"Dependencies: {', '.join(task.get('dependencies', []))}")

    lines.append("")
    lines.append("Acceptance Criteria:")
    for ac in acs:
        status = format_status(ac.get("status", "unknown"))
        lines.append(f"  {status} [{ac.get('id')}]")

    return "\n".join([l for l in lines if l])


def query_ac_detail(roadmap: dict, ac_id: str) -> str:
    """Query detailed AC info."""
    phase, milestone, task, ac = find_ac(roadmap, ac_id)
    if not ac:
        return f"Acceptance Criteria '{ac_id}' not found"

    lines = [
        f"Acceptance Criteria: [{ac_id}]",
        f"Status: {format_status(ac.get('status', 'unknown'))}",
        f"Task: [{task.get('id')}] {task.get('description', 'Unknown')}" if task else "",
        f"Milestone: [{milestone.get('id')}] {milestone.get('name', 'Unknown')}" if milestone else "",
        f"Phase: [{phase.get('id')}] {phase.get('name', 'Unknown')}" if phase else "",
    ]

    return "\n".join([l for l in lines if l])


def query_sc_detail(roadmap: dict, sc_id: str) -> str:
    """Query detailed SC info."""
    phase, milestone, sc = find_sc(roadmap, sc_id)
    if not sc:
        return f"Success Criteria '{sc_id}' not found"

    lines = [
        f"Success Criteria: [{sc_id}]",
        f"Status: {format_status(sc.get('status', 'unknown'))}",
        f"Milestone: [{milestone.get('id')}] {milestone.get('name', 'Unknown')}" if milestone else "",
        f"Phase: [{phase.get('id')}] {phase.get('name', 'Unknown')}" if phase else "",
    ]

    return "\n".join([l for l in lines if l])


def query_blockers(roadmap: dict) -> str:
    """Query blocked items and unmet criteria."""
    lines = ["Blockers:"]
    blocked_tasks = []
    unmet_acs = []
    unmet_scs = []

    for phase in roadmap.get("phases", []):
        for ms in phase.get("milestones", []):
            for sc in ms.get("success_criteria", []):
                if sc.get("status") != "met":
                    unmet_scs.append((ms.get("id"), sc.get("id")))
            for task in ms.get("tasks", []):
                if task.get("status") == "blocked":
                    blocked_tasks.append((ms.get("id"), task.get("id"), task.get("description")))
                for ac in task.get("acceptance_criteria", []):
                    if ac.get("status") != "met":
                        unmet_acs.append((task.get("id"), ac.get("id")))

    if blocked_tasks:
        lines.append("\nBlocked Tasks:")
        for ms_id, t_id, desc in blocked_tasks:
            lines.append(f"  [!] [{t_id}] {desc[:50]}... (in {ms_id})")

    if unmet_acs:
        lines.append("\nUnmet Acceptance Criteria:")
        for t_id, ac_id in unmet_acs[:10]:
            lines.append(f"  [ ] [{ac_id}] (task: {t_id})")
        if len(unmet_acs) > 10:
            lines.append(f"  ... and {len(unmet_acs) - 10} more")

    if unmet_scs:
        lines.append("\nUnmet Success Criteria:")
        for ms_id, sc_id in unmet_scs[:10]:
            lines.append(f"  [ ] [{sc_id}] (milestone: {ms_id})")
        if len(unmet_scs) > 10:
            lines.append(f"  ... and {len(unmet_scs) - 10} more")

    if not blocked_tasks and not unmet_acs and not unmet_scs:
        lines.append("  No blockers found!")

    return "\n".join(lines)


def query_metadata(roadmap: dict) -> str:
    """Query metadata."""
    metadata = roadmap.get("metadata", {})
    lines = [
        "Metadata:",
        f"  Last Updated: {metadata.get('last_updated', 'Unknown')}",
        f"  Schema Version: {metadata.get('schema_version', 'Unknown')}",
    ]
    return "\n".join(lines)


def query_todo(roadmap: dict) -> str:
    """Query current milestone tasks with full context."""
    current = roadmap.get("current", {})
    current_phase_id = current.get("phase")
    current_milestone_id = current.get("milestone")
    current_task_id = current.get("task")

    if not current_phase_id or not current_milestone_id:
        return "No current phase/milestone set in roadmap"

    phase = find_phase(roadmap, current_phase_id)
    if not phase:
        return f"Phase '{current_phase_id}' not found"

    _, milestone = find_milestone(roadmap, current_milestone_id)
    if not milestone:
        return f"Milestone '{current_milestone_id}' not found"

    # Success Criteria
    scs = milestone.get("success_criteria", [])
    sc_met = sum(1 for sc in scs if sc.get("status") == "met")
    sc_list = ", ".join(
        f"{'[✓]' if sc.get('status') == 'met' else '[ ]'} {sc.get('id')}"
        for sc in scs
    ) if scs else "None"

    lines = [
        "TODO - Current Milestone Tasks",
        "=" * 60,
        f"Project: {roadmap.get('name', 'Unknown')}",
        f"Version: {roadmap.get('version', 'Unknown')}",
        "",
        f"Phase: [{phase.get('id')}] {phase.get('name', 'Unknown')}",
        "",
        f"Milestone: [{milestone.get('id')}] {milestone.get('name', 'Unknown')}",
        f"  Feature: {milestone.get('feature', 'None')}",
        f"  Goal: {milestone.get('goal', 'None')}",
    ]

    # Milestone dependencies
    ms_deps = milestone.get("dependencies", [])
    if ms_deps:
        lines.append(f"  Dependencies: {', '.join(ms_deps)}")

    # Success Criteria inline
    lines.append(f"  SC: {sc_met}/{len(scs)} met - {sc_list}")

    lines.append("")
    lines.append("-" * 60)
    lines.append("Tasks:")
    lines.append("")

    tasks = milestone.get("tasks", [])
    in_progress = 0
    not_started = 0
    completed = 0

    for task in tasks:
        task_status = task.get("status", "not_started")
        task_id = task.get("id")
        is_current = task_id == current_task_id

        # Count all tasks
        if task_status == "completed":
            completed += 1
            continue  # Skip completed tasks
        elif task_status == "in_progress":
            in_progress += 1
            indicator = "[~]"
        elif task_status == "blocked":
            indicator = "[!]"
        else:
            not_started += 1
            indicator = "[ ]"

        if is_current:
            lines.append(">>> CURRENT <<<")
        lines.append(f"{indicator} [{task_id}] {task.get('description', 'Unknown')}")
        lines.append(f"    Owner: {task.get('owner', 'Unknown')}")
        lines.append(f"    Parallel: {'Yes' if task.get('parallel', False) else 'No'}")

        # Task dependencies
        task_deps = task.get("dependencies", [])
        if task_deps:
            lines.append(f"    Deps: {', '.join(task_deps)}")

        # Acceptance Criteria
        acs = task.get("acceptance_criteria", [])
        if acs:
            ac_met = sum(1 for ac in acs if ac.get("status") == "met")
            lines.append(f"    ACs: {ac_met}/{len(acs)} met")
            for ac in acs:
                ac_status = "[✓]" if ac.get("status") == "met" else "[ ]"
                lines.append(f"      {ac_status} {ac.get('id')}")

        lines.append("")

    lines.append("=" * 60)
    lines.append(f"Summary: {completed} completed, {in_progress} in progress, {not_started} pending")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query roadmap.json for project information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Query Types:
  todo         Show current tasks to do with full context
  version      Show project version and summary
  current      Show current phase/milestone/task
  phases       List all phases
  milestones   List all milestones (optionally filter by phase)
  tasks        List all tasks (optionally filter by milestone)
  acs          List all acceptance criteria (optionally filter by task)
  scs          List all success criteria (optionally filter by milestone)
  blockers     Show blocked tasks and unmet criteria
  metadata     Show roadmap metadata

Specific Item Queries (by ID):
  PH-XXX       Show phase details (e.g., PH-001)
  MS-XXX       Show milestone details (e.g., MS-001)
  TXXX         Show task details (e.g., T001)
  AC-XXX       Show acceptance criteria details (e.g., AC-001)
  SC-XXX       Show success criteria details (e.g., SC-001)

Examples:
  %(prog)s todo             # Show current tasks with full context
  %(prog)s version          # Show project version info
  %(prog)s current          # Show current focus
  %(prog)s phases           # List all phases
  %(prog)s milestones       # List all milestones
  %(prog)s tasks MS-001     # List tasks in milestone MS-001
  %(prog)s PH-001           # Show phase PH-001 details
  %(prog)s MS-001           # Show milestone MS-001 details
  %(prog)s T001             # Show task T001 details
  %(prog)s AC-001           # Show AC-001 details
  %(prog)s blockers         # Show all blockers
        """
    )
    parser.add_argument(
        "query",
        type=str,
        help="Query type or item ID"
    )
    parser.add_argument(
        "filter_id",
        type=str,
        nargs="?",
        default=None,
        help="Optional filter ID (e.g., phase ID for milestones, milestone ID for tasks)"
    )
    args = parser.parse_args()

    query = args.query
    filter_id = args.filter_id.upper() if args.filter_id else None

    version = get_current_version()
    if not version:
        print("Error: Could not retrieve current_version from project/product/PRD.json", file=sys.stderr)
        sys.exit(1)

    roadmap_path = get_roadmap_path(version)
    if not roadmap_path.exists():
        print(f"Error: Roadmap not found at: {roadmap_path}", file=sys.stderr)
        sys.exit(1)

    roadmap = load_roadmap(roadmap_path)
    if roadmap is None:
        print(f"Error: Could not load roadmap from: {roadmap_path}", file=sys.stderr)
        sys.exit(1)

    # Handle specific ID queries
    query_upper = query.upper()
    query_type = detect_query_type(query_upper)
    if query_type:
        if query_type == "phase":
            result = query_phase_detail(roadmap, query_upper)
        elif query_type == "milestone":
            result = query_milestone_detail(roadmap, query_upper)
        elif query_type == "task":
            result = query_task_detail(roadmap, query_upper)
        elif query_type == "ac":
            result = query_ac_detail(roadmap, query_upper)
        elif query_type == "sc":
            result = query_sc_detail(roadmap, query_upper)
        else:
            result = f"Unknown query type: {query}"
        print(result)
        return

    # Handle named queries
    query_lower = query.lower()
    if query_lower == "todo":
        result = query_todo(roadmap)
    elif query_lower == "version":
        result = query_version(roadmap)
    elif query_lower == "current":
        result = query_current(roadmap)
    elif query_lower == "phases":
        result = query_phases(roadmap)
    elif query_lower == "milestones":
        result = query_milestones(roadmap, filter_id)
    elif query_lower == "tasks":
        result = query_tasks(roadmap, filter_id)
    elif query_lower == "acs":
        result = query_acs(roadmap, filter_id)
    elif query_lower == "scs":
        result = query_scs(roadmap, filter_id)
    elif query_lower == "blockers":
        result = query_blockers(roadmap)
    elif query_lower == "metadata":
        result = query_metadata(roadmap)
    else:
        print(f"Error: Unknown query '{query}'. Use --help for usage.", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
