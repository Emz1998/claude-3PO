"""violations.py — Append-only markdown violation logger.

Logs every guardrail block to ``${CLAUDE_PLUGIN_ROOT}/logs/violations.md`` as
a markdown table. Override the target path with the ``VIOLATIONS_PATH`` env
variable (used by tests). The log is human-browseable as plain markdown but
machine-parseable via the table separator, so the same file serves both
debugging and automation.
"""

import os
from datetime import datetime
from pathlib import Path
from filelock import FileLock

from constants.paths import PLUGIN_ROOT

VIOLATIONS_PATH = Path(
    os.environ.get("VIOLATIONS_PATH", str(PLUGIN_ROOT / "logs" / "violations.md"))
)

HEADER = "| Timestamp | Session | Workflow | Story ID | Prompt Summary | Phase | Tool | Action | Reason |"
SEPARATOR = "|-----------|---------|----------|----------|----------------|-------|------|--------|--------|"


def _escape_pipe(value: str) -> str:
    """Escape ``|`` so a free-text value can sit inside a markdown table cell.

    Example:
        >>> _escape_pipe("a|b")
        'a\\\\|b'
    """
    return value.replace("|", "\\|")


def log_violation(
    session_id: str,
    workflow_type: str,
    story_id: str | None,
    prompt_summary: str | None,
    phase: str,
    tool: str,
    action: str,
    reason: str,
) -> None:
    """
    Append one violation row to the violations log, creating the file if needed.

    The first ever write seeds the markdown header + separator so the file is
    immediately rendered as a table. Missing ``story_id`` / ``prompt_summary``
    are recorded as ``"N/A"``.

    Args:
        session_id (str): Unique session identifier.
        workflow_type (str): Workflow identifier (e.g. ``"implement"``).
        story_id (str | None): Story being worked, or ``None``.
        prompt_summary (str | None): Short user-prompt summary; ``"N/A"`` if missing.
        phase (str): Workflow phase name when the block fired.
        tool (str): Tool that triggered the block (``Write``, ``Bash``, …).
        action (str): Tool-specific action string (file path, command, …).
        reason (str): Human-readable block reason.

    Returns:
        None: Side-effects only — appends to the violations file.

    Example:
        >>> log_violation("s1", "implement", "US-001", "add login",
        ...               "plan", "Write", "/x.py", "blocked")  # doctest: +SKIP
    """
    path = VIOLATIONS_PATH
    lock = FileLock(path.with_suffix(".lock"))

    story = story_id or "N/A"
    summary = prompt_summary or "N/A"
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    row = (
        f"| {timestamp} "
        f"| {_escape_pipe(session_id)} "
        f"| {workflow_type} "
        f"| {_escape_pipe(story)} "
        f"| {_escape_pipe(summary)} "
        f"| {phase} "
        f"| {tool} "
        f"| {_escape_pipe(action)} "
        f"| {_escape_pipe(reason)} |"
    )

    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists() or path.stat().st_size == 0:
            path.write_text(f"{HEADER}\n{SEPARATOR}\n{row}\n", encoding="utf-8")
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(row + "\n")


def extract_action(tool_name: str, hook_input: dict) -> str:
    """
    Pull the most informative action string from a hook payload.

    Each tool stores its "what it's doing" in a different field — file_path
    for Write/Edit, command for Bash, subagent_type for Agent, etc. This
    centralizes the per-tool unpacking so the logger doesn't have to know
    the schema. Bash commands are truncated to 80 chars to keep the table
    cell readable.

    Args:
        tool_name (str): Tool name (``"Write"``, ``"Bash"``, ``"Agent"``,
            ``"Skill"``, ``"WebFetch"``).
        hook_input (dict): Full hook payload.

    Returns:
        str: Action string suitable for the violations log; ``""`` if the
        tool isn't recognized or its field is missing.

    Example:
        >>> extract_action("Write", {"tool_input": {"file_path": "/a.py"}})
        '/a.py'
    """
    tool_input = hook_input.get("tool_input", {})

    if tool_name in ("Write", "Edit"):
        return tool_input.get("file_path", "")
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return cmd[:80] if len(cmd) > 80 else cmd
    if tool_name == "Agent":
        return tool_input.get("subagent_type", "")
    if tool_name == "Skill":
        return tool_input.get("skill", "")
    if tool_name == "WebFetch":
        return tool_input.get("url", "")

    return ""
