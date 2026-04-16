"""Convert sprint.md markdown into a sprint.json dict.

Parses sprint metadata, stories (User Story, Technical Story, Bug, Spike),
and tasks from markdown format into a structured dict matching
sample_structure.json. Handles blocked-by/is-blocking dependency graphs
and spike-to-task conversion for stories without explicit tasks.
"""

import re
from typing import Any


def _safe_int(value: str, default: int = 0) -> int:
    """Convert a string to int, returning default on failure."""
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


def _parse_header_line(line: str, prefix: str) -> str:
    """Extract the value after a bold markdown prefix."""
    return line.split(prefix)[1].strip()


def _parse_due_date(line: str) -> str:
    """Extract due date from a Dates line with arrow/to separator."""
    dates_raw = _parse_header_line(line, "**Dates:**")
    parts = [d.strip() for d in re.split(r"→|->|to", dates_raw)]
    return parts[1] if len(parts) > 1 else parts[0] if parts else ""


_METADATA_FIELDS: dict[str, str] = {
    "**Sprint #:**": "sprint",
    "**Goal:**": "description",
    "**Milestone:**": "milestone",
    "**Due Date:**": "due_date",
}


def _parse_sprint_metadata(content: str) -> dict[str, Any]:
    """Extract sprint number, milestone, goal, and due date from header lines."""
    result: dict[str, Any] = {"sprint": 0, "milestone": "", "description": "", "due_date": ""}

    for line in content.split("\n"):
        for prefix, key in _METADATA_FIELDS.items():
            if line.startswith(prefix):
                value = _parse_header_line(line, prefix)
                result[key] = _safe_int(value) if key == "sprint" else value
                break
        else:
            if line.startswith("**Dates:**"):
                result["due_date"] = _parse_due_date(line)

    return result


def _parse_story_description(block: str) -> str:
    """Extract story description from blockquote lines."""
    desc_match = re.search(r">\s*(.+?)(?:\n(?!>)|$)", block, re.DOTALL)
    if not desc_match:
        return ""
    raw_desc = desc_match.group(0)
    return re.sub(r"\n>\s*", " ", raw_desc).strip().lstrip("> ").strip()


def _parse_story_fields(block: str) -> dict[str, Any]:
    """Extract status, priority, labels, points, TDD, blocking, and dates from a story block."""
    return {
        "status": _parse_field(block, "Status") or "Ready",
        "priority": _parse_field(block, "Priority"),
        "labels": _parse_csv(_parse_field(block, "Labels")),
        "points": _safe_int(_parse_field(block, "Points")),
        "tdd": _parse_field(block, "TDD").lower() == "true",
        "is_blocking": _parse_csv(_parse_field(block, "Is Blocking")),
        "blocked_by": _parse_csv(_parse_field(block, "Blocked By")),
        "start_date": _parse_field(block, "Start Date"),
        "target_date": _parse_field(block, "Target Date"),
    }


def _parse_story_acceptance_criteria(block: str) -> list[str]:
    """Extract acceptance criteria before the tasks section."""
    tasks_marker = block.find("**Tasks:**")
    ac_block = block[:tasks_marker] if tasks_marker != -1 else block
    return re.findall(r"- \[[ x]\] (.+)", ac_block)


def _parse_story_tasks(block: str, prefix: str, story_id: str, milestone: str) -> list[dict[str, Any]]:
    """Parse tasks for a story, falling back to spike deliverables."""
    tasks = _parse_tasks(block, milestone)
    if _story_type(prefix) == "Spike" and not tasks:
        tasks = _parse_spike_as_tasks(block, story_id, milestone)
    _compute_is_blocking(tasks)
    return tasks


def _parse_story(prefix: str, story_num: str, story_title: str, block: str, milestone: str) -> dict[str, Any]:
    """Assemble a complete story dict from its markdown block and header match groups."""
    story_id = f"{prefix}-{story_num}"
    fields = _parse_story_fields(block)
    tasks = _parse_story_tasks(block, prefix, story_id, milestone)

    return {
        "id": story_id,
        "type": _story_type(prefix),
        "title": story_title,
        "description": _parse_story_description(block),
        "acceptance_criteria": _parse_story_acceptance_criteria(block),
        "item_type": "story",
        "milestone": milestone,
        "tasks": tasks,
        **fields,
    }


