"""Convert backlog.md markdown to backlog JSON matching sample_structure.json.

Parses the markdown structure (metadata, ## Stories, ### story headers)
and produces a dict with project, goal, dates, totalPoints, and stories.
"""

import re
from typing import Any


def _story_type(prefix: str) -> str:
    """Map a story ID prefix (e.g. 'US', 'BG') to its full type name.

    Returns 'User Story' for unrecognized prefixes.
    """
    mapping = {
        "US": "User Story",
        "TS": "Technical Story",
        "BG": "Bug",
        "SK": "Spike",
    }
    return mapping.get(prefix, "User Story")


def _parse_list_field(raw: str) -> list[str]:
    """Parse a comma-separated field into a list of trimmed strings.

    Strips surrounding backticks and brackets. Returns an empty list for
    placeholder values like 'None', '-', or template patterns.
    """
    raw = raw.strip().strip("`").strip("[").strip("]")
    if not raw or raw.lower() in ("none", "-", "none / sk-nnn", "none / ts-nnn, us-nnn"):
        return []
    return [v.strip() for v in raw.split(",") if v.strip() and v.strip().lower() != "none"]


def _extract_metadata(lines: list[str]) -> tuple[str, str]:
    """Extract project name and goal from **Project:** and **Goal:** lines.

    Returns a (project, goal) tuple; either value defaults to '' if not found.
    """
    project = ""
    goal = ""
    for line in lines:
        if "**Project:**" in line:
            project = line.split("**Project:**")[1].strip().strip("`")
        elif "**Goal:**" in line:
            goal = line.split("**Goal:**")[1].strip()
    return project, goal


def convert(content: str) -> dict[str, Any]:
    """Convert raw backlog.md content into the backlog JSON schema.

    Returns a dict with keys: project, goal, dates, totalPoints, stories.
    Dates and totalPoints are initialized to empty/zero defaults.
    """
    lines = content.split("\n")
    project, goal = _extract_metadata(lines)
    stories = _parse_stories(lines)
    return {
        "project": project,
        "goal": goal,
        "dates": {"start": "", "end": ""},
        "totalPoints": 0,
        "stories": stories,
    }


def _find_stories_section(lines: list[str]) -> int:
    """Return the line index of the '## Stories' header, or -1 if absent."""
    for i, line in enumerate(lines):
        if line.strip() == "## Stories":
            return i
    return -1


def _new_story(sid: str, title: str) -> dict[str, Any]:
    """Create a story dict with all required fields set to defaults.

    The story type is inferred from the ID prefix (e.g. 'US' -> 'User Story').
    """
    prefix = sid.split("-")[0] if "-" in sid else ""
    return {
        "id": sid,
        "type": _story_type(prefix),
        "title": title,
        "description": "",
        "status": "Backlog",
        "priority": "",
        "is_blocking": [],
        "blocked_by": [],
        "acceptance_criteria": [],
        "item_type": "story",
        "milestone": "",
        "start_date": "",
        "target_date": "",
    }


def _parse_story_field(story: dict[str, Any], stripped: str) -> None:
    """Parse a single markdown field line and update the story dict in place.

    Handles **Description:**, **Priority:**, **Milestone:**, dependency
    fields (**Is Blocking:**, **Blocked By:**), and acceptance criteria
    checkboxes (- [ ] / - [x]). Unrecognized lines are silently ignored.
    """
    field_map = {
        "**Description:**": "description",
        "**Priority:**": "priority",
        "**Milestone:**": "milestone",
    }
    for marker, key in field_map.items():
        if stripped.startswith(marker):
            story[key] = stripped.split(marker)[1].strip().strip("`")
            return

    if stripped.startswith("**Is Blocking:**"):
        story["is_blocking"] = _parse_list_field(stripped.split("**Is Blocking:**")[1])
    elif stripped.startswith("**Blocked By:**"):
        story["blocked_by"] = _parse_list_field(stripped.split("**Blocked By:**")[1])
    elif stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
        criterion = re.sub(r"^- \[[ x]\] ", "", stripped).strip("`")
        story["acceptance_criteria"].append(criterion)


def _parse_stories(lines: list[str]) -> list[dict[str, Any]]:
    """Parse all story sections below the '## Stories' header.

    Each story starts at a '### ID: Title' header. Lines between headers
    are parsed as story fields via _parse_story_field.
    """
    start = _find_stories_section(lines)
    if start < 0:
        return []

    stories: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for i in range(start + 1, len(lines)):
        match = re.match(r"^### ([\w-]+):\s*(.*)$", lines[i])
        if match:
            if current:
                stories.append(current)
            current = _new_story(match.group(1), match.group(2).strip().strip("`"))
            continue
        if current:
            _parse_story_field(current, lines[i].strip())

    if current:
        stories.append(current)
    return stories
