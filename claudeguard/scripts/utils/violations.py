"""violations.py — Append-only markdown violation logger.

Logs every guardrail block to .claude/logs/violations.md.
"""

from datetime import datetime
from pathlib import Path
from filelock import FileLock

VIOLATIONS_PATH = Path(".claude/logs/violations.md")

HEADER = "| Timestamp | Session | Workflow | Story ID | Prompt Summary | Phase | Tool | Action | Reason |"
SEPARATOR = "|-----------|---------|----------|----------|----------------|-------|------|--------|--------|"


def _escape_pipe(value: str) -> str:
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
    """Append a violation row to the violations log."""
    path = VIOLATIONS_PATH
    lock = FileLock(path.with_suffix(".lock"))

    story = story_id or "N/A"
    summary = prompt_summary or ("N/A" if workflow_type == "implement" else "Pending...")
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


def resolve_pending_summaries(path: Path, session_id: str, summary: str) -> None:
    """Replace 'Pending...' with the actual summary for a session."""
    if not path.exists():
        return

    lock = FileLock(path.with_suffix(".lock"))
    with lock:
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        updated = []

        for line in lines:
            if f"| {session_id} " in line and "| Pending... |" in line:
                line = line.replace("| Pending... |", f"| {_escape_pipe(summary)} |")
            updated.append(line)

        path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def extract_action(tool_name: str, hook_input: dict) -> str:
    """Extract the relevant action string from hook input based on tool type."""
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
