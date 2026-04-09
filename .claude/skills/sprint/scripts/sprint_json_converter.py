"""Convert sprint.md to sprint.json matching sample_structure.json format."""

import re
from typing import Any


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _story_type(prefix: str) -> str:
    """Map story ID prefix to type string."""
    mapping = {"US": "User Story", "TS": "Technical Story", "BG": "Bug", "SK": "Spike"}
    return mapping.get(prefix, "User Story")


def _parse_csv(raw: str, skip: tuple[str, ...] = ("-", "None", "none", "")) -> list[str]:
    """Split a comma-separated field, filtering out sentinel values."""
    raw = raw.strip()
    if raw in skip:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def _parse_field(block: str, label: str) -> str:
    """Extract a single **Label:** value from a block."""
    match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", block)
    return match.group(1).strip() if match else ""


def parse_sprint_md(content: str) -> dict[str, Any]:
    lines = content.split("\n")

    sprint: int = 0
    milestone: str = ""
    description: str = ""
    due_date: str = ""

    for line in lines:
        if line.startswith("**Sprint #:**"):
            sprint = _safe_int(line.split("**Sprint #:**")[1].strip())
        elif line.startswith("**Goal:**"):
            description = line.split("**Goal:**")[1].strip()
        elif line.startswith("**Milestone:**"):
            milestone = line.split("**Milestone:**")[1].strip()
        elif line.startswith("**Due Date:**"):
            due_date = line.split("**Due Date:**")[1].strip()
        elif line.startswith("**Dates:**"):
            dates_raw = line.split("**Dates:**")[1].strip()
            parts = [d.strip() for d in re.split(r"→|->|to", dates_raw)]
            due_date = parts[1] if len(parts) > 1 else parts[0] if parts else ""

    # Parse story sections
    story_pattern = r"#### ([A-Z]{2})-(\d+):\s*(.+?)(?:\n|$)"
    story_matches = list(re.finditer(story_pattern, content))

    stories: list[dict[str, Any]] = []

    for idx, smatch in enumerate(story_matches):
        prefix = smatch.group(1)
        story_num = smatch.group(2)
        story_id = f"{prefix}-{story_num}"
        story_title = smatch.group(3).strip()

        # Extract story block (until next story or end)
        start = smatch.end()
        end = story_matches[idx + 1].start() if idx + 1 < len(story_matches) else len(content)
        block = content[start:end]

        # Story description from blockquote
        desc_match = re.search(r">\s*(.+?)(?:\n(?!>)|$)", block, re.DOTALL)
        story_desc = ""
        if desc_match:
            raw_desc = desc_match.group(0)
            story_desc = re.sub(r"\n>\s*", " ", raw_desc).strip().lstrip("> ").strip()

        # Story-level fields
        status = _parse_field(block, "Status") or "Ready"
        priority = _parse_field(block, "Priority")
        labels = _parse_csv(_parse_field(block, "Labels"))
        points = _safe_int(_parse_field(block, "Points"))
        tdd_raw = _parse_field(block, "TDD").lower()
        tdd = tdd_raw == "true"
        is_blocking = _parse_csv(_parse_field(block, "Is Blocking"))
        blocked_by = _parse_csv(_parse_field(block, "Blocked By"))
        start_date = _parse_field(block, "Start Date")
        target_date = _parse_field(block, "Target Date")

        # Story-level acceptance criteria (before tasks section)
        tasks_marker = block.find("**Tasks:**")
        ac_block = block[:tasks_marker] if tasks_marker != -1 else block
        acceptance_criteria = re.findall(r"- \[[ x]\] (.+)", ac_block)

        # Parse tasks
        tasks = _parse_tasks(block, milestone)

        # For spikes without tasks, build from deliverables
        if _story_type(prefix) == "Spike" and not tasks:
            tasks = _parse_spike_as_tasks(block, story_id, milestone)

        # Compute is_blocking across tasks
        _compute_is_blocking(tasks)

        story: dict[str, Any] = {
            "id": story_id,
            "type": _story_type(prefix),
            "labels": labels,
            "title": story_title,
            "description": story_desc,
            "points": points,
            "status": status,
            "tdd": tdd,
            "priority": priority,
            "is_blocking": is_blocking,
            "blocked_by": blocked_by,
            "acceptance_criteria": acceptance_criteria,
            "item_type": "story",
            "milestone": milestone,
            "start_date": start_date,
            "target_date": target_date,
            "tasks": tasks,
        }
        stories.append(story)

    return {
        "sprint": sprint,
        "milestone": milestone,
        "description": description,
        "due_date": due_date,
        "stories": stories,
    }