def _parse_stories(content: str, milestone: str) -> list[dict[str, Any]]:
    """Split content by #### headers and parse each story section."""
    story_pattern = r"#### ([A-Z]{2})-(\d+):\s*(.+?)(?:\n|$)"
    story_matches = list(re.finditer(story_pattern, content))

    stories: list[dict[str, Any]] = []
    for idx, smatch in enumerate(story_matches):
        start = smatch.end()
        end = story_matches[idx + 1].start() if idx + 1 < len(story_matches) else len(content)
        block = content[start:end]

        story = _parse_story(smatch.group(1), smatch.group(2), smatch.group(3).strip(), block, milestone)
        stories.append(story)

    return stories


def parse_sprint_md(content: str) -> dict[str, Any]:
    """Parse full sprint markdown into a dict with metadata and stories."""
    metadata = _parse_sprint_metadata(content)
    stories = _parse_stories(content, metadata["milestone"])
    return {**metadata, "stories": stories}


def _parse_task_title(task_body: str) -> str:
    """Extract the task title from the first line of the body."""
    title_match = re.match(r"\s*(.+?)(?:\n|$)", task_body)
    return title_match.group(1).strip() if title_match else ""


def _parse_task_blocked_by(task_body: str) -> list[str]:
    """Extract blocked-by dependencies, checking both field name variants."""
    raw = _parse_field(task_body, "Blocked by")
    if not raw:
        raw = _parse_field(task_body, "Depends on")
    return _parse_csv(raw)


def _parse_task_fields(task_body: str) -> dict[str, Any]:
    """Extract labels, description, status, priority, complexity, AC, and dates from a task body."""
    return {
        "labels": _parse_csv(_parse_field(task_body, "Labels")),
        "description": _parse_field(task_body, "Description"),
        "status": _parse_field(task_body, "Status") or "Backlog",
        "priority": _parse_field(task_body, "Priority"),
        "complexity": _parse_field(task_body, "Complexity"),
        "acceptance_criteria": re.findall(r"- \[[ x]\] (.+)", task_body),
        "start_date": _parse_field(task_body, "Start date"),
        "target_date": _parse_field(task_body, "Target date"),
    }


def _parse_single_task(task_id: str, task_body: str, milestone: str) -> dict[str, Any]:
    """Assemble a complete task dict from its ID, body text, and milestone."""
    return {
        "id": task_id,
        "type": "task",
        "title": _parse_task_title(task_body),
        "is_blocking": [],
        "blocked_by": _parse_task_blocked_by(task_body),
        "item_type": "task",
        "milestone": milestone,
        **_parse_task_fields(task_body),
    }


def _parse_tasks(block: str, milestone: str) -> list[dict[str, Any]]:
    """Split a story block by T-NNN markers and parse each task."""
    task_splits = re.split(r"- \*\*T-(\d+):\*\*", block)
    return [
        _parse_single_task(f"T-{task_splits[i]}", task_splits[i + 1], milestone)
        for i in range(1, len(task_splits), 2)
    ]


def _build_spike_task(task_id: str, deliverable: str, milestone: str) -> dict[str, Any]:
    """Build a single task dict from a spike deliverable."""
    return {
        "id": task_id,
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
    }


def _parse_spike_as_tasks(block: str, spike_id: str, milestone: str) -> list[dict[str, Any]]:
    """For spikes without explicit tasks, create tasks from deliverables."""
    deliverables = re.findall(r"- \[[ x]\] (.+)", block)
    spike_num = spike_id.split("-")[1]
    return [
        _build_spike_task(f"T-{spike_num}{idx:02d}", d, milestone)
        for idx, d in enumerate(deliverables, start=1)
    ]


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
