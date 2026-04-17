#!/usr/bin/env python3
"""UserPromptSubmit async hook — generate ``state.prompt_summary``.

Flow:
    1. Read hook stdin; bail unless this is a `/build <instructions>` prompt
       on an active build workflow.
    2. Ask headless Claude for a one-sentence summary (~60 chars).
    3. Persist the summary to state and back-fill any `Pending...` rows in
       `violations.md` that were logged before the summary was available.

Registered with ``async: true`` in `hooks.json`, so it must never block
the live session — every failure path falls back silently rather than
raising.
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

from lib.hook import Hook
from lib.shell import invoke_claude
from lib.state_store import StateStore
from lib.extractors import extract_build_instructions
from lib.violations import resolve_pending_summaries, VIOLATIONS_PATH

STATE_PATH = SCRIPTS_DIR / "state.jsonl"


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------


def _build_summary_prompt(instructions: str) -> str:
    """Render the instruction string as a Claude prompt asking for a ≤60-char summary."""
    return (
        "Summarize the following task instructions in one short sentence (under 60 characters). "
        "Respond with ONLY the summary, nothing else.\n\n"
        f"Instructions: {instructions}"
    )


def _truncate(text: str, max_len: int = 60) -> str:
    """Hard-cap raw instruction text used as the fallback summary."""
    return text[:max_len] if len(text) > max_len else text


def summarize(instructions: str) -> str:
    """Return a short summary of ``instructions`` for the violations log.

    Calls headless Claude with a 30s timeout. The model output is trimmed
    to 80 chars (looser than the 60-char prompt target — the model often
    overshoots slightly, and a few extra chars beat a silent truncation).
    On any failure (timeout, missing CLI, empty output) falls back to the
    first 60 chars of ``instructions`` so the summary field is never empty.
    """
    prompt = _build_summary_prompt(instructions)
    output = invoke_claude(prompt, timeout=30)
    return output[:80] if output else _truncate(instructions)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point — runs once per UserPromptSubmit event.

    Exits silently (status 0) on every "this prompt isn't for us" branch:
    no session id, no prompt body, prompt isn't a `/build`, no active
    workflow, or workflow isn't ``build``. Only when all checks pass do
    we spend a Claude call to generate the summary.
    """
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
