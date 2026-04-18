"""injector.py — Stamp YAML frontmatter onto generated artifacts after writing.

The plan file is written by Claude as plain markdown (no frontmatter), then
post-processed by a hook that calls into here. Centralizing the metadata
shape in one place means the archive/parser flow only has to know about one
schema.
"""

from datetime import datetime
from pathlib import Path

from lib.extractors import extract_md_body
from lib.state_store import StateStore


def _build_frontmatter(state: StateStore) -> str:
    """Render session/workflow/story metadata as a YAML frontmatter block.

    Example:
        >>> _build_frontmatter(state)  # doctest: +SKIP
    """
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
    """
    Prepend session/workflow frontmatter to a freshly-written plan file.

    Existing frontmatter is stripped first via :func:`extract_md_body` so
    repeated invocations stay idempotent — the latest call always wins.
    Missing files are a silent no-op since this hook may fire on writes
    that don't actually produce a plan.

    Args:
        file_path (str): Absolute path to the plan markdown file.
        state (StateStore): Session state used to derive ``session_id``,
            ``workflow_type``, and ``story_id``.

    Returns:
        None: Side-effects only — rewrites the file in place.

    Example:
        >>> inject_plan_metadata("/tmp/plan.md", state)  # doctest: +SKIP
    """
    path = Path(file_path)
    if not path.exists():
        return

    content = extract_md_body(path.read_text())
    path.write_text(_build_frontmatter(state) + content)
