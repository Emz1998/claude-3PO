"""Validate backlog.md structure and format against the backlog schema."""

import re

VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_ITEM_TYPES = {"US", "TS", "BG", "SK"}

ID_PATTERNS = {
    "SK": r"^SK-\d+$",
    "TS": r"^TS-\d+$",
    "BG": r"^BG-\d+$",
    "US": r"^US-\d+$",
}


VALID_SECTIONS = {"Priority Legend", "ID Conventions", "Stories"}


def validate(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.split("\n")

    _validate_metadata(lines, errors)
    _validate_sections(lines, errors)
    stories = _parse_stories(lines)

    if not stories:
        errors.append("stories: no story sections found")
    else:
        for story in stories:
            _validate_story(story, errors)

    return errors


def _validate_metadata(lines: list[str], errors: list[str]) -> None:
    required = {
        "**Project:**": "Project",
        "**Last Updated:**": "Last Updated",
    }

    for key, label in required.items():
        found = [line for line in lines if key in line]
        if not found:
            errors.append(f"metadata: missing required field '{label}'")
        else:
            value = found[0].split(key)[1].strip().strip("`")
            if not value or value.startswith("["):
                errors.append(f"metadata.{label}: field is empty or placeholder")


def _validate_sections(lines: list[str], errors: list[str]) -> None:
    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            section = line[3:].strip()
            if section not in VALID_SECTIONS:
                errors.append(f"structure: unknown section '## {section}'")


def _parse_stories(lines: list[str]) -> list[dict]:
    """Parse story sections from ### headers under ## Stories."""
    stories: list[dict] = []
    stories_section_idx = -1

    for i, line in enumerate(lines):
        if line.strip() == "## Stories":
            stories_section_idx = i
            break

    if stories_section_idx < 0:
        return stories

    current_story: dict | None = None

    for i in range(stories_section_idx + 1, len(lines)):
        line = lines[i]

        # New story section
        match = re.match(r"^### ([\w-]+):\s*(.*)$", line)
        if match:
            if current_story:
                stories.append(current_story)
            current_story = {
                "id": match.group(1),
                "title": match.group(2).strip().strip("`"),
                "description": "",
                "priority": "",
                "milestone": "",
                "is_blocking": "",
                "blocked_by": "",
                "acceptance_criteria": [],
                "blockquotes": [],
                "line": i + 1,
            }
            continue

        if not current_story:
            continue

        stripped = line.strip()

        if stripped.startswith(">"):
            current_story["blockquotes"].append(stripped)
        elif stripped.startswith("**Description:**"):
            current_story["description"] = stripped.split("**Description:**")[1].strip().strip("`")
        elif stripped.startswith("**Priority:**"):
            current_story["priority"] = stripped.split("**Priority:**")[1].strip().strip("`")
        elif stripped.startswith("**Milestone:**"):
            current_story["milestone"] = stripped.split("**Milestone:**")[1].strip().strip("`")
        elif stripped.startswith("**Is Blocking:**"):
            current_story["is_blocking"] = stripped.split("**Is Blocking:**")[1].strip().strip("`")
        elif stripped.startswith("**Blocked By:**"):
            current_story["blocked_by"] = stripped.split("**Blocked By:**")[1].strip().strip("`")
        elif stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            current_story["acceptance_criteria"].append(stripped)

    if current_story:
        stories.append(current_story)

    return stories


def _validate_story(story: dict, errors: list[str]) -> None:
    sid = story["id"]
    prefix = sid.split("-")[0] if "-" in sid else ""
    pfx = f"stories.{sid}"

    if prefix not in VALID_ITEM_TYPES:
        errors.append(f"{pfx}.id: prefix '{prefix}' not in {VALID_ITEM_TYPES}")
    elif not re.match(ID_PATTERNS[prefix], sid):
        errors.append(f"{pfx}.id: '{sid}' doesn't match pattern for '{prefix}'")

    if not story["title"]:
        errors.append(f"{pfx}.title: is empty")

    if not story["description"]:
        errors.append(f"{pfx}.description: is empty")

    priority = story["priority"]
    if not priority:
        errors.append(f"{pfx}: missing **Priority:** field")
    elif priority not in VALID_PRIORITIES:
        errors.append(f"{pfx}.priority: '{priority}' not in {VALID_PRIORITIES}")

    if not story["acceptance_criteria"]:
        errors.append(f"{pfx}.acceptance_criteria: no criteria listed")

    # Validate blockquote format per story type
    blockquotes = story.get("blockquotes", [])
    bq_text = " ".join(blockquotes)

    if prefix == "US":
        if not re.search(r"\*\*As a\*\*", bq_text):
            errors.append(f"{pfx}.format: US stories must have '> **As a** [role], **I want** [what] **so that** [why]'")
    elif prefix == "TS":
        if not re.search(r"\*\*As a\*\*", bq_text):
            errors.append(f"{pfx}.format: TS stories must have '> **As a** [dev/system], **I need** [what] **so that** [why]'")
    elif prefix == "SK":
        if not re.search(r"\*\*Investigate:\*\*", bq_text):
            errors.append(f"{pfx}.format: SK stories must have '> **Investigate:** [what]' and '> **To decide:** [what]'")
    elif prefix == "BG":
        if not re.search(r"\*\*What's broken:\*\*", bq_text):
            errors.append(f"{pfx}.format: BG stories must have '> **What\\'s broken:** [x]', '> **Expected:** [x]', '> **Actual:** [x]'")
