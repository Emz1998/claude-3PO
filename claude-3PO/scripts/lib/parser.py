"""parser.py — Parsing helpers for workflow initialization."""

import re

from constants import STORY_ID_PATTERN


def parse_frontmatter(content: str) -> dict[str, str]:
    """Extract frontmatter key-value pairs from markdown."""
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip()
    return fm


def parse_skip(args: str) -> list[str]:
    skip: list[str] = []
    if "--skip-explore" in args or "--skip-all" in args:
        skip.append("explore")
    if "--skip-research" in args or "--skip-all" in args:
        skip.append("research")
    if "--skip-vision" in args:
        skip.append("vision")
    return skip


def parse_story_id(args: str) -> str | None:
    match = re.search(STORY_ID_PATTERN, args)
    return match.group(1) if match else None


def parse_instructions(args: str) -> str:
    flags = [
        "--skip-explore", "--skip-research", "--skip-vision", "--skip-all",
        "--tdd", "--reset", "--takeover", "--test",
    ]
    text = re.sub(STORY_ID_PATTERN, "", args)
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()
