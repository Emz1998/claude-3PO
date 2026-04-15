#!/usr/bin/env python3
"""summarize_prompt.py — UserPromptSubmit async hook.

Parses the user prompt for /build <instructions>, runs headless Claude
to summarize, writes prompt_summary to state, and resolves any
'Pending...' entries in violations.md.

Runs with async:true in hooks.json — non-blocking.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

from lib.hook import Hook
from lib.state_store import StateStore
from lib.extractors import extract_build_instructions
from lib.violations import resolve_pending_summaries, VIOLATIONS_PATH

STATE_PATH = SCRIPTS_DIR / "state.jsonl"


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------


def _build_summary_prompt(instructions: str) -> str:
    return (
        "Summarize the following task instructions in one short sentence (under 60 characters). "
        "Respond with ONLY the summary, nothing else.\n\n"
        f"Instructions: {instructions}"
    )


def _invoke_claude(prompt: str) -> str | None:
    """Run headless Claude to generate text. Returns output or None on failure."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt,
             "--output-format", "text",
             "--tools", "Read,Grep,Glob"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:80]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _truncate(text: str, max_len: int = 60) -> str:
    return text[:max_len] if len(text) > max_len else text


def summarize(instructions: str) -> str:
    """Use headless Claude to generate a short summary. Falls back to truncated instructions."""
    prompt = _build_summary_prompt(instructions)
    return _invoke_claude(prompt) or _truncate(instructions)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    prompt = hook_input.get("prompt", "")
    if not prompt:
        sys.exit(0)

    instructions = extract_build_instructions(prompt)
    if not instructions:
        sys.exit(0)

    state = StateStore(STATE_PATH, session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)
    if state.get("workflow_type") != "build":
        sys.exit(0)

    summary = summarize(instructions)
    state.set("prompt_summary", summary)
    resolve_pending_summaries(VIOLATIONS_PATH, session_id, summary)

    sys.exit(0)


if __name__ == "__main__":
    main()
