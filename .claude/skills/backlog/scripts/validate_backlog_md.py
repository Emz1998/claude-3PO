"""Validate backlog.md structure and format against the backlog schema.

Checks metadata fields, section headers, story IDs, priorities,
acceptance criteria, and per-type blockquote formats (US/TS/SK/BG).
Returns a list of human-readable error strings.
"""

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
    """Validate raw backlog.md content and return a list of error messages.

    An empty list means the markdown is valid. Checks metadata, sections,
    and every story found under '## Stories'.
    """
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
    """Verify required metadata fields (Project, Last Updated) are present and non-empty."""
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
    """Flag any '## ' section headers not in the allowed set."""
    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            section = line[3:].strip()
            if section not in VALID_SECTIONS:
                errors.append(f"structure: unknown section '## {section}'")


def _find_stories_section(lines: list[str]) -> int:
    """Return the line index of '## Stories', or -1 if absent."""
    for i, line in enumerate(lines):
        if line.strip() == "## Stories":
            return i
    return -1


def _new_story_entry(sid: str, title: str, line_num: int) -> dict:
    """Create a story dict with default fields for markdown validation."""
    return {
        "id": sid,
        "title": title,
        "description": "",
        "priority": "",
        "milestone": "",
        "is_blocking": "",
        "blocked_by": "",
        "acceptance_criteria": [],
        "blockquotes": [],
        "line": line_num,
    }


def _parse_story_line(story: dict, stripped: str) -> None:
    """Parse a single markdown line and update the story dict in place.

    Handles blockquotes, field markers, and acceptance criteria checkboxes.
    Unrecognized lines are silently ignored.
    """
    if stripped.startswith(">"):
        story["blockquotes"].append(stripped)
    elif stripped.startswith("**Description:**"):
        story["description"] = stripped.split("**Description:**")[1].strip().strip("`")
    elif stripped.startswith("**Priority:**"):
        story["priority"] = stripped.split("**Priority:**")[1].strip().strip("`")
    elif stripped.startswith("**Milestone:**"):
        story["milestone"] = stripped.split("**Milestone:**")[1].strip().strip("`")
    elif stripped.startswith("**Is Blocking:**"):
        story["is_blocking"] = stripped.split("**Is Blocking:**")[1].strip().strip("`")
    elif stripped.startswith("**Blocked By:**"):
        story["blocked_by"] = stripped.split("**Blocked By:**")[1].strip().strip("`")
    elif stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
        story["acceptance_criteria"].append(stripped)


def _parse_stories(lines: list[str]) -> list[dict]:
    """Parse all story sections below the '## Stories' header.

    Each story starts at a '### ID: Title' header. Lines between headers
    are parsed as story fields via _parse_story_line.
    """
    start = _find_stories_section(lines)
    if start < 0:
        return []

    stories: list[dict] = []
    current: dict | None = None

    for i in range(start + 1, len(lines)):
        match = re.match(r"^### ([\w-]+):\s*(.*)$", lines[i])
        if match:
            if current:
                stories.append(current)
            current = _new_story_entry(match.group(1), match.group(2).strip().strip("`"), i + 1)
            continue
        if current:
            _parse_story_line(current, lines[i].strip())

    if current:
        stories.append(current)
    return stories


def _validate_story(story: dict, errors: list[str]) -> None:
    """Run all validations on a single parsed story."""
    sid = story["id"]
    prefix = sid.split("-")[0] if "-" in sid else ""
    pfx = f"stories.{sid}"

    _validate_story_id(sid, prefix, pfx, errors)
    _validate_story_fields(story, pfx, errors)
    _validate_story_blockquote(story, prefix, pfx, errors)


def _validate_story_id(
    sid: str, prefix: str, pfx: str, errors: list[str]
) -> None:
    """Check that the story ID prefix is valid and matches its regex pattern."""
    if prefix not in VALID_ITEM_TYPES:
        errors.append(f"{pfx}.id: prefix '{prefix}' not in {VALID_ITEM_TYPES}")
    elif not re.match(ID_PATTERNS[prefix], sid):
        errors.append(f"{pfx}.id: '{sid}' doesn't match pattern for '{prefix}'")


def _validate_story_fields(
    story: dict, pfx: str, errors: list[str]
) -> None:
    """Check required story fields: title, description, priority, and acceptance criteria."""
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


def _validate_story_blockquote(
    story: dict, prefix: str, pfx: str, errors: list[str]
) -> None:
    """Validate blockquote format matches the expected pattern for the story type."""
    bq_text = " ".join(story.get("blockquotes", []))

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
