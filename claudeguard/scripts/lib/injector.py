"""Injector — Injects metadata into files after they're written."""

from datetime import datetime
from pathlib import Path

from lib.extractors import extract_md_body
from lib.state_store import StateStore


def _build_frontmatter(state: StateStore) -> str:
    metadata = {
        "session_id": state.get("session_id"),
        "workflow_type": state.get("workflow_type"),
        "story_id": state.get("story_id"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
    }
    lines = ["---"]
    for key, val in metadata.items():
        if val is not None:
            lines.append(f"{key}: {val}")
    lines.append("---\n")
    return "\n".join(lines)


def inject_plan_metadata(file_path: str, state: StateStore) -> None:
    """Inject frontmatter metadata into the plan file after it's written."""
    path = Path(file_path)
    if not path.exists():
        return

    content = extract_md_body(path.read_text())
    path.write_text(_build_frontmatter(state) + content)
