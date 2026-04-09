"""Convert backlog.md to backlog JSON matching sample_structure.json format."""

import re
from typing import Any


def _story_type(prefix: str) -> str:
    """Map story ID prefix to type string."""
    mapping = {
        "US": "User Story",
        "TS": "Technical Story",
        "BG": "Bug",
        "SK": "Spike",
    }
    return mapping.get(prefix, "User Story")


def _parse_list_field(raw: str) -> list[str]:
    """Parse a comma-separated field like 'US-001, TS-002' into a list."""
    raw = raw.strip().strip("`").strip("[").strip("]")
    if not raw or raw.lower() in ("none", "-", "none / sk-nnn", "none / ts-nnn, us-nnn"):
        return []
    return [v.strip() for v in raw.split(",") if v.strip() and v.strip().lower() != "none"]


def convert(content: str) -> dict[str, Any]:
    """Convert backlog.md content to the backlog JSON schema."""
    lines = content.split("\n")

    project = ""
    goal = ""

    for line in lines:
        if "**Project:**" in line:
            project = line.split("**Project:**")[1].strip().strip("`")
        elif "**Goal:**" in line:
            goal = line.split("**Goal:**")[1].strip()

    stories = _parse_stories(lines)

    return {
        "project": project,
        "goal": goal,
        "dates": {"start": "", "end": ""},
        "totalPoints": 0,
        "stories": stories,
    }


def _parse_stories(lines: list[str]) -> list[dict[str, Any]]:
    """Parse story sections from ### headers under ## Stories."""
    stories: list[dict[str, Any]] = []
    stories_section_idx = -1

    for i, line in enumerate(lines):
        if line.strip() == "## Stories":
            stories_section_idx = i
            break

    if stories_section_idx < 0:
        return stories

    current: dict[str, Any] | None = None

    for i in range(stories_section_idx + 1, len(lines)):
        line = lines[i]

        match = re.match(r"^### ([\w-]+):\s*(.*)$", line)
        if match:
            if current:
                stories.append(current)
            sid = match.group(1)
            prefix = sid.split("-")[0] if "-" in sid else ""
            current = {
                "id": sid,
                "type": _story_type(prefix),
                "title": match.group(2).strip().strip("`"),
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
            continue

        if not current:
            continue

        stripped = line.strip()

        if stripped.startswith("**Description:**"):
            current["description"] = stripped.split("**Description:**")[1].strip().strip("`")
        elif stripped.startswith("**Priority:**"):
            current["priority"] = stripped.split("**Priority:**")[1].strip().strip("`")
        elif stripped.startswith("**Milestone:**"):
            current["milestone"] = stripped.split("**Milestone:**")[1].strip().strip("`")
        elif stripped.startswith("**Is Blocking:**"):
            current["is_blocking"] = _parse_list_field(stripped.split("**Is Blocking:**")[1])
        elif stripped.startswith("**Blocked By:**"):
            current["blocked_by"] = _parse_list_field(stripped.split("**Blocked By:**")[1])
        elif stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            criterion = re.sub(r"^- \[[ x]\] ", "", stripped).strip("`")
            current["acceptance_criteria"].append(criterion)

    if current:
        stories.append(current)

    return stories