def _parse_tasks(block: str, milestone: str) -> list[dict[str, Any]]:
    """Parse task entries from a story block."""
    tasks: list[dict[str, Any]] = []
    task_splits = re.split(r"- \*\*T-(\d+):\*\*", block)

    for i in range(1, len(task_splits), 2):
        task_id = f"T-{task_splits[i]}"
        task_body = task_splits[i + 1]

        title_match = re.match(r"\s*(.+?)(?:\n|$)", task_body)
        title = title_match.group(1).strip() if title_match else ""

        status = _parse_field(task_body, "Status") or "Backlog"
        complexity = _parse_field(task_body, "Complexity")
        priority = _parse_field(task_body, "Priority")
        labels = _parse_csv(_parse_field(task_body, "Labels"))
        desc = _parse_field(task_body, "Description")

        blocked_by_raw = _parse_field(task_body, "Blocked by")
        if not blocked_by_raw:
            blocked_by_raw = _parse_field(task_body, "Depends on")
        blocked_by = _parse_csv(blocked_by_raw)

        ac_items = re.findall(r"- \[[ x]\] (.+)", task_body)

        start_date = _parse_field(task_body, "Start date")
        target_date = _parse_field(task_body, "Target date")

        tasks.append({
            "id": task_id,
            "type": "task",
            "labels": labels,
            "title": title,
            "description": desc,
            "status": status,
            "priority": priority,
            "complexity": complexity,
            "is_blocking": [],
            "blocked_by": blocked_by,
            "acceptance_criteria": ac_items,
            "item_type": "task",
            "milestone": milestone,
            "start_date": start_date,
            "target_date": target_date,
        })

    return tasks


def _parse_spike_as_tasks(block: str, spike_id: str, milestone: str) -> list[dict[str, Any]]:
    """For spikes without explicit tasks, create tasks from deliverables."""
    deliverables = re.findall(r"- \[[ x]\] (.+)", block)
    if not deliverables:
        return []

    tasks: list[dict[str, Any]] = []
    for idx, deliverable in enumerate(deliverables, start=1):
        task_num = f"T-{spike_id.split('-')[1]}{idx:02d}"
        tasks.append({
            "id": task_num,
            "type": "task",
            "labels": ["analysis", "documentation"],
            "title": deliverable,
            "description": "",
            "status": "Backlog",
            "priority": "P1",
            "complexity": "M",
            "is_blocking": [],
            "blocked_by": [],
            "acceptance_criteria": [deliverable],
            "item_type": "task",
            "milestone": milestone,
            "start_date": "",
            "target_date": "",
        })

    return tasks


def _compute_is_blocking(tasks: list[dict[str, Any]]) -> None:
    """Compute is_blocking by inverting blocked_by relationships."""
    task_ids = {t["id"] for t in tasks}
    for task in tasks:
        for dep_id in task["blocked_by"]:
            if dep_id in task_ids:
                for other in tasks:
                    if other["id"] == dep_id and task["id"] not in other["is_blocking"]:
                        other["is_blocking"].append(task["id"])


def convert(content: str) -> dict[str, Any]:
    """Convert sprint.md content to the sprint.json schema.

    Args:
        content: Raw markdown string of a sprint.md file.

    Returns:
        Parsed sprint data matching sample_structure.json format.
    """
    return parse_sprint_md(content)
